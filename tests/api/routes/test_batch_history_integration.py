"""
Integration tests for batch history API endpoints.
"""

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from github_analyzer.api.auth.jwt import create_access_token
from github_analyzer.api.services.async_batch_history_service import (
    AsyncBatchHistoryService,
)
from github_analyzer.database.models import (
    SubscriptionPlan,
    SubscriptionStatus,
    User,
    UserRole,
)


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
async def pro_user(db_session: AsyncSession) -> User:
    """Create a Professional tier user."""
    user = User(
        user_id=str(uuid.uuid4()),
        email="professional@test.com",
        password_hash="hashed_password",
        full_name="Professional User",
        subscription_plan=SubscriptionPlan.PROFESSIONAL,
        subscription_status=SubscriptionStatus.ACTIVE,
        user_role=UserRole.USER,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(enterprise_user: User) -> dict[str, str]:
    """Create auth headers for enterprise user."""
    token = create_access_token(data={"sub": enterprise_user.user_id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def scale_plus_auth_headers(scale_plus_user: User) -> dict[str, str]:
    """Create auth headers for scale+ user."""
    token = create_access_token(data={"sub": scale_plus_user.user_id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def pro_auth_headers(pro_user: User) -> dict[str, str]:
    """Create auth headers for pro user."""
    token = create_access_token(data={"sub": pro_user.user_id})
    return {"Authorization": f"Bearer {token}"}


class TestBatchHistoryIntegration:
    """Integration tests for batch history endpoints."""

    @pytest.mark.asyncio
    async def test_enterprise_user_can_access_batch_history(
        self,
        async_client: AsyncClient,
        enterprise_user: User,
        auth_headers: dict[str, str],
        db_session: AsyncSession,
    ) -> None:
        """Test that Enterprise users can access batch history."""
        # Create some batch history
        service = AsyncBatchHistoryService(db_session)
        batch_id = await service.create_batch_record(
            user_id=enterprise_user.user_id,
            repository_count=5,
            contexts=["startup", "enterprise"],
        )

        # Access the endpoint
        response = await async_client.get(
            "/api/v1/batch-history/",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["batch_id"] == batch_id

    @pytest.mark.asyncio
    async def test_scale_plus_user_can_access_batch_history(
        self,
        async_client: AsyncClient,
        scale_plus_user: User,
        scale_plus_auth_headers: dict[str, str],
        db_session: AsyncSession,
    ) -> None:
        """Test that Scale+ users can access batch history."""
        # Create some batch history
        service = AsyncBatchHistoryService(db_session)
        await service.create_batch_record(
            user_id=scale_plus_user.user_id,
            repository_count=3,
            contexts=["startup"],
        )

        # Access the endpoint
        response = await async_client.get(
            "/api/v1/batch-history/",
            headers=scale_plus_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1

    @pytest.mark.asyncio
    async def test_pro_user_cannot_access_batch_history(
        self,
        async_client: AsyncClient,
        pro_user: User,
        pro_auth_headers: dict[str, str],
    ) -> None:
        """Test that Professional users cannot access batch history."""
        response = await async_client.get(
            "/api/v1/batch-history/",
            headers=pro_auth_headers,
        )

        assert response.status_code == 403
        data = response.json()
        assert "only available for Enterprise and Scale+ plans" in data["detail"]

    @pytest.mark.asyncio
    async def test_batch_details_endpoint(
        self,
        async_client: AsyncClient,
        enterprise_user: User,
        auth_headers: dict[str, str],
        db_session: AsyncSession,
    ) -> None:
        """Test retrieving batch details."""
        # Create and complete a batch
        service = AsyncBatchHistoryService(db_session)
        batch_id = await service.create_batch_record(
            user_id=enterprise_user.user_id,
            repository_count=5,
            contexts=["startup", "enterprise"],
        )

        await service.complete_batch(
            batch_id=batch_id,
            successful_count=4,
            failed_count=1,
            total_cost=0.0125,
            processing_time_ms=45000,
            error_messages=["One repository failed to parse"],
        )

        # Get details
        response = await async_client.get(
            f"/api/v1/batch-history/{batch_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["batch_id"] == batch_id
        assert data["data"]["completed_count"] == 4
        assert data["data"]["failed_count"] == 1
        assert data["data"]["contexts"] == ["startup", "enterprise"]

    @pytest.mark.asyncio
    async def test_batch_statistics_endpoint(
        self,
        async_client: AsyncClient,
        enterprise_user: User,
        auth_headers: dict[str, str],
        db_session: AsyncSession,
    ) -> None:
        """Test batch statistics endpoint."""
        # Create multiple batches
        service = AsyncBatchHistoryService(db_session)

        for i in range(3):
            batch_id = await service.create_batch_record(
                user_id=enterprise_user.user_id,
                repository_count=i + 2,
                contexts=["startup"],
            )
            await service.complete_batch(
                batch_id=batch_id,
                successful_count=i + 1,
                failed_count=1,
                total_cost=0.01 * (i + 1),
                processing_time_ms=10000 * (i + 1),
            )

        # Get statistics
        response = await async_client.get(
            "/api/v1/batch-history/statistics/summary?days=30",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        stats = data["data"]
        assert stats["total_batches"] == 3
        assert stats["total_repositories"] == 9  # 2 + 3 + 4
        assert stats["total_successful"] == 6  # 1 + 2 + 3
        assert stats["total_failed"] == 3  # 1 + 1 + 1

    @pytest.mark.asyncio
    async def test_recent_batches_endpoint(
        self,
        async_client: AsyncClient,
        enterprise_user: User,
        auth_headers: dict[str, str],
        db_session: AsyncSession,
    ) -> None:
        """Test recent batches endpoint."""
        # Create a batch
        service = AsyncBatchHistoryService(db_session)
        batch_id = await service.create_batch_record(
            user_id=enterprise_user.user_id,
            repository_count=5,
            contexts=["startup"],
        )

        # Get recent batches
        response = await async_client.get(
            "/api/v1/batch-history/recent/summary?limit=10",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["batch_id"] == batch_id
