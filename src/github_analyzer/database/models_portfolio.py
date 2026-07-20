# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Portfolio Analysis and Candidate Assessment database models.

These models support the unified Candidate Assessment Portal that
combines Portfolio Analysis and PR Analysis into a single usage tracking system.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .connection import Base
from .models import AnalysisStatus

if TYPE_CHECKING:
    from .models import User  # noqa: F401


class PortfolioAnalysis(Base):
    """
    Portfolio analysis result storage model.

    Stores complete portfolio analysis results for a GitHub username,
    including all repositories analyzed and the generated insights.
    """

    __tablename__ = "portfolio_analyses"

    # Primary key - UUID
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Foreign key to user
    user_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("users.user_id"), nullable=False, index=True
    )

    # GitHub username analyzed
    github_username: Mapped[str] = mapped_column(
        String(39), nullable=False, index=True
    )  # GitHub username max length is 39

    # Analysis parameters
    context: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # startup, enterprise, agency, open_source

    role: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # junior, mid, senior - affects interview questions

    # Repository counts
    total_repos: Mapped[int] = mapped_column(Integer, nullable=False)
    repos_analyzed: Mapped[int] = mapped_column(Integer, nullable=False)
    repos_skipped: Mapped[int] = mapped_column(Integer, nullable=False)

    # Full analysis data (JSON/JSONB)
    full_analysis: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # Complete JSON with all analysis data

    # Optional S3 storage (future-proofing)
    s3_key: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )  # e.g., "analyses/abc123/result.json"

    # Analysis metadata (always in DB for querying/filtering)
    analysis_metadata: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # JSON with repo_count, token_count, cost, etc.

    # Performance metrics
    processing_time_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    api_cost: Mapped[float] = mapped_column(Float, nullable=False)
    api_calls_used: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Cache tracking
    from_cache: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cache_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # 30-day TTL

    # Processing status
    status: Mapped[AnalysisStatus] = mapped_column(
        Enum(AnalysisStatus), default=AnalysisStatus.PENDING, nullable=False, index=True
    )

    # Real-time progress tracking (for async background processing)
    progress_stage: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # fetching, analyzing, generating, finalizing
    progress_percent: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # 0-100
    progress_message: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )  # Human-readable progress message

    # Analysis results summary (for quick access without parsing JSON)
    key_observations_count: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_patterns_count: Mapped[int] = mapped_column(Integer, nullable=False)
    interview_questions_count: Mapped[int] = mapped_column(Integer, nullable=False)
    timeline_gaps_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # Quality indicators
    analysis_version: Mapped[str] = mapped_column(
        String(20), default="1.0.0", nullable=False
    )
    data_quality: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # excellent, good, limited, insufficient

    # Privacy & soft delete
    allow_training: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User")

    @property
    def is_deleted(self) -> bool:
        """Check if the analysis is soft deleted."""
        return self.deleted_at is not None

    @property
    def is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if not self.from_cache or not self.cache_expires_at:
            return False
        return datetime.now(timezone.utc) < self.cache_expires_at

    def __repr__(self) -> str:
        return (
            f"<PortfolioAnalysis(id='{self.id}', "
            f"github_username='{self.github_username}', "
            f"repos_analyzed={self.repos_analyzed})>"
        )


class PortfolioAnalysisCache(Base):
    """
    Cache table for portfolio analyses with deduplication.

    Separate from PortfolioAnalysis to enable:
    - Clean historical storage (PortfolioAnalysis) never deleted
    - Aggressive cache clearing without losing training data
    - Database-level deduplication via UNIQUE constraint
    - Race condition protection

    Cache key: (github_username, context, role)
    """

    __tablename__ = "portfolio_analysis_cache"

    __table_args__ = (
        UniqueConstraint(
            "github_username",
            "context",
            "role",
            name="uq_portfolio_cache_context",
        ),
    )

    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Foreign key to result storage
    result_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("portfolio_analyses.id"), nullable=False, index=True
    )

    # Cache key components
    github_username: Mapped[str] = mapped_column(String(39), nullable=False, index=True)
    context: Mapped[str] = mapped_column(String(50), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)

    # Cache expiry (30-day TTL)
    cache_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship to result
    result: Mapped["PortfolioAnalysis"] = relationship("PortfolioAnalysis")

    @property
    def is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        return datetime.now(timezone.utc) < self.cache_expires_at

    def __repr__(self) -> str:
        return (
            f"<PortfolioAnalysisCache(id='{self.id}', "
            f"github_username='{self.github_username}', "
            f"context='{self.context}', role='{self.role}')>"
        )


class CandidateAssessment(Base):
    """
    Candidate assessment tracking model.

    Tracks unique GitHub usernames analyzed per month to implement the
    "1 username = 1 assessment" counting logic across Portfolio and PR Analysis.

    Core principle: Analyzing the same GitHub username with Portfolio Analysis,
    PR Analysis, or both counts as 1 candidate assessment per month.
    """

    __tablename__ = "candidate_assessments"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to user
    user_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("users.user_id"), nullable=False, index=True
    )

    # GitHub username being assessed
    github_username: Mapped[str] = mapped_column(String(39), nullable=False, index=True)

    # Billing period (YYYY-MM format)
    billing_period: Mapped[str] = mapped_column(
        String(7), nullable=False, index=True
    )  # e.g., "2025-10"

    # Analysis types performed this month for this candidate
    portfolio_analysis_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    pr_analysis_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # First and last analysis timestamps
    first_analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<CandidateAssessment(id={self.id}, "
            f"user_id='{self.user_id}', "
            f"github_username='{self.github_username}', "
            f"period='{self.billing_period}', "
            f"portfolio={self.portfolio_analysis_count}, "
            f"pr={self.pr_analysis_count})>"
        )


class RepositoryDeepDive(Base):
    """
    Repository deep dive tracking model.

    Tracks individual repository analyses (not tied to candidate assessment).
    Used for standalone repo analysis separate from full candidate evaluation.
    """

    __tablename__ = "repository_deep_dives"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to user
    user_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("users.user_id"), nullable=False, index=True
    )

    # Repository analyzed (format: "owner/repo")
    repository_name: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )

    # Billing period (YYYY-MM format)
    billing_period: Mapped[str] = mapped_column(
        String(7), nullable=False, index=True
    )  # e.g., "2025-10"

    # Link to the actual analysis result
    analysis_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("analysis_results.id"), nullable=True
    )

    # Timestamps
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<RepositoryDeepDive(id={self.id}, "
            f"user_id='{self.user_id}', "
            f"repository='{self.repository_name}', "
            f"period='{self.billing_period}')>"
        )
