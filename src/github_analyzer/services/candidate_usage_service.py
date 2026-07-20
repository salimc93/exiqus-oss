# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Candidate Usage Service.

Implements "1 GitHub username = 1 candidate assessment per month" tracking
across both Portfolio Analysis and PR Analysis.

Core principle: Analyzing the same GitHub username with Portfolio, PR, or both
counts as a single candidate assessment in the monthly billing period.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import SubscriptionPlan
from ..database.models_portfolio import CandidateAssessment, RepositoryDeepDive
from ..utils.logging import get_logger

logger = get_logger(__name__)


class CandidateUsageService:
    """Service for tracking candidate assessments across Portfolio and PR Analysis."""

    # Monthly limits per tier for candidate assessments
    CANDIDATE_LIMITS = {
        SubscriptionPlan.FREE: 0,  # No candidate assessments (portfolio/PR blocked)
        SubscriptionPlan.BASIC: 10,  # 10 candidate assessments per month
        SubscriptionPlan.PROFESSIONAL: 50,  # 50 candidate assessments per month
        SubscriptionPlan.ENTERPRISE: 200,  # 200 candidate assessments per month
        SubscriptionPlan.SCALE_PLUS: 500,  # 500 candidate assessments per month
    }

    # Monthly limits per tier for repo deep dives
    REPO_DEEP_DIVE_LIMITS = {
        SubscriptionPlan.FREE: 0,  # No repo deep dives
        SubscriptionPlan.BASIC: 10,  # 10 repo deep dives per month
        SubscriptionPlan.PROFESSIONAL: 50,  # 50 repo deep dives per month
        SubscriptionPlan.ENTERPRISE: 200,  # 200 repo deep dives per month
        SubscriptionPlan.SCALE_PLUS: 500,  # 500 repo deep dives per month
    }

    # Backward compatibility
    TIER_LIMITS = CANDIDATE_LIMITS

    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize the candidate usage service.

        Args:
            db: Database session
        """
        self.db = db

    @staticmethod
    def get_current_billing_period() -> str:
        """
        Get current billing period in YYYY-MM format.

        Returns:
            Current billing period (e.g., "2025-10")
        """
        now = datetime.now(timezone.utc)
        return now.strftime("%Y-%m")

    async def get_or_create_assessment(
        self,
        user_id: str,
        github_username: str,
        analysis_type: str,
    ) -> tuple[CandidateAssessment, bool]:
        """
        Get or create candidate assessment record for current billing period.

        Args:
            user_id: User ID
            github_username: GitHub username being assessed
            analysis_type: "portfolio" or "pr"

        Returns:
            Tuple of (CandidateAssessment, is_new) where is_new indicates
            if this is a new assessment this month
        """
        billing_period = self.get_current_billing_period()

        # Check if assessment exists for this username in current period
        result = await self.db.execute(
            select(CandidateAssessment).where(
                CandidateAssessment.user_id == user_id,
                CandidateAssessment.github_username == github_username,
                CandidateAssessment.billing_period == billing_period,
            )
        )
        assessment = result.scalar_one_or_none()

        if assessment:
            # Update existing assessment
            is_new = False
            now = datetime.now(timezone.utc)

            if analysis_type == "portfolio":
                assessment.portfolio_analysis_count += 1
            elif analysis_type == "pr":
                assessment.pr_analysis_count += 1

            assessment.last_analyzed_at = now

            logger.info(
                f"Updated existing assessment for {github_username} by user {user_id}: "
                f"portfolio={assessment.portfolio_analysis_count}, "
                f"pr={assessment.pr_analysis_count}"
            )
        else:
            # Create new assessment
            is_new = True
            now = datetime.now(timezone.utc)

            assessment = CandidateAssessment(
                user_id=user_id,
                github_username=github_username,
                billing_period=billing_period,
                portfolio_analysis_count=1 if analysis_type == "portfolio" else 0,
                pr_analysis_count=1 if analysis_type == "pr" else 0,
                first_analyzed_at=now,
                last_analyzed_at=now,
            )
            self.db.add(assessment)

            logger.info(
                f"Created new assessment for {github_username} by user {user_id} "
                f"in period {billing_period}"
            )

        await self.db.commit()
        await self.db.refresh(assessment)

        return assessment, is_new

    async def get_monthly_usage(
        self, user_id: str, billing_period: Optional[str] = None
    ) -> int:
        """
        Get total unique candidate assessments for user in billing period.

        Args:
            user_id: User ID
            billing_period: Billing period (defaults to current)

        Returns:
            Number of unique candidates assessed this month
        """
        if billing_period is None:
            billing_period = self.get_current_billing_period()

        result = await self.db.execute(
            select(CandidateAssessment).where(
                CandidateAssessment.user_id == user_id,
                CandidateAssessment.billing_period == billing_period,
            )
        )
        assessments = result.scalars().all()

        count = len(assessments)
        logger.info(
            f"User {user_id} has assessed {count} unique candidates "
            f"in period {billing_period}"
        )

        return count

    async def check_limit(
        self, user_id: str, tier: SubscriptionPlan
    ) -> tuple[bool, int, int]:
        """
        Check if user can assess another candidate this month.

        Args:
            user_id: User ID
            tier: User's subscription tier

        Returns:
            Tuple of (is_allowed, current_count, limit)
        """
        limit = self.TIER_LIMITS.get(tier, 0)
        current_count = await self.get_monthly_usage(user_id)

        is_allowed = current_count < limit

        if not is_allowed:
            logger.warning(
                f"User {user_id} exceeded monthly candidate limit: "
                f"{current_count}/{limit}"
            )
        else:
            logger.info(
                f"User {user_id} within monthly candidate limit: "
                f"{current_count}/{limit}"
            )

        return is_allowed, current_count, limit

    async def has_assessed_candidate(
        self,
        user_id: str,
        github_username: str,
        billing_period: Optional[str] = None,
    ) -> bool:
        """
        Check if user has already assessed this candidate in billing period.

        Args:
            user_id: User ID
            github_username: GitHub username
            billing_period: Billing period (defaults to current)

        Returns:
            True if candidate already assessed this month
        """
        if billing_period is None:
            billing_period = self.get_current_billing_period()

        result = await self.db.execute(
            select(CandidateAssessment).where(
                CandidateAssessment.user_id == user_id,
                CandidateAssessment.github_username == github_username,
                CandidateAssessment.billing_period == billing_period,
            )
        )
        assessment = result.scalar_one_or_none()

        exists = assessment is not None
        logger.info(
            f"Candidate {github_username} {'already assessed' if exists else 'not yet assessed'} "
            f"by user {user_id} in period {billing_period}"
        )

        return exists

    async def get_assessment_details(
        self,
        user_id: str,
        github_username: str,
        billing_period: Optional[str] = None,
    ) -> Optional[CandidateAssessment]:
        """
        Get detailed assessment record for a specific candidate.

        Args:
            user_id: User ID
            github_username: GitHub username
            billing_period: Billing period (defaults to current)

        Returns:
            CandidateAssessment if exists, None otherwise
        """
        if billing_period is None:
            billing_period = self.get_current_billing_period()

        result = await self.db.execute(
            select(CandidateAssessment).where(
                CandidateAssessment.user_id == user_id,
                CandidateAssessment.github_username == github_username,
                CandidateAssessment.billing_period == billing_period,
            )
        )
        return result.scalar_one_or_none()

    @classmethod
    def get_tier_limit(cls, tier: SubscriptionPlan) -> int:
        """
        Get candidate assessment limit for a tier.

        Args:
            tier: Subscription tier

        Returns:
            Monthly candidate assessment limit
        """
        return cls.CANDIDATE_LIMITS.get(tier, 0)

    # ==================== REPO DEEP DIVE TRACKING ====================

    async def track_repo_deep_dive(
        self,
        user_id: str,
        repository_name: str,
        analysis_id: str,
    ) -> RepositoryDeepDive:
        """
        Track a repository deep dive analysis.

        Args:
            user_id: User ID
            repository_name: Repository name (format: "owner/repo")
            analysis_id: Analysis result ID

        Returns:
            RepositoryDeepDive record
        """
        billing_period = self.get_current_billing_period()
        now = datetime.now(timezone.utc)

        deep_dive = RepositoryDeepDive(
            user_id=user_id,
            repository_name=repository_name,
            billing_period=billing_period,
            analysis_id=analysis_id,
            analyzed_at=now,
        )
        self.db.add(deep_dive)

        logger.info(
            f"Tracked repo deep dive for {repository_name} by user {user_id} "
            f"in period {billing_period}"
        )

        await self.db.commit()
        await self.db.refresh(deep_dive)

        return deep_dive

    async def get_repo_deep_dive_usage(
        self, user_id: str, billing_period: Optional[str] = None
    ) -> int:
        """
        Get total repo deep dives for user in billing period.

        Args:
            user_id: User ID
            billing_period: Billing period (defaults to current)

        Returns:
            Number of repo deep dives this month
        """
        if billing_period is None:
            billing_period = self.get_current_billing_period()

        result = await self.db.execute(
            select(RepositoryDeepDive).where(
                RepositoryDeepDive.user_id == user_id,
                RepositoryDeepDive.billing_period == billing_period,
            )
        )
        deep_dives = result.scalars().all()

        count = len(deep_dives)
        logger.info(
            f"User {user_id} has performed {count} repo deep dives "
            f"in period {billing_period}"
        )

        return count

    async def check_repo_deep_dive_limit(
        self, user_id: str, tier: SubscriptionPlan
    ) -> tuple[bool, int, int]:
        """
        Check if user can perform another repo deep dive this month.

        Args:
            user_id: User ID
            tier: User's subscription tier

        Returns:
            Tuple of (is_allowed, current_count, limit)
        """
        limit = self.REPO_DEEP_DIVE_LIMITS.get(tier, 0)
        current_count = await self.get_repo_deep_dive_usage(user_id)

        is_allowed = current_count < limit

        if not is_allowed:
            logger.warning(
                f"User {user_id} exceeded monthly repo deep dive limit: "
                f"{current_count}/{limit}"
            )
        else:
            logger.info(
                f"User {user_id} within monthly repo deep dive limit: "
                f"{current_count}/{limit}"
            )

        return is_allowed, current_count, limit

    @classmethod
    def get_repo_deep_dive_limit(cls, tier: SubscriptionPlan) -> int:
        """
        Get repo deep dive limit for a tier.

        Args:
            tier: Subscription tier

        Returns:
            Monthly repo deep dive limit
        """
        return cls.REPO_DEEP_DIVE_LIMITS.get(tier, 0)
