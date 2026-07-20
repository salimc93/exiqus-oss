"""
Tests for the scheduler service.

Tests automated task scheduling including monthly quota resets.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from freezegun import freeze_time

from github_analyzer.api.services.scheduler_service import (
    ScheduledTask,
    SchedulerService,
    get_scheduler_service,
)
from github_analyzer.database.models import SubscriptionPlan


@pytest.fixture
def mock_session_factory():
    """Create a mock session factory."""
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()

    # Create a proper async context manager
    mock_context = MagicMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)
    mock_context.__aexit__ = AsyncMock(return_value=None)

    # Factory should return the context manager
    mock_factory = MagicMock(return_value=mock_context)

    return mock_factory, mock_session


@pytest.fixture
def scheduler_service(mock_session_factory):
    """Create a test scheduler service."""
    factory, _ = mock_session_factory
    service = SchedulerService(session_factory=factory)
    # Clear default tasks for testing
    service.tasks.clear()
    return service


@pytest.fixture
def mock_task():
    """Create a mock async task."""
    return AsyncMock()


class TestScheduledTask:
    """Test the ScheduledTask class."""

    def test_scheduled_task_creation(self, mock_task):
        """Test creating a scheduled task."""
        task = ScheduledTask(
            name="test_task",
            func=mock_task,
            interval_seconds=3600,
            enabled=True,
            run_on_startup=False,
        )

        assert task.name == "test_task"
        assert task.func == mock_task
        assert task.interval_seconds == 3600
        assert task.enabled is True
        assert task.run_on_startup is False
        assert task.last_run is None
        assert task.next_run is None
        assert task.run_count == 0
        assert task.error_count == 0

    def test_should_run_when_never_run(self, mock_task):
        """Test should_run returns True when task has never run."""
        task = ScheduledTask("test", mock_task, 3600)
        assert task.should_run(datetime.now(timezone.utc)) is True

    def test_should_run_when_disabled(self, mock_task):
        """Test should_run returns False when task is disabled."""
        task = ScheduledTask("test", mock_task, 3600, enabled=False)
        assert task.should_run(datetime.now(timezone.utc)) is False

    def test_should_run_based_on_schedule(self, mock_task):
        """Test should_run based on next_run time."""
        task = ScheduledTask("test", mock_task, 3600)
        now = datetime.now(timezone.utc)

        # Set next run to future
        task.next_run = now + timedelta(hours=1)
        assert task.should_run(now) is False

        # Set next run to past
        task.next_run = now - timedelta(hours=1)
        assert task.should_run(now) is True

    def test_update_next_run(self, mock_task):
        """Test updating next run time."""
        task = ScheduledTask("test", mock_task, 3600)
        base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        task.update_next_run(base_time)
        expected = base_time + timedelta(seconds=3600)
        assert task.next_run == expected


class TestSchedulerService:
    """Test the SchedulerService class."""

    def test_initialization(self, mock_session_factory):
        """Test scheduler service initialization with default tasks."""
        factory, _ = mock_session_factory
        service = SchedulerService(session_factory=factory)

        # Should have default tasks registered
        assert "monthly_quota_reset" in service.tasks
        assert "cleanup_old_metrics" in service.tasks
        assert "generate_usage_reports" in service.tasks

        # Check monthly quota reset task
        quota_task = service.tasks["monthly_quota_reset"]
        assert quota_task.interval_seconds == 3600 * 24  # Daily
        assert quota_task.run_on_startup is True

    def test_register_task(self, scheduler_service, mock_task):
        """Test registering a new task."""
        scheduler_service.register_task(
            name="custom_task",
            func=mock_task,
            interval_seconds=300,
            enabled=True,
            run_on_startup=True,
        )

        assert "custom_task" in scheduler_service.tasks
        task = scheduler_service.tasks["custom_task"]
        assert task.name == "custom_task"
        assert task.interval_seconds == 300
        assert task.run_on_startup is True

    @pytest.mark.asyncio
    async def test_start_stop(self, scheduler_service):
        """Test starting and stopping the scheduler."""
        assert scheduler_service.running is False
        assert scheduler_service.task_loop is None

        # Start scheduler
        await scheduler_service.start()
        assert scheduler_service.running is True
        assert scheduler_service.task_loop is not None

        # Stop scheduler
        await scheduler_service.stop()
        assert scheduler_service.running is False

    @pytest.mark.asyncio
    async def test_run_startup_tasks(self, scheduler_service, mock_task):
        """Test running startup tasks."""
        # Register startup task
        scheduler_service.register_task(
            name="startup_task",
            func=mock_task,
            interval_seconds=3600,
            run_on_startup=True,
        )

        # Register non-startup task
        non_startup_task = AsyncMock()
        scheduler_service.register_task(
            name="regular_task",
            func=non_startup_task,
            interval_seconds=3600,
            run_on_startup=False,
        )

        with patch(
            "github_analyzer.api.services.scheduler_service.SystemMetricOperations.record_metric",
            new_callable=AsyncMock,
        ):
            await scheduler_service._run_startup_tasks()

        # Only startup task should be called
        mock_task.assert_called_once()
        non_startup_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_task_success(self, scheduler_service, mock_task):
        """Test successful task execution."""
        task = ScheduledTask("test", mock_task, 3600)
        scheduler_service.tasks["test"] = task

        with patch(
            "github_analyzer.api.services.scheduler_service.SystemMetricOperations.record_metric",
            new_callable=AsyncMock,
        ):
            await scheduler_service._execute_task(task)

        mock_task.assert_called_once()
        assert task.run_count == 1
        assert task.last_run is not None
        assert task.next_run is not None
        assert task.error_count == 0

    @pytest.mark.asyncio
    async def test_execute_task_error(self, scheduler_service):
        """Test task execution with error."""
        error_task = AsyncMock(side_effect=Exception("Task failed"))
        task = ScheduledTask("error_task", error_task, 3600)
        scheduler_service.tasks["error_task"] = task

        with patch(
            "github_analyzer.api.services.scheduler_service.SystemMetricOperations.record_metric",
            new_callable=AsyncMock,
        ):
            await scheduler_service._execute_task(task)

        assert task.run_count == 0
        assert task.error_count == 1
        assert task.last_error == "Task failed"
        assert task.next_run is not None

    @pytest.mark.asyncio
    async def test_run_task_manually(self, scheduler_service, mock_task):
        """Test manually running a task."""
        scheduler_service.register_task("manual_task", mock_task, 3600)

        with patch(
            "github_analyzer.api.services.scheduler_service.SystemMetricOperations.record_metric",
            new_callable=AsyncMock,
        ):
            result = await scheduler_service.run_task_manually("manual_task")

        mock_task.assert_called_once()
        assert result["task_name"] == "manual_task"
        assert result["run_count"] == 1
        assert result["error_count"] == 0

    @pytest.mark.asyncio
    async def test_run_task_manually_not_found(self, scheduler_service):
        """Test manually running a non-existent task."""
        with pytest.raises(ValueError, match="Task not found"):
            await scheduler_service.run_task_manually("nonexistent")

    def test_get_task_status(self, scheduler_service, mock_task):
        """Test getting task status."""
        scheduler_service.register_task("status_task", mock_task, 3600)
        task = scheduler_service.tasks["status_task"]
        task.run_count = 5
        task.error_count = 1

        status = scheduler_service.get_task_status()

        assert len(status) == 1
        assert status[0]["name"] == "status_task"
        assert status[0]["enabled"] is True
        assert status[0]["run_count"] == 5
        assert status[0]["error_count"] == 1


class TestMonthlyQuotaReset:
    """Test the monthly quota reset functionality."""

    @pytest.mark.asyncio
    @freeze_time("2024-01-15")
    async def test_reset_monthly_quotas_on_billing_day(
        self, scheduler_service, mock_session_factory
    ):
        """Test resetting quotas for users on their billing day."""
        factory, mock_session = mock_session_factory

        # Create mock users with different billing days
        users = [
            # User with billing on the 15th (today)
            MagicMock(
                user_id="user1",
                subscription_start_date=datetime(2023, 12, 15, tzinfo=timezone.utc),
                created_at=None,
                subscription_plan=SubscriptionPlan.PROFESSIONAL,
                usage_count=100,
            ),
            # User with billing on the 1st (not today)
            MagicMock(
                user_id="user2",
                subscription_start_date=datetime(2023, 12, 1, tzinfo=timezone.utc),
                created_at=None,
                subscription_plan=SubscriptionPlan.BASIC,
                usage_count=50,
            ),
            # User with no subscription date, uses created_at on 15th
            MagicMock(
                user_id="user3",
                subscription_start_date=None,
                created_at=datetime(2023, 11, 15, tzinfo=timezone.utc),
                subscription_plan=SubscriptionPlan.ENTERPRISE,
                usage_count=200,
            ),
        ]

        # Mock get_all_users to return users on first call, empty list on second
        mock_get_users_calls = [users, []]

        with (
            patch(
                "github_analyzer.api.services.scheduler_service.UserOperations.get_all_users",
                side_effect=mock_get_users_calls,
            ) as mock_get_users,
            patch(
                "github_analyzer.api.services.scheduler_service.UserOperations.update_usage_count",
                return_value=True,
            ) as mock_update_usage,
            patch(
                "github_analyzer.api.services.scheduler_service.SystemMetricOperations.record_metric"
            ),
            patch(
                "github_analyzer.api.services.scheduler_service.datetime"
            ) as mock_datetime,
        ):
            # Configure the datetime mock to return the frozen time
            frozen_time = datetime(2024, 1, 15, tzinfo=timezone.utc)
            mock_datetime.now.return_value = frozen_time
            # Allow normal datetime constructor calls
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )
            # But override the .now() method specifically
            mock_datetime.now.return_value = frozen_time

            await scheduler_service._reset_monthly_quotas()

        # Should get all active users with pagination
        assert (
            mock_get_users.call_count == 2
        )  # First call returns users, second returns empty
        mock_get_users.assert_any_call(
            mock_session, offset=0, limit=100, active_only=True
        )

        # Should reset only users with billing on the 15th (user1 and user3)
        print(f"mock_update_usage.call_count: {mock_update_usage.call_count}")
        print(f"mock_update_usage.call_args_list: {mock_update_usage.call_args_list}")
        assert mock_update_usage.call_count == 2
        mock_update_usage.assert_any_call(mock_session, "user1", 0)
        mock_update_usage.assert_any_call(mock_session, "user3", 0)

    @pytest.mark.asyncio
    async def test_reset_monthly_quotas_error_handling(
        self, scheduler_service, mock_session_factory
    ):
        """Test error handling in quota reset."""
        factory, mock_session = mock_session_factory

        users = [
            MagicMock(
                user_id="user1",
                subscription_start_date=datetime(2023, 12, 15, tzinfo=timezone.utc),
                created_at=None,
                subscription_plan=SubscriptionPlan.PROFESSIONAL,
            ),
        ]

        # Mock get_all_users to return users on first call, empty list on second
        mock_get_users_calls = [users, []]

        with (
            freeze_time("2024-01-15"),
            patch(
                "github_analyzer.api.services.scheduler_service.UserOperations.get_all_users",
                side_effect=mock_get_users_calls,
            ),
            patch(
                "github_analyzer.api.services.scheduler_service.UserOperations.update_usage_count",
                side_effect=Exception("Database error"),
            ),
            patch(
                "github_analyzer.api.services.scheduler_service.SystemMetricOperations.record_metric"
            ) as mock_metric,
            patch(
                "github_analyzer.api.services.scheduler_service.datetime"
            ) as mock_datetime,
        ):
            # Configure the datetime mock to return the frozen time
            frozen_time = datetime(2024, 1, 15, tzinfo=timezone.utc)
            mock_datetime.now.return_value = frozen_time
            # Allow normal datetime constructor calls
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )
            # But override the .now() method specifically
            mock_datetime.now.return_value = frozen_time

            await scheduler_service._reset_monthly_quotas()

        # Should record error in metrics
        mock_metric.assert_called()
        call_args = mock_metric.call_args[1]
        assert call_args["metric_value"]["errors"] == 1


class TestUsageReports:
    """Test usage report generation."""

    @pytest.mark.asyncio
    async def test_generate_usage_reports(
        self, scheduler_service, mock_session_factory
    ):
        """Test generating daily usage reports."""
        factory, mock_session = mock_session_factory

        # Mock users by plan
        basic_users = [
            MagicMock(usage_count=10),
            MagicMock(usage_count=20),
            MagicMock(usage_count=0),
        ]
        pro_users = [
            MagicMock(usage_count=100),
            MagicMock(usage_count=150),
        ]

        with (
            patch(
                "github_analyzer.api.services.scheduler_service.UserOperations.get_users_by_subscription_plan",
                side_effect=lambda session, plan, limit: {
                    SubscriptionPlan.BASIC: basic_users,
                    SubscriptionPlan.PROFESSIONAL: pro_users,
                    SubscriptionPlan.ENTERPRISE: [],
                    SubscriptionPlan.FREE: [],
                }.get(plan, []),
            ),
            patch(
                "github_analyzer.api.services.scheduler_service.SystemMetricOperations.record_metric"
            ) as mock_metric,
        ):
            await scheduler_service._generate_usage_reports()

        # Check metric recording
        mock_metric.assert_called_once()
        call_args = mock_metric.call_args[1]
        usage_data = call_args["metric_value"]["usage_by_plan"]

        # Verify basic plan stats
        assert usage_data["BASIC"]["total_users"] == 3
        assert usage_data["BASIC"]["active_users"] == 2
        assert usage_data["BASIC"]["total_usage"] == 30
        assert usage_data["BASIC"]["average_usage"] == 10

        # Verify professional plan stats
        assert usage_data["PROFESSIONAL"]["total_users"] == 2
        assert usage_data["PROFESSIONAL"]["active_users"] == 2
        assert usage_data["PROFESSIONAL"]["total_usage"] == 250
        assert usage_data["PROFESSIONAL"]["average_usage"] == 125


def test_get_scheduler_service():
    """Test getting the global scheduler service."""
    service = asyncio.run(get_scheduler_service())
    assert isinstance(service, SchedulerService)
