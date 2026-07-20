"""
Tests for priority support service.
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from github_analyzer.api.services.priority_support_service import (
    PrioritySupportService,
)
from github_analyzer.database.models import (
    ContactMessage,
    ContactStatus,
    SubscriptionPlan,
    User,
)


@pytest.fixture
def mock_scale_plus_user() -> User:
    """Create a mock Scale+ user."""
    user = MagicMock(spec=User)
    user.user_id = str(uuid.uuid4())
    user.email = "scaleplus@test.com"
    user.subscription_plan = SubscriptionPlan.SCALE_PLUS
    user.is_admin = False
    return user


@pytest.fixture
def mock_enterprise_user() -> User:
    """Create a mock Enterprise user."""
    user = MagicMock(spec=User)
    user.user_id = str(uuid.uuid4())
    user.email = "enterprise@test.com"
    user.subscription_plan = SubscriptionPlan.ENTERPRISE
    user.is_admin = False
    return user


@pytest.fixture
def mock_professional_user() -> User:
    """Create a mock Professional user."""
    user = MagicMock(spec=User)
    user.user_id = str(uuid.uuid4())
    user.email = "professional@test.com"
    user.subscription_plan = SubscriptionPlan.PROFESSIONAL
    user.is_admin = False
    return user


@pytest.fixture
def mock_basic_user() -> User:
    """Create a mock Basic user."""
    user = MagicMock(spec=User)
    user.user_id = str(uuid.uuid4())
    user.email = "basic@test.com"
    user.subscription_plan = SubscriptionPlan.BASIC
    user.is_admin = False
    return user


@pytest.fixture
def mock_contact_message() -> ContactMessage:
    """Create a mock contact message."""
    message = MagicMock(spec=ContactMessage)
    message.message_id = str(uuid.uuid4())
    message.user_id = str(uuid.uuid4())
    message.name = "Test User"
    message.email = "test@example.com"
    message.subject = "Test Subject"
    message.message = "Test message content"
    message.status = ContactStatus.UNREAD
    message.created_at = datetime.now(timezone.utc)
    message.is_priority = False
    message.priority_level = 0
    message.target_response_hours = 48
    message.sla_status = "green"
    message.responded_at = None
    return message


class TestPrioritySupportService:
    """Test priority support service functionality."""

    @pytest.mark.asyncio
    async def test_enhance_message_with_priority_scale_plus(
        self,
        db_session: AsyncSession,
        mock_scale_plus_user: User,
        mock_contact_message: ContactMessage,
    ):
        """Test that Scale+ users get URGENT priority."""
        service = PrioritySupportService(db_session)

        enhanced_message = await service.enhance_message_with_priority(
            mock_contact_message, mock_scale_plus_user
        )

        assert enhanced_message.is_priority is True
        assert enhanced_message.priority_level == 3  # URGENT
        assert enhanced_message.target_response_hours == 4

    @pytest.mark.asyncio
    async def test_enhance_message_with_priority_enterprise(
        self,
        db_session: AsyncSession,
        mock_enterprise_user: User,
        mock_contact_message: ContactMessage,
    ):
        """Test that Enterprise users get HIGH priority."""
        service = PrioritySupportService(db_session)

        enhanced_message = await service.enhance_message_with_priority(
            mock_contact_message, mock_enterprise_user
        )

        assert enhanced_message.is_priority is True
        assert enhanced_message.priority_level == 2  # HIGH
        assert enhanced_message.target_response_hours == 12

    @pytest.mark.asyncio
    async def test_enhance_message_with_priority_professional(
        self,
        db_session: AsyncSession,
        mock_professional_user: User,
        mock_contact_message: ContactMessage,
    ):
        """Test that Professional users get MEDIUM priority."""
        service = PrioritySupportService(db_session)

        enhanced_message = await service.enhance_message_with_priority(
            mock_contact_message, mock_professional_user
        )

        assert enhanced_message.is_priority is True
        assert enhanced_message.priority_level == 1  # MEDIUM
        assert enhanced_message.target_response_hours == 24

    @pytest.mark.asyncio
    async def test_enhance_message_with_priority_basic(
        self,
        db_session: AsyncSession,
        mock_basic_user: User,
        mock_contact_message: ContactMessage,
    ):
        """Test that Basic users get standard priority."""
        service = PrioritySupportService(db_session)

        enhanced_message = await service.enhance_message_with_priority(
            mock_contact_message, mock_basic_user
        )

        assert enhanced_message.is_priority is False
        assert enhanced_message.priority_level == 0
        assert enhanced_message.target_response_hours == 48

    @pytest.mark.asyncio
    async def test_update_sla_status_green(
        self,
        db_session: AsyncSession,
        mock_contact_message: ContactMessage,
    ):
        """Test SLA status is green when within 50% of target."""
        service = PrioritySupportService(db_session)

        # Set message as priority with 8-hour SLA
        mock_contact_message.is_priority = True
        mock_contact_message.target_response_hours = 8
        mock_contact_message.created_at = datetime.now(timezone.utc) - timedelta(
            hours=2
        )

        updated_message = await service.update_sla_status(mock_contact_message)

        assert updated_message.sla_status == "green"

    @pytest.mark.asyncio
    async def test_update_sla_status_yellow(
        self,
        db_session: AsyncSession,
        mock_contact_message: ContactMessage,
    ):
        """Test SLA status is yellow when between 50-80% of target."""
        service = PrioritySupportService(db_session)

        # Set message as priority with 8-hour SLA, created 5 hours ago
        mock_contact_message.is_priority = True
        mock_contact_message.target_response_hours = 8
        mock_contact_message.created_at = datetime.now(timezone.utc) - timedelta(
            hours=5
        )

        updated_message = await service.update_sla_status(mock_contact_message)

        assert updated_message.sla_status == "yellow"

    @pytest.mark.asyncio
    async def test_update_sla_status_red_breached(
        self,
        db_session: AsyncSession,
        mock_contact_message: ContactMessage,
    ):
        """Test SLA status is red when SLA is breached."""
        service = PrioritySupportService(db_session)

        # Set message as priority with 4-hour SLA, created 6 hours ago
        mock_contact_message.is_priority = True
        mock_contact_message.target_response_hours = 4
        mock_contact_message.created_at = datetime.now(timezone.utc) - timedelta(
            hours=6
        )

        updated_message = await service.update_sla_status(mock_contact_message)

        assert updated_message.sla_status == "red"

    @pytest.mark.asyncio
    async def test_update_sla_status_responded_within_sla(
        self,
        db_session: AsyncSession,
        mock_contact_message: ContactMessage,
    ):
        """Test SLA status is green when responded within SLA."""
        service = PrioritySupportService(db_session)

        # Set message as priority with response within SLA
        mock_contact_message.is_priority = True
        mock_contact_message.target_response_hours = 8
        mock_contact_message.status = ContactStatus.RESPONDED
        mock_contact_message.created_at = datetime.now(timezone.utc) - timedelta(
            hours=5
        )
        mock_contact_message.responded_at = mock_contact_message.created_at + timedelta(
            hours=3
        )

        updated_message = await service.update_sla_status(mock_contact_message)

        assert updated_message.sla_status == "green"

    @pytest.mark.asyncio
    async def test_check_priority_support_access_scale_plus(
        self,
        db_session: AsyncSession,
        mock_scale_plus_user: User,
    ):
        """Test Scale+ users have priority support access."""
        service = PrioritySupportService(db_session)

        # Mock the database query
        db_session.execute = AsyncMock(
            return_value=MagicMock(
                scalar_one_or_none=MagicMock(return_value=mock_scale_plus_user)
            )
        )

        has_access = await service.check_priority_support_access(
            mock_scale_plus_user.user_id
        )

        assert has_access is True

    @pytest.mark.asyncio
    async def test_check_priority_support_access_professional(
        self,
        db_session: AsyncSession,
        mock_professional_user: User,
    ):
        """Test Professional users have priority support access."""
        service = PrioritySupportService(db_session)

        # Mock the database query
        db_session.execute = AsyncMock(
            return_value=MagicMock(
                scalar_one_or_none=MagicMock(return_value=mock_professional_user)
            )
        )

        has_access = await service.check_priority_support_access(
            mock_professional_user.user_id
        )

        assert has_access is True

    @pytest.mark.asyncio
    async def test_check_priority_support_access_basic(
        self,
        db_session: AsyncSession,
        mock_basic_user: User,
    ):
        """Test Basic users don't have priority support access."""
        service = PrioritySupportService(db_session)

        # Mock the database query
        db_session.execute = AsyncMock(
            return_value=MagicMock(
                scalar_one_or_none=MagicMock(return_value=mock_basic_user)
            )
        )

        has_access = await service.check_priority_support_access(
            mock_basic_user.user_id
        )

        assert has_access is False

    @pytest.mark.asyncio
    async def test_get_sla_metrics_empty(
        self,
        db_session: AsyncSession,
    ):
        """Test SLA metrics when no priority messages exist."""
        service = PrioritySupportService(db_session)

        # Mock empty result
        db_session.execute = AsyncMock(
            return_value=MagicMock(
                scalars=MagicMock(
                    return_value=MagicMock(all=MagicMock(return_value=[]))
                )
            )
        )

        metrics = await service.get_sla_metrics(days=30)

        assert metrics["total_priority_messages"] == 0
        assert metrics["sla_met_count"] == 0
        assert metrics["sla_missed_count"] == 0
        assert metrics["sla_compliance_rate"] == 100.0
        assert metrics["average_response_time_hours"] is None

    @pytest.mark.asyncio
    async def test_get_user_support_metrics(
        self,
        db_session: AsyncSession,
        mock_contact_message: ContactMessage,
    ):
        """Test getting support metrics for a specific user."""
        service = PrioritySupportService(db_session)

        # Create multiple messages with different statuses
        message1 = MagicMock(spec=ContactMessage)
        message1.is_priority = True
        message1.status = ContactStatus.UNREAD
        message1.responded_at = None

        message2 = MagicMock(spec=ContactMessage)
        message2.is_priority = False
        message2.status = ContactStatus.RESPONDED
        message2.created_at = datetime.now(timezone.utc) - timedelta(hours=3)
        message2.responded_at = message2.created_at + timedelta(hours=2)

        # Mock the database query
        db_session.execute = AsyncMock(
            return_value=MagicMock(
                scalars=MagicMock(
                    return_value=MagicMock(
                        all=MagicMock(return_value=[message1, message2])
                    )
                )
            )
        )

        metrics = await service.get_user_support_metrics("test-user-id")

        assert metrics["total_messages"] == 2
        assert metrics["priority_messages"] == 1
        assert metrics["average_response_time_hours"] == 2.0
        assert "unread" in metrics["messages_by_status"]
        assert "responded" in metrics["messages_by_status"]
