"""Tests for trial management API endpoints."""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from github_analyzer.api.auth.dependencies import require_admin
from github_analyzer.database.models import AuditLog, User


@pytest.mark.asyncio
async def test_list_trial_users(async_client: AsyncClient, test_db):
    """Test listing trial users."""
    # Create admin and trial users
    async with test_db() as db:
        admin = User(
            user_id="admin123",
            email="admin@example.com",
            password_hash="hashed",
            full_name="Admin User",
            is_admin=True,
            is_active=True,
        )
        trial1 = User(
            user_id="trial1",
            email="trial1@example.com",
            password_hash="hashed",
            full_name="Trial User 1",
            is_trial=True,
            trial_plan="basic",
            trial_analyses_limit=100,
            analyses_consumed=25,
            trial_end_date=datetime.now(timezone.utc) + timedelta(days=5),
            is_active=True,
        )
        trial2 = User(
            user_id="trial2",
            email="trial2@example.com",
            password_hash="hashed",
            full_name="Trial User 2",
            is_trial=True,
            trial_plan="enterprise",
            trial_analyses_limit=None,
            analyses_consumed=150,
            trial_end_date=datetime.now(timezone.utc) + timedelta(days=10),
            is_active=False,
        )
        db.add_all([admin, trial1, trial2])
        await db.commit()

    # Mock admin authentication
    async def mock_require_admin():
        return "admin123"

    # Override the dependency
    async_client.app.dependency_overrides[require_admin] = mock_require_admin

    response = await async_client.get(
        "/api/v1/admin/trials/list",
        headers={"Authorization": "Bearer fake-token"},
    )

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 2
    assert data[0]["email"] == "trial1@example.com"
    assert data[0]["trial_plan"] == "basic"
    assert data[0]["analyses_consumed"] == 25
    assert data[1]["email"] == "trial2@example.com"
    assert data[1]["analyses_limit"] is None


@pytest.mark.asyncio
async def test_list_trial_users_active_only(async_client: AsyncClient, test_db):
    """Test listing only active trial users."""
    # Create admin and trial users
    async with test_db() as db:
        admin = User(
            user_id="admin123",
            email="admin@example.com",
            password_hash="hashed",
            full_name="Admin User",
            is_admin=True,
            is_active=True,
        )
        trial1 = User(
            user_id="trial1",
            email="trial1@example.com",
            password_hash="hashed",
            full_name="Trial User 1",
            is_trial=True,
            trial_plan="basic",
            trial_end_date=datetime.now(timezone.utc) + timedelta(days=5),
            is_active=True,
        )
        trial2 = User(
            user_id="trial2",
            email="trial2@example.com",
            password_hash="hashed",
            full_name="Trial User 2",
            is_trial=True,
            trial_plan="enterprise",
            trial_end_date=datetime.now(timezone.utc) + timedelta(days=10),
            is_active=False,
        )
        db.add_all([admin, trial1, trial2])
        await db.commit()

    # Mock admin authentication
    async def mock_require_admin():
        return "admin123"

    async_client.app.dependency_overrides[require_admin] = mock_require_admin

    response = await async_client.get(
        "/api/v1/admin/trials/list?active_only=true",
        headers={"Authorization": "Bearer fake-token"},
    )

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 1
    assert data[0]["email"] == "trial1@example.com"


