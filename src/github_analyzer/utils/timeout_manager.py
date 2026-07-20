# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Dynamic timeout management for repository analysis.

This module provides intelligent timeout configuration based on repository
characteristics to ensure analyses complete successfully regardless of complexity.
"""

import logging
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from ..data.models import RepositoryData
from ..database.models import SubscriptionPlan

logger = logging.getLogger(__name__)


@dataclass
class TimeoutConfig:
    """Timeout configuration for an analysis."""

    frontend_timeout_ms: int  # Frontend axios timeout in milliseconds
    backend_timeout_s: int  # Backend processing timeout in seconds
    claude_timeout_s: int  # Claude API timeout in seconds
    category: str  # Repository category (TINY, SMALL, MEDIUM, etc.)
    explanation: str  # Human-readable explanation


class TimeoutManager:
    """Manages dynamic timeout configuration based on repository characteristics."""

    # Base timeouts by repository complexity (in seconds)
    # Re-calibrated for realistic candidate repositories
    # MINIMUM 180s (3 minutes) to ensure AI has time to generate all content
    # Increased minimums to handle Scale+ tier's comprehensive analysis
    # INCREASED 50% (Oct 2025) - New Claude 4.5 models slower due to network congestion
    BASE_TIMEOUTS = {
        "TINY": 270,  # Documentation, lists, minimal code (180s → 270s for Sonnet 4.5)
        "SMALL": 315,  # Small utilities, single-purpose libraries (210s → 315s)
        "MEDIUM": 360,  # Standard libraries and frameworks (240s → 360s = 6 mins)
        "LARGE": 450,  # Complex frameworks, large codebases (300s → 450s = 7.5 mins)
        "MASSIVE": 540,  # Large projects (360s → 540s = 9 mins)
        "EXTREME": None,  # Too large for sync - requires async batch
    }

    # NO TIER MULTIPLIERS - All users get same timeout for same repo
    # The tier difference is in AI quality/depth, not processing time
    # Removed tier multipliers to ensure fairness across all plans

    # Maximum allowed timeouts (safety limits)
    # Increased for batch processing - 15 repos at 4 min each = 60 minutes
    MAX_FRONTEND_TIMEOUT_MS = 3900000  # 65 minutes (extra buffer for batch of 15)
    MAX_BACKEND_TIMEOUT_S = 3900  # 65 minutes (extra buffer for batch of 15)
    MAX_CLAUDE_TIMEOUT_S = 300  # 5 minutes (Claude's own limit per request)

    @classmethod
    def categorize_repository(cls, repo_data: RepositoryData) -> Tuple[str, str]:
        """
        Categorize repository complexity based on evidence patterns.
        Uses rule-based categorization without numerical scoring.

        Returns:
            Tuple of (category, explanation)
        """
        # Extract evidence
        try:
            total_files = (
                len(repo_data.file_structure) if repo_data.file_structure else 0
            )
        except (TypeError, AttributeError):
            # Handle mock objects or missing data
            total_files = 0
        total_commits = repo_data.metrics.total_commits if repo_data.metrics else 0
        total_contributors = (
            repo_data.metrics.unique_contributors if repo_data.metrics else 0
        )
        try:
            total_languages = len(repo_data.languages) if repo_data.languages else 0
        except (TypeError, AttributeError):
            # Handle mock objects or missing data
            total_languages = 0
        repo_size_mb = repo_data.size / 1024 if repo_data.size else 0
        try:
            repo_name_lower = repo_data.name.lower() if repo_data.name else ""
        except (TypeError, AttributeError):
            # Handle mock objects
            repo_name_lower = ""

        # Evidence-based categorization (like token allocator)
        # Check for known massive projects first
        try:
            if repo_name_lower and any(
                name in repo_name_lower
                for name in ["kubernetes", "tensorflow", "linux", "chromium"]
            ):
                return "MASSIVE", f"Known large-scale project: {repo_data.name}"
        except (TypeError, AttributeError):
            # Skip if mock object
            pass

        # Check if documentation-only repository
        if total_files > 0 and repo_data.file_structure:
            doc_files = sum(
                1
                for f in repo_data.file_structure[:50]
                if f.name.endswith((".md", ".txt", ".rst", ".adoc"))
            )
            if doc_files > total_files * 0.8:
                return "TINY", f"Documentation repository with {total_files} files"

        # EXTREME: Repositories too large for synchronous analysis
        # These are full products/companies, not individual candidate repos
        if total_files > 10000 or total_commits > 50000 or repo_size_mb > 500:
            evidence_parts = []
            if total_files > 10000:
                evidence_parts.append(f"{total_files:,} files")
            if total_commits > 50000:
                evidence_parts.append(f"{total_commits:,} commits")
            if repo_size_mb > 500:
                evidence_parts.append(f"{repo_size_mb:.0f}MB")
            return "EXTREME", f"Extreme-scale repository: {', '.join(evidence_parts)}"

        # MASSIVE: Large projects but still analyzable synchronously
        if (
            total_files > 1000
            or total_commits > 10000
            or repo_size_mb > 100
            or (total_contributors > 100 and total_commits > 5000)
        ):
            evidence_parts = []
            if total_files > 1000:
                evidence_parts.append(f"{total_files:,} files")
            if total_commits > 10000:
                evidence_parts.append(f"{total_commits:,} commits")
            if repo_size_mb > 100:
                evidence_parts.append(f"{repo_size_mb:.0f}MB")
            return "MASSIVE", f"Massive repository: {', '.join(evidence_parts)}"

        # LARGE: Complex frameworks and large codebases
        if (
            total_files > 200
            or total_commits > 2000
            or repo_size_mb > 50
            or (total_contributors > 50 and total_languages > 5)
        ):
            evidence_parts = []
            if total_files > 200:
                evidence_parts.append(f"{total_files} files")
            if total_commits > 2000:
                evidence_parts.append(f"{total_commits:,} commits")
            if total_contributors > 50:
                evidence_parts.append(f"{total_contributors} contributors")
            return "LARGE", f"Large codebase: {', '.join(evidence_parts[:2])}"

        # MEDIUM: Standard libraries and frameworks
        if (
            total_files > 50
            or total_commits > 500
            or repo_size_mb > 10
            or total_languages > 3
        ):
            evidence_parts = []
            if total_files > 50:
                evidence_parts.append(f"{total_files} files")
            if total_languages > 3:
                evidence_parts.append(f"{total_languages} languages")
            return "MEDIUM", f"Medium complexity: {', '.join(evidence_parts[:2])}"

        # SMALL: Small utilities and single-purpose libraries
        if total_files > 10 or total_commits > 100:
            return "SMALL", f"Small project with {total_files} files"

        # TINY: Minimal projects, examples, documentation
        return "TINY", f"Minimal repository with {total_files} files"

    @classmethod
    def should_reject_extreme_repo(
        cls,
        repo_data: RepositoryData,
        subscription_plan: Optional[SubscriptionPlan] = None,
    ) -> tuple[bool, str]:
        """
        Check if repository is too large for synchronous analysis.

        Different tiers have different size limits:
        - Free/Basic: Reject repos > 500MB
        - Professional (Growth): Reject repos > 2GB
        - Enterprise (Scale): Reject repos > 5GB
        - Scale+: Reject repos > 10GB

        Returns:
            Tuple of (should_reject, rejection_message)
        """
        # Get repo size in MB
        repo_size_mb = repo_data.size / 1024 if repo_data.size else 0
        total_files = len(repo_data.file_structure) if repo_data.file_structure else 0
        total_commits = repo_data.metrics.total_commits if repo_data.metrics else 0

        # Define size limits by tier (in MB)
        size_limits = {
            SubscriptionPlan.FREE: 500,
            SubscriptionPlan.BASIC: 500,
            SubscriptionPlan.PROFESSIONAL: 2048,  # 2GB for Growth tier
            SubscriptionPlan.ENTERPRISE: 5120,  # 5GB for Scale tier
            SubscriptionPlan.SCALE_PLUS: 10240,  # 10GB for Scale+
        }

        # Default to most restrictive if no plan specified
        if subscription_plan is None:
            subscription_plan = SubscriptionPlan.FREE

        max_size_mb = size_limits.get(subscription_plan, 500)

        # Also check file and commit counts (same for all tiers)
        if repo_size_mb > max_size_mb or total_files > 50000 or total_commits > 100000:
            evidence_parts = []
            if repo_size_mb > max_size_mb:
                evidence_parts.append(f"{repo_size_mb:.0f}MB (limit: {max_size_mb}MB)")
            if total_files > 50000:
                evidence_parts.append(f"{total_files:,} files")
            if total_commits > 100000:
                evidence_parts.append(f"{total_commits:,} commits")

            rejection_message = (
                f"This repository exceeds the size limit for {subscription_plan.value} tier. "
                f"Repository characteristics: {', '.join(evidence_parts)}. \n\n"
            )

            # Add tier-specific upgrade message
            if subscription_plan in [SubscriptionPlan.FREE, SubscriptionPlan.BASIC]:
                rejection_message += (
                    "Upgrade to Growth tier to analyze repositories up to 2GB, "
                    "Scale tier for up to 5GB, or Scale+ for up to 10GB."
                )
            elif subscription_plan == SubscriptionPlan.PROFESSIONAL:
                rejection_message += (
                    "Upgrade to Scale tier to analyze repositories up to 5GB, "
                    "or Scale+ for up to 10GB."
                )
            elif subscription_plan == SubscriptionPlan.ENTERPRISE:
                rejection_message += (
                    "Upgrade to Scale+ tier to analyze repositories up to 10GB."
                )
            else:
                rejection_message += (
                    "For repositories larger than 10GB, please contact support "
                    "for custom batch analysis options."
                )

            return True, rejection_message

        # Not extreme for this tier
        return False, ""

    @classmethod
    def calculate_timeouts(
        cls, repo_data: RepositoryData, subscription_plan: SubscriptionPlan
    ) -> TimeoutConfig:
        """
        Calculate appropriate timeouts for a repository analysis.

        Args:
            repo_data: Repository data
            subscription_plan: User's subscription plan

        Returns:
            TimeoutConfig with calculated timeouts
        """
        # Categorize repository using evidence-based rules
        category, explanation = cls.categorize_repository(repo_data)

        # Get base timeout for category
        base_timeout = cls.BASE_TIMEOUTS.get(category, cls.BASE_TIMEOUTS["MEDIUM"])

        # Safety check - EXTREME repos should not reach here
        if base_timeout is None:
            logger.error(
                f"Attempted to calculate timeout for EXTREME repository: {repo_data.name}"
            )
            base_timeout = cls.BASE_TIMEOUTS["MASSIVE"]  # Fallback to maximum

        # Ensure base_timeout is not None for type checker
        if base_timeout is None:
            raise ValueError("base_timeout should not be None after fallback")

        # NO TIER MULTIPLIER - Same timeout for all users analyzing same repo
        # Calculate timeouts with safety margins
        backend_timeout = int(base_timeout * 1.2)  # 20% margin
        frontend_timeout_ms = int(
            backend_timeout * 1000 * 1.5
        )  # 50% margin for frontend
        claude_timeout = min(int(backend_timeout * 0.8), cls.MAX_CLAUDE_TIMEOUT_S)

        # Apply maximum limits
        backend_timeout = min(backend_timeout, cls.MAX_BACKEND_TIMEOUT_S)
        frontend_timeout_ms = min(frontend_timeout_ms, cls.MAX_FRONTEND_TIMEOUT_MS)

        logger.info(
            f"Timeout configuration for {repo_data.name}: "
            f"{explanation}, backend={backend_timeout}s, "
            f"frontend={frontend_timeout_ms / 1000}s, plan={subscription_plan.value}"
        )

        return TimeoutConfig(
            frontend_timeout_ms=frontend_timeout_ms,
            backend_timeout_s=backend_timeout,
            claude_timeout_s=claude_timeout,
            category=category,
            explanation=explanation,
        )

    @classmethod
    def get_quick_timeout_estimate(
        cls, repo_url: str, subscription_plan: SubscriptionPlan
    ) -> Dict[str, int]:
        """
        Get a quick timeout estimate without full repository data.
        Used for initial frontend configuration.

        Returns:
            Dict with 'frontend_ms' and 'backend_s' timeouts
        """
        # Default to MEDIUM category when we don't have data yet
        base_timeout = cls.BASE_TIMEOUTS["MEDIUM"]
        if base_timeout is None:
            raise ValueError("MEDIUM timeout should never be None")

        # NO TIER MULTIPLIER - Same timeout for all users
        backend_timeout = int(base_timeout * 1.2)  # 20% margin
        frontend_timeout_ms = int(backend_timeout * 1000 * 1.5)  # 50% margin

        # Apply limits
        backend_timeout = min(backend_timeout, cls.MAX_BACKEND_TIMEOUT_S)
        frontend_timeout_ms = min(frontend_timeout_ms, cls.MAX_FRONTEND_TIMEOUT_MS)

        return {
            "frontend_ms": frontend_timeout_ms,
            "backend_s": backend_timeout,
        }
