"""
Unit tests for template responses module.
"""

from datetime import datetime, timezone

import pytest

from github_analyzer.ai.templates import TemplateResponse, TemplateResponses
from github_analyzer.core.classifier import TemplateCategory
from github_analyzer.data.models import RepositoryData, RepositoryMetrics


class TestTemplateResponses:
    """Test cases for TemplateResponses class."""

    @pytest.fixture
    def templates(self):
        """Create TemplateResponses instance."""
        return TemplateResponses()

    @pytest.fixture
    def sample_repo_data(self):
        """Create sample repository data."""
        metrics = RepositoryMetrics(
            total_commits=2,
            unique_contributors=1,
            lines_of_code=100,
            test_coverage_estimate=0.2,
            documentation_presence="3 documentation files in 10 total files",
            days_since_last_commit=800,
            commit_frequency=0.1,
            avg_commit_size=50,
        )

        return RepositoryData(
            url="https://github.com/user/minimal-repo",
            full_name="user/minimal-repo",
            name="minimal-repo",
            owner="user",
            description="A minimal test repository",
            created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
            pushed_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
            default_branch="main",
            size=50,
            languages={"Python": 100},
            topics=[],
            license_name=None,
            stars=0,
            forks=0,
            watchers=0,
            open_issues=0,
            has_readme=True,
            has_license=False,
            has_contributing=False,
            has_tests=False,
            has_ci_config=False,
            recent_commits=[],
            file_structure=[],
            readme_content="Basic README",
            metrics=metrics,
            fetched_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
            is_private=False,
            is_fork=False,
            is_archived=False,
            is_disabled=False,
        )

    def test_get_template_response_inactive(self, templates, sample_repo_data):
        """Test template response for inactive repositories."""
        response = templates.get_response(TemplateCategory.INACTIVE, sample_repo_data)

        assert isinstance(response, TemplateResponse)
        assert isinstance(response.evidence_strength, dict)
        assert response.evidence_strength["technical_competence"] == 20
        assert "inactive" in response.summary.lower()
        assert response.cost == 0.0
        assert len(response.key_insights) >= 1
        assert len(response.verification_gaps) >= 1

    def test_get_template_response_minimal(self, templates, sample_repo_data):
        """Test template response for minimal repositories."""
        response = templates.get_response(TemplateCategory.MINIMAL, sample_repo_data)

        assert isinstance(response, TemplateResponse)
        assert isinstance(response.evidence_strength, dict)
        assert response.evidence_strength["technical_competence"] == 25
        assert (
            "minimal" in response.summary.lower()
            or "few commits" in response.summary.lower()
        )
        assert response.cost == 0.0

    def test_get_template_response_archived(self, templates, sample_repo_data):
        """Test template response for archived repositories."""
        sample_repo_data.is_archived = True
        response = templates.get_response(TemplateCategory.ARCHIVED, sample_repo_data)

        assert isinstance(response, TemplateResponse)
        assert isinstance(response.evidence_strength, dict)
        assert response.evidence_strength["technical_competence"] == 30
        assert "archived" in response.summary.lower()
        assert response.cost == 0.0

    def test_get_template_response_empty(self, templates, sample_repo_data):
        """Test template response for empty repositories."""
        response = templates.get_response(TemplateCategory.EMPTY, sample_repo_data)

        assert isinstance(response, TemplateResponse)
        assert isinstance(response.evidence_strength, dict)
        assert response.evidence_strength["technical_competence"] == 0
        assert (
            "empty" in response.summary.lower()
            or "minimal content" in response.summary.lower()
        )

    def test_get_template_response_fork(self, templates, sample_repo_data):
        """Test template response for unmodified forks."""
        sample_repo_data.is_fork = True
        response = templates.get_response(TemplateCategory.FORK, sample_repo_data)

        assert isinstance(response, TemplateResponse)
        assert isinstance(response.evidence_strength, dict)
        assert response.evidence_strength["technical_competence"] == 15
        assert "fork" in response.summary.lower()

    def test_get_template_response_learning(self, templates, sample_repo_data):
        """Test template response for learning repositories."""
        sample_repo_data.name = "python-tutorial"
        response = templates.get_response(TemplateCategory.LEARNING, sample_repo_data)

        assert isinstance(response, TemplateResponse)
        assert isinstance(response.evidence_strength, dict)
        assert response.evidence_strength["technical_competence"] == 40
        assert (
            "learning" in response.summary.lower()
            or "tutorial" in response.summary.lower()
        )

    def test_get_template_response_poor_practices(self, templates, sample_repo_data):
        """Test template response for poor practices."""
        sample_repo_data.has_readme = False
        response = templates.get_response(
            TemplateCategory.POOR_PRACTICES, sample_repo_data
        )

        assert isinstance(response, TemplateResponse)
        assert isinstance(response.evidence_strength, dict)
        assert response.evidence_strength["technical_competence"] == 35
        assert len(response.key_insights) >= 1

    def test_invalid_template_category(self, templates, sample_repo_data):
        """Test handling of invalid template category."""
        with pytest.raises(ValueError):
            templates.get_response("INVALID_CATEGORY", sample_repo_data)

    def test_template_personalization(self, templates, sample_repo_data):
        """Test that templates are personalized with repository data."""
        response = templates.get_response(TemplateCategory.MINIMAL, sample_repo_data)

        # Should contain repository-specific information
        assert (
            sample_repo_data.name in response.summary
            or sample_repo_data.full_name in response.summary
        )


class TestTemplateResponse:
    """Test cases for TemplateResponse class."""

    def test_template_response_creation(self):
        """Test TemplateResponse creation."""
        response = TemplateResponse(
            summary="This is a test template response",
            evidence_strength={
                "technical_competence": 90,
                "communication_skills": 85,
                "professional_practices": 80,
                "growth_potential": 75,
            },
            key_insights=["Good documentation", "Lacks tests"],
            evidence_patterns=[
                {
                    "pattern": "test_pattern",
                    "evidence": "Test evidence",
                    "strength": "moderate",
                }
            ],
            verification_gaps=["Cannot verify team collaboration"],
            cost=0.0,
        )

        assert response.evidence_strength["technical_competence"] == 90
        assert response.cost == 0.0
        assert len(response.key_insights) == 2
        assert len(response.evidence_patterns) == 1
        assert len(response.verification_gaps) == 1

    def test_template_response_to_dict(self):
        """Test TemplateResponse serialization."""
        response = TemplateResponse(
            summary="Mixed signals",
            evidence_strength={
                "technical_competence": 75,
                "communication_skills": 70,
                "professional_practices": 65,
                "growth_potential": 80,
            },
            key_insights=["Some positive indicators"],
            cost=0.0,
        )

        response_dict = response.to_dict()

        assert response_dict["evidence_strength"]["technical_competence"] == 75
        assert response_dict["cost"] == 0.0
        assert response_dict["method"] == "template"
        assert "summary" in response_dict

    def test_template_response_validation(self):
        """Test TemplateResponse validation."""
        # Template responses should always have zero cost
        with pytest.raises(ValueError):
            TemplateResponse(
                summary="Test",
                evidence_strength={"technical_competence": 90},
                cost=0.01,  # Should be 0.0 for template
            )

        # Test invalid evidence strength score
        with pytest.raises(ValueError):
            TemplateResponse(
                summary="Test",
                evidence_strength={"technical_competence": 150},  # Should be 0-100
                cost=0.0,
            )
