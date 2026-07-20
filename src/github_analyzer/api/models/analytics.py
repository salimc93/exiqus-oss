# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Analytics data models and response schemas.

This module defines Pydantic models for analytics endpoints,
including user analytics, admin dashboards, and time-series data.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TimeSeriesDataPoint(BaseModel):
    """Single data point in a time series."""

    timestamp: datetime = Field(..., description="Point in time")
    value: float = Field(..., description="Metric value at this time")
    label: Optional[str] = Field(None, description="Optional label for the data point")


class TimeSeries(BaseModel):
    """Time series data for charts and graphs."""

    name: str = Field(..., description="Series name")
    data: List[TimeSeriesDataPoint] = Field(..., description="Time series data points")
    unit: Optional[str] = Field(None, description="Unit of measurement")


class UsageStatistics(BaseModel):
    """User or system usage statistics."""

    total_analyses: int = Field(..., description="Total number of analyses")
    successful_analyses: int = Field(..., description="Successful analyses count")
    failed_analyses: int = Field(..., description="Failed analyses count")
    success_rate: float = Field(..., description="Success rate percentage")
    total_cost: Decimal = Field(..., description="Total cost incurred")
    average_cost_per_analysis: Decimal = Field(
        ..., description="Average cost per analysis"
    )


class RepositoryStatistics(BaseModel):
    """Statistics about analyzed repositories."""

    total_unique_repos: int = Field(..., description="Unique repositories analyzed")
    most_analyzed_repos: List[Dict[str, Any]] = Field(
        ..., description="Most frequently analyzed repositories"
    )
    repository_types: Dict[str, int] = Field(
        ..., description="Breakdown by repository type"
    )
    language_distribution: Dict[str, int] = Field(
        ..., description="Programming language distribution"
    )


class CostBreakdown(BaseModel):
    """Detailed cost breakdown."""

    period: str = Field(..., description="Time period for the breakdown")
    total_cost: Decimal = Field(..., description="Total cost for the period")
    cost_by_model: Dict[str, Decimal] = Field(
        ..., description="Cost breakdown by AI model"
    )
    cost_by_operation: Dict[str, Decimal] = Field(
        ..., description="Cost breakdown by operation type"
    )
    daily_costs: List[TimeSeriesDataPoint] = Field(
        ..., description="Daily cost time series"
    )


class UserAnalytics(BaseModel):
    """Complete user analytics dashboard data."""

    user_id: str = Field(..., description="User ID")
    period: str = Field(..., description="Analytics period")
    usage_stats: UsageStatistics = Field(..., description="Usage statistics")
    repository_stats: RepositoryStatistics = Field(
        ..., description="Repository analysis statistics"
    )
    cost_breakdown: CostBreakdown = Field(..., description="Cost analysis")
    usage_trend: TimeSeries = Field(..., description="Usage trend over time")
    quota_usage: Dict[str, Any] = Field(..., description="Current quota usage")


class SystemMetrics(BaseModel):
    """System-wide performance metrics."""

    api_requests: int = Field(..., description="Total API requests")
    average_response_time: float = Field(..., description="Average response time in ms")
    error_rate: float = Field(..., description="Error rate percentage")
    cache_hit_rate: float = Field(..., description="Cache hit rate percentage")
    active_users: int = Field(..., description="Currently active users")
    system_health: str = Field(..., description="Overall system health status")


class RevenueAnalytics(BaseModel):
    """Revenue and subscription analytics."""

    total_revenue: Decimal = Field(..., description="Total revenue")
    monthly_recurring_revenue: Decimal = Field(..., description="MRR")
    annual_recurring_revenue: Decimal = Field(..., description="ARR")
    revenue_by_plan: Dict[str, Decimal] = Field(
        ..., description="Revenue breakdown by subscription plan"
    )
    revenue_trend: TimeSeries = Field(..., description="Revenue trend over time")
    churn_rate: float = Field(..., description="Customer churn rate")
    conversion_rate: float = Field(..., description="Free to paid conversion rate")


class UserBehaviorAnalytics(BaseModel):
    """User behavior patterns and insights."""

    average_analyses_per_user: float = Field(
        ..., description="Average analyses per user"
    )
    user_retention_rate: float = Field(..., description="User retention rate")
    feature_adoption: Dict[str, float] = Field(
        ..., description="Feature adoption rates"
    )
    user_segments: Dict[str, int] = Field(..., description="User segmentation data")
    activity_patterns: TimeSeries = Field(
        ..., description="User activity patterns over time"
    )


class AdminAnalytics(BaseModel):
    """Complete admin analytics dashboard data."""

    period: str = Field(..., description="Analytics period")
    system_metrics: SystemMetrics = Field(..., description="System performance metrics")
    revenue_analytics: RevenueAnalytics = Field(..., description="Revenue analytics")
    user_behavior: UserBehaviorAnalytics = Field(
        ..., description="User behavior analytics"
    )
    usage_stats: UsageStatistics = Field(..., description="Overall usage statistics")
    growth_metrics: Dict[str, Any] = Field(..., description="Growth metrics")


class AnalyticsFilter(BaseModel):
    """Filter parameters for analytics queries."""

    start_date: Optional[datetime] = Field(None, description="Start date for analytics")
    end_date: Optional[datetime] = Field(None, description="End date for analytics")
    time_granularity: str = Field(
        default="daily",
        description="Time granularity: hourly, daily, weekly, monthly",
    )
    repository_id: Optional[str] = Field(
        default=None, description="Filter by specific repository"
    )
    limit: int = Field(default=100, description="Limit for results", ge=1, le=1000)


class UsageHistoryItem(BaseModel):
    """Single item in usage history."""

    timestamp: datetime = Field(..., description="When the analysis occurred")
    repository_url: str = Field(..., description="Analyzed repository URL")
    repository_name: str = Field(..., description="Repository name")
    success: bool = Field(..., description="Whether analysis succeeded")
    cost: Decimal = Field(..., description="Cost of the analysis")
    tokens_used: int = Field(..., description="Total tokens used")
    model_used: str = Field(..., description="AI model used")
    processing_time: float = Field(..., description="Processing time in seconds")


class UsageHistory(BaseModel):
    """User's usage history with pagination."""

    items: List[UsageHistoryItem] = Field(..., description="Usage history items")
    total_count: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page")
    per_page: int = Field(..., description="Items per page")
    has_next: bool = Field(..., description="Whether there's a next page")
    summary: UsageStatistics = Field(
        ..., description="Summary statistics for the period"
    )
