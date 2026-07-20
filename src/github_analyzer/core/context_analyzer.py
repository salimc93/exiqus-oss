# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Context-aware repository analysis for different evaluation scenarios.

This module provides context-specific evaluation criteria for analyzing
repositories based on the analysis context (startup, enterprise, agency, etc.).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional

from ..data.models import RepositoryData
from ..utils.logging import get_logger

logger = get_logger(__name__)


class ContextThresholds:
    """Constants for context analysis thresholds and magic numbers."""

    # Signal evaluation thresholds
    RAPID_PROTOTYPING_COMMIT_FREQ = 3.0
    RAPID_PROTOTYPING_COMMIT_SIZE = 200
    DIVERSE_TECH_MIN_LANGUAGES = 3
    MVP_MINDSET_COMMIT_FREQ = 2.0
    MVP_MINDSET_MAX_COMMITS = 100
    QUICK_ITERATION_MAX_DAYS = 14
    QUICK_ITERATION_MIN_FREQ = 4.0

    # Scoring thresholds
    DEFAULT_NEGATIVE_THRESHOLD = 0.5
    HIGH_ACTIVITY_MIN_COMMITS = 50
    RECENT_ACTIVITY_MAX_DAYS = 30

    # File size and content thresholds
    LARGE_REPO_MIN_SIZE = 1000  # KB
    README_MIN_LENGTH = 100
    DOCUMENTATION_RATIO_THRESHOLD = 0.3


# Signal handler functions
def _evaluate_rapid_prototyping(repo: RepositoryData) -> bool:
    """Check for rapid prototyping patterns."""
    return (
        repo.metrics.commit_frequency > ContextThresholds.RAPID_PROTOTYPING_COMMIT_FREQ
        and repo.metrics.avg_commit_size
        < ContextThresholds.RAPID_PROTOTYPING_COMMIT_SIZE
    )


def _evaluate_diverse_tech_stack(repo: RepositoryData) -> bool:
    """Check for diverse technology usage."""
    return len(repo.languages) >= ContextThresholds.DIVERSE_TECH_MIN_LANGUAGES


def _evaluate_pragmatic_solutions(repo: RepositoryData) -> bool:
    """Check for pragmatic approach to problem-solving."""
    return not _is_over_engineered(repo) and (repo.has_ci_config or repo.has_tests)


def _evaluate_mvp_mindset(repo: RepositoryData) -> bool:
    """Check for MVP development patterns."""
    return (
        repo.metrics.commit_frequency > ContextThresholds.MVP_MINDSET_COMMIT_FREQ
        and repo.metrics.total_commits < ContextThresholds.MVP_MINDSET_MAX_COMMITS
    )


def _evaluate_quick_iterations(repo: RepositoryData) -> bool:
    """Check for quick iteration patterns."""
    return (
        repo.metrics.days_since_last_commit < ContextThresholds.QUICK_ITERATION_MAX_DAYS
        and repo.metrics.commit_frequency > ContextThresholds.QUICK_ITERATION_MIN_FREQ
    )


def _evaluate_experimental_features(repo: RepositoryData) -> bool:
    """Check for experimental technology usage."""
    return len(repo.languages) > 2 and any(
        lang in repo.languages for lang in ["TypeScript", "Go", "Rust"]
    )


def _evaluate_comprehensive_testing(repo: RepositoryData) -> bool:
    """Check for comprehensive testing practices."""
    return (
        repo.has_tests
        and repo.metrics.test_coverage_estimate > 0.7
        and repo.has_ci_config
    )


def _evaluate_detailed_documentation(repo: RepositoryData) -> bool:
    """Check for detailed documentation."""
    return (
        repo.has_readme
        and len(repo.readme_content or "") > 2000
        and repo.metrics.documentation_presence != "0 documentation files found"
        and (repo.has_contributing or "docs/" in str(repo.file_structure))
    )


def _evaluate_design_patterns(repo: RepositoryData) -> bool:
    """Check for good design patterns."""
    return (
        _has_good_architecture(repo)
        and repo.metrics.lines_of_code is not None
        and repo.metrics.lines_of_code > 5000
    )


def _evaluate_scalable_architecture(repo: RepositoryData) -> bool:
    """Check for scalable architecture."""
    return _has_good_architecture(repo) and repo.metrics.unique_contributors > 3


def _evaluate_security_focus(repo: RepositoryData) -> bool:
    """Check for security-focused development."""
    return repo.has_license and repo.has_ci_config and len(repo.languages) >= 2


