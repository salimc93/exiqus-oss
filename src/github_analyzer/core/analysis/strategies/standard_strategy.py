# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Standard analysis strategy for Free, Basic, and Growth tiers.
Uses JSON-based prompting and simpler models.
"""

import json
from typing import Any, Dict

from ....ai.evidence_based_prompts import UNIFIED_INSIGHTS_AND_QUESTIONS_PROMPT
from ....utils.logging import get_logger
from ...tier_config import get_model_for_tier, get_token_limit
from .analysis_strategy import AnalysisStrategy

logger = get_logger(__name__)


class StandardAnalysisStrategy(AnalysisStrategy):
    """Strategy for standard tiers (Free, Basic, Growth)."""

    def analyze(
        self,
        repo_data: Any,
        context: Any,
        tier: str,
        anthropic_client: Any,
        evidence: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Perform standard JSON-based analysis."""

        # Determine model and limits
        model = get_model_for_tier(tier.lower())
        max_tokens = get_token_limit(tier, "unified")

        pattern_count = len(evidence.get("evidence_patterns", []))

        # Calculate proportional ranges
        multipliers = (0.35, 0.5) if tier.lower() == "basic" else (0.2, 0.3)
        min_insights = max(3, int(pattern_count * multipliers[0]))
        max_insights = max(min_insights + 2, int(pattern_count * multipliers[1]))

        # Caps
        tier_cap = 10 if tier.lower() == "basic" else 5
        max_insights = min(max_insights, tier_cap)
        min_insights = min(min_insights, max_insights - 2)

        insight_range = (min_insights, max_insights)
        question_range = (
            max(3, int(min_insights * 0.8)),
            max(5, int(max_insights * 0.9)),
        )
        recommendation_range = (
            max(3, int(min_insights * 0.6)),
            max(5, int(max_insights * 0.7)),
        )

        # Tier requirements string
        if tier.lower() == "basic":
            tier_requirements = f"""## Your Role as a Repository Analyst

You are an expert code analyst helping developers understand repository patterns. You will analyze this repository and share your findings in a structured way.

## Context About This Analysis
- Available Evidence: {pattern_count} distinct patterns identified
- Analysis Tier: Starter (comprehensive analysis for growing teams)

## Your Analysis Process

<thinking>
You will now think through the repository systematically:
1. First, you'll review the {pattern_count} evidence patterns available
2. Then, you'll convert each significant pattern into an insight
3. Next, you'll create questions that explore important technical decisions
4. Finally, you'll provide actionable recommendations

Remember: You have {pattern_count} evidence patterns to work with. This means you can easily generate 8 insights by selecting the most significant patterns.
</thinking>

## What You Will Generate

You will create a comprehensive analysis with these components:

### 1. Insights (EXACTLY 8)
**CRITICAL**: You have {pattern_count} evidence patterns. Convert EXACTLY 8 of them into insights!

**IMPORTANT**: Recognize ALL types of development work - frontend (React, Vue, CSS), backend (APIs, databases), mobile, DevOps, etc. Every repository has valuable patterns to identify, whether it's a portfolio site, API server, or full-stack application.

You will identify EXACTLY 8 distinct insights about:
- Programming language usage and distribution (JavaScript, TypeScript, CSS, etc.)
- Frontend frameworks and libraries (React, Vue, Next.js, styling libraries)
- Component architecture and UI patterns
- Testing infrastructure (unit tests, integration tests, E2E tests)
- Documentation completeness and quality
- Code organization and architectural patterns (frontend or backend)
- State management and data flow patterns
- Build tools and deployment configurations
- API integration and data fetching strategies
- Styling approaches (CSS-in-JS, CSS modules, utility classes)
- Accessibility and user experience considerations
- Performance optimization approaches

Think of it this way: Each evidence pattern you found can become an insight. With {pattern_count} patterns, generating 8 insights is straightforward.

**PORTFOLIO/UI REPOSITORIES**: If this is a portfolio, personal website, or UI-focused project, the visual design choices, component architecture, styling systems, and user experience decisions are JUST AS VALUABLE as backend logic. Convert UI/design patterns into insights - they demonstrate crucial frontend expertise.

Example of a good insight:
"TypeScript Adoption: The repository uses TypeScript for 89% of the codebase with strict type checking enabled, demonstrating commitment to type safety and developer experience."

### 2. Interview Questions (EXACTLY 8)
**CRITICAL**: You have {pattern_count} evidence patterns. Create questions based on the most interesting ones!

You will create EXACTLY 8 thoughtful questions that:
- Connect directly to patterns you observed
- Explore the reasoning behind technical decisions
- Understand the developer's problem-solving approach
- Assess depth of knowledge in key areas
- For portfolios/UI projects: Ask about design decisions, component patterns, and UX choices

Example of a good question:
"I noticed you use React hooks extensively throughout the application. Can you walk me through your decision to use custom hooks for state management instead of a traditional state library?"

### 3. Recommendations (EXACTLY 6)
You will provide EXACTLY 6 actionable recommendations based on:
- Strengths to highlight and leverage
- Areas that could benefit from improvement
- Opportunities for growth and learning

## Success Criteria
"""
        else:
            tier_requirements = f"""Available evidence patterns: {pattern_count}

            NON-NEGOTIABLE GENERATION REQUIREMENTS:
            - Start with INSIGHTS: Generate EXACTLY {insight_range[0]} to {insight_range[1]} insights
            - Then QUESTIONS: Generate EXACTLY {question_range[0]} to {question_range[1]} questions
            - Finally RECOMMENDATIONS: Generate EXACTLY {recommendation_range[0]} to {recommendation_range[1]} recommendations
            """

        # Build prompt
        prompt = UNIFIED_INSIGHTS_AND_QUESTIONS_PROMPT.format(
            context=context,
            evidence_json=json.dumps(evidence, indent=2),
            tier_requirements=tier_requirements,
            pattern_count=pattern_count,
            insight_range=insight_range,
            question_range=question_range,
            recommendation_range=recommendation_range,
            repo_full_name=repo_data.full_name if repo_data else "unknown",
            repo_owner=repo_data.owner if repo_data else "unknown",
        )

        role_guidance = self.get_role_level_guidance("senior", tier, context)
        prompt += f"\n\n{role_guidance}"

        logger.info(
            f"Standard Analysis Strategy - Model: {model}, Tokens: {max_tokens}"
        )

        # API Call
        system_prompt = "You are an expert code reviewer. Your response must be ONLY valid JSON. Do not include any explanatory text, reasoning, or thinking process. Start your response with { and end with }. No markdown code blocks. Just pure JSON."

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

        # Parse JSON
        if "```json" in ai_response:
            ai_response = ai_response.split("```json")[1].split("```")[0].strip()
        elif "```" in ai_response:
            ai_response = ai_response.split("```")[1].split("```")[0].strip()

        unified_result: Dict[str, Any] = json.loads(ai_response)

        # Post-processing steps (ensure required fields, etc.)
        if "insights" not in unified_result:
            unified_result["insights"] = []
        if "questions" not in unified_result:
            unified_result["questions"] = []
        if "recommendations" not in unified_result:
            unified_result["recommendations"] = []

        return unified_result
