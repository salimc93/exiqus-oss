"""
Tests for database migration system.

This module tests the migration management functionality including
migration application, verification, and rollback capabilities.
"""

import shutil
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from github_analyzer.database.migrations import (
    Migration,
    MigrationManager,
    MigrationRecord,
)


@pytest.fixture
def test_migration_manager(test_pg_url, test_pg_sync_engine):
    """Create test migration manager against the shared test Postgres."""

    class TestMigrationManager:
        def __init__(self):
            self.test_engine = None
            self.TestSessionLocal = None
            self.manager = None
            self.temp_dir = None
            self.original_engine = None
            self.original_session_local = None

        async def __aenter__(self):
            # Fresh async engine on the shared test Postgres
            async_url = test_pg_url.replace("postgresql://", "postgresql+asyncpg://")
            self.test_engine = create_async_engine(
                async_url, echo=False, poolclass=NullPool
            )

            # Create session factory
            self.TestSessionLocal = async_sessionmaker(
                self.test_engine, class_=AsyncSession, expire_on_commit=False
            )

            # Create temporary migrations directory
            self.temp_dir = Path(tempfile.mkdtemp())
            migrations_dir = self.temp_dir / "migrations"
            migrations_dir.mkdir()

            # Create test migration manager
            self.manager = MigrationManager(migrations_dir)

            # Patch manager to use test database
            original_module = __import__(
                "github_analyzer.database.migrations", fromlist=[""]
            )
            self.original_engine = original_module.engine
            self.original_session_local = original_module.AsyncSessionLocal

            # Override with test database
            original_module.engine = self.test_engine
            original_module.AsyncSessionLocal = self.TestSessionLocal

            # Add test session access for tests
            self.manager._test_engine = self.test_engine
            self.manager._test_session_local = self.TestSessionLocal

            return self.manager

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            # Cleanup: drop tables created by migration tests, reset history
            async with self.test_engine.begin() as conn:
                for table in (
                    "test_apply",
                    "test_users",
                    "test_posts",
                    "verify_test",
                    "verify_test_modified",
                    "dry_run_test",
                    "test1",
                    "test2",
                ):
                    await conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
                await conn.execute(text("TRUNCATE migration_history"))

            original_module = __import__(
                "github_analyzer.database.migrations", fromlist=[""]
            )
            original_module.engine = self.original_engine
            original_module.AsyncSessionLocal = self.original_session_local
            await self.test_engine.dispose()
            shutil.rmtree(self.temp_dir)

    return TestMigrationManager()


@pytest.mark.asyncio
async def test_migration_record_model(db_session):
    """Test MigrationRecord model creation and properties."""
    # Create migration record
    migration_record = MigrationRecord(
        migration_id="test_migration_001",
        description="Test migration for users table",
        content_hash="abc123def456",
    )

    db_session.add(migration_record)
    await db_session.commit()

    # Verify record was created
    assert migration_record.migration_id == "test_migration_001"
    assert migration_record.description == "Test migration for users table"
    assert migration_record.content_hash == "abc123def456"
    assert migration_record.applied_at is not None


@pytest.mark.asyncio
async def test_migration_class():
    """Test Migration class functionality."""
    migration = Migration(
        migration_id="001_test_migration",
        description="Test migration",
        up_sql="CREATE TABLE test (id INTEGER PRIMARY KEY);",
    )

    assert migration.migration_id == "001_test_migration"
    assert migration.description == "Test migration"
    assert migration.up_sql == "CREATE TABLE test (id INTEGER PRIMARY KEY);"
    assert migration.down_sql is None

    # Test content hash generation
    content_hash = migration.content_hash
    assert isinstance(content_hash, str)
    assert len(content_hash) == 64  # SHA256 hash length

    # Same migration should produce same hash
    migration2 = Migration(
        migration_id="001_test_migration",
        description="Test migration",
        up_sql="CREATE TABLE test (id INTEGER PRIMARY KEY);",
    )
    assert migration2.content_hash == content_hash


@pytest.mark.asyncio
async def test_init_migration_table(test_migration_manager):
    """Test migration table initialization."""
    async with test_migration_manager as manager:
        # Initialize migration table
        await manager.init_migration_table()

        # Verify table was created by checking it exists
        async with manager._test_session_local() as session:
            result = await session.execute(
                text(
                    "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename='migration_history'"
                )
            )
            tables = result.fetchall()
            assert len(tables) == 1
            assert tables[0][0] == "migration_history"


