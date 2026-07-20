# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Intelligent token allocation for Scale+ tier based on repository complexity.
Optimizes API costs while ensuring quality analysis.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class RepositoryComplexity:
    """Repository complexity metrics for token allocation."""

    total_files: int
    total_lines: int
    languages_count: int
    has_tests: bool
    has_ci_cd: bool
    commit_count: int
    contributor_count: int
    avg_file_size: float


class TokenAllocator:
    """Allocates tokens based on repository complexity for cost optimization."""

    # Token tiers for Scale+ (Claude 3.7 Sonnet)
    TOKEN_TIERS = {
        "small": 8192,  # For simple repos
        "medium": 16384,  # For medium complexity
        "large": 32768,  # For complex enterprise repos
    }

    # Cost per 1K tokens for Claude 3.7 Sonnet
    COST_PER_1K_TOKENS = {
        "input": 0.0015,  # $0.0015 per 1K input tokens
        "output": 0.0075,  # $0.0075 per 1K output tokens
    }

    def __init__(self) -> None:
        """Initialize the token allocator."""
        self.logger = logger

    def calculate_repository_complexity(
        self, repository_data: Dict[str, Any]
    ) -> RepositoryComplexity:
        """
        Calculate repository complexity based on various metrics.

        Args:
            repository_data: Repository metadata and statistics

        Returns:
            RepositoryComplexity object with calculated metrics
        """
        # Extract basic metrics
        total_files = repository_data.get("total_files", 0)
        total_lines = repository_data.get("total_lines", 0)
        languages = repository_data.get("languages", {})
        languages_count = len(languages)

        # Check for quality indicators
        has_tests = any(
            "test" in f.lower() or "spec" in f.lower()
            for f in repository_data.get("file_paths", [])
        )
        has_ci_cd = any(
            any(
                ci_pattern in f
                for ci_pattern in [
                    ".github/workflows",
                    ".gitlab-ci.yml",
                    ".circleci/config.yml",
                    "Jenkinsfile",
                    ".travis.yml",
                ]
            )
            for f in repository_data.get("file_paths", [])
        )

        # Extract collaboration metrics
        commit_count = repository_data.get("commit_count", 0)
        contributor_count = repository_data.get("contributor_count", 1)

        # Calculate average file size
        avg_file_size = total_lines / total_files if total_files > 0 else 0

        return RepositoryComplexity(
            total_files=total_files,
            total_lines=total_lines,
            languages_count=languages_count,
            has_tests=has_tests,
            has_ci_cd=has_ci_cd,
            commit_count=commit_count,
            contributor_count=contributor_count,
            avg_file_size=avg_file_size,
        )

    def allocate_tokens(
        self, complexity: RepositoryComplexity, tier: str
    ) -> Tuple[int, str, float]:
        """
        Allocate tokens based on clear, defensible heuristics.
        No scores, no oracles, just transparent rules.

        Args:
            complexity: Repository complexity metrics
            tier: Subscription tier

        Returns:
            Tuple of (max_tokens, allocation_reason, estimated_cost)
        """
        if tier.lower() != "scale_plus":
            # For non-Scale+ tiers, return standard allocations
            standard_tokens = {
                "free": 4096,
                "basic": 8192,
                "professional": 8192,
                "enterprise": 16384,
                "scale": 16384,
            }
            tokens = standard_tokens.get(tier.lower(), 8192)
            return tokens, "Standard allocation for tier", self._estimate_cost(tokens)

        # --- Scale+ Rule Engine: Clear, Transparent Heuristics ---

        # Rule 1: The Mega-Repo Rule (Highest Priority)
        if complexity.total_files > 2000 or complexity.total_lines > 200000:
            reason = "Very large codebase requires maximum analysis depth"
            max_tokens = self.TOKEN_TIERS["large"]
            return max_tokens, reason, self._estimate_cost(max_tokens)

        # Rule 2: The High-Collaboration Rule
        if complexity.contributor_count > 50 and complexity.commit_count > 5000:
            reason = "High contributor count and deep history suggests complex collaboration patterns"
            max_tokens = self.TOKEN_TIERS["large"]
            return max_tokens, reason, self._estimate_cost(max_tokens)

        # Rule 3: The Polyglot Rule
        if complexity.languages_count >= 5:
            reason = "Polyglot repository with multiple significant languages"
            max_tokens = self.TOKEN_TIERS["medium"]
            return max_tokens, reason, self._estimate_cost(max_tokens)

        # Rule 4: The Trivial Repo Rule (Lowest Priority)
        if complexity.total_files < 20 and complexity.commit_count < 50:
            reason = "Small, simple repository with limited history"
            max_tokens = self.TOKEN_TIERS["small"]
            return max_tokens, reason, self._estimate_cost(max_tokens)

        # Default Rule
        reason = "Standard repository complexity"
        max_tokens = self.TOKEN_TIERS["medium"]
        return max_tokens, reason, self._estimate_cost(max_tokens)

    def _estimate_cost(self, max_tokens: int) -> float:
        """
        Estimate the cost for the given token allocation.

        Assumes average input tokens of 2x output tokens.
        """
        # Estimate input tokens (typically 2x output for comprehensive analysis)
        estimated_input_tokens = max_tokens * 2

        # Calculate costs
        input_cost = (estimated_input_tokens / 1000) * self.COST_PER_1K_TOKENS["input"]
        output_cost = (max_tokens / 1000) * self.COST_PER_1K_TOKENS["output"]

        total_cost = input_cost + output_cost
        return round(total_cost, 4)

    def monitor_usage_for_admin(
        self, user_id: str, daily_cost: float, monthly_cost: float
    ) -> Optional[List[Dict[str, str]]]:
        """
        Monitor Scale+ usage for internal admin alerts.
        NEVER blocks customer usage - Scale+ users paid for 3,000 analyses!

        Args:
            user_id: User ID for tracking
            daily_cost: Current daily cost
            monthly_cost: Current monthly cost

        Returns:
            Alert info for admin dashboard, or None
        """
        alerts = []

        if daily_cost > 50:
            alerts.append(
                {
                    "level": "warning",
                    "message": f"Scale+ user {user_id} daily cost: ${daily_cost:.2f}",
                    "action": "Monitor for optimization opportunities",
                }
            )

        if daily_cost > 100:
            alerts.append(
                {
                    "level": "urgent",
                    "message": f"Scale+ user {user_id} exceeding expected daily cost: ${daily_cost:.2f}",
                    "action": "Review usage patterns for potential optimizations",
                }
            )

        if monthly_cost > 500:
            alerts.append(
                {
                    "level": "info",
                    "message": f"Scale+ power user {user_id} - consider Scale++ tier?",
                    "action": "Potential upsell opportunity",
                }
            )

        return alerts if alerts else None

    def get_batch_processing_strategy(
        self, repositories: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Determine optimal batch processing strategy for internal efficiency.
        This is NOT a limit - just optimization guidance.

        Args:
            repositories: List of repository data

        Returns:
            Processing strategy recommendation
        """
        if not repositories:
            return {"strategy": "none", "reason": "No repositories to process"}

        # Calculate complexities
        complexities = [
            self.calculate_repository_complexity(repo) for repo in repositories
        ]

        # Count by complexity level
        large_repos = sum(
            1 for c in complexities if c.total_files > 2000 or c.total_lines > 200000
        )
        trivial_repos = sum(
            1 for c in complexities if c.total_files < 20 and c.commit_count < 50
        )

        # Recommend strategy
        if large_repos > len(repositories) * 0.5:
            return {
                "strategy": "sequential",
                "chunk_size": 3,
                "reason": "Many large repositories - process in smaller chunks to avoid timeouts",
                "estimated_time_minutes": len(repositories) * 2,
            }
        elif trivial_repos > len(repositories) * 0.7:
            return {
                "strategy": "parallel",
                "chunk_size": 15,
                "reason": "Mostly small repositories - can process full batch",
                "estimated_time_minutes": 5,
            }
        else:
            return {
                "strategy": "adaptive",
                "chunk_size": 5,
                "reason": "Mixed repository sizes - balanced approach",
                "estimated_time_minutes": len(repositories),
            }
