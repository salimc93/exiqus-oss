# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Main CLI entry point for Exiqus.

Provides command-line interface for repository analysis, batch processing,
API testing, and cost reporting.
"""

import sys
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel

from ..utils.logging import get_logger

# from .commands import admin  # Imported dynamically when needed, analyze, batch, cost_report

console = Console()
logger = get_logger(__name__)


@click.group(name="exiqus")
@click.version_option(version="1.0.0", prog_name="Exiqus")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option(
    "--config-file",
    "-c",
    type=click.Path(exists=True),
    help="Path to configuration file",
)
@click.pass_context
def cli(ctx: click.Context, verbose: bool, config_file: Optional[str]) -> None:
    """
    🚀 Exiqus - AI-Powered Developer Assessment Platform

    Transform technical recruitment with intelligent, context-aware
    analysis of GitHub repositories.

    Analyze repositories, run batch processing, test API connectivity,
    and track usage costs with AI-powered insights.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)

    # Store configuration in context
    ctx.obj["verbose"] = verbose
    ctx.obj["config_file"] = config_file

    # Display banner in non-verbose mode
    if not verbose:
        console.print(
            Panel.fit(
                "[bold blue]🚀 Exiqus[/bold blue]\n"
                "[dim]AI-Powered Developer Assessment Platform[/dim]",
                border_style="blue",
            )
        )


@cli.command()
@click.argument("repo_url")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["json", "yaml", "table", "report"]),
    default="table",
    help="Output format",
)
@click.option(
    "--context",
    "-x",
    type=click.Choice(["startup", "enterprise", "agency", "freelance"]),
    help="Hiring context for analysis",
)
@click.option("--save", "-s", type=click.Path(), help="Save analysis results to file")
@click.pass_context
def analyze_cmd(
    ctx: click.Context,
    repo_url: str,
    output: str,
    context: Optional[str],
    save: Optional[str],
) -> None:
    """
    Analyze a single GitHub repository.

    REPO_URL: GitHub repository URL to analyze

    Examples:
      exiqus analyze https://github.com/user/repo
      exiqus analyze https://github.com/user/repo --context startup
      exiqus analyze https://github.com/user/repo -o json -s results.json
    """
    # TODO: Implement analyze command
    # analyze.run_analysis(
    #     repo_url=repo_url,
    #     output_format=output,
    #     context=context,
    #     save_path=save,
    #     verbose=ctx.obj["verbose"],
    # )
    console.print("[red]Analyze command not yet implemented[/red]")


@cli.command()
@click.argument("repos_file", type=click.File("r"))
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(),
    default="./batch_results",
    help="Directory to save batch results",
)
@click.option(
    "--context",
    "-x",
    type=click.Choice(["startup", "enterprise", "agency", "freelance"]),
    help="Hiring context for analysis",
)
@click.option(
    "--parallel", "-p", type=int, default=3, help="Number of parallel analyses"
)
@click.option(
    "--continue-on-error",
    is_flag=True,
    help="Continue processing if individual repositories fail",
)
@click.pass_context
def batch_cmd(
    ctx: click.Context,
    repos_file: click.File,
    output_dir: str,
    context: Optional[str],
    parallel: int,
    continue_on_error: bool,
) -> None:
    """
    Analyze multiple repositories from a file.

    REPOS_FILE: Text file with one GitHub URL per line

    Examples:
      exiqus batch repos.txt
      exiqus batch repos.txt --parallel 5 --context enterprise
      exiqus batch repos.txt -o results/ --continue-on-error
    """
    # TODO: Implement batch command
    # batch.run_batch_analysis(
    #     repos_file=repos_file,
    #     output_dir=output_dir,
    #     context=context,
    #     parallel_count=parallel,
    #     continue_on_error=continue_on_error,
    #     verbose=ctx.obj["verbose"],
    # )
    console.print("[red]Batch command not yet implemented[/red]")


# test_apis command removed - module not implemented


@cli.command()
@click.option(
    "--period",
    "-p",
    type=click.Choice(["day", "week", "month", "all"]),
    default="week",
    help="Reporting period",
)
@click.option(
    "--format",
    "-",
    type=click.Choice(["table", "json", "csv"]),
    default="table",
    help="Output format",
)
@click.option("--export", "-e", type=click.Path(), help="Export report to file")
@click.pass_context
def cost_report_cmd(
    ctx: click.Context, period: str, format: str, export: Optional[str]
) -> None:
    """
    Generate cost and usage reports.

    Examples:
      exiqus cost-report
      exiqus cost-report --period month
      exiqus cost-report --format json --export costs.json
    """
    # TODO: Implement cost-report command
    # cost_report.generate_report(
    #     period=period,
    #     output_format=format,
    #     export_path=export,
    #     verbose=ctx.obj["verbose"],
    # )
    console.print("[red]Cost-report command not yet implemented[/red]")


@cli.group()
@click.pass_context
def admin_group(ctx: click.Context) -> None:
    """
    Administrative commands for user and system management.

    These commands are intended for administrators to manage users,
    set custom repository limits, and monitor system health.
    """
    pass


@admin_group.command("set-repo-limit")
@click.argument("email")
@click.argument("limit_mb", type=int)
@click.option(
    "--force", "-", is_flag=True, help="Force update for non-enterprise users"
)
@click.pass_context
def admin_set_repo_limit_cmd(
    ctx: click.Context, email: str, limit_mb: int, force: bool
) -> None:
    """
    Set custom repository size limit for a user.

    EMAIL: User email address
    LIMIT_MB: Size limit in MB (1-10240)

    Examples:
      exiqus admin set-repo-limit enterprise@company.com 5120
      exiqus admin set-repo-limit user@company.com 2048 --force
    """
    try:
        # Import here to avoid dependency issues
        import typer

        from .commands.admin import set_repo_limit

        # Call the typer command directly with captured arguments
        try:
            set_repo_limit(email=email, limit_mb=limit_mb, force=force)
        except typer.Exit as e:
            sys.exit(e.exit_code)
    except ImportError:
        console.print("[red]Error: Admin commands require typer package[/red]")
        sys.exit(1)


@admin_group.command("get-repo-limit")
@click.argument("email")
@click.pass_context
def admin_get_repo_limit_cmd(ctx: click.Context, email: str) -> None:
    """
    Get current repository size limit for a user.

    EMAIL: User email address
    """
    try:
        import typer

        from .commands.admin import get_repo_limit

        try:
            get_repo_limit(email=email)
        except typer.Exit as e:
            sys.exit(e.exit_code)
    except ImportError:
        console.print("[red]Error: Admin commands require typer package[/red]")
        sys.exit(1)


@admin_group.command("user-info")
@click.argument("email")
@click.pass_context
def admin_user_info_cmd(ctx: click.Context, email: str) -> None:
    """
    Display comprehensive information about a user.

    EMAIL: User email address
    """
    try:
        import typer

        from .commands.admin import user_info

        try:
            user_info(email=email)
        except typer.Exit as e:
            sys.exit(e.exit_code)
    except ImportError:
        console.print("[red]Error: Admin commands require typer package[/red]")
        sys.exit(1)


def main() -> None:
    """Main entry point for the CLI application."""
    try:
        cli(obj={})
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        if "--verbose" in sys.argv or "-v" in sys.argv:
            console.print(f"[red]Error: {e}[/red]")
            raise
        else:
            console.print(f"[red]Error: {e}[/red]")
            console.print("[dim]Use --verbose for more details[/dim]")
            sys.exit(1)


if __name__ == "__main__":
    main()
