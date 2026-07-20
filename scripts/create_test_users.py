#!/usr/bin/env python
"""
Create test users with different subscription tiers for staging/testing.
This script is designed to be run in staging environments for testing purposes.
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select  # noqa: E402

from src.github_analyzer.api.auth.jwt import hash_password  # noqa: E402
from src.github_analyzer.database.connection import get_db_session  # noqa: E402
from src.github_analyzer.database.models import SubscriptionPlan, User  # noqa: E402

# Test users configuration
# Using Gmail's "+" trick so all emails go to admin@example.com
TEST_USERS = {
    "admin+test-basic@example.com": {
        "plan": SubscriptionPlan.BASIC.value,
        "quota": 25,
        "password": "TestBasic123!",
        "is_priority": False,
    },
    "admin+test-professional@example.com": {
        "plan": SubscriptionPlan.PROFESSIONAL.value,
        "quota": 100,
        "password": "TestProfessional123!",
        "is_priority": False,
    },
    "admin+test-enterprise@example.com": {
        "plan": SubscriptionPlan.ENTERPRISE.value,
        "quota": 500,
        "password": "TestEnterprise123!",
        "is_priority": True,
    },
    "admin+test-free@example.com": {
        "plan": SubscriptionPlan.FREE.value,
        "quota": 5,
        "password": "TestFree123!",
        "is_priority": False,
    },
    "admin+test-scale-plus@example.com": {
        "plan": SubscriptionPlan.SCALE_PLUS.value,
        "quota": 1000,
        "password": "TestScalePlus123!",
        "is_priority": True,
    },
}


async def create_test_user(email: str, config: dict, session):
    """Create or update a test user."""
    # Check if user exists
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user:
        # Update existing user
        user.subscription_plan = config["plan"]
        user.usage_quota = config["quota"]
        user.is_priority_support = config["is_priority"]
        user.password_hash = hash_password(config["password"])
        user.is_verified = True
        user.is_active = True
        await session.commit()
        print(f"✅ Updated test user: {email}")
    else:
        # Create new test user
        test_user = User(
            user_id=str(uuid.uuid4()),
            email=email,
            password_hash=hash_password(config["password"]),
            full_name=f"Test User ({config['plan'].title()})",
            is_active=True,
            is_verified=True,  # Test users are pre-verified
            is_admin=False,
            is_priority_support=config["is_priority"],
            subscription_plan=config["plan"],
            usage_quota=config["quota"],
            usage_count=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        session.add(test_user)
        await session.commit()
        print(f"✅ Created test user: {email}")

    return True


async def main():
    """Create all test users."""
    environment = os.getenv("ENVIRONMENT", "development")

    if environment == "production":
        print("⚠️  WARNING: Running in production environment!")
        confirm = input(
            "Are you sure you want to create test users in production? (yes/no): "
        )
        if confirm.lower() != "yes":
            print("Aborted.")
            return

    print(f"\n🧪 Creating test users for {environment} environment...")
    print("=" * 60)

    async for session in get_db_session():
        for email, config in TEST_USERS.items():
            await create_test_user(email, config, session)

    print("\n" + "=" * 60)
    print("📝 Test User Credentials:")
    print("=" * 60)

    for email, config in TEST_USERS.items():
        print(f"\n📧 Email: {email}")
        print(f"   Password: {config['password']}")
        print(f"   Plan: {config['plan']}")
        print(f"   Quota: {config['quota']} analyses/month")
        print(f"   Priority Support: {'Yes' if config['is_priority'] else 'No'}")

    print("\n" + "=" * 60)
    print("💡 Tips:")
    print("   - All test emails forward to admin@example.com")
    print("   - Use these for testing different subscription tiers")
    print("   - Passwords are intentionally simple for testing")
    print("   - Change passwords if using in any public-facing environment")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
