"""
Add concurrency_mode field to batch_analyses table.

This migration adds a concurrency_mode column to track whether batch analyses
were run in sequential, balanced, or fast mode.
"""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.github_analyzer.config import settings


async def upgrade():
    """Add concurrency_mode column to batch_analyses table."""
    engine = create_async_engine(settings.DATABASE_URL, echo=True)

    async with engine.begin() as conn:
        # Check if column already exists
        result = await conn.execute(
            text(
                """
                SELECT COUNT(*) 
                FROM pragma_table_info('batch_analyses') 
                WHERE name='concurrency_mode'
            """
            )
        )
        column_exists = result.scalar() > 0

        if not column_exists:
            # Add the concurrency_mode column with default value
            await conn.execute(
                text(
                    """
                    ALTER TABLE batch_analyses 
                    ADD COLUMN concurrency_mode VARCHAR(20) DEFAULT 'sequential' NOT NULL
                """
                )
            )
            print("✅ Added concurrency_mode column to batch_analyses table")
        else:
            print("ℹ️ concurrency_mode column already exists")

    await engine.dispose()


async def downgrade():
    """Remove concurrency_mode column from batch_analyses table."""
    engine = create_async_engine(settings.DATABASE_URL, echo=True)

    async with engine.begin() as conn:
        # SQLite doesn't support DROP COLUMN directly, need to recreate table
        # For now, we'll just log that downgrade isn't implemented
        print("⚠️ Downgrade not implemented for SQLite")

    await engine.dispose()


if __name__ == "__main__":
    print("Running migration: add_concurrency_mode_to_batch_analyses")
    asyncio.run(upgrade())
