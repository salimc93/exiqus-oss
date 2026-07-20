"""
Integration tests for AI analyzer with business logic components.
"""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from github_analyzer.ai.analyzer import (
    AIAnalyzer,
    AnalysisResult,
    EvidenceStrength,
)
from github_analyzer.core.classifier import (
    AnalysisMethod,
    TemplateCategory,
)
from github_analyzer.core.context_analyzer import AnalysisContext
from github_analyzer.core.report_generator import ReportFormat
from github_analyzer.data.models import FileInfo, RepositoryData, RepositoryMetrics
from tests.conftest import create_mock_anthropic_response


def create_test_repo(**kwargs):
    """Helper to create test repository with defaults."""
    defaults = {
        "url": "https://github.com/user/test-repo",
        "full_name": "user/test-repo",
        "name": "test-repo",
        "owner": "user",
        "description": "Test repository",
        "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2024, 12, 20, tzinfo=timezone.utc),
        "pushed_at": datetime(2024, 12, 20, tzinfo=timezone.utc),
        "default_branch": "main",
        "size": 1000,
        "languages": {"Python": 50000},
        "topics": [],
        "license_name": None,
        "stars": 0,
        "forks": 0,
        "watchers": 0,
        "open_issues": 0,
        "has_readme": True,
        "has_license": False,
        "has_contributing": False,
        "has_tests": False,
        "has_ci_config": False,
        "recent_commits": [],
        "file_structure": [],
        "readme_content": "# Test Repository",
        "metrics": RepositoryMetrics(
            total_commits=10,
            unique_contributors=1,
            lines_of_code=1000,
            test_coverage_estimate=0.0,
            documentation_presence="1 documentation files in 10 total files",
            days_since_last_commit=30,
            commit_frequency=1.0,
            avg_commit_size=100.0,
        ),
        "fetched_at": datetime.now(timezone.utc),
        "is_private": False,
        "is_fork": False,
        "is_archived": False,
        "is_disabled": False,
    }
    defaults.update(kwargs)
    return RepositoryData(**defaults)


@pytest.fixture
def high_quality_repo():
    """Create a high-quality repository for testing."""
    return create_test_repo(
        name="excellent-project",
        full_name="user/excellent-project",
        description="A well-maintained project with excellent practices",
        size=5000,
        stars=50,
        forks=10,
        has_readme=True,
        has_license=True,
        has_tests=True,
        has_ci_config=True,
        has_contributing=True,
        readme_content="# Excellent Project\n\n"
        + "Comprehensive documentation.\n" * 100,
        file_structure=[
            FileInfo(path="src", name="src", size=0, type="directory"),
            FileInfo(path="tests", name="tests", size=0, type="directory"),
            FileInfo(path="docs", name="docs", size=0, type="directory"),
            FileInfo(
                path="src/main.py",
                name="main.py",
                size=3000,
                type="file",
                extension="py",
            ),
            FileInfo(
                path="tests/test_main.py",
                name="test_main.py",
                size=2000,
                type="file",
                extension="py",
                is_test=True,
            ),
            FileInfo(
                path=".github/workflows/ci.yml",
                name="ci.yml",
                size=500,
                type="file",
                extension="yml",
            ),
        ],
        languages={"Python": 80000, "JavaScript": 20000, "TypeScript": 10000},
        metrics=RepositoryMetrics(
            total_commits=150,
            unique_contributors=8,
            lines_of_code=15000,
            test_coverage_estimate=0.90,
            documentation_presence="3 documentation files in 12 total files",
            days_since_last_commit=2,
            commit_frequency=6.0,
            avg_commit_size=150.0,
        ),
    )


@pytest.fixture
def abandoned_repo():
    """Create an abandoned repository for testing."""
    return create_test_repo(
        name="old-project",
        full_name="user/old-project",
        description="Old abandoned project",
        size=200,
        stars=0,
        forks=0,
        has_readme=False,
        has_license=False,
        has_tests=False,
        has_ci_config=False,
        readme_content=None,
        file_structure=[
            FileInfo(
                path="old_script.py",
                name="old_script.py",
                size=500,
                type="file",
                extension="py",
            ),
        ],
        languages={"Python": 5000},
        metrics=RepositoryMetrics(
            total_commits=2,
            unique_contributors=1,
            lines_of_code=500,
            test_coverage_estimate=0.0,
            documentation_presence="0 documentation files found",
            days_since_last_commit=900,  # Over 2 years
            commit_frequency=0.05,
            avg_commit_size=25.0,
        ),
    )


