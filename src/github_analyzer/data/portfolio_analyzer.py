# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Portfolio Analyzer - Orchestrates portfolio analysis workflow.

This module coordinates the entire portfolio analysis pipeline:
1. Fetches repository data via GraphQL
2. Extracts evidence patterns from repos
3. Generates AI insights from evidence
4. Returns structured analysis results

Follows validation script approach - evidence-based, NO SCORES.
"""

import time
from typing import Any, Dict, List

from ..ai.portfolio_insights_generator import PortfolioInsightsGenerator
from ..utils.logging import get_logger
from .portfolio_evidence_extractor import PortfolioEvidenceExtractor
from .portfolio_fetcher import PortfolioFetcher
from .portfolio_models import PortfolioMetadata, RepoData

logger = get_logger(__name__)


class PortfolioAnalyzer:
    """Orchestrates portfolio analysis workflow (evidence-based, NO SCORES)."""

    def __init__(self, github_token: str, anthropic_api_key: str) -> None:
        """
        Initialize portfolio analyzer.

        Args:
            github_token: GitHub API token for authentication
            anthropic_api_key: Anthropic API key for AI insights
        """
        self.fetcher = PortfolioFetcher(github_token)
        self.evidence_extractor = PortfolioEvidenceExtractor()
        self.insights_generator = PortfolioInsightsGenerator(anthropic_api_key)

    def analyze_portfolio(
        self,
        username: str,
        context: str = "enterprise",
        tier: str = "professional",
        max_repos: int = 100,
        role: str = "senior",
    ) -> Dict[str, Any]:
        """
        Analyze a developer's GitHub portfolio.

        Args:
            username: GitHub username to analyze
            context: Hiring context (startup/enterprise/agency/open_source)
            tier: User subscription tier (determines AI model)
            max_repos: Maximum number of repos to analyze
            role: Role level for interview questions (junior, mid, senior)

        Returns:
            Dictionary with complete portfolio analysis (NO SCORES)
        """
        logger.info(
            f"Starting portfolio analysis for {username} "
            f"(context: {context}, tier: {tier})"
        )

        analysis_start = time.time()

        try:
            # Step 1: Fetch repository data via GraphQL
            logger.info("Step 1/4: Fetching repository data via GraphQL...")
            fetch_start = time.time()
            fetch_result = self.fetcher.fetch_user_portfolio(username, max_repos)
            fetch_time = time.time() - fetch_start

            repos = fetch_result.repos

            # Calculate portfolio span from ALL repos (including skipped) for accurate timeline
            all_dates = fetch_result.all_repos_dates
            oldest_repo_date = min(all_dates) if all_dates else ""
            newest_repo_date = max(all_dates) if all_dates else ""

            # Build metadata from fetch result
            metadata = PortfolioMetadata(
                total_public_repos=fetch_result.total_public_repos,
                repos_analyzed=fetch_result.repos_fetched,
                repos_skipped=fetch_result.repos_skipped,
                skip_counts=fetch_result.skip_reasons,
                skipped_repos=fetch_result.skipped_repos,
                analyzed_repos=[r.name for r in repos],
                oldest_repo=oldest_repo_date,
                newest_repo=newest_repo_date,
                timeline_gaps=0,  # Will be calculated later
                tokens=0,  # Will be set after AI call
                cost=0.0,  # Will be set after AI call
            )

            logger.info(
                f"Fetched {len(repos)} repos (skipped {metadata.repos_skipped}) "
                f"in {fetch_time:.2f}s, {fetch_result.api_calls_used} API calls"
            )

            # Step 2: Extract evidence patterns from repos
            logger.info("Step 2/4: Extracting evidence patterns from repos...")
            evidence_start = time.time()
            evidence = self.evidence_extractor.extract_all_evidence(repos, username)
            evidence_time = time.time() - evidence_start

            logger.info(
                f"Extracted evidence in {evidence_time:.2f}s: "
                f"{len(evidence.get('portfolio_evolution_periods', []))} periods, "
                f"{len(evidence.get('substantial_repos_structured', []))} substantial repos"
            )

            # Step 3: Generate AI insights from evidence
            logger.info("Step 3/4: Generating AI insights from evidence...")
            insights_start = time.time()
            insights_result = self.insights_generator.generate_insights(
                username=username,
                evidence=evidence,
                metadata=metadata,
                repos=repos,
                context=context,
                tier=tier,
                role=role,
            )
            insights_time = time.time() - insights_start

            if insights_result["success"]:
                logger.info(
                    f"AI insights generated in {insights_time:.2f}s "
                    f"using {insights_result['model_used']}"
                )
                # Update metadata with AI token usage and cost
                metadata.tokens = insights_result.get("total_tokens", 0)
                metadata.cost = insights_result.get("cost", 0.0)
            else:
                logger.warning(
                    f"AI insights generation failed: {insights_result.get('error')}"
                )

            # Step 4: Build complete analysis result
            logger.info("Step 4/4: Building complete analysis result...")
            analysis_time = time.time() - analysis_start

            insights = insights_result.get("insights", {})

            # Build result dict (not PortfolioAnalysisResult dataclass directly)
            # The dataclass will be used later when saving to database
            result = {
                "username": username,
                "context": context,
                "summary": insights.get(
                    "executive_summary",
                    f"Portfolio analysis for {username} based on {len(repos)} public repositories.",
                ),
                "limitations": insights.get(
                    "data_limitations_warning",
                    "PUBLIC REPOSITORIES ONLY. Private work not visible.",
                ),
                "observations": insights.get("key_observations", []),
                "evolution_periods": insights.get("public_portfolio_evolution", []),
                "evidence_patterns": insights.get("evidence_patterns", []),
                "interview_questions": insights.get("interview_questions", []),
                "positive_indicators": insights.get("positive_indicators", []),
                "areas_to_explore": insights.get("areas_to_explore", []),
                "recommendations": insights.get("recommendations", []),
                "quality_indicators": insights.get("quality_indicators", []),
                "confidence_explanation": insights.get(
                    "confidence_explanation",
                    "AI analysis based on public repository evidence only.",
                ),
                "model_used": insights_result.get("model_used", "unknown"),
            }

            # Log summary
            self._log_analysis_summary(
                username=username,
                repos=repos,
                metadata=metadata,
                insights=insights,
                fetch_time=fetch_time,
                evidence_time=evidence_time,
                insights_time=insights_time,
                total_time=analysis_time,
            )

            return {
                "success": True,
                "username": username,
                "context": context,
                "tier": tier,
                "result": result,
                "evidence": evidence,
                "metadata": metadata,
                "fetch_time_seconds": fetch_time,
                "evidence_extraction_time_seconds": evidence_time,
                "ai_insights_time_seconds": insights_time,
                "total_analysis_time_seconds": analysis_time,
                "api_calls_used": fetch_result.api_calls_used,
                "model_used": insights_result.get("model_used", "N/A"),
                "questions_model_used": insights_result.get("questions_model_used"),
                "use_multi_model": insights_result.get("questions_model_used")
                is not None,
            }

        except Exception as e:
            logger.error(
                f"Portfolio analysis failed for {username}: {str(e)}", exc_info=True
            )
            analysis_time = time.time() - analysis_start

            # Return minimal result on error
            return {
                "success": False,
                "username": username,
                "context": context,
                "tier": tier,
                "error": str(e),
                "total_analysis_time_seconds": analysis_time,
                "result": None,
                "evidence": {},
                "metadata": PortfolioMetadata(
                    total_public_repos=0,
                    repos_analyzed=0,
                    repos_skipped=0,
                    skip_counts={},
                    skipped_repos={},
                    analyzed_repos=[],
                    oldest_repo="",
                    newest_repo="",
                    timeline_gaps=0,
                    tokens=0,
                    cost=0.0,
                ),
            }

    def _calculate_career_span_days(self, repos: List[RepoData]) -> int:
        """
        Calculate career span in days from oldest to newest repo.

        Args:
            repos: List of repository data

        Returns:
            Number of days between oldest and newest repo creation
        """
        if not repos or len(repos) < 2:
            return 0

        sorted_repos = sorted(repos, key=lambda r: r.created_at)
        oldest = sorted_repos[0].created_at
        newest = sorted_repos[-1].created_at

        return (newest - oldest).days

    def _log_analysis_summary(
        self,
        username: str,
        repos: List[RepoData],
        metadata: PortfolioMetadata,
        insights: Dict[str, Any],
        fetch_time: float,
        evidence_time: float,
        insights_time: float,
        total_time: float,
    ) -> None:
        """
        Log summary of portfolio analysis.

        Args:
            username: Analyzed username
            repos: List of repositories analyzed
            metadata: Portfolio metadata
            insights: AI-generated insights
            fetch_time: Time spent fetching (seconds)
            evidence_time: Time spent extracting evidence (seconds)
            insights_time: Time spent generating insights (seconds)
            total_time: Total analysis time (seconds)
        """
        logger.info(f"Portfolio analysis complete for {username}:")
        logger.info(f"  📊 Total public repos: {metadata.total_public_repos}")
        logger.info(f"  ✅ Repos analyzed: {metadata.repos_analyzed}")
        logger.info(f"  ⏭️  Repos skipped: {metadata.repos_skipped}")

        # Log skip breakdown
        if metadata.skip_counts:
            skip_details = ", ".join(
                f"{reason}: {count}" for reason, count in metadata.skip_counts.items()
            )
            logger.info(f"     Skip breakdown: {skip_details}")

        # Log timing breakdown
        logger.info(f"  ⏱️  Fetch time: {fetch_time:.2f}s")
        logger.info(f"  ⏱️  Evidence extraction: {evidence_time:.2f}s")
        logger.info(f"  ⏱️  AI insights: {insights_time:.2f}s")
        logger.info(f"  ⏱️  Total time: {total_time:.2f}s")

        # Log insights summary
        key_obs_count = len(insights.get("key_observations", []))
        questions_count = len(insights.get("interview_questions", []))
        evolution_count = len(insights.get("public_portfolio_evolution", []))

        logger.info(f"  💡 Key observations: {key_obs_count}")
        logger.info(f"  ❓ Interview questions: {questions_count}")
        logger.info(f"  📈 Evolution periods: {evolution_count}")

        # Log first key observation if available
        key_obs = insights.get("key_observations", [])
        if key_obs:
            first_obs = key_obs[0]
            preview = first_obs[:100] + "..." if len(first_obs) > 100 else first_obs
            logger.info(f"  📝 First observation: {preview}")
