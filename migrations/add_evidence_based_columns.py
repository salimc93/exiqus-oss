#!/usr/bin/env python3
"""
Add evidence-based analysis columns to analysis_results table.
Migration created: 2025-07-30
Supports both SQLite (dev) and PostgreSQL (production)

This migration adds columns to support the new evidence-driven analysis approach,
including consent management and tier-based privacy defaults.
"""

import os

import psycopg2


def up_sqlite(conn):
    """Add evidence-based columns to analysis_results table for SQLite."""
    cursor = conn.cursor()

    # Add new columns one by one (SQLite doesn't support adding multiple columns at once)
    cursor.execute(
        """
        ALTER TABLE analysis_results
        ADD COLUMN evidence_patterns JSON
    """
    )

    cursor.execute(
        """
        ALTER TABLE analysis_results
        ADD COLUMN screening_insights JSON
    """
    )

    cursor.execute(
        """
        ALTER TABLE analysis_results
        ADD COLUMN confidence_explanation TEXT
    """
    )

    cursor.execute(
        """
        ALTER TABLE analysis_results
        ADD COLUMN technical_patterns JSON
    """
    )

    cursor.execute(
        """
        ALTER TABLE analysis_results
        ADD COLUMN collaboration_patterns JSON
    """
    )

    cursor.execute(
        """
        ALTER TABLE analysis_results
        ADD COLUMN quality_indicators JSON
    """
    )

    cursor.execute(
        """
        ALTER TABLE analysis_results
        ADD COLUMN temporal_insights JSON
    """
    )

    cursor.execute(
        """
        ALTER TABLE analysis_results
        ADD COLUMN skill_evolution JSON
    """
    )

    cursor.execute(
        """
        ALTER TABLE analysis_results
        ADD COLUMN behavioral_analysis JSON
    """
    )

    cursor.execute(
        """
        ALTER TABLE analysis_results
        ADD COLUMN security_practices JSON
    """
    )

    cursor.execute(
        """
        ALTER TABLE analysis_results
        ADD COLUMN context_alignment JSON
    """
    )

    cursor.execute(
        """
        ALTER TABLE analysis_results
        ADD COLUMN verification_gaps JSON
    """
    )

    cursor.execute(
        """
        ALTER TABLE analysis_results
        ADD COLUMN analysis_method VARCHAR(20) DEFAULT 'legacy'
    """
    )

    cursor.execute(
        """
        ALTER TABLE analysis_results
        ADD COLUMN evidence_version VARCHAR(20) DEFAULT '1.0.0'
    """
    )

    # Privacy and consent columns
    cursor.execute(
        """
        ALTER TABLE analysis_results
        ADD COLUMN data_consent JSON
    """
    )

    cursor.execute(
        """
        ALTER TABLE analysis_results
        ADD COLUMN data_anonymized_at TIMESTAMP DEFAULT NULL
    """
    )

    cursor.execute(
        """
        ALTER TABLE analysis_results
        ADD COLUMN consent_updated_at TIMESTAMP DEFAULT NULL
    """
    )

    cursor.execute(
        """
        ALTER TABLE analysis_results
        ADD COLUMN training_eligible BOOLEAN DEFAULT 0
    """
    )

    # Add batch tracking column if not exists
    cursor.execute(
        """
        ALTER TABLE analysis_results
        ADD COLUMN batch_id VARCHAR(36) DEFAULT NULL
    """
    )

    # Create index for training data export
    cursor.execute(
        """
        CREATE INDEX idx_analysis_training_eligible
        ON analysis_results(training_eligible, created_at DESC)
        WHERE deleted_at IS NULL AND training_eligible = 1
    """
    )

    # Create index for batch queries
    cursor.execute(
        """
        CREATE INDEX idx_analysis_batch
        ON analysis_results(batch_id)
        WHERE batch_id IS NOT NULL
    """
    )

    conn.commit()
    print("✅ Added evidence-based columns to analysis_results table (SQLite)")


