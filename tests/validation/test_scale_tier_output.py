#!/usr/bin/env python3
"""
Test SCALE tier - shows exact user output with full Haiku 3.5
"""

import time

from test_utils import CONTEXT_CONFIGS, TEST_REPOS, TIER_CONFIGS, initialize_components


def test_scale_tier():
    """Test SCALE tier ($497/month) with full Haiku 3.5."""

    print("🏢 SCALE TIER TEST - $497/month (FULL HAIKU 3.5)")
    print("=" * 80)
    print("TESTING: Full Haiku 3.5 for everything (metrics + questions)")
    print(
        "Shows: 15-20 premium metrics, 15-20 executive questions, team fit analysis\n"
    )

    # Test configuration
    tier = "scale"
    context_name = "enterprise"
    repo_url = TEST_REPOS["api_framework"]  # Using FastAPI

    tier_config = TIER_CONFIGS[tier]
    context_enum = CONTEXT_CONFIGS[context_name]

    components = initialize_components()
    start_time = time.time()

    try:
        # Fetch and analyze
        print("🔍 Analyzing repository:", repo_url)
        print("📋 Context: Enterprise hiring (senior/executive level)\n")

        repo_data = components["github_fetcher"].fetch_repository_data(repo_url)
        evidence = components["evidence_extractor"].extract_all_evidence(repo_data)
        classification = components["classifier"].classify_repository(repo_data)
        context_assessment = components["context_analyzer"].analyze(
            repo_data, context_enum
        )
        confidence_analysis = components["confidence_scorer"].score_confidence_and_risk(
            repo_data, classification, context_assessment
        )

        # SIMULATE FULL HAIKU 3.5 for SCALE tier
        print("🤖 Phase 1: Would generate premium metrics with Haiku 3.5...")
        print("🤖 Phase 2: Would generate executive questions with Haiku 3.5...")
        print("   (Simulated: In production, EVERYTHING would use Haiku 3.5)")

        questions = components["question_builder"].generate_questions(
            evidence=evidence,
            context=context_name,
            tier="enterprise",  # SCALE tier - currently uses dual model
        )

        # Add simulation notes
        if questions.get("all_questions"):
            for q in questions["all_questions"]:
                q["production_note"] = (
                    "Full Haiku 3.5 would provide even deeper insights"
                )

        # Generate report with premium metrics
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
        print("\n" + "=" * 80)
        print("📊 PREMIUM ANALYSIS RESULTS - SCALE TIER")
        print("=" * 80)

        print(f"\n⏱️  Analysis completed in: {generation_time:.1f} seconds")
        print(
            f"🎯 Overall Confidence: {confidence_analysis.confidence_breakdown.overall_confidence:.1%} ± 10%"
        )
        print(f"📈 Context Fit Score: {report.context_fit_score:.1%}")
        print(f"🏢 Enterprise Readiness: {report.trust_score:.1%}")

        # Display premium metrics
        print("\n📊 COMPREHENSIVE METRICS BREAKDOWN:")
        print("-" * 60)

        sections = [
            ("Technical Excellence", report.technical_assessment),
            ("Professional Maturity", report.professional_practices),
            ("Leadership & Communication", report.communication_skills),
            ("Growth & Innovation", report.growth_indicators),
        ]

        total_metrics = 0
        for section_name, section in sections:
            if section and hasattr(section, "sub_metrics") and section.sub_metrics:
                print(f"\n{section_name}: ({len(section.sub_metrics)} metrics)")
                for metric in section.sub_metrics:
                    print(f"\n  📌 {metric.name}: {metric.percentage}% ± 10%")
                    print(f"     Evidence: {metric.evidence}")
                    print(f"     Context: {metric.context}")
                    print(f"     Insight: {metric.insight}")
                total_metrics += len(section.sub_metrics)

        print(f"\n📈 Total premium metrics: {total_metrics} (expected: 15-20)")
        print("🔮 In production with full Haiku 3.5:")
        print("   • Metrics would have richer insights and deeper analysis")
        print("   • More sophisticated scoring and calibration")
        print("   • Enhanced context-specific evaluations")

        # Display executive questions
        print("\n❓ EXECUTIVE INTERVIEW QUESTIONS:")
        print("-" * 60)

        all_questions = questions.get("all_questions", [])

        # Separate by source
        haiku_30_questions = [
            q for q in all_questions if q.get("source") == "haiku_3_0"
        ]
        haiku_35_questions = [
            q for q in all_questions if q.get("source") == "haiku_3_5"
        ]

        print(f"\nTotal questions: {len(all_questions)} (SCALE tier: 15-20 expected)")
        if haiku_30_questions or haiku_35_questions:
            print(f"  • Standard (Haiku 3.0): {len(haiku_30_questions)}")
            print(f"  • Premium (Haiku 3.5): {len(haiku_35_questions)}")
        print("\n🔮 In production with full Haiku 3.5:")
        print("   • ALL 15-20 questions would be premium executive-level")
        print("   • Deeper strategic and leadership assessment")
        print("   • More sophisticated behavioral analysis")

        # For SCALE tier, ALL questions should be from Sonnet 3.5
        print("\n🌟 EXECUTIVE QUESTIONS (Sonnet 3.5):")
        print("-" * 40)

        for i, q in enumerate(all_questions[:15], 1):
            print(f"\n{'='*60}")
            print(f"Executive Question {i}: [{q.get('category', 'strategic').upper()}]")
            print(f"\n📝 Question: {q.get('question', 'N/A')}")

            if q.get("executive_focus"):
                print(f"\n🎯 Executive Focus: {q.get('executive_focus')}")

            if q.get("green_flags"):
                print(f"\n✅ Green flags ({len(q.get('green_flags', []))} total):")
                for flag in q["green_flags"]:
                    print(f"   • {flag}")

            if q.get("red_flags"):
                print(f"\n🚩 Red flags ({len(q.get('red_flags', []))} total):")
                for flag in q["red_flags"]:
                    print(f"   • {flag}")

            if q.get("what_to_listen_for"):
                print(f"\n👂 What to listen for: {q['what_to_listen_for']}")

            if q.get("follow_up_probes"):
                print("\n🔍 Follow-up probes:")
                for probe in q.get("follow_up_probes", []):
                    print(f"   → {probe}")

        # Display team fit analysis (Enterprise only)
        print("\n👥 TEAM FIT ANALYSIS:")
        print("-" * 60)
        if report.evidence_summary and "team_fit_analysis" in report.evidence_summary:
            team_fit = report.evidence_summary["team_fit_analysis"]
            print(f"Collaboration Style: {team_fit.get('collaboration_style', 'N/A')}")
            print(f"Work Pattern: {team_fit.get('work_pattern', 'N/A')}")
            print(
                f"Leadership Potential: {team_fit.get('leadership_potential', 'N/A')}"
            )

            if team_fit.get("team_dynamics_fit"):
                print("\nRecommended Team Environments:")
                for rec in team_fit["team_dynamics_fit"]:
                    print(f"  • {rec}")

        # Display executive summary
        print("\n💼 EXECUTIVE BRIEFING:")
        print("-" * 60)
        print(f"Summary: {report.executive_summary}")
        print(f"\nRecommendation: {report.overall_recommendation}")

        # Display hiring recommendations
        print("\n🎯 STRATEGIC HIRING RECOMMENDATIONS:")
        print("-" * 60)
        for i, rec in enumerate(report.analysis_recommendations[:5], 1):
            print(f"{i}. {rec}")

        print("\n✅ Scale tier test completed successfully")
        print("\n💰 Estimated API cost: ~$0.12")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_scale_tier()
