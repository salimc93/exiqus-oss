# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Database migration system for schema versioning and updates.

This module provides utilities for managing database schema migrations
in a safe and versioned manner for production deployments.
"""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from sqlalchemy import DateTime, Text, select, text
from sqlalchemy.orm import Mapped, mapped_column

from .connection import AsyncSessionLocal, Base, engine

logger = logging.getLogger(__name__)


class MigrationRecord(Base):
    """Track applied database migrations."""

    __tablename__ = "migration_history"

    # Migration identifier (filename without extension)
    migration_id: Mapped[str] = mapped_column(Text, primary_key=True)

    # Migration description
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # When the migration was applied
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Migration SQL content hash for verification
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<MigrationRecord(id='{self.migration_id}', "
            f"applied_at='{self.applied_at}')>"
        )


class Migration:
    """Represents a single database migration."""

    def __init__(
        self,
        migration_id: str,
        description: str,
        up_sql: str,
        down_sql: Optional[str] = None,
    ):
        self.migration_id = migration_id
        self.description = description
        self.up_sql = up_sql
        self.down_sql = down_sql

    @property
    def content_hash(self) -> str:
        """Generate content hash for migration verification."""
        import hashlib

        content = f"{self.migration_id}:{self.description}:{self.up_sql}"
        return hashlib.sha256(content.encode()).hexdigest()


class MigrationManager:
    """Manage database schema migrations."""

    def __init__(self, migrations_dir: Optional[Path] = None):
        """
        Initialize migration manager.

        Args:
            migrations_dir: Directory containing migration files
        """
        if migrations_dir is None:
            # Default to migrations directory in same folder as this file
            migrations_dir = Path(__file__).parent / "migrations"

        self.migrations_dir = Path(migrations_dir)
        self.migrations_dir.mkdir(exist_ok=True)

    async def init_migration_table(self) -> None:
        """Initialize the migration history table."""
        async with engine.begin() as conn:
            # Create migration history table if it doesn't exist
            await conn.run_sync(
                lambda sync_conn: MigrationRecord.metadata.create_all(sync_conn)
            )

        logger.info("Migration history table initialized")

    def load_migrations_from_directory(self) -> List[Migration]:
        """Load all migration files from the migrations directory."""
        migrations = []

        # Look for .sql files in migrations directory
        for sql_file in sorted(self.migrations_dir.glob("*.sql")):
            migration_id = sql_file.stem

            # Read migration content
            content = sql_file.read_text(encoding="utf-8")

            # Parse migration (simple format: description on first line, then SQL)
            lines = content.strip().split("\n")
            if not lines:
                continue

            # First line should be a comment with description
            description = "No description"
            sql_start_idx = 0

            if lines[0].strip().startswith("--"):
                description = lines[0].strip()[2:].strip()
                sql_start_idx = 1

            up_sql = "\n".join(lines[sql_start_idx:]).strip()

            if up_sql:
                migration = Migration(
                    migration_id=migration_id,
                    description=description,
                    up_sql=up_sql,
                )
                migrations.append(migration)

        return migrations

    def create_initial_migrations(self) -> None:
        """Create initial migration files for current schema."""
        # Migration 001: Create users table
        users_migration = """-- Create users table for authentication  # nosec B105
