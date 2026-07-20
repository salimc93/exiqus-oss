"""Tests for trial admin API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from github_analyzer.api.auth.dependencies import require_admin
from github_analyzer.database.models import AuditLog, User


@pytest.mark.asyncio
async def test_grant_trial_success(async_client: AsyncClient, test_db):
    """Test successful trial grant."""
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

    # Mock admin authentication - mock the entire require_admin dependency
    async def mock_require_admin():
        return "admin123"

    # Override on the app instance that the client is using
    async_client.app.dependency_overrides[require_admin] = mock_require_admin

    try:
        response = await async_client.post(
            "/api/v1/admin/trials/grant",
            json={
                "email": "newuser@example.com",
                "trial_days": 7,
                "trial_plan": "professional",
            },
            headers={"Authorization": "Bearer fake-token"},
        )
    finally:
        # Clean up the override
        async_client.app.dependency_overrides.pop(require_admin, None)

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "user_id" in data
    assert "invite_link" in data
    assert "expires_at" in data
    assert "trial_details" in data

    # Verify trial details
    assert data["trial_details"]["plan"] == "professional"
    assert data["trial_details"]["limit"] == 500
    assert data["trial_details"]["value"] == "Professional"
    assert data["trial_details"]["days"] == 7

    # Verify invite link format
    assert "/activate?token=" in data["invite_link"]

    # Verify user was created in database
    async with test_db() as db:
        result = await db.execute(
            select(User).where(User.email == "newuser@example.com")
        )
        user = result.scalar_one()

        assert user.is_trial is True
        assert user.trial_plan == "professional"
        assert user.trial_analyses_limit == 500
        assert user.is_active is False  # Not active until activation
        assert user.invite_token is not None

        # Verify audit log
        result = await db.execute(
            select(AuditLog).where(AuditLog.action == "trial_granted")
        )
        audit = result.scalar_one()
        assert audit.admin_id == "admin123"
        assert audit.target_email == "newuser@example.com"


@pytest.mark.asyncio
async def test_grant_trial_enterprise_unlimited(async_client: AsyncClient, test_db):
    """Test granting enterprise trial with unlimited analyses."""
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

    try:
        response = await async_client.post(
            "/api/v1/admin/trials/grant",
            json={
                "email": "enterprise@example.com",
                "trial_days": 14,
                "trial_plan": "enterprise",
            },
            headers={"Authorization": "Bearer fake-token"},
        )
    finally:
        # Clean up the override
        async_client.app.dependency_overrides.pop(require_admin, None)

    assert response.status_code == 200
    data = response.json()

    assert data["trial_details"]["plan"] == "enterprise"
    assert data["trial_details"]["limit"] == "unlimited"
    assert data["trial_details"]["value"] == "Enterprise"

    # Verify in database
    async with test_db() as db:
        result = await db.execute(
            select(User).where(User.email == "enterprise@example.com")
        )
        user = result.scalar_one()
        assert user.trial_analyses_limit is None  # None = unlimited


@pytest.mark.asyncio
async def test_grant_trial_custom_plan(async_client: AsyncClient, test_db):
    """Test granting custom trial plan."""
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

    try:
        response = await async_client.post(
            "/api/v1/admin/trials/grant",
            json={
                "email": "custom@example.com",
                "trial_days": 30,
                "trial_plan": "custom",
                "custom_limit": 1000,
            },
            headers={"Authorization": "Bearer fake-token"},
        )
    finally:
        # Clean up the override
        async_client.app.dependency_overrides.pop(require_admin, None)

    assert response.status_code == 200
    data = response.json()

    assert data["trial_details"]["plan"] == "custom"
    assert data["trial_details"]["limit"] == 1000


@pytest.mark.asyncio
async def test_grant_trial_duplicate_email(async_client: AsyncClient, test_db):
    """Test granting trial to email that already has trial."""
    # Create admin and existing trial user
    async with test_db() as db:
        admin = User(
            user_id="admin123",
            email="admin@example.com",
            password_hash="hashed",
            full_name="Admin User",
            is_admin=True,
            is_active=True,
        )
        existing_user = User(
            user_id="user123",
            email="existing@example.com",
            password_hash="hashed",
            full_name="Existing User",
            is_trial=True,
            trial_plan="basic",
        )
        db.add_all([admin, existing_user])
        await db.commit()

    # Mock admin authentication
    async def mock_require_admin():
        return "admin123"

    async_client.app.dependency_overrides[require_admin] = mock_require_admin

    try:
        response = await async_client.post(
            "/api/v1/admin/trials/grant",
            json={
                "email": "existing@example.com",
                "trial_days": 7,
                "trial_plan": "professional",
            },
            headers={"Authorization": "Bearer fake-token"},
        )
    finally:
        # Clean up the override
        async_client.app.dependency_overrides.pop(require_admin, None)

    assert response.status_code == 400
    assert response.json()["detail"] == "Email already used trial"
