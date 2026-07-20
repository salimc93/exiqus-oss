"""
Simple tests for migration system functionality.

This module provides basic tests for the migration system without complex fixtures.
"""

import shutil
import tempfile
from pathlib import Path

from github_analyzer.database.migrations import Migration, MigrationManager


def test_migration_creation():
    """Test creating a Migration object."""
    migration = Migration(
        migration_id="001_test",
        description="Test migration",
        up_sql="CREATE TABLE test (id INTEGER);",
    )

    assert migration.migration_id == "001_test"
    assert migration.description == "Test migration"
    assert migration.up_sql == "CREATE TABLE test (id INTEGER);"
    assert migration.down_sql is None

    # Test content hash
    hash1 = migration.content_hash
    assert isinstance(hash1, str)
    assert len(hash1) == 64  # SHA256 hash

    # Same content should produce same hash
    migration2 = Migration(
        migration_id="001_test",
        description="Test migration",
        up_sql="CREATE TABLE test (id INTEGER);",
    )
    assert migration2.content_hash == hash1


def test_migration_manager_init():
    """Test MigrationManager initialization."""
    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp())

    try:
        manager = MigrationManager(temp_dir / "migrations")
        assert manager.migrations_dir == temp_dir / "migrations"
        assert manager.migrations_dir.exists()

    finally:
        shutil.rmtree(temp_dir)


def test_create_initial_migrations():
    """Test creating initial migration files."""
    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp())

    try:
        manager = MigrationManager(temp_dir / "migrations")

        # Create initial migrations
        manager.create_initial_migrations()

        # Check that migration files were created
        expected_files = [
            "001_create_users_table.sql",
            "002_create_api_keys_table.sql",
            "003_create_usage_records_table.sql",
            "004_create_token_blacklist_table.sql",
        ]

        for filename in expected_files:
            file_path = manager.migrations_dir / filename
            assert file_path.exists(), f"Migration file {filename} should exist"

            # Check file has content
            content = file_path.read_text()
            assert len(content) > 0, f"Migration file {filename} should not be empty"
            assert "CREATE TABLE" in content, (
                f"Migration file {filename} should contain CREATE TABLE"
            )

    finally:
        shutil.rmtree(temp_dir)


def test_load_migrations_from_directory():
    """Test loading migration files from directory."""
    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp())

    try:
        migrations_dir = temp_dir / "migrations"
        migrations_dir.mkdir()

        # Create test migration files
        migration1_content = """-- Create test table 1
CREATE TABLE test1 (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100)
);"""

        migration2_content = """-- Create test table 2
CREATE TABLE test2 (
    id INTEGER PRIMARY KEY,
    description TEXT
);"""

        (migrations_dir / "001_create_test1.sql").write_text(migration1_content)
        (migrations_dir / "002_create_test2.sql").write_text(migration2_content)

        # Create manager and load migrations
        manager = MigrationManager(migrations_dir)
        migrations = manager.load_migrations_from_directory()

        # Verify migrations were loaded correctly
        assert len(migrations) == 2

        # Check first migration
        assert migrations[0].migration_id == "001_create_test1"
        assert migrations[0].description == "Create test table 1"
        assert "CREATE TABLE test1" in migrations[0].up_sql

        # Check second migration
        assert migrations[1].migration_id == "002_create_test2"
        assert migrations[1].description == "Create test table 2"
        assert "CREATE TABLE test2" in migrations[1].up_sql

    finally:
        shutil.rmtree(temp_dir)


def test_migration_file_parsing():
    """Test parsing migration files with different formats."""
    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp())

    try:
        migrations_dir = temp_dir / "migrations"
        migrations_dir.mkdir()

        # Test migration with comment description
        with_comment = """-- This is a test migration
CREATE TABLE with_comment (id INTEGER);"""

        # Test migration without comment
        without_comment = """CREATE TABLE without_comment (id INTEGER);"""

        # Test empty migration file
        empty_migration = ""

        (migrations_dir / "001_with_comment.sql").write_text(with_comment)
        (migrations_dir / "002_without_comment.sql").write_text(without_comment)
        (migrations_dir / "003_empty.sql").write_text(empty_migration)

        manager = MigrationManager(migrations_dir)
        migrations = manager.load_migrations_from_directory()

        # Should only load non-empty migrations
        assert len(migrations) == 2

        # Check migration with comment
        migration_with_comment = next(
            m for m in migrations if m.migration_id == "001_with_comment"
        )
        assert migration_with_comment.description == "This is a test migration"
        assert "CREATE TABLE with_comment" in migration_with_comment.up_sql

        # Check migration without comment
        migration_without_comment = next(
            m for m in migrations if m.migration_id == "002_without_comment"
        )
        assert migration_without_comment.description == "No description"
        assert "CREATE TABLE without_comment" in migration_without_comment.up_sql

    finally:
        shutil.rmtree(temp_dir)
