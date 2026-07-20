"""
Tests for database models and operations.

This module tests SQLAlchemy models, database connections,
and CRUD operations for users and authentication.
"""

from datetime import datetime, timezone

import pytest

from github_analyzer.database.models import (
    AnalysisStatus,
    BatchAnalysis,
    ContactMessage,
    ContactStatus,
    SubscriptionPlan,
)

# Models will be imported through operations when needed
from github_analyzer.database.operations import (
    APIKeyOperations,
    TokenOperations,
    UsageOperations,
    UserOperations,
)


class TestUserModel:
    """Test User model and operations."""

    @pytest.mark.asyncio
    async def test_create_user(self, db_session):
        """Test user creation."""
        user = await UserOperations.create_user(
            db_session,
            email="test@example.com",
            password="secure_password123",
            full_name="Test User",
            company="Test Corp",
        )

        assert user.user_id.startswith("usr_")
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.company == "Test Corp"
        assert user.is_active is True
        assert user.is_verified is False
        assert user.usage_quota == 100
        assert user.usage_count == 0
        assert user.password_hash != "secure_password123"  # Should be hashed

    @pytest.mark.asyncio
    async def test_get_user_by_email(self, db_session):
        """Test retrieving user by email."""
        # Create user
        created_user = await UserOperations.create_user(
            db_session,
            email="lookup@example.com",
            password="password123",
            full_name="Lookup User",
        )

        # Retrieve user
        found_user = await UserOperations.get_user_by_email(
            db_session, "lookup@example.com"
        )

        assert found_user is not None
        assert found_user.user_id == created_user.user_id
        assert found_user.email == "lookup@example.com"

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, db_session):
        """Test retrieving user by ID."""
        # Create user
        created_user = await UserOperations.create_user(
            db_session,
            email="id_lookup@example.com",
            password="password123",
            full_name="ID Lookup User",
        )

        # Retrieve user
        found_user = await UserOperations.get_user_by_id(
            db_session, created_user.user_id
        )

        assert found_user is not None
        assert found_user.user_id == created_user.user_id
        assert found_user.email == "id_lookup@example.com"

    @pytest.mark.asyncio
    async def test_authenticate_user(self, db_session):
        """Test user authentication."""
        # Create user
        await UserOperations.create_user(
            db_session,
            email="auth@example.com",
            password="correct_password",
            full_name="Auth User",
        )

        # Test correct credentials
        user = await UserOperations.authenticate_user(
            db_session, "auth@example.com", "correct_password"
        )
        assert user is not None
        assert user.email == "auth@example.com"

        # Test incorrect password
        user = await UserOperations.authenticate_user(
            db_session, "auth@example.com", "wrong_password"
        )
        assert user is None

        # Test non-existent email
        user = await UserOperations.authenticate_user(
            db_session, "nonexistent@example.com", "any_password"
        )
        assert user is None

    @pytest.mark.asyncio
    async def test_duplicate_email_error(self, db_session):
        """Test that duplicate emails raise error."""
        # Create first user
        await UserOperations.create_user(
            db_session,
            email="duplicate@example.com",
            password="password1",
            full_name="First User",
        )

        # Try to create second user with same email
        with pytest.raises(ValueError, match="Email address already registered"):
            await UserOperations.create_user(
                db_session,
                email="duplicate@example.com",
                password="password2",
                full_name="Second User",
            )

    @pytest.mark.asyncio
    async def test_update_password(self, db_session):
        """Test password update."""
        # Create user
        user = await UserOperations.create_user(
            db_session,
            email="password_update@example.com",
            password="old_password",
            full_name="Password User",
        )

        original_hash = user.password_hash

        # Update password
        success = await UserOperations.update_password(
            db_session, user.user_id, "new_password"
        )

        assert success is True

        # Verify password changed
        updated_user = await UserOperations.get_user_by_id(db_session, user.user_id)
        assert updated_user.password_hash != original_hash

        # Verify authentication works with new password
        auth_user = await UserOperations.authenticate_user(
            db_session, "password_update@example.com", "new_password"
        )
        assert auth_user is not None


