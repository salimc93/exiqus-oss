"""
Edge case tests for AsyncBatchHistoryService - Production scenarios and error handling.
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
        # Create test users with different subscription tiers
        users = [
            User(
                user_id="free_user",
                email="free@example.com",
                password_hash="hashed",
                full_name="Free User",
                subscription_plan=SubscriptionPlan.FREE,
                subscription_status=SubscriptionStatus.ACTIVE,
                user_role=UserRole.USER,
                created_at=datetime.now(timezone.utc),
            ),
            User(
                user_id="scale_user",
                email="scale@example.com",
                password_hash="hashed",
                full_name="Scale User",
                subscription_plan=SubscriptionPlan.ENTERPRISE,
                subscription_status=SubscriptionStatus.ACTIVE,
                user_role=UserRole.USER,
                created_at=datetime.now(timezone.utc),
            ),
        ]
        for user in users:
            session.add(user)
        await session.commit()

        yield session


@pytest.fixture
async def batch_service(
    async_db_session: AsyncSession,
) -> AsyncBatchHistoryService:
    """Create AsyncBatchHistoryService instance with test database."""
    return AsyncBatchHistoryService(async_db_session)


class TestBatchFailureScenarios:
    """Test batch failure and recovery scenarios."""

    @pytest.mark.asyncio
    async def test_fail_batch_with_partial_progress(
        self, batch_service: AsyncBatchHistoryService, async_db_session: AsyncSession
    ) -> None:
        """Test failing a batch that was partially processed."""
        # Create and start a batch
        batch_id = await batch_service.create_batch_record(
            user_id="scale_user",
            repository_count=10,
            contexts=["startup", "enterprise"],
        )

        await batch_service.start_batch_processing(batch_id)

        # Update with some progress
        await batch_service.update_batch_progress(
            batch_id=batch_id,
            successful_count=3,
            failed_count=0,
            current_cost=0.005,
            error_messages=[],
        )

        # Fail the batch with partial progress
        await batch_service.fail_batch(
            batch_id=batch_id,
            error_message="API rate limit exceeded after processing 3 repositories",
            processing_time_ms=15000,
        )

        # Verify the batch state
        from sqlalchemy.future import select

        result = await async_db_session.execute(
            select(BatchAnalysis).filter_by(batch_id=batch_id)
        )
        batch = result.scalar_one_or_none()

        assert batch is not None
        assert batch.status == AnalysisStatus.FAILED
        assert batch.successful_count == 3
        assert batch.processing_time_ms == 15000
        assert "API rate limit exceeded" in json.loads(batch.error_messages)[0]
        assert batch.completed_at is not None

    @pytest.mark.asyncio
    async def test_fail_nonexistent_batch(
        self, batch_service: AsyncBatchHistoryService
    ) -> None:
        """Test failing a batch that doesn't exist."""
        with pytest.raises(ValueError, match="Batch fake-batch-id not found"):
            await batch_service.fail_batch(
                batch_id="fake-batch-id",
                error_message="This should fail",
            )

    @pytest.mark.asyncio
    async def test_concurrent_progress_updates(
        self, batch_service: AsyncBatchHistoryService, async_db_session: AsyncSession
    ) -> None:
        """Test handling concurrent progress updates (race condition)."""
        batch_id = await batch_service.create_batch_record(
            user_id="scale_user",
            repository_count=5,
            contexts=["startup"],
        )

        await batch_service.start_batch_processing(batch_id)

        # Simulate concurrent updates
        updates = [
            batch_service.update_batch_progress(
                batch_id=batch_id,
                successful_count=i,
                failed_count=0,
                current_cost=0.001 * i,
                error_messages=[],
            )
            for i in range(1, 6)
        ]

        # Execute all updates concurrently
        import asyncio

        await asyncio.gather(*updates, return_exceptions=True)

        # Verify final state
        from sqlalchemy.future import select

        result = await async_db_session.execute(
            select(BatchAnalysis).filter_by(batch_id=batch_id)
        )
        batch = result.scalar_one_or_none()

        assert batch is not None
        # Should have the highest update value
        assert batch.successful_count >= 1
        assert batch.status == AnalysisStatus.PROCESSING


