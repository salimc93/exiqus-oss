# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Security middleware for API protection.

This module provides security headers, CORS configuration,
and request validation middleware.
"""

import os
import time
from typing import Any, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

from github_analyzer.utils.logging import get_logger

logger = get_logger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Implements OWASP security header recommendations for API protection.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[..., Any]
    ) -> StarletteResponse:
        """
        Add security headers to response.

        Args:
            request: Incoming request
            call_next: Next middleware in chain

        Returns:
            Response: Response with security headers
        """
        response: StarletteResponse = await call_next(request)

        # Security headers following OWASP recommendations
        security_headers = {
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            # Enable XSS protection
            "X-XSS-Protection": "1; mode=block",
            # Strict transport security (HTTPS only)
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            # Content Security Policy for API
            "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none';",
            # Referrer policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            # Feature policy (deprecated but still useful)
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            # Server information disclosure
            "Server": "Exiqus-API/1.0",
            # Cache control for sensitive data
            "Cache-Control": "no-store, no-cache, must-revalidate, private",
            "Pragma": "no-cache",
            "Expires": "0",
        }

        # Add headers to response
        for header, value in security_headers.items():
            response.headers[header] = value

        return response


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request validation and rate limiting preparation.

    Validates request size, content type, and prepares data for rate limiting.
    """

    MAX_REQUEST_SIZE = 100 * 1024 * 1024  # 100MB limit

    async def dispatch(
        self, request: Request, call_next: Callable[..., Any]
    ) -> StarletteResponse:
        """
        Validate incoming request.

        Args:
            request: Incoming request
            call_next: Next middleware in chain

        Returns:
            Response: Response or validation error

        Raises:
            HTTPException: If request validation fails
        """
        # Check request size
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.MAX_REQUEST_SIZE:
            # Debug log to understand what's happening
            logger.warning(
                f"Request too large: {int(content_length)} bytes (max: {self.MAX_REQUEST_SIZE}). "
                f"Path: {request.url.path}, Method: {request.method}"
            )
            return Response(
                content='{"detail": "Request too large"}',
                status_code=413,
                media_type="application/json",
            )

        # Add request timing for monitoring
        start_time = time.time()
        request.state.start_time = start_time

        # Process request
        response: StarletteResponse = await call_next(request)

        # Add response timing header
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)

        return response


def get_cors_config() -> dict[str, Any]:
    """
    Get CORS configuration parameters.

    Returns:
        dict: CORS configuration parameters
    """
    # Defaults cover local development; set CORS_ALLOWED_ORIGINS for
    # production deployments.
    allowed_origins = [
        "http://localhost:3000",  # Development frontend
        "http://localhost:8080",  # Alternative dev port
    ]
    extra_origins = os.getenv("CORS_ALLOWED_ORIGINS", "")
    allowed_origins += [o.strip() for o in extra_origins.split(",") if o.strip()]

    return {
        "allow_origins": allowed_origins,
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": [
            "Authorization",
            "Content-Type",
            "X-API-Key",
            "X-Request-ID",
            "Accept",
            "Origin",
            "User-Agent",
        ],
        "expose_headers": [
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "X-Process-Time",
        ],
        "max_age": 3600,  # Cache preflight for 1 hour
    }


class APIVersionMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle API versioning.

    Ensures proper API version headers and deprecation warnings.
    """

    CURRENT_VERSION = "1.0"
    SUPPORTED_VERSIONS = ["1.0"]

    async def dispatch(
        self, request: Request, call_next: Callable[..., Any]
    ) -> StarletteResponse:
        """
        Handle API versioning.

        Args:
            request: Incoming request
            call_next: Next middleware in chain

        Returns:
            Response: Response with version headers
        """
        # Check if version is specified in headers
        requested_version = request.headers.get("API-Version", self.CURRENT_VERSION)

        # Validate version
        if requested_version not in self.SUPPORTED_VERSIONS:
            return Response(
                content=f'{{"detail": "Unsupported API version: {requested_version}"}}',
                status_code=400,
                media_type="application/json",
            )

        # Add version to request state
        request.state.api_version = requested_version

        # Process request
        response: StarletteResponse = await call_next(request)

        # Add version headers to response
        response.headers["API-Version"] = requested_version
        response.headers["API-Supported-Versions"] = ",".join(self.SUPPORTED_VERSIONS)

        return response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add unique request IDs for tracing.

    Generates or uses provided request IDs for distributed tracing.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[..., Any]
    ) -> StarletteResponse:
        """
        Add request ID to request and response.

        Args:
            request: Incoming request
            call_next: Next middleware in chain

        Returns:
            Response: Response with request ID header
        """
        # Get or generate request ID
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            import uuid

            request_id = str(uuid.uuid4())

        # Add to request state
        request.state.request_id = request_id

        # Process request
        response: StarletteResponse = await call_next(request)

        # Add request ID to response
        response.headers["X-Request-ID"] = request_id

        return response
