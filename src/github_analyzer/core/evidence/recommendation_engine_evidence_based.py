# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Evidence-based recommendation engine without arbitrary metrics.

This module generates analysis recommendations based purely on observed evidence,
without imposing arbitrary thresholds or scores.
"""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import anthropic

from ...utils.config import get_config
from ...utils.logging import get_logger
from ..tier_config import get_tier_config

logger = get_logger(__name__)


@dataclass
class EvidenceBasedRecommendation:
    """A recommendation based on observed evidence."""

    category: str  # technical, behavioral, cultural, growth, risk
    recommendation_type: str  # strength, opportunity, consideration, inquiry
    title: str
    observation: str  # What we actually observed
    evidence: List[str]  # Specific evidence points
    implications: str  # What this might mean for assessment
    exploration_areas: List[str]  # What to explore in interviews
    context_relevance: Dict[str, str] = field(default_factory=dict)
    data_confidence: str = "observed"  # observed, inferred, limited


@dataclass
class AnalysisAssessment:
    """Overall assessment based on evidence."""

    summary: str  # Overall narrative summary
    key_observations: List[str]  # Most important findings
    recommendations: List[EvidenceBasedRecommendation]
    areas_for_validation: List[str]  # What interviews should validate
    data_limitations: List[str]  # What we couldn't assess
    context_fit_observations: Dict[str, List[str]]  # Context-specific observations

    # Instead of scores, provide narrative assessment
    technical_readiness: str  # Narrative assessment
    collaboration_indicators: str  # What we observed about collaboration
    growth_trajectory: str  # What patterns suggest about growth

    # Risk areas without severity scores
    discussion_topics: List[Dict[str, str]]  # Topics that need discussion


class EvidenceBasedRecommendationEngine:
    """Generate evidence-based analysis recommendations without arbitrary metrics."""

    def __init__(self, anthropic_api_key: Optional[str] = None) -> None:
        """Initialize recommendation engine."""
        config = get_config()
        self.config = config
        self.anthropic_api_key = anthropic_api_key or config.anthropic_api_key
        self.anthropic_client: Optional[anthropic.Anthropic]

        if self.anthropic_api_key:
            self.anthropic_client = anthropic.Anthropic(api_key=self.anthropic_api_key)
        else:
            self.anthropic_client = None

        # Model configuration now comes from tier_config
        from ..tier_config import get_output_limits

        self.model_config = {}
        self.recommendation_limits = {}

        # Build configuration from tier_config
        for tier_name in ["free", "basic", "professional", "enterprise", "scale_plus"]:
            tier_cfg = get_tier_config(tier_name)
            if tier_cfg:
                # Use metrics model for recommendations
                self.model_config[tier_name] = (
                    tier_cfg.metrics_model or tier_cfg.main_model
                )

            # Get recommendation limits from centralized tier_config
            limits = get_output_limits(tier_name)
            self.recommendation_limits[tier_name] = limits["max_recommendations"]

        # Context-specific observation priorities
        self.context_priorities = {
            "startup": [
                "Self-direction indicators",
                "Adaptability patterns",
                "Rapid iteration evidence",
                "Pragmatic decision-making",
            ],
            "enterprise": [
                "Process adherence patterns",
                "Documentation practices",
                "Collaboration evidence",
                "Scalability considerations",
            ],
            "agency": [
                "Project variety",
                "Communication clarity",
                "Deadline awareness",
                "Quality consistency",
            ],
            "open_source": [
                "Community engagement",
                "Maintainability focus",
                "Clear communication",
                "Long-term thinking",
            ],
        }

    def generate_recommendations(
        self,
        evidence: Dict[str, Any],
        context: str = "general",
        tier: str = "professional",
        repository_type: Optional[str] = None,
        confidence_score: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Generate evidence-based recommendations and action items.

        Args:
            evidence: All extracted evidence from repository analysis
            context: Hiring context (startup, enterprise, agency, etc.)
            tier: Subscription tier
            repository_type: Type of repository analyzed
            confidence_score: Overall confidence in analysis (for compatibility)

        Returns:
            Dictionary with evidence-based recommendations and insights
        """
        try:
            # Prepare evidence observations
            observations = self._extract_observations(evidence)

            # Generate recommendations based on tier
            if tier != "free" and self.anthropic_client:
                recommendations = self._generate_ai_recommendations(
                    observations, context, tier, repository_type
                )
            else:
                recommendations = self._generate_rule_based_recommendations(
                    observations, context, repository_type
                )

            # Limit recommendations by tier
            max_recommendations = self.recommendation_limits.get(tier, 5)
            recommendations = recommendations[:max_recommendations]

            # Extract key observations
            key_observations = self._identify_key_observations(observations)

            # Generate narrative assessments
            technical_readiness = self._assess_technical_readiness(observations)
            collaboration_indicators = self._assess_collaboration(observations)
            growth_trajectory = self._assess_growth_trajectory(observations)

            # Identify areas for validation
            areas_for_validation = self._identify_validation_areas(
                observations, context
            )

            # Identify discussion topics
            discussion_topics = self._identify_discussion_topics(observations)

            # Generate context-specific observations
            context_fit_observations = self._generate_context_observations(
                observations, context
            )

            # Create overall summary
            summary = self._generate_summary(
                observations, recommendations, context, repository_type
            )

            assessment = AnalysisAssessment(
                summary=summary,
                key_observations=key_observations,
                recommendations=recommendations,
                areas_for_validation=areas_for_validation,
                data_limitations=self._identify_limitations(),
                context_fit_observations=context_fit_observations,
                technical_readiness=technical_readiness,
                collaboration_indicators=collaboration_indicators,
                growth_trajectory=growth_trajectory,
                discussion_topics=discussion_topics,
            )

            # Convert to dictionary format for backward compatibility
            return self._format_as_dictionary(assessment, context, tier)

        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return self._fallback_assessment(context, tier)

    def _extract_observations(self, evidence: Dict[str, Any]) -> Dict[str, List[str]]:
        """Extract factual observations from evidence."""
        observations: Dict[str, List[str]] = {
            "technical_patterns": [],
            "behavioral_patterns": [],
            "collaboration_patterns": [],
            "quality_indicators": [],
            "growth_indicators": [],
            "concerning_patterns": [],
        }

        # Technical patterns
        for pattern in evidence.get("technical_patterns", []):
            finding = pattern.get("finding", "")
            if finding:
                observations["technical_patterns"].append(finding)

                # Note quality-related patterns
                if "test" in finding.lower():
                    observations["quality_indicators"].append(f"Testing: {finding}")
                if "documentation" in finding.lower():
                    observations["quality_indicators"].append(
                        f"Documentation: {finding}"
                    )

        # Behavioral patterns
        behavioral = evidence.get("behavioral_patterns", {})
        if behavioral.get("commit_frequency", {}).get("pattern"):
            observations["behavioral_patterns"].append(
                f"Commit pattern: {behavioral['commit_frequency']['pattern']}"
            )
        if behavioral.get("work_timing", {}).get("pattern"):
            observations["behavioral_patterns"].append(
                f"Work timing: {behavioral['work_timing']['pattern']}"
            )

        # Additional behavioral insights if available
        behavioral_insights = evidence.get("behavioral_insights", [])
        for insight in behavioral_insights:
            if insight.get("type") == "work_life_concern":
                observations["concerning_patterns"].append(insight.get("finding", ""))
            else:
                observations["behavioral_patterns"].append(insight.get("finding", ""))

        # Collaboration patterns
        for pattern in evidence.get("collaboration_patterns", []):
            if pattern.get("type") == "collaboration":
                contributors = pattern.get("top_contributors", [])
                if contributors:
                    observations["collaboration_patterns"].append(
                        f"Collaborates with {len(contributors)} regular contributors"
                    )

        # Growth indicators
        skill_evolution = evidence.get("skill_evolution", {})
        if skill_evolution.get("development_trajectory", "unknown") != "unknown":
            observations["growth_indicators"].append(
                f"Development trajectory: {skill_evolution.get('development_trajectory', 'unknown')}"
            )
        if skill_evolution.get("recent_focus"):
            observations["growth_indicators"].append(
                f"Recent focus: {skill_evolution.get('recent_focus')}"
            )

        # Security observations
        security_issues = evidence.get("security_issues", [])
        if not security_issues:
            observations["quality_indicators"].append(
                "No obvious security vulnerabilities detected"
            )
        else:
            for issue in security_issues:
                observations["concerning_patterns"].append(
                    f"Security: {issue['finding']}"
                )

        return observations

    def _generate_rule_based_recommendations(
        self,
        observations: Dict[str, List[str]],
        context: str,
        repository_type: Optional[str],
    ) -> List[EvidenceBasedRecommendation]:
        """Generate recommendations without AI."""
        recommendations = []

        # Technical recommendations
        for obs in observations["technical_patterns"][:2]:
            if "language" in obs.lower() or "expertise" in obs.lower():
                recommendations.append(
                    EvidenceBasedRecommendation(
                        category="technical",
                        recommendation_type="strength",
                        title="Technical Expertise Observed",
                        observation=obs,
                        evidence=[obs],
                        implications="Suggests hands-on experience; explore depth with relevant technologies",
                        exploration_areas=[
                            "Explore depth of expertise in observed technologies",
                            "Discuss experience with similar tech stacks",
                            "Understand problem-solving approach",
                        ],
                        context_relevance={
                            "startup": "Can contribute immediately to technical development",
                            "enterprise": "Has foundation for enterprise-scale development",
                            "agency": "Brings valuable skills for client projects",
                            "open_source": "Can contribute to community projects",
                        },
                    )
                )

        # Quality recommendations
        test_observations = [
            o for o in observations["quality_indicators"] if "test" in o.lower()
        ]
        if test_observations:
            test_obs = test_observations[0]
            if "no test" in test_obs.lower() or "minimal" in test_obs.lower():
                recommendations.append(
                    EvidenceBasedRecommendation(
                        category="quality",
                        recommendation_type="inquiry",
                        title="Testing Practices to Explore",
                        observation=test_obs,
                        evidence=[test_obs],
                        implications="Testing approach might differ from what's visible; discuss testing philosophy",
                        exploration_areas=[
                            "Discuss testing philosophy and practices",
                            "Explore quality assurance approach",
                            "Understand experience with different testing strategies",
                        ],
                        context_relevance={
                            "startup": "Important to understand approach to quality vs speed",
                            "enterprise": "Critical for production reliability",
                            "agency": "Affects project maintenance and handoffs",
                            "open_source": "Important for community trust",
                        },
                    )
                )
            else:
                recommendations.append(
                    EvidenceBasedRecommendation(
                        category="quality",
                        recommendation_type="strength",
                        title="Quality-Focused Development",
                        observation=test_obs,
                        evidence=[test_obs],
                        implications="May indicate commitment to code quality; explore testing strategy",
                        exploration_areas=[
                            "Explore testing strategy and coverage goals",
                            "Discuss balance between testing and development speed",
                            "Understand experience with test-driven development",
                        ],
                        context_relevance={
                            "startup": "Quality practices for rapid iteration",
                            "enterprise": "Essential for maintainability",
                            "agency": "Important for client deliverables",
                            "open_source": "Builds contributor confidence",
                        },
                    )
                )

        # Behavioral recommendations
        for obs in observations["behavioral_patterns"][:1]:
            recommendations.append(
                EvidenceBasedRecommendation(
                    category="behavioral",
                    recommendation_type="opportunity",
                    title="Work Pattern Observations",
                    observation=obs,
                    evidence=[obs],
                    implications="May provide insight into work style; discuss preferred working environment",
                    exploration_areas=[
                        "Discuss preferred working environment",
                        "Explore collaboration style",
                        "Understand work-life balance priorities",
                    ],
                    context_relevance={
                        "startup": "Important to align with startup pace",
                        "enterprise": "Should match team working hours",
                        "agency": "Flexibility for client needs",
                        "open_source": "Understand contribution patterns",
                    },
                )
            )

        # Concerning patterns
        for obs in observations["concerning_patterns"][:1]:
            recommendations.append(
                EvidenceBasedRecommendation(
                    category="risk",
                    recommendation_type="consideration",
                    title="Area for Discussion",
                    observation=obs,
                    evidence=[obs],
                    implications="Could benefit from exploring context; discuss long-term sustainability",
                    exploration_areas=[
                        "Explore context behind the pattern",
                        "Discuss long-term sustainability",
                        "Understand strategies for balance",
                    ],
                    context_relevance={
                        "startup": "Important for sustainable performance",
                        "enterprise": "Work-life balance expectations",
                        "agency": "Project deadline management",
                        "open_source": "Contributor sustainability",
                    },
                )
            )

        # Always add at least one area to explore
        if not any(
            r.recommendation_type in ["consideration", "inquiry"]
            for r in recommendations
        ):
            recommendations.append(
                EvidenceBasedRecommendation(
                    category="behavioral",
                    recommendation_type="inquiry",
                    title="Team Collaboration Approach",
                    observation="Repository collaboration patterns need validation",
                    evidence=["Limited multi-contributor data available"],
                    implications="Team dynamics and collaboration style should be explored in interview",
                    exploration_areas=[
                        "Discuss experience working in teams",
                        "Explore communication preferences",
                        "Understand collaboration tools and processes used",
                    ],
                    context_relevance={
                        "startup": "Critical for fast-paced collaborative environment",
                        "enterprise": "Important for cross-team coordination",
                        "agency": "Essential for client project collaboration",
                        "open_source": "Key for community engagement",
                    },
                )
            )

        return recommendations

    def _generate_ai_recommendations(
        self,
        observations: Dict[str, List[str]],
        context: str,
        tier: str,
        repository_type: Optional[str],
    ) -> List[EvidenceBasedRecommendation]:
        """Generate AI-powered recommendations."""
        if not self.anthropic_client:
            return self._generate_rule_based_recommendations(
                observations, context, repository_type
            )

        prompt = self._build_ai_prompt(observations, context, tier, repository_type)
        model = self.model_config.get(tier, self.model_config["basic"])

        try:
            from ...core.tier_config import TIER_CONFIGURATIONS

            # Get tier-specific token limit
            tier_config = TIER_CONFIGURATIONS.get(tier.lower() if tier else "basic")
            max_tokens = (
                tier_config.unified_approach_tokens if tier_config else 2000  # fallback
            )

            message = self.anthropic_client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=0.1,
                system="Generate evidence-based recommendations and insights. Return valid JSON only.",
                messages=[{"role": "user", "content": prompt}],
            )

            response = ""
            if message.content and len(message.content) > 0:
                content_block = message.content[0]
                if hasattr(content_block, "text"):
                    response = content_block.text

            # Parse response - handle potential markdown wrapping
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()

            recommendations_data = json.loads(response)

            # Import and apply post-processing firewall
            from .insight_engine import strip_forbidden_keys

            recommendations_data = strip_forbidden_keys(recommendations_data)

            # Convert new format to recommendation objects
            recommendations = []

            # Process key observations as recommendations
            for obs in recommendations_data.get("key_observations", []):
                recommendations.append(
                    EvidenceBasedRecommendation(
                        category="technical",
                        recommendation_type=(
                            "strength"
                            if "strength" in obs.get("observation", "").lower()
                            else "consideration"
                        ),
                        title=obs.get("observation", "")[:50],
                        observation=obs.get("observation", ""),
                        evidence=obs.get("evidence", []),
                        implications=obs.get("implications", ""),
                        exploration_areas=(
                            obs.get("verification_needed", "").split(", ")
                            if obs.get("verification_needed")
                            else []
                        ),
                        context_relevance={context: "Relevant for this context"},
                        data_confidence="observed",
                    )
                )

            # Process areas of strength
            for area in recommendations_data.get("areas_of_strength", []):
                recommendations.append(
                    EvidenceBasedRecommendation(
                        category="technical",
                        recommendation_type="strength",
                        title=area.get("area", ""),
                        observation=area.get("area", ""),
                        evidence=area.get("evidence", []),
                        implications=area.get("note", ""),
                        exploration_areas=["Validate in technical interview"],
                        context_relevance={context: "Positive indicator"},
                        data_confidence="observed",
                    )
                )

            # Process areas to explore
            for area in recommendations_data.get("areas_to_explore", []):
                recommendations.append(
                    EvidenceBasedRecommendation(
                        category="behavioral",
                        recommendation_type="inquiry",
                        title=area.get("area", ""),
                        observation=area.get("why", ""),
                        evidence=[],
                        implications="Needs further exploration",
                        exploration_areas=[
                            area.get("suggested_approach", "Discuss in interview")
                        ],
                        context_relevance={context: "Important to validate"},
                        data_confidence="limited",
                    )
                )

            return recommendations[: self.recommendation_limits.get(tier, 5)]

        except Exception as e:
            logger.error(f"AI recommendation generation failed: {e}")
            return self._generate_rule_based_recommendations(
                observations, context, repository_type
            )

    def _build_ai_prompt(
        self,
        observations: Dict[str, List[str]],
        context: str,
        tier: str,
        repository_type: Optional[str],
    ) -> str:
        """Build prompt for AI recommendations."""
        from ...ai.evidence_based_prompts import EVIDENCE_BASED_RECOMMENDATION_PROMPT

        # Use the evidence-based recommendation prompt
        return EVIDENCE_BASED_RECOMMENDATION_PROMPT.format(
            evidence=json.dumps(observations, indent=2), context=context
        )

    def _identify_key_observations(
        self, observations: Dict[str, List[str]]
    ) -> List[str]:
        """Extract the most important observations."""
        key_obs = []

        # Add most significant technical observations
        for obs in observations["technical_patterns"][:2]:
            key_obs.append(obs)

        # Add collaboration if present
        for obs in observations["collaboration_patterns"][:1]:
            key_obs.append(obs)

        # Add growth indicators
        for obs in observations["growth_indicators"][:1]:
            key_obs.append(obs)

        # Add any major concerns
        for obs in observations["concerning_patterns"][:1]:
            key_obs.append(obs)

        return key_obs[:5]

    def _assess_technical_readiness(self, observations: Dict[str, List[str]]) -> str:
        """Generate narrative technical assessment."""
        tech_obs = observations["technical_patterns"]
        quality_obs = observations["quality_indicators"]

        if not tech_obs:
            return "Limited technical patterns observed in repository. Technical interview essential for assessment."

        assessment_parts = []

        # Technical diversity
        if len(tech_obs) > 3:
            assessment_parts.append(
                "Repository shows experience across multiple technologies"
            )
        elif len(tech_obs) > 0:
            assessment_parts.append("Repository demonstrates focused technical work")

        # Quality practices
        test_obs = [o for o in quality_obs if "test" in o.lower()]
        if test_obs:
            if "comprehensive" in str(test_obs).lower():
                assessment_parts.append("with strong testing practices")
            elif "minimal" in str(test_obs).lower():
                assessment_parts.append("though testing practices are not evident")
            else:
                assessment_parts.append("with some testing present")

        # Documentation
        doc_obs = [o for o in quality_obs if "documentation" in o.lower()]
        if doc_obs:
            assessment_parts.append("and attention to documentation")

        if assessment_parts:
            return (
                ". ".join(assessment_parts)
                + ". Technical interview should explore depth and problem-solving approach."
            )
        else:
            return "Technical patterns suggest competence. Detailed technical assessment needed to gauge expertise level."

    def _assess_collaboration(self, observations: Dict[str, List[str]]) -> str:
        """Generate narrative collaboration assessment."""
        collab_obs = observations["collaboration_patterns"]

        if not collab_obs:
            return "Repository appears to be primarily individual work. Team collaboration experience should be explored in interview."

        assessment_parts = []
        for obs in collab_obs:
            if "contributors" in obs:
                assessment_parts.append(obs)

        if assessment_parts:
            return (
                ". ".join(assessment_parts)
                + ". Interview should explore collaboration style and team dynamics."
            )
        else:
            return "Some collaboration indicators present. Team interaction preferences and communication style need validation."

    def _assess_growth_trajectory(self, observations: Dict[str, List[str]]) -> str:
        """Generate narrative growth assessment."""
        growth_obs = observations["growth_indicators"]

        if not growth_obs:
            return "Growth trajectory not evident from repository data. Learning approach and career goals should be discussed."

        assessment_parts = []
        for obs in growth_obs:
            assessment_parts.append(obs)

        if assessment_parts:
            return (
                ". ".join(assessment_parts)
                + ". Suggests ongoing professional development."
            )
        else:
            return "Limited growth indicators in repository. Explore learning mindset and adaptability in interview."

    def _identify_validation_areas(
        self, observations: Dict[str, List[str]], context: str
    ) -> List[str]:
        """Identify what needs validation in interviews."""
        areas = [
            "Problem-solving approach on unfamiliar challenges",
            "Communication style with stakeholders",
            "Team collaboration and conflict resolution",
        ]

        # Context-specific areas
        if context == "startup":
            areas.extend(
                [
                    "Comfort with ambiguity and changing priorities",
                    "Ability to wear multiple hats",
                    "Speed vs quality trade-offs",
                ]
            )
        elif context == "enterprise":
            areas.extend(
                [
                    "Experience with formal processes",
                    "Documentation and knowledge transfer",
                    "Working in large teams",
                ]
            )
        elif context == "agency":
            areas.extend(
                [
                    "Client communication skills",
                    "Managing multiple projects",
                    "Deadline negotiation",
                ]
            )

        # Add based on observations
        if not observations["quality_indicators"]:
            areas.append("Quality assurance practices and philosophy")

        if not observations["collaboration_patterns"]:
            areas.append("Team collaboration experience and preferences")

        return areas[:7]

    def _identify_discussion_topics(
        self, observations: Dict[str, List[str]]
    ) -> List[Dict[str, str]]:
        """Identify topics that need discussion."""
        topics = []

        # Any concerning patterns
        for obs in observations["concerning_patterns"]:
            topics.append(
                {
                    "topic": "Work sustainability",
                    "observation": obs,
                    "explore": "Context and long-term approach",
                }
            )

        # Missing quality indicators
        if not any("test" in o.lower() for o in observations["quality_indicators"]):
            topics.append(
                {
                    "topic": "Testing philosophy",
                    "observation": "Testing practices not evident",
                    "explore": "Quality assurance approach",
                }
            )

        # Limited collaboration
        if not observations["collaboration_patterns"]:
            topics.append(
                {
                    "topic": "Team collaboration",
                    "observation": "Limited multi-contributor activity",
                    "explore": "Team work experience and style",
                }
            )

        return topics

    def _generate_context_observations(
        self, observations: Dict[str, List[str]], context: str
    ) -> Dict[str, List[str]]:
        """Generate context-specific observations."""
        context_obs: Dict[str, List[str]] = {
            "alignments": [],
            "considerations": [],
            "validations_needed": [],
        }

        priorities = self.context_priorities.get(context, [])

        # Check for context alignments
        for priority in priorities:
            if (
                "self-direction" in priority.lower()
                and observations["behavioral_patterns"]
            ):
                for obs in observations["behavioral_patterns"]:
                    if "self" in obs.lower() or "independent" in obs.lower():
                        context_obs["alignments"].append(
                            f"{obs} - aligns with {context} need for self-direction"
                        )

            if (
                "documentation" in priority.lower()
                and observations["quality_indicators"]
            ):
                for obs in observations["quality_indicators"]:
                    if "documentation" in obs.lower():
                        context_obs["alignments"].append(
                            f"{obs} - important for {context} environment"
                        )

        # Add validation needs
        context_obs["validations_needed"] = [
            f"Validate {priority}" for priority in priorities[:3]
        ]

        # Ensure we always have some observations
        if not context_obs["alignments"]:
            context_obs["considerations"].append(
                f"Limited observable patterns for {context} context - thorough interview needed"
            )

        return context_obs

    def _generate_summary(
        self,
        observations: Dict[str, List[str]],
        recommendations: List[EvidenceBasedRecommendation],
        context: str,
        repository_type: Optional[str],
    ) -> str:
        """Generate overall summary."""
        total_patterns = sum(len(obs) for obs in observations.values())
        strength_count = sum(
            1 for r in recommendations if r.recommendation_type == "strength"
        )

        repo_context = f" {repository_type}" if repository_type else ""

        # Handle minimal data cases
        if total_patterns < 3:
            return (
                f"Minimal data available in repository{repo_context}. "
                "Limited patterns observed require comprehensive interview validation. "
                "Repository analysis alone insufficient for assessment."
            )

        parts = [
            f"Repository analysis of{repo_context} code reveals {total_patterns} observable patterns."
        ]

        if strength_count > len(recommendations) / 2:
            parts.append(
                f"Multiple positive indicators observed relevant to {context} environment."
            )
        elif strength_count > 0:
            parts.append(
                f"Analysis shows mixed indicators with some strengths relevant to {context} context."
            )
        else:
            parts.append(
                "Limited positive indicators observed, requiring thorough interview validation."
            )

        parts.append(
            "While repository analysis provides useful screening data, "
            "comprehensive technical and behavioral interviews remain essential "
            "for complete assessment."
        )

        return " ".join(parts)

    def _identify_limitations(self) -> List[str]:
        """Identify what we cannot assess."""
        return [
            "Actual job performance under pressure",
            "Soft skills and interpersonal dynamics",
            "Domain knowledge depth",
            "Learning from failure",
            "Mentoring and leadership abilities",
            "Customer/stakeholder interaction",
            "Debugging skills on unfamiliar code",
            "Adaptation to new technologies",
        ]

    def _format_as_dictionary(
        self, assessment: AnalysisAssessment, context: str, tier: str
    ) -> Dict[str, Any]:
        """Convert AnalysisAssessment to dictionary format for backward compatibility."""
        # Convert recommendations to dictionary format
        all_recommendations = []
        for rec in assessment.recommendations:
            rec_dict = {
                "type": rec.recommendation_type,
                "category": rec.category,
                "recommendation": rec.title,
                "evidence": ", ".join(rec.evidence),
                "action": rec.implications,
                "priority": (
                    "high" if rec.recommendation_type == "strength" else "medium"
                ),
                "context_relevance": rec.context_relevance.get(context, ""),
            }
            all_recommendations.append(rec_dict)

        # Extract key strengths
        key_strengths = [
            {
                "category": rec.category,
                "recommendation": rec.title,
                "evidence": rec.evidence,
                "priority": "high",
            }
            for rec in assessment.recommendations
            if rec.recommendation_type == "strength"
        ]

        # Extract areas to probe
        areas_to_probe = [
            {
                "category": rec.category,
                "recommendation": rec.title,
                "evidence": rec.evidence,
                "priority": "medium",
            }
            for rec in assessment.recommendations
            if rec.recommendation_type in ["consideration", "inquiry"]
        ]

        # Calculate counts for summary
        strength_count = len(key_strengths)
        concern_count = len(areas_to_probe)

        # NO SCORES OR THRESHOLDS - Just evidence summary
        evidence_summary = f"Analysis identified {strength_count} observable strengths and {concern_count} areas requiring further exploration"

        return {
            "evidence_summary": evidence_summary,
            # Note: hiring_recommendation field removed as per evidence-based methodology
            "context": context,
            "tier": tier,
            "total_recommendations": len(all_recommendations),
            "recommendations_by_type": {
                "strengths": key_strengths,
                "concerns": areas_to_probe,
                "neutral": [],
            },
            "all_recommendations": all_recommendations,
            "key_strengths": key_strengths,
            "areas_to_probe": areas_to_probe,
            "decision_factors": assessment.areas_for_validation[:5],
            "growth_potential": {
                "assessment": assessment.growth_trajectory
                # NO SCORES! Evidence-based analysis only
            },
            "cultural_fit": {
                "assessment": assessment.summary,
                "alignment_factors": assessment.context_fit_observations.get(
                    "alignments", []
                ),
            },
            "summary": assessment.summary,
            "data_limitations": assessment.data_limitations,
        }

    def _fallback_assessment(self, context: str, tier: str) -> Dict[str, Any]:
        """Generate fallback assessment if processing fails."""
        return {
            "context": context,
            "tier": tier,
            "total_recommendations": 0,
            "all_recommendations": [],
            "error": "Unable to generate recommendations, manual review required",
            "suggestions": [
                "Review repository manually",
                "Conduct thorough technical interview",
                "Request code samples or portfolio",
            ],
        }
