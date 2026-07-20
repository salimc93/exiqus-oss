"""
Tests for webhook handler functionality.

Tests Stripe webhook event processing, idempotency, error handling,
and database updates for subscription lifecycle events.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from github_analyzer.billing.webhook_handlers import (
    WEBHOOK_HANDLERS,
    WebhookHandlerError,
    WebhookHandlers,
)
from github_analyzer.database.models import (
    SubscriptionPlan,
    SubscriptionStatus,
    User,
)


class TestWebhookHandlers:
    """Test suite for WebhookHandlers."""

    @pytest.fixture
    def webhook_handlers(self):
        """Create WebhookHandlers instance for testing."""
        return WebhookHandlers()

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        """Mock user for testing."""
        return Mock(
            spec=User,
            **{
                "user_id": "usr_test123",
                "email": "test@example.com",
                "stripe_customer_id": "cus_test123",
                "subscription_plan": SubscriptionPlan.FREE,
                "subscription_status": SubscriptionStatus.ACTIVE,
            },
        )

    @pytest.fixture
    def subscription_created_event(self):
        """Mock subscription created event."""
        return {
            "id": "evt_test123",
            "type": "customer.subscription.created",
            "data": {
                "object": {
                    "id": "sub_test123",
                    "customer": "cus_test123",
                    "status": "active",
                    "current_period_start": 1234567890,
                    "current_period_end": 1234567890 + 86400 * 30,
                    "items": {
                        "data": [
                            {
                                "price": {
                                    "id": "price_basic_monthly",
                                    "unit_amount": 2000,
                                }
                            }
                        ]
                    },
                    "metadata": {"exiqus_user_id": "usr_test123"},
                }
            },
            "created": 1234567890,
        }

    @pytest.fixture
    def subscription_updated_event(self):
        """Mock subscription updated event."""
        return {
            "id": "evt_test124",
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_test123",
                    "customer": "cus_test123",
                    "status": "active",
                    "current_period_start": 1234567890,
                    "current_period_end": 1234567890 + 86400 * 30,
                    "items": {
                        "data": [
                            {
                                "price": {
                                    "id": "price_professional_monthly",
                                    "unit_amount": 5000,
                                }
                            }
                        ]
                    },
                    "metadata": {"exiqus_user_id": "usr_test123"},
                }
            },
            "created": 1234567890,
        }

    @pytest.fixture
    def subscription_deleted_event(self):
        """Mock subscription deleted event."""
        return {
            "id": "evt_test125",
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "id": "sub_test123",
                    "customer": "cus_test123",
                    "status": "canceled",
                    "metadata": {"exiqus_user_id": "usr_test123"},
                }
            },
            "created": 1234567890,
        }

    @pytest.fixture
    def invoice_payment_succeeded_event(self):
        """Mock invoice payment succeeded event."""
        return {
            "id": "evt_test126",
            "type": "invoice.payment_succeeded",
            "data": {
                "object": {
                    "id": "in_test123",
                    "customer": "cus_test123",
                    "subscription": "sub_test123",
                    "status": "paid",
                    "amount_due": 2000,
                    "amount_paid": 2000,
                    "currency": "usd",
                    "period_start": 1234567890,
                    "period_end": 1234567890 + 86400 * 30,
                }
            },
            "created": 1234567890,
        }

    async def test_handle_customer_subscription_created_success(
        self, webhook_handlers, mock_db, mock_user, subscription_created_event
    ):
        """Test successful subscription creation webhook handling."""
        with (
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_stripe_customer_id",
                return_value=mock_user,
            ),
            patch(
                "github_analyzer.database.operations.UserOperations.update_user_subscription",
                return_value=True,
            ),
            patch(
                "github_analyzer.database.operations.WebhookEventOperations.create_webhook_event",
                return_value=None,
            ),
        ):
            result = await webhook_handlers.handle_customer_subscription_created(
                mock_db, subscription_created_event
            )

            assert result["status"] == "processed"
            assert result["user_id"] == "usr_test123"
            assert result["subscription_id"] == "sub_test123"
            assert result["plan"] == "BASIC"

    async def test_handle_customer_subscription_created_user_not_found(
        self, webhook_handlers, mock_db, subscription_created_event
    ):
        """Test subscription creation webhook with user not found."""
        with (
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_stripe_customer_id",
                return_value=None,
            ),
            patch(
                "github_analyzer.database.operations.WebhookEventOperations.create_webhook_event",
                return_value=None,
            ),
        ):
            result = await webhook_handlers.handle_customer_subscription_created(
                mock_db, subscription_created_event
            )

            assert result["status"] == "ignored"
            assert result["reason"] == "User not found"

    async def test_handle_customer_subscription_updated_success(
        self, webhook_handlers, mock_db, mock_user, subscription_updated_event
    ):
        """Test successful subscription update webhook handling."""
        with (
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_stripe_subscription_id",
                return_value=mock_user,
            ),
            patch(
                "github_analyzer.database.operations.UserOperations.update_user_subscription",
                return_value=True,
            ),
            patch(
                "github_analyzer.database.operations.WebhookEventOperations.create_webhook_event",
                return_value=None,
            ),
        ):
            result = await webhook_handlers.handle_customer_subscription_updated(
                mock_db, subscription_updated_event
            )

            assert result["status"] == "processed"
            assert result["user_id"] == "usr_test123"
            assert result["subscription_id"] == "sub_test123"
            assert result["plan_changed"] is True
            assert result["new_plan"] == "PROFESSIONAL"

    async def test_handle_customer_subscription_deleted_success(
        self, webhook_handlers, mock_db, mock_user, subscription_deleted_event
    ):
        """Test successful subscription deletion webhook handling."""
        with (
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_stripe_subscription_id",
                return_value=mock_user,
            ),
            patch(
                "github_analyzer.database.operations.UserOperations.update_user_subscription",
                return_value=True,
            ),
            patch(
                "github_analyzer.database.operations.WebhookEventOperations.create_webhook_event",
                return_value=None,
            ),
        ):
            result = await webhook_handlers.handle_customer_subscription_deleted(
                mock_db, subscription_deleted_event
            )

            assert result["status"] == "processed"
            assert result["user_id"] == "usr_test123"
            assert result["subscription_id"] == "sub_test123"
            assert result["downgraded_to"] == "free"

    async def test_handle_invoice_payment_succeeded_success(
        self, webhook_handlers, mock_db, mock_user, invoice_payment_succeeded_event
    ):
        """Test successful invoice payment webhook handling."""
        # Mock invoice object
        mock_invoice = Mock()
        mock_invoice.invoice_id = "inv_20250704_123456_usr_test"

        # Mock subscription data
        mock_subscription = {
            "id": "sub_test123",
            "status": "active",
            "items": {
                "data": [
                    {
                        "price": {
                            "id": "price_1S7dsPRvLpeUOuiGCl9THAS9"  # Professional plan
                        }
                    }
                ]
            },
        }

        with (
            patch(
                "github_analyzer.database.operations.InvoiceOperations.get_invoice_by_stripe_id",
                return_value=None,  # No existing invoice
            ),
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_stripe_customer_id",
                return_value=mock_user,
            ),
            patch(
                "github_analyzer.database.operations.InvoiceOperations.create_invoice",
                return_value=mock_invoice,
            ),
            patch(
                "github_analyzer.database.operations.PaymentOperations.create_payment",
                return_value=None,
            ),
            patch(
                "github_analyzer.database.operations.WebhookEventOperations.create_webhook_event",
                return_value=None,
            ),
            patch(
                "github_analyzer.database.operations.UserOperations.update_user_subscription",
                return_value=None,
            ),
            patch.object(
                webhook_handlers.stripe_client,
                "get_subscription",
                return_value=mock_subscription,
            ),
        ):
            result = await webhook_handlers.handle_invoice_payment_succeeded(
                mock_db, invoice_payment_succeeded_event
            )

            assert result["status"] == "processed"
            assert result["action"] == "created"
            assert result["invoice_id"] == "inv_20250704_123456_usr_test"
            assert result["user_id"] == "usr_test123"

    @pytest.fixture
    def invoice_created_event(self):
        """Mock invoice created event."""
        return {
            "id": "evt_test128",
            "type": "invoice.created",
            "data": {
                "object": {
                    "id": "in_test125",
                    "customer": "cus_test123",
                    "subscription": "sub_test123",
                    "status": "draft",
                    "amount_due": 2000,
                    "currency": "usd",
                    "period_start": 1234567890,
                    "period_end": 1234567890 + 86400 * 30,
                    "lines": {
                        "data": [
                            {
                                "amount": 2000,
                                "description": "Professional Plan",
                                "price": {
                                    "id": "price_professional_monthly",
                                    "recurring": {"usage_type": "licensed"},
                                },
                            }
                        ]
                    },
                }
            },
            "created": 1234567890,
        }

    @pytest.fixture
    def invoice_finalized_event_with_overage(self):
        """Mock invoice finalized event with overage charges."""
        return {
            "id": "evt_test129",
            "type": "invoice.finalized",
            "data": {
                "object": {
                    "id": "in_test126",
                    "customer": "cus_test123",
                    "subscription": "sub_test123",
                    "status": "open",
                    "amount_due": 3000,  # $30 = $20 base + $10 overage
                    "currency": "usd",
                    "period_start": 1234567890,
                    "period_end": 1234567890 + 86400 * 30,
                    "lines": {
                        "data": [
                            {
                                "amount": 2000,
                                "description": "Professional Plan",
                                "price": {
                                    "id": "price_professional_monthly",
                                    "recurring": {"usage_type": "licensed"},
                                },
                            },
                            {
                                "amount": 1000,  # $10 overage
                                "quantity": 50,  # 50 overage calls
                                "description": "API Usage Overage",
                                "price": {
                                    "id": "price_professional_overage",
                                    "unit_amount": 20,  # $0.20 per call
                                    "recurring": {"usage_type": "metered"},
                                },
                            },
                        ]
                    },
                    "hosted_invoice_url": "https://invoice.stripe.com/i/test",
                }
            },
            "created": 1234567890,
        }

    async def test_handle_invoice_created_success(
        self, webhook_handlers, mock_db, mock_user, invoice_created_event
    ):
        """Test successful invoice created webhook handling."""
        with (
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_stripe_customer_id",
                return_value=mock_user,
            ),
            patch(
                "github_analyzer.database.operations.InvoiceOperations.get_invoice_by_stripe_id",
                return_value=None,  # No existing invoice
            ),
            patch(
                "github_analyzer.database.operations.InvoiceOperations.create_invoice",
                return_value=Mock(invoice_id="inv_20250704_123456_usr_test"),
            ),
        ):
            result = await webhook_handlers.handle_invoice_created(
                mock_db, invoice_created_event
            )

            assert result["status"] == "processed"
            assert result["action"] == "created"
            assert result["invoice_id"] == "inv_20250704_123456_usr_test"
            assert result["user_id"] == "usr_test123"

    async def test_handle_invoice_created_already_exists(
        self, webhook_handlers, mock_db, mock_user, invoice_created_event
    ):
        """Test invoice created webhook when invoice already exists."""
        existing_invoice = Mock(invoice_id="inv_existing")

        with (
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_stripe_customer_id",
                return_value=mock_user,
            ),
            patch(
                "github_analyzer.database.operations.InvoiceOperations.get_invoice_by_stripe_id",
                return_value=existing_invoice,
            ),
        ):
            result = await webhook_handlers.handle_invoice_created(
                mock_db, invoice_created_event
            )

            assert result["status"] == "processed"
            assert result["action"] == "already_exists"
            assert result["invoice_id"] == "inv_existing"

    async def test_handle_invoice_finalized_with_overage(
        self, webhook_handlers, mock_db, mock_user, invoice_finalized_event_with_overage
    ):
        """Test invoice finalized webhook with overage charges."""
        with (
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_stripe_customer_id",
                return_value=mock_user,
            ),
            patch(
                "github_analyzer.database.operations.InvoiceOperations.get_invoice_by_stripe_id",
                return_value=None,  # No existing invoice
            ),
            patch(
                "github_analyzer.database.operations.InvoiceOperations.create_invoice",
                return_value=Mock(invoice_id="inv_20250704_123456_usr_test"),
            ),
        ):
            result = await webhook_handlers.handle_invoice_finalized(
                mock_db, invoice_finalized_event_with_overage
            )

            assert result["status"] == "processed"
            assert result["action"] == "created"
            assert result["invoice_id"] == "inv_20250704_123456_usr_test"
            assert result["user_id"] == "usr_test123"
            assert result["has_overage"] is True
            assert result["overage_amount"] == 1000  # $10 in cents

    async def test_handle_invoice_finalized_update_existing(
        self, webhook_handlers, mock_db, mock_user, invoice_finalized_event_with_overage
    ):
        """Test invoice finalized webhook updating existing invoice."""
        existing_invoice = Mock(invoice_id="inv_existing", status="draft")

        with (
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_stripe_customer_id",
                return_value=mock_user,
            ),
            patch(
                "github_analyzer.database.operations.InvoiceOperations.get_invoice_by_stripe_id",
                return_value=existing_invoice,
            ),
            patch(
                "github_analyzer.database.operations.InvoiceOperations.update_invoice_status",
                return_value=None,
            ),
        ):
            result = await webhook_handlers.handle_invoice_finalized(
                mock_db, invoice_finalized_event_with_overage
            )

            assert result["status"] == "processed"
            assert result["action"] == "updated"
            assert result["invoice_id"] == "inv_existing"
            assert result["has_overage"] is True
            assert result["overage_amount"] == 1000

    async def test_handle_invoice_payment_failed_success(
        self, webhook_handlers, mock_db, mock_user
    ):
        """Test invoice payment failed webhook handling."""
        payment_failed_event = {
            "id": "evt_test127",
            "type": "invoice.payment_failed",
            "data": {
                "object": {
                    "id": "in_test124",
                    "customer": "cus_test123",
                    "subscription": "sub_test123",
                    "status": "open",
                    "amount_due": 2000,
                    "amount_paid": 0,
                    "currency": "usd",
                    "attempt_count": 1,
                    "period_start": 1234567890,
                    "period_end": 1234567890 + 86400 * 30,
                }
            },
            "created": 1234567890,
        }

        with (
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_stripe_customer_id",
                return_value=mock_user,
            ),
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_id",
                return_value=mock_user,
            ),
            patch(
                "github_analyzer.database.operations.UserOperations.update_user_subscription",
                return_value=True,
            ),
            patch(
                "github_analyzer.database.operations.InvoiceOperations.get_invoice_by_stripe_id",
                return_value=None,  # No existing invoice
            ),
            patch(
                "github_analyzer.database.operations.InvoiceOperations.create_invoice",
                return_value=None,
            ),
            patch(
                "github_analyzer.database.operations.PaymentOperations.create_payment",
                return_value=None,
            ),
            patch(
                "github_analyzer.database.operations.WebhookEventOperations.create_webhook_event",
                return_value=None,
            ),
        ):
            result = await webhook_handlers.handle_invoice_payment_failed(
                mock_db, payment_failed_event
            )

            assert result["status"] == "processed"
            assert result["user_id"] == "usr_test123"
            assert result["subscription_status"] == "past_due"

    async def test_price_id_to_plan_mapping(self, webhook_handlers):
        """Test price ID to subscription plan mapping."""
        # Test known mappings
        assert (
            webhook_handlers._map_price_to_plan("price_basic_monthly")
            == SubscriptionPlan.BASIC
        )
        assert (
            webhook_handlers._map_price_to_plan("price_professional_monthly")
            == SubscriptionPlan.PROFESSIONAL
        )
        assert (
            webhook_handlers._map_price_to_plan("price_enterprise_monthly")
            == SubscriptionPlan.ENTERPRISE
        )

        # Test unknown price ID
        assert webhook_handlers._map_price_to_plan("price_unknown") is None

    def test_webhook_handlers_registry(self):
        """Test that all expected webhook handlers are registered."""
        expected_events = [
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
            "invoice.created",
            "invoice.finalized",
            "invoice.payment_succeeded",
            "invoice.payment_failed",
        ]

        for event_type in expected_events:
            assert event_type in WEBHOOK_HANDLERS
            assert callable(WEBHOOK_HANDLERS[event_type])

    async def test_webhook_error_handling(
        self, webhook_handlers, mock_db, subscription_created_event
    ):
        """Test webhook error handling and logging."""
        with (
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_stripe_customer_id",
                side_effect=Exception("Database error"),
            ),
            patch(
                "github_analyzer.database.operations.WebhookEventOperations.create_webhook_event",
                return_value=None,
            ),
        ):
            with pytest.raises(WebhookHandlerError) as exc_info:
                await webhook_handlers.handle_customer_subscription_created(
                    mock_db, subscription_created_event
                )

            assert "Database error" in str(exc_info.value)
