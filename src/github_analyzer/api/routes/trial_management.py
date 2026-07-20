# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Admin routes for trial management operations.

This module provides admin-only endpoints for managing existing trial accounts,
including listing, viewing, extending, and revoking trial access.
"""

import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.connection import get_db_session
from ...database.models import AuditLog, User
from ...database.operations import UserOperations
from ..auth.dependencies import require_admin

router = APIRouter(prefix="/admin/trials", tags=["Trial Administration"])


class TrialUserInfo(BaseModel):
    """Trial user information."""

    user_id: str
    email: str
    trial_plan: Optional[str]
    trial_end_date: Optional[datetime]
    analyses_consumed: int
    analyses_limit: Optional[int]
    is_active: bool
    invite_token_expires: Optional[datetime]
    created_at: datetime


class ExtendTrialRequest(BaseModel):
    """Request model for extending trial."""

    additional_days: int


class ExtendTrialResponse(BaseModel):
    """Response model for extended trial."""

    user_id: str
    new_expiry: datetime
    total_trial_days: int


@router.get("/list", response_model=List[TrialUserInfo])
async def list_trial_users(
    admin_user_id: Annotated[str, Depends(require_admin)],
    db: AsyncSession = Depends(get_db_session),
    active_only: bool = False,
    include_expired: bool = False,
) -> List[TrialUserInfo]:
    """
    List all trial users with their status.

    Args:
        admin_user_id: Authenticated admin user ID
        db: Database session
        active_only: Only show active trials
        include_expired: Include expired trials

    Returns:
        List[TrialUserInfo]: Trial users information
    """
    query = select(User).where(User.is_trial.is_(True))

    if active_only:
        query = query.where(User.is_active.is_(True))

    if not include_expired:
        query = query.where(User.trial_end_date > datetime.now(timezone.utc))

    result = await db.execute(query)
    trial_users = result.scalars().all()

    return [
        TrialUserInfo(
            user_id=user.user_id,
            email=user.email,
            trial_plan=user.trial_plan,
            trial_end_date=user.trial_end_date,
            analyses_consumed=user.analyses_consumed,
            analyses_limit=user.trial_analyses_limit,
            is_active=user.is_active,
            invite_token_expires=user.invite_token_expires,
            created_at=user.created_at,
        )
        for user in trial_users
    ]


@router.get("/{user_id}", response_model=TrialUserInfo)
async def get_trial_user(
    user_id: str,
    admin_user_id: Annotated[str, Depends(require_admin)],
    db: AsyncSession = Depends(get_db_session),
) -> TrialUserInfo:
    """
    Get specific trial user details.

    Args:
        user_id: Trial user ID
        admin_user_id: Authenticated admin user ID
        db: Database session

    Returns:
        TrialUserInfo: Trial user information

    Raises:
        HTTPException: If user not found or not a trial user
    """
    user = await UserOperations.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not user.is_trial:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a trial user",
        )

    return TrialUserInfo(
        user_id=user.user_id,
        email=user.email,
        trial_plan=user.trial_plan,
        trial_end_date=user.trial_end_date,
        analyses_consumed=user.analyses_consumed,
        analyses_limit=user.trial_analyses_limit,
        is_active=user.is_active,
        invite_token_expires=user.invite_token_expires,
        created_at=user.created_at,
    )


@router.post("/{user_id}/extend", response_model=ExtendTrialResponse)
async def extend_trial(
    user_id: str,
    request: ExtendTrialRequest,
    admin_user_id: Annotated[str, Depends(require_admin)],
    db: AsyncSession = Depends(get_db_session),
) -> ExtendTrialResponse:
    """
    Extend a user's trial period.

    Uses database transaction to ensure atomic update of trial expiry
    and audit logging.

    Args:
        user_id: Trial user ID to extend
        request: Extension details
        admin_user_id: Authenticated admin user ID
        db: Database session

    Returns:
        ExtendTrialResponse: New trial expiry details

    Raises:
        HTTPException: If user not found or not a trial user
    """
    async with db.begin():  # Start transaction
        # Get user with row lock
        result = await db.execute(
            select(User).where(User.user_id == user_id).with_for_update()
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if not user.is_trial:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not a trial user",
            )

        # Calculate new expiry
        if not user.trial_end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Trial end date not set",
            )

        current_expiry = user.trial_end_date
        new_expiry = current_expiry + timedelta(days=request.additional_days)

        # Update user
        user.trial_end_date = new_expiry

        # Create audit log
        audit_log = AuditLog(
            log_id=f"log_{secrets.token_urlsafe(16)}",
            action="trial_extended",
            admin_id=admin_user_id,
            target_user_id=user_id,
            action_metadata=json.dumps(
                {
                    "additional_days": request.additional_days,
                    "old_expiry": current_expiry.isoformat(),
                    "new_expiry": new_expiry.isoformat(),
                }
            ),
        )
        db.add(audit_log)

    # Transaction commits here

    # Calculate total trial days
    total_days = (new_expiry - user.created_at).days

    return ExtendTrialResponse(
        user_id=user_id,
        new_expiry=new_expiry,
        total_trial_days=total_days,
    )


@router.delete("/{user_id}/revoke")
async def revoke_trial(
    user_id: str,
    admin_user_id: Annotated[str, Depends(require_admin)],
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, str]:
    """
    Revoke a user's trial access.

    Immediately expires the trial and deactivates the account.

    Args:
        user_id: Trial user ID to revoke
        admin_user_id: Authenticated admin user ID
        db: Database session

    Returns:
        Dict: Confirmation message

    Raises:
        HTTPException: If user not found or not a trial user
    """
    async with db.begin():
        # Get user with row lock
        result = await db.execute(
            select(User).where(User.user_id == user_id).with_for_update()
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if not user.is_trial:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not a trial user",
            )

        # Revoke trial
        user.trial_end_date = datetime.now(timezone.utc)
        user.is_active = False
        user.invite_token = None
        user.invite_token_expires = None

        # Create audit log
        audit_log = AuditLog(
            log_id=f"log_{secrets.token_urlsafe(16)}",
            action="trial_revoked",
            admin_id=admin_user_id,
            target_user_id=user_id,
            action_metadata=json.dumps(
                {
                    "reason": "Admin revoked",
                    "analyses_consumed": user.analyses_consumed,
                }
            ),
        )
        db.add(audit_log)

    return {"message": f"Trial revoked for user {user_id}"}
