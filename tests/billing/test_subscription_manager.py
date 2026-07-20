"""
Tests for subscription management functionality.

Tests subscription lifecycle, plan features, usage limits,
and business logic for billing operations.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from github_analyzer.billing.subscription_manager import (
    PlanFeatures,
    SubscriptionManager,
    SubscriptionManagerError,
)
from github_analyzer.database.models import (
    SubscriptionPlan,
    SubscriptionStatus,
    User,
)


class TestPlanFeatures:
    """Test suite for PlanFeatures."""

    def test_get_plan_limits_free(self):
        """Test getting limits for free plan."""
        limits = PlanFeatures.get_plan_limits(SubscriptionPlan.FREE)

        assert limits["monthly_analyses"] == 10
        assert limits["batch_size"] == 1
        assert limits["api_rate_limit"] == 10
        assert "basic_analysis" in limits["features"]

    def test_get_plan_limits_professional(self):
        """Test getting limits for professional plan."""
        limits = PlanFeatures.get_plan_limits(SubscriptionPlan.PROFESSIONAL)

        assert limits["monthly_analyses"] == 500
        assert limits["batch_size"] == 5
        assert limits["api_rate_limit"] == 300
        assert "advanced_metrics" in limits["features"]
        assert "api_access" in limits["features"]

    def test_get_plan_limits_enterprise(self):
        """Test getting limits for enterprise plan."""
        limits = PlanFeatures.get_plan_limits(SubscriptionPlan.ENTERPRISE)

        assert limits["monthly_analyses"] == 2000
        assert limits["batch_size"] == 10
        assert limits["api_rate_limit"] == 1000
        assert "custom_integrations" in limits["features"]
        assert "priority_support" in limits["features"]


class TestSubscriptionManager:
    """Test suite for SubscriptionManager."""

    @pytest.fixture
    def subscription_manager(self):
        """Create SubscriptionManager instance for testing."""
        return SubscriptionManager()

    @pytest.fixture
    def mock_user(self):
        """Mock user for testing."""
        return Mock(
            spec=User,
            **{
                "user_id": "usr_test123",
                "email": "test@example.com",
                "full_name": "Test User",
                "subscription_plan": SubscriptionPlan.FREE,
                "subscription_status": SubscriptionStatus.ACTIVE,
                "usage_quota": 10,
                "usage_count": 5,
                "stripe_customer_id": "cus_test123",
                "stripe_subscription_id": None,
            },
        )

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return AsyncMock()

    async def test_get_subscription_status_success(
        self, subscription_manager, mock_db, mock_user
    ):
        """Test successful subscription status retrieval."""
        with patch(
            "github_analyzer.database.operations.UserOperations.get_user_by_id",
            return_value=mock_user,
        ):
            status = await subscription_manager.get_subscription_status(
                mock_db, "usr_test123"
            )

            assert status["user_id"] == "usr_test123"
            assert status["plan"] == "FREE"
            assert status["status"] == "active"
            assert status["usage_quota"] == 10
            assert status["usage_consumed"] == 5
            assert status["usage_remaining"] == 5

    async def test_get_subscription_status_user_not_found(
        self, subscription_manager, mock_db
    ):
        """Test subscription status with user not found."""
        with patch(
            "github_analyzer.database.operations.UserOperations.get_user_by_id",
            return_value=None,
        ):
            with pytest.raises(SubscriptionManagerError) as exc_info:
                await subscription_manager.get_subscription_status(
                    mock_db, "usr_nonexistent"
                )

            assert "User not found" in str(exc_info.value)

    async def test_create_subscription_success(
        self, subscription_manager, mock_db, mock_user
    ):
        """Test successful subscription creation."""
        mock_stripe_customer = {"id": "cus_test123", "email": "test@example.com"}
        mock_stripe_subscription = {
            "id": "sub_test123",
            "status": "active",
            "current_period_start": 1234567890,
            "current_period_end": 1234567890 + 86400 * 30,
        }

        with (
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_id",
                return_value=mock_user,
            ),
            patch(
                "github_analyzer.billing.stripe_client.StripeClient.get_customer",
                return_value=mock_stripe_customer,
            ),
            patch(
                "github_analyzer.billing.stripe_client.StripeClient.create_customer",
                return_value=mock_stripe_customer,
            ),
            patch(
                "github_analyzer.billing.stripe_client.StripeClient.create_subscription",
                return_value=mock_stripe_subscription,
            ),
            patch(
                "github_analyzer.database.operations.UserOperations.update_user_subscription",
                return_value=True,
            ),
        ):
            result = await subscription_manager.create_subscription(
                mock_db, "usr_test123", SubscriptionPlan.BASIC
            )

            assert result["subscription_id"] == "sub_test123"
            assert result["status"] == "active"
            assert result["plan"] == "BASIC"

    async def test_create_subscription_user_not_found(
        self, subscription_manager, mock_db
    ):
        """Test subscription creation with user not found."""
        with patch(
            "github_analyzer.database.operations.UserOperations.get_user_by_id",
            return_value=None,
        ):
            with pytest.raises(SubscriptionManagerError) as exc_info:
                await subscription_manager.create_subscription(
                    mock_db, "usr_nonexistent", SubscriptionPlan.BASIC
                )

            assert "User not found" in str(exc_info.value)

    async def test_update_subscription_plan_success(
        self, subscription_manager, mock_db, mock_user
    ):
        """Test successful subscription plan update."""
        mock_user.stripe_subscription_id = "sub_test123"
        mock_stripe_subscription = {
            "id": "sub_test123",
            "status": "active",
            "current_period_start": 1234567890,
            "current_period_end": 1234567890 + 86400 * 30,
            "items": {
                "data": [{"id": "si_test123", "price": {"id": "price_professional"}}]
            },
        }

        with (
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_id",
                return_value=mock_user,
            ),
            patch(
                "github_analyzer.billing.stripe_client.StripeClient.get_subscription",
                return_value=mock_stripe_subscription,
            ),
            patch(
                "github_analyzer.billing.stripe_client.StripeClient.update_subscription",
                return_value=mock_stripe_subscription,
            ),
            patch(
                "github_analyzer.database.operations.UserOperations.update_user_subscription",
                return_value=True,
            ),
        ):
            result = await subscription_manager.update_subscription_plan(
                mock_db, "usr_test123", SubscriptionPlan.PROFESSIONAL
            )

            assert result["subscription_id"] == "sub_test123"
            assert result["status"] == "active"
            assert result["plan"] == "PROFESSIONAL"

    async def test_update_subscription_plan_no_subscription(
        self, subscription_manager, mock_db, mock_user
    ):
        """Test subscription plan update with no existing subscription."""
        mock_user.stripe_subscription_id = None

        with patch(
            "github_analyzer.database.operations.UserOperations.get_user_by_id",
            return_value=mock_user,
        ):
            with pytest.raises(SubscriptionManagerError) as exc_info:
                await subscription_manager.update_subscription_plan(
                    mock_db, "usr_test123", SubscriptionPlan.PROFESSIONAL
                )

            assert "User has no active subscription" in str(exc_info.value)

    async def test_cancel_subscription_success(
        self, subscription_manager, mock_db, mock_user
    ):
        """Test successful subscription cancellation."""
        mock_user.stripe_subscription_id = "sub_test123"
        mock_cancelled_subscription = {
            "id": "sub_test123",
            "status": "canceled",
            "cancel_at_period_end": True,
            "current_period_end": 1234567890 + 86400 * 30,
        }

        with (
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_id",
                return_value=mock_user,
            ),
            patch(
                "github_analyzer.billing.stripe_client.StripeClient.cancel_subscription",
                return_value=mock_cancelled_subscription,
            ),
            patch(
                "github_analyzer.database.operations.UserOperations.update_user_subscription",
                return_value=True,
            ),
        ):
            result = await subscription_manager.cancel_subscription(
                mock_db, "usr_test123", at_period_end=True
            )

            assert result["subscription_id"] == "sub_test123"
            assert result["status"] == "canceled"
            assert result["at_period_end"] is True

    async def test_check_usage_limits_within_quota(
        self, subscription_manager, mock_db, mock_user
    ):
        """Test usage limits check when within quota."""
        mock_user.usage_count = 5
        mock_user.usage_quota = 10

        with patch(
            "github_analyzer.database.operations.UserOperations.get_user_by_id",
            return_value=mock_user,
        ):
            result = await subscription_manager.check_usage_limits(
                mock_db, "usr_test123", requested_usage=3
            )

            assert result["can_proceed"] is True
            assert result["remaining_quota"] == 5
            assert result["requested_usage"] == 3

    async def test_check_usage_limits_exceeds_quota(
        self, subscription_manager, mock_db, mock_user
    ):
        """Test usage limits check when exceeding quota."""
        mock_user.usage_count = 8
        mock_user.usage_quota = 10

        with patch(
            "github_analyzer.database.operations.UserOperations.get_user_by_id",
            return_value=mock_user,
        ):
            result = await subscription_manager.check_usage_limits(
                mock_db, "usr_test123", requested_usage=5
            )

            assert result["can_proceed"] is False
            assert result["remaining_quota"] == 2
            assert result["requested_usage"] == 5
            assert "upgrade_options" in result
