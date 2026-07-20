# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Analysis endpoints for repository evaluation.

This module provides REST API endpoints for single and batch repository analysis
using the existing MVP business logic with smart caching and cost optimization.
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from ...ai.analyzer import AIAnalyzer
from ...ai.cost_tracker import CostTracker

# Import existing MVP business logic
from ...core.classifier import AnalysisMethod, RepositoryClassifier
from ...core.confidence_scorer import ConfidenceRiskAssessor
from ...core.context_analyzer import ContextAnalyzer
from ...core.report_generator import ReportFormat, ReportGenerator
from ...data.github_fetcher import GitHubFetcher
from ...database.connection import get_db_session
from ...database.models import (
    AnalysisResult,
    AnalysisStatus,
    BatchAnalysis,
    SubscriptionPlan,
    User,
)
from ...services.cancellation_service import (
    TaskStatus,
    TaskType,
    get_cancellation_service,
)
from ...services.candidate_usage_service import CandidateUsageService
from ...utils.config import get_config
from ...utils.logging import get_logger
from ...utils.timeout_manager import TimeoutManager
from ..auth.dependencies import get_current_active_user, require_api_access
from ..dependencies import (
    get_client_ip,
    get_github_fetcher,
    get_user_repo_size_limit,
    validate_github_url,
)
from ..models.analysis import (
    AnalysisResultList,
    AnalysisResultListItem,
    AnalysisResultResponse,
)
from ..models.clean_responses import convert_to_clean_response
from ..models.requests import AnalyzeRequest, BatchAnalyzeRequest
from ..models.responses import (
    AnalysisResponse,
    BatchAnalysisResponse,
    RepositorySizeLimitErrorResponse,
)
from ..services.async_batch_history_service import AsyncBatchHistoryService
from ..services.budget_dependencies import get_budget_monitor
from ..services.budget_monitor import BudgetMonitor
from ..services.candidate_context import validate_context
from ..services.consent_service import ConsentService
from ..services.rate_limit_dependencies import RateLimitContext, check_rate_limits
from ..services.redis_service import generate_analysis_cache_key, redis_service
from ..services.tier_rate_limiter import TierRateLimiter

# from fastapi.responses import JSONResponse  # Not used currently


logger = get_logger(__name__)
config = get_config()

router = APIRouter()

# Initialize MVP components (excluding GitHubFetcher which is now dependency-injected)
classifier = RepositoryClassifier()
context_analyzer = ContextAnalyzer()
confidence_scorer = ConfidenceRiskAssessor()
report_generator = ReportGenerator(config.anthropic_api_key)
cost_tracker = CostTracker()
ai_analyzer = AIAnalyzer()


