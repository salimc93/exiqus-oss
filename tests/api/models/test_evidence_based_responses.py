"""
Tests for evidence-based response models.

Ensures response models properly handle evidence-based data without scores.
"""

from datetime import datetime, timezone

from github_analyzer.api.models.clean_responses import (
    CleanAnalysisResponse,
    EvidencePatternModel,
    InsightModel,
    QuestionModel,
    RecommendationModel,
    convert_to_clean_response,
)


class TestEvidenceBasedModels:
    """Test evidence-based response model structure and validation."""

    def test_evidence_pattern_model(self):
        """Test EvidencePatternModel has no scores."""
        pattern = EvidencePatternModel(
            name="TypeScript Expertise",
            pattern_type="technical",
            evidence="89.5% TypeScript across 343 files",
            context="Modern web development",
            insight="Deep TypeScript experience",
            category="technical",
        )

        # Verify fields
        assert pattern.name == "TypeScript Expertise"
        assert pattern.pattern_type == "technical"
        assert pattern.evidence == "89.5% TypeScript across 343 files"

        # Verify no score fields
        assert not hasattr(pattern, "score")
        assert not hasattr(pattern, "percentage")

    def test_clean_analysis_response_no_scores(self):
        """Test CleanAnalysisResponse has evidence-based fields."""
        response = CleanAnalysisResponse(
            repository_url="https://github.com/user/repo",
            repository_name="repo",
            analysis_date="2025-07-28T00:00:00Z",
            subscription_tier="professional",
            context="startup",
            executive_summary="Evidence-based analysis shows strong patterns.",
            repository_type="portfolio_project",
            confidence_explanation="High confidence based on code analysis",
            insights=[],
            questions=[],
            recommendations=[],
            evidence_patterns=[
                EvidencePatternModel(
                    name="Testing Practices",
                    pattern_type="quality",
                    evidence="40 test files detected",
                    context="Quality assurance",
                    insight="Testing discipline present",
                    category="technical",
                )
            ],
            limitations=["Cannot assess soft skills"],
            data_limitations=["No access to private repos"],
            green_flags=["Testing present"],
            red_flags=[],
        )

        # Verify evidence-based fields exist
        assert (
            response.confidence_explanation == "High confidence based on code analysis"
        )
        assert response.evidence_patterns_count == 1
        assert response.data_limitations == ["No access to private repos"]

        # Verify no score fields
        assert not hasattr(response, "confidence_score")
        assert not hasattr(response, "data_completeness")
        assert not hasattr(response, "metrics")

    def test_convert_to_clean_response_evidence_based(self):
        """Test conversion properly extracts evidence patterns."""

        # Mock a structured report
        class MockReport:
            repository_url = "https://github.com/user/repo"
            repository_name = "repo"
            analysis_date = datetime.now(timezone.utc)
            subscription_tier = "professional"
            context = type("obj", (object,), {"value": "startup"})
            executive_summary = "Test summary"
            repository_type = type("obj", (object,), {"value": "portfolio_project"})
            analysis_limitations = ["Test limitation"]

            class screening_insights:
                confidence_explanation = "High confidence"
                data_limitations = ["No private access"]
                insights = [
                    type(
                        "obj",
                        (object,),
                        {
                            "category": "technical",
                            "description": "Test insight",
                            "evidence": ["Evidence 1"],
                            "confidence": "high",
                            "impact": "positive",
                        },
                    )
                ]

            evidence_summary = {
                "technical_patterns": [
                    {
                        "type": "language_expertise",
                        "finding": "TypeScript dominant",
                        "insight": "Strong TS skills",
                    }
                ]
            }

            interview_questions = None
            green_flags = []
            red_flags = []

        # Test conversion
        clean = convert_to_clean_response(MockReport(), estimated_cost=0.0034)

        # Verify evidence-based structure
        assert clean.confidence_explanation == "High confidence"
        assert clean.data_limitations == ["No private access"]
        assert len(clean.evidence_patterns) > 0
        assert clean.evidence_patterns[0].pattern_type == "technical"

        # Verify no scores in output
        assert clean.confidence_explanation != ""  # Text instead of number
        assert isinstance(clean.evidence_patterns, list)  # Patterns not metrics

    def test_question_model_evidence_reference(self):
        """Test QuestionModel includes evidence references."""
        question = QuestionModel(
            category="technical_decisions",
            question="Your commits show migration to microservices. What drove this decision?",
            evidence_reference="15 commits refactoring monolith (March-May 2025)",
            follow_ups=["How did you handle data consistency?"],
            what_to_listen_for="Architecture understanding",
            context_relevance="Important for distributed systems",
        )

        # Verify evidence reference
        assert (
            question.evidence_reference
            == "15 commits refactoring monolith (March-May 2025)"
        )
        assert "Your commits show" in question.question

    def test_insight_model_with_evidence(self):
        """Test InsightModel includes evidence list."""
        insight = InsightModel(
            category="collaboration",
            description="Strong team collaboration patterns",
            evidence=[
                "Co-authored 45% of commits",
                "References 40 different PRs",
                "3 regular collaborators",
            ],
            confidence="high",
            impact="positive",
        )

        # Verify evidence
        assert len(insight.evidence) == 3
        assert "Co-authored 45% of commits" in insight.evidence

    def test_recommendation_model_with_evidence(self):
        """Test RecommendationModel can include evidence."""
        recommendation = RecommendationModel(
            type="strength",
            text="Strong testing practices demonstrated",
            priority="high",
            evidence="40 test files, 85% of commits include tests",
        )

        # Verify evidence field
        assert recommendation.evidence == "40 test files, 85% of commits include tests"

    def test_response_handles_minimal_repos(self):
        """Test response properly handles minimal/empty repositories."""
        response = CleanAnalysisResponse(
            repository_url="https://github.com/kelseyhightower/nocode",
            repository_name="nocode",
            analysis_date="2025-07-28T00:00:00Z",
            subscription_tier="free",
            context="startup",
            executive_summary="This repository contains minimal content and lacks sufficient code for meaningful technical analysis.",
            repository_type="minimal",
            confidence_explanation="No analysis performed - repository contains minimal or no code",
            insights=[],
            questions=[],
            recommendations=[],
            evidence_patterns=[],
            limitations=["Repository contains minimal or no code"],
            data_limitations=["Insufficient content for analysis"],
            green_flags=[],
            red_flags=[],
        )

        # Verify minimal repo handling
        assert response.repository_type == "minimal"
        assert response.insights_count == 0
        assert response.evidence_patterns_count == 0
        assert "minimal content" in response.executive_summary.lower()
        assert response.estimated_cost == 0.0

    def test_tier_appropriate_fields(self):
        """Test that response models handle tier-specific fields correctly."""
        # FREE tier - no questions
        free_response = CleanAnalysisResponse(
            repository_url="https://github.com/user/repo",
            repository_name="repo",
            analysis_date="2025-07-28T00:00:00Z",
            subscription_tier="free",
            context="general",
            executive_summary="Basic analysis",
            repository_type="portfolio_project",
            confidence_explanation="Template-based analysis",
            insights=[],
            questions=[],  # Empty for free tier
            recommendations=[],
            evidence_patterns=[],
            limitations=[],
            data_limitations=[],
            green_flags=[],
            red_flags=[],
        )
        assert free_response.questions_count == 0

        # PROFESSIONAL tier - has questions
        pro_response = CleanAnalysisResponse(
            repository_url="https://github.com/user/repo",
            repository_name="repo",
            analysis_date="2025-07-28T00:00:00Z",
            subscription_tier="professional",
            context="general",
            executive_summary="Detailed analysis",
            repository_type="portfolio_project",
            confidence_explanation="AI-powered analysis",
            insights=[],
            questions=[
                QuestionModel(
                    category="technical",
                    question="Describe your approach to testing.",
                    evidence_reference="Test files detected",
                )
            ],
            recommendations=[],
            evidence_patterns=[],
            limitations=[],
            data_limitations=[],
            green_flags=[],
            red_flags=[],
        )
        assert pro_response.questions_count == 1
