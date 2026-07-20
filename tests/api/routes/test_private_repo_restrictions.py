"""
Test suite for private repository access restrictions.

This module tests that private repository analysis is not supported
for any subscription plan (public repos only strategy).
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import status

from github_analyzer.database.models import SubscriptionPlan
from github_analyzer.database.operations import UserOperations


class TestPrivateRepoRestrictions:
    """Test that private repository analysis is blocked for all subscription plans."""

    @pytest.fixture
    async def free_user(self, test_db):
        """Create a user with FREE plan."""
        async with test_db() as db_session:
            user = await UserOperations.create_user(
                db_session,
                email="free@example.com",
                password="TestPassword123!",
                full_name="Free User",
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
                email="basic@example.com",
                password="TestPassword123!",
                full_name="Basic User",
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
                email="professional@example.com",
                password="TestPassword123!",
                full_name="Professional User",
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
                email="enterprise@example.com",
                password="TestPassword123!",
                full_name="Enterprise User",
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

    @pytest.fixture
    def mock_github_fetcher_private(self):
        """Create mock GitHubFetcher that returns private repository."""
        mock_fetcher = Mock()
        # Mock the size check
        mock_fetcher.check_repository_size.return_value = {
            "size_kb": 1000,
            "file_count": 50,
        }
        # Mock the repository data
        mock_fetcher.fetch_repository_data.return_value = Mock(
            name="private-repo",
            full_name="user/private-repo",
            size=1000,
            languages={"Python": 100},
            is_private=True,  # This is the key - marking it as private
            description="A private repository",
            stars=10,
            forks=5,
            created_at="2023-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
            default_branch="main",
            has_readme=True,
            has_license=True,
            has_ci=True,
            commits_count=50,
            contributors_count=2,
            # Add required attributes for TimeoutManager
            file_structure=[],
            metrics=Mock(total_commits=50, unique_contributors=2),
        )
        return mock_fetcher

    @pytest.fixture
    def mock_github_fetcher_public(self):
        """Create mock GitHubFetcher that returns public repository."""
        mock_fetcher = Mock()
        # Mock the size check
        mock_fetcher.check_repository_size.return_value = {
            "size_kb": 1000,
            "file_count": 50,
        }
        # Mock the repository data
        mock_fetcher.fetch_repository_data.return_value = Mock(
            name="public-repo",
            full_name="user/public-repo",
            size=1000,
            languages={"Python": 100},
            is_private=False,  # Public repository
            description="A public repository",
            stars=10,
            forks=5,
            created_at="2023-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
            default_branch="main",
            has_readme=True,
            has_license=True,
            has_ci=True,
            commits_count=50,
            contributors_count=2,
            # Add required attributes for TimeoutManager
            file_structure=[],
            metrics=Mock(total_commits=50, unique_contributors=2),
        )
        return mock_fetcher

    @pytest.mark.asyncio
    async def test_free_user_blocked_private_repo(
        self, async_client, free_user, mock_github_fetcher_private
    ):
        """Test that FREE plan users cannot analyze private repositories (all users blocked)."""
        headers = await self._get_auth_headers(async_client, free_user.email)

        from github_analyzer.api.dependencies import (
            get_github_fetcher,
            get_user_repo_size_limit,
        )

        async_client.app.dependency_overrides[get_github_fetcher] = lambda: (
            mock_github_fetcher_private
        )
        async_client.app.dependency_overrides[get_user_repo_size_limit] = (
            lambda: 50  # Free plan limit
        )

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

            response = await async_client.post(
                "/api/v1/analyze",
                json={
                    "repository_url": "https://github.com/user/private-repo",
                    "context": "general",
                },
                headers=headers,
            )

            assert response.status_code == status.HTTP_403_FORBIDDEN
            data = response.json()
            assert (
                data["detail"]["error"] == "Private repository analysis not supported"
            )
            assert data["detail"]["is_private"] is True
            assert data["detail"]["current_plan"] == "FREE"

    @pytest.mark.asyncio
    async def test_basic_user_blocked_private_repo(
        self, async_client, basic_user, mock_github_fetcher_private
    ):
        """Test that BASIC plan users cannot analyze private repositories."""
        headers = await self._get_auth_headers(async_client, basic_user.email)

        from github_analyzer.api.dependencies import (
            get_github_fetcher,
            get_user_repo_size_limit,
        )

        async_client.app.dependency_overrides[get_github_fetcher] = lambda: (
            mock_github_fetcher_private
        )
        async_client.app.dependency_overrides[get_user_repo_size_limit] = (
            lambda: 100  # Basic plan limit
        )

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

            response = await async_client.post(
                "/api/v1/analyze",
                json={
                    "repository_url": "https://github.com/user/private-repo",
                    "context": "general",
                },
                headers=headers,
            )

            assert response.status_code == status.HTTP_403_FORBIDDEN
            data = response.json()
            assert (
                data["detail"]["error"] == "Private repository analysis not supported"
            )
            assert data["detail"]["is_private"] is True
            assert data["detail"]["current_plan"] == "BASIC"

    @pytest.mark.asyncio
    async def test_professional_user_blocked_private_repo(
        self, async_client, professional_user, mock_github_fetcher_private
    ):
        """Test that PROFESSIONAL plan users cannot analyze private repositories (all users blocked)."""
        headers = await self._get_auth_headers(async_client, professional_user.email)

        from github_analyzer.api.dependencies import (
            get_github_fetcher,
            get_user_repo_size_limit,
        )

        async_client.app.dependency_overrides[get_github_fetcher] = lambda: (
            mock_github_fetcher_private
        )
        async_client.app.dependency_overrides[get_user_repo_size_limit] = (
            lambda: 500  # Professional plan limit
        )

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

            response = await async_client.post(
                "/api/v1/analyze",
                json={
                    "repository_url": "https://github.com/user/private-repo",
                    "context": "general",
                },
                headers=headers,
            )

            assert response.status_code == status.HTTP_403_FORBIDDEN
            data = response.json()
            assert (
                data["detail"]["error"] == "Private repository analysis not supported"
            )
            assert data["detail"]["is_private"] is True
            assert data["detail"]["current_plan"] == "PROFESSIONAL"

    @pytest.mark.asyncio
    async def test_enterprise_user_blocked_private_repo(
        self, async_client, enterprise_user, mock_github_fetcher_private
    ):
        """Test that ENTERPRISE plan users cannot analyze private repositories (all users blocked)."""
        headers = await self._get_auth_headers(async_client, enterprise_user.email)

        from github_analyzer.api.dependencies import (
            get_github_fetcher,
            get_user_repo_size_limit,
        )

        async_client.app.dependency_overrides[get_github_fetcher] = lambda: (
            mock_github_fetcher_private
        )
        async_client.app.dependency_overrides[get_user_repo_size_limit] = (
            lambda: 1000  # Enterprise plan limit
        )

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

            response = await async_client.post(
                "/api/v1/analyze",
                json={
                    "repository_url": "https://github.com/user/private-repo",
                    "context": "general",
                },
                headers=headers,
            )

            assert response.status_code == status.HTTP_403_FORBIDDEN
            data = response.json()
            assert (
                data["detail"]["error"] == "Private repository analysis not supported"
            )
            assert data["detail"]["is_private"] is True
            assert data["detail"]["current_plan"] == "ENTERPRISE"

    @pytest.mark.asyncio
    async def test_all_users_allowed_public_repo(
        self, async_client, free_user, mock_github_fetcher_public
    ):
        """Test that all plan users can analyze public repositories."""
        headers = await self._get_auth_headers(async_client, free_user.email)

        from github_analyzer.api.dependencies import (
            get_github_fetcher,
            get_user_repo_size_limit,
        )

        async_client.app.dependency_overrides[get_github_fetcher] = lambda: (
            mock_github_fetcher_public
        )
        async_client.app.dependency_overrides[get_user_repo_size_limit] = (
            lambda: 50  # Free plan limit
        )

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

            with patch(
                "github_analyzer.api.routes.analysis._perform_repository_analysis"
            ) as mock_analysis:
                from github_analyzer.api.models.responses import AnalysisResponse

                mock_analysis.return_value = AnalysisResponse(
                    repository_url="https://github.com/user/public-repo",
                    context="general",
                    analysis={
                        "executive_summary": "Public repo analysis",
                        "overall_recommendation": "HIRE",
                        "confidence_score": 80,
                    },
                    metadata={
                        "ai_analysis_used": False,
                        "analysis_cost_usd": 0.0,
                        "cached": False,
                        "response_time_seconds": 1.0,
                    },
                )

                response = await async_client.post(
                    "/api/v1/analyze",
                    json={
                        "repository_url": "https://github.com/user/public-repo",
                        "context": "general",
                    },
                    headers=headers,
                )

                # FREE users can analyze public repos
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["repository_url"] == "https://github.com/user/public-repo"
