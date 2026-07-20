# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Cost analytics dependencies for API endpoints.

Provides dependency injection for cost analytics services.
"""

import logging

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.connection import get_db_session
from .cost_analytics_service import CostAnalyticsService
from .redis_service import RedisService, get_redis_service

logger = logging.getLogger(__name__)


async def get_cost_analytics_service(
    redis: RedisService = Depends(get_redis_service),
    db: AsyncSession = Depends(get_db_session),
) -> CostAnalyticsService:
    """
    Get cost analytics service instance.

    Creates a new instance per request with proper database session.

    Returns:
        CostAnalyticsService instance
    """
    return CostAnalyticsService(redis, db)
