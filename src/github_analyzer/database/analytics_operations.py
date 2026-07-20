# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Database operations for analytics.

This module provides database queries for analytics data including
user analytics, admin analytics, and time series data.
"""

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import Integer, Numeric, and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from .models import (
    Payment,
    SubscriptionPlan,
    SystemMetric,
    UsageRecord,
    User,
)


class AnalyticsOperations:
    """Database operations for analytics data."""

    @staticmethod
    async def get_user_usage_statistics(
        db: AsyncSession,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get usage statistics for a user.

        Args:
            db: Database session
            user_id: User ID
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dict containing usage statistics
        """
        query = select(
            func.count(UsageRecord.record_id).label("total_analyses"),
            func.sum(func.cast(UsageRecord.success, Integer)).label(
                "successful_analyses"
            ),
            func.sum(func.cast(~UsageRecord.success, Integer)).label("failed_analyses"),
            func.sum(func.cast(UsageRecord.cost_incurred, Numeric)).label("total_cost"),
            func.avg(func.cast(UsageRecord.cost_incurred, Numeric)).label(
                "average_cost"
            ),
            func.avg(UsageRecord.response_time_ms).label("avg_response_time"),
        )

        # Only filter by user_id if provided and not empty (for user-specific analytics)
        if user_id and user_id != "":
            query = query.where(UsageRecord.user_id == user_id)

        if start_date:
            query = query.where(UsageRecord.created_at >= start_date)
        if end_date:
            query = query.where(UsageRecord.created_at <= end_date)

        result = await db.execute(query)
        row = result.one()

        total = row.total_analyses or 0
        successful = row.successful_analyses or 0
        failed = row.failed_analyses or 0

        return {
            "total_analyses": total,
            "successful_analyses": successful,
            "failed_analyses": failed,
            "success_rate": (successful / total * 100) if total > 0 else 0,
            "total_cost": row.total_cost or Decimal("0.00"),
            "average_cost_per_analysis": row.average_cost or Decimal("0.00"),
            "average_response_time_ms": row.avg_response_time or 0,
        }

    @staticmethod
    async def get_repository_statistics(
        db: AsyncSession,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get repository analysis statistics for a user.

        Args:
            db: Database session
            user_id: User ID
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dict containing repository statistics
        """
        # Get unique repositories count
        query = select(
            func.count(func.distinct(UsageRecord.repository_url)).label("unique_repos")
        ).where(
            and_(UsageRecord.user_id == user_id, UsageRecord.repository_url.isnot(None))
        )

        if start_date:
            query = query.where(UsageRecord.created_at >= start_date)
        if end_date:
            query = query.where(UsageRecord.created_at <= end_date)

        result = await db.execute(query)
        unique_repos = result.scalar() or 0

        # Get most analyzed repositories
        repos_query = (
            select(
                UsageRecord.repository_url,
                func.count(UsageRecord.record_id).label("count"),
            )
            .where(
                and_(
                    UsageRecord.user_id == user_id,
                    UsageRecord.repository_url.isnot(None),
                )
            )
            .group_by(UsageRecord.repository_url)
            .order_by(desc("count"))
            .limit(10)
        )

        if start_date:
            repos_query = repos_query.where(UsageRecord.created_at >= start_date)
        if end_date:
            repos_query = repos_query.where(UsageRecord.created_at <= end_date)

        result = await db.execute(repos_query)
        most_analyzed = []
        for row in result:
            repo_url = row.repository_url
            repo_name = repo_url.split("/")[-1] if repo_url else "Unknown"
            most_analyzed.append(
                {
                    "name": repo_name,
                    "url": repo_url,
                    "count": row.count,
                }
            )

        return {
            "total_unique_repos": unique_repos,
            "most_analyzed_repos": most_analyzed,
        }

    @staticmethod
    async def get_usage_time_series(
        db: AsyncSession,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        granularity: str = "day",
    ) -> List[Dict[str, Any]]:
        """
        Get time series data for usage.

        Args:
            db: Database session
            user_id: User ID
            start_date: Start date
            end_date: End date
            granularity: Time granularity (hour, day, week, month)

        Returns:
            List of time series data points
        """
        # Determine date truncation based on granularity
        if granularity == "hour":
            date_trunc = "hour"
        elif granularity == "week":
            date_trunc = "week"
        elif granularity == "month":
            date_trunc = "month"
        else:
            date_trunc = "day"

        # Use raw SQL for date truncation (PostgreSQL specific)
        query = text(
            """
            SELECT
                DATE_TRUNC(:date_trunc, created_at AT TIME ZONE 'UTC') as timestamp,
                COUNT(*) as analyses_count,
                SUM(CAST(cost_incurred AS DECIMAL)) as total_cost
            FROM usage_records
            WHERE user_id = :user_id
                AND created_at >= :start_date
                AND created_at <= :end_date
            GROUP BY DATE_TRUNC(:date_trunc, created_at AT TIME ZONE 'UTC')
            ORDER BY timestamp
        """
        )

        result = await db.execute(
            query,
            {
                "date_trunc": date_trunc,
                "user_id": user_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )

        time_series = []
        for row in result:
            time_series.append(
                {
                    "timestamp": row.timestamp,
                    "analyses_count": row.analyses_count,
                    "total_cost": float(row.total_cost or 0),
                }
            )

        return time_series

    @staticmethod
    async def get_cost_breakdown(
        db: AsyncSession,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get cost breakdown for a user.

        Args:
            db: Database session
            user_id: User ID
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dict containing cost breakdown
        """
        # Get total cost
        query = select(
            func.sum(func.cast(UsageRecord.cost_incurred, Numeric)).label("total_cost")
        ).where(UsageRecord.user_id == user_id)

        if start_date:
            query = query.where(UsageRecord.created_at >= start_date)
        if end_date:
            query = query.where(UsageRecord.created_at <= end_date)

        result = await db.execute(query)
        total_cost = result.scalar() or Decimal("0.00")

        # Get cost by endpoint
        endpoint_query = (
            select(
                UsageRecord.endpoint,
                func.sum(func.cast(UsageRecord.cost_incurred, Numeric)).label("cost"),
            )
            .where(UsageRecord.user_id == user_id)
            .group_by(UsageRecord.endpoint)
        )

        if start_date:
            endpoint_query = endpoint_query.where(UsageRecord.created_at >= start_date)
        if end_date:
            endpoint_query = endpoint_query.where(UsageRecord.created_at <= end_date)

        result = await db.execute(endpoint_query)
        cost_by_operation = {}
        for row in result:
            operation = row.endpoint.replace("/api/v1/", "").replace("/", "_")
            cost_by_operation[operation] = row.cost or Decimal("0.00")

        return {
            "total_cost": total_cost,
            "cost_by_operation": cost_by_operation,
        }

    @staticmethod
    async def get_usage_history(
        db: AsyncSession,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        per_page: int = 50,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get paginated usage history for a user.

        Args:
            db: Database session
            user_id: User ID
            start_date: Optional start date filter
            end_date: Optional end date filter
            page: Page number (1-based)
            per_page: Items per page

        Returns:
            Tuple of (usage history list, total count)
        """
        # Build base query
        base_query = select(UsageRecord).where(UsageRecord.user_id == user_id)

        if start_date:
            base_query = base_query.where(UsageRecord.created_at >= start_date)
        if end_date:
            base_query = base_query.where(UsageRecord.created_at <= end_date)

        # Get total count
        count_query = select(func.count()).select_from(base_query.subquery())
        count_result = await db.execute(count_query)
        total_count = count_result.scalar() or 0

        # Get paginated results
        offset = (page - 1) * per_page
        query = (
            base_query.order_by(desc(UsageRecord.created_at))
            .offset(offset)
            .limit(per_page)
        )

        result = await db.execute(query)
        records = result.scalars().all()

        history = []
        for record in records:
            repo_name = "Unknown"
            if record.repository_url:
                repo_name = record.repository_url.split("/")[-1]

            history.append(
                {
                    "timestamp": record.created_at,
                    "repository_url": record.repository_url,
                    "repository_name": repo_name,
                    "success": record.success,
                    "cost": Decimal(record.cost_incurred),
                    "tokens_used": record.tokens_consumed,
                    "processing_time": record.response_time_ms
                    / 1000.0,  # Convert to seconds
                    "error_message": record.error_message,
                }
            )

        return history, total_count

    @staticmethod
    async def get_system_metrics(
        db: AsyncSession,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get system-wide metrics for admin dashboard.

        Args:
            db: Database session
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dict containing system metrics
        """
        # Get API request metrics
        query = select(
            func.count(UsageRecord.record_id).label("total_requests"),
            func.avg(UsageRecord.response_time_ms).label("avg_response_time"),
            func.sum(func.cast(~UsageRecord.success, Integer)).label("failed_requests"),
        )

        if start_date:
            query = query.where(UsageRecord.created_at >= start_date)
        if end_date:
            query = query.where(UsageRecord.created_at <= end_date)

        result = await db.execute(query)
        row = result.one()

        total_requests = row.total_requests or 0
        failed_requests = row.failed_requests or 0
        error_rate = (
            (failed_requests / total_requests * 100) if total_requests > 0 else 0
        )

        # Get active users count
        active_users_query = select(func.count(func.distinct(UsageRecord.user_id)))

        if start_date:
            active_users_query = active_users_query.where(
                UsageRecord.created_at >= start_date
            )
        if end_date:
            active_users_query = active_users_query.where(
                UsageRecord.created_at <= end_date
            )

        active_users_result = await db.execute(active_users_query)
        active_users = active_users_result.scalar() or 0

        # Get cache metrics from SystemMetric table
        cache_metrics = await AnalyticsOperations._get_latest_metric(
            db, "cache_hit_rate", start_date, end_date
        )
        cache_hit_rate = (
            float(cache_metrics.get("value", 85.0)) if cache_metrics else 85.0
        )

        # Determine system health based on error rate and response time
        avg_response_time = row.avg_response_time or 0
        if error_rate > 5 or avg_response_time > 1000:
            system_health = "degraded"
        elif error_rate > 2 or avg_response_time > 500:
            system_health = "warning"
        else:
            system_health = "healthy"

        return {
            "api_requests": total_requests,
            "average_response_time": avg_response_time / 1000.0,  # Convert to seconds
            "error_rate": error_rate,
            "cache_hit_rate": cache_hit_rate,
            "active_users": active_users,
            "system_health": system_health,
        }

    @staticmethod
    async def get_revenue_analytics(
        db: AsyncSession,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get revenue analytics for admin dashboard.

        Args:
            db: Database session
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dict containing revenue analytics
        """
        # Get total revenue from payments
        query = select(func.sum(Payment.amount).label("total_revenue")).where(
            Payment.status == "succeeded"
        )

        if start_date:
            query = query.where(Payment.created_at >= start_date)
        if end_date:
            query = query.where(Payment.created_at <= end_date)

        result = await db.execute(query)
        revenue_value = result.scalar() or 0
        total_revenue = Decimal(revenue_value) / 100  # Convert cents to dollars

        # Get revenue by subscription plan
        plan_query = (
            select(
                User.subscription_plan,
                func.count(User.user_id).label("user_count"),
            )
            .where(User.subscription_status == "active")
            .group_by(User.subscription_plan)
        )

        plan_result = await db.execute(plan_query)

        # Define plan prices (in dollars)
        plan_prices = {
            SubscriptionPlan.FREE: Decimal("0"),
            SubscriptionPlan.BASIC: Decimal("9.99"),
            SubscriptionPlan.PROFESSIONAL: Decimal("29.99"),
            SubscriptionPlan.ENTERPRISE: Decimal("99.99"),
        }

        revenue_by_plan = {}
        monthly_recurring_revenue = Decimal("0")

        for row in plan_result:
            plan = row.subscription_plan
            user_count = row.user_count
            monthly_revenue = plan_prices.get(plan, Decimal("0")) * user_count
            revenue_by_plan[plan.value] = monthly_revenue
            monthly_recurring_revenue += monthly_revenue

        annual_recurring_revenue = monthly_recurring_revenue * 12

        # Calculate churn rate (users who canceled in the period)
        churn_query = select(func.count(User.user_id)).where(
            User.subscription_status == "canceled"
        )

        if start_date:
            churn_query = churn_query.where(User.updated_at >= start_date)
        if end_date:
            churn_query = churn_query.where(User.updated_at <= end_date)

        churn_result = await db.execute(churn_query)
        churned_users = churn_result.scalar() or 0

        total_users_query = select(func.count(User.user_id))
        total_users_result = await db.execute(total_users_query)
        total_users = total_users_result.scalar() or 1

        churn_rate = (churned_users / total_users * 100) if total_users > 0 else 0

        # Calculate conversion rate (free to paid)
        paid_users_query = select(func.count(User.user_id)).where(
            User.subscription_plan != SubscriptionPlan.FREE
        )
        paid_users_result = await db.execute(paid_users_query)
        paid_users = paid_users_result.scalar() or 0

        conversion_rate = (paid_users / total_users * 100) if total_users > 0 else 0

        return {
            "total_revenue": total_revenue,
            "monthly_recurring_revenue": monthly_recurring_revenue,
            "annual_recurring_revenue": annual_recurring_revenue,
            "revenue_by_plan": revenue_by_plan,
            "churn_rate": churn_rate,
            "conversion_rate": conversion_rate,
        }

    @staticmethod
    async def get_user_behavior_analytics(
        db: AsyncSession,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get user behavior analytics for admin dashboard.

        Args:
            db: Database session
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dict containing user behavior analytics
        """
        # Get average analyses per user
        query = select(
            func.count(UsageRecord.record_id).label("total_analyses"),
            func.count(func.distinct(UsageRecord.user_id)).label("unique_users"),
        )

        if start_date:
            query = query.where(UsageRecord.created_at >= start_date)
        if end_date:
            query = query.where(UsageRecord.created_at <= end_date)

        result = await db.execute(query)
        row = result.one()

        total_analyses = row.total_analyses or 0
        unique_users = row.unique_users or 1
        avg_analyses_per_user = total_analyses / unique_users if unique_users > 0 else 0

        # Get user retention rate (users active in both current and previous period)
        if start_date and end_date:
            period_length = end_date - start_date
            previous_start = start_date - period_length
            previous_end = start_date

            # Users active in previous period
            prev_query = select(func.count(func.distinct(UsageRecord.user_id))).where(
                and_(
                    UsageRecord.created_at >= previous_start,
                    UsageRecord.created_at < previous_end,
                )
            )
            prev_result = await db.execute(prev_query)
            prev_users = prev_result.scalar() or 0

            # Users active in both periods
            retention_query = text(
                """
                SELECTCOUNT(DISTINCT current.user_id)
                FROM (
                    SELECTDISTINCT user_id
                    FROM usage_records
                    WHERE created_at >= :start_date AND created_at <= :end_date
                ) current
                INNER JOIN (
                    SELECTDISTINCT user_id
                    FROM usage_records
                    WHERE created_at >= :prev_start AND created_at < :prev_end
                ) previous ON current.user_id = previous.user_id
            """
            )

            retention_result = await db.execute(
                retention_query,
                {
                    "start_date": start_date,
                    "end_date": end_date,
                    "prev_start": previous_start,
                    "prev_end": previous_end,
                },
            )
            retained_users = retention_result.scalar() or 0

            retention_rate = (
                (retained_users / prev_users * 100) if prev_users > 0 else 0
            )
        else:
            retention_rate = 85.0  # Default retention rate

        # Get feature adoption (based on endpoints)
        feature_query = select(
            UsageRecord.endpoint,
            func.count(func.distinct(UsageRecord.user_id)).label("users"),
        ).group_by(UsageRecord.endpoint)

        if start_date:
            feature_query = feature_query.where(UsageRecord.created_at >= start_date)
        if end_date:
            feature_query = feature_query.where(UsageRecord.created_at <= end_date)

        feature_result = await db.execute(feature_query)

        feature_adoption = {}
        for row in feature_result.fetchall():  # type: ignore[assignment]
            feature = row[0].replace("/api/v1/", "").replace("/", "_")
            adoption_rate = (row[1] / unique_users * 100) if unique_users > 0 else 0
            feature_adoption[feature] = adoption_rate

        # Get user segments
        segments_query = select(
            User.subscription_plan,
            func.count(User.user_id).label("count"),
        ).group_by(User.subscription_plan)

        segments_result = await db.execute(segments_query)
        user_segments: Dict[str, int] = {}
        for row in segments_result.fetchall():  # type: ignore[assignment]
            segment = "paid" if row[0] != SubscriptionPlan.FREE else "free"
            user_segments[segment] = user_segments.get(segment, 0) + row[1]

        return {
            "average_analyses_per_user": avg_analyses_per_user,
            "user_retention_rate": retention_rate,
            "feature_adoption": feature_adoption,
            "user_segments": user_segments,
        }

    @staticmethod
    async def _get_latest_metric(
        db: AsyncSession,
        metric_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get the latest value for a specific metric.

        Args:
            db: Database session
            metric_name: Name of the metric
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dict containing metric value or None
        """
        query = (
            select(SystemMetric)
            .where(SystemMetric.metric_name == metric_name)
            .order_by(desc(SystemMetric.timestamp))
        )

        if start_date:
            query = query.where(SystemMetric.timestamp >= start_date)
        if end_date:
            query = query.where(SystemMetric.timestamp <= end_date)

        query = query.limit(1)

        result = await db.execute(query)
        metric = result.scalar_one_or_none()

        if metric:
            try:
                value = json.loads(metric.metric_value)
                return {"value": value, "timestamp": metric.timestamp}
            except json.JSONDecodeError:
                return None

        return None

    @staticmethod
    async def export_analytics_data(
        db: AsyncSession,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Export analytics data for a user.

        Args:
            db: Database session
            user_id: User ID
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dict containing all analytics data for export
        """
        # Get all analytics data
        usage_stats = await AnalyticsOperations.get_user_usage_statistics(
            db, user_id, start_date, end_date
        )
        repo_stats = await AnalyticsOperations.get_repository_statistics(
            db, user_id, start_date, end_date
        )
        cost_breakdown = await AnalyticsOperations.get_cost_breakdown(
            db, user_id, start_date, end_date
        )

        # Get time series data (daily for export)
        if not start_date:
            start_date = datetime.now(timezone.utc) - timedelta(days=30)
        if not end_date:
            end_date = datetime.now(timezone.utc)

        time_series = await AnalyticsOperations.get_usage_time_series(
            db, user_id, start_date, end_date, "day"
        )

        # Get recent usage history
        history, _ = await AnalyticsOperations.get_usage_history(
            db, user_id, start_date, end_date, 1, 100
        )

        return {
            "export_date": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "period": {
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
            },
            "usage_statistics": usage_stats,
            "repository_statistics": repo_stats,
            "cost_breakdown": cost_breakdown,
            "time_series_data": time_series,
            "recent_activity": history,
        }
