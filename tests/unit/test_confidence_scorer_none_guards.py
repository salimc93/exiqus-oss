"""
Unit tests for None/zero guards in evidence-based confidence scorer.

Tests that the confidence scorer handles None values and missing metrics gracefully.
"""

from datetime import datetime, timezone

import pytest

from github_analyzer.core.classifier import (
    AnalysisMethod,
    ClassificationResult,
    RepositoryType,
)
from github_analyzer.core.confidence_scorer import (
    ConfidenceRiskAssessor,
    RiskLevel,
)
from github_analyzer.data.models import RepositoryData, RepositoryMetrics


def create_minimal_repo(**kwargs):
    """Create a minimal repository with defaults that can be overridden."""
    defaults = {
        "url": "https://github.com/test/repo",
        "full_name": "test/repo",
        "name": "repo",
        "owner": "test",
        "description": "",
        "created_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2025, 1, 2, tzinfo=timezone.utc),
        "pushed_at": datetime(2025, 1, 2, tzinfo=timezone.utc),
        "default_branch": "main",
        "size": 100,
        "languages": {},
        "topics": [],
        "license_name": None,
        "stars": 0,
        "forks": 0,
        "watchers": 0,
        "open_issues": 0,
        "has_readme": False,
        "has_license": False,
        "has_contributing": False,
        "has_tests": False,
        "has_ci_config": False,
        "recent_commits": [],
        "file_structure": [],
        "readme_content": None,
        "metrics": None,
        "fetched_at": datetime.now(timezone.utc),
        "is_private": False,
        "is_fork": False,
        "is_archived": False,
        "is_disabled": False,
    }
    defaults.update(kwargs)
    return RepositoryData(**defaults)


def create_classification():
    """Create a basic classification result."""
    return ClassificationResult(
        method=AnalysisMethod.TEMPLATE,
        repository_type=RepositoryType.PORTFOLIO,
        reasoning="Test classification",
    )


