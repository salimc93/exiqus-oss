# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Evidence-based insight engine.

This module generates screening insights from evidence extracted during repository
analysis. It replaces the old hardcoded scoring system with nuanced,
evidence-driven analysis that acknowledges the limitations of GitHub-only data.
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import anthropic

from ...utils.config import get_config
from ...utils.logging import get_logger
from ..tier_config import get_tier_config

logger = get_logger(__name__)

# Post-processing firewall constants
FORBIDDEN_KEYS = {
    "score",
    "rating",
    "percentile",
    "grade",
    "rank",
    "hiring_recommendation",
    "recommendation_confidence",
    "ratio",
    "growth_potential",
}


def strip_forbidden_keys(data: Any) -> Any:
    """
    Recursively strip forbidden keys from AI output.

    This is our post-processing firewall that ensures no scores
    or ratings ever make it through, regardless of what the AI generates.
    """
    if isinstance(data, dict):
        cleaned = {}
        for key, value in data.items():
            # Check if key is forbidden
            if key in FORBIDDEN_KEYS:
                logger.critical(
                    f"AI VIOLATION DETECTED! Rogue key '{key}' found in output. Stripping it."
                )
                continue
            # Also check for keys containing forbidden words
            if any(forbidden in key.lower() for forbidden in FORBIDDEN_KEYS):
                logger.critical(
                    f"AI VIOLATION DETECTED! Key '{key}' contains forbidden word. Stripping it."
                )
                continue

            # CRITICAL NEW CHECK: Strip entire nested objects that contain scores
            # This catches things like growth_potential: {assessment: "...", score: 0.7}
            if isinstance(value, dict) and "score" in value:
                logger.critical(
                    f"AI VIOLATION DETECTED! Nested score found in '{key}' object. Stripping score field."
                )
                # Remove just the score field, keep the rest
                value = {k: v for k, v in value.items() if k not in FORBIDDEN_KEYS}

            # Recursively clean the value
            cleaned[key] = strip_forbidden_keys(value)
        return cleaned
    elif isinstance(data, list):
        return [strip_forbidden_keys(item) for item in data]
    else:
        return data


class InsightCategory(Enum):
    """Categories for grouping screening insights."""

    TECHNICAL_SKILLS = "technical_skills"
    PROBLEM_SOLVING = "problem_solving"
    COLLABORATION = "collaboration"
    CODE_QUALITY = "code_quality"
    COMMUNICATION = "communication"
    GROWTH_TRAJECTORY = "growth_trajectory"
    WORK_PATTERNS = "work_patterns"
    SECURITY_AWARENESS = "security_awareness"
    SKILL_EVOLUTION = "skill_evolution"  # Added to handle AI responses


class InsightConfidence(Enum):
    """Confidence levels for insights based on available evidence."""

    HIGH = "high"  # Strong, multiple corroborating evidence points
    MEDIUM = "medium"  # Some evidence, reasonable inference
    LOW = "low"  # Limited evidence, speculative
    INSUFFICIENT = "insufficient"  # Not enough data to form insight


@dataclass
class ScreeningInsight:
    """A single screening insight derived from evidence."""

    category: InsightCategory
    title: str
    description: str
    evidence: List[str]  # Specific evidence supporting this insight
    confidence: InsightConfidence
    impact: str  # "positive", "neutral", "concerning", "requires_discussion"
    context_relevance: Dict[str, str] = field(
        default_factory=dict
    )  # How it applies to different hiring contexts

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "category": self.category.value,
            "title": self.title,
            "description": self.description,
            "evidence": self.evidence,
            "confidence": self.confidence.value,
            "impact": self.impact,
            "context_relevance": self.context_relevance,
        }


@dataclass
class ScreeningReport:
    """Complete screening report with insights and recommendations."""

    insights: List[ScreeningInsight]
    key_strengths: List[str]  # Top 3-5 strengths with evidence
    areas_to_explore: List[str]  # Topics for interview discussion
    data_limitations: List[str]  # What we couldn't assess from GitHub
    overall_impression: str  # Brief, balanced summary
    confidence_explanation: str  # Why confidence is high/medium/low

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "insights": [insight.to_dict() for insight in self.insights],
            "key_strengths": self.key_strengths,
            "areas_to_explore": self.areas_to_explore,
            "data_limitations": self.data_limitations,
            "overall_impression": self.overall_impression,
            "confidence_explanation": self.confidence_explanation,
        }


