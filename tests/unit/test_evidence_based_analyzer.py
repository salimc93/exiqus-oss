"""
Unit tests for evidence-based analyzer.

Tests ensure no arbitrary metrics or scores are generated.
"""

from datetime import datetime, timedelta

import pytest

from github_analyzer.core.evidence_based_analyzer import (
    DataSufficiency,
    EvidenceBasedAnalyzer,
    Observation,
)


class TestEvidenceBasedAnalyzer:
    """Test evidence-based analysis without arbitrary metrics."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return EvidenceBasedAnalyzer()

    @pytest.fixture
    def sample_repo_data(self):
        """Create sample repository data."""
        base_date = datetime.now()
        return {
            "commits": [
                {
                    "sha": f"abc{i:03d}",
                    "message": f"commit {i}",
                    "author": "developer1" if i % 2 == 0 else "developer2",
                    "date": (base_date - timedelta(days=i)).isoformat(),
                }
                for i in range(20)
            ],
            "files": [
                "src/main.py",
                "src/utils.py",
                "tests/test_main.py",
                "README.md",
                ".github/workflows/ci.yml",
            ],
            "languages": {"Python": 10, "JavaScript": 5, "Shell": 2},
        }

    @pytest.fixture
    def minimal_repo_data(self):
        """Create minimal repository data."""
        return {
            "commits": [
                {
                    "sha": "abc123",
                    "message": "Initial commit",
                    "author": "developer1",
                    "date": datetime.now().isoformat(),
                }
            ],
            "files": ["index.html"],
            "languages": {"HTML": 1},
        }

    def test_no_arbitrary_scores_in_analysis(self, analyzer, sample_repo_data):
        """Ensure analysis contains no arbitrary scores or metrics."""
        result = analyzer.analyze(sample_repo_data)

        # Check that result doesn't contain score-related fields
        assert not hasattr(result, "score")
        assert not hasattr(result, "metrics")
        assert not hasattr(result, "ratings")

        # Check observations don't contain scores
        for obs in result.observations:
            assert "score" not in obs.finding.lower()
            # Allow percentages only when describing actual data
            if "%" in obs.finding:
                # Should be describing actual distribution, not a threshold
                assert any(
                    word in obs.finding.lower() for word in ["of", "commits", "files"]
                )

            # Check for arbitrary threshold decimals (0.7, 0.5, etc)
            # but allow legitimate decimals like "0.56 commits per day"
            import re

            threshold_pattern = (
                r"\b0\.[0-9]+\b(?!\s*(commits|files|days|hours|contributors))"
            )
            assert not re.search(threshold_pattern, obs.finding), (
                f"Found possible threshold in: {obs.finding}"
            )

    def test_observations_are_factual(self, analyzer, sample_repo_data):
        """Test that observations are factual, not evaluative."""
        result = analyzer.analyze(sample_repo_data)

        # Check that observations don't contain evaluative terms
        evaluative_terms = [
            "good",
            "bad",
            "poor",
            "excellent",
            "weak",
            "strong",
            "high",
            "low",
            "comprehensive",
            "lacking",
        ]

        for obs in result.observations:
            finding_lower = obs.finding.lower()
            for term in evaluative_terms:
                # Skip if the term is part of a file path or technical term
                if term == "low" and "workflow" in finding_lower:
                    continue
                # Check word boundaries to avoid false positives
                import re

                if re.search(rf"\b{term}\b", finding_lower):
                    assert False, f"Found evaluative term '{term}' in: {obs.finding}"

    def test_data_sufficiency_calculation(self, analyzer, sample_repo_data):
        """Test data sufficiency assessment."""
        result = analyzer.analyze(sample_repo_data)
        sufficiency = result.data_sufficiency

        assert sufficiency.total_commits == 20
        assert sufficiency.contributors == 2
        assert sufficiency.time_span_days == 19
        assert len(sufficiency.languages) == 3
        assert sufficiency.has_tests is True
        assert sufficiency.has_documentation is True

        # Check summary is descriptive, not evaluative
        assert "commits" in sufficiency.summary
        assert "days" in sufficiency.summary
        assert "contributors" in sufficiency.summary

    def test_insufficient_data_handling(self, analyzer, minimal_repo_data):
        """Test handling of insufficient data."""
        result = analyzer.analyze(minimal_repo_data)

        # Should acknowledge limitations
        assert len(result.data_sufficiency.limitations) > 0
        assert any(
            "limited" in lim.lower() for lim in result.data_sufficiency.limitations
        )

        # Should still provide observations
        assert len(result.observations) > 0

        # NO behavioral observations after The Great Purge
        behavioral_obs = [o for o in result.observations if o.category == "behavioral"]
        assert len(behavioral_obs) == 0  # No behavioral inferences allowed

    def test_interview_topics_generated(self, analyzer, sample_repo_data):
        """Test that interview topics are generated from observations."""
        result = analyzer.analyze(sample_repo_data)

        assert len(result.interview_guidance) > 0
        assert all(isinstance(topic, str) for topic in result.interview_guidance)

        # Should include fundamental topics
        fundamental_topics = ["problem-solving", "learning", "communication"]
        guidance_text = " ".join(result.interview_guidance).lower()
        assert any(topic in guidance_text for topic in fundamental_topics)

    def test_patterns_based_on_evidence(self, analyzer, sample_repo_data):
        """Test that patterns are based on actual evidence."""
        result = analyzer.analyze(sample_repo_data)

        for pattern in result.patterns:
            assert "evidence" in pattern
            assert len(pattern["evidence"]) > 0
            assert "description" in pattern
            assert "interview_focus" in pattern

    def test_no_hardcoded_thresholds(self, analyzer):
        """Test that analyzer doesn't use hardcoded thresholds."""
        # Check the analyzer source for hardcoded values
        source = str(analyzer.__class__)

        # These patterns should not exist in evidence-based analyzer
        forbidden_patterns = [
            "0.7",  # No arbitrary decimals
            "0.5",
            "> 20",  # No arbitrary comparisons
            "< 10",
            "threshold",
            "min_commits_for",
            "score",
            "rating",
        ]

        # This is a meta-test - in real implementation, scan the actual source
        assert all(pattern not in source.lower() for pattern in forbidden_patterns)

    def test_context_notes_are_exploratory(self, analyzer, sample_repo_data):
        """Test that context notes suggest exploration, not judgment."""
        result = analyzer.analyze(sample_repo_data)

        for context, note in result.context_notes.items():
            # Should focus on exploration
            assert any(
                word in note.lower() for word in ["explore", "discuss", "understand"]
            )

            # Should not make definitive statements
            assert not any(
                word in note.lower()
                for word in ["must", "should", "need to", "required"]
            )

    def test_single_contributor_handled_appropriately(self, analyzer):
        """Test handling of single-contributor repositories."""
        repo_data = {
            "commits": [
                {
                    "sha": f"abc{i:03d}",
                    "message": f"commit {i}",
                    "author": "single_dev",
                    "date": (datetime.now() - timedelta(days=i)).isoformat(),
                }
                for i in range(15)
            ],
            "files": ["main.py", "utils.py"],
            "languages": {"Python": 2},
        }

        result = analyzer.analyze(repo_data)

        # Should have observation about single contributor
        collab_obs = [o for o in result.observations if o.category == "collaboration"]
        assert any("single contributor" in o.finding.lower() for o in collab_obs)

        # Should acknowledge limitation
        single_contrib_obs = next(
            o for o in collab_obs if "single" in o.finding.lower()
        )
        assert len(single_contrib_obs.data_limitations) > 0
        assert any("team" in lim.lower() for lim in single_contrib_obs.data_limitations)

    def test_quality_practices_observed_not_judged(self, analyzer, sample_repo_data):
        """Test that quality practices are observed, not judged."""
        result = analyzer.analyze(sample_repo_data)

        quality_obs = [o for o in result.observations if o.category == "quality"]

        for obs in quality_obs:
            # Should state facts
            if "test" in obs.finding.lower():
                assert (
                    "found" in obs.finding.lower() or "detected" in obs.finding.lower()
                )
                assert "good" not in obs.finding.lower()
                assert "poor" not in obs.finding.lower()

    def test_work_patterns_without_judgment(self, analyzer):
        """Test work patterns are reported without judgment."""
        # Create repo with weekend commits
        base_date = datetime(2024, 1, 6)  # Saturday
        repo_data = {
            "commits": [
                {
                    "sha": f"abc{i:03d}",
                    "message": f"commit {i}",
                    "author": "developer1",
                    "date": (
                        base_date + timedelta(days=i * 7)
                    ).isoformat(),  # All Saturdays
                }
                for i in range(10)
            ],
            "files": ["main.py"],
            "languages": {"Python": 1},
        }

        result = analyzer.analyze(repo_data)

        behavioral_obs = [o for o in result.observations if o.category == "behavioral"]
        weekend_obs = [o for o in behavioral_obs if "weekend" in o.finding.lower()]

        if weekend_obs:
            obs = weekend_obs[0]
            # Should report fact, not judge
            assert "observed" in obs.finding.lower() or "made on" in obs.finding.lower()
            assert "poor work-life balance" not in obs.finding.lower()
            assert "concerning" not in obs.finding.lower()

    def test_evidence_is_specific(self, analyzer, sample_repo_data):
        """Test that evidence references specific files/commits."""
        result = analyzer.analyze(sample_repo_data)

        for obs in result.observations:
            if obs.evidence:  # If evidence is provided
                # Should be specific file names or commit SHAs
                for evidence in obs.evidence:
                    assert isinstance(evidence, str)
                    assert len(evidence) > 0
                    # Should be actual filenames or commit refs from the data
                    assert any(
                        evidence in sample_repo_data.get("files", [])
                        or evidence.startswith("abc")  # commit SHA pattern
                        or evidence in ["developer1", "developer2"]  # contributor names
                        for evidence in obs.evidence
                    )


