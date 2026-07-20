# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Evidence-based confidence scoring that reflects actual uncertainty.

This module provides transparent confidence assessment based on data availability
and analysis limitations without arbitrary thresholds.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from ...data.models import RepositoryData
from ...utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DataAvailability:
    """What data we have available for analysis."""

    has_readme: bool
    readme_length: Optional[int]
    file_count: int
    language_count: int
    commit_count: int
    contributor_count: int
    has_tests: bool
    has_ci: bool
    has_license: bool
    days_of_history: Optional[int]
    total_lines: Optional[int]

    def describe(self) -> str:
        """Human-readable description of available data."""
        parts = []

        if self.commit_count > 0:
            parts.append(f"{self.commit_count} commits")
        if self.contributor_count > 0:
            parts.append(f"{self.contributor_count} contributors")
        if self.file_count > 0:
            parts.append(f"{self.file_count} files")
        if self.language_count > 0:
            parts.append(f"{self.language_count} languages")

        return ", ".join(parts) if parts else "Minimal data available"


@dataclass
class AnalysisLimitations:
    """Known limitations of the analysis."""

    structural: List[str] = field(default_factory=list)  # Missing data
    temporal: List[str] = field(default_factory=list)  # Time-related
    contextual: List[str] = field(default_factory=list)  # Context gaps
    behavioral: List[str] = field(default_factory=list)  # Human factors

    def all_limitations(self) -> List[str]:
        """Get all limitations as a flat list."""
        return self.structural + self.temporal + self.contextual + self.behavioral


@dataclass
class UncertaintyFactors:
    """Factors contributing to uncertainty in analysis."""

    missing_critical_data: List[str] = field(default_factory=list)
    partial_visibility: List[str] = field(default_factory=list)
    inference_required: List[str] = field(default_factory=list)
    external_factors: List[str] = field(default_factory=list)


@dataclass
class EvidenceBasedConfidence:
    """Confidence assessment based on evidence and limitations."""

    data_availability: DataAvailability
    limitations: AnalysisLimitations
    uncertainty: UncertaintyFactors

    # Qualitative assessments
    data_sufficiency: str  # "comprehensive", "adequate", "limited", "minimal"
    analysis_depth: str  # "detailed", "standard", "basic", "surface"
    reliability_notes: List[str] = field(default_factory=list)

    # Specific concerns
    critical_gaps: List[str] = field(default_factory=list)
    assumptions_made: List[str] = field(default_factory=list)

    def summary(self) -> str:
        """Generate a human-readable confidence summary."""
        parts = []

        parts.append(f"Analysis based on {self.data_availability.describe()}")
        parts.append(f"Data sufficiency: {self.data_sufficiency}")
        parts.append(f"Analysis depth: {self.analysis_depth}")

        if self.critical_gaps:
            parts.append(f"Critical gaps: {len(self.critical_gaps)}")

        limitation_count = len(self.limitations.all_limitations())
        if limitation_count > 0:
            parts.append(f"Known limitations: {limitation_count}")

        return " | ".join(parts)


