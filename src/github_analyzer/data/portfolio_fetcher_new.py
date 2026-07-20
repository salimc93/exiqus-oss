# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

# This is a draft of the new _fetch_repos_graphql implementation with 3-tier fallback
import logging
from typing import Any, Dict, List

import requests

logger = logging.getLogger(__name__)


def _get_simplified_query_template(self: Any, batch_size: int) -> str:
    """
    Get simplified GraphQL query without heavy fields.

    Used as fallback for users with large portfolios when full query causes 502.
    Removes: README, fileStructure, repositoryTopics, licenseInfo
    Keeps: All core analysis fields (languages, commits, dates, stars)
    """
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
            name
            nameWithOwner
            description
            url
            createdAt
            updatedAt
            pushedAt
            stargazerCount
            forkCount
            watchers {{ totalCount }}
            isArchived
            isFork
            isPrivate
            diskUsage
            openIssues: issues(states: OPEN) {{ totalCount }}
            hasWikiEnabled
            hasPages: homepageUrl
            primaryLanguage {{ name }}
            languages(first: 10) {{
              edges {{
                node {{ name }}
                size
              }}
            }}
            defaultBranchRef {{
              target {{
                ... on Commit {{
                  history(first: 1) {{
                    totalCount
                  }}
                  committedDate
                }}
              }}
            }}
          }}
        }}
      }}
    }}
    """


def _get_full_query_template(self: Any, batch_size: int) -> str:
    """Get full GraphQL query with all fields including README, fileStructure, etc."""
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
            name
            nameWithOwner
            description
            url
            createdAt
            updatedAt
            pushedAt
            stargazerCount
            forkCount
            watchers {{ totalCount }}
            isArchived
            isFork
            isPrivate
            diskUsage
            openIssues: issues(states: OPEN) {{ totalCount }}
            hasWikiEnabled
            hasPages: homepageUrl
            primaryLanguage {{ name }}
            languages(first: 10) {{
              edges {{
                node {{ name }}
                size
              }}
            }}
            licenseInfo {{
              name
              spdxId
            }}
            defaultBranchRef {{
              target {{
                ... on Commit {{
                  history(first: 1) {{
                    totalCount
                  }}
                  committedDate
                }}
              }}
            }}
            repositoryTopics(first: 10) {{
              nodes {{
                topic {{ name }}
              }}
            }}
            readme: object(expression: "HEAD:README.md") {{
              ... on Blob {{
                text
                byteSize
              }}
            }}
            fileStructure: object(expression: "HEAD:") {{
              ... on Tree {{
                entries {{
                  name
                  type
                  object {{
                    ... on Blob {{
                      byteSize
                    }}
                  }}
                }}
              }}
            }}
          }}
        }}
      }}
    }}
    """


def _fetch_repos_graphql(self: Any, username: str, max_repos: int) -> Dict[str, Any]:
    """
    Fetch developer's public repos using GraphQL with 3-tier fallback strategy.

    Fallback tiers:
    1. Full query, batch_size=30 (best quality, works for most users)
    2. Full query, batch_size=10 (if 502: smaller batches, same quality)
    3. Simple query, batch_size=10 (if 502: remove heavy fields, 90% quality)
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

    return result  # type: ignore[no-any-return]


def _fetch_repos_with_config(
    self: Any, username: str, max_repos: int, batch_size: int, use_simple: bool
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
    # Select query template
    if use_simple:
        query = self._get_simplified_query_template(batch_size)
        logger.info(f"Using simplified query (no README/fileStructure) for {username}")
    else:
        query = self._get_full_query_template(batch_size)

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
                error_code = "api_502" if response.status_code == 502 else "api_error"
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
                if any("Could not resolve to a User" in msg for msg in error_messages):
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
                f"(total: {len(repos)}/{total_count}, batch_size={batch_size})"
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