class TestAPIKeyModel:
    """Test APIKey model and operations."""

    @pytest.mark.asyncio
    async def test_create_api_key(self, db_session):
        """Test API key creation."""
        # Create user first
        user = await UserOperations.create_user(
            db_session,
            email="api_user@example.com",
            password="password123",
            full_name="API User",
        )

        # Create API key
        api_key = await APIKeyOperations.create_api_key(
            db_session,
            user_id=user.user_id,
            name="Test API Key",
            key_hash="hashed_key_value",
            key_prefix="test_prefix",
            salt="test_salt",
            permissions=["analyze", "batch"],
        )

        assert api_key.key_id.startswith("key_")
        assert api_key.user_id == user.user_id
        assert api_key.name == "Test API Key"
        assert api_key.key_hash == "hashed_key_value"
        assert api_key.is_active is True
        assert api_key.expires_at is None

    @pytest.mark.asyncio
    async def test_get_user_api_keys(self, db_session):
        """Test retrieving user's API keys."""
        # Create user
        user = await UserOperations.create_user(
            db_session,
            email="multi_keys@example.com",
            password="password123",
            full_name="Multi Keys User",
        )

        # Create multiple API keys
        await APIKeyOperations.create_api_key(
            db_session,
            user_id=user.user_id,
            name="Key 1",
            key_hash="hash1",
            key_prefix="prefix1",
            salt="salt1",
            permissions=["analyze"],
        )

        await APIKeyOperations.create_api_key(
            db_session,
            user_id=user.user_id,
            name="Key 2",
            key_hash="hash2",
            key_prefix="prefix2",
            salt="salt2",
            permissions=["batch"],
        )

        # Retrieve keys
        keys = await APIKeyOperations.get_user_api_keys(db_session, user.user_id)

        assert len(keys) == 2
        key_names = [key.name for key in keys]
        assert "Key 1" in key_names
        assert "Key 2" in key_names

    @pytest.mark.asyncio
    async def test_deactivate_api_key(self, db_session):
        """Test API key deactivation."""
        # Create user and API key
        user = await UserOperations.create_user(
            db_session,
            email="deactivate@example.com",
            password="password123",
            full_name="Deactivate User",
        )

        api_key = await APIKeyOperations.create_api_key(
            db_session,
            user_id=user.user_id,
            name="Deactivate Key",
            key_hash="deactivate_hash",
            key_prefix="deact_key1",
            salt="deactivate_salt",
            permissions=["analyze"],
        )

        assert api_key.is_active is True

        # Deactivate key
        success = await APIKeyOperations.deactivate_api_key(
            db_session, api_key.key_id, user.user_id
        )

        assert success is True

        # Verify key is deactivated
        updated_key = await APIKeyOperations.get_api_key_by_id(
            db_session, api_key.key_id
        )
        assert updated_key.is_active is False


class TestUsageOperations:
    """Test usage tracking operations."""

    @pytest.mark.asyncio
    async def test_record_usage(self, db_session):
        """Test recording usage event."""
        # Create user
        user = await UserOperations.create_user(
            db_session,
            email="usage@example.com",
            password="password123",
            full_name="Usage User",
        )

        # Record usage
        usage_record = await UsageOperations.record_usage(
            db_session,
            user_id=user.user_id,
            endpoint="/api/v1/analyze",
            method="POST",
            repository_url="https://github.com/user/repo",
            tokens_consumed=150,
            cost_incurred="0.05",
            response_time_ms=1250,
            success=True,
        )

        assert usage_record.record_id.startswith("usage_")
        assert usage_record.user_id == user.user_id
        assert usage_record.endpoint == "/api/v1/analyze"
        assert usage_record.tokens_consumed == 150
        assert usage_record.success is True

        # Verify user's usage consumed was incremented
        updated_user = await UserOperations.get_user_by_id(db_session, user.user_id)
        assert updated_user.usage_count == 1

    @pytest.mark.asyncio
    async def test_get_user_usage(self, db_session):
        """Test retrieving user usage records."""
        # Create user
        user = await UserOperations.create_user(
            db_session,
            email="usage_history@example.com",
            password="password123",
            full_name="Usage History User",
        )

        # Record multiple usage events
        await UsageOperations.record_usage(
            db_session,
            user_id=user.user_id,
            endpoint="/api/v1/analyze",
            method="POST",
            repository_url="https://github.com/user/repo1",
            tokens_consumed=100,
            cost_incurred="0.03",
            response_time_ms=1000,
            success=True,
        )

        await UsageOperations.record_usage(
            db_session,
            user_id=user.user_id,
            endpoint="/api/v1/batch",
            method="POST",
            repository_url=None,
            tokens_consumed=250,
            cost_incurred="0.08",
            response_time_ms=2500,
            success=True,
        )

        # Retrieve usage records
        usage_records = await UsageOperations.get_user_usage(db_session, user.user_id)

        assert len(usage_records) == 2
        endpoints = [record.endpoint for record in usage_records]
        assert "/api/v1/analyze" in endpoints
        assert "/api/v1/batch" in endpoints


