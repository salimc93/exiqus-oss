"""
Tests for contact form API endpoints.
"""

from typing import Any, AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from github_analyzer.api.auth.dependencies import (
    get_current_user_id,
    get_current_user_id_optional,
    require_admin,
)
from github_analyzer.database.connection import get_db_session
from github_analyzer.database.models import User
from github_analyzer.database.operations import ContactOperations
from tests.conftest import create_test_app


class TestContactRoutes:
    """Test suite for contact form API routes."""

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

        # Mock admin authentication
        async def override_require_admin() -> str:
            return "admin_usr_test123"

        app.dependency_overrides[require_admin] = override_require_admin

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
    async def admin_user_id(self, test_db: Any) -> str:
        """Create the admin user and return its ID."""
        async with test_db() as session:
            session.add(
                User(
                    user_id="admin_usr_test123",
                    email="admin_usr_test123@example.com",
                    password_hash="hashed",
                    full_name="Admin User",
                    is_admin=True,
                    is_active=True,
                )
            )
            await session.commit()
        return "admin_usr_test123"

    @pytest.fixture
    async def authenticated_client(
        self, test_db: Any
    ) -> AsyncGenerator[AsyncClient, None]:
        """Create async test client with regular user authentication."""
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

        # The mocked user must actually exist - Postgres enforces FKs
        async with session_maker() as session:
            session.add(
                User(
                    user_id="usr_test123",
                    email="usr_test123@example.com",
                    password_hash="hashed",
                    full_name="Test User",
                    is_active=True,
                )
            )
            await session.commit()

        # Mock authentication
        async def override_get_current_user_id() -> str:
            return "usr_test123"

        app.dependency_overrides[get_current_user_id] = override_get_current_user_id
        app.dependency_overrides[get_current_user_id_optional] = (
            override_get_current_user_id
        )

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

    async def test_submit_contact_form(self, client: AsyncClient) -> None:
        """Test submitting a contact form."""
        # Submit a contact form
        response = await client.post(
            "/api/v1/contact",
            json={
                "name": "Test User",
                "email": "test@example.com",
                "subject": "Test Subject",
                "message": "This is a test message that is long enough to pass validation.",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "message_id" in data
        assert data["message_id"].startswith("msg_")
        assert (
            data["message"]
            == "Thank you for contacting us. We'll respond as soon as possible."
        )
        assert "timestamp" in data

    async def test_submit_contact_form_validation(self, client: AsyncClient) -> None:
        """Test contact form validation."""
        # Test missing fields
        response = await client.post(
            "/api/v1/contact",
            json={
                "name": "Test User",
                "email": "test@example.com",
                "subject": "Test",
                # Missing message
            },
        )
        assert response.status_code == 422

        # Test invalid email
        response = await client.post(
            "/api/v1/contact",
            json={
                "name": "Test User",
                "email": "invalid-email",
                "subject": "Test Subject",
                "message": "This is a test message.",
            },
        )
        assert response.status_code == 422

        # Test message too short
        response = await client.post(
            "/api/v1/contact",
            json={
                "name": "Test User",
                "email": "test@example.com",
                "subject": "Test Subject",
                "message": "Too short",  # Less than 10 characters
            },
        )
        assert response.status_code == 422

        # Test empty name
        response = await client.post(
            "/api/v1/contact",
            json={
                "name": "",
                "email": "test@example.com",
                "subject": "Test Subject",
                "message": "This is a valid test message.",
            },
        )
        assert response.status_code == 422

    async def test_contact_form_rate_limiting(self, client: AsyncClient) -> None:
        """Test rate limiting on contact form submissions."""
        # The rate limit is 5 per hour per IP
        # Submit 5 forms (should all succeed)
        for i in range(5):
            response = await client.post(
                "/api/v1/contact",
                json={
                    "name": f"User {i}",
                    "email": f"user{i}@example.com",
                    "subject": f"Subject {i}",
                    "message": f"This is test message number {i} with enough content.",
                },
            )
            assert response.status_code == 200

        # The 6th submission should be rate limited
        response = await client.post(
            "/api/v1/contact",
            json={
                "name": "Rate Limited User",
                "email": "ratelimited@example.com",
                "subject": "Should be blocked",
                "message": "This submission should be rate limited.",
            },
        )

        # Middleware now returns JSONResponse with 429 instead of raising HTTPException
        assert response.status_code == 429
        body = response.json()
        assert body["error"] == "Rate limit exceeded"

    async def test_submit_contact_form_as_authenticated_user(
        self, authenticated_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test submitting a contact form as an authenticated user."""
        # Submit a contact form
        response = await authenticated_client.post(
            "/api/v1/contact",
            json={
                "name": "Authenticated User",
                "email": "auth@example.com",
                "subject": "Authenticated Subject",
                "message": "This is a test message from an authenticated user.",
            },
        )

        assert response.status_code == 200
        data = response.json()
        message_id = data["message_id"]

        # Verify message is associated with user
        message = await ContactOperations.get_message_by_id(db_session, message_id)
        assert message is not None
        assert message.user_id == "usr_test123"  # The test user ID

    async def test_get_my_messages_authenticated(
        self, authenticated_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test getting user's own messages."""
        # Create messages for the test user
        user_id = "usr_test123"
        for i in range(3):
            await ContactOperations.create_message(
                db=db_session,
                name=f"User {i}",
                email=f"user{i}@example.com",
                subject=f"Subject {i}",
                message=f"Message content {i}",
                user_id=user_id,
            )

        # Create a message for another user
        await ContactOperations.create_message(
            db=db_session,
            name="Other User",
            email="other@example.com",
            subject="Other Subject",
            message="Other message",
            user_id=None,
        )

        # Get messages
        response = await authenticated_client.get("/api/v1/contact/my-messages")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 3  # Only user's messages
        assert len(data["messages"]) == 3
        # Verify all messages belong to the user
        for msg in data["messages"]:
            assert msg["email"] in [
                "user0@example.com",
                "user1@example.com",
                "user2@example.com",
            ]

    async def test_get_my_messages_unauthenticated(self, client: AsyncClient) -> None:
        """Test that unauthenticated users cannot access my-messages endpoint."""
        response = await client.get("/api/v1/contact/my-messages")
        assert response.status_code == 401
        assert "Authentication required" in response.json()["detail"]

    async def test_get_my_messages_with_admin_response(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        admin_user_id: str,
    ) -> None:
        """Test getting messages that have admin responses."""
        user_id = "usr_test123"

        # Create a message with admin response
        message = await ContactOperations.create_message(
            db=db_session,
            name="Test User",
            email="test@example.com",
            subject="Need Help",
            message="I need help with my account",
            user_id=user_id,
        )

        # Add admin response
        await ContactOperations.add_admin_response(
            db=db_session,
            message_id=message.message_id,
            admin_user_id=admin_user_id,
            admin_response="Here's the help you requested...",
        )
        await db_session.commit()

        # Get messages
        response = await authenticated_client.get("/api/v1/contact/my-messages")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 1
        msg = data["messages"][0]
        assert msg["status"] == "responded"
        assert msg["admin_response"] == "Here's the help you requested..."
        assert msg["responded_by"] == admin_user_id
        assert msg["responded_at"] is not None
