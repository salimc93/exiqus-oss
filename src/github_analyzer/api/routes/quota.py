# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Quota management API endpoints.

Provides endpoints for users to view their quota and for admins to manage quotas.
"""

from datetime import datetime, timezone
from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ...billing.usage_tracker import UsageTracker
from ...database.connection import get_db_session
from ...database.models import SubscriptionPlan, User
from ...database.operations import UserOperations
from ...utils.logging import get_logger
from ..auth.dependencies import (
    get_current_active_user,
    get_current_admin_user,
    get_current_user_id,
    require_admin,
)
from ..dependencies import get_usage_tracker
from ..models.responses import BulkResetResponse, QuotaDetailsResponse
from ..services.analytics_service import AnalyticsService

logger = get_logger(__name__)

router = APIRouter(prefix="/quota", tags=["Quota Management"])


# Pydantic models for quota endpoints


class QuotaInfo(BaseModel):
    """User quota information."""

    user_id: str = Field(..., description="User ID")
    plan: str = Field(..., description="Subscription plan")
    quota_total: int = Field(..., description="Total monthly quota")
    quota_used: int = Field(..., description="Quota consumed this month")
    quota_remaining: int = Field(..., description="Quota remaining")
    quota_percentage: float = Field(..., description="Usage percentage")


class UserQuotaResponse(BaseModel):
    """Response model for user quota list."""

    users: List[Dict[str, Any]] = Field(..., description="List of user quotas")
    total_users: int = Field(..., description="Total number of users")
    filter_applied: Optional[str] = Field(None, description="Applied filter")


class QuotaUpdateRequest(BaseModel):
    """Request model for updating user quota."""

    new_quota: int = Field(..., ge=0, description="New quota limit")


class QuotaUpdateResponse(BaseModel):
    """Response model for quota update."""

    user_id: str = Field(..., description="User ID")
    old_quota: int = Field(..., description="Previous quota")
    new_quota: int = Field(..., description="Updated quota")
    timestamp: datetime = Field(..., description="Update timestamp")


class UsageResetResponse(BaseModel):
    """Response model for usage reset."""

    success: bool = Field(..., description="Reset success status")
    user_id: str = Field(..., description="User ID")
    timestamp: datetime = Field(..., description="Reset timestamp")


class QuotaBonusRequest(BaseModel):
    """Request model for granting quota bonus."""

    bonus_amount: int = Field(..., ge=1, description="Bonus quota to grant")
    reason: str = Field(..., description="Reason for bonus")


class QuotaBonusResponse(BaseModel):
    """Response model for quota bonus."""

    user_id: str = Field(..., description="User ID")
    bonus_granted: int = Field(..., description="Bonus amount granted")
    new_quota: int = Field(..., description="New total quota")
    reason: str = Field(..., description="Reason for bonus")
    timestamp: datetime = Field(..., description="Grant timestamp")


class CustomQuotaRequest(BaseModel):
    """Request model for custom quota limit."""

    limit: int = Field(..., ge=0, description="Custom quota limit")
    reason: str = Field(..., description="Reason for custom limit")


class CustomQuotaResponse(BaseModel):
    """Response model for custom quota limit."""

    user_id: str = Field(..., description="User ID")
    custom_limit: int = Field(..., description="Custom quota limit")
    reason: str = Field(..., description="Reason for custom limit")
    timestamp: datetime = Field(..., description="Set timestamp")


# User endpoints


@router.get("/me", response_model=QuotaInfo)
async def get_my_quota(
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: AsyncSession = Depends(get_db_session),
) -> QuotaInfo:
    """
    Get current user's quota information.

    Returns quota usage and remaining allowance for the current billing period.
    """
    user = await UserOperations.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    quota_percentage = (
        (user.usage_count / max(user.usage_quota, 1)) * 100
        if user.usage_quota > 0
        else 0
    )

    return QuotaInfo(
        user_id=user_id,
        plan=user.subscription_plan.value,
        quota_total=user.usage_quota,
        quota_used=user.usage_count,
        quota_remaining=max(0, user.usage_quota - user.usage_count),
        quota_percentage=round(quota_percentage, 2),
    )


@router.get("/me/details", response_model=QuotaDetailsResponse)
async def get_my_quota_details(
    current_user: User = Depends(get_current_active_user),
    usage_tracker: UsageTracker = Depends(get_usage_tracker),
    db: AsyncSession = Depends(get_db_session),
) -> QuotaDetailsResponse:
    """
    Retrieves detailed quota and usage information for the authenticated user.
    """
    usage_summary = await usage_tracker.get_usage_summary(
        db, user_id=current_user.user_id
    )
    return QuotaDetailsResponse(
        user_id=usage_summary["user_id"],
        billing_period=usage_summary["billing_period"],
        usage_breakdown=usage_summary.get("usage_summary", {}),
        total_usage=usage_summary["total_usage"],
        total_cost=usage_summary["total_cost"],
        quota_total=usage_summary["quota_total"],
        quota_remaining=usage_summary["quota_remaining"],
    )


# Admin endpoints


@router.get("/admin/users", response_model=UserQuotaResponse)
async def get_all_user_quotas(
    _: Annotated[str, Depends(require_admin)],
    db: AsyncSession = Depends(get_db_session),
    plan: Optional[SubscriptionPlan] = Query(None, description="Filter by plan"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Result offset"),
) -> UserQuotaResponse:
    """
    Get quota information for all users (admin only).

    Returns paginated list of users with their quota usage.
    """
    if plan:
        users = await UserOperations.get_users_by_subscription_plan(
            db, plan=plan, limit=limit
        )
    else:
        users = await UserOperations.get_all_users(db, limit=limit, offset=offset)

    user_quotas = []
    for user in users:
        quota_percentage = (
            (user.usage_count / max(user.usage_quota, 1)) * 100
            if user.usage_quota > 0
            else 0
        )

        user_quotas.append(
            {
                "user_id": user.user_id,
                "email": user.email,
                "subscription_plan": user.subscription_plan.value,
                "quota_total": user.usage_quota,
                "quota_used": user.usage_count,
                "quota_remaining": max(0, user.usage_quota - user.usage_count),
                "quota_percentage": round(quota_percentage, 2),
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            }
        )

    return UserQuotaResponse(
        users=user_quotas,
        total_users=len(user_quotas),
        filter_applied=plan.value if plan else None,
    )


@router.put("/admin/users/{user_id}", response_model=QuotaUpdateResponse)
async def update_user_quota(
    user_id: str,
    quota_update: QuotaUpdateRequest,
    _: Annotated[str, Depends(require_admin)],
    db: AsyncSession = Depends(get_db_session),
) -> QuotaUpdateResponse:
    """
    Update a user's quota limit (admin only).

    Allows admins to adjust individual user quotas.
    """
    user = await UserOperations.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Validate new quota
    if quota_update.new_quota < user.usage_count:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"New quota ({quota_update.new_quota}) cannot be less than current usage ({user.usage_count})",
        )

    old_quota = user.usage_quota

    # Update user quota
    await UserOperations.update_usage_quota(
        db, user_id, new_quota=quota_update.new_quota
    )
    updated_user = await UserOperations.get_user_by_id(db, user_id)

    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found after update"
        )

    return QuotaUpdateResponse(
        user_id=user_id,
        old_quota=old_quota,
        new_quota=updated_user.usage_quota,
        timestamp=datetime.now(timezone.utc),
    )


@router.post("/admin/users/{user_id}/reset", response_model=UsageResetResponse)
async def reset_user_usage(
    user_id: str,
    _: Annotated[str, Depends(require_admin)],
    db: AsyncSession = Depends(get_db_session),
) -> UsageResetResponse:
    """
    Reset a user's usage to zero (admin only).

    Manually resets usage counter for a specific user.
    """
    usage_tracker = UsageTracker()
    success = await usage_tracker.reset_monthly_usage(db, user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset user usage",
        )

    return UsageResetResponse(
        success=True,
        user_id=user_id,
        timestamp=datetime.now(timezone.utc),
    )


@router.post("/admin/reset-all", response_model=BulkResetResponse)
async def bulk_reset_usage(
    usage_tracker: UsageTracker = Depends(get_usage_tracker),
    db: AsyncSession = Depends(get_db_session),
    plan_filter: Optional[SubscriptionPlan] = Query(
        None, description="Filter by plan name"
    ),
    _: User = Depends(get_current_admin_user),
) -> BulkResetResponse:
    """
    Admin endpoint to reset the monthly usage for all users, or a subset based on their plan.
    """
    reset_stats = await usage_tracker.bulk_reset_monthly_usage(db, plan=plan_filter)
    return BulkResetResponse(**reset_stats)


@router.get("/admin/analytics", response_model=Dict[str, Any])
async def get_usage_analytics(
    _: Annotated[str, Depends(require_admin)],
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Get usage analytics across all users (admin only).

    Returns aggregate usage statistics and insights.
    """
    analytics_service = AnalyticsService()
    analytics = await analytics_service.get_usage_analytics(db)

    return analytics


