# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Tier-based rate limiting with API overload protection.

This module provides enhanced rate limiting that considers:
1. Subscription tier limits
2. API provider rate limits (Anthropic)
3. Batch processing for GROWTH/SCALE tiers
4. Graceful degradation during overload
"""

import time
from typing import Any, Dict, List, Optional, Tuple

from ...core.tier_config import get_tier_config
from ...database.models import SubscriptionPlan
from ...utils.logging import get_logger

logger = get_logger(__name__)


class TierRateLimiter:
    """Enhanced rate limiter with tier-specific limits and API protection."""

    def _get_tier_limits(self, plan: SubscriptionPlan) -> Dict[str, Any]:
        """Get rate limits based on tier configuration."""
        # Map subscription plan to tier name
        tier_map = {
            SubscriptionPlan.FREE: "free",
            SubscriptionPlan.BASIC: "basic",
            SubscriptionPlan.PROFESSIONAL: "professional",
            SubscriptionPlan.ENTERPRISE: "enterprise",
            SubscriptionPlan.SCALE_PLUS: "scale_plus",
        }

        tier_name = tier_map.get(plan, "free")
        tier_config = get_tier_config(tier_name)

        if not tier_config:
            # Fallback to conservative defaults
            return {
                "concurrent_requests": 1,
                "requests_per_minute": 1,
                "requests_per_hour": 5,
                "requests_per_day": 5,
                "monthly_quota": 10,
                "batch_size": 1,
                "api_calls_per_minute": 5,
            }

        # Build rate limits from tier configuration
        batch_size = tier_config.features.get("batch_analysis", 1)

        # Calculate reasonable rate limits based on monthly quota
        monthly_quota = tier_config.analyses_per_month
        # Ensure at least 1 for FREE tier which has low monthly quota
        daily_limit = max(
            1, min(monthly_quota // 30, 200)
        )  # Cap daily at 200 for safety
        hourly_limit = max(
            1 if tier_name == "free" else 5, min(daily_limit // 10, 100)
        )  # Spread throughout day

        return {
            "concurrent_requests": (
                1
                if tier_name == "free"
                else (
                    2
                    if tier_name in ["basic", "professional"]
                    else (3 if tier_name == "enterprise" else 5)
                )
            ),
            "requests_per_minute": (
                1
                if tier_name == "free"
                else (
                    2
                    if tier_name == "basic"
                    else (
                        5
                        if tier_name == "professional"
                        else (10 if tier_name == "enterprise" else 20)
                    )
                )
            ),
            "requests_per_hour": hourly_limit,
            "requests_per_day": daily_limit,
            "monthly_quota": monthly_quota,
            "batch_size": batch_size,
            "api_calls_per_minute": (
                5
                if tier_name == "free"
                else (
                    10
                    if tier_name == "basic"
                    else (
                        20
                        if tier_name == "professional"
                        else (30 if tier_name == "enterprise" else 50)
                    )
                )
            ),
            "max_batches_per_hour": (
                6
                if tier_name == "professional"
                else (
                    4
                    if tier_name == "enterprise"
                    else (8 if tier_name == "scale_plus" else 1)
                )
            ),
            "cooldown_between_batches": (
                30 if tier_name in ["professional", "scale_plus"] else 60
            ),
            "daily_cost_limit": 100 if tier_name == "scale_plus" else None,
        }

    # API provider limits (Anthropic)
    API_LIMITS = {
        "claude-3-haiku-20240307": {  # Haiku 3.0
            "requests_per_minute": 50,
            "tokens_per_minute": 50000,
            "concurrent_requests": 10,
        },
        "claude-3-5-haiku-20241022": {  # Haiku 3.5
            "requests_per_minute": 50,
            "tokens_per_minute": 50000,
            "concurrent_requests": 10,
        },
        "claude-3-5-sonnet-20241022": {  # Sonnet 3.5
            "requests_per_minute": 50,
            "tokens_per_minute": 40000,
            "concurrent_requests": 8,
        },
    }

    def __init__(self, redis_service: Any) -> None:
        """Initialize tier-based rate limiter."""
        self.redis = redis_service
        self._request_history: Dict[str, List[float]] = {}
        self._api_request_history: Dict[str, List[float]] = {}

    async def check_rate_limit(
        self,
        user_id: str,
        subscription_plan: SubscriptionPlan,
        is_batch: bool = False,
        batch_size: int = 1,
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Check if request should be allowed based on tier limits.

        Returns:
            Tuple of (allowed, error_message, retry_info)
        """
        limits = self._get_tier_limits(subscription_plan)

        # Check batch support
        if is_batch and batch_size > limits["batch_size"]:
            return (
                False,
                (
                    f"Batch size {batch_size} exceeds limit of {limits['batch_size']} "
                    f"for {subscription_plan.value} plan"
                ),
                None,
            )

        # Check concurrent requests
        concurrent_key = f"rate_limit:concurrent:{user_id}"
        current_concurrent = await self._get_counter(concurrent_key)

        if current_concurrent >= limits["concurrent_requests"]:
            return (
                False,
                (
                    f"Concurrent request limit ({limits['concurrent_requests']}) exceeded"
                ),
                {"retry_after": 5},
            )

        # Check requests per minute
        rpm_key = f"rate_limit:rpm:{user_id}"
        current_rpm = await self._get_sliding_window_count(rpm_key, 60)

        if current_rpm >= limits["requests_per_minute"]:
            retry_after = 60 - (int(time.time()) % 60)  # Seconds until next minute
            return (
                False,
                (
                    f"Rate limit exceeded: {limits['requests_per_minute']} requests per minute"
                ),
                {"retry_after": retry_after},
            )

        # Check requests per hour (additional protection)
        rph_key = f"rate_limit:rph:{user_id}"
        current_rph = await self._get_sliding_window_count(rph_key, 3600)

        if current_rph >= limits.get("requests_per_hour", 1000):
            retry_after = 3600 - (int(time.time()) % 3600)  # Seconds until next hour
            return (
                False,
                (
                    f"Hourly rate limit exceeded: {limits.get('requests_per_hour')} requests per hour"
                ),
                {"retry_after": retry_after},
            )

        # Check API limits based on tier
        api_check = await self._check_api_limits(subscription_plan, batch_size)
        if not api_check[0]:
            return api_check

        return True, None, None

    async def _check_api_limits(
        self, subscription_plan: SubscriptionPlan, batch_size: int
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Check if we're within API provider limits."""
        # Estimate API calls based on tier
        if subscription_plan == SubscriptionPlan.SCALE_PLUS:
            # SCALE+ tier: Premium access with Sonnet 3.5 + Haiku 3.5
            models = ["claude-3-5-haiku-20241022", "claude-3-5-sonnet-20241022"]
            api_calls_per_request = 5  # Enhanced analysis with more API calls
        elif subscription_plan == SubscriptionPlan.ENTERPRISE:
            # SCALE tier: Haiku 3.5 + Sonnet 3.5
            models = ["claude-3-5-haiku-20241022", "claude-3-5-sonnet-20241022"]
            api_calls_per_request = 4  # Evidence + metrics + questions + report
        elif subscription_plan == SubscriptionPlan.PROFESSIONAL:
            # GROWTH tier: Haiku 3.0 + Haiku 3.5
            models = ["claude-3-haiku-20240307", "claude-3-5-haiku-20241022"]
            api_calls_per_request = 3
        else:
            # FREE/BASIC: Haiku 3.0 only
            models = ["claude-3-haiku-20240307"]
            api_calls_per_request = 2

        total_api_calls = api_calls_per_request * batch_size

        # Check each model's limits
        for model in models:
            model_limits = self.API_LIMITS.get(model, {})
            rpm_key = f"api_limit:rpm:{model}"
            current_rpm = await self._get_sliding_window_count(rpm_key, 60)

            if current_rpm + total_api_calls > model_limits.get(
                "requests_per_minute", 50
            ):
                retry_after = self._calculate_retry_after(
                    current_rpm, model_limits["requests_per_minute"]
                )
                return (
                    False,
                    (
                        f"API rate limit approaching for {model}. Please wait {retry_after} seconds."
                    ),
                    {"retry_after": retry_after, "reason": "api_limit"},
                )

        return True, None, None

    async def acquire_rate_limit(
        self, user_id: str, subscription_plan: SubscriptionPlan, batch_size: int = 1
    ) -> bool:
        """Acquire rate limit slots for request."""
        # Increment concurrent counter
        concurrent_key = f"rate_limit:concurrent:{user_id}"
        await self._increment_counter(concurrent_key)

        # Record request in sliding windows (both minute and hour)
        rpm_key = f"rate_limit:rpm:{user_id}"
        rph_key = f"rate_limit:rph:{user_id}"
        current_time = time.time()
        await self._add_to_sliding_window(rpm_key, current_time)
        await self._add_to_sliding_window(rph_key, current_time)

        # Record API calls
        if subscription_plan == SubscriptionPlan.ENTERPRISE:
            models = ["claude-3-5-haiku-20241022", "claude-3-5-sonnet-20241022"]
        elif subscription_plan == SubscriptionPlan.PROFESSIONAL:
            models = ["claude-3-haiku-20240307", "claude-3-5-haiku-20241022"]
        else:
            models = ["claude-3-haiku-20240307"]

        for model in models:
            api_key = f"api_limit:rpm:{model}"
            # Add estimated API calls
            for _ in range(batch_size * 2):  # Conservative estimate
                await self._add_to_sliding_window(api_key, time.time())

        return True

    async def release_rate_limit(self, user_id: str) -> None:
        """Release rate limit slots after request completion."""
        concurrent_key = f"rate_limit:concurrent:{user_id}"
        await self._decrement_counter(concurrent_key)

    async def handle_api_overload(self, error_message: str) -> Dict[str, Any]:
        """
        Handle API overload errors with intelligent backoff.

        Returns:
            Dict with retry strategy
        """
        if "overloaded" in error_message.lower():
            # Anthropic is overloaded, back off significantly
            logger.warning("API overload detected, implementing backoff strategy")

            # Reduce all API limits temporarily
            backoff_key = "api_limit:backoff:active"
            await self.redis.set(backoff_key, "1", expire=300)  # 5 minute backoff

            return {
                "retry_after": 30,  # Wait 30 seconds
                "reduce_batch_size": True,
                "use_fallback_model": True,  # Consider using Haiku 3.0 instead of 3.5
                "message": "API is currently overloaded. Implementing automatic backoff.",
            }

        return {"retry_after": 5}

    async def get_usage_stats(self, user_id: str) -> Dict[str, Any]:
        """Get current usage statistics for user."""
        concurrent_key = f"rate_limit:concurrent:{user_id}"
        rpm_key = f"rate_limit:rpm:{user_id}"

        current_concurrent = await self._get_counter(concurrent_key)
        current_rpm = await self._get_sliding_window_count(rpm_key, 60)

        # Check if in backoff mode
        backoff_active = await self.redis.get("api_limit:backoff:active")

        return {
            "concurrent_requests": current_concurrent,
            "requests_per_minute": current_rpm,
            "in_backoff_mode": bool(backoff_active),
            "api_health": "degraded" if backoff_active else "healthy",
        }

    # Helper methods
    async def _get_counter(self, key: str) -> int:
        """Get current counter value."""
        try:
            if not hasattr(self.redis, "is_connected") or not self.redis.is_connected():
                return 0
            value = await self.redis.get(key)
            return int(value) if value else 0
        except Exception as e:
            logger.warning(f"Redis error getting counter {key}: {e}")
            return 0

    async def _increment_counter(self, key: str) -> int:
        """Increment counter with expiry."""
        try:
            if not hasattr(self.redis, "is_connected") or not self.redis.is_connected():
                return 0
            result = await self.redis.incr(key, expire=3600)  # 1 hour expiry
            return int(result) if result is not None else 0
        except Exception as e:
            logger.warning(f"Redis error incrementing counter {key}: {e}")
            return 0

    async def _decrement_counter(self, key: str) -> int:
        """Decrement counter (min 0)."""
        try:
            if not hasattr(self.redis, "is_connected") or not self.redis.is_connected():
                return 0
            current = await self._get_counter(key)
            if current > 0:
                result = await self.redis.decr(key)
                return int(result) if result is not None else 0
            return 0
        except Exception as e:
            logger.warning(f"Redis error decrementing counter {key}: {e}")
            return 0

    async def _add_to_sliding_window(self, key: str, timestamp: float) -> None:
        """Add timestamp to sliding window."""
        try:
            if not hasattr(self.redis, "is_connected") or not self.redis.is_connected():
                return
            # Use Redis sorted set for sliding window
            await self.redis.zadd(key, {str(timestamp): timestamp})
            # Remove old entries (older than window)
            await self.redis.zremrangebyscore(key, 0, timestamp - 60)
            # Set expiry
            await self.redis.expire(key, 120)  # 2 minutes
        except Exception as e:
            logger.warning(f"Redis error adding to sliding window {key}: {e}")

    async def _get_sliding_window_count(self, key: str, window_seconds: int) -> int:
        """Get count of events in sliding window."""
        try:
            if not hasattr(self.redis, "is_connected") or not self.redis.is_connected():
                return 0
            current_time = time.time()
            count = await self.redis.zcount(
                key, current_time - window_seconds, current_time
            )
            return count or 0
        except Exception as e:
            logger.warning(f"Redis error getting sliding window count {key}: {e}")
            return 0

    def _calculate_retry_after(self, current_count: int, limit: int) -> int:
        """Calculate intelligent retry delay."""
        if current_count >= limit * 0.9:  # 90% of limit
            return 30  # Wait 30 seconds
        elif current_count >= limit * 0.8:  # 80% of limit
            return 15  # Wait 15 seconds
        else:
            return 5  # Wait 5 seconds
