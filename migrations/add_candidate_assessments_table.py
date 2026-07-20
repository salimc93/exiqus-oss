#!/usr/bin/env python3
"""
Add candidate_assessments and candidate_contexts tables.
Migration created: 2025-10-19 (updated 2025-10-24)
Supports both SQLite (dev) and PostgreSQL (production)

This migration adds:
1. candidate_assessments table - Track unique GitHub usernames analyzed per month
2. candidate_contexts table - Lock role/context per (user, candidate) pair

Core principles:
- Analyzing the same GitHub username counts as 1 candidate assessment per month
- Each user can evaluate the same candidate with different role/context settings
- candidate_contexts uses COMPOSITE PRIMARY KEY (locked_by_user_id, username)
"""

import os


def up_sqlite(conn):
    """Create candidate_assessments and candidate_contexts tables for SQLite."""
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS candidate_assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id VARCHAR(50) NOT NULL,
            github_username VARCHAR(39) NOT NULL,
            billing_period VARCHAR(7) NOT NULL,
            portfolio_analysis_count INTEGER NOT NULL DEFAULT 0,
            pr_analysis_count INTEGER NOT NULL DEFAULT 0,
            first_analyzed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_analyzed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            UNIQUE (user_id, github_username, billing_period)
        )
    """
    )

    # Create indexes
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_candidate_user_id ON candidate_assessments(user_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_candidate_github_username ON candidate_assessments(github_username)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_candidate_billing_period ON candidate_assessments(billing_period)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_candidate_created_at ON candidate_assessments(created_at)"
    )

    # Create candidate_contexts table with CORRECT composite primary key
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS candidate_contexts (
            locked_by_user_id VARCHAR(50) NOT NULL,
            username VARCHAR(39) NOT NULL,
            role VARCHAR(20) NOT NULL,
            organization_context VARCHAR(20) NOT NULL,
            locked_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            PRIMARY KEY (locked_by_user_id, username),
            FOREIGN KEY(locked_by_user_id) REFERENCES users (user_id)
        )
    """
    )

    # Create indexes for candidate_contexts
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_candidate_contexts_username ON candidate_contexts(username)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_candidate_contexts_user_id ON candidate_contexts(locked_by_user_id)"
    )

    conn.commit()
    print("✅ Created candidate_assessments and candidate_contexts tables (SQLite)")


def up_postgresql(conn):
    """Create candidate_assessments and candidate_contexts tables for PostgreSQL."""
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS candidate_assessments (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(50) NOT NULL REFERENCES users(user_id),
            github_username VARCHAR(39) NOT NULL,
            billing_period VARCHAR(7) NOT NULL,
            portfolio_analysis_count INTEGER NOT NULL DEFAULT 0,
            pr_analysis_count INTEGER NOT NULL DEFAULT 0,
            first_analyzed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            last_analyzed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            UNIQUE (user_id, github_username, billing_period)
        )
    """
    )

    # Create indexes for candidate_assessments
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_candidate_user_id ON candidate_assessments(user_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_candidate_github_username ON candidate_assessments(github_username)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_candidate_billing_period ON candidate_assessments(billing_period)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_candidate_created_at ON candidate_assessments(created_at)"
    )

    # Create candidate_contexts table with CORRECT composite primary key
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS candidate_contexts (
            locked_by_user_id VARCHAR(50) NOT NULL REFERENCES users(user_id),
            username VARCHAR(39) NOT NULL,
            role VARCHAR(20) NOT NULL,
            organization_context VARCHAR(20) NOT NULL,
            locked_at TIMESTAMP WITH TIME ZONE NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
            PRIMARY KEY (locked_by_user_id, username)
        )
    """
    )

    # Create indexes for candidate_contexts
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_candidate_contexts_username ON candidate_contexts(username)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_candidate_contexts_user_id ON candidate_contexts(locked_by_user_id)"
    )

    conn.commit()
    print("✅ Created candidate_assessments and candidate_contexts tables (PostgreSQL)")


def down_sqlite(conn):
    """Drop candidate_assessments and candidate_contexts tables for SQLite."""
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS candidate_contexts")
    cursor.execute("DROP TABLE IF EXISTS candidate_assessments")
    conn.commit()
    print("✅ Dropped candidate_assessments and candidate_contexts tables (SQLite)")


def down_postgresql(conn):
    """Drop candidate_assessments and candidate_contexts tables for PostgreSQL."""
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS candidate_contexts CASCADE")
    cursor.execute("DROP TABLE IF EXISTS candidate_assessments CASCADE")
    conn.commit()
    print("✅ Dropped candidate_assessments and candidate_contexts tables (PostgreSQL)")


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
        import psycopg2

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
