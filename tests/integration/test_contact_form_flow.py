"""
Integration tests for the complete contact form flow.
"""

from typing import Any, AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from github_analyzer.api.auth.dependencies import get_admin_user_from_token
from github_analyzer.database.connection import get_db_session
from github_analyzer.database.models import ContactStatus
from github_analyzer.database.operations import ContactOperations
from tests.conftest import create_test_app


class TestContactFormFlow:
    """Test suite for contact form integration flows."""

    @pytest.fixture
    async def client(self, test_db: Any) -> AsyncGenerator[AsyncClient, None]:
        """Create async test client."""
        from github_analyzer.api.dependencies import get_redis_service
        from github_analyzer.api.services.redis_service import redis_service
        from tests.conftest import MockRedisService

        app = create_test_app()
        session_maker = test_db

        # Override database dependency
        async def override_get_db() -> AsyncGenerator[Any, None]:
            async with session_maker() as session:
                yield session

        app.dependency_overrides[get_db_session] = override_get_db

        # Override Redis service with mock
        mock_redis = MockRedisService()

        def override_get_redis():
            return mock_redis

        app.dependency_overrides[get_redis_service] = override_get_redis

        # Monkey-patch the global redis_service to use mock
        original_increment = redis_service.increment_rate_limit
        original_connected = redis_service._connected
        original_redis = redis_service._redis

        redis_service.increment_rate_limit = mock_redis.increment_rate_limit
        redis_service._connected = True
        redis_service._redis = mock_redis

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",  # type: ignore[arg-type]
        ) as client:
            yield client

        # Restore original methods and state
        redis_service.increment_rate_limit = original_increment
        redis_service._connected = original_connected
        redis_service._redis = original_redis

    @pytest.fixture
    async def db_session(self, test_db: Any) -> AsyncGenerator[AsyncSession, None]:
        """Get database session for direct database operations."""
        async with test_db() as session:
            yield session

    @pytest.fixture
    async def admin_client(self, test_db: Any) -> AsyncGenerator[AsyncClient, None]:
        """Create async test client with admin authentication."""
        from github_analyzer.api.dependencies import get_redis_service
        from github_analyzer.api.services.redis_service import redis_service
        from tests.conftest import MockRedisService

        app = create_test_app()
        session_maker = test_db

        # Override database dependency
        async def override_get_db() -> AsyncGenerator[Any, None]:
            async with session_maker() as session:
                yield session

        app.dependency_overrides[get_db_session] = override_get_db

        # Mock admin authentication - create a mock admin user
        from github_analyzer.database.models import User

        mock_admin_user = User(
            user_id="admin_usr_test123",
            email="admin@test.com",
            password_hash="hashed",
            full_name="Test Admin",
            is_admin=True,
            is_active=True,
        )

        # Persist the admin user - Postgres enforces the responded_by FK
        async with session_maker() as session:
            session.add(mock_admin_user)
            await session.commit()

        async def override_get_admin_user() -> User:
            return mock_admin_user

        app.dependency_overrides[get_admin_user_from_token] = override_get_admin_user

        # Override Redis service with mock
        mock_redis = MockRedisService()

        def override_get_redis():
            return mock_redis

        app.dependency_overrides[get_redis_service] = override_get_redis

        # Monkey-patch the global redis_service to use mock
        original_increment = redis_service.increment_rate_limit
        original_connected = redis_service._connected
        original_redis = redis_service._redis

        redis_service.increment_rate_limit = mock_redis.increment_rate_limit
        redis_service._connected = True
        redis_service._redis = mock_redis

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",  # type: ignore[arg-type]
        ) as client:
            yield client

        # Restore original methods and state
        redis_service.increment_rate_limit = original_increment
        redis_service._connected = original_connected
        redis_service._redis = original_redis

    @pytest.fixture
    def admin_user_id(self) -> str:
        """Get admin user ID for tests."""
        return "admin_usr_test123"

    async def test_complete_contact_form_flow(
        self,
        client: AsyncClient,
        admin_client: AsyncClient,
        db_session: AsyncSession,
        admin_user_id: str,
    ) -> None:
        """Test the complete flow from submission to response."""
        # Step 1: User submits a contact form
        submit_response = await client.post(
            "/api/v1/contact",
            json={
                "name": "John Customer",
                "email": "john.customer@example.com",
                "subject": "Question about Enterprise Plan",
                "message": (
                    "I'm interested in the Enterprise Plan. Can you provide "
                    "more details about the features and pricing? "
                    "We have a team of 50 developers."
                ),
            },
        )
        assert submit_response.status_code == 200
        submit_data = submit_response.json()
        message_id = submit_data["message_id"]

        # Step 2: Verify message is in database as unread
        message = await ContactOperations.get_message_by_id(db_session, message_id)
        assert message is not None
        assert message.status == ContactStatus.UNREAD

        # Commit the session so it's visible to other sessions
        await db_session.commit()

        # Step 3: Admin views the dashboard
        dashboard_response = await admin_client.get("/api/v1/admin/dashboard")
        assert dashboard_response.status_code == 200
        dashboard_data = dashboard_response.json()
        # Dashboard doesn't have contact_stats, but we can verify it loads
        assert "total_users" in dashboard_data

        # Step 4: Admin lists support messages
        list_response = await admin_client.get("/api/v1/admin/support-messages")
        assert list_response.status_code == 200
        list_data = list_response.json()
        assert list_data["total_count"] == 1
        assert list_data["messages"][0]["id"] == message_id
        assert list_data["messages"][0]["status"] == "UNREAD"

        # Step 5: Admin marks message as read
        # Our implementation doesn't have a specific endpoint to view/mark as read
        # Instead, we'll update the status
        update_response = await admin_client.patch(
            f"/api/v1/admin/support-messages/{message_id}", json={"status": "READ"}
        )
        assert update_response.status_code == 200

        # Step 6: Verify message status changed
        list_response2 = await admin_client.get("/api/v1/admin/support-messages")
        assert list_response2.status_code == 200
        list_data2 = list_response2.json()
        # Find our message and check status
        our_msg = [m for m in list_data2["messages"] if m["id"] == message_id][0]
        assert our_msg["status"] == "READ"

        # Step 7: Admin responds to the message
        respond_response = await admin_client.post(
            f"/api/v1/admin/support-messages/{message_id}/reply",
            json={
                "reply": (
                    "Thank you for your interest in our Enterprise Plan! "
                    "Our Enterprise Plan includes unlimited repository analysis, "
                    "priority support, custom integrations, and dedicated account "
                    "management. For a team of 50 developers, the pricing would be "
                    "$2,500/month. I'd be happy to schedule a call to discuss your "
                    "specific needs. Please let me know your availability."
                )
            },
        )
        assert respond_response.status_code == 200
        respond_data = respond_response.json()
        assert respond_data["message"] == "Response sent successfully"

        # Step 8: Verify the complete message state
        # Verify in database
        await db_session.refresh(message)
        assert message.status == ContactStatus.RESPONDED
        assert message.admin_response is not None
        assert "Enterprise Plan includes" in message.admin_response
        assert (
            message.responded_by == "admin_usr_test123"
        )  # Now stores user_id, not email
        assert message.responded_at is not None

    async def test_multiple_messages_workflow(
        self,
        client: AsyncClient,
        admin_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test handling multiple contact messages with different statuses."""
        # Submit multiple contact forms
        message_ids = []
        for i in range(5):
            response = await client.post(
                "/api/v1/contact",
                json={
                    "name": f"Customer {i}",
                    "email": f"customer{i}@example.com",
                    "subject": f"Question {i}",
                    "message": f"This is question number {i} about your service offerings.",
                },
            )
            assert response.status_code == 200
            message_ids.append(response.json()["message_id"])

        # Check dashboard loads
        dashboard_response = await admin_client.get("/api/v1/admin/dashboard")
        assert dashboard_response.status_code == 200

        # Admin marks first two messages as read
        for i in range(2):
            response = await admin_client.patch(
                f"/api/v1/admin/support-messages/{message_ids[i]}",
                json={"status": "READ"},
            )
            assert response.status_code == 200

        # Respond to the first one
        response = await admin_client.post(
            f"/api/v1/admin/support-messages/{message_ids[0]}/reply",
            json={"reply": "Thank you for your inquiry. Here's your answer..."},
        )
        assert response.status_code == 200

        # Check status distribution
        messages, total = await ContactOperations.get_messages(db_session)
        assert total == 5

        # Count statuses
        status_counts = {
            ContactStatus.UNREAD: 0,
            ContactStatus.READ: 0,
            ContactStatus.RESPONDED: 0,
        }
        for msg in messages:
            status_counts[msg.status] += 1

        assert status_counts[ContactStatus.UNREAD] == 3
        assert status_counts[ContactStatus.READ] == 1
        assert status_counts[ContactStatus.RESPONDED] == 1

        # Test filtering by status
        unread_response = await admin_client.get(
            "/api/v1/admin/support-messages", params={"status": "UNREAD"}
        )
        assert unread_response.status_code == 200
        assert unread_response.json()["total_count"] == 3

        responded_response = await admin_client.get(
            "/api/v1/admin/support-messages", params={"status": "RESPONDED"}
        )
        assert responded_response.status_code == 200
        assert responded_response.json()["total_count"] == 1

    async def test_contact_form_spam_protection(self, client: AsyncClient) -> None:
        """Test that rate limiting protects against spam."""
        # Simulate rapid submissions from same IP
        for i in range(5):
            response = await client.post(
                "/api/v1/contact",
                json={
                    "name": f"Spammer {i}",
                    "email": f"spam{i}@example.com",
                    "subject": "Spam Subject",
                    "message": "This is a spam message attempting to flood the system.",
                },
            )
            assert response.status_code == 200

        # The next 5 should be rate limited
        for i in range(5):
            response = await client.post(
                "/api/v1/contact",
                json={
                    "name": f"Spammer {i + 5}",
                    "email": f"spam{i + 5}@example.com",
                    "subject": "Spam Subject",
                    "message": "This is a spam message attempting to flood the system.",
                },
            )
            # Middleware now returns JSONResponse with 429 instead of raising HTTPException
            assert response.status_code == 429
            body = response.json()
            assert body["error"] == "Rate limit exceeded"
