"""
Unit tests for report generator safety net.

Tests the post-processing safety net that prevents hallucinated
behavioral metrics from appearing in reports.
"""

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from github_analyzer.core.evidence.insight_engine import (
    InsightCategory,
    InsightConfidence,
)
from github_analyzer.core.report_generator import ReportGenerator
from github_analyzer.data.models import CommitInfo, RepositoryData, RepositoryMetrics


class TestReportGeneratorSafety:
    """Test post-processing safety net for hallucinated metrics."""

    @pytest.fixture
    def generator(self):
        """Create a report generator instance."""
        return ReportGenerator()

    @pytest.fixture
    def minimal_repo(self):
        """Create a repository with minimal commits."""
        commits = [
            CommitInfo(
                sha=f"commit_{i}",
                message=f"Test commit {i}",
                author_name="test",
                author_email="test@example.com",
                date=datetime(
                    2025, 1, i + 1, 23 if i % 2 else 10, 0, tzinfo=timezone.utc
                ),
            )
            for i in range(5)  # Only 5 commits
        ]

        return RepositoryData(
            url="https://github.com/test/minimal",
            full_name="test/minimal",
            name="minimal",
            owner="test",
            description="Minimal repository",
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2025, 1, 5, tzinfo=timezone.utc),
            pushed_at=datetime(2025, 1, 5, tzinfo=timezone.utc),
            default_branch="main",
            size=100,
            languages={"Python": 1000},
            topics=[],
            license_name="MIT",
            stars=1,
            forks=0,
            watchers=1,
            open_issues=0,
            has_readme=True,
            has_license=True,
            has_contributing=False,
            has_tests=False,
            has_ci_config=False,
            recent_commits=commits,
            file_structure=[],
            readme_content="# Minimal",
            metrics=RepositoryMetrics(
                total_commits=5,
                unique_contributors=1,
                lines_of_code=100,
                test_coverage_estimate=0.0,
                documentation_presence="1 documentation files in 10 total files",
                days_since_last_commit=1,
                commit_frequency=1.0,
                avg_commit_size=20.0,
            ),
            fetched_at=datetime.now(timezone.utc),
            is_private=False,
            is_fork=False,
            is_archived=False,
            is_disabled=False,
        )

    def test_sanitizes_hallucinated_metrics(self, generator, minimal_repo):
        """Test removal of hallucinated behavioral metrics."""
        # Create insights with hallucinated metrics
        hallucinated_insights = [
            Mock(
                title="Work Pattern Analysis",
                description="Developer shows late_night_ratio: 0.75 indicating night owl tendencies",
                category=InsightCategory.WORK_PATTERNS,
                confidence=InsightConfidence.HIGH,
                evidence=["3 of 4 commits after 10 PM"],
                impact="neutral",
                context_relevance={},
            ),
            Mock(
                title="Weekend Work Habits",
                description="weekend_work_ratio: 0.5 suggests work-life balance issues",
                category=InsightCategory.WORK_PATTERNS,
                confidence=InsightConfidence.MEDIUM,
                evidence=["2 weekend commits"],
                impact="concerning",
                context_relevance={},
            ),
            Mock(
                title="Technical Skills",
                description="Strong Python expertise demonstrated",
                category=InsightCategory.TECHNICAL_SKILLS,
                confidence=InsightConfidence.HIGH,
                evidence=["Python is primary language"],
                impact="positive",
                context_relevance={},
            ),
            Mock(
                title="Burnout Risk",
                description="Analysis shows burnout_risk: high based on work patterns",
                category=InsightCategory.WORK_PATTERNS,
                confidence=InsightConfidence.LOW,
                evidence=["Late night work detected"],
                impact="concerning",
                context_relevance={},
            ),
            Mock(
                title="Consistent Work Pattern",
                description="Developer consistently works late hours",
                category=InsightCategory.WORK_PATTERNS,
                confidence=InsightConfidence.MEDIUM,
                evidence=["Regular late commits"],
                impact="neutral",
                context_relevance={},
            ),
        ]

        # Apply sanitization
        sanitized = generator._sanitize_insights_for_data_sufficiency(
            hallucinated_insights, minimal_repo
        )

        # Should remove work pattern insights but keep technical insight
        assert len(sanitized) == 1
        assert sanitized[0].title == "Technical Skills"

        # Verify the removed insights
        removed_titles = [i.title for i in hallucinated_insights if i not in sanitized]
        assert "Work Pattern Analysis" in removed_titles
        assert "Weekend Work Habits" in removed_titles
        assert "Burnout Risk" in removed_titles
        assert "Consistent Work Pattern" in removed_titles

    def test_preserves_insights_with_sufficient_data(self, generator):
        """Test that insights are preserved when data is sufficient."""
        # Create repo with 25 commits (above threshold)
        commits = [
            CommitInfo(
                sha=f"commit_{i}",
                message=f"Test commit {i}",
                author_name="test",
                author_email="test@example.com",
                date=datetime(2025, 1, i // 2 + 1, i % 24, 0, tzinfo=timezone.utc),
            )
            for i in range(25)
        ]

        sufficient_repo = Mock(recent_commits=commits)

        insights = [
            Mock(
                title="Work Pattern Analysis",
                description="Developer frequently works late nights (60% of commits after 10 PM)",
                category=InsightCategory.WORK_PATTERNS,
                confidence=InsightConfidence.HIGH,
                evidence=["15 of 25 commits after 10 PM"],
                impact="neutral",
                context_relevance={},
            ),
            Mock(
                title="Technical Skills",
                description="Strong Python expertise",
                category=InsightCategory.TECHNICAL_SKILLS,
                confidence=InsightConfidence.HIGH,
                evidence=["Python is primary language"],
                impact="positive",
                context_relevance={},
            ),
        ]

        # Apply sanitization
        sanitized = generator._sanitize_insights_for_data_sufficiency(
            insights, sufficient_repo
        )

        # Should preserve all insights
        assert len(sanitized) == 2
        assert all(i in sanitized for i in insights)

    def test_handles_percentage_patterns(self, generator, minimal_repo):
        """Test detection of percentage patterns in insights."""
        insights = [
            Mock(
                title="Work Patterns",
                description="80% of commits happen after midnight",
                category=InsightCategory.WORK_PATTERNS,
                confidence=InsightConfidence.LOW,
                evidence=["4 of 5 commits late"],
                impact="concerning",
                context_relevance={},
            ),
            Mock(
                title="Code Quality",
                description="Code shows 80% test coverage",  # This is OK - not behavioral
                category=InsightCategory.CODE_QUALITY,
                confidence=InsightConfidence.HIGH,
                evidence=["Test files present"],
                impact="positive",
                context_relevance={},
            ),
        ]

        sanitized = generator._sanitize_insights_for_data_sufficiency(
            insights, minimal_repo
        )

        # Should remove behavioral percentage but keep code quality percentage
        assert len(sanitized) == 1
        assert sanitized[0].title == "Code Quality"

    def test_handles_various_formats(self, generator, minimal_repo):
        """Test handling of various metric format variations."""
        insights = [
            Mock(
                title="Night Owl",
                description="late-night-ratio: 0.75",  # Hyphenated
                category=InsightCategory.WORK_PATTERNS,
            ),
            Mock(
                title="Weekend Worker",
                description="weekend work ratio: 0.5",  # Spaced
                category=InsightCategory.WORK_PATTERNS,
            ),
            Mock(
                title="Balance",
                description="work life balance shows 75% evening work",  # Natural language
                category=InsightCategory.WORK_PATTERNS,
            ),
            Mock(
                title="Clean Code",
                description="Follows clean code principles",  # Should be kept
                category=InsightCategory.CODE_QUALITY,
            ),
        ]

        # Set missing attributes for mocks
        for insight in insights:
            if not hasattr(insight, "confidence"):
                insight.confidence = InsightConfidence.MEDIUM
            if not hasattr(insight, "evidence"):
                insight.evidence = []
            if not hasattr(insight, "impact"):
                insight.impact = "neutral"
            if not hasattr(insight, "context_relevance"):
                insight.context_relevance = {}

        sanitized = generator._sanitize_insights_for_data_sufficiency(
            insights, minimal_repo
        )

        # Should only keep the clean code insight
        assert len(sanitized) == 1
        assert sanitized[0].title == "Clean Code"

    def test_logs_removed_insights(self, generator, minimal_repo, caplog):
        """Test that removed insights are properly logged."""
        insights = [
            Mock(
                title="Late Night Patterns",
                description="Shows late_night_ratio: 0.8",
                category=InsightCategory.WORK_PATTERNS,
                confidence=InsightConfidence.HIGH,
                evidence=["4 of 5 commits late"],
                impact="neutral",
                context_relevance={},
            ),
        ]

        # Enable logging capture
        import logging

        caplog.set_level(logging.INFO)

        # Apply sanitization
        generator._sanitize_insights_for_data_sufficiency(insights, minimal_repo)

        # Check logs
        assert "Removing insight with hallucinated metric" in caplog.text
        assert "only 5 commits" in caplog.text
        assert "Late Night Patterns" in caplog.text

    def test_empty_insights_handling(self, generator, minimal_repo):
        """Test handling of empty insights list."""
        sanitized = generator._sanitize_insights_for_data_sufficiency([], minimal_repo)
        assert sanitized == []

    def test_none_fields_handling(self, generator, minimal_repo):
        """Test handling of insights with None fields."""
        insights = [
            Mock(
                title=None,
                description="late_night_ratio: 0.75",
                category=InsightCategory.WORK_PATTERNS,
                confidence=InsightConfidence.LOW,
                evidence=[],
                impact="neutral",
                context_relevance={},
            ),
            Mock(
                title="Good Insight",
                description=None,
                category=InsightCategory.TECHNICAL_SKILLS,
                confidence=InsightConfidence.HIGH,
                evidence=["Evidence"],
                impact="positive",
                context_relevance={},
            ),
        ]

        # Should handle None gracefully
        sanitized = generator._sanitize_insights_for_data_sufficiency(
            insights, minimal_repo
        )

        # Should remove the one with ratio in description, keep the other
        assert len(sanitized) == 1
        assert sanitized[0].title == "Good Insight"
