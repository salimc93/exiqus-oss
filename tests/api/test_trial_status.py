"""Tests for trial status API endpoint."""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from github_analyzer.api.auth.dependencies import get_current_user_id
from github_analyzer.database.models import User


@pytest.mark.asyncio
async def test_get_trial_status_active_trial(async_client: AsyncClient, test_db):
    """Test getting status for active trial user."""
    # Create trial user
    async with test_db() as db:
        user = User(
            user_id="trial123",
            email="trial@example.com",
            password_hash="hashed",
            full_name="Trial User",
            is_trial=True,
            trial_plan="PROFESSIONAL",
            trial_analyses_limit=500,
            analyses_consumed=100,
            trial_end_date=datetime.now(timezone.utc) + timedelta(days=5),
            is_active=True,
        )
        db.add(user)
        await db.commit()

    # Mock authentication
    async def mock_get_current_user_id():
        return "trial123"

    async_client.app.dependency_overrides[get_current_user_id] = (
        mock_get_current_user_id
    )

    response = await async_client.get(
        "/api/v1/trials/status",
        headers={"Authorization": "Bearer fake-token"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["is_trial"] is True
    assert data["trial_plan"] == "PROFESSIONAL"
    assert data["analyses_consumed"] == 100
    assert data["analyses_limit"] == 500
    assert data["analyses_remaining"] == 400
    assert data["days_remaining"] >= 4  # At least 4 days
    assert data["is_expired"] is False


@pytest.mark.asyncio
async def test_get_trial_status_unlimited_plan(async_client: AsyncClient, test_db):
    """Test getting status for unlimited trial plan."""
    # Create trial user with unlimited plan
    async with test_db() as db:
        user = User(
            user_id="trial123",
            email="trial@example.com",
            password_hash="hashed",
            full_name="Trial User",
            is_trial=True,
            trial_plan="ENTERPRISE",
            trial_analyses_limit=None,  # Unlimited
            analyses_consumed=1000,
            trial_end_date=datetime.now(timezone.utc) + timedelta(days=10),
            is_active=True,
        )
        db.add(user)
        await db.commit()

    async def mock_get_current_user_id():
        return "trial123"

    async_client.app.dependency_overrides[get_current_user_id] = (
        mock_get_current_user_id
    )

    response = await async_client.get(
        "/api/v1/trials/status",
        headers={"Authorization": "Bearer fake-token"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["is_trial"] is True
    assert data["trial_plan"] == "ENTERPRISE"
    assert data["analyses_consumed"] == 1000
    assert data["analyses_limit"] is None
    assert data["analyses_remaining"] is None  # Unlimited
    assert data["is_expired"] is False


@pytest.mark.asyncio
async def test_get_trial_status_expired(async_client: AsyncClient, test_db):
    """Test getting status for expired trial."""
    # Create expired trial user
    async with test_db() as db:
        user = User(
            user_id="trial123",
            email="trial@example.com",
            password_hash="hashed",
            full_name="Trial User",
            is_trial=True,
            trial_plan="BASIC",
            trial_analyses_limit=100,
            analyses_consumed=50,
            trial_end_date=datetime.now(timezone.utc) - timedelta(days=1),  # Expired
            is_active=True,
        )
        db.add(user)
        await db.commit()

    async def mock_get_current_user_id():
        return "trial123"

    async_client.app.dependency_overrides[get_current_user_id] = (
        mock_get_current_user_id
    )

    response = await async_client.get(
        "/api/v1/trials/status",
        headers={"Authorization": "Bearer fake-token"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["is_trial"] is True
    assert data["is_expired"] is True
    assert data["days_remaining"] is None


@pytest.mark.asyncio
async def test_get_trial_status_non_trial_user(async_client: AsyncClient, test_db):
    """Test getting status for non-trial user."""
    # Create regular user
    async with test_db() as db:
        user = User(
            user_id="regular123",
            email="regular@example.com",
            password_hash="hashed",
            full_name="Regular User",
            is_trial=False,
            analyses_consumed=0,
            is_active=True,
        )
        db.add(user)
        await db.commit()

    async def mock_get_current_user_id():
        return "regular123"

    async_client.app.dependency_overrides[get_current_user_id] = (
        mock_get_current_user_id
    )

    response = await async_client.get(
        "/api/v1/trials/status",
        headers={"Authorization": "Bearer fake-token"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["is_trial"] is False
    assert data["trial_plan"] is None
    assert data["analyses_consumed"] == 0
    assert data["analyses_limit"] is None
    assert data["is_expired"] is False


@pytest.mark.asyncio
async def test_get_trial_status_at_limit(async_client: AsyncClient, test_db):
    """Test getting status when at usage limit."""
    # Create trial user at limit
    async with test_db() as db:
        user = User(
            user_id="trial123",
            email="trial@example.com",
            password_hash="hashed",
            full_name="Trial User",
            is_trial=True,
            trial_plan="BASIC",
            trial_analyses_limit=100,
            analyses_consumed=100,  # At limit
            trial_end_date=datetime.now(timezone.utc) + timedelta(days=3),
            is_active=True,
        )
        db.add(user)
        await db.commit()

    async def mock_get_current_user_id():
        return "trial123"

    async_client.app.dependency_overrides[get_current_user_id] = (
        mock_get_current_user_id
    )

    response = await async_client.get(
        "/api/v1/trials/status",
        headers={"Authorization": "Bearer fake-token"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["analyses_consumed"] == 100
    assert data["analyses_limit"] == 100
    assert data["analyses_remaining"] == 0
