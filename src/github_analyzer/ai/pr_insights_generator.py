# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
PR Insights Generator using AI models.

This module generates insights from PR analysis evidence using
tier-appropriate AI models (Sonnet for Scale+).
"""

import json
from typing import Any, Dict, List, Optional

from ..core.pr_context_prompts import enhance_pr_evidence_with_context
from ..core.tier_config import get_model_for_tier, get_token_limit
from ..data.pr_models import PREvidence, QualitySignals
from ..utils.logging import get_logger
from .anthropic_wrapper import AnthropicWrapper

logger = get_logger(__name__)


class PRInsightsGenerator:
    """Generate AI-powered insights from PR analysis evidence."""

    def __init__(self, anthropic_api_key: str) -> None:
        """
        Initialize PR insights generator.

        Args:
            anthropic_api_key: API key for Anthropic
        """
        self.anthropic = AnthropicWrapper(anthropic_api_key)

    def _get_role_level_guidance(self, role: str) -> str:
        """Get role-level specific guidance for interview question generation."""
        role_guidance = {
            "junior": {
                "level": "Junior Developer",
                "years": "0-2 years",
                "focus": "Fundamentals, basic implementation, learning approach, debugging basics, code comprehension",
                "avoid": "Architecture decisions, scaling strategies, distributed systems, advanced design patterns, multi-team coordination",
                "complexity": "Surface-level technical understanding",
                "tone": "Encouraging, supportive, focused on learning journey",
                "example": "Walk me through how you debugged an issue in this PR",
            },
            "mid": {
                "level": "Mid-Level Developer",
                "years": "2-5 years",
                "focus": "Implementation decisions, testing strategies, code quality practices, problem-solving methodology, API design basics",
                "avoid": "Org-wide architecture, executive decisions, multi-team coordination, infrastructure at scale",
                "complexity": "Moderate technical depth with practical application",
                "tone": "Neutral, invitational, assumes professional experience exists",
                "example": "How did you decide between approach A and B for this PR?",
            },
            "senior": {
                "level": "Senior Developer",
                "years": "5+ years",
                "focus": "System architecture, scalability strategies, technical leadership, mentorship approach, system design, cross-team collaboration",
                "avoid": "Implementation minutiae, junior-level basics, overly simplistic questions",
                "complexity": "Deep technical expertise with leadership thinking",
                "tone": "Respectful, collaborative, assumes extensive private/professional work",
                "example": "How would you scale this system to handle 10x traffic?",
            },
        }

        role_config = role_guidance.get(role, role_guidance["senior"])

        return f"""
🎯 **ROLE LEVEL CONTEXT**: {role_config["level"].upper()} ({role_config["years"]})

**CRITICAL: ADJUST INTERVIEW QUESTION COMPLEXITY FOR {role_config["level"].upper()} ROLE**

**{role_config["level"].upper()}-Level Interview Question Requirements**:
- **Focus on**: {role_config["focus"]}
- **Avoid**: {role_config["avoid"]}
- **Complexity Level**: {role_config["complexity"]}
- **Example Question Style**: "{role_config["example"]}"
- **Tone**: {role_config["tone"]}

⚠️ **CRITICAL: NO LOADED OR ACCUSATORY QUESTIONS**
- ❌ DO NOT frame questions as "Why isn't X visible?" or "What have you been doing?"
- ❌ DO NOT imply gaps in PR activity are negative or need justification
- ❌ DO NOT ask defensive questions like "Tell me why you don't have..."
- ✅ DO frame questions as INVITATIONS to share experience: "Tell me about..." or "Walk me through..."
- ✅ DO assume positive intent - most professional work is in private repositories
- ✅ DO keep questions BROAD and OPEN-ENDED, not specific accusations
- ✅ DO acknowledge that public PRs are ONE data point, not complete picture

