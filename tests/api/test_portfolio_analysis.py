"""
Tests for Portfolio Analysis API endpoints.

Tests full integration including eligibility checks, candidate tracking,
AI insights generation, and caching.
"""

from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.github_analyzer.api.routes.portfolio_analysis import (
    PORTFOLIO_ANALYSIS_TIERS,
    analyze_portfolio,
    check_user_eligibility,
    format_analysis_response,
    get_cached_analysis,
    get_portfolio_analysis_by_id,
    get_portfolio_usage,
    list_portfolio_analyses,
)
from src.github_analyzer.database.models import SubscriptionPlan, User
from src.github_analyzer.database.models_portfolio import (
    CandidateAssessment,
    PortfolioAnalysis,
)


@pytest.fixture
def scale_plus_user() -> Mock:
    """Create a Scale+ user eligible for portfolio analysis."""
    user = Mock(spec=User)
    user.user_id = "scale-plus-user-id"
    user.email = "scale@example.com"
    user.subscription_plan = SubscriptionPlan.SCALE_PLUS
    return user


@pytest.fixture
def basic_user() -> Mock:
    """Create a Basic tier user eligible for portfolio analysis (10 candidates/month)."""
    user = Mock(spec=User)
    user.user_id = "basic-user-id"
    user.email = "basic@example.com"
    user.subscription_plan = SubscriptionPlan.BASIC
    return user


@pytest.fixture
def professional_user() -> Mock:
    """Create a Professional tier user (50 candidates/month)."""
    user = Mock(spec=User)
    user.user_id = "pro-user-id"
    user.email = "pro@example.com"
    user.subscription_plan = SubscriptionPlan.PROFESSIONAL
    return user


@pytest.fixture
def free_user() -> Mock:
    """Create a Free tier user not eligible for portfolio analysis."""
    user = Mock(spec=User)
    user.user_id = "free-user-id"
    user.email = "free@example.com"
    user.subscription_plan = SubscriptionPlan.FREE
    return user


@pytest.fixture
def mock_db_session() -> Mock:
    """Create mock database session."""
    session = Mock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.add = Mock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def portfolio_request() -> Any:
    """Create portfolio analysis request."""
    from src.github_analyzer.api.models.portfolio_requests import (
        PortfolioAnalyzeRequest,
    )

    return PortfolioAnalyzeRequest(
        github_username="testdev",
        github_token="test-token",
        context="startup",
        max_repos=50,
        force_refresh=False,
    )


@pytest.fixture
def sample_analysis_result() -> Dict[str, Any]:
    """Create sample portfolio analysis result."""
    # Create metadata as a Mock object with attributes (not a dict)
    from unittest.mock import Mock

    metadata_obj = Mock()
    metadata_obj.total_public_repos = 30
    metadata_obj.repos_analyzed = 25
    metadata_obj.repos_skipped = 5
    metadata_obj.skip_counts = {"too_small": 3, "fork": 2}
    metadata_obj.skipped_repos = {"too_small": ["repo1"], "fork": ["repo2"]}
    metadata_obj.analyzed_repos = ["repo3", "repo4"]
    metadata_obj.oldest_repo = "2020-01-01"
    metadata_obj.newest_repo = "2025-03-01"
    metadata_obj.timeline_gaps = []
    metadata_obj.tokens = 15000
    metadata_obj.cost = 0.75

    return {
        "success": True,
        "result": {
            "summary": "Strong full-stack developer with consistent contributions",
            "limitations": "Based on 25 public repositories",
            "observations": ["Active contributor", "Strong in Python/TypeScript"],
            "evolution_periods": [],
            "evidence_patterns": [
                {
                    "pattern": "Consistent Testing Practices",
                    "evidence": "95% of repos have test coverage",
                    "confidence": "High - verified in 24/25 repos",
                }
            ],
            "interview_questions": [
                {
                    "question": "Tell me about your testing philosophy",
                    "category": "technical",
                    "evidence_reference": "95% test coverage",
                }
            ],
            "positive_indicators": ["Strong testing", "Good documentation"],
            "areas_to_explore": ["Scalability patterns"],
            "recommendations": ["Explore distributed systems experience"],
            "quality_indicators": ["Consistent commits", "Clean code"],
            "confidence_explanation": "High confidence based on 25 repositories",
            "model_used": "claude-sonnet-4-20250514",
        },
        "evidence": {
            "total_repos": 30,
            "analyzed_repos": 25,
            "skipped_repos": 5,
        },
        "metadata": metadata_obj,  # Object with attributes, not dict
        "total_analysis_time_seconds": 45.5,
    }


