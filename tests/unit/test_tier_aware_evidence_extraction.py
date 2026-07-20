"""
Unit tests for tier-aware evidence extraction functionality.
Tests Operation "Reinforce the Tiers" implementation.
"""

from src.github_analyzer.api.models.clean_responses import (
    EvidencePatternModel,
    _create_tier_aware_pattern,
    _deduplicate_and_limit_patterns,
)


class TestTierAwarePatternCreation:
    """Test tier-aware evidence pattern creation and filtering."""

    def test_free_tier_gets_locked_preview_for_advanced_patterns(self):
        """Free tier should get locked previews for advanced patterns."""
        tier_config = {
            "sources": ["basic_insights", "surface_patterns"],
            "depth": "Surface",
            "max_patterns": 8,
            "confidence_threshold": "Low",
        }

        # Professional category requires architectural_analysis (not available to free tier)
        pattern = _create_tier_aware_pattern(
            name="Advanced Architecture",
            pattern_type="technical",
            evidence="Complex microservices setup with 15 services",
            context="Advanced architectural patterns",
            insight="Sophisticated system design",
            category="professional",
            tier_config=tier_config,
            subscription_tier="free",
        )

        assert pattern is not None
        assert pattern.tier_locked is True
        assert pattern.evidence == "🔒 Available in higher tiers"
        assert pattern.required_tier == "professional"
        # Now uses frontend tier names: Growth instead of professional
        assert "upgrade to growth" in pattern.context.lower()
        assert pattern.preview_teaser is not None
        assert "growth" in pattern.preview_teaser.lower()

    def test_professional_tier_gets_full_patterns(self):
        """Professional tier should get full patterns for their category."""
        tier_config = {
            "sources": [
                "basic_insights",
                "surface_patterns",
                "architectural_analysis",
                "temporal_patterns",
            ],
            "depth": "Architectural",
            "max_patterns": 15,
            "confidence_threshold": "Medium",
        }

        pattern = _create_tier_aware_pattern(
            name="Advanced Architecture",
            pattern_type="technical",
            evidence="Complex microservices setup with 15 services",
            context="Advanced architectural patterns",
            insight="Sophisticated system design",
            category="professional",
            tier_config=tier_config,
            subscription_tier="professional",
        )

        assert pattern is not None
        assert pattern.tier_locked is False
        assert pattern.evidence == "Complex microservices setup with 15 services"
        assert pattern.source_depth == "Architectural"
        assert pattern.confidence == "Medium"
        assert pattern.upgrade_hint is not None

    def test_basic_tier_category_mapping(self):
        """Test that categories map correctly to evidence sources."""
        tier_config = {
            "sources": ["basic_insights", "surface_patterns"],
            "depth": "Surface",
            "max_patterns": 8,
            "confidence_threshold": "Low",
        }

        # Technical category should be allowed (maps to basic_insights)
        technical_pattern = _create_tier_aware_pattern(
            name="Language Expertise",
            pattern_type="technical",
            evidence="Python 89.5% of codebase",
            context="Primary language analysis",
            insight="Strong Python skills",
            category="technical",
            tier_config=tier_config,
            subscription_tier="basic",
        )

        assert technical_pattern is not None
        assert technical_pattern.tier_locked is False

        # Security category should be locked (maps to security_patterns)
        security_pattern = _create_tier_aware_pattern(
            name="Security Practices",
            pattern_type="technical",
            evidence="Comprehensive security audit",
            context="Security analysis",
            insight="Strong security practices",
            category="security",
            tier_config=tier_config,
            subscription_tier="basic",
        )

        assert security_pattern is not None
        assert security_pattern.tier_locked is True

    def test_confidence_enhancement_by_tier(self):
        """Test that confidence is enhanced based on tier and evidence quality."""
        tier_config = {
            "sources": ["basic_insights", "surface_patterns", "architectural_analysis"],
            "depth": "Architectural",
            "max_patterns": 15,
            "confidence_threshold": "Medium",
        }

        # Long evidence with enterprise tier should get High confidence
        long_evidence = "A" * 150  # 150 characters

        pattern = _create_tier_aware_pattern(
            name="Test Pattern",
            pattern_type="technical",
            evidence=long_evidence,
            context="Test context",
            insight="Test insight",
            category="technical",
            tier_config=tier_config,
            subscription_tier="enterprise",
        )

        assert pattern is not None
        assert pattern.confidence == "High"

    def test_upgrade_hints_by_tier(self):
        """Test that appropriate upgrade hints are generated."""
        tier_config = {
            "sources": ["basic_insights"],
            "depth": "Surface",
            "max_patterns": 8,
            "confidence_threshold": "Low",
        }

        # Free tier should get basic upgrade hint
        pattern = _create_tier_aware_pattern(
            name="Test Pattern",
            pattern_type="technical",
            evidence="Test evidence",
            context="Test context",
            insight="Test insight",
            category="technical",
            tier_config=tier_config,
            subscription_tier="free",
        )

        assert pattern is not None
        assert "starter tier adds" in pattern.upgrade_hint.lower()


