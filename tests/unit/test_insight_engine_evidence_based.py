"""
Unit tests for evidence-based insight engine.

Ensures insights are based on actual observations without arbitrary scoring.
"""

import pytest

from github_analyzer.core.evidence.insight_engine_evidence_based import (
    EvidenceBasedInsight,
    EvidenceBasedInsightEngine,
    InsightReport,
)


class TestEvidenceBasedInsightEngine:
    """Test evidence-based insight generation."""

    @pytest.fixture
    def engine(self):
        """Create engine instance."""
        return EvidenceBasedInsightEngine()

    @pytest.fixture
    def comprehensive_observations(self):
        """Create comprehensive observation data."""
        return {
            "technical": [
                {
                    "type": "language_expertise",
                    "finding": "Primary language: Python (75% of codebase)",
                    "evidence": ["src/main.py", "src/utils.py"],
                },
                {
                    "type": "architecture",
                    "finding": "Modular architecture with clear separation of concerns",
                    "evidence": ["src/models/", "src/services/", "src/api/"],
                },
            ],
            "behavioral": [
                {
                    "category": "work_patterns",
                    "observation": "Commits on 45 of 90 days, typically between 9am-5pm",
                    "evidence": ["Commit timestamp analysis"],
                    "data_context": "Based on 150 commits",
                    "interview_topics": ["Work schedule preferences"],
                }
            ],
            "collaboration": [
                {
                    "observation": "Repository has 5 contributors with balanced contributions",
                    "evidence": [
                        "alice: 40 commits",
                        "bob: 35 commits",
                        "carol: 30 commits",
                    ],
                }
            ],
            "quality": [
                {
                    "type": "testing",
                    "finding": "Test files found in tests/ directory",
                    "evidence": ["tests/test_main.py", "tests/test_utils.py"],
                },
                {
                    "type": "documentation",
                    "finding": "README and inline documentation present",
                    "evidence": ["README.md", "Docstrings in 80% of functions"],
                },
            ],
            "growth": [
                {
                    "type": "evolution",
                    "finding": "Evolution from JavaScript to TypeScript over time",
                    "evidence": [
                        "Early commits: .js files",
                        "Recent commits: .ts files",
                    ],
                }
            ],
        }

    @pytest.fixture
    def minimal_observations(self):
        """Create minimal observation data."""
        return {
            "technical": [
                {
                    "type": "language",
                    "finding": "Single HTML file repository",
                    "evidence": ["index.html"],
                }
            ],
            "behavioral": [
                {
                    "category": "work_patterns",
                    "observation": "Only 3 commits total",
                    "evidence": ["Insufficient data for patterns"],
                }
            ],
        }

    @pytest.fixture
    def comprehensive_data_summary(self):
        """Create comprehensive data summary."""
        return {
            "total_commits": 150,
            "unique_contributors": 5,
            "timespan_days": 90,
            "languages": ["Python", "JavaScript", "TypeScript"],
            "has_tests": True,
            "has_readme": True,
        }

    @pytest.fixture
    def minimal_data_summary(self):
        """Create minimal data summary."""
        return {
            "total_commits": 3,
            "unique_contributors": 1,
            "timespan_days": 1,
            "languages": ["HTML"],
            "has_tests": False,
            "has_readme": False,
        }

    def test_no_arbitrary_scores(
        self, engine, comprehensive_observations, comprehensive_data_summary
    ):
        """Ensure insights contain no arbitrary scores or metrics."""
        report = engine.generate_insights(
            comprehensive_observations, comprehensive_data_summary, context="startup"
        )

        # Check report structure
        assert isinstance(report, InsightReport)
        assert len(report.insights) > 0

        # Check no scoring in insights
        for insight in report.insights:
            assert not hasattr(insight, "score")
            assert not hasattr(insight, "confidence_score")
            assert not hasattr(insight, "rating")

            # Check text doesn't contain scoring language
            all_text = insight.observation + insight.context + str(insight.limitations)
            assert "score" not in all_text.lower()
            assert "rating" not in all_text.lower()
            # Allow "moderate" only in context of "moderate data"
            if "moderate" in all_text.lower():
                assert "moderate data" in all_text.lower()

    def test_evidence_based_observations(
        self, engine, comprehensive_observations, comprehensive_data_summary
    ):
        """Test that insights are based on actual evidence."""
        report = engine.generate_insights(
            comprehensive_observations, comprehensive_data_summary
        )

        # Each insight should have evidence
        for insight in report.insights:
            assert len(insight.evidence) > 0
            assert all(isinstance(e, str) for e in insight.evidence)

            # Observation should be factual
            assert insight.observation
            assert isinstance(insight.observation, str)

    def test_limitations_acknowledged(
        self, engine, comprehensive_observations, comprehensive_data_summary
    ):
        """Test that limitations are properly acknowledged."""
        report = engine.generate_insights(
            comprehensive_observations, comprehensive_data_summary
        )

        # Report should have assessment gaps
        assert len(report.assessment_gaps) > 0

        # Some insights should have limitations
        insights_with_limitations = [i for i in report.insights if i.limitations]
        assert len(insights_with_limitations) > 0

        # Check fundamental limitations are included
        all_gaps = " ".join(report.assessment_gaps).lower()
        assert any(
            limit in all_gaps for limit in ["performance", "soft skills", "pressure"]
        )

    def test_interview_guidance_generated(
        self, engine, comprehensive_observations, comprehensive_data_summary
    ):
        """Test that interview guidance is generated."""
        report = engine.generate_insights(
            comprehensive_observations, comprehensive_data_summary, context="startup"
        )

        assert len(report.interview_guidance) > 0
        assert all(isinstance(topic, str) for topic in report.interview_guidance)

        # Should include some fundamental topics
        all_topics = " ".join(report.interview_guidance).lower()
        assert any(
            topic in all_topics for topic in ["problem-solving", "communication"]
        )

    def test_minimal_data_handling(
        self, engine, minimal_observations, minimal_data_summary
    ):
        """Test handling of minimal data."""
        report = engine.generate_insights(minimal_observations, minimal_data_summary)

        # Should acknowledge limited data
        behavioral_insights = [i for i in report.insights if i.category == "behavioral"]
        assert any(
            "limited" in i.observation.lower()
            or "insufficient" in i.observation.lower()
            for i in behavioral_insights
        )

        # Data summary should note limitations
        assert "limited data" in report.data_summary.lower()

    def test_context_specific_insights(
        self, engine, comprehensive_observations, comprehensive_data_summary
    ):
        """Test that insights are tailored to context."""
        contexts = ["startup", "enterprise", "agency", "open_source"]

        reports = {}
        for context in contexts:
            reports[context] = engine.generate_insights(
                comprehensive_observations, comprehensive_data_summary, context=context
            )

        # Each context should have context notes
        for context, report in reports.items():
            assert context in ["startup", "enterprise", "agency", "open_source"]
            assert "focus" in report.context_notes
            assert "caution" in report.context_notes

            # Context relevance should be present in insights
            for insight in report.insights:
                if insight.context_relevance:
                    assert context in insight.context_relevance

    def test_technical_insights(self, engine):
        """Test technical insight generation."""
        observations = {
            "technical": [
                {
                    "type": "language_expertise",
                    "finding": "Primary language: Go (90% of codebase)",
                    "evidence": ["main.go", "server.go", "handler.go"],
                },
                {
                    "type": "architecture",
                    "finding": "Microservices architecture pattern",
                    "evidence": ["services/auth", "services/api", "services/worker"],
                },
            ]
        }

        report = engine.generate_insights(
            observations, {"total_commits": 50, "unique_contributors": 2}
        )

        tech_insights = [i for i in report.insights if i.category == "technical"]
        assert len(tech_insights) > 0

        # Should mention Go
        go_insights = [i for i in tech_insights if "go" in i.observation.lower()]
        assert len(go_insights) > 0

        # Should have architecture insight
        arch_insights = [
            i
            for i in tech_insights
            if "structure" in i.observation.lower()
            or "organization" in i.observation.lower()
        ]
        assert len(arch_insights) > 0

    def test_behavioral_insights_require_data(self, engine):
        """Test that behavioral insights require sufficient data."""
        # Test with insufficient data
        insufficient_obs = {
            "behavioral": [
                {
                    "category": "work_patterns",
                    "observation": "Only 10 commits available",
                    "evidence": ["Limited data"],
                }
            ]
        }

        report = engine.generate_insights(insufficient_obs, {"total_commits": 10})

        behavioral = [i for i in report.insights if i.category == "behavioral"]
        if behavioral:
            # Should acknowledge insufficient data
            assert any(
                "insufficient" in i.observation.lower()
                or "limited" in i.observation.lower()
                for i in behavioral
            )

    def test_collaboration_single_contributor(self, engine):
        """Test collaboration insights for single contributor repos."""
        observations = {
            "collaboration": [
                {
                    "observation": "Single contributor repository",
                    "evidence": ["All commits by one author"],
                }
            ]
        }

        report = engine.generate_insights(
            observations, {"total_commits": 50, "unique_contributors": 1}
        )

        collab_insights = [i for i in report.insights if i.category == "collaboration"]
        assert len(collab_insights) > 0

        # Should note inability to assess team collaboration
        single_contrib = collab_insights[0]
        assert (
            "solo" in single_contrib.observation.lower()
            or "single" in single_contrib.observation.lower()
        )
        assert len(single_contrib.interview_topics) > 0
        assert any("team" in topic.lower() for topic in single_contrib.interview_topics)

    def test_quality_insights_with_tests(self, engine):
        """Test quality insights when tests are present."""
        observations = {
            "quality": [
                {
                    "type": "testing",
                    "finding": "Comprehensive test suite found",
                    "evidence": ["30 test files", "tests/unit/", "tests/integration/"],
                }
            ]
        }

        report = engine.generate_insights(
            observations, {"total_commits": 100, "has_tests": True}
        )

        quality_insights = [i for i in report.insights if i.category == "quality"]
        assert len(quality_insights) > 0

        test_insight = quality_insights[0]
        assert "test" in test_insight.observation.lower()
        assert len(test_insight.limitations) > 0
        assert any(
            "quality" in lim.lower() or "coverage" in lim.lower()
            for lim in test_insight.limitations
        )

    def test_data_summary_generation(self, engine, comprehensive_observations):
        """Test data summary text generation."""
        # Test comprehensive data
        report = engine.generate_insights(
            comprehensive_observations,
            {
                "total_commits": 200,
                "unique_contributors": 10,
                "timespan_days": 365,
                "languages": ["Python", "JavaScript", "Go", "Rust"],
            },
        )

        assert "200 commits" in report.data_summary
        assert "10 contributors" in report.data_summary
        assert "365 days" in report.data_summary
        assert "4 languages" in report.data_summary
        assert "comprehensive analysis" in report.data_summary.lower()

        # Test minimal data
        report_minimal = engine.generate_insights(
            {}, {"total_commits": 5, "unique_contributors": 1}
        )

        assert "5 commits" in report_minimal.data_summary
        assert "limited data" in report_minimal.data_summary.lower()

    def test_key_observations_extraction(
        self, engine, comprehensive_observations, comprehensive_data_summary
    ):
        """Test extraction of key observations."""
        report = engine.generate_insights(
            comprehensive_observations, comprehensive_data_summary
        )

        assert len(report.key_observations) > 0
        assert len(report.key_observations) <= 5  # Should be limited

        # Should be actual observations from insights
        insight_observations = [i.observation for i in report.insights]
        for key_obs in report.key_observations:
            assert key_obs in insight_observations

    def test_no_evaluative_language(
        self, engine, comprehensive_observations, comprehensive_data_summary
    ):
        """Test that insights avoid evaluative language."""
        report = engine.generate_insights(
            comprehensive_observations, comprehensive_data_summary
        )

        evaluative_terms = [
            "good",
            "bad",
            "excellent",
            "poor",
            "weak",
            "strong",
            "impressive",
            "concerning",
            "problematic",
        ]

        for insight in report.insights:
            all_text = (
                insight.observation
                + insight.context
                + " ".join(insight.limitations)
                + " ".join(insight.interview_topics)
            )

            for term in evaluative_terms:
                assert term not in all_text.lower(), (
                    f"Found evaluative term '{term}' in insight"
                )

    def test_growth_insights(self, engine):
        """Test growth and evolution insights."""
        observations = {
            "growth": [
                {
                    "type": "evolution",
                    "finding": "Progression from jQuery to React over 2 years",
                    "evidence": ["2022: jquery.js", "2023: App.jsx", "2024: App.tsx"],
                }
            ]
        }

        report = engine.generate_insights(observations, {"total_commits": 100})

        growth_insights = [i for i in report.insights if i.category == "growth"]
        assert len(growth_insights) > 0

        evolution = growth_insights[0]
        assert (
            "technology" in evolution.observation.lower()
            or "evolution" in evolution.observation.lower()
        )
        assert len(evolution.interview_topics) > 0
        assert any("learning" in topic.lower() for topic in evolution.interview_topics)