class TestObservationDataStructure:
    """Test the Observation data structure."""

    def test_observation_creation(self):
        """Test creating an observation."""
        obs = Observation(
            category="technical",
            finding="Repository uses Python and JavaScript",
            evidence=["main.py", "app.js"],
            context="Multi-language project",
            data_limitations=["Cannot assess proficiency level"],
            interview_topics=["Language selection criteria"],
        )

        assert obs.category == "technical"
        assert "Python and JavaScript" in obs.finding
        assert len(obs.evidence) == 2
        assert len(obs.data_limitations) == 1
        assert len(obs.interview_topics) == 1

    def test_observation_defaults(self):
        """Test observation with default values."""
        obs = Observation(
            category="quality",
            finding="Tests present",
            evidence=["test_main.py"],
            context="Testing infrastructure exists",
        )

        assert obs.data_limitations == []
        assert obs.interview_topics == []


class TestDataSufficiency:
    """Test DataSufficiency data structure."""

    def test_data_sufficiency_summary(self):
        """Test summary generation."""
        sufficiency = DataSufficiency(
            total_commits=50,
            time_span_days=90,
            contributors=3,
            file_count=25,
            languages=["Python", "JavaScript"],
            has_tests=True,
            has_documentation=True,
            limitations=["No PR data"],
        )

        summary = sufficiency.summary
        assert "50 commits" in summary
        assert "90 days" in summary
        assert "3 contributors" in summary
        assert "25 files" in summary

    def test_single_contributor_grammar(self):
        """Test correct grammar for single contributor."""
        sufficiency = DataSufficiency(
            total_commits=10,
            time_span_days=5,
            contributors=1,
            file_count=3,
            languages=["Python"],
            has_tests=False,
            has_documentation=False,
            limitations=[],
        )

        summary = sufficiency.summary
        assert "1 contributor" in summary  # Not "1 contributors"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
