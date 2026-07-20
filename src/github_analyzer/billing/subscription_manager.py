# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Subscription management business logic.

This module handles subscription lifecycle management, plan changes,
and usage tracking with proper validation and error handling.

Updated: Fixed Stripe price IDs for test mode.
"""

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import SubscriptionPlan, SubscriptionStatus
from ..database.operations import UserOperations
from ..utils.logging import get_logger
from .stripe_client import StripeClient, StripeClientError

logger = get_logger(__name__)


# Determine if we're in test mode based on Stripe API key
def _is_stripe_test_mode() -> bool:
    """Check if Stripe is configured for test mode."""
    stripe_key = os.getenv("STRIPE_SECRET_KEY", "")
    return stripe_key.startswith("sk_test_")


class PlanFeatures:
    """Plan feature definitions and limits."""

    PLANS = {
        SubscriptionPlan.FREE: {
            "monthly_analyses": 10,
            "monthly_ai_analyses": 2,  # Only 2 AI-powered analyses per month
            "batch_size": 1,
            "api_rate_limit": 10,  # per hour
            "features": ["basic_analysis"],
            "price_id": None,  # Free plan
            "price_id_test": None,  # Free plan (test mode)
        },
        SubscriptionPlan.BASIC: {
            "monthly_analyses": 100,
            "monthly_ai_analyses": 100,  # All can be AI-powered
            "batch_size": 2,
            "api_rate_limit": 60,  # per hour
            "features": ["basic_analysis", "pdf_reports"],
            "price_id": "price_1S9YiLRvLpeUOuiGRnTXyNKg",  # Starter tier - $49/month (LIVE MODE)
            "price_id_test": "price_1S3yVb2NUcXbQPePzeWEUswZ",  # Starter tier - $49/month (TEST MODE)
        },
        SubscriptionPlan.PROFESSIONAL: {
            "monthly_analyses": 500,
            "monthly_ai_analyses": 500,  # All can be AI-powered
            "batch_size": 5,
            "api_rate_limit": 300,  # per hour
            "features": [
                "basic_analysis",
                "pdf_reports",
                "advanced_metrics",
                "api_access",
            ],
            "price_id": "price_1S9YiKRvLpeUOuiGvPZwMfRu",  # Growth tier - $199/month (LIVE MODE)
            "price_id_test": "price_1SLwIi2NUcXbQPePzO8UXflv",  # Growth tier - $199/month (TEST MODE - Updated)
            "overage_price_id": "price_professional_overage",  # $0.20 per overage
            "overage_rate": 0.20,
        },
        SubscriptionPlan.ENTERPRISE: {
            "monthly_analyses": 2000,
            "monthly_ai_analyses": 2000,  # All can be AI-powered
            "batch_size": 10,
            "api_rate_limit": 1000,  # per hour
            "features": ["all_features", "priority_support", "custom_integrations"],
            "price_id": "price_1S9YiIRvLpeUOuiGNg81hyNC",  # Scale tier - $499/month (LIVE MODE)
            "price_id_test": "price_1SLwJc2NUcXbQPePqhUMHM8t",  # Scale tier - $499/month (TEST MODE - Updated)
            "overage_price_id": "price_enterprise_overage",  # $0.10 per overage
            "overage_rate": 0.10,
        },
        SubscriptionPlan.SCALE_PLUS: {
            "monthly_analyses": 3000,
            "monthly_ai_analyses": 3000,  # All can be AI-powered
            "batch_size": 15,
            "api_rate_limit": 2000,  # per hour
            "features": [
                "all_features",
                "priority_support",
                "custom_integrations",
                "batch_history",
                "bulk_export",
                "dedicated_support",
                "advanced_batch_processing",
            ],
            "price_id": "price_1S9YiFRvLpeUOuiGNzVKirF4",  # Scale+ tier - $2500/month (LIVE MODE)
            "price_id_test": "price_1S7dsSRvLpeUOuiGm51xWxcU",  # Scale+ tier - $2500/month (TEST MODE)
            "overage_price_id": "price_scale_plus_overage",  # $0.15 per overage
            "overage_rate": 0.15,
            "response_time_hours": 6,  # 4-8 hours priority support
        },
    }

    @classmethod
    def get_plan_limits(cls, plan: SubscriptionPlan) -> Dict[str, Any]:
        """Get limits for a subscription plan."""
        plan_config = cls.PLANS.get(plan, cls.PLANS[SubscriptionPlan.FREE]).copy()

        # Use test or live mode price ID based on Stripe configuration
        if _is_stripe_test_mode():
            # Use test mode price ID
            if "price_id_test" in plan_config:
                plan_config["price_id"] = plan_config["price_id_test"]

        return plan_config

    @classmethod
    def can_access_feature(cls, plan: SubscriptionPlan, feature: str) -> bool:
        """Check if a plan has access to a feature."""
        plan_data = cls.get_plan_limits(plan)
        features = plan_data.get("features", [])
        return feature in features or "all_features" in features


class SubscriptionManagerError(Exception):
    """Custom exception for subscription manager errors."""

    pass


class SubscriptionManager:
    """
    Manages subscription lifecycle and business logic.

    Handles subscription creation, updates, cancellations, and plan enforcement
    with proper integration between Stripe and our database.
    """

    def __init__(self) -> None:
        """Initialize subscription manager."""
        self.stripe_client = StripeClient()

    async def create_subscription(
        self,
        db: AsyncSession,
        user_id: str,
        plan: SubscriptionPlan,
        payment_method_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new subscription for a user.

        Args:
            db: Database session
            user_id: User ID
            plan: Subscription plan
            payment_method_id: Optional payment method ID for immediate start

        Returns:
            Subscription data with checkout URL or immediate activation

        Raises:
            SubscriptionManagerError: If subscription creation fails
        """
        try:
            # Get user from database
            user = await UserOperations.get_user_by_id(db, user_id)
            if not user:
                raise SubscriptionManagerError("User not found")

            # Get plan configuration
            plan_config = PlanFeatures.get_plan_limits(plan)
            if not plan_config.get("price_id"):
                raise SubscriptionManagerError(
                    "Cannot create subscription for free plan"
                )

            # Create or get Stripe customer
            customer_id = await self._ensure_stripe_customer(user)

            # Create subscription in Stripe
            subscription_data = await self.stripe_client.create_subscription(
                customer_id=customer_id,
                price_id=plan_config["price_id"],
                metadata={
                    "exiqus_user_id": user_id,
                    "plan": plan.value,
                },
            )

            # Update user subscription in database
            await self._update_user_subscription(db, user, subscription_data, plan)

            # Add metered price for overages if applicable
            if plan_config.get("overage_price_id"):
                try:
                    await self.stripe_client.add_metered_price_to_subscription(
                        subscription_id=subscription_data["id"],
                        price_id=plan_config["overage_price_id"],
                        metadata={"usage_type": "overage", "plan": plan.value},
                    )
                    logger.info(
                        f"Added overage pricing to subscription {subscription_data['id']}"
                    )
                except Exception as e:
                    logger.warning(f"Failed to add overage pricing: {e}")
                    # Continue without overage pricing - not critical for subscription

            logger.info(f"Created subscription for user {user_id}, plan {plan.value}")

            latest_invoice = subscription_data.get("latest_invoice", {}) or {}
            payment_intent = latest_invoice.get("payment_intent", {}) or {}
            client_secret = payment_intent.get("client_secret")

            response = {
                "subscription_id": subscription_data["id"],
                "status": subscription_data["status"],
                "client_secret": client_secret,
                "plan": plan.value,
                "features": plan_config["features"],
                "has_overage_pricing": bool(plan_config.get("overage_price_id")),
                "trial_end": subscription_data.get("trial_end"),
                "requires_payment_method": subscription_data["status"]
                in ["incomplete", "past_due"],
            }
            return response

        except StripeClientError as e:
            logger.error(f"Stripe error creating subscription: {e}")
            raise SubscriptionManagerError(f"Payment processing failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error creating subscription: {e}")
            raise SubscriptionManagerError(f"Subscription creation failed: {e}")

    async def update_subscription_plan(
        self, db: AsyncSession, user_id: str, new_plan: SubscriptionPlan
    ) -> Dict[str, Any]:
        """
        Update user's subscription plan with proration.

        Args:
            db: Database session
            user_id: User ID
            new_plan: New subscription plan

        Returns:
            Updated subscription data

        Raises:
            SubscriptionManagerError: If plan update fails
        """
        try:
            # Get user and current subscription
            user = await UserOperations.get_user_by_id(db, user_id)
            if not user:
                raise SubscriptionManagerError("User not found")

            if not user.stripe_subscription_id:
                raise SubscriptionManagerError("User has no active subscription")

            # Get new plan configuration
            new_plan_config = PlanFeatures.get_plan_limits(new_plan)
            if not new_plan_config.get("price_id"):
                raise SubscriptionManagerError(
                    "Cannot upgrade to free plan via this method"
                )

            # Get current subscription from Stripe
            current_subscription = await self.stripe_client.get_subscription(
                user.stripe_subscription_id
            )
            if not current_subscription:
                raise SubscriptionManagerError(
                    "Current subscription not found in Stripe"
                )

            # Prepare items update for subscription
            items_update = []
            if current_subscription.get("items", {}).get("data"):
                items_update.append(
                    {
                        "id": current_subscription["items"]["data"][0]["id"],
                        "price": new_plan_config["price_id"],
                    }
                )

            # Check if we need to remove overage pricing (downgrade scenario)
            old_plan_config = PlanFeatures.get_plan_limits(user.subscription_plan)
            remove_items = []

            if old_plan_config.get("overage_price_id") and not new_plan_config.get(
                "overage_price_id"
            ):
                # Downgrading from a plan with overages to one without
                for item in current_subscription["items"]["data"]:
                    if item["price"]["id"] == old_plan_config["overage_price_id"]:
                        remove_items.append(item["id"])
                        logger.info(
                            f"Will remove overage item {item['id']} during downgrade"
                        )

            # Update subscription in Stripe with proration
            update_params = {
                "items": items_update,
                "proration_behavior": "create_prorations",
                "metadata": {
                    "exiqus_user_id": user_id,
                    "plan": new_plan.value,
                    "upgraded_at": datetime.now(timezone.utc).isoformat(),
                },
            }

            if remove_items:
                update_params["remove_items"] = remove_items

            updated_subscription = await self.stripe_client.update_subscription(
                subscription_id=user.stripe_subscription_id, **update_params
            )

            # Update user subscription in database
            await self._update_user_subscription(
                db, user, updated_subscription, new_plan
            )

            # Handle overage pricing addition for upgrades
            has_overage_pricing = False
            if new_plan_config.get("overage_price_id"):
                if not old_plan_config.get("overage_price_id"):
                    # Upgrading to a plan with overages
                    try:
                        existing_item = (
                            await self.stripe_client.get_subscription_item_for_price(
                                user.stripe_subscription_id,
                                new_plan_config["overage_price_id"],
                            )
                        )
                        if not existing_item:
                            await self.stripe_client.add_metered_price_to_subscription(
                                subscription_id=user.stripe_subscription_id,
                                price_id=new_plan_config["overage_price_id"],
                                metadata={
                                    "usage_type": "overage",
                                    "plan": new_plan.value,
                                },
                            )
                            logger.info("Added new overage pricing")
                        has_overage_pricing = True
                    except Exception as e:
                        logger.warning(f"Failed to add overage pricing: {e}")
                        has_overage_pricing = False
                else:
                    # Plan already has overage pricing
                    has_overage_pricing = True

            logger.info(
                f"Updated subscription for user {user_id} to plan {new_plan.value}"
            )

            return {
                "subscription_id": updated_subscription["id"],
                "plan": new_plan.value,
                "status": updated_subscription["status"],
                "features": new_plan_config["features"],
                "prorated": True,
                "has_overage_pricing": has_overage_pricing,
            }

        except StripeClientError as e:
            logger.error(f"Stripe error updating subscription: {e}")
            raise SubscriptionManagerError(f"Plan update failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error updating subscription: {e}")
            raise SubscriptionManagerError(f"Plan update failed: {e}")

    async def cancel_subscription(
        self, db: AsyncSession, user_id: str, at_period_end: bool = True
    ) -> Dict[str, Any]:
        """
        Cancel user's subscription.

        Args:
            db: Database session
            user_id: User ID
            at_period_end: Whether to cancel at period end or immediately

        Returns:
            Cancellation data

        Raises:
            SubscriptionManagerError: If cancellation fails
        """
        try:
            # Get user and current subscription
            user = await UserOperations.get_user_by_id(db, user_id)
            if not user:
                raise SubscriptionManagerError("User not found")

            if not user.stripe_subscription_id:
                raise SubscriptionManagerError("User has no active subscription")

            # Cancel subscription in Stripe
            cancelled_subscription = await self.stripe_client.cancel_subscription(
                subscription_id=user.stripe_subscription_id, at_period_end=at_period_end
            )

            # Update user subscription status
            if at_period_end:
                # Mark as cancelling at period end
                await UserOperations.update_user_subscription(
                    db,
                    user_id,
                    subscription_status=SubscriptionStatus.CANCELED,
                    subscription_end_date=datetime.fromtimestamp(
                        cancelled_subscription["current_period_end"], tz=timezone.utc
                    ),
                )
            else:
                # Cancel immediately - downgrade to free
                await UserOperations.update_user_subscription(
                    db,
                    user_id,
                    subscription_plan=SubscriptionPlan.FREE,
                    subscription_status=SubscriptionStatus.CANCELED,
                    subscription_end_date=datetime.now(timezone.utc),
                    usage_quota=PlanFeatures.get_plan_limits(SubscriptionPlan.FREE)[
                        "monthly_analyses"
                    ],
                )

            logger.info(
                f"Cancelled subscription for user {user_id} (at_period_end={at_period_end})"
            )

            return {
                "subscription_id": cancelled_subscription["id"],
                "status": cancelled_subscription["status"],
                "cancelled_at": datetime.now(timezone.utc).isoformat(),
                "at_period_end": at_period_end,
                "access_until": (
                    datetime.fromtimestamp(
                        cancelled_subscription["current_period_end"], tz=timezone.utc
                    ).isoformat()
                    if at_period_end
                    else None
                ),
            }

        except StripeClientError as e:
            logger.error(f"Stripe error cancelling subscription: {e}")
            raise SubscriptionManagerError(f"Cancellation failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error cancelling subscription: {e}")
            raise SubscriptionManagerError(f"Cancellation failed: {e}")

    async def get_subscription_status(
        self, db: AsyncSession, user_id: str
    ) -> Dict[str, Any]:
        """
        Get comprehensive subscription status for a user.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            Subscription status and usage information

        Raises:
            SubscriptionManagerError: If status retrieval fails
        """
        try:
            # Get user from database
            user = await UserOperations.get_user_by_id(db, user_id)
            if not user:
                raise SubscriptionManagerError("User not found")

            # Get plan features
            plan_features = PlanFeatures.get_plan_limits(user.subscription_plan)

            result = {
                "user_id": user_id,
                "plan": user.subscription_plan.value,
                "status": user.subscription_status.value,
                "usage_quota": user.usage_quota,
                "usage_consumed": user.usage_count,
                "usage_remaining": max(0, user.usage_quota - user.usage_count),
                "features": plan_features["features"],
                "limits": {
                    "monthly_analyses": plan_features["monthly_analyses"],
                    "batch_size": plan_features["batch_size"],
                    "api_rate_limit": plan_features["api_rate_limit"],
                },
            }

            # Add Stripe subscription details if applicable
            stripe_period_found = False
            if user.stripe_subscription_id:
                try:
                    stripe_subscription = await self.stripe_client.get_subscription(
                        user.stripe_subscription_id
                    )
                    if stripe_subscription:
                        # Get period dates from Stripe subscription
                        period_start = stripe_subscription.get("current_period_start")
                        period_end = stripe_subscription.get("current_period_end")

                        # If period dates are available, add them to result
                        if period_start and period_end:
                            result.update(
                                {
                                    "stripe_subscription_id": stripe_subscription["id"],
                                    "current_period_start": datetime.fromtimestamp(
                                        period_start,
                                        tz=timezone.utc,
                                    ).isoformat(),
                                    "current_period_end": datetime.fromtimestamp(
                                        period_end,
                                        tz=timezone.utc,
                                    ).isoformat(),
                                    "cancel_at_period_end": stripe_subscription.get(
                                        "cancel_at_period_end", False
                                    ),
                                }
                            )
                            stripe_period_found = True
                except Exception as e:
                    logger.warning(f"Could not fetch Stripe subscription details: {e}")
                    # Continue to fallback logic below

            # Use subscription dates from user record as fallback if no Stripe period found
            if not stripe_period_found and user.stripe_subscription_id:
                if user.subscription_start_date and user.subscription_end_date:
                    # Use the dates directly from the database
                    result.update(
                        {
                            "stripe_subscription_id": user.stripe_subscription_id,
                            "current_period_start": user.subscription_start_date.isoformat(),
                            "current_period_end": user.subscription_end_date.isoformat(),
                            "cancel_at_period_end": False,
                        }
                    )
                elif user.subscription_start_date:
                    # Fallback to calculation if only start date exists
                    start_date = user.subscription_start_date
                    # Get current month's billing period
                    now = datetime.now(timezone.utc)
                    period_start = datetime(
                        now.year,
                        now.month,
                        start_date.day,
                        0,
                        0,
                        0,
                        tzinfo=timezone.utc,
                    )
                    # Handle month end edge cases
                    if period_start > now:
                        # We're still in previous month's period
                        if now.month == 1:
                            period_start = datetime(
                                now.year - 1,
                                12,
                                start_date.day,
                                0,
                                0,
                                0,
                                tzinfo=timezone.utc,
                            )
                        else:
                            period_start = datetime(
                                now.year,
                                now.month - 1,
                                start_date.day,
                                0,
                                0,
                                0,
                                tzinfo=timezone.utc,
                            )

                    # Calculate period end (next month same day)
                    if period_start.month == 12:
                        period_end = datetime(
                            period_start.year + 1,
                            1,
                            start_date.day,
                            0,
                            0,
                            0,
                            tzinfo=timezone.utc,
                        )
                    else:
                        period_end = datetime(
                            period_start.year,
                            period_start.month + 1,
                            start_date.day,
                            0,
                            0,
                            0,
                            tzinfo=timezone.utc,
                        )

                    result.update(
                        {
                            "stripe_subscription_id": user.stripe_subscription_id,
                            "current_period_start": period_start.isoformat(),
                            "current_period_end": period_end.isoformat(),
                            "cancel_at_period_end": False,
                        }
                    )

            return result

        except StripeClientError as e:
            logger.error(f"Stripe error getting subscription status: {e}")
            raise SubscriptionManagerError(f"Status retrieval failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error getting subscription status: {e}")
            raise SubscriptionManagerError(f"Status retrieval failed: {e}")

    async def check_usage_limits(
        self, db: AsyncSession, user_id: str, requested_usage: int = 1
    ) -> Dict[str, Any]:
        """
        Check if user can perform requested usage within their plan limits.

        Args:
            db: Database session
            user_id: User ID
            requested_usage: Number of API calls requested

        Returns:
            Usage check result with limits and recommendations

        Raises:
            SubscriptionManagerError: If usage check fails
        """
        try:
            # Get user from database
            user = await UserOperations.get_user_by_id(db, user_id)
            if not user:
                raise SubscriptionManagerError("User not found")

            # Get plan features
            plan_features = PlanFeatures.get_plan_limits(user.subscription_plan)
            supports_overage = bool(plan_features.get("overage_price_id"))

            # Check current usage against quota
            remaining_quota = max(0, user.usage_quota - user.usage_count)

            # Determine if user can proceed
            if supports_overage:
                # Plans with overage support (Professional/Enterprise)
                # Allow usage beyond quota with a 10% grace period
                grace_limit = int(user.usage_quota * 1.1)
                in_grace_period = (
                    user.usage_count >= user.usage_quota
                    and user.usage_count < grace_limit
                )
                grace_remaining = (
                    max(0, grace_limit - user.usage_count) if in_grace_period else 0
                )

                # Can proceed if under quota OR in grace period with enough remaining
                # Ensure no single request can push user beyond grace limit
                can_proceed = (
                    remaining_quota >= requested_usage
                    or (in_grace_period and grace_remaining >= requested_usage)
                    or (
                        supports_overage
                        and (user.usage_count + requested_usage) <= grace_limit
                    )
                )
            else:
                # Plans without overage support (Free/Basic)
                # Hard stop at quota limit
                can_proceed = remaining_quota >= requested_usage
                in_grace_period = False
                grace_remaining = 0

            result = {
                "user_id": user_id,
                "can_proceed": can_proceed,
                "requested_usage": requested_usage,
                "remaining_quota": remaining_quota,
                "current_plan": user.subscription_plan.value,
                "usage_consumed": user.usage_count,
                "usage_quota": user.usage_quota,
                "usage_limit": user.usage_quota,  # Add for header compatibility
                "usage_remaining": remaining_quota,
                "plan": user.subscription_plan.value,
                "reset_timestamp": self._get_quota_reset_timestamp(),
                "supports_overage": supports_overage,
                "grace_period": in_grace_period,
                "grace_remaining": grace_remaining,
            }

            # Add upgrade recommendations if at limit
            if not can_proceed:
                upgrade_options = []
                for plan in [
                    SubscriptionPlan.BASIC,
                    SubscriptionPlan.PROFESSIONAL,
                    SubscriptionPlan.ENTERPRISE,
                    SubscriptionPlan.SCALE_PLUS,
                ]:
                    if plan.value > user.subscription_plan.value:
                        plan_features = PlanFeatures.get_plan_limits(plan)
                        if plan_features["monthly_analyses"] > user.usage_quota:
                            upgrade_options.append(
                                {
                                    "plan": plan.value,
                                    "monthly_analyses": plan_features[
                                        "monthly_analyses"
                                    ],
                                    "features": plan_features["features"],
                                }
                            )

                result["upgrade_required"] = True
                result["upgrade_options"] = upgrade_options

                if supports_overage and user.usage_count >= grace_limit:
                    result["message"] = (
                        "Grace period exhausted. Further API calls are blocked to prevent excessive charges. "
                        "Please contact support to increase your limits."
                    )
                else:
                    result["message"] = (
                        "Monthly quota exceeded. Consider upgrading to continue using the service."
                    )

            return result

        except Exception as e:
            logger.error(f"Unexpected error checking usage limits: {e}")
            raise SubscriptionManagerError(f"Usage check failed: {e}")

    def _get_quota_reset_timestamp(self) -> datetime:
        """
        Get the timestamp when quota will reset (first day of next month).

        Returns:
            Datetime of next quota reset
        """
        now = datetime.now(timezone.utc)
        # Get first day of next month
        if now.month == 12:
            next_reset = datetime(now.year + 1, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        else:
            next_reset = datetime(
                now.year, now.month + 1, 1, 0, 0, 0, tzinfo=timezone.utc
            )
        return next_reset

    async def _ensure_stripe_customer(self, user: Any) -> str:
        """
        Ensure user has a Stripe customer record.

        Args:
            user: User database model

        Returns:
            Stripe customer ID
        """
        if user.stripe_customer_id:
            # Verify customer exists in Stripe
            customer = await self.stripe_client.get_customer(user.stripe_customer_id)
            if customer:
                return str(user.stripe_customer_id)

        # Create new Stripe customer
        customer_data = await self.stripe_client.create_customer(
            email=user.email,
            user_id=user.user_id,
            name=user.full_name,
            metadata={
                "created_at": user.created_at.isoformat(),
            },
        )

        # Update user with Stripe customer ID
        # Note: This would need to be implemented in UserOperations
        # await UserOperations.update_stripe_customer_id(db, user.user_id, customer_data["id"])

        return str(customer_data["id"])

    async def create_checkout_session(
        self,
        db: AsyncSession,
        user_id: str,
        plan: SubscriptionPlan,
        success_url: str,
        cancel_url: str,
    ) -> Dict[str, Any]:
        """
        Create a Stripe Checkout session for subscription signup.

        Args:
            db: Database session
            user_id: User ID
            plan: Subscription plan
            success_url: URL to redirect after successful payment
            cancel_url: URL to redirect if payment cancelled

        Returns:
            Checkout session data

        Raises:
            SubscriptionManagerError: If session creation fails
        """
        try:
            # Get user from database
            user = await UserOperations.get_user_by_id(db, user_id)
            if not user:
                raise SubscriptionManagerError("User not found")

            # Get plan configuration
            plan_config = PlanFeatures.get_plan_limits(plan)
            if not plan_config.get("price_id"):
                raise SubscriptionManagerError(
                    "Cannot create checkout session for free plan"
                )

            # Create or get Stripe customer
            customer_id = await self._ensure_stripe_customer(user)

            # Create checkout session metadata
            metadata = {
                "exiqus_user_id": user_id,
                "plan": plan.value,
            }

            # Add flag for overage pricing setup
            if plan_config.get("overage_price_id"):
                metadata["setup_overage_pricing"] = "true"
                metadata["overage_price_id"] = plan_config["overage_price_id"]

            # Create checkout session
            session_data = await self.stripe_client.create_checkout_session(
                customer_id=customer_id,
                price_id=plan_config["price_id"],
                success_url=success_url,
                cancel_url=cancel_url,
                metadata=metadata,
            )

            logger.info(
                f"Created checkout session for user {user_id}, plan {plan.value}"
            )

            return {
                "checkout_session_id": session_data["id"],
                "checkout_url": session_data["url"],
                "plan": plan.value,
                "features": plan_config["features"],
            }

        except StripeClientError as e:
            logger.error(f"Stripe error creating checkout session: {e}")
            raise SubscriptionManagerError(f"Checkout session creation failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error creating checkout session: {e}")
            raise SubscriptionManagerError(f"Checkout session creation failed: {e}")

    async def _update_user_subscription(
        self,
        db: AsyncSession,
        user: Any,
        subscription_data: Dict[str, Any],
        plan: SubscriptionPlan,
    ) -> None:
        """
        Update user subscription data in database.

        Args:
            db: Database session
            user: User database model
            subscription_data: Stripe subscription data
            plan: Subscription plan
        """
        # Map Stripe status to our enum
        stripe_status = subscription_data["status"]
        if stripe_status == "active":
            status = SubscriptionStatus.ACTIVE
        elif stripe_status == "trialing":
            status = SubscriptionStatus.TRIALING
        elif stripe_status == "past_due":
            status = SubscriptionStatus.PAST_DUE
        elif stripe_status in ["canceled", "unpaid"]:
            status = SubscriptionStatus.CANCELED
        else:
            status = SubscriptionStatus.SUSPENDED

        # Get plan limits
        plan_limits = PlanFeatures.get_plan_limits(plan)

        # Update user subscription
        await UserOperations.update_user_subscription(
            db,
            user.user_id,
            subscription_plan=plan,
            subscription_status=status,
            usage_quota=plan_limits["monthly_analyses"],
            stripe_subscription_id=subscription_data["id"],
            subscription_start_date=datetime.fromtimestamp(
                subscription_data["current_period_start"], tz=timezone.utc
            ),
            subscription_end_date=datetime.fromtimestamp(
                subscription_data["current_period_end"], tz=timezone.utc
            ),
        )
