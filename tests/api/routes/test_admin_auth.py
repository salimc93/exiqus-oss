"""
Test admin authentication endpoint with enhanced security.

This tests the critical admin login functionality that requires:
1. Valid email/password
2. User must be admin in database
3. Correct ADMIN_SECRET environment variable
"""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest
from fastapi import status
from httpx import AsyncClient

from src.github_analyzer.api.auth.jwt import hash_password
from src.github_analyzer.database.models import User


@pytest.fixture
def admin_user():
    """Create a mock admin user."""
    user = User(
        user_id="admin-123",
        email="admin@example.com",
        password_hash=hash_password("SecureAdminPass123!"),
        is_active=True,
        is_verified=True,
        is_admin=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    return user


@pytest.fixture
def non_admin_user():
    """Create a mock non-admin user."""
    user = User(
        user_id="user-456",
        email="user@example.com",
        password_hash=hash_password("UserPass123!"),
        is_active=True,
        is_verified=True,
        is_admin=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    return user


@pytest.fixture
def mock_config_with_secret():
    """Create a mock config with ADMIN_SECRET set."""
    mock_config = Mock()
    mock_config.ADMIN_SECRET = "SuperSecretAdminKey123"
    return mock_config


@pytest.fixture
def mock_config_without_secret():
    """Create a mock config without ADMIN_SECRET."""
    mock_config = Mock()
    mock_config.ADMIN_SECRET = None
    return mock_config


@pytest.fixture
async def admin_test_client(mock_config_with_secret):
    """Create test client with admin config override."""
    from httpx import AsyncClient

    from src.github_analyzer.api.main import app
    from src.github_analyzer.api.routes.admin_auth import get_admin_config

    # Set the override before creating the client
    app.dependency_overrides[get_admin_config] = lambda: mock_config_with_secret

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    # Clean up
    app.dependency_overrides.clear()


class TestAdminAuth:
    """Test admin authentication endpoint."""

    @pytest.mark.asyncio
    async def test_admin_login_success(self, admin_test_client, admin_user):
        """Test successful admin login with all requirements met."""
        with patch(
            "src.github_analyzer.database.operations.UserOperations.get_user_by_email"
        ) as mock_get_user:
            with patch(
                "src.github_analyzer.database.operations.UserOperations.update_last_login"
            ) as mock_update:
                mock_get_user.return_value = admin_user
                mock_update.return_value = None

                response = await admin_test_client.post(
                    "/api/v1/admin/auth/login",
                    json={
                        "email": "admin@example.com",
                        "password": "SecureAdminPass123!",
                        "admin_secret": "SuperSecretAdminKey123",
                    },
                )

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert "access_token" in data
                assert "refresh_token" in data
                assert data["is_admin"] is True
                assert data["email"] == "admin@example.com"
                # Verify last login was updated
                mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_admin_login_wrong_secret(self, admin_test_client, admin_user):
        """Test admin login fails with wrong admin secret."""
        with patch(
            "src.github_analyzer.database.operations.UserOperations.get_user_by_email"
        ) as mock_get_user:
            mock_get_user.return_value = admin_user

            response = await admin_test_client.post(
                "/api/v1/admin/auth/login",
                json={
                    "email": "admin@example.com",
                    "password": "SecureAdminPass123!",
                    "admin_secret": "WrongSecret",
                },
            )

            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert "Invalid admin credentials" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_admin_login_no_secret_configured(
        self, async_client: AsyncClient, admin_user, mock_config_without_secret
    ):
        """Test admin login fails when ADMIN_SECRET is not configured."""
        from src.github_analyzer.api.main import app
        from src.github_analyzer.api.routes.admin_auth import get_admin_config

        # Override config with one that has no ADMIN_SECRET
        app.dependency_overrides[get_admin_config] = lambda: mock_config_without_secret

        try:
            response = await async_client.post(
                "/api/v1/admin/auth/login",
                json={
                    "email": "admin@example.com",
                    "password": "SecureAdminPass123!",
                    "admin_secret": "AnySecret",
                },
            )

            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            assert "Admin authentication not configured" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_admin_login_non_admin_user(self, admin_test_client, non_admin_user):
        """Test that non-admin users cannot login via admin endpoint."""
        with patch(
            "src.github_analyzer.database.operations.UserOperations.get_user_by_email"
        ) as mock_get_user:
            mock_get_user.return_value = non_admin_user

            response = await admin_test_client.post(
                "/api/v1/admin/auth/login",
                json={
                    "email": "user@example.com",
                    "password": "UserPass123!",
                    "admin_secret": "SuperSecretAdminKey123",
                },
            )

            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert "Admin access required" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_admin_login_wrong_password(self, admin_test_client, admin_user):
        """Test admin login fails with wrong password."""
        with patch(
            "src.github_analyzer.database.operations.UserOperations.get_user_by_email"
        ) as mock_get_user:
            mock_get_user.return_value = admin_user

            response = await admin_test_client.post(
                "/api/v1/admin/auth/login",
                json={
                    "email": "admin@example.com",
                    "password": "WrongPassword",
                    "admin_secret": "SuperSecretAdminKey123",
                },
            )

            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert "Invalid admin credentials" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_admin_login_user_not_found(self, admin_test_client):
        """Test admin login fails when user doesn't exist."""
        with patch(
            "src.github_analyzer.database.operations.UserOperations.get_user_by_email"
        ) as mock_get_user:
            mock_get_user.return_value = None

            response = await admin_test_client.post(
                "/api/v1/admin/auth/login",
                json={
                    "email": "nonexistent@example.com",
                    "password": "AnyPassword",
                    "admin_secret": "SuperSecretAdminKey123",
                },
            )

            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert "Invalid admin credentials" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_admin_token_has_shorter_expiry(self, admin_test_client, admin_user):
        """Test that admin tokens have shorter expiry time (2 hours)."""
        with patch(
            "src.github_analyzer.database.operations.UserOperations.get_user_by_email"
        ) as mock_get_user:
            with patch(
                "src.github_analyzer.database.operations.UserOperations.update_last_login"
            ) as mock_update:
                mock_get_user.return_value = admin_user
                mock_update.return_value = None

                response = await admin_test_client.post(
                    "/api/v1/admin/auth/login",
                    json={
                        "email": "admin@example.com",
                        "password": "SecureAdminPass123!",
                        "admin_secret": "SuperSecretAdminKey123",
                    },
                )

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                # Admin tokens expire in 2 hours (7200 seconds)
                assert data["expires_in"] == 7200
