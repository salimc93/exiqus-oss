"""Tests for API quota database schema."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from github_analyzer.database.models import APIKey, User


@pytest.mark.asyncio
async def test_api_key_quota_fields(test_db):
    """Test that API key quota fields are properly added."""
    async with test_db() as db:
        # Create a user
        user = User(
            user_id="test_user_1",
            email="test@example.com",
            password_hash="hashed",
            full_name="Test User",
        )
        db.add(user)
        await db.commit()

        # Create an API key with quota fields
        api_key = APIKey(
            key_id="test_key_1",
            user_id=user.user_id,
            name="Test API Key",
            key_hash="hashed_key",
            key_prefix="test_prefix",
            salt="test_salt",
            permissions="[]",
            monthly_quota=1000,
            monthly_usage=250,
            last_quota_reset=datetime.now(timezone.utc),
        )
        db.add(api_key)
        await db.commit()

        # Query and verify
        result = await db.execute(select(APIKey).where(APIKey.key_id == "test_key_1"))
        saved_key = result.scalar_one()

        assert saved_key.monthly_quota == 1000
        assert saved_key.monthly_usage == 250
        assert saved_key.last_quota_reset is not None


@pytest.mark.asyncio
async def test_api_key_quota_defaults(test_db):
    """Test that API key quota fields have proper defaults."""
    async with test_db() as db:
        # Create a user
        user = User(
            user_id="test_user_2",
            email="test2@example.com",
            password_hash="hashed",
            full_name="Test User 2",
        )
        db.add(user)
        await db.commit()

        # Create an API key without specifying quota fields
        api_key = APIKey(
            key_id="test_key_2",
            user_id=user.user_id,
            name="Test API Key 2",
            key_hash="hashed_key",
            key_prefix="test_prefix2",
            salt="test_salt2",
            permissions="[]",
        )
        db.add(api_key)
        await db.commit()

        # Query and verify defaults
        result = await db.execute(select(APIKey).where(APIKey.key_id == "test_key_2"))
        saved_key = result.scalar_one()

        assert saved_key.monthly_quota == 0
        assert saved_key.monthly_usage == 0
        assert saved_key.last_quota_reset is None
