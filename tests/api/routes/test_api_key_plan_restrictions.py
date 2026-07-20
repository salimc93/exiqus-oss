"""
Test suite for API key plan restrictions.

This module tests that API key authentication (used for export and budget endpoints)
is only available to Professional and Enterprise plan users.
"""

from unittest.mock import Mock, patch

import pytest
from fastapi import status

from github_analyzer.database.models import SubscriptionPlan
from github_analyzer.database.operations import UserOperations


class TestAPIKeyPlanRestrictions:
    """Test API key access restrictions based on subscription plans."""

    @pytest.fixture
    async def create_user_with_plan(self, test_db):
        """Factory to create users with specific plans."""

        async def _create_user(email: str, plan: SubscriptionPlan):
            async with test_db() as db_session:
                from github_analyzer.api.services.api_key_service import APIKeyService

                user = await UserOperations.create_user(
                    db_session,
                    email=email,
                    password="TestPassword123!",
                    full_name=f"{plan.value.title()} User",
                )
                user.is_verified = True
                user.subscription_plan = plan
                await db_session.commit()

                # Create API key for the user using the service
                api_key_service = APIKeyService(db_session)
                api_key_model, api_key_plain = await api_key_service.create_api_key(
                    user_id=user.user_id,
                    name=f"{plan.value} API Key",
                    permissions=["read"],
                )

                return user, api_key_plain

        return _create_user

    @pytest.mark.asyncio
    async def test_free_user_blocked_export_endpoint(
        self, async_client, create_user_with_plan
    ):
        """Test that FREE plan users cannot access export endpoint via API key."""
        user, api_key = await create_user_with_plan(
            "free@example.com", SubscriptionPlan.FREE
        )

        response = await async_client.get(
            "/api/v1/export/test-analysis-id", headers={"X-API-Key": api_key}
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "API access is not available for your current plan" in data["detail"]

    @pytest.mark.asyncio
    async def test_basic_user_blocked_export_endpoint(
        self, async_client, create_user_with_plan
    ):
        """Test that BASIC plan users cannot access export endpoint via API key."""
        user, api_key = await create_user_with_plan(
            "basic@example.com", SubscriptionPlan.BASIC
        )

        response = await async_client.get(
            "/api/v1/export/test-analysis-id", headers={"X-API-Key": api_key}
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "Please upgrade to Professional or Enterprise" in data["detail"]

    @pytest.mark.asyncio
    async def test_professional_user_allowed_export_endpoint(
        self, async_client, create_user_with_plan
    ):
        """Test that PROFESSIONAL plan users can access export endpoint via API key."""
        user, api_key = await create_user_with_plan(
            "pro@example.com", SubscriptionPlan.PROFESSIONAL
        )

        # The export endpoint currently returns sample data
        response = await async_client.get(
            "/api/v1/export/test-analysis-id?format=json",
            headers={"X-API-Key": api_key},
        )

        # Should get 200 (sample data), NOT 403
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_enterprise_user_allowed_export_endpoint(
        self, async_client, create_user_with_plan
    ):
        """Test that ENTERPRISE plan users can access export endpoint via API key."""
        user, api_key = await create_user_with_plan(
            "ent@example.com", SubscriptionPlan.ENTERPRISE
        )

        # The export endpoint currently returns sample data
        response = await async_client.get(
            "/api/v1/export/test-analysis-id?format=json",
            headers={"X-API-Key": api_key},
        )

        # Should get 200 (sample data), NOT 403
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_free_user_blocked_budget_endpoint(
        self, async_client, create_user_with_plan
    ):
        """Test that FREE plan users cannot access budget endpoints via API key."""
        user, api_key = await create_user_with_plan(
            "free2@example.com", SubscriptionPlan.FREE
        )

        response = await async_client.get(
            "/api/v1/budget/status", headers={"X-API-Key": api_key}
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_professional_user_allowed_budget_endpoint(
        self, async_client, create_user_with_plan
    ):
        """Test that PROFESSIONAL plan users can access budget endpoints via API key."""
        user, api_key = await create_user_with_plan(
            "pro2@example.com", SubscriptionPlan.PROFESSIONAL
        )

        # Mock budget monitor
        with patch(
            "github_analyzer.api.routes.budget.get_budget_monitor"
        ) as mock_budget:
            mock_monitor = Mock()
            mock_monitor.get_user_budget_status.return_value = {
                "monthly_limit": 50.0,
                "current_spend": 10.0,
                "remaining": 40.0,
                "reset_date": "2024-02-01",
            }
            mock_budget.return_value = mock_monitor

            response = await async_client.get(
                "/api/v1/budget/status", headers={"X-API-Key": api_key}
            )

            assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_no_api_key_returns_401(self, async_client):
        """Test that requests without API key return 401."""
        response = await async_client.get("/api/v1/export/test-id")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_invalid_api_key_returns_401(self, async_client):
        """Test that requests with invalid API key return 401."""
        response = await async_client.get(
            "/api/v1/export/test-id", headers={"X-API-Key": "invalid-key-12345"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
