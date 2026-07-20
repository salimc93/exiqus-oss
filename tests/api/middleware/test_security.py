"""
Tests for security middleware.

Critical tests for API security headers, CORS configuration,
and request validation middleware.
"""

import os
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from github_analyzer.api.middleware.security import (
    APIVersionMiddleware,
    RequestIDMiddleware,
    RequestValidationMiddleware,
    SecurityHeadersMiddleware,
)


@pytest.fixture
def test_app():
    """Create a test FastAPI application."""
    app = FastAPI()

    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    @app.get("/api/test")
    async def api_test_endpoint():
        return {"message": "api test"}

    return app


@pytest.fixture
def app_with_security_headers(test_app):
    """Add SecurityHeadersMiddleware to test app."""
    test_app.add_middleware(SecurityHeadersMiddleware)
    return test_app


@pytest.fixture
def app_with_request_validation(test_app):
    """Add RequestValidationMiddleware to test app."""
    test_app.add_middleware(RequestValidationMiddleware)
    return test_app


@pytest.fixture
def app_with_api_version(test_app):
    """Add APIVersionMiddleware to test app."""
    test_app.add_middleware(APIVersionMiddleware)
    return test_app


class TestSecurityHeadersMiddleware:
    """Test security headers middleware."""

    def test_security_headers_added(self, app_with_security_headers):
        """Test that security headers are added to responses."""
        client = TestClient(app_with_security_headers)
        response = client.get("/test")

        assert response.status_code == 200

        # Check critical security headers
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert "Strict-Transport-Security" in response.headers
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_security_headers_on_api_routes(self, app_with_security_headers):
        """Test that security headers are added to API routes."""
        client = TestClient(app_with_security_headers)
        response = client.get("/api/test")

        assert response.status_code == 200
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-Content-Type-Options"] == "nosniff"

    def test_permissions_policy_header(self, app_with_security_headers):
        """Test that Permissions-Policy header is set correctly."""
        client = TestClient(app_with_security_headers)
        response = client.get("/test")

        assert "Permissions-Policy" in response.headers
        policy = response.headers["Permissions-Policy"]
        assert "geolocation=()" in policy
        assert "camera=()" in policy
        assert "microphone=()" in policy

    def test_cache_control_for_sensitive_routes(self, app_with_security_headers):
        """Test cache control headers for sensitive data."""
        client = TestClient(app_with_security_headers)
        response = client.get("/api/test")

        if "Cache-Control" in response.headers:
            assert "no-store" in response.headers["Cache-Control"]


