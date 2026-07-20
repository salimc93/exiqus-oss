"""
Tests for batch history API endpoints following orchestration testing pattern.
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
        email="pro@test.com",
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
def enterprise_auth_headers(enterprise_user: User) -> dict[str, str]:
    """Create auth headers for Enterprise user."""
    token = create_access_token(
        data={"sub": enterprise_user.user_id, "email": enterprise_user.email}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def scale_plus_auth_headers(scale_plus_user: User) -> dict[str, str]:
    """Create auth headers for Scale+ user."""
    token = create_access_token(
        data={"sub": scale_plus_user.user_id, "email": scale_plus_user.email}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def pro_auth_headers(pro_user: User) -> dict[str, str]:
    """Create auth headers for Professional user."""
    token = create_access_token(data={"sub": pro_user.user_id, "email": pro_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_batch_history_service() -> AsyncMock:
    """Create a mock batch history service."""
    mock_service = AsyncMock()

    # Mock batch history data - returns tuple (list, total_count)
    mock_service.get_batch_history.return_value = (
        [
            {
                "batch_id": str(uuid.uuid4()),
                "user_id": "test_user_id",
                "repository_count": 5,
                "status": "completed",
                "successful_count": 4,
                "failed_count": 1,
                "total_cost": 0.0125,
                "processing_time_ms": 45000,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "completed_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "batch_id": str(uuid.uuid4()),
                "user_id": "test_user_id",
                "repository_count": 3,
                "status": "processing",
                "successful_count": 1,
                "failed_count": 0,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        ],
        2,  # total_count
    )

    # Mock batch details
    mock_service.get_batch_details.return_value = {
        "batch_id": "test_batch_id",
        "user_id": "test_user_id",
        "repository_count": 5,
        "status": "completed",
        "successful_count": 4,
        "failed_count": 1,
        "total_cost": 0.0125,
        "processing_time_ms": 45000,
        "contexts": ["startup", "enterprise"],
        "error_messages": ["One repository failed to parse"],
        "success_rate": 80.0,
        "duration_seconds": 45.0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }

    # Mock statistics
    mock_service.get_batch_statistics.return_value = {
        "period_days": 30,
        "total_batches": 10,
        "total_repositories": 50,
        "total_successful": 45,
        "total_failed": 5,
        "total_cost": 0.125,
        "avg_processing_time_ms": 30000,
        "success_rate": 90.0,
        "status_breakdown": {
            "completed": 8,
            "processing": 1,
            "failed": 1,
        },
    }

    # Mock recent batches
    mock_service.get_recent_batches.return_value = [
        {
            "batch_id": str(uuid.uuid4()),
            "repository_count": 5,
            "status": "completed",
            "successful_count": 5,
            "failed_count": 0,
            "total_cost": 0.015,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        },
    ]

    return mock_service


class TestBatchHistoryEndpointsOrchestration:
    """Test batch history API endpoints with proper orchestration testing."""

    @pytest.mark.asyncio
    async def test_get_batch_history_orchestrates_correctly(
        self,
        async_client: AsyncClient,
        enterprise_user: User,
        enterprise_auth_headers: dict[str, str],
        mock_batch_history_service: AsyncMock,
    ) -> None:
        """Test that batch history endpoint orchestrates components correctly."""
        # Arrange: Setup mocks
        with patch(
            "github_analyzer.api.routes.batch_history.AsyncBatchHistoryService",
            return_value=mock_batch_history_service,
        ):
            # Act: Call the endpoint
            response = await async_client.get(
                "/api/v1/batch-history/", headers=enterprise_auth_headers
            )

            # Assert: Verify orchestration
            assert response.status_code == 200

            # Verify service was called (using return_value so __init__ not directly called)

            # Verify service method was called with correct parameters
            mock_batch_history_service.get_batch_history.assert_called_once_with(
                user_id=enterprise_user.user_id,
                limit=50,
                offset=0,
                status_filter=None,
            )

            # Verify response structure
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]) == 2
            assert data["message"] == "Retrieved 2 batch history records"

    @pytest.mark.asyncio
    async def test_get_batch_history_with_filters_passes_correctly(
        self,
        async_client: AsyncClient,
        scale_plus_user: User,
        scale_plus_auth_headers: dict[str, str],
        mock_batch_history_service: AsyncMock,
    ) -> None:
        """Test that filters are passed correctly to the service."""
        # Arrange
        with patch(
            "github_analyzer.api.routes.batch_history.AsyncBatchHistoryService",
            return_value=mock_batch_history_service,
        ):
            # Act
            response = await async_client.get(
                "/api/v1/batch-history/?limit=10&offset=5&status=completed",
                headers=scale_plus_auth_headers,
            )

            # Assert
            assert response.status_code == 200
            mock_batch_history_service.get_batch_history.assert_called_once_with(
                user_id=scale_plus_user.user_id,
                limit=10,
                offset=5,
                status_filter="completed",
            )

    @pytest.mark.asyncio
    async def test_batch_history_rejects_non_enterprise_users(
        self,
        async_client: AsyncClient,
        pro_user: User,
        pro_auth_headers: dict[str, str],
    ) -> None:
        """Test that Pro users are rejected before service is called."""
        # Act
        response = await async_client.get(
            "/api/v1/batch-history/", headers=pro_auth_headers
        )

        # Assert
        assert response.status_code == 403
        data = response.json()
        assert "only available for Enterprise and Scale+ plans" in data["detail"]

    @pytest.mark.asyncio
    async def test_get_batch_details_orchestrates_correctly(
        self,
        async_client: AsyncClient,
        enterprise_user: User,
        enterprise_auth_headers: dict[str, str],
        mock_batch_history_service: AsyncMock,
    ) -> None:
        """Test batch details endpoint orchestration."""
        # Arrange
        batch_id = str(uuid.uuid4())
        with patch(
            "github_analyzer.api.routes.batch_history.AsyncBatchHistoryService",
            return_value=mock_batch_history_service,
        ):
            # Act
            response = await async_client.get(
                f"/api/v1/batch-history/{batch_id}", headers=enterprise_auth_headers
            )

            # Assert
            assert response.status_code == 200

            # Verify service method called correctly
            mock_batch_history_service.get_batch_details.assert_called_once_with(
                batch_id=batch_id,
                user_id=enterprise_user.user_id,
            )

            # Verify response
            data = response.json()
            assert data["success"] is True
            assert data["data"]["batch_id"] == "test_batch_id"
            assert data["message"] == f"Retrieved details for batch {batch_id}"

    @pytest.mark.asyncio
    async def test_get_batch_details_handles_not_found(
        self,
        async_client: AsyncClient,
        enterprise_user: User,
        enterprise_auth_headers: dict[str, str],
        mock_batch_history_service: AsyncMock,
    ) -> None:
        """Test batch details returns 404 when batch not found."""
        # Arrange
        batch_id = str(uuid.uuid4())
        mock_batch_history_service.get_batch_details.return_value = None

        with patch(
            "github_analyzer.api.routes.batch_history.AsyncBatchHistoryService",
            return_value=mock_batch_history_service,
        ):
            # Act
            response = await async_client.get(
                f"/api/v1/batch-history/{batch_id}", headers=enterprise_auth_headers
            )

            # Assert
            assert response.status_code == 404
            data = response.json()
            assert "not found" in data["detail"]

    @pytest.mark.asyncio
    async def test_get_batch_statistics_orchestrates_correctly(
        self,
        async_client: AsyncClient,
        enterprise_user: User,
        enterprise_auth_headers: dict[str, str],
        mock_batch_history_service: AsyncMock,
    ) -> None:
        """Test batch statistics endpoint orchestration."""
        # Arrange
        with patch(
            "github_analyzer.api.routes.batch_history.AsyncBatchHistoryService",
            return_value=mock_batch_history_service,
        ):
            # Act
            response = await async_client.get(
                "/api/v1/batch-history/statistics/summary?days=7",
                headers=enterprise_auth_headers,
            )

            # Assert
            assert response.status_code == 200

            # Verify service called correctly
            mock_batch_history_service.get_batch_statistics.assert_called_once_with(
                user_id=enterprise_user.user_id,
                days=7,
            )

            # Verify response
            data = response.json()
            assert data["success"] is True
            assert data["data"]["period_days"] == 30
            assert data["data"]["total_batches"] == 10
            assert data["message"] == "Batch processing statistics for the last 7 days"

    @pytest.mark.asyncio
    async def test_error_handling_returns_500(
        self,
        async_client: AsyncClient,
        enterprise_user: User,
        enterprise_auth_headers: dict[str, str],
        mock_batch_history_service: AsyncMock,
    ) -> None:
        """Test that service errors are handled properly."""
        # Arrange
        mock_batch_history_service.get_batch_history.side_effect = Exception(
            "Database connection error"
        )

        with patch(
            "github_analyzer.api.routes.batch_history.AsyncBatchHistoryService",
            return_value=mock_batch_history_service,
        ):
            # Act
            response = await async_client.get(
                "/api/v1/batch-history/", headers=enterprise_auth_headers
            )

            # Assert
            assert response.status_code == 500
            data = response.json()
            assert "Failed to retrieve batch history" in data["detail"]
