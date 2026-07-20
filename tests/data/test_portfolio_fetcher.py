"""Tests for PortfolioFetcher - GraphQL data fetching.

Following the Orchestration Principle:
- Test the contract, not implementation
- Verify correct GraphQL queries are constructed
- Verify response parsing and error handling
- Test 3-tier fallback strategy orchestration
- NO SCORES OR RATINGS - data fetching only
"""

from typing import Any, Dict
from unittest.mock import Mock, patch

import pytest
import requests

from github_analyzer.data.portfolio_fetcher import PortfolioFetcher
from github_analyzer.data.portfolio_models import PortfolioFetchResult, RepoData


@pytest.fixture
def mock_github_token() -> str:
    """Mock GitHub token for testing."""
    return "ghp_test_token_abc123"


@pytest.fixture
def mock_graphql_response() -> Dict[str, Any]:
    """Mock successful GraphQL response with repo data."""
    return {
        "data": {
            "user": {
                "repositories": {
                    "totalCount": 2,
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [
                        {
                            "name": "test-repo-1",
                            "nameWithOwner": "testuser/test-repo-1",
                            "description": "A test repository",
                            "url": "https://github.com/testuser/test-repo-1",
                            "createdAt": "2023-01-01T00:00:00Z",
                            "updatedAt": "2024-12-01T00:00:00Z",
                            "pushedAt": "2024-12-01T00:00:00Z",
                            "stargazerCount": 10,
                            "forkCount": 2,
                            "watchers": {"totalCount": 5},
                            "isArchived": False,
                            "isFork": False,
                            "isPrivate": False,
                            "diskUsage": 500,
                            "openIssues": {"totalCount": 3},
                            "hasWikiEnabled": True,
                            "hasPages": "https://testuser.github.io/test-repo-1",
                            "primaryLanguage": {"name": "Python"},
                            "languages": {
                                "edges": [
                                    {"node": {"name": "Python"}, "size": 45000},
                                    {"node": {"name": "Shell"}, "size": 2000},
                                ]
                            },
                            "defaultBranchRef": {
                                "target": {
                                    "history": {"totalCount": 25},
                                    "committedDate": "2024-12-01T00:00:00Z",
                                }
                            },
                            "licenseInfo": {"name": "MIT License", "spdxId": "MIT"},
                            "repositoryTopics": {
                                "nodes": [
                                    {"topic": {"name": "python"}},
                                    {"topic": {"name": "testing"}},
                                ]
                            },
                            "readme": {
                                "text": "# Test Repo\n\nThis is a test.",
                                "byteSize": 100,
                            },
                            "fileStructure": {
                                "entries": [
                                    {"name": "tests", "type": "tree"},
                                    {"name": "src", "type": "tree"},
                                    {"name": ".github", "type": "tree"},
                                ]
                            },
                        },
                        {
                            "name": "test-repo-2",
                            "nameWithOwner": "testuser/test-repo-2",
                            "description": "Another test repository",
                            "url": "https://github.com/testuser/test-repo-2",
                            "createdAt": "2023-06-15T00:00:00Z",
                            "updatedAt": "2024-11-20T00:00:00Z",
                            "pushedAt": "2024-11-20T00:00:00Z",
                            "stargazerCount": 5,
                            "forkCount": 1,
                            "watchers": {"totalCount": 3},
                            "isArchived": False,
                            "isFork": False,
                            "isPrivate": False,
                            "diskUsage": 300,
                            "openIssues": {"totalCount": 1},
                            "hasWikiEnabled": False,
                            "hasPages": None,
                            "primaryLanguage": {"name": "TypeScript"},
                            "languages": {
                                "edges": [
                                    {"node": {"name": "TypeScript"}, "size": 30000}
                                ]
                            },
                            "defaultBranchRef": {
                                "target": {
                                    "history": {"totalCount": 15},
                                    "committedDate": "2024-11-20T00:00:00Z",
                                }
                            },
                            "licenseInfo": None,
                            "repositoryTopics": {"nodes": []},
                            "readme": None,
                            "fileStructure": None,
                        },
                    ],
                }
            }
        }
    }


