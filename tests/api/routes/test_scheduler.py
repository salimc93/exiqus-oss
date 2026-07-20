"""
Tests for scheduler management API endpoints.

Tests admin scheduler management and task execution capabilities.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession

from github_analyzer.api.services.scheduler_service import (
    ScheduledTask,
    SchedulerService,
)
from github_analyzer.database.models import User, UserRole


@pytest.fixture(scope="module", autouse=True)
def mock_scheduler_service(module_mocker: MockerFixture) -> MagicMock:
    """
    Fixture to mock the scheduler service for all tests in this module.

    This uses pytest-mock's module_mocker to patch the global scheduler_service
    instance before any tests run, preventing real database access.
    """
    mock_scheduler = module_mocker.patch(
        "github_analyzer.api.services.scheduler_service.scheduler_service",
        spec=SchedulerService,
    )
    mock_scheduler.tasks = {}
    mock_scheduler.running = True
    mock_scheduler.get_task_status = MagicMock(return_value=[])
    mock_scheduler.run_task_manually = AsyncMock()
    mock_scheduler.start = AsyncMock()
    mock_scheduler.stop = AsyncMock()
    return mock_scheduler


@pytest.fixture
def mock_scheduler(mock_scheduler_service: MagicMock) -> MagicMock:
    """
    Fixture to provide the module-level mock scheduler to individual tests.

    This allows tests to configure the mock's behavior (e.g., set return values)
    and assert calls against it.
    """
    # Reset mock before each test to ensure isolation
    mock_scheduler_service.reset_mock()
    # Restore default behaviors that might be cleared by reset_mock
    mock_scheduler_service.get_task_status.return_value = []
    mock_scheduler_service.run_task_manually.return_value = None
    mock_scheduler_service.run_task_manually.side_effect = None
    return mock_scheduler_service


@pytest.fixture
async def test_user(test_db: AsyncSession) -> User:
    """Fixture to create a standard user for testing."""
    async with test_db() as session:
        user = User(
            user_id="test-user-123",
            email="test@example.com",
            full_name="Test User",
            password_hash="hashed_password",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture
def user_auth_headers(test_user: User) -> dict:
    """Fixture to create auth headers for a standard user."""
    from github_analyzer.api.auth.jwt import create_access_token

    token = create_access_token(data={"sub": test_user.user_id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def admin_user(test_db: AsyncSession) -> User:
    """Fixture to create an admin user for testing."""
    async with test_db() as session:
        user = User(
            user_id="admin-user-456",
            email="admin@example.com",
            full_name="Admin User",
            password_hash="hashed_password",
            user_role=UserRole.ADMIN,
            is_admin=True,
            is_active=True,
            is_verified=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        # Ensure the user was saved correctly
        saved_user = await session.get(User, user.user_id)
        assert saved_user is not None
        assert saved_user.is_admin is True
        return saved_user


@pytest.fixture
def admin_auth_headers(admin_user: User) -> dict:
    """Fixture to create auth headers for an admin user."""
    from github_analyzer.api.auth.jwt import create_access_token

    token = create_access_token(data={"sub": admin_user.user_id})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
class TestSchedulerEndpoints:
    """Test suite for scheduler management endpoints."""

    async def test_get_scheduled_tasks_success(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict,
        mock_scheduler: MagicMock,
    ):
        """Test admin retrieval of scheduled tasks."""
        # Setup mock return value for get_task_status
        mock_scheduler.get_task_status.return_value = [
            {
                "name": "monthly_quota_reset",
                "enabled": True,
                "interval_seconds": 86400,
                "last_run": datetime.now(timezone.utc).isoformat(),
                "next_run": datetime.now(timezone.utc).isoformat(),
                "run_count": 5,
                "error_count": 0,
                "last_error": None,
            },
            {
                "name": "cleanup_old_metrics",
                "enabled": True,
                "interval_seconds": 604800,
                "last_run": None,
                "next_run": None,
                "run_count": 0,
                "error_count": 0,
                "last_error": None,
            },
        ]

        response = await async_client.get(
            "/api/v1/scheduler/tasks", headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        # Check that we get some scheduled tasks
        assert len(data) >= 1
        # Verify task structure
        if len(data) > 0:
            task = data[0]
            assert "name" in task
            assert "enabled" in task
            assert "interval_seconds" in task
            assert "run_count" in task
            assert "error_count" in task

    async def test_get_scheduled_tasks_non_admin(
        self,
        async_client: AsyncClient,
        user_auth_headers: dict,
        mock_scheduler: MagicMock,
    ):
        """Test non-admin cannot access scheduled tasks."""
        response = await async_client.get(
            "/api/v1/scheduler/tasks", headers=user_auth_headers
        )
        assert response.status_code == 403

    async def test_run_task_manually_success(
        self,
        mock_scheduler: MagicMock,
        async_client: AsyncClient,
        admin_auth_headers: dict,
    ):
        """Test manual task execution."""
        # Setup the mock return value
        task_result = {
            "task_name": "monthly_quota_reset",
            "last_run": datetime.now(timezone.utc).isoformat(),
            "next_run": datetime.now(timezone.utc).isoformat(),
            "run_count": 6,
            "error_count": 0,
        }
        mock_scheduler.run_task_manually.return_value = task_result

        response = await async_client.post(
            "/api/v1/scheduler/tasks/monthly_quota_reset/run",
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["task_name"] == "monthly_quota_reset"
        assert data["run_count"] == 6

    async def test_run_task_manually_not_found(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict,
        mock_scheduler: MagicMock,
    ):
        """Test running non-existent task."""
        mock_scheduler.run_task_manually.side_effect = ValueError(
            "Task not found: invalid_task"
        )

        response = await async_client.post(
            "/api/v1/scheduler/tasks/invalid_task/run", headers=admin_auth_headers
        )

        assert response.status_code == 404
        assert "Task not found" in response.json()["detail"]

    async def test_toggle_task_enabled_success(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict,
        mock_scheduler: MagicMock,
    ):
        """Test toggling task enabled state."""
        # Add a test task
        test_task = ScheduledTask(
            name="test_task", func=AsyncMock(), interval_seconds=3600, enabled=True
        )
        mock_scheduler.tasks["test_task"] = test_task

        response = await async_client.put(
            "/api/v1/scheduler/tasks/test_task/toggle", headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["task_name"] == "test_task"
        assert data["status"] == "disabled"
        assert not test_task.enabled

    async def test_trigger_monthly_quota_reset_success(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict,
        mock_scheduler: MagicMock,
    ):
        """Test manual monthly quota reset."""
        task_result = {
            "task_name": "monthly_quota_reset",
            "last_run": datetime.now(timezone.utc).isoformat(),
            "run_count": 1,
            "error_count": 0,
        }
        mock_scheduler.run_task_manually.return_value = task_result

        response = await async_client.post(
            "/api/v1/scheduler/quota/reset-monthly", headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Monthly quota reset completed" in data["message"]

    async def test_get_scheduler_health_success(
        self,
        async_client: AsyncClient,
        user_auth_headers: dict,
        mock_scheduler: MagicMock,
    ):
        """Test scheduler health check."""
        # Add a task with errors
        error_task = ScheduledTask(
            name="task_with_errors",
            func=AsyncMock(),
            interval_seconds=3600,
            enabled=False,
        )
        error_task.error_count = 2
        mock_scheduler.tasks["task_with_errors"] = error_task

        # Mock the get_task_status method
        mock_scheduler.get_task_status.return_value = [
            {
                "name": "monthly_quota_reset",
                "enabled": True,
                "error_count": 0,
            },
            {
                "name": "task_with_errors",
                "enabled": False,
                "error_count": 2,
            },
        ]

        response = await async_client.get(
            "/api/v1/scheduler/health", headers=user_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["running"] is True
        assert data["total_tasks"] == 2
        assert data["enabled_tasks"] == 1
        assert data["tasks_with_errors"] == 1

    async def test_get_scheduler_health_unauthenticated(
        self, async_client: AsyncClient
    ):
        """Test scheduler health requires authentication."""
        response = await async_client.get("/api/v1/scheduler/health")
        assert response.status_code == 401
