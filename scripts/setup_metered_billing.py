#!/usr/bin/env python3
"""
Setup script to initialize Stripe metered billing prices.

This script creates the necessary products and prices in Stripe
for overage billing functionality.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.github_analyzer.billing.stripe_client import StripeClient  # noqa: E402
from src.github_analyzer.utils.logging import get_logger  # noqa: E402

logger = get_logger(__name__)


async def setup_metered_billing():
    """Initialize metered billing prices in Stripe."""
    try:
        logger.info("Setting up Stripe metered billing...")

        stripe_client = StripeClient()

        if not stripe_client.is_configured:
            logger.error("Stripe is not configured. Please set STRIPE_SECRET_KEY.")
            return False

        # Create or retrieve metered prices
        prices = await stripe_client.create_metered_billing_prices()

        logger.info("Metered billing prices configured:")
        for plan, price_id in prices.items():
            logger.info(f"  {plan}: {price_id}")

        return True

    except Exception as e:
        logger.error(f"Failed to setup metered billing: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(setup_metered_billing())
    sys.exit(0 if success else 1)
