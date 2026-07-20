"""
Tests for budget monitoring endpoints.

Tests the budget status and spending API endpoints.
"""

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from tests.conftest import create_test_app


class TestBudgetEndpoints:
    """Test cases for budget monitoring endpoints."""

    @pytest.fixture
    def app(self):
        """Create test FastAPI application."""
        return create_test_app()

    @pytest.fixture
    async def client(self, app):
        """Create async test client with mocked dependencies."""
        from github_analyzer.api.auth.dependencies import require_api_access
        from github_analyzer.api.services.budget_dependencies import get_budget_monitor

        # Mock authentication
        app.dependency_overrides[require_api_access] = lambda: "test_user_123"

        # Mock budget monitor
        mock_budget_monitor = AsyncMock()
        app.dependency_overrides[get_budget_monitor] = lambda: mock_budget_monitor

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            client.mock_budget_monitor = mock_budget_monitor
            yield client

    @pytest.mark.asyncio
    async def test_get_budget_status_ok(self, client):
        """Test budget status endpoint with no warnings."""
        # Mock budget status response
        client.mock_budget_monitor.check_budget_status.return_value = {
            "daily_spent": 0.10,
            "monthly_spent": 5.00,
            "daily_budget_estimate": 0.50,
            "monthly_budget_estimate": 15.00,
            "warnings": [],
        }
        client.mock_budget_monitor.get_user_daily_spending.return_value = 0.05

        response = await client.get("/api/v1/budget/status")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ok"
        assert data["budget"]["daily_spent"] == 0.10
        assert data["budget"]["monthly_spent"] == 5.00
        assert data["budget"]["user_daily_spending"] == 0.05
        assert len(data["budget"]["warnings"]) == 0
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_get_budget_status_with_warnings(self, client):
        """Test budget status endpoint with warnings."""
        # Mock budget status response with warnings
        client.mock_budget_monitor.check_budget_status.return_value = {
            "daily_spent": 0.45,
            "monthly_spent": 13.50,
            "daily_budget_estimate": 0.50,
            "monthly_budget_estimate": 15.00,
            "warnings": [
                {
                    "level": "critical",
                    "message": "Monthly spending at 90% of initial budget",
                }
            ],
        }
        client.mock_budget_monitor.get_user_daily_spending.return_value = 0.20

        response = await client.get("/api/v1/budget/status")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "warning"
        assert len(data["budget"]["warnings"]) == 1
        assert data["budget"]["warnings"][0]["level"] == "critical"

    @pytest.mark.asyncio
    async def test_get_budget_status_error(self, client):
        """Test budget status endpoint with error."""
        # Mock exception
        client.mock_budget_monitor.check_budget_status.side_effect = Exception(
            "Redis error"
        )

        response = await client.get("/api/v1/budget/status")

        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["error"] == "Failed to retrieve budget status"
        assert "Redis error" in data["detail"]["message"]

    @pytest.mark.asyncio
    async def test_get_spending_summary(self, client):
        """Test spending summary endpoint."""
        # Mock spending data
        client.mock_budget_monitor.get_daily_spending.return_value = 0.20
        client.mock_budget_monitor.get_monthly_spending.return_value = 8.00
        client.mock_budget_monitor.get_user_daily_spending.return_value = 0.10

        response = await client.get("/api/v1/budget/spending")

        assert response.status_code == 200
        data = response.json()

        assert data["spending"]["daily"]["total"] == 0.20
        assert data["spending"]["daily"]["user"] == 0.10
        assert data["spending"]["monthly"]["total"] == 8.00

        # Check estimates
        assert data["estimates"]["analyses_today"] == 100  # 0.20 / 0.002
        assert data["estimates"]["analyses_this_month"] == 4000  # 8.00 / 0.002
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_get_spending_summary_no_spending(self, client):
        """Test spending summary with no spending."""
        # Mock zero spending
        client.mock_budget_monitor.get_daily_spending.return_value = 0.0
        client.mock_budget_monitor.get_monthly_spending.return_value = 0.0
        client.mock_budget_monitor.get_user_daily_spending.return_value = 0.0

        response = await client.get("/api/v1/budget/spending")

        assert response.status_code == 200
        data = response.json()

        assert data["spending"]["daily"]["total"] == 0.0
        assert data["spending"]["daily"]["user"] == 0.0
        assert data["spending"]["monthly"]["total"] == 0.0
        assert data["estimates"]["analyses_today"] == 0
        assert data["estimates"]["analyses_this_month"] == 0

    @pytest.mark.asyncio
    async def test_get_spending_summary_error(self, client):
        """Test spending summary endpoint with error."""
        # Mock exception
        client.mock_budget_monitor.get_daily_spending.side_effect = Exception(
            "Database error"
        )

        response = await client.get("/api/v1/budget/spending")

        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["error"] == "Failed to retrieve spending summary"
        assert "Database error" in data["detail"]["message"]

    @pytest.mark.asyncio
    async def test_budget_endpoints_unauthorized(self, app):
        """Test budget endpoints require authentication."""
        # Remove auth override to test unauthorized access
        app.dependency_overrides.clear()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Test status endpoint
            response = await client.get("/api/v1/budget/status")
            assert response.status_code in [401, 403]  # Unauthorized or Forbidden

            # Test spending endpoint
            response = await client.get("/api/v1/budget/spending")
            assert response.status_code in [401, 403]  # Unauthorized or Forbidden
