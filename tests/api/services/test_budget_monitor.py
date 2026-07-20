"""
Tests for budget monitoring service.

Tests cost tracking, budget warnings, and spending limits.
"""

from unittest.mock import AsyncMock

import pytest

from github_analyzer.api.services.budget_monitor import BudgetMonitor


class TestBudgetMonitor:
    """Test cases for budget monitoring service."""

    @pytest.fixture
    def mock_redis_service(self):
        """Create mock Redis service for testing."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.incr_by_float = AsyncMock(return_value=0.0)
        mock_redis.expire = AsyncMock(return_value=True)
        return mock_redis

    @pytest.fixture
    def budget_monitor(self, mock_redis_service):
        """Create BudgetMonitor instance with mocked dependencies."""
        return BudgetMonitor(mock_redis_service)

    @pytest.mark.asyncio
    async def test_track_cost_success(self, budget_monitor, mock_redis_service):
        """Test successful cost tracking."""
        # Track a cost
        await budget_monitor.track_cost(0.002, "test_user_123")

        # Verify Redis calls
        assert mock_redis_service.incr_by_float.call_count == 3  # daily, monthly, user

        # Check daily key
        daily_calls = [
            call
            for call in mock_redis_service.incr_by_float.call_args_list
            if "daily" in call[0][0]
        ]
        assert len(daily_calls) == 2  # global daily and user daily

    @pytest.mark.asyncio
    async def test_track_cost_handles_errors(self, budget_monitor, mock_redis_service):
        """Test that cost tracking continues despite Redis errors."""
        # Make Redis fail
        mock_redis_service.incr_by_float.side_effect = Exception("Redis error")

        # Should not raise
        await budget_monitor.track_cost(0.002, "test_user_123")

    @pytest.mark.asyncio
    async def test_check_budget_status_no_warnings(
        self, budget_monitor, mock_redis_service
    ):
        """Test budget status check with no warnings."""
        # Mock low spending
        mock_redis_service.get.side_effect = [
            "0.10",  # daily spending
            "5.00",  # monthly spending
        ]

        status = await budget_monitor.check_budget_status()

        assert status["daily_spent"] == 0.10
        assert status["monthly_spent"] == 5.00
        assert len(status["warnings"]) == 0

    @pytest.mark.asyncio
    async def test_check_budget_status_warning_threshold(
        self, budget_monitor, mock_redis_service
    ):
        """Test budget status check at warning threshold."""
        # Mock 80% daily spending
        mock_redis_service.get.side_effect = [
            "0.40",  # daily spending (80% of $0.50)
            "5.00",  # monthly spending
        ]

        status = await budget_monitor.check_budget_status()

        assert len(status["warnings"]) == 1
        assert status["warnings"][0]["level"] == "warning"
        assert "80%" in status["warnings"][0]["message"]

    @pytest.mark.asyncio
    async def test_check_budget_status_critical_threshold(
        self, budget_monitor, mock_redis_service
    ):
        """Test budget status check at critical threshold."""
        # Mock 90% monthly spending
        mock_redis_service.get.side_effect = [
            "0.30",  # daily spending
            "13.50",  # monthly spending (90% of $15)
        ]

        status = await budget_monitor.check_budget_status()

        assert len(status["warnings"]) == 1
        assert status["warnings"][0]["level"] == "critical"
        assert "90%" in status["warnings"][0]["message"]

    @pytest.mark.asyncio
    async def test_should_allow_request_under_limit(
        self, budget_monitor, mock_redis_service
    ):
        """Test request allowance when under budget."""
        # Mock low spending
        mock_redis_service.get.side_effect = [
            "0.10",  # daily spending
            "5.00",  # monthly spending
        ]

        allowed, reason = await budget_monitor.should_allow_request()

        assert allowed is True
        assert reason is None

    @pytest.mark.asyncio
    async def test_should_allow_request_at_limit(
        self, budget_monitor, mock_redis_service
    ):
        """Test request blocking at 95% budget limit."""
        # Mock 95% monthly spending
        mock_redis_service.get.side_effect = [
            "0.45",  # daily spending
            "14.25",  # monthly spending (95% of $15)
        ]

        allowed, reason = await budget_monitor.should_allow_request()

        assert allowed is False
        assert "Monthly budget nearly exhausted" in reason

    @pytest.mark.asyncio
    async def test_should_allow_request_critical_but_under_95(
        self, budget_monitor, mock_redis_service
    ):
        """Test request still allowed at 90% (critical but under 95%)."""
        # Mock 90% monthly spending
        mock_redis_service.get.side_effect = [
            "0.45",  # daily spending
            "13.50",  # monthly spending (90% of $15)
        ]

        allowed, reason = await budget_monitor.should_allow_request()

        assert allowed is True  # Still allowed at 90%
        assert reason is None

    @pytest.mark.asyncio
    async def test_get_daily_spending(self, budget_monitor, mock_redis_service):
        """Test retrieving daily spending."""
        mock_redis_service.get.return_value = "1.50"

        spending = await budget_monitor.get_daily_spending()

        assert spending == 1.50
        mock_redis_service.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_monthly_spending(self, budget_monitor, mock_redis_service):
        """Test retrieving monthly spending."""
        mock_redis_service.get.return_value = "10.00"

        spending = await budget_monitor.get_monthly_spending()

        assert spending == 10.00
        mock_redis_service.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_daily_spending(self, budget_monitor, mock_redis_service):
        """Test retrieving user-specific daily spending."""
        mock_redis_service.get.return_value = "0.25"

        spending = await budget_monitor.get_user_daily_spending("test_user_123")

        assert spending == 0.25
        mock_redis_service.get.assert_called_once()
        call_args = mock_redis_service.get.call_args[0][0]
        assert "test_user_123" in call_args
        assert "daily" in call_args

    def test_date_key_format(self, budget_monitor):
        """Test date key generation format."""
        date_key = budget_monitor._get_date_key()

        # Should be in YYYY-MM-DD format
        import re

        assert re.match(r"\d{4}-\d{2}-\d{2}", date_key)

    def test_monthly_key_format(self, budget_monitor):
        """Test monthly key generation format."""
        monthly_key = budget_monitor._get_monthly_key()

        # Should contain year and month
        assert "budget:monthly:" in monthly_key
        import re

        assert re.search(r"\d{4}-\d{2}", monthly_key)
