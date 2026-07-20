"""
Tests for GitHub PR fetcher with GraphQL.
"""

from datetime import timezone
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.github_analyzer.data.pr_fetcher import PRFetcher
from src.github_analyzer.data.pr_models import PRData, PRFetchResult


class TestPRFetcher:
    """Test PRFetcher class."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = MagicMock()
        config.github_token = "test-token-123"
        return config

    @pytest.fixture
    def fetcher(self, mock_config):
        """Create PRFetcher instance with mock config."""
        with patch(
            "src.github_analyzer.data.pr_fetcher.get_config", return_value=mock_config
        ):
            return PRFetcher()

    @pytest.fixture
    def sample_pr_graphql(self):
        """Sample PR data from GraphQL response."""
        return {
            "number": 123,
            "title": "Add awesome feature",
            "body": "This PR adds an awesome feature",
            "state": "MERGED",
            "merged": True,
            "mergedAt": "2025-01-15T10:00:00Z",
            "createdAt": "2025-01-10T10:00:00Z",
            "closedAt": "2025-01-15T10:00:00Z",
            "additions": 250,
            "deletions": 50,
            "baseRefName": "main",
            "headRefName": "feature/awesome",
            "changedFiles": 12,
            "reviewDecision": "APPROVED",
            "labels": {"nodes": [{"name": "feature"}, {"name": "enhancement"}]},
            "author": {"login": "testuser"},
            "repository": {"name": "test-repo", "owner": {"login": "test-owner"}},
            "reviews": {"totalCount": 3},
            "comments": {"totalCount": 5},
            "commits": {
                "totalCount": 8,
                "nodes": [
                    {
                        "commit": {
                            "message": "Initial commit",
                            "authoredDate": "2025-01-10T10:00:00Z",
                        }
                    },
                    {
                        "commit": {
                            "message": "Add tests\nCo-authored-by: Alice <alice@example.com>",
                            "authoredDate": "2025-01-11T10:00:00Z",
                        }
                    },
                ],
            },
            "assignees": {"nodes": [{"login": "reviewer1"}, {"login": "reviewer2"}]},
        }

    def test_fetcher_initialization_with_token(self, mock_config):
        """Test fetcher initializes with token from config."""
        with patch(
            "src.github_analyzer.data.pr_fetcher.get_config", return_value=mock_config
        ):
            fetcher = PRFetcher()
            assert fetcher.token == "test-token-123"
            assert fetcher.graphql_url == "https://api.github.com/graphql"

    def test_fetcher_initialization_with_custom_token(self, mock_config):
        """Test fetcher uses custom token when provided."""
        with patch(
            "src.github_analyzer.data.pr_fetcher.get_config", return_value=mock_config
        ):
            fetcher = PRFetcher(github_token="custom-token")
            assert fetcher.token == "custom-token"

    def test_fetcher_initialization_without_token_raises(self, mock_config):
        """Test fetcher raises error when no token available."""
        mock_config.github_token = None
        with patch(
            "src.github_analyzer.data.pr_fetcher.get_config", return_value=mock_config
        ):
            with pytest.raises(ValueError, match="GitHub token is required"):
                PRFetcher()

    def test_fetch_user_prs_success(self, fetcher, sample_pr_graphql):
        """Test successful PR fetching for a user."""
        # Mock authored PRs response
        authored_response = {
            "data": {
                "user": {
                    "pullRequests": {
                        "totalCount": 2,
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": [sample_pr_graphql, sample_pr_graphql],
                    }
                }
            }
        }

        # Mock assigned PRs response (empty for this test)
        assigned_response = {
            "data": {
                "search": {
                    "issueCount": 0,
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [],
                }
            }
        }

        # Mock involved PRs response (empty for this test)
        involved_response = {
            "data": {
                "search": {
                    "issueCount": 0,
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [],
                }
            }
        }

        with patch.object(fetcher.session, "post") as mock_post:
            mock_post.side_effect = [
                MagicMock(json=lambda: authored_response, status_code=200),
                MagicMock(json=lambda: assigned_response, status_code=200),
                MagicMock(json=lambda: involved_response, status_code=200),
            ]

            result = fetcher.fetch_user_prs("testuser")

            assert isinstance(result, PRFetchResult)
            assert result.username == "testuser"
            assert result.total_count == 2
            assert len(result.prs) == 2
            assert result.authored_count == 2
            assert result.assigned_count == 0
            assert result.api_calls_used == 3

    def test_fetch_user_prs_with_pagination(self, fetcher, sample_pr_graphql):
        """Test PR fetching with multiple pages."""
        # First page of authored PRs
        page1_response = {
            "data": {
                "user": {
                    "pullRequests": {
                        "totalCount": 150,
                        "pageInfo": {"hasNextPage": True, "endCursor": "cursor1"},
                        "nodes": [sample_pr_graphql] * 100,  # 100 PRs
                    }
                }
            }
        }

        # Second page of authored PRs
        page2_response = {
            "data": {
                "user": {
                    "pullRequests": {
                        "totalCount": 150,
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": [sample_pr_graphql] * 50,  # 50 PRs
                    }
                }
            }
        }

        # Empty assigned PRs
        assigned_response = {
            "data": {
                "search": {
                    "issueCount": 0,
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [],
                }
            }
        }

        # Empty involved PRs
        involved_response = {
            "data": {
                "search": {
                    "issueCount": 0,
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [],
                }
            }
        }

        with patch.object(fetcher.session, "post") as mock_post:
            mock_post.side_effect = [
                MagicMock(json=lambda: page1_response, status_code=200),
                MagicMock(json=lambda: page2_response, status_code=200),
                MagicMock(json=lambda: assigned_response, status_code=200),
                MagicMock(json=lambda: involved_response, status_code=200),
            ]

            result = fetcher.fetch_user_prs("testuser")

            assert result.total_count == 150
            assert len(result.prs) == 150
            assert (
                result.api_calls_used == 4
            )  # 2 for authored, 1 for assigned, 1 for involved

    def test_fetch_assigned_prs_filters_author(self, fetcher, sample_pr_graphql):
        """Test that assigned PRs filters out PRs authored by the user."""
        # Create two PRs - one authored by testuser, one by someone else
        pr_by_user = dict(sample_pr_graphql)
        pr_by_user["author"] = {"login": "testuser"}

        pr_by_other = dict(sample_pr_graphql)
        pr_by_other["author"] = {"login": "otheruser"}
        pr_by_other["number"] = 456

        assigned_response = {
            "data": {
                "search": {
                    "issueCount": 2,
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [pr_by_user, pr_by_other],  # Both assigned to testuser
                }
            }
        }

        with patch.object(fetcher.session, "post") as mock_post:
            mock_post.return_value = MagicMock(
                json=lambda: assigned_response, status_code=200
            )

            assigned_prs, api_calls = fetcher._fetch_assigned_prs("testuser")

            assert len(assigned_prs) == 1  # Only the one NOT authored by testuser
            assert assigned_prs[0]["number"] == 456
            assert assigned_prs[0]["author"]["login"] == "otheruser"
            assert api_calls == 1

    def test_pr_deduplication(self, fetcher, sample_pr_graphql):
        """Test that duplicate PRs are properly deduplicated."""
        # Same PR appears in both authored and assigned
        pr_data = dict(sample_pr_graphql)
        pr_data["number"] = 789

        authored_response = {
            "data": {
                "user": {
                    "pullRequests": {
                        "totalCount": 1,
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": [pr_data],
                    }
                }
            }
        }

        # PR by someone else but assigned to testuser
        assigned_pr = dict(pr_data)
        assigned_pr["author"] = {"login": "otheruser"}

        assigned_response = {
            "data": {
                "search": {
                    "issueCount": 1,
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [assigned_pr],  # Same PR number
                }
            }
        }

        # Empty involved PRs
        involved_response = {
            "data": {
                "search": {
                    "issueCount": 0,
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [],
                }
            }
        }

        with patch.object(fetcher.session, "post") as mock_post:
            mock_post.side_effect = [
                MagicMock(json=lambda: authored_response, status_code=200),
                MagicMock(json=lambda: assigned_response, status_code=200),
                MagicMock(json=lambda: involved_response, status_code=200),
            ]

            result = fetcher.fetch_user_prs("testuser")

            # Should only have 1 PR, not 2
            assert len(result.prs) == 1
            assert result.prs[0].number == 789

    def test_dict_to_pr_data_conversion(self, fetcher, sample_pr_graphql):
        """Test conversion from GraphQL dict to PRData object."""
        pr_data = fetcher._dict_to_pr_data(sample_pr_graphql, "testuser")

        assert isinstance(pr_data, PRData)
        assert pr_data.number == 123
        assert pr_data.title == "Add awesome feature"
        assert pr_data.body == "This PR adds an awesome feature"
        assert pr_data.state == "MERGED"
        assert pr_data.merged is True
        assert pr_data.additions == 250
        assert pr_data.deletions == 50
        assert pr_data.repository == "test-owner/test-repo"
        assert pr_data.author == "testuser"
        assert pr_data.assignees == ["reviewer1", "reviewer2"]
        # Test new fields
        assert pr_data.changed_files == 12
        assert pr_data.review_decision == "APPROVED"
        assert pr_data.labels == ["feature", "enhancement"]
        assert pr_data.reviews_count == 3
        assert pr_data.comments_count == 5
        assert pr_data.commits_total == 8

    def test_co_author_detection(self, fetcher, sample_pr_graphql):
        """Test that co-authors are properly extracted from commit messages."""
        pr_data = fetcher._dict_to_pr_data(sample_pr_graphql, "testuser")

        assert len(pr_data.co_authors) == 1
        assert "Alice " in pr_data.co_authors[0]

    def test_collaborative_pr_detection(self, fetcher, sample_pr_graphql):
        """Test detection of collaborative PRs."""
        # PR authored by someone else
        pr_dict = dict(sample_pr_graphql)
        pr_dict["author"] = {"login": "otheruser"}

        pr_data = fetcher._dict_to_pr_data(pr_dict, "testuser")
        assert pr_data.is_collaborative is True

        # PR with co-authors
        pr_dict2 = dict(sample_pr_graphql)
        pr_data2 = fetcher._dict_to_pr_data(pr_dict2, "testuser")
        assert pr_data2.is_collaborative is True  # Has co-authors

    def test_parse_datetime(self, fetcher):
        """Test datetime parsing with various formats."""
        # ISO format with Z
        dt1 = fetcher._parse_datetime("2025-01-15T10:00:00Z")
        assert dt1.year == 2025
        assert dt1.month == 1
        assert dt1.day == 15
        assert dt1.tzinfo == timezone.utc

        # ISO format with +00:00
        dt2 = fetcher._parse_datetime("2025-01-15T10:00:00+00:00")
        assert dt2.tzinfo == timezone.utc

        # None input
        dt3 = fetcher._parse_datetime(None)
        assert dt3 is None

        # Invalid format (should log warning and return None)
        with patch("src.github_analyzer.data.pr_fetcher.logger") as mock_logger:
            dt4 = fetcher._parse_datetime("invalid-date")
            assert dt4 is None
            mock_logger.warning.assert_called()

    def test_error_handling_in_fetch(self, fetcher):
        """Test error handling during API calls."""
        with patch.object(fetcher.session, "post") as mock_post:
            # Simulate network error on all retry attempts
            mock_post.side_effect = requests.RequestException("Network error")

            # Should raise RuntimeError after retries are exhausted
            with pytest.raises(
                RuntimeError, match="Failed to fetch PR data from GitHub"
            ):
                fetcher.fetch_user_prs("testuser")

    def test_graphql_error_handling(self, fetcher):
        """Test handling of GraphQL errors in response."""
        error_response = {"errors": [{"message": "User not found"}], "data": None}

        with patch.object(fetcher.session, "post") as mock_post:
            mock_post.return_value = MagicMock(
                json=lambda: error_response, status_code=200
            )

            authored_prs, api_calls = fetcher._fetch_authored_prs("nonexistent")

            assert len(authored_prs) == 0
            assert api_calls == 1

    def test_session_retry_configuration(self, fetcher):
        """Test that session is configured with retry strategy."""
        # Check that retry adapter is configured
        assert fetcher.session.adapters["https://"].max_retries.total == 5
        assert 429 in fetcher.session.adapters["https://"].max_retries.status_forcelist

    def test_authorization_header(self, fetcher):
        """Test that authorization header is properly set."""
        assert "Authorization" in fetcher.session.headers
        assert fetcher.session.headers["Authorization"] == "Bearer test-token-123"

    def test_assigned_to_user_flag(self, fetcher, sample_pr_graphql):
        """Test that assigned_to_user flag is properly set."""
        # Create authored and assigned responses
        authored_pr = dict(sample_pr_graphql)
        authored_pr["number"] = 100
        authored_pr["author"] = {"login": "testuser"}

        assigned_pr = dict(sample_pr_graphql)
        assigned_pr["number"] = 200
        assigned_pr["author"] = {"login": "otheruser"}

        authored_response = {
            "data": {
                "user": {
                    "pullRequests": {
                        "totalCount": 1,
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": [authored_pr],
                    }
                }
            }
        }

        assigned_response = {
            "data": {
                "search": {
                    "issueCount": 1,
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [assigned_pr],
                }
            }
        }

        # Empty involved PRs
        involved_response = {
            "data": {
                "search": {
                    "issueCount": 0,
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [],
                }
            }
        }

        with patch.object(fetcher.session, "post") as mock_post:
            mock_post.side_effect = [
                MagicMock(json=lambda: authored_response, status_code=200),
                MagicMock(json=lambda: assigned_response, status_code=200),
                MagicMock(json=lambda: involved_response, status_code=200),
            ]

            result = fetcher.fetch_user_prs("testuser")

            # Check flags
            authored_pr_data = next(pr for pr in result.prs if pr.number == 100)
            assigned_pr_data = next(pr for pr in result.prs if pr.number == 200)

            assert authored_pr_data.assigned_to_user is False
            assert assigned_pr_data.assigned_to_user is True
            assert (
                result.api_calls_used == 3
            )  # 1 for authored, 1 for assigned, 1 for involved
