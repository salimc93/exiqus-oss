# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
PR Analysis Report Generator.

This module generates human-readable reports from PR analysis results,
focusing on evidence patterns and quality signals without numerical scores.
"""

from datetime import datetime
from typing import Any, Dict

from ..utils.logging import get_logger
from .pr_models import PREvidence, QualitySignals

logger = get_logger(__name__)


class PRReportGenerator:
    """Generates formatted reports from PR analysis results."""

    def __init__(self) -> None:
        """Initialize the PR report generator."""
        pass

    def generate_summary_report(
        self,
        username: str,
        evidence: PREvidence,
        quality_signals: QualitySignals,
        context: str = "OPEN_SOURCE",
        role: str = "senior",
    ) -> str:
        """Generate a summary report from PR analysis.

        Args:
            username: GitHub username analyzed
            evidence: Extracted evidence patterns
            quality_signals: Calculated quality signals
            context: Analysis context (STARTUP, ENTERPRISE, AGENCY, OPEN_SOURCE)
            role: Role level for interview questions (junior, mid, senior)

        Returns:
            Formatted report as markdown string
        """
        report = []
        report.append(f"# PR Analysis Report: {username}")
        report.append(f"\n**Context**: {context}")
        report.append(
            f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
        report.append("")

        # Executive Summary
        report.append("## Executive Summary")
        report.append(self._generate_executive_summary(evidence, quality_signals))
        report.append("")

        # Key Evidence Patterns
        if evidence.technical_substance:
            report.append("## Technical Contribution Patterns")
            for item in evidence.technical_substance[:5]:  # Top 5
                report.append(f"- {item}")
            report.append("")

        # Collaboration Patterns
        if evidence.collaboration_patterns:
            report.append("## Collaboration & Team Dynamics")
            for pattern in evidence.collaboration_patterns[:5]:
                report.append(f"- {pattern}")
            report.append("")

        # Cross-Repository Work
        if evidence.cross_repo_contributions:
            report.append("## Cross-Repository Adaptability")
            for contribution in evidence.cross_repo_contributions[:3]:
                report.append(f"- {contribution}")
            report.append("")

        # Review Engagement
        if evidence.review_responsiveness:
            report.append("## Review Process Engagement")
            for item in evidence.review_responsiveness[:3]:
                report.append(f"- {item}")
            report.append("")

        # Integration Patterns
        if evidence.integration_patterns:
            report.append("## Integration Practices")
            for pattern in evidence.integration_patterns[:3]:
                report.append(f"- {pattern}")
            report.append("")

        # Quality Indicators
        report.append("## Quality Indicators")
        report.append(self._format_quality_indicators(quality_signals))
        report.append("")

        # Areas to Explore
        if evidence.areas_to_explore:
            report.append("## Areas for Further Discussion")
            for area in evidence.areas_to_explore[:5]:
                report.append(f"- {area}")
            report.append("")

        return "\n".join(report)

    def generate_detailed_report(
        self,
        username: str,
        evidence: PREvidence,
        quality_signals: QualitySignals,
        context: str = "OPEN_SOURCE",
        include_all_evidence: bool = False,
        role: str = "senior",
    ) -> Dict[str, Any]:
        """Generate a detailed structured report.

        Args:
            username: GitHub username analyzed
            evidence: Extracted evidence patterns
            quality_signals: Calculated quality signals
            context: Analysis context
            include_all_evidence: Whether to include all evidence items
            role: Role level for interview questions (junior, mid, senior)

        Returns:
            Structured dictionary with report sections
        """
        report: Dict[str, Any] = {
            "username": username,
            "context": context,
            "generated_at": datetime.now().isoformat(),
            "summary": self._generate_executive_summary(evidence, quality_signals),
            "evidence_sections": {},
            "quality_signals": self._format_quality_signals_dict(quality_signals),
            "total_evidence_items": evidence.total_evidence_count(),
        }

        # Add evidence sections
        limit = None if include_all_evidence else 10

        if evidence.technical_substance:
            report["evidence_sections"]["technical_substance"] = {
                "title": "Technical Contribution Patterns",
                "items": evidence.technical_substance[:limit],
                "total_count": len(evidence.technical_substance),
            }

        if evidence.collaboration_patterns:
            report["evidence_sections"]["collaboration"] = {
                "title": "Collaboration & Team Dynamics",
                "items": evidence.collaboration_patterns[:limit],
                "total_count": len(evidence.collaboration_patterns),
            }

        if evidence.cross_repo_contributions:
            report["evidence_sections"]["cross_repository"] = {
                "title": "Cross-Repository Adaptability",
                "items": evidence.cross_repo_contributions[:limit],
                "total_count": len(evidence.cross_repo_contributions),
            }

        if evidence.review_responsiveness:
            report["evidence_sections"]["review_engagement"] = {
                "title": "Review Process Engagement",
                "items": evidence.review_responsiveness[:limit],
                "total_count": len(evidence.review_responsiveness),
            }

        if evidence.integration_patterns:
            report["evidence_sections"]["integration"] = {
                "title": "Integration Practices",
                "items": evidence.integration_patterns[:limit],
                "total_count": len(evidence.integration_patterns),
            }

        if evidence.pr_description_quality:
            report["evidence_sections"]["documentation"] = {
                "title": "Documentation Quality",
                "items": evidence.pr_description_quality[:limit],
                "total_count": len(evidence.pr_description_quality),
            }

        if evidence.process_adherence:
            report["evidence_sections"]["process"] = {
                "title": "Process Adherence",
                "items": evidence.process_adherence[:limit],
                "total_count": len(evidence.process_adherence),
            }

        if evidence.areas_to_explore:
            report["areas_to_explore"] = evidence.areas_to_explore[:10]

        return report

    def _generate_executive_summary(
        self, evidence: PREvidence, signals: QualitySignals
    ) -> str:
        """Generate executive summary from evidence and signals.

        Args:
            evidence: PR evidence patterns
            signals: Quality signals

        Returns:
            Executive summary paragraph
        """
        summary_parts = []

        # Basic statistics
        if signals.total_prs > 0:
            summary_parts.append(
                f"Analyzed {signals.total_prs} pull requests across "
                f"{signals.unique_repos} repositories."
            )

        # Merge rate insight
        if signals.merge_rate is not None and signals.merge_rate > 0:
            summary_parts.append(
                f"Production integration rate of {signals.merge_rate:.0%} "
                f"({signals.merged_prs} PRs successfully merged)."
            )

        # Time consistency
        if signals.contribution_timespan:
            # contribution_timespan is already a formatted string like "6 months"
            summary_parts.append(
                f"Sustained contributions over {signals.contribution_timespan}."
            )

        # Collaboration indicators
        if signals.pair_programming_count > 0:
            summary_parts.append(
                f"Evidence of pair programming in {signals.pair_programming_count} PRs."
            )

        if signals.deep_collaboration_count > 0:
            summary_parts.append(
                f"Deep collaboration (3+ review cycles) in "
                f"{signals.deep_collaboration_count} PRs."
            )

        # Feature ownership
        if signals.feature_ownership_count > 0:
            summary_parts.append(
                f"Took {signals.feature_ownership_count} significant features "
                "to production."
            )

        # Add key evidence insight
        if evidence.technical_substance:
            # Look for production success or major contributions
            for item in evidence.technical_substance[:2]:
                if "Production Integration Success" in item:
                    break
                if "MAJOR SUCCESS" in item:
                    # Extract PR title from the evidence
                    import re

                    match = re.search(r"'([^']+)'", item)
                    if match:
                        summary_parts.append(
                            f"Notable contribution: {match.group(1)[:50]}"
                        )
                    break

        return " ".join(summary_parts) if summary_parts else "No PR data available."

    def _format_quality_indicators(self, signals: QualitySignals) -> str:
        """Format quality signals as readable text.

        Args:
            signals: Quality signals to format

        Returns:
            Formatted quality indicators
        """
        indicators = []

        # Activity level
        if signals.monthly_pr_rate:
            indicators.append(
                f"- PR velocity: ~{signals.monthly_pr_rate:.1f} PRs/month"
            )

        # Repository diversity
        indicators.append(
            f"- Repository diversity: {signals.unique_repos} repositories"
        )

        # Work distribution
        if signals.feature_prs > 0 or signals.fix_prs > 0:
            total = signals.feature_prs + signals.fix_prs
            if total > 0:
                feature_pct = (signals.feature_prs / total) * 100
                indicators.append(
                    f"- Work distribution: {feature_pct:.0f}% features, "
                    f"{100 - feature_pct:.0f}% fixes/maintenance"
                )

        # Collaboration metrics
        if signals.pair_programming_count > 0:
            indicators.append(
                f"- Pair programming instances: {signals.pair_programming_count}"
            )

        if signals.deep_collaboration_count > 0:
            indicators.append(
                f"- PRs with extensive review: {signals.deep_collaboration_count}"
            )

        # Production readiness
        if signals.merge_rate is not None:
            indicators.append(f"- Production merge rate: {signals.merge_rate:.0%}")

        # Time consistency
        if signals.first_pr_date and signals.last_pr_date:
            time_span = (signals.last_pr_date - signals.first_pr_date).days
            if time_span > 0:
                indicators.append(f"- Contribution span: {time_span} days")

        return (
            "\n".join(indicators) if indicators else "- No quality indicators available"
        )

    def _format_quality_signals_dict(self, signals: QualitySignals) -> Dict[str, Any]:
        """Convert quality signals to dictionary format.

        Args:
            signals: Quality signals to convert

        Returns:
            Dictionary representation of signals
        """
        result: Dict[str, Any] = {
            "total_prs": signals.total_prs,
            "merged_prs": signals.merged_prs,
            "merge_rate": signals.merge_rate,
            "unique_repositories": signals.unique_repos,
            "feature_prs": signals.feature_prs,
            "fix_prs": signals.fix_prs,
            "monthly_pr_rate": signals.monthly_pr_rate,
            "pair_programming_count": signals.pair_programming_count,
            "deep_collaboration_count": signals.deep_collaboration_count,
            "feature_ownership_count": signals.feature_ownership_count,
        }

        # Add time-based metrics
        if signals.first_pr_date:
            result["first_pr_date"] = signals.first_pr_date.isoformat()
        if signals.last_pr_date:
            result["last_pr_date"] = signals.last_pr_date.isoformat()
        if signals.contribution_timespan:
            result["contribution_timespan"] = signals.contribution_timespan

        return result

    def format_for_integration(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Format PR analysis for integration with main report generator.

        Args:
            analysis_result: Result from PRAnalyzer.analyze_user()

        Returns:
            Formatted data for main report integration
        """
        if not analysis_result.get("success", False):
            return {
                "pr_analysis_available": False,
                "error": analysis_result.get("error", "Analysis failed"),
            }

        evidence = analysis_result.get("evidence")
        signals = analysis_result.get("quality_signals")

        if not evidence or not signals:
            return {
                "pr_analysis_available": False,
                "error": "Missing evidence or signals",
            }

        return {
            "pr_analysis_available": True,
            "pr_evidence": {
                "technical_patterns": evidence.technical_substance[:10],
                "collaboration_patterns": evidence.collaboration_patterns[:10],
                "cross_repo_work": evidence.cross_repo_contributions[:5],
                "review_engagement": evidence.review_responsiveness[:5],
                "areas_to_explore": evidence.areas_to_explore[:5],
                "total_evidence_items": evidence.total_evidence_count(),
            },
            "pr_quality_signals": self._format_quality_signals_dict(signals),
            "pr_summary": self._generate_executive_summary(evidence, signals),
        }
