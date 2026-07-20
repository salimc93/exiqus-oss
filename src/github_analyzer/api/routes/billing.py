# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Billing API endpoints for customer subscription management.

This module provides customer-facing endpoints for managing subscriptions,
payment methods, invoices, and usage tracking.
"""

from datetime import datetime, timezone
from typing import Annotated, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ...billing.stripe_client import StripeClient, StripeClientError
from ...billing.subscription_manager import (
    PlanFeatures,
    SubscriptionManager,
    SubscriptionManagerError,
)
from ...database.connection import get_db_session
from ...database.models import SubscriptionPlan
from ...database.operations import (
    InvoiceOperations,
    PaymentOperations,
    UserOperations,
)
from ...services.candidate_usage_service import CandidateUsageService
from ...utils.config import get_config
from ...utils.logging import get_logger
from ..auth.dependencies import get_current_user_id
from ..models.auth import SubscriptionPlan as APIPlan
from ..models.responses import SuccessResponse
from ..services.webhook_service import WebhookService

logger = get_logger(__name__)

router = APIRouter(prefix="/billing", tags=["Billing"])


# Pydantic models for billing API


class SubscriptionCreateRequest(BaseModel):
    """Request model for creating a subscription."""

    plan: APIPlan = Field(..., description="Subscription plan")
    payment_method_id: Optional[str] = Field(
        None, description="Payment method ID for immediate setup"
    )


class SubscriptionUpdateRequest(BaseModel):
    """Request model for updating a subscription."""

    plan: APIPlan = Field(..., description="New subscription plan")


class CheckoutSessionRequest(BaseModel):
    """Request model for creating a checkout session."""

    plan: APIPlan = Field(..., description="Subscription plan")
    success_url: str = Field(..., description="Success redirect URL")
    cancel_url: str = Field(..., description="Cancel redirect URL")


class UsageSummaryResponse(BaseModel):
    """Response model for usage summary."""

    user_id: str = Field(..., description="User ID")
    current_period: str = Field(..., description="Current billing period")
    plan: str = Field(..., description="Current subscription plan")
    usage_quota: int = Field(..., description="Monthly usage quota")
    usage_consumed: int = Field(..., description="Usage consumed this period")
    usage_remaining: int = Field(..., description="Usage remaining")
    usage_percentage: float = Field(..., description="Usage percentage")
    plan_features: List[str] = Field(..., description="Available features")


class InvoiceResponse(BaseModel):
    """Response model for invoice data."""

    invoice_id: str = Field(..., description="Invoice ID")
    amount_due: int = Field(..., description="Amount due in cents")
    amount_paid: int = Field(..., description="Amount paid in cents")
    currency: str = Field(..., description="Currency code")
    status: str = Field(..., description="Invoice status")
    billing_period_start: datetime = Field(..., description="Billing period start")
    billing_period_end: datetime = Field(..., description="Billing period end")
    due_date: Optional[datetime] = Field(None, description="Due date")
    paid_at: Optional[datetime] = Field(None, description="Payment date")
    invoice_url: Optional[str] = Field(None, description="Hosted invoice URL")
    created_at: datetime = Field(..., description="Creation timestamp")


class PaymentResponse(BaseModel):
    """Response model for payment data."""

    payment_id: str = Field(..., description="Payment ID")
    amount: int = Field(..., description="Payment amount in cents")
    currency: str = Field(..., description="Currency code")
    status: str = Field(..., description="Payment status")
    payment_method: str = Field(..., description="Payment method")
    created_at: datetime = Field(..., description="Creation timestamp")
    processed_at: Optional[datetime] = Field(None, description="Processing timestamp")


@router.get("/subscription", response_model=dict)
async def get_subscription_status(
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """
    Get current subscription status and details.

    Returns comprehensive subscription information including plan details,
    usage statistics, and billing information.
    """
    try:
        subscription_manager = SubscriptionManager()
        subscription_status = await subscription_manager.get_subscription_status(
            db, user_id
        )

        return SuccessResponse(
            success=True,
            message="Subscription status retrieved",
            data=subscription_status,
        ).model_dump()

    except SubscriptionManagerError as e:
        logger.error(f"Failed to get subscription status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error getting subscription status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Subscription status retrieval failed",
        )


@router.post("/subscription", response_model=dict)
async def create_subscription(
    request: SubscriptionCreateRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """
    Create a new subscription for the authenticated user.

    Creates a subscription in Stripe and updates the user's plan.
    Returns checkout information for payment setup.
    """
    try:
        subscription_manager = SubscriptionManager()

        # Map API plan to database enum
        plan_mapping = {
            APIPlan.BASIC: SubscriptionPlan.BASIC,
            APIPlan.PROFESSIONAL: SubscriptionPlan.PROFESSIONAL,
            APIPlan.ENTERPRISE: SubscriptionPlan.ENTERPRISE,
            APIPlan.SCALE_PLUS: SubscriptionPlan.SCALE_PLUS,
        }

        db_plan = plan_mapping.get(request.plan)
        if not db_plan:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid subscription plan",
            )

        subscription_data = await subscription_manager.create_subscription(
            db, user_id, db_plan, request.payment_method_id
        )

        return SuccessResponse(
            success=True,
            message="Subscription created successfully",
            data=subscription_data,
        ).model_dump()

    except SubscriptionManagerError as e:
        logger.error(f"Failed to create subscription: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/subscription", response_model=dict)
async def update_subscription(
    request: SubscriptionUpdateRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """
    Update subscription plan with proration.

    Changes the user's subscription plan with automatic proration
    for the current billing period.
    """
    try:
        subscription_manager = SubscriptionManager()

        # Map API plan to database enum
        plan_mapping = {
            APIPlan.BASIC: SubscriptionPlan.BASIC,
            APIPlan.PROFESSIONAL: SubscriptionPlan.PROFESSIONAL,
            APIPlan.ENTERPRISE: SubscriptionPlan.ENTERPRISE,
            APIPlan.SCALE_PLUS: SubscriptionPlan.SCALE_PLUS,
        }

        db_plan = plan_mapping.get(request.plan)
        if not db_plan:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid subscription plan",
            )

        subscription_data = await subscription_manager.update_subscription_plan(
            db, user_id, db_plan
        )

        return SuccessResponse(
            success=True,
            message="Subscription updated successfully",
            data=subscription_data,
        ).model_dump()

    except SubscriptionManagerError as e:
        logger.error(f"Failed to update subscription: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/subscription", response_model=dict)
async def cancel_subscription(
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: AsyncSession = Depends(get_db_session),
    at_period_end: bool = True,
) -> dict[str, Any]:
    """
    Cancel subscription.

    Args:
        at_period_end: Whether to cancel at period end (default) or immediately
    """
    try:
        subscription_manager = SubscriptionManager()

        cancellation_data = await subscription_manager.cancel_subscription(
            db, user_id, at_period_end
        )

        return SuccessResponse(
            success=True,
            message="Subscription cancelled successfully",
            data=cancellation_data,
        ).model_dump()

    except SubscriptionManagerError as e:
        logger.error(f"Failed to cancel subscription: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/checkout-session", response_model=dict)
async def create_checkout_session(
    request: CheckoutSessionRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """
    Create Stripe checkout session for subscription signup.

    Returns a checkout session URL for the user to complete payment.
    """
    try:
        # Get user
        user = await UserOperations.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        # Get plan configuration
        plan_mapping = {
            APIPlan.BASIC: SubscriptionPlan.BASIC,
            APIPlan.PROFESSIONAL: SubscriptionPlan.PROFESSIONAL,
            APIPlan.ENTERPRISE: SubscriptionPlan.ENTERPRISE,
            APIPlan.SCALE_PLUS: SubscriptionPlan.SCALE_PLUS,
        }

        db_plan = plan_mapping.get(request.plan)
        if not db_plan:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid subscription plan",
            )

        plan_config = PlanFeatures.get_plan_limits(db_plan)
        price_id = plan_config.get("price_id")

        if not price_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Plan not available for checkout",
            )

        # Create or get Stripe customer
        stripe_client = StripeClient()

        if user.stripe_customer_id:
            # User already has a Stripe customer ID, verify it exists
            customer_data = await stripe_client.get_customer(user.stripe_customer_id)
            if customer_data:
                # Customer exists, use it
                customer_id = user.stripe_customer_id
                logger.info(
                    f"Using existing Stripe customer {customer_id} for user {user_id}"
                )
            else:
                # Customer doesn't exist, create new one and update user
                logger.warning(
                    f"Stripe customer {user.stripe_customer_id} not found, creating new one"
                )
                customer_data = await stripe_client.create_customer(
                    email=user.email, user_id=user.user_id, name=user.full_name
                )
                customer_id = customer_data["id"]
                # Update user with new customer ID
                await UserOperations.update_user_subscription(
                    db, user_id, stripe_customer_id=customer_id
                )
        else:
            # Create new customer and update user
            logger.info(f"Creating new Stripe customer for user {user_id}")
            customer_data = await stripe_client.create_customer(
                email=user.email, user_id=user.user_id, name=user.full_name
            )
            customer_id = customer_data["id"]
            # Update user with new customer ID
            await UserOperations.update_user_subscription(
                db, user_id, stripe_customer_id=customer_id
            )

        # Create checkout session
        checkout_session = await stripe_client.create_checkout_session(
            customer_id=customer_id,
            price_id=price_id,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            metadata={
                "exiqus_user_id": user_id,
                "plan": db_plan.value,
            },
        )

        return SuccessResponse(
            success=True,
            message="Checkout session created",
            data={
                "checkout_url": checkout_session["url"],
                "session_id": checkout_session["id"],
            },
        ).model_dump()

    except StripeClientError as e:
        logger.error(f"Stripe error creating checkout session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment processing error",
        )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Failed to create checkout session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Checkout session creation failed",
        )


@router.get("/usage", response_model=UsageSummaryResponse)
async def get_usage_summary(
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: AsyncSession = Depends(get_db_session),
) -> UsageSummaryResponse:
    """
    Get current usage summary and quota information.

    Returns detailed usage statistics for the current billing period.
    """
    try:
        # Get user
        user = await UserOperations.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        # Get plan features
        plan_features = PlanFeatures.get_plan_limits(user.subscription_plan)

        # Get candidate assessment usage (candidate-centric model)
        candidate_service = CandidateUsageService(db)
        candidate_usage = await candidate_service.get_monthly_usage(user_id)
        candidate_limit = CandidateUsageService.get_tier_limit(user.subscription_plan)

        # Calculate usage percentage based on candidate assessments
        usage_percentage = (
            (candidate_usage / max(candidate_limit, 1)) * 100
            if candidate_limit > 0
            else 0
        )

        return UsageSummaryResponse(
            user_id=user_id,
            current_period=datetime.now(timezone.utc).strftime("%Y-%m"),
            plan=user.subscription_plan.value,
            usage_quota=candidate_limit,
            usage_consumed=candidate_usage,
            usage_remaining=max(0, candidate_limit - candidate_usage),
            usage_percentage=round(usage_percentage, 2),
            plan_features=plan_features["features"],
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Failed to get usage summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Usage summary retrieval failed",
        )


@router.get("/invoices", response_model=List[InvoiceResponse])
async def get_invoices(
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: AsyncSession = Depends(get_db_session),
    limit: int = 10,
    offset: int = 0,
) -> List[InvoiceResponse]:
    """
    Get user's billing invoices.

    Returns paginated list of invoices for the authenticated user.
    """
    try:
        invoices = await InvoiceOperations.get_user_invoices(
            db, user_id, limit=limit, offset=offset
        )

        return [
            InvoiceResponse(
                invoice_id=invoice.invoice_id,
                amount_due=invoice.amount_due,
                amount_paid=invoice.amount_paid,
                currency=invoice.currency,
                status=invoice.status,
                billing_period_start=invoice.billing_period_start,
                billing_period_end=invoice.billing_period_end,
                due_date=invoice.due_date,
                paid_at=invoice.paid_at,
                invoice_url=invoice.invoice_url,
                created_at=invoice.created_at,
            )
            for invoice in invoices
        ]

    except Exception as e:
        logger.error(f"Failed to get invoices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invoice retrieval failed",
        )


@router.get("/payments", response_model=List[PaymentResponse])
async def get_payments(
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: AsyncSession = Depends(get_db_session),
    limit: int = 10,
    offset: int = 0,
) -> List[PaymentResponse]:
    """
    Get user's payment history.

    Returns paginated list of payments for the authenticated user.
    """
    try:
        payments = await PaymentOperations.get_user_payments(
            db, user_id, limit=limit, offset=offset
        )

        return [
            PaymentResponse(
                payment_id=payment.payment_id,
                amount=payment.amount,
                currency=payment.currency,
                status=payment.status,
                payment_method=payment.payment_method,
                created_at=payment.created_at,
                processed_at=payment.processed_at,
            )
            for payment in payments
        ]

    except Exception as e:
        logger.error(f"Failed to get payments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment history retrieval failed",
        )


@router.post("/webhooks/stripe", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """
    Handle Stripe webhooks.

    This endpoint receives and processes Stripe webhook events
    with proper signature verification and idempotency.
    """
    try:
        # Get raw payload and signature
        payload = await request.body()
        signature = request.headers.get("stripe-signature")

        if not signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing Stripe signature",
            )

        # Process webhook
        config = get_config()
        stripe_client = StripeClient()
        event = stripe_client.verify_webhook_signature(
            payload, signature, webhook_secret=config.stripe_webhook_secret
        )

        webhook_service = WebhookService()
        result = await webhook_service.process_webhook(db, event)

        return result

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Webhook processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing error",
        )
