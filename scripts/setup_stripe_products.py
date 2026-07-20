#!/usr/bin/env python
"""
Setup Stripe products and prices for the Exiqus platform.
Run this once to create all necessary products in your Stripe account.
"""

import os
import sys
from pathlib import Path

import stripe
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

if not stripe.api_key:
    print("Error: STRIPE_SECRET_KEY not found in .env file")
    sys.exit(1)

print(f"Using Stripe API key: {stripe.api_key[:7]}...{stripe.api_key[-4:]}")


def create_products():
    """Create Stripe products and prices for all subscription tiers."""

    products = [
        {
            "name": "Exiqus Starter",
            "id": "prod_exiqus_starter",
            "description": "10 candidate assessments per month with all contexts & roles",
            "price_id": "price_basic_monthly",
            "amount": 4900,  # $49.00 in cents
            "metadata": {
                "plan": "BASIC",
                "candidate_limit": "10",
                "repo_limit": "unlimited",
            },
        },
        {
            "name": "Exiqus Growth",
            "id": "prod_exiqus_growth",
            "description": "50 candidate assessments per month with interview questions",
            "price_id": "price_professional_monthly",
            "amount": 19900,  # $199.00 in cents
            "metadata": {
                "plan": "PROFESSIONAL",
                "candidate_limit": "50",
                "repo_limit": "unlimited",
            },
        },
        {
            "name": "Exiqus Scale",
            "id": "prod_exiqus_scale",
            "description": "200 candidate assessments per month with enterprise features",
            "price_id": "price_enterprise_monthly",
            "amount": 49900,  # $499.00 in cents
            "metadata": {
                "plan": "ENTERPRISE",
                "candidate_limit": "200",
                "repo_limit": "unlimited",
            },
        },
        # Scale+ tier: Custom pricing only - contact sales
        # Not created automatically in Stripe
    ]

    created_products = []

    for product_data in products:
        try:
            # Check if product already exists
            existing_products = stripe.Product.list(limit=100)
            product = None

            for existing in existing_products.data:
                if existing.metadata.get("plan") == product_data["metadata"]["plan"]:
                    product = existing
                    print(f"Product already exists: {product.name} ({product.id})")
                    break

            # Create product if it doesn't exist
            if not product:
                product = stripe.Product.create(
                    name=product_data["name"],
                    description=product_data["description"],
                    metadata=product_data["metadata"],
                )
                print(f"Created product: {product.name} ({product.id})")

            # Check if price already exists
            existing_prices = stripe.Price.list(product=product.id, limit=100)
            price = None

            for existing in existing_prices.data:
                if existing.unit_amount == product_data["amount"]:
                    price = existing
                    print(
                        f"Price already exists: ${price.unit_amount / 100:.2f} ({price.id})"
                    )
                    break

            # Create price if it doesn't exist
            if not price:
                price = stripe.Price.create(
                    product=product.id,
                    unit_amount=product_data["amount"],
                    currency="usd",
                    recurring={"interval": "month"},
                    metadata=product_data["metadata"],
                )
                print(f"Created price: ${price.unit_amount / 100:.2f} ({price.id})")

            created_products.append(
                {
                    "product": product,
                    "price": price,
                    "plan": product_data["metadata"]["plan"],
                }
            )

        except Exception as e:
            print(f"Error creating product {product_data['name']}: {e}")

    return created_products


def update_backend_config(products):
    """Update the backend configuration with actual Stripe price IDs."""

    print("\n" + "=" * 60)
    print("IMPORTANT: Update your backend configuration with these IDs:")
    print("=" * 60)

    print("\nIn src/github_analyzer/billing/subscription_manager.py:")
    print("-" * 40)

    for item in products:
        plan = item["plan"]
        price_id = item["price"].id
        print(f"    SubscriptionPlan.{plan}: {{")
        print(f'        "price_id": "{price_id}",')
        print("        # ... other config ...")
        print("    }},")

    print("\n" + "=" * 60)
    print("Also update src/github_analyzer/billing/webhook_handlers.py:")
    print("-" * 40)
    print("price_mapping = {")
    for item in products:
        plan = item["plan"]
        price_id = item["price"].id
        print(f'    "{price_id}": SubscriptionPlan.{plan},')
    print("}")
    print("=" * 60)


def setup_webhook_endpoint():
    """Create a webhook endpoint for Stripe events."""

    print("\n" + "=" * 60)
    print("WEBHOOK SETUP INSTRUCTIONS:")
    print("=" * 60)

    print(
        """
1. Go to https://dashboard.stripe.com/test/webhooks
2. Click "Add endpoint"
3. Enter your webhook URL:
   - For local testing: Use ngrok or similar tunnel
   - For production: https://your-domain.com/api/v1/billing/webhook
4. Select these events:
   - checkout.session.completed
   - customer.subscription.created
   - customer.subscription.updated
   - customer.subscription.deleted
   - invoice.payment_succeeded
   - invoice.payment_failed
5. Copy the webhook secret and add to .env:
   STRIPE_WEBHOOK_SECRET=whsec_...
"""
    )


if __name__ == "__main__":
    print("Setting up Stripe products for Exiqus...")
    print("=" * 60)

    try:
        # Create products and prices
        products = create_products()

        if products:
            print(f"\n✅ Successfully created/verified {len(products)} products")

            # Show configuration instructions
            update_backend_config(products)

            # Show webhook setup instructions
            setup_webhook_endpoint()
        else:
            print("\n❌ No products were created")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
