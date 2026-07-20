"""
Shared utilities for validation tests.
"""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from github_analyzer.core.classifier import RepositoryClassifier  # noqa: E402
from github_analyzer.core.confidence_scorer import ConfidenceRiskAssessor  # noqa: E402
from github_analyzer.core.context_analyzer import (  # noqa: E402
    AnalysisContext,
    ContextAnalyzer,
)
from github_analyzer.core.evidence.evidence_extractor import (  # noqa: E402
    EvidenceExtractor,
)
from github_analyzer.core.evidence.question_builder import QuestionBuilder  # noqa: E402
from github_analyzer.core.report_generator import ReportGenerator  # noqa: E402
from github_analyzer.data.github_fetcher import GitHubFetcher  # noqa: E402
from github_analyzer.database.models import SubscriptionPlan  # noqa: E402
from github_analyzer.utils.config import get_config  # noqa: E402


@dataclass
class ValidationResult:
    """Track validation results."""

    tier: str
    context: str
    repo: str
    passed: bool
    issues: List[str]
    metrics_count: int
    questions_count: int
    has_green_flags: bool
    has_red_flags: bool
    confidence_score: float
    generation_time: float


# Test repositories with diverse characteristics
TEST_REPOS = {
    "library": "https://github.com/sindresorhus/p-queue",  # Small, focused
    "web_framework": "https://github.com/vercel/next.js",  # Large, complex
    "cli_tool": "https://github.com/cli/cli",  # Enterprise tool
    "api_framework": "https://github.com/fastapi/fastapi",  # Well-documented
    "open_source": "https://github.com/microsoft/vscode",  # Community-driven
}

# Tier configurations
TIER_CONFIGS = {
    "free": {
        "plan": SubscriptionPlan.FREE,
        "expected_questions": 7,
        "visible_questions": 3,
        "expected_metrics": 2,
        "has_flags": False,
    },
    "starter": {
        "plan": SubscriptionPlan.BASIC,
        "expected_questions": 7,
        "visible_questions": 7,
        "expected_metrics": 5,
        "has_flags": True,  # Only top 3
    },
    "growth": {
        "plan": SubscriptionPlan.PROFESSIONAL,
        "expected_questions": 10,
        "visible_questions": 10,
        "expected_metrics": 12,
        "has_flags": True,
    },
    "scale": {
        "plan": SubscriptionPlan.ENTERPRISE,
        "expected_questions": 15,
        "visible_questions": 15,
        "expected_metrics": 15,
        "has_flags": True,
    },
}

# Context configurations
CONTEXT_CONFIGS = {
    "startup": AnalysisContext.STARTUP,
    "enterprise": AnalysisContext.ENTERPRISE,
    "agency": AnalysisContext.AGENCY,
    "open_source": AnalysisContext.OPEN_SOURCE,
}


def initialize_components():
    """Initialize all required components."""
    config = get_config()

    return {
        "github_fetcher": GitHubFetcher(config.github_token),
        "evidence_extractor": EvidenceExtractor(),
        "classifier": RepositoryClassifier(),
        "context_analyzer": ContextAnalyzer(),
        "confidence_scorer": ConfidenceRiskAssessor(),
        "question_builder": QuestionBuilder(config.anthropic_api_key),
        "report_generator": ReportGenerator(config.anthropic_api_key),
    }


def validate_metrics(
    metrics: List[Any], expected_count: int, tier: str
) -> Tuple[bool, List[str]]:
    """Validate metrics for a tier."""
    issues = []

    # Check count
    if len(metrics) < expected_count:
        issues.append(f"Insufficient metrics: {len(metrics)} < {expected_count}")

    # Check percentage scores
    for metric in metrics:
        score = metric.score * 100 if hasattr(metric, "score") else 0
        if not (0 <= score <= 100):
            issues.append(f"Invalid score for {metric.name}: {score}%")

        # Check for the display bug (5% instead of 50%)
        if score < 10 and score != 0:
            issues.append(f"Possible display bug for {metric.name}: {score}%")

    return len(issues) == 0, issues


def validate_questions(
    questions: Dict[str, Any], tier_config: Dict, tier: str
) -> Tuple[bool, List[str]]:
    """Validate questions for a tier."""
    issues = []

    all_questions = questions.get("all_questions", [])
    visible_questions = [q for q in all_questions if not q.get("is_blurred", False)]

    # Check total count
    if len(all_questions) != tier_config["expected_questions"]:
        issues.append(
            f"Wrong total questions: {len(all_questions)} != {tier_config['expected_questions']}"
        )

    # Check visible count
    if len(visible_questions) != tier_config["visible_questions"]:
        issues.append(
            f"Wrong visible questions: {len(visible_questions)} != {tier_config['visible_questions']}"
        )

    # Check flags for GROWTH/SCALE
    if tier_config["has_flags"] and tier in ["growth", "scale"]:
        for i, q in enumerate(visible_questions):
            if "green_flags" not in q or not q["green_flags"]:
                issues.append(f"Question {i+1} missing green flags")
            if "red_flags" not in q or not q["red_flags"]:
                issues.append(f"Question {i+1} missing red flags")
            if "what_to_listen_for" not in q:
                issues.append(f"Question {i+1} missing listen-for guidance")

    return len(issues) == 0, issues


def validate_confidence(confidence_score: float) -> Tuple[bool, List[str]]:
    """Validate confidence score alignment with methodology."""
    issues = []

    # Mixed assessment range: 52.5-77.5% ± 10%
    min_expected = 0.425  # 42.5%
    max_expected = 0.875  # 87.5%

    if not (min_expected <= confidence_score <= max_expected):
        issues.append(
            f"Confidence {confidence_score:.1%} outside methodology range {min_expected:.1%}-{max_expected:.1%}"
        )

    return len(issues) == 0, issues


def format_validation_report(results: List[ValidationResult]) -> str:
    """Format validation results into a report."""
    # total = len(results)  # TODO: Use for summary statistics
    # passed = sum(1 for r in results if r.passed)  # TODO: Use for pass rate

    report = """# Validation Report

## Summary
- Total Tests: {total}
- Passed: {passed}
- Failed: {total - passed}
- Success Rate: {(passed/total)*100:.1f}%

## Results by Tier
"""

    for tier in ["free", "starter", "growth", "scale"]:
        tier_results = [r for r in results if r.tier == tier]
        tier_passed = sum(1 for r in tier_results if r.passed)

        report += f"\n### {tier.upper()} Tier\n"
        report += f"- Tests: {len(tier_results)}\n"
        report += f"- Passed: {tier_passed}\n"
        report += f"- Success Rate: {(tier_passed/len(tier_results))*100:.1f}%\n"

        # Show issues
        all_issues = []
        for r in tier_results:
            if not r.passed:
                all_issues.extend(r.issues)

        if all_issues:
            report += "\nCommon Issues:\n"
            for issue in set(all_issues):
                count = all_issues.count(issue)
                report += f"- {issue} (×{count})\n"

    return report
