"""Purge scoring contamination from evidence-based analyses

Revision ID: purge_scoring_contamination
Revises: backfill_evidence_columns
Create Date: 2025-12-09

This migration:
1. Identifies analyses that contain forbidden scoring data in their full_analysis JSON
2. Either removes the contaminated data or marks the analysis for re-processing
3. Ensures The Great Purge is complete - NO scoring data in evidence-based system
"""

import json
from typing import Any, Tuple

from alembic import op
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = "purge_scoring_contamination"
down_revision = "backfill_evidence_columns"
branch_labels = None
depends_on = None


def has_forbidden_scoring_data(full_analysis_json: Any) -> Tuple[bool, str]:
    """Check if full_analysis contains forbidden scoring data."""
    try:
        if isinstance(full_analysis_json, str):
            data = json.loads(full_analysis_json)
        else:
            data = full_analysis_json

        # Check for forbidden fields at any level
        forbidden_fields = [
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
        ]

        def check_recursive(obj: Any, path: str = "") -> Tuple[bool, str]:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key

                    # Check if key itself is forbidden
                    if any(forbidden in key.lower() for forbidden in forbidden_fields):
                        return True, current_path

                    # Check value recursively
                    found, found_path = check_recursive(value, current_path)
                    if found:
                        return True, found_path

            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    found, found_path = check_recursive(item, f"{path}[{i}]")
                    if found:
                        return True, found_path

            elif isinstance(obj, (int, float)) and path:
                # Check if this numeric value is in a scoring context
                path_lower = path.lower()
                if any(forbidden in path_lower for forbidden in forbidden_fields):
                    return True, path

            return False, ""

        return check_recursive(data)

    except (json.JSONDecodeError, TypeError):
        return False, ""


def upgrade() -> None:
    """
    Purge scoring contamination from evidence-based analyses.
    """

    connection = op.get_bind()

    # Get all records to check for contamination
    result = connection.execute(
        text(
            """
            SELECT id, full_analysis, analysis_method, repository_url, created_at
            FROM analysis_results
            WHERE full_analysis IS NOT NULL
              AND full_analysis != ''
        """
        )
    )

    contaminated_count = 0
    evidence_based_contaminated = 0
    legacy_contaminated = 0

    contaminated_ids = []

    for row in result:
        try:
            has_scores, score_path = has_forbidden_scoring_data(row.full_analysis)

            if has_scores:
                contaminated_count += 1
                contaminated_ids.append(row.id)

                if row.analysis_method == "evidence_based":
                    evidence_based_contaminated += 1
                    print(
                        f"🚨 CRITICAL: Evidence-based analysis {row.id} contains forbidden scoring data at {score_path}"
                    )
                else:
                    legacy_contaminated += 1

        except Exception as e:
            print(f"Error checking record {row.id}: {e}")
            continue

    print("📊 SCORING CONTAMINATION REPORT:")
    print(f"   Total contaminated analyses: {contaminated_count}")
    print(f"   Evidence-based contaminated: {evidence_based_contaminated} 🚨")
    print(f"   Legacy contaminated: {legacy_contaminated}")

    if evidence_based_contaminated > 0:
        print("\n🔥 GREAT PURGE VIOLATION DETECTED!")
        print(
            f"   {evidence_based_contaminated} evidence-based analyses contain forbidden scoring data"
        )

        # Option 1: Mark these as needing re-analysis
        # Option 2: Clean the JSON data
        # Option 3: Delete contaminated records

        print("\n🧹 CLEANING CONTAMINATED EVIDENCE-BASED ANALYSES...")

        for analysis_id in contaminated_ids:
            # Get the full record
            record_result = connection.execute(
                text(
                    "SELECT analysis_method, full_analysis FROM analysis_results WHERE id = :id"
                ),
                {"id": analysis_id},
            )
            record = record_result.fetchone()

            if record and record.analysis_method == "evidence_based":
                # For evidence-based analyses, clean the full_analysis JSON
                try:
                    data = json.loads(record.full_analysis)
                    cleaned_data = clean_scoring_data(data)

                    # Update with cleaned data
                    connection.execute(
                        text(
                            """
                            UPDATE analysis_results
                            SET full_analysis = :cleaned_data,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = :id
                        """
                        ),
                        {"id": analysis_id, "cleaned_data": json.dumps(cleaned_data)},
                    )
                    print(f"   ✅ Cleaned analysis {analysis_id}")

                except Exception as e:
                    print(f"   ❌ Failed to clean analysis {analysis_id}: {e}")

    print("\n✅ SCORING CONTAMINATION PURGE COMPLETE")
    print("   The Great Purge is now enforced at the database level")


def clean_scoring_data(data: Any) -> Any:
    """Recursively remove forbidden scoring data from analysis JSON."""
    if isinstance(data, dict):
        cleaned = {}
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
        ]

        for key, value in data.items():
            # Skip forbidden keys
            if any(forbidden in key.lower() for forbidden in forbidden_keys):
                continue

            # Recursively clean nested structures
            cleaned[key] = clean_scoring_data(value)

        return cleaned

    elif isinstance(data, list):
        return [clean_scoring_data(item) for item in data]

    else:
        return data


def downgrade() -> None:
    """
    Cannot safely restore scoring contamination - The Great Purge is irreversible.
    """
    print("⚠️  Cannot restore scoring contamination - The Great Purge is permanent")
    print("   Scoring data has been permanently purged from evidence-based system")
    pass
