# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Cost analytics service for monitoring platform AI API costs.

This service tracks and analyzes AI API costs across all users and tiers,
providing insights into usage patterns, profitability, and cost trends.
Replaces the legacy BudgetMonitor with a focus on analytics over blocking.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import SubscriptionPlan, User
from ...utils.config import get_config
from ..services.redis_service import RedisService

logger = logging.getLogger(__name__)


class CostAnalyticsService:
    """
    Service for tracking and analyzing platform AI API costs.

    Unlike the legacy BudgetMonitor, this service focuses on analytics
    and insights rather than blocking requests. Designed for a v1 product
    with real customers and revenue.
    """

    # Actual model costs per 1K tokens based on Anthropic pricing (in USD)
    # Format: {"model": {"input": cost_per_1k_tokens, "output": cost_per_1k_tokens}}
    MODEL_COSTS = {
        # Haiku models
        "claude-3-haiku-20240307": {
            "input": 0.00025,
            "output": 0.00125,
        },  # $0.25/$1.25 per MTok
        "claude-3-5-haiku-20241022": {
            "input": 0.0008,
            "output": 0.004,
        },  # $0.80/$4 per MTok
        # Sonnet models
        "claude-3-5-sonnet-20241022": {
            "input": 0.003,
            "output": 0.015,
        },  # $3/$15 per MTok
        "claude-3-7-sonnet-20250219": {
            "input": 0.003,
            "output": 0.015,
        },  # $3/$15 per MTok (same as 3.5)
    }

    # Average tokens per analysis type (rough estimates)
    TOKENS_PER_ANALYSIS = {
        "basic": 5000,  # ~5K tokens for basic analysis
        "detailed": 15000,  # ~15K tokens for detailed analysis
        "batch": 3000,  # ~3K tokens per repo in batch (optimized)
    }

    def __init__(self, redis_service: RedisService, db: AsyncSession):
        """Initialize cost analytics service."""
        self.redis = redis_service
        self.db = db
        self.config = get_config()

    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """
        Calculate cost for API usage based on model pricing.

        Args:
            model: Model name used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        if model not in self.MODEL_COSTS:
            logger.warning(f"Unknown model {model}, using default Haiku pricing")
            model_pricing = self.MODEL_COSTS["claude-3-haiku-20240307"]
        else:
            model_pricing = self.MODEL_COSTS[model]

        input_cost = (input_tokens / 1000) * model_pricing["input"]
        output_cost = (output_tokens / 1000) * model_pricing["output"]

        total_cost = input_cost + output_cost
        logger.debug(
            f"Cost calculation: {model} - {input_tokens}+{output_tokens} tokens = ${total_cost:.6f}"
        )

        return total_cost

    async def track_analysis_cost(
        self,
        user_id: str,
        cost_usd: float,
        model: str,
        tokens_used: int,
        analysis_type: str = "basic",
        metadata: Optional[Dict[str, Any]] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
    ) -> None:
        """
        Track cost for an analysis operation.

        Args:
            user_id: User who triggered the analysis
            cost_usd: Actual cost in USD
            model: AI model used
            tokens_used: Number of tokens consumed
            analysis_type: Type of analysis (basic, detailed, batch)
            metadata: Additional metadata (repository, context, etc.)
        """
        try:
            # Get user's subscription plan for tier tracking
            user = await self._get_user(user_id)
            tier = user.subscription_plan.value if user else "unknown"

            # Track overall platform costs
            await self._track_platform_cost(cost_usd)

            # Track per-user costs
            await self._track_user_cost(user_id, cost_usd)

            # Track per-tier costs
            await self._track_tier_cost(tier, cost_usd)

            # Track model usage
            await self._track_model_usage(model, tokens_used, cost_usd)

            # Store detailed analytics data
            await self._store_cost_analytics(
                user_id=user_id,
                tier=tier,
                cost=cost_usd,
                model=model,
                tokens=tokens_used,
                analysis_type=analysis_type,
                metadata=metadata,
            )

            logger.info(
                f"Tracked cost: ${cost_usd:.4f} for user {user_id} "
                f"[tier={tier}, model={model}, tokens={tokens_used}]"
            )

        except Exception as e:
            logger.error(f"Failed to track analysis cost: {e}")
            # Don't fail the request if tracking fails

    async def get_platform_cost_summary(self, days: int = 30) -> Dict[str, Any]:
        """
        Get platform-wide cost summary for admins.

        Returns cost breakdown by tier, model, and trends.
        """
        # Get date range
        end_date = datetime.now(timezone.utc)
        _ = end_date - timedelta(days=days)  # start_date not used

        # Get total costs
        daily_costs = await self._get_daily_platform_costs(days)
        total_cost = sum(cost["amount"] for cost in daily_costs)

        # Get costs by tier
        tier_costs = {}
        for tier in SubscriptionPlan:
            tier_cost = await self._get_tier_total_cost(tier.value, days)
            if tier_cost > 0:
                tier_costs[tier.value] = tier_cost

        # Get costs by model
        model_costs = await self._get_model_costs(days)

        # Calculate daily average and trends
        daily_average = total_cost / days if days > 0 else 0

        # Estimate monthly cost based on daily average
        estimated_monthly = daily_average * 30

        # Get top cost drivers (users)
        top_users = await self._get_top_cost_users(limit=10, days=days)

        return {
            "period_days": days,
            "total_cost": total_cost,
            "daily_average": daily_average,
            "estimated_monthly_cost": estimated_monthly,
            "cost_by_tier": tier_costs,
            "cost_by_model": model_costs,
            "daily_costs": daily_costs,
            "top_cost_users": top_users,
            "cost_trends": {
                "increasing": self._calculate_trend(daily_costs),
                "peak_day": (
                    max(daily_costs, key=lambda x: x["amount"]) if daily_costs else None
                ),
            },
        }

    async def get_tier_analytics(
        self, tier: SubscriptionPlan, days: int = 30
    ) -> Dict[str, Any]:
        """Get detailed analytics for a specific tier."""
        # Get all users in this tier
        users = await self._get_users_by_tier(tier)
        user_count = len(users)

        # Get total cost for tier
        total_cost = await self._get_tier_total_cost(tier.value, days)

        # Calculate per-user average
        avg_cost_per_user = total_cost / user_count if user_count > 0 else 0

        # Get tier pricing
        tier_monthly_price = self._get_tier_price(tier)

        # Calculate margin (simplified - doesn't include other costs)
        monthly_revenue = tier_monthly_price * user_count
        estimated_monthly_cost = (total_cost / days * 30) if days > 0 else 0
        gross_margin = monthly_revenue - estimated_monthly_cost
        margin_percentage = (
            (gross_margin / monthly_revenue * 100) if monthly_revenue > 0 else 0
        )

        # Get usage patterns
        usage_patterns = await self._get_tier_usage_patterns(tier, days)

        return {
            "tier": tier.value,
            "period_days": days,
            "user_count": user_count,
            "total_cost": total_cost,
            "average_cost_per_user": avg_cost_per_user,
            "financial_metrics": {
                "monthly_revenue": monthly_revenue,
                "estimated_monthly_cost": estimated_monthly_cost,
                "gross_margin": gross_margin,
                "margin_percentage": margin_percentage,
            },
            "usage_patterns": usage_patterns,
            "profitability": "profitable" if gross_margin > 0 else "unprofitable",
        }

    async def get_user_cost_analytics(
        self, user_id: str, days: int = 30
    ) -> Dict[str, Any]:
        """Get cost analytics for a specific user."""
        user = await self._get_user(user_id)
        if not user:
            return {"error": "User not found"}

        # Get user's total cost
        total_cost = await self._get_user_total_cost(user_id, days)

        # Get daily breakdown
        daily_costs = await self._get_user_daily_costs(user_id, days)

        # Get model usage
        model_usage = await self._get_user_model_usage(user_id, days)

        # Calculate profitability for this user
        tier_price = self._get_tier_price(user.subscription_plan)
        monthly_cost_estimate = (total_cost / days * 30) if days > 0 else 0
        profit_margin = tier_price - monthly_cost_estimate

        return {
            "user_id": user_id,
            "email": user.email,
            "tier": user.subscription_plan.value,
            "period_days": days,
            "total_cost": total_cost,
            "daily_average": total_cost / days if days > 0 else 0,
            "estimated_monthly_cost": monthly_cost_estimate,
            "subscription_price": tier_price,
            "profit_margin": profit_margin,
            "is_profitable": profit_margin > 0,
            "daily_costs": daily_costs,
            "model_usage": model_usage,
        }

    async def get_cost_anomalies(
        self, threshold_multiplier: float = 2.0
    ) -> List[Dict[str, Any]]:
        """
        Detect cost anomalies (unusual spikes or patterns).

        Args:
            threshold_multiplier: Alert if cost exceeds average by this multiplier

        Returns:
            List of detected anomalies
        """
        anomalies = []

        # Check for daily spikes
        daily_costs = await self._get_daily_platform_costs(days=7)
        if daily_costs:
            avg_daily = sum(c["amount"] for c in daily_costs) / len(daily_costs)

            for day_cost in daily_costs:
                if day_cost["amount"] > avg_daily * threshold_multiplier:
                    anomalies.append(
                        {
                            "type": "daily_spike",
                            "date": day_cost["date"],
                            "amount": day_cost["amount"],
                            "average": avg_daily,
                            "multiplier": day_cost["amount"] / avg_daily,
                            "severity": (
                                "high"
                                if day_cost["amount"] > avg_daily * 3
                                else "medium"
                            ),
                        }
                    )

        # Check for user anomalies
        user_anomalies = await self._detect_user_anomalies(threshold_multiplier)
        anomalies.extend(user_anomalies)

        return sorted(anomalies, key=lambda x: x.get("amount", 0), reverse=True)

    async def estimate_monthly_costs(self) -> Dict[str, Any]:
        """Estimate monthly costs based on current usage patterns."""
        # Get last 7 days average
        recent_costs = await self._get_daily_platform_costs(days=7)
        if not recent_costs:
            return {"error": "No recent cost data"}

        daily_avg = sum(c["amount"] for c in recent_costs) / len(recent_costs)

        # Estimate by tier
        tier_estimates = {}
        for tier in SubscriptionPlan:
            tier_daily = await self._get_tier_daily_average(tier.value, days=7)
            if tier_daily > 0:
                tier_estimates[tier.value] = {
                    "daily_average": tier_daily,
                    "monthly_estimate": tier_daily * 30,
                }

        return {
            "platform_total": {
                "daily_average": daily_avg,
                "monthly_estimate": daily_avg * 30,
                "annual_estimate": daily_avg * 365,
            },
            "by_tier": tier_estimates,
            "based_on_days": 7,
            "calculation_date": datetime.now(timezone.utc).isoformat(),
        }

    # Private helper methods
    async def _get_user(self, user_id: str) -> Optional[User]:
        """Get user from database."""
        result = await self.db.execute(select(User).where(User.user_id == user_id))
        return result.scalar_one_or_none()

    async def _get_users_by_tier(self, tier: SubscriptionPlan) -> List[User]:
        """Get all users in a specific tier."""
        result = await self.db.execute(
            select(User).where(User.subscription_plan == tier)
        )
        return list(result.scalars().all())

    async def _track_platform_cost(self, cost: float) -> None:
        """Track overall platform cost."""
        daily_key = f"cost:platform:daily:{datetime.now(timezone.utc).date()}"
        monthly_key = f"cost:platform:monthly:{self._get_month_key()}"

        await self.redis.incr_by_float(daily_key, cost)
        await self.redis.expire(daily_key, 86400 * 35)  # Keep 35 days

        await self.redis.incr_by_float(monthly_key, cost)
        await self.redis.expire(monthly_key, 86400 * 65)  # Keep 65 days

    async def _track_user_cost(self, user_id: str, cost: float) -> None:
        """Track per-user cost."""
        daily_key = f"cost:user:{user_id}:daily:{datetime.now(timezone.utc).date()}"
        monthly_key = f"cost:user:{user_id}:monthly:{self._get_month_key()}"

        await self.redis.incr_by_float(daily_key, cost)
        await self.redis.expire(daily_key, 86400 * 35)

        await self.redis.incr_by_float(monthly_key, cost)
        await self.redis.expire(monthly_key, 86400 * 65)

    async def _track_tier_cost(self, tier: str, cost: float) -> None:
        """Track per-tier cost."""
        daily_key = f"cost:tier:{tier}:daily:{datetime.now(timezone.utc).date()}"
        monthly_key = f"cost:tier:{tier}:monthly:{self._get_month_key()}"

        await self.redis.incr_by_float(daily_key, cost)
        await self.redis.expire(daily_key, 86400 * 35)

        await self.redis.incr_by_float(monthly_key, cost)
        await self.redis.expire(monthly_key, 86400 * 65)

    async def _track_model_usage(self, model: str, tokens: int, cost: float) -> None:
        """Track model usage statistics."""
        # Track daily model costs
        model_key = f"cost:model:{model}:daily:{datetime.now(timezone.utc).date()}"
        await self.redis.incr_by_float(model_key, cost)
        await self.redis.expire(model_key, 86400 * 35)

        # Track token usage
        token_key = f"tokens:model:{model}:daily:{datetime.now(timezone.utc).date()}"
        await self.redis.incr(token_key)
        await self.redis.expire(token_key, 86400 * 35)

    async def _store_cost_analytics(
        self,
        user_id: str,
        tier: str,
        cost: float,
        model: str,
        tokens: int,
        analysis_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Store detailed cost analytics data."""
        # Create analytics record
        timestamp = datetime.now(timezone.utc).timestamp()

        # Store in sorted set for time-series queries
        analytics_key = f"cost:analytics:{datetime.now(timezone.utc).date()}"
        analytics_data = {
            "timestamp": timestamp,
            "user_id": user_id,
            "tier": tier,
            "cost": cost,
            "model": model,
            "tokens": tokens,
            "analysis_type": analysis_type,
            "metadata": metadata or {},
        }

        # Store as JSON with timestamp as score
        import json

        # For now, just store in a simple key since zadd is not available
        await self.redis.set(
            f"{analytics_key}:{int(timestamp)}", json.dumps(analytics_data)
        )
        await self.redis.expire(f"{analytics_key}:{int(timestamp)}", 86400 * 90)

    async def _get_daily_platform_costs(self, days: int) -> List[Dict[str, Any]]:
        """Get daily platform costs for the specified period."""
        costs = []
        today = datetime.now(timezone.utc).date()

        for i in range(days):
            date = today - timedelta(days=i)
            daily_key = f"cost:platform:daily:{date}"
            cost = await self.redis.get(daily_key)

            costs.append(
                {
                    "date": date.isoformat(),
                    "amount": float(cost) if cost else 0.0,
                }
            )

        # Return in chronological order
        return list(reversed(costs))

    async def _get_tier_total_cost(self, tier: str, days: int) -> float:
        """Get total cost for a tier over specified days."""
        total = 0.0
        today = datetime.now(timezone.utc).date()

        for i in range(days):
            date = today - timedelta(days=i)
            daily_key = f"cost:tier:{tier}:daily:{date}"
            cost = await self.redis.get(daily_key)
            if cost:
                total += float(cost)

        return total

    async def _get_model_costs(self, days: int) -> Dict[str, float]:
        """Get costs broken down by model."""
        model_costs = {}

        for model in self.MODEL_COSTS:
            total = 0.0
            today = datetime.now(timezone.utc).date()

            for i in range(days):
                date = today - timedelta(days=i)
                model_key = f"cost:model:{model}:daily:{date}"
                cost = await self.redis.get(model_key)
                if cost:
                    total += float(cost)

            if total > 0:
                model_costs[model] = total

        return model_costs

    async def _get_top_cost_users(
        self, limit: int = 10, days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get top users by cost."""
        # This would need a more sophisticated approach in production
        # For now, return empty list
        return []

    async def _get_user_total_cost(self, user_id: str, days: int) -> float:
        """Get total cost for a user over specified days."""
        total = 0.0
        today = datetime.now(timezone.utc).date()

        for i in range(days):
            date = today - timedelta(days=i)
            daily_key = f"cost:user:{user_id}:daily:{date}"
            cost = await self.redis.get(daily_key)
            if cost:
                total += float(cost)

        return total

    async def _get_user_daily_costs(
        self, user_id: str, days: int
    ) -> List[Dict[str, Any]]:
        """Get daily costs for a user."""
        costs = []
        today = datetime.now(timezone.utc).date()

        for i in range(days):
            date = today - timedelta(days=i)
            daily_key = f"cost:user:{user_id}:daily:{date}"
            cost = await self.redis.get(daily_key)

            costs.append(
                {
                    "date": date.isoformat(),
                    "amount": float(cost) if cost else 0.0,
                }
            )

        return list(reversed(costs))

    async def _get_user_model_usage(self, user_id: str, days: int) -> Dict[str, Any]:
        """Get model usage for a user."""
        # Simplified implementation
        return {}

    async def _get_tier_usage_patterns(
        self, tier: SubscriptionPlan, days: int
    ) -> Dict[str, Any]:
        """Get usage patterns for a tier."""
        # Simplified implementation
        return {
            "peak_usage_time": "14:00-18:00 UTC",
            "average_analyses_per_user": 0,
            "popular_features": [],
        }

    async def _get_tier_daily_average(self, tier: str, days: int) -> float:
        """Get daily average cost for a tier."""
        total = await self._get_tier_total_cost(tier, days)
        return total / days if days > 0 else 0.0

    async def _detect_user_anomalies(
        self, threshold_multiplier: float
    ) -> List[Dict[str, Any]]:
        """Detect user-level cost anomalies."""
        # Simplified implementation
        return []

    def _calculate_trend(self, daily_costs: List[Dict[str, Any]]) -> str:
        """Calculate if costs are trending up, down, or stable."""
        if len(daily_costs) < 3:
            return "insufficient_data"

        # Simple trend detection
        first_half = daily_costs[: len(daily_costs) // 2]
        second_half = daily_costs[len(daily_costs) // 2 :]

        avg_first = sum(c["amount"] for c in first_half) / len(first_half)
        avg_second = sum(c["amount"] for c in second_half) / len(second_half)

        if avg_second > avg_first * 1.1:
            return "increasing"
        elif avg_second < avg_first * 0.9:
            return "decreasing"
        else:
            return "stable"

    def _get_tier_price(self, tier: SubscriptionPlan) -> float:
        """Get monthly price for a tier."""
        prices = {
            SubscriptionPlan.FREE: 0.0,
            SubscriptionPlan.BASIC: 29.0,
            SubscriptionPlan.PROFESSIONAL: 99.0,
            SubscriptionPlan.ENTERPRISE: 997.0,
            SubscriptionPlan.SCALE_PLUS: 1997.0,
        }
        return prices.get(tier, 0.0)

    def _get_month_key(self) -> str:
        """Get current month key."""
        now = datetime.now(timezone.utc)
        return f"{now.year}-{now.month:02d}"
