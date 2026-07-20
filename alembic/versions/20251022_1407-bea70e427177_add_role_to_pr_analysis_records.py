"""add_role_to_pr_analysis_records

Revision ID: bea70e427177
Revises: b579d682f397
Create Date: 2025-10-22 14:07:47.361961

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bea70e427177"
down_revision: Union[str, None] = "b579d682f397"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add role column to pr_analysis_records table
    # Default to 'mid' for existing records (neutral role level)
    op.add_column(
        "pr_analysis_records",
        sa.Column("role", sa.String(length=20), nullable=False, server_default="mid"),
    )


def downgrade() -> None:
    # Remove role column
    op.drop_column("pr_analysis_records", "role")
