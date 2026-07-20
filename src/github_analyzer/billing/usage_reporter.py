# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Usage reporting service for Stripe metered billing.

This module handles the reporting of usage data to Stripe for
metered billing and overage charges. It includes batch processing,
retry logic, and idempotency support.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import SubscriptionPlan
from ..database.operations import BillingUsageOperations, UserOperations
from ..utils.logging import get_logger
from .stripe_client import StripeClient, StripeClientError
from .subscription_manager import PlanFeatures

logger = get_logger(__name__)


class UsageReportingError(Exception):
    """Custom exception for usage reporting errors."""

    pass


class UsageReporter:
    """
    Service for reporting usage data to Stripe.

    Handles batch processing of unreported usage records,
    aggregation by subscription item, and reliable reporting
    with retry logic.
    """

    def __init__(self, stripe_client: Optional[StripeClient] = None):
        """Initialize the usage reporter."""
        self.stripe_client = stripe_client or StripeClient()
        self.max_retries = 3
        self.batch_size = 100

    async def report_all_unreported_usage(
        self, db: AsyncSession, limit: int = 1000
    ) -> Dict[str, Any]:
        """
        Report all unreported usage records to Stripe.

        Args:
            db: Database session
            limit: Maximum number of records to process

        Returns:
            Summary of reporting results
        """
        try:
            # Get unreported usage records
            unreported_records = await BillingUsageOperations.get_unreported_usage(
                db, limit
            )

            if not unreported_records:
                logger.info("No unreported usage records found")
                return {
                    "success": True,
                    "records_processed": 0,
                    "records_reported": 0,
                    "records_failed": 0,
                }

            logger.info(f"Found {len(unreported_records)} unreported usage records")

            # Group records by user for efficient processing
            user_records_map = self._group_records_by_user(unreported_records)

            # Process each user's records
            results = await self._process_user_records(db, user_records_map)

            return results

        except Exception as e:
            logger.error(f"Failed to report unreported usage: {e}")
            raise UsageReportingError(f"Usage reporting failed: {e}")

    async def report_user_overage_usage(
        self, db: AsyncSession, user_id: str, overage_count: int
    ) -> bool:
        """
        Report overage usage for a specific user.

        Args:
            db: Database session
            user_id: User ID
            overage_count: Number of overage units

        Returns:
            True if reporting was successful
        """
        try:
            # Get user information
            user = await UserOperations.get_user_by_id(db, user_id)
            if not user:
                logger.error(f"User {user_id} not found")
                return False

            # Check if user has a subscription that supports overages
            if user.subscription_plan not in [
                SubscriptionPlan.PROFESSIONAL,
                SubscriptionPlan.ENTERPRISE,
            ]:
                logger.info(
                    f"User {user_id} plan {user.subscription_plan} doesn't support overages"
                )
                return False

            if not user.stripe_subscription_id:
                logger.warning(f"User {user_id} has no Stripe subscription")
                return False

            # Get the overage price ID for the user's plan
            plan_config = PlanFeatures.get_plan_limits(user.subscription_plan)
            overage_price_id = plan_config.get("overage_price_id")

            if not overage_price_id:
                logger.warning(
                    f"No overage price configured for plan {user.subscription_plan}"
                )
                return False

            # Find the subscription item for overage pricing
            subscription_item = await self._get_overage_subscription_item(
                user.stripe_subscription_id, overage_price_id
            )

            if not subscription_item:
                logger.warning(
                    f"No subscription item found for overage price {overage_price_id}"
                )
                return False

            # Report the usage to Stripe
            timestamp = int(datetime.now(timezone.utc).timestamp())
            await self.stripe_client.create_usage_record(
                subscription_item_id=subscription_item["id"],
                quantity=overage_count,
                timestamp=timestamp,
                action="increment",
            )

            logger.info(
                f"Reported {overage_count} overage units for user {user_id} "
                f"to subscription item {subscription_item['id']}"
            )

            return True

        except StripeClientError as e:
            logger.error(f"Stripe error reporting overage usage: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error reporting overage usage: {e}")
            return False

    async def _process_user_records(
        self, db: AsyncSession, user_records_map: Dict[str, List[Any]]
    ) -> Dict[str, Any]:
        """Process usage records grouped by user."""
        total_processed = 0
        total_reported = 0
        total_failed = 0
        failed_records = []

        for user_id, records in user_records_map.items():
            try:
                # Get user information
                user = await UserOperations.get_user_by_id(db, user_id)
                if not user:
                    logger.warning(f"User {user_id} not found, skipping records")
                    total_failed += len(records)
                    total_processed += len(records)
                    failed_records.extend([r.record_id for r in records])
                    continue

                # Process records for this user
                user_results = await self._report_user_usage_batch(db, user, records)

                total_processed += user_results["processed"]
                total_reported += user_results["reported"]
                total_failed += user_results["failed"]
                failed_records.extend(user_results["failed_records"])

            except Exception as e:
                logger.error(f"Failed to process records for user {user_id}: {e}")
                total_failed += len(records)
                failed_records.extend([r.record_id for r in records])

        return {
            "success": total_failed == 0,
            "records_processed": total_processed,
            "records_reported": total_reported,
            "records_failed": total_failed,
            "failed_records": failed_records,
        }

    async def _report_user_usage_batch(
        self, db: AsyncSession, user: Any, records: List[Any]
    ) -> Dict[str, Any]:
        """Report a batch of usage records for a single user."""
        processed = 0
        reported = 0
        failed = 0
        failed_records: List[str] = []

        # Check if user has overage pricing configured
        if user.subscription_plan not in [
            SubscriptionPlan.PROFESSIONAL,
            SubscriptionPlan.ENTERPRISE,
        ]:
            logger.info(
                f"User {user.user_id} plan doesn't support usage reporting, marking as reported"
            )
            # Mark as reported even though we didn't report to Stripe
            for record in records:
                await BillingUsageOperations.mark_usage_reported_to_stripe(
                    db, record.record_id, "no_overage_support"
                )
                processed += 1
                reported += 1
            return {
                "processed": processed,
                "reported": reported,
                "failed": failed,
                "failed_records": failed_records,
            }

        if not user.stripe_subscription_id:
            logger.warning(f"User {user.user_id} has no Stripe subscription")
            failed += len(records)
            failed_records.extend([r.record_id for r in records])
            return {
                "processed": len(records),
                "reported": reported,
                "failed": failed,
                "failed_records": failed_records,
            }

        # Get overage subscription item
        plan_config = PlanFeatures.get_plan_limits(user.subscription_plan)
        overage_price_id = plan_config.get("overage_price_id")

        if not overage_price_id:
            logger.warning(f"No overage price for plan {user.subscription_plan}")
            failed += len(records)
            failed_records.extend([r.record_id for r in records])
            return {
                "processed": len(records),
                "reported": reported,
                "failed": failed,
                "failed_records": failed_records,
            }

        subscription_item = await self._get_overage_subscription_item(
            user.stripe_subscription_id, overage_price_id
        )

        if not subscription_item:
            logger.warning("No subscription item found for overage pricing")
            failed += len(records)
            failed_records.extend([r.record_id for r in records])
            return {
                "processed": len(records),
                "reported": reported,
                "failed": failed,
                "failed_records": failed_records,
            }

        # Aggregate usage by billing period
        period_usage = self._aggregate_usage_by_period(records)

        # Report each period's usage
        for period, period_records in period_usage.items():
            try:
                # Calculate total usage for the period
                total_usage = sum(r.usage_count for r in period_records)

                # Get timestamp for the period (use first record's timestamp)
                timestamp = int(period_records[0].created_at.timestamp())

                # Report to Stripe with retries
                success = await self._report_with_retries(
                    subscription_item["id"], total_usage, timestamp
                )

                if success:
                    # Mark all records in this batch as reported
                    stripe_record_id = f"aggregated_{period}_{user.user_id}"
                    for record in period_records:
                        try:
                            await BillingUsageOperations.mark_usage_reported_to_stripe(
                                db, record.record_id, stripe_record_id
                            )
                            reported += 1
                        except Exception as e:
                            logger.error(
                                f"Failed to mark record {record.record_id} as reported: {e}"
                            )
                            failed += 1
                            failed_records.append(record.record_id)
                else:
                    failed += len(period_records)
                    failed_records.extend([r.record_id for r in period_records])

                processed += len(period_records)

            except Exception as e:
                logger.error(f"Failed to report usage for period {period}: {e}")
                failed += len(period_records)
                failed_records.extend([r.record_id for r in period_records])
                processed += len(period_records)

        return {
            "processed": processed,
            "reported": reported,
            "failed": failed,
            "failed_records": failed_records,
        }

    async def _report_with_retries(
        self, subscription_item_id: str, quantity: int, timestamp: int
    ) -> bool:
        """Report usage to Stripe with retry logic."""
        for attempt in range(self.max_retries):
            try:
                await self.stripe_client.create_usage_record(
                    subscription_item_id=subscription_item_id,
                    quantity=quantity,
                    timestamp=timestamp,
                    action="set",  # Use 'set' for aggregated reporting
                )
                return True

            except StripeClientError as e:
                if attempt < self.max_retries - 1:
                    wait_time = (attempt + 1) * 2  # Exponential backoff
                    logger.warning(
                        f"Stripe error on attempt {attempt + 1}, retrying in {wait_time}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"Failed to report usage after {self.max_retries} attempts: {e}"
                    )
                    return False

            except Exception as e:
                logger.error(f"Unexpected error reporting usage: {e}")
                return False

        return False

    async def _get_overage_subscription_item(
        self, subscription_id: str, overage_price_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get the subscription item for overage pricing."""
        try:
            return await self.stripe_client.get_subscription_item_for_price(
                subscription_id, overage_price_id
            )
        except Exception as e:
            logger.error(f"Failed to get subscription item: {e}")
            return None

    def _group_records_by_user(self, records: List[Any]) -> Dict[str, List[Any]]:
        """Group usage records by user ID."""
        user_records: Dict[str, List[Any]] = {}

        for record in records:
            user_id = record.user_id
            if user_id not in user_records:
                user_records[user_id] = []
            user_records[user_id].append(record)

        return user_records

    def _aggregate_usage_by_period(self, records: List[Any]) -> Dict[str, List[Any]]:
        """Aggregate usage records by billing period."""
        period_records: Dict[str, List[Any]] = {}

        for record in records:
            period = record.billing_period
            if period not in period_records:
                period_records[period] = []
            period_records[period].append(record)

        return period_records

    async def process_hourly_usage_reporting(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Process hourly usage reporting task.

        This is the main entry point for scheduled usage reporting.

        Args:
            db: Database session

        Returns:
            Processing results
        """
        try:
            logger.info("Starting hourly usage reporting")

            # Report all unreported usage with a reasonable batch size
            results = await self.report_all_unreported_usage(db, limit=500)

            logger.info(
                "Hourly usage reporting complete: "
                f"{results['records_reported']} reported, "
                f"{results['records_failed']} failed"
            )

            return results

        except Exception as e:
            logger.error(f"Hourly usage reporting failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "records_processed": 0,
                "records_reported": 0,
                "records_failed": 0,
            }
