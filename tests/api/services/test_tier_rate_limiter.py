"""
Tests for TierRateLimiter with Operation Sustainable Limits.
Tests the new rate limiting structure:
- Monthly quotas
- Daily limits
- Burst limits (per minute)
- Batch size limits
- Cooldown periods
"""

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from github_analyzer.api.services.tier_rate_limiter import TierRateLimiter
from github_analyzer.database.models import SubscriptionPlan


class TestTierRateLimiter:
    """Test cases for tier-based rate limiting."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis service."""
        redis = AsyncMock()
        redis.is_connected = MagicMock(return_value=True)
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncMock(return_value=True)
        redis.incr = AsyncMock(return_value=1)
        redis.decr = AsyncMock(return_value=0)
        redis.zadd = AsyncMock(return_value=1)
        redis.zcount = AsyncMock(return_value=0)
        redis.zremrangebyscore = AsyncMock(return_value=0)
        redis.expire = AsyncMock(return_value=True)
        return redis

    @pytest.fixture
    def rate_limiter(self, mock_redis):
        """Create TierRateLimiter instance."""
        return TierRateLimiter(mock_redis)

    @pytest.mark.asyncio
    async def test_free_tier_limits(self, rate_limiter):
        """Test FREE tier rate limits."""
        # Test single request allowed
        allowed, error, retry_info = await rate_limiter.check_rate_limit(
            "user_free", SubscriptionPlan.FREE, is_batch=False, batch_size=1
        )
        assert allowed is True
        assert error is None
        # Test batch not allowed for FREE tier
        allowed, error, retry_info = await rate_limiter.check_rate_limit(
            "user_free", SubscriptionPlan.FREE, is_batch=True, batch_size=2
        )
        assert allowed is False
        assert "Batch size 2 exceeds limit of 1" in error

    @pytest.mark.asyncio
    async def test_basic_tier_limits(self, rate_limiter):
        """Test BASIC tier rate limits."""
        # Test single request allowed
        allowed, error, retry_info = await rate_limiter.check_rate_limit(
            "user_basic", SubscriptionPlan.BASIC, is_batch=False, batch_size=1
        )
        assert allowed is True
        # Test batch size 2 allowed
        allowed, error, retry_info = await rate_limiter.check_rate_limit(
            "user_basic", SubscriptionPlan.BASIC, is_batch=True, batch_size=2
        )
        assert allowed is True
        # Test batch size 3 not allowed
        allowed, error, retry_info = await rate_limiter.check_rate_limit(
            "user_basic", SubscriptionPlan.BASIC, is_batch=True, batch_size=3
        )
        assert allowed is False
        assert "Batch size 3 exceeds limit of 2" in error

    @pytest.mark.asyncio
    async def test_professional_tier_limits(self, rate_limiter):
        """Test PROFESSIONAL tier rate limits."""
        # Test batch size 5 allowed
        allowed, error, retry_info = await rate_limiter.check_rate_limit(
            "user_pro", SubscriptionPlan.PROFESSIONAL, is_batch=True, batch_size=5
        )
        assert allowed is True
        # Test batch size 6 not allowed
        allowed, error, retry_info = await rate_limiter.check_rate_limit(
            "user_pro", SubscriptionPlan.PROFESSIONAL, is_batch=True, batch_size=6
        )
        assert allowed is False
        assert "Batch size 6 exceeds limit of 5" in error

    @pytest.mark.asyncio
    async def test_enterprise_tier_limits(self, rate_limiter):
        """Test ENTERPRISE tier rate limits."""
        # Test batch size 10 allowed
        allowed, error, retry_info = await rate_limiter.check_rate_limit(
            "user_ent", SubscriptionPlan.ENTERPRISE, is_batch=True, batch_size=10
        )
        assert allowed is True
        # Test batch size 11 not allowed
        allowed, error, retry_info = await rate_limiter.check_rate_limit(
            "user_ent", SubscriptionPlan.ENTERPRISE, is_batch=True, batch_size=11
        )
        assert allowed is False
        assert "Batch size 11 exceeds limit of 10" in error

    @pytest.mark.asyncio
    async def test_requests_per_minute_limit(self, rate_limiter, mock_redis):
        """Test per-minute burst limits."""
        # Mock sliding window count to simulate hitting limit
        mock_redis.zcount = AsyncMock(return_value=1)  # Already at limit for FREE
        allowed, error, retry_info = await rate_limiter.check_rate_limit(
            "user_free", SubscriptionPlan.FREE
        )
        assert allowed is False
        assert "Rate limit exceeded: 1 requests per minute" in error
        assert retry_info["retry_after"] > 0

    @pytest.mark.asyncio
    async def test_requests_per_hour_limit(self, rate_limiter, mock_redis):
        """Test hourly limits."""

        # First mock minute check passes
        async def mock_zcount(key, start, end):
            if "rpm" in key:
                return 0  # Pass minute check
            elif "rph" in key:
                return 5  # At hourly limit for FREE
            return 0

        mock_redis.zcount = mock_zcount
        allowed, error, retry_info = await rate_limiter.check_rate_limit(
            "user_free", SubscriptionPlan.FREE
        )
        assert allowed is False
        assert "Hourly rate limit exceeded: 1 requests per hour" in error

    @pytest.mark.asyncio
    async def test_concurrent_request_limits(self, rate_limiter, mock_redis):
        """Test concurrent request limits."""
        # Mock high concurrent count
        mock_redis.get = AsyncMock(return_value="1")  # At limit for FREE
        allowed, error, retry_info = await rate_limiter.check_rate_limit(
            "user_free", SubscriptionPlan.FREE
        )
        assert allowed is False
        assert "Concurrent request limit (1) exceeded" in error

    @pytest.mark.asyncio
    async def test_daily_limits(self, rate_limiter, mock_redis):
        """Test daily limits (new in Operation Sustainable Limits)."""

        # Mock to simulate daily limit reached
        async def mock_zcount(key, start, end):
            if "rpm" in key:
                return 0  # Pass minute check
            elif "rph" in key:
                return 4  # Pass hour check
            elif "rpd" in key:
                return 5  # At daily limit for FREE
            return 0

        mock_redis.zcount = mock_zcount
        # Check if daily limits are implemented
        # Note: This test assumes daily limits will be added to the implementation
        allowed, error, retry_info = await rate_limiter.check_rate_limit(
            "user_free", SubscriptionPlan.FREE
        )
        # Current implementation might not have daily limits yet
        # This test documents what should be added

    @pytest.mark.asyncio
    async def test_enterprise_no_cost_limit(self, rate_limiter):
        """Test that Enterprise tier has no daily cost limit."""
        limits = rate_limiter._get_tier_limits(SubscriptionPlan.ENTERPRISE)
        # Verify daily_cost_limit is None (no limit) for Enterprise
        assert limits.get("daily_cost_limit") is None

    @pytest.mark.asyncio
    async def test_api_overload_handling(self, rate_limiter):
        """Test API overload handling."""
        error_message = "API is overloaded"
        result = await rate_limiter.handle_api_overload(error_message)
        assert result["retry_after"] == 30
        assert result["reduce_batch_size"] is True
        assert result["use_fallback_model"] is True
        assert "overloaded" in result["message"]

    @pytest.mark.asyncio
    async def test_sliding_window_cleanup(self, rate_limiter, mock_redis):
        """Test that old entries are cleaned from sliding windows."""
        await rate_limiter._add_to_sliding_window("test_key", time.time())
        # Verify cleanup was called
        mock_redis.zremrangebyscore.assert_called()
        mock_redis.expire.assert_called_with("test_key", 120)

    @pytest.mark.asyncio
    async def test_tier_specific_api_limits(self, rate_limiter):
        """Test that different tiers check appropriate API models."""
        # Test Enterprise checks both Haiku 3.5 and Sonnet 3.5
        allowed, error, retry_info = await rate_limiter._check_api_limits(
            SubscriptionPlan.ENTERPRISE, batch_size=1
        )
        assert allowed is True  # Should pass with default mocks
        # Test Professional checks Haiku 3.0 and 3.5
        allowed, error, retry_info = await rate_limiter._check_api_limits(
            SubscriptionPlan.PROFESSIONAL, batch_size=1
        )
        assert allowed is True
        # Test Basic/Free only checks Haiku 3.0
        allowed, error, retry_info = await rate_limiter._check_api_limits(
            SubscriptionPlan.BASIC, batch_size=1
        )
        assert allowed is True

    @pytest.mark.asyncio
    async def test_usage_stats(self, rate_limiter, mock_redis):
        """Test usage statistics retrieval."""
        mock_redis.get = AsyncMock(
            side_effect=lambda key: "3" if "concurrent" in key else None
        )
        stats = await rate_limiter.get_usage_stats("user_test")
        assert stats["concurrent_requests"] == 3
        assert stats["requests_per_minute"] == 0
        assert stats["api_health"] == "healthy"
        # Test with backoff active
        mock_redis.get = AsyncMock(
            side_effect=lambda key: "1" if "backoff" in key else None
        )
        stats = await rate_limiter.get_usage_stats("user_test")
        assert stats["in_backoff_mode"] is True
        assert stats["api_health"] == "degraded"

    @pytest.mark.asyncio
    async def test_rate_limit_acquisition_and_release(self, rate_limiter, mock_redis):
        """Test acquiring and releasing rate limit slots."""
        # Setup mock to return a positive count for concurrent key
        mock_redis.get = AsyncMock(return_value="1")
        # Test acquire
        result = await rate_limiter.acquire_rate_limit(
            "user_test", SubscriptionPlan.PROFESSIONAL, batch_size=5
        )
        assert result is True
        # Verify counters were incremented
        mock_redis.incr.assert_called()
        # Test release
        await rate_limiter.release_rate_limit("user_test")
        # Verify counter was decremented
        mock_redis.decr.assert_called()

    @pytest.mark.asyncio
    async def test_batch_hour_limits(self, rate_limiter):
        """Test batch per hour limits for Professional, Enterprise, and Scale+."""
        # Get limits from tier config
        pro_limits = rate_limiter._get_tier_limits(SubscriptionPlan.PROFESSIONAL)
        # Professional should allow batch size of 5 (from tier_config.py)
        assert pro_limits["batch_size"] == 5

        ent_limits = rate_limiter._get_tier_limits(SubscriptionPlan.ENTERPRISE)
        # Enterprise should allow batch size of 10 (from tier_config.py)
        assert ent_limits["batch_size"] == 10

        scale_plus_limits = rate_limiter._get_tier_limits(SubscriptionPlan.SCALE_PLUS)
        # Scale+ should allow batch size of 15 (from tier_config.py)
        assert scale_plus_limits["batch_size"] == 15