**TONE GUIDANCE**:
- Assume professional experience exists (especially for mid/senior)
- Frame questions as collaborative exploration, not interrogation
- Focus on learning about their approach, not challenging their gaps
"""

    def generate_insights(
        self,
        username: str,
        evidence: PREvidence,
        quality_signals: QualitySignals,
        context: str = "OPEN_SOURCE",
        tier: str = "scale_plus",
        repos_contributed: Optional[List[str]] = None,
        role: str = "senior",
    ) -> Dict[str, Any]:
        """
        Generate AI insights from PR evidence.

        Args:
            username: GitHub username analyzed
            evidence: PR evidence extracted
            quality_signals: Quality signals from analysis
            context: Analysis context (STARTUP, ENTERPRISE, etc.)
            tier: User subscription tier (determines AI model)
            repos_contributed: List of repository names contributed to
            role: Role level for interview questions (junior, mid, senior)

        Returns:
            Dictionary containing AI-generated insights
        """
        try:
            logger.info(
                f"Generating PR insights for {username} "
                f"(context: {context}, tier: {tier})"
            )

            # Get appropriate model for tier (simplified: single model per tier)
            model = get_model_for_tier(tier)
            if not model:
                logger.warning(f"No model configured for tier {tier}, using default")
                model = "claude-3-haiku-20240307"

            # Get tier-specific token limit to leverage full model capacity
            max_tokens = get_token_limit(tier, limit_type="main")
            logger.info(
                f"Using tier-specific token limit for {tier}: {max_tokens} tokens"
            )

            # Build evidence summary
            evidence_summary = self._build_evidence_summary(
                username, evidence, quality_signals, repos_contributed or []
            )

            # Enhance with context-specific prompts
            enhanced_prompt = enhance_pr_evidence_with_context(
                evidence_summary, context
            )

            # Get role-level guidance
            role_guidance = self._get_role_level_guidance(role)

            # Add specific instructions for insights generation
            full_prompt = f"""
{enhanced_prompt}

{role_guidance}

Based on the PR evidence above, generate the following comprehensive analysis:

1. **Key Strengths** (7-10 detailed observations)
   - What does this developer excel at based on their PR history?
   - What patterns show consistent quality or expertise?
   - Include specific PR examples where possible

2. **Technical Capabilities** (7-10 specific skills/patterns)
   - What technical skills are demonstrated through their PRs?
   - What technologies/frameworks do they work with effectively?
   - What architectural patterns or practices do they follow?
   - How do they handle technical challenges?

3. **Collaboration & Communication** (5-7 observations)
   - How do they work with others based on review patterns?
   - What does their PR communication style reveal?
   - How do they handle feedback and iterations?
   - What about their pair programming or co-authorship patterns?

4. **Code Quality Indicators** (5-7 patterns)
   - Testing practices evident in PRs
   - Documentation habits
   - Refactoring and maintenance patterns
   - Performance considerations

5. **Areas for Deep Dive** (5-7 specific topics)
   - What questions would help clarify their capabilities?
   - What patterns deserve deeper exploration?
   - Specific PRs that need discussion
   - Potential growth areas to explore

6. **Context Fit Assessment for {context}**
   - How well do their PR patterns align with {context} environment needs?
   - What evidence supports or challenges this fit?
   - Specific examples that demonstrate fit or misalignment

7. **Notable Contributions** (3-5 highlights)
   - Most impactful PRs or features
   - Complex problems solved
   - Leadership or mentorship examples

8. **Interview Questions** (10-15 detailed questions)
   Generate comprehensive interview questions with the following structure for each:
   - Main question (specific and evidence-based)
   - Category (technical/collaboration/process/growth)
   - Evidence reference (specific PR numbers or patterns)
   - 3 follow-up questions
   - Key listening points (what to evaluate in their answer)

CRITICAL: PRIORITIZATION RULES FOR KEY_INSIGHTS AND KEY_STRENGTHS
When ranking insights and strengths, prioritize by HIRING IMPACT, not just size metrics:

1. **Assigned PRs with High Commits** = Highest Priority
   - PRs assigned to the user by others (shows team trust) with 500+ commits
   - Example: Assigned to "Debugger implementation" with 977 commits ranks HIGHER than self-authored "Transition to GPUI 3" with 246 commits
   - Team assignment + high commit count = major trusted execution

2. **Product Features > Infrastructure**
   - Product features (Debugger, Authentication, Payment) > Infrastructure migrations (GPUI 3 transition, dependency updates)
   - Features directly impact users and product success
   - Migrations are important but secondary to product capabilities

3. **Commit Count × Assignment Weight > Raw Line Count**
   - 977 commits (assigned) > 246 commits (self) even if line count is lower
   - Commits indicate complexity and iteration, not just volume
   - Use this formula: (commit_count × (2 if assigned else 1)) as primary sort key

4. **Context-Specific Weighting**
   - STARTUP: Prioritize product features, user-facing work, fast delivery
   - ENTERPRISE: Prioritize scale, reliability, process adherence
   - OPEN_SOURCE: Prioritize community collaboration, documentation, review engagement
   - AGENCY: Prioritize client-facing work, diverse tech stack, rapid delivery

APPLY THESE RULES when ordering key_insights (top 5-7) and key_strengths (top 7-10).
The FIRST insight/strength should be the highest hiring-impact work based on these criteria.

Format your response as JSON with the following structure:
{{
    "interview_questions": [
        {{
            "question": "Main interview question referencing specific PR or pattern",
            "category": "technical|collaboration|process|growth",
            "evidence_reference": "Specific PR #XXX or pattern from evidence",
            "context_note": "Why this matters for {context} environment",
            "hiring_implication": "How this evidence relates to hiring decision for {context} role",
            "follow_up_questions": [
                "Follow-up question 1",
                "Follow-up question 2",
                "Follow-up question 3"
            ],
            "key_listening_points": "What to evaluate in their response"
        }},
        ... // 10-15 detailed questions
    ],
    "key_insights": [
        {{
            "title": "Insight Title",
            "category": "technical_skills|collaboration|work_patterns|technical_practices",
            "description": "Detailed description of the insight with evidence",
            "evidence": "Specific PR numbers, patterns, or measurable data",
            "impact": "positive|negative|neutral",
            "hiring_implication": "How this insight affects hiring decision for {context} environment"
        }},
        ... // 5-7 detailed insights
    ],
    "key_strengths": [
        "Detailed strength 1 with evidence",
        "Detailed strength 2 with evidence",
        ... // 7-10 items
    ],
    "technical_capabilities": [
        "Specific technical capability 1",
        "Specific technical capability 2",
        ... // 7-10 items
    ],
    "collaboration_style": [
        "Collaboration observation 1 with example",
        "Collaboration observation 2 with example",
        ... // 5-7 items
    ],
    "code_quality_indicators": [
        "Quality pattern 1",
        "Quality pattern 2",
        ... // 5-7 items
    ],
    "areas_for_discussion": [
        "Specific area 1 with context",
        "Specific area 2 with context",
        ... // 5-7 items
    ],
    "notable_contributions": [
        "Highlight 1 with impact",
        "Highlight 2 with impact",
        ... // 3-5 items
    ],
    "context_fit": {{
        "alignment": "strong|moderate|needs_discussion",
        "supporting_evidence": [
            "Detailed evidence 1",
            "Detailed evidence 2",
            ... // 5-7 items
        ],
        "considerations": [
            "Important consideration 1",
            "Important consideration 2",
            ... // 3-5 items
        ],
        "specific_strengths_for_context": [
            "Context-specific strength 1",
            "Context-specific strength 2",
            ... // 3-5 items
        ],
    }},
    "recommendations": [
        "Actionable recommendation 1 for interview focus",
        "Actionable recommendation 2 for assessment approach",
        ... // 5-7 items
    ],
    "data_limitations": [
        "Cannot assess X due to Y limitation",
        "No visibility into Z aspect",
        ... // 7-10 items covering BOTH technical AND strategic/soft skill limitations
        // REQUIRED: Include limitations about technical decision-making, cross-functional collaboration,
        // communication to non-technical stakeholders, performance under pressure, and product thinking
    ],
    "quality_indicators": {{
        "positive_indicators": [
            "Quality pattern 1: Description with evidence",
            "Quality pattern 2: Description with evidence",
            ... // 5-7 items
        ],
        "areas_to_explore": [
            "Area needing exploration: Description with evidence",
            "Another area: Description with evidence",
            ... // 3-5 items
        ]
    }},
    "executive_summary": "2-3 sentence summary focusing on {context} fit based on PR contribution patterns. Highlight key technical strengths, collaboration patterns, and notable achievements with specific evidence. Be concrete and hiring-focused.",
    "confidence_explanation": "Explain OUR confidence in THIS ANALYSIS based on PR data availability and sample size. Frame as 'Based on available PR data, we have [HIGH/MODERATE/LIMITED] confidence in this analysis.' Do NOT say 'PR data quality is poor' - instead say 'our confidence is limited due to [specific data constraints].' Specify PR volume, pattern consistency, evidence completeness. Be clear about what we CAN and CANNOT confidently assess from the available data."
}}

