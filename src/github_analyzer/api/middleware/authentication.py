# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Authentication middleware for API requests.

This middleware handles API key authentication for incoming requests,
validating API keys and setting user context for authenticated requests.
"""

import logging
from typing import Any, Optional, cast

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ...database.connection import get_db_session
from ...database.models import APIKey
from ..services.api_key_service import APIKeyService

logger = logging.getLogger(__name__)


class APIKeyAuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle API key authentication.

    This middleware:
    1. Extracts API keys from X-API-Key header
    2. Validates API keys using the secure APIKeyService
    3. Sets user context for authenticated requests
    4. Tracks API key usage for billing/analytics
    5. Enforces quota limits for API key usage
    """

    def __init__(self, app: Any, enforce_quota: bool = True) -> None:
        """
        Initialize the authentication middleware.

        Args:
            app: FastAPI application instance
            enforce_quota: Whether to enforce API quota limits
        """
        super().__init__(app)
        self.enforce_quota = enforce_quota

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """
        Process incoming request with API key authentication.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            Response: HTTP response
        """
        # Check if request has API key
        api_key = request.headers.get("X-API-Key")

        if api_key:
            try:
                # Validate API key and get user context
                api_key_record = await self._validate_api_key(api_key)

                if api_key_record:
                    # Set user context in request state
                    request.state.authenticated_user_id = api_key_record.user_id
                    request.state.api_key_record = api_key_record
                    request.state.auth_method = "api_key"

                    # Check quota if enforcement is enabled
                    if self.enforce_quota:
                        quota_check = await self._check_quota(api_key_record)
                        if not quota_check:
                            return JSONResponse(
                                status_code=429,
                                content={
                                    "detail": "API quota exceeded. Please upgrade your plan or wait for quota reset.",
                                    "error_code": "QUOTA_EXCEEDED",
                                },
                            )

                    logger.info(
                        f"API key authentication successful for user {api_key_record.user_id} "
                        f"(key: {api_key_record.name})"
                    )

                    # Continue to next middleware/handler
                    response = await call_next(request)

                    # Track API usage after successful request
                    await self._track_usage(api_key_record)

                    return cast(Response, response)
                else:
                    # Invalid API key
                    return JSONResponse(
                        status_code=401,
                        content={
                            "detail": "Invalid API key",
                            "error_code": "INVALID_API_KEY",
                        },
                        headers={"WWW-Authenticate": "Bearer"},
                    )

            except Exception as e:
                logger.error(f"API key authentication error: {str(e)}")
                return JSONResponse(
                    status_code=500,
                    content={
                        "detail": "Authentication service error",
                        "error_code": "AUTH_SERVICE_ERROR",
                    },
                )

        # No API key provided - continue without authentication
        response = await call_next(request)
        return cast(Response, response)

    async def _validate_api_key(self, api_key: str) -> Optional[APIKey]:
        """
        Validate API key using the secure APIKeyService.

        Args:
            api_key: Plain text API key

        Returns:
            APIKey record if valid, None otherwise
        """
        try:
            # Get database session
            db_generator = get_db_session()
            db = await db_generator.__anext__()
            try:
                service = APIKeyService(db)

                # Use the secure O(1) validation method
                api_key_record = await service.validate_api_key(api_key)

                return api_key_record
            finally:
                await db.close()

        except Exception as e:
            logger.error(f"API key validation error: {str(e)}")
            return None

    async def _check_quota(self, api_key_record: APIKey) -> bool:
        """
        Check if API key has available quota.

        Args:
            api_key_record: API key database record

        Returns:
            bool: True if quota is available, False otherwise
        """
        try:
            db_generator = get_db_session()
            db = await db_generator.__anext__()
            try:
                service = APIKeyService(db)

                has_quota, remaining = await service.check_quota_available(
                    api_key_record
                )

                logger.debug(
                    f"Quota check for API key {api_key_record.name}: "
                    f"has_quota={has_quota}, remaining={remaining}"
                )

                return has_quota
            finally:
                await db.close()

        except Exception as e:
            logger.error(f"Quota check error: {str(e)}")
            # On error, allow the request to proceed (fail open)
            return True

    async def _track_usage(self, api_key_record: APIKey) -> None:
        """
        Track API key usage for billing and analytics.

        Args:
            api_key_record: API key database record
        """
        try:
            db_generator = get_db_session()
            db = await db_generator.__anext__()
            try:
                service = APIKeyService(db)

                # Increment usage counter
                await service.increment_usage(api_key_record.key_id)

                logger.debug(f"Usage tracked for API key {api_key_record.name}")
            finally:
                await db.close()

        except Exception as e:
            logger.error(f"Usage tracking error: {str(e)}")
            # Don't fail the request if usage tracking fails


class APIKeyValidationMiddleware(BaseHTTPMiddleware):
    """
    Lightweight middleware for API key validation without quota enforcement.

    This is useful for health checks and other endpoints where we want to
    validate API keys but not enforce quotas.
    """

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """
        Process incoming request with API key validation only.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            Response: HTTP response
        """
        # Check if request has API key
        api_key = request.headers.get("X-API-Key")

        if api_key:
            try:
                # Validate API key format and existence
                db_generator = get_db_session()
                db = await db_generator.__anext__()
                try:
                    service = APIKeyService(db)
                    api_key_record = await service.validate_api_key(api_key)

                    if api_key_record:
                        # Set minimal user context
                        request.state.authenticated_user_id = api_key_record.user_id
                        request.state.auth_method = "api_key_validation"

                        logger.debug(
                            f"API key validation successful for user {api_key_record.user_id}"
                        )
                    else:
                        # Invalid API key - but don't block the request
                        logger.warning(f"Invalid API key provided: {api_key[:10]}...")
                finally:
                    await db.close()

            except Exception as e:
                logger.error(f"API key validation error: {str(e)}")

        # Continue to next middleware/handler
        response = await call_next(request)
        return cast(Response, response)
