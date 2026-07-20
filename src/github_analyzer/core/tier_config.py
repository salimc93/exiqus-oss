# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Centralized tier configuration - The single source of truth.
All tier-specific settings MUST be defined here.

This module contains all subscription tier configurations including:
- Pricing (monthly/annual)
- AI model assignments
- Token limits
- Feature flags
- Smart allocation logic

NO OTHER MODULE should define tier-specific settings.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Tuple


@dataclass
class TierConfiguration:
    """Complete configuration for a subscription tier."""

    # Pricing
    monthly_price: int
    annual_price: int
    analyses_per_month: int

    # AI Models
    main_model: str

    # Token Limits
    main_generation_tokens: int
    unified_approach_tokens: int

    # Optional AI Models
    metrics_model: Optional[str] = None
    questions_model: Optional[str] = None

    # Smart Allocation (Scale+ only)
    use_smart_allocation: bool = False
    token_allocator: Optional[Callable[[int], int]] = None

    # Output Limits (max potential, not minimum requirements)
    max_insights: int = 3  # Maximum insights to generate
    max_questions: int = 3  # Maximum interview questions
    max_recommendations: int = 5  # Maximum recommendations

    # Target Ranges - Commander's Intent (business decisions, not formulas)
    insight_range: Tuple[int, int] = (2, 3)  # Target range for insights
    question_range: Tuple[int, int] = (2, 3)  # Target range for questions
    recommendation_range: Tuple[int, int] = (2, 3)  # Target range for recommendations

    # Features
    features: Dict[str, Any] = field(default_factory=dict)


def scale_plus_token_allocator(repo_size_mb: int) -> int:
    """
    Smart token allocation for Scale+ with higher caps for powerful models.

    Leverages Claude 3.7 Sonnet and Sonnet 4's increased capacity
    to provide comprehensive analysis while maintaining efficiency.
    """
    if repo_size_mb < 50:
        return 12000  # Small repos: Standard allocation
    elif repo_size_mb < 200:
        return 20000  # Medium repos: Enhanced allocation
    else:
        return 35000  # Large repos: Maximum allocation for complex codebases


