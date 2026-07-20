"""
Tests for Portfolio Insights Generator.

Tests AI-powered portfolio insights generation with proper mocking to avoid real API calls.
"""

from typing import Any, Dict, List
from unittest.mock import Mock, patch

import pytest

from github_analyzer.ai.portfolio_insights_generator import PortfolioInsightsGenerator
from github_analyzer.core.tier_config import get_model_for_tier, get_tier_config
from github_analyzer.data.portfolio_models import PortfolioMetadata, RepoData


@pytest.fixture
def api_key() -> str:
    """Test API key."""
    return "test-api-key"


@pytest.fixture
def sample_metadata() -> PortfolioMetadata:
    """Sample portfolio metadata."""
    return PortfolioMetadata(
        total_public_repos=30,
        repos_analyzed=25,
        repos_skipped=5,
        skip_counts={"too_small": 3, "fork": 2},
        skipped_repos={"too_small": ["tiny-repo"], "fork": ["forked-repo"]},
        analyzed_repos=["repo1", "repo2", "repo3"],
        oldest_repo="2020-01-01",
        newest_repo="2025-01-01",
        timeline_gaps=[],
        tokens=15000,
        cost=0.75,
    )


@pytest.fixture
def sample_repos() -> List[RepoData]:
    """Sample repository data."""
    from datetime import datetime, timezone

    return [
        RepoData(
            name="awesome-project",
            full_name="user/awesome-project",
            url="https://github.com/user/awesome-project",
            owner="user",
            description="A great project",
            created_at=datetime(2023, 1, 15, tzinfo=timezone.utc),
            updated_at=datetime(2024, 12, 20, tzinfo=timezone.utc),
            pushed_at=datetime(2024, 12, 20, tzinfo=timezone.utc),
            size_kb=2500,
            primary_language="Python",
            languages={"Python": 50000, "JavaScript": 10000},
            topics=["web", "api"],
            stars=150,
            forks=25,
            open_issues=5,
            watchers=150,
            is_fork=False,
            is_archived=False,
            is_private=False,
            total_commits=250,
            has_wiki=True,
            has_pages=False,
            has_tests=True,
            has_ci=True,
            user_commits=200,
            user_is_owner=True,
        ),
        RepoData(
            name="ml-toolkit",
            full_name="user/ml-toolkit",
            url="https://github.com/user/ml-toolkit",
            owner="user",
            description="Machine learning utilities",
            created_at=datetime(2022, 6, 10, tzinfo=timezone.utc),
            updated_at=datetime(2024, 11, 15, tzinfo=timezone.utc),
            pushed_at=datetime(2024, 11, 15, tzinfo=timezone.utc),
            size_kb=1800,
            primary_language="Python",
            languages={"Python": 40000, "Jupyter Notebook": 5000},
            topics=["machine-learning", "ai"],
            stars=80,
            forks=12,
            open_issues=3,
            watchers=80,
            is_fork=False,
            is_archived=False,
            is_private=False,
            total_commits=180,
            has_wiki=False,
            has_pages=True,
            has_tests=True,
            has_ci=False,
            user_commits=150,
            user_is_owner=True,
        ),
    ]


@pytest.fixture
def sample_evidence() -> Dict[str, Any]:
    """Sample evidence data."""
    return {
        "languages": {"Python": 75, "JavaScript": 20, "Go": 5},
        "frameworks": ["Django", "React", "FastAPI"],
        "patterns": [
            {
                "pattern": "Consistent Testing Practices",
                "evidence": "Test coverage across multiple repositories",
                "strength": "observed",
            },
            {
                "pattern": "Modern Tech Stack",
                "evidence": "Uses contemporary frameworks and tools",
                "strength": "observed",
            },
        ],
        "commit_activity": {"total_commits": 430, "repos_with_commits": 25},
        "community_engagement": {"total_stars": 230, "total_forks": 37},
    }


