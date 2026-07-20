# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Evidence-based template responses for common repository patterns.

This module provides pre-defined responses for repositories that can be
classified without AI analysis, using factual observations without scores.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List

from ..core.classifier import TemplateCategory
from ..data.models import RepositoryData
from ..utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class EvidenceBasedTemplateResponse:
    """Evidence-based template response without arbitrary scores."""

    summary: str
    observations: List[str] = field(default_factory=list)
    evidence_patterns: List[Dict[str, Any]] = field(default_factory=list)
    data_limitations: List[str] = field(default_factory=list)
    interview_guidance: List[str] = field(default_factory=list)
    cost: float = 0.0  # Templates are always free
    generated_by: str = "template"
    data_sufficiency: str = "minimal"  # minimal, limited, adequate

    def __post_init__(self) -> None:
        """Validate template response after initialization."""
        if self.cost != 0.0:
            raise ValueError("Template responses must have zero cost")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "summary": self.summary,
            "observations": self.observations,
            "evidence_patterns": self.evidence_patterns,
            "data_limitations": self.data_limitations,
            "interview_guidance": self.interview_guidance,
            "cost": self.cost,
            "generated_by": self.generated_by,
            "data_sufficiency": self.data_sufficiency,
            "method": "template",
        }


class EvidenceBasedTemplateResponses:
    """
    Manages evidence-based template responses for different repository categories.

    Provides cost-free, instant responses for repositories that can be
    classified using simple heuristics, without arbitrary scoring.
    """

    def __init__(self) -> None:
        """Initialize template response manager."""
        logger.debug("Initializing evidence-based template response manager")

    def get_response(
        self, category: TemplateCategory, repo_data: RepositoryData
    ) -> EvidenceBasedTemplateResponse:
        """
        Get evidence-based template response for repository category.

        Args:
            category: Template category from classifier
            repo_data: Repository data for personalization

        Returns:
            Evidence-based template response for the category

        Raises:
            ValueError: If category is not supported
        """
        logger.debug(
            f"Generating evidence-based template response for category: {category}"
        )

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

    def _get_inactive_response(
        self, repo_data: RepositoryData
    ) -> EvidenceBasedTemplateResponse:
        """Generate response for inactive repositories."""
        days_inactive = repo_data.metrics.days_since_last_commit

        return EvidenceBasedTemplateResponse(
            summary=(
                f"Repository '{repo_data.name}' shows no commits for "
                f"{days_inactive} days. Limited data available for assessment."
            ),
            observations=[
                f"Last commit was {days_inactive} days ago",
                f"Repository contains {repo_data.metrics.total_commits} total commits",
                "No recent development activity observed",
            ],
            evidence_patterns=[
                {
                    "pattern": "inactive_repository",
                    "evidence": f"No commits in {days_inactive} days",
                    "data_points": 1,
                }
            ],
            data_limitations=[
                "Cannot assess current technical skills from inactive repository",
                "Recent work may exist in other repositories",
                "Unable to evaluate current development practices",
                "No insight into recent learning or growth",
            ],
            interview_guidance=[
                "Discuss current projects and active repositories",
                "Explore reasons for repository inactivity",
                "Assess technical skills through other means",
                "Review more recent work samples if available",
            ],
            data_sufficiency="minimal",
        )

    def _get_minimal_response(
        self, repo_data: RepositoryData
    ) -> EvidenceBasedTemplateResponse:
        """Generate response for repositories with minimal commits."""
        commit_count = repo_data.metrics.total_commits

        return EvidenceBasedTemplateResponse(
            summary=(
                f"Repository '{repo_data.name}' contains {commit_count} commits. "
                "Insufficient data for comprehensive analysis."
            ),
            observations=[
                f"Repository has {commit_count} total commits",
                "Limited development history available",
                f"Total commits: {repo_data.metrics.total_commits}",
            ],
            evidence_patterns=[
                {
                    "pattern": "minimal_activity",
                    "evidence": f"Only {commit_count} commits total",
                    "data_points": commit_count,
                }
            ],
            data_limitations=[
                "Cannot identify coding patterns from minimal history",
                "Unable to assess development velocity",
                "Insufficient data for behavioral analysis",
                "Cannot evaluate collaboration patterns",
            ],
            interview_guidance=[
                "Request additional code samples",
                "Discuss larger projects they've worked on",
                "Explore their development process",
                "Assess problem-solving through technical discussion",
            ],
            data_sufficiency="minimal",
        )

    def _get_archived_response(
        self, repo_data: RepositoryData
    ) -> EvidenceBasedTemplateResponse:
        """Generate response for archived repositories."""
        return EvidenceBasedTemplateResponse(
            summary=(
                f"Repository '{repo_data.name}' is marked as archived. "
                "Historical reference only."
            ),
            observations=[
                "Repository is explicitly archived",
                "No new commits or issues can be added",
                f"Last activity before archival: {repo_data.metrics.days_since_last_commit} days ago",
            ],
            evidence_patterns=[
                {
                    "pattern": "archived_repository",
                    "evidence": "Repository archived status",
                    "data_points": 1,
                }
            ],
            data_limitations=[
                "Cannot assess current development practices",
                "Historical code may not reflect current skills",
                "Unable to evaluate recent technology adoption",
                "No insight into current coding standards",
            ],
            interview_guidance=[
                "Discuss the project's completion or archival reason",
                "Review current active projects",
                "Assess how skills have evolved since",
                "Explore learnings from this project",
            ],
            data_sufficiency="limited",
        )

    def _get_empty_response(
        self, repo_data: RepositoryData
    ) -> EvidenceBasedTemplateResponse:
        """Generate response for empty or nearly empty repositories."""
        return EvidenceBasedTemplateResponse(
            summary=(
                f"Repository '{repo_data.name}' contains no substantial content "
                "for analysis."
            ),
            observations=[
                "Repository contains minimal or no code",
                "No meaningful commits to analyze",
                "Possible placeholder or initialization",
            ],
            evidence_patterns=[
                {
                    "pattern": "empty_repository",
                    "evidence": "No substantial content found",
                    "data_points": 0,
                }
            ],
            data_limitations=[
                "No code available for analysis",
                "Cannot assess any technical capabilities",
                "Unable to evaluate any development practices",
                "No behavioral patterns to observe",
            ],
            interview_guidance=[
                "Request actual code samples",
                "Discuss active projects",
                "Use technical interviews for assessment",
                "Review portfolio or other work",
            ],
            data_sufficiency="minimal",
        )

    def _get_fork_response(
        self, repo_data: RepositoryData
    ) -> EvidenceBasedTemplateResponse:
        """Generate response for unmodified forks."""
        return EvidenceBasedTemplateResponse(
            summary=(
                f"Repository '{repo_data.name}' is a fork. Individual contributions "
                "need verification."
            ),
            observations=[
                "Repository is forked from another project",
                "Need to identify individual contributions",
                "Shows interest in open source projects",
            ],
            evidence_patterns=[
                {
                    "pattern": "forked_repository",
                    "evidence": "Repository fork status",
                    "data_points": 1,
                }
            ],
            data_limitations=[
                "Cannot distinguish individual contributions from original",
                "Original code vs modifications unclear",
                "Unable to assess unique problem-solving",
                "Contribution scope needs clarification",
            ],
            interview_guidance=[
                "Discuss specific contributions to the fork",
                "Explore motivation for forking",
                "Review original work in other repositories",
                "Assess understanding of the forked codebase",
            ],
            data_sufficiency="limited",
        )

    def _get_learning_response(
        self, repo_data: RepositoryData
    ) -> EvidenceBasedTemplateResponse:
        """Generate response for learning/tutorial repositories."""
        return EvidenceBasedTemplateResponse(
            summary=(
                f"Repository '{repo_data.name}' appears to contain learning or "
                "tutorial content."
            ),
            observations=[
                "Content appears to be from tutorials or courses",
                "Shows commitment to learning",
                "Educational repository structure detected",
            ],
            evidence_patterns=[
                {
                    "pattern": "learning_repository",
                    "evidence": "Tutorial/course content structure",
                    "data_points": 1,
                }
            ],
            data_limitations=[
                "Cannot assess original problem-solving",
                "Tutorial code may not reflect independent work",
                "Production experience unclear",
                "Real-world application skills need verification",
            ],
            interview_guidance=[
                "Discuss what was learned from tutorials",
                "Explore how concepts were applied elsewhere",
                "Review original projects if available",
                "Assess understanding beyond tutorials",
            ],
            data_sufficiency="limited",
        )

    def _get_poor_practices_response(
        self, repo_data: RepositoryData
    ) -> EvidenceBasedTemplateResponse:
        """Generate response for repositories showing areas for improvement."""
        observations = []
        patterns = []

        if not repo_data.has_readme:
            observations.append("No README documentation found")
            patterns.append("missing_documentation")

        if not repo_data.has_tests:
            observations.append("No test files detected")
            patterns.append("no_tests")

        if repo_data.metrics.commit_frequency < 0.1:
            observations.append(
                f"Commit frequency: {repo_data.metrics.commit_frequency:.2f} per day"
            )
            patterns.append("low_commit_frequency")

        return EvidenceBasedTemplateResponse(
            summary=(
                f"Repository '{repo_data.name}' shows several areas where "
                "development practices could be explored further."
            ),
            observations=observations,
            evidence_patterns=[
                {
                    "pattern": "development_practices",
                    "evidence": ", ".join(patterns),
                    "data_points": len(patterns),
                }
            ],
            data_limitations=[
                "Cannot assess potential with different environment",
                "Team practices may differ from personal projects",
                "Context for decisions unknown",
                "May not reflect current practices",
            ],
            interview_guidance=[
                "Discuss approach to documentation",
                "Explore testing philosophy and practices",
                "Understand project context and constraints",
                "Review development process preferences",
            ],
            data_sufficiency="limited",
        )
