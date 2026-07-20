"""Add portfolio analysis and candidate assessment tables

Revision ID: add_portfolio_analysis_tables
Revises: add_pr_count_api_calls
Create Date: 2025-10-17

This migration:
1. Creates portfolio_analyses table (complete portfolio analysis storage)
2. Creates candidate_assessments table (unified tracking for Portfolio + PR analysis)
3. Implements "1 username = 1 assessment per month" counting logic
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_portfolio_analysis_tables"
down_revision: Union[str, None] = "6f2b0a4bc7f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create portfolio analysis and candidate assessment tables."""

    conn = op.get_bind()

    # Check if portfolio_analyses table exists (works for both SQLite and PostgreSQL)
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()
    table_exists = "portfolio_analyses" in existing_tables

    if not table_exists:
        # Create portfolio_analyses table
        op.create_table(
            "portfolio_analyses",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "user_id",
                sa.String(50),
                sa.ForeignKey("users.user_id"),
                nullable=False,
                index=True,
            ),
            sa.Column("github_username", sa.String(39), nullable=False, index=True),
            sa.Column("context", sa.String(50), nullable=False),
            # Repository counts
            sa.Column("total_repos", sa.Integer(), nullable=False),
            sa.Column("repos_analyzed", sa.Integer(), nullable=False),
            sa.Column("repos_skipped", sa.Integer(), nullable=False),
            # Full analysis data (JSON/JSONB)
            sa.Column("full_analysis", sa.Text(), nullable=False),
            # Optional S3 storage (future-proofing)
            sa.Column("s3_key", sa.String(255), nullable=True),
            # Analysis metadata (always in DB for querying/filtering)
            sa.Column("analysis_metadata", sa.Text(), nullable=False),
            # Performance metrics
            sa.Column("processing_time_seconds", sa.Float(), nullable=False),
            sa.Column("token_count", sa.Integer(), nullable=False),
            sa.Column("api_cost", sa.Float(), nullable=False),
            sa.Column(
                "api_calls_used", sa.Integer(), nullable=False, server_default="1"
            ),
            # Cache tracking
            sa.Column("from_cache", sa.Boolean(), default=False, nullable=False),
            sa.Column("cache_expires_at", sa.DateTime(timezone=True), nullable=True),
            # Analysis results summary (for quick access without parsing JSON)
            sa.Column("key_observations_count", sa.Integer(), nullable=False),
            sa.Column("evidence_patterns_count", sa.Integer(), nullable=False),
            sa.Column("interview_questions_count", sa.Integer(), nullable=False),
            sa.Column("timeline_gaps_count", sa.Integer(), nullable=False),
            # Quality indicators
            sa.Column(
                "analysis_version",
                sa.String(20),
                nullable=False,
                server_default="1.0.0",
            ),
            sa.Column("data_quality", sa.String(20), nullable=False),
            # Privacy & soft delete
            sa.Column("allow_training", sa.Boolean(), default=True, nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            # Timestamps
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                onupdate=sa.func.now(),
                nullable=False,
            ),
        )
        print("✅ Created portfolio_analyses table")
    else:
        print("⏭️  portfolio_analyses table already exists")

    # Check if candidate_assessments table exists (works for both SQLite and PostgreSQL)
    assessments_table_exists = "candidate_assessments" in existing_tables

    if not assessments_table_exists:
        # Create candidate_assessments table
        op.create_table(
            "candidate_assessments",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "user_id",
                sa.String(50),
                sa.ForeignKey("users.user_id"),
                nullable=False,
                index=True,
            ),
            sa.Column("github_username", sa.String(39), nullable=False, index=True),
            sa.Column("billing_period", sa.String(7), nullable=False, index=True),
            # Analysis types performed this month for this candidate
            sa.Column(
                "portfolio_analysis_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "pr_analysis_count", sa.Integer(), nullable=False, server_default="0"
            ),
            # First and last analysis timestamps
            sa.Column(
                "first_analyzed_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "last_analyzed_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            # Timestamps
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
                index=True,
            ),
        )
        print("✅ Created candidate_assessments table")
    else:
        print("⏭️  candidate_assessments table already exists")


def downgrade() -> None:
    """Drop portfolio analysis and candidate assessment tables."""
    op.drop_table("candidate_assessments")
    op.drop_table("portfolio_analyses")
    print("🗑️  Dropped portfolio analysis tables")
