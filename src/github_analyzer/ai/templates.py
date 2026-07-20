# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Template responses for common repository patterns.

This module provides pre-defined responses for repositories that can be
classified without AI analysis, optimizing for cost and speed.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List

from ..core.classifier import TemplateCategory
from ..data.models import RepositoryData
from ..utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TemplateResponse:
    """Pre-defined template response for common repository patterns."""

    summary: str
    evidence_strength: Dict[str, int] = field(
        default_factory=dict
    )  # technical, communication scores
    key_insights: List[str] = field(default_factory=list)
    evidence_patterns: List[Dict[str, Any]] = field(default_factory=list)
    verification_gaps: List[str] = field(default_factory=list)
    cost: float = 0.0  # Templates are always free
    generated_by: str = "template"

    def __post_init__(self) -> None:
        """Validate template response after initialization."""
        if self.cost != 0.0:
            raise ValueError("Template responses must have zero cost")

        # Validate evidence strength scores if provided
        for score in self.evidence_strength.values():
            if not (0 <= score <= 100):
                raise ValueError(f"Invalid evidence strength score: {score}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "summary": self.summary,
            "evidence_strength": self.evidence_strength,
            "key_insights": self.key_insights,
            "evidence_patterns": self.evidence_patterns,
            "verification_gaps": self.verification_gaps,
            "cost": self.cost,
            "generated_by": self.generated_by,
            "method": "template",
        }


