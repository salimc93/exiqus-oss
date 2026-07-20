"""
Tests for PR Report Generator.
"""

from datetime import datetime, timezone

import pytest

from src.github_analyzer.data.pr_models import PREvidence, QualitySignals
from src.github_analyzer.data.pr_report_generator import PRReportGenerator


class TestPRReportGenerator:
    """Test PR report generation."""

    @pytest.fixture
    def generator(self):
        """Create report generator instance."""
        return PRReportGenerator()

    @pytest.fixture
    def sample_evidence(self):
        """Create sample evidence for testing."""
        evidence = PREvidence()
        evidence.technical_substance = [
            "Production Integration Success: 10/12 PRs successfully merged (83% success rate)",
            "MAJOR SUCCESS: PR #123 'Implement caching system' - 50 commits, 2,500+ additions (MERGED)",
            "Long-term commitment: 6+ months of sustained contributions",
        ]
        evidence.collaboration_patterns = [
            "Sustained contributions over 180 days",
            "Pair programming: PRs co-authored with 3 different developers",
            "Deep collaboration: 5 PRs with 3+ review cycles",
        ]
        evidence.cross_repo_contributions = [
            "Cross-Repository Adaptability: Active in 3 different repositories",
            "Repositories: org/repo1 (5 PRs), org/repo2 (4 PRs), org/repo3 (3 PRs)",
        ]
        evidence.review_responsiveness = [
            "Persistent Review Engagement: 8 PRs merged after extensive review cycles",
            "Persisted through 5+ reviews on PR #456 (eventually merged)",
        ]
        evidence.integration_patterns = [
            "Branch patterns: 7 feature branches, 5 fix branches",
            "Consistent use of conventional branch naming",
        ]
        evidence.pr_description_quality = [
            "Provides detailed descriptions (avg 200+ characters)",
            "Clear problem statements and solution approaches",
        ]
        evidence.process_adherence = [
            "Uses conventional commit format in 75% of PRs",
            "Consistent PR title formatting",
        ]
        evidence.areas_to_explore = [
            "Large unmerged PR #789 with 3,000+ additions needs discussion",
            "Review patterns in collaborative features",
        ]
        return evidence

    @pytest.fixture
    def sample_signals(self):
        """Create sample quality signals for testing."""
        now = datetime.now(timezone.utc)
        return QualitySignals(
            total_prs=12,
            merged_prs=10,
            unique_repos=3,
            feature_prs=7,
            fix_prs=5,
            pair_programming_count=2,
            deep_collaboration_count=5,
            feature_ownership_count=3,
            first_pr_date=datetime(2024, 3, 1, tzinfo=timezone.utc),
            last_pr_date=now,
            contribution_timespan="6 months",
            monthly_pr_rate=2.0,
        )

    def test_generator_initialization(self):
        """Test generator initializes properly."""
        generator = PRReportGenerator()
        assert generator is not None

    def test_generate_summary_report(self, generator, sample_evidence, sample_signals):
        """Test summary report generation."""
        report = generator.generate_summary_report(
            username="testuser",
            evidence=sample_evidence,
            quality_signals=sample_signals,
            context="STARTUP",
        )

        # Check report structure
        assert "# PR Analysis Report: testuser" in report
        assert "**Context**: STARTUP" in report
        assert "## Executive Summary" in report

        # Check evidence sections are included
        assert "## Technical Contribution Patterns" in report
        assert "## Collaboration & Team Dynamics" in report
        assert "## Cross-Repository Adaptability" in report
        assert "## Review Process Engagement" in report
        assert "## Integration Practices" in report
        assert "## Quality Indicators" in report
        assert "## Areas for Further Discussion" in report

        # Check specific evidence is included
        assert "Production Integration Success" in report
        assert "Sustained contributions" in report
        assert "Cross-Repository Adaptability" in report

    def test_generate_detailed_report(self, generator, sample_evidence, sample_signals):
        """Test detailed report generation."""
        report = generator.generate_detailed_report(
            username="testuser",
            evidence=sample_evidence,
            quality_signals=sample_signals,
            context="ENTERPRISE",
            include_all_evidence=False,
        )

        # Check report structure
        assert report["username"] == "testuser"
        assert report["context"] == "ENTERPRISE"
        assert "generated_at" in report
        assert "summary" in report
        assert "evidence_sections" in report
        assert "quality_signals" in report

        # Check evidence sections
        sections = report["evidence_sections"]
        assert "technical_substance" in sections
        assert (
            sections["technical_substance"]["title"]
            == "Technical Contribution Patterns"
        )
        assert len(sections["technical_substance"]["items"]) <= 10

        # Check quality signals
        signals = report["quality_signals"]
        assert signals["total_prs"] == 12
        assert signals["merged_prs"] == 10
        assert signals["merge_rate"] == pytest.approx(0.833, rel=0.01)

    def test_include_all_evidence(self, generator, sample_evidence, sample_signals):
        """Test report includes all evidence when requested."""
        report = generator.generate_detailed_report(
            username="testuser",
            evidence=sample_evidence,
            quality_signals=sample_signals,
            include_all_evidence=True,
        )

        # Should include all evidence items
        tech_items = report["evidence_sections"]["technical_substance"]["items"]
        assert len(tech_items) == len(sample_evidence.technical_substance)

    def test_executive_summary_generation(
        self, generator, sample_evidence, sample_signals
    ):
        """Test executive summary generation."""
        summary = generator._generate_executive_summary(sample_evidence, sample_signals)

        # Check key information is in summary
        assert "12 pull requests" in summary
        assert "3 repositories" in summary
        assert "83%" in summary  # merge rate
        assert "6 months" in summary  # time span
        assert "pair programming in 2 PRs" in summary

    def test_quality_indicators_formatting(self, generator, sample_signals):
        """Test quality indicators are properly formatted."""
        formatted = generator._format_quality_indicators(sample_signals)

        # Check indicators are present
        assert "PR velocity: ~2.0 PRs/month" in formatted
        assert "Repository diversity: 3 repositories" in formatted
        assert "Work distribution: 58% features, 42% fixes/maintenance" in formatted
        assert "Pair programming instances: 2" in formatted
        assert "PRs with extensive review: 5" in formatted
        assert "Production merge rate: 83%" in formatted

    def test_empty_evidence_handling(self, generator):
        """Test handling of empty evidence."""
        empty_evidence = PREvidence()
        empty_signals = QualitySignals(
            total_prs=0,
            merged_prs=0,
            unique_repos=0,
            feature_prs=0,
            fix_prs=0,
        )
        # Initialize empty list for areas_to_explore
        empty_evidence.areas_to_explore = []

        report = generator.generate_summary_report(
            username="emptyuser",
            evidence=empty_evidence,
            quality_signals=empty_signals,
        )

        # Should handle empty data gracefully
        assert "# PR Analysis Report: emptyuser" in report
        assert "No PR data available" in report

    def test_format_for_integration(self, generator, sample_evidence, sample_signals):
        """Test formatting for integration with main report."""
        analysis_result = {
            "success": True,
            "evidence": sample_evidence,
            "quality_signals": sample_signals,
        }

        formatted = generator.format_for_integration(analysis_result)

        # Check integration format
        assert formatted["pr_analysis_available"] is True
        assert "pr_evidence" in formatted
        assert "pr_quality_signals" in formatted
        assert "pr_summary" in formatted

        # Check evidence is limited
        assert len(formatted["pr_evidence"]["technical_patterns"]) <= 10
        assert len(formatted["pr_evidence"]["areas_to_explore"]) <= 5

    def test_format_for_integration_failure(self, generator):
        """Test formatting when analysis failed."""
        failed_result = {
            "success": False,
            "error": "API rate limit exceeded",
        }

        formatted = generator.format_for_integration(failed_result)

        assert formatted["pr_analysis_available"] is False
        assert formatted["error"] == "API rate limit exceeded"

    def test_quality_signals_dict_conversion(self, generator, sample_signals):
        """Test quality signals convert to dictionary properly."""
        signals_dict = generator._format_quality_signals_dict(sample_signals)

        assert signals_dict["total_prs"] == 12
        assert signals_dict["merged_prs"] == 10
        assert signals_dict["unique_repositories"] == 3
        assert "first_pr_date" in signals_dict
        assert "contribution_timespan" in signals_dict

    def test_markdown_formatting(self, generator, sample_evidence, sample_signals):
        """Test markdown formatting is correct."""
        report = generator.generate_summary_report(
            username="testuser",
            evidence=sample_evidence,
            quality_signals=sample_signals,
        )

        # Check markdown elements
        assert report.count("#") >= 7  # Headers
        assert report.count("##") >= 6  # Section headers
        assert report.count("-") >= 10  # List items
        assert report.count("**") >= 2  # Bold text

    def test_context_handling(self, generator, sample_evidence, sample_signals):
        """Test different contexts are handled."""
        contexts = ["STARTUP", "ENTERPRISE", "AGENCY", "OPEN_SOURCE"]

        for context in contexts:
            report = generator.generate_summary_report(
                username="testuser",
                evidence=sample_evidence,
                quality_signals=sample_signals,
                context=context,
            )
            assert f"**Context**: {context}" in report

    def test_report_timestamp(self, generator, sample_evidence, sample_signals):
        """Test report includes timestamp."""
        report = generator.generate_summary_report(
            username="testuser",
            evidence=sample_evidence,
            quality_signals=sample_signals,
        )

        # Check timestamp is present
        assert "**Generated**:" in report
        assert "UTC" in report
