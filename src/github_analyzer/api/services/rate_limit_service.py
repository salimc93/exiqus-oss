# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Rate limiting service using Redis-based semaphores.

This service implements concurrent request limiting to protect the API
from abuse and control resource usage.
"""

import asyncio
import time
from typing import Any, Dict, Optional

from ...utils.config import get_config
from ...utils.logging import get_logger

logger = get_logger(__name__)


class RateLimitService:
    """Service for managing concurrent request limits using Redis."""

    def __init__(self, redis_service: Any) -> None:
        """
        Initialize rate limit service.

        Args:
            redis_service: RedisService instance for distributed locking
        """
        self.redis = redis_service
        self.config = get_config()
        self._local_locks: Dict[str, Any] = {}  # Local asyncio locks for coordination

    async def acquire_user_limit(self, user_id: str, timeout: float = 5.0) -> bool:
        """
        Try to acquire a slot for user-specific concurrent requests.

        Args:
            user_id: User identifier
            timeout: Maximum time to wait for a slot (seconds)

        Returns:
            bool: True if slot acquired, False if limit exceeded
        """
        key = f"rate_limit:user:{user_id}"
        max_concurrent = self.config.analysis.max_concurrent_per_user

        return await self._acquire_semaphore(key, max_concurrent, timeout)

    async def release_user_limit(self, user_id: str) -> None:
        """
        Release a user's concurrent request slot.

        Args:
            user_id: User identifier
        """
        key = f"rate_limit:user:{user_id}"
        await self._release_semaphore(key)

    async def acquire_global_limit(self, timeout: float = 5.0) -> bool:
        """
        Try to acquire a slot for global concurrent requests.

        Args:
            timeout: Maximum time to wait for a slot (seconds)

        Returns:
            bool: True if slot acquired, False if limit exceeded
        """
        key = "rate_limit:global"
        max_concurrent = self.config.analysis.max_concurrent_global

        return await self._acquire_semaphore(key, max_concurrent, timeout)

    async def release_global_limit(self) -> None:
        """Release a global concurrent request slot."""
        key = "rate_limit:global"
        await self._release_semaphore(key)

    async def _acquire_semaphore(
        self, key: str, max_count: int, timeout: float
    ) -> bool:
        """
        Acquire a semaphore slot using Redis.

        Args:
            key: Redis key for the semaphore
            max_count: Maximum allowed concurrent operations
            timeout: Maximum time to wait

        Returns:
            bool: True if acquired, False if limit exceeded
        """
        start_time = time.time()

        while (time.time() - start_time) < timeout:
            try:
                # Get current count
                current = await self.redis.get(key)
                current_count = int(current) if current else 0

                if current_count < max_count:
                    # Try to increment atomically
                    new_count = await self.redis.incr(key)

                    if new_count <= max_count:
                        # Successfully acquired
                        # Set expiry to prevent stale counts (10 minutes)
                        await self.redis.expire(key, 600)
                        logger.debug(
                            f"Acquired semaphore {key}: {new_count}/{max_count}"
                        )
                        return True
                    else:
                        # Race condition - someone else got it, decrement back
                        await self.redis.decr(key)

                # Wait before retrying
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Error acquiring semaphore {key}: {e}")
                return False

        logger.warning(f"Timeout acquiring semaphore {key} after {timeout}s")
        return False

    async def _release_semaphore(self, key: str) -> None:
        """
        Release a semaphore slot.

        Args:
            key: Redis key for the semaphore
        """
        try:
            current = await self.redis.decr(key)
            if current < 0:
                # Should not happen, but reset to 0 to be safe
                await self.redis.set(key, "0")
                logger.warning(f"Semaphore {key} went negative, reset to 0")
            else:
                logger.debug(f"Released semaphore {key}: {current} remaining")
        except Exception as e:
            logger.error(f"Error releasing semaphore {key}: {e}")

    async def get_current_usage(self, user_id: Optional[str] = None) -> dict[str, int]:
        """
        Get current usage statistics.

        Args:
            user_id: Optional user ID to get user-specific stats

        Returns:
            dict: Current usage information
        """
        stats = {}

        try:
            # Global usage
            global_key = "rate_limit:global"
            global_count = await self.redis.get(global_key)
            stats["global_concurrent"] = int(global_count) if global_count else 0
            stats["global_limit"] = self.config.analysis.max_concurrent_global

            # User-specific usage
            if user_id:
                user_key = f"rate_limit:user:{user_id}"
                user_count = await self.redis.get(user_key)
                stats["user_concurrent"] = int(user_count) if user_count else 0
                stats["user_limit"] = self.config.analysis.max_concurrent_per_user

        except Exception as e:
            logger.error(f"Error getting usage stats: {e}")

        return stats
