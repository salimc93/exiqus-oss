# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Candidate context management endpoints.

Provides APIs for retrieving and resetting locked evaluation contexts.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.connection import get_db_session
from ...database.models import User
from ..auth.dependencies import get_current_active_user
from ..services.cache_service import clear_candidate_caches
from ..services.candidate_context import (
    get_locked_context,
    get_most_recent_analysis_context,
    lock_context,
    reset_context,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/candidates", tags=["candidates"])


class CandidateContextResponse(BaseModel):
    """Response model for candidate context."""

    model_config = ConfigDict(from_attributes=True)

    username: str
    role: str
    organization_context: str
    locked_at: str
    locked_by_user_id: str


class ContextResetResponse(BaseModel):
    """Response model for context reset."""

    success: bool
    message: str
    caches_cleared: bool


@router.get("/{username}/context", response_model=CandidateContextResponse)
async def get_candidate_context(
    username: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> CandidateContextResponse:
    """
    Get locked evaluation context for a candidate (for this hiring manager).

    Returns the locked role + organization context if one exists for this user.
    If no lock exists but analyses do, intelligently locks to most recent analysis.

    This helps frontend show what context the candidate is being evaluated under.

    Note: Different hiring managers can have different locked contexts for the same candidate.
    """
    locked = await get_locked_context(db, username, current_user.user_id)

    # If no lock exists, check for existing analyses and auto-lock to most recent
    if not locked:
        recent_context = await get_most_recent_analysis_context(
            db, username, current_user.user_id
        )

        if recent_context:
            role, org_context = recent_context
            logger.info(
                f"Auto-locking @{username} to most recent analysis: {role}/{org_context}"
            )
            locked = await lock_context(
                db, username, role, org_context, current_user.user_id
            )
        else:
            # No analyses exist yet - will lock on first analysis
            raise HTTPException(
                status_code=404,
                detail=f"No locked context for @{username}. "
                f"Context will be locked on first analysis.",
            )

    return CandidateContextResponse(
        username=locked.username,
        role=locked.role,
        organization_context=locked.organization_context,
        locked_at=locked.locked_at.isoformat(),
        locked_by_user_id=locked.locked_by_user_id,
    )


@router.delete("/{username}/context", response_model=ContextResetResponse)
async def reset_candidate_context(
    username: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> ContextResetResponse:
    """
    Reset locked evaluation context for a candidate (for this hiring manager).

    This allows re-evaluation with a different role/org context.
    WARNING: This will clear all cached analyses for this candidate (for this user).

    Use case: User wants to evaluate same candidate for a different role
    (e.g., originally evaluated as Senior/Enterprise, now want Mid/Startup).

    Note: This only resets YOUR locked context. Other hiring managers' contexts
    for this candidate remain unchanged.
    """
    # Reset the locked context for this user+candidate
    was_reset = await reset_context(db, username, current_user.user_id)

    if not was_reset:
        raise HTTPException(
            status_code=404,
            detail=f"No locked context to reset for @{username}.",
        )

    # Clear all caches for this user+candidate
    caches_cleared = await clear_candidate_caches(username, current_user.user_id, db)

    logger.info(
        f"User {current_user.user_id} reset context for @{username}. "
        f"Caches cleared: {caches_cleared}"
    )

    return ContextResetResponse(
        success=True,
        message=(
            f"Context reset for @{username}. "
            f"You can now re-analyze with a different role/org context."
        ),
        caches_cleared=caches_cleared,
    )
