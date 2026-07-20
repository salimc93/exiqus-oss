"""Integration tests for consent management API endpoints."""

import json
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi import status

from github_analyzer.api.auth.jwt import create_access_token
from github_analyzer.api.services.consent_service import CURRENT_CONSENT_VERSION
from github_analyzer.database.models import SubscriptionPlan, User, UserRole


class TestConsentIntegration:
    """Test consent management endpoints with proper auth."""

    @pytest.fixture
    def test_token(self):
        """Create a valid test token."""
        return create_access_token(
            {"sub": "test-user-123", "email": "test@example.com"}
        )

    @pytest.fixture
    def test_user(self):
        """Create a test user."""
        user = User(
            user_id="test-user-123",
            email="test@example.com",
            full_name="Test User",
            subscription_plan=SubscriptionPlan.PROFESSIONAL,
            user_role=UserRole.USER,
            is_active=True,
            privacy_preferences=None,
            consent_version_accepted=None,
            consent_notice_dismissed_at=None,
        )
        return user

    @pytest.mark.asyncio
    async def test_get_consent_settings_success_integration(
        self, async_client, test_token, test_user, db_session
    ):
        """Test getting consent settings with proper auth setup."""

        async def mock_get_user_by_id(db, user_id):
            if user_id == "test-user-123":
                return test_user
            return None

        with (
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_id",
                mock_get_user_by_id,
            ),
            patch(
                "github_analyzer.api.auth.jwt.verify_token",
                return_value={"sub": test_user.user_id, "email": test_user.email},
            ),
        ):
            response = await async_client.get(
                "/api/v1/consent/settings",
                headers={"Authorization": f"Bearer {test_token}"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "consent_settings" in data
        assert "tier_defaults" in data
        assert "consent_version" in data
        assert data["consent_version"] == CURRENT_CONSENT_VERSION
        assert data["show_notice"] is True  # New pro user should see notice

        # Check professional tier defaults
        assert data["consent_settings"]["training_usage"] is False
        assert data["consent_settings"]["tier"] == "PROFESSIONAL"

    @pytest.mark.asyncio
    async def test_update_consent_settings_integration(
        self, async_client, test_token, test_user, db_session
    ):
        """Test updating consent settings with proper auth."""

        async def mock_get_user_by_id(db, user_id):
            if user_id == "test-user-123":
                return test_user
            return None

        with (
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_id",
                mock_get_user_by_id,
            ),
            patch(
                "github_analyzer.api.auth.jwt.verify_token",
                return_value={"sub": test_user.user_id, "email": test_user.email},
            ),
        ):
            response = await async_client.put(
                "/api/v1/consent/settings",
                headers={"Authorization": f"Bearer {test_token}"},
                json={
                    "training_usage": True,
                    "anonymized": True,
                    "retention_period": "3_years",
                },
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["success"] is True
        assert "updated_settings" in data
        assert data["updated_settings"]["training_usage"] is True

    @pytest.mark.asyncio
    async def test_accept_consent_notice_integration(
        self, async_client, test_token, test_user, db_session
    ):
        """Test accepting consent notice with proper auth."""

        async def mock_get_user_by_id(db, user_id):
            if user_id == "test-user-123":
                return test_user
            return None

        with (
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_id",
                mock_get_user_by_id,
            ),
            patch(
                "github_analyzer.api.auth.jwt.verify_token",
                return_value={"sub": test_user.user_id, "email": test_user.email},
            ),
        ):
            response = await async_client.post(
                "/api/v1/consent/accept-notice",
                headers={"Authorization": f"Bearer {test_token}"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["success"] is True
        assert data["consent_version"] == CURRENT_CONSENT_VERSION

    @pytest.mark.asyncio
    async def test_export_privacy_preferences_integration(
        self, async_client, test_token, db_session
    ):
        """Test exporting privacy preferences with proper auth."""
        # Create user with preferences
        user = User(
            user_id="test-export-user",
            email="export@example.com",
            full_name="Export User",
            subscription_plan=SubscriptionPlan.PROFESSIONAL,
            user_role=UserRole.USER,
            is_active=True,
            privacy_preferences=json.dumps(
                {
                    "training_usage": False,
                    "retention_period": "3_years",
                }
            ),
            consent_version_accepted="1.0",
            consent_notice_dismissed_at=datetime(
                2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc
            ),
        )

        async def mock_get_user_by_id(db, user_id):
            if user_id == "test-export-user":
                return user
            return None

        # Create token for export user
        export_token = create_access_token(
            {"sub": "test-export-user", "email": "export@example.com"}
        )

        with (
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_id",
                mock_get_user_by_id,
            ),
            patch(
                "github_analyzer.api.auth.jwt.verify_token",
                return_value={"sub": user.user_id, "email": user.email},
            ),
        ):
            response = await async_client.get(
                "/api/v1/consent/export-preferences",
                headers={"Authorization": f"Bearer {export_token}"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["user_id"] == "test-export-user"
        assert data["email"] == "export@example.com"
        assert "consent_settings" in data
        assert data["consent_version_accepted"] == "1.0"
