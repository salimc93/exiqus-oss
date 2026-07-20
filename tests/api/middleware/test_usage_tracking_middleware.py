"""
Comprehensive tests for the UsageTrackingMiddleware.

Tests quota enforcement, usage recording, and error handling.
"""

import json
from typing import Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from github_analyzer.api.middleware.usage_tracking import (
    QuotaEnforcementError,
    UsageTrackingMiddleware,
    check_user_quota,
    enforce_quota,
)
from github_analyzer.database.models import SubscriptionPlan, User


class MockRequest:
    """Mock request object for testing."""

    def __init__(
        self,
        path: str,
        method: str = "POST",
        headers: Optional[Dict[str, str]] = None,
        body: Optional[bytes] = None,
        client_host: Optional[str] = None,
    ):
        self.url = MagicMock()
        self.url.path = path
        self.method = method
        self.headers = headers or {}
        self._body = body
        self.client = MagicMock()
        self.client.host = client_host or "127.0.0.1"

    async def body(self) -> bytes:
        """Return request body."""
        return self._body or b""


@pytest.fixture
def middleware():
    """Create middleware instance."""
    app = MagicMock()
    return UsageTrackingMiddleware(app)


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_user():
    """Create mock user."""
    user = MagicMock(spec=User)
    user.id = "test-user-123"
    user.subscription_plan = SubscriptionPlan.PROFESSIONAL
    user.usage_count = 100
    return user


