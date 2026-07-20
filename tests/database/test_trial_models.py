"""Tests for trial/invite system database models."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from github_analyzer.database.models import AuditLog, User


@pytest.mark.asyncio
async def test_user_trial_fields(test_db):
    """Test that User model includes all trial-related fields."""
    async with test_db() as db_session:
        # Create a trial user
        user = User(
            user_id=str(uuid.uuid4()),
            email="trial@example.com",
            password_hash="hashed_password",
            full_name="Trial User",
            company="Test Company",
            is_trial=True,
            trial_plan="professional",
            trial_analyses_limit=500,
            analyses_consumed=25,
            invite_token="test_token_123",
            invite_token_expires=datetime.now(timezone.utc) + timedelta(hours=48),
            has_completed_onboarding=False,
            trial_value="$149/month",
            trial_end_date=datetime.now(timezone.utc) + timedelta(days=7),
        )

        db_session.add(user)
        await db_session.commit()

        # Query the user back
        result = await db_session.execute(
            select(User).where(User.email == "trial@example.com")
        )
        saved_user = result.scalar_one()

        # Verify all trial fields
        assert saved_user.is_trial is True
        assert saved_user.trial_plan == "professional"
        assert saved_user.trial_analyses_limit == 500
        assert saved_user.analyses_consumed == 25
        assert saved_user.invite_token == "test_token_123"
        assert saved_user.invite_token_expires is not None
        assert saved_user.has_completed_onboarding is False
        assert saved_user.trial_value == "$149/month"
        assert saved_user.trial_end_date is not None


@pytest.mark.asyncio
async def test_user_trial_unlimited_plan(test_db):
    """Test that unlimited trial plans work with None as limit."""
    async with test_db() as db_session:
        user = User(
            user_id=str(uuid.uuid4()),
            email="enterprise@example.com",
            password_hash="hashed_password",
            full_name="Enterprise User",
            is_trial=True,
            trial_plan="enterprise",
            trial_analyses_limit=None,  # Unlimited
            trial_value="$399/month",
        )

        db_session.add(user)
        await db_session.commit()

        # Query back
        result = await db_session.execute(
            select(User).where(User.email == "enterprise@example.com")
        )
        saved_user = result.scalar_one()

        assert saved_user.trial_analyses_limit is None  # Unlimited


@pytest.mark.asyncio
async def test_invite_token_unique_constraint(test_db):
    """Test that invite tokens must be unique."""
    async with test_db() as db_session:
        # Create first user with invite token
        user1 = User(
            user_id=str(uuid.uuid4()),
            email="user1@example.com",
            password_hash="hashed_password",
            full_name="User 1",
            invite_token="duplicate_token",
        )
        db_session.add(user1)
        await db_session.commit()

        # Try to create second user with same invite token
        user2 = User(
            user_id=str(uuid.uuid4()),
            email="user2@example.com",
            password_hash="hashed_password",
            full_name="User 2",
            invite_token="duplicate_token",  # Same token
        )
        db_session.add(user2)

        # Should raise integrity error
        with pytest.raises(Exception):  # IntegrityError
            await db_session.commit()


@pytest.mark.asyncio
async def test_audit_log_creation(test_db):
    """Test creating audit log entries."""
    async with test_db() as db_session:
        # Create admin and target users
        admin = User(
            user_id=str(uuid.uuid4()),
            email="admin@example.com",
            password_hash="hashed_password",
            full_name="Admin User",
            is_admin=True,
        )
        db_session.add(admin)
        await db_session.commit()

        # Create audit log entry
        audit_log = AuditLog(
            log_id=str(uuid.uuid4()),
            action="trial_granted",
            admin_id=admin.user_id,
            target_email="newuser@example.com",
            action_metadata='{"trial_days": 7, "trial_plan": "professional"}',
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )
        db_session.add(audit_log)
        await db_session.commit()

        # Query back
        result = await db_session.execute(
            select(AuditLog).where(AuditLog.action == "trial_granted")
        )
        saved_log = result.scalar_one()

        assert saved_log.admin_id == admin.user_id
        assert saved_log.target_email == "newuser@example.com"
        assert saved_log.action_metadata is not None
        assert saved_log.ip_address == "192.168.1.1"
        assert saved_log.created_at is not None


@pytest.mark.asyncio
async def test_audit_log_relationships(test_db):
    """Test audit log relationships with users."""
    async with test_db() as db_session:
        # Create admin and target user
        admin = User(
            user_id=str(uuid.uuid4()),
            email="admin@example.com",
            password_hash="hashed_password",
            full_name="Admin User",
            is_admin=True,
        )
        target_user = User(
            user_id=str(uuid.uuid4()),
            email="target@example.com",
            password_hash="hashed_password",
            full_name="Target User",
            is_trial=True,
        )
        db_session.add_all([admin, target_user])
        await db_session.commit()

        # Create audit log with both admin and target user
        audit_log = AuditLog(
            log_id=str(uuid.uuid4()),
            action="trial_activated",
            admin_id=admin.user_id,
            target_user_id=target_user.user_id,
            target_email=target_user.email,
        )
        db_session.add(audit_log)
        await db_session.commit()

        # Query with relationships
        result = await db_session.execute(
            select(AuditLog)
            .where(AuditLog.action == "trial_activated")
            .options(
                # Eager load relationships
                selectinload(AuditLog.admin),
                selectinload(AuditLog.target_user),
            )
        )
        saved_log = result.scalar_one()

        # Verify relationships work
        assert saved_log.admin.email == "admin@example.com"
        assert saved_log.target_user.email == "target@example.com"


@pytest.mark.asyncio
async def test_trial_user_defaults(test_db):
    """Test default values for trial fields."""
    async with test_db() as db_session:
        # Create minimal user
        user = User(
            user_id=str(uuid.uuid4()),
            email="minimal@example.com",
            password_hash="hashed_password",
            full_name="Minimal User",
        )
        db_session.add(user)
        await db_session.commit()

        # Query back
        result = await db_session.execute(
            select(User).where(User.email == "minimal@example.com")
        )
        saved_user = result.scalar_one()

        # Check defaults
        assert saved_user.is_trial is False
        assert saved_user.trial_plan is None
        assert saved_user.trial_analyses_limit is None
        assert saved_user.analyses_consumed == 0
        assert saved_user.invite_token is None
        assert saved_user.has_completed_onboarding is False
