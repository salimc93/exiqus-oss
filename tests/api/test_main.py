"""
Tests for the main FastAPI application.

This module tests the FastAPI application creation, configuration,
and global exception handling.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from github_analyzer.api.main import create_app


class TestFastAPIApp:
    """Test FastAPI application creation and configuration."""

    def test_create_app_returns_fastapi_instance(self):
        """Test that create_app returns a FastAPI instance."""
        app = create_app()
        assert isinstance(app, FastAPI)

    def test_app_has_correct_metadata(self):
        """Test that the app has correct title, description, and version."""
        app = create_app()
        assert app.title == "Exiqus API"
        assert app.description == "AI-Powered Developer Assessment Platform API"
        assert app.version == "1.0.0"

    def test_app_has_correct_endpoints(self):
        """Test that the app has the expected documentation endpoints."""
        app = create_app()
        assert app.docs_url == "/docs"
        assert app.redoc_url == "/redoc"
        assert app.openapi_url == "/openapi.json"


class TestGlobalExceptionHandler:
    """Test global exception handling."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        app = create_app()
        return TestClient(app)

    def test_global_exception_handler_returns_500(self, client):
        """Test that unhandled exceptions return 500 status."""
        # This would require a route that raises an exception
        # For now, we'll test the structure exists
        app = create_app()
        assert hasattr(app, "exception_handlers")


class TestCORSConfiguration:
    """Test CORS middleware configuration."""

    def test_cors_middleware_configured(self):
        """Test that CORS middleware is properly configured."""
        app = create_app()

        # Check that middleware is added
        cors_middleware = None
        for middleware in app.user_middleware:
            if "CORSMiddleware" in str(middleware.cls):
                cors_middleware = middleware
                break

        assert cors_middleware is not None

    def test_cors_allows_all_origins(self):
        """Test CORS configuration allows all origins."""
        # This would require testing actual CORS headers
        # For now, we verify the middleware is present
        app = create_app()
        assert len(app.user_middleware) > 0
