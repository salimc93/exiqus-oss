"""
Script to deactivate trial for a specific user in production.

This script:
1. Sets subscription_status to 'ACTIVE'
2. Sets is_trial to false
3. Sets subscription_plan to 'FREE'

Usage:
    DATABASE_URL='postgresql+asyncpg://user:pass@host:port/db' \\
    poetry run python scripts/deactivate_trial.py user@example.com

For Railway production:
    Get DATABASE_URL from Railway dashboard → Variables → DATABASE_URL
"""

import asyncio
import os
import sys

from sqlalchemy.ext.asyncio import create_async_engine

# Get database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL environment variable is required. "
        "Set it to your production database connection string."
    )


async def deactivate_trial(email: str) -> None:
    """
    Deactivate trial for a user.

    Args:
        email: User email address
    """
    engine = create_async_engine(DATABASE_URL, echo=True)

    try:
        async with engine.begin() as conn:
            # Update user to deactivate trial using raw SQL
            from sqlalchemy import text

            result = await conn.execute(
                text(
                    """
                    UPDATE users
                    SET subscription_status = 'ACTIVE',
                        is_trial = false,
                        subscription_plan = 'FREE'
                    WHERE email = :email
                    RETURNING user_id, email, subscription_plan, subscription_status, is_trial, trial_end_date
                    """
                ),
                {"email": email},
            )

            # Fetch and display result
            row = result.fetchone()
            if row:
                print("\n✅ Trial deactivated successfully!")
                print(f"User ID: {row[0]}")
                print(f"Email: {row[1]}")
                print(f"Subscription Plan: {row[2]}")
                print(f"Subscription Status: {row[3]}")
                print(f"Is Trial: {row[4]}")
                print(f"Trial End Date: {row[5]}")
            else:
                print(f"\n❌ User with email '{email}' not found.")

    finally:
        await engine.dispose()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/deactivate_trial.py <email>")
        print(
            "Example: DATABASE_URL='postgresql+asyncpg://...' poetry run python scripts/deactivate_trial.py user@example.com"
        )
        sys.exit(1)

    email = sys.argv[1]
    print(f"Deactivating trial for: {email}")
    asyncio.run(deactivate_trial(email))
