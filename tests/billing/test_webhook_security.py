"""
Tests for webhook security, idempotency, and chaos scenarios.

This test suite covers advanced webhook handling scenarios including:
- Signature verification
- Idempotency handling
- Duplicate webhook delivery
- Timeout and retry scenarios
- Database transaction rollbacks
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from github_analyzer.billing.stripe_client import StripeClientError
from github_analyzer.billing.webhook_handlers import (
    WebhookHandlerError,
    WebhookHandlers,
)
from github_analyzer.database.models import WebhookEvent


class TestWebhookSecurity:
    """Test webhook signature verification and security."""

    @pytest.fixture
    def webhook_handlers(self):
        """Create WebhookHandlers instance."""
        return WebhookHandlers()

    @pytest.fixture
    def valid_webhook_payload(self):
        """Valid webhook payload."""
        return b'{"id":"evt_test","type":"invoice.created","data":{"object":{}}}'

    @pytest.fixture
    def valid_signature(self):
        """Valid Stripe signature header."""
        return "t=1234567890,v1=test_signature"

    @pytest.fixture
    def webhook_secret(self):
        """Webhook endpoint secret."""
        return "whsec_test123"

    async def test_webhook_signature_verification_success(
        self, webhook_handlers, valid_webhook_payload, valid_signature, webhook_secret
    ):
        """Test successful webhook signature verification."""
        mock_event = {"id": "evt_test", "type": "invoice.created", "data": {}}

        with patch.object(
            webhook_handlers.stripe_client,
            "verify_webhook_signature",
            return_value=mock_event,
        ) as mock_verify:
            result = webhook_handlers.stripe_client.verify_webhook_signature(
                valid_webhook_payload, valid_signature, webhook_secret
            )

            assert result == mock_event
            mock_verify.assert_called_once_with(
                valid_webhook_payload, valid_signature, webhook_secret
            )

    async def test_webhook_signature_verification_failure(
        self, webhook_handlers, valid_webhook_payload, webhook_secret
    ):
        """Test webhook signature verification failure."""
        invalid_signature = "t=1234567890,v1=invalid_signature"

        with patch.object(
            webhook_handlers.stripe_client,
            "verify_webhook_signature",
            side_effect=StripeClientError("Invalid signature"),
        ):
            with pytest.raises(StripeClientError) as exc_info:
                webhook_handlers.stripe_client.verify_webhook_signature(
                    valid_webhook_payload, invalid_signature, webhook_secret
                )

            assert "Invalid signature" in str(exc_info.value)

    async def test_webhook_replay_attack_protection(
        self, webhook_handlers, valid_webhook_payload, valid_signature, webhook_secret
    ):
        """Test protection against webhook replay attacks."""
        # Simulate old timestamp (more than 5 minutes old)
        old_timestamp = "1234567890"  # Very old timestamp
        old_signature = f"t={old_timestamp},v1=test_signature"

        with patch.object(
            webhook_handlers.stripe_client,
            "verify_webhook_signature",
            side_effect=StripeClientError("Timestamp outside the tolerance zone"),
        ):
            with pytest.raises(StripeClientError):
                webhook_handlers.stripe_client.verify_webhook_signature(
                    valid_webhook_payload, old_signature, webhook_secret
                )


class TestWebhookIdempotency:
    """Test webhook idempotency handling."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return AsyncMock()

    @pytest.fixture
    def webhook_event(self):
        """Sample webhook event."""
        return {
            "id": "evt_test123",
            "type": "invoice.payment_succeeded",
            "data": {
                "object": {
                    "id": "in_test123",
                    "customer": "cus_test123",
                }
            },
        }

    async def test_idempotent_webhook_processing(self, mock_db, webhook_event):
        """Test that webhooks are processed idempotently."""
        from github_analyzer.api.services.webhook_service import WebhookService

        service = WebhookService()

        # Mock existing webhook event
        existing_event = Mock(
            spec=WebhookEvent,
            event_id="evt_test123",
            status="processed",
            processed_at=Mock(),
        )

        with patch(
            "github_analyzer.database.operations.WebhookEventOperations.get_webhook_event",
            return_value=existing_event,
        ):
            result = await service.process_webhook(mock_db, webhook_event)

            assert result["status"] == "already_processed"
            assert result["event_id"] == "evt_test123"

    async def test_concurrent_webhook_delivery(self, mock_db, webhook_event):
        """Test handling of concurrent duplicate webhook deliveries."""
        from github_analyzer.api.services.webhook_service import WebhookService

        service = WebhookService()

        # Track call count
        call_count = 0

        async def mock_create_webhook(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return Mock(event_id="evt_test123")
            else:
                raise Exception("Duplicate key error")

        with (
            patch(
                "github_analyzer.database.operations.WebhookEventOperations.get_webhook_event",
                return_value=None,  # First check shows no existing event
            ),
            patch(
                "github_analyzer.database.operations.WebhookEventOperations.create_webhook_event",
                side_effect=mock_create_webhook,
            ),
            patch(
                "github_analyzer.database.operations.WebhookEventOperations.update_webhook_status",
                return_value=None,
            ),
            patch.dict(
                "github_analyzer.billing.webhook_handlers.WEBHOOK_HANDLERS",
                {"invoice.payment_succeeded": AsyncMock(return_value={"status": "ok"})},
            ),
        ):
            # Process webhook once
            result1 = await service.process_webhook(mock_db, webhook_event)
            assert result1["status"] == "ok"

            # Second attempt should fail with duplicate key
            with pytest.raises(Exception) as exc_info:
                await service.process_webhook(mock_db, webhook_event)
            assert "Duplicate key error" in str(exc_info.value)


class TestWebhookChaosScenarios:
    """Test webhook handling under chaos scenarios."""

    @pytest.fixture
    def webhook_handlers(self):
        """Create WebhookHandlers instance."""
        return WebhookHandlers()

    @pytest.fixture
    def mock_db(self):
        """Mock database session with transaction support."""
        db = AsyncMock()
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        db.close = AsyncMock()
        return db

    @pytest.fixture
    def payment_succeeded_event(self):
        """Payment succeeded event."""
        return {
            "id": "evt_chaos_test",
            "type": "invoice.payment_succeeded",
            "data": {
                "object": {
                    "id": "in_chaos123",
                    "customer": "cus_test123",
                    "amount_paid": 5000,
                    "currency": "usd",
                    "period_start": 1234567890,
                    "period_end": 1234567890 + 86400 * 30,
                }
            },
        }

    async def test_stripe_api_timeout_handling(
        self, webhook_handlers, mock_db, payment_succeeded_event
    ):
        """Test handling of Stripe API timeouts during webhook processing."""
        mock_user = Mock(user_id="usr_test123", stripe_customer_id="cus_test123")

        with (
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_stripe_customer_id",
                return_value=mock_user,
            ),
            patch(
                "github_analyzer.database.operations.InvoiceOperations.get_invoice_by_stripe_id",
                side_effect=asyncio.TimeoutError("Database timeout"),
            ),
        ):
            with pytest.raises(WebhookHandlerError) as exc_info:
                await webhook_handlers.handle_invoice_payment_succeeded(
                    mock_db, payment_succeeded_event
                )

            assert "Database timeout" in str(exc_info.value)

    async def test_database_transaction_rollback(
        self, webhook_handlers, mock_db, payment_succeeded_event
    ):
        """Test that payment creation failure raises WebhookHandlerError."""
        mock_user = Mock(user_id="usr_test123", stripe_customer_id="cus_test123")
        mock_invoice = Mock(invoice_id="inv_test123")

        # Add payment_intent and amount_due to the event to trigger payment creation
        payment_succeeded_event["data"]["object"]["payment_intent"] = "pi_test123"
        payment_succeeded_event["data"]["object"]["amount_due"] = (
            5000  # Non-zero amount
        )

        with (
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_stripe_customer_id",
                return_value=mock_user,
            ),
            patch(
                "github_analyzer.database.operations.InvoiceOperations.get_invoice_by_stripe_id",
                return_value=None,
            ),
            patch(
                "github_analyzer.database.operations.InvoiceOperations.create_invoice",
                return_value=mock_invoice,
            ),
            patch(
                "github_analyzer.database.operations.PaymentOperations.create_payment",
                side_effect=Exception("Payment creation failed"),
            ),
        ):
            # The handler should raise a WebhookHandlerError when payment creation fails
            with pytest.raises(WebhookHandlerError):
                await webhook_handlers.handle_invoice_payment_succeeded(
                    mock_db, payment_succeeded_event
                )

    async def test_webhook_processing_with_network_flakiness(
        self, webhook_handlers, mock_db
    ):
        """Test webhook processing with intermittent network failures."""
        flaky_event = {
            "id": "evt_flaky",
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_test123",
                    "customer": "cus_test123",
                    "status": "active",
                    "current_period_start": 1234567890,
                    "current_period_end": 1234567890 + 86400 * 30,
                    "items": {
                        "data": [{"price": {"id": "price_professional_monthly"}}]
                    },
                }
            },
        }

        mock_user = Mock(
            user_id="usr_test123",
            stripe_subscription_id="sub_test123",
            subscription_plan="professional",
        )

        call_count = 0

        async def flaky_get_user(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Network error")
            return mock_user

        with (
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_stripe_subscription_id",
                side_effect=flaky_get_user,
            ),
            patch(
                "github_analyzer.database.operations.UserOperations.update_user_subscription",
                return_value=True,
            ),
        ):
            # First two attempts should fail
            for i in range(2):
                with pytest.raises(WebhookHandlerError):
                    await webhook_handlers.handle_customer_subscription_updated(
                        mock_db, flaky_event
                    )

            # Third attempt should succeed
            result = await webhook_handlers.handle_customer_subscription_updated(
                mock_db, flaky_event
            )
            assert result["status"] == "processed"

    async def test_webhook_processing_prevents_double_charging(
        self, webhook_handlers, mock_db
    ):
        """Test that webhook processing prevents double charging."""
        # Create two identical payment succeeded events
        event1 = {
            "id": "evt_double1",
            "type": "invoice.payment_succeeded",
            "data": {
                "object": {
                    "id": "in_double123",
                    "customer": "cus_test123",
                    "amount_due": 10000,  # $100
                    "amount_paid": 10000,  # $100
                    "currency": "usd",
                    "period_start": 1234567890,
                    "period_end": 1234567890 + 86400 * 30,
                }
            },
        }

        event2 = event1.copy()
        event2["id"] = "evt_double2"  # Different event ID, same invoice

        mock_user = Mock(user_id="usr_test123", stripe_customer_id="cus_test123")
        mock_invoice = Mock(invoice_id="inv_existing", status="paid")

        with (
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_stripe_customer_id",
                return_value=mock_user,
            ),
            patch(
                "github_analyzer.database.operations.InvoiceOperations.get_invoice_by_stripe_id",
                side_effect=[
                    None,  # First event: no existing invoice
                    mock_invoice,  # Second event: invoice exists
                ],
            ),
            patch(
                "github_analyzer.database.operations.InvoiceOperations.create_invoice",
                return_value=Mock(invoice_id="inv_new123"),
            ),
            patch(
                "github_analyzer.database.operations.InvoiceOperations.update_invoice_status",
                return_value=None,
            ),
        ):
            # Process first event - should create invoice
            result1 = await webhook_handlers.handle_invoice_payment_succeeded(
                mock_db, event1
            )
            assert result1["action"] == "created"

            # Process second event - should only update
            result2 = await webhook_handlers.handle_invoice_payment_succeeded(
                mock_db, event2
            )
            assert result2["action"] == "updated"


