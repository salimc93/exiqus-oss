# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Billing administration routes.

This module provides admin-only endpoints for monitoring and managing
billing operations including webhook monitoring, subscription management,
and overage tracking.
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...billing.usage_tracker import UsageTracker
from ...database.connection import get_db_session
from ...database.models import SubscriptionPlan
from ...database.operations import (
    InvoiceOperations,
    PaymentOperations,
    UserOperations,
    WebhookEventOperations,
)
from ..auth.dependencies import require_admin
from ..models.responses import (
    BillingOverviewResponse,
    InvoiceListResponse,
    OverageReportResponse,
    PaymentListResponse,
    SubscriptionMetricsResponse,
    WebhookMetricsResponse,
)
from ..services.webhook_service import WebhookService

router = APIRouter(prefix="/admin/billing", tags=["Billing Administration"])


@router.get("/overview", response_model=BillingOverviewResponse)
async def get_billing_overview(
    admin_user_id: Annotated[str, Depends(require_admin)],
    db: AsyncSession = Depends(get_db_session),
) -> BillingOverviewResponse:
    """
    Get comprehensive billing overview.

    Provides high-level metrics for billing operations including:
    - Total revenue (current month and all-time)
    - Active subscriptions by plan
    - Overage statistics
    - Payment success rates
    - Webhook processing metrics

    Requires admin role.
    """
    # Get current month for filtering
    now = datetime.now(timezone.utc)
    start_of_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    # Get subscription counts by plan
    subscription_counts = {}
    for plan in SubscriptionPlan:
        users = await UserOperations.get_users_by_subscription_plan(db, plan)
        subscription_counts[plan.value] = len(users)

    # Get payment metrics for current month
    payments = await PaymentOperations.get_payments_by_date_range(
        db, start_of_month, now
    )
    successful_payments = [p for p in payments if p.status == "succeeded"]
    failed_payments = [p for p in payments if p.status == "failed"]

    total_revenue_month = (
        sum(p.amount for p in successful_payments) / 100
    )  # Convert cents to dollars
    payment_success_rate = (
        len(successful_payments) / len(payments) * 100 if payments else 0
    )

    # Get webhook metrics
    webhook_stats = await WebhookEventOperations.get_webhook_statistics(db)

    # Get overage statistics
    overage_users = []
    professional_users = await UserOperations.get_users_by_subscription_plan(
        db, SubscriptionPlan.PROFESSIONAL
    )
    enterprise_users = await UserOperations.get_users_by_subscription_plan(
        db, SubscriptionPlan.ENTERPRISE
    )
    scale_plus_users = await UserOperations.get_users_by_subscription_plan(
        db, SubscriptionPlan.SCALE_PLUS
    )

    total_overage_revenue = 0.0
    for user in professional_users + enterprise_users + scale_plus_users:
        if user.usage_count > user.usage_quota:
            overage_users.append(user)
            overage_amount = user.usage_count - user.usage_quota
            if user.subscription_plan == SubscriptionPlan.PROFESSIONAL:
                rate = 0.20
            elif user.subscription_plan == SubscriptionPlan.SCALE_PLUS:
                rate = 0.15  # Scale+ has $0.15 per analysis overage
            else:
                rate = 0.10  # Enterprise rate
            total_overage_revenue += overage_amount * rate

    return BillingOverviewResponse(
        total_revenue_month=total_revenue_month,
        total_revenue_all_time=0.0,  # Would need historical data
        active_subscriptions=subscription_counts,
        total_active_subscriptions=sum(
            count for plan, count in subscription_counts.items() if plan != "free"
        ),
        overage_users_count=len(overage_users),
        total_overage_revenue=total_overage_revenue,
        payment_success_rate=payment_success_rate,
        failed_payments_count=len(failed_payments),
        webhook_success_rate=webhook_stats.get("success_rate", 0),
        pending_webhooks=webhook_stats.get("pending", 0),
    )


@router.get("/subscriptions/metrics", response_model=SubscriptionMetricsResponse)
async def get_subscription_metrics(
    admin_user_id: Annotated[str, Depends(require_admin)],
    db: AsyncSession = Depends(get_db_session),
) -> SubscriptionMetricsResponse:
    """
    Get detailed subscription metrics.

    Provides:
    - MRR (Monthly Recurring Revenue)
    - ARR (Annual Recurring Revenue)
    - Churn rate
    - Upgrade/downgrade trends
    - Plan distribution

    Requires admin role.
    """
    # Calculate MRR
    basic_users = len(
        await UserOperations.get_users_by_subscription_plan(db, SubscriptionPlan.BASIC)
    )
    professional_users = len(
        await UserOperations.get_users_by_subscription_plan(
            db, SubscriptionPlan.PROFESSIONAL
        )
    )
    enterprise_users = len(
        await UserOperations.get_users_by_subscription_plan(
            db, SubscriptionPlan.ENTERPRISE
        )
    )

    mrr = (basic_users * 49) + (professional_users * 149) + (enterprise_users * 399)
    arr = mrr * 12

    # Get plan distribution
    total_paid_users = basic_users + professional_users + enterprise_users
    plan_distribution = {
        "basic": basic_users,
        "professional": professional_users,
        "enterprise": enterprise_users,
    }

    # Calculate churn (simplified - would need historical data)
    churn_rate = 0.0  # Placeholder

    # Get recent upgrades/downgrades (would need activity tracking)
    upgrades_this_month = 0
    downgrades_this_month = 0

    return SubscriptionMetricsResponse(
        mrr=mrr,
        arr=arr,
        total_paid_subscriptions=total_paid_users,
        plan_distribution=plan_distribution,
        churn_rate=churn_rate,
        upgrades_this_month=upgrades_this_month,
        downgrades_this_month=downgrades_this_month,
        average_revenue_per_user=mrr / total_paid_users if total_paid_users > 0 else 0,
    )


