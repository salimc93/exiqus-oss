# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Markdown renderer for repository analysis reports.
"""

from typing import Any, Dict, List

from ..report_models import StructuredReport
from .report_renderer import ReportRenderer


class MarkdownRenderer(ReportRenderer):
    """Renders reports in Markdown format."""

    def render(self, report: StructuredReport) -> str:
        """Format report as Markdown - Evidence-Based Approach."""
        md = f"""# Repository Analysis Report

**Repository:** {report.repository_name}
**Analysis Date:** {report.analysis_date.strftime("%Y-%m-%d %H:%M")}

## Executive Summary

{report.executive_summary}

## Key Observations

### Evidence Patterns
"""
        for strength in report.key_strengths:
            md += f"- {strength}\n"

        md += "\n### Areas for Discussion\n"
        for concern in report.primary_concerns:
            md += f"- {concern}\n"

        # Add screening insights section
        if report.screening_insights:
            md += "\n## Evidence-Based Analysis\n"

            # Overall impression
            md += f"\n**Overall Assessment:** {report.screening_insights.overall_impression}\n"
            md += f"\n**Analysis Context:** {report.screening_insights.confidence_explanation}\n"

            # Group insights by category
            insights_by_category: Dict[str, List[Any]] = {}
            for insight in report.screening_insights.insights:
                category = insight.category.value
                if category not in insights_by_category:
                    insights_by_category[category] = []
                insights_by_category[category].append(insight)

            for category, insights in sorted(insights_by_category.items()):
                md += f"\n### {category.replace('_', ' ').title()}\n"
                for insight in insights:
                    md += f"\n**{insight.title}**\n"
                    md += f"{insight.description}\n"
                    if insight.evidence:
                        md += "\n_Supporting Evidence:_\n"
                        for evidence in insight.evidence[:2]:
                            md += f"- {evidence}\n"

            # Data limitations
            if report.screening_insights.data_limitations:
                md += "\n### Analysis Considerations\n"
                md += "_Repository data limitations:_\n"
                for limitation in report.screening_insights.data_limitations:
                    md += f"- {limitation}\n"

        # Add recommendations if any (these come from areas_to_explore)
        if report.analysis_recommendations:
            md += "\n## Topics for Discussion\n"
            for rec in report.analysis_recommendations:
                md += f"- {rec}\n"

        # Add evidence summary for Professional and Enterprise tiers
        if report.subscription_tier in ["professional", "enterprise"]:
            if report.evidence_summary:
                md += "\n## Detailed Evidence Analysis\n"
                patterns = report.evidence_summary.get("patterns", [])
                if patterns:
                    md += "### Key Evidence Patterns\n"
                    for pattern in patterns[:5]:
                        md += f"- **{pattern.get('pattern', 'N/A')}**\n"
                        md += f"  - *Evidence:* {pattern.get('evidence', '')}\n"
                        if pattern.get("files"):
                            md += f"  - *Files:* {', '.join(pattern['files'][:3])}\n"

            if report.interview_questions:
                md += "\n## Evidence-Based Interview Questions\n"
                md += f"*Estimated time: {report.interview_questions.get('estimated_time', '15-30 minutes')}*\n\n"

                all_questions = report.interview_questions.get("all_questions", [])
                upgrade_prompt = report.interview_questions.get("upgrade_prompt", "")

                for i, q in enumerate(all_questions, 1):
                    if q.get("is_blurred", False):
                        md += f"{i}. **{q.get('question', '')}**\n"
                        md += f"   - {q.get('upgrade_message', '')}\n\n"
                    else:
                        md += f"{i}. **{q.get('question', '')}**\n"
                        md += f"   - *Based on:* {q.get('evidence_reference', '')}\n"
                        md += (
                            f"   - *Listen for:* {q.get('what_to_listen_for', '')}\n\n"
                        )

                if upgrade_prompt:
                    md += f"\n> {upgrade_prompt}\n"

        return md
