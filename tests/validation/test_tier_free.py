#!/usr/bin/env python3
"""
Test FREE tier across all contexts.
"""

import time
from datetime import datetime

from test_utils import (
    CONTEXT_CONFIGS,
    TEST_REPOS,
    TIER_CONFIGS,
    ValidationResult,
    initialize_components,
    validate_confidence,
    validate_metrics,
    validate_questions,
)


def test_free_tier():
    """Test FREE tier with all contexts and repos."""

    print("🆓 TESTING FREE TIER")
    print("=" * 60)

    tier = "free"
    tier_config = TIER_CONFIGS[tier]
    components = initialize_components()
    results = []

    # Test each repository with startup context (most common for FREE)
    for repo_type, repo_url in TEST_REPOS.items():
        for context_name, context_enum in CONTEXT_CONFIGS.items():
            print(f"\n📦 Testing {repo_type} with {context_name} context...")

            start_time = time.time()
            issues = []

            try:
                # Fetch and analyze
                repo_data = components["github_fetcher"].fetch_repository_data(repo_url)
                evidence = components["evidence_extractor"].extract_all_evidence(
                    repo_data
                )
                classification = components["classifier"].classify_repository(repo_data)
                context_assessment = components["context_analyzer"].analyze(
                    repo_data, context_enum
                )
                confidence_analysis = components[
                    "confidence_scorer"
                ].score_confidence_and_risk(
                    repo_data, classification, context_assessment
                )

                # Generate questions
                questions = components["question_builder"].generate_questions(
                    evidence=evidence, context=context_name, tier=tier
                )

                # Generate report
                report = components["report_generator"].generate_report(
                    repo_data,
                    classification,
                    context_assessment,
                    context_enum,
                    confidence_analysis,
                    None,
                    tier_config["plan"],
                )

                generation_time = time.time() - start_time

                # Validate metrics
                if (
                    hasattr(report, "technical_assessment")
                    and report.technical_assessment
                ):
                    metrics = report.technical_assessment.sub_metrics
                    metrics_valid, metrics_issues = validate_metrics(
                        metrics, tier_config["expected_metrics"], tier
                    )
                    issues.extend(metrics_issues)
                else:
                    issues.append("No technical assessment generated")
                    metrics = []

                # Validate questions
                questions_valid, questions_issues = validate_questions(
                    questions, tier_config, tier
                )
                issues.extend(questions_issues)

                # Special FREE tier validation
                all_questions = questions.get("all_questions", [])
                blurred_count = len(
                    [q for q in all_questions if q.get("is_blurred", False)]
                )
                if blurred_count != 4:
                    issues.append(f"Wrong blurred count: {blurred_count} != 4")

                # Validate confidence
                confidence = confidence_analysis.confidence_breakdown.overall_confidence
                conf_valid, conf_issues = validate_confidence(confidence)
                issues.extend(conf_issues)

                # Check that FREE tier shows basic analysis only
                if hasattr(report, "ai_insights") and report.ai_insights:
                    issues.append("FREE tier should not have AI insights")

                result = ValidationResult(
                    tier=tier,
                    context=context_name,
                    repo=repo_type,
                    passed=len(issues) == 0,
                    issues=issues,
                    metrics_count=len(metrics),
                    questions_count=len(all_questions),
                    has_green_flags=False,  # FREE tier shouldn't have flags
                    has_red_flags=False,
                    confidence_score=confidence,
                    generation_time=generation_time,
                )

                results.append(result)

                if result.passed:
                    print(f"   ✅ Passed in {generation_time:.1f}s")
                else:
                    print(f"   ❌ Failed with {len(issues)} issues:")
                    for issue in issues[:3]:  # Show first 3 issues
                        print(f"      - {issue}")
                    if len(issues) > 3:
                        print(f"      ... and {len(issues) - 3} more")

            except Exception as e:
                print(f"   ❌ Error: {e}")
                results.append(
                    ValidationResult(
                        tier=tier,
                        context=context_name,
                        repo=repo_type,
                        passed=False,
                        issues=[f"Exception: {str(e)}"],
                        metrics_count=0,
                        questions_count=0,
                        has_green_flags=False,
                        has_red_flags=False,
                        confidence_score=0.0,
                        generation_time=time.time() - start_time,
                    )
                )

    # Summary
    passed = sum(1 for r in results if r.passed)
    print("\n📊 FREE Tier Summary:")
    print(f"   Total tests: {len(results)}")
    print(f"   Passed: {passed}")
    print(f"   Failed: {len(results) - passed}")
    print(f"   Success rate: {(passed/len(results))*100:.1f}%")

    # Common issues
    all_issues = []
    for r in results:
        all_issues.extend(r.issues)

    if all_issues:
        print("\n❌ Common Issues:")
        issue_counts = {}
        for issue in all_issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1

        for issue, count in sorted(
            issue_counts.items(), key=lambda x: x[1], reverse=True
        )[:5]:
            print(f"   - {issue} (×{count})")

    return results


if __name__ == "__main__":
    results = test_free_tier()

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"free_tier_results_{timestamp}.txt", "w") as f:
        for r in results:
            f.write(f"{r.tier},{r.context},{r.repo},{r.passed},{len(r.issues)}\n")
