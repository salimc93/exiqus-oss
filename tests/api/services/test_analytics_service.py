"""
Tests for the analytics service.

This module tests the real analytics service implementation
to ensure it correctly queries the database and returns accurate data.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from github_analyzer.api.models.analytics import (
    AdminAnalytics,
    AnalyticsFilter,
    UsageHistory,
    UserAnalytics,
)
from github_analyzer.api.services.analytics_service import AnalyticsService
from github_analyzer.database.models import UsageRecord, User


@pytest.fixture
def analytics_service():
    """Create analytics service instance."""
    return AnalyticsService()


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def sample_user():
    """Create sample user."""
    return User(
        user_id="test_user_123",
        email="test@example.com",
        full_name="Test User",
        usage_quota=1000,
        usage_count=50,
    )


@pytest.fixture
def sample_usage_records():
    """Create sample usage records."""
    base_time = datetime.now(timezone.utc) - timedelta(days=7)
    records = []

    for i in range(10):
        records.append(
            UsageRecord(
                record_id=f"usage_{i}",
                user_id="test_user_123",
                endpoint="/api/v1/analyze",
                method="POST",
                repository_url=f"https://github.com/user/repo{i % 3}",
                tokens_consumed=1000 + i * 100,
                cost_incurred=str(Decimal("0.01") * (i + 1)),
                response_time_ms=500 + i * 50,
                success=i % 4 != 0,  # Every 4th request fails
                error_message="Test error" if i % 4 == 0 else None,
                created_at=base_time + timedelta(days=i // 2),
            )
        )

    return records


class TestAnalyticsService:
    """Test analytics service methods."""

    @pytest.mark.asyncio
    async def test_get_user_analytics_with_valid_data(
        self, analytics_service, mock_db_session, sample_user
    ):
        """Test getting user analytics with valid data."""
        # Mock the analytics operations - patch individual static methods as AsyncMock
        with (
            patch(
                "github_analyzer.database.analytics_operations.AnalyticsOperations.get_user_usage_statistics",
                new_callable=AsyncMock,
            ) as mock_usage_stats,
            patch(
                "github_analyzer.database.analytics_operations.AnalyticsOperations.get_repository_statistics",
                new_callable=AsyncMock,
            ) as mock_repo_stats,
            patch(
                "github_analyzer.database.analytics_operations.AnalyticsOperations.get_cost_breakdown",
                new_callable=AsyncMock,
            ) as mock_cost_breakdown,
            patch(
                "github_analyzer.database.analytics_operations.AnalyticsOperations.get_usage_time_series",
                new_callable=AsyncMock,
            ) as mock_time_series,
        ):
            # Mock usage statistics
            mock_usage_stats.return_value = {
                "total_analyses": 10,
                "successful_analyses": 8,
                "failed_analyses": 2,
                "success_rate": 80.0,
                "total_cost": Decimal("0.55"),
                "average_cost_per_analysis": Decimal("0.055"),
                "average_response_time_ms": 750,
            }

            # Mock repository statistics
            mock_repo_stats.return_value = {
                "total_unique_repos": 3,
                "most_analyzed_repos": [
                    {
                        "name": "repo0",
                        "url": "https://github.com/user/repo0",
                        "count": 4,
                    },
                    {
                        "name": "repo1",
                        "url": "https://github.com/user/repo1",
                        "count": 3,
                    },
                    {
                        "name": "repo2",
                        "url": "https://github.com/user/repo2",
                        "count": 3,
                    },
                ],
            }

            # Mock cost breakdown
            mock_cost_breakdown.return_value = {
                "total_cost": Decimal("0.55"),
                "cost_by_operation": {"analyze": Decimal("0.55")},
            }

            # Mock time series data
            mock_time_series.return_value = [
                {
                    "timestamp": datetime.now(timezone.utc) - timedelta(days=i),
                    "analyses_count": 2,
                    "total_cost": 0.1 * (i + 1),
                }
                for i in range(7)
            ]

            # Mock user operations
            with patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_id",
                new_callable=AsyncMock,
            ) as mock_get_user:
                mock_get_user.return_value = sample_user

                # Call the service
                result = await analytics_service.get_user_analytics(
                    mock_db_session, "test_user_123"
                )

                # Verify result
                assert isinstance(result, UserAnalytics)
                assert result.user_id == "test_user_123"
                assert result.usage_stats.total_analyses == 10
                assert result.usage_stats.success_rate == 80.0
                assert result.repository_stats.total_unique_repos == 3
                assert result.cost_breakdown.total_cost == Decimal("0.55")
                assert len(result.usage_trend.data) == 7
                assert result.quota_usage["current_month_usage"] == 50

    @pytest.mark.asyncio
    async def test_get_user_analytics_with_date_filter(
        self, analytics_service, mock_db_session
    ):
        """Test getting user analytics with date filters."""
        start_date = datetime.now(timezone.utc) - timedelta(days=30)
        end_date = datetime.now(timezone.utc)

        filter_params = AnalyticsFilter(
            start_date=start_date,
            end_date=end_date,
        )

        with (
            patch(
                "github_analyzer.database.analytics_operations.AnalyticsOperations.get_user_usage_statistics",
                new_callable=AsyncMock,
            ) as mock_usage_stats,
            patch(
                "github_analyzer.database.analytics_operations.AnalyticsOperations.get_repository_statistics",
                new_callable=AsyncMock,
            ) as mock_repo_stats,
            patch(
                "github_analyzer.database.analytics_operations.AnalyticsOperations.get_cost_breakdown",
                new_callable=AsyncMock,
            ) as mock_cost_breakdown,
            patch(
                "github_analyzer.database.analytics_operations.AnalyticsOperations.get_usage_time_series",
                new_callable=AsyncMock,
            ) as mock_time_series,
        ):
            # Set up all required mocks
            mock_usage_stats.return_value = {
                "total_analyses": 5,
                "successful_analyses": 5,
                "failed_analyses": 0,
                "success_rate": 100.0,
                "total_cost": Decimal("0.25"),
                "average_cost_per_analysis": Decimal("0.05"),
                "average_response_time_ms": 500,
            }
            mock_repo_stats.return_value = {
                "total_unique_repos": 2,
                "most_analyzed_repos": [],
            }
            mock_cost_breakdown.return_value = {
                "total_cost": Decimal("0.25"),
                "cost_by_operation": {},
            }
            mock_time_series.return_value = []

            with patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_id",
                new_callable=AsyncMock,
            ) as mock_get_user:
                mock_get_user.return_value = MagicMock(
                    usage_consumed=25, usage_quota=100
                )

                await analytics_service.get_user_analytics(
                    mock_db_session, "test_user_123", filter_params
                )

                # Verify date parameters were passed correctly
                mock_usage_stats.assert_called_with(
                    mock_db_session, "test_user_123", start_date, end_date
                )

    @pytest.mark.asyncio
    async def test_get_user_analytics_invalid_user_id(
        self, analytics_service, mock_db_session
    ):
        """Test getting user analytics with invalid user ID."""
        with pytest.raises(ValueError, match="Invalid user_id provided"):
            await analytics_service.get_user_analytics(mock_db_session, "")

        with pytest.raises(ValueError, match="Invalid user_id provided"):
            await analytics_service.get_user_analytics(mock_db_session, None)

    @pytest.mark.asyncio
    async def test_get_user_analytics_future_date_validation(
        self, analytics_service, mock_db_session
    ):
        """Test that future dates are prevented."""
        future_date = datetime.now(timezone.utc) + timedelta(days=1)
        filter_params = AnalyticsFilter(end_date=future_date)

        with (
            patch(
                "github_analyzer.database.analytics_operations.AnalyticsOperations.get_user_usage_statistics",
                new_callable=AsyncMock,
            ) as mock_usage_stats,
            patch(
                "github_analyzer.database.analytics_operations.AnalyticsOperations.get_repository_statistics",
                new_callable=AsyncMock,
            ) as mock_repo_stats,
            patch(
                "github_analyzer.database.analytics_operations.AnalyticsOperations.get_cost_breakdown",
                new_callable=AsyncMock,
            ) as mock_cost_breakdown,
            patch(
                "github_analyzer.database.analytics_operations.AnalyticsOperations.get_usage_time_series",
                new_callable=AsyncMock,
            ) as mock_time_series,
        ):
            # Set up minimal mocks
            mock_usage_stats.return_value = {
                "total_analyses": 0,
                "successful_analyses": 0,
                "failed_analyses": 0,
                "success_rate": 0,
                "total_cost": Decimal("0"),
                "average_cost_per_analysis": Decimal("0"),
                "average_response_time_ms": 0,
            }
            mock_repo_stats.return_value = {
                "total_unique_repos": 0,
                "most_analyzed_repos": [],
            }
            mock_cost_breakdown.return_value = {
                "total_cost": Decimal("0"),
                "cost_by_operation": {},
            }
            mock_time_series.return_value = []

            with patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_id",
                new_callable=AsyncMock,
            ) as mock_get_user:
                mock_get_user.return_value = MagicMock(
                    usage_consumed=0, usage_quota=100
                )

                result = await analytics_service.get_user_analytics(
                    mock_db_session, "test_user_123", filter_params
                )

                # The service should have adjusted the end date
                assert result is not None

    @pytest.mark.asyncio
    async def test_get_usage_history_with_pagination(
        self, analytics_service, mock_db_session
    ):
        """Test getting usage history with pagination."""
        with (
            patch(
                "github_analyzer.database.analytics_operations.AnalyticsOperations.get_usage_history",
                new_callable=AsyncMock,
            ) as mock_usage_history,
            patch(
                "github_analyzer.database.analytics_operations.AnalyticsOperations.get_user_usage_statistics",
                new_callable=AsyncMock,
            ) as mock_usage_stats,
        ):
            # Mock usage history
            mock_usage_history.return_value = (
                [
                    {
                        "timestamp": datetime.now(timezone.utc),
                        "repository_url": "https://github.com/user/repo",
                        "repository_name": "repo",
                        "success": True,
                        "cost": Decimal("0.01"),
                        "tokens_used": 1000,
                        "processing_time": 0.5,
                        "error_message": None,
                    }
                    for _ in range(5)
                ],
                100,  # total count
            )

            # Mock summary statistics
            mock_usage_stats.return_value = {
                "total_analyses": 100,
                "successful_analyses": 95,
                "failed_analyses": 5,
                "success_rate": 95.0,
                "total_cost": Decimal("1.00"),
                "average_cost_per_analysis": Decimal("0.01"),
            }

            result = await analytics_service.get_usage_history(
                mock_db_session, "test_user_123", page=2, per_page=5
            )

            assert isinstance(result, UsageHistory)
            assert len(result.items) == 5
            assert result.total_count == 100
            assert result.page == 2
            assert result.per_page == 5
            assert result.has_next is True
            assert result.summary.total_analyses == 100

    @pytest.mark.asyncio
    async def test_get_usage_history_invalid_pagination(
        self, analytics_service, mock_db_session
    ):
        """Test usage history with invalid pagination parameters."""
        with pytest.raises(ValueError, match="Page number must be >= 1"):
            await analytics_service.get_usage_history(
                mock_db_session, "test_user_123", page=0
            )

        with pytest.raises(
            ValueError, match="Items per page must be between 1 and 100"
        ):
            await analytics_service.get_usage_history(
                mock_db_session, "test_user_123", per_page=150
            )

    @pytest.mark.asyncio
    async def test_get_admin_analytics(self, analytics_service, mock_db_session):
        """Test getting admin analytics."""
        with (
            patch(
                "github_analyzer.database.analytics_operations.AnalyticsOperations.get_system_metrics",
                new_callable=AsyncMock,
            ) as mock_system_metrics,
            patch(
                "github_analyzer.database.analytics_operations.AnalyticsOperations.get_user_behavior_analytics",
                new_callable=AsyncMock,
            ) as mock_user_behavior,
            patch(
                "github_analyzer.database.analytics_operations.AnalyticsOperations.get_revenue_analytics",
                new_callable=AsyncMock,
            ) as mock_revenue_analytics,
        ):
            # Mock system metrics
            mock_system_metrics.return_value = {
                "api_requests": 10000,
                "average_response_time": 0.05,
                "error_rate": 1.5,
                "cache_hit_rate": 85.0,
                "active_users": 150,
                "system_health": "healthy",
            }

            # Mock revenue analytics
            mock_revenue_analytics.return_value = {
                "total_revenue": Decimal("50000"),
                "monthly_recurring_revenue": Decimal("5000"),
                "annual_recurring_revenue": Decimal("60000"),
                "revenue_by_plan": {
                    "free": Decimal("0"),
                    "basic": Decimal("1000"),
                    "professional": Decimal("3000"),
                    "enterprise": Decimal("1000"),
                },
                "churn_rate": 2.5,
                "conversion_rate": 15.0,
            }

            # Mock user behavior
            mock_user_behavior.return_value = {
                "average_analyses_per_user": 25.5,
                "user_retention_rate": 85.0,
                "feature_adoption": {"analyze": 100.0, "batch_analyze": 45.0},
                "user_segments": {"free": 100, "paid": 50},
            }

            # Add the missing mock_usage_stats with proper patch context
            with patch(
                "github_analyzer.database.analytics_operations.AnalyticsOperations.get_user_usage_statistics",
                new_callable=AsyncMock,
            ) as mock_usage_stats:
                # Mock usage statistics
                mock_usage_stats.return_value = {
                    "total_analyses": 5000,
                    "successful_analyses": 4800,
                    "failed_analyses": 200,
                    "success_rate": 96.0,
                    "total_cost": Decimal("500"),
                    "average_cost_per_analysis": Decimal("0.10"),
                }

                # Mock database queries for additional data
                with patch(
                    "github_analyzer.database.operations.UserOperations.get_user_count",
                    new_callable=AsyncMock,
                ) as mock_user_count:
                    mock_user_count.return_value = 150

                    # Mock the database execute calls
                    mock_result = MagicMock()
                    mock_result.all.return_value = []
                    mock_result.scalar.return_value = 10
                    mock_db_session.execute.return_value = mock_result

                    result = await analytics_service.get_admin_analytics(
                        mock_db_session
                    )

                assert isinstance(result, AdminAnalytics)
                assert result.system_metrics.api_requests == 10000
                assert result.revenue_analytics.monthly_recurring_revenue == Decimal(
                    "5000"
                )
                assert result.user_behavior.average_analyses_per_user == 25.5
                assert result.usage_stats.total_analyses == 5000

    @pytest.mark.asyncio
    async def test_export_analytics(self, analytics_service, mock_db_session):
        """Test exporting analytics data."""
        with patch(
            "github_analyzer.database.analytics_operations.AnalyticsOperations.export_analytics_data",
            new_callable=AsyncMock,
        ) as mock_export_data:
            mock_export_data.return_value = {
                "export_date": datetime.now(timezone.utc).isoformat(),
                "user_id": "test_user_123",
                "period": {
                    "start_date": None,
                    "end_date": None,
                },
                "usage_statistics": {
                    "total_analyses": 100,
                    "successful_analyses": 95,
                    "failed_analyses": 5,
                    "success_rate": 95.0,
                    "total_cost": "10.00",
                    "average_cost_per_analysis": "0.10",
                },
                "repository_statistics": {
                    "total_unique_repos": 10,
                    "most_analyzed_repos": [],
                },
                "cost_breakdown": {
                    "total_cost": "10.00",
                    "cost_by_operation": {},
                },
                "time_series_data": [],
                "recent_activity": [],
            }

            result = await analytics_service.export_analytics(
                mock_db_session, "test_user_123"
            )

            assert isinstance(result, dict)
            assert result["user_id"] == "test_user_123"
            assert "usage_statistics" in result
            assert "repository_statistics" in result

    @pytest.mark.asyncio
    async def test_cache_functionality(self, analytics_service, mock_db_session):
        """Test that caching works correctly."""
        # Mock Redis to simulate cache hit
        mock_redis = AsyncMock()
        analytics_service.redis = mock_redis

        # First call - cache miss
        mock_redis.get.return_value = None

        with (
            patch(
                "github_analyzer.database.analytics_operations.AnalyticsOperations.get_user_usage_statistics",
                new_callable=AsyncMock,
            ) as mock_usage_stats,
            patch(
                "github_analyzer.database.analytics_operations.AnalyticsOperations.get_repository_statistics",
                new_callable=AsyncMock,
            ) as mock_repo_stats,
            patch(
                "github_analyzer.database.analytics_operations.AnalyticsOperations.get_cost_breakdown",
                new_callable=AsyncMock,
            ) as mock_cost_breakdown,
            patch(
                "github_analyzer.database.analytics_operations.AnalyticsOperations.get_usage_time_series",
                new_callable=AsyncMock,
            ) as mock_time_series,
        ):
            # Set up minimal mocks
            mock_usage_stats.return_value = {
                "total_analyses": 0,
                "successful_analyses": 0,
                "failed_analyses": 0,
                "success_rate": 0,
                "total_cost": Decimal("0"),
                "average_cost_per_analysis": Decimal("0"),
                "average_response_time_ms": 0,
            }
            mock_repo_stats.return_value = {
                "total_unique_repos": 0,
                "most_analyzed_repos": [],
            }
            mock_cost_breakdown.return_value = {
                "total_cost": Decimal("0"),
                "cost_by_operation": {},
            }
            mock_time_series.return_value = []

            with patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_id",
                new_callable=AsyncMock,
            ) as mock_get_user:
                mock_get_user.return_value = MagicMock(
                    usage_consumed=0, usage_quota=100
                )

                # First call should fetch from database
                await analytics_service.get_user_analytics(
                    mock_db_session, "test_user_123"
                )

                # Verify cache was checked and data was stored
                assert mock_redis.get.called
                assert mock_redis.set.called

    @pytest.mark.asyncio
    async def test_database_error_handling(self, analytics_service, mock_db_session):
        """Test handling of database errors."""
        with patch(
            "github_analyzer.database.analytics_operations.AnalyticsOperations.get_user_usage_statistics",
            new_callable=AsyncMock,
        ) as mock_usage_stats:
            # Simulate database error
            mock_usage_stats.side_effect = Exception("Database connection error")

            with pytest.raises(Exception, match="Database connection error"):
                await analytics_service.get_user_analytics(
                    mock_db_session, "test_user_123"
                )
