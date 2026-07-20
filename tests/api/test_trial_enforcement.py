"""Tests for trial enforcement middleware."""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException, Request, Response
from sqlalchemy import select

from github_analyzer.api.middleware.trial_enforcement import (
    TrialEnforcementMiddleware,
)
from github_analyzer.database.models import AuditLog, BillingUsageRecord, User


@pytest.fixture
def mock_app():
    """Create a mock FastAPI app for testing."""
    app = FastAPI()

    @app.post("/api/v1/analyze")
    async def analyze():
        return {"result": "success"}

    @app.post("/api/v1/batch")
    async def batch():
        return {"results": ["success1", "success2"]}

    @app.get("/api/v1/health")
    async def health():
        return {"status": "ok"}

    return app


@pytest.fixture
def middleware(mock_app):
    """Create middleware instance."""
    return TrialEnforcementMiddleware(mock_app)


@pytest.mark.asyncio
async def test_non_protected_endpoint_bypassed(middleware):
    """Test that non-protected endpoints are not checked."""
    # Create mock request for health endpoint
    request = MagicMock(spec=Request)
    request.url.path = "/api/v1/health"

    # Mock call_next
    async def call_next(req):
        return Response(content="OK", status_code=200)

    # Should pass through without any checks
    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_no_authentication_bypassed(middleware):
    """Test that requests without authentication are bypassed."""
    request = MagicMock(spec=Request)
    request.url.path = "/api/v1/analyze"
    request.headers = {}

    async def call_next(req):
        return Response(content="OK", status_code=200)

    with patch.object(middleware, "_get_user_id_from_request", return_value=None):
        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_non_trial_user_bypassed(middleware, test_db):
    """Test that non-trial users are not limited."""
    # Create non-trial user
    async with test_db() as db:
        user = User(
            user_id="regular123",
            email="regular@example.com",
            password_hash="hashed",
            full_name="Regular User",
            is_trial=False,
            is_active=True,
        )
        db.add(user)
        await db.commit()

    request = MagicMock(spec=Request)
    request.url.path = "/api/v1/analyze"
    request.state = MagicMock()

    async def call_next(req):
        return Response(content="OK", status_code=200)

    async def mock_get_db_session():
        async with test_db() as db:
            yield db

    with patch.object(
        middleware, "_get_user_id_from_request", return_value="regular123"
    ):
        with patch(
            "github_analyzer.api.middleware.trial_enforcement.get_db_session",
            mock_get_db_session,
        ):
            response = await middleware.dispatch(request, call_next)
            assert response.status_code == 200


