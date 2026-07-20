# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Rate limiting dependencies for FastAPI endpoints.

This module provides decorators and dependencies for enforcing
concurrent request limits on API endpoints.
"""

import functools
from typing import Any, Callable

from fastapi import Depends, HTTPException

from ...utils.logging import get_logger
from ..auth.dependencies import get_current_user_id
from ..dependencies import get_redis_service
from ..services.rate_limit_service import RateLimitService

logger = get_logger(__name__)

# Global rate limit service instance
_rate_limit_service = None


def get_rate_limit_service() -> RateLimitService:
    """Get or create rate limit service instance."""
    global _rate_limit_service
    if _rate_limit_service is None:
        redis_service = get_redis_service()
        _rate_limit_service = RateLimitService(redis_service)
    return _rate_limit_service


class RateLimitContext:
    """Context manager for rate limit acquisition and release."""

    def __init__(self, rate_limit_service: RateLimitService, user_id: str) -> None:
        self.service = rate_limit_service
        self.user_id = user_id
        self.user_acquired = False
        self.global_acquired = False

    async def __aenter__(self) -> "RateLimitContext":
        """Acquire rate limit slots."""
        # Try to acquire user limit first
        self.user_acquired = await self.service.acquire_user_limit(self.user_id)
        if not self.user_acquired:
            usage = await self.service.get_current_usage(self.user_id)
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Too many concurrent requests",
                    "message": f"User concurrent request limit exceeded ({usage.get('user_concurrent', 0)}/{usage.get('user_limit', 3)})",
                    "user_concurrent": usage.get("user_concurrent", 0),
                    "user_limit": usage.get("user_limit", 3),
                },
            )

        # Then try to acquire global limit
        self.global_acquired = await self.service.acquire_global_limit()
        if not self.global_acquired:
            # Release user limit since we can't get global
            await self.service.release_user_limit(self.user_id)
            self.user_acquired = False

            usage = await self.service.get_current_usage()
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "System at capacity",
                    "message": f"System concurrent request limit exceeded ({usage.get('global_concurrent', 0)}/{usage.get('global_limit', 10)})",
                    "global_concurrent": usage.get("global_concurrent", 0),
                    "global_limit": usage.get("global_limit", 10),
                },
            )

        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Release acquired rate limit slots."""
        if self.user_acquired:
            await self.service.release_user_limit(self.user_id)
        if self.global_acquired:
            await self.service.release_global_limit()


async def check_rate_limits(
    user_id: str = Depends(get_current_user_id),
    rate_limit_service: RateLimitService = Depends(get_rate_limit_service),
) -> RateLimitContext:
    """
    Dependency that returns a rate limit context manager.

    Usage:
        async with rate_limits:
            # Your endpoint logic here
            pass

    Args:
        user_id: User ID from authentication
        rate_limit_service: Rate limit service instance

    Returns:
        RateLimitContext: Context manager for rate limiting
    """
    return RateLimitContext(rate_limit_service, user_id)


def with_rate_limit(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator for applying rate limits to an endpoint.

    This is an alternative to using the dependency directly.
    """

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Extract dependencies
        user_id = kwargs.get("user_id")
        if not user_id:
            raise ValueError("Rate limited endpoints must have user_id parameter")

        rate_limit_service = get_rate_limit_service()
        async with RateLimitContext(rate_limit_service, user_id):
            return await func(*args, **kwargs)

    return wrapper
