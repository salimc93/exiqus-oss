# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Priority support API routes for Scale+ and Enterprise users.

Provides endpoints for accessing priority support features and SLA metrics.
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from github_analyzer.api.auth.dependencies import get_current_active_user
from github_analyzer.api.models.responses import ErrorResponse
from github_analyzer.database.connection import get_db_session
from github_analyzer.database.models import SubscriptionPlan, User

from ..services.priority_support_service import PrioritySupportService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/priority-support", tags=["priority-support"])


@router.get(
    "/status",
    responses={
        200: {"description": "Priority support access status"},
        403: {"model": ErrorResponse, "description": "Not available for your plan"},
    },
)
async def get_priority_support_status(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Check if the current user has access to priority support.

    Returns details about their priority level and SLA targets.
    """
    priority_service = PrioritySupportService(db)
    has_access = await priority_service.check_priority_support_access(
        current_user.user_id
    )

    if not has_access:
        raise HTTPException(
            status_code=403,
            detail="Priority support is only available for Scale+ and Enterprise plans",
        )

    # Return priority support details based on plan
    if current_user.subscription_plan == SubscriptionPlan.SCALE_PLUS:
        return {
            "has_access": True,
            "plan": "Scale+",
            "priority_level": 3,
            "priority_name": "URGENT",
            "sla_response_hours": 4,
            "benefits": [
                "4-hour response time SLA",
                "Dedicated support channel",
                "Priority issue resolution",
                "Direct escalation path",
                "Dedicated account manager",
            ],
        }
    elif current_user.subscription_plan == SubscriptionPlan.ENTERPRISE:
        return {
            "has_access": True,
            "plan": "Enterprise",
            "priority_level": 2,
            "priority_name": "HIGH",
            "sla_response_hours": 12,
            "benefits": [
                "12-hour response time SLA",
                "Priority support queue",
                "Expedited issue resolution",
            ],
        }
    else:
        return {
            "has_access": False,
            "plan": current_user.subscription_plan.value,
            "priority_level": 0,
            "priority_name": "STANDARD",
            "sla_response_hours": 48,
            "upgrade_options": ["Scale+", "Enterprise"],
        }


@router.get(
    "/metrics",
    responses={
        200: {"description": "User support metrics"},
        403: {"model": ErrorResponse, "description": "Not available for your plan"},
    },
)
async def get_support_metrics(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Get support metrics for the current user.

    Only available for Scale+ and Enterprise users.
    """
    # Check if user has priority support access
    if current_user.subscription_plan not in [
        SubscriptionPlan.SCALE_PLUS,
        SubscriptionPlan.ENTERPRISE,
    ]:
        raise HTTPException(
            status_code=403,
            detail="Support metrics are only available for Scale+ and Enterprise plans",
        )

    priority_service = PrioritySupportService(db)
    metrics = await priority_service.get_user_support_metrics(current_user.user_id)

    return {
        "success": True,
        "data": metrics,
        "message": "Support metrics retrieved successfully",
    }


@router.get(
    "/sla-performance",
    responses={
        200: {"description": "SLA performance metrics"},
        403: {"model": ErrorResponse, "description": "Admin access required"},
    },
)
async def get_sla_performance(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Get SLA performance metrics for priority support.

    Admin only endpoint.
    """
    # Check admin access
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required to view SLA performance metrics",
        )

    priority_service = PrioritySupportService(db)
    sla_metrics = await priority_service.get_sla_metrics(days=days)

    return {
        "success": True,
        "data": sla_metrics,
        "period_days": days,
        "message": f"SLA performance metrics for the last {days} days",
    }
