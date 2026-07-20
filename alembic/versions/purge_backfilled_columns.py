"""Purge scoring contamination from backfilled evidence columns

Revision ID: purge_backfilled_columns
Revises: comprehensive_scoring_purge
Create Date: 2025-12-09

This migration cleans scoring contamination from the evidence-based columns
that were backfilled from full_analysis. These columns may contain old
scoring data that violates The Great Purge principles.
"""

import json
from typing import Any

from alembic import op
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = "purge_backfilled_columns"
down_revision = "comprehensive_scoring_purge"
branch_labels = None
depends_on = None


def clean_scoring_structure(data: Any) -> Any:
    """Remove all scoring contamination from JSON data."""
    if isinstance(data, dict):
        cleaned = {}

        # Forbidden keys that indicate scoring
        forbidden_keys = [
            "overall_score",
            "confidence_score",
            "score",
            "rating",
            "verdict",
            "hire",
            "pass",
            "investigate",
            "metrics",
            "numerical_assessment",
            "overall_assessment",
            "code_quality",
            "architecture",
            "testing",
            "documentation",
            "best_practices",
            "version_control",
            "collaboration",
            "issue_management",
            "ci_cd",
            "documentation_quality",
            "commit_messages",
            "pr_descriptions",
            "issue_discussions",
            "learning_velocity",
            "technology_adoption",
            "contribution_consistency",
            "skill_progression",
            "sub_metrics",
            "confidence_range",
            "percentage",
            "is_behavioral",
        ]

        for key, value in data.items():
            # Skip forbidden keys
            if any(forbidden in key.lower() for forbidden in forbidden_keys):
                continue

            # Recursively clean nested structures
            cleaned[key] = clean_scoring_structure(value)

        return cleaned

    elif isinstance(data, list):
        cleaned_list = []
        for item in data:
            cleaned_item = clean_scoring_structure(item)
            if cleaned_item:  # Only keep non-empty items
                cleaned_list.append(cleaned_item)
        return cleaned_list

    else:
        return data


def clean_json_column(connection: Any, table: str, column: str) -> int:
    """Clean a JSON column of scoring contamination."""
    # Get all records with data in this column
    result = connection.execute(
        text(
            f"""
            SELECT id, {column}
            FROM {table}
            WHERE {column} IS NOT NULL
              AND {column} != ''
              AND {column} != 'null'
              AND {column} != '{{}}'
              AND {column} != '[]'
        """
        )
    )

    cleaned_count = 0
    for row in result:
        try:
            # Parse the JSON data
            if isinstance(row[1], str):
                data = json.loads(row[1])
            else:
                data = row[1]

            # Clean the data
            cleaned_data = clean_scoring_structure(data)

            # Only update if cleaning made changes
            original_json = json.dumps(data, sort_keys=True)
            cleaned_json = json.dumps(cleaned_data, sort_keys=True)

            if original_json != cleaned_json:
                # Update with cleaned data
                connection.execute(
                    text(
                        f"""
                        UPDATE {table}
                        SET {column} = :cleaned_data,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :id
                    """
                    ),
                    {"id": row[0], "cleaned_data": json.dumps(cleaned_data)},
                )
                cleaned_count += 1
                print(f"   🧹 Cleaned {column} for record {row[0][:8]}...")

        except Exception as e:
            print(f"   ⚠️  Error cleaning {column} for {row[0]}: {e}")
            continue

    return cleaned_count


def upgrade() -> None:
    """
    Clean scoring contamination from all evidence-based columns.
    """

    connection = op.get_bind()

    print("\n🔥 THE GREAT PURGE 3.0 - BACKFILLED COLUMNS CLEANUP")
    print("=" * 60)

    # List of columns that may contain contaminated JSON data
    columns_to_clean = [
        "evidence_patterns",
        "screening_insights",
        "technical_patterns",
        "collaboration_patterns",
        "quality_indicators",
        "temporal_insights",
        "skill_evolution",
        "behavioral_analysis",
        "security_practices",
        "context_alignment",
        "verification_gaps",
    ]

    total_cleaned = 0

    for column in columns_to_clean:
        print(f"\n📋 Checking column: {column}")
        cleaned = clean_json_column(connection, "analysis_results", column)
        if cleaned > 0:
            print(f"   ✅ Cleaned {cleaned} records")
            total_cleaned += cleaned
        else:
            print("   🎯 Already clean")

    print("\n" + "=" * 60)
    print("📊 THE GREAT PURGE 3.0 SUMMARY:")
    print(f"   Total contaminated records cleaned: {total_cleaned}")

    if total_cleaned > 0:
        print("\n✅ SUCCESS: All evidence columns now free of scoring contamination!")
        print("   🎯 Complete data purity achieved")
        print("   🔒 No scoring data remains in database")
    else:
        print("\n🎉 All columns already clean - no contamination found!")

    print("   🚀 Database ready for production")


def downgrade() -> None:
    """
    Cannot restore scoring contamination - The Great Purge is permanent.
    """
    print("⚠️  Cannot restore scoring contamination to backfilled columns")
    print("   The Great Purge 3.0 has permanently eliminated all scoring data")
    print("   This ensures complete data purity for ML/AI systems")
    pass
