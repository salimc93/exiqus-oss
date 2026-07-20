#!/usr/bin/env python
"""
Create or update an admin user for the Exiqus platform.
This script connects directly to Railway PostgreSQL database.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import asyncpg

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def create_or_update_admin(
    email: str, password: str = None, tier: str = "SCALE_PLUS"
):
    """Create or update a user to have admin privileges with specified tier."""
    from src.github_analyzer.api.auth.jwt import hash_password

    # Validate tier
    valid_tiers = ["FREE", "BASIC", "PROFESSIONAL", "ENTERPRISE", "SCALE_PLUS"]
    tier = tier.upper()
    if tier not in valid_tiers:
        print(f"❌ Invalid tier: {tier}. Must be one of: {', '.join(valid_tiers)}")
        return False

    # Get database URL from environment or use the provided one
    DATABASE_URL = os.getenv(
        "DATABASE_PUBLIC_URL",
        "postgresql://user:password@host:port/database",  # REMOVED - Use environment variable
    )

    # Connect directly to PostgreSQL
    conn = await asyncpg.connect(DATABASE_URL)

    try:
        # Check if user exists
        existing = await conn.fetchrow(
            "SELECT user_id, is_admin FROM users WHERE email = $1", email
        )

        if existing:
            # Update existing user to be admin with specified tier
            if password:
                await conn.execute(
                    """
                    UPDATE users
                    SET is_admin = true,
                        is_active = true,
                        is_verified = true,
                        is_priority_support = true,
                        subscription_plan = $1,
                        subscription_status = 'ACTIVE',
                        password_hash = $2,
                        updated_at = $3,
                        usage_quota = 99999
                    WHERE email = $4
                    """,
                    tier,
                    hash_password(password),
                    datetime.now(timezone.utc),
                    email,
                )
            else:
                await conn.execute(
                    """
                    UPDATE users
                    SET is_admin = true,
                        is_active = true,
                        is_verified = true,
                        is_priority_support = true,
                        subscription_plan = $1,
                        subscription_status = 'ACTIVE',
                        updated_at = $2,
                        usage_quota = 99999
                    WHERE email = $3
                    """,
                    tier,
                    datetime.now(timezone.utc),
                    email,
                )
            print(f"✅ Updated {email} to admin status")
            print(f"   User ID: {existing['user_id']}")
            print(f"   Tier: {tier}")
            return True
        else:
            # Create new admin user with ALL required fields
            if not password:
                import getpass

                password = getpass.getpass(f"Enter password for {email}: ")
                confirm_password = getpass.getpass("Confirm password: ")

                if password != confirm_password:
                    print("❌ Passwords don't match!")
                    return False

            import uuid

            user_id = f"usr_{uuid.uuid4()}"
            now = datetime.now(timezone.utc)

            await conn.execute(
                """
                INSERT INTO users (
                    user_id, email, password_hash, full_name,
                    is_active, is_verified, is_admin,
                    user_role, subscription_plan, subscription_status,
                    is_trial, analyses_consumed, has_completed_onboarding,
                    created_at, updated_at, usage_quota, usage_count,
                    is_priority_support, response_time_hours
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19)
                """,
                user_id,
                email,
                hash_password(password),
                "Admin User",  # full_name
                True,  # is_active
                True,  # is_verified
                True,  # is_admin
                "ADMIN",  # user_role - must be uppercase for enum
                tier,  # subscription_plan - use the specified tier
                "ACTIVE",  # subscription_status
                False,  # is_trial - admin isn't on trial
                0,  # analyses_consumed - start at 0
                True,  # has_completed_onboarding - admin doesn't need onboarding
                now,  # created_at
                now,  # updated_at
                99999,  # usage_quota - unlimited for admin
                0,  # usage_count - start at 0
                True,  # is_priority_support
                0,  # response_time_hours - instant for admin
            )
            print(f"✅ Created admin user {email}")
            print(f"   User ID: {user_id}")
            print(f"   Tier: {tier}")
            return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        await conn.close()


async def main():
    # Use environment variable or default
    admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")

    # For automated setup, you can set a default password
    # In production, use a secure password from environment
    admin_password = os.getenv("ADMIN_PASSWORD", None)

    # Default to SCALE_PLUS tier for the admin
    admin_tier = os.getenv("ADMIN_TIER", "SCALE_PLUS")

    print(f"Setting up admin user: {admin_email}")
    print(f"Subscription tier: {admin_tier}")
    success = await create_or_update_admin(admin_email, admin_password, admin_tier)

    if success:
        print("\n🎯 Admin user configured successfully!")
        print(f"   Email: {admin_email}")
        print("\n📝 To access admin portal:")
        print("   URL: https://exiqus-staging.vercel.app/admin-portal/login")
        print(f"   Email: {admin_email}")
        print(
            f"   Password: {admin_password if admin_password else '[the password you entered]'}"
        )
        print(
            f"   Admin Secret: {os.getenv('ADMIN_SECRET', 'exiqus-admin-2024-trust-coding')}"
        )
        print("\n⚠️  IMPORTANT: Change the password after first login!")


if __name__ == "__main__":
    asyncio.run(main())
