# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Batch history API endpoints for Enterprise and Scale+ tiers.
Provides access to batch analysis history, statistics, and details.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from github_analyzer.api.auth.dependencies import get_current_active_user
from github_analyzer.api.models.responses import (
    BatchDetailsResponse,
    BatchHistoryResponse,
    BatchStatisticsResponse,
    ErrorResponse,
)
from github_analyzer.api.services.async_batch_history_service import (
    AsyncBatchHistoryService,
)
from github_analyzer.database.connection import get_db_session
from github_analyzer.database.models import SubscriptionPlan, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/batch-history", tags=["batch-history"])


@router.get(
    "/",
    response_model=BatchHistoryResponse,
    responses={
        403: {"model": ErrorResponse, "description": "Not available for your plan"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_batch_history(
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    status: Optional[str] = Query(
        None,
        description="Filter by status",
        pattern="^(pending|processing|completed|failed)$",
    ),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> BatchHistoryResponse:
    """
    Get batch analysis history for the current user.

    Only available for Enterprise and Scale+ tiers.

    Args:
        limit: Maximum number of records to return (1-100)
        offset: Number of records to skip for pagination
        status: Optional status filter
        current_user: Authenticated user
        db: Database session

    Returns:
        List of batch history records
    """
    # Check if user has access to batch history
    if current_user.subscription_plan not in [
        SubscriptionPlan.ENTERPRISE,
        SubscriptionPlan.SCALE_PLUS,
    ]:
        raise HTTPException(
            status_code=403,
            detail="Batch history is only available for Enterprise and Scale+ plans",
        )

    try:
        batch_service = AsyncBatchHistoryService(db)
        history, total_count = await batch_service.get_batch_history(
            user_id=current_user.user_id,
            limit=limit,
            offset=offset,
            status_filter=status,
        )

        logger.info(
            f"Retrieved {len(history)} batch history records for user {current_user.user_id} (total: {total_count})"
        )

        # Return data with total_count for pagination
        return BatchHistoryResponse(
            success=True,
            data=history,
            total_count=total_count,
            message=f"Retrieved {len(history)} batch history records",
        )

    except Exception as e:
        logger.error(f"Error retrieving batch history: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve batch history: {str(e)}"
        )


@router.get(
    "/{batch_id}",
    response_model=BatchDetailsResponse,
    responses={
        403: {"model": ErrorResponse, "description": "Not available for your plan"},
        404: {"model": ErrorResponse, "description": "Batch not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_batch_details(
    batch_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> BatchDetailsResponse:
    """
    Get detailed information about a specific batch analysis.

    Only available for Enterprise and Scale+ tiers.

    Args:
        batch_id: ID of the batch to retrieve
        current_user: Authenticated user
        db: Database session

    Returns:
        Detailed batch information including contexts and error messages
    """
    # Check if user has access to batch history
    if current_user.subscription_plan not in [
        SubscriptionPlan.ENTERPRISE,
        SubscriptionPlan.SCALE_PLUS,
    ]:
        raise HTTPException(
            status_code=403,
            detail="Batch history is only available for Enterprise and Scale+ plans",
        )

    try:
        batch_service = AsyncBatchHistoryService(db)
        batch_details = await batch_service.get_batch_details(
            batch_id=batch_id, user_id=current_user.user_id
        )

        if not batch_details:
            raise HTTPException(
                status_code=404,
                detail=f"Batch {batch_id} not found or you don't have access to it",
            )

        logger.info(
            f"Retrieved batch details for {batch_id} by user {current_user.user_id}"
        )

        return BatchDetailsResponse(
            success=True,
            data=batch_details,
            message=f"Retrieved details for batch {batch_id}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving batch details: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve batch details: {str(e)}"
        )


@router.get(
    "/statistics/summary",
    response_model=BatchStatisticsResponse,
    responses={
        403: {"model": ErrorResponse, "description": "Not available for your plan"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_batch_statistics(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> BatchStatisticsResponse:
    """
    Get batch processing statistics for the current user.

    Only available for Enterprise and Scale+ tiers.

    Provides aggregated statistics including:
    - Total batches processed
    - Total repositories analyzed
    - Success/failure rates
    - Average processing time
    - Total costs
    - Status breakdown

    Args:
        days: Number of days to include in statistics (1-365)
        current_user: Authenticated user
        db: Database session

    Returns:
        Aggregated batch processing statistics
    """
    # Check if user has access to batch history
    if current_user.subscription_plan not in [
        SubscriptionPlan.ENTERPRISE,
        SubscriptionPlan.SCALE_PLUS,
    ]:
        raise HTTPException(
            status_code=403,
            detail="Batch statistics are only available for Enterprise and Scale+ plans",
        )

    try:
        batch_service = AsyncBatchHistoryService(db)
        statistics = await batch_service.get_batch_statistics(
            user_id=current_user.user_id, days=days
        )

        logger.info(
            f"Retrieved batch statistics for user {current_user.user_id} "
            f"(last {days} days)"
        )

        return BatchStatisticsResponse(
            success=True,
            data=statistics,
            message=f"Batch processing statistics for the last {days} days",
        )

    except Exception as e:
        logger.error(f"Error retrieving batch statistics: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve batch statistics: {str(e)}"
        )


@router.get(
    "/recent/summary",
    response_model=BatchHistoryResponse,
    responses={
        403: {"model": ErrorResponse, "description": "Not available for your plan"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_recent_batches(
    limit: int = Query(10, ge=1, le=50, description="Number of recent batches"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> BatchHistoryResponse:
    """
    Get a summary of recent batch analyses.

    Only available for Enterprise and Scale+ tiers.

    Provides a quick overview of the most recent batch processing jobs.

    Args:
        limit: Number of recent batches to return (1-50)
        current_user: Authenticated user
        db: Database session

    Returns:
        List of recent batch summaries
    """
    # Check if user has access to batch history
    if current_user.subscription_plan not in [
        SubscriptionPlan.ENTERPRISE,
        SubscriptionPlan.SCALE_PLUS,
    ]:
        raise HTTPException(
            status_code=403,
            detail="Batch history is only available for Enterprise and Scale+ plans",
        )

    try:
        batch_service = AsyncBatchHistoryService(db)
        recent_batches = await batch_service.get_recent_batches(
            user_id=current_user.user_id, limit=limit
        )

        logger.info(
            f"Retrieved {len(recent_batches)} recent batches for user {current_user.user_id}"
        )

        # Return data with total_count
        return BatchHistoryResponse(
            success=True,
            data=recent_batches,
            total_count=len(recent_batches),
            message=f"Retrieved {len(recent_batches)} recent batch summaries",
        )

    except Exception as e:
        logger.error(f"Error retrieving recent batches: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve recent batches: {str(e)}"
        )


@router.get(
    "/{batch_id}/aggregated-insights",
    responses={
        403: {"model": ErrorResponse, "description": "Not available for your plan"},
        404: {"model": ErrorResponse, "description": "Batch not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_batch_aggregated_insights(
    batch_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Get aggregated insights across all repositories in a batch.

    Only available for Enterprise and Scale+ tiers.

    Provides:
    - Common patterns across repositories
    - Technology distribution
    - Quality indicators
    - Top strengths and common challenges
    - Repository comparison matrix

    Args:
        batch_id: ID of the batch to analyze
        current_user: Authenticated user
        db: Database session

    Returns:
        Aggregated insights and comparison data
    """
    # Check if user has access to batch history
    if current_user.subscription_plan not in [
        SubscriptionPlan.ENTERPRISE,
        SubscriptionPlan.SCALE_PLUS,
    ]:
        raise HTTPException(
            status_code=403,
            detail="Batch aggregated insights are only available for Enterprise and Scale+ plans",
        )

    try:
        batch_service = AsyncBatchHistoryService(db)
        aggregated_insights = await batch_service.get_batch_aggregated_insights(
            batch_id=batch_id, user_id=current_user.user_id
        )

        if not aggregated_insights:
            raise HTTPException(
                status_code=404,
                detail=f"Batch {batch_id} not found or you don't have access to it",
            )

        logger.info(
            f"Retrieved aggregated insights for batch {batch_id} by user {current_user.user_id}"
        )

        return {
            "success": True,
            "data": aggregated_insights,
            "message": f"Aggregated insights for batch {batch_id}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving batch aggregated insights: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve aggregated insights: {str(e)}"
        )
