"""Add Scale+ tier and batch history tracking

Revision ID: add_scale_plus_batch_history
Revises: add_batch_id
Create Date: 2025-08-02 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "add_scale_plus_batch_history"
down_revision: Union[str, None] = "add_batch_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Check and add priority support fields to users table
    result = conn.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='users' AND column_name='is_priority_support'"
        )
    )
    if not result.fetchone():
        op.add_column(
            "users",
            sa.Column(
                "is_priority_support",
                sa.Boolean(),
                nullable=False,
                server_default="false",
            ),
        )

    result = conn.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='users' AND column_name='response_time_hours'"
        )
    )
    if not result.fetchone():
        op.add_column(
            "users",
            sa.Column(
                "response_time_hours", sa.Integer(), nullable=False, server_default="48"
            ),
        )

    # Check if contact_messages table exists
    result = conn.execute(
        text(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'contact_messages')"
        )
    )
    contact_messages_exists = result.scalar()

    if contact_messages_exists:
        # Add priority fields to contact_messages table if they don't exist
        result = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='contact_messages' AND column_name='is_priority'"
            )
        )
        if not result.fetchone():
            op.add_column(
                "contact_messages",
                sa.Column(
                    "is_priority", sa.Boolean(), nullable=False, server_default="false"
                ),
            )

        result = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='contact_messages' AND column_name='priority_level'"
            )
        )
        if not result.fetchone():
            op.add_column(
                "contact_messages",
                sa.Column(
                    "priority_level", sa.Integer(), nullable=False, server_default="0"
                ),
            )

        result = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='contact_messages' AND column_name='target_response_hours'"
            )
        )
        if not result.fetchone():
            op.add_column(
                "contact_messages",
                sa.Column(
                    "target_response_hours",
                    sa.Integer(),
                    nullable=False,
                    server_default="48",
                ),
            )

        result = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='contact_messages' AND column_name='sla_status'"
            )
        )
        if not result.fetchone():
            op.add_column(
                "contact_messages",
                sa.Column(
                    "sla_status", sa.String(20), nullable=False, server_default="green"
                ),
            )

    # Check if batch_analyses table exists
    result = conn.execute(
        text(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'batch_analyses')"
        )
    )
    batch_analyses_exists = result.scalar()

    if not batch_analyses_exists:
        # Create batch_analyses table
        op.create_table(
            "batch_analyses",
            sa.Column("batch_id", sa.String(36), nullable=False),
            sa.Column("user_id", sa.String(50), nullable=False),
            sa.Column("repository_count", sa.Integer(), nullable=False),
            sa.Column(
                "successful_count", sa.Integer(), nullable=False, server_default="0"
            ),
            sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "status", sa.String(20), nullable=False, server_default="pending"
            ),
            sa.Column("processing_time_ms", sa.Integer(), nullable=True),
            sa.Column("total_cost", sa.Float(), nullable=True),
            sa.Column("contexts", sa.Text(), nullable=False),
            sa.Column("error_messages", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            # Note: This foreign key might fail if users.user_id doesn't exist
            # We'll handle this gracefully
            sa.PrimaryKeyConstraint("batch_id"),
        )

        # Create indexes for batch_analyses
        op.create_index("ix_batch_analyses_user_id", "batch_analyses", ["user_id"])
        op.create_index(
            "ix_batch_analyses_created_at", "batch_analyses", ["created_at"]
        )

    # Create index for contact_messages if table exists and index doesn't
    if contact_messages_exists:
        result = conn.execute(
            text(
                "SELECT indexname FROM pg_indexes "
                "WHERE tablename='contact_messages' AND indexname='ix_contact_messages_priority_level'"
            )
        )
        if not result.fetchone():
            op.create_index(
                "ix_contact_messages_priority_level",
                "contact_messages",
                ["priority_level"],
            )


def downgrade() -> None:
    conn = op.get_bind()

    # Drop indexes if they exist
    result = conn.execute(
        text(
            "SELECT indexname FROM pg_indexes "
            "WHERE tablename='contact_messages' AND indexname='ix_contact_messages_priority_level'"
        )
    )
    if result.fetchone():
        op.drop_index("ix_contact_messages_priority_level", "contact_messages")

    result = conn.execute(
        text(
            "SELECT indexname FROM pg_indexes "
            "WHERE tablename='batch_analyses' AND indexname='ix_batch_analyses_created_at'"
        )
    )
    if result.fetchone():
        op.drop_index("ix_batch_analyses_created_at", "batch_analyses")

    result = conn.execute(
        text(
            "SELECT indexname FROM pg_indexes "
            "WHERE tablename='batch_analyses' AND indexname='ix_batch_analyses_user_id'"
        )
    )
    if result.fetchone():
        op.drop_index("ix_batch_analyses_user_id", "batch_analyses")

    # Drop batch_analyses table if exists
    result = conn.execute(
        text(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'batch_analyses')"
        )
    )
    if result.scalar():
        op.drop_table("batch_analyses")

    # Remove priority fields from contact_messages if they exist
    result = conn.execute(
        text(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'contact_messages')"
        )
    )
    if result.scalar():
        for column in [
            "sla_status",
            "target_response_hours",
            "priority_level",
            "is_priority",
        ]:
            result = conn.execute(
                text(
                    f"SELECT column_name FROM information_schema.columns "
                    f"WHERE table_name='contact_messages' AND column_name='{column}'"
                )
            )
            if result.fetchone():
                op.drop_column("contact_messages", column)

    # Remove priority support fields from users
    for column in ["response_time_hours", "is_priority_support"]:
        result = conn.execute(
            text(
                f"SELECT column_name FROM information_schema.columns "
                f"WHERE table_name='users' AND column_name='{column}'"
            )
        )
        if result.fetchone():
            op.drop_column("users", column)
