# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Budget monitoring dependencies for API endpoints.

Provides dependency injection for budget monitoring services.
Now returns a wrapper that uses the new CostAnalyticsService for tracking
while maintaining backward compatibility.
"""

import logging
from typing import Optional

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.connection import get_db_session
from ..services.budget_monitor import BudgetMonitor
from ..services.cost_tracking_wrapper import CostTrackingWrapper

logger = logging.getLogger(__name__)

# Global instance for singleton pattern
_budget_monitor: Optional[BudgetMonitor] = None


async def get_budget_monitor(
    db: AsyncSession = Depends(get_db_session),
) -> BudgetMonitor:
    """
    Get budget monitor instance.

    Now returns a CostTrackingWrapper that uses the new analytics service
    while maintaining the BudgetMonitor interface for backward compatibility.

    Returns:
        BudgetMonitor-compatible instance
    """
    from ..services.redis_service import redis_service

    # Return wrapper that uses new analytics service
    wrapper = CostTrackingWrapper(redis_service, db)
    logger.info("Using CostTrackingWrapper for budget monitoring")

    return wrapper


def reset_budget_monitor() -> None:
    """Reset budget monitor instance (for testing)."""
    global _budget_monitor
    _budget_monitor = None
