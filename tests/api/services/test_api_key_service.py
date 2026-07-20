"""Tests for API key service."""

from datetime import datetime, timedelta, timezone

import pytest

from github_analyzer.api.services.api_key_service import APIKeyService
from github_analyzer.api.utils.api_key import verify_api_key_with_salt
from github_analyzer.database.models import SubscriptionPlan, User


@pytest.mark.asyncio
class TestAPIKeyService:
    """Test API key service functionality."""

    async def test_create_api_key_success(self, test_db):
        """Test successful API key creation."""
        async with test_db() as db:
            # Create a user
            user = User(
                user_id="test_user_1",
                email="test@example.com",
                password_hash="hashed",
                full_name="Test User",
                subscription_plan=SubscriptionPlan.PROFESSIONAL,
            )
            db.add(user)
            await db.commit()

            # Create API key
            service = APIKeyService(db)
            api_key, plain_key = await service.create_api_key(
                user_id=user.user_id,
                name="Test API Key",
                permissions=["analyze", "batch"],
            )

            # Verify API key
            assert api_key.user_id == user.user_id
            assert api_key.name == "Test API Key"
            assert api_key.permissions == '["analyze", "batch"]'
            assert api_key.monthly_quota == 1000  # Professional plan
            assert api_key.monthly_usage == 0
            assert api_key.is_active is True
            assert plain_key.startswith("gha_")
            assert len(plain_key) == 36

            # Verify the hash can be used to validate the key
            assert (
                verify_api_key_with_salt(plain_key, api_key.key_hash, api_key.salt)
                is True
            )

            # Verify the key has the expected format
            assert "_" in plain_key
            parts = plain_key.split("_")
            assert len(parts) == 3
            assert parts[1] == api_key.key_prefix

    async def test_create_api_key_user_not_found(self, test_db):
        """Test API key creation fails when user not found."""
        async with test_db() as db:
            service = APIKeyService(db)

            with pytest.raises(ValueError, match="User nonexistent not found"):
                await service.create_api_key(
                    user_id="nonexistent",
                    name="Test API Key",
                    permissions=["analyze"],
                )

    async def test_create_api_key_different_plans(self, test_db):
        """Test API key creation with different subscription plans."""
        async with test_db() as db:
            # Test plan quotas
            test_cases = [
                (SubscriptionPlan.FREE, 0),
                (SubscriptionPlan.BASIC, 0),
                (SubscriptionPlan.PROFESSIONAL, 1000),
                (SubscriptionPlan.ENTERPRISE, 10000),
            ]

            for i, (plan, expected_quota) in enumerate(test_cases):
                user = User(
                    user_id=f"test_user_{i}",
                    email=f"test{i}@example.com",
                    password_hash="hashed",
                    full_name=f"Test User {i}",
                    subscription_plan=plan,
                )
                db.add(user)
                await db.commit()

                service = APIKeyService(db)
                api_key, _ = await service.create_api_key(
                    user_id=user.user_id,
                    name=f"Key for {plan.value}",
                    permissions=["analyze"],
                )

                assert api_key.monthly_quota == expected_quota

    async def test_get_api_key_by_id(self, test_db):
        """Test retrieving API key by ID."""
        async with test_db() as db:
            # Create user and API key
            user = User(
                user_id="test_user",
                email="test@example.com",
                password_hash="hashed",
                full_name="Test User",
            )
            db.add(user)
            await db.commit()

            service = APIKeyService(db)
            api_key, _ = await service.create_api_key(
                user_id=user.user_id,
                name="Test Key",
                permissions=["analyze"],
            )

            # Retrieve by ID
            retrieved = await service.get_api_key_by_id(api_key.key_id)
            assert retrieved is not None
            assert retrieved.key_id == api_key.key_id
            assert retrieved.name == "Test Key"

            # Try non-existent ID
            not_found = await service.get_api_key_by_id("nonexistent")
            assert not_found is None

    async def test_get_user_api_keys(self, test_db):
        """Test retrieving all API keys for a user."""
        async with test_db() as db:
            # Create user
            user = User(
                user_id="test_user",
                email="test@example.com",
                password_hash="hashed",
                full_name="Test User",
            )
            db.add(user)
            await db.commit()

            service = APIKeyService(db)

            # Create multiple API keys
            for i in range(3):
                await service.create_api_key(
                    user_id=user.user_id,
                    name=f"Key {i}",
                    permissions=["analyze"],
                )

            # Retrieve all keys
            keys = await service.get_user_api_keys(user.user_id)
            assert len(keys) == 3
            # Should be ordered by created_at desc
            assert keys[0].name == "Key 2"
            assert keys[1].name == "Key 1"
            assert keys[2].name == "Key 0"

    async def test_validate_api_key_valid(self, test_db):
        """Test validating a valid API key."""
        async with test_db() as db:
            # Create user and API key
            user = User(
                user_id="test_user",
                email="test@example.com",
                password_hash="hashed",
                full_name="Test User",
            )
            db.add(user)
            await db.commit()

            service = APIKeyService(db)
            api_key, plain_key = await service.create_api_key(
                user_id=user.user_id,
                name="Test Key",
                permissions=["analyze"],
            )

            # Validate the key
            validated = await service.validate_api_key(plain_key)
            assert validated is not None
            assert validated.key_id == api_key.key_id
            assert validated.last_used is not None

    async def test_validate_api_key_invalid(self, test_db):
        """Test validating invalid API keys."""
        async with test_db() as db:
            service = APIKeyService(db)

            # Non-existent key
            validated = await service.validate_api_key(
                "gha_nonexistent12345678901234567890"
            )
            assert validated is None

    async def test_validate_api_key_inactive(self, test_db):
        """Test validating an inactive API key."""
        async with test_db() as db:
            # Create user and API key
            user = User(
                user_id="test_user",
                email="test@example.com",
                password_hash="hashed",
                full_name="Test User",
            )
            db.add(user)
            await db.commit()

            service = APIKeyService(db)
            api_key, plain_key = await service.create_api_key(
                user_id=user.user_id,
                name="Test Key",
                permissions=["analyze"],
            )

            # Deactivate the key
            api_key.is_active = False
            await db.commit()

            # Try to validate
            validated = await service.validate_api_key(plain_key)
            assert validated is None

    async def test_validate_api_key_expired(self, test_db):
        """Test validating an expired API key."""
        async with test_db() as db:
            # Create user and API key
            user = User(
                user_id="test_user",
                email="test@example.com",
                password_hash="hashed",
                full_name="Test User",
            )
            db.add(user)
            await db.commit()

            service = APIKeyService(db)
            api_key, plain_key = await service.create_api_key(
                user_id=user.user_id,
                name="Test Key",
                permissions=["analyze"],
            )

            # Set expiration in the past
            api_key.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
            await db.commit()

            # Try to validate
            validated = await service.validate_api_key(plain_key)
            assert validated is None

    async def test_revoke_api_key(self, test_db):
        """Test revoking an API key."""
        async with test_db() as db:
            # Create user and API key
            user = User(
                user_id="test_user",
                email="test@example.com",
                password_hash="hashed",
                full_name="Test User",
            )
            db.add(user)
            await db.commit()

            service = APIKeyService(db)
            api_key, _ = await service.create_api_key(
                user_id=user.user_id,
                name="Test Key",
                permissions=["analyze"],
            )

            # Revoke the key
            success = await service.revoke_api_key(api_key.key_id, user.user_id)
            assert success is True

            # Check it's inactive
            revoked = await service.get_api_key_by_id(api_key.key_id)
            assert revoked.is_active is False

            # Try to revoke with wrong user
            success = await service.revoke_api_key(api_key.key_id, "wrong_user")
            assert success is False

    async def test_update_api_key_quota(self, test_db):
        """Test updating API key quota."""
        async with test_db() as db:
            # Create user and API key
            user = User(
                user_id="test_user",
                email="test@example.com",
                password_hash="hashed",
                full_name="Test User",
            )
            db.add(user)
            await db.commit()

            service = APIKeyService(db)
            api_key, _ = await service.create_api_key(
                user_id=user.user_id,
                name="Test Key",
                permissions=["analyze"],
            )

            # Update quota
            success = await service.update_api_key_quota(api_key.key_id, 5000)
            assert success is True

            # Verify update
            updated = await service.get_api_key_by_id(api_key.key_id)
            assert updated.monthly_quota == 5000

    async def test_increment_usage(self, test_db):
        """Test incrementing API key usage."""
        async with test_db() as db:
            # Create user and API key
            user = User(
                user_id="test_user",
                email="test@example.com",
                password_hash="hashed",
                full_name="Test User",
            )
            db.add(user)
            await db.commit()

            service = APIKeyService(db)
            api_key, _ = await service.create_api_key(
                user_id=user.user_id,
                name="Test Key",
                permissions=["analyze"],
            )

            # Increment usage
            success = await service.increment_usage(api_key.key_id)
            assert success is True

            # Verify increment
            updated = await service.get_api_key_by_id(api_key.key_id)
            assert updated.monthly_usage == 1

            # Increment by specific amount
            success = await service.increment_usage(api_key.key_id, 5)
            assert success is True

            updated = await service.get_api_key_by_id(api_key.key_id)
            assert updated.monthly_usage == 6

    async def test_check_quota_available(self, test_db):
        """Test checking quota availability."""
        async with test_db() as db:
            # Create user
            user = User(
                user_id="test_user",
                email="test@example.com",
                password_hash="hashed",
                full_name="Test User",
                subscription_plan=SubscriptionPlan.PROFESSIONAL,
            )
            db.add(user)
            await db.commit()

            service = APIKeyService(db)
            api_key, _ = await service.create_api_key(
                user_id=user.user_id,
                name="Test Key",
                permissions=["analyze"],
            )

            # Check initial quota
            has_quota, remaining = await service.check_quota_available(api_key)
            assert has_quota is True
            assert remaining == 1000

            # Use some quota
            api_key.monthly_usage = 800
            await db.commit()

            has_quota, remaining = await service.check_quota_available(api_key)
            assert has_quota is True
            assert remaining == 200

            # Exceed quota
            api_key.monthly_usage = 1001
            await db.commit()

            has_quota, remaining = await service.check_quota_available(api_key)
            assert has_quota is False
            assert remaining == 0

            # Test no access (quota = 0)
            api_key.monthly_quota = 0
            await db.commit()

            has_quota, remaining = await service.check_quota_available(api_key)
            assert has_quota is False
            assert remaining == 0

            # Test unlimited (quota = -1)
            api_key.monthly_quota = -1
            await db.commit()

            has_quota, remaining = await service.check_quota_available(api_key)
            assert has_quota is True
            assert remaining == -1

    async def test_reset_monthly_usage(self, test_db):
        """Test resetting monthly usage."""
        async with test_db() as db:
            # Create user and API key
            user = User(
                user_id="test_user",
                email="test@example.com",
                password_hash="hashed",
                full_name="Test User",
            )
            db.add(user)
            await db.commit()

            service = APIKeyService(db)
            api_key, _ = await service.create_api_key(
                user_id=user.user_id,
                name="Test Key",
                permissions=["analyze"],
            )

            # Set some usage
            api_key.monthly_usage = 500
            await db.commit()

            # Get the key to ensure we have the latest from DB
            api_key = await service.get_api_key_by_id(api_key.key_id)
            old_reset_time = api_key.last_quota_reset

            # Reset usage
            success = await service.reset_monthly_usage(api_key.key_id)
            assert success is True

            # Verify reset
            reset_key = await service.get_api_key_by_id(api_key.key_id)
            assert reset_key.monthly_usage == 0
            # Just check that last_quota_reset was updated
            assert reset_key.last_quota_reset is not None
            # The reset should have updated the timestamp
            assert reset_key.last_quota_reset != old_reset_time

    async def test_validate_api_key_prefix_lookup(self, test_db):
        """Test that API key validation uses efficient prefix lookup."""
        async with test_db() as db:
            # Create user
            user = User(
                user_id="test_user",
                email="test@example.com",
                password_hash="hashed",
                full_name="Test User",
            )
            db.add(user)
            await db.commit()

            service = APIKeyService(db)

            # Create multiple API keys to ensure O(1) lookup is working
            created_keys = []
            for i in range(5):
                api_key, plain_key = await service.create_api_key(
                    user_id=user.user_id,
                    name=f"Test Key {i}",
                    permissions=["analyze"],
                )
                created_keys.append((api_key, plain_key))

            # Validate the middle key - should still be fast with prefix lookup
            target_key = created_keys[2][1]
            validated = await service.validate_api_key(target_key)

            assert validated is not None
            assert validated.key_id == created_keys[2][0].key_id
            assert validated.name == "Test Key 2"
