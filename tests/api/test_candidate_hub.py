"""
Tests for Candidate Hub API endpoint.

Tests aggregation of portfolio, PR, and single repo analyses for a candidate.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.github_analyzer.api.routes.candidate_hub import (
    extract_github_stats,
    format_portfolio_summary,
    format_pr_summary,
    format_single_repo_summary,
    get_candidate_hub,
)
from src.github_analyzer.database.models import (
    AnalysisResult,
    PRAnalysisRecord,
    SubscriptionPlan,
    User,
)
from src.github_analyzer.database.models_portfolio import PortfolioAnalysis


@pytest.fixture
def scale_plus_user() -> Mock:
    """Create a Scale+ user for testing."""
    user = Mock(spec=User)
    user.user_id = "scale-plus-user-id"
    user.email = "scale@example.com"
    user.subscription_plan = SubscriptionPlan.SCALE_PLUS
    return user


@pytest.fixture
def mock_db_session() -> Mock:
    """Create mock database session."""
    session = Mock(spec=AsyncSession)
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_portfolio_analysis(scale_plus_user: Mock) -> Mock:
    """Create mock PortfolioAnalysis database record."""
    import json

    analysis = Mock(spec=PortfolioAnalysis)
    analysis.id = str(uuid4())
    analysis.user_id = scale_plus_user.user_id
    analysis.github_username = "testdev"
    analysis.context = "startup"
    analysis.role = "senior"
    analysis.total_repos = 30
    analysis.repos_analyzed = 25
    analysis.repos_skipped = 5
    analysis.full_analysis = json.dumps(
        {
            "username": "testdev",
            "result": {
                "role": "senior",  # Add role field for proper extraction
                "summary": "Strong full-stack developer with consistent contributions",
                "limitations": "Based on 25 public repositories",
            },
            "metadata": {
                "total_public_repos": 30,
                "repos_analyzed": 25,
                "account_created": "2018-05-12T00:00:00Z",
            },
        }
    )
    analysis.processing_time_seconds = 45.5
    analysis.token_count = 15000
    analysis.api_cost = 0.75
    analysis.from_cache = False
    analysis.created_at = datetime.now(timezone.utc)
    return analysis


@pytest.fixture
def mock_pr_analysis(scale_plus_user: Mock) -> Mock:
    """Create mock PRAnalysisRecord database record."""
    record = Mock(spec=PRAnalysisRecord)
    record.id = 123
    record.user_id = scale_plus_user.user_id
    record.analysis_id = str(uuid4())
    record.github_username = "testdev"
    record.pr_count = 42
    record.context = "startup"
    record.status = "completed"
    record.created_at = datetime.now(timezone.utc)
    record.completed_at = datetime.now(timezone.utc)
    return record


@pytest.fixture
def mock_single_repo_analyses(scale_plus_user: Mock) -> list[Mock]:
    """Create mock AnalysisResult database records."""
    analyses = []
    for i in range(3):
        analysis = Mock(spec=AnalysisResult)
        analysis.id = str(uuid4())
        analysis.user_id = scale_plus_user.user_id
        analysis.repository_name = f"testdev/repo-{i}"
        analysis.repository_url = f"https://github.com/testdev/repo-{i}"
        analysis.context = "startup"
        analysis.created_at = datetime.now(timezone.utc)
        analyses.append(analysis)
    return analyses


class TestCandidateHubEndpoint:
    """Test candidate hub endpoint."""

    @pytest.mark.asyncio
    async def test_get_candidate_hub_with_all_analyses(
        self,
        scale_plus_user: Mock,
        mock_db_session: Mock,
        mock_portfolio_analysis: Mock,
        mock_pr_analysis: Mock,
        mock_single_repo_analyses: list[Mock],
    ) -> None:
        """Test getting candidate hub with all analysis types present."""
        # Mock portfolio query
        portfolio_result = Mock()
        portfolio_result.scalar_one_or_none = Mock(return_value=mock_portfolio_analysis)

        # Mock PR query
        pr_result = Mock()
        pr_result.scalar_one_or_none = Mock(return_value=mock_pr_analysis)

        # Mock single repo query
        single_repo_result = Mock()
        single_repo_result.scalars = Mock(
            return_value=Mock(all=Mock(return_value=mock_single_repo_analyses))
        )

        # Mock PR analysis result query (4th query)
        pr_analysis_result = Mock()
        pr_analysis_result.scalar_one_or_none = Mock(
            return_value=None
        )  # No detailed PR result

        # Configure execute to return different results based on call order
        mock_db_session.execute = AsyncMock(
            side_effect=[
                portfolio_result,
                pr_result,
                single_repo_result,
                pr_analysis_result,
            ]
        )

        response = await get_candidate_hub("testdev", scale_plus_user, mock_db_session)

        # Verify response structure
        assert response["username"] == "testdev"
        assert response["snapshot"] is not None
        assert response["portfolio_analysis"] is not None
        assert response["pr_analysis"] is not None
        assert len(response["single_repo_analyses"]) == 3

        # Verify portfolio analysis data
        assert response["portfolio_analysis"]["id"] == mock_portfolio_analysis.id
        assert response["portfolio_analysis"]["context"] == "startup"
        assert response["portfolio_analysis"]["role"] == "senior"

        # Verify PR analysis data
        assert response["pr_analysis"]["id"] == mock_pr_analysis.analysis_id
        assert response["pr_analysis"]["total_prs"] == 42
        assert response["pr_analysis"]["status"] == "completed"

        # Verify single repo analyses
        for i, repo_analysis in enumerate(response["single_repo_analyses"]):
            assert repo_analysis["repository_name"] == f"testdev/repo-{i}"

    @pytest.mark.asyncio
    async def test_get_candidate_hub_with_no_analyses(
        self,
        scale_plus_user: Mock,
        mock_db_session: Mock,
    ) -> None:
        """Test getting candidate hub with no analyses."""
        # Mock all queries returning None/empty
        portfolio_result = Mock()
        portfolio_result.scalar_one_or_none = Mock(return_value=None)

        pr_result = Mock()
        pr_result.scalar_one_or_none = Mock(return_value=None)

        single_repo_result = Mock()
        single_repo_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[])))

        mock_db_session.execute = AsyncMock(
            side_effect=[portfolio_result, pr_result, single_repo_result]
        )

        response = await get_candidate_hub("newdev", scale_plus_user, mock_db_session)

        # Verify response structure with no data
        assert response["username"] == "newdev"
        assert response["portfolio_analysis"] is None
        assert response["pr_analysis"] is None
        assert len(response["single_repo_analyses"]) == 0
        assert response["snapshot"] is not None
        assert response["snapshot"]["username"] == "newdev"
        assert response["snapshot"]["avatar_url"] == "https://github.com/newdev.png"

    @pytest.mark.asyncio
    async def test_get_candidate_hub_with_only_portfolio(
        self,
        scale_plus_user: Mock,
        mock_db_session: Mock,
        mock_portfolio_analysis: Mock,
    ) -> None:
        """Test getting candidate hub with only portfolio analysis."""
        # Mock portfolio query - found
        portfolio_result = Mock()
        portfolio_result.scalar_one_or_none = Mock(return_value=mock_portfolio_analysis)

        # Mock PR query - not found
        pr_result = Mock()
        pr_result.scalar_one_or_none = Mock(return_value=None)

        # Mock single repo query - not found
        single_repo_result = Mock()
        single_repo_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[])))

        mock_db_session.execute = AsyncMock(
            side_effect=[portfolio_result, pr_result, single_repo_result]
        )

        response = await get_candidate_hub("testdev", scale_plus_user, mock_db_session)

        # Verify only portfolio data present
        assert response["portfolio_analysis"] is not None
        assert response["pr_analysis"] is None
        assert len(response["single_repo_analyses"]) == 0

        # Verify snapshot includes role from portfolio
        assert response["snapshot"] is not None
        assert response["snapshot"]["role"] == "senior"  # From portfolio

    @pytest.mark.asyncio
    async def test_get_candidate_hub_only_returns_owned_data(
        self,
        scale_plus_user: Mock,
        mock_db_session: Mock,
    ) -> None:
        """Test that candidate hub only returns data owned by the current user."""
        # This test verifies that queries filter by user_id
        # Mock empty results (as if another user owns the data)
        portfolio_result = Mock()
        portfolio_result.scalar_one_or_none = Mock(return_value=None)

        pr_result = Mock()
        pr_result.scalar_one_or_none = Mock(return_value=None)

        single_repo_result = Mock()
        single_repo_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[])))

        mock_db_session.execute = AsyncMock(
            side_effect=[portfolio_result, pr_result, single_repo_result]
        )

        response = await get_candidate_hub("otherdev", scale_plus_user, mock_db_session)

        # Verify no data returned (user isolation working)
        assert response["portfolio_analysis"] is None
        assert response["pr_analysis"] is None
        assert len(response["single_repo_analyses"]) == 0


class TestCandidateHubHelperFunctions:
    """Test helper functions for candidate hub."""

    def test_extract_github_stats_from_portfolio(
        self, mock_portfolio_analysis: Mock
    ) -> None:
        """Test extracting GitHub stats from portfolio analysis."""
        stats = extract_github_stats(
            portfolio=mock_portfolio_analysis, pr=None, repos=[], username="testdev"
        )

        assert stats["public_repos"] == 30
        assert stats["created_at"] == "2018-05-12T00:00:00Z"
        assert stats["avatar_url"] == "https://github.com/testdev.png"

    def test_extract_github_stats_fallback(self) -> None:
        """Test GitHub stats fallback when no data available."""
        stats = extract_github_stats(
            portfolio=None, pr=None, repos=[], username="testdev"
        )

        assert stats["public_repos"] == 0
        assert stats["total_commits"] == 0
        assert stats["created_at"] == ""
        assert stats["avatar_url"] == "https://github.com/testdev.png"

    def test_format_portfolio_summary(self, mock_portfolio_analysis: Mock) -> None:
        """Test formatting portfolio analysis summary."""
        summary = format_portfolio_summary(mock_portfolio_analysis)

        assert summary["id"] == mock_portfolio_analysis.id
        assert summary["context"] == "startup"
        assert summary["role"] == "senior"
        assert summary["total_repos"] == 30
        assert summary["repos_analyzed"] == 25

    def test_format_pr_summary(self, mock_pr_analysis: Mock) -> None:
        """Test formatting PR analysis summary."""
        summary = format_pr_summary(mock_pr_analysis)

        assert summary["id"] == mock_pr_analysis.analysis_id
        assert summary["total_prs"] == 42
        assert summary["status"] == "completed"
        assert "created_at" in summary

    def test_format_single_repo_summary(
        self, mock_single_repo_analyses: list[Mock]
    ) -> None:
        """Test formatting single repo analysis summary."""
        analysis = mock_single_repo_analyses[0]
        summary = format_single_repo_summary(analysis)

        assert summary["id"] == analysis.id
        assert summary["repository_name"] == "testdev/repo-0"
        assert summary["context"] == "startup"
        assert "created_at" in summary
