# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
MarkdownParser - Robust Markdown-based AI Response Parser

Replaces JSON parsing with structured Markdown format for more reliable
AI response handling. Maintains 100% API compatibility while eliminating
JSON parsing errors.

Part of the evidence-based analysis system.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from ..utils.logging import get_logger

logger = get_logger(__name__)


# Explicit format instructions for AI models
MARKDOWN_FORMAT_INSTRUCTION = """
🔴🔴🔴 CRITICAL: YOU MUST OUTPUT MARKDOWN FORMAT, NOT JSON! 🔴🔴🔴

⛔ FORBIDDEN: Do NOT return JSON with "observed_patterns" or curly braces {{}}
✅ REQUIRED: Return MARKDOWN with # headers and **bold** formatting

OUTPUT FORMAT: Generate structured Markdown following this EXACT format:

# Summary
[Executive summary here - single paragraph]

# Insights
Generate AT LEAST {insight_count} insights (you can generate more based on available evidence) using this format:

## Insight 1
**Title:** [UNIQUE and SPECIFIC title. ⛔ ABSOLUTELY FORBIDDEN: 'The Repository Demonstrates', 'The Presence Of', 'The Ability To', generic phrases. ✅ REQUIRED: Use SPECIFIC titles like 'Python Language Mastery', 'Security-First Architecture', 'Test-Driven Development', 'CI/CD Pipeline Expertise', 'API Design Patterns', 'Database Integration Skills'. Each title MUST be UNIQUE - NO DUPLICATES!]
**Category:** [technical_skills|professional_practices|collaboration|problem_solving|growth_potential]
**Description:** [2-3 sentences explaining the insight based on evidence]
**Evidence:** [Specific evidence supporting this insight - files, commits, patterns]
**Confidence:** [high|medium|low]
**Impact:** [positive|neutral|concerning]

## Insight 2
[Continue with same format...]

# Questions
Generate AT LEAST {question_count} questions using this format:

## Question 1
**Question:** [The actual interview question]
**Purpose:** [Why this question matters]
**Context:** [What evidence prompted this question]
**Relevance:** [Why this matters for the specific hiring context - e.g., "Critical for startup environment", "Important for enterprise collaboration", "Key for open-source contribution"]
**Category:** [technical|behavioral|situational|experience]
**Follow-ups:**
- [Follow-up question 1]
- [Follow-up question 2]
- [Follow-up question 3]

## Question 2
[Continue with same format...]

# Recommendations
Generate AT LEAST {recommendation_count} recommendations using this format:

## Recommendation 1
**Recommendation:** [Clear actionable recommendation]
**Priority:** [high|medium|low]
**Rationale:** [Why this is recommended based on evidence]

## Recommendation 2
[Continue with same format...]

# Areas to Explore
- [Clear, specific area to explore - NO BOLD TEXT, just plain description]
- [Another area that warrants discussion - avoid using ** or formatting]
- [Continue for 3-5 areas total - keep it simple and readable]

# Data Limitations
- [Limitation 1 about available data]
- [Limitation 2 about available data]
- [Continue for 2-4 limitations total]

# Analysis Confidence Level
[Single paragraph explaining overall confidence level based on data availability and sample size]

CRITICAL REQUIREMENTS:
- Use EXACT heading structure (# for main sections, ## for items)
- Include ALL required fields for each item
- Generate EXACT counts specified (not ranges)
- Use only the specified category/confidence/priority values
- Keep descriptions concise and evidence-based

🚨 FINAL WARNING: If you return JSON instead of Markdown, the analysis will FAIL!
DO NOT USE: {{"observed_patterns": [...], "summary": "..."}}
MUST USE: # Summary followed by # Insights followed by # Questions etc.
"""


