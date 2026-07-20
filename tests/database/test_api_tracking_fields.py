"""Tests for API tracking fields in usage records."""

import pytest
from sqlalchemy import select

from github_analyzer.database.models import APIKey, UsageRecord, User


@pytest.mark.asyncio
async def test_usage_record_api_tracking_fields(test_db):
    """Test that usage records can track API key usage."""
    async with test_db() as db:
        # Create a user
        user = User(
            user_id="test_user_api",
            email="api@example.com",
            password_hash="hashed",
            full_name="API Test User",
        )
        db.add(user)
        await db.commit()

        # Create an API key
        api_key = APIKey(
            key_id="test_api_key",
            user_id=user.user_id,
            name="Test API Key",
            key_hash="hashed_key",
            key_prefix="test_prefix",
            salt="test_salt",
            permissions='["analyze"]',
            monthly_quota=1000,
        )
        db.add(api_key)
        await db.commit()

        # Create a usage record for API request
        api_usage = UsageRecord(
            record_id="usage_api_1",
            user_id=user.user_id,
            endpoint="/api/v1/analyze",
            method="POST",
            repository_url="https://github.com/test/repo",
            tokens_consumed=100,
            cost_incurred="0.001",
            response_time_ms=250,
            success=True,
            api_key_id=api_key.key_id,
            is_api_request=True,
        )
        db.add(api_usage)
        await db.commit()

        # Query and verify
        result = await db.execute(
            select(UsageRecord).where(UsageRecord.record_id == "usage_api_1")
        )
        saved_usage = result.scalar_one()

        assert saved_usage.api_key_id == "test_api_key"
        assert saved_usage.is_api_request is True
        assert saved_usage.api_key is not None
        assert saved_usage.api_key.name == "Test API Key"


@pytest.mark.asyncio
async def test_usage_record_web_request_defaults(test_db):
    """Test that web requests have proper defaults for API fields."""
    async with test_db() as db:
        # Create a user
        user = User(
            user_id="test_user_web",
            email="web@example.com",
            password_hash="hashed",
            full_name="Web Test User",
        )
        db.add(user)
        await db.commit()

        # Create a usage record for web request (no API key)
        web_usage = UsageRecord(
            record_id="usage_web_1",
            user_id=user.user_id,
            endpoint="/api/v1/analyze",
            method="POST",
            repository_url="https://github.com/test/repo",
            tokens_consumed=100,
            cost_incurred="0.001",
            response_time_ms=250,
            success=True,
            # Not specifying api_key_id or is_api_request
        )
        db.add(web_usage)
        await db.commit()

        # Query and verify defaults
        result = await db.execute(
            select(UsageRecord).where(UsageRecord.record_id == "usage_web_1")
        )
        saved_usage = result.scalar_one()

        assert saved_usage.api_key_id is None
        assert saved_usage.is_api_request is False
        assert saved_usage.api_key is None


@pytest.mark.asyncio
async def test_api_key_usage_records_relationship(test_db):
    """Test the relationship between API keys and usage records."""
    async with test_db() as db:
        # Create a user
        user = User(
            user_id="test_user_rel",
            email="rel@example.com",
            password_hash="hashed",
            full_name="Relationship Test User",
        )
        db.add(user)
        await db.commit()

        # Create an API key
        api_key = APIKey(
            key_id="test_api_key_rel",
            user_id=user.user_id,
            name="Relationship Test Key",
            key_hash="hashed_key",
            key_prefix="test_pf_rel",
            salt="test_salt_rel",
            permissions='["analyze"]',
            monthly_quota=1000,
        )
        db.add(api_key)
        await db.commit()

        # Create multiple usage records
        for i in range(3):
            usage = UsageRecord(
                record_id=f"usage_rel_{i}",
                user_id=user.user_id,
                endpoint="/api/v1/analyze",
                method="POST",
                repository_url=f"https://github.com/test/repo{i}",
                tokens_consumed=100,
                cost_incurred="0.001",
                response_time_ms=250,
                success=True,
                api_key_id=api_key.key_id,
                is_api_request=True,
            )
            db.add(usage)
        await db.commit()

        # Query usage records for this API key
        result = await db.execute(
            select(UsageRecord).where(UsageRecord.api_key_id == "test_api_key_rel")
        )
        usage_records = result.scalars().all()

        # Verify we have 3 records
        assert len(usage_records) == 3
        assert all(record.is_api_request for record in usage_records)
        assert all(record.api_key_id == "test_api_key_rel" for record in usage_records)