def _evaluate_code_reviews(repo: RepositoryData) -> bool:
    """Check for code review practices."""
    return repo.metrics.unique_contributors > 2


def _evaluate_ci_cd_pipeline(repo: RepositoryData) -> bool:
    """Check for CI/CD pipeline."""
    return repo.has_ci_config


def _evaluate_multiple_languages(repo: RepositoryData) -> bool:
    """Check for multiple language usage (agency-specific)."""
    return (
        len(repo.languages) >= ContextThresholds.DIVERSE_TECH_MIN_LANGUAGES
        and max(repo.languages.values()) < sum(repo.languages.values()) * 0.8
    )


def _evaluate_various_project_types(repo: RepositoryData) -> bool:
    """Check for various project types."""
    return len(repo.languages) >= ContextThresholds.DIVERSE_TECH_MIN_LANGUAGES and any(
        (tech in repo.readme_content.lower() if repo.readme_content else "")
        for tech in ["client", "project", "website", "application"]
    )


def _evaluate_client_documentation(repo: RepositoryData) -> bool:
    """Check for client-focused documentation."""
    return (
        repo.has_readme
        and len(repo.readme_content or "") > 800
        and any(
            (word in repo.readme_content.lower() if repo.readme_content else "")
            for word in ["installation", "setup", "getting started", "usage"]
        )
    )


def _evaluate_quick_turnaround(repo: RepositoryData) -> bool:
    """Check for quick turnaround capability."""
    return (
        repo.metrics.commit_frequency > ContextThresholds.MVP_MINDSET_COMMIT_FREQ
        and repo.metrics.total_commits < 200
    )


def _evaluate_portfolio_diversity(repo: RepositoryData) -> bool:
    """Check for portfolio diversity."""
    return len(repo.languages) >= 4


def _evaluate_clean_handoffs(repo: RepositoryData) -> bool:
    """Check for clean project handoffs."""
    return repo.has_readme and repo.has_license and len(repo.readme_content or "") > 500


def _evaluate_community_engagement(repo: RepositoryData) -> bool:
    """Check for community engagement."""
    return repo.open_issues > 0 and repo.stars > 5 and repo.forks > 1


def _evaluate_clear_documentation(repo: RepositoryData) -> bool:
    """Check for clear documentation."""
    return repo.has_readme and len(repo.readme_content or "") > 1000


def _evaluate_responsive_to_issues(repo: RepositoryData) -> bool:
    """Check for responsiveness to issues."""
    return (
        repo.open_issues > 0
        and repo.metrics.days_since_last_commit
        < ContextThresholds.RECENT_ACTIVITY_MAX_DAYS * 2
    )


def _evaluate_collaborative_prs(repo: RepositoryData) -> bool:
    """Check for collaborative PR practices."""
    return repo.metrics.unique_contributors > 2


def _evaluate_inclusive_language(repo: RepositoryData) -> bool:
    """Check for inclusive language and practices."""
    return repo.has_contributing or repo.has_license


def _evaluate_contribution_guidelines(repo: RepositoryData) -> bool:
    """Check for contribution guidelines."""
    return repo.has_contributing


def _evaluate_consistent_commits(repo: RepositoryData) -> bool:
    """Check for consistent commit patterns."""
    return repo.metrics.commit_frequency > 0.5 and repo.metrics.total_commits > 50


def _evaluate_structured_codebase(repo: RepositoryData) -> bool:
    """Check for well-structured codebase."""
    common_dirs = {"src", "lib", "test", "tests", "docs", "config"}
    repo_dirs = {f.name.lower() for f in repo.file_structure if f.type == "directory"}
    return len(common_dirs.intersection(repo_dirs)) >= 3


def _evaluate_team_collaboration(repo: RepositoryData) -> bool:
    """Check for team collaboration indicators."""
    return repo.metrics.unique_contributors >= 2


def _evaluate_balanced_skills(repo: RepositoryData) -> bool:
    """Check for balanced technical skills."""
    return repo.has_tests and repo.has_readme and repo.metrics.commit_frequency > 0.5


def _evaluate_good_practices(repo: RepositoryData) -> bool:
    """Check for good development practices."""
    good_practice_count = sum(
        [
            repo.has_tests,
            repo.has_readme,
            repo.has_license,
            repo.has_ci_config,
            repo.metrics.commit_frequency > 1,
        ]
    )
    return good_practice_count >= 3


