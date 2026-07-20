"""Tests for PR Rate Limiter Service."""

from unittest.mock import AsyncMock, patch

import pytest

from src.github_analyzer.database.models import SubscriptionPlan
from src.github_analyzer.services.pr_rate_limiter import PRRateLimiter, pr_rate_limiter


class TestPRRateLimiter:
    """Test PRRateLimiter class."""

    @pytest.fixture
    def rate_limiter(self):
        """Create a rate limiter instance."""
        return PRRateLimiter()

    @pytest.mark.asyncio
    async def test_check_limit_free_tier_no_access(self, rate_limiter):
        """Test that FREE tier has no PR access."""
        is_allowed, count, limit = await rate_limiter.check_limit(
            "user123", SubscriptionPlan.FREE
        )

        assert is_allowed is False
        assert count == 0
        assert limit == 0

    @pytest.mark.asyncio
    async def test_check_limit_within_limit(self, rate_limiter):
        """Test check_limit when user is within limit."""
        # Mock Redis incr to return 1 (first request)
        with patch.object(rate_limiter.redis, "incr", new=AsyncMock(return_value=1)):
            with patch.object(rate_limiter.redis, "expire", new=AsyncMock()):
                is_allowed, count, limit = await rate_limiter.check_limit(
                    "user123", SubscriptionPlan.BASIC
                )

        assert is_allowed is True
        assert count == 1
        assert limit == 10

    @pytest.mark.asyncio
    async def test_check_limit_at_limit(self, rate_limiter):
        """Test check_limit when user is at the limit."""
        # Mock Redis incr to return 10 (at limit for BASIC tier)
        with patch.object(rate_limiter.redis, "incr", new=AsyncMock(return_value=10)):
            is_allowed, count, limit = await rate_limiter.check_limit(
                "user123", SubscriptionPlan.BASIC
            )

        assert is_allowed is True
        assert count == 10
        assert limit == 10

    @pytest.mark.asyncio
    async def test_check_limit_exceeded(self, rate_limiter):
        """Test check_limit when user has exceeded limit."""
        # Mock Redis incr to return 11 (exceeded limit for BASIC tier)
        with patch.object(rate_limiter.redis, "incr", new=AsyncMock(return_value=11)):
            is_allowed, count, limit = await rate_limiter.check_limit(
                "user123", SubscriptionPlan.BASIC
            )

        assert is_allowed is False
        assert count == 11
        assert limit == 10

    @pytest.mark.asyncio
    async def test_check_limit_bytes_response(self, rate_limiter):
        """Test check_limit handles bytes response from Redis."""
        # Mock Redis incr to return bytes
        with patch.object(rate_limiter.redis, "incr", new=AsyncMock(return_value=b"5")):
            with patch.object(rate_limiter.redis, "expire", new=AsyncMock()):
                is_allowed, count, limit = await rate_limiter.check_limit(
                    "user123", SubscriptionPlan.PROFESSIONAL
                )

        assert is_allowed is True
        assert count == 5
        assert limit == 15

    @pytest.mark.asyncio
    async def test_check_limit_first_request_sets_expiry(self, rate_limiter):
        """Test that expiry is set on first request."""
        mock_expire = AsyncMock()

        with patch.object(rate_limiter.redis, "incr", new=AsyncMock(return_value=1)):
            with patch.object(rate_limiter.redis, "expire", new=mock_expire):
                await rate_limiter.check_limit("user123", SubscriptionPlan.ENTERPRISE)

        # Verify expire was called with correct TTL
        mock_expire.assert_called_once_with("pr_rate:user123:hour", 3600)

    @pytest.mark.asyncio
    async def test_check_limit_error_handling(self, rate_limiter):
        """Test check_limit error handling."""
        # Mock Redis incr to raise an exception
        with patch.object(
            rate_limiter.redis, "incr", side_effect=Exception("Redis error")
        ):
            is_allowed, count, limit = await rate_limiter.check_limit(
                "user123", SubscriptionPlan.BASIC
            )

        # On error, should allow the request
        assert is_allowed is True
        assert count == 0

    @pytest.mark.asyncio
    async def test_check_limit_all_tiers(self, rate_limiter):
        """Test check_limit with all subscription tiers."""
        expected_limits = {
            SubscriptionPlan.FREE: 0,
            SubscriptionPlan.BASIC: 10,
            SubscriptionPlan.PROFESSIONAL: 15,
            SubscriptionPlan.ENTERPRISE: 20,
            SubscriptionPlan.SCALE_PLUS: 25,
        }

        for tier, expected_limit in expected_limits.items():
            with patch.object(
                rate_limiter.redis, "incr", new=AsyncMock(return_value=1)
            ):
                with patch.object(rate_limiter.redis, "expire", new=AsyncMock()):
                    is_allowed, count, limit = await rate_limiter.check_limit(
                        f"user_{tier.value}", tier
                    )

                    if tier == SubscriptionPlan.FREE:
                        assert is_allowed is False
                        assert limit == 0
                    else:
                        assert is_allowed is True
                        assert limit == expected_limit

    @pytest.mark.asyncio
    async def test_get_remaining_time_with_active_limit(self, rate_limiter):
        """Test get_remaining_time when rate limit is active."""
        # Mock Redis get to return a value (rate limit exists)
        with patch.object(rate_limiter.redis, "get", new=AsyncMock(return_value="5")):
            remaining = await rate_limiter.get_remaining_time("user123")

        assert remaining == 3600

    @pytest.mark.asyncio
    async def test_get_remaining_time_no_active_limit(self, rate_limiter):
        """Test get_remaining_time when no rate limit is active."""
        # Mock Redis get to return None
        with patch.object(rate_limiter.redis, "get", new=AsyncMock(return_value=None)):
            remaining = await rate_limiter.get_remaining_time("user123")

        assert remaining is None

    @pytest.mark.asyncio
    async def test_get_remaining_time_error_handling(self, rate_limiter):
        """Test get_remaining_time error handling."""
        # Mock Redis get to raise an exception
        with patch.object(
            rate_limiter.redis, "get", side_effect=Exception("Redis error")
        ):
            remaining = await rate_limiter.get_remaining_time("user123")

        assert remaining is None

    @pytest.mark.asyncio
    async def test_reset_limit_success(self, rate_limiter):
        """Test reset_limit successful reset."""
        mock_delete = AsyncMock()

        with patch.object(rate_limiter.redis, "delete", new=mock_delete):
            result = await rate_limiter.reset_limit("user123")

        assert result is True
        mock_delete.assert_called_once_with("pr_rate:user123:hour")

    @pytest.mark.asyncio
    async def test_reset_limit_error_handling(self, rate_limiter):
        """Test reset_limit error handling."""
        # Mock Redis delete to raise an exception
        with patch.object(
            rate_limiter.redis, "delete", side_effect=Exception("Redis error")
        ):
            result = await rate_limiter.reset_limit("user123")

        assert result is False

    @pytest.mark.asyncio
    async def test_get_usage_stats_with_count(self, rate_limiter):
        """Test get_usage_stats with existing usage."""
        # Mock Redis get to return current count
        with patch.object(rate_limiter.redis, "get", new=AsyncMock(return_value="7")):
            stats = await rate_limiter.get_usage_stats(
                "user123", SubscriptionPlan.BASIC
            )

        assert stats["current_hour_usage"] == 7
        assert stats["hourly_limit"] == 10
        assert stats["remaining_this_hour"] == 3
        assert stats["resets_in_seconds"] == 3600
        assert stats["resets_in_minutes"] == 60

    @pytest.mark.asyncio
    async def test_get_usage_stats_no_usage(self, rate_limiter):
        """Test get_usage_stats with no usage."""
        # Mock Redis get to return None
        with patch.object(rate_limiter.redis, "get", new=AsyncMock(return_value=None)):
            stats = await rate_limiter.get_usage_stats(
                "user123", SubscriptionPlan.PROFESSIONAL
            )

        assert stats["current_hour_usage"] == 0
        assert stats["hourly_limit"] == 15
        assert stats["remaining_this_hour"] == 15
        assert stats["resets_in_seconds"] is None
        assert stats["resets_in_minutes"] is None

    @pytest.mark.asyncio
    async def test_get_usage_stats_bytes_response(self, rate_limiter):
        """Test get_usage_stats handles bytes response."""
        # Mock Redis get to return bytes
        with patch.object(rate_limiter.redis, "get", new=AsyncMock(return_value=b"3")):
            stats = await rate_limiter.get_usage_stats(
                "user123", SubscriptionPlan.ENTERPRISE
            )

        assert stats["current_hour_usage"] == 3
        assert stats["hourly_limit"] == 20
        assert stats["remaining_this_hour"] == 17

    @pytest.mark.asyncio
    async def test_get_usage_stats_malformed_string(self, rate_limiter):
        """Test get_usage_stats handles malformed string responses."""
        # Test various malformed string formats
        malformed_values = ["b'5'", 'b"5"', "  b'5'  ", '  b"5"  ']

        for malformed in malformed_values:
            with patch.object(
                rate_limiter.redis, "get", new=AsyncMock(return_value=malformed)
            ):
                stats = await rate_limiter.get_usage_stats(
                    "user123", SubscriptionPlan.SCALE_PLUS
                )

            assert stats["current_hour_usage"] == 5
            assert stats["hourly_limit"] == 25

    @pytest.mark.asyncio
    async def test_get_usage_stats_error_handling(self, rate_limiter):
        """Test get_usage_stats error handling."""
        # Mock Redis get to raise an exception
        with patch.object(
            rate_limiter.redis, "get", side_effect=Exception("Redis error")
        ):
            stats = await rate_limiter.get_usage_stats(
                "user123", SubscriptionPlan.BASIC
            )

        assert stats["current_hour_usage"] == 0
        assert stats["hourly_limit"] == 10
        assert stats["remaining_this_hour"] == 0
        assert stats["resets_in_seconds"] is None
        assert stats["resets_in_minutes"] is None

    @pytest.mark.asyncio
    async def test_get_usage_stats_at_limit(self, rate_limiter):
        """Test get_usage_stats when at limit."""
        # Mock Redis get to return count equal to limit
        with patch.object(rate_limiter.redis, "get", new=AsyncMock(return_value="10")):
            stats = await rate_limiter.get_usage_stats(
                "user123", SubscriptionPlan.BASIC
            )

        assert stats["current_hour_usage"] == 10
        assert stats["hourly_limit"] == 10
        assert stats["remaining_this_hour"] == 0

    @pytest.mark.asyncio
    async def test_get_usage_stats_over_limit(self, rate_limiter):
        """Test get_usage_stats when over limit (negative shouldn't happen but use max)."""
        # Mock Redis get to return count over limit
        with patch.object(rate_limiter.redis, "get", new=AsyncMock(return_value="15")):
            stats = await rate_limiter.get_usage_stats(
                "user123", SubscriptionPlan.BASIC
            )

        assert stats["current_hour_usage"] == 15
        assert stats["hourly_limit"] == 10
        # Uses max(0, limit - count) so should be 0
        assert stats["remaining_this_hour"] == 0

    def test_module_level_instance(self):
        """Test that module-level pr_rate_limiter instance exists."""
        assert pr_rate_limiter is not None
        assert isinstance(pr_rate_limiter, PRRateLimiter)

    def test_hourly_limits_configured(self):
        """Test that hourly limits are properly configured."""
        limiter = PRRateLimiter()

        assert limiter.hourly_limits[SubscriptionPlan.FREE] == 0
        assert limiter.hourly_limits[SubscriptionPlan.BASIC] == 10
        assert limiter.hourly_limits[SubscriptionPlan.PROFESSIONAL] == 15
        assert limiter.hourly_limits[SubscriptionPlan.ENTERPRISE] == 20
        assert limiter.hourly_limits[SubscriptionPlan.SCALE_PLUS] == 25
        assert limiter.ttl == 3600
