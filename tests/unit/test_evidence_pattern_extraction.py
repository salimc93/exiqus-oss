"""
Unit test for Operation Final Exorcism - Evidence Pattern Extraction
This test ensures that evidence patterns are NEVER lost in the data transformation pipeline.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional

from src.github_analyzer.api.models.clean_responses import convert_to_clean_response


@dataclass
class MockInsight:
    """Mock insight object for testing."""

    category: str
    description: str
    evidence: List[str]
    confidence: str = "high"
    impact: str = "positive"
    context_relevance: Optional[str] = None


@dataclass
class MockScreeningInsights:
    """Mock screening insights object."""

    insights: List[MockInsight]
    confidence_explanation: str = "High confidence based on evidence"
    data_limitations: List[str] = None

    def __post_init__(self):
        if self.data_limitations is None:
            self.data_limitations = []


@dataclass
class MockQuestion:
    """Mock interview question object."""

    category: str
    question: str
    evidence_reference: str
    follow_ups: List[str] = None
    what_to_listen_for: str = ""
    context_relevance: str = ""

    def __post_init__(self):
        if self.follow_ups is None:
            self.follow_ups = []


@dataclass
class MockAssessmentSection:
    """Mock assessment section with details."""

    details: List[str]
    summary: str = "Section summary"


def create_complete_structured_report() -> Any:
    """Create a complete mock StructuredReport with all evidence sources."""

    # Create a mock object with all required attributes
    class MockReport:
        def __init__(self):
            # Basic metadata
            self.repository_url = "https://github.com/test/repo"
            self.repository_name = "test/repo"
            self.analysis_date = datetime.now()
            self.subscription_tier = "professional"
            self.context = type("obj", (object,), {"value": "startup"})()
            self.executive_summary = "Test repository with evidence patterns"
            self.repository_type = type("obj", (object,), {"value": "production"})()

            # Screening insights with multiple insights
            self.screening_insights = MockScreeningInsights(
                insights=[
                    MockInsight(
                        category="technical_skills",
                        description="Strong TypeScript expertise demonstrated",
                        evidence=["89.5% TypeScript", "Advanced patterns"],
                        context_relevance="Critical for startup development",
                    ),
                    MockInsight(
                        category="work_patterns",
                        description="Consistent commit patterns",
                        evidence=["Daily commits", "Clear messages"],
                        impact="positive",
                    ),
                    MockInsight(
                        category="collaboration",
                        description="Active team collaboration",
                        evidence=["PR reviews", "Issue discussions"],
                        confidence="medium",
                    ),
                ]
            )

            # Interview questions with evidence references
            self.interview_questions = {
                "all_questions": [
                    {
                        "category": "technical_decisions",
                        "question": "How do you approach TypeScript in production?",
                        "evidence_reference": "89.5% TypeScript usage",
                        "follow_ups": ["Type safety approaches"],
                        "what_to_listen_for": "Understanding of type systems",
                        "context_relevance": "Startup technical needs",
                    },
                    {
                        "category": "team_collaboration",
                        "question": "Describe your PR review process?",
                        "evidence_reference": "Active PR participation",
                        "follow_ups": ["Code quality standards"],
                        "what_to_listen_for": "Team practices",
                        "context_relevance": "Team dynamics",
                    },
                ]
            }

            # Evidence summary with technical patterns
            self.evidence_summary = {
                "technical_patterns": [
                    {
                        "type": "Testing Infrastructure",
                        "finding": "98% test coverage with 847 tests",
                        "insight": "Strong testing practices",
                    },
                    {
                        "type": "Architecture Pattern",
                        "finding": "Clean architecture with dependency injection",
                        "insight": "Scalable design",
                    },
                ],
                "behavioral_analysis": {
                    "behavioral_insights": [
                        {
                            "type": "Communication Style",
                            "finding": "Clear, detailed commit messages",
                            "insight": "Good documentation practices",
                        }
                    ]
                },
            }

            # Assessment sections with details
            self.technical_assessment = MockAssessmentSection(
                details=[
                    "Strong TypeScript proficiency",
                    "Clean code architecture",
                    "Comprehensive testing",
                ]
            )
            self.professional_practices = MockAssessmentSection(
                details=[
                    "Consistent coding standards",
                    "Regular refactoring",
                    "Documentation focus",
                ]
            )
            self.communication_skills = MockAssessmentSection(
                details=["Clear commit messages", "Detailed PR descriptions"]
            )
            self.growth_indicators = MockAssessmentSection(
                details=["Learning new frameworks", "Skill progression visible"]
            )

            # Other required fields
            self.overall_recommendation = "Strong candidate"
            self.context_fit_score = 0.85
            self.key_strengths = ["TypeScript", "Testing", "Architecture"]
            self.primary_concerns = []
            self.analysis_recommendations = []
            self.interview_focus_areas = ["Technical depth", "Team collaboration"]
            self.analysis_limitations = []
            self.green_flags = []
            self.red_flags = []
            self.evidence_based_recommendations = None

    return MockReport()


class TestEvidencePatternExtraction:
    """Test suite for evidence pattern extraction - Operation Final Exorcism."""

    def test_evidence_patterns_extracted_from_all_sources(self):
        """Test that evidence patterns are extracted from ALL available sources."""
        # Arrange
        structured_report = create_complete_structured_report()

        # Act
        clean_response = convert_to_clean_response(
            structured_report, estimated_cost=0.001
        )

        # Assert - The critical assertion
        assert clean_response.evidence_patterns is not None, (
            "Evidence patterns should not be None"
        )
        assert len(clean_response.evidence_patterns) > 0, (
            "Evidence patterns list should not be empty"
        )

        # Verify we got patterns from multiple sources
        pattern_types = {p.pattern_type for p in clean_response.evidence_patterns}
        assert "technical" in pattern_types, "Should have technical patterns"
        assert "behavioral" in pattern_types, "Should have behavioral patterns"

        # Verify counts match
        assert clean_response.evidence_patterns_count == len(
            clean_response.evidence_patterns
        ), "Count should match actual patterns"

        # Log the actual count for debugging
        print(
            f"✅ Successfully extracted {len(clean_response.evidence_patterns)} evidence patterns"
        )

        # Verify patterns from insights (should be 3)
        insights_patterns = [
            p
            for p in clean_response.evidence_patterns
            if any(
                cat in p.category
                for cat in ["technical_skills", "work_patterns", "collaboration"]
            )
        ]
        assert len(insights_patterns) >= 3, "Should have patterns from insights"

        # Questions are NOT converted to patterns anymore (user requirement)
        # They should only appear in the Questions tab, not Evidence tab
        # This test has been updated to reflect the correct behavior

        # Verify patterns from evidence_summary
        summary_patterns = [
            p
            for p in clean_response.evidence_patterns
            if "Testing Infrastructure" in p.name or "Architecture Pattern" in p.name
        ]
        assert len(summary_patterns) >= 2, "Should have patterns from evidence_summary"

    def test_evidence_patterns_structure(self):
        """Test that each evidence pattern has the required structure."""
        # Arrange
        structured_report = create_complete_structured_report()

        # Act
        clean_response = convert_to_clean_response(structured_report)

        # Assert - Check structure of each pattern
        for pattern in clean_response.evidence_patterns:
            assert pattern.name, "Pattern must have a name"
            assert pattern.pattern_type, "Pattern must have a type"
            assert pattern.evidence, "Pattern must have evidence"
            assert pattern.context is not None, (
                "Pattern must have context (can be empty string)"
            )
            assert pattern.insight, "Pattern must have insight"
            assert pattern.category, "Pattern must have category"

            # Verify pattern_type is valid
            valid_types = [
                "technical",
                "behavioral",
                "collaboration",
                "quality",
                "professional",
                "communication",
                "growth",
            ]
            assert pattern.pattern_type in valid_types, (
                f"Pattern type {pattern.pattern_type} not in valid types"
            )

    def test_evidence_patterns_from_insights_with_enum_category(self):
        """Test that InsightCategory enums are properly converted (the original bug)."""

        # Arrange
        class InsightCategory:
            """Mock enum class."""

            def __init__(self, value):
                self.value = value

        class MockReportWithEnum:
            def __init__(self):
                self.repository_url = "https://github.com/test/repo"
                self.repository_name = "test/repo"
                self.analysis_date = datetime.now()
                self.subscription_tier = "professional"
                self.context = type("obj", (object,), {"value": "startup"})()
                self.executive_summary = "Test"
                self.repository_type = type("obj", (object,), {"value": "production"})()

                # Create insight with enum category (the bug case)
                insight = type(
                    "obj",
                    (object,),
                    {
                        "category": InsightCategory("technical_skills"),
                        "description": "Test insight",
                        "evidence": ["Evidence 1"],
                        "confidence": "high",
                        "impact": "positive",
                        "context_relevance": "Relevant to startup",
                    },
                )()

                self.screening_insights = type(
                    "obj",
                    (object,),
                    {
                        "insights": [insight],
                        "confidence_explanation": "High confidence",
                        "data_limitations": [],
                    },
                )()

                # Minimal other fields - add all required fields
                self.overall_recommendation = "Test"
                self.context_fit_score = 0.5
                self.key_strengths = []
                self.primary_concerns = []
                self.analysis_recommendations = []
                self.interview_focus_areas = []
                self.analysis_limitations = []
                self.green_flags = []
                self.red_flags = []
                self.interview_questions = None
                self.evidence_summary = None
                self.technical_assessment = None
                self.professional_practices = None
                self.communication_skills = None
                self.growth_indicators = None
                self.evidence_based_recommendations = None

        report = MockReportWithEnum()

        # Act - This should not raise an AttributeError
        clean_response = convert_to_clean_response(report)

        # Assert
        assert len(clean_response.evidence_patterns) > 0, (
            "Should extract patterns even with enum categories"
        )
        assert clean_response.evidence_patterns[0].category == "technical_skills", (
            "Category should be properly converted from enum"
        )

    def test_evidence_patterns_never_empty_when_insights_exist(self):
        """The critical test: If insights exist, evidence patterns MUST be extracted."""

        # Arrange - Minimal report with just insights
        class MinimalReport:
            def __init__(self):
                self.repository_url = "https://github.com/test/repo"
                self.repository_name = "test/repo"
                self.analysis_date = datetime.now()
                self.subscription_tier = "starter"
                self.context = type("obj", (object,), {"value": "startup"})()
                self.executive_summary = "Test"
                self.repository_type = type("obj", (object,), {"value": "production"})()

                self.screening_insights = MockScreeningInsights(
                    insights=[
                        MockInsight(
                            category="technical",
                            description="Has code",
                            evidence=["Some evidence"],
                        )
                    ]
                )

                # Required fields
                self.overall_recommendation = ""
                self.context_fit_score = 0
                self.key_strengths = []
                self.primary_concerns = []
                self.analysis_recommendations = []
                self.interview_focus_areas = []
                self.analysis_limitations = []
                self.green_flags = []
                self.red_flags = []

        report = MinimalReport()

        # Act
        clean_response = convert_to_clean_response(report)

        # Assert - THE GOLDEN RULE
        assert len(clean_response.insights) > 0, "Has insights"
        assert len(clean_response.evidence_patterns) > 0, (
            "🔴 CRITICAL FAILURE: Evidence patterns MUST be extracted when insights exist!"
        )
        assert clean_response.evidence_patterns_count > 0, (
            "🔴 CRITICAL FAILURE: Evidence pattern count must be > 0 when insights exist!"
        )


if __name__ == "__main__":
    # Run the tests
    test = TestEvidencePatternExtraction()

    print("Running Operation Final Exorcism Unit Tests...")
    print("=" * 60)

    try:
        test.test_evidence_patterns_extracted_from_all_sources()
        print("✅ Test 1: Evidence patterns extracted from all sources")
    except AssertionError as e:
        print(f"❌ Test 1 FAILED: {e}")

    try:
        test.test_evidence_patterns_structure()
        print("✅ Test 2: Evidence patterns have correct structure")
    except AssertionError as e:
        print(f"❌ Test 2 FAILED: {e}")

    try:
        test.test_evidence_patterns_from_insights_with_enum_category()
        print("✅ Test 3: Enum categories are properly converted")
    except AssertionError as e:
        print(f"❌ Test 3 FAILED: {e}")

    try:
        test.test_evidence_patterns_never_empty_when_insights_exist()
        print("✅ Test 4: Evidence patterns never empty when insights exist")
    except AssertionError as e:
        print(f"❌ Test 4 FAILED: {e}")

    print("=" * 60)
    print("Unit test suite complete!")
