# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Tier utility functions for converting between backend and frontend tier names.

This module handles the mapping between internal tier names (used in the database
and backend logic) and user-facing tier names (displayed in the UI).

It also enforces tier-specific restrictions for analysis contexts and roles.
"""

from typing import Any, Dict, List, Optional

from ..core.context_analyzer import AnalysisContext


def get_frontend_tier_name(backend_tier: str) -> str:
    """
    Convert backend tier name to frontend display name.

    Args:
        backend_tier: Backend tier name (free, basic, professional, enterprise, scale_plus)

    Returns:
        Frontend display name (Free, Starter, Growth, Scale, Scale+)
    """
    tier_mapping = {
        "free": "Free",
        "basic": "Starter",
        "professional": "Growth",
        "enterprise": "Scale",
        "scale_plus": "Scale+",
    }
    return tier_mapping.get(backend_tier.lower(), "Free")


def get_backend_tier_name(frontend_tier: str) -> str:
    """
    Convert frontend tier name to backend enum value.

    Args:
        frontend_tier: Frontend display name (Free, Starter, Growth, Scale, Scale+)

    Returns:
        Backend tier name (free, basic, professional, enterprise, scale_plus)
    """
    tier_mapping = {
        "free": "free",
        "starter": "basic",
        "growth": "professional",
        "scale": "enterprise",
        "scale+": "scale_plus",
    }
    return tier_mapping.get(frontend_tier.lower(), "free")


def get_next_tier(current_backend_tier: str) -> Optional[str]:
    """
    Get the next tier in the progression path (backend name).

    Args:
        current_backend_tier: Current backend tier name

    Returns:
        Next backend tier name, or None if already at highest tier
    """
    tier_progression = {
        "free": "basic",
        "basic": "professional",
        "professional": "enterprise",
        "enterprise": "scale_plus",
        "scale_plus": None,  # Already at highest tier
    }
    return tier_progression.get(current_backend_tier.lower())


def get_next_frontend_tier(current_backend_tier: str) -> Optional[str]:
    """
    Get the next tier in the progression path (frontend display name).

    Args:
        current_backend_tier: Current backend tier name

    Returns:
        Next frontend tier display name, or None if already at highest tier
    """
    next_backend = get_next_tier(current_backend_tier)
    if next_backend:
        return get_frontend_tier_name(next_backend)
    return None


def get_tier_display_props(backend_tier: str) -> Dict[str, Any]:
    """
    Get display properties for a tier.

    Args:
        backend_tier: Backend tier name

    Returns:
        Dictionary with display properties including name, color, and description
    """
    tier_props: Dict[str, Dict[str, Any]] = {
        "free": {
            "name": "Free",
            "color": "gray",
            "short_desc": "Essential insights for individual developers",
            "upgrade_message": "Upgrade to Starter for AI-powered analysis",
        },
        "basic": {
            "name": "Starter",
            "color": "blue",
            "short_desc": "Professional insights that save 40% of screening time",
            "upgrade_message": "Upgrade to Growth for deeper analysis and batch processing",
        },
        "professional": {
            "name": "Growth",
            "color": "purple",
            "short_desc": "Scale your hiring with multi-model intelligence",
            "upgrade_message": "Upgrade to Scale for enterprise features and team analysis",
        },
        "enterprise": {
            "name": "Scale",
            "color": "amber",
            "short_desc": "Enterprise confidence with comprehensive analysis",
            "upgrade_message": "Upgrade to Scale+ for maximum depth and Claude 3.7",
        },
        "scale_plus": {
            "name": "Scale+",
            "color": "gradient",
            "short_desc": "Maximum intelligence with exclusive Claude 3.7 access",
            "upgrade_message": None,  # Already at highest tier
        },
    }
    return tier_props.get(backend_tier.lower(), tier_props["free"])


def get_progressive_upgrade_message(
    current_backend_tier: str, feature_category: Optional[str] = None
) -> str:
    """
    Get a progressive upgrade message based on current tier and feature.

    Args:
        current_backend_tier: Current backend tier name
        feature_category: Optional feature category for context-specific messaging

    Returns:
        Upgrade message suggesting the next tier up
    """
    next_tier = get_next_frontend_tier(current_backend_tier)
    if not next_tier:
        return ""

    feature_messages = {
        "batch_analysis": f"Analyze multiple repos at once with {next_tier}",
        "interview_questions": f"Get AI-generated interview questions with {next_tier}",
        "team_analysis": f"Unlock team collaboration insights with {next_tier}",
        "export_formats": f"Export in multiple formats with {next_tier}",
        "priority_support": f"Get priority support with {next_tier}",
        "architectural_analysis": f"See architectural patterns with {next_tier}",
        "temporal_patterns": f"Track skill evolution over time with {next_tier}",
        "work_patterns": f"See detailed work patterns with {next_tier}",
        "deeper_insights": f"Get deeper analysis with {next_tier}",
        "evidence_patterns": f"Unlock more evidence patterns with {next_tier}",
    }

    if feature_category and feature_category in feature_messages:
        return feature_messages[feature_category]

    # Default progressive message
    return f"Upgrade to {next_tier} for enhanced analysis"


def format_tier_for_display(backend_tier: str, include_tier_word: bool = True) -> str:
    """
    Format tier name for user display.

    Args:
        backend_tier: Backend tier name
        include_tier_word: Whether to include the word "tier" in the output

    Returns:
        Formatted tier name for display (e.g., "Scale tier" or just "Scale")
    """
    frontend_name = get_frontend_tier_name(backend_tier)
    if include_tier_word and frontend_name not in ["Free", "Scale+"]:
        return f"{frontend_name} tier"
    return frontend_name


def get_allowed_contexts_for_tier(backend_tier: str) -> List[AnalysisContext]:
    """
    Get allowed analysis contexts for a tier.

    FREE tier: OPEN_SOURCE only
    ALL PAID tiers: ALL contexts (OPEN_SOURCE, STARTUP, ENTERPRISE, AGENCY)

    Args:
        backend_tier: Backend tier name (free, basic, professional, enterprise, scale_plus)

    Returns:
        List of allowed AnalysisContext enum values
    """
    if backend_tier.lower() == "free":
        # FREE tier: Open source context only
        return [AnalysisContext.OPEN_SOURCE]
    else:
        # ALL PAID tiers: All contexts available
        return [
            AnalysisContext.OPEN_SOURCE,
            AnalysisContext.STARTUP,
            AnalysisContext.ENTERPRISE,
            AnalysisContext.AGENCY,
        ]


def get_allowed_roles_for_tier(backend_tier: str) -> List[str]:
    """
    Get allowed role levels for a tier.

    FREE tier: NO role selection (basic analysis only)
    ALL PAID tiers: All roles (junior, mid, senior)

    Args:
        backend_tier: Backend tier name

    Returns:
        List of allowed role strings
    """
    if backend_tier.lower() == "free":
        # FREE tier: No role-specific analysis
        return []
    else:
        # ALL PAID tiers: All role levels available
        return ["junior", "mid", "senior"]


def validate_context_for_tier(
    context: AnalysisContext, backend_tier: str
) -> tuple[bool, Optional[str]]:
    """
    Validate if a context is allowed for a tier.

    Args:
        context: Analysis context to validate
        backend_tier: Backend tier name

    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if valid
        - (False, error_message) if invalid
    """
    allowed_contexts = get_allowed_contexts_for_tier(backend_tier)

    if context not in allowed_contexts:
        if backend_tier.lower() == "free":
            return (
                False,
                "FREE tier only supports Open Source context. Upgrade to Starter ($49/mo) to analyze for Startup, Enterprise, or Agency contexts.",
            )
        else:
            return (False, f"Context {context.value} is not available for your tier.")

    return (True, None)


def validate_role_for_tier(role: str, backend_tier: str) -> tuple[bool, Optional[str]]:
    """
    Validate if a role is allowed for a tier.

    Args:
        role: Role level to validate
        backend_tier: Backend tier name

    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if valid
        - (False, error_message) if invalid
    """
    allowed_roles = get_allowed_roles_for_tier(backend_tier)

    if role.lower() not in allowed_roles:
        if backend_tier.lower() == "free":
            return (
                False,
                "FREE tier does not support role-specific analysis. Upgrade to Starter ($49/mo) to analyze for Junior, Mid, or Senior roles.",
            )
        else:
            return (False, f"Role {role} is not available for your tier.")

    return (True, None)
