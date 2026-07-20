# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
PR Analysis API endpoints.

Provides REST API endpoints for GitHub PR analysis functionality.
Available for all paid tiers with candidate-based counting (1 username = 1 assessment/month).
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...ai.pr_insights_generator import PRInsightsGenerator
from ...core.tier_utils import get_frontend_tier_name
from ...data.pr_analyzer import PRAnalyzer
from ...data.pr_evidence_extractor import PREvidenceExtractor
from ...data.pr_models import PREvidence, QualitySignals
from ...data.pr_report_generator import PRReportGenerator
from ...database.connection import get_db_session
from ...database.models import (
    AnalysisStatus,
    PRAnalysisCache,
    PRAnalysisRecord,
    PRAnalysisResult,
    SubscriptionPlan,
    User,
)
from ...services.candidate_usage_service import CandidateUsageService
from ...services.pr_rate_limiter import pr_rate_limiter
from ...utils.config import get_config
from ...utils.logging import get_logger
from ..auth.dependencies import get_current_active_user
from ..models.requests import PRAnalyzeRequest
from ..models.responses import PRAnalysisResponse
from ..services.candidate_context import validate_context

logger = get_logger(__name__)
config = get_config()

router = APIRouter(prefix="/pr", tags=["PR Analysis"])

# PR analysis is available for all paid tiers
PR_ANALYSIS_TIERS = [
    SubscriptionPlan.BASIC,
    SubscriptionPlan.PROFESSIONAL,
    SubscriptionPlan.ENTERPRISE,  # Backend name (frontend: "Scale")
    SubscriptionPlan.SCALE_PLUS,
]


class PRAnalysisService:
    """Service for PR analysis operations."""

    def __init__(self) -> None:
        """Initialize PR analysis service."""
        self.report_generator = PRReportGenerator()
        # Initialize AI insights generator if API key is available
        self.insights_generator: Optional[PRInsightsGenerator]
        if config.anthropic_api_key:
            self.insights_generator = PRInsightsGenerator(config.anthropic_api_key)
        else:
            self.insights_generator = None
            logger.warning(
                "No Anthropic API key configured - AI insights will be unavailable"
            )

    async def check_user_eligibility(
        self, user: User, username: str, db: AsyncSession
    ) -> tuple[bool, str | dict[str, Any]]:
        """
        Check if user is eligible for PR analysis.

        Args:
            user: User object
            username: GitHub username to analyze
            db: Database session

        Returns:
            Tuple of (is_eligible, reason_if_not)
        """
        # Check tier eligibility (all paid tiers)
        if user.subscription_plan not in PR_ANALYSIS_TIERS:
            tier_name = get_frontend_tier_name(user.subscription_plan.value)
            return (
                False,
                f"PR Analysis is available for paid plans. "
                f"Your current plan: {tier_name}. Upgrade to access this feature.",
            )

        # Check if this username would count as new assessment
        candidate_service = CandidateUsageService(db)
        assessment, is_new = await candidate_service.get_or_create_assessment(
            user_id=user.user_id,
            github_username=username,
            analysis_type="pr",
        )

        if is_new:
            # Check if user has reached their monthly limit
            monthly_usage = await candidate_service.get_monthly_usage(user.user_id)
            limit = CandidateUsageService.get_tier_limit(user.subscription_plan)

            if monthly_usage >= limit:
                return (
                    False,
                    {
                        "error": "Monthly candidate assessment limit reached",
                        "message": f"You have used all {limit} candidate assessments this month ({monthly_usage}/{limit}).",
                        "current_usage": monthly_usage,
                        "limit": limit,
                        "billing_period": candidate_service.get_current_billing_period(),
                        "upgrade_message": "Upgrade your plan for more capacity or wait until next month.",
                    },
                )

        return True, ""

    async def get_monthly_usage(self, user_id: str, db: AsyncSession) -> int:
        """
        Get user's PR analysis usage for current month.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            Number of PR analyses used this month
        """
        # Get start of current month
        now = datetime.now(timezone.utc)
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Query PR analysis records for current month
        result = await db.execute(
            select(func.count(PRAnalysisRecord.id))
            .where(PRAnalysisRecord.user_id == user_id)
            .where(PRAnalysisRecord.created_at >= start_of_month)
        )
        count = result.scalar() or 0
        return count

    async def record_analysis(
        self,
        user_id: str,
        username: str,
        pr_count: int,
        api_calls: int,
        context: str,
        role: str,
        db: AsyncSession,
        analysis_id: Optional[str] = None,
    ) -> None:
        """
        Record PR analysis in database for tracking.

        Args:
            user_id: User ID
            username: GitHub username analyzed
            pr_count: Number of PRs analyzed
            api_calls: Number of API calls used
            context: Analysis context
            role: Role level (junior/mid/senior)
            db: Database session
            analysis_id: Optional analysis result ID to link to
        """
        now = datetime.now(timezone.utc)
        record = PRAnalysisRecord(
            # ID is auto-generated by database (autoincrement)
            user_id=user_id,
            analysis_id=analysis_id,
            github_username=username,
            pr_count=pr_count,
            api_calls_used=api_calls,
            context=context,
            role=role,
            status="completed",  # Analysis is complete by the time we record it
            error_message=None,
            created_at=now,
            completed_at=now,
        )
        db.add(record)
        await db.commit()