CREATE TABLE users (
    user_id VARCHAR(50) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name VARCHAR(200) NOT NULL,
    company VARCHAR(200),
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_verified BOOLEAN NOT NULL DEFAULT false,
    is_admin BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE,
    usage_quota INTEGER NOT NULL DEFAULT 100,
    usage_consumed INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_is_active ON users(is_active);
"""

        # Migration 002: Create API keys table
        api_keys_migration = """-- Create API keys table for programmatic access  # nosec B105
CREATE TABLE api_keys (
    key_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    key_hash TEXT NOT NULL,
    permissions TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,
    last_used TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX idx_api_keys_is_active ON api_keys(is_active);
"""

        # Migration 003: Create usage records table
        usage_records_migration = """-- Create usage records table for tracking API usage
CREATE TABLE usage_records (
    record_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    endpoint VARCHAR(100) NOT NULL,
    method VARCHAR(10) NOT NULL,
    repository_url TEXT,
    tokens_consumed INTEGER NOT NULL DEFAULT 0,
    cost_incurred VARCHAR(20) NOT NULL DEFAULT '0.00',
    response_time_ms INTEGER NOT NULL,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_usage_records_user_id ON usage_records(user_id);
CREATE INDEX idx_usage_records_created_at ON usage_records(created_at);
CREATE INDEX idx_usage_records_endpoint ON usage_records(endpoint);
"""

        # Migration 004: Create token blacklist table
        token_blacklist_migration = """-- Create token blacklist table for JWT revocation
CREATE TABLE token_blacklist (
    token_id VARCHAR(100) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    token_type VARCHAR(20) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    blacklisted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_token_blacklist_user_id ON token_blacklist(user_id);
CREATE INDEX idx_token_blacklist_expires_at ON token_blacklist(expires_at);
"""  # noqa: S105 - SQL DDL, not a credential

        # Write migration files
        migrations = [
            ("001_create_users_table.sql", users_migration),
            ("002_create_api_keys_table.sql", api_keys_migration),
            ("003_create_usage_records_table.sql", usage_records_migration),
            ("004_create_token_blacklist_table.sql", token_blacklist_migration),
        ]

        for filename, content in migrations:
            migration_file = self.migrations_dir / filename
            if not migration_file.exists():
                migration_file.write_text(content, encoding="utf-8")
                logger.info(f"Created migration file: {filename}")

    async def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration IDs."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(MigrationRecord.migration_id))
            return [row[0] for row in result.fetchall()]

    async def apply_migration(self, migration: Migration) -> None:
        """Apply a single migration."""
        async with AsyncSessionLocal() as session:
            try:
                # Execute the migration SQL
                for statement in migration.up_sql.split(";"):
                    statement = statement.strip()
                    if statement:
                        await session.execute(text(statement))

                # Record the migration
                migration_record = MigrationRecord(
                    migration_id=migration.migration_id,
                    description=migration.description,
                    content_hash=migration.content_hash,
                )
                session.add(migration_record)

                await session.commit()
                logger.info(
                    f"Applied migration: {migration.migration_id} - "
                    f"{migration.description}"
                )

            except Exception:
                await session.rollback()
                raise

    async def run_migrations(self, dry_run: bool = False) -> None:
        """
        Run all pending migrations.

        Args:
            dry_run: If True, show what would be migrated without applying
        """
        await self.init_migration_table()

        # Load all available migrations
        available_migrations = self.load_migrations_from_directory()

        # Get applied migrations
        applied_migration_ids = await self.get_applied_migrations()

        # Find pending migrations
        pending_migrations = [
            migration
            for migration in available_migrations
            if migration.migration_id not in applied_migration_ids
        ]

        if not pending_migrations:
            logger.info("No pending migrations")
            return

        logger.info(f"Found {len(pending_migrations)} pending migrations")

        for migration in pending_migrations:
            if dry_run:
                logger.info(
                    f"Would apply: {migration.migration_id} - {migration.description}"
                )
            else:
                await self.apply_migration(migration)

        if dry_run:
            logger.info("Dry run completed - no migrations were actually applied")
        else:
            logger.info(f"Applied {len(pending_migrations)} migrations successfully")

    async def verify_migrations(self) -> bool:
        """
        Verify that applied migrations match their recorded hashes.

        Returns:
            bool: True if all migrations are valid
        """
        available_migrations = {
            m.migration_id: m for m in self.load_migrations_from_directory()
        }

        async with AsyncSessionLocal() as session:
            applied_records = await session.execute(select(MigrationRecord))

            for record in applied_records.scalars():
                if record.migration_id not in available_migrations:
                    logger.warning(
                        f"Applied migration not found in files: {record.migration_id}"
                    )
                    return False

                migration = available_migrations[record.migration_id]
                if migration.content_hash != record.content_hash:
                    logger.error(f"Migration content mismatch: {record.migration_id}")
                    return False

        logger.info("All applied migrations verified successfully")
        return True


# Convenience functions for CLI usage
async def init_migrations() -> None:
    """Initialize migration system and create initial migration files."""
    manager = MigrationManager()
    manager.create_initial_migrations()
    await manager.init_migration_table()
    logger.info("Migration system initialized")


async def run_migrations(dry_run: bool = False) -> None:
    """Run pending migrations."""
    manager = MigrationManager()
    await manager.run_migrations(dry_run=dry_run)


async def verify_migrations() -> bool:
    """Verify migration integrity."""
    manager = MigrationManager()
    return await manager.verify_migrations()


# CLI entry point
async def main() -> None:
    """CLI entry point for migration management."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m src.github_analyzer.database.migrations <command>")
        print("Commands: init, migrate, verify, dry-run")
        return

    command = sys.argv[1]

    if command == "init":
        await init_migrations()
    elif command == "migrate":
        await run_migrations()
    elif command == "verify":
        success = await verify_migrations()
        sys.exit(0 if success else 1)
    elif command == "dry-run":
        await run_migrations(dry_run=True)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
