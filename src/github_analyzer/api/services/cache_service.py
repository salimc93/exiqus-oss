# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Cache management service for candidate analyses.

Handles clearing of Redis and database caches when candidate context is reset.

Storage + Cache Separation:
- PortfolioAnalysis & PRAnalysisResult: Permanent historical storage (never deleted)
- PortfolioAnalysisCache & PRAnalysisCache: Temporary cache (cleared on reset)
- Benefits: Clean training data, database-level deduplication, race condition protection
"""

import logging
from typing import List

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import PRAnalysisCache, PRAnalysisRecord
from ...database.models_portfolio import PortfolioAnalysisCache
from ...database.rowcount import affected_rows
from .redis_service import redis_service

logger = logging.getLogger(__name__)


async def clear_candidate_caches(username: str, user_id: str, db: AsyncSession) -> bool:
    """
    Clear all cached analyses for a candidate (for a specific hiring manager).

    This is called when resetting candidate context to ensure
    fresh analyses are run with the new context.

    Storage + Cache Separation:
    - Clears CACHE tables only (PortfolioAnalysisCache, PRAnalysisCache)
    - DOES NOT delete STORAGE tables (PortfolioAnalysis, PRAnalysisResult)
    - Historical analyses are preserved for training data
    - PR analysis records (usage tracking) are also cleared

    Clears:
    - Portfolio analysis cache (30 day TTL) - database cache table
    - PR analysis cache (30 day TTL) - database cache table
    - PR analysis records (usage tracking) - database
    - Single repo analysis caches (24 hour TTL) - Redis cached

    Args:
        username: GitHub username
        user_id: User ID of the hiring manager
        db: Database session

    Returns:
        True if caches were cleared successfully
    """
    try:
        # Clear database CACHE tables for this user+candidate
        # Note: We clear by username only (not user_id) since cache is shared

        # 1. Portfolio analysis cache
        portfolio_cache_result = await db.execute(
            delete(PortfolioAnalysisCache).where(
                PortfolioAnalysisCache.github_username == username,
            )
        )
        portfolio_cache_deleted = affected_rows(portfolio_cache_result) or 0

        # 2. PR analysis cache
        pr_cache_result = await db.execute(
            delete(PRAnalysisCache).where(
                PRAnalysisCache.github_username == username,
            )
        )
        pr_cache_deleted = affected_rows(pr_cache_result) or 0

        # 3. PR analysis records (usage tracking) - user-specific
        pr_records_result = await db.execute(
            delete(PRAnalysisRecord).where(
                PRAnalysisRecord.user_id == user_id,
                PRAnalysisRecord.github_username == username,
            )
        )
        pr_records_deleted = affected_rows(pr_records_result) or 0

        await db.commit()

        logger.info(
            f"Cleared database caches for user {user_id} + @{username}: "
            f"{portfolio_cache_deleted} portfolio cache, "
            f"{pr_cache_deleted} PR cache, "
            f"{pr_records_deleted} PR records"
        )

        # Clear Redis caches for single repo analyses
        redis_cleared = 0

        if redis_service.is_connected():
            patterns_to_clear: List[str] = [
                f"analysis:*:{username}/*:*",  # Single repo analyses (owner/repo)
            ]

            for pattern in patterns_to_clear:
                deleted = await redis_service.clear_pattern(pattern)
                redis_cleared += deleted

            logger.info(
                f"Cleared total of {redis_cleared} Redis cache entries for "
                f"user {user_id} + @{username}"
            )
        else:
            logger.warning("Redis unavailable - skipped Redis cache clearing")

        return True

    except Exception as e:
        logger.error(
            f"Error clearing caches for user {user_id} + @{username}: {e}",
            exc_info=True,
        )
        await db.rollback()
        return False
