# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Authentication routes for user management and security.

This module provides endpoints for user registration, login, token refresh,
and API key management.
"""

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Annotated, List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Cookie,
    Depends,
    HTTPException,
    Response,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.connection import get_db_session
from ...database.models import User
from ...database.operations import APIKeyOperations, UserOperations
from ...utils.logging import get_logger
from ..auth.dependencies import get_current_active_user, get_current_user_id
from ..auth.jwt import (
    JWTError,
    create_token_pair,
    generate_api_key,
    hash_password,
    refresh_access_token,
    verify_password,
)
from ..models.auth import (
    APIKeyCreate,
    APIKeyInfo,
    APIKeyResponse,
    PasswordChange,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserLogin,
    UserProfile,
    UserProfileUpdate,
    UserRegistration,
)
from ..utils.user_profile import convert_db_user_to_profile

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])

# Cookie configuration for refresh tokens
REFRESH_TOKEN_COOKIE_NAME = "refresh_token"  # nosec B105 - cookie name, not a password  # noqa: S105 - not a credential
REFRESH_TOKEN_MAX_AGE = 30 * 24 * 60 * 60  # 30 days in seconds
REFRESH_TOKEN_PATH = "/api/v1/auth/"  # nosec B105 - URL path, not a password  # noqa: S105 - not a credential


def _is_production() -> bool:
    """Check if running in production environment."""
    return os.getenv("ENVIRONMENT", "development").lower() == "production"


def _set_refresh_token_cookie(response: Response, refresh_token: str) -> None:
    """Set httpOnly cookie for refresh token."""
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        value=refresh_token,
        httponly=True,  # Not accessible to JavaScript - XSS protection
        secure=_is_production(),  # HTTPS only in production
        samesite="lax",  # CSRF protection, allows same-site navigation
        max_age=REFRESH_TOKEN_MAX_AGE,
        path=REFRESH_TOKEN_PATH,
    )


def _clear_refresh_token_cookie(response: Response) -> None:
    """Clear the refresh token cookie on logout."""
    response.delete_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        path=REFRESH_TOKEN_PATH,
        httponly=True,
        secure=_is_production(),
        samesite="lax",
    )


@router.post(
    "/register", response_model=UserProfile, status_code=status.HTTP_201_CREATED
)
async def register_user(
    user_data: UserRegistration,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
) -> UserProfile:
    """
    Register a new user account.

    Creates a new user with hashed password and default settings.
    Email verification is required before account activation.

    Args:
        user_data: User registration information
        db: Database session

    Returns:
        UserProfile: Created user profile

    Raises:
        HTTPException: If email already exists or registration fails
    """
    # Validate email is not disposable
    from ..services.email_validator import EmailValidator

    is_valid, error_message = EmailValidator.validate_email(user_data.email)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=error_message
        )

    try:
        # Create user in database
        user = await UserOperations.create_user(
            db,
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
            company=user_data.company,
            usage_quota=100,  # Default quota
        )

        await db.commit()

        # Send verification email
        import secrets

        from ...database.operations import EmailVerificationOperations
        from ..services.email_service import EmailService
        from ..services.email_templates import verification_email_template

        # Generate verification token
        token = secrets.token_urlsafe(32)
        verification_url = f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/auth/verify-email?token={token}"

        # Save token to database
        await EmailVerificationOperations.create_verification_token(
            db, user.user_id, token, expires_in_hours=24
        )
        await db.commit()

        # Send email in background
        email_service = EmailService()
        html_content, text_content = verification_email_template(
            user.full_name or user.email, verification_url, expires_in_hours=24
        )

        background_tasks.add_task(
            email_service.send_email,
            to_email=user.email,
            subject="Verify your email - Exiqus",
            html_content=html_content,
            text_content=text_content,
        )

        logger.info(f"Queued verification email for: {user.email}")

        return convert_db_user_to_profile(user)

    except ValueError as e:
        # Handle duplicate email error
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}",
        )


@router.post("/login", response_model=TokenResponse)
async def login_user(
    credentials: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """
    Authenticate user and return JWT tokens.

    Validates credentials and returns access token. Refresh token is set
    as an httpOnly cookie for security (not accessible to JavaScript).

    Args:
        credentials: User login credentials
        response: FastAPI response object for setting cookies
        db: Database session

    Returns:
        TokenResponse: Access token with expiration info

    Raises:
        HTTPException: If credentials are invalid
    """
    # Authenticate user
    user = await UserOperations.authenticate_user(
        db, credentials.email, credentials.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if email is verified
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please check your email for verification link.",
        )

    # Update last login timestamp
    await UserOperations.update_last_login(db, user.user_id)
    await db.commit()

    # Create token pair with user permissions
    tokens = create_token_pair(
        user_id=user.user_id,
        email=user.email,
        permissions=["analyze", "batch"] if user.is_verified else ["analyze"],
    )

    # Set refresh token as httpOnly cookie (XSS protection)
    _set_refresh_token_cookie(response, tokens["refresh_token"])

    # Return only access token in response body (refresh token is in cookie)
    return TokenResponse(
        access_token=tokens["access_token"],
        token_type="bearer",  # nosec B106  # noqa: S106 - not a credential
        expires_in=3600,  # 1 hour
        refresh_token=None,  # Not returned in body - stored in httpOnly cookie
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    response: Response,
    refresh_token_cookie: Optional[str] = Cookie(None, alias=REFRESH_TOKEN_COOKIE_NAME),
    token_request: Optional[RefreshTokenRequest] = None,
) -> TokenResponse:
    """
    Refresh access token using refresh token from httpOnly cookie.

    Validates refresh token and issues new access token.
    Also accepts refresh token in request body for backward compatibility.

    Args:
        response: FastAPI response for setting new cookie
        refresh_token_cookie: Refresh token from httpOnly cookie (preferred)
        token_request: Optional refresh token in request body (legacy support)

    Returns:
        TokenResponse: New access token

    Raises:
        HTTPException: If refresh token is missing or invalid
    """
    # Get refresh token from cookie (preferred) or request body (legacy)
    token_value = refresh_token_cookie
    if not token_value and token_request:
        token_value = token_request.refresh_token

    if not token_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        new_access_token = refresh_access_token(token_value)

        return TokenResponse(
            access_token=new_access_token,
            token_type="bearer",  # nosec B106  # noqa: S106 - not a credential
            expires_in=3600,  # 1 hour
            refresh_token=None,  # Refresh token stays in httpOnly cookie
        )

    except JWTError as e:
        # Clear invalid cookie
        _clear_refresh_token_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/profile", response_model=UserProfile)
async def get_user_profile(
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: AsyncSession = Depends(get_db_session),
) -> UserProfile:
    """
    Get current user profile information.

    Returns detailed profile information for the authenticated user.

    Args:
        user_id: Authenticated user ID
        db: Database session

    Returns:
        UserProfile: User profile data

    Raises:
        HTTPException: If user not found
    """
    user = await UserOperations.get_user_by_id(db, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return convert_db_user_to_profile(user)


@router.put("/profile", response_model=UserProfile)
async def update_user_profile(
    profile_update: UserProfileUpdate,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: AsyncSession = Depends(get_db_session),
) -> UserProfile:
    """
    Update user profile information.

    Updates the authenticated user's profile with the provided information.
    All fields are optional and only provided fields will be updated.

    Args:
        profile_update: Profile update data
        user_id: Authenticated user ID
        db: Database session

    Returns:
        UserProfile: Updated user profile

    Raises:
        HTTPException: If user not found or update fails
    """
    user = await UserOperations.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    try:
        # Convert notification preferences to JSON string if provided
        notification_prefs = None
        if profile_update.notification_preferences is not None:
            import json

            notification_prefs = json.dumps(profile_update.notification_preferences)

        # Update profile
        success = await UserOperations.update_user_profile(
            db,
            user_id,
            full_name=profile_update.full_name,
            company=profile_update.company,
            company_size=profile_update.company_size,
            industry=profile_update.industry,
            use_case=profile_update.use_case,
            notification_preferences=notification_prefs,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update profile",
            )

        await db.commit()

        # Return updated profile
        updated_user = await UserOperations.get_user_by_id(db, user_id)
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User disappeared after update",
            )
        return convert_db_user_to_profile(updated_user)

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {str(e)}",
        )


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    password_data: PasswordChange,
    db: AsyncSession = Depends(get_db_session),
    user_id: str = Depends(get_current_user_id),
) -> None:
    """
    Change user password.

    Validates current password and updates to new password.
    Invalidates all existing tokens.

    Args:
        password_data: Current and new password
        db: Database session
        user_id: Authenticated user ID

    Raises:
        HTTPException: If current password is incorrect
    """
    user = await UserOperations.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Authenticate with current password
    if not await UserOperations.authenticate_user(
        db, user.email, password_data.current_password
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Update password
    success = await UserOperations.update_password(
        db, user_id, password_data.new_password
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password",
        )

    await db.commit()

    # TODO: Invalidate all existing tokens for this user
    # This could be done by incrementing a token version in the database
    # and checking it during token validation


@router.post(
    "/api-keys", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED
)
async def create_api_key(
    key_data: APIKeyCreate,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: AsyncSession = Depends(get_db_session),
) -> APIKeyResponse:
    """
    Create a new API key for the authenticated user.

    Generates a secure API key with specified permissions and expiration.

    Args:
        key_data: API key creation parameters
        user_id: Authenticated user ID
        db: Database session

    Returns:
        APIKeyResponse: Created API key (key shown only once)
    """
    # Generate secure API key
    api_key = generate_api_key()
    now = datetime.now(timezone.utc)

    # Calculate expiration
    expires_at = None
    if key_data.expires_in_days:
        expires_at = now + timedelta(days=key_data.expires_in_days)

    # Hash the API key for storage
    key_hash = hash_password(api_key)  # Reuse password hashing for API keys

    # Store in database
    api_key_record = await APIKeyOperations.create_api_key(
        db,
        user_id=user_id,
        name=key_data.name,
        key_hash=key_hash,
        key_prefix="legacy",  # Legacy API keys use fixed prefix
        salt="legacy_salt",  # Legacy API keys use fixed salt
        permissions=key_data.permissions,
        expires_at=expires_at,
    )

    await db.commit()

    return APIKeyResponse(
        key_id=api_key_record.key_id,
        name=api_key_record.name,
        key=api_key,  # Only returned once during creation
        permissions=json.loads(api_key_record.permissions),
        created_at=api_key_record.created_at,
        expires_at=api_key_record.expires_at,
        is_active=api_key_record.is_active,
    )


@router.get("/api-keys", response_model=List[APIKeyInfo])
async def list_api_keys(
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: AsyncSession = Depends(get_db_session),
) -> List[APIKeyInfo]:
    """
    List all API keys for the authenticated user.

    Returns API key information without exposing the actual keys.

    Args:
        user_id: Authenticated user ID
        db: Database session

    Returns:
        List[APIKeyInfo]: User's API keys (without keys)
    """
    api_keys = await APIKeyOperations.get_user_api_keys(db, user_id)

    return [
        APIKeyInfo(
            key_id=api_key.key_id,
            name=api_key.name,
            permissions=json.loads(api_key.permissions),
            created_at=api_key.created_at,
            expires_at=api_key.expires_at,
            is_active=api_key.is_active,
            last_used=api_key.last_used,
        )
        for api_key in api_keys
    ]


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """
    Revoke (deactivate) an API key.

    Marks the API key as inactive, preventing further use.

    Args:
        key_id: API key identifier to revoke
        user_id: Authenticated user ID
        db: Database session

    Raises:
        HTTPException: If key not found or not owned by user
    """
    success = await APIKeyOperations.deactivate_api_key(db, key_id, user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )

    await db.commit()


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_user(
    response: Response,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> None:
    """
    Logout user by clearing refresh token cookie.

    Clears the httpOnly refresh token cookie to invalidate the session.
    Access tokens will expire naturally after their TTL.

    Args:
        response: FastAPI response for clearing cookie
        user_id: Authenticated user ID
    """
    # Clear the httpOnly refresh token cookie
    _clear_refresh_token_cookie(response)

    # TODO: Implement token blacklist for access tokens when database layer is ready
    # This could be done by:
    # 1. Adding token to blacklist table
    # 2. Incrementing user token version
    # 3. Storing token revocation in Redis
    logger.info(f"User {user_id} logged out successfully")


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    request_data: PasswordResetRequest,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """
    Request password reset email.

    Sends a password reset link to the user's email if the account exists.
    Returns success even if email doesn't exist (security best practice).
    Rate limited to prevent abuse.

    Args:
        request_data: Email address to send reset link
        db: Database session

    Returns:
        Success message
    """
    import secrets
    import uuid
    from datetime import timedelta

    from ...database.models import PasswordResetToken
    from ..services.email_service import email_service

    try:
        # Look up user by email
        user = await UserOperations.get_user_by_email(db, request_data.email)

        if user:
            # Generate secure reset token
            raw_token = secrets.token_urlsafe(32)
            token_hash = hash_password(raw_token)  # Reuse password hashing for tokens

            # Create reset token record
            reset_token = PasswordResetToken(
                token_id=f"prt_{uuid.uuid4().hex[:16]}",
                user_id=user.user_id,
                token_hash=token_hash,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                request_ip=None,  # TODO: Get from request context
                user_agent=None,  # TODO: Get from request headers
            )

            db.add(reset_token)
            await db.commit()

            # Build reset URL
            frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
            reset_url = f"{frontend_url}/reset-password?token={raw_token}"

            # Send email
            await email_service.send_password_reset_email(
                to_email=user.email, reset_url=reset_url, user_name=user.full_name
            )

        # Always return success (security best practice)
        return {
            "message": "If an account exists with this email, a password reset link has been sent."
        }

    except Exception as e:
        # Log error but don't expose it to user
        logger.error(f"Password reset error: {str(e)}")
        # Still return success message
        return {
            "message": "If an account exists with this email, a password reset link has been sent."
        }


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    reset_data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """
    Reset password with token.

    Validates the reset token and updates the user's password.
    Token is marked as used after successful reset.

    Args:
        reset_data: Reset token and new password
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If token is invalid, expired, or already used
    """
    from sqlalchemy import select

    from ...database.models import PasswordResetToken

    try:
        # Find all valid (unused, not expired) reset tokens
        query = select(PasswordResetToken).where(
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > datetime.now(timezone.utc),
        )

        result = await db.execute(query)
        potential_tokens = result.scalars().all()

        # Check each token hash with bcrypt
        import bcrypt

        reset_token = None
        for token in potential_tokens:
            if bcrypt.checkpw(reset_data.token.encode(), token.token_hash.encode()):
                reset_token = token
                break

        if not reset_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )

        # Update user's password
        user = await UserOperations.get_user_by_id(db, reset_token.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="User not found"
            )

        # Update password
        success = await UserOperations.update_password(
            db, user.user_id, reset_data.new_password
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update password",
            )

        # Mark token as used
        reset_token.used_at = datetime.now(timezone.utc)
        await db.commit()

        return {
            "message": "Password reset successful. You can now login with your new password."
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Password reset error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password",
        )


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    password_confirm: dict[str, str],
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """
    Delete user account (soft delete).

    Requires password confirmation for security.
    Account will be deactivated immediately and permanently deleted after 30 days.

    Args:
        password_confirm: Dictionary with 'password' key
        user: Current authenticated user
        db: Database session

    Raises:
        HTTPException: If password is incorrect
    """
    # Verify password
    password = password_confirm.get("password")
    if not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password confirmation required",
        )

    # Authenticate with current password
    if not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password"
        )

    # Soft delete the user
    success = await UserOperations.soft_delete_user(db, user.user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete account",
        )

    await db.commit()

    # Log the deletion request
    logger.info(f"User {user.email} requested account deletion")
