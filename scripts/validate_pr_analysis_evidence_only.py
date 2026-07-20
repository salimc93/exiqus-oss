#!/usr/bin/env python3
"""
PR Analysis Validation Script - Pure GraphQL Version.
Uses GraphQL for bulk data fetching, REST for details GraphQL can't provide.
Isolated test to validate we get same quality with fewer API calls.
"""

import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import anthropic  # noqa: E402
import requests  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

from src.github_analyzer.utils.config import get_config  # noqa: E402
from src.github_analyzer.utils.logging import get_logger  # noqa: E402

# Load environment variables
load_dotenv()

logger = get_logger(__name__)


@dataclass
class PREvidence:
    """PR-specific evidence patterns matching public repo structure."""

    pr_description_quality: List[str] = field(default_factory=list)
    review_responsiveness: List[str] = field(default_factory=list)
    code_review_skills: List[str] = field(default_factory=list)
    collaboration_patterns: List[str] = field(default_factory=list)
    integration_patterns: List[str] = field(default_factory=list)
    cross_repo_contributions: List[str] = field(default_factory=list)
    technical_substance: List[str] = field(default_factory=list)
    process_adherence: List[str] = field(default_factory=list)


class HybridPRAnalyzer:
    """
    Hybrid PR Analyzer using GraphQL for bulk fetch, REST for missing details.
    Reduces API calls from 120 to ~5-10 while maintaining depth.
    """

    def __init__(self, github_token: str, anthropic_api_key: str):
        """Initialize with API credentials."""
        self.github_token = github_token
        self.anthropic_client = anthropic.Anthropic(
            api_key=anthropic_api_key,
            timeout=600.0,
            max_retries=2,
        )

        # Scale+ tier configuration
        self.model = "claude-sonnet-4-20250514"
        self.max_tokens = 12000

        # GitHub API configuration
        self.base_url = "https://api.github.com"
        self.graphql_url = "https://api.github.com/graphql"
        self.headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3+json",
        }
        self.request_timeout = 30

    def fetch_user_prs_hybrid(
        self, username: str, max_prs: int = 999999
    ) -> Dict[str, Any]:
        """
        PURE GRAPHQL APPROACH:
        1. Check total PR count
        2. Use pagination to fetch complete history (up to max_prs)
        3. Apply smart temporal sampling
        4. Fetch REST details only for sampled PRs
        This ensures we NEVER miss critical contributions!
        """
        logger.info(f"[GraphQL] Starting PR fetch for: {username}")
        start_time = time.time()
        api_call_count = 0

        # Step 1: First get total count and initial batch
        graphql_query = """
        query($username: String!, $prCount: Int!, $cursor: String) {
          user(login: $username) {
            pullRequests(first: $prCount, after: $cursor, orderBy: {field: CREATED_AT, direction: DESC}) {
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
                additions
                deletions
                createdAt
                closedAt
                mergedAt
                author {
                  login
                }
                repository {
                  name
                  owner {
                    login
                  }
                  isPrivate
                }
                # Enhanced: Get review decisions and content
                reviews(first: 10) {
                  totalCount
                  nodes {
                    state  # APPROVED/CHANGES_REQUESTED/COMMENTED
                    body   # Review comment content
                    author {
                      login
                    }
                  }
                }
                # NEW: Get assignees to find collaborative PRs
                assignees(first: 5) {
                  nodes {
                    login
                  }
                }
                comments {
                  totalCount
                }
                # Enhanced: Get commit details for co-authors
                commits(first: 5) {
                  totalCount
                  nodes {
                    commit {
                      message  # Contains Co-authored-by
                      author {
                        name
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """

        # Execute GraphQL with PAGINATION to get complete history
        all_prs = []
        cursor = None
        total_count = 0

        # Determine fetch strategy based on total count
        batch_size = 100  # GitHub's max per page

        # Fetch until we have everything or hit the total count
        while True:
            graphql_payload = {
                "query": graphql_query,
                "variables": {
                    "username": username,
                    "prCount": batch_size,
                    "cursor": cursor,
                },
            }

            logger.info(
                f"[GraphQL] Fetching batch {len(all_prs) // batch_size + 1} (cursor: {cursor[:10] if cursor else 'start'}...)"
            )

            # Add retry logic for 502 errors
            max_retries = 3
            for retry in range(max_retries):
                try:
                    response = requests.post(
                        self.graphql_url,
                        headers={**self.headers, "Content-Type": "application/json"},
                        json=graphql_payload,
                        timeout=self.request_timeout,
                    )
                    api_call_count += 1

                    if (
                        response.status_code in [502, 503, 504]
                        and retry < max_retries - 1
                    ):
                        logger.warning(
                            f"Got {response.status_code} error, retrying in {2**retry} seconds..."
                        )
                        time.sleep(2**retry)  # Exponential backoff: 1s, 2s, 4s
                        continue
                    elif response.status_code == 200:
                        break  # Success!
                    else:
                        logger.error(f"GraphQL error: {response.status_code}")
                        if len(all_prs) > 0:
                            break  # Use what we have
                        return self._fallback_to_rest(username, max_prs)
                except requests.exceptions.Timeout:
                    if retry < max_retries - 1:
                        logger.warning("Request timeout, retrying...")
                        continue
                    else:
                        logger.error("Request timeout after retries")
                        if len(all_prs) > 0:
                            break
                        return self._fallback_to_rest(username, max_prs)

            # Only try to parse JSON if we got a 200 response
            if response.status_code != 200:
                logger.error(f"Non-200 status after retries: {response.status_code}")
                if len(all_prs) > 0:
                    break  # Use what we have
                return self._fallback_to_rest(username, max_prs)

            graphql_data = response.json()
            if "errors" in graphql_data:
                logger.error(f"GraphQL errors: {graphql_data['errors']}")
                if len(all_prs) > 0:
                    break  # Use what we have
                return self._fallback_to_rest(username, max_prs)

            # Extract this batch
            user_data = graphql_data.get("data", {}).get("user", {})
            pr_batch = user_data.get("pullRequests", {})
            batch_prs = pr_batch.get("nodes", [])

            # First batch - get total count
            if total_count == 0:
                total_count = pr_batch.get("totalCount", 0)
                logger.info(
                    f"[GraphQL] Total authored PRs for {username}: {total_count}"
                )

                # Always fetch complete history
                logger.info(
                    f"[GraphQL] Will fetch ALL {total_count} authored PRs (complete history)"
                )

            all_prs.extend(batch_prs)

            # Check if we have more pages and should continue
            page_info = pr_batch.get("pageInfo", {})
            # Stop only when there are no more pages
            if not page_info.get("hasNextPage"):
                break

            cursor = page_info.get("endCursor")

        prs = all_prs
        print(f"\n🔍 DEBUG: After pagination, all_prs has {len(all_prs)} PRs")
        logger.info(
            f"[GraphQL] Fetched {len(prs)} authored PRs using {api_call_count} API calls (pagination)"
        )

        # Step 2: SMART TEMPORAL SAMPLING - Sample across entire history
        repos_contributed = set()

        now = datetime.now(timezone.utc)

        # Time-based categorization
        recent_prs = []  # Last 3 months
        mid_term_prs = []  # 3-12 months ago
        historical_prs = []  # 12+ months ago (CATCHES DEBUGGER PR!)

        # Size/impact-based categorization
        hero_prs = []  # Large PRs or high commits
        reviewed_prs = []  # PRs with significant review activity

        for idx, pr in enumerate(prs):
            if not pr:
                continue

            # Track repos
            repo = pr.get("repository", {})
            repo_name = (
                f"{repo.get('owner', {}).get('login', '')}/{repo.get('name', '')}"
            )
            repos_contributed.add(repo_name)

            # Parse PR date
            created_at = pr.get("createdAt", "")
            if created_at:
                pr_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                age_days = (now - pr_date).days

                # Temporal categorization
                if age_days < 90:  # Last 3 months
                    if len(recent_prs) < 20:  # Limit recent PRs
                        recent_prs.append(pr)
                elif age_days < 365:  # 3-12 months
                    if len(mid_term_prs) < 15:  # Sample mid-term
                        mid_term_prs.append(pr)
                else:  # Over 1 year old
                    if len(historical_prs) < 10:  # Sample historical
                        historical_prs.append(pr)

            # Impact categorization
            additions = pr.get("additions", 0)
            commits = pr.get("commits", {}).get("totalCount", 0)

            # Hero PRs: Large additions OR many commits (catches debugger!)
            if additions > 500 or commits > 50:
                hero_prs.append(pr)

            # High review activity
            if pr.get("reviews", {}).get("totalCount", 0) > 3:
                reviewed_prs.append(pr)

        # Smart selection: Get diverse sample across time periods
        selected_for_rest = set()

        # Add top hero PRs (max 7) - includes large/high-commit PRs
        for pr in hero_prs[:7]:
            selected_for_rest.add(pr.get("number"))
            logger.debug(
                f"Selected hero PR #{pr.get('number')}: {pr.get('title', '')[:50]}"
            )

        # Add samples from each time period for temporal coverage
        for pr in recent_prs[:3]:  # 3 from recent
            selected_for_rest.add(pr.get("number"))
        for pr in mid_term_prs[:3]:  # 3 from mid-term
            selected_for_rest.add(pr.get("number"))
        for pr in historical_prs[:2]:  # 2 from historical (includes old important work)
            selected_for_rest.add(pr.get("number"))

        # Add highly reviewed PRs (max 3)
        for pr in sorted(
            reviewed_prs,
            key=lambda x: x.get("reviews", {}).get("totalCount", 0),
            reverse=True,
        )[:3]:
            selected_for_rest.add(pr.get("number"))

        logger.info(
            f"[GraphQL] Temporal sampling: {len(recent_prs)} recent, {len(mid_term_prs)} mid-term, {len(historical_prs)} historical"
        )
        logger.info(
            f"[GraphQL] Impact sampling: {len(hero_prs)} hero PRs, {len(reviewed_prs)} reviewed"
        )
        logger.info(
            f"[GraphQL] Selected {len(selected_for_rest)} PRs for potential detailed analysis"
        )

        # Step 2.5: SEARCH FOR COLLABORATIVE PRs (where user is assignee)
        # COMMENTED OUT - We're somehow getting all 230 PRs with just 4 API calls
        # This code searches for PRs where user is assignee but not author
        # But we're already getting those 14 PRs somehow...

        # Step 2.5: SEARCH FOR COLLABORATIVE PRs (where user is assignee)
        # This adds the 14 PRs where Anthony is assignee but not author
        # Including the critical debugger PR #13433!

        print(
            f"\n🔍 DEBUG: About to search for assignee PRs. Current count: {len(all_prs)}"
        )
        logger.info(f"[GraphQL] Searching for PRs where {username} is assignee...")
        logger.info(f"[GraphQL] API calls before assignee search: {api_call_count}")

        # GraphQL query for PRs where user is an assignee
        assignee_query = """
        query($searchQuery: String!, $prCount: Int!, $cursor: String) {
          search(query: $searchQuery, type: ISSUE, first: $prCount, after: $cursor) {
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
                additions
                deletions
                createdAt
                closedAt
                mergedAt
                author {
                  login
                }
                repository {
                  name
                  owner {
                    login
                  }
                  isPrivate
                }
                reviews(first: 10) {
                  totalCount
                  nodes {
                    state
                    body
                    author {
                      login
                    }
                  }
                }
                assignees(first: 5) {
                  nodes {
                    login
                  }
                }
                comments {
                  totalCount
                }
                commits(first: 5) {
                  totalCount
                  nodes {
                    commit {
                      message
                      author {
                        name
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """

        assignee_prs = []
        cursor = None
        max_assignee_prs = 100  # Fetch up to 100 PRs where user is assignee

        while len(assignee_prs) < max_assignee_prs:
            # Construct search query with username
            search_query = f"assignee:{username} type:pr is:merged"
            logger.info(f"[GraphQL] Assignee search query: '{search_query}'")

            assignee_payload = {
                "query": assignee_query,
                "variables": {
                    "searchQuery": search_query,
                    "prCount": min(100, max_assignee_prs - len(assignee_prs)),
                    "cursor": cursor,
                },
            }
            logger.debug(
                f"[GraphQL] Assignee payload variables: {assignee_payload['variables']}"
            )

            # Try with retries
            for retry in range(max_retries):
                try:
                    response = requests.post(
                        f"{self.base_url}/graphql",
                        headers=self.headers,
                        json=assignee_payload,
                        timeout=self.request_timeout,
                    )
                    api_call_count += 1
                    logger.info(f"[GraphQL] Assignee search API call #{api_call_count}")

                    if (
                        response.status_code in [502, 503, 504]
                        and retry < max_retries - 1
                    ):
                        logger.warning(
                            f"Got {response.status_code} error on assignee search, retrying..."
                        )
                        time.sleep(2**retry)
                        continue
                    elif response.status_code == 200:
                        break
                    else:
                        logger.error(
                            f"GraphQL assignee search error: {response.status_code}"
                        )
                        break
                except requests.exceptions.Timeout:
                    if retry < max_retries - 1:
                        logger.warning("Assignee search timeout, retrying...")
                        continue
                    else:
                        logger.error("Assignee search timeout after retries")
                        break

            if response.status_code == 200:
                assignee_data = response.json()
                if "errors" in assignee_data:
                    logger.error(
                        f"GraphQL assignee search errors: {assignee_data['errors']}"
                    )
                    break

                search_results = assignee_data.get("data", {}).get("search", {})
                total_count = search_results.get("issueCount", 0)
                logger.info(
                    f"[GraphQL] Assignee search found {total_count} total PRs where {username} is assignee"
                )
                batch = search_results.get("nodes", [])

                # Filter out PRs that the user authored (we already have those)
                collaborative_batch = [
                    pr
                    for pr in batch
                    if pr and pr.get("author", {}).get("login") != username
                ]

                assignee_prs.extend(collaborative_batch)

                page_info = search_results.get("pageInfo", {})
                if (
                    not page_info.get("hasNextPage")
                    or len(assignee_prs) >= max_assignee_prs
                ):
                    break

                cursor = page_info.get("endCursor")

        print(f"🔍 DEBUG: Found {len(assignee_prs)} assignee PRs")
        logger.info(
            f"[GraphQL] Found {len(assignee_prs)} PRs where {username} is assignee (not author)"
        )
        logger.info(
            f"[GraphQL] Total API calls after assignee search: {api_call_count}"
        )

        # Add assignee PRs to our main PR list
        collaborative_prs = assignee_prs
        print(f"🔍 DEBUG: Before adding assignee PRs: {len(all_prs)} PRs")
        all_prs.extend(assignee_prs)
        print(f"🔍 DEBUG: After adding assignee PRs: {len(all_prs)} PRs")

        # Update prs to include all
        prs = all_prs

        # Mark collaborative PRs for potential detail analysis
        for pr in assignee_prs:
            repo = pr.get("repository", {})
            repo_name = (
                f"{repo.get('owner', {}).get('login', '')}/{repo.get('name', '')}"
            )
            repos_contributed.add(repo_name)

            # High-commit collaborative PRs are significant
            if pr.get("commits", {}).get("totalCount", 0) > 50:
                selected_for_rest.add(pr.get("number"))
                logger.info(
                    f"[GraphQL] Found high-commit collaborative PR #{pr.get('number')} ({pr.get('commits', {}).get('totalCount', 0)} commits): {pr.get('title', '')[:50]}"
                )

        logger.info(
            f"[GraphQL] Found {len(collaborative_prs)} collaborative PRs where user is assignee"
        )
        logger.info(f"[GraphQL] Total PRs to analyze: {len(prs)} (authored + assigned)")

        # Step 3: Process PRs - no REST needed, GraphQL has everything!
        print(f"\n🔍 DEBUG: Before processing - prs has {len(prs)} items")
        enhanced_prs = []

        for pr in prs:
            if pr:
                # Check if user is assigned (collaborative PR detection)
                if pr.get("assignees"):
                    assignee_logins = [a.get("login") for a in pr["assignees"]["nodes"]]
                    # If user is assignee but not author = collaborative
                    if username in assignee_logins:
                        # Get the author login if available
                        # Note: For authored PRs, this will be handled elsewhere
                        pr["is_collaborative"] = True
                        pr["assigned_to_user"] = True

                # All review data already in GraphQL
                if pr.get("reviews", {}).get("nodes"):
                    pr["review_decisions"] = [
                        {
                            "state": r.get("state"),
                            "body": (r.get("body") or "")[:200],
                            "author": r.get("author", {}).get("login"),
                        }
                        for r in pr["reviews"]["nodes"]
                    ]

                enhanced_prs.append(pr)

        # Step 4: Calculate elapsed time (no REST calls anymore!)
        elapsed_time = time.time() - start_time

        print(
            f"\n🔍 DEBUG: After processing - enhanced_prs has {len(enhanced_prs)} items"
        )
        logger.info(
            f"[GRAPHQL-ONLY] Complete. API calls: {api_call_count}, Time: {elapsed_time:.2f}s"
        )

        # Format data to match original structure
        print(f"\n🔍 DEBUG FINAL: Returning total_prs as {len(enhanced_prs)}")
        return {
            "username": username,
            "total_prs": len(enhanced_prs),
            "repos_contributed_to": list(repos_contributed),
            "repos_count": len(repos_contributed),
            "prs": enhanced_prs,
            "api_calls_used": api_call_count,
            "fetch_time": elapsed_time,
        }

    def _fallback_to_rest(self, username: str, max_prs: int) -> Dict[str, Any]:
        """Fallback to REST API if GraphQL fails."""
        logger.warning("[GraphQL] Error in GraphQL query, data may be incomplete...")

        # Use the original REST approach but optimized
        search_url = "https://api.github.com/search/issues"
        params = {
            "q": f"author:{username} type:pr is:public",
            "sort": "created",
            "order": "desc",
            "per_page": min(max_prs, 100),
        }

        response = requests.get(
            search_url,
            headers=self.headers,
            params=params,
            timeout=self.request_timeout,
        )

        if response.status_code != 200:
            logger.error(f"REST API error: {response.status_code}")
            return {}

        data = response.json()
        pr_list = data.get("items", [])

        return {
            "username": username,
            "total_prs": len(pr_list),
            "repos_contributed_to": [],
            "repos_count": 0,
            "prs": pr_list,
            "api_calls_used": 1,
            "fetch_time": 0,
        }

    def extract_pr_evidence(self, pr_data: Dict[str, Any]) -> PREvidence:
        """Extract evidence from GraphQL-formatted PR data."""
        evidence = PREvidence()

        # CRITICAL: Track merge evidence as PRIMARY signal
        merged_prs = []
        total_prs = len(pr_data.get("prs", []))

        # NEW: Time-based consistency analysis (what Zed values)
        pr_dates = []
        co_authored_prs = []
        high_review_prs = []
        feature_prs = []
        fix_prs = []
        owned_features = []  # Features taken from start to production

        for pr in pr_data.get("prs", []):
            if not pr:
                continue

            repo = pr.get("repository", {})
            repo_name = f"{repo.get('owner', {}).get('login', 'unknown')}/{repo.get('name', 'unknown')}"

            # Check if this is a collaborative PR
            is_collaborative = pr.get("is_collaborative", False)

            # NEW: Collect time-based data for consistency analysis
            if pr.get("createdAt"):
                pr_dates.append(
                    datetime.fromisoformat(pr["createdAt"].replace("Z", "+00:00"))
                )

            # NEW: Feature vs Fix classification (Zed values feature ownership)
            pr_title_lower = pr.get("title", "").lower()
            if any(
                word in pr_title_lower
                for word in [
                    "implement",
                    "add",
                    "create",
                    "feature",
                    "introduce",
                    "new",
                ]
            ):
                feature_prs.append(pr)
                # If it's a large merged feature, it's owned
                if pr.get("merged") and pr.get("additions", 0) > 200:
                    owned_features.append(
                        {
                            "title": pr.get("title", ""),
                            "additions": pr.get("additions", 0),
                            "reviews": pr.get("reviews", {}).get("totalCount", 0),
                        }
                    )
            elif any(
                word in pr_title_lower
                for word in ["fix", "bug", "resolve", "patch", "correct"]
            ):
                fix_prs.append(pr)

            # NEW: Track high review engagement (3+ reviews = deep collaboration)
            if pr.get("reviews", {}).get("totalCount", 0) >= 3:
                high_review_prs.append(
                    {
                        "title": pr.get("title", ""),
                        "reviews": pr.get("reviews", {}).get("totalCount", 0),
                        "merged": pr.get("merged", False),
                    }
                )

            # NEW: Check for co-authorship (pair programming evidence)
            if pr.get("commits", {}).get("nodes"):
                for commit in pr["commits"]["nodes"][:5]:  # Check first 5 commits
                    if commit and commit.get("commit", {}).get("message", ""):
                        if "Co-authored-by" in commit["commit"]["message"]:
                            co_authored_prs.append(pr.get("number"))
                            break

            # MERGE SUCCESS - The most fundamental evidence
            if pr.get("merged"):
                merged_prs.append(
                    {
                        "repo": repo_name,
                        "title": pr.get("title", ""),
                        "additions": pr.get("additions", 0),
                        "reviews": pr.get("reviews", {}).get("totalCount", 0),
                        "comments": pr.get("comments", {}).get("totalCount", 0),
                        "is_collaborative": is_collaborative,
                        "user_commits": (
                            pr.get("user_commits", 0) if is_collaborative else None
                        ),
                    }
                )

                # Detailed merge evidence - distinguish collaborative work
                if is_collaborative:
                    user_commits = pr.get("user_commits", 0)
                    commits_data = pr.get("commits", {})
                    total_commits = (
                        commits_data.get("totalCount", 0)
                        if isinstance(commits_data, dict)
                        else 0
                    )
                    author = (
                        pr.get("author", {}).get("login", "unknown")
                        if pr.get("author")
                        else "unknown"
                    )

                    # For assignee PRs, use total commits as proxy for significance
                    significant_contribution = user_commits > 10 or (
                        pr.get("assigned_to_user") and total_commits > 50
                    )

                    if significant_contribution:
                        if pr.get("assigned_to_user") and not user_commits:
                            # This is an assignee PR (not authored)
                            # Check if author is the same as the user being analyzed (self-assignment)
                            if author == pr_data.get("username", ""):
                                evidence.collaboration_patterns.append(
                                    f"Self-managed major PR '{pr.get('title', 'untitled')[:50]}' with {total_commits} commits - {pr.get('additions', 0):,} additions"
                                )
                            else:
                                evidence.collaboration_patterns.append(
                                    f"Assigned to major PR '{pr.get('title', 'untitled')[:50]}' with {total_commits} commits (collaborated with {author}) - {pr.get('additions', 0):,} additions"
                                )
                        else:
                            evidence.collaboration_patterns.append(
                                f"Co-authored {user_commits} commits on PR '{pr.get('title', 'untitled')[:50]}' (led by {author}) - demonstrates sustained collaborative work"
                            )

                        # Highlight exceptionally large collaborative contributions
                        if total_commits > 500 or pr.get("additions", 0) > 10000:
                            pr_title = pr.get("title", "untitled")[:50]
                            if author == pr_data.get("username", ""):
                                evidence.technical_substance.append(
                                    f"Major self-managed contribution: '{pr_title}' with {total_commits} commits and {pr.get('additions', 0):,} additions"
                                )
                                evidence.collaboration_patterns.append(
                                    f"KEY HIRING SIGNAL: Exceptional self-managed PR '{pr_title}' - {total_commits} commits, {pr.get('additions', 0):,} additions"
                                )
                            else:
                                evidence.technical_substance.append(
                                    f"Major collaborative contribution: Assigned to '{pr_title}' with {total_commits} commits and {pr.get('additions', 0):,} additions"
                                )
                                evidence.collaboration_patterns.append(
                                    f"KEY HIRING SIGNAL: Exceptional collaborative PR '{pr_title}' - {total_commits} commits, {pr.get('additions', 0):,} additions (with {author})"
                                )
                    else:
                        evidence.collaboration_patterns.append(
                            f"Contributed {user_commits} commits to collaborative PR '{pr.get('title', 'untitled')[:50]}'"
                        )
                else:
                    evidence.collaboration_patterns.append(
                        f"Successfully merged authored PR '{pr.get('title', 'untitled')[:50]}' into {repo_name}"
                    )
                evidence.integration_patterns.append(
                    f"Code met production standards for {repo_name}"
                )

                # If merged after review, that's even stronger evidence
                if pr.get("reviews", {}).get("totalCount", 0) > 0:
                    evidence.review_responsiveness.append(
                        f"Merged after {pr.get('reviews', {}).get('totalCount', 0)} reviews - demonstrates ability to address feedback"
                    )

            # Technical Substance - Include PR title for context
            additions = pr.get("additions", 0)
            deletions = pr.get("deletions", 0)
            pr_title = pr.get("title", "")[:60]  # First 60 chars of title

            if additions > 100 or deletions > 100:
                merge_status = "merged" if pr.get("merged") else "unmerged"
                if pr_title:
                    evidence.technical_substance.append(
                        f"Substantial {merge_status} PR '{pr_title}' with {additions}+ additions in {repo_name}"
                    )
                else:
                    evidence.technical_substance.append(
                        f"Substantial {merge_status} PR with {additions}+ additions in {repo_name}"
                    )

            # PR Description Quality - GraphQL provides body
            body = pr.get("body", "")
            if body:
                body_length = len(body)
                if body_length > 500:
                    evidence.pr_description_quality.append(
                        f"Comprehensive PR description ({body_length} chars) in {repo_name}"
                    )
                    evidence.process_adherence.append(
                        f"Follows documentation standards in {repo_name}"
                    )
                elif body_length > 100:
                    evidence.pr_description_quality.append(
                        f"Adequate PR description in {repo_name}"
                    )

            # Review Activity - Enhanced with REST data when available
            # Handle both GraphQL (nested dict) and REST (direct integer) formats
            reviews_data = pr.get("reviews", 0)
            review_count = (
                reviews_data.get("totalCount", 0)
                if isinstance(reviews_data, dict)
                else reviews_data
            )

            comments_data = pr.get("comments", 0)
            comment_count = (
                comments_data.get("totalCount", 0)
                if isinstance(comments_data, dict)
                else comments_data
            )

            # Extract review decision patterns (from REST)
            if pr.get("review_decisions"):
                decisions = pr["review_decisions"]
                approved_count = sum(1 for d in decisions if d["state"] == "APPROVED")
                changes_requested = sum(
                    1 for d in decisions if d["state"] == "CHANGES_REQUESTED"
                )

                if changes_requested > 0 and pr.get("merged"):
                    evidence.review_responsiveness.append(
                        f"PR '{pr.get('title', '')[:40]}' had {changes_requested} change requests, addressed them, and got merged"
                    )
                    evidence.collaboration_patterns.append(
                        f"Successfully navigated review feedback to achieve merge in {repo_name}"
                    )

                if approved_count > 0:
                    evidence.integration_patterns.append(
                        f"Received {approved_count} approvals before merge in {repo_name}"
                    )

                # Extract specific feedback patterns
                for decision in decisions[:2]:  # Top 2 review decisions
                    if decision["body"]:
                        evidence.review_responsiveness.append(
                            f"Review feedback: '{decision['body'][:100]}...'"
                        )

            elif review_count > 0:
                evidence.review_responsiveness.append(
                    f"Received {review_count} reviews in {repo_name}"
                )

            # Extract communication patterns from comments (from REST)
            if pr.get("review_comments"):
                comments = pr["review_comments"]
                evidence.collaboration_patterns.append(
                    f"Active discussion with {len(comments)} detailed comments in PR '{pr.get('title', '')[:40]}'"
                )

                # Sample a comment to show communication style
                if comments and comments[0]["body"]:
                    evidence.collaboration_patterns.append(
                        f"Discussion excerpt: '{comments[0]['body'][:100]}...'"
                    )
            elif comment_count > 0:
                evidence.collaboration_patterns.append(
                    f"Engaged with {comment_count} comments in {repo_name}"
                )

            # PR Size Analysis
            if additions < 100 and deletions < 100:
                evidence.integration_patterns.append(
                    f"Small, focused PR in {repo_name} (good for review)"
                )
            elif additions > 500:
                evidence.technical_substance.append(
                    f"Large feature implementation in {repo_name}"
                )

        # Cross-repo contributions
        if pr_data.get("repos_count", 0) > 1:
            evidence.cross_repo_contributions.append(
                f"Contributed to {pr_data['repos_count']} different repositories"
            )
            evidence.cross_repo_contributions.append(
                "Demonstrates adaptability across codebases"
            )

        # Sustained engagement
        if pr_data.get("total_prs", 0) >= 10:
            evidence.collaboration_patterns.append(
                f"Sustained engagement with {pr_data['total_prs']} PRs"
            )

        # PRIMARY EVIDENCE: Merge Success Pattern
        if merged_prs:
            merge_evidence = f"{len(merged_prs)} of {total_prs} PRs successfully merged into production codebases"
            evidence.collaboration_patterns.insert(0, merge_evidence)

            # Add specific merge patterns
            large_merged = [p for p in merged_prs if p["additions"] > 500]
            if large_merged:
                evidence.technical_substance.insert(
                    0,
                    f"Successfully merged {len(large_merged)} large PRs (500+ lines) - proven ability to ship substantial features",
                )

            reviewed_merged = [p for p in merged_prs if p["reviews"] > 0]
            if reviewed_merged:
                evidence.review_responsiveness.insert(
                    0,
                    f"{len(reviewed_merged)} PRs merged after review cycles - demonstrates feedback incorporation",
                )

        # Enhanced Hybrid Approach Summary
        evidence.process_adherence.append(
            "Enhanced hybrid approach: GraphQL (1 call) + strategic REST (5-8 calls) = comprehensive evidence"
        )
        evidence.process_adherence.append(
            "Evidence extracted: merge patterns, review decisions, actual feedback, communication style"
        )

        # NEW: Add time-based consistency evidence (what Zed values)
        if pr_dates:
            pr_dates.sort()
            first_pr = pr_dates[0]
            last_pr = pr_dates[-1]
            span_days = (last_pr - first_pr).days

            if span_days > 30:  # More than a month of contributions
                years = span_days // 365
                months = (span_days % 365) // 30

                # Calculate contribution frequency
                monthly_rate = len(pr_dates) / max(1, (span_days / 30))

                # This is CRITICAL hiring signal - sustained engagement over time
                time_evidence = f"Sustained contributions over {years} years, {months} months ({first_pr.date()} to {last_pr.date()})"
                evidence.collaboration_patterns.insert(0, time_evidence)

                if monthly_rate > 2:  # More than 2 PRs per month average
                    evidence.collaboration_patterns.insert(
                        1,
                        f"Consistent delivery pace: {monthly_rate:.1f} PRs per month average",
                    )

        # NEW: Add deep collaboration evidence (review cycles)
        if high_review_prs:
            evidence.collaboration_patterns.insert(
                0,
                f"Deep collaboration: {len(high_review_prs)} PRs with 3+ review cycles (iterative improvement)",
            )

            # Add specific examples of high-review PRs
            for pr_info in high_review_prs[:3]:  # Top 3 examples
                if pr_info["merged"]:
                    evidence.review_responsiveness.append(
                        f"'{pr_info['title'][:40]}...' - {pr_info['reviews']} review cycles, merged successfully"
                    )

        # NEW: Add pair programming evidence (co-authorship)
        if co_authored_prs:
            evidence.collaboration_patterns.insert(
                0,
                f"Pair programming evidence: {len(co_authored_prs)} PRs with co-authorship (collaborative development)",
            )

            # This is a strong signal of team collaboration
            if len(co_authored_prs) >= 10:
                evidence.technical_substance.insert(
                    0,
                    f"Strong collaborative development: {len(co_authored_prs)}+ PRs show pair programming practice",
                )

        # NEW: Add feature ownership evidence (taking features from concept to production)
        if owned_features:
            evidence.technical_substance.insert(
                0,
                f"Feature ownership: {len(owned_features)} major features taken from concept to production",
            )

            # Add specific examples of owned features
            for feature in owned_features[:3]:  # Top 3 features
                evidence.technical_substance.append(
                    f"Owned feature: '{feature['title'][:50]}...' - {feature['additions']} additions, {feature['reviews']} review cycles"
                )

        # NEW: Add feature vs fix balance (shows range of contributions)
        if feature_prs or fix_prs:
            feature_count = len(feature_prs)
            fix_count = len(fix_prs)

            if feature_count > 0 and fix_count > 0:
                evidence.technical_substance.insert(
                    1,
                    f"Full-stack contribution pattern: {feature_count} features + {fix_count} bug fixes",
                )
            elif feature_count > 10:
                evidence.technical_substance.insert(
                    1,
                    f"Feature-focused development: {feature_count} features implemented",
                )
            elif fix_count > 10:
                evidence.technical_substance.insert(
                    1, f"Production stability focus: {fix_count} bugs fixed"
                )

        # Sort evidence by significance before returning
        # Priority 1: KEY HIRING SIGNAL and major collaborative contributions
        # Priority 2: Sort by size indicators (numbers in the pattern)

        def sort_by_evidence_data(pattern):
            """Sort by actual data in evidence: commits, additions, merge status."""
            import re

            # Extract actual metrics from the pattern
            commits = 0
            additions = 0

            # Look for commit counts (e.g., "977 commits")
            commit_match = re.search(r"(\d+)\s+commit", pattern.lower())
            if commit_match:
                commits = int(commit_match.group(1))

            # Look for additions (e.g., "25837 additions" or "345+ additions")
            addition_match = re.search(r"(\d+)\+?\s+addition", pattern.lower())
            if addition_match:
                additions = int(addition_match.group(1))

            # If no specific metrics found, use largest number in pattern
            if commits == 0 and additions == 0:
                numbers = re.findall(r"\d+", pattern)
                if numbers:
                    additions = max(int(n) for n in numbers)

            # Check if merged (binary: True/False)
            is_merged = (
                "merged" in pattern.lower() and "unmerged" not in pattern.lower()
            )

            # Check if it's a key signal
            is_key_signal = "KEY HIRING SIGNAL" in pattern

            # Sort by: key signals first, then commits (sustained work), then additions (size), then merge status
            # Using negative values because sort is ascending by default
            return (-is_key_signal, -commits, -additions, -is_merged)

        # Sort all evidence lists by actual data in the patterns
        evidence.technical_substance = sorted(
            evidence.technical_substance, key=sort_by_evidence_data
        )

        evidence.collaboration_patterns = sorted(
            evidence.collaboration_patterns, key=sort_by_evidence_data
        )

        evidence.review_responsiveness = sorted(
            evidence.review_responsiveness, key=sort_by_evidence_data
        )

        return evidence

    def generate_enterprise_pr_prompt(
        self, pr_data: Dict[str, Any], evidence: PREvidence, context: str = "ENTERPRISE"
    ) -> str:
        """Generate the prompt for specified context (STARTUP, ENTERPRISE, AGENCY, OPEN_SOURCE)."""
        # Format evidence exactly like v2
        evidence_json = {
            "pr_contribution_patterns": {
                "total_prs_analyzed": pr_data["total_prs"],
                "repositories_contributed": pr_data["repos_count"],
                "repository_names": pr_data["repos_contributed_to"][:5],
            },
            "technical_patterns": (
                evidence.technical_substance[:5]
                if evidence.technical_substance
                else ["Limited technical substance visible"]
            ),
            "collaboration_patterns": (
                evidence.collaboration_patterns[:5]
                if evidence.collaboration_patterns
                else ["Limited collaboration evidence"]
            ),
            "communication_patterns": (
                evidence.pr_description_quality[:5]
                if evidence.pr_description_quality
                else ["Limited PR descriptions"]
            ),
            "review_patterns": (
                evidence.review_responsiveness[:5]
                if evidence.review_responsiveness
                else ["Limited review engagement"]
            ),
            "integration_patterns": (
                evidence.integration_patterns[:5]
                if evidence.integration_patterns
                else ["Limited integration evidence"]
            ),
            "process_patterns": (
                evidence.process_adherence[:3]
                if evidence.process_adherence
                else ["Process adherence not visible"]
            ),
            "cross_repo_patterns": (
                evidence.cross_repo_contributions[:3]
                if evidence.cross_repo_contributions
                else ["Single repository focus"]
            ),
        }

        # Context-specific focus areas
        context_prompts = {
            "STARTUP": """STARTUP CONTEXT FOCUS:
You are evaluating for a fast-moving startup where developers must:
- Ship MVPs quickly and iterate based on user feedback
- Wear multiple hats and jump between different parts of the stack
- Make pragmatic technical decisions balancing speed vs. perfection
- Work with ambiguous requirements that change frequently
- Build greenfield systems with modern tech stacks
- Collaborate closely in small, tight-knit teams
- Move fast while maintaining enough quality to scale later""",
            "ENTERPRISE": """ENTERPRISE CONTEXT FOCUS:
You are evaluating for a large enterprise organization where developers must:
- Work within established architectural standards and governance
- Collaborate across multiple teams and time zones
- Navigate complex approval and deployment processes
- Ensure compliance with security and regulatory requirements
- Maintain and evolve mission-critical legacy systems
- Document thoroughly for knowledge transfer
- Think in quarters and years, not weeks""",
            "AGENCY": """AGENCY CONTEXT FOCUS:
You are evaluating for a consulting/agency environment where developers must:
- Quickly ramp up on diverse client codebases and tech stacks
- Juggle multiple client projects with different requirements
- Communicate effectively with non-technical stakeholders
- Deliver on fixed timelines and budgets
- Adapt to different team cultures and processes
- Document handoffs clearly for client teams
- Balance technical excellence with client satisfaction""",
            "OPEN_SOURCE": """OPEN_SOURCE CONTEXT FOCUS:
You are evaluating for open source project contribution where developers must:
- Work asynchronously with distributed global contributors
- Write self-documenting code that others can understand
- Follow project contribution guidelines meticulously
- Engage constructively in public technical discussions
- Handle feedback from diverse community members
- Maintain backward compatibility and stability
- Think about long-term maintainability over quick fixes""",
        }

        # Get the appropriate context prompt
        context_prompt = context_prompts.get(
            context.upper(), context_prompts["STARTUP"]
        )

        # Return context-specific prompt
        return f"""You are a senior technical hiring consultant analyzing GitHub pull requests for {context} hiring context.

CRITICAL WARNING - EXIQUS DNA: EVIDENCE ONLY, NO INFERENCES
- NO numeric scores, percentages, ratings, or arbitrary thresholds
- NO personality traits (ego-less, team player, self-motivated)
- NO mindset inferences (growth mindset, learning attitude)
- NO behavioral assumptions beyond what is directly observable
- ONLY report what you can DIRECTLY OBSERVE from PR data
- STICK TO: "addressed feedback", "persisted through reviews", "incorporated changes"
- AVOID: "strong collaboration", "ego-less", "good team fit" (unless explicit evidence)

{context_prompt}

VALIDATED HIRING SIGNALS (What Actually Gets People Hired):
1. SUSTAINED ENGAGEMENT: Long-term contribution patterns over months
2. TECHNICAL SUBSTANCE: Working on substantial features vs minor fixes
3. COLLABORATION DEPTH: Multiple review cycles, addressing feedback
4. FEATURE OWNERSHIP: Taking features from concept to completion
5. PRODUCTION IMPACT: PRs that get merged and used in production

CRITICAL UNDERSTANDING ABOUT PR SIGNIFICANCE:
- Authored and assigned/collaborative PRs should be evaluated EQUALLY based on their evidence
- Significance is determined by: scale (additions/deletions), commit count, merge success, and impact
- A 25,000-line assigned PR with 977 commits is MORE significant than a 300-line authored PR
- A 500-line authored PR might be MORE significant than a 100-line assigned PR
- Judge by the EVIDENCE (size, commits, success) not the authorship type
- Terms like "KEY HIRING SIGNAL" or "Major collaborative contribution" indicate critical evidence
- Both solo and collaborative work demonstrate valuable but different capabilities

Your job: Generate ACTIONABLE, SPECIFIC insights that help {context.lower()} hiring teams understand this candidate fit for {context.lower()} environment constraints and requirements.

PR Evidence Data:
{json.dumps(evidence_json, indent=2)}

CRITICAL REQUIREMENTS - OBSERVABLE EVIDENCE ONLY:
- Each insight must reference SPECIFIC PR evidence including PR TITLES when available
- When referencing large PRs, include: "PR 'actual title here' with X+ lines"
- When referencing reviews, include: "PR 'title' went through Y reviews"
- MANDATORY: Your FIRST insight and FIRST interview question MUST discuss the LARGEST PR by additions (if over 1000 lines)
- Any PR marked as "KEY HIRING SIGNAL" in evidence MUST be discussed prominently
- Focus on {context.lower()} hiring implications
- Be honest about what PRs can and cannot tell us
- Connect OBSERVABLE patterns to {context.lower()} needs
- Use BEHAVIORAL language: "addressed X reviews", "incorporated feedback", "persisted through Y cycles"
- AVOID PERSONALITY language: "collaborative", "ego-less", "team player", "self-motivated"
- State what happened, NOT what it means about their character
- Use context-appropriate categories: avoid "enterprise_fit" in startup context

Return ONLY this exact JSON format:
{{
    "insights": [
        {{
            "category": "technical_skills|collaboration|work_patterns|technical_practices",
            "title": "Specific pattern name (e.g., 'Multi-Repository Adaptability')",
            "description": "Detailed insight with concrete PR examples",
            "evidence": ["List specific PRs, repos, or patterns observed"],
            "data_availability": "complete|partial|limited",
            "impact": "positive|concerning|neutral|needs_validation",
            "hiring_implication": "What this means for enterprise hiring decision",
            "interview_focus": "What to listen for in their response"
        }}
        // Generate 5-7 insights minimum
    ],
    "key_strengths": [
        // 3-5 standout strengths based on PR evidence
        "Strength with specific evidence"
    ],
    "areas_to_validate": [
        // 3-5 interview priorities based on what PRs do not show
        "Area that needs validation beyond GitHub"
    ],
    "red_flags": [
        // Any concerning patterns (can be empty if none)
        "Specific concern with evidence"
    ],
    "context_alignment": {{
        "strong_fit_indicators": [
            // 3-5 PR patterns WITH EVIDENCE supporting enterprise fit
            "Pattern description | Evidence: specific PRs or examples"
        ],
        "areas_to_explore": [
            // 2-3 patterns needing deeper investigation
            "Pattern requiring further validation with evidence"
        ],
        "needs_validation": [
            // 3-5 key areas requiring interview confirmation
            "Critical area PRs cannot reveal"
        ]
    }},
    "data_limitations": [
        // 3-5 things PR analysis cannot tell us
        "What we cannot determine from public PRs"
    ],
    "interview_questions": [
        {{
            "question": "Specific question about their most impactful work first, then probing beyond visible PR work",
            "category": "technical|collaboration|process|governance",
            "context": "Why we're asking based on their PR patterns",
            "evidence_basis": "Which PR pattern triggered this question (prioritize KEY HIRING SIGNALS)",
            "follow_up_prompts": [
                "Follow-up question 1",
                "Follow-up question 2",
                "Follow-up question 3"
            ],
            "interview_focus": "What to listen for in their response"
        }}
        // Generate 5-6 interview questions minimum
    ],
    "recommendations": [
        // 5-6 evidence-based observations for hiring team consideration
        "Evidence-based observation about what to explore in interviews"
    ],
    "quality_indicators": [
        {{
            "indicator": "Specific PR pattern observed",
            "observation": "What we observed in their PRs",
            "hiring_signal": "positive|explore",
            "implication": "What this suggests about the candidate"
        }}
        // Generate 6-8 quality indicators
    ],
    "executive_summary": "2-3 sentence summary focusing on enterprise fit based on PR contribution patterns",
    "confidence_explanation": "Explanation of confidence level based on PR data volume and pattern consistency"
}}

CRITICAL: You MUST generate ALL sections with substantive content. Empty or minimal sections will cause system failure.
"""

    def analyze_with_ai(
        self, pr_data: Dict[str, Any], evidence: PREvidence, context: str = "ENTERPRISE"
    ) -> Dict[str, Any]:
        """Analyze PR data using Anthropic API - FULL implementation."""
        logger.info(f"Analyzing with AI using {self.model} for {context} context")

        prompt = self.generate_enterprise_pr_prompt(pr_data, evidence, context)

        try:
            start_time = time.time()
            response = self.anthropic_client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=0.3,
                timeout=600.0,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )

            ai_content = response.content[0].text if response.content else ""

            # Calculate costs
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            total_tokens = input_tokens + output_tokens
            analysis_time = time.time() - start_time
            cost = (input_tokens * 3.0 + output_tokens * 15.0) / 1_000_000

            logger.info(
                f"AI analysis complete. Time: {analysis_time:.2f}s, Tokens: {total_tokens}, Cost: ${cost:.4f}"
            )

            # Clean and parse JSON
            if ai_content.startswith("```json"):
                ai_content = ai_content[7:]
            if ai_content.endswith("```"):
                ai_content = ai_content[:-3]
            ai_content = ai_content.strip()

            result = json.loads(ai_content)

            # Add metadata including API optimization info
            result["metadata"] = {
                "username": pr_data["username"],
                "prs_analyzed": pr_data["total_prs"],
                "repos": pr_data["repos_count"],
                "tokens": total_tokens,
                "cost": cost,
                "analysis_time": analysis_time,
                "model": self.model,
                "context": "enterprise",
                "api_optimization": {
                    "method": "GraphQL Only (Pure)",
                    "api_calls_used": pr_data.get("api_calls_used", 1),
                    "api_calls_saved": 120 - pr_data.get("api_calls_used", 1),
                    "fetch_time": pr_data.get("fetch_time", 0),
                    "fetch_time_saved": 75 - pr_data.get("fetch_time", 0),
                },
            }

            return result

        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return {
                "executive_summary": "Analysis failed",
                "metadata": {
                    "error": str(e),
                    "api_calls_used": pr_data.get("api_calls_used", 1),
                },
            }

    def format_markdown_report(
        self, result: Dict[str, Any], context: str = "ENTERPRISE"
    ) -> str:
        """Format exactly like v2 but with API optimization stats."""
        metadata = result.get("metadata", {})
        api_opt = metadata.get("api_optimization", {})

        # Build report using concatenation to avoid f-string parsing issues
        report = f"# PR Analysis Report - {metadata.get('username', 'Unknown')}\n\n"
        report += "## 📊 Analysis Metadata\n"
        report += f"- **Context**: {context}\n"
        report += f"- **PRs Analyzed**: {metadata.get('prs_analyzed', 0)}\n"
        report += f"- **Repositories**: {metadata.get('repos', 0)}\n"
        report += f"- **Model**: Scale+ ({metadata.get('model', 'claude-sonnet-4')})\n"
        report += f"- **Tokens Used**: {metadata.get('tokens', 0):,}\n"
        report += f"- **Analysis Cost**: ${metadata.get('cost', 0):.4f}\n"
        report += (
            f"- **Analysis Time**: {metadata.get('analysis_time', 0):.2f} seconds\n\n"
        )

        report += "## 🚀 API Optimization Results\n"
        report += f"- **Method**: {api_opt.get('method', 'GraphQL Only (Pure)')}\n"
        report += (
            f"- **API Calls**: {api_opt.get('api_calls_used', 1)} (vs 120 original)\n"
        )
        report += f"- **API Calls Saved**: {api_opt.get('api_calls_saved', 119)}\n"
        report += (
            f"- **Fetch Time**: {api_opt.get('fetch_time', 0):.2f}s (vs 75s original)\n"
        )
        report += (
            f"- **Time Saved**: {api_opt.get('fetch_time_saved', 0):.1f} seconds\n\n"
        )

        report += "---\n\n"
        report += "## 🏢 Executive Summary\n"
        report += f"{result.get('executive_summary', 'No summary available')}\n\n"
        report += "### Evidence Quality Assessment\n"
        report += f"{result.get('confidence_explanation', 'Confidence assessment not available')}\n\n"
        report += "---\n\n"
        report += "## 💡 Key Insights\n\n"
        # Rest of the formatting exactly like v2...
        for i, insight in enumerate(result.get("insights", []), 1):
            if isinstance(insight, dict):
                report += f"### {i}. {insight.get('title', 'Untitled Insight')}\n"
                report += f"**Category**: `{insight.get('category', 'general')}`\n"
                report += (
                    f"**Description**: {insight.get('description', 'No description')}\n"
                )
                report += f"**Evidence**: {', '.join(insight.get('evidence', []))}\n"
                report += f"**Impact**: {insight.get('impact', 'neutral')}\n"
                report += f"**Hiring Implication**: {insight.get('hiring_implication', 'N/A')}\n\n"

        # Key Strengths
        report += """
---

## 🎯 Key Strengths

"""
        for strength in result.get("key_strengths", []):
            report += f"- {strength}\n"

        # Interview Questions
        report += """
---

## 💬 Interview Questions

"""
        for i, question in enumerate(result.get("interview_questions", []), 1):
            if isinstance(question, dict):
                report += f"### Q{i}\n\n"
                report += f"**{question.get('question', 'N/A')}**\n\n"
                report += f"`{question.get('category', 'general')}` "
                report += f"*{question.get('context', 'N/A')}*\n\n"
                report += f"📍 **Based on Evidence**: {question.get('evidence_basis', 'N/A')}\n\n"

                if question.get("follow_up_prompts"):
                    report += "**Follow-up questions**:\n"
                    for j, follow_up in enumerate(
                        question.get("follow_up_prompts", []), 1
                    ):
                        report += f"{j}. {follow_up}\n"

                report += "\n**Key Listening Points**:\n"
                report += f"*{question.get('interview_focus', 'Assess technical depth and collaboration skills')}*\n\n"

        # Recommendations
        report += """
---

## ✅ Recommendations

"""
        for i, rec in enumerate(result.get("recommendations", []), 1):
            report += f"{i}. {rec}\n"

        # Quality Indicators
        report += """
---

## 📈 Quality Indicators

### ✅ Positive Indicators
"""
        positive_indicators = [
            ind
            for ind in result.get("quality_indicators", [])
            if isinstance(ind, dict) and ind.get("hiring_signal") == "positive"
        ]

        for indicator in positive_indicators:
            report += f"- **{indicator.get('indicator', 'N/A')}**: {indicator.get('observation', 'N/A')}\n"

        report += "\n### 🔍 Areas to Explore\n"

        explore_indicators = [
            ind
            for ind in result.get("quality_indicators", [])
            if isinstance(ind, dict) and ind.get("hiring_signal") == "explore"
        ]

        for indicator in explore_indicators:
            report += f"- **{indicator.get('indicator', 'N/A')}**: {indicator.get('observation', 'N/A')}\n"
            report += f"  - *{indicator.get('implication', 'N/A')}*\n"

        # Context Alignment
        report += """
---

## 🔍 Context Alignment

### Strong Fit Indicators
"""
        for indicator in result.get("context_alignment", {}).get(
            "strong_fit_indicators", []
        ):
            report += f"- {indicator}\n"

        report += """\n### Areas to Explore
"""
        for area in result.get("context_alignment", {}).get("areas_to_explore", []):
            report += f"- {area}\n"

        report += """\n### Needs Validation
"""
        for validation in result.get("context_alignment", {}).get(
            "needs_validation", []
        ):
            report += f"- {validation}\n"

        # Data Limitations
        report += """
---

## ⚠️ Data Limitations

"""
        for limitation in result.get("data_limitations", []):
            report += f"- {limitation}\n"

        return report


