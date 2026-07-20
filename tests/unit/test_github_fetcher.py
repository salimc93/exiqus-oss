"""
Tests for GitHub data fetcher functionality.

This module tests the GitHub API integration, data extraction,
and conversion to internal data models.
"""

from datetime import datetime, timezone
from typing import Generator
from unittest.mock import Mock, PropertyMock, patch

import pytest
from github.GithubException import UnknownObjectException

from github_analyzer.data.github_fetcher import GitHubFetcher
from github_analyzer.data.models import CommitInfo, FileInfo, RepositoryData


class TestGitHubFetcher:
    """Test GitHub API data fetcher."""

    @pytest.fixture
    def mock_github_client(self) -> Generator[Mock, None, None]:
        """Create mock GitHub client."""
        with patch("github_analyzer.data.github_fetcher.Github") as mock_github:
            with patch("github_analyzer.data.github_fetcher.get_config") as mock_config:
                # Mock config
                mock_config_obj = Mock()
                mock_config_obj.github_token = "test_token"
                mock_config.return_value = mock_config_obj

                mock_client = Mock()
                mock_github.return_value = mock_client

                # Mock rate limit. PyGithub 2.x returns a RateLimitOverview
                # whose per-resource limits live under .resources.
                mock_rate_limit = Mock()
                mock_rate_limit.resources.core.limit = 5000
                mock_rate_limit.resources.core.remaining = 4000
                mock_rate_limit.resources.core.reset = Mock()
                mock_rate_limit.resources.core.reset.timestamp.return_value = 1234567890
                mock_client.get_rate_limit.return_value = mock_rate_limit

                yield mock_client

    @pytest.fixture
    def mock_repository(self) -> Mock:
        """Create mock repository object."""
        repo = Mock()
        repo.full_name = "test-user/test-repo"
        repo.name = "test-repo"
        repo.owner.login = "test-user"
        repo.description = "A test repository"
        repo.created_at = datetime(2023, 1, 1, tzinfo=timezone.utc)
        repo.updated_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        repo.pushed_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        repo.default_branch = "main"
        repo.size = 1024
        repo.stargazers_count = 42
        repo.forks_count = 7
        repo.watchers_count = 10
        repo.open_issues_count = 3
        repo.private = False
        repo.fork = False
        repo.archived = False
        repo.disabled = False

        # Mock languages
        repo.get_languages.return_value = {"Python": 12345, "JavaScript": 5678}

        # Mock topics
        repo.get_topics.return_value = ["python", "api", "testing"]

        # Mock license
        repo.license = Mock()
        repo.license.name = "MIT License"

        return repo

    @pytest.fixture
    def mock_commits(self) -> list[Mock]:
        """Create mock commit data."""
        commits = []
        for i in range(3):
            commit = Mock()
            commit.sha = f"abc123{i}"
            commit.commit.message = f"Test commit {i}"
            commit.commit.author.name = "Test Author"
            commit.commit.author.email = "test@example.com"
            commit.commit.author.date = datetime(2024, 1, i + 1, tzinfo=timezone.utc)
            commit.stats.additions = 10 + i
            commit.stats.deletions = 2 + i
            commit.files = [Mock(), Mock()]  # 2 files changed
            commits.append(commit)
        return commits

    @pytest.fixture
    def mock_file_contents(self) -> list[Mock]:
        """Create mock file contents."""
        contents = []

        # Mock README file
        readme = Mock()
        readme.path = "README.md"
        readme.name = "README.md"
        readme.type = "file"
        readme.size = 1024
        contents.append(readme)

        # Mock Python file
        py_file = Mock()
        py_file.path = "main.py"
        py_file.name = "main.py"
        py_file.type = "file"
        py_file.size = 2048
        contents.append(py_file)

        # Mock test directory
        test_dir = Mock()
        test_dir.path = "tests"
        test_dir.name = "tests"
        test_dir.type = "dir"
        test_dir.size = 0
        contents.append(test_dir)

        return contents

    def test_init_with_token(self, mock_github_client):
        """Test GitHubFetcher initialization with token."""
        fetcher = GitHubFetcher("test_token")
        assert fetcher.token == "test_token"
        assert fetcher.client is not None

    def test_init_without_token_raises_error(self):
        """Test that missing token raises ValueError."""
        with patch("github_analyzer.data.github_fetcher.get_config") as mock_config:
            mock_config.return_value.github_token = None
            with pytest.raises(ValueError, match="GitHub token is required"):
                GitHubFetcher()

    def test_check_rate_limit(self, mock_github_client):
        """Test rate limit checking."""
        fetcher = GitHubFetcher("test_token")
        rate_info = fetcher.check_rate_limit()

        assert rate_info["limit"] == 5000
        assert rate_info["remaining"] == 4000
        assert "reset_time" in rate_info

    def test_check_rate_limit_error_handling(self, mock_github_client):
        """Test rate limit error handling."""
        mock_github_client.get_rate_limit.side_effect = Exception("API Error")

        fetcher = GitHubFetcher("test_token")
        rate_info = fetcher.check_rate_limit()

        assert rate_info["limit"] == 0
        assert rate_info["remaining"] == 0
        assert rate_info["reset_time"] == 0

    def test_fetch_repository_data_invalid_url(self, mock_github_client):
        """Test fetch with invalid URL."""
        fetcher = GitHubFetcher("test_token")

        with pytest.raises(ValueError, match="Invalid GitHub repository URL"):
            fetcher.fetch_repository_data("invalid-url")

    def test_fetch_repository_data_not_found(self, mock_github_client):
        """Test fetch with non-existent repository."""
        mock_github_client.get_repo.side_effect = UnknownObjectException(
            404, "Not Found", {}
        )

        fetcher = GitHubFetcher("test_token")

        with pytest.raises(ValueError, match="Repository not found"):
            fetcher.fetch_repository_data("https://github.com/user/nonexistent")

    def test_fetch_repository_data_success(
        self, mock_github_client, mock_repository, mock_commits, mock_file_contents
    ):
        """Test successful repository data fetching."""
        # Setup mocks
        mock_github_client.get_repo.return_value = mock_repository
        mock_repository.get_commits.return_value = mock_commits

        # Mock README content
        readme_content = Mock()
        readme_content.encoding = "base64"
        readme_content.content = (
            "VGVzdCBSRUFETUUgY29udGVudA=="  # "Test README content" in base64
        )

        def mock_get_contents(path):
            if path == "README.md":
                return readme_content
            elif path == "":
                return mock_file_contents
            else:
                raise Exception("Not found")

        mock_repository.get_contents.side_effect = mock_get_contents

        fetcher = GitHubFetcher("test_token")
        result = fetcher.fetch_repository_data("https://github.com/test-user/test-repo")

        # Verify result
        assert isinstance(result, RepositoryData)
        assert result.full_name == "test-user/test-repo"
        assert result.name == "test-repo"
        assert result.owner == "test-user"
        assert result.description == "A test repository"
        assert result.stars == 42
        assert result.forks == 7
        assert len(result.recent_commits) == 3
        assert len(result.file_structure) == 3
        assert result.readme_content is not None

    def test_extract_basic_info(self, mock_github_client, mock_repository):
        """Test basic repository info extraction."""
        fetcher = GitHubFetcher("test_token")

        # Test with file checking mocks
        with patch.object(fetcher, "_check_has_file") as mock_check_file:
            with patch.object(fetcher, "_check_has_tests") as mock_check_tests:
                with patch.object(fetcher, "_check_has_ci_config") as mock_check_ci:
                    mock_check_file.return_value = True
                    mock_check_tests.return_value = True
                    mock_check_ci.return_value = False

                    basic_info = fetcher._extract_basic_info(
                        mock_repository, "https://github.com/test-user/test-repo"
                    )

                    assert basic_info["full_name"] == "test-user/test-repo"
                    assert basic_info["owner"] == "test-user"
                    assert basic_info["description"] == "A test repository"
                    assert basic_info["has_readme"] is True
                    assert basic_info["has_tests"] is True
                    assert basic_info["has_ci_config"] is False

    def test_extract_recent_commits(self, mock_github_client, mock_commits):
        """Test commit extraction."""
        mock_repository = Mock()
        mock_repository.get_commits.return_value = mock_commits

        fetcher = GitHubFetcher("test_token")
        commits = fetcher._extract_recent_commits(mock_repository)

        assert len(commits) == 3
        assert all(isinstance(commit, CommitInfo) for commit in commits)
        assert commits[0].message == "Test commit 0"
        assert commits[0].author_name == "Test Author"
        assert commits[0].additions == 10

    def test_extract_file_structure(self, mock_github_client, mock_file_contents):
        """Test file structure extraction."""
        mock_repository = Mock()

        def mock_get_contents(path):
            if path == "":
                return mock_file_contents
            else:
                raise Exception("Not found")

        mock_repository.get_contents.side_effect = mock_get_contents

        fetcher = GitHubFetcher("test_token")
        files = fetcher._extract_file_structure(mock_repository)

        assert len(files) == 3
        assert all(isinstance(file_info, FileInfo) for file_info in files)

        # Check specific files
        readme_file = next(f for f in files if f.name == "README.md")
        assert readme_file.is_documentation is True
        assert readme_file.type == "file"

        test_dir = next(f for f in files if f.name == "tests")
        assert test_dir.type == "dir"

    def test_extract_readme_content(self, mock_github_client):
        """Test README content extraction."""
        mock_repository = Mock()

        # Mock README content
        readme_content = Mock()
        readme_content.encoding = "base64"
        readme_content.content = (
            "VGVzdCBSRUFETUUgY29udGVudA=="  # "Test README content" in base64
        )

        mock_repository.get_contents.side_effect = lambda name: (
            readme_content if name == "README.md" else Exception("Not found")
        )

        fetcher = GitHubFetcher("test_token")
        content = fetcher._extract_readme_content(mock_repository)

        assert content == "Test README content"

    def test_extract_readme_content_not_found(self, mock_github_client):
        """Test README extraction when not found."""
        mock_repository = Mock()
        mock_repository.get_contents.side_effect = Exception("Not found")

        fetcher = GitHubFetcher("test_token")
        content = fetcher._extract_readme_content(mock_repository)

        assert content is None

    def test_calculate_metrics(self, mock_github_client):
        """Test metrics calculation."""
        mock_repository = Mock()

        # Create proper commit data with real datetime objects
        commits = [
            CommitInfo(
                sha="abc123",
                message="Test commit",
                author_name="Test Author",
                author_email="test@example.com",
                date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                additions=10,
                deletions=2,
                files_changed=2,
            ),
            CommitInfo(
                sha="def456",
                message="Another commit",
                author_name="Test Author",
                author_email="test@example.com",
                date=datetime(2024, 1, 2, tzinfo=timezone.utc),
                additions=5,
                deletions=1,
                files_changed=1,
            ),
        ]

        # Create test files
        files = [
            FileInfo("main.py", "main.py", 1000, "file", "py"),
            FileInfo("test_main.py", "test_main.py", 500, "file", "py", is_test=True),
            FileInfo(
                "README.md", "README.md", 200, "file", "md", is_documentation=True
            ),
        ]

        fetcher = GitHubFetcher("test_token")
        metrics = fetcher._calculate_metrics(mock_repository, commits, files)

        assert metrics.total_commits == 2
        assert metrics.unique_contributors == 1  # All commits from same author
        assert metrics.test_coverage_estimate > 0
        assert "documentation files" in metrics.documentation_presence
        assert metrics.commit_frequency >= 0

    def test_check_has_file_found(self, mock_github_client):
        """Test file existence checking when file exists."""
        mock_repository = Mock()
        mock_repository.get_contents.return_value = Mock()  # File exists

        fetcher = GitHubFetcher("test_token")
        result = fetcher._check_has_file(mock_repository, ["README.md"])

        assert result is True

    def test_check_has_file_not_found(self, mock_github_client):
        """Test file existence checking when file doesn't exist."""
        mock_repository = Mock()
        mock_repository.get_contents.side_effect = Exception("Not found")

        fetcher = GitHubFetcher("test_token")
        result = fetcher._check_has_file(mock_repository, ["README.md"])

        assert result is False

    def test_is_config_file(self, mock_github_client):
        """Test configuration file detection."""
        fetcher = GitHubFetcher("test_token")

        assert fetcher._is_config_file("package.json") is True
        assert fetcher._is_config_file("config.yml") is True
        assert fetcher._is_config_file(".env") is True
        assert fetcher._is_config_file("main.py") is False


