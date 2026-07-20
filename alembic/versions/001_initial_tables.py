"""Create initial tables

Revision ID: 001_initial
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if users table exists
    conn = op.get_bind()
    result = conn.execute(
        text(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'users')"
        )
    )
    table_exists = result.scalar()

    if table_exists:
        print("Tables already exist, skipping creation...")
        return

    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("github_username", sa.String(255), nullable=True),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("is_admin", sa.Boolean(), nullable=False, default=False),
        sa.Column("subscription_plan", sa.String(50), nullable=False, default="free"),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(255), nullable=True),
        sa.Column("monthly_analysis_count", sa.Integer(), nullable=False, default=0),
        sa.Column("last_analysis_reset", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index(
        "ix_users_github_username", "users", ["github_username"], unique=True
    )
    op.create_index(
        "ix_users_stripe_customer_id", "users", ["stripe_customer_id"], unique=True
    )

    # Create analysis_results table
    op.create_table(
        "analysis_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("repository_url", sa.String(), nullable=False),
        sa.Column("repository_name", sa.String(), nullable=False),
        sa.Column("analysis_data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("report_version", sa.String(10), nullable=False, default="1.0"),
        sa.Column("status", sa.String(50), nullable=False, default="completed"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analysis_results_user_id", "analysis_results", ["user_id"])
    op.create_index(
        "ix_analysis_results_repository_url", "analysis_results", ["repository_url"]
    )
    op.create_index(
        "ix_analysis_results_created_at", "analysis_results", ["created_at"]
    )

    # Create billing_transactions table
    op.create_table(
        "billing_transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("stripe_payment_intent_id", sa.String(255), nullable=True),
        sa.Column("stripe_invoice_id", sa.String(255), nullable=True),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, default="USD"),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_billing_transactions_user_id", "billing_transactions", ["user_id"]
    )
    op.create_index(
        "ix_billing_transactions_stripe_payment_intent_id",
        "billing_transactions",
        ["stripe_payment_intent_id"],
    )


def downgrade() -> None:
    op.drop_table("billing_transactions")
    op.drop_table("analysis_results")
    op.drop_table("users")
