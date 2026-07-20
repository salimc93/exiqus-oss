# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Data models for GitHub repository analysis.

This module defines the data structures used throughout the analysis pipeline
for representing repository information, commit data, and analysis results.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class CommitInfo:
    """Information about a repository commit."""

    sha: str
    message: str
    author_name: str
    author_email: str
    date: datetime
    author_login: Optional[str] = None  # GitHub username, if available
    additions: Optional[int] = None
    deletions: Optional[int] = None
    files_changed: Optional[int] = None


@dataclass
class FileInfo:
    """Information about a repository file."""

    path: str
    name: str
    size: int
    type: str  # 'file' or 'dir'
    extension: Optional[str] = None
    is_documentation: bool = False
    is_test: bool = False
    is_config: bool = False


@dataclass
class RepositoryMetrics:
    """Calculated metrics for a repository."""

    total_commits: int
    unique_contributors: int
    lines_of_code: Optional[int]
    test_coverage_estimate: float  # 0.0 to 1.0
    documentation_presence: str  # e.g., "5 documentation files in 20 total files"
    days_since_last_commit: int
    commit_frequency: float  # commits per week
    avg_commit_size: float  # lines changed per commit


@dataclass
class RepositoryData:
    """Complete repository data for analysis."""

    # Basic repository information
    url: str
    full_name: str
    name: str
    owner: str
    description: Optional[str]

    # Repository metadata
    created_at: datetime
    updated_at: datetime
    pushed_at: datetime
    default_branch: str
    size: int  # KB

    # Content information
    languages: Dict[str, int]  # language -> bytes
    topics: List[str]
    license_name: Optional[str]

    # Activity information
    stars: int
    forks: int
    watchers: int
    open_issues: int

    # Repository structure
    has_readme: bool
    has_license: bool
    has_contributing: bool
    has_tests: bool
    has_ci_config: bool

    # Detailed data
    recent_commits: List[CommitInfo]
    file_structure: List[FileInfo]
    readme_content: Optional[str]

    # Calculated metrics
    metrics: RepositoryMetrics

    # Analysis metadata
    fetched_at: datetime
    is_private: bool
    is_fork: bool
    is_archived: bool
    is_disabled: bool

    # Optional enhanced data (must come after all required fields)
    key_files_content: Optional[Dict[str, Any]] = None  # Strategic file samples

    def __post_init__(self) -> None:
        """Validate and process repository data after initialization."""
        # Ensure required fields are present
        if not self.url or not self.full_name:
            raise ValueError("Repository URL and full name are required")

        # Validate language data
        if self.languages and not isinstance(self.languages, dict):
            raise ValueError("Languages must be a dictionary")

        # Ensure dates are timezone-aware
        if self.created_at.tzinfo is None:
            raise ValueError("All datetime fields must be timezone-aware")

    @property
    def primary_language(self) -> Optional[str]:
        """Get the primary programming language of the repository."""
        if not self.languages:
            return None
        return max(self.languages.keys(), key=lambda k: self.languages[k])

    @property
    def language_percentages(self) -> Dict[str, float]:
        """Get language usage as percentages."""
        if not self.languages:
            return {}

        total_bytes = sum(self.languages.values())
        if total_bytes == 0:
            return {}

        return {
            lang: round((bytes_count / total_bytes) * 100, 1)
            for lang, bytes_count in self.languages.items()
        }

    @property
    def is_active(self) -> bool:
        """Check if repository shows signs of recent activity."""
        return (
            self.metrics.days_since_last_commit <= 90
            and self.metrics.total_commits >= 3
        )