@pytest.mark.asyncio
async def test_create_and_load_migrations(test_migration_manager):
    """Test creating and loading migration files."""
    async with test_migration_manager as manager:
        # Create test migration files
        test_migration_1 = """-- Create test table 1
CREATE TABLE test1 (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100)
);"""

        test_migration_2 = """-- Create test table 2
CREATE TABLE test2 (
    id INTEGER PRIMARY KEY,
    description TEXT
);"""

        # Write test migration files
        (manager.migrations_dir / "001_create_test1.sql").write_text(test_migration_1)
        (manager.migrations_dir / "002_create_test2.sql").write_text(test_migration_2)

        # Load migrations
        migrations = manager.load_migrations_from_directory()

        assert len(migrations) == 2

        # Check first migration
        assert migrations[0].migration_id == "001_create_test1"
        assert migrations[0].description == "Create test table 1"
        assert "CREATE TABLE test1" in migrations[0].up_sql

        # Check second migration
        assert migrations[1].migration_id == "002_create_test2"
        assert migrations[1].description == "Create test table 2"
        assert "CREATE TABLE test2" in migrations[1].up_sql


@pytest.mark.asyncio
async def test_apply_migration(test_migration_manager):
    """Test applying a single migration."""
    async with test_migration_manager as manager:
        # Initialize migration table
        await manager.init_migration_table()

        # Create test migration
        migration = Migration(
            migration_id="001_test_table",
            description="Create test table",
            up_sql="CREATE TABLE test_apply (id INTEGER PRIMARY KEY, name VARCHAR(100));",
        )

        # Apply migration
        await manager.apply_migration(migration)

        # Verify table was created
        async with manager._test_session_local() as session:
            result = await session.execute(
                text(
                    "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename='test_apply'"
                )
            )
            tables = result.fetchall()
            assert len(tables) == 1

            # Verify migration was recorded
            applied_migrations = await manager.get_applied_migrations()
            assert "001_test_table" in applied_migrations


@pytest.mark.asyncio
async def test_run_migrations(test_migration_manager):
    """Test running multiple migrations."""
    async with test_migration_manager as manager:
        # Create test migration files
        migration_1 = """-- Create test_users table
CREATE TABLE test_users (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL
);"""

        migration_2 = """-- Create test_posts table
CREATE TABLE test_posts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES test_users(id),
    title VARCHAR(200)
);"""

        # Write migration files
        (manager.migrations_dir / "001_create_users.sql").write_text(migration_1)
        (manager.migrations_dir / "002_create_posts.sql").write_text(migration_2)

        # Run migrations
        await manager.run_migrations()

        # Verify both tables were created and both migrations were recorded
        async with manager._test_session_local() as session:
            result = await session.execute(
                text(
                    "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
                )
            )
            tables = [row[0] for row in result.fetchall()]

            # Should have migration_history + our 2 tables
            assert "migration_history" in tables
            assert "test_users" in tables
            assert "test_posts" in tables

            # Verify both migrations were recorded within the same session context
            applied_migrations = await manager.get_applied_migrations()
            assert len(applied_migrations) == 2
            assert "001_create_users" in applied_migrations
            assert "002_create_posts" in applied_migrations


@pytest.mark.asyncio
async def test_dry_run_migrations(test_migration_manager):
    """Test dry run mode doesn't apply migrations."""
    async with test_migration_manager as manager:
        # Create test migration file
        migration_content = """-- Create test table
CREATE TABLE dry_run_test (id INTEGER PRIMARY KEY);"""

        (manager.migrations_dir / "001_dry_run_test.sql").write_text(migration_content)

        # Run migrations in dry run mode
        await manager.run_migrations(dry_run=True)

        # Verify table was NOT created
        async with manager._test_session_local() as session:
            result = await session.execute(
                text(
                    "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename='dry_run_test'"
                )
            )
            tables = result.fetchall()
            assert len(tables) == 0

            # Verify migration was NOT recorded
            applied_migrations = await manager.get_applied_migrations()
            assert "001_dry_run_test" not in applied_migrations


@pytest.mark.asyncio
async def test_verify_migrations(test_migration_manager):
    """Test migration verification."""
    async with test_migration_manager as manager:
        # Create and apply a migration
        migration_content = """-- Create verification test table
CREATE TABLE verify_test (id INTEGER PRIMARY KEY);"""

        migration_file = manager.migrations_dir / "001_verify_test.sql"
        migration_file.write_text(migration_content)

        # Run migration
        await manager.run_migrations()

        # Verify migrations (should pass)
        is_valid = await manager.verify_migrations()
        assert is_valid is True

        # Modify migration file content (simulate corruption)
        modified_content = """-- Modified verification test table
CREATE TABLE verify_test_modified (id INTEGER PRIMARY KEY);"""

        migration_file.write_text(modified_content)

        # Verify migrations (should fail due to content mismatch)
        is_valid = await manager.verify_migrations()
        assert is_valid is False