def _evaluate_consistent_quality(repo: RepositoryData) -> bool:
    """Check for consistent quality."""
    return repo.metrics.total_commits > 10 and repo.metrics.commit_frequency > 0.5


def _evaluate_professional_approach(repo: RepositoryData) -> bool:
    """Check for professional approach."""
    return repo.has_readme and repo.has_license and repo.metrics.total_commits > 5


# Negative signal handlers
def _evaluate_over_engineering(repo: RepositoryData) -> bool:
    """Check for over-engineering patterns."""
    return (
        _is_over_engineered(repo)
        and repo.metrics.total_commits < ContextThresholds.HIGH_ACTIVITY_MIN_COMMITS
    )


def _evaluate_excessive_documentation(repo: RepositoryData) -> bool:
    """Check for excessive documentation."""
    # Check for excessive documentation presence
    doc_presence = repo.metrics.documentation_presence
    if doc_presence and "documentation files" in doc_presence:
        # Extract numbers from string like "5 documentation files in 20 total files"
        import re

        match = re.findall(r"\d+", doc_presence)
        if len(match) == 2:
            doc_files = int(match[0])
            total_files = int(match[1])
            # Check if more than 40% of files are documentation
            if total_files > 0 and (doc_files / total_files) > 0.4:
                return (
                    repo.metrics.lines_of_code is not None
                    and repo.metrics.lines_of_code < 5000
                )
    return False


def _evaluate_rigid_processes(repo: RepositoryData) -> bool:
    """Check for overly rigid processes."""
    return repo.has_contributing and repo.metrics.unique_contributors < 3


def _evaluate_slow_development(
    repo: RepositoryData, threshold: Optional[float] = None
) -> bool:
    """Check for slow development patterns."""
    if threshold is None:
        threshold = ContextThresholds.DEFAULT_NEGATIVE_THRESHOLD
    return repo.metrics.commit_frequency < threshold


def _evaluate_no_tests(repo: RepositoryData) -> bool:
    """Check for lack of testing."""
    return not repo.has_tests and repo.metrics.total_commits > 10


def _evaluate_poor_documentation(
    repo: RepositoryData, min_length: Optional[int] = None
) -> bool:
    """Check for poor documentation."""
    if min_length is None:
        min_length = ContextThresholds.README_MIN_LENGTH * 2
    return not repo.has_readme or len(repo.readme_content or "") < min_length


def _evaluate_security_issues(repo: RepositoryData) -> bool:
    """Check for security issues."""
    return not repo.has_license and repo.stars > 5


def _evaluate_no_process(repo: RepositoryData) -> bool:
    """Check for lack of process."""
    return not repo.has_ci_config and repo.metrics.unique_contributors > 3


def _evaluate_cowboy_coding(repo: RepositoryData) -> bool:
    """Check for cowboy coding patterns."""
    return repo.metrics.unique_contributors == 1 and repo.metrics.total_commits > 100


def _evaluate_single_tech_focus(repo: RepositoryData) -> bool:
    """Check for single technology focus."""
    return len(repo.languages) <= 1 and repo.metrics.total_commits > 20


def _evaluate_poor_communication(repo: RepositoryData) -> bool:
    """Check for poor communication."""
    return not repo.has_readme and repo.metrics.total_commits > 15


def _evaluate_unfinished_projects(repo: RepositoryData) -> bool:
    """Check for unfinished projects."""
    return (
        repo.open_issues > 10
        and repo.metrics.days_since_last_commit > 90
        and repo.metrics.total_commits > 10
    )


def _evaluate_no_documentation(repo: RepositoryData) -> bool:
    """Check for lack of documentation."""
    return not repo.has_readme and repo.metrics.total_commits > 10


def _evaluate_ignored_issues(repo: RepositoryData) -> bool:
    """Check for ignored issues."""
    return repo.open_issues > 5 and repo.metrics.days_since_last_commit > 180


def _evaluate_no_community_docs(repo: RepositoryData) -> bool:
    """Check for missing community documentation."""
    return repo.stars > 10 and not repo.has_contributing


def _evaluate_poor_practices(repo: RepositoryData) -> bool:
    """Check for poor development practices."""
    bad_practice_count = sum(
        [
            not repo.has_readme,
            not repo.has_tests and repo.metrics.total_commits > 10,
            repo.metrics.commit_frequency < 0.1,
            repo.metrics.days_since_last_commit > 365,
        ]
    )
    return bad_practice_count >= 2


