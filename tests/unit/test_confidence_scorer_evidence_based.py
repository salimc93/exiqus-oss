"""
Unit tests for evidence-based confidence scorer.

Ensures confidence assessment is based on actual data availability
without arbitrary scores or thresholds.
"""

from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

from github_analyzer.core.evidence.confidence_scorer_evidence_based import (
    DataAvailability,
    EvidenceBasedConfidenceScorer,
)
from github_analyzer.data.models import CommitInfo, RepositoryData, RepositoryMetrics


class TestEvidenceBasedConfidenceScorer:
    """Test evidence-based confidence assessment."""

    @pytest.fixture
    def scorer(self):
        """Create scorer instance."""
        return EvidenceBasedConfidenceScorer()

    @pytest.fixture
    def comprehensive_repo(self):
        """Create a repository with comprehensive data."""
        base_date = datetime.now()
        commits = [
            CommitInfo(
                sha=f"abc{i:03d}",
                message=f"feat: Add feature {i}",
                author_name="Dev One",
                author_email="dev1@example.com",
                date=base_date - timedelta(days=i * 7),
                additions=50,
                deletions=10,
            )
            for i in range(20)
        ]

        repo = Mock(spec=RepositoryData)
        repo.full_name = "user/comprehensive-repo"
        repo.has_readme = True
        repo.readme_content = "# Comprehensive Project\n\n" + "x" * 1000
        repo.file_structure = [f"file{i}.py" for i in range(30)]
        repo.languages = {"Python": 10000, "JavaScript": 5000, "Shell": 1000}
        repo.recent_commits = commits
        repo.has_tests = True
        repo.has_ci_config = True
        repo.has_license = True
        repo.description = "A comprehensive test project"
        repo.is_fork = False

        repo.metrics = Mock(spec=RepositoryMetrics)
        repo.metrics.total_commits = 100
        repo.metrics.unique_contributors = 5
        repo.metrics.lines_of_code = 5000
        repo.metrics.days_since_last_commit = 3

        return repo

    @pytest.fixture
    def minimal_repo(self):
        """Create a repository with minimal data."""
        repo = Mock(spec=RepositoryData)
        repo.full_name = "user/minimal-repo"
        repo.has_readme = False
        repo.readme_content = None
        repo.file_structure = ["index.html"]
        repo.languages = {"HTML": 100}
        repo.recent_commits = []
        repo.has_tests = False
        repo.has_ci_config = False
        repo.has_license = False
        repo.description = None
        repo.is_fork = False

        repo.metrics = Mock(spec=RepositoryMetrics)
        repo.metrics.total_commits = 1
        repo.metrics.unique_contributors = 1
        repo.metrics.lines_of_code = None
        repo.metrics.days_since_last_commit = 365

        return repo

    @pytest.fixture
    def limited_repo(self):
        """Create a repository with limited data."""
        base_date = datetime.now()
        commits = [
            CommitInfo(
                sha=f"def{i:03d}",
                message=f"Update {i}",
                author_name="Solo Dev",
                author_email="solo@example.com",
                date=base_date - timedelta(days=i * 30),
                additions=10,
                deletions=5,
            )
            for i in range(8)
        ]

        repo = Mock(spec=RepositoryData)
        repo.full_name = "user/limited-repo"
        repo.has_readme = True
        repo.readme_content = "# Limited Project\n\nBasic description."
        repo.file_structure = ["main.py", "utils.py", "config.json"]
        repo.languages = {"Python": 500}
        repo.recent_commits = commits
        repo.has_tests = False
        repo.has_ci_config = False
        repo.has_license = True
        repo.description = "A limited project"
        repo.is_fork = False

        repo.metrics = Mock(spec=RepositoryMetrics)
        repo.metrics.total_commits = 8
        repo.metrics.unique_contributors = 1
        repo.metrics.lines_of_code = 200
        repo.metrics.days_since_last_commit = 45

        return repo

    def test_no_arbitrary_scores(self, scorer, comprehensive_repo):
        """Ensure assessment contains no arbitrary scores."""
        result = scorer.assess_confidence(comprehensive_repo)

        # Check that result doesn't contain numeric scores
        assert not hasattr(result, "score")
        assert not hasattr(result, "confidence")
        assert not hasattr(result, "rating")

        # Check data structures don't contain scores
        for attr_name in dir(result):
            attr_value = getattr(result, attr_name)
            if isinstance(attr_value, (int, float)) and not attr_name.startswith("_"):
                # Only allow counts and actual data values
                assert attr_name in ["data_availability"]  # This contains counts

    def test_data_availability_assessment(self, scorer, comprehensive_repo):
        """Test accurate data availability assessment."""
        result = scorer.assess_confidence(comprehensive_repo)
        data = result.data_availability

        assert data.has_readme is True
        assert data.readme_length == 1025  # Header + 1000 chars
        assert data.file_count == 30
        assert data.language_count == 3
        assert data.commit_count == 100
        assert data.contributor_count == 5
        assert data.has_tests is True
        assert data.has_ci is True
        assert data.has_license is True
        assert data.total_lines == 5000

        # Test description
        desc = data.describe()
        assert "100 commits" in desc
        assert "5 contributors" in desc
        assert "30 files" in desc
        assert "3 languages" in desc

    def test_minimal_data_handling(self, scorer, minimal_repo):
        """Test handling of minimal data."""
        result = scorer.assess_confidence(minimal_repo)

        assert result.data_sufficiency == "minimal"
        assert result.analysis_depth == "surface"

        # Should have many limitations
        assert len(result.limitations.structural) > 2
        assert len(result.limitations.temporal) > 0
        # Critical gaps may or may not exist depending on specific criteria

        # Check specific limitations
        structural_text = " ".join(result.limitations.structural).lower()
        assert "no readme" in structural_text
        assert "very few files" in structural_text
        assert "no tests" in structural_text

    def test_limitations_identification(self, scorer, limited_repo):
        """Test identification of various limitations."""
        result = scorer.assess_confidence(limited_repo)

        # Structural limitations
        assert any(
            "minimal readme" in lim.lower() for lim in result.limitations.structural
        )
        assert any("no tests" in lim.lower() for lim in result.limitations.structural)

        # Contextual limitations
        assert any(
            "single contributor" in lim.lower() for lim in result.limitations.contextual
        )

        # Behavioral limitations (always present)
        assert len(result.limitations.behavioral) >= 4
        assert any(
            "soft skills" in lim.lower() for lim in result.limitations.behavioral
        )

    def test_uncertainty_assessment(self, scorer, comprehensive_repo):
        """Test uncertainty factor assessment."""
        result = scorer.assess_confidence(comprehensive_repo)
        uncertainty = result.uncertainty

        # Should have standard uncertainty factors
        assert len(uncertainty.partial_visibility) > 0
        assert any(
            "public repositories" in factor.lower()
            for factor in uncertainty.partial_visibility
        )
        assert any(
            "code review" in factor.lower() for factor in uncertainty.partial_visibility
        )

        # External factors always present
        assert len(uncertainty.external_factors) > 0
        assert any(
            "professional vs personal" in factor.lower()
            for factor in uncertainty.external_factors
        )

    def test_data_sufficiency_levels(self, scorer):
        """Test different data sufficiency determinations."""
        # Test comprehensive
        comprehensive = Mock(spec=DataAvailability)
        comprehensive.has_readme = True
        comprehensive.readme_length = 1000
        comprehensive.commit_count = 100
        comprehensive.file_count = 50
        comprehensive.has_tests = True
        comprehensive.has_ci = True
        comprehensive.language_count = 3
        comprehensive.contributor_count = 5

        assert scorer._determine_data_sufficiency(comprehensive) == "comprehensive"

        # Test minimal
        minimal = Mock(spec=DataAvailability)
        minimal.has_readme = False
        minimal.readme_length = None
        minimal.commit_count = 1
        minimal.file_count = 1
        minimal.has_tests = False
        minimal.has_ci = False
        minimal.language_count = 1
        minimal.contributor_count = 1

        assert scorer._determine_data_sufficiency(minimal) == "minimal"

    def test_critical_gaps_identification(self, scorer):
        """Test identification of critical gaps."""
        # Create a repo with no commits
        repo = Mock(spec=RepositoryData)
        repo.full_name = "user/empty-repo"
        repo.has_readme = False
        repo.readme_content = None
        repo.file_structure = []
        repo.languages = {}
        repo.recent_commits = []
        repo.has_tests = False
        repo.has_ci_config = False
        repo.has_license = False
        repo.description = None
        repo.is_fork = False

        repo.metrics = Mock(spec=RepositoryMetrics)
        repo.metrics.total_commits = 0
        repo.metrics.unique_contributors = 0
        repo.metrics.lines_of_code = None
        repo.metrics.days_since_last_commit = None

        result = scorer.assess_confidence(repo)

        assert len(result.critical_gaps) > 0

        # Should identify major issues
        assert any(
            gap
            for gap in result.critical_gaps
            if "commit history" in gap.lower() or "code files" in gap.lower()
        )

    def test_assumptions_noted(self, scorer, limited_repo):
        """Test that assumptions are properly noted."""
        result = scorer.assess_confidence(limited_repo)

        assert len(result.assumptions_made) > 0

        # Should note solo development assumption
        assert any(
            "solo development" in assumption.lower()
            for assumption in result.assumptions_made
        )

        # Should note testing assumption
        assert any(
            "testing" in assumption.lower() and "outside" in assumption.lower()
            for assumption in result.assumptions_made
        )

    def test_reliability_notes_generation(self, scorer, comprehensive_repo):
        """Test generation of reliability notes."""
        result = scorer.assess_confidence(comprehensive_repo)

        assert len(result.reliability_notes) > 0

        # Should note positive indicators
        notes_text = " ".join(result.reliability_notes).lower()
        assert "quality practices" in notes_text or "thorough analysis" in notes_text

    def test_inactive_repository_detection(self, scorer):
        """Test detection of inactive repositories."""
        repo = Mock(spec=RepositoryData)
        repo.full_name = "user/old-repo"
        repo.has_readme = True
        repo.readme_content = "Old project"
        repo.file_structure = ["old.py"]
        repo.languages = {"Python": 100}
        repo.recent_commits = []
        repo.has_tests = False
        repo.has_ci_config = False
        repo.has_license = False
        repo.description = None
        repo.is_fork = False

        repo.metrics = Mock(spec=RepositoryMetrics)
        repo.metrics.total_commits = 10
        repo.metrics.unique_contributors = 1
        repo.metrics.lines_of_code = 100
        repo.metrics.days_since_last_commit = 400

        result = scorer.assess_confidence(repo)

        # Should note temporal limitation
        temporal_text = " ".join(result.limitations.temporal).lower()
        assert "inactive" in temporal_text or "months" in temporal_text

    def test_confidence_summary(self, scorer, comprehensive_repo):
        """Test confidence summary generation."""
        result = scorer.assess_confidence(comprehensive_repo)
        summary = result.summary()

        assert "100 commits" in summary
        assert "comprehensive" in summary
        assert "detailed" in summary

        # Should be factual, not evaluative
        assert "good" not in summary.lower()
        assert "bad" not in summary.lower()
        assert "high" not in summary.lower()
        assert "low" not in summary.lower()

    def test_fork_handling(self, scorer):
        """Test handling of forked repositories."""
        repo = Mock(spec=RepositoryData)
        repo.full_name = "user/forked-repo"
        repo.has_readme = True
        repo.readme_content = "Forked project"
        repo.file_structure = ["main.py"]
        repo.languages = {"Python": 100}
        repo.recent_commits = []
        repo.has_tests = False
        repo.has_ci_config = False
        repo.has_license = True
        repo.description = "Fork of upstream"
        repo.is_fork = True

        repo.metrics = Mock(spec=RepositoryMetrics)
        repo.metrics.total_commits = 0
        repo.metrics.unique_contributors = 1
        repo.metrics.lines_of_code = 100
        repo.metrics.days_since_last_commit = 1

        result = scorer.assess_confidence(repo)

        # Should note fork with no commits as critical gap
        assert any(
            "fork with no unique commits" in gap.lower() for gap in result.critical_gaps
        )

        # Should note assumption about upstream
        assert any(
            "upstream" in assumption.lower() for assumption in result.assumptions_made
        )

    def test_no_evaluative_language(self, scorer, comprehensive_repo):
        """Test that output uses factual, not evaluative language."""
        result = scorer.assess_confidence(comprehensive_repo)

        # Check all string fields
        all_text = []
        all_text.append(result.summary())
        all_text.extend(result.reliability_notes)
        all_text.extend(result.critical_gaps)
        all_text.extend(result.assumptions_made)
        all_text.extend(result.limitations.all_limitations())

        full_text = " ".join(all_text).lower()

        # Should not contain evaluative terms
        evaluative_terms = [
            "excellent",
            "poor",
            "weak",
            "strong",
            "good quality",
            "bad quality",
            "high confidence",
            "low confidence",
        ]

        for term in evaluative_terms:
            assert term not in full_text, f"Found evaluative term: {term}"


class TestDataAvailability:
    """Test DataAvailability structure."""

    def test_comprehensive_description(self):
        """Test description of comprehensive data."""
        data = DataAvailability(
            has_readme=True,
            readme_length=1000,
            file_count=50,
            language_count=3,
            commit_count=200,
            contributor_count=10,
            has_tests=True,
            has_ci=True,
            has_license=True,
            days_of_history=180,
            total_lines=10000,
        )

        desc = data.describe()
        assert "200 commits" in desc
        assert "10 contributors" in desc
        assert "50 files" in desc
        assert "3 languages" in desc

    def test_minimal_description(self):
        """Test description of minimal data."""
        data = DataAvailability(
            has_readme=False,
            readme_length=None,
            file_count=0,
            language_count=0,
            commit_count=0,
            contributor_count=0,
            has_tests=False,
            has_ci=False,
            has_license=False,
            days_of_history=None,
            total_lines=None,
        )

        desc = data.describe()
        assert desc == "Minimal data available"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
