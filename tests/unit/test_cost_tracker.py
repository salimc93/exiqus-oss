"""
Unit tests for cost tracking module.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pytest

from github_analyzer.ai.cost_tracker import APIUsage, CostReport, CostTracker


class TestCostTracker:
    """Test cases for CostTracker class."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        with patch("github_analyzer.ai.cost_tracker.get_config") as mock_config:
            config = Mock()
            config.cost.max_daily_cost = 10.0
            config.cost.max_cost_per_analysis = 0.02
            config.cost.alert_threshold = 0.8
            mock_config.return_value = config
            yield config

    @pytest.fixture
    def cost_tracker(self, mock_config):
        """Create CostTracker instance."""
        with patch("github_analyzer.ai.cost_tracker.get_cost_storage") as mock_storage:
            # Mock cost storage to return disabled storage
            mock_storage_instance = Mock()
            mock_storage_instance.enabled = False
            mock_storage.return_value = mock_storage_instance
            return CostTracker()

    def test_cost_tracker_initialization(self, cost_tracker):
        """Test CostTracker initialization."""
        assert cost_tracker is not None
        assert hasattr(cost_tracker, "usage_history")
        assert hasattr(cost_tracker, "max_daily_cost")
        assert hasattr(cost_tracker, "max_cost_per_analysis")

    def test_track_analysis_success(self, cost_tracker):
        """Test successful analysis tracking."""
        usage = APIUsage(
            model="claude-3-haiku-20240307",
            input_tokens=1000,
            output_tokens=500,
            cost=0.015,
            timestamp=datetime.now(timezone.utc),
        )

        cost_tracker.track_analysis(usage)

        assert len(cost_tracker.usage_history) == 1
        assert cost_tracker.usage_history[0] == usage

    def test_calculate_cost_haiku(self, cost_tracker):
        """Test cost calculation for Haiku model."""
        cost = cost_tracker.calculate_cost("claude-3-haiku-20240307", 1000, 500)

        expected_cost = (1000 * 0.00025 + 500 * 0.00125) / 1000  # Haiku pricing
        assert abs(cost - expected_cost) < 0.0001

    def test_calculate_cost_sonnet(self, cost_tracker):
        """Test cost calculation for Sonnet model."""
        cost = cost_tracker.calculate_cost("claude-3-5-sonnet-20241022", 1000, 500)

        expected_cost = (1000 * 0.003 + 500 * 0.015) / 1000  # Sonnet pricing
        assert abs(cost - expected_cost) < 0.0001

    def test_calculate_cost_unknown_model(self, cost_tracker):
        """Test cost calculation for unknown model - should use Haiku pricing as fallback."""
        cost = cost_tracker.calculate_cost("unknown-model", 1000, 500)

        # Should fall back to Haiku pricing
        expected_cost = (1000 * 0.00025 + 500 * 0.00125) / 1000  # Haiku pricing
        assert abs(cost - expected_cost) < 0.0001

    def test_get_daily_usage(self, cost_tracker):
        """Test daily usage calculation."""
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)

        # Add usage from today and yesterday
        today_usage = APIUsage("claude-3-haiku-20240307", 1000, 500, 0.01, now)
        yesterday_usage = APIUsage(
            "claude-3-haiku-20240307", 1000, 500, 0.01, yesterday
        )

        cost_tracker.track_analysis(today_usage)
        cost_tracker.track_analysis(yesterday_usage)

        daily_usage = cost_tracker.get_daily_usage()

        assert daily_usage.total_cost == 0.01  # Only today's usage
        assert daily_usage.total_requests == 1
        assert daily_usage.total_input_tokens == 1000
        assert daily_usage.total_output_tokens == 500

    def test_check_budget_under_limit(self, cost_tracker):
        """Test budget check when under limit."""
        # Add usage that's under the daily limit
        usage = APIUsage(
            "claude-3-haiku-20240307", 1000, 500, 5.0, datetime.now(timezone.utc)
        )
        cost_tracker.track_analysis(usage)

        is_within_budget, reason = cost_tracker.check_budget(0.01)

        assert is_within_budget is True
        assert reason is None

    def test_check_budget_over_daily_limit(self, cost_tracker):
        """Test budget check when over daily limit."""
        # Add usage that exceeds daily limit
        usage = APIUsage(
            "claude-3-haiku-20240307", 1000, 500, 9.99, datetime.now(timezone.utc)
        )
        cost_tracker.track_analysis(usage)

        is_within_budget, reason = cost_tracker.check_budget(0.02)

        assert is_within_budget is False
        assert "daily" in reason.lower()

    def test_check_budget_over_per_analysis_limit(self, cost_tracker):
        """Test budget check when single analysis exceeds limit."""
        is_within_budget, reason = cost_tracker.check_budget(0.05)  # Exceeds 0.02 limit

        assert is_within_budget is False
        assert "analysis" in reason.lower()

    def test_should_alert(self, cost_tracker):
        """Test alert threshold checking."""
        # Add usage that's at 90% of daily limit (above 80% threshold)
        usage = APIUsage(
            "claude-3-haiku-20240307", 1000, 500, 9.0, datetime.now(timezone.utc)
        )
        cost_tracker.track_analysis(usage)

        assert cost_tracker.should_alert() is True

    def test_should_not_alert(self, cost_tracker):
        """Test no alert when usage is low."""
        # Add usage that's at 50% of daily limit (below 80% threshold)
        usage = APIUsage(
            "claude-3-haiku-20240307", 1000, 500, 5.0, datetime.now(timezone.utc)
        )
        cost_tracker.track_analysis(usage)

        assert cost_tracker.should_alert() is False

    def test_get_cost_report(self, cost_tracker):
        """Test cost report generation."""
        now = datetime.now(timezone.utc)

        # Add some usage
        usage1 = APIUsage("claude-3-haiku-20240307", 1000, 500, 0.01, now)
        usage2 = APIUsage("claude-3-sonnet-20240229", 2000, 1000, 0.02, now)

        cost_tracker.track_analysis(usage1)
        cost_tracker.track_analysis(usage2)

        report = cost_tracker.get_cost_report()

        assert isinstance(report, CostReport)
        assert report.total_cost == 0.03
        assert report.total_requests == 2
        assert report.average_cost_per_request == 0.015
        assert len(report.usage_by_model) == 2

    def test_reset_daily_usage(self, cost_tracker):
        """Test resetting daily usage."""
        # Add some usage
        usage = APIUsage(
            "claude-3-haiku-20240307", 1000, 500, 0.01, datetime.now(timezone.utc)
        )
        cost_tracker.track_analysis(usage)

        # Reset usage
        cost_tracker.reset_daily_usage()

        daily_usage = cost_tracker.get_daily_usage()
        assert daily_usage.total_cost == 0.0
        assert daily_usage.total_requests == 0


