# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Analytics API routes for user dashboards and reporting.

This module provides endpoints for users to view their analytics,
usage history, and generate reports.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.connection import get_db_session
from ..auth.dependencies import get_current_user_id
from ..dependencies import get_analytics_service
from ..models.analytics import (
    AnalyticsFilter,
    CostBreakdown,
    RepositoryStatistics,
    UsageHistory,
    UserAnalytics,
)
from ..services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get(
    "/personal",
    response_model=UserAnalytics,
    summary="Get personal analytics dashboard",
    description="Get comprehensive analytics for the authenticated user",
)
async def get_personal_analytics(
    start_date: Optional[datetime] = Query(
        None, description="Start date for analytics period"
    ),
    end_date: Optional[datetime] = Query(
        None, description="End date for analytics period"
    ),
    time_granularity: str = Query(
        "daily",
        description="Time granularity for time series data",
        pattern="^(hourly|daily|weekly|monthly)$",
    ),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> UserAnalytics:
    """
    Get comprehensive personal analytics for the authenticated user.

    This endpoint provides:
    - Usage statistics (total analyses, success rate, costs)
    - Repository analysis statistics
    - Cost breakdown by model and operation
    - Usage trends over time
    - Current quota usage

    The data can be filtered by date range and time granularity.
    """
    try:
        # Validate date range
        if start_date and end_date and start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date must be before end date",
            )

        # Prevent future dates
        now = datetime.now(timezone.utc)
        if start_date and start_date > now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date cannot be in the future",
            )
        if end_date and end_date > now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End date cannot be in the future",
            )

        # Create filter from query parameters
        filter_params = AnalyticsFilter(
            start_date=start_date,
            end_date=end_date,
            time_granularity=time_granularity,
        )

        # Get user analytics
        analytics = await analytics_service.get_user_analytics(
            db, current_user_id, filter_params
        )

        logger.info(
            f"Retrieved personal analytics for user {current_user_id} "
            f"for period {analytics.period}"
        )

        return analytics

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error in personal analytics: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrieving personal analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analytics",
        )


@router.get(
    "/usage-history",
    response_model=UsageHistory,
    summary="Get usage history",
    description="Get paginated usage history with detailed information",
)
async def get_usage_history(
    page: int = Query(1, description="Page number", ge=1),
    per_page: int = Query(50, description="Items per page", ge=1, le=100),
    start_date: Optional[datetime] = Query(None, description="Start date for history"),
    end_date: Optional[datetime] = Query(None, description="End date for history"),
    repository_id: Optional[str] = Query(
        None, description="Filter by specific repository"
    ),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> UsageHistory:
    """
    Get paginated usage history for the authenticated user.

    Returns detailed information about each analysis including:
    - Repository information
    - Success/failure status
    - Cost and token usage
    - Processing time
    - AI model used
    """
    try:
        # Validate date range
        if start_date and end_date and start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date must be before end date",
            )

        # Prevent future dates
        now = datetime.now(timezone.utc)
        if start_date and start_date > now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date cannot be in the future",
            )
        if end_date and end_date > now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End date cannot be in the future",
            )

        # Create filter from query parameters
        filter_params = AnalyticsFilter(
            start_date=start_date,
            end_date=end_date,
            repository_id=repository_id,
        )

        # Get usage history
        history = await analytics_service.get_usage_history(
            db, current_user_id, filter_params, page, per_page
        )

        logger.info(
            f"Retrieved usage history for user {current_user_id} "
            f"page {page} with {len(history.items)} items"
        )

        return history

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error in usage history: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrieving usage history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve usage history",
        )


