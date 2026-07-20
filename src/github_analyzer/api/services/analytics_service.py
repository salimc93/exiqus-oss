# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Analytics service for user and admin analytics.

This service provides real analytics data from the database,
replacing the previous mock data implementation.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ...database.analytics_operations import AnalyticsOperations
from ..models.analytics import (
    AdminAnalytics,
    AnalyticsFilter,
    CostBreakdown,
    RepositoryStatistics,
    RevenueAnalytics,
    SystemMetrics,
    TimeSeries,
    TimeSeriesDataPoint,
    UsageHistory,
    UsageHistoryItem,
    UsageStatistics,
    UserAnalytics,
    UserBehaviorAnalytics,
)
from .redis_service import RedisService

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Analytics service that provides real data from the database."""

    def __init__(self, redis_service: Optional[RedisService] = None):
        """Initialize analytics service."""
        self.redis = redis_service or RedisService()
        self.cache_ttl = 300  # 5 minutes cache for analytics

    def _get_secure_cache_key(
        self, prefix: str, user_id: str, params: Dict[str, Any]
    ) -> str:
        """
        Generate a secure cache key using SHA256.

        Args:
            prefix: Cache key prefix
            user_id: User ID
            params: Parameters to include in the cache key

        Returns:
            Secure cache key
        """
        # Create a deterministic string from parameters
        param_str = json.dumps(params, sort_keys=True, default=str)
        key_data = f"{prefix}:{user_id}:{param_str}"

        # Use SHA256 for secure hashing
        hash_digest = hashlib.sha256(key_data.encode()).hexdigest()
        return f"{prefix}:{user_id}:{hash_digest[:16]}"

    async def get_user_analytics(
        self,
        db: AsyncSession,
        user_id: str,
        filter_params: Optional[AnalyticsFilter] = None,
    ) -> UserAnalytics:
        """
        Get user analytics data from the database.

        Args:
            db: Database session
            user_id: User ID
            filter_params: Optional analytics filters

        Returns:
            UserAnalytics object with real data

        Raises:
            ValueError: If user_id is invalid
            Exception: For database errors
        """
        try:
            # Validate user_id
            if not user_id or not isinstance(user_id, str):
                raise ValueError("Invalid user_id provided")

            # Set default filter params
            if not filter_params:
                filter_params = AnalyticsFilter(
                    start_date=datetime.now(timezone.utc) - timedelta(days=30),
                    end_date=datetime.now(timezone.utc),
                )

            # Validate date range
            if filter_params.start_date and filter_params.end_date:
                if filter_params.start_date > filter_params.end_date:
                    raise ValueError("Start date cannot be after end date")

                # Prevent querying future dates
                now = datetime.now(timezone.utc)
                if filter_params.end_date > now:
                    filter_params.end_date = now

            # Generate secure cache key
            cache_params = {
                "start_date": (
                    filter_params.start_date.isoformat()
                    if filter_params.start_date
                    else None
                ),
                "end_date": (
                    filter_params.end_date.isoformat()
                    if filter_params.end_date
                    else None
                ),
            }
            cache_key = self._get_secure_cache_key(
                "user_analytics", user_id, cache_params
            )

            # Try to get from cache
            try:
                cached_data = await self.redis.get(cache_key)
                if cached_data:
                    logger.debug(f"Cache hit for user analytics: {user_id}")
                    return UserAnalytics.model_validate_json(cached_data)
            except Exception as e:
                logger.warning(f"Cache retrieval failed: {e}")

            # Get data from database
            logger.info(f"Fetching user analytics from database for user: {user_id}")

            # Get usage statistics
            usage_stats_data = await AnalyticsOperations.get_user_usage_statistics(
                db, user_id, filter_params.start_date, filter_params.end_date
            )

            usage_stats = UsageStatistics(
                total_analyses=usage_stats_data["total_analyses"],
                successful_analyses=usage_stats_data["successful_analyses"],
                failed_analyses=usage_stats_data["failed_analyses"],
                success_rate=usage_stats_data["success_rate"],
                total_cost=usage_stats_data["total_cost"],
                average_cost_per_analysis=usage_stats_data["average_cost_per_analysis"],
            )

            # Get repository statistics
            repo_stats_data = await AnalyticsOperations.get_repository_statistics(
                db, user_id, filter_params.start_date, filter_params.end_date
            )

            repository_stats = RepositoryStatistics(
                total_unique_repos=repo_stats_data["total_unique_repos"],
                most_analyzed_repos=repo_stats_data["most_analyzed_repos"],
                repository_types={},  # TODO: Implement repository type detection
                language_distribution={},  # TODO: Implement language detection from analysis results
            )

            # Get cost breakdown
            cost_data = await AnalyticsOperations.get_cost_breakdown(
                db, user_id, filter_params.start_date, filter_params.end_date
            )

            # Get time series data for daily costs
            start_date = filter_params.start_date or datetime.now(
                timezone.utc
            ) - timedelta(days=7)
            end_date = filter_params.end_date or datetime.now(timezone.utc)

            time_series_data = await AnalyticsOperations.get_usage_time_series(
                db, user_id, start_date, end_date, "day"
            )

            daily_costs = []
            for point in time_series_data:
                daily_costs.append(
                    TimeSeriesDataPoint(
                        timestamp=point["timestamp"],
                        value=float(point["total_cost"]),
                        label=None,
                    )
                )

            cost_breakdown = CostBreakdown(
                period=self._format_period(filter_params),
                total_cost=cost_data["total_cost"],
                cost_by_model={
                    "claude-3-haiku-20240307": cost_data["total_cost"]
                },  # TODO: Track model usage
                cost_by_operation=cost_data["cost_by_operation"],
                daily_costs=daily_costs,
            )

            # Get usage trend
            usage_trend_data = []
            for point in time_series_data:
                usage_trend_data.append(
                    TimeSeriesDataPoint(
                        timestamp=point["timestamp"],
                        value=float(point["analyses_count"]),
                        label=None,
                    )
                )

            usage_trend = TimeSeries(
                name="Usage Trend",
                data=usage_trend_data,
                unit="analyses",
            )

            # Get quota usage from user data
            from ...database.operations import UserOperations

            user = await UserOperations.get_user_by_id(db, user_id)

            quota_usage = {
                "current_month_usage": user.usage_count if user else 0,
                "plan_limits": {
                    "monthly_analysis_limit": user.usage_quota if user else 100
                },
                "usage_percentage": (
                    (user.usage_count / user.usage_quota * 100)
                    if user and user.usage_quota > 0
                    else 0
                ),
            }

            # Create UserAnalytics object
            analytics = UserAnalytics(
                user_id=user_id,
                period=self._format_period(filter_params),
                usage_stats=usage_stats,
                repository_stats=repository_stats,
                cost_breakdown=cost_breakdown,
                usage_trend=usage_trend,
                quota_usage=quota_usage,
            )

            # Cache the result
            try:
                await self.redis.set(
                    cache_key, analytics.model_dump_json(), ttl=self.cache_ttl
                )
                logger.debug(f"Cached user analytics for: {user_id}")
            except Exception as e:
                logger.warning(f"Failed to cache user analytics: {e}")

            return analytics

        except ValueError as e:
            logger.error(f"Validation error in get_user_analytics: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching user analytics for {user_id}: {e}")
            raise

    async def get_usage_history(
        self,
        db: AsyncSession,
        user_id: str,
        filter_params: Optional[AnalyticsFilter] = None,
        page: int = 1,
        per_page: int = 50,
    ) -> UsageHistory:
        """
        Get usage history for a user.

        Args:
            db: Database session
            user_id: User ID
            filter_params: Optional analytics filters
            page: Page number (1-based)
            per_page: Items per page

        Returns:
            UsageHistory object with paginated results
        """
        try:
            # Validate inputs
            if not user_id or not isinstance(user_id, str):
                raise ValueError("Invalid user_id provided")

            if page < 1:
                raise ValueError("Page number must be >= 1")

            if per_page < 1 or per_page > 100:
                raise ValueError("Items per page must be between 1 and 100")

            # Get history from database
            history_data, total_count = await AnalyticsOperations.get_usage_history(
                db,
                user_id,
                filter_params.start_date if filter_params else None,
                filter_params.end_date if filter_params else None,
                page,
                per_page,
            )

            # Convert to UsageHistoryItem objects
            items = []
            for record in history_data:
                items.append(
                    UsageHistoryItem(
                        timestamp=record["timestamp"],
                        repository_url=record["repository_url"],
                        repository_name=record["repository_name"],
                        success=record["success"],
                        cost=record["cost"],
                        tokens_used=record["tokens_used"],
                        model_used="claude-3-haiku-20240307",  # TODO: Track actual model used
                        processing_time=record["processing_time"],
                    )
                )

            # Get summary statistics for the filtered period
            stats_data = await AnalyticsOperations.get_user_usage_statistics(
                db,
                user_id,
                filter_params.start_date if filter_params else None,
                filter_params.end_date if filter_params else None,
            )

            summary = UsageStatistics(
                total_analyses=stats_data["total_analyses"],
                successful_analyses=stats_data["successful_analyses"],
                failed_analyses=stats_data["failed_analyses"],
                success_rate=stats_data["success_rate"],
                total_cost=stats_data["total_cost"],
                average_cost_per_analysis=stats_data["average_cost_per_analysis"],
            )

            return UsageHistory(
                items=items,
                total_count=total_count,
                page=page,
                per_page=per_page,
                has_next=(page * per_page) < total_count,
                summary=summary,
            )

        except ValueError as e:
            logger.error(f"Validation error in get_usage_history: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching usage history for {user_id}: {e}")
            raise

    async def get_admin_analytics(
        self,
        db: AsyncSession,
        filter_params: Optional[AnalyticsFilter] = None,
    ) -> AdminAnalytics:
        """
        Get admin analytics data from the database.

        Args:
            db: Database session
            filter_params: Optional analytics filters

        Returns:
            AdminAnalytics object with real data
        """
        try:
            # Set default filter params
            if not filter_params:
                filter_params = AnalyticsFilter.model_validate({})

            # Generate cache key
            cache_params = {
                "start_date": (
                    filter_params.start_date.isoformat()
                    if filter_params.start_date
                    else None
                ),
                "end_date": (
                    filter_params.end_date.isoformat()
                    if filter_params.end_date
                    else None
                ),
            }
            cache_key = self._get_secure_cache_key(
                "admin_analytics", "admin", cache_params
            )

            # Try to get from cache
            try:
                cached_data = await self.redis.get(cache_key)
                if cached_data:
                    logger.debug("Cache hit for admin analytics")
                    return AdminAnalytics.model_validate_json(cached_data)
            except Exception as e:
                logger.warning(f"Cache retrieval failed: {e}")

            logger.info("Fetching admin analytics from database")

            # Get system metrics
            system_data = await AnalyticsOperations.get_system_metrics(
                db, filter_params.start_date, filter_params.end_date
            )

            system_metrics = SystemMetrics(
                api_requests=system_data["api_requests"],
                average_response_time=system_data["average_response_time"],
                error_rate=system_data["error_rate"],
                cache_hit_rate=system_data["cache_hit_rate"],
                active_users=system_data["active_users"],
                system_health=system_data["system_health"],
            )

            # Get revenue analytics
            revenue_data = await AnalyticsOperations.get_revenue_analytics(
                db, filter_params.start_date, filter_params.end_date
            )

            # Get revenue trend time series
            # For revenue trend, we'll use payments data
            from sqlalchemy import func, select

            from ...database.models import Payment

            revenue_query = (
                select(
                    func.date_trunc("day", Payment.created_at).label("date"),
                    func.sum(Payment.amount).label("revenue"),
                )
                .where(Payment.status == "succeeded")
                .group_by("date")
                .order_by("date")
            )

            if filter_params.start_date:
                revenue_query = revenue_query.where(
                    Payment.created_at >= filter_params.start_date
                )
            if filter_params.end_date:
                revenue_query = revenue_query.where(
                    Payment.created_at <= filter_params.end_date
                )

            revenue_result = await db.execute(revenue_query)

            revenue_trend_data = []
            for row in revenue_result:
                revenue_trend_data.append(
                    TimeSeriesDataPoint(
                        timestamp=row.date,
                        value=(
                            float(row.revenue / 100) if row.revenue else 0.0
                        ),  # Convert cents to dollars
                        label=None,
                    )
                )

            revenue_analytics = RevenueAnalytics(
                total_revenue=revenue_data["total_revenue"],
                monthly_recurring_revenue=revenue_data["monthly_recurring_revenue"],
                annual_recurring_revenue=revenue_data["annual_recurring_revenue"],
                revenue_by_plan=revenue_data["revenue_by_plan"],
                revenue_trend=TimeSeries(
                    name="Revenue Trend",
                    data=revenue_trend_data,
                    unit="USD",
                ),
                churn_rate=revenue_data["churn_rate"],
                conversion_rate=revenue_data["conversion_rate"],
            )

            # Get user behavior analytics
            behavior_data = await AnalyticsOperations.get_user_behavior_analytics(
                db, filter_params.start_date, filter_params.end_date
            )

            # Get activity patterns (hourly distribution)
            from ...database.models import UsageRecord

            activity_query = (
                select(
                    func.extract("hour", UsageRecord.created_at).label("hour"),
                    func.count(UsageRecord.record_id).label("count"),
                )
                .group_by("hour")
                .order_by("hour")
            )

            if filter_params.start_date:
                activity_query = activity_query.where(
                    UsageRecord.created_at >= filter_params.start_date
                )
            if filter_params.end_date:
                activity_query = activity_query.where(
                    UsageRecord.created_at <= filter_params.end_date
                )

            activity_result = await db.execute(activity_query)

            activity_pattern_data = []
            now = datetime.now(timezone.utc)
            for hour in range(24):
                timestamp = now.replace(hour=hour, minute=0, second=0, microsecond=0)
                count = 0
                for row in activity_result.fetchall():
                    if row[0] == hour:
                        count = row[1]
                        break
                activity_pattern_data.append(
                    TimeSeriesDataPoint(
                        timestamp=timestamp, value=float(count), label=None
                    )
                )

            user_behavior = UserBehaviorAnalytics(
                average_analyses_per_user=behavior_data["average_analyses_per_user"],
                user_retention_rate=behavior_data["user_retention_rate"],
                feature_adoption=behavior_data["feature_adoption"],
                user_segments=behavior_data["user_segments"],
                activity_patterns=TimeSeries(
                    name="Activity Patterns",
                    data=activity_pattern_data,
                    unit="activities",
                ),
            )

            # Get overall usage statistics - pass empty string for all users
            usage_stats_data = await AnalyticsOperations.get_user_usage_statistics(
                db,
                "",
                filter_params.start_date,
                filter_params.end_date,  # Empty string for all users
            )

            usage_stats = UsageStatistics(
                total_analyses=usage_stats_data["total_analyses"],
                successful_analyses=usage_stats_data["successful_analyses"],
                failed_analyses=usage_stats_data["failed_analyses"],
                success_rate=usage_stats_data["success_rate"],
                total_cost=usage_stats_data["total_cost"],
                average_cost_per_analysis=usage_stats_data["average_cost_per_analysis"],
            )

            # Get growth metrics
            from ...database.models import User
            from ...database.operations import UserOperations

            # New users in period
            new_users_query = select(func.count(User.user_id)).select_from(User)
            if filter_params.start_date:
                new_users_query = new_users_query.where(
                    User.created_at >= filter_params.start_date
                )
            if filter_params.end_date:
                new_users_query = new_users_query.where(
                    User.created_at <= filter_params.end_date
                )

            new_users_result = await db.execute(new_users_query)
            new_users = new_users_result.scalar() or 0

            total_users = await UserOperations.get_user_count(db)

            # Calculate growth rates (simplified for now)
            growth_metrics = {
                "new_users": new_users,
                "user_growth_rate": (
                    (new_users / total_users * 100) if total_users > 0 else 0
                ),
                "total_analyses": usage_stats_data["total_analyses"],
                "analysis_growth_rate": 15.0,  # TODO: Calculate actual growth rate
                "market_penetration": 2.5,  # TODO: Calculate based on target market
            }

            # Create AdminAnalytics object
            analytics = AdminAnalytics(
                period=self._format_period(filter_params),
                system_metrics=system_metrics,
                revenue_analytics=revenue_analytics,
                user_behavior=user_behavior,
                usage_stats=usage_stats,
                growth_metrics=growth_metrics,
            )

            # Cache the result
            try:
                await self.redis.set(
                    cache_key, analytics.model_dump_json(), ttl=self.cache_ttl
                )
                logger.debug("Cached admin analytics")
            except Exception as e:
                logger.warning(f"Failed to cache admin analytics: {e}")

            return analytics

        except Exception as e:
            logger.error(f"Error fetching admin analytics: {e}")
            raise

    async def export_analytics(
        self,
        db: AsyncSession,
        user_id: str,
        filter_params: Optional[AnalyticsFilter] = None,
    ) -> Dict[str, Any]:
        """
        Export analytics data for a user.

        Args:
            db: Database session
            user_id: User ID
            filter_params: Optional analytics filters

        Returns:
            Dict containing exported analytics data
        """
        try:
            # Validate user_id
            if not user_id or not isinstance(user_id, str):
                raise ValueError("Invalid user_id provided")

            # Get export data from database
            export_data = await AnalyticsOperations.export_analytics_data(
                db,
                user_id,
                filter_params.start_date if filter_params else None,
                filter_params.end_date if filter_params else None,
            )

            return export_data

        except ValueError as e:
            logger.error(f"Validation error in export_analytics: {e}")
            raise
        except Exception as e:
            logger.error(f"Error exporting analytics for {user_id}: {e}")
            raise

    async def get_usage_analytics(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Get usage analytics across all users.

        Args:
            db: Database session

        Returns:
            Dict containing usage analytics data
        """
        try:
            from sqlalchemy import func, select

            from ...database.models import SubscriptionPlan, User

            # Get total users
            total_users_result = await db.execute(select(func.count(User.user_id)))
            total_users = total_users_result.scalar() or 0

            # Get users by plan
            plan_stats = {}
            for plan in SubscriptionPlan:
                plan_result = await db.execute(
                    select(
                        func.count(User.user_id),
                        func.sum(User.usage_count),
                    ).where(User.subscription_plan == plan)
                )
                user_count, total_usage = plan_result.one()
                plan_stats[plan.value] = {
                    "users": user_count or 0,
                    "total_usage": total_usage or 0,
                }

            # Get users with high usage (>80% of quota)
            high_usage_query = select(
                User.user_id,
                User.usage_count,
                User.usage_quota,
                ((User.usage_count * 100.0) / User.usage_quota).label(
                    "usage_percentage"
                ),
            ).where(
                User.usage_quota > 0,
                (User.usage_count * 100.0 / User.usage_quota) > 80,
            )

            high_usage_result = await db.execute(high_usage_query)
            high_usage_users = []
            for row in high_usage_result:
                high_usage_users.append(
                    {
                        "user_id": row.user_id,
                        "usage_percentage": round(row.usage_percentage, 2),
                    }
                )

            # Get users with exhausted quota
            exhausted_query = select(func.count(User.user_id)).where(
                User.usage_count >= User.usage_quota, User.usage_quota > 0
            )
            exhausted_result = await db.execute(exhausted_query)
            quota_exhausted_users = exhausted_result.scalar() or 0

            return {
                "total_users": total_users,
                "by_plan": plan_stats,
                "high_usage_users": high_usage_users[:10],  # Top 10
                "quota_exhausted_users": quota_exhausted_users,
            }

        except Exception as e:
            logger.error(f"Error fetching usage analytics: {e}")
            raise

    def _format_period(self, filter_params: AnalyticsFilter) -> str:
        """Format the analytics period for display."""
        if filter_params.start_date and filter_params.end_date:
            return f"{filter_params.start_date.strftime('%Y-%m-%d')} to {filter_params.end_date.strftime('%Y-%m-%d')}"
        elif filter_params.start_date:
            return f"Since {filter_params.start_date.strftime('%Y-%m-%d')}"
        elif filter_params.end_date:
            return f"Until {filter_params.end_date.strftime('%Y-%m-%d')}"
        else:
            return "All time"
