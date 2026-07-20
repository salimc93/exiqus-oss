# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Data models for GitHub Portfolio analysis.

This module defines the data structures used for portfolio analysis,
following the evidence-based approach with NO SCORES OR RATINGS.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class RepoData:
    """Repository data structure for portfolio analysis."""

    name: str
    full_name: str
    url: str
    owner: str
    created_at: datetime
    updated_at: datetime
    pushed_at: datetime
    stars: int
    forks: int
    watchers: int
    is_fork: bool
    is_archived: bool
    is_private: bool
    primary_language: Optional[str]
    languages: Dict[str, int]  # {language: bytes_of_code}
    total_commits: int
    topics: List[str]
    description: Optional[str]
    size_kb: int
    open_issues: int
    has_wiki: bool
    has_pages: bool

    # Content analysis
    readme_content: Optional[str] = None
    readme_size: int = 0
    has_tests: bool = False
    has_ci: bool = False
    has_docker: bool = False
    has_license: bool = False
    license_type: Optional[str] = None

    # Contribution data
    user_commits: int = 0
    user_is_owner: bool = False
    last_commit_date: Optional[datetime] = None

    # File structure metadata
    file_count: int = 0
    directory_count: int = 0
    key_files: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate timezone-aware datetimes."""
        if self.created_at and self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        if self.updated_at and self.updated_at.tzinfo is None:
            raise ValueError("updated_at must be timezone-aware")
        if self.pushed_at and self.pushed_at.tzinfo is None:
            raise ValueError("pushed_at must be timezone-aware")
        if self.last_commit_date and self.last_commit_date.tzinfo is None:
            raise ValueError("last_commit_date must be timezone-aware")

    @property
    def age_days(self) -> int:
        """Calculate repository age in days."""
        now = datetime.now(self.created_at.tzinfo)
        delta = now - self.created_at
        return delta.days

    @property
    def days_since_push(self) -> int:
        """Calculate days since last push."""
        now = datetime.now(self.pushed_at.tzinfo)
        delta = now - self.pushed_at
        return delta.days

    @property
    def is_substantial(self) -> bool:
        """Check if repository meets minimum substance criteria."""
        return (
            self.total_commits >= 10
            and self.size_kb >= 100
            and not self.is_fork
            and not self.is_archived
        )


@dataclass
class PortfolioMetadata:
    """Metadata about the portfolio analysis."""

    total_public_repos: int
    repos_analyzed: int
    repos_skipped: int
    skip_counts: Dict[str, int]  # {forks: 2, archived: 0, etc}
    skipped_repos: Dict[str, List[str]]  # {forks: [repo1, repo2]}
    analyzed_repos: List[str]
    oldest_repo: str  # ISO datetime string
    newest_repo: str  # ISO datetime string
    timeline_gaps: int
    tokens: int
    cost: float


@dataclass
class EvolutionPeriod:
    """Portfolio evolution for a time period (FACTUAL DATA ONLY - NO SCORES)."""

    period: str  # e.g., "2019-2020", "2023-2024"
    public_repos_created: int
    technologies_observed: List[str]
    total_commits: str  # e.g., "101 (avg 33/repo)"
    domain_focus: str  # e.g., "Data Science/Python"
    largest_project: str  # e.g., "'repo-name' (68 commits, Python)"
    code_quality: str  # FACTUAL counts only: "Testing 0/3, README files 3/3"
    community_recognition: str  # FACTUAL counts: "8 stars total, 1 repo with 5+ stars"
    note: str = ""


@dataclass
class EvidencePattern:
    """Evidence pattern with factual evidence (NO SCORES OR RATINGS)."""

    pattern: str  # e.g., "Python Specialization Depth"
    evidence: str  # Factual evidence supporting the pattern
    analysis: Optional[str] = (
        None  # AI-generated insight explaining significance of the evidence
    )


@dataclass
class InterviewQuestion:
    """Interview question with evidence-based context."""

    question: str
    category: str  # architecture, problem-solving, code-quality, testing, etc.
    evidence: str  # Factual evidence that prompted this question
    follow_up_questions: List[str]
    key_listening_points: str  # What to assess in the answer
    context: str  # Why this matters for enterprise/startup/etc.


@dataclass
class QualityIndicator:
    """
    Quality indicator with OBSERVATION and SCOPE (NO SCORES OR RATINGS).

    This is NOT a score - it's a factual observation with explicit scope.
    """

    indicator: str  # e.g., "Code Organization", "Testing Practices"
    observation: str  # Factual observation from public repos
    scope: str  # Always "public repositories only" or similar
    implication: str  # What this suggests (with limitations noted)


@dataclass
class PortfolioAnalysisResult:
    """
    Complete portfolio analysis result.

    CRITICAL: Evidence-based approach with NO SCORES OR RATINGS.
    """

    username: str
    metadata: PortfolioMetadata

    # Core analysis sections
    summary: str  # Executive summary with data limitations warning
    limitations: str  # Explicit data limitations warning
    observations: List[str]  # Factual observations
    evolution: List[EvolutionPeriod]  # Timeline periods
    patterns: List[EvidencePattern]  # Evidence patterns
    questions: List[InterviewQuestion]  # Interview questions
    recommendations: List[str]  # Areas to explore in interview
    indicators: List[QualityIndicator]  # Observations with scope

    # Analysis metadata
    context: str  # STARTUP, ENTERPRISE, AGENCY, OPEN_SOURCE
    analysis_timestamp: datetime
    api_calls_used: int
    fetch_time_seconds: float
    analysis_time_seconds: float
    analysis_cost_usd: float
    model_used: str
    tokens_used: int

    # Optional: Raw data for debugging
    raw_repo_data: Optional[List[Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "username": self.username,
            "metadata": {
                "total_public_repos": self.metadata.total_public_repos,
                "repos_analyzed": self.metadata.repos_analyzed,
                "repos_skipped": self.metadata.repos_skipped,
                "skip_counts": self.metadata.skip_counts,
                "skipped_repos": self.metadata.skipped_repos,
                "analyzed_repos": self.metadata.analyzed_repos,
                "oldest_repo": self.metadata.oldest_repo,
                "newest_repo": self.metadata.newest_repo,
                "timeline_gaps": self.metadata.timeline_gaps,
                "tokens": self.metadata.tokens,
                "cost": self.metadata.cost,
            },
            "summary": self.summary,
            "limitations": self.limitations,
            "observations": self.observations,
            "evolution": [
                {
                    "period": p.period,
                    "public_repos_created": p.public_repos_created,
                    "technologies_observed": p.technologies_observed,
                    "total_commits": p.total_commits,
                    "domain_focus": p.domain_focus,
                    "largest_project": p.largest_project,
                    "code_quality": p.code_quality,
                    "community_recognition": p.community_recognition,
                    "note": p.note,
                }
                for p in self.evolution
            ],
            "patterns": [
                {
                    "pattern": p.pattern,
                    "evidence": p.evidence,
                    "analysis": p.analysis,
                }
                for p in self.patterns
            ],
            "questions": [
                {
                    "question": q.question,
                    "category": q.category,
                    "evidence": q.evidence,
                    "follow_up_questions": q.follow_up_questions,
                    "key_listening_points": q.key_listening_points,
                    "context": q.context,
                }
                for q in self.questions
            ],
            "recommendations": self.recommendations,
            "indicators": [
                {
                    "indicator": i.indicator,
                    "observation": i.observation,
                    "scope": i.scope,
                    "implication": i.implication,
                }
                for i in self.indicators
            ],
            "context": self.context,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
            "api_calls_used": self.api_calls_used,
            "fetch_time_seconds": self.fetch_time_seconds,
            "analysis_time_seconds": self.analysis_time_seconds,
            "analysis_cost_usd": self.analysis_cost_usd,
            "model_used": self.model_used,
            "tokens_used": self.tokens_used,
        }


@dataclass
class PortfolioFetchResult:
    """Result from fetching portfolio data."""

    repos: List[RepoData]
    username: str
    total_public_repos: int
    repos_fetched: int
    repos_skipped: int
    skip_reasons: Dict[str, int]  # {reason: count}
    skipped_repos: Dict[str, List[str]]  # {reason: [repo names]}
    api_calls_used: int
    fetch_time_seconds: float
    all_repos_dates: List[str]  # pushed_at dates from ALL repos (for span calculation)
    from_cache: bool = False

    @property
    def owned_repos_count(self) -> int:
        """Count of repositories owned by user."""
        return sum(1 for repo in self.repos if repo.user_is_owner)

    @property
    def forked_repos_count(self) -> int:
        """Count of forked repositories."""
        return sum(1 for repo in self.repos if repo.is_fork)

    @property
    def substantial_repos_count(self) -> int:
        """Count of substantial repositories (FACTUAL COUNT - NOT A SCORE)."""
        return sum(1 for repo in self.repos if repo.is_substantial)

    @property
    def technologies_used(self) -> List[str]:
        """Get list of all unique technologies across portfolio."""
        techs = set()
        for repo in self.repos:
            if repo.primary_language:
                techs.add(repo.primary_language)
            techs.update(repo.languages.keys())
        return sorted(list(techs))
