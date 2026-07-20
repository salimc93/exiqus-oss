"""
Tests for Stripe client functionality.

Tests Stripe API integration, customer management, subscription handling,
and webhook signature verification.
"""

from unittest.mock import Mock, patch

import pytest
import stripe
from stripe import StripeError

from github_analyzer.billing.stripe_client import (
    StripeClient,
    StripeClientError,
)


class TestStripeClient:
    """Test suite for StripeClient."""

    @pytest.fixture
    def stripe_client(self):
        """Create StripeClient instance for testing."""
        return StripeClient()

    @pytest.fixture
    def configured_stripe_client(self):
        """Create a properly configured StripeClient for testing."""
        with patch.object(StripeClient, "_setup_stripe"):
            client = StripeClient()
            # Since is_configured is an instance attribute, we patch it on the instance
            with patch.object(client, "is_configured", True):
                yield client

    @pytest.fixture
    def mock_stripe_customer(self):
        """Mock Stripe customer data."""
        from unittest.mock import Mock

        mock_customer = Mock()
        mock_customer.id = "cus_test123"
        mock_customer.email = "test@example.com"
        mock_customer.name = "Test User"
        mock_customer.metadata = {"exiqus_user_id": "usr_test123"}
        mock_customer.created = 1234567890
        mock_customer.to_dict.return_value = {
            "id": "cus_test123",
            "email": "test@example.com",
            "name": "Test User",
            "metadata": {"exiqus_user_id": "usr_test123"},
            "created": 1234567890,
        }
        return mock_customer

    @pytest.fixture
    def mock_stripe_subscription(self):
        """Mock Stripe subscription data."""
        from unittest.mock import Mock

        mock_subscription = Mock()
        mock_subscription.id = "sub_test123"
        mock_subscription.customer = "cus_test123"
        mock_subscription.status = "active"
        mock_subscription.current_period_start = 1234567890
        mock_subscription.current_period_end = 1234567890 + 86400 * 30
        mock_subscription.items = {
            "data": [
                {
                    "price": {
                        "id": "price_test123",
                        "unit_amount": 2000,
                        "currency": "usd",
                    }
                }
            ]
        }
        mock_subscription.to_dict.return_value = {
            "id": "sub_test123",
            "customer": "cus_test123",
            "status": "active",
            "current_period_start": 1234567890,
            "current_period_end": 1234567890 + 86400 * 30,
            "items": {
                "data": [
                    {
                        "price": {
                            "id": "price_test123",
                            "unit_amount": 2000,
                            "currency": "usd",
                        }
                    }
                ]
            },
        }
        return mock_subscription

    @pytest.fixture
    def mock_checkout_session(self):
        """Mock Stripe checkout session data."""
        mock_session = Mock()
        mock_session.id = "cs_test123"
        mock_session.url = "https://checkout.stripe.com/c/pay/cs_test123"
        mock_session.to_dict.return_value = {
            "id": "cs_test123",
            "url": "https://checkout.stripe.com/c/pay/cs_test123",
        }
        return mock_session

    async def test_create_customer_success(
        self, configured_stripe_client, mock_stripe_customer
    ):
        """Test successful customer creation."""
        with patch("stripe.Customer.create", return_value=mock_stripe_customer):
            result = await configured_stripe_client.create_customer(
                email="test@example.com", user_id="usr_test123", name="Test User"
            )

            assert result["id"] == "cus_test123"
            assert result["email"] == "test@example.com"
            assert result["metadata"]["exiqus_user_id"] == "usr_test123"

    async def test_create_customer_stripe_error(self, configured_stripe_client):
        """Test customer creation with Stripe error."""
        with patch("stripe.Customer.create", side_effect=StripeError("Test error")):
            with pytest.raises(StripeClientError) as exc_info:
                await configured_stripe_client.create_customer(
                    email="test@example.com", user_id="usr_test123"
                )

            assert "Failed to create customer" in str(exc_info.value)

    async def test_get_customer_success(
        self, configured_stripe_client, mock_stripe_customer
    ):
        """Test successful customer retrieval."""
        with patch("stripe.Customer.retrieve", return_value=mock_stripe_customer):
            # Override test environment check for this test
            with patch.object(
                configured_stripe_client, "_is_test_environment", return_value=False
            ):
                result = await configured_stripe_client.get_customer("cus_test123")

                assert result["id"] == "cus_test123"
                assert result["email"] == "test@example.com"

    async def test_get_customer_not_found(self, stripe_client):
        """Test customer retrieval when customer doesn't exist."""
        from stripe import InvalidRequestError

        with patch(
            "stripe.Customer.retrieve",
            side_effect=InvalidRequestError("No such customer", param=None),
        ):
            result = await stripe_client.get_customer("cus_nonexistent")

            assert result is None

    async def test_create_subscription_success(
        self, stripe_client, mock_stripe_subscription
    ):
        """Test successful subscription creation."""
        with patch("stripe.Subscription.create", return_value=mock_stripe_subscription):
            result = await stripe_client.create_subscription(
                customer_id="cus_test123", price_id="price_test123"
            )

            assert result["id"] == "sub_test123"
            assert result["customer"] == "cus_test123"
            assert result["status"] == "active"

    async def test_create_subscription_stripe_error(self, stripe_client):
        """Test subscription creation with Stripe error."""
        with patch("stripe.Subscription.create", side_effect=StripeError("Test error")):
            with pytest.raises(StripeClientError) as exc_info:
                await stripe_client.create_subscription(
                    customer_id="cus_test123", price_id="price_test123"
                )

            assert "Failed to create subscription" in str(exc_info.value)

    async def test_update_subscription_success(
        self, configured_stripe_client, mock_stripe_subscription
    ):
        """Test successful subscription update."""
        # Create a new mock with updated data
        updated_subscription = Mock()
        updated_subscription.id = "sub_test123"
        updated_subscription.customer = "cus_test123"
        updated_subscription.status = "active"
        updated_subscription.current_period_start = 1234567890
        updated_subscription.current_period_end = 1234567890 + 86400 * 30
        updated_subscription.items = {
            "data": [
                {
                    "price": {
                        "id": "price_new123",  # Updated price
                        "unit_amount": 2000,
                        "currency": "usd",
                    }
                }
            ]
        }
        updated_subscription.to_dict.return_value = {
            "id": "sub_test123",
            "customer": "cus_test123",
            "status": "active",
            "current_period_start": 1234567890,
            "current_period_end": 1234567890 + 86400 * 30,
            "items": {
                "data": [
                    {
                        "price": {
                            "id": "price_new123",
                            "unit_amount": 2000,
                            "currency": "usd",
                        }
                    }
                ]
            },
        }

        with patch(
            "stripe.Subscription.retrieve", return_value=mock_stripe_subscription
        ):
            with patch("stripe.Subscription.modify", return_value=updated_subscription):
                result = await configured_stripe_client.update_subscription(
                    subscription_id="sub_test123", price_id="price_new123"
                )

                assert result["id"] == "sub_test123"
                assert result["items"]["data"][0]["price"]["id"] == "price_new123"

    async def test_cancel_subscription_success(
        self, configured_stripe_client, mock_stripe_subscription
    ):
        """Test successful subscription cancellation."""
        # Create a new mock with canceled status
        cancelled_subscription = Mock()
        cancelled_subscription.id = "sub_test123"
        cancelled_subscription.customer = "cus_test123"
        cancelled_subscription.status = "canceled"
        cancelled_subscription.current_period_start = 1234567890
        cancelled_subscription.current_period_end = 1234567890 + 86400 * 30
        cancelled_subscription.items = mock_stripe_subscription.items
        cancelled_subscription.to_dict.return_value = {
            "id": "sub_test123",
            "customer": "cus_test123",
            "status": "canceled",
            "current_period_start": 1234567890,
            "current_period_end": 1234567890 + 86400 * 30,
            "items": mock_stripe_subscription.items,
        }

        with patch("stripe.Subscription.modify", return_value=cancelled_subscription):
            result = await configured_stripe_client.cancel_subscription(
                subscription_id="sub_test123", at_period_end=True
            )

            assert result["id"] == "sub_test123"
            assert result["status"] == "canceled"

    async def test_verify_webhook_signature_valid(self, stripe_client):
        """Test valid webhook signature verification."""
        payload = b'{"test": "data"}'
        signature = "valid_signature"
        webhook_secret = "whsec_test"

        mock_event = {"id": "evt_test123", "type": "test.event"}

        with patch("stripe.Webhook.construct_event", return_value=mock_event):
            result = stripe_client.verify_webhook_signature(
                payload, signature, webhook_secret
            )

            assert result["id"] == "evt_test123"
            assert result["type"] == "test.event"

    async def test_verify_webhook_signature_rejects_empty_secret(self, stripe_client):
        """An unconfigured webhook secret must fail closed, not verify.

        stripe.Webhook.construct_event will successfully verify a payload
        signed with an empty key, so a deployment missing
        STRIPE_WEBHOOK_SECRET would otherwise accept forged events.
        """
        payload = b'{"type": "customer.subscription.created"}'
        signature = "t=1,v1=anything"

        with patch("stripe.Webhook.construct_event") as construct:
            with pytest.raises(StripeClientError, match="not configured"):
                stripe_client.verify_webhook_signature(payload, signature, "")

            # Must reject before ever reaching Stripe's verification.
            construct.assert_not_called()

    async def test_verify_webhook_signature_invalid(self, stripe_client):
        """Test invalid webhook signature verification."""
        payload = b'{"test": "data"}'
        signature = "invalid_signature"
        webhook_secret = "whsec_test"

        with patch(
            "stripe.Webhook.construct_event",
            side_effect=stripe.error.SignatureVerificationError(
                "Invalid signature", None
            ),
        ):
            with pytest.raises(StripeClientError) as exc_info:
                stripe_client.verify_webhook_signature(
                    payload, signature, webhook_secret
                )

            assert "Invalid signature" in str(exc_info.value)

    async def test_create_checkout_session_success(
        self, configured_stripe_client, mock_checkout_session
    ):
        """Test successful checkout session creation."""
        with patch(
            "stripe.checkout.Session.create", return_value=mock_checkout_session
        ):
            result = await configured_stripe_client.create_checkout_session(
                customer_id="cus_test123",
                price_id="price_test123",
                success_url="https://example.com/success",
                cancel_url="https://example.com/cancel",
            )

            assert result["id"] == "cs_test123"
            assert result["url"] == "https://checkout.stripe.com/c/pay/cs_test123"

    async def test_create_checkout_session_stripe_error(self, configured_stripe_client):
        """Test checkout session creation with Stripe error."""
        with patch(
            "stripe.checkout.Session.create", side_effect=StripeError("Test error")
        ):
            with pytest.raises(StripeClientError) as exc_info:
                await configured_stripe_client.create_checkout_session(
                    customer_id="cus_test123",
                    price_id="price_test123",
                    success_url="https://example.com/success",
                    cancel_url="https://example.com/cancel",
                )

            assert "Failed to create checkout session" in str(exc_info.value)