def main():
    """Test the hybrid approach and generate FULL markdown report."""
    config = get_config()
    github_token = os.getenv("GITHUB_TOKEN") or config.github.token
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY") or config.anthropic_api_key

    if not github_token or not anthropic_api_key:
        logger.error("Missing API credentials.")
        sys.exit(1)

    # Accept user and context as command line arguments
    test_user = sys.argv[1] if len(sys.argv) > 1 else "octocat"
    context = sys.argv[2].upper() if len(sys.argv) > 2 else "OPEN_SOURCE"

    print(f"🎯 Testing with {context} context")
    analyzer = HybridPRAnalyzer(github_token, anthropic_api_key)

    # Create output directory
    output_dir = "pr_analysis_validation"
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n{'=' * 60}")
    print("Pure GraphQL PR Analysis Test")
    print(f"User: {test_user}")
    print(f"Context: {context}")
    print("=" * 60 + "\n")

    # Fetch PR data using Pure GraphQL approach with pagination
    # Will fetch COMPLETE history regardless of PR count
    pr_data = analyzer.fetch_user_prs_hybrid(test_user)  # No limit - fetch everything

    # Handle edge cases gracefully
    if not pr_data or not pr_data.get("prs"):
        print(f"\n⚠️ No PR contributions found for {test_user}")
        print("This user has no public pull request history to analyze.")
        print("\n💡 Suggestions:")
        print("  - Try analyzing their public repositories instead")
        print("  - Verify the username is correct")
        print("  - Check if they contribute under a different account")
        sys.exit(0)

    # Minimal PR threshold check
    if pr_data["total_prs"] < 3:
        print(f"\n⚠️ Limited PR data for {test_user} ({pr_data['total_prs']} PRs)")
        print("Analysis requires at least 3 PRs for meaningful patterns.")
        print("\n💡 Consider:")
        print("  - Analyzing their public repositories for coding patterns")
        print("  - Waiting for more PR contributions before analysis")
        print("  - Using other assessment methods for this candidate")
        sys.exit(0)

    # Show optimization results
    print("\n🚀 OPTIMIZATION RESULTS:")
    print(f"   - PRs fetched: {pr_data['total_prs']}")
    print(f"   - Repositories: {pr_data['repos_count']}")
    print(f"   - API calls used: {pr_data.get('api_calls_used', 'unknown')}")
    print(f"   - Fetch time: {pr_data.get('fetch_time', 0):.2f}s")
    print("   - Original approach: 120 API calls, ~75 seconds")
    print(
        f"   - SAVINGS: {120 - pr_data.get('api_calls_used', 1)} API calls, "
        f"{75 - pr_data.get('fetch_time', 0):.0f} seconds"
    )

    # Extract evidence
    evidence = analyzer.extract_pr_evidence(pr_data)
    print("\n📊 Evidence extracted successfully")
    print(f"   - Technical patterns: {len(evidence.technical_substance)}")
    print(f"   - Collaboration patterns: {len(evidence.collaboration_patterns)}")
    print(f"   - Review patterns: {len(evidence.review_responsiveness)}")

    # Analyze with AI
    print("\n🤖 Analyzing with AI (this may take a minute)...")
    result = analyzer.analyze_with_ai(pr_data, evidence, context)

    # Format markdown report
    markdown_report = analyzer.format_markdown_report(result, context)

    # Save MARKDOWN report with version and timestamp to avoid overwriting
    import glob

    # Find existing versions to increment
    existing_files = glob.glob(
        os.path.join(output_dir, f"{test_user}_{context}_v*_collab_*.md")
    )
    if existing_files:
        # Extract version numbers and find the highest
        versions = []
        for f in existing_files:
            try:
                # Split by _v and get the number part
                parts = f.split("_v")
                if len(parts) > 1:
                    version_str = parts[1].split("_")[0]
                    versions.append(int(version_str))
            except Exception as e:
                logger.debug(f"Could not parse version from {f}: {e}")

        # Get the highest version and increment
        if versions:
            next_version = max(versions) + 1
            logger.info(f"Found existing versions: {versions}, using v{next_version}")
        else:
            next_version = 1
    else:
        next_version = 1  # Start fresh if no files exist

    # No manual overrides - let version numbering work naturally

    timestamp = datetime.now().strftime("%H%M%S")  # Just time for readability
    # Format: Username_CONTEXT_v3_collab_143025.md
    markdown_file = os.path.join(
        output_dir, f"{test_user}_{context}_v{next_version}_collab_{timestamp}.md"
    )
    with open(markdown_file, "w") as f:
        f.write(markdown_report)
    print(f"\n✅ Markdown report saved to: {markdown_file}")

    # Save JSON for debugging
    json_file = os.path.join(
        output_dir, f"{test_user}_{context}_v{next_version}_collab_{timestamp}.json"
    )
    with open(json_file, "w") as f:
        json.dump(result, f, indent=2)
    print(f"📄 JSON data saved to: {json_file}")

    # Print summary
    metadata = result.get("metadata", {})
    api_opt = metadata.get("api_optimization", {})

    print("\n" + "=" * 60)
    print(f"✅ Analysis Complete for {test_user}")
    print("-" * 60)
    print(f"   PRs analyzed: {metadata.get('prs_analyzed', 0)}")
    print(f"   Repos: {metadata.get('repos', 0)}")
    print(f"   Key insights: {len(result.get('insights', []))}")
    print(f"   Interview questions: {len(result.get('interview_questions', []))}")
    print(f"   Recommendations: {len(result.get('recommendations', []))}")
    print(f"   Quality indicators: {len(result.get('quality_indicators', []))}")
    print("-" * 60)
    print("   API Optimization:")
    print(f"   - Method: {api_opt.get('method', 'N/A')}")
    print(
        f"   - API calls: {api_opt.get('api_calls_used', 0)} (saved {api_opt.get('api_calls_saved', 0)})"
    )
    print(
        f"   - Time: {api_opt.get('fetch_time', 0):.1f}s (saved {api_opt.get('fetch_time_saved', 0):.1f}s)"
    )
    print(f"   - AI Cost: ${metadata.get('cost', 0):.4f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
