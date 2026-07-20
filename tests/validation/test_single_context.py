#!/usr/bin/env python3
"""
Test a single context/tier combination with better error handling.
"""

import json
import sys
import time

from test_utils import CONTEXT_CONFIGS, TEST_REPOS, TIER_CONFIGS, initialize_components


def test_with_retries(context_name: str, tier_name: str, max_retries: int = 3):
    """Test with retry logic for API errors."""

    repo_url = TEST_REPOS["api_framework"]

    for attempt in range(max_retries):
        try:
            print(
                f"\n🔬 Testing {context_name}/{tier_name} (Attempt {attempt + 1}/{max_retries})"
            )

            components = initialize_components()
            start_time = time.time()

            # Fetch repo data
            print("  📦 Fetching repository data...")
            repo_data = components["github_fetcher"].fetch_repository_data(repo_url)

            # Extract evidence
            print("  🔍 Extracting evidence...")
            evidence = components["evidence_extractor"].extract_all_evidence(repo_data)

            # Classify
            print("  📊 Classifying repository...")
            classification = components["classifier"].classify_repository(repo_data)

            # Context analysis
            print("  🎯 Analyzing context fit...")
            context_enum = CONTEXT_CONFIGS[context_name]
            context_assessment = components["context_analyzer"].analyze(
                repo_data, context_enum
            )
            confidence_analysis = components[
                "confidence_scorer"
            ].score_confidence_and_risk(repo_data, classification, context_assessment)

            # Generate questions
            print("  ❓ Generating questions...")
            tier_mapping = {
                "free": "free",
                "starter": "basic",
                "growth": "professional",
                "scale": "enterprise",
            }

            questions = components["question_builder"].generate_questions(
                evidence=evidence,
                context=context_name,
                tier=tier_mapping.get(tier_name, tier_name),
            )

            # Generate report
            print("  📝 Generating report...")
            report = components["report_generator"].generate_report(
                repo_data,
                classification,
                context_assessment,
                context_enum,
                confidence_analysis,
                None,
                TIER_CONFIGS[tier_name]["plan"],
            )

            generation_time = time.time() - start_time

            print(f"  ✅ Success in {generation_time:.1f}s!")

            # Save result
            result = {
                "context": context_name,
                "tier": tier_name,
                "success": True,
                "generation_time": generation_time,
                "context_fit_score": report.context_fit_score,
                "confidence_score": report.confidence_score,
                "total_questions": len(questions.get("all_questions", [])),
                "questions": [
                    q.get("question", "") for q in questions.get("all_questions", [])
                ],
                "metrics_count": sum(
                    [
                        len(getattr(report.technical_assessment, "sub_metrics", [])),
                        len(getattr(report.professional_practices, "sub_metrics", [])),
                        len(getattr(report.communication_skills, "sub_metrics", [])),
                        len(getattr(report.growth_indicators, "sub_metrics", [])),
                    ]
                ),
            }

            filename = f"tests/validation/{context_name}_{tier_name}_complete.json"
            with open(filename, "w") as f:
                json.dump(result, f, indent=2)

            print(f"  💾 Saved to {filename}")

            return result

        except Exception as e:
            print(f"  ❌ Attempt {attempt + 1} failed: {e}")
            if "overloaded" in str(e).lower():
                print("  ⏳ API overloaded, waiting 30 seconds...")
                time.sleep(30)
            else:
                # Other error, wait less
                time.sleep(5)

    # All attempts failed
    return {
        "context": context_name,
        "tier": tier_name,
        "success": False,
        "error": "Max retries exceeded",
    }


def main():
    """Run single test or specific combination."""
    if len(sys.argv) >= 3:
        context = sys.argv[1]
        tier = sys.argv[2]
        result = test_with_retries(context, tier)

        if result["success"]:
            print("\n✅ Test completed successfully!")
            print(f"   Context fit: {result['context_fit_score']:.1%}")
            print(f"   Questions: {result['total_questions']}")
            print(f"   Metrics: {result['metrics_count']}")
        else:
            print(f"\n❌ Test failed: {result['error']}")
    else:
        # Test all combinations with delays
        contexts = ["startup", "enterprise", "agency", "open_source"]
        tiers = ["free", "growth"]  # Just test free and growth for now

        results = []
        for tier in tiers:
            for context in contexts:
                print(f"\n{'='*60}")
                print(f"Testing {context}/{tier}")
                print(f"{'='*60}")

                result = test_with_retries(context, tier)
                results.append(result)

                # Wait between tests to avoid rate limits
                print("\n⏳ Waiting 10 seconds before next test...")
                time.sleep(10)

        # Summary
        successful = sum(1 for r in results if r["success"])
        print(f"\n📊 Summary: {successful}/{len(results)} tests completed")

        # Save all results
        with open("tests/validation/COMPLETE_TEST_RESULTS.json", "w") as f:
            json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
