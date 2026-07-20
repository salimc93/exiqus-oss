# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Data models for GitHub Pull Request analysis.

This module defines the data structures used for PR analysis,
including PR data, evidence patterns, and quality signals.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class PRData:
    """Pull request data structure."""

    number: int
    title: str
    body: Optional[str]
    state: str
    merged: bool
    created_at: datetime
    merged_at: Optional[datetime]
    closed_at: Optional[datetime]
    additions: int
    deletions: int
    commits_total: int
    reviews_count: int
    comments_count: int
    author: str
    assignees: List[str]
    repository_owner: str
    repository_name: str
    base_ref: str
    head_ref: str

    # NEW: High-value evidence fields
    changed_files: int = 0
    review_decision: Optional[str] = (
        None  # APPROVED, CHANGES_REQUESTED, REVIEW_REQUIRED, None
    )
    labels: List[str] = field(default_factory=list)

    # Collaborative PR fields
    user_commits: int = 0
    is_collaborative: bool = False
    co_authors: List[str] = field(default_factory=list)
    assigned_to_user: bool = False

    # Review data
    review_decisions: List[str] = field(default_factory=list)
    approved_count: int = 0
    changes_requested_count: int = 0

    # Computed fields
    total_changes: int = field(init=False)

    def __post_init__(self) -> None:
        """Compute derived fields after initialization."""
        self.total_changes = self.additions + self.deletions

        # Ensure dates are timezone-aware
        if self.created_at and self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        if self.merged_at and self.merged_at.tzinfo is None:
            raise ValueError("merged_at must be timezone-aware")
        if self.closed_at and self.closed_at.tzinfo is None:
            raise ValueError("closed_at must be timezone-aware")

    @property
    def repository(self) -> str:
        """Get full repository name."""
        return f"{self.repository_owner}/{self.repository_name}"

    @property
    def merge_time_days(self) -> Optional[float]:
        """Calculate days from creation to merge."""
        if not self.merged_at:
            return None
        delta = self.merged_at - self.created_at
        return delta.total_seconds() / 86400  # Convert to days

    @property
    def is_significant(self) -> bool:
        """Check if PR is significant based on size and impact."""
        return (
            self.additions > 100
            or self.deletions > 100
            or self.commits_total > 10
            or self.reviews_count > 3
        )


@dataclass
class PREvidence:
    """Evidence extracted from PR data for analysis."""

    technical_substance: List[str] = field(default_factory=list)
    collaboration_patterns: List[str] = field(default_factory=list)
    review_responsiveness: List[str] = field(default_factory=list)
    integration_patterns: List[str] = field(default_factory=list)
    cross_repo_contributions: List[str] = field(default_factory=list)
    pr_description_quality: List[str] = field(default_factory=list)
    process_adherence: List[str] = field(default_factory=list)
    areas_to_explore: List[str] = field(default_factory=list)

    def get_all_evidence(self) -> Dict[str, List[str]]:
        """Get all evidence as a dictionary."""
        return {
            "technical_substance": self.technical_substance,
            "collaboration_patterns": self.collaboration_patterns,
            "review_responsiveness": self.review_responsiveness,
            "integration_patterns": self.integration_patterns,
            "cross_repo_contributions": self.cross_repo_contributions,
            "pr_description_quality": self.pr_description_quality,
            "process_adherence": self.process_adherence,
            "areas_to_explore": self.areas_to_explore,
        }

    def total_evidence_count(self) -> int:
        """Get total count of all evidence items."""
        return sum(len(v) for v in self.get_all_evidence().values())


