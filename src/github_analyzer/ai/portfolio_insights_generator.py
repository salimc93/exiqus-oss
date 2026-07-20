# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Portfolio Insights Generator using AI models.

This module generates insights from portfolio evidence using tier-appropriate AI models.
Follows validation script's proven approach - evidence-based, NO SCORES.
"""

import json
from typing import Any, Dict, List

from ..core.tier_config import get_model_for_tier, get_token_limit
from ..data.portfolio_models import PortfolioMetadata, RepoData
from ..data.portfolio_report_generator import PortfolioReportGenerator
from ..utils.logging import get_logger
from .anthropic_wrapper import AnthropicWrapper

logger = get_logger(__name__)


class PortfolioInsightsGenerator:
    """Generate AI-powered insights from portfolio evidence (NO SCORES)."""

    def __init__(self, anthropic_api_key: str) -> None:
        """
        Initialize portfolio insights generator.

        Args:
            anthropic_api_key: API key for Anthropic Claude
        """
        self.anthropic = AnthropicWrapper(anthropic_api_key)
        self.report_generator = PortfolioReportGenerator()

    def generate_insights(
        self,
        username: str,
        evidence: Dict[str, Any],
        metadata: PortfolioMetadata,
        repos: List[RepoData],
        context: str = "enterprise",
        tier: str = "professional",
        role: str = "senior",
    ) -> Dict[str, Any]:
        """
        Generate AI insights from portfolio evidence.

        Args:
            username: GitHub username
            evidence: Extracted evidence patterns from portfolio_evidence_extractor
            metadata: Portfolio metadata (total repos, skip counts, etc.)
            repos: List of RepoData objects
            context: Hiring context (startup/enterprise/agency/open_source)
            tier: User subscription tier (determines AI model)
            role: Role level for interview questions (junior, mid, senior)

        Returns:
            Dictionary containing AI-generated insights (NO SCORES)
        """
        try:
            logger.info(
                f"Generating portfolio insights for {username} "
                f"(context: {context}, tier: {tier})"
            )

            # Resolves to ANTHROPIC_MODEL unless the tier sets an override.
            main_model = get_model_for_tier(tier, model_type="main")

            # Check if tier has separate questions model (Scale+ multi-model approach)
            questions_model = get_model_for_tier(tier, model_type="questions")
            use_multi_model = questions_model and questions_model != main_model

            if use_multi_model:
                logger.info(
                    f"Multi-model approach: {main_model} for main analysis, {questions_model} for interview questions"
                )
            else:
                logger.info(f"Single-model approach: {main_model} for all sections")

            # Get tier-specific token limit to leverage full model capacity
            max_tokens = get_token_limit(tier, limit_type="main")
            logger.info(
                f"Using tier-specific token limit for {tier}: {max_tokens} tokens"
            )

            # Generate AI prompt using report generator
            prompt = self.report_generator.generate_analysis_prompt(
                username=username,
                metadata=metadata,
                repos=repos,
                evidence=evidence,
                context=context,
                role=role,
                tier=tier,
            )

            logger.info(f"Calling {main_model} for portfolio insights generation")
            logger.info(f"Prompt length: {len(prompt)} characters")

            # Call AI model for main analysis
            response = self.anthropic.create_message(
                system="You are a senior technical hiring consultant analyzing developer portfolios.",
                messages=[{"role": "user", "content": prompt}],
                model=main_model,
                max_tokens=max_tokens,
                temperature=0.3,  # Lower temperature for focused analysis
            )

            # Parse main response
            try:
                # Extract text from response
                if not response or not hasattr(response, "content"):
                    raise ValueError("No response from AI")

                if len(response.content) == 0:
                    raise ValueError("Response content is empty")

                response_text = (
                    response.content[0].text
                    if hasattr(response.content[0], "text")
                    else str(response.content[0])
                )

                if not response_text:
                    raise ValueError("Response text is empty")

                logger.info(f"Main response text length: {len(response_text)}")

                # Parse sections from markdown response
                insights = self._parse_portfolio_response(response_text)

                # Extract token usage from main model
                main_input_tokens = (
                    response.usage.input_tokens if hasattr(response, "usage") else 0
                )
                main_output_tokens = (
                    response.usage.output_tokens if hasattr(response, "usage") else 0
                )

                # If multi-model tier, generate interview questions with second model (Phase 2)
                if use_multi_model:
                    logger.info(
                        f"PHASE 2: Generating interview questions with {questions_model}"
                    )

                    try:
                        # Get Phase 2 token limit
                        questions_max_tokens = get_token_limit(
                            tier, limit_type="questions"
                        )

                        # Generate Phase 2 question prompt using main analysis results
                        question_prompt = (
                            self.report_generator.generate_question_prompt(
                                username=username,
                                metadata=metadata,
                                repos=repos,
                                evidence=evidence,
                                main_analysis_insights=insights,
                                context=context,
                                role=role,
                                tier=tier,
                            )
                        )

                        logger.info(
                            f"Phase 2 prompt length: {len(question_prompt)} characters"
                        )

                        # Call second model for question generation
                        question_response = self.anthropic.create_message(
                            system="You are a senior technical hiring consultant generating interview questions.",
                            messages=[{"role": "user", "content": question_prompt}],
                            model=questions_model,
                            max_tokens=questions_max_tokens,
                            temperature=0.3,
                        )

                        # Extract question response text
                        question_response_text = (
                            question_response.content[0].text
                            if hasattr(question_response.content[0], "text")
                            else str(question_response.content[0])
                        )

                        logger.info(
                            f"Phase 2 response length: {len(question_response_text)}"
                        )

                        # Parse questions from Phase 2 response
                        phase2_questions = self._parse_questions_from_response(
                            question_response_text
                        )

                        # Merge Phase 2 questions into main insights (replacing any from Phase 1)
                        insights["interview_questions"] = phase2_questions

                        # Extract token usage from Phase 2
                        questions_input_tokens = (
                            question_response.usage.input_tokens
                            if hasattr(question_response, "usage")
                            else 0
                        )
                        questions_output_tokens = (
                            question_response.usage.output_tokens
                            if hasattr(question_response, "usage")
                            else 0
                        )

                        logger.info(
                            f"Phase 2 complete: {questions_input_tokens} in + {questions_output_tokens} out = {questions_input_tokens + questions_output_tokens} tokens"
                        )

                    except Exception as e:
                        logger.error(
                            f"Phase 2 (question generation) failed: {e}", exc_info=True
                        )
                        # Continue with questions from Phase 1 rather than fail entire analysis
                        questions_input_tokens = 0
                        questions_output_tokens = 0
                else:
                    # Single-model approach: questions already in Phase 1 response
                    questions_input_tokens = 0
                    questions_output_tokens = 0

                # Calculate total tokens and cost (Phase 1 + Phase 2)
                total_input_tokens = main_input_tokens + questions_input_tokens
                total_output_tokens = main_output_tokens + questions_output_tokens
                total_tokens = total_input_tokens + total_output_tokens

                # Calculate cost (Sonnet-4 pricing: $3/1M input, $15/1M output)
                # Note: Both models use same pricing tier for simplicity
                cost = (total_input_tokens / 1_000_000 * 3.0) + (
                    total_output_tokens / 1_000_000 * 15.0
                )

                logger.info(
                    f"Total token usage (Phase 1+2): {total_input_tokens} in + {total_output_tokens} out = {total_tokens} total (${cost:.4f})"
                )

                # Apply sanitization (remove any scores/percentages that slipped through)
                insights = self._sanitize_insights(insights)

                logger.info(f"Successfully generated portfolio insights for {username}")

                return {
                    "success": True,
                    "insights": insights,
                    "model_used": main_model,
                    "questions_model_used": (
                        questions_model if use_multi_model else None
                    ),
                    "context": context,
                    "raw_response": response_text,  # For debugging
                    "input_tokens": total_input_tokens,
                    "output_tokens": total_output_tokens,
                    "total_tokens": total_tokens,
                    "cost": cost,
                }

            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to parse AI response: {e}")
                logger.error(
                    f"Raw response: {response_text[:1000] if response_text else 'Empty'}"
                )
                return {
                    "success": False,
                    "error": f"Failed to parse AI response: {str(e)}",
                    "raw_response": response_text[:500] if response_text else "",
                    "insights": self._get_fallback_insights(username),
                }

        except Exception as e:
            logger.error(
                f"Error generating portfolio insights: {str(e)}", exc_info=True
            )
            return {
                "success": False,
                "error": str(e),
                "insights": self._get_fallback_insights(username),
            }

    def _parse_portfolio_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse portfolio analysis response from AI using state machine approach.

        Based on validate_developer_portfolio.py parsing logic.
        Parses line-by-line to handle both markdown and JSON sections.

        Args:
            response_text: Raw markdown response from AI

        Returns:
            Structured insights dictionary
        """
        logger.info("Parsing portfolio response into structured format")

        # Initialize result structure
        result: Dict[str, Any] = {
            "executive_summary": "",
            "data_limitations_warning": "",
            "key_observations": [],
            "evidence_patterns": [],
            "public_portfolio_evolution": [],
            "interview_questions": [],
            "positive_indicators": [],
            "areas_to_explore": [],
            "recommendations": [],
            "quality_indicators": [],
            "confidence_explanation": "",
        }

        # Section header mapping to state names
        section_headers = {
            "EXECUTIVE SUMMARY": "summary",
            "DATA LIMITATIONS": "limitations",
            "KEY OBSERVATIONS": "observations",
            "PUBLIC PORTFOLIO EVOLUTION": "evolution",
            "EVIDENCE PATTERNS": "patterns",
            "INTERVIEW QUESTIONS": "questions",
            "POSITIVE INDICATORS": "positive_indicators",
            "AREAS TO EXPLORE": "areas_to_explore",
            "RECOMMENDATIONS": "recommendations",
            "QUALITY INDICATORS": "indicators",
            "EVIDENCE QUALITY ASSESSMENT": "confidence",
        }

        # State machine variables
        current_section = ""
        current_evolution_period = None
        current_question = None
        in_code_block = False
        code_block_lines: list[str] = []

        # Parse line by line
        for line in response_text.split("\n"):
            # Check for section headers
            section_found = False
            for header, state in section_headers.items():
                if header in line:
                    current_section = state
                    section_found = True
                    break

            if section_found:
                continue

            # Handle content based on current section
            stripped = line.strip()

            if current_section == "summary" and stripped:
                result["executive_summary"] += stripped + " "

            elif current_section == "limitations" and stripped:
                result["data_limitations_warning"] += stripped + " "

            elif current_section == "confidence" and stripped:
                result["confidence_explanation"] += stripped + " "

            elif current_section in [
                "observations",
                "recommendations",
                "positive_indicators",
                "areas_to_explore",
            ]:
                # Parse numbered lists (1., 2., etc.) or bullet points (-)
                if stripped.startswith("-") or (
                    stripped and stripped[0].isdigit() and "." in stripped[:4]
                ):
                    # Remove number prefix (e.g., "1. " or "2. ") or bullet (-)
                    text = (
                        stripped[1:].strip()
                        if stripped.startswith("-")
                        else stripped.split(".", 1)[1].strip()
                    )
                    result[
                        {
                            "observations": "key_observations",
                            "recommendations": "recommendations",
                            "positive_indicators": "positive_indicators",
                            "areas_to_explore": "areas_to_explore",
                        }[current_section]
                    ].append(text)

            elif current_section == "evolution":
                current_evolution_period = self._parse_evolution_line(
                    line, current_evolution_period, result["public_portfolio_evolution"]
                )

            elif current_section == "questions":
                current_question, in_code_block, code_block_lines = (
                    self._parse_question_line(
                        line,
                        current_question,
                        in_code_block,
                        code_block_lines,
                        result["interview_questions"],
                    )
                )

        # Finalize any pending items
        if current_evolution_period:
            result["public_portfolio_evolution"].append(current_evolution_period)
        if current_question:
            result["interview_questions"].append(current_question)

        # Deduplicate evolution periods (AI sometimes generates duplicates)
        result["public_portfolio_evolution"] = self._deduplicate_evolution_periods(
            result["public_portfolio_evolution"]
        )

        # Extract JSON sections (Evidence Patterns and Quality Indicators)
        result["evidence_patterns"] = self._extract_json_section(
            response_text,
            "EVIDENCE PATTERNS",
            r"EVIDENCE PATTERNS.*?(\[.*?\]).*?(?:KEY OBSERVATIONS|INTERVIEW QUESTIONS|$)",
        )

        result["quality_indicators"] = self._extract_json_section(
            response_text,
            "QUALITY INDICATORS",
            r"QUALITY INDICATORS.*?(\[.*?\]).*?(?:NEXT STEPS|$)",
        )

        return result

    def _extract_json_section(
        self, text: str, section_name: str, regex_pattern: str
    ) -> List[Dict[str, Any]]:
        """Extract JSON array from a section using regex with repair fallback."""
        import json
        import re

        try:
            match = re.search(regex_pattern, text, re.DOTALL)
            if match:
                json_text = match.group(1)

                # Try basic JSON parsing first (works 99% of the time)
                try:
                    result: list[dict[str, Any]] = json.loads(json_text)
                    if isinstance(result, list):
                        return result
                    logger.warning(
                        f"{section_name} JSON parsed but not a list: {type(result)}"
                    )
                except json.JSONDecodeError as e:
                    logger.warning(
                        f"Basic JSON parsing failed for {section_name}, "
                        f"attempting repairs: {e}"
                    )
                    # Apply basic repairs for common AI JSON errors
                    repaired = self._repair_json_array(json_text)
                    try:
                        result = json.loads(repaired)
                        if isinstance(result, list):
                            logger.info(f"{section_name} parsed after repairs")
                            return result
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse {section_name} after repairs")

        except Exception as e:
            logger.warning(f"Failed to extract {section_name} JSON: {e}")
        return []

    def _repair_json_array(self, json_text: str) -> str:
        """Apply basic repairs to malformed JSON arrays."""
        import re

        # Fix trailing commas before closing brackets
        json_text = re.sub(r",\s*]", "]", json_text)
        json_text = re.sub(r",\s*}", "}", json_text)

        # Fix unescaped quotes in strings (conservative)
        # This is tricky - only fix obvious cases

        # Fix unterminated strings at end of file
        if json_text.count('"') % 2 != 0:
            # Odd number of quotes - add closing quote before last ]
            last_bracket = json_text.rfind("]")
            if last_bracket > 0:
                json_text = json_text[:last_bracket] + '"' + json_text[last_bracket:]

        return json_text

    def _parse_evolution_line(
        self,
        line: str,
        current_period: Dict[str, Any] | None,
        periods_list: List[Dict[str, Any]],
    ) -> Dict[str, Any] | None:
        """Parse a single line from the evolution section."""
        import re

        stripped = line.strip()

        if stripped.startswith("###"):
            if current_period:
                periods_list.append(current_period)
            period_name = stripped.replace("###", "").strip()
            return {
                "period": period_name,
                "public_repos_created": 0,
                "technologies_observed": [],
                "total_commits": "",
                "domain_focus": "",
                "largest_project": "",
                "code_quality": "",
                "community_recognition": "",
                "note": "",
            }

        if not current_period or ":" not in line:
            return current_period

        # Field mapping for evolution periods
        field_map = {
            "repos created": (
                "public_repos_created",
                lambda v: int(m.group(1)) if (m := re.search(r"(\d+)", v)) else 0,
            ),
            "public repos created": (
                "public_repos_created",
                lambda v: int(m.group(1)) if (m := re.search(r"(\d+)", v)) else 0,
            ),
            "technologies": (
                "technologies_observed",
                lambda v: [t.strip() for t in v.split(",")],
            ),
            "total commits": ("total_commits", lambda v: v),
            "domain": ("domain_focus", lambda v: v),
            "largest project": ("largest_project", lambda v: v),
            "code quality": ("code_quality", lambda v: v),
            "community recognition": ("community_recognition", lambda v: v),
            "note": ("note", lambda v: v),
        }

        key_part = line.split(":")[0].strip("**").strip("*").strip().lower()
        value_part = line.split(":", 1)[1].strip()

        if value_part and not value_part.startswith("**"):
            for key_pattern, (field_name, transform) in field_map.items():
                if key_pattern in key_part:
                    try:
                        current_period[field_name] = transform(value_part)  # type: ignore[no-untyped-call]
                    except (ValueError, IndexError, AttributeError, KeyError) as e:
                        logger.warning(
                            f"Failed to parse evolution field '{field_name}' with value '{value_part[:100]}': {e}. "
                            "Skipping field and continuing with default value."
                        )
                        # Field remains with its default value from the period initialization
                    break

        return current_period

    def _deduplicate_evolution_periods(
        self, periods: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Deduplicate evolution periods that represent the same time range.

        Sometimes the AI generates multiple periods with similar names like:
        - "2023 (Actual Early Period - January-August)"
        - "2023 (January–August)"

        This method detects and merges such duplicates by extracting the year
        from the period name and merging periods with matching years.

        Args:
            periods: List of evolution period dictionaries

        Returns:
            Deduplicated list of periods
        """
        import re

        if not periods:
            return periods

        # Group periods by their primary year/year-range
        year_groups: Dict[str, List[Dict[str, Any]]] = {}

        for period in periods:
            period_name = period.get("period", "")

            # Extract year or year range from period name
            # Matches: "2023", "2023-2024", "2023 (anything)", etc.
            year_match = re.match(r"(\d{4})(?:-(\d{4}))?", period_name)

            if year_match:
                # Use the matched year or year-range as the key
                year_key = year_match.group(0)  # e.g., "2023" or "2023-2024"

                if year_key not in year_groups:
                    year_groups[year_key] = []
                year_groups[year_key].append(period)
            else:
                # No year found, treat as unique period
                # Use full period name as key to avoid grouping with others
                unique_key = f"_unique_{period_name}"
                year_groups[unique_key] = [period]

        # Merge duplicate periods within each year group
        deduplicated = []

        for year_key, group_periods in year_groups.items():
            if len(group_periods) == 1:
                # No duplicates, keep as-is
                deduplicated.append(group_periods[0])
            else:
                # Multiple periods for same year - merge them
                # Keep the first period and merge data from others
                merged = group_periods[0].copy()

                # Use the shortest/cleanest period name (usually without extra descriptors)
                period_names = [p.get("period", "") for p in group_periods]
                # Sort by length to get shortest name
                period_names_sorted = sorted(period_names, key=len)
                merged["period"] = period_names_sorted[0]

                # Sum up repos created
                merged["public_repos_created"] = sum(
                    p.get("public_repos_created", 0) for p in group_periods
                )

                # Merge technologies (deduplicate)
                all_techs = set()
                for p in group_periods:
                    all_techs.update(p.get("technologies_observed", []))
                merged["technologies_observed"] = sorted(list(all_techs))

                # Keep the longest/most detailed descriptions from any period
                for field in [
                    "total_commits",
                    "domain_focus",
                    "largest_project",
                    "code_quality",
                    "community_recognition",
                    "note",
                ]:
                    # Use the longest non-empty value
                    values = [
                        str(p.get(field, "")) for p in group_periods if p.get(field)
                    ]
                    if values:
                        merged[field] = max(values, key=len)

                logger.info(
                    f"Merged {len(group_periods)} duplicate periods for {year_key}: "
                    f"{[p.get('period') for p in group_periods]} -> {merged['period']}"
                )

                deduplicated.append(merged)

        # Sort by period name (chronological order)
        deduplicated.sort(key=lambda p: p.get("period", ""))

        return deduplicated

    def _parse_question_line(
        self,
        line: str,
        current_question: Dict[str, Any] | None,
        in_code_block: bool,
        code_block_lines: List[str],
        questions_list: List[Dict[str, Any]],
    ) -> tuple[Dict[str, Any] | None, bool, List[str]]:
        """Parse a single line from the interview questions section."""
        import re

        stripped = line.strip()

        # Start new question
        if stripped.startswith("### Q"):
            if current_question:
                questions_list.append(current_question)
            return (
                {
                    "question": "",
                    "category": "",
                    "evidence": "",
                    "follow_up_questions": [],
                    "key_listening_points": "",
                    "context": "",
                    "code_snippet": "",
                },
                in_code_block,
                code_block_lines,
            )

        if not current_question:
            return current_question, in_code_block, code_block_lines

        # Question text (bold line after ### Q)
        if stripped.startswith("**") and not any(
            x in stripped for x in ["**Based on", "**Follow-up", "**Key Listening"]
        ):
            if not current_question["question"]:
                current_question["question"] = stripped.replace("**", "")

        # Category (backtick-wrapped)
        elif stripped.startswith("`") and stripped.endswith("`"):
            current_question["category"] = stripped.replace("`", "")

        # Context field
        elif "**Context**" in line:
            current_question["context"] = (
                line.split(":")[-1]
                .strip()
                .replace("💼", "")
                .replace("**Context**", "")
                .strip()
                if ":" in line
                else ""
            )

        # Evidence field
        elif "Based on Evidence" in line:
            current_question["evidence"] = (
                line.split(":")[-1]
                .strip()
                .replace("📍", "")
                .replace("**Based on Evidence**", "")
                .strip()
                if ":" in line
                else ""
            )

        # Code block handling
        elif stripped.startswith("```"):
            if not in_code_block:
                in_code_block = True
                code_block_lines = [line]
            else:
                code_block_lines.append(line)
                current_question["code_snippet"] = "\n".join(code_block_lines)
                in_code_block = False
                code_block_lines = []

        elif in_code_block:
            code_block_lines.append(line)

        # Follow-up questions (numbered list)
        elif stripped and re.match(r"^\d+\.", stripped):
            follow_up = re.sub(r"^\d+\.\s*", "", stripped)
            current_question["follow_up_questions"].append(follow_up)

        # Key listening points (italic text)
        elif (
            stripped.startswith("*")
            and stripped.endswith("*")
            and not stripped.startswith("**")
        ):
            current_question["key_listening_points"] = stripped.replace("*", "")

        return current_question, in_code_block, code_block_lines

    def _sanitize_insights(self, insights: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove any scores, percentages, or ratings from insights.

        Portfolio analysis should be ZERO SCORES - purely evidence-based.
        """
        import re

        # Forbidden patterns that indicate scoring or inference
        FORBIDDEN_PATTERNS = [
            r"\d+/\d+",  # Scores like 7/10
            r"\d+%",  # Percentages like 75%
            r"\d+\.\d+",  # Decimal scores like 0.75
            r"score:\s*\d+",  # Score: 5
            r"rating:\s*\w+",  # Rating: high
            r"high|medium|low",  # Arbitrary ratings (context-dependent)
        ]

        # Forbidden inference phrases - ONLY THE EGREGIOUS ONES
        # Focus on blatant inferences about purpose, intent, or skill level
        FORBIDDEN_INFERENCE_PHRASES = [
            r"suggesting\s+these\s+may\s+be\s+(?:passion|hobby|portfolio|professional)",  # Inferring project purpose
            r"passion\s+project",  # Cannot determine intent
            r"hobby\s+project",  # Cannot determine intent
            r"portfolio\s+piece",  # Cannot determine purpose
            r"appears\s+to\s+be\s+(?:a|an)\s+(?:passion|hobby|portfolio)",  # Purpose inference
            r"(?:lacks|demonstrates|shows)\s+(?:strong|weak|poor|excellent)\s+(?:skill|ability|capability)",  # Skill judgment
        ]

        def sanitize_text(text: str) -> str:
            """Remove forbidden patterns from text and replace inference phrases."""
            if not isinstance(text, str):
                return text

            violations = []
            inference_violations = []

            # Check for scoring patterns
            for pattern in FORBIDDEN_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE):
                    violations.append(pattern)

            # Check for inference phrases and replace them
            for pattern in FORBIDDEN_INFERENCE_PHRASES:
                if re.search(pattern, text, re.IGNORECASE):
                    inference_violations.append(pattern)

            # Replace egregious inference phrases with neutral alternatives
            replacements = {
                r"passion\s+project": "personal project",
                r"hobby\s+project": "personal project",
                r"portfolio\s+piece": "project",
                r"suggesting\s+these\s+may\s+be\s+(?:passion|hobby|portfolio|professional)": "these are",
                r"appears\s+to\s+be\s+(?:a|an)\s+(?:passion|hobby|portfolio)": "is a",
            }

            for pattern, replacement in replacements.items():
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

            if violations:
                logger.warning(
                    "Portfolio insights sanitization: Found potential scores/ratings"
                )

            if inference_violations:
                logger.warning(
                    f"Portfolio insights sanitization: Found and replaced inference phrases. "
                    f"Patterns matched: {inference_violations}"
                )

            return text

        def sanitize_recursive(obj: Any) -> Any:
            """Recursively sanitize all values."""
            if isinstance(obj, dict):
                # Remove any keys that are explicitly scores/ratings
                filtered = {
                    k: sanitize_recursive(v)
                    for k, v in obj.items()
                    if k
                    not in [
                        "score",
                        "rating",
                        "percentage",
                        "quality_score",
                        "confidence_score",
                    ]
                }
                return filtered
            elif isinstance(obj, list):
                return [sanitize_recursive(item) for item in obj]
            elif isinstance(obj, str):
                return sanitize_text(obj)
            else:
                return obj

        result = sanitize_recursive(insights)
        return result if isinstance(result, dict) else insights

    def _get_fallback_insights(self, username: str) -> Dict[str, Any]:
        """
        Get fallback insights when AI generation fails.

        Args:
            username: GitHub username

        Returns:
            Basic insights structure
        """
        return {
            "executive_summary": f"Analysis pending for {username}. Manual review recommended.",
            "data_limitations_warning": "PUBLIC REPOSITORIES ONLY. Private work not visible.",
            "key_observations": [
                "Comprehensive analysis requires manual review",
                "AI generation encountered an error",
            ],
            "evidence_patterns": [
                {
                    "pattern": "Analysis Pending",
                    "evidence": "Manual review required for comprehensive insights",
                }
            ],
            "public_portfolio_evolution": [],
            "interview_questions": [
                {
                    "question": f"Tell me about your work on GitHub ({username})",
                    "category": "general",
                    "evidence": "Review portfolio for specific projects",
                    "context": "Understanding public contributions",
                    "follow_up_questions": [
                        "What are your main focus areas?",
                        "Which projects are you most proud of?",
                        "What technologies do you prefer working with?",
                    ],
                    "key_listening_points": "Technical depth and project ownership",
                }
            ],
            "positive_indicators": ["Analysis pending - manual review recommended"],
            "areas_to_explore": ["Complete portfolio review needed"],
            "recommendations": ["Conduct manual analysis of public repositories"],
            "quality_indicators": [
                {
                    "indicator": "Analysis Status",
                    "observation": "Automated analysis incomplete",
                    "scope": "public repositories only",
                    "implication": "Manual review required for hiring decision",
                }
            ],
            "confidence_explanation": "AI analysis failed. Manual review recommended for comprehensive assessment.",
        }

    def _parse_questions_from_response(
        self, response_text: str
    ) -> List[Dict[str, Any]]:
        """
        Parse interview questions from Phase 2 response.

        Based on hybrid_portfolio_analyzer.py parsing logic.

        Args:
            response_text: Raw text response from Phase 2 question generation

        Returns:
            List of parsed interview question dictionaries
        """
        import re

        questions = []
        lines = response_text.split("\n")
        current_question = None

        for line in lines:
            # Start of new question (### Q1, ### Q2, etc.)
            if line.strip().startswith("### Q"):
                if current_question:
                    questions.append(current_question)
                current_question = {
                    "question": "",
                    "category": "",
                    "evidence": "",
                    "follow_up_questions": [],
                    "key_listening_points": "",
                    "context": "",
                }

            # Question text (bold line after ### Q)
            elif (
                current_question
                and line.strip().startswith("**")
                and not line.strip().startswith("**Based on")
                and not line.strip().startswith("**Follow-up")
                and not line.strip().startswith("**Key Listening")
                and not line.strip().startswith("**Context")
            ):
                question_text = line.strip().replace("**", "")
                if not current_question["question"]:
                    current_question["question"] = question_text

            # Category (line with backticks)
            elif (
                current_question
                and line.strip().startswith("`")
                and line.strip().endswith("`")
            ):
                category = line.strip().replace("`", "")
                current_question["category"] = category

            # Context
            elif current_question and (
                "**Context**" in line or "💼 **Context**" in line
            ):
                context_text = (
                    line.split(":")[-1].strip() if ":" in line else line.strip()
                )
                context_text = (
                    context_text.replace("💼", "").replace("**Context**", "").strip()
                )
                current_question["context"] = context_text

            # Evidence
            elif current_question and (
                "Based on Evidence" in line or "📍 **Based on Evidence**" in line
            ):
                evidence = line.split(":")[-1].strip() if ":" in line else line.strip()
                evidence = (
                    evidence.replace("📍", "")
                    .replace("**Based on Evidence**", "")
                    .strip()
                )
                current_question["evidence"] = evidence

            # Follow-up questions (numbered list items)
            elif (
                current_question
                and line.strip()
                and line.strip()[0].isdigit()
                and "." in line
                and "Follow-up" not in line  # Skip the section header
            ):
                follow_up = re.sub(r"^\d+\.\s*", "", line.strip())
                current_question["follow_up_questions"].append(follow_up)  # type: ignore[attr-defined]

            # Key listening points (italic text)
            elif (
                current_question
                and line.strip().startswith("*")
                and line.strip().endswith("*")
                and not line.strip().startswith("**")
            ):
                listening_point = line.strip().replace("*", "")
                current_question["key_listening_points"] = listening_point

        # Append final question
        if current_question:
            questions.append(current_question)

        logger.info(
            f"Parsed {len(questions)} interview questions from Phase 2 response"
        )
        return questions
