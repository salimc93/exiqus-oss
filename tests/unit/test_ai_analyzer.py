"""
Unit tests for AI analysis module.
"""

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
from github_analyzer.data.models import FileInfo, RepositoryData, RepositoryMetrics
from tests.conftest import create_mock_anthropic_response


class TestAIAnalyzer:
    """Test cases for AIAnalyzer class."""

    @pytest.fixture
    def analyzer(self, mock_get_config_new):
        """Create AIAnalyzer instance."""
        return AIAnalyzer()

    @pytest.fixture
    def sample_repo_data(self):
        """Create sample repository data for testing."""
        metrics = RepositoryMetrics(
            total_commits=50,
            unique_contributors=5,
            lines_of_code=5000,
            test_coverage_estimate=0.8,
            documentation_presence="9 documentation files in 10 total files",
            days_since_last_commit=10,
            commit_frequency=2.5,
            avg_commit_size=150,
        )

        return RepositoryData(
            url="https://github.com/user/complex-project",
            full_name="user/complex-project",
            name="complex-project",
            owner="user",
            description="A complex web application with multiple services",
            created_at=datetime(2022, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            pushed_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            default_branch="main",
            size=2500,
            languages={"Python": 5000, "JavaScript": 3000, "CSS": 1000},
            topics=["web-app", "python"],
            license_name="MIT",
            stars=25,
            forks=8,
            watchers=15,
            open_issues=3,
            has_readme=True,
            has_license=True,
            has_contributing=True,
            has_tests=True,
            has_ci_config=True,
            recent_commits=[],
            file_structure=[
                FileInfo("app.py", "app.py", 2000, "file", "py"),
                FileInfo("tests/", "tests", 0, "dir", None),
                FileInfo("requirements.txt", "requirements.txt", 500, "file", "txt"),
            ],
            readme_content="A comprehensive web application...",
            metrics=metrics,
            fetched_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            is_private=False,
            is_fork=False,
            is_archived=False,
            is_disabled=False,
        )

    def test_analyzer_initialization(self, analyzer):
        """Test AIAnalyzer initialization."""
        assert analyzer is not None
        assert hasattr(analyzer, "anthropic_client")
        assert hasattr(analyzer, "cost_tracker")

    @patch("github_analyzer.ai.analyzer.anthropic.Anthropic")
    def test_analyze_repository_success(
        self, mock_anthropic, analyzer, sample_repo_data
    ):
        """Test successful repository analysis."""
        # Mock Anthropic client response
        mock_client = Mock()
        mock_response = create_mock_anthropic_response(
            verdict="HIRE", confidence=85, summary="Great repo"
        )
        # Update the response format for the evidence-based JSON test
        # Must match expected structure: observed_patterns, limitations, context_notes, upgrade_benefit
        mock_response.content[0].text = (
            '{"summary": "Great repository with evidence-based analysis", '
            '"observed_patterns": ['
            '{"pattern": "good_tests", "evidence": "Good test coverage", "commits": [], "files": ["tests/"]}'
            "], "
            '"limitations": ["Cannot assess team collaboration"], '
            '"context_notes": "Good repository structure with clear patterns", '
            '"upgrade_benefit": "Deeper analysis would provide more comprehensive patterns", '
            '"key_insights": ["Good tests", "Well structured"]'
            "}"
        )

        mock_client.messages.create.return_value = mock_response
        analyzer.anthropic_client = mock_client

        result = analyzer.analyze_repository(sample_repo_data)

        assert isinstance(result, AnalysisResult)
        assert hasattr(result, "evidence_strength")
        # Evidence-based approach: no numerical scores
        assert result.evidence_strength.technical_competence == 0
        assert result.evidence_strength.professional_practices == 0
        assert result.summary == "Great repository with evidence-based analysis"
        assert result.cost > 0
        assert len(result.key_insights) > 0

    def test_prepare_analysis_context(self, analyzer, sample_repo_data):
        """Test context preparation for AI analysis."""
        context = analyzer._prepare_context(sample_repo_data)

        assert isinstance(context, str)
        assert sample_repo_data.full_name in context
        assert sample_repo_data.description in context
        assert "Python" in context  # Should include main language
        assert str(sample_repo_data.metrics.total_commits) in context

    def test_context_length_management(self, analyzer, sample_repo_data):
        """Test that context stays within token limits."""
        # Create repo with very large README
        sample_repo_data.readme_content = "A" * 20000  # Large content

        context = analyzer._prepare_context(sample_repo_data)

        # Context should be truncated to stay within limits
        assert len(context) <= analyzer.max_context_length

    def test_cost_tracking(self, analyzer, sample_repo_data):
        """Test that cost tracking works properly."""
        with patch.object(analyzer.cost_tracker, "track_analysis") as mock_track:
            # Mock successful analysis
            mock_client = Mock()
            mock_response = create_mock_anthropic_response(
                verdict="HIRE", confidence=85, summary="Great repo"
            )
            # Update the response format for the evidence-based JSON test
            mock_response.content[0].text = (
                '{"summary": "Great repo", '
                '"evidence_strength": {'
                '"technical_competence": 85, '
                '"communication_skills": 80, '
                '"professional_practices": 90, '
                '"growth_potential": 75'
                "}, "
                '"evidence_patterns": [], '
                '"context_alignment": {}, '
                '"verification_gaps": [], '
                '"key_insights": []'
                "}"
            )

            mock_client.messages.create.return_value = mock_response
            analyzer.anthropic_client = mock_client

            analyzer.analyze_repository(sample_repo_data)

            mock_track.assert_called_once()
            # Verify that track_analysis was called with an APIUsage object
            call_args = mock_track.call_args[0][0]
            assert hasattr(call_args, "input_tokens")
            assert hasattr(call_args, "output_tokens")
            assert call_args.input_tokens == 1000
            assert call_args.output_tokens == 500

    def test_analysis_error_handling(self, analyzer, sample_repo_data):
        """Test error handling during analysis."""
        with patch("github_analyzer.ai.analyzer.anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.side_effect = Exception("API Error")
            mock_anthropic.return_value = mock_client

            with pytest.raises(Exception):
                analyzer.analyze_repository(sample_repo_data)


class TestAnalysisResult:
    """Test cases for AnalysisResult class."""

    def test_analysis_result_creation(self):
        """Test AnalysisResult creation."""
        result = AnalysisResult(
            summary="Great repository with good practices",
            evidence_strength=EvidenceStrength(
                technical_competence=85,
                communication_skills=80,
                professional_practices=90,
                growth_potential=75,
            ),
            evidence_patterns=[
                EvidencePattern(
                    pattern="documentation",
                    evidence="Well documented",
                    commits=[],
                    files=["README.md"],
                    strength="strong",
                ),
                EvidencePattern(
                    pattern="testing",
                    evidence="Has tests",
                    commits=[],
                    files=["tests/"],
                    strength="strong",
                ),
            ],
            context_alignment=ContextAlignment(),
            verification_gaps=["Minor code quality issues"],
            key_insights=["Well documented", "Has tests"],
            cost=0.015,
        )

        assert result.evidence_strength.technical_competence == 85
        assert result.cost == 0.015
        assert len(result.evidence_patterns) == 2
        assert len(result.key_insights) == 2
        assert len(result.verification_gaps) == 1

    def test_analysis_result_to_dict(self):
        """Test AnalysisResult serialization."""
        result = AnalysisResult(
            summary="Mixed signals",
            evidence_strength=EvidenceStrength(
                technical_competence=65,
                communication_skills=60,
                professional_practices=70,
                growth_potential=65,
            ),
            cost=0.012,
        )

        result_dict = result.to_dict()

        assert "evidence_strength" in result_dict
        assert result_dict["evidence_strength"]["technical_competence"] == 65
        assert result_dict["cost"] == 0.012
        assert "summary" in result_dict

    def test_analysis_result_validation(self):
        """Test AnalysisResult validation with evidence-based format."""
        # Test valid creation with minimal fields
        result = AnalysisResult(
            summary="Test analysis",
            evidence_strength=EvidenceStrength(
                technical_competence=85,
                communication_skills=80,
                professional_practices=90,
                growth_potential=75,
            ),
        )
        assert result is not None

        # Test with all fields
        result_full = AnalysisResult(
            summary="Full analysis",
            evidence_strength=EvidenceStrength(),
            evidence_patterns=[],
            context_alignment=ContextAlignment(),
            verification_gaps=[],
            key_insights=[],
            cost=0.01,
        )
        assert result_full is not None