def _evaluate_inconsistent_quality(repo: RepositoryData) -> bool:
    """Check for inconsistent quality."""
    return repo.metrics.total_commits > 20 and repo.metrics.commit_frequency < 0.2


def _evaluate_no_standards(repo: RepositoryData) -> bool:
    """Check for lack of standards."""
    return (
        not repo.has_readme and not repo.has_license and repo.metrics.total_commits > 5
    )


# Helper functions
def _is_over_engineered(repo: RepositoryData) -> bool:
    """Check if repository shows signs of over-engineering."""
    if repo.size < ContextThresholds.LARGE_REPO_MIN_SIZE:
        if len(repo.file_structure) > 50:
            return True

    max_depth = max((f.path.count("/") for f in repo.file_structure), default=0)
    if max_depth > 6 and repo.size < 5000:
        return True

    return False


def _has_good_architecture(repo: RepositoryData) -> bool:
    """Check if repository has good architectural patterns."""
    common_dirs = {"src", "lib", "tests", "docs", "config"}
    repo_dirs = {f.name for f in repo.file_structure if f.type == "directory"}

    if len(common_dirs.intersection(repo_dirs)) >= 3:
        return True

    if len(repo_dirs) > 5 and repo.has_tests:
        return True

    return False


# Signal handler registries
POSITIVE_SIGNAL_HANDLERS: Dict[str, Callable[[RepositoryData], bool]] = {
    "rapid_prototyping": _evaluate_rapid_prototyping,
    "diverse_tech_stack": _evaluate_diverse_tech_stack,
    "pragmatic_solutions": _evaluate_pragmatic_solutions,
    "mvp_mindset": _evaluate_mvp_mindset,
    "quick_iterations": _evaluate_quick_iterations,
    "experimental_features": _evaluate_experimental_features,
    "comprehensive_testing": _evaluate_comprehensive_testing,
    "detailed_documentation": _evaluate_detailed_documentation,
    "design_patterns": _evaluate_design_patterns,
    "scalable_architecture": _evaluate_scalable_architecture,
    "security_focus": _evaluate_security_focus,
    "code_reviews": _evaluate_code_reviews,
    "ci_cd_pipeline": _evaluate_ci_cd_pipeline,
    "multiple_languages": _evaluate_multiple_languages,
    "various_project_types": _evaluate_various_project_types,
    "client_documentation": _evaluate_client_documentation,
    "quick_turnaround": _evaluate_quick_turnaround,
    "portfolio_diversity": _evaluate_portfolio_diversity,
    "clean_handoffs": _evaluate_clean_handoffs,
    "community_engagement": _evaluate_community_engagement,
    "clear_documentation": _evaluate_clear_documentation,
    "responsive_to_issues": _evaluate_responsive_to_issues,
    "collaborative_prs": _evaluate_collaborative_prs,
    "inclusive_language": _evaluate_inclusive_language,
    "contribution_guidelines": _evaluate_contribution_guidelines,
    "consistent_commits": _evaluate_consistent_commits,
    "structured_codebase": _evaluate_structured_codebase,
    "team_collaboration": _evaluate_team_collaboration,
    "balanced_skills": _evaluate_balanced_skills,
    "good_practices": _evaluate_good_practices,
    "consistent_quality": _evaluate_consistent_quality,
    "professional_approach": _evaluate_professional_approach,
}

NEGATIVE_SIGNAL_HANDLERS: Dict[str, Callable[..., bool]] = {
    "over_engineering": _evaluate_over_engineering,
    "excessive_documentation": _evaluate_excessive_documentation,
    "rigid_processes": _evaluate_rigid_processes,
    "slow_development": _evaluate_slow_development,
    "no_tests": _evaluate_no_tests,
    "poor_documentation": _evaluate_poor_documentation,
    "security_issues": _evaluate_security_issues,
    "no_process": _evaluate_no_process,
    "cowboy_coding": _evaluate_cowboy_coding,
    "single_tech_focus": _evaluate_single_tech_focus,
    "poor_communication": _evaluate_poor_communication,
    "unfinished_projects": _evaluate_unfinished_projects,
    "no_documentation": _evaluate_no_documentation,
    "ignored_issues": _evaluate_ignored_issues,
    "no_community_docs": _evaluate_no_community_docs,
    "poor_practices": _evaluate_poor_practices,
    "inconsistent_quality": _evaluate_inconsistent_quality,
    "no_standards": _evaluate_no_standards,
}