@dataclass
class QualitySignals:
    """Quality signals extracted from PR history."""

    # Time-based metrics
    contribution_timespan: Optional[str] = None  # e.g., "3 years, 2 months"
    first_pr_date: Optional[datetime] = None
    last_pr_date: Optional[datetime] = None
    monthly_pr_rate: float = 0.0

    # Collaboration metrics
    pair_programming_count: int = 0
    deep_collaboration_count: int = 0  # PRs with 3+ review cycles
    self_managed_prs: int = 0
    assigned_prs: int = 0

    # Contribution patterns
    feature_prs: int = 0
    fix_prs: int = 0
    feature_ownership_count: int = 0  # Features taken to production
    total_prs: int = 0
    merged_prs: int = 0

    # Repository diversity
    unique_repos: int = 0
    repo_list: List[str] = field(default_factory=list)

    # Size metrics
    large_prs: int = 0  # 500+ lines
    focused_prs: int = 0  # <100 lines

    @property
    def merge_rate(self) -> float:
        """Calculate merge success rate."""
        if self.total_prs == 0:
            return 0.0
        return self.merged_prs / self.total_prs

    @property
    def contribution_balance(self) -> str:
        """Get feature vs fix balance description."""
        if self.feature_prs == 0 and self.fix_prs == 0:
            return "No categorized contributions"
        elif self.feature_prs > 0 and self.fix_prs > 0:
            return f"Full-stack contributions: {self.feature_prs} features, {self.fix_prs} fixes"
        elif self.feature_prs > 0:
            return f"Feature-focused: {self.feature_prs} features implemented"
        else:
            return f"Stability-focused: {self.fix_prs} fixes delivered"


@dataclass
class PRAnalysisResult:
    """Complete PR analysis result."""

    username: str
    context: str  # STARTUP, ENTERPRISE, AGENCY, OPEN_SOURCE
    total_prs_analyzed: int

    # Core analysis components
    evidence: PREvidence
    quality_signals: QualitySignals

    # AI-generated content
    executive_summary: str
    insights: List[Dict[str, str]]  # Key insights with evidence
    interview_questions: List[Dict[str, str]]  # Questions with context
    recommendations: List[str]
    areas_to_explore: List[str]

    # Metadata
    analysis_timestamp: datetime
    api_calls_used: int
    fetch_time_seconds: float
    analysis_cost_usd: float
    model_used: str

    # Confidence and limitations
    confidence_explanation: str
    data_limitations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "username": self.username,
            "context": self.context,
            "total_prs_analyzed": self.total_prs_analyzed,
            "evidence": self.evidence.get_all_evidence(),
            "quality_signals": {
                "contribution_timespan": self.quality_signals.contribution_timespan,
                "monthly_pr_rate": self.quality_signals.monthly_pr_rate,
                "pair_programming_count": self.quality_signals.pair_programming_count,
                "deep_collaboration_count": self.quality_signals.deep_collaboration_count,
                "feature_ownership_count": self.quality_signals.feature_ownership_count,
                "contribution_balance": self.quality_signals.contribution_balance,
                "merge_rate": self.quality_signals.merge_rate,
                "unique_repos": self.quality_signals.unique_repos,
            },
            "executive_summary": self.executive_summary,
            "insights": self.insights,
            "interview_questions": self.interview_questions,
            "recommendations": self.recommendations,
            "areas_to_explore": self.areas_to_explore,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
            "api_calls_used": self.api_calls_used,
            "fetch_time_seconds": self.fetch_time_seconds,
            "analysis_cost_usd": self.analysis_cost_usd,
            "model_used": self.model_used,
            "confidence_explanation": self.confidence_explanation,
            "data_limitations": self.data_limitations,
        }


@dataclass
class PRFetchResult:
    """Result from fetching PR data."""

    prs: List[PRData]
    username: str
    total_count: int
    repos_contributed: List[str]
    api_calls_used: int
    fetch_time_seconds: float
    from_cache: bool = False

    @property
    def authored_count(self) -> int:
        """Count of PRs authored by user."""
        return sum(1 for pr in self.prs if pr.author == self.username)

    @property
    def assigned_count(self) -> int:
        """Count of PRs assigned to user but not authored."""
        return sum(
            1 for pr in self.prs if pr.assigned_to_user and pr.author != self.username
        )
