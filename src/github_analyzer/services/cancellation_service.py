# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Task cancellation service with smart timing constraints.

Manages running analysis tasks and provides cancellation capabilities
with timing windows to prevent token waste.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional, Set

from ..utils.logging import get_logger

logger = get_logger(__name__)


class TaskType(Enum):
    SINGLE_ANALYSIS = "single_analysis"
    BATCH_ANALYSIS = "batch_analysis"


class TaskStatus(Enum):
    RUNNING = "running"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class RunningTask:
    task_id: str
    task_type: TaskType
    user_id: str
    started_at: datetime
    cancel_deadline: datetime
    asyncio_task: Optional[asyncio.Task[Any]] = None
    status: TaskStatus = TaskStatus.RUNNING


class CancellationService:
    """
    Service for managing task cancellation with smart timing constraints.

    Timing Windows:
    - Single analysis: 10 seconds (before heavy token usage)
    - Batch analysis: 30 seconds (more complex setup time)
    """

    def __init__(self) -> None:
        self._running_tasks: Dict[str, RunningTask] = {}
        self._user_tasks: Dict[str, Set[str]] = {}  # user_id -> set of task_ids

    def register_task(
        self,
        task_id: str,
        task_type: TaskType,
        user_id: str,
        asyncio_task: Optional[asyncio.Task[Any]] = None,
    ) -> RunningTask:
        """Register a new running task with cancellation window."""
        now = datetime.now(timezone.utc)

        # Set cancellation deadline based on task type
        if task_type == TaskType.SINGLE_ANALYSIS:
            cancel_window_seconds = 10
        elif task_type == TaskType.BATCH_ANALYSIS:
            cancel_window_seconds = 30
        else:
            cancel_window_seconds = 10  # Default fallback

        from datetime import timedelta

        cancel_deadline = now + timedelta(seconds=cancel_window_seconds)

        task = RunningTask(
            task_id=task_id,
            task_type=task_type,
            user_id=user_id,
            started_at=now,
            cancel_deadline=cancel_deadline,
            asyncio_task=asyncio_task,
            status=TaskStatus.RUNNING,
        )

        self._running_tasks[task_id] = task

        # Track by user
        if user_id not in self._user_tasks:
            self._user_tasks[user_id] = set()
        self._user_tasks[user_id].add(task_id)

        logger.info(
            f"Registered {task_type.value} task {task_id} for user {user_id}, "
            f"cancellable until {cancel_deadline.isoformat()}"
        )

        return task

    def can_cancel_task(self, task_id: str) -> tuple[bool, str]:
        """Check if a task can be cancelled and return reason."""
        task = self._running_tasks.get(task_id)

        if not task:
            return False, "Task not found or already completed"

        if task.status != TaskStatus.RUNNING:
            return False, f"Task is {task.status.value}, cannot cancel"

        now = datetime.now(timezone.utc)
        if now > task.cancel_deadline:
            return (
                False,
                f"Cancellation window expired (deadline was {task.cancel_deadline.isoformat()})",
            )

        return True, "Task can be cancelled"

    async def cancel_task(self, task_id: str, user_id: str) -> tuple[bool, str]:
        """Cancel a running task if within the cancellation window."""
        task = self._running_tasks.get(task_id)

        if not task:
            return False, "Task not found"

        # Verify ownership
        if task.user_id != user_id:
            return False, "Permission denied: task belongs to different user"

        # Check if cancellation is allowed
        can_cancel, reason = self.can_cancel_task(task_id)
        if not can_cancel:
            return False, reason

        # Cancel the asyncio task if it exists
        if task.asyncio_task and not task.asyncio_task.done():
            task.asyncio_task.cancel()
            logger.info(f"Cancelled asyncio task for {task_id}")

        # Update task status
        task.status = TaskStatus.CANCELLED

        # Clean up tracking
        self._cleanup_task(task_id, user_id)

        logger.info(
            f"Successfully cancelled {task.task_type.value} task {task_id} for user {user_id}"
        )

        return True, "Task cancelled successfully"

    def complete_task(
        self, task_id: str, status: TaskStatus = TaskStatus.COMPLETED
    ) -> None:
        """Mark a task as completed and clean up."""
        task = self._running_tasks.get(task_id)
        if task:
            task.status = status
            self._cleanup_task(task_id, task.user_id)
            logger.info(f"Task {task_id} marked as {status.value}")

    def _cleanup_task(self, task_id: str, user_id: str) -> None:
        """Remove task from tracking."""
        if task_id in self._running_tasks:
            del self._running_tasks[task_id]

        if user_id in self._user_tasks:
            self._user_tasks[user_id].discard(task_id)
            if not self._user_tasks[user_id]:
                del self._user_tasks[user_id]

    def get_user_running_tasks(self, user_id: str) -> list[RunningTask]:
        """Get all running tasks for a user."""
        task_ids = self._user_tasks.get(user_id, set())
        return [
            self._running_tasks[task_id]
            for task_id in task_ids
            if task_id in self._running_tasks
        ]

    def get_task_info(self, task_id: str) -> Optional[RunningTask]:
        """Get information about a specific task."""
        return self._running_tasks.get(task_id)

    def cleanup_expired_tasks(self) -> int:
        """Clean up tasks that are past their cancellation deadline."""
        now = datetime.now(timezone.utc)
        expired_tasks = []

        for task_id, task in self._running_tasks.items():
            if task.status == TaskStatus.RUNNING and now > task.cancel_deadline:
                expired_tasks.append((task_id, task.user_id))

        for task_id, user_id in expired_tasks:
            self._cleanup_task(task_id, user_id)

        if expired_tasks:
            logger.info(f"Cleaned up {len(expired_tasks)} expired tasks")

        return len(expired_tasks)


# Global instance
_cancellation_service: Optional[CancellationService] = None


def get_cancellation_service() -> CancellationService:
    """Get the global cancellation service instance."""
    global _cancellation_service
    if _cancellation_service is None:
        _cancellation_service = CancellationService()
    return _cancellation_service
