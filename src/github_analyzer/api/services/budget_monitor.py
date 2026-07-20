# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Budget monitoring service for tracking API costs.

This service monitors spending against the initial budget allocation,
providing warnings but not blocking requests. As the business grows
and customers pay, the budget will naturally increase.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from ...utils.config import get_config
from ..services.redis_service import RedisService

logger = logging.getLogger(__name__)


class BudgetMonitor:
    """
    Monitor API spending and provide budget alerts.

    This is a monitoring service, not a strict enforcement mechanism.
    It tracks spending and warns when approaching limits, helping
    manage the initial $15 budget efficiently.
    """

    def __init__(self, redis_service: RedisService):
        """Initialize budget monitor with Redis for tracking."""
        self.redis = redis_service
        self.config = get_config()

    async def track_cost(self, cost_usd: float, user_id: str) -> None:
        """
        Track a cost against the budget.

        Args:
            cost_usd: Cost in USD to track
            user_id: User who incurred the cost
        """
        try:
            # Track daily spending
            daily_key = self._get_daily_key()
            await self.redis.incr_by_float(daily_key, cost_usd)
            await self.redis.expire(daily_key, 86400)  # 24 hours

            # Track monthly spending
            monthly_key = self._get_monthly_key()
            await self.redis.incr_by_float(monthly_key, cost_usd)
            await self.redis.expire(monthly_key, 2592000)  # 30 days

            # Track per-user spending
            user_daily_key = f"budget:user:{user_id}:daily:{self._get_date_key()}"
            await self.redis.incr_by_float(user_daily_key, cost_usd)
            await self.redis.expire(user_daily_key, 86400)

            # Log spending
            logger.info(
                f"Tracked cost: ${cost_usd:.4f} for user {user_id}. "
                f"Daily total: ${await self.get_daily_spending():.4f}"
            )

        except Exception as e:
            logger.error(f"Failed to track cost: {e}")
            # Don't fail the request if tracking fails

    async def check_budget_status(self) -> Dict[str, Any]:
        """
        Check current budget status and return warnings if needed.

        Returns:
            Dict with budget status information
        """
        daily_spent = await self.get_daily_spending()
        monthly_spent = await self.get_monthly_spending()

        # For initial $15 budget, assume roughly $0.50/day sustainable rate
        daily_budget_estimate = 0.50
        monthly_budget_estimate = 15.00

        status: Dict[str, Any] = {
            "daily_spent": daily_spent,
            "monthly_spent": monthly_spent,
            "daily_budget_estimate": daily_budget_estimate,
            "monthly_budget_estimate": monthly_budget_estimate,
            "warnings": [],
        }

        # Check thresholds
        daily_percent = (
            daily_spent / daily_budget_estimate if daily_budget_estimate > 0 else 0
        )
        monthly_percent = (
            monthly_spent / monthly_budget_estimate
            if monthly_budget_estimate > 0
            else 0
        )

        if daily_percent >= self.config.analysis.budget_critical_threshold:
            status["warnings"].append(
                {
                    "level": "critical",
                    "message": (
                        f"Daily spending at {daily_percent:.0%} of sustainable rate"
                    ),
                }
            )
        elif daily_percent >= self.config.analysis.budget_warning_threshold:
            status["warnings"].append(
                {
                    "level": "warning",
                    "message": (
                        f"Daily spending at {daily_percent:.0%} of sustainable rate"
                    ),
                }
            )

        if monthly_percent >= self.config.analysis.budget_critical_threshold:
            status["warnings"].append(
                {
                    "level": "critical",
                    "message": (
                        f"Monthly spending at {monthly_percent:.0%} of initial budget"
                    ),
                }
            )
        elif monthly_percent >= self.config.analysis.budget_warning_threshold:
            status["warnings"].append(
                {
                    "level": "warning",
                    "message": (
                        f"Monthly spending at {monthly_percent:.0%} of initial budget"
                    ),
                }
            )

        return status

    async def should_allow_request(self) -> Tuple[bool, Optional[str]]:
        """
        Check if a request should be allowed based on budget.

        This is lenient - only blocks at extreme levels (>95% of budget).

        Returns:
            Tuple of (allowed, reason_if_blocked)
        """
        status = await self.check_budget_status()

        # Only block if we have critical warnings and are over 95%
        critical_warnings = [w for w in status["warnings"] if w["level"] == "critical"]

        if critical_warnings:
            monthly_percent = (
                status["monthly_spent"] / status["monthly_budget_estimate"]
            )
            if monthly_percent >= 0.95:
                return (
                    False,
                    "Monthly budget nearly exhausted. Please top up to continue.",
                )

        return True, None

    async def get_daily_spending(self) -> float:
        """Get total spending for current day."""
        daily_key = self._get_daily_key()
        value = await self.redis.get(daily_key)
        return float(value) if value else 0.0

    async def get_monthly_spending(self) -> float:
        """Get total spending for current month."""
        monthly_key = self._get_monthly_key()
        value = await self.redis.get(monthly_key)
        return float(value) if value else 0.0

    async def get_user_daily_spending(self, user_id: str) -> float:
        """Get spending for a specific user today."""
        user_key = f"budget:user:{user_id}:daily:{self._get_date_key()}"
        value = await self.redis.get(user_key)
        return float(value) if value else 0.0

    def _get_daily_key(self) -> str:
        """Get Redis key for daily spending."""
        return f"budget:daily:{self._get_date_key()}"

    def _get_monthly_key(self) -> str:
        """Get Redis key for monthly spending."""
        now = datetime.now(timezone.utc)
        return f"budget:monthly:{now.year}-{now.month:02d}"

    def _get_date_key(self) -> str:
        """Get date key for current UTC date."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")
