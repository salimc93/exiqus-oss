# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Cost tracking wrapper to bridge old BudgetMonitor with new CostAnalyticsService.

This provides backward compatibility while transitioning to the new analytics-focused
cost tracking system.
"""

import logging
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from .budget_monitor import BudgetMonitor
from .cost_analytics_service import CostAnalyticsService
from .redis_service import RedisService

logger = logging.getLogger(__name__)


class CostTrackingWrapper(BudgetMonitor):
    """
    Wrapper that extends BudgetMonitor but uses CostAnalyticsService.

    This allows gradual migration from the old budget blocking system to the new
    analytics-focused system while maintaining type compatibility.
    """

    def __init__(
        self,
        redis_service: RedisService,
        db_session: Optional[AsyncSession] = None,
    ):
        """Initialize wrapper with both services."""
        super().__init__(redis_service)
        self.db = db_session
        self.analytics_redis = redis_service

    async def track_cost(
        self,
        cost_usd: float,
        user_id: str,
        model: Optional[str] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
    ) -> None:
        """
        Track cost using the new analytics service.

        This method maintains the BudgetMonitor interface while using
        the new CostAnalyticsService for actual tracking.
        """
        try:
            # If we have a database session, use the new analytics service
            if self.db:
                analytics_service = CostAnalyticsService(self.redis, self.db)

                # Track with enhanced analytics
                await analytics_service.track_analysis_cost(
                    user_id=user_id,
                    cost_usd=cost_usd,
                    model=model
                    or "claude-3-haiku-20240307",  # Use actual model or default
                    tokens_used=(
                        input_tokens + output_tokens
                        if input_tokens and output_tokens
                        else int(cost_usd * 3333)
                    ),
                    analysis_type="basic",
                    metadata={
                        "source": "legacy_wrapper",
                        "migrated": True,
                    },
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )

                logger.info(
                    f"Tracked cost ${cost_usd:.4f} for user {user_id} "
                    "using new CostAnalyticsService"
                )
            else:
                # Fallback to legacy tracking if no DB session
                await super().track_cost(cost_usd, user_id)
                logger.info(
                    f"Tracked cost ${cost_usd:.4f} for user {user_id} "
                    "using legacy BudgetMonitor (no DB session)"
                )

        except Exception as e:
            logger.error(f"Failed to track cost: {e}")
            # Don't fail the request if tracking fails

    async def should_allow_request(self) -> tuple[bool, Optional[str]]:
        """
        Always allow requests - we don't block based on budget anymore.

        This maintains interface compatibility while removing blocking behavior.
        """
        # Always allow - we're past the $15 bootstrap phase
        return True, None

    async def check_budget_status(self) -> dict[str, Any]:
        """
        Get budget status - now returns analytics instead of warnings.
        """
        # Return empty status - real analytics are in the new service
        return {
            "daily_spent": 0.0,
            "monthly_spent": 0.0,
            "warnings": [],
            "note": "Use /api/v1/admin/cost-analytics for detailed analytics",
        }

    async def get_daily_spending(self) -> float:
        """Legacy method - returns 0 as we don't track this way anymore."""
        return 0.0

    async def get_monthly_spending(self) -> float:
        """Legacy method - returns 0 as we don't track this way anymore."""
        return 0.0
