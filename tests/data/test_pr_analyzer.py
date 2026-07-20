"""
Tests for PR Analyzer orchestration.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pytest

from src.github_analyzer.data.pr_analyzer import PRAnalyzer
from src.github_analyzer.data.pr_models import (
    PRData,
    PREvidence,
    PRFetchResult,
    QualitySignals,
)


class TestPRAnalyzer:
    """Test PR analyzer orchestration."""

    @pytest.fixture
    def mock_token(self):
        """Mock GitHub token."""
        return "ghp_test_token_123"

    @pytest.fixture
    def sample_prs(self):
        """Create sample PR data."""
        now = datetime.now(timezone.utc)
        return [
            PRData(
                number=100,
                title="feat: Add new feature",
                body="Implements important functionality",
                state="MERGED",
                merged=True,
                created_at=now - timedelta(days=30),
                merged_at=now - timedelta(days=28),
                closed_at=now - timedelta(days=28),
                additions=500,
                deletions=100,
                commits_total=10,
                reviews_count=3,
                comments_count=5,
                author="testuser",
                assignees=[],
                repository_owner="test-org",
                repository_name="test-repo",
                base_ref="main",
                head_ref="feature/new-feature",
            ),
            PRData(
                number=101,
                title="fix: Fix critical bug",
                body="Fixes memory leak",
                state="MERGED",
                merged=True,
                created_at=now - timedelta(days=20),
                merged_at=now - timedelta(days=19),
                closed_at=now - timedelta(days=19),
                additions=50,
                deletions=30,
                commits_total=3,
                reviews_count=2,
                comments_count=1,
                author="testuser",
                assignees=["testuser"],
                repository_owner="test-org",
                repository_name="test-repo",
                base_ref="main",
                head_ref="fix/memory-leak",
            ),
            PRData(
                number=102,
                title="feat: Add another feature",
                body="Work in progress",
                state="OPEN",
                merged=False,
                created_at=now - timedelta(days=5),
                merged_at=None,
                closed_at=None,
                additions=300,
                deletions=50,
                commits_total=8,
                reviews_count=1,
                comments_count=10,
                author="testuser",
                assignees=[],
                repository_owner="other-org",
                repository_name="other-repo",
                base_ref="develop",
                head_ref="feature/wip",
            ),
        ]

    @pytest.fixture
    def mock_fetcher(self, sample_prs):
        """Create mock PR fetcher."""
        fetcher = Mock()
        fetcher.fetch_user_prs.return_value = PRFetchResult(
            prs=sample_prs,
            username="testuser",
            total_count=len(sample_prs),
            repos_contributed=["test-org/test-repo", "other-org/other-repo"],
            api_calls_used=3,
            fetch_time_seconds=2.5,
        )
        fetcher.get_rate_limit_status.return_value = (4997, 5000)
        return fetcher

    @pytest.fixture
    def mock_extractor(self):
        """Create mock evidence extractor."""
        extractor = Mock()

        # Mock evidence extraction
        evidence = PREvidence()
        evidence.technical_substance = [
            "Production Integration Success: 2/3 PRs successfully merged"
        ]
        evidence.collaboration_patterns = ["Sustained contributions over 30 days"]
        extractor.extract_evidence.return_value = evidence

        # Mock quality signals extraction
        signals = QualitySignals(
            total_prs=3, merged_prs=2, unique_repos=2, feature_prs=2, fix_prs=1
        )
        extractor.extract_quality_signals.return_value = signals

        return extractor

    def test_analyzer_initialization(self, mock_token):
        """Test analyzer initializes with token."""
        analyzer = PRAnalyzer(mock_token)
        assert analyzer.fetcher is not None
        assert analyzer.extractor is not None

    @patch("src.github_analyzer.data.pr_analyzer.PRFetcher")
    @patch("src.github_analyzer.data.pr_analyzer.PREvidenceExtractor")
    def test_analyze_user_success(
        self,
        mock_extractor_class,
        mock_fetcher_class,
        mock_fetcher,
        mock_extractor,
        mock_token,
    ):
        """Test successful user analysis."""
        # Setup mocks
        mock_fetcher_class.return_value = mock_fetcher
        mock_extractor_class.return_value = mock_extractor

        analyzer = PRAnalyzer(mock_token)
        result = analyzer.analyze_user("testuser")

        # Verify fetcher was called correctly
        mock_fetcher.fetch_user_prs.assert_called_once_with("testuser")

        # Verify extractor was called with fetched PRs
        assert mock_extractor.extract_evidence.called
        assert mock_extractor.extract_quality_signals.called

        # Check result structure
        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["username"] == "testuser"
        assert result["total_prs"] == 3
        assert result["api_calls_used"] == 3
        assert "error" not in result

    @patch("src.github_analyzer.data.pr_analyzer.PRFetcher")
    @patch("src.github_analyzer.data.pr_analyzer.PREvidenceExtractor")
    def test_analyze_user_with_limit(
        self,
        mock_extractor_class,
        mock_fetcher_class,
        mock_fetcher,
        mock_extractor,
        mock_token,
    ):
        """Test user analysis with PR limit - DEPRECATED: max_prs parameter removed."""
        # max_prs parameter no longer exists, so this test just verifies basic behavior
        mock_fetcher_class.return_value = mock_fetcher
        mock_extractor_class.return_value = mock_extractor

        analyzer = PRAnalyzer(mock_token)
        analyzer.analyze_user("testuser")

        # Verify fetcher was called
        mock_fetcher.fetch_user_prs.assert_called_once_with("testuser")

    @patch("src.github_analyzer.data.pr_analyzer.PRFetcher")
    @patch("src.github_analyzer.data.pr_analyzer.PREvidenceExtractor")
    def test_analyze_user_fetch_failure(
        self, mock_extractor_class, mock_fetcher_class, mock_token
    ):
        """Test user analysis when fetch fails."""
        # Setup failed fetch
        failed_fetcher = Mock()
        failed_fetcher.fetch_user_prs.side_effect = Exception("API rate limit exceeded")

        mock_fetcher_class.return_value = failed_fetcher
        mock_extractor_class.return_value = Mock()

        analyzer = PRAnalyzer(mock_token)
        result = analyzer.analyze_user("testuser")

        # Check error handling
        assert result["success"] is False
        assert result["error"] == "API rate limit exceeded"
        assert result["total_prs"] == 0
        assert isinstance(result["evidence"], PREvidence)
        assert isinstance(result["quality_signals"], QualitySignals)

    @patch("src.github_analyzer.data.pr_analyzer.PRFetcher")
    @patch("src.github_analyzer.data.pr_analyzer.PREvidenceExtractor")
    def test_analyze_repository_contributors(
        self,
        mock_extractor_class,
        mock_fetcher_class,
        mock_fetcher,
        mock_extractor,
        mock_token,
    ):
        """Test repository contributor analysis."""
        mock_fetcher_class.return_value = mock_fetcher
        mock_extractor_class.return_value = mock_extractor

        analyzer = PRAnalyzer(mock_token)

        # Mock get_top_contributors to return test users
        with patch.object(
            analyzer, "_get_top_contributors", return_value=["user1", "user2"]
        ):
            results = analyzer.analyze_repository_contributors(
                "test-org", "test-repo", top_n=2
            )

        # Should have results for each contributor
        assert len(results) == 2
        assert "user1" in results
        assert "user2" in results

        # Each result should be a dictionary result
        for username, result in results.items():
            assert isinstance(result, dict)
            assert result["username"] == username

    @patch("src.github_analyzer.data.pr_analyzer.PRFetcher")
    @patch("src.github_analyzer.data.pr_analyzer.PREvidenceExtractor")
    def test_analyze_user_for_repo(
        self,
        mock_extractor_class,
        mock_fetcher_class,
        mock_fetcher,
        mock_extractor,
        mock_token,
        sample_prs,
    ):
        """Test analyzing user's contributions to specific repo."""
        mock_fetcher_class.return_value = mock_fetcher
        mock_extractor_class.return_value = mock_extractor

        analyzer = PRAnalyzer(mock_token)
        result = analyzer._analyze_user_for_repo("testuser", "test-org", "test-repo")

        # Verify it filters PRs for the specific repo
        calls = mock_extractor.extract_evidence.call_args_list
        filtered_prs = calls[0][0][0]

        # Should only include PRs from test-org/test-repo
        for pr in filtered_prs:
            assert pr.repository_owner == "test-org"
            assert pr.repository_name == "test-repo"

        # Result should indicate repo context
        assert result["repository_context"] == "test-org/test-repo"

    @patch("src.github_analyzer.data.pr_analyzer.PRFetcher")
    @patch("src.github_analyzer.data.pr_analyzer.PREvidenceExtractor")
    def test_get_rate_limit_status(
        self, mock_extractor_class, mock_fetcher_class, mock_fetcher, mock_token
    ):
        """Test getting rate limit status."""
        mock_fetcher_class.return_value = mock_fetcher

        analyzer = PRAnalyzer(mock_token)
        remaining, limit = analyzer.get_rate_limit_status()

        assert remaining == 4997
        assert limit == 5000
        mock_fetcher.get_rate_limit_status.assert_called_once()

    @patch("src.github_analyzer.data.pr_analyzer.PRFetcher")
    @patch("src.github_analyzer.data.pr_analyzer.PREvidenceExtractor")
    def test_evidence_extraction_called_correctly(
        self,
        mock_extractor_class,
        mock_fetcher_class,
        mock_fetcher,
        mock_extractor,
        mock_token,
        sample_prs,
    ):
        """Test evidence extraction is called with correct params."""
        mock_fetcher_class.return_value = mock_fetcher
        mock_extractor_class.return_value = mock_extractor

        analyzer = PRAnalyzer(mock_token)
        analyzer.analyze_user("testuser")

        # Verify extractor methods called with correct arguments
        mock_extractor.extract_evidence.assert_called_once_with(sample_prs, "testuser")
        mock_extractor.extract_quality_signals.assert_called_once_with(
            sample_prs, "testuser"
        )

    @patch("src.github_analyzer.data.pr_analyzer.PRFetcher")
    @patch("src.github_analyzer.data.pr_analyzer.PREvidenceExtractor")
    def test_empty_pr_list_handling(
        self, mock_extractor_class, mock_fetcher_class, mock_token
    ):
        """Test handling of empty PR list."""
        # Setup fetcher to return empty list
        empty_fetcher = Mock()
        empty_fetcher.fetch_user_prs.return_value = PRFetchResult(
            prs=[],
            username="emptyuser",
            total_count=0,
            repos_contributed=[],
            api_calls_used=1,
            fetch_time_seconds=0.5,
        )

        # Setup extractor to handle empty list
        empty_extractor = Mock()
        empty_extractor.extract_evidence.return_value = PREvidence()
        empty_extractor.extract_quality_signals.return_value = QualitySignals(
            total_prs=0, merged_prs=0, unique_repos=0, feature_prs=0, fix_prs=0
        )

        mock_fetcher_class.return_value = empty_fetcher
        mock_extractor_class.return_value = empty_extractor

        analyzer = PRAnalyzer(mock_token)
        result = analyzer.analyze_user("emptyuser")

        assert result["total_prs"] == 0
        assert result["evidence"].total_evidence_count() == 0
        assert result["quality_signals"].total_prs == 0

    @patch("src.github_analyzer.data.pr_analyzer.PRFetcher")
    @patch("src.github_analyzer.data.pr_analyzer.PREvidenceExtractor")
    @patch("src.github_analyzer.data.pr_analyzer.logger")
    def test_logging_output(
        self,
        mock_logger,
        mock_extractor_class,
        mock_fetcher_class,
        mock_fetcher,
        mock_extractor,
        mock_token,
    ):
        """Test that appropriate logging occurs during analysis."""
        mock_fetcher_class.return_value = mock_fetcher
        mock_extractor_class.return_value = mock_extractor

        analyzer = PRAnalyzer(mock_token)
        analyzer.analyze_user("testuser")

        # Verify key log messages
        assert any(
            "Starting PR analysis for user: testuser" in str(call)
            for call in mock_logger.info.call_args_list
        )
        assert any(
            "Fetching PR data via GraphQL" in str(call)
            for call in mock_logger.info.call_args_list
        )
        assert any(
            "Analysis complete for testuser" in str(call)
            for call in mock_logger.info.call_args_list
        )

    def test_analyzer_integration_with_real_components(self, mock_token):
        """Test analyzer with real fetcher and extractor components."""
        # This test verifies the components work together
        # Note: This would normally mock the HTTP calls, but tests the integration

        with patch(
            "src.github_analyzer.data.pr_fetcher.requests.Session.post"
        ) as mock_post:
            # Mock GraphQL responses for all three fetch methods
            # Response 1: authored PRs (empty)
            authored_response = Mock()
            authored_response.json.return_value = {
                "data": {
                    "user": {
                        "pullRequests": {
                            "nodes": [],
                            "pageInfo": {"hasNextPage": False},
                            "totalCount": 0,
                        }
                    },
                    "rateLimit": {"remaining": 4999, "limit": 5000},
                }
            }
            authored_response.status_code = 200

            # Response 2: assigned PRs (empty)
            assigned_response = Mock()
            assigned_response.json.return_value = {
                "data": {
                    "search": {
                        "nodes": [],
                        "pageInfo": {"hasNextPage": False},
                        "issueCount": 0,
                    },
                    "rateLimit": {"remaining": 4998, "limit": 5000},
                }
            }
            assigned_response.status_code = 200

            # Response 3: involved PRs (empty)
            involved_response = Mock()
            involved_response.json.return_value = {
                "data": {
                    "search": {
                        "nodes": [],
                        "pageInfo": {"hasNextPage": False},
                        "issueCount": 0,
                    },
                    "rateLimit": {"remaining": 4997, "limit": 5000},
                }
            }
            involved_response.status_code = 200

            mock_post.side_effect = [
                authored_response,
                assigned_response,
                involved_response,
            ]

            # Create analyzer with real components
            analyzer = PRAnalyzer(mock_token)
            result = analyzer.analyze_user("testuser")

            # Verify integration works
            assert isinstance(result, dict)
            assert result["username"] == "testuser"
            assert result["total_prs"] == 0  # Empty response
            assert result["success"] is True
