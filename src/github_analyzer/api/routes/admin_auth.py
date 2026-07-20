# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Admin authentication routes with enhanced security.

This module provides separate authentication for admin users with
additional security measures including admin secret verification.
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Union

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.connection import get_db_session
from ...database.operations import UserOperations
from ...utils.config import get_config
from ..auth.jwt import create_access_token, create_refresh_token, verify_password

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/auth", tags=["Admin Authentication"])


def get_admin_config() -> Any:
    """Dependency provider for admin configuration."""
    return get_config()


class AdminLoginRequest(BaseModel):
    """Admin login request with additional security."""

    email: str
    password: str
    admin_secret: str


class AdminAuthResponse(BaseModel):
    """Admin authentication response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105 - not a credential
    expires_in: int = 7200  # 2 hours
    is_admin: bool = True
    email: str


@router.post("/login", response_model=AdminAuthResponse)
async def admin_login(
    request: AdminLoginRequest,
    db: AsyncSession = Depends(get_db_session),
    config: Any = Depends(get_admin_config),
) -> AdminAuthResponse:
    """
    Authenticate admin user with additional security verification.

    Requirements:
    - Valid email and password
    - User must have is_admin=True in database
    - Correct admin secret must be provided

    Args:
        request: Admin login credentials including secret
        db: Database session
        config: Configuration injected via dependency

    Returns:
        AdminAuthResponse: Admin JWT tokens and user info

    Raises:
        HTTPException: If authentication fails
    """
    # Verify admin secret first - MUST be set in environment variable
    expected_secret = getattr(config, "ADMIN_SECRET", None)

    if not expected_secret:
        logger.error("ADMIN_SECRET not configured - admin authentication disabled")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin authentication not configured",
        )

    if not secrets.compare_digest(request.admin_secret, expected_secret):
        logger.warning(f"Invalid admin secret attempt for email: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin credentials"
        )

    # Get user from database
    user = await UserOperations.get_user_by_email(db, request.email)

    if not user:
        logger.warning(f"Admin login attempt for non-existent user: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin credentials"
        )

    # Verify password
    if not verify_password(request.password, user.password_hash):
        logger.warning(f"Invalid password for admin login: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin credentials"
        )

    # Verify admin status
    if not user.is_admin:
        logger.warning(f"Non-admin user attempted admin login: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )

    # Create admin tokens with shorter expiry
    access_token_data: Dict[str, Union[str, int, bool, datetime]] = {
        "sub": user.user_id,
        "email": user.email,
        "is_admin": True,
        "admin_session": True,
        "exp": datetime.now(timezone.utc)
        + timedelta(hours=2),  # 2 hour expiry for admin
    }

    refresh_token_data: Dict[str, Union[str, int, bool, datetime]] = {
        "sub": user.user_id,
        "email": user.email,
        "is_admin": True,
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(hours=4),  # 4 hour refresh token
    }

    access_token = create_access_token(access_token_data)  # type: ignore[arg-type]
    refresh_token = create_refresh_token(refresh_token_data)  # type: ignore[arg-type]

    # Update last login
    await UserOperations.update_last_login(db, user.user_id)

    logger.info(f"Admin login successful for: {user.email}")

    return AdminAuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        email=user.email,
        expires_in=7200,
    )