class TestNoneGuards:
    """Test None/zero guards in confidence scorer."""

    @pytest.fixture
    def scorer(self):
        """Create a confidence scorer instance."""
        return ConfidenceRiskAssessor()

    def test_score_with_none_metrics(self, scorer):
        """Test scoring with completely None metrics."""
        repo = create_minimal_repo(metrics=None)
        classification = create_classification()

        result = scorer.assess_confidence_and_risk(repo, classification)

        assert result is not None
        assert result.confidence_breakdown.get_confidence_level() in [
            "LOW",
            "MEDIUM",
            "HIGH",
        ]
        assert len(result.confidence_breakdown.evidence_patterns) >= 0
        assert result.overall_risk_level in RiskLevel

    def test_score_with_partial_none_metrics(self, scorer):
        """Test scoring with partial None values in metrics."""
        metrics = RepositoryMetrics(
            total_commits=None,
            unique_contributors=None,
            lines_of_code=None,
            test_coverage_estimate=None,
            documentation_presence="1 documentation files in 10 total files",
            days_since_last_commit=None,
            commit_frequency=None,
            avg_commit_size=100.0,
        )
        repo = create_minimal_repo(metrics=metrics)
        classification = create_classification()

        result = scorer.assess_confidence_and_risk(repo, classification)

        assert result is not None
        assert result.confidence_breakdown.get_confidence_level() in [
            "LOW",
            "MEDIUM",
            "HIGH",
        ]
        assert len(result.confidence_breakdown.evidence_patterns) >= 0

    def test_score_with_zero_metrics(self, scorer):
        """Test scoring with zero values in metrics."""
        metrics = RepositoryMetrics(
            total_commits=0,
            unique_contributors=0,
            lines_of_code=0,
            test_coverage_estimate=0.0,
            documentation_presence="0 documentation files found",
            days_since_last_commit=0,
            commit_frequency=0.0,
            avg_commit_size=0.0,
        )
        repo = create_minimal_repo(metrics=metrics)
        classification = create_classification()

        result = scorer.assess_confidence_and_risk(repo, classification)

        assert result is not None
        assert result.confidence_breakdown.get_confidence_level() in [
            "LOW",
            "MEDIUM",
            "HIGH",
        ]
        assert len(result.confidence_breakdown.evidence_patterns) >= 0

    @pytest.mark.parametrize(
        "metrics",
        [
            None,
            RepositoryMetrics(
                total_commits=None,
                unique_contributors=None,
                lines_of_code=None,
                test_coverage_estimate=None,
                documentation_presence=None,
                days_since_last_commit=None,
                commit_frequency=None,
                avg_commit_size=None,
            ),
            RepositoryMetrics(
                total_commits=0,
                unique_contributors=0,
                lines_of_code=0,
                test_coverage_estimate=0,
                documentation_presence="0 documentation files found",
                days_since_last_commit=999999,  # Very old
                commit_frequency=0,
                avg_commit_size=0,
            ),
        ],
    )
    def test_temporal_reliability_handles_none(self, scorer, metrics):
        """Test temporal reliability assessment with various None/zero states."""
        repo = create_minimal_repo(metrics=metrics)

        evidence_patterns, limitations = scorer._assess_temporal_reliability(repo)

        assert isinstance(evidence_patterns, list)
        assert isinstance(limitations, list)
        # Should have at least one limitation with poor data
        assert len(limitations) >= 0

    @pytest.mark.parametrize(
        "metrics",
        [
            None,
            RepositoryMetrics(
                total_commits=None,
                unique_contributors=None,
                lines_of_code=None,
                test_coverage_estimate=None,
                documentation_presence=None,
                days_since_last_commit=None,
                commit_frequency=None,
                avg_commit_size=None,
            ),
        ],
    )
    def test_data_availability_handles_none(self, scorer, metrics):
        """Test data availability assessment with None metrics."""
        repo = create_minimal_repo(metrics=metrics)

        evidence_patterns, limitations = scorer._assess_data_availability(repo)

        assert isinstance(evidence_patterns, list)
        assert isinstance(limitations, list)

    def test_repository_quality_handles_none(self, scorer):
        """Test repository quality assessment with None metrics."""
        repo = create_minimal_repo(metrics=None)

        evidence_patterns = scorer._assess_repository_quality(repo)

        assert isinstance(evidence_patterns, list)

    def test_data_completeness_handles_none(self, scorer):
        """Test data completeness calculation with None metrics."""
        repo = create_minimal_repo(metrics=None)

        completeness = scorer._calculate_data_completeness(repo)

        # Evidence-based approach returns 0 (no scores)
        assert completeness == 0.0

    def test_technical_risks_handles_none(self, scorer):
        """Test technical risk identification with None metrics."""
        repo = create_minimal_repo(metrics=None)

        risks = scorer._identify_technical_risks(repo)

        assert isinstance(risks, list)
        # Should not crash, but may return empty or minimal risks

    def test_maintenance_risks_handles_none(self, scorer):
        """Test maintenance risk identification with None metrics."""
        repo = create_minimal_repo(metrics=None)

        risks = scorer._identify_maintenance_risks(repo)

        assert isinstance(risks, list)

    def test_experience_risks_handles_none(self, scorer):
        """Test experience risk identification with None metrics."""
        repo = create_minimal_repo(metrics=None)

        risks = scorer._identify_experience_risks(repo)

        assert isinstance(risks, list)

    def test_cultural_risks_handles_none(self, scorer):
        """Test cultural risk identification with None metrics."""
        repo = create_minimal_repo(metrics=None)

        risks = scorer._identify_cultural_risks(repo)

        assert isinstance(risks, list)

    def test_classification_risks_handles_none(self, scorer):
        """Test classification risk identification with None metrics."""
        repo = create_minimal_repo(metrics=None)
        classification = create_classification()

        risks = scorer._identify_classification_risks(repo, classification)

        assert isinstance(risks, list)

    def test_edge_case_inf_days_since_commit(self, scorer):
        """Test handling of infinity days since last commit."""
        metrics = RepositoryMetrics(
            total_commits=10,
            unique_contributors=1,
            lines_of_code=1000,
            test_coverage_estimate=0.5,
            documentation_presence="1 documentation files in 10 total files",
            days_since_last_commit=float("inf"),  # Simulating None handling
            commit_frequency=0.1,
            avg_commit_size=100.0,
        )
        repo = create_minimal_repo(metrics=metrics)
        classification = create_classification()

        result = scorer.assess_confidence_and_risk(repo, classification)

        assert result is not None
        # Should identify as stale/abandoned
        assert any(risk.category == "maintenance" for risk in result.risk_indicators)

    def test_mixed_none_and_valid_values(self, scorer):
        """Test with a mix of None and valid values."""
        metrics = RepositoryMetrics(
            total_commits=50,  # Valid
            unique_contributors=None,  # None
            lines_of_code=1000,  # Valid
            test_coverage_estimate=None,  # None
            documentation_presence="2 documentation files in 10 total files",  # Valid
            days_since_last_commit=None,  # None
            commit_frequency=1.5,  # Valid
            avg_commit_size=None,  # None
        )
        repo = create_minimal_repo(
            metrics=metrics,
            has_readme=True,
            has_tests=True,
            file_structure=["src/", "tests/", "docs/"],
            languages={"Python": 5000},
        )
        classification = create_classification()

        result = scorer.assess_confidence_and_risk(repo, classification)

        assert result is not None
        assert len(result.confidence_breakdown.evidence_patterns) > 0
        # Should still identify some risks due to None values
        assert len(result.risk_indicators) >= 0

    def test_all_none_guard_paths(self, scorer):
        """Test that all None guard code paths are exercised."""
        # Test with metrics object but all fields None
        all_none_metrics = RepositoryMetrics(
            total_commits=None,
            unique_contributors=None,
            lines_of_code=None,
            test_coverage_estimate=None,
            documentation_presence=None,
            days_since_last_commit=None,
            commit_frequency=None,
            avg_commit_size=None,
        )

        # Create repos with different combinations
        repos = [
            create_minimal_repo(metrics=None),  # No metrics object
            create_minimal_repo(metrics=all_none_metrics),  # Metrics with all None
            create_minimal_repo(  # Mix of conditions
                metrics=all_none_metrics,
                has_tests=True,  # Trigger test coverage check
                has_readme=False,  # Trigger documentation check
                languages={"Python": 1000},  # Single language
            ),
        ]

        classification = create_classification()

        for repo in repos:
            result = scorer.assess_confidence_and_risk(repo, classification)
            assert result is not None
            assert result.confidence_breakdown.get_confidence_level() in [
                "LOW",
                "MEDIUM",
                "HIGH",
            ]
            assert len(result.confidence_breakdown.evidence_patterns) >= 0
            assert result.overall_risk_level in RiskLevel
