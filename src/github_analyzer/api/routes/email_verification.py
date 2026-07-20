# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Email verification endpoints.

Handles email verification token generation, validation, and resending.
"""

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.connection import get_db_session
from ...database.operations import EmailVerificationOperations, UserOperations
from ...utils.config import get_config
from ...utils.logging import get_logger
from ..services.email_service import EmailService
from ..services.email_templates import (
    resend_verification_email_template,
    verification_email_template,
    welcome_email_template,
)

logger = get_logger(__name__)
config = get_config()
router = APIRouter(prefix="/auth", tags=["Authentication"])


# Response models
class VerificationResponse(BaseModel):
    message: str
    user_id: str
    email: str


class ResendVerificationRequest(BaseModel):
    email: str


class ResendVerificationResponse(BaseModel):
    message: str
    email: str


# Helper functions
def generate_verification_token() -> str:
    """Generate a secure verification token."""
    return secrets.token_urlsafe(32)


def build_verification_url(token: str) -> str:
    """Build the verification URL."""
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    return f"{frontend_url}/auth/verify-email?token={token}"


@router.get("/verify-email", response_model=VerificationResponse)
async def verify_email(
    token: str,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> VerificationResponse:
    """
    Verify user email with the provided token.

    Args:
        token: Email verification token
        background_tasks: Background task queue for sending welcome email
        db: Database session

    Returns:
        VerificationResponse: Success message with user info

    Raises:
        HTTPException: If token is invalid, expired, or already used
    """
    try:
        # Get the verification token
        verification_token = await EmailVerificationOperations.get_valid_token(
            db, token
        )

        if not verification_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token",
            )

        # Get the user
        user = await UserOperations.get_user_by_id(db, verification_token.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Check if already verified
        if user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already verified",
            )

        # Mark email as verified
        await EmailVerificationOperations.verify_user_email(db, user.user_id)

        # Mark token as used
        await EmailVerificationOperations.mark_token_used(db, token)

        await db.commit()

        # Send welcome email in background
        email_service = EmailService()
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        html_content, text_content = welcome_email_template(
            user.full_name, frontend_url
        )

        background_tasks.add_task(
            email_service.send_email,
            to_email=user.email,
            subject="Welcome to Exiqus - Your Account is Ready",
            html_content=html_content,
            text_content=text_content,
        )

        logger.info(f"Email verified for user: {user.email}")

        return VerificationResponse(
            message="Email verified successfully! You can now login.",
            user_id=user.user_id,
            email=user.email,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify email",
        )


@router.post("/resend-verification", response_model=ResendVerificationResponse)
async def resend_verification_email(
    request: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ResendVerificationResponse:
    """
    Resend verification email to user.

    Rate limited to prevent abuse.

    Args:
        request: Email to resend verification to
        background_tasks: Background task queue
        db: Database session

    Returns:
        ResendVerificationResponse: Success message

    Raises:
        HTTPException: If user not found or already verified
    """
    # Validate email is not disposable
    from ..services.email_validator import EmailValidator

    is_valid, error_message = EmailValidator.validate_email(request.email)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=error_message
        )

    try:
        # Get user by email
        user = await UserOperations.get_user_by_email(db, request.email)

        if not user:
            # Don't reveal if email exists
            raise HTTPException(
                status_code=status.HTTP_200_OK,
                detail="If the email exists, a verification link has been sent",
            )

        # Check if already verified
        if user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already verified",
            )

        # Check rate limit - get recent tokens
        recent_tokens = await EmailVerificationOperations.get_user_tokens(
            db, user.user_id
        )

        # Check if recent token was created in last 5 minutes
        five_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
        recent_token = next(
            (
                t
                for t in recent_tokens
                if (
                    t.created_at.replace(tzinfo=timezone.utc)
                    if t.created_at.tzinfo is None
                    else t.created_at
                )
                > five_minutes_ago
                and not t.used_at
            ),
            None,
        )

        if recent_token:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Please wait 5 minutes before requesting another verification email",
            )

        # Generate new token
        token = generate_verification_token()
        verification_url = build_verification_url(token)

        # Save token
        await EmailVerificationOperations.create_verification_token(
            db, user.user_id, token, expires_in_hours=24
        )

        await db.commit()

        # Send email in background
        email_service = EmailService()
        html_content, text_content = resend_verification_email_template(
            user.full_name, verification_url, expires_in_hours=24
        )

        background_tasks.add_task(
            email_service.send_email,
            to_email=user.email,
            subject="New verification link - Exiqus",
            html_content=html_content,
            text_content=text_content,
        )

        logger.info(f"Resent verification email to: {user.email}")

        return ResendVerificationResponse(
            message="Verification email sent! Please check your inbox.",
            email=request.email,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resending verification email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resend verification email",
        )


@router.post("/send-verification/{user_id}")
async def send_verification_email_internal(
    user_id: str,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, bool]:
    """
    Internal endpoint to send verification email.

    Used by signup process.

    Args:
        user_id: User ID to send verification to
        background_tasks: Background task queue
        db: Database session

    Returns:
        dict: Success status
    """
    try:
        # Get user
        user = await UserOperations.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Generate token
        token = generate_verification_token()
        verification_url = build_verification_url(token)

        # Save token
        await EmailVerificationOperations.create_verification_token(
            db, user.user_id, token, expires_in_hours=24
        )

        await db.commit()

        # Send email in background
        email_service = EmailService()
        html_content, text_content = verification_email_template(
            user.full_name, verification_url, expires_in_hours=24
        )

        background_tasks.add_task(
            email_service.send_email,
            to_email=user.email,
            subject="Verify your email - Exiqus",
            html_content=html_content,
            text_content=text_content,
        )

        logger.info(f"Sent verification email to: {user.email}")

        return {"success": True}

    except Exception as e:
        logger.error(f"Error sending verification email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email",
        )
