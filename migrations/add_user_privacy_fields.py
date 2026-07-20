#!/usr/bin/env python3
"""
Add privacy preference fields to users table.
Migration created: 2025-07-30
Supports both SQLite (dev) and PostgreSQL (production)

This migration adds fields to support user privacy preferences
and consent management.
"""

import os

import psycopg2


def up_sqlite(conn):
    """Add privacy fields to users table for SQLite."""
    cursor = conn.cursor()

    # Add new columns one by one (SQLite doesn't support adding multiple columns at once)
    cursor.execute(
        """
        ALTER TABLE users
        ADD COLUMN privacy_preferences TEXT DEFAULT NULL
    """
    )

    cursor.execute(
        """
        ALTER TABLE users
        ADD COLUMN consent_version_accepted VARCHAR(20) DEFAULT NULL
    """
    )

    cursor.execute(
        """
        ALTER TABLE users
        ADD COLUMN consent_notice_dismissed_at TIMESTAMP DEFAULT NULL
    """
    )

    conn.commit()
    print("✅ Added privacy fields to users table (SQLite)")


def up_postgresql(conn):
    """Add privacy fields to users table for PostgreSQL."""
    cursor = conn.cursor()

    # PostgreSQL supports adding multiple columns in one statement
    cursor.execute(
        """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS privacy_preferences TEXT DEFAULT NULL,
        ADD COLUMN IF NOT EXISTS consent_version_accepted VARCHAR(20) DEFAULT NULL,
        ADD COLUMN IF NOT EXISTS consent_notice_dismissed_at TIMESTAMP WITH TIME ZONE DEFAULT NULL
    """
    )

    conn.commit()
    print("✅ Added privacy fields to users table (PostgreSQL)")


def down_sqlite(conn):
    """Remove privacy fields from users table for SQLite."""
    # Note: SQLite doesn't support dropping columns easily
    # In production, you'd need to recreate the table without these columns
    print(
        "⚠️  SQLite doesn't support dropping columns. Manual intervention required to remove columns."
    )
    conn.commit()


def down_postgresql(conn):
    """Remove privacy fields from users table for PostgreSQL."""
    cursor = conn.cursor()

    # Drop columns
    cursor.execute(
        """
        ALTER TABLE users
        DROP COLUMN IF EXISTS privacy_preferences,
        DROP COLUMN IF EXISTS consent_version_accepted,
        DROP COLUMN IF EXISTS consent_notice_dismissed_at
    """
    )

    conn.commit()
    print("✅ Removed privacy fields from users table (PostgreSQL)")


def get_db_type(db_url):
    """Determine database type from URL."""
    if "postgresql" in db_url or "postgres" in db_url:
        return "postgresql"
    elif "sqlite" in db_url:
        return "sqlite"
    else:
        raise ValueError(f"Unsupported database type in URL: {db_url}")


if __name__ == "__main__":
    import sqlite3
    import sys

    # Get database URL
    db_url = os.environ.get("DATABASE_URL", "sqlite:///./github_analyzer.db")
    db_type = get_db_type(db_url)

    if db_type == "sqlite":
        # SQLite connection
        db_path = db_url.replace("sqlite:///", "")
        conn = sqlite3.connect(db_path)

        if len(sys.argv) > 1 and sys.argv[1] == "down":
            down_sqlite(conn)
        else:
            up_sqlite(conn)

    elif db_type == "postgresql":
        # PostgreSQL connection
        # Handle Railway's postgres:// vs postgresql:// URLs
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)

        conn = psycopg2.connect(db_url)
        conn.autocommit = False

        if len(sys.argv) > 1 and sys.argv[1] == "down":
            down_postgresql(conn)
        else:
            up_postgresql(conn)

    conn.close()
