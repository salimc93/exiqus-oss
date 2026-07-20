# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Evidence-based interview question generation.

This module generates sophisticated, context-aware interview questions based on
extracted evidence from repository analysis. Questions are tailored to probe
deeper into specific patterns, behaviors, and technical decisions.
"""

import json
from typing import Any, Dict, List, Optional

import anthropic

from ...utils.config import get_config
from ...utils.logging import get_logger
from ..tier_config import get_model_for_tier, get_tier_config, get_token_limit
from .context_prompts import ContextPromptEnhancer

logger = get_logger(__name__)


class QuestionBuilder:
    """Generate evidence-based interview questions from repository analysis."""

    def __init__(self, anthropic_api_key: Optional[str] = None) -> None:
        """
        Initialize question builder with Anthropic client.

        Args:
            anthropic_api_key: API key for Anthropic. If None, gets from config.
        """
        config = get_config()
        self.anthropic_client = anthropic.Anthropic(
            api_key=anthropic_api_key or config.anthropic_api_key
        )
        # Model configuration now comes from tier_config
        self.base_model = config.analysis.anthropic_model  # Fallback

        # Build model configuration from tier_config
        growth_tier = get_tier_config("professional")
        scale_tier = get_tier_config("enterprise")
        scale_plus_tier = get_tier_config("scale_plus")

        self.growth_questions_model = (
            get_model_for_tier("professional")  # Simplified: single model per tier
            if growth_tier
            else config.analysis.anthropic_model
        )
        self.scale_questions_model = (
            get_model_for_tier("enterprise")  # Simplified: single model per tier
            if scale_tier
            else config.analysis.anthropic_model
        )
        self.scale_plus_questions_model = (
            get_model_for_tier("scale_plus")  # Simplified: single model per tier
            if scale_plus_tier
            else self.scale_questions_model
        )

        # Keep legacy enterprise_model for backward compatibility
        self.enterprise_model = self.scale_questions_model

        # Token limits from tier config
        self.max_tokens = (
            get_token_limit("professional", "main") if growth_tier else 4000
        )
        self.enterprise_max_tokens = (
            get_token_limit("enterprise", "main") if scale_tier else 8192
        )
        self.scale_plus_max_tokens = (
            get_token_limit("scale_plus", "main") if scale_plus_tier else 8192
        )

        # Question categories for comprehensive coverage
        self.question_categories = [
            "technical_decisions",
            "collaboration_style",
            "problem_solving",
            "growth_mindset",
            "work_patterns",
            "quality_practices",
            "leadership_potential",
        ]

    def _get_role_level_guidance(self, role: str) -> str:
        """Get role-level specific guidance for question generation."""
        role_guidance = {
            "junior": {
                "years": "0-2 years",
                "focus": "Fundamentals, basic implementation, learning approach, debugging basics, code comprehension",
                "avoid": "Architecture decisions, scaling strategies, distributed systems, advanced design patterns, multi-team coordination",
                "complexity": "Surface-level technical understanding",
                "tone": "Encouraging, supportive, focused on learning journey",
                "example": "Walk me through how you debugged an issue in this code",
            },
            "mid": {
                "years": "2-5 years",
                "focus": "Implementation decisions, testing strategies, code quality practices, problem-solving methodology, API design basics",
                "avoid": "Org-wide architecture, executive decisions, multi-team coordination, infrastructure at scale",
                "complexity": "Moderate technical depth with practical application",
                "tone": "Neutral, invitational, assumes professional experience exists",
                "example": "How did you decide between approach A and B for this feature?",
            },
            "senior": {
                "years": "5+ years",
                "focus": "System architecture, scalability strategies, technical leadership, mentorship approach, system design, cross-team collaboration",
                "avoid": "Implementation minutiae, junior-level basics, overly simplistic questions",
                "complexity": "Deep technical expertise with leadership thinking",
                "tone": "Respectful, collaborative, assumes extensive private/professional work",
                "example": "How would you scale this system to handle 10x traffic?",
            },
        }

        role_level = role_guidance.get(role, role_guidance["senior"])

        return f"""
🎯 **ROLE LEVEL CONTEXT**: {role.upper()} ({role_level["years"]})

**CRITICAL: ADJUST QUESTION COMPLEXITY FOR {role.upper()} ROLE**

**{role.upper()}-Level Question Requirements**:
- **Focus on**: {role_level["focus"]}
- **Avoid**: {role_level["avoid"]}
- **Complexity Level**: {role_level["complexity"]}
- **Example Question Style**: "{role_level["example"]}"
- **Tone**: {role_level["tone"]}

⚠️ **CRITICAL: NO LOADED OR ACCUSATORY QUESTIONS**
- ❌ DO NOT frame questions as "Why isn't X visible?" or "What have you been doing?"
- ❌ DO NOT imply gaps in public activity are negative or need justification
- ❌ DO NOT ask defensive questions like "Tell me why you don't have..."
- ✅ DO frame questions as INVITATIONS to share experience: "Tell me about..." or "Walk me through..."
- ✅ DO assume positive intent - most professional work is in private repositories
- ✅ DO keep questions BROAD and OPEN-ENDED, not specific accusations
- ✅ DO acknowledge that public repos are ONE data point, not complete picture

**TONE GUIDANCE**:
- Assume professional experience exists (especially for mid/senior)
- Frame questions as collaborative exploration, not interrogation
- Focus on learning about their approach, not challenging their gaps

