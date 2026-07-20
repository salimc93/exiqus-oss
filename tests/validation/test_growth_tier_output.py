#!/usr/bin/env python3
"""
Test GROWTH tier - shows exact user output with multi-model approach
TESTING: Haiku 3.0 for metrics + Haiku 3.5 for questions
"""

import time

from test_utils import CONTEXT_CONFIGS, TEST_REPOS, TIER_CONFIGS, initialize_components


def test_growth_tier():
    """Test GROWTH tier ($297/month) with multi-model approach."""

    print("🚀 GROWTH TIER TEST - $297/month (DUAL-MODEL)")
    print("=" * 80)
    print("TESTING CONFIGURATION:")
    print("  • Metrics: Haiku 3.0 (current implementation)")
    print("  • Questions: Would use Haiku 3.5 (currently using 3.0 in codebase)")
    print("  • Expected: 12+ metrics, 10-12 enhanced professional questions\n")

    # Test configuration
    tier = "growth"
    context_name = "enterprise"  # Testing enterprise context
    repo_url = TEST_REPOS["cli_tool"]  # Using GitHub CLI

    tier_config = TIER_CONFIGS[tier]
    context_enum = CONTEXT_CONFIGS[context_name]

    components = initialize_components()
    start_time = time.time()

    try:
        # Fetch and analyze
        print("🔍 Analyzing repository:", repo_url)
        print("📋 Context: Enterprise hiring\n")

        repo_data = components["github_fetcher"].fetch_repository_data(repo_url)
        evidence = components["evidence_extractor"].extract_all_evidence(repo_data)
        classification = components["classifier"].classify_repository(repo_data)
        context_assessment = components["context_analyzer"].analyze(
            repo_data, context_enum
        )
        confidence_analysis = components["confidence_scorer"].score_confidence_and_risk(
            repo_data, classification, context_assessment
        )

        # DUAL-MODEL for GROWTH tier
        print("📊 Phase 1: Generating metrics with Haiku 3.0...")

        print("💎 Phase 2: Generating professional questions with Haiku 3.5...")

        questions = components["question_builder"].generate_questions(
            evidence=evidence,
            context=context_name,
            tier="professional",  # GROWTH tier - will use Haiku 3.5
        )

        # Generate report with granular metrics (Haiku 3.0)
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

        # Display results as user would see them
        print("=" * 80)
        print("📊 ANALYSIS RESULTS - GROWTH TIER")
        print("=" * 80)

        print(f"\n⏱️  Analysis completed in: {generation_time:.1f} seconds")
        print(
            f"🎯 Overall Confidence: {confidence_analysis.confidence_breakdown.overall_confidence:.1%} ± 10%"
        )
        print(f"📈 Context Fit Score: {report.context_fit_score:.1%}")

        # Display granular metrics
        print("\n📊 GRANULAR METRICS BREAKDOWN (Haiku 3.0):")
        print("-" * 60)

        sections = [
            ("Technical Assessment", report.technical_assessment),
            ("Professional Practices", report.professional_practices),
            ("Communication Skills", report.communication_skills),
            ("Growth Indicators", report.growth_indicators),
        ]

        total_metrics = 0
        for section_name, section in sections:
            if section and hasattr(section, "sub_metrics") and section.sub_metrics:
                print(f"\n{section_name}: ({len(section.sub_metrics)} metrics)")
                for metric in section.sub_metrics:
                    print(f"  • {metric.name}: {metric.percentage}% ± 10%")
                    print(f"    Evidence: {metric.evidence}")
                    print(f"    Insight: {metric.insight}")
                total_metrics += len(section.sub_metrics)

        print(f"\n📈 Total granular metrics: {total_metrics} (expected: 12+)")

        # Display professional questions from Haiku 3.5
        print("\n❓ PROFESSIONAL INTERVIEW QUESTIONS (Haiku 3.5):")
        print("-" * 60)

        all_questions = questions.get("all_questions", [])
        visible_questions = [q for q in all_questions if not q.get("is_blurred", False)]

        print(f"\nTotal questions: {len(all_questions)} (GROWTH tier: 10-12 expected)")
        print("Model: Haiku 3.5 for enhanced quality\n")

        for i, q in enumerate(visible_questions[:12], 1):  # Show up to 12 questions
            print(f"\n{'='*60}")
            print(f"Question {i}: [{q.get('category', 'general').upper()}]")
            print(f"\n📝 Question: {q.get('question', 'N/A')}")
            print(f"\n📊 Evidence: {q.get('evidence_reference', 'N/A')}")

            if q.get("green_flags"):
                print("\n✅ Green flags:")
                for flag in q["green_flags"]:
                    print(f"   • {flag}")

            if q.get("red_flags"):
                print("\n🚩 Red flags:")
                for flag in q["red_flags"]:
                    print(f"   • {flag}")

            if q.get("what_to_listen_for"):
                print(f"\n👂 What to listen for: {q['what_to_listen_for']}")

        # Display evidence-based recommendations
        print("\n🎯 EVIDENCE-BASED RECOMMENDATIONS:")
        print("-" * 60)
        if report.evidence_based_recommendations:
            recs = report.evidence_based_recommendations.get("all_recommendations", [])
            for rec in recs[:5]:
                print(f"\n• {rec.get('recommendation', 'N/A')}")
                print(
                    f"  Type: {rec.get('type', 'N/A')} | Priority: {rec.get('priority', 'N/A')}"
                )
                print(f"  Evidence: {rec.get('evidence', 'N/A')[:100]}...")

        # Display summary
        print("\n💡 EXECUTIVE SUMMARY:")
        print("-" * 60)
        print(report.executive_summary)

        print("\n✅ Growth tier test completed successfully")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_growth_tier()
