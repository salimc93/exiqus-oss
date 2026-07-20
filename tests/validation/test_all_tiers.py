#!/usr/bin/env python3
"""
Test all tiers with selected contexts and repos.
More focused than the comprehensive test but still thorough.
"""

import time
from datetime import datetime
from pathlib import Path

from test_utils import (
    CONTEXT_CONFIGS,
    TEST_REPOS,
    TIER_CONFIGS,
    ValidationResult,
    format_validation_report,
    initialize_components,
    validate_confidence,
    validate_metrics,
    validate_questions,
)


def test_tier_with_context(
    tier: str, context_name: str, repo_type: str, repo_url: str, components: dict
) -> ValidationResult:
    """Test a specific tier/context/repo combination."""

    print(
        f"\n🧪 Testing {tier.upper()} tier with {context_name} context on {repo_type}..."
    )

    tier_config = TIER_CONFIGS[tier]
    context_enum = CONTEXT_CONFIGS[context_name]

    start_time = time.time()
    issues = []

    try:
        # Fetch and analyze
        print("   📥 Fetching repository data...")
        repo_data = components["github_fetcher"].fetch_repository_data(repo_url)

        print("   🔍 Extracting evidence...")
        evidence = components["evidence_extractor"].extract_all_evidence(repo_data)

        print("   📊 Running analysis...")
        classification = components["classifier"].classify_repository(repo_data)
        context_assessment = components["context_analyzer"].analyze(
            repo_data, context_enum
        )
        confidence_analysis = components["confidence_scorer"].score_confidence_and_risk(
            repo_data, classification, context_assessment
        )

        # Generate questions
        print("   ❓ Generating questions...")
        questions = components["question_builder"].generate_questions(
            evidence=evidence, context=context_name, tier=tier
        )

        # Generate report
        print("   📝 Generating report...")
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
        metrics = []
        if hasattr(report, "technical_assessment") and report.technical_assessment:
            metrics = report.technical_assessment.sub_metrics
            metrics_valid, metrics_issues = validate_metrics(
                metrics, tier_config["expected_metrics"], tier
            )
            issues.extend(metrics_issues)
            print(f"   📊 Metrics: {len(metrics)} generated")
        else:
            issues.append("No technical assessment generated")
            print("   ❌ No metrics generated")

        # Validate questions
        all_questions = questions.get("all_questions", [])
        questions_valid, questions_issues = validate_questions(
            questions, tier_config, tier
        )
        issues.extend(questions_issues)
        print(f"   ❓ Questions: {len(all_questions)} generated")

        # Validate confidence
        confidence = confidence_analysis.confidence_breakdown.overall_confidence
        conf_valid, conf_issues = validate_confidence(confidence)
        issues.extend(conf_issues)
        print(f"   🎯 Confidence: {confidence:.1%}")

        # Check green/red flags for GROWTH/SCALE
        has_green_flags = False
        has_red_flags = False
        if tier in ["growth", "scale"]:
            visible_questions = [
                q for q in all_questions if not q.get("is_blurred", False)
            ]
            has_green_flags = all(
                "green_flags" in q and q["green_flags"] for q in visible_questions
            )
            has_red_flags = all(
                "red_flags" in q and q["red_flags"] for q in visible_questions
            )

            if not has_green_flags:
                issues.append("Missing green flags on some questions")
            if not has_red_flags:
                issues.append("Missing red flags on some questions")

        result = ValidationResult(
            tier=tier,
            context=context_name,
            repo=repo_type,
            passed=len(issues) == 0,
            issues=issues,
            metrics_count=len(metrics),
            questions_count=len(all_questions),
            has_green_flags=has_green_flags,
            has_red_flags=has_red_flags,
            confidence_score=confidence,
            generation_time=generation_time,
        )

        if result.passed:
            print(f"   ✅ PASSED in {generation_time:.1f}s")
        else:
            print(f"   ❌ FAILED with {len(issues)} issues:")
            for issue in issues[:3]:
                print(f"      - {issue}")
            if len(issues) > 3:
                print(f"      ... and {len(issues) - 3} more")

        return result

    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        import traceback

        traceback.print_exc()

        return ValidationResult(
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


def run_focused_validation():
    """Run a focused validation test covering key scenarios."""

    print("🔬 FOCUSED TIER VALIDATION TEST")
    print("=" * 60)
    print("Testing key tier/context/repo combinations\n")

    components = initialize_components()
    results = []

    # Define focused test scenarios
    test_scenarios = [
        # FREE tier - test with different contexts
        ("free", "startup", "library", TEST_REPOS["library"]),
        ("free", "enterprise", "web_framework", TEST_REPOS["web_framework"]),
        # STARTER tier - basic professional use
        ("starter", "startup", "library", TEST_REPOS["library"]),
        ("starter", "agency", "api_framework", TEST_REPOS["api_framework"]),
        # GROWTH tier - professional teams
        ("growth", "startup", "web_framework", TEST_REPOS["web_framework"]),
        ("growth", "enterprise", "cli_tool", TEST_REPOS["cli_tool"]),
        ("growth", "open_source", "open_source", TEST_REPOS["open_source"]),
        # SCALE tier - enterprise needs
        ("scale", "enterprise", "web_framework", TEST_REPOS["web_framework"]),
        ("scale", "startup", "api_framework", TEST_REPOS["api_framework"]),
        ("scale", "open_source", "open_source", TEST_REPOS["open_source"]),
    ]

    # Run tests
    for tier, context, repo_type, repo_url in test_scenarios:
        result = test_tier_with_context(tier, context, repo_type, repo_url, components)
        results.append(result)

    # Generate summary report
    print("\n" + "=" * 60)
    print("📊 VALIDATION SUMMARY")
    print("=" * 60)

    # Overall stats
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    print(f"\nOverall: {passed}/{total} passed ({(passed/total)*100:.1f}%)")

    # By tier
    for tier in ["free", "starter", "growth", "scale"]:
        tier_results = [r for r in results if r.tier == tier]
        if tier_results:
            tier_passed = sum(1 for r in tier_results if r.passed)
            print(f"\n{tier.upper()}: {tier_passed}/{len(tier_results)} passed")

            # Show common issues for failed tests
            tier_issues = []
            for r in tier_results:
                if not r.passed:
                    tier_issues.extend(r.issues)

            if tier_issues:
                print("   Common issues:")
                issue_counts = {}
                for issue in tier_issues:
                    # Group similar issues
                    if "Wrong total questions:" in issue:
                        key = "Wrong question count"
                    elif "missing green flags" in issue:
                        key = "Missing green flags"
                    elif "missing red flags" in issue:
                        key = "Missing red flags"
                    else:
                        key = issue
                    issue_counts[key] = issue_counts.get(key, 0) + 1

                for issue, count in sorted(
                    issue_counts.items(), key=lambda x: x[1], reverse=True
                )[:3]:
                    print(f"   - {issue} (×{count})")

    # Save detailed report
    report = format_validation_report(results)
    report_path = Path(
        f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    )
    report_path.write_text(report)
    print(f"\n📄 Detailed report saved to: {report_path}")

    return results


if __name__ == "__main__":
    results = run_focused_validation()

    # Exit with error code if any tests failed
    import sys

    if any(not r.passed for r in results):
        sys.exit(1)
