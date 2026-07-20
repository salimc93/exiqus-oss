"""
Tests for CostAnalyticsService.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from github_analyzer.api.services.cost_analytics_service import CostAnalyticsService
from github_analyzer.api.services.redis_service import RedisService
from github_analyzer.database.models import SubscriptionPlan, User


@pytest.fixture
def mock_redis_service() -> AsyncMock:
    """Create a mock Redis service."""
    mock = AsyncMock(spec=RedisService)
    return mock


@pytest.fixture
def mock_db() -> AsyncMock:
    """Create a mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def cost_analytics_service(
    mock_redis_service: AsyncMock, mock_db: AsyncMock
) -> CostAnalyticsService:
    """Create a CostAnalyticsService instance with mocked dependencies."""
    return CostAnalyticsService(redis_service=mock_redis_service, db=mock_db)


@pytest.fixture
def mock_user() -> User:
    """Create a mock user."""
    user = MagicMock(spec=User)
    user.user_id = "test_user"
    user.subscription_plan = SubscriptionPlan.PROFESSIONAL
    return user


class TestCostAnalyticsService:
    """Test cases for CostAnalyticsService."""

    @pytest.mark.asyncio
    async def test_calculate_cost_haiku_3_model(
        self, cost_analytics_service: CostAnalyticsService
    ) -> None:
        """Test cost calculation for Haiku 3 model (FREE tier)."""
        # Arrange
        model = "claude-3-haiku-20240307"
        input_tokens = 1000
        output_tokens = 500

        # Act
        cost = cost_analytics_service.calculate_cost(model, input_tokens, output_tokens)

        # Assert
        # Expected: ($0.25/MTok * 1000/1M) + ($1.25/MTok * 500/1M)
        expected_cost = (0.25 * 1000 / 1_000_000) + (1.25 * 500 / 1_000_000)
        assert cost == pytest.approx(expected_cost, rel=1e-6)

    @pytest.mark.asyncio
    async def test_calculate_cost_haiku_3_5_model(
        self, cost_analytics_service: CostAnalyticsService
    ) -> None:
        """Test cost calculation for Haiku 3.5 model (BASIC tier)."""
        # Arrange
        model = "claude-3-5-haiku-20241022"
        input_tokens = 2000
        output_tokens = 1000

        # Act
        cost = cost_analytics_service.calculate_cost(model, input_tokens, output_tokens)

        # Assert
        # Expected: ($0.80/MTok * 2000/1M) + ($4.00/MTok * 1000/1M)
        expected_cost = (0.80 * 2000 / 1_000_000) + (4.00 * 1000 / 1_000_000)
        assert cost == pytest.approx(expected_cost, rel=1e-6)

    @pytest.mark.asyncio
    async def test_calculate_cost_sonnet_3_5_model(
        self, cost_analytics_service: CostAnalyticsService
    ) -> None:
        """Test cost calculation for Sonnet 3.5 model (PROFESSIONAL/ENTERPRISE)."""
        # Arrange
        model = "claude-3-5-sonnet-20241022"
        input_tokens = 5000
        output_tokens = 2500

        # Act
        cost = cost_analytics_service.calculate_cost(model, input_tokens, output_tokens)

        # Assert
        # Expected: ($3.00/MTok * 5000/1M) + ($15.00/MTok * 2500/1M)
        expected_cost = (3.00 * 5000 / 1_000_000) + (15.00 * 2500 / 1_000_000)
        assert cost == pytest.approx(expected_cost, rel=1e-6)

    @pytest.mark.asyncio
    async def test_calculate_cost_sonnet_3_7_model(
        self, cost_analytics_service: CostAnalyticsService
    ) -> None:
        """Test cost calculation for Sonnet 3.7 model (SCALE_PLUS)."""
        # Arrange
        model = "claude-3-7-sonnet-20250219"
        input_tokens = 10000
        output_tokens = 5000

        # Act
        cost = cost_analytics_service.calculate_cost(model, input_tokens, output_tokens)

        # Assert
        # Expected: ($3.00/MTok * 10000/1M) + ($15.00/MTok * 5000/1M)
        expected_cost = (3.00 * 10000 / 1_000_000) + (15.00 * 5000 / 1_000_000)
        assert cost == pytest.approx(expected_cost, rel=1e-6)

    @pytest.mark.asyncio
    async def test_calculate_cost_unknown_model_uses_default(
        self, cost_analytics_service: CostAnalyticsService
    ) -> None:
        """Test that unknown models fall back to default Haiku 3 pricing."""
        # Arrange
        model = "claude-4-ultra-future"
        input_tokens = 1000
        output_tokens = 500

        # Act
        cost = cost_analytics_service.calculate_cost(model, input_tokens, output_tokens)

        # Assert - should use default Haiku 3 pricing
        expected_cost = (0.25 * 1000 / 1_000_000) + (1.25 * 500 / 1_000_000)
        assert cost == pytest.approx(expected_cost, rel=1e-6)

    @pytest.mark.asyncio
    async def test_track_analysis_cost_basic(
        self,
        cost_analytics_service: CostAnalyticsService,
        mock_redis_service: AsyncMock,
        mock_db: AsyncMock,
        mock_user: User,
    ) -> None:
        """Test tracking analysis cost."""
        # Arrange
        user_id = "test_user"
        model = "claude-3-5-sonnet-20241022"
        input_tokens = 1000
        output_tokens = 500

        # Calculate expected cost
        cost_usd = cost_analytics_service.calculate_cost(
            model, input_tokens, output_tokens
        )

        # Mock the user lookup
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_user)
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        await cost_analytics_service.track_analysis_cost(
            user_id=user_id,
            cost_usd=cost_usd,
            model=model,
            tokens_used=input_tokens + output_tokens,
            analysis_type="basic",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        # Assert
        # Verify user was looked up
        mock_db.execute.assert_called()

    @pytest.mark.asyncio
    async def test_get_platform_cost_summary(
        self,
        cost_analytics_service: CostAnalyticsService,
        mock_redis_service: AsyncMock,
        mock_db: AsyncMock,
    ) -> None:
        """Test getting platform cost summary."""

        # Arrange
        # Mock Redis get to return costs for some calls and None for others
        async def mock_get(key):
            if "daily" in key and "platform" in key:
                # Return costs for platform daily keys
                return "15.5"
            elif "daily" in key and "tier" in key:
                # Return costs for tier daily keys
                return "5.0"
            elif "daily" in key and "model" in key:
                # Return costs for model daily keys
                return "3.0"
            return None

        mock_redis_service.get = AsyncMock(side_effect=mock_get)

        # Mock database execute for get_users_by_tier
        mock_execute_result = MagicMock()
        mock_execute_result.scalars = MagicMock()
        mock_execute_result.scalars.return_value.all = MagicMock(return_value=[])
        mock_db.execute = AsyncMock(return_value=mock_execute_result)

        # Act
        summary = await cost_analytics_service.get_platform_cost_summary(days=7)

        # Assert
        assert summary is not None
        assert summary["period_days"] == 7
        assert summary["total_cost"] > 0  # Should sum up the daily costs
        assert "daily_average" in summary
        assert "estimated_monthly_cost" in summary
        assert "cost_by_tier" in summary
        assert "cost_by_model" in summary
        assert "daily_costs" in summary
        assert len(summary["daily_costs"]) == 7

    @pytest.mark.asyncio
    async def test_get_tier_analytics(
        self,
        cost_analytics_service: CostAnalyticsService,
        mock_redis_service: AsyncMock,
        mock_db: AsyncMock,
    ) -> None:
        """Test getting tier-specific analytics."""
        # Arrange
        tier = SubscriptionPlan.PROFESSIONAL

        # Mock database results for users
        mock_user = MagicMock()
        mock_user.subscription_plan = tier
        mock_users = [mock_user, mock_user]  # 2 users

        # Mock the execute for SELECT users
        mock_execute_result = MagicMock()
        mock_execute_result.scalars = MagicMock()
        mock_execute_result.scalars.return_value.all = MagicMock(
            return_value=mock_users
        )
        mock_db.execute = AsyncMock(return_value=mock_execute_result)

        # Mock Redis get calls for tier costs
        mock_redis_service.get = AsyncMock(
            return_value="10.50"
        )  # Return cost as string

        # Act
        analytics = await cost_analytics_service.get_tier_analytics(tier=tier, days=30)

        # Assert
        assert analytics is not None
        # Verify tier value is correct
        assert analytics["tier"] == "PROFESSIONAL"
        assert analytics["user_count"] == 2
        assert "financial_metrics" in analytics

    @pytest.mark.asyncio
    async def test_all_tier_pricing_calculations(
        self, cost_analytics_service: CostAnalyticsService
    ) -> None:
        """Test that all tiers have correct pricing calculations."""
        # Test data: (tier, expected_monthly_price)
        # From _get_tier_price in implementation
        tier_data = [
            (SubscriptionPlan.FREE, 0.0),
            (SubscriptionPlan.BASIC, 29.0),  # Correct price from implementation
            (SubscriptionPlan.PROFESSIONAL, 99.0),  # Correct price from implementation
            (SubscriptionPlan.ENTERPRISE, 997.0),  # Correct price from implementation
            (SubscriptionPlan.SCALE_PLUS, 1997.0),
        ]

        for tier, expected_price in tier_data:
            # Get tier price using the internal method
            actual_price = cost_analytics_service._get_tier_price(tier)

            # Assert correct pricing
            assert actual_price == expected_price

    @pytest.mark.asyncio
    async def test_all_models_have_pricing(
        self, cost_analytics_service: CostAnalyticsService
    ) -> None:
        """Test that all expected models have pricing defined."""
        expected_models = [
            "claude-3-haiku-20240307",  # FREE tier
            "claude-3-5-haiku-20241022",  # BASIC tier
            "claude-3-5-sonnet-20241022",  # PROFESSIONAL/ENTERPRISE
            "claude-3-7-sonnet-20250219",  # SCALE_PLUS tier
        ]

        for model in expected_models:
            # Verify model has pricing
            assert model in cost_analytics_service.MODEL_COSTS
            assert "input" in cost_analytics_service.MODEL_COSTS[model]
            assert "output" in cost_analytics_service.MODEL_COSTS[model]

            # Verify costs are positive
            assert cost_analytics_service.MODEL_COSTS[model]["input"] > 0
            assert cost_analytics_service.MODEL_COSTS[model]["output"] > 0