class TestEvidenceBasedInsight:
    """Test the EvidenceBasedInsight data structure."""

    def test_insight_creation(self):
        """Test creating an insight."""
        insight = EvidenceBasedInsight(
            category="technical",
            observation="Uses Python for backend development",
            evidence=["app.py", "requirements.txt"],
            context="Python is common for web backends",
            limitations=["Cannot assess Python proficiency level"],
            interview_topics=["Python experience and best practices"],
            context_relevance={
                "startup": "Python enables rapid development",
                "enterprise": "Python has good enterprise support",
            },
        )

        assert insight.category == "technical"
        assert "Python" in insight.observation
        assert len(insight.evidence) == 2
        assert len(insight.limitations) == 1
        assert len(insight.interview_topics) == 1
        assert "startup" in insight.context_relevance


class TestInsightReport:
    """Test the InsightReport structure."""

    def test_report_creation(self):
        """Test creating an insight report."""
        insights = [
            EvidenceBasedInsight(
                category="technical",
                observation="Primarily JavaScript development",
                evidence=["index.js"],
                context="Frontend focus apparent",
            )
        ]

        report = InsightReport(
            insights=insights,
            key_observations=["Primarily JavaScript development"],
            assessment_gaps=["Cannot assess performance"],
            interview_guidance=["Discuss JavaScript expertise"],
            data_summary="Analysis based on 50 commits",
            context_notes={"focus": "Technical skills"},
        )

        assert len(report.insights) == 1
        assert len(report.key_observations) == 1
        assert len(report.assessment_gaps) == 1
        assert len(report.interview_guidance) == 1
        assert "50 commits" in report.data_summary
        assert "focus" in report.context_notes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
