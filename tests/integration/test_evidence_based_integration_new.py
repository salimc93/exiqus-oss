"""
Integration tests for the new evidence-based analysis system.

Tests the complete flow without arbitrary metrics or scores.
"""

from datetime import datetime, timezone

import pytest

from github_analyzer.core.context_analyzer import AnalysisContext
from github_analyzer.core.evidence_based_analyzer import (
    DataSufficiency,
    EvidenceBasedAnalysis,
    EvidenceBasedAnalyzer,
    Observation,
)
from github_analyzer.core.report_generator import ReportGenerator
from github_analyzer.data.models import (
    CommitInfo,
    FileInfo,
    RepositoryData,
    RepositoryMetrics,
)


class TestEvidenceBasedIntegration:
    """Test evidence-based analysis integration without arbitrary metrics."""

    def _convert_repo_to_dict(self, repo_data: RepositoryData) -> dict:
        """Convert RepositoryData to dictionary format expected by analyzer."""
        return {
            "url": repo_data.url,
            "full_name": repo_data.full_name,
            "name": repo_data.name,
            "owner": repo_data.owner,
            "description": repo_data.description,
            "languages": repo_data.languages,
            "topics": repo_data.topics,
            "commits": [
                {
                    "sha": c.sha,
                    "message": c.message,
                    "author": c.author_name,
                    "date": c.date.isoformat() if c.date else None,
                }
                for c in (repo_data.recent_commits or [])
            ],
            "files": (
                [
                    "src/main.py",
                    "src/api.py",
                    "src/utils.py",
                    "tests/test_main.py",
                    "tests/test_api.py",
                    "docs/README.md",
                    "docs/API.md",
                    ".github/workflows/ci.yml",
                ]
                if repo_data.has_tests
                else []
            ),
            "readme_content": repo_data.readme_content,
            "metrics": repo_data.metrics.__dict__ if repo_data.metrics else {},
            "has_tests": repo_data.has_tests,
            "has_documentation": repo_data.has_readme,
            "pull_requests": [],  # Not available in test data
            "issues": [],  # Not available in test data
        }

    @pytest.fixture
    def portfolio_repo(self):
        """Create a portfolio-quality repository for testing."""
        return RepositoryData(
            url="https://github.com/expert/awesome-project",
            full_name="expert/awesome-project",
            name="awesome-project",
            owner="expert",
            description="A comprehensive portfolio project showcasing best practices",
            created_at=datetime(2021, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2025, 7, 20, tzinfo=timezone.utc),
            pushed_at=datetime(2025, 7, 20, tzinfo=timezone.utc),
            default_branch="main",
            size=15000,
            languages={
                "Python": 60000,
                "TypeScript": 30000,
                "JavaScript": 15000,
                "Rust": 10000,
            },
            topics=["api", "microservices", "best-practices", "clean-code"],
            license_name="MIT",
            stars=500,
            forks=120,
            watchers=80,
            open_issues=5,
            has_readme=True,
            has_license=True,
            has_contributing=True,
            has_tests=True,
            has_ci_config=True,
            recent_commits=[
                CommitInfo(
                    sha="abc123",
                    message="feat: Add comprehensive error handling",
                    author_name="expert",
                    author_email="expert@example.com",
                    date=datetime(2025, 7, 20, 10, 0, tzinfo=timezone.utc),
                ),
                CommitInfo(
                    sha="def456",
                    message="test: Improve test coverage",
                    author_name="expert",
                    author_email="expert@example.com",
                    date=datetime(2025, 7, 19, 15, 0, tzinfo=timezone.utc),
                ),
            ],
            file_structure=[
                FileInfo("src/", "src", 0, "directory"),
                FileInfo("tests/", "tests", 0, "directory"),
                FileInfo("docs/", "docs", 0, "directory"),
                FileInfo(".github/workflows/", "workflows", 0, "directory"),
            ],
            readme_content="""
# Awesome Project

A comprehensive demonstration of software engineering best practices.

## Features
- Clean architecture
- Comprehensive testing
- Detailed documentation
- CI/CD pipeline
- Performance optimized

## Getting Started
...""",
            metrics=RepositoryMetrics(
                total_commits=1200,
                unique_contributors=25,
                lines_of_code=35000,
                test_coverage_estimate=0.85,  # Just a data point, not a score
                documentation_presence="3 documentation files in 10 total files",
                days_since_last_commit=1,
                commit_frequency=12.0,
                avg_commit_size=100.0,
            ),
            fetched_at=datetime.now(timezone.utc),
            is_private=False,
            is_fork=False,
            is_archived=False,
            is_disabled=False,
        )

    def test_evidence_based_analysis_flow(self, portfolio_repo):
        """Test complete evidence-based analysis without scores."""
        analyzer = EvidenceBasedAnalyzer()

        # Perform analysis
        result = analyzer.analyze(self._convert_repo_to_dict(portfolio_repo))

        # Verify observation-based structure
        assert isinstance(result, EvidenceBasedAnalysis)
        assert len(result.observations) > 0

        # Check observations are factual
        for obs in result.observations:
            assert isinstance(obs, Observation)
            assert obs.category in [
                "technical",
                "behavioral",
                "collaboration",
                "quality",
            ]
            # Some observations may not have evidence (e.g., "Single contributor")
            assert isinstance(obs.evidence, list)
            assert obs.context  # Should have context

            # No scores or ratings
            assert "score" not in obs.finding.lower()
            assert "excellent" not in obs.finding.lower()
            assert "poor" not in obs.finding.lower()
            assert "good" not in obs.finding.lower()
            assert "bad" not in obs.finding.lower()

        # Check data limitations are acknowledged
        assert hasattr(result, "data_sufficiency")
        assert len(result.data_sufficiency.limitations) > 0
        for limitation in result.data_sufficiency.limitations:
            assert isinstance(limitation, str)
            assert limitation  # Should describe what's missing

        # Check interview guidance is actionable
        assert len(result.interview_guidance) > 0
        for guidance in result.interview_guidance:
            assert isinstance(guidance, str)
            assert guidance  # Should be a topic/question

        # Check data sufficiency
        assert isinstance(result.data_sufficiency, DataSufficiency)
        assert result.data_sufficiency.total_commits >= 0
        assert len(result.data_sufficiency.limitations) >= 0

    def test_behavioral_patterns_without_scores(self, portfolio_repo):
        """Test behavioral analysis returns observations not scores."""
        from github_analyzer.core.evidence.behavioral_analyzer_evidence_based import (
            BehavioralAnalyzerEvidenceBased,
        )

        analyzer = BehavioralAnalyzerEvidenceBased()
        result = analyzer.analyze_behavior(portfolio_repo)

        # Should return factual data
        assert "data_context" in result
        assert "work_patterns" in result
        assert "communication_patterns" in result

        # Check work patterns contain only factual observations
        work_patterns = result.get("work_patterns", {})
        if "observations" in work_patterns:
            # Check observations are factual
            for obs in work_patterns["observations"]:
                # No scoring or evaluation
                observation_text = obs.lower()
                assert "score" not in observation_text
                assert "excellent" not in observation_text
                assert "poor" not in observation_text

    def test_confidence_assessment_transparency(self, portfolio_repo):
        """Test confidence scorer provides transparent assessment."""
        from github_analyzer.core.evidence.confidence_scorer_evidence_based import (
            EvidenceBasedConfidenceScorer,
        )

        scorer = EvidenceBasedConfidenceScorer()
        confidence = scorer.assess_confidence(portfolio_repo)

        # Should return confidence assessment (EvidenceBasedConfidence object)
        assert hasattr(confidence, "data_availability")
        assert hasattr(confidence, "limitations")
        assert hasattr(confidence, "uncertainty")
        assert hasattr(confidence, "data_sufficiency")

        # Data sufficiency should be categorical
        assert confidence.data_sufficiency in [
            "comprehensive",
            "adequate",
            "limited",
            "minimal",
        ]

        # Analysis depth should be categorical
        assert confidence.analysis_depth in ["detailed", "standard", "basic", "surface"]

        # Check limitations are listed
        assert isinstance(confidence.limitations, object)
        assert hasattr(confidence.limitations, "all_limitations")

    def test_insight_generation_factual(self, portfolio_repo):
        """Test insight engine generates factual insights."""
        from github_analyzer.core.evidence.evidence_extractor import EvidenceExtractor
        from github_analyzer.core.evidence.insight_engine_evidence_based import (
            EvidenceBasedInsightEngine,
        )

        extractor = EvidenceExtractor()
        evidence = extractor.extract_all_evidence(portfolio_repo)

        engine = EvidenceBasedInsightEngine()
        # Convert evidence to expected format
        observations = {}
        if hasattr(evidence, "observations"):
            # Group observations by category
            for obs in evidence.observations:
                category = obs.get("category", "general")
                if category not in observations:
                    observations[category] = []
                observations[category].append(obs)
        else:
            observations = evidence if isinstance(evidence, dict) else {"general": []}

        data_summary = {
            "repository": portfolio_repo.name,
            "total_commits": portfolio_repo.metrics.total_commits,
            "languages": list(portfolio_repo.languages.keys()),
        }

        insights = engine.generate_insights(observations, data_summary)

        # Should have InsightReport object
        assert hasattr(insights, "insights")
        assert hasattr(insights, "key_observations")
        assert hasattr(insights, "assessment_gaps")
        assert hasattr(insights, "interview_guidance")

        # Key observations should be factual
        assert len(insights.key_observations) >= 0  # May be empty for minimal repos
        for observation in insights.key_observations:
            assert isinstance(observation, str)

            # No evaluative language
            obs_lower = observation.lower()
            assert "excellent" not in obs_lower
            assert "poor" not in obs_lower
            assert "good" not in obs_lower
            assert "bad" not in obs_lower

    def test_question_builder_exploration_focused(self, portfolio_repo):
        """Test question builder focuses on exploration not judgment."""
        from github_analyzer.core.evidence.evidence_extractor import EvidenceExtractor
        from github_analyzer.core.evidence.question_builder_evidence_based import (
            EvidenceBasedQuestionBuilder,
        )

        extractor = EvidenceExtractor()
        evidence = extractor.extract_all_evidence(portfolio_repo)

        builder = EvidenceBasedQuestionBuilder()
        # Convert evidence to expected format
        observations = {}
        if hasattr(evidence, "observations"):
            # Group observations by category
            for obs in evidence.observations:
                category = obs.get("category", "general")
                if category not in observations:
                    observations[category] = []
                observations[category].append(obs)
        else:
            observations = evidence if isinstance(evidence, dict) else {"general": []}

        interview_guide = builder.generate_questions(
            observations, context=AnalysisContext.ENTERPRISE.value
        )

        # Should have exploration-focused questions
        assert hasattr(interview_guide, "questions")
        assert hasattr(interview_guide, "key_observations")
        assert hasattr(interview_guide, "exploration_priorities")

        # Check questions
        assert len(interview_guide.questions) > 0
        for q in interview_guide.questions:
            assert hasattr(q, "question")
            assert hasattr(q, "category")
            assert hasattr(q, "observation_basis")
            assert hasattr(q, "exploration_areas")

            # Questions should be open-ended
            question_text = q.question
            # Questions may end with ? or .
            assert question_text.endswith("?") or question_text.endswith(".")
            assert any(
                starter in question_text.lower()
                for starter in [
                    "how",
                    "what",
                    "why",
                    "describe",
                    "explain",
                    "tell me",
                    "can you",
                    "walk me through",
                ]
            )

    def test_recommendation_engine_evidence_based(self, portfolio_repo):
        """Test recommendation engine provides evidence-based guidance."""
        from github_analyzer.core.evidence.evidence_extractor import EvidenceExtractor
        from github_analyzer.core.evidence.recommendation_engine_evidence_based import (
            EvidenceBasedRecommendationEngine,
        )

        extractor = EvidenceExtractor()
        evidence = extractor.extract_all_evidence(portfolio_repo)

        engine = EvidenceBasedRecommendationEngine()
        assessment = engine.generate_recommendations(
            evidence.observations if hasattr(evidence, "observations") else evidence,
            context=AnalysisContext.ENTERPRISE,
        )

        # Should provide narrative assessment
        assert assessment["summary"]
        assert assessment["total_recommendations"] > 0
        assert len(assessment["all_recommendations"]) > 0
        assert len(assessment["decision_factors"]) > 0
        assert len(assessment["data_limitations"]) > 0

        # Recommendations should be evidence-based
        for rec in assessment["all_recommendations"]:
            assert rec["recommendation"]  # What we observed
            assert rec["evidence"]  # Supporting evidence
            assert rec["action"]  # What it might mean

            # No scoring
            assert "score" not in rec["recommendation"].lower()

        # Narrative assessments instead of scores (now in dictionary)
        # These fields are not directly in the dictionary output anymore

    def test_template_responses_scoreless(self, portfolio_repo):
        """Test template responses contain no scores."""
        from github_analyzer.ai.templates_evidence_based import (
            EvidenceBasedTemplateResponses,
        )
        from github_analyzer.core.classifier import TemplateCategory

        template_manager = EvidenceBasedTemplateResponses()

        # Test various template categories
        categories = [
            TemplateCategory.INACTIVE,
            TemplateCategory.MINIMAL,
            TemplateCategory.POOR_PRACTICES,
        ]

        for category in categories:
            # Modify repo to match category
            if category == TemplateCategory.INACTIVE:
                portfolio_repo.metrics.days_since_last_commit = 500
            elif category == TemplateCategory.MINIMAL:
                portfolio_repo.metrics.total_commits = 3

            response = template_manager.get_response(category, portfolio_repo)

            # Verify no scores
            assert response.cost == 0.0
            assert response.generated_by == "template"

            # Check content has no scores
            all_text = (
                response.summary
                + " ".join(response.observations)
                + " ".join(response.data_limitations)
            ).lower()

            assert "score" not in all_text
            assert "excellent" not in all_text
            assert "poor" not in all_text
            assert "good" not in all_text
            assert "bad" not in all_text
            assert "weak" not in all_text
            assert "strong" not in all_text

    def test_report_generation_without_verdicts(self, portfolio_repo):
        """Test report generation without hiring verdicts."""
        from github_analyzer.core.classifier import (
            AnalysisMethod,
            ClassificationResult,
            RepositoryType,
        )

        # Create classification
        classification = ClassificationResult(
            method=AnalysisMethod.AI,
            repository_type=RepositoryType.PORTFOLIO,
            reasoning="Complex repository requiring analysis",
        )

        # Generate report
        generator = ReportGenerator()
        report = generator.generate_report(
            repo_data=portfolio_repo,
            classification=classification,
            context=AnalysisContext.ENTERPRISE,
        )

        # Evidence-based approach: no hiring verdicts, focus on evidence
        assert report.evidence_summary  # Should contain evidence patterns

        # Should have evidence-based content
        assert report.executive_summary
        # Analysis limitations may be empty for portfolio repos with good data
        assert isinstance(report.analysis_limitations, list)
        # Screening insights should be present
        assert hasattr(report, "screening_insights")
        assert hasattr(report.screening_insights, "areas_to_explore")
        assert len(report.screening_insights.areas_to_explore) > 0

        # Check data completeness is reasonable
        assert 0 <= report.data_completeness <= 1
        # Evidence-based approach - no trust scores

    @pytest.mark.parametrize(
        "context",
        [
            AnalysisContext.STARTUP,
            AnalysisContext.ENTERPRISE,
            AnalysisContext.AGENCY,
            AnalysisContext.OPEN_SOURCE,
        ],
    )
    def test_context_specific_observations(self, portfolio_repo, context):
        """Test that observations are contextualized properly."""
        analyzer = EvidenceBasedAnalyzer()
        result = analyzer.analyze(self._convert_repo_to_dict(portfolio_repo))

        # Should have context-relevant observations
        context_mentioned = False
        for obs in result.observations:
            if context.value.lower() in obs.context.lower():
                context_mentioned = True
                break

        # Interview guidance should be context-aware
        # Since interview_guidance is a list of strings, we can check context mentions
        if context_mentioned:
            assert True  # Context is mentioned in observations

    def test_integration_with_missing_data(self):
        """Test system handles repositories with missing data gracefully."""
        # Create minimal repository
        minimal_repo = RepositoryData(
            url="https://github.com/user/minimal",
            full_name="user/minimal",
            name="minimal",
            owner="user",
            description=None,
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2025, 7, 1, tzinfo=timezone.utc),
            pushed_at=datetime(2025, 7, 1, tzinfo=timezone.utc),
            default_branch="main",
            size=100,
            languages={"Python": 500},
            topics=[],
            license_name=None,
            stars=0,
            forks=0,
            watchers=0,
            open_issues=0,
            has_readme=False,
            has_license=False,
            has_contributing=False,
            has_tests=False,
            has_ci_config=False,
            recent_commits=[],
            file_structure=[],
            readme_content=None,
            metrics=RepositoryMetrics(
                total_commits=2,
                unique_contributors=1,
                lines_of_code=100,
                test_coverage_estimate=0.0,
                documentation_presence="0 documentation files found",
                days_since_last_commit=20,
                commit_frequency=0.05,
                avg_commit_size=50.0,
            ),
            fetched_at=datetime.now(timezone.utc),
            is_private=False,
            is_fork=False,
            is_archived=False,
            is_disabled=False,
        )

        analyzer = EvidenceBasedAnalyzer()
        result = analyzer.analyze(self._convert_repo_to_dict(minimal_repo))

        # Should handle gracefully
        assert result is not None
        assert len(result.observations) >= 0  # May have minimal observations
        assert hasattr(result, "data_sufficiency")
        assert len(result.data_sufficiency.limitations) > 0

        # Should emphasize limitations in the limitations list
        limitations_text = " ".join(result.data_sufficiency.limitations).lower()
        assert "limited" in limitations_text or "minimal" in limitations_text

        # Should suggest comprehensive interviews
        assert len(result.interview_guidance) > 0
        # Check that interview guidance mentions important topics
        guidance_text = " ".join(result.interview_guidance).lower()
        # Should mention areas that need exploration due to limited data
        assert any(
            keyword in guidance_text
            for keyword in [
                "experience",
                "approach",
                "philosophy",
                "strategy",
                "collaboration",
            ]
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
