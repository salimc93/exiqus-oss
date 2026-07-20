# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Stripe API client for billing operations.

This module provides a secure, centralized interface to the Stripe API
with proper error handling, retry logic, and logging.
"""

import os
import sys
from typing import Any, Dict, List, Optional

import stripe
from stripe import StripeError

from ..utils.config import get_config
from ..utils.logging import get_logger

logger = get_logger(__name__)

# Metered billing price IDs for overage charges
OVERAGE_PRICE_IDS = {
    "professional": "price_professional_overage",  # $0.20 per overage call
    "enterprise": "price_enterprise_overage",  # $0.10 per overage call
}


class StripeClientError(Exception):
    """Custom exception for Stripe client errors."""

    def __init__(self, message: str, stripe_error: Optional[StripeError] = None):
        super().__init__(message)
        self.stripe_error = stripe_error


class StripeClient:
    """
    Centralized Stripe API client with enterprise-grade error handling.

    Provides secure access to Stripe APIs for customer management,
    subscription operations, and payment processing.
    """

    def __init__(self) -> None:
        """Initialize Stripe client with configuration."""
        self.config = get_config()
        self.is_configured = False
        self._setup_stripe()

    def _is_test_environment(self) -> bool:
        """Check if running in test environment."""
        return (
            "pytest" in sys.modules
            or "PYTEST_CURRENT_TEST" in os.environ
            or any("test" in arg for arg in sys.argv)
        )

    def _setup_stripe(self) -> None:
        """Configure Stripe with API keys and settings."""
        try:
            # Get Stripe keys from config
            stripe_secret_key = self.config._get_str("STRIPE_SECRET_KEY", "")
            if not stripe_secret_key:
                # In test/development mode, allow graceful degradation
                logger.warning(
                    "STRIPE_SECRET_KEY not configured - Stripe client will not be functional"
                )
                return

            # Set Stripe API key
            stripe.api_key = stripe_secret_key

            # Configure Stripe client settings
            stripe.api_version = "2024-12-18.acacia"  # Latest API version
            stripe.max_network_retries = 3
            self.is_configured = True

            logger.info("Stripe client initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Stripe client: {e}")
            raise StripeClientError(f"Stripe initialization failed: {e}")

    async def create_customer(
        self,
        email: str,
        user_id: str,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new Stripe customer.

        Args:
            email: Customer email address
            user_id: Internal user ID for tracking
            name: Customer full name
            metadata: Additional customer metadata

        Returns:
            Dict containing customer data

        Raises:
            StripeClientError: If customer creation fails
        """
        if not self.is_configured:
            raise StripeClientError("Stripe client not configured")

        try:
            # Create customer with properly typed parameters
            customer_params: Dict[str, Any] = {
                "email": email,
                "metadata": {"exiqus_user_id": user_id, **(metadata or {})},
            }

            if name:
                customer_params["name"] = name

            customer = stripe.Customer.create(**customer_params)

            logger.info(f"Created Stripe customer {customer.id} for user {user_id}")
            return customer.to_dict()

        except StripeError as e:
            logger.error(f"Stripe customer creation failed: {e}")
            raise StripeClientError(f"Failed to create customer: {e.user_message}", e)
        except Exception as e:
            logger.error(f"Unexpected error creating customer: {e}")
            raise StripeClientError(f"Customer creation failed: {e}")

    async def get_customer(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a Stripe customer by ID.

        Args:
            customer_id: Stripe customer ID

        Returns:
            Customer data or None if not found

        Raises:
            StripeClientError: If retrieval fails
        """
        # In test environment, return None to avoid real API calls
        if self._is_test_environment():
            logger.debug("Test environment detected, returning None for get_customer")
            return None

        if not self.is_configured:
            logger.warning("Stripe client not configured, returning None for customer")
            return None

        try:
            customer = stripe.Customer.retrieve(customer_id)
            return customer.to_dict()

        except stripe.InvalidRequestError as e:
            if "No such customer" in str(e):
                logger.warning(f"Customer {customer_id} not found")
                return None
            raise StripeClientError(f"Failed to retrieve customer: {e.user_message}", e)
        except StripeError as e:
            logger.error(f"Stripe customer retrieval failed: {e}")
            raise StripeClientError(f"Failed to retrieve customer: {e.user_message}", e)

    async def create_subscription(
        self, customer_id: str, price_id: str, metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Create a subscription for a customer.

        Args:
            customer_id: Stripe customer ID
            price_id: Stripe price ID for the subscription
            metadata: Additional subscription metadata

        Returns:
            Subscription data

        Raises:
            StripeClientError: If subscription creation fails
        """
        try:
            # Create subscription with properly typed parameters
            subscription_params: Dict[str, Any] = {
                "customer": customer_id,
                "items": [{"price": price_id}],
                "payment_behavior": "default_incomplete",
                "payment_settings": {"save_default_payment_method": "on_subscription"},
                "expand": ["latest_invoice.payment_intent"],
            }

            if metadata:
                subscription_params["metadata"] = metadata

            subscription = stripe.Subscription.create(**subscription_params)

            logger.info(
                f"Created subscription {subscription.id} for customer {customer_id}"
            )
            return subscription.to_dict()

        except StripeError as e:
            logger.error(f"Stripe subscription creation failed: {e}")
            raise StripeClientError(
                f"Failed to create subscription: {e.user_message}", e
            )

    async def get_subscription(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a subscription by ID.

        Args:
            subscription_id: Stripe subscription ID

        Returns:
            Subscription data or None if not found

        Raises:
            StripeClientError: If retrieval fails
        """
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return subscription.to_dict()

        except stripe.InvalidRequestError as e:
            if "No such subscription" in str(e):
                logger.warning(f"Subscription {subscription_id} not found")
                return None
            raise StripeClientError(
                f"Failed to retrieve subscription: {e.user_message}", e
            )
        except StripeError as e:
            logger.error(f"Stripe subscription retrieval failed: {e}")
            raise StripeClientError(
                f"Failed to retrieve subscription: {e.user_message}", e
            )

    async def update_subscription(
        self, subscription_id: str, **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Update a subscription.

        Args:
            subscription_id: Stripe subscription ID
            **kwargs: Fields to update

        Returns:
            Updated subscription data

        Raises:
            StripeClientError: If update fails
        """
        if not self.is_configured:
            raise StripeClientError("Stripe client not configured")

        try:
            subscription = stripe.Subscription.retrieve(subscription_id)

            # Handle rate limit errors with special logic
            try:
                subscription = stripe.Subscription.modify(subscription_id, **kwargs)
            except stripe.RateLimitError as e:
                logger.error(f"Rate limit error updating subscription: {e}")
                raise StripeClientError(f"Failed to update subscription: {str(e)}")

            logger.info(f"Updated subscription {subscription_id}")
            return subscription.to_dict()

        except StripeError as e:
            logger.error(f"Stripe subscription update failed: {e}")
            raise StripeClientError(f"Failed to update subscription: {str(e)}")

    async def cancel_subscription(
        self, subscription_id: str, at_period_end: bool = True
    ) -> Dict[str, Any]:
        """
        Cancel a subscription.

        Args:
            subscription_id: Stripe subscription ID
            at_period_end: Whether to cancel at period end or immediately

        Returns:
            Cancelled subscription data

        Raises:
            StripeClientError: If cancellation fails
        """
        try:
            if at_period_end:
                # Cancel at period end
                subscription = stripe.Subscription.modify(
                    subscription_id, cancel_at_period_end=True
                )
            else:
                # Cancel immediately
                subscription = stripe.Subscription.cancel(subscription_id)

            logger.info(
                f"Cancelled subscription {subscription_id} (at_period_end={at_period_end})"
            )
            return subscription.to_dict()

        except StripeError as e:
            logger.error(f"Stripe subscription cancellation failed: {e}")
            raise StripeClientError(
                f"Failed to cancel subscription: {e.user_message}", e
            )

    async def list_customer_subscriptions(
        self, customer_id: str, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List all subscriptions for a customer.

        Args:
            customer_id: Stripe customer ID
            status: Filter by subscription status

        Returns:
            List of subscription data

        Raises:
            StripeClientError: If listing fails
        """
        try:
            # List subscriptions with properly typed parameters
            list_params: Dict[str, Any] = {"customer": customer_id, "limit": 100}
            if status:
                list_params["status"] = status

            subscriptions = stripe.Subscription.list(**list_params)

            return [sub.to_dict() for sub in subscriptions.data]

        except StripeError as e:
            logger.error(f"Stripe subscription listing failed: {e}")
            raise StripeClientError(
                f"Failed to list subscriptions: {e.user_message}", e
            )

    async def create_checkout_session(
        self,
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a Stripe Checkout session for subscription signup.

        Args:
            customer_id: Stripe customer ID
            price_id: Stripe price ID
            success_url: URL to redirect after successful payment
            cancel_url: URL to redirect if payment cancelled
            metadata: Additional session metadata

        Returns:
            Checkout session data

        Raises:
            StripeClientError: If session creation fails
        """
        if not self.is_configured:
            raise StripeClientError("Stripe client not configured")

        try:
            # Create checkout session with properly typed parameters
            session_params: Dict[str, Any] = {
                "customer": customer_id,
                "payment_method_types": ["card"],
                "mode": "subscription",
                "line_items": [{"price": price_id, "quantity": 1}],
                "success_url": success_url,
                "cancel_url": cancel_url,
                "allow_promotion_codes": True,
            }

            if metadata:
                session_params["metadata"] = metadata

            session = stripe.checkout.Session.create(**session_params)

            logger.info(
                f"Created checkout session {session.id} for customer {customer_id}"
            )
            return session.to_dict()

        except StripeError as e:
            logger.error(f"Stripe checkout session creation failed: {e}")
            raise StripeClientError(
                f"Failed to create checkout session: {e.user_message}", e
            )

    async def get_invoice(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve an invoice by ID.

        Args:
            invoice_id: Stripe invoice ID

        Returns:
            Invoice data or None if not found

        Raises:
            StripeClientError: If retrieval fails
        """
        try:
            invoice = stripe.Invoice.retrieve(invoice_id)
            return invoice.to_dict()

        except stripe.InvalidRequestError as e:
            if "No such invoice" in str(e):
                logger.warning(f"Invoice {invoice_id} not found")
                return None
            raise StripeClientError(f"Failed to retrieve invoice: {e.user_message}", e)
        except StripeError as e:
            logger.error(f"Stripe invoice retrieval failed: {e}")
            raise StripeClientError(f"Failed to retrieve invoice: {e.user_message}", e)

    async def list_customer_invoices(
        self, customer_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        List invoices for a customer.

        Args:
            customer_id: Stripe customer ID
            limit: Maximum number of invoices to return

        Returns:
            List of invoice data

        Raises:
            StripeClientError: If listing fails
        """
        try:
            invoices = stripe.Invoice.list(customer=customer_id, limit=limit)

            return [invoice.to_dict() for invoice in invoices.data]

        except StripeError as e:
            logger.error(f"Stripe invoice listing failed: {e}")
            raise StripeClientError(f"Failed to list invoices: {e.user_message}", e)

    def verify_webhook_signature(
        self, payload: bytes, signature: str, webhook_secret: str
    ) -> Dict[str, Any]:
        """
        Verify Stripe webhook signature and parse event.

        Args:
            payload: Raw webhook payload
            signature: Stripe signature header
            webhook_secret: Webhook endpoint secret

        Returns:
            Parsed webhook event

        Raises:
            StripeClientError: If the secret is missing or verification fails
        """
        # Fail closed. Stripe's construct_event will happily verify against an
        # empty secret, and an attacker who guesses the deployment is
        # misconfigured can then forge any event - including subscription
        # upgrades. A missing secret must never be treated as "no signing".
        if not webhook_secret:
            logger.error(
                "STRIPE_WEBHOOK_SECRET is not configured; refusing to process "
                "webhook. Set it to the signing secret from your Stripe "
                "endpoint configuration."
            )
            raise StripeClientError("Webhook secret is not configured")

        try:
            event = stripe.Webhook.construct_event(payload, signature, webhook_secret)  # type: ignore[no-untyped-call]

            logger.info(f"Verified webhook event {event['id']} of type {event['type']}")
            return dict(event)

        except ValueError as e:
            logger.error(f"Invalid webhook payload: {e}")
            raise StripeClientError(f"Invalid payload: {e}")
        except stripe.SignatureVerificationError as e:
            logger.error(f"Webhook signature verification failed: {e}")
            raise StripeClientError(f"Invalid signature: {e}")

    async def create_usage_record(
        self,
        subscription_item_id: str,
        quantity: int,
        timestamp: Optional[int] = None,
        action: str = "increment",
    ) -> Dict[str, Any]:
        """
        Create a usage record for metered billing.

        Args:
            subscription_item_id: Stripe subscription item ID for metered product
            quantity: Usage quantity to report
            timestamp: Unix timestamp for usage (defaults to now)
            action: "increment" (add to existing) or "set" (replace)

        Returns:
            Usage record data

        Raises:
            StripeClientError: If usage record creation fails
        """
        if not self.is_configured:
            raise StripeClientError("Stripe client not configured")

        try:
            # Create usage record with properly typed parameters
            usage_params: Dict[str, Any] = {
                "quantity": quantity,
                "action": action,
            }

            if timestamp:
                usage_params["timestamp"] = timestamp

            # In older Stripe versions, this was stripe.SubscriptionItem.create_usage_record
            # For compatibility, we'll use the method directly on the SubscriptionItem
            subscription_item = stripe.SubscriptionItem.retrieve(subscription_item_id)
            usage_record = subscription_item.create_usage_record(**usage_params)

            logger.info(
                f"Created usage record for item {subscription_item_id}: "
                f"{quantity} units ({action})"
            )
            return usage_record.to_dict()

        except StripeError as e:
            logger.error(f"Stripe usage record creation failed: {e}")
            raise StripeClientError(
                f"Failed to create usage record: {e.user_message}", e
            )

    async def list_subscription_items(
        self, subscription_id: str
    ) -> List[Dict[str, Any]]:
        """
        List all items in a subscription.

        Args:
            subscription_id: Stripe subscription ID

        Returns:
            List of subscription items

        Raises:
            StripeClientError: If listing fails
        """
        if not self.is_configured:
            raise StripeClientError("Stripe client not configured")

        try:
            items = stripe.SubscriptionItem.list(
                subscription=subscription_id, limit=100
            )

            return [item.to_dict() for item in items.data]

        except StripeError as e:
            logger.error(f"Stripe subscription item listing failed: {e}")
            raise StripeClientError(
                f"Failed to list subscription items: {e.user_message}", e
            )

    async def add_metered_price_to_subscription(
        self,
        subscription_id: str,
        price_id: str,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Add a metered price (for overages) to an existing subscription.

        Args:
            subscription_id: Stripe subscription ID
            price_id: Stripe price ID for metered product
            metadata: Optional metadata for the subscription item

        Returns:
            Updated subscription data

        Raises:
            StripeClientError: If adding metered price fails
        """
        if not self.is_configured:
            raise StripeClientError("Stripe client not configured")

        try:
            # Add new item to subscription
            item_params: Dict[str, Any] = {"price": price_id}
            if metadata:
                item_params["metadata"] = metadata

            subscription = stripe.Subscription.modify(
                subscription_id,
                items=[{"price": price_id}],
                proration_behavior="none",  # Don't prorate metered items
            )

            logger.info(
                f"Added metered price {price_id} to subscription {subscription_id}"
            )
            return subscription.to_dict()

        except StripeError as e:
            logger.error(f"Failed to add metered price to subscription: {e}")
            raise StripeClientError(f"Failed to add metered price: {e.user_message}", e)

    async def get_subscription_item_for_price(
        self, subscription_id: str, price_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find subscription item for a specific price.

        Args:
            subscription_id: Stripe subscription ID
            price_id: Stripe price ID to find

        Returns:
            Subscription item data or None if not found

        Raises:
            StripeClientError: If retrieval fails
        """
        try:
            items = await self.list_subscription_items(subscription_id)

            for item in items:
                if item.get("price", {}).get("id") == price_id:
                    return item

            return None

        except StripeClientError:
            # Error already logged, return None to indicate not found
            return None
        except Exception as e:
            logger.error(f"Failed to find subscription item for price: {e}")
            return None

    async def create_metered_billing_prices(self) -> Dict[str, str]:
        """
        Create or retrieve metered billing prices for overages.

        This should be run during initial setup to ensure prices exist in Stripe.

        Returns:
            Mapping of plan names to price IDs

        Raises:
            StripeClientError: If price creation fails
        """
        if not self.is_configured:
            raise StripeClientError("Stripe client not configured")

        created_prices: Dict[str, str] = {}

        # Define overage prices with proper typing
        overage_configs: List[Dict[str, Any]] = [
            {
                "nickname": "Professional Plan Overage",
                "product_id": "prod_professional_overage",
                "unit_amount": 20,  # $0.20 in cents
                "plan_key": "professional",
            },
            {
                "nickname": "Enterprise Plan Overage",
                "product_id": "prod_enterprise_overage",
                "unit_amount": 10,  # $0.10 in cents
                "plan_key": "enterprise",
            },
        ]

        for config in overage_configs:
            try:
                # First, ensure product exists
                product_id = str(config["product_id"])
                nickname = str(config["nickname"])
                unit_amount = int(config["unit_amount"])
                plan_key = str(config["plan_key"])

                try:
                    product = stripe.Product.retrieve(product_id)
                except stripe.InvalidRequestError:
                    # Create product if it doesn't exist
                    try:
                        product = stripe.Product.create(
                            id=product_id,
                            name=nickname,
                            description=f"API usage overage charges for {nickname}",
                        )
                        logger.info(f"Created product {product.id}")
                    except StripeError as e:
                        logger.error(f"Failed to create product {product_id}: {e}")
                        raise StripeClientError(
                            f"Failed to setup metered billing: {str(e)}"
                        )

                # Check if price already exists
                prices = stripe.Price.list(product=product.id, limit=100)
                existing_price = None

                for price in prices.data:
                    if (
                        price.unit_amount == unit_amount
                        and price.recurring
                        and price.recurring.get("usage_type") == "metered"
                    ):
                        existing_price = price
                        break

                if existing_price:
                    created_prices[plan_key] = existing_price.id
                    logger.info(
                        f"Using existing price {existing_price.id} for {nickname}"
                    )
                else:
                    # Create new metered price
                    price = stripe.Price.create(
                        product=product.id,
                        nickname=nickname,
                        unit_amount=unit_amount,
                        currency="usd",
                        recurring={
                            "interval": "month",
                            "usage_type": "metered",
                            "aggregate_usage": "sum",
                        },
                    )
                    created_prices[plan_key] = price.id
                    logger.info(f"Created price {price.id} for {nickname}")

            except StripeError as e:
                logger.error(f"Failed to create metered price for {nickname}: {e}")
                raise StripeClientError(
                    f"Failed to create metered prices: {e.user_message}", e
                )

        return created_prices

    async def create_payment_intent(
        self, amount: int, currency: str, customer_id: str
    ) -> Dict[str, Any]:
        """
        Create a payment intent.

        Args:
            amount: Amount in cents
            currency: Currency code (e.g., "usd")
            customer_id: Stripe customer ID

        Returns:
            Payment intent data

        Raises:
            StripeClientError: If creation fails
        """
        if not self.is_configured:
            raise StripeClientError("Stripe client not configured")

        try:
            payment_intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                customer=customer_id,
                automatic_payment_methods={"enabled": True},
            )
            return payment_intent.to_dict()

        except StripeError as e:
            logger.error(f"Failed to create payment intent: {e}")
            raise StripeClientError(f"Failed to create payment intent: {str(e)}")

    async def confirm_payment_intent(self, payment_intent_id: str) -> Dict[str, Any]:
        """
        Confirm a payment intent.

        Args:
            payment_intent_id: Stripe payment intent ID

        Returns:
            Confirmed payment intent data

        Raises:
            StripeClientError: If confirmation fails
        """
        if not self.is_configured:
            raise StripeClientError("Stripe client not configured")

        try:
            payment_intent = stripe.PaymentIntent.confirm(payment_intent_id)
            return payment_intent.to_dict()

        except stripe.CardError as e:
            logger.error(f"Card error confirming payment: {e}")
            raise StripeClientError(f"Failed to confirm payment: {str(e)}")
        except StripeError as e:
            logger.error(f"Failed to confirm payment intent: {e}")
            raise StripeClientError(f"Failed to confirm payment: {str(e)}")

    async def get_customer_portal_url(self, customer_id: str, return_url: str) -> str:
        """
        Create a customer portal session.

        Args:
            customer_id: Stripe customer ID
            return_url: URL to return to after portal

        Returns:
            Portal session URL

        Raises:
            StripeClientError: If creation fails
        """
        if not self.is_configured:
            raise StripeClientError("Stripe client not configured")

        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )
            return session.url

        except StripeError as e:
            logger.error(f"Failed to create portal session: {e}")
            raise StripeClientError(f"Failed to create portal session: {str(e)}")

    async def list_invoices(
        self, customer_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        List invoices for a customer.

        Args:
            customer_id: Stripe customer ID
            limit: Maximum number of invoices

        Returns:
            List of invoice data

        Raises:
            StripeClientError: If listing fails
        """
        if not self.is_configured:
            raise StripeClientError("Stripe client not configured")

        try:
            invoices = stripe.Invoice.list(customer=customer_id, limit=limit)
            return [invoice.to_dict() for invoice in invoices.data]

        except StripeError as e:
            logger.error(f"Failed to list invoices: {e}")
            raise StripeClientError(f"Failed to list invoices: {str(e)}")

    async def update_customer(self, customer_id: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Update customer information.

        Args:
            customer_id: Stripe customer ID
            **kwargs: Fields to update

        Returns:
            Updated customer data

        Raises:
            StripeClientError: If update fails
        """
        if not self.is_configured:
            raise StripeClientError("Stripe client not configured")

        try:
            customer = stripe.Customer.modify(customer_id, **kwargs)
            return customer.to_dict()

        except StripeError as e:
            logger.error(f"Failed to update customer: {e}")
            raise StripeClientError(f"Failed to update customer: {str(e)}")

    async def construct_webhook_event(
        self, payload: bytes, signature: str, webhook_secret: str
    ) -> Dict[str, Any]:
        """
        Construct and verify a webhook event.

        Args:
            payload: Raw webhook payload
            signature: Stripe signature header
            webhook_secret: Webhook endpoint secret

        Returns:
            Verified webhook event

        Raises:
            StripeClientError: If the secret is missing or verification fails
        """
        # See verify_webhook_signature: an empty secret still "verifies".
        if not webhook_secret:
            logger.error(
                "STRIPE_WEBHOOK_SECRET is not configured; refusing to process webhook."
            )
            raise StripeClientError("Webhook secret is not configured")

        try:
            event = stripe.Webhook.construct_event(payload, signature, webhook_secret)  # type: ignore[no-untyped-call]
            return dict(event)

        except ValueError as e:
            logger.error(f"Invalid webhook signature: {e}")
            raise StripeClientError(f"Invalid webhook signature: {str(e)}")
        except stripe.SignatureVerificationError as e:
            logger.error(f"Webhook signature verification failed: {e}")
            raise StripeClientError(f"Failed to verify webhook: {str(e)}")
