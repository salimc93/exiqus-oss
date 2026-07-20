"""Purge behavioral inferences from PR analysis data

Revision ID: purge_pr_analysis_inferences
Revises: add_pr_analysis_tables
Create Date: 2025-10-02

This migration:
1. Identifies PR analyses with behavioral inferences in full_analysis JSON
2. Removes forbidden corporate jargon and personality inferences
3. Ensures EVIDENCE ONLY principle - no unobservable behavioral claims
"""

import json
import re
from typing import Any, Tuple

from alembic import op
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = "purge_pr_analysis_inferences"
down_revision = "add_pr_analysis_tables"
branch_labels = None
depends_on = None


def has_forbidden_inferences(data: Any) -> Tuple[bool, list]:
    """Check if data contains forbidden behavioral inferences or corporate jargon."""

    # FORBIDDEN_PHRASES - corporate jargon and behavioral inferences
    FORBIDDEN_PATTERNS = [
        r"minimal\s+bureaucracy",
        r"bureaucratic",
        r"startup\s+mentality",
        r"cultural?\s+fit",
        r"team\s+player",
        r"go[_\s-]?getter",
        r"self[_\s-]?starter",
        r"proactive\s+(approach|mindset)",
        r"takes?\s+initiative",
        r"ownership\s+mentality",
        r"entrepreneurial\s+spirit",
        r"startup\s+environment\s+fit",
        r"autonomous\s+work\s+style",
        r"independent\s+problem[_\s-]?solving\s+approach",
        r"fits?\s+startup\s+environments?",
        r"work\s+ethic",
        r"dedication",
        r"dedicated\s+(developer|contributor|programmer)",
        r"hard[_\s-]?working",
        r"committed\s+to\s+(the\s+)?project",
        r"ego[_\s-]?less",
        r"humble",
        r"growth\s+mindset",
        r"learning\s+attitude",
        r"strong\s+collaboration",
        r"good\s+team\s+fit",
    ]

    violations = []

    def check_text(text: str, path: str = "") -> None:
        if not isinstance(text, str):
            return

        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                violations.append(
                    {"pattern": pattern, "path": path, "sample": text[:100]}
                )

    def check_recursive(obj: Any, path: str = "") -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                check_recursive(value, current_path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                check_recursive(item, f"{path}[{i}]")
        elif isinstance(obj, str):
            check_text(obj, path)

    try:
        if isinstance(data, str):
            check_recursive(json.loads(data))
        else:
            check_recursive(data)
    except (json.JSONDecodeError, TypeError):
        pass

    return len(violations) > 0, violations


def clean_pr_inferences(data: Any) -> Any:
    """Recursively remove forbidden behavioral inferences from PR analysis JSON."""

    FORBIDDEN_PATTERNS = [
        r"minimal\s+bureaucracy",
        r"bureaucratic",
        r"startup\s+mentality",
        r"cultural?\s+fit",
        r"team\s+player",
        r"go[_\s-]?getter",
        r"self[_\s-]?starter",
        r"proactive\s+(approach|mindset)",
        r"takes?\s+initiative",
        r"ownership\s+mentality",
        r"entrepreneurial\s+spirit",
        r"startup\s+environment\s+fit",
        r"autonomous\s+work\s+style",
        r"independent\s+problem[_\s-]?solving\s+approach",
        r"fits?\s+startup\s+environments?",
        r"work\s+ethic",
        r"dedication",
        r"dedicated\s+(developer|contributor|programmer)",
        r"hard[_\s-]?working",
        r"committed\s+to\s+(the\s+)?project",
        r"ego[_\s-]?less",
        r"humble",
        r"growth\s+mindset",
        r"learning\s+attitude",
        r"strong\s+collaboration",
        r"good\s+team\s+fit",
    ]

    def sanitize_text(text: str) -> str:
        """Remove sentences containing forbidden patterns."""
        if not isinstance(text, str):
            return text

        # Check each forbidden phrase
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                # Find and remove sentences containing this pattern
                sentences = text.split(".")
                filtered_sentences = []

                for sentence in sentences:
                    if not re.search(pattern, sentence, re.IGNORECASE):
                        filtered_sentences.append(sentence)

                text = ".".join(filtered_sentences)

        # Clean up formatting
        text = re.sub(r"\.+", ".", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def clean_recursive(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {key: clean_recursive(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [clean_recursive(item) for item in obj]
        elif isinstance(obj, str):
            return sanitize_text(obj)
        else:
            return obj

    return clean_recursive(data)


def upgrade() -> None:
    """
    Purge behavioral inferences from PR analysis data.
    """

    connection = op.get_bind()

    # Check if table exists
    result = connection.execute(
        text(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'pr_analysis_results')"
        )
    )
    table_exists = result.scalar()

    if not table_exists:
        print("⏭️  pr_analysis_results table doesn't exist - skipping purge")
        return

    # Get all PR analysis records
    result = connection.execute(
        text(
            """
            SELECT id, full_analysis, summary_report, detailed_report, ai_insights
            FROM pr_analysis_results
            WHERE full_analysis IS NOT NULL
        """
        )
    )

    contaminated_count = 0
    cleaned_count = 0

    for row in result:
        try:
            # Check all JSON fields for contamination
            fields_to_check = {
                "full_analysis": row.full_analysis,
                "summary_report": row.summary_report,
                "detailed_report": row.detailed_report,
                "ai_insights": row.ai_insights,
            }

            has_violations = False
            cleaned_fields = {}

            for field_name, field_value in fields_to_check.items():
                if field_value:
                    has_forbidden, violations = has_forbidden_inferences(field_value)

                    if has_forbidden:
                        has_violations = True
                        contaminated_count += 1

                        print(
                            f"🚨 PR Analysis {row.id} contains {len(violations)} inference violations in {field_name}"
                        )
                        for v in violations[:3]:  # Show first 3 violations
                            print(f"   - Pattern: {v['pattern']} at {v['path']}")

                        # Clean the data
                        data = (
                            json.loads(field_value)
                            if isinstance(field_value, str)
                            else field_value
                        )
                        cleaned_data = clean_pr_inferences(data)
                        cleaned_fields[field_name] = json.dumps(cleaned_data)

            # Update if contamination found
            if has_violations and cleaned_fields:
                set_clauses = []
                params = {"id": row.id}

                for field_name, cleaned_value in cleaned_fields.items():
                    set_clauses.append(f"{field_name} = :{field_name}")
                    params[field_name] = cleaned_value

                if set_clauses:
                    connection.execute(
                        text(
                            f"""
                            UPDATE pr_analysis_results
                            SET {', '.join(set_clauses)},
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = :id
                        """
                        ),
                        params,
                    )
                    cleaned_count += 1
                    print(f"   ✅ Cleaned PR analysis {row.id}")

        except Exception as e:
            print(f"   ❌ Error processing PR analysis {row.id}: {e}")
            continue

    print("\n📊 PR ANALYSIS INFERENCE PURGE REPORT:")
    print(f"   Total contaminated analyses: {contaminated_count}")
    print(f"   Successfully cleaned: {cleaned_count}")

    if cleaned_count > 0:
        print("\n✅ EVIDENCE ONLY PRINCIPLE ENFORCED")
        print(f"   {cleaned_count} PR analyses cleaned of behavioral inferences")
    else:
        print(
            "\n✅ NO CONTAMINATION DETECTED - All PR analyses follow evidence-only principle"
        )


def downgrade() -> None:
    """
    Cannot restore behavioral inferences - purge is permanent.
    """
    print("⚠️  Cannot restore behavioral inferences - Evidence-only purge is permanent")
    print("   Inference data has been permanently removed from PR analysis system")
    pass
