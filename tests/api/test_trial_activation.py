"""Tests for trial activation API endpoint."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from github_analyzer.api.auth.jwt import verify_password
from github_analyzer.database.models import AuditLog, User


@pytest.mark.asyncio
async def test_activate_trial_success(async_client: AsyncClient, test_db):
    """Test successful trial activation."""
    # Create user with invite token
    invite_token = "test_token_123"
    async with test_db() as db:
        user = User(
            user_id="user123",
            email="trial@example.com",
            password_hash="",  # Empty until activation
            full_name="",  # Empty until activation
            is_trial=True,
            trial_plan="professional",
            trial_analyses_limit=500,
            trial_value="$149/month",
            trial_end_date=datetime.now(timezone.utc) + timedelta(days=7),
            invite_token=invite_token,
            invite_token_expires=datetime.now(timezone.utc) + timedelta(hours=48),
            is_active=False,
            analyses_consumed=0,
        )
        db.add(user)
        await db.commit()

    # Mock JWT creation
    with patch(
        "github_analyzer.api.routes.trial_activation.create_token_pair"
    ) as mock_jwt:
        mock_jwt.return_value = {
            "access_token": "fake_access_token",
            "refresh_token": "fake_refresh_token",
        }

        response = await async_client.post(
            "/api/v1/trials/activate",
            json={
                "token": invite_token,
                "password": "SecurePass123!",
                "full_name": "John Doe",
                "company": "Acme Corp",
            },
        )

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert data["access_token"] == "fake_access_token"
    assert data["refresh_token"] == "fake_refresh_token"
    assert data["token_type"] == "bearer"
    assert "user" in data

    # Verify user details in response
    user_data = data["user"]
    assert user_data["email"] == "trial@example.com"
    assert user_data["full_name"] == "John Doe"
    assert user_data["company"] == "Acme Corp"
    assert user_data["trial_plan"] == "professional"
    assert user_data["analyses_limit"] == 500

    # Verify user was updated in database
    async with test_db() as db:
        result = await db.execute(select(User).where(User.user_id == "user123"))
        user = result.scalar_one()

        assert user.is_active is True
        assert user.full_name == "John Doe"
        assert user.company == "Acme Corp"
        assert user.invite_token is None  # Cleared after use
        assert user.invite_token_expires is None
        assert user.password_hash != ""  # Password was set
        assert verify_password("SecurePass123!", user.password_hash)

        # Verify audit log
        result = await db.execute(
            select(AuditLog).where(AuditLog.action == "trial_activated")
        )
        audit = result.scalar_one()
        assert audit.target_user_id == "user123"


@pytest.mark.asyncio
async def test_activate_trial_invalid_token(async_client: AsyncClient, test_db):
    """Test activation with invalid token."""
    response = await async_client.post(
        "/api/v1/trials/activate",
        json={
            "token": "invalid_token",
            "password": "SecurePass123!",
            "full_name": "John Doe",
            "company": "Acme Corp",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Invalid activation token"


@pytest.mark.asyncio
async def test_activate_trial_expired_token(async_client: AsyncClient, test_db):
    """Test activation with expired token."""
    invite_token = "expired_token_123"
    async with test_db() as db:
        user = User(
            user_id="user123",
            email="trial@example.com",
            password_hash="",
            full_name="",
            is_trial=True,
            trial_plan="basic",
            invite_token=invite_token,
            invite_token_expires=datetime.now(timezone.utc)
            - timedelta(hours=1),  # Expired
            is_active=False,
        )
        db.add(user)
        await db.commit()

    response = await async_client.post(
        "/api/v1/trials/activate",
        json={
            "token": invite_token,
            "password": "SecurePass123!",
            "full_name": "John Doe",
            "company": "Acme Corp",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Activation token has expired"


@pytest.mark.asyncio
async def test_activate_trial_already_activated(async_client: AsyncClient, test_db):
    """Test activation of already activated account."""
    invite_token = "already_used_token"
    async with test_db() as db:
        user = User(
            user_id="user123",
            email="trial@example.com",
            password_hash="already_set",
            full_name="Already Set",
            is_trial=True,
            trial_plan="professional",
            invite_token=invite_token,
            invite_token_expires=datetime.now(timezone.utc) + timedelta(hours=1),
            is_active=True,  # Already active
        )
        db.add(user)
        await db.commit()

    response = await async_client.post(
        "/api/v1/trials/activate",
        json={
            "token": invite_token,
            "password": "NewPassword123!",
            "full_name": "New Name",
            "company": "New Company",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Account already activated"
