"""
Comprehensive tests for analysis cancellation API endpoints.
Tests real backend cancellation with smart timing constraints.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.github_analyzer.database.models import SubscriptionPlan, User
from src.github_analyzer.services.cancellation_service import (
    RunningTask,
    TaskStatus,
    TaskType,
)


class TestAnalysisCancellationComprehensive:
    """Comprehensive tests for analysis cancellation endpoints."""

    @pytest.fixture
    def mock_user(self):
        """Create mock user for authentication."""
        user = MagicMock(spec=User)
        user.user_id = "test_user_123"
        user.email = "test@example.com"
        user.subscription_plan = SubscriptionPlan.PROFESSIONAL
        return user

    @pytest.fixture
    def mock_cancellation_service(self):
        """Create mock cancellation service."""
        from unittest.mock import AsyncMock

        service = MagicMock()
        # Make cancel_task async
        service.cancel_task = AsyncMock()
        return service

    @pytest.fixture
    def client_with_mocks(self, mock_user, mock_cancellation_service):
        """Create test client with mocked dependencies and authentication."""
        from src.github_analyzer.api.auth.dependencies import get_current_active_user
        from src.github_analyzer.api.main import app

        # Override dependency to return mock user
        app.dependency_overrides[get_current_active_user] = lambda: mock_user

        with patch(
            "src.github_analyzer.api.routes.analysis.get_cancellation_service",
            return_value=mock_cancellation_service,
        ):
            client = TestClient(app)
            yield client, mock_cancellation_service

        # Clean up
        app.dependency_overrides.clear()

    def test_cancel_analysis_success(self, client_with_mocks):
        """Test successful single analysis cancellation."""
        client, mock_service = client_with_mocks
        task_id = "single_test_123"

        # Mock successful cancellation
        mock_service.cancel_task.return_value = (True, "Task cancelled successfully")

        response = client.post(f"/api/v1/cancel/{task_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id
        assert data["status"] == "cancelled"
        assert "cancelled successfully" in data["message"].lower()
        assert "timestamp" in data

        # Verify service was called correctly
        mock_service.cancel_task.assert_called_once_with(task_id, "test_user_123")

    def test_cancel_analysis_task_not_found(self, client_with_mocks):
        """Test cancellation of non-existent task."""
        client, mock_service = client_with_mocks
        task_id = "nonexistent_task"

        # Mock task not found
        mock_service.cancel_task.return_value = (False, "Task not found")

        response = client.post(f"/api/v1/cancel/{task_id}")

        assert response.status_code == 404
        assert "Task not found" in response.json()["detail"]

    def test_cancel_analysis_permission_denied(self, client_with_mocks):
        """Test cancellation with permission denied."""
        client, mock_service = client_with_mocks
        task_id = "other_user_task"

        # Mock permission denied
        mock_service.cancel_task.return_value = (
            False,
            "Permission denied: task belongs to different user",
        )

        response = client.post(f"/api/v1/cancel/{task_id}")

        assert response.status_code == 403
        assert "Permission denied" in response.json()["detail"]

    def test_cancel_analysis_window_expired(self, client_with_mocks):
        """Test cancellation after window expires."""
        client, mock_service = client_with_mocks
        task_id = "expired_task"

        # Mock expired window
        deadline = datetime.now(timezone.utc) - timedelta(seconds=5)
        mock_service.cancel_task.return_value = (
            False,
            f"Cancellation window expired (deadline was {deadline.isoformat()})",
        )

        response = client.post(f"/api/v1/cancel/{task_id}")

        assert response.status_code == 400
        assert "expired" in response.json()["detail"].lower()

    def test_cancel_analysis_internal_error(self, client_with_mocks):
        """Test cancellation with internal service error."""
        client, mock_service = client_with_mocks
        task_id = "error_task"

        # Mock service error
        mock_service.cancel_task.side_effect = Exception("Internal service error")

        response = client.post(f"/api/v1/cancel/{task_id}")

        assert response.status_code == 500
        assert "Failed to cancel analysis" in response.json()["detail"]

    def test_cancel_batch_analysis_success(self, client_with_mocks):
        """Test successful batch analysis cancellation."""
        client, mock_service = client_with_mocks
        batch_id = "batch_test_456"

        # Mock successful cancellation
        mock_service.cancel_task.return_value = (True, "Task cancelled successfully")

        response = client.post(f"/api/v1/batch/cancel/{batch_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["batch_id"] == batch_id
        assert data["status"] == "cancelled"
        assert "cancelled successfully" in data["message"].lower()

        # Verify service was called correctly
        mock_service.cancel_task.assert_called_once_with(batch_id, "test_user_123")

    def test_cancel_batch_analysis_not_found(self, client_with_mocks):
        """Test cancellation of non-existent batch."""
        client, mock_service = client_with_mocks
        batch_id = "nonexistent_batch"

        # Mock batch not found
        mock_service.cancel_task.return_value = (False, "Task not found")

        response = client.post(f"/api/v1/batch/cancel/{batch_id}")

        assert response.status_code == 404

    def test_cancel_batch_analysis_permission_denied(self, client_with_mocks):
        """Test batch cancellation with permission denied."""
        client, mock_service = client_with_mocks
        batch_id = "other_user_batch"

        # Mock permission denied
        mock_service.cancel_task.return_value = (
            False,
            "Permission denied: task belongs to different user",
        )

        response = client.post(f"/api/v1/batch/cancel/{batch_id}")

        assert response.status_code == 403

    def test_cancel_batch_analysis_window_expired(self, client_with_mocks):
        """Test batch cancellation after 30s window expires."""
        client, mock_service = client_with_mocks
        batch_id = "expired_batch"

        # Mock expired window
        deadline = datetime.now(timezone.utc) - timedelta(seconds=10)
        mock_service.cancel_task.return_value = (
            False,
            f"Cancellation window expired (deadline was {deadline.isoformat()})",
        )

        response = client.post(f"/api/v1/batch/cancel/{batch_id}")

        assert response.status_code == 400
        assert "expired" in response.json()["detail"].lower()

    def test_get_task_status_success(self, client_with_mocks):
        """Test getting task status successfully."""
        client, mock_service = client_with_mocks
        task_id = "status_test_789"

        # Create mock task
        now = datetime.now(timezone.utc)
        deadline = now + timedelta(seconds=8)

        mock_task = RunningTask(
            task_id=task_id,
            task_type=TaskType.SINGLE_ANALYSIS,
            user_id="test_user_123",
            started_at=now,
            cancel_deadline=deadline,
            status=TaskStatus.RUNNING,
        )

        mock_service.get_task_info.return_value = mock_task
        mock_service.can_cancel_task.return_value = (True, "Task can be cancelled")

        response = client.get(f"/api/v1/tasks/{task_id}/status")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id
        assert data["task_type"] == "single_analysis"
        assert data["status"] == "running"
        assert data["can_cancel"] is True
        assert "can be cancelled" in data["cancel_reason"]
        assert data["time_remaining_seconds"] > 0

    def test_get_task_status_not_found(self, client_with_mocks):
        """Test getting status for non-existent task."""
        client, mock_service = client_with_mocks
        task_id = "nonexistent_status"

        mock_service.get_task_info.return_value = None

        response = client.get(f"/api/v1/tasks/{task_id}/status")

        assert response.status_code == 404
        assert "Task not found" in response.json()["detail"]

    def test_get_task_status_permission_denied(self, client_with_mocks):
        """Test getting status for task owned by different user."""
        client, mock_service = client_with_mocks
        task_id = "other_user_status"

        # Create mock task for different user
        now = datetime.now(timezone.utc)
        deadline = now + timedelta(seconds=5)

        mock_task = RunningTask(
            task_id=task_id,
            task_type=TaskType.BATCH_ANALYSIS,
            user_id="other_user_456",  # Different user
            started_at=now,
            cancel_deadline=deadline,
            status=TaskStatus.RUNNING,
        )

        mock_service.get_task_info.return_value = mock_task

        response = client.get(f"/api/v1/tasks/{task_id}/status")

        assert response.status_code == 403
        assert "Permission denied" in response.json()["detail"]

    def test_get_task_status_expired_window(self, client_with_mocks):
        """Test getting status for task with expired cancellation window."""
        client, mock_service = client_with_mocks
        task_id = "expired_status"

        # Create mock task with expired deadline
        now = datetime.now(timezone.utc)
        past_deadline = now - timedelta(seconds=5)

        mock_task = RunningTask(
            task_id=task_id,
            task_type=TaskType.SINGLE_ANALYSIS,
            user_id="test_user_123",
            started_at=now - timedelta(seconds=15),
            cancel_deadline=past_deadline,
            status=TaskStatus.RUNNING,
        )

        mock_service.get_task_info.return_value = mock_task
        mock_service.can_cancel_task.return_value = (
            False,
            "Cancellation window expired",
        )

        response = client.get(f"/api/v1/tasks/{task_id}/status")

        assert response.status_code == 200
        data = response.json()
        assert data["can_cancel"] is False
        assert "expired" in data["cancel_reason"].lower()
        assert data["time_remaining_seconds"] == 0

    def test_get_task_status_internal_error(self, client_with_mocks):
        """Test getting task status with internal error."""
        client, mock_service = client_with_mocks
        task_id = "error_status"

        mock_service.get_task_info.side_effect = Exception("Internal service error")

        response = client.get(f"/api/v1/tasks/{task_id}/status")

        assert response.status_code == 500
        assert "Failed to get task status" in response.json()["detail"]

    def test_cancellation_timing_windows(self, client_with_mocks):
        """Test that different task types return appropriate timing information."""
        client, mock_service = client_with_mocks

        # Test single analysis (10s window)
        now = datetime.now(timezone.utc)
        single_deadline = now + timedelta(seconds=7)  # 7s remaining

        single_task = RunningTask(
            task_id="single_timing",
            task_type=TaskType.SINGLE_ANALYSIS,
            user_id="test_user_123",
            started_at=now - timedelta(seconds=3),
            cancel_deadline=single_deadline,
            status=TaskStatus.RUNNING,
        )

        mock_service.get_task_info.return_value = single_task
        mock_service.can_cancel_task.return_value = (True, "Task can be cancelled")

        response = client.get("/api/v1/tasks/single_timing/status")
        assert response.status_code == 200
        data = response.json()
        assert data["task_type"] == "single_analysis"
        assert 5 <= data["time_remaining_seconds"] <= 8  # Allow some tolerance

        # Test batch analysis (30s window)
        batch_deadline = now + timedelta(seconds=25)  # 25s remaining

        batch_task = RunningTask(
            task_id="batch_timing",
            task_type=TaskType.BATCH_ANALYSIS,
            user_id="test_user_123",
            started_at=now - timedelta(seconds=5),
            cancel_deadline=batch_deadline,
            status=TaskStatus.RUNNING,
        )

        mock_service.get_task_info.return_value = batch_task
        mock_service.can_cancel_task.return_value = (True, "Task can be cancelled")

        response = client.get("/api/v1/tasks/batch_timing/status")
        assert response.status_code == 200
        data = response.json()
        assert data["task_type"] == "batch_analysis"
        assert 23 <= data["time_remaining_seconds"] <= 27  # Allow some tolerance

    def test_cancellation_response_format(self, client_with_mocks):
        """Test that cancellation responses have correct format."""
        client, mock_service = client_with_mocks
        task_id = "format_test"

        # Mock successful cancellation
        mock_service.cancel_task.return_value = (True, "Task cancelled successfully")

        response = client.post(f"/api/v1/cancel/{task_id}")

        assert response.status_code == 200
        data = response.json()

        # Check required fields
        required_fields = ["task_id", "status", "message", "timestamp"]
        for field in required_fields:
            assert field in data

        assert data["task_id"] == task_id
        assert data["status"] == "cancelled"
        assert isinstance(data["message"], str)

        # Validate timestamp format
        timestamp = data["timestamp"]
        assert isinstance(timestamp, str)
        # Should be valid ISO format
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    def test_batch_cancellation_response_format(self, client_with_mocks):
        """Test that batch cancellation responses have correct format."""
        client, mock_service = client_with_mocks
        batch_id = "batch_format_test"

        # Mock successful cancellation
        mock_service.cancel_task.return_value = (True, "Task cancelled successfully")

        response = client.post(f"/api/v1/batch/cancel/{batch_id}")

        assert response.status_code == 200
        data = response.json()

        # Check required fields
        required_fields = ["batch_id", "status", "message", "timestamp"]
        for field in required_fields:
            assert field in data

        assert data["batch_id"] == batch_id
        assert data["status"] == "cancelled"

    def test_task_status_response_format(self, client_with_mocks):
        """Test that task status responses have correct format."""
        client, mock_service = client_with_mocks
        task_id = "status_format_test"

        # Create mock task
        now = datetime.now(timezone.utc)
        deadline = now + timedelta(seconds=8)

        mock_task = RunningTask(
            task_id=task_id,
            task_type=TaskType.SINGLE_ANALYSIS,
            user_id="test_user_123",
            started_at=now,
            cancel_deadline=deadline,
            status=TaskStatus.RUNNING,
        )

        mock_service.get_task_info.return_value = mock_task
        mock_service.can_cancel_task.return_value = (True, "Task can be cancelled")

        response = client.get(f"/api/v1/tasks/{task_id}/status")

        assert response.status_code == 200
        data = response.json()

        # Check required fields
        required_fields = [
            "task_id",
            "task_type",
            "status",
            "started_at",
            "cancel_deadline",
            "can_cancel",
            "cancel_reason",
            "time_remaining_seconds",
        ]
        for field in required_fields:
            assert field in data

        assert data["task_id"] == task_id
        assert data["task_type"] in ["single_analysis", "batch_analysis"]
        assert data["status"] in ["running", "cancelled", "completed", "failed"]
        assert isinstance(data["can_cancel"], bool)
        assert isinstance(data["time_remaining_seconds"], int)
        assert data["time_remaining_seconds"] >= 0

        # Validate timestamp formats
        for field in ["started_at", "cancel_deadline"]:
            timestamp = data[field]
            assert isinstance(timestamp, str)
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    def test_authentication_required(self):
        """Test that authentication is required for cancellation endpoints."""
        from src.github_analyzer.api.main import app

        client = TestClient(app)

        # Test without authentication
        response = client.post("/api/v1/cancel/test_task")
        assert response.status_code == 401

        response = client.post("/api/v1/batch/cancel/test_batch")
        assert response.status_code == 401

        response = client.get("/api/v1/tasks/test_task/status")
        assert response.status_code == 401

    def test_endpoint_paths_correct(self, client_with_mocks):
        """Test that all cancellation endpoints have correct paths."""
        client, mock_service = client_with_mocks

        # Mock successful responses
        mock_service.cancel_task.return_value = (True, "Success")
        mock_service.get_task_info.return_value = RunningTask(
            task_id="test",
            task_type=TaskType.SINGLE_ANALYSIS,
            user_id="test_user_123",
            started_at=datetime.now(timezone.utc),
            cancel_deadline=datetime.now(timezone.utc) + timedelta(seconds=10),
        )
        mock_service.can_cancel_task.return_value = (True, "Can cancel")

        # Test single analysis cancellation
        response = client.post("/api/v1/cancel/test_task")
        assert response.status_code == 200

        # Test batch analysis cancellation
        response = client.post("/api/v1/batch/cancel/test_batch")
        assert response.status_code == 200

        # Test task status
        response = client.get("/api/v1/tasks/test_task/status")
        assert response.status_code == 200

    def test_error_status_codes_comprehensive(self, client_with_mocks):
        """Test comprehensive error status code mapping."""
        client, mock_service = client_with_mocks

        test_cases = [
            ("Task not found", 404),
            ("task not found", 404),  # Case insensitive
            ("Permission denied: access denied", 403),
            ("permission denied: wrong user", 403),  # Case insensitive
            ("Cancellation window expired", 400),
            ("window expired", 400),  # Partial match
            ("Some other error", 400),  # Default for other failures
        ]

        for error_message, expected_status in test_cases:
            mock_service.cancel_task.return_value = (False, error_message)

            response = client.post("/api/v1/cancel/test_task")
            assert response.status_code == expected_status, (
                f"Failed for message: {error_message}"
            )
            assert error_message in response.json()["detail"]
