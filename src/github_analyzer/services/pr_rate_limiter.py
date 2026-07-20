# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
PR Rate Limiter Service.

Implements hourly rate limiting for PR analysis requests per tier.
Works alongside the monthly quota limits.
"""

from typing import Any, Dict, Optional

from ..api.services.redis_service import redis_service
from ..database.models import SubscriptionPlan
from ..utils.logging import get_logger

logger = get_logger(__name__)


class PRRateLimiter:
    """Rate limiting for PR analysis requests."""

    def __init__(self) -> None:
        """Initialize PR rate limiter."""
        self.redis = redis_service

        # Hourly limits per tier (in addition to monthly quotas)
        self.hourly_limits: Dict[SubscriptionPlan, int] = {
            SubscriptionPlan.FREE: 0,  # No access to PR analysis
            SubscriptionPlan.BASIC: 10,  # Starter tier: 10 per hour
            SubscriptionPlan.PROFESSIONAL: 15,  # Growth tier: 15 per hour
            SubscriptionPlan.ENTERPRISE: 20,  # Scale tier: 20 per hour
            SubscriptionPlan.SCALE_PLUS: 25,  # Scale+ tier: 25 per hour
        }

        # Cache TTL in seconds (1 hour)
        self.ttl = 3600

    async def check_limit(
        self, user_id: str, tier: SubscriptionPlan
    ) -> tuple[bool, int, int]:
        """
        Check if user has exceeded hourly rate limit.

        Args:
            user_id: User ID to check
            tier: User's subscription tier

        Returns:
            Tuple of (is_allowed, current_count, limit)
        """
        try:
            # Get hourly limit for tier
            limit = self.hourly_limits.get(tier, 0)

            # No PR access for this tier
            if limit == 0:
                logger.info(
                    f"User {user_id} tier {tier.value} has no PR analysis access"
                )
                return False, 0, 0

            # Build Redis key for hourly rate limiting
            key = f"pr_rate:{user_id}:hour"

            # Increment counter
            count_bytes = await self.redis.incr(key)

            # Parse count - handle both bytes and int returns
            if isinstance(count_bytes, bytes):
                count = int(count_bytes.decode())
            else:
                count = int(count_bytes)

            # Set expiry on first request in the hour
            if count == 1:
                await self.redis.expire(key, self.ttl)
                logger.info(
                    f"Started new hourly rate limit window for user {user_id}: "
                    f"1/{limit}"
                )

            # Check if within limit
            is_allowed = count <= limit

            if not is_allowed:
                logger.warning(
                    f"User {user_id} exceeded hourly rate limit: {count}/{limit}"
                )
            else:
                logger.info(f"User {user_id} within hourly rate limit: {count}/{limit}")

            return is_allowed, count, limit

        except Exception as e:
            logger.error(f"Error checking rate limit for user {user_id}: {e}")
            # On error, allow the request but log it
            return True, 0, limit

    async def get_remaining_time(self, user_id: str) -> Optional[int]:
        """
        Get remaining time in seconds until rate limit resets.

        Args:
            user_id: User ID to check

        Returns:
            Remaining seconds until reset, or None if no limit active
        """
        try:
            # For now, return a default 3600 seconds (1 hour) if rate limit exists
            # This is because RedisService doesn't have a ttl method
            key = f"pr_rate:{user_id}:hour"
            exists = await self.redis.get(key)
            if exists:
                # Return approximate time until reset (assume 1 hour TTL)
                return 3600
            return None

        except Exception as e:
            logger.error(f"Error getting TTL for user {user_id}: {e}")
            return None

    async def reset_limit(self, user_id: str) -> bool:
        """
        Reset rate limit for a user (admin action).

        Args:
            user_id: User ID to reset

        Returns:
            True if reset successful
        """
        try:
            key = f"pr_rate:{user_id}:hour"
            await self.redis.delete(key)
            logger.info(f"Reset rate limit for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error resetting rate limit for user {user_id}: {e}")
            return False

    async def get_usage_stats(
        self, user_id: str, tier: SubscriptionPlan
    ) -> Dict[str, Any]:
        """
        Get current usage statistics for a user.

        Args:
            user_id: User ID to check
            tier: User's subscription tier

        Returns:
            Dictionary with usage stats
        """
        try:
            key = f"pr_rate:{user_id}:hour"

            # Get current count - handle various Redis return types
            count_value = await self.redis.get(key)
            if count_value:
                # Handle bytes
                if isinstance(count_value, bytes):
                    current_count = int(count_value.decode())
                # Handle string (including malformed "b'1'" or 'b"1"' strings)
                elif isinstance(count_value, str):
                    # Remove common malformed prefixes/suffixes
                    cleaned = (
                        count_value.strip()
                        .removeprefix("b'")
                        .removesuffix("'")
                        .removeprefix('b"')
                        .removesuffix('"')
                    )
                    current_count = int(cleaned)
                # Handle int
                else:
                    current_count = int(count_value)
            else:
                current_count = 0

            # Get limit and TTL
            limit = self.hourly_limits.get(tier, 0)
            ttl = await self.get_remaining_time(user_id)

            return {
                "current_hour_usage": current_count,
                "hourly_limit": limit,
                "remaining_this_hour": max(0, limit - current_count),
                "resets_in_seconds": ttl,
                "resets_in_minutes": round(ttl / 60) if ttl else None,
            }

        except Exception as e:
            logger.error(f"Error getting usage stats for user {user_id}: {e}")
            return {
                "current_hour_usage": 0,
                "hourly_limit": self.hourly_limits.get(tier, 0),
                "remaining_this_hour": 0,
                "resets_in_seconds": None,
                "resets_in_minutes": None,
            }


# Initialize rate limiter
pr_rate_limiter = PRRateLimiter()
