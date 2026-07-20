# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Candidate context locking service.

Ensures consistent role + organization context across all analysis types
(Portfolio, PR, Single Repo) for meaningful intelligence blending.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import CandidateContext, PRAnalysisRecord
from ...database.models_portfolio import PortfolioAnalysis as PortfolioAnalysisModel

logger = logging.getLogger(__name__)


async def get_most_recent_analysis_context(
    db: AsyncSession, username: str, user_id: str
) -> Optional[Tuple[str, str]]:
    """
    Find the most recent analysis context (role, org) for a candidate.

    Checks Portfolio, PR, and Single Repo analyses to find the newest one.
    This is used for intelligent auto-locking when no context exists yet.

    Args:
        db: Database session
        username: GitHub username
        user_id: User ID

    Returns:
        Tuple of (role, organization_context) from most recent analysis,
        or None if no analyses exist
    """
    from ...database.models import AnalysisResult

    # Get most recent portfolio analysis
    portfolio_result = await db.execute(
        select(PortfolioAnalysisModel)
        .where(
            PortfolioAnalysisModel.user_id == user_id,
            PortfolioAnalysisModel.github_username == username,
        )
        .order_by(PortfolioAnalysisModel.created_at.desc())
        .limit(1)
    )
    portfolio = portfolio_result.scalar_one_or_none()

    # Get most recent PR analysis
    pr_result = await db.execute(
        select(PRAnalysisRecord)
        .where(
            PRAnalysisRecord.user_id == user_id,
            PRAnalysisRecord.github_username == username,
        )
        .order_by(PRAnalysisRecord.created_at.desc())
        .limit(1)
    )
    pr = pr_result.scalar_one_or_none()

    # Get most recent single repo analysis
    single_repo_result = await db.execute(
        select(AnalysisResult)
        .where(
            AnalysisResult.user_id == user_id,
            AnalysisResult.repository_name.like(f"{username}/%"),
        )
        .order_by(AnalysisResult.created_at.desc())
        .limit(1)
    )
    single_repo = single_repo_result.scalar_one_or_none()

    # Find the most recent among all three
    candidates = []
    if portfolio:
        candidates.append((portfolio.created_at, portfolio.role, portfolio.context))
    if pr:
        candidates.append((pr.created_at, pr.role, pr.context))
    if (
        single_repo
        and hasattr(single_repo, "role")
        and hasattr(single_repo, "context")
        and single_repo.role is not None
        and single_repo.context is not None
    ):
        candidates.append(
            (single_repo.created_at, single_repo.role, single_repo.context)
        )

    if not candidates:
        return None

    # Sort by created_at (most recent first)
    candidates.sort(key=lambda x: x[0], reverse=True)
    most_recent = candidates[0]

    logger.info(
        f"Found most recent analysis for {username}: "
        f"{most_recent[1]}/{most_recent[2]} from {most_recent[0]}"
    )

    return (most_recent[1], most_recent[2])


class ContextMismatchError(HTTPException):
    """Raised when analysis context doesn't match locked context."""

    def __init__(self, username: str, locked_role: str, locked_org: str):
        detail = (
            f"Context locked for @{username}. "
            f"All analyses must use: {locked_role.title()} | "
            f"{locked_org.title()}. "
            f"Reset context to evaluate for a different role."
        )
        super().__init__(status_code=400, detail=detail)


async def get_locked_context(
    db: AsyncSession, username: str, user_id: str
) -> Optional[CandidateContext]:
    """
    Get locked context for a candidate (for a specific hiring manager).

    Args:
        db: Database session
        username: GitHub username
        user_id: User ID of the hiring manager

    Returns:
        CandidateContext if locked for this user+candidate, None otherwise
    """
    result = await db.execute(
        select(CandidateContext).where(
            CandidateContext.locked_by_user_id == user_id,
            CandidateContext.username == username,
        )
    )
    return result.scalar_one_or_none()


