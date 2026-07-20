# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Clean, flat API response models for predictable JSON structure.
Part of Operation "Data Contract Integrity".
"""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from github_analyzer.core.tier_utils import (
    get_next_frontend_tier,
    get_progressive_upgrade_message,
)


def _map_category_to_pattern_type(category: str) -> str:
    """Map insight category to evidence pattern type."""
    mapping = {
        "technical": "technical",
        "work_style": "behavioral",
        "collaboration": "behavioral",
        "context_fit": "technical",
    }
    return mapping.get(category, "technical")


def _join_evidence_list(evidence: List[str]) -> str:
    """Join evidence list into a single string with better formatting."""
    if isinstance(evidence, list):
        # Filter and clean evidence items
        clean_evidence = []
        for e in evidence:
            if e:
                e_str = str(e)
                # Clean up technical jargon
                e_str = e_str.replace(
                    "commits >500 lines", "large commits (500+ lines)"
                )
                e_str = e_str.replace("File structure depth:", "Folder nesting:")
                e_str = e_str.replace(" levels", " layers deep")
                # Clean up commit evidence that might come through
                e_str = e_str.replace("Found ", "Made ")
                e_str = e_str.replace(" commits with ", " commits, each with ")
                e_str = e_str.replace(
                    "large commits with 500+ lines of changes",
                    "substantial code changes (500+ lines each)",
                )
                clean_evidence.append(e_str)

        # Join with better formatting
        if len(clean_evidence) == 1:
            return clean_evidence[0]
        elif len(clean_evidence) == 2:
            return f"{clean_evidence[0]} and {clean_evidence[1]}"
        else:
            return ", ".join(clean_evidence[:-1]) + f", and {clean_evidence[-1]}"
    return str(evidence) if evidence else ""


def _ensure_string(value: Any, default: str = "") -> str:
    """Ensure a value is a string, handling dict cases where AI returns unexpected format."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        # AI sometimes returns {"startup": "value"} instead of just "value"
        # Try to extract the actual value
        if len(value) == 1:
            # Single key dict - return the value
            return str(list(value.values())[0])
        # Multiple keys - try common patterns
        for key in [
            "startup",
            "enterprise",
            "agency",
            "general",
            "value",
            "text",
            "description",
        ]:
            if key in value:
                return str(value[key])
        # Last resort - stringify the whole dict
        return str(value)
    if value is None:
        return default
    return str(value)


def _format_pattern_name(name: str) -> str:
    """Format pattern names to be consistent Title Case."""
    if not name:
        return "Pattern"

    # Replace underscores with spaces
    name = name.replace("_", " ")

    # Handle camelCase
    import re

    name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)

    # Title case each word
    words = name.split()
    formatted_words = []
    for word in words:
        # Keep certain words lowercase
        if word.lower() in ["of", "the", "in", "at", "to", "for", "and", "or", "with"]:
            formatted_words.append(word.lower())
        else:
            formatted_words.append(word.capitalize())

    # Capitalize first word regardless
    if formatted_words:
        formatted_words[0] = formatted_words[0].capitalize()

    return " ".join(formatted_words)


class InsightModel(BaseModel):
    """A single insight from the analysis."""

    category: str
    description: str
    evidence: List[str] = Field(default_factory=list)
    confidence: str = "medium"


class QuestionModel(BaseModel):
    """An interview question with context."""

    category: str
    question: str
    evidence_reference: str = ""
    follow_ups: List[str] = Field(default_factory=list)
    what_to_listen_for: str = ""
    context_relevance: str = ""


class RecommendationModel(BaseModel):
    """An evidence-based recommendation or action item."""

    type: str  # "strength", "concern", "neutral"
    text: str
    priority: str = "medium"
    evidence: Optional[str] = None


class EvidencePatternModel(BaseModel):
    """An evidence pattern extracted from the repository."""

    name: str
    pattern_type: str  # technical, behavioral, collaboration, quality
    evidence: str
    context: str
    insight: str
    category: str  # technical, professional, communication, growth

    # Tier-aware fields for Operation "Reinforce the Tiers"
    source_depth: str = "Surface"  # Surface/Architectural/Forensic/Maximum
    confidence: str = "Medium"  # Low/Medium/High based on data richness
    upgrade_hint: Optional[str] = None  # Hint for higher tier value
    tier_locked: bool = False  # True if pattern is locked for current tier
    required_tier: Optional[str] = None  # Required tier to unlock this pattern
    preview_teaser: Optional[str] = None  # Preview text for locked patterns