class TestBatchStatisticsEdgeCases:
    """Test edge cases in batch statistics calculation."""

    @pytest.mark.asyncio
    async def test_statistics_with_no_batches(
        self, batch_service: AsyncBatchHistoryService
    ) -> None:
        """Test getting statistics when user has no batches."""
        stats = await batch_service.get_batch_statistics("nonexistent_user")

        assert stats["total_batches"] == 0
        assert stats["total_successful"] == 0
        assert stats["total_failed"] == 0
        assert stats["total_repositories"] == 0
        assert stats["total_cost"] == 0.0
        assert stats["avg_processing_time_ms"] == 0

    @pytest.mark.asyncio
    async def test_statistics_with_mixed_statuses(
        self, batch_service: AsyncBatchHistoryService, async_db_session: AsyncSession
    ) -> None:
        """Test statistics with batches in various states."""
        # Create batches in different states
        batch1 = await batch_service.create_batch_record(
            user_id="scale_user",
            repository_count=5,
            contexts=["startup"],
        )

        batch2 = await batch_service.create_batch_record(
            user_id="scale_user",
            repository_count=3,
            contexts=["enterprise"],
        )

        # Third batch (left pending)
        await batch_service.create_batch_record(
            user_id="scale_user",
            repository_count=2,
            contexts=["startup"],
        )

        # Complete first batch successfully
        await batch_service.complete_batch(
            batch_id=batch1,
            successful_count=5,
            failed_count=0,
            total_cost=0.025,
            processing_time_ms=30000,
            error_messages=[],
        )

        # Fail second batch
        await batch_service.fail_batch(
            batch_id=batch2,
            error_message="Network timeout",
            processing_time_ms=5000,
        )

        # Leave third batch in pending state

        stats = await batch_service.get_batch_statistics("scale_user")

        assert stats["total_batches"] == 3
        assert stats["total_successful"] == 5  # Only batch1 had 5 successful
        assert (
            stats["total_failed"] == 0
        )  # batch1 had 0 failed, batch2 failed entirely, batch3 pending
        assert stats["status_breakdown"]["completed"] == 1
        assert stats["status_breakdown"]["failed"] == 1
        assert stats["status_breakdown"]["pending"] == 1
        assert stats["total_repositories"] == 10  # 5 + 3 + 2
        assert stats["total_cost"] == 0.025
        assert int(stats["avg_processing_time_ms"]) == 17500  # (30000 + 5000) / 2


class TestBatchAggregationEdgeCases:
    """Test edge cases in batch insight aggregation."""

    @pytest.mark.asyncio
    async def test_aggregation_with_empty_insights(
        self, batch_service: AsyncBatchHistoryService
    ) -> None:
        """Test aggregation when batch has no insights."""
        batch_id = await batch_service.create_batch_record(
            user_id="scale_user",
            repository_count=1,
            contexts=["startup"],
        )

        # Complete batch with empty aggregated insights
        await batch_service.complete_batch(
            batch_id=batch_id,
            successful_count=0,
            failed_count=1,
            total_cost=0.0,
            processing_time_ms=1000,
            error_messages=["All repositories failed"],
        )

        insights = await batch_service.get_batch_aggregated_insights(
            batch_id, "scale_user"
        )

        # Should return empty structures or None
        if insights:
            assert insights.get("common_patterns", {}) == {}
            assert insights.get("technology_distribution", {}) == {}
            assert insights.get("quality_indicators", {}) == {}
        else:
            # It's okay to return None for empty insights
            assert insights is None

    @pytest.mark.asyncio
    async def test_aggregation_with_malformed_json(
        self, batch_service: AsyncBatchHistoryService, async_db_session: AsyncSession
    ) -> None:
        """Test handling malformed JSON in aggregated insights."""
        batch_id = await batch_service.create_batch_record(
            user_id="scale_user",
            repository_count=1,
            contexts=["startup"],
        )

        # Manually set malformed JSON
        from sqlalchemy.future import select

        result = await async_db_session.execute(
            select(BatchAnalysis).filter_by(batch_id=batch_id)
        )
        batch = result.scalar_one_or_none()

        if batch:
            batch.aggregated_insights = '{"broken": '  # Malformed JSON
            await async_db_session.commit()

        # Should handle gracefully
        insights = await batch_service.get_batch_aggregated_insights(
            batch_id, "scale_user"
        )

        # Should return None or empty structures for malformed JSON
        if insights:
            assert insights.get("common_patterns", {}) == {}
            assert insights.get("technology_distribution", {}) == {}
            assert insights.get("quality_indicators", {}) == {}
        else:
            assert insights is None


class TestBatchHistoryPagination:
    """Test pagination edge cases."""

    @pytest.mark.asyncio
    async def test_pagination_with_large_offset(
        self, batch_service: AsyncBatchHistoryService
    ) -> None:
        """Test pagination when offset exceeds total records."""
        # Create a few batches
        for i in range(3):
            await batch_service.create_batch_record(
                user_id="scale_user",
                repository_count=1,
                contexts=["startup"],
            )

        # Request with offset beyond total
        batches, total = await batch_service.get_batch_history(
            user_id="scale_user",
            limit=10,
            offset=100,  # Way beyond the 3 batches
        )

        assert len(batches) == 0
        assert total == 3

    @pytest.mark.asyncio
    async def test_pagination_with_status_filter(
        self, batch_service: AsyncBatchHistoryService
    ) -> None:
        """Test pagination with status filtering."""
        # Create batches with different statuses
        batch1 = await batch_service.create_batch_record(
            user_id="scale_user",
            repository_count=1,
            contexts=["startup"],
        )

        batch2 = await batch_service.create_batch_record(
            user_id="scale_user",
            repository_count=1,
            contexts=["startup"],
        )

        # Complete one, fail the other
        await batch_service.complete_batch(
            batch_id=batch1,
            successful_count=1,
            failed_count=0,
            total_cost=0.01,
            processing_time_ms=5000,
            error_messages=[],
        )

        await batch_service.fail_batch(
            batch_id=batch2,
            error_message="Test failure",
        )

        # Filter for completed only
        completed, total_completed = await batch_service.get_batch_history(
            user_id="scale_user",
            limit=10,
            offset=0,
            status_filter="completed",
        )

        assert len(completed) == 1
        assert total_completed == 1

        # Filter for failed only
        failed, total_failed = await batch_service.get_batch_history(
            user_id="scale_user",
            limit=10,
            offset=0,
            status_filter="failed",
        )

        assert len(failed) == 1
        assert total_failed == 1
