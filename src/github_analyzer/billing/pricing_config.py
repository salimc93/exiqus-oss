# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Pricing configuration for subscription plans.

This module centralizes all pricing information to ensure consistency
across the application and proper revenue tracking.
"""

from enum import Enum
from typing import Any, Dict, Optional, TypedDict, Union


class PlanConfig(TypedDict):
    name: str
    price: Union[int, float]
    stripe_price_id: Optional[str]
    analyses_per_month: int


class PricingPlan(Enum):
    """Pricing plan tiers with their monthly prices."""

    FREE = {
        "name": "Free",
        "price": 0,
        "stripe_price_id": None,  # No Stripe price for free plan
        "analyses_per_month": 5,
    }
    BASIC = {  # Called "Starter" in frontend
        "name": "Starter",
        "price": 49,
        "stripe_price_id": "price_starter_monthly",  # TODO: Replace with actual Stripe price ID
        "analyses_per_month": 25,
    }
    PROFESSIONAL = {  # Called "Growth" in frontend
        "name": "Growth",
        "price": 199,
        "stripe_price_id": "price_growth_monthly",  # TODO: Replace with actual Stripe price ID
        "analyses_per_month": 100,
    }
    ENTERPRISE = {  # Called "Scale" in frontend
        "name": "Scale",
        "price": 499,
        "stripe_price_id": "price_scale_monthly",  # TODO: Replace with actual Stripe price ID
        "analyses_per_month": 500,
    }
    SCALE_PLUS = {
        "name": "Scale+",
        "price": 2500,
        "stripe_price_id": "price_scale_plus_monthly",  # TODO: Replace with actual Stripe price ID
        "analyses_per_month": 1000,
    }


def get_plan_price(plan_key: str) -> float:
    """
    Get the monthly price for a subscription plan.

    Args:
        plan_key: The plan key (e.g., 'free', 'basic', 'professional', 'enterprise', 'scale_plus')

    Returns:
        The monthly price in dollars
    """
    plan_map = {
        "free": PricingPlan.FREE,
        "basic": PricingPlan.BASIC,
        "professional": PricingPlan.PROFESSIONAL,
        "enterprise": PricingPlan.ENTERPRISE,
        "scale_plus": PricingPlan.SCALE_PLUS,
    }

    plan = plan_map.get(plan_key.lower())
    if plan:
        return float(plan.value["price"])  # type: ignore[arg-type]
    return 0.0


def get_plan_prices() -> Dict[str, float]:
    """
    Get all plan prices as a dictionary.

    Returns:
        Dictionary mapping plan keys to their monthly prices
    """
    return {
        "free": float(PricingPlan.FREE.value["price"]),  # type: ignore[arg-type]
        "basic": float(PricingPlan.BASIC.value["price"]),  # type: ignore[arg-type]
        "professional": float(PricingPlan.PROFESSIONAL.value["price"]),  # type: ignore[arg-type]
        "enterprise": float(PricingPlan.ENTERPRISE.value["price"]),  # type: ignore[arg-type]
        "scale_plus": float(PricingPlan.SCALE_PLUS.value["price"]),  # type: ignore[arg-type]
    }


def get_stripe_price_id(plan_key: str) -> Optional[str]:
    """
    Get the Stripe price ID for a subscription plan.

    Args:
        plan_key: The plan key

    Returns:
        The Stripe price ID or None if not applicable
    """
    plan_map = {
        "free": PricingPlan.FREE,
        "basic": PricingPlan.BASIC,
        "professional": PricingPlan.PROFESSIONAL,
        "enterprise": PricingPlan.ENTERPRISE,
        "scale_plus": PricingPlan.SCALE_PLUS,
    }

    plan = plan_map.get(plan_key.lower())
    if plan:
        stripe_id = plan.value.get("stripe_price_id")
        return str(stripe_id) if stripe_id else None
    return None


# For production, these should be retrieved from database
# based on actual Stripe subscription data
async def calculate_actual_mrr_from_database(db_session: Any) -> float:
    """
    Calculate actual MRR from database records.

    This function:
    1. Queries all active subscriptions
    2. Maps subscription plans to their monthly amounts
    3. Sums up all monthly recurring charges

    This ensures accuracy even if prices change or customers have custom pricing.
    """
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    from ..database.models import User

    if not isinstance(db_session, AsyncSession):
        # Return 0 if not an async session (backwards compatibility)
        return 0.0

    try:
        # Query all users with active subscriptions
        result = await db_session.execute(
            select(User).where(
                User.stripe_subscription_status == "active"  # type: ignore[attr-defined]
            )
        )
        active_users = result.scalars().all()

        total_mrr = 0.0

        for user in active_users:
            # Map subscription plan to monthly amount
            # Note: subscription_plan is stored as string in DB but typed as enum
            plan = str(user.subscription_plan)
            if plan == "BASIC":
                total_mrr += float(PricingPlan.BASIC.value["price"])  # type: ignore[arg-type]
            elif plan == "PROFESSIONAL":
                total_mrr += float(PricingPlan.PROFESSIONAL.value["price"])  # type: ignore[arg-type]
            elif plan == "SCALE_PLUS":
                total_mrr += float(PricingPlan.SCALE_PLUS.value["price"])  # type: ignore[arg-type]
            elif plan == "ENTERPRISE":
                # Enterprise has custom pricing, try to get from user's custom field
                # or use default enterprise price
                if hasattr(user, "custom_monthly_rate") and user.custom_monthly_rate:
                    total_mrr += float(user.custom_monthly_rate)
                else:
                    total_mrr += float(PricingPlan.ENTERPRISE.value["price"])  # type: ignore[arg-type]

        return total_mrr

    except Exception as e:
        # Log error and return 0 rather than crashing
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Error calculating MRR from database: {e}")
        return 0.0