@pytest.fixture
def mock_graphql_response_with_skips() -> Dict[str, Any]:
    """Mock GraphQL response including repos that should be skipped."""
    return {
        "data": {
            "user": {
                "repositories": {
                    "totalCount": 5,
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [
                        # Valid repo
                        {
                            "name": "valid-repo",
                            "nameWithOwner": "testuser/valid-repo",
                            "description": "Valid repository",
                            "url": "https://github.com/testuser/valid-repo",
                            "createdAt": "2023-01-01T00:00:00Z",
                            "updatedAt": "2024-12-01T00:00:00Z",
                            "pushedAt": "2024-12-01T00:00:00Z",
                            "stargazerCount": 10,
                            "forkCount": 2,
                            "watchers": {"totalCount": 5},
                            "isArchived": False,
                            "isFork": False,
                            "isPrivate": False,
                            "diskUsage": 500,
                            "openIssues": {"totalCount": 3},
                            "hasWikiEnabled": True,
                            "hasPages": None,
                            "primaryLanguage": {"name": "Python"},
                            "languages": {
                                "edges": [{"node": {"name": "Python"}, "size": 45000}]
                            },
                            "defaultBranchRef": {
                                "target": {
                                    "history": {"totalCount": 25},
                                    "committedDate": "2024-12-01T00:00:00Z",
                                }
                            },
                        },
                        # Fork - should be skipped
                        {
                            "name": "forked-repo",
                            "nameWithOwner": "testuser/forked-repo",
                            "isFork": True,
                            "isArchived": False,
                            "diskUsage": 500,
                            "defaultBranchRef": {
                                "target": {"history": {"totalCount": 100}}
                            },
                        },
                        # Archived - should be skipped
                        {
                            "name": "archived-repo",
                            "nameWithOwner": "testuser/archived-repo",
                            "isFork": False,
                            "isArchived": True,
                            "diskUsage": 500,
                            "defaultBranchRef": {
                                "target": {"history": {"totalCount": 100}}
                            },
                        },
                        # Valid repo - with LOC-based filtering (<=5 repos, lenient=50 LOC), this passes
                        {
                            "name": "tiny-repo",
                            "nameWithOwner": "testuser/tiny-repo",
                            "description": "Tiny learning repo",
                            "url": "https://github.com/testuser/tiny-repo",
                            "createdAt": "2023-06-01T00:00:00Z",
                            "updatedAt": "2023-06-15T00:00:00Z",
                            "pushedAt": "2023-06-15T00:00:00Z",
                            "stargazerCount": 0,
                            "forkCount": 0,
                            "watchers": {"totalCount": 0},
                            "isFork": False,
                            "isArchived": False,
                            "isPrivate": False,
                            "diskUsage": 5,
                            "openIssues": {"totalCount": 0},
                            "hasWikiEnabled": False,
                            "hasPages": None,
                            "primaryLanguage": {"name": "Python"},
                            "languages": {
                                "edges": [
                                    {"node": {"name": "Python"}, "size": 5000}
                                ]  # 100 LOC
                            },
                            "defaultBranchRef": {
                                "target": {
                                    "history": {"totalCount": 100},
                                    "committedDate": "2023-06-15T00:00:00Z",
                                }
                            },
                        },
                        # Valid repo - with LOC-based filtering (<=5 repos, lenient=50 LOC), this passes
                        {
                            "name": "low-commit-repo",
                            "nameWithOwner": "testuser/low-commit-repo",
                            "description": "Learning basics",
                            "url": "https://github.com/testuser/low-commit-repo",
                            "createdAt": "2023-03-01T00:00:00Z",
                            "updatedAt": "2023-03-10T00:00:00Z",
                            "pushedAt": "2023-03-10T00:00:00Z",
                            "stargazerCount": 0,
                            "forkCount": 0,
                            "watchers": {"totalCount": 0},
                            "isFork": False,
                            "isArchived": False,
                            "isPrivate": False,
                            "diskUsage": 500,
                            "openIssues": {"totalCount": 0},
                            "hasWikiEnabled": False,
                            "hasPages": None,
                            "primaryLanguage": {"name": "Java"},
                            "languages": {
                                "edges": [
                                    {"node": {"name": "Java"}, "size": 30000}
                                ]  # 600 LOC
                            },
                            "defaultBranchRef": {
                                "target": {
                                    "history": {
                                        "totalCount": 3
                                    },  # Commit count is IGNORED now
                                    "committedDate": "2023-03-10T00:00:00Z",
                                }
                            },
                        },
                    ],
                }
            }
        }
    }


