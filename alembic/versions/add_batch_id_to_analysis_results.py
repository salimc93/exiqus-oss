"""Add batch_id to analysis_results table

Revision ID: add_batch_id
Revises:
Create Date: 2025-07-30 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "add_batch_id"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if column exists before adding
    conn = op.get_bind()
    result = conn.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='analysis_results' AND column_name='batch_id'"
        )
    )
    if not result.fetchone():
        # Add batch_id column to analysis_results table
        op.add_column(
            "analysis_results", sa.Column("batch_id", sa.String(36), nullable=True)
        )

    # Check if index exists before creating
    result = conn.execute(
        text(
            "SELECT indexname FROM pg_indexes "
            "WHERE tablename='analysis_results' AND indexname='ix_analysis_results_batch_id'"
        )
    )
    if not result.fetchone():
        # Create index on batch_id for faster queries
        op.create_index(
            "ix_analysis_results_batch_id", "analysis_results", ["batch_id"]
        )


def downgrade() -> None:
    # Drop index first
    op.drop_index("ix_analysis_results_batch_id", "analysis_results")

    # Drop the column
    op.drop_column("analysis_results", "batch_id")
