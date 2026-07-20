#!/usr/bin/env python3
"""
Add analysis_results table for storing analysis data and training.
Migration created: 2025-01-12
Supports both SQLite (dev) and PostgreSQL (production)
"""

import os

import psycopg2


def up_sqlite(conn):
    """Create analysis_results table for SQLite."""
    cursor = conn.cursor()

    # Create the analysis_results table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS analysis_results (
            -- Use TEXT for UUID in SQLite
            id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
            user_id VARCHAR(50) NOT NULL,
            repository_url TEXT NOT NULL,
            repository_name VARCHAR(255) NOT NULL,
            context VARCHAR(50) NOT NULL,

            -- Core results
            overall_score DECIMAL(3,2),
            confidence_score DECIMAL(3,2),
            recommendation VARCHAR(50),

            -- Use JSON for SQLite (no JSONB)
            full_analysis JSON NOT NULL,

            -- Metadata
            analysis_version VARCHAR(20) DEFAULT '1.0.0',
            processing_time_ms INTEGER,
            token_count INTEGER,
            api_cost DECIMAL(10,6),

            -- Privacy & soft delete
            allow_training BOOLEAN DEFAULT 1,
            deleted_at TIMESTAMP DEFAULT NULL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            -- Foreign key constraint
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    """
    )

    # Create indexes for performance
    cursor.execute(
        """
        CREATE INDEX idx_analysis_user_created
        ON analysis_results(user_id, created_at DESC)
        WHERE deleted_at IS NULL
    """
    )

    cursor.execute(
        """
        CREATE INDEX idx_analysis_repo
        ON analysis_results(repository_url)
    """
    )

    cursor.execute(
        """
        CREATE INDEX idx_analysis_deleted
        ON analysis_results(deleted_at)
        WHERE deleted_at IS NOT NULL
    """
    )

    # Create trigger to update updated_at (SQLite version)
    cursor.execute(
        """
        CREATE TRIGGER update_analysis_results_updated_at
        AFTER UPDATE ON analysis_results
        FOR EACH ROW
        WHEN NEW.updated_at = OLD.updated_at
        BEGIN
            UPDATE analysis_results
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = NEW.id;
        END
    """
    )

    conn.commit()
    print("✅ Created analysis_results table with indexes (SQLite)")


def up_postgresql(conn):
    """Create analysis_results table for PostgreSQL."""
    cursor = conn.cursor()

    # Enable UUID extension
    cursor.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

    # Create the analysis_results table with PostgreSQL features
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS analysis_results (
            -- Use proper UUID with DB generation
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id VARCHAR(50) NOT NULL,
            repository_url TEXT NOT NULL,
            repository_name VARCHAR(255) NOT NULL,
            context VARCHAR(50) NOT NULL,

            -- Core results
            overall_score DECIMAL(3,2),
            confidence_score DECIMAL(3,2),
            recommendation VARCHAR(50),

            -- Use JSONB for better performance in PostgreSQL
            full_analysis JSONB NOT NULL,

            -- Metadata
            analysis_version VARCHAR(20) DEFAULT '1.0.0',
            processing_time_ms INTEGER,
            token_count INTEGER,
            api_cost DECIMAL(10,6),

            -- Privacy & soft delete
            allow_training BOOLEAN DEFAULT TRUE,
            deleted_at TIMESTAMP DEFAULT NULL,

            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

            -- Foreign key constraint
            CONSTRAINT fk_user FOREIGN KEY (user_id)
                REFERENCES users(user_id) ON DELETE CASCADE
        )
    """
    )

    # Create composite index for efficient user pagination
    cursor.execute(
        """
        CREATE INDEX idx_analysis_user_created
        ON analysis_results(user_id, created_at DESC)
        WHERE deleted_at IS NULL
    """
    )

    # Additional indexes
    cursor.execute(
        """
        CREATE INDEX idx_analysis_repo
        ON analysis_results(repository_url)
    """
    )

    cursor.execute(
        """
        CREATE INDEX idx_analysis_deleted
        ON analysis_results(deleted_at)
        WHERE deleted_at IS NOT NULL
    """
    )

    # Create index on JSONB for efficient querying (PostgreSQL specific)
    cursor.execute(
        """
        CREATE INDEX idx_analysis_scores
        ON analysis_results((full_analysis->'overall_assessment'->>'score')::float)
        WHERE deleted_at IS NULL
    """
    )

    # Function to auto-update updated_at
    cursor.execute(
        """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql'
    """
    )

    # Create trigger
    cursor.execute(
        """
        CREATE TRIGGER update_analysis_results_updated_at
        BEFORE UPDATE ON analysis_results
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column()
    """
    )

    conn.commit()
    print("✅ Created analysis_results table with indexes (PostgreSQL)")


def down_sqlite(conn):
    """Drop analysis_results table for SQLite."""
    cursor = conn.cursor()

    # Drop trigger first
    cursor.execute("DROP TRIGGER IF EXISTS update_analysis_results_updated_at")

    # Drop indexes
    cursor.execute("DROP INDEX IF EXISTS idx_analysis_user_created")
    cursor.execute("DROP INDEX IF EXISTS idx_analysis_repo")
    cursor.execute("DROP INDEX IF EXISTS idx_analysis_deleted")

    # Drop table
    cursor.execute("DROP TABLE IF EXISTS analysis_results")

    conn.commit()
    print("✅ Dropped analysis_results table (SQLite)")


def down_postgresql(conn):
    """Drop analysis_results table for PostgreSQL."""
    cursor = conn.cursor()

    # Drop trigger and function
    cursor.execute(
        "DROP TRIGGER IF EXISTS update_analysis_results_updated_at ON analysis_results"
    )
    cursor.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")

    # Drop indexes (CASCADE will handle them, but explicit is clearer)
    cursor.execute("DROP INDEX IF EXISTS idx_analysis_user_created")
    cursor.execute("DROP INDEX IF EXISTS idx_analysis_repo")
    cursor.execute("DROP INDEX IF EXISTS idx_analysis_deleted")
    cursor.execute("DROP INDEX IF EXISTS idx_analysis_scores")

    # Drop table
    cursor.execute("DROP TABLE IF EXISTS analysis_results CASCADE")

    conn.commit()
    print("✅ Dropped analysis_results table (PostgreSQL)")


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
