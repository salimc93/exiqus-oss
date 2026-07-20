#!/usr/bin/env python3
"""
Add portfolio_analyses table for portfolio analysis feature.
Migration created: 2025-10-19
Supports both SQLite (dev) and PostgreSQL (production)

This migration adds the portfolio_analyses table to store complete
portfolio analysis results for GitHub usernames, including all
repositories analyzed and the generated insights.
"""

import os


def up_sqlite(conn):
    """Create portfolio_analyses table for SQLite."""
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS portfolio_analyses (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(50) NOT NULL,
            github_username VARCHAR(39) NOT NULL,
            context VARCHAR(50) NOT NULL,
            total_repos INTEGER NOT NULL,
            repos_analyzed INTEGER NOT NULL,
            repos_skipped INTEGER NOT NULL,
            full_analysis TEXT NOT NULL,
            s3_key VARCHAR(255) DEFAULT NULL,
            analysis_metadata TEXT NOT NULL,
            processing_time_seconds REAL NOT NULL,
            token_count INTEGER NOT NULL,
            api_cost REAL NOT NULL,
            api_calls_used INTEGER NOT NULL DEFAULT 1,
            from_cache BOOLEAN NOT NULL DEFAULT 0,
            cache_expires_at TIMESTAMP DEFAULT NULL,
            key_observations_count INTEGER NOT NULL,
            evidence_patterns_count INTEGER NOT NULL,
            interview_questions_count INTEGER NOT NULL,
            timeline_gaps_count INTEGER NOT NULL,
            analysis_version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
            data_quality VARCHAR(20) NOT NULL,
            allow_training BOOLEAN NOT NULL DEFAULT 1,
            deleted_at TIMESTAMP DEFAULT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    """
    )

    # Create indexes
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_portfolio_user_id ON portfolio_analyses(user_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_portfolio_github_username ON portfolio_analyses(github_username)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_portfolio_created_at ON portfolio_analyses(created_at)"
    )

    conn.commit()
    print("✅ Created portfolio_analyses table (SQLite)")


def up_postgresql(conn):
    """Create portfolio_analyses table for PostgreSQL."""
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS portfolio_analyses (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(50) NOT NULL REFERENCES users(user_id),
            github_username VARCHAR(39) NOT NULL,
            context VARCHAR(50) NOT NULL,
            total_repos INTEGER NOT NULL,
            repos_analyzed INTEGER NOT NULL,
            repos_skipped INTEGER NOT NULL,
            full_analysis TEXT NOT NULL,
            s3_key VARCHAR(255) DEFAULT NULL,
            analysis_metadata TEXT NOT NULL,
            processing_time_seconds DOUBLE PRECISION NOT NULL,
            token_count INTEGER NOT NULL,
            api_cost DOUBLE PRECISION NOT NULL,
            api_calls_used INTEGER NOT NULL DEFAULT 1,
            from_cache BOOLEAN NOT NULL DEFAULT FALSE,
            cache_expires_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
            key_observations_count INTEGER NOT NULL,
            evidence_patterns_count INTEGER NOT NULL,
            interview_questions_count INTEGER NOT NULL,
            timeline_gaps_count INTEGER NOT NULL,
            analysis_version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
            data_quality VARCHAR(20) NOT NULL,
            allow_training BOOLEAN NOT NULL DEFAULT TRUE,
            deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """
    )

    # Create indexes
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_portfolio_user_id ON portfolio_analyses(user_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_portfolio_github_username ON portfolio_analyses(github_username)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_portfolio_created_at ON portfolio_analyses(created_at)"
    )

    conn.commit()
    print("✅ Created portfolio_analyses table (PostgreSQL)")


def down_sqlite(conn):
    """Drop portfolio_analyses table for SQLite."""
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS portfolio_analyses")
    conn.commit()
    print("✅ Dropped portfolio_analyses table (SQLite)")


def down_postgresql(conn):
    """Drop portfolio_analyses table for PostgreSQL."""
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS portfolio_analyses CASCADE")
    conn.commit()
    print("✅ Dropped portfolio_analyses table (PostgreSQL)")


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