async def lock_context(
    db: AsyncSession,
    username: str,
    role: str,
    organization_context: str,
    user_id: str,
) -> CandidateContext:
    """
    Lock role + org context for a candidate (for a specific hiring manager).

    This is called on the FIRST analysis run for a candidate by this user.
    All subsequent analyses by this user must use the same context.

    Different hiring managers can analyze the same candidate with different contexts.

    Handles race conditions via retry logic.

    Args:
        db: Database session
        username: GitHub username
        role: Role level (junior/mid/senior)
        organization_context: Org context (startup/enterprise)
        user_id: User who is locking the context

    Returns:
        Created CandidateContext
    """
    # Try up to 5 times to handle race conditions
    for attempt in range(5):
        # Check if already locked for this user+candidate
        existing = await get_locked_context(db, username, user_id)
        if existing:
            logger.info(
                f"Context already locked for user {user_id} + @{username}: "
                f"{existing.role}/{existing.organization_context}"
            )
            return existing

        # Create new locked context
        locked = CandidateContext(
            locked_by_user_id=user_id,
            username=username,
            role=role,
            organization_context=organization_context,
            locked_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        db.add(locked)

        try:
            await db.commit()
            await db.refresh(locked)

            logger.info(
                f"Locked context for user {user_id} + @{username}: "
                f"{role}/{organization_context}"
            )
            return locked

        except Exception as e:
            await db.rollback()

            error_str = str(e)
            is_unique_error = (
                "UNIQUE constraint failed" in error_str
                or "duplicate key" in error_str.lower()
            )

            if not is_unique_error:
                # Not a race condition, re-raise immediately
                logger.error(
                    f"Failed to lock context for user {user_id} + @{username}: "
                    f"{error_str}"
                )
                raise

            # Race condition detected - loop will retry
            logger.info(
                f"Race condition on attempt {attempt + 1} for "
                f"user {user_id} + @{username}, will retry"
            )
            # Brief delay to allow other transaction to commit
            await asyncio.sleep(0.001)  # 1ms

    # All retry attempts exhausted - one final fetch attempt
    logger.warning(
        f"All {5} lock attempts failed for user {user_id} + @{username}, final fetch"
    )
    await asyncio.sleep(0.01)  # 10ms for transaction to complete
    existing = await get_locked_context(db, username, user_id)
    if existing:
        logger.info(
            f"Successfully fetched context on final attempt for "
            f"user {user_id} + @{username}"
        )
        return existing

    # Failed completely
    raise RuntimeError(
        f"Failed to lock or fetch context for user {user_id} + @{username} "
        f"after {5} attempts"
    )


async def validate_context(
    db: AsyncSession,
    username: str,
    role: str,
    organization_context: str,
    user_id: str,
) -> Tuple[bool, Optional[CandidateContext]]:
    """
    Validate that analysis context matches locked context (for a specific hiring manager).

    If no context is locked yet for this user+candidate, lock it with the provided values.
    If context is locked, verify the provided values match.

    Different hiring managers can analyze the same candidate with different contexts.

    Args:
        db: Database session
        username: GitHub username
        role: Requested role level
        organization_context: Requested org context
        user_id: User performing the analysis

    Returns:
        Tuple of (is_valid, locked_context)

    Raises:
        ContextMismatchError: If context doesn't match locked values
    """
    locked = await get_locked_context(db, username, user_id)

    # No context locked yet for this user+candidate - lock it now
    if not locked:
        locked = await lock_context(db, username, role, organization_context, user_id)
        return (True, locked)

    # Context is locked - validate match (case-insensitive comparison)
    if (
        locked.role.lower() != role.lower()
        or locked.organization_context.lower() != organization_context.lower()
    ):
        logger.warning(
            f"Context mismatch for user {user_id} + @{username}. "
            f"Locked: {locked.role}/{locked.organization_context}, "
            f"Requested: {role}/{organization_context}"
        )
        raise ContextMismatchError(username, locked.role, locked.organization_context)

    logger.info(
        f"Context validated for user {user_id} + @{username}: "
        f"{role}/{organization_context}"
    )
    return (True, locked)


async def reset_context(db: AsyncSession, username: str, user_id: str) -> bool:
    """
    Reset (delete) locked context for a candidate (for a specific hiring manager).

    This allows re-evaluation with different role/org context.
    NOTE: Cache clearing must be handled separately by the caller.

    Args:
        db: Database session
        username: GitHub username
        user_id: User ID of the hiring manager

    Returns:
        True if context was reset, False if no context was locked
    """
    locked = await get_locked_context(db, username, user_id)

    if not locked:
        logger.info(f"No locked context to reset for user {user_id} + @{username}")
        return False

    await db.delete(locked)
    await db.commit()

    logger.info(
        f"Reset context for user {user_id} + @{username} "
        f"(was: {locked.role}/{locked.organization_context})"
    )

    return True
