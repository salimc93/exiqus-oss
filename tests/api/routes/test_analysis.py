"""
Tests for analysis endpoints.

Tests the core repository analysis API endpoints with mocked components
to ensure proper integration and error handling.
"""

import json
from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import create_test_app

# Removed unused imports


@pytest.fixture(autouse=True)
def mock_rate_limits():
    """Fixture to automatically mock rate limiting for all tests in this module."""

    @asynccontextmanager
    async def dummy_rate_limit_context():
        """A dummy context manager that does nothing."""
        yield

    def _mock_check_rate_limits():
        """This function will be used to replace the actual check_rate_limits."""
        return dummy_rate_limit_context()

    with patch(
        "github_analyzer.api.routes.analysis.check_rate_limits",
        new=_mock_check_rate_limits,
    ):
        yield


class TestAnalysisEndpoints:
    """Test cases for repository analysis endpoints."""

    @pytest.fixture
    def app(self):
        """Create test FastAPI application."""
        return create_test_app()

    @pytest.fixture
    def mock_github_fetcher(self, mock_repo_data):
        """Create mock GitHubFetcher for testing."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_repository_data.return_value = mock_repo_data
        return mock_fetcher

    @pytest.fixture
    def mock_repo_data(self):
        """Mock repository data for testing."""
        return {
            "name": "test-repo",
            "full_name": "user/test-repo",
            "description": "Test repository",
            "size": 1000,
            "languages": {"Python": 80, "JavaScript": 20},
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "stars": 10,
            "forks": 5,
            "default_branch": "main",
            "has_readme": True,
            "has_license": True,
            "has_ci": True,
            "commits_count": 50,
            "contributors_count": 2,
        }

    @pytest.fixture
    def mock_classification(self):
        """Mock repository classification."""
        mock_class = MagicMock()
        mock_class.primary_type = "portfolio"
        mock_class.confidence = 0.85
        # Add any other attributes that might be accessed
        mock_class.secondary_types = ["showcase"]
        return mock_class

    @pytest.fixture
    def mock_api_auth(self):
        """Mock API authentication for testing."""
        # This fixture is used to indicate that API auth should be mocked
        # The actual mocking happens in the client fixture
        return True

    @pytest.fixture
    async def auth_headers(self, async_client, test_db):
        """Get auth headers for test user with Professional plan."""
        from github_analyzer.database.models import SubscriptionPlan
        from github_analyzer.database.operations import UserOperations

        async with test_db() as db_session:
            # Check if user already exists
            user = await UserOperations.get_user_by_email(
                db_session, "test_api_user@example.com"
            )
            if not user:
                # Create a test user with Professional plan for API access
                user = await UserOperations.create_user(
                    db_session,
                    email="test_api_user@example.com",
                    password="TestPassword123!",
                    full_name="Test API User",
                )
                user.is_verified = True
                user.subscription_plan = (
                    SubscriptionPlan.PROFESSIONAL
                )  # Give API access
                await db_session.commit()

        # Login to get token
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "test_api_user@example.com", "password": "TestPassword123!"},
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    async def enterprise_auth_headers(self, async_client, test_db):
        """Get auth headers for test user with Enterprise plan."""
        from github_analyzer.database.models import SubscriptionPlan
        from github_analyzer.database.operations import UserOperations

        async with test_db() as db_session:
            # Check if user already exists
            user = await UserOperations.get_user_by_email(
                db_session, "test_enterprise_user@example.com"
            )
            if not user:
                # Create a test user with Enterprise plan for batch access
                user = await UserOperations.create_user(
                    db_session,
                    email="test_enterprise_user@example.com",
                    password="TestPassword123!",
                    full_name="Test Enterprise User",
                )
                user.is_verified = True
                user.subscription_plan = (
                    SubscriptionPlan.ENTERPRISE
                )  # Give batch access
                await db_session.commit()

        # Login to get token
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": "test_enterprise_user@example.com",
                "password": "TestPassword123!",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def mock_confidence_analysis(self):
        """Mock confidence analysis."""
        mock_conf = MagicMock()
        mock_conf.overall_confidence = 0.80
        mock_conf.overall_grade = "B+"
        mock_conf.data_completeness_score = 0.75
        # Add any other attributes that might be accessed
        mock_conf.confidence_scores = {"technical": 0.8, "documentation": 0.75}
        return mock_conf

    @pytest.fixture
    def mock_report(self):
        """Mock analysis report."""
        return {
            "analysis": {
                "executive_summary": "Well-structured repository with good practices",
                "verdict": "HIRE",
                "confidence_score": 85,
                "strengths": ["Good documentation", "Comprehensive tests"],
                "concerns": ["Some code duplication"],
                "repository_type": "portfolio",
                "trust_score": 0.85,
            }
        }

    @pytest.mark.asyncio
    async def test_analyze_endpoint_success(
        self,
        async_client,
        test_db,
        mock_github_fetcher,
        mock_repo_data,
        mock_classification,
        mock_confidence_analysis,
        mock_report,
        mock_redis_service,
    ):
        """Test successful repository analysis."""
        # First create a test user and get auth token
        from github_analyzer.database.models import SubscriptionPlan
        from github_analyzer.database.operations import UserOperations

        async with test_db() as db_session:
            # Create a test user
            user = await UserOperations.create_user(
                db_session,
                email="test_analyze@example.com",
                password="TestPassword123!",
                full_name="Test Analyzer",
            )
            user.is_verified = True  # Mark as verified
            user.subscription_plan = SubscriptionPlan.PROFESSIONAL  # Need API access
            await db_session.commit()

        # Login to get token
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "test_analyze@example.com", "password": "TestPassword123!"},
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        # Override github fetcher dependency
        from github_analyzer.api.dependencies import get_github_fetcher

        async_client.app.dependency_overrides[get_github_fetcher] = lambda: (
            mock_github_fetcher
        )

        with (
            patch(
                "github_analyzer.api.routes.analysis.redis_service", mock_redis_service
            ),
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

            # Import the response model
            from github_analyzer.api.models.responses import AnalysisResponse

            # Mock the entire analysis function to return a complete response
            mock_analysis_response = AnalysisResponse(
                repository_url="https://github.com/user/test-repo",
                context="general",
                analysis=mock_report["analysis"],
                metadata={
                    "ai_analysis_used": True,
                    "analysis_cost_usd": 0.002,
                    "cached": False,
                    "analysis_time": "2024-01-01T12:00:00Z",
                    "response_time_seconds": 1.5,
                },
            )

            with patch(
                "github_analyzer.api.routes.analysis._perform_repository_analysis"
            ) as mock_perform_analysis:
                mock_perform_analysis.return_value = mock_analysis_response

                response = await async_client.post(
                    "/api/v1/analyze",
                    json={
                        "repository_url": "https://github.com/user/test-repo",
                        "context": "general",
                        "force_refresh": False,
                    },
                    headers={"Authorization": f"Bearer {token}"},
                )

                assert response.status_code == 200
                data = response.json()

                assert data["repository_url"] == "https://github.com/user/test-repo"
                assert data["context"] == "general"
                assert "analysis" in data
                assert "metadata" in data
                assert data["metadata"]["ai_analysis_used"] is True
                assert data["metadata"]["analysis_cost_usd"] == 0.002

    @pytest.mark.asyncio
    async def test_analyze_endpoint_cache_hit(self, async_client, auth_headers):
        """Test analysis endpoint with cache hit."""
        cached_result = {
            "repository_url": "https://github.com/user/test-repo",
            "context": "general",
            "analysis": {"verdict": "HIRE", "confidence_score": 85},
            "metadata": {"cached": False, "timestamp": "2024-01-01T12:00:00Z"},
        }

        with patch("github_analyzer.api.routes.analysis.redis_service") as mock_redis:
            # Create an async function that returns the cached result
            async def async_get(key):
                # Only return cached result for the analysis cache key
                if "analysis:" in key:
                    return json.dumps(cached_result)
                # For rate limit counters, return None
                return None

            mock_redis.get = async_get
            mock_redis.incr = AsyncMock(return_value=1)
            mock_redis.decr = AsyncMock(return_value=0)
            mock_redis.zadd = AsyncMock()
            mock_redis.zremrangebyscore = AsyncMock()
            mock_redis.expire = AsyncMock()
            mock_redis.zcount = AsyncMock(return_value=0)

            response = await async_client.post(
                "/api/v1/analyze",
                json={
                    "repository_url": "https://github.com/user/test-repo",
                    "context": "general",
                    "force_refresh": False,
                },
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()

            assert data["repository_url"] == "https://github.com/user/test-repo"
            assert data["metadata"]["cached"] is True
            assert "cache_hit_time" in data["metadata"]

    @pytest.mark.asyncio
    async def test_analyze_endpoint_force_refresh(
        self,
        async_client,
        auth_headers,
        mock_repo_data,
        mock_classification,
        mock_confidence_analysis,
        mock_report,
    ):
        """Test analysis endpoint with force refresh ignoring cache."""
        from github_analyzer.api.models.responses import AnalysisResponse

        # Mock the entire analysis function to return a complete response
        mock_analysis_response = AnalysisResponse(
            repository_url="https://github.com/user/test-repo",
            context="general",
            analysis=mock_report["analysis"],
            metadata={
                "ai_analysis_used": True,
                "analysis_cost_usd": 0.002,
                "cached": False,
                "analysis_time": "2024-01-01T12:00:00Z",
                "response_time_seconds": 1.5,
            },
        )

        with patch("github_analyzer.api.routes.analysis.redis_service") as mock_redis:
            # Create AsyncMock objects with proper return values
            mock_redis.get = AsyncMock(return_value=None)  # Force refresh ignores cache
            mock_redis.set = AsyncMock()
            mock_redis.delete = AsyncMock()
            mock_redis.incr = AsyncMock(return_value=1)
            mock_redis.decr = AsyncMock(return_value=0)
            mock_redis.zadd = AsyncMock()
            mock_redis.zremrangebyscore = AsyncMock()
            mock_redis.expire = AsyncMock()
            mock_redis.zcount = AsyncMock(return_value=0)

            with patch(
                "github_analyzer.api.routes.analysis._perform_repository_analysis"
            ) as mock_perform_analysis:
                mock_perform_analysis.return_value = mock_analysis_response

                response = await async_client.post(
                    "/api/v1/analyze",
                    json={
                        "repository_url": "https://github.com/user/test-repo",
                        "context": "general",
                        "force_refresh": True,
                    },
                    headers=auth_headers,
                )

                assert response.status_code == 200
                # Verify cache was not called due to force_refresh
                # Note: redis.get IS called for rate limiting, so we check calls instead
                get_calls = mock_redis.get.call_args_list
                cache_calls = [call for call in get_calls if "analysis:" in str(call)]
                assert len(cache_calls) == 0, (
                    "Cache should not be checked with force_refresh=True"
                )

    @pytest.mark.asyncio
    async def test_analyze_endpoint_invalid_url(self, async_client, auth_headers):
        """Test analysis endpoint with invalid GitHub URL."""
        response = await async_client.post(
            "/api/v1/analyze",
            json={
                "repository_url": "https://invalid-url.com/repo",
                "context": "general",
            },
            headers=auth_headers,
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_analyze_endpoint_analysis_failure(self, async_client, auth_headers):
        """Test analysis endpoint when GitHub fetcher fails."""
        with patch("github_analyzer.api.routes.analysis.redis_service") as mock_redis:
            # Mock all redis methods with proper return types
            mock_redis.get = AsyncMock(return_value=None)
            mock_redis.set = AsyncMock()
            mock_redis.delete = AsyncMock()
            mock_redis.incr = AsyncMock(return_value=1)
            mock_redis.decr = AsyncMock(return_value=0)
            mock_redis.zadd = AsyncMock()
            mock_redis.zremrangebyscore = AsyncMock()
            mock_redis.expire = AsyncMock()
            mock_redis.zcount = AsyncMock(return_value=0)

            # Create an async function that raises an exception
            async def mock_perform_analysis(
                url,
                context,
                start_time,
                github_fetcher,
                user,
                size_limit_mb,
                db,  # Added to match actual signature
                budget_monitor=None,
                output_format="json",
                batch_id=None,  # Added to match actual signature
                role="senior",  # Changed to match actual default
            ):
                from fastapi import HTTPException

                raise HTTPException(
                    status_code=401,
                    detail={
                        "error": "Analysis failed",
                        "message": "GitHub API error",
                        "repository_url": url,
                    },
                )

            with patch(
                "github_analyzer.api.routes.analysis._perform_repository_analysis",
                new=mock_perform_analysis,
            ):
                response = await async_client.post(
                    "/api/v1/analyze",
                    json={
                        "repository_url": "https://github.com/user/test-repo",
                        "context": "general",
                    },
                    headers=auth_headers,
                )

                assert response.status_code == 401
                data = response.json()
                assert "error" in data["detail"]
                assert data["detail"]["error"] == "Analysis failed"
                assert "GitHub API error" in data["detail"]["message"]
                assert (
                    data["detail"]["repository_url"]
                    == "https://github.com/user/test-repo"
                )

    @pytest.mark.asyncio
    async def test_analyze_endpoint_repository_too_large(
        self, async_client, auth_headers, mock_github_fetcher
    ):
        """Test analysis endpoint with repository that exceeds size limit."""
        # Mock the check_repository_size method
        mock_github_fetcher.check_repository_size.return_value = {
            "size_kb": 150000,  # 150MB (exceeds 100MB limit)
            "file_count": 5000,
        }

        with patch("github_analyzer.api.routes.analysis.redis_service") as mock_redis:
            # Create an async function that returns None
            async def async_get(key):
                return None

            mock_redis.get = async_get
            mock_redis.set = AsyncMock()
            mock_redis.delete = AsyncMock()
            mock_redis.incr = AsyncMock(return_value=1)
            mock_redis.decr = AsyncMock(return_value=0)
            mock_redis.zadd = AsyncMock()
            mock_redis.zremrangebyscore = AsyncMock()
            mock_redis.expire = AsyncMock()
            mock_redis.zcount = AsyncMock(return_value=0)

            # Create an async function that raises HTTPException for size limit
            async def mock_perform_analysis(
                url,
                context,
                start_time,
                github_fetcher,
                user,
                size_limit_mb,
                db,  # Added to match actual signature
                budget_monitor=None,
                output_format="json",
                batch_id=None,  # Added to match actual signature
                role="senior",  # Changed to match actual default
            ):
                from datetime import datetime, timezone

                from fastapi import HTTPException

                raise HTTPException(
                    status_code=413,
                    detail={
                        "error": "Repository too large",
                        "message": "Repository size (146.5MB) exceeds maximum allowed size (100MB) for your basic plan.",
                        "repository_url": url,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )

            with patch(
                "github_analyzer.api.routes.analysis._perform_repository_analysis",
                new=mock_perform_analysis,
            ):
                response = await async_client.post(
                    "/api/v1/analyze",
                    json={
                        "repository_url": "https://github.com/user/large-repo",
                        "context": "general",
                    },
                    headers=auth_headers,
                )

                assert response.status_code == 413  # Payload Too Large
                data = response.json()
                assert "error" in data["detail"]
                assert data["detail"]["error"] == "Repository too large"
                assert "exceeds maximum allowed size" in data["detail"]["message"]
                assert (
                    data["detail"]["repository_url"]
                    == "https://github.com/user/large-repo"
                )

    @pytest.mark.asyncio
    async def test_analyze_endpoint_too_many_files(
        self, async_client, auth_headers, mock_github_fetcher
    ):
        """Test analysis endpoint with repository that has too many files."""
        # Mock the check_repository_size method
        mock_github_fetcher.check_repository_size.return_value = {
            "size_kb": 50000,  # 50MB (within limit)
            "file_count": 15000,  # Exceeds 10000 file limit
        }

        with patch("github_analyzer.api.routes.analysis.redis_service") as mock_redis:
            # Create an async function that returns None
            async def async_get(key):
                return None

            mock_redis.get = async_get
            mock_redis.set = AsyncMock()
            mock_redis.delete = AsyncMock()
            mock_redis.incr = AsyncMock(return_value=1)
            mock_redis.decr = AsyncMock(return_value=0)
            mock_redis.zadd = AsyncMock()
            mock_redis.zremrangebyscore = AsyncMock()
            mock_redis.expire = AsyncMock()
            mock_redis.zcount = AsyncMock(return_value=0)

            # Create an async function that raises HTTPException for file count limit
            async def mock_perform_analysis(
                url,
                context,
                start_time,
                github_fetcher,
                user,
                size_limit_mb,
                db,  # Added to match actual signature
                budget_monitor=None,
                output_format="json",
                batch_id=None,  # Added to match actual signature
                role="senior",  # Changed to match actual default
            ):
                from datetime import datetime, timezone

                from fastapi import HTTPException

                raise HTTPException(
                    status_code=413,
                    detail={
                        "error": "Repository has too many files",
                        "message": "Repository file count (15000) exceeds maximum allowed (10000)",
                        "repository_url": url,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )

            with patch(
                "github_analyzer.api.routes.analysis._perform_repository_analysis",
                new=mock_perform_analysis,
            ):
                response = await async_client.post(
                    "/api/v1/analyze",
                    json={
                        "repository_url": "https://github.com/user/many-files-repo",
                        "context": "general",
                    },
                    headers=auth_headers,
                )

                assert response.status_code == 413  # Payload Too Large
                data = response.json()
                assert "error" in data["detail"]
                assert data["detail"]["error"] == "Repository has too many files"
                assert "file count" in data["detail"]["message"]
                assert "exceeds maximum allowed" in data["detail"]["message"]
                assert (
                    data["detail"]["repository_url"]
                    == "https://github.com/user/many-files-repo"
                )

    @pytest.mark.asyncio
    async def test_batch_analyze_success(
        self,
        async_client,
        enterprise_auth_headers,
        mock_repo_data,
        mock_classification,
        mock_confidence_analysis,
        mock_report,
    ):
        """Test successful batch repository analysis."""
        from github_analyzer.api.models.responses import AnalysisResponse

        # Mock the analysis function to return complete responses
        mock_analysis_response1 = AnalysisResponse(
            repository_url="https://github.com/user/repo1",
            context="general",
            analysis=mock_report["analysis"],
            metadata={
                "ai_analysis_used": True,
                "analysis_cost_usd": 0.002,
                "cached": False,
                "analysis_time": "2024-01-01T12:00:00Z",
                "response_time_seconds": 1.5,
            },
        )

        mock_analysis_response2 = AnalysisResponse(
            repository_url="https://github.com/user/repo2",
            context="startup",
            analysis=mock_report["analysis"],
            metadata={
                "ai_analysis_used": True,
                "analysis_cost_usd": 0.002,
                "cached": False,
                "analysis_time": "2024-01-01T12:00:00Z",
                "response_time_seconds": 1.5,
            },
        )

        # Create a custom async mock that returns different values
        async def mock_perform_analysis(
            url,
            context,
            start_time,
            github_fetcher,
            user,
            size_limit_mb,
            budget_monitor=None,
            output_format="json",
            batch_id=None,
        ):
            if "repo1" in url:
                return mock_analysis_response1
            else:
                return mock_analysis_response2

        with (
            patch(
                "github_analyzer.api.routes.analysis._perform_repository_analysis",
                new=mock_perform_analysis,
            ),
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

            response = await async_client.post(
                "/api/v1/batch",
                json={
                    "repositories": [
                        {
                            "repository_url": "https://github.com/user/repo1",
                            "context": "general",
                        },
                        {
                            "repository_url": "https://github.com/user/repo2",
                            "context": "startup",
                        },
                    ]
                },
                headers=enterprise_auth_headers,
            )

            assert response.status_code == 200
            data = response.json()

            assert len(data["results"]) == 2
            assert len(data["errors"]) == 0
            assert data["metadata"]["total_repositories"] == 2
            assert data["metadata"]["successful_count"] == 2
            assert data["metadata"]["failed_count"] == 0

    @pytest.mark.asyncio
    async def test_batch_analyze_partial_failure(
        self,
        async_client,
        enterprise_auth_headers,
        mock_repo_data,
        mock_classification,
        mock_confidence_analysis,
        mock_report,
    ):
        """Test batch analysis with some repositories failing."""
        from github_analyzer.api.models.responses import AnalysisResponse

        # Mock successful response for first repo
        mock_analysis_response = AnalysisResponse(
            repository_url="https://github.com/user/repo1",
            context="general",
            analysis=mock_report["analysis"],
            metadata={
                "ai_analysis_used": True,
                "analysis_cost_usd": 0.002,
                "cached": False,
                "analysis_time": "2024-01-01T12:00:00Z",
                "response_time_seconds": 1.5,
            },
        )

        # Create a custom async mock that returns different values
        async def mock_perform_analysis(
            url,
            context,
            start_time,
            github_fetcher,
            user,
            size_limit_mb,
            budget_monitor=None,
            output_format="json",
            batch_id=None,
        ):
            if "repo1" in url:
                return mock_analysis_response
            else:
                raise Exception("Repository not found")

        with (
            patch(
                "github_analyzer.api.routes.analysis._perform_repository_analysis",
                new=mock_perform_analysis,
            ),
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

            response = await async_client.post(
                "/api/v1/batch",
                json={
                    "repositories": [
                        {
                            "repository_url": "https://github.com/user/repo1",
                            "context": "general",
                        },
                        {
                            "repository_url": "https://github.com/user/private-repo",
                            "context": "startup",
                        },
                    ]
                },
                headers=enterprise_auth_headers,
            )

            assert response.status_code == 200
            data = response.json()

            assert len(data["results"]) == 1  # One success
            assert len(data["errors"]) == 1  # One failure
            assert data["metadata"]["successful_count"] == 1
            assert data["metadata"]["failed_count"] == 1
            assert (
                data["errors"][0]["repository_url"]
                == "https://github.com/user/private-repo"
            )

    @pytest.mark.asyncio
    async def test_batch_analyze_empty_request(self, async_client, auth_headers):
        """Test batch analysis with empty repository list."""
        response = await async_client.post(
            "/api/v1/batch", json={"repositories": []}, headers=auth_headers
        )

        assert response.status_code == 400  # Business logic validation error

    @pytest.mark.asyncio
    async def test_batch_analyze_oversized_request(self, async_client, auth_headers):
        """Test batch analysis with too many repositories."""
        repositories = []
        for i in range(15):  # Exceeds limit of 10
            repositories.append(
                {
                    "repository_url": f"https://github.com/user/repo{i}",
                    "context": "general",
                }
            )

        response = await async_client.post(
            "/api/v1/batch", json={"repositories": repositories}, headers=auth_headers
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_batch_analyze_requires_enterprise(self, async_client, test_db):
        """Test batch analysis requires Professional, Enterprise, or Scale+ plan."""
        from github_analyzer.database.models import SubscriptionPlan
        from github_analyzer.database.operations import UserOperations

        async with test_db() as db_session:
            # Create a BASIC user (not Professional or Enterprise)
            user = await UserOperations.get_user_by_email(
                db_session, "basic_user@example.com"
            )
            if not user:
                user = await UserOperations.create_user(
                    db_session,
                    email="basic_user@example.com",
                    password="TestPassword123!",
                    full_name="Basic User",
                )
                user.is_verified = True
                user.subscription_plan = SubscriptionPlan.BASIC
                await db_session.commit()

        # Login to get token
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "basic_user@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Try batch analysis
        response = await async_client.post(
            "/api/v1/batch",
            json={
                "repositories": [
                    {
                        "repository_url": "https://github.com/user/repo1",
                        "context": "general",
                    }
                ]
            },
            headers=headers,
        )

        assert response.status_code == 403
        data = response.json()
        assert (
            "Batch analysis requires Professional, Enterprise, or Scale+ plan"
            in data["detail"]["error"]
        )
        assert data["detail"]["current_plan"] == "BASIC"
        assert data["detail"]["required_plans"] == [
            "professional",
            "enterprise",
            "scale_plus",
        ]

    def test_should_use_ai_analysis_template_cases(self):
        """Test AI usage decision for template cases."""
        from github_analyzer.api.routes.analysis import _should_use_ai_analysis

        # Mock abandoned project that should use template
        repo_data = MagicMock()
        repo_data.size = 30  # Small
        repo_data.languages = {"Python": 100}
        repo_data.stars = 0
        repo_data.metrics = MagicMock(
            commit_frequency=0,
            unique_contributors=0,
            days_since_last_commit=400,  # >1 year
        )
        repo_data.file_count = 3
        repo_data.forks = 0
        repo_data.full_name = "user/old-project"

        classification = MagicMock()
        classification.repository_type = MagicMock(value="abandoned")

        confidence = MagicMock()

        result = _should_use_ai_analysis(repo_data, classification, confidence)
        assert result is False  # Should use template for truly abandoned projects

    def test_should_use_ai_analysis_complex_cases(self):
        """Test AI usage decision for complex cases."""
        from github_analyzer.api.routes.analysis import _should_use_ai_analysis

        # Mock production project that should use AI
        repo_data = MagicMock()
        repo_data.size = 5000  # Large
        repo_data.languages = {"Python": 60, "JavaScript": 40}
        repo_data.stars = 10
        repo_data.metrics = MagicMock(commit_frequency=1.5, unique_contributors=2)
        repo_data.full_name = "company/production-app"

        classification = MagicMock()
        classification.repository_type = MagicMock(value="production")

        confidence = MagicMock()

        result = _should_use_ai_analysis(repo_data, classification, confidence)
        assert result is True  # Production repos always use AI

    def test_should_use_ai_analysis_minimal_repo(self):
        """Test AI usage decision for minimal repositories."""
        from github_analyzer.api.routes.analysis import _should_use_ai_analysis

        # Mock minimal hello-world repository
        repo_data = MagicMock()
        repo_data.size = 10  # <50KB
        repo_data.languages = {"Python": 100}
        repo_data.stars = 0
        repo_data.metrics = MagicMock(commit_frequency=0, unique_contributors=1)
        repo_data.file_count = 2
        repo_data.forks = 0
        repo_data.full_name = "student/hello-world"

        classification = MagicMock()
        classification.repository_type = MagicMock(value="learning")

        confidence = MagicMock()

        result = _should_use_ai_analysis(repo_data, classification, confidence)
        assert result is False  # Should use template for trivial repos

    @pytest.mark.asyncio
    async def test_analyze_endpoint_includes_ai_features(
        self,
        async_client,
        test_db,
        mock_github_fetcher,
        mock_repo_data,
        mock_redis_service,
    ):
        """Test that analysis endpoint includes insights, questions, and recommendations."""
        from github_analyzer.api.dependencies import get_github_fetcher
        from github_analyzer.database.models import SubscriptionPlan
        from github_analyzer.database.operations import UserOperations

        # Create test user
        async with test_db() as db_session:
            user = await UserOperations.create_user(
                db_session,
                email="test_ai_features@example.com",
                password="TestPassword123!",
                full_name="Test AI Features",
            )
            user.is_verified = True
            user.subscription_plan = SubscriptionPlan.PROFESSIONAL
            await db_session.commit()

        # Login to get token
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": "test_ai_features@example.com",
                "password": "TestPassword123!",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Override dependencies
        async_client.app.dependency_overrides[get_github_fetcher] = lambda: (
            mock_github_fetcher
        )

        # Mock the repository size check
        mock_github_fetcher.check_repository_size.return_value = {
            "size_kb": 5000,  # 5MB
            "file_count": 100,
        }

        # Mock fetched repo data
        mock_repo_data["is_private"] = False
        mock_repo_data["size"] = 5000
        mock_repo_data["stars"] = 10

        # Create a proper mock for repository data
        from types import SimpleNamespace

        repo_data_mock = SimpleNamespace(**mock_repo_data)
        repo_data_mock.is_private = False
        repo_data_mock.metrics = SimpleNamespace(
            unique_contributors=3, commit_frequency=2.5
        )
        mock_github_fetcher.fetch_repository_data.return_value = repo_data_mock

        # Create a mock report with AI features
        mock_report = MagicMock()
        mock_report.repository_url = "https://github.com/user/test-repo"
        mock_report.repository_name = "test-repo"
        mock_report.analysis_date = datetime.now()
        mock_report.subscription_tier = "professional"
        mock_report.context = MagicMock(value="startup")
        mock_report.executive_summary = "Strong developer with modern practices"
        mock_report.overall_recommendation = "HIRE"
        mock_report.confidence_score = 0.85
        mock_report.repository_type = MagicMock(value="portfolio")
        mock_report.context_fit_score = 0.8
        mock_report.key_strengths = ["Strong code", "Good tests"]
        mock_report.primary_concerns = ["Low documentation"]
        mock_report.analysis_recommendations = ["Great candidate"]
        mock_report.interview_focus_areas = ["Architecture decisions"]
        mock_report.data_completeness = 0.9
        mock_report.technical_assessment = None
        mock_report.professional_practices = None
        mock_report.communication_skills = None
        mock_report.growth_indicators = None
        mock_report.evidence_summary = {}
        mock_report.analysis_limitations = ["Limited collaboration data"]

        # Mock AI components
        mock_report.screening_insights = MagicMock()
        mock_report.screening_insights.insights = [
            {
                "category": "technical_skills",
                "description": "Strong TypeScript proficiency demonstrated",
                "evidence": ["100% TypeScript codebase", "Advanced type usage"],
                "confidence": "high",
                "impact": "positive",
            }
        ]

        mock_report.interview_questions = {
            "all_questions": [
                {
                    "category": "technical_decisions",
                    "question": "Can you explain your TypeScript adoption strategy?",
                    "evidence_reference": "100% TypeScript codebase",
                    "follow_ups": ["How do you handle type complexity?"],
                    "what_to_listen_for": "Understanding of type system benefits",
                    "context_relevance": "Important for startup's tech stack",
                }
            ]
        }

        mock_report.evidence_based_recommendations = {
            "all_recommendations": [
                {
                    "type": "strength",
                    "recommendation": "Strong technical foundation in modern web technologies",
                    "priority": "high",
                    "evidence": "TypeScript, React, comprehensive testing",
                }
            ]
        }

        mock_report.green_flags = [MagicMock(description="Comprehensive testing")]
        mock_report.red_flags = []

        # Add screening_insights attributes for confidence_explanation
        mock_report.screening_insights.confidence_explanation = (
            "High confidence based on comprehensive analysis"
        )
        mock_report.screening_insights.data_limitations = [
            "Cannot assess team collaboration"
        ]

        # Import the response model
        from github_analyzer.api.models.clean_responses import convert_to_clean_response
        from github_analyzer.api.models.responses import AnalysisResponse

        # Convert mock report to clean response
        clean_response = convert_to_clean_response(mock_report, 0.03)

        # Create expected analysis response
        expected_analysis = {
            "executive_summary": clean_response.executive_summary,
            "overall_recommendation": "HIRE",
            "confidence_explanation": clean_response.confidence_explanation,
            "repository_type": clean_response.repository_type,
            "context_fit_score": 0.8,
            "key_strengths": ["Strong code", "Good tests"],
            "primary_concerns": ["Low documentation"],
            "analysis_recommendations": ["Great candidate"],
            "interview_focus_areas": ["Architecture decisions"],
            "insights": [insight.model_dump() for insight in clean_response.insights],
            "questions": [
                question.model_dump() for question in clean_response.questions
            ],
            "recommendations": [
                rec.model_dump() for rec in clean_response.recommendations
            ],
            "evidence_patterns": [
                pattern.model_dump() for pattern in clean_response.evidence_patterns
            ],
            "insights_count": clean_response.insights_count,
            "questions_count": clean_response.questions_count,
            "recommendations_count": clean_response.recommendations_count,
            "evidence_patterns_count": clean_response.evidence_patterns_count,
            "green_flags": clean_response.green_flags,
            "red_flags": clean_response.red_flags,
            "limitations": clean_response.limitations,
            "data_limitations": clean_response.data_limitations,
            "estimated_cost": clean_response.estimated_cost,
        }

        # Mock the entire analysis function to return a complete response
        mock_analysis_response = AnalysisResponse(
            repository_url="https://github.com/user/test-repo",
            context="startup",
            analysis=expected_analysis,
            metadata={
                "ai_analysis_used": True,
                "analysis_cost_usd": 0.03,
                "cached": False,
                "analysis_time": "2024-01-01T12:00:00Z",
                "response_time_seconds": 1.5,
                "repository_type": "portfolio",
                "confidence_grade": "B+",
                "data_completeness": 0.9,
            },
        )

        with (
            patch(
                "github_analyzer.api.routes.analysis.redis_service", mock_redis_service
            ),
            patch(
                "github_analyzer.api.routes.analysis.TierRateLimiter"
            ) as mock_tier_limiter,
            patch(
                "github_analyzer.api.routes.analysis._perform_repository_analysis"
            ) as mock_perform_analysis,
        ):
            # Mock tier rate limiter
            mock_instance = MagicMock()
            mock_instance.check_rate_limit = AsyncMock(return_value=(True, None, {}))
            mock_tier_limiter.return_value = mock_instance

            # Mock the analysis function
            mock_perform_analysis.return_value = mock_analysis_response

            response = await async_client.post(
                "/api/v1/analyze",
                json={
                    "repository_url": "https://github.com/user/test-repo",
                    "context": "startup",
                    "force_refresh": True,
                },
                headers={"Authorization": f"Bearer {token}"},
            )

            if response.status_code != 200:
                print(f"Response status: {response.status_code}")
                print(f"Response body: {response.json()}")
            assert response.status_code == 200
            data = response.json()

            # Verify basic structure
            assert data["repository_url"] == "https://github.com/user/test-repo"
            assert "analysis" in data

            # Verify AI features are included
            analysis = data["analysis"]
            assert "insights" in analysis
            assert "questions" in analysis
            assert "recommendations" in analysis
            assert "insights_count" in analysis
            assert "questions_count" in analysis
            assert "recommendations_count" in analysis

            # Verify evidence-based fields
            assert "evidence_patterns" in analysis
            assert "evidence_patterns_count" in analysis
            assert "confidence_explanation" in analysis
            assert "data_limitations" in analysis

            # Verify content
            assert len(analysis["insights"]) > 0
            assert analysis["insights"][0]["category"] == "technical_skills"
            assert (
                analysis["insights"][0]["description"]
                == "Strong TypeScript proficiency demonstrated"
            )

            assert len(analysis["questions"]) > 0
            assert (
                analysis["questions"][0]["question"]
                == "Can you explain your TypeScript adoption strategy?"
            )

            assert len(analysis["recommendations"]) > 0
            assert analysis["recommendations"][0]["type"] == "strength"

            # Verify counts match
            assert analysis["insights_count"] == len(analysis["insights"])
            assert analysis["questions_count"] == len(analysis["questions"])
            assert analysis["recommendations_count"] == len(analysis["recommendations"])