# Initialize service
pr_service = PRAnalysisService()


async def run_pr_analysis_background(
    analysis_id: str,
    username: str,
    context: str,
    role: str,
    github_token: str,
    include_all_evidence: bool,
    user_id: str,
    user_subscription_plan: SubscriptionPlan,
) -> None:
    """
    Background task to run PR analysis asynchronously.

    Updates the PRAnalysisResult status as it progresses:
    - PENDING -> PROCESSING -> COMPLETED/FAILED

    Args:
        analysis_id: ID of the PRAnalysisResult record to update
        username: GitHub username to analyze
        context: Organization context
        role: Role level
        github_token: GitHub API token
        include_all_evidence: Whether to include all evidence
        user_id: ID of user requesting analysis
        user_subscription_plan: User's subscription plan
    """
    from sqlalchemy import update

    from ...database.connection import AsyncSessionLocal

    # Create a new database session for the background task
    async with AsyncSessionLocal() as db:
        try:
            # Update status to PROCESSING with initial progress
            await db.execute(
                update(PRAnalysisResult)
                .where(PRAnalysisResult.id == analysis_id)
                .values(
                    status=AnalysisStatus.PROCESSING,
                    progress_stage="starting",
                    progress_percent=10,
                    progress_message="Starting PR analysis...",
                )
            )
            await db.commit()

            logger.info(
                f"Starting background PR analysis for {username} (analysis_id: {analysis_id})"
            )

            # Start timing
            start_time = time.time()

            # Update progress: Fetching PRs
            await db.execute(
                update(PRAnalysisResult)
                .where(PRAnalysisResult.id == analysis_id)
                .values(
                    progress_stage="fetching",
                    progress_percent=20,
                    progress_message=f"Fetching pull requests for {username}...",
                )
            )
            await db.commit()

            # Initialize analyzer
            analyzer = PRAnalyzer(github_token)

            # Perform analysis (in thread to avoid blocking)
            analysis_result = await asyncio.to_thread(
                analyzer.analyze_user,
                username,
                context=context,
            )

            if not analysis_result["success"]:
                error_msg = analysis_result.get(
                    "error", "Unknown error during PR analysis"
                )
                logger.error(f"PR analysis failed for {username}: {error_msg}")

                # Update status to FAILED
                await db.execute(
                    update(PRAnalysisResult)
                    .where(PRAnalysisResult.id == analysis_id)
                    .values(
                        status=AnalysisStatus.FAILED,
                        total_time_seconds=round(time.time() - start_time, 2),
                        progress_stage="failed",
                        progress_percent=0,
                        progress_message=f"Analysis failed: {error_msg}",
                    )
                )
                await db.commit()
                return

            # Update progress: Analysing PRs
            await db.execute(
                update(PRAnalysisResult)
                .where(PRAnalysisResult.id == analysis_id)
                .values(
                    progress_stage="analyzing",
                    progress_percent=60,
                    progress_message="Analysing pull request patterns and code quality...",
                )
            )
            await db.commit()

            # Generate reports
            evidence = analysis_result["evidence"]
            quality_signals = analysis_result["quality_signals"]

            # Update progress: Generating insights
            await db.execute(
                update(PRAnalysisResult)
                .where(PRAnalysisResult.id == analysis_id)
                .values(
                    progress_stage="generating",
                    progress_percent=80,
                    progress_message="Generating AI-powered insights from pull requests...",
                )
            )
            await db.commit()

            summary_report = pr_service.report_generator.generate_summary_report(
                username=username,
                evidence=evidence,
                quality_signals=quality_signals,
                context=context,
                role=role,
            )

            detailed_report = pr_service.report_generator.generate_detailed_report(
                username=username,
                evidence=evidence,
                quality_signals=quality_signals,
                context=context,
                include_all_evidence=include_all_evidence,
                role=role,
            )

            # Generate AI insights if available AND sufficient data
            ai_insights = None
            data_quality = "insufficient"

            total_prs = analysis_result["total_prs"]
            total_changes = getattr(
                quality_signals, "total_changes", 0
            ) or analysis_result.get("total_changes", 0)

            # Data quality assessment
            if total_prs >= 10:
                data_quality = "high"
            elif total_prs >= 5 or total_changes >= 1000:
                data_quality = "moderate"
            else:
                data_quality = "low"

            # Generate AI insights only if we have PR data
            if pr_service.insights_generator and total_prs > 0:
                logger.info(f"Generating AI insights for {username} ({total_prs} PRs)")
                insights_result = pr_service.insights_generator.generate_insights(
                    username=username,
                    evidence=evidence,
                    quality_signals=quality_signals,
                    context=context,
                    tier="scale_plus",
                    repos_contributed=analysis_result.get("repos_contributed", []),
                    role=role,
                )
                if insights_result["success"]:
                    ai_insights = insights_result["insights"]
                    logger.info("AI insights generated successfully")
                else:
                    logger.warning(
                        f"AI insights generation failed: {insights_result.get('error')}"
                    )
            elif total_prs == 0:
                logger.info(f"Skipping AI insights for {username} - no PRs found")
                ai_insights = {
                    "message": "No public pull request activity found for this user.",
                    "suggestion": "Try the Repository Analysis feature to see their public repository contributions, or discuss their development experience directly.",
                }

            # Calculate total time
            total_time = time.time() - start_time

            # Update the existing record with results
            if total_prs > 0:
                await db.execute(
                    update(PRAnalysisResult)
                    .where(PRAnalysisResult.id == analysis_id)
                    .values(
                        status=AnalysisStatus.COMPLETED,
                        total_prs_analyzed=total_prs,
                        full_analysis=json.dumps(
                            {
                                "username": username,
                                "context": context,
                                "total_prs": total_prs,
                                "evidence": (
                                    evidence.get_all_evidence() if evidence else {}
                                ),
                                "quality_signals": (
                                    {
                                        "contribution_timespan": getattr(
                                            quality_signals,
                                            "contribution_timespan",
                                            None,
                                        ),
                                        "monthly_pr_rate": getattr(
                                            quality_signals, "monthly_pr_rate", None
                                        ),
                                        "total_prs": getattr(
                                            quality_signals, "total_prs", 0
                                        ),
                                        "merged_prs": getattr(
                                            quality_signals, "merged_prs", 0
                                        ),
                                        "unique_repos": getattr(
                                            quality_signals, "unique_repos", 0
                                        ),
                                        "feature_prs": getattr(
                                            quality_signals, "feature_prs", 0
                                        ),
                                        "fix_prs": getattr(
                                            quality_signals, "fix_prs", 0
                                        ),
                                        "pair_programming_count": getattr(
                                            quality_signals, "pair_programming_count", 0
                                        ),
                                        "deep_collaboration_count": getattr(
                                            quality_signals,
                                            "deep_collaboration_count",
                                            0,
                                        ),
                                        "feature_ownership_count": getattr(
                                            quality_signals,
                                            "feature_ownership_count",
                                            0,
                                        ),
                                        "contribution_balance": getattr(
                                            quality_signals,
                                            "contribution_balance",
                                            None,
                                        ),
                                        "merge_rate": getattr(
                                            quality_signals, "merge_rate", None
                                        ),
                                    }
                                    if quality_signals
                                    else {}
                                ),
                                "repositories": analysis_result.get(
                                    "repos_contributed", []
                                ),
                                "api_usage": {
                                    "api_calls": analysis_result["api_calls_used"],
                                    "fetch_time": analysis_result.get(
                                        "fetch_time_seconds", 0
                                    ),
                                },
                            }
                        ),
                        summary_report=(
                            json.dumps(summary_report) if summary_report else None
                        ),
                        detailed_report=(
                            json.dumps(detailed_report) if detailed_report else None
                        ),
                        ai_insights=json.dumps(ai_insights) if ai_insights else None,
                        evidence=(
                            json.dumps(evidence.get_all_evidence() if evidence else {})
                            if evidence
                            else None
                        ),
                        quality_signals=(
                            json.dumps(
                                {
                                    "contribution_timespan": getattr(
                                        quality_signals, "contribution_timespan", None
                                    ),
                                    "monthly_pr_rate": getattr(
                                        quality_signals, "monthly_pr_rate", None
                                    ),
                                    "total_prs": getattr(
                                        quality_signals, "total_prs", 0
                                    ),
                                    "merged_prs": getattr(
                                        quality_signals, "merged_prs", 0
                                    ),
                                    "unique_repos": getattr(
                                        quality_signals, "unique_repos", 0
                                    ),
                                    "feature_prs": getattr(
                                        quality_signals, "feature_prs", 0
                                    ),
                                    "fix_prs": getattr(quality_signals, "fix_prs", 0),
                                    "pair_programming_count": getattr(
                                        quality_signals, "pair_programming_count", 0
                                    ),
                                    "deep_collaboration_count": getattr(
                                        quality_signals, "deep_collaboration_count", 0
                                    ),
                                    "feature_ownership_count": getattr(
                                        quality_signals, "feature_ownership_count", 0
                                    ),
                                    "contribution_balance": getattr(
                                        quality_signals, "contribution_balance", None
                                    ),
                                    "merge_rate": getattr(
                                        quality_signals, "merge_rate", None
                                    ),
                                }
                            )
                            if quality_signals
                            else None
                        ),
                        data_quality=data_quality,
                        api_calls_used=analysis_result["api_calls_used"],
                        fetch_time_seconds=analysis_result.get("fetch_time_seconds", 0),
                        total_time_seconds=round(total_time, 2),
                        from_cache=False,
                        # Progress tracking
                        progress_stage="completed",
                        progress_percent=100,
                        progress_message=f"Analysis completed! Analysed {total_prs} pull requests.",
                    )
                )
                await db.commit()

                # Refresh to get updated record
                result = await db.execute(
                    select(PRAnalysisResult).where(PRAnalysisResult.id == analysis_id)
                )
                pr_result = result.scalar_one()

                # Create cache entry
                await create_pr_cache_entry(pr_result, db)

                # Record analysis for usage tracking
                await pr_service.record_analysis(
                    user_id=user_id,
                    username=username,
                    pr_count=total_prs,
                    api_calls=analysis_result["api_calls_used"],
                    context=context,
                    role=role,
                    db=db,
                    analysis_id=analysis_id,
                )

                # Record candidate assessment
                candidate_service = CandidateUsageService(db)
                await candidate_service.get_or_create_assessment(
                    user_id=user_id,
                    github_username=username,
                    analysis_type="pr",
                )

                logger.info(
                    f"Background PR analysis completed for {username} (analysis_id: {analysis_id})"
                )
            else:
                # No PRs found - mark as completed with minimal data
                await db.execute(
                    update(PRAnalysisResult)
                    .where(PRAnalysisResult.id == analysis_id)
                    .values(
                        status=AnalysisStatus.COMPLETED,
                        total_prs_analyzed=0,
                        data_quality="insufficient",
                        total_time_seconds=round(total_time, 2),
                    )
                )
                await db.commit()
                logger.info(
                    f"Background PR analysis completed for {username} - no PRs found (analysis_id: {analysis_id})"
                )

        except Exception as e:
            logger.error(
                f"Error in background PR analysis for {username}: {str(e)}",
                exc_info=True,
            )
            # Update status to FAILED
            try:
                await db.execute(
                    update(PRAnalysisResult)
                    .where(PRAnalysisResult.id == analysis_id)
                    .values(
                        status=AnalysisStatus.FAILED,
                        total_time_seconds=round(time.time() - start_time, 2),
                    )
                )
                await db.commit()
            except Exception as update_error:
                logger.error(
                    f"Failed to update status to FAILED: {str(update_error)}",
                    exc_info=True,
                )