class MarkdownParser:
    """
    Parser for structured Markdown AI responses.

    Provides robust parsing with validation and error recovery,
    maintaining API compatibility with the existing JSON structure.
    """

    def __init__(self) -> None:
        """Initialize the Markdown parser."""
        self.parse_attempts = 0
        self.last_error: Optional[str] = None

    def parse(
        self, response_text: str, expected_counts: Optional[Dict[str, int]] = None
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        Parse structured Markdown into API-compatible dictionary.

        Args:
            response_text: Raw Markdown response from AI
            expected_counts: Expected counts for validation (insights, questions, etc.)

        Returns:
            Tuple of (parsed_dict, error_message)
            If successful: (dict, "")
            If failed: (None, error_description)
        """
        self.parse_attempts = 0
        self.last_error = None

        # Handle empty input
        if not response_text or not response_text.strip():
            error_msg = "Empty response text provided"
            self.last_error = error_msg
            return None, error_msg

        logger.debug(f"Parsing Markdown response of {len(response_text)} characters")

        try:
            # Parse the markdown structure
            parsed = self._parse_markdown_structure(response_text)

            # Validate counts if provided
            if expected_counts:
                validation_error = self._validate_counts(parsed, expected_counts)
                if validation_error:
                    logger.warning(f"Count validation failed: {validation_error}")
                    # Don't fail, just log the warning

            # Convert to API-compatible format
            api_response = self._markdown_to_api_response(parsed)

            logger.info("Markdown parsed successfully")
            return api_response, ""

        except Exception as e:
            error_msg = f"Failed to parse Markdown: {str(e)}"
            logger.error(error_msg)
            self.last_error = error_msg
            return None, error_msg

    def _parse_markdown_structure(self, text: str) -> Dict[str, Any]:
        """Parse the Markdown text into a structured dictionary."""
        result: Dict[str, Any] = {
            "summary": "",
            "insights": [],
            "questions": [],
            "recommendations": [],
            "areas_to_explore": [],
            "data_limitations": [],
            "confidence_explanation": "",
        }

        # Handle empty text
        if not text or not text.strip():
            return result

        # Parse Summary section
        summary_match = re.search(r"# Summary\s*\n(.*?)(?=\n#|\Z)", text, re.DOTALL)
        if summary_match:
            result["summary"] = summary_match.group(1).strip()

        # Parse Insights section - match until next # heading (not ##)
        insights_section = re.search(
            r"# Insights\s*\n(.*?)(?=\n# [A-Z]|\Z)", text, re.DOTALL
        )
        if insights_section:
            result["insights"] = self._parse_insights(insights_section.group(1))

        # Parse Questions section - match until next # heading (not ##)
        questions_section = re.search(
            r"# Questions\s*\n(.*?)(?=\n# [A-Z]|\Z)", text, re.DOTALL
        )
        if questions_section:
            result["questions"] = self._parse_questions(questions_section.group(1))

        # Parse Recommendations section - match until next # heading (not ##)
        recommendations_section = re.search(
            r"# Recommendations\s*\n(.*?)(?=\n# [A-Z]|\Z)", text, re.DOTALL
        )
        if recommendations_section:
            result["recommendations"] = self._parse_recommendations(
                recommendations_section.group(1)
            )

        # Parse Areas to Explore
        areas_section = re.search(
            r"# Areas to Explore\s*\n(.*?)(?=\n# Data|\n#|\Z)", text, re.DOTALL
        )
        if areas_section:
            result["areas_to_explore"] = self._parse_bullet_list(areas_section.group(1))

        # Parse Data Limitations
        limitations_section = re.search(
            r"# Data Limitations\s*\n(.*?)(?=\n# Confidence|\n#|\Z)", text, re.DOTALL
        )
        if limitations_section:
            result["data_limitations"] = self._parse_bullet_list(
                limitations_section.group(1)
            )

        # Parse Confidence Explanation
        confidence_section = re.search(
            r"# Confidence Explanation\s*\n(.*?)(?=\n#|\Z)", text, re.DOTALL
        )
        if confidence_section:
            result["confidence_explanation"] = confidence_section.group(1).strip()

        return result

    def _parse_insights(self, text: str) -> List[Dict[str, Any]]:
        """Parse the insights section."""
        insights = []

        # Find all insight blocks - look for next section or end of string
        insight_blocks = re.findall(
            r"## Insight \d+\s*\n(.*?)(?=## Insight \d+|# Questions|# Recommendations|\Z)",
            text,
            re.DOTALL,
        )

        for i, block in enumerate(insight_blocks, 1):
            insight = {}

            # Extract fields using regex
            title_match = re.search(r"\*\*Title:\*\*\s*(.*?)(?:\n|$)", block)
            if title_match:
                insight["title"] = title_match.group(1).strip()

            category_match = re.search(r"\*\*Category:\*\*\s*(.*?)(?:\n|$)", block)
            if category_match:
                insight["category"] = category_match.group(1).strip()

            description_match = re.search(
                r"\*\*Description:\*\*\s*(.*?)(?=\*\*Evidence:|\*\*|$)",
                block,
                re.DOTALL,
            )
            if description_match:
                insight["description"] = description_match.group(1).strip()

            evidence_match = re.search(
                r"\*\*Evidence:\*\*\s*(.*?)(?=\*\*Confidence:|\*\*|$)", block, re.DOTALL
            )
            if evidence_match:
                insight["evidence"] = evidence_match.group(1).strip()

            confidence_match = re.search(r"\*\*Confidence:\*\*\s*(.*?)(?:\n|$)", block)
            if confidence_match:
                insight["confidence"] = confidence_match.group(1).strip()

            impact_match = re.search(r"\*\*Impact:\*\*\s*(.*?)(?:\n|$)", block)
            if impact_match:
                insight["impact"] = impact_match.group(1).strip()

            if insight:  # Only add if we found some fields
                insights.append(insight)

        return insights

    def _parse_questions(self, text: str) -> List[Dict[str, Any]]:
        """Parse the questions section."""
        questions = []

        # Find all question blocks - look for next section or end of string
        question_blocks = re.findall(
            r"## Question \d+\s*\n(.*?)(?=## Question \d+|# Recommendations|# Areas to Explore|\Z)",
            text,
            re.DOTALL,
        )

        for block in question_blocks:
            question = {}

            # Extract fields using regex
            question_match = re.search(
                r"\*\*Question:\*\*\s*(.*?)(?=\*\*Purpose:|\*\*|$)", block, re.DOTALL
            )
            if question_match:
                question["question"] = question_match.group(1).strip()

            purpose_match = re.search(
                r"\*\*Purpose:\*\*\s*(.*?)(?=\*\*Context:|\*\*|$)", block, re.DOTALL
            )
            if purpose_match:
                question["purpose"] = purpose_match.group(1).strip()

            context_match = re.search(
                r"\*\*Context:\*\*\s*(.*?)(?=\*\*Relevance:|\*\*Category:|\*\*|$)",
                block,
                re.DOTALL,
            )
            if context_match:
                question["context"] = context_match.group(1).strip()

            relevance_match = re.search(
                r"\*\*Relevance:\*\*\s*(.*?)(?=\*\*Category:|\*\*|$)", block, re.DOTALL
            )
            if relevance_match:
                question["relevance"] = relevance_match.group(1).strip()

            category_match = re.search(r"\*\*Category:\*\*\s*(.*?)(?:\n|$)", block)
            if category_match:
                question["category"] = category_match.group(1).strip()

            # Parse follow-up questions
            followups_match = re.search(
                r"\*\*Follow-ups:\*\*\s*(.*?)(?=\n\n|\Z)", block, re.DOTALL
            )
            if followups_match:
                followups_text = followups_match.group(1).strip()
                # Extract bullet points
                followups = []
                for line in followups_text.split("\n"):
                    line = line.strip()
                    if line.startswith("-"):
                        followups.append(line[1:].strip())
                question["follow_ups"] = followups
            else:
                question["follow_ups"] = []

            if question:  # Only add if we found some fields
                questions.append(question)

        return questions

    def _parse_recommendations(self, text: str) -> List[Dict[str, Any]]:
        """Parse the recommendations section."""
        recommendations = []

        # Find all recommendation blocks - look for next section or end of string
        recommendation_blocks = re.findall(
            r"## Recommendation \d+\s*\n(.*?)(?=## Recommendation \d+|# Areas to Explore|# Data Limitations|# Confidence Explanation|\Z)",
            text,
            re.DOTALL,
        )

        for block in recommendation_blocks:
            recommendation = {}

            # Extract fields using regex
            rec_match = re.search(
                r"\*\*Recommendation:\*\*\s*(.*?)(?=\*\*Priority:|\*\*|$)",
                block,
                re.DOTALL,
            )
            if rec_match:
                recommendation["recommendation"] = rec_match.group(1).strip()

            priority_match = re.search(r"\*\*Priority:\*\*\s*(.*?)(?:\n|$)", block)
            if priority_match:
                recommendation["priority"] = priority_match.group(1).strip()

            rationale_match = re.search(
                r"\*\*Rationale:\*\*\s*(.*?)(?:\n|$)", block, re.DOTALL
            )
            if rationale_match:
                recommendation["rationale"] = rationale_match.group(1).strip()

            if recommendation:  # Only add if we found some fields
                recommendations.append(recommendation)

        return recommendations

    def _parse_bullet_list(self, text: str) -> List[str]:
        """Parse a bullet point list and clean up formatting."""
        items = []

        # Find all bullet points (- or *)
        matches = re.findall(r"^[\-\*]\s*(.*?)$", text, re.MULTILINE)

        for match in matches:
            item = match.strip()
            if item:
                # Remove bold formatting (**text**) if present
                # This helps clean up areas_to_explore that have unwanted bold text
                item = re.sub(r"\*\*(.*?)\*\*:", r"\1:", item)  # Remove bold with colon
                item = re.sub(
                    r"\*\*(.*?)\*\*", r"\1", item
                )  # Remove any remaining bold
                items.append(item)

        return items

    def _validate_counts(
        self, parsed: Dict[str, Any], expected: Dict[str, int]
    ) -> Optional[str]:
        """Validate that parsed data meets expected counts."""
        errors = []

        if "insights" in expected:
            actual = len(parsed.get("insights", []))
            expected_count = expected["insights"]
            if actual != expected_count:
                errors.append(f"insights: expected {expected_count}, got {actual}")

        if "questions" in expected:
            actual = len(parsed.get("questions", []))
            expected_count = expected["questions"]
            if actual != expected_count:
                errors.append(f"questions: expected {expected_count}, got {actual}")

        if "recommendations" in expected:
            actual = len(parsed.get("recommendations", []))
            expected_count = expected["recommendations"]
            if actual != expected_count:
                errors.append(
                    f"recommendations: expected {expected_count}, got {actual}"
                )

        if errors:
            return "Count validation failed: " + "; ".join(errors)

        return None

    def _markdown_to_api_response(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert parsed Markdown to API-compatible JSON structure.

        Maintains exact same structure as current JSON responses
        for zero breaking changes.
        """
        # Build the API response maintaining exact compatibility with UI
        api_response = {
            "executive_summary": parsed.get("summary", ""),
            "overall_recommendation": "",  # Not in Markdown format
            "confidence_explanation": parsed.get(
                "confidence_explanation", "Evidence-based analysis"
            ),
            "repository_type": "standard",  # Default value
            "context_fit_score": 0.0,  # Not used in evidence-based approach
            "key_strengths": [],  # Will be extracted from insights
            "primary_concerns": [],  # Will be extracted from insights
            "analysis_recommendations": [],  # Not used
            "interview_focus_areas": [],  # Not used
            "technical_assessment": {},  # Not populated from Markdown
            "professional_practices": {},  # Not populated from Markdown
            "communication_skills": {},  # Not populated from Markdown
            "growth_indicators": {},  # Not populated from Markdown
            "team_fit_analysis": {},  # Not populated from Markdown
            "insights": [],
            "questions": [],
            "recommendations": [],
            "evidence_patterns": [],  # Populated separately
            "insights_count": 0,  # Will be set after parsing
            "questions_count": 0,  # Will be set after parsing
            "recommendations_count": 0,  # Will be set after parsing
            "evidence_patterns_count": 0,  # Set separately
            "green_flags": [],  # Extract from positive insights
            "red_flags": [],  # Extract from negative insights
            "limitations": parsed.get("data_limitations", []),
            "areas_to_explore": parsed.get("areas_to_explore", []),
            # Legacy fields for backward compatibility
            "summary": parsed.get("summary", ""),
            "overall_impression": parsed.get("summary", ""),
            "data_limitations": parsed.get("data_limitations", []),
        }

        # Convert insights to API format - match exact structure from UI
        for insight in parsed.get("insights", []):
            api_insight = {
                "category": insight.get("category", "general"),
                "description": insight.get("description", ""),
                "evidence": (
                    [insight.get("evidence", "")]
                    if isinstance(insight.get("evidence"), str)
                    else insight.get("evidence", [])
                ),
                "confidence": insight.get("confidence", "medium"),
                "impact": insight.get("impact", "neutral"),
            }
            # Include title field for display in Evidence tab
            if insight.get("title"):
                api_insight["title"] = insight["title"]
            else:
                # Generate title from description if not present
                desc = insight.get("description", "")
                if desc:
                    # Take first sentence or up to 50 chars as title
                    sentences = desc.split(".")
                    if sentences and sentences[0]:
                        api_insight["title"] = sentences[0].strip()[:50]
                    else:
                        api_insight["title"] = desc[:50].strip()
            api_response["insights"].append(api_insight)

            # Extract key strengths and green flags from positive insights
            if insight.get("impact") == "positive":
                if insight.get("confidence") in ["high", "medium"]:
                    strength_text = (
                        insight.get("title") or insight.get("description", "")[:100]
                    )
                    if strength_text:
                        api_response["key_strengths"].append(strength_text)
                # Add to green flags
                flag_text = insight.get("description", "")
                if flag_text:
                    api_response["green_flags"].append(flag_text)

            # Extract primary concerns from negative/concerning insights
            elif insight.get("impact") in ["negative", "concerning"]:
                concern_text = insight.get("description", "")
                if concern_text:
                    api_response["primary_concerns"].append(concern_text)
                    api_response["red_flags"].append(concern_text)

        # Convert questions to API format - match exact structure from UI
        for question in parsed.get("questions", []):
            # Ensure question has proper punctuation
            question_text = question.get("question", "")
            if question_text and not question_text.rstrip().endswith(("?", ".", "!")):
                question_text = question_text.rstrip() + "?"

            api_question = {
                "category": question.get("category", "general"),
                "question": question_text,
                "evidence_reference": question.get(
                    "context", ""
                ),  # Map context to evidence_reference
                "follow_ups": question.get("follow_ups", []),  # Use parsed follow-ups
                "what_to_listen_for": question.get(
                    "purpose", ""
                ),  # Map purpose to what_to_listen_for
                "context_relevance": question.get(
                    "relevance", ""
                ),  # Use parsed relevance field
            }
            api_response["questions"].append(api_question)

        # Convert recommendations to API format - match exact structure from UI
        for rec in parsed.get("recommendations", []):
            api_rec = {
                "type": "strength" if rec.get("priority") == "high" else "suggestion",
                "text": rec.get("recommendation", ""),
                "priority": rec.get("priority", "medium"),
                "evidence": rec.get("rationale", ""),
            }
            api_response["recommendations"].append(api_rec)

        # Set counts
        api_response["insights_count"] = len(api_response["insights"])
        api_response["questions_count"] = len(api_response["questions"])
        api_response["recommendations_count"] = len(api_response["recommendations"])

        # Limit lists as needed
        api_response["key_strengths"] = api_response["key_strengths"][:5]
        api_response["green_flags"] = api_response["green_flags"][:5]
        api_response["primary_concerns"] = api_response["primary_concerns"][:2]

        return api_response


def create_markdown_parser() -> MarkdownParser:
    """Factory function to create a Markdown parser instance."""
    return MarkdownParser()


def get_markdown_instructions(
    insight_count: int, question_count: int, recommendation_count: int
) -> str:
    """
    Get formatted Markdown instructions with specific counts.

    Args:
        insight_count: Number of insights to generate
        question_count: Number of questions to generate
        recommendation_count: Number of recommendations to generate

    Returns:
        Formatted instruction string
    """
    return MARKDOWN_FORMAT_INSTRUCTION.format(
        insight_count=insight_count,
        question_count=question_count,
        recommendation_count=recommendation_count,
    )
