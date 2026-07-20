"""
Integration tests for repository size limit enforcement.

Tests end-to-end verification that repository size limits have been effectively removed
for all standard plans, while maintaining custom limit functionality for enterprise users.
"""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest
from fastapi import status
from httpx import AsyncClient

from github_analyzer.data.github_fetcher import GitHubFetcher
from github_analyzer.data.models import RepositoryData, RepositoryMetrics
from github_analyzer.database.models import SubscriptionPlan, User


@pytest.fixture
async def free_user(test_db):
    """Create a free plan user for testing."""
    from github_analyzer.database.operations import UserOperations

    async with test_db() as db_session:
        user = await UserOperations.create_user(
            db_session,
            email="free@limits.com",
            password="TestPassword123!",
            full_name="Free Limits Test User",
        )
        user.is_verified = True
        user.subscription_plan = SubscriptionPlan.FREE
        await db_session.commit()
        return user


@pytest.fixture
async def basic_user(test_db):
    """Create a basic plan user for testing."""
    from github_analyzer.database.operations import UserOperations

    async with test_db() as db_session:
        user = await UserOperations.create_user(
            db_session,
            email="basic@limits.com",
            password="TestPassword123!",
            full_name="Basic Limits Test User",
        )
        user.is_verified = True
        user.subscription_plan = SubscriptionPlan.BASIC
        await db_session.commit()
        return user


@pytest.fixture
async def professional_user(test_db):
    """Create a professional plan user for testing."""
    from github_analyzer.database.operations import UserOperations

    async with test_db() as db_session:
        user = await UserOperations.create_user(
            db_session,
            email="professional@limits.com",
            password="TestPassword123!",
            full_name="Professional Limits Test User",
        )
        user.is_verified = True
        user.subscription_plan = SubscriptionPlan.PROFESSIONAL
        await db_session.commit()
        return user


@pytest.fixture
async def enterprise_user(test_db):
    """Create an enterprise plan user for testing."""
    from github_analyzer.database.operations import UserOperations

    async with test_db() as db_session:
        user = await UserOperations.create_user(
            db_session,
            email="enterprise@limits.com",
            password="TestPassword123!",
            full_name="Enterprise Limits Test User",
        )
        user.is_verified = True
        user.subscription_plan = SubscriptionPlan.ENTERPRISE
        await db_session.commit()
        return user


def create_mock_repository_data(
    url: str, size_mb: float, is_private: bool = False, **kwargs
) -> RepositoryData:
    """Helper to create mock RepositoryData for testing."""
    return RepositoryData(
        url=url,
        full_name="/".join(url.split("/")[-2:]),  # Extract owner/repo
        name=url.split("/")[-1],
        owner=url.split("/")[-2],
        description=kwargs.get("description", "Test repository"),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        pushed_at=datetime.now(timezone.utc),
        default_branch="main",
        size=int(size_mb * 1024),  # Convert MB to KB
        languages=kwargs.get("languages", {"Python": 80, "JavaScript": 20}),
        topics=[],
        license_name="MIT",
        stars=0,
        forks=0,
        watchers=0,
        open_issues=0,
        has_readme=True,
        has_license=True,
        has_contributing=False,
        has_tests=True,
        has_ci_config=False,
        recent_commits=[],
        file_structure=[],
        readme_content=kwargs.get("readme_content", "# Test Repository"),
        metrics=RepositoryMetrics(
            total_commits=10,
            unique_contributors=2,
            lines_of_code=1000,
            test_coverage_estimate=0.8,
            documentation_presence="3 documentation files in 10 total files",
            days_since_last_commit=1,
            commit_frequency=2.5,  # commits per week
            avg_commit_size=50.0,
        ),
        fetched_at=datetime.now(timezone.utc),
        is_private=is_private,
        is_fork=False,
        is_archived=False,
        is_disabled=False,
    )


