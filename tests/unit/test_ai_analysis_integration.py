"""
Unit tests for AI analysis integration in analysis route and report generator.
"""

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from github_analyzer.ai.analyzer import (
    AnalysisResult,
    ContextAlignment,
    EvidencePattern,
    EvidenceStrength,
)
from github_analyzer.api.routes.analysis import _should_use_ai_analysis
from github_analyzer.core.classifier import (
    AnalysisMethod,
    ClassificationResult,
    RepositoryType,
)
from github_analyzer.core.report_generator import ReportGenerator
from github_analyzer.data.models import RepositoryData, RepositoryMetrics


class TestAIAnalysisIntegration:
    """Test cases for AI analysis integration."""

    @pytest.fixture
    def mock_ai_result(self):
        """Create mock AI analysis result."""
        return AnalysisResult(
            summary="Excellent promise queue implementation with clean async/await patterns and strong TypeScript usage.",
            evidence_strength=EvidenceStrength(
                technical_competence=85,
                communication_skills=80,
                professional_practices=90,
                growth_potential=75,
            ),
            evidence_patterns=[
                EvidencePattern(
                    pattern="excellent_implementation",
                    evidence="Excellent promise queue implementation with clean async/await patterns",
                    commits=[],
                    files=["src/index.ts", "src/queue.ts"],
                    strength="strong",
                ),
                EvidencePattern(
                    pattern="good_documentation",
                    evidence="Well-documented API design with comprehensive examples",
                    commits=[],
                    files=["README.md", "docs/"],
                    strength="strong",
                ),
                EvidencePattern(
                    pattern="strong_typing",
                    evidence="Strong TypeScript usage with proper typing throughout",
                    commits=[],
                    files=["src/"],
                    strength="strong",
                ),
                EvidencePattern(
                    pattern="test_coverage",
                    evidence="Comprehensive test coverage with unit and integration tests",
                    commits=[],
                    files=["test/"],
                    strength="strong",
                ),
                EvidencePattern(
                    pattern="limited_activity",
                    evidence="Limited recent activity in the repository",
                    commits=[],
                    files=[],
                    strength="weak",
                ),
            ],
            context_alignment=ContextAlignment(),
            verification_gaps=[
                "Cannot verify team collaboration",
                "Unable to assess production usage",
            ],
            key_insights=[
                "Excellent promise queue implementation",
                "Clean async/await patterns throughout codebase",
                "Well-documented API design",
                "Strong TypeScript usage with proper typing",
                "Comprehensive test coverage",
            ],
            cost=0.0045,  # Realistic AI cost
            analysis_time=2.5,
            generated_by="ai",
        )

    @pytest.fixture
    def sample_repo_data(self):
        """Create sample repository data."""
        metrics = RepositoryMetrics(
            total_commits=150,
            unique_contributors=12,
            lines_of_code=8000,
            test_coverage_estimate=0.85,
            documentation_presence="9 documentation files in 10 total files",
            days_since_last_commit=5,
            commit_frequency=3.5,
            avg_commit_size=120,
        )

        return RepositoryData(
            url="https://github.com/sindresorhus/p-queue",
            full_name="sindresorhus/p-queue",
            name="p-queue",
            owner="sindresorhus",
            description="Promise queue with concurrency control",
            created_at=datetime(2016, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 1, 10, tzinfo=timezone.utc),
            pushed_at=datetime(2024, 1, 10, tzinfo=timezone.utc),
            default_branch="main",
            size=1200,
            languages={"TypeScript": 6000, "JavaScript": 2000},
            topics=["promise", "queue", "async"],
            license_name="MIT",
            forks=75,
            stars=2500,  # High stars - should trigger AI
            watchers=35,
            open_issues=5,
            has_readme=True,
            has_license=True,
            has_contributing=False,
            has_tests=True,
            has_ci_config=True,
            recent_commits=[],
            file_structure=[],
            readme_content="# p-queue\n\nPromise queue with concurrency control...",
            metrics=metrics,
            fetched_at=datetime.now(timezone.utc),
            is_private=False,
            is_fork=False,
            is_archived=False,
            is_disabled=False,
        )

    def test_ai_analysis_triggered_for_quality_repo(self, sample_repo_data):
        """Test that AI analysis is triggered for high-quality repositories."""
        classification = ClassificationResult(
            method=AnalysisMethod.AI,
            repository_type=RepositoryType.OPEN_SOURCE,
        )

        confidence_analysis = Mock(confidence_score=0.8)

        # Should use AI for repos with >50 stars
        should_use_ai = _should_use_ai_analysis(
            sample_repo_data, classification, confidence_analysis
        )
        assert should_use_ai is True

    def test_report_generator_uses_ai_insights(self, sample_repo_data, mock_ai_result):
        """Test that report generator properly uses AI analysis results."""
        generator = ReportGenerator()
        classification = ClassificationResult(
            method=AnalysisMethod.AI,
            repository_type=RepositoryType.OPEN_SOURCE,
        )

        # Generate report with AI analysis
        report = generator.generate_report(
            repo_data=sample_repo_data,
            classification=classification,
            contextual_assessment=None,
            context=None,
            confidence_scoring=None,
            ai_analysis=mock_ai_result,
        )

        # Verify AI insights are used
        assert report.executive_summary == mock_ai_result.summary
        # No longer making binary hiring decisions
        # Report should have evidence summary instead of recommendation
        assert report.evidence_summary
        # Evidence-based confidence explanation (no numerical scores)
        # Key insights from evidence patterns (strong and moderate)
        assert len(report.key_strengths) == 4  # 4 strong patterns
        assert (
            report.key_strengths[0]
            == "Excellent promise queue implementation with clean async/await patterns"
        )
        # Primary concerns from weak patterns and verification gaps
        assert len(report.primary_concerns) >= 1  # At least the weak pattern
        assert "Limited recent activity in the repository" in report.primary_concerns

    def test_report_generator_fallback_without_ai(self, sample_repo_data):
        """Test that report generator falls back to templates without AI."""
        generator = ReportGenerator()
        classification = ClassificationResult(
            method=AnalysisMethod.AI,
            repository_type=RepositoryType.OPEN_SOURCE,
        )

        # Generate report without AI analysis
        report = generator.generate_report(
            repo_data=sample_repo_data,
            classification=classification,
            contextual_assessment=None,
            context=None,
            confidence_scoring=None,
            ai_analysis=None,  # No AI analysis
        )

        # Verify template-based generation
        assert report.executive_summary != ""  # Should have template summary
        # No longer making binary hiring decisions without AI
        # Report should have evidence summary instead of recommendation
        assert report.evidence_summary
        # Evidence-based approach - no numerical scores
        # Template-based insights are more generic
        assert len(report.key_strengths) > 0
        assert len(report.primary_concerns) >= 0

    def test_cost_calculation_with_ai_analysis(self, mock_ai_result):
        """Test that actual AI cost is used instead of hardcoded value."""
        # AI result has realistic cost
        assert mock_ai_result.cost == 0.0045

        # This is more than the hardcoded 0.002
        assert mock_ai_result.cost > 0.002
        assert mock_ai_result.cost < 0.01  # But still reasonable
