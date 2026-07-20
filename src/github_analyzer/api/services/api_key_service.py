# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""Service for managing API keys."""

import json
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from github_analyzer.api.utils.api_key import (
    extract_key_prefix,
    generate_api_key,
    validate_api_key_format,
    verify_api_key_with_salt,
)
from github_analyzer.database.models import APIKey, SubscriptionPlan, User
from github_analyzer.utils.helpers import generate_unique_id


class APIKeyService:
    """Service for managing API keys."""

    def __init__(self, db: AsyncSession):
        """Initialize the API key service."""
        self.db = db

    async def create_api_key(
        self,
        user_id: str,
        name: str,
        permissions: List[str],
    ) -> tuple[APIKey, str]:
        """
        Create a new API key for a user.

        Args:
            user_id: The user's ID
            name: A descriptive name for the API key
            permissions: List of permissions for this key

        Returns:
            Tuple of (APIKey model, plain text API key)
            The plain text key should be shown to the user once.

        Raises:
            ValueError: If user not found or invalid permissions
        """
        # Verify user exists
        user = await self.db.get(User, user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Set monthly quota based on user's subscription plan
        monthly_quota = self._get_plan_api_quota(user.subscription_plan)

        # Generate the API key
        api_key_plain, key_prefix, api_key_hash, salt = generate_api_key()

        # Create the API key record
        api_key = APIKey(
            key_id=generate_unique_id("ak"),
            user_id=user_id,
            name=name,
            key_prefix=key_prefix,
            key_hash=api_key_hash,
            salt=salt,
            permissions=json.dumps(permissions),
            monthly_quota=monthly_quota,
            monthly_usage=0,
            last_quota_reset=datetime.now(timezone.utc),
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        self.db.add(api_key)
        await self.db.commit()
        await self.db.refresh(api_key)

        return api_key, api_key_plain

    async def get_api_key_by_id(self, key_id: str) -> Optional[APIKey]:
        """Get an API key by its ID."""
        return await self.db.get(APIKey, key_id)

    async def get_user_api_keys(self, user_id: str) -> List[APIKey]:
        """Get all API keys for a user."""
        result = await self.db.execute(
            select(APIKey)
            .where(APIKey.user_id == user_id)
            .order_by(APIKey.created_at.desc())
        )
        return list(result.scalars().all())

    async def validate_api_key(self, api_key_plain: str) -> Optional[APIKey]:
        """
        Validate an API key and return the key record if valid.
        Uses O(1) prefix-based lookup for performance and security.

        Args:
            api_key_plain: The plain text API key

        Returns:
            APIKey record if valid, None otherwise
        """
        # First validate the format
        if not validate_api_key_format(api_key_plain):
            return None

        # Extract the prefix for O(1) lookup
        key_prefix = extract_key_prefix(api_key_plain)
        if not key_prefix:
            return None

        # Query for the specific API key by prefix (O(1) lookup)
        result = await self.db.execute(
            select(APIKey).where(
                APIKey.key_prefix == key_prefix,
                APIKey.is_active == True,  # noqa: E712
            )
        )
        api_key = result.scalar_one_or_none()

        # If no key found with this prefix, it's invalid
        if not api_key:
            return None

        # Verify the full API key against the stored hash
        if not verify_api_key_with_salt(api_key_plain, api_key.key_hash, api_key.salt):
            return None

        # Check if key has expired
        if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
            return None

        # Update last used timestamp
        api_key.last_used = datetime.now(timezone.utc)
        await self.db.commit()

        return api_key

    async def revoke_api_key(self, key_id: str, user_id: str) -> bool:
        """
        Revoke an API key.

        Args:
            key_id: The API key ID
            user_id: The user ID (for authorization check)

        Returns:
            True if revoked successfully, False otherwise
        """
        api_key = await self.get_api_key_by_id(key_id)
        if not api_key or api_key.user_id != user_id:
            return False

        api_key.is_active = False
        await self.db.commit()
        return True

    async def update_api_key_quota(self, key_id: str, new_quota: int) -> bool:
        """
        Update the monthly quota for an API key.

        Args:
            key_id: The API key ID
            new_quota: The new monthly quota

        Returns:
            True if updated successfully
        """
        api_key = await self.get_api_key_by_id(key_id)
        if not api_key:
            return False

        api_key.monthly_quota = new_quota
        await self.db.commit()
        return True

    async def increment_usage(self, key_id: str, count: int = 1) -> bool:
        """
        Increment the usage counter for an API key.

        Args:
            key_id: The API key ID
            count: Number to increment by

        Returns:
            True if incremented successfully
        """
        api_key = await self.get_api_key_by_id(key_id)
        if not api_key:
            return False

        api_key.monthly_usage += count
        await self.db.commit()
        return True

    async def check_quota_available(self, api_key: APIKey) -> tuple[bool, int]:
        """
        Check if an API key has quota available.

        Args:
            api_key: The API key to check

        Returns:
            Tuple of (has_quota, remaining_quota)
        """
        if api_key.monthly_quota == 0:  # No API access
            return False, 0

        if api_key.monthly_quota == -1:  # Unlimited
            return True, -1

        remaining = api_key.monthly_quota - api_key.monthly_usage
        return remaining > 0, max(0, remaining)

    async def reset_monthly_usage(self, key_id: str) -> bool:
        """
        Reset the monthly usage counter for an API key.

        Args:
            key_id: The API key ID

        Returns:
            True if reset successfully
        """
        api_key = await self.get_api_key_by_id(key_id)
        if not api_key:
            return False

        api_key.monthly_usage = 0
        api_key.last_quota_reset = datetime.now(timezone.utc)
        await self.db.commit()
        return True

    def _get_plan_api_quota(self, plan: SubscriptionPlan) -> int:
        """
        Get the API quota for a subscription plan.

        Args:
            plan: The subscription plan

        Returns:
            Monthly API quota (0 = no access, -1 = unlimited)
        """
        quotas = {
            SubscriptionPlan.FREE: 0,  # No API access
            SubscriptionPlan.BASIC: 0,  # No API access
            SubscriptionPlan.PROFESSIONAL: 1000,  # 1,000 calls/month
            SubscriptionPlan.ENTERPRISE: 10000,  # 10,000 calls/month
        }
        return quotas.get(plan, 0)
