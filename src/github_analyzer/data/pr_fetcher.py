# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
GitHub PR data fetcher using GraphQL API.

This module handles fetching pull request data for users using
GitHub's GraphQL API for optimal performance (4-5 API calls instead of 120+).
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..utils.config import get_config
from ..utils.logging import get_logger
from .pr_models import PRData, PRFetchResult

logger = get_logger(__name__)


class PRFetcher:
    """Fetch PR data using GraphQL API only."""

    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize PR fetcher with GitHub token.

        Args:
            github_token: GitHub personal access token. If None, uses config.
        """
        self.config = get_config()
        self.token = github_token or self.config.github_token

        if not self.token:
            raise ValueError("GitHub token is required for PR fetching")

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
        self.rate_limit_remaining = 5000  # Default until first API call
        self.rate_limit_limit = 5000

    def fetch_user_prs(self, username: str, max_prs: int = 1500) -> PRFetchResult:
        """
        Fetch PRs for a user (both authored and assigned), up to a maximum limit.

        Args:
            username: GitHub username to analyze
            max_prs: Maximum number of PRs to fetch (default: 1500)

        Returns:
            PRFetchResult with all PR data
        """
        import time

        start_time = time.time()
        api_calls = 0

        # Fetch authored PRs with pagination
        logger.info(f"Fetching authored PRs for {username} (max total: {max_prs})")
        authored_prs, authored_calls = self._fetch_authored_prs(username, max_prs)

        # Check if user was not found
        if authored_calls == -1:
            raise ValueError(f"GitHub user '{username}' not found")

        api_calls += authored_calls
        logger.info(
            f"Fetched {len(authored_prs)} authored PRs using {authored_calls} API calls"
        )

        # Calculate remaining budget for other PR types
        remaining_budget = max_prs - len(authored_prs)
        if remaining_budget <= 0:
            logger.warning(
                f"Reached max PR limit ({max_prs}) with authored PRs alone. "
                f"Skipping assigned/reviewed PRs."
            )
            # Set empty lists for other PR types and skip to deduplication
            assigned_prs: List[Dict[str, Any]] = []
            reviewed_prs: List[Dict[str, Any]] = []
        else:
            # Fetch assigned PRs (not authored by user)
            logger.info(
                f"Fetching assigned PRs for {username} (budget: {remaining_budget})"
            )
            assigned_prs, assigned_calls = self._fetch_assigned_prs(
                username, remaining_budget
            )
            api_calls += assigned_calls
            logger.info(
                f"Fetched {len(assigned_prs)} assigned PRs using {assigned_calls} API calls"
            )

            # OPTIONAL: Fetch PRs where user contributed reviews
            # This catches PRs they reviewed but didn't author/weren't assigned to
            # Using stable GraphQL API instead of unreliable search API
            logger.info(f"Fetching PRs with contributions (reviews) for {username}")
            reviewed_calls: int = 0
            try:
                reviewed_prs_temp, reviewed_calls = self._fetch_reviewed_prs(username)
                reviewed_prs = reviewed_prs_temp
                api_calls += reviewed_calls
                logger.info(
                    f"Fetched {len(reviewed_prs)} reviewed PRs using {reviewed_calls} API calls"
                )
            except Exception as e:
                # Review fetch failed - log warning but continue
                logger.warning(
                    f"Failed to fetch reviewed PRs: {e}. "
                    f"Continuing with {len(authored_prs) + len(assigned_prs)} PRs from authored + assigned."
                )

        # Combine and deduplicate
        all_prs = authored_prs.copy()
        seen_pr_keys = {
            f"{pr['repository']['owner']['login']}/{pr['repository']['name']}#{pr['number']}"
            for pr in authored_prs
        }

        for pr in assigned_prs:
            pr_key = f"{pr['repository']['owner']['login']}/{pr['repository']['name']}#{pr['number']}"
            if pr_key not in seen_pr_keys:
                pr["assigned_to_user"] = True
                all_prs.append(pr)
                seen_pr_keys.add(pr_key)

        for pr in reviewed_prs:
            pr_key = f"{pr['repository']['owner']['login']}/{pr['repository']['name']}#{pr['number']}"
            if pr_key not in seen_pr_keys:
                pr["reviewed_by_user"] = True
                all_prs.append(pr)
                seen_pr_keys.add(pr_key)

        # Convert to PRData objects
        pr_objects = []
        repos_set = set()

        for pr_dict in all_prs:
            # Skip None entries (can happen if GitHub returns incomplete data)
            if pr_dict is None:
                logger.warning("Skipping None PR entry from GitHub API response")
                continue

            pr_data = self._dict_to_pr_data(pr_dict, username)
            pr_objects.append(pr_data)
            repos_set.add(pr_data.repository)

        fetch_time = time.time() - start_time

        logger.info(
            f"Fetched {len(pr_objects)} PRs ({len(authored_prs)} authored, "
            f"{len(assigned_prs)} assigned) in {fetch_time:.2f}s using {api_calls} API calls"
        )

        return PRFetchResult(
            prs=pr_objects,
            username=username,
            total_count=len(pr_objects),
            repos_contributed=sorted(list(repos_set)),
            api_calls_used=api_calls,
            fetch_time_seconds=fetch_time,
        )

    def _fetch_authored_prs(
        self, username: str, max_prs: int = 1500
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Fetch PRs authored by the user, up to max_prs limit.

        Args:
            username: GitHub username
            max_prs: Maximum number of PRs to fetch

        Returns:
            Tuple of (list of PR dicts, number of API calls made)
        """
        query = """
        query($username: String!, $cursor: String) {
            user(login: $username) {
                pullRequests(first: 60, after: $cursor, orderBy: {field: CREATED_AT, direction: DESC}) {
                    totalCount
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                    nodes {
                        number
                        title
                        body
                        state
                        merged
                        mergedAt
                        createdAt
                        closedAt
                        additions
                        deletions
                        baseRefName
                        headRefName
                        changedFiles
                        reviewDecision
                        labels(first: 10) {
                            nodes {
                                name
                            }
                        }
                        author {
                            login
                        }
                        repository {
                            name
                            owner {
                                login
                            }
                        }
                        reviews {
                            totalCount
                        }
                        comments {
                            totalCount
                        }
                        commits {
                            totalCount
                        }
                        assignees(first: 10) {
                            nodes {
                                login
                            }
                        }
                    }
                }
            }
        }
        """

        all_prs: List[Dict[str, Any]] = []
        cursor = None
        api_calls = 0
        max_retries = 3
        retry_delay = 2  # seconds

        while True:  # Continue until no more pages
            variables = {"username": username, "cursor": cursor}

            # Add delay BEFORE making request to avoid triggering abuse detection
            import time

            # Smart rate limiting based on remaining quota
            base_delay = 5.0
            if self.rate_limit_remaining < 500:
                # Approaching limit - slow down significantly
                base_delay = 15.0
                logger.warning(
                    f"Rate limit low ({self.rate_limit_remaining} remaining), increasing delay to {base_delay}s"
                )
            elif self.rate_limit_remaining < 1000:
                # Getting close to limit - moderate slowdown
                base_delay = 10.0
                logger.info(
                    f"Rate limit moderate ({self.rate_limit_remaining} remaining), increasing delay to {base_delay}s"
                )

            time.sleep(base_delay)

            # Retry logic for failed requests
            for attempt in range(max_retries):
                try:
                    response = self.session.post(
                        self.graphql_url,
                        json={"query": query, "variables": variables},
                        timeout=30,
                    )
                    response.raise_for_status()
                    data = response.json()

                    # Validate response is not None or empty
                    if data is None:
                        raise ValueError("GitHub API returned None response")

                    api_calls += 1
                    break  # Success - exit retry loop

                except (requests.RequestException, ValueError) as e:
                    error_msg = str(e)

                    if attempt < max_retries - 1:
                        # Not the last attempt - retry after delay
                        # Use longer delays for 502 errors (abuse detection)
                        if "502" in error_msg or "Bad Gateway" in error_msg:
                            wait_time = 5 * (attempt + 1)  # 5s, 10s, 15s for 502s
                            logger.warning(
                                f"GitHub API 502 detected (page {api_calls + 1}, attempt {attempt + 1}/{max_retries}). "
                                f"Backing off for {wait_time}s to avoid abuse detection..."
                            )
                        else:
                            wait_time = retry_delay * (
                                attempt + 1
                            )  # Standard exponential backoff
                            logger.warning(
                                f"Error fetching authored PRs (page {api_calls + 1}, attempt {attempt + 1}/{max_retries}): {error_msg}. "
                                f"Retrying in {wait_time}s..."
                            )
                        import time

                        time.sleep(wait_time)
                        continue
                    else:
                        # Last attempt failed - raise error
                        logger.error(
                            f"Error fetching authored PRs (page {api_calls + 1}): {error_msg} after {max_retries} attempts"
                        )

                        # If this is the first call and it failed, raise specific errors
                        if api_calls == 0 and not all_prs:
                            if "502" in error_msg or "Bad Gateway" in error_msg:
                                raise RuntimeError(
                                    "GitHub API is currently experiencing issues (502 Bad Gateway). "
                                    "Please try again in a few minutes."
                                ) from e
                            elif (
                                "403" in error_msg or "rate limit" in error_msg.lower()
                            ):
                                raise RuntimeError(
                                    "GitHub API rate limit exceeded. Please try again later."
                                ) from e
                            else:
                                raise RuntimeError(
                                    f"Failed to fetch PR data from GitHub: {error_msg}"
                                ) from e

                        # Got partial data - raise error to prevent silent data loss
                        logger.warning(
                            f"Pagination interrupted after {api_calls} successful calls with {len(all_prs)} PRs. "
                            f"Data may be incomplete!"
                        )
                        raise RuntimeError(
                            f"Failed to fetch complete PR history. Got {len(all_prs)} PRs before error: {error_msg}"
                        ) from e

            # Process successful response (only reached if retry loop succeeded)
            # Safety check - ensure data is not None
            if data is None:
                logger.error("GitHub API returned None response - stopping pagination")
                break

            # Track rate limit from response
            if "data" in data and data["data"] and "rateLimit" in data["data"]:
                self.rate_limit_remaining = data["data"]["rateLimit"].get(
                    "remaining", self.rate_limit_remaining
                )
                self.rate_limit_limit = data["data"]["rateLimit"].get(
                    "limit", self.rate_limit_limit
                )

            if "errors" in data:
                logger.error(f"GraphQL errors: {data['errors']}")
                if not data.get("data"):
                    break

            user_data = data.get("data", {}).get("user")
            if not user_data:
                logger.warning(f"User {username} not found")
                # Return a special indicator for non-existent user
                return [], -1  # -1 indicates user not found

            pr_data = user_data.get("pullRequests", {})
            nodes = pr_data.get("nodes", [])

            for pr in nodes:
                if pr:
                    all_prs.append(pr)
                    # Check if we've reached the limit
                    if len(all_prs) >= max_prs:
                        logger.info(
                            f"Reached max PR limit ({max_prs}) for authored PRs. Stopping pagination."
                        )
                        return all_prs, api_calls

            # Check for more pages
            page_info = pr_data.get("pageInfo", {})
            if not page_info.get("hasNextPage"):
                break  # No more pages - we've fetched everything

            cursor = page_info.get("endCursor")

        return all_prs, api_calls

    def _fetch_reviewed_prs(self, username: str) -> Tuple[List[Dict[str, Any]], int]:
        """
        Fetch PRs where user contributed reviews using contributionsCollection.

        This is more reliable than the search API and fetches the last year of review activity.
        Returns PRs the user reviewed but didn't author or wasn't assigned to.
        """
        query = """
        query($username: String!, $from: DateTime!, $to: DateTime!) {
            user(login: $username) {
                contributionsCollection(from: $from, to: $to) {
                    pullRequestReviewContributions(first: 60) {
                        nodes {
                            pullRequest {
                                number
                                title
                                body
                                state
                                merged
                                mergedAt
                                createdAt
                                closedAt
                                additions
                                deletions
                                baseRefName
                                headRefName
                                changedFiles
                                reviewDecision
                                labels(first: 10) {
                                    nodes {
                                        name
                                    }
                                }
                                author {
                                    login
                                }
                                repository {
                                    name
                                    owner {
                                        login
                                    }
                                }
                                reviews {
                                    totalCount
                                }
                                comments {
                                    totalCount
                                }
                            }
                        }
                    }
                }
            }
        }
        """

        # Fetch last year of review activity
        from datetime import datetime, timedelta, timezone

        to_date = datetime.now(timezone.utc)
        from_date = to_date - timedelta(days=365)

        variables = {
            "username": username,
            "from": from_date.isoformat(),
            "to": to_date.isoformat(),
        }

        all_prs = []
        api_calls = 1

        try:
            response = self.session.post(
                self.graphql_url,
                json={"query": query, "variables": variables},
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=30,
            )

            if response.status_code != 200:
                logger.error(
                    f"GraphQL request failed with status {response.status_code}: {response.text}"
                )
                return [], api_calls

            data = response.json()

            if "errors" in data:
                logger.error(f"GraphQL errors in review fetch: {data['errors']}")
                return [], api_calls

            user_data = data.get("data", {}).get("user")
            if not user_data:
                logger.warning(f"User {username} not found")
                return [], api_calls

            contributions = user_data.get("contributionsCollection", {})
            review_contributions = contributions.get(
                "pullRequestReviewContributions", {}
            ).get("nodes", [])

            for contribution in review_contributions:
                pr = contribution.get("pullRequest")
                if pr:
                    all_prs.append(pr)

            logger.info(
                f"Fetched {len(all_prs)} reviewed PRs from contributionsCollection"
            )

        except Exception as e:
            logger.error(f"Failed to fetch reviewed PRs: {e}")
            raise

        return all_prs, api_calls

    def _fetch_involved_prs(self, username: str) -> Tuple[List[Dict[str, Any]], int]:
        """
        Fetch ALL PRs where user is involved (authored, assigned, reviewed, mentioned).

        Uses involves: search which is more comprehensive than user.pullRequests.
        This catches PRs that the GraphQL user query might miss.
        """
        query = """
        query($searchQuery: String!, $cursor: String) {
            search(query: $searchQuery, type: ISSUE, first: 60, after: $cursor) {
                issueCount
                pageInfo {
                    hasNextPage
                    endCursor
                }
                nodes {
                    ... on PullRequest {
                        number
                        title
                        body
                        state
                        merged
                        mergedAt
                        createdAt
                        closedAt
                        additions
                        deletions
                        baseRefName
                        headRefName
                        changedFiles
                        reviewDecision
                        labels(first: 10) {
                            nodes {
                                name
                            }
                        }
                        author {
                            login
                        }
                        repository {
                            name
                            owner {
                                login
                            }
                        }
                        reviews {
                            totalCount
                        }
                        comments {
                            totalCount
                        }
                        commits {
                            totalCount
                        }
                        assignees(first: 10) {
                            nodes {
                                login
                            }
                        }
                    }
                }
            }
        }
        """

        search_query = f"involves:{username} is:pr"
        all_prs: List[Dict[str, Any]] = []
        cursor = None
        api_calls = 0
        max_retries = 3
        retry_delay = 2

        while True:
            variables = {"searchQuery": search_query, "cursor": cursor}

            # Add delay BEFORE making request to avoid triggering abuse detection
            import time

            # Smart rate limiting based on remaining quota
            base_delay = 5.0
            if self.rate_limit_remaining < 500:
                base_delay = 15.0
                logger.warning(
                    f"Rate limit low ({self.rate_limit_remaining} remaining), increasing delay to {base_delay}s"
                )
            elif self.rate_limit_remaining < 1000:
                base_delay = 10.0
                logger.info(
                    f"Rate limit moderate ({self.rate_limit_remaining} remaining), increasing delay to {base_delay}s"
                )

            time.sleep(base_delay)

            # Retry logic for failed requests
            for attempt in range(max_retries):
                try:
                    response = self.session.post(
                        self.graphql_url,
                        json={"query": query, "variables": variables},
                        timeout=30,
                    )
                    response.raise_for_status()
                    data = response.json()

                    # Validate response is not None or empty
                    if data is None:
                        raise ValueError("GitHub API returned None response")

                    api_calls += 1
                    break  # Success - exit retry loop

                except (requests.RequestException, ValueError) as e:
                    error_msg = str(e)

                    if attempt < max_retries - 1:
                        # Use longer delays for 502 errors (abuse detection)
                        if "502" in error_msg or "Bad Gateway" in error_msg:
                            wait_time = 5 * (attempt + 1)  # 5s, 10s, 15s for 502s
                            logger.warning(
                                f"GitHub API 502 detected (page {api_calls + 1}, attempt {attempt + 1}/{max_retries}). "
                                f"Backing off for {wait_time}s to avoid abuse detection..."
                            )
                        else:
                            wait_time = retry_delay * (attempt + 1)
                            logger.warning(
                                f"Error fetching involved PRs (page {api_calls + 1}, attempt {attempt + 1}/{max_retries}): {error_msg}. "
                                f"Retrying in {wait_time}s..."
                            )
                        import time

                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(
                            f"Error fetching involved PRs (page {api_calls + 1}): {error_msg} after {max_retries} attempts"
                        )

                        if api_calls == 0 and not all_prs:
                            if "502" in error_msg or "Bad Gateway" in error_msg:
                                raise RuntimeError(
                                    "GitHub API is currently experiencing issues (502 Bad Gateway). "
                                    "Please try again in a few minutes."
                                ) from e
                            elif (
                                "403" in error_msg or "rate limit" in error_msg.lower()
                            ):
                                raise RuntimeError(
                                    "GitHub API rate limit exceeded. Please try again later."
                                ) from e
                            else:
                                raise RuntimeError(
                                    f"Failed to fetch PR data from GitHub: {error_msg}"
                                ) from e

                        logger.warning(
                            f"Pagination interrupted after {api_calls} successful calls with {len(all_prs)} PRs."
                        )
                        raise RuntimeError(
                            f"Failed to fetch complete PR history. Got {len(all_prs)} PRs before error: {error_msg}"
                        ) from e

            # Process successful response
            # Safety check - ensure data is not None
            if data is None:
                logger.error("GitHub API returned None response - stopping pagination")
                break

            # Track rate limit
            if "data" in data and data["data"] and "rateLimit" in data["data"]:
                self.rate_limit_remaining = data["data"]["rateLimit"].get(
                    "remaining", self.rate_limit_remaining
                )
                self.rate_limit_limit = data["data"]["rateLimit"].get(
                    "limit", self.rate_limit_limit
                )

            if "errors" in data:
                logger.error(f"GraphQL errors in involves search: {data['errors']}")
                if not data.get("data"):
                    break

            search_data = data.get("data", {}).get("search", {})
            nodes = search_data.get("nodes", [])

            for pr in nodes:
                if pr:
                    all_prs.append(pr)

            # Check for more pages
            page_info = search_data.get("pageInfo", {})
            if not page_info.get("hasNextPage"):
                break

            cursor = page_info.get("endCursor")

        return all_prs, api_calls

    def _fetch_assigned_prs(
        self, username: str, max_prs: int = 1500
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Fetch PRs where user is assigned but not the author, up to max_prs limit.

        Args:
            username: GitHub username
            max_prs: Maximum number of PRs to fetch

        Returns:
            Tuple of (list of PR dicts, number of API calls made)
        """
        query = """
        query($searchQuery: String!, $cursor: String) {
            search(query: $searchQuery, type: ISSUE, first: 60, after: $cursor) {
                issueCount
                pageInfo {
                    hasNextPage
                    endCursor
                }
                nodes {
                    ... on PullRequest {
                        number
                        title
                        body
                        state
                        merged
                        mergedAt
                        createdAt
                        closedAt
                        additions
                        deletions
                        baseRefName
                        headRefName
                        changedFiles
                        reviewDecision
                        labels(first: 10) {
                            nodes {
                                name
                            }
                        }
                        author {
                            login
                        }
                        repository {
                            name
                            owner {
                                login
                            }
                        }
                        reviews {
                            totalCount
                        }
                        comments {
                            totalCount
                        }
                        commits {
                            totalCount
                        }
                        assignees(first: 10) {
                            nodes {
                                login
                            }
                        }
                    }
                }
            }
        }
        """

        search_query = f"assignee:{username} is:pr"
        all_prs: List[Dict[str, Any]] = []
        cursor = None
        api_calls = 0
        max_retries = 3
        retry_delay = 2

        while True:
            variables = {"searchQuery": search_query, "cursor": cursor}

            # Add delay BEFORE making request to avoid triggering abuse detection
            import time

            # Smart rate limiting based on remaining quota
            base_delay = 5.0
            if self.rate_limit_remaining < 500:
                base_delay = 15.0
                logger.warning(
                    f"Rate limit low ({self.rate_limit_remaining} remaining), increasing delay to {base_delay}s"
                )
            elif self.rate_limit_remaining < 1000:
                base_delay = 10.0
                logger.info(
                    f"Rate limit moderate ({self.rate_limit_remaining} remaining), increasing delay to {base_delay}s"
                )

            time.sleep(base_delay)

            # Retry logic for failed requests
            for attempt in range(max_retries):
                try:
                    response = self.session.post(
                        self.graphql_url,
                        json={"query": query, "variables": variables},
                        timeout=30,
                    )
                    response.raise_for_status()
                    data = response.json()

                    # Validate response is not None or empty
                    if data is None:
                        raise ValueError("GitHub API returned None response")

                    api_calls += 1
                    break  # Success - exit retry loop

                except (requests.RequestException, ValueError) as e:
                    error_msg = str(e)

                    if attempt < max_retries - 1:
                        # Use longer delays for 502 errors (abuse detection)
                        if "502" in error_msg or "Bad Gateway" in error_msg:
                            wait_time = 5 * (attempt + 1)  # 5s, 10s, 15s for 502s
                            logger.warning(
                                f"GitHub API 502 detected (page {api_calls + 1}, attempt {attempt + 1}/{max_retries}). "
                                f"Backing off for {wait_time}s to avoid abuse detection..."
                            )
                        else:
                            wait_time = retry_delay * (attempt + 1)
                            logger.warning(
                                f"Error fetching assigned PRs (page {api_calls + 1}, attempt {attempt + 1}/{max_retries}): {error_msg}. "
                                f"Retrying in {wait_time}s..."
                            )
                        import time

                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(
                            f"Error fetching assigned PRs (page {api_calls + 1}): {error_msg} after {max_retries} attempts"
                        )

                        if api_calls == 0 and not all_prs:
                            if "502" in error_msg or "Bad Gateway" in error_msg:
                                raise RuntimeError(
                                    "GitHub API is currently experiencing issues (502 Bad Gateway). "
                                    "Please try again in a few minutes."
                                ) from e
                            elif (
                                "403" in error_msg or "rate limit" in error_msg.lower()
                            ):
                                raise RuntimeError(
                                    "GitHub API rate limit exceeded. Please try again later."
                                ) from e
                            else:
                                raise RuntimeError(
                                    f"Failed to fetch PR data from GitHub: {error_msg}"
                                ) from e

                        logger.warning(
                            f"Pagination interrupted after {api_calls} successful calls with {len(all_prs)} PRs."
                        )
                        raise RuntimeError(
                            f"Failed to fetch complete PR history. Got {len(all_prs)} PRs before error: {error_msg}"
                        ) from e

            # Process successful response
            # Safety check - ensure data is not None
            if data is None:
                logger.error("GitHub API returned None response - stopping pagination")
                break

            # Track rate limit from response
            if "data" in data and data["data"] and "rateLimit" in data["data"]:
                self.rate_limit_remaining = data["data"]["rateLimit"].get(
                    "remaining", self.rate_limit_remaining
                )
                self.rate_limit_limit = data["data"]["rateLimit"].get(
                    "limit", self.rate_limit_limit
                )

            if "errors" in data:
                logger.error(f"GraphQL errors in assignee search: {data['errors']}")
                if not data.get("data"):
                    break

            search_data = data.get("data", {}).get("search", {})
            nodes = search_data.get("nodes", [])

            for pr in nodes:
                if pr:
                    # Only include if user is NOT the author
                    author = pr.get("author") or {}
                    author_login = author.get("login", "")
                    if author_login != username:
                        all_prs.append(pr)
                        # Check if we've reached the limit
                        if len(all_prs) >= max_prs:
                            logger.info(
                                f"Reached max PR limit ({max_prs}) for assigned PRs. Stopping pagination."
                            )
                            return all_prs, api_calls

            # Check for more pages
            page_info = search_data.get("pageInfo", {})
            if not page_info.get("hasNextPage"):
                break

            cursor = page_info.get("endCursor")

        return all_prs, api_calls

    def _dict_to_pr_data(self, pr_dict: Dict[str, Any], username: str) -> PRData:
        """Convert GraphQL PR dict to PRData object."""
        # Validate pr_dict is not None
        if pr_dict is None:
            raise ValueError("Cannot convert None to PRData")

        # Parse dates
        created_at = self._parse_datetime(pr_dict.get("createdAt"))
        merged_at = self._parse_datetime(pr_dict.get("mergedAt"))
        closed_at = self._parse_datetime(pr_dict.get("closedAt"))

        # Extract repository info
        repo = pr_dict.get("repository") or {}
        repo_owner_data = repo.get("owner") or {}
        repo_owner = repo_owner_data.get("login", "unknown")
        repo_name = repo.get("name", "unknown")

        # Extract author
        author_data = pr_dict.get("author") or {}
        author = author_data.get("login", "unknown")

        # Extract assignees
        assignees = []
        assignees_data = pr_dict.get("assignees") or {}
        for assignee in assignees_data.get("nodes", []):
            if assignee:
                assignees.append(assignee.get("login", ""))

        # Extract labels
        labels = []
        labels_data = pr_dict.get("labels") or {}
        for label in labels_data.get("nodes", []):
            if label:
                labels.append(label.get("name", ""))

        # Extract review decision and changed files
        review_decision = pr_dict.get("reviewDecision")
        changed_files = pr_dict.get("changedFiles", 0)

        # Count user commits if collaborative
        user_commits = 0
        co_authors = []

        commits = pr_dict.get("commits", {})
        commit_nodes = commits.get("nodes", []) if isinstance(commits, dict) else []

        for commit in commit_nodes:
            if commit and commit.get("commit"):
                message = commit["commit"].get("message", "")
                # Check for co-authorship
                if "Co-authored-by:" in message:
                    import re

                    co_author_matches = re.findall(r"Co-authored-by: ([^<]+)", message)
                    co_authors.extend(co_author_matches)

        # Deduplicate co-authors
        co_authors = list(set(co_authors))

        # Determine if collaborative
        is_collaborative = (
            author != username
            or pr_dict.get("assigned_to_user", False)
            or len(co_authors) > 0
        )

        # Extract review counts
        reviews = pr_dict.get("reviews", {})
        reviews_count = reviews.get("totalCount", 0) if isinstance(reviews, dict) else 0

        comments = pr_dict.get("comments", {})
        comments_count = (
            comments.get("totalCount", 0) if isinstance(comments, dict) else 0
        )

        commits_count = commits.get("totalCount", 0) if isinstance(commits, dict) else 0

        # PRData requires created_at to be non-None
        if created_at is None:
            # Default to current time if parsing fails
            created_at = datetime.now(timezone.utc)

        return PRData(
            number=pr_dict.get("number", 0),
            title=pr_dict.get("title", ""),
            body=pr_dict.get("body"),
            state=pr_dict.get("state", "UNKNOWN"),
            merged=pr_dict.get("merged", False),
            created_at=created_at,
            merged_at=merged_at,
            closed_at=closed_at,
            additions=pr_dict.get("additions", 0),
            deletions=pr_dict.get("deletions", 0),
            commits_total=commits_count,
            reviews_count=reviews_count,
            comments_count=comments_count,
            author=author,
            assignees=assignees,
            repository_owner=repo_owner,
            repository_name=repo_name,
            base_ref=pr_dict.get("baseRefName", ""),
            head_ref=pr_dict.get("headRefName", ""),
            changed_files=changed_files,
            review_decision=review_decision,
            labels=labels,
            user_commits=user_commits,
            is_collaborative=is_collaborative,
            co_authors=co_authors,
            assigned_to_user=pr_dict.get("assigned_to_user", False),
        )

    def _parse_datetime(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO datetime string to timezone-aware datetime."""
        if not date_str:
            return None

        try:
            # Handle GitHub's ISO format
            if date_str.endswith("Z"):
                date_str = date_str.replace("Z", "+00:00")

            dt = datetime.fromisoformat(date_str)

            # Ensure timezone aware
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            return dt
        except (ValueError, AttributeError) as e:
            logger.warning(f"Failed to parse datetime {date_str}: {e}")
            return None

    def check_pr_count(self, username: str) -> int:
        """
        Lightweight check to get PR count for a user without fetching full data.

        Uses a single GraphQL query to get just the totalCount of user's PRs.
        This is used to determine if we should show "Run PR Analysis" banner.

        Args:
            username: GitHub username to check

        Returns:
            Total count of user's public PRs, or 0 if user not found or error
        """
        query = """
        query($username: String!) {
            user(login: $username) {
                pullRequests {
                    totalCount
                }
            }
        }
        """

        try:
            variables = {"username": username}
            response = self.session.post(
                self.graphql_url,
                json={"query": query, "variables": variables},
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()

            # Check for errors
            if "errors" in data:
                error_msg = data["errors"][0].get("message", "Unknown error")
                logger.warning(
                    f"GraphQL error checking PR count for {username}: {error_msg}"
                )
                return 0

            # Extract PR count
            user_data = data.get("data", {}).get("user")
            if not user_data:
                logger.info(f"User {username} not found when checking PR count")
                return 0

            pr_count = user_data.get("pullRequests", {}).get("totalCount", 0)
            logger.info(f"User {username} has {pr_count} total PRs")
            return int(pr_count)

        except Exception as e:
            logger.error(f"Failed to check PR count for {username}: {e}")
            return 0

    def get_rate_limit_status(self) -> tuple[int, int]:
        """Get current GitHub API rate limit status.

        Returns:
            Tuple of (remaining, limit)
        """
        return (self.rate_limit_remaining, self.rate_limit_limit)