class TestTokenOperations:
    """Test token blacklist operations."""

    @pytest.mark.asyncio
    async def test_blacklist_token(self, db_session):
        """Test token blacklisting."""
        expires_at = datetime.now(timezone.utc)

        user = await UserOperations.create_user(
            db_session,
            email="blacklist@example.com",
            password="password123",
            full_name="Blacklist User",
        )

        # Blacklist token
        blacklist_entry = await TokenOperations.blacklist_token(
            db_session,
            token_id="test_token_123",
            user_id=user.user_id,
            token_type="access",
            expires_at=expires_at,
        )

        assert blacklist_entry.token_id == "test_token_123"
        assert blacklist_entry.user_id == user.user_id
        assert blacklist_entry.token_type == "access"
        assert blacklist_entry.expires_at == expires_at

    @pytest.mark.asyncio
    async def test_is_token_blacklisted(self, db_session):
        """Test checking if token is blacklisted."""
        # Token should not be blacklisted initially
        is_blacklisted = await TokenOperations.is_token_blacklisted(
            db_session, "check_token_456"
        )
        assert is_blacklisted is False

        user = await UserOperations.create_user(
            db_session,
            email="blacklist_check@example.com",
            password="password123",
            full_name="Blacklist Check User",
        )

        # Blacklist the token
        await TokenOperations.blacklist_token(
            db_session,
            token_id="check_token_456",
            user_id=user.user_id,
            token_type="refresh",
            expires_at=datetime.now(timezone.utc),
        )

        # Now token should be blacklisted
        is_blacklisted = await TokenOperations.is_token_blacklisted(
            db_session, "check_token_456"
        )
        assert is_blacklisted is True


class TestSubscriptionPlanEnum:
    """Test SubscriptionPlan enum including new SCALE_PLUS."""

    def test_scale_plus_enum_exists(self):
        """Test that SCALE_PLUS enum value exists."""
        assert hasattr(SubscriptionPlan, "SCALE_PLUS")
        assert SubscriptionPlan.SCALE_PLUS.value == "SCALE_PLUS"

    def test_all_subscription_plans(self):
        """Test all subscription plan values."""
        expected_plans = {"FREE", "BASIC", "PROFESSIONAL", "ENTERPRISE", "SCALE_PLUS"}
        actual_plans = {plan.value for plan in SubscriptionPlan}
        assert actual_plans == expected_plans


