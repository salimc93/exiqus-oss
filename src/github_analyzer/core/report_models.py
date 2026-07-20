# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Data models for repository analysis reports.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .classifier import RepositoryType
from .context_analyzer import AnalysisContext
from .evidence.insight_engine import ScreeningReport


class ReportFormat(Enum):
    """Available report output formats."""

    JSON = "json"
    HTML = "html"
    MARKDOWN = "markdown"
    PDF_READY = "pdf_ready"
    USER_FRIENDLY = (
        "user_friendly"  # Easy-to-read format for technical evaluation teams
    )


class ConfidenceLevel(Enum):
    """Confidence levels for different assessment areas."""

    HIGH = "high"  # 80-100%
    MEDIUM = "medium"  # 50-79%
    LOW = "low"  # 0-49%


@dataclass
class Flag:
    """Represents a red or green flag in the analysis."""

    type: str  # "red" or "green"
    category: str  # "technical", "professional", "communication", etc.
    description: str
    severity: str  # "critical", "moderate", "minor"
    evidence: List[str] = field(default_factory=list)


@dataclass
class SubMetric:
    """Represents evidence patterns without numerical scores (Great Purge compliant)."""

    name: str  # Evidence pattern name (e.g., "Version Control Practices")
    evidence: str  # Specific examples from the repository
    context: str  # Why this matters for analysis
    insight: str  # What this reveals about the developer (2-3 sentences)


@dataclass
class SectionAssessment:
    """Assessment for a specific section with evidence-based patterns."""

    title: str
    confidence: ConfidenceLevel
    summary: str
    evidence_patterns: List[str] = field(
        default_factory=list
    )  # Key evidence patterns found
    details: List[str] = field(default_factory=list)
    flags: List[Flag] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    sub_metrics: List[SubMetric] = field(default_factory=list)  # Evidence patterns only


@dataclass
class EnhancedSubMetric(SubMetric):
    """Extended sub-metric with confidence data."""

    confidence_range: Tuple[int, int] = (60, 80)
    interview_prompt: Optional[str] = None
    metric_type: str = "technical"


@dataclass
class StructuredReport:
    """Complete structured report for repository analysis."""

    # Metadata
    repository_url: str
    repository_name: str
    analysis_date: datetime
    report_version: str = "1.0"

    # Executive Summary
    executive_summary: str = ""
    screening_insights: Optional[ScreeningReport] = None  # Evidence-based insights
    # confidence_score removed - evidence-based approach (Great Purge)
    confidence_explanation: str = ""  # Evidence-based confidence explanation

    # Context Analysis
    context: Optional[AnalysisContext] = None
    repository_type: Optional[RepositoryType] = None

    # Section Assessments
    technical_assessment: Optional[SectionAssessment] = None
    professional_practices: Optional[SectionAssessment] = None
    communication_skills: Optional[SectionAssessment] = None
    growth_indicators: Optional[SectionAssessment] = None

    # Key Insights
    key_strengths: List[str] = field(default_factory=list)
    primary_concerns: List[str] = field(default_factory=list)
    red_flags: List[Flag] = field(default_factory=list)
    green_flags: List[Flag] = field(default_factory=list)

    # Recommendations
    analysis_recommendations: List[str] = field(
        default_factory=list
    )  # Renamed from hiring_recommendations
    interview_focus_areas: List[str] = field(default_factory=list)

    # Evidence-Based Features (NEW)
    evidence_summary: Optional[Dict[str, Any]] = None
    evidence_based_recommendations: Optional[Dict[str, Any]] = None
    interview_questions: Optional[Dict[str, Any]] = None
    subscription_tier: Optional[str] = None

    # Analysis Metadata
    data_completeness: float = 0.0  # 0.0 to 1.0
    analysis_limitations: List[str] = field(default_factory=list)
    risk_indicators: List[str] = field(default_factory=list)

    # Evidence-Based Assessment (Great Purge: no scores)
    confidence_grade: str = ""  # A+, A, B+, B, C+, C, D - based on evidence patterns
    overall_risk_level: str = (
        ""  # low, medium, high, critical - based on evidence patterns
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary for serialization - evidence-based approach without scores."""
        return {
            "metadata": {
                "repository_url": self.repository_url,
                "repository_name": self.repository_name,
                "analysis_date": self.analysis_date.isoformat(),
                "report_version": self.report_version,
            },
            "executive_summary": {
                "summary": self.executive_summary,
                # No recommendation or confidence_score - using evidence-based approach
            },
            "screening_insights": (
                self.screening_insights.to_dict() if self.screening_insights else None
            ),
            "context_analysis": {
                "context": self.context.value if self.context else None,
                # Evidence-based approach - no numerical scores
                "repository_type": (
                    self.repository_type.value if self.repository_type else None
                ),
            },
            "section_assessments": {
                "technical": self._section_to_dict(self.technical_assessment),
                "professional": self._section_to_dict(self.professional_practices),
                "communication": self._section_to_dict(self.communication_skills),
                "growth": self._section_to_dict(self.growth_indicators),
            },
            "key_insights": {
                "strengths": self.key_strengths,
                "concerns": self.primary_concerns,
                "red_flags": [self._flag_to_dict(f) for f in self.red_flags],
                "green_flags": [self._flag_to_dict(f) for f in self.green_flags],
            },
            "recommendations": {
                "recommendations": self.analysis_recommendations,
                "interview_focus": self.interview_focus_areas,
            },
            "evidence_based_features": {
                "subscription_tier": self.subscription_tier,
                "evidence_summary": (
                    self.evidence_summary if self.subscription_tier != "free" else None
                ),
                "evidence_based_recommendations": (
                    self.evidence_based_recommendations
                    if self.subscription_tier in ["professional", "enterprise"]
                    else None
                ),
                "interview_questions": (
                    self.interview_questions
                    if self.subscription_tier in ["professional", "enterprise"]
                    else None
                ),
            },
            "analysis_quality": {
                "limitations": self.analysis_limitations,
                "confidence_explanation": (
                    self.screening_insights.confidence_explanation
                    if self.screening_insights
                    else "No analysis performed"
                ),
            },
        }

    def _section_to_dict(
        self, section: Optional[SectionAssessment]
    ) -> Optional[Dict[str, Any]]:
        """Convert section assessment to dictionary."""
        if not section:
            return None

        # Evidence-based approach - no scores
        return {
            "title": section.title,
            "confidence": section.confidence.value,
            "summary": section.summary,
            "details": section.details,
            "flags": [self._flag_to_dict(f) for f in section.flags],
            "limitations": section.limitations,
            "sub_metrics": [self._sub_metric_to_dict(sm) for sm in section.sub_metrics],
            # No score field - evidence-based approach
        }

    def _flag_to_dict(self, flag: Flag) -> Dict[str, Any]:
        """Convert flag to dictionary."""
        return {
            "type": flag.type,
            "category": flag.category,
            "description": flag.description,
            "severity": flag.severity,
            "evidence": flag.evidence,
        }

    def _sub_metric_to_dict(self, sub_metric: SubMetric) -> Dict[str, Any]:
        """Convert sub-metric to dictionary - evidence-based approach without scores."""
        return {
            "name": sub_metric.name,
            "evidence": sub_metric.evidence,
            "context": sub_metric.context,
            "insight": sub_metric.insight,
            # No score, percentage, or confidence_display - evidence-based
        }
