# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Cost reporting command implementation.

Handles the 'cost-report' CLI command for generating usage and cost reports
with various time periods and output formats.
"""

import csv
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ...ai.cost_tracker import CostTracker
from ...utils.logging import get_logger

console = Console()
logger = get_logger(__name__)


def generate_report(
    period: str = "week",
    output_format: str = "table",
    export_path: Optional[str] = None,
    verbose: bool = False,
) -> None:
    """
    Generate cost and usage reports.

    Args:
        period: Reporting period (day, week, month, all)
        output_format: Output format (table, json, csv)
        export_path: Path to export report
        verbose: Enable verbose output
    """
    try:
        console.print(f"[blue]📊 Generating {period} cost report...[/blue]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=not verbose,
        ) as progress:
            task = progress.add_task("Loading cost data...", total=None)

            # Load cost tracking data
            cost_tracker = CostTracker()
            cost_data = _load_cost_data(period, verbose)

            progress.update(task, description="Generating report...")

            # Generate report
            report = _generate_cost_report(cost_data, period, cost_tracker)

            progress.update(task, description="✅ Report generated")

        # Output report in requested format
        _output_report(report, output_format, export_path, period)

    except KeyboardInterrupt:
        console.print("\n[yellow]Report generation cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        console.print(f"[red]Report generation failed: {e}[/red]")
        if verbose:
            raise
        sys.exit(1)


def _load_cost_data(period: str, verbose: bool) -> Dict[str, Any]:
    """Load cost tracking data for the specified period."""

    # Calculate date range based on period
    now = datetime.utcnow().replace(tzinfo=None)  # Remove timezone for consistency

    if period == "day":
        start_date = now - timedelta(days=1)
    elif period == "week":
        start_date = now - timedelta(weeks=1)
    elif period == "month":
        start_date = now - timedelta(days=30)
    else:  # "all"
        start_date = datetime(2020, 1, 1)  # Far in the past

    # Load real cost tracking data
    cost_tracker = CostTracker()

    # Get current session data
    current_session = {
        "total_tokens": cost_tracker.get_total_tokens(),
        "total_cost": cost_tracker.get_total_cost(),
        "total_requests": cost_tracker.get_total_requests(),
        "usage_by_model": cost_tracker.get_usage_by_model(),
    }

    # Load historical data from persistent storage
    historical_records: List[Any] = []
    daily_breakdown: List[Dict[str, Any]] = []

    if cost_tracker.persistence_enabled and cost_tracker.cost_storage:
        try:
            if verbose:
                console.print(
                    "[dim]Loading historical data from persistent storage...[/dim]"
                )

            # Convert dates to timezone-aware for storage queries
            from datetime import timezone as tz

            start_date_tz = start_date.replace(tzinfo=tz.utc)
            now_tz = now.replace(tzinfo=tz.utc)

            # Get historical cost records
            historical_records = cost_tracker.get_historical_data(start_date_tz, now_tz)

            # Generate daily breakdown from historical records
            daily_breakdown = _process_historical_daily_breakdown(
                historical_records, start_date, now
            )

            if verbose:
                console.print(
                    f"[dim]Loaded {len(historical_records)} historical records[/dim]"
                )

        except Exception as e:
            if verbose:
                console.print(
                    f"[yellow]Warning: Failed to load historical data: {e}[/yellow]"
                )
            # Fall back to sample data if storage fails
            historical_records = []
            daily_breakdown = []

    # If no historical data available, use sample data for demonstration
    if not historical_records:
        if verbose:
            console.print("[dim]No historical data available, using sample data[/dim]")
        historical_records = _generate_sample_historical_data(period, start_date, now)
        daily_breakdown = _generate_daily_breakdown(period, start_date, now)

    cost_data = {
        "period": period,
        "start_date": start_date.isoformat(),
        "end_date": now.isoformat(),
        "current_session": current_session,
        "historical_records": historical_records,
        "daily_breakdown": daily_breakdown,
        "persistence_enabled": cost_tracker.persistence_enabled,
        "storage_status": (
            cost_tracker.get_storage_status()
            if cost_tracker.persistence_enabled
            else None
        ),
    }

    return cost_data


def _generate_sample_historical_data(
    period: str, start_date: datetime, end_date: datetime
) -> List[Dict[str, Any]]:
    """Generate sample historical data for demonstration."""

    sessions = []
    current_date = start_date
    session_id = 1

    # Generate sample sessions based on period
    if period == "day":
        num_sessions = 3
    elif period == "week":
        num_sessions = 10
    elif period == "month":
        num_sessions = 25
    else:  # "all"
        num_sessions = 50

    for i in range(num_sessions):
        # Simulate session data
        session = {
            "session_id": f"session_{session_id:03d}",
            "timestamp": (current_date + timedelta(hours=i * 2)).isoformat(),
            "repositories_analyzed": 1 + (i % 3),  # 1-3 repos per session
            "tokens_used": 1500 + (i * 200),
            "cost": (1500 + (i * 200)) * 0.000003,  # Approximate cost per token
            "model": "claude-3-haiku" if i % 3 == 0 else "claude-3-sonnet",
        }
        sessions.append(session)
        session_id += 1

        # Advance date
        if period == "day":
            current_date += timedelta(hours=8)
        elif period == "week":
            current_date += timedelta(hours=16)
        else:
            current_date += timedelta(days=1)

    return sessions


def _process_historical_daily_breakdown(
    historical_records: List[Any], start_date: datetime, end_date: datetime
) -> List[Dict[str, Any]]:
    """Process historical records to create daily breakdown."""

    daily_data: Dict[str, Dict[str, Any]] = {}

    for record in historical_records:
        try:
            # Parse timestamp from record
            from datetime import datetime

            record_date = datetime.fromisoformat(
                record.timestamp.replace("Z", "+00:00")
            )
            date_key = record_date.strftime("%Y-%m-%d")

            if date_key not in daily_data:
                daily_data[date_key] = {
                    "date": date_key,
                    "total_tokens": 0,
                    "total_input_tokens": 0,
                    "total_output_tokens": 0,
                    "total_cost": 0.0,
                    "api_requests": 0,
                    "operations": 0,
                    "models_used": set(),
                }

            # Aggregate data for this day
            daily_data[date_key]["total_tokens"] += (
                record.input_tokens + record.output_tokens
            )
            daily_data[date_key]["total_input_tokens"] += record.input_tokens
            daily_data[date_key]["total_output_tokens"] += record.output_tokens
            daily_data[date_key]["total_cost"] += record.cost
            daily_data[date_key]["operations"] += 1
            daily_data[date_key]["models_used"].add(record.model)

            # Count API requests (assume 1 request per operation for now)
            daily_data[date_key]["api_requests"] += 1

        except (ValueError, KeyError, AttributeError) as e:
            # Skip invalid records - log for debugging
            logger.debug(f"Skipping invalid record: {e}")
            continue

    # Convert sets to lists and sort by date
    result = []
    for date_key in sorted(daily_data.keys()):
        day_data = daily_data[date_key]
        day_data["models_used"] = list(day_data["models_used"])
        result.append(day_data)

    return result


def _generate_daily_breakdown(
    period: str, start_date: datetime, end_date: datetime
) -> List[Dict[str, Any]]:
    """Generate daily breakdown of usage."""

    daily_data: List[Dict[str, Any]] = []
    current_date = start_date

    while current_date < end_date:
        # Simulate daily usage
        daily_usage = {
            "date": current_date.strftime("%Y-%m-%d"),
            "repositories_analyzed": 2 + (len(daily_data) % 5),  # 2-6 repos per day
            "total_tokens": 3000 + (len(daily_data) * 500),
            "total_cost": (3000 + (len(daily_data) * 500)) * 0.000003,
            "api_requests": 10 + (len(daily_data) % 8),
        }
        daily_data.append(daily_usage)
        current_date += timedelta(days=1)

    return daily_data


def _generate_cost_report(
    cost_data: Dict[str, Any], period: str, cost_tracker: CostTracker
) -> Dict[str, Any]:
    """Generate comprehensive cost report."""

    current_session = cost_data["current_session"]
    historical_records = cost_data.get("historical_records", [])
    daily_breakdown = cost_data.get("daily_breakdown", [])

    # Handle both CostRecord objects and dict format for backward compatibility
    def get_record_value(record: Any, field: str) -> Any:
        if hasattr(record, field):
            return getattr(record, field)
        return record.get(field, 0)

    # Calculate historical totals from real records
    if historical_records and hasattr(historical_records[0], "cost"):
        # Real CostRecord objects
        total_historical_tokens = sum(
            record.input_tokens + record.output_tokens for record in historical_records
        )
        total_historical_cost = sum(record.cost for record in historical_records)
        total_historical_operations = len(historical_records)
    else:
        # Fallback to sample data format
        total_historical_tokens = sum(
            get_record_value(record, "tokens_used") for record in historical_records
        )
        total_historical_cost = sum(
            get_record_value(record, "cost") for record in historical_records
        )
        total_historical_operations = len(historical_records)

    # Current session totals
    current_tokens = current_session["total_tokens"]
    current_cost = current_session["total_cost"]
    current_requests = current_session["total_requests"]

    # Combined totals
    grand_total_tokens = total_historical_tokens + current_tokens
    grand_total_cost = total_historical_cost + current_cost
    total_operations = total_historical_operations + current_requests

    # Calculate averages (use operations as proxy for repos)
    avg_tokens_per_operation = grand_total_tokens / max(total_operations, 1)
    avg_cost_per_operation = grand_total_cost / max(total_operations, 1)

    # Model usage breakdown from historical records
    model_usage = {}

    if historical_records:
        for record in historical_records:
            if hasattr(record, "model"):
                # Real CostRecord object
                model = record.model
                tokens = record.input_tokens + record.output_tokens
                cost = record.cost
            else:
                # Sample data format
                model = get_record_value(record, "model") or "unknown"
                tokens = get_record_value(record, "tokens_used")
                cost = get_record_value(record, "cost")

            if model not in model_usage:
                model_usage[model] = {
                    "tokens": 0,
                    "cost": 0.0,
                    "requests": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                }

            model_usage[model]["tokens"] += tokens
            model_usage[model]["cost"] += cost
            model_usage[model]["requests"] += 1

            if hasattr(record, "input_tokens"):
                model_usage[model]["input_tokens"] += record.input_tokens
                model_usage[model]["output_tokens"] += record.output_tokens

    # Add current session model usage
    current_model_usage = current_session.get("usage_by_model", {})
    for model, tokens in current_model_usage.items():
        if model not in model_usage:
            model_usage[model] = {
                "tokens": 0,
                "cost": 0.0,
                "requests": 0,
                "input_tokens": 0,
                "output_tokens": 0,
            }
        model_usage[model]["tokens"] += tokens
        # Estimate cost for current session if not available
        estimated_cost = (
            cost_tracker.calculate_cost(model, tokens // 2, tokens // 2)
            if tokens > 0
            else 0
        )
        model_usage[model]["cost"] += estimated_cost
        model_usage[model]["requests"] += 1

    report = {
        "report_metadata": {
            "period": period,
            "start_date": cost_data["start_date"],
            "end_date": cost_data["end_date"],
            "generated_at": datetime.utcnow().isoformat(),
            "persistence_enabled": cost_data.get("persistence_enabled", False),
            "data_source": (
                "persistent_storage"
                if cost_data.get("persistence_enabled") and historical_records
                else "sample_data"
            ),
        },
        "summary": {
            "total_operations": total_operations,
            "total_tokens_used": grand_total_tokens,
            "total_cost": grand_total_cost,
            "average_tokens_per_operation": round(avg_tokens_per_operation),
            "average_cost_per_operation": round(avg_cost_per_operation, 6),
            "historical_records": len(historical_records),
            "current_session_active": current_tokens > 0,
            "total_input_tokens": sum(
                usage.get("input_tokens", 0) for usage in model_usage.values()
            ),
            "total_output_tokens": sum(
                usage.get("output_tokens", 0) for usage in model_usage.values()
            ),
        },
        "storage_status": cost_data.get("storage_status"),
        "current_session": current_session,
        "model_breakdown": model_usage,
        "daily_breakdown": (
            daily_breakdown[-7:] if len(daily_breakdown) > 7 else daily_breakdown
        ),  # Last 7 days
        "historical_records": (
            [_format_record_for_display(record) for record in historical_records[-10:]]
            if len(historical_records) > 10
            else [_format_record_for_display(record) for record in historical_records]
        ),  # Last 10 records
    }

    return report


def _format_record_for_display(record: Any) -> Dict[str, Any]:
    """Format a cost record for display purposes."""
    if hasattr(record, "timestamp"):
        # Real CostRecord object
        return {
            "timestamp": record.timestamp,
            "model": record.model,
            "operation": record.operation,
            "input_tokens": record.input_tokens,
            "output_tokens": record.output_tokens,
            "total_tokens": record.input_tokens + record.output_tokens,
            "cost": record.cost,
            "metadata": record.metadata,
        }
    else:
        # Sample data format - already formatted
        return dict(record)


def _output_report(
    report: Dict[str, Any], output_format: str, export_path: Optional[str], period: str
) -> None:
    """Output the report in the specified format."""

    if output_format == "json":
        output = json.dumps(report, indent=2, default=str)
        if export_path:
            Path(export_path).write_text(output)
            console.print(f"[green]Report exported to {export_path}[/green]")
        else:
            console.print(output)

    elif output_format == "csv":
        if export_path:
            _export_csv_report(report, export_path)
            console.print(f"[green]Report exported to {export_path}[/green]")
        else:
            console.print("[yellow]CSV format requires --export option[/yellow]")
            _display_table_report(report, period)

    else:  # table format
        _display_table_report(report, period)
        if export_path:
            # Save as JSON when table format is used with export
            json_output = json.dumps(report, indent=2, default=str)
            Path(export_path).write_text(json_output)
            console.print(f"[green]Report saved to {export_path} (JSON format)[/green]")


def _display_table_report(report: Dict[str, Any], period: str) -> None:
    """Display the report as formatted tables."""

    summary = report["summary"]
    metadata = report["report_metadata"]

    # Summary Table
    console.print(f"\n[bold blue]💰 Cost Report - {period.title()} Summary[/bold blue]")
    console.print(
        f"[dim]Period: {metadata['start_date'][:10]} to {metadata['end_date'][:10]}[/dim]"
    )

    # Show data source
    data_source = metadata.get("data_source", "unknown")
    persistence_enabled = metadata.get("persistence_enabled", False)

    if persistence_enabled:
        if data_source == "persistent_storage":
            console.print("[dim]📂 Data source: Persistent storage[/dim]")
        else:
            console.print(
                "[dim]📂 Data source: Sample data (no historical records found)[/dim]"
            )
    else:
        console.print("[dim]📂 Data source: Sample data (persistence disabled)[/dim]")

    console.print()

    summary_table = Table(title="📊 Usage Summary", show_header=True)
    summary_table.add_column("Metric", style="bold")
    summary_table.add_column("Value", style="white")

    summary_table.add_row("Total Operations", f"{summary['total_operations']:,}")
    summary_table.add_row("Total Tokens Used", f"{summary['total_tokens_used']:,}")
    summary_table.add_row("Input Tokens", f"{summary.get('total_input_tokens', 0):,}")
    summary_table.add_row("Output Tokens", f"{summary.get('total_output_tokens', 0):,}")
    summary_table.add_row("Total Cost", f"${summary['total_cost']:.6f}")
    summary_table.add_row(
        "Avg Tokens/Operation", f"{summary['average_tokens_per_operation']:,}"
    )
    summary_table.add_row(
        "Avg Cost/Operation", f"${summary['average_cost_per_operation']:.6f}"
    )
    summary_table.add_row("Historical Records", f"{summary['historical_records']:,}")

    console.print(summary_table)
    console.print()

    # Model Breakdown
    if report["model_breakdown"]:
        model_table = Table(title="🤖 Model Usage Breakdown", show_header=True)
        model_table.add_column("Model", style="bold blue")
        model_table.add_column("Total Tokens", style="white")
        model_table.add_column("Input", style="cyan")
        model_table.add_column("Output", style="yellow")
        model_table.add_column("Cost", style="white")
        model_table.add_column("Operations", style="white")

        for model, usage in report["model_breakdown"].items():
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)

            model_table.add_row(
                model,
                f"{usage['tokens']:,}",
                f"{input_tokens:,}" if input_tokens > 0 else "-",
                f"{output_tokens:,}" if output_tokens > 0 else "-",
                f"${usage['cost']:.6f}",
                f"{usage['requests']:,}",
            )

        console.print(model_table)
        console.print()

    # Daily Breakdown (if available)
    if report["daily_breakdown"]:
        daily_table = Table(title="📅 Daily Usage (Last 7 Days)", show_header=True)
        daily_table.add_column("Date", style="bold")
        daily_table.add_column("Operations", style="white")
        daily_table.add_column("Tokens", style="white")
        daily_table.add_column("Cost", style="white")
        daily_table.add_column("Models", style="cyan")

        for day in report["daily_breakdown"]:
            operations = day.get("operations", day.get("repositories_analyzed", 0))
            models_used = day.get("models_used", [])
            models_str = ", ".join(models_used[:2]) if models_used else "-"
            if len(models_used) > 2:
                models_str += f" +{len(models_used) - 2}"

            daily_table.add_row(
                day["date"],
                f"{operations:,}",
                f"{day['total_tokens']:,}",
                f"${day['total_cost']:.6f}",
                models_str,
            )

        console.print(daily_table)
        console.print()

    # Storage Status (if available and enabled)
    storage_status = report.get("storage_status")
    if storage_status and metadata.get("persistence_enabled"):
        console.print("[bold green]💾 Storage Status:[/bold green]")
        console.print(
            f"  • Storage Path: {storage_status.get('storage_path', 'unknown')}"
        )
        console.print(
            f"  • Records Today: {storage_status.get('today_stored_records', 0):,}"
        )
        console.print(
            f"  • Cost Today: ${storage_status.get('today_stored_cost', 0):.6f}"
        )
        console.print(
            f"  • Current Session: {storage_status.get('current_session_records', 0):,} records"
        )
        if storage_status.get("storage_error"):
            console.print(
                f"  • [yellow]Warning: {storage_status['storage_error']}[/yellow]"
            )
        console.print()

    # Current Session Info
    current = report["current_session"]
    if current["total_tokens"] > 0:
        console.print("[bold green]🔄 Current Session:[/bold green]")
        console.print(f"  • Tokens Used: {current['total_tokens']:,}")
        console.print(f"  • Estimated Cost: ${current['total_cost']:.4f}")
        console.print(f"  • API Requests: {current['total_requests']:,}")
        console.print()


def _export_csv_report(report: Dict[str, Any], export_path: str) -> None:
    """Export report data to CSV format."""

    with open(export_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)

        # Write summary section
        writer.writerow(["Cost Report Summary"])
        writer.writerow(["Metric", "Value"])

        summary = report["summary"]
        writer.writerow(["Total Repositories", summary["total_repositories_analyzed"]])
        writer.writerow(["Total Tokens", summary["total_tokens_used"]])
        writer.writerow(["Total Cost", f"${summary['total_cost']:.4f}"])
        writer.writerow(["Average Tokens per Repo", summary["average_tokens_per_repo"]])
        writer.writerow(
            ["Average Cost per Repo", f"${summary['average_cost_per_repo']:.4f}"]
        )
        writer.writerow([])  # Empty row

        # Write daily breakdown
        if report["daily_breakdown"]:
            writer.writerow(["Daily Breakdown"])
            writer.writerow(["Date", "Repositories", "Tokens", "Cost"])

            for day in report["daily_breakdown"]:
                writer.writerow(
                    [
                        day["date"],
                        day["repositories_analyzed"],
                        day["total_tokens"],
                        f"${day['total_cost']:.4f}",
                    ]
                )
            writer.writerow([])  # Empty row

        # Write model breakdown
        if report["model_breakdown"]:
            writer.writerow(["Model Breakdown"])
            writer.writerow(["Model", "Tokens", "Cost", "Requests"])

            for model, usage in report["model_breakdown"].items():
                writer.writerow(
                    [model, usage["tokens"], f"${usage['cost']:.4f}", usage["requests"]]
                )
