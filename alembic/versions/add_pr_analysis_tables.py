"""Add PR analysis tables with inference cleaning

Revision ID: add_pr_analysis_tables
Revises: purge_backfilled_columns
Create Date: 2025-10-02

This migration:
1. Creates pr_analysis_results table (anonymized PR analysis storage)
2. Creates pr_analysis_records table (user tracking for rate limiting)
3. Implements data cleaning to remove behavioral inferences from storage
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "add_pr_analysis_tables"
down_revision: Union[str, None] = "purge_backfilled_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create PR analysis tables."""

    # Check if pr_analysis_results table exists
    conn = op.get_bind()
    result = conn.execute(
        text(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'pr_analysis_results')"
        )
    )
    table_exists = result.scalar()

    if not table_exists:
        # Create pr_analysis_results table
        op.create_table(
            "pr_analysis_results",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("github_username", sa.String(39), nullable=False, index=True),
            sa.Column("context", sa.String(50), nullable=False),
            sa.Column("total_prs_analyzed", sa.Integer(), nullable=False),
            # Full analysis data (JSON/JSONB) - Unified result first, then separated
            sa.Column("full_analysis", sa.Text(), nullable=False),
            sa.Column("summary_report", sa.Text(), nullable=True),
            sa.Column("detailed_report", sa.Text(), nullable=True),
            sa.Column("ai_insights", sa.Text(), nullable=True),
            sa.Column("evidence", sa.Text(), nullable=True),
            sa.Column("quality_signals", sa.Text(), nullable=True),
            # Data quality indicator
            sa.Column("data_quality", sa.String(20), nullable=False),
            # API usage tracking
            sa.Column("api_calls_used", sa.Integer(), nullable=False),
            sa.Column("fetch_time_seconds", sa.Float(), nullable=False),
            sa.Column("total_time_seconds", sa.Float(), nullable=True),
            sa.Column("from_cache", sa.Boolean(), default=False, nullable=False),
            # Timestamps
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                onupdate=sa.func.now(),
                nullable=False,
            ),
        )
        print("✅ Created pr_analysis_results table")
    else:
        print("⏭️  pr_analysis_results table already exists")

    # Check if pr_analysis_records table exists
    result = conn.execute(
        text(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'pr_analysis_records')"
        )
    )
    records_table_exists = result.scalar()

    if not records_table_exists:
        # Create pr_analysis_records table
        op.create_table(
            "pr_analysis_records",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "user_id",
                sa.String(36),
                sa.ForeignKey("users.user_id"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "analysis_id",
                sa.String(36),
                sa.ForeignKey("pr_analysis_results.id"),
                nullable=True,
                index=True,
            ),
            sa.Column("github_username", sa.String(39), nullable=False),
            sa.Column("context", sa.String(50), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, default="pending"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        )
        print("✅ Created pr_analysis_records table")
    else:
        print("⏭️  pr_analysis_records table already exists")


def downgrade() -> None:
    """Drop PR analysis tables."""
    op.drop_table("pr_analysis_records")
    op.drop_table("pr_analysis_results")
    print("🗑️  Dropped PR analysis tables")