class TestUsageTrackingMiddleware:
    """Test suite for UsageTrackingMiddleware."""

    async def test_dispatch_untracked_endpoint(self, middleware):
        """Test that untracked endpoints pass through without tracking."""
        request = MockRequest("/api/v1/health")
        response = Response(content="OK", status_code=200)
        call_next = AsyncMock(return_value=response)

        result = await middleware.dispatch(request, call_next)

        assert result == response
        call_next.assert_called_once_with(request)

    async def test_dispatch_unauthenticated_request(self, middleware):
        """Test that unauthenticated requests pass through."""
        request = MockRequest("/api/v1/analyze")
        response = Response(content="OK", status_code=200)
        call_next = AsyncMock(return_value=response)

        with patch.object(middleware, "_extract_user_id", return_value=None):
            result = await middleware.dispatch(request, call_next)

        assert result == response
        call_next.assert_called_once_with(request)

    async def test_dispatch_quota_exceeded(self, middleware, mock_db_session):
        """Test that requests are blocked when quota is exceeded."""
        request = MockRequest(
            "/api/v1/analyze", headers={"authorization": "Bearer test-token"}
        )
        call_next = AsyncMock()

        quota_check = {
            "can_proceed": False,
            "message": "Monthly quota exceeded",
            "usage_consumed": 1000,
            "usage_limit": 1000,
            "upgrade_options": ["ENTERPRISE"],
        }

        with patch.object(middleware, "_extract_user_id", return_value="test-user-123"):
            with patch.object(
                middleware, "_check_usage_quota", return_value=quota_check
            ):
                result = await middleware.dispatch(request, call_next)

        assert result.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        response_data = json.loads(result.body)
        assert "Monthly quota exceeded" in response_data["detail"]
        assert response_data["quota_info"] == quota_check
        assert response_data["upgrade_options"] == ["ENTERPRISE"]
        call_next.assert_not_called()

    async def test_dispatch_successful_request_with_usage_recording(
        self, middleware, mock_db_session, mock_user
    ):
        """Test successful request processing with usage recording."""
        request = MockRequest(
            "/api/v1/analyze", headers={"authorization": "Bearer test-token"}
        )
        response = Response(content="OK", status_code=200)
        call_next = AsyncMock(return_value=response)

        quota_check = {
            "can_proceed": True,
            "usage_consumed": 100,
            "usage_limit": 1000,
        }

        with patch.object(middleware, "_extract_user_id", return_value="test-user-123"):
            with patch.object(
                middleware, "_check_usage_quota", return_value=quota_check
            ):
                with patch.object(middleware, "_record_usage") as mock_record:
                    result = await middleware.dispatch(request, call_next)

        assert result == response
        call_next.assert_called_once_with(request)
        mock_record.assert_called_once()

    async def test_dispatch_failed_request_no_usage_recording(
        self, middleware, mock_db_session
    ):
        """Test that failed requests don't record usage."""
        request = MockRequest(
            "/api/v1/analyze", headers={"authorization": "Bearer test-token"}
        )
        response = Response(content="Error", status_code=400)
        call_next = AsyncMock(return_value=response)

        quota_check = {
            "can_proceed": True,
            "usage_consumed": 100,
            "usage_limit": 1000,
        }

        with patch.object(middleware, "_extract_user_id", return_value="test-user-123"):
            with patch.object(
                middleware, "_check_usage_quota", return_value=quota_check
            ):
                with patch.object(middleware, "_record_usage") as mock_record:
                    result = await middleware.dispatch(request, call_next)

        assert result == response
        call_next.assert_called_once_with(request)
        mock_record.assert_not_called()

    async def test_dispatch_quota_check_error_allows_request(
        self, middleware, mock_db_session
    ):
        """Test that quota check errors don't block requests."""
        request = MockRequest(
            "/api/v1/analyze", headers={"authorization": "Bearer test-token"}
        )
        response = Response(content="OK", status_code=200)
        call_next = AsyncMock(return_value=response)

        with patch.object(middleware, "_extract_user_id", return_value="test-user-123"):
            with patch.object(
                middleware, "_check_usage_quota", side_effect=Exception("DB Error")
            ):
                with patch.object(middleware, "_record_usage") as mock_record:
                    result = await middleware.dispatch(request, call_next)

        assert result == response
        call_next.assert_called_once_with(request)
        mock_record.assert_called_once()

    async def test_dispatch_usage_recording_error_returns_response(
        self, middleware, mock_db_session
    ):
        """Test that usage recording errors don't affect response."""
        request = MockRequest(
            "/api/v1/analyze", headers={"authorization": "Bearer test-token"}
        )
        response = Response(content="OK", status_code=200)
        call_next = AsyncMock(return_value=response)

        quota_check = {
            "can_proceed": True,
            "usage_consumed": 100,
            "usage_limit": 1000,
        }

        with patch.object(middleware, "_extract_user_id", return_value="test-user-123"):
            with patch.object(
                middleware, "_check_usage_quota", return_value=quota_check
            ):
                with patch.object(
                    middleware, "_record_usage", side_effect=Exception("DB Error")
                ):
                    result = await middleware.dispatch(request, call_next)

        assert result == response
        call_next.assert_called_once_with(request)

    def test_get_tracking_config_exact_match(self, middleware):
        """Test exact endpoint matching."""
        config = middleware._get_tracking_config("/api/v1/analyze")
        assert config == {"usage_type": "analysis", "quota_cost": 1}

    def test_get_tracking_config_prefix_match(self, middleware):
        """Test prefix endpoint matching."""
        config = middleware._get_tracking_config("/api/v1/analyze/detailed")
        assert config == {"usage_type": "analysis", "quota_cost": 1}

    def test_get_tracking_config_excluded_endpoint(self, middleware):
        """Test excluded endpoints return None."""
        assert middleware._get_tracking_config("/api/v1/health") is None
        assert middleware._get_tracking_config("/docs") is None
        assert middleware._get_tracking_config("/api/v1/auth/login") is None

    def test_get_tracking_config_untracked_endpoint(self, middleware):
        """Test untracked endpoints return None."""
        assert middleware._get_tracking_config("/api/v1/unknown") is None

    @patch("github_analyzer.api.auth.jwt.extract_user_id")
    async def test_extract_user_id_valid_token(self, mock_extract_user_id, middleware):
        """Test extracting user ID from valid token."""
        request = MockRequest("/", headers={"authorization": "Bearer valid-token"})
        mock_extract_user_id.return_value = "test-user-123"

        user_id = await middleware._extract_user_id(request)

        assert user_id == "test-user-123"
        mock_extract_user_id.assert_called_once_with("valid-token")

    async def test_extract_user_id_no_auth_header(self, middleware):
        """Test extracting user ID with no auth header."""
        request = MockRequest("/")
        user_id = await middleware._extract_user_id(request)
        assert user_id is None

    async def test_extract_user_id_invalid_format(self, middleware):
        """Test extracting user ID with invalid auth format."""
        request = MockRequest("/", headers={"authorization": "Basic invalid"})
        user_id = await middleware._extract_user_id(request)
        assert user_id is None

    @patch("github_analyzer.api.auth.jwt.extract_user_id")
    async def test_extract_user_id_token_error(self, mock_extract_user_id, middleware):
        """Test extracting user ID when token parsing fails."""
        request = MockRequest("/", headers={"authorization": "Bearer invalid-token"})
        mock_extract_user_id.side_effect = Exception("Invalid token")

        user_id = await middleware._extract_user_id(request)

        assert user_id is None
        mock_extract_user_id.assert_called_once_with("invalid-token")

    async def test_check_usage_quota_single_request(self, middleware, mock_db_session):
        """Test quota checking for single request."""
        request = MockRequest("/api/v1/analyze")
        tracking_config = {"usage_type": "analysis", "quota_cost": 1}

        expected_result = {
            "can_proceed": True,
            "usage_consumed": 100,
            "usage_limit": 1000,
        }

        with patch(
            "github_analyzer.api.middleware.usage_tracking.get_db_session"
        ) as mock_get_db:
            mock_get_db.return_value.__aiter__.return_value = iter([mock_db_session])

            with patch.object(
                middleware.subscription_manager,
                "check_usage_limits",
                return_value=expected_result,
            ) as mock_check:
                result = await middleware._check_usage_quota(
                    request, "test-user-123", tracking_config
                )

        assert result == expected_result
        mock_check.assert_called_once_with(mock_db_session, "test-user-123", 1)
        mock_db_session.close.assert_called_once()

    async def test_check_usage_quota_batch_request(self, middleware, mock_db_session):
        """Test quota checking for batch request."""
        batch_data = {"repositories": ["repo1", "repo2", "repo3"]}
        request = MockRequest(
            "/api/v1/batch", body=json.dumps(batch_data).encode("utf-8")
        )
        tracking_config = {"usage_type": "batch_analysis", "quota_cost": 1}

        expected_result = {
            "can_proceed": True,
            "usage_consumed": 100,
            "usage_limit": 1000,
        }

        with patch(
            "github_analyzer.api.middleware.usage_tracking.get_db_session"
        ) as mock_get_db:
            mock_get_db.return_value.__aiter__.return_value = iter([mock_db_session])

            with patch.object(
                middleware.subscription_manager,
                "check_usage_limits",
                return_value=expected_result,
            ) as mock_check:
                result = await middleware._check_usage_quota(
                    request, "test-user-123", tracking_config
                )

        assert result == expected_result
        # Should multiply quota cost by number of repositories
        mock_check.assert_called_once_with(mock_db_session, "test-user-123", 3)

    async def test_check_usage_quota_batch_request_parse_error(
        self, middleware, mock_db_session
    ):
        """Test quota checking when batch request parsing fails."""
        request = MockRequest("/api/v1/batch", body=b"invalid json")
        tracking_config = {"usage_type": "batch_analysis", "quota_cost": 1}

        expected_result = {
            "can_proceed": True,
            "usage_consumed": 100,
            "usage_limit": 1000,
        }

        with patch(
            "github_analyzer.api.middleware.usage_tracking.get_db_session"
        ) as mock_get_db:
            mock_get_db.return_value.__aiter__.return_value = iter([mock_db_session])

            with patch.object(
                middleware.subscription_manager,
                "check_usage_limits",
                return_value=expected_result,
            ) as mock_check:
                result = await middleware._check_usage_quota(
                    request, "test-user-123", tracking_config
                )

        assert result == expected_result
        # Should use default cost when parsing fails
        mock_check.assert_called_once_with(mock_db_session, "test-user-123", 1)

    async def test_check_usage_quota_database_error(self, middleware):
        """Test quota checking when database is unavailable."""
        request = MockRequest("/api/v1/analyze")
        tracking_config = {"usage_type": "analysis", "quota_cost": 1}

        with patch(
            "github_analyzer.api.middleware.usage_tracking.get_db_session"
        ) as mock_get_db:
            mock_get_db.return_value.__aiter__.return_value = iter([])

            result = await middleware._check_usage_quota(
                request, "test-user-123", tracking_config
            )

        assert result == {"allowed": False, "reason": "Database session unavailable"}

    async def test_record_usage_single_request(
        self, middleware, mock_db_session, mock_user
    ):
        """Test usage recording for single request."""
        request = MockRequest(
            "/api/v1/analyze",
            headers={"user-agent": "TestClient/1.0"},
            client_host="192.168.1.1",
        )
        response = Response(status_code=200)
        tracking_config = {"usage_type": "analysis", "quota_cost": 1}
        start_time = 1234567890.0

        with patch(
            "github_analyzer.api.middleware.usage_tracking.get_db_session"
        ) as mock_get_db:
            mock_get_db.return_value.__aiter__.return_value = iter([mock_db_session])

            with patch(
                "github_analyzer.api.middleware.usage_tracking.time.time",
                return_value=start_time + 0.5,
            ):
                with patch(
                    "github_analyzer.api.middleware.usage_tracking.BillingUsageOperations"
                ) as mock_billing_ops:
                    mock_billing_ops.create_usage_record = AsyncMock()
                    with patch(
                        "github_analyzer.api.middleware.usage_tracking.UserOperations"
                    ) as mock_user_ops:
                        mock_user_ops.increment_usage_count = AsyncMock()

                        await middleware._record_usage(
                            request,
                            response,
                            "test-user-123",
                            tracking_config,
                            start_time,
                        )

        # Verify usage record creation
        mock_billing_ops.create_usage_record.assert_called_once()
        call_args = mock_billing_ops.create_usage_record.call_args
        assert call_args.kwargs["user_id"] == "test-user-123"
        assert call_args.kwargs["usage_type"] == "analysis"
        assert call_args.kwargs["usage_count"] == 1

        # Verify metadata
        metadata = json.loads(call_args.kwargs["metadata"])
        assert metadata["endpoint"] == "/api/v1/analyze"
        assert metadata["method"] == "POST"
        assert metadata["response_status"] == 200
        assert metadata["response_time_ms"] == 500
        assert metadata["user_agent"] == "TestClient/1.0"
        assert metadata["ip_address"] == "192.168.1.1"

        # Verify user usage update
        mock_user_ops.increment_usage_count.assert_called_once_with(
            mock_db_session, "test-user-123", 1
        )

    async def test_record_usage_batch_request(
        self, middleware, mock_db_session, mock_user
    ):
        """Test usage recording for batch request."""
        batch_data = {"repositories": ["repo1", "repo2", "repo3", "repo4"]}
        request = MockRequest(
            "/api/v1/batch", body=json.dumps(batch_data).encode("utf-8")
        )
        response = Response(status_code=200)
        tracking_config = {"usage_type": "batch_analysis", "quota_cost": 1}
        start_time = 1234567890.0

        with patch(
            "github_analyzer.api.middleware.usage_tracking.get_db_session"
        ) as mock_get_db:
            mock_get_db.return_value.__aiter__.return_value = iter([mock_db_session])

            with patch(
                "github_analyzer.api.middleware.usage_tracking.time.time",
                return_value=start_time + 1.0,
            ):
                with patch(
                    "github_analyzer.api.middleware.usage_tracking.BillingUsageOperations"
                ) as mock_billing_ops:
                    mock_billing_ops.create_usage_record = AsyncMock()
                    with patch(
                        "github_analyzer.api.middleware.usage_tracking.UserOperations"
                    ) as mock_user_ops:
                        mock_user_ops.increment_usage_count = AsyncMock()

                        await middleware._record_usage(
                            request,
                            response,
                            "test-user-123",
                            tracking_config,
                            start_time,
                        )

        # Verify usage count is based on number of repositories
        call_args = mock_billing_ops.create_usage_record.call_args
        assert call_args.kwargs["usage_count"] == 4

        # Verify user usage update
        mock_user_ops.increment_usage_count.assert_called_once_with(
            mock_db_session, "test-user-123", 4
        )

    async def test_record_usage_user_not_found(self, middleware, mock_db_session):
        """Test usage recording when user is not found."""
        request = MockRequest("/api/v1/analyze")
        response = Response(status_code=200)
        tracking_config = {"usage_type": "analysis", "quota_cost": 1}
        start_time = 1234567890.0

        with patch(
            "github_analyzer.api.middleware.usage_tracking.get_db_session"
        ) as mock_get_db:
            mock_get_db.return_value.__aiter__.return_value = iter([mock_db_session])

            with patch(
                "github_analyzer.api.middleware.usage_tracking.BillingUsageOperations"
            ) as mock_billing_ops:
                mock_billing_ops.create_usage_record = AsyncMock()
                with patch(
                    "github_analyzer.api.middleware.usage_tracking.UserOperations"
                ) as mock_user_ops:
                    mock_user_ops.increment_usage_count = AsyncMock()

                    # Should not raise even when user not found
                    await middleware._record_usage(
                        request,
                        response,
                        "test-user-123",
                        tracking_config,
                        start_time,
                    )

                    # Usage record should still be created
                    mock_billing_ops.create_usage_record.assert_called_once()
                    # And usage should still be incremented
                    mock_user_ops.increment_usage_count.assert_called_once_with(
                        mock_db_session, "test-user-123", 1
                    )

    async def test_get_plan_limits(self, middleware):
        """Test getting plan limits."""
        with patch(
            "github_analyzer.api.middleware.usage_tracking.PlanFeatures.get_plan_limits"
        ) as mock_get_limits:
            expected_limits = {"monthly_api_calls": 1000}
            mock_get_limits.return_value = expected_limits

            limits = await middleware._get_plan_limits(SubscriptionPlan.PROFESSIONAL)

        assert limits == expected_limits
        mock_get_limits.assert_called_once_with(SubscriptionPlan.PROFESSIONAL)


