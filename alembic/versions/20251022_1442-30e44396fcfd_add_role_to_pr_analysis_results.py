"""add_role_to_pr_analysis_results

Revision ID: 30e44396fcfd
Revises: 04e1283b342f
Create Date: 2025-10-22 14:42:52.530759

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "30e44396fcfd"
down_revision: Union[str, None] = "04e1283b342f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add role column to pr_analysis_results table
    # Default to 'mid' for existing records (neutral role level)
    op.add_column(
        "pr_analysis_results",
        sa.Column("role", sa.String(length=20), nullable=False, server_default="mid"),
    )


def downgrade() -> None:
    # Remove role column
    op.drop_column("pr_analysis_results", "role")
