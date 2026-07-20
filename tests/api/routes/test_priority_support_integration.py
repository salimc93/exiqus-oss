"""
Integration tests for priority support API endpoints.
"""

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from github_analyzer.api.auth.jwt import create_access_token
from github_analyzer.database.models import (
    SubscriptionPlan,
    SubscriptionStatus,
    User,
    UserRole,
)


@pytest.fixture
async def scale_plus_user(db_session: AsyncSession) -> User:
    """Create a Scale+ tier user."""
    user = User(
        user_id=str(uuid.uuid4()),
        email="scaleplus@test.com",
        password_hash="hashed_password",
        full_name="Scale Plus User",
        subscription_plan=SubscriptionPlan.SCALE_PLUS,
        subscription_status=SubscriptionStatus.ACTIVE,
        user_role=UserRole.USER,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def enterprise_user(db_session: AsyncSession) -> User:
    """Create an Enterprise tier user."""
    user = User(
        user_id=str(uuid.uuid4()),
        email="enterprise@test.com",
        password_hash="hashed_password",
        full_name="Enterprise User",
        subscription_plan=SubscriptionPlan.ENTERPRISE,
        subscription_status=SubscriptionStatus.ACTIVE,
        user_role=UserRole.USER,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def basic_user(db_session: AsyncSession) -> User:
    """Create a Basic tier user."""
    user = User(
        user_id=str(uuid.uuid4()),
        email="basic@test.com",
        password_hash="hashed_password",
        full_name="Basic User",
        subscription_plan=SubscriptionPlan.BASIC,
        subscription_status=SubscriptionStatus.ACTIVE,
        user_role=UserRole.USER,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create an admin user."""
    user = User(
        user_id=str(uuid.uuid4()),
        email="admin@test.com",
        password_hash="hashed_password",
        full_name="Admin User",
        subscription_plan=SubscriptionPlan.ENTERPRISE,
        subscription_status=SubscriptionStatus.ACTIVE,
        user_role=UserRole.ADMIN,
        is_admin=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def scale_plus_auth_headers(scale_plus_user: User) -> dict[str, str]:
    """Create auth headers for Scale+ user."""
    token = create_access_token(data={"sub": scale_plus_user.user_id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def enterprise_auth_headers(enterprise_user: User) -> dict[str, str]:
    """Create auth headers for Enterprise user."""
    token = create_access_token(data={"sub": enterprise_user.user_id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def basic_auth_headers(basic_user: User) -> dict[str, str]:
    """Create auth headers for Basic user."""
    token = create_access_token(data={"sub": basic_user.user_id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(admin_user: User) -> dict[str, str]:
    """Create auth headers for admin user."""
    token = create_access_token(data={"sub": admin_user.user_id})
    return {"Authorization": f"Bearer {token}"}


class TestPrioritySupportIntegration:
    """Integration tests for priority support endpoints."""

    @pytest.mark.asyncio
    async def test_scale_plus_priority_support_status(
        self,
        async_client: AsyncClient,
        scale_plus_user: User,
        scale_plus_auth_headers: dict[str, str],
    ) -> None:
        """Test Scale+ users can check priority support status."""
        response = await async_client.get(
            "/api/v1/priority-support/status",
            headers=scale_plus_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["has_access"] is True
        assert data["plan"] == "Scale+"
        assert data["priority_level"] == 3
        assert data["priority_name"] == "URGENT"
        assert data["sla_response_hours"] == 4

    @pytest.mark.asyncio
    async def test_enterprise_priority_support_status(
        self,
        async_client: AsyncClient,
        enterprise_user: User,
        enterprise_auth_headers: dict[str, str],
    ) -> None:
        """Test Enterprise users can check priority support status."""
        response = await async_client.get(
            "/api/v1/priority-support/status",
            headers=enterprise_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["has_access"] is True
        assert data["plan"] == "Enterprise"
        assert data["priority_level"] == 2
        assert data["priority_name"] == "HIGH"
        assert data["sla_response_hours"] == 12

    @pytest.mark.asyncio
    async def test_basic_user_no_priority_support(
        self,
        async_client: AsyncClient,
        basic_user: User,
        basic_auth_headers: dict[str, str],
    ) -> None:
        """Test Basic users are denied priority support."""
        response = await async_client.get(
            "/api/v1/priority-support/status",
            headers=basic_auth_headers,
        )

        assert response.status_code == 403
        data = response.json()
        assert "only available for Scale+ and Enterprise" in data["detail"]

    @pytest.mark.asyncio
    async def test_scale_plus_support_metrics(
        self,
        async_client: AsyncClient,
        scale_plus_user: User,
        scale_plus_auth_headers: dict[str, str],
    ) -> None:
        """Test Scale+ users can access support metrics."""
        response = await async_client.get(
            "/api/v1/priority-support/metrics",
            headers=scale_plus_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "total_messages" in data["data"]
        assert "priority_messages" in data["data"]

    @pytest.mark.asyncio
    async def test_basic_user_no_support_metrics(
        self,
        async_client: AsyncClient,
        basic_user: User,
        basic_auth_headers: dict[str, str],
    ) -> None:
        """Test Basic users cannot access support metrics."""
        response = await async_client.get(
            "/api/v1/priority-support/metrics",
            headers=basic_auth_headers,
        )

        assert response.status_code == 403
        data = response.json()
        assert "only available for Scale+ and Enterprise" in data["detail"]

    @pytest.mark.asyncio
    async def test_admin_sla_performance(
        self,
        async_client: AsyncClient,
        admin_user: User,
        admin_auth_headers: dict[str, str],
    ) -> None:
        """Test admins can access SLA performance metrics."""
        response = await async_client.get(
            "/api/v1/priority-support/sla-performance?days=30",
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["period_days"] == 30
        assert "sla_compliance_rate" in data["data"]

    @pytest.mark.asyncio
    async def test_non_admin_no_sla_performance(
        self,
        async_client: AsyncClient,
        scale_plus_user: User,
        scale_plus_auth_headers: dict[str, str],
    ) -> None:
        """Test non-admins cannot access SLA performance metrics."""
        response = await async_client.get(
            "/api/v1/priority-support/sla-performance",
            headers=scale_plus_auth_headers,
        )

        assert response.status_code == 403
        data = response.json()
        assert "Admin access required" in data["detail"]

    @pytest.mark.asyncio
    async def test_unauthenticated_no_access(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test unauthenticated users cannot access priority support."""
        response = await async_client.get("/api/v1/priority-support/status")

        assert response.status_code == 401
        data = response.json()
        assert "authentication token" in data["detail"].lower()