class TestQuotaUtilityFunctions:
    """Test suite for quota utility functions."""

    async def test_check_user_quota_with_db_session(self, mock_db_session):
        """Test check_user_quota with provided database session."""
        expected_result = {
            "can_proceed": True,
            "usage_consumed": 100,
            "usage_limit": 1000,
        }

        with patch(
            "github_analyzer.api.middleware.usage_tracking.SubscriptionManager"
        ) as mock_manager_class:
            mock_manager = mock_manager_class.return_value
            mock_manager.check_usage_limits = AsyncMock(return_value=expected_result)

            result = await check_user_quota("test-user-123", 5, mock_db_session)

        assert result == expected_result
        mock_manager.check_usage_limits.assert_called_once_with(
            mock_db_session, "test-user-123", 5
        )
        # Should not close provided session
        mock_db_session.close.assert_not_called()

    async def test_check_user_quota_without_db_session(self, mock_db_session):
        """Test check_user_quota without database session."""
        expected_result = {
            "can_proceed": True,
            "usage_consumed": 100,
            "usage_limit": 1000,
        }

        with patch(
            "github_analyzer.api.middleware.usage_tracking.get_db_session"
        ) as mock_get_db:
            mock_get_db.return_value.__aiter__.return_value = iter([mock_db_session])

            with patch(
                "github_analyzer.api.middleware.usage_tracking.SubscriptionManager"
            ) as mock_manager_class:
                mock_manager = mock_manager_class.return_value
                mock_manager.check_usage_limits = AsyncMock(
                    return_value=expected_result
                )

                result = await check_user_quota("test-user-123", 5)

        assert result == expected_result
        # Should close created session
        mock_db_session.close.assert_called_once()

    async def test_check_user_quota_no_db_available(self):
        """Test check_user_quota when database is unavailable."""
        with patch(
            "github_analyzer.api.middleware.usage_tracking.get_db_session"
        ) as mock_get_db:
            mock_get_db.return_value.__aiter__.return_value = iter([])

            with pytest.raises(ValueError, match="Unable to acquire database session"):
                await check_user_quota("test-user-123")

    async def test_enforce_quota_allowed(self):
        """Test enforce_quota when quota is not exceeded."""
        quota_result = {
            "can_proceed": True,
            "usage_consumed": 100,
            "usage_limit": 1000,
        }

        with patch(
            "github_analyzer.api.middleware.usage_tracking.check_user_quota",
            return_value=quota_result,
        ):
            # Should not raise
            await enforce_quota("test-user-123", 5)

    async def test_enforce_quota_exceeded(self):
        """Test enforce_quota when quota is exceeded."""
        quota_result = {
            "can_proceed": False,
            "message": "Monthly quota exceeded",
            "usage_consumed": 1000,
            "usage_limit": 1000,
        }

        with patch(
            "github_analyzer.api.middleware.usage_tracking.check_user_quota",
            return_value=quota_result,
        ):
            with pytest.raises(QuotaEnforcementError) as exc_info:
                await enforce_quota("test-user-123", 5)

            assert str(exc_info.value) == "Monthly quota exceeded"
            assert exc_info.value.quota_info == quota_result

    async def test_enforce_quota_no_message(self):
        """Test enforce_quota with no specific message."""
        quota_result = {
            "can_proceed": False,
            "usage_consumed": 1000,
            "usage_limit": 1000,
        }

        with patch(
            "github_analyzer.api.middleware.usage_tracking.check_user_quota",
            return_value=quota_result,
        ):
            with pytest.raises(QuotaEnforcementError) as exc_info:
                await enforce_quota("test-user-123")

            assert str(exc_info.value) == "Quota exceeded"


