"""
Test suite for Question Builder module.

Tests the generation of interview questions based on repository evidence,
including tier-based gating and context-aware question generation.
"""

import json
from typing import Any
from unittest.mock import Mock, patch

import pytest

from github_analyzer.core.evidence.question_builder import QuestionBuilder
from github_analyzer.core.tier_config import get_model_for_tier


class TestQuestionBuilder:
    """Test suite for question building functionality."""

    @pytest.fixture
    def question_builder(self) -> Any:
        """Create a QuestionBuilder instance with mocked API key."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            return QuestionBuilder(anthropic_api_key="test-key")

    @pytest.fixture
    def mock_evidence(self) -> Any:
        """Create comprehensive mock evidence data."""
        return {
            "technical_patterns": [
                {
                    "type": "language_expertise",
                    "finding": "Primary language Python (75% of codebase)",
                    "languages": {"Python": 15000, "JavaScript": 5000},
                    "insight": "Strong Python developer with some frontend experience",
                },
                {
                    "type": "test_coverage_structure",
                    "finding": "65% test coverage with unit and integration tests",
                    "ratio": "0.65",
                    "insight": "Good testing practices but room for improvement",
                },
                {
                    "type": "architecture",
                    "finding": "Uses microservices architecture with Docker",
                    "insight": "Experience with distributed systems",
                },
            ],
            "security_issues": [
                {
                    "type": "security_pattern",
                    "finding": "Potential SQL injection in user queries",
                    "severity": "high",
                    "commit_sha": "abc123",
                },
            ],
            "collaboration_patterns": [
                {
                    "type": "collaboration",
                    "finding": "Works primarily solo (1 contributor)",
                    "top_contributors": [("dev@example.com", 150)],
                    "insight": "Independent work style",
                },
            ],
            "quality_indicators": [
                {
                    "type": "code_maintenance",
                    "finding": "Regular refactoring (15 refactoring commits)",
                    "recent_refactor": "2024-01-15",
                    "insight": "Actively maintains code quality",
                },
            ],
            "behavioral_analysis": {
                "work_style": "consistent",
                "collaboration_level": "independent",
                "communication_quality": "detailed",
                "work_life_balance": "balanced",
                "leadership_potential": 0.4,
                "behavioral_insights": [
                    {
                        "type": "work_consistency",
                        "finding": "Highly consistent commit patterns",
                        "insight": "Reliable and predictable delivery",
                    },
                ],
            },
            "skill_evolution": {
                "skill_progression": "expanding",
                "growth_rate": 0.6,
                "recent_focus": "performance optimization",
                "temporal_insights": [
                    {
                        "type": "skill_growth",
                        "finding": "Added 3 new technologies in past 6 months",
                        "insight": "Continuous learner",
                    },
                ],
            },
        }

    @pytest.fixture
    def mock_insights(self) -> Any:
        """Create mock insights for testing."""
        return [
            {
                "category": "Technical Skills",
                "insight": "Strong Python developer with microservices experience",
                "confidence": 0.85,
                "evidence": [
                    "75% Python codebase",
                    "Docker usage",
                    "Microservices architecture",
                ],
            },
            {
                "category": "Work Style",
                "insight": "Independent contributor with consistent delivery patterns",
                "confidence": 0.70,
                "evidence": [
                    "Solo contributor",
                    "Regular commit schedule",
                    "Predictable velocity",
                ],
            },
            {
                "category": "Areas for Growth",
                "insight": "Security awareness needs improvement",
                "confidence": 0.80,
                "evidence": [
                    "SQL injection vulnerability found",
                    "Limited security-focused commits",
                ],
            },
            {
                "category": "Professional Practices",
                "insight": "Strong code maintenance habits with regular refactoring",
                "confidence": 0.75,
                "evidence": [
                    "15 refactoring commits",
                    "65% test coverage",
                    "Clean architecture",
                ],
            },
        ]

    def test_initialization(self, question_builder: Any) -> None:
        """Test QuestionBuilder initialization."""
        assert hasattr(question_builder, "anthropic_client")
        # Model is now determined dynamically based on tier
        assert hasattr(question_builder, "question_categories")

    def test_generate_questions_professional_tier(
        self, question_builder: Any, mock_evidence: Any, mock_insights: Any
    ) -> None:
        """Test question generation for PROFESSIONAL tier."""
        # Mock the Anthropic API response
        mock_response = Mock()
        mock_response.content = [
            Mock(
                text=json.dumps(
                    [
                        {
                            "category": "technical_decisions",
                            "question": "Can you explain your decision to use TypeScript in the dashboard project?",
                            "evidence_reference": "Evidence shows mixed language usage",
                            "follow_ups": [
                                "How do you handle type safety in mixed JS/TS projects?"
                            ],
                            "what_to_listen_for": "Understanding of type safety and practical approach",
                            "red_flags": ["No understanding of typing benefits"],
                            "context_relevance": "Important for startup environment",
                        },
                        {
                            "category": "collaboration_style",
                            "question": "How do you approach code reviews?",
                            "evidence_reference": "Multiple contributors in projects",
                            "follow_ups": [
                                "What's your process for giving constructive feedback?"
                            ],
                            "what_to_listen_for": "Collaborative approach and communication skills",
                            "red_flags": [
                                "Avoids code reviews",
                                "Poor feedback skills",
                            ],
                            "context_relevance": "Critical for team environment",
                        },
                    ]
                )
            )
        ]

        question_builder.anthropic_client.messages = Mock()
        question_builder.anthropic_client.messages.create = Mock(
            return_value=mock_response
        )

        result = question_builder.generate_questions(
            evidence=mock_evidence,
            context="startup",
            tier="professional",
        )

        # Should return the structured result with all_questions
        assert "all_questions" in result
        assert "context" in result
        assert result["context"] == "startup"

        # The actual implementation returns validated questions
        # Since we mocked the response, check the structure
        assert "total_questions" in result
        assert "estimated_time" in result
        assert "questions_by_category" in result

    def test_generate_questions_enterprise_tier(
        self, question_builder: Any, mock_evidence: Any, mock_insights: Any
    ) -> None:
        """Test question generation for ENTERPRISE tier."""
        # Mock the Anthropic API response with more questions for enterprise
        mock_response = Mock()
        mock_response.content = [
            Mock(
                text=json.dumps(
                    [
                        {
                            "category": "technical_decisions",
                            "question": "Can you explain your decision to use TypeScript?",
                            "evidence_reference": "Evidence shows mixed language usage",
                            "follow_ups": ["How do you handle type safety?"],
                            "what_to_listen_for": "Strategic thinking and technical depth",
                            "red_flags": ["No strategic reasoning"],
                            "context_relevance": "Important for enterprise architecture decisions",
                        },
                        {
                            "category": "collaboration_style",
                            "question": "How do you handle team conflicts?",
                            "evidence_reference": "Multiple contributors in projects",
                            "follow_ups": [
                                "What's your approach to consensus building?"
                            ],
                            "what_to_listen_for": "Leadership and conflict resolution skills",
                            "red_flags": ["Avoids conflict", "Poor leadership"],
                            "context_relevance": "Critical for enterprise team dynamics",
                        },
                        {
                            "category": "leadership_potential",
                            "question": "Tell me about a time you mentored someone.",
                            "evidence_reference": "Senior-level position",
                            "follow_ups": ["How do you measure mentoring success?"],
                            "what_to_listen_for": "Mentoring experience and growth mindset",
                            "red_flags": [
                                "No mentoring experience",
                                "Poor teaching skills",
                            ],
                            "context_relevance": "Essential for enterprise leadership roles",
                        },
                    ]
                )
            )
        ]

        question_builder.anthropic_client.messages = Mock()
        question_builder.anthropic_client.messages.create = Mock(
            return_value=mock_response
        )

        result = question_builder.generate_questions(
            evidence=mock_evidence,
            context="enterprise",
            tier="enterprise",
        )

        # Should return structured result
        assert "all_questions" in result
        assert "context" in result
        assert result["context"] == "enterprise"

    def test_generate_questions_basic_tier(
        self, question_builder: Any, mock_evidence: Any, mock_insights: Any
    ) -> None:
        """Test that BASIC tier gets questions."""
        # Mock the Anthropic API response
        mock_response = Mock()
        mock_response.content = [
            Mock(
                text=json.dumps(
                    [
                        {
                            "category": "technical_decisions",
                            "question": "What technologies do you prefer?",
                            "evidence_reference": "General assessment",
                            "follow_ups": ["Why those choices?"],
                            "what_to_listen_for": "Technical preferences and reasoning",
                            "red_flags": ["No clear preferences"],
                            "context_relevance": "Important for agency project matching",
                        }
                    ]
                )
            )
        ]

        question_builder.anthropic_client.messages = Mock()
        question_builder.anthropic_client.messages.create = Mock(
            return_value=mock_response
        )

        result = question_builder.generate_questions(
            evidence=mock_evidence,
            context="agency",
            tier="basic",
        )

        # Basic tier should get questions
        assert "all_questions" in result
        assert result["total_questions"] >= 0

    def test_generate_questions_free_tier(
        self, question_builder: Any, mock_evidence: Any, mock_insights: Any
    ) -> None:
        """Test that FREE tier still works."""
        # Mock the Anthropic API response
        mock_response = Mock()
        mock_response.content = [Mock(text=json.dumps([]))]

        question_builder.anthropic_client.messages = Mock()
        question_builder.anthropic_client.messages.create = Mock(
            return_value=mock_response
        )

        result = question_builder.generate_questions(
            evidence=mock_evidence,
            context="open_source",
            tier="free",
        )

        # Free tier should still return structured response
        assert "all_questions" in result
        assert "context" in result

    def test_anthropic_api_integration(
        self, question_builder: Any, mock_evidence: Any
    ) -> None:
        """Test that Anthropic API is called correctly."""
        # Mock Haiku response with the expected structure
        mock_response = Mock()
        mock_response.content = [
            Mock(
                text=json.dumps(
                    [
                        {
                            "category": "technical_decisions",
                            "question": "Can you walk me through your experience with microservices architecture?",
                            "evidence_reference": "Repository shows Docker usage and service separation",
                            "follow_ups": [
                                "How do you handle service communication?",
                                "What's your approach to service discovery?",
                            ],
                            "what_to_listen_for": "Practical microservices experience and architectural understanding",
                            "red_flags": [
                                "No understanding of distributed systems",
                                "Over-complicated architecture",
                            ],
                            "context_relevance": "Critical for startup scalability planning",
                        },
                        {
                            "category": "quality_practices",
                            "question": "How do you typically handle user input validation in your applications?",
                            "evidence_reference": "Found potential SQL injection vulnerability",
                            "follow_ups": [
                                "What security tools do you use?",
                                "How do you stay updated on security best practices?",
                            ],
                            "what_to_listen_for": "Security awareness and preventive practices",
                            "red_flags": [
                                "No security considerations",
                                "Dismissive of security",
                            ],
                            "context_relevance": "Essential for startup data protection",
                        },
                    ]
                )
            )
        ]

        # Mock the API call
        question_builder.anthropic_client.messages = Mock()
        question_builder.anthropic_client.messages.create = Mock(
            return_value=mock_response
        )

        # Call the public method
        result = question_builder.generate_questions(
            evidence=mock_evidence, context="startup", tier="professional"
        )

        # Verify the API was called
        question_builder.anthropic_client.messages.create.assert_called_once()

        # Verify the result structure
        assert "all_questions" in result
        assert "questions_by_category" in result
        assert result["context"] == "startup"

    def test_error_handling(self, question_builder: Any, mock_evidence: Any) -> None:
        """Test error handling when API fails."""
        # Mock API failure
        question_builder.anthropic_client.messages = Mock()
        question_builder.anthropic_client.messages.create = Mock(
            side_effect=Exception("API Error")
        )

        # Should fall back to rule-based generation
        result = question_builder.generate_questions(
            evidence=mock_evidence,
            context="startup",
            tier="professional",
        )

        # Should still return a valid result (falls back to rule-based)
        assert "all_questions" in result
        assert "context" in result
        assert result["context"] == "startup"

    def test_question_structure(
        self, question_builder: Any, mock_evidence: Any
    ) -> None:
        """Test that generated questions have proper structure."""
        # Mock a successful API response
        mock_response = Mock()
        mock_response.content = [
            Mock(
                text=json.dumps(
                    [
                        {
                            "category": "technical_decisions",
                            "question": "Describe your Python experience",
                            "evidence_reference": "Strong Python usage detected",
                            "follow_ups": ["What frameworks?", "Any async experience?"],
                            "what_to_listen_for": "Depth of Python knowledge and practical experience",
                            "red_flags": [
                                "No framework experience",
                                "Only basic Python",
                            ],
                            "context_relevance": "Critical for agency project requirements",
                        }
                    ]
                )
            )
        ]

        question_builder.anthropic_client.messages = Mock()
        question_builder.anthropic_client.messages.create = Mock(
            return_value=mock_response
        )

        result = question_builder.generate_questions(
            evidence=mock_evidence, context="agency", tier="professional"
        )

        # Verify the structure includes all expected fields
        assert "all_questions" in result
        assert "questions_by_category" in result
        assert "interview_flow" in result
        assert "key_areas_covered" in result
        assert "estimated_time" in result

    def test_question_categories(self, question_builder: Any) -> None:
        """Test that question categories are properly defined."""
        # Check that the question builder has proper categories
        assert hasattr(question_builder, "question_categories")
        assert len(question_builder.question_categories) > 0

        # Should include essential categories
        assert "technical_decisions" in question_builder.question_categories
        assert "collaboration_style" in question_builder.question_categories
        assert "problem_solving" in question_builder.question_categories
        assert "growth_mindset" in question_builder.question_categories

    def test_fallback_questions(self, question_builder: Any) -> None:
        """Test fallback questions when all else fails."""
        # Test the fallback method directly
        questions = question_builder._generate_fallback_questions_list({})

        # Should return a list of fallback questions
        assert isinstance(questions, list)
        assert len(questions) >= 3  # Should have at least 3 fallback questions

        # Check that each fallback question has proper structure
        for question in questions:
            assert "category" in question
            assert "question" in question
            assert "evidence_reference" in question
            assert "follow_ups" in question
            assert "what_to_listen_for" in question
            assert "red_flags" in question
            assert "context_relevance" in question

    def test_handling_api_errors(
        self, question_builder: Any, mock_evidence: Any, mock_insights: Any
    ) -> None:
        """Test graceful handling of API errors."""
        # Mock API failure
        question_builder.anthropic_client.messages = Mock()
        question_builder.anthropic_client.messages.create = Mock(
            side_effect=Exception("API Error")
        )

        # Should fallback to rule-based generation
        result = question_builder.generate_questions(
            evidence=mock_evidence,
            context="startup",
            tier="professional",
        )

        # Should still return valid structured result
        assert "all_questions" in result
        assert "context" in result
        assert result["context"] == "startup"

    def test_question_validation(self, question_builder: Any) -> None:
        """Test that questions are properly validated."""
        # Test _validate_questions method with mock data
        raw_questions = [
            {
                "category": "technical_decisions",
                "question": "How do you approach microservices architecture design?",
                "evidence_reference": "Repository shows microservices with Docker",
                "follow_ups": [
                    "What about service mesh?",
                    "How do you handle transactions?",
                ],
                "what_to_listen_for": "Architectural understanding",
                "red_flags": ["No distributed systems knowledge"],
                "context_relevance": "Important for startup scalability",
            },
            {
                "category": "technical_decisions",
                "question": "",  # Empty question should be filtered out
                "evidence_reference": "Test",
                "follow_ups": [],
                "what_to_listen_for": "Test",
                "red_flags": [],
                "context_relevance": "Test",
            },
        ]

        validated = question_builder._validate_questions(raw_questions, {})

        # Should filter out empty question
        assert len(validated) == 1
        assert "microservices" in validated[0]["question"]

    def test_evidence_summary_preparation(
        self, question_builder: Any, mock_evidence: Any
    ) -> None:
        """Test that evidence is properly summarized for question generation."""
        summary = question_builder._prepare_evidence_summary(mock_evidence)

        # Should extract key evidence categories
        assert "key_findings" in summary
        assert "red_flags" in summary
        assert "positive_signals" in summary
        assert "behavioral_patterns" in summary
        assert "technical_patterns" in summary
        assert "temporal_insights" in summary

        # Should have found some evidence
        assert len(summary["key_findings"]) > 0
        assert len(summary["positive_signals"]) > 0

    def test_rule_based_question_generation(
        self, question_builder: Any, mock_evidence: Any
    ) -> None:
        """Test rule-based question generation as fallback."""
        # Prepare evidence summary
        evidence_summary = question_builder._prepare_evidence_summary(mock_evidence)

        # Test rule-based generation
        questions = question_builder._generate_rule_based_questions(
            evidence_summary, "startup"
        )

        # Should generate questions based on evidence
        assert len(questions) > 0

        # Should have proper structure
        for question in questions:
            assert "category" in question
            assert "question" in question
            assert "evidence_reference" in question
            assert "follow_ups" in question
            assert "what_to_listen_for" in question
            assert "red_flags" in question
            assert "context_relevance" in question

    def test_interview_flow_generation(self, question_builder: Any) -> None:
        """Test that interview flow is properly generated."""
        # Mock some questions
        mock_questions = [
            {
                "category": "work_patterns",
                "question": "Test work patterns question",
                "priority": "medium",
            },
            {
                "category": "technical_decisions",
                "question": "Test technical question",
                "priority": "high",
            },
            {
                "category": "collaboration_style",
                "question": "Test collaboration question",
                "priority": "medium",
            },
        ]

        # Test interview flow generation
        flow = question_builder._suggest_interview_flow(mock_questions)

        # Should return a list of flow steps
        assert isinstance(flow, list)
        assert len(flow) > 0

        # Should contain guidance for interview structure
        flow_text = " ".join(flow)
        assert "work patterns" in flow_text.lower() or "technical" in flow_text.lower()

    @patch("anthropic.Anthropic")
    def test_dual_model_for_professional_tier(
        self, mock_anthropic_class: Any, question_builder: Any
    ) -> None:
        """Test that PROFESSIONAL tier uses Haiku 3.5 for questions."""
        evidence_summary = {
            "key_findings": ["Test finding 1", "Test finding 2"],
            "strengths": ["Good practices", "Clean code"],
            "concerns": ["Limited tests"],
            "behavioral_patterns": ["Consistent commits", "Regular reviews"],
            "temporal_insights": ["Growing expertise", "Recent activity"],
            "red_flags": ["Some security issues"],
            "positive_signals": ["Active maintenance", "Good documentation"],
            "technical_patterns": ["Modern stack", "Best practices"],
        }

        # Mock Haiku 3.5 response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [
            Mock(
                text='[{"category": "technical", "question": "Test question", "evidence_reference": "Test re", "green_flags": ["Flag1", "Flag2"], "red_flags": ["Flag3"], "what_to_listen_for": "Listen for..."}]'
            )
        ]
        mock_client.messages.create.return_value = mock_response
        question_builder.anthropic_client = mock_client

        # Generate questions for PROFESSIONAL tier
        questions = question_builder._generate_professional_haiku35_questions(
            evidence_summary, "startup"
        )

        # Model comes from configuration, not the tier.
        mock_client.messages.create.assert_called()
        call_args = mock_client.messages.create.call_args
        assert call_args.kwargs["model"] == get_model_for_tier("professional")
        assert (
            call_args.kwargs["max_tokens"] == 16000
        )  # PROFESSIONAL uses 16000 tokens from tier_config (upgraded with Haiku 4.5)

        # Should return valid questions
        assert len(questions) > 0
        assert questions[0]["category"] == "technical"

    @patch("anthropic.Anthropic")
    def test_dual_model_for_enterprise_tier(
        self, mock_anthropic_class: Any, question_builder: Any
    ) -> None:
        """Test that ENTERPRISE tier uses Sonnet 3.5 for questions."""
        evidence_summary = {
            "key_findings": ["Executive finding 1", "Strategic finding 2"],
            "strengths": ["Leadership qualities", "Strategic thinking"],
            "concerns": ["Scale limitations"],
            "behavioral_patterns": ["Leadership behaviors", "Strategic patterns"],
            "temporal_insights": ["Career progression", "Recent initiatives"],
            "red_flags": ["Scalability concerns"],
            "positive_signals": ["Strong leadership", "Vision"],
            "technical_patterns": ["Enterprise architecture", "System design"],
        }

        # Mock Sonnet 3.5 response
        mock_client = Mock()
        import anthropic.types

        mock_text_block = Mock(spec=anthropic.types.TextBlock)
        mock_text_block.text = '[{"category": "strategic_thinking", "question": "Executive question", "evidence_reference": "Strategic re", "green_flags": ["Leader1", "Leader2", "Leader3"], "red_flags": ["Risk1", "Risk2"], "what_to_listen_for": "Executive thinking...", "context_relevance": "Enterprise context", "executive_focus": "Leadership", "follow_up_probes": ["Probe1", "Probe2"]}]'

        mock_response = Mock()
        mock_response.content = [mock_text_block]
        mock_client.messages.create.return_value = mock_response
        question_builder.anthropic_client = mock_client

        # Generate questions for ENTERPRISE tier
        questions = question_builder._generate_enterprise_dual_questions(
            evidence_summary, "enterprise"
        )

        # Model comes from configuration, not the tier, so assert it matches
        # what tier_config resolves rather than a pinned ID.
        mock_client.messages.create.assert_called()
        call_args = mock_client.messages.create.call_args
        assert call_args.kwargs["model"] == get_model_for_tier("enterprise")
        assert (
            call_args.kwargs["max_tokens"] == 20000
        )  # ENTERPRISE uses 20000 tokens from tier_config

        # Should return executive-level questions
        assert len(questions) > 0
        assert questions[0]["category"] == "strategic_thinking"
        assert (
            "follow_ups" in questions[0]
        )  # Enterprise questions have follow-ups (validated format)
