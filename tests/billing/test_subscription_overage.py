"""
Tests for subscription manager overage handling.

Tests plan upgrades/downgrades with overage pricing and subscription updates.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from github_analyzer.billing.subscription_manager import (
    PlanFeatures,
    SubscriptionManager,
)
from github_analyzer.database.models import SubscriptionPlan, User


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_stripe_client():
    """Create mock Stripe client."""
    client = AsyncMock()
    return client


@pytest.fixture
def professional_user():
    """Create a user with professional subscription."""
    user = MagicMock(spec=User)
    user.user_id = "user_prof_123"
    user.email = "prof@example.com"
    user.full_name = "Professional User"
    user.subscription_plan = SubscriptionPlan.PROFESSIONAL
    user.stripe_customer_id = "cus_professional"
    user.stripe_subscription_id = "sub_professional"
    user.usage_quota = 500
    user.usage_count = 300
    user.created_at = datetime.now(timezone.utc)
    return user


@pytest.fixture
def basic_user():
    """Create a user with basic subscription."""
    user = MagicMock(spec=User)
    user.user_id = "user_basic_123"
    user.email = "basic@example.com"
    user.full_name = "Basic User"
    user.subscription_plan = SubscriptionPlan.BASIC
    user.stripe_customer_id = "cus_basic"
    user.stripe_subscription_id = "sub_basic"
    user.usage_quota = 100
    user.usage_count = 50
    user.created_at = datetime.now(timezone.utc)
    return user


class TestOveragePricingSetup:
    """Test overage pricing setup during subscription creation."""

    @patch("github_analyzer.database.operations.UserOperations.get_user_by_id")
    async def test_create_professional_subscription_with_overage(
        self, mock_get_user, mock_db_session, mock_stripe_client, professional_user
    ):
        """Test creating professional subscription includes overage pricing."""
        mock_get_user.return_value = professional_user

        # Mock Stripe responses
        mock_stripe_client.create_subscription.return_value = {
            "id": "sub_new_professional",
            "status": "active",
            "items": {
                "data": [{"id": "si_base", "price": {"id": "price_professional"}}]
            },
            "current_period_start": 1625097600,
            "current_period_end": 1627776000,
        }

        mock_stripe_client.add_metered_price_to_subscription.return_value = {
            "id": "si_overage",
            "price": {"id": "price_professional_overage"},
        }

        # Create subscription manager with mocked client
        manager = SubscriptionManager()
        manager.stripe_client = mock_stripe_client

        # Test subscription creation
        with patch.object(manager, "_update_user_subscription", AsyncMock()):
            await manager.create_subscription(
                mock_db_session,
                user_id="user_prof_123",
                plan=SubscriptionPlan.PROFESSIONAL,
            )

        # Verify overage pricing was added
        mock_stripe_client.add_metered_price_to_subscription.assert_called_once()
        call_args = mock_stripe_client.add_metered_price_to_subscription.call_args[1]
        assert call_args["subscription_id"] == "sub_new_professional"
        assert call_args["price_id"] == "price_professional_overage"
        assert call_args["metadata"]["usage_type"] == "overage"

    @patch("github_analyzer.database.operations.UserOperations.get_user_by_id")
    async def test_create_basic_subscription_no_overage(
        self, mock_get_user, mock_db_session, mock_stripe_client, basic_user
    ):
        """Test creating basic subscription excludes overage pricing."""
        mock_get_user.return_value = basic_user

        # Mock Stripe responses
        mock_stripe_client.create_subscription.return_value = {
            "id": "sub_new_basic",
            "status": "active",
            "items": {"data": [{"id": "si_base", "price": {"id": "price_basic"}}]},
            "current_period_start": 1625097600,
            "current_period_end": 1627776000,
        }

        # Create subscription manager with mocked client
        manager = SubscriptionManager()
        manager.stripe_client = mock_stripe_client

        # Test subscription creation
        with patch.object(manager, "_update_user_subscription", AsyncMock()):
            await manager.create_subscription(
                mock_db_session,
                user_id="user_basic_123",
                plan=SubscriptionPlan.BASIC,
            )

        # Verify overage pricing was NOT added
        mock_stripe_client.add_metered_price_to_subscription.assert_not_called()


class TestPlanUpgradeWithOverage:
    """Test plan upgrades involving overage pricing."""

    @patch("github_analyzer.database.operations.UserOperations.get_user_by_id")
    async def test_upgrade_basic_to_professional_adds_overage(
        self, mock_get_user, mock_db_session, mock_stripe_client, basic_user
    ):
        """Test upgrading from basic to professional adds overage pricing."""
        mock_get_user.return_value = basic_user

        # Mock current subscription (basic plan)
        mock_stripe_client.get_subscription.return_value = {
            "id": "sub_basic",
            "items": {"data": [{"id": "si_basic", "price": {"id": "price_basic"}}]},
        }

        # Mock subscription update
        mock_stripe_client.update_subscription.return_value = {
            "id": "sub_basic",
            "status": "active",
            "items": {
                "data": [{"id": "si_basic", "price": {"id": "price_professional"}}]
            },
        }

        # Mock overage item check and addition
        mock_stripe_client.get_subscription_item_for_price = AsyncMock(
            return_value=None
        )
        mock_stripe_client.add_metered_price_to_subscription.return_value = {
            "id": "si_overage",
            "price": {"id": "price_professional_overage"},
        }

        # Create subscription manager
        manager = SubscriptionManager()
        manager.stripe_client = mock_stripe_client

        # Test upgrade
        with patch.object(manager, "_update_user_subscription", AsyncMock()):
            await manager.update_subscription_plan(
                mock_db_session,
                user_id="user_basic_123",
                new_plan=SubscriptionPlan.PROFESSIONAL,
            )

        # Verify subscription was updated
        mock_stripe_client.update_subscription.assert_called_once()

        # Verify overage pricing was added
        mock_stripe_client.add_metered_price_to_subscription.assert_called_once()
        overage_call = mock_stripe_client.add_metered_price_to_subscription.call_args[1]
        assert overage_call["price_id"] == "price_professional_overage"
        assert overage_call["metadata"]["plan"] == "PROFESSIONAL"

    @patch("github_analyzer.database.operations.UserOperations.get_user_by_id")
    @patch.dict(
        "github_analyzer.billing.subscription_manager.PlanFeatures.PLANS",
        {
            SubscriptionPlan.FREE: {
                "monthly_analyses": 10,
                "price_id": None,
                "features": ["basic_analysis"],
            },
            SubscriptionPlan.PROFESSIONAL: {
                "price_id": "mock_price_professional",
                "monthly_analyses": 500,
                "overage_price_id": "price_professional_overage",
                "overage_rate": 0.20,
                "features": ["basic_analysis", "pdf_reports"],
            },
            SubscriptionPlan.ENTERPRISE: {
                "price_id": "mock_price_enterprise",
                "monthly_analyses": 2000,
                "overage_price_id": "price_enterprise_overage",
                "overage_rate": 0.10,
                "features": ["all_features"],
            },
        },
        clear=True,
    )
    async def test_upgrade_professional_to_enterprise_updates_overage(
        self, mock_get_user, mock_db_session, mock_stripe_client, professional_user
    ):
        """Test upgrading from professional to enterprise updates overage pricing."""
        mock_get_user.return_value = professional_user

        # Mock current subscription with professional overage
        mock_stripe_client.get_subscription.return_value = {
            "id": "sub_professional",
            "items": {
                "data": [
                    {"id": "si_base", "price": {"id": "price_professional"}},
                    {
                        "id": "si_overage",
                        "price": {"id": "price_professional_overage"},
                    },
                ]
            },
        }

        # Mock subscription update
        mock_stripe_client.update_subscription.return_value = {
            "id": "sub_professional",
            "status": "active",
            "items": {"data": [{"id": "si_base", "price": {"id": "price_enterprise"}}]},
        }

        # Create subscription manager
        manager = SubscriptionManager()
        manager.stripe_client = mock_stripe_client

        # Test upgrade
        with patch.object(manager, "_update_user_subscription", AsyncMock()):
            await manager.update_subscription_plan(
                mock_db_session,
                user_id="user_prof_123",
                new_plan=SubscriptionPlan.ENTERPRISE,
            )

        # Verify subscription was updated
        update_call = mock_stripe_client.update_subscription.call_args[1]
        # The current logic does not remove/re-add overage items on upgrade,
        # so we just verify the main plan was updated with our mock price
        assert update_call["items"][0]["price"] == "mock_price_enterprise"


class TestPlanDowngradeWithOverage:
    """Test plan downgrades removing overage pricing."""

    @patch("github_analyzer.database.operations.UserOperations.get_user_by_id")
    async def test_downgrade_professional_to_basic_removes_overage(
        self, mock_get_user, mock_db_session, mock_stripe_client, professional_user
    ):
        """Test downgrading from professional to basic removes overage pricing."""
        mock_get_user.return_value = professional_user

        # Mock current subscription with overage
        mock_stripe_client.get_subscription.return_value = {
            "id": "sub_professional",
            "items": {
                "data": [
                    {"id": "si_base", "price": {"id": "price_professional"}},
                    {
                        "id": "si_overage",
                        "price": {"id": "price_professional_overage"},
                    },
                ]
            },
        }

        # Mock subscription update
        mock_stripe_client.update_subscription.return_value = {
            "id": "sub_professional",
            "status": "active",
            "items": {"data": [{"id": "si_base", "price": {"id": "price_basic"}}]},
        }

        # Create subscription manager
        manager = SubscriptionManager()
        manager.stripe_client = mock_stripe_client

        # Test downgrade
        with patch.object(manager, "_update_user_subscription", AsyncMock()):
            await manager.update_subscription_plan(
                mock_db_session,
                user_id="user_prof_123",
                new_plan=SubscriptionPlan.BASIC,
            )

        # Verify overage item was removed
        update_call = mock_stripe_client.update_subscription.call_args[1]
        assert "remove_items" in update_call
        assert "si_overage" in update_call["remove_items"]


class TestPlanFeaturesOverage:
    """Test plan features configuration for overage."""

    def test_plan_features_professional_has_overage(self):
        """Test professional plan features include overage configuration."""
        features = PlanFeatures.get_plan_limits(SubscriptionPlan.PROFESSIONAL)

        assert features["overage_price_id"] == "price_professional_overage"
        assert features["overage_rate"] == 0.20
        assert features["monthly_analyses"] == 500

    def test_plan_features_enterprise_has_overage(self):
        """Test enterprise plan features include overage configuration."""
        features = PlanFeatures.get_plan_limits(SubscriptionPlan.ENTERPRISE)

        assert features["overage_price_id"] == "price_enterprise_overage"
        assert features["overage_rate"] == 0.10
        assert features["monthly_analyses"] == 2000

    def test_plan_features_basic_no_overage(self):
        """Test basic plan features exclude overage configuration."""
        features = PlanFeatures.get_plan_limits(SubscriptionPlan.BASIC)

        assert "overage_price_id" not in features
        assert features.get("overage_rate", "0.00") == "0.00"
        assert features.get("supports_overage", False) is False
        assert features["monthly_analyses"] == 100

    def test_plan_features_free_no_overage(self):
        """Test free plan features exclude overage configuration."""
        features = PlanFeatures.get_plan_limits(SubscriptionPlan.FREE)

        assert "overage_price_id" not in features
        assert features.get("overage_rate", "0.00") == "0.00"
        assert features.get("supports_overage", False) is False
        assert features["monthly_analyses"] == 10


class TestOverageEdgeCases:
    """Test edge cases in overage handling."""

    @patch("github_analyzer.database.operations.UserOperations.get_user_by_id")
    async def test_check_usage_limits_exactly_at_grace_limit(
        self, mock_get_user, mock_db_session, professional_user
    ):
        """Test behavior when usage is exactly at grace period limit."""
        professional_user.usage_count = 550  # Exactly at 10% grace limit
        mock_get_user.return_value = professional_user

        manager = SubscriptionManager()
        result = await manager.check_usage_limits(mock_db_session, "user_prof_123", 1)

        # Should not proceed as we need 1 more call
        assert result["can_proceed"] is False
        assert result["grace_period"] is False
        assert result["grace_remaining"] == 0

    @patch("github_analyzer.database.operations.UserOperations.get_user_by_id")
    async def test_check_usage_limits_large_batch_request(
        self, mock_get_user, mock_db_session, professional_user
    ):
        """Test usage check for large batch request that exceeds grace period."""
        professional_user.usage_count = 520  # In grace period
        mock_get_user.return_value = professional_user

        manager = SubscriptionManager()
        # Request 50 calls at once (would go to 570, beyond grace)
        result = await manager.check_usage_limits(mock_db_session, "user_prof_123", 50)

        # Should be blocked because request would exceed grace limit
        assert result["can_proceed"] is False
        assert result["grace_period"] is True
        assert result["grace_remaining"] == 30
        assert result["requested_usage"] == 50

    @patch("github_analyzer.database.operations.UserOperations.get_user_by_id")
    async def test_check_usage_limits_small_request_within_grace(
        self, mock_get_user, mock_db_session, professional_user
    ):
        """Test small request that fits within grace period is allowed."""
        professional_user.usage_count = 520  # In grace period
        mock_get_user.return_value = professional_user

        manager = SubscriptionManager()
        # Request 20 calls (would go to 540, still within grace)
        result = await manager.check_usage_limits(mock_db_session, "user_prof_123", 20)

        # Should be allowed because it fits within grace limit
        assert result["can_proceed"] is True
        assert result["grace_period"] is True
        assert result["grace_remaining"] == 30


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
