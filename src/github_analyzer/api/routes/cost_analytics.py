# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Cost analytics API routes for administrators.

Provides detailed cost analytics, profitability metrics, and usage insights
for platform administrators to monitor AI API costs and margins.
"""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.connection import get_db_session
from ...database.models import SubscriptionPlan
from ..auth.dependencies import require_admin
from ..dependencies import get_redis_service
from ..services.cost_analytics_service import CostAnalyticsService
from ..services.redis_service import RedisService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/cost-analytics", tags=["admin-cost-analytics"])


@router.get(
    "/summary",
    response_model=Dict[str, Any],
    summary="Get platform cost summary",
    description="Get comprehensive cost analytics for the entire platform",
)
async def get_cost_summary(
    admin_user_id: str = Depends(require_admin),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_db_session),
    redis: RedisService = Depends(get_redis_service),
) -> Dict[str, Any]:
    """
    Get platform-wide cost summary including breakdowns by tier and model.

    Provides insights into:
    - Total platform costs
    - Cost breakdown by subscription tier
    - Cost breakdown by AI model
    - Daily cost trends
    - Top cost-driving users
    """
    analytics_service = CostAnalyticsService(redis, db)

    try:
        summary = await analytics_service.get_platform_cost_summary(days=days)

        logger.info(
            f"Admin {admin_user_id} accessed cost summary for {days} days. "
            f"Total cost: ${summary.get('total_cost', 0):.2f}"
        )

        return summary

    except Exception as e:
        logger.error(f"Error getting cost summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cost summary",
        )


@router.get(
    "/tier/{tier}",
    response_model=Dict[str, Any],
    summary="Get tier-specific analytics",
    description="Get detailed cost analytics for a specific subscription tier",
)
async def get_tier_analytics(
    tier: SubscriptionPlan,
    admin_user_id: str = Depends(require_admin),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_db_session),
    redis: RedisService = Depends(get_redis_service),
) -> Dict[str, Any]:
    """
    Get detailed analytics for a specific subscription tier.

    Includes:
    - Total costs for the tier
    - Average cost per user
    - Profitability metrics
    - Usage patterns
    """
    analytics_service = CostAnalyticsService(redis, db)

    try:
        tier_data = await analytics_service.get_tier_analytics(tier, days=days)

        logger.info(
            f"Admin {admin_user_id} accessed {tier.value} tier analytics. "
            f"Margin: {tier_data['financial_metrics']['margin_percentage']:.1f}%"
        )

        return tier_data

    except Exception as e:
        logger.error(f"Error getting tier analytics for {tier.value}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve analytics for {tier.value} tier",
        )


@router.get(
    "/user/{user_id}",
    response_model=Dict[str, Any],
    summary="Get user cost analytics",
    description="Get detailed cost analytics for a specific user",
)
async def get_user_cost_analytics(
    user_id: str,
    admin_user_id: str = Depends(require_admin),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_db_session),
    redis: RedisService = Depends(get_redis_service),
) -> Dict[str, Any]:
    """
    Get cost analytics for a specific user.

    Shows:
    - Total costs incurred by the user
    - Daily cost breakdown
    - Model usage patterns
    - Profitability for this user
    """
    analytics_service = CostAnalyticsService(redis, db)

    try:
        user_analytics = await analytics_service.get_user_cost_analytics(
            user_id, days=days
        )

        if "error" in user_analytics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=user_analytics["error"],
            )

        logger.info(
            f"Admin {admin_user_id} accessed cost analytics for user {user_id}. "
            f"Profitable: {user_analytics.get('is_profitable', False)}"
        )

        return user_analytics

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user cost analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user cost analytics",
        )


@router.get(
    "/anomalies",
    response_model=List[Dict[str, Any]],
    summary="Detect cost anomalies",
    description="Detect unusual cost spikes or patterns",
)
async def get_cost_anomalies(
    admin_user_id: str = Depends(require_admin),
    threshold: float = Query(
        2.0,
        ge=1.5,
        le=5.0,
        description="Anomaly detection threshold multiplier",
    ),
    db: AsyncSession = Depends(get_db_session),
    redis: RedisService = Depends(get_redis_service),
) -> List[Dict[str, Any]]:
    """
    Detect cost anomalies that might indicate issues or unusual usage.

    Returns list of detected anomalies sorted by severity.
    """
    analytics_service = CostAnalyticsService(redis, db)

    try:
        anomalies = await analytics_service.get_cost_anomalies(
            threshold_multiplier=threshold
        )

        logger.info(
            f"Admin {admin_user_id} checked cost anomalies. "
            f"Found {len(anomalies)} anomalies with threshold {threshold}"
        )

        return anomalies

    except Exception as e:
        logger.error(f"Error detecting cost anomalies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to detect cost anomalies",
        )


@router.get(
    "/estimates",
    response_model=Dict[str, Any],
    summary="Get cost estimates",
    description="Estimate monthly and annual costs based on current usage",
)
async def get_cost_estimates(
    admin_user_id: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
    redis: RedisService = Depends(get_redis_service),
) -> Dict[str, Any]:
    """
    Get cost estimates based on recent usage patterns.

    Provides monthly and annual projections by tier.
    """
    analytics_service = CostAnalyticsService(redis, db)

    try:
        estimates = await analytics_service.estimate_monthly_costs()

        if "error" in estimates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=estimates["error"],
            )

        logger.info(
            f"Admin {admin_user_id} accessed cost estimates. "
            f"Monthly estimate: ${estimates['platform_total']['monthly_estimate']:.2f}"
        )

        return estimates

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cost estimates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate cost estimates",
        )


@router.get(
    "/profitability",
    response_model=Dict[str, Any],
    summary="Get profitability analysis",
    description="Analyze profitability by tier and overall platform margins",
)
async def get_profitability_analysis(
    admin_user_id: str = Depends(require_admin),
    days: int = Query(30, ge=7, le=90, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_db_session),
    redis: RedisService = Depends(get_redis_service),
) -> Dict[str, Any]:
    """
    Get detailed profitability analysis for the platform.

    Shows which tiers are profitable and overall platform margins.
    """
    analytics_service = CostAnalyticsService(redis, db)

    try:
        # Get analytics for each tier
        tier_profitability = {}

        for tier in SubscriptionPlan:
            if tier != SubscriptionPlan.FREE:  # Skip free tier
                tier_data = await analytics_service.get_tier_analytics(tier, days=days)

                tier_profitability[tier.value] = {
                    "user_count": tier_data["user_count"],
                    "monthly_revenue": tier_data["financial_metrics"][
                        "monthly_revenue"
                    ],
                    "estimated_monthly_cost": tier_data["financial_metrics"][
                        "estimated_monthly_cost"
                    ],
                    "gross_margin": tier_data["financial_metrics"]["gross_margin"],
                    "margin_percentage": tier_data["financial_metrics"][
                        "margin_percentage"
                    ],
                    "status": tier_data["profitability"],
                }

        # Calculate overall platform profitability
        total_revenue = sum(t["monthly_revenue"] for t in tier_profitability.values())
        total_cost = sum(
            t["estimated_monthly_cost"] for t in tier_profitability.values()
        )
        total_margin = total_revenue - total_cost
        overall_margin_percentage = (
            (total_margin / total_revenue * 100) if total_revenue > 0 else 0
        )

        result = {
            "period_days": days,
            "by_tier": tier_profitability,
            "platform_total": {
                "monthly_revenue": total_revenue,
                "estimated_monthly_cost": total_cost,
                "gross_margin": total_margin,
                "margin_percentage": overall_margin_percentage,
                "status": "profitable" if total_margin > 0 else "unprofitable",
            },
            "insights": _generate_profitability_insights(
                tier_profitability, overall_margin_percentage
            ),
        }

        logger.info(
            f"Admin {admin_user_id} accessed profitability analysis. "
            f"Overall margin: {overall_margin_percentage:.1f}%"
        )

        return result

    except Exception as e:
        logger.error(f"Error calculating profitability: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate profitability analysis",
        )


def _generate_profitability_insights(
    tier_profitability: Dict[str, Any],
    overall_margin: float,
) -> List[str]:
    """Generate insights based on profitability data."""
    insights = []

    # Overall health
    if overall_margin > 50:
        insights.append("Platform has healthy profit margins above 50%")
    elif overall_margin > 20:
        insights.append("Platform is profitable with moderate margins")
    elif overall_margin > 0:
        insights.append("Platform is profitable but margins are thin")
    else:
        insights.append("⚠️ Platform is currently unprofitable")

    # Check for unprofitable tiers
    unprofitable_tiers = [
        tier
        for tier, data in tier_profitability.items()
        if data["status"] == "unprofitable"
    ]

    if unprofitable_tiers:
        insights.append(f"⚠️ Unprofitable tiers: {', '.join(unprofitable_tiers)}")

    # Best performing tier
    if tier_profitability:
        best_tier = max(
            tier_profitability.items(), key=lambda x: x[1]["margin_percentage"]
        )
        insights.append(
            f"Best performing tier: {best_tier[0]} "
            f"({best_tier[1]['margin_percentage']:.1f}% margin)"
        )

    # Scale+ specific insight
    if "scale_plus" in tier_profitability:
        scale_plus = tier_profitability["scale_plus"]
        if scale_plus["user_count"] > 0:
            insights.append(
                f"Scale+ tier has {scale_plus['user_count']} users "
                f"generating ${scale_plus['monthly_revenue']:.0f}/month"
            )

    return insights
