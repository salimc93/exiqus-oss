"""Add portfolio and PR analysis cache tables

Revision ID: add_analysis_cache_tables
Revises: add_portfolio_analysis_tables
Create Date: 2025-10-22

This migration:
1. Creates portfolio_analysis_cache table (separate cache from storage)
2. Creates pr_analysis_cache table (separate cache from storage)
3. Implements UNIQUE constraint for deduplication: (github_username, context, role)

Storage + Cache Separation:
- PortfolioAnalysis & PRAnalysisResult: Permanent historical storage (never deleted)
- PortfolioAnalysisCache & PRAnalysisCache: Temporary cache (can be cleared)
- Benefits: Clean training data, database-level deduplication, race condition protection
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_analysis_cache_tables"
down_revision: Union[str, None] = "add_portfolio_analysis_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create analysis cache tables with deduplication."""

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # 1. Create portfolio_analysis_cache table
    portfolio_cache_exists = "portfolio_analysis_cache" in existing_tables

    if not portfolio_cache_exists:
        op.create_table(
            "portfolio_analysis_cache",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "result_id",
                sa.String(36),
                sa.ForeignKey("portfolio_analyses.id"),
                nullable=False,
                index=True,
            ),
            sa.Column("github_username", sa.String(39), nullable=False, index=True),
            sa.Column("context", sa.String(50), nullable=False),
            sa.Column("role", sa.String(20), nullable=False),
            sa.Column(
                "cache_expires_at",
                sa.DateTime(timezone=True),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            # UNIQUE constraint for deduplication
            sa.UniqueConstraint(
                "github_username",
                "context",
                "role",
                name="uq_portfolio_cache_context",
            ),
        )
        print("✅ Created portfolio_analysis_cache table")
    else:
        print("⏭️  portfolio_analysis_cache table already exists")

    # 2. Create pr_analysis_cache table
    pr_cache_exists = "pr_analysis_cache" in existing_tables

    if not pr_cache_exists:
        op.create_table(
            "pr_analysis_cache",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "result_id",
                sa.String(36),
                sa.ForeignKey("pr_analysis_results.id"),
                nullable=False,
                index=True,
            ),
            sa.Column("github_username", sa.String(39), nullable=False, index=True),
            sa.Column("context", sa.String(50), nullable=False),
            sa.Column("role", sa.String(20), nullable=False),
            sa.Column(
                "cache_expires_at",
                sa.DateTime(timezone=True),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            # UNIQUE constraint for deduplication
            sa.UniqueConstraint(
                "github_username",
                "context",
                "role",
                name="uq_pr_cache_context",
            ),
        )
        print("✅ Created pr_analysis_cache table")
    else:
        print("⏭️  pr_analysis_cache table already exists")


def downgrade() -> None:
    """Drop analysis cache tables."""
    op.drop_table("pr_analysis_cache")
    op.drop_table("portfolio_analysis_cache")
    print("🗑️  Dropped analysis cache tables")