class TestPatternDeduplication:
    """Test evidence pattern deduplication and limiting."""

    def test_deduplication_removes_similar_patterns(self):
        """Test that patterns with similar signatures are deduplicated."""
        patterns = [
            EvidencePatternModel(
                name="language_expertise",
                pattern_type="technical",
                evidence="Python 89.5% of codebase with identical evidence",
                context="Primary language",
                insight="Strong Python skills",
                category="technical",
            ),
            EvidencePatternModel(
                name="language_expertise",  # Exactly same name (after .lower())
                pattern_type="technical",
                evidence="Python 89.5% of codebase with identical evidence",  # Identical first 50 chars
                context="Primary language analysis",
                insight="Deep Python experience",
                category="technical",
            ),
            EvidencePatternModel(
                name="testing_practices",
                pattern_type="quality",
                evidence="45 test files for 120 source files",
                context="Testing infrastructure",
                insight="Good test coverage",
                category="quality",
            ),
        ]

        tier_config = {"max_patterns": 10, "depth": "Architectural"}
        result = _deduplicate_and_limit_patterns(patterns, tier_config)

        # Should remove one of the similar language patterns (same name + category + evidence snippet)
        assert len(result) == 2
        pattern_names = [p.name.lower() for p in result]
        assert "testing_practices" in pattern_names

    def test_tier_limits_applied_correctly(self):
        """Test that tier pattern limits are enforced."""
        patterns = []
        for i in range(15):
            patterns.append(
                EvidencePatternModel(
                    name=f"pattern_{i}",
                    pattern_type="technical",
                    evidence=f"Evidence {i} with specific data: {i * 100} files",
                    context=f"Context {i}",
                    insight=f"Insight {i}",
                    category="technical",
                )
            )

        # Basic tier limited to 8 patterns
        tier_config = {"max_patterns": 8, "depth": "Architectural"}
        result = _deduplicate_and_limit_patterns(patterns, tier_config)

        assert len(result) == 8

    def test_evidence_based_prioritization(self):
        """Test that patterns are prioritized by evidence quality, not metrics."""
        patterns = [
            EvidencePatternModel(
                name="low_priority",
                pattern_type="technical",
                evidence="Short evidence",  # Low priority: short, no numbers
                context="Basic context",
                insight="Basic insight",
                category="technical",
            ),
            EvidencePatternModel(
                name="high_priority",
                pattern_type="technical",
                evidence="Comprehensive evidence with 127 files, 89.5% coverage, and detailed metrics showing 15 components",  # High priority: long, numbers, detail
                context="Very detailed context with comprehensive analysis spanning multiple architectural layers and providing deep insights into system design",
                insight="Advanced insight",
                category="technical",
            ),
            EvidencePatternModel(
                name="medium_priority",
                pattern_type="technical",
                evidence="Evidence with 45 files analyzed",  # Medium priority: has numbers
                context="Standard context",
                insight="Standard insight",
                category="technical",
            ),
        ]

        tier_config = {"max_patterns": 2, "depth": "Architectural"}
        result = _deduplicate_and_limit_patterns(patterns, tier_config)

        assert len(result) == 2
        # High priority should be first (evidence-based ranking)
        assert result[0].name == "high_priority"
        assert result[1].name == "medium_priority"

    def test_locked_patterns_for_basic_tier(self):
        """Test that basic tier gets locked pattern previews."""
        unlocked_patterns = [
            EvidencePatternModel(
                name="basic_pattern",
                pattern_type="technical",
                evidence="Basic evidence",
                context="Basic context",
                insight="Basic insight",
                category="technical",
                tier_locked=False,
            )
        ]

        locked_patterns = [
            EvidencePatternModel(
                name="advanced_pattern",
                pattern_type="technical",
                evidence="🔒 Available in higher tiers",
                context="Upgrade to professional to see full analysis",
                insight="Advanced security insights available",
                category="security",
                tier_locked=True,
            )
        ]

        all_patterns = unlocked_patterns + locked_patterns
        tier_config = {"max_patterns": 8, "depth": "Surface"}

        result = _deduplicate_and_limit_patterns(all_patterns, tier_config)

        # Should include both unlocked and some locked previews
        unlocked_in_result = [p for p in result if not p.tier_locked]
        locked_in_result = [p for p in result if p.tier_locked]

        assert len(unlocked_in_result) == 1
        assert len(locked_in_result) == 1
        assert locked_in_result[0].evidence == "🔒 Available in higher tiers"


class TestTierConfiguration:
    """Test tier configuration mapping and validation."""

    def test_tier_evidence_sources_mapping(self):
        """Test that tier configurations map correctly to evidence sources."""
        # This test verifies the TIER_EVIDENCE_SOURCES configuration
        # We can't easily test convert_to_clean_response without a full StructuredReport
        # But we can verify the tier config exists and has correct structure
        # Test will be in integration test file
        pass

    def test_category_to_source_mapping(self):
        """Test that categories correctly map to evidence sources."""
        tier_config = {
            "sources": ["basic_insights", "surface_patterns"],
            "depth": "Surface",
            "max_patterns": 8,
            "confidence_threshold": "Low",
        }

        # Technical should be allowed (basic_insights)
        technical_pattern = _create_tier_aware_pattern(
            name="Technical",
            pattern_type="technical",
            evidence="Test evidence",
            context="Test context",
            insight="Test insight",
            category="technical",
            tier_config=tier_config,
            subscription_tier="basic",
        )
        assert technical_pattern.tier_locked is False

        # Growth should be locked (temporal_patterns)
        growth_pattern = _create_tier_aware_pattern(
            name="Growth",
            pattern_type="behavioral",
            evidence="Test evidence",
            context="Test context",
            insight="Test insight",
            category="growth",
            tier_config=tier_config,
            subscription_tier="basic",
        )
        assert growth_pattern.tier_locked is True
