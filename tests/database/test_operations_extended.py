"""
Extended tests for database operations to increase coverage.

Tests ONLY uncovered database operation methods not in existing test files.
"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from github_analyzer.database.models import (
    SubscriptionPlan,
    SubscriptionStatus,
    User,
    UserRole,
)
from github_analyzer.database.repositories.user_repository import UserRepository


class TestUserOperationsExtended:
    """Tests for UserOperations methods not covered elsewhere."""

    async def test_update_user_profile(self, test_db: AsyncSession):
        """Test updating user profile information."""
        async with test_db() as db:
            user = User(
                user_id=str(uuid4()),
                email="update@example.com",
                password_hash="old_hash",
                full_name="Old Name",
            )
            db.add(user)
            await db.commit()

            # Update user profile
            repo = UserRepository(db)
            success = await repo.update_user_profile(
                user.user_id,
                full_name="New Name",
                company="New Company",
            )

            assert success is True

            # Get updated user to verify
            updated_user = await repo.get_user_by_id(user.user_id)
            assert updated_user.full_name == "New Name"
            assert updated_user.company == "New Company"

    async def test_get_all_users_paginated(self, test_db: AsyncSession):
        """Test getting users with pagination."""
        async with test_db() as db:
            # Create multiple users
            for i in range(15):
                user = User(
                    user_id=str(uuid4()),
                    email=f"user{i}@example.com",
                    password_hash="hash",
                    full_name=f"User {i}",
                )
                db.add(user)
            await db.commit()

            # Get first page
            repo = UserRepository(db)
            users = await repo.get_all_users(offset=0, limit=10, active_only=False)
            assert len(users) <= 10

            # Get second page
            users2 = await repo.get_all_users(offset=10, limit=10, active_only=False)
            assert len(users2) >= 5

            # Test with active_only filter
            active_users = await repo.get_all_users(active_only=True)
            assert isinstance(active_users, list)

    async def test_update_last_login(self, test_db: AsyncSession):
        """Test updating user's last login timestamp."""
        async with test_db() as db:
            # Create user with required fields
            user = User(
                user_id=str(uuid4()),
                email="login@example.com",
                password_hash="hash",
                full_name="Login Test User",  # Add required field
                last_login=None,
            )
            db.add(user)
            await db.commit()

            # Update last login
            before = datetime.now(timezone.utc)
            repo = UserRepository(db)
            await repo.update_last_login(user.user_id)

            # Need to refresh to see changes
            await db.refresh(user)

            # Verify update
            assert user.last_login is not None
            # Compare naive datetimes (SQLite stores as naive)
            if user.last_login.tzinfo is None:
                before = before.replace(tzinfo=None)
            assert user.last_login >= before

    async def test_update_user_subscription(self, test_db: AsyncSession):
        """Test updating user subscription."""
        async with test_db() as db:
            user = User(
                user_id=str(uuid4()),
                email="sub@example.com",
                password_hash="hash",
                full_name="Subscription Test User",
                subscription_plan=SubscriptionPlan.FREE,
                subscription_status=SubscriptionStatus.CANCELED,
            )
            db.add(user)
            await db.commit()

            # Update subscription
            repo = UserRepository(db)
            updated = await repo.update_subscription(
                user.user_id,
                subscription_plan=SubscriptionPlan.PROFESSIONAL,
                subscription_status=SubscriptionStatus.ACTIVE,
                stripe_customer_id="cus_test123",
                stripe_subscription_id="sub_test123",
            )

            assert updated is not None

            # Get the updated user to verify changes
            updated_user = await repo.get_user_by_id(user.user_id)
            assert updated_user.subscription_plan == SubscriptionPlan.PROFESSIONAL
            assert updated_user.subscription_status == SubscriptionStatus.ACTIVE
            assert updated_user.stripe_customer_id == "cus_test123"

    async def test_get_user_by_stripe_customer_id(self, test_db: AsyncSession):
        """Test getting user by Stripe customer ID."""
        async with test_db() as db:
            user = User(
                user_id=str(uuid4()),
                email="stripe@example.com",
                password_hash="hash",
                full_name="Stripe Test User",
                stripe_customer_id="cus_unique123",
            )
            db.add(user)
            await db.commit()

            # Find by Stripe customer ID
            repo = UserRepository(db)
            found = await repo.get_user_by_stripe_customer_id("cus_unique123")
            assert found is not None
            assert found.stripe_customer_id == "cus_unique123"

            # Non-existent ID
            not_found = await repo.get_user_by_stripe_customer_id("cus_notexist")
            assert not_found is None

    async def test_get_user_by_stripe_subscription_id(self, test_db: AsyncSession):
        """Test getting user by Stripe subscription ID."""
        async with test_db() as db:
            user = User(
                user_id=str(uuid4()),
                email="stripe_sub@example.com",
                password_hash="hash",
                full_name="Stripe Sub Test User",
                stripe_subscription_id="sub_unique456",
            )
            db.add(user)
            await db.commit()

            # Find by Stripe subscription ID
            repo = UserRepository(db)
            found = await repo.get_user_by_stripe_subscription_id("sub_unique456")
            assert found is not None
            assert found.stripe_subscription_id == "sub_unique456"

            # Non-existent ID
            not_found = await repo.get_user_by_stripe_subscription_id("sub_notexist")
            assert not_found is None

    async def test_get_users_by_subscription_plan(self, test_db: AsyncSession):
        """Test getting users by subscription plan."""
        async with test_db() as db:
            # Create users with different plans
            for i, plan in enumerate(
                [
                    SubscriptionPlan.FREE,
                    SubscriptionPlan.PROFESSIONAL,
                    SubscriptionPlan.PROFESSIONAL,
                ]
            ):
                user = User(
                    user_id=str(uuid4()),
                    email=f"plan_{i}@example.com",
                    password_hash="hash",
                    full_name=f"Plan User {i}",
                    subscription_plan=plan,
                )
                db.add(user)
            await db.commit()

            # Get users by plan
            repo = UserRepository(db)
            pro_users = await repo.get_users_by_subscription_plan(
                SubscriptionPlan.PROFESSIONAL
            )
            assert len(pro_users) == 2

            free_users = await repo.get_users_by_subscription_plan(
                SubscriptionPlan.FREE
            )
            assert len(free_users) == 1

    async def test_update_user_role(self, test_db: AsyncSession):
        """Test updating user admin role."""
        async with test_db() as db:
            user = User(
                user_id=str(uuid4()),
                email="role@example.com",
                password_hash="hash",
                full_name="Role Test User",
                is_admin=False,
            )
            db.add(user)
            await db.commit()

            # Update role to admin
            repo = UserRepository(db)
            success = await repo.update_user_role(user.user_id, UserRole.ADMIN)
            assert success is True

            # Verify
            await db.refresh(user)
            assert user.user_role == UserRole.ADMIN