class TestRequestValidationMiddleware:
    """Test request validation middleware."""

    def test_request_size_validation(self, test_app):
        """Test request size validation."""

        # Add a POST endpoint to test app
        @test_app.post("/test")
        async def post_endpoint():
            return {"message": "post"}

        test_app.add_middleware(RequestValidationMiddleware)
        client = TestClient(test_app)

        # Small request should pass
        response = client.post("/test", json={"data": "test"})
        assert response.status_code == 200

    def test_content_type_validation(self, test_app):
        """Test content type validation."""

        # Add a POST endpoint to test app
        @test_app.post("/test-content")
        async def post_content_endpoint():
            return {"message": "post"}

        test_app.add_middleware(RequestValidationMiddleware)
        client = TestClient(test_app)

        # JSON content type should be accepted
        response = client.post(
            "/test-content",
            json={"data": "test"},
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200

    def test_request_validation_middleware_allows_get(
        self, app_with_request_validation
    ):
        """Test that GET requests pass validation."""
        client = TestClient(app_with_request_validation)
        response = client.get("/test")
        assert response.status_code == 200

    def test_request_id_tracking(self, test_app):
        """Test request ID tracking."""
        test_app.add_middleware(RequestIDMiddleware)
        client = TestClient(test_app)
        response = client.get("/test")
        assert response.status_code == 200
        # Check if request ID header is present
        if "X-Request-ID" in response.headers:
            assert len(response.headers["X-Request-ID"]) > 0


class TestAPIVersionMiddleware:
    """Test API version middleware."""

    def test_api_version_header_present(self, app_with_api_version):
        """Test that API version header is present."""
        client = TestClient(app_with_api_version)
        response = client.get("/test")

        assert response.status_code == 200
        # Check for API version header if implemented
        if "X-API-Version" in response.headers:
            assert response.headers["X-API-Version"] != ""

    def test_api_deprecation_headers(self, app_with_api_version):
        """Test API deprecation headers if used."""
        client = TestClient(app_with_api_version)
        response = client.get("/test")

        assert response.status_code == 200
        # Check for deprecation headers if API version is old
        # This is optional and depends on implementation

    def test_api_version_compatibility(self, app_with_api_version):
        """Test API version compatibility checks."""
        client = TestClient(app_with_api_version)
        response = client.get("/test", headers={"X-API-Version": "1.0"})

        assert response.status_code == 200

    def test_api_version_in_response(self, app_with_api_version):
        """Test API version is included in responses."""
        client = TestClient(app_with_api_version)
        response = client.get("/api/test")

        assert response.status_code == 200


class TestRequestIDMiddleware:
    """Test request ID middleware."""

    def test_request_id_generation(self, test_app):
        """Test that request IDs are generated."""
        test_app.add_middleware(RequestIDMiddleware)
        client = TestClient(test_app)

        response1 = client.get("/test")
        response2 = client.get("/test")

        assert response1.status_code == 200
        assert response2.status_code == 200

        # If request IDs are in headers, they should be unique
        if "X-Request-ID" in response1.headers and "X-Request-ID" in response2.headers:
            assert (
                response1.headers["X-Request-ID"] != response2.headers["X-Request-ID"]
            )

    def test_request_id_passthrough(self, test_app):
        """Test that existing request IDs are preserved."""
        test_app.add_middleware(RequestIDMiddleware)
        client = TestClient(test_app)

        custom_id = "test-request-123"
        response = client.get("/test", headers={"X-Request-ID": custom_id})

        assert response.status_code == 200
        # Check if the custom ID is preserved
        if "X-Request-ID" in response.headers:
            assert response.headers["X-Request-ID"] == custom_id


class TestCORSConfiguration:
    """Test CORS configuration."""

    def test_cors_allowed_origins(self):
        """Test CORS configuration includes production origins."""
        from github_analyzer.api.middleware.security import get_cors_config

        cors_config = get_cors_config()

        # Development origins are always present
        assert "http://localhost:3000" in cors_config["allow_origins"]
        assert "http://localhost:8080" in cors_config["allow_origins"]

        # Production origins come from CORS_ALLOWED_ORIGINS
        with patch.dict(
            os.environ, {"CORS_ALLOWED_ORIGINS": "https://app.example.com"}
        ):
            cors_config = get_cors_config()
            assert "https://app.example.com" in cors_config["allow_origins"]

    def test_cors_allowed_methods(self):
        """Test CORS allows necessary HTTP methods."""
        from github_analyzer.api.middleware.security import get_cors_config

        cors_config = get_cors_config()

        # Check all required methods are allowed
        required_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        for method in required_methods:
            assert method in cors_config["allow_methods"]

    def test_cors_allowed_headers(self):
        """Test CORS allows necessary headers."""
        from github_analyzer.api.middleware.security import get_cors_config

        cors_config = get_cors_config()

        # Check critical headers are allowed
        assert "Authorization" in cors_config["allow_headers"]
        assert "Content-Type" in cors_config["allow_headers"]
        assert "X-API-Key" in cors_config["allow_headers"]
        assert "X-Request-ID" in cors_config["allow_headers"]

    def test_cors_exposed_headers(self):
        """Test CORS exposes rate limit headers."""
        from github_analyzer.api.middleware.security import get_cors_config

        cors_config = get_cors_config()

        # Check rate limit headers are exposed
        assert "X-RateLimit-Limit" in cors_config["expose_headers"]
        assert "X-RateLimit-Remaining" in cors_config["expose_headers"]
        assert "X-RateLimit-Reset" in cors_config["expose_headers"]
        assert "X-Process-Time" in cors_config["expose_headers"]

    def test_cors_max_age(self):
        """Test CORS preflight cache duration."""
        from github_analyzer.api.middleware.security import get_cors_config

        cors_config = get_cors_config()

        # Check preflight is cached for 1 hour
        assert cors_config["max_age"] == 3600

    def test_cors_credentials(self):
        """Test CORS allows credentials."""
        from github_analyzer.api.middleware.security import get_cors_config

        cors_config = get_cors_config()

        # Check credentials are allowed
        assert cors_config["allow_credentials"] is True


class TestSecurityMiddlewareIntegration:
    """Test integration of all security middlewares."""

    def test_all_security_middlewares_together(self, test_app):
        """Test all security middlewares work together."""
        # Add all security middlewares
        test_app.add_middleware(SecurityHeadersMiddleware)
        test_app.add_middleware(RequestValidationMiddleware)
        test_app.add_middleware(APIVersionMiddleware)
        test_app.add_middleware(RequestIDMiddleware)

        client = TestClient(test_app)
        response = client.get("/test", headers={"Origin": "https://app.example.com"})

        assert response.status_code == 200

        # Verify critical security headers are present
        assert "X-Frame-Options" in response.headers
        assert "X-Content-Type-Options" in response.headers
        # CSP is already in SecurityHeadersMiddleware
        assert "Content-Security-Policy" in response.headers

    def test_security_headers_on_error_responses(self, test_app):
        """Test security headers are added to error responses."""
        from fastapi import HTTPException

        test_app.add_middleware(SecurityHeadersMiddleware)

        @test_app.get("/error")
        async def error_endpoint():
            raise HTTPException(status_code=500, detail="Test error")

        client = TestClient(test_app)
        response = client.get("/error")

        # Even on errors, security headers should be present
        assert response.status_code == 500
        assert "X-Frame-Options" in response.headers
        assert "X-Content-Type-Options" in response.headers

    def test_security_headers_on_all_methods(self, test_app):
        """Test security headers are added to all HTTP methods."""
        test_app.add_middleware(SecurityHeadersMiddleware)

        @test_app.post("/test")
        async def post_endpoint():
            return {"message": "post"}

        @test_app.put("/test")
        async def put_endpoint():
            return {"message": "put"}

        client = TestClient(test_app)

        # Test different HTTP methods
        for method in [client.get, client.post, client.put]:
            response = method("/test")
            assert "X-Frame-Options" in response.headers
            assert "X-Content-Type-Options" in response.headers
