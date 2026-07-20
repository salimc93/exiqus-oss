# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Consent and privacy preference management routes.

This module provides endpoints for users to manage their data consent
and privacy preferences with tier-based defaults.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.connection import get_db_session
from ...database.models import User
from ...utils.logging import get_logger
from ..auth.dependencies import get_current_active_user
from ..services.consent_service import (
    CURRENT_CONSENT_VERSION,
    TIER_DEFAULT_CONSENT,
    ConsentService,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/consent", tags=["Privacy"])


class ConsentSettings(BaseModel):
    """User consent settings model."""

    analysis_storage: bool
    training_usage: bool
    anonymized: bool
    retention_period: str
    third_party_sharing: bool
    custom_retention_days: Optional[int] = None


class ConsentResponse(BaseModel):
    """Response model for consent settings."""

    consent_settings: Dict[str, Any]
    tier_defaults: Dict[str, Any]
    consent_version: str
    consent_notice: Optional[str] = None
    show_notice: bool = False


class ConsentUpdateRequest(BaseModel):
    """Request model for updating consent."""

    training_usage: Optional[bool] = None
    anonymized: Optional[bool] = None
    retention_period: Optional[str] = None
    third_party_sharing: Optional[bool] = None
    custom_retention_days: Optional[int] = None
    dismiss_notice: bool = False


class ConsentUpdateResponse(BaseModel):
    """Response model for consent update."""

    success: bool
    message: str
    updated_settings: Dict[str, Any]


@router.get("/settings", response_model=ConsentResponse)
async def get_consent_settings(
    user: User = Depends(get_current_active_user),
) -> ConsentResponse:
    """
    Get current consent settings for the authenticated user.

    Returns effective consent settings combining tier defaults
    and user preferences.
    """
    # Get effective consent
    consent = ConsentService.get_user_consent(user)

    # Get tier defaults for comparison
    tier_defaults = TIER_DEFAULT_CONSENT[user.subscription_plan].copy()

    # Check if notice should be shown
    show_notice = ConsentService.should_show_consent_notice(user)
    consent_notice = None
    if show_notice:
        consent_notice = ConsentService.get_consent_notice(user.subscription_plan)

    return ConsentResponse(
        consent_settings=consent,
        tier_defaults=tier_defaults,
        consent_version=CURRENT_CONSENT_VERSION,
        consent_notice=consent_notice,
        show_notice=show_notice,
    )


@router.put("/settings", response_model=ConsentUpdateResponse)
async def update_consent_settings(
    update_request: ConsentUpdateRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> ConsentUpdateResponse:
    """
    Update user consent settings.

    Updates user privacy preferences within tier constraints.
    Free tier users have limited customization options.
    """
    try:
        # Extract non-None updates
        updates: Dict[str, Any] = {}
        if update_request.training_usage is not None:
            updates["training_usage"] = update_request.training_usage
        if update_request.anonymized is not None:
            updates["anonymized"] = update_request.anonymized
        if update_request.retention_period is not None:
            updates["retention_period"] = update_request.retention_period
        if update_request.third_party_sharing is not None:
            updates["third_party_sharing"] = update_request.third_party_sharing
        if update_request.custom_retention_days is not None:
            updates["custom_retention_days"] = update_request.custom_retention_days

        # Validate updates based on tier
        validated_updates = ConsentService.validate_consent_update(user, updates)

        # Get current consent and merge updates
        current_consent = ConsentService.get_user_consent(user)
        current_consent.update(validated_updates)

        # Save to user preferences
        import json

        user.privacy_preferences = json.dumps(current_consent)

        # Update consent version if accepting
        if update_request.dismiss_notice:
            user.consent_version_accepted = CURRENT_CONSENT_VERSION
            user.consent_notice_dismissed_at = datetime.now(timezone.utc)

        await db.commit()

        # Log consent update
        logger.info(
            f"User {user.user_id} updated consent settings: {validated_updates}"
        )

        return ConsentUpdateResponse(
            success=True,
            message="Consent settings updated successfully",
            updated_settings=validated_updates,
        )

    except Exception as e:
        logger.error(f"Failed to update consent for user {user.user_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update consent settings",
        )


@router.post("/accept-notice", response_model=Dict[str, Any])
async def accept_consent_notice(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Accept the consent notice and dismiss it.

    Marks the consent notice as seen and accepted.
    """
    try:
        user.consent_version_accepted = CURRENT_CONSENT_VERSION
        user.consent_notice_dismissed_at = datetime.now(timezone.utc)

        await db.commit()

        logger.info(
            f"User {user.user_id} accepted consent notice v{CURRENT_CONSENT_VERSION}"
        )

        return {
            "success": True,
            "message": "Consent notice accepted",
            "consent_version": CURRENT_CONSENT_VERSION,
        }

    except Exception as e:
        logger.error(f"Failed to accept consent notice for user {user.user_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to accept consent notice",
        )


@router.get("/export-preferences", response_model=Dict[str, Any])
async def export_privacy_preferences(
    user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Export user privacy preferences for GDPR compliance.

    Returns all privacy-related settings and consent history.
    """
    consent = ConsentService.get_user_consent(user)

    return {
        "user_id": user.user_id,
        "email": user.email,
        "consent_settings": consent,
        "consent_version_accepted": user.consent_version_accepted,
        "consent_notice_dismissed_at": (
            user.consent_notice_dismissed_at.isoformat()
            if user.consent_notice_dismissed_at
            else None
        ),
        "subscription_plan": user.subscription_plan.value,
        "data_retention_days": ConsentService.get_retention_days(user),
        "export_timestamp": datetime.now(timezone.utc).isoformat(),
    }
