"""
Tests for PR Insights Generator.

Tests the AI-powered insights generation from PR evidence.
"""

import json
from unittest.mock import Mock, patch

import pytest

from src.github_analyzer.ai.pr_insights_generator import PRInsightsGenerator
from src.github_analyzer.data.pr_models import PREvidence, QualitySignals


@pytest.fixture
def pr_insights_generator():
    """Create PR insights generator instance."""
    return PRInsightsGenerator("test-api-key")


@pytest.fixture
def sample_evidence():
    """Create sample PR evidence for testing."""
    return PREvidence(
        technical_substance=[
            "Production Integration Success: 45/50 PRs merged successfully",
            "Implemented OAuth2 authentication system (PR #123)",
            "Refactored payment processing for 3x performance (PR #456)",
            "Added comprehensive test suite with 95% coverage",
            "Migrated database from PostgreSQL 11 to 14",
        ],
        collaboration_patterns=[
            "Average review response time: 2 hours",
            "Co-authored 12 PRs with 5 different team members",
            "Provided detailed review feedback on 30+ PRs",
            "Led architecture discussions in 8 major PRs",
            "Mentored junior developers in 15 PRs",
        ],
        review_responsiveness=[
            "Responded to 95% of review comments within 4 hours",
            "Implemented reviewer suggestions in 85% of cases",
            "Average iteration count: 2.3 before merge",
        ],
        cross_repo_contributions=[
            "Contributed to 8 different repositories",
            "Cross-team collaboration on shared libraries",
            "Standardized CI/CD across 3 repositories",
        ],
        areas_to_explore=[
            "Limited frontend contributions (only 5 PRs)",
            "No evidence of mobile development",
            "Security practices not explicitly documented",
            "Performance testing methodology unclear",
            "Documentation patterns inconsistent",
        ],
    )


@pytest.fixture
def sample_quality_signals():
    """Create sample quality signals for testing."""
    return QualitySignals(
        total_prs=50,
        merged_prs=45,
        unique_repos=8,
        contribution_timespan="2 years 3 months",
        feature_prs=25,
        fix_prs=15,
    )


@pytest.fixture
def successful_ai_response():
    """Create a successful AI response with comprehensive insights."""
    return json.dumps(
        {
            "interview_questions": [
                {
                    "question": "In PR #123, you implemented OAuth2 authentication. Walk me through your security considerations.",
                    "category": "technical",
                    "evidence_reference": "PR #123 - OAuth2 authentication system",
                    "context_note": "Security is critical for startup customer trust",
                    "follow_up_questions": [
                        "How did you handle token refresh?",
                        "What measures did you take against CSRF attacks?",
                        "How did you test the security implementation?",
                    ],
                    "key_listening_points": "Understanding of security principles and practical implementation",
                },
                {
                    "question": "PR #456 shows a 3x performance improvement. How did you identify and solve this bottleneck?",
                    "category": "technical",
                    "evidence_reference": "PR #456 - Payment processing refactor",
                    "context_note": "Performance optimization crucial for scale",
                    "follow_up_questions": [
                        "What profiling tools did you use?",
                        "How did you validate the improvement?",
                        "What trade-offs did you consider?",
                    ],
                    "key_listening_points": "Systematic approach to performance optimization",
                },
            ]
            + [
                {
                    "question": f"Question {i}",
                    "category": "collaboration",
                    "evidence_reference": f"Evidence {i}",
                    "context_note": f"Context {i}",
                    "follow_up_questions": ["F1", "F2", "F3"],
                    "key_listening_points": f"Listening point {i}",
                }
                for i in range(3, 11)
            ],
            "key_strengths": [
                "Strong production integration success rate (90% merge rate)",
                "Excellent collaboration with 2-hour average response time",
                "Deep technical expertise in authentication and security",
                "Performance optimization skills (3x improvement achieved)",
                "Test-driven development with 95% coverage",
                "Cross-team collaboration across 8 repositories",
                "Mentorship and knowledge sharing evident",
            ],
            "technical_capabilities": [
                "OAuth2 and authentication systems",
                "Payment processing systems",
                "PostgreSQL database administration",
                "Performance profiling and optimization",
                "Test automation and coverage",
                "CI/CD pipeline configuration",
                "Database migration strategies",
            ],
            "collaboration_style": [
                "Highly responsive to code reviews (2-hour average)",
                "Active mentor to junior developers",
                "Constructive feedback provider",
                "Cross-team collaboration leader",
                "Clear technical communication",
            ],
            "code_quality_indicators": [
                "95% test coverage achievement",
                "Consistent refactoring for performance",
                "Clean architecture patterns",
                "Comprehensive documentation",
                "Security-conscious implementation",
            ],
            "areas_for_discussion": [
                "Frontend development experience gaps",
                "Mobile development capabilities",
                "Security testing methodologies",
                "Performance testing strategies",
                "Documentation standardization approach",
            ],
            "notable_contributions": [
                "OAuth2 authentication system implementation",
                "3x performance improvement in payment processing",
                "PostgreSQL 11 to 14 migration leadership",
            ],
            "context_fit": {
                "alignment": "strong",
                "supporting_evidence": [
                    "High velocity with 25 feature PRs",
                    "Rapid iteration with 2.3 average iterations",
                    "Full-stack capability demonstrated",
                    "Strong ownership of critical systems",
                    "Startup-friendly fast response times",
                ],
                "considerations": [
                    "May need frontend skill development",
                    "Mobile experience would be beneficial",
                    "Security practices need documentation",
                ],
                "specific_strengths_for_context": [
                    "Fast iteration cycles perfect for startup",
                    "Critical system ownership capability",
                    "Strong technical depth for scaling",
                ],
            },
        }
    )