CRITICAL EVIDENCE-ONLY REQUIREMENTS:
- Generate AT LEAST the minimum number of items specified for each section
- Base ALL observations STRICTLY on the provided PR evidence data ONLY
- Include specific PR references, numbers, dates, or measurable patterns where available

FORBIDDEN INFERENCES - DO NOT SPECULATE:
- NEVER speculate WHY PRs were not merged (could be closed, abandoned, project archived, or legitimately rejected)
- NEVER assume different data points represent the same PR unless explicitly stated (e.g., "500+ line PR" ≠ "2-day PR" unless proven)
- NEVER infer "sustained engagement" or "consistent activity" from date ranges alone - could be sparse or clustered
- NEVER extrapolate "developer focus" or "priorities" from PR type classifications alone
- NEVER infer "collaboration style" or "team dynamics" from timing data or merge speeds alone
- NEVER make negative assumptions about unmerged PRs - absence of merge ≠ failure
- NEVER conflate separate metrics without evidence they're related
- FORBIDDEN: Corporate jargon like "bureaucracy", "synergy", "culture fit", "soft skills"
- FORBIDDEN: Inferences about personality, work style, or preferences not directly observable in PRs
- FORBIDDEN: Assumptions about team dynamics beyond what's directly shown in PR interactions

REQUIRED EVIDENCE-BASED APPROACH:
- State WHAT the evidence shows (e.g., "1 merged, 5 not merged") NOT what it might mean
- For interview questions: Ask to EXPLORE unknowns, NEVER assume negative explanations
  - BAD: "What caused your low merge rate?" (assumes problem + negative framing)
  - GOOD: "Tell me about your 6 PRs - what happened with the 5 that weren't merged?" (neutral exploration)
- Use specific numbers, dates, PR patterns, code changes, review cycles, merge patterns
- State "based on X PRs showing Y pattern" or "evidenced by Z specific examples"
- When data is missing or unclear, explicitly state "Cannot assess X from available evidence"
- Be detailed and specific with measurable evidence, never generic or inferential
- Focus on observable behaviors in PRs, NOT inferred motivations or capabilities

