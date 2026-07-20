# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Portfolio Analysis API endpoints.

Provides REST API endpoints for GitHub portfolio analysis functionality.
Available for all paid tiers with candidate-based counting (1 username = 1 assessment/month).
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.tier_utils import get_frontend_tier_name
from ...data.portfolio_analyzer import PortfolioAnalyzer
from ...database.connection import get_db_session
from ...database.models import AnalysisStatus, SubscriptionPlan, User
from ...database.models_portfolio import PortfolioAnalysis, PortfolioAnalysisCache
from ...services.candidate_usage_service import CandidateUsageService
from ...utils.config import get_config
from ...utils.logging import get_logger
from ..auth.dependencies import get_current_active_user
from ..models.portfolio_requests import PortfolioAnalyzeRequest
from ..services.candidate_context import validate_context

logger = get_logger(__name__)
config = get_config()

router = APIRouter(prefix="/portfolio", tags=["Portfolio Analysis"])

# Portfolio analysis is available for all paid tiers
PORTFOLIO_ANALYSIS_TIERS = [
    SubscriptionPlan.BASIC,
    SubscriptionPlan.PROFESSIONAL,
    SubscriptionPlan.ENTERPRISE,  # Backend name (frontend: "Scale")
    SubscriptionPlan.SCALE_PLUS,
]


