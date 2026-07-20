# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Scheduler service for automated tasks.

This module provides scheduled task management for periodic operations
like monthly quota resets, usage report generation, and cleanup tasks.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ...billing.usage_reporter import UsageReporter
from ...database.models import SubscriptionPlan
from ...database.operations import SystemMetricOperations, UserOperations
from ...utils.logging import get_logger

logger = get_logger(__name__)


class ScheduledTask:
    """Represents a scheduled task."""

    def __init__(
        self,
        name: str,
        func: Callable[..., Coroutine[Any, Any, Any]],
        interval_seconds: int,
        enabled: bool = True,
        run_on_startup: bool = False,
    ):
        self.name = name
        self.func = func
        self.interval_seconds = interval_seconds
        self.enabled = enabled
        self.run_on_startup = run_on_startup
        self.last_run: Optional[datetime] = None
        self.next_run: Optional[datetime] = None
        self.run_count: int = 0
        self.error_count: int = 0
        self.last_error: Optional[str] = None

    def should_run(self, now: datetime) -> bool:
        """Check if task should run based on schedule."""
        if not self.enabled:
            return False

        if self.next_run is None:
            return True

        return now >= self.next_run

    def update_next_run(self, from_time: datetime) -> None:
        """Update next run time based on interval."""
        self.next_run = from_time + timedelta(seconds=self.interval_seconds)


