"""
Test suite for subscription manager edge cases and error scenarios.

Tests plan downgrades, error handling, and edge cases that could
occur in production with subscription management.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from github_analyzer.billing.stripe_client import StripeClientError
from github_analyzer.billing.subscription_manager import (
    SubscriptionManager,
    SubscriptionPlan,
)
from github_analyzer.database.models import SubscriptionStatus


class TestSubscriptionManagerEdgeCases:
    """Test edge cases and error scenarios in SubscriptionManager."""

    @pytest.fixture
    def subscription_manager(self):
        """Create a SubscriptionManager instance."""
        manager = SubscriptionManager()
        # Mock the stripe client
        manager.stripe_client = MagicMock()
        manager.stripe_client.get_customer = AsyncMock(return_value=None)
        manager.stripe_client.create_customer = AsyncMock(
            return_value={"id": "cus_new123"}
        )
        return manager

    @pytest.fixture
    def mock_user_professional(self):
        """Create a mock professional user."""
        user = MagicMock()
        user.user_id = "user123"
        user.email = "prof@example.com"
        user.full_name = "Professional User"
        user.stripe_customer_id = "cus_prof123"
        user.stripe_subscription_id = "sub_prof123"
        user.subscription_plan = SubscriptionPlan.PROFESSIONAL
        user.subscription_status = SubscriptionStatus.ACTIVE
        user.usage_quota = 500
        user.usage_count = 100
        return user

    @pytest.fixture
    def mock_user_enterprise(self):
        """Create a mock enterprise user."""
        user = MagicMock()
        user.user_id = "user456"
        user.email = "ent@example.com"
        user.full_name = "Enterprise User"
        user.stripe_customer_id = "cus_ent456"
        user.stripe_subscription_id = "sub_ent456"
        user.subscription_plan = SubscriptionPlan.ENTERPRISE
        return user

    async def test_plan_downgrade_removes_old_overage_price(
        self, subscription_manager, mock_user_professional
    ):
        """Test that downgrading from Professional to Basic removes overage pricing."""
        mock_db = MagicMock()

        # Mock the current subscription with professional overage price
        mock_sub = {
            "items": {
                "data": [
                    {"id": "si_basic", "price": {"id": "price_basic"}},
                    {
                        "id": "si_prof_overage",
                        "price": {"id": "price_professional_overage"},
                    },
                ]
            },
            "status": "active",
        }

        subscription_manager.stripe_client.get_subscription = AsyncMock(
            return_value=mock_sub
        )

        # Mock the update subscription call
        subscription_manager.stripe_client.update_subscription = AsyncMock(
            return_value={
                "id": "sub_prof123",
                "status": "active",
                "current_period_start": 1234567890,
                "current_period_end": 1234567890,
            }
        )

        with patch(
            "github_analyzer.database.operations.UserOperations.get_user_by_id",
            new_callable=AsyncMock,
        ) as mock_get_user:
            mock_get_user.return_value = mock_user_professional

            with patch.object(subscription_manager, "_update_user_subscription"):
                result = await subscription_manager.update_subscription_plan(
                    mock_db, "user123", SubscriptionPlan.BASIC
                )

                # Verify the old overage price was removed
                update_call = (
                    subscription_manager.stripe_client.update_subscription.call_args
                )
                assert update_call[1]["remove_items"] == ["si_prof_overage"]
                assert result["has_overage_pricing"] is False

    async def test_plan_upgrade_adds_new_overage_price(
        self, subscription_manager, mock_user_professional
    ):
        """Test that upgrading from Basic to Enterprise adds overage pricing."""
        mock_db = MagicMock()
        mock_user_professional.subscription_plan = SubscriptionPlan.BASIC

        # Mock the current subscription without overage price
        mock_sub = {
            "items": {"data": [{"id": "si_basic", "price": {"id": "price_basic"}}]},
            "status": "active",
        }

        subscription_manager.stripe_client.get_subscription = AsyncMock(
            return_value=mock_sub
        )

        subscription_manager.stripe_client.update_subscription = AsyncMock(
            return_value={
                "id": "sub_prof123",
                "status": "active",
                "current_period_start": 1234567890,
                "current_period_end": 1234567890,
            }
        )

        # Mock checking for existing overage item
        subscription_manager.stripe_client.get_subscription_item_for_price = AsyncMock(
            return_value=None
        )

        # Mock adding overage price
        subscription_manager.stripe_client.add_metered_price_to_subscription = (
            AsyncMock()
        )

        with patch(
            "github_analyzer.database.operations.UserOperations.get_user_by_id",
            new_callable=AsyncMock,
        ) as mock_get_user:
            mock_get_user.return_value = mock_user_professional

            with patch.object(subscription_manager, "_update_user_subscription"):
                result = await subscription_manager.update_subscription_plan(
                    mock_db, "user123", SubscriptionPlan.ENTERPRISE
                )

                # Verify overage price was added
                subscription_manager.stripe_client.add_metered_price_to_subscription.assert_awaited_once()
                assert result["has_overage_pricing"] is True

    async def test_subscription_creation_stripe_error_rollback(
        self, subscription_manager, mock_user_professional
    ):
        """Test that subscription creation errors are handled properly."""
        mock_db = MagicMock()
        mock_user_professional.stripe_subscription_id = None
        mock_user_professional.stripe_customer_id = None
        mock_user_professional.email = "test@example.com"
        mock_user_professional.full_name = "Test User"
        mock_user_professional.created_at = MagicMock()
        mock_user_professional.created_at.isoformat.return_value = "2025-07-08T00:00:00"

        # Mock subscription creation failure
        subscription_manager.stripe_client.create_subscription = AsyncMock(
            side_effect=StripeClientError("Card declined")
        )

        with patch(
            "github_analyzer.database.operations.UserOperations.get_user_by_id",
            new_callable=AsyncMock,
        ) as mock_get_user:
            mock_get_user.return_value = mock_user_professional

            from github_analyzer.billing.subscription_manager import (
                SubscriptionManagerError,
            )

            with pytest.raises(SubscriptionManagerError) as exc_info:
                await subscription_manager.create_subscription(
                    mock_db, "user123", SubscriptionPlan.PROFESSIONAL
                )

            assert "Card declined" in str(exc_info.value)

    async def test_cancel_subscription_error_handling(
        self, subscription_manager, mock_user_professional
    ):
        """Test error handling during subscription cancellation."""
        mock_db = MagicMock()

        # Mock cancellation failure
        subscription_manager.stripe_client.cancel_subscription = AsyncMock(
            side_effect=StripeClientError("Subscription not found")
        )

        with patch(
            "github_analyzer.database.operations.UserOperations.get_user_by_id",
            new_callable=AsyncMock,
        ) as mock_get_user:
            mock_get_user.return_value = mock_user_professional

            from github_analyzer.billing.subscription_manager import (
                SubscriptionManagerError,
            )

            with pytest.raises(SubscriptionManagerError) as exc_info:
                await subscription_manager.cancel_subscription(mock_db, "user123")

            assert "Subscription not found" in str(exc_info.value)

    async def test_update_subscription_overage_price_addition_error(
        self, subscription_manager, mock_user_professional
    ):
        """Test error when adding overage price during update fails."""
        mock_db = MagicMock()

        # Change user's current plan to BASIC (no overage pricing)
        mock_user_professional.subscription_plan = SubscriptionPlan.BASIC

        # Mock the current subscription
        mock_sub = {
            "items": {"data": [{"id": "si_basic", "price": {"id": "price_basic"}}]},
            "status": "active",
        }

        subscription_manager.stripe_client.get_subscription = AsyncMock(
            return_value=mock_sub
        )

        subscription_manager.stripe_client.update_subscription = AsyncMock(
            return_value={
                "id": "sub_prof123",
                "status": "active",
                "current_period_start": 1234567890,
                "current_period_end": 1234567890,
            }
        )

        subscription_manager.stripe_client.get_subscription_item_for_price = AsyncMock(
            return_value=None
        )

        # Mock overage price addition failure
        subscription_manager.stripe_client.add_metered_price_to_subscription = (
            AsyncMock(side_effect=StripeClientError("Failed to add metered price"))
        )

        with patch(
            "github_analyzer.database.operations.UserOperations.get_user_by_id",
            new_callable=AsyncMock,
        ) as mock_get_user:
            mock_get_user.return_value = mock_user_professional

            with patch.object(subscription_manager, "_update_user_subscription"):
                # Should still succeed but log the error
                result = await subscription_manager.update_subscription_plan(
                    mock_db, "user123", SubscriptionPlan.PROFESSIONAL
                )

                # Subscription update succeeded even though overage addition failed
                assert result["subscription_id"] == "sub_prof123"
                assert result["has_overage_pricing"] is False

    async def test_get_subscription_status_stripe_error(
        self, subscription_manager, mock_user_professional
    ):
        """Test error handling in get_subscription_status - should continue gracefully."""
        mock_db = MagicMock()

        subscription_manager.stripe_client.get_subscription = AsyncMock(
            side_effect=StripeClientError("Network error")
        )

        # Remove subscription dates to simulate no fallback data available
        mock_user_professional.subscription_start_date = None
        mock_user_professional.subscription_end_date = None

        with patch(
            "github_analyzer.database.operations.UserOperations.get_user_by_id",
            new_callable=AsyncMock,
        ) as mock_get_user:
            mock_get_user.return_value = mock_user_professional

            # Should not raise exception, but return status without Stripe details
            result = await subscription_manager.get_subscription_status(
                mock_db, "user123"
            )

            # Verify basic user data is returned
            assert result["user_id"] == "user123"
            assert result["plan"] == "PROFESSIONAL"
            assert result["status"] == "active"
            # Stripe subscription details should not be present due to error
            assert "stripe_subscription_id" not in result

    async def test_create_checkout_session_with_overage_pricing(
        self, subscription_manager, mock_user_professional
    ):
        """Test checkout session creation includes overage pricing setup."""
        mock_db = MagicMock()
        mock_user_professional.stripe_customer_id = None

        subscription_manager.stripe_client.create_checkout_session = AsyncMock(
            return_value={
                "id": "cs_test123",
                "url": "https://checkout.stripe.com/pay/cs_test123",
            }
        )

        with patch(
            "github_analyzer.database.operations.UserOperations.get_user_by_id",
            new_callable=AsyncMock,
        ) as mock_get_user:
            mock_get_user.return_value = mock_user_professional

            with patch.object(
                subscription_manager, "_ensure_stripe_customer", new_callable=AsyncMock
            ) as mock_ensure:
                mock_ensure.return_value = "cus_123"
                result = await subscription_manager.create_checkout_session(
                    mock_db,
                    "user123",
                    SubscriptionPlan.PROFESSIONAL,
                    "http://example.com/success",
                    "http://example.com/cancel",
                )

                # Verify checkout session was created
                assert (
                    result["checkout_url"]
                    == "https://checkout.stripe.com/pay/cs_test123"
                )

                # Verify the metadata includes overage setup flag
                create_call = (
                    subscription_manager.stripe_client.create_checkout_session.call_args
                )
                metadata = create_call[1]["metadata"]
                assert metadata["setup_overage_pricing"] == "true"

    async def test_concurrent_subscription_updates(
        self, subscription_manager, mock_user_professional
    ):
        """Test handling of concurrent subscription update attempts."""
        mock_db = MagicMock()

        # Simulate a subscription that's already being modified
        subscription_manager.stripe_client.get_subscription = AsyncMock(
            return_value={
                "items": {"data": []},
                "status": "active",
                "metadata": {"updating": "true"},
            }
        )

        # Mock update to simulate conflict
        subscription_manager.stripe_client.update_subscription = AsyncMock(
            side_effect=StripeClientError("Another update is in progress")
        )

        with patch(
            "github_analyzer.database.operations.UserOperations.get_user_by_id",
            new_callable=AsyncMock,
        ) as mock_get_user:
            mock_get_user.return_value = mock_user_professional

            from github_analyzer.billing.subscription_manager import (
                SubscriptionManagerError,
            )

            with pytest.raises(SubscriptionManagerError) as exc_info:
                await subscription_manager.update_subscription_plan(
                    mock_db, "user123", SubscriptionPlan.ENTERPRISE
                )

            assert "Another update is in progress" in str(exc_info.value)

    async def test_subscription_with_trial_period_handling(
        self, subscription_manager, mock_user_professional
    ):
        """Test handling subscriptions with trial periods."""
        mock_db = MagicMock()
        mock_user_professional.stripe_subscription_id = None

        # Mock subscription creation with trial
        subscription_manager.stripe_client.create_subscription = AsyncMock(
            return_value={
                "id": "sub_trial123",
                "status": "trialing",
                "trial_end": 1234567890,
                "latest_invoice": {"payment_intent": None},
            }
        )

        with patch(
            "github_analyzer.database.operations.UserOperations.get_user_by_id",
            new_callable=AsyncMock,
        ) as mock_get_user:
            mock_get_user.return_value = mock_user_professional

            with patch.object(
                subscription_manager, "_ensure_stripe_customer"
            ) as mock_ensure:
                mock_ensure.return_value = "cus_trial123"

                with patch.object(subscription_manager, "_update_user_subscription"):
                    result = await subscription_manager.create_subscription(
                        mock_db, "user123", SubscriptionPlan.PROFESSIONAL
                    )

                    assert result["status"] == "trialing"
                    assert result["trial_end"] == 1234567890
                    assert result["client_secret"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