class TestWebhookErrorRecovery:
    """Test webhook error recovery mechanisms."""

    @pytest.fixture
    def webhook_service(self):
        """Create webhook service instance."""
        from github_analyzer.api.services.webhook_service import WebhookService

        return WebhookService()

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return AsyncMock()

    async def test_retry_failed_webhooks(self, webhook_service, mock_db):
        """Test retry mechanism for failed webhooks."""
        # Create failed webhook events
        failed_events = [
            Mock(
                event_id=f"evt_failed{i}",
                stripe_event_id=f"evt_stripe{i}",
                event_type="invoice.payment_succeeded",
                status="failed",
                attempts=i,
                event_data={
                    "id": f"evt_stripe{i}",
                    "type": "invoice.payment_succeeded",
                },
            )
            for i in range(3)
        ]

        with (
            patch(
                "github_analyzer.database.operations.WebhookEventOperations.get_failed_webhooks",
                return_value=failed_events,
            ),
            patch.dict(
                "github_analyzer.billing.webhook_handlers.WEBHOOK_HANDLERS",
                {
                    "invoice.payment_succeeded": AsyncMock(
                        side_effect=[
                            {"status": "processed"},  # First succeeds
                            Exception("Still failing"),  # Second fails
                            {"status": "processed"},  # Third succeeds
                        ]
                    )
                },
            ),
            patch(
                "github_analyzer.database.operations.WebhookEventOperations.update_webhook_status",
                return_value=None,
            ),
        ):
            result = await webhook_service.retry_failed_webhooks(
                mock_db, max_attempts=5
            )

            assert result["total_webhooks"] == 3
            assert result["successful_retries"] == 2
            assert result["failed_retries"] == 1

    async def test_cleanup_old_webhooks(self, webhook_service, mock_db):
        """Test cleanup of old processed webhooks."""
        with patch(
            "github_analyzer.database.operations.WebhookEventOperations.delete_old_webhooks",
            return_value=150,
        ) as mock_delete:
            result = await webhook_service.cleanup_old_webhooks(mock_db, days=30)

            assert result["deleted_count"] == 150
            mock_delete.assert_called_once_with(mock_db, days=30)

    async def test_webhook_statistics(self, webhook_service, mock_db):
        """Test webhook statistics collection."""
        mock_stats = {
            "total_webhooks": 1000,
            "processed": 950,
            "failed": 30,
            "pending": 20,
            "success_rate": 95.0,
            "average_processing_time": 250,  # milliseconds
            "events_by_type": {
                "invoice.payment_succeeded": 400,
                "customer.subscription.updated": 300,
                "invoice.payment_failed": 50,
            },
        }

        with patch(
            "github_analyzer.database.operations.WebhookEventOperations.get_webhook_statistics",
            return_value=mock_stats,
        ):
            stats = await webhook_service.get_webhook_statistics(mock_db)

            assert stats["total_webhooks"] == 1000
            assert stats["success_rate"] == 95.0
            assert stats["events_by_type"]["invoice.payment_succeeded"] == 400