class CleanAnalysisResponse(BaseModel):
    """
    Clean, flat response structure for repository analysis.
    All fields are always present, using empty lists/None for missing data.
    Evidence-based approach with no numerical scores.
    """

    # Metadata - always present
    repository_url: str
    repository_name: str
    analysis_date: str  # ISO format string
    subscription_tier: str
    context: str  # hiring context

    # Summary - always present
    executive_summary: str
    repository_type: str
    confidence_explanation: str = ""  # Evidence quality explanation

    # Insights - empty list if none
    insights: List[InsightModel] = Field(default_factory=list)
    insights_count: int = 0

    # Questions - empty list if none (Professional/Enterprise only)
    questions: List[QuestionModel] = Field(default_factory=list)
    questions_count: int = 0

    # Recommendations - empty list if none
    recommendations: List[RecommendationModel] = Field(default_factory=list)
    recommendations_count: int = 0

    # Evidence Patterns - empty list if none (replaces metrics)
    evidence_patterns: List[EvidencePatternModel] = Field(default_factory=list)
    evidence_patterns_count: int = 0

    # Limitations - always present
    limitations: List[str] = Field(default_factory=list)
    data_limitations: List[str] = Field(default_factory=list)

    # Flags - empty lists if none
    green_flags: List[str] = Field(default_factory=list)
    red_flags: List[str] = Field(default_factory=list)

    # Areas to explore - empty list if none
    areas_to_explore: List[str] = Field(default_factory=list)

    # Cost tracking
    estimated_cost: float = 0.0

    def __init__(self, **data: Any) -> None:
        """Initialize and auto-calculate count fields."""
        super().__init__(**data)
        # Auto-calculate counts
        self.insights_count = len(self.insights)
        self.questions_count = len(self.questions)
        self.recommendations_count = len(self.recommendations)
        self.evidence_patterns_count = len(self.evidence_patterns)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "repository_url": "https://github.com/user/repo",
                "repository_name": "repo",
                "analysis_date": "2025-07-28T00:00:00Z",
                "subscription_tier": "professional",
                "context": "startup",
                "executive_summary": "Repository analysis shows strong TypeScript expertise and modern development practices with evidence of testing and collaboration.",
                "repository_type": "portfolio_project",
                "confidence_explanation": "High confidence based on comprehensive code analysis and commit history",
                "insights": [
                    {
                        "category": "technical_skills",
                        "description": "Strong TypeScript proficiency demonstrated",
                        "evidence": [
                            "89.5% TypeScript codebase",
                            "Advanced type patterns in 15 files",
                        ],
                        "confidence": "high",
                        "impact": "positive",
                    }
                ],
                "insights_count": 1,
                "questions": [
                    {
                        "category": "technical_decisions",
                        "question": "Your repository shows 89.5% TypeScript usage. Walk me through your approach to type safety in complex applications.",
                        "evidence_reference": "89.5% TypeScript codebase with advanced patterns",
                        "follow_ups": [
                            "How do you handle type complexity?",
                            "What's your approach to any types?",
                        ],
                        "what_to_listen_for": "Understanding of type system benefits and trade-offs",
                        "context_relevance": "Critical for startup's rapid development needs",
                    }
                ],
                "questions_count": 1,
                "recommendations": [
                    {
                        "type": "strength",
                        "text": "Strong TypeScript expertise with modern development practices",
                        "priority": "high",
                        "evidence": "89.5% TypeScript, testing infrastructure, active maintenance",
                    }
                ],
                "recommendations_count": 1,
                "evidence_patterns": [
                    {
                        "name": "language_expertise",
                        "pattern_type": "technical",
                        "evidence": "89.5% TypeScript across 343 files",
                        "context": "Modern web development expertise",
                        "insight": "Deep TypeScript experience in production code",
                        "category": "technical",
                    }
                ],
                "evidence_patterns_count": 1,
                "limitations": ["Cannot assess soft skills from code alone"],
                "data_limitations": [
                    "No access to code reviews",
                    "Cannot evaluate real-time problem solving",
                ],
                "green_flags": [
                    "Has testing infrastructure",
                    "Consistent commit patterns",
                ],
                "red_flags": [],
                "areas_to_explore": [
                    "How do you approach TypeScript adoption in legacy JavaScript codebases?",
                    "What's your strategy for maintaining type safety across microservices?",
                    "How do you balance development velocity with comprehensive testing?",
                ],
                "estimated_cost": 0.0034,
            }
        }
    )


