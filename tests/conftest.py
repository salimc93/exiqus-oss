"""
Shared test configuration and fixtures.

This module provides common pytest fixtures and test utilities
for the Exiqus API test suite.
"""

import os
import secrets
from typing import Any, AsyncGenerator, Dict, Generator, List, Optional

# Set up test environment variables before any imports
os.environ["TESTING"] = "true"  # Enable test mode for JWT key generation
os.environ["JWT_SECRET_KEY"] = secrets.token_urlsafe(32)  # Legacy (now using RS256)
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-api03-test-key"
# Pin the model so a developer's .env cannot change what the suite asserts.
# The model is deployment-configurable, so without this the same test can pass
# on one machine and fail on another.
os.environ["ANTHROPIC_MODEL"] = "claude-opus-4-8"
os.environ["GITHUB_TOKEN"] = "ghp_test_token_1234567890123456789012345678"
# Tests never use the global engine (fixtures override it), but the URL must
# be a valid Postgres one regardless of what a local .env contains.
os.environ["DATABASE_URL"] = (
    "postgresql://github_analyzer:exiqus_dev_password@localhost:5432/github_analyzer"
)

from unittest.mock import AsyncMock, Mock, patch  # noqa: E402

import pytest  # noqa: E402
from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import Engine, create_engine, text  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool  # noqa: E402

from github_analyzer.api.routes import (  # noqa: E402
    analysis,
    analytics,
    api_keys,
    auth,
    batch_history,
    billing,
    billing_admin,
    budget,
    consent,
    contact,
    email_verification,
    health,
    priority_support,
    quota,
    scheduler,
    training_data,
    trial_activation,
    trial_admin,
    trial_management,
    trial_status,
)
from github_analyzer.database.connection import Base, get_db_session  # noqa: E402


class MockRedisService:
    """Mock Redis service for testing."""

    def __init__(self) -> None:
        self._cache: Dict[str, Any] = {}
        self._rate_limits: Dict[str, int] = {}
        self._connected = True  # Mock is always "connected"
        self._redis = self  # Self-reference for compatibility

    async def get(self, key: str) -> Optional[str]:
        """Mock get method."""
        # For rate limit keys, check _rate_limits first
        if key.startswith("rate_limit:"):
            value = self._rate_limits.get(key)
            return str(value) if value is not None else None
        return self._cache.get(key)

    async def set(self, key: str, value: str, expire: Optional[int] = None) -> None:
        """Mock set method."""
        # For rate limit keys, store in _rate_limits
        if key.startswith("rate_limit:"):
            self._rate_limits[key] = int(value)
        else:
            self._cache[key] = value

    async def delete(self, key: str) -> None:
        """Mock delete method."""
        self._cache.pop(key, None)

    async def clear(self) -> None:
        """Mock clear method."""
        self._cache.clear()
        self._rate_limits.clear()

    async def increment_rate_limit(
        self, key: str, window_seconds: int = 60, limit: int = 60
    ) -> tuple[int, bool]:
        """Mock increment rate limit method."""
        current_count = self._rate_limits.get(key, 0) + 1
        self._rate_limits[key] = current_count
        is_allowed = current_count <= limit
        return current_count, is_allowed

    async def connect(self) -> None:
        """Mock connect method."""
        pass  # Already "connected"

    async def disconnect(self) -> None:
        """Mock disconnect method."""
        pass  # No-op for mock

    async def incr(self, key: str, expire: Optional[int] = None) -> int:
        """Mock incr method."""
        current = self._rate_limits.get(key, 0)
        self._rate_limits[key] = current + 1
        return self._rate_limits[key]

    async def decr(self, key: str) -> int:
        """Mock decr method."""
        current = self._rate_limits.get(key, 0)
        self._rate_limits[key] = max(0, current - 1)
        return self._rate_limits[key]

    async def zadd(self, key: str, mapping: Dict[str, float]) -> int:
        """Mock zadd method for sorted sets."""
        if key not in self._cache:
            self._cache[key] = {}
        self._cache[key].update(mapping)
        return len(mapping)

    async def zremrangebyscore(
        self, key: str, min_score: float, max_score: float
    ) -> int:
        """Mock zremrangebyscore method."""
        if key not in self._cache or not isinstance(self._cache[key], dict):
            return 0
        removed = 0
        to_remove = []
        for member, score in self._cache.get(key, {}).items():
            if min_score <= float(score) <= max_score:
                to_remove.append(member)
                removed += 1
        for member in to_remove:
            del self._cache[key][member]
        return removed

    async def zcount(self, key: str, min_score: float, max_score: float) -> int:
        """Mock zcount method for sorted sets."""
        if key not in self._cache or not isinstance(self._cache[key], dict):
            return 0
        count = 0
        for score in self._cache.get(key, {}).values():
            if min_score <= float(score) <= max_score:
                count += 1
        return count

    async def expire(self, key: str, seconds: int) -> bool:
        """Mock expire method."""
        # Just return True for simplicity
        return True

    async def setex(self, key: str, seconds: int, value: str) -> bool:
        """Mock setex method - set with expiration."""
        self._cache[key] = value
        return True

    async def incrbyfloat(self, key: str, amount: float) -> float:
        """Mock incrbyfloat method."""
        current = float(self._cache.get(key, 0))
        new_value = current + amount
        self._cache[key] = str(new_value)
        return new_value

    def pipeline(self) -> "MockRedisPipeline":
        """Mock pipeline method."""
        return MockRedisPipeline(self)


