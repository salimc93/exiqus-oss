"""
Unit tests for evidence-based recommendation engine.

Ensures recommendations are based on observations without arbitrary metrics.
"""

import pytest

from github_analyzer.core.evidence.recommendation_engine_evidence_based import (
    AnalysisAssessment,
    EvidenceBasedRecommendation,
    EvidenceBasedRecommendationEngine,
)


class TestEvidenceBasedRecommendationEngine:
    """Test evidence-based recommendation generation."""

    @pytest.fixture
    def engine(self):
        """Create engine instance."""
        return EvidenceBasedRecommendationEngine()

    @pytest.fixture
    def comprehensive_evidence(self):
        """Create comprehensive evidence data."""
        return {
            "technical_patterns": [
                {
                    "type": "language_expertise",
                    "finding": "Primary expertise in Python (75% of code)",
                    "insight": "Strong Python focus",
                },
                {
                    "type": "test_coverage_structure",
                    "finding": "Test files present in 40% of modules",
                    "ratio": 0.4,
                },
                {
                    "type": "architecture",
                    "finding": "Modular architecture with clear separation",
                    "insight": "Well-structured codebase",
                },
            ],
            "behavioral_analysis": {
                "work_style": "consistent_contributor",
                "collaboration_level": "moderate",
                "communication_quality": "clear",
                "work_life_balance": "healthy",
                "behavioral_insights": [
                    {
                        "type": "collaboration",
                        "finding": "Regular interaction with 3 team members",
                    }
                ],
            },
            "behavioral_patterns": {
                "commit_frequency": {
                    "pattern": "Regular daily commits",
                    "analysis": "Consistent work pattern",
                },
                "work_timing": {
                    "pattern": "Primarily business hours",
                    "analysis": "Standard schedule",
                },
            },
            "skill_evolution": {
                "skill_progression": "steady_growth",
                "growth_rate": 0.15,
                "recent_focus": "API development",
                "activity_trend": "increasing",
            },
            "collaboration_patterns": [
                {
                    "type": "collaboration",
                    "top_contributors": ["user1", "user2", "user3", "user4"],
                }
            ],
            "security_issues": [],
        }

    @pytest.fixture
    def minimal_evidence(self):
        """Create minimal evidence data."""
        return {
            "technical_patterns": [],
            "behavioral_patterns": {},
            "skill_evolution": {},
            "collaboration_patterns": [],
            "security_issues": [],
        }

    @pytest.fixture
    def concerning_evidence(self):
        """Create evidence with concerning patterns."""
        return {
            "technical_patterns": [
                {
                    "type": "test_coverage_structure",
                    "finding": "No test files found",
                    "ratio": 0.0,
                }
            ],
            "behavioral_patterns": {
                "commit_frequency": {
                    "pattern": "Irregular bursts",
                    "analysis": "Inconsistent contribution",
                }
            },
            "behavioral_insights": [
                {
                    "type": "work_life_concern",
                    "finding": "90% of commits outside business hours",
                }
            ],
            "skill_evolution": {},
            "collaboration_patterns": [],
            "security_issues": [
                {"finding": "Hardcoded credentials in config.py", "severity": "high"}
            ],
        }

    def test_no_arbitrary_metrics(self, engine, comprehensive_evidence):
        """Ensure no arbitrary metrics in recommendations."""
        assessment = engine.generate_recommendations(
            comprehensive_evidence, context="startup"
        )

        # Check recommendations don't contain scores
        for rec in assessment["all_recommendations"]:
            assert "score" not in rec
            assert "confidence_score" not in rec

            # Check no scoring language
            all_text = rec["recommendation"] + rec["evidence"] + rec["action"]
            assert "score" not in all_text.lower()
            assert "excellent" not in all_text.lower()
            assert "poor" not in all_text.lower()
            assert "high quality" not in all_text.lower()
            assert "low quality" not in all_text.lower()

    def test_no_numerical_thresholds(self, engine, comprehensive_evidence):
        """Test that no numerical thresholds are used."""
        assessment = engine.generate_recommendations(
            comprehensive_evidence, context="enterprise"
        )

        # Check assessment doesn't contain numerical evaluations
        assert "hiring_score" not in assessment
        assert "team_fit_score" not in assessment

        # Check narrative assessments don't use threshold language
        all_text = assessment["summary"]
        if "growth_potential" in assessment:
            all_text += assessment["growth_potential"]["assessment"]

        # Should not contain percentage-based judgments
        assert "70%" not in all_text
        assert "above average" not in all_text.lower()
        assert "below average" not in all_text.lower()
        assert "good coverage" not in all_text.lower()
        assert "poor coverage" not in all_text.lower()

    def test_evidence_based_recommendations(self, engine, comprehensive_evidence):
        """Test that recommendations are based on actual evidence."""
        assessment = engine.generate_recommendations(
            comprehensive_evidence, context="startup"
        )

        # Each recommendation should have evidence
        for rec in assessment["all_recommendations"]:
            assert rec["recommendation"]  # What was observed
            assert rec["evidence"]  # Specific evidence
            assert rec["action"]  # What it might mean

            # Should reference actual findings
            evidence_found = False
            for evidence_item in comprehensive_evidence["technical_patterns"]:
                if evidence_item["finding"] in rec["evidence"]:
                    evidence_found = True
                    break

            # At least some recommendations should directly reference evidence
            if rec["category"] == "technical":
                assert evidence_found or "observed" in rec["recommendation"].lower()

    def test_recommendation_types(self, engine, comprehensive_evidence):
        """Test that recommendations use appropriate types."""
        assessment = engine.generate_recommendations(
            comprehensive_evidence, context="agency"
        )

        # Check recommendation types
        rec_types = {rec["type"] for rec in assessment["all_recommendations"]}
        valid_types = {"strength", "opportunity", "consideration", "inquiry"}

        assert rec_types.issubset(valid_types)

        # Should have different types based on evidence
        if len(assessment["all_recommendations"]) > 3:
            assert len(rec_types) > 1  # Should have variety

    def test_exploration_focus(self, engine, comprehensive_evidence):
        """Test that recommendations focus on exploration, not judgment."""
        assessment = engine.generate_recommendations(
            comprehensive_evidence, context="startup"
        )

        # Each recommendation should suggest exploration
        for rec in assessment["all_recommendations"]:
            # Should have actionable guidance
            assert rec["action"]

            # Should suggest what to validate/explore
            assert (
                "explore" in rec["action"].lower()
                or "discuss" in rec["action"].lower()
                or "validate" in rec["action"].lower()
                or "assess" in rec["action"].lower()
                or "understand" in rec["action"].lower()
            )

    def test_context_specific_observations(self, engine, comprehensive_evidence):
        """Test context-specific observations."""
        contexts = ["startup", "enterprise", "agency", "open_source"]

        assessments = {}
        for context in contexts:
            assessments[context] = engine.generate_recommendations(
                comprehensive_evidence, context=context
            )

        # Different contexts should have different observations
        startup_recs = assessments["startup"]["all_recommendations"]
        enterprise_recs = assessments["enterprise"]["all_recommendations"]

        # Context relevance should differ
        startup_relevance = [r["context_relevance"] for r in startup_recs]
        enterprise_relevance = [r["context_relevance"] for r in enterprise_recs]

        assert startup_relevance != enterprise_relevance

    def test_narrative_assessments(self, engine, comprehensive_evidence):
        """Test narrative assessments instead of scores."""
        assessment = engine.generate_recommendations(
            comprehensive_evidence, context="enterprise"
        )

        # Should have narrative summary
        assert isinstance(assessment["summary"], str)
        assert len(assessment["summary"]) > 50  # Meaningful summary

        # Should describe observations, not rate them
        assert (
            "observed" in assessment["summary"].lower()
            or "shows" in assessment["summary"].lower()
            or "indicates" in assessment["summary"].lower()
            or "suggests" in assessment["summary"].lower()
        )

        # Should not make absolute judgments
        assert "excellent candidate" not in assessment["summary"].lower()
        assert "poor fit" not in assessment["summary"].lower()
        assert "must hire" not in assessment["summary"].lower()
        assert "do not hire" not in assessment["summary"].lower()

    def test_concerning_patterns_handling(self, engine, concerning_evidence):
        """Test handling of concerning patterns without judgment."""
        assessment = engine.generate_recommendations(
            concerning_evidence, context="startup"
        )

        # Should identify patterns needing discussion
        concerning_recs = [
            r
            for r in assessment["all_recommendations"]
            if r["type"] in ["consideration", "inquiry"]
        ]

        assert len(concerning_recs) > 0

        # Should frame as areas to explore, not red flags
        for rec in concerning_recs:
            assert (
                "explore" in rec["action"].lower()
                or "discuss" in rec["action"].lower()
                or "understand" in rec["action"].lower()
            )

            # Should not use alarmist language
            assert "red flag" not in rec["recommendation"].lower()
            assert "warning" not in rec["recommendation"].lower()
            assert "avoid" not in rec["recommendation"].lower()

    def test_minimal_data_handling(self, engine, minimal_evidence):
        """Test handling of minimal data."""
        assessment = engine.generate_recommendations(
            minimal_evidence, context="startup"
        )

        # Should acknowledge limitations
        assert (
            "limited" in assessment["summary"].lower()
            or "minimal" in assessment["summary"].lower()
            or "insufficient" in assessment["summary"].lower()
        )

        # Should have fewer recommendations
        assert len(assessment["all_recommendations"]) <= 3

        # Should emphasize need for more data
        assert len(assessment["data_limitations"]) > 0

    def test_key_observations_extraction(self, engine, comprehensive_evidence):
        """Test extraction of key observations."""
        assessment = engine.generate_recommendations(
            comprehensive_evidence, context="enterprise"
        )

        # Should have key observations
        assert len(assessment["decision_factors"]) > 0
        assert len(assessment["decision_factors"]) <= 7  # Focused list

        # Observations should be specific
        for factor in assessment["decision_factors"]:
            assert isinstance(factor, str)
            assert len(factor) > 10  # Not just a word or two

    def test_tier_based_limits(self, engine, comprehensive_evidence):
        """Test tier-based recommendation limits."""
        tiers = ["free", "basic", "professional", "enterprise"]
        expected_limits = {"free": 3, "basic": 6, "professional": 10, "enterprise": 18}

        for tier in tiers:
            assessment = engine.generate_recommendations(
                comprehensive_evidence, context="startup", tier=tier
            )

            # Should respect tier limits
            assert len(assessment["all_recommendations"]) <= expected_limits[tier]

    def test_data_confidence_levels(self, engine, comprehensive_evidence):
        """Test data confidence in recommendations."""
        assessment = engine.generate_recommendations(
            comprehensive_evidence, context="startup"
        )

        # Evidence-based approach tracks data limitations instead of confidence scores
        assert "data_limitations" in assessment
        assert isinstance(assessment["data_limitations"], list)

    def test_no_hiring_decisions(self, engine, comprehensive_evidence):
        """Ensure engine doesn't make hiring decisions."""
        assessment = engine.generate_recommendations(
            comprehensive_evidence, context="enterprise"
        )

        # Check recommendations don't make decisions
        for rec in assessment["all_recommendations"]:
            assert "hire" not in rec["recommendation"].lower()
            assert "reject" not in rec["recommendation"].lower()
            assert "pass" not in rec["recommendation"].lower()

        # Summary should not contain hiring decision
        assert "should hire" not in assessment["summary"].lower()
        assert "should not hire" not in assessment["summary"].lower()
        assert "recommend hiring" not in assessment["summary"].lower()

        # Hiring recommendation should be informative, not decisive
        hiring_rec = assessment.get("hiring_recommendation", "")
        if hiring_rec:
            # Evidence-based approach doesn't make hiring decisions
            assert hiring_rec == "SEE_EVIDENCE_SUMMARY"

    def test_implications_not_judgments(self, engine, comprehensive_evidence):
        """Test that implications are exploratory, not judgmental."""
        assessment = engine.generate_recommendations(
            comprehensive_evidence, context="startup"
        )

        for rec in assessment["all_recommendations"]:
            implications = rec["action"]

            # Should use tentative language
            assert any(
                word in implications.lower()
                for word in [
                    "might",
                    "could",
                    "may",
                    "suggest",
                    "appear",
                    "seem",
                    "possible",
                    "explore",
                    "validate",
                ]
            )

            # Should not use absolute language
            assert not any(
                word in implications.lower()
                for word in [
                    "definitely",
                    "certainly",
                    "always",
                    "never",
                    "must be",
                    "proves",
                    "guarantees",
                ]
            )

    def test_areas_for_validation(self, engine, comprehensive_evidence):
        """Test identification of validation areas."""
        assessment = engine.generate_recommendations(
            comprehensive_evidence, context="enterprise"
        )

        # Should identify areas needing validation
        assert len(assessment["areas_to_probe"]) > 0

        # Areas should be specific and actionable
        for area in assessment["areas_to_probe"]:
            assert isinstance(area, dict)
            assert "recommendation" in area
            assert len(area["recommendation"]) > 20  # Meaningful description

    def test_recommendation_creation(self):
        """Test EvidenceBasedRecommendation creation."""
        rec = EvidenceBasedRecommendation(
            category="technical",
            recommendation_type="strength",
            title="Strong Python expertise",
            observation="Extensive use of advanced Python features",
            evidence=["Type hints in all modules", "Async/await patterns"],
            implications="May excel in Python-heavy environments",
            exploration_areas=["Discuss experience with Python at scale"],
            data_confidence="observed",
        )

        assert rec.category == "technical"
        assert rec.recommendation_type == "strength"
        assert len(rec.evidence) == 2
        assert len(rec.exploration_areas) == 1

    def test_assessment_creation(self):
        """Test AnalysisAssessment creation."""
        assessment = AnalysisAssessment(
            summary="Developer shows strong technical foundation",
            key_observations=["Python expertise", "Testing practices"],
            recommendations=[],
            areas_for_validation=["Team collaboration", "System design"],
            data_limitations=["Limited commit history"],
            context_fit_observations={"startup": ["Self-directed work"]},
            technical_readiness="Shows competence in core technologies",
            collaboration_indicators="Limited multi-contributor activity",
            growth_trajectory="Steady skill development observed",
            discussion_topics=[],
        )

        assert len(assessment.key_observations) == 2
        assert len(assessment.areas_for_validation) == 2
        assert assessment.technical_readiness
        assert assessment.collaboration_indicators