def _deduplicate_and_limit_patterns(
    patterns: List[EvidencePatternModel], tier_config: dict[str, Any]
) -> List[EvidencePatternModel]:
    """
    Deduplicate evidence patterns and apply tier-based limits.
    Implements the "23 Patterns Paradox" fix by removing duplicates and phantom patterns.
    """
    if not patterns:
        return []

    # Deduplication by content similarity
    deduplicated = []
    seen_signatures = set()

    for pattern in patterns:
        # Create signature for deduplication (name + category + evidence snippet)
        evidence_snippet = pattern.evidence[:50] if pattern.evidence else ""
        signature = f"{pattern.name.lower()}:{pattern.category}:{evidence_snippet}"

        if signature not in seen_signatures:
            seen_signatures.add(signature)
            deduplicated.append(pattern)

    # Separate locked and unlocked patterns
    unlocked_patterns = [p for p in deduplicated if not p.tier_locked]
    locked_patterns = [p for p in deduplicated if p.tier_locked]

    # Apply tier limits to unlocked patterns
    max_patterns = tier_config["max_patterns"]

    # Prioritize patterns by evidence richness and specificity (evidence-based, not metric-based)
    def evidence_priority(pattern: EvidencePatternModel) -> int:
        evidence_length = len(pattern.evidence) if pattern.evidence else 0
        has_specific_data = (
            any(char.isdigit() for char in pattern.evidence)
            if pattern.evidence
            else False
        )
        has_detailed_context = len(pattern.context) > 50 if pattern.context else False

        # Evidence-based ranking: specificity and detail, not numerical scores
        priority_factors = [
            evidence_length,  # More detailed evidence = higher priority
            (
                100 if has_specific_data else 0
            ),  # Patterns with numbers/data = higher priority
            50 if has_detailed_context else 0,  # Rich context = higher priority
        ]
        return sum(priority_factors)

    unlocked_patterns.sort(key=evidence_priority, reverse=True)

    # Limit unlocked patterns to tier maximum
    limited_unlocked = unlocked_patterns[:max_patterns]

    # For basic/free tiers, show some locked patterns as previews
    if tier_config["depth"] in ["Surface"]:
        # Add up to 5 locked patterns as previews
        preview_locked = locked_patterns[:5]
        return limited_unlocked + preview_locked

    # Higher tiers get only unlocked patterns (no locked previews)
    return limited_unlocked


