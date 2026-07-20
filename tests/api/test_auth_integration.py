"""
Integration tests for authentication routes with database.

This module tests the complete authentication flow using real database
operations to ensure routes work with persistent storage.
"""

from unittest.mock import patch

import pytest

from github_analyzer.database.operations import UserOperations


@pytest.mark.asyncio
async def test_user_registration_and_login_flow(async_client, test_db):
    """Test complete user registration and login flow."""
    # Mock email service
    with patch(
        "github_analyzer.api.services.email_service.EmailService.send_email"
    ) as mock_send:
        mock_send.return_value = True

        # Test user registration
        register_data = {
            "email": "test@example.com",
            "password": "secure_password123",
            "full_name": "Test User",
            "company": "Test Corp",
        }

        response = await async_client.post("/api/v1/auth/register", json=register_data)
        assert response.status_code == 201

    user_data = response.json()
    assert user_data["email"] == "test@example.com"
    assert user_data["full_name"] == "Test User"
    assert user_data["company"] == "Test Corp"
    assert user_data["is_active"] is True
    assert user_data["is_verified"] is False
    assert user_data["usage_quota"] == 100
    assert user_data["usage_consumed"] == 0

    # Test duplicate email registration fails
    with patch(
        "github_analyzer.api.services.email_service.EmailService.send_email"
    ) as mock_send:
        mock_send.return_value = True
        response = await async_client.post("/api/v1/auth/register", json=register_data)
        assert response.status_code == 409
        assert "Email address already registered" in response.json()["detail"]

    # Mark user as verified for login test
    async with test_db() as db_session:
        user = await UserOperations.get_user_by_email(db_session, "test@example.com")
        user.is_verified = True
        await db_session.commit()

    # Test user login
    login_data = {
        "email": "test@example.com",
        "password": "secure_password123",
    }

    response = await async_client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200

    token_data = response.json()
    assert "access_token" in token_data
    assert "refresh_token" in token_data
    assert token_data["token_type"] == "bearer"
    access_token = token_data["access_token"]

    # Test profile access with token
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await async_client.get("/api/v1/auth/profile", headers=headers)
    assert response.status_code == 200

    profile_data = response.json()
    assert profile_data["email"] == "test@example.com"
    assert profile_data["full_name"] == "Test User"

    # Test login with wrong password
    wrong_login_data = {
        "email": "test@example.com",
        "password": "wrong_password",
    }

    response = await async_client.post("/api/v1/auth/login", json=wrong_login_data)
    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]


@pytest.mark.asyncio
async def test_api_key_management_flow(async_client, test_db):
    """Test API key creation and management."""
    # First register and login a user
    with patch(
        "github_analyzer.api.services.email_service.EmailService.send_email"
    ) as mock_send:
        mock_send.return_value = True

        register_data = {
            "email": "apiuser@example.com",
            "password": "secure_password123",
            "full_name": "API User",
            "company": "Test Corp",
        }

        await async_client.post("/api/v1/auth/register", json=register_data)

    # Mark user as verified
    async with test_db() as db_session:
        user = await UserOperations.get_user_by_email(db_session, "apiuser@example.com")
        user.is_verified = True
        await db_session.commit()

    login_data = {
        "email": "apiuser@example.com",
        "password": "secure_password123",
    }

    response = await async_client.post("/api/v1/auth/login", json=login_data)
    token_data = response.json()
    access_token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Test API key creation
    response = await async_client.post(
        "/api/v1/keys/?name=Test API Key&permissions=analyze&permissions=batch",
        json=[],
        headers=headers,
    )
    assert response.status_code == 201

    api_key_response = response.json()
    assert "api_key" in api_key_response
    assert api_key_response["name"] == "Test API Key"
    assert api_key_response["is_active"] is True

    # Test API key listing
    response = await async_client.get("/api/v1/keys/", headers=headers)
    assert response.status_code == 200

    api_keys = response.json()
    assert len(api_keys["keys"]) == 1
    assert api_keys["keys"][0]["name"] == "Test API Key"

    # Test API key deletion
    api_key_id = api_keys["keys"][0]["key_id"]
    response = await async_client.delete(f"/api/v1/keys/{api_key_id}", headers=headers)
    assert response.status_code == 204

    # Verify key is revoked (deactivated, not deleted)
    response = await async_client.get("/api/v1/keys/", headers=headers)
    api_keys = response.json()
    assert len(api_keys["keys"]) == 1  # Key still exists but is deactivated
    assert api_keys["keys"][0]["is_active"] is False


