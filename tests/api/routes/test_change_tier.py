"""Tests for the change trial tier endpoint."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from github_analyzer.api.auth.dependencies import get_admin_user_from_token
from github_analyzer.database.connection import get_db_session
from github_analyzer.database.models import (
    SubscriptionPlan,
    SubscriptionStatus,
    User,
)


class TestChangeTrialTier:
    """Test the change trial tier functionality."""

    @pytest.fixture
    async def admin_user(self) -> User:
        """Create an admin user for testing."""
        return User(
            user_id=str(uuid4()),
            email="admin@test.com",
            password_hash="hashed_password",
            full_name="Test Admin",
            is_admin=True,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

    @pytest.fixture
    async def admin_client(self, async_client: AsyncClient, admin_user):
        """Create client with admin authentication."""
        async_client.app.dependency_overrides[get_admin_user_from_token] = lambda: (
            admin_user
        )
        yield async_client
        async_client.app.dependency_overrides.clear()

    async def test_change_trial_tier_success(
        self, admin_client: AsyncClient, admin_user
    ):
        """Test changing trial tier for a user."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Create test user with active trial
        test_user = User(
            user_id=str(uuid4()),
            email="trial@example.com",
            full_name="Trial User",
            is_active=True,
            subscription_plan=SubscriptionPlan.BASIC,
            subscription_status=SubscriptionStatus.TRIALING,
            trial_end_date=datetime.now(timezone.utc) + timedelta(days=5),
            created_at=datetime.now(timezone.utc),
        )

        # Mock database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=test_user)
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        admin_client.app.dependency_overrides[get_db_session] = lambda: mock_session

        # Change tier to scale
        response = await admin_client.put(
            "/api/v1/admin/trial/change-tier",
            json={"email": "trial@example.com", "tier": "scale"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert "changed to scale" in response.json()["message"]

        # Verify tier was changed
        assert test_user.subscription_plan == SubscriptionPlan.ENTERPRISE
        assert test_user.subscription_status == SubscriptionStatus.TRIALING

    async def test_change_trial_tier_no_active_trial(
        self, admin_client: AsyncClient, admin_user
    ):
        """Test changing tier for user without active trial."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Create test user without trial
        test_user = User(
            user_id=str(uuid4()),
            email="notrial@example.com",
            full_name="No Trial User",
            is_active=True,
            subscription_plan=SubscriptionPlan.FREE,
            subscription_status=SubscriptionStatus.ACTIVE,
            trial_end_date=None,
            created_at=datetime.now(timezone.utc),
        )

        # Mock database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=test_user)
        mock_session.execute = AsyncMock(return_value=mock_result)

        admin_client.app.dependency_overrides[get_db_session] = lambda: mock_session

        response = await admin_client.put(
            "/api/v1/admin/trial/change-tier",
            json={"email": "notrial@example.com", "tier": "growth"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "does not have an active trial" in response.json()["detail"]

    async def test_change_trial_tier_invalid_tier(
        self, admin_client: AsyncClient, admin_user
    ):
        """Test changing tier with invalid tier name."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Create test user with active trial
        test_user = User(
            user_id=str(uuid4()),
            email="trial@example.com",
            full_name="Trial User",
            is_active=True,
            subscription_plan=SubscriptionPlan.BASIC,
            subscription_status=SubscriptionStatus.TRIALING,
            trial_end_date=datetime.now(timezone.utc) + timedelta(days=5),
            created_at=datetime.now(timezone.utc),
        )

        # Mock database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=test_user)
        mock_session.execute = AsyncMock(return_value=mock_result)

        admin_client.app.dependency_overrides[get_db_session] = lambda: mock_session

        response = await admin_client.put(
            "/api/v1/admin/trial/change-tier",
            json={"email": "trial@example.com", "tier": "invalid_tier"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid tier" in response.json()["detail"]
        assert (
            "Must be one of: starter, growth, scale, scale_plus"
            in response.json()["detail"]
        )

    async def test_change_trial_tier_user_not_found(
        self, admin_client: AsyncClient, admin_user
    ):
        """Test changing tier for non-existent user."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock database query to return no user
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        admin_client.app.dependency_overrides[get_db_session] = lambda: mock_session

        response = await admin_client.put(
            "/api/v1/admin/trial/change-tier",
            json={"email": "nonexistent@example.com", "tier": "scale_plus"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"]

    async def test_change_trial_tier_all_tiers(
        self, admin_client: AsyncClient, admin_user
    ):
        """Test changing to all valid tier types."""
        mock_session = AsyncMock(spec=AsyncSession)

        tier_mappings = [
            ("starter", SubscriptionPlan.BASIC),
            ("growth", SubscriptionPlan.PROFESSIONAL),
            ("scale", SubscriptionPlan.ENTERPRISE),
            ("scale_plus", SubscriptionPlan.SCALE_PLUS),
        ]

        for tier_name, expected_plan in tier_mappings:
            # Create test user with active trial
            test_user = User(
                user_id=str(uuid4()),
                email=f"trial_{tier_name}@example.com",
                full_name="Trial User",
                is_active=True,
                subscription_plan=SubscriptionPlan.BASIC,
                subscription_status=SubscriptionStatus.TRIALING,
                trial_end_date=datetime.now(timezone.utc) + timedelta(days=5),
                created_at=datetime.now(timezone.utc),
            )

            # Mock database query
            mock_result = MagicMock()
            mock_result.scalar_one_or_none = MagicMock(return_value=test_user)
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_session.commit = AsyncMock()

            admin_client.app.dependency_overrides[get_db_session] = lambda: mock_session

            # Change tier
            response = await admin_client.put(
                "/api/v1/admin/trial/change-tier",
                json={"email": f"trial_{tier_name}@example.com", "tier": tier_name},
            )

            assert response.status_code == status.HTTP_200_OK
            assert f"changed to {tier_name}" in response.json()["message"]
            assert test_user.subscription_plan == expected_plan