@pytest.mark.asyncio
async def test_get_trial_user(async_client: AsyncClient, test_db):
    """Test getting a specific trial user."""
    # Create admin and trial user
    async with test_db() as db:
        admin = User(
            user_id="admin123",
            email="admin@example.com",
            password_hash="hashed",
            full_name="Admin User",
            is_admin=True,
            is_active=True,
        )
        trial_user = User(
            user_id="trial123",
            email="trial@example.com",
            password_hash="hashed",
            full_name="Trial User",
            is_trial=True,
            trial_plan="professional",
            trial_analyses_limit=500,
            analyses_consumed=50,
            trial_end_date=datetime.now(timezone.utc) + timedelta(days=5),
            is_active=True,
        )
        db.add_all([admin, trial_user])
        await db.commit()

    # Mock admin authentication
    async def mock_require_admin():
        return "admin123"

    async_client.app.dependency_overrides[require_admin] = mock_require_admin

    response = await async_client.get(
        "/api/v1/admin/trials/trial123",
        headers={"Authorization": "Bearer fake-token"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["user_id"] == "trial123"
    assert data["email"] == "trial@example.com"
    assert data["trial_plan"] == "professional"
    assert data["analyses_consumed"] == 50
    assert data["analyses_limit"] == 500


@pytest.mark.asyncio
async def test_get_trial_user_not_found(async_client: AsyncClient, test_db):
    """Test getting a non-existent trial user."""
    # Create admin user
    async with test_db() as db:
        admin = User(
            user_id="admin123",
            email="admin@example.com",
            password_hash="hashed",
            full_name="Admin User",
            is_admin=True,
            is_active=True,
        )
        db.add(admin)
        await db.commit()

    # Mock admin authentication
    async def mock_require_admin():
        return "admin123"

    async_client.app.dependency_overrides[require_admin] = mock_require_admin

    response = await async_client.get(
        "/api/v1/admin/trials/nonexistent",
        headers={"Authorization": "Bearer fake-token"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


@pytest.mark.asyncio
async def test_extend_trial(async_client: AsyncClient, test_db):
    """Test extending a trial."""
    # Create admin and trial user
    original_expiry = datetime.now(timezone.utc) + timedelta(days=2)
    async with test_db() as db:
        admin = User(
            user_id="admin123",
            email="admin@example.com",
            password_hash="hashed",
            full_name="Admin User",
            is_admin=True,
            is_active=True,
        )
        trial_user = User(
            user_id="trial123",
            email="trial@example.com",
            password_hash="hashed",
            full_name="Trial User",
            is_trial=True,
            trial_plan="professional",
            trial_end_date=original_expiry,
        )
        db.add_all([admin, trial_user])
        await db.commit()

    # Mock admin authentication
    async def mock_require_admin():
        return "admin123"

    async_client.app.dependency_overrides[require_admin] = mock_require_admin

    response = await async_client.post(
        "/api/v1/admin/trials/trial123/extend",
        json={"additional_days": 7},
        headers={"Authorization": "Bearer fake-token"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["user_id"] == "trial123"

    # Verify in database
    async with test_db() as db:
        result = await db.execute(select(User).where(User.user_id == "trial123"))
        user = result.scalar_one()

        # Check that trial was extended by 7 days
        expected_expiry = original_expiry + timedelta(days=7)
        # Ensure both datetimes are timezone-aware
        user_expiry = (
            user.trial_end_date.replace(tzinfo=timezone.utc)
            if user.trial_end_date.tzinfo is None
            else user.trial_end_date
        )
        assert (
            abs((user_expiry - expected_expiry).total_seconds()) < 60
        )  # Within 1 minute

        # Verify audit log
        result = await db.execute(
            select(AuditLog).where(AuditLog.action == "trial_extended")
        )
        audit = result.scalar_one()
        assert audit.target_user_id == "trial123"


@pytest.mark.asyncio
async def test_extend_trial_not_trial_user(async_client: AsyncClient, test_db):
    """Test extending trial for non-trial user."""
    # Create admin and regular user
    async with test_db() as db:
        admin = User(
            user_id="admin123",
            email="admin@example.com",
            password_hash="hashed",
            full_name="Admin User",
            is_admin=True,
            is_active=True,
        )
        regular_user = User(
            user_id="user123",
            email="user@example.com",
            password_hash="hashed",
            full_name="Regular User",
            is_trial=False,
        )
        db.add_all([admin, regular_user])
        await db.commit()

    # Mock admin authentication
    async def mock_require_admin():
        return "admin123"

    async_client.app.dependency_overrides[require_admin] = mock_require_admin

    response = await async_client.post(
        "/api/v1/admin/trials/user123/extend",
        json={"additional_days": 7},
        headers={"Authorization": "Bearer fake-token"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "User is not a trial user"


@pytest.mark.asyncio
async def test_revoke_trial(async_client: AsyncClient, test_db):
    """Test revoking a trial."""
    # Create admin and trial user
    async with test_db() as db:
        admin = User(
            user_id="admin123",
            email="admin@example.com",
            password_hash="hashed",
            full_name="Admin User",
            is_admin=True,
            is_active=True,
        )
        trial_user = User(
            user_id="trial123",
            email="trial@example.com",
            password_hash="hashed",
            full_name="Trial User",
            is_trial=True,
            trial_plan="professional",
            trial_end_date=datetime.now(timezone.utc) + timedelta(days=5),
            is_active=True,
            invite_token="some_token",
        )
        db.add_all([admin, trial_user])
        await db.commit()

    # Mock admin authentication
    async def mock_require_admin():
        return "admin123"

    async_client.app.dependency_overrides[require_admin] = mock_require_admin

    response = await async_client.delete(
        "/api/v1/admin/trials/trial123/revoke",
        headers={"Authorization": "Bearer fake-token"},
    )

    assert response.status_code == 200

    # Verify in database
    async with test_db() as db:
        result = await db.execute(select(User).where(User.user_id == "trial123"))
        user = result.scalar_one()

        assert user.is_active is False
        assert user.invite_token is None
        # Ensure both datetimes are timezone-aware for comparison
        user_trial_end = (
            user.trial_end_date.replace(tzinfo=timezone.utc)
            if user.trial_end_date.tzinfo is None
            else user.trial_end_date
        )
        assert user_trial_end <= datetime.now(timezone.utc)

        # Verify audit log
        result = await db.execute(
            select(AuditLog).where(AuditLog.action == "trial_revoked")
        )
        audit = result.scalar_one()
        assert audit.target_user_id == "trial123"
