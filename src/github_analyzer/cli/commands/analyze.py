# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Single repository analysis command implementation.

Handles the 'analyze' CLI command for analyzing individual GitHub repositories
with context-aware AI insights and multiple output formats.
"""

import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table

from ...ai.analyzer import AIAnalyzer
from ...ai.cost_tracker import CostTracker
from ...core.context_analyzer import AnalysisContext
from ...core.report_generator import ReportFormat
from ...data.github_fetcher import GitHubFetcher
from ...utils.helpers import validate_github_url
from ...utils.logging import get_logger

console = Console()
logger = get_logger(__name__)


def run_analysis(
    repo_url: str,
    output_format: str = "table",
    context: Optional[str] = None,
    save_path: Optional[str] = None,
    verbose: bool = False,
    comprehensive: bool = True,
) -> None:
    """
    Run comprehensive analysis on a single GitHub repository.

    Args:
        repo_url: GitHub repository URL to analyze
        output_format: Output format (json, yaml, table, report, markdown, html, pdf)
        context: Hiring context (startup, enterprise, agency, open_source, general)
        save_path: Path to save results
        verbose: Enable verbose output
        comprehensive: Use comprehensive analysis with all business logic components
    """
    try:
        # Validate repository URL
        if not validate_github_url(repo_url):
            console.print(
                f"[red]Error: Invalid GitHub repository URL: {repo_url}[/red]"
            )
            sys.exit(1)

        # Initialize components
        cost_tracker = CostTracker()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=not verbose,
        ) as progress:
            # Step 1: Fetch repository data
            task = progress.add_task("Fetching repository data...", total=None)

            try:
                fetcher = GitHubFetcher()
                repo_data = fetcher.fetch_repository_data(repo_url)
                progress.update(task, description="✅ Repository data fetched")
            except Exception as e:
                progress.update(task, description="❌ Failed to fetch repository data")
                console.print(f"[red]Error fetching repository data: {e}[/red]")
                sys.exit(1)

            # Step 2: Parse hiring context
            analysis_context = None
            if context:
                try:
                    context_map = {
                        "startup": AnalysisContext.STARTUP,
                        "enterprise": AnalysisContext.ENTERPRISE,
                        "agency": AnalysisContext.AGENCY,
                        "open_source": AnalysisContext.OPEN_SOURCE,
                        "general": AnalysisContext.GENERAL,
                        "freelance": AnalysisContext.AGENCY,  # Alias for agency
                    }
                    analysis_context = context_map.get(context.lower())
                    if not analysis_context:
                        console.print(
                            f"[yellow]Warning: Unknown context '{context}', using general context[/yellow]"
                        )
                        analysis_context = AnalysisContext.GENERAL
                except Exception:
                    console.print(
                        f"[yellow]Warning: Invalid context '{context}', using general context[/yellow]"
                    )
                    analysis_context = AnalysisContext.GENERAL

            # Step 3: Run comprehensive analysis
            progress.update(task, description="Running comprehensive analysis...")

            try:
                analyzer = AIAnalyzer()

                # Parse report format
                format_map = {
                    "json": ReportFormat.JSON,
                    "markdown": ReportFormat.MARKDOWN,
                    "html": ReportFormat.HTML,
                    "pd": ReportFormat.PDF_READY,
                    "report": ReportFormat.JSON,  # Default to JSON for report
                    "table": ReportFormat.JSON,  # Will be formatted as table for display
                }
                report_format = format_map.get(output_format.lower(), ReportFormat.JSON)

                if comprehensive:
                    # Use comprehensive analysis with all business logic
                    analysis = analyzer.analyze_repository_comprehensive(
                        repo_data=repo_data,
                        context=analysis_context,
                        format_type=report_format,
                    )
                    progress.update(
                        task, description="✅ Comprehensive analysis completed"
                    )
                else:
                    # Use legacy analysis for compatibility
                    analysis = analyzer.analyze_repository(repo_data)
                    progress.update(task, description="✅ Analysis completed")

            except Exception as e:
                progress.update(task, description="❌ Failed to generate analysis")
                console.print(f"[red]Error generating analysis: {e}[/red]")
                if verbose:
                    console.print(f"[red]Details: {str(e)}[/red]")
                sys.exit(1)

        # Prepare results
        if comprehensive:
            # Use comprehensive analysis result structure
            results = {
                "repository": {
                    "url": repo_data.url,
                    "name": repo_data.name,
                    "owner": repo_data.owner,
                    "description": repo_data.description,
                    "stars": repo_data.stars,
                    "forks": repo_data.forks,
                    "languages": repo_data.languages,
                    "created_at": repo_data.created_at.isoformat(),
                    "updated_at": repo_data.updated_at.isoformat(),
                },
                "analysis": {
                    "summary": analysis.summary,
                    "evidence_strength": (
                        asdict(analysis.evidence_strength)
                        if hasattr(analysis, "evidence_strength")
                        and analysis.evidence_strength
                        else {}
                    ),
                    "key_insights": (
                        analysis.key_insights
                        if hasattr(analysis, "key_insights")
                        else []
                    ),
                    "evidence_patterns": (
                        [asdict(p) for p in analysis.evidence_patterns]
                        if hasattr(analysis, "evidence_patterns")
                        else []
                    ),
                    "verification_gaps": (
                        analysis.verification_gaps
                        if hasattr(analysis, "verification_gaps")
                        else []
                    ),
                    "generated_by": (
                        analysis.generated_by
                        if hasattr(analysis, "generated_by")
                        else "unknown"
                    ),
                    "repository_type": (
                        analysis.repository_type
                        if hasattr(analysis, "repository_type")
                        else None
                    ),
                    # Evidence-based approach - no trust scores
                    "risk_level": (
                        analysis.risk_level if hasattr(analysis, "risk_level") else None
                    ),
                    "context": analysis.context.value if analysis.context else None,
                },
                "metrics": {
                    "total_commits": repo_data.metrics.total_commits,
                    "unique_contributors": repo_data.metrics.unique_contributors,
                    "lines_of_code": repo_data.metrics.lines_of_code,
                    "test_coverage_estimate": repo_data.metrics.test_coverage_estimate,
                    "documentation_presence": repo_data.metrics.documentation_presence,
                    "days_since_last_commit": repo_data.metrics.days_since_last_commit,
                },
                "cost_info": {
                    "tokens_used": cost_tracker.get_total_tokens(),
                    "estimated_cost": cost_tracker.get_total_cost(),
                    "analysis_cost": analysis.cost,
                    "analysis_time": analysis.analysis_time,
                },
            }

            # Add business logic components if available
            if analysis.classification_result:
                results["classification"] = {
                    "method": analysis.classification_result.method.value,
                    "confidence": analysis.classification_result.confidence,
                    "repository_type": (
                        analysis.classification_result.repository_type.value
                        if analysis.classification_result.repository_type
                        else None
                    ),
                    "template_category": (
                        analysis.classification_result.template_category.value
                        if analysis.classification_result.template_category
                        else None
                    ),
                    "reasoning": analysis.classification_result.reasoning,
                    "cost_estimate": analysis.classification_result.cost_estimate,
                }

            if analysis.contextual_assessment:
                results["contextual_assessment"] = {
                    "context": analysis.contextual_assessment.context.value,
                    "evidence_count": analysis.contextual_assessment.evidence_count,
                    "strengths": analysis.contextual_assessment.strengths,
                    "concerns": analysis.contextual_assessment.concerns,
                    "recommendations": analysis.contextual_assessment.recommendations,
                    "key_insight": analysis.contextual_assessment.key_insight,
                }

            if analysis.confidence_scoring:
                results["confidence_scoring"] = {
                    "overall_confidence": analysis.confidence_scoring.confidence_breakdown.overall_confidence,
                    "confidence_grade": analysis.confidence_scoring.confidence_breakdown.get_confidence_grade(),
                    "data_completeness": analysis.confidence_scoring.confidence_breakdown.data_completeness,
                    # Evidence-based approach - no trust scores
                    "overall_risk_level": analysis.confidence_scoring.overall_risk_level.value,
                    "risk_indicator_count": len(
                        analysis.confidence_scoring.risk_indicators
                    ),
                    "high_risk_count": len(
                        [
                            r
                            for r in analysis.confidence_scoring.risk_indicators
                            if r.risk_level.value in ["high", "critical"]
                        ]
                    ),
                    "recommendations": analysis.confidence_scoring.recommendations,
                }

            if analysis.structured_report:
                results["structured_report"] = {
                    "executive_summary": analysis.structured_report.executive_summary,
                    "assessment_type": "evidence-based",  # Replaced overall_recommendation
                    # Evidence-based approach - no confidence scores
                    "report_format": report_format.value,
                }
        else:
            # Legacy analysis result structure
            results = {
                "repository": {
                    "url": repo_data.url,
                    "name": repo_data.name,
                    "owner": repo_data.owner,
                    "description": repo_data.description,
                    "stars": repo_data.stars,
                    "forks": repo_data.forks,
                    "languages": repo_data.languages,
                    "created_at": repo_data.created_at.isoformat(),
                    "updated_at": repo_data.updated_at.isoformat(),
                },
                "analysis": {
                    "summary": analysis.summary,
                    "evidence_strength": (
                        asdict(analysis.evidence_strength)
                        if hasattr(analysis, "evidence_strength")
                        and analysis.evidence_strength
                        else {}
                    ),
                    "key_insights": (
                        analysis.key_insights
                        if hasattr(analysis, "key_insights")
                        else []
                    ),
                    "evidence_patterns": (
                        [asdict(p) for p in analysis.evidence_patterns]
                        if hasattr(analysis, "evidence_patterns")
                        else []
                    ),
                    "verification_gaps": (
                        analysis.verification_gaps
                        if hasattr(analysis, "verification_gaps")
                        else []
                    ),
                    "context": "general",
                },
                "metrics": {
                    "total_commits": repo_data.metrics.total_commits,
                    "unique_contributors": repo_data.metrics.unique_contributors,
                    "lines_of_code": repo_data.metrics.lines_of_code,
                    "test_coverage_estimate": repo_data.metrics.test_coverage_estimate,
                    "documentation_presence": repo_data.metrics.documentation_presence,
                    "days_since_last_commit": repo_data.metrics.days_since_last_commit,
                },
                "cost_info": {
                    "tokens_used": cost_tracker.get_total_tokens(),
                    "estimated_cost": cost_tracker.get_total_cost(),
                    "analysis_cost": analysis.cost,
                    "analysis_time": analysis.analysis_time,
                },
            }

        # Output results in requested format
        _output_results(results, output_format, save_path, verbose)

        # Show cost summary if verbose
        if verbose:
            _show_cost_summary(cost_tracker)

    except KeyboardInterrupt:
        console.print("\n[yellow]Analysis cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        console.print(f"[red]Analysis failed: {e}[/red]")
        if verbose:
            raise
        sys.exit(1)


def _output_results(
    results: dict[str, Any], output_format: str, save_path: Optional[str], verbose: bool
) -> None:
    """Output analysis results in the specified format."""

    if output_format == "json":
        output = json.dumps(results, indent=2, default=str)
        if save_path:
            Path(save_path).write_text(output)
            console.print(f"[green]Results saved to {save_path}[/green]")
        else:
            console.print(output)

    elif output_format == "yaml":
        output = yaml.dump(results, default_flow_style=False, sort_keys=False)
        if save_path:
            Path(save_path).write_text(output)
            console.print(f"[green]Results saved to {save_path}[/green]")
        else:
            console.print(output)

    elif output_format == "table":
        _display_table_output(results)
        if save_path:
            # Save as JSON when table format is used with save
            json_output = json.dumps(results, indent=2, default=str)
            Path(save_path).write_text(json_output)
            console.print(f"[green]Results saved to {save_path} (JSON format)[/green]")

    elif output_format == "report":
        _display_report_output(results)
        if save_path:
            # Save as formatted text report
            report_text = _generate_text_report(results)
            Path(save_path).write_text(report_text)
            console.print(f"[green]Report saved to {save_path}[/green]")

    elif output_format in ["markdown", "html", "pd"]:
        # For structured report formats, use the structured report content if available
        if "structured_report" in results:
            if output_format == "markdown":
                console.print("[green]Structured Report (Markdown format):[/green]")
                # Use the report display function for markdown-like output
                _display_report_output(results)
            elif output_format == "html":
                console.print("[green]Structured Report (HTML-ready format):[/green]")
                _display_report_output(results)
            elif output_format == "pd":
                # PDF-ready content
                console.print(
                    "[yellow]PDF-ready content (requires frontend rendering):[/yellow]"
                )
                _display_report_output(results)
        else:
            # Fallback to JSON for unsupported formats
            output = json.dumps(results, indent=2, default=str)
            console.print(output)

        if save_path:
            if "structured_report" in results:
                # Save as formatted text report for structured formats
                report_text = _generate_text_report(results)
                Path(save_path).write_text(report_text)
            else:
                json_output = json.dumps(results, indent=2, default=str)
                Path(save_path).write_text(json_output)
            console.print(f"[green]Results saved to {save_path}[/green]")


def _display_table_output(results: dict[str, Any]) -> None:
    """Display results in a formatted table."""
    repo = results["repository"]
    analysis = results["analysis"]

    # Repository Overview Table
    repo_table = Table(title="🔍 Repository Overview", show_header=True)
    repo_table.add_column("Property", style="bold blue")
    repo_table.add_column("Value", style="white")

    repo_table.add_row("Name", f"{repo['owner']}/{repo['name']}")
    repo_table.add_row("Description", repo["description"] or "No description")
    repo_table.add_row("Stars", str(repo["stars"]))
    repo_table.add_row("Forks", str(repo["forks"]))
    repo_table.add_row(
        "Primary Language",
        list(repo["languages"].keys())[0] if repo["languages"] else "Unknown",
    )
    repo_table.add_row("Last Updated", repo["updated_at"][:10])

    console.print(repo_table)
    console.print()

    # Classification Table
    class_table = Table(title="📊 Repository Classification", show_header=True)
    class_table.add_column("Property", style="bold green")
    class_table.add_column("Value", style="white")

    # Handle both comprehensive and legacy classification formats
    if "classification" in results:
        classification = results["classification"]
        class_table.add_row("Method", classification["method"].title())
        class_table.add_row("Confidence", f"{classification['confidence']:.1%}")
        if classification.get("repository_type"):
            class_table.add_row(
                "Repository Type", classification["repository_type"].title()
            )
        if classification.get("template_category"):
            class_table.add_row("Category", classification["template_category"].title())
    else:
        # Use analysis data for classification info
        analysis = results["analysis"]
        class_table.add_row("Verdict", analysis["verdict"])
        class_table.add_row("Confidence", f"{analysis['confidence']}%")
        if analysis.get("repository_type"):
            class_table.add_row("Repository Type", analysis["repository_type"].title())

    console.print(class_table)
    console.print()

    # Analysis Summary
    console.print(
        Panel(analysis["summary"], title="🤖 AI Analysis Summary", border_style="green")
    )
    console.print()

    # Evidence-based analysis summary
    console.print("[bold]Analysis Type: [green]Evidence-Based[/green][/bold]")

    # Show assessment type (evidence-based)
    if analysis.get("assessment_type"):
        console.print(
            f"[bold]Assessment Type: [cyan]{analysis['assessment_type']}[/cyan][/bold]"
        )

    # Evidence-based - no trust scores

    if analysis.get("risk_level"):
        risk_color = {
            "low": "green",
            "medium": "yellow",
            "high": "red",
            "critical": "bright_red",
        }.get(analysis["risk_level"], "white")
        console.print(
            f"[bold]Risk Level: [{risk_color}]{analysis['risk_level'].title()}[/{risk_color}][/bold]"
        )

    console.print()

    if analysis["strengths"]:
        console.print("[bold green]✅ Strengths:[/bold green]")
        for strength in analysis["strengths"]:
            console.print(f"  • {strength}")
        console.print()

    if analysis["concerns"]:
        console.print("[bold red]⚠️  Concerns:[/bold red]")
        for concern in analysis["concerns"]:
            console.print(f"  • {concern}")
        console.print()

    # Handle recommendations from different sources
    recommendations = []
    if analysis.get("recommendations"):
        recommendations.extend(analysis["recommendations"])

    # Add contextual assessment recommendations
    if "contextual_assessment" in results and results["contextual_assessment"].get(
        "recommendations"
    ):
        recommendations.extend(results["contextual_assessment"]["recommendations"])

    # Add confidence scoring recommendations
    if "confidence_scoring" in results and results["confidence_scoring"].get(
        "recommendations"
    ):
        recommendations.extend(results["confidence_scoring"]["recommendations"])

    if recommendations:
        console.print("[bold blue]💡 Recommendations:[/bold blue]")
        # Remove duplicates while preserving order
        seen = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recommendations.append(rec)

        for rec in unique_recommendations[:5]:  # Limit to top 5
            console.print(f"  • {rec}")
        console.print()


def _display_report_output(results: dict[str, Any]) -> None:
    """Display results in a comprehensive report format."""
    repo = results["repository"]
    analysis = results["analysis"]

    # Create comprehensive report
    report_content = f"""
