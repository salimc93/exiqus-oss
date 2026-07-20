#!/usr/bin/env python3
"""
Test to identify and fix enterprise context scoring bias.
"""


from test_utils import CONTEXT_CONFIGS, TEST_REPOS, initialize_components


def test_enterprise_scoring():
    """Test why enterprise context scores lower than others."""

    print("🔍 INVESTIGATING ENTERPRISE CONTEXT SCORING BIAS")
    print("=" * 60)

    components = initialize_components()
    repo_url = TEST_REPOS["api_framework"]  # FastAPI - should work well for enterprise

    # Fetch repo data once
    repo_data = components["github_fetcher"].fetch_repository_data(repo_url)

    # Test all contexts with same repo
    contexts = ["startup", "enterprise", "agency", "open_source"]
    results = {}

    for context_name in contexts:
        context_enum = CONTEXT_CONFIGS[context_name]
        assessment = components["context_analyzer"].analyze(repo_data, context_enum)

        results[context_name] = {
            "fit_score": assessment.fit_score,
            "strengths": len(assessment.strengths),
            "concerns": len(assessment.concerns),
        }

        print(f"\n{context_name.upper()}:")
        print(f"  Fit Score: {assessment.fit_score:.1%}")
        print(f"  Strengths: {len(assessment.strengths)}")
        print(f"  Concerns: {len(assessment.concerns)}")

    # Analyze the bias
    print("\n" + "=" * 60)
    print("📊 ANALYSIS:")

    # Check scoring differences
    enterprise_score = results["enterprise"]["fit_score"]
    avg_other_scores = (
        sum(results[c]["fit_score"] for c in ["startup", "agency", "open_source"]) / 3
    )

    print(f"\nEnterprise Score: {enterprise_score:.1%}")
    print(f"Average Other Scores: {avg_other_scores:.1%}")
    print(f"Difference: {(avg_other_scores - enterprise_score):.1%}")

    if enterprise_score < avg_other_scores - 0.2:
        print("\n⚠️  BIAS DETECTED: Enterprise scoring significantly lower!")
        print("\nPOSSIBLE CAUSES:")
        print("1. Enterprise positive signals are too strict")
        print("2. Scoring multipliers favor other contexts")
        print("3. Weight adjustments penalize enterprise unfairly")

        print("\n💡 RECOMMENDED FIXES:")
        print("1. Use same base scoring multipliers for all contexts")
        print("2. Add more achievable enterprise positive signals")
        print("3. Balance weight adjustments across contexts")
    else:
        print("\n✅ No significant bias detected")

    return results


def test_proposed_fix():
    """Test proposed fix for enterprise scoring."""

    print("\n\n🔧 TESTING PROPOSED FIX")
    print("=" * 60)

    # Proposed changes to test:
    print("\nPROPOSED CHANGES:")
    print(
        "1. Change enterprise positive_contribution from 0.5 to 0.4 (same as startup)"
    )
    print("2. Change enterprise negative_penalty from 0.4 to 0.3 (same as startup)")
    print("3. Add achievable positive signals:")
    print("   - consistent_commits (>50 commits, >0.5 frequency)")
    print("   - structured_codebase (has src/lib/test dirs)")
    print("   - team_collaboration (>2 contributors)")

    print("\nEXPECTED OUTCOME:")
    print("- Enterprise score should increase from ~52% to ~70-80%")
    print("- All contexts should score within 20% of each other")
    print("- No context should consistently score below 60% for good repos")


if __name__ == "__main__":
    # Run analysis
    results = test_enterprise_scoring()

    # Show proposed fix
    test_proposed_fix()

    print("\n\n📝 NEXT STEPS:")
    print("1. Update context_analyzer.py with balanced scoring")
    print("2. Add new positive signal handlers")
    print("3. Test with multiple repositories")
    print("4. Verify all contexts score fairly")
