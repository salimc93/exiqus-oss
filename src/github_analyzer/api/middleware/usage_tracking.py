# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Usage tracking middleware for API quota enforcement and billing.

This middleware tracks API usage, enforces quotas based on subscription plans,
and records usage for billing purposes.
"""

import json
import time
from datetime import datetime, timezone
from typing import Any, Callable, Optional, cast

from fastapi import Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware

from ...billing.subscription_manager import PlanFeatures, SubscriptionManager
from ...billing.usage_tracker import UsageTracker
from ...database.connection import get_db_session
from ...database.models import SubscriptionPlan
from ...database.operations import BillingUsageOperations, UserOperations
from ...utils.logging import get_logger

logger = get_logger(__name__)


class UsageTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for tracking API usage and enforcing quotas.

    Monitors API usage, enforces subscription plan limits, and records
    usage data for billing and analytics purposes.
    """

    # API endpoints that count towards usage quota
    TRACKED_ENDPOINTS = {
        "/api/v1/analyze": {"usage_type": "analysis", "quota_cost": 1},
        "/api/v1/batch": {
            "usage_type": "batch_analysis",
            "quota_cost": 1,
        },  # Per repo in batch
    }

    # Endpoints that don't count towards quota
    EXCLUDED_ENDPOINTS = {
        "/api/v1/health",
        "/api/v1/auth",
        "/api/v1/billing",
        "/api/v1/admin",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/favicon.ico",
    }

    def __init__(self, app: Any) -> None:
        """Initialize usage tracking middleware."""
        super().__init__(app)
        self.subscription_manager = SubscriptionManager()

    async def dispatch(
        self, request: Request, call_next: Callable[..., Any]
    ) -> Response:
        """
        Process request with usage tracking and quota enforcement.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response
        """
        start_time = time.time()

        # Check if this endpoint should be tracked
        endpoint_path = request.url.path
        tracking_config = self._get_tracking_config(endpoint_path)

        if not tracking_config:
            # Not a tracked endpoint, process normally
            return cast(Response, await call_next(request))

        # Get user ID from request (if authenticated)
        user_id = await self._extract_user_id(request)

        if not user_id:
            # Unauthenticated requests are handled by auth middleware
            return cast(Response, await call_next(request))

        # Check quota before processing request
        quota_check = None
        try:
            quota_check = await self._check_usage_quota(
                request, user_id, tracking_config
            )

            if not quota_check["can_proceed"]:
                # Quota exceeded
                logger.warning(f"Quota exceeded for user {user_id}")

                # Build rate limit headers
                headers = self._build_rate_limit_headers(quota_check)
                headers["Content-Type"] = "application/json"

                # Convert datetime objects to ISO format for JSON serialization
                quota_info_json = quota_check.copy()
                if "reset_timestamp" in quota_info_json:
                    quota_info_json["reset_timestamp"] = quota_info_json[
                        "reset_timestamp"
                    ].isoformat()

                return Response(
                    content=json.dumps(
                        {
                            "detail": quota_check["message"],
                            "quota_info": quota_info_json,
                            "upgrade_options": quota_check.get("upgrade_options", []),
                        }
                    ),
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    headers=headers,
                )
        except Exception as e:
            logger.error(f"Error checking usage quota: {e}")
            # Allow request to proceed if quota check fails

        # Process the request
        response = cast(Response, await call_next(request))

        # Add rate limit headers to successful tracked requests
        if quota_check is not None:
            # Get enhanced overage information for response headers
            overage_headers = await self._get_overage_headers(user_id)
            rate_limit_headers = self._build_rate_limit_headers(quota_check)

            # Merge overage headers with rate limit headers
            all_headers = {**rate_limit_headers, **overage_headers}
            for header, value in all_headers.items():
                response.headers[header] = value

        # Record usage after successful request
        if response.status_code < 400:  # Only track successful requests
            try:
                await self._record_usage(
                    request, response, user_id, tracking_config, start_time
                )
            except Exception as e:
                logger.error(f"Error recording usage: {e}")
                # Don't fail the request if usage recording fails

        return response

    def _get_tracking_config(self, endpoint_path: str) -> Optional[dict[str, Any]]:
        """
        Get tracking configuration for an endpoint.

        Args:
            endpoint_path: Request endpoint path

        Returns:
            Tracking configuration or None if not tracked
        """
        # Check if endpoint is explicitly excluded
        for excluded in self.EXCLUDED_ENDPOINTS:
            if endpoint_path.startswith(excluded):
                return None

        # Check for exact matches first
        if endpoint_path in self.TRACKED_ENDPOINTS:
            return self.TRACKED_ENDPOINTS[endpoint_path]

        # Check for prefix matches
        for tracked_path, config in self.TRACKED_ENDPOINTS.items():
            if endpoint_path.startswith(tracked_path):
                return config

        return None

    async def _extract_user_id(self, request: Request) -> Optional[str]:
        """
        Extract user ID from request.

        Args:
            request: HTTP request

        Returns:
            User ID or None if not authenticated
        """
        try:
            # Try to get user ID from Authorization header
            auth_header = request.headers.get("authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return None

            # Extract token and get user ID
            token = auth_header.replace("Bearer ", "")

            # Import here to avoid circular imports
            from ..auth.jwt import extract_user_id

            user_id = extract_user_id(token)
            return user_id

        except Exception as e:
            logger.debug(f"Could not extract user ID: {e}")
            return None

    async def _check_usage_quota(
        self, request: Request, user_id: str, tracking_config: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Check if user can proceed with request based on quota.

        Args:
            request: HTTP request
            user_id: User ID
            tracking_config: Endpoint tracking configuration

        Returns:
            Quota check result
        """
        # Get database session
        async for db in get_db_session():
            try:
                # Determine usage cost
                usage_cost = tracking_config.get("quota_cost", 1)

                # For batch requests, multiply by number of repositories
                if tracking_config["usage_type"] == "batch_analysis":
                    try:
                        body = await request.body()
                        if body:
                            request_data = json.loads(body)
                            repositories = request_data.get("repositories", [])
                            usage_cost = len(repositories) * usage_cost
                    except Exception:  # noqa: S110
                        # If we can't parse the body, use default cost
                        # This is defensive programming - JSON parsing may fail if request body is malformed,
                        # and we want to gracefully fall back to default cost estimation rather than crash
                        pass

                # Check quota using subscription manager
                quota_check = await self.subscription_manager.check_usage_limits(
                    db, user_id, usage_cost
                )

                return quota_check

            finally:
                await db.close()

        # Fallback return if session acquisition fails
        return {"allowed": False, "reason": "Database session unavailable"}

    async def _record_usage(
        self,
        request: Request,
        response: Response,
        user_id: str,
        tracking_config: dict[str, Any],
        start_time: float,
    ) -> None:
        """
        Record API usage for billing and analytics.

        Args:
            request: HTTP request
            response: HTTP response
            user_id: User ID
            tracking_config: Endpoint tracking configuration
            start_time: Request start time
        """
        # Get database session
        async for db in get_db_session():
            try:
                # Calculate usage metrics
                response_time_ms = int((time.time() - start_time) * 1000)
                usage_type = tracking_config["usage_type"]
                usage_count = tracking_config.get("quota_cost", 1)

                # For batch requests, count actual repositories processed
                if usage_type == "batch_analysis":
                    try:
                        body = await request.body()
                        if body:
                            request_data = json.loads(body)
                            repositories = request_data.get("repositories", [])
                            usage_count = len(repositories)
                    except Exception:  # noqa: S110
                        # Use default if we can't parse
                        # This is defensive programming - JSON parsing may fail if request body is malformed,
                        # and we want to gracefully fall back to default usage count rather than crash
                        pass

                # Generate usage record ID with microseconds for uniqueness
                now = datetime.now(timezone.utc)
                record_id = f"usage_{now.strftime('%Y%m%d_%H%M%S%f')}_{user_id[:8]}"

                # Create usage record
                await BillingUsageOperations.create_usage_record(
                    db=db,
                    record_id=record_id,
                    user_id=user_id,
                    usage_type=usage_type,
                    usage_count=usage_count,
                    metadata=json.dumps(
                        {
                            "endpoint": request.url.path,
                            "method": request.method,
                            "response_status": response.status_code,
                            "response_time_ms": response_time_ms,
                            "user_agent": request.headers.get("user-agent"),
                            "ip_address": (
                                request.client.host if request.client else None
                            ),
                        }
                    ),
                )

                # Update user's usage consumed
                # Atomically increment user's usage consumed
                await UserOperations.increment_usage_count(db, user_id, usage_count)

                logger.info(
                    f"Recorded {usage_count} {usage_type} usage for user {user_id}"
                )

            except Exception as e:
                logger.error(f"Failed to record usage: {e}")
                raise
            finally:
                await db.close()

    async def _get_plan_limits(self, plan: SubscriptionPlan) -> dict[str, Any]:
        """
        Get plan limits for quota enforcement.

        Args:
            plan: Subscription plan

        Returns:
            Plan limits configuration
        """
        return PlanFeatures.get_plan_limits(plan)

    async def _get_overage_headers(self, user_id: str) -> dict[str, str]:
        """
        Get overage-specific headers with usage warnings.

        Args:
            user_id: User ID

        Returns:
            Dictionary of overage-related headers
        """
        headers = {}

        try:
            # Get database session
            async for db in get_db_session():
                try:
                    # Get detailed overage status
                    overage_status = await UsageTracker.get_overage_status(db, user_id)

                    # Add overage headers
                    if overage_status.get("supports_overage"):
                        headers["X-Overage-Allowed"] = "true"
                        headers["X-Overage-Rate"] = f"${overage_status['overage_rate']}"

                        if overage_status["overage_amount"] > 0:
                            headers["X-Overage-Amount"] = str(
                                overage_status["overage_amount"]
                            )
                            headers["X-Overage-Cost"] = (
                                f"${overage_status['overage_cost']}"
                            )
                            headers["X-Overage-Status"] = "active"
                    else:
                        headers["X-Overage-Allowed"] = "false"

                    # Add usage percentage header
                    headers["X-Usage-Percentage"] = (
                        f"{overage_status['usage_percentage']}%"
                    )

                    # Add specific warning headers based on usage level
                    warning_level = overage_status.get("warning_level")
                    if warning_level:
                        headers["X-Usage-Warning-Level"] = warning_level

                        if warning_level == "exceeded":
                            if overage_status.get("supports_overage"):
                                headers["X-Usage-Warning"] = (
                                    f"Quota exceeded. Overage charges of ${overage_status['overage_cost']} "
                                    f"will apply at ${overage_status['overage_rate']} per API call."
                                )
                            else:
                                headers["X-Usage-Warning"] = (
                                    "Quota exceeded. Upgrade to Professional or Enterprise plan for continued access."
                                )
                        elif warning_level == "critical":
                            remaining = (
                                overage_status["usage_quota"]
                                - overage_status["usage_count"]
                            )
                            headers["X-Usage-Warning"] = (
                                f"Critical: {remaining} API calls remaining ({overage_status['usage_percentage']}% used). "
                                "Consider upgrading to avoid service interruption."
                            )
                        elif warning_level == "high":
                            headers["X-Usage-Warning"] = (
                                f"Usage at {overage_status['usage_percentage']}%. "
                                "Monitor usage to avoid unexpected charges."
                            )

                    # Add billing period header
                    headers["X-Billing-Period"] = overage_status["billing_period"]

                finally:
                    await db.close()

        except Exception as e:
            logger.error(f"Error getting overage headers: {e}")
            # Return empty headers on error to avoid blocking requests

        return headers

    def _build_rate_limit_headers(self, quota_info: dict[str, Any]) -> dict[str, str]:
        """
        Build standard rate limit headers.

        Args:
            quota_info: Quota information from check

        Returns:
            Dictionary of headers to add to response
        """
        headers = {}

        # Basic rate limit headers
        limit = quota_info.get("usage_limit", 0)
        remaining = quota_info.get("usage_remaining", 0)

        # Only add headers for plans with API access
        if limit > 0:
            headers["X-RateLimit-Limit"] = str(limit)
            headers["X-RateLimit-Remaining"] = str(max(0, remaining))
            headers["X-RateLimit-Resource"] = "api_quota"

            # Add plan information
            if "plan" in quota_info:
                headers["X-RateLimit-Plan"] = quota_info["plan"]

            # Reset timestamp
            if "reset_timestamp" in quota_info:
                reset_dt = quota_info["reset_timestamp"]
                # Unix timestamp
                headers["X-RateLimit-Reset"] = str(int(reset_dt.timestamp()))

                # Seconds until reset
                seconds_until_reset = int(
                    (reset_dt - datetime.now(timezone.utc)).total_seconds()
                )
                headers["X-RateLimit-Reset-After"] = str(max(0, seconds_until_reset))

                # Retry-After header for 429 responses
                if not quota_info.get("can_proceed", True):
                    headers["Retry-After"] = str(max(0, seconds_until_reset))

            # Warning headers
            consumed = quota_info.get("usage_consumed", 0)
            usage_percentage = (consumed / limit) * 100

            # Grace period warning
            if quota_info.get("grace_period"):
                grace_remaining = quota_info.get("grace_remaining", 0)
                headers["X-RateLimit-Grace-Period"] = "active"
                headers["X-RateLimit-Grace-Remaining"] = str(grace_remaining)
                headers["X-RateLimit-Warning"] = (
                    f"Grace period active - {grace_remaining} requests remaining"
                )

            # Near quota warning (>90% used)
            elif usage_percentage >= 90:
                headers["X-RateLimit-Warning"] = (
                    f"Quota usage at {usage_percentage:.1f}% - consider upgrading"
                )

        return headers


class QuotaEnforcementError(Exception):
    """Exception raised when quota limits are exceeded."""

    def __init__(self, message: str, quota_info: dict[str, Any]):
        super().__init__(message)
        self.quota_info = quota_info


# Utility functions for quota checking
async def check_user_quota(
    user_id: str, usage_count: int = 1, db: Optional[AsyncSession] = None
) -> dict[str, Any]:
    """
    Check if user has sufficient quota for a request.

    Args:
        user_id: User ID
        usage_count: Number of usage units requested
        db: Optional database session

    Returns:
        Quota check result
    """
    close_db = False
    if db is None:
        # Get database session
        async for db in get_db_session():
            close_db = True
            break

    if db is None:
        raise ValueError("Unable to acquire database session")

    try:
        subscription_manager = SubscriptionManager()
        return await subscription_manager.check_usage_limits(db, user_id, usage_count)
    finally:
        if close_db and db:
            await db.close()


async def enforce_quota(user_id: str, usage_count: int = 1) -> None:
    """
    Enforce quota limits for a user.

    Args:
        user_id: User ID
        usage_count: Number of usage units requested

    Raises:
        QuotaEnforcementError: If quota is exceeded
    """
    quota_check = await check_user_quota(user_id, usage_count)

    if not quota_check["can_proceed"]:
        raise QuotaEnforcementError(
            quota_check.get("message", "Quota exceeded"), quota_check
        )
