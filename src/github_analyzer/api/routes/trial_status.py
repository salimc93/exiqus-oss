# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Public route for checking trial status.

This module provides a public endpoint for trial users to check
their current usage and remaining quota.
"""

from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.connection import get_db_session
from ...database.operations import UserOperations
from ..auth.dependencies import get_current_user_id

router = APIRouter(prefix="/trials", tags=["Trial Management"])


class TrialStatusResponse(BaseModel):
    """Response model for trial status."""

    is_trial: bool
    trial_plan: Optional[str]
    analyses_consumed: int
    analyses_limit: Optional[int]
    analyses_remaining: Optional[int]
    trial_end_date: Optional[datetime]
    days_remaining: Optional[int]
    is_expired: bool


@router.get("/status", response_model=TrialStatusResponse)
async def get_trial_status(
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: AsyncSession = Depends(get_db_session),
) -> TrialStatusResponse:
    """
    Get current trial status for authenticated user.

    This endpoint allows users to check:
    - Their trial plan and limits
    - Current usage and remaining analyses
    - Trial expiry date and days remaining

    Args:
        user_id: Authenticated user ID
        db: Database session

    Returns:
        TrialStatusResponse: Current trial status

    Raises:
        HTTPException: If user not found
    """
    user = await UserOperations.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Calculate trial status
    now = datetime.now(timezone.utc)
    is_expired = False
    days_remaining = None
    analyses_remaining = None

    if user.is_trial and user.trial_end_date:
        # Ensure timezone-aware comparison
        trial_end = (
            user.trial_end_date.replace(tzinfo=timezone.utc)
            if user.trial_end_date.tzinfo is None
            else user.trial_end_date
        )
        is_expired = trial_end < now
        if not is_expired:
            days_remaining = (trial_end - now).days

        if user.trial_analyses_limit is not None:
            analyses_remaining = max(
                0, user.trial_analyses_limit - user.analyses_consumed
            )

    return TrialStatusResponse(
        is_trial=user.is_trial,
        trial_plan=user.trial_plan if user.is_trial else None,
        analyses_consumed=user.analyses_consumed,
        analyses_limit=user.trial_analyses_limit,
        analyses_remaining=analyses_remaining,
        trial_end_date=user.trial_end_date,
        days_remaining=days_remaining,
        is_expired=is_expired,
    )
