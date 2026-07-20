"""
Unit tests for evidence-based template responses.

Ensures template responses avoid arbitrary scores and provide factual observations.
"""

from datetime import datetime, timezone

import pytest

from github_analyzer.ai.templates_evidence_based import (
    EvidenceBasedTemplateResponse,
    EvidenceBasedTemplateResponses,
)
from github_analyzer.core.classifier import TemplateCategory
from github_analyzer.data.models import RepositoryData, RepositoryMetrics


def create_test_repo(**kwargs):
    """Helper to create test repository with defaults."""
    defaults = {
        "url": "https://github.com/user/test-repo",
        "full_name": "user/test-repo",
        "name": "test-repo",
        "owner": "user",
        "description": "Test repository",
        "created_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2025, 7, 20, tzinfo=timezone.utc),
        "pushed_at": datetime(2025, 7, 20, tzinfo=timezone.utc),
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


class TestEvidenceBasedTemplateResponses:
    """Test evidence-based template response generation."""

    @pytest.fixture
    def template_manager(self):
        """Create template response manager."""
        return EvidenceBasedTemplateResponses()

    @pytest.fixture
    def inactive_repo(self):
        """Create inactive repository data."""
        return create_test_repo(
            name="inactive-repo",
            full_name="test/inactive-repo",
            metrics=RepositoryMetrics(
                total_commits=50,
                unique_contributors=1,
                lines_of_code=1000,
                test_coverage_estimate=0.0,
                documentation_presence="2 documentation files in 10 total files",
                days_since_last_commit=800,
                commit_frequency=0.0,
                avg_commit_size=20.0,
            ),
            has_readme=True,
            has_tests=False,
        )

    @pytest.fixture
    def minimal_repo(self):
        """Create minimal repository data."""
        return create_test_repo(
            name="minimal-repo",
            full_name="test/minimal-repo",
            metrics=RepositoryMetrics(
                total_commits=2,
                unique_contributors=1,
                lines_of_code=100,
                test_coverage_estimate=0.0,
                documentation_presence="0 documentation files found",
                days_since_last_commit=30,
                commit_frequency=0.05,
                avg_commit_size=10.0,
            ),
            has_readme=False,
            has_tests=False,
        )

    def test_no_scores_in_responses(self, template_manager, inactive_repo):
        """Ensure template responses contain no scores."""
        response = template_manager.get_response(
            TemplateCategory.INACTIVE, inactive_repo
        )

        # Check response doesn't have score fields
        response_dict = response.to_dict()
        assert "evidence_strength" not in response_dict
        assert "score" not in response_dict
        assert "rating" not in response_dict

        # Check no scoring language in content
        all_text = (
            response.summary
            + " ".join(response.observations)
            + " ".join(response.data_limitations)
            + " ".join(response.interview_guidance)
        ).lower()

        assert "score" not in all_text
        assert "excellent" not in all_text
        assert "poor" not in all_text
        assert "good" not in all_text
        assert "bad" not in all_text

    def test_observations_are_factual(self, template_manager, minimal_repo):
        """Test that observations state facts without judgment."""
        response = template_manager.get_response(TemplateCategory.MINIMAL, minimal_repo)

        # Each observation should be factual
        for obs in response.observations:
            # Should contain factual language (numbers, states of being, etc.)
            factual_indicators = [
                any(char.isdigit() for char in obs),
                "has" in obs.lower(),
                "contains" in obs.lower(),
                "available" in obs.lower(),
                "detected" in obs.lower(),
                "found" in obs.lower(),
                "shows" in obs.lower(),
                "total" in obs.lower(),
            ]
            assert any(factual_indicators), f"Observation lacks factual language: {obs}"

            # Should not contain evaluative language
            assert "good" not in obs.lower()
            assert "poor" not in obs.lower()
            assert "excellent" not in obs.lower()
            assert "weak" not in obs.lower()

    def test_data_limitations_acknowledged(self, template_manager, inactive_repo):
        """Test that data limitations are explicitly stated."""
        response = template_manager.get_response(
            TemplateCategory.INACTIVE, inactive_repo
        )

        assert len(response.data_limitations) > 0

        # Should acknowledge what cannot be assessed
        limitations_text = " ".join(response.data_limitations).lower()
        assert "cannot" in limitations_text or "unable" in limitations_text
        assert "assess" in limitations_text or "evaluate" in limitations_text

    def test_interview_guidance_provided(self, template_manager, minimal_repo):
        """Test that interview guidance is actionable."""
        response = template_manager.get_response(TemplateCategory.MINIMAL, minimal_repo)

        assert len(response.interview_guidance) > 0

        # Guidance should be exploratory
        for guidance in response.interview_guidance:
            assert any(
                word in guidance.lower()
                for word in ["discuss", "explore", "assess", "review", "request"]
            )

    def test_data_sufficiency_levels(self, template_manager):
        """Test that data sufficiency is properly set."""
        repos = [
            (TemplateCategory.EMPTY, "minimal"),
            (TemplateCategory.MINIMAL, "minimal"),
            (TemplateCategory.ARCHIVED, "limited"),
            (TemplateCategory.FORK, "limited"),
            (TemplateCategory.LEARNING, "limited"),
        ]

        for category, expected_sufficiency in repos:
            # Create appropriate repo data for each category
            metrics = RepositoryMetrics(
                total_commits=1 if category == TemplateCategory.MINIMAL else 10,
                unique_contributors=1,
                lines_of_code=100,
                test_coverage_estimate=0.0,
                documentation_presence="1 documentation files in 10 total files",
                days_since_last_commit=(
                    1000 if category == TemplateCategory.INACTIVE else 30
                ),
                commit_frequency=0.01,
                avg_commit_size=15.0,
            )

            repo_data = create_test_repo(
                name="test-repo",
                full_name="test/test-repo",
                metrics=metrics,
                is_archived=(category == TemplateCategory.ARCHIVED),
                is_fork=(category == TemplateCategory.FORK),
                has_readme=False,
                has_tests=False,
            )

            response = template_manager.get_response(category, repo_data)
            assert response.data_sufficiency == expected_sufficiency

    def test_inactive_response_content(self, template_manager, inactive_repo):
        """Test specific content of inactive repository response."""
        response = template_manager.get_response(
            TemplateCategory.INACTIVE, inactive_repo
        )

        # Should mention the specific days
        assert "800 days" in response.summary or "800 days" in response.observations[0]

        # Should have appropriate limitations
        assert any("current" in lim for lim in response.data_limitations)

        # Should suggest looking at other repos
        assert any(
            "repositories" in guide.lower() for guide in response.interview_guidance
        )

    def test_minimal_response_content(self, template_manager, minimal_repo):
        """Test specific content of minimal repository response."""
        response = template_manager.get_response(TemplateCategory.MINIMAL, minimal_repo)

        # Should mention the commit count
        assert "2" in response.summary or "2" in response.observations[0]

        # Should acknowledge insufficient data
        assert "insufficient" in response.summary.lower()

        # Should request more samples
        assert any("samples" in guide.lower() for guide in response.interview_guidance)

    def test_archived_response_content(self, template_manager):
        """Test archived repository response."""
        metrics = RepositoryMetrics(
            total_commits=100,
            unique_contributors=3,
            lines_of_code=5000,
            test_coverage_estimate=0.3,
            documentation_presence="4 documentation files in 10 total files",
            days_since_last_commit=500,
            commit_frequency=0.1,
            avg_commit_size=30.0,
        )

        archived_repo = create_test_repo(
            name="archived-repo",
            full_name="test/archived-repo",
            metrics=metrics,
            is_archived=True,
            is_fork=False,
            has_readme=True,
            has_tests=True,
        )

        response = template_manager.get_response(
            TemplateCategory.ARCHIVED, archived_repo
        )

        # Should state it's archived
        assert "archived" in response.summary.lower()
        assert "archived" in response.observations[0].lower()

        # Should note it's historical
        assert "historical" in response.summary.lower()

    def test_poor_practices_response_content(self, template_manager):
        """Test poor practices response avoids judgment."""
        metrics = RepositoryMetrics(
            total_commits=20,
            unique_contributors=1,
            lines_of_code=500,
            test_coverage_estimate=0.0,
            documentation_presence="0 documentation files found",
            days_since_last_commit=10,
            commit_frequency=0.05,
            avg_commit_size=15.0,
        )

        poor_repo = create_test_repo(
            name="poor-practices-repo",
            full_name="test/poor-practices-repo",
            metrics=metrics,
            is_archived=False,
            is_fork=False,
            has_readme=False,
            has_tests=False,
        )

        response = template_manager.get_response(
            TemplateCategory.POOR_PRACTICES, poor_repo
        )

        # Should not use judgmental language (except in repo name)
        summary_without_repo_name = response.summary.replace(poor_repo.name, "")
        assert "poor" not in summary_without_repo_name.lower()
        assert "bad" not in summary_without_repo_name.lower()

        # Should frame as exploration
        assert "explored" in response.summary or "areas" in response.summary

        # Should list specific observations
        assert "No README documentation found" in response.observations
        assert "No test files detected" in response.observations

    def test_template_cost_is_zero(self, template_manager, inactive_repo):
        """Ensure all template responses have zero cost."""
        categories = [
            TemplateCategory.INACTIVE,
            TemplateCategory.MINIMAL,
            TemplateCategory.ARCHIVED,
            TemplateCategory.EMPTY,
            TemplateCategory.FORK,
            TemplateCategory.LEARNING,
            TemplateCategory.POOR_PRACTICES,
        ]

        for category in categories:
            response = template_manager.get_response(category, inactive_repo)
            assert response.cost == 0.0
            assert response.generated_by == "template"

    def test_evidence_patterns_structure(self, template_manager, minimal_repo):
        """Test that evidence patterns have proper structure."""
        response = template_manager.get_response(TemplateCategory.MINIMAL, minimal_repo)

        assert len(response.evidence_patterns) > 0

        for pattern in response.evidence_patterns:
            assert "pattern" in pattern
            assert "evidence" in pattern
            assert "data_points" in pattern

            # Should not have strength ratings
            assert "strength" not in pattern
            assert "score" not in pattern


class TestEvidenceBasedTemplateResponse:
    """Test the template response data structure."""

    def test_response_creation(self):
        """Test creating a template response."""
        response = EvidenceBasedTemplateResponse(
            summary="Repository shows no recent activity.",
            observations=["Last commit 365 days ago", "10 total commits"],
            evidence_patterns=[
                {
                    "pattern": "inactive",
                    "evidence": "No recent commits",
                    "data_points": 1,
                }
            ],
            data_limitations=["Cannot assess current skills"],
            interview_guidance=["Discuss recent work"],
            data_sufficiency="minimal",
        )

        assert response.cost == 0.0
        assert response.generated_by == "template"
        assert response.data_sufficiency == "minimal"
        assert len(response.observations) == 2
        assert len(response.data_limitations) == 1
        assert len(response.interview_guidance) == 1

    def test_response_validation(self):
        """Test that non-zero cost raises error."""
        with pytest.raises(ValueError, match="Template responses must have zero cost"):
            EvidenceBasedTemplateResponse(summary="Test", cost=0.01)  # Should fail

    def test_response_serialization(self):
        """Test converting response to dictionary."""
        response = EvidenceBasedTemplateResponse(
            summary="Test summary",
            observations=["Observation 1"],
            data_sufficiency="limited",
        )

        response_dict = response.to_dict()

        assert response_dict["summary"] == "Test summary"
        assert response_dict["observations"] == ["Observation 1"]
        assert response_dict["data_sufficiency"] == "limited"
        assert response_dict["method"] == "template"
        assert response_dict["cost"] == 0.0

        # Should not have score fields
        assert "evidence_strength" not in response_dict
        assert "scores" not in response_dict


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