@pytest.mark.asyncio
async def test_trial_expired_blocked(middleware, test_db):
    """Test that expired trial users are blocked."""
    # Create expired trial user
    async with test_db() as db:
        user = User(
            user_id="trial123",
            email="trial@example.com",
            password_hash="hashed",
            full_name="Trial User",
            is_trial=True,
            trial_plan="BASIC",
            trial_end_date=datetime.now(timezone.utc) - timedelta(days=1),  # Expired
            is_active=True,
        )
        db.add(user)
        await db.commit()

    request = MagicMock(spec=Request)
    request.url.path = "/api/v1/analyze"

    async def call_next(req):
        return Response(content="OK", status_code=200)

    async def mock_get_db_session():
        async with test_db() as db:
            yield db

    with patch.object(middleware, "_get_user_id_from_request", return_value="trial123"):
        with patch(
            "github_analyzer.api.middleware.trial_enforcement.get_db_session",
            mock_get_db_session,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await middleware.dispatch(request, call_next)
            assert exc_info.value.status_code == 403
            assert "Trial period has expired" in exc_info.value.detail


@pytest.mark.asyncio
async def test_trial_limit_exceeded_blocked(middleware, test_db):
    """Test that users exceeding their limit are blocked."""
    # Create trial user at limit
    async with test_db() as db:
        user = User(
            user_id="trial123",
            email="trial@example.com",
            password_hash="hashed",
            full_name="Trial User",
            is_trial=True,
            trial_plan="BASIC",
            trial_analyses_limit=100,
            analyses_consumed=100,  # At limit
            trial_end_date=datetime.now(timezone.utc) + timedelta(days=7),
            is_active=True,
        )
        db.add(user)
        await db.commit()

    request = MagicMock(spec=Request)
    request.url.path = "/api/v1/analyze"

    async def call_next(req):
        return Response(content="OK", status_code=200)

    async def mock_get_db_session():
        async with test_db() as db:
            yield db

    with patch.object(middleware, "_get_user_id_from_request", return_value="trial123"):
        with patch(
            "github_analyzer.api.middleware.trial_enforcement.get_db_session",
            mock_get_db_session,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await middleware.dispatch(request, call_next)
            assert exc_info.value.status_code == 429
            assert "Trial limit reached" in exc_info.value.detail


@pytest.mark.asyncio
async def test_trial_unlimited_allowed(middleware, test_db):
    """Test that users with unlimited plans are not blocked."""
    # Create trial user with unlimited plan
    async with test_db() as db:
        user = User(
            user_id="trial123",
            email="trial@example.com",
            password_hash="hashed",
            full_name="Trial User",
            is_trial=True,
            trial_plan="ENTERPRISE",
            trial_analyses_limit=None,  # Unlimited
            analyses_consumed=1000,  # High usage but unlimited
            trial_end_date=datetime.now(timezone.utc) + timedelta(days=7),
            is_active=True,
        )
        db.add(user)
        await db.commit()

    request = MagicMock(spec=Request)
    request.url.path = "/api/v1/analyze"
    request.state = MagicMock()

    async def call_next(req):
        return Response(content="OK", status_code=200)

    async def mock_get_db_session():
        async with test_db() as db:
            yield db

    with patch.object(middleware, "_get_user_id_from_request", return_value="trial123"):
        with patch(
            "github_analyzer.api.middleware.trial_enforcement.get_db_session",
            mock_get_db_session,
        ):
            response = await middleware.dispatch(request, call_next)
            assert response.status_code == 200


@pytest.mark.asyncio
async def test_usage_incremented_on_success(middleware, test_db):
    """Test that usage is incremented after successful analysis."""
    # Create trial user with available quota
    async with test_db() as db:
        user = User(
            user_id="trial123",
            email="trial@example.com",
            password_hash="hashed",
            full_name="Trial User",
            is_trial=True,
            trial_plan="BASIC",
            trial_analyses_limit=100,
            analyses_consumed=50,  # Half used
            trial_end_date=datetime.now(timezone.utc) + timedelta(days=7),
            is_active=True,
        )
        db.add(user)
        await db.commit()

    request = MagicMock(spec=Request)
    request.url.path = "/api/v1/analyze"
    request.state = MagicMock()
    request.body = AsyncMock(return_value=b"{}")

    async def call_next(req):
        return Response(content="OK", status_code=200)

    async def mock_get_db_session():
        async with test_db() as db:
            yield db

    with patch.object(middleware, "_get_user_id_from_request", return_value="trial123"):
        with patch(
            "github_analyzer.api.middleware.trial_enforcement.get_db_session",
            mock_get_db_session,
        ):
            with patch.object(middleware, "_increment_usage") as mock_increment:
                response = await middleware.dispatch(request, call_next)
                assert response.status_code == 200
                mock_increment.assert_called_once_with("trial123", request)


@pytest.mark.asyncio
async def test_usage_not_incremented_on_failure(middleware, test_db):
    """Test that usage is not incremented on failed requests."""
    # Create trial user
    async with test_db() as db:
        user = User(
            user_id="trial123",
            email="trial@example.com",
            password_hash="hashed",
            full_name="Trial User",
            is_trial=True,
            trial_plan="BASIC",
            trial_analyses_limit=100,
            analyses_consumed=50,
            trial_end_date=datetime.now(timezone.utc) + timedelta(days=7),
            is_active=True,
        )
        db.add(user)
        await db.commit()

    request = MagicMock(spec=Request)
    request.url.path = "/api/v1/analyze"
    request.state = MagicMock()

    async def call_next(req):
        return Response(content="Error", status_code=400)

    async def mock_get_db_session():
        async with test_db() as db:
            yield db

    with patch.object(middleware, "_get_user_id_from_request", return_value="trial123"):
        with patch(
            "github_analyzer.api.middleware.trial_enforcement.get_db_session",
            mock_get_db_session,
        ):
            with patch.object(middleware, "_increment_usage") as mock_increment:
                response = await middleware.dispatch(request, call_next)
                assert response.status_code == 400
                mock_increment.assert_not_called()


@pytest.mark.asyncio
async def test_batch_usage_counted_correctly(middleware, test_db):
    """Test that batch requests count multiple analyses."""
    # Create trial user
    async with test_db() as db:
        user = User(
            user_id="trial123",
            email="trial@example.com",
            password_hash="hashed",
            full_name="Trial User",
            is_trial=True,
            trial_plan="BASIC",
            trial_analyses_limit=100,
            analyses_consumed=50,
            trial_end_date=datetime.now(timezone.utc) + timedelta(days=7),
            is_active=True,
        )
        db.add(user)
        await db.commit()

    # Test increment_usage directly with batch request
    request = MagicMock(spec=Request)
    request.url.path = "/api/v1/batch"
    request.body = AsyncMock(
        return_value=json.dumps(
            {
                "repository_urls": [
                    "https://github.com/user/repo1",
                    "https://github.com/user/repo2",
                    "https://github.com/user/repo3",
                ]
            }
        ).encode()
    )

    async def mock_get_db_session():
        async with test_db() as db:
            yield db

    with patch(
        "github_analyzer.api.middleware.trial_enforcement.get_db_session",
        mock_get_db_session,
    ):
        await middleware._increment_usage("trial123", request)

    # Verify usage was incremented by 3
    async with test_db() as db:
        result = await db.execute(select(User).where(User.user_id == "trial123"))
        user = result.scalar_one()
        assert user.analyses_consumed == 53  # 50 + 3

        # Verify billing record created
        result = await db.execute(
            select(BillingUsageRecord)
            .where(BillingUsageRecord.user_id == "trial123")
            .where(BillingUsageRecord.usage_type == "trial_analysis")
        )
        usage_record = result.scalar_one()
        assert usage_record.usage_count == 3

        # Verify audit log created
        result = await db.execute(
            select(AuditLog)
            .where(AuditLog.action == "trial_usage_incremented")
            .where(AuditLog.target_user_id == "trial123")
        )
        audit = result.scalar_one()
        metadata = json.loads(audit.action_metadata)
        assert metadata["analyses_count"] == 3
        assert metadata["total_consumed"] == 53
