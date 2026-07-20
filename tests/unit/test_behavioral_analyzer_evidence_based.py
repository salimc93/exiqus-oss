"""
Unit tests for evidence-based behavioral analyzer.

Ensures no arbitrary thresholds or scores are used.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from github_analyzer.core.evidence.behavioral_analyzer_evidence_based import (
    BehavioralAnalyzerEvidenceBased,
)
from github_analyzer.data.models import CommitInfo, RepositoryData


class TestEvidenceBasedBehavioralAnalyzer:
    """Test evidence-based behavioral analysis."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return BehavioralAnalyzerEvidenceBased()

    @pytest.fixture
    def sample_repo_data(self):
        """Create sample repository data with varied patterns."""
        base_date = datetime.now(timezone.utc)

        # Create commits with different patterns
        commits = []

        # Weekday morning commits
        for i in range(10):
            date = base_date - timedelta(days=i * 2)  # Skip weekends
            if date.weekday() < 5:  # Weekday
                date = date.replace(hour=9, minute=30)
                commits.append(
                    CommitInfo(
                        sha=f"abc{i:03d}",
                        message=f"feat: Add feature {i}",
                        author_name="Dev One",
                        author_email="dev1@example.com",
                        date=date,
                        additions=50,
                        deletions=10,
                    )
                )

        # Weekend commits from another developer
        for i in range(5):
            date = base_date - timedelta(days=i * 7)  # Weekly on Saturdays
            date = date.replace(hour=14, minute=0)
            date = date - timedelta(days=date.weekday() - 5)  # Make it Saturday
            commits.append(
                CommitInfo(
                    sha=f"def{i:03d}",
                    message=f"refactor: Clean up module {i}",
                    author_name="Dev Two",
                    author_email="dev2@example.com",
                    date=date,
                    additions=30,
                    deletions=40,
                )
            )

        # Add some collaborative commits
        commits.extend(
            [
                CommitInfo(
                    sha="ghi001",
                    message="fix: Address issue #100 reported by @user1",
                    author_name="Dev One",
                    author_email="dev1@example.com",
                    date=base_date - timedelta(days=5),
                    additions=10,
                    deletions=5,
                ),
                CommitInfo(
                    sha="jkl002",
                    message="Merge PR #101: Add authentication\n\nCo-authored-by: Dev Three <dev3@example.com>",
                    author_name="Dev One",
                    author_email="dev1@example.com",
                    date=base_date - timedelta(days=3),
                    additions=100,
                    deletions=20,
                ),
                CommitInfo(
                    sha="mno003",
                    message="docs: Update README with installation instructions",
                    author_name="Dev Two",
                    author_email="dev2@example.com",
                    date=base_date - timedelta(days=2),
                    additions=20,
                    deletions=5,
                ),
            ]
        )

        repo_data = Mock(spec=RepositoryData)
        repo_data.recent_commits = commits
        repo_data.languages = {"Python": 10000, "JavaScript": 5000}
        repo_data.file_structure = []
        repo_data.metrics = Mock(unique_contributors=2)
        repo_data.name = "test-repo"

        return repo_data

    @pytest.fixture
    def minimal_repo_data(self):
        """Create minimal repository data."""
        repo_data = Mock(spec=RepositoryData)
        repo_data.recent_commits = []
        repo_data.languages = {"Python": 1000}
        repo_data.file_structure = []
        repo_data.metrics = Mock(unique_contributors=1)
        repo_data.name = "minimal-repo"

        return repo_data

    def test_no_scores_in_analysis(self, analyzer, sample_repo_data):
        """Ensure analysis contains no scores or arbitrary metrics."""
        result = analyzer.analyze_behavior(sample_repo_data)

        # Check result structure
        assert "work_patterns" in result
        assert "collaboration_patterns" in result
        assert "communication_patterns" in result
        assert "time_patterns" in result
        assert "data_context" in result
        assert "summary" in result

        # Ensure no score-related fields
        result_str = str(result).lower()
        assert "score" not in result_str
        assert "rating" not in result_str
        # confidence is ok as long as it's not a numeric score

        # Check all pattern categories have observations
        for pattern_key in [
            "work_patterns",
            "collaboration_patterns",
            "communication_patterns",
            "time_patterns",
            "response_patterns",
            "leadership_indicators",
        ]:
            if pattern_key in result:
                assert "observations" in result[pattern_key]
                # Check observations are strings
                for obs in result[pattern_key]["observations"]:
                    assert isinstance(obs, str)
                    assert "score" not in obs.lower()
                    # Allow percentages only when describing actual data
                    if "%" in obs:
                        # Should be describing actual distribution, not comparing to threshold
                        assert any(
                            word in obs.lower()
                            for word in ["commits", "found", "of", "out of"]
                        )

    def test_observations_are_factual(self, analyzer, sample_repo_data):
        """Test that observations state facts without judgment."""
        result = analyzer.analyze_behavior(sample_repo_data)

        evaluative_terms = [
            "good",
            "bad",
            "poor",
            "excellent",
            "concerning",
            "healthy",
            "unhealthy",
            "balanced",
            "unbalanced",
        ]

        # Check all observations across all pattern categories
        for pattern_key in [
            "work_patterns",
            "collaboration_patterns",
            "communication_patterns",
            "time_patterns",
            "response_patterns",
            "leadership_indicators",
        ]:
            if pattern_key in result and "observations" in result[pattern_key]:
                for obs in result[pattern_key]["observations"]:
                    observation_lower = obs.lower()
                    for term in evaluative_terms:
                        assert term not in observation_lower, (
                            f"Found evaluative term '{term}' in: {obs}"
                        )

    def test_data_context_provided(self, analyzer, sample_repo_data):
        """Test data context is provided without thresholds."""
        result = analyzer.analyze_behavior(sample_repo_data)
        context = result["data_context"]

        # Should contain factual metrics
        assert "total_commits_analyzed" in context
        assert "time_span" in context
        assert "unique_contributors" in context

        # No arbitrary thresholds - just verify the counts are actual numbers
        assert isinstance(context["total_commits_analyzed"], int)
        assert isinstance(context["unique_contributors"], int)
        assert context["total_commits_analyzed"] > 0  # Has commits

        # Time span should have factual information
        assert "days" in context["time_span"]
        assert isinstance(context["time_span"]["days"], int)

    def test_no_data_handling(self, analyzer, minimal_repo_data):
        """Test handling of repositories with no commits."""
        result = analyzer.analyze_behavior(minimal_repo_data)

        assert result["status"] == "no_data"
        assert "message" in result
        assert len(result["observations"]) == 0

    def test_work_pattern_observations(self, analyzer, sample_repo_data):
        """Test work pattern observations are factual."""
        result = analyzer.analyze_behavior(sample_repo_data)
        work_patterns = result["work_patterns"]

        assert "observations" in work_patterns
        assert "patterns_found" in work_patterns

        # Check that patterns found are reported factually
        if work_patterns["patterns_found"]:
            for style, matches in work_patterns["patterns_found"].items():
                assert isinstance(matches, list)
                for match in matches:
                    assert "commit" in match
                    assert "message" in match

    def test_collaboration_observations(self, analyzer, sample_repo_data):
        """Test collaboration observations are factual."""
        result = analyzer.analyze_behavior(sample_repo_data)
        collab = result["collaboration_patterns"]

        assert "observations" in collab

        # Check factual reporting
        if collab.get("team_mentions"):
            # Should report actual counts, not judgments
            assert isinstance(collab["team_mentions"], list)

        if collab.get("pr_references"):
            assert isinstance(collab["pr_references"], list)

    def test_time_pattern_observations(self, analyzer, sample_repo_data):
        """Test time pattern observations are factual."""
        result = analyzer.analyze_behavior(sample_repo_data)
        time_patterns = result["time_patterns"]

        assert "observations" in time_patterns

        # Check factual reporting
        for obs in time_patterns["observations"]:
            # Should state facts like "5 commits made on weekends"
            # Not judgments like "works too much on weekends"
            assert isinstance(obs, str)
            if "weekend" in obs.lower():
                assert "commits" in obs.lower()
                assert any(word in obs.lower() for word in ["made", "out of", "total"])

    def test_no_hardcoded_thresholds(self, analyzer):
        """Verify the analyzer doesn't use hardcoded thresholds."""
        # This is a code inspection test - we're checking the analyzer
        # doesn't have methods that make threshold-based decisions

        # The analyzer should not have methods like:
        # - _is_high_collaboration
        # - _calculate_burnout_risk
        # - _determine_skill_level

        method_names = [
            attr for attr in dir(analyzer) if callable(getattr(analyzer, attr))
        ]

        threshold_indicators = [
            "is_high",
            "is_low",
            "calculate_score",
            "determine_level",
            "assess_risk",
            "evaluate",
            "grade",
            "rank",
        ]

        for method in method_names:
            method_lower = method.lower()
            for indicator in threshold_indicators:
                assert indicator not in method_lower, (
                    f"Method '{method}' suggests threshold-based logic"
                )

    def test_summary_is_factual(self, analyzer, sample_repo_data):
        """Test that the summary provides factual information."""
        result = analyzer.analyze_behavior(sample_repo_data)
        summary = result["summary"]

        assert "total_observations" in summary
        assert "key_findings" in summary
        assert "data_limitations" in summary

        # Key findings should be factual observations
        for finding in summary["key_findings"]:
            assert isinstance(finding, str)
            # Should not contain evaluative language
            assert not any(
                term in finding.lower() for term in ["good", "bad", "poor", "excellent"]
            )

    def test_generate_behavioral_insights(self, analyzer, sample_repo_data):
        """Test the public method for generating insights."""
        insights = analyzer.generate_behavioral_insights(sample_repo_data)

        assert isinstance(insights, list)

        # Each insight should be a factual observation
        for insight in insights:
            assert isinstance(insight, str)
            # Should start with a category prefix
            assert any(
                insight.startswith(prefix)
                for prefix in [
                    "Work style:",
                    "Collaboration:",
                    "Schedule:",
                    "Communication:",
                ]
            )
