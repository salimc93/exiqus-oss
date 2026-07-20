"""Tests for account deletion functionality."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from github_analyzer.database.models import SubscriptionStatus
from github_analyzer.database.operations import APIKeyOperations, UserOperations


@pytest.mark.asyncio
async def test_soft_delete_user(test_db):
    """Test soft deletion of user account."""
    # Create database session
    async with test_db() as db_session:
        # Create a test user
        user = await UserOperations.create_user(
            db_session,
            email="delete_test@example.com",
            password="TestPassword123!",
            full_name="Delete Test User",
            company="Test Corp",
        )
        await db_session.commit()

        # Create an API key for the user
        await APIKeyOperations.create_api_key(
            db_session,
            user_id=user.user_id,
            name="Test Key",
            key_hash="test_hash",
            key_prefix="test_",
            salt="test_salt",
            permissions=["read", "write"],
        )
        await db_session.commit()

        # Soft delete the user
        success = await UserOperations.soft_delete_user(db_session, user.user_id)
        await db_session.commit()

        assert success is True

        # Verify user is deactivated
        deleted_user = await UserOperations.get_user_by_id(db_session, user.user_id)
        assert deleted_user.is_active is False
        assert deleted_user.subscription_status == SubscriptionStatus.CANCELED
        assert deleted_user.deletion_requested_at is not None

        # Verify API key is deactivated
        api_keys = await APIKeyOperations.get_user_api_keys(
            db_session, user.user_id, active_only=False
        )
        assert len(api_keys) == 1
        assert api_keys[0].is_active is False


@pytest.mark.asyncio
async def test_hard_delete_user(test_db):
    """Test hard deletion of user account."""
    # Create database session
    async with test_db() as db_session:
        # Create a test user
        user = await UserOperations.create_user(
            db_session,
            email="hard_delete_test@example.com",
            password="TestPassword123!",
            full_name="Hard Delete Test User",
            company="Test Corp",
        )
        await db_session.commit()

        user_id = user.user_id

        # Hard delete the user
        success = await UserOperations.hard_delete_user(db_session, user_id)
        await db_session.commit()

        assert success is True

        # Verify user is completely gone
        deleted_user = await UserOperations.get_user_by_id(db_session, user_id)
        assert deleted_user is None


@pytest.mark.asyncio
async def test_get_users_pending_deletion(test_db):
    """Test getting users pending deletion after grace period."""
    # Create database session
    async with test_db() as db_session:
        # Create users with different deletion dates
        user1 = await UserOperations.create_user(
            db_session,
            email="pending1@example.com",
            password="TestPassword123!",
            full_name="Pending User 1",
        )

        user2 = await UserOperations.create_user(
            db_session,
            email="pending2@example.com",
            password="TestPassword123!",
            full_name="Pending User 2",
        )

        await db_session.commit()

        # Soft delete user1 and manually set deletion date to 31 days ago
        await UserOperations.soft_delete_user(db_session, user1.user_id)
        user1.deletion_requested_at = datetime.now(timezone.utc) - timedelta(days=31)

        # Soft delete user2 with recent deletion date
        await UserOperations.soft_delete_user(db_session, user2.user_id)

        await db_session.commit()

        # Get users pending deletion (older than 30 days)
        pending_users = await UserOperations.get_users_pending_deletion(db_session)

        # Only user1 should be in the list
        assert len(pending_users) == 1
        assert pending_users[0].user_id == user1.user_id


@pytest.mark.asyncio
async def test_delete_account_endpoint(async_client: AsyncClient, test_db):
    """Test the delete account API endpoint."""
    # Mock email service to avoid sending actual emails
    with patch(
        "github_analyzer.api.services.email_service.EmailService.send_email"
    ) as mock_send:
        mock_send.return_value = True

        # Register a user
        register_data = {
            "email": "api_delete_test@example.com",
            "password": "TestPassword123!",
            "full_name": "API Delete Test",
            "company": "Test Corp",
        }

        register_response = await async_client.post(
            "/api/v1/auth/register", json=register_data
        )
        assert register_response.status_code == 201

    # Mark user as verified since we're not actually clicking the verification link
    async with test_db() as db_session:
        user = await UserOperations.get_user_by_email(
            db_session, register_data["email"]
        )
        user.is_verified = True
        await db_session.commit()

    # Login to get token
    login_data = {
        "email": register_data["email"],
        "password": register_data["password"],
    }

    login_response = await async_client.post("/api/v1/auth/login", json=login_data)
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    # Try to delete account without password
    delete_response = await async_client.request(
        method="DELETE",
        url="/api/v1/auth/account",
        headers={"Authorization": f"Bearer {token}"},
        json={},
    )
    assert delete_response.status_code == 400

    # Try to delete account with wrong password
    delete_response = await async_client.request(
        method="DELETE",
        url="/api/v1/auth/account",
        headers={"Authorization": f"Bearer {token}"},
        json={"password": "WrongPassword123!"},
    )
    assert delete_response.status_code == 401

    # Delete account with correct password
    delete_response = await async_client.request(
        method="DELETE",
        url="/api/v1/auth/account",
        headers={"Authorization": f"Bearer {token}"},
        json={"password": register_data["password"]},
    )
    assert delete_response.status_code == 204

    # Try to login again - should fail
    login_response = await async_client.post("/api/v1/auth/login", json=login_data)
    assert login_response.status_code == 401


@pytest.mark.asyncio
async def test_deactivate_all_user_keys(test_db):
    """Test deactivating all API keys for a user."""
    # Create database session
    async with test_db() as db_session:
        # Create a user
        user = await UserOperations.create_user(
            db_session,
            email="key_test@example.com",
            password="TestPassword123!",
            full_name="Key Test User",
        )
        await db_session.commit()

        # Create multiple API keys
        for i in range(3):
            await APIKeyOperations.create_api_key(
                db_session,
                user_id=user.user_id,
                name=f"Test Key {i}",
                key_hash=f"hash_{i}",
                key_prefix=f"prefix_{i}",
                salt=f"salt_{i}",
                permissions=["read"],
            )
        await db_session.commit()

        # Deactivate all keys
        count = await APIKeyOperations.deactivate_all_user_keys(
            db_session, user.user_id
        )
        await db_session.commit()

        assert count == 3

        # Verify all keys are inactive
        api_keys = await APIKeyOperations.get_user_api_keys(
            db_session, user.user_id, active_only=False
        )
        assert len(api_keys) == 3
        assert all(not key.is_active for key in api_keys)
