#!/usr/bin/env python3
"""
Modular context testing - test individual context/tier combinations.
"""

import json
import sys
import time
from typing import Any, Dict

from test_utils import CONTEXT_CONFIGS, TEST_REPOS, TIER_CONFIGS, initialize_components
from pathlib import Path



VALIDATION_DIR = Path(__file__).resolve().parent
def test_context_tier_combination(
    context_name: str, tier_name: str, repo_url: str
) -> Dict[str, Any]:
    """Test a specific context/tier combination."""

    print(f"\n🔬 Testing {context_name.upper()} context with {tier_name.upper()} tier")
    print("=" * 60)

    components = initialize_components()
    start_time = time.time()

    try:
        # Fetch and analyze
        repo_data = components["github_fetcher"].fetch_repository_data(repo_url)
        evidence = components["evidence_extractor"].extract_all_evidence(repo_data)
        classification = components["classifier"].classify_repository(repo_data)

        context_enum = CONTEXT_CONFIGS[context_name]
        context_assessment = components["context_analyzer"].analyze(
            repo_data, context_enum
        )
        confidence_analysis = components["confidence_scorer"].score_confidence_and_risk(
            repo_data, classification, context_assessment
        )

        # Generate questions for this context/tier
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

        # Extract results
        all_questions = questions.get("all_questions", [])

        # Count visible vs blurred questions for FREE tier
        visible_questions = []
        blurred_questions = []

        if tier_name == "free":
            for q in all_questions:
                if q.get("is_blurred", False):
                    blurred_questions.append(q)
                else:
                    visible_questions.append(q)
        else:
            visible_questions = all_questions

        result = {
            "context": context_name,
            "tier": tier_name,
            "success": True,
            "generation_time": generation_time,
            "context_fit_score": report.context_fit_score,
            "confidence_score": report.confidence_score,
            "total_questions": len(all_questions),
            "visible_questions": len(visible_questions),
            "blurred_questions": len(blurred_questions),
            "question_categories": {},
            "sample_questions": [],
            "analysis_recommendations": report.analysis_recommendations[:3],
            "metric_count": count_metrics(report),
            "api_model": get_model_used(tier_name),
        }

        # Analyze questions
        for q in visible_questions[:3]:
            result["sample_questions"].append(
                {
                    "question": q.get("question", "N/A"),
                    "category": q.get("category", "unknown"),
                    "has_green_flags": len(q.get("green_flags", [])) > 0,
                    "has_red_flags": len(q.get("red_flags", [])) > 0,
                }
            )

        # Count categories
        for q in all_questions:
            cat = q.get("category", "unknown")
            result["question_categories"][cat] = (
                result["question_categories"].get(cat, 0) + 1
            )

        print(f"✅ Success! Generated in {generation_time:.1f}s")
        print(
            f"📊 Results: {len(visible_questions)} visible questions, {result['metric_count']} metrics"
        )

        return result

    except Exception as e:
        print(f"❌ Error: {e}")
        return {
            "context": context_name,
            "tier": tier_name,
            "success": False,
            "error": str(e),
        }


def count_metrics(report) -> int:
    """Count total metrics in report."""
    count = 0
    sections = [
        report.technical_assessment,
        report.professional_practices,
        report.communication_skills,
        report.growth_indicators,
    ]

    for section in sections:
        if section and hasattr(section, "sub_metrics") and section.sub_metrics:
            count += len(section.sub_metrics)

    return count


def get_model_used(tier_name: str) -> str:
    """Get the AI model configuration for tier."""
    if tier_name == "free":
        return "Haiku 3.0 (minimal)"
    elif tier_name == "starter":
        return "Haiku 3.0"
    elif tier_name == "growth":
        return "Haiku 3.0 + Haiku 3.5 (questions)"
    elif tier_name == "scale":
        return "Haiku 3.5 + Sonnet 3.5 (questions)"
    return "Unknown"


def display_result(result: Dict[str, Any]):
    """Display test result."""
    if not result["success"]:
        print(f"\n❌ FAILED: {result['context']}/{result['tier']}")
        print(f"Error: {result.get('error', 'Unknown error')}")
        return

    print(f"\n📋 {result['context'].upper()} + {result['tier'].upper()} Results:")
    print("-" * 40)
    print(f"Context Fit: {result['context_fit_score']:.1%}")
    print(f"Confidence: {result['confidence_score']:.1%}")
    print(f"Questions: {result['visible_questions']} visible", end="")
    if result["blurred_questions"] > 0:
        print(f", {result['blurred_questions']} blurred")
    else:
        print()
    print(f"Metrics: {result['metric_count']}")
    print(f"Model: {result['api_model']}")

    if result["sample_questions"]:
        print("\n📝 Sample Questions:")
        for i, q in enumerate(result["sample_questions"], 1):
            print(f"  {i}. [{q['category']}] {q['question'][:80]}...")
            flags = []
            if q["has_green_flags"]:
                flags.append("✅")
            if q["has_red_flags"]:
                flags.append("🚩")
            if flags:
                print(f"     Flags: {' '.join(flags)}")


def run_all_combinations():
    """Run all context/tier combinations."""
    contexts = ["startup", "enterprise", "agency", "open_source"]
    tiers = ["free", "starter", "growth", "scale"]

    results = []
    repo_url = TEST_REPOS["api_framework"]

    total_combinations = len(contexts) * len(tiers)
    current = 0

    print(f"🚀 Testing {total_combinations} context/tier combinations")
    print(f"📦 Using repository: {repo_url}")

    for tier in tiers:
        print(f"\n{'='*60}")
        print(f"TIER: {tier.upper()}")
        print(f"{'='*60}")

        for context in contexts:
            current += 1
            print(f"\n[{current}/{total_combinations}] {context}/{tier}")

            result = test_context_tier_combination(context, tier, repo_url)
            results.append(result)
            display_result(result)

            # Small delay to avoid rate limits
            time.sleep(0.5)

    # Save all results
    output_file = str(VALIDATION_DIR / "ALL_CONTEXT_TIER_RESULTS.json")
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n💾 All results saved to: {output_file}")

    # Summary
    successful = sum(1 for r in results if r["success"])
    print(f"\n📊 Summary: {successful}/{total_combinations} tests passed")


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        # Test specific combination
        if len(sys.argv) == 3:
            context = sys.argv[1]
            tier = sys.argv[2]
            repo_url = TEST_REPOS.get("api_framework")

            result = test_context_tier_combination(context, tier, repo_url)
            display_result(result)

            # Save individual result
            output_file = f"{VALIDATION_DIR}/{context}_{tier}_result.json"
            with open(output_file, "w") as f:
                json.dump(result, f, indent=2)
            print(f"\n💾 Result saved to: {output_file}")
        else:
            print("Usage: python test_context_by_tier.py [context] [tier]")
            print("  Contexts: startup, enterprise, agency, open_source")
            print("  Tiers: free, starter, growth, scale")
            print("Or run without arguments to test all combinations")
    else:
        # Test all combinations
        run_all_combinations()


if __name__ == "__main__":
    main()