@router.get(
    "/repository-stats",
    response_model=RepositoryStatistics,
    summary="Get repository statistics",
    description="Get statistics about analyzed repositories",
)
async def get_repository_statistics(
    start_date: Optional[datetime] = Query(
        None, description="Start date for statistics"
    ),
    end_date: Optional[datetime] = Query(None, description="End date for statistics"),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> RepositoryStatistics:
    """
    Get statistics about repositories analyzed by the user.

    Returns:
    - Total unique repositories analyzed
    - Most frequently analyzed repositories
    - Repository type distribution
    - Programming language distribution
    """
    try:
        # Create filter from query parameters
        filter_params = AnalyticsFilter(
            start_date=start_date,
            end_date=end_date,
        )

        # Get full analytics and extract repository stats
        analytics = await analytics_service.get_user_analytics(
            db, current_user_id, filter_params
        )

        return analytics.repository_stats

    except Exception as e:
        logger.error(f"Error retrieving repository statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve repository statistics",
        )


@router.get(
    "/cost-breakdown",
    response_model=CostBreakdown,
    summary="Get cost breakdown",
    description="Get detailed cost analysis",
)
async def get_cost_breakdown(
    start_date: Optional[datetime] = Query(None, description="Start date for costs"),
    end_date: Optional[datetime] = Query(None, description="End date for costs"),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> CostBreakdown:
    """
    Get detailed cost breakdown for the user.

    Returns:
    - Total cost for the period
    - Cost breakdown by AI model
    - Cost breakdown by operation type
    - Daily cost time series
    """
    try:
        # Create filter from query parameters
        filter_params = AnalyticsFilter(
            start_date=start_date,
            end_date=end_date,
        )

        # Get full analytics and extract cost breakdown
        analytics = await analytics_service.get_user_analytics(
            db, current_user_id, filter_params
        )

        return analytics.cost_breakdown

    except Exception as e:
        logger.error(f"Error retrieving cost breakdown: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cost breakdown",
        )


@router.get(
    "/time-series/{metric}",
    response_model=dict,
    summary="Get time series data for specific metric",
    description="Get time series data for visualization",
)
async def get_time_series(
    metric: str,
    start_date: Optional[datetime] = Query(
        None, description="Start date for time series"
    ),
    end_date: Optional[datetime] = Query(None, description="End date for time series"),
    time_granularity: str = Query(
        "daily",
        description="Time granularity",
        pattern="^(hourly|daily|weekly|monthly)$",
    ),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> dict[str, Any]:
    """
    Get time series data for a specific metric.

    Supported metrics:
    - usage: Analysis count over time
    - cost: Cost over time
    - success_rate: Success rate over time

    Returns data in a format suitable for charting libraries.
    """
    # Validate metric
    valid_metrics = ["usage", "cost", "success_rate"]
    if metric not in valid_metrics:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid metric. Must be one of: {', '.join(valid_metrics)}",
        )

    try:
        # Create filter from query parameters
        filter_params = AnalyticsFilter(
            start_date=start_date,
            end_date=end_date,
            time_granularity=time_granularity,
        )

        # Get full analytics
        analytics = await analytics_service.get_user_analytics(
            db, current_user_id, filter_params
        )

        # Extract requested time series
        time_series_data: dict[str, Any] = {}
        if metric == "usage":
            time_series_data = analytics.usage_trend.model_dump()
        elif metric == "cost":
            # Convert cost breakdown daily costs to time series format
            time_series_data = {
                "name": "Cost Over Time",
                "data": [
                    {"timestamp": point.timestamp.isoformat(), "value": point.value}
                    for point in analytics.cost_breakdown.daily_costs
                ],
                "unit": "USD",
            }
        else:  # success_rate
            # This would need to be calculated in the service
            # For now, return a placeholder
            time_series_data = {
                "name": "Success Rate",
                "data": [],
                "unit": "%",
            }

        return {
            "metric": metric,
            "period": analytics.period,
            "time_series": time_series_data,
        }

    except Exception as e:
        logger.error(f"Error retrieving time series for {metric}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve time series data",
        )


@router.get(
    "/export",
    response_model=dict,
    summary="Export analytics data",
    description="Export analytics data in various formats",
)
async def export_analytics(
    format: str = Query("json", description="Export format", pattern="^(json|csv)$"),
    start_date: Optional[datetime] = Query(None, description="Start date for export"),
    end_date: Optional[datetime] = Query(None, description="End date for export"),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> dict[str, Any]:
    """
    Export analytics data in JSON or CSV format.

    Note: This endpoint returns a download URL rather than the actual data
    to handle large exports efficiently.
    """
    try:
        # For MVP, we'll return a simple JSON response
        # In production, this would generate a file and return a download URL

        filter_params = AnalyticsFilter(
            start_date=start_date,
            end_date=end_date,
        )

        # Get analytics data
        analytics = await analytics_service.get_user_analytics(
            db, current_user_id, filter_params
        )

        if format == "json":
            # Return the analytics data directly for now
            return {
                "export_format": "json",
                "data": analytics.model_dump(),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
        else:
            # CSV format would need special handling
            return {
                "export_format": "csv",
                "message": "CSV export not yet implemented",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

    except Exception as e:
        logger.error(f"Error exporting analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export analytics",
        )
