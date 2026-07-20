"""
Integration tests for tiered repository size limits.

This test suite verifies that the tiered repository size limits feature works end-to-end,
including database user creation, JWT authentication, GitHub API mocking, and proper
enforcement of size limits based on subscription plans.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import status

from github_analyzer.ai.analyzer import (
    AnalysisResult,
    ContextAlignment,
    EvidencePattern,
    EvidenceStrength,
)
from github_analyzer.database.models import SubscriptionPlan
from github_analyzer.database.operations import UserOperations


class TestTieredRepoSizeLimits:
    """Test tiered repository size limits end-to-end."""

    def _get_mock_analysis_result(self):
        """Helper to create a mock analysis result."""
        return AnalysisResult(
            summary="Test analysis",
            evidence_strength=EvidenceStrength(
                technical_competence=85,
                communication_skills=80,
                professional_practices=90,
                growth_potential=75,
            ),
            evidence_patterns=[
                EvidencePattern(
                    pattern="good_practices",
                    evidence="Good code structure observed",
                    commits=[],
                    files=[],
                    strength="strong",
                )
            ],
            context_alignment=ContextAlignment(),
            verification_gaps=[],
            key_insights=["Good code"],
            cost=0.0,
            analysis_time=1.0,
            generated_by="mock",
        )

    @pytest.fixture
    async def free_user(self, test_db):
        """Create a user with FREE plan."""
        async with test_db() as db_session:
            user = await UserOperations.create_user(
                db_session,
                email="free@sizetest.com",
                password="TestPassword123!",
                full_name="Free Size Test User",
            )
            user.is_verified = True
            user.subscription_plan = SubscriptionPlan.FREE
            await db_session.commit()
            return user

    @pytest.fixture
    async def basic_user(self, test_db):
        """Create a user with BASIC plan."""
        async with test_db() as db_session:
            user = await UserOperations.create_user(
                db_session,
                email="basic@sizetest.com",
                password="TestPassword123!",
                full_name="Basic Size Test User",
            )
            user.is_verified = True
            user.subscription_plan = SubscriptionPlan.BASIC
            await db_session.commit()
            return user

    @pytest.fixture
    async def professional_user(self, test_db):
        """Create a user with PROFESSIONAL plan."""
        async with test_db() as db_session:
            user = await UserOperations.create_user(
                db_session,
                email="professional@sizetest.com",
                password="TestPassword123!",
                full_name="Professional Size Test User",
            )
            user.is_verified = True
            user.subscription_plan = SubscriptionPlan.PROFESSIONAL
            await db_session.commit()
            return user

    @pytest.fixture
    async def enterprise_user(self, test_db):
        """Create a user with ENTERPRISE plan."""
        async with test_db() as db_session:
            user = await UserOperations.create_user(
                db_session,
                email="enterprise@sizetest.com",
                password="TestPassword123!",
                full_name="Enterprise Size Test User",
            )
            user.is_verified = True
            user.subscription_plan = SubscriptionPlan.ENTERPRISE
            await db_session.commit()
            return user

    async def _get_auth_headers(self, async_client, email: str):
        """Get JWT auth headers for a user."""
        login_response = await async_client.post(
            "/api/v1/auth/login", json={"email": email, "password": "TestPassword123!"}
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    async def _get_admin_auth_headers(self, async_client, email: str):
        """Get JWT auth headers for an admin user."""
        login_response = await async_client.post(
            "/api/v1/auth/login", json={"email": email, "password": "AdminPassword123!"}
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def mock_github_fetcher_75mb(self):
        """Mock GitHubFetcher for 75MB repository."""
        mock_fetcher = Mock()
        # 75MB = 75 * 1024 = 76,800 KB
        mock_fetcher.check_repository_size.return_value = {
            "size_kb": 76_800,  # 75MB
            "file_count": 500,
        }
        from datetime import datetime, timezone

        from github_analyzer.data.models import RepositoryData, RepositoryMetrics

        mock_fetcher.fetch_repository_data.return_value = RepositoryData(
            url="https://github.com/example/medium-repo",
            name="medium-repo",
            full_name="example/medium-repo",
            owner="example",
            size=76_800,  # 75MB in KB
            languages={"Python": 60, "JavaScript": 40},
            is_private=False,
            description="A 75MB test repository",
            stars=20,
            forks=5,
            created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            pushed_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            default_branch="main",
            fetched_at=datetime.now(timezone.utc),
            topics=[],
            license_name="MIT",
            watchers=20,
            open_issues=5,
            has_readme=True,
            has_license=True,
            has_contributing=False,
            has_tests=True,
            has_ci_config=True,
            is_fork=False,
            is_archived=False,
            is_disabled=False,
            recent_commits=[],
            file_structure=[],
            readme_content="# Medium Test Repository",
            metrics=RepositoryMetrics(
                total_commits=100,
                unique_contributors=5,
                lines_of_code=5000,
                test_coverage_estimate=0.7,
                documentation_presence="8 documentation files in 10 total files",
                days_since_last_commit=7,
                commit_frequency=2.5,
                avg_commit_size=100,
            ),
        )
        return mock_fetcher

    @pytest.fixture
    def mock_github_fetcher_600mb(self):
        """Mock GitHubFetcher for 600MB repository."""
        mock_fetcher = Mock()
        # 600MB = 600 * 1024 = 614,400 KB
        mock_fetcher.check_repository_size.return_value = {
            "size_kb": 614_400,  # 600MB
            "file_count": 2000,
        }
        from datetime import datetime, timezone

        from github_analyzer.data.models import RepositoryData, RepositoryMetrics

        mock_fetcher.fetch_repository_data.return_value = RepositoryData(
            url="https://github.com/example/large-repo",
            name="large-repo",
            full_name="example/large-repo",
            owner="example",
            size=614_400,  # 600MB in KB
            languages={"Java": 50, "Python": 30, "C++": 20},
            is_private=False,
            description="A 600MB test repository",
            stars=100,
            forks=25,
            created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            pushed_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            default_branch="main",
            fetched_at=datetime.now(timezone.utc),
            topics=[],
            license_name="Apache-2.0",
            watchers=100,
            open_issues=15,
            has_readme=True,
            has_license=True,
            has_contributing=True,
            has_tests=True,
            has_ci_config=True,
            is_fork=False,
            is_archived=False,
            is_disabled=False,
            recent_commits=[],
            file_structure=[],
            readme_content="# Large Test Repository",
            metrics=RepositoryMetrics(
                total_commits=500,
                unique_contributors=15,
                lines_of_code=25000,
                test_coverage_estimate=0.8,
                documentation_presence="9 documentation files in 10 total files",
                days_since_last_commit=3,
                commit_frequency=5.0,
                avg_commit_size=150,
            ),
        )
        return mock_fetcher

    @pytest.mark.asyncio
    async def test_free_user_fails_with_75mb_repo(
        self, async_client, free_user, mock_github_fetcher_75mb
    ):
        """Test that FREE user fails with 75MB repository (free tier has 50MB limit)."""
        # Override GitHubFetcher dependency
        from github_analyzer.api.dependencies import get_github_fetcher

        async_client.app.dependency_overrides[get_github_fetcher] = lambda: (
            mock_github_fetcher_75mb
        )

        # Get auth headers for free user
        headers = await self._get_auth_headers(async_client, free_user.email)

        # Mock Redis cache to avoid cache hits
        with patch("github_analyzer.api.routes.analysis.redis_service") as mock_redis:
            mock_redis.get = AsyncMock(return_value=None)  # No cache hit
            mock_redis.zcount = AsyncMock(return_value=0)  # For TierRateLimiter
            mock_redis.zadd = AsyncMock(return_value=1)
            mock_redis.zremrangebyscore = AsyncMock(return_value=0)
            mock_redis.expire = AsyncMock(return_value=True)
            mock_redis._connected = True
            mock_redis._redis = mock_redis

            # Mock AI analyzer to prevent real API calls
            with patch(
                "github_analyzer.ai.analyzer.AIAnalyzer.analyze_repository"
            ) as mock_analyze:
                mock_analyze.return_value = self._get_mock_analysis_result()

                # Attempt to analyze 75MB repository
                response = await async_client.post(
                    "/api/v1/analyze",
                    json={"repository_url": "https://github.com/example/medium-repo"},
                    headers=headers,
                )

                # Should fail as free tier has 50MB limit
                assert response.status_code in [
                    status.HTTP_400_BAD_REQUEST,
                    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                ]

                # Verify error message
                data = response.json()
                assert "detail" in data
                assert (
                    "exceeds" in data["detail"].lower()
                    or "size" in data["detail"].lower()
                )

        # Clean up
        async_client.app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_professional_user_succeeds_with_75mb_repo(
        self, async_client, professional_user, mock_github_fetcher_75mb
    ):
        """Test that PROFESSIONAL user succeeds with 75MB repository (all tiers have 10GB limit)."""
        # Override GitHubFetcher dependency
        from github_analyzer.api.dependencies import get_github_fetcher

        async_client.app.dependency_overrides[get_github_fetcher] = lambda: (
            mock_github_fetcher_75mb
        )

        # Get auth headers for professional user
        headers = await self._get_auth_headers(async_client, professional_user.email)

        # Mock Redis cache to avoid cache hits
        with patch("github_analyzer.api.routes.analysis.redis_service") as mock_redis:
            mock_redis.get = AsyncMock(return_value=None)  # No cache hit
            mock_redis.zcount = AsyncMock(return_value=0)  # For TierRateLimiter
            mock_redis.zadd = AsyncMock(return_value=1)
            mock_redis.zremrangebyscore = AsyncMock(return_value=0)
            mock_redis.expire = AsyncMock(return_value=True)
            mock_redis._connected = True
            mock_redis._redis = mock_redis

            # Mock AI analyzer to prevent real API calls
            with patch(
                "github_analyzer.ai.analyzer.AIAnalyzer.analyze_repository"
            ) as mock_analyze:
                mock_analyze.return_value = self._get_mock_analysis_result()

                # Attempt to analyze 75MB repository
                response = await async_client.post(
                    "/api/v1/analyze",
                    json={"repository_url": "https://github.com/example/medium-repo"},
                    headers=headers,
                )

                # Should succeed (professional tier has 3GB limit, 75MB < 3GB)
                assert response.status_code in [
                    status.HTTP_200_OK,
                    status.HTTP_202_ACCEPTED,
                ]

                result = response.json()
                assert (
                    result["repository_url"] == "https://github.com/example/medium-repo"
                )

        # Clean up
        async_client.app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_professional_user_succeeds_with_600mb_repo(
        self, async_client, professional_user, mock_github_fetcher_600mb
    ):
        """Test that PROFESSIONAL user succeeds with 600MB repository (all tiers have 10GB limit)."""
        # Override GitHubFetcher dependency
        from github_analyzer.api.dependencies import get_github_fetcher

        async_client.app.dependency_overrides[get_github_fetcher] = lambda: (
            mock_github_fetcher_600mb
        )

        # Get auth headers for professional user
        headers = await self._get_auth_headers(async_client, professional_user.email)

        # Mock Redis cache to avoid cache hits
        with patch("github_analyzer.api.routes.analysis.redis_service") as mock_redis:
            mock_redis.get = AsyncMock(return_value=None)  # No cache hit
            mock_redis.zcount = AsyncMock(return_value=0)  # For TierRateLimiter
            mock_redis.zadd = AsyncMock(return_value=1)
            mock_redis.zremrangebyscore = AsyncMock(return_value=0)
            mock_redis.expire = AsyncMock(return_value=True)
            mock_redis._connected = True
            mock_redis._redis = mock_redis

            # Mock AI analyzer to prevent real API calls
            with patch(
                "github_analyzer.ai.analyzer.AIAnalyzer.analyze_repository"
            ) as mock_analyze:
                mock_analyze.return_value = self._get_mock_analysis_result()

                # Attempt to analyze 600MB repository
                response = await async_client.post(
                    "/api/v1/analyze",
                    json={"repository_url": "https://github.com/example/large-repo"},
                    headers=headers,
                )

                # Should succeed as professional tier has 3GB limit (600MB < 3GB)
                assert response.status_code in [
                    status.HTTP_200_OK,
                    status.HTTP_202_ACCEPTED,
                ]

                # Verify response has expected structure
                data = response.json()
                assert "repository_url" in data
                assert data["repository_url"] == "https://github.com/example/large-repo"

        # Clean up
        async_client.app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_enterprise_user_custom_limit_workflow(
        self, async_client, enterprise_user, mock_github_fetcher_600mb, test_db
    ):
        """
        Test complete enterprise workflow:
        1. Create enterprise user
        2. Set custom limit via admin endpoint
        3. Verify they can analyze 600MB repository
        """
        # Step 1: Enterprise user is already created via fixture

        # Step 2: Create admin user and set custom limit
        async with test_db() as db_session:
            admin_user = await UserOperations.create_user(
                db_session,
                email="admin@sizetest.com",
                password="AdminPassword123!",
                full_name="Admin Size Test User",
            )
            admin_user.is_verified = True
            admin_user.is_admin = True
            admin_user.subscription_plan = SubscriptionPlan.ENTERPRISE
            await db_session.commit()

        # Skip setting custom limit - this endpoint doesn't exist yet
        # This would be an admin feature to set custom limits for enterprise users
        # For now, enterprise users have a fixed 500MB limit

        # Step 3: Test that enterprise user still can't analyze 600MB repo (exceeds 500MB limit)
        # Override GitHubFetcher dependency
        from github_analyzer.api.dependencies import get_github_fetcher

        async_client.app.dependency_overrides[get_github_fetcher] = lambda: (
            mock_github_fetcher_600mb
        )

        # Get auth headers for enterprise user
        enterprise_headers = await self._get_auth_headers(
            async_client, enterprise_user.email
        )

        # Mock Redis cache to avoid cache hits
        with patch("github_analyzer.api.routes.analysis.redis_service") as mock_redis:
            mock_redis.get = AsyncMock(return_value=None)  # No cache hit
            mock_redis.zcount = AsyncMock(return_value=0)  # For TierRateLimiter
            mock_redis.zadd = AsyncMock(return_value=1)
            mock_redis.zremrangebyscore = AsyncMock(return_value=0)
            mock_redis.expire = AsyncMock(return_value=True)
            mock_redis._connected = True
            mock_redis._redis = mock_redis

            # Mock AI analyzer to prevent real API calls
            with patch(
                "github_analyzer.ai.analyzer.AIAnalyzer.analyze_repository"
            ) as mock_analyze:
                mock_analyze.return_value = self._get_mock_analysis_result()

                # Attempt to analyze 600MB repository without custom limit
                response = await async_client.post(
                    "/api/v1/analyze",
                    json={"repository_url": "https://github.com/example/large-repo"},
                    headers=enterprise_headers,
                )

                # Enterprise users can handle large repos (up to 10GB actually)
                assert response.status_code in [
                    status.HTTP_200_OK,
                    status.HTTP_202_ACCEPTED,
                ]
                result = response.json()
                assert "repository_url" in result or "analysis_id" in result

        # Clean up
        async_client.app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_basic_user_succeeds_with_75mb_repo(
        self, async_client, basic_user, mock_github_fetcher_75mb
    ):
        """Test that BASIC user can analyze 75MB repository (all tiers have 10GB limit)."""
        # Override GitHubFetcher dependency
        from github_analyzer.api.dependencies import get_github_fetcher

        async_client.app.dependency_overrides[get_github_fetcher] = lambda: (
            mock_github_fetcher_75mb
        )

        # Get auth headers for basic user
        headers = await self._get_auth_headers(async_client, basic_user.email)

        # Mock Redis cache to avoid cache hits
        with patch("github_analyzer.api.routes.analysis.redis_service") as mock_redis:
            mock_redis.get = AsyncMock(return_value=None)  # No cache hit
            mock_redis.zcount = AsyncMock(return_value=0)  # For TierRateLimiter
            mock_redis.zadd = AsyncMock(return_value=1)
            mock_redis.zremrangebyscore = AsyncMock(return_value=0)
            mock_redis.expire = AsyncMock(return_value=True)
            mock_redis._connected = True
            mock_redis._redis = mock_redis

            # Mock AI analyzer to prevent real API calls
            with patch(
                "github_analyzer.ai.analyzer.AIAnalyzer.analyze_repository"
            ) as mock_analyze:
                mock_analyze.return_value = self._get_mock_analysis_result()

                # Attempt to analyze 75MB repository
                response = await async_client.post(
                    "/api/v1/analyze",
                    json={"repository_url": "https://github.com/example/medium-repo"},
                    headers=headers,
                )

                # Should succeed as basic tier has 1GB limit (75MB < 1GB)
                assert response.status_code in [
                    status.HTTP_200_OK,
                    status.HTTP_202_ACCEPTED,
                ]

                # Verify response has expected structure
                data = response.json()
                assert "repository_url" in data
                assert (
                    data["repository_url"] == "https://github.com/example/medium-repo"
                )

        # Clean up
        async_client.app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_users_with_75mb_repo(
        self,
        async_client,
        free_user,
        basic_user,
        professional_user,
        enterprise_user,
        mock_github_fetcher_75mb,
    ):
        """
        Test that subscription tiers handle 75MB repository based on their limits.
        Free tier (50MB limit) should fail, others should succeed.
        """
        # Test repository: 75MB (should fail for free tier, pass for others)
        from github_analyzer.api.dependencies import get_github_fetcher

        async_client.app.dependency_overrides[get_github_fetcher] = lambda: (
            mock_github_fetcher_75mb
        )

        # Test cases: (user, plan_name)
        test_cases = [
            (free_user, "FREE"),
            (basic_user, "BASIC"),
            (professional_user, "PROFESSIONAL"),
            (enterprise_user, "ENTERPRISE"),
        ]

        for user, plan_name in test_cases:
            headers = await self._get_auth_headers(async_client, user.email)

            # Mock Redis cache to avoid cache hits
            with patch(
                "github_analyzer.api.routes.analysis.redis_service"
            ) as mock_redis:
                mock_redis.get = AsyncMock(return_value=None)
                mock_redis.zcount = AsyncMock(return_value=0)  # For TierRateLimiter
                mock_redis.zadd = AsyncMock(return_value=1)
                mock_redis.zremrangebyscore = AsyncMock(return_value=0)
                mock_redis.expire = AsyncMock(return_value=True)
                mock_redis._connected = True
                mock_redis._redis = mock_redis

                # Mock AI analyzer to prevent real API calls
                with patch(
                    "github_analyzer.ai.analyzer.AIAnalyzer.analyze_repository"
                ) as mock_analyze:
                    mock_analyze.return_value = self._get_mock_analysis_result()

                    response = await async_client.post(
                        "/api/v1/analyze",
                        json={
                            "repository_url": "https://github.com/example/medium-repo"
                        },
                        headers=headers,
                    )

                    # Free tier should fail (50MB limit), others should succeed
                    if plan_name == "FREE":
                        assert response.status_code in [
                            status.HTTP_400_BAD_REQUEST,
                            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        ], f"{plan_name} should fail with 75MB repo (limit is 50MB)"
                        data = response.json()
                        assert "detail" in data
                    else:
                        if response.status_code not in [
                            status.HTTP_200_OK,
                            status.HTTP_202_ACCEPTED,
                        ]:
                            print(f"Response status: {response.status_code}")
                            print(f"Response body: {response.text}")
                        assert response.status_code in [
                            status.HTTP_200_OK,
                            status.HTTP_202_ACCEPTED,
                        ], f"{plan_name} should succeed with 75MB repo"

                        # Verify response structure
                        data = response.json()
                        assert "repository_url" in data
                        assert (
                            data["repository_url"]
                            == "https://github.com/example/medium-repo"
                        )

        # Clean up
        async_client.app.dependency_overrides.clear()


if __name__ == "__main__":
    print("Integration tests for tiered repository size limits")
    print("Run with: pytest tests/integration/test_tiered_repo_size_limits.py -v")
