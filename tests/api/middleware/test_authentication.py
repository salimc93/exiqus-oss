"""Tests for authentication middleware."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from github_analyzer.api.middleware.authentication import (
    APIKeyAuthenticationMiddleware,
    APIKeyValidationMiddleware,
)
from github_analyzer.database.models import APIKey


@pytest.fixture
def test_app():
    """Create a test FastAPI app with authentication middleware."""
    app = FastAPI()

    @app.get("/test")
    async def test_endpoint():
        return {"message": "success"}

    @app.get("/protected")
    async def protected_endpoint(request: Request):
        user_id = getattr(request.state, "authenticated_user_id", None)
        return {"user_id": user_id}

    return app


@pytest.fixture
def test_client(test_app):
    """Create a test client with authentication middleware."""
    test_app.add_middleware(APIKeyAuthenticationMiddleware, enforce_quota=True)
    return TestClient(test_app)


@pytest.fixture
def validation_client(test_app):
    """Create a test client with validation-only middleware."""
    test_app.add_middleware(APIKeyValidationMiddleware)
    return TestClient(test_app)


@pytest.fixture
def mock_api_key():
    """Create a mock API key record."""
    return APIKey(
        key_id="ak_test123",
        user_id="user_test123",
        name="Test API Key",
        key_prefix="1234567890",
        key_hash="hashed_key_value",
        salt="random_salt_value",
        permissions='["analyze", "batch"]',
        monthly_quota=1000,
        monthly_usage=100,
        is_active=True,
    )


class TestAPIKeyAuthenticationMiddleware:
    """Test API key authentication middleware functionality."""

    @patch("github_analyzer.api.middleware.authentication.get_db_session")
    async def test_valid_api_key_authentication(
        self, mock_get_db, test_client, mock_api_key
    ):
        """Test successful API key authentication."""
        # Mock database session and service
        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db

        with patch(
            "github_analyzer.api.middleware.authentication.APIKeyService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.validate_api_key.return_value = mock_api_key
            mock_service.check_quota_available.return_value = (True, 900)
            mock_service.increment_usage.return_value = True

            # Make request with API key
            response = test_client.get(
                "/protected",
                headers={"X-API-Key": "gha_1234567890_123456789012345678901"},
            )

            assert response.status_code == 200
            assert response.json()["user_id"] == "user_test123"

            # Verify service calls
            mock_service.validate_api_key.assert_called_once()
            mock_service.check_quota_available.assert_called_once()
            mock_service.increment_usage.assert_called_once_with("ak_test123")

    @patch("github_analyzer.api.middleware.authentication.get_db_session")
    async def test_invalid_api_key(self, mock_get_db, test_client):
        """Test invalid API key handling."""
        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db

        with patch(
            "github_analyzer.api.middleware.authentication.APIKeyService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.validate_api_key.return_value = None  # Invalid key

            response = test_client.get(
                "/test", headers={"X-API-Key": "invalid_key_format"}
            )

            assert response.status_code == 401
            assert response.json()["detail"] == "Invalid API key"
            assert response.json()["error_code"] == "INVALID_API_KEY"

    @patch("github_analyzer.api.middleware.authentication.get_db_session")
    async def test_quota_exceeded(self, mock_get_db, test_client, mock_api_key):
        """Test quota enforcement when limit is exceeded."""
        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db

        with patch(
            "github_analyzer.api.middleware.authentication.APIKeyService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.validate_api_key.return_value = mock_api_key
            mock_service.check_quota_available.return_value = (False, 0)  # No quota

            response = test_client.get(
                "/test", headers={"X-API-Key": "gha_1234567890_123456789012345678901"}
            )

            assert response.status_code == 429
            assert "quota exceeded" in response.json()["detail"].lower()
            assert response.json()["error_code"] == "QUOTA_EXCEEDED"

    async def test_no_api_key_provided(self, test_client):
        """Test request without API key."""
        response = test_client.get("/test")

        # Should proceed without authentication
        assert response.status_code == 200
        assert response.json()["message"] == "success"

    @patch("github_analyzer.api.middleware.authentication.get_db_session")
    async def test_authentication_service_error(self, mock_get_db, test_client):
        """Test handling of authentication service errors."""
        mock_get_db.side_effect = Exception("Database connection failed")

        response = test_client.get(
            "/test", headers={"X-API-Key": "gha_1234567890_123456789012345678901"}
        )

        # When validation fails due to service error, it returns None and middleware treats as invalid key
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid API key"
        assert response.json()["error_code"] == "INVALID_API_KEY"

    @patch("github_analyzer.api.middleware.authentication.get_db_session")
    async def test_quota_check_error_fails_open(
        self, mock_get_db, test_client, mock_api_key
    ):
        """Test that quota check errors fail open (allow request)."""
        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db

        with patch(
            "github_analyzer.api.middleware.authentication.APIKeyService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.validate_api_key.return_value = mock_api_key
            mock_service.check_quota_available.side_effect = Exception(
                "Quota service down"
            )
            mock_service.increment_usage.return_value = True

            response = test_client.get(
                "/test", headers={"X-API-Key": "gha_1234567890_123456789012345678901"}
            )

            # Should succeed despite quota check error
            assert response.status_code == 200

    @patch("github_analyzer.api.middleware.authentication.get_db_session")
    async def test_usage_tracking_error_continues(
        self, mock_get_db, test_client, mock_api_key
    ):
        """Test that usage tracking errors don't block requests."""
        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db

        with patch(
            "github_analyzer.api.middleware.authentication.APIKeyService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.validate_api_key.return_value = mock_api_key
            mock_service.check_quota_available.return_value = (True, 900)
            mock_service.increment_usage.side_effect = Exception(
                "Usage tracking failed"
            )

            response = test_client.get(
                "/test", headers={"X-API-Key": "gha_1234567890_123456789012345678901"}
            )

            # Should succeed despite usage tracking error
            assert response.status_code == 200


class TestAPIKeyValidationMiddleware:
    """Test API key validation middleware functionality."""

    @patch("github_analyzer.api.middleware.authentication.get_db_session")
    async def test_valid_api_key_validation_only(
        self, mock_get_db, validation_client, mock_api_key
    ):
        """Test API key validation without quota enforcement."""
        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db

        with patch(
            "github_analyzer.api.middleware.authentication.APIKeyService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.validate_api_key.return_value = mock_api_key

            response = validation_client.get(
                "/protected",
                headers={"X-API-Key": "gha_1234567890_123456789012345678901"},
            )

            assert response.status_code == 200
            assert response.json()["user_id"] == "user_test123"

            # Should validate but not check quota or track usage
            mock_service.validate_api_key.assert_called_once()
            mock_service.check_quota_available.assert_not_called()
            mock_service.increment_usage.assert_not_called()

    @patch("github_analyzer.api.middleware.authentication.get_db_session")
    async def test_invalid_api_key_continues(self, mock_get_db, validation_client):
        """Test that invalid API key doesn't block request in validation mode."""
        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db

        with patch(
            "github_analyzer.api.middleware.authentication.APIKeyService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.validate_api_key.return_value = None  # Invalid key

            response = validation_client.get("/test")

            # Should continue despite invalid key
            assert response.status_code == 200

    @patch("github_analyzer.api.middleware.authentication.get_db_session")
    async def test_validation_error_continues(self, mock_get_db, validation_client):
        """Test that validation errors don't block requests."""
        mock_get_db.side_effect = Exception("Database error")

        response = validation_client.get(
            "/test", headers={"X-API-Key": "gha_1234567890_123456789012345678901"}
        )

        # Should continue despite validation error
        assert response.status_code == 200

    async def test_no_quota_enforcement(self, validation_client):
        """Test that validation middleware doesn't enforce quotas."""
        test_app = FastAPI()

        # Create middleware without quota enforcement
        middleware = APIKeyValidationMiddleware(test_app)

        # Middleware should not have quota enforcement logic
        assert not hasattr(middleware, "enforce_quota")


class TestMiddlewareIntegration:
    """Test middleware integration scenarios."""

    def test_middleware_initialization(self):
        """Test middleware initialization with different configurations."""
        app = FastAPI()

        # Test with quota enforcement
        auth_middleware = APIKeyAuthenticationMiddleware(app, enforce_quota=True)
        assert auth_middleware.enforce_quota is True

        # Test without quota enforcement
        auth_middleware_no_quota = APIKeyAuthenticationMiddleware(
            app, enforce_quota=False
        )
        assert auth_middleware_no_quota.enforce_quota is False

        # Test validation middleware
        validation_middleware = APIKeyValidationMiddleware(app)
        assert validation_middleware is not None

    @patch("github_analyzer.api.middleware.authentication.get_db_session")
    async def test_request_state_population(
        self, mock_get_db, test_client, mock_api_key
    ):
        """Test that middleware properly populates request state."""
        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db

        with patch(
            "github_analyzer.api.middleware.authentication.APIKeyService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.validate_api_key.return_value = mock_api_key
            mock_service.check_quota_available.return_value = (True, 900)
            mock_service.increment_usage.return_value = True

            # Create a test app to inspect request state
            app = FastAPI()

            @app.get("/inspect")
            async def inspect_state(request: Request):
                return {
                    "authenticated_user_id": getattr(
                        request.state, "authenticated_user_id", None
                    ),
                    "auth_method": getattr(request.state, "auth_method", None),
                    "api_key_record": getattr(request.state, "api_key_record", None)
                    is not None,
                }

            app.add_middleware(APIKeyAuthenticationMiddleware, enforce_quota=True)
            client = TestClient(app)

            response = client.get(
                "/inspect",
                headers={"X-API-Key": "gha_1234567890_123456789012345678901"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["authenticated_user_id"] == "user_test123"
            assert data["auth_method"] == "api_key"
            assert data["api_key_record"] is True
