# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Admin routes for trial/invite system management.

This module provides admin-only endpoints for managing trial invitations,
monitoring trial usage, and administering trial accounts.
"""

import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.connection import get_db_session
from ...database.models import AuditLog, User
from ...database.operations import UserOperations
from ..auth.dependencies import require_admin

router = APIRouter(prefix="/admin/trials", tags=["Trial Administration"])


# Request/Response models for trial management
class GrantTrialRequest(BaseModel):
    """Request model for granting trial access."""

    email: EmailStr
    trial_days: int = 7
    trial_plan: str = "professional"
    custom_limit: Optional[int] = None


class GrantTrialResponse(BaseModel):
    """Response model for granted trial."""

    user_id: str
    invite_link: str
    expires_at: datetime
    trial_details: Dict[str, Any]


# Trial plan configurations. `value` is a free-text label stored on the
# user record; adjust these to whatever tiers your deployment offers.
TRIAL_PLANS: Dict[str, Dict[str, Any]] = {
    "basic": {
        "limit": 100,
        "value": "Basic",
    },
    "professional": {
        "limit": 500,
        "value": "Professional",
    },
    "enterprise": {
        "limit": None,  # Unlimited
        "value": "Enterprise",
    },
    "custom": {
        "limit": None,  # Will be set from custom_limit parameter
        "value": "Custom",
    },
}


@router.post("/grant", response_model=GrantTrialResponse)
async def grant_trial(
    request: GrantTrialRequest,
    admin_user_id: Annotated[str, Depends(require_admin)],
    db: AsyncSession = Depends(get_db_session),
) -> GrantTrialResponse:
    """
    Grant trial access to a new user.

    Creates an inactive user account with trial privileges and generates
    an invite token for account activation. Uses database transactions
    to ensure atomicity.

    Args:
        request: Trial grant details
        admin_user_id: Authenticated admin user ID
        db: Database session

    Returns:
        GrantTrialResponse: Trial details and invite link

    Raises:
        HTTPException: If email already has trial or invalid plan
    """
    # Validate trial plan
    if request.trial_plan not in TRIAL_PLANS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid trial plan. Available plans: {list(TRIAL_PLANS.keys())}",
        )

    plan = dict(TRIAL_PLANS[request.trial_plan])
    if request.trial_plan == "custom" and request.custom_limit is not None:
        plan["limit"] = request.custom_limit

    async with db.begin():  # Start transaction
        # Check if email already used trial
        existing = await UserOperations.get_user_by_email(db, request.email)
        if existing is not None and existing.is_trial:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already used trial",
            )

        # Generate secure invite token
        invite_token = secrets.token_urlsafe(32)

        # Create user with trial settings
        user_id = f"usr_{secrets.token_urlsafe(16)}"
        user = User(
            user_id=user_id,
            email=request.email,
            password_hash="",  # nosec B106 # Will be set during activation
            full_name="",  # Will be set during activation
            is_trial=True,
            trial_plan=request.trial_plan,
            trial_analyses_limit=plan["limit"],
            trial_value=plan["value"],
            trial_end_date=datetime.now(timezone.utc)
            + timedelta(days=request.trial_days),
            invite_token=invite_token,
            invite_token_expires=datetime.now(timezone.utc) + timedelta(days=2),
            is_active=False,  # Not active until password set
            analyses_consumed=0,
            has_completed_onboarding=False,
        )
        db.add(user)

        # Create audit log entry
        audit_log = AuditLog(
            log_id=f"log_{secrets.token_urlsafe(16)}",
            action="trial_granted",
            admin_id=admin_user_id,
            target_email=request.email,
            action_metadata=json.dumps(
                {
                    "trial_days": request.trial_days,
                    "trial_plan": request.trial_plan,
                    "limit": plan["limit"],
                    "value": plan["value"],
                }
            ),
        )
        db.add(audit_log)

    # Transaction commits here - all or nothing

    # Generate response
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    invite_link = f"{frontend_url}/activate?token={invite_token}"

    return GrantTrialResponse(
        user_id=user_id,
        invite_link=invite_link,
        expires_at=user.invite_token_expires or datetime.now(timezone.utc),
        trial_details={
            "plan": request.trial_plan,
            "limit": plan["limit"] or "unlimited",
            "value": plan["value"],
            "days": request.trial_days,
            "expires_at": (
                user.trial_end_date.isoformat() if user.trial_end_date else ""
            ),
        },
    )