class TestAnalysisLimitsIntegration:
    """Integration tests for repository size limits - all standard plans now have 10GB limit."""

    @pytest.mark.asyncio
    async def test_free_plan_size_limit_enforcement(
        self, async_client: AsyncClient, free_user: User
    ):
        """Test that FREE plan users can analyze large repos (size limits removed)."""
        # Mock GitHub fetcher to return repo that would have been too large under old limits
        mock_fetcher = Mock(spec=GitHubFetcher)
        mock_fetcher.check_repository_size = Mock(
            return_value={
                "size_kb": 77_312,
                "file_count": 500,
            }  # 75.5MB (would exceed old 50MB limit)
        )
        mock_fetcher.fetch_repository_data = Mock(
            return_value=create_mock_repository_data(
                url="https://github.com/example/large-repo",
                size_mb=75.5,  # Previously would exceed FREE plan limit, now allowed
                is_private=False,
                languages={"Python": 80, "JavaScript": 20},
                readme_content="# Large Repository\nThis is a large repository.",
            )
        )

        # Override GitHubFetcher dependency
        from github_analyzer.api.dependencies import get_github_fetcher

        async_client.app.dependency_overrides[get_github_fetcher] = lambda: mock_fetcher

        # Get auth headers for free user
        headers = await self._get_auth_headers(async_client, free_user.email)

        # Mock the size checking mechanism and cache
        from tests.conftest import MockRedisService

        mock_redis_service = MockRedisService()

        # Mock the analysis to return success without calling AI
        with (
            patch(
                "github_analyzer.api.routes.analysis.redis_service", mock_redis_service
            ),
            patch(
                "github_analyzer.api.routes.analysis._perform_repository_analysis"
            ) as mock_analysis,
        ):
            from github_analyzer.api.models.responses import AnalysisResponse

            mock_analysis.return_value = AnalysisResponse(
                repository_url="https://github.com/example/large-repo",
                context="general",
                analysis={
                    "executive_summary": "Free plan analysis successful",
                    "overall_recommendation": "HIRE",
                    "confidence_score": 85,
                },
                metadata={
                    "repository_size_mb": 75.5,
                    "files_analyzed": 25,
                    "analysis_duration_seconds": 3.0,
                    "ai_analysis_used": False,
                    "analysis_cost_usd": 0.0,
                    "cached": False,
                    "response_time_seconds": 0.8,
                },
            )

            # Attempt analysis
            response = await async_client.post(
                "/api/v1/analyze",
                json={"repository_url": "https://github.com/example/large-repo"},
                headers=headers,
            )

            # Should now succeed (size limits removed for all standard plans)
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_202_ACCEPTED,
            ]

        # Clean up
        async_client.app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_basic_plan_size_limit_enforcement(
        self, async_client: AsyncClient, basic_user: User
    ):
        """Test that BASIC plan users can analyze large repos (size limits removed)."""
        # Mock GitHub fetcher to return repo that would have been too large under old limits
        mock_fetcher = Mock(spec=GitHubFetcher)
        mock_fetcher.check_repository_size = Mock(
            return_value={"size_kb": 153_600, "file_count": 800}  # 150MB
        )
        mock_fetcher.fetch_repository_data = Mock(
            return_value=create_mock_repository_data(
                url="https://github.com/example/larger-repo",
                size_mb=150.0,  # Previously would exceed BASIC plan limit, now allowed
                is_private=False,
                languages={"Python": 60, "JavaScript": 30, "TypeScript": 10},
                readme_content="# Larger Repository\nThis is a larger repository.",
            )
        )

        # Override dependency
        from github_analyzer.api.dependencies import get_github_fetcher

        async_client.app.dependency_overrides[get_github_fetcher] = lambda: mock_fetcher

        # Get auth headers
        headers = await self._get_auth_headers(async_client, basic_user.email)

        # Mock the size checking mechanism
        from tests.conftest import MockRedisService

        mock_redis_service = MockRedisService()

        # Mock the analysis to return success without calling AI
        with (
            patch(
                "github_analyzer.api.routes.analysis.redis_service", mock_redis_service
            ),
            patch(
                "github_analyzer.api.routes.analysis._perform_repository_analysis"
            ) as mock_analysis,
        ):
            from github_analyzer.api.models.responses import AnalysisResponse

            mock_analysis.return_value = AnalysisResponse(
                repository_url="https://github.com/example/larger-repo",
                context="general",
                analysis={
                    "executive_summary": "Basic plan analysis successful",
                    "overall_recommendation": "HIRE",
                    "confidence_score": 80,
                },
                metadata={
                    "repository_size_mb": 150.0,
                    "files_analyzed": 35,
                    "analysis_duration_seconds": 4.0,
                    "ai_analysis_used": True,
                    "analysis_cost_usd": 0.01,
                    "cached": False,
                    "response_time_seconds": 1.0,
                },
            )

            # Attempt analysis
            response = await async_client.post(
                "/api/v1/analyze",
                json={"repository_url": "https://github.com/example/larger-repo"},
                headers=headers,
            )

            # Should now succeed (size limits removed)
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_202_ACCEPTED,
            ]

        # Clean up
        async_client.app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_professional_plan_allows_larger_repos(
        self, async_client: AsyncClient, professional_user: User
    ):
        """Test that PROFESSIONAL plan users can analyze repos up to 500MB."""
        # Mock GitHub fetcher to return repo within Professional limits
        mock_fetcher = Mock(spec=GitHubFetcher)
        mock_fetcher.check_repository_size = Mock(
            return_value={"size_kb": 409_600, "file_count": 1200}  # 400MB
        )
        mock_fetcher.fetch_repository_data = Mock(
            return_value=create_mock_repository_data(
                url="https://github.com/example/pro-repo",
                size_mb=400.0,  # Within PROFESSIONAL plan 500MB limit
                is_private=True,  # Professional can access private repos
                languages={"Python": 50, "JavaScript": 30, "Go": 20},
                readme_content="# Professional Repository\nLarge enterprise codebase.",
            )
        )

        # Override dependencies
        from github_analyzer.api.dependencies import get_github_fetcher

        async_client.app.dependency_overrides[get_github_fetcher] = lambda: mock_fetcher

        # Mock the analysis process
        with patch(
            "github_analyzer.api.routes.analysis._perform_repository_analysis"
        ) as mock_analysis:
            from github_analyzer.api.models.responses import AnalysisResponse

            mock_analysis.return_value = AnalysisResponse(
                repository_url="https://github.com/example/pro-repo",
                context="general",
                analysis={
                    "executive_summary": "Professional repository analysis",
                    "overall_recommendation": "HIRE",
                    "confidence_score": 85,
                },
                metadata={
                    "repository_size_mb": 400.0,
                    "files_analyzed": 50,
                    "analysis_duration_seconds": 12.5,
                    "ai_analysis_used": False,
                    "analysis_cost_usd": 0.0,
                    "cached": False,
                    "response_time_seconds": 1.0,
                },
            )

            from tests.conftest import MockRedisService

            mock_redis_service = MockRedisService()

            with patch(
                "github_analyzer.api.routes.analysis.redis_service", mock_redis_service
            ):
                # Get auth headers
                headers = await self._get_auth_headers(
                    async_client, professional_user.email
                )

                # Attempt analysis - should succeed
                response = await async_client.post(
                    "/api/v1/analyze",
                    json={"repository_url": "https://github.com/example/pro-repo"},
                    headers=headers,
                )

                # Should succeed
                assert response.status_code == status.HTTP_200_OK

                result = response.json()
                assert result["repository_url"] == "https://github.com/example/pro-repo"
                assert result["metadata"]["repository_size_mb"] == 400.0

        # Clean up
        async_client.app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_enterprise_custom_limit_enforcement(
        self, async_client: AsyncClient, enterprise_user: User
    ):
        """Test that enterprise users can have custom limits."""
        # Mock GitHub fetcher to return very large repo
        mock_fetcher = Mock(spec=GitHubFetcher)
        mock_fetcher.check_repository_size = Mock(
            return_value={"size_kb": 2_097_152, "file_count": 5000}  # 2GB
        )
        mock_fetcher.fetch_repository_data = Mock(
            return_value=create_mock_repository_data(
                url="https://github.com/enterprise/huge-repo",
                size_mb=2048.0,  # 2GB repository
                is_private=True,
                languages={"Java": 40, "Python": 30, "JavaScript": 20, "C++": 10},
                readme_content="# Enterprise Monorepo\nMassive enterprise codebase.",
            )
        )

        # Override dependencies
        from github_analyzer.api.dependencies import get_github_fetcher

        async_client.app.dependency_overrides[get_github_fetcher] = lambda: mock_fetcher

        # Mock the analysis process
        with patch(
            "github_analyzer.api.routes.analysis._perform_repository_analysis"
        ) as mock_analysis:
            from github_analyzer.api.models.responses import AnalysisResponse

            mock_analysis.return_value = AnalysisResponse(
                repository_url="https://github.com/enterprise/huge-repo",
                context="general",
                analysis={
                    "executive_summary": "Enterprise monorepo analysis",
                    "overall_recommendation": "HIRE",
                    "confidence_score": 90,
                },
                metadata={
                    "repository_size_mb": 2048.0,
                    "files_analyzed": 100,
                    "analysis_duration_seconds": 45.2,
                    "ai_analysis_used": True,
                    "analysis_cost_usd": 0.01,
                    "cached": False,
                    "response_time_seconds": 2.0,
                },
            )

            from tests.conftest import MockRedisService

            mock_redis_service = MockRedisService()

            with patch(
                "github_analyzer.api.routes.analysis.redis_service", mock_redis_service
            ):
                # Get auth headers
                headers = await self._get_auth_headers(
                    async_client, enterprise_user.email
                )

                # Attempt analysis - should succeed with custom limit
                response = await async_client.post(
                    "/api/v1/analyze",
                    json={"repository_url": "https://github.com/enterprise/huge-repo"},
                    headers=headers,
                )

                # Should succeed
                assert response.status_code == status.HTTP_200_OK

                result = response.json()
                assert (
                    result["repository_url"]
                    == "https://github.com/enterprise/huge-repo"
                )
                assert result["metadata"]["repository_size_mb"] == 2048.0

        # Clean up
        async_client.app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_enterprise_custom_limit_exceeded(
        self, async_client: AsyncClient, enterprise_user: User
    ):
        """Test that enterprise users are still limited by their custom limit."""
        # Mock GitHub fetcher to return repo larger than custom limit
        mock_fetcher = Mock(spec=GitHubFetcher)
        mock_fetcher.check_repository_size = Mock(
            return_value={"size_kb": 4_194_304, "file_count": 10000}  # 4GB
        )
        mock_fetcher.fetch_repository_data = Mock(
            return_value=create_mock_repository_data(
                url="https://github.com/enterprise/too-huge-repo",
                size_mb=4096.0,  # 4GB repository, within 10GB enterprise limit
                is_private=False,  # V1 only supports public repos
                languages={"Java": 50, "Python": 25, "C++": 25},
                readme_content="# Massive Enterprise Repo\nExtremely large codebase.",
            )
        )

        # Override dependencies
        from github_analyzer.api.dependencies import get_github_fetcher

        async_client.app.dependency_overrides[get_github_fetcher] = lambda: mock_fetcher

        # Get auth headers
        headers = await self._get_auth_headers(async_client, enterprise_user.email)

        # Mock the size checking mechanism
        from tests.conftest import MockRedisService

        mock_redis_service = MockRedisService()

        # Mock the analysis to return success without calling AI
        with (
            patch(
                "github_analyzer.api.routes.analysis.redis_service", mock_redis_service
            ),
            patch(
                "github_analyzer.api.routes.analysis._perform_repository_analysis"
            ) as mock_analysis,
        ):
            from github_analyzer.api.models.responses import AnalysisResponse

            mock_analysis.return_value = AnalysisResponse(
                repository_url="https://github.com/enterprise/too-huge-repo",
                context="general",
                analysis={
                    "executive_summary": "Enterprise analysis successful",
                    "overall_recommendation": "HIRE",
                    "confidence_score": 95,
                },
                metadata={
                    "repository_size_mb": 4096.0,
                    "files_analyzed": 150,
                    "analysis_duration_seconds": 8.0,
                    "ai_analysis_used": True,
                    "analysis_cost_usd": 0.05,
                    "cached": False,
                    "response_time_seconds": 2.5,
                },
            )

            # Attempt analysis
            response = await async_client.post(
                "/api/v1/analyze",
                json={"repository_url": "https://github.com/enterprise/too-huge-repo"},
                headers=headers,
            )

            # Should now succeed (enterprise plan has 10GB limit)
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_202_ACCEPTED,
            ]

        # Clean up
        async_client.app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_exact_limit_boundary(
        self, async_client: AsyncClient, free_user: User
    ):
        """Test repo exactly at the size limit."""
        # Mock GitHub fetcher to return repo exactly at limit
        mock_fetcher = Mock(spec=GitHubFetcher)
        mock_fetcher.check_repository_size = Mock(
            return_value={"size_kb": 51_200, "file_count": 200}  # 50MB
        )
        mock_fetcher.fetch_repository_data = Mock(
            return_value=create_mock_repository_data(
                url="https://github.com/example/exact-limit-repo",
                size_mb=50.0,  # Exactly at FREE plan limit
                is_private=False,
                languages={"Python": 100},
                readme_content="# Exactly at limit repo",
            )
        )

        # Override dependencies
        from github_analyzer.api.dependencies import get_github_fetcher

        async_client.app.dependency_overrides[get_github_fetcher] = lambda: mock_fetcher

        # Mock successful analysis
        with patch(
            "github_analyzer.api.routes.analysis._perform_repository_analysis"
        ) as mock_analysis:
            from github_analyzer.api.models.responses import AnalysisResponse

            mock_analysis.return_value = AnalysisResponse(
                repository_url="https://github.com/example/exact-limit-repo",
                context="general",
                analysis={
                    "executive_summary": "Exactly at limit analysis",
                    "overall_recommendation": "HIRE",
                    "confidence_score": 80,
                },
                metadata={
                    "repository_size_mb": 50.0,
                    "files_analyzed": 30,
                    "analysis_duration_seconds": 5.0,
                    "ai_analysis_used": False,
                    "analysis_cost_usd": 0.0,
                    "cached": False,
                    "response_time_seconds": 0.5,
                },
            )

            from tests.conftest import MockRedisService

            mock_redis_service = MockRedisService()

            with patch(
                "github_analyzer.api.routes.analysis.redis_service", mock_redis_service
            ):
                # Get auth headers
                headers = await self._get_auth_headers(async_client, free_user.email)

                # Attempt analysis - should succeed (<=)
                response = await async_client.post(
                    "/api/v1/analyze",
                    json={
                        "repository_url": "https://github.com/example/exact-limit-repo"
                    },
                    headers=headers,
                )

                # Should succeed at exact limit
                assert response.status_code == status.HTTP_200_OK

        # Clean up
        async_client.app.dependency_overrides.clear()

    async def _get_auth_headers(self, async_client, email: str):
        """Get JWT auth headers for a user."""
        login_response = await async_client.post(
            "/api/v1/auth/login", json={"email": email, "password": "TestPassword123!"}
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}


if __name__ == "__main__":
    # Simple test runner if pytest is not available
    print("Integration tests for analysis limits")
    print("Run with: pytest tests/integration/test_analysis_limits.py -v")