⚠️ **IMPORTANT FOR {role.upper()}: "Avoid minutiae" applies to QUESTIONS ONLY**
- ✅ DO generate ALL required sections: Evidence Patterns, Quality Indicators, Observations, etc.
- ✅ DO include factual repo-level details (dates, commit counts, technology adoption timeline)
- ❌ DO NOT skip Evidence Patterns thinking they are "minutiae" - they are REQUIRED factual observations
- The "avoid minutiae" guidance means: don't ask questions about line-by-line code implementation details
"""

    def generate_questions(
        self,
        evidence: Dict[str, Any],
        context: str = "general",
        tier: str = "professional",
        role: str = "senior",
    ) -> Dict[str, Any]:
        """
        Generate interview questions based on evidence.

        Args:
            evidence: All extracted evidence from repository analysis
            context: Hiring context (startup, enterprise, agency, etc.)
            tier: Subscription tier (affects question depth)
            role: Developer role level (junior, mid, senior) - defaults to senior

        Returns:
            Dictionary containing categorized questions with context
        """
        try:
            # Extract key evidence points for question generation
            evidence_summary = self._prepare_evidence_summary(evidence)

            # Generate questions using AI
            questions = self._generate_ai_questions(
                evidence_summary, context, tier, role
            )

            # Add metadata and scoring guidance
            enhanced_questions = self._enhance_questions(questions, evidence_summary)

            # Format for output
            return self._format_question_output(enhanced_questions, context, tier)

        except Exception as e:
            logger.error(f"Error generating questions: {e}")
            # Return empty questions if there's truly nothing to ask
            return {
                "context": context,
                "total_questions": 0,
                "estimated_time": "0-0 minutes",
                "questions_by_category": {},
                "all_questions": [],
                "interview_flow": [
                    "1. Start with work patterns to understand their style",
                    "2. Move to technical decisions to assess depth",
                    "3. Explore collaboration and communication",
                    "4. Address any red flags constructively",
                    "5. End with growth mindset and future goals",
                ],
                "key_areas_covered": [],
                "customization_notes": f"Questions tailored for {context} hiring context",
            }

    def _prepare_evidence_summary(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare a focused summary of evidence for question generation."""
        summary: Dict[str, Any] = {
            "key_findings": [],
            "red_flags": [],
            "positive_signals": [],
            "behavioral_patterns": {},
            "technical_patterns": {},
            "temporal_insights": {},
        }

        # Extract technical patterns
        if "technical_patterns" in evidence:
            for pattern in evidence["technical_patterns"]:
                if pattern.get("type") == "test_coverage_structure":
                    ratio = float(pattern.get("ratio", 0))
                    if ratio < 0.1:
                        summary["red_flags"].append(
                            {
                                "type": "low_test_coverage",
                                "detail": pattern["finding"],
                                "severity": "high",
                            }
                        )
                    elif ratio > 0.5:
                        summary["positive_signals"].append(
                            {"type": "good_test_coverage", "detail": pattern["finding"]}
                        )

                summary["key_findings"].append(
                    {
                        "category": "technical",
                        "finding": pattern.get("finding", ""),
                        "insight": pattern.get("insight", ""),
                    }
                )

        # Extract behavioral analysis
        if "behavioral_analysis" in evidence:
            behavioral = evidence["behavioral_analysis"]
            summary["behavioral_patterns"] = {
                "work_style": behavioral.get("work_style", "unknown"),
                "collaboration_level": behavioral.get("collaboration_level", "unknown"),
                "communication_quality": behavioral.get(
                    "communication_quality", "unknown"
                ),
                "work_life_balance": behavioral.get("work_life_balance", "unknown"),
            }

            # Extract specific insights
            for insight in behavioral.get("behavioral_insights", []):
                if insight["type"] == "work_life_concern":
                    summary["red_flags"].append(
                        {
                            "type": "burnout_risk",
                            "detail": insight["finding"],
                            "metrics": insight.get("metrics", {}),
                        }
                    )
                elif insight["type"] in ["work_consistency", "collaboration"]:
                    summary["positive_signals"].append(
                        {"type": insight["type"], "detail": insight["finding"]}
                    )

        # Extract temporal/skill evolution
        if "skill_evolution" in evidence:
            temporal = evidence["skill_evolution"]
            summary["temporal_insights"] = {
                "progression": temporal.get("development_trajectory", "unknown"),
                "growth_rate": temporal.get("growth_rate", 0.0),
                "recent_focus": temporal.get("recent_focus", "unknown"),
                "activity_trend": temporal.get("activity_trend", "unknown"),
            }

            # Add temporal insights to findings
            for insight in temporal.get("temporal_insights", []):
                summary["key_findings"].append(
                    {
                        "category": "growth",
                        "finding": insight.get("finding", ""),
                        "insight": insight.get("insight", ""),
                    }
                )

        # Extract collaboration patterns
        if "collaboration_patterns" in evidence:
            for pattern in evidence["collaboration_patterns"]:
                if pattern.get("type") == "collaboration":
                    summary["technical_patterns"]["collaboration"] = {
                        "contributors": pattern.get("top_contributors", []),
                        "style": pattern.get("finding", ""),
                    }
                elif pattern.get("type") == "commit_discipline":
                    summary["positive_signals"].append(
                        {"type": "professional_practices", "detail": pattern["finding"]}
                    )

        # Extract security issues
        if "security_issues" in evidence:
            for issue in evidence["security_issues"]:
                if issue.get("severity") == "high":
                    summary["red_flags"].append(
                        {
                            "type": "security",
                            "detail": issue["finding"],
                            "example": issue.get("commit_sha", ""),
                        }
                    )

        return summary

    def _generate_ai_questions(
        self,
        evidence_summary: Dict[str, Any],
        context: str,
        tier: str,
        role: str = "senior",
    ) -> List[Dict[str, Any]]:
        """Generate questions using Claude Haiku (dual-model for enterprise)."""

        if tier.lower() == "enterprise":
            # Enterprise tier: FULL Haiku 3.5 for testing
            return self._generate_enterprise_full_haiku35(
                evidence_summary, context, role
            )
        elif tier.lower() == "professional":
            # Professional tier: Haiku 3.5 for questions (dual-model approach)
            return self._generate_professional_haiku35_questions(
                evidence_summary, context, role
            )
        else:
            # Standard single-model approach
            return self._generate_standard_questions(
                evidence_summary, context, tier, role
            )

    def _generate_enterprise_dual_questions(
        self, evidence_summary: Dict[str, Any], context: str
    ) -> List[Dict[str, Any]]:
        """Generate enterprise questions using dual-model approach."""
        all_questions = []

        try:
            # Step 1: Generate standard professional questions with Haiku 3.0
            logger.info("Generating standard questions with Haiku 3.0...")
            standard_questions = self._generate_standard_questions(
                evidence_summary, context, "professional"
            )

            # Add source annotation
            for q in standard_questions:
                q["source"] = "haiku_3_0"
                q["tier"] = "professional"

            all_questions.extend(standard_questions)

            # Step 2: Generate premium insights with Haiku 3.5
            logger.info("Generating premium insights with Haiku 3.5...")
            premium_prompt = self._build_premium_question_prompt(
                evidence_summary, context
            )

            message = self.anthropic_client.messages.create(
                model=self.scale_questions_model,  # claude-3-5-sonnet-20241022 for enterprise
                max_tokens=self.enterprise_max_tokens,
                temperature=0.1,
                system="You are an expert interviewer. Always respond with valid JSON only, no additional text or markdown formatting.",
                messages=[{"role": "user", "content": premium_prompt}],
            )

            if isinstance(message.content[0], anthropic.types.TextBlock):
                response = message.content[0].text
            else:
                response = ""

            premium_questions = self._parse_ai_response(response)
            premium_questions = self._validate_questions(
                premium_questions, evidence_summary
            )

            # Add source annotation
            for q in premium_questions:
                q["source"] = "haiku_3_5"
                q["tier"] = "enterprise"
                q["premium"] = True

            all_questions.extend(premium_questions)

            logger.info(
                f"Enterprise dual-model: {len(standard_questions)} standard + {len(premium_questions)} premium = {len(all_questions)} total"
            )

            return all_questions

        except Exception as e:
            logger.error(f"Enterprise dual-model generation failed: {e}")
            # Fall back to single model
            return self._generate_standard_questions(
                evidence_summary, context, "enterprise"
            )

    def _generate_professional_haiku35_questions(
        self, evidence_summary: Dict[str, Any], context: str, role: str = "senior"
    ) -> List[Dict[str, Any]]:
        """Generate professional questions using Haiku 3.5 for GROWTH tier testing."""

        # Build prompt for professional-level questions
        prompt = self._build_question_generation_prompt(
            evidence_summary, context, "professional", role
        )

        try:
            # Use Haiku 3.5 for GROWTH tier questions
            message = self.anthropic_client.messages.create(
                model=self.growth_questions_model,  # claude-3-5-haiku-20241022
                max_tokens=self.max_tokens,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract text from response, handling different content block types
            response = ""
            if message.content:
                for block in message.content:
                    if hasattr(block, "text"):
                        response = block.text
                        break

            # Log response for debugging
            logger.debug(f"Haiku 3.5 response length: {len(response)}")

            questions = self._parse_ai_response(response)

            logger.info(
                f"Generated {len(questions)} professional questions with Haiku 3.5"
            )
            return self._validate_questions(questions, evidence_summary)

        except Exception as e:
            if "overloaded" in str(e).lower():
                logger.warning("API overloaded for GROWTH tier, retrying after delay")
                import time

                time.sleep(5)  # Simple 5 second delay
                # Retry once with same model
                try:
                    message = self.anthropic_client.messages.create(
                        model=self.growth_questions_model,
                        max_tokens=self.max_tokens,
                        temperature=0.1,
                        messages=[{"role": "user", "content": prompt}],
                    )
                    # Extract text from response, handling different content block types
                    response = ""
                    if message.content:
                        for block in message.content:
                            if hasattr(block, "text"):
                                response = block.text
                                break
                    questions = self._parse_ai_response(response)
                    return self._validate_questions(questions, evidence_summary)
                except Exception as retry_error:
                    logger.error(f"Retry failed: {retry_error}")

            logger.error(f"Error generating professional questions with Haiku 3.5: {e}")
            return self._generate_standard_questions(
                evidence_summary, context, "professional"
            )

    def _generate_enterprise_full_haiku35(
        self, evidence_summary: Dict[str, Any], context: str, role: str = "senior"
    ) -> List[Dict[str, Any]]:
        """Generate ALL questions using DUAL MODEL for SCALE tier testing."""

        # For SCALE: Use Haiku 3.5 for metrics, Sonnet 3.5 for questions
        prompt = f"""You are an expert technical interviewer for senior/staff engineering positions. Generate 15 in-depth interview questions for {context} senior engineering hiring.

CANDIDATE PROFILE:
{json.dumps(evidence_summary, indent=2)}

Generate 15 advanced technical questions that:
1. Probe system design and architectural decisions
2. Assess technical leadership and mentorship abilities
3. Evaluate problem-solving at scale
4. Explore cross-team collaboration and influence
5. Test deep technical expertise and best practices

Each question must include ALL of these fields:
{{
    "category": "system_design|technical_leadership|architecture|collaboration|deep_expertise|scaling",
    "question": "Advanced technical question that references specific evidence from their code",
    "evidence_reference": "Specific pattern or metric from their repository",
    "green_flags": [
        "First positive indicator of senior engineering capability",
        "Second sign of technical maturity",
        "Third marker of architectural thinking"
    ],
    "red_flags": [
        "First warning sign of technical gaps",
        "Second indicator of potential issues",
        "Third concern for senior role"
    ],
    "what_to_listen_for": "Specific technical depth and reasoning to assess",
    "context_relevance": "Why this matters for {context} senior engineering",
    "technical_focus": "The specific technical dimension being evaluated",
    "follow_up_probes": [
        "Deeper technical follow-up 1",
        "Architecture/scale probe 2"
    ]
}}

These are for companies paying $497/month for premium technical assessment - deliver exceptional, technically sophisticated questions.

Return ONLY a JSON array of exactly 15 questions."""

        try:
            # Use Sonnet 3.5 for SCALE tier questions
            from ...core.tier_config import TIER_CONFIGURATIONS

            sonnet_model = "claude-3-5-sonnet-20241022"
            logger.info("Using Sonnet 3.5 for SCALE tier executive questions")

            # Get tier-specific token limit
            tier_config = TIER_CONFIGURATIONS.get(
                "enterprise"
            )  # SCALE = enterprise tier
            max_tokens = (
                tier_config.main_generation_tokens if tier_config else 8192  # fallback
            )

            message = self.anthropic_client.messages.create(
                model=sonnet_model,
                max_tokens=max_tokens,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract text from response, handling different content block types
            response = ""
            if message.content:
                for block in message.content:
                    if hasattr(block, "text"):
                        response = block.text
                        break
            questions = self._parse_ai_response(response)

            logger.info(
                f"Generated {len(questions)} executive questions with Sonnet 3.5"
            )
            return self._validate_questions(questions, evidence_summary)

        except Exception as e:
            if "overloaded" in str(e).lower():
                logger.warning(
                    "API overloaded for SCALE tier, falling back to Haiku 3.5"
                )
                import time

                time.sleep(5)  # Simple 5 second delay
            else:
                logger.error(
                    f"Error generating executive questions with Sonnet 3.5: {e}"
                )
            # Fallback to Haiku 3.5
            return self._generate_enterprise_haiku35_fallback(evidence_summary, context)

    def _generate_enterprise_haiku35_fallback(
        self, evidence_summary: Dict[str, Any], context: str
    ) -> List[Dict[str, Any]]:
        """Fallback to Haiku 3.5 if Sonnet fails."""
        logger.warning("Falling back to Haiku 3.5 for questions")
        # Simplified prompt for Haiku 3.5
        prompt = """Generate 15 executive interview questions for {context} hiring.

Evidence: {json.dumps(evidence_summary.get('key_findings', [])[:3], indent=2)}

Format as JSON array with: category, question, evidence_reference, green_flags (2), red_flags (2), what_to_listen_for, executive_focus.

Return ONLY JSON array of 15 questions."""

        try:
            from ...core.tier_config import TIER_CONFIGURATIONS

            # Get tier-specific token limit
            tier_config = TIER_CONFIGURATIONS.get("enterprise")
            max_tokens = (
                tier_config.main_generation_tokens if tier_config else 8192  # fallback
            )

            message = self.anthropic_client.messages.create(
                model=self.enterprise_model,
                max_tokens=max_tokens,
                temperature=0.1,
                system="You are an expert technical interviewer. Always respond with valid JSON only, no additional text or markdown formatting.",
                messages=[{"role": "user", "content": prompt}],
            )
            # Extract text from response, handling different content block types
            response = ""
            if message.content:
                for block in message.content:
                    if hasattr(block, "text"):
                        response = block.text
                        break
            return self._parse_ai_response(response)
        except Exception as e:
            logger.error(f"Fallback also failed: {e}")
            return []

    def _generate_standard_questions(
        self,
        evidence_summary: Dict[str, Any],
        context: str,
        tier: str,
        role: str = "senior",
    ) -> List[Dict[str, Any]]:
        """Generate questions using single model (Haiku 3.0)."""

        # Build a comprehensive prompt
        prompt = self._build_question_generation_prompt(
            evidence_summary, context, tier, role
        )

        # Use base model for standard questions
        model = self.base_model
        max_tokens = self.max_tokens

        try:
            # Call Claude Haiku
            message = self.anthropic_client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=0.1,
                system="You are an expert technical interviewer. Your response must be a valid JSON array only, with no additional text, no markdown, no explanations. Start with [ and end with ].",
                messages=[{"role": "user", "content": prompt}],
            )
            if isinstance(message.content[0], anthropic.types.TextBlock):
                response = message.content[0].text
            else:
                response = ""

            # Parse the response
            questions = self._parse_ai_response(response)

            # Log what we got
            logger.info(
                f"AI returned {len(questions)} questions for {context} context, {tier} tier"
            )
            if len(questions) == 0:
                logger.warning(f"No questions generated. Response was: {response}")

            # Validate and enhance questions
            return self._validate_questions(questions, evidence_summary)

        except Exception as e:
            logger.error(f"AI question generation failed: {e}")
            # Fall back to rule-based generation
            return self._generate_rule_based_questions(evidence_summary, context)

    def _build_question_generation_prompt(
        self,
        evidence_summary: Dict[str, Any],
        context: str,
        tier: str,
        role: str = "senior",
    ) -> str:
        """Build a sophisticated prompt for question generation."""

        # Get context-specific enhancements
        context_enhancement = ContextPromptEnhancer.get_context_prompt(
            context, evidence_summary
        )

        # Get role-level guidance
        role_guidance = self._get_role_level_guidance(role)

        # Use evidence-based question prompt for better quality
        from ...ai.evidence_based_prompts import EVIDENCE_BASED_QUESTION_PROMPT

        # Format observations from evidence summary for the prompt
        observations_list = []

        # Convert key findings to observations
        for finding in evidence_summary.get("key_findings", []):
            if isinstance(finding, str):
                observations_list.append(f"- {finding}")
            elif isinstance(finding, dict):
                observations_list.append(
                    f"- {finding.get('type', 'Pattern')}: {finding.get('detail', finding.get('finding', ''))}"
                )

        # Add behavioral patterns
        behavioral_patterns = evidence_summary.get("behavioral_patterns", {})
        if isinstance(behavioral_patterns, list):
            # Handle list format (test case)
            for pattern in behavioral_patterns:
                observations_list.append(f"- Behavioral: {pattern}")
        elif isinstance(behavioral_patterns, dict):
            # Handle dict format
            for pattern_type, pattern_data in behavioral_patterns.items():
                if isinstance(pattern_data, dict) and pattern_data.get("pattern"):
                    observations_list.append(
                        f"- {pattern_type}: {pattern_data.get('pattern', '')}"
                    )

        # Add temporal insights
        temporal_insights = evidence_summary.get("temporal_insights", {})
        if isinstance(temporal_insights, list):
            # Handle list format (test case)
            for insight in temporal_insights:
                observations_list.append(f"- Temporal: {insight}")
        elif isinstance(temporal_insights, dict):
            # Handle dict format
            for insight_type, insight_data in temporal_insights.items():
                if isinstance(insight_data, str):
                    observations_list.append(f"- {insight_type}: {insight_data}")

        # Add technical patterns
        technical_patterns = evidence_summary.get("technical_patterns", [])
        if isinstance(technical_patterns, list):
            for pattern in technical_patterns:
                observations_list.append(f"- Technical: {pattern}")

        # Add strengths
        for strength in evidence_summary.get("strengths", []):
            observations_list.append(f"- Strength: {strength}")

        # Add concerns
        for concern in evidence_summary.get("concerns", []):
            observations_list.append(f"- Concern: {concern}")

        # Add red flags
        for flag in evidence_summary.get("red_flags", []):
            observations_list.append(f"- Red Flag: {flag}")

        # Add positive signals
        for signal in evidence_summary.get("positive_signals", []):
            observations_list.append(f"- Positive: {signal}")

        observations_text = (
            "\n".join(observations_list)
            if observations_list
            else "No specific patterns observed"
        )

        # For tier-specific prompts, we'll still use the template but customize
        if tier == "enterprise":
            prompt = (
                EVIDENCE_BASED_QUESTION_PROMPT.format(
                    observations=observations_text, context=context
                )
                + f"\n\n{role_guidance}\n\nGenerate {self._get_question_count(tier)} sophisticated questions for enterprise-level evaluation."
            )
        else:
            prompt = f"""You are an expert technical interviewer. Generate insightful interview questions based on the following evidence from a developer's GitHub repository analysis.

HIRING CONTEXT: {context}
TIER: {tier} (generate {"advanced" if tier == "enterprise" else "professional"} questions)

{context_enhancement}

{role_guidance}

EVIDENCE SUMMARY:

Key Findings:
{json.dumps(evidence_summary["key_findings"], indent=2)}

Behavioral Patterns:
{json.dumps(evidence_summary["behavioral_patterns"], indent=2)}

Temporal Insights:
{json.dumps(evidence_summary["temporal_insights"], indent=2)}

Red Flags:
{json.dumps(evidence_summary["red_flags"], indent=2)}

Positive Signals:
{json.dumps(evidence_summary["positive_signals"], indent=2)}

IMPORTANT: Generate exactly {self._get_question_count(tier)} interview questions. This is a firm requirement for the {tier} tier.

Each question must:
1. Reference specific evidence from the analysis
2. Probe deeper into patterns and decisions
3. Be tailored to the {context} hiring context
4. Include follow-up suggestions
5. Help assess cultural fit and technical depth

{"For enterprise tier, generate comprehensive questions that demonstrate the premium value of advanced AI insights." if tier == "enterprise" else ""}

Format each question as JSON:
{{
    "category": "technical_decisions|collaboration_style|problem_solving|growth_mindset|work_patterns|quality_practices|leadership_potential",
    "question": "The main question referencing specific evidence",
    "evidence_reference": "The specific finding this question is based on",
    "follow_ups": ["Potential follow-up question 1", "Potential follow-up question 2"],
    "what_to_listen_for": "Key points to evaluate in their response",
    "green_flags": ["Positive responses that indicate strong capabilities"],
    "red_flags": ["Concerning responses to watch for"],
    "context_relevance": "Why this matters for {context}"
}}

Focus on questions that reveal:
- Technical decision-making process
- How they handle challenges and setbacks
- Team collaboration and communication style
- Learning and growth mindset
- Problem-solving approach
- Quality and maintenance philosophy

IMPORTANT: Make questions specific to the evidence, not generic. Bad example: "Tell me about your testing philosophy." Good example: "I noticed your test coverage dropped from 80% to 0% over the last 6 months. Can you walk me through what led to this change?"

Return ONLY a JSON array of question objects, starting with [ and ending with ]. Do not include any text before or after the JSON array."""

        return prompt

    def _build_premium_question_prompt(
        self, evidence_summary: Dict[str, Any], context: str
    ) -> str:
        """Build premium question prompt for Haiku 3.5 (enterprise tier)."""

        prompt = f"""You are a senior technical interviewer specializing in staff/principal engineer assessment. Generate premium-quality interview questions that probe advanced technical capabilities.

HIRING CONTEXT: {context} (senior/staff/principal level)
FOCUS: Technical depth, architectural thinking, technical leadership

EVIDENCE SUMMARY:
{json.dumps(evidence_summary, indent=2)}

Generate 5-8 premium interview questions that focus on:
1. Complex system design and architectural decisions
2. Technical mentorship and knowledge sharing
3. Cross-team technical influence and collaboration
4. Performance optimization and scalability challenges
5. Technology evaluation and adoption strategies
6. Technical debt management and refactoring approaches
7. Code quality standards and engineering best practices

These questions should complement standard technical questions by probing:
- Trade-offs in technical decisions (not just solutions)
- Technical leadership and mentorship experience
- System-level thinking and long-term planning
- Problem-solving approach for complex challenges
- Ability to work across technical boundaries
- Communication of technical concepts

Format each question as JSON:
{{
    "category": "system_design|technical_leadership|architecture|performance|best_practices|collaboration",
    "question": "Advanced technical question referencing specific evidence",
    "evidence_reference": "The specific finding this question is based on",
    "follow_ups": ["Technical deep-dive follow-up 1", "Architecture follow-up 2"],
    "what_to_listen_for": "Technical depth and architectural thinking",
    "green_flags": ["Positive technical maturity indicators"],
    "red_flags": ["Concerning technical gaps or oversights"],
    "context_relevance": "Why this matters for senior {context} engineering",
    "technical_focus": "The specific technical dimension being assessed"
}}

IMPORTANT: These are premium questions for enterprise clients. Focus on technical insights valuable for senior engineering hiring decisions.

Return a JSON array of question objects."""

        return prompt

    def _get_question_count(self, tier: str) -> str:
        """Get number of questions to generate based on tier."""
        tier_questions = {
            "free": "7",  # Generate 7 but only show 3 clearly
            "basic": "7",
            "professional": "10",  # GROWTH tier
            "enterprise": "15",  # SCALE tier
        }
        return tier_questions.get(tier.lower(), "7")

    def _parse_ai_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse AI response into structured questions."""
        try:
            # Clean response first
            response = response.strip()

            # Try direct JSON parsing first
            try:
                data = json.loads(response)

                # Handle new format with categorized questions
                if isinstance(data, dict) and any(
                    key in data
                    for key in [
                        "technical_questions",
                        "behavioral_questions",
                        "context_questions",
                    ]
                ):
                    all_questions = []

                    # Extract technical questions
                    for q in data.get("technical_questions", []):
                        all_questions.append(
                            {
                                "category": "technical_decisions",
                                "question": q.get("question", ""),
                                "evidence_reference": q.get("observation_basis", ""),
                                "follow_ups": [q.get("what_to_explore", "")],
                                "context": "technical",
                            }
                        )

                    # Extract behavioral questions
                    for q in data.get("behavioral_questions", []):
                        all_questions.append(
                            {
                                "category": "collaboration_style",
                                "question": q.get("question", ""),
                                "evidence_reference": q.get("observation_basis", ""),
                                "follow_ups": [q.get("what_to_explore", "")],
                                "context": "behavioral",
                            }
                        )

                    # Extract context-specific questions
                    for q in data.get("context_questions", []):
                        all_questions.append(
                            {
                                "category": "problem_solving",
                                "question": q.get("question", ""),
                                "evidence_reference": q.get("observation_basis", ""),
                                "follow_ups": [q.get("what_to_explore", "")],
                                "context": "contextual",
                            }
                        )

                    return all_questions

                # Handle old array format
                elif isinstance(data, list):
                    return data

            except json.JSONDecodeError:
                pass

            # Try to extract JSON from markdown code blocks
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                if json_end > json_start:
                    json_str = response[json_start:json_end].strip()
                    try:
                        return self._parse_ai_response(
                            json_str
                        )  # Recursive call with extracted JSON
                    except Exception as e:
                        logger.debug(f"Failed to parse extracted JSON: {e}")

            # Try to find JSON array using regex
            import re

            json_pattern = r"\[\s*\{[^}]*\}(?:\s*,\s*\{[^}]*\})*\s*\]"
            matches = re.findall(json_pattern, response, re.DOTALL)
            if matches:
                # Try the longest match first
                for match in sorted(matches, key=len, reverse=True):
                    try:
                        questions = json.loads(match)
                        if isinstance(questions, list):
                            return questions
                    except json.JSONDecodeError:
                        continue

            # Last resort - try to find anything that looks like a JSON array
            start_idx = response.find("[")
            if start_idx >= 0:
                # Find the matching closing bracket
                bracket_count = 0
                end_idx = start_idx
                for i in range(start_idx, len(response)):
                    if response[i] == "[":
                        bracket_count += 1
                    elif response[i] == "]":
                        bracket_count -= 1
                        if bracket_count == 0:
                            end_idx = i + 1
                            break

                if end_idx > start_idx:
                    json_str = response[start_idx:end_idx]
                    try:
                        questions = json.loads(json_str)
                        if isinstance(questions, list):
                            return questions
                    except json.JSONDecodeError:
                        pass

            # If all parsing fails, log the issue
            logger.error("Failed to parse AI response as JSON")
            logger.debug(f"Response that failed to parse: {response[:500]}...")
            logger.debug(f"Full response: {response[:1000]}...")
            # Try to extract questions from plain text
            return self._extract_questions_from_text(response)

        except Exception as e:
            logger.error(f"Unexpected error parsing AI response: {e}")
            return self._extract_questions_from_text(response)

    def _extract_questions_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extract questions from plain text response."""
        questions = []

        # Simple extraction - look for question marks
        lines = text.split("\n")
        current_question = None

        for line in lines:
            line = line.strip()
            if line.endswith("?"):
                if current_question:
                    questions.append(current_question)
                current_question = {
                    "category": "general",
                    "question": line,
                    "evidence_reference": "Extracted from analysis",
                    "follow_ups": [],
                    "what_to_listen_for": "Clarity and depth of response",
                    "red_flags": [],
                    "context_relevance": "Relevant to technical assessment",
                }
            elif current_question and line.startswith("-"):
                # Might be a follow-up
                if isinstance(current_question["follow_ups"], list):
                    current_question["follow_ups"].append(line[1:].strip())

        if current_question:
            questions.append(current_question)

        return questions

    def _validate_questions(
        self, questions: List[Dict[str, Any]], evidence_summary: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Validate and enhance generated questions."""
        validated = []

        for q in questions:
            # Ensure all required fields
            if not isinstance(q, dict):
                continue

            # Add missing fields with defaults
            validated_q = {
                "category": q.get("category", "general"),
                "question": q.get("question", ""),
                "evidence_reference": q.get(
                    "evidence_reference", "Based on repository analysis"
                ),
                "follow_ups": q.get("follow_ups", []),
                "what_to_listen_for": q.get("what_to_listen_for", ""),
                "green_flags": q.get("green_flags", []),
                "red_flags": q.get("red_flags", []),
                "context_relevance": q.get("context_relevance", ""),
            }

            # Skip if no question
            if not validated_q["question"]:
                continue

            # Ensure follow_ups is a list
            if not isinstance(validated_q["follow_ups"], list):
                validated_q["follow_ups"] = [validated_q["follow_ups"]]

            # Ensure red_flags is a list
            if not isinstance(validated_q["red_flags"], list):
                validated_q["red_flags"] = [validated_q["red_flags"]]

            validated.append(validated_q)

        return validated

    def _generate_rule_based_questions(
        self, evidence_summary: Dict[str, Any], context: str
    ) -> List[Dict[str, Any]]:
        """Generate questions using rule-based approach as fallback."""
        questions = []

        # Generate questions based on red flags
        for red_flag in evidence_summary["red_flags"]:
            if red_flag["type"] == "low_test_coverage":
                questions.append(
                    {
                        "category": "quality_practices",
                        "question": f"I noticed {red_flag['detail']}. Can you explain your approach to testing and why you made this choice?",
                        "evidence_reference": red_flag["detail"],
                        "follow_ups": [
                            "How do you ensure code quality without tests?",
                            "What would be your testing strategy if you joined our team?",
                        ],
                        "what_to_listen_for": "Understanding of testing importance and pragmatic approach",
                        "red_flags": [
                            "Dismissive of testing",
                            "No quality assurance strategy",
                        ],
                        "context_relevance": f"Critical for {context} environment where quality is paramount",
                    }
                )
            elif red_flag["type"] == "burnout_risk":
                questions.append(
                    {
                        "category": "work_patterns",
                        "question": f"Your commit patterns show {red_flag['detail']}. How do you manage work-life balance?",
                        "evidence_reference": red_flag["detail"],
                        "follow_ups": [
                            "What drives these work patterns?",
                            "How do you prevent burnout?",
                        ],
                        "what_to_listen_for": "Self-awareness and sustainable practices",
                        "red_flags": ["Glorifying overwork", "No boundaries"],
                        "context_relevance": f"Important for long-term success in {context}",
                    }
                )

        # Generate questions based on behavioral patterns
        behavioral = evidence_summary["behavioral_patterns"]
        if behavioral["work_style"] != "unknown":
            questions.append(
                {
                    "category": "work_patterns",
                    "question": f"Your commits suggest a {behavioral['work_style']} work style. Can you describe your ideal development workflow?",
                    "evidence_reference": f"{behavioral['work_style']} work style detected",
                    "follow_ups": [
                        "How do you adapt when working with different styles?",
                        "What environments help you be most productive?",
                    ],
                    "what_to_listen_for": "Self-awareness and adaptability",
                    "red_flags": ["Inflexibility", "Unaware of own style"],
                    "context_relevance": f"Team fit consideration for {context}",
                }
            )

        # Generate questions based on positive signals
        for signal in evidence_summary["positive_signals"]:
            if signal["type"] == "good_test_coverage":
                questions.append(
                    {
                        "category": "quality_practices",
                        "question": f"I'm impressed by {signal['detail']}. What's your philosophy on balancing test coverage with development speed?",
                        "evidence_reference": signal["detail"],
                        "follow_ups": [
                            "How do you decide what to test?",
                            "Share an example where tests saved you from a major issue",
                        ],
                        "what_to_listen_for": "Pragmatic approach to testing",
                        "red_flags": [
                            "Dogmatic about 100% coverage",
                            "Tests for the sake of metrics",
                        ],
                        "context_relevance": f"Validates quality mindset needed for {context}",
                    }
                )

        # Add growth-focused question based on temporal insights
        temporal = evidence_summary["temporal_insights"]
        if temporal["progression"] != "unknown":
            questions.append(
                {
                    "category": "growth_mindset",
                    "question": f"Your repository shows {temporal['progression']} development trajectory. What's driving your learning journey?",
                    "evidence_reference": f"{temporal['progression']} progression detected",
                    "follow_ups": [
                        "What are you learning next?",
                        "How do you stay current with technology?",
                    ],
                    "what_to_listen_for": "Growth mindset and learning strategies",
                    "red_flags": ["No learning goals", "Resistant to new technologies"],
                    "context_relevance": f"Essential for evolving {context} environment",
                }
            )

        # If no questions generated, use fallback questions list
        if len(questions) == 0:
            questions = self._generate_fallback_questions_list(evidence_summary)

        return questions

    def _enhance_questions(
        self, questions: List[Dict[str, Any]], evidence_summary: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Enhance questions with additional metadata and scoring guidance."""
        enhanced = []

        for q in questions:
            # Add difficulty rating based on evidence
            q["difficulty"] = self._calculate_question_difficulty(q, evidence_summary)

            # Add time estimate
            q["time_estimate"] = (
                "2-5 minutes" if q["difficulty"] == "medium" else "5-10 minutes"
            )

            # Add scoring rubric
            q["scoring_rubric"] = {
                "excellent": "Demonstrates deep understanding and self-reflection",
                "good": "Shows awareness and reasonable approach",
                "fair": "Basic understanding but lacks depth",
                "poor": "Concerning gaps or problematic attitudes",
            }

            # Priority based on red flags
            has_red_flag_reference = any(
                rf["detail"] in q["evidence_reference"]
                for rf in evidence_summary["red_flags"]
            )
            q["priority"] = "high" if has_red_flag_reference else "medium"

            enhanced.append(q)

        # Sort by priority and category
        enhanced.sort(key=lambda x: (x["priority"], x["category"]))

        return enhanced

    def _calculate_question_difficulty(
        self, question: Dict[str, Any], evidence_summary: Dict[str, Any]
    ) -> str:
        """Calculate question difficulty based on evidence complexity."""
        # Questions about red flags are harder
        if any(
            rf["detail"] in question["evidence_reference"]
            for rf in evidence_summary["red_flags"]
        ):
            return "hard"

        # Questions about behavioral patterns are medium
        if question["category"] in ["work_patterns", "collaboration_style"]:
            return "medium"

        # Technical questions vary
        if question["category"] == "technical_decisions":
            if "architecture" in question["question"].lower():
                return "hard"
            else:
                return "medium"

        return "medium"

    def _apply_free_tier_blur(
        self, questions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Apply blurring to questions beyond the first 3 for free tier."""
        blurred_questions = []

        for i, question in enumerate(questions):
            if i < 3:
                # First 3 questions are shown clearly
                blurred_questions.append(question)
            else:
                # Blur remaining questions
                blurred_question = {
                    "category": question["category"],
                    "question": "████████████████████████████████████████████████",
                    "evidence_reference": "🔒 Upgrade to view evidence",
                    "follow_ups": ["🔒 Upgrade to see follow-up questions"],
                    "what_to_listen_for": "🔒 Upgrade to see evaluation criteria",
                    "red_flags": ["🔒 Upgrade to see red flags"],
                    "context_relevance": "🔒 Upgrade to see context relevance",
                    "is_blurred": True,
                    "upgrade_message": "This question is available in Basic, Professional, and Enterprise plans",
                }
                if hasattr(question, "difficulty"):
                    blurred_question["difficulty"] = question.get(
                        "difficulty", "medium"
                    )
                if hasattr(question, "priority"):
                    blurred_question["priority"] = question.get("priority", "medium")
                blurred_questions.append(blurred_question)

        return blurred_questions

    def _format_question_output(
        self, questions: List[Dict[str, Any]], context: str, tier: str = "professional"
    ) -> Dict[str, Any]:
        """Format the final question output."""
        # Apply free tier limitations
        if tier.lower() == "free":
            questions = self._apply_free_tier_blur(questions)

        return {
            "context": context,
            "total_questions": len(questions),
            "estimated_time": f"{len(questions) * 5}-{len(questions) * 10} minutes",
            "questions_by_category": self._group_by_category(questions),
            "all_questions": questions,
            "interview_flow": self._suggest_interview_flow(questions),
            "key_areas_covered": (
                list(set(q["category"] for q in questions))
                if tier.lower() != "free"
                else [q["category"] for q in questions[:3]]
            ),
            "customization_notes": f"Questions tailored for {context} hiring context",
            "upgrade_prompt": (
                "🔓 Upgrade to see all questions with full details"
                if tier.lower() == "free" and len(questions) > 3
                else None
            ),
        }

    def _group_by_category(
        self, questions: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group questions by category."""
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for q in questions:
            category = q["category"]
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(q)
        return grouped

    def _suggest_interview_flow(self, questions: List[Dict[str, Any]]) -> List[str]:
        """Suggest an interview flow based on questions."""
        flow = [
            "1. Start with work patterns to understand their style",
            "2. Move to technical decisions to assess depth",
            "3. Explore collaboration and communication",
            "4. Address any red flags constructively",
            "5. End with growth mindset and future goals",
        ]

        # Customize based on actual questions
        if any(q.get("priority") == "high" for q in questions):
            flow.insert(0, "0. Begin with rapport building before addressing concerns")

        return flow

    def _generate_fallback_questions_list(
        self, evidence: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate basic fallback questions as a list if all else fails."""
        questions = [
            {
                "category": "general",
                "question": "Can you walk me through a recent technical challenge you solved?",
                "evidence_reference": "General assessment",
                "follow_ups": ["What did you learn from this experience?"],
                "what_to_listen_for": "Problem-solving approach",
                "red_flags": ["No specific examples"],
                "context_relevance": "Universal technical assessment",
                "priority": "medium",
                "difficulty": "medium",
                "time_estimate": "5-10 minutes",
                "scoring_rubric": {
                    "excellent": "Detailed example with clear problem-solving process",
                    "good": "Solid example with some detail",
                    "fair": "Basic example but lacks depth",
                    "poor": "No concrete example or vague response",
                },
            },
            {
                "category": "collaboration_style",
                "question": "Describe your ideal team environment and collaboration style.",
                "evidence_reference": "Team fit assessment",
                "follow_ups": ["How do you handle disagreements?"],
                "what_to_listen_for": "Self-awareness and flexibility",
                "red_flags": ["Only works alone", "Conflict avoidance"],
                "context_relevance": "Team dynamics evaluation",
                "priority": "medium",
                "difficulty": "medium",
                "time_estimate": "5-10 minutes",
                "scoring_rubric": {
                    "excellent": "Shows adaptability and constructive collaboration",
                    "good": "Clear preferences with flexibility",
                    "fair": "Basic understanding of teamwork",
                    "poor": "Rigid or concerning attitudes",
                },
            },
            {
                "category": "growth_mindset",
                "question": "What are you currently learning and why?",
                "evidence_reference": "Growth potential",
                "follow_ups": ["How do you stay updated?"],
                "what_to_listen_for": "Curiosity and learning strategies",
                "red_flags": ["Not learning anything", "Stuck in comfort zone"],
                "context_relevance": "Future potential assessment",
                "priority": "medium",
                "difficulty": "easy",
                "time_estimate": "5 minutes",
                "scoring_rubric": {
                    "excellent": "Active learning with clear goals",
                    "good": "Some learning activities",
                    "fair": "Minimal learning efforts",
                    "poor": "No current learning",
                },
            },
        ]

        # Add evidence-based questions if we have specific patterns
        if evidence.get("technical_patterns"):
            for pattern in evidence.get("technical_patterns", [])[:2]:
                if pattern.get("type") == "test_coverage_structure":
                    questions.append(
                        {
                            "category": "quality_practices",
                            "question": f"I noticed your repository has {pattern.get('finding', 'some test coverage')}. Can you walk me through your testing philosophy?",
                            "evidence_reference": pattern.get(
                                "finding", "Test coverage analysis"
                            ),
                            "follow_ups": [
                                "How do you decide what to test?",
                                "What's your approach to test maintenance?",
                            ],
                            "what_to_listen_for": "Testing strategy and quality mindset",
                            "red_flags": [
                                "No testing philosophy",
                                "Tests as afterthought",
                            ],
                            "context_relevance": "Code quality assessment",
                            "priority": "high",
                            "difficulty": "medium",
                            "time_estimate": "5-10 minutes",
                            "scoring_rubric": {
                                "excellent": "Clear testing strategy with business value focus",
                                "good": "Solid understanding of testing importance",
                                "fair": "Basic testing knowledge",
                                "poor": "Limited testing experience",
                            },
                        }
                    )
                    break

        return questions
