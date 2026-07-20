"""fix_pr_analysis_records_autoincrement

Revision ID: 7b42c9bc6ae9
Revises: cfae7ff43be3
Create Date: 2025-10-23 14:19:20.455697

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7b42c9bc6ae9"
down_revision: Union[str, None] = "cfae7ff43be3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fix pr_analysis_records table to use INTEGER PRIMARY KEY for autoincrement."""

    # SQLite doesn't support ALTER COLUMN, so we need to recreate the table

    # 1. Create new table with correct schema
    op.create_table(
        "pr_analysis_records_new",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("user_id", sa.String(length=50), nullable=False),
        sa.Column("analysis_id", sa.Text(), nullable=True),
        sa.Column("github_username", sa.String(length=39), nullable=False),
        sa.Column("pr_count", sa.Integer(), nullable=False),
        sa.Column("api_calls_used", sa.Integer(), nullable=False),
        sa.Column("context", sa.String(length=50), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="mid"),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="pending"
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["analysis_id"],
            ["pr_analysis_results.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # 2. Copy data from old table to new table (let id auto-generate)
    op.execute(
        """
        INSERT INTO pr_analysis_records_new
            (user_id, analysis_id, github_username, pr_count, api_calls_used,
             context, role, status, error_message, created_at, completed_at)
        SELECT
            user_id, analysis_id, github_username, pr_count, api_calls_used,
            context, role, status, error_message, created_at, completed_at
        FROM pr_analysis_records
    """
    )

    # 3. Drop old table
    op.drop_table("pr_analysis_records")

    # 4. Rename new table to original name
    op.rename_table("pr_analysis_records_new", "pr_analysis_records")

    # 5. Recreate indexes
    op.create_index(
        "ix_pr_analysis_records_user_id", "pr_analysis_records", ["user_id"]
    )
    op.create_index(
        "ix_pr_analysis_records_analysis_id", "pr_analysis_records", ["analysis_id"]
    )


def downgrade() -> None:
    """Revert pr_analysis_records table to BIGINT primary key."""

    # 1. Create old table structure with BIGINT
    op.create_table(
        "pr_analysis_records_old",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.String(length=50), nullable=False),
        sa.Column("analysis_id", sa.Text(), nullable=True),
        sa.Column("github_username", sa.String(length=39), nullable=False),
        sa.Column("pr_count", sa.Integer(), nullable=False),
        sa.Column("api_calls_used", sa.Integer(), nullable=False),
        sa.Column("context", sa.String(length=50), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="mid"),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="pending"
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["analysis_id"],
            ["pr_analysis_results.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # 2. Copy data back
    op.execute(
        """
        INSERT INTO pr_analysis_records_old
            (id, user_id, analysis_id, github_username, pr_count, api_calls_used,
             context, role, status, error_message, created_at, completed_at)
        SELECT
            id, user_id, analysis_id, github_username, pr_count, api_calls_used,
            context, role, status, error_message, created_at, completed_at
        FROM pr_analysis_records
    """
    )

    # 3. Drop new table
    op.drop_table("pr_analysis_records")

    # 4. Rename old table back
    op.rename_table("pr_analysis_records_old", "pr_analysis_records")

    # 5. Recreate indexes
    op.create_index(
        "ix_pr_analysis_records_user_id", "pr_analysis_records", ["user_id"]
    )
    op.create_index(
        "ix_pr_analysis_records_analysis_id", "pr_analysis_records", ["analysis_id"]
    )