@router.get("/overages/report", response_model=List[OverageReportResponse])
async def get_overage_report(
    admin_user_id: Annotated[str, Depends(require_admin)],
    db: AsyncSession = Depends(get_db_session),
    threshold: int = Query(0, description="Minimum overage amount to include"),
) -> List[OverageReportResponse]:
    """
    Get detailed overage report for all users.

    Shows users who have exceeded their quotas with:
    - Current usage vs quota
    - Overage amount and estimated cost
    - Grace period status
    - Historical overage trends

    Requires admin role.
    """
    overage_reports = []

    # Get all users with plans that support overages
    professional_users = await UserOperations.get_users_by_subscription_plan(
        db, SubscriptionPlan.PROFESSIONAL
    )
    enterprise_users = await UserOperations.get_users_by_subscription_plan(
        db, SubscriptionPlan.ENTERPRISE
    )

    for user in professional_users + enterprise_users:
        if user.usage_count > user.usage_quota:
            overage_amount = user.usage_count - user.usage_quota

            if overage_amount < threshold:
                continue

            # Get overage details
            usage_tracker = UsageTracker()
            overage_info = await usage_tracker.get_user_overage_info(db, user.user_id)

            # Calculate grace period info
            grace_limit = int(user.usage_quota * 1.1)
            in_grace_period = user.usage_count <= grace_limit
            grace_remaining = max(0, grace_limit - user.usage_count)

            # Calculate overage rate string
            overage_rate_per_call = (
                0.20
                if user.subscription_plan == SubscriptionPlan.PROFESSIONAL
                else 0.10
            )
            overage_rate_str = f"${overage_rate_per_call:.2f} per API call"

            overage_reports.append(
                OverageReportResponse(
                    user_id=user.user_id,
                    email=user.email,
                    plan=user.subscription_plan.value,
                    usage_quota=user.usage_quota,
                    usage_count=user.usage_count,
                    overage_amount=overage_amount,
                    overage_cost=overage_info["overage_cost"]
                    / 100,  # Convert cents to dollars
                    overage_rate=overage_rate_str,
                    in_grace_period=in_grace_period,
                    grace_remaining=grace_remaining,
                    billing_period=datetime.now(timezone.utc).strftime("%Y-%m"),
                )
            )

    # Sort by overage amount descending
    overage_reports.sort(key=lambda x: x.overage_amount, reverse=True)

    return overage_reports


@router.get("/webhooks/metrics", response_model=WebhookMetricsResponse)
async def get_webhook_metrics(
    admin_user_id: Annotated[str, Depends(require_admin)],
    db: AsyncSession = Depends(get_db_session),
) -> WebhookMetricsResponse:
    """
    Get webhook processing metrics.

    Provides:
    - Total webhooks processed
    - Success/failure rates
    - Processing times
    - Event type distribution
    - Failed webhook details

    Requires admin role.
    """
    webhook_service = WebhookService()
    stats = await webhook_service.get_webhook_statistics(db)

    # Get failed webhooks for debugging
    failed_webhooks = await WebhookEventOperations.get_failed_webhooks(db)
    failed_webhook_details = [
        {
            "event_id": webhook.event_id,
            "event_type": webhook.event_type,
            "attempts": webhook.attempts,
            "last_error": webhook.last_error,
            "created_at": webhook.created_at.isoformat(),
        }
        for webhook in failed_webhooks[:10]  # Limit to 10 most recent
    ]

    return WebhookMetricsResponse(
        total_webhooks=stats["total_webhooks"],
        processed=stats["processed"],
        failed=stats["failed"],
        pending=stats["pending"],
        success_rate=stats["success_rate"],
        average_processing_time=stats["average_processing_time"],
        events_by_type=stats["events_by_type"],
        failed_webhook_details=failed_webhook_details,
    )


