"""
Test suite for Stripe metered billing functionality.

Tests the creation of usage records, subscription item management,
and metered price configuration.
"""

from unittest.mock import MagicMock, patch

import pytest
from stripe.error import InvalidRequestError, StripeError

from github_analyzer.billing.stripe_client import StripeClient, StripeClientError


class TestStripeMeteredBilling:
    """Test Stripe metered billing functionality."""

    @pytest.fixture
    def stripe_client(self):
        """Create a StripeClient instance with mocked configuration."""
        with patch.object(StripeClient, "_setup_stripe"):
            client = StripeClient()
            client.is_configured = True
            return client

    @pytest.fixture
    def mock_subscription_item(self):
        """Create a mock subscription item."""
        mock_item = MagicMock()
        mock_item.to_dict.return_value = {
            "id": "si_test123",
            "price": {"id": "price_professional_overage"},
            "subscription": "sub_test123",
        }
        return mock_item

    @pytest.fixture
    def mock_usage_record(self):
        """Create a mock usage record."""
        mock_record = MagicMock()
        mock_record.to_dict.return_value = {
            "id": "mbur_test123",
            "quantity": 100,
            "subscription_item": "si_test123",
            "timestamp": 1234567890,
        }
        return mock_record

    async def test_create_usage_record_success(self, stripe_client, mock_usage_record):
        """Test successful creation of a usage record."""
        with patch("stripe.SubscriptionItem.retrieve") as mock_retrieve:
            mock_item = MagicMock()
            mock_item.create_usage_record.return_value = mock_usage_record
            mock_retrieve.return_value = mock_item

            result = await stripe_client.create_usage_record(
                subscription_item_id="si_test123", quantity=100
            )

            assert result["id"] == "mbur_test123"
            assert result["quantity"] == 100
            mock_retrieve.assert_called_once_with("si_test123")
            mock_item.create_usage_record.assert_called_once_with(
                quantity=100, action="increment"
            )

    async def test_create_usage_record_with_timestamp(
        self, stripe_client, mock_usage_record
    ):
        """Test creating a usage record with custom timestamp."""
        with patch("stripe.SubscriptionItem.retrieve") as mock_retrieve:
            mock_item = MagicMock()
            mock_item.create_usage_record.return_value = mock_usage_record
            mock_retrieve.return_value = mock_item
            timestamp = 1234567890

            await stripe_client.create_usage_record(
                subscription_item_id="si_test123",
                quantity=50,
                timestamp=timestamp,
                action="set",
            )

            mock_retrieve.assert_called_once_with("si_test123")
            mock_item.create_usage_record.assert_called_once_with(
                quantity=50, action="set", timestamp=timestamp
            )

    async def test_create_usage_record_not_configured(self, stripe_client):
        """Test usage record creation when Stripe is not configured."""
        stripe_client.is_configured = False

        with pytest.raises(StripeClientError) as exc_info:
            await stripe_client.create_usage_record("si_test123", 100)

        assert "not configured" in str(exc_info.value)

    async def test_create_usage_record_stripe_error(self, stripe_client):
        """Test handling of Stripe errors during usage record creation."""
        with patch("stripe.SubscriptionItem.retrieve") as mock_retrieve:
            mock_item = MagicMock()
            mock_item.create_usage_record.side_effect = StripeError("API error")
            mock_retrieve.return_value = mock_item

            with pytest.raises(StripeClientError) as exc_info:
                await stripe_client.create_usage_record("si_test123", 100)

            assert "Failed to create usage record" in str(exc_info.value)

    async def test_list_subscription_items_success(self, stripe_client):
        """Test successful listing of subscription items."""
        mock_items = MagicMock()
        mock_item1 = MagicMock()
        mock_item1.to_dict.return_value = {"id": "si_1", "price": {"id": "price_1"}}
        mock_item2 = MagicMock()
        mock_item2.to_dict.return_value = {"id": "si_2", "price": {"id": "price_2"}}
        mock_items.data = [mock_item1, mock_item2]

        with patch("stripe.SubscriptionItem.list") as mock_list:
            mock_list.return_value = mock_items

            result = await stripe_client.list_subscription_items("sub_test123")

            assert len(result) == 2
            assert result[0]["id"] == "si_1"
            assert result[1]["id"] == "si_2"
            mock_list.assert_called_once_with(subscription="sub_test123", limit=100)

    async def test_add_metered_price_to_subscription_success(self, stripe_client):
        """Test successful addition of metered price to subscription."""
        mock_subscription = MagicMock()
        mock_subscription.to_dict.return_value = {
            "id": "sub_test123",
            "items": {"data": [{"id": "si_new", "price": {"id": "price_overage"}}]},
        }

        with patch("stripe.Subscription.modify") as mock_modify:
            mock_modify.return_value = mock_subscription

            result = await stripe_client.add_metered_price_to_subscription(
                subscription_id="sub_test123",
                price_id="price_overage",
                metadata={"usage_type": "overage"},
            )

            assert result["id"] == "sub_test123"
            mock_modify.assert_called_once_with(
                "sub_test123",
                items=[{"price": "price_overage"}],
                proration_behavior="none",
            )

    async def test_get_subscription_item_for_price_found(self, stripe_client):
        """Test finding a subscription item for a specific price."""
        with patch.object(stripe_client, "list_subscription_items") as mock_list:
            mock_list.return_value = [
                {"id": "si_1", "price": {"id": "price_basic"}},
                {"id": "si_2", "price": {"id": "price_overage"}},
            ]

            result = await stripe_client.get_subscription_item_for_price(
                "sub_test123", "price_overage"
            )

            assert result["id"] == "si_2"
            assert result["price"]["id"] == "price_overage"

    async def test_get_subscription_item_for_price_not_found(self, stripe_client):
        """Test when subscription item for price is not found."""
        with patch.object(stripe_client, "list_subscription_items") as mock_list:
            mock_list.return_value = [
                {"id": "si_1", "price": {"id": "price_basic"}},
            ]

            result = await stripe_client.get_subscription_item_for_price(
                "sub_test123", "price_overage"
            )

            assert result is None

    async def test_create_metered_billing_prices_success(self, stripe_client):
        """Test successful creation of metered billing prices."""
        mock_product = MagicMock()
        mock_product.id = "prod_test"

        mock_price = MagicMock()
        mock_price.id = "price_new_overage"
        mock_price.unit_amount = 20
        mock_price.recurring = {"usage_type": "metered"}

        mock_price_list = MagicMock()
        mock_price_list.data = []

        with patch("stripe.Product.retrieve") as mock_retrieve:
            mock_retrieve.return_value = mock_product
            with patch("stripe.Price.list") as mock_list:
                mock_list.return_value = mock_price_list
                with patch("stripe.Price.create") as mock_create:
                    mock_create.return_value = mock_price

                    result = await stripe_client.create_metered_billing_prices()

                    assert "professional" in result
                    assert "enterprise" in result
                    assert mock_create.call_count == 2

    async def test_create_metered_billing_prices_existing(self, stripe_client):
        """Test when metered prices already exist."""
        mock_product = MagicMock()
        mock_product.id = "prod_test"

        # Create prices for both professional and enterprise
        mock_existing_price_prof = MagicMock()
        mock_existing_price_prof.id = "price_existing_prof_overage"
        mock_existing_price_prof.unit_amount = 20
        mock_existing_price_prof.recurring = {"usage_type": "metered"}

        mock_existing_price_ent = MagicMock()
        mock_existing_price_ent.id = "price_existing_ent_overage"
        mock_existing_price_ent.unit_amount = 10
        mock_existing_price_ent.recurring = {"usage_type": "metered"}

        # First call returns professional price list, second returns enterprise
        mock_price_list_prof = MagicMock()
        mock_price_list_prof.data = [mock_existing_price_prof]

        mock_price_list_ent = MagicMock()
        mock_price_list_ent.data = [mock_existing_price_ent]

        with patch("stripe.Product.retrieve") as mock_retrieve:
            mock_retrieve.return_value = mock_product
            with patch("stripe.Price.list") as mock_list:
                mock_list.side_effect = [mock_price_list_prof, mock_price_list_ent]
                with patch("stripe.Price.create") as mock_create:
                    result = await stripe_client.create_metered_billing_prices()

                    # Should use existing prices, not create new ones
                    assert mock_create.call_count == 0
                    assert result["professional"] == "price_existing_prof_overage"
                    assert result["enterprise"] == "price_existing_ent_overage"

    async def test_create_metered_billing_prices_product_creation(self, stripe_client):
        """Test creating products when they don't exist."""
        mock_product = MagicMock()
        mock_product.id = "prod_new"

        mock_price = MagicMock()
        mock_price.id = "price_new"

        mock_price_list = MagicMock()
        mock_price_list.data = []

        with patch("stripe.Product.retrieve") as mock_retrieve:
            mock_retrieve.side_effect = InvalidRequestError("No such product", "id")
            with patch("stripe.Product.create") as mock_create_product:
                mock_create_product.return_value = mock_product
                with patch("stripe.Price.list") as mock_list:
                    mock_list.return_value = mock_price_list
                    with patch("stripe.Price.create") as mock_create_price:
                        mock_create_price.return_value = mock_price

                        await stripe_client.create_metered_billing_prices()

                        assert mock_create_product.call_count == 2


