"""
Tests for PR data models.
"""

from datetime import datetime, timezone

import pytest

from src.github_analyzer.data.pr_models import (
    PRAnalysisResult,
    PRData,
    PREvidence,
    PRFetchResult,
    QualitySignals,
)


class TestPRData:
    """Test PRData model."""

    def test_pr_data_creation(self):
        """Test creating PRData instance."""
        pr = PRData(
            number=123,
            title="Test PR",
            body="Test description",
            state="closed",
            merged=True,
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            merged_at=datetime(2025, 1, 2, tzinfo=timezone.utc),
            closed_at=datetime(2025, 1, 2, tzinfo=timezone.utc),
            additions=100,
            deletions=50,
            commits_total=5,
            reviews_count=2,
            comments_count=3,
            author="testuser",
            assignees=["user1", "user2"],
            repository_owner="owner",
            repository_name="repo",
            base_ref="main",
            head_ref="feature",
        )

        assert pr.number == 123
        assert pr.title == "Test PR"
        assert pr.merged is True
        assert pr.total_changes == 150
        assert pr.repository == "owner/repo"

    def test_pr_data_timezone_validation(self):
        """Test that timezone-naive dates raise error."""
        with pytest.raises(ValueError, match="created_at must be timezone-aware"):
            PRData(
                number=123,
                title="Test PR",
                body=None,
                state="open",
                merged=False,
                created_at=datetime(2025, 1, 1),  # No timezone
                merged_at=None,
                closed_at=None,
                additions=10,
                deletions=5,
                commits_total=1,
                reviews_count=0,
                comments_count=0,
                author="user",
                assignees=[],
                repository_owner="owner",
                repository_name="repo",
                base_ref="main",
                head_ref="feature",
            )

    def test_merge_time_calculation(self):
        """Test merge time calculation."""
        pr = PRData(
            number=1,
            title="Test",
            body=None,
            state="closed",
            merged=True,
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            merged_at=datetime(2025, 1, 3, tzinfo=timezone.utc),
            closed_at=datetime(2025, 1, 3, tzinfo=timezone.utc),
            additions=10,
            deletions=5,
            commits_total=1,
            reviews_count=0,
            comments_count=0,
            author="user",
            assignees=[],
            repository_owner="owner",
            repository_name="repo",
            base_ref="main",
            head_ref="feature",
        )

        assert pr.merge_time_days == 2.0

    def test_is_significant(self):
        """Test significance detection."""
        # Large PR
        pr1 = PRData(
            number=1,
            title="Large PR",
            body=None,
            state="open",
            merged=False,
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            merged_at=None,
            closed_at=None,
            additions=200,
            deletions=50,
            commits_total=5,
            reviews_count=2,
            comments_count=0,
            author="user",
            assignees=[],
            repository_owner="owner",
            repository_name="repo",
            base_ref="main",
            head_ref="feature",
        )
        assert pr1.is_significant is True

        # Small PR
        pr2 = PRData(
            number=2,
            title="Small PR",
            body=None,
            state="open",
            merged=False,
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            merged_at=None,
            closed_at=None,
            additions=10,
            deletions=5,
            commits_total=1,
            reviews_count=0,
            comments_count=0,
            author="user",
            assignees=[],
            repository_owner="owner",
            repository_name="repo",
            base_ref="main",
            head_ref="fix",
        )
        assert pr2.is_significant is False


class TestPREvidence:
    """Test PREvidence model."""

    def test_evidence_creation(self):
        """Test creating PREvidence instance."""
        evidence = PREvidence()
        evidence.technical_substance.append("Test evidence 1")
        evidence.collaboration_patterns.append("Test pattern 1")

        assert len(evidence.technical_substance) == 1
        assert len(evidence.collaboration_patterns) == 1
        assert evidence.total_evidence_count() == 2

    def test_get_all_evidence(self):
        """Test getting all evidence as dictionary."""
        evidence = PREvidence(
            technical_substance=["tech1", "tech2"],
            collaboration_patterns=["collab1"],
            review_responsiveness=["review1"],
        )

        all_evidence = evidence.get_all_evidence()
        assert len(all_evidence["technical_substance"]) == 2
        assert len(all_evidence["collaboration_patterns"]) == 1
        assert len(all_evidence["review_responsiveness"]) == 1
        assert evidence.total_evidence_count() == 4


