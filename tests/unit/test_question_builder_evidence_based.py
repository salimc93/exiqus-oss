"""
Unit tests for evidence-based question builder.

Ensures questions are based on observations without arbitrary scoring.
"""

import pytest

from github_analyzer.core.evidence.question_builder_evidence_based import (
    EvidenceBasedQuestionBuilder,
    InterviewGuide,
    InterviewQuestion,
)


class TestEvidenceBasedQuestionBuilder:
    """Test evidence-based question generation."""

    @pytest.fixture
    def builder(self):
        """Create builder instance."""
        return EvidenceBasedQuestionBuilder()

    @pytest.fixture
    def comprehensive_observations(self):
        """Create comprehensive observation data."""
        return {
            "technical_patterns": [
                {
                    "type": "test_coverage_structure",
                    "finding": "Test files present in 30% of modules",
                    "insight": "Selective testing approach observed",
                },
                {
                    "type": "architecture",
                    "finding": "Modular architecture with service separation",
                    "insight": "Clear architectural boundaries",
                },
            ],
            "behavioral_analysis": {
                "work_style": "consistent_contributor",
                "collaboration_level": "moderate",
                "communication_quality": "clear",
                "work_life_balance": "healthy",
            },
            "collaboration_patterns": [
                {
                    "type": "collaboration",
                    "finding": "Works with 5 regular contributors",
                    "top_contributors": ["alice", "bob", "carol", "dave", "eve"],
                }
            ],
            "skill_evolution": {
                "skill_progression": "steady_growth",
                "recent_focus": "TypeScript and React",
                "activity_trend": "increasing",
            },
        }

    @pytest.fixture
    def minimal_observations(self):
        """Create minimal observation data."""
        return {
            "technical_patterns": [
                {
                    "type": "language",
                    "finding": "Single Python file",
                    "insight": "Minimal codebase",
                }
            ],
            "behavioral_analysis": {
                "work_style": "unknown",
                "work_life_balance": "unknown",
            },
        }

    @pytest.fixture
    def concerning_observations(self):
        """Create observations with concerning patterns."""
        return {
            "technical_patterns": [
                {
                    "type": "test_coverage_structure",
                    "finding": "No test files found",
                    "insight": "Testing practices not visible",
                }
            ],
            "behavioral_analysis": {
                "work_style": "burst_contributor",
                "work_life_balance": "concerning",
                "behavioral_insights": [
                    {
                        "type": "work_life_concern",
                        "finding": "Frequent late night and weekend commits",
                    }
                ],
            },
        }

    def test_no_scoring_in_questions(self, builder, comprehensive_observations):
        """Ensure questions contain no scoring or arbitrary metrics."""
        guide = builder.generate_questions(
            comprehensive_observations, context="startup"
        )

        # Check questions don't have scores
        for question in guide.questions:
            assert not hasattr(question, "score")
            assert not hasattr(question, "difficulty")
            assert not hasattr(question, "rating")

            # Check no scoring language in content
            all_text = (
                question.question
                + question.context_notes
                + " ".join(question.exploration_areas)
            )
            assert "score" not in all_text.lower()
            assert "excellent" not in all_text.lower()
            assert "poor" not in all_text.lower()
            assert "rating" not in all_text.lower()

    def test_observation_based_questions(self, builder, comprehensive_observations):
        """Test that questions are based on actual observations."""
        guide = builder.generate_questions(
            comprehensive_observations, context="enterprise"
        )

        # Each question should reference an observation
        for question in guide.questions:
            assert question.observation_basis
            assert len(question.observation_basis) > 0

            # Should have exploration areas
            assert len(question.exploration_areas) > 0

            # Should have context notes
            assert question.context_notes
            assert "enterprise" in question.context_notes.lower()

    def test_exploration_not_judgment(self, builder, comprehensive_observations):
        """Test that questions explore rather than judge."""
        guide = builder.generate_questions(
            comprehensive_observations, context="startup"
        )

        for question in guide.questions:
            # Check exploration guidance doesn't judge
            for guidance in question.exploration_guidance:
                assert "score" not in guidance.lower()
                assert "evaluate" not in guidance.lower()
                assert "judge" not in guidance.lower()

                # Should use exploratory language
                exploratory_terms = ["explore", "understand", "discuss", "listen for"]
                assert any(term in guidance.lower() for term in exploratory_terms)

    def test_understanding_indicators(self, builder, comprehensive_observations):
        """Test understanding indicators are descriptive, not evaluative."""
        guide = builder.generate_questions(comprehensive_observations, context="agency")

        for question in guide.questions:
            if question.understanding_indicators:
                for key, value in question.understanding_indicators.items():
                    # Should describe what to look for
                    assert len(value) > 0

                    # Not evaluative terms
                    assert "excellent" not in value.lower()
                    assert "poor" not in value.lower()
                    assert "good" not in value.lower()
                    assert "bad" not in value.lower()

    def test_concerning_patterns_handled_constructively(
        self, builder, concerning_observations
    ):
        """Test that concerning patterns are addressed constructively."""
        guide = builder.generate_questions(concerning_observations, context="startup")

        # Should have questions about concerning patterns
        work_pattern_questions = [
            q
            for q in guide.questions
            if "work" in q.question.lower() or "commit" in q.question.lower()
        ]
        assert len(work_pattern_questions) > 0

        # Questions should be exploratory, not accusatory
        for question in work_pattern_questions:
            assert "?" in question.question  # Should be a question
            # Should explore context
            assert any(
                area
                for area in question.exploration_areas
                if "preference" in area.lower() or "sustainability" in area.lower()
            )

    def test_minimal_data_handling(self, builder, minimal_observations):
        """Test handling of minimal data."""
        guide = builder.generate_questions(minimal_observations, context="enterprise")

        # Should still generate questions
        assert len(guide.questions) > 0

        # Should acknowledge limitations
        assert len(guide.data_limitations) > 0
        assert any(
            "insufficient" in lim.lower() or "cannot assess" in lim.lower()
            for lim in guide.data_limitations
        )

        # Should focus on fundamentals
        fundamental_questions = [
            q
            for q in guide.questions
            if "technical challenge" in q.question.lower()
            or "stakeholder" in q.question.lower()
        ]
        assert len(fundamental_questions) > 0

    def test_context_specific_questions(self, builder, comprehensive_observations):
        """Test that questions are tailored to context."""
        contexts = ["startup", "enterprise", "agency", "open_source"]
        guides = {}

        for context in contexts:
            guides[context] = builder.generate_questions(
                comprehensive_observations, context=context
            )

        # Each context should have specific considerations
        for context, guide in guides.items():
            assert guide.context_considerations is not None
            assert len(guide.context_considerations) > 0

            # Should have appropriate keys for the context
            assert "environment" in guide.context_considerations
            assert "key_traits" in guide.context_considerations

            # Questions should reference context
            context_specific = [
                q for q in guide.questions if context in q.context_notes.lower()
            ]
            assert len(context_specific) > 0

    def test_tier_based_question_limits(self, builder, comprehensive_observations):
        """Test that question counts respect tier limits."""
        tier_limits = {"free": 3, "basic": 7, "professional": 10, "enterprise": 15}

        for tier, expected_max in tier_limits.items():
            guide = builder.generate_questions(
                comprehensive_observations, context="startup", tier=tier
            )

            assert len(guide.questions) <= expected_max

            # Free tier should have exactly 3
            if tier == "free":
                assert len(guide.questions) == 3

    def test_key_observations_extraction(self, builder, comprehensive_observations):
        """Test extraction of key observations."""
        guide = builder.generate_questions(
            comprehensive_observations, context="startup"
        )

        assert len(guide.key_observations) > 0
        assert len(guide.key_observations) <= 5

        # Should be actual observations
        for obs in guide.key_observations:
            assert len(obs) > 0
            # Should be factual
            assert any(
                pattern in obs.lower()
                for pattern in ["observed", "present", "found", "shows", "suggests"]
            )

    def test_exploration_priorities(self, builder, comprehensive_observations):
        """Test generation of exploration priorities."""
        guide = builder.generate_questions(
            comprehensive_observations, context="enterprise"
        )

        assert len(guide.exploration_priorities) > 0

        # Should always include fundamentals
        fundamental_priorities = [
            "Problem-solving approach and methodology",
            "Team collaboration and communication style",
            "Technical decision-making process",
        ]

        for fundamental in fundamental_priorities:
            assert fundamental in guide.exploration_priorities

        # Should include context-specific priorities
        assert any("process" in p.lower() for p in guide.exploration_priorities)
        assert any("documentation" in p.lower() for p in guide.exploration_priorities)

    def test_interview_flow_generation(self, builder, comprehensive_observations):
        """Test interview flow suggestions."""
        guide = builder.generate_questions(
            comprehensive_observations, context="startup"
        )

        assert len(guide.interview_flow) > 0

        # Should start with rapport
        assert "introduction" in guide.interview_flow[0].lower()

        # Should end with candidate questions
        assert "candidate questions" in guide.interview_flow[-1].lower()

        # Should be numbered
        for step in guide.interview_flow:
            # Check that step has a number followed by a period
            assert any(f"{num}." in step for num in range(1, 10))

    def test_no_arbitrary_thresholds(self, builder):
        """Test that no arbitrary thresholds are used."""
        # Create observations with specific numeric values
        observations = {
            "technical_patterns": [
                {
                    "type": "test_coverage_structure",
                    "finding": "Test files in 15% of modules",
                    "ratio": 0.15,  # This should not trigger arbitrary thresholds
                }
            ],
            "behavioral_analysis": {
                "work_style": "consistent_contributor",
                "leadership_potential": 0.7,  # This should be ignored
            },
            "skill_evolution": {
                "growth_rate": 0.3,  # This should be ignored
                "skill_progression": "steady_growth",
            },
        }

        guide = builder.generate_questions(observations)

        # Questions should not reference specific thresholds
        for question in guide.questions:
            all_text = str(question.__dict__)
            # Should not contain judgment based on thresholds
            assert "low test coverage" not in all_text.lower()
            assert "high test coverage" not in all_text.lower()
            assert "good coverage" not in all_text.lower()
            assert "poor coverage" not in all_text.lower()

            # Should describe what was observed
            if "test" in question.question.lower():
                assert "15%" in question.question or "noticed" in question.question

    def test_question_categories(self, builder, comprehensive_observations):
        """Test that questions cover various categories."""
        guide = builder.generate_questions(
            comprehensive_observations, context="startup", tier="professional"
        )

        categories = [q.category for q in guide.questions]

        # Should have diverse categories
        assert len(set(categories)) >= 3

        # Valid categories
        valid_categories = [
            "technical",
            "behavioral",
            "collaboration",
            "quality",
            "growth",
        ]
        for cat in categories:
            assert cat in valid_categories


