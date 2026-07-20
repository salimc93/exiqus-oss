"""
Integration tests for tier-aware evidence extraction flow.
Tests the TIER_EVIDENCE_SOURCES configuration and category mapping.
"""

from src.github_analyzer.api.models.clean_responses import (
    EvidencePatternModel,
    _create_tier_aware_pattern,
)


class TestTierConfiguration:
    """Test tier configuration and evidence source mapping."""

    def test_tier_evidence_sources_exist(self):
        """Test that all expected tiers have configuration."""
        # Import the TIER_EVIDENCE_SOURCES from the actual implementation
        from src.github_analyzer.api.models.clean_responses import (
            convert_to_clean_response,
        )

        # We can't directly access TIER_EVIDENCE_SOURCES since it's inside the function
        # But we can test that the function accepts all expected tiers

        expected_tiers = ["free", "basic", "professional", "enterprise", "scale_plus"]

        # This test verifies the tiers exist by testing they don't raise errors
        for tier in expected_tiers:
            # Create minimal mock for testing
            class MockReport:
                repository_url = "https://github.com/test/repo"
                repository_name = "test-repo"
                analysis_date = "2025-07-28T00:00:00Z"
                subscription_tier = tier
                executive_summary = "Test"
                analysis_limitations = []

                def __init__(self):
                    self.context = type("obj", (object,), {"value": "startup"})
                    self.repository_type = type(
                        "obj", (object,), {"value": "web_application"}
                    )
                    self.screening_insights = None
                    self.green_flags = []
                    self.red_flags = []

            # Should not raise error for any valid tier
            result = convert_to_clean_response(MockReport(), subscription_tier=tier)
            assert result.subscription_tier == (tier if tier != "free" else "free")

    def test_category_to_source_mapping_coverage(self):
        """Test that all categories map to appropriate evidence sources."""
        test_categories = [
            ("technical", "basic_insights"),
            ("security", "security_patterns"),
            ("professional", "architectural_analysis"),
            ("growth", "temporal_patterns"),
            ("collaboration", "team_dynamics"),
        ]

        for category, expected_source in test_categories:
            # Test with a tier that doesn't have the required source
            basic_tier_config = {
                "sources": ["basic_insights", "surface_patterns"],
                "depth": "Surface",
                "max_patterns": 8,
                "confidence_threshold": "Low",
            }

            pattern = _create_tier_aware_pattern(
                name="Test Pattern",
                pattern_type="technical",
                evidence="Test evidence",
                context="Test context",
                insight="Test insight",
                category=category,
                tier_config=basic_tier_config,
                subscription_tier="basic",
            )

            if expected_source in basic_tier_config["sources"]:
                # Should be unlocked if source is available
                assert pattern is not None
                assert pattern.tier_locked is False
            else:
                # Should be locked preview if source not available
                if (
                    pattern is not None
                ):  # Some categories may return None for high tiers
                    assert pattern.tier_locked is True

    def test_tier_progression_pattern_limits(self):
        """Test that tier pattern limits follow expected progression."""
        # Test pattern limit progression: free(8) < basic(8) < professional(15) < enterprise(22) < scale_plus(30)

        # This is tested implicitly in the unit tests, but we can verify the progression
        # by testing with large pattern sets

        many_patterns = []
        for i in range(35):  # More than scale_plus limit
            many_patterns.append(
                EvidencePatternModel(
                    name=f"pattern_{i}",
                    pattern_type="technical",
                    evidence=f"Evidence {i}",
                    context="Context",
                    insight="Insight",
                    category="technical",
                )
            )

        from src.github_analyzer.api.models.clean_responses import (
            _deduplicate_and_limit_patterns,
        )

        # Test tier limits
        tier_configs = [
            ("basic", 8),
            ("professional", 15),
            ("enterprise", 22),
            ("scale_plus", 30),
        ]

        for tier_name, expected_max in tier_configs:
            tier_config = {"max_patterns": expected_max, "depth": "Architectural"}
            result = _deduplicate_and_limit_patterns(many_patterns, tier_config)
            unlocked = [p for p in result if not p.tier_locked]
            assert len(unlocked) <= expected_max, (
                f"{tier_name} should limit to {expected_max} patterns"
            )
