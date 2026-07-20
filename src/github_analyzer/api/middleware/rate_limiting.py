# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Rate limiting middleware.

This module provides rate limiting middleware using Redis for tracking
request counts per client IP and endpoint.
"""

from typing import Any, Awaitable, Callable, Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from ...utils.logging import get_logger
from ..services.redis_service import redis_service

logger = get_logger(__name__)


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce rate limits using Redis.

    Tracks requests per client IP and enforces limits based on endpoint.
    """

    def __init__(
        self,
        app: Any,
        requests_per_minute: int = 60,
        burst_requests_per_minute: int = 120,
        analysis_requests_per_hour: int = 10,
        contact_requests_per_hour: int = 5,
        registration_requests_per_hour: int = 5,
        registration_requests_per_day: int = 10,
    ):
        """
        Initialize rate limiting middleware.

        Args:
            app: ASGI application
            requests_per_minute: General API requests per minute
            burst_requests_per_minute: Burst allowance for short periods
            analysis_requests_per_hour: Analysis endpoint limit per hour
            contact_requests_per_hour: Contact form submissions per hour
            registration_requests_per_hour: Account registrations per hour
            registration_requests_per_day: Account registrations per day
        """
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_requests_per_minute = burst_requests_per_minute
        self.analysis_requests_per_hour = analysis_requests_per_hour
        self.contact_requests_per_hour = contact_requests_per_hour
        self.registration_requests_per_hour = registration_requests_per_hour
        self.registration_requests_per_day = registration_requests_per_day

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Process request and enforce rate limits.

        Args:
            request: The incoming HTTP request
            call_next: The next middleware or route handler

        Returns:
            Response: The HTTP response

        Raises:
            HTTPException: When rate limit is exceeded
        """
        # Skip rate limiting for health checks
        if request.url.path.startswith("/api/v1/health"):
            return await call_next(request)

        # Determine rate limit key - prefer API key over IP
        rate_limit_identifier, is_api_key = self._get_rate_limit_identifier(request)

        # Get custom rate limits if using API key
        custom_limits = self._get_custom_limits(request) if is_api_key else None

        # Check API key scopes if applicable
        if is_api_key and "/analyze" in request.url.path:
            if not self._check_api_key_scope(request, "analysis"):
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "Insufficient scope",
                        "message": "API key does not have 'analysis' scope",
                        "required_scope": "analysis",
                    },
                )

        # Determine rate limit based on endpoint
        analysis_limit_key = None  # Track if we need to rollback on failure
        if "/analyze" in request.url.path:
            # Analysis endpoints have stricter limits
            limit_key = self._generate_rate_limit_key(
                rate_limit_identifier, "analysis", is_api_key
            )
            analysis_limit_key = limit_key  # Save for potential rollback
            limit = self.analysis_requests_per_hour
            if custom_limits and "analysis_requests_per_hour" in custom_limits:
                limit = custom_limits["analysis_requests_per_hour"]
            current_count, is_allowed = await redis_service.increment_rate_limit(
                limit_key,
                window_seconds=3600,  # 1 hour
                limit=limit,
            )

            if not is_allowed:
                logger.warning(
                    f"Analysis rate limit exceeded for {rate_limit_identifier}: "
                    f"{current_count}/{limit} per hour"
                )
                detail = {
                    "error": "Rate limit exceeded",
                    "message": f"Analysis requests limited to {limit} per hour",
                    "current_usage": current_count,
                    "limit": limit,
                    "reset_in_seconds": 3600,
                    "endpoint": "analysis",
                }
                if is_api_key:
                    api_key_record = getattr(request.state, "api_key_record", None)
                    if api_key_record:
                        detail["api_key_id"] = api_key_record.key_id
                return JSONResponse(
                    status_code=429,
                    content=detail,
                    headers={"Retry-After": "3600"},
                )

        elif "/contact" in request.url.path and request.method == "POST":
            # Contact form submissions have strict limits to prevent spam
            limit_key = self._generate_rate_limit_key(
                rate_limit_identifier, "contact", is_api_key
            )
            limit = self.contact_requests_per_hour
            if custom_limits and "contact_requests_per_hour" in custom_limits:
                limit = custom_limits["contact_requests_per_hour"]
            current_count, is_allowed = await redis_service.increment_rate_limit(
                limit_key,
                window_seconds=3600,  # 1 hour
                limit=limit,
            )

            if not is_allowed:
                logger.warning(
                    f"Contact form rate limit exceeded for {rate_limit_identifier}: "
                    f"{current_count}/{limit} per hour"
                )
                detail = {
                    "error": "Rate limit exceeded",
                    "message": f"Contact form submissions limited to {limit} per hour",
                    "current_usage": current_count,
                    "limit": limit,
                    "reset_in_seconds": 3600,
                    "endpoint": "contact",
                }
                if is_api_key:
                    api_key_record = getattr(request.state, "api_key_record", None)
                    if api_key_record:
                        detail["api_key_id"] = api_key_record.key_id
                return JSONResponse(
                    status_code=429,
                    content=detail,
                    headers={"Retry-After": "3600"},
                )

        elif "/auth/register" in request.url.path and request.method == "POST":
            # Account registration has strict limits to prevent abuse
            # Check hourly limit
            hourly_key = self._generate_rate_limit_key(
                rate_limit_identifier, "registration_hourly", is_api_key
            )
            hourly_limit = self.registration_requests_per_hour
            hourly_count, hourly_allowed = await redis_service.increment_rate_limit(
                hourly_key,
                window_seconds=3600,  # 1 hour
                limit=hourly_limit,
            )

            if not hourly_allowed:
                logger.warning(
                    f"Registration hourly rate limit exceeded for {rate_limit_identifier}: "
                    f"{hourly_count}/{hourly_limit} per hour"
                )
                detail = {
                    "error": "Rate limit exceeded",
                    "message": f"Account registrations limited to {hourly_limit} per hour to prevent abuse",
                    "current_usage": hourly_count,
                    "limit": hourly_limit,
                    "reset_in_seconds": 3600,
                    "endpoint": "registration",
                }
                return JSONResponse(
                    status_code=429,
                    content={"detail": detail},
                    headers={"Retry-After": "3600"},
                )

            # Check daily limit
            daily_key = self._generate_rate_limit_key(
                rate_limit_identifier, "registration_daily", is_api_key
            )
            daily_limit = self.registration_requests_per_day
            daily_count, daily_allowed = await redis_service.increment_rate_limit(
                daily_key,
                window_seconds=86400,  # 24 hours
                limit=daily_limit,
            )

            if not daily_allowed:
                logger.warning(
                    f"Registration daily rate limit exceeded for {rate_limit_identifier}: "
                    f"{daily_count}/{daily_limit} per day"
                )
                detail = {
                    "error": "Rate limit exceeded",
                    "message": f"Account registrations limited to {daily_limit} per day to prevent abuse",
                    "current_usage": daily_count,
                    "limit": daily_limit,
                    "reset_in_seconds": 86400,
                    "endpoint": "registration",
                }
                return JSONResponse(
                    status_code=429,
                    content={"detail": detail},
                    headers={"Retry-After": "86400"},
                )

            # Set limit and current_count for response headers (use hourly limit)
            limit = hourly_limit
            current_count = hourly_count

        else:
            # General API endpoints
            limit_key = self._generate_rate_limit_key(
                rate_limit_identifier, "general", is_api_key
            )
            limit = self.requests_per_minute
            if custom_limits and "requests_per_minute" in custom_limits:
                limit = custom_limits["requests_per_minute"]
            current_count, is_allowed = await redis_service.increment_rate_limit(
                limit_key,
                window_seconds=60,
                limit=limit,  # 1 minute
            )

            if not is_allowed:
                # Check if we can allow under burst limit
                burst_key = self._generate_rate_limit_key(
                    rate_limit_identifier, "burst", is_api_key
                )
                burst_limit = self.burst_requests_per_minute
                if custom_limits and "burst_requests_per_minute" in custom_limits:
                    burst_limit = custom_limits["burst_requests_per_minute"]
                burst_count, burst_allowed = await redis_service.increment_rate_limit(
                    burst_key, window_seconds=60, limit=burst_limit
                )

                if not burst_allowed:
                    logger.warning(
                        f"Rate limit exceeded for {rate_limit_identifier}: "
                        f"{current_count}/{limit} per minute"
                    )
                    detail = {
                        "error": "Rate limit exceeded",
                        "message": f"Requests limited to {limit} per minute",
                        "current_usage": current_count,
                        "limit": limit,
                        "reset_in_seconds": 60,
                        "endpoint": "general",
                    }
                    if is_api_key:
                        api_key_record = getattr(request.state, "api_key_record", None)
                        if api_key_record:
                            detail["api_key_id"] = api_key_record.key_id
                    # Return JSONResponse directly instead of raising HTTPException
                    # to avoid middleware exception handling issues in Starlette 0.49+
                    return JSONResponse(
                        status_code=429,
                        content=detail,
                        headers={"Retry-After": "60"},
                    )
                else:
                    # If burst is allowed, update limit and count for header generation
                    limit = burst_limit
                    current_count = burst_count

        # Process the request
        response = await call_next(request)

        # If analysis failed (5xx error), decrement the rate limit counter
        # so failed analyses don't count against the user's quota
        if analysis_limit_key and response.status_code >= 500:
            try:
                await redis_service.decrement_rate_limit(analysis_limit_key)
                logger.info(
                    f"Decremented rate limit for {rate_limit_identifier} "
                    f"due to failed analysis (status {response.status_code})"
                )
            except Exception as e:
                logger.warning(f"Failed to decrement rate limit: {e}")

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - current_count))
        response.headers["X-RateLimit-Resource"] = "api_key" if is_api_key else "ip"

        if is_api_key:
            api_key_record = getattr(request.state, "api_key_record", None)
            if api_key_record:
                response.headers["X-RateLimit-Key-ID"] = api_key_record.key_id

        return response

    def _get_rate_limit_identifier(self, request: Request) -> tuple[str, bool]:
        """
        Get rate limit identifier from request.

        Prefers API key over IP address for authenticated requests.

        Args:
            request: HTTP request

        Returns:
            Tuple of (identifier, is_api_key)
        """
        # Check for API key authentication
        api_key_record = getattr(request.state, "api_key_record", None)
        if api_key_record:
            return api_key_record.key_id, True

        # Fall back to IP-based rate limiting
        return self._get_client_ip(request), False

    def _get_custom_limits(self, request: Request) -> Optional[dict[str, int]]:
        """
        Get custom rate limits for API key.

        Args:
            request: HTTP request

        Returns:
            Custom limits dictionary or None
        """
        api_key_record = getattr(request.state, "api_key_record", None)
        if api_key_record and hasattr(api_key_record, "rate_limit_override"):
            return api_key_record.rate_limit_override  # type: ignore
        return None

    def _check_api_key_scope(self, request: Request, required_scope: str) -> bool:
        """
        Check if API key has required scope.

        Args:
            request: HTTP request
            required_scope: Required scope name

        Returns:
            True if scope is present or no scopes defined
        """
        api_key_record = getattr(request.state, "api_key_record", None)
        if not api_key_record:
            return True  # No API key, other auth method

        # If no scopes defined, allow all
        if not hasattr(api_key_record, "scopes") or not api_key_record.scopes:
            return True

        return required_scope in api_key_record.scopes

    def _generate_rate_limit_key(
        self, identifier: str, endpoint: str, is_api_key: bool
    ) -> str:
        """
        Generate rate limit key.

        Args:
            identifier: API key ID or IP address
            endpoint: Endpoint type
            is_api_key: Whether identifier is an API key

        Returns:
            Rate limit key
        """
        prefix = "api_key" if is_api_key else "ip"
        return f"rate_limit:{prefix}:{endpoint}:{identifier}"

    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP from request with security considerations.

        Args:
            request: HTTP request

        Returns:
            Client IP address
        """
        # In production, we should trust proxy headers only from known sources
        # For now, we'll use a more secure approach

        # Check if we're behind a trusted proxy (e.g., Railway, AWS ALB)
        # In production, you should verify the proxy's IP first
        import os

        trusted_proxy = os.getenv("TRUSTED_PROXY", "false").lower() == "true"

        if trusted_proxy:
            # Only trust forwarded headers if explicitly configured
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                # Take the first IP in the chain (original client)
                # In production, you might want to take the last trusted proxy
                ips = [ip.strip() for ip in forwarded_for.split(",")]
                # Filter out local/private IPs that shouldn't be rate limited
                for ip in ips:
                    if not ip.startswith(("127.", "10.", "172.", "192.168.", "::1")):
                        return ip

            real_ip = request.headers.get("X-Real-IP")
            if real_ip and not real_ip.startswith(
                ("127.", "10.", "172.", "192.168.", "::1")
            ):
                return real_ip

        # Always fall back to direct client IP (most secure default)
        # This prevents header spoofing attacks
        direct_ip = request.client.host if request.client else "unknown"

        # Log when we're not using forwarded headers in production
        if not trusted_proxy and (
            request.headers.get("X-Forwarded-For") or request.headers.get("X-Real-IP")
        ):
            logger.debug(
                "Ignoring forwarded headers (TRUSTED_PROXY not set). "
                f"Using direct IP: {direct_ip}"
            )

        return direct_ip
