"""
Integration tests for AI analysis module.

Tests the complete flow from repository classification to AI analysis.
"""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from github_analyzer.ai.analyzer import AIAnalyzer
from github_analyzer.ai.templates import TemplateResponses
from github_analyzer.core.classifier import (
    AnalysisMethod,
    RepositoryClassifier,
    TemplateCategory,
)
from github_analyzer.data.models import FileInfo, RepositoryData, RepositoryMetrics


class TestAIIntegration:
    """Integration tests for AI analysis workflow."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration for integration tests."""
        with patch(
            "github_analyzer.core.classifier.get_config"
        ) as mock_classifier_config:
            with patch(
                "github_analyzer.ai.analyzer.get_config"
            ) as mock_analyzer_config:
                with patch(
                    "github_analyzer.ai.cost_tracker.get_config"
                ) as mock_cost_config:
                    config = Mock()

                    # Analysis config
                    analysis_config = Mock()
                    analysis_config.template_threshold_days = 730
                    analysis_config.min_commits_for_ai = 3
                    analysis_config.max_context_length = 8000
                    analysis_config.ai_temperature = 0.3
                    config.analysis = analysis_config

                    # Cost config
                    cost_config = Mock()
                    cost_config.max_cost_per_analysis = 0.02
                    cost_config.max_daily_cost = 10.0
                    cost_config.alert_threshold = 0.8
                    config.cost = cost_config

                    # Anthropic config
                    config.anthropic_api_key = "test-api-key"

                    mock_classifier_config.return_value = config
                    mock_analyzer_config.return_value = config
                    mock_cost_config.return_value = config
                    yield config

    @pytest.fixture
    def sample_inactive_repo(self):
        """Create sample inactive repository data."""
        metrics = RepositoryMetrics(
            total_commits=10,
            unique_contributors=2,
            lines_of_code=1000,
            test_coverage_estimate=0.3,
            documentation_presence="4 documentation files in 10 total files",
            days_since_last_commit=800,  # Inactive
            commit_frequency=0.5,
            avg_commit_size=50,
        )

        return RepositoryData(
            url="https://github.com/user/inactive-repo",
            full_name="user/inactive-repo",
            name="inactive-repo",
            owner="user",
            description="An inactive test repository",
            created_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2022, 1, 1, tzinfo=timezone.utc),
            pushed_at=datetime(2022, 1, 1, tzinfo=timezone.utc),
            default_branch="main",
            size=100,
            languages={"Python": 1000},
            topics=["python"],
            license_name="MIT",
            stars=5,
            forks=1,
            watchers=2,
            open_issues=0,
            has_readme=True,
            has_license=True,
            has_contributing=False,
            has_tests=False,
            has_ci_config=False,
            recent_commits=[],
            file_structure=[
                FileInfo("main.py", "main.py", 500, "file", "py"),
                FileInfo(
                    "README.md", "README.md", 200, "file", "md", is_documentation=True
                ),
                FileInfo("utils.py", "utils.py", 800, "file", "py"),
                FileInfo("config.py", "config.py", 600, "file", "py"),
                FileInfo("setup.py", "setup.py", 400, "file", "py"),
                FileInfo("requirements.txt", "requirements.txt", 300, "file", "txt"),
            ],
            readme_content="Basic README for inactive repo",
            metrics=metrics,
            fetched_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            is_private=False,
            is_fork=False,
            is_archived=False,
            is_disabled=False,
        )

    @pytest.fixture
    def sample_complex_repo(self):
        """Create sample complex repository that should get AI analysis."""
        metrics = RepositoryMetrics(
            total_commits=50,
            unique_contributors=5,
            lines_of_code=5000,
            test_coverage_estimate=0.8,
            documentation_presence="9 documentation files in 10 total files",
            days_since_last_commit=10,  # Active
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
            topics=["web-app", "python", "javascript"],
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
                FileInfo(".github/", ".github", 0, "dir", None),
                FileInfo("utils.py", "utils.py", 1500, "file", "py"),
                FileInfo("config.py", "config.py", 800, "file", "py"),
                FileInfo("README.md", "README.md", 1200, "file", "md"),
                FileInfo("setup.py", "setup.py", 600, "file", "py"),
            ],
            readme_content="A comprehensive web application with modern architecture...",
            metrics=metrics,
            fetched_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            is_private=False,
            is_fork=False,
            is_archived=False,
            is_disabled=False,
        )

    def test_inactive_repository_template_flow(self, mock_config, sample_inactive_repo):
        """Test complete flow for inactive repository using template response."""
        # Step 1: Classify repository
        classifier = RepositoryClassifier()
        classification = classifier.classify(sample_inactive_repo)

        assert classification.method == AnalysisMethod.TEMPLATE
        assert classification.template_category == TemplateCategory.INACTIVE
        # confidence field removed - no longer checking it
        assert classification.cost_estimate == 0.0

        # Step 2: Generate template response
        templates = TemplateResponses()
        response = templates.get_response(
            classification.template_category, sample_inactive_repo
        )

        assert isinstance(response.evidence_strength, dict)
        assert response.evidence_strength["technical_competence"] == 20
        assert response.cost == 0.0
        assert "inactive" in response.summary.lower()
        assert len(response.key_insights) >= 1

        # Step 3: Verify cost optimization
        assert classification.cost_estimate == 0.0
        assert response.cost == 0.0

    def test_complex_repository_ai_flow(self, mock_config, sample_complex_repo):
        """Test complete flow for complex repository using AI analysis."""
        # Step 1: Classify repository
        classifier = RepositoryClassifier()
        classification = classifier.classify(sample_complex_repo)

        assert classification.method == AnalysisMethod.AI
        assert classification.template_category is None
        # confidence field removed - no longer checking it
        assert classification.cost_estimate > 0.0

        # Step 2: Prepare for AI analysis
        analyzer = AIAnalyzer()

        # Test context preparation
        context = analyzer._prepare_context(sample_complex_repo)
        assert sample_complex_repo.full_name in context
        assert "Python" in context
        assert "web-app" in context
        assert "50" in context  # commit count

        # Verify context length management
        assert (
            len(context) <= analyzer.max_context_length * 4
        )  # 4 chars per token estimate

    @patch("github_analyzer.ai.analyzer.anthropic.Anthropic")
    def test_end_to_end_ai_analysis_flow(
        self, mock_anthropic, mock_config, sample_complex_repo
    ):
        """Test complete end-to-end AI analysis flow."""
        # Mock Anthropic API response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [
            Mock(
                text="""{
            "summary": "Excellent repository with professional development practices",
            "observed_patterns": [
                {
                    "pattern": "comprehensive_testing",
                    "evidence": "98% test coverage with 50 test files",
                    "commits": ["abc123", "def456"],
                    "files": ["tests/", "pytest.ini"],
                    "strength": "strong"
                }
            ],
            "limitations": [
                "Cannot assess team collaboration from single-author repo"
            ],
            "context_notes": {
                "startup": {
                    "shipping_velocity": "Fast development cycles with CI/CD",
                    "adaptability": "Modern architecture supports rapid changes"
                },
                "enterprise": {
                    "scalability_thinking": "Well-documented and structured",
                    "maintainability": "Clean code with proper abstractions"
                }
            },
            "upgrade_benefit": "Additional depth analysis would provide more comprehensive patterns",
            "key_insights": [
                "Comprehensive test coverage",
                "Well-documented codebase",
                "Modern CI/CD setup"
            ]
        }"""
            )
        ]
        # Mock usage attribute for token tracking
        mock_usage = Mock()
        mock_usage.input_tokens = 1200
        mock_usage.output_tokens = 600
        mock_response.usage = mock_usage

        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        # Step 1: Classification
        classifier = RepositoryClassifier()
        classification = classifier.classify(sample_complex_repo)
        assert classification.method == AnalysisMethod.AI

        # Step 2: AI Analysis
        analyzer = AIAnalyzer()
        result = analyzer.analyze_repository(sample_complex_repo)

        # Verify results - evidence-based approach (no numerical scores)
        assert "professional development practices" in result.summary
        assert len(result.key_insights) == 3
        assert len(result.evidence_patterns) >= 1
        # Limitations are mapped to verification_gaps
        assert len(result.verification_gaps) >= 1
        # Context alignment will be empty since context_notes is not mapped to it
        assert result.context_alignment is not None
        assert result.cost > 0.0
        assert result.generated_by == "ai"

    def test_cost_tracking_integration(self, mock_config, isolated_cost_tracker):
        """Test cost tracking integration across the system."""
        cost_tracker = isolated_cost_tracker

        # Test initial state
        daily_usage = cost_tracker.get_daily_usage()
        assert daily_usage.total_cost == 0.0
        assert daily_usage.total_requests == 0

        # Simulate cost tracking
        from github_analyzer.ai.cost_tracker import APIUsage

        usage = APIUsage(
            model="claude-3-haiku-20240307",
            input_tokens=1000,
            output_tokens=500,
            cost=0.015,
            timestamp=datetime.now(timezone.utc),
        )

        cost_tracker.track_analysis(usage)

        # Verify tracking
        daily_usage = cost_tracker.get_daily_usage()
        assert daily_usage.total_cost == 0.015
        assert daily_usage.total_requests == 1
        assert daily_usage.total_input_tokens == 1000
        assert daily_usage.total_output_tokens == 500

        # Test budget checking
        within_budget, reason = cost_tracker.check_budget(0.01)
        assert within_budget is True
        assert reason is None

    def test_error_handling_integration(self, mock_config, sample_complex_repo):
        """Test error handling across integrated components."""
        # Test with invalid configuration
        with patch("github_analyzer.ai.analyzer.get_config") as mock_bad_config:
            mock_bad_config.side_effect = Exception("Config error")

            with pytest.raises(Exception):
                AIAnalyzer()

    def test_analysis_method_selection_logic(self, mock_config):
        """Test the logic that determines analysis method."""
        classifier = RepositoryClassifier()

        # Create repositories that should trigger different analysis methods
        test_cases = [
            # (repo_modifications, expected_method, expected_category)
            (
                {"metrics.days_since_last_commit": 800},
                AnalysisMethod.TEMPLATE,
                TemplateCategory.INACTIVE,
            ),
            (
                {"metrics.total_commits": 2},
                AnalysisMethod.TEMPLATE,
                TemplateCategory.MINIMAL,
            ),
            ({"is_archived": True}, AnalysisMethod.TEMPLATE, TemplateCategory.ARCHIVED),
            ({"size": 5}, AnalysisMethod.TEMPLATE, TemplateCategory.EMPTY),
        ]

        for modifications, expected_method, expected_category in test_cases:
            # Create base repo
            # NOTE: Use 25 commits (not 50) so inactive test works correctly
            # With new logic: >30 commits bypasses INACTIVE classification
            metrics = RepositoryMetrics(
                total_commits=25,
                unique_contributors=5,
                lines_of_code=5000,
                test_coverage_estimate=0.8,
                documentation_presence="9 documentation files in 10 total files",
                days_since_last_commit=10,
                commit_frequency=2.5,
                avg_commit_size=150,
            )

            repo_data = RepositoryData(
                url="https://github.com/user/test-repo",
                full_name="user/test-repo",
                name="test-repo",
                owner="user",
                description="Test repository",
                created_at=datetime(2022, 1, 1, tzinfo=timezone.utc),
                updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
                pushed_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
                default_branch="main",
                size=2500,
                languages={"Python": 5000},
                topics=[],
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
                    FileInfo("main.py", "main.py", 2000, "file", "py"),
                    FileInfo("utils.py", "utils.py", 1500, "file", "py"),
                    FileInfo("test_main.py", "test_main.py", 1000, "file", "py"),
                    FileInfo("config.py", "config.py", 800, "file", "py"),
                    FileInfo("setup.py", "setup.py", 600, "file", "py"),
                    FileInfo("README.md", "README.md", 1200, "file", "md"),
                ],
                readme_content="Test README",
                metrics=metrics,
                fetched_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
                is_private=False,
                is_fork=False,
                is_archived=False,
                is_disabled=False,
            )

            # Apply modifications
            for key, value in modifications.items():
                if "." in key:
                    obj_name, attr_name = key.split(".")
                    setattr(getattr(repo_data, obj_name), attr_name, value)
                else:
                    setattr(repo_data, key, value)

            # Test classification
            classification = classifier.classify(repo_data)
            assert classification.method == expected_method
            if expected_category:
                assert classification.template_category == expected_category
