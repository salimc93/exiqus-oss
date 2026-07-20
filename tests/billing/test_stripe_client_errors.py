"""
Test suite for Stripe client error handling.

Tests error scenarios and edge cases that could occur
in production with Stripe API interactions.
"""

from unittest.mock import MagicMock, patch

import pytest
import stripe.error
from stripe import StripeError

from github_analyzer.billing.stripe_client import StripeClient, StripeClientError


class TestStripeClientErrorHandling:
    """Test error handling in StripeClient."""

    @pytest.fixture
    def stripe_client(self):
        """Create a StripeClient instance with mocked configuration."""
        with patch.object(StripeClient, "_setup_stripe"):
            client = StripeClient()
            client.is_configured = True
            return client

    @pytest.fixture
    def unconfigured_client(self):
        """Create an unconfigured StripeClient instance."""
        with patch.object(StripeClient, "_setup_stripe"):
            client = StripeClient()
            client.is_configured = False
            return client

    async def test_create_customer_not_configured(self, unconfigured_client):
        """Test creating customer when Stripe is not configured."""
        with pytest.raises(StripeClientError) as exc_info:
            await unconfigured_client.create_customer("test@example.com", "Test User")
        assert "not configured" in str(exc_info.value)

    async def test_create_customer_authentication_error(self, stripe_client):
        """Test authentication error when creating customer."""
        with patch("stripe.Customer.create") as mock_create:
            mock_create.side_effect = stripe.error.AuthenticationError(
                "Invalid API key"
            )

            with pytest.raises(StripeClientError) as exc_info:
                await stripe_client.create_customer("test@example.com", "Test User")
            assert "Failed to create customer" in str(exc_info.value)

    async def test_create_subscription_card_error(self, stripe_client):
        """Test card error when creating subscription."""
        with patch("stripe.Subscription.create") as mock_create:
            mock_create.side_effect = stripe.error.CardError(
                "Your card was declined", "card_declined", "card_declined"
            )

            with pytest.raises(StripeClientError) as exc_info:
                await stripe_client.create_subscription("cus_123", "price_123")
            assert "Failed to create subscription" in str(exc_info.value)

    async def test_update_subscription_rate_limit_error(self, stripe_client):
        """Test rate limit error when updating subscription."""
        with patch("stripe.Subscription.retrieve") as mock_retrieve:
            with patch("stripe.Subscription.modify") as mock_modify:
                mock_retrieve.return_value = MagicMock()
                mock_modify.side_effect = stripe.error.RateLimitError(
                    "Too many requests"
                )

                with pytest.raises(StripeClientError) as exc_info:
                    await stripe_client.update_subscription(
                        "sub_123", items=[{"price": "price_456"}]
                    )
                assert "Failed to update subscription" in str(exc_info.value)

    async def test_cancel_subscription_api_connection_error(self, stripe_client):
        """Test API connection error when canceling subscription."""
        with patch("stripe.Subscription.delete") as mock_delete:
            mock_delete.side_effect = stripe.error.APIConnectionError("Network error")

            with pytest.raises(StripeClientError) as exc_info:
                await stripe_client.cancel_subscription("sub_123")
            assert "Failed to cancel subscription" in str(exc_info.value)

    async def test_create_usage_record_invalid_request(self, stripe_client):
        """Test invalid request error when creating usage record."""
        with patch("stripe.SubscriptionItem.retrieve") as mock_retrieve:
            mock_item = MagicMock()
            mock_item.create_usage_record.side_effect = (
                stripe.error.InvalidRequestError(
                    "Invalid subscription item", "subscription_item"
                )
            )
            mock_retrieve.return_value = mock_item

            with pytest.raises(StripeClientError) as exc_info:
                await stripe_client.create_usage_record("si_123", 100)
            assert "Failed to create usage record" in str(exc_info.value)

    async def test_list_subscription_items_generic_stripe_error(self, stripe_client):
        """Test generic Stripe error when listing subscription items."""
        with patch("stripe.SubscriptionItem.list") as mock_list:
            mock_list.side_effect = StripeError("Unknown error")

            with pytest.raises(StripeClientError) as exc_info:
                await stripe_client.list_subscription_items("sub_123")
            assert "Failed to list subscription items" in str(exc_info.value)

    async def test_add_metered_price_not_configured(self, unconfigured_client):
        """Test adding metered price when not configured."""
        with pytest.raises(StripeClientError) as exc_info:
            await unconfigured_client.add_metered_price_to_subscription(
                "sub_123", "price_123"
            )
        assert "not configured" in str(exc_info.value)

    async def test_create_metered_billing_prices_existing_products(self, stripe_client):
        """Test creating metered prices with existing products."""
        mock_product = MagicMock()
        mock_product.id = "prod_existing"

        # Mock existing metered prices
        mock_price_prof = MagicMock()
        mock_price_prof.id = "price_prof_existing"
        mock_price_prof.unit_amount = 20
        mock_price_prof.recurring = {"usage_type": "metered"}

        mock_price_ent = MagicMock()
        mock_price_ent.id = "price_ent_existing"
        mock_price_ent.unit_amount = 10
        mock_price_ent.recurring = {"usage_type": "metered"}

        with patch("stripe.Product.retrieve") as mock_retrieve:
            mock_retrieve.return_value = mock_product

            with patch("stripe.Price.list") as mock_list:
                # Return existing prices for both queries
                mock_list.side_effect = [
                    MagicMock(data=[mock_price_prof]),
                    MagicMock(data=[mock_price_ent]),
                ]

                with patch("stripe.Price.create") as mock_create:
                    result = await stripe_client.create_metered_billing_prices()

                    # Should use existing prices, not create new ones
                    assert mock_create.call_count == 0
                    assert result["professional"] == "price_prof_existing"
                    assert result["enterprise"] == "price_ent_existing"

    async def test_create_metered_billing_prices_product_creation_error(
        self, stripe_client
    ):
        """Test error when creating product for metered billing."""
        with patch("stripe.Product.retrieve") as mock_retrieve:
            mock_retrieve.side_effect = stripe.error.InvalidRequestError(
                "No such product", "id"
            )

            with patch("stripe.Product.create") as mock_create:
                mock_create.side_effect = StripeError("Failed to create product")

                with pytest.raises(StripeClientError) as exc_info:
                    await stripe_client.create_metered_billing_prices()
                assert "Failed to setup metered billing" in str(exc_info.value)

    async def test_get_subscription_item_for_price_error_handling(self, stripe_client):
        """Test error handling in get_subscription_item_for_price."""
        with patch.object(stripe_client, "list_subscription_items") as mock_list:
            mock_list.side_effect = StripeClientError("Failed to list items")

            result = await stripe_client.get_subscription_item_for_price(
                "sub_123", "price_123"
            )
            assert result is None

    async def test_create_payment_intent_not_configured(self, unconfigured_client):
        """Test creating payment intent when not configured."""
        with pytest.raises(StripeClientError) as exc_info:
            await unconfigured_client.create_payment_intent(1000, "usd", "cus_123")
        assert "not configured" in str(exc_info.value)

    async def test_confirm_payment_intent_error(self, stripe_client):
        """Test error when confirming payment intent."""
        with patch("stripe.PaymentIntent.confirm") as mock_confirm:
            mock_confirm.side_effect = stripe.error.CardError(
                "Card verification failed", "card_declined", "verification_failed"
            )

            with pytest.raises(StripeClientError) as exc_info:
                await stripe_client.confirm_payment_intent("pi_123")
            assert "Failed to confirm payment" in str(exc_info.value)

    async def test_create_checkout_session_insufficient_funds(self, stripe_client):
        """Test creating checkout session with insufficient funds error."""
        with patch("stripe.checkout.Session.create") as mock_create:
            mock_create.side_effect = stripe.error.CardError(
                "Insufficient funds", "card_declined", "insufficient_funds"
            )

            with pytest.raises(StripeClientError) as exc_info:
                await stripe_client.create_checkout_session(
                    "cus_123",
                    "price_123",
                    "http://example.com/success",
                    "http://example.com/cancel",
                )
            assert "Failed to create checkout session" in str(exc_info.value)

    async def test_get_customer_portal_url_error(self, stripe_client):
        """Test error when creating customer portal session."""
        with patch("stripe.billing_portal.Session.create") as mock_create:
            mock_create.side_effect = stripe.error.InvalidRequestError(
                "Customer not found", "customer"
            )

            with pytest.raises(StripeClientError) as exc_info:
                await stripe_client.get_customer_portal_url(
                    "cus_invalid", "http://example.com/return"
                )
            assert "Failed to create portal session" in str(exc_info.value)

    async def test_list_invoices_pagination_error(self, stripe_client):
        """Test error during invoice pagination."""
        with patch("stripe.Invoice.list") as mock_list:
            mock_list.side_effect = StripeError("Pagination error")

            with pytest.raises(StripeClientError) as exc_info:
                await stripe_client.list_invoices("cus_123", limit=10)
            assert "Failed to list invoices" in str(exc_info.value)

    async def test_update_customer_metadata_error(self, stripe_client):
        """Test error when updating customer metadata."""
        with patch("stripe.Customer.modify") as mock_modify:
            mock_modify.side_effect = stripe.error.RateLimitError("Rate limit exceeded")

            with pytest.raises(StripeClientError) as exc_info:
                await stripe_client.update_customer(
                    "cus_123", metadata={"key": "value"}
                )
            assert "Failed to update customer" in str(exc_info.value)

    async def test_construct_webhook_event_invalid_signature(self, stripe_client):
        """Test invalid webhook signature."""
        with patch("stripe.Webhook.construct_event") as mock_construct:
            mock_construct.side_effect = ValueError("Invalid signature")

            with pytest.raises(StripeClientError) as exc_info:
                await stripe_client.construct_webhook_event(
                    b"payload", "invalid_sig", "secret"
                )
            assert "Invalid webhook signature" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
