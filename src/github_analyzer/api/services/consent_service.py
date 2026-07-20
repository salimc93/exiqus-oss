# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Consent management service with tier-based defaults.

This service manages user consent for data usage, including tier-based
default settings and GDPR compliance features.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict

from ...database.models import SubscriptionPlan, User

# Current consent version - increment when consent terms change
CURRENT_CONSENT_VERSION = "1.0"


# Tier-based default consent settings
TIER_DEFAULT_CONSENT: Dict[SubscriptionPlan, Dict[str, Any]] = {
    SubscriptionPlan.FREE: {
        "analysis_storage": True,  # Store analysis results
        "training_usage": True,  # Opt-in by default (with clear notice)
        "anonymized": True,  # Always anonymize free tier data
        "retention_period": "2_years",
        "third_party_sharing": False,
        "consent_notice_shown": False,  # Track if user has seen notice
    },
    SubscriptionPlan.BASIC: {
        "analysis_storage": True,
        "training_usage": True,  # Opt-in by default (with clear notice)
        "anonymized": True,  # Anonymize by default
        "retention_period": "3_years",
        "third_party_sharing": False,
        "consent_notice_shown": False,
    },
    SubscriptionPlan.PROFESSIONAL: {
        "analysis_storage": True,
        "training_usage": False,  # Privacy-first: opt-out by default
        "anonymized": False,  # Keep data intact for pro users
        "retention_period": "5_years",
        "third_party_sharing": False,
        "consent_notice_shown": False,
    },
    SubscriptionPlan.ENTERPRISE: {
        "analysis_storage": True,
        "training_usage": False,  # Privacy-first: opt-out by default
        "anonymized": False,  # Full control for enterprise
        "retention_period": "custom",  # Configurable by contract
        "third_party_sharing": False,
        "consent_notice_shown": False,
        "custom_retention_days": 730,  # 2 years default, configurable
    },
    SubscriptionPlan.SCALE_PLUS: {
        "analysis_storage": True,
        "training_usage": False,  # Privacy-first: opt-out by default
        "anonymized": False,  # Full control for scale+ users
        "retention_period": "custom",  # Configurable by contract
        "third_party_sharing": False,
        "consent_notice_shown": False,
        "custom_retention_days": 1095,  # 3 years default, configurable
    },
}


class ConsentService:
    """Manage user consent with tier-based defaults."""

    @staticmethod
    def get_user_consent(user: User) -> Dict[str, Any]:
        """Get effective consent combining tier defaults and user preferences."""
        # Start with tier defaults
        tier_defaults = TIER_DEFAULT_CONSENT[user.subscription_plan].copy()

        # Override with user preferences if set
        if user.privacy_preferences:
            user_prefs = json.loads(user.privacy_preferences)
            tier_defaults.update(user_prefs)

        # Add metadata
        tier_defaults["tier"] = user.subscription_plan.value
        tier_defaults["consent_version"] = CURRENT_CONSENT_VERSION

        return tier_defaults

    @staticmethod
    def should_show_consent_notice(user: User) -> bool:
        """Check if user should see consent notice."""
        consent = ConsentService.get_user_consent(user)

        # Show notice for free/basic tiers who haven't dismissed it
        if user.subscription_plan in [SubscriptionPlan.FREE, SubscriptionPlan.BASIC]:
            return (
                not consent.get("consent_notice_shown", False)
                and user.consent_notice_dismissed_at is None
            )

        # Pro/Enterprise/Scale+: Show if they haven't seen the privacy-first notice
        return user.consent_version_accepted != CURRENT_CONSENT_VERSION

    @staticmethod
    def get_consent_notice(tier: SubscriptionPlan) -> str:
        """Get appropriate consent notice based on tier."""
        if tier in [SubscriptionPlan.FREE, SubscriptionPlan.BASIC]:
            return (
                "Your anonymized analysis data helps improve our AI models. "
                "You can opt-out anytime in settings. Learn more about our "
                "privacy practices at /privacy"
            )
        else:  # Professional/Enterprise/Scale+
            return (
                "Your analysis data is private by default. You can choose to "
                "contribute anonymized data to improve our AI models in settings."
            )

    @staticmethod
    def validate_consent_update(user: User, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Validate consent updates based on user tier."""
        # Free tier has limited customization
        if user.subscription_plan == SubscriptionPlan.FREE:
            # Can only opt-out of training, not storage
            allowed_fields = {"training_usage"}
            return {k: v for k, v in updates.items() if k in allowed_fields}

        # Other tiers can customize all consent options
        return updates

    @staticmethod
    def create_consent_snapshot(user: User) -> Dict[str, Any]:
        """Create a snapshot of current consent for storage with analysis."""
        consent = ConsentService.get_user_consent(user)
        consent["snapshot_date"] = datetime.now(timezone.utc).isoformat()
        consent["user_id"] = user.user_id
        return consent

    @staticmethod
    def should_allow_training(consent: Dict[str, Any]) -> bool:
        """Check if data should be used for training based on consent."""
        training_usage = bool(consent.get("training_usage", False))
        anonymized = bool(consent.get("anonymized", True))
        return training_usage and anonymized

    @staticmethod
    def get_retention_days(user: User) -> int:
        """Get retention period in days based on user tier and settings."""
        consent = ConsentService.get_user_consent(user)
        retention = consent.get("retention_period", "2_years")

        if retention == "custom":
            custom_days = consent.get("custom_retention_days", 730)  # Default 2 years
            return int(custom_days)

        retention_map = {
            "1_year": 365,
            "2_years": 730,
            "3_years": 1095,
            "5_years": 1825,
            "indefinite": 36500,  # ~100 years
        }

        return retention_map.get(str(retention), 730)  # Default 2 years