class TestQualitySignals:
    """Test QualitySignals model."""

    def test_quality_signals_creation(self):
        """Test creating QualitySignals instance."""
        signals = QualitySignals(
            contribution_timespan="2 years, 3 months",
            pair_programming_count=15,
            deep_collaboration_count=8,
            feature_prs=25,
            fix_prs=40,
            total_prs=100,
            merged_prs=85,
            unique_repos=5,
        )

        assert signals.contribution_timespan == "2 years, 3 months"
        assert signals.pair_programming_count == 15
        assert signals.merge_rate == 0.85

    def test_contribution_balance(self):
        """Test contribution balance calculation."""
        # Balanced
        signals1 = QualitySignals(feature_prs=20, fix_prs=30)
        assert "Full-stack contributions" in signals1.contribution_balance

        # Feature-focused
        signals2 = QualitySignals(feature_prs=20, fix_prs=0)
        assert "Feature-focused" in signals2.contribution_balance

        # Fix-focused
        signals3 = QualitySignals(feature_prs=0, fix_prs=30)
        assert "Stability-focused" in signals3.contribution_balance

        # No contributions
        signals4 = QualitySignals()
        assert "No categorized contributions" in signals4.contribution_balance

    def test_merge_rate(self):
        """Test merge rate calculation."""
        signals = QualitySignals(total_prs=100, merged_prs=75)
        assert signals.merge_rate == 0.75

        # Edge case: no PRs
        signals2 = QualitySignals(total_prs=0, merged_prs=0)
        assert signals2.merge_rate == 0.0


class TestPRAnalysisResult:
    """Test PRAnalysisResult model."""

    def test_analysis_result_creation(self):
        """Test creating PRAnalysisResult instance."""
        result = PRAnalysisResult(
            username="testuser",
            context="STARTUP",
            total_prs_analyzed=50,
            evidence=PREvidence(technical_substance=["evidence1"]),
            quality_signals=QualitySignals(total_prs=50),
            executive_summary="Test summary",
            insights=[{"title": "Insight 1", "description": "Description"}],
            interview_questions=[{"question": "Q1", "context": "Context"}],
            recommendations=["Rec 1"],
            areas_to_explore=["Area 1"],
            analysis_timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            api_calls_used=4,
            fetch_time_seconds=10.5,
            analysis_cost_usd=0.05,
            model_used="claude-3-haiku",
            confidence_explanation="High confidence based on substantial data",
            data_limitations=["Cannot assess private repos"],
        )

        assert result.username == "testuser"
        assert result.context == "STARTUP"
        assert result.total_prs_analyzed == 50

    def test_analysis_result_to_dict(self):
        """Test converting analysis result to dictionary."""
        result = PRAnalysisResult(
            username="testuser",
            context="STARTUP",
            total_prs_analyzed=50,
            evidence=PREvidence(technical_substance=["evidence1"]),
            quality_signals=QualitySignals(
                total_prs=50,
                merged_prs=45,
                feature_prs=20,
                fix_prs=25,
            ),
            executive_summary="Summary",
            insights=[],
            interview_questions=[],
            recommendations=[],
            areas_to_explore=[],
            analysis_timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            api_calls_used=4,
            fetch_time_seconds=10.5,
            analysis_cost_usd=0.05,
            model_used="claude-3-haiku",
            confidence_explanation="High confidence",
            data_limitations=[],
        )

        result_dict = result.to_dict()
        assert result_dict["username"] == "testuser"
        assert result_dict["quality_signals"]["merge_rate"] == 0.9
        assert "contribution_balance" in result_dict["quality_signals"]


class TestPRFetchResult:
    """Test PRFetchResult model."""

    def test_fetch_result_creation(self):
        """Test creating PRFetchResult instance."""
        pr1 = PRData(
            number=1,
            title="PR 1",
            body=None,
            state="closed",
            merged=True,
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            merged_at=datetime(2025, 1, 2, tzinfo=timezone.utc),
            closed_at=datetime(2025, 1, 2, tzinfo=timezone.utc),
            additions=10,
            deletions=5,
            commits_total=1,
            reviews_count=0,
            comments_count=0,
            author="testuser",
            assignees=[],
            repository_owner="owner",
            repository_name="repo",
            base_ref="main",
            head_ref="feature",
        )

        pr2 = PRData(
            number=2,
            title="PR 2",
            body=None,
            state="closed",
            merged=True,
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            merged_at=datetime(2025, 1, 2, tzinfo=timezone.utc),
            closed_at=datetime(2025, 1, 2, tzinfo=timezone.utc),
            additions=20,
            deletions=10,
            commits_total=2,
            reviews_count=1,
            comments_count=0,
            author="otheruser",
            assignees=["testuser"],
            repository_owner="owner",
            repository_name="repo",
            base_ref="main",
            head_ref="fix",
            assigned_to_user=True,
        )

        fetch_result = PRFetchResult(
            prs=[pr1, pr2],
            username="testuser",
            total_count=2,
            repos_contributed=["owner/repo"],
            api_calls_used=4,
            fetch_time_seconds=5.2,
        )

        assert fetch_result.total_count == 2
        assert fetch_result.authored_count == 1  # Only pr1
        assert fetch_result.assigned_count == 1  # Only pr2
        assert fetch_result.from_cache is False
