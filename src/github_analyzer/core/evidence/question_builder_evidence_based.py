# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Evidence-based interview question generation without arbitrary scoring.

This module generates interview questions based on actual observations from
repository analysis, without imposing arbitrary judgments or scores.
"""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import anthropic

from ...utils.config import get_config
from ...utils.logging import get_logger

# from .context_prompts import ContextPromptEnhancer

logger = get_logger(__name__)


@dataclass
class InterviewQuestion:
    """An evidence-based interview question."""

    category: str  # technical, behavioral, collaboration, quality, growth
    question: str  # The main question
    observation_basis: str  # What we observed that prompted this question
    exploration_areas: List[str]  # Areas to explore further
    context_notes: str  # Why this matters for the specific context

    # What to explore (not judge)
    exploration_guidance: List[str] = field(default_factory=list)

    # Understanding context (not scoring)
    understanding_indicators: Dict[str, str] = field(default_factory=dict)


@dataclass
class InterviewGuide:
    """Complete interview guide based on evidence."""

    questions: List[InterviewQuestion]
    key_observations: List[str]  # What we noticed
    exploration_priorities: List[str]  # What to focus on
    context_considerations: Dict[str, str]  # Context-specific notes
    data_limitations: List[str]  # What we couldn't assess
    interview_flow: List[str]  # Suggested flow


class EvidenceBasedQuestionBuilder:
    """Generate interview questions based on evidence without arbitrary scoring."""

    def __init__(self, anthropic_api_key: Optional[str] = None) -> None:
        """Initialize question builder."""
        config = get_config()
        self.anthropic_api_key = anthropic_api_key or config.anthropic_api_key
        self.anthropic_client: Optional[anthropic.Anthropic]

        if self.anthropic_api_key:
            self.anthropic_client = anthropic.Anthropic(api_key=self.anthropic_api_key)
        else:
            self.anthropic_client = None

        # Model configuration - using tier_config for model selection
        from ..tier_config import get_model_for_tier, get_output_limits

        self.model_config = {
            "free": None,  # No AI
            "basic": get_model_for_tier("basic"),  # Simplified: single model per tier
            "professional": get_model_for_tier("professional"),
            "enterprise": get_model_for_tier("enterprise"),
            "scale_plus": get_model_for_tier("scale_plus"),
        }

        # Get question limits from centralized tier_config
        self.question_limits = {}
        for tier_name in ["free", "basic", "professional", "enterprise", "scale_plus"]:
            limits = get_output_limits(tier_name)
            self.question_limits[tier_name] = limits["max_questions"]

        # What we fundamentally cannot assess
        self.interview_essentials = [
            "Problem-solving approach under pressure",
            "Communication with non-technical stakeholders",
            "Team collaboration dynamics",
            "Learning from failures",
            "Handling ambiguity and change",
            "Technical decision-making process",
            "Work-life balance preferences",
            "Career goals and motivations",
        ]

    def generate_questions(
        self, observations: Dict[str, Any], context: str = "general", tier: str = "free"
    ) -> InterviewGuide:
        """
        Generate interview questions from observations.

        Args:
            observations: All observations from analysis
            context: Hiring context
            tier: Subscription tier

        Returns:
            Interview guide with evidence-based questions
        """
        # Prepare evidence summary
        evidence_summary = self._prepare_evidence_summary(observations)

        # Generate questions based on tier
        if tier == "free" or not self.anthropic_client:
            questions = self._generate_rule_based_questions(evidence_summary, context)
        else:
            questions = self._generate_ai_questions(evidence_summary, context, tier)

        # Limit questions by tier
        max_questions = self.question_limits.get(tier, 3)
        questions = questions[:max_questions]

        # Extract key observations
        key_observations = self._extract_key_observations(evidence_summary)

        # Determine exploration priorities
        exploration_priorities = self._determine_exploration_priorities(
            evidence_summary, context
        )

        # Generate context considerations
        context_considerations = self._generate_context_considerations(context)

        # Identify data limitations
        data_limitations = self._identify_limitations(evidence_summary)

        # Suggest interview flow
        interview_flow = self._suggest_interview_flow(questions, evidence_summary)

        return InterviewGuide(
            questions=questions,
            key_observations=key_observations,
            exploration_priorities=exploration_priorities,
            context_considerations=context_considerations,
            data_limitations=data_limitations,
            interview_flow=interview_flow,
        )

    def _prepare_evidence_summary(self, observations: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare evidence summary without scoring."""
        summary: Dict[str, Any] = {
            "technical_observations": [],
            "behavioral_observations": [],
            "collaboration_observations": [],
            "quality_observations": [],
            "growth_observations": [],
            "noteworthy_patterns": [],
            "exploration_areas": [],
        }

        # Process technical patterns
        for pattern in observations.get("technical_patterns", []):
            summary["technical_observations"].append(
                {
                    "type": pattern.get("type", ""),
                    "observation": pattern.get("finding", ""),
                    "context": pattern.get("insight", ""),
                }
            )

            # Note patterns worth exploring
            if "test" in pattern.get("finding", "").lower():
                summary["exploration_areas"].append("Testing philosophy and practices")
            if "architecture" in pattern.get("finding", "").lower():
                summary["exploration_areas"].append("Architectural decision-making")

        # Process behavioral data
        behavioral = observations.get("behavioral_analysis", {})
        if behavioral.get("work_style", "unknown") != "unknown":
            summary["behavioral_observations"].append(
                {
                    "pattern": behavioral.get("work_style", "unknown"),
                    "context": "Work pattern analysis",
                    "explore": "Work preferences and productivity",
                }
            )

        # Process collaboration patterns
        for pattern in observations.get("collaboration_patterns", []):
            summary["collaboration_observations"].append(
                {
                    "finding": pattern.get("finding", ""),
                    "contributors": pattern.get("top_contributors", []),
                }
            )

        # Process skill evolution
        evolution = observations.get("skill_evolution", {})
        if evolution.get("development_trajectory", "unknown") != "unknown":
            summary["growth_observations"].append(
                {
                    "progression": evolution.get("development_trajectory", "unknown"),
                    "focus": evolution.get("recent_focus", "varied"),
                    "trend": evolution.get("activity_trend", "stable"),
                }
            )

        # Note any concerning patterns without judgment
        if behavioral.get("work_life_balance") == "concerning":
            summary["noteworthy_patterns"].append(
                "High activity levels observed - worth discussing sustainability"
            )

        return summary

    def _generate_rule_based_questions(
        self, evidence_summary: Dict[str, Any], context: str
    ) -> List[InterviewQuestion]:
        """Generate questions without AI."""
        questions = []

        # Technical observations
        for obs in evidence_summary["technical_observations"][:2]:
            if "test" in obs["observation"].lower():
                questions.append(
                    InterviewQuestion(
                        category="quality",
                        question=f"I noticed {obs['observation']}. Can you walk me through your approach to testing?",
                        observation_basis=obs["observation"],
                        exploration_areas=[
                            "Testing philosophy",
                            "Balance between coverage and pragmatism",
                            "Test maintenance strategies",
                        ],
                        context_notes=f"Understanding quality practices for {context}",
                        exploration_guidance=[
                            "Listen for pragmatic approach",
                            "Explore testing in different scenarios",
                            "Understand trade-offs they consider",
                        ],
                        understanding_indicators={
                            "depth": "Can explain testing choices with context",
                            "experience": "Shares specific examples and learnings",
                            "flexibility": "Adapts approach to project needs",
                        },
                    )
                )

        # Behavioral observations
        for obs in evidence_summary["behavioral_observations"][:1]:
            questions.append(
                InterviewQuestion(
                    category="behavioral",
                    question=f"Your commits suggest a {obs['pattern']} pattern. What does your ideal work day look like?",
                    observation_basis=f"{obs['pattern']} work pattern observed",
                    exploration_areas=[
                        "Work preferences",
                        "Productivity patterns",
                        "Collaboration style",
                    ],
                    context_notes=f"Understanding work style fit for {context}",
                    exploration_guidance=[
                        "Explore what drives their patterns",
                        "Understand flexibility and adaptability",
                        "Discuss team interaction preferences",
                    ],
                )
            )

        # Growth observations
        for obs in evidence_summary["growth_observations"][:1]:
            questions.append(
                InterviewQuestion(
                    category="growth",
                    question=f"I see {obs['progression']} progression in your work. What drives your learning choices?",
                    observation_basis=f"{obs['progression']} development trajectory",
                    exploration_areas=[
                        "Learning motivation",
                        "Skill development strategy",
                        "Future learning goals",
                    ],
                    context_notes=f"Growth potential for {context} environment",
                    exploration_guidance=[
                        "Understand learning approach",
                        "Explore adaptability to new domains",
                        "Discuss knowledge sharing",
                    ],
                )
            )

        # Always include fundamental questions
        questions.extend(self._generate_fundamental_questions(context))

        return questions

    def _generate_ai_questions(
        self, evidence_summary: Dict[str, Any], context: str, tier: str
    ) -> List[InterviewQuestion]:
        """Generate questions using AI."""
        if not self.anthropic_client:
            return self._generate_rule_based_questions(evidence_summary, context)

        prompt = self._build_ai_prompt(evidence_summary, context, tier)
        model = self.model_config.get(tier, self.model_config["basic"])

        try:
            from ...core.tier_config import TIER_CONFIGURATIONS

            # Get tier-specific token limit
            tier_config = TIER_CONFIGURATIONS.get(tier.lower() if tier else "basic")
            max_tokens = (
                tier_config.unified_approach_tokens if tier_config else 2000  # fallback
            )

            # Ensure model is not None
            if not model:
                model = self.model_config["basic"]

            message = self.anthropic_client.messages.create(
                model=str(model),
                max_tokens=max_tokens,
                temperature=0.1,
                system="Generate interview questions based on evidence. Return valid JSON only.",
                messages=[{"role": "user", "content": prompt}],
            )

            response = ""
            if message.content and len(message.content) > 0:
                content_block = message.content[0]
                if hasattr(content_block, "text"):
                    response = content_block.text
            questions_data = json.loads(response)

            # Import and apply post-processing firewall
            from .insight_engine import strip_forbidden_keys

            questions_data = strip_forbidden_keys(questions_data)

            # Convert to InterviewQuestion objects
            questions = []
            for q_data in questions_data.get("questions", []):
                questions.append(
                    InterviewQuestion(
                        category=q_data["category"],
                        question=q_data["question"],
                        observation_basis=q_data["observation_basis"],
                        exploration_areas=q_data["exploration_areas"],
                        context_notes=q_data["context_notes"],
                        exploration_guidance=q_data.get("exploration_guidance", []),
                        understanding_indicators=q_data.get(
                            "understanding_indicators", {}
                        ),
                    )
                )

            return questions

        except Exception as e:
            logger.error(f"AI question generation failed: {e}")
            return self._generate_rule_based_questions(evidence_summary, context)

    def _build_ai_prompt(
        self, evidence_summary: Dict[str, Any], context: str, tier: str
    ) -> str:
        """Build prompt for AI question generation."""
        return f"""
Generate interview questions based on repository observations for {context} hiring.

EVIDENCE SUMMARY:
{json.dumps(evidence_summary, indent=2)}

Generate up to {self.question_limits[tier]} interview questions based on available evidence that:
1. Explore specific observations without judgment
2. Seek to understand context and reasoning
3. Are relevant to {context} environment
4. Focus on learning about the candidate

For each question provide:
{{
    "category": "technical|behavioral|collaboration|quality|growth",
    "question": "Question based on specific observation",
    "observation_basis": "The observation that prompted this question",
    "exploration_areas": ["Area 1 to explore", "Area 2 to explore"],
    "context_notes": "Why this matters for {context}",
    "exploration_guidance": ["What to explore", "How to dig deeper"],
    "understanding_indicators": {{
        "depth": "What indicates deep understanding",
        "experience": "What shows relevant experience",
        "adaptability": "What demonstrates flexibility"
    }}
}}

Return JSON with key "questions" containing array of questions.
"""

    def _generate_fundamental_questions(self, context: str) -> List[InterviewQuestion]:
        """Generate fundamental questions we always need to ask."""
        return [
            InterviewQuestion(
                category="technical",
                question="Walk me through a recent technical challenge you solved.",
                observation_basis="Need to assess problem-solving beyond code",
                exploration_areas=[
                    "Problem-solving methodology",
                    "Technical decision-making",
                    "Learning from challenges",
                ],
                context_notes=f"Core capability for {context}",
                exploration_guidance=[
                    "Explore their thought process",
                    "Understand constraints they faced",
                    "Discuss alternative approaches",
                ],
            ),
            InterviewQuestion(
                category="collaboration",
                question="Describe a time you had to work with difficult stakeholders.",
                observation_basis="Cannot assess soft skills from code",
                exploration_areas=[
                    "Communication strategies",
                    "Conflict resolution",
                    "Stakeholder management",
                ],
                context_notes=f"Critical for success in {context}",
                exploration_guidance=[
                    "Listen for empathy and understanding",
                    "Explore their communication approach",
                    "Understand how they build consensus",
                ],
            ),
        ]

    def _extract_key_observations(self, evidence_summary: Dict[str, Any]) -> List[str]:
        """Extract key observations from evidence."""
        observations = []

        # Technical observations
        for obs in evidence_summary["technical_observations"][:2]:
            if obs["observation"]:
                # Ensure it's framed as an observation
                observation = obs["observation"]
                if not any(
                    word in observation.lower()
                    for word in ["observed", "present", "found", "shows"]
                ):
                    observation = f"Observed: {observation}"
                observations.append(observation)

        # Behavioral patterns
        for obs in evidence_summary["behavioral_observations"][:1]:
            observations.append(f"{obs['pattern']} work pattern observed")

        # Growth indicators
        for obs in evidence_summary["growth_observations"][:1]:
            observations.append(f"{obs['progression']} development trajectory observed")

        # Noteworthy patterns
        observations.extend(evidence_summary["noteworthy_patterns"][:2])

        return observations[:5]  # Limit to top 5

    def _determine_exploration_priorities(
        self, evidence_summary: Dict[str, Any], context: str
    ) -> List[str]:
        """Determine what to prioritize exploring."""
        priorities = []

        # Always explore fundamentals
        priorities.extend(
            [
                "Problem-solving approach and methodology",
                "Team collaboration and communication style",
                "Technical decision-making process",
            ]
        )

        # Add from exploration areas
        priorities.extend(evidence_summary["exploration_areas"][:3])

        # Context-specific priorities
        if context == "startup":
            priorities.extend(
                [
                    "Adaptability to changing requirements",
                    "Comfort with ambiguity",
                    "Self-direction capabilities",
                ]
            )
        elif context == "enterprise":
            priorities.extend(
                [
                    "Process adherence and documentation",
                    "Cross-team collaboration",
                    "Scalability considerations",
                ]
            )
        elif context == "agency":
            priorities.extend(
                [
                    "Client communication skills",
                    "Project versatility",
                    "Deadline management",
                ]
            )

        # Remove duplicates while preserving order
        seen = set()
        unique_priorities = []
        for p in priorities:
            if p not in seen:
                seen.add(p)
                unique_priorities.append(p)

        return unique_priorities[:8]

    def _generate_context_considerations(self, context: str) -> Dict[str, str]:
        """Generate context-specific considerations."""
        considerations = {
            "startup": {
                "environment": "Fast-paced, resource-constrained, high autonomy",
                "key_traits": "Adaptability, self-direction, pragmatism",
                "challenges": "Ambiguity, changing priorities, wearing many hats",
                "opportunities": "High impact, varied work, rapid growth",
            },
            "enterprise": {
                "environment": "Structured, process-driven, collaborative",
                "key_traits": "Process adherence, documentation, teamwork",
                "challenges": "Bureaucracy, slow change, compliance requirements",
                "opportunities": "Resources, mentorship, specialized roles",
            },
            "agency": {
                "environment": "Client-focused, project-based, varied domains",
                "key_traits": "Communication, versatility, deadline awareness",
                "challenges": "Context switching, client management, tight deadlines",
                "opportunities": "Variety, client exposure, rapid skill development",
            },
            "open_source": {
                "environment": "Community-driven, transparent, asynchronous",
                "key_traits": "Clear communication, patience, collaboration",
                "challenges": "Volunteer coordination, diverse skill levels, sustainability",
                "opportunities": "Global impact, reputation building, learning",
            },
        }

        return considerations.get(
            context,
            {
                "environment": "Professional development environment",
                "key_traits": "Technical skills, teamwork, communication",
                "challenges": "Various technical and interpersonal challenges",
                "opportunities": "Growth and contribution opportunities",
            },
        )

    def _identify_limitations(self, evidence_summary: Dict[str, Any]) -> List[str]:
        """Identify what we cannot assess from the data."""
        limitations = []

        # Always present limitations
        limitations.extend(
            [
                "Actual job performance and consistency",
                "Soft skills and interpersonal dynamics",
                "Problem-solving under time pressure",
                "Domain-specific knowledge depth",
            ]
        )

        # Add based on what's missing
        if not evidence_summary["collaboration_observations"]:
            limitations.append("Team collaboration style (single contributor)")

        if len(evidence_summary["behavioral_observations"]) == 0:
            limitations.append("Work patterns (insufficient commit history)")

        return limitations

    def _suggest_interview_flow(
        self, questions: List[InterviewQuestion], evidence_summary: Dict[str, Any]
    ) -> List[str]:
        """Suggest interview flow based on questions and evidence."""
        flow = []

        # Start with rapport
        flow.append("1. Begin with introductions and role overview")

        # Address any noteworthy patterns early
        if evidence_summary["noteworthy_patterns"]:
            flow.append("2. Address observations constructively early in conversation")
        else:
            flow.append("2. Start with general technical discussion")

        # Category-based flow
        categories = list(set(q.category for q in questions))

        if "technical" in categories:
            flow.append("3. Explore technical decisions and problem-solving")

        if "behavioral" in categories:
            flow.append("4. Discuss work patterns and preferences")

        if "collaboration" in categories:
            flow.append("5. Understand team collaboration approach")

        if "quality" in categories:
            flow.append("6. Explore quality and maintenance philosophy")

        if "growth" in categories:
            flow.append("7. Discuss learning and career growth")

        # Always end with candidate questions
        flow.append(f"{len(flow) + 1}. Allow time for candidate questions")

        return flow
