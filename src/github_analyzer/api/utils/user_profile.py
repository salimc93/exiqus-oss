# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Utility functions for user profile management.

This module provides helper functions for converting between database models
and API response models, handling enum conversions and data transformation.
"""

from ...database.models import SubscriptionPlan as DBSubscriptionPlan
from ...database.models import SubscriptionStatus as DBSubscriptionStatus
from ...database.models import User
from ...database.models import UserRole as DBUserRole
from ..models.auth import SubscriptionPlan as APISubscriptionPlan
from ..models.auth import SubscriptionStatus as APISubscriptionStatus
from ..models.auth import UserProfile
from ..models.auth import UserRole as APIUserRole
from ..services.consent_service import ConsentService


def convert_db_user_to_profile(user: User) -> UserProfile:
    """
    Convert a database User model to API UserProfile response.

    Handles enum conversions between database and API models and includes
    consent information.

    Args:
        user: Database User model

    Returns:
        UserProfile: API response model with consent data
    """
    # Get consent settings
    consent_settings = ConsentService.get_user_consent(user)
    show_consent_notice = ConsentService.should_show_consent_notice(user)

    # Map database subscription plan values to API values
    # Database uses uppercase (FREE, BASIC, PROFESSIONAL, ENTERPRISE)
    # API uses lowercase (free, basic, professional, enterprise)
    subscription_plan_value = user.subscription_plan.value.lower()

    # Map backend names to frontend names for the response
    # Backend database: FREE, BASIC, PROFESSIONAL, ENTERPRISE, SCALE_PLUS
    # Frontend expects: free, starter, growth, scale, scale_plus
    plan_mapping = {
        "free": "free",
        "basic": "starter",  # BASIC -> starter
        "professional": "growth",  # PROFESSIONAL -> growth
        "enterprise": "scale",  # ENTERPRISE -> scale
        "scale_plus": "scale_plus",  # SCALE_PLUS -> scale_plus
    }
    frontend_plan_name = plan_mapping.get(
        subscription_plan_value, subscription_plan_value
    )

    return UserProfile(
        user_id=user.user_id,
        email=user.email,
        full_name=user.full_name,
        company=user.company,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
        last_login=user.last_login,
        usage_quota=user.usage_quota,
        usage_consumed=user.usage_count,
        user_role=APIUserRole(user.user_role.value),
        subscription_plan=frontend_plan_name,
        subscription_status=APISubscriptionStatus(user.subscription_status.value),
        subscription_start_date=user.subscription_start_date,
        subscription_end_date=user.subscription_end_date,
        trial_end_date=user.trial_end_date,
        company_size=user.company_size,
        industry=user.industry,
        use_case=user.use_case,
        consent_settings=consent_settings,
        consent_version=user.consent_version_accepted,
        show_consent_notice=show_consent_notice,
    )


def convert_api_user_role_to_db(role: APIUserRole) -> DBUserRole:
    """Convert API UserRole to database UserRole."""
    return DBUserRole(role.value)


def convert_api_subscription_plan_to_db(
    plan: APISubscriptionPlan,
) -> DBSubscriptionPlan:
    """Convert API SubscriptionPlan to database SubscriptionPlan."""
    # Convert from API enum values to database enum values
    # API uses lowercase, database uses uppercase
    return DBSubscriptionPlan(plan.value.upper())


def convert_api_subscription_status_to_db(
    status: APISubscriptionStatus,
) -> DBSubscriptionStatus:
    """Convert API SubscriptionStatus to database SubscriptionStatus."""
    return DBSubscriptionStatus(status.value)
