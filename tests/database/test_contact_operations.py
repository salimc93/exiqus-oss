"""
Tests for ContactOperations database operations.
"""

from datetime import datetime
from typing import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from github_analyzer.database.models import ContactStatus
from github_analyzer.database.operations import ContactOperations, UserOperations


@pytest.fixture
async def db_session(
    test_db: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """Get database session for tests."""
    async with test_db() as session:
        yield session


@pytest.mark.asyncio
async def test_create_message(db_session: AsyncSession) -> None:
    """Test creating a new contact message."""
    # Create a contact message
    message = await ContactOperations.create_message(
        db=db_session,
        name="John Doe",
        email="john.doe@example.com",
        subject="Test Subject",
        message="This is a test message content.",
    )

    # Verify the message was created
    assert message.message_id.startswith("msg_")
    assert message.name == "John Doe"
    assert message.email == "john.doe@example.com"
    assert message.subject == "Test Subject"
    assert message.message == "This is a test message content."
    assert message.status == ContactStatus.UNREAD
    assert message.admin_response is None
    assert message.responded_at is None
    assert message.responded_by is None
    assert isinstance(message.created_at, datetime)


@pytest.mark.asyncio
async def test_get_message_by_id(db_session: AsyncSession) -> None:
    """Test retrieving a message by ID."""
    # Create a message
    created_message = await ContactOperations.create_message(
        db=db_session,
        name="Jane Smith",
        email="jane.smith@example.com",
        subject="Query",
        message="I have a question about the service.",
    )

    # Retrieve the message
    retrieved_message = await ContactOperations.get_message_by_id(
        db_session, created_message.message_id
    )

    # Verify the retrieved message
    assert retrieved_message is not None
    assert retrieved_message.message_id == created_message.message_id
    assert retrieved_message.name == "Jane Smith"
    assert retrieved_message.email == "jane.smith@example.com"

    # Test non-existent message
    non_existent = await ContactOperations.get_message_by_id(
        db_session, "msg_nonexistent"
    )
    assert non_existent is None


@pytest.mark.asyncio
async def test_get_messages_pagination(db_session: AsyncSession) -> None:
    """Test getting paginated list of messages."""
    # Create multiple messages
    for i in range(5):
        await ContactOperations.create_message(
            db=db_session,
            name=f"User {i}",
            email=f"user{i}@example.com",
            subject=f"Subject {i}",
            message=f"Message content {i}",
        )

    # Test pagination
    messages, total = await ContactOperations.get_messages(
        db_session, limit=3, offset=0
    )
    assert len(messages) == 3
    assert total == 5

    # Test second page
    messages_page2, total2 = await ContactOperations.get_messages(
        db_session, limit=3, offset=3
    )
    assert len(messages_page2) == 2
    assert total2 == 5

    # Verify messages are ordered by created_at descending
    for i in range(len(messages) - 1):
        assert messages[i].created_at >= messages[i + 1].created_at


@pytest.mark.asyncio
async def test_get_messages_with_status_filter(db_session: AsyncSession) -> None:
    """Test filtering messages by status."""
    # Create messages with different statuses
    await ContactOperations.create_message(
        db=db_session,
        name="Unread User",
        email="unread@example.com",
        subject="Unread",
        message="Unread message",
    )

    msg2 = await ContactOperations.create_message(
        db=db_session,
        name="Read User",
        email="read@example.com",
        subject="Read",
        message="Read message",
    )
    await ContactOperations.update_message_status(
        db_session, msg2.message_id, ContactStatus.READ
    )

    # Test filtering by status
    unread_messages, unread_total = await ContactOperations.get_messages(
        db_session, status=ContactStatus.UNREAD
    )
    assert unread_total == 1
    assert unread_messages[0].status == ContactStatus.UNREAD

    read_messages, read_total = await ContactOperations.get_messages(
        db_session, status=ContactStatus.READ
    )
    assert read_total == 1
    assert read_messages[0].status == ContactStatus.READ


@pytest.mark.asyncio
async def test_update_message_status(db_session: AsyncSession) -> None:
    """Test updating message status."""
    # Create a message
    message = await ContactOperations.create_message(
        db=db_session,
        name="Status Test",
        email="status@example.com",
        subject="Status Update",
        message="Testing status update",
    )

    # Update status to READ
    success = await ContactOperations.update_message_status(
        db_session, message.message_id, ContactStatus.READ
    )
    assert success is True

    # Verify status was updated
    updated_message = await ContactOperations.get_message_by_id(
        db_session, message.message_id
    )
    assert updated_message is not None
    assert updated_message.status == ContactStatus.READ

    # Test updating non-existent message
    success = await ContactOperations.update_message_status(
        db_session, "msg_nonexistent", ContactStatus.READ
    )
    assert success is False


@pytest.mark.asyncio
async def test_add_admin_response(db_session: AsyncSession) -> None:
    """Test adding admin response to a message."""
    # Create an admin user
    admin_user = await UserOperations.create_user(
        db=db_session,
        email="admin@example.com",
        password="securepass123",
        full_name="Admin User",
    )
    admin_user.is_admin = True
    await db_session.flush()

    # Create a contact message
    message = await ContactOperations.create_message(
        db=db_session,
        name="Customer",
        email="customer@example.com",
        subject="Inquiry",
        message="I need help with my account.",
    )

    # Add admin response
    success = await ContactOperations.add_admin_response(
        db=db_session,
        message_id=message.message_id,
        admin_user_id=admin_user.user_id,
        admin_response="Thank you for contacting us. Here's the help you need...",
    )
    assert success is True

    # Verify the response was added
    updated_message = await ContactOperations.get_message_by_id(
        db_session, message.message_id
    )
    assert updated_message is not None
    assert updated_message.status == ContactStatus.RESPONDED
    assert (
        updated_message.admin_response
        == "Thank you for contacting us. Here's the help you need..."
    )
    assert updated_message.responded_by == admin_user.user_id
    assert isinstance(updated_message.responded_at, datetime)
    assert updated_message.responded_at.tzinfo is not None

    # Test responding to non-existent message
    success = await ContactOperations.add_admin_response(
        db_session,
        message_id="msg_nonexistent",
        admin_user_id=admin_user.user_id,
        admin_response="Response",
    )
    assert success is False


@pytest.mark.asyncio
async def test_get_unread_count(db_session: AsyncSession) -> None:
    """Test getting count of unread messages."""
    # Initially should be 0
    count = await ContactOperations.get_unread_count(db_session)
    assert count == 0

    # Create some messages
    for i in range(3):
        await ContactOperations.create_message(
            db=db_session,
            name=f"User {i}",
            email=f"user{i}@example.com",
            subject=f"Subject {i}",
            message=f"Message {i}",
        )

    # All should be unread
    count = await ContactOperations.get_unread_count(db_session)
    assert count == 3

    # Mark one as read
    messages, _ = await ContactOperations.get_messages(db_session, limit=1)
    await ContactOperations.update_message_status(
        db_session, messages[0].message_id, ContactStatus.READ
    )

    # Should now be 2 unread
    count = await ContactOperations.get_unread_count(db_session)
    assert count == 2
