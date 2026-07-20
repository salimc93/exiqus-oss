"""
Test password reset functionality - critical for account recovery.

This module tests the password reset flow which is vital for security
and user account recovery.
"""

from unittest.mock import patch

import pytest

from github_analyzer.database.operations import UserOperations


@pytest.mark.asyncio
async def test_password_reset_request_flow(async_client, test_db):
    """Test requesting a password reset sends email with reset link."""
    # Register and verify user
    with patch(
        "github_analyzer.api.services.email_service.EmailService.send_email"
    ) as mock_send:
        mock_send.return_value = True

        register_data = {
            "email": "reset@example.com",
            "password": "original_password123",
            "full_name": "Reset User",
            "company": "Test Corp",
        }

        await async_client.post("/api/v1/auth/register", json=register_data)

    # Mark user as verified
    async with test_db() as db_session:
        user = await UserOperations.get_user_by_email(db_session, "reset@example.com")
        user.is_verified = True
        await db_session.commit()

    # Request password reset
    with patch(
        "github_analyzer.api.services.email_service.EmailService.send_password_reset_email"
    ) as mock_send:
        mock_send.return_value = True

        reset_request = {"email": "reset@example.com"}
        response = await async_client.post(
            "/api/v1/auth/forgot-password", json=reset_request
        )
        assert response.status_code == 200
        assert "password reset link has been sent" in response.json()["message"]

        # Verify email was called
        mock_send.assert_called_once()
        call_args = mock_send.call_args[1]
        assert call_args["to_email"] == "reset@example.com"
        assert "reset_url" in call_args


@pytest.mark.asyncio
async def test_password_reset_confirm_flow(async_client, test_db):
    """Test confirming password reset with valid token."""
    import secrets
    import uuid
    from datetime import datetime, timedelta, timezone

    from github_analyzer.api.auth.jwt import hash_password
    from github_analyzer.database.models import PasswordResetToken

    # Register and verify user
    with patch(
        "github_analyzer.api.services.email_service.EmailService.send_email"
    ) as mock_send:
        mock_send.return_value = True

        register_data = {
            "email": "resetconfirm@example.com",
            "password": "original_password123",
            "full_name": "Reset Confirm User",
            "company": "Test Corp",
        }

        await async_client.post("/api/v1/auth/register", json=register_data)

    # Mark user as verified
    async with test_db() as db_session:
        user = await UserOperations.get_user_by_email(
            db_session, "resetconfirm@example.com"
        )
        user.is_verified = True
        await db_session.commit()
        user_id = user.user_id

    # Create a valid reset token manually (mimicking forgot-password flow)
    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_password(raw_token)

    async with test_db() as db_session:
        reset_token = PasswordResetToken(
            token_id=f"prt_{uuid.uuid4().hex[:16]}",
            user_id=user_id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            request_ip=None,
            user_agent=None,
        )
        db_session.add(reset_token)
        await db_session.commit()

    # Confirm password reset
    reset_confirm = {
        "token": raw_token,
        "new_password": "new_secure_password456",
    }

    response = await async_client.post(
        "/api/v1/auth/reset-password", json=reset_confirm
    )
    assert response.status_code == 200
    assert "Password reset successful" in response.json()["message"]

    # Test login with old password fails
    old_login = {
        "email": "resetconfirm@example.com",
        "password": "original_password123",
    }
    response = await async_client.post("/api/v1/auth/login", json=old_login)
    assert response.status_code == 401

    # Test login with new password succeeds
    new_login = {
        "email": "resetconfirm@example.com",
        "password": "new_secure_password456",
    }
    response = await async_client.post("/api/v1/auth/login", json=new_login)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_password_reset_invalid_token(async_client, test_db):
    """Test password reset with invalid token is rejected."""
    # Try to reset with invalid token
    reset_confirm = {
        "token": "invalid_token_12345",
        "new_password": "new_password123",
    }

    response = await async_client.post(
        "/api/v1/auth/reset-password", json=reset_confirm
    )
    assert response.status_code == 400
    assert "Invalid or expired reset token" in response.json()["detail"]


