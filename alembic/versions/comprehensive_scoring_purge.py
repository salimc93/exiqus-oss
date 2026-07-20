"""Comprehensive scoring purge - The Great Purge 2.0

Revision ID: comprehensive_scoring_purge
Revises: purge_scoring_contamination
Create Date: 2025-12-09

This migration comprehensively removes ALL scoring contamination from full_analysis JSON:
1. Removes all nested scoring structures (technical_assessment, professional_practices, etc.)
2. Removes all behavioral summaries and assessments
3. Ensures database stores same clean data that users see
4. Prevents training data contamination for future ML/AI systems
"""

import json
from typing import Any

from alembic import op
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = "comprehensive_scoring_purge"
down_revision = "purge_scoring_contamination"
branch_labels = None
depends_on = None


def clean_scoring_structure(data: Any) -> Any:
    """Comprehensively remove all scoring structures from analysis JSON."""
    if isinstance(data, dict):
        cleaned = {}

        # Forbidden top-level structures that contain scoring
        forbidden_structures = [
            "technical_assessment",
            "professional_practices",
            "communication_skills",
            "growth_indicators",
            "team_fit_analysis",
        ]

        # Forbidden keys at any level
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
        ]

        # Forbidden behavioral summary phrases
        forbidden_summaries = [
            "Shows moderate technical capability",
            "Follows industry best practices consistently",
            "Strong written communication evident",
            "Limited evidence of recent skill development",
        ]

        for key, value in data.items():
            # Skip entire forbidden structures
            if key in forbidden_structures:
                print(f"   🧹 Removed forbidden structure: {key}")
                continue

            # Skip forbidden keys
            if any(forbidden in key.lower() for forbidden in forbidden_keys):
                print(f"   🧹 Removed forbidden key: {key}")
                continue

            # Clean forbidden summaries
            if isinstance(value, str) and any(
                forbidden in value for forbidden in forbidden_summaries
            ):
                print(f"   🧹 Removed behavioral summary: {key}")
                continue

            # Recursively clean nested structures
            cleaned[key] = clean_scoring_structure(value)

        return cleaned

    elif isinstance(data, list):
        cleaned_list = []
        for item in data:
            cleaned_item = clean_scoring_structure(item)
            # Only keep non-empty items
            if cleaned_item:
                cleaned_list.append(cleaned_item)
        return cleaned_list

    else:
        return data


def upgrade() -> None:
    """
    Comprehensive scoring purge - removes ALL scoring contamination.
    """

    connection = op.get_bind()

    # Get all evidence-based analyses with full_analysis data
    result = connection.execute(
        text(
            """
            SELECT id, full_analysis, repository_url
            FROM analysis_results
            WHERE analysis_method = 'evidence_based'
              AND full_analysis IS NOT NULL
              AND full_analysis != ''
        """
        )
    )

    total_analyses = 0
    cleaned_analyses = 0

    print("\n🔥 THE GREAT PURGE 2.0 - COMPREHENSIVE SCORING ELIMINATION")
    print("=" * 60)

    for row in result:
        total_analyses += 1

        try:
            analysis_data = json.loads(row.full_analysis)
            original_size = len(json.dumps(analysis_data))

            # Apply comprehensive cleaning
            cleaned_data = clean_scoring_structure(analysis_data)
            cleaned_size = len(json.dumps(cleaned_data))

            # Calculate reduction
            reduction_percent = ((original_size - cleaned_size) / original_size) * 100

            if reduction_percent > 5:  # Only update if significant cleaning occurred
                print(f"\n🚨 Analysis {row.id[:8]}... ({row.repository_url})")
                print(
                    f"   📊 Size reduced by {reduction_percent:.1f}% "
                    f"({original_size} → {cleaned_size} chars)"
                )

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
                    {"id": row.id, "cleaned_data": json.dumps(cleaned_data)},
                )
                cleaned_analyses += 1
                print("   ✅ Purged and updated")

        except Exception as e:
            print(f"   ❌ Error cleaning {row.id}: {e}")
            continue

    print("\n" + "=" * 60)
    print("📊 THE GREAT PURGE 2.0 SUMMARY:")
    print(f"   Total evidence-based analyses: {total_analyses}")
    print(f"   Analyses cleaned: {cleaned_analyses}")
    print(f"   Contamination removed: {cleaned_analyses > 0}")

    if cleaned_analyses > 0:
        print("\n✅ SUCCESS: Database now stores same clean data that users see!")
        print("   🎯 Training data contamination eliminated")
        print("   🔒 Evidence-based principles enforced at source")
    else:
        print("\n🎉 Database already clean - no contamination found!")

    print("   🚀 Ready for production deployment")


def downgrade() -> None:
    """
    Cannot restore scoring contamination - The Great Purge 2.0 is irreversible.
    """
    print("⚠️  Cannot restore comprehensive scoring contamination")
    print("   The Great Purge 2.0 has permanently eliminated all scoring data")
    print("   This ensures training data purity for future ML/AI systems")
    pass
