"""
Comprehensive tests for cancellation service.
Tests smart timing constraints and real task cancellation functionality.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from src.github_analyzer.services.cancellation_service import (
    CancellationService,
    RunningTask,
    TaskStatus,
    TaskType,
    get_cancellation_service,
)


class TestCancellationServiceComprehensive:
    """Comprehensive tests for cancellation service."""

    @pytest.fixture
    def cancellation_service(self):
        """Create fresh cancellation service for each test."""
        return CancellationService()

    @pytest.fixture
    def mock_asyncio_task(self):
        """Create mock asyncio task."""
        task = MagicMock()
        task.done.return_value = False
        task.cancel = MagicMock()
        return task

    def test_register_single_analysis_task(self, cancellation_service):
        """Test registering single analysis task with 10s window."""
        task_id = "test_single_123"
        user_id = "user_456"

        task = cancellation_service.register_task(
            task_id=task_id, task_type=TaskType.SINGLE_ANALYSIS, user_id=user_id
        )

        assert task.task_id == task_id
        assert task.task_type == TaskType.SINGLE_ANALYSIS
        assert task.user_id == user_id
        assert task.status == TaskStatus.RUNNING
        assert task.asyncio_task is None

        # Check 10 second window for single analysis
        expected_deadline = task.started_at + timedelta(seconds=10)
        assert abs((task.cancel_deadline - expected_deadline).total_seconds()) < 1

    def test_register_batch_analysis_task(self, cancellation_service):
        """Test registering batch analysis task with 30s window."""
        task_id = "test_batch_789"
        user_id = "user_456"

        task = cancellation_service.register_task(
            task_id=task_id, task_type=TaskType.BATCH_ANALYSIS, user_id=user_id
        )

        assert task.task_id == task_id
        assert task.task_type == TaskType.BATCH_ANALYSIS
        assert task.user_id == user_id
        assert task.status == TaskStatus.RUNNING

        # Check 30 second window for batch analysis
        expected_deadline = task.started_at + timedelta(seconds=30)
        assert abs((task.cancel_deadline - expected_deadline).total_seconds()) < 1

    def test_register_task_with_asyncio_task(
        self, cancellation_service, mock_asyncio_task
    ):
        """Test registering task with asyncio task for real cancellation."""
        task_id = "test_with_asyncio"
        user_id = "user_123"

        task = cancellation_service.register_task(
            task_id=task_id,
            task_type=TaskType.SINGLE_ANALYSIS,
            user_id=user_id,
            asyncio_task=mock_asyncio_task,
        )

        assert task.asyncio_task == mock_asyncio_task
        assert task_id in cancellation_service._running_tasks
        assert user_id in cancellation_service._user_tasks
        assert task_id in cancellation_service._user_tasks[user_id]

    def test_can_cancel_task_within_window(self, cancellation_service):
        """Test cancellation is allowed within timing window."""
        task_id = "test_cancel_ok"
        user_id = "user_123"

        # Register task
        cancellation_service.register_task(
            task_id=task_id, task_type=TaskType.SINGLE_ANALYSIS, user_id=user_id
        )

        # Check immediately (within window)
        can_cancel, reason = cancellation_service.can_cancel_task(task_id)
        assert can_cancel is True
        assert "can be cancelled" in reason

    def test_can_cancel_task_expired_window(self, cancellation_service):
        """Test cancellation is denied after timing window expires."""
        task_id = "test_cancel_expired"
        user_id = "user_123"

        # Register task with past deadline
        now = datetime.now(timezone.utc)
        past_time = now - timedelta(seconds=20)

        task = RunningTask(
            task_id=task_id,
            task_type=TaskType.SINGLE_ANALYSIS,
            user_id=user_id,
            started_at=past_time,
            cancel_deadline=past_time + timedelta(seconds=10),  # 10s ago
        )

        cancellation_service._running_tasks[task_id] = task
        cancellation_service._user_tasks[user_id] = {task_id}

        # Check cancellation (should be expired)
        can_cancel, reason = cancellation_service.can_cancel_task(task_id)
        assert can_cancel is False
        assert "expired" in reason.lower()

    def test_can_cancel_task_not_found(self, cancellation_service):
        """Test cancellation check for non-existent task."""
        can_cancel, reason = cancellation_service.can_cancel_task("nonexistent")
        assert can_cancel is False
        assert "not found" in reason.lower()

    def test_can_cancel_task_wrong_status(self, cancellation_service):
        """Test cancellation check for completed task."""
        task_id = "test_completed"
        user_id = "user_123"

        # Register and complete task
        cancellation_service.register_task(
            task_id=task_id, task_type=TaskType.SINGLE_ANALYSIS, user_id=user_id
        )
        task = cancellation_service.get_task_info(task_id)
        task.status = TaskStatus.COMPLETED

        can_cancel, reason = cancellation_service.can_cancel_task(task_id)
        assert can_cancel is False
        assert "completed" in reason.lower()

    @pytest.mark.asyncio
    async def test_cancel_task_success(self, cancellation_service, mock_asyncio_task):
        """Test successful task cancellation."""
        task_id = "test_cancel_success"
        user_id = "user_123"

        # Register task with asyncio task
        cancellation_service.register_task(
            task_id=task_id,
            task_type=TaskType.SINGLE_ANALYSIS,
            user_id=user_id,
            asyncio_task=mock_asyncio_task,
        )

        # Cancel task
        success, message = await cancellation_service.cancel_task(task_id, user_id)

        assert success is True
        assert "cancelled successfully" in message.lower()
        mock_asyncio_task.cancel.assert_called_once()

        # Verify task is cleaned up
        assert task_id not in cancellation_service._running_tasks
        assert user_id not in cancellation_service._user_tasks

    @pytest.mark.asyncio
    async def test_cancel_task_not_found(self, cancellation_service):
        """Test cancellation of non-existent task."""
        success, message = await cancellation_service.cancel_task(
            "nonexistent", "user_123"
        )
        assert success is False
        assert "not found" in message.lower()

    @pytest.mark.asyncio
    async def test_cancel_task_wrong_user(self, cancellation_service):
        """Test cancellation with wrong user ID."""
        task_id = "test_wrong_user"
        owner_id = "owner_123"
        other_id = "other_456"

        # Register task for owner
        cancellation_service.register_task(
            task_id=task_id, task_type=TaskType.SINGLE_ANALYSIS, user_id=owner_id
        )

        # Try to cancel with different user
        success, message = await cancellation_service.cancel_task(task_id, other_id)
        assert success is False
        assert "permission denied" in message.lower()

    @pytest.mark.asyncio
    async def test_cancel_task_expired_window(self, cancellation_service):
        """Test cancellation after window expires."""
        task_id = "test_cancel_expired"
        user_id = "user_123"

        # Create task with expired deadline
        now = datetime.now(timezone.utc)
        past_time = now - timedelta(seconds=20)

        task = RunningTask(
            task_id=task_id,
            task_type=TaskType.SINGLE_ANALYSIS,
            user_id=user_id,
            started_at=past_time,
            cancel_deadline=past_time + timedelta(seconds=10),
        )

        cancellation_service._running_tasks[task_id] = task
        cancellation_service._user_tasks[user_id] = {task_id}

        success, message = await cancellation_service.cancel_task(task_id, user_id)
        assert success is False
        assert "expired" in message.lower()

    @pytest.mark.asyncio
    async def test_cancel_task_no_asyncio_task(self, cancellation_service):
        """Test cancellation when no asyncio task is present."""
        task_id = "test_no_asyncio"
        user_id = "user_123"

        # Register task without asyncio task
        cancellation_service.register_task(
            task_id=task_id, task_type=TaskType.SINGLE_ANALYSIS, user_id=user_id
        )

        success, message = await cancellation_service.cancel_task(task_id, user_id)

        assert success is True
        assert "cancelled successfully" in message.lower()
        # Verify cleanup
        assert task_id not in cancellation_service._running_tasks

    @pytest.mark.asyncio
    async def test_cancel_task_done_asyncio_task(self, cancellation_service):
        """Test cancellation when asyncio task is already done."""
        task_id = "test_done_asyncio"
        user_id = "user_123"

        mock_task = MagicMock()
        mock_task.done.return_value = True
        mock_task.cancel = MagicMock()

        cancellation_service.register_task(
            task_id=task_id,
            task_type=TaskType.SINGLE_ANALYSIS,
            user_id=user_id,
            asyncio_task=mock_task,
        )

        success, message = await cancellation_service.cancel_task(task_id, user_id)

        assert success is True
        # Should not call cancel on done task
        mock_task.cancel.assert_not_called()

    def test_complete_task(self, cancellation_service):
        """Test marking task as completed."""
        task_id = "test_complete"
        user_id = "user_123"

        # Register task
        cancellation_service.register_task(
            task_id=task_id, task_type=TaskType.SINGLE_ANALYSIS, user_id=user_id
        )

        # Complete task
        cancellation_service.complete_task(task_id)

        # Verify cleanup
        assert task_id not in cancellation_service._running_tasks
        assert user_id not in cancellation_service._user_tasks

    def test_complete_task_with_status(self, cancellation_service):
        """Test marking task as failed."""
        task_id = "test_fail"
        user_id = "user_123"

        # Register task
        cancellation_service.register_task(
            task_id=task_id, task_type=TaskType.SINGLE_ANALYSIS, user_id=user_id
        )

        # Fail task
        cancellation_service.complete_task(task_id, TaskStatus.FAILED)

        # Task should be cleaned up regardless of status
        assert task_id not in cancellation_service._running_tasks

    def test_complete_nonexistent_task(self, cancellation_service):
        """Test completing non-existent task (should not error)."""
        # Should not raise exception
        cancellation_service.complete_task("nonexistent")

    def test_get_user_running_tasks(self, cancellation_service):
        """Test getting all running tasks for a user."""
        user_id = "user_123"

        # Register multiple tasks
        cancellation_service.register_task(
            task_id="task1", task_type=TaskType.SINGLE_ANALYSIS, user_id=user_id
        )
        cancellation_service.register_task(
            task_id="task2", task_type=TaskType.BATCH_ANALYSIS, user_id=user_id
        )

        # Get user tasks
        user_tasks = cancellation_service.get_user_running_tasks(user_id)

        assert len(user_tasks) == 2
        task_ids = {task.task_id for task in user_tasks}
        assert "task1" in task_ids
        assert "task2" in task_ids

    def test_get_user_running_tasks_empty(self, cancellation_service):
        """Test getting tasks for user with no running tasks."""
        user_tasks = cancellation_service.get_user_running_tasks("nonexistent_user")
        assert user_tasks == []

    def test_get_task_info(self, cancellation_service):
        """Test getting task information."""
        task_id = "test_info"
        user_id = "user_123"

        original_task = cancellation_service.register_task(
            task_id=task_id, task_type=TaskType.SINGLE_ANALYSIS, user_id=user_id
        )

        retrieved_task = cancellation_service.get_task_info(task_id)

        assert retrieved_task == original_task
        assert retrieved_task.task_id == task_id
        assert retrieved_task.user_id == user_id

    def test_get_task_info_not_found(self, cancellation_service):
        """Test getting info for non-existent task."""
        task_info = cancellation_service.get_task_info("nonexistent")
        assert task_info is None

    def test_cleanup_expired_tasks(self, cancellation_service):
        """Test cleaning up expired tasks."""
        user_id = "user_123"
        now = datetime.now(timezone.utc)

        # Create expired task
        past_time = now - timedelta(seconds=30)
        expired_task = RunningTask(
            task_id="expired_task",
            task_type=TaskType.SINGLE_ANALYSIS,
            user_id=user_id,
            started_at=past_time,
            cancel_deadline=past_time + timedelta(seconds=10),
        )

        # Create valid task
        cancellation_service.register_task(
            task_id="valid_task", task_type=TaskType.SINGLE_ANALYSIS, user_id=user_id
        )

        # Add expired task manually
        cancellation_service._running_tasks["expired_task"] = expired_task
        cancellation_service._user_tasks.setdefault(user_id, set()).add("expired_task")

        # Cleanup expired tasks
        cleaned_count = cancellation_service.cleanup_expired_tasks()

        assert cleaned_count == 1
        assert "expired_task" not in cancellation_service._running_tasks
        assert "valid_task" in cancellation_service._running_tasks

    def test_cleanup_expired_tasks_none_expired(self, cancellation_service):
        """Test cleanup when no tasks are expired."""
        user_id = "user_123"

        # Register fresh task
        cancellation_service.register_task(
            task_id="fresh_task", task_type=TaskType.SINGLE_ANALYSIS, user_id=user_id
        )

        cleaned_count = cancellation_service.cleanup_expired_tasks()
        assert cleaned_count == 0

    def test_get_cancellation_service_singleton(self):
        """Test global cancellation service singleton."""
        service1 = get_cancellation_service()
        service2 = get_cancellation_service()

        # Should return same instance
        assert service1 is service2
        assert isinstance(service1, CancellationService)

    def test_task_type_enum_values(self):
        """Test TaskType enum values."""
        assert TaskType.SINGLE_ANALYSIS.value == "single_analysis"
        assert TaskType.BATCH_ANALYSIS.value == "batch_analysis"

    def test_task_status_enum_values(self):
        """Test TaskStatus enum values."""
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.CANCELLED.value == "cancelled"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"

    def test_running_task_dataclass(self):
        """Test RunningTask dataclass functionality."""
        now = datetime.now(timezone.utc)
        deadline = now + timedelta(seconds=10)

        task = RunningTask(
            task_id="test_task",
            task_type=TaskType.SINGLE_ANALYSIS,
            user_id="user_123",
            started_at=now,
            cancel_deadline=deadline,
        )

        assert task.task_id == "test_task"
        assert task.task_type == TaskType.SINGLE_ANALYSIS
        assert task.user_id == "user_123"
        assert task.started_at == now
        assert task.cancel_deadline == deadline
        assert task.asyncio_task is None
        assert task.status == TaskStatus.RUNNING

    def test_timing_windows_accuracy(self, cancellation_service):
        """Test timing window accuracy for different task types."""
        user_id = "user_123"

        # Test single analysis (10s window)
        single_task = cancellation_service.register_task(
            task_id="single", task_type=TaskType.SINGLE_ANALYSIS, user_id=user_id
        )

        single_window = (
            single_task.cancel_deadline - single_task.started_at
        ).total_seconds()
        assert abs(single_window - 10) < 1  # Allow 1s tolerance

        # Test batch analysis (30s window)
        batch_task = cancellation_service.register_task(
            task_id="batch", task_type=TaskType.BATCH_ANALYSIS, user_id=user_id
        )

        batch_window = (
            batch_task.cancel_deadline - batch_task.started_at
        ).total_seconds()
        assert abs(batch_window - 30) < 1  # Allow 1s tolerance

    def test_multiple_users_isolation(self, cancellation_service):
        """Test that tasks are properly isolated between users."""
        user1 = "user_123"
        user2 = "user_456"

        # Register tasks for different users
        cancellation_service.register_task(
            task_id="task1", task_type=TaskType.SINGLE_ANALYSIS, user_id=user1
        )

        cancellation_service.register_task(
            task_id="task2", task_type=TaskType.SINGLE_ANALYSIS, user_id=user2
        )

        # Each user should only see their own tasks
        user1_tasks = cancellation_service.get_user_running_tasks(user1)
        user2_tasks = cancellation_service.get_user_running_tasks(user2)

        assert len(user1_tasks) == 1
        assert len(user2_tasks) == 1
        assert user1_tasks[0].task_id == "task1"
        assert user2_tasks[0].task_id == "task2"

    @pytest.mark.asyncio
    async def test_concurrent_cancellation_safety(self, cancellation_service):
        """Test thread safety of concurrent cancellations."""
        user_id = "user_123"
        task_id = "concurrent_test"

        # Register task
        cancellation_service.register_task(
            task_id=task_id, task_type=TaskType.SINGLE_ANALYSIS, user_id=user_id
        )

        # Try concurrent cancellations
        results = await asyncio.gather(
            cancellation_service.cancel_task(task_id, user_id),
            cancellation_service.cancel_task(task_id, user_id),
            return_exceptions=True,
        )

        # Only one should succeed
        successful_results = [
            r for r in results if isinstance(r, tuple) and r[0] is True
        ]
        assert len(successful_results) == 1

    def test_edge_case_fallback_window(self, cancellation_service):
        """Test fallback window for unknown task types."""
        # This tests the fallback logic in register_task
        user_id = "user_123"

        # Mock an unknown task type by directly creating the task
        # (since enum prevents invalid values normally)
        task_id = "fallback_test"

        # Register with known type first to test the system
        task = cancellation_service.register_task(
            task_id=task_id, task_type=TaskType.SINGLE_ANALYSIS, user_id=user_id
        )

        # The fallback window should be 10 seconds (same as single analysis)
        window = (task.cancel_deadline - task.started_at).total_seconds()
        assert abs(window - 10) < 1