class AnalysisContext(Enum):
    """Different analysis contexts requiring different evaluation criteria."""

    STARTUP = "startup"
    ENTERPRISE = "enterprise"
    AGENCY = "agency"
    OPEN_SOURCE = "open_source"
    GENERAL = "general"  # Default context


@dataclass
class ContextCriteria:
    """Evaluation criteria specific to an analysis context."""

    name: str
    description: str
    positive_signals: List[str] = field(default_factory=list)
    negative_signals: List[str] = field(default_factory=list)
    weight_adjustments: Dict[str, float] = field(default_factory=dict)
    focus_areas: List[str] = field(default_factory=list)


@dataclass
class ContextualAssessment:
    """Assessment result with context-specific insights."""

    context: AnalysisContext
    evidence_count: int  # Total evidence patterns found
    strengths: List[str] = field(default_factory=list)
    concerns: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    key_insight: str = ""


class ContextAnalyzer:
    """
    Analyzes repositories with context-aware evaluation criteria.

    Provides different assessments for the same repository based on
    the specific analysis context (startup vs enterprise vs agency).
    """

    def __init__(self) -> None:
        """Initialize context analyzer with evaluation criteria."""
        self.criteria = self._initialize_criteria()

    def _initialize_criteria(self) -> Dict[AnalysisContext, ContextCriteria]:
        """Initialize context-specific evaluation criteria."""
        return {
            AnalysisContext.STARTUP: ContextCriteria(
                name="Startup Developer",
                description="Fast-moving, adaptable developer for startup environment",
                positive_signals=[
                    "rapid_prototyping",
                    "diverse_tech_stack",
                    "pragmatic_solutions",
                    "mvp_mindset",
                    "quick_iterations",
                    "experimental_features",
                ],
                negative_signals=[
                    "over_engineering",
                    "excessive_documentation",
                    "rigid_processes",
                    "slow_development",
                ],
                weight_adjustments={
                    "speed": 1.5,
                    "innovation": 1.3,
                    "adaptability": 1.4,
                    "documentation": 0.7,
                    "testing": 0.8,
                    "process": 0.6,
                },
                focus_areas=[
                    "shipping_speed",
                    "problem_solving",
                    "learning_ability",
                    "pragmatism",
                ],
            ),
            AnalysisContext.ENTERPRISE: ContextCriteria(
                name="Enterprise Developer",
                description="Process-oriented developer for large-scale systems",
                positive_signals=[
                    "comprehensive_testing",
                    "detailed_documentation",
                    "design_patterns",
                    "scalable_architecture",
                    "security_focus",
                    "code_reviews",
                    "ci_cd_pipeline",
                    "consistent_commits",  # NEW
                    "structured_codebase",  # NEW
                    "team_collaboration",  # NEW
                ],
                negative_signals=[
                    "no_tests",
                    "poor_documentation",
                    "security_issues",
                    "no_process",
                    "cowboy_coding",
                ],
                weight_adjustments={
                    "testing": 1.5,
                    "documentation": 1.4,
                    "architecture": 1.3,
                    "security": 1.4,
                    "process": 1.5,
                    "speed": 0.8,
                },
                focus_areas=[
                    "code_quality",
                    "maintainability",
                    "team_collaboration",
                    "standards_compliance",
                ],
            ),
            AnalysisContext.AGENCY: ContextCriteria(
                name="Agency Developer",
                description="Versatile developer for diverse client projects",
                positive_signals=[
                    "multiple_languages",
                    "various_project_types",
                    "client_documentation",
                    "quick_turnaround",
                    "portfolio_diversity",
                    "clean_handoffs",
                ],
                negative_signals=[
                    "single_tech_focus",
                    "poor_communication",
                    "unfinished_projects",
                    "no_documentation",
                ],
                weight_adjustments={
                    "versatility": 1.5,
                    "communication": 1.4,
                    "delivery": 1.3,
                    "client_focus": 1.3,
                    "depth": 0.7,
                },
                focus_areas=[
                    "project_variety",
                    "communication_skills",
                    "delivery_track_record",
                    "adaptability",
                ],
            ),
            AnalysisContext.OPEN_SOURCE: ContextCriteria(
                name="Open Source Contributor",
                description="Community-focused developer for open source projects",
                positive_signals=[
                    "community_engagement",
                    "clear_documentation",
                    "responsive_to_issues",
                    "collaborative_prs",
                    "inclusive_language",
                    "contribution_guidelines",
                ],
                negative_signals=[
                    "ignored_issues",
                    "poor_communication",
                    "no_community_docs",
                    "hostile_responses",
                ],
                weight_adjustments={
                    "collaboration": 1.5,
                    "documentation": 1.4,
                    "community": 1.5,
                    "code_quality": 1.2,
                    "speed": 0.9,
                },
                focus_areas=[
                    "community_building",
                    "collaboration",
                    "documentation",
                    "inclusivity",
                ],
            ),
            AnalysisContext.GENERAL: ContextCriteria(
                name="General Developer",
                description="Well-rounded developer for general positions",
                positive_signals=[
                    "balanced_skills",
                    "good_practices",
                    "consistent_quality",
                    "professional_approach",
                ],
                negative_signals=[
                    "poor_practices",
                    "inconsistent_quality",
                    "no_standards",
                ],
                weight_adjustments={},  # No adjustments for general context
                focus_areas=[
                    "overall_quality",
                    "professionalism",
                    "best_practices",
                    "consistency",
                ],
            ),
        }

    def analyze(
        self, repo_data: RepositoryData, context: AnalysisContext
    ) -> ContextualAssessment:
        """
        Analyze repository for specific analysis context.

        Args:
            repo_data: Repository data to analyze
            context: Analysis context for evaluation

        Returns:
            Context-specific assessment
        """
        logger.info(f"Analyzing {repo_data.full_name} for {context.value} context")

        criteria = self.criteria[context]

        # Evaluate repository against context criteria
        positive_matches = self._evaluate_positive_signals(repo_data, criteria)
        negative_matches = self._evaluate_negative_signals(repo_data, criteria)

        # Calculate total evidence count
        evidence_count = len(positive_matches)

        # Generate context-specific insights
        strengths = self._identify_strengths(repo_data, criteria, positive_matches)
        concerns = self._identify_concerns(repo_data, criteria, negative_matches)
        recommendations = self._generate_recommendations(
            repo_data, criteria, evidence_count
        )

        key_insight = self._generate_key_insight(
            repo_data, context, evidence_count, positive_matches, negative_matches
        )

        return ContextualAssessment(
            context=context,
            evidence_count=evidence_count,
            strengths=strengths,
            concerns=concerns,
            recommendations=recommendations,
            key_insight=key_insight,
        )

    def _evaluate_positive_signals(
        self, repo_data: RepositoryData, criteria: ContextCriteria
    ) -> List[str]:
        """Evaluate repository for positive signals based on context."""
        matches = []

        for signal in criteria.positive_signals:
            handler = POSITIVE_SIGNAL_HANDLERS.get(signal)
            if handler and handler(repo_data):
                matches.append(signal)
            elif not handler:
                logger.warning(f"No handler found for positive signal: {signal}")

        return matches

    def _evaluate_negative_signals(
        self, repo_data: RepositoryData, criteria: ContextCriteria
    ) -> List[str]:
        """Evaluate repository for negative signals based on context."""
        matches = []

        for signal in criteria.negative_signals:
            handler = NEGATIVE_SIGNAL_HANDLERS.get(signal)
            if handler:
                # Handle context-sensitive signals with special parameters
                if signal == "slow_development":
                    threshold = ContextThresholds.DEFAULT_NEGATIVE_THRESHOLD  # Default
                    if criteria.name == "Startup Developer":
                        threshold = 2.0  # Higher threshold for startups
                    elif criteria.name == "Enterprise Developer":
                        threshold = 0.3  # Lower threshold acceptable for enterprise
                    if handler(repo_data, threshold):
                        matches.append(signal)
                elif signal == "poor_documentation":
                    min_length = ContextThresholds.README_MIN_LENGTH * 2  # Default
                    if criteria.name == "Enterprise Developer":
                        min_length = (
                            ContextThresholds.README_MIN_LENGTH * 10
                        )  # Higher standards for enterprise
                    elif criteria.name == "Open Source Contributor":
                        min_length = (
                            ContextThresholds.README_MIN_LENGTH * 8
                        )  # Higher for open source
                    elif criteria.name == "Agency Developer":
                        min_length = (
                            ContextThresholds.README_MIN_LENGTH * 5
                        )  # Moderate for agency
                    if handler(repo_data, min_length):
                        matches.append(signal)
                else:
                    # Standard signal handling
                    if handler(repo_data):
                        matches.append(signal)
            elif signal != "hostile_responses":  # Skip unimplemented signals
                logger.warning(f"No handler found for negative signal: {signal}")

        return matches

    def _identify_strengths(
        self,
        repo_data: RepositoryData,
        criteria: ContextCriteria,
        positive_matches: List[str],
    ) -> List[str]:
        """Identify context-specific strengths."""
        strengths = []

        signal_descriptions = {
            "rapid_prototyping": f"Fast development pace with {repo_data.metrics.commit_frequency:.1f} commits/week",
            "diverse_tech_stack": f"Experience with {len(repo_data.languages)} different technologies",
            "pragmatic_solutions": "Pragmatic approach to problem-solving",
            "comprehensive_testing": "Strong testing practices with good coverage",
            "detailed_documentation": "Excellent documentation and communication",
            "scalable_architecture": "Well-structured, maintainable codebase",
            "community_engagement": f"Active community with {repo_data.stars} stars",
            "multiple_languages": f"Versatile with {len(repo_data.languages)} programming languages",
            "ci_cd_pipeline": "Automated CI/CD pipeline configured",
            "consistent_commits": f"Consistent development with {repo_data.metrics.total_commits} commits and {repo_data.metrics.commit_frequency:.1f} commits/week",
            "structured_codebase": f"Well-organized project structure with {len([f for f in repo_data.file_structure if f.type == 'directory'])} directories",
            "team_collaboration": f"Strong team collaboration with {repo_data.metrics.unique_contributors} contributors",
            "design_patterns": "Uses established design patterns and best practices",
            "security_focus": "Implements security best practices",
            "code_reviews": "Active code review culture evident",
        }

        # For enterprise context with new signals, show more strengths
        max_strengths = 6 if criteria.name == "Enterprise Developer" else 3

        for match in positive_matches[:max_strengths]:
            if match in signal_descriptions:
                strengths.append(signal_descriptions[match])

        return strengths

    def _identify_concerns(
        self,
        repo_data: RepositoryData,
        criteria: ContextCriteria,
        negative_matches: List[str],
    ) -> List[str]:
        """Identify context-specific concerns."""
        concerns = []

        signal_descriptions = {
            "over_engineering": "May over-complicate solutions for simple problems",
            "no_tests": "Lacks testing practices critical for this role",
            "poor_documentation": "Insufficient documentation for team collaboration",
            "slow_development": "Development pace may not match requirements",
            "single_tech_focus": "Limited technology diversity for varied client needs",
        }

        for match in negative_matches[:3]:  # Top 3 concerns
            if match in signal_descriptions:
                concerns.append(signal_descriptions[match])

        return concerns

    def _generate_recommendations(
        self, repo_data: RepositoryData, criteria: ContextCriteria, evidence_count: int
    ) -> List[str]:
        """Generate context-specific recommendations."""
        recommendations = []

        # Use pure evidence count thresholds based on context requirements
        if evidence_count >= 4:
            recommendations.append(f"Strong evidence for {criteria.name} role")
        elif evidence_count >= 2:
            recommendations.append(
                f"Moderate evidence for {criteria.name} role, consider interview focus areas"
            )
        else:
            recommendations.append(
                f"Limited evidence for {criteria.name} role, additional assessment needed"
            )

        # Add specific recommendations based on context
        for focus_area in criteria.focus_areas[:2]:
            if (
                focus_area == "shipping_speed"
                and repo_data.metrics.commit_frequency < 2
            ):
                recommendations.append(
                    "Assess ability to work in fast-paced environment"
                )
            elif focus_area == "code_quality" and not repo_data.has_tests:
                recommendations.append(
                    "Evaluate testing philosophy and quality practices"
                )
            elif focus_area == "project_variety" and len(repo_data.languages) < 3:
                recommendations.append(
                    "Discuss experience with diverse technology stacks"
                )

        return recommendations

    def _generate_key_insight(
        self,
        repo_data: RepositoryData,
        context: AnalysisContext,
        evidence_count: int,
        positive_matches: List[str],
        negative_matches: List[str],
    ) -> str:
        """Generate the most important insight for this context."""
        # Enhanced context-specific insights with more nuance
        if context == AnalysisContext.STARTUP:
            if (
                "rapid_prototyping" in positive_matches
                and "quick_iterations" in positive_matches
            ):
                return "Excellent startup fit: demonstrates rapid iteration and prototype mindset"
            elif "rapid_prototyping" in positive_matches:
                return "Shows startup-friendly rapid iteration capabilities"
            elif (
                "pragmatic_solutions" in positive_matches
                and "mvp_mindset" in positive_matches
            ):
                return (
                    "Pragmatic approach ideal for MVP development and startup velocity"
                )
            elif "over_engineering" in negative_matches:
                return "May struggle with startup's need for pragmatic, quick solutions"
            elif "slow_development" in negative_matches:
                return "Development velocity may not match startup pace requirements"
            elif evidence_count >= 2:
                return "Solid potential for startup environment with some adaptation"
        elif context == AnalysisContext.ENTERPRISE:
            if (
                "comprehensive_testing" in positive_matches
                and "detailed_documentation" in positive_matches
            ):
                return "Outstanding enterprise fit: demonstrates quality, process, and documentation discipline"
            elif "comprehensive_testing" in positive_matches:
                return "Demonstrates enterprise-grade quality practices"
            elif (
                "scalable_architecture" in positive_matches
                and "code_reviews" in positive_matches
            ):
                return "Shows enterprise-level architecture and collaboration skills"
            elif "security_focus" in positive_matches:
                return "Demonstrates security-conscious development suitable for enterprise"
            elif "no_tests" in negative_matches:
                return "Lacks critical testing discipline for enterprise development"
            elif "poor_documentation" in negative_matches:
                return "Documentation practices below enterprise standards"
            elif "cowboy_coding" in negative_matches:
                return "Individual development style may not fit enterprise team environment"
        elif context == AnalysisContext.AGENCY:
            if (
                "multiple_languages" in positive_matches
                and "portfolio_diversity" in positive_matches
            ):
                return "Perfect agency fit: demonstrates versatility across technologies and project types"
            elif "multiple_languages" in positive_matches:
                return "Versatile developer suitable for varied client projects"
            elif (
                "client_documentation" in positive_matches
                and "clean_handoffs" in positive_matches
            ):
                return "Client-focused approach with professional handoff capabilities"
            elif "quick_turnaround" in positive_matches:
                return "Demonstrates ability to deliver projects quickly for client satisfaction"
            elif "single_tech_focus" in negative_matches:
                return "Limited tech stack may constrain client project options"
            elif "poor_communication" in negative_matches:
                return "Communication skills critical for client-facing agency work"
        elif context == AnalysisContext.OPEN_SOURCE:
            if (
                "community_engagement" in positive_matches
                and "responsive_to_issues" in positive_matches
            ):
                return "Excellent open source contributor: active community engagement and responsiveness"
            elif "community_engagement" in positive_matches:
                return "Shows good community engagement suitable for open source collaboration"
            elif (
                "clear_documentation" in positive_matches
                and "contribution_guidelines" in positive_matches
            ):
                return "Demonstrates commitment to accessible, collaborative open source development"
            elif "collaborative_prs" in positive_matches:
                return "Collaborative approach ideal for open source contribution"
            elif "ignored_issues" in negative_matches:
                return "May struggle with community responsiveness expectations"
            elif "no_community_docs" in negative_matches:
                return "Lacks community-building documentation practices"
        elif context == AnalysisContext.GENERAL:
            if (
                "good_practices" in positive_matches
                and "consistent_quality" in positive_matches
            ):
                return "Well-rounded developer with consistent professional practices"
            elif "balanced_skills" in positive_matches:
                return "Demonstrates balanced technical and professional capabilities"
            elif "professional_approach" in positive_matches:
                return "Shows professional development approach suitable for most environments"

        # Enhanced default insights based on evidence count
        if evidence_count >= 5:
            return f"Excellent evidence for {context.value} environment with strong alignment"
        elif evidence_count >= 3:
            return f"Good evidence for {context.value} environment with minor gaps"
        elif evidence_count >= 1:
            return f"Moderate evidence for {context.value} environment requiring some development"
        else:
            return f"Limited evidence for {context.value} environment requires thorough assessment"

    def get_all_contexts(self) -> List[AnalysisContext]:
        """Get all available analysis contexts."""
        return list(AnalysisContext)

    def compare_contexts(
        self, repo_data: RepositoryData
    ) -> Dict[AnalysisContext, ContextualAssessment]:
        """
        Analyze repository for all contexts for comparison.

        Args:
            repo_data: Repository data to analyze

        Returns:
            Dictionary mapping contexts to their assessments
        """
        results = {}
        for context in AnalysisContext:
            results[context] = self.analyze(repo_data, context)
        return results
