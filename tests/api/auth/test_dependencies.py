"""
Tests for authentication dependencies including require_api_access.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from github_analyzer.api.auth.dependencies import (
    AuthenticationError,
    AuthorizationError,
    require_api_access,
)
from github_analyzer.database.models import SubscriptionPlan, User


class TestRequireAPIAccess:
    """Test suite for require_api_access dependency."""

    @pytest.fixture
    def mock_request(self):
        """Create a mock FastAPI request."""
        request = Mock(spec=Request)
        request.state = Mock()
        return request

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return Mock(spec=AsyncSession)

    @pytest.fixture
    def mock_api_key_record(self):
        """Create a mock API key record."""
        record = Mock()
        record.user_id = "test_user_123"
        record.key_id = "key_123"
        record.name = "Test API Key"
        return record

    @pytest.fixture
    def mock_user_professional(self):
        """Create a mock user with Professional plan."""
        user = Mock(spec=User)
        user.user_id = "test_user_123"
        user.email = "pro@example.com"
        user.subscription_plan = SubscriptionPlan.PROFESSIONAL
        return user

    @pytest.fixture
    def mock_user_basic(self):
        """Create a mock user with Basic plan."""
        user = Mock(spec=User)
        user.user_id = "test_user_123"
        user.email = "basic@example.com"
        user.subscription_plan = SubscriptionPlan.BASIC
        return user

    @pytest.fixture
    def mock_user_free(self):
        """Create a mock user with Free plan."""
        user = Mock(spec=User)
        user.user_id = "test_user_123"
        user.email = "free@example.com"
        user.subscription_plan = SubscriptionPlan.FREE
        return user

    async def test_no_api_key_raises_authentication_error(self, mock_request, mock_db):
        """Test that missing API key raises AuthenticationError."""
        with pytest.raises(AuthenticationError) as exc_info:
            await require_api_access(mock_request, None, mock_db)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "API key required" in str(exc_info.value.detail)

    async def test_invalid_api_key_raises_authentication_error(
        self, mock_request, mock_db
    ):
        """Test that invalid API key raises AuthenticationError."""
        with patch(
            "github_analyzer.api.auth.dependencies.APIKeyService"
        ) as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.validate_api_key = AsyncMock(return_value=None)

            with pytest.raises(AuthenticationError) as exc_info:
                await require_api_access(mock_request, "invalid_key", mock_db)

            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Invalid or inactive API key" in str(exc_info.value.detail)

    async def test_user_not_found_raises_authentication_error(
        self, mock_request, mock_db, mock_api_key_record
    ):
        """Test that missing user raises AuthenticationError."""
        with (
            patch(
                "github_analyzer.api.auth.dependencies.APIKeyService"
            ) as mock_service_class,
            patch(
                "github_analyzer.api.auth.dependencies.UserOperations"
            ) as mock_ops_class,
        ):
            # Setup API key validation
            mock_service = mock_service_class.return_value
            mock_service.validate_api_key = AsyncMock(return_value=mock_api_key_record)

            # Setup user lookup to return None
            mock_ops_class.get_user_by_id = AsyncMock(return_value=None)

            with pytest.raises(AuthenticationError) as exc_info:
                await require_api_access(mock_request, "valid_key", mock_db)

            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "User not found" in str(exc_info.value.detail)

    async def test_basic_plan_raises_authorization_error(
        self, mock_request, mock_db, mock_api_key_record, mock_user_basic
    ):
        """Test that Basic plan user gets AuthorizationError."""
        with (
            patch(
                "github_analyzer.api.auth.dependencies.APIKeyService"
            ) as mock_service_class,
            patch(
                "github_analyzer.api.auth.dependencies.UserOperations"
            ) as mock_ops_class,
        ):
            # Setup API key validation
            mock_service = mock_service_class.return_value
            mock_service.validate_api_key = AsyncMock(return_value=mock_api_key_record)

            # Setup user lookup
            mock_ops_class.get_user_by_id = AsyncMock(return_value=mock_user_basic)

            with pytest.raises(AuthorizationError) as exc_info:
                await require_api_access(mock_request, "valid_key", mock_db)

            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
            assert "API access is not available for your current plan" in str(
                exc_info.value.detail
            )
            assert "upgrade to Professional or Enterprise" in str(exc_info.value.detail)

    async def test_free_plan_raises_authorization_error(
        self, mock_request, mock_db, mock_api_key_record, mock_user_free
    ):
        """Test that Free plan user gets AuthorizationError."""
        with (
            patch(
                "github_analyzer.api.auth.dependencies.APIKeyService"
            ) as mock_service_class,
            patch(
                "github_analyzer.api.auth.dependencies.UserOperations"
            ) as mock_ops_class,
        ):
            # Setup API key validation
            mock_service = mock_service_class.return_value
            mock_service.validate_api_key = AsyncMock(return_value=mock_api_key_record)

            # Setup user lookup
            mock_ops_class.get_user_by_id = AsyncMock(return_value=mock_user_free)

            with pytest.raises(AuthorizationError) as exc_info:
                await require_api_access(mock_request, "valid_key", mock_db)

            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
            assert "API access is not available" in str(exc_info.value.detail)

    async def test_professional_plan_success(
        self, mock_request, mock_db, mock_api_key_record, mock_user_professional
    ):
        """Test that Professional plan user is authorized."""
        with (
            patch(
                "github_analyzer.api.auth.dependencies.APIKeyService"
            ) as mock_service_class,
            patch(
                "github_analyzer.api.auth.dependencies.UserOperations"
            ) as mock_ops_class,
        ):
            # Setup API key validation
            mock_service = mock_service_class.return_value
            mock_service.validate_api_key = AsyncMock(return_value=mock_api_key_record)

            # Setup user lookup
            mock_ops_class.get_user_by_id = AsyncMock(
                return_value=mock_user_professional
            )

            # Call the dependency
            result = await require_api_access(mock_request, "valid_key", mock_db)

            # Assert success
            assert result == "test_user_123"

            # Verify request state was updated
            assert mock_request.state.api_key_record == mock_api_key_record
            assert mock_request.state.authenticated_user_id == "test_user_123"

    async def test_enterprise_plan_success(
        self, mock_request, mock_db, mock_api_key_record
    ):
        """Test that Enterprise plan user is authorized."""
        # Create enterprise user
        mock_user_enterprise = Mock(spec=User)
        mock_user_enterprise.user_id = "test_user_123"
        mock_user_enterprise.email = "enterprise@example.com"
        mock_user_enterprise.subscription_plan = SubscriptionPlan.ENTERPRISE

        with (
            patch(
                "github_analyzer.api.auth.dependencies.APIKeyService"
            ) as mock_service_class,
            patch(
                "github_analyzer.api.auth.dependencies.UserOperations"
            ) as mock_ops_class,
        ):
            # Setup API key validation
            mock_service = mock_service_class.return_value
            mock_service.validate_api_key = AsyncMock(return_value=mock_api_key_record)

            # Setup user lookup
            mock_ops_class.get_user_by_id = AsyncMock(return_value=mock_user_enterprise)

            # Call the dependency
            result = await require_api_access(mock_request, "valid_key", mock_db)

            # Assert success
            assert result == "test_user_123"

    async def test_exception_handling(self, mock_request, mock_db):
        """Test that general exceptions are wrapped properly."""
        with patch(
            "github_analyzer.api.auth.dependencies.APIKeyService"
        ) as mock_service_class:
            # Setup API key validation to raise an exception
            mock_service = mock_service_class.return_value
            mock_service.validate_api_key = AsyncMock(
                side_effect=Exception("Database error")
            )

            with pytest.raises(AuthenticationError) as exc_info:
                await require_api_access(mock_request, "valid_key", mock_db)

            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "API key verification failed" in str(exc_info.value.detail)

    async def test_http_exceptions_are_reraised(self, mock_request, mock_db):
        """Test that HTTPExceptions are re-raised without wrapping."""
        custom_exception = HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Payment required"
        )

        with patch(
            "github_analyzer.api.auth.dependencies.APIKeyService"
        ) as mock_service_class:
            # Setup API key validation to raise HTTPException
            mock_service = mock_service_class.return_value
            mock_service.validate_api_key = AsyncMock(side_effect=custom_exception)

            with pytest.raises(HTTPException) as exc_info:
                await require_api_access(mock_request, "valid_key", mock_db)

            # Verify it's the same exception, not wrapped
            assert exc_info.value == custom_exception
            assert exc_info.value.status_code == status.HTTP_402_PAYMENT_REQUIRED