@router.post("/webhooks/retry-failed")
async def retry_failed_webhooks(
    admin_user_id: Annotated[str, Depends(require_admin)],
    db: AsyncSession = Depends(get_db_session),
    max_attempts: int = Query(5, description="Maximum retry attempts"),
) -> Dict[str, int]:
    """
    Retry processing of failed webhooks.

    Attempts to reprocess webhooks that have failed but haven't
    exceeded the maximum retry attempts.

    Requires admin role.
    """
    webhook_service = WebhookService()
    result = await webhook_service.retry_failed_webhooks(db, max_attempts)

    return {
        "total_retried": result["total_webhooks"],
        "successful": result["successful_retries"],
        "failed": result["failed_retries"],
    }


@router.delete("/webhooks/cleanup")
async def cleanup_old_webhooks(
    admin_user_id: Annotated[str, Depends(require_admin)],
    db: AsyncSession = Depends(get_db_session),
    days: int = Query(30, ge=7, description="Days to keep processed webhooks"),
) -> Dict[str, int]:
    """
    Clean up old processed webhooks.

    Removes webhook events older than specified days that have been
    successfully processed.

    Requires admin role.
    """
    webhook_service = WebhookService()
    result = await webhook_service.cleanup_old_webhooks(db, days)

    return {"deleted_count": result["deleted_count"], "days": days}


@router.get("/invoices", response_model=InvoiceListResponse)
async def get_recent_invoices(
    admin_user_id: Annotated[str, Depends(require_admin)],
    db: AsyncSession = Depends(get_db_session),
    status: Optional[str] = Query(None, description="Filter by invoice status"),
    limit: int = Query(50, ge=1, le=200),
) -> InvoiceListResponse:
    """
    Get recent invoices with optional status filter.

    Provides list of recent invoices for monitoring payment
    collection and identifying issues.

    Requires admin role.
    """
    # Get all invoices or filter by status
    if status:
        invoices = await InvoiceOperations.get_invoices_by_status(db, status, limit)
    else:
        invoices = await InvoiceOperations.get_recent_invoices(db, limit)

    invoice_list: List[Dict[str, Any]] = []
    for invoice in invoices:
        # Get user info
        user = await UserOperations.get_user_by_id(db, invoice.user_id)

        invoice_list.append(
            {
                "invoice_id": invoice.invoice_id,
                "user_email": user.email if user else "Unknown",
                "amount_due": invoice.amount_due / 100,  # Convert cents to dollars
                "amount_paid": invoice.amount_paid / 100 if invoice.amount_paid else 0,
                "status": invoice.status,
                "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
                "created_at": invoice.created_at.isoformat(),
            }
        )

    return InvoiceListResponse(
        invoices=invoice_list,
        total_count=len(invoice_list),
    )


@router.get("/payments", response_model=PaymentListResponse)
async def get_recent_payments(
    admin_user_id: Annotated[str, Depends(require_admin)],
    db: AsyncSession = Depends(get_db_session),
    status: Optional[str] = Query(None, description="Filter by payment status"),
    days: int = Query(7, ge=1, le=90, description="Days to look back"),
) -> PaymentListResponse:
    """
    Get recent payments with optional filters.

    Shows payment activity for monitoring and troubleshooting
    payment issues.

    Requires admin role.
    """
    # Calculate date range
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    # Get payments
    payments = await PaymentOperations.get_payments_by_date_range(
        db, start_date, end_date
    )

    # Filter by status if provided
    if status:
        payments = [p for p in payments if p.status == status]

    payment_list: List[Dict[str, Any]] = []
    for payment in payments:
        # Get user info
        user = await UserOperations.get_user_by_id(db, payment.user_id)

        payment_list.append(
            {
                "payment_id": payment.payment_id,
                "user_email": user.email if user else "Unknown",
                "amount": payment.amount / 100,  # Convert cents to dollars
                "status": payment.status,
                "payment_method": payment.payment_method,
                "failure_message": payment.failure_message,
                "processed_at": (
                    payment.processed_at.isoformat() if payment.processed_at else None
                ),
            }
        )

    # Calculate summary stats
    total_amount = sum(p["amount"] for p in payment_list if p["status"] == "succeeded")
    success_count = len([p for p in payment_list if p["status"] == "succeeded"])
    failed_count = len([p for p in payment_list if p["status"] == "failed"])

    return PaymentListResponse(
        payments=payment_list,
        total_count=len(payment_list),
        total_amount=total_amount,
        success_count=success_count,
        failed_count=failed_count,
    )


@router.post("/usage/reset/{user_id}")
async def reset_user_usage(
    user_id: str,
    admin_user_id: Annotated[str, Depends(require_admin)],
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, str]:
    """
    Reset usage counter for a specific user.

    Emergency admin action to reset a user's usage count to 0.
    Use with caution as this affects billing.

    Requires admin role.
    """
    # Verify user exists
    user = await UserOperations.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found"
        )

    # Reset usage
    success = await UserOperations.update_usage_count(db, user_id, 0)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset usage",
        )

    await db.commit()

    return {
        "status": "success",
        "message": f"Usage reset for user {user.email}",
        "previous_usage": str(user.usage_count),
    }
