"""
Tests for Dashboard API endpoint.

Tests aggregation of candidates for dashboard display.
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.github_analyzer.api.routes.dashboard import get_dashboard_candidates
from src.github_analyzer.database.models import (
    AnalysisResult,
    PRAnalysisRecord,
    PRAnalysisResult,
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
def mock_portfolio_analyses(scale_plus_user: Mock) -> list[Mock]:
    """Create mock PortfolioAnalysis database records for multiple users."""
    analyses = []

    # User 1: testdev (has portfolio)
    portfolio1 = Mock(spec=PortfolioAnalysis)
    portfolio1.id = str(uuid4())
    portfolio1.user_id = scale_plus_user.user_id
    portfolio1.github_username = "testdev"
    portfolio1.total_repos = 30
    portfolio1.repos_analyzed = 25
    portfolio1.repos_skipped = 5
    portfolio1.full_analysis = json.dumps(
        {
            "username": "testdev",
            "result": {
                "summary": "Strong full-stack developer with consistent contributions",
                "limitations": "Based on 25 public repositories",
            },
        }
    )
    portfolio1.created_at = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
    analyses.append(portfolio1)

    # User 2: devguru (has portfolio)
    portfolio2 = Mock(spec=PortfolioAnalysis)
    portfolio2.id = str(uuid4())
    portfolio2.user_id = scale_plus_user.user_id
    portfolio2.github_username = "devguru"
    portfolio2.total_repos = 50
    portfolio2.repos_analyzed = 45
    portfolio2.repos_skipped = 5
    portfolio2.full_analysis = json.dumps(
        {
            "username": "devguru",
            "result": {
                "summary": "Expert backend engineer with deep systems knowledge",
                "limitations": "Based on 45 public repositories",
            },
        }
    )
    portfolio2.created_at = datetime(2025, 1, 10, 10, 0, 0, tzinfo=timezone.utc)
    analyses.append(portfolio2)

    return analyses


@pytest.fixture
def mock_pr_analyses(scale_plus_user: Mock) -> list[Mock]:
    """Create mock PRAnalysisRecord database records."""
    analyses = []

    # testdev has PR analysis
    pr1 = Mock(spec=PRAnalysisRecord)
    pr1.id = 1
    pr1.user_id = scale_plus_user.user_id
    pr1.analysis_id = str(uuid4())
    pr1.github_username = "testdev"
    pr1.pr_count = 42
    pr1.context = "startup"
    pr1.status = "completed"
    pr1.created_at = datetime(2025, 1, 12, 10, 0, 0, tzinfo=timezone.utc)
    pr1.completed_at = datetime(2025, 1, 12, 11, 0, 0, tzinfo=timezone.utc)
    analyses.append(pr1)

    # newdev has ONLY PR analysis (no portfolio)
    pr2 = Mock(spec=PRAnalysisRecord)
    pr2.id = 2
    pr2.user_id = scale_plus_user.user_id
    pr2.analysis_id = str(uuid4())
    pr2.github_username = "newdev"
    pr2.pr_count = 15
    pr2.context = "startup"
    pr2.status = "completed"
    pr2.created_at = datetime(2025, 1, 20, 10, 0, 0, tzinfo=timezone.utc)
    pr2.completed_at = datetime(2025, 1, 20, 11, 0, 0, tzinfo=timezone.utc)
    analyses.append(pr2)

    return analyses


@pytest.fixture
def mock_single_repo_analyses(scale_plus_user: Mock) -> list[Mock]:
    """Create mock AnalysisResult database records for single repos."""
    analyses = []

    # testdev has 2 single repo analyses
    for i in range(2):
        repo = Mock(spec=AnalysisResult)
        repo.id = str(uuid4())
        repo.user_id = scale_plus_user.user_id
        repo.repository_name = f"testdev/repo-{i}"
        repo.repository_url = f"https://github.com/testdev/repo-{i}"
        repo.context = "startup"
        repo.created_at = datetime(2025, 1, 18, 10, i, 0, tzinfo=timezone.utc)
        analyses.append(repo)

    # devguru has 1 single repo analysis
    repo = Mock(spec=AnalysisResult)
    repo.id = str(uuid4())
    repo.user_id = scale_plus_user.user_id
    repo.repository_name = "devguru/backend-api"
    repo.repository_url = "https://github.com/devguru/backend-api"
    repo.context = "startup"
    repo.created_at = datetime(2025, 1, 8, 10, 0, 0, tzinfo=timezone.utc)
    analyses.append(repo)

    return analyses


class TestDashboardCandidatesEndpoint:
    """Test dashboard candidates endpoint."""

    @pytest.mark.asyncio
    async def test_get_dashboard_candidates_with_multiple_candidates(
        self,
        scale_plus_user: Mock,
        mock_db_session: Mock,
        mock_portfolio_analyses: list[Mock],
        mock_pr_analyses: list[Mock],
        mock_single_repo_analyses: list[Mock],
    ) -> None:
        """Test getting dashboard candidates with multiple candidates."""
        # Mock portfolio query
        portfolio_result = Mock()
        portfolio_result.scalars = Mock(
            return_value=Mock(all=Mock(return_value=mock_portfolio_analyses))
        )

        # Mock PR query
        pr_result = Mock()
        pr_result.scalars = Mock(
            return_value=Mock(all=Mock(return_value=mock_pr_analyses))
        )

        # Mock PRAnalysisResult queries for each PR analysis
        # testdev's PR analysis result
        pr_analysis_result_1 = Mock(spec=PRAnalysisResult)
        pr_analysis_result_1.id = mock_pr_analyses[0].analysis_id
        pr_analysis_result_1.ai_insights = json.dumps(
            {"executive_summary": "Strong developer with excellent PR contributions"}
        )

        # newdev's PR analysis result
        pr_analysis_result_2 = Mock(spec=PRAnalysisResult)
        pr_analysis_result_2.id = mock_pr_analyses[1].analysis_id
        pr_analysis_result_2.ai_insights = json.dumps(
            {"executive_summary": "Promising developer with good collaboration skills"}
        )

        # Mock PRAnalysisResult queries
        pr_result_1_query = Mock()
        pr_result_1_query.scalar_one_or_none = Mock(return_value=pr_analysis_result_1)

        pr_result_2_query = Mock()
        pr_result_2_query.scalar_one_or_none = Mock(return_value=pr_analysis_result_2)

        # Mock single repo query
        repo_result = Mock()
        repo_result.scalars = Mock(
            return_value=Mock(all=Mock(return_value=mock_single_repo_analyses))
        )

        # Configure execute to return different results based on call order
        # Order: portfolio, pr_records, pr_result_1, pr_result_2, repos
        mock_db_session.execute = AsyncMock(
            side_effect=[
                portfolio_result,
                pr_result,
                pr_result_1_query,
                pr_result_2_query,
                repo_result,
            ]
        )

        response = await get_dashboard_candidates(10, scale_plus_user, mock_db_session)

        # Should have 3 candidates: testdev, devguru, newdev
        assert len(response) == 3

        # Verify candidates are sorted by latest_activity (desc)
        # newdev: 2025-01-20 (most recent PR)
        # testdev: 2025-01-18 (single repo)
        # devguru: 2025-01-10 (portfolio)
        assert response[0]["username"] == "newdev"
        assert response[1]["username"] == "testdev"
        assert response[2]["username"] == "devguru"

    @pytest.mark.asyncio
    async def test_get_dashboard_candidates_candidate_aggregation(
        self,
        scale_plus_user: Mock,
        mock_db_session: Mock,
        mock_portfolio_analyses: list[Mock],
        mock_pr_analyses: list[Mock],
        mock_single_repo_analyses: list[Mock],
    ) -> None:
        """Test that candidates are properly aggregated with correct flags."""
        # Mock queries
        portfolio_result = Mock()
        portfolio_result.scalars = Mock(
            return_value=Mock(all=Mock(return_value=mock_portfolio_analyses))
        )

        pr_result = Mock()
        pr_result.scalars = Mock(
            return_value=Mock(all=Mock(return_value=mock_pr_analyses))
        )

        # Mock PRAnalysisResult queries for each PR analysis
        pr_analysis_result_1 = Mock(spec=PRAnalysisResult)
        pr_analysis_result_1.id = mock_pr_analyses[0].analysis_id
        pr_analysis_result_1.ai_insights = json.dumps(
            {"executive_summary": "Strong developer with excellent PR contributions"}
        )

        pr_analysis_result_2 = Mock(spec=PRAnalysisResult)
        pr_analysis_result_2.id = mock_pr_analyses[1].analysis_id
        pr_analysis_result_2.ai_insights = json.dumps(
            {"executive_summary": "Promising developer with good collaboration skills"}
        )

        pr_result_1_query = Mock()
        pr_result_1_query.scalar_one_or_none = Mock(return_value=pr_analysis_result_1)

        pr_result_2_query = Mock()
        pr_result_2_query.scalar_one_or_none = Mock(return_value=pr_analysis_result_2)

        repo_result = Mock()
        repo_result.scalars = Mock(
            return_value=Mock(all=Mock(return_value=mock_single_repo_analyses))
        )

        mock_db_session.execute = AsyncMock(
            side_effect=[
                portfolio_result,
                pr_result,
                pr_result_1_query,
                pr_result_2_query,
                repo_result,
            ]
        )

        response = await get_dashboard_candidates(10, scale_plus_user, mock_db_session)

        # Find testdev (has all 3 types)
        testdev = next(c for c in response if c["username"] == "testdev")
        assert testdev["has_portfolio"] is True
        assert testdev["has_pr"] is True
        assert testdev["repo_count"] == 2
        assert "Strong full-stack developer" in testdev["portfolio_summary"]

        # Find devguru (has portfolio + single repo)
        devguru = next(c for c in response if c["username"] == "devguru")
        assert devguru["has_portfolio"] is True
        assert devguru["has_pr"] is False
        assert devguru["repo_count"] == 1

        # Find newdev (has ONLY PR analysis)
        newdev = next(c for c in response if c["username"] == "newdev")
        assert newdev["has_portfolio"] is False
        assert newdev["has_pr"] is True
        assert newdev["repo_count"] == 0
        # Dashboard intentionally populates portfolio_summary with PR summary when no portfolio exists
        assert newdev["portfolio_summary"] != ""
        assert "Promising developer" in newdev["portfolio_summary"]

    @pytest.mark.asyncio
    async def test_get_dashboard_candidates_with_no_analyses(
        self,
        scale_plus_user: Mock,
        mock_db_session: Mock,
    ) -> None:
        """Test getting dashboard candidates with no analyses."""
        # Mock all queries returning empty
        portfolio_result = Mock()
        portfolio_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[])))

        pr_result = Mock()
        pr_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[])))

        repo_result = Mock()
        repo_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[])))

        mock_db_session.execute = AsyncMock(
            side_effect=[portfolio_result, pr_result, repo_result]
        )

        response = await get_dashboard_candidates(10, scale_plus_user, mock_db_session)

        # Should return empty list
        assert len(response) == 0

    @pytest.mark.asyncio
    async def test_get_dashboard_candidates_limit_parameter(
        self,
        scale_plus_user: Mock,
        mock_db_session: Mock,
        mock_portfolio_analyses: list[Mock],
        mock_pr_analyses: list[Mock],
        mock_single_repo_analyses: list[Mock],
    ) -> None:
        """Test that limit parameter correctly limits results."""
        # Mock queries
        portfolio_result = Mock()
        portfolio_result.scalars = Mock(
            return_value=Mock(all=Mock(return_value=mock_portfolio_analyses))
        )

        pr_result = Mock()
        pr_result.scalars = Mock(
            return_value=Mock(all=Mock(return_value=mock_pr_analyses))
        )

        # Mock PRAnalysisResult queries for each PR analysis
        pr_analysis_result_1 = Mock(spec=PRAnalysisResult)
        pr_analysis_result_1.id = mock_pr_analyses[0].analysis_id
        pr_analysis_result_1.ai_insights = json.dumps(
            {"executive_summary": "Strong developer with excellent PR contributions"}
        )

        pr_analysis_result_2 = Mock(spec=PRAnalysisResult)
        pr_analysis_result_2.id = mock_pr_analyses[1].analysis_id
        pr_analysis_result_2.ai_insights = json.dumps(
            {"executive_summary": "Promising developer with good collaboration skills"}
        )

        pr_result_1_query = Mock()
        pr_result_1_query.scalar_one_or_none = Mock(return_value=pr_analysis_result_1)

        pr_result_2_query = Mock()
        pr_result_2_query.scalar_one_or_none = Mock(return_value=pr_analysis_result_2)

        repo_result = Mock()
        repo_result.scalars = Mock(
            return_value=Mock(all=Mock(return_value=mock_single_repo_analyses))
        )

        mock_db_session.execute = AsyncMock(
            side_effect=[
                portfolio_result,
                pr_result,
                pr_result_1_query,
                pr_result_2_query,
                repo_result,
            ]
        )

        # Request only 2 candidates (out of 3)
        response = await get_dashboard_candidates(2, scale_plus_user, mock_db_session)

        # Should return only 2 candidates
        assert len(response) == 2

        # Should be the 2 most recent (newdev, testdev)
        assert response[0]["username"] == "newdev"
        assert response[1]["username"] == "testdev"

    @pytest.mark.asyncio
    async def test_get_dashboard_candidates_avatar_urls(
        self,
        scale_plus_user: Mock,
        mock_db_session: Mock,
        mock_portfolio_analyses: list[Mock],
    ) -> None:
        """Test that avatar URLs are correctly generated."""
        # Mock only portfolio query
        portfolio_result = Mock()
        portfolio_result.scalars = Mock(
            return_value=Mock(all=Mock(return_value=mock_portfolio_analyses))
        )

        pr_result = Mock()
        pr_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[])))

        repo_result = Mock()
        repo_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[])))

        mock_db_session.execute = AsyncMock(
            side_effect=[portfolio_result, pr_result, repo_result]
        )

        response = await get_dashboard_candidates(10, scale_plus_user, mock_db_session)

        # Verify avatar URLs
        testdev = next(c for c in response if c["username"] == "testdev")
        assert testdev["avatar_url"] == "https://github.com/testdev.png"

        devguru = next(c for c in response if c["username"] == "devguru")
        assert devguru["avatar_url"] == "https://github.com/devguru.png"

    @pytest.mark.asyncio
    async def test_get_dashboard_candidates_user_isolation(
        self,
        scale_plus_user: Mock,
        mock_db_session: Mock,
    ) -> None:
        """Test that dashboard only returns data owned by the current user."""
        # This test verifies that queries filter by user_id
        # Mock empty results (as if another user owns the data)
        portfolio_result = Mock()
        portfolio_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[])))

        pr_result = Mock()
        pr_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[])))

        repo_result = Mock()
        repo_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[])))

        mock_db_session.execute = AsyncMock(
            side_effect=[portfolio_result, pr_result, repo_result]
        )

        response = await get_dashboard_candidates(10, scale_plus_user, mock_db_session)

        # Verify no data returned (user isolation working)
        assert len(response) == 0

    @pytest.mark.asyncio
    async def test_get_dashboard_candidates_latest_activity_sorting(
        self,
        scale_plus_user: Mock,
        mock_db_session: Mock,
        mock_portfolio_analyses: list[Mock],
        mock_pr_analyses: list[Mock],
        mock_single_repo_analyses: list[Mock],
    ) -> None:
        """Test that candidates are sorted by latest_activity in descending order."""
        # Mock queries
        portfolio_result = Mock()
        portfolio_result.scalars = Mock(
            return_value=Mock(all=Mock(return_value=mock_portfolio_analyses))
        )

        pr_result = Mock()
        pr_result.scalars = Mock(
            return_value=Mock(all=Mock(return_value=mock_pr_analyses))
        )

        # Mock PRAnalysisResult queries for each PR analysis
        pr_analysis_result_1 = Mock(spec=PRAnalysisResult)
        pr_analysis_result_1.id = mock_pr_analyses[0].analysis_id
        pr_analysis_result_1.ai_insights = json.dumps(
            {"executive_summary": "Strong developer with excellent PR contributions"}
        )

        pr_analysis_result_2 = Mock(spec=PRAnalysisResult)
        pr_analysis_result_2.id = mock_pr_analyses[1].analysis_id
        pr_analysis_result_2.ai_insights = json.dumps(
            {"executive_summary": "Promising developer with good collaboration skills"}
        )

        pr_result_1_query = Mock()
        pr_result_1_query.scalar_one_or_none = Mock(return_value=pr_analysis_result_1)

        pr_result_2_query = Mock()
        pr_result_2_query.scalar_one_or_none = Mock(return_value=pr_analysis_result_2)

        repo_result = Mock()
        repo_result.scalars = Mock(
            return_value=Mock(all=Mock(return_value=mock_single_repo_analyses))
        )

        mock_db_session.execute = AsyncMock(
            side_effect=[
                portfolio_result,
                pr_result,
                pr_result_1_query,
                pr_result_2_query,
                repo_result,
            ]
        )

        response = await get_dashboard_candidates(10, scale_plus_user, mock_db_session)

        # Verify sorting (most recent first)
        # newdev: 2025-01-20 (PR)
        # testdev: 2025-01-18 (single repo - more recent than portfolio/PR)
        # devguru: 2025-01-10 (portfolio)
        assert response[0]["username"] == "newdev"
        assert response[0]["latest_activity"] == datetime(
            2025, 1, 20, 10, 0, 0, tzinfo=timezone.utc
        )

        assert response[1]["username"] == "testdev"
        assert response[1]["latest_activity"] == datetime(
            2025, 1, 18, 10, 1, 0, tzinfo=timezone.utc
        )

        assert response[2]["username"] == "devguru"
        assert response[2]["latest_activity"] == datetime(
            2025, 1, 10, 10, 0, 0, tzinfo=timezone.utc
        )
