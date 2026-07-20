# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Database connection management for PostgreSQL.

This module handles async database connections, session management,
and connection pooling using SQLAlchemy 2.0 with asyncpg.
"""

from contextlib import contextmanager
from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from ..utils.config import get_config


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


# Global database components
config = get_config()
DATABASE_URL = config.database_url

# Convert DATABASE_URL to async if needed
if DATABASE_URL.startswith("sqlite"):
    raise RuntimeError(
        "Exiqus requires PostgreSQL; SQLite support was removed. "
        "Point DATABASE_URL at a PostgreSQL instance - for local dev, "
        "run `docker compose up -d postgres` and unset DATABASE_URL to "
        "use the default."
    )
if DATABASE_URL.startswith("postgresql://"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
else:
    # Already async (postgresql+asyncpg://)
    ASYNC_DATABASE_URL = DATABASE_URL

engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=config.debug,  # Log SQL queries in debug mode
    pool_pre_ping=True,  # Validate connections before use
    pool_recycle=3600,  # Recycle connections every hour
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=True,
    autocommit=False,
)

# Create synchronous engine for CLI usage
SYNC_DATABASE_URL = DATABASE_URL
if DATABASE_URL.startswith("postgresql+asyncpg://"):
    SYNC_DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

sync_engine = create_engine(
    SYNC_DATABASE_URL,
    echo=config.debug,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# Create sync session factory for CLI
SyncSessionLocal = sessionmaker(
    sync_engine,
    class_=Session,
    expire_on_commit=False,
    autoflush=True,
    autocommit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session for dependency injection.

    Yields:
        AsyncSession: Database session

    Example:
        ```python
        @app.post("/users/")
        async def create_user(
            user_data: UserCreate,
            db: AsyncSession = Depends(get_db_session)
        ):
            return await create_user_record(db, user_data)
        ```
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_database() -> None:
    """
    Initialize database by creating all tables and running migrations.

    This should be called at application startup.
    """
    from sqlalchemy import text

    async with engine.begin() as conn:
        # Import all models to ensure they're registered
        from . import models  # noqa: F401

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

        # Run evidence column backfill migration (idempotent - safe to run multiple times)
        try:
            # Check if we need to backfill evidence columns
            result = await conn.execute(
                text(
                    """
                    SELECT COUNT(*) as count
                    FROM analysis_results
                    WHERE analysis_method = 'evidence_based'
                    AND screening_insights IS NULL
                    AND full_analysis IS NOT NULL
                """
                )
            )
            count = result.scalar()
            needs_backfill = count is not None and count > 0

            if needs_backfill:
                print("Running evidence column backfill migration...")

                # Backfill evidence columns from full_analysis
                await conn.execute(
                    text(
                        """
                        UPDATE analysis_results
                        SET
                            screening_insights = CASE
                                WHEN full_analysis::jsonb ? 'insights'
                                THEN full_analysis::jsonb->'insights'
                                ELSE NULL
                            END,
                            skill_evolution = CASE
                                WHEN full_analysis::jsonb ? 'questions'
                                THEN full_analysis::jsonb->'questions'
                                ELSE NULL
                            END,
                            behavioral_analysis = CASE
                                WHEN full_analysis::jsonb ? 'recommendations'
                                THEN full_analysis::jsonb->'recommendations'
                                ELSE NULL
                            END,
                            security_practices = CASE
                                WHEN full_analysis::jsonb ? 'green_flags'
                                THEN full_analysis::jsonb->'green_flags'
                                ELSE NULL
                            END,
                            context_alignment = CASE
                                WHEN full_analysis::jsonb ? 'red_flags'
                                THEN full_analysis::jsonb->'red_flags'
                                ELSE NULL
                            END,
                            verification_gaps = CASE
                                WHEN full_analysis::jsonb ? 'areas_to_explore'
                                THEN full_analysis::jsonb->'areas_to_explore'
                                ELSE NULL
                            END,
                            technical_patterns = CASE
                                WHEN full_analysis::jsonb ? 'technical_assessment'
                                THEN full_analysis::jsonb->'technical_assessment'
                                ELSE NULL
                            END,
                            professional_growth = CASE
                                WHEN full_analysis::jsonb ? 'professional_assessment'
                                THEN full_analysis::jsonb->'professional_assessment'
                                ELSE NULL
                            END,
                            communication_style = CASE
                                WHEN full_analysis::jsonb ? 'communication_assessment'
                                THEN full_analysis::jsonb->'communication_assessment'
                                ELSE NULL
                            END,
                            growth_trajectory = CASE
                                WHEN full_analysis::jsonb ? 'growth_assessment'
                                THEN full_analysis::jsonb->'growth_assessment'
                                ELSE NULL
                            END
                        WHERE analysis_method = 'evidence_based'
                        AND screening_insights IS NULL
                        AND full_analysis IS NOT NULL
                    """
                    )
                )

                print("Evidence column backfill completed")

            # Check and remove obsolete columns if they still exist
            result = await conn.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'analysis_results'
                    AND column_name IN ('overall_score', 'confidence_score', 'recommendation')
                """
                )
            )
            obsolete_columns = [row[0] for row in result]

            if obsolete_columns:
                print(f"Removing obsolete columns: {', '.join(obsolete_columns)}")
                for column in obsolete_columns:
                    await conn.execute(
                        text(
                            f"ALTER TABLE analysis_results DROP COLUMN IF EXISTS {column}"
                        )
                    )
                print("Obsolete columns removed")

        except Exception as e:
            # Log but don't fail startup - migrations are best effort
            print(f"Migration warning (non-fatal): {e}")


@contextmanager
def get_sync_db_session() -> Generator[Session, None, None]:
    """
    Get synchronous database session for CLI usage.

    Yields:
        Session: Synchronous database session

    Example:
        ```python
        with get_sync_db_session() as db:
            user = db.query(User).filter(User.email == email).first()
        ```
    """
    with SyncSessionLocal() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


async def close_database() -> None:
    """
    Close database connections.

    This should be called at application shutdown.
    """
    await engine.dispose()
    sync_engine.dispose()
