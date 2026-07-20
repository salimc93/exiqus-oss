"""Tests for training data export API endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status

from github_analyzer.api.auth.jwt import create_access_token
from github_analyzer.database.models import SubscriptionPlan, User, UserRole


class TestTrainingDataRoutes:
    """Test training data export endpoints."""

    @pytest.fixture
    def admin_user(self):
        """Create an admin user."""
        user = MagicMock(spec=User)
        user.user_id = "admin-123"
        user.email = "admin@example.com"
        user.user_role = UserRole.ADMIN
        user.is_admin = True
        user.is_active = True
        user.subscription_plan = SubscriptionPlan.ENTERPRISE
        return user

    @pytest.fixture
    def regular_user(self):
        """Create a regular user."""
        user = MagicMock(spec=User)
        user.user_id = "user-123"
        user.email = "user@example.com"
        user.user_role = UserRole.USER
        user.is_admin = False
        user.is_active = True
        user.subscription_plan = SubscriptionPlan.PROFESSIONAL
        return user

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def admin_token(self):
        """Create a valid admin token."""
        return create_access_token({"sub": "admin-123", "email": "admin@example.com"})

    @pytest.fixture
    def user_token(self):
        """Create a valid user token."""
        return create_access_token({"sub": "user-123", "email": "user@example.com"})

    async def _with_auth(self, async_client, token, user, mock_db_session, test_func):
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
                "github_analyzer.api.routes.training_data.get_db_session",
                return_value=mock_db_session,
            ),
        ):
            return await test_func(async_client, token)

    @pytest.mark.asyncio
    async def test_export_training_data_success(
        self, async_client, admin_user, admin_token, mock_db_session
    ):
        """Test successful training data export."""
        mock_training_data = [
            {
                "analysis_id": "1",
                "anonymized_user": "anon1",
                "context": "startup",
                "evidence_patterns": {"test": True},
            },
            {
                "analysis_id": "2",
                "anonymized_user": "anon2",
                "context": "enterprise",
                "evidence_patterns": {"test": True},
            },
        ]

        async def test_func(client, token):
            with (
                patch(
                    "github_analyzer.api.routes.training_data.TrainingDataExporter.export_training_data",
                    return_value=mock_training_data,
                ) as mock_export,
                patch(
                    "github_analyzer.api.routes.training_data.TrainingDataExporter.validate_consent_compliance",
                    return_value={
                        "compliant": 2,
                        "non_compliant": 0,
                        "non_compliant_ids": [],
                        "compliance_rate": 1.0,
                    },
                ),
                patch(
                    "github_analyzer.api.routes.training_data.TrainingDataExporter.prepare_for_export",
                    return_value='{"test": "data"}',
                ),
            ):
                response = await client.post(
                    "/api/v1/training-data/export",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "days_back": 30,
                        "min_analyses_per_user": 5,
                        "format": "jsonl",
                    },
                )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["message"] == "Training data exported successfully"
            assert data["examples_exported"] == 2
            assert data["format"] == "jsonl"
            assert data["compliance_rate"] == 1.0

            # Verify export was called with correct parameters
            mock_export.assert_called_once()
            call_args = mock_export.call_args[1]
            assert call_args["days_back"] == 30
            assert call_args["min_analyses_per_user"] == 5
            assert call_args["tier_filter"] is None
            return response

        await self._with_auth(
            async_client, admin_token, admin_user, mock_db_session, test_func
        )

    @pytest.mark.asyncio
    async def test_export_training_data_with_tier_filter(
        self, async_client, admin_user, admin_token, mock_db_session
    ):
        """Test training data export with tier filter."""

        async def test_func(client, token):
            with (
                patch(
                    "github_analyzer.api.routes.training_data.TrainingDataExporter.export_training_data",
                    return_value=[],
                ) as mock_export,
            ):
                response = await client.post(
                    "/api/v1/training-data/export",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "days_back": 30,
                        "min_analyses_per_user": 5,
                        "tier_filter": ["PROFESSIONAL", "ENTERPRISE"],
                        "format": "json",
                    },
                )

            assert response.status_code == status.HTTP_200_OK

            # Verify tier filter was converted to enums
            call_args = mock_export.call_args[1]
            assert call_args["tier_filter"] == [
                SubscriptionPlan.PROFESSIONAL,
                SubscriptionPlan.ENTERPRISE,
            ]
            return response

        await self._with_auth(
            async_client, admin_token, admin_user, mock_db_session, test_func
        )

    @pytest.mark.asyncio
    async def test_export_training_data_no_data(
        self, async_client, admin_user, admin_token, mock_db_session
    ):
        """Test export when no training data is available."""

        async def test_func(client, token):
            with (
                patch(
                    "github_analyzer.api.routes.training_data.TrainingDataExporter.export_training_data",
                    return_value=[],
                ),
            ):
                response = await client.post(
                    "/api/v1/training-data/export",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"days_back": 30},
                )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["message"] == "No training data available with current filters"
            assert data["examples_exported"] == 0
            return response

        await self._with_auth(
            async_client, admin_token, admin_user, mock_db_session, test_func
        )

    @pytest.mark.asyncio
    async def test_export_training_data_non_admin(
        self, async_client, regular_user, user_token, mock_db_session
    ):
        """Test that non-admin users cannot export training data."""

        async def test_func(client, token):
            response = await client.post(
                "/api/v1/training-data/export",
                headers={"Authorization": f"Bearer {token}"},
                json={"days_back": 30},
            )

            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert "admin privileges" in response.json()["detail"].lower()
            return response

        await self._with_auth(
            async_client, user_token, regular_user, mock_db_session, test_func
        )

    @pytest.mark.asyncio
    async def test_export_training_data_with_compliance_check(
        self, async_client, admin_user, admin_token, mock_db_session
    ):
        """Test export with compliance validation."""
        mock_training_data = [
            {"analysis_id": "1", "data": "compliant"},
            {"analysis_id": "2", "data": "compliant"},
        ]

        async def test_func(client, token):
            # Create an async function for the mock
            async def mock_validate_compliance(db, data):
                return {
                    "compliant": 2,
                    "non_compliant": 0,
                    "non_compliant_ids": [],
                    "compliance_rate": 1.0,
                }

            with (
                patch(
                    "github_analyzer.api.routes.training_data.TrainingDataExporter.export_training_data",
                    return_value=mock_training_data,
                ),
                patch(
                    "github_analyzer.api.routes.training_data.TrainingDataExporter.validate_consent_compliance",
                    side_effect=mock_validate_compliance,
                ),
                patch(
                    "github_analyzer.api.routes.training_data.TrainingDataExporter.prepare_for_export",
                    return_value='[{"data": "export_data"}]',
                ),
            ):
                response = await client.post(
                    "/api/v1/training-data/export",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"format": "jsonl"},
                )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["examples_exported"] == 2
            assert data["compliance_rate"] == 1.0
            return response

        await self._with_auth(
            async_client, admin_token, admin_user, mock_db_session, test_func
        )

    @pytest.mark.asyncio
    async def test_get_training_data_metrics_success(
        self, async_client, admin_user, admin_token, mock_db_session
    ):
        """Test getting training data metrics."""
        mock_training_data = [
            {
                "anonymized_user": "user1",
                "context": "startup",
                "repository_type": "web-app",
                "analysis_date": "2024-01-01T10:00:00",
            },
            {
                "anonymized_user": "user2",
                "context": "enterprise",
                "repository_type": "api",
                "analysis_date": "2024-01-02T10:00:00",
            },
        ]

        async def test_func(client, token):
            with (
                patch(
                    "github_analyzer.api.routes.training_data.TrainingDataExporter.export_training_data",
                    return_value=mock_training_data,
                ),
                patch(
                    "github_analyzer.api.routes.training_data.TrainingDataExporter.export_diversity_metrics",
                    return_value={
                        "total_examples": 2,
                        "unique_users": 2,
                        "context_distribution": {"startup": 1, "enterprise": 1},
                        "repository_types": {"web-app": 1, "api": 1},
                        "date_range": {
                            "earliest": "2024-01-01T10:00:00",
                            "latest": "2024-01-02T10:00:00",
                        },
                        "examples_per_user": 1.0,
                    },
                ),
                patch(
                    "github_analyzer.api.routes.training_data.TrainingDataExporter.validate_consent_compliance",
                    return_value={
                        "compliant": 2,
                        "compliance_rate": 1.0,
                    },
                ),
            ):
                response = await client.get(
                    "/api/v1/training-data/metrics?days_back=30",
                    headers={"Authorization": f"Bearer {token}"},
                )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["total_examples"] == 2
            assert data["unique_users"] == 2
            assert data["context_distribution"]["startup"] == 1
            assert data["repository_types"]["api"] == 1
            assert data["examples_per_user"] == 1.0
            assert data["consent_compliance"]["compliance_rate"] == 1.0
            return response

        await self._with_auth(
            async_client, admin_token, admin_user, mock_db_session, test_func
        )

    @pytest.mark.asyncio
    async def test_get_training_data_metrics_non_admin(
        self, async_client, regular_user, user_token, mock_db_session
    ):
        """Test that non-admin users cannot get metrics."""

        async def test_func(client, token):
            response = await client.get(
                "/api/v1/training-data/metrics",
                headers={"Authorization": f"Bearer {token}"},
            )

            assert response.status_code == status.HTTP_403_FORBIDDEN
            return response

        await self._with_auth(
            async_client, user_token, regular_user, mock_db_session, test_func
        )

    @pytest.mark.asyncio
    async def test_download_training_data_not_implemented(
        self, async_client, admin_user, admin_token, mock_db_session
    ):
        """Test download endpoint returns not implemented."""

        async def test_func(client, token):
            response = await client.get(
                "/api/v1/training-data/download/export-123",
                headers={"Authorization": f"Bearer {token}"},
            )

            assert response.status_code == status.HTTP_501_NOT_IMPLEMENTED
            assert "not yet implemented" in response.json()["detail"]
            return response

        await self._with_auth(
            async_client, admin_token, admin_user, mock_db_session, test_func
        )

    @pytest.mark.asyncio
    async def test_export_training_data_invalid_tier(
        self, async_client, admin_user, admin_token, mock_db_session
    ):
        """Test export with invalid tier filter."""

        async def test_func(client, token):
            response = await client.post(
                "/api/v1/training-data/export",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "tier_filter": ["invalid_tier"],
                },
            )

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            return response

        await self._with_auth(
            async_client, admin_token, admin_user, mock_db_session, test_func
        )