class TemplateResponses:
    """
    Manages template responses for different repository categories.

    Provides cost-free, instant responses for repositories that can be
    classified using simple heuristics.
    """

    def __init__(self) -> None:
        """Initialize template response manager."""
        logger.debug("Initializing template response manager")

    def get_response(
        self, category: TemplateCategory, repo_data: RepositoryData
    ) -> TemplateResponse:
        """
        Get template response for repository category.

        Args:
            category: Template category from classifier
            repo_data: Repository data for personalization

        Returns:
            Template response for the category

        Raises:
            ValueError: If category is not supported
        """
        logger.debug(f"Generating template response for category: {category}")

        if category == TemplateCategory.INACTIVE:
            return self._get_inactive_response(repo_data)
        elif category == TemplateCategory.MINIMAL:
            return self._get_minimal_response(repo_data)
        elif category == TemplateCategory.ARCHIVED:
            return self._get_archived_response(repo_data)
        elif category == TemplateCategory.EMPTY:
            return self._get_empty_response(repo_data)
        elif category == TemplateCategory.FORK:
            return self._get_fork_response(repo_data)
        elif category == TemplateCategory.LEARNING:
            return self._get_learning_response(repo_data)
        elif category == TemplateCategory.POOR_PRACTICES:
            return self._get_poor_practices_response(repo_data)
        else:
            raise ValueError(f"Unsupported template category: {category}")

    def _get_inactive_response(self, repo_data: RepositoryData) -> TemplateResponse:
        """Generate response for inactive repositories."""
        days_inactive = repo_data.metrics.days_since_last_commit

        return TemplateResponse(
            summary=(
                f"Repository '{repo_data.name}' has been inactive for "
                f"{days_inactive} days, indicating limited recent development activity."
            ),
            evidence_strength={
                "technical_competence": 20,
                "communication_skills": 10,
                "professional_practices": 15,
                "growth_potential": 5,
            },
            key_insights=[
                f"No activity for {days_inactive} days",
                "Repository appears to be abandoned or completed",
                "Limited evidence of recent technical growth",
            ],
            evidence_patterns=[
                {
                    "pattern": "inactive_repository",
                    "evidence": f"No commits in {days_inactive} days",
                    "strength": "weak",
                }
            ],
            verification_gaps=[
                "Cannot assess current technical skills from inactive repository",
                "May have active development in other repositories",
            ],
        )

    def _get_minimal_response(self, repo_data: RepositoryData) -> TemplateResponse:
        """Generate response for repositories with minimal commits."""
        commit_count = repo_data.metrics.total_commits

        return TemplateResponse(
            summary=(
                f"Repository '{repo_data.name}' has only {commit_count} commits, "
                "providing limited evidence for comprehensive assessment."
            ),
            evidence_strength={
                "technical_competence": 25,
                "communication_skills": 20,
                "professional_practices": 20,
                "growth_potential": 30,
            },
            key_insights=[
                f"Limited development history with {commit_count} commits",
                "Early-stage or experimental project",
                "Insufficient data for pattern analysis",
            ],
            evidence_patterns=[
                {
                    "pattern": "minimal_activity",
                    "evidence": f"Only {commit_count} commits total",
                    "strength": "weak",
                }
            ],
            verification_gaps=[
                "Cannot identify coding patterns from minimal history",
                "Development practices unclear from limited commits",
            ],
        )

    def _get_archived_response(self, repo_data: RepositoryData) -> TemplateResponse:
        """Generate response for archived repositories."""
        return TemplateResponse(
            summary=(
                f"Repository '{repo_data.name}' is explicitly archived, "
                "indicating completed or deprecated project."
            ),
            evidence_strength={
                "technical_competence": 30,
                "communication_skills": 25,
                "professional_practices": 35,
                "growth_potential": 10,
            },
            key_insights=[
                "Repository explicitly marked as archived",
                "Project reached end-of-life or completion",
                "Historical code reference only",
            ],
            evidence_patterns=[
                {
                    "pattern": "archived_repository",
                    "evidence": "Repository is archived and read-only",
                    "strength": "moderate",
                }
            ],
            verification_gaps=[
                "Cannot assess current development practices from archived work",
                "More recent work may exist elsewhere",
            ],
        )

    def _get_empty_response(self, repo_data: RepositoryData) -> TemplateResponse:
        """Generate response for empty or nearly empty repositories."""
        return TemplateResponse(
            summary=(
                f"Repository '{repo_data.name}' contains minimal content, "
                "providing no substantial code for analysis."
            ),
            evidence_strength={
                "technical_competence": 0,
                "communication_skills": 0,
                "professional_practices": 0,
                "growth_potential": 0,
            },
            key_insights=[
                "Repository is essentially empty",
                "No code available for assessment",
                "Possible placeholder or initialization only",
            ],
            evidence_patterns=[
                {
                    "pattern": "empty_repository",
                    "evidence": "Repository contains no substantial content",
                    "strength": "none",
                }
            ],
            verification_gaps=[
                "No code to analyze",
                "Cannot assess any technical capabilities",
            ],
        )

    def _get_fork_response(self, repo_data: RepositoryData) -> TemplateResponse:
        """Generate response for unmodified forks."""
        return TemplateResponse(
            summary=(
                f"Repository '{repo_data.name}' is a fork with minimal original contributions, "
                "limiting assessment of individual work."
            ),
            evidence_strength={
                "technical_competence": 15,
                "communication_skills": 10,
                "professional_practices": 20,
                "growth_potential": 25,
            },
            key_insights=[
                "Fork with minimal modifications from original",
                "Limited original code contributions",
                "Shows interest in existing projects",
            ],
            evidence_patterns=[
                {
                    "pattern": "unmodified_fork",
                    "evidence": "Repository is a fork with minimal changes",
                    "strength": "weak",
                }
            ],
            verification_gaps=[
                "Cannot distinguish individual contributions from original work",
                "Original coding ability unclear",
            ],
        )

    def _get_learning_response(self, repo_data: RepositoryData) -> TemplateResponse:
        """Generate response for learning/tutorial repositories."""
        return TemplateResponse(
            summary=(
                f"Repository '{repo_data.name}' appears to be learning or tutorial content, "
                "showing educational progress but limited production experience."
            ),
            evidence_strength={
                "technical_competence": 40,
                "communication_skills": 35,
                "professional_practices": 30,
                "growth_potential": 60,
            },
            key_insights=[
                "Learning/tutorial repository",
                "Demonstrates commitment to skill development",
                "May lack production-level complexity",
            ],
            evidence_patterns=[
                {
                    "pattern": "learning_repository",
                    "evidence": "Content appears to be from tutorials or courses",
                    "strength": "moderate",
                }
            ],
            verification_gaps=[
                "Cannot assess original problem-solving from tutorial code",
                "Production experience unclear",
                "Real-world application skills need verification",
            ],
        )

    def _get_poor_practices_response(
        self, repo_data: RepositoryData
    ) -> TemplateResponse:
        """Generate response for repositories with poor practices."""
        evidence_items = []

        if not repo_data.has_readme:
            evidence_items.append("No README documentation")
        if not repo_data.has_tests:
            evidence_items.append("No test coverage")
        if repo_data.metrics.commit_frequency < 0.1:
            evidence_items.append("Very low commit frequency")

        return TemplateResponse(
            summary=(
                f"Repository '{repo_data.name}' shows indicators of developing practices, "
                "suggesting room for improvement in professional standards."
            ),
            evidence_strength={
                "technical_competence": 35,
                "communication_skills": 25,
                "professional_practices": 20,
                "growth_potential": 45,
            },
            key_insights=evidence_items
            + [
                "Development practices need improvement",
                "May benefit from mentoring or code review",
            ],
            evidence_patterns=[
                {
                    "pattern": "poor_practices",
                    "evidence": ", ".join(evidence_items),
                    "strength": "moderate",
                }
            ],
            verification_gaps=[
                "Cannot assess potential with proper guidance",
                "May have better practices in team environments",
            ],
        )