class MockRedisPipeline:
    """Mock Redis pipeline for testing."""

    def __init__(self, mock_redis: MockRedisService) -> None:
        self.mock_redis = mock_redis
        self.commands: List[Any] = []

    async def __aenter__(self) -> "MockRedisPipeline":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass

    async def incr(self, key: str) -> None:
        """Mock incr command."""
        self.commands.append(("incr", key))

    async def expire(self, key: str, seconds: int) -> None:
        """Mock expire command."""
        self.commands.append(("expire", key, seconds))

    async def execute(self) -> List[Any]:
        """Execute pipeline commands."""
        results = []
        for cmd in self.commands:
            if cmd[0] == "incr":
                key = cmd[1]
                current = self.mock_redis._rate_limits.get(key, 0) + 1
                self.mock_redis._rate_limits[key] = current
                results.append(current)
            elif cmd[0] == "expire":
                results.append(True)
        return results


def create_test_app() -> FastAPI:
    """
    Create a test-specific FastAPI application with test-appropriate middleware.

    This includes rate limiting middleware with mock Redis for proper testing.

    Returns:
        FastAPI: Test application instance
    """
    # Import rate limiting middleware
    from github_analyzer.api.middleware.rate_limiting import RateLimitingMiddleware

    # Create app with debug mode for better error handling
    app = FastAPI(
        title="Exiqus API Test",
        description="Test application with rate limiting for testing",
        version="1.0.0",
        debug=True,
    )

    # Add minimal CORS middleware for tests
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add rate limiting middleware with test configuration
    app.add_middleware(
        RateLimitingMiddleware,
        requests_per_minute=60,
        burst_requests_per_minute=120,
        analysis_requests_per_hour=10,
        contact_requests_per_hour=5,  # This is what we test
        registration_requests_per_hour=5,
        registration_requests_per_day=10,
    )

    # Add exception handler for HTTPException to ensure proper error responses
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Any, exc: HTTPException) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    # Mount routes
    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(analysis.router, prefix="/api/v1", tags=["analysis"])
    app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
    app.include_router(
        email_verification.router, prefix="/api/v1", tags=["authentication"]
    )
    app.include_router(api_keys.router)  # API key router already has prefix

    # Import and include admin routes
    from github_analyzer.api.routes import admin_auth, admin_management

    app.include_router(
        admin_auth.router, prefix="/api/v1", tags=["admin_authentication"]
    )
    app.include_router(
        admin_management.router, prefix="/api/v1", tags=["admin_management"]
    )

    app.include_router(analytics.router, prefix="/api/v1", tags=["analytics"])
    app.include_router(billing.router, prefix="/api/v1", tags=["billing"])
    app.include_router(billing_admin.router, prefix="/api/v1", tags=["billing_admin"])
    app.include_router(budget.router, prefix="/api/v1", tags=["budget"])
    app.include_router(consent.router, prefix="/api/v1", tags=["consent"])
    app.include_router(contact.router, prefix="/api/v1", tags=["contact"])
    app.include_router(training_data.router, prefix="/api/v1", tags=["training_data"])
    app.include_router(trial_admin.router, prefix="/api/v1", tags=["trial_admin"])
    app.include_router(
        trial_activation.router, prefix="/api/v1", tags=["trial_activation"]
    )
    app.include_router(
        trial_management.router, prefix="/api/v1", tags=["trial_management"]
    )
    app.include_router(trial_status.router, prefix="/api/v1", tags=["trial_status"])
    app.include_router(quota.router, prefix="/api/v1", tags=["quota"])
    app.include_router(batch_history.router)  # Batch history router already has prefix
    app.include_router(
        priority_support.router
    )  # Priority support router already has prefix
    app.include_router(scheduler.router)  # Scheduler router already has prefix

    return app


