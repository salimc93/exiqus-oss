"""
Tests for Redis service functionality.

Tests Redis connection, caching, rate limiting, and error handling.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from github_analyzer.api.services.redis_service import (
    RedisService,
    generate_analysis_cache_key,
    generate_rate_limit_key,
    get_redis_service,
    redis_service,
)


class TestRedisService:
    """Test cases for Redis service."""

    @pytest.fixture
    def redis_mock(self):
        """Mock Redis client."""
        mock = AsyncMock()
        mock.ping = AsyncMock()
        mock.get = AsyncMock()
        mock.setex = AsyncMock()
        mock.delete = AsyncMock(return_value=1)
        mock.keys = AsyncMock(return_value=["key1", "key2"])
        mock.info = AsyncMock(
            return_value={
                "used_memory": 1024,
                "keyspace_hits": 100,
                "keyspace_misses": 20,
                "redis_version": "6.2.0",
                "uptime_in_seconds": 3600,
            }
        )
        mock.incr = AsyncMock(return_value=1)
        mock.expire = AsyncMock()
        mock.pipeline = AsyncMock()
        mock.aclose = AsyncMock()
        return mock

    @pytest.fixture
    def connection_pool_mock(self):
        """Mock Redis connection pool."""
        mock = MagicMock()
        mock.aclose = AsyncMock()
        return mock

    @pytest.fixture
    def redis_service_instance(self):
        """Fresh Redis service instance for testing."""
        return RedisService()

    @pytest.mark.asyncio
    async def test_redis_connect_success(
        self, redis_service_instance, redis_mock, connection_pool_mock
    ):
        """Test successful Redis connection."""
        with (
            patch("redis.asyncio.ConnectionPool") as pool_class,
            patch("redis.asyncio.Redis") as redis_class,
            patch("github_analyzer.api.services.redis_service.config") as config_mock,
        ):
            config_mock.get.return_value = "redis://localhost:6379/0"
            pool_class.from_url.return_value = connection_pool_mock
            redis_class.return_value = redis_mock

            await redis_service_instance.connect()

            assert redis_service_instance.is_connected()
            pool_class.from_url.assert_called_once()
            redis_mock.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_connect_failure(self, redis_service_instance):
        """Test Redis connection failure handling."""
        with patch("redis.asyncio.ConnectionPool") as pool_class:
            pool_class.from_url.side_effect = Exception("Connection failed")

            await redis_service_instance.connect()

            assert not redis_service_instance.is_connected()

    @pytest.mark.asyncio
    async def test_redis_disconnect(
        self, redis_service_instance, redis_mock, connection_pool_mock
    ):
        """Test Redis disconnection."""
        redis_service_instance._redis = redis_mock
        redis_service_instance._connection_pool = connection_pool_mock
        redis_service_instance._connected = True

        await redis_service_instance.disconnect()

        redis_mock.aclose.assert_called_once()
        connection_pool_mock.aclose.assert_called_once()
        assert not redis_service_instance.is_connected()

    @pytest.mark.asyncio
    async def test_get_cache_hit(self, redis_service_instance, redis_mock):
        """Test cache get with hit."""
        redis_service_instance._redis = redis_mock
        redis_service_instance._connected = True
        redis_mock.get.return_value = "cached_value"

        result = await redis_service_instance.get("test_key")

        assert result == "cached_value"
        redis_mock.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_cache_miss(self, redis_service_instance, redis_mock):
        """Test cache get with miss."""
        redis_service_instance._redis = redis_mock
        redis_service_instance._connected = True
        redis_mock.get.return_value = None

        result = await redis_service_instance.get("test_key")

        assert result is None
        redis_mock.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_not_connected(self, redis_service_instance):
        """Test get when Redis not connected."""
        redis_service_instance._connected = False

        result = await redis_service_instance.get("test_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_set_cache_success(self, redis_service_instance, redis_mock):
        """Test successful cache set."""
        redis_service_instance._redis = redis_mock
        redis_service_instance._connected = True

        result = await redis_service_instance.set("test_key", "test_value", 300)

        assert result is True
        redis_mock.setex.assert_called_once_with("test_key", 300, "test_value")

    @pytest.mark.asyncio
    async def test_set_cache_not_connected(self, redis_service_instance):
        """Test cache set when not connected."""
        redis_service_instance._connected = False

        result = await redis_service_instance.set("test_key", "test_value")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_cache_success(self, redis_service_instance, redis_mock):
        """Test successful cache delete."""
        redis_service_instance._redis = redis_mock
        redis_service_instance._connected = True
        redis_mock.delete.return_value = 1

        result = await redis_service_instance.delete("test_key")

        assert result is True
        redis_mock.delete.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_clear_pattern_success(self, redis_service_instance, redis_mock):
        """Test successful pattern clearing."""
        redis_service_instance._redis = redis_mock
        redis_service_instance._connected = True
        redis_mock.keys.return_value = ["key1", "key2", "key3"]
        redis_mock.delete.return_value = 3

        result = await redis_service_instance.clear_pattern("test:*")

        assert result == 3
        redis_mock.keys.assert_called_once_with("test:*")
        redis_mock.delete.assert_called_once_with("key1", "key2", "key3")

    @pytest.mark.asyncio
    async def test_clear_pattern_no_keys(self, redis_service_instance, redis_mock):
        """Test pattern clearing with no matching keys."""
        redis_service_instance._redis = redis_mock
        redis_service_instance._connected = True
        redis_mock.keys.return_value = []

        result = await redis_service_instance.clear_pattern("test:*")

        assert result == 0
        redis_mock.keys.assert_called_once_with("test:*")
        redis_mock.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_stats_connected(self, redis_service_instance, redis_mock):
        """Test getting stats when connected."""
        redis_service_instance._redis = redis_mock
        redis_service_instance._connected = True

        info_response = {
            "used_memory": 1024,
            "keyspace_hits": 100,
            "keyspace_misses": 20,
            "redis_version": "6.2.0",
            "uptime_in_seconds": 3600,
        }
        keyspace_response = {"db0": {"keys": 50, "expires": 10}}

        redis_mock.info.side_effect = [info_response, keyspace_response]

        result = await redis_service_instance.get_stats()

        expected_hit_rate = (100 / (100 + 20)) * 100  # 83.33%

        assert result["connected"] is True
        assert result["total_keys"] == 50
        assert result["memory_usage"] == 1024
        assert result["hit_rate"] == expected_hit_rate
        assert result["version"] == "6.2.0"
        assert result["uptime"] == 3600

    @pytest.mark.asyncio
    async def test_get_stats_not_connected(self, redis_service_instance):
        """Test getting stats when not connected."""
        redis_service_instance._connected = False

        result = await redis_service_instance.get_stats()

        assert result["connected"] is False
        assert result["total_keys"] == 0
        assert result["memory_usage"] == 0
        assert result["hit_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_rate_limit_allowed(self, redis_service_instance, redis_mock):
        """Test rate limiting when under limit."""
        redis_service_instance._redis = redis_mock
        redis_service_instance._connected = True

        # Mock pipeline - using a different approach
        pipeline_mock = AsyncMock()
        pipeline_mock.incr = AsyncMock()
        pipeline_mock.expire = AsyncMock()
        pipeline_mock.execute = AsyncMock(
            return_value=[5, True]
        )  # Current count, expire result

        # Create a proper async context manager mock
        class PipelineContextManager:
            async def __aenter__(self):
                return pipeline_mock

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        # Set pipeline to be a method, not an AsyncMock
        def pipeline():
            return PipelineContextManager()

        redis_mock.pipeline = pipeline

        count, allowed = await redis_service_instance.increment_rate_limit(
            "test_key", window_seconds=60, limit=10
        )

        assert count == 5
        assert allowed is True

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, redis_service_instance, redis_mock):
        """Test rate limiting when limit exceeded."""
        redis_service_instance._redis = redis_mock
        redis_service_instance._connected = True

        # Mock pipeline - using the same approach
        pipeline_mock = AsyncMock()
        pipeline_mock.incr = AsyncMock()
        pipeline_mock.expire = AsyncMock()
        pipeline_mock.execute = AsyncMock(
            return_value=[15, True]
        )  # Current count > limit

        # Create a proper async context manager mock
        class PipelineContextManager:
            async def __aenter__(self):
                return pipeline_mock

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        # Set pipeline to be a method, not an AsyncMock
        def pipeline():
            return PipelineContextManager()

        redis_mock.pipeline = pipeline

        count, allowed = await redis_service_instance.increment_rate_limit(
            "test_key", window_seconds=60, limit=10
        )

        assert count == 15
        assert allowed is False

    @pytest.mark.asyncio
    async def test_rate_limit_not_connected(self, redis_service_instance):
        """Test rate limiting when Redis not connected."""
        redis_service_instance._connected = False

        count, allowed = await redis_service_instance.increment_rate_limit(
            "test_key", window_seconds=60, limit=10
        )

        assert count == 1
        assert allowed is True  # Allow when Redis unavailable

    def test_calculate_hit_rate_normal(self, redis_service_instance):
        """Test hit rate calculation with normal values."""
        info = {"keyspace_hits": 80, "keyspace_misses": 20}

        hit_rate = redis_service_instance._calculate_hit_rate(info)

        assert hit_rate == 80.0

    def test_calculate_hit_rate_no_requests(self, redis_service_instance):
        """Test hit rate calculation with no requests."""
        info = {"keyspace_hits": 0, "keyspace_misses": 0}

        hit_rate = redis_service_instance._calculate_hit_rate(info)

        assert hit_rate == 0.0

    def test_generate_analysis_cache_key(self):
        """Test analysis cache key generation."""
        key = generate_analysis_cache_key("https://github.com/user/repo", "startup")

        assert key.startswith("analysis:")
        assert len(key) == 41  # "analysis:" + 32-char MD5 hash

    def test_generate_rate_limit_key(self):
        """Test rate limit key generation."""
        key = generate_rate_limit_key("192.168.1.1", "analysis")

        assert key == "rate_limit:analysis:192.168.1.1"

    def test_generate_rate_limit_key_default_endpoint(self):
        """Test rate limit key generation with default endpoint."""
        key = generate_rate_limit_key("192.168.1.1")

        assert key == "rate_limit:global:192.168.1.1"

    @pytest.mark.asyncio
    async def test_get_redis_service_dependency(self):
        """Test Redis service dependency function."""
        service = await get_redis_service()

        assert isinstance(service, RedisService)
        assert service is redis_service  # Should return singleton

    def test_global_redis_service_instance(self):
        """Test global Redis service instance."""
        assert isinstance(redis_service, RedisService)
        assert not redis_service.is_connected()  # Not connected by default
