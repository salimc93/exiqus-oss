# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Scheduler management endpoints for administrators.

This module provides REST API endpoints for managing scheduled tasks,
including viewing task status and manually triggering task execution.
"""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from ...database.models import User
from ...utils.logging import get_logger
from ..auth.dependencies import get_current_active_user, get_current_admin_user
from ..services.scheduler_service import get_scheduler_service

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/scheduler", tags=["scheduler"])


@router.get("/tasks", response_model=List[Dict[str, Any]])
async def get_scheduled_tasks(
    current_user: User = Depends(get_current_admin_user),
) -> List[Dict[str, Any]]:
    """
    Get status of all scheduled tasks.

    Returns information about all registered scheduled tasks including
    their last run time, next run time, and error counts.

    Admin access required.
    """
    scheduler = await get_scheduler_service()
    return scheduler.get_task_status()


@router.post("/tasks/{task_name}/run", response_model=Dict[str, Any])
async def run_task_manually(
    task_name: str,
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Manually trigger a scheduled task.

    Runs the specified task immediately, regardless of its schedule.
    Useful for testing or emergency operations.

    Admin access required.

    Args:
        task_name: Name of the task to run

    Returns:
        Task execution result

    Raises:
        HTTPException: If task not found or execution fails
    """
    scheduler = await get_scheduler_service()

    try:
        result = await scheduler.run_task_manually(task_name)
        logger.info(f"Admin {current_user.email} manually triggered task: {task_name}")
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to run task {task_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to execute task: {str(e)}")


@router.put("/tasks/{task_name}/toggle", response_model=Dict[str, str])
async def toggle_task_enabled(
    task_name: str,
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, str]:
    """
    Enable or disable a scheduled task.

    Toggles the enabled state of a task. Disabled tasks will not run
    on their schedule but can still be triggered manually.

    Admin access required.

    Args:
        task_name: Name of the task to toggle

    Returns:
        Updated task status

    Raises:
        HTTPException: If task not found
    """
    scheduler = await get_scheduler_service()

    task = scheduler.tasks.get(task_name)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_name}")

    # Toggle enabled state
    task.enabled = not task.enabled
    new_state = "enabled" if task.enabled else "disabled"

    logger.info(f"Admin {current_user.email} {new_state} task: {task_name}")

    return {
        "task_name": task_name,
        "status": new_state,
        "message": f"Task {task_name} has been {new_state}",
    }


@router.post("/quota/reset-monthly", response_model=Dict[str, Any])
async def trigger_monthly_quota_reset(
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Manually trigger monthly quota reset.

    Runs the monthly quota reset task immediately. This will reset
    usage for all users whose billing period starts today.

    Admin access required.

    Returns:
        Reset operation result
    """
    scheduler = await get_scheduler_service()

    try:
        result = await scheduler.run_task_manually("monthly_quota_reset")
        logger.info(
            f"Admin {current_user.email} manually triggered monthly quota reset"
        )
        return {
            "success": True,
            "message": "Monthly quota reset completed",
            "task_result": result,
        }
    except Exception as e:
        logger.error(f"Failed to run monthly quota reset: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset quotas: {str(e)}")


@router.get("/health", response_model=Dict[str, Any])
async def get_scheduler_health(
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Get scheduler service health status.

    Returns information about the scheduler's operational status.

    Requires authentication.
    """
    scheduler = await get_scheduler_service()

    tasks = scheduler.get_task_status()
    total_tasks = len(tasks)
    enabled_tasks = sum(1 for task in tasks if task["enabled"])
    tasks_with_errors = sum(1 for task in tasks if task["error_count"] > 0)

    # Get scheduler uptime from monthly quota reset task
    scheduler_uptime = None
    quota_reset_task = scheduler.tasks.get("monthly_quota_reset")
    if quota_reset_task and quota_reset_task.last_run:
        scheduler_uptime = quota_reset_task.last_run.isoformat()

    return {
        "status": "healthy" if scheduler.running else "stopped",
        "running": scheduler.running,
        "total_tasks": total_tasks,
        "enabled_tasks": enabled_tasks,
        "tasks_with_errors": tasks_with_errors,
        "scheduler_uptime": scheduler_uptime,
    }