@pytest.fixture
def mock_portfolio_analysis(
    scale_plus_user: Mock, sample_analysis_result: Dict[str, Any]
) -> Mock:
    """Create mock PortfolioAnalysis database record."""
    import json

    # Convert metadata Mock object to JSON serialization-ready format
    metadata = sample_analysis_result["metadata"]
    metadata_dict = {
        "total_public_repos": metadata.total_public_repos,
        "repos_analyzed": metadata.repos_analyzed,
        "repos_skipped": metadata.repos_skipped,
        "skip_counts": metadata.skip_counts,
        "oldest_repo": metadata.oldest_repo,
        "newest_repo": metadata.newest_repo,
        "timeline_gaps": metadata.timeline_gaps,
    }

    analysis = Mock(spec=PortfolioAnalysis)
    analysis.id = str(uuid4())
    analysis.user_id = scale_plus_user.user_id
    analysis.github_username = "testdev"
    analysis.context = "startup"
    analysis.total_repos = 30
    analysis.repos_analyzed = 25
    analysis.repos_skipped = 5
    analysis.full_analysis = json.dumps(
        {
            "username": "testdev",
            "context": "startup",
            "result": sample_analysis_result["result"],
            "evidence": sample_analysis_result["evidence"],
            "metadata": metadata_dict,
        }
    )
    analysis.processing_time_seconds = 45.5
    analysis.token_count = 15000
    analysis.api_cost = 0.75
    analysis.from_cache = False
    analysis.analysis_metadata = json.dumps(metadata_dict)
    analysis.created_at = datetime.now(timezone.utc)
    analysis.cache_expires_at = datetime.now(timezone.utc)
    return analysis