@router.post(
    "/analyze",
    response_model=AnalysisResponse,
    responses={
        200: {"description": "Analysis completed successfully"},
        400: {"description": "Invalid repository URL or validation errors"},
        403: {
            "description": "Private repository requires Professional/Enterprise plan"
        },
        413: {
            "description": "Repository size exceeds plan limit",
            "model": RepositorySizeLimitErrorResponse,
        },
        500: {"description": "Analysis failure or system error"},
    },
)
async def analyze_repository(
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_active_user),
    client_ip: str = Depends(get_client_ip),
    github_fetcher: GitHubFetcher = Depends(get_github_fetcher),
    rate_limits: RateLimitContext = Depends(check_rate_limits),
    budget_monitor: BudgetMonitor = Depends(get_budget_monitor),
    db: AsyncSession = Depends(get_db_session),
    size_limit_mb: int = Depends(get_user_repo_size_limit),
) -> AnalysisResponse:
    """
    Analyze a single GitHub repository.

    Performs comprehensive analysis using MVP business logic with smart caching
    for sub-30 second response times and cost optimization.

    **Repository Size Limits by Plan:**
    - Free: 50MB
    - Basic: 100MB
    - Professional: 500MB
    - Enterprise: 1GB (customizable up to 10GB+)

    **Repository Access:**
    - All plans: Public repositories only
    - Private repositories: Not supported (focus on public portfolio assessment)

    Args:
        request: Repository analysis request
        background_tasks: FastAPI background tasks
        client_ip: Client IP for rate limiting

    Returns:
        AnalysisResponse: Complete repository analysis

    Raises:
        HTTPException:
            - 400: Invalid repository URL or validation errors
            - 403: Private repository analysis not supported
            - 413: Repository size exceeds plan limit
            - 500: Analysis failure or system error
    """
    start_time = datetime.now(timezone.utc)
    validated_url: str = str(request.repository_url)  # Initialize for error handling
    logger.info(
        f"DEBUG ANALYZE START: user.user_id = '{user.user_id}', user.email = '{user.email}'"
    )

    # Check tier-specific rate limits first
    tier_limiter = TierRateLimiter(redis_service)
    allowed, error_msg, retry_info = await tier_limiter.check_rate_limit(
        user.user_id, user.subscription_plan, is_batch=False
    )
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": error_msg,
                "retry_after": retry_info.get("retry_after", 5) if retry_info else 5,
            },
        )

    async with rate_limits:
        try:
            # Validate and normalize the repository URL
            validated_url = validate_github_url(request.repository_url)

            # Extract username from repository URL (format: github.com/owner/repo)
            url_parts = validated_url.rstrip("/").split("/")
            github_username = url_parts[-2]  # owner is second-to-last part

            # Validate/lock candidate context (PAID TIERS ONLY)
            # Free tier can analyze any repo without candidate linking
            candidate_username: Optional[str]
            if user.subscription_plan != SubscriptionPlan.FREE:
                # Use provided username if explicitly passed, otherwise use extracted username
                # For paid tiers, this links repo analysis to candidate profile
                candidate_username = request.github_username or github_username

                await validate_context(
                    db=db,
                    username=candidate_username,
                    role=request.role,
                    organization_context=request.context.value,  # AnalysisContext enum value
                    user_id=user.user_id,
                )
                logger.info(
                    f"Context validated for candidate {candidate_username} (paid tier)"
                )
            else:
                # Free tier: no candidate linking, no context lock
                candidate_username = None
                logger.info(
                    f"Free tier analysis - no candidate linking for {validated_url}"
                )

            logger.info(
                f"Starting analysis for {validated_url} (context: {request.context})"
            )

            # Check repo deep dive quota for paid tiers
            # This is a SEPARATE quota from candidate assessments
            if user.subscription_plan != SubscriptionPlan.FREE:
                usage_service = CandidateUsageService(db)
                (
                    is_allowed,
                    current_count,
                    limit,
                ) = await usage_service.check_repo_deep_dive_limit(
                    user.user_id, user.subscription_plan
                )

                if not is_allowed:
                    raise HTTPException(
                        status_code=403,
                        detail={
                            "error": "Monthly repo deep dive limit reached",
                            "message": f"You have used {current_count}/{limit} repo deep dives this month. Upgrade your plan for more capacity.",
                            "current_usage": current_count,
                            "limit": limit,
                            "billing_period": usage_service.get_current_billing_period(),
                        },
                    )

                logger.info(
                    f"Repo deep dive quota check passed: {current_count}/{limit} used"
                )

            # Register task with cancellation service
            cancellation_service = get_cancellation_service()
            task_id = f"single_{user.user_id}_{int(start_time.timestamp())}"

            cancellation_service.register_task(
                task_id=task_id,
                task_type=TaskType.SINGLE_ANALYSIS,
                user_id=user.user_id,
            )

            # Generate cache key
            cache_key = generate_analysis_cache_key(
                validated_url, request.context.value, request.role
            )

            # Check cache unless force refresh requested
            cached_result = None
            if not request.force_refresh:
                cached_result = await redis_service.get(cache_key)

            if cached_result:
                try:
                    # Parse cached result - validate it's proper JSON
                    analysis_data = json.loads(cached_result)

                    logger.info(f"Cache hit for {validated_url}")

                    # Update metadata
                    analysis_data["metadata"].update(
                        {
                            "cached": True,
                            "cache_hit_time": datetime.now(timezone.utc).isoformat(),
                            "response_time_seconds": (
                                datetime.now(timezone.utc) - start_time
                            ).total_seconds(),
                        }
                    )

                    return AnalysisResponse(**analysis_data)
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    # Invalid cache entry - log and continue with fresh analysis
                    logger.warning(f"Invalid cache entry for {validated_url}: {e}")
                    logger.info(
                        f"Clearing invalid cache and performing fresh analysis for {validated_url}"
                    )
                    # Clear the invalid cache entry
                    await redis_service.delete(cache_key)
                    cached_result = None

            # Check budget status before analysis
            budget_allowed, budget_reason = await budget_monitor.should_allow_request()
            if not budget_allowed:
                raise HTTPException(
                    status_code=402,  # Payment Required
                    detail={
                        "error": "Budget limit reached",
                        "message": budget_reason,
                        "repository_url": validated_url,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )

            # Perform fresh analysis using MVP business logic
            analysis_result = await _perform_repository_analysis(
                validated_url,
                request.context.value,
                start_time,
                github_fetcher,
                user,
                size_limit_mb,
                db,  # NEW: Pass database session
                budget_monitor,
                request.format or "json",
                role=request.role,  # Pass role for interview question customization
            )

            # Cache the result (24 hour TTL for analysis results)
            cache_data = analysis_result.model_dump()
            cache_data["metadata"]["cached"] = False

            # Background task to cache result
            background_tasks.add_task(
                _cache_analysis_result, cache_key, json.dumps(cache_data, default=str)
            )

            # Store analysis result in database
            # Extract repository name from URL
            repo_parts = validated_url.rstrip("/").split("/")
            repo_name = (
                f"{repo_parts[-2]}/{repo_parts[-1]}"
                if len(repo_parts) >= 2
                else validated_url
            )

            processing_time_ms = int(
                analysis_result.metadata.get("response_time_seconds", 0) * 1000
            )

            # Store the analysis result and get the ID
            analysis_id = await _store_analysis_result(
                db,
                user,
                validated_url,
                repo_name,
                request.context.value,
                analysis_result,
                processing_time_ms,
                token_count=analysis_result.metadata.get(
                    "token_count"
                ),  # Pass token count from metadata
                api_cost=analysis_result.metadata.get("analysis_cost_usd"),
                github_username=candidate_username,  # Links to candidate for paid tiers
                role=request.role,  # Store role for context consistency
            )

            # Update the metadata with the stored analysis ID if successful
            if analysis_id:
                analysis_result.metadata["analysis_id"] = analysis_id
                analysis_result.metadata["stored"] = True
                # Set the ID at the top level for frontend redirect
                analysis_result.id = analysis_id
                logger.info(f"Analysis stored with ID: {analysis_id}")

                # Track repo deep dive for paid tiers (SEPARATE from candidate assessments)
                if user.subscription_plan != SubscriptionPlan.FREE:
                    try:
                        usage_service = CandidateUsageService(db)
                        await usage_service.track_repo_deep_dive(
                            user_id=user.user_id,
                            repository_name=repo_name,  # Format: "owner/repo"
                            analysis_id=analysis_id,
                        )
                        logger.info(
                            f"Tracked repo deep dive for {repo_name} by user {user.user_id}"
                        )
                    except Exception as e:
                        # Don't fail the analysis if tracking fails
                        logger.error(
                            f"Failed to track repo deep dive: {e}", exc_info=True
                        )
            else:
                # Generate a temporary ID if storage failed
                temp_id = str(uuid.uuid4())
                analysis_result.metadata["analysis_id"] = temp_id
                analysis_result.metadata["stored"] = False
                analysis_result.id = temp_id
                logger.warning(
                    f"Failed to store analysis, using temporary ID: {temp_id}"
                )

            # Add task_id to metadata for frontend tracking
            analysis_result.metadata["task_id"] = task_id

            # Mark task as completed
            cancellation_service.complete_task(task_id)

            logger.info(
                f"Analysis completed for {validated_url} in "
                f"{analysis_result.metadata['response_time_seconds']:.2f}s"
            )

            return analysis_result

        except ValueError as e:
            error_message = str(e)

            # Mark task as failed before raising exception
            cancellation_service.complete_task(task_id, TaskStatus.FAILED)

            # Check if it's a size-related error
            if "exceeds maximum allowed size" in error_message:
                logger.warning(
                    f"Repository too large: {validated_url} - {error_message}"
                )
                raise HTTPException(
                    status_code=413,
                    detail={
                        "error": "Repository too large",
                        "message": error_message,
                        "repository_url": validated_url,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
            elif (
                "exceeds maximum allowed" in error_message
                and "file count" in error_message
            ):
                logger.warning(
                    f"Repository has too many files: {validated_url} - {error_message}"
                )
                raise HTTPException(
                    status_code=413,
                    detail={
                        "error": "Repository has too many files",
                        "message": error_message,
                        "repository_url": validated_url,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
            else:
                # Other validation errors
                # Get context value safely (handle both enum and string)
                context_value = (
                    request.context.value
                    if hasattr(request.context, "value")
                    else str(request.context)
                )
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "Validation failed",
                        "message": error_message,
                        "repository_url": validated_url,
                        "context": context_value,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
        except HTTPException:
            # Re-raise HTTPExceptions (like the 403 for private repos)
            # Mark task as failed for HTTP errors too
            cancellation_service.complete_task(task_id, TaskStatus.FAILED)
            raise
        except Exception as e:
            logger.error(f"Analysis failed for {validated_url}: {e}", exc_info=True)

            # Mark task as failed before raising exception
            cancellation_service.complete_task(task_id, TaskStatus.FAILED)

            # Return structured error response
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Analysis failed",
                    "message": str(e),
                    "repository_url": validated_url,
                    "context": request.context.value,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )


@router.post(
    "/batch",
    response_model=BatchAnalysisResponse,
    responses={
        200: {"description": "Batch analysis completed (may include partial failures)"},
        400: {"description": "Invalid batch size or repository URLs"},
        403: {"description": "Batch analysis requires Enterprise plan"},
        402: {"description": "Budget limit reached"},
        408: {"description": "Batch analysis timeout"},
        413: {"description": "One or more repositories exceed size limits"},
        500: {"description": "System error during batch processing"},
    },
)
async def batch_analyze_repositories(
    request: BatchAnalyzeRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_active_user),
    client_ip: str = Depends(get_client_ip),
    github_fetcher: GitHubFetcher = Depends(get_github_fetcher),
    budget_monitor: BudgetMonitor = Depends(get_budget_monitor),
    size_limit_mb: int = Depends(get_user_repo_size_limit),
    db: AsyncSession = Depends(get_db_session),
) -> BatchAnalysisResponse:
    """
    Analyze multiple GitHub repositories in parallel (Enterprise-only).

    Process up to 10 repositories concurrently with smart caching
    and cost optimization. Results are returned as they complete.

    **🏢 Enterprise-Only Feature:**
    - Bulk analysis designed for hiring teams and large-scale candidate assessment
    - Requires Enterprise subscription plan
    - Contact support via the contact page for upgrade assistance

    **Repository Size Limits:**
    - Enterprise: 1GB per repository (customizable up to 10GB+)

    **Repository Access:**
    - All plans: Public repositories only
    - Private repositories: Not supported (focus on public portfolio assessment)

    Args:
        request: Batch analysis request (max 10 repositories)
        background_tasks: FastAPI background tasks
        client_ip: Client IP for rate limiting

    Returns:
        BatchAnalysisResponse: Results for all repositories with success/error breakdown

    Raises:
        HTTPException:
            - 400: Invalid batch size or repository URLs
            - 403: Batch analysis requires Enterprise plan
            - 402: Budget limit reached
            - 408: Batch analysis timeout (max 60 minutes)
            - 500: System error during batch processing
    """
    start_time = datetime.now(timezone.utc)

    try:
        # Validate batch size (handled by Pydantic max_length, but double-check)
        if len(request.repositories) == 0:
            raise HTTPException(
                status_code=400,
                detail="Batch request must contain at least one repository",
            )
        # Batch analysis is Professional, Enterprise, and Scale+ feature
        # Check tier access first before validating batch size
        if user.subscription_plan not in [
            SubscriptionPlan.PROFESSIONAL,
            SubscriptionPlan.ENTERPRISE,
            SubscriptionPlan.SCALE_PLUS,
        ]:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Batch analysis requires Professional, Enterprise, or Scale+ plan",
                    "message": "Bulk repository analysis is available to Professional, Enterprise, and Scale+ subscribers for efficient candidate assessment.",
                    "current_plan": user.subscription_plan.value,
                    "required_plans": ["professional", "enterprise", "scale_plus"],
                    "upgrade_url": "/pricing",
                    "batch_limits": {
                        "professional": "5 repositories per batch",
                        "enterprise": "10 repositories per batch",
                        "scale_plus": "15 repositories per batch",
                    },
                    "repository_count": len(request.repositories),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        # Validate batch size based on tier
        if user.subscription_plan == SubscriptionPlan.PROFESSIONAL:
            max_batch_size = 5
        elif user.subscription_plan == SubscriptionPlan.SCALE_PLUS:
            max_batch_size = 15
        else:  # ENTERPRISE
            max_batch_size = 10
        if len(request.repositories) > max_batch_size:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": f"Batch size exceeds {user.subscription_plan.value} plan limit",
                    "message": f"{user.subscription_plan.value.capitalize()} plan allows up to {max_batch_size} repositories per batch",
                    "current_batch_size": len(request.repositories),
                    "max_batch_size": max_batch_size,
                    "current_plan": user.subscription_plan.value,
                },
            )

        # Check budget status before batch analysis
        budget_allowed, budget_reason = await budget_monitor.should_allow_request()
        if not budget_allowed:
            raise HTTPException(
                status_code=402,  # Payment Required
                detail={
                    "error": "Budget limit reached",
                    "message": budget_reason,
                    "repository_count": len(request.repositories),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        # Check tier-specific rate limits for batch
        tier_limiter = TierRateLimiter(redis_service)
        allowed, error_msg, retry_info = await tier_limiter.check_rate_limit(
            user.user_id,
            user.subscription_plan,
            is_batch=True,  # This is a batch request
        )
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": error_msg,
                    "retry_after": (
                        retry_info.get("retry_after", 5) if retry_info else 5
                    ),
                },
            )

        # Create batch history record for Enterprise (Scale) and Scale+ tiers
        batch_history_service = None
        batch_id = str(uuid.uuid4())

        # Register batch task with cancellation service
        cancellation_service = get_cancellation_service()
        batch_task = cancellation_service.register_task(
            task_id=batch_id, task_type=TaskType.BATCH_ANALYSIS, user_id=user.user_id
        )

        if user.subscription_plan in [
            SubscriptionPlan.ENTERPRISE,
            SubscriptionPlan.SCALE_PLUS,
        ]:
            batch_history_service = AsyncBatchHistoryService(db)
            contexts = [repo.context.value for repo in request.repositories]
            batch_id = await batch_history_service.create_batch_record(
                user_id=user.user_id,
                repository_count=len(request.repositories),
                contexts=contexts,
                concurrency_mode=request.concurrency_mode or "sequential",
            )
            await batch_history_service.start_batch_processing(batch_id)

        logger.info(
            f"Starting batch analysis of {len(request.repositories)} repositories with batch_id: {batch_id}"
        )

        # Determine concurrency limit based on mode and subscription plan
        concurrency_mode = request.concurrency_mode or "sequential"

        # Validate concurrency mode based on subscription plan
        if (
            concurrency_mode == "fast"
            and user.subscription_plan != SubscriptionPlan.SCALE_PLUS
        ):
            raise HTTPException(
                status_code=403,
                detail="Fast mode (5 concurrent) is only available for Scale+ plans",
            )

        if concurrency_mode == "balanced" and user.subscription_plan not in [
            SubscriptionPlan.ENTERPRISE,
            SubscriptionPlan.SCALE_PLUS,
        ]:
            raise HTTPException(
                status_code=403,
                detail="Balanced mode (2 concurrent) is only available for Enterprise/Scale and Scale+ plans",
            )

        # Set concurrency limit
        concurrency_limits = {"sequential": 1, "balanced": 2, "fast": 5}
        max_concurrent = concurrency_limits.get(concurrency_mode, 1)

        # Calculate timeout based on mode and number of repos
        # Sequential: 5 min per repo (increased for enterprise context), Balanced: 3 min per batch, Fast: 2 min per batch
        num_repos = len(request.repositories)
        if concurrency_mode == "sequential":
            # Increased to 5 minutes per repo for thorough enterprise analysis
            timeout_seconds = num_repos * 300  # 5 min per repo
        elif concurrency_mode == "balanced":
            num_batches = (num_repos + 1) // 2  # Round up
            timeout_seconds = num_batches * 180  # 3 min per batch of 2
        else:  # fast
            num_batches = (num_repos + 4) // 5  # Round up
            timeout_seconds = num_batches * 120  # 2 min per batch of 5

        # Add buffer and cap at 60 minutes
        timeout_seconds = min(
            timeout_seconds + 120, 3600
        )  # Add 2 min buffer, max 60 min

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)

        async def analyze_with_semaphore(repo_request: Any) -> AnalysisResponse:
            async with semaphore:
                return await _perform_repository_analysis(
                    str(repo_request.repository_url),
                    repo_request.context.value,
                    start_time,
                    github_fetcher,
                    user,
                    size_limit_mb,
                    db,  # NEW: Pass database session
                    budget_monitor,
                    batch_id=batch_id,
                )

        # Create individual analysis tasks with semaphore
        analysis_tasks = []
        for repo_request in request.repositories:
            task = analyze_with_semaphore(repo_request)
            analysis_tasks.append(task)

        # Execute analyses with controlled concurrency and appropriate timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*analysis_tasks, return_exceptions=True),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            # Mark batch as failed if we're tracking history
            timeout_minutes = timeout_seconds // 60
            if batch_history_service:
                await batch_history_service.fail_batch(
                    batch_id=batch_id,
                    error_message=f"Batch analysis timed out after {timeout_minutes} minutes",
                    processing_time_ms=timeout_seconds
                    * 1000,  # Convert to milliseconds
                )

            # Mark batch task as failed for timeout
            cancellation_service.complete_task(batch_id, TaskStatus.FAILED)

            raise HTTPException(
                status_code=408,
                detail=f"Batch analysis timed out after {timeout_minutes} minutes",
            )

        # Process results and separate successes from failures
        successful_analyses = []
        failed_analyses = []
        total_cost = 0.0
        error_messages = []

        for i, result in enumerate(results):
            repository_url = str(request.repositories[i].repository_url)

            if isinstance(result, Exception):
                error_msg = str(result)
                failed_analyses.append(
                    {
                        "repository_url": repository_url,
                        "error": error_msg,
                        "context": request.repositories[i].context.value,
                    }
                )
                error_messages.append(f"{repository_url}: {error_msg}")
                logger.error(f"Batch analysis failed for {repository_url}: {result}")
            else:
                # Only add AnalysisResponse objects, not exceptions
                if isinstance(result, AnalysisResponse):
                    successful_analyses.append(result)
                    # Add cost if available
                    if result.metadata.get("analysis_cost_usd"):
                        total_cost += result.metadata["analysis_cost_usd"]

                    # Store result in database with batch_id
                    try:
                        repo_name = repository_url.split("/")[-1]
                        processing_time_ms = int(
                            (datetime.now(timezone.utc) - start_time).total_seconds()
                            * 1000
                        )

                        await _store_analysis_result(
                            db,
                            user,
                            repository_url,
                            repo_name,
                            request.repositories[i].context.value,
                            result,
                            processing_time_ms,
                            token_count=result.metadata.get(
                                "token_count"
                            ),  # Pass token count from metadata
                            api_cost=result.metadata.get("analysis_cost_usd"),
                            batch_id=batch_id,
                            github_username=None,  # Batch analysis doesn't link to candidates yet
                            role=None,  # Batch analysis doesn't track roles yet
                        )
                    except Exception as e:
                        logger.error(f"Failed to store batch analysis result: {e}")

                    # Cache successful results in background
                    cache_key = generate_analysis_cache_key(
                        repository_url,
                        request.repositories[i].context.value,
                        request.repositories[i].role,
                    )
                    cache_data = result.model_dump()
                    background_tasks.add_task(
                        _cache_analysis_result,
                        cache_key,
                        json.dumps(cache_data, default=str),
                    )

        total_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        processing_time_ms = int(total_time * 1000)

        # Complete batch history record if tracking
        if batch_history_service:
            await batch_history_service.complete_batch(
                batch_id=batch_id,
                successful_count=len(successful_analyses),
                failed_count=len(failed_analyses),
                total_cost=total_cost,
                processing_time_ms=processing_time_ms,
                error_messages=error_messages if error_messages else None,
            )

        # Mark batch task as completed
        cancellation_service.complete_task(batch_id)

        logger.info(
            f"Batch analysis completed: {len(successful_analyses)} successful, "
            f"{len(failed_analyses)} failed in {total_time:.2f}s"
        )

        return BatchAnalysisResponse(
            results=successful_analyses,
            errors=failed_analyses,
            metadata={
                "total_repositories": len(request.repositories),
                "successful_count": len(successful_analyses),
                "failed_count": len(failed_analyses),
                "total_time_seconds": total_time,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "batch_id": batch_id,
            },
        )

    except HTTPException:
        # Mark batch task as failed for HTTP errors
        if "cancellation_service" in locals() and cancellation_service:
            cancellation_service.complete_task(batch_id, TaskStatus.FAILED)
        raise
    except Exception as e:
        # Mark batch as failed if we're tracking history
        if "batch_history_service" in locals() and batch_history_service:
            try:
                await batch_history_service.fail_batch(
                    batch_id=batch_id,
                    error_message=f"System error: {str(e)}",
                    processing_time_ms=int(
                        (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                    ),
                )
            except Exception as history_error:
                logger.error(
                    f"Failed to update batch history on error: {history_error}"
                )

        # Mark batch task as failed for system errors
        cancellation_service.complete_task(batch_id, TaskStatus.FAILED)

        logger.error(f"Batch analysis system error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Batch analysis failed",
                "message": str(e),
                "repository_count": len(request.repositories),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )


async def _perform_repository_analysis(
    repository_url: str,
    context: str,
    start_time: datetime,
    github_fetcher: GitHubFetcher,
    user: User,
    size_limit_mb: int,
    db: AsyncSession,  # NEW: Database session for FREE tier AI quota check
    budget_monitor: Optional[BudgetMonitor] = None,
    output_format: str = "json",
    batch_id: Optional[str] = None,
    role: str = "senior",  # Role level for interview question customization
) -> AnalysisResponse:
    """
    Perform comprehensive repository analysis using MVP business logic.

    Integrates all existing components: GitHub fetching, classification,
    context analysis, confidence scoring, and report generation.

    Args:
        repository_url: GitHub repository URL
        context: Analysis context (startup, enterprise, etc.)
        start_time: Analysis start timestamp
        github_fetcher: GitHubFetcher instance for data retrieval

    Returns:
        AnalysisResponse: Complete analysis result
    """
    # Step 0: Check repository size first (for batch processing)
    size_info = await asyncio.to_thread(
        github_fetcher.check_repository_size, repository_url
    )
    size_mb = size_info["size_kb"] / 1024
    file_count = size_info["file_count"]

    # Check size limits - all plans now have 10GB limit
    if size_mb > size_limit_mb:
        # All plans have same 10GB limit now, but still check for edge cases
        logger.warning(
            f"Repository size ({size_mb:.1f}MB) exceeds {size_limit_mb}MB limit"
        )
        raise HTTPException(
            status_code=413,
            detail=f"Repository size ({size_mb:.1f}MB) exceeds maximum allowed size "
            f"({size_limit_mb}MB). All plans support repositories up to 10GB.",
        )

    if file_count > 0 and file_count > config.analysis.max_repo_files:
        raise ValueError(
            f"Repository file count ({file_count}) exceeds maximum allowed "
            f"({config.analysis.max_repo_files})"
        )

    # Step 1: Fetch repository data
    repo_data = await asyncio.to_thread(
        github_fetcher.fetch_repository_data, repository_url
    )

    # Step 1.5: Configure dynamic timeouts based on repository characteristics
    timeout_config = TimeoutManager.calculate_timeouts(
        repo_data, user.subscription_plan
    )
    logger.info(
        f"Timeout configuration for {repository_url}: {timeout_config.explanation}, "
        f"backend={timeout_config.backend_timeout_s}s, frontend={timeout_config.frontend_timeout_ms / 1000}s"
    )

    # Check if private repository - we focus on public repos only
    if repo_data.is_private:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Private repository analysis not supported",
                "message": "Exiqus focuses on public repository analysis for hiring decisions. Please use a public repository.",
                "current_plan": user.subscription_plan.value,
                "is_private": True,
                "repository_url": repository_url,
                "suggestion": "Consider making the repository public or using a public portfolio repository",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    # Step 2: Classify repository type
    repo_classification = await asyncio.to_thread(
        classifier.classify_repository, repo_data
    )

    # Step 2.5: Handle special repository types with appropriate responses
    from ...core.classifier import TemplateCategory

    # Check for special edge cases that need custom handling
    if repo_classification.method == AnalysisMethod.TEMPLATE:
        special_response = None

        # Helper function to format file size
        def format_size(size_kb: int) -> str:
            """Format size from KB to human-readable format."""
            if size_kb < 1024:
                return f"{size_kb}KB"
            elif size_kb < 1024 * 1024:
                return f"{size_kb / 1024:.1f}MB"
            else:
                return f"{size_kb / (1024 * 1024):.1f}GB"

        # CRITICAL: Check for content-free or trivial repositories FIRST
        # Use the classification result instead of re-checking
        if repo_classification.template_category == TemplateCategory.EMPTY:
            formatted_size = format_size(repo_data.size)
            file_count = len([f for f in repo_data.file_structure if f.type == "file"])
            special_response = {
                "repository_type": "minimal",
                "message": f"This repository appears to be a trivial or experimental project with minimal content ({file_count} files, {formatted_size}). It may be a joke repository, quick experiment, or placeholder project that lacks sufficient implementation for meaningful technical analysis.",
                "recommendation": "For meaningful skill assessment, please analyze repositories that demonstrate real-world problem-solving and substantial code implementation",
            }

        # Documentation-only repositories
        elif await asyncio.to_thread(
            classifier._is_documentation_only_repository, repo_data
        ):
            special_response = {
                "repository_type": "documentation",
                "message": "This is primarily a documentation repository containing curated lists, guides, or references. While there may be minimal scripts or configuration files present, the repository's main purpose is informational rather than functional code implementation.",
                "recommendation": "This type of repository showcases curation and documentation skills rather than coding ability - consider analyzing repositories with substantial implementation for technical assessment",
            }

        # Hello World / Minimal examples
        elif await asyncio.to_thread(classifier._is_hello_world_repository, repo_data):
            special_response = {
                "repository_type": "example",
                "message": "This appears to be a 'Hello World' or tutorial example repository. While useful for learning, such minimal examples don't provide enough complexity to assess real development skills, architectural decisions, or problem-solving abilities.",
                "recommendation": "To showcase your skills, analyze repositories with substantial business logic, multiple components, or real-world applications",
            }

        # Empty repositories
        elif await asyncio.to_thread(classifier._is_empty_repository, repo_data):
            special_response = {
                "repository_type": "empty",
                "message": "This repository is essentially empty, containing only auto-generated files (like README or .gitignore) with no actual code implementation. It may be a newly initialized project, abandoned repository, or placeholder.",
                "recommendation": "No technical skills can be assessed from an empty repository - please select a repository with actual code implementation",
            }

        # Archived repositories
        elif repo_data.is_archived:
            special_response = {
                "repository_type": "archived",
                "message": "This is an archived repository that is no longer actively maintained. Analysis reflects historical state only.",
                "recommendation": "Consider analyzing active repositories for current skill assessment",
            }

        # Unmodified forks
        elif await asyncio.to_thread(classifier._is_unmodified_fork, repo_data):
            special_response = {
                "repository_type": "fork",
                "message": "This appears to be an unmodified fork with no original contributions. Analysis would reflect the original author's work.",
                "recommendation": "Analyze repositories with original contributions for accurate assessment",
            }

        if special_response:
            # Return early with special handling response
            return AnalysisResponse(
                id=None,  # No ID for special response
                repository_url=repository_url,
                context=context,
                formatted_report="",  # Empty for special response
                analysis={
                    "executive_summary": f"{special_response['message']}\n\nRecommendation: {special_response['recommendation']}",
                    "context_analysis": {
                        "context": context,
                        "repository_type": special_response["repository_type"],
                    },
                    "key_insights": [special_response["message"]],
                    "analysis_quality": {
                        "confidence_grade": "N/A",
                        "overall_risk_level": "N/A",
                        "limitations": [
                            "Repository type not suitable for code analysis"
                        ],
                    },
                },
                metadata={
                    "repository_url": repository_url,
                    "repository_name": repo_data.full_name,
                    "analysis_date": datetime.now(timezone.utc).isoformat(),
                    "report_version": config.analysis.report_version,
                    "response_time_seconds": (
                        datetime.now(timezone.utc) - start_time
                    ).total_seconds(),
                    "repository_type": special_response["repository_type"],
                    "special_case": True,
                },
            )

    # Step 3: Perform context-aware analysis (only for analyzable repos)
    from ...core.context_analyzer import AnalysisContext

    context_enum = AnalysisContext(context)
    context_analysis = await asyncio.to_thread(
        context_analyzer.analyze, repo_data, context_enum
    )

    # Step 4: Calculate confidence scores
    confidence_analysis = await asyncio.to_thread(
        confidence_scorer.assess_confidence_and_risk,
        repo_data,
        repo_classification,
        context_analysis,
    )

    # Step 5: Determine if AI analysis is needed (30/70 cost optimization)
    use_ai = _should_use_ai_analysis(
        repo_data, repo_classification, confidence_analysis
    )

    analysis_cost = 0.0
    ai_analysis_result = None

    if use_ai:
        # Step 6: AI-powered analysis for complex cases (with timeout)
        try:
            ai_analysis_result = await asyncio.wait_for(
                asyncio.to_thread(
                    ai_analyzer.analyze_repository,
                    repo_data,
                    subscription_plan=user.subscription_plan,
                ),
                timeout=timeout_config.claude_timeout_s,
            )
            # Get actual cost from AI analysis result
            analysis_cost = (
                ai_analysis_result.cost
                if ai_analysis_result
                else config.analysis.estimated_cost_per_analysis
            )
        except asyncio.TimeoutError:
            logger.error(
                f"AI analysis timed out after {timeout_config.claude_timeout_s}s for {repository_url}"
            )
            raise HTTPException(
                status_code=504,
                detail={
                    "error": "Analysis timeout",
                    "message": f"Repository analysis timed out. This repository ({timeout_config.category}) may be too complex. Please try a smaller repository.",
                    "repository_url": repository_url,
                    "timeout_seconds": timeout_config.claude_timeout_s,
                    "repository_category": timeout_config.category,
                    "suggestion": "Try analyzing a smaller repository or contact support for assistance",
                },
            )

        # Track the cost if budget monitor is available
        if budget_monitor:
            await budget_monitor.track_cost(analysis_cost, user.user_id)

        logger.info(
            f"🤖 AI ANALYSIS used for {repository_url} "
            f"[stars={repo_data.stars}, contributors={repo_data.metrics.unique_contributors}, "
            f"type={repo_classification.repository_type}, cost=${analysis_cost:.4f}]"
        )
    else:
        logger.warning(
            f"📋 TEMPLATE ANALYSIS used for {repository_url} "
            f"[stars={repo_data.stars}, type={repo_classification.repository_type}, "
            f"size={repo_data.size}KB] - Consider if this provides enough value!"
        )

    # Step 7: Generate comprehensive report with subscription plan (with timeout)
    # IMPORTANT: Always pass ai_analysis_result so unified generation has access to evidence patterns
    # The report generator will decide whether to use unified generation based on tier

    # For FREE tier: Check if user still has AI analyses remaining (3/month)
    use_ai_for_free = False
    if user.subscription_plan == SubscriptionPlan.FREE:
        from sqlalchemy import func, select

        from ...database.models import AnalysisResult

        # Get current billing period
        now = datetime.now(timezone.utc)
        billing_period_start = now.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        # Calculate first day of next month
        if now.month == 12:
            billing_period_end = now.replace(
                year=now.year + 1,
                month=1,
                day=1,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )
        else:
            billing_period_end = now.replace(
                month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0
            )

        # Count AI analyses this month (token_count > 0 means AI was used)
        # Use date range comparison instead of strftime for PostgreSQL compatibility
        ai_count_query = select(func.count(AnalysisResult.id)).where(
            AnalysisResult.user_id == user.user_id,
            AnalysisResult.created_at >= billing_period_start,
            AnalysisResult.created_at < billing_period_end,
            AnalysisResult.token_count > 0,
            AnalysisResult.deleted_at.is_(None),
        )
        ai_count_result = await db.execute(ai_count_query)
        ai_count = ai_count_result.scalar() or 0

        # FREE tier gets 3 AI analyses per month
        use_ai_for_free = ai_count < 3

        logger.info(
            f"FREE tier user {user.user_id}: {ai_count}/3 AI analyses used this month. "
            f"{'Using AI' if use_ai_for_free else 'Using templates'} for this analysis."
        )

    try:
        report = await asyncio.wait_for(
            asyncio.to_thread(
                report_generator.generate_report,
                repo_data,
                repo_classification,
                context_analysis,
                context_enum,
                confidence_analysis,
                ai_analysis_result,  # Always pass AI analysis for evidence patterns
                user.subscription_plan,  # Pass user's subscription plan for enhanced metrics
                role=role,  # Pass role for interview question customization
                use_ai_for_free=use_ai_for_free,  # NEW: Allow AI for FREE tier if quota available
            ),
            timeout=timeout_config.backend_timeout_s,
        )
    except ValueError as e:
        # Check for EXTREME_REPO rejection
        if str(e).startswith("EXTREME_REPO:"):
            rejection_msg = str(e).replace("EXTREME_REPO: ", "")
            logger.warning(f"Repository rejected as EXTREME: {repository_url}")
            raise HTTPException(
                status_code=413,
                detail={
                    "error": "Repository too large",
                    "message": rejection_msg,
                    "repository_url": repository_url,
                    "repository_category": "EXTREME",
                    "recommendation": "Use batch analysis for extreme-scale repositories",
                    "alternatives": [
                        "Analyze a specific subdirectory instead",
                        "Use our batch analysis feature (available in Professional tier and above)",
                        "Consider analyzing a smaller sample of the codebase",
                    ],
                },
            )
        # Re-raise other ValueErrors
        raise
    except asyncio.TimeoutError:
        logger.error(
            f"Report generation timed out after {timeout_config.backend_timeout_s}s for {repository_url}"
        )
        raise HTTPException(
            status_code=504,
            detail={
                "error": "Report generation timeout",
                "message": f"Report generation timed out. This repository ({timeout_config.category}) is too complex to analyze within the time limit.",
                "repository_url": repository_url,
                "timeout_seconds": timeout_config.backend_timeout_s,
                "repository_category": timeout_config.category,
                "explanation": timeout_config.explanation,
            },
        )

    # Calculate response time
    response_time = (datetime.now(timezone.utc) - start_time).total_seconds()

    # Generate formatted report if requested
    formatted_report = None
    if output_format and output_format.lower() != "json":
        # Map format strings to ReportFormat enum
        format_mapping = {
            "user_friendly": ReportFormat.USER_FRIENDLY,
            "markdown": ReportFormat.MARKDOWN,
            "html": ReportFormat.HTML,
        }

        if output_format.lower() in format_mapping:
            try:
                formatted_report = report_generator.format_report(
                    report,
                    format_mapping[output_format.lower()],
                    user.subscription_plan.value,  # Pass user's plan for tier-based access
                )
            except Exception as e:
                logger.error(
                    f"Failed to generate {output_format} format: {e}", exc_info=True
                )
                # Continue without formatted report but log the error

    # Convert to clean response with tier-aware evidence extraction
    clean_response = convert_to_clean_response(
        report,
        analysis_cost,
        subscription_tier=(
            user.subscription_plan.value if user.subscription_plan else "free"
        ),
    )

    # Build comprehensive response
    return AnalysisResponse(
        id=None,  # ID is set by the database when stored
        repository_url=repository_url,
        context=context,
        analysis={
            "executive_summary": clean_response.executive_summary,
            "confidence_explanation": clean_response.confidence_explanation,
            "repository_type": clean_response.repository_type,
            # Evidence-based approach - no numerical scores
            "key_strengths": report.key_strengths,
            "primary_concerns": report.primary_concerns,
            "analysis_recommendations": report.analysis_recommendations,
            "interview_focus_areas": report.interview_focus_areas,
            "technical_assessment": (
                _format_section_assessment(report.technical_assessment)
                if report.technical_assessment
                else None
            ),
            "professional_practices": (
                _format_section_assessment(report.professional_practices)
                if report.professional_practices
                else None
            ),
            "communication_skills": (
                _format_section_assessment(report.communication_skills)
                if report.communication_skills
                else None
            ),
            "growth_indicators": (
                _format_section_assessment(report.growth_indicators)
                if report.growth_indicators
                else None
            ),
            "team_fit_analysis": (
                report.evidence_summary.get("team_fit_analysis")
                if report.evidence_summary
                and report.evidence_summary.get("team_fit_analysis")
                else None
            ),
            # NEW AI FEATURES
            "insights": [insight.model_dump() for insight in clean_response.insights],
            "questions": [
                question.model_dump() for question in clean_response.questions
            ],
            "recommendations": [
                rec.model_dump() for rec in clean_response.recommendations
            ],
            # OPERATION FINAL EXORCISM: Include evidence patterns!
            "evidence_patterns": [
                pattern.model_dump() for pattern in clean_response.evidence_patterns
            ],
            # No metrics in evidence-based approach
            # Counts for easy access
            "insights_count": clean_response.insights_count,
            "questions_count": clean_response.questions_count,
            "recommendations_count": clean_response.recommendations_count,
            "evidence_patterns_count": clean_response.evidence_patterns_count,
            # Flags and limitations
            "green_flags": clean_response.green_flags,
            "red_flags": clean_response.red_flags,
            "limitations": clean_response.limitations,
            # Areas to explore - critical for UI display
            "areas_to_explore": clean_response.areas_to_explore,
        },
        metadata={
            "analysis_id": (
                f"analysis_{int(start_time.timestamp())}_{hash(repository_url) % 10000}"
            ),
            "repository_type": clean_response.repository_type,
            "confidence_grade": "N/A",  # No confidence scores in evidence-based approach
            "ai_analysis_used": use_ai,
            "analysis_cost_usd": analysis_cost,
            "token_count": ai_analysis_result.token_count if ai_analysis_result else 0,
            "response_time_seconds": response_time,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cached": False,
            "timeout_config": {
                "frontend_timeout_ms": timeout_config.frontend_timeout_ms,
                "backend_timeout_s": timeout_config.backend_timeout_s,
                "category": timeout_config.category,
                "explanation": timeout_config.explanation,
            },
        },
        formatted_report=formatted_report,
    )


def _get_confidence_grade_from_score(score: float) -> str:
    """Get letter grade from confidence score to ensure consistency."""
    grade_thresholds = [
        (0.9, "A+"),
        (0.8, "A"),
        (0.7, "B+"),
        (0.6, "B"),
        (0.5, "C+"),
        (0.4, "C"),
        (0.0, "D"),
    ]

    for threshold, grade in grade_thresholds:
        if score >= threshold:
            return grade

    return "D"  # Fallback for edge cases


def _format_section_assessment(section: Any) -> dict[str, Any]:
    """Format section assessment for API response with rich contextual data."""
    if not section:
        return {}

    # Base structure with all the rich data
    base_format = {
        # "overall_score": removed in Great Purge
        "confidence": (
            section.confidence.value
            if hasattr(section.confidence, "value")
            else str(section.confidence)
        ),
        "summary": section.summary,
        "details": section.details if hasattr(section, "details") else [],
        "flags": (
            [_format_flag(f) for f in section.flags]
            if hasattr(section, "flags")
            else []
        ),
        "limitations": section.limitations if hasattr(section, "limitations") else [],
        "sub_metrics": (
            [_format_sub_metric(sm) for sm in section.sub_metrics]
            if hasattr(section, "sub_metrics") and section.sub_metrics
            else []
        ),
    }

    # Remove score-based metric breakdowns per The Great Purge
    # Evidence patterns are now in sub_metrics instead

    return base_format


def _format_flag(flag: Any) -> dict[str, Any]:
    """Format flag for API response."""
    return {
        "type": flag.type,
        "category": flag.category,
        "description": flag.description,
        "severity": flag.severity if hasattr(flag, "severity") else None,
        "evidence": flag.evidence if hasattr(flag, "evidence") else [],
    }


def _format_sub_metric(sub_metric: Any) -> dict[str, Any]:
    """Format sub-metric for API response - evidence-based only."""
    base_metric = {
        "name": sub_metric.name,
        "evidence": sub_metric.evidence,
        "context": sub_metric.context if hasattr(sub_metric, "context") else "",
        "insight": sub_metric.insight,
    }

    # Add confidence range if available (EnhancedSubMetric)
    if hasattr(sub_metric, "confidence_range"):
        base_metric["confidence_range"] = {
            "low": sub_metric.confidence_range[0],
            "high": sub_metric.confidence_range[1],
        }

    # Add interview prompt if available
    if hasattr(sub_metric, "interview_prompt"):
        base_metric["interview_prompt"] = sub_metric.interview_prompt

    # Add metric type if available
    if hasattr(sub_metric, "metric_type"):
        base_metric["metric_type"] = sub_metric.metric_type

    return base_metric


def _get_model_for_tier(subscription_plan: SubscriptionPlan) -> str:
    """Get the AI model used for a subscription tier."""
    from ...core.tier_config import get_model_for_tier as get_model

    # Map subscription plan to tier name
    tier_map = {
        SubscriptionPlan.FREE: "free",
        SubscriptionPlan.BASIC: "basic",
        SubscriptionPlan.PROFESSIONAL: "professional",
        SubscriptionPlan.ENTERPRISE: "enterprise",
        SubscriptionPlan.SCALE_PLUS: "scale_plus",
    }

    tier_name = tier_map.get(subscription_plan, "free")
    return get_model(tier_name, "main")


def _should_use_ai_analysis(
    repo_data: Any, classification: Any, confidence: Any
) -> bool:
    """
    Determine if AI analysis is needed based on repository value and complexity.

    Prioritizes AI analysis for repositories that matter:
    - Popular repositories (community validated)
    - Production/library code (real-world impact)
    - Active development (ongoing projects)
    - Complex codebases (architectural decisions)

    Only uses templates for truly trivial cases to maintain quality.

    Args:
        repo_data: Repository data from GitHub
        classification: Repository classification result
        confidence: Confidence analysis result

    Returns:
        bool: True if AI analysis should be used
    """
    # ALWAYS use AI for high-value repositories
    if (
        # Popular repositories deserve detailed analysis
        repo_data.stars > 50
        or
        # Active community involvement
        repo_data.metrics.unique_contributors > 5
        or
        # Production/library code ALWAYS gets AI analysis
        (
            classification.repository_type
            and classification.repository_type.value
            in ["production", "library", "framework"]
        )
        or
        # Substantial codebases with architecture decisions
        repo_data.size > 500  # >500KB
        or
        # Multi-language projects show versatility
        len(repo_data.languages) > 2
        or
        # Active development patterns
        repo_data.metrics.commit_frequency > 2  # >2 commits/week average
    ):
        logger.info(
            f"Using AI analysis for {repo_data.full_name}: "
            f"stars={repo_data.stars}, type={classification.repository_type}, "
            f"size={repo_data.size}KB"
        )
        return True

    # Template ONLY for truly obvious/trivial cases:
    if (
        # Completely abandoned projects
        (
            classification.repository_type
            and classification.repository_type.value == "abandoned"
            and repo_data.metrics.days_since_last_commit > 365  # 1+ year inactive
        )
        or
        # Empty or hello-world repositories
        (
            repo_data.size < 50  # <50KB
            and len(repo_data.file_structure) < 5
            and repo_data.stars == 0
        )
        or
        # Clear homework/tutorial with no value
        (
            classification.repository_type
            and classification.repository_type.value == "learning"
            and repo_data.stars == 0
            and repo_data.forks == 0
            and repo_data.size < 100
        )
    ):
        logger.info(
            f"Using template analysis for trivial repo {repo_data.full_name}: "
            f"type={classification.repository_type}, size={repo_data.size}KB"
        )
        return False

    # Default to AI for everything else - quality over cost savings
    logger.info(
        f"Defaulting to AI analysis for {repo_data.full_name} to ensure quality"
    )
    return True


@router.post("/cancel/{task_id}")
async def cancel_analysis(
    task_id: str,
    user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Cancel a running single analysis task.

    Allows cancellation within the smart timing window:
    - Single analysis: 10 seconds after start
    - Only cancels if task is still in cancellation window

    Args:
        task_id: The task ID to cancel
        user: Current authenticated user

    Returns:
        Dict with cancellation status and message

    Raises:
        HTTPException:
            - 404: Task not found
            - 403: Permission denied (not your task)
            - 400: Cancellation window expired
    """
    try:
        cancellation_service = get_cancellation_service()

        # Attempt to cancel the task
        success, message = await cancellation_service.cancel_task(task_id, user.user_id)

        if not success:
            # Determine appropriate HTTP status code based on message
            if "not found" in message.lower():
                raise HTTPException(status_code=404, detail=message)
            elif "permission denied" in message.lower():
                raise HTTPException(status_code=403, detail=message)
            elif "expired" in message.lower():
                raise HTTPException(status_code=400, detail=message)
            else:
                raise HTTPException(status_code=400, detail=message)

        logger.info(f"Analysis task {task_id} cancelled by user {user.user_id}")

        return {
            "task_id": task_id,
            "status": "cancelled",
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel task {task_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to cancel analysis: {str(e)}"
        )


@router.post("/batch/cancel/{batch_id}")
async def cancel_batch_analysis(
    batch_id: str,
    user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Cancel a running batch analysis.

    Allows cancellation within the smart timing window:
    - Batch analysis: 30 seconds after start
    - Only cancels if batch is still in cancellation window

    Args:
        batch_id: The batch ID to cancel
        user: Current authenticated user

    Returns:
        Dict with cancellation status and message

    Raises:
        HTTPException:
            - 404: Batch not found
            - 403: Permission denied (not your batch)
            - 400: Cancellation window expired
    """
    try:
        cancellation_service = get_cancellation_service()

        # Attempt to cancel the batch task
        success, message = await cancellation_service.cancel_task(
            batch_id, user.user_id
        )

        if not success:
            # Determine appropriate HTTP status code based on message
            if "not found" in message.lower():
                raise HTTPException(status_code=404, detail=message)
            elif "permission denied" in message.lower():
                raise HTTPException(status_code=403, detail=message)
            elif "expired" in message.lower():
                raise HTTPException(status_code=400, detail=message)
            else:
                raise HTTPException(status_code=400, detail=message)

        logger.info(f"Batch analysis {batch_id} cancelled by user {user.user_id}")

        return {
            "batch_id": batch_id,
            "status": "cancelled",
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel batch {batch_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to cancel batch analysis: {str(e)}"
        )


@router.get("/tasks/{task_id}/status")
async def get_task_status(
    task_id: str,
    user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Get the status of a running task.

    Args:
        task_id: The task ID to check
        user: Current authenticated user

    Returns:
        Dict with task status and timing information

    Raises:
        HTTPException:
            - 404: Task not found
            - 403: Permission denied (not your task)
    """
    try:
        cancellation_service = get_cancellation_service()

        # Get task information
        task = cancellation_service.get_task_info(task_id)

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Verify ownership
        if task.user_id != user.user_id:
            raise HTTPException(
                status_code=403,
                detail="Permission denied: task belongs to different user",
            )

        # Check if task can be cancelled
        can_cancel, cancel_reason = cancellation_service.can_cancel_task(task_id)

        return {
            "task_id": task_id,
            "task_type": task.task_type.value,
            "status": task.status.value,
            "started_at": task.started_at.isoformat(),
            "cancel_deadline": task.cancel_deadline.isoformat(),
            "can_cancel": can_cancel,
            "cancel_reason": cancel_reason,
            "time_remaining_seconds": max(
                0,
                int(
                    (task.cancel_deadline - datetime.now(timezone.utc)).total_seconds()
                ),
            ),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task status {task_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get task status: {str(e)}"
        )


@router.get("/export/{analysis_id}")
async def export_analysis(
    analysis_id: str,
    format: str = "json",
    user_id: str = Depends(require_api_access),
) -> Response:
    """
    Export analysis results in various formats.

    Supported formats:
    - json: Raw JSON data
    - html: Styled HTML report
    - pdf: PDF-ready text format
    - markdown: Markdown format

    Args:
        analysis_id: The analysis ID from the metadata
        format: Export format (json, html, pdf, markdown)
        user_id: Authenticated user ID

    Returns:
        Response with appropriate content type and file attachment
    """
    try:
        # For now, we'll need to fetch from cache or rerun analysis
        # In production, you'd store analysis results in a database

        # Validate format
        valid_formats = ["json", "html", "pd", "markdown"]
        if format.lower() not in valid_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid format. Must be one of: {', '.join(valid_formats)}",
            )

        # For demonstration, create a sample export
        # In production, you'd fetch the actual analysis data
        sample_data: Dict[str, Any] = {
            "repository_url": "https://github.com/example/repo",
            "analysis_date": datetime.now(timezone.utc).isoformat(),
            "assessment_type": "evidence-based",
            "executive_summary": "Strong candidate with excellent technical skills...",
            "evidence_patterns": {
                "technical_patterns": [
                    "Strong testing practices",
                    "Clean architecture",
                ],
                "behavioral_patterns": [
                    "Consistent commit messages",
                    "Active collaboration",
                ],
                "quality_indicators": ["High code coverage", "Well-documented code"],
            },
        }

        # Get evidence patterns with proper type
        evidence_patterns: Dict[str, List[Any]] = sample_data["evidence_patterns"]

        # Generate report based on format
        if format.lower() == "json":
            content = json.dumps(sample_data, indent=2)
            media_type = "application/json"
            filename = f"analysis_{analysis_id}.json"

        elif format.lower() == "html":
            # Generate HTML report
            html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>GitHub Analysis Report - {analysis_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        .summary {{ background: #f0f0f0; padding: 20px; border-radius: 8px; }}
        .score {{ font-size: 24px; color: #007bff; }}
    </style>
</head>
<body>
    <h1>GitHub Repository Analysis Report</h1>
    <div class="summary">
        <h2>Executive Summary</h2>
        <p>{sample_data['executive_summary']}</p>
        <p><strong>Evidence Patterns Found:</strong></p>
        <ul>{' '.join(['<li>' + p + '</li>' for p in evidence_patterns.get('technical_patterns', [])])}</ul>
    </div>
    <p><em>Analysis Date: {sample_data['analysis_date']}</em></p>
</body>
</html>
"""
            content = html_template
            media_type = "text/html"
            filename = f"analysis_{analysis_id}.html"

        elif format.lower() == "pd":
            # Generate PDF-ready text
            pdf_text = f"""
GITHUB REPOSITORY ANALYSIS REPORT
================================

Analysis ID: {analysis_id}
Repository: {sample_data["repository_url"]}
Date: {sample_data["analysis_date"]}

EXECUTIVE SUMMARY
----------------
{sample_data["executive_summary"]}

EVIDENCE PATTERNS
----------------
Technical: {", ".join(evidence_patterns.get("technical_patterns", []))}
Behavioral: {", ".join(evidence_patterns.get("behavioral_patterns", []))}
Quality: {", ".join(evidence_patterns.get("quality_indicators", []))}

================================
Generated by Exiqus GitHub Analyzer
"""
            content = pdf_text
            media_type = "text/plain"
            filename = f"analysis_{analysis_id}_pdf_ready.txt"

        elif format.lower() == "markdown":
            # Generate Markdown report
            markdown_content = """
# GitHub Repository Analysis Report

**Analysis ID:** {analysis_id}
**Repository:** {sample_data['repository_url']}
**Date:** {sample_data['analysis_date']}

## Executive Summary

{sample_data['executive_summary']}

## Evidence Patterns

**Technical Patterns:**
{chr(10).join(['- ' + p for p in evidence_patterns.get('technical_patterns', [])])}

**Behavioral Patterns:**
{chr(10).join(['- ' + p for p in evidence_patterns.get('behavioral_patterns', [])])}

**Quality Indicators:**
{chr(10).join(['- ' + p for p in evidence_patterns.get('quality_indicators', [])])}

---
*Generated by Exiqus GitHub Analyzer*
"""
            content = markdown_content
            media_type = "text/markdown"
            filename = f"analysis_{analysis_id}.md"

        # Return as downloadable file
        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(content.encode())),
                "Cache-Control": "private, max-age=3600",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export failed for analysis {analysis_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to export analysis: {str(e)}"
        )


async def _cache_analysis_result(cache_key: str, analysis_data: str) -> None:
    """
    Background task to cache analysis results.

    Args:
        cache_key: Redis cache key
        analysis_data: Serialized analysis result
    """
    try:
        # Cache for 24 hours (86400 seconds)
        success = await redis_service.set(cache_key, analysis_data, ttl=86400)
        if success:
            logger.debug(f"Analysis result cached: {cache_key}")
        else:
            logger.warning(f"Failed to cache analysis result: {cache_key}")
    except Exception as e:
        logger.error(f"Cache operation failed for {cache_key}: {e}")
        # Don't raise - caching failure shouldn't break the API


async def _store_analysis_result(
    db: AsyncSession,
    user: User,
    repository_url: str,
    repository_name: str,
    context: str,
    analysis_response: AnalysisResponse,
    processing_time_ms: int,
    token_count: Optional[int] = None,
    api_cost: Optional[float] = None,
    batch_id: Optional[str] = None,
    github_username: Optional[str] = None,
    role: Optional[str] = None,
) -> Optional[str]:
    """
    Store analysis result in the database with evidence-based data and consent.

    Args:
        db: Database session
        user: User object
        repository_url: Repository URL
        repository_name: Repository name
        context: Analysis context
        analysis_response: Analysis response object
        processing_time_ms: Processing time in milliseconds
        token_count: Token count (if available)
        api_cost: API cost (if available)
        batch_id: Batch ID if part of a batch
        github_username: GitHub username for candidate linking (paid tiers only)
        role: Role for context consistency (paid tiers only)

    Returns:
        Optional[str]: Analysis ID if stored successfully, None if storage failed
    """
    try:
        # Generate UUID for the analysis
        analysis_id = str(uuid.uuid4())

        # Get user consent settings
        user_consent = ConsentService.get_user_consent(user)
        consent_snapshot = ConsentService.create_consent_snapshot(user)

        # Check if data should be eligible for training
        training_eligible = ConsentService.should_allow_training(user_consent)

        # Extract analysis data
        analysis_data = analysis_response.analysis

        # Determine analysis method - check if evidence-based fields exist
        is_evidence_based = any(
            key in analysis_data
            for key in ["screening_insights", "evidence_patterns", "evidence_strength"]
        )
        analysis_method = "evidence_based" if is_evidence_based else "legacy"

        # Extract evidence-based fields if present
        evidence_patterns = None
        screening_insights = None
        confidence_explanation = None
        technical_patterns = None
        collaboration_patterns = None
        quality_indicators = None
        temporal_insights = None
        skill_evolution = None
        behavioral_analysis = None
        security_practices = None
        context_alignment = None
        verification_gaps = None

        if is_evidence_based:
            # Extract evidence patterns (already correct)
            evidence_patterns = json.dumps(analysis_data.get("evidence_patterns", []))

            # Extract insights array (was incorrectly looking for "screening_insights")
            screening_insights = json.dumps(analysis_data.get("insights", []))

            # Get confidence explanation directly from top level
            confidence_explanation = analysis_data.get("confidence_explanation", "")

            # Extract assessment sections - check both top level and nested in 'evidence'
            evidence_data = analysis_data.get("evidence", {})

            # Try to get from top level first, then from evidence field
            technical_assessment = analysis_data.get(
                "technical_assessment"
            ) or evidence_data.get("technical_patterns")
            professional_practices = analysis_data.get(
                "professional_practices"
            ) or evidence_data.get("collaboration_patterns")
            communication_skills = analysis_data.get(
                "communication_skills"
            ) or evidence_data.get("quality_indicators")
            growth_indicators = analysis_data.get(
                "growth_indicators"
            ) or evidence_data.get("temporal_insights")

            # Store these as JSON strings for database columns (None if missing)
            technical_patterns = (
                json.dumps(technical_assessment) if technical_assessment else None
            )
            collaboration_patterns = (
                json.dumps(professional_practices) if professional_practices else None
            )
            quality_indicators = (
                json.dumps(communication_skills) if communication_skills else None
            )
            temporal_insights = (
                json.dumps(growth_indicators) if growth_indicators else None
            )

            # Extract questions and recommendations
            # Check if we have nested evidence structure
            skill_evolution_data = analysis_data.get("questions") or evidence_data.get(
                "skill_evolution"
            )
            behavioral_analysis_data = analysis_data.get(
                "recommendations"
            ) or evidence_data.get("behavioral_analysis")

            skill_evolution = (
                json.dumps(skill_evolution_data)
                if skill_evolution_data
                else json.dumps([])
            )
            behavioral_analysis = (
                json.dumps(behavioral_analysis_data)
                if behavioral_analysis_data
                else json.dumps([])
            )

            # Extract green_flags and red_flags (important for frontend indicators tab)
            # Store green_flags in security_practices field
            security_practices_data = analysis_data.get(
                "green_flags"
            ) or evidence_data.get("security_practices")
            security_practices = (
                json.dumps(security_practices_data)
                if security_practices_data
                else json.dumps([])
            )

            # Store red_flags in context_alignment field
            # But also check for context_alignment from the test data
            context_alignment_data = analysis_data.get(
                "red_flags"
            ) or analysis_data.get("context_alignment")
            context_alignment = (
                json.dumps(context_alignment_data)
                if context_alignment_data
                else json.dumps([])
            )

            # Store areas_to_explore in verification_gaps field
            verification_gaps_data = analysis_data.get(
                "areas_to_explore"
            ) or analysis_data.get("verification_gaps")
            verification_gaps = (
                json.dumps(verification_gaps_data)
                if verification_gaps_data
                else json.dumps([])
            )

        # Create the analysis result record
        # NOTE: Following the Great Purge - NO SCORES stored for evidence-based analysis
        analysis_result = AnalysisResult(
            id=analysis_id,
            status=AnalysisStatus.COMPLETED,  # Mark as completed when storing
            user_id=user.user_id,
            repository_url=repository_url,
            repository_name=repository_name,
            context=context,
            github_username=github_username,  # Links to candidate for paid tiers, None for free
            role=role,  # Store role for context consistency
            # Legacy fields removed - no longer in database (Great Purge)
            full_analysis=json.dumps(analysis_response.model_dump(mode="json")),
            processing_time_ms=processing_time_ms,
            token_count=token_count,
            api_cost=api_cost,
            allow_training=user_consent.get("training_usage", True),
            batch_id=batch_id,
            # Evidence-based fields
            evidence_patterns=evidence_patterns,
            screening_insights=screening_insights,
            confidence_explanation=confidence_explanation,
            technical_patterns=technical_patterns,
            collaboration_patterns=collaboration_patterns,
            quality_indicators=quality_indicators,
            temporal_insights=temporal_insights,
            skill_evolution=skill_evolution,
            behavioral_analysis=behavioral_analysis,
            security_practices=security_practices,
            context_alignment=context_alignment,
            verification_gaps=verification_gaps,
            analysis_method=analysis_method,
            evidence_version="1.0.0",
            # Privacy/consent fields
            data_consent=json.dumps(consent_snapshot),
            consent_updated_at=datetime.now(timezone.utc),
            training_eligible=training_eligible,
        )

        db.add(analysis_result)
        await db.commit()

        logger.info(
            f"Analysis result stored: {analysis_id} for {repository_url} "
            f"(method: {analysis_method}, training_eligible: {training_eligible})"
        )
        return analysis_id

    except Exception as e:
        logger.error(f"Failed to store analysis result: {e}", exc_info=True)
        await db.rollback()
        # Don't raise - storage failure shouldn't break the API response
        # Return None instead of empty string to properly indicate failure
        return None


@router.get("/analyses", response_model=AnalysisResultList)
async def get_user_analyses(
    cursor: Optional[str] = None,
    limit: int = 20,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> AnalysisResultList:
    """
    Get user's analysis history with pagination.

    Args:
        cursor: Pagination cursor (ISO timestamp)
        limit: Number of results per page (1-100)
        user: Current authenticated user
        db: Database session

    Returns:
        AnalysisResultList: Paginated list of analyses
    """
    try:
        # Validate limit
        limit = min(max(limit, 1), 100)

        # Build base query
        from datetime import datetime

        from sqlalchemy import and_, desc, func, select

        query = select(AnalysisResult).where(
            and_(
                AnalysisResult.user_id == user.user_id,
                AnalysisResult.deleted_at.is_(None),  # Exclude soft-deleted
            )
        )

        # Apply cursor if provided
        if cursor:
            try:
                cursor_time = datetime.fromisoformat(cursor.replace("Z", "+00:00"))
                query = query.where(AnalysisResult.created_at < cursor_time)
            except ValueError:
                logger.warning(f"Invalid cursor format: {cursor}")

        # Order by created_at descending and limit
        query = query.order_by(desc(AnalysisResult.created_at)).limit(limit + 1)

        # Execute query
        result = await db.execute(query)
        analyses = result.scalars().all()

        # Check if there are more results
        has_next = len(analyses) > limit
        if has_next:
            analyses = analyses[:limit]  # Remove the extra item

        # Convert to response models
        items = []
        for analysis in analyses:
            # Parse the stored JSON to get evidence-based data
            try:
                full_data = json.loads(analysis.full_analysis)
                analysis_data = full_data.get("analysis", {})
                evidence_strength = analysis_data.get("evidence_strength")
                key_insights = analysis_data.get("key_insights", [])
                key_insight = key_insights[0] if key_insights else None
                # Get the executive summary
                executive_summary = analysis_data.get("executive_summary", "")
                # Use executive summary as the key insight if no key insights
                if not key_insight and executive_summary:
                    # Take first sentence or first 200 chars of executive summary
                    key_insight = (
                        executive_summary.split(".")[0] + "."
                        if "." in executive_summary
                        else executive_summary[:200]
                    )
            except Exception:
                # Fallback for older analyses - convert score to evidence strength
                # Fallback - no scores in Great Purge
                evidence_strength = None
                key_insight = "Evidence-based analysis"

            items.append(
                AnalysisResultListItem(
                    id=analysis.id,
                    repository_name=analysis.repository_name,
                    repository_url=analysis.repository_url,
                    context=analysis.context,
                    evidence_strength=evidence_strength,
                    key_insight=key_insight,
                    created_at=analysis.created_at,
                    batch_id=analysis.batch_id,  # Include batch_id
                )
            )

        # Determine next cursor
        next_cursor = None
        if has_next and items:
            next_cursor = items[-1].created_at.isoformat()

        # Determine if there's a previous page (if cursor was provided)
        has_prev = cursor is not None

        # Get total count (optional, can be expensive for large datasets)
        count_query = select(func.count()).where(
            and_(
                AnalysisResult.user_id == user.user_id,
                AnalysisResult.deleted_at.is_(None),
            )
        )
        total_result = await db.execute(count_query)
        total_count = total_result.scalar()

        # Get weekly count (analyses in the last 7 days)
        from datetime import timedelta

        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        weekly_count_query = select(func.count()).where(
            and_(
                AnalysisResult.user_id == user.user_id,
                AnalysisResult.deleted_at.is_(None),
                AnalysisResult.created_at >= seven_days_ago,
            )
        )
        weekly_result = await db.execute(weekly_count_query)
        weekly_count = weekly_result.scalar()

        return AnalysisResultList(
            items=items,
            cursor=next_cursor,
            has_next=has_next,
            has_prev=has_prev,
            total_count=total_count,
            weekly_count=weekly_count,
        )

    except Exception as e:
        logger.error(f"Failed to fetch user analyses: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch analysis history")


@router.get("/analyses/{analysis_id}", response_model=AnalysisResultResponse)
async def get_analysis_by_id(
    analysis_id: str,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> AnalysisResultResponse:
    """
    Get a specific analysis by ID.

    Args:
        analysis_id: Analysis ID
        user: Current authenticated user
        db: Database session

    Returns:
        AnalysisResultResponse: Full analysis details
    """
    try:
        from sqlalchemy import and_, select

        # Query for the specific analysis
        query = select(AnalysisResult).where(
            and_(
                AnalysisResult.id == analysis_id,
                AnalysisResult.user_id == user.user_id,
                AnalysisResult.deleted_at.is_(None),
            )
        )

        result = await db.execute(query)
        analysis = result.scalar_one_or_none()

        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")

        # Parse the full analysis JSON
        full_analysis = json.loads(analysis.full_analysis)

        # Extract evidence-based fields from full_analysis
        analysis_data = full_analysis.get("analysis", {})
        evidence_strength = analysis_data.get("evidence_strength", None)
        key_insights = analysis_data.get("key_insights", None)
        data_completeness = analysis_data.get("data_completeness", None)

        return AnalysisResultResponse(
            id=analysis.id,
            user_id=analysis.user_id,
            repository_url=analysis.repository_url,
            repository_name=analysis.repository_name,
            context=analysis.context,
            github_username=analysis.github_username,
            evidence_strength=evidence_strength,
            key_insights=key_insights,
            data_completeness=data_completeness,
            full_analysis=full_analysis,
            analysis_version=analysis.analysis_version,
            processing_time_ms=analysis.processing_time_ms,
            token_count=analysis.token_count,
            api_cost=analysis.api_cost,
            allow_training=analysis.allow_training,
            created_at=analysis.created_at,
            updated_at=analysis.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch analysis {analysis_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch analysis")


@router.delete("/analyses/{analysis_id}", status_code=204)
async def delete_analysis(
    analysis_id: str,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """
    Soft delete an analysis.

    Args:
        analysis_id: Analysis ID to delete
        user: Current authenticated user
        db: Database session
    """
    try:
        from datetime import datetime, timezone

        from sqlalchemy import and_, select, update

        # Check if analysis exists and belongs to user
        query = select(AnalysisResult).where(
            and_(
                AnalysisResult.id == analysis_id,
                AnalysisResult.user_id == user.user_id,
                AnalysisResult.deleted_at.is_(None),
            )
        )

        result = await db.execute(query)
        analysis = result.scalar_one_or_none()

        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")

        # Soft delete by setting deleted_at
        update_query = (
            update(AnalysisResult)
            .where(AnalysisResult.id == analysis_id)
            .values(deleted_at=datetime.now(timezone.utc))
        )

        await db.execute(update_query)
        await db.commit()

        logger.info(f"Analysis {analysis_id} soft deleted by user {user.user_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete analysis {analysis_id}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete analysis")


@router.get("/analysis/batch/{batch_id}", response_model=Dict[str, Any])
async def get_batch_status(
    batch_id: str,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Get status and results of a batch analysis.

    Returns:
        Dictionary containing:
        - batch_id: The batch identifier
        - status: Overall batch status (pending/processing/completed/failed)
        - total_repositories: Total number of repositories in batch
        - completed: Number of completed analyses
        - failed: Number of failed analyses
        - results: List of analysis results (when completed)
    """
    try:
        # Batch features require Professional, Enterprise, or Scale+ tier
        if user.subscription_plan not in [
            SubscriptionPlan.PROFESSIONAL,
            SubscriptionPlan.ENTERPRISE,
            SubscriptionPlan.SCALE_PLUS,
        ]:
            raise HTTPException(
                status_code=403,
                detail="Batch features require Professional, Enterprise, or Scale+ plan",
            )

        # Query all analyses for this batch
        from sqlalchemy import select

        query = select(AnalysisResult).where(
            AnalysisResult.batch_id == batch_id,
            AnalysisResult.user_id == user.user_id,
            AnalysisResult.deleted_at.is_(None),
        )

        result = await db.execute(query)
        analyses = result.scalars().all()

        if not analyses:
            raise HTTPException(status_code=404, detail="Batch not found")

        # Build results from stored analyses
        results = []
        for analysis in analyses:
            # Parse the full analysis JSON
            full_analysis = json.loads(analysis.full_analysis)

            result_data = {
                "repository_url": analysis.repository_url,
                "analysis_id": analysis.id,
                "context": analysis.context,
                # Obsolete scoring fields removed in Great Purge
                "created_at": analysis.created_at.isoformat(),
                "processing_time_ms": analysis.processing_time_ms,
                "analysis": full_analysis.get("analysis", {}),
                "metadata": full_analysis.get("metadata", {}),
            }

            results.append(result_data)

        # All analyses stored in DB are completed
        total = len(analyses)

        return {
            "batch_id": batch_id,
            "status": "completed",
            "total_repositories": total,
            "completed": total,
            "failed": 0,  # Failed analyses are not stored in DB
            "results": results,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get batch status for {batch_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve batch status")


@router.get("/analysis/batch/{batch_id}/export")
async def export_batch_results(
    batch_id: str,
    format: str = Query("csv", description="Export format: csv, json, or zip"),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    """
    Export batch analysis results in CSV, JSON, or ZIP format.

    Args:
        batch_id: The batch ID to export
        format: Export format - 'csv', 'json', or 'zip' (default: csv)
        user: Current authenticated user
        db: Database session

    Returns:
        File response with appropriate content type
    """
    try:
        # Batch features require Professional, Enterprise, or Scale+ tier
        if user.subscription_plan not in [
            SubscriptionPlan.PROFESSIONAL,
            SubscriptionPlan.ENTERPRISE,
            SubscriptionPlan.SCALE_PLUS,
        ]:
            raise HTTPException(
                status_code=403,
                detail="Batch export features require Professional, Enterprise, or Scale+ plan",
            )

        from sqlalchemy import and_, select

        # Validate format
        if format not in ["csv", "json", "zip"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid format. Supported formats: csv, json, zip",
            )

        # First check if the batch exists
        batch_query = select(BatchAnalysis).where(
            and_(
                BatchAnalysis.batch_id == batch_id,
                BatchAnalysis.user_id == user.user_id,
            )
        )
        batch_result = await db.execute(batch_query)
        batch = batch_result.scalar_one_or_none()

        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")

        # Query successful batch results
        query = (
            select(AnalysisResult)
            .where(
                and_(
                    AnalysisResult.batch_id == batch_id,
                    AnalysisResult.user_id == user.user_id,
                    AnalysisResult.deleted_at.is_(None),
                )
            )
            .order_by(AnalysisResult.created_at)
        )

        result = await db.execute(query)
        analyses = result.scalars().all()

        # Check if this is a failed-only batch
        if not analyses and batch.failed_count > 0:
            # For batches with only failed analyses, return a special response
            export_data = {
                "batch_id": batch_id,
                "export_date": datetime.now(timezone.utc).isoformat(),
                "total_repositories": batch.repository_count,
                "successful_count": 0,
                "failed_count": batch.failed_count,
                "status": batch.status,
                "message": "This batch contains only failed analyses. No successful analysis data to export.",
                "error_messages": (
                    json.loads(batch.error_messages) if batch.error_messages else []
                ),
            }

            if format == "json":
                failed_content: Union[str, bytes] = json.dumps(export_data, indent=2)
                failed_media_type = "application/json"
                failed_filename = f"batch_{batch_id}_failed_export.json"
            elif format == "csv":
                # For CSV, create a simple summary
                import csv
                import io

                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(
                    [
                        "Batch ID",
                        "Status",
                        "Total Repositories",
                        "Failed Count",
                        "Message",
                    ]
                )
                writer.writerow(
                    [
                        batch_id,
                        batch.status,
                        batch.repository_count,
                        batch.failed_count,
                        "Batch contains only failed analyses",
                    ]
                )
                failed_content = output.getvalue()
                failed_media_type = "text/csv"
                failed_filename = f"batch_{batch_id}_failed_export.csv"
            else:  # zip
                # For ZIP, just include a summary JSON file
                import zipfile
                from io import BytesIO

                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    summary_json = json.dumps(export_data, indent=2)
                    zip_file.writestr(f"batch_{batch_id}_summary.json", summary_json)
                failed_content = zip_buffer.getvalue()
                failed_media_type = "application/zip"
                failed_filename = f"batch_{batch_id}_failed_export.zip"

            return Response(
                content=failed_content,
                media_type=failed_media_type,
                headers={
                    "Content-Disposition": f"attachment; filename={failed_filename}"
                },
            )

        # Export based on format
        if format == "json":
            # JSON export
            import json

            full_export_data: Dict[str, Any] = {
                "batch_id": batch_id,
                "export_date": datetime.now(timezone.utc).isoformat(),
                "total_analyses": len(analyses),
                "analyses": [],
            }

            for analysis in analyses:
                try:
                    full_analysis = json.loads(analysis.full_analysis)

                    # Handle different data structures
                    if isinstance(full_analysis, dict):
                        analysis_data = full_analysis.get("analysis", {})
                    else:
                        # If it's not a dict, use empty defaults
                        analysis_data = {}

                    # Safely extract nested data
                    executive_summary = (
                        analysis_data.get("executive_summary", "")
                        if isinstance(analysis_data, dict)
                        else ""
                    )
                    raw_evidence = (
                        analysis_data.get("evidence_patterns", {})
                        if isinstance(analysis_data, dict)
                        else {}
                    )
                    # Clean evidence patterns - only include what's shown in UI
                    evidence_patterns = {}
                    if isinstance(raw_evidence, dict):
                        # Only include the actual evidence pattern lists
                        evidence_patterns = {
                            "technical_patterns": raw_evidence.get(
                                "technical_patterns", []
                            ),
                            "behavioral_patterns": raw_evidence.get(
                                "behavioral_patterns", []
                            ),
                            "quality_indicators": raw_evidence.get(
                                "quality_indicators", []
                            ),
                        }
                    insights = (
                        analysis_data.get("insights", [])
                        if isinstance(analysis_data, dict)
                        else []
                    )
                    recommendations = (
                        analysis_data.get("recommendations", [])
                        if isinstance(analysis_data, dict)
                        else []
                    )

                except (json.JSONDecodeError, TypeError):
                    # If JSON parsing fails, use empty defaults
                    executive_summary = ""
                    evidence_patterns = {}
                    insights = []
                    recommendations = []

                full_export_data["analyses"].append(
                    {
                        "repository_url": analysis.repository_url,
                        "repository_name": analysis.repository_name,
                        "context": analysis.context,
                        "analyzed_at": analysis.created_at.isoformat(),
                        "processing_time_ms": analysis.processing_time_ms,
                        "executive_summary": executive_summary,
                        "evidence_patterns": evidence_patterns,
                        "insights": insights,
                        "recommendations": recommendations,
                    }
                )

            content: Union[str, bytes] = json.dumps(full_export_data, indent=2)
            media_type = "application/json"
            filename = f"batch_{batch_id}_export.json"

        elif format == "csv":
            # CSV export
            import csv
            import io
            import json

            output = io.StringIO()
            writer = csv.writer(output)

            # Write headers
            headers = [
                "Repository URL",
                "Repository Name",
                "Context",
                "Analyzed At",
                "Processing Time (ms)",
                "Summary",
                "Analysis Confidence Level",
                "Positive Indicators",
                "Key Insights",
                "Evidence Patterns",
                "Interview Questions (Full Detail)",
                "Recommendations (Full Detail)",
                "Areas to Explore",
            ]
            writer.writerow(headers)

            # Write data rows
            for analysis in analyses:
                full_analysis = json.loads(analysis.full_analysis)
                analysis_data = full_analysis.get("analysis", {})

                # Get executive summary - just the text
                exec_summary = analysis_data.get("executive_summary", "")
                summary_text = exec_summary if isinstance(exec_summary, str) else ""

                # Get insights - extract full description from dict format
                insights = analysis_data.get("insights", [])
                key_insights = "\n".join(
                    [
                        (
                            f"• {i.get('description', '')}"
                            if isinstance(i, dict)
                            else f"• {str(i)}"
                        )
                        for i in insights
                    ]
                )

                # Get ALL evidence patterns - they contain technical, behavioral, etc.
                evidence_patterns = analysis_data.get("evidence_patterns", [])
                all_patterns = []
                for pattern in evidence_patterns:
                    if isinstance(pattern, dict):
                        insight = pattern.get("insight", "")
                        evidence_text = pattern.get("evidence", "")
                        # Combine insight and evidence for display
                        pattern_text = (
                            f"{insight}: {evidence_text}" if insight else evidence_text
                        )
                        all_patterns.append(pattern_text)

                evidence_patterns_text = "\n".join([f"• {p}" for p in all_patterns])

                # Get interview questions with FULL details
                questions = analysis_data.get("questions", [])
                questions_full = []
                for q in questions:
                    if isinstance(q, dict):
                        question = q.get("question", "")
                        category = q.get("category", "")
                        evidence_ref = q.get("evidence_reference", "")
                        follow_ups = q.get("follow_ups", [])
                        listening = q.get("what_to_listen_for", "")
                        context = q.get("context_relevance", "")

                        q_detail = f"Q: {question}"
                        if category:
                            q_detail += f"\nCategory: {category}"
                        if evidence_ref:
                            q_detail += f"\nEvidence: {evidence_ref}"
                        if follow_ups:
                            q_detail += f"\nFollow-ups: {'; '.join(follow_ups)}"
                        if listening:
                            q_detail += f"\nListen for: {listening}"
                        if context:
                            q_detail += f"\nContext: {context}"
                        questions_full.append(q_detail)
                    else:
                        questions_full.append(str(q))

                questions_text = "\n\n".join(questions_full)

                # Get recommendations with FULL details
                recommendations = analysis_data.get("recommendations", [])
                recommendations_full = []
                for r in recommendations:
                    if isinstance(r, dict):
                        text = r.get("text", "")
                        priority = r.get("priority", "")
                        rtype = r.get("type", "")
                        evidence = r.get("evidence", "")

                        r_detail = f"• {text}"
                        if priority:
                            r_detail += f"\n  Priority: {priority}"
                        if rtype:
                            r_detail += f"\n  Type: {rtype}"
                        if evidence:
                            r_detail += f"\n  Evidence: {evidence}"
                        recommendations_full.append(r_detail)
                    else:
                        recommendations_full.append(str(r))

                recommendations_text = "\n\n".join(recommendations_full)

                # Get areas to explore
                areas_to_explore = analysis_data.get("areas_to_explore", [])
                areas_text = "\n".join([f"• {area}" for area in areas_to_explore])

                # Get confidence explanation (Analysis Confidence Level)
                confidence_explanation = analysis_data.get("confidence_explanation", "")

                # Get green flags (Positive Indicators)
                green_flags = analysis_data.get("green_flags", [])
                green_flags_text = "\n".join([f"• {flag}" for flag in green_flags])

                row = [
                    analysis.repository_url,
                    analysis.repository_name,
                    analysis.context,
                    analysis.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    analysis.processing_time_ms,
                    summary_text,
                    confidence_explanation,  # Analysis Confidence Level
                    green_flags_text,  # Positive Indicators
                    key_insights,
                    evidence_patterns_text,
                    questions_text,
                    recommendations_text,
                    areas_text,
                ]
                writer.writerow(row)

            content = output.getvalue()
            media_type = "text/csv"
            filename = f"batch_{batch_id}_export.csv"

        elif format == "zip":
            # ZIP export with individual HTML files (for design consistency with frontend)
            import io
            import json
            import zipfile

            # Create ZIP file in memory
            zip_buffer = io.BytesIO()

            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                # Add a summary JSON file
                summary_data: Dict[str, Any] = {
                    "batch_id": batch_id,
                    "export_date": datetime.now(timezone.utc).isoformat(),
                    "total_analyses": len(analyses),
                    "analyses": [],
                }

                for i, analysis in enumerate(analyses):
                    try:
                        full_analysis = json.loads(analysis.full_analysis)

                        # Parse the full analysis data - handle different structures
                        if not isinstance(full_analysis, dict):
                            continue

                        analysis_dict = full_analysis.get("analysis", {})

                        # Extract data matching frontend export
                        insights = analysis_dict.get("insights", [])
                        questions = analysis_dict.get("questions", [])
                        evidence_patterns = analysis_dict.get("evidence_patterns", [])
                        recommendations = analysis_dict.get("recommendations", [])
                        executive_summary = analysis_dict.get("executive_summary", "")
                        confidence_explanation = analysis_dict.get(
                            "confidence_explanation", ""
                        )
                        green_flags = analysis_dict.get("green_flags", [])
                        red_flags = analysis_dict.get("red_flags", [])
                        limitations = analysis_dict.get("limitations", [])
                        data_limitations = analysis_dict.get("data_limitations", [])
                        areas_to_explore = analysis_dict.get("areas_to_explore", [])

                        # Generate HTML exactly matching frontend export
                        from ..utils.export_html import generate_analysis_html

                        html_content = generate_analysis_html(
                            repository_name=analysis.repository_name,
                            repository_url=analysis.repository_url,
                            context=analysis.context,
                            created_at=analysis.created_at,
                            insights=insights,
                            questions=questions,
                            evidence_patterns=evidence_patterns,
                            recommendations=recommendations,
                            executive_summary=executive_summary,
                            confidence_explanation=confidence_explanation,
                            green_flags=green_flags,
                            red_flags=red_flags,
                            limitations=limitations,
                            data_limitations=data_limitations,
                            areas_to_explore=areas_to_explore,
                        )

                        # Add HTML to ZIP
                        html_filename = f"{analysis.repository_name.replace('/', '_')}_{analysis.created_at.strftime('%Y%m%d')}.html"
                        zip_file.writestr(html_filename, html_content)

                        # Add to summary
                        summary_data["analyses"].append(
                            {
                                "repository": analysis.repository_name,
                                "url": analysis.repository_url,
                                "context": analysis.context,
                                "analyzed_at": analysis.created_at.isoformat(),
                                "file": html_filename,
                            }
                        )

                    except Exception as e:
                        # Log the error and skip this analysis
                        logger.warning(
                            f"Failed to export analysis {i} for batch {batch_id}: {str(e)}"
                        )
                        continue

                # Add summary JSON to ZIP
                zip_file.writestr(
                    "batch_summary.json", json.dumps(summary_data, indent=2)
                )

            # Get ZIP content
            zip_buffer.seek(0)
            content = zip_buffer.getvalue()
            media_type = "application/zip"
            filename = f"batch_{batch_id}_export.zip"

        # Return file response
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export batch {batch_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to export batch results")


@router.get("/ai-quota", tags=["Analysis"])
async def get_ai_quota_status(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Get AI analysis quota status for FREE tier users.

    Returns quota information including used and remaining AI analyses for the current month.
    """
    from sqlalchemy import func, select

    # Only relevant for FREE tier users
    if user.subscription_plan != SubscriptionPlan.FREE:
        return {
            "tier": user.subscription_plan.value,
            "has_quota_limit": False,
            "message": "Unlimited AI analyses available for your subscription plan",
        }

    # Get current billing period
    now = datetime.now(timezone.utc)
    billing_period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # Calculate first day of next month
    if now.month == 12:
        billing_period_end = now.replace(
            year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0
        )
    else:
        billing_period_end = now.replace(
            month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0
        )

    # Count AI analyses this month (token_count > 0 means AI was used)
    # Use date range comparison instead of strftime for PostgreSQL compatibility
    ai_count_query = select(func.count(AnalysisResult.id)).where(
        AnalysisResult.user_id == user.user_id,
        AnalysisResult.created_at >= billing_period_start,
        AnalysisResult.created_at < billing_period_end,
        AnalysisResult.token_count > 0,
        AnalysisResult.deleted_at.is_(None),
    )
    ai_count_result = await db.execute(ai_count_query)
    ai_count = ai_count_result.scalar() or 0

    billing_period = now.strftime("%Y-%m")

    # FREE tier gets 3 AI analyses per month
    ai_quota_limit = 3
    remaining = max(0, ai_quota_limit - ai_count)

    # Generate friendly message
    if remaining == 3:
        message = "You have 3 AI-powered analyses available this month!"
    elif remaining == 2:
        message = "2 AI analyses remaining this month. After that, you'll receive template-based analysis."
    elif remaining == 1:
        message = "This is your last AI analysis for this month! Future analyses will use templates until next month."
    else:
        message = "You've used all 3 AI analyses this month. Analyses will now use template responses. AI analyses will reset next month!"

    return {
        "tier": "free",
        "has_quota_limit": True,
        "ai_quota_limit": ai_quota_limit,
        "ai_used": ai_count,
        "ai_remaining": remaining,
        "billing_period": billing_period,
        "message": message,
        "upgrade_available": True,
    }
