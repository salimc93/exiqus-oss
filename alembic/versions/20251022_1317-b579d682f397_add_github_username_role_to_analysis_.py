"""add_github_username_role_to_analysis_results

Revision ID: b579d682f397
Revises: add_analysis_cache_tables
Create Date: 2025-10-22 13:17:58.116862

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b579d682f397"
down_revision: Union[str, None] = "add_analysis_cache_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add github_username column (nullable for backward compatibility + free tier)
    op.add_column(
        "analysis_results",
        sa.Column("github_username", sa.String(length=39), nullable=True),
    )
    op.create_index(
        op.f("ix_analysis_results_github_username"),
        "analysis_results",
        ["github_username"],
        unique=False,
    )

    # Add role column (nullable for backward compatibility)
    op.add_column(
        "analysis_results", sa.Column("role", sa.String(length=20), nullable=True)
    )


def downgrade() -> None:
    # Drop columns in reverse order
    op.drop_column("analysis_results", "role")
    op.drop_index(
        op.f("ix_analysis_results_github_username"), table_name="analysis_results"
    )
    op.drop_column("analysis_results", "github_username")