class InsightEngine:
    """Generate evidence-based screening insights from repository analysis."""

    def __init__(self, anthropic_api_key: Optional[str] = None) -> None:
        """Initialize the insight engine with AI capabilities."""
        config = get_config()
        self.anthropic_api_key = anthropic_api_key or config.anthropic_api_key
        self.anthropic_client: Optional[anthropic.Anthropic]

        # Initialize AI client for BASIC+ tiers
        if self.anthropic_api_key:
            self.anthropic_client = anthropic.Anthropic(api_key=self.anthropic_api_key)
        else:
            self.anthropic_client = None

        # Model configuration now comes from tier_config
        from ..tier_config import get_output_limits

        self.model_config = {}
        self.insight_counts = {}  # Will be populated from tier_config

        for tier_name in ["free", "basic", "professional", "enterprise", "scale_plus"]:
            tier_cfg = get_tier_config(tier_name)
            if tier_cfg:
                # Use metrics model for insights, fallback to main model
                self.model_config[tier_name] = (
                    tier_cfg.metrics_model or tier_cfg.main_model
                )
            else:
                self.model_config[tier_name] = (
                    "claude-3-haiku-20240307"  # Default fallback
                )

            # Get insight counts from centralized tier_config
            limits = get_output_limits(tier_name)
            self.insight_counts[tier_name] = limits["max_insights"]

        # Define what we can and cannot determine from GitHub data
        self.github_limitations = [
            "Teamwork dynamics in meetings and discussions",
            "Problem-solving approach under time pressure",
            "Communication style with non-technical stakeholders",
            "Debugging skills on unfamiliar codebases",
            "Performance in pair programming sessions",
            "Ability to handle constructive criticism",
            "Leadership and mentoring capabilities",
            "Domain knowledge depth beyond code",
            "Work performance consistency over time",
            "Cultural fit with specific team dynamics",
        ]

        # Context-specific priorities
        self.context_priorities = {
            "startup": [
                "adaptability",
                "self_direction",
                "rapid_iteration",
                "wearing_many_hats",
            ],
            "enterprise": [
                "process_adherence",
                "documentation",
                "team_collaboration",
                "stability",
            ],
            "agency": [
                "client_communication",
                "project_variety",
                "deadline_awareness",
                "quality_delivery",
            ],
            "open_source": [
                "community_engagement",
                "long_term_commitment",
                "clear_communication",
                "collaboration",
            ],
        }

    def generate_screening_insights(
        self,
        evidence: Dict[str, Any],
        context: str = "general",
        repository_type: Optional[str] = None,
        tier: str = "free",
    ) -> ScreeningReport:
        """
        Generate screening insights from evidence.

        Args:
            evidence: All extracted evidence from repository analysis
            context: Hiring context (startup, enterprise, agency, open_source)
            repository_type: Type of repository analyzed
            tier: Subscription tier (free, basic, professional, enterprise)

        Returns:
            ScreeningReport with evidence-based insights
        """
        insights = []

        # Get insight limits from centralized configuration
        max_insights = self.insight_counts.get(tier.lower(), 2)

        # For non-free tiers, use AI to generate insights
        if tier.lower() != "free" and self.anthropic_client:
            try:
                logger.info(
                    f"Generating AI insights for {tier} tier (max: {max_insights})"
                )
                ai_insights = self._generate_ai_insights(
                    evidence, context, repository_type, tier, max_insights
                )
                logger.info(f"Generated {len(ai_insights)} AI insights for {tier} tier")
                insights.extend(ai_insights)
            except Exception as e:
                logger.error(f"Failed to generate AI insights for {tier} tier: {e}")
                import traceback

                logger.error(f"Traceback: {traceback.format_exc()}")
                # Fall back to rule-based insights
                logger.warning(f"Falling back to rule-based insights for {tier} tier")
                insights = self._generate_rule_based_insights(
                    evidence, context, repository_type
                )
        else:
            # Free tier uses rule-based insights only
            insights = self._generate_rule_based_insights(
                evidence, context, repository_type
            )

        # Sort insights by confidence and impact for prioritization
        def insight_priority(insight: ScreeningInsight) -> tuple[int, int]:
            confidence_order = {
                InsightConfidence.HIGH: 3,
                InsightConfidence.MEDIUM: 2,
                InsightConfidence.LOW: 1,
                InsightConfidence.INSUFFICIENT: 0,
            }
            impact_order = {
                "positive": 3,
                "neutral": 2,
                "concerning": 1,
                "requires_discussion": 1,
            }
            return (
                confidence_order.get(insight.confidence, 0),
                impact_order.get(insight.impact, 0),
            )

        insights.sort(key=insight_priority, reverse=True)

        # Ensure free tier gets at least 1 insight if any exist
        if tier.lower() == "free" and len(insights) > 0:
            insights = insights[: max(1, min(len(insights), max_insights))]
        else:
            insights = insights[:max_insights]

        # Generate key strengths and areas to explore
        key_strengths = self._identify_key_strengths(insights)
        areas_to_explore = self._identify_areas_to_explore(insights, context)

        # Calculate overall confidence
        confidence_explanation = self._explain_confidence_level(evidence, insights)

        # Generate overall impression
        overall_impression = self._generate_overall_impression(
            insights, context, repository_type
        )

        return ScreeningReport(
            insights=insights,
            key_strengths=key_strengths,
            areas_to_explore=areas_to_explore,
            data_limitations=self._get_relevant_limitations(context),
            overall_impression=overall_impression,
            confidence_explanation=confidence_explanation,
        )

    def _analyze_technical_patterns(
        self, patterns: List[Dict[str, Any]], repo_type: Optional[str]
    ) -> List[ScreeningInsight]:
        """Analyze technical patterns to generate insights."""
        insights = []

        # Look for language expertise patterns
        lang_patterns = [p for p in patterns if p.get("type") == "language_expertise"]
        if lang_patterns:
            primary_lang = lang_patterns[0]
            insights.append(
                ScreeningInsight(
                    category=InsightCategory.TECHNICAL_SKILLS,
                    title="Primary Language Expertise",
                    description=f"Demonstrates expertise in {primary_lang.get('finding', 'multiple languages')}",
                    evidence=[primary_lang["finding"]],
                    confidence=InsightConfidence.HIGH,
                    impact="positive",
                    context_relevance={
                        "startup": "Technical expertise crucial for rapid development",
                        "enterprise": "Strong foundation for enterprise-scale development",
                        "agency": "Valuable for diverse client projects",
                        "open_source": "Important for community contributions",
                    },
                )
            )

        # Look for testing patterns
        test_patterns = [
            p for p in patterns if p.get("type") == "test_coverage_structure"
        ]
        if test_patterns:
            test_ratio = float(test_patterns[0].get("ratio", 0))
            if test_ratio > 0.5:
                insights.append(
                    ScreeningInsight(
                        category=InsightCategory.CODE_QUALITY,
                        title="Strong Testing Culture",
                        description=f"Repository shows {test_ratio:.0%} test file ratio, indicating commitment to quality",
                        evidence=[test_patterns[0]["finding"]],
                        confidence=InsightConfidence.HIGH,
                        impact="positive",
                        context_relevance={
                            "startup": "Essential for rapid iteration without breaking things",
                            "enterprise": "Aligns with quality standards and maintainability",
                            "agency": "Ensures deliverables meet client expectations",
                            "open_source": "Critical for community trust and contributions",
                        },
                    )
                )
            elif test_ratio < 0.1:
                insights.append(
                    ScreeningInsight(
                        category=InsightCategory.CODE_QUALITY,
                        title="Limited Test Coverage Observed",
                        description="Repository shows minimal test coverage, worth discussing testing philosophy",
                        evidence=[test_patterns[0]["finding"]],
                        confidence=InsightConfidence.MEDIUM,
                        impact="requires_discussion",
                        context_relevance={
                            "startup": "May indicate focus on rapid prototyping over stability",
                            "enterprise": "Could be a concern for production reliability",
                            "agency": "Might affect project maintenance and handoffs",
                            "open_source": "May limit community contributions",
                        },
                    )
                )

        # Look for architecture patterns
        arch_patterns = [
            p for p in patterns if "architecture" in p.get("finding", "").lower()
        ]
        if arch_patterns:
            insights.append(
                ScreeningInsight(
                    category=InsightCategory.TECHNICAL_SKILLS,
                    title="Architectural Thinking",
                    description="Shows evidence of thoughtful code organization and structure",
                    evidence=[p["finding"] for p in arch_patterns[:2]],
                    confidence=InsightConfidence.MEDIUM,
                    impact="positive",
                    context_relevance={
                        "startup": "Important for building scalable foundations",
                        "enterprise": "Critical for large-scale system design",
                        "agency": "Helps manage multiple project complexities",
                        "open_source": "Facilitates community understanding",
                    },
                )
            )

        # Look for modern practices
        modern_patterns = [
            p
            for p in patterns
            if any(
                term in p.get("finding", "").lower()
                for term in ["typescript", "async", "modern", "es6", "hooks"]
            )
        ]
        if modern_patterns:
            insights.append(
                ScreeningInsight(
                    category=InsightCategory.TECHNICAL_SKILLS,
                    title="Modern Development Practices",
                    description="Uses contemporary tools and patterns, staying current with technology",
                    evidence=[p["finding"] for p in modern_patterns[:2]],
                    confidence=InsightConfidence.HIGH,
                    impact="positive",
                    context_relevance={
                        "startup": "Indicates adaptability and learning mindset",
                        "enterprise": "Shows professional development commitment",
                        "agency": "Valuable for diverse client projects",
                        "open_source": "Attracts modern contributors",
                    },
                )
            )

        return insights

    def _analyze_behavioral_patterns(
        self, behavioral_data: Dict[str, Any], context: str
    ) -> List[ScreeningInsight]:
        """Analyze behavioral patterns from commit and work patterns."""
        insights = []

        work_style = behavioral_data.get("work_style", "unknown")
        if work_style != "unknown":
            if work_style == "consistent_contributor":
                insights.append(
                    ScreeningInsight(
                        category=InsightCategory.WORK_PATTERNS,
                        title="Consistent Work Patterns",
                        description="Shows steady, reliable contribution patterns over time",
                        evidence=[f"Work style identified as: {work_style}"],
                        confidence=InsightConfidence.HIGH,
                        impact="positive",
                        context_relevance={
                            "startup": "Provides stability in fast-paced environment",
                            "enterprise": "Aligns with structured development cycles",
                            "agency": "Reliable for project timelines",
                            "open_source": "Dependable maintainer potential",
                        },
                    )
                )
            elif work_style == "burst_contributor":
                insights.append(
                    ScreeningInsight(
                        category=InsightCategory.WORK_PATTERNS,
                        title="Sprint-Focused Work Style",
                        description="Works in focused bursts, potentially indicating project-based approach",
                        evidence=[f"Work style identified as: {work_style}"],
                        confidence=InsightConfidence.MEDIUM,
                        impact="neutral",
                        context_relevance={
                            "startup": "May align with sprint-based development",
                            "enterprise": "Worth discussing work style preferences",
                            "agency": "Could match project-based nature",
                            "open_source": "Common pattern for contributors",
                        },
                    )
                )

        # Work-life balance indicators
        balance = behavioral_data.get("work_life_balance", "unknown")
        if balance == "concerning":
            insights.append(
                ScreeningInsight(
                    category=InsightCategory.WORK_PATTERNS,
                    title="Intense Work Patterns Observed",
                    description="Shows signs of very high activity levels, worth discussing sustainable practices",
                    evidence=[
                        "Frequent late-night commits",
                        "Weekend activity patterns",
                    ],
                    confidence=InsightConfidence.MEDIUM,
                    impact="requires_discussion",
                    context_relevance={
                        "startup": "May indicate high dedication but burnout risk",
                        "enterprise": "Important to discuss work-life expectations",
                        "agency": "Could affect long-term performance",
                        "open_source": "Sustainability concern for maintainers",
                    },
                )
            )

        return insights

    def _analyze_collaboration_patterns(
        self, collab_patterns: List[Dict[str, Any]], context: str
    ) -> List[ScreeningInsight]:
        """Analyze collaboration and teamwork indicators."""
        insights = []

        # Look for multi-contributor patterns
        multi_contrib = [p for p in collab_patterns if p.get("type") == "collaboration"]
        if multi_contrib and multi_contrib[0].get("top_contributors", []):
            num_contributors = len(multi_contrib[0]["top_contributors"])
            if num_contributors > 3:
                insights.append(
                    ScreeningInsight(
                        category=InsightCategory.COLLABORATION,
                        title="Team Collaboration Experience",
                        description=f"Has worked with {num_contributors}+ contributors, showing team experience",
                        evidence=[
                            f"Collaborated with {', '.join(multi_contrib[0]['top_contributors'][:3])}..."
                        ],
                        confidence=InsightConfidence.HIGH,
                        impact="positive",
                        context_relevance={
                            "startup": "Can work effectively in small teams",
                            "enterprise": "Experience with team dynamics",
                            "agency": "Comfortable with client collaboration",
                            "open_source": "Strong community collaboration",
                        },
                    )
                )

        # Look for PR/issue patterns
        pr_patterns = [
            p for p in collab_patterns if "pull request" in p.get("finding", "").lower()
        ]
        if pr_patterns:
            insights.append(
                ScreeningInsight(
                    category=InsightCategory.COMMUNICATION,
                    title="Code Review Participation",
                    description="Actively participates in code review process",
                    evidence=[p["finding"] for p in pr_patterns[:2]],
                    confidence=InsightConfidence.MEDIUM,
                    impact="positive",
                    context_relevance={
                        "startup": "Values collaborative development",
                        "enterprise": "Follows review processes",
                        "agency": "Quality-conscious approach",
                        "open_source": "Community-oriented developer",
                    },
                )
            )

        return insights

    def _analyze_growth_trajectory(
        self, skill_evolution: Dict[str, Any], temporal_patterns: Dict[str, Any]
    ) -> List[ScreeningInsight]:
        """Analyze developer growth and learning patterns."""
        insights = []

        progression = skill_evolution.get("development_trajectory", "unknown")
        growth_rate = skill_evolution.get("growth_rate", 0)

        if progression == "steady_growth" and growth_rate > 0:
            insights.append(
                ScreeningInsight(
                    category=InsightCategory.GROWTH_TRAJECTORY,
                    title="Continuous Learning Pattern",
                    description=f"Shows {growth_rate:.1%} skill expansion over time, indicating growth mindset",
                    evidence=[
                        f"Progression: {progression}",
                        f"Recent focus: {skill_evolution.get('recent_focus', 'varied technologies')}",
                    ],
                    confidence=InsightConfidence.HIGH,
                    impact="positive",
                    context_relevance={
                        "startup": "Adaptable to changing technology needs",
                        "enterprise": "Committed to professional development",
                        "agency": "Can handle diverse projects",
                        "open_source": "Evolving with community needs",
                    },
                )
            )

        # Technology diversity
        if skill_evolution.get("technology_breadth", 0) > 3:
            insights.append(
                ScreeningInsight(
                    category=InsightCategory.TECHNICAL_SKILLS,
                    title="Diverse Technology Experience",
                    description="Works across multiple languages and frameworks, showing versatility",
                    evidence=[
                        f"Primary: {skill_evolution.get('primary_languages', ['Not specified'])}",
                        f"Also uses: {skill_evolution.get('secondary_languages', ['Various'])}",
                    ],
                    confidence=InsightConfidence.MEDIUM,
                    impact="positive",
                    context_relevance={
                        "startup": "Can wear multiple hats effectively",
                        "enterprise": "Brings broad perspective",
                        "agency": "Ready for varied client needs",
                        "open_source": "Can contribute across projects",
                    },
                )
            )

        return insights

    def _analyze_code_quality(
        self,
        quality_indicators: List[Dict[str, Any]],
        technical_patterns: List[Dict[str, Any]],
    ) -> List[ScreeningInsight]:
        """Analyze code quality practices and standards."""
        insights = []

        # Documentation quality
        doc_patterns = [
            p for p in technical_patterns if p.get("type") == "documentation_quality"
        ]
        if doc_patterns:
            if "comprehensive" in doc_patterns[0].get("finding", "").lower():
                insights.append(
                    ScreeningInsight(
                        category=InsightCategory.COMMUNICATION,
                        title="Strong Documentation Practices",
                        description="Writes clear, comprehensive documentation for code",
                        evidence=[doc_patterns[0]["finding"]],
                        confidence=InsightConfidence.HIGH,
                        impact="positive",
                        context_relevance={
                            "startup": "Helps onboard team members quickly",
                            "enterprise": "Essential for maintenance",
                            "agency": "Critical for client handoffs",
                            "open_source": "Enables community adoption",
                        },
                    )
                )

        # Code organization from quality indicators
        modular_patterns = [
            p
            for p in quality_indicators
            if "modular" in p.get("finding", "").lower()
            or "architecture" in p.get("finding", "").lower()
        ]
        if modular_patterns:
            insights.append(
                ScreeningInsight(
                    category=InsightCategory.CODE_QUALITY,
                    title="Modular Code Design",
                    description="Structures code in reusable, maintainable components",
                    evidence=[p["finding"] for p in modular_patterns[:2]],
                    confidence=InsightConfidence.MEDIUM,
                    impact="positive",
                    context_relevance={
                        "startup": "Enables rapid feature development",
                        "enterprise": "Supports large-scale systems",
                        "agency": "Facilitates code reuse across projects",
                        "open_source": "Easy for contributors to understand",
                    },
                )
            )

        return insights

    def _analyze_security_awareness(
        self, security_issues: List[Dict[str, Any]], security_practices: Dict[str, Any]
    ) -> List[ScreeningInsight]:
        """Analyze security awareness and practices."""
        insights = []

        if not security_issues:
            insights.append(
                ScreeningInsight(
                    category=InsightCategory.SECURITY_AWARENESS,
                    title="Security-Conscious Development",
                    description="No obvious security vulnerabilities detected in code",
                    evidence=[
                        "No exposed credentials",
                        "No common vulnerabilities found",
                    ],
                    confidence=InsightConfidence.MEDIUM,
                    impact="positive",
                    context_relevance={
                        "startup": "Protects early-stage product integrity",
                        "enterprise": "Meets security compliance needs",
                        "agency": "Ensures client data protection",
                        "open_source": "Maintains project reputation",
                    },
                )
            )
        elif len(security_issues) > 2:
            insights.append(
                ScreeningInsight(
                    category=InsightCategory.SECURITY_AWARENESS,
                    title="Security Practices Need Review",
                    description="Several potential security concerns identified for discussion",
                    evidence=[issue["finding"] for issue in security_issues[:2]],
                    confidence=InsightConfidence.HIGH,
                    impact="requires_discussion",
                    context_relevance={
                        "startup": "Important to establish secure practices early",
                        "enterprise": "Critical for compliance requirements",
                        "agency": "Affects client trust and liability",
                        "open_source": "Community security concern",
                    },
                )
            )

        return insights

    def _identify_key_strengths(self, insights: List[ScreeningInsight]) -> List[str]:
        """Identify top 3-5 key strengths from insights."""
        positive_insights = [i for i in insights if i.impact == "positive"]

        # Sort by confidence and category diversity
        sorted_insights = sorted(
            positive_insights,
            key=lambda x: (
                x.confidence.value == "high",
                x.confidence.value == "medium",
            ),
            reverse=True,
        )

        strengths: List[str] = []
        categories_used = set()

        for insight in sorted_insights:
            if len(strengths) >= 5:
                break
            if insight.category not in categories_used or len(strengths) < 3:
                strengths.append(f"{insight.title}: {insight.description}")
                categories_used.add(insight.category)

        return strengths

    def _identify_areas_to_explore(
        self, insights: List[ScreeningInsight], context: str
    ) -> List[str]:
        """Identify areas that need exploration in interviews."""
        areas = []

        # Add insights that require discussion
        discussion_insights = [i for i in insights if i.impact == "requires_discussion"]
        for insight in discussion_insights:
            relevance = insight.context_relevance.get(context, "Worth exploring")
            areas.append(f"{insight.title} - {relevance}")

        # Add standard areas we can't assess from GitHub
        if context == "startup":
            areas.extend(
                [
                    "Comfort with ambiguity and changing requirements",
                    "Experience with rapid prototyping vs. production code",
                    "Approach to technical debt in fast-moving environment",
                ]
            )
        elif context == "enterprise":
            areas.extend(
                [
                    "Experience with formal development processes",
                    "Approach to documentation and knowledge transfer",
                    "Collaboration in large, distributed teams",
                ]
            )
        elif context == "agency":
            areas.extend(
                [
                    "Client communication and requirement gathering",
                    "Balancing quality with project timelines",
                    "Experience with diverse technology stacks",
                ]
            )

        # Always include some fundamentals
        areas.extend(
            [
                "Problem-solving approach on unfamiliar challenges",
                "Debugging methodology and tools",
                "Preferred collaboration and communication style",
            ]
        )

        return areas[:8]  # Limit to 8 most relevant areas

    def _get_relevant_limitations(self, context: str) -> List[str]:
        """Get limitations relevant to the hiring context."""
        base_limitations = [
            "Actual job performance and consistency",
            "Soft skills and interpersonal dynamics",
            "Domain-specific knowledge depth",
        ]

        if context == "startup":
            base_limitations.extend(
                [
                    "Ability to handle ambiguity and pivots",
                    "Customer interaction skills",
                    "Resourcefulness under constraints",
                ]
            )
        elif context == "enterprise":
            base_limitations.extend(
                [
                    "Experience with enterprise tools and processes",
                    "Stakeholder management abilities",
                    "Compliance and governance understanding",
                ]
            )
        elif context == "agency":
            base_limitations.extend(
                [
                    "Client presentation skills",
                    "Project estimation accuracy",
                    "Multi-project management ability",
                ]
            )

        return base_limitations[:5]

    def _generate_rule_based_insights(
        self, evidence: Dict[str, Any], context: str, repository_type: Optional[str]
    ) -> List[ScreeningInsight]:
        """Generate rule-based insights for free tier."""
        insights = []

        # Analyze technical patterns
        technical_insights = self._analyze_technical_patterns(
            evidence.get("technical_patterns", []), repository_type
        )
        insights.extend(technical_insights)

        # Basic behavioral patterns
        behavioral_insights = self._analyze_behavioral_patterns(
            evidence.get("behavioral_analysis", {}), context
        )
        insights.extend(behavioral_insights[:1])  # Limit for free tier

        return insights

    def _generate_ai_insights(
        self,
        evidence: Dict[str, Any],
        context: str,
        repository_type: Optional[str],
        tier: str,
        max_insights: int,
    ) -> List[ScreeningInsight]:
        """Generate AI-powered insights based on tier."""
        from ...ai.evidence_based_prompts import EVIDENCE_BASED_INSIGHT_PROMPT

        # Get context-specific prompt enhancement
        # context_prompt = ContextPromptEnhancer.get_context_prompt(context, evidence)
        # Select model based on tier
        model = self.model_config.get(tier.lower(), self.model_config["basic"])

        # Use the evidence-based insight prompt template
        prompt = EVIDENCE_BASED_INSIGHT_PROMPT.format(
            context=context, evidence_json=json.dumps(evidence, indent=2)
        )

        try:
            # Get tier-specific token limits from centralized config
            from ...core.tier_config import TIER_CONFIGURATIONS

            tier_config = TIER_CONFIGURATIONS.get(tier.lower())
            max_tokens = (
                tier_config.unified_approach_tokens if tier_config else 2000  # fallback
            )

            logger.debug(
                f"Making AI call for {tier} tier with model {model}, max_tokens: {max_tokens}"
            )

            # Import the wrapper to add timeout
            from ...ai.anthropic_wrapper import AnthropicWrapper

            # Use wrapper if not already wrapped
            client: Any = self.anthropic_client
            if not isinstance(client, AnthropicWrapper):
                client = AnthropicWrapper(api_key=self.anthropic_api_key)

            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=0.1,  # Lower temperature for consistency
                system="You are an expert code reviewer. Always respond with valid JSON only, no additional text or markdown formatting.",
                messages=[{"role": "user", "content": prompt}],
            )

            # Parse AI response
            if hasattr(response.content[0], "text"):
                ai_response = response.content[0].text
            else:
                logger.error(f"Unexpected response format: {type(response.content[0])}")
                return self._generate_rule_based_insights(
                    evidence, context, repository_type
                )

            # Try to extract JSON from the response
            try:
                # Sometimes AI wraps JSON in markdown code blocks
                if "```json" in ai_response:
                    ai_response = (
                        ai_response.split("```json")[1].split("```")[0].strip()
                    )
                elif "```" in ai_response:
                    ai_response = ai_response.split("```")[1].split("```")[0].strip()

                insights_data = json.loads(ai_response)

                # Apply post-processing firewall to strip forbidden keys
                insights_data = strip_forbidden_keys(insights_data)

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.debug(f"Raw response: {ai_response[:500]}...")
                # Try to extract insights manually or fall back
                return self._generate_rule_based_insights(
                    evidence, context, repository_type
                )

            # Convert AI response to ScreeningInsight objects
            ai_insights = []

            # Process key observations
            for idx, observation in enumerate(
                insights_data.get("key_observations", [])
            ):
                try:
                    # Determine category based on finding content
                    category = self._categorize_observation(
                        observation.get("finding", "")
                    )

                    # Create descriptive title from finding
                    finding_text = observation.get("finding", "Observation")
                    title = self._generate_descriptive_title(finding_text, category)

                    insight = ScreeningInsight(
                        category=category,
                        title=title,
                        description=observation.get("finding", ""),
                        evidence=observation.get("evidence", []),
                        confidence=(
                            InsightConfidence.HIGH
                            if len(observation.get("evidence", [])) > 1
                            else InsightConfidence.MEDIUM
                        ),
                        impact=(
                            "positive"
                            if "strength" in observation.get("finding", "").lower()
                            else "neutral"
                        ),
                        context_relevance={
                            context: observation.get(
                                "relevance_to_context", "Relevant for this context"
                            )
                        },
                    )
                    ai_insights.append(insight)
                except (ValueError, KeyError) as e:
                    logger.warning(f"Failed to parse observation: {e}")
                    continue

            # Add patterns as insights
            for pattern in insights_data.get("patterns_observed", [])[
                :2
            ]:  # Limit patterns
                try:
                    insight = ScreeningInsight(
                        category=InsightCategory.WORK_PATTERNS,
                        title=f"Pattern: {pattern.get('pattern', 'Observed Pattern')}",
                        description=f"{pattern.get('pattern', '')} - {pattern.get('frequency', '')}",
                        evidence=pattern.get("examples", []),
                        confidence=InsightConfidence.MEDIUM,
                        impact="neutral",
                        context_relevance={context: "Pattern observed in repository"},
                    )
                    ai_insights.append(insight)
                except Exception as e:
                    logger.warning(f"Failed to parse pattern: {e}")
                    continue

            return ai_insights[:max_insights]  # Respect tier limits

        except Exception as e:
            logger.error(f"AI insight generation failed for {tier} tier: {e}")
            import traceback

            logger.error(f"Full error: {traceback.format_exc()}")
            # Fall back to rule-based insights
            return self._generate_rule_based_insights(
                evidence, context, repository_type
            )

    def _categorize_observation(self, finding: str) -> InsightCategory:
        """Categorize an observation based on its content using pattern matching."""
        finding_lower = finding.lower()

        # Define category patterns
        category_patterns = {
            InsightCategory.CODE_QUALITY: [
                "test",
                "testing",
                "spec",
                "jest",
                "pytest",
                "unit",
                "integration",
                "quality",
                "clean",
                "lint",
                "format",
                "style",
                "coverage",
                "refactor",
                "maintenance",
                "bug",
                "fix",
                "error",
                "exception",
            ],
            InsightCategory.TECHNICAL_SKILLS: [
                "language",
                "framework",
                "library",
                "stack",
                "technology",
                "tool",
                # Core Languages
                "javascript",
                "typescript",
                "python",
                "java",
                "go",
                "rust",
                "php",
                "ruby",
                "kotlin",
                "scala",
                "clojure",
                "swift",
                "dart",
                # Web Frameworks
                "react",
                "vue",
                "angular",
                "svelte",
                "django",
                "flask",
                "fastapi",
                "laravel",
                "rails",
                "spring",
                "express",
                "nestjs",
                # Mobile & Desktop
                "flutter",
                "react native",
                "ionic",
                "electron",
                "unity",
                "unreal",
                # Data & AI
                "tensorflow",
                "pytorch",
                "pandas",
                "numpy",
                "jupyter",
                "spark",
                "r",
                "matlab",
                # Infrastructure & Cloud
                "docker",
                "kubernetes",
                "aws",
                "azure",
                "gcp",
                "terraform",
                "ansible",
                "jenkins",
                # Databases & APIs
                "sql",
                "nosql",
                "mongodb",
                "redis",
                "graphql",
                "rest",
                "grpc",
                "api",
                "database",
                # Other Tech
                "blockchain",
                "microservices",
                "serverless",
                "cloud",
                "devops",
                "ci/cd",
            ],
            InsightCategory.WORK_PATTERNS: [
                "commit",
                "commits",
                "work",
                "pattern",
                "frequency",
                "schedule",
                "timing",
                "hours",
                "regular",
                "consistent",
                "sprint",
                "burst",
                "productivity",
                "velocity",
                "pace",
                "workflow",
            ],
            InsightCategory.COMMUNICATION: [
                "documentation",
                "docs",
                "readme",
                "comment",
                "comments",
                "message",
                "description",
                "explain",
                "clear",
                "communication",
                "writing",
            ],
            InsightCategory.SECURITY_AWARENESS: [
                "security",
                "secure",
                "vulnerability",
                "auth",
                "authentication",
                "authorization",
                "encryption",
                "ssl",
                "https",
                "token",
                "password",
            ],
            InsightCategory.GROWTH_TRAJECTORY: [
                "refactor",
                "improve",
                "evolve",
                "learn",
                "learning",
                "skill",
                "growth",
                "progress",
                "development",
                "advancement",
                "education",
            ],
            InsightCategory.COLLABORATION: [
                "team",
                "teams",
                "collaborate",
                "collaboration",
                "review",
                "pr",
                "pull request",
                "contributor",
                "contributors",
                "pair",
                "merge",
            ],
        }

        # Find best matching category
        category_scores = {}
        for category, keywords in category_patterns.items():
            score = sum(1 for keyword in keywords if keyword in finding_lower)
            if score > 0:
                category_scores[category] = score

        if category_scores:
            return max(category_scores.items(), key=lambda x: x[1])[0]

        return InsightCategory.TECHNICAL_SKILLS  # Default

    def _generate_descriptive_title(
        self, finding: str, category: InsightCategory
    ) -> str:
        """Generate a descriptive title from finding text."""
        # If finding is already short and descriptive, use it
        if len(finding) <= 60 and any(char.isupper() for char in finding):
            return finding

        finding_lower = finding.lower()

        # Define title mapping with comprehensive language and tech patterns
        title_patterns = {
            InsightCategory.TECHNICAL_SKILLS: {
                # Web Frontend Frameworks
                ("javascript", "js"): "JavaScript Expertise",
                ("typescript", "ts"): "TypeScript Development",
                ("react", "reactjs"): "React Framework Experience",
                ("vue", "vuejs"): "Vue.js Framework Experience",
                ("angular", "angularjs"): "Angular Framework Experience",
                ("svelte", "sveltekit"): "Svelte Framework Experience",
                ("solid", "solidjs"): "SolidJS Framework Experience",
                ("lit", "lit-element"): "Lit Web Components",
                ("alpine", "alpinejs"): "Alpine.js Lightweight Framework",
                # JavaScript Runtime & Backend
                ("node", "nodejs"): "Node.js Backend Development",
                ("express", "expressjs"): "Express.js Web Development",
                ("fastify",): "Fastify High-performance Framework",
                ("koa", "koajs"): "Koa.js Web Framework",
                ("nestjs", "nest"): "NestJS Enterprise Framework",
                ("nextjs", "next.js"): "Next.js Full-stack Development",
                ("nuxt", "nuxtjs"): "Nuxt.js Vue Framework",
                ("remix",): "Remix Full-stack Framework",
                ("sveltekit",): "SvelteKit Full-stack Framework",
                ("astro",): "Astro Static Site Generator",
                ("gatsby",): "Gatsby React Framework",
                # Python Web Frameworks
                ("python",): "Python Development Skills",
                ("django",): "Django Web Framework",
                ("flask",): "Flask Micro-framework",
                ("fastapi",): "FastAPI High-performance API Framework",
                ("tornado",): "Tornado Async Framework",
                ("pyramid",): "Pyramid Web Framework",
                ("bottle",): "Bottle Micro-framework",
                ("starlette",): "Starlette Async Framework",
                ("quart",): "Quart Async Flask Alternative",
                # Java & JVM Frameworks
                ("java",): "Java Enterprise Development",
                ("spring", "spring boot"): "Spring Boot Framework",
                ("spring mvc",): "Spring MVC Framework",
                ("micronaut",): "Micronaut Framework",
                ("quarkus",): "Quarkus Native Java Framework",
                ("play", "play framework"): "Play Framework",
                ("vert.x", "vertx"): "Vert.x Reactive Framework",
                ("dropwizard",): "Dropwizard Framework",
                # PHP Frameworks
                ("php",): "PHP Web Development",
                ("laravel",): "Laravel PHP Framework",
                ("symfony",): "Symfony PHP Framework",
                ("codeigniter",): "CodeIgniter Framework",
                ("yii", "yii2"): "Yii PHP Framework",
                ("cakephp",): "CakePHP Framework",
                ("zend", "laminas"): "Zend/Laminas Framework",
                ("phalcon",): "Phalcon High-performance Framework",
                # Ruby Frameworks
                ("ruby",): "Ruby Development",
                ("rails", "ruby on rails"): "Ruby on Rails Framework",
                ("sinatra",): "Sinatra Micro-framework",
                ("hanami",): "Hanami Web Framework",
                ("roda",): "Roda Ruby Framework",
                # Go Frameworks
                ("go", "golang"): "Go Systems Programming",
                ("gin",): "Gin Go Framework",
                ("echo",): "Echo Go Framework",
                ("fiber",): "Fiber Go Framework",
                ("beego",): "Beego Go Framework",
                ("chi",): "Chi Go Router",
                ("gorilla",): "Gorilla Web Toolkit",
                # C# .NET Frameworks
                ("c#", "csharp", "dotnet"): "C# .NET Development",
                ("asp.net", "aspnet"): "ASP.NET Framework",
                ("blazor",): "Blazor WebAssembly Framework",
                ("minimal api",): "ASP.NET Minimal APIs",
                ("maui",): ".NET MAUI Cross-platform",
                # Rust Web Frameworks
                ("rust",): "Rust Systems Programming",
                ("actix", "actix-web"): "Actix Web Framework",
                ("warp",): "Warp Rust Framework",
                ("rocket",): "Rocket Rust Framework",
                ("axum",): "Axum Rust Framework",
                ("tide",): "Tide Rust Framework",
                # Other Backend Languages
                ("kotlin",): "Kotlin Development",
                ("ktor",): "Ktor Kotlin Framework",
                ("scala",): "Scala Development",
                ("akka",): "Akka Scala Framework",
                ("clojure",): "Clojure Functional Programming",
                ("ring", "compojure"): "Clojure Web Frameworks",
                # Mobile Development
                ("swift", "swiftui"): "iOS Swift Development",
                ("objective-c", "objc"): "iOS Objective-C Development",
                ("flutter", "dart"): "Flutter Mobile Development",
                ("react native", "react-native"): "React Native Mobile Development",
                ("ionic",): "Ionic Cross-platform Development",
                ("xamarin",): "Xamarin Cross-platform Development",
                ("cordova", "phonegap"): "Cordova Mobile Development",
                ("nativescript",): "NativeScript Mobile Development",
                ("expo",): "Expo React Native Development",
                ("capacitor",): "Capacitor Mobile Development",
                # Data Science & Analytics
                ("r",): "R Data Analysis",
                ("matlab",): "MATLAB Scientific Computing",
                ("julia",): "Julia Scientific Computing",
                ("pandas", "numpy"): "Python Data Science",
                ("scipy",): "SciPy Scientific Computing",
                ("scikit-learn", "sklearn"): "Scikit-learn Machine Learning",
                ("tensorflow", "tf"): "TensorFlow Machine Learning",
                ("pytorch",): "PyTorch Deep Learning",
                ("keras",): "Keras Deep Learning",
                ("xgboost",): "XGBoost Gradient Boosting",
                ("lightgbm",): "LightGBM Machine Learning",
                ("catboost",): "CatBoost Gradient Boosting",
                ("statsmodels",): "Statsmodels Statistical Analysis",
                ("plotly", "matplotlib", "seaborn"): "Data Visualization",
                ("jupyter", "notebook"): "Jupyter Notebook Development",
                ("dask",): "Dask Parallel Computing",
                ("spark", "pyspark"): "Apache Spark Big Data",
                # Systems & Infrastructure
                ("c", "c++"): "Systems Programming",
                ("assembly", "asm"): "Low-level Systems Programming",
                ("shell", "bash", "zsh"): "Shell Scripting",
                ("powershell",): "PowerShell Automation",
                # Databases
                ("sql", "mysql", "postgresql"): "SQL Database Management",
                ("mongodb", "nosql"): "NoSQL Database Experience",
                ("redis",): "Redis Caching",
                ("elasticsearch",): "Elasticsearch Search Engine",
                # Cloud & DevOps
                ("docker",): "Docker Containerization",
                ("kubernetes", "k8s"): "Kubernetes Orchestration",
                ("aws", "amazon web services"): "AWS Cloud Services",
                ("azure",): "Microsoft Azure Cloud",
                ("gcp", "google cloud"): "Google Cloud Platform",
                ("terraform",): "Infrastructure as Code",
                ("ansible",): "Ansible Configuration Management",
                ("chef",): "Chef Infrastructure Automation",
                ("puppet",): "Puppet Configuration Management",
                ("vagrant",): "Vagrant Development Environments",
                ("jenkins",): "Jenkins CI/CD Pipeline",
                ("gitlab ci", "github actions"): "CI/CD Pipeline Automation",
                ("helm",): "Helm Kubernetes Package Manager",
                ("istio",): "Istio Service Mesh",
                ("prometheus",): "Prometheus Monitoring",
                ("grafana",): "Grafana Observability",
                ("elk", "elasticsearch"): "ELK Stack Logging",
                ("jaeger",): "Jaeger Distributed Tracing",
                # API & Architecture
                ("api", "rest"): "REST API Development",
                ("graphql",): "GraphQL API Development",
                ("grpc",): "gRPC High-performance RPC",
                ("websocket",): "WebSocket Real-time Communication",
                ("microservices",): "Microservices Architecture",
                ("serverless", "lambda"): "Serverless Architecture",
                ("event-driven",): "Event-driven Architecture",
                ("saga pattern",): "Saga Pattern Implementation",
                # Blockchain & Web3
                ("blockchain",): "Blockchain Development",
                ("ethereum", "solidity"): "Ethereum Smart Contracts",
                ("web3",): "Web3 Development",
                ("defi",): "DeFi Protocol Development",
                ("nft",): "NFT Development",
                ("smart contract",): "Smart Contract Development",
                # Game Development
                ("unity",): "Unity Game Development",
                ("unreal", "ue4", "ue5"): "Unreal Engine Game Development",
                ("godot",): "Godot Game Engine",
                ("pygame",): "Pygame Game Development",
                ("three.js", "threejs"): "Three.js 3D Web Graphics",
                ("webgl",): "WebGL Graphics Programming",
                # Desktop Development
                ("electron",): "Electron Desktop Development",
                ("tauri",): "Tauri Rust Desktop Apps",
                ("qt",): "Qt Cross-platform Development",
                ("gtk",): "GTK+ Linux Desktop Development",
                ("winui",): "WinUI Windows Development",
                ("avalonia",): "Avalonia Cross-platform UI",
                "default": "Technical Skill Demonstration",
            },
            InsightCategory.CODE_QUALITY: {
                ("test", "testing", "spec", "jest"): "Testing Practices",
                ("error", "exception", "handling"): "Error Handling Approach",
                ("documentation", "docs", "readme"): "Code Documentation",
                ("lint", "format", "style"): "Code Standards",
                ("refactor", "clean"): "Code Refactoring",
                "default": "Code Quality Indicators",
            },
            InsightCategory.WORK_PATTERNS: {
                ("commit", "commits"): "Development Workflow",
                ("time", "schedule", "hours"): "Work Schedule Patterns",
                ("frequency", "regular"): "Consistency Patterns",
                ("sprint", "burst"): "Work Intensity Patterns",
                "default": "Work Style Analysis",
            },
            InsightCategory.COLLABORATION: {
                ("team", "teams"): "Team Collaboration",
                ("review", "pr", "pull request"): "Code Review Participation",
                ("contributor", "contributors"): "Multi-contributor Experience",
                ("merge", "branch"): "Branch Management",
                "default": "Collaboration Indicators",
            },
            InsightCategory.GROWTH_TRAJECTORY: {
                ("learning", "learn"): "Continuous Learning",
                ("skill", "skills"): "Skill Development",
                ("progress", "growth"): "Professional Growth",
                "default": "Learning and Growth Patterns",
            },
            InsightCategory.SECURITY_AWARENESS: {
                ("security", "secure"): "Security Implementation",
                ("auth", "authentication"): "Authentication Practices",
                ("vulnerability", "vuln"): "Security Risk Management",
                "default": "Security Practices",
            },
            InsightCategory.COMMUNICATION: {
                ("comment", "comments"): "Code Documentation",
                ("message", "description"): "Communication Clarity",
                ("readme", "docs"): "Project Documentation",
                "default": "Communication Style",
            },
        }

        # Get patterns for the category
        patterns = title_patterns.get(category, {})

        # Find matching pattern
        for keywords, title in patterns.items():
            if keywords == "default":
                continue
            if any(keyword in finding_lower for keyword in keywords):
                return title

        # Use default for category
        return patterns.get("default", self._extract_title_from_text(finding))

    def _extract_title_from_text(self, finding: str) -> str:
        """Extract a title from finding text as fallback."""
        words = finding.split()[:6]  # First 6 words
        title = " ".join(words)
        return title.title() if len(title) <= 60 else title[:57] + "..."

    def _explain_confidence_level(
        self, evidence: Dict[str, Any], insights: List[ScreeningInsight]
    ) -> str:
        """Explain the confidence level of the analysis."""
        high_confidence_count = sum(
            1 for i in insights if i.confidence == InsightConfidence.HIGH
        )
        total_insights = len(insights)

        # Calculate evidence completeness
        evidence_types = sum(1 for k, v in evidence.items() if v and k != "metadata")

        if high_confidence_count > total_insights * 0.6 and evidence_types >= 4:
            return (
                f"High confidence based on {evidence_types} types of evidence analyzed "
                f"with {high_confidence_count}/{total_insights} high-confidence insights. "
                "Multiple data points corroborate the findings."
            )
        elif high_confidence_count > total_insights * 0.3 and evidence_types >= 3:
            return (
                f"Medium confidence with {evidence_types} evidence types available "
                f"and {high_confidence_count}/{total_insights} high-confidence insights. "
                "Some areas have limited data for complete assessment."
            )
        else:
            return (
                f"Limited confidence due to sparse evidence ({evidence_types} types) "
                f"with only {high_confidence_count}/{total_insights} high-confidence insights. "
                "Recommend thorough technical interview for validation."
            )

    def _generate_overall_impression(
        self, insights: List[ScreeningInsight], context: str, repo_type: Optional[str]
    ) -> str:
        """Generate a balanced overall impression."""
        positive_count = sum(1 for i in insights if i.impact == "positive")
        concern_count = sum(1 for i in insights if i.impact == "requires_discussion")

        # Categorize the developer profile
        if positive_count > len(insights) * 0.7:
            tone = "strong positive indicators"
        elif positive_count > len(insights) * 0.5:
            tone = "generally positive profile"
        elif concern_count > len(insights) * 0.5:
            tone = "several areas needing discussion"
        else:
            tone = "mixed signals requiring clarification"

        # Build context-aware impression
        if context == "startup":
            focus = "adaptability and self-direction"
        elif context == "enterprise":
            focus = "process adherence and collaboration"
        elif context == "agency":
            focus = "versatility and delivery focus"
        else:
            focus = "technical capabilities"

        repo_context = f" in {repo_type} development" if repo_type else ""

        return (
            f"Repository analysis shows {tone}{repo_context}. "
            f"The evidence suggests {focus} with {len(insights)} specific insights identified. "
            "While GitHub data provides useful screening indicators, "
            "a technical interview is essential to validate findings and explore areas "
            "that cannot be assessed through code analysis alone."
        )
