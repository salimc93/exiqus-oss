# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
GitHub API data fetcher for repository analysis.

This module handles GitHub API integration, data extraction, and conversion
to our internal data models for analysis processing.
"""

import base64
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from github import Auth, Github
from github.GithubException import (
    RateLimitExceededException,
    UnknownObjectException,
)
from github.Repository import Repository

from ..utils.config import get_config
from ..utils.helpers import (
    calculate_days_between,
    extract_repo_info,
    is_documentation_file,
    is_test_file,
    validate_github_url,
)
from ..utils.logging import get_logger
from .models import CommitInfo, FileInfo, RepositoryData, RepositoryMetrics

logger = get_logger(__name__)


class GitHubFetcher:
    """GitHub API client for repository data extraction."""

    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize GitHub API client.

        Args:
            github_token: GitHub personal access token. If None, uses config.
        """
        self.config = get_config()
        self.token = github_token or self.config.github_token

        if not self.token:
            raise ValueError("GitHub token is required")

        self.client = Github(auth=Auth.Token(self.token))
        self._rate_limit_checked = False

    def check_rate_limit(self) -> Dict[str, int]:
        """
        Check GitHub API rate limit status.

        Returns:
            Dictionary with rate limit information
        """
        try:
            rate_limit = self.client.get_rate_limit()
            return {
                "limit": rate_limit.core.limit,
                "remaining": rate_limit.core.remaining,
                "reset_time": int(rate_limit.core.reset.timestamp()),
            }
        except Exception as e:
            logger.error(f"Failed to check rate limit: {e}")
            return {"limit": 0, "remaining": 0, "reset_time": 0}

    def check_repository_size(self, repo_url: str) -> Dict[str, int]:
        """
        Check repository size and file count before full analysis.

        Args:
            repo_url: GitHub repository URL

        Returns:
            Dictionary with size_kb and file_count

        Raises:
            ValueError: If URL is invalid or repository not accessible
        """
        # Validate URL and extract repo info
        if not validate_github_url(repo_url):
            raise ValueError(f"Invalid GitHub repository URL: {repo_url}")

        repo_info = extract_repo_info(repo_url)
        if not repo_info:
            raise ValueError(f"Could not extract repository info from URL: {repo_url}")

        try:
            # Get repository object
            repo = self.client.get_repo(repo_info["full_name"])

            # Get file count (approximate - using tree API)
            try:
                default_branch = repo.default_branch
                tree = repo.get_git_tree(sha=default_branch, recursive=True)
                file_count = len([item for item in tree.tree if item.type == "blob"])
            except Exception as e:
                logger.warning(f"Could not get exact file count: {e}")
                file_count = -1  # Indicate unknown

            return {"size_kb": repo.size, "file_count": file_count}

        except UnknownObjectException:
            raise ValueError(
                f"Repository not found or not accessible: {repo_info['full_name']}"
            )
        except Exception as e:
            logger.error(f"Failed to check repository size: {e}")
            raise ValueError(f"Failed to check repository size: {e}")

    def fetch_repository_data(self, repo_url: str) -> RepositoryData:
        """
        Fetch comprehensive repository data from GitHub.

        Args:
            repo_url: GitHub repository URL

        Returns:
            RepositoryData object with all extracted information

        Raises:
            ValueError: If URL is invalid
            GithubException: If repository access fails
        """
        # Validate URL and extract repo info
        if not validate_github_url(repo_url):
            raise ValueError(f"Invalid GitHub repository URL: {repo_url}")

        repo_info = extract_repo_info(repo_url)
        if not repo_info:
            raise ValueError(f"Could not extract repository info from URL: {repo_url}")

        logger.info(f"Fetching data for repository: {repo_info['full_name']}")

        try:
            # Check rate limit before making requests
            if not self._rate_limit_checked:
                rate_info = self.check_rate_limit()
                if rate_info["remaining"] < 10:
                    logger.warning(
                        f"Low GitHub API rate limit: {rate_info['remaining']} "
                        "requests remaining"
                    )
                self._rate_limit_checked = True

            # Get repository object
            repo = self.client.get_repo(repo_info["full_name"])

            # Extract file structure first (1 API call)
            file_structure = self._extract_file_structure(repo)

            # Extract basic repository information (now with file structure)
            basic_info = self._extract_basic_info(repo, repo_url, file_structure)

            # Extract detailed information
            commits = self._extract_recent_commits(repo)
            readme_content = self._extract_readme_content(repo)

            # Extract key files for deep insights (5-10 strategic API calls)
            key_files_content = self._extract_key_files_content(repo, file_structure)

            # Calculate metrics
            metrics = self._calculate_metrics(repo, commits, file_structure)

            # Create RepositoryData object
            repository_data = RepositoryData(
                **basic_info,
                recent_commits=commits,
                file_structure=file_structure,
                readme_content=readme_content,
                key_files_content=key_files_content,
                metrics=metrics,
                fetched_at=datetime.now(timezone.utc),
            )

            logger.info(f"Successfully fetched data for {repo_info['full_name']}")
            return repository_data

        except UnknownObjectException:
            error_msg = (
                f"Repository not found or not accessible: {repo_info['full_name']}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        except RateLimitExceededException:
            # Get rate limit info for internal logging
            rate_info = self.check_rate_limit()
            reset_time = datetime.fromtimestamp(rate_info["reset_time"])
            minutes_until_reset = max(
                0, int((reset_time - datetime.now()).total_seconds() / 60)
            )

            logger.error(
                "GitHub API rate limit exceeded. "
                f"Limit: {rate_info['limit']}/hour, "
                f"Remaining: {rate_info['remaining']}, "
                f"Resets in: {minutes_until_reset} minutes"
            )

            # User-friendly message without exposing internal details
            raise ValueError(
                "We're experiencing high demand. Please try again in a few minutes. "
                "If this persists, please contact support."
            )
        except Exception as e:
            logger.error(f"Failed to fetch repository data: {e}")
            raise ValueError(f"Failed to fetch repository data: {e}")

    def _extract_basic_info(
        self,
        repo: Repository,
        repo_url: str,
        file_structure: Optional[List[FileInfo]] = None,
    ) -> Dict[str, Any]:
        """Extract basic repository information."""
        try:
            # Get languages (with fallback)
            try:
                languages = repo.get_languages()
            except Exception:
                languages = {}

            # Get topics (with fallback)
            try:
                topics = repo.get_topics()
            except Exception:
                topics = []

            # Get license info (with fallback)
            license_name = None
            try:
                if hasattr(repo, "license") and repo.license:
                    license_name = repo.license.name
            except (AttributeError, Exception) as e:
                logger.debug(f"License info not available: {e}")
                pass

            return {
                "url": repo_url,
                "full_name": repo.full_name,
                "name": repo.name,
                "owner": repo.owner.login,
                "description": repo.description,
                "created_at": repo.created_at.replace(tzinfo=timezone.utc),
                "updated_at": repo.updated_at.replace(tzinfo=timezone.utc),
                "pushed_at": (
                    repo.pushed_at.replace(tzinfo=timezone.utc)
                    if repo.pushed_at
                    else repo.updated_at.replace(tzinfo=timezone.utc)
                ),
                "default_branch": repo.default_branch,
                "size": repo.size,
                "languages": languages,
                "topics": topics,
                "license_name": license_name,
                "stars": repo.stargazers_count,
                "forks": repo.forks_count,
                "watchers": repo.watchers_count,
                "open_issues": repo.open_issues_count,
                "has_readme": (
                    self._check_has_file_in_structure(
                        file_structure,
                        ["README.md", "README.rst", "README.txt", "readme.md"],
                    )
                    if file_structure
                    else self._check_has_file(
                        repo, ["README.md", "README.rst", "README.txt", "readme.md"]
                    )
                ),
                "has_license": (
                    self._check_has_file_in_structure(
                        file_structure,
                        [
                            "LICENSE",
                            "LICENSE.md",
                            "LICENSE.txt",
                            "license",
                            "license.md",
                        ],
                    )
                    if file_structure
                    else self._check_has_file(
                        repo,
                        [
                            "LICENSE",
                            "LICENSE.md",
                            "LICENSE.txt",
                            "license",
                            "license.md",
                        ],
                    )
                ),
                "has_contributing": (
                    self._check_has_file_in_structure(
                        file_structure,
                        ["CONTRIBUTING.md", "CONTRIBUTING.rst", "contributing.md"],
                    )
                    if file_structure
                    else self._check_has_file(
                        repo, ["CONTRIBUTING.md", "CONTRIBUTING.rst", "contributing.md"]
                    )
                ),
                "has_tests": (
                    self._check_has_tests_in_structure(file_structure)
                    if file_structure
                    else self._check_has_tests(repo)
                ),
                "has_ci_config": (
                    self._check_has_ci_config_in_structure(file_structure)
                    if file_structure
                    else self._check_has_ci_config(repo)
                ),
                "is_private": repo.private,
                "is_fork": repo.fork,
                "is_archived": repo.archived,
                "is_disabled": repo.disabled if hasattr(repo, "disabled") else False,
            }
        except Exception as e:
            logger.error(f"Failed to extract basic repository info: {e}")
            raise

    def _extract_recent_commits(
        self, repo: Repository, limit: int = 30
    ) -> List[CommitInfo]:
        """Extract recent commit information."""
        commits = []
        try:
            commit_list = repo.get_commits()

            for i, commit in enumerate(commit_list):
                if i >= limit:  # Limit to recent commits
                    break

                try:
                    # Get GitHub username from commit author (may be None for unlinked commits)
                    author_login = None
                    if commit.author:
                        author_login = commit.author.login

                    commit_info = CommitInfo(
                        sha=commit.sha,
                        message=commit.commit.message,
                        author_name=commit.commit.author.name,
                        author_email=commit.commit.author.email,
                        date=commit.commit.author.date.replace(tzinfo=timezone.utc),
                        author_login=author_login,
                        additions=commit.stats.additions if commit.stats else None,
                        deletions=commit.stats.deletions if commit.stats else None,
                        files_changed=len(list(commit.files)) if commit.files else None,
                    )
                    commits.append(commit_info)
                except Exception as e:
                    logger.warning(
                        f"Failed to extract commit info for {commit.sha}: {e}"
                    )
                    continue

        except Exception as e:
            logger.warning(f"Failed to extract commit history: {e}")

        return commits

    def _extract_file_structure(
        self, repo: Repository, max_files: int = 1000
    ) -> List[FileInfo]:
        """Extract repository file structure using Git Tree API (1 API call).

        This provides the same data as recursive get_contents but much more efficiently.
        We get ALL files in the repo, which gives us accurate metrics for:
        - Test coverage ratio
        - Architecture patterns
        - Technology distribution
        """
        files = []

        try:
            # Get entire tree in ONE API call - this is the key optimization
            default_branch = repo.default_branch
            tree = repo.get_git_tree(sha=default_branch, recursive=True)

            # Check if this might be a monorepo
            total_entries = len(tree.tree)
            if total_entries > max_files * 2:  # Likely a monorepo
                logger.info(
                    f"Detected potential monorepo with {total_entries} entries. Using smart sampling."
                )
                files = self._sample_monorepo_tree(tree.tree, max_files)
            else:
                # Regular extraction for normal repos
                for i, entry in enumerate(tree.tree):
                    if i >= max_files:
                        break

                    # Extract path components for analysis
                    path_parts = entry.path.split("/")
                    name = path_parts[-1]

                    # Build FileInfo with all the same data we had before
                    if entry.type == "tree":
                        file_info = FileInfo(
                            path=entry.path, name=name, size=0, type="dir"
                        )
                    else:
                        extension = Path(name).suffix.lstrip(".")
                        file_info = FileInfo(
                            path=entry.path,
                            name=name,
                            size=(
                                int(entry.size)
                                if hasattr(entry, "size") and entry.size is not None
                                else 0
                            ),
                            type="file",
                            extension=extension if extension else None,
                            is_documentation=is_documentation_file(name),
                            is_test=is_test_file(name),
                            is_config=self._is_config_file(name),
                        )

                    files.append(file_info)

            logger.info(f"Extracted {len(files)} files using Git Tree API (1 API call)")

        except Exception as e:
            logger.warning(
                f"Failed to extract via tree API, falling back to limited scan: {e}"
            )
            # Fallback to limited directory scan if tree API fails
            files = self._extract_file_structure_fallback(repo, max_files=100)

        return files

    def _sample_monorepo_tree(
        self, tree_entries: List[Any], max_files: int = 1000
    ) -> List[FileInfo]:
        """Smart sampling for monorepos - get representative files across categories."""
        # Categorize all entries
        source_files = []
        test_files = []
        config_files = []
        doc_files = []
        directories = []

        for entry in tree_entries:
            if entry.type == "tree":
                directories.append(entry)
                continue

            path = entry.path
            name = path.split("/")[-1]

            if is_test_file(name) or "/test" in path or "/tests" in path:
                test_files.append(entry)
            elif is_documentation_file(name) or "/docs" in path:
                doc_files.append(entry)
            elif self._is_config_file(name) or name in [
                "package.json",
                "go.mod",
                "pom.xml",
            ]:
                config_files.append(entry)
            else:
                # Source files
                extension = Path(name).suffix.lstrip(".")
                if extension in {
                    "py",
                    "js",
                    "ts",
                    "go",
                    "java",
                    "cpp",
                    "c",
                    "rs",
                    "rb",
                }:
                    source_files.append(entry)

        # Calculate proportional sampling
        sample_proportions = {
            "source": 0.4,  # 40% source files
            "test": 0.3,  # 30% test files
            "config": 0.2,  # 20% config files
            "doc": 0.1,  # 10% documentation
        }

        # Calculate actual sample sizes
        source_sample_size = int(max_files * sample_proportions["source"])
        test_sample_size = int(max_files * sample_proportions["test"])
        config_sample_size = int(max_files * sample_proportions["config"])
        doc_sample_size = int(max_files * sample_proportions["doc"])

        # Smart selection: prioritize important files
        sampled_entries = []

        # For source files: prioritize main entry points and core modules
        important_patterns = [
            "main.",
            "index.",
            "app.",
            "server.",
            "api.",
            "core/",
            "pkg/",
            "src/",
        ]
        important_sources = [
            f for f in source_files if any(p in f.path for p in important_patterns)
        ]
        other_sources = [f for f in source_files if f not in important_sources]

        sampled_entries.extend(important_sources[: source_sample_size // 2])
        sampled_entries.extend(other_sources[: source_sample_size // 2])

        # For tests: get a good distribution
        sampled_entries.extend(test_files[:test_sample_size])

        # For configs: prioritize root configs
        root_configs = [f for f in config_files if "/" not in f.path]
        other_configs = [f for f in config_files if "/" in f.path]
        sampled_entries.extend(root_configs)
        sampled_entries.extend(
            other_configs[: max(0, config_sample_size - len(root_configs))]
        )

        # Documentation
        sampled_entries.extend(doc_files[:doc_sample_size])

        # Add all directories (they don't count against file limit)
        sampled_entries.extend(directories)

        # Convert to FileInfo objects
        files = []
        for entry in sampled_entries:
            path_parts = entry.path.split("/")
            name = path_parts[-1]

            if entry.type == "tree":
                file_info = FileInfo(path=entry.path, name=name, size=0, type="dir")
            else:
                extension = Path(name).suffix.lstrip(".")
                file_info = FileInfo(
                    path=entry.path,
                    name=name,
                    size=(
                        int(entry.size)
                        if hasattr(entry, "size") and entry.size is not None
                        else 0
                    ),
                    type="file",
                    extension=extension if extension else None,
                    is_documentation=is_documentation_file(name),
                    is_test=is_test_file(name),
                    is_config=self._is_config_file(name),
                )
            files.append(file_info)

        logger.info(
            f"Sampled {len(files)} entries from monorepo: "
            f"{len([f for f in files if f.type == 'file' and not f.is_test and not f.is_documentation and not f.is_config])} source, "
            f"{len([f for f in files if f.is_test])} test, "
            f"{len([f for f in files if f.is_config])} config, "
            f"{len([f for f in files if f.is_documentation])} doc files"
        )

        return files

    def _extract_file_structure_fallback(
        self, repo: Repository, max_files: int = 100
    ) -> List[FileInfo]:
        """Fallback file extraction using limited get_contents calls."""
        files = []
        try:
            # Just get root level files/dirs
            contents = repo.get_contents("")

            # Handle both list and single item returns
            content_list = contents if isinstance(contents, list) else [contents]
            for item in content_list[:max_files]:
                if item.type == "dir":
                    file_info = FileInfo(
                        path=item.path, name=item.name, size=0, type="dir"
                    )
                else:
                    extension = Path(item.name).suffix.lstrip(".")
                    file_info = FileInfo(
                        path=item.path,
                        name=item.name,
                        size=item.size,
                        type="file",
                        extension=extension if extension else None,
                        is_documentation=is_documentation_file(item.name),
                        is_test=is_test_file(item.name),
                        is_config=self._is_config_file(item.name),
                    )
                files.append(file_info)

        except Exception as e:
            logger.error(f"Fallback file extraction also failed: {e}")

        return files

    def _extract_key_files_content(
        self, repo: Repository, files: List[FileInfo]
    ) -> Dict[str, Any]:
        """Extract content from strategically selected files for deep insights.

        This method fetches 5-10 key files that provide maximum insight value:
        - Package manager files (dependencies, scripts)
        - CI/CD configurations (quality practices)
        - Test samples (testing approach)
        - Main entry points (code structure)

        Returns:
            Dictionary with categorized file contents for evidence extraction
        """
        key_files_content = {}
        api_calls_used = 0
        max_api_calls = 10

        # Priority 1: Package manager files (reveals tech stack, dependencies, scripts)
        package_files = [
            "package.json",
            "requirements.txt",
            "Cargo.toml",
            "go.mod",
            "pom.xml",
            "build.gradle",
            "Gemfile",
            "pyproject.toml",
        ]
        for filename in package_files:
            if api_calls_used >= max_api_calls:
                break
            matching = [f for f in files if f.name == filename and f.type == "file"]
            if matching:
                try:
                    content = repo.get_contents(matching[0].path)
                    if hasattr(content, "decoded_content"):
                        key_files_content["package_info"] = {
                            "filename": filename,
                            "content": content.decoded_content.decode("utf-8")[:5000],
                        }
                        api_calls_used += 1
                        break
                except Exception as e:
                    logger.debug(f"Failed to fetch {filename}: {e}")

        # Priority 2: CI/CD files (reveals quality practices)
        ci_files = [
            ".github/workflows/ci.yml",
            ".github/workflows/main.yml",
            ".gitlab-ci.yml",
            ".travis.yml",
            "Jenkinsfile",
            ".circleci/config.yml",
            "azure-pipelines.yml",
        ]
        for ci_file in ci_files:
            if api_calls_used >= max_api_calls:
                break
            matching = [f for f in files if f.path == ci_file]
            if matching:
                try:
                    content = repo.get_contents(matching[0].path)
                    if hasattr(content, "decoded_content"):
                        key_files_content["ci_config"] = {
                            "filename": ci_file,
                            "content": content.decoded_content.decode("utf-8")[:3000],
                        }
                        api_calls_used += 1
                        break
                except Exception as e:
                    logger.debug(f"Failed to fetch CI config {ci_file}: {e}")
                    continue

        # Priority 3: Linting/Quality configs (code standards)
        quality_configs = [
            ".eslintrc.json",
            ".eslintrc.js",
            "tsconfig.json",
            ".prettierrc",
            "tslint.json",
            ".rubocop.yml",
            "ruff.toml",
        ]
        for config_file in quality_configs:
            if api_calls_used >= max_api_calls:
                break
            matching = [f for f in files if f.name == config_file]
            if matching:
                try:
                    content = repo.get_contents(matching[0].path)
                    if hasattr(content, "decoded_content"):
                        key_files_content["quality_config"] = {
                            "filename": config_file,
                            "content": content.decoded_content.decode("utf-8")[:2000],
                        }
                        api_calls_used += 1
                        break
                except Exception as e:
                    logger.debug(f"Failed to fetch quality config {config_file}: {e}")
                    continue

        # Priority 4: Sample test file (testing approach)
        test_files = [
            f
            for f in files
            if f.is_test and f.extension in ["js", "ts", "py", "rb", "go"]
        ]
        if test_files and api_calls_used < max_api_calls:
            # Prefer integration/e2e tests over unit tests for insights
            priority_test = next(
                (f for f in test_files if "integration" in f.path or "e2e" in f.path),
                test_files[0],
            )
            try:
                content = repo.get_contents(priority_test.path)
                if hasattr(content, "decoded_content"):
                    key_files_content["sample_test"] = {
                        "path": priority_test.path,
                        "content": content.decoded_content.decode("utf-8")[:3000],
                    }
                    api_calls_used += 1
            except Exception as e:
                logger.debug(f"Failed to fetch test file {priority_test.path}: {e}")

        # Priority 5: Main entry point (architecture insights)
        entry_patterns = ["main.", "index.", "app.", "server.", "api.", "handler."]
        for pattern in entry_patterns:
            if api_calls_used >= max_api_calls:
                break
            entry_files = [
                f
                for f in files
                if pattern in f.name
                and f.type == "file"
                and f.extension in ["js", "ts", "py", "go", "rb", "java"]
            ]
            if entry_files:
                try:
                    content = repo.get_contents(entry_files[0].path)
                    if hasattr(content, "decoded_content"):
                        key_files_content["main_entry"] = {
                            "path": entry_files[0].path,
                            "content": content.decoded_content.decode("utf-8")[:3000],
                        }
                        api_calls_used += 1
                        break
                except Exception as e:
                    logger.debug(
                        f"Failed to fetch entry file {entry_files[0].path}: {e}"
                    )
                    continue

        logger.info(
            f"Fetched {len(key_files_content)} key files using {api_calls_used} API calls"
        )
        return key_files_content

    def _extract_readme_content(self, repo: Repository) -> Optional[str]:
        """Extract README content if available.

        README is crucial for assessing communication skills and documentation quality.
        We fetch the full content as it's one of the most valuable signals.
        """
        readme_files = [
            "README.md",
            "README.rst",
            "README.txt",
            "readme.md",
            "Readme.md",
        ]

        for readme_name in readme_files:
            try:
                content = repo.get_contents(readme_name)
                # Handle both single file and list responses
                if isinstance(content, list):
                    continue  # Skip directories

                if content.encoding == "base64" and content.content:
                    decoded_content = base64.b64decode(content.content).decode("utf-8")
                    return decoded_content[:5000]  # Limit to first 5000 characters
                else:
                    decoded_content = content.decoded_content.decode("utf-8")
                    return decoded_content[:5000]
            except (UnicodeDecodeError, ValueError, AttributeError, Exception) as e:
                logger.debug(f"Failed to access or decode README content: {e}")
                continue

        return None

    def _calculate_metrics(
        self, repo: Repository, commits: List[CommitInfo], files: List[FileInfo]
    ) -> RepositoryMetrics:
        """Calculate repository metrics."""
        try:
            # Basic metrics
            total_commits = len(commits)

            # Count unique contributors using GitHub usernames (not emails)
            # This prevents counting the same person multiple times due to different email addresses
            repo_owner = repo.owner.login.lower()
            contributor_logins = set()

            for commit in commits:
                # Use author_login if available (the actual GitHub username)
                if commit.author_login:
                    login = commit.author_login.lower()
                    # Filter out bots
                    if not login.endswith("[bot]"):
                        contributor_logins.add(login)
                else:
                    # If no GitHub login available, assume it's the repo owner
                    # (commits from local git without linked GitHub account)
                    contributor_logins.add(repo_owner)

            unique_contributors = len(contributor_logins)

            # File metrics
            code_files = [
                f
                for f in files
                if f.type == "file"
                and f.extension
                in {"py", "js", "ts", "java", "cpp", "c", "cs", "rb", "go", "rs", "php"}
            ]
            test_files = [f for f in files if f.is_test]
            doc_files = [f for f in files if f.is_documentation]

            # Estimates
            lines_of_code = (
                sum(f.size for f in code_files) // 50 if code_files else 0
            )  # Rough estimate
            test_coverage_estimate = min(
                len(test_files) / max(len(code_files), 1) * 0.5, 1.0
            )
            # Evidence-based documentation observation
            documentation_presence = (
                f"{len(doc_files)} documentation files in {len(files)} total files"
            )

            # Time-based metrics
            if commits:
                last_commit_date = max(commit.date for commit in commits)
                days_since_last_commit = calculate_days_between(last_commit_date)

                # Calculate commit frequency (commits per week)
                if len(commits) > 1:
                    first_commit = min(commit.date for commit in commits)
                    total_days = max(
                        calculate_days_between(first_commit, last_commit_date), 1
                    )
                    commit_frequency = (total_commits / total_days) * 7
                else:
                    commit_frequency = 0.0

                # Average commit size
                changes = [
                    c
                    for c in commits
                    if c.additions is not None and c.deletions is not None
                ]
                if changes:
                    avg_commit_size = sum(
                        (c.additions or 0) + (c.deletions or 0) for c in changes
                    ) / len(changes)
                else:
                    avg_commit_size = 0.0
            else:
                days_since_last_commit = 999
                commit_frequency = 0.0
                avg_commit_size = 0.0

            return RepositoryMetrics(
                total_commits=total_commits,
                unique_contributors=unique_contributors,
                lines_of_code=lines_of_code,
                test_coverage_estimate=test_coverage_estimate,
                documentation_presence=documentation_presence,
                days_since_last_commit=days_since_last_commit,
                commit_frequency=commit_frequency,
                avg_commit_size=avg_commit_size,
            )

        except Exception as e:
            logger.error(f"Failed to calculate metrics: {e}")
            # Return default metrics
            return RepositoryMetrics(
                total_commits=0,
                unique_contributors=0,
                lines_of_code=None,
                test_coverage_estimate=0.0,
                documentation_presence="0 documentation files found",
                days_since_last_commit=999,
                commit_frequency=0.0,
                avg_commit_size=0.0,
            )

    def _check_has_file_in_structure(
        self, file_structure: List[FileInfo], filenames: List[str]
    ) -> bool:
        """Check if any of the specified files exist in the file structure (no API calls)."""
        if not file_structure:
            return False

        file_names_in_structure = {
            f.name.lower() for f in file_structure if f.type == "file"
        }
        for filename in filenames:
            if filename.lower() in file_names_in_structure:
                return True
        return False

    def _check_has_tests_in_structure(self, file_structure: List[FileInfo]) -> bool:
        """Check if repository has test files or directories in the file structure (no API calls)."""
        if not file_structure:
            return False

        # Check for test directories
        test_dirs = {"tests", "test", "__tests__", "spec"}
        dir_names = {f.name.lower() for f in file_structure if f.type == "dir"}
        if test_dirs.intersection(dir_names):
            return True

        # Check for test config files
        test_configs = {"pytest.ini", "jest.config.js", "karma.conf.js"}
        file_names = {f.name.lower() for f in file_structure if f.type == "file"}
        if test_configs.intersection(file_names):
            return True

        # Check for test files
        return any(f.is_test for f in file_structure if f.type == "file")

    def _check_has_ci_config_in_structure(self, file_structure: List[FileInfo]) -> bool:
        """Check if repository has CI/CD configuration in the file structure (no API calls)."""
        if not file_structure:
            return False

        # Check for CI directories
        ci_paths = [f.path for f in file_structure]
        if any(".github/workflows" in path for path in ci_paths):
            return True

        # Check for CI config files
        ci_files = {
            ".gitlab-ci.yml",
            ".travis.yml",
            "azure-pipelines.yml",
            "jenkinsfile",
            ".circleci/config.yml",
        }
        file_names = {f.name.lower() for f in file_structure if f.type == "file"}
        return bool(ci_files.intersection(file_names))

    def _check_has_file(self, repo: Repository, filenames: List[str]) -> bool:
        """Check if repository has any of the specified files."""
        for filename in filenames:
            try:
                repo.get_contents(filename)
                return True
            except Exception as e:
                logger.debug(f"File {filename} not found: {e}")
                continue
        return False

    def _check_has_tests(self, repo: Repository) -> bool:
        """Check if repository has test files or directories."""
        test_indicators = [
            "tests/",
            "test/",
            "__tests__/",
            "spec/",
            "pytest.ini",
            "jest.config.js",
            "karma.conf.js",
        ]

        for indicator in test_indicators:
            try:
                repo.get_contents(indicator)
                return True
            except Exception as e:
                logger.debug(f"Test indicator {indicator} not found: {e}")
                continue
        return False

    def _check_has_ci_config(self, repo: Repository) -> bool:
        """Check if repository has CI/CD configuration."""
        ci_files = [
            ".github/workflows/",
            ".gitlab-ci.yml",
            ".travis.yml",
            "azure-pipelines.yml",
            "Jenkinsfile",
            ".circleci/config.yml",
        ]

        for ci_file in ci_files:
            try:
                repo.get_contents(ci_file)
                return True
            except Exception as e:
                logger.debug(f"CI file {ci_file} not found: {e}")
                continue
        return False

    def _is_config_file(self, filename: str) -> bool:
        """Check if file is a configuration file."""
        config_patterns = [
            r".*\.json$",
            r".*\.yml$",
            r".*\.yaml$",
            r".*\.toml$",
            r".*\.ini$",
            r".*\.cfg$",
            r".*config.*",
            r".*\.env.*",
        ]

        filename_lower = filename.lower()
        return any(re.match(pattern, filename_lower) for pattern in config_patterns)