class SchedulerService:
    """
    Service for managing scheduled tasks.

    Provides automated task execution for periodic operations.
    """

    def __init__(
        self, session_factory: Optional[async_sessionmaker[AsyncSession]] = None
    ) -> None:
        self.tasks: Dict[str, ScheduledTask] = {}
        self.running = False
        self.task_loop: Optional[asyncio.Task[None]] = None
        self._session_factory = session_factory
        self._initialize_tasks()

    def set_session_factory(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Set the database session factory."""
        self._session_factory = session_factory

    def _initialize_tasks(self) -> None:
        """Initialize scheduled tasks."""
        # Monthly quota reset task - runs daily to catch any users
        # whose billing period starts that day
        self.register_task(
            name="monthly_quota_reset",
            func=self._reset_monthly_quotas,
            interval_seconds=3600 * 24,  # 24 hours
            run_on_startup=True,
        )

        # Cleanup old metrics - runs weekly
        self.register_task(
            name="cleanup_old_metrics",
            func=self._cleanup_old_metrics,
            interval_seconds=3600 * 24 * 7,  # 7 days
            run_on_startup=False,
        )

        # Generate usage reports - runs daily
        self.register_task(
            name="generate_usage_reports",
            func=self._generate_usage_reports,
            interval_seconds=3600 * 24,  # 24 hours
            run_on_startup=False,
        )

        # Report usage to Stripe - runs hourly
        self.register_task(
            name="report_usage_to_stripe",
            func=self._report_usage_to_stripe,
            interval_seconds=3600,  # 1 hour
            run_on_startup=False,
        )

    def register_task(
        self,
        name: str,
        func: Callable[..., Coroutine[Any, Any, Any]],
        interval_seconds: int,
        enabled: bool = True,
        run_on_startup: bool = False,
    ) -> None:
        """Register a new scheduled task."""
        task = ScheduledTask(
            name=name,
            func=func,
            interval_seconds=interval_seconds,
            enabled=enabled,
            run_on_startup=run_on_startup,
        )
        self.tasks[name] = task
        logger.info(
            f"Registered scheduled task: {name} (interval: {interval_seconds}s)"
        )

    async def start(self) -> None:
        """Start the scheduler service."""
        if self.running:
            logger.warning("Scheduler already running")
            return

        self.running = True
        self.task_loop = asyncio.create_task(self._run_scheduler())
        logger.info("Scheduler service started")

        # Run startup tasks
        await self._run_startup_tasks()

    async def stop(self) -> None:
        """Stop the scheduler service."""
        self.running = False
        if self.task_loop:
            self.task_loop.cancel()
            try:
                await self.task_loop
            except asyncio.CancelledError:
                pass
        logger.info("Scheduler service stopped")

    async def _run_scheduler(self) -> None:
        """Main scheduler loop."""
        while self.running:
            try:
                now = datetime.now(timezone.utc)
                await self._check_and_run_tasks(now)
                await asyncio.sleep(60)  # Check every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)

    async def _run_startup_tasks(self) -> None:
        """Run tasks marked for startup."""
        for task in self.tasks.values():
            if task.run_on_startup:
                logger.info(f"Running startup task: {task.name}")
                await self._execute_task(task)

    async def _check_and_run_tasks(self, now: datetime) -> None:
        """Check and run due tasks."""
        for task in self.tasks.values():
            if task.should_run(now):
                await self._execute_task(task)

    async def _execute_task(self, task: ScheduledTask) -> None:
        """Execute a scheduled task."""
        try:
            logger.info(f"Executing scheduled task: {task.name}")
            start_time = datetime.now(timezone.utc)

            await task.func()

            task.last_run = start_time
            task.update_next_run(start_time)
            task.run_count += 1

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(
                f"Completed scheduled task: {task.name} "
                f"(duration: {duration:.2f}s, run #{task.run_count})"
            )

            # Record metric
            if self._session_factory:
                async with self._session_factory() as session:
                    await SystemMetricOperations.record_metric(
                        db=session,
                        metric_name="scheduled_task_execution",
                        metric_type="counter",
                        metric_value={
                            "task_name": task.name,
                            "duration_seconds": duration,
                            "success": True,
                        },
                        labels={"task": task.name},
                    )
                    await session.commit()

        except Exception as e:
            task.error_count += 1
            task.last_error = str(e)
            task.update_next_run(datetime.now(timezone.utc))

            logger.error(
                f"Error executing scheduled task {task.name}: {e}",
                exc_info=True,
            )

            # Record error metric
            if self._session_factory:
                try:
                    async with self._session_factory() as session:
                        await SystemMetricOperations.record_metric(
                            db=session,
                            metric_name="scheduled_task_error",
                            metric_type="counter",
                            metric_value={
                                "task_name": task.name,
                                "error": str(e),
                            },
                            labels={"task": task.name},
                        )
                        await session.commit()
                except Exception as e:
                    logger.warning(f"Failed to record metric for task {task.name}: {e}")

    # Scheduled task implementations

    async def _reset_monthly_quotas(self) -> None:
        """
        Reset monthly quotas for users whose billing period starts today.

        This task runs daily and checks for users whose billing period
        starts on the current day of the month.
        """
        logger.info("Starting monthly quota reset task")

        if not self._session_factory:
            logger.error("No session factory available for monthly quota reset")
            return

        async with self._session_factory() as session:
            # Get current day of month
            today = datetime.now(timezone.utc)
            current_day = today.day

            # Get all active users in pages to avoid memory issues
            offset = 0
            limit = 100
            reset_count = 0
            error_count = 0

            while True:
                users = await UserOperations.get_all_users(
                    session, offset=offset, limit=limit, active_only=True
                )
                if not users:
                    break

                for user in users:
                    try:
                        # Determine billing cycle start day
                        if user.subscription_start_date:
                            billing_day = user.subscription_start_date.day
                        elif user.created_at:
                            billing_day = user.created_at.day
                        else:
                            # Skip if no dates available
                            continue

                        # Check if today is the user's billing day
                        if billing_day == current_day:
                            # Reset usage for this user
                            success = await UserOperations.update_usage_count(
                                session, user.user_id, 0
                            )
                            if success:
                                reset_count += 1
                                logger.info(
                                    f"Reset monthly usage for user {user.user_id} "
                                    f"(plan: {user.subscription_plan.value})"
                                )
                            else:
                                error_count += 1

                    except Exception as e:
                        error_count += 1
                        logger.error(
                            f"Error resetting usage for user {user.user_id}: {e}"
                        )

                offset += limit

            await session.commit()

            logger.info(
                "Monthly quota reset completed: "
                f"{reset_count} users reset, {error_count} errors"
            )

            # Record completion metric
            await SystemMetricOperations.record_metric(
                db=session,
                metric_name="monthly_quota_reset",
                metric_type="gauge",
                metric_value={
                    "users_reset": reset_count,
                    "errors": error_count,
                    "date": today.isoformat(),
                },
            )

    async def _cleanup_old_metrics(self) -> None:
        """Clean up old system metrics older than 90 days."""
        logger.info("Starting metrics cleanup task")

        if not self._session_factory:
            logger.error("No session factory available for metrics cleanup")
            return

        async with self._session_factory() as session:
            # This would be implemented based on your retention policy
            # For now, just log
            logger.info("Metrics cleanup completed (not implemented)")
            await session.commit()

    async def _generate_usage_reports(self) -> None:
        """Generate daily usage reports for monitoring."""
        logger.info("Starting usage report generation")

        if not self._session_factory:
            logger.error("No session factory available for usage reports")
            return

        async with self._session_factory() as session:
            # Get usage statistics for the previous day
            yesterday = datetime.now(timezone.utc) - timedelta(days=1)
            billing_period = yesterday.strftime("%Y-%m")

            # Get usage by plan
            usage_by_plan: Dict[str, Dict[str, Any]] = {}

            for plan in SubscriptionPlan:
                users = await UserOperations.get_users_by_subscription_plan(
                    session, plan, limit=10000
                )

                total_usage = sum(user.usage_count for user in users)
                active_users = sum(bool(user.usage_count) for user in users)

                usage_by_plan[plan.value] = {
                    "total_users": len(users),
                    "active_users": active_users,
                    "total_usage": total_usage,
                    "average_usage": total_usage / len(users) if users else 0,
                }

            logger.info(f"Usage report for {billing_period}: {usage_by_plan}")

            # Record report metric
            await SystemMetricOperations.record_metric(
                db=session,
                metric_name="daily_usage_report",
                metric_type="gauge",
                metric_value={
                    "date": yesterday.isoformat(),
                    "billing_period": billing_period,
                    "usage_by_plan": usage_by_plan,
                },
            )

    async def _report_usage_to_stripe(self) -> None:
        """Report unreported usage to Stripe for metered billing."""
        logger.info("Starting usage reporting to Stripe")

        if not self._session_factory:
            logger.error("No session factory available for usage reporting")
            return

        try:
            # Create usage reporter instance
            usage_reporter = UsageReporter()

            async with self._session_factory() as session:
                # Process hourly usage reporting
                results = await usage_reporter.process_hourly_usage_reporting(session)

                logger.info(
                    "Usage reporting completed: "
                    f"{results['records_reported']} reported, "
                    f"{results['records_failed']} failed"
                )

                # Record metric
                await SystemMetricOperations.record_metric(
                    db=session,
                    metric_name="stripe_usage_reporting",
                    metric_type="gauge",
                    metric_value={
                        "success": results["success"],
                        "records_processed": results.get("records_processed", 0),
                        "records_reported": results.get("records_reported", 0),
                        "records_failed": results.get("records_failed", 0),
                    },
                )
                await session.commit()

        except Exception as e:
            logger.error(f"Error in usage reporting task: {e}", exc_info=True)
            if self._session_factory:
                try:
                    async with self._session_factory() as session:
                        await SystemMetricOperations.record_metric(
                            db=session,
                            metric_name="stripe_usage_reporting_error",
                            metric_type="counter",
                            metric_value={"error": str(e)},
                        )
                        await session.commit()
                except Exception as e:
                    logger.warning(
                        f"Failed to record stripe usage reporting error metric: {e}"
                    )

    # Manual task execution methods

    async def run_task_manually(self, task_name: str) -> Dict[str, Any]:
        """
        Run a specific task manually.

        Args:
            task_name: Name of the task to run

        Returns:
            Task execution result
        """
        task = self.tasks.get(task_name)
        if not task:
            raise ValueError(f"Task not found: {task_name}")

        logger.info(f"Manually executing task: {task_name}")
        await self._execute_task(task)

        return {
            "task_name": task_name,
            "last_run": task.last_run.isoformat() if task.last_run else None,
            "next_run": task.next_run.isoformat() if task.next_run else None,
            "run_count": task.run_count,
            "error_count": task.error_count,
        }

    def get_task_status(self) -> List[Dict[str, Any]]:
        """Get status of all scheduled tasks."""
        return [
            {
                "name": task.name,
                "enabled": task.enabled,
                "interval_seconds": task.interval_seconds,
                "last_run": task.last_run.isoformat() if task.last_run else None,
                "next_run": task.next_run.isoformat() if task.next_run else None,
                "run_count": task.run_count,
                "error_count": task.error_count,
                "last_error": task.last_error,
            }
            for task in self.tasks.values()
        ]


# Global scheduler instance
scheduler_service = SchedulerService()


async def get_scheduler_service() -> SchedulerService:
    """Dependency to get scheduler service."""
    return scheduler_service
