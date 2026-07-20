"""Test the updated AI vs template analysis decision logic."""

from unittest.mock import MagicMock

from github_analyzer.api.routes.analysis import _should_use_ai_analysis


class TestAIAnalysisLogic:
    """Test suite for AI vs template analysis decisions."""

    def test_popular_repository_always_uses_ai(self):
        """Popular repositories should ALWAYS get AI analysis."""
        repo_data = MagicMock()
        repo_data.stars = 100  # Popular repo
        repo_data.size = 200
        repo_data.languages = {"JavaScript": 100}
        repo_data.metrics = MagicMock(commit_frequency=1, unique_contributors=3)
        repo_data.full_name = "sindresorhus/p-queue"

        classification = MagicMock()
        classification.repository_type = MagicMock(value="production")

        confidence = MagicMock()

        assert _should_use_ai_analysis(repo_data, classification, confidence) is True

    def test_production_library_always_uses_ai(self):
        """Production/library code should ALWAYS get AI analysis."""
        repo_data = MagicMock()
        repo_data.stars = 10  # Not popular
        repo_data.size = 100
        repo_data.languages = {"Python": 100}
        repo_data.metrics = MagicMock(commit_frequency=0.5, unique_contributors=2)
        repo_data.full_name = "company/internal-lib"

        classification = MagicMock()
        classification.repository_type = MagicMock(value="library")

        confidence = MagicMock()

        assert _should_use_ai_analysis(repo_data, classification, confidence) is True

    def test_active_community_uses_ai(self):
        """Repos with active community should get AI analysis."""
        repo_data = MagicMock()
        repo_data.stars = 20
        repo_data.size = 300
        repo_data.languages = {"Go": 100}
        repo_data.metrics = MagicMock(
            commit_frequency=1, unique_contributors=6
        )  # >5 contributors
        repo_data.full_name = "team/collaborative-project"

        classification = MagicMock()
        classification.repository_type = MagicMock(value="production")

        confidence = MagicMock()

        assert _should_use_ai_analysis(repo_data, classification, confidence) is True

    def test_large_codebase_uses_ai(self):
        """Large codebases should get AI analysis."""
        repo_data = MagicMock()
        repo_data.stars = 5
        repo_data.size = 600  # >500KB
        repo_data.languages = {"Java": 100}
        repo_data.metrics = MagicMock(commit_frequency=0.5, unique_contributors=1)
        repo_data.full_name = "dev/big-project"

        classification = MagicMock()
        classification.repository_type = MagicMock(value="unknown")

        confidence = MagicMock()

        assert _should_use_ai_analysis(repo_data, classification, confidence) is True

    def test_multi_language_uses_ai(self):
        """Multi-language projects should get AI analysis."""
        repo_data = MagicMock()
        repo_data.stars = 10
        repo_data.size = 200
        repo_data.languages = {"Python": 40, "JavaScript": 30, "Go": 30}
        repo_data.metrics = MagicMock(commit_frequency=1, unique_contributors=2)
        repo_data.full_name = "startup/fullstack-app"

        classification = MagicMock()
        classification.repository_type = MagicMock(value="portfolio")

        confidence = MagicMock()

        assert _should_use_ai_analysis(repo_data, classification, confidence) is True

    def test_active_development_uses_ai(self):
        """Actively developed projects should get AI analysis."""
        repo_data = MagicMock()
        repo_data.stars = 15
        repo_data.size = 300
        repo_data.languages = {"Rust": 100}
        repo_data.metrics = MagicMock(
            commit_frequency=3, unique_contributors=1
        )  # >2 commits/week
        repo_data.full_name = "dev/active-project"

        classification = MagicMock()
        classification.repository_type = MagicMock(value="production")

        confidence = MagicMock()

        assert _should_use_ai_analysis(repo_data, classification, confidence) is True

    def test_abandoned_project_uses_template(self):
        """Truly abandoned projects can use templates."""
        repo_data = MagicMock()
        repo_data.stars = 0
        repo_data.size = 40
        repo_data.languages = {"Python": 100}
        repo_data.metrics = MagicMock(
            commit_frequency=0,
            unique_contributors=1,
            days_since_last_commit=400,  # >1 year
        )
        repo_data.file_count = 3
        repo_data.forks = 0
        repo_data.full_name = "student/old-homework"

        classification = MagicMock()
        classification.repository_type = MagicMock(value="abandoned")

        confidence = MagicMock()

        assert _should_use_ai_analysis(repo_data, classification, confidence) is False

    def test_hello_world_uses_template(self):
        """Hello world repos can use templates."""
        repo_data = MagicMock()
        repo_data.stars = 0
        repo_data.size = 10  # <50KB
        repo_data.languages = {"Python": 100}
        repo_data.metrics = MagicMock(commit_frequency=0, unique_contributors=1)
        repo_data.file_count = 2
        repo_data.forks = 0
        repo_data.full_name = "beginner/hello-world"

        classification = MagicMock()
        classification.repository_type = MagicMock(value="learning")

        confidence = MagicMock()

        assert _should_use_ai_analysis(repo_data, classification, confidence) is False

    def test_small_learning_project_uses_template(self):
        """Small learning projects with no community can use templates."""
        repo_data = MagicMock()
        repo_data.stars = 0
        repo_data.size = 80
        repo_data.languages = {"JavaScript": 100}
        repo_data.metrics = MagicMock(commit_frequency=0.1, unique_contributors=1)
        repo_data.forks = 0
        repo_data.full_name = "student/todo-app"

        classification = MagicMock()
        classification.repository_type = MagicMock(value="learning")

        confidence = MagicMock()

        assert _should_use_ai_analysis(repo_data, classification, confidence) is False

    def test_medium_repo_defaults_to_ai(self):
        """Medium repos that don't fit clear categories should use AI."""
        repo_data = MagicMock()
        repo_data.stars = 30
        repo_data.size = 400
        repo_data.languages = {"Python": 80, "Shell": 20}
        repo_data.metrics = MagicMock(commit_frequency=1.5, unique_contributors=3)
        repo_data.full_name = "team/side-project"

        classification = MagicMock()
        classification.repository_type = MagicMock(value="portfolio")

        confidence = MagicMock()

        assert _should_use_ai_analysis(repo_data, classification, confidence) is True

    def test_edge_case_defaults_to_ai(self):
        """When in doubt, default to AI for quality."""
        repo_data = MagicMock()
        repo_data.stars = 25
        repo_data.size = 250
        repo_data.languages = {"TypeScript": 100}
        repo_data.metrics = MagicMock(
            commit_frequency=1, unique_contributors=2, days_since_last_commit=30
        )
        repo_data.file_count = 20
        repo_data.forks = 2
        repo_data.full_name = "startup/mvp"

        classification = MagicMock()
        classification.repository_type = MagicMock(value="unknown")

        confidence = MagicMock()

        assert _should_use_ai_analysis(repo_data, classification, confidence) is True
