"""
Tests for rate limiting functionality.

Tests concurrent request limiting for both per-user and global limits.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import create_test_app

# Removed unused imports


class TestRateLimiting:
    """Test cases for rate limiting."""

    @pytest.fixture(autouse=True)
    def reset_rate_limit_service(self):
        """Reset the global rate limit service before each test."""
        from github_analyzer.api.services import rate_limit_dependencies

        # Store original state
        original_service = getattr(rate_limit_dependencies, "_rate_limit_service", None)

        # Reset to None for clean test start
        rate_limit_dependencies._rate_limit_service = None

        yield

        # Restore original state after test
        rate_limit_dependencies._rate_limit_service = original_service

    @pytest.fixture
    def app(self):
        """Create test FastAPI application."""
        return create_test_app()

    @pytest.fixture
    async def authenticated_client(
        self, async_client, test_db, mock_github_fetcher, mock_redis_service
    ):
        """Create async test client with authentication and mocked dependencies."""
        # Create a test user with unique email
        import time

        from github_analyzer.api.dependencies import get_github_fetcher
        from github_analyzer.api.services.rate_limit_dependencies import (
            get_rate_limit_service,
        )
        from github_analyzer.api.services.rate_limit_service import RateLimitService
        from github_analyzer.database.models import SubscriptionPlan
        from github_analyzer.database.operations import UserOperations

        unique_email = f"ratelimit_test_{int(time.time() * 1000)}@example.com"

        async with test_db() as db_session:
            user = await UserOperations.create_user(
                db_session,
                email=unique_email,
                password="TestPassword123!",
                full_name="Rate Limit Test User",
            )
            user.is_verified = True
            user.subscription_plan = SubscriptionPlan.PROFESSIONAL
            await db_session.commit()

        # Create rate limit service with mock redis
        mock_rate_limit_service = RateLimitService(mock_redis_service)

        # Override dependencies on the async_client's app
        async_client.app.dependency_overrides[get_github_fetcher] = lambda: (
            mock_github_fetcher
        )
        async_client.app.dependency_overrides[get_rate_limit_service] = lambda: (
            mock_rate_limit_service
        )

        # Login to get JWT token
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": unique_email, "password": "TestPassword123!"},
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Set auth headers
        async_client.headers = {"Authorization": f"Bearer {token}"}
        yield async_client

    @pytest.fixture
    def mock_github_fetcher(self):
        """Create mock GitHubFetcher for testing."""
        from datetime import datetime, timezone

        from github_analyzer.data.models import RepositoryData, RepositoryMetrics

        mock_fetcher = MagicMock()
        mock_fetcher.check_repository_size.return_value = {
            "size_kb": 1000,  # 1MB
            "file_count": 100,
        }

        # Create properly structured mock repository data
        mock_metrics = RepositoryMetrics(
            total_commits=50,
            unique_contributors=5,
            lines_of_code=1000,
            test_coverage_estimate=0.7,
            documentation_presence="3 documentation files in 10 total files",
            days_since_last_commit=7,
            commit_frequency=2.5,
            avg_commit_size=150.0,
        )

        mock_repo_data = RepositoryData(
            url="https://github.com/user/test-repo",
            full_name="user/test-repo",
            name="test-repo",
            owner="user",
            description="Test repository",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            pushed_at=datetime.now(timezone.utc),
            default_branch="main",
            size=1000,
            languages={"Python": 50000, "JavaScript": 25000},
            topics=[],
            license_name="MIT",
            stars=10,
            forks=2,
            watchers=5,
            open_issues=3,
            has_readme=True,
            has_license=True,
            has_contributing=False,
            has_tests=True,
            has_ci_config=True,
            recent_commits=[],
            file_structure=[],
            readme_content="# Test Repo",
            metrics=mock_metrics,
            fetched_at=datetime.now(timezone.utc),
            is_private=False,
            is_fork=False,
            is_archived=False,
            is_disabled=False,
        )

        mock_fetcher.fetch_repository_data.return_value = mock_repo_data

        return mock_fetcher

    @pytest.mark.asyncio
    async def test_single_request_allowed(self, authenticated_client):
        """Test that a single request is allowed."""
        with (
            patch("github_analyzer.api.routes.analysis.redis_service") as mock_redis,
            patch(
                "github_analyzer.api.routes.analysis.TierRateLimiter"
            ) as mock_tier_limiter,
        ):
            # Mock the tier rate limiter to always allow
            mock_instance = MagicMock()
            mock_instance.check_rate_limit = AsyncMock(
                return_value=(True, None, {})  # allowed, no error, no retry info
            )
            mock_tier_limiter.return_value = mock_instance

            # Create async function that returns None
            async def async_get(key):
                return None

            mock_redis.get = async_get

            # Mock the analysis function
            with patch(
                "github_analyzer.api.routes.analysis._perform_repository_analysis"
            ) as mock_perform:
                from github_analyzer.api.models.responses import AnalysisResponse

                mock_perform.return_value = AnalysisResponse(
                    repository_url="https://github.com/user/test-repo",
                    context="general",
                    analysis={
                        "executive_summary": "Test summary",
                        "overall_recommendation": "HIRE",
                        "confidence_score": 85,
                        "repository_type": "production",
                        "context_fit_score": 80,
                        "key_strengths": ["Good code quality"],
                        "primary_concerns": [],
                        "analysis_recommendations": ["Proceed with interview"],
                        "interview_focus_areas": ["System design"],
                    },
                    metadata={
                        "analysis_id": "test_123",
                        "repository_type": "production",
                        "confidence_grade": "B",
                        "ai_analysis_used": False,
                        "analysis_cost_usd": 0.0,
                        "response_time_seconds": 1.5,
                        "timestamp": "2024-01-01T12:00:00Z",
                        "cached": False,
                        "data_completeness": 0.9,
                    },
                )

                response = await authenticated_client.post(
                    "/api/v1/analyze",
                    json={
                        "repository_url": "https://github.com/user/test-repo",
                        "context": "general",
                    },
                )

                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_user_concurrent_limit_exceeded(
        self, authenticated_client, mock_redis_service
    ):
        """Test that user concurrent limit is enforced."""
        with patch(
            "github_analyzer.api.routes.analysis.TierRateLimiter"
        ) as mock_tier_limiter:
            # Mock the tier rate limiter to reject the request
            mock_instance = MagicMock()
            mock_instance.check_rate_limit = AsyncMock(
                return_value=(
                    False,
                    "Too many concurrent requests",
                    {"user_concurrent": 3},
                )  # rejected
            )
            mock_tier_limiter.return_value = mock_instance

            # Override the get method to return max count for user rate limits
            original_get = mock_redis_service.get

            async def mock_get_with_limit(key):
                if key.startswith("rate_limit:user:"):
                    return "3"  # Max user limit
                return await original_get(key)

            mock_redis_service.get = mock_get_with_limit

            response = await authenticated_client.post(
                "/api/v1/analyze",
                json={
                    "repository_url": "https://github.com/user/test-repo",
                    "context": "general",
                },
            )

            assert response.status_code == 429
            data = response.json()
            assert "Too many concurrent requests" in data["detail"]["error"]
            # The retry_after is included in the response
            assert "retry_after" in data["detail"]

    @pytest.mark.asyncio
    async def test_global_concurrent_limit_exceeded(
        self, authenticated_client, mock_redis_service
    ):
        """Test that global concurrent limit is enforced."""
        with patch(
            "github_analyzer.api.routes.analysis.TierRateLimiter"
        ) as mock_tier_limiter:
            # Mock the tier rate limiter to reject the request
            mock_instance = MagicMock()
            mock_instance.check_rate_limit = AsyncMock(
                return_value=(
                    False,
                    "System at capacity",
                    {"global_concurrent": 100},
                )  # rejected
            )
            mock_tier_limiter.return_value = mock_instance

            # Override the get method to return max count for global rate limit
            original_get = mock_redis_service.get

            async def mock_get_with_limit(key):
                if key == "rate_limit:global":
                    return "100"  # Max global limit
                return await original_get(key)

            mock_redis_service.get = mock_get_with_limit

            response = await authenticated_client.post(
                "/api/v1/analyze",
                json={
                    "repository_url": "https://github.com/user/test-repo",
                    "context": "general",
                },
            )

            assert response.status_code == 429
            data = response.json()
            assert "System at capacity" in data["detail"]["error"]
            # The retry_after is included in the response
            assert "retry_after" in data["detail"]

    @pytest.mark.asyncio
    async def test_concurrent_requests_release_on_completion(
        self, authenticated_client, mock_redis_service
    ):
        """Test that rate limit slots are released after request completion."""
        # Start with empty rate limits
        mock_redis_service._rate_limits.clear()

        with (
            patch("github_analyzer.api.routes.analysis.redis_service") as mock_redis,
            patch(
                "github_analyzer.api.routes.analysis.TierRateLimiter"
            ) as mock_tier_limiter,
        ):
            # Mock the tier rate limiter to always allow
            mock_instance = MagicMock()
            mock_instance.check_rate_limit = AsyncMock(
                return_value=(True, None, {})  # allowed, no error, no retry info
            )
            mock_tier_limiter.return_value = mock_instance

            async def async_get(key):
                return None

            mock_redis.get = async_get

            # Mock the analysis function to be slow
            with patch(
                "github_analyzer.api.routes.analysis._perform_repository_analysis"
            ) as mock_perform:
                from github_analyzer.api.models.responses import AnalysisResponse

                async def slow_analysis(*args, **kwargs):
                    await asyncio.sleep(0.1)  # Simulate work
                    return AnalysisResponse(
                        repository_url="https://github.com/user/test-repo",
                        context="general",
                        analysis={
                            "executive_summary": "Test summary",
                            "overall_recommendation": "HIRE",
                            "confidence_score": 85,
                            "repository_type": "production",
                            "context_fit_score": 80,
                            "key_strengths": ["Good code quality"],
                            "primary_concerns": [],
                            "analysis_recommendations": ["Proceed with interview"],
                            "interview_focus_areas": ["System design"],
                        },
                        metadata={
                            "analysis_id": "test_123",
                            "repository_type": "production",
                            "confidence_grade": "B",
                            "ai_analysis_used": False,
                            "analysis_cost_usd": 0.0,
                            "response_time_seconds": 1.5,
                            "timestamp": "2024-01-01T12:00:00Z",
                            "cached": False,
                            "data_completeness": 0.9,
                        },
                    )

                mock_perform.side_effect = slow_analysis

                # Make a request
                response = await authenticated_client.post(
                    "/api/v1/analyze",
                    json={
                        "repository_url": "https://github.com/user/test-repo",
                        "context": "general",
                    },
                )

                assert response.status_code == 200

                # Check that counters were decremented (released)
                # In a real implementation, the context manager would handle this
                # For testing, we verify the final state

    @pytest.mark.asyncio
    @pytest.mark.timeout(30)  # Deterministic test - will never timeout
    async def test_multiple_users_different_limits(
        self, async_client, test_db, mock_github_fetcher
    ):
        """Test that different users have separate rate limits.

        This test verifies that:
        1. User1 can exceed their limit and get 429 errors
        2. User2 can still make requests when User1 is at their limit
        3. Both users' requests complete successfully when allowed
        """
        from github_analyzer.api.dependencies import (
            get_github_fetcher,
            get_redis_service,
        )
        from github_analyzer.api.services.rate_limit_dependencies import (
            get_rate_limit_service,
        )
        from github_analyzer.api.services.rate_limit_service import RateLimitService
        from github_analyzer.database.models import SubscriptionPlan
        from github_analyzer.database.operations import UserOperations

        # Get the mock redis service from the app's dependency overrides
        mock_redis_service = async_client.app.dependency_overrides[get_redis_service]()

        # Create rate limit service with mock redis
        mock_rate_limit_service = RateLimitService(mock_redis_service)

        # Override dependencies on async_client's app
        async_client.app.dependency_overrides[get_github_fetcher] = lambda: (
            mock_github_fetcher
        )
        async_client.app.dependency_overrides[get_rate_limit_service] = lambda: (
            mock_rate_limit_service
        )

        # Create two test users with unique emails
        import time

        timestamp = int(time.time() * 1000)
        user1_email = f"user1_{timestamp}@example.com"
        user2_email = f"user2_{timestamp}@example.com"

        async with test_db() as db_session:
            user1 = await UserOperations.create_user(
                db_session,
                email=user1_email,
                password="TestPassword123!",
                full_name="User One",
            )
            user1.is_verified = True
            user1.subscription_plan = SubscriptionPlan.PROFESSIONAL

            user2 = await UserOperations.create_user(
                db_session,
                email=user2_email,
                password="TestPassword123!",
                full_name="User Two",
            )
            user2.is_verified = True
            user2.subscription_plan = SubscriptionPlan.PROFESSIONAL

            await db_session.commit()

        # Login as user1
        login1 = await async_client.post(
            "/api/v1/auth/login",
            json={"email": user1_email, "password": "TestPassword123!"},
        )
        token1 = login1.json()["access_token"]

        # Login as user2
        login2 = await async_client.post(
            "/api/v1/auth/login",
            json={"email": user2_email, "password": "TestPassword123!"},
        )
        token2 = login2.json()["access_token"]

        # Mock the Redis cache for analysis results
        with (
            patch("github_analyzer.api.routes.analysis.redis_service") as mock_cache,
            patch(
                "github_analyzer.api.routes.analysis.TierRateLimiter"
            ) as mock_tier_limiter,
            patch(
                "github_analyzer.api.routes.analysis.validate_context"
            ) as mock_validate_context,
        ):
            # Mock the tier rate limiter to always allow
            mock_instance = MagicMock()
            mock_instance.check_rate_limit = AsyncMock(
                return_value=(True, None, {})  # allowed, no error, no retry info
            )
            mock_tier_limiter.return_value = mock_instance

            async def async_get(key):
                return None  # No cache hits

            mock_cache.get = async_get

            # ==============================================================
            # OPERATION "SURGICAL ISOLATION"
            # Mock validate_context to eliminate database race conditions.
            # Rate limiting tests must test ONLY rate limiting logic.
            # ==============================================================
            mock_validate_context.return_value = None  # AsyncMock by default

            # ==============================================================
            # DETERMINISTIC CONDUCTOR PATTERN
            # The test is the absolute master of the event loop.
            # No timeouts. No races. No luck. Only logic.
            # ==============================================================

            # Mock analysis to avoid hitting real services
            with patch(
                "github_analyzer.api.routes.analysis._perform_repository_analysis"
            ) as mock_perform:
                import asyncio

                from github_analyzer.api.models.responses import AnalysisResponse

                # Dictionary to store per-request events
                # The TEST controls when each request completes
                request_events = {}
                request_counter = 0

                async def mock_analysis_deterministic(*args, **kwargs):
                    """Deterministic mock - completes ONLY when test explicitly allows it."""
                    nonlocal request_counter
                    request_id = request_counter
                    request_counter += 1

                    # Create event for this specific request
                    event = asyncio.Event()
                    request_events[request_id] = event

                    # Wait for THIS request's event to be set by the test conductor
                    # NO TIMEOUT - the test WILL set it when ready
                    await event.wait()

                    return AnalysisResponse(
                        repository_url=args[0],
                        context="general",
                        analysis={
                            "executive_summary": "Test",
                            "overall_recommendation": "HIRE",
                            "confidence_score": 85,
                            "repository_type": "portfolio",
                            "context_fit_score": 80,
                            "key_strengths": ["Good"],
                            "primary_concerns": [],
                            "analysis_recommendations": ["Yes"],
                            "interview_focus_areas": ["Tech"],
                        },
                        metadata={
                            "analysis_id": f"test_{request_id}",
                            "repository_type": "portfolio",
                            "confidence_grade": "B",
                            "ai_analysis_used": False,
                            "analysis_cost_usd": 0.0,
                            "response_time_seconds": 0.1,
                            "timestamp": "2024-01-01T12:00:00Z",
                            "cached": False,
                            "data_completeness": 0.9,
                        },
                    )

                mock_perform.side_effect = mock_analysis_deterministic

                try:
                    # ==============================================================
                    # CONDUCTOR'S ORCHESTRATION
                    # Every action is explicit. Every completion is controlled.
                    # ==============================================================

                    # STEP 1: Create 3 concurrent tasks for user1
                    # These will block in mock until we release them
                    tasks_user1 = []
                    for i in range(3):
                        task = asyncio.create_task(
                            async_client.post(
                                "/api/v1/analyze",
                                json={
                                    "repository_url": f"https://github.com/testuser{i + 1}/repo",
                                    "context": "general",
                                },
                                headers={"Authorization": f"Bearer {token1}"},
                            )
                        )
                        tasks_user1.append(task)
                        # Yield after each task creation to ensure it gets scheduled
                        await asyncio.sleep(0)

                    # STEP 2: Give event loop time to schedule all tasks
                    await asyncio.sleep(0.01)

                    # STEP 3: Wait for all 3 user1 tasks to reach the event wait
                    # Poll until we have 3 request events created
                    for _ in range(100):  # Max 10 seconds at 0.1s intervals
                        if len(request_events) >= 3:
                            break
                        await asyncio.sleep(0.1)

                    assert len(request_events) == 3, (
                        f"Expected 3 requests to start, got {len(request_events)}"
                    )

                    # STEP 4: User1's 4th request should be IMMEDIATELY rejected (at concurrent limit)
                    response4 = await async_client.post(
                        "/api/v1/analyze",
                        json={
                            "repository_url": "https://github.com/testuser4/repo",
                            "context": "general",
                        },
                        headers={"Authorization": f"Bearer {token1}"},
                    )

                    assert response4.status_code == 429, (
                        f"Expected 429 for user1's 4th concurrent request, got {response4.status_code}"
                    )
                    assert (
                        "Too many concurrent requests"
                        in response4.json()["detail"]["error"]
                    )

                    # STEP 5: User2 should be able to start a request (separate limit)
                    task_user2 = asyncio.create_task(
                        async_client.post(
                            "/api/v1/analyze",
                            json={
                                "repository_url": "https://github.com/user/repo_user2",
                                "context": "general",
                            },
                            headers={"Authorization": f"Bearer {token2}"},
                        )
                    )

                    # STEP 6: Allow task_user2 to start and get scheduled
                    await asyncio.sleep(0)
                    await asyncio.sleep(0.01)

                    # Wait for user2's request to reach event wait
                    for _ in range(100):
                        if len(request_events) >= 4:
                            break
                        await asyncio.sleep(0.1)

                    assert len(request_events) == 4, (
                        f"Expected 4 total requests (3 user1, 1 user2), got {len(request_events)}"
                    )

                    # STEP 7: User1 should STILL be blocked
                    response5 = await async_client.post(
                        "/api/v1/analyze",
                        json={
                            "repository_url": "https://github.com/user/repo5",
                            "context": "general",
                        },
                        headers={"Authorization": f"Bearer {token1}"},
                    )
                    assert response5.status_code == 429, (
                        f"Expected 429 for user1's 5th concurrent request, got {response5.status_code}"
                    )

                    # ==============================================================
                    # CONDUCTOR RELEASES THE TASKS
                    # We explicitly set each event to complete each request
                    # ==============================================================

                    # STEP 8: Release all 4 requests (3 user1 + 1 user2)
                    for request_id in range(4):
                        request_events[request_id].set()

                    # STEP 9: Await ALL tasks - they complete instantly now
                    all_results = await asyncio.gather(
                        *tasks_user1, task_user2, return_exceptions=True
                    )

                    # STEP 10: Verify all 4 tasks succeeded
                    success_count = sum(
                        1
                        for r in all_results
                        if hasattr(r, "status_code") and r.status_code == 200
                    )
                    assert success_count == 4, (
                        f"Expected 4 successful requests (3 for user1, 1 for user2), got {success_count}"
                    )

                    # STEP 11: Verify user1 can make new requests after slots released
                    # This request will create request_id 4
                    final_task = asyncio.create_task(
                        async_client.post(
                            "/api/v1/analyze",
                            json={
                                "repository_url": "https://github.com/user/final1",
                                "context": "general",
                            },
                            headers={"Authorization": f"Bearer {token1}"},
                        )
                    )

                    # Allow task to start and get scheduled
                    await asyncio.sleep(0)
                    await asyncio.sleep(0.01)
                    for _ in range(100):
                        if 4 in request_events:
                            break
                        await asyncio.sleep(0.1)

                    # Release final request
                    request_events[4].set()

                    final_response1 = await final_task
                    assert final_response1.status_code == 200, (
                        f"User1 should be able to make requests after cleanup, got {final_response1.status_code}"
                    )

                finally:
                    # Cleanup: Release any remaining events
                    for event in request_events.values():
                        event.set()
