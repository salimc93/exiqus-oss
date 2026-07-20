#!/usr/bin/env python3
"""
Test a single scenario to quickly identify issues.
"""

import time

from test_utils import (
    CONTEXT_CONFIGS,
    TEST_REPOS,
    TIER_CONFIGS,
    initialize_components,
)


def test_single_scenario():
    """Test just FREE tier with startup context on library repo."""

    print("🔬 SINGLE SCENARIO TEST")
    print("=" * 60)

    # Test configuration
    tier = "free"
    context_name = "startup"
    repo_url = TEST_REPOS["library"]

    tier_config = TIER_CONFIGS[tier]
    context_enum = CONTEXT_CONFIGS[context_name]

    print(f"\nTesting {tier.upper()} tier with {context_name} context...")
    print(f"Repository: {repo_url}")

    components = initialize_components()
    start_time = time.time()
    issues = []

    try:
        # Fetch and analyze
        print("📥 Fetching repository data...")
        repo_data = components["github_fetcher"].fetch_repository_data(repo_url)

        print("🔍 Extracting evidence...")
        evidence = components["evidence_extractor"].extract_all_evidence(repo_data)

        print("📊 Running analysis...")
        classification = components["classifier"].classify_repository(repo_data)
        context_assessment = components["context_analyzer"].analyze(
            repo_data, context_enum
        )
        confidence_analysis = components["confidence_scorer"].score_confidence_and_risk(
            repo_data, classification, context_assessment
        )

        # Generate questions
        print("❓ Generating questions...")
        questions = components["question_builder"].generate_questions(
            evidence=evidence, context=context_name, tier=tier
        )

        # Generate report
        print("📝 Generating report...")
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

        # Validate results
        print("\n🔍 Validation Results:")

        # Check metrics
        if hasattr(report, "technical_assessment") and report.technical_assessment:
            metrics = report.technical_assessment.sub_metrics
            print(
                f"   Metrics: {len(metrics)} generated (expected: {tier_config['expected_metrics']})"
            )
            for m in metrics[:3]:
                print(f"      - {m.name}: {m.score * 100:.0f}%")
        else:
            print("   ❌ No metrics generated")
            issues.append("No technical assessment generated")

        # Check questions
        all_questions = questions.get("all_questions", [])
        visible_questions = [q for q in all_questions if not q.get("is_blurred", False)]
        print(
            f"   Questions: {len(all_questions)} total, {len(visible_questions)} visible"
        )
        print(
            f"   Expected: {tier_config['expected_questions']} total, {tier_config['visible_questions']} visible"
        )

        if len(all_questions) != tier_config["expected_questions"]:
            issues.append(
                f"Wrong total questions: {len(all_questions)} != {tier_config['expected_questions']}"
            )

        # Show sample questions
        if all_questions:
            print("   Sample questions:")
            for i, q in enumerate(all_questions[:3]):
                status = "visible" if not q.get("is_blurred", False) else "blurred"
                print(
                    f"      {i+1}. [{status}] {q.get('question', 'No question text')[:80]}..."
                )

        # Check confidence
        confidence = confidence_analysis.confidence_breakdown.overall_confidence
        print(f"   Confidence: {confidence:.1%}")

        # Summary
        print(f"\n⏱️  Total time: {generation_time:.1f}s")
        if issues:
            print(f"❌ Found {len(issues)} issues:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print("✅ All validations passed!")

        return len(issues) == 0

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_single_scenario()
    import sys

    sys.exit(0 if success else 1)