@pytest.mark.asyncio
async def test_password_change_flow(async_client, test_db):
    """Test password change functionality."""
    # Register user
    with patch(
        "github_analyzer.api.services.email_service.EmailService.send_email"
    ) as mock_send:
        mock_send.return_value = True

        register_data = {
            "email": "pwchange@example.com",
            "password": "old_password123",
            "full_name": "Password User",
        }

        await async_client.post("/api/v1/auth/register", json=register_data)

    # Mark user as verified
    async with test_db() as db_session:
        user = await UserOperations.get_user_by_email(
            db_session, "pwchange@example.com"
        )
        user.is_verified = True
        await db_session.commit()

    # Login with old password
    login_data = {
        "email": "pwchange@example.com",
        "password": "old_password123",
    }

    response = await async_client.post("/api/v1/auth/login", json=login_data)
    token_data = response.json()
    access_token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Change password
    password_change_data = {
        "current_password": "old_password123",
        "new_password": "new_password456",
    }

    response = await async_client.post(
        "/api/v1/auth/change-password", json=password_change_data, headers=headers
    )
    assert response.status_code == 204

    # Test login with old password fails
    response = await async_client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 401

    # Test login with new password succeeds
    new_login_data = {
        "email": "pwchange@example.com",
        "password": "new_password456",
    }

    response = await async_client.post("/api/v1/auth/login", json=new_login_data)
    assert response.status_code == 200

    # Test password change with wrong current password
    wrong_password_data = {
        "current_password": "wrong_password",
        "new_password": "another_password",
    }

    response = await async_client.post(
        "/api/v1/auth/change-password", json=wrong_password_data, headers=headers
    )
    assert response.status_code == 400
    assert "Current password is incorrect" in response.json()["detail"]


@pytest.mark.asyncio
async def test_refresh_token_flow(async_client, test_db):
    """Test refresh token functionality."""
    # Register and verify user
    with patch(
        "github_analyzer.api.services.email_service.EmailService.send_email"
    ) as mock_send:
        mock_send.return_value = True

        register_data = {
            "email": "refresh@example.com",
            "password": "secure_password123",
            "full_name": "Refresh User",
            "company": "Test Corp",
        }

        await async_client.post("/api/v1/auth/register", json=register_data)

    # Mark user as verified
    async with test_db() as db_session:
        user = await UserOperations.get_user_by_email(db_session, "refresh@example.com")
        user.is_verified = True
        await db_session.commit()

    # Login to get tokens
    login_data = {
        "email": "refresh@example.com",
        "password": "secure_password123",
    }

    response = await async_client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200

    token_data = response.json()
    # Verify refresh_token is not in body (it's now in httpOnly cookie)
    assert token_data.get("refresh_token") is None
    # Verify refresh_token cookie was set
    assert "refresh_token" in response.cookies

    # Test refresh token endpoint - cookie is sent automatically by httpx
    response = await async_client.post("/api/v1/auth/refresh")
    assert response.status_code == 200

    new_token_data = response.json()
    assert "access_token" in new_token_data
    assert new_token_data["token_type"] == "bearer"
    assert new_token_data["expires_in"] == 3600

    # Verify new access token works
    new_access_token = new_token_data["access_token"]
    headers = {"Authorization": f"Bearer {new_access_token}"}
    response = await async_client.get("/api/v1/auth/profile", headers=headers)
    assert response.status_code == 200

    # Test invalid refresh token (body fallback when no cookie)
    # Clear cookies to test body-based fallback
    async_client.cookies.clear()
    invalid_refresh_data = {"refresh_token": "invalid_token"}
    response = await async_client.post(
        "/api/v1/auth/refresh", json=invalid_refresh_data
    )
    assert response.status_code == 401
    assert "Invalid refresh token" in response.json()["detail"]