class TestRepositoryDataModel:
    """Test RepositoryData model functionality."""

    def test_repository_data_creation(self):
        """Test creating RepositoryData object."""
        from github_analyzer.data.models import RepositoryMetrics

        metrics = RepositoryMetrics(
            total_commits=10,
            unique_contributors=2,
            lines_of_code=1000,
            test_coverage_estimate=0.8,
            documentation_presence="3 documentation files in 10 total files",
            days_since_last_commit=5,
            commit_frequency=2.0,
            avg_commit_size=50.0,
        )

        repo_data = RepositoryData(
            url="https://github.com/user/repo",
            full_name="user/repo",
            name="repo",
            owner="user",
            description="Test repository",
            created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            pushed_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            default_branch="main",
            size=1024,
            languages={"Python": 1000},
            topics=["python"],
            license_name="MIT",
            stars=10,
            forks=2,
            watchers=5,
            open_issues=1,
            has_readme=True,
            has_license=True,
            has_contributing=False,
            has_tests=True,
            has_ci_config=True,
            recent_commits=[],
            file_structure=[],
            readme_content="Test README",
            metrics=metrics,
            fetched_at=datetime.now(timezone.utc),
            is_private=False,
            is_fork=False,
            is_archived=False,
            is_disabled=False,
        )

        assert repo_data.full_name == "user/repo"
        assert repo_data.primary_language == "Python"
        assert repo_data.is_active is True  # Recent activity

    def test_repository_data_validation_error(self):
        """Test RepositoryData validation."""
        from github_analyzer.data.models import RepositoryMetrics

        metrics = RepositoryMetrics(
            total_commits=0,
            unique_contributors=0,
            lines_of_code=None,
            test_coverage_estimate=0.0,
            documentation_presence="0 documentation files found",
            days_since_last_commit=999,
            commit_frequency=0.0,
            avg_commit_size=0.0,
        )

        # Missing required field should raise ValueError
        with pytest.raises(
            ValueError, match="Repository URL and full name are required"
        ):
            RepositoryData(
                url="",  # Empty URL
                full_name="user/repo",
                name="repo",
                owner="user",
                description=None,
                created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
                updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
                pushed_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
                default_branch="main",
                size=0,
                languages={},
                topics=[],
                license_name=None,
                stars=0,
                forks=0,
                watchers=0,
                open_issues=0,
                has_readme=False,
                has_license=False,
                has_contributing=False,
                has_tests=False,
                has_ci_config=False,
                recent_commits=[],
                file_structure=[],
                readme_content=None,
                metrics=metrics,
                fetched_at=datetime.now(timezone.utc),
                is_private=False,
                is_fork=False,
                is_archived=False,
                is_disabled=False,
            )

    def test_language_percentages(self):
        """Test language percentage calculation."""
        from github_analyzer.data.models import RepositoryMetrics

        metrics = RepositoryMetrics(
            total_commits=1,
            unique_contributors=1,
            lines_of_code=100,
            test_coverage_estimate=0.0,
            documentation_presence="0 documentation files found",
            days_since_last_commit=1,
            commit_frequency=1.0,
            avg_commit_size=10.0,
        )

        repo_data = RepositoryData(
            url="https://github.com/user/repo",
            full_name="user/repo",
            name="repo",
            owner="user",
            description="Test",
            created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            pushed_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            default_branch="main",
            size=100,
            languages={"Python": 800, "JavaScript": 200},
            topics=[],
            license_name=None,
            stars=0,
            forks=0,
            watchers=0,
            open_issues=0,
            has_readme=False,
            has_license=False,
            has_contributing=False,
            has_tests=False,
            has_ci_config=False,
            recent_commits=[],
            file_structure=[],
            readme_content=None,
            metrics=metrics,
            fetched_at=datetime.now(timezone.utc),
            is_private=False,
            is_fork=False,
            is_archived=False,
            is_disabled=False,
        )

        percentages = repo_data.language_percentages
        assert percentages["Python"] == 80.0
        assert percentages["JavaScript"] == 20.0


