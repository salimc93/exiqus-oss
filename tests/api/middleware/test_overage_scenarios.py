"""
Comprehensive tests for overage scenarios in UsageTrackingMiddleware.
Tests overage detection, grace periods, warning headers, and enforcement.
"""

import json
from datetime import datetime, timezone
from typing import Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from github_analyzer.api.middleware.usage_tracking import UsageTrackingMiddleware
from github_analyzer.database.models import SubscriptionPlan, User


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


@pytest.fixture
def mock_user_professional():
    """Create a mock professional user."""
    user = MagicMock(spec=User)
    user.user_id = "prof_user_123"
    user.email = "professional@example.com"
    user.subscription_plan = SubscriptionPlan.PROFESSIONAL
    user.usage_quota = 500
    user.usage_consumed = 450  # 90% consumed
    return user


@pytest.fixture
def mock_user_enterprise():
    """Create a mock enterprise user."""
    user = MagicMock(spec=User)
    user.user_id = "ent_user_123"
    user.email = "enterprise@example.com"
    user.subscription_plan = SubscriptionPlan.ENTERPRISE
    user.usage_quota = 2000
    user.usage_consumed = 2100  # Over quota
    return user


@pytest.fixture
def mock_user_basic():
    """Create a mock basic user."""
    user = MagicMock(spec=User)
    user.user_id = "basic_user_123"
    user.email = "basic@example.com"
    user.subscription_plan = SubscriptionPlan.BASIC
    user.usage_quota = 100
    user.usage_consumed = 100  # At quota limit
    return user


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.close = AsyncMock()
    return session


class TestOverageScenarios:
    """Test overage scenarios."""

    @patch("github_analyzer.api.middleware.usage_tracking.get_db_session")
    @patch(
        "github_analyzer.api.middleware.usage_tracking.UsageTrackingMiddleware._check_usage_quota"
    )
    @patch(
        "github_analyzer.api.middleware.usage_tracking.UsageTrackingMiddleware._get_overage_headers"
    )
    async def test_overage_headers_are_added(
        self,
        mock_get_overage_headers,
        mock_check_usage_quota,
        mock_get_db,
        middleware,
        mock_db_session,
    ):
        """Test that overage headers are added to the response."""
        mock_get_db.return_value.__aiter__.return_value = [mock_db_session]
        mock_check_usage_quota.return_value = {"can_proceed": True}
        mock_get_overage_headers.return_value = {"X-Test-Header": "Test-Value"}

        request = MockRequest(
            "/api/v1/analyze", headers={"authorization": "Bearer valid_token"}
        )
        response = Response(status_code=200)
        call_next = AsyncMock(return_value=response)

        with patch.object(
            middleware, "_extract_user_id", AsyncMock(return_value="test_user")
        ):
            final_response = await middleware.dispatch(request, call_next)

        assert final_response.headers["X-Test-Header"] == "Test-Value"

    @patch("github_analyzer.api.middleware.usage_tracking.get_db_session")
    @patch(
        "github_analyzer.api.middleware.usage_tracking.UsageTrackingMiddleware._check_usage_quota"
    )
    async def test_request_blocked_when_quota_exceeded(
        self, mock_check_usage_quota, mock_get_db, middleware, mock_db_session
    ):
        """Test that the request is blocked when the quota is exceeded."""
        mock_get_db.return_value.__aiter__.return_value = [mock_db_session]
        mock_check_usage_quota.return_value = {
            "can_proceed": False,
            "message": "Quota exceeded",
            "reset_timestamp": datetime.now(timezone.utc),
        }

        request = MockRequest(
            "/api/v1/analyze", headers={"authorization": "Bearer valid_token"}
        )
        call_next = AsyncMock()

        with patch.object(
            middleware, "_extract_user_id", AsyncMock(return_value="test_user")
        ):
            response = await middleware.dispatch(request, call_next)

        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "Quota exceeded" in json.loads(response.body.decode())["detail"]
        call_next.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
