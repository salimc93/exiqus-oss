"""Tests for consent management API endpoints."""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status

from github_analyzer.api.auth.jwt import create_access_token
from github_analyzer.api.services.consent_service import CURRENT_CONSENT_VERSION
from github_analyzer.database.models import SubscriptionPlan, User


class TestConsentRoutes:
    """Test consent management endpoints."""

    @pytest.fixture
    def test_token(self):
        """Create a valid test token."""
        return create_access_token(
            {"sub": "test-user-123", "email": "test@example.com"}
        )

    @pytest.fixture
    def mock_user(self):
        """Create a mock user for testing."""
        user = MagicMock(spec=User)
        user.user_id = "test-user-123"
        user.email = "test@example.com"
        user.subscription_plan = SubscriptionPlan.PROFESSIONAL
        user.privacy_preferences = None
        user.consent_version_accepted = None
        user.consent_notice_dismissed_at = None
        user.is_active = True
        # Allow setting attributes on the mock
        user.configure_mock(
            **{
                "privacy_preferences": None,
                "consent_version_accepted": None,
                "consent_notice_dismissed_at": None,
            }
        )
        return user

    @pytest.fixture
    def mock_free_user(self):
        """Create a mock free tier user."""
        user = MagicMock(spec=User)
        user.user_id = "free-user-123"
        user.email = "free@example.com"
        user.subscription_plan = SubscriptionPlan.FREE
        user.privacy_preferences = None
        user.consent_version_accepted = None
        user.consent_notice_dismissed_at = None
        user.is_active = True
        return user

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    async def _with_auth(
        self, async_client, test_token, user, mock_db_session, test_func
    ):
        """Helper to run tests with authentication patches."""

        async def mock_get_user_by_id(db, user_id):
            if user_id == user.user_id:
                return user
            return None

        with (
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_id",
                mock_get_user_by_id,
            ),
            patch(
                "github_analyzer.api.auth.jwt.verify_token",
                return_value={"sub": user.user_id, "email": user.email},
            ),
            patch(
                "github_analyzer.api.routes.consent.get_db_session",
                return_value=mock_db_session,
            ),
        ):
            return await test_func(async_client, test_token)

    @pytest.mark.asyncio
    async def test_get_consent_settings_success(
        self, async_client, test_token, mock_user, mock_db_session
    ):
        """Test getting consent settings."""

        async def test_func(client, token):
            response = await client.get(
                "/api/v1/consent/settings",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert "consent_settings" in data
            assert "tier_defaults" in data
            assert "consent_version" in data
            assert data["consent_version"] == CURRENT_CONSENT_VERSION
            assert "show_notice" in data
            assert data["show_notice"] is True  # New pro user should see notice
            return response

        await self._with_auth(
            async_client, test_token, mock_user, mock_db_session, test_func
        )

    @pytest.mark.asyncio
    async def test_get_consent_settings_with_preferences(
        self, async_client, test_token, mock_db_session
    ):
        """Test getting consent settings with existing preferences."""
        user = MagicMock(spec=User)
        user.user_id = "test-user-456"
        user.email = "test@example.com"
        user.subscription_plan = SubscriptionPlan.ENTERPRISE
        user.is_active = True
        user.privacy_preferences = json.dumps(
            {
                "training_usage": True,
                "anonymized": True,
            }
        )
        user.consent_version_accepted = CURRENT_CONSENT_VERSION
        user.consent_notice_dismissed_at = datetime.now(timezone.utc)

        async def test_func(client, token):
            response = await client.get(
                "/api/v1/consent/settings",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["consent_settings"]["training_usage"] is True
            assert data["show_notice"] is False  # Already dismissed
            return response

        await self._with_auth(
            async_client, test_token, user, mock_db_session, test_func
        )

    @pytest.mark.asyncio
    async def test_update_consent_settings_success(
        self, async_client, test_token, mock_user, mock_db_session
    ):
        """Test updating consent settings."""

        async def test_func(client, token):
            response = await client.put(
                "/api/v1/consent/settings",
                headers={"Authorization": f"Bearer {token}"},
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
            return response

        await self._with_auth(
            async_client, test_token, mock_user, mock_db_session, test_func
        )

    @pytest.mark.asyncio
    async def test_update_consent_settings_free_tier_limited(
        self, async_client, test_token, mock_free_user, mock_db_session
    ):
        """Test that free tier users have limited update options."""

        async def test_func(client, token):
            response = await client.put(
                "/api/v1/consent/settings",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "training_usage": False,
                    "retention_period": "5_years",  # Should be ignored
                },
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # Only training_usage should be updated
            assert data["updated_settings"] == {"training_usage": False}
            return response

        await self._with_auth(
            async_client, test_token, mock_free_user, mock_db_session, test_func
        )

    @pytest.mark.asyncio
    async def test_update_consent_with_dismiss_notice(
        self, async_client, test_token, mock_user, mock_db_session
    ):
        """Test updating consent and dismissing notice."""

        async def test_func(client, token):
            response = await client.put(
                "/api/v1/consent/settings",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "training_usage": False,
                    "dismiss_notice": True,
                },
            )
            assert response.status_code == status.HTTP_200_OK
            return response

        await self._with_auth(
            async_client, test_token, mock_user, mock_db_session, test_func
        )

    @pytest.mark.asyncio
    async def test_update_consent_all_fields(
        self, async_client, test_token, mock_user, mock_db_session
    ):
        """Test updating all consent fields at once."""

        async def test_func(client, token):
            response = await client.put(
                "/api/v1/consent/settings",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "training_usage": False,
                    "anonymized": False,
                    "retention_period": "1_year",
                    "third_party_sharing": False,
                    "custom_retention_days": 180,
                },
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # Verify all fields were updated
            assert data["success"] is True
            assert "updated_settings" in data
            assert data["updated_settings"]["training_usage"] is False
            assert data["updated_settings"]["retention_period"] == "1_year"
            return response

        await self._with_auth(
            async_client, test_token, mock_user, mock_db_session, test_func
        )

    @pytest.mark.asyncio
    async def test_accept_consent_notice_success(
        self, async_client, test_token, mock_user, mock_db_session
    ):
        """Test accepting consent notice."""

        async def test_func(client, token):
            response = await client.post(
                "/api/v1/consent/accept-notice",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["success"] is True
            assert data["consent_version"] == CURRENT_CONSENT_VERSION
            return response

        await self._with_auth(
            async_client, test_token, mock_user, mock_db_session, test_func
        )

    @pytest.mark.asyncio
    async def test_export_privacy_preferences(
        self, async_client, test_token, mock_db_session
    ):
        """Test exporting privacy preferences."""
        user = MagicMock(spec=User)
        user.user_id = "test-export-user"
        user.email = "export@example.com"
        user.subscription_plan = SubscriptionPlan.PROFESSIONAL
        user.is_active = True
        user.privacy_preferences = json.dumps(
            {
                "training_usage": False,
                "retention_period": "3_years",
            }
        )
        user.consent_version_accepted = "1.0"
        user.consent_notice_dismissed_at = datetime(
            2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc
        )

        async def test_func(client, token):
            response = await client.get(
                "/api/v1/consent/export-preferences",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["user_id"] == "test-export-user"
            assert data["email"] == "export@example.com"
            assert "consent_settings" in data
            assert data["consent_version_accepted"] == "1.0"
            assert data["consent_notice_dismissed_at"] == "2024-01-15T10:30:00+00:00"
            assert data["subscription_plan"] == "PROFESSIONAL"
            assert "data_retention_days" in data
            assert "export_timestamp" in data
            return response

        await self._with_auth(
            async_client, test_token, user, mock_db_session, test_func
        )

    @pytest.mark.asyncio
    async def test_get_consent_settings_unauthorized(self, async_client):
        """Test getting consent settings without authentication."""
        response = await async_client.get("/api/v1/consent/settings")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