class TestAPIUsage:
    """Test cases for APIUsage class."""

    def test_api_usage_creation(self):
        """Test APIUsage creation."""
        timestamp = datetime.now(timezone.utc)
        usage = APIUsage(
            model="claude-3-haiku-20240307",
            input_tokens=1000,
            output_tokens=500,
            cost=0.015,
            timestamp=timestamp,
        )

        assert usage.model == "claude-3-haiku-20240307"
        assert usage.input_tokens == 1000
        assert usage.output_tokens == 500
        assert usage.cost == 0.015
        assert usage.timestamp == timestamp

    def test_api_usage_total_tokens(self):
        """Test total tokens calculation."""
        usage = APIUsage(
            model="claude-3-haiku-20240307",
            input_tokens=1000,
            output_tokens=500,
            cost=0.015,
            timestamp=datetime.now(timezone.utc),
        )

        assert usage.total_tokens == 1500

    def test_api_usage_validation(self):
        """Test APIUsage validation."""
        # Test negative tokens
        with pytest.raises(ValueError):
            APIUsage(
                model="claude-3-haiku-20240307",
                input_tokens=-100,
                output_tokens=500,
                cost=0.015,
                timestamp=datetime.now(timezone.utc),
            )

        # Test negative cost
        with pytest.raises(ValueError):
            APIUsage(
                model="claude-3-haiku-20240307",
                input_tokens=1000,
                output_tokens=500,
                cost=-0.015,
                timestamp=datetime.now(timezone.utc),
            )


class TestCostReport:
    """Test cases for CostReport class."""

    def test_cost_report_creation(self):
        """Test CostReport creation."""
        report = CostReport(
            total_cost=0.05,
            total_requests=3,
            average_cost_per_request=0.0167,
            usage_by_model={
                "claude-3-haiku-20240307": 2,
                "claude-3-sonnet-20240229": 1,
            },
            period_start=datetime.now(timezone.utc) - timedelta(days=1),
            period_end=datetime.now(timezone.utc),
        )

        assert report.total_cost == 0.05
        assert report.total_requests == 3
        assert abs(report.average_cost_per_request - 0.0167) < 0.001
        assert len(report.usage_by_model) == 2

    def test_cost_report_to_dict(self):
        """Test CostReport serialization."""
        now = datetime.now(timezone.utc)
        report = CostReport(
            total_cost=0.05,
            total_requests=3,
            average_cost_per_request=0.0167,
            usage_by_model={"claude-3-haiku-20240307": 2},
            period_start=now - timedelta(days=1),
            period_end=now,
        )

        report_dict = report.to_dict()

        assert report_dict["total_cost"] == 0.05
        assert report_dict["total_requests"] == 3
        assert "usage_by_model" in report_dict
        assert "period_start" in report_dict
