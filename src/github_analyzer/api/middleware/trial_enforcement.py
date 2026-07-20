# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Trial enforcement middleware for API usage limits.

This middleware enforces trial user limits and tracks analysis usage
for accurate billing and quota management.
"""

import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, Request, Response, status
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from ...database.connection import get_db_session
from ...database.models import AuditLog, BillingUsageRecord, User
from ..auth.jwt import JWTError, extract_user_id


class TrialEnforcementMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce trial user limits and track usage.

    This middleware:
    1. Identifies trial users from JWT tokens
    2. Checks if they have exceeded their analysis limits
    3. Tracks analysis usage for billing
    4. Enforces trial expiry dates
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Process request and enforce trial limits if applicable."""
        protected_endpoints = {
            "/api/v1/analyze",
            "/api/v1/batch",
        }

        # Only check protected endpoints
        if not any(request.url.path.startswith(ep) for ep in protected_endpoints):
            return await call_next(request)

        # Extract user ID from token if present
        user_id = await self._get_user_id_from_request(request)
        if not user_id:
            # No authentication, let other middleware handle it
            return await call_next(request)

        # Get user from database
        async for db in get_db_session():
            result = await db.execute(select(User).where(User.user_id == user_id))
            user = result.scalar_one_or_none()

            if not user:
                # User not found, let auth middleware handle it
                return await call_next(request)

            # Check if user is a trial user
            if not user.is_trial:
                # Not a trial user, no limits apply
                return await call_next(request)

            # Check trial expiry
            if user.trial_end_date:
                # Ensure timezone-aware comparison (SQLite returns naive datetimes)
                trial_end = user.trial_end_date
                if trial_end.tzinfo is None:
                    trial_end = trial_end.replace(tzinfo=timezone.utc)
                if trial_end < datetime.now(timezone.utc):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Trial period has expired. Please upgrade to continue using the service.",
                    )

            # Check usage limits (if not unlimited)
            if user.trial_analyses_limit is not None:
                if user.analyses_consumed >= user.trial_analyses_limit:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Trial limit reached. You have used {user.analyses_consumed} of {user.trial_analyses_limit} analyses.",
                    )

            # Store user info in request state for later use
            request.state.trial_user = {
                "user_id": user.user_id,
                "is_trial": True,
                "trial_plan": user.trial_plan,
                "analyses_limit": user.trial_analyses_limit,
                "analyses_consumed": user.analyses_consumed,
            }
            break  # Exit after processing with first db session

        # Process the request
        response = await call_next(request)

        # If request was successful, increment usage
        if response.status_code == 200 and hasattr(request.state, "trial_user"):
            await self._increment_usage(user_id, request)

        return response

    async def _get_user_id_from_request(self, request: Request) -> Optional[str]:
        """Extract user ID from JWT token in Authorization header."""
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None

        token = auth_header.split(" ")[1]
        try:
            return extract_user_id(token)
        except JWTError:
            return None

    async def _increment_usage(self, user_id: str, request: Request) -> None:
        """Increment usage counter for trial user after successful analysis."""
        async for db in get_db_session():
            async with db.begin():  # Start transaction
                # Get user with row lock
                result = await db.execute(
                    select(User).where(User.user_id == user_id).with_for_update()
                )
                user = result.scalar_one_or_none()

                if not user or not user.is_trial:
                    return

                # Determine number of analyses from request
                analyses_count = 1
                if request.url.path.endswith("/batch"):
                    # For batch endpoint, count number of repositories
                    try:
                        body = await request.body()
                        data = json.loads(body) if body else {}
                        analyses_count = len(data.get("repository_urls", []))
                    except Exception:
                        analyses_count = 1

                # Increment usage
                user.analyses_consumed += analyses_count

                # Create billing usage record
                usage_record = BillingUsageRecord(
                    record_id=f"usage_{user_id}_{datetime.now(timezone.utc).timestamp()}",
                    user_id=user_id,
                    usage_type="trial_analysis",
                    usage_count=analyses_count,
                    billing_period=datetime.now(timezone.utc).strftime("%Y-%m"),
                    unit_cost="0.00",  # Trial analyses are free
                    total_cost="0.00",
                    request_metadata=json.dumps(
                        {
                            "endpoint": str(request.url.path),
                            "trial_plan": user.trial_plan,
                            "analyses_consumed": user.analyses_consumed,
                            "analyses_limit": user.trial_analyses_limit,
                        }
                    ),
                )
                db.add(usage_record)

                # Create audit log
                audit_log = AuditLog(
                    log_id=f"audit_{user_id}_{datetime.now(timezone.utc).timestamp()}",
                    action="trial_usage_incremented",
                    target_user_id=user_id,
                    action_metadata=json.dumps(
                        {
                            "analyses_count": analyses_count,
                            "total_consumed": user.analyses_consumed,
                            "limit": user.trial_analyses_limit,
                            "endpoint": str(request.url.path),
                        }
                    ),
                )
                db.add(audit_log)
            # Transaction commits here
            break  # Exit after processing with first db session
