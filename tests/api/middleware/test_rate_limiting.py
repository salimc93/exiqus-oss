"""
Tests for rate limiting middleware.

Tests rate limiting logic, client IP extraction, and Redis integration.
"""

import sys
from unittest.mock import AsyncMock, patch

import pytest

if sys.version_info < (3, 11):
    from exceptiongroup import ExceptionGroup  # noqa: F401
else:
    from builtins import ExceptionGroup  # noqa: F401

from github_analyzer.api.middleware.rate_limiting import RateLimitingMiddleware
from github_analyzer.api.services.redis_service import redis_service


class TestRateLimitingMiddleware:
    """Test cases for rate limiting middleware."""

    @pytest.fixture
    def mock_app(self):
        """Mock ASGI application."""
        return AsyncMock()

    @pytest.fixture
    def middleware(self, mock_app):
        """Rate limiting middleware instance."""
        return RateLimitingMiddleware(
            mock_app,
            requests_per_minute=60,
            burst_requests_per_minute=120,
            analysis_requests_per_hour=20,
        )

    @pytest.fixture
    def mock_request(self):
        """Mock HTTP request."""
        request = AsyncMock()
        request.url.path = "/api/v1/test"
        request.client.host = "192.168.1.1"
        request.headers = {}
        request.state = AsyncMock()
        request.state.api_key_record = None
        return request

    @pytest.fixture
    def mock_response(self):
        """Mock HTTP response."""
        response = AsyncMock()
        response.headers = {}
        response.status_code = 200
        return response

    @pytest.fixture
    def mock_call_next(self, mock_response):
        """Mock call_next function."""
        return AsyncMock(return_value=mock_response)

    @pytest.mark.asyncio
    async def test_skip_health_endpoints(self, middleware, mock_call_next):
        """Test that health endpoints skip rate limiting."""
        request = AsyncMock()
        request.url.path = "/api/v1/health"
        request.state = AsyncMock()
        request.state.api_key_record = None

        response = await middleware.dispatch(request, mock_call_next)

        mock_call_next.assert_called_once_with(request)
        assert response == mock_call_next.return_value

    @pytest.mark.asyncio
    async def test_general_endpoint_allowed(
        self, middleware, mock_request, mock_call_next, mock_response
    ):
        """Test general endpoint request within limits."""
        with patch.object(
            redis_service, "increment_rate_limit", AsyncMock(return_value=(30, True))
        ):
            response = await middleware.dispatch(mock_request, mock_call_next)

            mock_call_next.assert_called_once_with(mock_request)
            assert response == mock_response
            assert "X-RateLimit-Limit" in mock_response.headers
            assert "X-RateLimit-Remaining" in mock_response.headers

    @pytest.mark.asyncio
    async def test_general_endpoint_rate_limited(
        self, middleware, mock_request, mock_call_next
    ):
        """Test general endpoint request exceeding limits."""
        # Both general and burst limits exceeded
        with patch.object(
            redis_service,
            "increment_rate_limit",
            AsyncMock(
                side_effect=[
                    (65, False),  # General limit exceeded
                    (125, False),  # Burst limit also exceeded
                ]
            ),
        ):
            # Middleware now returns JSONResponse instead of raising exception
            response = await middleware.dispatch(mock_request, mock_call_next)

            assert response.status_code == 429
            # Parse response body
            import json

            body = json.loads(response.body.decode())
            assert "Rate limit exceeded" in body["error"]
            assert body["endpoint"] == "general"
            mock_call_next.assert_not_called()

    @pytest.mark.asyncio
    async def test_general_endpoint_burst_allowed(
        self, middleware, mock_request, mock_call_next, mock_response
    ):
        """Test general endpoint request allowed under burst limit."""
        with patch.object(
            redis_service,
            "increment_rate_limit",
            AsyncMock(
                side_effect=[
                    (65, False),  # General limit exceeded
                    (100, True),  # But burst limit allows it
                ]
            ),
        ):
            response = await middleware.dispatch(mock_request, mock_call_next)

            mock_call_next.assert_called_once_with(mock_request)
            assert response == mock_response
            # Headers should reflect the burst limit that was applied
            assert response.headers["X-RateLimit-Limit"] == "120"
            assert response.headers["X-RateLimit-Remaining"] == "20"

    @pytest.mark.asyncio
    async def test_analysis_endpoint_allowed(
        self, middleware, mock_call_next, mock_response
    ):
        """Test analysis endpoint request within limits."""
        request = AsyncMock()
        request.url.path = "/api/v1/analyze"
        request.client.host = "192.168.1.1"
        request.headers = {}
        request.state = AsyncMock()
        request.state.api_key_record = None

        with patch.object(
            redis_service, "increment_rate_limit", AsyncMock(return_value=(5, True))
        ) as mock_increment:
            response = await middleware.dispatch(request, mock_call_next)

            mock_call_next.assert_called_once_with(request)
            assert response == mock_response

            # Verify analysis-specific rate limit was used
            mock_increment.assert_called_once()
            call_args = mock_increment.call_args
            assert call_args[1]["window_seconds"] == 3600  # 1 hour
            assert call_args[1]["limit"] == 20

    @pytest.mark.asyncio
    async def test_analysis_endpoint_rate_limited(self, middleware, mock_call_next):
        """Test analysis endpoint request exceeding limits."""
        request = AsyncMock()
        request.url.path = "/api/v1/analyze"
        request.client.host = "192.168.1.1"
        request.headers = {}
        request.state = AsyncMock()
        request.state.api_key_record = None

        with patch.object(
            redis_service, "increment_rate_limit", AsyncMock(return_value=(15, False))
        ):
            # Middleware now returns JSONResponse instead of raising exception
            response = await middleware.dispatch(request, mock_call_next)

            assert response.status_code == 429
            # Parse response body
            import json

            body = json.loads(response.body.decode())
            assert "Analysis requests limited to 20 per hour" in body["message"]
            assert body["endpoint"] == "analysis"
            assert response.headers["Retry-After"] == "3600"
            mock_call_next.assert_not_called()

    def test_get_client_ip_direct(self, middleware):
        """Test client IP extraction from direct connection."""
        request = AsyncMock()
        request.headers = {}
        request.client.host = "192.168.1.100"

        ip = middleware._get_client_ip(request)

        assert ip == "192.168.1.100"

    def test_get_client_ip_forwarded_for(self, middleware):
        """Test client IP extraction from X-Forwarded-For header."""
        request = AsyncMock()
        request.headers = {"X-Forwarded-For": "203.0.113.1, 192.168.1.1, 10.0.0.1"}
        request.client.host = "10.0.0.1"

        # Set TRUSTED_PROXY for this test
        import os

        original_value = os.environ.get("TRUSTED_PROXY")
        os.environ["TRUSTED_PROXY"] = "true"

        try:
            ip = middleware._get_client_ip(request)
            assert ip == "203.0.113.1"  # First non-private IP in the chain
        finally:
            # Restore original value
            if original_value is None:
                os.environ.pop("TRUSTED_PROXY", None)
            else:
                os.environ["TRUSTED_PROXY"] = original_value

    def test_get_client_ip_real_ip(self, middleware):
        """Test client IP extraction from X-Real-IP header."""
        request = AsyncMock()
        request.headers = {"X-Real-IP": "203.0.113.50"}
        request.client.host = "10.0.0.1"

        # Set TRUSTED_PROXY for this test
        import os

        original_value = os.environ.get("TRUSTED_PROXY")
        os.environ["TRUSTED_PROXY"] = "true"

        try:
            ip = middleware._get_client_ip(request)
            assert ip == "203.0.113.50"
        finally:
            # Restore original value
            if original_value is None:
                os.environ.pop("TRUSTED_PROXY", None)
            else:
                os.environ["TRUSTED_PROXY"] = original_value

    def test_get_client_ip_no_client(self, middleware):
        """Test client IP extraction when no client info available."""
        request = AsyncMock()
        request.headers = {}
        request.client = None

        ip = middleware._get_client_ip(request)

        assert ip == "unknown"

    def test_get_client_ip_priority(self, middleware):
        """Test client IP extraction header priority."""
        request = AsyncMock()
        request.headers = {"X-Forwarded-For": "203.0.113.1", "X-Real-IP": "203.0.113.2"}
        request.client.host = "10.0.0.1"

        # Set TRUSTED_PROXY for this test
        import os

        original_value = os.environ.get("TRUSTED_PROXY")
        os.environ["TRUSTED_PROXY"] = "true"

        try:
            ip = middleware._get_client_ip(request)
            # X-Forwarded-For takes priority
            assert ip == "203.0.113.1"
        finally:
            # Restore original value
            if original_value is None:
                os.environ.pop("TRUSTED_PROXY", None)
            else:
                os.environ["TRUSTED_PROXY"] = original_value

    @pytest.mark.asyncio
    async def test_middleware_initialization(self, mock_app):
        """Test middleware initialization with custom parameters."""
        middleware = RateLimitingMiddleware(
            mock_app,
            requests_per_minute=30,
            burst_requests_per_minute=60,
            analysis_requests_per_hour=5,
        )

        assert middleware.requests_per_minute == 30
        assert middleware.burst_requests_per_minute == 60
        assert middleware.analysis_requests_per_hour == 5

    @pytest.mark.asyncio
    async def test_rate_limit_headers_general(
        self, middleware, mock_request, mock_call_next, mock_response
    ):
        """Test rate limit headers for general endpoints."""
        with patch.object(
            redis_service, "increment_rate_limit", AsyncMock(return_value=(25, True))
        ):
            await middleware.dispatch(mock_request, mock_call_next)

            assert mock_response.headers["X-RateLimit-Limit"] == "60"
            assert mock_response.headers["X-RateLimit-Remaining"] == "35"

    @pytest.mark.asyncio
    async def test_rate_limit_headers_analysis(
        self, middleware, mock_call_next, mock_response
    ):
        """Test rate limit headers for analysis endpoints."""
        request = AsyncMock()
        request.url.path = "/api/v1/analyze"
        request.client.host = "192.168.1.1"
        request.headers = {}
        request.state = AsyncMock()
        request.state.api_key_record = None

        with patch.object(
            redis_service, "increment_rate_limit", AsyncMock(return_value=(3, True))
        ):
            await middleware.dispatch(request, mock_call_next)

            assert mock_response.headers["X-RateLimit-Limit"] == "20"
            assert mock_response.headers["X-RateLimit-Remaining"] == "17"
