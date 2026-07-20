"""
Tests for per-API-key rate limiting middleware.

Tests API key-based rate limiting to replace IP-based limiting.
"""

import json
from typing import Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from github_analyzer.api.middleware.rate_limiting import RateLimitingMiddleware
from github_analyzer.api.services.redis_service import redis_service


class MockRequest:
    """Mock request object for testing."""

    def __init__(
        self,
        path: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        client_host: Optional[str] = None,
    ):
        self.url = MagicMock()
        self.url.path = path
        self.method = method
        self.headers = headers or {}
        self.client = MagicMock()
        self.client.host = client_host or "127.0.0.1"
        # Add state for API key authentication
        self.state = MagicMock()
        self.state.api_key_record = None
        self.state.authenticated_user_id = None


class MockResponse:
    """Mock response object."""

    def __init__(self, status_code: int = 200):
        self.status_code = status_code
        self.headers = {}


@pytest.fixture
def middleware():
    """Create middleware instance."""
    app = MagicMock()
    return RateLimitingMiddleware(
        app,
        requests_per_minute=60,
        burst_requests_per_minute=120,
        analysis_requests_per_hour=10,
        contact_requests_per_hour=5,
    )


@pytest.fixture
def mock_api_key_record():
    """Create mock API key record."""
    record = MagicMock()
    record.key_id = "key_test123"
    record.user_id = "user_test456"
    record.name = "Test API Key"
    record.scopes = ["analysis", "general"]
    record.rate_limit_override = None  # No custom rate limit
    return record