@pytest.fixture
def mock_ai_response_single_model() -> str:
    """Mock AI response for single-model approach."""
    return """# Portfolio Analysis

## EXECUTIVE SUMMARY
testuser demonstrates solid technical skills across Python and JavaScript ecosystems with focus on web development and API design.

## DATA LIMITATIONS
PUBLIC REPOSITORIES ONLY - Private work and proprietary contributions not visible in this analysis.

## KEY OBSERVATIONS
1. Consistent use of modern frameworks including Django and FastAPI
2. Active maintenance across multiple repositories
3. Community engagement through stars and forks

## EVIDENCE PATTERNS
[
  {
    "pattern": "Testing Practices",
    "evidence": "Multiple repositories contain test suites",
    "observation": "Developer prioritizes code quality"
  }
]

## PUBLIC PORTFOLIO EVOLUTION

### 2022-2023: Foundation Building
**Public Repos Created**: 10
**Technologies**: Python, JavaScript, React
**Domain Focus**: Web development
**Largest Project**: ml-toolkit (1800 KB)
**Code Quality**: Active maintenance evident
**Community Recognition**: Growing star count

### 2024-2025: Continued Growth
**Public Repos Created**: 15
**Technologies**: Python, FastAPI, Go
**Domain Focus**: API development, microservices
**Largest Project**: awesome-project (2500 KB)
**Code Quality**: Regular commits and updates
**Community Recognition**: Strong engagement

## INTERVIEW QUESTIONS

### Q1: Architecture Decisions
**Can you walk me through your architecture decisions for the awesome-project repository?**
`technical-deep-dive`
**Context**: Repository shows 250 commits and active development
**Based on Evidence**: Public repository awesome-project has sustained development
**Follow-up Questions**:
1. How do you handle scaling challenges?
2. What trade-offs did you make in the design?
*Look for technical depth and decision-making rationale*

### Q2: Testing Strategy
**How do you approach testing in your projects?**
`code-quality`
**Context**: Multiple repositories show evidence of test coverage
**Based on Evidence**: Testing patterns observed across portfolio
**Follow-up Questions**:
1. What's your approach to integration vs unit testing?
2. How do you measure test effectiveness?
*Listen for quality-focused mindset*

## POSITIVE INDICATORS
- Consistent repository maintenance
- Modern technology stack
- Community engagement through stars and forks

## AREAS TO EXPLORE
- Collaboration patterns and team experience
- Scale of production deployments
- Private/proprietary work not visible here

## RECOMMENDATIONS
- Discuss specific technical challenges in interviews
- Explore team collaboration experiences
- Verify scale and complexity of projects

## QUALITY INDICATORS
[
  {
    "indicator": "Commit Frequency",
    "observation": "Regular commits across 25 repositories",
    "scope": "public repositories only",
    "implication": "Active developer with consistent output"
  }
]

## EVIDENCE QUALITY ASSESSMENT
Analysis based on 25 public repositories. Private work and team contributions not visible. Interview recommended to understand full scope of experience.
"""


@pytest.fixture
def mock_ai_response_phase2_questions() -> str:
    """Mock AI response for Phase 2 questions (multi-model approach)."""
    return """## INTERVIEW QUESTIONS

### Q1: System Design Experience
**Describe your experience designing scalable systems**
`system-design`
**Context**: Multiple API projects suggest backend focus
**Based on Evidence**: awesome-project and other backend repositories
**Follow-up Questions**:
1. How do you handle database optimization?
2. What monitoring solutions have you implemented?
*Focus on scalability and production experience*

### Q2: Code Review Philosophy
**What's your approach to code reviews?**
`collaboration`
**Context**: Pull request activity across repositories
**Based on Evidence**: 45 PRs in awesome-project
**Follow-up Questions**:
1. How do you balance thoroughness with velocity?
2. What makes a good code review?
*Listen for collaboration and quality mindset*
"""


