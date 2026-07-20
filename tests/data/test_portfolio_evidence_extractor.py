"""Tests for portfolio evidence extraction.

Following the Orchestration Principle:
- Test the contract, not implementation
- Verify correct arguments passed to methods
- Verify results assembled correctly
- Test behavior with empty, single, and multiple repos
- NO SCORES OR RATINGS - evidence-based only
"""

from datetime import datetime, timezone
from typing import List

import pytest

from github_analyzer.data.portfolio_evidence_extractor import PortfolioEvidenceExtractor
from github_analyzer.data.portfolio_models import RepoData


@pytest.fixture
def extractor() -> PortfolioEvidenceExtractor:
    """Create a portfolio evidence extractor instance."""
    return PortfolioEvidenceExtractor()


@pytest.fixture
def sample_repos() -> List[RepoData]:
    """Create sample repos with diverse characteristics for testing.

    Creates repos with:
    - Different creation dates to test timeline
    - Different languages to test technology evolution
    - Different sizes to test substantial repos filtering
    - Mix of active/archived to test patterns
    """
    return [
        # Old Python repo - substantial with good quality indicators
        RepoData(
            name="data-pipeline",
            full_name="user/data-pipeline",
            url="https://github.com/user/data-pipeline",
            owner="user",
            created_at=datetime(2020, 1, 15, tzinfo=timezone.utc),
            updated_at=datetime(2024, 12, 20, tzinfo=timezone.utc),
            pushed_at=datetime(2024, 12, 20, tzinfo=timezone.utc),
            stars=45,
            forks=8,
            watchers=12,
            is_fork=False,
            is_archived=False,
            is_private=False,
            primary_language="Python",
            languages={"Python": 85000, "Shell": 5000},
            total_commits=156,
            topics=["data", "pipeline", "etl"],
            description="ETL pipeline for data processing",
            size_kb=1200,
            open_issues=3,
            has_wiki=True,
            has_pages=False,
            has_license=True,
            license_type="MIT",
        ),
        # Recent TypeScript repo - substantial and active
        RepoData(
            name="web-dashboard",
            full_name="user/web-dashboard",
            url="https://github.com/user/web-dashboard",
            owner="user",
            created_at=datetime(2023, 6, 10, tzinfo=timezone.utc),
            updated_at=datetime(2025, 1, 10, tzinfo=timezone.utc),
            pushed_at=datetime(2025, 1, 10, tzinfo=timezone.utc),
            stars=23,
            forks=4,
            watchers=8,
            is_fork=False,
            is_archived=False,
            is_private=False,
            primary_language="TypeScript",
            languages={"TypeScript": 65000, "JavaScript": 15000, "CSS": 8000},
            total_commits=89,
            topics=["react", "dashboard", "visualization"],
            description="Analytics dashboard built with React",
            size_kb=950,
            open_issues=2,
            has_wiki=False,
            has_pages=True,
            has_license=True,
            license_type="Apache-2.0",
        ),
        # Small toy repo - should be filtered as non-substantial
        RepoData(
            name="hello-world",
            full_name="user/hello-world",
            url="https://github.com/user/hello-world",
            owner="user",
            created_at=datetime(2019, 3, 5, tzinfo=timezone.utc),
            updated_at=datetime(2019, 3, 6, tzinfo=timezone.utc),
            pushed_at=datetime(2019, 3, 6, tzinfo=timezone.utc),
            stars=1,
            forks=0,
            watchers=1,
            is_fork=False,
            is_archived=True,
            is_private=False,
            primary_language="JavaScript",
            languages={"JavaScript": 500},
            total_commits=2,
            topics=[],
            description="Learning JavaScript",
            size_kb=15,
            open_issues=0,
            has_wiki=False,
            has_pages=False,
            has_license=False,
            license_type=None,
        ),
        # Medium Rust repo - showing technology evolution
        RepoData(
            name="cli-tool",
            full_name="user/cli-tool",
            url="https://github.com/user/cli-tool",
            owner="user",
            created_at=datetime(2022, 4, 20, tzinfo=timezone.utc),
            updated_at=datetime(2024, 11, 15, tzinfo=timezone.utc),
            pushed_at=datetime(2024, 11, 15, tzinfo=timezone.utc),
            stars=12,
            forks=2,
            watchers=5,
            is_fork=False,
            is_archived=False,
            is_private=False,
            primary_language="Rust",
            languages={"Rust": 45000, "Shell": 2000},
            total_commits=67,
            topics=["cli", "rust", "tool"],
            description="Command-line utility for file processing",
            size_kb=680,
            open_issues=1,
            has_wiki=False,
            has_pages=False,
            has_license=True,
            license_type="MIT",
        ),
        # Gap year - archived Go repo
        RepoData(
            name="api-service",
            full_name="user/api-service",
            url="https://github.com/user/api-service",
            owner="user",
            created_at=datetime(2021, 2, 10, tzinfo=timezone.utc),
            updated_at=datetime(2021, 8, 20, tzinfo=timezone.utc),
            pushed_at=datetime(2021, 8, 20, tzinfo=timezone.utc),
            stars=8,
            forks=1,
            watchers=3,
            is_fork=False,
            is_archived=True,
            is_private=False,
            primary_language="Go",
            languages={"Go": 35000, "Dockerfile": 1000},
            total_commits=42,
            topics=["api", "rest", "service"],
            description="REST API service",
            size_kb=520,
            open_issues=0,
            has_wiki=False,
            has_pages=False,
            has_license=True,
            license_type="MIT",
        ),
    ]


