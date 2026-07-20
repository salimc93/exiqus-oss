# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
PR Analyzer - Orchestrates PR data fetching and evidence extraction.

This module coordinates the entire PR analysis pipeline:
1. Fetches PR data via GraphQL
2. Extracts evidence patterns
3. Returns structured analysis results
"""

from typing import Any, Dict, List, Tuple

from ..utils.logging import get_logger
from .pr_evidence_extractor import PREvidenceExtractor
from .pr_fetcher import PRFetcher
from .pr_models import PRData, PREvidence, QualitySignals

logger = get_logger(__name__)


class PRAnalyzer:
    """Orchestrates PR analysis workflow."""

    def __init__(self, github_token: str) -> None:
        """Initialize PR analyzer with GitHub token.

        Args:
            github_token: GitHub API token for authentication
        """
        self.fetcher = PRFetcher(github_token)
        self.extractor = PREvidenceExtractor()

    def analyze_user(
        self, username: str, context: str = "OPEN_SOURCE"
    ) -> Dict[str, Any]:
        """Analyze a GitHub user's PR contributions.

        Args:
            username: GitHub username to analyze
            context: Analysis context (STARTUP, ENTERPRISE, AGENCY, OPEN_SOURCE)

        Returns:
            Dictionary with analysis results including evidence and signals
        """
        logger.info(f"Starting PR analysis for user: {username}")

        try:
            # Fetch PR data via GraphQL (always fetch ALL PRs)
            logger.info("Fetching PR data via GraphQL...")
            fetch_result = self.fetcher.fetch_user_prs(username)

            prs = fetch_result.prs
            logger.info(
                f"Fetched {len(prs)} PRs in {fetch_result.api_calls_used} API calls"
            )

            # Extract evidence patterns
            logger.info("Extracting evidence patterns...")
            evidence = self.extractor.extract_evidence(prs, username)

            # Extract quality signals
            logger.info("Extracting quality signals...")
            quality_signals = self.extractor.extract_quality_signals(prs, username)

            # Log summary statistics
            self._log_analysis_summary(username, prs, evidence, quality_signals)

            return {
                "success": True,
                "username": username,
                "context": context,
                "total_prs": len(prs),
                "evidence": evidence,
                "quality_signals": quality_signals,
                "api_calls_used": fetch_result.api_calls_used,
                "fetch_time_seconds": fetch_result.fetch_time_seconds,
                "repos_contributed": fetch_result.repos_contributed,
            }

        except Exception as e:
            logger.error(f"Failed to analyze user {username}: {str(e)}", exc_info=True)
            return {
                "success": False,
                "username": username,
                "context": context,
                "total_prs": 0,
                "error": str(e),
                "evidence": PREvidence(),
                "quality_signals": QualitySignals(
                    total_prs=0, merged_prs=0, unique_repos=0, feature_prs=0, fix_prs=0
                ),
            }

    def analyze_repository_contributors(
        self, owner: str, repo: str, top_n: int = 10
    ) -> Dict[str, Dict[str, Any]]:
        """Analyze top contributors to a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            top_n: Number of top contributors to analyze

        Returns:
            Dictionary mapping usernames to their PR analysis results
        """
        logger.info(f"Analyzing top {top_n} contributors to {owner}/{repo}")

        # Get top contributors
        contributors = self._get_top_contributors(owner, repo, top_n)

        results = {}
        for contributor in contributors:
            logger.info(f"Analyzing contributor: {contributor}")
            # Analyze PRs for this repo specifically
            result = self._analyze_user_for_repo(
                username=contributor, owner=owner, repo=repo
            )
            results[contributor] = result

        return results

    def _analyze_user_for_repo(
        self, username: str, owner: str, repo: str
    ) -> Dict[str, Any]:
        """Analyze a user's contributions to a specific repository.

        Args:
            username: GitHub username
            owner: Repository owner
            repo: Repository name

        Returns:
            PR analysis result for the user in this repository
        """
        logger.info(f"Fetching {username}'s PRs for {owner}/{repo}")

        try:
            # Fetch all user PRs
            fetch_result = self.fetcher.fetch_user_prs(username)

            # Filter PRs for this repository
            repo_prs = [
                pr
                for pr in fetch_result.prs
                if pr.repository_owner == owner and pr.repository_name == repo
            ]

            logger.info(f"Found {len(repo_prs)} PRs in {owner}/{repo}")

            # Extract evidence and signals for repo-specific PRs
            evidence = self.extractor.extract_evidence(repo_prs, username)
            quality_signals = self.extractor.extract_quality_signals(repo_prs, username)

            return {
                "success": True,
                "username": username,
                "total_prs": len(repo_prs),
                "evidence": evidence,
                "quality_signals": quality_signals,
                "repository_context": f"{owner}/{repo}",
                "api_calls_used": fetch_result.api_calls_used,
                "fetch_time_seconds": fetch_result.fetch_time_seconds,
            }

        except Exception as e:
            logger.error(f"Failed to analyze {username} for {owner}/{repo}: {str(e)}")
            return {
                "success": False,
                "username": username,
                "repository_context": f"{owner}/{repo}",
                "total_prs": 0,
                "error": str(e),
                "evidence": PREvidence(),
                "quality_signals": QualitySignals(
                    total_prs=0, merged_prs=0, unique_repos=0, feature_prs=0, fix_prs=0
                ),
            }

    def _get_top_contributors(self, owner: str, repo: str, limit: int) -> List[str]:
        """Get top contributors to a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            limit: Number of contributors to return

        Returns:
            List of top contributor usernames
        """
        # This would use GraphQL to get top contributors
        # For now, return empty list as this requires additional GraphQL implementation
        logger.warning(
            f"Repository contributor analysis not yet implemented for {owner}/{repo}"
        )
        return []

    def _log_analysis_summary(
        self,
        username: str,
        prs: List[PRData],
        evidence: PREvidence,
        signals: QualitySignals,
    ) -> None:
        """Log summary of analysis results.

        Args:
            username: Analyzed username
            prs: List of PRs analyzed
            evidence: Extracted evidence
            signals: Quality signals
        """
        merged_count = sum(1 for pr in prs if pr.merged)

        logger.info(f"Analysis complete for {username}:")
        logger.info(f"  - Total PRs: {len(prs)}")
        logger.info(f"  - Merged PRs: {merged_count}")
        logger.info(
            f"  - Merge rate: {signals.merge_rate:.1%}"
            if signals.merge_rate
            else "  - Merge rate: N/A"
        )
        logger.info(f"  - Unique repositories: {signals.unique_repos}")
        logger.info(f"  - Evidence items: {evidence.total_evidence_count()}")

        # Log key evidence highlights
        if evidence.technical_substance:
            logger.info(f"  - Key evidence: {evidence.technical_substance[0][:100]}...")

    def get_rate_limit_status(self) -> Tuple[int, int]:
        """Get current GitHub API rate limit status.

        Returns:
            Tuple of (remaining, limit)
        """
        return self.fetcher.get_rate_limit_status()
