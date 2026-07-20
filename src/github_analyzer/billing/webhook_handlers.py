# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Stripe webhook event handlers.

This module provides individual handlers for different Stripe webhook events
with proper error handling and idempotency.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import SubscriptionPlan, SubscriptionStatus
from ..database.operations import (
    InvoiceOperations,
    PaymentOperations,
    UserOperations,
)
from ..utils.logging import get_logger
from .stripe_client import StripeClient
from .subscription_manager import SubscriptionManager

logger = get_logger(__name__)


class WebhookHandlerError(Exception):
    """Custom exception for webhook handler errors."""

    pass


class WebhookHandlers:
    """
    Collection of Stripe webhook event handlers.

    Each handler is responsible for processing a specific webhook event type
    and updating the local database accordingly.
    """

    def __init__(self) -> None:
        """Initialize webhook handlers."""
        self.stripe_client = StripeClient()
        self.subscription_manager = SubscriptionManager()

    async def handle_customer_subscription_created(
        self, db: AsyncSession, event: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle customer.subscription.created webhook.

        Args:
            db: Database session
            event: Stripe webhook event data

        Returns:
            Processing result

        Raises:
            WebhookHandlerError: If handling fails
        """
        try:
            subscription_data = event["data"]["object"]
            customer_id = subscription_data["customer"]

            # Get user by Stripe customer ID
            user = await UserOperations.get_user_by_stripe_customer_id(db, customer_id)
            if not user:
                logger.warning(f"User not found for Stripe customer {customer_id}")
                return {"status": "ignored", "reason": "User not found"}

            # Map Stripe price to our subscription plan
            price_id = subscription_data["items"]["data"][0]["price"]["id"]
            plan = self._map_price_to_plan(price_id)
            if not plan:
                logger.warning(f"Unknown price ID: {price_id}")
                return {"status": "ignored", "reason": "Unknown price ID"}

            # Update user subscription
            await self._update_user_subscription_from_stripe_data(
                db, user, subscription_data, plan
            )

            logger.info(f"Processed subscription created for user {user.user_id}")
            return {
                "status": "processed",
                "user_id": user.user_id,
                "subscription_id": subscription_data["id"],
                "plan": plan.value,
            }

        except Exception as e:
            logger.error(f"Failed to handle subscription created: {e}")
            raise WebhookHandlerError(f"Subscription created handler failed: {e}")

    async def handle_customer_subscription_updated(
        self, db: AsyncSession, event: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle customer.subscription.updated webhook.

        Args:
            db: Database session
            event: Stripe webhook event data

        Returns:
            Processing result

        Raises:
            WebhookHandlerError: If handling fails
        """
        try:
            subscription_data = event["data"]["object"]
            subscription_id = subscription_data["id"]
            customer_id = subscription_data["customer"]

            # First try to get user by Stripe subscription ID
            user = await UserOperations.get_user_by_stripe_subscription_id(
                db, subscription_id
            )

            # If not found, try by customer ID (happens when subscription is just created via checkout)
            if not user:
                user = await UserOperations.get_user_by_stripe_customer_id(
                    db, customer_id
                )

            if not user:
                logger.warning(
                    f"User not found for subscription {subscription_id} or customer {customer_id}"
                )
                return {"status": "ignored", "reason": "User not found"}

            # Check if this is a plan change
            price_id = subscription_data["items"]["data"][0]["price"]["id"]
            new_plan = self._map_price_to_plan(price_id)
            plan_changed = new_plan and new_plan != user.subscription_plan

            # Update user subscription
            await self._update_user_subscription_from_stripe_data(
                db, user, subscription_data, new_plan or user.subscription_plan
            )

            logger.info(f"Processed subscription updated for user {user.user_id}")
            return {
                "status": "processed",
                "user_id": user.user_id,
                "subscription_id": subscription_id,
                "plan_changed": plan_changed,
                "new_plan": new_plan.value if new_plan else None,
            }

        except Exception as e:
            logger.error(f"Failed to handle subscription updated: {e}")
            raise WebhookHandlerError(f"Subscription updated handler failed: {e}")

    async def handle_customer_subscription_deleted(
        self, db: AsyncSession, event: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle customer.subscription.deleted webhook.

        Args:
            db: Database session
            event: Stripe webhook event data

        Returns:
            Processing result

        Raises:
            WebhookHandlerError: If handling fails
        """
        try:
            subscription_data = event["data"]["object"]
            subscription_id = subscription_data["id"]
            customer_id = subscription_data["customer"]

            # First try to get user by Stripe subscription ID
            user = await UserOperations.get_user_by_stripe_subscription_id(
                db, subscription_id
            )

            # If not found, try by customer ID
            if not user:
                user = await UserOperations.get_user_by_stripe_customer_id(
                    db, customer_id
                )

            if not user:
                logger.warning(
                    f"User not found for subscription {subscription_id} or customer {customer_id}"
                )
                return {"status": "ignored", "reason": "User not found"}

            # Downgrade to free plan
            from .subscription_manager import PlanFeatures

            free_plan_limits = PlanFeatures.get_plan_limits(SubscriptionPlan.FREE)

            await UserOperations.update_user_subscription(
                db,
                user.user_id,
                subscription_plan=SubscriptionPlan.FREE,
                subscription_status=SubscriptionStatus.CANCELED,
                subscription_end_date=datetime.now(timezone.utc),
                usage_quota=free_plan_limits["monthly_analyses"],
                stripe_subscription_id=None,  # Clear subscription ID
            )

            logger.info(f"Processed subscription deleted for user {user.user_id}")
            return {
                "status": "processed",
                "user_id": user.user_id,
                "subscription_id": subscription_id,
                "downgraded_to": "free",
            }

        except Exception as e:
            logger.error(f"Failed to handle subscription deleted: {e}")
            raise WebhookHandlerError(f"Subscription deleted handler failed: {e}")

    async def handle_invoice_payment_succeeded(
        self, db: AsyncSession, event: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle invoice.payment_succeeded webhook.

        This handles both initial subscription payments and renewals.
        For renewals, it updates the subscription period dates.

        Args:
            db: Database session
            event: Stripe webhook event data

        Returns:
            Processing result

        Raises:
            WebhookHandlerError: If handling fails
        """
        try:
            invoice_data = event["data"]["object"]
            stripe_invoice_id = invoice_data["id"]

            # Skip $0 invoices in TEST mode (common for initial subscription setup)
            amount_due = invoice_data.get("amount_due", 0)
            amount_paid = invoice_data.get("amount_paid", 0)
            if amount_due == 0 and amount_paid == 0:
                logger.info(
                    f"Skipping $0 invoice {stripe_invoice_id} (TEST mode initial setup)"
                )
                return {
                    "status": "ignored",
                    "reason": "Zero amount invoice - TEST mode initial setup",
                }

            # Check if we already have this invoice
            existing_invoice = await InvoiceOperations.get_invoice_by_stripe_id(
                db, stripe_invoice_id
            )

            if existing_invoice:
                # Update existing invoice
                await InvoiceOperations.update_invoice_status(
                    db,
                    existing_invoice.invoice_id,
                    status="paid",
                    amount_paid=invoice_data["amount_paid"],
                    paid_at=datetime.fromtimestamp(
                        invoice_data.get("status_transitions", {}).get(
                            "paid_at", datetime.now(timezone.utc).timestamp()
                        ),
                        tz=timezone.utc,
                    ),
                )

                # For existing invoices (renewals), also update subscription dates
                customer_id = invoice_data["customer"]
                user = await UserOperations.get_user_by_stripe_customer_id(
                    db, customer_id
                )

                if user and invoice_data.get("subscription"):
                    # This is a renewal - update the subscription period dates
                    await UserOperations.update_user_subscription(
                        db,
                        user.user_id,
                        subscription_start_date=datetime.fromtimestamp(
                            invoice_data["period_start"], tz=timezone.utc
                        ),
                        subscription_end_date=datetime.fromtimestamp(
                            invoice_data["period_end"], tz=timezone.utc
                        ),
                    )
                    logger.info(
                        f"Updated subscription renewal dates for user {user.user_id}: "
                        f"{datetime.fromtimestamp(invoice_data['period_start'])} to "
                        f"{datetime.fromtimestamp(invoice_data['period_end'])}"
                    )

                logger.info(f"Updated existing invoice {existing_invoice.invoice_id}")
                return {
                    "status": "processed",
                    "action": "updated",
                    "invoice_id": existing_invoice.invoice_id,
                }
            else:
                # Create new invoice record
                customer_id = invoice_data["customer"]
                user = await UserOperations.get_user_by_stripe_customer_id(
                    db, customer_id
                )

                if not user:
                    logger.warning(f"User not found for customer {customer_id}")
                    return {"status": "ignored", "reason": "User not found"}

                # Generate invoice ID
                invoice_id = f"inv_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{user.user_id[:8]}"

                # For subscription invoices, get the actual amount from subscription price
                actual_amount = invoice_data.get("amount_due", 0)
                if actual_amount == 0 and invoice_data.get("subscription"):
                    # Try to get amount from line items
                    lines = invoice_data.get("lines", {}).get("data", [])
                    for line in lines:
                        if line.get("type") == "subscription":
                            actual_amount = line.get("amount", 0)
                            break

                # Still skip if amount is 0
                if actual_amount == 0:
                    logger.info(f"Skipping zero-amount invoice {stripe_invoice_id}")
                    return {
                        "status": "ignored",
                        "reason": "Zero amount invoice",
                    }

                # For paid invoices, amount_paid should match amount_due
                amount_paid = invoice_data.get("amount_paid", actual_amount)

                invoice = await InvoiceOperations.create_invoice(
                    db=db,
                    invoice_id=invoice_id,
                    user_id=user.user_id,
                    stripe_invoice_id=stripe_invoice_id,
                    stripe_customer_id=customer_id,
                    amount_due=actual_amount,
                    amount_paid=amount_paid,  # Add the actual paid amount
                    currency=invoice_data["currency"],
                    status="paid",
                    billing_period_start=datetime.fromtimestamp(
                        invoice_data["period_start"], tz=timezone.utc
                    ),
                    billing_period_end=datetime.fromtimestamp(
                        invoice_data["period_end"], tz=timezone.utc
                    ),
                    description=invoice_data.get("description"),
                    invoice_url=invoice_data.get("hosted_invoice_url"),
                    due_date=(
                        datetime.fromtimestamp(
                            invoice_data["due_date"], tz=timezone.utc
                        )
                        if invoice_data.get("due_date")
                        else None
                    ),
                )

                # Create payment record if payment intent exists
                if invoice_data.get("payment_intent"):
                    payment_intent_id = invoice_data["payment_intent"]
                    payment_id = f"pay_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{user.user_id[:8]}"

                    await PaymentOperations.create_payment(
                        db=db,
                        payment_id=payment_id,
                        user_id=user.user_id,
                        invoice_id=invoice.invoice_id,
                        stripe_payment_intent_id=payment_intent_id,
                        stripe_customer_id=customer_id,
                        amount=invoice_data["amount_paid"],
                        currency=invoice_data["currency"],
                        status="succeeded",
                        payment_method="card",  # Default assumption
                        processed_at=datetime.now(timezone.utc),
                    )

                # If this invoice is for a subscription, update user's subscription details
                # This is especially important for renewals to update the period dates
                if invoice_data.get("subscription"):
                    stripe_subscription_id = invoice_data["subscription"]

                    # Get the subscription details from Stripe
                    subscription = await self.stripe_client.get_subscription(
                        stripe_subscription_id
                    )
                    if subscription:
                        # Get the price ID from subscription to determine plan
                        if subscription.get("items", {}).get("data"):
                            price_id = subscription["items"]["data"][0]["price"]["id"]
                            plan = self._map_price_to_plan(price_id)

                            if plan:
                                # Update user subscription details
                                await self._update_user_subscription_from_stripe_data(
                                    db, user, subscription, plan
                                )

                                # ALWAYS update the subscription period dates from the subscription
                                # Use subscription period, not invoice period (invoice periods can be same for setup)
                                subscription_start = subscription.get(
                                    "current_period_start"
                                )
                                subscription_end = subscription.get(
                                    "current_period_end"
                                )

                                if subscription_start and subscription_end:
                                    await UserOperations.update_user_subscription(
                                        db,
                                        user.user_id,
                                        subscription_start_date=datetime.fromtimestamp(
                                            subscription_start, tz=timezone.utc
                                        ),
                                        subscription_end_date=datetime.fromtimestamp(
                                            subscription_end, tz=timezone.utc
                                        ),
                                    )
                                    logger.info(
                                        f"Updated subscription period dates for user {user.user_id}: "
                                        f"{datetime.fromtimestamp(subscription_start, tz=timezone.utc)} to "
                                        f"{datetime.fromtimestamp(subscription_end, tz=timezone.utc)}"
                                    )

                logger.info(
                    f"Created new invoice {invoice.invoice_id} for payment success"
                )
                return {
                    "status": "processed",
                    "action": "created",
                    "invoice_id": invoice.invoice_id,
                    "user_id": user.user_id,
                }

        except Exception as e:
            logger.error(f"Failed to handle payment succeeded: {e}")
            raise WebhookHandlerError(f"Payment succeeded handler failed: {e}")

    async def handle_invoice_finalized(
        self, db: AsyncSession, event: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle invoice.finalized webhook.

        This event is triggered when an invoice is finalized and ready for payment.
        For metered billing, this is when overage charges are added to the invoice.

        Args:
            db: Database session
            event: Stripe webhook event data

        Returns:
            Processing result

        Raises:
            WebhookHandlerError: If handling fails
        """
        try:
            invoice_data = event["data"]["object"]
            stripe_invoice_id = invoice_data["id"]
            customer_id = invoice_data["customer"]

            # Get user by Stripe customer ID
            user = await UserOperations.get_user_by_stripe_customer_id(db, customer_id)
            if not user:
                logger.warning(f"User not found for customer {customer_id}")
                return {"status": "ignored", "reason": "User not found"}

            # Check if this invoice has metered line items (overage charges)
            has_metered_items = False
            overage_amount = 0

            for line_item in invoice_data.get("lines", {}).get("data", []):
                if (
                    line_item.get("price", {}).get("recurring", {}).get("usage_type")
                    == "metered"
                ):
                    has_metered_items = True
                    overage_amount += line_item.get("amount", 0)

            # Check if we already have this invoice
            existing_invoice = await InvoiceOperations.get_invoice_by_stripe_id(
                db, stripe_invoice_id
            )

            if existing_invoice:
                # Update existing invoice with finalized details
                await InvoiceOperations.update_invoice_status(
                    db,
                    existing_invoice.invoice_id,
                    status="finalized",
                )
                logger.info(
                    f"Updated existing invoice {existing_invoice.invoice_id} as finalized"
                )
                return {
                    "status": "processed",
                    "action": "updated",
                    "invoice_id": existing_invoice.invoice_id,
                    "has_overage": has_metered_items,
                    "overage_amount": overage_amount,
                }
            else:
                # Create new invoice record
                invoice_id = f"inv_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{user.user_id[:8]}"

                invoice = await InvoiceOperations.create_invoice(
                    db=db,
                    invoice_id=invoice_id,
                    user_id=user.user_id,
                    stripe_invoice_id=stripe_invoice_id,
                    stripe_customer_id=customer_id,
                    amount_due=invoice_data["amount_due"],
                    currency=invoice_data["currency"],
                    status="finalized",
                    billing_period_start=datetime.fromtimestamp(
                        invoice_data["period_start"], tz=timezone.utc
                    ),
                    billing_period_end=datetime.fromtimestamp(
                        invoice_data["period_end"], tz=timezone.utc
                    ),
                    description=invoice_data.get("description"),
                    invoice_url=invoice_data.get("hosted_invoice_url"),
                    due_date=(
                        datetime.fromtimestamp(
                            invoice_data["due_date"], tz=timezone.utc
                        )
                        if invoice_data.get("due_date")
                        else None
                    ),
                )

                logger.info(
                    f"Created new invoice {invoice.invoice_id} for finalized event"
                )
                return {
                    "status": "processed",
                    "action": "created",
                    "invoice_id": invoice.invoice_id,
                    "user_id": user.user_id,
                    "has_overage": has_metered_items,
                    "overage_amount": overage_amount,
                }

        except Exception as e:
            logger.error(f"Failed to handle invoice finalized: {e}")
            raise WebhookHandlerError(f"Invoice finalized handler failed: {e}")

    async def handle_invoice_created(
        self, db: AsyncSession, event: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle invoice.created webhook.

        This event is triggered when a new invoice is created.
        We track it to ensure we capture all invoices, especially those with overages.

        Args:
            db: Database session
            event: Stripe webhook event data

        Returns:
            Processing result

        Raises:
            WebhookHandlerError: If handling fails
        """
        try:
            invoice_data = event["data"]["object"]
            stripe_invoice_id = invoice_data["id"]
            customer_id = invoice_data["customer"]

            # Get user by Stripe customer ID
            user = await UserOperations.get_user_by_stripe_customer_id(db, customer_id)
            if not user:
                logger.warning(f"User not found for customer {customer_id}")
                return {"status": "ignored", "reason": "User not found"}

            # Check if we already have this invoice
            existing_invoice = await InvoiceOperations.get_invoice_by_stripe_id(
                db, stripe_invoice_id
            )

            if existing_invoice:
                logger.info(f"Invoice {existing_invoice.invoice_id} already exists")
                return {
                    "status": "processed",
                    "action": "already_exists",
                    "invoice_id": existing_invoice.invoice_id,
                }

            # Create new invoice record with draft status
            invoice_id = f"inv_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{user.user_id[:8]}"

            invoice = await InvoiceOperations.create_invoice(
                db=db,
                invoice_id=invoice_id,
                user_id=user.user_id,
                stripe_invoice_id=stripe_invoice_id,
                stripe_customer_id=customer_id,
                amount_due=invoice_data["amount_due"],
                currency=invoice_data["currency"],
                status="draft",
                billing_period_start=datetime.fromtimestamp(
                    invoice_data["period_start"], tz=timezone.utc
                ),
                billing_period_end=datetime.fromtimestamp(
                    invoice_data["period_end"], tz=timezone.utc
                ),
                description=invoice_data.get("description"),
                due_date=(
                    datetime.fromtimestamp(invoice_data["due_date"], tz=timezone.utc)
                    if invoice_data.get("due_date")
                    else None
                ),
            )

            logger.info(f"Created new invoice {invoice.invoice_id} for created event")
            return {
                "status": "processed",
                "action": "created",
                "invoice_id": invoice.invoice_id,
                "user_id": user.user_id,
            }

        except Exception as e:
            logger.error(f"Failed to handle invoice created: {e}")
            raise WebhookHandlerError(f"Invoice created handler failed: {e}")

    async def handle_invoice_payment_failed(
        self, db: AsyncSession, event: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle invoice.payment_failed webhook.

        Args:
            db: Database session
            event: Stripe webhook event data

        Returns:
            Processing result

        Raises:
            WebhookHandlerError: If handling fails
        """
        try:
            invoice_data = event["data"]["object"]
            stripe_invoice_id = invoice_data["id"]
            customer_id = invoice_data["customer"]

            # Get user by Stripe customer ID
            user = await UserOperations.get_user_by_stripe_customer_id(db, customer_id)
            if not user:
                logger.warning(f"User not found for customer {customer_id}")
                return {"status": "ignored", "reason": "User not found"}

            # Update user subscription status to past_due
            await UserOperations.update_user_subscription(
                db, user.user_id, subscription_status=SubscriptionStatus.PAST_DUE
            )

            # Update or create invoice record
            existing_invoice = await InvoiceOperations.get_invoice_by_stripe_id(
                db, stripe_invoice_id
            )

            if existing_invoice:
                await InvoiceOperations.update_invoice_status(
                    db,
                    existing_invoice.invoice_id,
                    status="open",  # Failed payment keeps invoice open
                )
                invoice_id = existing_invoice.invoice_id
            else:
                # Create invoice record for failed payment
                invoice_id = f"inv_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{user.user_id[:8]}"

                await InvoiceOperations.create_invoice(
                    db=db,
                    invoice_id=invoice_id,
                    user_id=user.user_id,
                    stripe_invoice_id=stripe_invoice_id,
                    stripe_customer_id=customer_id,
                    amount_due=invoice_data["amount_due"],
                    currency=invoice_data["currency"],
                    status="open",
                    billing_period_start=datetime.fromtimestamp(
                        invoice_data["period_start"], tz=timezone.utc
                    ),
                    billing_period_end=datetime.fromtimestamp(
                        invoice_data["period_end"], tz=timezone.utc
                    ),
                    description=invoice_data.get("description"),
                    due_date=(
                        datetime.fromtimestamp(
                            invoice_data["due_date"], tz=timezone.utc
                        )
                        if invoice_data.get("due_date")
                        else None
                    ),
                )

            # Create failed payment record if payment intent exists
            if invoice_data.get("payment_intent"):
                payment_intent_id = invoice_data["payment_intent"]
                payment_id = f"pay_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{user.user_id[:8]}"

                await PaymentOperations.create_payment(
                    db=db,
                    payment_id=payment_id,
                    user_id=user.user_id,
                    invoice_id=invoice_id,
                    stripe_payment_intent_id=payment_intent_id,
                    stripe_customer_id=customer_id,
                    amount=invoice_data["amount_due"],
                    currency=invoice_data["currency"],
                    status="failed",
                    payment_method="card",  # Default assumption
                    failure_message="Payment failed",
                    processed_at=datetime.now(timezone.utc),
                )

            logger.info(f"Processed payment failed for user {user.user_id}")
            return {
                "status": "processed",
                "user_id": user.user_id,
                "invoice_id": invoice_id,
                "subscription_status": "past_due",
            }

        except Exception as e:
            logger.error(f"Failed to handle payment failed: {e}")
            raise WebhookHandlerError(f"Payment failed handler failed: {e}")

    def _map_price_to_plan(self, price_id: str) -> Optional[SubscriptionPlan]:
        """Map Stripe price ID to subscription plan."""
        price_mapping = {
            # Production LIVE price IDs
            "price_1S9YiLRvLpeUOuiGRnTXyNKg": SubscriptionPlan.BASIC,  # Starter $49
            "price_1S9YiKRvLpeUOuiGvPZwMfRu": SubscriptionPlan.PROFESSIONAL,  # Growth $199
            "price_1S9YiIRvLpeUOuiGNg81hyNC": SubscriptionPlan.ENTERPRISE,  # Scale $499
            "price_1S9YiFRvLpeUOuiGNzVKirF4": SubscriptionPlan.SCALE_PLUS,  # Scale+ $2500
            # TEST mode price IDs (for testing - these won't trigger live charges)
            "price_1S3yVb2NUcXbQPePzeWEUswZ": SubscriptionPlan.BASIC,  # TEST Starter (Updated)
            "price_1SLwIi2NUcXbQPePzO8UXflv": SubscriptionPlan.PROFESSIONAL,  # TEST Growth (Updated)
            "price_1SLwJc2NUcXbQPePqhUMHM8t": SubscriptionPlan.ENTERPRISE,  # TEST Scale (Updated)
            "price_1S7dsSRvLpeUOuiGm51xWxcU": SubscriptionPlan.SCALE_PLUS,  # TEST Scale+
            # Mock price IDs (for unit tests)
            "price_basic_monthly": SubscriptionPlan.BASIC,
            "price_professional_monthly": SubscriptionPlan.PROFESSIONAL,
            "price_enterprise_monthly": SubscriptionPlan.ENTERPRISE,
            "price_scale_plus_monthly": SubscriptionPlan.SCALE_PLUS,
        }
        return price_mapping.get(price_id)

    async def _update_user_subscription_from_stripe_data(
        self,
        db: AsyncSession,
        user: Any,
        subscription_data: Dict[str, Any],
        plan: SubscriptionPlan,
    ) -> None:
        """Update user subscription from Stripe subscription data."""
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
        from .subscription_manager import PlanFeatures

        plan_limits = PlanFeatures.get_plan_limits(plan)

        # Get period dates - these might be in different places depending on the event
        # For checkout.session.completed, they're at the root level
        # For subscription events, check both root and latest_invoice
        current_period_start = subscription_data.get("current_period_start")
        current_period_end = subscription_data.get("current_period_end")

        # If not found at root, check in latest_invoice
        if not current_period_start and "latest_invoice" in subscription_data:
            latest_invoice = subscription_data["latest_invoice"]
            if isinstance(latest_invoice, dict):
                # If latest_invoice is expanded
                current_period_start = latest_invoice.get("period_start")
                current_period_end = latest_invoice.get("period_end")

        # Default to created timestamp and 30 days later if still not found
        if not current_period_start:
            current_period_start = subscription_data.get(
                "created", subscription_data.get("start_date")
            )
        if not current_period_end and current_period_start:
            # Default to 30 days from start
            current_period_end = current_period_start + (30 * 24 * 60 * 60)

        # Convert timestamps to datetime if we have them
        subscription_start = None
        subscription_end = None
        if current_period_start:
            subscription_start = datetime.fromtimestamp(
                current_period_start, tz=timezone.utc
            )
        if current_period_end:
            subscription_end = datetime.fromtimestamp(
                current_period_end, tz=timezone.utc
            )

        # Update user subscription
        update_params = {
            "subscription_plan": plan,
            "subscription_status": status,
            "usage_quota": plan_limits["monthly_analyses"],
            "stripe_subscription_id": subscription_data["id"],
        }

        # Only add dates if we have them
        if subscription_start:
            update_params["subscription_start_date"] = subscription_start
        if subscription_end:
            update_params["subscription_end_date"] = subscription_end

        await UserOperations.update_user_subscription(db, user.user_id, **update_params)


# Global webhook handler registry
WEBHOOK_HANDLERS = {
    "customer.subscription.created": WebhookHandlers().handle_customer_subscription_created,
    "customer.subscription.updated": WebhookHandlers().handle_customer_subscription_updated,
    "customer.subscription.deleted": WebhookHandlers().handle_customer_subscription_deleted,
    "invoice.created": WebhookHandlers().handle_invoice_created,
    "invoice.finalized": WebhookHandlers().handle_invoice_finalized,
    "invoice.payment_succeeded": WebhookHandlers().handle_invoice_payment_succeeded,
    "invoice.payment_failed": WebhookHandlers().handle_invoice_payment_failed,
}