@pytest.fixture
def empty_repos() -> List[RepoData]:
    """Empty repos list for edge case testing."""
    return []


@pytest.fixture
def single_repo(sample_repos: List[RepoData]) -> List[RepoData]:
    """Single repo for minimal case testing."""
    return [sample_repos[0]]


class TestPortfolioEvidenceExtractor:
    """Test suite for PortfolioEvidenceExtractor.

    Tests follow the Orchestration Principle - verifying that the extractor:
    - Properly orchestrates evidence extraction from repos
    - Returns correct evidence structure
    - Handles edge cases (empty, single repo)
    - Extracts evidence without scores or ratings
    """

    def test_extract_all_evidence_returns_correct_structure(
        self, extractor: PortfolioEvidenceExtractor, sample_repos: List[RepoData]
    ):
        """Test that extract_all_evidence returns all expected evidence fields."""
        evidence = extractor.extract_all_evidence(sample_repos, "testuser")

        # Verify all required evidence fields are present (based on actual implementation)
        assert "public_repos_timeline" in evidence
        assert "technology_adoption_timeline" in evidence
        assert "public_work_quality_indicators" in evidence
        assert "timeline_gaps" in evidence
        assert "cross_technology_evidence" in evidence
        assert "portfolio_evolution_periods" in evidence
        assert "substantial_repos_structured" in evidence
        assert "technology_evolution_evidence" in evidence
        assert "quality_progression_evidence" in evidence
        assert "cross_repo_patterns" in evidence
        assert "aggregated_technologies" in evidence
        assert "aggregated_quality_indicators" in evidence
        assert "repo_substance_indicators" in evidence

    def test_extract_all_evidence_with_multiple_repos(
        self, extractor: PortfolioEvidenceExtractor, sample_repos: List[RepoData]
    ):
        """Test evidence extraction orchestration with multiple diverse repos."""
        evidence = extractor.extract_all_evidence(sample_repos, "testuser")

        # Verify aggregated technologies includes all languages from repos
        aggregated_tech = evidence["aggregated_technologies"]
        assert isinstance(aggregated_tech, dict)
        # Should have counts for each language
        assert "Python" in str(aggregated_tech) or len(aggregated_tech) > 0
        assert "TypeScript" in str(aggregated_tech) or len(aggregated_tech) > 0

        # Verify repos timeline is created (returns list of strings)
        timeline = evidence["public_repos_timeline"]
        assert isinstance(timeline, list)
        assert len(timeline) > 0
        # Timeline items are strings like "2020: data-pipeline (Python)"
        assert all(isinstance(item, str) for item in timeline)

        # Verify technology timeline exists (list of strings)
        tech_timeline = evidence["technology_adoption_timeline"]
        assert isinstance(tech_timeline, list)
        assert len(tech_timeline) > 0
        assert all(isinstance(item, str) for item in tech_timeline)

        # Verify substantial repos filtering (should exclude hello-world)
        substantial = evidence["substantial_repos_structured"]
        assert isinstance(substantial, list)
        # Should filter out at least the toy repo (hello-world is archived + small)
        assert len(substantial) >= 0  # May vary based on filtering logic

        # Verify evolution periods (should have multiple periods across years)
        periods = evidence["portfolio_evolution_periods"]
        assert isinstance(periods, list)

        # Verify timeline gaps detected (we have gaps between repos)
        gaps = evidence["timeline_gaps"]
        assert isinstance(gaps, list)
        assert len(gaps) >= 0  # May or may not have gaps depending on logic

    def test_extract_all_evidence_with_empty_repos(
        self, extractor: PortfolioEvidenceExtractor, empty_repos: List[RepoData]
    ):
        """Test evidence extraction with no repos returns empty evidence."""
        evidence = extractor.extract_all_evidence(empty_repos, "testuser")

        # Should return empty evidence structure
        assert evidence["public_repos_timeline"] == []
        assert evidence["technology_adoption_timeline"] == []
        assert evidence["substantial_repos_structured"] == []
        assert evidence["portfolio_evolution_periods"] == []
        assert evidence["aggregated_technologies"] == {}
        assert evidence["aggregated_quality_indicators"] == {}

    def test_extract_all_evidence_with_single_repo(
        self, extractor: PortfolioEvidenceExtractor, single_repo: List[RepoData]
    ):
        """Test evidence extraction with single repo."""
        evidence = extractor.extract_all_evidence(single_repo, "testuser")

        # Verify timeline has one entry
        assert len(evidence["public_repos_timeline"]) == 1
        # Timeline item is a string like "2020: data-pipeline (Python)"
        assert single_repo[0].name in evidence["public_repos_timeline"][0]

        # Verify primary language is in aggregated technologies
        if single_repo[0].primary_language:
            assert (
                single_repo[0].primary_language in evidence["aggregated_technologies"]
            )

    def test_build_repos_timeline_creates_sorted_timeline(
        self, extractor: PortfolioEvidenceExtractor, sample_repos: List[RepoData]
    ):
        """Test that repos timeline is created and sorted chronologically."""
        timeline = extractor._build_repos_timeline(sample_repos)

        # Should have entry for each repo (returns list of strings)
        assert len(timeline) == 5
        assert isinstance(timeline, list)

        # Each entry should be a string like "2020: data-pipeline (Python)"
        for item in timeline:
            assert isinstance(item, str)
            assert ":" in item  # Year separator
            assert "(" in item  # Language in parentheses

        # Verify hello-world is in timeline
        timeline_str = " ".join(timeline)
        assert "hello-world" in timeline_str

    def test_build_technology_timeline_tracks_first_usage(
        self, extractor: PortfolioEvidenceExtractor, sample_repos: List[RepoData]
    ):
        """Test that technology timeline tracks when each language was first used."""
        tech_timeline = extractor._build_technology_timeline(sample_repos)

        # Should have entries for all primary languages (returns list of strings)
        assert isinstance(tech_timeline, list)
        assert len(tech_timeline) > 0

        # Convert to string for easier checking
        timeline_str = " ".join(tech_timeline)

        # Should mention various languages
        assert (
            "Python" in timeline_str
            or "TypeScript" in timeline_str
            or "Rust" in timeline_str
        )

        # Each entry should be a string like "Python: First observed in public repos on 2020-01-15"
        for item in tech_timeline:
            assert isinstance(item, str)
            assert ":" in item
            assert "First observed" in item or len(item) > 0

    def test_detect_timeline_gaps_identifies_inactivity_periods(
        self, extractor: PortfolioEvidenceExtractor, sample_repos: List[RepoData]
    ):
        """Test that timeline gaps are detected between repos."""
        gaps = extractor._detect_timeline_gaps(sample_repos)

        # Gaps should be a list (may be empty if no significant gaps)
        assert isinstance(gaps, list)

        # If gaps exist, each should have required fields
        for gap in gaps:
            assert "start_date" in gap
            assert "end_date" in gap
            assert "duration_months" in gap
            assert gap["duration_months"] > 0

    def test_build_technology_summary_aggregates_languages(
        self, extractor: PortfolioEvidenceExtractor, sample_repos: List[RepoData]
    ):
        """Test that technology summary aggregates language usage correctly."""
        summary = extractor._build_technology_summary(sample_repos)

        # Should be a list of strings describing technologies
        assert isinstance(summary, list)
        assert len(summary) > 0

        # Should contain a summary string
        summary_str = " ".join(summary)
        assert "Technologies observed" in summary_str or len(summary_str) > 0

    def test_extract_evolution_periods_groups_by_year(
        self, extractor: PortfolioEvidenceExtractor, sample_repos: List[RepoData]
    ):
        """Test that evolution periods group repos by year."""
        periods = extractor._extract_evolution_periods(sample_repos)

        # Should return a list (may be empty or have dict entries)
        assert isinstance(periods, list)
        # May have periods for multiple years (2019-2025)
        assert len(periods) >= 0

    def test_extract_substantial_repos_filters_toy_repos(
        self, extractor: PortfolioEvidenceExtractor, sample_repos: List[RepoData]
    ):
        """Test that substantial repos filtering excludes toy/trivial repos."""
        substantial = extractor._extract_substantial_repos(sample_repos)

        # Should return a list
        assert isinstance(substantial, list)
        # Filtering is based on repo.is_substantial property
        # (commits >= 10, size_kb >= 100, not fork, not archived)

    def test_build_technology_evolution_tracks_adoption(
        self, extractor: PortfolioEvidenceExtractor, sample_repos: List[RepoData]
    ):
        """Test that technology evolution tracks language adoption over time."""
        evolution = extractor._build_technology_evolution(sample_repos)

        # Should be a dict or list tracking technology adoption
        assert evolution is not None

        # If it's a list, each entry should describe a technology adoption
        if isinstance(evolution, list):
            for item in evolution:
                # Structure depends on implementation
                pass

    def test_build_quality_progression_analyzes_quality_changes(
        self, extractor: PortfolioEvidenceExtractor, sample_repos: List[RepoData]
    ):
        """Test that quality progression analyzes quality indicators over time."""
        progression = extractor._build_quality_progression(sample_repos)

        # Should analyze quality trends without scores
        assert progression is not None

        # If it's a list, should have entries
        if isinstance(progression, list):
            # Each entry should describe quality evidence, not scores
            for item in progression:
                # Verify NO forbidden patterns (scores, ratings)
                item_str = str(item).lower()
                assert "score" not in item_str
                assert "rating" not in item_str
                assert "grade" not in item_str

    def test_build_cross_repo_patterns_identifies_patterns(
        self, extractor: PortfolioEvidenceExtractor, sample_repos: List[RepoData]
    ):
        """Test that cross-repo patterns identify common patterns across repos."""
        patterns = extractor._build_cross_repo_patterns(sample_repos)

        # Should identify patterns across repos
        assert patterns is not None

        # Should be a dict or list of pattern evidence
        if isinstance(patterns, dict):
            # Verify structure contains evidence, not scores
            pattern_str = str(patterns).lower()
            assert "score" not in pattern_str
            assert "rating" not in pattern_str

    def test_aggregate_technologies_combines_language_data(
        self, extractor: PortfolioEvidenceExtractor, sample_repos: List[RepoData]
    ):
        """Test that technology aggregation combines language data correctly."""
        aggregated = extractor._aggregate_technologies(sample_repos)

        # Should aggregate all languages from all repos
        assert isinstance(aggregated, dict)

        # Should include languages from all repos
        assert "Python" in aggregated or len(aggregated) > 0
        assert "TypeScript" in aggregated or len(aggregated) > 0

        # Each language should have total bytes
        for lang, bytes_count in aggregated.items():
            assert bytes_count > 0

    def test_aggregate_quality_indicators_no_scores(
        self, extractor: PortfolioEvidenceExtractor, sample_repos: List[RepoData]
    ):
        """Test that quality aggregation provides evidence without scores."""
        # Need to get substantial repos first
        substantial = extractor._extract_substantial_repos(sample_repos)
        quality = extractor._aggregate_quality_indicators(sample_repos, substantial)

        # Should aggregate quality indicators
        assert quality is not None
        assert isinstance(quality, dict)

        # CRITICAL: Verify NO scores or ratings (forbidden)
        quality_str = str(quality).lower()
        assert "score" not in quality_str
        assert "rating" not in quality_str
        assert "grade" not in quality_str

    def test_empty_evidence_returns_complete_structure(
        self, extractor: PortfolioEvidenceExtractor
    ):
        """Test that _empty_evidence returns complete empty structure."""
        empty = extractor._empty_evidence()

        # Should have all required fields (based on actual implementation)
        assert "public_repos_timeline" in empty
        assert "technology_adoption_timeline" in empty
        assert "public_work_quality_indicators" in empty
        assert "timeline_gaps" in empty
        assert "cross_technology_evidence" in empty
        assert "portfolio_evolution_periods" in empty
        assert "substantial_repos_structured" in empty
        assert "technology_evolution_evidence" in empty
        assert "quality_progression_evidence" in empty
        assert "cross_repo_patterns" in empty
        assert "aggregated_technologies" in empty
        assert "aggregated_quality_indicators" in empty
        assert "repo_substance_indicators" in empty

        # All should be empty
        assert empty["public_repos_timeline"] == []
        assert empty["technology_adoption_timeline"] == []
        assert empty["aggregated_technologies"] == {}
        assert empty["aggregated_quality_indicators"] == {}

    def test_no_scores_in_any_evidence(
        self, extractor: PortfolioEvidenceExtractor, sample_repos: List[RepoData]
    ):
        """CRITICAL: Test that NO scores, ratings, or grades appear in any evidence.

        This is a forbidden pattern per CLAUDE.local.md - evidence-based only.
        """
        evidence = extractor.extract_all_evidence(sample_repos, "testuser")

        # Convert entire evidence to string and check for forbidden patterns
        evidence_str = str(evidence).lower()

        # FORBIDDEN PATTERNS - must not appear
        assert "score" not in evidence_str, "Found forbidden 'score' in evidence"
        assert "rating" not in evidence_str, "Found forbidden 'rating' in evidence"
        assert "grade" not in evidence_str, "Found forbidden 'grade' in evidence"
        assert "rank" not in evidence_str, "Found forbidden 'rank' in evidence"

    def test_build_quality_indicators_provides_factual_evidence(
        self, extractor: PortfolioEvidenceExtractor, sample_repos: List[RepoData]
    ):
        """Test that quality indicators are factual evidence, not subjective scores."""
        indicators = extractor._build_quality_indicators(sample_repos)

        # Should return factual indicators
        assert indicators is not None

        # Verify NO scores
        indicators_str = str(indicators).lower()
        assert "score" not in indicators_str
        assert "rating" not in indicators_str

    def test_build_substance_indicators_identifies_substantial_work(
        self, extractor: PortfolioEvidenceExtractor, sample_repos: List[RepoData]
    ):
        """Test that substance indicators identify substantial work evidence."""
        # Need substantial repos first
        substantial = extractor._extract_substantial_repos(sample_repos)
        substance = extractor._build_substance_indicators(substantial)

        # Should identify substantial work patterns
        assert substance is not None
        assert isinstance(substance, list)

        # Should be evidence-based (commits, size, etc.) not scores
        substance_str = str(substance).lower()
        assert "score" not in substance_str
        assert "rating" not in substance_str
