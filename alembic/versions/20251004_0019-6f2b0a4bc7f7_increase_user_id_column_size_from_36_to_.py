"""increase user_id column size from 36 to 50 in pr_analysis_records

Revision ID: 6f2b0a4bc7f7
Revises: 332cc2d7e766
Create Date: 2025-10-04 00:19:53.154051

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6f2b0a4bc7f7"
down_revision: Union[str, None] = "332cc2d7e766"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Increase user_id column size from VARCHAR(36) to VARCHAR(50)
    # Using raw SQL because op.alter_column() doesn't work reliably for varchar size changes
    op.execute("ALTER TABLE pr_analysis_records ALTER COLUMN user_id TYPE VARCHAR(50)")


def downgrade() -> None:
    # Revert user_id column size from VARCHAR(50) to VARCHAR(36)
    op.execute("ALTER TABLE pr_analysis_records ALTER COLUMN user_id TYPE VARCHAR(36)")