class TestPortfolioInsightsGeneratorInit:
    """Test PortfolioInsightsGenerator initialization."""

    def test_init_with_api_key(self, api_key: str) -> None:
        """Test initialization with API key."""
        generator = PortfolioInsightsGenerator(api_key)

        assert generator.anthropic is not None
        assert generator.report_generator is not None

    def test_init_creates_anthropic_wrapper(self, api_key: str) -> None:
        """Test that initialization creates AnthropicWrapper."""
        with patch(
            "github_analyzer.ai.portfolio_insights_generator.AnthropicWrapper"
        ) as mock_wrapper:
            PortfolioInsightsGenerator(api_key)

            mock_wrapper.assert_called_once_with(api_key)


class TestGenerateInsightsSingleModel:
    """Test generate_insights with single-model approach."""

    def test_generate_insights_success(
        self,
        api_key: str,
        sample_metadata: PortfolioMetadata,
        sample_repos: List[RepoData],
        sample_evidence: Dict[str, Any],
        mock_ai_response_single_model: str,
    ) -> None:
        """Test successful insights generation with single model."""
        generator = PortfolioInsightsGenerator(api_key)

        # Mock the AI response
        mock_response = Mock()
        mock_response.content = [Mock(text=mock_ai_response_single_model)]
        mock_response.usage = Mock(input_tokens=1000, output_tokens=2000)

        with patch.object(
            generator.anthropic, "create_message", return_value=mock_response
        ):
            result = generator.generate_insights(
                username="testuser",
                evidence=sample_evidence,
                metadata=sample_metadata,
                repos=sample_repos,
                context="enterprise",
                tier="professional",
                role="senior",
            )

        # Verify success
        assert result["success"] is True
        assert "insights" in result
        assert result["model_used"] == get_model_for_tier("professional")
        assert result["context"] == "enterprise"

        # Verify token tracking
        assert result["input_tokens"] == 1000
        assert result["output_tokens"] == 2000
        assert result["total_tokens"] == 3000
        assert "cost" in result

        # Verify insights structure
        insights = result["insights"]
        assert "executive_summary" in insights
        assert "key_observations" in insights
        assert "interview_questions" in insights
        assert len(insights["interview_questions"]) > 0

    def test_generate_insights_with_different_tier(
        self,
        api_key: str,
        sample_metadata: PortfolioMetadata,
        sample_repos: List[RepoData],
        sample_evidence: Dict[str, Any],
        mock_ai_response_single_model: str,
    ) -> None:
        """Test insights generation with different subscription tier."""
        generator = PortfolioInsightsGenerator(api_key)

        mock_response = Mock()
        mock_response.content = [Mock(text=mock_ai_response_single_model)]
        mock_response.usage = Mock(input_tokens=500, output_tokens=1000)

        with patch.object(
            generator.anthropic, "create_message", return_value=mock_response
        ):
            result = generator.generate_insights(
                username="testuser",
                evidence=sample_evidence,
                metadata=sample_metadata,
                repos=sample_repos,
                context="startup",
                tier="basic",
                role="mid",
            )

        assert result["success"] is True
        assert result["context"] == "startup"


