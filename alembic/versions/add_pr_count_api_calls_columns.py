"""Add pr_count and api_calls_used to pr_analysis_records

Revision ID: add_pr_count_api_calls
Revises: add_pr_analysis_tables
Create Date: 2025-10-03

This migration adds missing columns to pr_analysis_records:
- pr_count: Number of PRs analyzed
- api_calls_used: Number of GitHub API calls made
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "add_pr_count_api_calls"
down_revision: Union[str, None] = "purge_pr_analysis_inferences"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add pr_count and api_calls_used columns."""

    conn = op.get_bind()

    # Check if pr_count column exists
    result = conn.execute(
        text(
            "SELECT EXISTS (SELECT FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'pr_analysis_records' "
            "AND column_name = 'pr_count')"
        )
    )
    pr_count_exists = result.scalar()

    if not pr_count_exists:
        op.add_column(
            "pr_analysis_records",
            sa.Column("pr_count", sa.Integer(), nullable=False, server_default="0"),
        )
        print("✅ Added pr_count column to pr_analysis_records")
    else:
        print("⏭️  pr_count column already exists")

    # Check if api_calls_used column exists
    result = conn.execute(
        text(
            "SELECT EXISTS (SELECT FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'pr_analysis_records' "
            "AND column_name = 'api_calls_used')"
        )
    )
    api_calls_exists = result.scalar()

    if not api_calls_exists:
        op.add_column(
            "pr_analysis_records",
            sa.Column(
                "api_calls_used", sa.Integer(), nullable=False, server_default="0"
            ),
        )
        print("✅ Added api_calls_used column to pr_analysis_records")
    else:
        print("⏭️  api_calls_used column already exists")


def downgrade() -> None:
    """Remove pr_count and api_calls_used columns."""

    op.drop_column("pr_analysis_records", "api_calls_used")
    op.drop_column("pr_analysis_records", "pr_count")
