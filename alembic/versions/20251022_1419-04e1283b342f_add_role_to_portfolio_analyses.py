"""add_role_to_portfolio_analyses

Revision ID: 04e1283b342f
Revises: bea70e427177
Create Date: 2025-10-22 14:19:27.008927

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "04e1283b342f"
down_revision: Union[str, None] = "bea70e427177"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add role column to portfolio_analyses table with index
    # Default to 'mid' for existing records (neutral role level)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("portfolio_analyses")]

    if "role" not in columns:
        op.add_column(
            "portfolio_analyses",
            sa.Column(
                "role", sa.String(length=20), nullable=False, server_default="mid"
            ),
        )
        # Create index on role column
        op.create_index(
            op.f("ix_portfolio_analyses_role"),
            "portfolio_analyses",
            ["role"],
            unique=False,
        )
        print("✅ Added role column to portfolio_analyses")
    else:
        print("⏭️  role column already exists in portfolio_analyses")


def downgrade() -> None:
    # Remove index first
    op.drop_index(op.f("ix_portfolio_analyses_role"), table_name="portfolio_analyses")
    # Remove role column
    op.drop_column("portfolio_analyses", "role")