class TestPortfolioEligibility:
    """Test portfolio analysis eligibility checking."""

    @pytest.mark.asyncio
    async def test_check_eligibility_scale_plus_new_candidate(
        self, scale_plus_user: Mock, mock_db_session: Mock
    ) -> None:
        """Test eligibility for Scale+ user with new candidate."""
        with patch(
            "src.github_analyzer.api.routes.portfolio_analysis.CandidateUsageService"
        ) as mock_service_class:
            # Mock the instance
            mock_candidate_service = Mock()
            mock_service_class.return_value = mock_candidate_service

            # Mock get_or_create_assessment - new candidate
            mock_assessment = Mock(spec=CandidateAssessment)
            mock_candidate_service.get_or_create_assessment = AsyncMock(
                return_value=(mock_assessment, True)  # is_new = True
            )

            # Mock monthly usage - well under limit (500 for Scale+)
            mock_candidate_service.get_monthly_usage = AsyncMock(return_value=25)

            # Mock tier limit
            mock_service_class.get_tier_limit = Mock(return_value=500)

            is_eligible, reason = await check_user_eligibility(
                scale_plus_user, "testdev", mock_db_session
            )

            assert is_eligible is True
            assert reason == ""

    @pytest.mark.asyncio
    async def test_check_eligibility_free_tier_rejected(
        self, free_user: Mock, mock_db_session: Mock
    ) -> None:
        """Test that Free tier users are not eligible."""
        is_eligible, reason = await check_user_eligibility(
            free_user, "testdev", mock_db_session
        )

        assert is_eligible is False
        assert "available for paid plans" in reason.lower()
        assert "Free" in reason

    @pytest.mark.asyncio
    async def test_check_eligibility_basic_tier_at_limit(
        self, basic_user: Mock, mock_db_session: Mock
    ) -> None:
        """Test Basic user at monthly candidate limit (10)."""
        with patch(
            "src.github_analyzer.api.routes.portfolio_analysis.CandidateUsageService"
        ) as mock_service_class:
            mock_candidate_service = Mock()
            mock_service_class.return_value = mock_candidate_service

            # Mock get_or_create_assessment - new candidate
            mock_assessment = Mock(spec=CandidateAssessment)
            mock_candidate_service.get_or_create_assessment = AsyncMock(
                return_value=(mock_assessment, True)  # is_new = True
            )

            # Mock monthly usage at limit for BASIC tier
            mock_candidate_service.get_monthly_usage = AsyncMock(return_value=10)

            # Mock tier limit for BASIC
            mock_service_class.get_tier_limit = Mock(return_value=10)

            is_eligible, reason = await check_user_eligibility(
                basic_user, "newdev", mock_db_session
            )

            assert is_eligible is False
            # Reason is now a dict with structured error information
            assert isinstance(reason, dict)
            assert reason["error"] == "Monthly candidate assessment limit reached"
            assert reason["current_usage"] == 10
            assert reason["limit"] == 10

    @pytest.mark.asyncio
    async def test_check_eligibility_existing_candidate_allowed(
        self, basic_user: Mock, mock_db_session: Mock
    ) -> None:
        """Test that existing candidates don't count against limit."""
        with patch(
            "src.github_analyzer.api.routes.portfolio_analysis.CandidateUsageService"
        ) as mock_service_class:
            mock_candidate_service = Mock()
            mock_service_class.return_value = mock_candidate_service

            # Mock get_or_create_assessment - existing candidate
            mock_assessment = Mock(spec=CandidateAssessment)
            mock_candidate_service.get_or_create_assessment = AsyncMock(
                return_value=(mock_assessment, False)  # is_new = False
            )

            # Even if at limit, existing candidates are OK
            mock_candidate_service.get_monthly_usage = AsyncMock(return_value=10)
            mock_service_class.get_tier_limit = Mock(return_value=10)

            is_eligible, reason = await check_user_eligibility(
                basic_user, "existingdev", mock_db_session
            )

            assert is_eligible is True
            assert reason == ""


class TestPortfolioAnalysisEndpoint:
    """Test portfolio analysis endpoint."""

    @pytest.mark.asyncio
    @patch("src.github_analyzer.api.routes.portfolio_analysis.config")
    @patch("src.github_analyzer.api.routes.portfolio_analysis.check_user_eligibility")
    @patch("src.github_analyzer.api.routes.portfolio_analysis.validate_context")
    async def test_analyze_portfolio_success(
        self,
        mock_validate_context: Any,
        mock_check_eligibility: Any,
        mock_config: Any,
        portfolio_request: Any,
        scale_plus_user: Mock,
        mock_db_session: Mock,
    ) -> None:
        """Test successful portfolio analysis (async with BackgroundTasks)."""
        # Setup config
        mock_config.github_token = "test-github-token"
        mock_config.anthropic_api_key = "test-anthropic-key"

        # Mock context validation (returns True for valid, None for locked context)
        mock_validate_context.return_value = (True, None)

        # Mock eligibility check
        mock_check_eligibility.return_value = (True, "")

        # Mock BackgroundTasks
        mock_background_tasks = Mock()
        mock_background_tasks.add_task = Mock()

        # Call endpoint
        response = await analyze_portfolio(
            portfolio_request, mock_background_tasks, scale_plus_user, mock_db_session
        )

        # Verify response structure (now returns PENDING status immediately)
        assert response["username"] == "testdev"
        assert response["context"] == "startup"
        assert response["status"] == "pending"
        assert "analysis_id" in response or "id" in response

        # Verify database commit (creates PENDING record)
        assert mock_db_session.add.call_count == 1
        assert mock_db_session.commit.call_count == 1

        # Verify background task was launched
        mock_background_tasks.add_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_portfolio_free_tier_rejected(
        self, portfolio_request: Any, free_user: Mock, mock_db_session: Mock
    ) -> None:
        """Test that Free tier users cannot access portfolio analysis."""
        with patch(
            "src.github_analyzer.api.routes.portfolio_analysis.check_user_eligibility"
        ) as mock_check_eligibility:
            mock_check_eligibility.return_value = (
                False,
                "Portfolio Analysis is available for paid plans. Your current plan: Free.",
            )

            with pytest.raises(HTTPException) as exc_info:
                await analyze_portfolio(portfolio_request, free_user, mock_db_session)

            assert exc_info.value.status_code == 403
            assert "available for paid plans" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    @patch("src.github_analyzer.api.routes.portfolio_analysis.config")
    @patch("src.github_analyzer.api.routes.portfolio_analysis.check_user_eligibility")
    @patch("src.github_analyzer.api.routes.portfolio_analysis.validate_context")
    async def test_analyze_portfolio_returns_cached(
        self,
        mock_validate_context: Any,
        mock_check_eligibility: Any,
        mock_config: Any,
        portfolio_request: Any,
        scale_plus_user: Mock,
        mock_db_session: Mock,
    ) -> None:
        """Test that cached analysis triggers async processing."""
        # Setup config
        mock_config.github_token = "test-github-token"
        mock_config.anthropic_api_key = "test-anthropic-key"

        # Mock context validation
        mock_validate_context.return_value = (True, None)

        # Mock eligibility check
        mock_check_eligibility.return_value = (True, "")

        # Mock BackgroundTasks
        mock_background_tasks = Mock()
        mock_background_tasks.add_task = Mock()

        # Call endpoint with force_refresh=False
        portfolio_request.force_refresh = False
        response = await analyze_portfolio(
            portfolio_request, mock_background_tasks, scale_plus_user, mock_db_session
        )

        # Verify response (returns PENDING even for cached - background task checks cache)
        assert response["status"] == "pending"
        assert "analysis_id" in response or "id" in response

        # Verify database commit (creates PENDING record)
        assert mock_db_session.add.call_count == 1
        assert mock_db_session.commit.call_count == 1

        # Verify background task was launched
        mock_background_tasks.add_task.assert_called_once()


