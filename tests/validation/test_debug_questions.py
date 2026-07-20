#!/usr/bin/env python3
"""
Debug test to understand question generation.
"""

import json

from test_utils import CONTEXT_CONFIGS, TEST_REPOS, TIER_CONFIGS, initialize_components


def test_debug_questions():
    """Debug question generation for GROWTH tier."""

    print("🔍 DEBUG: GROWTH TIER QUESTIONS")
    print("=" * 60)

    # Test configuration
    tier = "growth"
    context_name = "startup"
    repo_url = TEST_REPOS["library"]

    tier_config = TIER_CONFIGS[tier]
    CONTEXT_CONFIGS[context_name]  # Retrieved but not stored

    components = initialize_components()

    try:
        # Fetch and analyze
        print("\n1. Extracting evidence...")
        repo_data = components["github_fetcher"].fetch_repository_data(repo_url)
        evidence = components["evidence_extractor"].extract_all_evidence(repo_data)

        print("\n2. Generating questions...")
        questions = components["question_builder"].generate_questions(
            evidence=evidence, context=context_name, tier="professional"  # GROWTH tier
        )

        # Debug output
        print("\n❓ QUESTIONS ANALYSIS:")

        all_questions = questions.get("all_questions", [])
        visible_questions = [q for q in all_questions if not q.get("is_blurred", False)]

        print(f"\nTotal questions: {len(all_questions)}")
        print(f"Visible questions: {len(visible_questions)}")
        print(f"Expected: {tier_config['expected_questions']} total")

        # Check question structure
        if all_questions:
            print("\n📋 Question details:")
            for i, q in enumerate(all_questions[:3], 1):
                print(f"\nQuestion {i}:")
                print(f"  Category: {q.get('category', 'N/A')}")
                print(f"  Question: {q.get('question', 'N/A')[:80]}...")
                print(f"  Has green_flags: {'green_flags' in q and q['green_flags']}")
                print(f"  Has red_flags: {'red_flags' in q and q['red_flags']}")
                print(f"  Has what_to_listen_for: {'what_to_listen_for' in q}")
                print(f"  Is blurred: {q.get('is_blurred', False)}")

        # Check evidence summary
        evidence_summary = questions.get("evidence_summary", {})
        if evidence_summary:
            print(
                f"\n✅ Evidence summary provided: {len(json.dumps(evidence_summary))} chars"
            )
        else:
            print("\n❌ No evidence summary in questions response")

        return len(all_questions)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        return 0


if __name__ == "__main__":
    questions_count = test_debug_questions()
    print(
        f"\n{'✅' if questions_count == 10 else '❌'} Test {'passed' if questions_count == 10 else 'failed'}"
    )