class EvidenceBasedConfidenceScorer:
    """
    Assesses confidence based on actual data availability and known limitations.

    No arbitrary scores or thresholds - just transparent assessment of what
    we know and what we don't know.
    """

    def assess_confidence(self, repo_data: RepositoryData) -> EvidenceBasedConfidence:
        """
        Assess confidence based on available evidence.

        Args:
            repo_data: Repository data

        Returns:
            Evidence-based confidence assessment
        """
        logger.info(f"Assessing confidence for {repo_data.full_name}")

        # Assess what data we have
        data_availability = self._assess_data_availability(repo_data)

        # Identify limitations
        limitations = self._identify_limitations(repo_data, data_availability)

        # Assess uncertainty factors
        uncertainty = self._assess_uncertainty(repo_data, data_availability)

        # Determine sufficiency levels
        data_sufficiency = self._determine_data_sufficiency(data_availability)
        analysis_depth = self._determine_analysis_depth(data_availability)

        # Identify critical gaps
        critical_gaps = self._identify_critical_gaps(repo_data, data_availability)

        # Note assumptions
        assumptions = self._note_assumptions(repo_data, data_availability)

        # Generate reliability notes
        reliability_notes = self._generate_reliability_notes(
            data_availability, limitations, uncertainty
        )

        return EvidenceBasedConfidence(
            data_availability=data_availability,
            limitations=limitations,
            uncertainty=uncertainty,
            data_sufficiency=data_sufficiency,
            analysis_depth=analysis_depth,
            reliability_notes=reliability_notes,
            critical_gaps=critical_gaps,
            assumptions_made=assumptions,
        )

    def _assess_data_availability(self, repo_data: RepositoryData) -> DataAvailability:
        """Assess what data is available."""
        # Calculate days of history
        days_of_history = None
        if repo_data.recent_commits and len(repo_data.recent_commits) >= 2:
            oldest = min(c.date for c in repo_data.recent_commits)
            newest = max(c.date for c in repo_data.recent_commits)
            days_of_history = (newest - oldest).days

        return DataAvailability(
            has_readme=repo_data.has_readme,
            readme_length=(
                len(repo_data.readme_content) if repo_data.readme_content else None
            ),
            file_count=len(repo_data.file_structure),
            language_count=len(repo_data.languages),
            commit_count=repo_data.metrics.total_commits if repo_data.metrics else 0,
            contributor_count=(
                repo_data.metrics.unique_contributors if repo_data.metrics else 0
            ),
            has_tests=repo_data.has_tests,
            has_ci=repo_data.has_ci_config,
            has_license=repo_data.has_license,
            days_of_history=days_of_history,
            total_lines=repo_data.metrics.lines_of_code if repo_data.metrics else None,
        )

    def _identify_limitations(
        self, repo_data: RepositoryData, data_availability: DataAvailability
    ) -> AnalysisLimitations:
        """Identify analysis limitations based on missing or incomplete data."""
        limitations = AnalysisLimitations()

        # Structural limitations
        if not data_availability.has_readme:
            limitations.structural.append(
                "No README - project context and goals unclear"
            )
        elif data_availability.readme_length and data_availability.readme_length < 200:
            limitations.structural.append("Minimal README - limited project context")

        if data_availability.file_count < 5:
            limitations.structural.append(
                "Very few files - cannot assess code organization"
            )

        if not data_availability.has_tests:
            limitations.structural.append("No tests found - quality practices unknown")

        if data_availability.total_lines is None:
            limitations.structural.append(
                "Code volume unknown - cannot assess project scale"
            )

        # Temporal limitations
        if data_availability.commit_count < 5:
            limitations.temporal.append(
                "Minimal commit history - development patterns unclear"
            )

        if data_availability.days_of_history is not None:
            if data_availability.days_of_history < 7:
                limitations.temporal.append(
                    "Very recent history - long-term patterns unknown"
                )
            elif data_availability.days_of_history > 730:  # 2 years
                limitations.temporal.append(
                    "Old repository - current skills may differ"
                )

        days_since_last = (
            repo_data.metrics.days_since_last_commit if repo_data.metrics else None
        )
        if days_since_last and days_since_last > 180:
            limitations.temporal.append("Repository inactive for 6+ months")

        # Contextual limitations
        if not repo_data.description:
            limitations.contextual.append("No repository description")

        if data_availability.contributor_count <= 1:
            limitations.contextual.append(
                "Single contributor - collaboration style unknown"
            )

        # Behavioral limitations (always present)
        limitations.behavioral.extend(
            [
                "Cannot assess soft skills from code alone",
                "Work environment context missing",
                "Communication style partially visible through commits",
                "Problem-solving approach inferred from code patterns",
            ]
        )

        return limitations

    def _assess_uncertainty(
        self, repo_data: RepositoryData, data_availability: DataAvailability
    ) -> UncertaintyFactors:
        """Assess factors contributing to uncertainty."""
        uncertainty = UncertaintyFactors()

        # Missing critical data
        if not data_availability.has_readme:
            uncertainty.missing_critical_data.append("Project documentation")
        if data_availability.commit_count < 10:
            uncertainty.missing_critical_data.append("Sufficient development history")
        if not data_availability.has_tests:
            uncertainty.missing_critical_data.append("Testing practices")

        # Partial visibility
        uncertainty.partial_visibility.extend(
            [
                "Only public repositories visible",
                "No access to code review discussions",
                "Pull request history not analyzed",
                "Issue tracking data not included",
            ]
        )

        # Inference required
        if data_availability.language_count > 3:
            uncertainty.inference_required.append(
                "Primary expertise among multiple languages"
            )
        if data_availability.contributor_count > 5:
            uncertainty.inference_required.append(
                "Individual contribution in team context"
            )

        # External factors
        uncertainty.external_factors.extend(
            [
                "Professional vs personal project unknown",
                "Time constraints and deadlines unknown",
                "Team dynamics and processes unknown",
            ]
        )

        return uncertainty

    def _determine_data_sufficiency(self, data_availability: DataAvailability) -> str:
        """Determine qualitative data sufficiency level."""
        # Count significant data points
        significant_points = 0

        if (
            data_availability.has_readme
            and data_availability.readme_length
            and data_availability.readme_length > 500
        ):
            significant_points += 2
        elif data_availability.has_readme:
            significant_points += 1

        if data_availability.commit_count >= 50:
            significant_points += 2
        elif data_availability.commit_count >= 10:
            significant_points += 1

        if data_availability.file_count >= 20:
            significant_points += 2
        elif data_availability.file_count >= 5:
            significant_points += 1

        if data_availability.has_tests:
            significant_points += 2

        if data_availability.has_ci:
            significant_points += 1

        if data_availability.language_count >= 2:
            significant_points += 1

        if data_availability.contributor_count >= 2:
            significant_points += 1

        # Determine level
        if significant_points >= 8:
            return "comprehensive"
        elif significant_points >= 5:
            return "adequate"
        elif significant_points >= 2:
            return "limited"
        else:
            return "minimal"

    def _determine_analysis_depth(self, data_availability: DataAvailability) -> str:
        """Determine how deep our analysis can go."""
        if data_availability.commit_count >= 50 and data_availability.file_count >= 20:
            if data_availability.has_tests and data_availability.has_readme:
                return "detailed"
            else:
                return "standard"
        elif data_availability.commit_count >= 10:
            return "basic"
        else:
            return "surface"

    def _identify_critical_gaps(
        self, repo_data: RepositoryData, data_availability: DataAvailability
    ) -> List[str]:
        """Identify critical gaps that significantly impact analysis."""
        gaps = []

        if not data_availability.has_readme and data_availability.commit_count > 10:
            gaps.append("No documentation for active project")

        if data_availability.commit_count == 0:
            gaps.append("No commit history available")

        if data_availability.file_count == 0:
            gaps.append("No code files accessible")

        if repo_data.is_fork and not repo_data.recent_commits:
            gaps.append("Fork with no unique commits")

        if data_availability.days_of_history == 0:
            gaps.append("All commits on same day - no development timeline")

        return gaps

    def _note_assumptions(
        self, repo_data: RepositoryData, data_availability: DataAvailability
    ) -> List[str]:
        """Note assumptions made during analysis."""
        assumptions = []

        if data_availability.contributor_count == 1:
            assumptions.append("Assuming solo development practices")

        if not data_availability.has_tests:
            assumptions.append("Testing may be done outside repository")

        if repo_data.is_fork:
            assumptions.append("Contributions to upstream may not be visible")

        if data_availability.language_count > 3:
            assumptions.append("Multi-language use indicates versatility")

        if not data_availability.has_ci:
            assumptions.append("CI/CD may be configured elsewhere")

        return assumptions

    def _generate_reliability_notes(
        self,
        data_availability: DataAvailability,
        limitations: AnalysisLimitations,
        uncertainty: UncertaintyFactors,
    ) -> List[str]:
        """Generate notes about analysis reliability."""
        notes = []

        # Determine sufficiency for this method
        sufficiency = self._determine_data_sufficiency(data_availability)

        # Data-based notes
        if sufficiency == "comprehensive":
            notes.append("Rich data enables thorough analysis")
        elif sufficiency == "minimal":
            notes.append("Limited data significantly constrains analysis")

        # Limitation-based notes
        total_limitations = len(limitations.all_limitations())
        if total_limitations > 10:
            notes.append(f"Analysis has {total_limitations} known limitations")

        # Uncertainty-based notes
        if len(uncertainty.missing_critical_data) > 2:
            notes.append("Multiple critical data points missing")

        # Positive indicators
        if data_availability.has_tests and data_availability.has_ci:
            notes.append("Quality practices visible enhance reliability")

        if data_availability.days_of_history and data_availability.days_of_history > 90:
            notes.append("Extended history provides behavioral patterns")

        return notes
