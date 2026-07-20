"""
Tests for priority support API endpoints.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

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
    token = create_access_token(
        data={"sub": scale_plus_user.user_id, "email": scale_plus_user.email}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def enterprise_auth_headers(enterprise_user: User) -> dict[str, str]:
    """Create auth headers for Enterprise user."""
    token = create_access_token(
        data={"sub": enterprise_user.user_id, "email": enterprise_user.email}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def basic_auth_headers(basic_user: User) -> dict[str, str]:
    """Create auth headers for Basic user."""
    token = create_access_token(
        data={"sub": basic_user.user_id, "email": basic_user.email}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(admin_user: User) -> dict[str, str]:
    """Create auth headers for admin user."""
    token = create_access_token(
        data={"sub": admin_user.user_id, "email": admin_user.email}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_priority_service() -> AsyncMock:
    """Create a mock priority support service."""
    mock_service = AsyncMock()
    mock_service.check_priority_support_access = AsyncMock(return_value=True)
    mock_service.get_user_support_metrics = AsyncMock(
        return_value={
            "total_messages": 5,
            "priority_messages": 3,
            "average_response_time_hours": 2.5,
            "messages_by_status": {"unread": 1, "read": 2, "responded": 2},
        }
    )
    mock_service.get_sla_metrics = AsyncMock(
        return_value={
            "total_priority_messages": 10,
            "sla_met_count": 8,
            "sla_missed_count": 2,
            "sla_compliance_rate": 80.0,
            "average_response_time_hours": 3.5,
            "by_priority_level": {
                2: {"met": 5, "missed": 1, "compliance_rate": 83.33},
                3: {"met": 3, "missed": 1, "compliance_rate": 75.0},
            },
        }
    )
    return mock_service


class TestPrioritySupportEndpoints:
    """Test priority support API endpoints."""

    @pytest.mark.asyncio
    async def test_get_priority_support_status_scale_plus(
        self,
        async_client: AsyncClient,
        scale_plus_user: User,
        scale_plus_auth_headers: dict[str, str],
        mock_priority_service: AsyncMock,
    ):
        """Test Scale+ users can check priority support status."""
        with patch(
            "github_analyzer.api.routes.priority_support.PrioritySupportService",
            return_value=mock_priority_service,
        ):
            response = await async_client.get(
                "/api/v1/priority-support/status", headers=scale_plus_auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["has_access"] is True
            assert data["plan"] == "Scale+"
            assert data["priority_level"] == 3
            assert data["priority_name"] == "URGENT"
            assert data["sla_response_hours"] == 4

    @pytest.mark.asyncio
    async def test_get_priority_support_status_enterprise(
        self,
        async_client: AsyncClient,
        enterprise_user: User,
        enterprise_auth_headers: dict[str, str],
        mock_priority_service: AsyncMock,
    ):
        """Test Enterprise users can check priority support status."""
        with patch(
            "github_analyzer.api.routes.priority_support.PrioritySupportService",
            return_value=mock_priority_service,
        ):
            response = await async_client.get(
                "/api/v1/priority-support/status", headers=enterprise_auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["has_access"] is True
            assert data["plan"] == "Enterprise"
            assert data["priority_level"] == 2
            assert data["priority_name"] == "HIGH"
            assert data["sla_response_hours"] == 12

    @pytest.mark.asyncio
    async def test_get_priority_support_status_basic_denied(
        self,
        async_client: AsyncClient,
        basic_user: User,
        basic_auth_headers: dict[str, str],
        mock_priority_service: AsyncMock,
    ):
        """Test Basic users are denied priority support access."""
        mock_priority_service.check_priority_support_access.return_value = False

        with patch(
            "github_analyzer.api.routes.priority_support.PrioritySupportService",
            return_value=mock_priority_service,
        ):
            response = await async_client.get(
                "/api/v1/priority-support/status", headers=basic_auth_headers
            )

            assert response.status_code == 403
            data = response.json()
            assert "only available for Scale+ and Enterprise" in data["detail"]

    @pytest.mark.asyncio
    async def test_get_support_metrics_scale_plus(
        self,
        async_client: AsyncClient,
        scale_plus_user: User,
        scale_plus_auth_headers: dict[str, str],
        mock_priority_service: AsyncMock,
    ):
        """Test Scale+ users can get their support metrics."""
        with patch(
            "github_analyzer.api.routes.priority_support.PrioritySupportService",
            return_value=mock_priority_service,
        ):
            response = await async_client.get(
                "/api/v1/priority-support/metrics", headers=scale_plus_auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["total_messages"] == 5
            assert data["data"]["priority_messages"] == 3
            assert data["data"]["average_response_time_hours"] == 2.5

    @pytest.mark.asyncio
    async def test_get_support_metrics_basic_denied(
        self,
        async_client: AsyncClient,
        basic_user: User,
        basic_auth_headers: dict[str, str],
    ):
        """Test Basic users cannot access support metrics."""
        response = await async_client.get(
            "/api/v1/priority-support/metrics", headers=basic_auth_headers
        )

        assert response.status_code == 403
        data = response.json()
        assert "only available for Scale+ and Enterprise" in data["detail"]

    @pytest.mark.asyncio
    async def test_get_sla_performance_admin_only(
        self,
        async_client: AsyncClient,
        admin_user: User,
        admin_auth_headers: dict[str, str],
        mock_priority_service: AsyncMock,
    ):
        """Test only admins can access SLA performance metrics."""
        with patch(
            "github_analyzer.api.routes.priority_support.PrioritySupportService",
            return_value=mock_priority_service,
        ):
            response = await async_client.get(
                "/api/v1/priority-support/sla-performance?days=30",
                headers=admin_auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["period_days"] == 30
            assert data["data"]["sla_compliance_rate"] == 80.0

    @pytest.mark.asyncio
    async def test_get_sla_performance_non_admin_denied(
        self,
        async_client: AsyncClient,
        scale_plus_user: User,
        scale_plus_auth_headers: dict[str, str],
    ):
        """Test non-admin users cannot access SLA performance metrics."""
        response = await async_client.get(
            "/api/v1/priority-support/sla-performance", headers=scale_plus_auth_headers
        )

        assert response.status_code == 403
        data = response.json()
        assert "Admin access required" in data["detail"]
