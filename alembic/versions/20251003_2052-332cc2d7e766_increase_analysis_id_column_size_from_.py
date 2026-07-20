"""increase analysis_id column size from 36 to 50

Revision ID: 332cc2d7e766
Revises: add_pr_count_api_calls
Create Date: 2025-10-03 20:52:34.095807

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "332cc2d7e766"
down_revision: Union[str, None] = "add_pr_count_api_calls"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Increase analysis_id column size from VARCHAR(36) to VARCHAR(50)
    # Using raw SQL because op.alter_column doesn't work reliably for varchar size changes
    op.execute(
        "ALTER TABLE pr_analysis_records ALTER COLUMN analysis_id TYPE VARCHAR(50)"
    )


def downgrade() -> None:
    # Revert analysis_id column size from VARCHAR(50) to VARCHAR(36)
    op.execute(
        "ALTER TABLE pr_analysis_records ALTER COLUMN analysis_id TYPE VARCHAR(36)"
    )
