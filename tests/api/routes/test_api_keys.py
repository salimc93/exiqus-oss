"""
Consolidated and corrected tests for API key management endpoints.
"""

from datetime import datetime, timezone

import pytest
from fastapi import status

from github_analyzer.api.auth.dependencies import get_current_user_id
from github_analyzer.database.models import APIKey, SubscriptionPlan, User, UserRole

# A real user who will exist in the test database
TEST_USER_ID = "test_user_auth_api_keys"
TEST_USER_EMAIL = "test-auth-api-keys@example.com"


@pytest.fixture(scope="function")
async def test_user(test_db) -> User:
    """
    Fixture to create a real user in the database for integration testing.
    The user is cleaned up after the test.
    """
    async with test_db() as session:
        user = User(
            user_id=TEST_USER_ID,
            email=TEST_USER_EMAIL,
            password_hash="a_real_password_hash",
            full_name="API Key Test User",
            subscription_plan=SubscriptionPlan.PROFESSIONAL,
            user_role=UserRole.USER,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        yield user

        # Teardown is handled by the in-memory database being recreated for each test


class TestAPIKeyCreation:
    """Tests for the API key creation endpoint."""

    async def test_create_api_key_success(self, async_client, test_user, mocker):
        """Test successful API key creation for an authenticated user."""
        # Override the dependency to use our real test user
        async_client.app.dependency_overrides[get_current_user_id] = lambda: (
            test_user.user_id
        )

        # Mock the service layer to isolate the endpoint logic
        mock_service = mocker.patch(
            "github_analyzer.api.routes.api_keys.APIKeyService",
            autospec=True,
        ).return_value
        mock_service.create_api_key.return_value = (
            APIKey(
                key_id="new_key_123",
                name="My New Key",
                permissions='["analyze"]',
                monthly_quota=500,
                monthly_usage=0,
                is_active=True,
                created_at=datetime.now(timezone.utc),
                last_used=None,
                expires_at=None,
                user_id=test_user.user_id,
            ),
            "gha_plaintextkey123456",  # The one-time plain text key
        )

        # Make the request with correct query parameters and an empty JSON body
        response = await async_client.post(
            "/api/v1/keys/?name=My New Key&permissions=analyze",
            json=[],
        )

        # Assertions
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["key_id"] == "new_key_123"
        assert data["name"] == "My New Key"
        assert data["api_key"] == "gha_plaintextkey123456"
        assert data["permissions"] == ["analyze"]

        # Cleanup
        async_client.app.dependency_overrides.clear()

    async def test_create_api_key_invalid_permissions(self, async_client, test_user):
        """Test that creating a key with invalid permissions fails correctly."""
        # This test validates the endpoint's own permission check, so we do NOT mock the service.
        async_client.app.dependency_overrides[get_current_user_id] = lambda: (
            test_user.user_id
        )

        # Make the request with an invalid permission
        response = await async_client.post(
            "/api/v1/keys/?name=Invalid Key&permissions=analyze&permissions=sudo",
            json=[],
        )

        # The endpoint should validate permissions and return a 400 before calling the service.
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid permissions" in response.json()["detail"]
        assert "sudo" in response.json()["detail"]

        # Cleanup
        async_client.app.dependency_overrides.clear()

    async def test_create_api_key_user_not_found(self, async_client):
        """Test creating a key for a user that does not exist."""
        # Use a user ID that is not in the database
        async_client.app.dependency_overrides[get_current_user_id] = lambda: (
            "non_existent_user"
        )

        response = await async_client.post(
            "/api/v1/keys/?name=A Key&permissions=analyze",
            json=[],
        )

        # The service should raise a ValueError, which the endpoint translates to a 404
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "User not found" in response.json()["detail"]

        # Cleanup
        async_client.app.dependency_overrides.clear()


class TestAPIKeyManagement:
    """Tests for listing, getting, and revoking API keys."""

    @pytest.fixture
    def auth_headers(self, test_user):
        """Fixture to provide authentication headers for a test user."""
        # In a real scenario, this would generate a valid JWT.
        # For these tests, we are mocking the dependency that decodes the token.
        return {"Authorization": f"Bearer fake-token-for-{test_user.user_id}"}

    async def test_list_api_keys(self, async_client, test_user, mocker, auth_headers):
        """Test listing API keys for an authenticated user."""
        async_client.app.dependency_overrides[get_current_user_id] = lambda: (
            test_user.user_id
        )

        mock_service = mocker.patch(
            "github_analyzer.api.routes.api_keys.APIKeyService",
            autospec=True,
        ).return_value
        mock_service.get_user_api_keys.return_value = [
            APIKey(
                key_id="key1",
                name="Key One",
                permissions="[]",
                monthly_quota=100,
                monthly_usage=10,
                is_active=True,
                created_at=datetime.now(timezone.utc),
            ),
            APIKey(
                key_id="key2",
                name="Key Two",
                permissions="[]",
                monthly_quota=100,
                monthly_usage=10,
                is_active=True,
                created_at=datetime.now(timezone.utc),
            ),
        ]

        response = await async_client.get("/api/v1/keys/", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_count"] == 2
        assert len(data["keys"]) == 2
        assert data["keys"][0]["key_id"] == "key1"
        assert (
            data["keys"][0]["api_key"] is None
        )  # Ensure plain text key is not exposed

        async_client.app.dependency_overrides.clear()

    async def test_get_api_key_details(
        self, async_client, test_user, mocker, auth_headers
    ):
        """Test getting the details of a specific API key."""
        async_client.app.dependency_overrides[get_current_user_id] = lambda: (
            test_user.user_id
        )

        mock_service = mocker.patch(
            "github_analyzer.api.routes.api_keys.APIKeyService",
            autospec=True,
        ).return_value
        mock_key = APIKey(
            key_id="some_key_id",
            name="A Key",
            user_id=test_user.user_id,
            permissions='["batch"]',
            monthly_quota=100,
            monthly_usage=10,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        mock_service.get_api_key_by_id.return_value = mock_key

        response = await async_client.get(
            "/api/v1/keys/some_key_id", headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["permissions"] == ["batch"]
        mock_service.get_api_key_by_id.assert_called_with("some_key_id")

        async_client.app.dependency_overrides.clear()

    async def test_get_api_key_access_denied(
        self, async_client, test_user, mocker, auth_headers
    ):
        """Test that a user cannot get a key they do not own."""
        async_client.app.dependency_overrides[get_current_user_id] = lambda: (
            test_user.user_id
        )

        mock_service = mocker.patch(
            "github_analyzer.api.routes.api_keys.APIKeyService",
            autospec=True,
        ).return_value
        # Key belongs to a different user
        mock_key = APIKey(
            key_id="another_users_key",
            name="Another Key",
            user_id="another_user_id",
            permissions="[]",
            monthly_quota=100,
            monthly_usage=10,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        mock_service.get_api_key_by_id.return_value = mock_key

        response = await async_client.get(
            "/api/v1/keys/another_users_key", headers=auth_headers
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Access denied" in response.json()["detail"]

        async_client.app.dependency_overrides.clear()

    async def test_revoke_api_key(self, async_client, test_user, mocker, auth_headers):
        """Test successfully revoking an API key."""
        async_client.app.dependency_overrides[get_current_user_id] = lambda: (
            test_user.user_id
        )

        mock_service = mocker.patch(
            "github_analyzer.api.routes.api_keys.APIKeyService",
            autospec=True,
        ).return_value
        mock_service.revoke_api_key.return_value = True

        response = await async_client.delete(
            "/api/v1/keys/key_to_revoke", headers=auth_headers
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_service.revoke_api_key.assert_called_with(
            "key_to_revoke", test_user.user_id
        )

        async_client.app.dependency_overrides.clear()