class TestPortfolioUsageEndpoint:
    """Test portfolio usage statistics endpoint."""

    @pytest.mark.asyncio
    async def test_get_usage_professional_tier(
        self, professional_user: Mock, mock_db_session: Mock
    ) -> None:
        """Test usage endpoint for Professional tier user."""
        with patch(
            "src.github_analyzer.api.routes.portfolio_analysis.CandidateUsageService"
        ) as mock_service_class:
            mock_candidate_service = Mock()
            mock_service_class.return_value = mock_candidate_service

            # Mock monthly usage (15 out of 50)
            mock_candidate_service.get_monthly_usage = AsyncMock(return_value=15)
            mock_service_class.get_tier_limit = Mock(return_value=50)

            response = await get_portfolio_usage(professional_user, mock_db_session)

            assert response["eligible"] is True
            assert response["used_this_month"] == 15
            assert response["remaining_this_month"] == 35  # 50 - 15
            assert response["monthly_limit"] == 50
            assert "1 GitHub username = 1 candidate assessment" in response["note"]

    @pytest.mark.asyncio
    async def test_get_usage_free_tier_ineligible(
        self, free_user: Mock, mock_db_session: Mock
    ) -> None:
        """Test usage endpoint for Free tier (ineligible)."""
        response = await get_portfolio_usage(free_user, mock_db_session)

        assert response["eligible"] is False
        assert "available for paid plans" in response["message"].lower()
        assert response["required_plan"] == "BASIC or higher"


class TestPortfolioListEndpoint:
    """Test listing portfolio analyses."""

    @pytest.mark.asyncio
    async def test_list_portfolio_analyses(
        self,
        scale_plus_user: Mock,
        mock_db_session: Mock,
        mock_portfolio_analysis: Mock,
    ) -> None:
        """Test listing user's portfolio analyses."""
        # Mock query result
        mock_result = Mock()
        mock_result.scalars = Mock(
            return_value=Mock(all=Mock(return_value=[mock_portfolio_analysis]))
        )
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        response = await list_portfolio_analyses(
            scale_plus_user, mock_db_session, skip=0, limit=50
        )

        assert response["total"] == 1
        assert response["skip"] == 0
        assert response["limit"] == 50
        assert len(response["analyses"]) == 1
        assert response["analyses"][0]["github_username"] == "testdev"
        assert response["analyses"][0]["context"] == "startup"


