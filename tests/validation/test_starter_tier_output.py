#!/usr/bin/env python3
"""
Test STARTER tier - shows exact user output
"""

import time

from test_utils import CONTEXT_CONFIGS, TEST_REPOS, TIER_CONFIGS, initialize_components


def test_starter_tier():
    """Test STARTER tier ($97/month) with actual user output."""

    print("💼 STARTER TIER TEST - $97/month")
    print("=" * 80)
    print("Shows: Basic metrics, 7 questions, green/red flags on top 3\n")

    # Test configuration
    tier = "starter"
    context_name = "startup"
    repo_url = TEST_REPOS["web_framework"]  # Using Next.js

    tier_config = TIER_CONFIGS[tier]
    context_enum = CONTEXT_CONFIGS[context_name]

    components = initialize_components()
    start_time = time.time()

    try:
        # Fetch and analyze
        print("🔍 Analyzing repository:", repo_url)
        print("📋 Context: Startup hiring\n")

        repo_data = components["github_fetcher"].fetch_repository_data(repo_url)
        evidence = components["evidence_extractor"].extract_all_evidence(repo_data)
        classification = components["classifier"].classify_repository(repo_data)
        context_assessment = components["context_analyzer"].analyze(
            repo_data, context_enum
        )
        confidence_analysis = components["confidence_scorer"].score_confidence_and_risk(
            repo_data, classification, context_assessment
        )

        # Generate questions
        questions = components["question_builder"].generate_questions(
            evidence=evidence, context=context_name, tier="basic"  # STARTER tier
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

        # Display results as user would see them
        print("=" * 80)
        print("📊 ANALYSIS RESULTS - STARTER TIER")
        print("=" * 80)

        print(f"\n⏱️  Analysis completed in: {generation_time:.1f} seconds")
        print(
            f"🎯 Overall Confidence: {confidence_analysis.confidence_breakdown.overall_confidence:.1%} ± 10%"
        )
        print(f"📈 Context Fit Score: {report.context_fit_score:.1%}")

        # Display metrics
        print("\n📊 METRICS BREAKDOWN:")
        print("-" * 40)

        sections = [
            ("Technical Skills", report.technical_assessment),
            ("Professional Practices", report.professional_practices),
            ("Communication", report.communication_skills),
            ("Growth Indicators", report.growth_indicators),
        ]

        total_metrics = 0
        for section_name, section in sections:
            if section and hasattr(section, "sub_metrics") and section.sub_metrics:
                print(f"\n{section_name}:")
                for metric in section.sub_metrics:
                    print(f"  • {metric.name}: {metric.percentage}% ± 10%")
                    print(f"    Evidence: {metric.evidence[:60]}...")
                total_metrics += len(section.sub_metrics)

        print(f"\nTotal metrics: {total_metrics}")

        # Display questions
        print("\n❓ INTERVIEW QUESTIONS:")
        print("-" * 40)

        all_questions = questions.get("all_questions", [])
        for i, q in enumerate(all_questions[:7], 1):  # Show all 7 questions
            print(f"\nQuestion {i}: [{q.get('category', 'general')}]")
            print(f"Q: {q.get('question', 'N/A')}")

            # Only top 3 have flags for STARTER
            if i <= 3:
                if q.get("green_flags"):
                    print(f"✅ Green flags: {', '.join(q['green_flags'][:2])}")
                if q.get("red_flags"):
                    print(f"🚩 Red flags: {', '.join(q['red_flags'][:2])}")

        # Display summary insights
        print("\n💡 KEY INSIGHTS:")
        print("-" * 40)
        print(f"Executive Summary: {report.executive_summary[:200]}...")
        print(f"\nStrengths: {', '.join(report.key_strengths[:3])}")
        print(f"Concerns: {', '.join(report.primary_concerns[:3])}")

        print("\n✅ Test completed successfully")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_starter_tier()