@pytest.fixture(scope="session")
def test_pg_url() -> Generator[str, None, None]:
    """Sync SQLAlchemy URL for the test Postgres database.

    Uses TEST_DATABASE_URL if set (e.g. a CI service container);
    otherwise starts a throwaway Postgres via testcontainers, so the
    only local requirement is a running Docker daemon.
    """
    external = os.getenv("TEST_DATABASE_URL")
    if external:
        yield external.replace("+asyncpg", "").replace("+psycopg2", "")
        return

    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg.get_connection_url().replace("+psycopg2", "")


@pytest.fixture(scope="session")
def test_pg_sync_engine(test_pg_url: str) -> Generator[Engine, None, None]:
    """Session-scoped sync engine; creates the schema once."""
    # Import all models so they register on Base.metadata
    from github_analyzer.database import models  # noqa: F401

    engine = create_engine(test_pg_url)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
async def test_db(
    test_pg_url: str, test_pg_sync_engine: Engine
) -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    """Create a test database engine and session factory.

    Each test gets its own async engine (NullPool keeps connections
    tied to the test's event loop); the shared database is wiped with
    TRUNCATE after every test for isolation.
    """
    async_url = test_pg_url.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(async_url, echo=False, future=True, poolclass=NullPool)

    async_session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # Return the session factory, not the session itself
    yield async_session_maker

    # Cleanup: drop this test's connections, then wipe all data
    await engine.dispose()
    table_names = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    with test_pg_sync_engine.begin() as conn:
        # A test that leaks an open session would block TRUNCATE forever;
        # this is a throwaway database, so terminate any stragglers first.
        conn.execute(
            text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = current_database() AND pid <> pg_backend_pid()"
            )
        )
        conn.execute(text(f"TRUNCATE {table_names} RESTART IDENTITY CASCADE"))