# The One True Configuration
TIER_CONFIGURATIONS = {
    "free": TierConfiguration(  # Backend: free, Frontend: Free
        monthly_price=0,
        annual_price=0,
        analyses_per_month=10,
        main_model="claude-3-5-haiku-20241022",  # Haiku 3.5 for single repo analysis
        main_generation_tokens=8000,  # Max for Haiku 3.5
        unified_approach_tokens=8000,  # Max tokens for Haiku 3.5
        max_insights=3,
        max_questions=3,
        max_recommendations=3,
        # Commander's Intent target ranges
        insight_range=(2, 3),
        question_range=(2, 3),
        recommendation_range=(2, 3),
        features={
            "ai_analyses": 3,
            "public_repos_only": True,
            "export_formats": ["json"],
            "portfolio_access": False,  # Single repo analysis ONLY
            # RESTRICTIONS:
            "allowed_contexts": ["OPEN_SOURCE"],  # Only Open Source context
            "allowed_roles": [],  # No role-specific analysis (basic analysis only)
        },
    ),
    "basic": TierConfiguration(  # Backend: basic, Frontend: Starter
        monthly_price=49,
        annual_price=490,
        analyses_per_month=10,  # 10 candidate assessments per month
        main_model="claude-haiku-4-5-20251001",  # UPGRADED: Haiku 4.5 for portfolio analysis
        main_generation_tokens=16000,  # Leverage 64K output capacity
        unified_approach_tokens=16000,  # Full portfolio analysis support
        max_insights=10,  # Fixed for all repos
        max_questions=10,
        max_recommendations=7,
        # Commander's Intent target ranges - Fixed for all repos
        insight_range=(8, 10),  # Always 8-10 regardless of repo size
        question_range=(8, 10),  # Always 8-10 regardless of repo size
        recommendation_range=(5, 7),  # Always 5-7 regardless of repo size
        features={
            "ai_analyses": 50,  # 50 single repo deep dives per month
            "candidate_assessments": 10,  # 10 candidate assessments (portfolio/PR)
            "public_repos_only": True,
            "export_formats": ["json", "html", "pdf"],
            "batch_analysis": 2,
            "portfolio_access": True,  # Full portfolio analysis enabled
            # FULL ACCESS:
            "allowed_contexts": ["OPEN_SOURCE", "STARTUP", "ENTERPRISE", "AGENCY"],
            "allowed_roles": ["junior", "mid", "senior"],
        },
    ),
    "professional": TierConfiguration(  # Backend: professional, Frontend: Growth
        monthly_price=199,
        annual_price=1990,
        analyses_per_month=50,  # 50 candidate assessments per month
        # UPGRADED: Single-model approach with Haiku 4.5 (64K output!)
        main_model="claude-haiku-4-5-20251001",  # Haiku 4.5 - 64K output capacity
        metrics_model=None,  # REMOVED: Single model for all operations
        questions_model=None,  # REMOVED: Single model for all operations
        main_generation_tokens=16000,  # INCREASED: Leverage 64K capacity
        unified_approach_tokens=16000,  # INCREASED: Richer outputs with 2x capacity
        max_insights=15,  # With 64K output, can generate more
        max_questions=15,
        max_recommendations=15,
        # Commander's Intent target ranges
        insight_range=(12, 15),
        question_range=(12, 15),
        recommendation_range=(9, 12),
        features={
            "ai_analyses": 100,  # 100 single repo deep dives per month
            "candidate_assessments": 50,  # 50 candidate assessments (portfolio/PR)
            "public_repos_only": True,
            "interview_questions": 10,
            "temporal_analysis": True,
            "export_formats": ["json", "html", "pdf"],
            "batch_analysis": 5,
            "priority_support": True,
            "portfolio_access": True,  # Full portfolio analysis enabled
            # FULL ACCESS:
            "allowed_contexts": ["OPEN_SOURCE", "STARTUP", "ENTERPRISE", "AGENCY"],
            "allowed_roles": ["junior", "mid", "senior"],
        },
    ),
    "enterprise": TierConfiguration(  # Backend: enterprise, Frontend: Scale
        monthly_price=499,
        annual_price=4990,
        analyses_per_month=200,  # 200 candidate assessments per month
        # UPGRADED: Sonnet 4 for premium intelligence
        main_model="claude-sonnet-4-20250514",  # Sonnet 4 - High intelligence
        metrics_model=None,  # REMOVED: Clean single-model approach
        questions_model=None,  # REMOVED: Clean single-model approach
        main_generation_tokens=20000,  # INCREASED: Premium analysis with more capacity
        unified_approach_tokens=20000,  # INCREASED: Comprehensive outputs
        max_insights=18,
        max_questions=18,
        max_recommendations=18,
        # Commander's Intent target ranges
        insight_range=(15, 18),
        question_range=(15, 18),
        recommendation_range=(12, 15),
        features={
            "ai_analyses": 250,  # 250 single repo deep dives per month
            "candidate_assessments": 200,  # 200 candidate assessments (portfolio/PR)
            "public_repos_only": True,
            "interview_questions": 30,
            "temporal_analysis": True,
            "comprehensive_patterns": True,
            "export_formats": ["json", "html", "pdf", "markdown"],
            "batch_analysis": 10,
            "batch_history": True,
            "priority_support": True,
            "sla_12_hours": True,
            "overage_rate": 0.10,  # $0.10 per extra analysis
            "portfolio_access": True,  # Full portfolio analysis enabled
            # FULL ACCESS:
            "allowed_contexts": ["OPEN_SOURCE", "STARTUP", "ENTERPRISE", "AGENCY"],
            "allowed_roles": ["junior", "mid", "senior"],
        },
    ),
    "scale_plus": TierConfiguration(  # Backend: scale_plus, Frontend: Scale+
        monthly_price=2500,  # NEW PRICE (was $1,997)
        annual_price=25000,
        analyses_per_month=500,  # 500 candidate assessments per month
        # HYBRID: Sonnet 4 for main analysis + Sonnet 4.5 for questions
        main_model="claude-sonnet-4-20250514",  # Sonnet 4 for main analysis
        metrics_model=None,  # REMOVED: Single model cleaner
        questions_model="claude-sonnet-4-5-20250929",  # Sonnet 4.5 for deep questions
        main_generation_tokens=32000,  # INCREASED: Maximum depth with 64K capacity
        unified_approach_tokens=32000,  # INCREASED: Comprehensive analysis
        use_smart_allocation=True,
        token_allocator=scale_plus_token_allocator,
        max_insights=35,  # UNCAPPED: Generate as many as evidence supports
        max_questions=35,  # UNCAPPED: Generate as many as evidence supports
        max_recommendations=20,  # More than Enterprise's max
        # Commander's Intent target ranges - maximize evidence utilization
        insight_range=(25, 35),  # Generate MORE when evidence is abundant
        question_range=(25, 35),  # Generate MORE when evidence is abundant
        recommendation_range=(15, 20),  # More than Enterprise's 12-15
        features={
            "ai_analyses": -1,  # Unlimited single repo deep dives
            "candidate_assessments": 500,  # 500 candidate assessments (portfolio/PR)
            "public_repos_only": True,
            "interview_questions": 50,
            "temporal_analysis": True,
            "comprehensive_patterns": True,
            "export_formats": ["json", "html", "pdf", "markdown"],
            "batch_analysis": 15,
            "batch_history": True,
            "api_access": True,
            "priority_support": True,
            "dedicated_support": True,
            "sla_6_hours": True,
            "custom_integrations": True,
            "overage_rate": 0.10,
            "portfolio_access": True,  # Full portfolio analysis enabled
            "use_hybrid_approach": True,  # Use Sonnet 4 + 4.5 hybrid
            # FULL ACCESS:
            "allowed_contexts": ["OPEN_SOURCE", "STARTUP", "ENTERPRISE", "AGENCY"],
            "allowed_roles": ["junior", "mid", "senior"],
        },
    ),
}


# TIER RESTRICTIONS SUMMARY:
# FREE: Open Source context ONLY, NO role selection (basic analysis)
# ALL PAID (Starter/Growth/Scale/Scale+): ALL contexts + ALL roles


def get_tier_config(tier: str) -> Optional[TierConfiguration]:
    """
    Get configuration for a specific tier.

    Args:
        tier: Tier name (case-insensitive)

    Returns:
        TierConfiguration object or None if tier not found
    """
    return TIER_CONFIGURATIONS.get(tier.lower())


def get_model_for_tier(tier: str, model_type: str = "main") -> str:
    """
    Get the appropriate AI model for a tier.

    Args:
        tier: Tier name
        model_type: Type of model ("main", "metrics", "questions")

    Returns:
        Model identifier string
    """
    config = get_tier_config(tier)
    if not config:
        # Fallback to free tier model
        return TIER_CONFIGURATIONS["free"].main_model

    if model_type == "metrics" and config.metrics_model:
        return config.metrics_model
    elif model_type == "questions" and config.questions_model:
        return config.questions_model
    else:
        return config.main_model


def get_token_limit(tier: str, limit_type: str = "main") -> int:
    """
    Get token limit for a tier.

    Args:
        tier: Tier name
        limit_type: Type of limit ("main" or "unified")

    Returns:
        Token limit as integer
    """
    config = get_tier_config(tier)
    if not config:
        # Fallback to free tier limits
        config = TIER_CONFIGURATIONS["free"]

    if limit_type == "unified":
        return config.unified_approach_tokens
    else:
        return config.main_generation_tokens


def get_output_limits(tier: str) -> Dict[str, int]:
    """
    Get output limits for insights, questions, and recommendations.

    Args:
        tier: Tier name

    Returns:
        Dictionary with max_insights, max_questions, max_recommendations
    """
    config = get_tier_config(tier)
    if not config:
        config = TIER_CONFIGURATIONS["free"]

    return {
        "max_insights": config.max_insights,
        "max_questions": config.max_questions,
        "max_recommendations": config.max_recommendations,
    }


def get_target_ranges(tier: str) -> Dict[str, Tuple[int, int]]:
    """
    Get target ranges for a tier (Commander's Intent).

    Args:
        tier: Tier name

    Returns:
        Dictionary with insight_range, question_range, recommendation_range
    """
    config = get_tier_config(tier)
    if not config:
        config = TIER_CONFIGURATIONS["free"]

    return {
        "insight_range": config.insight_range,
        "question_range": config.question_range,
        "recommendation_range": config.recommendation_range,
    }


# Value messaging for each tier
TIER_VALUE_PROPS = {
    "free": "Essential insights for individual developers",
    "basic": "Professional insights that save 40% of screening time",
    "professional": "Scale your hiring with Claude Haiku 4.5's 64K output capacity",
    "enterprise": "Enterprise confidence with Claude Sonnet 4's high intelligence",
    "scale_plus": "Latest Claude Sonnet 4.5 powers deepest insights, questions & recommendations",
}

# ROI messaging
ROI_MESSAGING = {
    "bad_hire_cost": 252195,  # Based on DevSkiller research
    "time_savings_percent": 50,  # 40-60% average
    "roi_multiplier": 8.4,  # One prevented bad hire = 8.4 years of Scale+
    "tagline": "Join companies saving 40-60% of engineering interview time while improving hire quality with evidence-based insights",
}
