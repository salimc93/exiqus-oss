"""Backfill evidence-based columns from full_analysis and remove obsolete scoring columns

Revision ID: backfill_evidence_columns
Revises:
Create Date: 2025-01-12

This migration:
1. Backfills all evidence-based columns from existing full_analysis JSON data
2. Removes obsolete scoring columns (overall_score, confidence_score, recommendation)
   that are no longer used in the evidence-based analysis system (post-Great Purge)
"""

import json

import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = "backfill_evidence_columns"
down_revision = "add_scale_plus_batch_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Backfill evidence-based columns from full_analysis JSON and remove obsolete columns.
    """

    # First, backfill the evidence-based columns from full_analysis
    connection = op.get_bind()

    # Get all records with full_analysis data
    result = connection.execute(
        text(
            """
            SELECT id, full_analysis
            FROM analysis_results
            WHERE full_analysis IS NOT NULL
              AND full_analysis != ''
              AND analysis_method = 'evidence_based'
        """
        )
    )

    records_updated = 0

    for row in result:
        try:
            analysis_id = row.id
            full_analysis = json.loads(row.full_analysis)

            # Extract the analysis data
            if "analysis" in full_analysis:
                analysis_data = full_analysis["analysis"]
            else:
                analysis_data = full_analysis

            # Prepare update data with proper field mappings
            update_data = {}

            # Map fields according to FIELD_MAPPING.md
            if "evidence_patterns" in analysis_data:
                update_data["evidence_patterns"] = json.dumps(
                    analysis_data["evidence_patterns"]
                )

            if "insights" in analysis_data:
                update_data["screening_insights"] = json.dumps(
                    analysis_data["insights"]
                )

            if "confidence_explanation" in analysis_data:
                update_data["confidence_explanation"] = analysis_data[
                    "confidence_explanation"
                ]

            if "technical_assessment" in analysis_data:
                update_data["technical_patterns"] = json.dumps(
                    analysis_data["technical_assessment"]
                )

            if "professional_practices" in analysis_data:
                update_data["collaboration_patterns"] = json.dumps(
                    analysis_data["professional_practices"]
                )

            if "communication_skills" in analysis_data:
                update_data["quality_indicators"] = json.dumps(
                    analysis_data["communication_skills"]
                )

            if "growth_indicators" in analysis_data:
                update_data["temporal_insights"] = json.dumps(
                    analysis_data["growth_indicators"]
                )

            if "questions" in analysis_data:
                update_data["skill_evolution"] = json.dumps(analysis_data["questions"])

            if "recommendations" in analysis_data:
                update_data["behavioral_analysis"] = json.dumps(
                    analysis_data["recommendations"]
                )

            if "green_flags" in analysis_data:
                update_data["security_practices"] = json.dumps(
                    analysis_data["green_flags"]
                )

            if "red_flags" in analysis_data:
                update_data["context_alignment"] = json.dumps(
                    analysis_data["red_flags"]
                )

            if "areas_to_explore" in analysis_data:
                update_data["verification_gaps"] = json.dumps(
                    analysis_data["areas_to_explore"]
                )

            # Build and execute update query
            if update_data:
                set_clause = ", ".join(
                    [f"{key} = :{key}" for key in update_data.keys()]
                )
                update_data["id"] = analysis_id

                connection.execute(
                    text(
                        f"""
                        UPDATE analysis_results
                        SET {set_clause}
                        WHERE id = :id
                    """
                    ),
                    update_data,
                )
                records_updated += 1

        except Exception as e:
            print(f"Error processing record {row.id}: {e}")
            continue

    print(f"Successfully backfilled {records_updated} records")

    # Now remove the obsolete scoring columns
    # These columns are from the old scoring system and should not exist
    # in the evidence-based analysis system

    # Check which columns exist before trying to drop them
    inspector = sa.inspect(connection)
    existing_columns = [
        col["name"] for col in inspector.get_columns("analysis_results")
    ]

    columns_to_drop = []
    for col in ["overall_score", "confidence_score", "recommendation"]:
        if col in existing_columns:
            columns_to_drop.append(col)

    if columns_to_drop:
        with op.batch_alter_table("analysis_results") as batch_op:
            for col in columns_to_drop:
                batch_op.drop_column(col)
        print(f"Removed obsolete columns: {', '.join(columns_to_drop)}")
    else:
        print("Obsolete columns already removed")


def downgrade() -> None:
    """
    Re-add the obsolete columns (but don't restore data as it's obsolete).
    """

    with op.batch_alter_table("analysis_results") as batch_op:
        # Re-add the obsolete columns for rollback
        batch_op.add_column(sa.Column("overall_score", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("confidence_score", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("recommendation", sa.String(50), nullable=True))

    print("Re-added obsolete columns for rollback")
