# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Core constants and enums for the GitHub Analyzer system.
Single source of truth for metric names and other shared constants.
"""

from enum import Enum
from typing import Dict, Tuple


class MetricName(str, Enum):
    """Standardized metric names used across the system."""

    # Technical Skills Metrics
    LANGUAGE_PROFICIENCY = "language_proficiency"
    LANGUAGE_SCORE = "language_score"
    TESTING_APPROACH = "testing_approach"
    TEST_COVERAGE = "test_coverage"
    CODE_COMPLEXITY = "code_complexity"
    ARCHITECTURAL_COMPLEXITY = "architectural_complexity"
    COMPLEXITY_MANAGEMENT = "complexity_management"
    COMPLEXITY_HANDLING = "complexity_handling"

    # Collaboration Metrics
    COLLABORATION_EFFECTIVENESS = "collaboration_effectiveness"
    COLLABORATION_EXPERIENCE = "collaboration_experience"
    COLLABORATION_INVOLVEMENT = "collaboration_involvement"
    COLLABORATIVE_ENGAGEMENT = "collaborative_engagement"
    COLLABORATIVE_COMMUNICATION = "collaborative_communication"
    COLLABORATIVE_DIALOGUE = "collaborative_dialogue"
    COLLABORATIVE_LEARNING = "collaborative_learning"

    # Communication Metrics
    COMMUNICATION_CLARITY = "communication_clarity"
    COMMIT_MESSAGE_QUALITY = "commit_message_quality"
    COMMIT_MESSAGE_CLARITY = "commit_message_clarity"
    DOCUMENTATION_QUALITY = "documentation_quality"
    DOCUMENTATION_CLARITY = "documentation_clarity"
    TECHNICAL_COMMUNICATION = "technical_communication"
    ISSUE_COMMUNICATION = "issue_communication"

    # Development Practices
    CONTINUOUS_INTEGRATION = "continuous_integration"
    CI_CD_INTEGRATION = "ci_cd_integration"
    DEPENDENCY_MANAGEMENT = "dependency_management"
    SECURITY_AWARENESS = "security_awareness"
    SECURITY_CONSCIOUSNESS = "security_consciousness"

    # Work Patterns
    COMMIT_DISCIPLINE = "commit_discipline"
    CONSISTENCY_SCORE = "consistency_score"
    RESPONSIVENESS = "responsiveness"
    ISSUE_TRACKING = "issue_tracking"
    ISSUE_TRACKING_DISCIPLINE = "issue_tracking_discipline"
    ISSUE_MANAGEMENT = "issue_management"

    # Problem Solving
    PROBLEM_SOLVING = "problem_solving"
    PROBLEM_SOLVING_CAPABILITY = "problem_solving_capability"
    PROBLEM_SOLVING_CAPACITY = "problem_solving_capacity"
    BUG_FIXING = "bug_fixing"
    BUG_FIXING_COMMITMENT = "bug_fixing_commitment"
    DEBUGGING_SKILLS = "debugging_skills"

    # Growth and Learning
    REFACTORING_ACTIVITY = "refactoring_activity"
    TECHNOLOGY_ADOPTION = "technology_adoption"
    TECHNOLOGY_ADAPTABILITY = "technology_adaptability"
    TECHNOLOGY_ECOSYSTEM_BREADTH = "technology_ecosystem_breadth"
    CONTINUOUS_IMPROVEMENT = "continuous_improvement"
    TESTING_EVOLUTION = "testing_evolution"

    # Domain Knowledge
    DOMAIN_EXPERTISE = "domain_expertise"
    PROBLEM_DOMAIN_EXPERTISE = "problem_domain_expertise"
    CROSS_FRAMEWORK_COMMUNICATION = "cross_framework_communication"

    # Performance Metrics
    TESTING_RIGOR = "testing_rigor"
    ERROR_HANDLING = "error_handling"
    CONFLICT_RESOLUTION = "conflict_resolution"
    ADAPTABILITY = "adaptability"


# Confidence ranges for each metric
METRIC_CONFIDENCE_RANGES: Dict[MetricName, Tuple[int, int]] = {
    # Technical Skills (generally higher expectations)
    MetricName.LANGUAGE_PROFICIENCY: (60, 85),
    MetricName.LANGUAGE_SCORE: (60, 85),
    MetricName.TESTING_APPROACH: (50, 75),
    MetricName.TEST_COVERAGE: (60, 85),
    MetricName.CODE_COMPLEXITY: (40, 70),
    MetricName.ARCHITECTURAL_COMPLEXITY: (40, 70),
    MetricName.COMPLEXITY_MANAGEMENT: (50, 75),
    MetricName.COMPLEXITY_HANDLING: (50, 75),
    # Collaboration (moderate expectations)
    MetricName.COLLABORATION_EFFECTIVENESS: (50, 70),
    MetricName.COLLABORATION_EXPERIENCE: (50, 70),
    MetricName.COLLABORATION_INVOLVEMENT: (50, 70),
    MetricName.COLLABORATIVE_ENGAGEMENT: (50, 70),
    MetricName.COLLABORATIVE_COMMUNICATION: (50, 70),
    MetricName.COLLABORATIVE_DIALOGUE: (50, 70),
    MetricName.COLLABORATIVE_LEARNING: (50, 70),
    # Communication (moderate to high)
    MetricName.COMMUNICATION_CLARITY: (60, 80),
    MetricName.COMMIT_MESSAGE_QUALITY: (60, 80),
    MetricName.COMMIT_MESSAGE_CLARITY: (60, 80),
    MetricName.DOCUMENTATION_QUALITY: (50, 75),
    MetricName.DOCUMENTATION_CLARITY: (50, 75),
    MetricName.TECHNICAL_COMMUNICATION: (50, 70),
    MetricName.ISSUE_COMMUNICATION: (50, 70),
    # Development Practices
    MetricName.CONTINUOUS_INTEGRATION: (50, 70),
    MetricName.CI_CD_INTEGRATION: (50, 70),
    MetricName.DEPENDENCY_MANAGEMENT: (50, 70),
    MetricName.SECURITY_AWARENESS: (50, 70),
    MetricName.SECURITY_CONSCIOUSNESS: (50, 70),
    # Work Patterns
    MetricName.COMMIT_DISCIPLINE: (50, 70),
    MetricName.CONSISTENCY_SCORE: (50, 70),
    MetricName.RESPONSIVENESS: (50, 70),
    MetricName.ISSUE_TRACKING: (50, 70),
    MetricName.ISSUE_TRACKING_DISCIPLINE: (50, 70),
    MetricName.ISSUE_MANAGEMENT: (50, 70),
    # Problem Solving
    MetricName.PROBLEM_SOLVING: (50, 70),
    MetricName.PROBLEM_SOLVING_CAPABILITY: (50, 70),
    MetricName.PROBLEM_SOLVING_CAPACITY: (50, 70),
    MetricName.BUG_FIXING: (50, 70),
    MetricName.BUG_FIXING_COMMITMENT: (50, 70),
    MetricName.DEBUGGING_SKILLS: (50, 70),
    # Growth and Learning
    MetricName.REFACTORING_ACTIVITY: (50, 70),
    MetricName.TECHNOLOGY_ADOPTION: (50, 70),
    MetricName.TECHNOLOGY_ADAPTABILITY: (50, 70),
    MetricName.TECHNOLOGY_ECOSYSTEM_BREADTH: (50, 70),
    MetricName.CONTINUOUS_IMPROVEMENT: (50, 70),
    MetricName.TESTING_EVOLUTION: (50, 70),
    # Domain Knowledge
    MetricName.DOMAIN_EXPERTISE: (50, 70),
    MetricName.PROBLEM_DOMAIN_EXPERTISE: (50, 70),
    MetricName.CROSS_FRAMEWORK_COMMUNICATION: (50, 70),
    # Performance Metrics
    MetricName.TESTING_RIGOR: (50, 70),
    MetricName.ERROR_HANDLING: (50, 70),
    MetricName.CONFLICT_RESOLUTION: (50, 70),
    MetricName.ADAPTABILITY: (50, 70),
}


# Metric synonym mapping for AI-generated variations
METRIC_SYNONYMS: Dict[str, MetricName] = {
    # Language variations
    "Language Expertise": MetricName.LANGUAGE_PROFICIENCY,
    "language expertise": MetricName.LANGUAGE_PROFICIENCY,
    "language_expertise": MetricName.LANGUAGE_PROFICIENCY,
    "Language Skills": MetricName.LANGUAGE_PROFICIENCY,
    "language skills": MetricName.LANGUAGE_PROFICIENCY,
    "Programming Language Proficiency": MetricName.LANGUAGE_PROFICIENCY,
    # Testing variations
    "Test Coverage": MetricName.TEST_COVERAGE,
    "test coverage": MetricName.TEST_COVERAGE,
    "Testing Practices": MetricName.TEST_COVERAGE,
    "testing practices": MetricName.TEST_COVERAGE,
    "Testing Coverage": MetricName.TEST_COVERAGE,
    # Documentation variations
    "Documentation": MetricName.DOCUMENTATION_QUALITY,
    "documentation": MetricName.DOCUMENTATION_QUALITY,
    "Documentation Quality": MetricName.DOCUMENTATION_QUALITY,
    "documentation quality": MetricName.DOCUMENTATION_QUALITY,
    "Code Documentation": MetricName.DOCUMENTATION_QUALITY,
    # Commit variations
    "Commit Quality": MetricName.COMMIT_DISCIPLINE,
    "commit quality": MetricName.COMMIT_DISCIPLINE,
    "Commit Discipline": MetricName.COMMIT_DISCIPLINE,
    "commit discipline": MetricName.COMMIT_DISCIPLINE,
    "Commit Message Quality": MetricName.COMMIT_MESSAGE_QUALITY,
    # CI/CD variations
    "CI/CD": MetricName.CONTINUOUS_INTEGRATION,
    "ci/cd": MetricName.CONTINUOUS_INTEGRATION,
    "Continuous Integration": MetricName.CONTINUOUS_INTEGRATION,
    "continuous integration": MetricName.CONTINUOUS_INTEGRATION,
    "CI/CD Integration": MetricName.CI_CD_INTEGRATION,
    # Collaboration variations
    "Collaboration": MetricName.COLLABORATION_EFFECTIVENESS,
    "collaboration": MetricName.COLLABORATION_EFFECTIVENESS,
    "Collaboration Engagement": MetricName.COLLABORATIVE_ENGAGEMENT,
    "collaboration engagement": MetricName.COLLABORATIVE_ENGAGEMENT,
    "Team Collaboration": MetricName.COLLABORATION_EFFECTIVENESS,
    # Communication variations
    "Communication": MetricName.COMMUNICATION_CLARITY,
    "communication": MetricName.COMMUNICATION_CLARITY,
    "Clarity of Communication": MetricName.COMMUNICATION_CLARITY,
    "clarity of communication": MetricName.COMMUNICATION_CLARITY,
    "Communication Skills": MetricName.COMMUNICATION_CLARITY,
    # Problem solving variations
    "Problem Solving": MetricName.PROBLEM_SOLVING,
    "problem solving": MetricName.PROBLEM_SOLVING,
    "Problem-Solving": MetricName.PROBLEM_SOLVING,
    "problem-solving": MetricName.PROBLEM_SOLVING,
    "Bug Fixing": MetricName.BUG_FIXING,
    # Consistency variations
    "Consistency": MetricName.CONSISTENCY_SCORE,
    "consistency": MetricName.CONSISTENCY_SCORE,
    "Work Consistency": MetricName.CONSISTENCY_SCORE,
    "work consistency": MetricName.CONSISTENCY_SCORE,
    "Commit Consistency": MetricName.COMMIT_DISCIPLINE,
    "Commit Frequency": MetricName.CONSISTENCY_SCORE,
    "commit frequency": MetricName.CONSISTENCY_SCORE,
    # Growth variations
    "Skill Progression": MetricName.CONTINUOUS_IMPROVEMENT,
    "skill progression": MetricName.CONTINUOUS_IMPROVEMENT,
    "Learning": MetricName.CONTINUOUS_IMPROVEMENT,
    "learning": MetricName.CONTINUOUS_IMPROVEMENT,
    "Growth": MetricName.CONTINUOUS_IMPROVEMENT,
    # Additional common variations
    "Activity Trend": MetricName.CONSISTENCY_SCORE,
    "activity trend": MetricName.CONSISTENCY_SCORE,
    "Issue Tracking": MetricName.ISSUE_TRACKING,
    "issue tracking": MetricName.ISSUE_TRACKING,
    "Security": MetricName.SECURITY_AWARENESS,
    "security": MetricName.SECURITY_AWARENESS,
    "Refactoring": MetricName.REFACTORING_ACTIVITY,
    "refactoring": MetricName.REFACTORING_ACTIVITY,
}


def normalize_metric_name(name: str) -> str:
    """
    Normalize a metric name to match our standard format.
    Uses synonym mapping to handle AI-generated variations.
    """
    # First check if it's already a known synonym
    if name in METRIC_SYNONYMS:
        return METRIC_SYNONYMS[name].value

    # Try lowercase version
    lower_name = name.lower()
    if lower_name in METRIC_SYNONYMS:
        return METRIC_SYNONYMS[lower_name].value

    # Try with underscores
    normalized = name.lower().replace(" ", "_").replace("-", "_")
    if normalized in METRIC_SYNONYMS:
        return METRIC_SYNONYMS[normalized].value

    # Try to find a matching metric enum directly
    for metric in MetricName:
        if metric.value == normalized:
            return metric.value

    # Log warning for unknown metric (but don't fail)
    # Return the normalized version as fallback
    return normalized
