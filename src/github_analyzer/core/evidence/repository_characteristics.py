# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Repository Characteristics Pre-processor.

This module generates factual characteristics from repository data
to enrich the evidence package sent to the AI engine.
NO JUDGMENTS, only facts.
"""

from typing import Any, Dict

from ...data.models import RepositoryData


def generate_repository_characteristics(repo_data: RepositoryData) -> Dict[str, Any]:
    """
    Generate factual characteristics from repository data.

    This function creates FACTS, not judgments or human-readable text.
    These characteristics will be used by the AI to generate intelligent
    Areas to Explore.

    Args:
        repo_data: The repository data to analyze

    Returns:
        Dictionary of factual characteristics
    """
    characteristics: Dict[str, Any] = {}

    # File and structure characteristics
    if repo_data.file_structure:
        characteristics["total_file_count"] = len(repo_data.file_structure)

        # Calculate max folder depth
        max_depth = 0
        for f in repo_data.file_structure[:200]:  # Sample first 200 files
            depth = f.path.count("/")
            max_depth = max(max_depth, depth)
        characteristics["max_folder_depth"] = max_depth

        # Check for test files
        test_files = [
            f
            for f in repo_data.file_structure[:200]
            if "test" in f.path.lower() or "spec" in f.path.lower()
        ]
        characteristics["has_test_files"] = len(test_files) > 0
        characteristics["test_file_count"] = len(test_files)
    else:
        characteristics["total_file_count"] = 0
        characteristics["max_folder_depth"] = 0
        characteristics["has_test_files"] = False
        characteristics["test_file_count"] = 0

    # Language characteristics
    if repo_data.languages:
        characteristics["language_count"] = len(repo_data.languages)
        characteristics["primary_language"] = max(
            repo_data.languages, key=lambda x: repo_data.languages[x]
        )
        characteristics["language_list"] = list(repo_data.languages.keys())[
            :10
        ]  # Top 10

        # Calculate if TypeScript migration is happening
        has_js = "JavaScript" in repo_data.languages
        has_ts = "TypeScript" in repo_data.languages
        characteristics["has_javascript_and_typescript"] = has_js and has_ts

        if has_js and has_ts:
            js_lines = repo_data.languages.get("JavaScript", 0)
            ts_lines = repo_data.languages.get("TypeScript", 0)
            total = js_lines + ts_lines
            characteristics["typescript_percentage"] = (
                (ts_lines / total * 100) if total > 0 else 0
            )
    else:
        characteristics["language_count"] = 0
        characteristics["primary_language"] = "unknown"
        characteristics["language_list"] = []
        characteristics["has_javascript_and_typescript"] = False

    # Collaboration characteristics
    if repo_data.metrics:
        characteristics["total_commits"] = repo_data.metrics.total_commits
        characteristics["unique_contributors"] = repo_data.metrics.unique_contributors
        # Note: RepositoryMetrics doesn't have total_files, use file_structure length
    else:
        characteristics["total_commits"] = 0
        characteristics["unique_contributors"] = 0

    # Commit pattern characteristics
    if repo_data.recent_commits:
        # Count refactoring commits
        refactor_commits = [
            c for c in repo_data.recent_commits[:100] if "refactor" in c.message.lower()
        ]
        characteristics["refactoring_commit_count"] = len(refactor_commits)

        # Count fix commits
        fix_commits = [
            c for c in repo_data.recent_commits[:100] if "fix" in c.message.lower()
        ]
        characteristics["fix_commit_count"] = len(fix_commits)

        # Count feature commits
        feature_commits = [
            c
            for c in repo_data.recent_commits[:100]
            if "feat" in c.message.lower() or "feature" in c.message.lower()
        ]
        characteristics["feature_commit_count"] = len(feature_commits)

        # Check for conventional commits
        conventional_prefixes = [
            "feat:",
            "fix:",
            "docs:",
            "style:",
            "refactor:",
            "test:",
            "chore:",
            "perf:",
            "ci:",
            "build:",
        ]
        conventional_commits = [
            c
            for c in repo_data.recent_commits[:50]
            if any(
                c.message.lower().startswith(prefix) for prefix in conventional_prefixes
            )
        ]
        characteristics["uses_conventional_commits"] = len(conventional_commits) > 10

        # Check for issue references
        issue_refs = [
            c
            for c in repo_data.recent_commits[:50]
            if "#" in c.message or "issue" in c.message.lower()
        ]
        characteristics["references_issues_in_commits"] = len(issue_refs) > 5
        characteristics["issue_reference_count"] = len(issue_refs)
    else:
        characteristics["refactoring_commit_count"] = 0
        characteristics["fix_commit_count"] = 0
        characteristics["feature_commit_count"] = 0
        characteristics["uses_conventional_commits"] = False
        characteristics["references_issues_in_commits"] = False
        characteristics["issue_reference_count"] = 0

    # Repository size characteristics
    if repo_data.size:
        characteristics["repository_size_kb"] = repo_data.size
        characteristics["repository_size_mb"] = repo_data.size / 1024
    else:
        characteristics["repository_size_kb"] = 0
        characteristics["repository_size_mb"] = 0

    # Activity characteristics
    characteristics["is_monorepo"] = (
        characteristics.get("total_file_count", 0) >= 1000
        and characteristics.get("max_folder_depth", 0) >= 6
    )

    characteristics["is_library"] = (
        (
            "lib" in repo_data.name.lower()
            or "sdk" in repo_data.name.lower()
            or "framework" in repo_data.name.lower()
        )
        if repo_data.name
        else False
    )

    # CI/CD characteristics
    characteristics["has_ci"] = (
        repo_data.has_ci_config if hasattr(repo_data, "has_ci_config") else False
    )
    characteristics["has_readme"] = (
        repo_data.has_readme if hasattr(repo_data, "has_readme") else False
    )
    characteristics["has_license"] = (
        repo_data.has_license if hasattr(repo_data, "has_license") else False
    )

    return characteristics