@pytest.mark.asyncio
async def test_password_reset_expired_token(async_client, test_db):
    """Test password reset with expired token is rejected."""
    import secrets
    import uuid
    from datetime import datetime, timedelta, timezone

    from github_analyzer.api.auth.jwt import hash_password
    from github_analyzer.database.models import PasswordResetToken

    # Register and verify user
    with patch(
        "github_analyzer.api.services.email_service.EmailService.send_email"
    ) as mock_send:
        mock_send.return_value = True

        register_data = {
            "email": "expired@example.com",
            "password": "original_password123",
            "full_name": "Expired User",
            "company": "Test Corp",
        }

        await async_client.post("/api/v1/auth/register", json=register_data)

    # Mark user as verified
    async with test_db() as db_session:
        user = await UserOperations.get_user_by_email(db_session, "expired@example.com")
        user.is_verified = True
        await db_session.commit()
        user_id = user.user_id

    # Create an expired reset token (expired 2 hours ago)
    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_password(raw_token)

    async with test_db() as db_session:
        reset_token = PasswordResetToken(
            token_id=f"prt_{uuid.uuid4().hex[:16]}",
            user_id=user_id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc)
            - timedelta(hours=2),  # Already expired
            request_ip=None,
            user_agent=None,
        )
        db_session.add(reset_token)
        await db_session.commit()

    # Try to use expired token
    reset_confirm = {
        "token": raw_token,
        "new_password": "new_password123",
    }

    response = await async_client.post(
        "/api/v1/auth/reset-password", json=reset_confirm
    )
    assert response.status_code == 400
    assert "Invalid or expired reset token" in response.json()["detail"]


@pytest.mark.asyncio
async def test_password_reset_nonexistent_email(async_client):
    """Test password reset for non-existent email returns success (security)."""
    # Request reset for non-existent email
    # Should return success to prevent email enumeration
    reset_request = {"email": "nonexistent@example.com"}

    with patch(
        "github_analyzer.api.services.email_service.EmailService.send_password_reset_email"
    ) as mock_send:
        mock_send.return_value = True

        response = await async_client.post(
            "/api/v1/auth/forgot-password", json=reset_request
        )
        # Should return 200 to prevent email enumeration
        assert response.status_code == 200
        assert "password reset link has been sent" in response.json()["message"]

        # But no email should actually be sent
        mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_password_reset_weak_password_rejected(async_client, test_db):
    """Test that weak passwords are rejected during reset."""
    import secrets
    import uuid
    from datetime import datetime, timedelta, timezone

    from github_analyzer.api.auth.jwt import hash_password
    from github_analyzer.database.models import PasswordResetToken

    # Register and verify user
    with patch(
        "github_analyzer.api.services.email_service.EmailService.send_email"
    ) as mock_send:
        mock_send.return_value = True

        register_data = {
            "email": "weakreset@example.com",
            "password": "original_password123",
            "full_name": "Weak Reset User",
            "company": "Test Corp",
        }

        await async_client.post("/api/v1/auth/register", json=register_data)

    # Mark user as verified
    async with test_db() as db_session:
        user = await UserOperations.get_user_by_email(
            db_session, "weakreset@example.com"
        )
        user.is_verified = True
        await db_session.commit()
        user_id = user.user_id

    # Create a valid reset token
    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_password(raw_token)

    async with test_db() as db_session:
        reset_token = PasswordResetToken(
            token_id=f"prt_{uuid.uuid4().hex[:16]}",
            user_id=user_id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            request_ip=None,
            user_agent=None,
        )
        db_session.add(reset_token)
        await db_session.commit()

    # Try to reset with weak password
    reset_confirm = {
        "token": raw_token,
        "new_password": "123",  # Too short
    }

    response = await async_client.post(
        "/api/v1/auth/reset-password", json=reset_confirm
    )
    assert response.status_code == 422  # Validation error