CRITICAL: REPOSITORY OWNERSHIP DISTINCTION
- ALWAYS distinguish between external repositories (valuable open-source contributions) vs own repositories (personal projects)
- External contributions show: open-source collaboration, ability to work in unfamiliar codebases, community engagement
- Own repository contributions show: personal project ownership, initiative, but less collaboration evidence
- When discussing "repository experience" or "cross-repo work", ONLY count external repositories
- Example: If evidence shows "External repositories: 5 (aclysma/profiling, gfx-rs/wgpu...) and Own repositories: 2 (username/project1, username/project2)", then highlight the 5 external repos as the valuable multi-repo experience
"""

            # Call AI model
            logger.info(f"Calling {model} for PR insights generation")
            logger.info(f"Full prompt length: {len(full_prompt)} characters")
            logger.info(f"First 500 chars of prompt: {full_prompt[:500]}")

            # Log the actual model being used
            logger.info(f"Using model: {model}")
            logger.info(f"Max tokens: {max_tokens}")
            logger.info("Temperature: 0.3")

            response = self.anthropic.create_message(
                system="You are an expert technical recruiter analyzing developer PR contributions.",
                messages=[{"role": "user", "content": full_prompt}],
                model=model,
                max_tokens=max_tokens,
                temperature=0.3,  # Lower temperature for more focused analysis
            )

            logger.info(f"AI response type: {type(response)}")
            logger.info(f"AI response has content: {hasattr(response, 'content')}")
            if hasattr(response, "content"):
                logger.info(f"AI response content type: {type(response.content)}")
                logger.info(
                    f"AI response content length: {len(response.content) if response.content else 0}"
                )
                if response.content and len(response.content) > 0:
                    logger.info(f"First content item type: {type(response.content[0])}")
                    if hasattr(response.content[0], "text"):
                        logger.info(
                            f"Response text length: {len(response.content[0].text)}"
                        )
                        logger.info(
                            f"First 200 chars: {response.content[0].text[:200]}"
                        )

            # Parse response
            try:
                # Extract text content from the response - better error handling
                if not response:
                    logger.error("Response is None")
                    raise ValueError("No response from AI")

                if not hasattr(response, "content") or not response.content:
                    logger.error(f"Response has no content. Response: {response}")
                    raise ValueError("Response has no content")

                if len(response.content) == 0:
                    logger.error("Response content is empty list")
                    raise ValueError("Response content is empty")

                # Log the full response structure for debugging
                logger.info(f"Response content length: {len(response.content)}")
                logger.info(f"Response content[0] type: {type(response.content[0])}")

                response_text = ""
                if hasattr(response.content[0], "text"):
                    response_text = response.content[0].text
                    logger.info(
                        f"Extracted text from response, length: {len(response_text)}"
                    )
                else:
                    logger.error(
                        f"Response content[0] has no text attribute: {response.content[0]}"
                    )
                    response_text = str(response.content[0])

                if not response_text:
                    logger.error("Response text is empty")
                    raise ValueError("Response text is empty")

                # Log first 500 chars of response for debugging
                logger.info(f"Response text first 500 chars: {response_text[:500]}")

                # Strip markdown code block formatting if present
                if response_text.startswith("```json"):
                    response_text = response_text[7:]  # Remove ```json
                    if response_text.endswith("```"):
                        response_text = response_text[:-3]  # Remove closing ```
                    response_text = response_text.strip()
                elif response_text.startswith("```"):
                    response_text = response_text[3:]  # Remove ```
                    if response_text.endswith("```"):
                        response_text = response_text[:-3]  # Remove closing ```
                    response_text = response_text.strip()

                insights = json.loads(response_text)

                # Apply behavioral inference sanitization to all text fields
                insights = self._sanitize_insights(insights)

                logger.info(f"Successfully generated PR insights for {username}")
                return {
                    "success": True,
                    "insights": insights,
                    "model_used": model,
                    "context": context,
                }
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI response as JSON: {e}")
                logger.error(
                    f"Raw response text: {response_text[:1000] if response_text else 'Empty'}"
                )
                # Return structured fallback
                return {
                    "success": False,
                    "error": "Failed to parse AI response",
                    "raw_response": (
                        response_text[:500] if response_text else ""
                    ),  # First 500 chars for debugging
                    "insights": self._get_fallback_insights(),
                }

        except Exception as e:
            logger.error(f"Error generating PR insights: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "insights": self._get_fallback_insights(),
            }

    def _build_evidence_summary(
        self,
        username: str,
        evidence: PREvidence,
        quality_signals: QualitySignals,
        repos_contributed: List[str],
    ) -> str:
        """
        Build a comprehensive evidence summary for AI processing.

        Args:
            username: GitHub username
            evidence: PR evidence
            quality_signals: Quality signals
            repos_contributed: List of repository names

        Returns:
            Formatted evidence summary string
        """
        summary_parts = []

        # Header
        summary_parts.append(f"PR ANALYSIS EVIDENCE FOR: {username}")
        summary_parts.append("=" * 60)

        # Key metrics
        summary_parts.append("\nKEY METRICS:")
        summary_parts.append(f"- Total PRs analyzed: {quality_signals.total_prs}")
        summary_parts.append(f"- PRs merged: {quality_signals.merged_prs}")
        summary_parts.append(f"- Repositories: {quality_signals.unique_repos}")

        # CRITICAL: Distinguish between owned repos vs external contributions
        if repos_contributed:
            owned_repos = [r for r in repos_contributed if r.startswith(f"{username}/")]
            external_repos = [
                r for r in repos_contributed if not r.startswith(f"{username}/")
            ]

            if external_repos:
                summary_parts.append(
                    f"- External repositories contributed to: {len(external_repos)}"
                )
                summary_parts.append(f"  {', '.join(external_repos)}")
            if owned_repos:
                summary_parts.append(f"- Own repositories: {len(owned_repos)}")
                summary_parts.append(f"  {', '.join(owned_repos)}")

            summary_parts.append(
                f"\nIMPORTANT: External repository contributions ({len(external_repos)}) show open-source collaboration and ability to work in unfamiliar codebases. Own repository contributions ({len(owned_repos)}) show personal project ownership."
            )

        summary_parts.append(
            f"- Time span: {quality_signals.contribution_timespan or 'Unknown'}"
        )
        summary_parts.append(f"- Feature PRs: {quality_signals.feature_prs}")
        summary_parts.append(f"- Fix PRs: {quality_signals.fix_prs}")

        # Technical patterns
        if evidence.technical_substance:
            summary_parts.append("\nTECHNICAL PATTERNS:")
            for item in evidence.technical_substance[:5]:
                summary_parts.append(f"- {item}")

        # Collaboration patterns
        if evidence.collaboration_patterns:
            summary_parts.append("\nCOLLABORATION PATTERNS:")
            for item in evidence.collaboration_patterns[:5]:
                summary_parts.append(f"- {item}")

        # Cross-repo work
        if evidence.cross_repo_contributions:
            summary_parts.append("\nCROSS-REPOSITORY WORK:")
            for item in evidence.cross_repo_contributions[:3]:
                summary_parts.append(f"- {item}")

        # Review engagement
        if evidence.review_responsiveness:
            summary_parts.append("\nREVIEW ENGAGEMENT:")
            for item in evidence.review_responsiveness[:3]:
                summary_parts.append(f"- {item}")

        # Areas to explore
        if evidence.areas_to_explore:
            summary_parts.append("\nAREAS TO EXPLORE:")
            for item in evidence.areas_to_explore[:3]:
                summary_parts.append(f"- {item}")

        return "\n".join(summary_parts)

    def _sanitize_insights(self, insights: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply behavioral inference sanitization to all text fields in insights.

        This ensures PR insights don't contain non-observable behavioral inferences
        or corporate jargon that can't be proven from PR data.
        """
        import re

        # FORBIDDEN_PHRASES for corporate jargon and behavioral inferences
        FORBIDDEN_PHRASES = [
            # Corporate jargon and non-observable inferences
            r"minimal\s+bureaucracy",
            r"bureaucratic",
            r"startup\s+mentality",
            r"cultural?\s+fit",
            r"team\s+player",
            r"go[_\s-]?getter",
            r"self[_\s-]?starter",
            r"proactive\s+(approach|mindset)",
            r"takes?\s+initiative",
            r"ownership\s+mentality",
            r"entrepreneurial\s+spirit",
            r"startup\s+environment\s+fit",
            r"autonomous\s+work\s+style",
            r"independent\s+problem[_\s-]?solving\s+approach",
            r"fits?\s+startup\s+environments?",
            r"work\s+ethic",
            r"dedication",
            r"dedicated\s+(developer|contributor|programmer)",
            r"hard[_\s-]?working",
            r"committed\s+to\s+(the\s+)?project",
        ]

        def sanitize_text(text: str) -> str:
            """Sanitize a single text field."""
            if not isinstance(text, str):
                return text

            violations_found = []

            # Check each forbidden phrase
            for pattern in FORBIDDEN_PHRASES:
                if re.search(pattern, text, re.IGNORECASE):
                    violations_found.append(pattern)
                    # Find all sentences containing this pattern
                    sentences = text.split(".")
                    filtered_sentences: list[str] = []

                    for sentence in sentences:
                        if not re.search(pattern, sentence, re.IGNORECASE):
                            filtered_sentences.append(sentence)
                        else:
                            logger.critical(
                                f"AI VIOLATION DETECTED! Forbidden corporate jargon pattern '{pattern}' "
                                f"found in PR insights: {sentence.strip()[:100]}..."
                            )

                    text = ".".join(filtered_sentences)

            # Clean up any double periods or spacing issues
            text = re.sub(r"\.+", ".", text)
            text = re.sub(r"\s+", " ", text)
            text = text.strip()

            if violations_found:
                logger.critical(
                    f"PR INSIGHTS SANITIZATION ACTIVATED! "
                    f"Removed {len(violations_found)} forbidden patterns: {violations_found}"
                )

            return text

        def sanitize_recursive(obj: Any) -> Any:
            """Recursively sanitize all string values in the insights object."""
            if isinstance(obj, dict):
                return {key: sanitize_recursive(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [sanitize_recursive(item) for item in obj]
            elif isinstance(obj, str):
                return sanitize_text(obj)
            else:
                return obj

        result = sanitize_recursive(insights)
        return result if isinstance(result, dict) else insights

    def _get_fallback_insights(self) -> Dict[str, Any]:
        """
        Get fallback insights when AI generation fails.

        Returns:
            Basic insights structure
        """
        return {
            "interview_questions": [
                {
                    "question": "Tell me about your most significant PR contribution",
                    "category": "technical",
                    "evidence_reference": "Review PR evidence for specific PRs",
                    "context_note": "Understanding major contributions",
                    "hiring_implication": "Assesses technical capability and impact",
                    "follow_up_questions": [
                        "What challenges did you face?",
                        "How did you approach the solution?",
                        "What was the impact?",
                    ],
                    "key_listening_points": "Technical depth and problem-solving approach",
                }
            ],
            "key_insights": [
                {
                    "title": "Analysis Pending",
                    "category": "technical_skills",
                    "description": "Manual analysis required for comprehensive insights",
                    "evidence": "Review evidence summary for details",
                    "impact": "neutral",
                    "hiring_implication": "Requires manual assessment for hiring decision",
                }
            ],
            "key_strengths": ["Analysis pending - see evidence summary"],
            "technical_capabilities": ["Review PR evidence for details"],
            "collaboration_style": ["See collaboration patterns in evidence"],
            "code_quality_indicators": ["Review PR patterns for quality signals"],
            "areas_for_discussion": ["Discuss specific PRs mentioned in evidence"],
            "notable_contributions": ["See highlighted PRs in evidence"],
            "context_fit": {
                "alignment": "needs_discussion",
                "supporting_evidence": ["Review evidence patterns"],
                "considerations": ["Manual review recommended"],
                "specific_strengths_for_context": ["Context analysis pending"],
            },
            "recommendations": [
                "Manual analysis recommended for comprehensive assessment"
            ],
            "data_limitations": ["Limited PR data requires manual review"],
            "quality_indicators": {
                "positive_indicators": ["See evidence summary for patterns"],
                "areas_to_explore": [
                    "Manual review needed for comprehensive assessment"
                ],
            },
        }