class TestPrioritySupportFields:
    """Test priority support fields in User and ContactMessage models."""

    @pytest.mark.asyncio
    async def test_user_priority_support_fields(self, db_session):
        """Test User model has priority support fields."""
        user = await UserOperations.create_user(
            db_session,
            email="priority@example.com",
            password="password123",
            full_name="Priority User",
        )

        # Check default values
        assert user.is_priority_support is False
        assert user.response_time_hours == 48

        # Update priority support
        user.is_priority_support = True
        user.response_time_hours = 6  # Scale+ response time
        await db_session.commit()

        # Verify updates
        updated_user = await UserOperations.get_user_by_id(db_session, user.user_id)
        assert updated_user.is_priority_support is True
        assert updated_user.response_time_hours == 6

    @pytest.mark.asyncio
    async def test_contact_message_priority_fields(self, db_session):
        """Test ContactMessage model has priority fields."""
        # Create a contact message
        message = ContactMessage(
            message_id="msg_test123",
            name="Test User",
            email="test@example.com",
            subject="Test Subject",
            message="Test message content",
            created_at=datetime.now(timezone.utc),
        )

        # Add to session first to get defaults
        db_session.add(message)
        await db_session.commit()

        # Check default values
        assert message.is_priority is False
        assert message.priority_level == 0
        assert message.target_response_hours == 48
        assert message.sla_status == "green"
        assert message.status == ContactStatus.UNREAD

        # Update priority fields
        message.is_priority = True
        message.priority_level = 2  # Scale+ level
        message.target_response_hours = 6
        message.sla_status = "yellow"
        await db_session.commit()

        # Verify updates
        await db_session.refresh(message)
        assert message.is_priority is True
        assert message.priority_level == 2
        assert message.target_response_hours == 6
        assert message.sla_status == "yellow"


class TestBatchAnalysisModel:
    """Test BatchAnalysis model for batch history tracking."""

    @pytest.mark.asyncio
    async def test_create_batch_analysis(self, db_session):
        """Test creating a batch analysis record."""
        # Create user first
        user = await UserOperations.create_user(
            db_session,
            email="batch_user@example.com",
            password="password123",
            full_name="Batch User",
        )

        # Create batch analysis
        batch = BatchAnalysis(
            batch_id="batch_test123",
            user_id=user.user_id,
            repository_count=5,
            contexts='["startup", "enterprise"]',
            status=AnalysisStatus.PENDING,
        )

        db_session.add(batch)
        await db_session.commit()

        # Check default values
        assert batch.successful_count == 0
        assert batch.failed_count == 0
        assert batch.processing_time_ms is None
        assert batch.total_cost is None
        assert batch.completed_at is None
        assert batch.error_messages is None

        # Update batch progress
        batch.status = AnalysisStatus.PROCESSING
        batch.successful_count = 3
        batch.failed_count = 1
        await db_session.commit()

        await db_session.refresh(batch)
        assert batch.status == AnalysisStatus.PROCESSING
        assert batch.successful_count == 3
        assert batch.failed_count == 1

    @pytest.mark.asyncio
    async def test_batch_analysis_completion(self, db_session):
        """Test completing a batch analysis."""
        # Create user
        user = await UserOperations.create_user(
            db_session,
            email="batch_complete@example.com",
            password="password123",
            full_name="Batch Complete User",
        )

        # Create and complete batch
        batch = BatchAnalysis(
            batch_id="batch_complete123",
            user_id=user.user_id,
            repository_count=10,
            contexts='["startup"]',
            status=AnalysisStatus.COMPLETED,
            successful_count=9,
            failed_count=1,
            processing_time_ms=15000,
            total_cost=1.25,
            error_messages='["Error analyzing repo X"]',
            completed_at=datetime.now(timezone.utc),
        )

        db_session.add(batch)
        await db_session.commit()

        # Verify completion fields
        assert batch.status == AnalysisStatus.COMPLETED
        assert batch.successful_count == 9
        assert batch.failed_count == 1
        assert batch.processing_time_ms == 15000
        assert batch.total_cost == 1.25
        assert batch.completed_at is not None

    @pytest.mark.asyncio
    async def test_batch_analysis_relationships(self, db_session):
        """Test BatchAnalysis relationships."""
        # Create user
        user = await UserOperations.create_user(
            db_session,
            email="batch_rel@example.com",
            password="password123",
            full_name="Batch Relationship User",
        )

        # Create batch
        batch = BatchAnalysis(
            batch_id="batch_rel123",
            user_id=user.user_id,
            repository_count=3,
            contexts='["enterprise"]',
        )

        db_session.add(batch)
        await db_session.commit()

        # Test user relationship
        await db_session.refresh(batch)
        assert batch.user.user_id == user.user_id
        assert batch.user.email == "batch_rel@example.com"
