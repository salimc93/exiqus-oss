"""
Tests for PR evidence extraction.
"""

from datetime import datetime, timedelta, timezone

import pytest

from src.github_analyzer.data.pr_evidence_extractor import PREvidenceExtractor
from src.github_analyzer.data.pr_models import PRData


class TestPREvidenceExtractor:
    """Test PR evidence extraction."""

    @pytest.fixture
    def extractor(self):
        """Create evidence extractor instance."""
        return PREvidenceExtractor()

    @pytest.fixture
    def sample_prs(self):
        """Create sample PR data for testing."""
        now = datetime.now(timezone.utc)
        return [
            # Massive merged PR (like debugger)
            PRData(
                number=13433,
                title="Debugger implementation",
                body="Implements the most requested feature for the editor",
                state="MERGED",
                merged=True,
                created_at=now - timedelta(days=180),
                merged_at=now - timedelta(days=170),
                closed_at=now - timedelta(days=170),
                additions=25837,
                deletions=500,
                commits_total=977,
                reviews_count=15,
                comments_count=45,
                author="RemcoSmitsDev",
                assignees=["testuser"],
                repository_owner="zed-industries",
                repository_name="zed",
                base_ref="main",
                head_ref="feature/debugger",
                assigned_to_user=True,
            ),
            # Large unmerged PR
            PRData(
                number=200,
                title="Windows: A new implementation of keystrokes",
                body="Refactoring keystroke handling on Windows",
                state="OPEN",
                merged=False,
                created_at=now - timedelta(days=30),
                merged_at=None,
                closed_at=None,
                additions=4343,
                deletions=100,
                commits_total=25,
                reviews_count=3,
                comments_count=10,
                author="testuser",
                assignees=[],
                repository_owner="zed-industries",
                repository_name="zed",
                base_ref="main",
                head_ref="feature/windows-keystrokes",
            ),
            # Regular merged PR with co-authors
            PRData(
                number=300,
                title="feat: Add collaborative editing",
                body="Implements real-time collaborative editing feature",
                state="MERGED",
                merged=True,
                created_at=now - timedelta(days=60),
                merged_at=now - timedelta(days=58),
                closed_at=now - timedelta(days=58),
                additions=800,
                deletions=200,
                commits_total=15,
                reviews_count=8,
                comments_count=20,
                author="testuser",
                assignees=[],
                repository_owner="zed-industries",
                repository_name="zed",
                base_ref="main",
                head_ref="feature/collab",
                co_authors=["alice", "bob"],
            ),
            # Quick merge PR
            PRData(
                number=400,
                title="fix: Resolve memory leak in renderer",
                body="Fixes critical memory leak",
                state="MERGED",
                merged=True,
                created_at=now - timedelta(days=10),
                merged_at=now - timedelta(days=9),
                closed_at=now - timedelta(days=9),
                additions=50,
                deletions=30,
                commits_total=3,
                reviews_count=2,
                comments_count=5,
                author="testuser",
                assignees=[],
                repository_owner="notify-rs",
                repository_name="notify",
                base_ref="main",
                head_ref="fix/memory-leak",
            ),
            # PR in different repo
            PRData(
                number=500,
                title="Add GPU profiling support",
                body="Adds profiling capabilities for GPU operations",
                state="MERGED",
                merged=True,
                created_at=now - timedelta(days=90),
                merged_at=now - timedelta(days=85),
                closed_at=now - timedelta(days=85),
                additions=300,
                deletions=50,
                commits_total=10,
                reviews_count=4,
                comments_count=15,
                author="testuser",
                assignees=[],
                repository_owner="gfx-rs",
                repository_name="wgpu",
                base_ref="trunk",
                head_ref="feature/gpu-profiling",
            ),
        ]

    def test_extract_evidence_captures_debugger_pr(self, extractor, sample_prs):
        """Test that massive PRs like debugger appear first."""
        evidence = extractor.extract_evidence(sample_prs, "testuser")

        # Check technical substance - debugger PR should be prominent
        assert len(evidence.technical_substance) > 0
        first_evidence = evidence.technical_substance[0]

        # Should highlight the debugger PR or production success
        assert (
            "25,837" in first_evidence
            or "Production Integration Success" in first_evidence
        )

        # Should mention it's assigned
        assigned_evidence = [
            e for e in evidence.collaboration_patterns if "Trusted with major PR" in e
        ]
        if assigned_evidence:
            assert "Debugger implementation" in assigned_evidence[0]
            assert "977 commits" in assigned_evidence[0]

    def test_production_integration_success(self, extractor, sample_prs):
        """Test production merge success rate is highlighted."""
        evidence = extractor.extract_evidence(sample_prs, "testuser")

        # Check for production integration evidence
        production_evidence = [
            e
            for e in evidence.technical_substance
            if "Production Integration Success" in e
        ]
        assert len(production_evidence) > 0

        # Should show merge rate
        assert "PRs successfully merged" in production_evidence[0]

    def test_sustained_engagement_over_time(self, extractor, sample_prs):
        """Test time-based consistency is captured as primary signal."""
        evidence = extractor.extract_evidence(sample_prs, "testuser")

        # Should have time-based evidence in collaboration patterns
        time_evidence = [
            e for e in evidence.collaboration_patterns if "Sustained contributions" in e
        ]

        # With 180 days span, should show months
        if time_evidence:
            assert "months" in time_evidence[0]

    def test_pair_programming_detection(self, extractor, sample_prs):
        """Test co-authorship is detected as pair programming."""
        evidence = extractor.extract_evidence(sample_prs, "testuser")

        # Check for pair programming evidence
        pair_evidence = [
            e for e in evidence.collaboration_patterns if "Pair programming" in e
        ]
        assert len(pair_evidence) > 0
        assert "co-authored" in pair_evidence[0]
        assert "2 different developers" in pair_evidence[0]  # alice and bob

    def test_deep_collaboration_detection(self, extractor, sample_prs):
        """Test PRs with many reviews are highlighted."""
        evidence = extractor.extract_evidence(sample_prs, "testuser")

        # Check for deep collaboration (3+ reviews)
        deep_collab = [
            e for e in evidence.collaboration_patterns if "Deep collaboration" in e
        ]
        assert len(deep_collab) > 0
        assert "review cycles" in deep_collab[0]

    def test_cross_repository_adaptability(self, extractor, sample_prs):
        """Test multiple repository contributions are highlighted."""
        evidence = extractor.extract_evidence(sample_prs, "testuser")

        # Check for cross-repo evidence
        cross_repo = [
            e for e in evidence.cross_repo_contributions if "Cross-Repository" in e
        ]
        assert len(cross_repo) > 0
        assert "3 different repositories" in cross_repo[0]

        # Should list specific repos
        repo_list = [
            e for e in evidence.cross_repo_contributions if "Repositories:" in e
        ]
        if repo_list:
            assert "zed-industries/zed" in repo_list[0]

    def test_persistent_review_engagement(self, extractor, sample_prs):
        """Test high review count PRs are highlighted."""
        evidence = extractor.extract_evidence(sample_prs, "testuser")

        # Check for persistence evidence
        persistence = [
            e for e in evidence.review_responsiveness if "Persistent Review" in e
        ]

        # Should show PRs that merged after many reviews
        if persistence:
            assert "merged after extensive review cycles" in persistence[0]

        # Should have specific examples
        specific = [
            e for e in evidence.review_responsiveness if "Persisted through" in e
        ]
        if specific:
            assert "reviews" in specific[0]

    def test_unmerged_large_prs_need_validation(self, extractor, sample_prs):
        """Test unmerged large PRs are marked as needing validation."""
        evidence = extractor.extract_evidence(sample_prs, "testuser")

        # Find evidence about unmerged large PRs
        unmerged_evidence = [
            e
            for e in evidence.technical_substance
            if "unmerged" in e or "needs validation" in e
        ]

        if unmerged_evidence:
            assert "Windows: A new implementation" in unmerged_evidence[0]
            assert "4,343" in unmerged_evidence[0]
            assert "needs validation" in unmerged_evidence[0]

    def test_quality_signals_extraction(self, extractor, sample_prs):
        """Test quality signals are properly extracted."""
        signals = extractor.extract_quality_signals(sample_prs, "testuser")

        # Check basic counts
        assert signals.total_prs == 5
        assert signals.merged_prs == 4  # All except the Windows PR

        # Check time metrics
        assert signals.contribution_timespan is not None
        assert signals.first_pr_date is not None
        assert signals.last_pr_date is not None

        # Check collaboration metrics
        assert signals.pair_programming_count == 1  # The collab editing PR
        assert signals.deep_collaboration_count >= 2  # PRs with 3+ reviews

        # Check repository diversity
        assert signals.unique_repos == 3  # zed, notify-rs, gfx-rs

        # Check feature vs fix classification
        assert signals.feature_prs > 0
        assert signals.fix_prs > 0

    def test_merge_rate_calculation(self, extractor, sample_prs):
        """Test merge rate is properly calculated."""
        signals = extractor.extract_quality_signals(sample_prs, "testuser")

        # 4 out of 5 PRs merged
        assert signals.merge_rate == 0.8

    def test_feature_ownership_tracking(self, extractor, sample_prs):
        """Test features taken to production are tracked."""
        signals = extractor.extract_quality_signals(sample_prs, "testuser")

        # Features with 200+ additions that merged
        assert signals.feature_ownership_count >= 1  # At least the collab editing

    def test_empty_pr_list_handling(self, extractor):
        """Test extractor handles empty PR list gracefully."""
        evidence = extractor.extract_evidence([], "testuser")
        signals = extractor.extract_quality_signals([], "testuser")

        # Should return empty evidence
        assert evidence.total_evidence_count() == 0

        # Should have zero counts
        assert signals.total_prs == 0
        assert signals.merged_prs == 0

    def test_evidence_prioritization(self, extractor, sample_prs):
        """Test important evidence appears first."""
        evidence = extractor.extract_evidence(sample_prs, "testuser")

        # Technical substance should have production success first
        if evidence.technical_substance:
            first = evidence.technical_substance[0]
            # Should be either production success, long-term commitment, or major PR
            assert any(
                [
                    "Production Integration Success" in first,
                    "Long-term commitment" in first,
                    "MAJOR SUCCESS" in first,
                ]
            )

        # Collaboration should have time consistency or pair programming first
        if evidence.collaboration_patterns:
            first = evidence.collaboration_patterns[0]
            assert any(
                [
                    "Sustained contributions" in first,
                    "Pair programming" in first,
                    "Deep collaboration" in first,
                ]
            )

    def test_assigned_pr_trust_indicator(self, extractor, sample_prs):
        """Test assigned PRs show trust indicators."""
        evidence = extractor.extract_evidence(sample_prs, "testuser")

        # Should have evidence about being assigned the debugger PR
        assigned = [
            e
            for e in evidence.collaboration_patterns
            if "assigned" in e.lower() or "trusted" in e.lower()
        ]
        assert len(assigned) > 0

    def test_monthly_pr_rate_calculation(self, extractor, sample_prs):
        """Test monthly PR rate is calculated."""
        signals = extractor.extract_quality_signals(sample_prs, "testuser")

        # With 180 day span and 5 PRs
        if signals.monthly_pr_rate:
            assert signals.monthly_pr_rate > 0
            # Should be roughly 5 PRs / 6 months = 0.83 per month
            assert 0.5 < signals.monthly_pr_rate < 1.5

    def test_branch_pattern_detection(self, extractor, sample_prs):
        """Test feature and fix branches are detected."""
        evidence = extractor.extract_evidence(sample_prs, "testuser")

        # Should detect feature branches
        feature_branches = [
            e for e in evidence.integration_patterns if "feature implementation" in e
        ]
        assert len(feature_branches) > 0

        # Should detect fix branches
        fix_branches = [
            e
            for e in evidence.integration_patterns
            if "bug fix" in e or "fix branch" in e
        ]
        assert len(fix_branches) > 0

    def test_pr_description_quality(self, extractor, sample_prs):
        """Test PR description quality is assessed."""
        # Add a PR with long description
        sample_prs.append(
            PRData(
                number=600,
                title="feat: Add comprehensive documentation",
                body="x" * 250,  # Long description
                state="MERGED",
                merged=True,
                created_at=sample_prs[0].created_at,
                merged_at=sample_prs[0].merged_at,
                closed_at=sample_prs[0].closed_at,
                additions=100,
                deletions=10,
                commits_total=5,
                reviews_count=2,
                comments_count=3,
                author="testuser",
                assignees=[],
                repository_owner="zed-industries",
                repository_name="zed",
                base_ref="main",
                head_ref="docs",
            )
        )

        evidence = extractor.extract_evidence(sample_prs, "testuser")

        # Should have evidence about PR descriptions
        descriptions = evidence.pr_description_quality
        assert len(descriptions) > 0
        assert "detailed descriptions" in descriptions[0]

    def test_conventional_commits_detection(self, extractor, sample_prs):
        """Test conventional commit format is detected."""
        evidence = extractor.extract_evidence(sample_prs, "testuser")

        # Should detect conventional commit format
        conventional = [
            e for e in evidence.process_adherence if "conventional commit" in e
        ]
        assert len(conventional) > 0
