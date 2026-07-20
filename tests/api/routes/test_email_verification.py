"""
Tests for email verification endpoints.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from github_analyzer.database.models import EmailVerificationToken
from github_analyzer.database.operations import (
    EmailVerificationOperations,
    UserOperations,
)


class TestEmailVerification:
    """Test suite for email verification functionality."""

    @pytest.mark.asyncio
    async def test_verify_email_success(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test successful email verification."""
        # Create unverified user
        user = await UserOperations.create_user(
            db_session,
            email="test@example.com",
            password="TestPassword123!",
            full_name="Test User",
            usage_quota=100,
        )
        await db_session.commit()

        # Create verification token
        token = "test-verification-token"
        await EmailVerificationOperations.create_verification_token(
            db_session, user.user_id, token
        )
        await db_session.commit()

        # Mock email service
        with patch(
            "github_analyzer.api.services.email_service.EmailService.send_email"
        ) as mock_send:
            mock_send.return_value = True

            # Verify email
            response = await async_client.get(
                f"/api/v1/auth/verify-email?token={token}"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Email verified successfully! You can now login."
        assert data["user_id"] == user.user_id
        assert data["email"] == user.email

        # Check user is verified - need to refresh the session
        await db_session.refresh(user)
        assert user.is_verified is True

        # Check token is marked as used
        query = select(EmailVerificationToken).where(
            EmailVerificationToken.token == token
        )
        result = await db_session.execute(query)
        token_obj = result.scalar_one()
        assert token_obj.used_at is not None

    @pytest.mark.asyncio
    async def test_verify_email_invalid_token(self, async_client: AsyncClient):
        """Test email verification with invalid token."""
        response = await async_client.get(
            "/api/v1/auth/verify-email?token=invalid-token"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Invalid or expired verification token"

    @pytest.mark.asyncio
    async def test_verify_email_expired_token(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test email verification with expired token."""
        # Create user
        user = await UserOperations.create_user(
            db_session,
            email="test@example.com",
            password="TestPassword123!",
            full_name="Test User",
            usage_quota=100,
        )
        await db_session.commit()

        # Create expired token
        token = "expired-token"
        expired_time = datetime.now(timezone.utc) - timedelta(hours=25)
        token_obj = EmailVerificationToken(
            user_id=user.user_id,
            token=token,
            expires_at=expired_time,
        )
        db_session.add(token_obj)
        await db_session.commit()

        # Try to verify
        response = await async_client.get(f"/api/v1/auth/verify-email?token={token}")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Invalid or expired verification token"

    @pytest.mark.asyncio
    async def test_verify_email_already_used_token(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test email verification with already used token."""
        # Create user
        user = await UserOperations.create_user(
            db_session,
            email="test@example.com",
            password="TestPassword123!",
            full_name="Test User",
            usage_quota=100,
        )
        await db_session.commit()

        # Create used token
        token = "used-token"
        token_obj = EmailVerificationToken(
            user_id=user.user_id,
            token=token,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            used_at=datetime.now(timezone.utc),
        )
        db_session.add(token_obj)
        await db_session.commit()

        # Try to verify
        response = await async_client.get(f"/api/v1/auth/verify-email?token={token}")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Invalid or expired verification token"

    @pytest.mark.asyncio
    async def test_verify_email_already_verified_user(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test email verification for already verified user."""
        # Create verified user
        user = await UserOperations.create_user(
            db_session,
            email="test@example.com",
            password="TestPassword123!",
            full_name="Test User",
            usage_quota=100,
        )
        user.is_verified = True
        await db_session.commit()

        # Create token
        token = "test-token"
        await EmailVerificationOperations.create_verification_token(
            db_session, user.user_id, token
        )
        await db_session.commit()

        # Try to verify again
        response = await async_client.get(f"/api/v1/auth/verify-email?token={token}")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Email already verified"

    @pytest.mark.asyncio
    async def test_resend_verification_email_success(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test resending verification email."""
        # Create unverified user
        user = await UserOperations.create_user(
            db_session,
            email="test@example.com",
            password="TestPassword123!",
            full_name="Test User",
            usage_quota=100,
        )
        await db_session.commit()

        # Mock email service
        with patch(
            "github_analyzer.api.services.email_service.EmailService.send_email"
        ) as mock_send:
            mock_send.return_value = True

            # Resend verification
            response = await async_client.post(
                "/api/v1/auth/resend-verification", json={"email": "test@example.com"}
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Verification email sent! Please check your inbox."
        assert data["email"] == "test@example.com"

        # Check new token was created
        query = select(EmailVerificationToken).where(
            EmailVerificationToken.user_id == user.user_id
        )
        result = await db_session.execute(query)
        tokens = result.scalars().all()
        assert len(tokens) == 1
        assert tokens[0].used_at is None

    @pytest.mark.asyncio
    async def test_resend_verification_email_rate_limit(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test rate limiting for resending verification emails."""
        # Create unverified user
        user = await UserOperations.create_user(
            db_session,
            email="test@example.com",
            password="TestPassword123!",
            full_name="Test User",
            usage_quota=100,
        )
        await db_session.commit()

        # Create recent token (within 5 minutes)
        token = "recent-token"
        await EmailVerificationOperations.create_verification_token(
            db_session, user.user_id, token
        )
        await db_session.commit()

        # Try to resend immediately
        response = await async_client.post(
            "/api/v1/auth/resend-verification", json={"email": "test@example.com"}
        )

        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "wait 5 minutes" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_resend_verification_email_nonexistent_user(
        self, async_client: AsyncClient
    ):
        """Test resending verification for non-existent user."""
        # Should return success for security (don't reveal if email exists)
        response = await async_client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "nonexistent@example.com"},
        )

        # Returns 200 with generic message for security
        assert response.status_code == status.HTTP_200_OK
        assert "If the email exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_resend_verification_email_already_verified(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test resending verification for already verified user."""
        # Create verified user
        user = await UserOperations.create_user(
            db_session,
            email="test@example.com",
            password="TestPassword123!",
            full_name="Test User",
            usage_quota=100,
        )
        user.is_verified = True
        await db_session.commit()

        # Try to resend
        response = await async_client.post(
            "/api/v1/auth/resend-verification", json={"email": "test@example.com"}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Email already verified"

    @pytest.mark.asyncio
    async def test_login_unverified_user(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test login attempt with unverified email."""
        # Create unverified user
        await UserOperations.create_user(
            db_session,
            email="test@example.com",
            password="TestPassword123!",
            full_name="Test User",
            usage_quota=100,
        )
        await db_session.commit()

        # Try to login
        response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "TestPassword123!"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Email not verified" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_verified_user(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test login with verified email."""
        # Create verified user
        user = await UserOperations.create_user(
            db_session,
            email="test@example.com",
            password="TestPassword123!",
            full_name="Test User",
            usage_quota=100,
        )
        user.is_verified = True
        await db_session.commit()

        # Login should succeed
        response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "TestPassword123!"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_signup_sends_verification_email(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test that signup sends verification email."""
        # Mock the actual email service instead of the internal function
        with patch(
            "github_analyzer.api.services.email_service.EmailService.send_email"
        ) as mock_send:
            mock_send.return_value = True

            # Register new user
            response = await async_client.post(
                "/api/v1/auth/register",
                json={
                    "email": "newuser@example.com",
                    "password": "TestPassword123!",
                    "full_name": "New User",
                    "company": "Test Corp",
                },
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["is_verified"] is False

        # Check that a verification token was created in the database
        query = select(EmailVerificationToken).where(
            EmailVerificationToken.user_id == data["user_id"]
        )
        result = await db_session.execute(query)
        tokens = result.scalars().all()
        assert len(tokens) == 1
        assert tokens[0].used_at is None

    @pytest.mark.asyncio
    async def test_email_verification_operations(self, db_session: AsyncSession):
        """Test EmailVerificationOperations methods."""
        # Create user
        user = await UserOperations.create_user(
            db_session,
            email="test@example.com",
            password="TestPassword123!",
            full_name="Test User",
            usage_quota=100,
        )
        await db_session.commit()

        # Test create_verification_token
        token = "test-token-ops"
        await EmailVerificationOperations.create_verification_token(
            db_session, user.user_id, token, expires_in_hours=48
        )
        await db_session.commit()

        # Test get_valid_token
        valid_token = await EmailVerificationOperations.get_valid_token(
            db_session, token
        )
        assert valid_token is not None
        assert valid_token.user_id == user.user_id
        assert valid_token.used_at is None

        # Test mark_token_used
        await EmailVerificationOperations.mark_token_used(db_session, token)
        await db_session.commit()

        # Token should no longer be valid
        invalid_token = await EmailVerificationOperations.get_valid_token(
            db_session, token
        )
        assert invalid_token is None

        # Test verify_user_email
        await EmailVerificationOperations.verify_user_email(db_session, user.user_id)
        await db_session.commit()

        verified_user = await UserOperations.get_user_by_id(db_session, user.user_id)
        assert verified_user.is_verified is True

        # Test get_user_tokens
        tokens = await EmailVerificationOperations.get_user_tokens(
            db_session, user.user_id
        )
        assert len(tokens) == 1
        assert tokens[0].token == token


class TestEmailTemplates:
    """Test email template generation."""

    def test_verification_email_template(self):
        """Test verification email template generation."""
        from github_analyzer.api.services.email_templates import (
            verification_email_template,
        )

        html, text = verification_email_template(
            "Test User", "https://example.com/verify/test-token", 24
        )

        assert "Test User" in html
        assert "Test User" in text
        assert "https://example.com/verify/test-token" in html
        assert "https://example.com/verify/test-token" in text
        assert "24 hours" in html
        assert "24 hours" in text
        assert "Verify Email Address" in html

    def test_welcome_email_template(self):
        """Test welcome email template generation."""
        from github_analyzer.api.services.email_templates import (
            welcome_email_template,
        )

        html, text = welcome_email_template("Test User")

        assert "Test User" in html
        assert "Test User" in text
        assert "Welcome to Exiqus" in html
        assert "Go to Dashboard" in html

    def test_resend_verification_email_template(self):
        """Test resend verification email template generation."""
        from github_analyzer.api.services.email_templates import (
            resend_verification_email_template,
        )

        html, text = resend_verification_email_template(
            "Test User", "https://example.com/verify/new-token", 24
        )

        assert "Test User" in html
        assert "Test User" in text
        assert "https://example.com/verify/new-token" in html
        assert "https://example.com/verify/new-token" in text
        assert "24 hours" in html
        assert "24 hours" in text
        assert "New Verification Link" in html


class TestEmailService:
    """Test email service functionality."""

    @pytest.mark.asyncio
    async def test_console_email_backend(self):
        """Test console email backend."""
        from github_analyzer.api.services.email_service import ConsoleEmailBackend

        backend = ConsoleEmailBackend()

        # Should always return True and print to console
        result = await backend.send_email(
            to_email="test@example.com",
            subject="Test Email",
            html_content="<p>Test</p>",
            text_content="Test",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_resend_email_backend_no_api_key(self):
        """Test Resend backend without API key."""
        from github_analyzer.api.services.email_service import ResendEmailBackend

        with patch.dict("os.environ", {}, clear=True):
            backend = ResendEmailBackend()

            result = await backend.send_email(
                to_email="test@example.com",
                subject="Test Email",
                html_content="<p>Test</p>",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_email_service_backend_selection(self):
        """Test email service backend selection."""
        from github_analyzer.api.services.email_service import EmailService

        # Test console backend (default)
        with patch.dict("os.environ", {"EMAIL_BACKEND": "console"}):
            service = EmailService()
            assert service.backend.__class__.__name__ == "ConsoleEmailBackend"

        # Test resend backend
        with patch.dict("os.environ", {"EMAIL_BACKEND": "resend"}):
            service = EmailService()
            assert service.backend.__class__.__name__ == "ResendEmailBackend"
