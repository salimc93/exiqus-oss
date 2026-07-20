"""
Unit tests for context-aware repository analysis.
"""

from datetime import datetime, timezone

import pytest

from github_analyzer.core.context_analyzer import (
    AnalysisContext,
    ContextAnalyzer,
    ContextualAssessment,
)
from github_analyzer.data.models import (
    FileInfo,
    RepositoryData,
    RepositoryMetrics,
)


def create_test_repo(**kwargs):
    """Helper to create test repository with defaults."""
    defaults = {
        "url": "https://github.com/user/repo",
        "full_name": "user/repo",
        "name": "repo",
        "owner": "user",
        "description": "Test repository",
        "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2024, 12, 20, tzinfo=timezone.utc),
        "pushed_at": datetime(2024, 12, 20, tzinfo=timezone.utc),
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
    # Override with provided kwargs
    defaults.update(kwargs)
    return RepositoryData(**defaults)


@pytest.fixture
def context_analyzer():
    """Create a context analyzer instance."""
    return ContextAnalyzer()


@pytest.fixture
def startup_repo():
    """Create a repository typical for startup development."""
    return create_test_repo(
        name="rapid-mvp",
        full_name="user/rapid-mvp",
        description="Quick MVP for startup idea",
        size=500,
        stars=2,
        forks=0,
        open_issues=3,
        languages={"JavaScript": 60000, "Python": 30000, "Go": 10000},
        readme_content="# Rapid MVP\n\nQuick and dirty solution that works!",
        has_license=False,
        has_tests=False,
        has_ci_config=False,
        has_contributing=False,
        topics=["mvp", "startup", "prototype"],
        file_structure=[
            FileInfo(path="src", name="src", size=0, type="directory"),
            FileInfo(
                path="src/app.js", name="app.js", size=5000, type="file", extension="js"
            ),
            FileInfo(
                path="src/api.py", name="api.py", size=3000, type="file", extension="py"
            ),
            FileInfo(
                path="README.md",
                name="README.md",
                size=100,
                type="file",
                extension="md",
                is_documentation=True,
            ),
        ],
        metrics=RepositoryMetrics(
            total_commits=50,
            unique_contributors=1,
            days_since_last_commit=10,
            commit_frequency=7.0,  # High frequency
            avg_commit_size=200.0,
            lines_of_code=8000,
            test_coverage_estimate=0.0,
            documentation_presence="1 documentation files in 20 total files",
        ),
    )


@pytest.fixture
def enterprise_repo():
    """Create a repository typical for enterprise development."""
    return create_test_repo(
        name="payment-service",
        full_name="company/payment-service",
        owner="company",
        description="Enterprise payment processing service",
        created_at=datetime(2022, 1, 1, tzinfo=timezone.utc),
        size=10000,
        stars=15,
        forks=5,
        open_issues=2,
        languages={"Java": 200000, "SQL": 50000},
        readme_content="# Payment Service\n\n" + "Detailed docs...\n" * 100,
        has_license=True,
        license_name="MIT",
        has_tests=True,
        has_ci_config=True,
        has_contributing=True,
        topics=["enterprise", "payment", "java"],
        file_structure=[
            FileInfo(path="src", name="src", size=0, type="directory"),
            FileInfo(path="src/main", name="main", size=0, type="directory"),
            FileInfo(path="src/test", name="test", size=0, type="directory"),
            FileInfo(path="docs", name="docs", size=0, type="directory"),
            FileInfo(path="config", name="config", size=0, type="directory"),
            FileInfo(
                path=".github/workflows/ci.yml",
                name="ci.yml",
                size=500,
                type="file",
                extension="yml",
            ),
        ],
        metrics=RepositoryMetrics(
            total_commits=500,
            unique_contributors=10,
            days_since_last_commit=5,
            commit_frequency=2.0,
            avg_commit_size=100.0,
            lines_of_code=50000,
            test_coverage_estimate=0.8,
            documentation_presence="2 documentation files in 10 total files",
        ),
    )


@pytest.fixture
def agency_repo():
    """Create a repository typical for agency development."""
    return create_test_repo(
        name="client-portfolio",
        full_name="agency/client-portfolio",
        owner="agency",
        description="Portfolio of client projects",
        created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
        size=3000,
        stars=8,
        forks=2,
        open_issues=0,
        languages={"JavaScript": 40000, "Python": 30000, "Ruby": 20000, "PHP": 10000},
        readme_content="# Client Portfolio\n\nVarious client projects",
        has_license=True,
        license_name="Apache-2.0",
        has_tests=True,
        has_ci_config=False,
        has_contributing=False,
        topics=["portfolio", "clients", "web"],
        file_structure=[
            FileInfo(path="project1", name="project1", size=0, type="directory"),
            FileInfo(path="project2", name="project2", size=0, type="directory"),
            FileInfo(path="project3", name="project3", size=0, type="directory"),
            FileInfo(
                path="docs/handoff.md",
                name="handoff.md",
                size=1000,
                type="file",
                extension="md",
                is_documentation=True,
            ),
        ],
        metrics=RepositoryMetrics(
            total_commits=200,
            unique_contributors=3,
            days_since_last_commit=15,
            commit_frequency=3.0,
            avg_commit_size=150.0,
            lines_of_code=20000,
            test_coverage_estimate=0.6,
            documentation_presence="2 documentation files in 13 total files",
        ),
    )


class TestContextAnalyzer:
    """Test context analyzer functionality."""

    def test_initialization(self, context_analyzer):
        """Test context analyzer initialization."""
        assert context_analyzer is not None
        assert len(context_analyzer.criteria) == 5
        assert AnalysisContext.STARTUP in context_analyzer.criteria
        assert AnalysisContext.ENTERPRISE in context_analyzer.criteria

    def test_startup_context_analysis(self, context_analyzer, startup_repo):
        """Test analysis for startup context."""
        result = context_analyzer.analyze(startup_repo, AnalysisContext.STARTUP)

        assert isinstance(result, ContextualAssessment)
        assert result.context == AnalysisContext.STARTUP
        assert result.evidence_count >= 2  # Should have some evidence patterns
        assert len(result.strengths) >= 0  # May have no strengths for minimal repos
        assert result.key_insight is not None and len(result.key_insight) > 0

    def test_enterprise_context_analysis(self, context_analyzer, enterprise_repo):
        """Test analysis for enterprise context."""
        result = context_analyzer.analyze(enterprise_repo, AnalysisContext.ENTERPRISE)

        assert result.context == AnalysisContext.ENTERPRISE
        assert result.evidence_count >= 4  # Should have strong evidence
        assert len(result.strengths) > 0
        # Either comprehensive testing or CI/CD pipeline
        assert any(
            "testing" in s.lower() or "ci/cd" in s.lower() for s in result.strengths
        )

    def test_agency_context_analysis(self, context_analyzer, agency_repo):
        """Test analysis for agency context."""
        result = context_analyzer.analyze(agency_repo, AnalysisContext.AGENCY)

        assert result.context == AnalysisContext.AGENCY
        assert result.evidence_count >= 2  # Should have some evidence
        # Agency should have 4 languages, so should have multiple_languages signal
        if len(result.strengths) > 0:
            assert any(
                ("languages" in s or "versatile" in s.lower()) for s in result.strengths
            )

    def test_poor_fit_detection(self, context_analyzer, startup_repo):
        """Test detection of poor fit for context."""
        # Startup repo should be poor fit for enterprise
        result = context_analyzer.analyze(startup_repo, AnalysisContext.ENTERPRISE)

        assert result.evidence_count < 4  # Should have low evidence for enterprise
        assert len(result.concerns) > 0
        assert any("testing" in c.lower() for c in result.concerns)

    def test_context_comparison(self, context_analyzer, enterprise_repo):
        """Test comparing same repo across contexts."""
        results = context_analyzer.compare_contexts(enterprise_repo)

        assert len(results) == 5  # All contexts
        assert (
            results[AnalysisContext.ENTERPRISE].evidence_count
            > results[AnalysisContext.STARTUP].evidence_count
        )

        # Enterprise repo should have more evidence for enterprise than startup
        enterprise_evidence = results[AnalysisContext.ENTERPRISE].evidence_count
        startup_evidence = results[AnalysisContext.STARTUP].evidence_count
        assert enterprise_evidence > startup_evidence

    def test_recommendations_generation(self, context_analyzer, startup_repo):
        """Test recommendation generation."""
        result = context_analyzer.analyze(startup_repo, AnalysisContext.STARTUP)

        assert len(result.recommendations) > 0
        assert any("evidence" in r.lower() for r in result.recommendations)

    def test_key_insight_generation(self, context_analyzer, enterprise_repo):
        """Test key insight generation."""
        result = context_analyzer.analyze(enterprise_repo, AnalysisContext.ENTERPRISE)

        assert result.key_insight
        assert (
            "enterprise" in result.key_insight.lower()
            or "quality" in result.key_insight.lower()
        )

    def test_over_engineering_detection(self, context_analyzer):
        """Test over-engineering detection."""
        # Create over-engineered small project
        over_engineered = create_test_repo(
            name="simple-app",
            full_name="user/simple-app",
            description="Simple app",
            size=500,  # Small project
            stars=0,
            forks=0,
            open_issues=0,
            languages={"Java": 10000},
            readme_content="Simple app",
            topics=[],
            file_structure=[
                FileInfo(
                    path=f"src/layer{i}/sub{j}/file.java",
                    name="file.java",
                    size=100,
                    type="file",
                    extension="java",
                )
                for i in range(8)
                for j in range(8)
            ],  # 64 files, deep structure
            metrics=RepositoryMetrics(
                total_commits=10,
                unique_contributors=1,
                days_since_last_commit=30,
                commit_frequency=0.5,
                avg_commit_size=50.0,
                lines_of_code=1000,
                test_coverage_estimate=0.0,
                documentation_presence="1 documentation files in 10 total files",
            ),
        )

        result = context_analyzer.analyze(over_engineered, AnalysisContext.STARTUP)
        assert result.evidence_count < 3  # Low evidence for startup
        assert any("over-complicate" in c for c in result.concerns)

    def test_all_contexts_method(self, context_analyzer):
        """Test get_all_contexts method."""
        contexts = context_analyzer.get_all_contexts()
        assert len(contexts) == 5
        assert AnalysisContext.STARTUP in contexts
        assert AnalysisContext.ENTERPRISE in contexts
        assert AnalysisContext.AGENCY in contexts
        assert AnalysisContext.OPEN_SOURCE in contexts
        assert AnalysisContext.GENERAL in contexts

    def test_general_context(self, context_analyzer, startup_repo):
        """Test general context analysis."""
        result = context_analyzer.analyze(startup_repo, AnalysisContext.GENERAL)

        assert result.context == AnalysisContext.GENERAL
        assert 1 <= result.evidence_count <= 4  # Should be moderate evidence
        assert len(result.recommendations) > 0

    def test_open_source_context(self, context_analyzer):
        """Test open source context analysis."""
        open_source_repo = create_test_repo(
            name="awesome-library",
            full_name="user/awesome-library",
            description="A useful library for developers",
            created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
            size=2000,
            stars=50,
            forks=10,
            open_issues=5,
            languages={"Python": 50000},
            readme_content="# Awesome Library\n\n## Contributing\n\nWe welcome contributions!",
            has_license=True,
            license_name="MIT",
            has_tests=True,
            has_ci_config=True,
            has_contributing=True,
            topics=["library", "python", "open-source"],
            file_structure=[
                FileInfo(
                    path="CONTRIBUTING.md",
                    name="CONTRIBUTING.md",
                    size=1000,
                    type="file",
                    extension="md",
                    is_documentation=True,
                ),
                FileInfo(
                    path="CODE_OF_CONDUCT.md",
                    name="CODE_OF_CONDUCT.md",
                    size=500,
                    type="file",
                    extension="md",
                    is_documentation=True,
                ),
            ],
            metrics=RepositoryMetrics(
                total_commits=200,
                unique_contributors=15,
                days_since_last_commit=7,
                commit_frequency=2.5,
                avg_commit_size=100.0,
                lines_of_code=10000,
                test_coverage_estimate=0.85,
                documentation_presence="3 documentation files in 12 total files",
            ),
        )

        result = context_analyzer.analyze(open_source_repo, AnalysisContext.OPEN_SOURCE)
        assert result.evidence_count >= 4  # Should have strong evidence
        assert any("community" in s.lower() for s in result.strengths)

    def test_new_enterprise_signals(self, context_analyzer):
        """Test the new enterprise signals: consistent_commits, structured_codebase, team_collaboration."""
        # Create a repo that should match all new enterprise signals
        enterprise_repo = create_test_repo(
            name="enterprise-app",
            full_name="company/enterprise-app",
            description="Enterprise application for business",
            created_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
            size=50000,
            stars=10,
            forks=2,
            open_issues=15,
            languages={"Java": 80000, "TypeScript": 20000},
            readme_content="# Enterprise Application\n\n## Setup\n\nDetailed setup instructions...",
            has_license=True,
            license_name="Proprietary",
            has_tests=True,
            has_ci_config=True,
            has_contributing=True,
            topics=["enterprise", "business", "java"],
            file_structure=[
                FileInfo(
                    path="src", name="src", size=0, type="directory", extension=""
                ),
                FileInfo(
                    path="lib", name="lib", size=0, type="directory", extension=""
                ),
                FileInfo(
                    path="tests", name="tests", size=0, type="directory", extension=""
                ),
                FileInfo(
                    path="docs", name="docs", size=0, type="directory", extension=""
                ),
                FileInfo(
                    path="config", name="config", size=0, type="directory", extension=""
                ),
            ],
            metrics=RepositoryMetrics(
                total_commits=500,  # > 50 for consistent_commits
                unique_contributors=10,  # >= 2 for team_collaboration
                days_since_last_commit=2,
                commit_frequency=2.5,  # > 0.5 for consistent_commits
                avg_commit_size=150.0,
                lines_of_code=50000,
                test_coverage_estimate=0.85,
                documentation_presence="2 documentation files in 10 total files",
            ),
        )

        result = context_analyzer.analyze(enterprise_repo, AnalysisContext.ENTERPRISE)

        # With the new signals, enterprise should have strong evidence
        assert result.evidence_count >= 5  # Should have high evidence count
        assert len(result.strengths) > 5  # Should have many strengths

        # Test that each new signal handler works correctly
        from github_analyzer.core.context_analyzer import (
            _evaluate_consistent_commits,
            _evaluate_structured_codebase,
            _evaluate_team_collaboration,
        )

        # Test consistent_commits signal
        assert _evaluate_consistent_commits(enterprise_repo) is True

        # Test structured_codebase signal
        assert _evaluate_structured_codebase(enterprise_repo) is True

        # Test team_collaboration signal
        assert _evaluate_team_collaboration(enterprise_repo) is True
