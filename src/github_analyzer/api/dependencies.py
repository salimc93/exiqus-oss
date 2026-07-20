# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
FastAPI dependencies.

This module provides reusable dependencies for the FastAPI application
including rate limiting, authentication, and service injections.
"""

import hashlib
from typing import List, Optional
from urllib.parse import urlparse

from fastapi import Depends, HTTPException, Request, status
from pydantic import HttpUrl

from ..billing.usage_tracker import UsageTracker
from ..data.github_fetcher import GitHubFetcher
from ..database.models import User
from ..utils.config import get_config
from ..utils.logging import get_logger
from .auth.dependencies import get_current_active_user
from .services.analytics_service import AnalyticsService
from .services.redis_service import RedisService

logger = get_logger(__name__)


def validate_github_url(url: HttpUrl) -> str:
    """
    Validate and normalize GitHub repository URL.

    Supports both standard repository URLs and nested subdirectory URLs.
    For subdirectory URLs, returns the base repository URL.

    Args:
        url: GitHub repository URL to validate

    Returns:
        str: Normalized GitHub URL (base repository)

    Raises:
        HTTPException: If URL is not a valid GitHub repository URL
    """
    from ..utils.helpers import parse_github_url_with_subdirectory

    url_str = str(url)

    # Use the new parser that handles subdirectories
    parsed_info = parse_github_url_with_subdirectory(url_str)

    if not parsed_info:
        # Provide specific error message based on URL format
        parsed = urlparse(url_str)

        if parsed.netloc.lower() not in ["github.com", "www.github.com"]:
            raise HTTPException(
                status_code=400, detail="URL must be a GitHub repository URL"
            )

        path_parts = [part for part in parsed.path.split("/") if part]
        if len(path_parts) < 2:
            raise HTTPException(
                status_code=400,
                detail=(
                    "URL must point to a specific repository "
                    "(format: github.com/user/repo)"
                ),
            )

        # If we got here, the URL structure is okay but validation failed
        raise HTTPException(
            status_code=400,
            detail="Invalid GitHub repository URL: URL validation failed",
        )

    # Return the base repository URL (not the subdirectory)
    # The analysis will focus on the entire repository
    return parsed_info["base_url"]


def generate_cache_key(repository_url: str, context: str = "general") -> str:
    """
    Generate a consistent cache key for repository analysis.

    Args:
        repository_url: Repository URL
        context: Analysis context

    Returns:
        str: Cache key
    """
    # Create a deterministic hash of the URL and context
    content = f"{repository_url}:{context}"
    return (
        f"analysis:{hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()}"
    )


async def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request.

    Args:
        request: FastAPI request object

    Returns:
        str: Client IP address
    """
    # Check for forwarded headers (reverse proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP in the chain
        return forwarded_for.split(",")[0].strip()

    # Check for real IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fall back to direct client IP
    if request.client:
        return request.client.host

    return "unknown"


async def check_rate_limit(
    client_ip: str, requests_per_minute: int = 60, requests_per_hour: int = 1000
) -> None:
    """
    Check rate limits for client requests.

    This is a placeholder implementation for Phase 1.
    In Phase 2, this will use Redis for distributed rate limiting.

    Args:
        client_ip: Client IP address
        requests_per_minute: Requests per minute limit
        requests_per_hour: Requests per hour limit

    Raises:
        HTTPException: If rate limit is exceeded
    """
    # TODO: Implement Redis-based rate limiting in Phase 2
    # For now, this is a no-op placeholder

    logger.debug(
        f"Rate limit check for IP: {client_ip}",
        extra={
            "client_ip": client_ip,
            "limits": {
                "per_minute": requests_per_minute,
                "per_hour": requests_per_hour,
            },
        },
    )


def validate_batch_size(
    request: Optional[List[str]] = None,
    urls: Optional[List[str]] = None,
    max_size: int = 10,
) -> int:
    """
    Validate batch request size.

    Args:
        request: List of URLs to validate (for compatibility)
        urls: List of URLs to validate (for compatibility)
        max_size: Maximum allowed batch size

    Returns:
        int: Size of the batch

    Raises:
        HTTPException: If batch size exceeds limit
    """
    # Handle both parameter names for compatibility
    url_list = request or urls or []

    if len(url_list) > max_size:
        raise HTTPException(
            status_code=400, detail=f"Batch size cannot exceed {max_size} repositories"
        )

    if len(url_list) == 0:
        raise HTTPException(
            status_code=400, detail="Batch request must contain at least one repository"
        )

    return len(url_list)


# Service dependencies
_analytics_service: Optional[AnalyticsService] = None
_redis_service: Optional[RedisService] = None
_github_fetcher: Optional[GitHubFetcher] = None
_usage_tracker: Optional[UsageTracker] = None


def get_analytics_service() -> AnalyticsService:
    """
    Get or create analytics service instance.

    Returns:
        AnalyticsService: Analytics service instance
    """
    global _analytics_service
    if _analytics_service is None:
        redis_service = get_redis_service()
        _analytics_service = AnalyticsService(redis_service=redis_service)
    return _analytics_service


def get_redis_service() -> RedisService:
    """
    Get or create Redis service instance.

    Returns:
        RedisService: Redis service instance
    """
    global _redis_service
    if _redis_service is None:
        _redis_service = RedisService()
    return _redis_service


def get_github_fetcher() -> GitHubFetcher:
    """
    Get or create GitHubFetcher instance.

    Returns:
        GitHubFetcher: GitHub fetcher instance
    """
    global _github_fetcher
    if _github_fetcher is None:
        _github_fetcher = GitHubFetcher()
    return _github_fetcher


def get_usage_tracker() -> UsageTracker:
    """
    Dependency injector for a singleton UsageTracker instance.
    """
    global _usage_tracker
    if _usage_tracker is None:
        _usage_tracker = UsageTracker()
    return _usage_tracker


def get_user_repo_size_limit(
    current_user: User = Depends(get_current_active_user),
) -> int:
    """
    Get repository size limit based on user's plan or custom setting.

    Args:
        current_user: Current authenticated user

    Returns:
        int: Repository size limit in MB
    """
    # Check for custom limit first (typically for enterprise users)
    if current_user.custom_repo_size_limit_mb is not None:
        logger.info(
            f"Using custom repo size limit for user {current_user.email}: "
            f"{current_user.custom_repo_size_limit_mb}MB"
        )
        return current_user.custom_repo_size_limit_mb

    # Otherwise use plan-based limit
    config = get_config()
    plan_name = current_user.subscription_plan.value
    limit = config.analysis.get_plan_repo_size_limit(plan_name)

    logger.debug(
        f"Using plan-based repo size limit for {current_user.email} "
        f"({plan_name} plan): {limit}MB"
    )

    return limit


async def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Dependency to require admin access for endpoints.

    NOTE: This is for regular user endpoints that require admin privileges.
    For admin portal endpoints, use get_admin_user_from_token from auth.dependencies.

    Args:
        current_user: Currently authenticated user

    Returns:
        User: The admin user

    Raises:
        HTTPException: If user is not an admin
    """
    if not current_user.is_admin:
        logger.warning(
            f"Non-admin user {current_user.email} attempted to access admin endpoint"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )

    return current_user
