"""
Tests for PR context-specific prompts.
"""

from src.github_analyzer.core.pr_context_prompts import (
    PR_CONTEXT_PROMPTS,
    enhance_pr_evidence_with_context,
    get_pr_context_prompt,
)


class TestPRContextPrompts:
    """Test PR context prompt functionality."""

    def test_all_contexts_have_prompts(self):
        """Test that all required contexts have prompts defined."""
        required_contexts = ["STARTUP", "ENTERPRISE", "AGENCY", "OPEN_SOURCE"]
        for context in required_contexts:
            assert context in PR_CONTEXT_PROMPTS
            assert len(PR_CONTEXT_PROMPTS[context]) > 100  # Non-trivial prompt

    def test_startup_prompt_content(self):
        """Test startup prompt contains key elements."""
        prompt = PR_CONTEXT_PROMPTS["STARTUP"]
        assert "MVP mindset" in prompt
        assert "velocity" in prompt
        assert "adaptability" in prompt
        assert "Use only evidence provided" in prompt

    def test_enterprise_prompt_content(self):
        """Test enterprise prompt contains key elements."""
        prompt = PR_CONTEXT_PROMPTS["ENTERPRISE"]
        assert "scale" in prompt.lower()
        assert "process adherence" in prompt.lower()
        assert "review cycle" in prompt.lower()
        assert "Use only evidence provided" in prompt

    def test_agency_prompt_content(self):
        """Test agency prompt contains key elements."""
        prompt = PR_CONTEXT_PROMPTS["AGENCY"]
        assert "multi-project" in prompt.lower()
        assert "client-ready" in prompt.lower()
        assert "context switching" in prompt.lower()
        assert "Use only evidence provided" in prompt

    def test_open_source_prompt_content(self):
        """Test open source prompt contains key elements."""
        prompt = PR_CONTEXT_PROMPTS["OPEN_SOURCE"]
        assert "community" in prompt.lower()
        assert "documentation" in prompt.lower()
        assert "feedback" in prompt.lower()
        assert "Use only evidence provided" in prompt

    def test_get_pr_context_prompt(self):
        """Test getting prompts by context name."""
        # Test exact match
        startup_prompt = get_pr_context_prompt("STARTUP")
        assert startup_prompt == PR_CONTEXT_PROMPTS["STARTUP"]

        # Test case insensitivity
        enterprise_prompt = get_pr_context_prompt("enterprise")
        assert enterprise_prompt == PR_CONTEXT_PROMPTS["ENTERPRISE"]

        # Test mixed case
        agency_prompt = get_pr_context_prompt("Agency")
        assert agency_prompt == PR_CONTEXT_PROMPTS["AGENCY"]

    def test_get_pr_context_prompt_default(self):
        """Test default prompt for unknown context."""
        # Unknown context should return OPEN_SOURCE
        default_prompt = get_pr_context_prompt("UNKNOWN")
        assert default_prompt == PR_CONTEXT_PROMPTS["OPEN_SOURCE"]

        # Empty string should also return OPEN_SOURCE
        empty_prompt = get_pr_context_prompt("")
        assert empty_prompt == PR_CONTEXT_PROMPTS["OPEN_SOURCE"]

    def test_enhance_pr_evidence_with_context(self):
        """Test enhancing evidence with context."""
        evidence = "User has 50 merged PRs across 10 repositories."

        # Test startup context
        enhanced = enhance_pr_evidence_with_context(evidence, "STARTUP")
        assert "STARTUP" in enhanced
        assert evidence in enhanced
        assert "MVP mindset" in enhanced
        assert "Based on the evidence above" in enhanced

    def test_enhance_different_contexts(self):
        """Test that different contexts produce different enhancements."""
        evidence = "Consistent contributions over 2 years."

        startup_enhanced = enhance_pr_evidence_with_context(evidence, "STARTUP")
        enterprise_enhanced = enhance_pr_evidence_with_context(evidence, "ENTERPRISE")

        # They should be different
        assert startup_enhanced != enterprise_enhanced

        # Each should contain its context
        assert "velocity" in startup_enhanced.lower()
        assert "scale" in enterprise_enhanced.lower()

    def test_no_behavioral_inference_reminder(self):
        """Test that all prompts include the no-inference reminder."""
        for context_name, prompt in PR_CONTEXT_PROMPTS.items():
            assert (
                "Use only evidence provided" in prompt
                or "No behavioral inferences" in prompt
            ), f"{context_name} prompt missing evidence-only reminder"

    def test_evidence_enhancement_structure(self):
        """Test the structure of enhanced evidence."""
        evidence = "Test evidence"
        enhanced = enhance_pr_evidence_with_context(evidence, "AGENCY")

        # Check structure elements
        assert "EXTRACTED PR EVIDENCE:" in enhanced
        assert "Based on the evidence above" in enhanced
        assert "1. Key strengths" in enhanced
        assert "2. Areas where evidence" in enhanced
        assert "3. Patterns that deserve" in enhanced
        assert "4. Specific PRs" in enhanced

    def test_prompt_length_reasonable(self):
        """Test that prompts are reasonable length."""
        for context_name, prompt in PR_CONTEXT_PROMPTS.items():
            # Should be substantial but not excessive
            assert 200 < len(prompt) < 2000, (
                f"{context_name} prompt length {len(prompt)} out of range"
            )
