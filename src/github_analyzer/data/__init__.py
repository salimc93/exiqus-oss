# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Data fetching and processing components.

This module handles GitHub API integration, caching, and data validation
for secure and efficient repository analysis.
"""

from .github_fetcher import GitHubFetcher
from .models import (
    CommitInfo,
    FileInfo,
    RepositoryData,
    RepositoryMetrics,
)

# Future data components
# from .cache import AnalysisCache
# from .validators import URLValidator, InputValidator

__all__: list[str] = [
    "GitHubFetcher",
    "RepositoryData",
    "CommitInfo",
    "FileInfo",
    "RepositoryMetrics",
    # Will be uncommented as modules are implemented
    # "AnalysisCache",
    # "URLValidator",
    # "InputValidator"
]
