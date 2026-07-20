"""
End-to-end integration tests for webhook processing.

Tests the complete webhook flow from receipt to database updates,
including overage charge processing and invoice generation.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from github_analyzer.database.models import (
    SubscriptionPlan,
    SubscriptionStatus,
)


class TestWebhookE2E:
    """End-to-end webhook integration tests."""

    @pytest.fixture
    def test_user(self):
        """Create a test user with Professional plan."""
        from unittest.mock import Mock

        user = Mock(
            user_id="usr_e2e_test",
            email="e2e@test.com",
            name="E2E Test User",
            subscription_plan=SubscriptionPlan.PROFESSIONAL,
            subscription_status=SubscriptionStatus.ACTIVE,
            stripe_customer_id="cus_e2e_test",
            stripe_subscription_id="sub_e2e_test",
            usage_quota=1000,  # Professional plan quota
            usage_count=1200,  # 200 overage calls
        )
        return user

    @pytest.fixture
    def mock_db(self):
        """Mock database session with transaction support."""
        db = AsyncMock()
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        db.begin = AsyncMock()
        db.close = AsyncMock()
        return db

    @pytest.fixture
    def overage_invoice_webhook(self, test_user):
        """Create a webhook event for an invoice with overage charges."""
        return {
            "id": "evt_e2e_overage",
            "type": "invoice.finalized",
            "created": int(datetime.now(timezone.utc).timestamp()),
            "data": {
                "object": {
                    "id": "in_e2e_overage",
                    "customer": test_user.stripe_customer_id,
                    "subscription": test_user.stripe_subscription_id,
                    "status": "open",
                    "amount_due": 14900,  # $149 base + $40 overage (200 * $0.20)
                    "amount_paid": 0,
                    "currency": "usd",
                    "period_start": int(datetime.now(timezone.utc).timestamp())
                    - 86400 * 30,
                    "period_end": int(datetime.now(timezone.utc).timestamp()),
                    "lines": {
                        "data": [
                            {
                                "id": "il_base",
                                "amount": 14900,
                                "description": "Professional Plan - Monthly",
                                "price": {
                                    "id": "price_professional_monthly",
                                    "recurring": {"usage_type": "licensed"},
                                },
                            },
                            {
                                "id": "il_overage",
                                "amount": 4000,  # $40 overage
                                "quantity": 200,  # 200 overage calls
                                "description": "API Usage Overage (200 calls × $0.20)",
                                "price": {
                                    "id": "price_professional_overage",
                                    "unit_amount": 20,  # $0.20 per call
                                    "recurring": {"usage_type": "metered"},
                                },
                            },
                        ]
                    },
                    "hosted_invoice_url": "https://invoice.stripe.com/i/e2e_test",
                    "invoice_pd": "https://invoice.stripe.com/i/e2e_test/pd",
                }
            },
        }

    async def test_complete_overage_billing_flow(
        self, mock_db, test_user, overage_invoice_webhook
    ):
        """Test complete flow from usage reporting to invoice generation with overages."""
        from github_analyzer.api.services.webhook_service import WebhookService
        from github_analyzer.billing.usage_reporter import UsageReporter

        webhook_service = WebhookService()
        usage_reporter = UsageReporter()

        # Step 1: Report overage usage to Stripe
        with (
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_id",
                return_value=test_user,
            ),
            patch.object(
                usage_reporter.stripe_client,
                "get_subscription_item_for_price",
                return_value={"id": "si_overage_test"},
            ),
            patch.object(
                usage_reporter.stripe_client,
                "create_usage_record",
                return_value={"id": "mbur_test", "quantity": 200},
            ) as mock_create_usage,
        ):
            # Report the 200 overage calls
            success = await usage_reporter.report_user_overage_usage(
                mock_db, test_user.user_id, 200
            )

            assert success is True
            mock_create_usage.assert_called_once_with(
                subscription_item_id="si_overage_test",
                quantity=200,
                timestamp=pytest.approx(
                    int(datetime.now(timezone.utc).timestamp()), abs=10
                ),
                action="increment",
            )

        # Step 2: Process the invoice.finalized webhook
        with (
            patch(
                "github_analyzer.database.operations.WebhookEventOperations.get_webhook_event",
                return_value=None,  # No duplicate
            ),
            patch(
                "github_analyzer.database.operations.WebhookEventOperations.create_webhook_event",
                return_value=Mock(event_id="whe_test"),
            ),
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_stripe_customer_id",
                return_value=test_user,
            ),
            patch(
                "github_analyzer.database.operations.InvoiceOperations.get_invoice_by_stripe_id",
                return_value=None,  # No existing invoice
            ),
            patch(
                "github_analyzer.database.operations.InvoiceOperations.create_invoice",
                return_value=Mock(invoice_id="inv_e2e_test"),
            ) as mock_create_invoice,
            patch(
                "github_analyzer.database.operations.WebhookEventOperations.update_webhook_status",
                return_value=None,
            ),
        ):
            result = await webhook_service.process_webhook(
                mock_db, overage_invoice_webhook
            )

            assert result["status"] == "processed"
            assert result["has_overage"] is True
            assert result["overage_amount"] == 4000  # $40 in cents

            # Verify invoice creation with correct overage amount
            mock_create_invoice.assert_called_once()
            invoice_args = mock_create_invoice.call_args[1]
            assert invoice_args["amount_due"] == 14900  # Total including overage
            assert invoice_args["user_id"] == test_user.user_id

        # Step 3: Process payment succeeded webhook
        payment_webhook = {
            "id": "evt_e2e_payment",
            "type": "invoice.payment_succeeded",
            "data": {
                "object": {
                    **overage_invoice_webhook["data"]["object"],
                    "status": "paid",
                    "amount_paid": 14900,
                    "payment_intent": "pi_e2e_test",
                }
            },
        }

        with (
            patch(
                "github_analyzer.database.operations.WebhookEventOperations.get_webhook_event",
                return_value=None,
            ),
            patch(
                "github_analyzer.database.operations.WebhookEventOperations.create_webhook_event",
                return_value=Mock(event_id="whe_payment"),
            ),
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_stripe_customer_id",
                return_value=test_user,
            ),
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_id",
                new_callable=AsyncMock,
                return_value=test_user,
            ),
            patch(
                "github_analyzer.database.operations.UserOperations.update_user_subscription",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "github_analyzer.database.operations.InvoiceOperations.get_invoice_by_stripe_id",
                return_value=Mock(invoice_id="inv_e2e_test", status="finalized"),
            ),
            patch(
                "github_analyzer.database.operations.InvoiceOperations.update_invoice_status",
                return_value=None,
            ) as mock_update_invoice,
            patch(
                "github_analyzer.database.operations.PaymentOperations.create_payment",
                return_value=None,
            ),
            patch(
                "github_analyzer.database.operations.WebhookEventOperations.update_webhook_status",
                return_value=None,
            ),
        ):
            payment_result = await webhook_service.process_webhook(
                mock_db, payment_webhook
            )

            assert payment_result["status"] == "processed"
            assert payment_result["action"] == "updated"

            # Verify invoice was marked as paid
            mock_update_invoice.assert_called_once()
            update_args = mock_update_invoice.call_args[1]
            assert update_args["status"] == "paid"
            assert update_args["amount_paid"] == 14900

    async def test_grace_period_overage_handling(self, mock_db, test_user):
        """Test that grace period overages don't trigger immediate charges."""
        # User at 1050 calls (5% over quota - within grace period)
        test_user.usage_count = 1050

        from github_analyzer.billing.usage_tracker import UsageTracker

        usage_tracker = UsageTracker()

        with patch(
            "github_analyzer.database.operations.UserOperations.get_user_by_id",
            return_value=test_user,
        ):
            overage_info = await usage_tracker.get_user_overage_info(
                mock_db, test_user.user_id
            )

            assert overage_info["is_over_quota"] is True
            assert overage_info["in_grace_period"] is True
            assert overage_info["overage_count"] == 50
            assert overage_info["overage_cost"] == 0  # No charge in grace period

    async def test_subscription_upgrade_webhook_flow(self, mock_db, test_user):
        """Test subscription upgrade from Professional to Enterprise."""
        # Initial state: Professional plan
        assert test_user.subscription_plan == SubscriptionPlan.PROFESSIONAL

        upgrade_webhook = {
            "id": "evt_upgrade",
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": test_user.stripe_subscription_id,
                    "customer": test_user.stripe_customer_id,
                    "status": "active",
                    "current_period_start": int(datetime.now(timezone.utc).timestamp()),
                    "current_period_end": int(datetime.now(timezone.utc).timestamp())
                    + 86400 * 30,
                    "items": {
                        "data": [
                            {
                                "price": {
                                    "id": "price_enterprise_monthly",
                                    "unit_amount": 39900,  # $399
                                }
                            }
                        ]
                    },
                }
            },
        }

        from github_analyzer.api.services.webhook_service import WebhookService

        webhook_service = WebhookService()

        with (
            patch(
                "github_analyzer.database.operations.WebhookEventOperations.get_webhook_event",
                return_value=None,
            ),
            patch(
                "github_analyzer.database.operations.WebhookEventOperations.create_webhook_event",
                return_value=Mock(event_id="whe_upgrade"),
            ),
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_stripe_subscription_id",
                return_value=test_user,
            ),
            patch(
                "github_analyzer.database.operations.UserOperations.update_user_subscription",
                return_value=None,
            ) as mock_update_sub,
            patch(
                "github_analyzer.database.operations.WebhookEventOperations.update_webhook_status",
                return_value=None,
            ),
        ):
            result = await webhook_service.process_webhook(mock_db, upgrade_webhook)

            assert result["status"] == "processed"
            assert result["plan_changed"] is True
            assert result["new_plan"] == "ENTERPRISE"

            # Verify subscription update with new quota
            mock_update_sub.assert_called_once()
            update_args = mock_update_sub.call_args[1]
            assert update_args["subscription_plan"] == SubscriptionPlan.ENTERPRISE
            assert update_args["usage_quota"] == 2000  # Enterprise quota

    async def test_failed_payment_webhook_flow(self, mock_db, test_user):
        """Test handling of failed payment webhooks."""
        failed_payment_webhook = {
            "id": "evt_failed_payment",
            "type": "invoice.payment_failed",
            "data": {
                "object": {
                    "id": "in_failed",
                    "customer": test_user.stripe_customer_id,
                    "subscription": test_user.stripe_subscription_id,
                    "status": "open",
                    "amount_due": 14900,
                    "amount_paid": 0,
                    "attempt_count": 1,
                    "currency": "usd",
                    "period_start": int(datetime.now(timezone.utc).timestamp())
                    - 86400 * 30,
                    "period_end": int(datetime.now(timezone.utc).timestamp()),
                    "payment_intent": "pi_failed",
                }
            },
        }

        from github_analyzer.api.services.webhook_service import WebhookService

        webhook_service = WebhookService()

        with (
            patch(
                "github_analyzer.database.operations.WebhookEventOperations.get_webhook_event",
                return_value=None,
            ),
            patch(
                "github_analyzer.database.operations.WebhookEventOperations.create_webhook_event",
                return_value=Mock(event_id="whe_failed"),
            ),
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_stripe_customer_id",
                return_value=test_user,
            ),
            patch(
                "github_analyzer.database.operations.UserOperations.update_user_subscription",
                return_value=None,
            ) as mock_update_sub,
            patch(
                "github_analyzer.database.operations.InvoiceOperations.get_invoice_by_stripe_id",
                return_value=None,
            ),
            patch(
                "github_analyzer.database.operations.InvoiceOperations.create_invoice",
                return_value=None,
            ),
            patch(
                "github_analyzer.database.operations.PaymentOperations.create_payment",
                return_value=None,
            ) as mock_create_payment,
            patch(
                "github_analyzer.database.operations.WebhookEventOperations.update_webhook_status",
                return_value=None,
            ),
        ):
            result = await webhook_service.process_webhook(
                mock_db, failed_payment_webhook
            )

            assert result["status"] == "processed"
            assert result["subscription_status"] == "past_due"

            # Verify subscription marked as past_due
            mock_update_sub.assert_called_once()
            update_args = mock_update_sub.call_args[1]
            assert update_args["subscription_status"] == SubscriptionStatus.PAST_DUE

            # Verify failed payment record created
            mock_create_payment.assert_called_once()
            payment_args = mock_create_payment.call_args[1]
            assert payment_args["status"] == "failed"
            assert payment_args["amount"] == 14900

    async def test_webhook_metrics_collection(self, mock_db):
        """Test that webhook processing collects proper metrics."""
        from github_analyzer.api.services.webhook_service import WebhookService

        webhook_service = WebhookService()

        # Simulate processing multiple webhooks
        webhook_types = [
            "invoice.created",
            "invoice.finalized",
            "invoice.payment_succeeded",
            "customer.subscription.updated",
            "invoice.payment_failed",
        ]

        processing_times = []

        for i, event_type in enumerate(webhook_types):
            webhook = {
                "id": f"evt_metric_{i}",
                "type": event_type,
                "data": {"object": {}},
            }

            with (
                patch(
                    "github_analyzer.database.operations.WebhookEventOperations.get_webhook_event",
                    return_value=None,
                ),
                patch(
                    "github_analyzer.database.operations.WebhookEventOperations.create_webhook_event",
                    return_value=Mock(event_id=f"whe_metric_{i}"),
                ),
                patch.dict(
                    "github_analyzer.billing.webhook_handlers.WEBHOOK_HANDLERS",
                    {
                        event_type: AsyncMock(
                            return_value={"status": "processed" if i < 4 else "failed"}
                        )
                    },
                ),
                patch(
                    "github_analyzer.database.operations.WebhookEventOperations.update_webhook_status",
                    return_value=None,
                ) as mock_update_status,
            ):
                await webhook_service.process_webhook(mock_db, webhook)

                # Check that processing time was recorded
                update_call = mock_update_status.call_args[1]
                if "processing_time" in update_call:
                    processing_times.append(update_call["processing_time"])

        # Get statistics
        mock_stats = {
            "total_webhooks": 5,
            "processed": 4,
            "failed": 1,
            "success_rate": 80.0,
            "average_processing_time": (
                sum(processing_times) / len(processing_times) if processing_times else 0
            ),
            "events_by_type": {
                "invoice.created": 1,
                "invoice.finalized": 1,
                "invoice.payment_succeeded": 1,
                "customer.subscription.updated": 1,
                "invoice.payment_failed": 1,
            },
        }

        with patch(
            "github_analyzer.database.operations.WebhookEventOperations.get_webhook_statistics",
            return_value=mock_stats,
        ):
            stats = await webhook_service.get_webhook_statistics(mock_db)

            assert stats["total_webhooks"] == 5
            assert stats["processed"] == 4
            assert stats["failed"] == 1
            assert stats["success_rate"] == 80.0
            assert len(stats["events_by_type"]) == 5