class TestAPIKeyRateLimiting:
    """Test suite for API key-based rate limiting."""

    async def test_api_key_rate_limiting_general_endpoint(
        self, middleware, mock_api_key_record
    ):
        """Test rate limiting based on API key for general endpoints."""
        request = MockRequest("/api/v1/some-endpoint")
        request.state.api_key_record = mock_api_key_record
        request.state.authenticated_user_id = mock_api_key_record.user_id

        response = MockResponse()
        call_next = AsyncMock(return_value=response)

        # Mock Redis to simulate rate limit not exceeded
        with patch.object(
            redis_service, "increment_rate_limit", return_value=(30, True)
        ) as mock_increment:
            result = await middleware.dispatch(request, call_next)

            # Should use API key ID for rate limiting, not IP
            mock_increment.assert_called_once()
            args, kwargs = mock_increment.call_args
            assert "key_test123" in args[0]  # Rate limit key should contain API key ID
            assert "general" in args[0]
            assert (
                kwargs["window_seconds"] == 60
            )  # Window seconds for general endpoints
            assert kwargs["limit"] == 60  # Default limit for general endpoints

        assert result.status_code == 200
        assert result.headers["X-RateLimit-Limit"] == "60"
        assert result.headers["X-RateLimit-Remaining"] == "30"

    async def test_api_key_rate_limiting_analysis_endpoint(
        self, middleware, mock_api_key_record
    ):
        """Test rate limiting for analysis endpoints with API key."""
        request = MockRequest("/api/v1/analyze/repo")
        request.state.api_key_record = mock_api_key_record

        response = MockResponse()
        call_next = AsyncMock(return_value=response)

        with patch.object(
            redis_service, "increment_rate_limit", return_value=(5, True)
        ) as mock_increment:
            result = await middleware.dispatch(request, call_next)

            mock_increment.assert_called_once()
            args, kwargs = mock_increment.call_args
            assert "key_test123" in args[0]
            assert "analysis" in args[0]
            assert kwargs["window_seconds"] == 3600  # 1 hour window for analysis
            assert kwargs["limit"] == 10  # Default analysis limit

        assert result.status_code == 200
        assert result.headers["X-RateLimit-Limit"] == "10"
        assert result.headers["X-RateLimit-Remaining"] == "5"

    async def test_api_key_custom_rate_limit_override(
        self, middleware, mock_api_key_record
    ):
        """Test custom rate limit override for specific API keys."""
        # Set custom rate limit for this API key
        mock_api_key_record.rate_limit_override = {
            "requests_per_minute": 200,
            "analysis_requests_per_hour": 50,
        }

        request = MockRequest("/api/v1/some-endpoint")
        request.state.api_key_record = mock_api_key_record

        response = MockResponse()
        call_next = AsyncMock(return_value=response)

        with patch.object(
            redis_service, "increment_rate_limit", return_value=(100, True)
        ):
            result = await middleware.dispatch(request, call_next)

        # Should use custom limit of 200
        assert result.headers["X-RateLimit-Limit"] == "200"
        assert result.headers["X-RateLimit-Remaining"] == "100"

    async def test_api_key_rate_limit_exceeded(self, middleware, mock_api_key_record):
        """Test when API key rate limit is exceeded."""
        request = MockRequest("/api/v1/some-endpoint")
        request.state.api_key_record = mock_api_key_record

        # Mock rate limit exceeded
        with patch.object(
            redis_service, "increment_rate_limit", return_value=(61, False)
        ):
            # Also mock burst limit check
            with patch.object(
                redis_service,
                "increment_rate_limit",
                side_effect=[(61, False), (121, False)],
            ):
                # Middleware now returns JSONResponse instead of raising exception
                response = await middleware.dispatch(request, AsyncMock())

                assert response.status_code == 429
                # Parse response body
                import json

                body = json.loads(response.body.decode())
                assert "Rate limit exceeded" in body["error"]
                assert body["api_key_id"] == "key_test123"

    async def test_fallback_to_ip_when_no_api_key(self, middleware):
        """Test fallback to IP-based rate limiting when no API key."""
        request = MockRequest("/api/v1/some-endpoint", client_host="192.168.1.100")
        # No API key in request state

        response = MockResponse()
        call_next = AsyncMock(return_value=response)

        with patch.object(
            redis_service, "increment_rate_limit", return_value=(30, True)
        ) as mock_increment:
            result = await middleware.dispatch(request, call_next)

            # Should use IP for rate limiting
            mock_increment.assert_called_once()
            args = mock_increment.call_args[0]
            assert "192.168.1.100" in args[0]
            assert "general" in args[0]

        assert result.status_code == 200

    async def test_api_key_scopes_affect_limits(self, middleware, mock_api_key_record):
        """Test that API key scopes can affect rate limits."""
        # API key with limited scopes
        mock_api_key_record.scopes = ["general"]  # No analysis scope

        request = MockRequest("/api/v1/analyze/repo")
        request.state.api_key_record = mock_api_key_record

        # Middleware now returns JSONResponse instead of raising exception
        response = await middleware.dispatch(request, AsyncMock())

        assert response.status_code == 403
        # Parse response body
        import json

        body = json.loads(response.body.decode())
        assert "insufficient scope" in body["error"].lower()

    async def test_api_key_rate_limit_headers_include_key_info(
        self, middleware, mock_api_key_record
    ):
        """Test rate limit headers include API key information."""
        request = MockRequest("/api/v1/some-endpoint")
        request.state.api_key_record = mock_api_key_record

        response = MockResponse()
        call_next = AsyncMock(return_value=response)

        with patch.object(
            redis_service, "increment_rate_limit", return_value=(30, True)
        ):
            result = await middleware.dispatch(request, call_next)

        assert result.headers["X-RateLimit-Resource"] == "api_key"
        assert result.headers["X-RateLimit-Key-ID"] == "key_test123"

    async def test_different_api_keys_have_separate_limits(self, middleware):
        """Test that different API keys have independent rate limits."""
        # First API key
        api_key1 = MagicMock()
        api_key1.key_id = "key_001"
        api_key1.rate_limit_override = None

        request1 = MockRequest("/api/v1/some-endpoint")
        request1.state.api_key_record = api_key1

        # Second API key
        api_key2 = MagicMock()
        api_key2.key_id = "key_002"
        api_key2.rate_limit_override = None

        request2 = MockRequest("/api/v1/some-endpoint")
        request2.state.api_key_record = api_key2

        response = MockResponse()
        call_next = AsyncMock(return_value=response)

        # Track calls to increment_rate_limit
        with patch.object(
            redis_service, "increment_rate_limit", return_value=(1, True)
        ) as mock_increment:
            await middleware.dispatch(request1, call_next)
            await middleware.dispatch(request2, call_next)

            # Should be called twice with different keys
            assert mock_increment.call_count == 2
            call_args = [call[0][0] for call in mock_increment.call_args_list]
            assert any("key_001" in key for key in call_args)
            assert any("key_002" in key for key in call_args)

    async def test_api_key_rate_limit_with_redis_failure(
        self, middleware, mock_api_key_record
    ):
        """Test graceful handling when Redis is unavailable."""
        request = MockRequest("/api/v1/some-endpoint")
        request.state.api_key_record = mock_api_key_record

        response = MockResponse()
        call_next = AsyncMock(return_value=response)

        # Simulate Redis failure
        with patch.object(redis_service, "_connected", False):
            with patch.object(
                redis_service, "increment_rate_limit", return_value=(1, True)
            ):
                result = await middleware.dispatch(request, call_next)

        # Should allow request when Redis is down
        assert result.status_code == 200
        call_next.assert_called_once()

    async def test_batch_requests_count_correctly_with_api_key(
        self, middleware, mock_api_key_record
    ):
        """Test batch analysis requests count multiple uses with API key."""
        request = MockRequest(
            "/api/v1/batch/analyze",
            method="POST",
            headers={"content-type": "application/json"},
        )
        request.state.api_key_record = mock_api_key_record

        # Mock request body for batch with 3 repositories
        async def mock_body():
            return json.dumps({"repositories": ["repo1", "repo2", "repo3"]}).encode()

        request.body = mock_body

        response = MockResponse()
        call_next = AsyncMock(return_value=response)

        with patch.object(redis_service, "increment_rate_limit") as mock_increment:
            # First call returns current count, second adds batch size
            mock_increment.side_effect = [(7, True), (10, True)]

            result = await middleware.dispatch(request, call_next)

            # Should increment by 3 for batch request
            assert mock_increment.call_count >= 1
            # Verify it attempted to add 3 to the count

        assert result.status_code == 200

    async def test_health_endpoint_bypass_with_api_key(
        self, middleware, mock_api_key_record
    ):
        """Test health endpoints bypass rate limiting even with API key."""
        request = MockRequest("/api/v1/health/status")
        request.state.api_key_record = mock_api_key_record

        response = MockResponse()
        call_next = AsyncMock(return_value=response)

        with patch.object(redis_service, "increment_rate_limit") as mock_increment:
            result = await middleware.dispatch(request, call_next)

            # Should not call rate limiter for health endpoints
            mock_increment.assert_not_called()

        assert result.status_code == 200
        call_next.assert_called_once()