class TestQuotaEnforcementError:
    """Test suite for QuotaEnforcementError."""

    def test_quota_enforcement_error_creation(self):
        """Test creating QuotaEnforcementError."""
        quota_info = {
            "usage_consumed": 1000,
            "usage_limit": 1000,
            "upgrade_options": ["ENTERPRISE"],
        }

        error = QuotaEnforcementError("Monthly quota exceeded", quota_info)

        assert str(error) == "Monthly quota exceeded"
        assert error.quota_info == quota_info


class TestEdgeCases:
    """Test edge cases and error conditions."""

    async def test_dispatch_with_none_client(self, middleware):
        """Test request with no client information."""
        request = MockRequest(
            "/api/v1/analyze", headers={"authorization": "Bearer test-token"}
        )
        request.client = None
        response = Response(content="OK", status_code=200)
        call_next = AsyncMock(return_value=response)

        quota_check = {"can_proceed": True}

        with patch.object(middleware, "_extract_user_id", return_value="test-user-123"):
            with patch.object(
                middleware, "_check_usage_quota", return_value=quota_check
            ):
                with patch.object(middleware, "_record_usage") as mock_record:
                    result = await middleware.dispatch(request, call_next)

        assert result == response
        # Should still record usage but with None IP
        mock_record.assert_called_once()

    async def test_batch_request_empty_repositories(self, middleware, mock_db_session):
        """Test batch request with empty repositories list."""
        batch_data = {"repositories": []}
        request = MockRequest(
            "/api/v1/batch", body=json.dumps(batch_data).encode("utf-8")
        )
        tracking_config = {"usage_type": "batch_analysis", "quota_cost": 1}

        with patch(
            "github_analyzer.api.middleware.usage_tracking.get_db_session"
        ) as mock_get_db:
            mock_get_db.return_value.__aiter__.return_value = iter([mock_db_session])

            with patch.object(
                middleware.subscription_manager, "check_usage_limits"
            ) as mock_check:
                await middleware._check_usage_quota(
                    request, "test-user-123", tracking_config
                )

        # Should use 0 for empty batch
        mock_check.assert_called_once_with(mock_db_session, "test-user-123", 0)

    async def test_record_usage_database_error(self, middleware, mock_db_session):
        """Test handling database errors during usage recording."""
        request = MockRequest("/api/v1/analyze")
        response = Response(status_code=200)
        tracking_config = {"usage_type": "analysis", "quota_cost": 1}

        with patch(
            "github_analyzer.api.middleware.usage_tracking.get_db_session"
        ) as mock_get_db:
            mock_get_db.return_value.__aiter__.return_value = iter([mock_db_session])

            with patch(
                "github_analyzer.api.middleware.usage_tracking.BillingUsageOperations.create_usage_record",
                side_effect=Exception("Database error"),
            ):
                with pytest.raises(Exception, match="Database error"):
                    await middleware._record_usage(
                        request,
                        response,
                        "test-user-123",
                        tracking_config,
                        1234567890.0,
                    )

        mock_db_session.close.assert_called_once()