@router.post("/admin/users/{user_id}/bonus", response_model=QuotaBonusResponse)
async def grant_quota_bonus(
    user_id: str,
    bonus_request: QuotaBonusRequest,
    _: Annotated[str, Depends(require_admin)],
    db: AsyncSession = Depends(get_db_session),
) -> QuotaBonusResponse:
    """
    Grant bonus quota to a user (admin only).

    Adds additional quota on top of the user's plan allowance.
    """
    user = await UserOperations.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    new_quota = user.usage_quota + bonus_request.bonus_amount

    # Update user quota
    await UserOperations.update_usage_quota(db, user_id, new_quota=new_quota)
    updated_user = await UserOperations.get_user_by_id(db, user_id)

    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found after update"
        )

    logger.info(
        f"Granted quota bonus to user {user_id}: +{bonus_request.bonus_amount} "
        f"(reason: {bonus_request.reason})"
    )

    return QuotaBonusResponse(
        user_id=user_id,
        bonus_granted=bonus_request.bonus_amount,
        new_quota=updated_user.usage_quota,
        reason=bonus_request.reason,
        timestamp=datetime.now(timezone.utc),
    )


@router.post("/admin/users/{user_id}/custom-limit", response_model=CustomQuotaResponse)
async def set_custom_quota_limit(
    user_id: str,
    custom_limit: CustomQuotaRequest,
    _: Annotated[str, Depends(require_admin)],
    db: AsyncSession = Depends(get_db_session),
) -> CustomQuotaResponse:
    """
    Set a custom quota limit for a user (admin only).

    Overrides the default plan quota with a custom value.
    """
    # Update user with custom quota
    await UserOperations.update_usage_quota(db, user_id, new_quota=custom_limit.limit)

    logger.info(
        f"Set custom quota limit for user {user_id}: {custom_limit.limit} "
        f"(reason: {custom_limit.reason})"
    )

    return CustomQuotaResponse(
        user_id=user_id,
        custom_limit=custom_limit.limit,
        reason=custom_limit.reason,
        timestamp=datetime.now(timezone.utc),
    )
