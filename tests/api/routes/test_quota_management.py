"""
Tests for quota management API endpoints.

Tests both admin quota management and user quota viewing capabilities.
"""

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from github_analyzer.database.models import SubscriptionPlan, User, UserRole
from github_analyzer.database.operations import UserOperations


@pytest.fixture
async def test_user(test_db: AsyncSession) -> User:
    """Fixture to create a standard user for testing."""
    async with test_db() as session:
        user = User(
            user_id="test-user-123",
            email="test@example.com",
            full_name="Test User",
            password_hash="hashed_password",
            subscription_plan=SubscriptionPlan.PROFESSIONAL,
            usage_quota=1000,
            usage_count=250,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture
def user_auth_headers(test_user: User) -> dict:
    """Fixture to create auth headers for a standard user."""
    from github_analyzer.api.auth.jwt import create_access_token

    token = create_access_token(data={"sub": test_user.user_id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def admin_user(test_db: AsyncSession) -> User:
    """Fixture to create an admin user for testing."""
    async with test_db() as session:
        user = User(
            user_id="admin-user-456",
            email="admin@example.com",
            full_name="Admin User",
            password_hash="hashed_password",
            user_role=UserRole.ADMIN,
            is_admin=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture
def admin_auth_headers(admin_user: User) -> dict:
    """Fixture to create auth headers for an admin user."""
    from github_analyzer.api.auth.jwt import create_access_token

    token = create_access_token(data={"sub": admin_user.user_id})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
class TestUserQuotaEndpoints:
    """Test suite for user-facing quota viewing endpoints."""

    async def test_get_my_quota_success(
        self, async_client: AsyncClient, user_auth_headers: dict, test_user: User
    ):
        """Test successful retrieval of user's own quota."""
        response = await async_client.get("/api/v1/quota/me", headers=user_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == test_user.user_id
        assert data["plan"] == "PROFESSIONAL"
        assert data["quota_total"] == 1000
        assert data["quota_used"] == 250
        assert data["quota_remaining"] == 750
        assert data["quota_percentage"] == 25.0

    async def test_get_my_quota_details_success(
        self,
        async_client: AsyncClient,
        user_auth_headers: dict,
        test_user: User,
        test_db: AsyncSession,
    ):
        """Test retrieval of detailed quota information."""
        # Create mock usage records in the database for this test
        from github_analyzer.database.models import BillingUsageRecord

        # Get a database session
        async with test_db() as session:
            # Create usage records for the test user
            billing_period = datetime.now(timezone.utc).strftime("%Y-%m")

            # Create analysis usage record
            analysis_record = BillingUsageRecord(
                record_id=f"test_analysis_{test_user.user_id}",
                user_id=test_user.user_id,
                usage_type="analysis",
                usage_count=100,
                unit_cost="0.01",
                total_cost="1.00",
                billing_period=billing_period,
            )
            session.add(analysis_record)

            # Create API call usage record
            api_record = BillingUsageRecord(
                record_id=f"test_api_{test_user.user_id}",
                user_id=test_user.user_id,
                usage_type="api_call",
                usage_count=150,
                unit_cost="0.01",
                total_cost="1.50",
                billing_period=billing_period,
            )
            session.add(api_record)

            await session.commit()

        # Now make the request
        response = await async_client.get(
            "/api/v1/quota/me/details", headers=user_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == test_user.user_id
        assert data["billing_period"] == datetime.now(timezone.utc).strftime("%Y-%m")
        assert data["usage_breakdown"] == {"analysis": 100, "api_call": 150}
        assert data["total_cost"] == 2.5


@pytest.mark.asyncio
class TestAdminQuotaEndpoints:
    """Test suite for admin quota management endpoints."""

    @pytest.fixture
    async def seeded_users(self, test_db: AsyncSession) -> list[User]:
        """Seed the database with multiple users for testing."""
        async with test_db() as session:
            users = [
                User(
                    user_id="user-1",
                    email="user1@example.com",
                    full_name="Seeded User One",
                    password_hash="hashed",
                    subscription_plan=SubscriptionPlan.BASIC,
                    usage_quota=100,
                    usage_count=80,
                    created_at=datetime.now(timezone.utc),
                ),
                User(
                    user_id="user-2",
                    email="user2@example.com",
                    full_name="Seeded User Two",
                    password_hash="hashed",
                    subscription_plan=SubscriptionPlan.PROFESSIONAL,
                    usage_quota=1000,
                    usage_count=500,
                    created_at=datetime.now(timezone.utc),
                ),
            ]
            session.add_all(users)
            await session.commit()
            for user in users:
                await session.refresh(user)
            return users

    async def test_get_all_user_quotas_success(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict,
        seeded_users: list[User],
    ):
        """Test admin retrieval of all user quotas."""
        response = await async_client.get(
            "/api/v1/quota/admin/users", headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        # Includes admin user from fixture + 2 seeded users
        assert data["total_users"] == 3
        assert len(data["users"]) == 3

    async def test_get_all_user_quotas_with_filters(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict,
        seeded_users: list[User],
    ):
        """Test admin retrieval with plan filter."""
        response = await async_client.get(
            "/api/v1/quota/admin/users?plan=BASIC", headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_users"] == 1
        assert len(data["users"]) == 1
        assert data["users"][0]["subscription_plan"] == "BASIC"

    async def test_update_user_quota_success(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict,
        seeded_users: list[User],
    ):
        """Test admin updating a user's quota."""
        user_to_update = seeded_users[0]
        response = await async_client.put(
            f"/api/v1/quota/admin/users/{user_to_update.user_id}",
            headers=admin_auth_headers,
            json={"new_quota": 500},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["new_quota"] == 500

    async def test_reset_user_usage_success(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict,
        seeded_users: list[User],
    ):
        """Test admin resetting a user's usage."""
        user_to_reset = seeded_users[0]
        response = await async_client.post(
            f"/api/v1/quota/admin/users/{user_to_reset.user_id}/reset",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_bulk_reset_usage_success(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict,
        seeded_users: list[User],
        test_db: AsyncSession,
    ):
        """Test bulk usage reset."""
        # First, set some usage for the seeded users
        async with test_db() as session:
            # Update usage_consumed for seeded users
            for user in seeded_users:
                await UserOperations.increment_usage_count(session, user.user_id, 50)
            await session.commit()

        # Now test the bulk reset
        response = await async_client.post(
            "/api/v1/quota/admin/reset-all", headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        # Should reset 2 seeded users (admin user from fixture may not have usage)
        assert data["reset_successful"] >= 2
        assert data["total_users"] >= 2

    async def test_grant_quota_bonus_success(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict,
        seeded_users: list[User],
    ):
        """Test granting bonus quota to a user."""
        user_to_bonus = seeded_users[1]  # User with 1000 quota
        response = await async_client.post(
            f"/api/v1/quota/admin/users/{user_to_bonus.user_id}/bonus",
            headers=admin_auth_headers,
            json={"bonus_amount": 500, "reason": "Test Bonus"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["new_quota"] == 1500