# Repository Analysis Report

## 🔍 Repository: {repo["owner"]}/{repo["name"]}

**URL:** {repo["url"]}
**Description:** {repo["description"] or "No description provided"}
**Stars:** {repo["stars"]} | **Forks:** {repo["forks"]}

## 📊 Analysis Summary

{analysis["summary"]}

**Analysis Type: Evidence-Based**
**Context:** {analysis.get("context", "General").title()}

## ✅ Strengths
{chr(10).join(f"• {s}" for s in analysis["strengths"]) if analysis["strengths"] else "None identified"}

## ⚠️ Concerns
{chr(10).join(f"• {c}" for c in analysis["concerns"]) if analysis["concerns"] else "None identified"}

## 💡 Recommendations
{chr(10).join(f"• {r}" for r in analysis["recommendations"]) if analysis["recommendations"] else "No specific recommendations"}

---
*Generated by GitHub Profile Analyzer*
"""

    console.print(Syntax(report_content, "markdown", theme="monokai"))


def _generate_text_report(results: dict[str, Any]) -> str:
    """Generate a text report for saving."""
    repo = results["repository"]
    analysis = results["analysis"]
    classification = results["classification"]

    return f"""Repository Analysis Report
==========================

Repository: {repo["owner"]}/{repo["name"]}
URL: {repo["url"]}
Description: {repo["description"] or "No description provided"}
Stars: {repo["stars"]} | Forks: {repo["forks"]}
Classification: {classification["type"].title()} ({classification["confidence"]:.1%} confidence)

Analysis Summary:
{analysis["summary"]}

Analysis Type: Evidence-Based
Context: {analysis.get("context", "General").title()}

Strengths:
{chr(10).join(f"• {s}" for s in analysis["strengths"]) if analysis["strengths"] else "• None identified"}

Concerns:
{chr(10).join(f"• {c}" for c in analysis["concerns"]) if analysis["concerns"] else "• None identified"}

Recommendations:
{chr(10).join(f"• {r}" for r in analysis["recommendations"]) if analysis["recommendations"] else "• No specific recommendations"}

---
Generated by GitHub Profile Analyzer
"""


def _show_cost_summary(cost_tracker: CostTracker) -> None:
    """Display cost and usage summary."""
    console.print("\n[bold blue]💰 Cost Summary[/bold blue]")

    cost_table = Table(show_header=True)
    cost_table.add_column("Metric", style="bold")
    cost_table.add_column("Value", style="white")

    cost_table.add_row("Total Tokens", f"{cost_tracker.get_total_tokens():,}")
    cost_table.add_row("Estimated Cost", f"${cost_tracker.get_total_cost():.4f}")
    cost_table.add_row("API Calls", f"{cost_tracker.get_total_requests()}")

    console.print(cost_table)
