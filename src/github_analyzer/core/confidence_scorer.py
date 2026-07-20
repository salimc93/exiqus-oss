# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Advanced confidence and risk assessment system for repository analysis.

This module provides granular confidence assessment, data completeness evaluation,
and risk indicator detection to build trust in analysis results.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from ..core.classifier import AnalysisMethod, ClassificationResult
from ..core.context_analyzer import ContextualAssessment
from ..data.models import RepositoryData
from ..utils.logging import get_logger

logger = get_logger(__name__)

__all__ = [
    "RiskLevel",
    "ConfidenceCategory",
    "RiskIndicator",
    "ConfidenceBreakdown",
    "ConfidenceResult",
    "ConfidenceRiskAssessor",
]


class RiskLevel(Enum):
    """Risk levels for different indicators."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    def __lt__(self, other: object) -> bool:
        """Enable comparison for sorting by severity order."""
        if isinstance(other, self.__class__):
            # Order by definition: LOW < MEDIUM < HIGH < CRITICAL
            members = list(self.__class__)
            return members.index(self) < members.index(other)
        return NotImplemented


class ConfidenceCategory(Enum):
    """Categories for confidence assessment."""

    DATA_AVAILABILITY = "data_availability"
    ANALYSIS_DEPTH = "analysis_depth"
    REPOSITORY_QUALITY = "repository_quality"
    TEMPORAL_RELIABILITY = "temporal_reliability"
    CONTEXTUAL_ACCURACY = "contextual_accuracy"


@dataclass(frozen=True)
class RiskIndicator:
    """Represents evidence patterns."""

    category: str  # "technical", "maintenance", "experience", "cultural"
    description: str
    risk_level: RiskLevel
    evidence: List[str] = field(default_factory=list)
    mitigation_suggestions: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ConfidenceBreakdown:
    """Evidence patterns breakdown."""

    confidence_explanation: str
    category_evidence: Dict[str, List[str]] = field(default_factory=dict)
    analysis_limitations: List[str] = field(default_factory=list)
    evidence_patterns: List[str] = field(default_factory=list)

    def get_confidence_level(self) -> str:
        """Get confidence level based on evidence patterns."""
        strong_patterns = len(
            [
                p
                for p in self.evidence_patterns
                if "strong" in p.lower() or "comprehensive" in p.lower()
            ]
        )
        total_patterns = len(self.evidence_patterns)

        if strong_patterns >= 4 or total_patterns >= 6:
            return "HIGH"
        elif strong_patterns >= 2 or total_patterns >= 3:
            return "MEDIUM"
        else:
            return "LOW"


@dataclass(frozen=True)
class ConfidenceResult:
    """Evidence patterns result."""

    confidence_breakdown: ConfidenceBreakdown
    risk_indicators: List[RiskIndicator]
    overall_risk_level: RiskLevel
    trust_explanation: str
    recommendations: List[str] = field(default_factory=list)


class ConfidenceRiskAssessor:
    """
    Advanced confidence and risk assessment system.

    Provides granular confidence assessment and risk indicator detection
    to help hiring teams understand the reliability of analysis results.
    """

    def __init__(self) -> None:
        """Initialize the confidence and risk assessor."""
        # Evidence pattern categories
        self.evidence_categories = [
            ConfidenceCategory.DATA_AVAILABILITY,
            ConfidenceCategory.ANALYSIS_DEPTH,
            ConfidenceCategory.REPOSITORY_QUALITY,
            ConfidenceCategory.TEMPORAL_RELIABILITY,
            ConfidenceCategory.CONTEXTUAL_ACCURACY,
        ]

    def assess_confidence_and_risk(
        self,
        repo_data: RepositoryData,
        classification: ClassificationResult,
        contextual_assessment: Optional[ContextualAssessment] = None,
    ) -> ConfidenceResult:
        """
        Generate comprehensive confidence and risk assessment.

        Args:
            repo_data: Repository data
            classification: Classification result
            contextual_assessment: Optional contextual assessment

        Returns:
            Complete assessment result with confidence and risk analysis
        """
        logger.info(
            f"Generating confidence and risk assessment for {repo_data.full_name}"
        )

        # Calculate confidence breakdown
        confidence_breakdown = self._calculate_confidence_breakdown(
            repo_data, classification, contextual_assessment
        )

        # Identify risk indicators
        risk_indicators = self._identify_risk_indicators(repo_data, classification)

        # Calculate overall risk level
        overall_risk_level = self._calculate_overall_risk_level(risk_indicators)

        # Determine trust level explanation
        trust_explanation = self._determine_trust_level(
            confidence_breakdown, risk_indicators
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            confidence_breakdown, risk_indicators, contextual_assessment
        )

        result = ConfidenceResult(
            confidence_breakdown=confidence_breakdown,
            risk_indicators=risk_indicators,
            overall_risk_level=overall_risk_level,
            trust_explanation=trust_explanation,
            recommendations=recommendations,
        )

        logger.info(
            "Evidence analysis complete: "
            f"{len(confidence_breakdown.evidence_patterns)} evidence patterns, "
            f"{len(risk_indicators)} risk indicators, "
            f"{overall_risk_level.value} risk level"
        )

        return result

    def _calculate_confidence_breakdown(
        self,
        repo_data: RepositoryData,
        classification: ClassificationResult,
        contextual_assessment: Optional[ContextualAssessment],
    ) -> ConfidenceBreakdown:
        """Calculate detailed confidence breakdown."""

        category_evidence = {}
        evidence_patterns = []
        limitations = []

        # 1. Data Availability Assessment
        data_evidence, data_limitations = self._assess_data_availability(repo_data)
        category_evidence[ConfidenceCategory.DATA_AVAILABILITY.value] = data_evidence
        evidence_patterns.extend(data_evidence)
        limitations.extend(data_limitations)

        # 2. Analysis Depth Assessment
        depth_evidence = self._assess_analysis_depth(
            repo_data, classification, contextual_assessment
        )
        category_evidence[ConfidenceCategory.ANALYSIS_DEPTH.value] = depth_evidence
        evidence_patterns.extend(depth_evidence)

        # 3. Repository Quality Assessment
        quality_evidence = self._assess_repository_quality(repo_data)
        category_evidence[ConfidenceCategory.REPOSITORY_QUALITY.value] = (
            quality_evidence
        )
        evidence_patterns.extend(quality_evidence)

        # 4. Temporal Reliability Assessment
        temporal_evidence, temporal_limitations = self._assess_temporal_reliability(
            repo_data
        )
        category_evidence[ConfidenceCategory.TEMPORAL_RELIABILITY.value] = (
            temporal_evidence
        )
        evidence_patterns.extend(temporal_evidence)
        limitations.extend(temporal_limitations)

        # 5. Contextual Accuracy Assessment
        contextual_evidence = self._assess_contextual_accuracy(
            repo_data, contextual_assessment
        )
        category_evidence[ConfidenceCategory.CONTEXTUAL_ACCURACY.value] = (
            contextual_evidence
        )
        evidence_patterns.extend(contextual_evidence)

        # Generate confidence explanation
        strong_patterns = len(
            [
                p
                for p in evidence_patterns
                if "strong" in p.lower() or "comprehensive" in p.lower()
            ]
        )
        total_patterns = len(evidence_patterns)

        if strong_patterns >= 4:
            confidence_explanation = f"High confidence based on {strong_patterns} strong evidence patterns from {total_patterns} total patterns"
        elif strong_patterns >= 2:
            confidence_explanation = f"Medium confidence based on {strong_patterns} strong evidence patterns from {total_patterns} total patterns"
        else:
            confidence_explanation = f"Low confidence with only {strong_patterns} strong evidence patterns from {total_patterns} total patterns"

        return ConfidenceBreakdown(
            confidence_explanation=confidence_explanation,
            category_evidence=category_evidence,
            analysis_limitations=limitations,
            evidence_patterns=evidence_patterns,
        )

    def _assess_data_availability(
        self, repo_data: RepositoryData
    ) -> Tuple[List[str], List[str]]:
        """Identify available data evidence patterns."""
        evidence = []
        limitations = []

        # README availability and quality
        if repo_data.has_readme and repo_data.readme_content:
            readme_length = len(repo_data.readme_content)
            if readme_length > 1500:
                evidence.append("Comprehensive README documentation available")
            elif readme_length > 500:
                evidence.append("Adequate README documentation present")
            else:
                evidence.append("Basic README documentation found")
                limitations.append(
                    "README is very brief - limited context for assessment"
                )
        else:
            limitations.append(
                "No README available - context assessment severely limited"
            )

        # File structure availability
        if len(repo_data.file_structure) > 10:
            evidence.append("Rich file structure with detailed organization")
        elif len(repo_data.file_structure) > 3:
            evidence.append("Basic file structure available")
        else:
            limitations.append(
                "Very limited file structure - architectural assessment impossible"
            )

        # Language information
        if len(repo_data.languages) > 0:
            evidence.append("Programming language data available")
            if len(repo_data.languages) > 2:
                evidence.append("Multi-language technology stack evident")
        else:
            limitations.append("No language information available")

        # Metrics availability
        metrics_available = 0
        if (
            repo_data.metrics
            and repo_data.metrics.total_commits
            and repo_data.metrics.total_commits > 0
        ):
            metrics_available += 1
        if (
            repo_data.metrics
            and repo_data.metrics.unique_contributors
            and repo_data.metrics.unique_contributors > 0
        ):
            metrics_available += 1
        if (
            repo_data.metrics
            and repo_data.metrics.lines_of_code
            and repo_data.metrics.lines_of_code > 0
        ):
            metrics_available += 1
        if (
            repo_data.metrics
            and hasattr(repo_data.metrics, "has_tests")
            and repo_data.metrics.has_tests
        ):
            metrics_available += 1

        if metrics_available >= 3:
            evidence.append("Comprehensive repository metrics available")
        elif metrics_available >= 2:
            evidence.append("Basic repository metrics present")
        else:
            limitations.append("Limited repository metrics available")

        # Community data
        if repo_data.stars > 0 or repo_data.forks > 0:
            evidence.append("Community engagement data available")

        return evidence, limitations

    def _assess_analysis_depth(
        self,
        repo_data: RepositoryData,
        classification: ClassificationResult,
        contextual_assessment: Optional[ContextualAssessment],
    ) -> List[str]:
        """Identify analysis depth evidence patterns."""
        evidence = []

        # Classification method evidence
        if classification.method is AnalysisMethod.AI:
            evidence.append("AI-powered analysis performed")
        else:
            evidence.append("Template-based analysis conducted")

        # Contextual analysis availability
        if contextual_assessment:
            evidence.append("Contextual analysis available")
            # Use evidence patterns instead of scores
            if (
                hasattr(contextual_assessment, "match_type")
                and contextual_assessment.match_type == "strong"
            ):
                evidence.append("Strong contextual fit assessment")

        # Repository type classification
        if classification.repository_type:
            evidence.append("Repository type classification completed")

        return evidence

    def _assess_repository_quality(self, repo_data: RepositoryData) -> List[str]:
        """Identify repository quality evidence patterns."""
        evidence = []

        # Professional practices
        if repo_data.has_tests:
            evidence.append("Testing infrastructure present")
            if (
                repo_data.metrics
                and hasattr(repo_data.metrics, "test_files_count")
                and repo_data.metrics.test_files_count
                and repo_data.metrics.test_files_count > 5
            ):
                evidence.append("Comprehensive test suite maintained")

        if repo_data.has_ci_config:
            evidence.append("Continuous integration configured")

        if repo_data.has_license:
            evidence.append("Open source license included")

        # Development activity
        if (
            repo_data.metrics
            and repo_data.metrics.total_commits
            and repo_data.metrics.total_commits > 20
        ):
            evidence.append("Substantial development history")

        if (
            repo_data.metrics
            and repo_data.metrics.unique_contributors
            and repo_data.metrics.unique_contributors > 1
        ):
            evidence.append("Collaborative development evident")

        # Code quality indicators
        if repo_data.size > 1000:  # >1MB
            evidence.append("Substantial codebase size")

        return evidence

    def _assess_temporal_reliability(
        self, repo_data: RepositoryData
    ) -> Tuple[List[str], List[str]]:
        """Identify temporal reliability evidence patterns."""
        evidence = []
        limitations = []

        # Recency of activity
        days_since_commit = (
            repo_data.metrics.days_since_last_commit
            if repo_data.metrics
            and repo_data.metrics.days_since_last_commit is not None
            else float("inf")
        )
        if days_since_commit <= 30:
            evidence.append("Recent development activity")
        elif days_since_commit <= 90:
            evidence.append("Moderately recent activity")
        elif days_since_commit <= 365:
            evidence.append("Some recent activity within past year")
            limitations.append("Repository has been inactive for several months")
        else:
            evidence.append("Stale repository with old activity")
            limitations.append(
                "Repository may be outdated - analysis reliability reduced"
            )

        # Development consistency
        commit_frequency = (
            repo_data.metrics.commit_frequency
            if repo_data.metrics and repo_data.metrics.commit_frequency is not None
            else 0
        )
        if commit_frequency > 1:
            evidence.append("Active development pattern")
        elif commit_frequency > 0.5:
            evidence.append("Moderate development activity")
        else:
            evidence.append("Infrequent commit pattern")
            limitations.append(
                "Low commit frequency reduces development pattern reliability"
            )

        # Project maturity
        total_commits = (
            repo_data.metrics.total_commits
            if repo_data.metrics and repo_data.metrics.total_commits
            else 0
        )
        if total_commits > 50:
            evidence.append("Mature project with substantial history")
        elif total_commits > 10:
            evidence.append("Developing project with growing history")
        else:
            limitations.append(
                "Very limited commit history - development patterns unclear"
            )

        return evidence, limitations

    def _assess_contextual_accuracy(
        self,
        repo_data: RepositoryData,
        contextual_assessment: Optional[ContextualAssessment],
    ) -> List[str]:
        """Identify contextual analysis evidence patterns."""
        evidence = []

        if contextual_assessment:
            # Use match type for contextual alignment
            if hasattr(contextual_assessment, "match_type"):
                if contextual_assessment.match_type == "strong":
                    evidence.append("Clear contextual match identified")
                elif contextual_assessment.match_type == "moderate":
                    evidence.append("Good contextual alignment found")
                elif contextual_assessment.match_type == "weak":
                    evidence.append("Poor contextual fit detected")
            else:
                evidence.append("Contextual assessment completed")

            # Number of insights indicates thorough analysis
            insight_count = len(contextual_assessment.strengths) + len(
                contextual_assessment.concerns
            )
            if insight_count > 5:
                evidence.append("Comprehensive contextual insights available")
            elif insight_count > 3:
                evidence.append("Adequate contextual insights provided")
        else:
            evidence.append("No contextual analysis performed")

        return evidence

    def _calculate_data_completeness(self, repo_data: RepositoryData) -> float:
        """Calculate data completeness as evidence count."""
        evidence_count = 0

        # Core data points (each counts as evidence)
        if repo_data.readme_content:
            evidence_count += 1
        if repo_data.has_tests:
            evidence_count += 1
        if len(repo_data.file_structure) > 5:
            evidence_count += 1
        if len(repo_data.languages) > 0:
            evidence_count += 1
        if (
            repo_data.metrics
            and repo_data.metrics.total_commits
            and repo_data.metrics.total_commits > 10
        ):
            evidence_count += 1
        if (
            repo_data.metrics
            and repo_data.metrics.lines_of_code
            and repo_data.metrics.lines_of_code > 0
        ):
            evidence_count += 1
        if repo_data.has_ci_config:
            evidence_count += 1
        if (
            repo_data.metrics
            and hasattr(repo_data.metrics, "has_tests")
            and repo_data.metrics.has_tests
        ):
            evidence_count += 1

        # No scoring - return 0
        return 0.0

    def _identify_risk_indicators(
        self, repo_data: RepositoryData, classification: ClassificationResult
    ) -> List[RiskIndicator]:
        """Identify potential hiring risks."""
        risks = []

        # Technical risks
        risks.extend(self._identify_technical_risks(repo_data))

        # Maintenance risks
        risks.extend(self._identify_maintenance_risks(repo_data))

        # Experience risks
        risks.extend(self._identify_experience_risks(repo_data))

        # Cultural risks
        risks.extend(self._identify_cultural_risks(repo_data))

        # Classification-specific risks
        risks.extend(self._identify_classification_risks(repo_data, classification))

        return sorted(risks, key=lambda r: r.risk_level.value)

    def _identify_technical_risks(
        self, repo_data: RepositoryData
    ) -> List[RiskIndicator]:
        """Identify technical skill risks."""
        risks = []

        # No testing practices
        if (
            not repo_data.has_tests
            and repo_data.metrics
            and repo_data.metrics.total_commits
            and repo_data.metrics.total_commits > 10
        ):
            total_commits = (
                repo_data.metrics.total_commits
                if repo_data.metrics and repo_data.metrics.total_commits
                else 0
            )
            risks.append(
                RiskIndicator(
                    category="technical",
                    description="No automated testing practices evident",
                    risk_level=RiskLevel.HIGH,
                    evidence=[
                        "No test files found",
                        f"{total_commits} commits without tests",
                    ],
                    mitigation_suggestions=[
                        "Assess testing philosophy in technical interview",
                        "Provide testing mentorship during onboarding",
                    ],
                )
            )

        # Minimal test coverage
        if (
            repo_data.has_tests
            and repo_data.metrics
            and hasattr(repo_data.metrics, "test_files_count")
            and repo_data.metrics.test_files_count is not None
            and repo_data.metrics.test_files_count < 2
        ):
            risks.append(
                RiskIndicator(
                    category="technical",
                    description="Minimal test coverage indicates limited testing",
                    risk_level=RiskLevel.MEDIUM,
                    evidence=[
                        f"Only {repo_data.metrics.test_files_count} test files found"
                    ],
                    mitigation_suggestions=["Evaluate quality over quantity of tests"],
                )
            )

        # Single language experience only
        if (
            len(repo_data.languages) == 1
            and repo_data.metrics
            and repo_data.metrics.total_commits
            and repo_data.metrics.total_commits > 20
        ):
            risks.append(
                RiskIndicator(
                    category="technical",
                    description=(
                        "Limited technology diversity may indicate narrow skill set"
                    ),
                    risk_level=RiskLevel.LOW,
                    evidence=[
                        f"Only {list(repo_data.languages.keys())[0]} experience visible"
                    ],
                    mitigation_suggestions=["Assess adaptability and learning ability"],
                )
            )

        return risks

    def _identify_maintenance_risks(
        self, repo_data: RepositoryData
    ) -> List[RiskIndicator]:
        """Identify project maintenance risks."""
        risks = []

        # Abandoned projects
        days_since_last = (
            repo_data.metrics.days_since_last_commit
            if repo_data.metrics
            and repo_data.metrics.days_since_last_commit is not None
            else 0
        )
        if days_since_last > 730:  # 2 years
            risks.append(
                RiskIndicator(
                    category="maintenance",
                    description="Repository appears abandoned",
                    risk_level=RiskLevel.CRITICAL,
                    evidence=[f"Last commit {days_since_last} days ago"],
                    mitigation_suggestions=[
                        "Request explanation for inactivity",
                        "Assess current technical engagement",
                    ],
                )
            )
        elif days_since_last > 365:  # 1 year
            risks.append(
                RiskIndicator(
                    category="maintenance",
                    description="Long period of inactivity raises maintenance concerns",
                    risk_level=RiskLevel.MEDIUM,
                    evidence=[f"Last commit {days_since_last} days ago"],
                    mitigation_suggestions=["Discuss current development practices"],
                )
            )

        # Very infrequent commits
        commit_freq = (
            repo_data.metrics.commit_frequency
            if repo_data.metrics and repo_data.metrics.commit_frequency is not None
            else 0
        )
        total_commits = (
            repo_data.metrics.total_commits
            if repo_data.metrics and repo_data.metrics.total_commits
            else 0
        )
        if commit_freq < 0.1 and total_commits > 10:
            risks.append(
                RiskIndicator(
                    category="maintenance",
                    description="Extremely low development velocity",
                    risk_level=RiskLevel.MEDIUM,
                    evidence=[f"Average {commit_freq:.1f} commits per week"],
                    mitigation_suggestions=[
                        "Assess development workflow and consistency"
                    ],
                )
            )

        return risks

    def _identify_experience_risks(
        self, repo_data: RepositoryData
    ) -> List[RiskIndicator]:
        """Identify experience-related risks."""
        risks = []

        # Very limited experience
        total_commits = (
            repo_data.metrics.total_commits
            if repo_data.metrics and repo_data.metrics.total_commits
            else 0
        )
        if total_commits < 5:
            risks.append(
                RiskIndicator(
                    category="experience",
                    description="Very limited development history",
                    risk_level=RiskLevel.HIGH,
                    evidence=[f"Only {total_commits} commits total"],
                    mitigation_suggestions=[
                        "Request additional portfolio evidence",
                        "Focus on fundamentals in technical assessment",
                    ],
                )
            )

        # No collaboration experience
        unique_contributors = (
            repo_data.metrics.unique_contributors
            if repo_data.metrics and repo_data.metrics.unique_contributors is not None
            else 1
        )
        total_commits = (
            repo_data.metrics.total_commits
            if repo_data.metrics and repo_data.metrics.total_commits
            else 0
        )
        if unique_contributors == 1 and total_commits > 50:
            risks.append(
                RiskIndicator(
                    category="experience",
                    description="No visible collaboration experience",
                    risk_level=RiskLevel.MEDIUM,
                    evidence=["Solo contributor on all visible projects"],
                    mitigation_suggestions=[
                        "Assess teamwork and communication skills",
                        "Evaluate code review experience",
                    ],
                )
            )

        return risks

    def _identify_cultural_risks(
        self, repo_data: RepositoryData
    ) -> List[RiskIndicator]:
        """Identify cultural fit risks."""
        risks = []

        # Poor documentation practices
        total_commits = (
            repo_data.metrics.total_commits
            if repo_data.metrics and repo_data.metrics.total_commits
            else 0
        )
        if not repo_data.has_readme and total_commits > 10:
            risks.append(
                RiskIndicator(
                    category="cultural",
                    description=(
                        "Poor documentation practices may indicate communication issues"
                    ),
                    risk_level=RiskLevel.MEDIUM,
                    evidence=["No README documentation"],
                    mitigation_suggestions=[
                        "Assess communication skills and documentation attitude"
                    ],
                )
            )

        # No open source engagement
        if repo_data.stars == 0 and repo_data.forks == 0 and not repo_data.has_license:
            risks.append(
                RiskIndicator(
                    category="cultural",
                    description="Limited open source community engagement",
                    risk_level=RiskLevel.LOW,
                    evidence=["No community interaction visible"],
                    mitigation_suggestions=["Evaluate interest in knowledge sharing"],
                )
            )

        return risks

    def _identify_classification_risks(
        self, repo_data: RepositoryData, classification: ClassificationResult
    ) -> List[RiskIndicator]:
        """Identify risks based on classification results."""
        risks = []

        # Removed classification confidence check since confidence field was removed

        # Template-only analysis for complex project
        total_commits = (
            repo_data.metrics.total_commits
            if repo_data.metrics and repo_data.metrics.total_commits
            else 0
        )
        if (
            classification.method is AnalysisMethod.TEMPLATE
            and repo_data.size > 1000
            and total_commits > 20
        ):
            risks.append(
                RiskIndicator(
                    category="analysis",
                    description="Complex project received simplified analysis",
                    risk_level=RiskLevel.LOW,
                    evidence=["Template analysis used for substantial project"],
                    mitigation_suggestions=["Consider deeper technical evaluation"],
                )
            )

        return risks

    def _calculate_overall_risk_level(
        self, risk_indicators: List[RiskIndicator]
    ) -> RiskLevel:
        """Determine risk level based on evidence patterns."""
        if not risk_indicators:
            return RiskLevel.LOW

        # Check for critical risks
        critical_risks = [
            r for r in risk_indicators if r.risk_level == RiskLevel.CRITICAL
        ]
        if critical_risks:
            return RiskLevel.CRITICAL

        # Check for high risks
        high_risks = [r for r in risk_indicators if r.risk_level == RiskLevel.HIGH]
        if high_risks:
            return RiskLevel.HIGH

        # Check for medium risks
        medium_risks = [r for r in risk_indicators if r.risk_level == RiskLevel.MEDIUM]
        if medium_risks:
            return RiskLevel.MEDIUM

        return RiskLevel.LOW

    def _determine_trust_level(
        self, confidence: ConfidenceBreakdown, risks: List[RiskIndicator]
    ) -> str:
        """Generate trust explanation based on evidence patterns and risk indicators."""
        evidence_count = len(confidence.evidence_patterns)
        risk_count = len(risks)

        # Generate explanation based on evidence and risk patterns
        if evidence_count >= 5 and risk_count <= 1:
            return f"High trust level with {evidence_count} evidence patterns and minimal risk indicators"
        elif evidence_count >= 3 and risk_count <= 2:
            return f"Moderate trust level with {evidence_count} evidence patterns and {risk_count} risk indicators"
        else:
            return f"Limited trust level with only {evidence_count} evidence patterns and {risk_count} risk indicators"

    def _generate_recommendations(
        self,
        confidence: ConfidenceBreakdown,
        risks: List[RiskIndicator],
        contextual_assessment: Optional[ContextualAssessment],
    ) -> List[str]:
        """Generate recommendations based on confidence and risk analysis."""
        recommendations = []

        # Evidence-based recommendations
        if len(confidence.analysis_limitations) > 3:
            recommendations.append(
                "Request additional portfolio evidence for more reliable assessment"
            )

        if len(confidence.evidence_patterns) < 3:
            recommendations.append(
                "Gather more repository information for comprehensive analysis"
            )

        # Risk-based recommendations
        high_risks = [
            r for r in risks if r.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        ]
        if high_risks:
            recommendations.append("Address critical risk indicators before proceeding")
            for risk in high_risks[:2]:  # Top 2
                recommendations.extend(risk.mitigation_suggestions)

        # Context-specific recommendations
        # Evidence-based recommendation

        # Limit to top 5 recommendations
        return recommendations[:5]
