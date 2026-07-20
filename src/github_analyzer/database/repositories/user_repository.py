# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
User repository for database operations related to users, authentication, and profiles.
"""

import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.auth.jwt import hash_password, verify_password
from ..models import (
    APIKey,
    BillingUsageRecord,
    ContactMessage,
    EmailVerificationToken,
    SubscriptionPlan,
    SubscriptionStatus,
    TokenBlacklist,
    UsageRecord,
    User,
    UserRole,
)
from ..rowcount import affected_rows


class UserRepository:
    """Repository for user management operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_user(
        self,
        email: str,
        password: str,
        full_name: str,
        company: Optional[str] = None,
        usage_quota: int = 100,
    ) -> User:
        """
        Create a new user account.
        """
        # Check if email already exists
        existing_user = await self.get_user_by_email(email)
        if existing_user:
            raise ValueError(f"Email address already registered: {email}")

        # Generate user ID
        user_id = f"usr_{secrets.token_urlsafe(16)}"

        # Hash password
        password_hash = hash_password(password)

        # Create user
        user = User(
            user_id=user_id,
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            company=company,
            usage_quota=usage_quota,
        )

        self.db.add(user)
        await self.db.flush()  # Flush to get any database-generated values
        await self.db.refresh(user)

        return user

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        result = await self.db.execute(select(User).where(User.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """
        Authenticate user with email and password.
        """
        user = await self.get_user_by_email(email)
        if not user or not user.is_active:
            return None

        if not verify_password(password, user.password_hash):
            return None

        return user

    async def update_last_login(self, user_id: str) -> None:
        """Update user's last login timestamp."""
        user = await self.get_user_by_id(user_id)
        if user:
            user.last_login = datetime.now(timezone.utc)
            await self.db.flush()

    async def update_password(self, user_id: str, new_password: str) -> bool:
        """
        Update user password.
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            return False

        user.password_hash = hash_password(new_password)
        await self.db.flush()
        return True

    async def update_usage_quota(self, user_id: str, new_quota: int) -> bool:
        """Update user's usage quota."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False

        user.usage_quota = new_quota
        await self.db.flush()
        return True

    async def update_user_profile(
        self,
        user_id: str,
        full_name: Optional[str] = None,
        company: Optional[str] = None,
        company_size: Optional[str] = None,
        industry: Optional[str] = None,
        use_case: Optional[str] = None,
        notification_preferences: Optional[str] = None,
    ) -> bool:
        """
        Update user profile information.
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            return False

        if full_name is not None:
            user.full_name = full_name
        if company is not None:
            user.company = company
        if company_size is not None:
            user.company_size = company_size
        if industry is not None:
            user.industry = industry
        if use_case is not None:
            user.use_case = use_case
        if notification_preferences is not None:
            user.notification_preferences = notification_preferences

        await self.db.flush()
        return True

    async def update_subscription(
        self,
        user_id: str,
        subscription_plan: Optional[SubscriptionPlan] = None,
        subscription_status: Optional[SubscriptionStatus] = None,
        usage_quota: Optional[int] = None,
        subscription_start_date: Optional[datetime] = None,
        subscription_end_date: Optional[datetime] = None,
        trial_end_date: Optional[datetime] = None,
        stripe_customer_id: Optional[str] = None,
        stripe_subscription_id: Optional[str] = None,
    ) -> bool:
        """
        Update user subscription information.
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            return False

        if subscription_plan is not None:
            user.subscription_plan = subscription_plan
        if subscription_status is not None:
            user.subscription_status = subscription_status
        if usage_quota is not None:
            user.usage_quota = usage_quota
        if stripe_customer_id is not None:
            user.stripe_customer_id = stripe_customer_id
        if stripe_subscription_id is not None:
            user.stripe_subscription_id = stripe_subscription_id
        if subscription_start_date is not None:
            user.subscription_start_date = subscription_start_date
        if subscription_end_date is not None:
            user.subscription_end_date = subscription_end_date
        if trial_end_date is not None:
            user.trial_end_date = trial_end_date

        await self.db.flush()
        return True

    async def update_user_role(self, user_id: str, new_role: UserRole) -> bool:
        """Update user role (admin function)."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False

        user.user_role = new_role
        user.is_admin = new_role == UserRole.ADMIN
        await self.db.flush()
        return True

    async def get_users_by_subscription_plan(
        self, plan: SubscriptionPlan, limit: int = 100, offset: int = 0
    ) -> List[User]:
        """Get users by subscription plan (admin function)."""
        query = (
            select(User)
            .where(User.subscription_plan == plan)
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_all_users(
        self, offset: int = 0, limit: int = 100, active_only: bool = True
    ) -> List[User]:
        """Get all users with pagination (admin function)."""
        query = select(User)

        if active_only:
            query = query.where(User.is_active == True)  # noqa: E712

        query = query.offset(offset).limit(limit).order_by(User.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_user_count(self) -> int:
        """Get total number of users (admin function)."""
        result = await self.db.execute(select(func.count(User.user_id)))
        return result.scalar() or 0

    async def get_user_by_stripe_customer_id(
        self, stripe_customer_id: str
    ) -> Optional[User]:
        """Get user by Stripe customer ID."""
        result = await self.db.execute(
            select(User).where(User.stripe_customer_id == stripe_customer_id)
        )
        return result.scalar_one_or_none()

    async def get_user_by_stripe_subscription_id(
        self, stripe_subscription_id: str
    ) -> Optional[User]:
        """Get user by Stripe subscription ID."""
        result = await self.db.execute(
            select(User).where(User.stripe_subscription_id == stripe_subscription_id)
        )
        return result.scalar_one_or_none()

    async def increment_usage_count(self, user_id: str, increment_by: int = 1) -> bool:
        """
        Atomically increment user's usage count.
        """
        result = await self.db.execute(
            update(User)
            .where(User.user_id == user_id)
            .values(usage_count=User.usage_count + increment_by)
        )
        await self.db.flush()
        return affected_rows(result) > 0

    async def update_usage_count(self, user_id: str, usage_value: int) -> bool:
        """
        Update user's usage count to a specific value.
        """
        result = await self.db.execute(
            update(User).where(User.user_id == user_id).values(usage_count=usage_value)
        )
        await self.db.flush()
        return affected_rows(result) > 0

    async def soft_delete_user(self, user_id: str) -> bool:
        """
        Soft delete user account (deactivate).
        """
        # Get user to check if exists
        user = await self.get_user_by_id(user_id)
        if not user:
            return False

        # Update user to inactive and set deletion timestamp
        updates = {
            "is_active": False,
            "subscription_status": SubscriptionStatus.CANCELED,
            "subscription_end_date": datetime.now(timezone.utc),
            "deletion_requested_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

        result = await self.db.execute(
            update(User).where(User.user_id == user_id).values(**updates)
        )

        # Also deactivate all API keys
        if affected_rows(result) > 0:
            # We can instantiate APIKeyRepository here or use helper method
            # For now, let's just do it directly or rely on service layer coordination
            # BUT: In Repository pattern, repositories ideally shouldn't depend on each other too much.
            # However, soft deleting user implies side effects.
            # Let's keep the API key logic here or move "soft_delete_account" to a Service.
            # I'll include API key logic here for simplicity as per original operations.py
            await self.db.execute(
                update(APIKey).where(APIKey.user_id == user_id).values(is_active=False)
            )

        return affected_rows(result) > 0

    async def hard_delete_user(self, user_id: str) -> bool:
        """
        Permanently delete user and all associated data.
        """
        # Delete in order to respect foreign key constraints

        # 1. Delete API keys
        await self.db.execute(delete(APIKey).where(APIKey.user_id == user_id))

        # 2. Anonymize contact messages instead of deleting
        user = await self.get_user_by_id(user_id)
        if user:
            await self.db.execute(
                update(ContactMessage)
                .where(ContactMessage.email == user.email)
                .values(email="deleted@user.com", name="Deleted User")
            )

        # 3. Delete usage records
        await self.db.execute(delete(UsageRecord).where(UsageRecord.user_id == user_id))

        # 4. Delete billing records
        await self.db.execute(
            delete(BillingUsageRecord).where(BillingUsageRecord.user_id == user_id)
        )

        # 5. Finally delete the user
        result = await self.db.execute(delete(User).where(User.user_id == user_id))

        return affected_rows(result) > 0

    async def get_users_pending_deletion(self, days_ago: int = 30) -> List[User]:
        """Get users who requested deletion more than X days ago."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_ago)

        query = select(User).where(
            and_(
                User.is_active.is_(False),
                User.deletion_requested_at.isnot(None),
                User.deletion_requested_at <= cutoff_date,
            )
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())


class APIKeyRepository:
    """Repository for API key management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_api_key(
        self,
        user_id: str,
        name: str,
        key_hash: str,
        key_prefix: str,
        salt: str,
        permissions: List[str],
        expires_at: Optional[datetime] = None,
    ) -> APIKey:
        """
        Create a new API key.
        """
        key_id = f"key_{secrets.token_urlsafe(16)}"

        api_key = APIKey(
            key_id=key_id,
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            salt=salt,
            permissions=json.dumps(permissions),
            expires_at=expires_at,
        )

        self.db.add(api_key)
        await self.db.flush()
        await self.db.refresh(api_key)

        return api_key

    async def get_api_key_by_id(self, key_id: str) -> Optional[APIKey]:
        """Get API key by ID."""
        result = await self.db.execute(select(APIKey).where(APIKey.key_id == key_id))
        return result.scalar_one_or_none()

    async def get_user_api_keys(
        self, user_id: str, active_only: bool = True
    ) -> List[APIKey]:
        """Get all API keys for a user."""
        query = select(APIKey).where(APIKey.user_id == user_id)

        if active_only:
            query = query.where(APIKey.is_active == True)  # noqa: E712

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def deactivate_api_key(self, key_id: str, user_id: str) -> bool:
        """
        Deactivate an API key.
        """
        api_key = await self.get_api_key_by_id(key_id)
        if not api_key or api_key.user_id != user_id:
            return False

        api_key.is_active = False
        await self.db.flush()
        return True

    async def deactivate_all_user_keys(self, user_id: str) -> int:
        """Deactivate all API keys for a user."""
        result = await self.db.execute(
            update(APIKey).where(APIKey.user_id == user_id).values(is_active=False)
        )
        return affected_rows(result)

    async def update_last_used(self, key_id: str) -> None:
        """Update API key's last used timestamp."""
        api_key = await self.get_api_key_by_id(key_id)
        if api_key:
            api_key.last_used = datetime.now(timezone.utc)
            await self.db.flush()


class TokenRepository:
    """Repository for token blacklist management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def blacklist_token(
        self,
        token_id: str,
        user_id: str,
        token_type: str,
        expires_at: datetime,
    ) -> TokenBlacklist:
        """
        Add token to blacklist.
        """
        blacklist_entry = TokenBlacklist(
            token_id=token_id,
            user_id=user_id,
            token_type=token_type,
            expires_at=expires_at,
        )

        self.db.add(blacklist_entry)
        await self.db.flush()

        return blacklist_entry

    async def is_token_blacklisted(self, token_id: str) -> bool:
        """Check if token is blacklisted."""
        result = await self.db.execute(
            select(TokenBlacklist).where(TokenBlacklist.token_id == token_id)
        )
        return result.scalar_one_or_none() is not None

    async def cleanup_expired_tokens(self) -> int:
        """
        Remove expired tokens from blacklist.
        """
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(TokenBlacklist).where(TokenBlacklist.expires_at < now)
        )
        expired_tokens = list(result.scalars().all())

        for token in expired_tokens:
            await self.db.delete(token)

        await self.db.flush()
        return len(expired_tokens)


class EmailVerificationRepository:
    """Repository for email verification tokens."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_verification_token(
        self,
        user_id: str,
        token: str,
        expires_in_hours: int = 24,
    ) -> EmailVerificationToken:
        """Create a new email verification token."""
        expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)

        verification_token = EmailVerificationToken(
            user_id=user_id,
            token=token,
            expires_at=expires_at,
        )

        self.db.add(verification_token)
        await self.db.flush()
        return verification_token

    async def get_valid_token(self, token: str) -> Optional[EmailVerificationToken]:
        """Get a valid (unused and not expired) verification token."""
        result = await self.db.execute(
            select(EmailVerificationToken).where(
                and_(
                    EmailVerificationToken.token == token,
                    EmailVerificationToken.used_at.is_(None),
                    EmailVerificationToken.expires_at > datetime.now(timezone.utc),
                )
            )
        )
        return result.scalar_one_or_none()

    async def mark_token_used(self, token: str) -> bool:
        """Mark a verification token as used."""
        result = await self.db.execute(
            update(EmailVerificationToken)
            .where(EmailVerificationToken.token == token)
            .values(used_at=datetime.now(timezone.utc))
        )
        return affected_rows(result) > 0

    async def verify_user_email(self, user_id: str) -> bool:
        """Mark user's email as verified."""
        result = await self.db.execute(
            update(User).where(User.user_id == user_id).values(is_verified=True)
        )
        return affected_rows(result) > 0

    async def cleanup_expired_tokens(self, days_old: int = 7) -> int:
        """Clean up expired tokens older than specified days."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
        result = await self.db.execute(
            delete(EmailVerificationToken).where(
                EmailVerificationToken.created_at < cutoff_date
            )
        )
        await self.db.commit()
        return affected_rows(result)

    async def get_user_tokens(self, user_id: str) -> List[EmailVerificationToken]:
        """Get all verification tokens for a user."""
        result = await self.db.execute(
            select(EmailVerificationToken)
            .where(EmailVerificationToken.user_id == user_id)
            .order_by(EmailVerificationToken.created_at.desc())
        )
        return list(result.scalars().all())
