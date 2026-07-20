# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Batch repository analysis command implementation.

Handles the 'batch' CLI command for analyzing multiple GitHub repositories
from a file with parallel processing and comprehensive reporting.
"""

import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn
from rich.table import Table

from ...ai.analyzer import RepositoryAnalyzer
from ...ai.cost_tracker import CostTracker
from ...core.classifier import RepositoryClassifier
from ...data.github_fetcher import GitHubFetcher
from ...utils.helpers import validate_github_url
from ...utils.logging import get_logger

console = Console()
logger = get_logger(__name__)


def run_batch_analysis(
    repos_file: Any,
    output_dir: str = "./batch_results",
    context: Optional[str] = None,
    parallel_count: int = 3,
    continue_on_error: bool = False,
    verbose: bool = False,
) -> None:
    """
    Run batch analysis on multiple GitHub repositories.

    Args:
        repos_file: File object containing repository URLs (one per line)
        output_dir: Directory to save batch results
        context: Hiring context for all analyses
        parallel_count: Number of parallel analyses to run
        continue_on_error: Continue processing if individual repos fail
        verbose: Enable verbose output
    """
    try:
        # Read repository URLs from file
        repo_urls = _read_repository_urls(repos_file)

        if not repo_urls:
            console.print("[yellow]No valid repository URLs found in file[/yellow]")
            return

        console.print(
            f"[blue]Starting batch analysis of {len(repo_urls)} repositories[/blue]"
        )
        console.print(f"[dim]Parallel processing: {parallel_count} workers[/dim]")
        console.print(f"[dim]Output directory: {output_dir}[/dim]")

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Initialize shared components
        cost_tracker = CostTracker()

        # Run batch processing
        results = _process_repositories_parallel(
            repo_urls=repo_urls,
            output_dir=output_path,
            context=context,
            parallel_count=parallel_count,
            continue_on_error=continue_on_error,
            cost_tracker=cost_tracker,
            verbose=verbose,
        )

        # Generate batch summary
        _generate_batch_summary(results, output_path, cost_tracker)

        console.print("\n[green]✅ Batch analysis completed![/green]")
        console.print(f"[blue]Results saved to: {output_path.absolute()}[/blue]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Batch analysis cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Batch analysis failed: {e}")
        console.print(f"[red]Batch analysis failed: {e}[/red]")
        if verbose:
            raise
        sys.exit(1)


def _read_repository_urls(repos_file: Any) -> List[str]:
    """Read and validate repository URLs from file."""
    urls = []
    line_number = 0

    for line in repos_file:
        line_number += 1
        url = line.strip()

        # Skip empty lines and comments
        if not url or url.startswith("#"):
            continue

        # Validate URL
        if validate_github_url(url):
            urls.append(url)
        else:
            console.print(
                f"[yellow]Warning: Invalid URL on line {line_number}: {url}[/yellow]"
            )

    return urls


def _process_repositories_parallel(
    repo_urls: List[str],
    output_dir: Path,
    context: Optional[str],
    parallel_count: int,
    continue_on_error: bool,
    cost_tracker: CostTracker,
    verbose: bool,
) -> List[Dict[str, Any]]:
    """Process repositories in parallel with progress tracking."""

    results = []
    failed_repos: List[Dict[str, str]] = []

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        # Create progress task
        task = progress.add_task(
            f"Processing {len(repo_urls)} repositories...", total=len(repo_urls)
        )

        # Process repositories using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=parallel_count) as executor:
            # Submit all tasks
            future_to_url = {
                executor.submit(
                    _analyze_single_repository, url, context, cost_tracker, verbose
                ): url
                for url in repo_urls
            }

            # Process completed tasks
            for future in as_completed(future_to_url):
                url = future_to_url[future]

                try:
                    result = future.result()
                    if result:
                        # Save individual result
                        _save_individual_result(result, output_dir)
                        results.append(result)

                        # Update progress with success
                        progress.update(
                            task,
                            advance=1,
                            description=f"✅ {len(results)} completed, {len(failed_repos)} failed",
                        )
                    else:
                        failed_repos.append(
                            {"url": url, "error": "Analysis returned no results"}
                        )
                        if not continue_on_error:
                            console.print(
                                f"[red]Failed to analyze {url}, stopping batch processing[/red]"
                            )
                            break
                        progress.update(
                            task,
                            advance=1,
                            description=f"✅ {len(results)} completed, {len(failed_repos)} failed",
                        )

                except Exception as e:
                    failed_repos.append({"url": url, "error": str(e)})

                    if continue_on_error:
                        progress.update(
                            task,
                            advance=1,
                            description=f"✅ {len(results)} completed, {len(failed_repos)} failed",
                        )
                        if verbose:
                            console.print(f"[red]Error analyzing {url}: {e}[/red]")
                    else:
                        console.print(f"[red]Failed to analyze {url}: {e}[/red]")
                        console.print(
                            "[red]Stopping batch processing (use --continue-on-error to continue)[/red]"
                        )
                        break

    # Report failed repositories
    if failed_repos:
        console.print(f"\n[yellow]⚠️  {len(failed_repos)} repositories failed:[/yellow]")
        for failed in failed_repos:
            console.print(f"  • {failed['url']}: {failed['error']}")

    return results


def _analyze_single_repository(
    repo_url: str, context: Optional[str], cost_tracker: CostTracker, verbose: bool
) -> Optional[Dict[str, Any]]:
    """Analyze a single repository (called in parallel)."""
    try:
        # Initialize components for this thread
        fetcher = GitHubFetcher()
        classifier = RepositoryClassifier()
        analyzer = RepositoryAnalyzer(cost_tracker=cost_tracker)

        # Fetch repository data
        repo_data = fetcher.fetch_repository_data(repo_url)

        # Classify repository
        classification = classifier.classify_repository(repo_data)

        # Generate AI analysis
        analysis = analyzer.analyze_repository(
            repo_data=repo_data, classification=classification, context=context
        )

        # Return results
        return {
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
            "classification": {
                "method": classification.method.value,
                "template_category": (
                    classification.template_category.value
                    if classification.template_category
                    else None
                ),
                "reasoning": classification.reasoning,
                "cost_estimate": classification.cost_estimate,
            },
            "analysis": {
                "summary": analysis.summary,
                "strengths": analysis.strengths,
                "concerns": analysis.concerns,
                "recommendations": analysis.recommendations,
                # Evidence-based approach - no scores
                "context": analysis.context,
            },
            "metrics": {
                "total_commits": repo_data.metrics.total_commits,
                "unique_contributors": repo_data.metrics.unique_contributors,
                "lines_of_code": repo_data.metrics.lines_of_code,
                "test_coverage_estimate": repo_data.metrics.test_coverage_estimate,
                "documentation_presence": repo_data.metrics.documentation_presence,
                "days_since_last_commit": repo_data.metrics.days_since_last_commit,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        if verbose:
            logger.error(f"Error analyzing {repo_url}: {e}")
        raise


def _save_individual_result(result: Dict[str, Any], output_dir: Path) -> None:
    """Save individual repository analysis result."""
    repo_name = result["repository"]["name"]
    owner = result["repository"]["owner"]

    # Create safe filename
    safe_name = f"{owner}_{repo_name}".replace("/", "_").replace(" ", "_")
    filename = f"{safe_name}_analysis.json"

    # Save result
    output_file = output_dir / filename
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2, default=str)


def _generate_batch_summary(
    results: List[Dict[str, Any]], output_dir: Path, cost_tracker: CostTracker
) -> None:
    """Generate comprehensive batch analysis summary."""

    if not results:
        console.print("[yellow]No results to summarize[/yellow]")
        return

    # Calculate summary statistics
    total_repos = len(results)

    # Evidence-based pattern distribution (no scores)

    # Repository types
    repo_types: Dict[str, int] = {}
    for result in results:
        repo_type = result["classification"]["type"]
        repo_types[repo_type] = repo_types.get(repo_type, 0) + 1

    # Languages
    languages: Dict[str, int] = {}
    for result in results:
        for lang in result["repository"]["languages"].keys():
            languages[lang] = languages.get(lang, 0) + 1

    # Create summary report
    summary = {
        "batch_summary": {
            "total_repositories": total_repos,
            "analysis_type": "evidence-based",
            "completion_time": datetime.utcnow().isoformat(),
        },
        "repository_types": repo_types,
        "top_languages": dict(
            sorted(languages.items(), key=lambda x: x[1], reverse=True)[:10]
        ),
        "cost_summary": {
            "total_tokens": cost_tracker.get_total_tokens(),
            "total_cost": cost_tracker.get_total_cost(),
            "total_requests": cost_tracker.get_total_requests(),
        },
        "detailed_results": results,
    }

    # Save summary to file
    summary_file = output_dir / "batch_summary.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    # Display summary table
    _display_batch_summary_table(summary)


def _display_batch_summary_table(summary: Dict[str, Any]) -> None:
    """Display batch summary in a formatted table."""
    console.print("\n[bold blue]📊 Batch Analysis Summary[/bold blue]")

    # Overview table
    overview_table = Table(title="Overview", show_header=True)
    overview_table.add_column("Metric", style="bold")
    overview_table.add_column("Value", style="white")

    batch_info = summary["batch_summary"]
    overview_table.add_row("Total Repositories", str(batch_info["total_repositories"]))
    overview_table.add_row(
        "Analysis Type", batch_info.get("analysis_type", "evidence-based")
    )
    overview_table.add_row("Completion Time", batch_info["completion_time"][:19])

    console.print(overview_table)
    console.print()

    # Evidence-based analysis summary
    console.print("[bold green]📈 Evidence-Based Analysis Complete[/bold green]")
    console.print(f"  ✅ Analyzed {batch_info['total_repositories']} repositories")
    console.print("  📊 Generated evidence patterns for each repository")
    console.print()

    # Repository types
    if summary["repository_types"]:
        console.print("[bold blue]📂 Repository Types:[/bold blue]")
        for repo_type, count in summary["repository_types"].items():
            console.print(f"  • {repo_type.title()}: {count}")
        console.print()

    # Top languages
    if summary["top_languages"]:
        console.print("[bold purple]🔤 Top Languages:[/bold purple]")
        for lang, count in list(summary["top_languages"].items())[:5]:
            console.print(f"  • {lang}: {count}")
        console.print()

    # Cost summary
    cost_info = summary["cost_summary"]
    console.print("[bold yellow]💰 Cost Summary:[/bold yellow]")
    console.print(f"  • Total Tokens: {cost_info['total_tokens']:,}")
    console.print(f"  • Estimated Cost: ${cost_info['total_cost']:.4f}")
    console.print(f"  • API Requests: {cost_info['total_requests']}")
    console.print()