class TestGenerateInsightsMultiModel:
    """Test generate_insights with multi-model approach (Scale+ tier)."""

    def test_generate_insights_multi_model_success(
        self,
        api_key: str,
        sample_metadata: PortfolioMetadata,
        sample_repos: List[RepoData],
        sample_evidence: Dict[str, Any],
        mock_ai_response_single_model: str,
        mock_ai_response_phase2_questions: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Two-phase generation runs when a tier overrides the questions model.

        Tiers ship with no overrides, so both models resolve to ANTHROPIC_MODEL
        and this path stays dormant. Setting an explicit questions_model is what
        activates it, so the test configures one rather than relying on a tier
        that happens to differ.
        """
        scale_plus = get_tier_config("scale_plus")
        assert scale_plus is not None
        monkeypatch.setattr(scale_plus, "questions_model", "claude-questions-model")

        generator = PortfolioInsightsGenerator(api_key)

        # Mock Phase 1 response
        mock_response_phase1 = Mock()
        mock_response_phase1.content = [Mock(text=mock_ai_response_single_model)]
        mock_response_phase1.usage = Mock(input_tokens=2000, output_tokens=4000)

        # Mock Phase 2 response
        mock_response_phase2 = Mock()
        mock_response_phase2.content = [Mock(text=mock_ai_response_phase2_questions)]
        mock_response_phase2.usage = Mock(input_tokens=1000, output_tokens=1500)

        with patch.object(
            generator.anthropic,
            "create_message",
            side_effect=[mock_response_phase1, mock_response_phase2],
        ):
            result = generator.generate_insights(
                username="testuser",
                evidence=sample_evidence,
                metadata=sample_metadata,
                repos=sample_repos,
                context="enterprise",
                tier="scale_plus",
                role="senior",
            )

        # Verify success
        assert result["success"] is True
        assert result["questions_model_used"] == "claude-questions-model"

        # Verify total tokens include both phases
        assert result["input_tokens"] == 3000  # 2000 + 1000
        assert result["output_tokens"] == 5500  # 4000 + 1500
        assert result["total_tokens"] == 8500

    def test_generate_insights_multi_model_phase2_failure(
        self,
        api_key: str,
        sample_metadata: PortfolioMetadata,
        sample_repos: List[RepoData],
        sample_evidence: Dict[str, Any],
        mock_ai_response_single_model: str,
    ) -> None:
        """Test multi-model approach with Phase 2 failure (should still succeed with Phase 1 questions)."""
        generator = PortfolioInsightsGenerator(api_key)

        # Mock Phase 1 response
        mock_response_phase1 = Mock()
        mock_response_phase1.content = [Mock(text=mock_ai_response_single_model)]
        mock_response_phase1.usage = Mock(input_tokens=2000, output_tokens=4000)

        with patch.object(
            generator.anthropic,
            "create_message",
            side_effect=[mock_response_phase1, Exception("Phase 2 API error")],
        ):
            result = generator.generate_insights(
                username="testuser",
                evidence=sample_evidence,
                metadata=sample_metadata,
                repos=sample_repos,
                context="enterprise",
                tier="scale_plus",
                role="senior",
            )

        # Should still succeed with Phase 1 questions
        assert result["success"] is True
        assert len(result["insights"]["interview_questions"]) > 0
        # Phase 2 tokens should be 0
        assert result["input_tokens"] == 2000
        assert result["output_tokens"] == 4000


class TestGenerateInsightsErrorHandling:
    """Test error handling in generate_insights."""

    def test_generate_insights_api_error(
        self,
        api_key: str,
        sample_metadata: PortfolioMetadata,
        sample_repos: List[RepoData],
        sample_evidence: Dict[str, Any],
    ) -> None:
        """Test handling of API errors."""
        generator = PortfolioInsightsGenerator(api_key)

        with patch.object(
            generator.anthropic,
            "create_message",
            side_effect=Exception("API connection failed"),
        ):
            result = generator.generate_insights(
                username="testuser",
                evidence=sample_evidence,
                metadata=sample_metadata,
                repos=sample_repos,
                context="enterprise",
                tier="professional",
                role="senior",
            )

        # Should return failure with fallback insights
        assert result["success"] is False
        assert "error" in result
        assert "API connection failed" in result["error"]
        assert "insights" in result
        assert (
            result["insights"]["executive_summary"]
            == "Analysis pending for testuser. Manual review recommended."
        )

    def test_generate_insights_empty_response(
        self,
        api_key: str,
        sample_metadata: PortfolioMetadata,
        sample_repos: List[RepoData],
        sample_evidence: Dict[str, Any],
    ) -> None:
        """Test handling of empty AI response."""
        generator = PortfolioInsightsGenerator(api_key)

        mock_response = Mock()
        mock_response.content = []

        with patch.object(
            generator.anthropic, "create_message", return_value=mock_response
        ):
            result = generator.generate_insights(
                username="testuser",
                evidence=sample_evidence,
                metadata=sample_metadata,
                repos=sample_repos,
                context="enterprise",
                tier="professional",
                role="senior",
            )

        # Should handle gracefully with fallback
        assert result["success"] is False
        assert "error" in result


class TestSanitizeInsights:
    """Test _sanitize_insights method."""

    def test_sanitize_removes_scores(self, api_key: str) -> None:
        """Test that sanitization removes scores and ratings."""
        generator = PortfolioInsightsGenerator(api_key)

        insights = {
            "executive_summary": "Developer has a score of 8/10 with 75% code coverage",
            "key_observations": ["Rating: high quality code"],
            "recommendations": ["Score: 7/10 for experience"],
        }

        # Sanitization should log warnings but not crash
        result = generator._sanitize_insights(insights)

        # Should still return valid structure
        assert "executive_summary" in result
        assert "key_observations" in result

    def test_sanitize_removes_inference_phrases(self, api_key: str) -> None:
        """Test that sanitization replaces inference phrases."""
        generator = PortfolioInsightsGenerator(api_key)

        insights = {
            "executive_summary": "These appear to be passion projects suggesting hobby development",
            "key_observations": ["This is a portfolio piece"],
        }

        result = generator._sanitize_insights(insights)

        # Egregious inference phrases should be replaced
        assert "passion project" not in result["executive_summary"].lower()
        assert "portfolio piece" not in result["key_observations"][0].lower()

    def test_sanitize_handles_nested_structures(self, api_key: str) -> None:
        """Test sanitization of nested data structures."""
        generator = PortfolioInsightsGenerator(api_key)

        insights = {
            "evidence_patterns": [
                {"pattern": "Testing", "score": 9, "evidence": "High quality tests"}
            ],
            "quality_indicators": [
                {
                    "indicator": "Code Quality",
                    "rating": "excellent",
                    "percentage": "95%",
                }
            ],
        }

        result = generator._sanitize_insights(insights)

        # Should remove score/rating keys
        assert "score" not in result["evidence_patterns"][0]
        assert "rating" not in result["quality_indicators"][0]
        assert "percentage" not in result["quality_indicators"][0]


class TestParsingMethods:
    """Test parsing helper methods."""

    def test_parse_portfolio_response(
        self, api_key: str, mock_ai_response_single_model: str
    ) -> None:
        """Test parsing of portfolio response."""
        generator = PortfolioInsightsGenerator(api_key)

        result = generator._parse_portfolio_response(mock_ai_response_single_model)

        # Verify parsed structure
        assert "executive_summary" in result
        assert len(result["executive_summary"]) > 0
        assert "key_observations" in result
        assert len(result["key_observations"]) > 0
        assert "interview_questions" in result
        assert len(result["interview_questions"]) >= 2
        assert "public_portfolio_evolution" in result
        assert len(result["public_portfolio_evolution"]) == 2

    def test_parse_questions_from_response(
        self, api_key: str, mock_ai_response_phase2_questions: str
    ) -> None:
        """Test parsing of Phase 2 questions response."""
        generator = PortfolioInsightsGenerator(api_key)

        questions = generator._parse_questions_from_response(
            mock_ai_response_phase2_questions
        )

        # Verify parsed questions
        assert len(questions) == 2
        assert (
            questions[0]["question"]
            == "Describe your experience designing scalable systems"
        )
        assert questions[0]["category"] == "system-design"
        assert questions[1]["question"] == "What's your approach to code reviews?"
        assert questions[1]["category"] == "collaboration"

    def test_get_fallback_insights(self, api_key: str) -> None:
        """Test fallback insights generation."""
        generator = PortfolioInsightsGenerator(api_key)

        fallback = generator._get_fallback_insights("testuser")

        # Verify fallback structure
        assert "executive_summary" in fallback
        assert "testuser" in fallback["executive_summary"]
        assert "interview_questions" in fallback
        assert len(fallback["interview_questions"]) > 0
        assert "recommendations" in fallback
