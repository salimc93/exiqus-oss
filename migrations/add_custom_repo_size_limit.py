"""
Add custom_repo_size_limit_mb to users table.

This migration adds a new column to support custom repository size limits
for enterprise users.
"""

import sqlite3
from pathlib import Path


def upgrade():
    """Add custom_repo_size_limit_mb column to users table."""
    db_path = Path(__file__).parent.parent / "github_analyzer.db"

    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]

        if "custom_repo_size_limit_mb" not in columns:
            cursor.execute(
                """
                ALTER TABLE users
                ADD COLUMN custom_repo_size_limit_mb INTEGER
            """
            )
            print("✓ Added custom_repo_size_limit_mb column to users table")
        else:
            print("- Column custom_repo_size_limit_mb already exists")

        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"✗ Migration failed: {e}")
        raise
    finally:
        conn.close()


def downgrade():
    """Remove custom_repo_size_limit_mb column from users table."""
    db_path = Path(__file__).parent.parent / "github_analyzer.db"

    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)

    try:
        # SQLite doesn't support DROP COLUMN directly, need to recreate table
        # For simplicity, we'll just note this limitation
        print(
            "Note: SQLite does not support DROP COLUMN. Manual intervention required for downgrade."
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"✗ Downgrade failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    upgrade()
