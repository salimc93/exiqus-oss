"""
Tests for PR Analysis API endpoints.

Tests the full integration including eligibility checks,
rate limiting, AI insights generation, and caching.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.github_analyzer.api.routes.pr_analysis import (
    PRAnalysisService,
    analyze_user_prs,
    get_pr_analysis_history,
    get_pr_analysis_usage,
)
from src.github_analyzer.data.pr_models import PREvidence, QualitySignals
from src.github_analyzer.database.models import (
    PRAnalysisRecord,
    SubscriptionPlan,
    User,
)
from src.github_analyzer.database.models_portfolio import CandidateAssessment


@pytest.fixture
def pr_service():
    """Create PR analysis service instance."""
    with patch("src.github_analyzer.api.routes.pr_analysis.config") as mock_config:
        mock_config.anthropic_api_key = "test-api-key"
        service = PRAnalysisService()
        return service


@pytest.fixture
def scale_plus_user():
    """Create a Scale+ user eligible for PR analysis."""
    user = Mock(spec=User)
    user.user_id = "test-user-id"
    user.email = "test@example.com"
    user.subscription_plan = SubscriptionPlan.SCALE_PLUS
    return user


@pytest.fixture
def basic_user():
    """Create a Basic tier user eligible for PR analysis (10 candidates/month)."""
    user = Mock(spec=User)
    user.user_id = "basic-user-id"
    user.email = "basic@example.com"
    user.subscription_plan = SubscriptionPlan.BASIC
    return user


@pytest.fixture
def free_user():
    """Create a Free tier user not eligible for PR analysis."""
    user = Mock(spec=User)
    user.user_id = "free-user-id"
    user.email = "free@example.com"
    user.subscription_plan = SubscriptionPlan.FREE
    return user


@pytest.fixture
def professional_user():
    """Create a Professional tier user (50 candidates/month)."""
    user = Mock(spec=User)
    user.user_id = "pro-user-id"
    user.email = "pro@example.com"
    user.subscription_plan = SubscriptionPlan.PROFESSIONAL
    return user


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    session = Mock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.add = Mock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def pr_analysis_request():
    """Create PR analysis request."""
    from src.github_analyzer.api.models.requests import PRAnalyzeRequest

    return PRAnalyzeRequest(
        github_username="testuser",
        context="STARTUP",
        max_prs=50,
        force_refresh=False,
        include_all_evidence=True,
    )


@pytest.fixture
def sample_evidence():
    """Create sample PR evidence."""
    return PREvidence(
        technical_substance=[
            "Production Integration Success: 45/50 PRs merged successfully",
            "Implemented 5 major features across 3 repositories",
        ],
        collaboration_patterns=["Regular code reviews", "Active in discussions"],
        review_responsiveness=["Average review response time: 2 hours"],
        cross_repo_contributions=["Contributed to 8 different repositories"],
        areas_to_explore=["Testing practices need exploration"],
    )


@pytest.fixture
def sample_quality_signals():
    """Create sample quality signals."""
    return QualitySignals(
        total_prs=50,
        merged_prs=45,
        unique_repos=8,
        contribution_timespan="2 years",
        feature_prs=25,
        fix_prs=15,
    )


@pytest.fixture
def sample_ai_insights():
    """Create sample AI insights."""
    return {
        "interview_questions": [
            {
                "question": "Tell me about PR #123 where you refactored the auth system",
                "category": "technical",
                "evidence_reference": "PR #123",
                "context_note": "Important for startup velocity",
                "follow_up_questions": [
                    "What challenges did you face?",
                    "How did you ensure backward compatibility?",
                    "What was the performance improvement?",
                ],
                "key_listening_points": "Technical depth and problem-solving approach",
            }
        ],
        "key_strengths": [
            "Strong feature velocity with 25 feature PRs",
            "Cross-team collaboration evident in 8 repositories",
        ],
        "technical_capabilities": ["Python expertise", "Distributed systems"],
        "collaboration_style": ["Responsive to feedback", "Clear communication"],
        "code_quality_indicators": ["Consistent testing", "Clean architecture"],
        "areas_for_discussion": ["Testing strategy", "Performance optimization"],
        "notable_contributions": ["Auth system refactor", "Payment integration"],
        "context_fit": {
            "alignment": "strong",
            "supporting_evidence": ["High feature velocity", "MVP mindset"],
            "considerations": ["May need guidance on enterprise patterns"],
            "specific_strengths_for_context": [
                "Rapid iteration",
                "Full-stack capability",
            ],
        },
    }


class TestPRAnalysisService:
    """Test PR Analysis Service."""

    @pytest.mark.asyncio
    async def test_check_user_eligibility_scale_plus_new_candidate(
        self, pr_service, scale_plus_user, mock_db_session
    ):
        """Test eligibility check for Scale+ user with new candidate."""
        with patch(
            "src.github_analyzer.api.routes.pr_analysis.CandidateUsageService"
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
            mock_candidate_service.get_monthly_usage = AsyncMock(return_value=10)

            # Mock tier limit
            mock_service_class.get_tier_limit = Mock(return_value=500)

            is_eligible, reason = await pr_service.check_user_eligibility(
                scale_plus_user, "testuser", mock_db_session
            )

            assert is_eligible is True
            assert reason == ""

    @pytest.mark.asyncio
    async def test_check_user_eligibility_wrong_tier(
        self, pr_service, free_user, mock_db_session
    ):
        """Test eligibility check for Free tier user (not paid)."""
        is_eligible, reason = await pr_service.check_user_eligibility(
            free_user, "testuser", mock_db_session
        )

        assert is_eligible is False
        assert "available for paid plans" in reason

    @pytest.mark.asyncio
    async def test_check_user_eligibility_basic_tier_new_candidate_at_limit(
        self, pr_service, basic_user, mock_db_session
    ):
        """Test eligibility check for Basic user at monthly limit (10 candidates)."""
        with patch(
            "src.github_analyzer.api.routes.pr_analysis.CandidateUsageService"
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

            is_eligible, reason = await pr_service.check_user_eligibility(
                basic_user, "newuser", mock_db_session
            )

            assert is_eligible is False
            # Reason is now a dict with structured error information
            assert isinstance(reason, dict)
            assert reason["error"] == "Monthly candidate assessment limit reached"
            assert reason["current_usage"] == 10
            assert reason["limit"] == 10

    @pytest.mark.asyncio
    async def test_check_user_eligibility_existing_candidate(
        self, pr_service, basic_user, mock_db_session
    ):
        """Test eligibility check for existing candidate (doesn't count against limit)."""
        with patch(
            "src.github_analyzer.api.routes.pr_analysis.CandidateUsageService"
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

            is_eligible, reason = await pr_service.check_user_eligibility(
                basic_user, "existinguser", mock_db_session
            )

            assert is_eligible is True
            assert reason == ""

    @pytest.mark.asyncio
    async def test_record_analysis(self, pr_service, mock_db_session):
        """Test recording PR analysis for tracking."""
        await pr_service.record_analysis(
            user_id="test-user-id",
            username="testuser",
            pr_count=50,
            api_calls=5,
            context="STARTUP",
            role="senior",
            db=mock_db_session,
        )

        # Verify record was added
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

        # Check the record that was added
        record = mock_db_session.add.call_args[0][0]
        assert isinstance(record, PRAnalysisRecord)
        assert record.user_id == "test-user-id"
        assert record.github_username == "testuser"
        assert record.pr_count == 50
        assert record.api_calls_used == 5


class TestPRAnalysisEndpoints:
    """Test PR Analysis API endpoints."""

    @pytest.mark.asyncio
    @patch("src.github_analyzer.api.routes.pr_analysis.validate_context")
    @patch("src.github_analyzer.api.routes.pr_analysis.CandidateUsageService")
    @patch("src.github_analyzer.api.routes.pr_analysis.pr_rate_limiter")
    @patch("src.github_analyzer.api.routes.pr_analysis.get_cached_pr_analysis")
    async def test_analyze_user_prs_success(
        self,
        mock_get_cached,
        mock_rate_limiter,
        mock_candidate_service_class,
        mock_validate_context,
        pr_analysis_request,
        scale_plus_user,
        mock_db_session,
    ):
        """Test successful PR analysis (async with BackgroundTasks)."""
        # Mock context validation
        mock_validate_context.return_value = (True, None)

        # Mock rate limiter
        mock_rate_limiter.check_limit = AsyncMock(return_value=(True, 5, 20))
        mock_rate_limiter.get_remaining_time = AsyncMock(return_value=1800)

        # Mock CandidateUsageService
        mock_candidate_service = Mock()
        mock_candidate_service_class.return_value = mock_candidate_service
        mock_candidate_service.get_or_create_assessment = AsyncMock(
            return_value=(Mock(), False)
        )
        mock_candidate_service.get_monthly_usage = AsyncMock(return_value=10)
        mock_candidate_service_class.get_tier_limit = Mock(return_value=500)

        # Mock cache lookup (no cached result)
        mock_get_cached.return_value = None

        # Mock BackgroundTasks
        mock_background_tasks = Mock()
        mock_background_tasks.add_task = Mock()

        # Mock pr_service eligibility check
        with patch(
            "src.github_analyzer.api.routes.pr_analysis.pr_service"
        ) as mock_service:
            mock_service.check_user_eligibility = AsyncMock(return_value=(True, ""))

            # Call endpoint
            response = await analyze_user_prs(
                pr_analysis_request,
                mock_background_tasks,
                scale_plus_user,
                mock_db_session,
            )

            # Verify response (returns PENDING status immediately)
            assert response.username == "testuser"
            assert response.context == "STARTUP"
            assert response.status == "pending"
            assert response.analysis_id is not None

            # Verify database commit (creates PENDING PRAnalysisResult AND PRAnalysisRecord)
            assert mock_db_session.add.call_count == 2
            assert mock_db_session.commit.call_count == 2

            # Verify background task was launched
            mock_background_tasks.add_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_user_prs_unauthorized(
        self, pr_analysis_request, free_user, mock_db_session
    ):
        """Test PR analysis with unauthorized Free tier user."""
        with patch(
            "src.github_analyzer.api.routes.pr_analysis.pr_service"
        ) as mock_service:
            mock_service.check_user_eligibility = AsyncMock(
                return_value=(
                    False,
                    "PR Analysis is available for paid plans.",
                )
            )

            # Call endpoint and expect exception
            with pytest.raises(HTTPException) as exc_info:
                await analyze_user_prs(pr_analysis_request, free_user, mock_db_session)

            assert exc_info.value.status_code == 403
            assert "available for paid plans" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("src.github_analyzer.api.routes.pr_analysis.pr_rate_limiter")
    @patch("src.github_analyzer.api.routes.pr_analysis.CandidateUsageService")
    async def test_get_pr_analysis_usage_eligible(
        self, mock_service_class, mock_rate_limiter, scale_plus_user, mock_db_session
    ):
        """Test getting PR analysis usage for eligible Scale+ user."""
        # Mock rate limiter
        mock_rate_limiter.get_usage_stats = AsyncMock(
            return_value={
                "current_hour_usage": 5,
                "hourly_limit": 20,
                "remaining_this_hour": 15,
                "resets_in_seconds": 1800,
                "resets_in_minutes": 30,
            }
        )

        # Mock CandidateUsageService
        mock_candidate_service = Mock()
        mock_service_class.return_value = mock_candidate_service
        mock_candidate_service.get_monthly_usage = AsyncMock(return_value=25)
        mock_service_class.get_tier_limit = Mock(return_value=500)  # Scale+ limit

        response = await get_pr_analysis_usage(scale_plus_user, mock_db_session)

        assert response["eligible"] is True
        assert response["used_this_month"] == 25
        assert response["remaining_this_month"] == 475  # 500 - 25
        assert response["monthly_limit"] == 500
        assert "1 GitHub username = 1 candidate assessment" in response["note"]

    @pytest.mark.asyncio
    async def test_get_pr_analysis_usage_ineligible(self, free_user, mock_db_session):
        """Test getting PR analysis usage for ineligible Free tier user."""
        response = await get_pr_analysis_usage(free_user, mock_db_session)

        assert response["eligible"] is False
        assert "available for paid plans" in response["message"]
        assert response["required_plan"] == "BASIC or higher"

    @pytest.mark.asyncio
    async def test_get_pr_analysis_history_success(
        self, scale_plus_user, mock_db_session
    ):
        """Test getting PR analysis history."""
        # Create mock records
        mock_record = Mock(spec=PRAnalysisRecord)
        mock_record.github_username = "testuser"
        mock_record.pr_count = 50
        mock_record.api_calls_used = 5
        mock_record.context = "STARTUP"
        mock_record.created_at = datetime.now(timezone.utc)

        # Mock query result
        mock_result = Mock()
        mock_result.scalars = Mock(
            return_value=Mock(all=Mock(return_value=[mock_record]))
        )
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        response = await get_pr_analysis_history(
            scale_plus_user, mock_db_session, limit=10
        )

        assert len(response["history"]) == 1
        assert response["history"][0]["github_username"] == "testuser"
        assert response["history"][0]["pr_count"] == 50
        assert response["period"] == "current_month"

    @pytest.mark.asyncio
    async def test_get_pr_analysis_history_unauthorized(
        self, free_user, mock_db_session
    ):
        """Test getting PR analysis history for unauthorized Free tier user."""
        with pytest.raises(HTTPException) as exc_info:
            await get_pr_analysis_history(free_user, mock_db_session)

        assert exc_info.value.status_code == 403
        assert "available for paid plans only" in exc_info.value.detail