class TestAIAnalyzerIntegration:
    """Test AI analyzer integration with business logic components."""

    @patch("github_analyzer.ai.analyzer.anthropic.Anthropic")
    def test_analyzer_initialization(self, mock_anthropic, mock_get_config_new):
        """Test analyzer initialization with all business logic components."""
        analyzer = AIAnalyzer()

        # Check all business logic components are initialized
        assert analyzer.classifier is not None
        assert analyzer.context_analyzer is not None
        assert analyzer.report_generator is not None
        assert analyzer.confidence_scorer is not None
        assert analyzer.cost_tracker is not None

    @patch("github_analyzer.ai.analyzer.anthropic.Anthropic")
    def test_comprehensive_analysis_high_quality_repo(
        self, mock_anthropic, mock_get_config_new, high_quality_repo
    ):
        """Test comprehensive analysis of high-quality repository."""
        # Mock AI response for complex repository
        mock_response = create_mock_anthropic_response(
            verdict="HIRE",
            confidence=85,
            summary="Excellent repository with strong technical practices",
        )
        # Update response to use evidence-based format
        mock_response.content[0].text = (
            '{"summary": "Excellent repository with strong technical practices", '
            '"evidence_strength": {'
            '"technical_competence": 85, '
            '"communication_skills": 80, '
            '"professional_practices": 90, '
            '"growth_potential": 75'
            "}, "
            '"evidence_patterns": ['
            '{"pattern": "strong_practices", "evidence": "Excellent technical implementation", "commits": [], "files": [], "strength": "strong"}'
            "], "
            '"context_alignment": {}, '
            '"verification_gaps": [], '
            '"key_insights": ["Strong technical practices", "Well-structured code"]'
            "}"
        )
        mock_anthropic.return_value.messages.create.return_value = mock_response

        analyzer = AIAnalyzer()

        # Mock cost tracker to allow AI analysis
        analyzer.cost_tracker.check_budget = Mock(return_value=(True, "Within budget"))
        analyzer.cost_tracker.track_analysis = Mock()

        # Run comprehensive analysis with startup context
        result = analyzer.analyze_repository_comprehensive(
            high_quality_repo,
            context=AnalysisContext.STARTUP,
            format_type=ReportFormat.JSON,
        )

        # Verify result structure
        assert isinstance(result, AnalysisResult)
        assert hasattr(result, "evidence_strength")
        assert result.evidence_strength.technical_competence > 0
        assert result.generated_by == "comprehensive"
        assert result.context == AnalysisContext.STARTUP

        # Verify business logic components are included
        assert result.classification_result is not None
        assert result.structured_report is not None
        assert result.confidence_scoring is not None

        # For high-quality repo, should have contextual assessment
        assert result.contextual_assessment is not None
        assert result.contextual_assessment.context == AnalysisContext.STARTUP

        # Verify legacy compatibility fields
        assert result.repository_type is not None
        # trust_score removed in evidence-based approach
        assert result.risk_level is not None

    @patch("github_analyzer.ai.analyzer.anthropic.Anthropic")
    def test_comprehensive_analysis_abandoned_repo(
        self, mock_anthropic, mock_get_config_new, abandoned_repo
    ):
        """Test comprehensive analysis of abandoned repository."""
        analyzer = AIAnalyzer()

        # Run comprehensive analysis (should use template, not AI)
        result = analyzer.analyze_repository_comprehensive(abandoned_repo)

        # Verify result
        assert hasattr(result, "evidence_strength")
        assert (
            result.evidence_strength.technical_competence <= 50
        )  # Low score for abandoned repos
        assert result.generated_by == "comprehensive"
        assert result.cost == 0.0  # No AI cost for template analysis

        # Verify classification detected abandonment
        assert result.classification_result is not None
        assert result.classification_result.method == AnalysisMethod.TEMPLATE
        # Abandoned repo with only 1 file is classified as EMPTY
        assert result.classification_result.template_category == TemplateCategory.EMPTY

        # Verify high risk indicators
        assert result.confidence_scoring is not None
        assert result.risk_level in ["high", "critical"]

    @patch("github_analyzer.ai.analyzer.anthropic.Anthropic")
    def test_template_result_generation(self, mock_anthropic, mock_get_config_new):
        """Test template result generation for different categories."""
        analyzer = AIAnalyzer()

        # Test abandoned category
        mock_classification = Mock()
        mock_classification.template_category = Mock()
        mock_classification.template_category.value = "abandoned"

        test_repo = create_test_repo()
        result = analyzer._generate_template_result(test_repo, mock_classification)

        assert hasattr(result, "evidence_strength")
        assert (
            result.evidence_strength.technical_competence <= 50
        )  # Low score for abandoned
        assert "insufficient development activity" in result.summary.lower()
        assert len(result.verification_gaps) > 0
        assert result.cost == 0.0

    @patch("github_analyzer.ai.analyzer.anthropic.Anthropic")
    def test_context_comparison_analysis(
        self, mock_anthropic, mock_get_config_new, high_quality_repo
    ):
        """Test analysis with different contexts produces different results."""
        # Mock AI response
        mock_response = create_mock_anthropic_response(
            verdict="HIRE", confidence=85, summary="Excellent repository"
        )
        mock_anthropic.return_value.messages.create.return_value = mock_response

        analyzer = AIAnalyzer()
        analyzer.cost_tracker.check_budget = Mock(return_value=(True, "Within budget"))
        analyzer.cost_tracker.track_analysis = Mock()

        # Analyze with different contexts
        startup_result = analyzer.analyze_repository_comprehensive(
            high_quality_repo, context=AnalysisContext.STARTUP
        )
        enterprise_result = analyzer.analyze_repository_comprehensive(
            high_quality_repo, context=AnalysisContext.ENTERPRISE
        )

        # Results should have different contextual assessments
        assert startup_result.contextual_assessment.context == AnalysisContext.STARTUP
        assert (
            enterprise_result.contextual_assessment.context
            == AnalysisContext.ENTERPRISE
        )

        # Context-specific insights should be different
        # fit_score removed in evidence-based approach
        assert startup_result.contextual_assessment.strengths
        assert enterprise_result.contextual_assessment.strengths

        # Context strengths should be lists of evidence
        assert isinstance(startup_result.contextual_assessment.strengths, list)
        assert isinstance(enterprise_result.contextual_assessment.strengths, list)

    @patch("github_analyzer.ai.analyzer.anthropic.Anthropic")
    def test_analysis_result_serialization(
        self, mock_anthropic, mock_get_config_new, high_quality_repo
    ):
        """Test serialization of comprehensive analysis result."""
        # Mock AI response
        mock_response = create_mock_anthropic_response(
            verdict="HIRE", confidence=90, summary="Excellent project"
        )
        # Update response to use evidence-based format
        mock_response.content[0].text = (
            '{"summary": "Excellent project", '
            '"evidence_strength": {'
            '"technical_competence": 90, '
            '"communication_skills": 85, '
            '"professional_practices": 95, '
            '"growth_potential": 80'
            "}, "
            '"evidence_patterns": [], '
            '"context_alignment": {}, '
            '"verification_gaps": [], '
            '"key_insights": []'
            "}"
        )
        mock_anthropic.return_value.messages.create.return_value = mock_response

        analyzer = AIAnalyzer()
        analyzer.cost_tracker.check_budget = Mock(return_value=(True, "Within budget"))
        analyzer.cost_tracker.track_analysis = Mock()

        result = analyzer.analyze_repository_comprehensive(
            high_quality_repo, context=AnalysisContext.STARTUP
        )

        # Test serialization
        result_dict = result.to_dict()

        # Check basic fields
        assert "evidence_strength" in result_dict
        assert "summary" in result_dict
        assert "repository_type" in result_dict
        assert "context" in result_dict
        # Evidence-based confidence structure - trust_score removed in The Great Purge
        if "confidence_scoring" in result_dict:
            assert "trust_explanation" in result_dict["confidence_scoring"]
            assert "overall_risk_level" in result_dict["confidence_scoring"]

        # Check business logic components
        assert "classification" in result_dict
        assert "contextual_assessment" in result_dict
        assert "structured_report" in result_dict
        assert "confidence_scoring" in result_dict

        # Verify nested structure
        assert result_dict["contextual_assessment"]["context"] == "startup"
        # fit_score removed in evidence-based approach
        assert "strengths" in result_dict["contextual_assessment"]
        assert "confidence_explanation" in result_dict["confidence_scoring"]
        assert "overall_risk_level" in result_dict["confidence_scoring"]

    @patch("github_analyzer.ai.analyzer.anthropic.Anthropic")
    def test_analysis_without_context(
        self, mock_anthropic, mock_get_config_new, high_quality_repo
    ):
        """Test comprehensive analysis without providing hiring context."""
        # Mock AI response
        mock_response = create_mock_anthropic_response(
            verdict="HIRE", confidence=80, summary="Good repository"
        )
        mock_anthropic.return_value.messages.create.return_value = mock_response

        analyzer = AIAnalyzer()
        analyzer.cost_tracker.check_budget = Mock(return_value=(True, "Within budget"))
        analyzer.cost_tracker.track_analysis = Mock()

        result = analyzer.analyze_repository_comprehensive(high_quality_repo)

        # Should still work without contextual assessment
        assert result.context is None
        assert result.contextual_assessment is None
        assert result.classification_result is not None
        assert result.structured_report is not None
        assert result.confidence_scoring is not None

    @patch("github_analyzer.ai.analyzer.anthropic.Anthropic")
    def test_budget_exceeded_handling(
        self, mock_anthropic, mock_get_config_new, high_quality_repo
    ):
        """Test handling when AI analysis would exceed budget."""

        analyzer = AIAnalyzer()

        # Mock classifier to force AI analysis
        mock_classification = Mock()
        mock_classification.method.value = "ai"
        mock_classification.confidence = 0.85
        mock_classification.repository_type = Mock()
        mock_classification.repository_type.value = "portfolio"
        mock_classification.reasoning = "Complex repository requiring AI analysis"
        mock_classification.cost_estimate = 0.015
        analyzer.classifier.classify = Mock(return_value=mock_classification)

        # Mock the _estimate_cost method directly to avoid context preparation issues
        analyzer._estimate_cost = Mock(return_value=0.05)

        # Mock budget check to fail
        analyzer.cost_tracker.check_budget = Mock(
            return_value=(False, "Budget exceeded")
        )

        # Should raise exception for AI-requiring repository
        with pytest.raises(Exception, match="Budget exceeded"):
            analyzer.analyze_repository_comprehensive(high_quality_repo)

    def test_analysis_result_validation(self):
        """Test AnalysisResult validation."""
        # Valid result
        result = AnalysisResult(
            summary="Good candidate",
            evidence_strength=EvidenceStrength(
                technical_competence=85,
                communication_skills=80,
                professional_practices=90,
                growth_potential=75,
            ),
        )
        assert result.evidence_strength.technical_competence == 85
        assert result.summary == "Good candidate"

    def test_enhanced_analysis_result_fields(self):
        """Test enhanced AnalysisResult fields are properly handled."""
        from github_analyzer.ai.analyzer import ContextAlignment, EvidencePattern

        result = AnalysisResult(
            summary="Excellent candidate with strong evidence",
            evidence_strength=EvidenceStrength(
                technical_competence=90,
                communication_skills=85,
                professional_practices=95,
                growth_potential=80,
            ),
            evidence_patterns=[
                EvidencePattern(
                    pattern="Technical Excellence",
                    evidence="Strong Python skills with test coverage",
                    strength="strong",
                )
            ],
            context_alignment=ContextAlignment(),
            key_insights=["Strong technical foundation", "Good testing practices"],
            areas_to_explore=["Leadership experience", "Team collaboration"],
        )

        # Test evidence-based fields
        assert result.summary == "Excellent candidate with strong evidence"
        assert result.evidence_strength.technical_competence == 90
        assert len(result.evidence_patterns) == 1
        assert result.evidence_patterns[0].pattern == "Technical Excellence"
        assert len(result.key_insights) == 2
        assert len(result.areas_to_explore) == 2