@pytest.fixture(scope="function")
async def async_client(
    test_db: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[Any, None]:
    """Create async test client with database override."""
    from github_analyzer.api.dependencies import get_redis_service
    from github_analyzer.api.services.redis_service import redis_service

    # Mock scheduler service to avoid startup issues
    with patch(
        "github_analyzer.api.services.scheduler_service.get_scheduler_service"
    ) as mock_get_scheduler:
        # Create a mock scheduler that mimics the expected interface
        mock_scheduler = Mock()
        mock_scheduler.set_session_factory = Mock()
        mock_scheduler.start = AsyncMock()
        mock_scheduler.stop = AsyncMock()
        mock_scheduler.add_job = Mock()
        mock_scheduler.get_job_status = Mock(return_value="completed")
        mock_scheduler.running = True
        mock_scheduler.tasks = {}
        mock_get_scheduler.return_value = mock_scheduler

        app = create_test_app()

        # Get the session maker directly (test_db yields it, not an async generator)
        session_maker = test_db

        # Override database dependency to use test session factory
        async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
            async with session_maker() as session:
                yield session

        app.dependency_overrides[get_db_session] = override_get_db

        # Override Redis service with mock
        mock_redis = MockRedisService()

        def override_get_redis():
            return mock_redis

        app.dependency_overrides[get_redis_service] = override_get_redis

        # The scheduler service is now mocked at the test module level
        # where it is used, to avoid pathing and import order issues.

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
            # Attach app to client for test access
            client.app = app  # type: ignore[attr-defined]
            yield client

        # Restore original methods and state
        redis_service.increment_rate_limit = original_increment
        redis_service._connected = original_connected
        redis_service._redis = original_redis

        # Clear overrides
        app.dependency_overrides.clear()


@pytest.fixture
def test_app() -> FastAPI:
    """Fixture providing test FastAPI app."""
    return create_test_app()


@pytest.fixture
def mock_redis_service() -> MockRedisService:
    """Fixture providing mock Redis service."""
    return MockRedisService()


def override_get_db_session(test_db_session: AsyncSession) -> Any:
    """Override database session for testing."""

    # This is used by auth integration tests
    async def get_test_db() -> AsyncGenerator[AsyncSession, None]:
        # Return the provided test database session
        yield test_db_session

    return get_test_db


def create_mock_anthropic_response(
    content: str = "Test response",
    verdict: Optional[str] = None,
    confidence: Optional[int] = None,
    summary: Optional[str] = None,
) -> Mock:
    """Create a mock Anthropic API response for testing."""
    # This is used by AI analyzer tests
    # If verdict, confidence, or summary provided, create structured JSON content
    if verdict or confidence or summary:
        json_content = {
            "verdict": verdict or "HIRE",
            "confidence": confidence or 85,
            "summary": summary or "Great repository",
            "strengths": ["Good tests", "Well structured"],
            "concerns": ["Minor issues"],
        }
        content = str(json_content).replace("'", '"')

    # Create mock response object with proper structure
    mock_response = Mock()
    mock_response.content = [Mock()]
    mock_response.content[0].text = content
    mock_response.model = "claude-3-haiku-20240307"
    mock_response.usage = Mock()
    mock_response.usage.input_tokens = 1000  # Match test expectations
    mock_response.usage.output_tokens = 500  # Match test expectations

    return mock_response


@pytest.fixture
def isolated_cost_tracker() -> Any:
    """Create isolated cost tracker for testing."""
    from github_analyzer.ai.cost_tracker import CostTracker

    # Create cost tracker with no persistent storage for isolation
    tracker = CostTracker(storage=None)
    # Clear any existing usage history for true isolation
    tracker.usage_history = []
    # Ensure persistence is disabled
    tracker.persistence_enabled = False
    tracker.cost_storage = None
    return tracker


@pytest.fixture
def mock_get_config_new() -> Any:
    """Mock config for new-style tests."""
    from unittest.mock import Mock, patch

    mock_config = Mock()
    mock_config.github_token = "test_token"
    mock_config.anthropic_api_key = "test_key"
    mock_config.anthropic_model = "claude-3-haiku-20240307"
    mock_config.max_daily_cost = 10.0
    mock_config.enable_cost_tracking = True
    mock_config.storage.enabled = False

    with patch("github_analyzer.utils.config.get_config", return_value=mock_config):
        yield mock_config


@pytest.fixture(scope="function")
async def db_session(
    test_db: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """Create a database session for tests."""
    async with test_db() as session:
        yield session
