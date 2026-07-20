"""
Tests for request logging middleware.

This module tests the custom request logging middleware functionality
including request/response logging and performance metrics.
"""

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from github_analyzer.api.middleware.logging import RequestLoggingMiddleware


class TestRequestLoggingMiddleware:
    """Test request logging middleware."""

    @pytest.fixture
    def app_with_middleware(self):
        """Create a FastAPI app with logging middleware."""
        app = FastAPI()
        app.add_middleware(RequestLoggingMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        @app.get("/error")
        async def error_endpoint():
            raise ValueError("Test error")

        return app

    @pytest.fixture
    def client(self, app_with_middleware):
        """Create a test client with middleware."""
        return TestClient(app_with_middleware)

    def test_successful_request_logging(self, client):
        """Test that successful requests are logged properly."""
        with patch("github_analyzer.api.middleware.logging.logger") as mock_logger:
            response = client.get("/test")

            assert response.status_code == 200

            # Check that info was called for request and response
            assert mock_logger.info.call_count >= 2

            # Check that request was logged
            request_call = mock_logger.info.call_args_list[0]
            assert "Request:" in request_call[0][0]
            assert "GET" in request_call[0][0]
            assert "/test" in request_call[0][0]

            # Check that response was logged
            response_call = mock_logger.info.call_args_list[1]
            assert "Response:" in response_call[0][0]
            assert "200" in response_call[0][0]

    def test_error_request_logging(self, client):
        """Test that error requests are logged properly."""
        with patch("github_analyzer.api.middleware.logging.logger") as mock_logger:
            # The error will be caught by FastAPI's exception handler
            try:
                response = client.get("/error")
                # If we get here, check it's a 500 error
                assert response.status_code == 500
            except ValueError:
                # If the exception bubbles up, that's also expected behavior
                pass

            # Check that error was logged
            assert mock_logger.error.called

            error_call = mock_logger.error.call_args
            assert "Request error:" in error_call[0][0]
            assert "GET" in error_call[0][0]
            assert "/error" in error_call[0][0]

    def test_process_time_header_added(self, client):
        """Test that X-Process-Time header is added to responses."""
        response = client.get("/test")

        assert "X-Process-Time" in response.headers

        # Check that the process time is a valid float
        process_time = float(response.headers["X-Process-Time"])
        assert process_time >= 0

    def test_logging_extra_fields(self, client):
        """Test that logging includes extra fields for structured logging."""
        with patch("github_analyzer.api.middleware.logging.logger") as mock_logger:
            response = client.get(
                "/test?param=value", headers={"User-Agent": "test-agent"}
            )

            assert response.status_code == 200

            # Check request logging extra fields
            request_call = mock_logger.info.call_args_list[0]
            extra = request_call[1].get("extra", {})

            assert extra.get("method") == "GET"
            assert extra.get("path") == "/test"
            assert "param=value" in extra.get("query_params", "")
            assert extra.get("user_agent") == "test-agent"

            # Check response logging extra fields
            response_call = mock_logger.info.call_args_list[1]
            extra = response_call[1].get("extra", {})

            assert extra.get("status_code") == 200
            assert "process_time" in extra
            assert extra.get("method") == "GET"
            assert extra.get("path") == "/test"

    def test_client_ip_extraction(self, app_with_middleware):
        """Test that client IP is properly extracted and logged."""
        client = TestClient(app_with_middleware)

        with patch("github_analyzer.api.middleware.logging.logger") as mock_logger:
            # Test direct client IP
            response = client.get("/test")
            assert response.status_code == 200

            request_call = mock_logger.info.call_args_list[0]
            extra = request_call[1].get("extra", {})
            assert "client_ip" in extra

    def test_middleware_handles_exceptions_gracefully(self, app_with_middleware):
        """Test that middleware handles exceptions and still logs them."""
        client = TestClient(app_with_middleware)

        with patch("github_analyzer.api.middleware.logging.logger") as mock_logger:
            # Make request to error endpoint
            try:
                response = client.get("/error")
                # If we get here, it should be a 500 error
                assert response.status_code == 500
            except ValueError:
                # Exception might bubble up, which is also valid
                pass

            # Should log the error
            assert mock_logger.error.called

            # Check error logging includes exception info
            error_call = mock_logger.error.call_args
            assert error_call[1].get("exc_info") is True


class TestMiddlewareIntegration:
    """Test middleware integration with FastAPI."""

    def test_middleware_preserves_request_response_cycle(self):
        """Test that middleware doesn't interfere with normal request/response."""
        app = FastAPI()
        app.add_middleware(RequestLoggingMiddleware)

        @app.get("/integration-test")
        async def integration_test():
            return {"status": "success", "data": [1, 2, 3]}

        client = TestClient(app)
        response = client.get("/integration-test")

        assert response.status_code == 200
        assert response.json() == {"status": "success", "data": [1, 2, 3]}
        assert "X-Process-Time" in response.headers

    def test_middleware_with_async_endpoints(self):
        """Test middleware compatibility with async endpoints."""
        app = FastAPI()
        app.add_middleware(RequestLoggingMiddleware)

        @app.get("/async-test")
        async def async_test():
            # Simulate async operation
            import asyncio

            await asyncio.sleep(0.001)
            return {"async": True}

        client = TestClient(app)

        with patch("github_analyzer.api.middleware.logging.logger"):
            response = client.get("/async-test")

            assert response.status_code == 200
            assert response.json() == {"async": True}
            assert "X-Process-Time" in response.headers

            # Process time should be > 0.001 seconds
            process_time = float(response.headers["X-Process-Time"])
            assert process_time > 0.001
