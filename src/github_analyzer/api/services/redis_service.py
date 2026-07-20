# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Redis service for caching and rate limiting.

This module provides Redis connection management and caching operations
for the FastAPI application with smart cache strategies.
"""

import hashlib
from typing import Any, Dict, Optional

import redis.asyncio as redis
from redis.asyncio.retry import Retry
from redis.backoff import ExponentialBackoff
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError
from redis.exceptions import TimeoutError as RedisTimeoutError

from ...utils.config import get_config
from ...utils.logging import get_logger

logger = get_logger(__name__)
config = get_config()


class RedisService:
    """
    Redis service for caching and rate limiting operations.

    Provides smart caching with TTL management, rate limiting,
    and graceful fallback when Redis is unavailable.
    """

    def __init__(self) -> None:
        """Initialize Redis service with connection pool."""
        self._redis: Optional[redis.Redis] = None
        self._connection_pool: Optional[redis.ConnectionPool] = None
        self._connected = False

    async def connect(self) -> None:
        """
        Establish Redis connection with error handling.

        Creates connection pool with health checks and retry mechanism.
        Gracefully handles Redis unavailability.
        """
        try:
            # Redis configuration from environment
            redis_url = getattr(config, "REDIS_URL", "redis://localhost:6379/0")

            # Retry strategy: 3 retries with exponential backoff
            retry = Retry(ExponentialBackoff(), 3)

            # Create connection pool with health checks
            self._connection_pool = redis.ConnectionPool.from_url(
                redis_url,
                max_connections=20,
                retry_on_timeout=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                # Health check: ping before each operation if idle > 30s
                health_check_interval=30,
            )

            # Create Redis client with retry on connection errors
            self._redis = redis.Redis(
                connection_pool=self._connection_pool,
                decode_responses=True,
                retry=retry,
                retry_on_error=[RedisConnectionError, RedisTimeoutError, OSError],
            )

            # Test connection
            await self._redis.ping()
            self._connected = True

            logger.info("Redis connected successfully with health checks enabled")

        except RedisError as e:
            logger.warning(f"Redis connection failed: {e}. Operating without cache.")
            self._connected = False
        except Exception as e:
            logger.warning(f"Unexpected Redis error: {e}. Operating without cache.")
            self._connected = False

    async def disconnect(self) -> None:
        """Close Redis connections gracefully."""
        if self._redis:
            await self._redis.aclose()
        if self._connection_pool:
            await self._connection_pool.aclose()

        self._connected = False
        logger.info("Redis disconnected")

    def is_connected(self) -> bool:
        """Check if Redis is connected and available."""
        return self._connected

    async def get(self, key: str) -> Optional[str]:
        """
        Get value from Redis cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/unavailable
        """
        if not self._connected or not self._redis:
            return None

        try:
            value = await self._redis.get(key)
            if value:
                logger.debug(f"Cache hit: {key}")
            return str(value) if value is not None else None

        except RedisError as e:
            logger.warning(f"Redis get error for key {key}: {e}")
            return None

    async def set(self, key: str, value: str, ttl: int = 3600) -> bool:
        """
        Set value in Redis cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default: 1 hour)

        Returns:
            True if successful, False otherwise
        """
        if not self._connected or not self._redis:
            return False

        try:
            await self._redis.setex(key, ttl, value)
            logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
            return True

        except RedisError as e:
            logger.warning(f"Redis set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete key from Redis cache.

        Args:
            key: Cache key to delete

        Returns:
            True if successful, False otherwise
        """
        if not self._connected or not self._redis:
            return False

        try:
            result = await self._redis.delete(key)
            logger.debug(f"Cache delete: {key}")
            return bool(result)

        except RedisError as e:
            logger.warning(f"Redis delete error for key {key}: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """
        Clear multiple keys matching a pattern.

        Args:
            pattern: Redis pattern (e.g., "analysis:*")

        Returns:
            Number of keys deleted
        """
        if not self._connected or not self._redis:
            return 0

        try:
            keys = await self._redis.keys(pattern)
            if keys:
                deleted = await self._redis.delete(*keys)
                logger.info(f"Cache cleared: {deleted} keys matching '{pattern}'")
                return int(deleted)
            return 0

        except RedisError as e:
            logger.warning(f"Redis clear pattern error for '{pattern}': {e}")
            return 0

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get Redis cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        if not self._connected or not self._redis:
            return {
                "connected": False,
                "total_keys": 0,
                "memory_usage": 0,
                "hit_rate": 0.0,
            }

        try:
            info = await self._redis.info()
            keyspace = await self._redis.info("keyspace")

            # Extract stats
            total_keys = 0
            if "db0" in keyspace:
                db_info = keyspace["db0"]
                if "keys" in db_info:
                    total_keys = db_info["keys"]

            return {
                "connected": True,
                "total_keys": total_keys,
                "memory_usage": info.get("used_memory", 0),
                "hit_rate": self._calculate_hit_rate(info),
                "version": info.get("redis_version", "unknown"),
                "uptime": info.get("uptime_in_seconds", 0),
            }

        except RedisError as e:
            logger.warning(f"Redis stats error: {e}")
            return {
                "connected": False,
                "error": str(e),
                "total_keys": 0,
                "memory_usage": 0,
                "hit_rate": 0.0,
            }

    def _calculate_hit_rate(self, info: Dict[str, Any]) -> float:
        """Calculate cache hit rate from Redis info."""
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)

        if hits + misses == 0:
            return 0.0

        return float((hits / (hits + misses)) * 100)

    async def increment_rate_limit(
        self, key: str, window_seconds: int = 60, limit: int = 60
    ) -> tuple[int, bool]:
        """
        Increment rate limit counter.

        Args:
            key: Rate limit key (e.g., "rate_limit:192.168.1.1")
            window_seconds: Time window in seconds
            limit: Maximum requests in window

        Returns:
            Tuple of (current_count, is_allowed)
        """
        if not self._connected or not self._redis:
            # If Redis unavailable, allow all requests
            return 1, True

        try:
            # Use pipeline for atomic operations
            async with self._redis.pipeline() as pipe:
                await pipe.incr(key)
                await pipe.expire(key, window_seconds)
                results = await pipe.execute()

            current_count = results[0]
            is_allowed = current_count <= limit

            if not is_allowed:
                logger.warning(f"Rate limit exceeded: {key} ({current_count}/{limit})")

            return current_count, is_allowed

        except RedisError as e:
            logger.warning(f"Rate limit Redis error for {key}: {e}")
            # Default to allowing request if Redis fails
            return 1, True
        except (TypeError, OSError, ConnectionError) as e:
            # Catch transport/connection errors when connection is broken
            logger.error(f"Rate limit connection error for {key}: {e}")
            self._connected = False
            return 1, True
        except Exception as e:
            # Catch any unexpected errors to prevent middleware crash
            logger.error(f"Rate limit unexpected error for {key}: {e}")
            return 1, True

    async def decrement_rate_limit(self, key: str) -> bool:
        """
        Decrement rate limit counter (e.g., for failed requests that shouldn't count).

        Args:
            key: Rate limit key

        Returns:
            True if decremented successfully
        """
        if not self._connected or not self._redis:
            return False

        try:
            current = await self._redis.get(key)
            if current and int(current) > 0:
                await self._redis.decr(key)
                logger.info(f"Decremented rate limit for {key}")
                return True
            return False
        except RedisError as e:
            logger.error(f"Error decrementing rate limit for {key}: {e}")
            return False

    async def incr(self, key: str) -> int:
        """
        Increment a counter in Redis.

        Args:
            key: Counter key

        Returns:
            New counter value
        """
        if not self._connected or not self._redis:
            return 0

        try:
            result = await self._redis.incr(key)
            return int(result)
        except RedisError as e:
            logger.warning(f"Redis incr error for {key}: {e}")
            return 0

    async def incr_by_float(self, key: str, amount: float) -> float:
        """
        Increment a float value in Redis.

        Args:
            key: Counter key
            amount: Amount to increment by

        Returns:
            New counter value
        """
        if not self._connected or not self._redis:
            return 0.0

        try:
            result = await self._redis.incrbyfloat(key, amount)
            return float(result)
        except RedisError as e:
            logger.warning(f"Redis incrbyfloat error for {key}: {e}")
            return 0.0

    async def decr(self, key: str) -> int:
        """
        Decrement a counter in Redis.

        Args:
            key: Counter key

        Returns:
            New counter value
        """
        if not self._connected or not self._redis:
            return 0

        try:
            result = await self._redis.decr(key)
            return int(result)
        except RedisError as e:
            logger.warning(f"Redis decr error for {key}: {e}")
            return 0

    async def expire(self, key: str, ttl: int) -> bool:
        """
        Set expiration on a key.

        Args:
            key: Redis key
            ttl: Time to live in seconds

        Returns:
            True if expiration was set
        """
        if not self._connected or not self._redis:
            return False

        try:
            result = await self._redis.expire(key, ttl)
            return bool(result)
        except RedisError as e:
            logger.warning(f"Redis expire error for {key}: {e}")
            return False

    async def zcount(self, key: str, min_score: float, max_score: float) -> int:
        """
        Count members in a sorted set within score range.

        Args:
            key: Sorted set key
            min_score: Minimum score (inclusive)
            max_score: Maximum score (inclusive)

        Returns:
            Number of elements with scores in the given range
        """
        if not self._connected or not self._redis:
            logger.warning("Redis not connected, zcount returning 0")
            return 0

        try:
            result = await self._redis.zcount(key, min_score, max_score)
            return int(result) if result is not None else 0
        except RedisError as e:
            logger.warning(f"Redis zcount error for {key}: {e}")
            return 0


# Global Redis service instance
redis_service = RedisService()


def generate_analysis_cache_key(
    repository_url: str, context: str = "general", role: str = "senior"
) -> str:
    """
    Generate cache key for analysis results.

    Args:
        repository_url: Repository URL
        context: Analysis context
        role: Role level for interview questions (junior, mid, senior)

    Returns:
        Cache key string
    """
    content = f"analysis:{repository_url}:{context}:{role}"
    cache_hash = hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()
    return f"analysis:{cache_hash}"


def generate_rate_limit_key(client_ip: str, endpoint: str = "global") -> str:
    """
    Generate rate limit key.

    Args:
        client_ip: Client IP address
        endpoint: Endpoint identifier

    Returns:
        Rate limit key string
    """
    return f"rate_limit:{endpoint}:{client_ip}"


async def get_redis_service() -> RedisService:
    """
    Dependency to get Redis service instance.

    Returns:
        Redis service instance
    """
    return redis_service
