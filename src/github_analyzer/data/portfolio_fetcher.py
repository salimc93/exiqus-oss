# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
GitHub Portfolio data fetcher using GraphQL API.

This module handles fetching repository data for portfolio analysis using
GitHub's GraphQL API exclusively for optimal performance.
"""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..utils.config import get_config
from ..utils.logging import get_logger
from .portfolio_models import PortfolioFetchResult, RepoData

logger = get_logger(__name__)


class PortfolioFetcher:
    """Fetch portfolio repository data using GraphQL API only."""

    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize portfolio fetcher with GitHub token.

        Args:
            github_token: GitHub personal access token. If None, uses config.
        """
        self.config = get_config()
        self.token = github_token or self.config.github_token

        if not self.token:
            raise ValueError("GitHub token is required for portfolio fetching")

        # Set up session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=5,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github.v3+json",
            }
        )

        self.graphql_url = "https://api.github.com/graphql"
        self.request_timeout = 30

    def fetch_user_portfolio(
        self, username: str, max_repos: int = 100
    ) -> PortfolioFetchResult:
        """
        Fetch all public repositories for a user.

        Args:
            username: GitHub username to analyze
            max_repos: Maximum number of repos to fetch (default: 100)

        Returns:
            PortfolioFetchResult with all repository data
        """
        start_time = time.time()

        logger.info(f"Fetching portfolio for {username} via GraphQL (max: {max_repos})")

        # Fetch repos using GraphQL
        raw_data = self._fetch_repos_graphql(username, max_repos)

        # Check if user was found
        if not raw_data.get("repos"):
            if raw_data.get("error") == "user_not_found":
                raise ValueError(f"GitHub user '{username}' not found")

        # Extract pushed_at dates from ALL repos BEFORE filtering (for portfolio span)
        all_repos_dates = []
        for repo in raw_data.get("repos", []):
            if repo.get("pushedAt"):
                all_repos_dates.append(repo["pushedAt"])

        # Process and filter repos
        processed_repos, skip_reasons, skipped_repos = self._process_repos(
            raw_data["repos"], username
        )

        fetch_time = time.time() - start_time

        logger.info(
            f"Fetched {len(processed_repos)} repos for {username} "
            f"({skip_reasons.get('total_skipped', 0)} skipped) "
            f"in {fetch_time:.2f}s using {raw_data['api_calls']} API calls"
        )

        return PortfolioFetchResult(
            repos=processed_repos,
            username=username,
            total_public_repos=raw_data.get("total_count", 0),
            repos_fetched=len(processed_repos),
            repos_skipped=skip_reasons.get("total_skipped", 0),
            skip_reasons=skip_reasons,
            skipped_repos=skipped_repos,
            api_calls_used=raw_data["api_calls"],
            fetch_time_seconds=round(fetch_time, 2),
            all_repos_dates=all_repos_dates,
        )

    def _get_query_template(self, batch_size: int, use_simple: bool = False) -> str:
        """
        Get GraphQL query template with specified batch size.

        Args:
            batch_size: Number of repos per request (10 or 30)
            use_simple: If True, exclude heavy fields (README, fileStructure, topics, license)
                       Used as fallback for large portfolios causing 502 errors

        Returns:
            GraphQL query string
        """
        # Common fields for both query types (critical for analysis)
        common_fields = """
                name
                nameWithOwner
                description
                url
                createdAt
                updatedAt
                pushedAt
                stargazerCount
                forkCount
                watchers { totalCount }
                isArchived
                isFork
                isPrivate
                diskUsage
                openIssues: issues(states: OPEN) { totalCount }
                hasWikiEnabled
                hasPages: homepageUrl
                primaryLanguage { name }
                languages(first: 10) {
                  edges {
                    node { name }
                    size
                  }
                }
                defaultBranchRef {
                  target {
                    ... on Commit {
                      history(first: 1) {
                        totalCount
                      }
                      committedDate
                    }
                  }
                }
        """

        # Heavy fields (nice-to-have, removed in simplified mode)
        heavy_fields = (
            """
                licenseInfo {
                  name
                  spdxId
                }
                repositoryTopics(first: 10) {
                  nodes {
                    topic { name }
                  }
                }
                readme: object(expression: "HEAD:README.md") {
                  ... on Blob {
                    text
                    byteSize
                  }
                }
                fileStructure: object(expression: "HEAD:") {
                  ... on Tree {
                    entries {
                      name
                      type
                      object {
                        ... on Blob {
                          byteSize
                        }
                      }
                    }
                  }
                }
        """
            if not use_simple
            else ""
        )

        return f"""
        query($username: String!, $cursor: String) {{
          user(login: $username) {{
            repositories(
              first: {batch_size},
              after: $cursor,
              ownerAffiliations: OWNER,
              privacy: PUBLIC,
              orderBy: {{field: CREATED_AT, direction: ASC}}
            ) {{
              totalCount
              pageInfo {{ hasNextPage, endCursor }}
              nodes {{
                {common_fields}
                {heavy_fields}
              }}
            }}
          }}
        }}
        """

    def _fetch_repos_graphql(self, username: str, max_repos: int) -> Dict[str, Any]:
        """
        Fetch developer's public repos using GraphQL with 3-tier fallback strategy.

        Fallback tiers for large portfolios (>50 repos):
        1. Full query, batch_size=30 (best quality, works for most users)
        2. Full query, batch_size=10 (if 502: smaller batches, same quality)
        3. Simple query, batch_size=10 (if 502: remove heavy fields, 90% quality)

        Args:
            username: GitHub username
            max_repos: Maximum repos to fetch

        Returns:
            Dictionary with repos and metadata
        """
        # Attempt 1: Full query with batch_size=30
        logger.info(
            f"Fetching portfolio for {username} via GraphQL (batch_size=30, full query)"
        )
        result = self._fetch_repos_with_config(
            username, max_repos, batch_size=30, use_simple=False
        )

        if result.get("error") == "api_502":
            logger.info(
                f"Reducing batch size for {username}: Retrying with batch_size=10 (GitHub API overload)"
            )
            # Attempt 2: Full query with batch_size=10
            result = self._fetch_repos_with_config(
                username, max_repos, batch_size=10, use_simple=False
            )

            if result.get("error") == "api_502":
                logger.info(
                    f"Switching to simplified query for {username}: Using batch_size=10 with reduced fields"
                )
                # Attempt 3: Simplified query with batch_size=10
                result = self._fetch_repos_with_config(
                    username, max_repos, batch_size=10, use_simple=True
                )

                if result.get("error") == "api_502":
                    logger.error(
                        f"All fallback attempts failed for {username}. GitHub API may be experiencing issues."
                    )

        return result

    def _fetch_repos_with_config(
        self, username: str, max_repos: int, batch_size: int, use_simple: bool
    ) -> Dict[str, Any]:
        """
        Fetch repos using specified configuration.

        Args:
            username: GitHub username
            max_repos: Maximum repos to fetch
            batch_size: Number of repos per request (10 or 30)
            use_simple: If True, use simplified query (no README, fileStructure, topics, license)

        Returns:
            Dictionary with repos and metadata
        """
        query = self._get_query_template(batch_size, use_simple)
        if use_simple:
            logger.info(
                f"Using simplified query (no README/fileStructure/topics/license) for {username}"
            )

        repos: List[Dict[str, Any]] = []
        cursor = None
        api_calls = 0
        total_count = 0

        while len(repos) < max_repos:
            variables = {"username": username, "cursor": cursor}

            try:
                response = self.session.post(
                    self.graphql_url,
                    json={"query": query, "variables": variables},
                    timeout=self.request_timeout,
                )
                api_calls += 1

                if response.status_code != 200:
                    # Provide clean logging for common errors, detailed logging for unexpected ones
                    if response.status_code == 502:
                        logger.warning(
                            f"GitHub API temporarily unavailable (502 Bad Gateway) for {username}"
                        )
                    else:
                        logger.error(
                            f"GraphQL API error: {response.status_code} - "
                            f"{response.text[:200]}"
                        )
                    # Return specific error code for 502 to trigger fallback
                    error_code = (
                        "api_502" if response.status_code == 502 else "api_error"
                    )
                    return {
                        "username": username,
                        "repos": [],
                        "total_count": 0,
                        "api_calls": api_calls,
                        "error": error_code,
                    }

                data = response.json()

                # Check for GraphQL errors
                if "errors" in data:
                    logger.error(f"GraphQL errors: {data['errors']}")

                    # Check if user not found
                    error_messages = [e.get("message", "") for e in data["errors"]]
                    if any(
                        "Could not resolve to a User" in msg for msg in error_messages
                    ):
                        return {
                            "username": username,
                            "repos": [],
                            "total_count": 0,
                            "api_calls": api_calls,
                            "error": "user_not_found",
                        }

                    return {
                        "username": username,
                        "repos": [],
                        "total_count": 0,
                        "api_calls": api_calls,
                        "error": "graphql_error",
                    }

                # Extract user data
                user_data = data.get("data", {}).get("user")
                if not user_data:
                    logger.warning(f"No user data returned for {username}")
                    break

                repo_data = user_data["repositories"]
                total_count = repo_data["totalCount"]

                # Add repos from this page
                repos.extend(repo_data["nodes"])

                logger.info(
                    f"Fetched page with {len(repo_data['nodes'])} repos "
                    f"(total: {len(repos)}/{total_count}, batch_size: {batch_size}, simple: {use_simple})"
                )

                # Check if we need to paginate
                page_info = repo_data["pageInfo"]
                if not page_info["hasNextPage"] or len(repos) >= max_repos:
                    break

                cursor = page_info["endCursor"]

            except requests.exceptions.Timeout:
                logger.error(f"Timeout fetching repos for {username}")
                break
            except Exception as e:
                logger.error(f"Error fetching repos for {username}: {e}")
                break

        return {
            "username": username,
            "repos": repos[:max_repos],  # Ensure we don't exceed max
            "total_count": total_count,
            "api_calls": api_calls,
        }

    def _process_repos(
        self, raw_repos: List[Dict[str, Any]], username: str
    ) -> Tuple[List[RepoData], Dict[str, int], Dict[str, List[str]]]:
        """
        Process raw repo data from GraphQL into RepoData objects.

        Args:
            raw_repos: Raw repository data from GraphQL
            username: GitHub username (for ownership check)

        Returns:
            Tuple of (processed_repos, skip_counts, skipped_repos_by_reason)
        """
        # Adaptive filtering: Use portfolio-size-based thresholds
        # Principle: Smaller portfolios need lenient thresholds to capture all work
        # Larger portfolios can be more selective to focus on substantial projects
        # Size thresholds are kept low - even 3KB can be 60+ lines of meaningful code
        total_public_repos = len(raw_repos)

        # Portfolio filtering: LOC-based only (commit count is unreliable)
        # Rationale: For project portfolios, commit count doesn't indicate quality
        # - 1 commit with 500 LOC is a complete project
        # - 50 commits doesn't mean better code
        # Focus on LOC as primary quality signal

        if total_public_repos <= 5:
            # Very small portfolios: Accept almost everything with code
            min_loc_threshold = 50  # Even small projects worth reviewing
            threshold_tier = "lenient"
        elif total_public_repos <= 15:
            # Small-medium portfolios: Moderate filtering
            min_loc_threshold = 100  # ~100 LOC meaningful project
            threshold_tier = "moderate"
        elif total_public_repos <= 25:
            # Medium-large portfolios: Standard filtering
            min_loc_threshold = 150  # ~150 LOC threshold
            threshold_tier = "standard"
        else:
            # Very large portfolios: More selective to focus on significant work
            min_loc_threshold = 200  # ~200 LOC threshold
            threshold_tier = "selective"

        logger.info(
            f"Using {threshold_tier} thresholds for portfolio "
            f"({total_public_repos} repos): >={min_loc_threshold} LOC "
            f"(commit count ignored for project portfolios)"
        )

        processed: List[RepoData] = []
        skip_counts: Dict[str, int] = {
            "forks": 0,
            "archived": 0,
            "trivial_size": 0,
            "total_skipped": 0,
        }
        skipped_repos: Dict[str, List[str]] = {
            "forks": [],
            "archived": [],
            "trivial_size": [],
        }

        for repo in raw_repos:
            # Extract basic data
            name = repo["name"]
            is_fork = repo["isFork"]
            is_archived = repo["isArchived"]
            size_kb = repo["diskUsage"]

            # Get commit count
            commits = 0
            if repo.get("defaultBranchRef"):
                target = repo["defaultBranchRef"].get("target", {})
                history = target.get("history", {})
                commits = history.get("totalCount", 0)

            # Calculate LOC from language data (primary metric)
            # diskUsage includes assets/builds, but language bytes is pure code
            languages = {}
            total_code_bytes = 0
            if repo.get("languages"):
                for edge in repo["languages"]["edges"]:
                    lang_name = edge["node"]["name"]
                    lang_size = edge["size"]
                    languages[lang_name] = lang_size
                    total_code_bytes += lang_size

            # Estimate LOC: ~50 bytes per line of code
            estimated_loc = total_code_bytes // 50

            # Skip forks
            if is_fork:
                skip_counts["forks"] += 1
                skip_counts["total_skipped"] += 1
                skipped_repos["forks"].append(name)
                logger.debug(f"Skipping fork: {name}")
                continue

            # Skip archived repos
            if is_archived:
                skip_counts["archived"] += 1
                skip_counts["total_skipped"] += 1
                skipped_repos["archived"].append(name)
                logger.debug(f"Skipping archived: {name}")
                continue

            # HYBRID FILTERING: LOC-based (primary) + size-based (backup)
            # Use LOC for code repos, diskUsage catches truly empty repos
            is_trivial = False

            if estimated_loc == 0 and size_kb < 2:
                # Truly empty repo (no code, < 2KB total)
                is_trivial = True
                skip_reason = f"empty repo ({size_kb}KB, 0 LOC)"
            elif estimated_loc > 0 and estimated_loc < min_loc_threshold:
                # Has code but below LOC threshold
                is_trivial = True
                skip_reason = f"{estimated_loc} LOC (< {min_loc_threshold} threshold)"
            elif estimated_loc == 0 and size_kb < 5:
                # No language data but small diskUsage (might be config-only repo)
                is_trivial = True
                skip_reason = f"{size_kb}KB, no code detected"

            if is_trivial:
                skip_counts["trivial_size"] += 1
                skip_counts["total_skipped"] += 1
                skipped_repos["trivial_size"].append(f"{name} ({skip_reason})")
                logger.debug(f"Skipping trivial: {name} ({skip_reason})")
                continue

            # NOTE: Commit count filtering removed
            # Rationale: For project portfolios, commit count is not a quality indicator
            # A single commit with 500 LOC is a complete project worth analyzing

            # Process topics
            topics = []
            if repo.get("repositoryTopics"):
                topics = [
                    node["topic"]["name"] for node in repo["repositoryTopics"]["nodes"]
                ]

            # Process README
            readme_content = None
            readme_size = 0
            if repo.get("readme"):
                readme_content = repo["readme"].get("text")
                readme_size = repo["readme"].get("byteSize", 0)

            # Check for key files in file structure
            key_files = []
            has_tests = False
            has_ci = False
            has_docker = False

            if repo.get("fileStructure"):
                entries = repo["fileStructure"].get("entries", [])
                for entry in entries:
                    entry_name = entry["name"].lower()
                    key_files.append(entry["name"])

                    if "test" in entry_name or entry_name in [
                        "tests",
                        "test",
                        "__tests__",
                    ]:
                        has_tests = True
                    if entry_name in [".github", ".gitlab-ci.yml", ".travis.yml"]:
                        has_ci = True
                    if entry_name in ["dockerfile", "docker-compose.yml"]:
                        has_docker = True

            # Get last commit date
            last_commit_date = None
            if repo.get("defaultBranchRef"):
                target = repo["defaultBranchRef"].get("target", {})
                committed_date = target.get("committedDate")
                if committed_date:
                    last_commit_date = datetime.fromisoformat(
                        committed_date.replace("Z", "+00:00")
                    )

            # Get license info
            has_license = False
            license_type = None
            if repo.get("licenseInfo"):
                has_license = True
                license_type = repo["licenseInfo"].get("spdxId")

            # Parse datetimes
            created_at = datetime.fromisoformat(
                repo["createdAt"].replace("Z", "+00:00")
            )
            updated_at = datetime.fromisoformat(
                repo["updatedAt"].replace("Z", "+00:00")
            )
            pushed_at = datetime.fromisoformat(repo["pushedAt"].replace("Z", "+00:00"))

            # Check ownership
            owner = repo["nameWithOwner"].split("/")[0]
            user_is_owner = owner.lower() == username.lower()

            # Create RepoData object
            repo_data = RepoData(
                name=name,
                full_name=repo["nameWithOwner"],
                url=repo["url"],
                owner=owner,
                created_at=created_at,
                updated_at=updated_at,
                pushed_at=pushed_at,
                stars=repo["stargazerCount"],
                forks=repo["forkCount"],
                watchers=repo.get("watchers", {}).get("totalCount", 0),
                is_fork=is_fork,
                is_archived=is_archived,
                is_private=repo.get("isPrivate", False),
                primary_language=(
                    repo.get("primaryLanguage", {}).get("name")
                    if repo.get("primaryLanguage")
                    else None
                ),
                languages=languages,
                total_commits=commits,
                topics=topics,
                description=repo.get("description"),
                size_kb=size_kb,
                open_issues=repo.get("openIssues", {}).get("totalCount", 0),
                has_wiki=repo.get("hasWikiEnabled", False),
                has_pages=bool(repo.get("hasPages")),
                readme_content=readme_content,
                readme_size=readme_size,
                has_tests=has_tests,
                has_ci=has_ci,
                has_docker=has_docker,
                has_license=has_license,
                license_type=license_type,
                user_commits=commits if user_is_owner else 0,
                user_is_owner=user_is_owner,
                last_commit_date=last_commit_date,
                file_count=len(entries) if repo.get("fileStructure") else 0,
                key_files=key_files[:20],  # Limit to first 20 key files
            )

            processed.append(repo_data)

        logger.info(
            f"Processed {len(processed)} repos, skipped {skip_counts['total_skipped']}: "
            f"forks={skip_counts['forks']}, archived={skip_counts['archived']}, "
            f"trivial={skip_counts['trivial_size']}"
        )

        return processed, skip_counts, skipped_repos