@pytest.mark.asyncio
async def test_logout_flow(async_client, test_db):
    """Test user logout functionality."""
    # Register and verify user
    with patch(
        "github_analyzer.api.services.email_service.EmailService.send_email"
    ) as mock_send:
        mock_send.return_value = True

        register_data = {
            "email": "logout@example.com",
            "password": "secure_password123",
            "full_name": "Logout User",
            "company": "Test Corp",
        }

        await async_client.post("/api/v1/auth/register", json=register_data)

    # Mark user as verified
    async with test_db() as db_session:
        user = await UserOperations.get_user_by_email(db_session, "logout@example.com")
        user.is_verified = True
        await db_session.commit()

    # Login
    login_data = {
        "email": "logout@example.com",
        "password": "secure_password123",
    }

    response = await async_client.post("/api/v1/auth/login", json=login_data)
    token_data = response.json()
    access_token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Test logout
    response = await async_client.post("/api/v1/auth/logout", headers=headers)
    assert response.status_code == 204

    # Verify access token still works (logout just clears refresh token)
    response = await async_client.get("/api/v1/auth/profile", headers=headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_unverified_user_restrictions(async_client, test_db):
    """Test that unverified users cannot login."""
    # Register user but don't verify
    with patch(
        "github_analyzer.api.services.email_service.EmailService.send_email"
    ) as mock_send:
        mock_send.return_value = True

        register_data = {
            "email": "unverified@example.com",
            "password": "secure_password123",
            "full_name": "Unverified User",
            "company": "Test Corp",
        }

        response = await async_client.post("/api/v1/auth/register", json=register_data)
        assert response.status_code == 201

    # Try to login without email verification
    login_data = {
        "email": "unverified@example.com",
        "password": "secure_password123",
    }

    response = await async_client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 403
    assert "Email not verified" in response.json()["detail"]


@pytest.mark.asyncio
async def test_profile_update_flow(async_client, test_db):
    """Test profile update functionality."""
    # Register and verify user
    with patch(
        "github_analyzer.api.services.email_service.EmailService.send_email"
    ) as mock_send:
        mock_send.return_value = True

        register_data = {
            "email": "profile@example.com",
            "password": "secure_password123",
            "full_name": "Profile User",
            "company": "Old Company",
        }

        await async_client.post("/api/v1/auth/register", json=register_data)

    # Mark user as verified
    async with test_db() as db_session:
        user = await UserOperations.get_user_by_email(db_session, "profile@example.com")
        user.is_verified = True
        await db_session.commit()

    # Login
    login_data = {
        "email": "profile@example.com",
        "password": "secure_password123",
    }

    response = await async_client.post("/api/v1/auth/login", json=login_data)
    token_data = response.json()
    access_token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Update profile
    update_data = {
        "full_name": "Updated Name",
        "company": "New Company",
    }

    response = await async_client.put(
        "/api/v1/auth/profile", json=update_data, headers=headers
    )
    assert response.status_code == 200

    updated_profile = response.json()
    assert updated_profile["full_name"] == "Updated Name"
    assert updated_profile["company"] == "New Company"
    assert updated_profile["email"] == "profile@example.com"  # Email unchanged

    # Verify changes persist
    response = await async_client.get("/api/v1/auth/profile", headers=headers)
    assert response.status_code == 200
    profile = response.json()
    assert profile["full_name"] == "Updated Name"
    assert profile["company"] == "New Company"


@pytest.mark.asyncio
async def test_weak_password_rejection(async_client, test_db):
    """Test that weak passwords are rejected during registration."""
    with patch(
        "github_analyzer.api.services.email_service.EmailService.send_email"
    ) as mock_send:
        mock_send.return_value = True

        # Test password too short
        register_data = {
            "email": "weak1@example.com",
            "password": "123",  # Too short
            "full_name": "Weak Password User",
            "company": "Test Corp",
        }

        response = await async_client.post("/api/v1/auth/register", json=register_data)
        assert response.status_code == 422  # Validation error

        # Test with empty password field
        register_data["email"] = "weak2@example.com"
        register_data["password"] = ""

        response = await async_client.post("/api/v1/auth/register", json=register_data)
        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_unauthorized_access_without_token(async_client):
    """Test that protected endpoints require authentication."""
    # Try to access profile without token
    response = await async_client.get("/api/v1/auth/profile")
    assert response.status_code == 401

    # Try to change password without token
    password_data = {
        "current_password": "old",
        "new_password": "new",
    }
    response = await async_client.post(
        "/api/v1/auth/change-password", json=password_data
    )
    assert response.status_code == 401

    # Try to create API key without token
    response = await async_client.post("/api/v1/keys/?name=Test", json=[])
    assert response.status_code == 401
