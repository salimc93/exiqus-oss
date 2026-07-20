# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Advanced analysis strategy for Professional, Enterprise, and Scale+ tiers.
Uses Markdown-based prompting, "Glass House" logging, and sophisticated models.
"""

import json
from typing import Any, Dict

from ....ai.evidence_based_prompts import UNIFIED_INSIGHTS_AND_QUESTIONS_PROMPT
from ....utils.logging import get_logger
from ...tier_config import get_model_for_tier, get_target_ranges, get_token_limit
from .analysis_strategy import AnalysisStrategy

logger = get_logger(__name__)


class AdvancedAnalysisStrategy(AnalysisStrategy):
    """Strategy for advanced tiers (Professional, Enterprise, Scale+)."""

    def analyze(
        self,
        repo_data: Any,
        context: Any,
        tier: str,
        anthropic_client: Any,
        evidence: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Perform advanced Markdown-based analysis."""

        model = get_model_for_tier(tier.lower())

        # Scale+ specific token logic
        if tier.lower() == "scale_plus":
            from ...token_allocator import TokenAllocator

            allocator = TokenAllocator()

            # Simple complexity estimation for token allocation
            complexity_data = {
                "total_files": len(evidence.get("file_analysis", {}).get("files", [])),
                "total_lines": sum(
                    f.get("lines", 0)
                    for f in evidence.get("file_analysis", {}).get("files", [])
                ),
            }
            # Missing some fields but good enough for allocation
            complexity = allocator.calculate_repository_complexity(complexity_data)
            max_tokens, _, _ = allocator.allocate_tokens(complexity, tier)
        else:
            max_tokens = get_token_limit(tier, "unified")

        target_ranges = get_target_ranges(tier)
        pattern_count = len(evidence.get("evidence_patterns", []))

        # Determine ranges (logic simplified from giant block)
        if (
            hasattr(repo_data.metrics, "lines_of_code")
            and repo_data.metrics.lines_of_code
        ):
            loc = repo_data.metrics.lines_of_code
            if loc < 300:
                insight_range = (5, 8)
                question_range = (5, 8)
                recommendation_range = (3, 5)
            elif loc < 1000:
                insight_range = (10, 12)
                question_range = (10, 12)
                recommendation_range = (7, 10)
            else:
                insight_range = target_ranges["insight_range"]
                question_range = target_ranges["question_range"]
                recommendation_range = target_ranges["recommendation_range"]
        else:
            insight_range = target_ranges["insight_range"]
            question_range = target_ranges["question_range"]
            recommendation_range = target_ranges["recommendation_range"]

        # Prepare Prompt (Markdown focused)
        evidence_text = ""
        if evidence.get("evidence_patterns"):
            evidence_text += (
                f"EVIDENCE PATTERNS ({len(evidence['evidence_patterns'])} available):\n"
            )
            for i, pattern in enumerate(evidence["evidence_patterns"], 1):
                if isinstance(pattern, dict):
                    evidence_text += f"\nPattern {i}:\n  {pattern.get('pattern', 'N/A')}\n  Evidence: {pattern.get('evidence', 'N/A')}\n"

        if evidence.get("technical_patterns"):
            evidence_text += f"\nTECHNICAL PATTERNS: {evidence['technical_patterns']}\n"

        tier_display_name = tier.upper()

        tier_requirements = f"""🔴🔴🔴 TIER {tier_display_name} - CONTRACTUAL OBLIGATIONS 🔴🔴🔴

    ⚠️ THIS IS A {tier_display_name} TIER ANALYSIS WITH MANDATORY MINIMUMS ⚠️

    Available evidence patterns: {pattern_count}

    🎯 NON-NEGOTIABLE GENERATION REQUIREMENTS:
    ✅ INSIGHTS: YOU MUST GENERATE EXACTLY {insight_range[0]} TO {insight_range[1]} INSIGHTS
       - MINIMUM: {insight_range[0]} insights (NOT {insight_range[0] - 1}, NOT "approximately {insight_range[0]}")
       - TARGET: {insight_range[1]} insights

    ✅ QUESTIONS: YOU MUST GENERATE EXACTLY {question_range[0]} TO {question_range[1]} QUESTIONS
       - MINIMUM: {question_range[0]} questions
       - TARGET: {question_range[1]} questions

    ✅ RECOMMENDATIONS: YOU MUST GENERATE EXACTLY {recommendation_range[0]} TO {recommendation_range[1]} RECOMMENDATIONS
       - MINIMUM: {recommendation_range[0]} recommendations
       - TARGET: {recommendation_range[1]} recommendations
"""

        prompt = UNIFIED_INSIGHTS_AND_QUESTIONS_PROMPT.format(
            context=context,
            evidence_json=evidence_text,  # Passed as text for Markdown strategy
            tier_requirements=tier_requirements,
            pattern_count=pattern_count,
            insight_range=insight_range,
            question_range=question_range,
            recommendation_range=recommendation_range,
            repo_full_name=repo_data.full_name if repo_data else "unknown",
            repo_owner=repo_data.owner if repo_data else "unknown",
        )

        # Inject Markdown structure instructions (Scale+/Enterprise/Pro logic)
        # This part was injecting complex markdown template in original code.
        # We should replicate the Markdown structure requirement.

        markdown_structure = """
<output_format>
⚠️ CRITICAL FORMAT REQUIREMENT ⚠️
YOU MUST ALWAYS USE THIS EXACT MARKDOWN FORMAT. NO EXCEPTIONS.
DO NOT RETURN JSON.

# Summary
[Executive summary]

# Insights
## Insight 1
**Title:** ...
**Category:** ...
**Description:** ...
**Evidence:** ...
**Confidence:** ...
**Impact:** ...

# Questions
## Question 1
**Question:** ...
**Purpose:** ...
**Context:** ...
**Relevance:** ...
**Category:** ...

# Recommendations
## Recommendation 1
**Recommendation:** ...
**Priority:** ...
**Rationale:** ...

# Areas to Explore
...

# Data Limitations
...

# Confidence Explanation
...
</output_format>
"""
        prompt += f"\n\n{markdown_structure}"

        role_guidance = self.get_role_level_guidance("senior", tier, context)
        prompt += f"\n\n{role_guidance}"

        logger.info(
            f"Advanced Analysis Strategy - Model: {model}, Tokens: {max_tokens}"
        )

        system_prompt = """You are an expert code reviewer and technical interviewer.
🔴🔴🔴 CRITICAL: YOU MUST OUTPUT MARKDOWN FORMAT, NOT JSON! 🔴🔴🔴
Your response MUST start with:
# Summary
NOT with {{
"""

        response = anthropic_client.create_message(
            model=model,
            max_tokens=max_tokens,
            temperature=0.1,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )

        if hasattr(response.content[0], "text"):
            ai_response = response.content[0].text
        else:
            raise Exception("Invalid AI response format")

        # Parse Markdown (local import avoids a circular dependency)
        from ....ai.markdown_parser import MarkdownParser

        parser = MarkdownParser()
        parsed_result, error_msg = parser.parse(ai_response)

        if parsed_result:
            unified_result = parsed_result
        else:
            logger.error(f"Markdown parsing suspected failure: {error_msg}")
            # Fallback attempt if JSON was returned
            try:
                if "```json" in ai_response:
                    ai_response = (
                        ai_response.split("```json")[1].split("```")[0].strip()
                    )
                unified_result = json.loads(ai_response)
            except Exception:
                raise ValueError(f"Failed to parse response: {error_msg}")

        return unified_result
