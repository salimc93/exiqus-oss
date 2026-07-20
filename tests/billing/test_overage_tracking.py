"""
Tests for overage tracking functionality in the billing module.

Tests UsageTracker overage methods and grace period calculations.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from github_analyzer.billing.subscription_manager import SubscriptionManager
from github_analyzer.billing.usage_tracker import UsageTracker
from github_analyzer.database.models import SubscriptionPlan, User


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    session = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def professional_user():
    """Create a professional plan user."""
    user = MagicMock(spec=User)
    user.user_id = "prof_123"
    user.email = "prof@example.com"
    user.subscription_plan = SubscriptionPlan.PROFESSIONAL
    user.usage_quota = 500
    user.usage_count = 450
    return user


@pytest.fixture
def enterprise_user():
    """Create an enterprise plan user."""
    user = MagicMock(spec=User)
    user.user_id = "ent_123"
    user.email = "ent@example.com"
    user.subscription_plan = SubscriptionPlan.ENTERPRISE
    user.usage_quota = 2000
    user.usage_count = 2100
    return user


@pytest.fixture
def basic_user():
    """Create a basic plan user."""
    user = MagicMock(spec=User)
    user.user_id = "basic_123"
    user.email = "basic@example.com"
    user.subscription_plan = SubscriptionPlan.BASIC
    user.usage_quota = 100
    user.usage_count = 100
    return user


class TestOverageStatusCalculation:
    """Test overage status calculation for different scenarios."""

    @patch("github_analyzer.database.operations.UserOperations.get_user_by_id")
    async def test_get_overage_status_professional_at_80_percent(
        self, mock_get_user, mock_db_session, professional_user
    ):
        """Test overage status when professional user is at 80% usage."""
        professional_user.usage_count = 400  # 80% of 500
        mock_get_user.return_value = professional_user

        status = await UsageTracker.get_overage_status(mock_db_session, "prof_123")

        assert status["user_id"] == "prof_123"
        assert status["plan"] == "PROFESSIONAL"
        assert status["usage_consumed"] == 400
        assert status["usage_quota"] == 500
        assert status["overage_amount"] == 0
        assert status["overage_cost"] == "0.00"
        assert status["overage_rate"] in ["0.20", 0.2, 0.20]  # Accept string or float
        assert status["supports_overage"] is True
        assert status["warning_level"] == "high"
        assert status["usage_percentage"] == 80.0

    @patch("github_analyzer.database.operations.UserOperations.get_user_by_id")
    async def test_get_overage_status_professional_at_90_percent(
        self, mock_get_user, mock_db_session, professional_user
    ):
        """Test overage status when professional user is at 90% usage."""
        professional_user.usage_count = 450  # 90% of 500
        mock_get_user.return_value = professional_user

        status = await UsageTracker.get_overage_status(mock_db_session, "prof_123")

        assert status["warning_level"] == "critical"
        assert status["usage_percentage"] == 90.0

    @patch("github_analyzer.database.operations.UserOperations.get_user_by_id")
    async def test_get_overage_status_enterprise_with_overage(
        self, mock_get_user, mock_db_session, enterprise_user
    ):
        """Test overage status when enterprise user exceeds quota."""
        mock_get_user.return_value = enterprise_user

        status = await UsageTracker.get_overage_status(mock_db_session, "ent_123")

        assert status["usage_consumed"] == 2100
        assert status["usage_quota"] == 2000
        assert status["overage_amount"] == 100
        assert status["overage_cost"] == "10.00"  # 100 * $0.10
        assert status["overage_rate"] in ["0.10", 0.1, 0.10]  # Accept string or float
        assert status["supports_overage"] is True
        assert status["warning_level"] == "exceeded"
        assert status["usage_percentage"] == 105.0

    @patch("github_analyzer.database.operations.UserOperations.get_user_by_id")
    async def test_get_overage_status_basic_at_limit(
        self, mock_get_user, mock_db_session, basic_user
    ):
        """Test overage status when basic user is at quota limit."""
        mock_get_user.return_value = basic_user

        status = await UsageTracker.get_overage_status(mock_db_session, "basic_123")

        assert status["overage_amount"] == 0
        assert status["overage_cost"] == "0.00"
        assert status["overage_rate"] in ["0.00", 0.0, 0.00]  # Accept string or float
        assert status["supports_overage"] is False
        assert status["warning_level"] == "exceeded"
        assert status["usage_percentage"] == 100.0

    @patch("github_analyzer.database.operations.UserOperations.get_user_by_id")
    async def test_get_overage_status_user_not_found(
        self, mock_get_user, mock_db_session
    ):
        """Test overage status when user not found."""
        mock_get_user.return_value = None

        with pytest.raises(ValueError, match="User not found"):
            await UsageTracker.get_overage_status(mock_db_session, "invalid_user")


class TestOverageCostCalculation:
    """Test overage cost calculation."""

    def test_calculate_overage_cost_no_overage(self):
        """Test cost calculation when no overage."""
        cost = UsageTracker.calculate_overage_cost(450, 500, 0.20)
        assert cost == "0.00"

    def test_calculate_overage_cost_professional(self):
        """Test cost calculation for professional plan overage."""
        # 100 calls over quota at $0.20 each
        cost = UsageTracker.calculate_overage_cost(600, 500, 0.20)
        assert cost == "20.00"

    def test_calculate_overage_cost_enterprise(self):
        """Test cost calculation for enterprise plan overage."""
        # 500 calls over quota at $0.10 each
        cost = UsageTracker.calculate_overage_cost(2500, 2000, 0.10)
        assert cost == "50.00"

    def test_calculate_overage_cost_fractional(self):
        """Test cost calculation with fractional result."""
        # 7 calls over quota at $0.20 each = $1.40
        cost = UsageTracker.calculate_overage_cost(507, 500, 0.20)
        assert cost == "1.40"

    def test_calculate_overage_cost_zero_rate(self):
        """Test cost calculation with zero rate."""
        cost = UsageTracker.calculate_overage_cost(600, 500, 0.00)
        assert cost == "0.00"


class TestGracePeriodCalculation:
    """Test grace period calculations in SubscriptionManager."""

    @patch("github_analyzer.database.operations.UserOperations.get_user_by_id")
    async def test_grace_period_professional_user(
        self, mock_get_user, mock_db_session, professional_user
    ):
        """Test grace period allows professional user to continue."""
        professional_user.usage_count = 520  # Over quota but within 10% grace
        mock_get_user.return_value = professional_user

        manager = SubscriptionManager()
        result = await manager.check_usage_limits(mock_db_session, "prof_123", 1)

        assert result["can_proceed"] is True
        assert result["grace_period"] is True
        assert result["grace_remaining"] == 30  # 550 limit - 520 consumed

    @patch("github_analyzer.database.operations.UserOperations.get_user_by_id")
    async def test_grace_period_exhausted(
        self, mock_get_user, mock_db_session, professional_user
    ):
        """Test when grace period is exhausted."""
        professional_user.usage_count = 560  # Beyond 10% grace (550 limit)
        mock_get_user.return_value = professional_user

        manager = SubscriptionManager()
        result = await manager.check_usage_limits(mock_db_session, "prof_123", 1)

        assert result["can_proceed"] is False
        assert result["grace_period"] is False
        assert result["grace_remaining"] == 0
        assert "Grace period exhausted" in result["message"]

    @patch("github_analyzer.database.operations.UserOperations.get_user_by_id")
    async def test_no_grace_period_for_basic_plan(
        self, mock_get_user, mock_db_session, basic_user
    ):
        """Test basic plan has no grace period."""
        basic_user.usage_count = 101  # Over quota
        mock_get_user.return_value = basic_user

        manager = SubscriptionManager()
        result = await manager.check_usage_limits(mock_db_session, "basic_123", 1)

        assert result["can_proceed"] is False
        assert result["grace_period"] is False
        assert result["supports_overage"] is False


class TestQuotaResetTimestamp:
    """Test quota reset timestamp calculation."""

    def test_quota_reset_timestamp_mid_month(self):
        """Test reset timestamp calculation mid-month."""
        manager = SubscriptionManager()

        # Mock current time as July 15, 2025
        with patch("github_analyzer.billing.subscription_manager.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(
                2025, 7, 15, 10, 30, 0, tzinfo=timezone.utc
            )
            mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            reset_time = manager._get_quota_reset_timestamp()

            assert reset_time.year == 2025
            assert reset_time.month == 8
            assert reset_time.day == 1
            assert reset_time.hour == 0
            assert reset_time.minute == 0

    def test_quota_reset_timestamp_december(self):
        """Test reset timestamp calculation in December."""
        manager = SubscriptionManager()

        # Mock current time as December 25, 2025
        with patch("github_analyzer.billing.subscription_manager.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(
                2025, 12, 25, 15, 45, 0, tzinfo=timezone.utc
            )
            mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            reset_time = manager._get_quota_reset_timestamp()

            assert reset_time.year == 2026
            assert reset_time.month == 1
            assert reset_time.day == 1


class TestOverageIntegration:
    """Integration tests for overage functionality."""

    @pytest.mark.integration
    @patch("github_analyzer.database.operations.UserOperations.get_user_by_id")
    @patch("github_analyzer.database.operations.UserOperations.increment_usage_count")
    async def test_usage_tracking_with_overage_transition(
        self, mock_increment, mock_get_user, mock_db_session, professional_user
    ):
        """Test usage tracking as user transitions to overage."""
        # Start at 499 usage (1 below quota)
        professional_user.usage_count = 499
        mock_get_user.return_value = professional_user
        mock_increment.return_value = True

        # Record 5 API calls
        with patch(
            "github_analyzer.billing.usage_tracker.BillingUsageOperations.create_usage_record",
            new_callable=AsyncMock,
        ):
            await UsageTracker.record_api_usage(
                mock_db_session,
                user_id="prof_123",
                usage_type="analysis",
                usage_count=5,
            )

        # Verify increment was called with 5
        mock_increment.assert_called_once_with(mock_db_session, "prof_123", 5)

        # Now user would be at 504 (4 calls into overage)
        professional_user.usage_count = 504
        status = await UsageTracker.get_overage_status(mock_db_session, "prof_123")

        assert status["overage_amount"] == 4
        assert status["overage_cost"] == "0.80"  # 4 * $0.20


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