class TestPortfolioFetcher:
    """Test PortfolioFetcher orchestration and data fetching."""

    def test_fetcher_initialization_with_token(self, mock_github_token):
        """Test that fetcher initializes correctly with token."""
        fetcher = PortfolioFetcher(github_token=mock_github_token)

        assert fetcher.token == mock_github_token
        assert fetcher.graphql_url == "https://api.github.com/graphql"
        assert fetcher.session is not None
        assert "Authorization" in fetcher.session.headers
        assert fetcher.session.headers["Authorization"] == f"Bearer {mock_github_token}"

    def test_fetcher_initialization_without_token_raises_error(self):
        """Test that fetcher raises error when no token provided."""
        with patch("github_analyzer.data.portfolio_fetcher.get_config") as mock_config:
            mock_config.return_value.github_token = None

            with pytest.raises(ValueError, match="GitHub token is required"):
                PortfolioFetcher()

    def test_fetch_user_portfolio_success(
        self, mock_github_token, mock_graphql_response
    ):
        """Test successful portfolio fetching with valid data."""
        with patch("requests.Session.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_graphql_response

            fetcher = PortfolioFetcher(github_token=mock_github_token)
            result = fetcher.fetch_user_portfolio("testuser", max_repos=100)

            # Verify result structure
            assert isinstance(result, PortfolioFetchResult)
            assert result.username == "testuser"
            assert result.total_public_repos == 2
            assert result.repos_fetched == 2
            assert result.repos_skipped == 0
            assert result.api_calls_used >= 1
            assert result.fetch_time_seconds >= 0  # Time can be very small in tests

            # Verify repos were parsed correctly
            assert len(result.repos) == 2
            assert all(isinstance(repo, RepoData) for repo in result.repos)

            # Verify first repo data
            repo1 = result.repos[0]
            assert repo1.name == "test-repo-1"
            assert repo1.primary_language == "Python"
            assert repo1.total_commits == 25
            assert repo1.has_tests is True  # Has "tests" folder
            assert repo1.has_ci is True  # Has ".github" folder

    def test_fetch_user_portfolio_with_repo_filtering(
        self, mock_github_token, mock_graphql_response_with_skips
    ):
        """Test that repos are correctly filtered based on skip criteria.

        This test has 5 total repos, so adaptive filtering applies lenient thresholds:
        - min_loc_threshold = 50 LOC (lenient tier)
        - commit count is IGNORED (removed in LOC-based approach)

        tiny-repo: 5,000 bytes = 100 LOC (PASSES >=50 threshold)
        low-commit-repo: 30,000 bytes = 600 LOC (PASSES >=50 threshold)
        Only forks and archived repos are skipped.
        """
        with patch("requests.Session.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_graphql_response_with_skips

            fetcher = PortfolioFetcher(github_token=mock_github_token)
            result = fetcher.fetch_user_portfolio("testuser", max_repos=100)

            # Verify 3 repos were kept (2 skipped: fork + archived)
            # With LOC-based filtering (<=5 repos, lenient), tiny-repo (100 LOC) and low-commit-repo (600 LOC) pass
            assert result.repos_fetched == 3
            assert result.repos_skipped == 2

            # Verify skip reasons (only forks and archived)
            assert result.skip_reasons["forks"] == 1
            assert result.skip_reasons["archived"] == 1
            assert (
                result.skip_reasons["trivial_size"] == 0
            )  # 100 LOC passes >=50 threshold
            assert result.skip_reasons["total_skipped"] == 2

            # Verify skipped repos tracking
            assert "forked-repo" in result.skipped_repos["forks"]
            assert "archived-repo" in result.skipped_repos["archived"]
            assert len(result.skipped_repos["trivial_size"]) == 0

    def test_fetch_user_not_found(self, mock_github_token):
        """Test handling of user not found error."""
        error_response = {
            "errors": [
                {
                    "message": "Could not resolve to a User with the login of 'nonexistent'"
                }
            ]
        }

        with patch("requests.Session.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = error_response

            fetcher = PortfolioFetcher(github_token=mock_github_token)

            with pytest.raises(ValueError, match="GitHub user 'nonexistent' not found"):
                fetcher.fetch_user_portfolio("nonexistent", max_repos=100)

    def test_fetch_with_502_error_triggers_fallback(self, mock_github_token):
        """Test that 502 errors trigger fallback to smaller batch size."""
        # Create mock response for successful retry
        success_response = {
            "data": {
                "user": {
                    "repositories": {
                        "totalCount": 0,
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": [],
                    }
                }
            }
        }

        with patch("requests.Session.post") as mock_post:
            # First call returns 502 error (batch_size=30)
            mock_response_502 = Mock()
            mock_response_502.status_code = 502
            mock_response_502.text = "Bad Gateway"

            # Second call succeeds (batch_size=10)
            mock_response_success = Mock()
            mock_response_success.status_code = 200
            mock_response_success.json = Mock(return_value=success_response)

            mock_post.side_effect = [mock_response_502, mock_response_success]

            fetcher = PortfolioFetcher(github_token=mock_github_token)
            result = fetcher.fetch_user_portfolio("testuser", max_repos=100)

            # Verify fallback was triggered (2 HTTP calls made total)
            assert mock_post.call_count == 2
            # api_calls_used reflects only successful attempt's count
            assert result.api_calls_used >= 1
            assert result.repos_fetched == 0  # Empty result from fallback

    def test_fetch_with_pagination(self, mock_github_token):
        """Test pagination handling across multiple GraphQL requests."""
        # First page response
        page1_response = {
            "data": {
                "user": {
                    "repositories": {
                        "totalCount": 2,
                        "pageInfo": {
                            "hasNextPage": True,
                            "endCursor": "cursor123",
                        },
                        "nodes": [
                            {
                                "name": "repo-1",
                                "nameWithOwner": "testuser/repo-1",
                                "url": "https://github.com/testuser/repo-1",
                                "createdAt": "2023-01-01T00:00:00Z",
                                "updatedAt": "2024-12-01T00:00:00Z",
                                "pushedAt": "2024-12-01T00:00:00Z",
                                "stargazerCount": 10,
                                "forkCount": 2,
                                "watchers": {"totalCount": 5},
                                "isArchived": False,
                                "isFork": False,
                                "isPrivate": False,
                                "diskUsage": 500,
                                "openIssues": {"totalCount": 3},
                                "hasWikiEnabled": True,
                                "hasPages": None,
                                "primaryLanguage": {"name": "Python"},
                                "languages": {
                                    "edges": [
                                        {"node": {"name": "Python"}, "size": 45000}
                                    ]
                                },
                                "defaultBranchRef": {
                                    "target": {
                                        "history": {"totalCount": 25},
                                        "committedDate": "2024-12-01T00:00:00Z",
                                    }
                                },
                            }
                        ],
                    }
                }
            }
        }

        # Second page response
        page2_response = {
            "data": {
                "user": {
                    "repositories": {
                        "totalCount": 2,
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": [
                            {
                                "name": "repo-2",
                                "nameWithOwner": "testuser/repo-2",
                                "url": "https://github.com/testuser/repo-2",
                                "createdAt": "2023-06-01T00:00:00Z",
                                "updatedAt": "2024-11-01T00:00:00Z",
                                "pushedAt": "2024-11-01T00:00:00Z",
                                "stargazerCount": 5,
                                "forkCount": 1,
                                "watchers": {"totalCount": 3},
                                "isArchived": False,
                                "isFork": False,
                                "isPrivate": False,
                                "diskUsage": 300,
                                "openIssues": {"totalCount": 1},
                                "hasWikiEnabled": False,
                                "hasPages": None,
                                "primaryLanguage": {"name": "TypeScript"},
                                "languages": {
                                    "edges": [
                                        {"node": {"name": "TypeScript"}, "size": 30000}
                                    ]
                                },
                                "defaultBranchRef": {
                                    "target": {
                                        "history": {"totalCount": 15},
                                        "committedDate": "2024-11-01T00:00:00Z",
                                    }
                                },
                            }
                        ],
                    }
                }
            }
        }

        with patch("requests.Session.post") as mock_post:
            # Return different responses for each call
            mock_post.side_effect = [
                Mock(status_code=200, json=lambda: page1_response),
                Mock(status_code=200, json=lambda: page2_response),
            ]

            fetcher = PortfolioFetcher(github_token=mock_github_token)
            result = fetcher.fetch_user_portfolio("testuser", max_repos=100)

            # Verify pagination worked correctly
            assert mock_post.call_count == 2
            assert result.api_calls_used == 2
            assert result.repos_fetched == 2
            assert len(result.repos) == 2

            # Verify repos from both pages
            assert result.repos[0].name == "repo-1"
            assert result.repos[1].name == "repo-2"

    def test_fetch_respects_max_repos_limit(self, mock_github_token):
        """Test that fetcher respects max_repos parameter."""
        # Response with 3 repos
        response = {
            "data": {
                "user": {
                    "repositories": {
                        "totalCount": 3,
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": [
                            {
                                "name": f"repo-{i}",
                                "nameWithOwner": f"testuser/repo-{i}",
                                "url": f"https://github.com/testuser/repo-{i}",
                                "createdAt": "2023-01-01T00:00:00Z",
                                "updatedAt": "2024-12-01T00:00:00Z",
                                "pushedAt": "2024-12-01T00:00:00Z",
                                "stargazerCount": 10,
                                "forkCount": 2,
                                "watchers": {"totalCount": 5},
                                "isArchived": False,
                                "isFork": False,
                                "isPrivate": False,
                                "diskUsage": 500,
                                "openIssues": {"totalCount": 3},
                                "hasWikiEnabled": True,
                                "hasPages": None,
                                "primaryLanguage": {"name": "Python"},
                                "languages": {
                                    "edges": [
                                        {"node": {"name": "Python"}, "size": 45000}
                                    ]
                                },
                                "defaultBranchRef": {
                                    "target": {
                                        "history": {"totalCount": 25},
                                        "committedDate": "2024-12-01T00:00:00Z",
                                    }
                                },
                            }
                            for i in range(1, 4)
                        ],
                    }
                }
            }
        }

        with patch("requests.Session.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = response

            fetcher = PortfolioFetcher(github_token=mock_github_token)
            result = fetcher.fetch_user_portfolio("testuser", max_repos=2)

            # Verify only 2 repos returned despite 3 available
            assert result.repos_fetched == 2
            assert len(result.repos) == 2

    def test_process_repos_parses_language_data_correctly(
        self, mock_github_token, mock_graphql_response
    ):
        """Test that language data is correctly parsed from GraphQL response."""
        with patch("requests.Session.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_graphql_response

            fetcher = PortfolioFetcher(github_token=mock_github_token)
            result = fetcher.fetch_user_portfolio("testuser", max_repos=100)

            # Verify language parsing
            repo1 = result.repos[0]
            assert repo1.primary_language == "Python"
            assert "Python" in repo1.languages
            assert "Shell" in repo1.languages
            assert repo1.languages["Python"] == 45000
            assert repo1.languages["Shell"] == 2000

    def test_process_repos_detects_key_files_correctly(
        self, mock_github_token, mock_graphql_response
    ):
        """Test that key files (tests, CI, Docker) are detected correctly."""
        with patch("requests.Session.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_graphql_response

            fetcher = PortfolioFetcher(github_token=mock_github_token)
            result = fetcher.fetch_user_portfolio("testuser", max_repos=100)

            # Verify key file detection
            repo1 = result.repos[0]
            assert repo1.has_tests is True  # Has "tests" folder
            assert repo1.has_ci is True  # Has ".github" folder
            assert repo1.has_docker is False  # No Docker files

    def test_process_repos_handles_missing_optional_fields(self, mock_github_token):
        """Test that repos with missing optional fields are processed correctly."""
        minimal_response = {
            "data": {
                "user": {
                    "repositories": {
                        "totalCount": 1,
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": [
                            {
                                "name": "minimal-repo",
                                "nameWithOwner": "testuser/minimal-repo",
                                "url": "https://github.com/testuser/minimal-repo",
                                "createdAt": "2023-01-01T00:00:00Z",
                                "updatedAt": "2024-12-01T00:00:00Z",
                                "pushedAt": "2024-12-01T00:00:00Z",
                                "stargazerCount": 0,
                                "forkCount": 0,
                                "watchers": {"totalCount": 0},
                                "isArchived": False,
                                "isFork": False,
                                "isPrivate": False,
                                "diskUsage": 100,
                                "openIssues": {"totalCount": 0},
                                "hasWikiEnabled": False,
                                "hasPages": None,
                                "primaryLanguage": None,  # No primary language
                                "languages": {"edges": []},  # No languages
                                "defaultBranchRef": {
                                    "target": {
                                        "history": {"totalCount": 10},
                                        "committedDate": "2024-12-01T00:00:00Z",
                                    }
                                },
                                # Missing optional fields
                                "licenseInfo": None,
                                "repositoryTopics": None,
                                "readme": None,
                                "fileStructure": None,
                            }
                        ],
                    }
                }
            }
        }

        with patch("requests.Session.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = minimal_response

            fetcher = PortfolioFetcher(github_token=mock_github_token)
            result = fetcher.fetch_user_portfolio("testuser", max_repos=100)

            # Verify repo was processed despite missing fields
            assert result.repos_fetched == 1
            repo = result.repos[0]
            assert repo.name == "minimal-repo"
            assert repo.primary_language is None
            assert repo.languages == {}
            assert repo.topics == []
            assert repo.has_license is False
            assert repo.has_tests is False
            assert repo.has_ci is False

    def test_fetch_timeout_handling(self, mock_github_token):
        """Test that timeout errors are handled gracefully."""
        with patch("requests.Session.post") as mock_post:
            mock_post.side_effect = requests.exceptions.Timeout("Request timeout")

            fetcher = PortfolioFetcher(github_token=mock_github_token)
            result = fetcher.fetch_user_portfolio("testuser", max_repos=100)

            # Verify graceful handling (empty result, no crash)
            assert result.repos_fetched == 0
            assert len(result.repos) == 0

    def test_no_scores_in_fetched_data(self, mock_github_token, mock_graphql_response):
        """Test that fetched data contains NO SCORES OR RATINGS (evidence-based only)."""
        with patch("requests.Session.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_graphql_response

            fetcher = PortfolioFetcher(github_token=mock_github_token)
            result = fetcher.fetch_user_portfolio("testuser", max_repos=100)

            # Verify no scoring fields exist
            for repo in result.repos:
                # Check that no score-related attributes exist
                repo_dict = vars(repo)
                assert "score" not in str(repo_dict).lower()
                assert "rating" not in str(repo_dict).lower()
                assert "metric" not in str(repo_dict).lower()

                # Verify only evidence-based fields exist
                assert hasattr(repo, "total_commits")  # Evidence: commit count
                assert hasattr(repo, "languages")  # Evidence: languages used
                assert hasattr(repo, "has_tests")  # Evidence: testing infrastructure
                assert hasattr(repo, "has_ci")  # Evidence: CI/CD setup
