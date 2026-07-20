# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Public route for trial activation.

This module provides the public endpoint for trial users to activate
their accounts using the invite token.
"""

import json
import secrets
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.connection import get_db_session
from ...database.models import AuditLog, User
from ..auth.jwt import create_token_pair, hash_password

router = APIRouter(prefix="/trials", tags=["Trial Management"])


class ActivateTrialRequest(BaseModel):
    """Request model for trial activation."""

    token: str
    password: str
    full_name: str
    company: str


class ActivateTrialResponse(BaseModel):
    """Response model for trial activation."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105 - not a credential
    user: Dict[str, Any]


@router.post("/activate", response_model=ActivateTrialResponse)
async def activate_trial(
    request: ActivateTrialRequest,
    db: AsyncSession = Depends(get_db_session),
) -> ActivateTrialResponse:
    """
    Activate a trial account using invite token.

    This endpoint:
    1. Validates the invite token and checks expiry
    2. Sets the user password and profile information
    3. Activates the account
    4. Returns authentication tokens for immediate login

    Args:
        request: Activation details including token and password
        db: Database session

    Returns:
        ActivateTrialResponse: Auth tokens and user information

    Raises:
        HTTPException: If token is invalid, expired, or already used
    """
    async with db.begin():  # Start transaction
        # Find user by invite token with row lock
        result = await db.execute(
            select(User).where(User.invite_token == request.token).with_for_update()
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid activation token",
            )

        # Check if already activated
        if user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account already activated",
            )

        # Check token expiry
        now = datetime.now(timezone.utc)
        if user.invite_token_expires is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid activation token",
            )

        # Make comparison timezone-aware
        if user.invite_token_expires.replace(tzinfo=timezone.utc) < now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Activation token has expired",
            )

        # Set password and activate account
        user.password_hash = hash_password(request.password)
        user.full_name = request.full_name
        user.company = request.company
        user.is_active = True
        user.invite_token = None  # Clear the token
        user.invite_token_expires = None

        # Create audit log
        audit_log = AuditLog(
            log_id=f"log_{secrets.token_urlsafe(16)}",
            action="trial_activated",
            target_user_id=user.user_id,
            action_metadata=json.dumps(
                {
                    "company": request.company,
                    "trial_plan": user.trial_plan,
                    "activation_date": datetime.now(timezone.utc).isoformat(),
                }
            ),
        )
        db.add(audit_log)

    # Transaction commits here

    # Generate auth tokens
    token_data = create_token_pair(user.user_id, user.email)

    return ActivateTrialResponse(
        access_token=token_data["access_token"],
        refresh_token=token_data["refresh_token"],
        user={
            "user_id": user.user_id,
            "email": user.email,
            "full_name": user.full_name,
            "company": user.company,
            "is_trial": user.is_trial,
            "trial_plan": user.trial_plan,
            "trial_ends_at": (
                user.trial_end_date.isoformat() if user.trial_end_date else None
            ),
            "analyses_limit": user.trial_analyses_limit,
            "analyses_consumed": user.analyses_consumed,
        },
    )
