# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Evidence-based insight engine without arbitrary metrics.

This module generates insights from actual observations and evidence,
acknowledging limitations and avoiding arbitrary judgments.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List

from ...utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class EvidenceBasedInsight:
    """An insight derived from actual evidence without arbitrary scoring."""

    category: str  # technical, behavioral, collaboration, quality, growth
    observation: str  # What we actually observed
    evidence: List[str]  # Specific evidence supporting this
    context: str  # Additional context for interpretation

    # What we can't determine
    limitations: List[str] = field(default_factory=list)

    # Questions for further exploration
    interview_topics: List[str] = field(default_factory=list)

    # Relevance to different contexts (descriptive, not scored)
    context_relevance: Dict[str, str] = field(default_factory=dict)


@dataclass
class InsightReport:
    """Complete insight report based on evidence."""

    insights: List[EvidenceBasedInsight]

    # Summary of what we found
    key_observations: List[str]

    # What we couldn't assess
    assessment_gaps: List[str]

    # Suggested interview focus areas
    interview_guidance: List[str]

    # Data completeness summary
    data_summary: str

    # Context-specific considerations
    context_notes: Dict[str, str] = field(default_factory=dict)


class EvidenceBasedInsightEngine:
    """
    Generates insights based on actual evidence without arbitrary scoring.

    Core principles:
    - Only state what we can observe
    - Acknowledge what we cannot determine
    - Provide context for interpretation
    - Suggest areas for further exploration
    """

    def __init__(self) -> None:
        """Initialize the evidence-based insight engine."""
        # Define what we fundamentally cannot assess from GitHub
        self.fundamental_limitations = [
            "Actual job performance and productivity",
            "Soft skills and interpersonal dynamics",
            "Problem-solving under pressure",
            "Learning speed and adaptability",
            "Team collaboration effectiveness",
            "Communication with stakeholders",
            "Domain knowledge depth",
            "Work quality consistency",
            "Initiative and leadership",
            "Cultural fit with specific teams",
        ]

        # Context-specific focus areas
        self.context_focus = {
            "startup": {
                "key_traits": ["adaptability", "self-direction", "versatility"],
                "important_questions": [
                    "Comfort with ambiguity and changing requirements",
                    "Experience with rapid iteration",
                    "Wearing multiple hats effectively",
                ],
            },
            "enterprise": {
                "key_traits": ["process adherence", "collaboration", "stability"],
                "important_questions": [
                    "Experience with formal development processes",
                    "Working in large, structured teams",
                    "Documentation and knowledge transfer practices",
                ],
            },
            "agency": {
                "key_traits": ["client focus", "versatility", "delivery"],
                "important_questions": [
                    "Managing multiple project contexts",
                    "Client communication experience",
                    "Balancing speed and quality",
                ],
            },
            "open_source": {
                "key_traits": [
                    "community engagement",
                    "transparency",
                    "sustainability",
                ],
                "important_questions": [
                    "Long-term commitment to projects",
                    "Community interaction style",
                    "Handling external contributions",
                ],
            },
        }

    def generate_insights(
        self,
        observations: Dict[str, List[Dict[str, Any]]],
        data_summary: Dict[str, Any],
        context: str = "general",
    ) -> InsightReport:
        """
        Generate insights from observations.

        Args:
            observations: Categorized observations from analysis
            data_summary: Summary of available data
            context: Hiring context (startup, enterprise, agency, open_source)

        Returns:
            Evidence-based insight report
        """
        insights = []

        # Process each category of observations
        if "technical" in observations:
            insights.extend(
                self._generate_technical_insights(observations["technical"], context)
            )

        if "behavioral" in observations:
            insights.extend(
                self._generate_behavioral_insights(
                    observations["behavioral"], context, data_summary
                )
            )

        if "collaboration" in observations:
            insights.extend(
                self._generate_collaboration_insights(
                    observations["collaboration"], context
                )
            )

        if "quality" in observations:
            insights.extend(
                self._generate_quality_insights(observations["quality"], context)
            )

        if "growth" in observations:
            insights.extend(
                self._generate_growth_insights(observations["growth"], context)
            )

        # Generate key observations
        key_observations = self._extract_key_observations(insights)

        # Identify assessment gaps
        assessment_gaps = self._identify_assessment_gaps(observations, data_summary)

        # Generate interview guidance
        interview_guidance = self._generate_interview_guidance(insights, context)

        # Create data summary
        data_summary_text = self._create_data_summary(data_summary)

        # Generate context notes
        context_notes = self._generate_context_notes(insights, context)

        return InsightReport(
            insights=insights,
            key_observations=key_observations,
            assessment_gaps=assessment_gaps,
            interview_guidance=interview_guidance,
            data_summary=data_summary_text,
            context_notes=context_notes,
        )

    def _generate_technical_insights(
        self, technical_obs: List[Dict[str, Any]], context: str
    ) -> List[EvidenceBasedInsight]:
        """Generate insights from technical observations."""
        insights = []

        # Language expertise
        lang_obs = [o for o in technical_obs if "language" in o.get("type", "")]
        if lang_obs:
            primary_langs = []
            for obs in lang_obs:
                if "primary" in obs.get("finding", "").lower():
                    primary_langs.append(obs["finding"])

            if primary_langs:
                insights.append(
                    EvidenceBasedInsight(
                        category="technical",
                        observation=f"Repository shows focus on {', '.join(primary_langs[:2])}",
                        evidence=primary_langs,
                        context="Language choice may indicate domain focus or team standards",
                        limitations=["Cannot assess proficiency level from code alone"],
                        interview_topics=[
                            "Experience with language-specific best practices",
                            "Reasons for technology choices",
                        ],
                        context_relevance={
                            "startup": "Consider if languages align with your tech stack",
                            "enterprise": "Evaluate fit with established technology standards",
                            "agency": "Assess versatility for varied client needs",
                            "open_source": "Check alignment with project ecosystem",
                        },
                    )
                )

        # Architecture patterns
        arch_obs = [o for o in technical_obs if "architecture" in o.get("type", "")]
        if arch_obs:
            insights.append(
                EvidenceBasedInsight(
                    category="technical",
                    observation="Code shows structured organization patterns",
                    evidence=[o["finding"] for o in arch_obs[:2]],
                    context="Structure suggests attention to maintainability",
                    limitations=["Cannot assess architectural decision rationale"],
                    interview_topics=[
                        "Approach to system design",
                        "Trade-offs in architectural decisions",
                    ],
                    context_relevance={
                        "startup": "May indicate ability to build scalable foundations",
                        "enterprise": "Suggests familiarity with structured development",
                        "agency": "Could help with project handoffs",
                        "open_source": "Facilitates community contributions",
                    },
                )
            )

        return insights

    def _generate_behavioral_insights(
        self,
        behavioral_obs: List[Dict[str, Any]],
        context: str,
        data_summary: Dict[str, Any],
    ) -> List[EvidenceBasedInsight]:
        """Generate insights from behavioral observations."""
        insights = []

        # Only generate if we have sufficient data
        commit_count = data_summary.get("total_commits", 0)
        if commit_count < 20:
            insights.append(
                EvidenceBasedInsight(
                    category="behavioral",
                    observation=f"Limited behavioral data available ({commit_count} commits)",
                    evidence=[f"Only {commit_count} commits to analyze"],
                    context="Insufficient data for meaningful behavioral patterns",
                    limitations=["Need more activity history for behavioral analysis"],
                    interview_topics=[
                        "Typical work patterns and habits",
                        "Approach to consistent contribution",
                    ],
                )
            )
            return insights

        # Work patterns
        work_pattern_obs = [
            o for o in behavioral_obs if "work_pattern" in o.get("category", "")
        ]
        if work_pattern_obs:
            for obs in work_pattern_obs[:1]:  # Take most relevant
                insights.append(
                    EvidenceBasedInsight(
                        category="behavioral",
                        observation=obs["observation"],
                        evidence=obs.get("evidence", []),
                        context=obs.get(
                            "data_context",
                            "Patterns vary by project and personal style",
                        ),
                        limitations=["Cannot determine motivations or constraints"],
                        interview_topics=obs.get(
                            "interview_topics",
                            ["Preferred working style", "Work-life balance approach"],
                        ),
                        context_relevance={
                            "startup": "Discuss expectations for availability and flexibility",
                            "enterprise": "Explore fit with team schedules and processes",
                            "agency": "Consider project deadline management",
                            "open_source": "Understand contribution sustainability",
                        },
                    )
                )

        return insights

    def _generate_collaboration_insights(
        self, collab_obs: List[Dict[str, Any]], context: str
    ) -> List[EvidenceBasedInsight]:
        """Generate insights from collaboration observations."""
        insights = []

        # Multi-contributor patterns
        multi_contrib = [
            o for o in collab_obs if "contributor" in o.get("observation", "").lower()
        ]
        if multi_contrib:
            contrib_count = 0
            for obs in multi_contrib:
                # Extract contributor count from observation
                import re

                numbers = re.findall(r"\d+", obs.get("observation", ""))
                if numbers:
                    contrib_count = int(numbers[0])
                    break

            if contrib_count > 1:
                insights.append(
                    EvidenceBasedInsight(
                        category="collaboration",
                        observation=f"Has worked in repository with {contrib_count} contributors",
                        evidence=[o["observation"] for o in multi_contrib[:1]],
                        context="Multi-contributor environment suggests team experience",
                        limitations=[
                            "Cannot assess quality of collaboration",
                            "PR/issue interactions not analyzed",
                        ],
                        interview_topics=[
                            "Team collaboration experiences",
                            "Conflict resolution approaches",
                            "Code review practices",
                        ],
                        context_relevance={
                            "startup": "May have experience in small team dynamics",
                            "enterprise": "Has exposure to multi-developer environments",
                            "agency": "Understands shared codebase practices",
                            "open_source": "Familiar with distributed collaboration",
                        },
                    )
                )
            else:
                insights.append(
                    EvidenceBasedInsight(
                        category="collaboration",
                        observation="Solo contributor in analyzed repository",
                        evidence=["Single author on all commits"],
                        context="Cannot assess team collaboration from this data",
                        limitations=["No team interaction data available"],
                        interview_topics=[
                            "Experience working in teams",
                            "Collaboration preferences and style",
                            "Handling code reviews and feedback",
                        ],
                    )
                )

        return insights

    def _generate_quality_insights(
        self, quality_obs: List[Dict[str, Any]], context: str
    ) -> List[EvidenceBasedInsight]:
        """Generate insights from code quality observations."""
        insights = []

        # Testing practices
        test_obs = [o for o in quality_obs if "test" in o.get("finding", "").lower()]
        if test_obs:
            has_tests = any("found" in o.get("finding", "").lower() for o in test_obs)

            if has_tests:
                insights.append(
                    EvidenceBasedInsight(
                        category="quality",
                        observation="Repository includes test files",
                        evidence=[o["finding"] for o in test_obs[:2]],
                        context="Presence of tests suggests quality awareness",
                        limitations=[
                            "Cannot assess test quality or coverage",
                            "Testing philosophy unknown",
                        ],
                        interview_topics=[
                            "Testing strategy and philosophy",
                            "Approach to test-driven development",
                            "Balancing test coverage with delivery speed",
                        ],
                        context_relevance={
                            "startup": "Consider approach to testing vs. speed",
                            "enterprise": "Evaluate alignment with quality standards",
                            "agency": "Discuss testing in client projects",
                            "open_source": "Important for project reliability",
                        },
                    )
                )
            else:
                insights.append(
                    EvidenceBasedInsight(
                        category="quality",
                        observation="No test files found in repository",
                        evidence=["Test directory not present"],
                        context="Testing practices not visible in this repository",
                        limitations=["Tests may exist elsewhere"],
                        interview_topics=[
                            "Approach to quality assurance",
                            "Experience with different testing strategies",
                            "Views on test importance",
                        ],
                    )
                )

        # Documentation
        doc_obs = [o for o in quality_obs if "documentation" in o.get("type", "")]
        if doc_obs:
            insights.append(
                EvidenceBasedInsight(
                    category="quality",
                    observation="Documentation present in repository",
                    evidence=[o["finding"] for o in doc_obs[:2]],
                    context="Documentation suggests communication awareness",
                    limitations=["Cannot assess documentation quality"],
                    interview_topics=[
                        "Documentation philosophy",
                        "Balancing documentation with development",
                    ],
                    context_relevance={
                        "startup": "Consider documentation in fast-paced environment",
                        "enterprise": "Important for knowledge transfer",
                        "agency": "Critical for client handoffs",
                        "open_source": "Essential for adoption",
                    },
                )
            )

        return insights

    def _generate_growth_insights(
        self, growth_obs: List[Dict[str, Any]], context: str
    ) -> List[EvidenceBasedInsight]:
        """Generate insights from growth/evolution observations."""
        insights = []

        # Technology evolution
        tech_evolution = [o for o in growth_obs if "evolution" in o.get("type", "")]
        if tech_evolution:
            insights.append(
                EvidenceBasedInsight(
                    category="growth",
                    observation="Repository shows technology exploration over time",
                    evidence=[o["finding"] for o in tech_evolution[:2]],
                    context="Multiple technologies suggest learning orientation",
                    limitations=["Cannot assess learning speed or depth"],
                    interview_topics=[
                        "Approach to learning new technologies",
                        "Balancing breadth vs. depth",
                    ],
                    context_relevance={
                        "startup": "May adapt well to changing tech needs",
                        "enterprise": "Consider depth in core technologies",
                        "agency": "Versatility valuable for varied projects",
                        "open_source": "Can contribute across ecosystems",
                    },
                )
            )

        return insights

    def _extract_key_observations(
        self, insights: List[EvidenceBasedInsight]
    ) -> List[str]:
        """Extract the most significant observations."""
        key_obs = []

        # Group by category and take most significant from each
        by_category: Dict[str, List[EvidenceBasedInsight]] = {}
        for insight in insights:
            if insight.category not in by_category:
                by_category[insight.category] = []
            by_category[insight.category].append(insight)

        # Take one from each category
        for category, category_insights in by_category.items():
            if category_insights:
                # Prefer insights with more evidence
                sorted_insights = sorted(
                    category_insights, key=lambda i: len(i.evidence), reverse=True
                )
                key_obs.append(sorted_insights[0].observation)

        return key_obs[:5]  # Limit to top 5

    def _identify_assessment_gaps(
        self,
        observations: Dict[str, List[Dict[str, Any]]],
        data_summary: Dict[str, Any],
    ) -> List[str]:
        """Identify what we couldn't assess."""
        gaps = []

        # Check data sufficiency
        if data_summary.get("total_commits", 0) < 10:
            gaps.append("Limited commit history prevents pattern analysis")

        if data_summary.get("unique_contributors", 0) <= 1:
            gaps.append("Single contributor - cannot assess team collaboration")

        if not data_summary.get("has_tests", False):
            gaps.append("No visible testing practices to evaluate")

        # Add fundamental limitations
        gaps.extend(self.fundamental_limitations[:3])

        return gaps

    def _generate_interview_guidance(
        self, insights: List[EvidenceBasedInsight], context: str
    ) -> List[str]:
        """Generate interview focus areas based on insights and context."""
        guidance = []

        # Collect all interview topics from insights
        all_topics = []
        for insight in insights:
            all_topics.extend(insight.interview_topics)

        # Remove duplicates while preserving order
        seen = set()
        unique_topics = []
        for topic in all_topics:
            if topic not in seen:
                seen.add(topic)
                unique_topics.append(topic)

        guidance.extend(unique_topics[:5])

        # Add context-specific questions
        if context in self.context_focus:
            guidance.extend(self.context_focus[context]["important_questions"][:2])

        # Always include fundamentals
        guidance.extend(
            [
                "Problem-solving approach and methodology",
                "Communication style and preferences",
            ]
        )

        return guidance[:10]  # Limit to 10 topics

    def _create_data_summary(self, data_summary: Dict[str, Any]) -> str:
        """Create a summary of available data."""
        parts = []

        commits = data_summary.get("total_commits", 0)
        contributors = data_summary.get("unique_contributors", 0)
        timespan = data_summary.get("timespan_days", 0)

        parts.append(f"{commits} commits")
        if contributors > 0:
            parts.append(f"{contributors} contributor{'s' if contributors > 1 else ''}")
        if timespan > 0:
            parts.append(f"over {timespan} days")

        languages = data_summary.get("languages", [])
        if languages:
            parts.append(f"{len(languages)} languages")

        summary = f"Analysis based on: {', '.join(parts)}"

        # Add data quality note
        if commits < 20:
            summary += ". Limited data may affect insight reliability."
        elif commits < 50:
            summary += ". Moderate data provides reasonable insights."
        else:
            summary += ". Substantial data enables comprehensive analysis."

        return summary

    def _generate_context_notes(
        self, insights: List[EvidenceBasedInsight], context: str
    ) -> Dict[str, str]:
        """Generate context-specific notes."""
        notes = {}

        if context == "startup":
            notes["focus"] = "Consider adaptability and self-direction indicators"
            notes["caution"] = "Repository may not reflect fast-paced startup reality"
        elif context == "enterprise":
            notes["focus"] = "Look for process adherence and collaboration signs"
            notes["caution"] = (
                "Open source practices may differ from enterprise standards"
            )
        elif context == "agency":
            notes["focus"] = "Evaluate versatility and project variety"
            notes["caution"] = "Client interaction skills not visible in code"
        elif context == "open_source":
            notes["focus"] = "Community engagement and sustainability"
            notes["caution"] = "Maintainer burden not apparent from contributions"
        else:
            notes["focus"] = "General technical capability assessment"
            notes["caution"] = "Context-specific skills need further evaluation"

        return notes