class TestGitHubFetcherEdgeCases:
    """Test edge cases and error scenarios for GitHub Fetcher."""

    @pytest.fixture
    def mock_github_client(self):
        """Create mock GitHub client for edge case testing."""
        with patch("github_analyzer.data.github_fetcher.Github") as mock_github:
            with patch("github_analyzer.data.github_fetcher.get_config") as mock_config:
                mock_config_obj = Mock()
                mock_config_obj.github_token = "test_token"
                mock_config.return_value = mock_config_obj

                mock_client = Mock()
                mock_github.return_value = mock_client

                # Mock rate limit. PyGithub 2.x returns a RateLimitOverview
                # whose per-resource limits live under .resources.
                mock_rate_limit = Mock()
                mock_rate_limit.resources.core.limit = 5000
                mock_rate_limit.resources.core.remaining = 4000
                mock_rate_limit.resources.core.reset = Mock()
                mock_rate_limit.resources.core.reset.timestamp.return_value = 1234567890
                mock_client.get_rate_limit.return_value = mock_rate_limit

                yield mock_client

    def test_low_rate_limit_warning(self, mock_github_client):
        """Test rate limit warning when approaching limit."""
        # Set up low remaining rate limit
        mock_rate_limit = Mock()
        mock_rate_limit.core.limit = 5000
        mock_rate_limit.core.remaining = 5  # Very low
        mock_rate_limit.core.reset = Mock()
        mock_rate_limit.core.reset.timestamp.return_value = 1234567890
        mock_github_client.get_rate_limit.return_value = mock_rate_limit

        # Mock repository
        mock_repo = Mock()
        mock_repo.full_name = "test/repo"
        mock_repo.name = "repo"
        mock_repo.owner.login = "test"
        mock_repo.description = "Test repo"
        mock_repo.created_at = datetime(2023, 1, 1, tzinfo=timezone.utc)
        mock_repo.updated_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_repo.pushed_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_repo.default_branch = "main"
        mock_repo.size = 100
        mock_repo.stargazers_count = 1
        mock_repo.forks_count = 0
        mock_repo.watchers_count = 1
        mock_repo.open_issues_count = 0
        mock_repo.private = False
        mock_repo.fork = False
        mock_repo.archived = False
        mock_repo.disabled = False

        # Mock required methods
        mock_repo.get_languages.return_value = {"Python": 1000}
        mock_repo.get_topics.return_value = []
        mock_repo.license = None
        mock_repo.get_commits.return_value = []
        mock_repo.get_contents.side_effect = Exception("Not found")

        mock_github_client.get_repo.return_value = mock_repo

        fetcher = GitHubFetcher("test_token")

        # This should trigger the low rate limit warning
        with patch("github_analyzer.data.github_fetcher.logger") as mock_logger:
            fetcher.fetch_repository_data("https://github.com/test/repo")
            mock_logger.warning.assert_called()

    def test_extract_basic_info_language_error(self, mock_github_client):
        """Test language extraction error handling."""
        mock_repo = Mock()
        mock_repo.full_name = "test/repo"
        mock_repo.name = "repo"
        mock_repo.owner.login = "test"
        mock_repo.description = "Test repo"
        mock_repo.created_at = datetime(2023, 1, 1, tzinfo=timezone.utc)
        mock_repo.updated_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_repo.pushed_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_repo.default_branch = "main"
        mock_repo.size = 100
        mock_repo.stargazers_count = 1
        mock_repo.forks_count = 0
        mock_repo.watchers_count = 1
        mock_repo.open_issues_count = 0
        mock_repo.private = False
        mock_repo.fork = False
        mock_repo.archived = False
        mock_repo.disabled = False

        # Mock language error
        mock_repo.get_languages.side_effect = Exception("API Error")
        mock_repo.get_topics.return_value = []
        mock_repo.license = None

        fetcher = GitHubFetcher("test_token")

        with patch.object(fetcher, "_check_has_file") as mock_check_file:
            with patch.object(fetcher, "_check_has_tests") as mock_check_tests:
                with patch.object(fetcher, "_check_has_ci_config") as mock_check_ci:
                    mock_check_file.return_value = False
                    mock_check_tests.return_value = False
                    mock_check_ci.return_value = False

                    basic_info = fetcher._extract_basic_info(
                        mock_repo, "https://github.com/test/repo"
                    )

                    # Should fallback to empty dict for languages
                    assert basic_info["languages"] == {}

    def test_extract_basic_info_topics_error(self, mock_github_client):
        """Test topics extraction error handling."""
        mock_repo = Mock()
        mock_repo.full_name = "test/repo"
        mock_repo.name = "repo"
        mock_repo.owner.login = "test"
        mock_repo.description = "Test repo"
        mock_repo.created_at = datetime(2023, 1, 1, tzinfo=timezone.utc)
        mock_repo.updated_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_repo.pushed_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_repo.default_branch = "main"
        mock_repo.size = 100
        mock_repo.stargazers_count = 1
        mock_repo.forks_count = 0
        mock_repo.watchers_count = 1
        mock_repo.open_issues_count = 0
        mock_repo.private = False
        mock_repo.fork = False
        mock_repo.archived = False
        mock_repo.disabled = False

        # Mock topics error
        mock_repo.get_languages.return_value = {"Python": 1000}
        mock_repo.get_topics.side_effect = Exception("API Error")
        mock_repo.license = None

        fetcher = GitHubFetcher("test_token")

        with patch.object(fetcher, "_check_has_file") as mock_check_file:
            with patch.object(fetcher, "_check_has_tests") as mock_check_tests:
                with patch.object(fetcher, "_check_has_ci_config") as mock_check_ci:
                    mock_check_file.return_value = False
                    mock_check_tests.return_value = False
                    mock_check_ci.return_value = False

                    basic_info = fetcher._extract_basic_info(
                        mock_repo, "https://github.com/test/repo"
                    )

                    # Should fallback to empty list for topics
                    assert basic_info["topics"] == []

    def test_extract_basic_info_license_error(self, mock_github_client):
        """Test license extraction error handling."""
        mock_repo = Mock()
        mock_repo.full_name = "test/repo"
        mock_repo.name = "repo"
        mock_repo.owner.login = "test"
        mock_repo.description = "Test repo"
        mock_repo.created_at = datetime(2023, 1, 1, tzinfo=timezone.utc)
        mock_repo.updated_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_repo.pushed_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_repo.default_branch = "main"
        mock_repo.size = 100
        mock_repo.stargazers_count = 1
        mock_repo.forks_count = 0
        mock_repo.watchers_count = 1
        mock_repo.open_issues_count = 0
        mock_repo.private = False
        mock_repo.fork = False
        mock_repo.archived = False
        mock_repo.disabled = False

        # Mock license error
        mock_repo.get_languages.return_value = {"Python": 1000}
        mock_repo.get_topics.return_value = []

        # Create a mock license that raises an exception when name is accessed
        mock_license = Mock()
        type(mock_license).name = PropertyMock(side_effect=Exception("License error"))
        mock_repo.license = mock_license

        fetcher = GitHubFetcher("test_token")

        with patch.object(fetcher, "_check_has_file") as mock_check_file:
            with patch.object(fetcher, "_check_has_tests") as mock_check_tests:
                with patch.object(fetcher, "_check_has_ci_config") as mock_check_ci:
                    mock_check_file.return_value = False
                    mock_check_tests.return_value = False
                    mock_check_ci.return_value = False

                    basic_info = fetcher._extract_basic_info(
                        mock_repo, "https://github.com/test/repo"
                    )

                    # Should fallback to None for license
                    assert basic_info["license_name"] is None

    def test_extract_recent_commits_error(self, mock_github_client):
        """Test commit extraction error handling."""
        mock_repo = Mock()
        mock_repo.get_commits.side_effect = Exception("Commits error")

        fetcher = GitHubFetcher("test_token")
        commits = fetcher._extract_recent_commits(mock_repo)

        # Should return empty list on error
        assert commits == []

    def test_extract_recent_commits_individual_error(self, mock_github_client):
        """Test individual commit extraction error."""
        # Create commits with one that fails
        good_commit = Mock()
        good_commit.sha = "abc123"
        good_commit.commit.message = "Good commit"
        good_commit.commit.author.name = "Author"
        good_commit.commit.author.email = "test@example.com"
        good_commit.commit.author.date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        good_commit.stats.additions = 10
        good_commit.stats.deletions = 2
        good_commit.files = [Mock(), Mock()]

        bad_commit = Mock()
        bad_commit.sha = "def456"
        # Make the commit object raise an error
        bad_commit.commit = Mock(side_effect=Exception("Commit error"))

        mock_repo = Mock()
        mock_repo.get_commits.return_value = [good_commit, bad_commit]

        fetcher = GitHubFetcher("test_token")
        commits = fetcher._extract_recent_commits(mock_repo)

        # Should return only the good commit
        assert len(commits) == 1
        assert commits[0].sha == "abc123"

    def test_extract_file_structure_error(self, mock_github_client):
        """Test file structure extraction error handling."""
        mock_repo = Mock()
        mock_repo.get_contents.side_effect = Exception("Contents error")

        fetcher = GitHubFetcher("test_token")
        files = fetcher._extract_file_structure(mock_repo)

        # Should return empty list on error
        assert files == []

    def test_extract_file_structure_individual_file_error(self, mock_github_client):
        """Test individual file processing error."""
        # Create good and bad file items
        good_file = Mock()
        good_file.type = "file"
        good_file.path = "good.py"
        good_file.name = "good.py"
        good_file.size = 100

        bad_file = Mock()
        bad_file.type = "file"
        bad_file.path = Mock(side_effect=Exception("Path error"))

        mock_repo = Mock()
        mock_repo.get_contents.return_value = [good_file, bad_file]

        fetcher = GitHubFetcher("test_token")
        files = fetcher._extract_file_structure(mock_repo)

        # Should return only the good file
        assert len(files) == 1
        assert files[0].name == "good.py"

    def test_extract_readme_content_decoded_content(self, mock_github_client):
        """Test README extraction with decoded_content."""
        mock_repo = Mock()

        # Mock README with decoded_content instead of base64
        readme_content = Mock()
        readme_content.encoding = "utf-8"
        readme_content.content = None
        readme_content.decoded_content = b"Test README content"

        mock_repo.get_contents.side_effect = lambda name: (
            readme_content if name == "README.md" else Exception("Not found")
        )

        fetcher = GitHubFetcher("test_token")
        content = fetcher._extract_readme_content(mock_repo)

        assert content == "Test README content"

    def test_extract_readme_content_list_response(self, mock_github_client):
        """Test README extraction when get_contents returns a list."""
        mock_repo = Mock()

        # Mock get_contents returning a list (directory)
        mock_repo.get_contents.return_value = [Mock(), Mock()]

        fetcher = GitHubFetcher("test_token")
        content = fetcher._extract_readme_content(mock_repo)

        assert content is None

    def test_calculate_metrics_no_commits(self, mock_github_client):
        """Test metrics calculation with no commits."""
        mock_repo = Mock()
        commits = []
        files = [
            FileInfo("main.py", "main.py", 1000, "file", "py"),
        ]

        fetcher = GitHubFetcher("test_token")
        metrics = fetcher._calculate_metrics(mock_repo, commits, files)

        assert metrics.total_commits == 0
        assert metrics.unique_contributors == 0
        assert metrics.days_since_last_commit == 999
        assert metrics.commit_frequency == 0.0
        assert metrics.avg_commit_size == 0.0

    def test_calculate_metrics_no_stats(self, mock_github_client):
        """Test metrics calculation with commits that have no stats."""
        mock_repo = Mock()

        # Create commits without stats
        commits = [
            CommitInfo(
                sha="abc123",
                message="Test commit",
                author_name="Test Author",
                author_email="test@example.com",
                date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                additions=None,  # No stats
                deletions=None,
                files_changed=None,
            )
        ]
        files = [FileInfo("main.py", "main.py", 1000, "file", "py")]

        fetcher = GitHubFetcher("test_token")
        metrics = fetcher._calculate_metrics(mock_repo, commits, files)

        assert metrics.total_commits == 1
        assert metrics.avg_commit_size == 0.0  # Should handle None stats

    def test_calculate_metrics_single_commit(self, mock_github_client):
        """Test metrics calculation with single commit."""
        mock_repo = Mock()

        commits = [
            CommitInfo(
                sha="abc123",
                message="Test commit",
                author_name="Test Author",
                author_email="test@example.com",
                date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                additions=10,
                deletions=2,
                files_changed=2,
            )
        ]
        files = [FileInfo("main.py", "main.py", 1000, "file", "py")]

        fetcher = GitHubFetcher("test_token")
        metrics = fetcher._calculate_metrics(mock_repo, commits, files)

        assert metrics.total_commits == 1
        assert metrics.commit_frequency == 0.0  # Single commit has no frequency

    def test_calculate_metrics_error(self, mock_github_client):
        """Test metrics calculation error handling."""
        mock_repo = Mock()

        # Create invalid data that will cause an error
        commits = [Mock()]  # Invalid commit object
        files = [Mock()]  # Invalid file object

        fetcher = GitHubFetcher("test_token")

        # Should return default metrics on error
        metrics = fetcher._calculate_metrics(mock_repo, commits, files)

        assert metrics.total_commits == 0
        assert metrics.unique_contributors == 0
        assert metrics.lines_of_code is None
        assert metrics.test_coverage_estimate == 0.0

    def test_github_rate_limit_exceeded(self, mock_github_client):
        """Test handling of GitHub API rate limit exceeded exception."""
        from github.GithubException import RateLimitExceededException

        # Mock rate limit exception
        mock_github_client.get_repo.side_effect = RateLimitExceededException(
            status=403, data={"message": "API rate limit exceeded"}, headers={}
        )

        # Mock rate limit info for the error message
        mock_rate_limit = Mock()
        mock_rate_limit.core.limit = 5000
        mock_rate_limit.core.remaining = 0
        mock_rate_limit.core.reset = Mock()
        mock_rate_limit.core.reset.timestamp = Mock(return_value=1234567890)
        mock_github_client.get_rate_limit.return_value = mock_rate_limit

        fetcher = GitHubFetcher("test_token")

        # Should raise ValueError with user-friendly message
        with pytest.raises(ValueError) as exc_info:
            fetcher.fetch_repository_data("https://github.com/test/repo")

        # Check user-friendly message
        error_msg = str(exc_info.value)
        assert "experiencing high demand" in error_msg
        assert "try again in a few minutes" in error_msg
        assert "contact support" in error_msg

        # Should NOT expose internal details
        assert "GitHub token" not in error_msg
        assert "Enterprise" not in error_msg
        assert "15,000" not in error_msg
