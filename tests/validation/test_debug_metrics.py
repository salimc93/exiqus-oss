#!/usr/bin/env python3
"""
Debug test to understand metrics generation.
"""

import json

from test_utils import CONTEXT_CONFIGS, TEST_REPOS, TIER_CONFIGS, initialize_components


def test_debug_metrics():
    """Debug metrics generation for GROWTH tier."""

    print("🔍 DEBUG: GROWTH TIER METRICS")
    print("=" * 60)

    # Test configuration
    tier = "growth"
    context_name = "startup"
    repo_url = TEST_REPOS["library"]

    tier_config = TIER_CONFIGS[tier]
    context_enum = CONTEXT_CONFIGS[context_name]

    components = initialize_components()

    try:
        # Fetch and analyze
        print("\n1. Fetching repository...")
        repo_data = components["github_fetcher"].fetch_repository_data(repo_url)

        print("\n2. Extracting evidence...")
        components["evidence_extractor"].extract_all_evidence(repo_data)

        print("\n3. Running classification...")
        classification = components["classifier"].classify_repository(repo_data)
        context_assessment = components["context_analyzer"].analyze(
            repo_data, context_enum
        )
        confidence_analysis = components["confidence_scorer"].score_confidence_and_risk(
            repo_data, classification, context_assessment
        )

        print("\n4. Generating report...")
        report = components["report_generator"].generate_report(
            repo_data,
            classification,
            context_assessment,
            context_enum,
            confidence_analysis,
            None,
            tier_config["plan"],
        )

        # Debug output
        print("\n📊 METRICS ANALYSIS:")

        sections = [
            ("Technical Assessment", report.technical_assessment),
            ("Professional Practices", report.professional_practices),
            ("Communication Skills", report.communication_skills),
            ("Growth Indicators", report.growth_indicators),
        ]

        total_metrics = 0
        for section_name, section in sections:
            if section and hasattr(section, "sub_metrics"):
                print(f"\n{section_name}: {len(section.sub_metrics)} metrics")
                for i, metric in enumerate(section.sub_metrics, 1):
                    print(f"  {i}. {metric.name}: {metric.score * 100:.0f}%")
                total_metrics += len(section.sub_metrics)
            else:
                print(f"\n{section_name}: No metrics")

        print(
            f"\n📈 Total metrics: {total_metrics} (expected: {tier_config['expected_metrics']})"
        )

        # Check if evidence was passed properly
        if hasattr(report, "evidence_summary") and report.evidence_summary:
            print(
                f"\n✅ Evidence summary exists: {len(json.dumps(report.evidence_summary))} chars"
            )
        else:
            print("\n❌ No evidence summary found")

        return total_metrics

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        return 0


if __name__ == "__main__":
    metrics_count = test_debug_metrics()
    print(
        f"\n{'✅' if metrics_count >= 12 else '❌'} Test {'passed' if metrics_count >= 12 else 'failed'}"
    )