class TestPortfolioGetByIdEndpoint:
    """Test getting portfolio analysis by ID."""

    @pytest.mark.asyncio
    async def test_get_by_id_success(
        self,
        scale_plus_user: Mock,
        mock_db_session: Mock,
        mock_portfolio_analysis: Mock,
    ) -> None:
        """Test retrieving portfolio analysis by ID."""
        # Mock query result
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_portfolio_analysis)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "src.github_analyzer.api.routes.portfolio_analysis.format_analysis_response"
        ) as mock_format:
            mock_format.return_value = {"analysis_id": mock_portfolio_analysis.id}

            response = await get_portfolio_analysis_by_id(
                mock_portfolio_analysis.id, scale_plus_user, mock_db_session
            )

            assert response["analysis_id"] == mock_portfolio_analysis.id

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self, scale_plus_user: Mock, mock_db_session: Mock
    ) -> None:
        """Test 404 when analysis not found or unauthorized."""
        # Mock query result - not found
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await get_portfolio_analysis_by_id(
                "non-existent-id", scale_plus_user, mock_db_session
            )

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()


class TestHelperFunctions:
    """Test helper functions."""

    @pytest.mark.asyncio
    async def test_get_cached_analysis_found(self, mock_db_session: Mock) -> None:
        """Test getting cached analysis that exists."""
        from github_analyzer.database.models_portfolio import PortfolioAnalysisCache

        # Mock cache entry (first query)
        mock_cache = Mock(spec=PortfolioAnalysisCache)
        mock_cache.result_id = "test-result-id"

        # Mock analysis result (second query)
        mock_analysis = Mock(spec=PortfolioAnalysis)

        # Mock execute to return different results for each query
        mock_cache_result = Mock()
        mock_cache_result.scalar_one_or_none = Mock(return_value=mock_cache)

        mock_analysis_result = Mock()
        mock_analysis_result.scalar_one_or_none = Mock(return_value=mock_analysis)

        mock_db_session.execute = AsyncMock(
            side_effect=[mock_cache_result, mock_analysis_result]
        )

        result = await get_cached_analysis(
            "testdev", "startup", "senior", mock_db_session
        )

        assert result == mock_analysis
        assert mock_db_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_get_cached_analysis_not_found(self, mock_db_session: Mock) -> None:
        """Test getting cached analysis that doesn't exist."""
        # Mock cache entry not found (first query returns None)
        mock_cache_result = Mock()
        mock_cache_result.scalar_one_or_none = Mock(return_value=None)
        mock_db_session.execute = AsyncMock(return_value=mock_cache_result)

        result = await get_cached_analysis(
            "testdev", "startup", "senior", mock_db_session
        )

        assert result is None
        # Only one query (cache lookup), doesn't try to fetch result
        assert mock_db_session.execute.call_count == 1

    def test_format_analysis_response(self, mock_portfolio_analysis: Mock) -> None:
        """Test formatting portfolio analysis for response."""
        response = format_analysis_response(mock_portfolio_analysis, from_cache=False)

        assert response["analysis_id"] == mock_portfolio_analysis.id
        assert response["username"] == "testdev"
        assert response["context"] == "startup"
        assert response["from_cache"] is False
        assert "summary" in response
        assert "evidence_patterns" in response


class TestTierConfiguration:
    """Test tier configuration constants."""

    def test_portfolio_analysis_tiers(self) -> None:
        """Test that portfolio analysis tiers include all paid tiers."""
        assert SubscriptionPlan.BASIC in PORTFOLIO_ANALYSIS_TIERS
        assert SubscriptionPlan.PROFESSIONAL in PORTFOLIO_ANALYSIS_TIERS
        assert SubscriptionPlan.ENTERPRISE in PORTFOLIO_ANALYSIS_TIERS
        assert SubscriptionPlan.SCALE_PLUS in PORTFOLIO_ANALYSIS_TIERS
        assert SubscriptionPlan.FREE not in PORTFOLIO_ANALYSIS_TIERS