async def check_user_eligibility(
    user: User, username: str, db: AsyncSession
) -> tuple[bool, str | dict[str, Any]]:
    """
    Check if user is eligible for portfolio analysis.

    Args:
        user: User object
        username: GitHub username to analyze
        db: Database session

    Returns:
        Tuple of (is_eligible, reason_if_not)
    """
    # Check tier eligibility (all paid tiers)
    if user.subscription_plan not in PORTFOLIO_ANALYSIS_TIERS:
        tier_name = get_frontend_tier_name(user.subscription_plan.value)
        return (
            False,
            f"Portfolio Analysis is available for paid plans. "
            f"Your current plan: {tier_name}. Upgrade to access this feature.",
        )

    # Check if this username would count as new assessment
    candidate_service = CandidateUsageService(db)
    assessment, is_new = await candidate_service.get_or_create_assessment(
        user_id=user.user_id,
        github_username=username,
        analysis_type="portfolio",
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


async def run_portfolio_analysis_background(
    analysis_id: str,
    username: str,
    context: str,
    role: str,
    github_token: str,
    max_repos: int,
    force_refresh: bool,
    user_id: str,
    user_email: str,
    user_subscription_plan: SubscriptionPlan,
) -> None:
    """
    Background task to run portfolio analysis asynchronously.

    This prevents HTTP timeouts for long-running analyses (2-4 minutes).
    Updates analysis status from PENDING -> PROCESSING -> COMPLETED/FAILED.
    """
    from ...database.connection import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            # Update status to PROCESSING with initial progress
            await db.execute(
                update(PortfolioAnalysis)
                .where(PortfolioAnalysis.id == analysis_id)
                .values(
                    status=AnalysisStatus.PROCESSING,
                    progress_stage="starting",
                    progress_percent=10,
                    progress_message="Starting portfolio analysis...",
                )
            )
            await db.commit()

            logger.info(
                f"Background portfolio analysis PROCESSING for {username} "
                f"(analysis_id: {analysis_id}, user: {user_email})"
            )

            # Check for cached analysis (30-day TTL)
            if not force_refresh:
                cached_analysis = await get_cached_analysis(username, context, role, db)
                if cached_analysis:
                    logger.info(
                        f"Found cached portfolio analysis for {username} in background task"
                    )

                    # Update the existing PENDING record with cached data
                    await db.execute(
                        update(PortfolioAnalysis)
                        .where(PortfolioAnalysis.id == analysis_id)
                        .values(
                            total_repos=cached_analysis.total_repos,
                            repos_analyzed=cached_analysis.repos_analyzed,
                            repos_skipped=cached_analysis.repos_skipped,
                            full_analysis=cached_analysis.full_analysis,
                            s3_key=cached_analysis.s3_key,
                            analysis_metadata=cached_analysis.analysis_metadata,
                            processing_time_seconds=cached_analysis.processing_time_seconds,
                            token_count=cached_analysis.token_count,
                            api_cost=cached_analysis.api_cost,
                            api_calls_used=0,
                            from_cache=True,
                            cache_expires_at=cached_analysis.cache_expires_at,
                            key_observations_count=cached_analysis.key_observations_count,
                            evidence_patterns_count=cached_analysis.evidence_patterns_count,
                            interview_questions_count=cached_analysis.interview_questions_count,
                            timeline_gaps_count=cached_analysis.timeline_gaps_count,
                            analysis_version=cached_analysis.analysis_version,
                            data_quality=cached_analysis.data_quality,
                            allow_training=False,
                            status=AnalysisStatus.COMPLETED,
                        )
                    )
                    await db.commit()

                    logger.info(
                        f"Updated analysis {analysis_id} from cache, status=COMPLETED"
                    )
                    return

            # Initialize portfolio analyzer
            if not config.anthropic_api_key:
                raise Exception(
                    "Portfolio analysis requires AI insights but no Anthropic API key is configured."
                )

            analyzer = PortfolioAnalyzer(github_token, config.anthropic_api_key)

            # Update progress: Fetching repositories
            await db.execute(
                update(PortfolioAnalysis)
                .where(PortfolioAnalysis.id == analysis_id)
                .values(
                    progress_stage="fetching",
                    progress_percent=20,
                    progress_message=f"Fetching public repositories for {username}...",
                )
            )
            await db.commit()

            # Perform analysis in thread to avoid blocking
            logger.info(
                f"Starting portfolio analysis for {username} (max {max_repos} repos)"
            )

            analysis_result = await asyncio.to_thread(
                analyzer.analyze_portfolio,
                username=username,
                context=context,
                tier=user_subscription_plan.value,
                max_repos=max_repos,
                role=role,
            )

            if not analysis_result["success"]:
                error_msg = analysis_result.get(
                    "error", "Unknown error during portfolio analysis"
                )
                logger.error(f"Portfolio analysis failed: {error_msg}")

                # Update status to FAILED
                await db.execute(
                    update(PortfolioAnalysis)
                    .where(PortfolioAnalysis.id == analysis_id)
                    .values(
                        status=AnalysisStatus.FAILED,
                        progress_stage="failed",
                        progress_percent=0,
                        progress_message=f"Analysis failed: {error_msg}",
                    )
                )
                await db.commit()
                return

            # Update progress: Analysing patterns
            await db.execute(
                update(PortfolioAnalysis)
                .where(PortfolioAnalysis.id == analysis_id)
                .values(
                    progress_stage="analyzing",
                    progress_percent=60,
                    progress_message="Analysing technical patterns and code quality...",
                )
            )
            await db.commit()

            # Prepare analysis data
            result_dict = analysis_result["result"]
            metadata = analysis_result["metadata"]

            # Update progress: Generating insights
            await db.execute(
                update(PortfolioAnalysis)
                .where(PortfolioAnalysis.id == analysis_id)
                .values(
                    progress_stage="generating",
                    progress_percent=80,
                    progress_message="Generating AI-powered insights and interview questions...",
                )
            )
            await db.commit()

            # Update analysis with COMPLETED status and results
            await db.execute(
                update(PortfolioAnalysis)
                .where(PortfolioAnalysis.id == analysis_id)
                .values(
                    # Repository counts
                    total_repos=metadata.total_public_repos,
                    repos_analyzed=metadata.repos_analyzed,
                    repos_skipped=metadata.repos_skipped,
                    # Full analysis (JSON)
                    full_analysis=json.dumps(
                        {
                            "username": username,
                            "context": context,
                            "result": result_dict,
                            "evidence": analysis_result["evidence"],
                            "metadata": {
                                "total_public_repos": metadata.total_public_repos,
                                "repos_analyzed": metadata.repos_analyzed,
                                "repos_skipped": metadata.repos_skipped,
                                "skip_counts": metadata.skip_counts,
                                "analyzed_repos": metadata.analyzed_repos,
                                "skipped_repos": metadata.skipped_repos,
                                "oldest_repo": metadata.oldest_repo,
                                "newest_repo": metadata.newest_repo,
                                "timeline_gaps": metadata.timeline_gaps,
                            },
                        }
                    ),
                    # Analysis metadata
                    analysis_metadata=json.dumps(
                        {
                            "repo_count": metadata.repos_analyzed,
                            "token_count": metadata.tokens,
                            "api_cost": metadata.cost,
                            "repos_skipped": metadata.repos_skipped,
                            "total_public_repos": metadata.total_public_repos,
                            "oldest_repo": metadata.oldest_repo,
                            "newest_repo": metadata.newest_repo,
                        }
                    ),
                    # Performance metrics
                    processing_time_seconds=analysis_result[
                        "total_analysis_time_seconds"
                    ],
                    token_count=metadata.tokens,
                    api_cost=metadata.cost,
                    # Cache tracking
                    from_cache=False,
                    cache_expires_at=datetime.now(timezone.utc).replace(
                        day=1, hour=0, minute=0, second=0, microsecond=0
                    )
                    + __import__("dateutil.relativedelta").relativedelta.relativedelta(
                        months=1
                    ),
                    # Analysis results summary
                    key_observations_count=len(result_dict.get("observations") or []),
                    evidence_patterns_count=len(
                        result_dict.get("evidence_patterns") or []
                    ),
                    interview_questions_count=len(
                        result_dict.get("interview_questions") or []
                    ),
                    timeline_gaps_count=metadata.timeline_gaps,
                    # Data quality
                    data_quality=result_dict.get("data_quality", "limited"),
                    # Status and progress
                    status=AnalysisStatus.COMPLETED,
                    progress_stage="completed",
                    progress_percent=100,
                    progress_message=f"Analysis completed! Analysed {metadata.repos_analyzed} repositories.",
                )
            )
            await db.commit()

            logger.info(
                f"Portfolio analysis COMPLETED for {username} "
                f"(analysis_id: {analysis_id}, {metadata.repos_analyzed} repos)"
            )

            # Fetch the updated analysis for cache creation
            result = await db.execute(
                select(PortfolioAnalysis).where(PortfolioAnalysis.id == analysis_id)
            )
            portfolio_analysis = result.scalar_one()

            # Create cache entry
            await create_cache_entry(portfolio_analysis, db)

            # Record candidate assessment
            candidate_service = CandidateUsageService(db)
            await candidate_service.get_or_create_assessment(
                user_id=user_id,
                github_username=username,
                analysis_type="portfolio",
            )

        except Exception as e:
            logger.error(
                f"Background portfolio analysis failed for {username}: {str(e)}",
                exc_info=True,
            )

            # Update status to FAILED
            try:
                await db.execute(
                    update(PortfolioAnalysis)
                    .where(PortfolioAnalysis.id == analysis_id)
                    .values(status=AnalysisStatus.FAILED)
                )
                await db.commit()
            except Exception as update_error:
                logger.error(
                    f"Failed to update analysis status to FAILED: {str(update_error)}"
                )


@router.post(
    "/analyze",
    summary="Analyze GitHub developer's portfolio",
    description="Analyze a developer's GitHub portfolio. Available for all paid tiers. 1 username = 1 assessment per month.",
)
async def analyze_portfolio(
    request: PortfolioAnalyzeRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Analyze a developer's GitHub portfolio (async with background processing).

    Available for all paid tiers:
    - BASIC: 10 candidates/month
    - PROFESSIONAL: 50 candidates/month
    - SCALE (ENTERPRISE): 200 candidates/month
    - SCALE+: 500 candidates/month

    Counting: 1 GitHub username = 1 candidate assessment per month
    (Applies across both Portfolio and PR analyses)

    Returns immediately with status='pending', processes analysis in background.
    Frontend polls GET endpoint to check status.

    Args:
        request: Portfolio analysis request
        background_tasks: FastAPI background tasks
        user: Authenticated user
        db: Database session

    Returns:
        Portfolio analysis response with analysis_id and status='pending'

    Raises:
        HTTPException: If user is not eligible
    """
    try:
        # Check user eligibility (tier and monthly quota)
        is_eligible, reason = await check_user_eligibility(
            user, request.github_username, db
        )
        if not is_eligible:
            raise HTTPException(status_code=403, detail=reason)

        # Validate/lock candidate context (ensures consistent evaluation)
        await validate_context(
            db=db,
            username=request.github_username,
            role=request.role,
            organization_context=request.context,
            user_id=user.user_id,
        )

        # Validate GitHub token
        github_token = request.github_token or config.github_token
        if not github_token:
            raise HTTPException(
                status_code=400,
                detail="GitHub token is required for portfolio analysis. "
                "Please provide a token or configure one in settings.",
            )

        logger.info(
            f"Starting ASYNC portfolio analysis for GitHub user: {request.github_username} "
            f"(requested by {user.email}, context: {request.context}, tier: {user.subscription_plan.value})"
        )

        # Create PortfolioAnalysis record with PENDING status immediately
        analysis_id = str(uuid.uuid4())

        portfolio_analysis = PortfolioAnalysis(
            id=analysis_id,
            user_id=user.user_id,
            github_username=request.github_username,
            context=request.context,
            role=request.role,
            total_repos=0,
            repos_analyzed=0,
            repos_skipped=0,
            full_analysis="{}",  # Empty JSON for PENDING status
            analysis_metadata="{}",  # Empty JSON for PENDING status
            processing_time_seconds=0.0,
            token_count=0,
            api_cost=0.0,
            api_calls_used=0,
            key_observations_count=0,
            evidence_patterns_count=0,
            interview_questions_count=0,
            timeline_gaps_count=0,
            data_quality="insufficient",  # Will be updated by background task
            status=AnalysisStatus.PENDING,
            from_cache=False,
        )

        db.add(portfolio_analysis)
        await db.commit()

        logger.info(
            f"Created PENDING portfolio analysis record {analysis_id}, "
            f"launching background task"
        )

        # Launch background task to perform analysis
        background_tasks.add_task(
            run_portfolio_analysis_background,
            analysis_id=analysis_id,
            username=request.github_username,
            context=request.context,
            role=request.role,
            github_token=github_token,
            max_repos=request.max_repos,
            force_refresh=request.force_refresh,
            user_id=user.user_id,
            user_email=user.email,
            user_subscription_plan=user.subscription_plan,
        )

        # Return immediately with PENDING status
        return {
            "id": analysis_id,
            "analysis_id": analysis_id,
            "github_username": request.github_username,
            "username": request.github_username,
            "context": request.context,
            "role": request.role,
            "status": "pending",
            "message": "Portfolio analysis started. Use the analysis_id to poll for results.",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error starting portfolio analysis: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred starting portfolio analysis: {str(e)}",
        )


@router.get(
    "/",
    summary="List portfolio analyses for current user",
    description="Get all portfolio analyses for the authenticated user.",
)
async def list_portfolio_analyses(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
    skip: int = 0,
    limit: int = 50,
) -> Dict[str, Any]:
    """List all portfolio analyses for the current user."""
    # Get portfolio analyses for current user
    result = await db.execute(
        select(PortfolioAnalysis)
        .where(PortfolioAnalysis.user_id == user.user_id)
        .order_by(PortfolioAnalysis.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    analyses = result.scalars().all()

    return {
        "analyses": [
            {
                "id": analysis.id,
                "github_username": analysis.github_username,
                "context": analysis.context,
                "total_repos": analysis.total_repos,
                "repos_analyzed": analysis.repos_analyzed,
                "created_at": analysis.created_at.isoformat(),
                "from_cache": analysis.from_cache,
                # Extract summary from full_analysis
                "summary": (
                    json.loads(analysis.full_analysis)
                    .get("result", {})
                    .get("summary", "")[:200]
                    if analysis.full_analysis
                    else ""
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
    summary="Get portfolio analysis usage statistics",
    description="Get current month's candidate assessment usage (portfolio + PR combined).",
)
async def get_portfolio_usage(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Get user's candidate assessment usage statistics.

    Returns combined usage across Portfolio and PR analyses.
    """
    # Check if user is eligible
    is_eligible = user.subscription_plan in PORTFOLIO_ANALYSIS_TIERS

    if not is_eligible:
        tier_name = get_frontend_tier_name(user.subscription_plan.value)
        return {
            "eligible": False,
            "message": f"Portfolio Analysis is available for paid plans. Current plan: {tier_name}",
            "current_plan": tier_name,
            "required_plan": "BASIC or higher",
        }

    # Get usage statistics
    candidate_service = CandidateUsageService(db)
    monthly_usage = await candidate_service.get_monthly_usage(user.user_id)
    limit = CandidateUsageService.get_tier_limit(user.subscription_plan)
    remaining = limit - monthly_usage

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
        "current_plan": get_frontend_tier_name(user.subscription_plan.value),
        "note": "1 GitHub username = 1 candidate assessment (applies to both Portfolio and PR analyses)",
    }


@router.get(
    "/{analysis_id}",
    summary="Get portfolio analysis result by ID",
    description="Retrieve a stored portfolio analysis result by its ID.",
)
async def get_portfolio_analysis_by_id(
    analysis_id: str,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """Get portfolio analysis result by ID - requires authentication for security."""
    logger.info(
        f"Fetching portfolio analysis with ID: {analysis_id} for user: {user.user_id}"
    )

    # SECURITY: Verify ownership
    result = await db.execute(
        select(PortfolioAnalysis)
        .where(PortfolioAnalysis.id == analysis_id)
        .where(PortfolioAnalysis.user_id == user.user_id)
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        logger.warning(
            f"Portfolio analysis not found or unauthorized for ID: {analysis_id}, user: {user.user_id}"
        )
        raise HTTPException(
            status_code=404,
            detail="Portfolio analysis not found or you don't have permission to access it",
        )

    # Get PR analysis info for this username (user-specific)
    pr_info = await get_pr_analysis_info(analysis.github_username, user.user_id, db)

    # Return the stored analysis with PR info
    return format_analysis_response(
        analysis, from_cache=analysis.from_cache, pr_info=pr_info
    )


# Helper functions


async def get_pr_analysis_info(
    username: str, user_id: str, db: AsyncSession
) -> Dict[str, Any]:
    """
    Get PR analysis information for this username (filtered by user_id for security).

    Returns dict with:
    - pr_count: Total PRs if known
    - has_pr_analysis: Whether PR analysis exists
    - pr_analysis_id: ID of existing analysis
    - show_pr_card: True if PR analysis exists OR user has PRs on GitHub

    Args:
        username: GitHub username
        user_id: Current user's ID (for security filtering)
        db: Database session
    """
    from ...data.pr_fetcher import PRFetcher
    from ...database.models import PRAnalysisRecord, PRAnalysisResult

    try:
        # SECURITY: Filter by user_id to prevent cross-user data leakage
        result = await db.execute(
            select(PRAnalysisResult)
            .join(PRAnalysisRecord, PRAnalysisResult.id == PRAnalysisRecord.analysis_id)
            .where(PRAnalysisRecord.github_username == username)
            .where(PRAnalysisRecord.user_id == user_id)
            .order_by(PRAnalysisResult.created_at.desc())
            .limit(1)
        )
        existing_pr_analysis = result.scalar_one_or_none()

        if existing_pr_analysis:
            # PR analysis exists - always show card to view it
            return {
                "pr_count": existing_pr_analysis.total_prs_analyzed or 0,
                "has_pr_analysis": True,
                "pr_analysis_id": existing_pr_analysis.id,
                "show_pr_card": True,
            }
        else:
            # No PR analysis - check if user has PRs via GraphQL
            # This is a lightweight query that only fetches totalCount
            try:
                pr_fetcher = PRFetcher(config.github_token)
                pr_count = await asyncio.to_thread(pr_fetcher.check_pr_count, username)

                # Only show card if user has at least 5 PRs (moderate quality threshold)
                # This matches PR analysis data quality threshold for meaningful analysis
                show_card = pr_count >= 5
                logger.info(
                    f"PR availability check for {username}: {pr_count} PRs, "
                    f"show_card={show_card} (threshold: 5 PRs)"
                )

                return {
                    "pr_count": pr_count,
                    "has_pr_analysis": False,
                    "pr_analysis_id": None,
                    "show_pr_card": show_card,
                }
            except Exception as check_error:
                # If PR count check fails, hide card to avoid confusion
                logger.warning(
                    f"Failed to check PR count for {username}: {check_error}"
                )
                return {
                    "pr_count": 0,
                    "has_pr_analysis": False,
                    "pr_analysis_id": None,
                    "show_pr_card": False,
                }

    except Exception as e:
        logger.warning(f"Failed to check PR analysis for {username}: {e}")
        return {
            "pr_count": 0,
            "has_pr_analysis": False,
            "pr_analysis_id": None,
            "show_pr_card": False,
        }


async def get_cached_analysis(
    username: str, context: str, role: str, db: AsyncSession
) -> Optional[PortfolioAnalysis]:
    """
    Get cached portfolio analysis if available and not expired.

    Storage + Cache Separation:
    - Checks PortfolioAnalysisCache table (not PortfolioAnalysis)
    - Returns linked PortfolioAnalysis result from storage
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
        select(PortfolioAnalysisCache)
        .where(PortfolioAnalysisCache.github_username == username)
        .where(PortfolioAnalysisCache.context == context)
        .where(PortfolioAnalysisCache.role == role)
        .where(PortfolioAnalysisCache.cache_expires_at > now)
        .order_by(PortfolioAnalysisCache.created_at.desc())
        .limit(1)
    )

    cache_entry = result.scalar_one_or_none()

    if not cache_entry:
        return None

    # Fetch the linked result from storage
    result_query = await db.execute(
        select(PortfolioAnalysis).where(PortfolioAnalysis.id == cache_entry.result_id)
    )

    return result_query.scalar_one_or_none()


def format_analysis_response(
    analysis: PortfolioAnalysis,
    from_cache: bool,
    pr_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Format portfolio analysis for API response.

    Args:
        analysis: Portfolio analysis database record
        from_cache: Whether this is from cache
        pr_info: Dict with PR analysis info (count, exists, id, show_card)

    Returns:
        Formatted response dictionary
    """
    if pr_info is None:
        pr_info = {
            "pr_count": 0,
            "has_pr_analysis": False,
            "pr_analysis_id": None,
            "show_pr_card": False,
        }
    # Parse full analysis
    full_data = json.loads(analysis.full_analysis) if analysis.full_analysis else {}

    result = full_data.get("result", {})
    evidence = full_data.get("evidence", {})
    metadata_dict = full_data.get("metadata", {})

    # Extract repository names from metadata for Repositories tab
    # Use analyzed_repos from metadata which contains ALL analyzed repos, not just substantial ones
    repositories_analyzed = []
    username = analysis.github_username
    analyzed_repos_list = metadata_dict.get("analyzed_repos", [])

    if analyzed_repos_list:
        # metadata.analyzed_repos contains just repo names, need to add username
        for repo_name in analyzed_repos_list:
            if repo_name:
                repositories_analyzed.append(f"{username}/{repo_name}")
    else:
        # Fallback to substantial_repos if metadata.analyzed_repos not available
        substantial_repos = evidence.get("substantial_repos_structured", [])
        for repo in substantial_repos:
            if isinstance(repo, dict):
                repo_name = repo.get("name", "")
                if repo_name:
                    repositories_analyzed.append(f"{username}/{repo_name}")

    # Convert JSON result to markdown format for frontend compatibility
    markdown_sections = []

    # Executive Summary
    if result.get("summary"):
        exec_summary = f"## 📊 Executive Summary\n\n{result['summary']}"
        # Add Evidence Quality Assessment under Executive Summary
        if result.get("confidence_explanation"):
            # Clean up the assessment text - remove "END OF ANALYSIS" and separators
            clean_assessment = result["confidence_explanation"]
            # Remove END OF ANALYSIS markers
            clean_assessment = clean_assessment.replace("--- **END OF ANALYSIS**", "")
            clean_assessment = clean_assessment.replace("---\n**END OF ANALYSIS**", "")
            clean_assessment = clean_assessment.replace("**END OF ANALYSIS**", "")
            clean_assessment = clean_assessment.replace("END OF ANALYSIS", "")
            # Remove standalone separator lines
            clean_assessment = clean_assessment.replace("\n---\n\n", "\n\n")
            clean_assessment = clean_assessment.replace("\n---\n", "\n\n")
            # Fix Next Steps bullet formatting - replace "•" with "-" for proper parsing
            import re

            # Match lines that start with whitespace + bullet + content
            clean_assessment = re.sub(r"(\n\s*)•(\s*)", r"\1-\2", clean_assessment)
            # Also handle if bullets are at start of string
            clean_assessment = re.sub(r"^(\s*)•(\s*)", r"\1-\2", clean_assessment)
            # Clean up extra whitespace
            clean_assessment = clean_assessment.strip()
            exec_summary += f"\n\n### Analysis Confidence Level\n\n{clean_assessment}"
        markdown_sections.append(exec_summary)

    # Data Limitations
    if result.get("limitations"):
        markdown_sections.append(f"## ⚠️ Data Limitations\n\n{result['limitations']}")

    # Key Observations
    observations = result.get("observations", [])
    if observations:
        obs_text = "\n".join([f"- {obs}" for obs in observations])
        markdown_sections.append(
            f"## 🏢 Key Observations (Public Repos Only)\n\n{obs_text}"
        )

    # Public Portfolio Evolution
    evolution_periods = result.get("evolution_periods", [])
    if evolution_periods:
        if isinstance(evolution_periods, list):
            # Handle list of dicts or strings
            evo_items = []
            for period in evolution_periods:
                if isinstance(period, dict):
                    # Convert dict to formatted text
                    period_text = (
                        period.get("period", "")
                        or period.get("text", "")
                        or str(period)
                    )
                    evo_items.append(period_text)
                else:
                    evo_items.append(str(period))
            evo_text = "\n\n".join(evo_items)
        else:
            evo_text = str(evolution_periods)
        markdown_sections.append(f"## 📈 Public Portfolio Evolution\n\n{evo_text}")

    # Evidence Patterns
    evidence_patterns = result.get("evidence_patterns", [])
    if evidence_patterns:
        ep_text = ""
        for ep in evidence_patterns:
            if isinstance(ep, dict):
                pattern_name = ep.get("pattern", "")
                evidence = ep.get("evidence", "")
                ep_text += f"### {pattern_name}\n\n{evidence}\n\n"
            else:
                ep_text += f"- {ep}\n"
        markdown_sections.append(f"## 🔍 Evidence Patterns\n\n{ep_text}")

    # Interview Questions
    interview_questions = result.get("interview_questions", [])
    if interview_questions:
        iq_text = ""
        for idx, q in enumerate(interview_questions, 1):
            if isinstance(q, dict):
                question_text = q.get("question", str(q))
                category = q.get("category", "")
                context = q.get("context", "")
                evidence_ref = q.get("evidence", "")
                followups = q.get("follow_up_questions", [])
                listening = q.get("key_listening_points", "")

                iq_text += f"### Q{idx}: {question_text}\n\n"
                if category:
                    iq_text += f"**Category**: `{category}`\n"
                if context:
                    iq_text += f"**Context**: {context}\n"
                if evidence_ref:
                    iq_text += f"**📍 Based on Evidence**: {evidence_ref}\n"
                iq_text += "\n"
                if followups:
                    iq_text += "**Follow-up Questions**:\n"
                    iq_text += "\n".join([f"- {fu}" for fu in followups])
                    iq_text += "\n\n"
                if listening:
                    iq_text += f"**Key Listening Points**:\n- {listening}\n\n"
            else:
                iq_text += f"### Q{idx}: {q}\n\n"
        markdown_sections.append(f"## 💬 Interview Questions\n\n{iq_text}")

    # Positive Indicators
    positive_indicators = result.get("positive_indicators", [])
    if positive_indicators:
        pi_text = "\n".join([f"- {pi}" for pi in positive_indicators])
        markdown_sections.append(f"## ✨ Positive Indicators\n\n{pi_text}")

    # Areas to Explore
    areas_to_explore = result.get("areas_to_explore", [])
    if areas_to_explore:
        ate_text = "\n".join([f"- {area}" for area in areas_to_explore])
        markdown_sections.append(f"## 🔍 Areas to Explore\n\n{ate_text}")

    # Recommendations
    recommendations = result.get("recommendations", [])
    if recommendations:
        rec_text = "\n".join([f"- {rec}" for rec in recommendations])
        markdown_sections.append(f"## ✅ Recommendations\n\n{rec_text}")

    # Quality Indicators
    quality_indicators = result.get("quality_indicators", [])
    if quality_indicators:
        qi_text = ""
        for qi in quality_indicators:
            if isinstance(qi, dict):
                indicator = qi.get("indicator", "")
                observation = qi.get("observation", "")
                scope = qi.get("scope", "")
                implication = qi.get("implication", "")
                qi_text += f"### {indicator}\n\n"
                qi_text += f"**Observation**: {observation}\n"
                qi_text += f"**Scope**: {scope}\n"
                qi_text += f"**Implication**: {implication}\n\n"
            else:
                qi_text += f"- {qi}\n"
        markdown_sections.append(
            f"## 📈 Quality Indicators (Public Work Only)\n\n{qi_text}"
        )

    # Combine all sections into markdown
    full_analysis_markdown = "\n\n".join(markdown_sections)

    # Parse analysis_metadata JSON
    analysis_metadata = (
        json.loads(analysis.analysis_metadata) if analysis.analysis_metadata else {}
    )

    # Calculate portfolio span from oldest and newest repo dates
    portfolio_span_days = 0
    if metadata_dict.get("oldest_repo") and metadata_dict.get("newest_repo"):
        from datetime import datetime

        try:
            oldest = datetime.fromisoformat(
                metadata_dict["oldest_repo"].replace("Z", "+00:00")
            )
            newest = datetime.fromisoformat(
                metadata_dict["newest_repo"].replace("Z", "+00:00")
            )
            portfolio_span_days = (newest - oldest).days
        except Exception:
            portfolio_span_days = 0

    return {
        "id": analysis.id,
        "user_id": analysis.user_id,
        "analysis_id": analysis.id,
        "github_username": analysis.github_username,
        "username": analysis.github_username,
        "context": analysis.context,
        "role": analysis.role,
        "status": analysis.status.value if analysis.status else "completed",
        # Progress tracking (for async background processing)
        "progress_stage": analysis.progress_stage,
        "progress_percent": analysis.progress_percent,
        "progress_message": analysis.progress_message,
        "total_repos": analysis.total_repos,
        "repos_analyzed": analysis.repos_analyzed,
        "repos_skipped": analysis.repos_skipped,
        # Count fields for frontend stats display
        "key_observations_count": analysis.key_observations_count,
        "evidence_patterns_count": analysis.evidence_patterns_count,
        "interview_questions_count": analysis.interview_questions_count,
        # Full analysis for frontend compatibility (converted to markdown)
        "full_analysis": full_analysis_markdown,
        # Analysis metadata for frontend compatibility
        "analysis_metadata": {
            "total_public_repos": analysis_metadata.get(
                "total_public_repos", analysis.total_repos
            ),
            "repos_analyzed": analysis_metadata.get(
                "repo_count", analysis.repos_analyzed
            ),
            "repos_skipped": analysis_metadata.get(
                "repos_skipped", analysis.repos_skipped
            ),
            "forks_count": metadata_dict.get("forks_count", 0),
            "oldest_repo_date": metadata_dict.get("oldest_repo", ""),
            "newest_repo_date": metadata_dict.get("newest_repo", ""),
            "portfolio_span_days": portfolio_span_days,
            "model": result.get("model_used", "unknown"),
            "token_count": analysis.token_count,
            "api_cost": analysis.api_cost,
        },
        "processing_time_seconds": analysis.processing_time_seconds,
        "from_cache": from_cache or analysis.from_cache,
        "created_at": analysis.created_at.isoformat(),
        # Analysis result sections (for backward compatibility)
        "summary": result.get("summary", ""),
        "limitations": result.get("limitations", ""),
        "observations": result.get("observations", []),
        "evolution_periods": result.get("evolution_periods", []),
        "evidence_patterns": result.get("evidence_patterns", []),
        "interview_questions": result.get("interview_questions", []),
        "repositories_analyzed": repositories_analyzed,  # List of "username/repo" strings
        "positive_indicators": result.get("positive_indicators", []),
        "areas_to_explore": result.get("areas_to_explore", []),
        "recommendations": result.get("recommendations", []),
        "quality_indicators": result.get("quality_indicators", []),
        "confidence_explanation": result.get("confidence_explanation", ""),
        # PR analysis info - always show card (either to run or view analysis)
        "pr_count": pr_info["pr_count"],
        "has_pr_analysis": pr_info["has_pr_analysis"],
        "pr_analysis_id": pr_info["pr_analysis_id"],
        "show_pr_card": pr_info["show_pr_card"],
        # Evidence data (optional - can be large)
        "evidence": evidence,
        # Metadata
        "metadata": metadata_dict,
        # Performance metrics
        "token_count": analysis.token_count,
        "api_cost": analysis.api_cost,
        "model_used": result.get("model_used", "unknown"),
        # Cache info
        "cache_expires_at": (
            analysis.cache_expires_at.isoformat() if analysis.cache_expires_at else None
        ),
    }


async def create_cache_entry(
    analysis: PortfolioAnalysis, db: AsyncSession, max_retries: int = 3
) -> bool:
    """
    Create cache entry for portfolio analysis with deduplication.

    Handles race conditions via UNIQUE constraint and retry logic.
    If multiple users analyze same candidate simultaneously, only one
    cache entry is created (database enforces uniqueness).

    Args:
        analysis: Portfolio analysis result to cache
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
            cache_entry = PortfolioAnalysisCache(
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
                f"Created cache entry for portfolio analysis: {analysis.id} "
                f"(@{analysis.github_username}, {analysis.context}, {analysis.role})"
            )
            return True

        except IntegrityError as e:
            # UNIQUE constraint violation - cache entry already exists
            await db.rollback()

            if "uq_portfolio_cache_context" in str(e).lower():
                logger.info(
                    f"Cache entry already exists for @{analysis.github_username}, "
                    f"{analysis.context}, {analysis.role} (attempt {attempt + 1}/{max_retries})"
                )

                # Check if existing cache points to our result (race condition resolved)
                result = await db.execute(
                    select(PortfolioAnalysisCache)
                    .where(
                        PortfolioAnalysisCache.github_username
                        == analysis.github_username
                    )
                    .where(PortfolioAnalysisCache.context == analysis.context)
                    .where(PortfolioAnalysisCache.role == analysis.role)
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