class TestMeteredBillingIntegration:
    """Integration tests for metered billing with subscription manager."""

    @pytest.fixture
    def mock_user(self):
        """Create a mock user object."""
        user = MagicMock()
        user.user_id = "user123"
        user.email = "test@example.com"
        user.full_name = "Test User"
        user.stripe_customer_id = "cus_test123"
        user.stripe_subscription_id = "sub_test123"
        user.subscription_plan = MagicMock(value="PROFESSIONAL")
        return user

    async def test_subscription_with_overage_pricing(self, mock_user):
        """Test that subscriptions include overage pricing."""
        from github_analyzer.billing.subscription_manager import (
            SubscriptionManager,
            SubscriptionPlan,
        )

        manager = SubscriptionManager()

        # Mock the stripe client methods
        with patch.object(manager.stripe_client, "create_subscription") as mock_create:
            mock_create.return_value = {
                "id": "sub_new123",
                "status": "active",
                "latest_invoice": {"payment_intent": {"client_secret": "secret"}},
            }
            with patch.object(
                manager.stripe_client, "add_metered_price_to_subscription"
            ) as mock_add:
                with patch(
                    "github_analyzer.database.operations.UserOperations.get_user_by_id"
                ) as mock_get:
                    mock_get.return_value = mock_user
                    with patch.object(
                        manager, "_ensure_stripe_customer"
                    ) as mock_ensure:
                        mock_ensure.return_value = "cus_test123"
                        with patch.object(manager, "_update_user_subscription"):
                            # Use a real AsyncSession mock
                            mock_db = MagicMock()

                            result = await manager.create_subscription(
                                mock_db, "user123", SubscriptionPlan.PROFESSIONAL
                            )

                            assert result["has_overage_pricing"] is True
                            mock_add.assert_called_once()

    async def test_plan_update_overage_pricing_change(self, mock_user):
        """Test that plan updates handle overage pricing changes."""
        from github_analyzer.billing.subscription_manager import (
            SubscriptionManager,
            SubscriptionPlan,
        )

        manager = SubscriptionManager()
        mock_user.subscription_plan = SubscriptionPlan.BASIC

        with patch.object(manager.stripe_client, "get_subscription") as mock_get_sub:
            mock_get_sub.return_value = {
                "items": {"data": [{"id": "si_basic"}]},
                "status": "active",
            }
            with patch.object(
                manager.stripe_client, "update_subscription"
            ) as mock_update:
                mock_update.return_value = {
                    "id": "sub_test123",
                    "status": "active",
                    "current_period_start": 1234567890,
                    "current_period_end": 1234567890,
                }
                with patch.object(
                    manager.stripe_client, "get_subscription_item_for_price"
                ) as mock_get_item:
                    mock_get_item.return_value = None  # No existing overage pricing
                    with patch.object(
                        manager.stripe_client, "add_metered_price_to_subscription"
                    ) as mock_add:
                        with patch(
                            "github_analyzer.database.operations.UserOperations.get_user_by_id"
                        ) as mock_get:
                            mock_get.return_value = mock_user
                            with patch.object(manager, "_update_user_subscription"):
                                mock_db = MagicMock()

                                result = await manager.update_subscription_plan(
                                    mock_db, "user123", SubscriptionPlan.PROFESSIONAL
                                )

                                assert result["has_overage_pricing"] is True
                                mock_add.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
