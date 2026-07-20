# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Usage tracking utilities for billing and quota management.

This module provides utilities for tracking API usage, calculating costs,
and managing user quotas across different subscription plans.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import SubscriptionPlan
from ..database.operations import (
    BillingUsageOperations,
    UserOperations,
)
from ..utils.logging import get_logger
from .subscription_manager import PlanFeatures

logger = get_logger(__name__)


class UsageTracker:
    """
    Utility class for tracking and managing API usage.

    Provides methods for recording usage, checking quotas,
    and calculating billing amounts.
    """

    # Usage type configurations
    USAGE_TYPES = {
        "analysis": {
            "name": "Repository Analysis",
            "unit": "analysis",
            "base_cost": "0.01",  # $0.01 per analysis
        },
        "batch_analysis": {
            "name": "Batch Analysis",
            "unit": "repository",
            "base_cost": "0.01",  # $0.01 per repository
        },
        "api_call": {
            "name": "API Call",
            "unit": "call",
            "base_cost": "0.001",  # $0.001 per call
        },
    }

    @staticmethod
    async def record_api_usage(
        db: AsyncSession,
        user_id: str,
        usage_type: str,
        usage_count: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Record API usage for a user.

        Args:
            db: Database session
            user_id: User ID
            usage_type: Type of usage (analysis, batch_analysis, etc.)
            usage_count: Number of units consumed
            metadata: Optional metadata about the usage

        Returns:
            Usage record ID
        """
        try:
            # Get usage type configuration
            usage_config = UsageTracker.USAGE_TYPES.get(usage_type, {})
            unit_cost = usage_config.get("base_cost", "0.00")

            # Calculate total cost
            total_cost = str(float(unit_cost) * usage_count)

            # Generate record ID with microseconds for uniqueness
            now = datetime.now(timezone.utc)
            record_id = f"usage_{now.strftime('%Y%m%d_%H%M%S%f')}_{user_id[:8]}"

            # Create billing usage record
            await BillingUsageOperations.create_usage_record(
                db=db,
                record_id=record_id,
                user_id=user_id,
                usage_type=usage_type,
                usage_count=usage_count,
                unit_cost=unit_cost,
                total_cost=total_cost,
                metadata=json.dumps(metadata) if metadata else None,
            )

            # Atomically increment user's usage consumed
            await UserOperations.increment_usage_count(db, user_id, usage_count)

            logger.info(f"Recorded {usage_count} {usage_type} usage for user {user_id}")
            return record_id

        except Exception as e:
            logger.error(f"Failed to record usage: {e}")
            raise

    @staticmethod
    async def check_quota_available(
        db: AsyncSession, user_id: str, requested_usage: int = 1
    ) -> Dict[str, Any]:
        """
        Check if user has sufficient quota for requested usage.

        Args:
            db: Database session
            user_id: User ID
            requested_usage: Number of usage units requested

        Returns:
            Quota availability information with overage details
        """
        try:
            user = await UserOperations.get_user_by_id(db, user_id)
            if not user:
                return {
                    "available": False,
                    "reason": "User not found",
                    "quota_remaining": 0,
                }

            # Get plan limits
            plan_limits = PlanFeatures.get_plan_limits(user.subscription_plan)
            quota_remaining = max(0, user.usage_quota - user.usage_count)

            # Calculate overage information
            is_over_quota = user.usage_count >= user.usage_quota
            overage_amount = max(0, user.usage_count - user.usage_quota)
            usage_percentage = (
                (user.usage_count / user.usage_quota * 100)
                if user.usage_quota > 0
                else 0
            )

            # Check if user is in overage grace period
            in_grace_period = False
            grace_remaining = 0
            if is_over_quota and plan_limits.get("overage_price_id"):
                # Professional and Enterprise plans have overage pricing, so allow with warning
                in_grace_period = True
                # Grace period allows up to 10% overage before hard enforcement
                grace_limit = int(user.usage_quota * 0.1)
                grace_remaining = max(0, grace_limit - overage_amount)

            # Determine availability based on plan and overage status
            if user.subscription_plan in [
                SubscriptionPlan.FREE,
                SubscriptionPlan.BASIC,
            ]:
                # Free and Basic plans: hard stop at quota limit
                available = quota_remaining >= requested_usage
            else:
                # Professional and Enterprise: allow overages (they'll be billed)
                available = True

            return {
                "available": available,
                "quota_remaining": quota_remaining,
                "quota_total": user.usage_quota,
                "usage_consumed": user.usage_count,
                "usage_percentage": round(usage_percentage, 2),
                "requested_usage": requested_usage,
                "plan": user.subscription_plan.value,
                "plan_limits": plan_limits,
                "is_over_quota": is_over_quota,
                "overage_amount": overage_amount,
                "in_grace_period": in_grace_period,
                "grace_remaining": grace_remaining,
                "supports_overage": bool(plan_limits.get("overage_price_id")),
                "overage_rate": plan_limits.get("overage_rate", "0.00"),
                "reason": UsageTracker._get_quota_reason(
                    available,
                    is_over_quota,
                    in_grace_period,
                    quota_remaining,
                    requested_usage,
                ),
            }

        except Exception as e:
            logger.error(f"Failed to check quota: {e}")
            return {
                "available": False,
                "reason": f"Quota check failed: {e}",
                "quota_remaining": 0,
            }

    @staticmethod
    def _get_quota_reason(
        available: bool,
        is_over_quota: bool,
        in_grace_period: bool,
        quota_remaining: int,
        requested_usage: int,
    ) -> Optional[str]:
        """Generate appropriate reason message for quota status."""
        if available:
            if is_over_quota and in_grace_period:
                return "Over quota but within grace period - overage charges will apply"
            return None

        if quota_remaining < requested_usage:
            return "Insufficient quota - please upgrade your plan"

        return "Quota exceeded - upgrade required"

    @staticmethod
    async def get_usage_summary(
        db: AsyncSession, user_id: str, billing_period: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get usage summary for a user and billing period.

        Args:
            db: Database session
            user_id: User ID
            billing_period: Billing period (YYYY-MM format), defaults to current

        Returns:
            Usage summary information
        """
        try:
            if billing_period is None:
                billing_period = datetime.now(timezone.utc).strftime("%Y-%m")

            # Get user information
            user = await UserOperations.get_user_by_id(db, user_id)
            if not user:
                raise ValueError("User not found")

            # Get usage records for the period
            usage_records = await BillingUsageOperations.get_user_usage_for_period(
                db, user_id, billing_period
            )

            # Get usage summary by type
            usage_summary = await BillingUsageOperations.get_usage_summary_for_period(
                db, user_id, billing_period
            )

            # Calculate total usage and cost
            total_usage = sum(usage_summary.values())
            total_cost = sum(float(record.total_cost) for record in usage_records)

            # Get plan information
            plan_limits = PlanFeatures.get_plan_limits(user.subscription_plan)

            return {
                "user_id": user_id,
                "billing_period": billing_period,
                "plan": user.subscription_plan.value,
                "usage_summary": usage_summary,
                "total_usage": total_usage,
                "total_cost": round(total_cost, 4),
                "quota_total": user.usage_quota,
                "quota_remaining": max(0, user.usage_quota - user.usage_count),
                "plan_limits": plan_limits,
                "usage_records_count": len(usage_records),
            }

        except Exception as e:
            logger.error(f"Failed to get usage summary: {e}")
            raise

    @staticmethod
    async def reset_monthly_usage(db: AsyncSession, user_id: str) -> bool:
        """
        Reset user's monthly usage counter.

        This is typically called at the start of a new billing period.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            True if reset was successful
        """
        try:
            success = await UserOperations.update_usage_count(db, user_id, 0)

            if success:
                logger.info(f"Reset monthly usage for user {user_id}")

            return success

        except Exception as e:
            logger.error(f"Failed to reset usage for user {user_id}: {e}")
            return False

    @staticmethod
    async def bulk_reset_monthly_usage(
        db: AsyncSession, plan: Optional[SubscriptionPlan] = None
    ) -> Dict[str, Any]:
        """
        Reset monthly usage for multiple users.

        This is typically used for billing period transitions.

        Args:
            db: Database session
            plan: Optional plan filter (reset only users with specific plan)

        Returns:
            Reset operation results
        """
        try:
            # Get users to reset
            if plan:
                users = await UserOperations.get_users_by_subscription_plan(
                    db, plan, limit=10000
                )
            else:
                users = await UserOperations.get_all_users(
                    db, limit=10000, active_only=True
                )

            reset_count = 0
            failed_count = 0

            for user in users:
                try:
                    success = await UserOperations.update_usage_count(
                        db, user.user_id, 0
                    )
                    if success:
                        reset_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    logger.error(f"Failed to reset usage for user {user.user_id}: {e}")
                    failed_count += 1

            logger.info(
                f"Bulk usage reset: {reset_count} successful, {failed_count} failed"
            )

            return {
                "total_users": len(users),
                "reset_successful": reset_count,
                "reset_failed": failed_count,
                "plan_filter": plan.value if plan else None,
            }

        except Exception as e:
            logger.error(f"Failed bulk usage reset: {e}")
            raise

    async def get_user_overage_info(
        self, db: AsyncSession, user_id: str
    ) -> Dict[str, Any]:
        """
        Get detailed overage information for a user.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            Overage information including count, cost, and grace period status
        """
        try:
            # Get user information
            user = await UserOperations.get_user_by_id(db, user_id)
            if not user:
                return {
                    "is_over_quota": False,
                    "in_grace_period": False,
                    "overage_count": 0,
                    "overage_cost": 0,
                    "error": "User not found",
                }

            # Get plan limits
            plan_limits = PlanFeatures.get_plan_limits(user.subscription_plan)
            quota_limit = user.usage_quota or plan_limits["monthly_analyses"]

            # Calculate overage
            overage_count = max(0, user.usage_count - quota_limit)
            is_over_quota = overage_count > 0

            # Check grace period (5% buffer)
            grace_period_limit = int(quota_limit * 1.05)
            in_grace_period = user.usage_count <= grace_period_limit

            # Calculate overage cost
            overage_cost = 0
            if is_over_quota and not in_grace_period:
                overage_rate = plan_limits.get(
                    "overage_rate_cents", 20
                )  # Default $0.20
                # Only charge for usage beyond grace period
                billable_overage = user.usage_count - grace_period_limit
                overage_cost = billable_overage * overage_rate  # In cents

            return {
                "is_over_quota": is_over_quota,
                "in_grace_period": in_grace_period,
                "overage_count": overage_count,
                "overage_cost": overage_cost,
                "quota_limit": quota_limit,
                "grace_period_limit": grace_period_limit,
                "current_usage": user.usage_count,
            }

        except Exception as e:
            logger.error(f"Failed to get user overage info: {e}")
            return {
                "is_over_quota": False,
                "in_grace_period": False,
                "overage_count": 0,
                "overage_cost": 0,
                "error": str(e),
            }

    @staticmethod
    def calculate_overage_cost(
        usage_consumed: int, quota_limit: int, overage_rate: str = "0.02"
    ) -> str:
        """
        Calculate cost for usage over quota limits.

        Args:
            usage_consumed: Total usage consumed
            quota_limit: Quota limit for the plan
            overage_rate: Cost per unit over quota

        Returns:
            Overage cost as string
        """
        if usage_consumed <= quota_limit:
            return "0.00"

        overage_units = usage_consumed - quota_limit
        overage_cost = float(overage_rate) * overage_units

        return f"{overage_cost:.2f}"

    @staticmethod
    async def get_overage_status(db: AsyncSession, user_id: str) -> Dict[str, Any]:
        """
        Get detailed overage status for a user.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            Detailed overage status including costs and warnings
        """
        try:
            user = await UserOperations.get_user_by_id(db, user_id)
            if not user:
                raise ValueError("User not found")

            plan_limits = PlanFeatures.get_plan_limits(user.subscription_plan)
            overage_amount = max(0, user.usage_count - user.usage_quota)

            # Calculate warning thresholds
            warning_80_percent = int(user.usage_quota * 0.8)
            warning_90_percent = int(user.usage_quota * 0.9)
            warning_100_percent = user.usage_quota

            # Determine warning level
            warning_level = None
            if user.usage_count >= warning_100_percent:
                warning_level = "exceeded"
            elif user.usage_count >= warning_90_percent:
                warning_level = "critical"
            elif user.usage_count >= warning_80_percent:
                warning_level = "high"

            # Calculate overage cost if applicable
            overage_cost = "0.00"
            if overage_amount > 0 and plan_limits.get("overage_rate"):
                overage_cost = UsageTracker.calculate_overage_cost(
                    user.usage_count, user.usage_quota, plan_limits["overage_rate"]
                )

            # Get current billing period
            current_period = datetime.now(timezone.utc).strftime("%Y-%m")

            return {
                "user_id": user_id,
                "plan": user.subscription_plan.value,
                "billing_period": current_period,
                "usage_consumed": user.usage_count,
                "usage_quota": user.usage_quota,
                "overage_amount": overage_amount,
                "overage_cost": overage_cost,
                "overage_rate": plan_limits.get("overage_rate", "0.00"),
                "supports_overage": bool(plan_limits.get("overage_price_id")),
                "warning_level": warning_level,
                "thresholds": {
                    "80_percent": warning_80_percent,
                    "90_percent": warning_90_percent,
                    "100_percent": warning_100_percent,
                },
                "usage_percentage": round(
                    (
                        (user.usage_count / user.usage_quota * 100)
                        if user.usage_quota > 0
                        else 0
                    ),
                    2,
                ),
            }

        except Exception as e:
            logger.error(f"Failed to get overage status: {e}")
            raise

    @staticmethod
    async def get_unreported_usage(db: AsyncSession, limit: int = 1000) -> List[Any]:
        """
        Get usage records that haven't been reported to Stripe yet.

        Args:
            db: Database session
            limit: Maximum number of records to return

        Returns:
            List of unreported usage records
        """
        try:
            return await BillingUsageOperations.get_unreported_usage(db, limit)
        except Exception as e:
            logger.error(f"Failed to get unreported usage: {e}")
            raise

    @staticmethod
    async def mark_usage_reported(
        db: AsyncSession, record_id: str, stripe_usage_record_id: str
    ) -> bool:
        """
        Mark usage record as reported to Stripe.

        Args:
            db: Database session
            record_id: Usage record ID
            stripe_usage_record_id: Stripe usage record ID

        Returns:
            True if successfully marked
        """
        try:
            return await BillingUsageOperations.mark_usage_reported_to_stripe(
                db, record_id, stripe_usage_record_id
            )
        except Exception as e:
            logger.error(f"Failed to mark usage as reported: {e}")
            raise