class TestInterviewQuestion:
    """Test the InterviewQuestion data structure."""

    def test_question_creation(self):
        """Test creating a question."""
        question = InterviewQuestion(
            category="technical",
            question="How do you approach system design?",
            observation_basis="Modular architecture observed",
            exploration_areas=["Design philosophy", "Trade-off considerations"],
            context_notes="Important for startup scalability",
            exploration_guidance=["Explore their thought process"],
            understanding_indicators={
                "depth": "Can explain design choices with context",
                "experience": "References past projects",
            },
        )

        assert question.category == "technical"
        assert "system design" in question.question
        assert len(question.exploration_areas) == 2
        assert "startup" in question.context_notes
        assert len(question.exploration_guidance) == 1
        assert "depth" in question.understanding_indicators


class TestInterviewGuide:
    """Test the InterviewGuide structure."""

    def test_guide_creation(self):
        """Test creating an interview guide."""
        questions = [
            InterviewQuestion(
                category="technical",
                question="Tell me about your testing approach",
                observation_basis="Tests found in some modules",
                exploration_areas=["Testing philosophy"],
                context_notes="Quality focus for enterprise",
            )
        ]

        guide = InterviewGuide(
            questions=questions,
            key_observations=["Selective testing approach"],
            exploration_priorities=["Testing philosophy", "Quality practices"],
            context_considerations={"environment": "Enterprise"},
            data_limitations=["Cannot assess pair programming"],
            interview_flow=["1. Start with rapport", "2. Explore technical skills"],
        )

        assert len(guide.questions) == 1
        assert len(guide.key_observations) == 1
        assert len(guide.exploration_priorities) == 2
        assert "environment" in guide.context_considerations
        assert len(guide.data_limitations) == 1
        assert len(guide.interview_flow) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