class TestPRInsightsGenerator:
    """Test PR Insights Generator."""

    def test_init_with_api_key(self, pr_insights_generator):
        """Test initialization with API key."""
        assert pr_insights_generator.anthropic is not None
        assert pr_insights_generator.anthropic.api_key == "test-api-key"

    @patch("src.github_analyzer.ai.pr_insights_generator.get_token_limit")
    @patch("src.github_analyzer.core.tier_config.get_tier_config")
    @patch("src.github_analyzer.ai.pr_insights_generator.get_model_for_tier")
    @patch(
        "src.github_analyzer.ai.pr_insights_generator.enhance_pr_evidence_with_context"
    )
    @patch("src.github_analyzer.ai.pr_insights_generator.AnthropicWrapper")
    def test_generate_insights_success(
        self,
        mock_anthropic_class,
        mock_enhance_context,
        mock_get_model,
        mock_get_tier_config,
        mock_get_token_limit,
        sample_evidence,
        sample_quality_signals,
        successful_ai_response,
    ):
        """Test successful insights generation."""
        # Setup mocks
        mock_anthropic = Mock()
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = successful_ai_response
        mock_anthropic.create_message = Mock(return_value=mock_response)
        mock_anthropic_class.return_value = mock_anthropic

        # Mock tier config
        mock_tier_config = Mock()
        mock_tier_config.max_tokens_main = 4096
        mock_get_tier_config.return_value = mock_tier_config
        mock_get_model.return_value = "claude-3-sonnet-20240229"
        mock_get_token_limit.return_value = 32000  # Scale+ tier token limit

        # Mock context enhancement
        mock_enhance_context.return_value = "Enhanced evidence for STARTUP"

        # Create generator
        generator = PRInsightsGenerator("test-api-key")

        # Generate insights
        result = generator.generate_insights(
            username="testuser",
            evidence=sample_evidence,
            quality_signals=sample_quality_signals,
            context="STARTUP",
            tier="scale_plus",
        )

        # Verify result
        assert result["success"] is True
        assert "insights" in result
        insights = result["insights"]

        # Verify interview questions
        assert len(insights["interview_questions"]) >= 10
        assert insights["interview_questions"][0]["category"] == "technical"
        assert "follow_up_questions" in insights["interview_questions"][0]
        assert len(insights["interview_questions"][0]["follow_up_questions"]) == 3

        # Verify other sections
        assert len(insights["key_strengths"]) >= 7
        assert len(insights["technical_capabilities"]) >= 7
        assert len(insights["collaboration_style"]) >= 5
        assert len(insights["areas_for_discussion"]) >= 5

        # Verify context fit
        assert insights["context_fit"]["alignment"] == "strong"
        assert len(insights["context_fit"]["supporting_evidence"]) >= 5

        # Verify API call
        mock_anthropic.create_message.assert_called_once()
        call_args, call_kwargs = mock_anthropic.create_message.call_args
        # Verify the context enhancement was called with correct parameters
        mock_enhance_context.assert_called_once()
        # The enhanced content should be in the API call
        assert (
            mock_enhance_context.return_value in call_kwargs["messages"][0]["content"]
        )
        # Verify correct model and settings were used
        assert call_kwargs["model"] == "claude-3-sonnet-20240229"
        # Scale+ tier uses 32000 tokens (from tier_config.py)
        assert call_kwargs["max_tokens"] == 32000

    @patch("src.github_analyzer.core.tier_config.get_tier_config")
    @patch("src.github_analyzer.ai.pr_insights_generator.get_model_for_tier")
    @patch(
        "src.github_analyzer.ai.pr_insights_generator.enhance_pr_evidence_with_context"
    )
    @patch("src.github_analyzer.ai.pr_insights_generator.AnthropicWrapper")
    def test_generate_insights_json_parse_error(
        self,
        mock_anthropic_class,
        mock_enhance_context,
        mock_get_model,
        mock_get_tier_config,
        sample_evidence,
        sample_quality_signals,
    ):
        """Test handling of JSON parse errors."""
        # Setup mocks with invalid JSON response
        mock_anthropic = Mock()
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = "This is not valid JSON"
        mock_anthropic.create_message = Mock(return_value=mock_response)
        mock_anthropic_class.return_value = mock_anthropic

        # Mock tier config
        mock_tier_config = Mock()
        mock_tier_config.max_tokens_main = 4096
        mock_get_tier_config.return_value = mock_tier_config
        mock_get_model.return_value = "claude-3-sonnet-20240229"
        mock_enhance_context.return_value = "Enhanced evidence"

        # Create generator
        generator = PRInsightsGenerator("test-api-key")

        # Generate insights
        result = generator.generate_insights(
            username="testuser",
            evidence=sample_evidence,
            quality_signals=sample_quality_signals,
            context="STARTUP",
            tier="scale_plus",
        )

        # Verify fallback response
        assert result["success"] is False
        assert "Failed to parse AI response" in result["error"]
        assert "insights" in result
        assert result["insights"]["interview_questions"][0]["question"] is not None

    @patch("src.github_analyzer.core.tier_config.get_tier_config")
    @patch("src.github_analyzer.ai.pr_insights_generator.get_model_for_tier")
    @patch(
        "src.github_analyzer.ai.pr_insights_generator.enhance_pr_evidence_with_context"
    )
    @patch("src.github_analyzer.ai.pr_insights_generator.AnthropicWrapper")
    def test_generate_insights_api_error(
        self,
        mock_anthropic_class,
        mock_enhance_context,
        mock_get_model,
        mock_get_tier_config,
        sample_evidence,
        sample_quality_signals,
    ):
        """Test handling of API errors."""
        # Setup mocks with exception
        mock_anthropic = Mock()
        mock_anthropic.create_message = Mock(side_effect=Exception("API Error"))
        mock_anthropic_class.return_value = mock_anthropic

        # Mock tier config
        mock_tier_config = Mock()
        mock_tier_config.max_tokens_main = 4096
        mock_get_tier_config.return_value = mock_tier_config
        mock_get_model.return_value = "claude-3-sonnet-20240229"
        mock_enhance_context.return_value = "Enhanced evidence"

        # Create generator
        generator = PRInsightsGenerator("test-api-key")

        # Generate insights
        result = generator.generate_insights(
            username="testuser",
            evidence=sample_evidence,
            quality_signals=sample_quality_signals,
            context="ENTERPRISE",
            tier="scale_plus",
        )

        # Verify error handling
        assert result["success"] is False
        assert "API Error" in result["error"]
        assert "insights" in result  # Fallback insights provided

    def test_build_evidence_summary(
        self, pr_insights_generator, sample_evidence, sample_quality_signals
    ):
        """Test building evidence summary."""
        summary = pr_insights_generator._build_evidence_summary(
            username="testuser",
            evidence=sample_evidence,
            quality_signals=sample_quality_signals,
            repos_contributed=[
                "repo1",
                "repo2",
                "repo3",
                "repo4",
                "repo5",
                "repo6",
                "repo7",
                "repo8",
            ],
        )

        # Verify summary content
        assert "PR ANALYSIS EVIDENCE FOR: testuser" in summary
        assert "Total PRs analyzed: 50" in summary
        assert "PRs merged: 45" in summary
        assert "Repositories: 8" in summary
        assert "Feature PRs: 25" in summary

        # Verify evidence sections
        assert "TECHNICAL PATTERNS:" in summary
        assert "Production Integration Success" in summary
        assert "COLLABORATION PATTERNS:" in summary
        assert "Average review response time" in summary
        assert "CROSS-REPOSITORY WORK:" in summary
        assert "Contributed to 8 different repositories" in summary

    def test_get_fallback_insights(self, pr_insights_generator):
        """Test fallback insights structure."""
        insights = pr_insights_generator._get_fallback_insights()

        # Verify structure
        assert "interview_questions" in insights
        assert len(insights["interview_questions"]) >= 1
        assert "question" in insights["interview_questions"][0]
        assert "follow_up_questions" in insights["interview_questions"][0]

        assert "key_strengths" in insights
        assert "technical_capabilities" in insights
        assert "collaboration_style" in insights
        assert "code_quality_indicators" in insights
        assert "areas_for_discussion" in insights
        assert "notable_contributions" in insights
        assert "context_fit" in insights

        # Verify context fit structure
        assert "alignment" in insights["context_fit"]
        assert "supporting_evidence" in insights["context_fit"]
        assert "considerations" in insights["context_fit"]

    @patch("src.github_analyzer.ai.pr_insights_generator.get_token_limit")
    @patch("src.github_analyzer.ai.pr_insights_generator.get_model_for_tier")
    @patch("src.github_analyzer.ai.pr_insights_generator.AnthropicWrapper")
    def test_tier_based_model_selection(
        self,
        mock_anthropic_class,
        mock_get_model,
        mock_get_token_limit,
        sample_evidence,
        sample_quality_signals,
        successful_ai_response,
    ):
        """Test that correct model is selected based on tier."""
        # Setup mocks
        mock_get_model.return_value = "claude-3-sonnet-20240229"
        mock_get_token_limit.return_value = 32000  # Scale+ tier token limit

        mock_anthropic = Mock()
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = successful_ai_response
        mock_anthropic.create_message = Mock(return_value=mock_response)
        mock_anthropic_class.return_value = mock_anthropic

        # Create generator and generate insights
        generator = PRInsightsGenerator("test-api-key")
        generator.generate_insights(
            username="testuser",
            evidence=sample_evidence,
            quality_signals=sample_quality_signals,
            context="STARTUP",
            tier="scale_plus",
        )

        # Verify correct model was requested (default model_type="main")
        mock_get_model.assert_called_with("scale_plus")

        # Verify model was used
        call_args = mock_anthropic.create_message.call_args
        assert call_args[1]["model"] == "claude-3-sonnet-20240229"
        # Scale+ tier uses 32000 tokens (from tier_config.py)
        assert call_args[1]["max_tokens"] == 32000

    @patch("src.github_analyzer.core.tier_config.get_tier_config")
    @patch("src.github_analyzer.ai.pr_insights_generator.get_model_for_tier")
    @patch(
        "src.github_analyzer.ai.pr_insights_generator.enhance_pr_evidence_with_context"
    )
    @patch("src.github_analyzer.ai.pr_insights_generator.AnthropicWrapper")
    def test_context_enhancement(
        self,
        mock_anthropic_class,
        mock_enhance_context,
        mock_get_model,
        mock_get_tier_config,
        sample_evidence,
        sample_quality_signals,
        successful_ai_response,
    ):
        """Test that context enhancement is applied."""
        # Setup mocks
        mock_enhance_context.return_value = "Enhanced evidence with AGENCY context"
        mock_anthropic = Mock()
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = successful_ai_response
        mock_anthropic.create_message = Mock(return_value=mock_response)
        mock_anthropic_class.return_value = mock_anthropic

        # Mock tier config
        mock_tier_config = Mock()
        mock_tier_config.max_tokens_main = 4096
        mock_get_tier_config.return_value = mock_tier_config
        mock_get_model.return_value = "claude-3-sonnet-20240229"

        # Generate insights with specific context
        generator = PRInsightsGenerator("test-api-key")
        generator.generate_insights(
            username="contractor",
            evidence=sample_evidence,
            quality_signals=sample_quality_signals,
            context="AGENCY",
            tier="scale_plus",
        )

        # Verify context enhancement was called
        mock_enhance_context.assert_called_once()
        call_args = mock_enhance_context.call_args[0]
        assert "contractor" in call_args[0]
        assert call_args[1] == "AGENCY"

        # Verify enhanced prompt was used
        ai_call_args = mock_anthropic.create_message.call_args[1]["messages"][0][
            "content"
        ]
        assert "Enhanced evidence with AGENCY context" in ai_call_args