def up_postgresql(conn):
    """Add evidence-based columns to analysis_results table for PostgreSQL."""
    cursor = conn.cursor()

    # PostgreSQL supports adding multiple columns in one statement
    cursor.execute(
        """
        ALTER TABLE analysis_results
        ADD COLUMN IF NOT EXISTS evidence_patterns JSONB,
        ADD COLUMN IF NOT EXISTS screening_insights JSONB,
        ADD COLUMN IF NOT EXISTS confidence_explanation TEXT,
        ADD COLUMN IF NOT EXISTS technical_patterns JSONB,
        ADD COLUMN IF NOT EXISTS collaboration_patterns JSONB,
        ADD COLUMN IF NOT EXISTS quality_indicators JSONB,
        ADD COLUMN IF NOT EXISTS temporal_insights JSONB,
        ADD COLUMN IF NOT EXISTS skill_evolution JSONB,
        ADD COLUMN IF NOT EXISTS behavioral_analysis JSONB,
        ADD COLUMN IF NOT EXISTS security_practices JSONB,
        ADD COLUMN IF NOT EXISTS context_alignment JSONB,
        ADD COLUMN IF NOT EXISTS verification_gaps JSONB,
        ADD COLUMN IF NOT EXISTS analysis_method VARCHAR(20) DEFAULT 'legacy',
        ADD COLUMN IF NOT EXISTS evidence_version VARCHAR(20) DEFAULT '1.0.0',
        ADD COLUMN IF NOT EXISTS data_consent JSONB,
        ADD COLUMN IF NOT EXISTS data_anonymized_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
        ADD COLUMN IF NOT EXISTS consent_updated_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
        ADD COLUMN IF NOT EXISTS training_eligible BOOLEAN DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS batch_id VARCHAR(36) DEFAULT NULL
    """
    )

    # Create indexes for efficient querying of evidence data
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_analysis_training_eligible
        ON analysis_results(training_eligible, created_at DESC)
        WHERE deleted_at IS NULL AND training_eligible = TRUE
    """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_analysis_batch
        ON analysis_results(batch_id)
        WHERE batch_id IS NOT NULL
    """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_analysis_method
        ON analysis_results(analysis_method)
    """
    )

    # JSONB indexes for efficient pattern queries
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_evidence_patterns_gin
        ON analysis_results USING GIN (evidence_patterns)
        WHERE evidence_patterns IS NOT NULL
    """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_screening_insights_gin
        ON analysis_results USING GIN (screening_insights)
        WHERE screening_insights IS NOT NULL
    """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_data_consent_gin
        ON analysis_results USING GIN (data_consent)
        WHERE data_consent IS NOT NULL
    """
    )

    # Index for consent queries
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_consent_training
        ON analysis_results((data_consent->>'training_usage')::boolean)
        WHERE data_consent IS NOT NULL
    """
    )

    conn.commit()
    print("✅ Added evidence-based columns to analysis_results table (PostgreSQL)")


def down_sqlite(conn):
    """Remove evidence-based columns from analysis_results table for SQLite."""
    cursor = conn.cursor()

    # Drop indexes first
    cursor.execute("DROP INDEX IF EXISTS idx_analysis_training_eligible")
    cursor.execute("DROP INDEX IF EXISTS idx_analysis_batch")

    # Note: SQLite doesn't support dropping columns easily
    # In production, you'd need to recreate the table without these columns
    print(
        "⚠️  SQLite doesn't support dropping columns. Manual intervention required to remove columns."
    )
    conn.commit()


def down_postgresql(conn):
    """Remove evidence-based columns from analysis_results table for PostgreSQL."""
    cursor = conn.cursor()

    # Drop indexes first
    cursor.execute("DROP INDEX IF EXISTS idx_analysis_training_eligible")
    cursor.execute("DROP INDEX IF EXISTS idx_analysis_batch")
    cursor.execute("DROP INDEX IF EXISTS idx_analysis_method")
    cursor.execute("DROP INDEX IF EXISTS idx_evidence_patterns_gin")
    cursor.execute("DROP INDEX IF EXISTS idx_screening_insights_gin")
    cursor.execute("DROP INDEX IF EXISTS idx_data_consent_gin")
    cursor.execute("DROP INDEX IF EXISTS idx_consent_training")

    # Drop columns
    cursor.execute(
        """
        ALTER TABLE analysis_results
        DROP COLUMN IF EXISTS evidence_patterns,
        DROP COLUMN IF EXISTS screening_insights,
        DROP COLUMN IF EXISTS confidence_explanation,
        DROP COLUMN IF EXISTS technical_patterns,
        DROP COLUMN IF EXISTS collaboration_patterns,
        DROP COLUMN IF EXISTS quality_indicators,
        DROP COLUMN IF EXISTS temporal_insights,
        DROP COLUMN IF EXISTS skill_evolution,
        DROP COLUMN IF EXISTS behavioral_analysis,
        DROP COLUMN IF EXISTS security_practices,
        DROP COLUMN IF EXISTS context_alignment,
        DROP COLUMN IF EXISTS verification_gaps,
        DROP COLUMN IF EXISTS analysis_method,
        DROP COLUMN IF EXISTS evidence_version,
        DROP COLUMN IF EXISTS data_consent,
        DROP COLUMN IF EXISTS data_anonymized_at,
        DROP COLUMN IF EXISTS consent_updated_at,
        DROP COLUMN IF EXISTS training_eligible,
        DROP COLUMN IF EXISTS batch_id
    """
    )

    conn.commit()
    print("✅ Removed evidence-based columns from analysis_results table (PostgreSQL)")


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