def _create_tier_aware_pattern(
    name: str,
    pattern_type: str,
    evidence: str,
    context: str,
    insight: str,
    category: str,
    tier_config: dict[str, Any],
    subscription_tier: str,
) -> Optional[EvidencePatternModel]:
    """
    Create a tier-aware evidence pattern with appropriate filtering and enhancements.
    Returns None if pattern should be filtered out for current tier.
    """

    # Determine if this pattern type is allowed for current tier
    allowed_sources = tier_config["sources"]

    # Map pattern categories to evidence sources
    CATEGORY_TO_SOURCE = {
        "technical": "basic_insights",
        "technical_skills": "basic_insights",
        "work_patterns": "surface_patterns",
        "collaboration": "team_dynamics",
        "professional": "architectural_analysis",
        "communication": "team_dynamics",
        "growth": "temporal_patterns",
        "security": "security_patterns",
        "quality": "architectural_analysis",
    }

    required_source = CATEGORY_TO_SOURCE.get(category, "basic_insights")

    # Filter out patterns that require sources not available to this tier
    if required_source not in allowed_sources:
        # For higher tiers, create locked preview patterns with progressive upgrade path
        if subscription_tier in ["free", "basic"]:
            # Get the next tier in progression, not jump to highest
            next_tier_backend = get_next_frontend_tier(subscription_tier)
            if subscription_tier == "free" and required_source in [
                "architectural_analysis",
                "temporal_patterns",
                "forensic_patterns",
            ]:
                # For free tier needing advanced features, suggest professional (Growth)
                next_tier_backend = "professional"
                next_tier_display = "Growth"
            elif (
                subscription_tier == "basic" and required_source == "forensic_patterns"
            ):
                # For basic tier needing forensic, suggest enterprise (Scale)
                next_tier_backend = "enterprise"
                next_tier_display = "Scale"
            else:
                # Progressive upgrade path
                next_tier_display = (
                    get_next_frontend_tier(subscription_tier) or "Starter"
                )
                next_tier_backend = (
                    "basic" if subscription_tier == "free" else "professional"
                )

            return EvidencePatternModel(
                name=name,
                pattern_type=pattern_type,
                evidence="🔒 Available in higher tiers",
                context=f"Upgrade to {next_tier_display} to see full analysis",
                insight=f"Advanced {category} insights available",
                category=category,
                source_depth="Locked",
                confidence="High",
                upgrade_hint=get_progressive_upgrade_message(
                    subscription_tier, category
                ),
                tier_locked=True,
                required_tier=next_tier_backend,
                preview_teaser=f"Found {category} patterns - unlock with {next_tier_display}",
            )
        return None  # Don't show locked patterns to professional+ users

    # Determine source depth and confidence based on tier
    source_depth = tier_config["depth"]
    base_confidence = tier_config["confidence_threshold"]

    # Enhance confidence based on evidence quality
    confidence = base_confidence
    if len(evidence) > 100 and subscription_tier in ["enterprise", "scale_plus"]:
        confidence = "High"
    elif len(evidence) > 50 and subscription_tier in [
        "professional",
        "enterprise",
        "scale_plus",
    ]:
        confidence = "Medium"

    # Generate upgrade hints for lower tiers
    upgrade_hint = None
    if subscription_tier == "free":
        upgrade_hint = "Starter tier adds detailed evidence analysis"
    elif subscription_tier == "basic":
        upgrade_hint = "Growth tier adds architectural patterns and timeline analysis"
    elif subscription_tier == "professional":
        upgrade_hint = "Scale tier adds team dynamics and security analysis"
    elif subscription_tier == "enterprise":
        upgrade_hint = (
            "Scale+ tier adds compliance analysis and cross-repository correlation"
        )

    return EvidencePatternModel(
        name=name,
        pattern_type=pattern_type,
        evidence=evidence,
        context=context,
        insight=insight,
        category=category,
        source_depth=source_depth,
        confidence=confidence,
        upgrade_hint=upgrade_hint,
        tier_locked=False,
        required_tier=None,
        preview_teaser=None,
    )


