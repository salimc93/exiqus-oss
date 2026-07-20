"""
Tests for enhanced quota enforcement with proper headers.
"""

import json
from datetime import datetime, timezone
from typing import Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status

from github_analyzer.api.middleware.usage_tracking import UsageTrackingMiddleware


class MockRequest:
    """Mock request object for testing."""

    def __init__(
        self,
        path: str,
        method: str = "POST",
        headers: Optional[Dict[str, str]] = None,
        body: Optional[bytes] = None,
    ):
        self.url = MagicMock()
        self.url.path = path
        self.method = method
        self.headers = headers or {}
        self._body = body
        self.client = MagicMock()
        self.client.host = "127.0.0.1"

    async def body(self) -> bytes:
        """Return request body."""
        return self._body or b""


@pytest.fixture
def middleware():
    """Create middleware instance."""
    app = MagicMock()
    return UsageTrackingMiddleware(app)


class TestQuotaHeaders:
    """Test suite for enhanced quota headers."""

    async def test_quota_exceeded_with_rate_limit_headers(self, middleware):
        """Test that quota exceeded response includes proper rate limit headers."""
        request = MockRequest(
            "/api/v1/analyze", headers={"authorization": "Bearer test-token"}
        )
        call_next = AsyncMock()

        # Fixed test time to make test deterministic
        test_now = datetime(2025, 7, 1, 0, 0, 0, tzinfo=timezone.utc)
        reset_time = datetime(2025, 8, 1, 0, 0, 0, tzinfo=timezone.utc)

        # Mock quota check with detailed information
        quota_check = {
            "can_proceed": False,
            "message": "Monthly API quota exceeded",
            "usage_consumed": 1000,
            "usage_limit": 1000,
            "usage_remaining": 0,
            "reset_timestamp": reset_time,
            "upgrade_options": ["ENTERPRISE"],
            "plan": "PROFESSIONAL",
        }

        with patch.object(middleware, "_extract_user_id", return_value="test-user-123"):
            with patch.object(
                middleware, "_check_usage_quota", return_value=quota_check
            ):
                with patch(
                    "github_analyzer.api.middleware.usage_tracking.datetime"
                ) as mock_dt:
                    mock_dt.now.return_value = test_now
                    mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
                    result = await middleware.dispatch(request, call_next)

        # Verify response
        assert result.status_code == status.HTTP_429_TOO_MANY_REQUESTS

        # Verify response body
        response_data = json.loads(result.body)
        assert "Monthly API quota exceeded" in response_data["detail"]
        assert response_data["quota_info"]["usage_consumed"] == 1000
        assert response_data["quota_info"]["usage_limit"] == 1000

        # Verify rate limit headers
        assert result.headers["X-RateLimit-Limit"] == "1000"
        assert result.headers["X-RateLimit-Remaining"] == "0"
        assert (
            result.headers["X-RateLimit-Reset"] == "1754006400"
        )  # Unix timestamp for 2025-08-01
        assert result.headers["X-RateLimit-Reset-After"] == str(
            int((reset_time - test_now).total_seconds())
        )
        assert result.headers["X-RateLimit-Resource"] == "api_quota"
        assert result.headers["Retry-After"] == str(
            int((reset_time - test_now).total_seconds())
        )

        call_next.assert_not_called()

    async def test_successful_request_with_rate_limit_headers(self, middleware):
        """Test that successful requests include rate limit headers."""
        request = MockRequest(
            "/api/v1/analyze", headers={"authorization": "Bearer test-token"}
        )
        # Create a mock response with mutable headers
        response = MagicMock()
        response.status_code = 200
        response.headers = {}
        call_next = AsyncMock(return_value=response)

        quota_check = {
            "can_proceed": True,
            "usage_consumed": 450,
            "usage_limit": 1000,
            "usage_remaining": 550,
            "reset_timestamp": datetime(2025, 8, 1, 0, 0, 0, tzinfo=timezone.utc),
            "plan": "PROFESSIONAL",
        }

        with patch.object(middleware, "_extract_user_id", return_value="test-user-123"):
            with patch.object(
                middleware, "_check_usage_quota", return_value=quota_check
            ):
                with patch.object(middleware, "_record_usage"):
                    result = await middleware.dispatch(request, call_next)

        # Verify response
        assert result.status_code == 200

        # Verify rate limit headers on successful request
        assert result.headers["X-RateLimit-Limit"] == "1000"
        assert result.headers["X-RateLimit-Remaining"] == "550"
        assert result.headers["X-RateLimit-Reset"] == "1754006400"
        assert result.headers["X-RateLimit-Resource"] == "api_quota"

        call_next.assert_called_once_with(request)

    async def test_batch_request_quota_headers(self, middleware):
        """Test quota headers for batch requests."""
        batch_data = {"repositories": ["repo1", "repo2", "repo3"]}
        request = MockRequest(
            "/api/v1/batch",
            body=json.dumps(batch_data).encode("utf-8"),
            headers={"authorization": "Bearer test-token"},
        )
        # Create a mock response with mutable headers
        response = MagicMock()
        response.status_code = 200
        response.headers = {}
        call_next = AsyncMock(return_value=response)

        quota_check = {
            "can_proceed": True,
            "usage_consumed": 100,
            "usage_limit": 10000,  # Enterprise plan
            "usage_remaining": 9900,
            "reset_timestamp": datetime(2025, 8, 1, 0, 0, 0, tzinfo=timezone.utc),
            "plan": "ENTERPRISE",
        }

        with patch.object(middleware, "_extract_user_id", return_value="test-user-123"):
            with patch.object(
                middleware, "_check_usage_quota", return_value=quota_check
            ):
                with patch.object(middleware, "_record_usage"):
                    result = await middleware.dispatch(request, call_next)

        # Verify headers reflect batch cost
        assert result.headers["X-RateLimit-Limit"] == "10000"
        assert result.headers["X-RateLimit-Remaining"] == "9900"
        assert result.headers["X-RateLimit-Resource"] == "api_quota"

    async def test_near_quota_warning_header(self, middleware):
        """Test warning header when approaching quota limit."""
        request = MockRequest(
            "/api/v1/analyze", headers={"authorization": "Bearer test-token"}
        )
        # Create a mock response with mutable headers
        response = MagicMock()
        response.status_code = 200
        response.headers = {}
        call_next = AsyncMock(return_value=response)

        quota_check = {
            "can_proceed": True,
            "usage_consumed": 950,
            "usage_limit": 1000,
            "usage_remaining": 50,
            "reset_timestamp": datetime(2025, 8, 1, 0, 0, 0, tzinfo=timezone.utc),
            "plan": "PROFESSIONAL",
        }

        with patch.object(middleware, "_extract_user_id", return_value="test-user-123"):
            with patch.object(
                middleware, "_check_usage_quota", return_value=quota_check
            ):
                with patch.object(middleware, "_record_usage"):
                    result = await middleware.dispatch(request, call_next)

        # Verify warning header when >90% quota used
        assert (
            result.headers["X-RateLimit-Warning"]
            == "Quota usage at 95.0% - consider upgrading"
        )
        assert result.headers["X-RateLimit-Remaining"] == "50"

    async def test_untracked_endpoint_no_headers(self, middleware):
        """Test that untracked endpoints don't get rate limit headers."""
        request = MockRequest("/api/v1/health")
        # Create a mock response with mutable headers
        response = MagicMock()
        response.status_code = 200
        response.headers = {}
        call_next = AsyncMock(return_value=response)

        result = await middleware.dispatch(request, call_next)

        # Verify no rate limit headers on untracked endpoints
        # Since untracked endpoints don't set quota_check, no headers should be added
        assert len(result.headers) == 0

    async def test_quota_headers_with_grace_period(self, middleware):
        """Test quota headers when in grace period."""
        request = MockRequest(
            "/api/v1/analyze", headers={"authorization": "Bearer test-token"}
        )
        # Create a mock response with mutable headers
        response = MagicMock()
        response.status_code = 200
        response.headers = {}
        call_next = AsyncMock(return_value=response)

        quota_check = {
            "can_proceed": True,
            "usage_consumed": 1050,
            "usage_limit": 1000,
            "usage_remaining": -50,
            "reset_timestamp": datetime(2025, 8, 1, 0, 0, 0, tzinfo=timezone.utc),
            "plan": "PROFESSIONAL",
            "grace_period": True,
            "grace_remaining": 50,
        }

        with patch.object(middleware, "_extract_user_id", return_value="test-user-123"):
            with patch.object(
                middleware, "_check_usage_quota", return_value=quota_check
            ):
                with patch.object(middleware, "_record_usage"):
                    result = await middleware.dispatch(request, call_next)

        # Verify grace period headers
        assert result.headers["X-RateLimit-Limit"] == "1000"
        assert result.headers["X-RateLimit-Remaining"] == "0"
        assert result.headers["X-RateLimit-Grace-Period"] == "active"
        assert result.headers["X-RateLimit-Grace-Remaining"] == "50"
        assert (
            result.headers["X-RateLimit-Warning"]
            == "Grace period active - 50 requests remaining"
        )

    async def test_different_plan_limits_in_headers(self, middleware):
        """Test that headers reflect correct limits for different plans."""
        test_cases = [
            ("FREE", 0, 0),
            ("BASIC", 0, 0),
            ("PROFESSIONAL", 1000, 750),
            ("ENTERPRISE", 10000, 8500),
        ]

        for plan, limit, consumed in test_cases:
            request = MockRequest(
                "/api/v1/analyze", headers={"authorization": "Bearer test-token"}
            )
            # Create a mock response with mutable headers
            response = MagicMock()
            response.status_code = 200
            response.headers = {}
            call_next = AsyncMock(return_value=response)

            quota_check = {
                "can_proceed": True,
                "usage_consumed": consumed,
                "usage_limit": limit,
                "usage_remaining": limit - consumed,
                "reset_timestamp": datetime(2025, 8, 1, 0, 0, 0, tzinfo=timezone.utc),
                "plan": plan,
            }

            with patch.object(
                middleware, "_extract_user_id", return_value="test-user-123"
            ):
                with patch.object(
                    middleware, "_check_usage_quota", return_value=quota_check
                ):
                    with patch.object(middleware, "_record_usage"):
                        result = await middleware.dispatch(request, call_next)

            if limit > 0:  # Plans with API access
                assert result.headers["X-RateLimit-Limit"] == str(limit)
                assert result.headers["X-RateLimit-Remaining"] == str(limit - consumed)
                assert result.headers["X-RateLimit-Plan"] == plan
            else:  # Free/Basic plans
                # Should still process but with no quota headers
                assert "X-RateLimit-Limit" not in result.headers

    @patch("github_analyzer.api.middleware.usage_tracking.datetime")
    async def test_reset_timestamp_calculation(self, mock_datetime, middleware):
        """Test correct calculation of reset timestamp."""
        # Mock current time to be July 15, 2025
        current_time = datetime(2025, 7, 15, 10, 30, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = current_time
        mock_datetime.timezone = timezone

        request = MockRequest(
            "/api/v1/analyze", headers={"authorization": "Bearer test-token"}
        )
        # Create a mock response with mutable headers
        response = MagicMock()
        response.status_code = 200
        response.headers = {}
        call_next = AsyncMock(return_value=response)

        quota_check = {
            "can_proceed": True,
            "usage_consumed": 500,
            "usage_limit": 1000,
            "usage_remaining": 500,
            "reset_timestamp": datetime(2025, 8, 1, 0, 0, 0, tzinfo=timezone.utc),
            "plan": "PROFESSIONAL",
        }

        with patch.object(middleware, "_extract_user_id", return_value="test-user-123"):
            with patch.object(
                middleware, "_check_usage_quota", return_value=quota_check
            ):
                with patch.object(middleware, "_record_usage"):
                    result = await middleware.dispatch(request, call_next)

        # Verify reset calculations
        expected_seconds_until_reset = int(
            (
                datetime(2025, 8, 1, 0, 0, 0, tzinfo=timezone.utc) - current_time
            ).total_seconds()
        )
        assert result.headers["X-RateLimit-Reset-After"] == str(
            expected_seconds_until_reset
        )
