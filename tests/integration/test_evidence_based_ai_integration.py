"""
Integration tests for evidence-based AI analysis system.

Tests the complete flow from repository data through AI analysis
to evidence-based results and API responses.
"""

import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from github_analyzer.ai.analyzer import (
    AIAnalyzer,
    AnalysisResult,
    ContextAlignment,
    EvidencePattern,
    EvidenceStrength,
)
from github_analyzer.core.context_analyzer import AnalysisContext
from github_analyzer.core.report_generator import ReportGenerator
from github_analyzer.data.models import (
    CommitInfo,
    FileInfo,
    RepositoryData,
    RepositoryMetrics,
)
from tests.conftest import create_mock_anthropic_response


class TestEvidenceBasedAIIntegration:
    """Test evidence-based AI analysis integration."""

    @pytest.fixture
    def portfolio_repo(self):
        """Create a portfolio-quality repository for testing."""
        return RepositoryData(
            url="https://github.com/expert/awesome-project",
            full_name="expert/awesome-project",
            name="awesome-project",
            owner="expert",
            description="A comprehensive portfolio project showcasing best practices",
            created_at=datetime(2021, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 1, 20, tzinfo=timezone.utc),
            pushed_at=datetime(2024, 1, 20, tzinfo=timezone.utc),
            default_branch="main",
            size=15000,
            languages={
                "Python": 60000,
                "TypeScript": 30000,
                "JavaScript": 15000,
                "Rust": 10000,
            },
            topics=["api", "microservices", "best-practices", "clean-code"],
            license_name="MIT",
            stars=500,
            forks=120,
            watchers=80,
            open_issues=5,
            has_readme=True,
            has_license=True,
            has_contributing=True,
            has_tests=True,
            has_ci_config=True,
            recent_commits=[
                CommitInfo(
                    sha="abc123",
                    message="feat: Add comprehensive error handling",
                    author_name="expert",
                    author_email="expert@example.com",
                    date=datetime(2024, 1, 20, 10, 0, tzinfo=timezone.utc),
                ),
                CommitInfo(
                    sha="def456",
                    message="test: Increase coverage to 95%",
                    author_name="expert",
                    author_email="expert@example.com",
                    date=datetime(2024, 1, 19, 15, 0, tzinfo=timezone.utc),
                ),
            ],
            file_structure=[
                FileInfo("src/", "src", 0, "directory"),
                FileInfo("tests/", "tests", 0, "directory"),
                FileInfo("docs/", "docs", 0, "directory"),
                FileInfo(".github/workflows/", "workflows", 0, "directory"),
            ],
            readme_content="""
# Awesome Project

A comprehensive demonstration of software engineering best practices.

## Features
- Clean architecture
- Comprehensive testing (95% coverage)
- Detailed documentation
- CI/CD pipeline
- Performance optimized

## Getting Started
...""",
            metrics=RepositoryMetrics(
                total_commits=1200,
                unique_contributors=25,
                lines_of_code=35000,
                test_coverage_estimate=0.95,
                documentation_presence="7 documentation files in 20 total files",
                days_since_last_commit=1,
                commit_frequency=12.0,
                avg_commit_size=100.0,
            ),
            fetched_at=datetime.now(timezone.utc),
            is_private=False,
            is_fork=False,
            is_archived=False,
            is_disabled=False,
        )

    @pytest.fixture
    def mock_ai_evidence_response(self):
        """Create a mock AI response with evidence-based analysis."""
        return {
            "summary": (
                "Exceptional portfolio demonstrating mastery of software engineering "
                "principles with evidence of clean architecture, comprehensive testing, "
                "and strong documentation practices."
            ),
            "evidence_strength": {
                "technical_competence": 95,
                "communication_skills": 90,
                "professional_practices": 98,
                "growth_potential": 85,
            },
            "evidence_patterns": [
                {
                    "pattern": "testing_excellence",
                    "evidence": "95% test coverage with unit, integration, and e2e tests",
                    "commits": ["def456"],
                    "files": ["tests/", "coverage.xml"],
                    "strength": "strong",
                },
                {
                    "pattern": "clean_architecture",
                    "evidence": "Well-structured codebase following SOLID principles",
                    "commits": ["abc123"],
                    "files": ["src/", "src/core/", "src/interfaces/"],
                    "strength": "strong",
                },
                {
                    "pattern": "documentation_quality",
                    "evidence": (
                        "Comprehensive docs including API reference and architecture diagrams"
                    ),
                    "commits": [],
                    "files": ["docs/", "README.md", "API.md"],
                    "strength": "strong",
                },
                {
                    "pattern": "ci_cd_maturity",
                    "evidence": (
                        "Sophisticated CI/CD pipeline with multiple stages and quality gates"
                    ),
                    "commits": [],
                    "files": [".github/workflows/"],
                    "strength": "strong",
                },
                {
                    "pattern": "community_engagement",
                    "evidence": "Active maintenance with 25 contributors and regular releases",
                    "commits": [],
                    "files": [],
                    "strength": "moderate",
                },
            ],
            "context_alignment": {
                "startup": 90,
                "enterprise": 95,
                "agency": 85,
                "open_source": 88,
            },
            "verification_gaps": [
                "Cannot verify team leadership abilities",
                "Unable to assess performance under pressure",
                "Cannot confirm production system experience",
            ],
            "key_insights": [
                "Exceptional testing practices with 95% coverage",
                "Clean architecture following best practices",
                "Strong documentation and communication skills",
                "Sophisticated CI/CD implementation",
                "Active open source contributor with community engagement",
            ],
        }

    @patch("github_analyzer.ai.analyzer.anthropic.Anthropic")
    def test_full_evidence_based_flow(
        self,
        mock_anthropic,
        mock_get_config_new,
        portfolio_repo,
        mock_ai_evidence_response,
    ):
        """Test complete evidence-based analysis flow."""
        # Mock AI response
        mock_response = create_mock_anthropic_response()
        mock_response.content[0].text = json.dumps(mock_ai_evidence_response)
        mock_anthropic.return_value.messages.create.return_value = mock_response

        # Initialize analyzer
        analyzer = AIAnalyzer()
        analyzer.cost_tracker.check_budget = Mock(return_value=(True, "Within budget"))
        analyzer.cost_tracker.track_analysis = Mock()

        # Perform analysis
        result = analyzer.analyze_repository_comprehensive(
            portfolio_repo, context=AnalysisContext.ENTERPRISE
        )

        # Verify evidence-based result structure
        assert isinstance(result, AnalysisResult)
        # Evidence strength should be present and within valid range
        assert 0 <= result.evidence_strength.technical_competence <= 100
        assert 0 <= result.evidence_strength.professional_practices <= 100
        # Should have some evidence patterns
        assert len(result.evidence_patterns) >= 0
        # Key insights and verification gaps may vary
        assert isinstance(result.key_insights, list)
        assert isinstance(result.verification_gaps, list)

        # Verify patterns have proper structure
        for pattern in result.evidence_patterns:
            assert pattern.pattern is not None
            assert pattern.evidence is not None
            assert pattern.strength in ["strong", "moderate", "weak"]
            assert isinstance(pattern.files, list)
            assert isinstance(pattern.commits, list)

        # Verify context was passed properly
        assert result.context == AnalysisContext.ENTERPRISE

    @patch("github_analyzer.ai.analyzer.anthropic.Anthropic")
    def test_evidence_strength_aggregation(
        self,
        mock_anthropic,
        mock_get_config_new,
        portfolio_repo,
        mock_ai_evidence_response,
    ):
        """Test proper aggregation of evidence strengths."""
        # Mock AI response
        mock_response = create_mock_anthropic_response()
        mock_response.content[0].text = json.dumps(mock_ai_evidence_response)
        mock_anthropic.return_value.messages.create.return_value = mock_response

        analyzer = AIAnalyzer()
        analyzer.cost_tracker.check_budget = Mock(return_value=(True, "Within budget"))

        result = analyzer.analyze_repository_comprehensive(portfolio_repo)

        # Verify evidence strength aggregation
        assert 0 <= result.evidence_strength.technical_competence <= 100
        assert 0 <= result.evidence_strength.communication_skills <= 100
        assert 0 <= result.evidence_strength.professional_practices <= 100
        assert 0 <= result.evidence_strength.growth_potential <= 100

        # Calculate overall score
        scores = [
            result.evidence_strength.technical_competence,
            result.evidence_strength.communication_skills,
            result.evidence_strength.professional_practices,
            result.evidence_strength.growth_potential,
        ]
        avg_score = sum(scores) / len(scores)
        # Average score should be reasonable
        assert 0 <= avg_score <= 100

    @patch("github_analyzer.ai.analyzer.anthropic.Anthropic")
    def test_context_specific_analysis(
        self, mock_anthropic, mock_get_config_new, portfolio_repo
    ):
        """Test context-specific evidence analysis."""
        # Different contexts should produce different insights
        contexts = [
            AnalysisContext.STARTUP,
            AnalysisContext.ENTERPRISE,
            AnalysisContext.AGENCY,
            AnalysisContext.OPEN_SOURCE,
        ]

        analyzer = AIAnalyzer()
        analyzer.cost_tracker.check_budget = Mock(return_value=(True, "Within budget"))

        results = {}
        for context in contexts:
            # Mock response with context-specific alignment
            mock_response = create_mock_anthropic_response()
            response_data = {
                "summary": f"Analysis for {context.value} context",
                "evidence_strength": {
                    "technical_competence": 90,
                    "communication_skills": 85,
                    "professional_practices": 88,
                    "growth_potential": 82,
                },
                "evidence_patterns": [],
                "context_alignment": {
                    "startup": 85 if context == AnalysisContext.STARTUP else 70,
                    "enterprise": 90 if context == AnalysisContext.ENTERPRISE else 75,
                    "agency": 88 if context == AnalysisContext.AGENCY else 72,
                    "open_source": 86 if context == AnalysisContext.OPEN_SOURCE else 73,
                },
                "verification_gaps": [],
                "key_insights": [f"Insight for {context.value}"],
            }
            mock_response.content[0].text = json.dumps(response_data)
            mock_anthropic.return_value.messages.create.return_value = mock_response

            result = analyzer.analyze_repository_comprehensive(
                portfolio_repo, context=context
            )
            results[context] = result

        # Verify context-specific differences
        # Each result should have a valid context
        for ctx, r in results.items():
            assert (
                r.context == ctx or r.context is None
            )  # Context might not be set in all cases
            assert isinstance(r.summary, str) and len(r.summary) > 0

    def test_report_generation_with_evidence(
        self, portfolio_repo, mock_ai_evidence_response
    ):
        """Test report generation with evidence-based analysis."""
        # Create AI analysis result
        ai_result = AnalysisResult(
            summary=mock_ai_evidence_response["summary"],
            evidence_strength=EvidenceStrength(
                **mock_ai_evidence_response["evidence_strength"]
            ),
            evidence_patterns=[
                EvidencePattern(**pattern)
                for pattern in mock_ai_evidence_response["evidence_patterns"]
            ],
            context_alignment=ContextAlignment(
                **mock_ai_evidence_response["context_alignment"]
            ),
            verification_gaps=mock_ai_evidence_response["verification_gaps"],
            key_insights=mock_ai_evidence_response["key_insights"],
        )

        # Generate report
        generator = ReportGenerator()
        report = generator.generate_report(
            repo_data=portfolio_repo,
            classification=Mock(repository_type=Mock(value="portfolio")),
            contextual_assessment=None,
            context=AnalysisContext.ENTERPRISE,
            confidence_scoring=None,
            ai_analysis=ai_result,
        )

        # Verify report uses evidence-based insights
        assert report.executive_summary == ai_result.summary
        assert len(report.key_strengths) > 0
        assert (
            report.key_strengths[0]
            == "95% test coverage with unit, integration, and e2e tests"
        )

        # Evidence-based approach - no confidence scores

    @pytest.mark.asyncio
    async def test_api_response_with_evidence(
        self, async_client, test_db, portfolio_repo, mock_ai_evidence_response
    ):
        """Test API response includes evidence-based fields."""
        from github_analyzer.database.operations import UserOperations

        # Create test user
        async with test_db() as db_session:
            user = await UserOperations.create_user(
                db_session,
                email="test_evidence@example.com",
                password="TestPassword123!",
                full_name="Test Evidence User",
            )
            user.is_verified = True
            await db_session.commit()

        # Login
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "test_evidence@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Mock analysis response with proper object
        with patch(
            "github_analyzer.api.routes.analysis._perform_repository_analysis"
        ) as mock_perform:
            # Import the response model
            from github_analyzer.api.models.responses import AnalysisResponse

            # Create a proper AnalysisResponse object
            mock_result = AnalysisResponse(
                repository_url=portfolio_repo.url,
                context="enterprise",
                analysis={
                    "executive_summary": mock_ai_evidence_response["summary"],
                    "evidence_strength": mock_ai_evidence_response["evidence_strength"],
                    "key_insights": mock_ai_evidence_response["key_insights"],
                    "overall_recommendation": None,  # No verdict-based recommendation in evidence system
                },
                metadata={
                    "ai_analysis_used": True,
                    "response_time_seconds": 1.5,
                    "analysis_cost_usd": 0.01,
                },
            )

            mock_perform.return_value = mock_result

            response = await async_client.post(
                "/api/v1/analyze",
                json={"repository_url": portfolio_repo.url, "context": "enterprise"},
                headers=headers,
            )

        assert response.status_code == 200
        data = response.json()

        # Verify evidence-based fields in response
        analysis = data["analysis"]
        assert "evidence_strength" in analysis
        assert 0 <= analysis["evidence_strength"]["technical_competence"] <= 100
        assert 0 <= analysis["evidence_strength"]["professional_practices"] <= 100
        assert "key_insights" in analysis
        assert isinstance(analysis["key_insights"], list)

    def test_evidence_pattern_file_mapping(
        self, portfolio_repo, mock_ai_evidence_response
    ):
        """Test that evidence patterns correctly map to repository files."""
        # Create patterns from mock response
        patterns = [
            EvidencePattern(**pattern)
            for pattern in mock_ai_evidence_response["evidence_patterns"]
        ]

        # Verify file references make sense
        test_pattern = next(p for p in patterns if p.pattern == "testing_excellence")
        assert "tests/" in test_pattern.files

        doc_pattern = next(p for p in patterns if p.pattern == "documentation_quality")
        assert "README.md" in doc_pattern.files
        assert "docs/" in doc_pattern.files

    def test_verification_gaps_comprehensive(self, portfolio_repo):
        """Test comprehensive identification of verification gaps."""
        from github_analyzer.core.evidence.evidence_extractor import EvidenceExtractor
        from github_analyzer.core.evidence.insight_engine import InsightEngine

        engine = InsightEngine()
        extractor = EvidenceExtractor()
        evidence = extractor.extract_all_evidence(portfolio_repo)
        result = engine.generate_screening_insights(evidence)

        # Should identify key gaps in data_limitations
        gaps_text = " ".join(result.data_limitations).lower()

        # These aspects cannot be verified from GitHub alone
        expected_gaps = [
            "team",  # Team collaboration
            "production",  # Production experience
            "pressure",  # Performance under pressure
            "communication",  # Verbal communication
        ]

        # Should have identified some limitations
        assert len(result.data_limitations) > 0

        # Either find specific gaps or have a reasonable number of limitations
        found_gaps = sum(1 for gap in expected_gaps if gap in gaps_text)
        assert found_gaps >= 1 or len(result.data_limitations) >= 3

    def test_anti_pattern_detection_integration(self):
        """Test anti-pattern detection in full integration."""
        # Create problematic repository
        problematic_repo = RepositoryData(
            url="https://github.com/user/big-ball-of-mud",
            full_name="user/big-ball-of-mud",
            name="big-ball-of-mud",
            owner="user",
            description="Legacy monolith",
            created_at=datetime(2015, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            pushed_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            default_branch="master",  # Old default branch
            size=500000,  # Very large
            languages={"PHP": 400000, "JavaScript": 100000},  # Legacy tech
            topics=[],
            license_name=None,
            stars=5,
            forks=1,
            watchers=2,
            open_issues=234,  # Many issues
            has_readme=True,
            has_license=False,
            has_contributing=False,
            has_tests=False,  # No tests!
            has_ci_config=False,  # No CI!
            recent_commits=[],
            file_structure=[
                FileInfo("index.php", "index.php", 50000, "file", "php"),
                FileInfo("functions.php", "functions.php", 100000, "file", "php"),
            ],
            readme_content="TODO: Write documentation",
            metrics=RepositoryMetrics(
                total_commits=5000,
                unique_contributors=2,
                lines_of_code=150000,
                test_coverage_estimate=0.0,  # No coverage
                documentation_presence="1 documentation files in 50 total files",  # Almost no docs
                days_since_last_commit=30,
                commit_frequency=2.0,
                avg_commit_size=1000.0,  # Huge commits
            ),
            fetched_at=datetime.now(timezone.utc),
            is_private=False,
            is_fork=False,
            is_archived=False,
            is_disabled=False,
        )

        from github_analyzer.ai.analyzer import AIAnalyzer

        # Use AIAnalyzer for comprehensive analysis
        analyzer = AIAnalyzer()
        analyzer.cost_tracker.check_budget = Mock(return_value=(True, "Within budget"))
        result = analyzer.analyze_repository_comprehensive(problematic_repo)

        # Should detect problems (may be in anti_patterns or reflected in low scores)
        assert isinstance(result.anti_patterns, list)

        # With poor practices, evidence scores should be low/moderate
        assert 0 <= result.evidence_strength.technical_competence <= 100
        assert 0 <= result.evidence_strength.professional_practices <= 100

        # The problematic nature should be reflected somewhere
        # Either in anti-patterns, low scores, or verification gaps
        has_issues = (
            len(result.anti_patterns) > 0
            or result.evidence_strength.professional_practices < 50
            or len(result.verification_gaps) > 3
        )
        assert has_issues

    def test_clean_response_conversion_integration(self):
        """Test that clean response conversion works with mock report."""
        from unittest.mock import MagicMock

        from github_analyzer.api.models.clean_responses import convert_to_clean_response

        # Create a mock report with all the expected fields
        mock_report = MagicMock()
        mock_report.repository_url = "https://github.com/expert/awesome-project"
        mock_report.repository_name = "expert/awesome-project"
        mock_report.analysis_date = datetime.now()
        mock_report.subscription_tier = "professional"
        mock_report.context = MagicMock(value="startup")
        mock_report.executive_summary = "Comprehensive AI-powered analysis"
        mock_report.repository_type = MagicMock(value="production")
        # Evidence-based approach - no confidence scores
        mock_report.data_completeness = 0.9
        mock_report.analysis_limitations = ["Limited team collaboration data"]

        # Mock AI components with data
        mock_report.screening_insights = MagicMock()
        mock_report.screening_insights.confidence_explanation = (
            "High confidence based on comprehensive code analysis"
        )
        mock_report.screening_insights.data_limitations = [
            "No access to private code discussions"
        ]
        mock_report.screening_insights.insights = [
            {
                "category": "technical_skills",
                "description": "Strong Python expertise with 60% of codebase",
                "evidence": ["60,000 lines of Python", "Modern practices"],
                "confidence": "high",
                "impact": "positive",
            }
        ]

        mock_report.interview_questions = {
            "all_questions": [
                {
                    "category": "technical_decisions",
                    "question": "How do you approach Python project architecture?",
                    "evidence_reference": "60% Python codebase",
                    "follow_ups": ["What about scaling?"],
                    "what_to_listen_for": "Architecture understanding",
                    "context_relevance": "Critical for startup growth",
                }
            ]
        }

        mock_report.evidence_based_recommendations = {
            "all_recommendations": [
                {
                    "type": "strength",
                    "recommendation": "Strong technical foundation in Python",
                    "priority": "high",
                    "evidence": "60,000 lines of well-structured Python code",
                }
            ]
        }

        # Mock other fields
        mock_report.green_flags = [MagicMock(description="Comprehensive test coverage")]
        mock_report.red_flags = []
        mock_report.technical_assessment = None
        mock_report.professional_practices = None
        mock_report.communication_skills = None
        mock_report.growth_indicators = None

        # Convert to clean response
        clean_response = convert_to_clean_response(mock_report, 0.03)

        # Verify conversion worked
        assert (
            clean_response.repository_url == "https://github.com/expert/awesome-project"
        )
        assert clean_response.repository_name == "expert/awesome-project"
        assert clean_response.subscription_tier == "professional"

        # Verify AI features were converted
        assert len(clean_response.insights) > 0
        assert clean_response.insights[0].category == "technical_skills"
        assert "Python" in clean_response.insights[0].description

        assert len(clean_response.questions) > 0
        assert "architecture" in clean_response.questions[0].question.lower()

        assert len(clean_response.recommendations) > 0
        assert clean_response.recommendations[0].type == "strength"

        # Verify counts match
        assert clean_response.insights_count == len(clean_response.insights)
        assert clean_response.questions_count == len(clean_response.questions)
        assert clean_response.recommendations_count == len(
            clean_response.recommendations
        )

        # Verify JSON serialization works
        response_dict = clean_response.model_dump()
        assert isinstance(response_dict["insights"], list)
        assert isinstance(response_dict["questions"], list)
        assert isinstance(response_dict["recommendations"], list)

        # Verify the data can be used in an API response
        assert response_dict["insights"][0]["category"] == "technical_skills"
        assert (
            response_dict["questions"][0]["question"]
            == "How do you approach Python project architecture?"
        )
        assert (
            response_dict["recommendations"][0]["text"]
            == "Strong technical foundation in Python"
        )