def convert_to_clean_response(
    structured_report: Any,  # StructuredReport from report_generator
    estimated_cost: float = 0.0,
    subscription_tier: str = "free",  # Backend tier: free, basic, professional, enterprise, scale_plus
) -> CleanAnalysisResponse:
    """
    Convert the complex StructuredReport to a clean, flat response.
    This is the adapter between our internal complexity and external simplicity.
    Implements tier-aware evidence extraction per Operation "Reinforce the Tiers".
    """

    # Tier configuration for evidence source filtering
    # Backend tiers: free, basic, professional, enterprise, scale_plus
    TIER_EVIDENCE_SOURCES = {
        "free": {
            "sources": ["basic_insights", "surface_patterns"],
            "depth": "Surface",
            "max_patterns": 8,
            "confidence_threshold": "Low",
        },
        "basic": {  # Frontend: starter
            "sources": ["basic_insights", "surface_patterns"],
            "depth": "Surface",
            "max_patterns": 12,  # Increased to allow more evidence patterns
            "confidence_threshold": "Low",
        },
        "professional": {  # Frontend: growth
            "sources": [
                "basic_insights",
                "surface_patterns",
                "architectural_analysis",
                "temporal_patterns",
            ],
            "depth": "Architectural",
            "max_patterns": 15,
            "confidence_threshold": "Medium",
        },
        "enterprise": {  # Frontend: scale
            "sources": [
                "basic_insights",
                "surface_patterns",
                "architectural_analysis",
                "temporal_patterns",
                "team_dynamics",
                "security_patterns",
            ],
            "depth": "Forensic",
            "max_patterns": 22,
            "confidence_threshold": "Medium",
        },
        "scale_plus": {  # Frontend: scale+
            "sources": [
                "basic_insights",
                "surface_patterns",
                "architectural_analysis",
                "temporal_patterns",
                "team_dynamics",
                "security_patterns",
                "compliance_analysis",
                "cross_repo_correlation",
            ],
            "depth": "Maximum",
            "max_patterns": 30,
            "confidence_threshold": "High",
        },
    }

    # Get tier configuration (default to free if unknown tier)
    tier_config = TIER_EVIDENCE_SOURCES.get(
        subscription_tier.lower(), TIER_EVIDENCE_SOURCES["free"]
    )

    # Extract insights
    insights = []
    if (
        hasattr(structured_report, "screening_insights")
        and structured_report.screening_insights
    ):
        if hasattr(structured_report.screening_insights, "insights"):
            for insight in structured_report.screening_insights.insights:
                # Handle both dict and object cases
                if isinstance(insight, dict):
                    insights.append(
                        InsightModel(
                            category=insight.get("category", "general"),
                            description=insight.get("description", ""),
                            evidence=insight.get("evidence", []),
                            confidence=insight.get("confidence", "medium"),
                        )
                    )
                else:
                    # It's an object (e.g., ScreeningInsight)
                    # Handle enum case - convert to string first
                    category = getattr(insight, "category", "general")
                    if hasattr(category, "value"):
                        category = category.value

                    # Handle evidence field which might be string or list
                    evidence_value = getattr(insight, "evidence", [])
                    if isinstance(evidence_value, str):
                        # Convert string to list with single item
                        evidence_value = [evidence_value] if evidence_value else []
                    elif not isinstance(evidence_value, list):
                        evidence_value = []

                    insights.append(
                        InsightModel(
                            category=str(category),
                            description=getattr(insight, "description", ""),
                            evidence=evidence_value,
                            confidence=getattr(insight, "confidence", "medium"),
                        )
                    )

    # Extract questions
    questions = []
    if (
        hasattr(structured_report, "interview_questions")
        and structured_report.interview_questions
    ):
        if isinstance(structured_report.interview_questions, dict):
            all_questions = structured_report.interview_questions.get(
                "all_questions", []
            )
            for q in all_questions:
                if isinstance(q, dict):
                    # Ensure what_to_listen_for is a string
                    listen_for = q.get("what_to_listen_for", "")
                    if isinstance(listen_for, list):
                        listen_for = ". ".join(listen_for) if listen_for else ""

                    questions.append(
                        QuestionModel(
                            category=q.get("category", "general"),
                            question=q.get("question", ""),
                            evidence_reference=q.get("evidence_reference", ""),
                            follow_ups=q.get("follow_ups", []),
                            what_to_listen_for=listen_for,
                            context_relevance=q.get("context_relevance", ""),
                        )
                    )

    # Extract recommendations
    recommendations = []

    # From evidence_based_recommendations
    if (
        hasattr(structured_report, "evidence_based_recommendations")
        and structured_report.evidence_based_recommendations
    ):
        if isinstance(structured_report.evidence_based_recommendations, dict):
            all_recs = structured_report.evidence_based_recommendations.get(
                "all_recommendations", []
            )
            for rec in all_recs:
                if isinstance(rec, dict):
                    recommendations.append(
                        RecommendationModel(
                            type=rec.get("type", "neutral"),
                            text=rec.get("recommendation", rec.get("text", "")) or "",
                            priority=rec.get("priority", "medium"),
                            evidence=rec.get("evidence", None),
                        )
                    )

    # Note: We no longer process hiring_recommendations as we've moved to evidence-based approach

    # Extract evidence patterns from various sources
    evidence_patterns = []

    # NOTE: We DO NOT extract patterns from questions anymore
    # Questions belong in the Questions tab, not Evidence tab
    # Evidence patterns should only come from actual evidence analysis

    # Extract from evidence_summary if available (though this may be empty with unified prompt)
    if (
        hasattr(structured_report, "evidence_summary")
        and structured_report.evidence_summary
    ):
        evidence_data = structured_report.evidence_summary

        # Technical patterns
        if "technical_patterns" in evidence_data:
            tech_patterns = evidence_data.get("technical_patterns", [])
            for pattern in tech_patterns:
                evidence_patterns.append(
                    EvidencePatternModel(
                        name=_format_pattern_name(pattern.get("type", "Unknown")),
                        pattern_type="technical",
                        evidence=_ensure_string(pattern.get("finding", "")),
                        context=_ensure_string(pattern.get("insight", "")),
                        insight=_ensure_string(pattern.get("insight", "")),
                        category="technical",
                    )
                )

        # Behavioral patterns
        if (
            "behavioral_analysis" in evidence_data
            and "behavioral_insights" in evidence_data["behavioral_analysis"]
        ):
            behavioral_insights = evidence_data["behavioral_analysis"][
                "behavioral_insights"
            ]
            for pattern in behavioral_insights:
                evidence_patterns.append(
                    EvidencePatternModel(
                        name=_format_pattern_name(pattern.get("type", "Unknown")),
                        pattern_type="behavioral",
                        evidence=_ensure_string(pattern.get("finding", "")),
                        context=_ensure_string(pattern.get("insight", "")),
                        insight=_ensure_string(pattern.get("insight", "")),
                        category="professional",
                    )
                )

    # Extract from section assessments if they have evidence
    for section_name, section_attr in [
        ("technical", "technical_assessment"),
        ("professional", "professional_practices"),
        ("communication", "communication_skills"),
        ("growth", "growth_indicators"),
    ]:
        if hasattr(structured_report, section_attr):
            section = getattr(structured_report, section_attr)
            if section and hasattr(section, "details") and section.details:
                # Convert details into evidence patterns
                for detail in section.details[:3]:  # Limit to top 3 per section
                    evidence_patterns.append(
                        EvidencePatternModel(
                            name=f"{section_name.title()} Pattern",
                            pattern_type=section_name,
                            evidence=detail,
                            context=f"Observable pattern in {section_name} practices",
                            insight=detail,
                            category=section_name,
                        )
                    )

    # CRITICAL FIX: Convert screening_insights.insights to evidence_patterns
    # This is the missing piece that was causing Evidence tab to be empty
    if (
        hasattr(structured_report, "screening_insights")
        and structured_report.screening_insights
        and hasattr(structured_report.screening_insights, "insights")
    ):
        insights_list = structured_report.screening_insights.insights
        for idx, insight in enumerate(insights_list):
            # Handle both dict and object cases
            if isinstance(insight, dict):
                # Use the title field if available, otherwise fall back to description
                name = insight.get("title", "")
                if not name:
                    # Fall back to creating name from category and description
                    name = insight.get("category", "Pattern").replace("_", " ").title()
                    description = insight.get("description", "")
                    if description:
                        # Take first few words of description for more specific name
                        name_parts = description.split()[:3]
                        if name_parts:
                            name = " ".join(name_parts).title()

                # Apply tier-aware evidence pattern creation
                pattern = _create_tier_aware_pattern(
                    name=name,
                    pattern_type=_map_category_to_pattern_type(
                        insight.get("category", "technical")
                    ),
                    evidence=_join_evidence_list(insight.get("evidence", [])),
                    context=_ensure_string(
                        insight.get("context_relevance", insight.get("description", ""))
                    ),
                    insight=_ensure_string(insight.get("description", "")),
                    category=insight.get("category", "technical"),
                    tier_config=tier_config,
                    subscription_tier=subscription_tier,
                )
                if pattern:  # Only add if pattern passes tier filtering
                    evidence_patterns.append(pattern)
            else:
                # Handle object case
                # Use the title attribute if available, otherwise fall back to description
                name = getattr(insight, "title", "")
                if not name:
                    # Fall back to creating name from category and description
                    category = getattr(insight, "category", "Pattern")
                    # Handle enum case - convert to string first
                    if hasattr(category, "value"):
                        category = category.value
                    name = str(category).replace("_", " ").title()
                    description = getattr(insight, "description", "")
                    if description:
                        # Take first few words of description for more specific name
                        name_parts = description.split()[:3]
                        if name_parts:
                            name = " ".join(name_parts).title()

                # Get category and convert from enum if needed
                cat_for_mapping = getattr(insight, "category", "technical")
                if hasattr(cat_for_mapping, "value"):
                    cat_for_mapping = cat_for_mapping.value

                # Apply tier-aware evidence pattern creation
                pattern = _create_tier_aware_pattern(
                    name=name,
                    pattern_type=_map_category_to_pattern_type(str(cat_for_mapping)),
                    evidence=_join_evidence_list(getattr(insight, "evidence", [])),
                    context=_ensure_string(
                        getattr(
                            insight,
                            "context_relevance",
                            getattr(insight, "description", ""),
                        )
                    ),
                    insight=_ensure_string(getattr(insight, "description", "")),
                    category=str(cat_for_mapping),
                    tier_config=tier_config,
                    subscription_tier=subscription_tier,
                )
                if pattern:  # Only add if pattern passes tier filtering
                    evidence_patterns.append(pattern)

    # Extract flags
    green_flags = []
    red_flags = []

    if hasattr(structured_report, "green_flags"):
        for flag in structured_report.green_flags:
            if hasattr(flag, "description"):
                green_flags.append(flag.description)
            else:
                green_flags.append(str(flag))

    if hasattr(structured_report, "red_flags"):
        for flag in structured_report.red_flags:
            if hasattr(flag, "description"):
                red_flags.append(flag.description)
            else:
                red_flags.append(str(flag))

    # Extract areas to explore
    areas_to_explore: List[str] = []
    if (
        hasattr(structured_report, "screening_insights")
        and structured_report.screening_insights
        and hasattr(structured_report.screening_insights, "areas_to_explore")
    ):
        areas_to_explore = structured_report.screening_insights.areas_to_explore or []

    # Extract confidence explanation
    confidence_explanation = ""
    if (
        hasattr(structured_report, "screening_insights")
        and structured_report.screening_insights
    ):
        confidence_explanation = getattr(
            structured_report.screening_insights, "confidence_explanation", ""
        )

    # Extract data limitations
    data_limitations: List[str] = []
    if (
        hasattr(structured_report, "screening_insights")
        and structured_report.screening_insights
    ):
        data_limitations = getattr(
            structured_report.screening_insights, "data_limitations", []
        )

    # Apply deduplication and tier-based pattern limiting
    evidence_patterns = _deduplicate_and_limit_patterns(evidence_patterns, tier_config)

    # Build clean response
    return CleanAnalysisResponse(
        repository_url=structured_report.repository_url,
        repository_name=structured_report.repository_name,
        analysis_date=(
            structured_report.analysis_date.isoformat()
            if isinstance(structured_report.analysis_date, datetime)
            else str(structured_report.analysis_date)
        ),
        subscription_tier=structured_report.subscription_tier or "free",
        context=(
            structured_report.context.value if structured_report.context else "general"
        ),
        executive_summary=structured_report.executive_summary or "",
        repository_type=(
            structured_report.repository_type.value
            if structured_report.repository_type
            else "unknown"
        ),
        confidence_explanation=confidence_explanation,
        insights=insights,
        insights_count=len(insights),
        questions=questions,
        questions_count=len(questions),
        recommendations=recommendations,
        recommendations_count=len(recommendations),
        evidence_patterns=evidence_patterns,
        evidence_patterns_count=len(evidence_patterns),
        limitations=structured_report.analysis_limitations or [],
        data_limitations=data_limitations,
        green_flags=green_flags,
        red_flags=red_flags,
        areas_to_explore=areas_to_explore,
        estimated_cost=estimated_cost,
    )