@router.post(
    "/analyze",
    response_model=PRAnalysisResponse,
    summary="Analyze GitHub user's PR history",
    description="Analyze a GitHub user's pull request history. Available for all paid tiers. 1 username = 1 assessment per month.",
)
async def analyze_user_prs(
    request: PRAnalyzeRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> PRAnalysisResponse:
    """
    Analyze a GitHub user's PR history.

    Available for all paid tiers:
    - BASIC: 10 candidates/month
    - PROFESSIONAL: 50 candidates/month
    - SCALE (ENTERPRISE): 200 candidates/month
    - SCALE+: 500 candidates/month

    Counting: 1 GitHub username = 1 candidate assessment per month
    (Applies across both Portfolio and PR analyses)

    Args:
        request: PR analysis request
        user: Authenticated user
        db: Database session

    Returns:
        PR analysis response with evidence and insights

    Raises:
        HTTPException: If user is not eligible or analysis fails
    """
    try:
        # Check user eligibility (tier and monthly quota)
        is_eligible, reason = await pr_service.check_user_eligibility(
            user, request.github_username, db
        )
        if not is_eligible:
            raise HTTPException(status_code=403, detail=reason)

        # Check hourly rate limit
        is_allowed, current_count, limit = await pr_rate_limiter.check_limit(
            user.user_id, user.subscription_plan
        )
        if not is_allowed:
            remaining_time = await pr_rate_limiter.get_remaining_time(user.user_id)
            if remaining_time is not None:
                reset_minutes = remaining_time // 60
                detail = f"Hourly rate limit exceeded ({current_count}/{limit}). Resets in {reset_minutes} minutes."
            else:
                detail = f"Hourly rate limit exceeded ({current_count}/{limit})."
            raise HTTPException(status_code=429, detail=detail)

        # Validate/lock candidate context (ensures consistent evaluation)
        await validate_context(
            db=db,
            username=request.github_username,
            role=request.role,
            organization_context=request.context,
            user_id=user.user_id,
        )

        # Check cache for existing analysis (Storage + Cache Separation)
        cached_analysis = await get_cached_pr_analysis(
            username=request.github_username,
            context=request.context,
            role=request.role,
            db=db,
        )

        if cached_analysis:
            logger.info(
                f"Found cached PR analysis for @{request.github_username}, creating user-specific record"
            )

            # Create a NEW PRAnalysisResult record for THIS user pointing to cached data
            # This ensures each user gets their own unique URL while benefiting from cached data
            new_analysis_id = str(uuid.uuid4())

            # Create new analysis result with same data but new ID
            user_analysis = PRAnalysisResult(
                id=new_analysis_id,
                github_username=cached_analysis.github_username,
                context=cached_analysis.context,
                role=cached_analysis.role,
                total_prs_analyzed=cached_analysis.total_prs_analyzed,
                full_analysis=cached_analysis.full_analysis,  # Same data as cache
                summary_report=cached_analysis.summary_report,
                detailed_report=cached_analysis.detailed_report,
                ai_insights=cached_analysis.ai_insights,
                evidence=cached_analysis.evidence,
                quality_signals=cached_analysis.quality_signals,
                data_quality=cached_analysis.data_quality,
                api_calls_used=0,  # User didn't make API calls (cached)
                fetch_time_seconds=0.0,  # Minimal time to retrieve from cache
                total_time_seconds=0.0,  # Same for cached results
                from_cache=True,  # Mark as from cache
            )

            db.add(user_analysis)
            await db.commit()
            await db.refresh(user_analysis)

            logger.info(
                f"Created user-specific PR analysis record {new_analysis_id} from cache for user {user.user_id}"
            )

            # Record usage tracking for this cached access with NEW analysis ID
            await pr_service.record_analysis(
                user_id=user.user_id,
                username=request.github_username,
                pr_count=cached_analysis.total_prs_analyzed,
                context=request.context,
                role=request.role,
                db=db,
                api_calls=0,  # Cached - no API calls
                analysis_id=new_analysis_id,  # Use NEW analysis ID for this user
            )

            # Record candidate assessment
            candidate_service = CandidateUsageService(db)
            await candidate_service.get_or_create_assessment(
                user_id=user.user_id,
                github_username=request.github_username,
                analysis_type="pr",
            )

            # Return user's own analysis (not cached_analysis)
            return format_pr_analysis_response(user_analysis, from_cache=True)

        logger.info(
            f"Starting ASYNC PR analysis for GitHub user: {request.github_username} "
            f"(requested by {user.email}, context: {request.context})"
        )

        # Validate GitHub token
        github_token = request.github_token or config.github_token
        if not github_token:
            raise HTTPException(
                status_code=400,
                detail="GitHub token is required for PR analysis. "
                "Please provide a token or configure one in settings.",
            )

        # Create PRAnalysisResult record with PENDING status immediately
        analysis_id = str(uuid.uuid4())
        pr_result = PRAnalysisResult(
            id=analysis_id,
            github_username=request.github_username,
            context=request.context,
            role=request.role,
            total_prs_analyzed=0,  # Will be updated by background task
            full_analysis="{}",  # Empty JSON for PENDING status
            data_quality="insufficient",  # Will be updated by background task
            api_calls_used=0,
            fetch_time_seconds=0.0,
            status=AnalysisStatus.PENDING,
            from_cache=False,
        )
        db.add(pr_result)
        await db.commit()
        await db.refresh(pr_result)

        logger.info(
            f"Created PENDING PR analysis record {analysis_id} for {request.github_username}"
        )

        # Create PRAnalysisRecord immediately so GET endpoint can find it
        from ...database.models import PRAnalysisRecord

        pr_record = PRAnalysisRecord(
            user_id=user.user_id,
            github_username=request.github_username,
            analysis_id=analysis_id,
            role=request.role,
            pr_count=0,  # Will be updated by background task
            api_calls_used=0,  # Will be updated by background task
            context=request.context,  # Required NOT NULL field
            status="pending",  # Mark as pending
        )
        db.add(pr_record)
        await db.commit()

        logger.info(
            f"Created PRAnalysisRecord for user {user.user_id}, analysis {analysis_id}"
        )

        # Launch background task to perform actual analysis
        background_tasks.add_task(
            run_pr_analysis_background,
            analysis_id=analysis_id,
            username=request.github_username,
            context=request.context,
            role=request.role,
            github_token=github_token,
            include_all_evidence=request.include_all_evidence,
            user_id=user.user_id,
            user_subscription_plan=user.subscription_plan,
        )

        # Calculate remaining analyses using candidate service
        candidate_service = CandidateUsageService(db)
        monthly_usage = await candidate_service.get_monthly_usage(user.user_id)
        limit = CandidateUsageService.get_tier_limit(user.subscription_plan)
        remaining = limit - monthly_usage

        # Return immediately with PENDING status and analysis_id
        # Frontend will poll GET /api/v1/pr/{analysis_id} to check status
        logger.info(
            f"Returning PENDING PR analysis {analysis_id} - processing in background"
        )

        return PRAnalysisResponse(
            analysis_id=analysis_id,
            username=request.github_username,
            context=request.context,
            total_prs_analyzed=0,  # Will be updated when complete
            repositories_contributed=[],
            summary_report="",  # Will be populated when complete
            detailed_report={},
            ai_insights=None,
            data_quality="insufficient",  # Will be updated when complete
            ai_insights_available=False,
            api_calls_used=0,
            fetch_time_seconds=0,
            total_time_seconds=0,
            from_cache=False,
            remaining_analyses_this_month=remaining,
            monthly_limit=limit,
            status="pending",  # NEW: indicate this is still processing
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in PR analysis: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred during PR analysis: {str(e)}",
        )


@router.get(
    "/",
    summary="List PR analyses for current user",
    description="Get all PR analyses for the authenticated user.",
)
async def list_pr_analyses(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
    skip: int = 0,
    limit: int = 50,
) -> Dict[str, Any]:
    """List all PR analyses for the current user."""
    import json

    from ...database.models import PRAnalysisResult

    # Get PR analyses for current user by joining with PRAnalysisRecord on analysis_id
    result = await db.execute(
        select(PRAnalysisResult)
        .join(PRAnalysisRecord, PRAnalysisResult.id == PRAnalysisRecord.analysis_id)
        .where(PRAnalysisRecord.user_id == user.user_id)
        .order_by(PRAnalysisResult.created_at.desc())
        .offset(skip)
        .limit(limit)
        .distinct()
    )
    analyses = result.scalars().all()

    return {
        "analyses": [
            {
                "id": analysis.id,
                "github_username": analysis.github_username,
                "context": analysis.context,
                "total_prs_analyzed": analysis.total_prs_analyzed,
                "data_quality": analysis.data_quality,
                "created_at": analysis.created_at.isoformat(),
                "from_cache": analysis.from_cache,
                # Extract executive_summary from ai_insights for preview
                "executive_summary": (
                    json.loads(analysis.ai_insights).get("executive_summary", "")
                    if analysis.ai_insights
                    else ""
                ),
                # Count repositories
                "repositories_count": (
                    len(json.loads(analysis.full_analysis).get("repositories", []))
                    if analysis.full_analysis
                    else 0
                ),
            }
            for analysis in analyses
        ],
        "total": len(analyses),
        "skip": skip,
        "limit": limit,
    }


@router.get(
    "/usage",
    summary="Get PR analysis usage statistics",
    description="Get current month's candidate assessment usage (PR + Portfolio combined).",
)
async def get_pr_analysis_usage(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Get user's candidate assessment usage statistics.

    Returns combined usage across Portfolio and PR analyses.
    """
    # Check if user is eligible
    is_eligible = user.subscription_plan in PR_ANALYSIS_TIERS

    if not is_eligible:
        tier_name = get_frontend_tier_name(user.subscription_plan.value)
        return {
            "eligible": False,
            "message": f"PR Analysis is available for paid plans. Current plan: {tier_name}",
            "current_plan": tier_name,
            "required_plan": "BASIC or higher",
        }

    # Get usage statistics from candidate service
    candidate_service = CandidateUsageService(db)
    monthly_usage = await candidate_service.get_monthly_usage(user.user_id)
    limit = CandidateUsageService.get_tier_limit(user.subscription_plan)
    remaining = limit - monthly_usage

    # Get hourly rate limit stats
    rate_limit_stats = await pr_rate_limiter.get_usage_stats(
        user.user_id, user.subscription_plan
    )

    # Calculate reset date (first day of next month)
    now = datetime.now(timezone.utc)
    if now.month == 12:
        reset_date = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        reset_date = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)

    days_until_reset = (reset_date - now).days

    return {
        "eligible": True,
        "used_this_month": monthly_usage,
        "remaining_this_month": remaining,
        "monthly_limit": limit,
        "reset_date": reset_date.isoformat(),
        "days_until_reset": days_until_reset,
        "hourly_limit": rate_limit_stats["hourly_limit"],
        "used_this_hour": rate_limit_stats["current_hour_usage"],
        "remaining_this_hour": rate_limit_stats["remaining_this_hour"],
        "hour_resets_in_minutes": rate_limit_stats["resets_in_minutes"],
        "current_plan": get_frontend_tier_name(user.subscription_plan.value),
        "note": "1 GitHub username = 1 candidate assessment (applies to both Portfolio and PR analyses)",
    }


@router.get(
    "/history",
    summary="Get PR analysis history",
    description="Get user's PR analysis history for current month.",
)
async def get_pr_analysis_history(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(10, ge=1, le=50, description="Number of records to return"),
) -> Dict[str, Any]:
    """
    Get user's PR analysis history.

    Args:
        user: Authenticated user
        db: Database session
        limit: Number of records to return

    Returns:
        Dictionary with analysis history
    """
    # Check if user is eligible
    if user.subscription_plan not in PR_ANALYSIS_TIERS:
        raise HTTPException(
            status_code=403,
            detail="PR Analysis history is available for paid plans only.",
        )

    # Get analysis history for current month
    now = datetime.now(timezone.utc)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    result = await db.execute(
        select(PRAnalysisRecord)
        .where(PRAnalysisRecord.user_id == user.user_id)
        .where(PRAnalysisRecord.created_at >= start_of_month)
        .order_by(PRAnalysisRecord.created_at.desc())
        .limit(limit)
    )
    records = result.scalars().all()

    # Format history
    history = [
        {
            "github_username": record.github_username,
            "pr_count": record.pr_count,
            "api_calls_used": record.api_calls_used,
            "context": record.context,
            "analyzed_at": record.created_at.isoformat(),
        }
        for record in records
    ]

    return {
        "history": history,
        "total_records": len(history),
        "period": "current_month",
        "start_date": start_of_month.isoformat(),
    }


@router.get(
    "/{analysis_id}",
    summary="Get PR analysis result by ID",
    description="Retrieve a stored PR analysis result by its ID.",
)
async def get_pr_analysis_by_id(
    analysis_id: str,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """Get PR analysis result by ID - requires authentication for security."""
    import json

    from ...database.models import PRAnalysisResult

    logger.info(f"Fetching PR analysis with ID: {analysis_id} for user: {user.user_id}")

    # SECURITY: Verify ownership by joining with PRAnalysisRecord
    # Also fetch the PRAnalysisRecord to get the role
    result = await db.execute(
        select(PRAnalysisResult, PRAnalysisRecord)
        .join(PRAnalysisRecord, PRAnalysisResult.id == PRAnalysisRecord.analysis_id)
        .where(PRAnalysisResult.id == analysis_id)
        .where(PRAnalysisRecord.user_id == user.user_id)
    )
    row = result.first()

    if not row:
        pr_analysis = None
        pr_record = None
    else:
        pr_analysis, pr_record = row

    if not pr_analysis:
        logger.warning(
            f"PR analysis not found or unauthorized for ID: {analysis_id}, user: {user.user_id}"
        )
        raise HTTPException(
            status_code=404,
            detail="PR analysis not found or you don't have permission to access it",
        )

    # Get portfolio analysis info for this username
    portfolio_info = await get_portfolio_analysis_info(pr_analysis.github_username, db)

    # Extract repositories from full_analysis if available
    repositories_contributed = []
    if pr_analysis.full_analysis:
        try:
            full_data = json.loads(pr_analysis.full_analysis)
            # Try both field names for backwards compatibility
            repositories_contributed = full_data.get(
                "repos_contributed", []
            ) or full_data.get("repositories", [])
        except (json.JSONDecodeError, TypeError):
            pass

    # Transform evidence to evidence patterns for Evidence tab display
    evidence_patterns = []
    if pr_analysis.evidence and pr_analysis.quality_signals:
        try:
            evidence_data = json.loads(pr_analysis.evidence)
            quality_signals_data = json.loads(pr_analysis.quality_signals)

            # Reconstruct evidence and quality signals objects
            evidence = PREvidence()
            for key, value in evidence_data.items():
                if hasattr(evidence, key):
                    setattr(evidence, key, value)

            quality_signals = QualitySignals()
            for key, value in quality_signals_data.items():
                # Skip properties that are computed from other fields
                if key in ["contribution_balance", "merge_rate"]:
                    continue
                if hasattr(quality_signals, key):
                    setattr(quality_signals, key, value)

            # Transform to evidence patterns
            extractor = PREvidenceExtractor()
            evidence_patterns = extractor.transform_to_evidence_patterns(
                evidence, quality_signals
            )

        except (json.JSONDecodeError, TypeError, AttributeError) as e:
            logger.warning(f"Failed to transform evidence to patterns: {e}")
            evidence_patterns = []

    # Return the stored analysis
    return {
        "analysis_id": pr_analysis.id,
        "username": pr_analysis.github_username,
        "context": pr_analysis.context,
        "role": pr_record.role if pr_record and pr_record.role else "mid",
        "total_prs_analyzed": pr_analysis.total_prs_analyzed,
        "repositories_contributed": repositories_contributed,
        "summary_report": (
            json.loads(pr_analysis.summary_report)
            if pr_analysis.summary_report
            else None
        ),
        "detailed_report": (
            json.loads(pr_analysis.detailed_report)
            if pr_analysis.detailed_report
            else None
        ),
        "ai_insights": (
            json.loads(pr_analysis.ai_insights) if pr_analysis.ai_insights else None
        ),
        "evidence": json.loads(pr_analysis.evidence) if pr_analysis.evidence else {},
        "evidence_patterns": evidence_patterns,  # NEW: Evidence patterns for Evidence tab
        "quality_signals": (
            json.loads(pr_analysis.quality_signals)
            if pr_analysis.quality_signals
            else {}
        ),
        "data_quality": pr_analysis.data_quality,
        "api_calls_used": pr_analysis.api_calls_used,
        "fetch_time_seconds": pr_analysis.fetch_time_seconds,
        "total_time_seconds": pr_analysis.total_time_seconds,
        "from_cache": pr_analysis.from_cache,
        "created_at": pr_analysis.created_at.isoformat(),
        "status": pr_analysis.status.value if pr_analysis.status else "completed",
        # Progress tracking (for async background processing)
        "progress_stage": pr_analysis.progress_stage,
        "progress_percent": pr_analysis.progress_percent,
        "progress_message": pr_analysis.progress_message,
        # Portfolio analysis info - always show card (either to run or view analysis)
        "repos_analyzed": portfolio_info.get("repos_analyzed", 0),
        "has_portfolio_analysis": portfolio_info.get("has_portfolio_analysis", False),
        "portfolio_analysis_id": portfolio_info.get("portfolio_analysis_id"),
        "show_portfolio_card": portfolio_info.get("show_portfolio_card", False),
    }


# Helper functions for formatting and cache management


async def get_portfolio_analysis_info(
    username: str, db: AsyncSession
) -> Dict[str, Any]:
    """
    Get portfolio analysis information for this username.

    Returns dict with:
    - repos_analyzed: Number of repos analyzed
    - has_portfolio_analysis: Whether portfolio analysis exists
    - portfolio_analysis_id: ID of existing analysis
    - show_portfolio_card: Always True (show card to run or view analysis)

    Args:
        username: GitHub username
        db: Database session
    """
    from ...database.models_portfolio import PortfolioAnalysis

    try:
        result = await db.execute(
            select(PortfolioAnalysis)
            .where(PortfolioAnalysis.github_username == username)
            .order_by(PortfolioAnalysis.created_at.desc())
            .limit(1)
        )
        existing_portfolio = result.scalar_one_or_none()

        if existing_portfolio:
            # Portfolio analysis exists - show card to view it
            return {
                "repos_analyzed": existing_portfolio.repos_analyzed or 0,
                "has_portfolio_analysis": True,
                "portfolio_analysis_id": existing_portfolio.id,
                "show_portfolio_card": True,
            }
        else:
            # No portfolio analysis - show card to run it
            return {
                "repos_analyzed": 0,
                "has_portfolio_analysis": False,
                "portfolio_analysis_id": None,
                "show_portfolio_card": True,
            }

    except Exception as e:
        logger.warning(f"Failed to check portfolio analysis for {username}: {e}")
        return {
            "repos_analyzed": 0,
            "has_portfolio_analysis": False,
            "portfolio_analysis_id": None,
            "show_portfolio_card": False,
        }


def format_pr_analysis_response(
    pr_analysis: PRAnalysisResult, from_cache: bool
) -> PRAnalysisResponse:
    """
    Format PR analysis result for API response.

    Args:
        pr_analysis: PR analysis database record
        from_cache: Whether this is from cache

    Returns:
        Formatted PRAnalysisResponse
    """
    # Parse full analysis
    full_data = (
        json.loads(pr_analysis.full_analysis) if pr_analysis.full_analysis else {}
    )

    # Extract components
    summary_report = (
        json.loads(pr_analysis.summary_report) if pr_analysis.summary_report else None
    )
    detailed_report = (
        json.loads(pr_analysis.detailed_report) if pr_analysis.detailed_report else None
    )
    ai_insights = (
        json.loads(pr_analysis.ai_insights) if pr_analysis.ai_insights else None
    )

    return PRAnalysisResponse(
        analysis_id=pr_analysis.id,
        username=pr_analysis.github_username,
        context=pr_analysis.context,
        total_prs_analyzed=pr_analysis.total_prs_analyzed,
        repositories_contributed=full_data.get("repositories", []),
        summary_report=summary_report or "",
        detailed_report=detailed_report or {},
        ai_insights=ai_insights,
        data_quality=pr_analysis.data_quality,
        ai_insights_available=ai_insights is not None,
        api_calls_used=pr_analysis.api_calls_used,
        fetch_time_seconds=pr_analysis.fetch_time_seconds,
        total_time_seconds=pr_analysis.total_time_seconds or 0,
        from_cache=from_cache,
        remaining_analyses_this_month=0,  # Will be set by caller if needed
        monthly_limit=0,  # Will be set by caller if needed
        status=pr_analysis.status.value if pr_analysis.status else "completed",
    )


async def get_cached_pr_analysis(
    username: str, context: str, role: str, db: AsyncSession
) -> Optional[PRAnalysisResult]:
    """
    Get cached PR analysis if available and not expired.

    Storage + Cache Separation:
    - Checks PRAnalysisCache table (not PRAnalysisResult)
    - Returns linked PRAnalysisResult from storage
    - Cache is shared across all users for same (username, context, role)
    - Prevents duplicate analyses when multiple hiring managers evaluate same candidate

    Args:
        username: GitHub username
        context: Analysis context
        role: Role level for interview questions (junior, mid, senior)
        db: Database session

    Returns:
        Cached analysis or None (regardless of which user created it)
    """
    now = datetime.now(timezone.utc)

    # Check cache table (not result table)
    result = await db.execute(
        select(PRAnalysisCache)
        .where(PRAnalysisCache.github_username == username)
        .where(PRAnalysisCache.context == context)
        .where(PRAnalysisCache.role == role)
        .where(PRAnalysisCache.cache_expires_at > now)
        .order_by(PRAnalysisCache.created_at.desc())
        .limit(1)
    )

    cache_entry = result.scalar_one_or_none()

    if not cache_entry:
        return None

    # Fetch the linked result from storage
    result_query = await db.execute(
        select(PRAnalysisResult).where(PRAnalysisResult.id == cache_entry.result_id)
    )

    return result_query.scalar_one_or_none()


async def create_pr_cache_entry(
    analysis: PRAnalysisResult, db: AsyncSession, max_retries: int = 3
) -> bool:
    """
    Create cache entry for PR analysis with deduplication.

    Handles race conditions via UNIQUE constraint and retry logic.
    If multiple users analyze same candidate simultaneously, only one
    cache entry is created (database enforces uniqueness).

    Args:
        analysis: PR analysis result to cache
        db: Database session
        max_retries: Maximum number of retries on UNIQUE constraint violation

    Returns:
        True if cache entry created successfully (or already exists)
    """
    cache_expiry = datetime.now(timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    ) + __import__("dateutil.relativedelta").relativedelta.relativedelta(
        months=1
    )  # Next month (30-day TTL)

    for attempt in range(max_retries):
        try:
            cache_entry = PRAnalysisCache(
                id=str(uuid.uuid4()),
                result_id=analysis.id,
                github_username=analysis.github_username,
                context=analysis.context,
                role=analysis.role,
                cache_expires_at=cache_expiry,
            )

            db.add(cache_entry)
            await db.commit()

            logger.info(
                f"Created cache entry for PR analysis: {analysis.id} "
                f"(@{analysis.github_username}, {analysis.context}, {analysis.role})"
            )
            return True

        except IntegrityError as e:
            # UNIQUE constraint violation - cache entry already exists
            await db.rollback()

            if "uq_pr_cache_context" in str(e).lower():
                logger.info(
                    f"Cache entry already exists for @{analysis.github_username}, "
                    f"{analysis.context}, {analysis.role} (attempt {attempt + 1}/{max_retries})"
                )

                # Check if existing cache points to our result (race condition resolved)
                result = await db.execute(
                    select(PRAnalysisCache)
                    .where(PRAnalysisCache.github_username == analysis.github_username)
                    .where(PRAnalysisCache.context == analysis.context)
                    .where(PRAnalysisCache.role == analysis.role)
                )
                existing_cache = result.scalar_one_or_none()

                if existing_cache and existing_cache.result_id == analysis.id:
                    logger.info("Existing cache already points to our result")
                    return True

                # Another user's analysis won the race - that's fine
                logger.info("Another analysis won the cache race - using their result")
                return True
            else:
                # Some other integrity error
                logger.error(f"Unexpected IntegrityError creating cache entry: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff
                    continue
                return False

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating cache entry: {e}", exc_info=True)
            if attempt < max_retries - 1:
                await asyncio.sleep(0.1 * (attempt + 1))
                continue
            return False

    return False
