# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Request logging middleware.

This module provides structured logging middleware for all API requests
and responses, including performance metrics and error tracking.
"""

import time
from typing import Awaitable, Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from ...utils.logging import get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all HTTP requests and responses with performance metrics.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Process HTTP request and log details.

        Args:
            request: The incoming HTTP request
            call_next: The next middleware or route handler

        Returns:
            Response: The HTTP response
        """
        start_time = time.time()

        # Log request details
        logger.info(
            f"Request: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            },
        )

        # Process request
        try:
            response = await call_next(request)

            # Calculate processing time
            process_time = time.time() - start_time

            # Log response details
            logger.info(
                f"Response: {response.status_code} in {process_time:.3f}s",
                extra={
                    "status_code": response.status_code,
                    "process_time": process_time,
                    "method": request.method,
                    "path": request.url.path,
                },
            )

            # Add performance header
            response.headers["X-Process-Time"] = str(process_time)

            return response

        except Exception as e:
            # Log error details
            process_time = time.time() - start_time
            logger.error(
                f"Request error: {request.method} {request.url.path} - {str(e)}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "process_time": process_time,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise
