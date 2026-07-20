"""
Unit tests for tier configuration module.

Tests the centralized tier configuration system that manages
all subscription tier settings including pricing, models, and limits.
"""

import pytest

from github_analyzer.core.tier_config import (
    get_configured_model,
    get_model_for_tier,
    get_tier_config,
    get_token_limit,
    scale_plus_token_allocator,
)
from github_analyzer.utils.config import DEFAULT_ANTHROPIC_MODEL


class TestTierConfiguration:
    """Test tier configuration retrieval and structure."""

    def test_get_tier_config_valid_tiers(self) -> None:
        """Test retrieving configuration for valid tiers."""
        # Test all valid tiers
        for tier in ["free", "basic", "professional", "enterprise", "scale_plus"]:
            config = get_tier_config(tier)
            assert config is not None
            assert config.monthly_price >= 0
            assert config.analyses_per_month > 0
            assert config.main_generation_tokens > 0
            assert config.unified_approach_tokens > 0

    def test_get_tier_config_case_insensitive(self) -> None:
        """Test that tier lookup is case-insensitive."""
        config_lower = get_tier_config("enterprise")
        config_upper = get_tier_config("ENTERPRISE")
        config_mixed = get_tier_config("EnTeRpRiSe")

        assert config_lower == config_upper == config_mixed

    def test_get_tier_config_invalid_tier(self) -> None:
        """Test retrieving configuration for invalid tier."""
        config = get_tier_config("invalid_tier")
        assert config is None

    def test_tier_pricing_progression(self) -> None:
        """Test that pricing increases with tier level."""
        free = get_tier_config("free")
        basic = get_tier_config("basic")
        professional = get_tier_config("professional")
        enterprise = get_tier_config("enterprise")
        scale_plus = get_tier_config("scale_plus")

        assert free is not None and basic is not None
        assert professional is not None and enterprise is not None
        assert scale_plus is not None

        assert free.monthly_price == 0
        assert basic.monthly_price < professional.monthly_price
        assert professional.monthly_price < enterprise.monthly_price
        assert enterprise.monthly_price < scale_plus.monthly_price

    def test_tier_analyses_progression(self) -> None:
        """Test that monthly analyses make sense by tier level."""
        free = get_tier_config("free")
        basic = get_tier_config("basic")
        professional = get_tier_config("professional")
        enterprise = get_tier_config("enterprise")
        scale_plus = get_tier_config("scale_plus")

        assert free is not None and basic is not None
        assert professional is not None and enterprise is not None
        assert scale_plus is not None

        # Free tier: 10 total analyses (3 AI-powered, 7 template-based)
        # Basic tier: 10 full AI-powered portfolio analyses
        assert free.analyses_per_month == 10
        assert basic.analyses_per_month == 10

        # Free has limited AI analyses (single repo only, 3 AI-powered)
        assert free.features["ai_analyses"] == 3
        assert free.features["portfolio_access"] is False

        # Basic has full AI analyses (portfolio access, 50 single repo deep dives, 10 candidate assessments)
        assert basic.features["ai_analyses"] == 50
        assert basic.features["candidate_assessments"] == 10
        assert basic.features["portfolio_access"] is True

        # Paid tiers increase from there
        assert professional.analyses_per_month == 50
        assert enterprise.analyses_per_month == 200
        assert scale_plus.analyses_per_month == 500

        # Verify progression for paid tiers
        assert professional.analyses_per_month > basic.analyses_per_month
        assert enterprise.analyses_per_month > professional.analyses_per_month
        assert scale_plus.analyses_per_month > enterprise.analyses_per_month


class TestModelConfiguration:
    """Model selection resolves from configuration, not from the tier."""

    def test_all_tiers_resolve_to_the_configured_model(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Every tier and model type uses ANTHROPIC_MODEL by default.

        Tiers ship with no model overrides, so a deployment picks one model and
        it applies everywhere. This is the behaviour that replaced the old
        per-tier model pinning from the SaaS era.
        """
        monkeypatch.setenv("ANTHROPIC_MODEL", "claude-test-model")

        for tier in ["free", "basic", "professional", "enterprise", "scale_plus"]:
            for model_type in ["main", "metrics", "questions"]:
                assert get_model_for_tier(tier, model_type) == "claude-test-model"

    def test_unset_env_falls_back_to_the_documented_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With no ANTHROPIC_MODEL set, the shared default applies."""
        monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)

        assert get_configured_model() == DEFAULT_ANTHROPIC_MODEL
        assert get_model_for_tier("professional") == DEFAULT_ANTHROPIC_MODEL

    def test_unknown_tier_still_resolves(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """An unrecognised tier gets the configured model, not an error."""
        monkeypatch.setenv("ANTHROPIC_MODEL", "claude-test-model")

        assert get_model_for_tier("no-such-tier") == "claude-test-model"

    def test_explicit_tier_override_wins_over_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A tier that sets a model explicitly keeps it.

        No shipped tier does this, but the capability is retained so an operator
        can put one call site on a cheaper model.
        """
        monkeypatch.setenv("ANTHROPIC_MODEL", "claude-test-model")
        config = get_tier_config("free")
        assert config is not None
        monkeypatch.setattr(config, "questions_model", "claude-cheaper-model")

        assert get_model_for_tier("free", "questions") == "claude-cheaper-model"
        assert get_model_for_tier("free", "main") == "claude-test-model"


class TestTokenLimits:
    """Test token limit configuration."""

    def test_get_token_limit_main(self) -> None:
        """Test getting main generation token limits."""
        assert get_token_limit("free", "main") == 8000  # Haiku 3.5 max
        assert get_token_limit("basic", "main") == 16000  # Haiku 4.5 increased capacity
        assert (
            get_token_limit("professional", "main") == 16000
        )  # Haiku 4.5 increased capacity
        assert (
            get_token_limit("enterprise", "main") == 20000
        )  # Sonnet 4 increased capacity
        assert get_token_limit("scale_plus", "main") == 32000  # Sonnet 4 maximum depth

    def test_get_token_limit_unified(self) -> None:
        """Test getting unified approach token limits."""
        assert get_token_limit("free", "unified") == 8000  # Haiku 3.5 max
        assert get_token_limit("basic", "unified") == 16000  # Haiku 4.5 richer outputs
        assert (
            get_token_limit("professional", "unified") == 16000
        )  # Haiku 4.5 richer outputs
        assert (
            get_token_limit("enterprise", "unified") == 20000
        )  # Sonnet 4 comprehensive
        assert (
            get_token_limit("scale_plus", "unified") == 32000
        )  # Sonnet 4 comprehensive

    def test_get_token_limit_invalid_tier(self) -> None:
        """Test token limit fallback for invalid tier."""
        # Should fall back to free tier limits
        assert get_token_limit("invalid", "main") == 8000
        assert get_token_limit("invalid", "unified") == 8000


class TestScalePlusTokenAllocator:
    """Test smart token allocation for Scale+ tier."""

    def test_scale_plus_token_allocator_small_repo(self) -> None:
        """Test token allocation for small repositories."""
        # Repos under 50MB get 12,000 tokens
        assert scale_plus_token_allocator(10) == 12000
        assert scale_plus_token_allocator(25) == 12000
        assert scale_plus_token_allocator(49) == 12000

    def test_scale_plus_token_allocator_medium_repo(self) -> None:
        """Test token allocation for medium repositories."""
        # Repos 50-199MB get 20,000 tokens
        assert scale_plus_token_allocator(50) == 20000
        assert scale_plus_token_allocator(100) == 20000
        assert scale_plus_token_allocator(199) == 20000

    def test_scale_plus_token_allocator_large_repo(self) -> None:
        """Test token allocation for large repositories."""
        # Repos 200MB+ get 35,000 tokens
        assert scale_plus_token_allocator(200) == 35000
        assert scale_plus_token_allocator(500) == 35000
        assert scale_plus_token_allocator(1000) == 35000


class TestFeatureConfiguration:
    """Test feature flags and limits by tier."""

    def test_batch_analysis_limits(self) -> None:
        """Test batch analysis limits by tier."""
        free = get_tier_config("free")
        basic = get_tier_config("basic")
        professional = get_tier_config("professional")
        enterprise = get_tier_config("enterprise")
        scale_plus = get_tier_config("scale_plus")

        assert free is not None and basic is not None
        assert professional is not None and enterprise is not None
        assert scale_plus is not None

        # Free has no batch analysis
        assert "batch_analysis" not in free.features

        # Others have increasing limits
        assert basic.features.get("batch_analysis") == 2
        assert professional.features.get("batch_analysis") == 5
        assert enterprise.features.get("batch_analysis") == 10
        assert scale_plus.features.get("batch_analysis") == 15

    def test_export_formats_by_tier(self) -> None:
        """Test available export formats by tier."""
        free = get_tier_config("free")
        basic = get_tier_config("basic")
        enterprise = get_tier_config("enterprise")

        assert free is not None and basic is not None and enterprise is not None

        assert free.features.get("export_formats") == ["json"]
        assert basic.features.get("export_formats") == ["json", "html", "pdf"]
        assert enterprise.features.get("export_formats") == [
            "json",
            "html",
            "pdf",
            "markdown",
        ]

    def test_support_features(self) -> None:
        """Test support features by tier."""
        professional = get_tier_config("professional")
        enterprise = get_tier_config("enterprise")
        scale_plus = get_tier_config("scale_plus")

        assert professional is not None and enterprise is not None
        assert scale_plus is not None

        assert professional.features.get("priority_support") is True
        assert enterprise.features.get("sla_12_hours") is True
        assert scale_plus.features.get("sla_6_hours") is True
        assert scale_plus.features.get("dedicated_support") is True


class TestPricingUpdates:
    """Test that pricing updates are correctly applied."""

    def test_scale_tier_pricing(self) -> None:
        """Test Scale tier has updated pricing."""
        scale = get_tier_config("enterprise")  # Backend name for Scale
        assert scale is not None
        assert scale.monthly_price == 499
        assert scale.annual_price == 4990

    def test_scale_plus_tier_pricing(self) -> None:
        """Test Scale+ tier has updated pricing."""
        scale_plus = get_tier_config("scale_plus")
        assert scale_plus is not None
        assert scale_plus.monthly_price == 2500  # Was $1,997
        assert scale_plus.annual_price == 25000


class TestModelAssignments:
    """Tiers must not pin models; that is a deployment choice."""

    def test_no_tier_hardcodes_a_model(self) -> None:
        """Shipped tiers leave all three model fields unset.

        A hardcoded model here would silently override ANTHROPIC_MODEL and can
        rot into a retired model ID that returns 404.
        """
        for tier in ["free", "basic", "professional", "enterprise", "scale_plus"]:
            config = get_tier_config(tier)
            assert config is not None
            assert config.main_model is None, f"{tier} pins a main model"
            assert config.metrics_model is None, f"{tier} pins a metrics model"
            assert config.questions_model is None, f"{tier} pins a questions model"
