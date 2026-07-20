"""
Simple tests for overage headers functionality.

Tests the _get_overage_headers method in isolation.
"""

from unittest.mock import AsyncMock, patch

import pytest

from github_analyzer.api.middleware.usage_tracking import UsageTrackingMiddleware


@pytest.fixture
def middleware():
    """Create middleware instance."""
    app = AsyncMock()
    return UsageTrackingMiddleware(app)


class TestOverageHeaders:
    """Test overage header generation."""

    @patch("github_analyzer.api.middleware.usage_tracking.get_db_session")
    @patch("github_analyzer.api.middleware.usage_tracking.UsageTracker")
    async def test_get_overage_headers_professional_80_percent(
        self, mock_usage_tracker, mock_get_db, middleware
    ):
        """Test headers for professional user at 80% usage."""
        # Mock database session
        mock_db = AsyncMock()
        mock_get_db.return_value.__aiter__.return_value = [mock_db]

        # Mock overage status
        mock_usage_tracker.get_overage_status = AsyncMock(
            return_value={
                "user_id": "prof_user_123",
                "plan": "professional",
                "billing_period": "2025-07",
                "usage_consumed": 400,
                "usage_quota": 500,
                "overage_amount": 0,
                "overage_cost": "0.00",
                "overage_rate": "0.20",
                "supports_overage": True,
                "warning_level": "high",
                "usage_percentage": 80.0,
            }
        )

        # Get headers
        headers = await middleware._get_overage_headers("prof_user_123")

        # Verify headers
        assert headers["X-Overage-Allowed"] == "true"
        assert headers["X-Overage-Rate"] == "$0.20"
        assert headers["X-Usage-Percentage"] == "80.0%"
        assert headers["X-Usage-Warning-Level"] == "high"
        assert "Usage at 80.0%" in headers["X-Usage-Warning"]
        assert headers["X-Billing-Period"] == "2025-07"

    @patch("github_analyzer.api.middleware.usage_tracking.get_db_session")
    @patch("github_analyzer.api.middleware.usage_tracking.UsageTracker")
    async def test_get_overage_headers_enterprise_overage(
        self, mock_usage_tracker, mock_get_db, middleware
    ):
        """Test headers for enterprise user in overage."""
        # Mock database session
        mock_db = AsyncMock()
        mock_get_db.return_value.__aiter__.return_value = [mock_db]

        # Mock overage status
        mock_usage_tracker.get_overage_status = AsyncMock(
            return_value={
                "user_id": "ent_user_123",
                "plan": "enterprise",
                "billing_period": "2025-07",
                "usage_consumed": 2100,
                "usage_quota": 2000,
                "overage_amount": 100,
                "overage_cost": "10.00",
                "overage_rate": "0.10",
                "supports_overage": True,
                "warning_level": "exceeded",
                "usage_percentage": 105.0,
            }
        )

        # Get headers
        headers = await middleware._get_overage_headers("ent_user_123")

        # Verify headers
        assert headers["X-Overage-Allowed"] == "true"
        assert headers["X-Overage-Rate"] == "$0.10"
        assert headers["X-Overage-Amount"] == "100"
        assert headers["X-Overage-Cost"] == "$10.00"
        assert headers["X-Overage-Status"] == "active"
        assert headers["X-Usage-Warning-Level"] == "exceeded"
        assert "Quota exceeded" in headers["X-Usage-Warning"]
        assert "charges of $10.00" in headers["X-Usage-Warning"]

    @patch("github_analyzer.api.middleware.usage_tracking.get_db_session")
    @patch("github_analyzer.api.middleware.usage_tracking.UsageTracker")
    async def test_get_overage_headers_basic_no_overage(
        self, mock_usage_tracker, mock_get_db, middleware
    ):
        """Test headers for basic user with no overage support."""
        # Mock database session
        mock_db = AsyncMock()
        mock_get_db.return_value.__aiter__.return_value = [mock_db]

        # Mock overage status
        mock_usage_tracker.get_overage_status = AsyncMock(
            return_value={
                "user_id": "basic_user_123",
                "plan": "basic",
                "billing_period": "2025-07",
                "usage_consumed": 100,
                "usage_quota": 100,
                "overage_amount": 0,
                "overage_cost": "0.00",
                "overage_rate": "0.00",
                "supports_overage": False,
                "warning_level": "exceeded",
                "usage_percentage": 100.0,
            }
        )

        # Get headers
        headers = await middleware._get_overage_headers("basic_user_123")

        # Verify headers
        assert headers["X-Overage-Allowed"] == "false"
        assert headers["X-Usage-Warning-Level"] == "exceeded"
        assert "Upgrade to Professional or Enterprise" in headers["X-Usage-Warning"]

    @patch("github_analyzer.api.middleware.usage_tracking.get_db_session")
    @patch("github_analyzer.api.middleware.usage_tracking.UsageTracker")
    async def test_get_overage_headers_error_handling(
        self, mock_usage_tracker, mock_get_db, middleware
    ):
        """Test headers when overage status fails."""
        # Mock database session
        mock_db = AsyncMock()
        mock_get_db.return_value.__aiter__.return_value = [mock_db]

        # Mock overage status to raise error
        mock_usage_tracker.get_overage_status = AsyncMock(
            side_effect=Exception("Database error")
        )

        # Get headers - should return empty dict on error
        headers = await middleware._get_overage_headers("user_123")

        # Verify empty headers returned
        assert headers == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
