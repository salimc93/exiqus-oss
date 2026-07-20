"""
Tests for AsyncBatchHistoryService - async batch analysis history tracking.
"""

import json
from datetime import datetime, timezone
from typing import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from github_analyzer.api.services.async_batch_history_service import (
    AsyncBatchHistoryService,
)
from github_analyzer.database.models import (
    AnalysisStatus,
    BatchAnalysis,
    SubscriptionPlan,
    SubscriptionStatus,
    User,
    UserRole,
)


@pytest.fixture
async def async_db_session(test_db) -> AsyncGenerator[AsyncSession, None]:
    """Create a session on the shared test Postgres database."""
    async with test_db() as session:
        # Create a test user
        user = User(
            user_id="test_user_123",
            email="test@example.com",
            password_hash="hashed_password",
            full_name="Test User",
            subscription_plan=SubscriptionPlan.SCALE_PLUS,
            subscription_status=SubscriptionStatus.ACTIVE,
            user_role=UserRole.USER,
            created_at=datetime.now(timezone.utc),
        )
        session.add(user)
        await session.commit()

        yield session


@pytest.fixture
async def batch_service(
    async_db_session: AsyncSession,
) -> AsyncBatchHistoryService:
    """Create AsyncBatchHistoryService instance with test database."""
    return AsyncBatchHistoryService(async_db_session)


class TestAsyncBatchRecordCreation:
    """Test async batch record creation functionality."""

    @pytest.mark.asyncio
    async def test_create_batch_record_success(
        self, batch_service: AsyncBatchHistoryService, async_db_session: AsyncSession
    ) -> None:
        """Test successful batch record creation."""
        batch_id = await batch_service.create_batch_record(
            user_id="test_user_123",
            repository_count=5,
            contexts=["startup", "enterprise"],
        )

        assert batch_id is not None
        assert len(batch_id) == 36  # UUID format

        # Verify record in database
        from sqlalchemy.future import select

        result = await async_db_session.execute(
            select(BatchAnalysis).filter_by(batch_id=batch_id)
        )
        batch = result.scalar_one_or_none()

        assert batch is not None
        assert batch.user_id == "test_user_123"
        assert batch.repository_count == 5
        assert json.loads(batch.contexts) == ["startup", "enterprise"]
        assert batch.status == AnalysisStatus.PENDING

    @pytest.mark.asyncio
    async def test_start_batch_processing(
        self, batch_service: AsyncBatchHistoryService, async_db_session: AsyncSession
    ) -> None:
        """Test starting batch processing."""
        batch_id = await batch_service.create_batch_record(
            user_id="test_user_123",
            repository_count=5,
            contexts=["startup"],
        )

        await batch_service.start_batch_processing(batch_id)

        from sqlalchemy.future import select

        result = await async_db_session.execute(
            select(BatchAnalysis).filter_by(batch_id=batch_id)
        )
        batch = result.scalar_one_or_none()

        assert batch is not None
        assert batch.status == AnalysisStatus.PROCESSING

    @pytest.mark.asyncio
    async def test_complete_batch(
        self, batch_service: AsyncBatchHistoryService, async_db_session: AsyncSession
    ) -> None:
        """Test completing a batch."""
        batch_id = await batch_service.create_batch_record(
            user_id="test_user_123",
            repository_count=8,
            contexts=["startup", "enterprise"],
        )

        await batch_service.complete_batch(
            batch_id=batch_id,
            successful_count=7,
            failed_count=1,
            total_cost=0.0125,
            processing_time_ms=45000,
            error_messages=["One repository failed parsing"],
        )

        from sqlalchemy.future import select

        result = await async_db_session.execute(
            select(BatchAnalysis).filter_by(batch_id=batch_id)
        )
        batch = result.scalar_one_or_none()

        assert batch is not None
        assert batch.status == AnalysisStatus.COMPLETED
        assert batch.successful_count == 7
        assert batch.failed_count == 1
        assert batch.total_cost == 0.0125
        assert batch.processing_time_ms == 45000
        assert batch.completed_at is not None
        assert batch.error_messages is not None
        assert json.loads(batch.error_messages) == ["One repository failed parsing"]

    @pytest.mark.asyncio
    async def test_fail_batch(
        self, batch_service: AsyncBatchHistoryService, async_db_session: AsyncSession
    ) -> None:
        """Test marking batch as failed."""
        batch_id = await batch_service.create_batch_record(
            user_id="test_user_123",
            repository_count=5,
            contexts=["startup"],
        )

        await batch_service.fail_batch(
            batch_id=batch_id,
            error_message="API rate limit exceeded",
            processing_time_ms=5000,
        )

        from sqlalchemy.future import select

        result = await async_db_session.execute(
            select(BatchAnalysis).filter_by(batch_id=batch_id)
        )
        batch = result.scalar_one_or_none()

        assert batch is not None
        assert batch.status == AnalysisStatus.FAILED
        assert batch.completed_at is not None
        assert batch.processing_time_ms == 5000
        assert batch.error_messages is not None
        assert json.loads(batch.error_messages) == ["API rate limit exceeded"]

    @pytest.mark.asyncio
    async def test_get_batch_history(
        self, batch_service: AsyncBatchHistoryService
    ) -> None:
        """Test retrieving batch history."""
        # Create multiple batches
        batch_ids = []
        for i in range(3):
            batch_id = await batch_service.create_batch_record(
                user_id="test_user_123",
                repository_count=i + 1,
                contexts=["startup"],
            )
            batch_ids.append(batch_id)

        history, total_count = await batch_service.get_batch_history("test_user_123")

        assert len(history) == 3
        assert total_count == 3
        # Should be ordered by created_at desc (newest first)
        assert history[0]["total_repositories"] == 3
        assert history[1]["total_repositories"] == 2
        assert history[2]["total_repositories"] == 1

    @pytest.mark.asyncio
    async def test_get_batch_statistics(
        self, batch_service: AsyncBatchHistoryService
    ) -> None:
        """Test getting batch statistics."""
        # Create and complete a batch
        batch_id = await batch_service.create_batch_record(
            user_id="test_user_123",
            repository_count=10,
            contexts=["startup"],
        )
        await batch_service.complete_batch(
            batch_id=batch_id,
            successful_count=9,
            failed_count=1,
            total_cost=0.0156,
            processing_time_ms=60000,
        )

        stats = await batch_service.get_batch_statistics("test_user_123", days=30)

        assert stats["total_batches"] == 1
        assert stats["total_repositories"] == 10
        assert stats["total_successful"] == 9
        assert stats["total_failed"] == 1
        assert abs(stats["total_cost"] - 0.0156) < 0.0001
        assert stats["avg_processing_time_ms"] == 60000
        assert abs(stats["success_rate"] - 90.0) < 0.01
