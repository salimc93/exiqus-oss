#!/usr/bin/env python3
"""
Compare two contexts side-by-side to see exact differences.
Useful for improving differentiation.
"""

import json
import sys
from typing import Dict, List, Tuple
from pathlib import Path


VALIDATION_DIR = Path(__file__).resolve().parent
# Try to import colorama, but work without it
try:
    from colorama import Fore, Style, init

    init()
    HAS_COLOR = True
except ImportError:
    # Define dummy color classes

    class Fore:
        GREEN = ""
        BLUE = ""
        RESET = ""

    class Style:
        RESET_ALL = ""

    HAS_COLOR = False


def load_context_results(
    context1: str, context2: str, tier: str = "growth"
) -> Tuple[Dict, Dict]:
    """Load results for two contexts."""
    # Try to load from recent test results
    results_file = str(VALIDATION_DIR / "ALL_CONTEXT_TIER_RESULTS.json")

    try:
        with open(results_file, "r") as f:
            all_results = json.load(f)

        result1 = None
        result2 = None

        for result in all_results:
            if result.get("context") == context1 and result.get("tier") == tier:
                result1 = result
            elif result.get("context") == context2 and result.get("tier") == tier:
                result2 = result

        return result1, result2

    except FileNotFoundError:
        print("❌ Results file not found. Run tests first.")
        return None, None


def compare_questions(questions1: List[str], questions2: List[str]):
    """Compare questions between contexts."""
    print("\n" + "=" * 80)
    print("❓ QUESTION COMPARISON")
    print("=" * 80)

    max_questions = max(len(questions1), len(questions2))

    for i in range(max_questions):
        print(f"\nQuestion {i+1}:")
        print("-" * 60)

        if i < len(questions1):
            print(f"{Fore.GREEN}Context 1:{Style.RESET_ALL}")
            print(f"  {questions1[i][:100]}...")
        else:
            print(f"{Fore.GREEN}Context 1:{Style.RESET_ALL} (No more questions)")

        print()

        if i < len(questions2):
            print(f"{Fore.BLUE}Context 2:{Style.RESET_ALL}")
            print(f"  {questions2[i][:100]}...")
        else:
            print(f"{Fore.BLUE}Context 2:{Style.RESET_ALL} (No more questions)")


def compare_themes(themes1: List[str], themes2: List[str]):
    """Compare themes between contexts."""
    print("\n" + "=" * 80)
    print("💡 THEME COMPARISON")
    print("=" * 80)

    set1 = set(themes1)
    set2 = set(themes2)

    common = set1.intersection(set2)
    unique1 = set1 - set2
    unique2 = set2 - set1

    print(f"\n🔄 Common Themes ({len(common)}):")
    for theme in sorted(common):
        print(f"  • {theme}")

    print(f"\n{Fore.GREEN}✨ Unique to Context 1 ({len(unique1)}):{Style.RESET_ALL}")
    for theme in sorted(unique1):
        print(f"  • {theme}")

    print(f"\n{Fore.BLUE}✨ Unique to Context 2 ({len(unique2)}):{Style.RESET_ALL}")
    for theme in sorted(unique2):
        print(f"  • {theme}")


def compare_metrics(metrics1: Dict, metrics2: Dict):
    """Compare metric distributions."""
    print("\n" + "=" * 80)
    print("📊 METRIC FOCUS COMPARISON")
    print("=" * 80)

    categories = ["technical", "professional", "communication", "growth"]

    print("\nMetric Distribution:")
    print(f"{'Category':15} {'Context 1':>12} {'Context 2':>12} {'Difference':>12}")
    print("-" * 55)

    for cat in categories:
        val1 = metrics1.get("distribution", {}).get(cat, 0)
        val2 = metrics2.get("distribution", {}).get(cat, 0)
        diff = val1 - val2

        diff_str = f"{diff:+d}" if diff != 0 else "same"

        print(f"{cat:15} {val1:>12} {val2:>12} {diff_str:>12}")

    print(
        f"\n{'Total':15} {metrics1.get('total_metrics', 0):>12} {metrics2.get('total_metrics', 0):>12}"
    )

    print("\nPrimary Focus:")
    print(f"  Context 1: {metrics1.get('primary_focus', 'none')}")
    print(f"  Context 2: {metrics2.get('primary_focus', 'none')}")


def compare_recommendations(recs1: List[str], recs2: List[str]):
    """Compare hiring recommendations."""
    print("\n" + "=" * 80)
    print("🎯 HIRING RECOMMENDATIONS COMPARISON")
    print("=" * 80)

    for i, (rec1, rec2) in enumerate(zip(recs1[:3], recs2[:3]), 1):
        print(f"\nRecommendation {i}:")
        print(f"{Fore.GREEN}Context 1:{Style.RESET_ALL} {rec1[:80]}...")
        print(f"{Fore.BLUE}Context 2:{Style.RESET_ALL} {rec2[:80]}...")


def generate_improvement_suggestions(
    context1: str, context2: str, result1: Dict, result2: Dict
):
    """Generate suggestions for improving differentiation."""
    print("\n" + "=" * 80)
    print("💡 DIFFERENTIATION IMPROVEMENT SUGGESTIONS")
    print("=" * 80)

    # Analyze what's too similar
    themes1 = set(result1.get("question_themes", []))
    themes2 = set(result2.get("question_themes", []))

    overlap_ratio = (
        len(themes1.intersection(themes2)) / len(themes1.union(themes2))
        if themes1.union(themes2)
        else 0
    )

    if overlap_ratio > 0.6:
        print(f"\n⚠️  High theme overlap ({overlap_ratio:.0%})")
        print("\nSuggestions:")

        # Context-specific suggestions
        if context1 == "startup":
            print(
                f"  • For {context1}: Add more questions about MVP development, pivoting, resource constraints"
            )
        elif context1 == "enterprise":
            print(
                f"  • For {context1}: Emphasize compliance, governance, large-scale coordination"
            )
        elif context1 == "agency":
            print(
                f"  • For {context1}: Focus on client management, project switching, deadline juggling"
            )
        elif context1 == "open_source":
            print(
                f"  • For {context1}: Highlight community building, volunteer coordination, sustainability"
            )

        if context2 == "startup":
            print(
                f"  • For {context2}: Add more questions about speed vs quality trade-offs, wearing multiple hats"
            )
        elif context2 == "enterprise":
            print(
                f"  • For {context2}: Include process adherence, documentation standards, stakeholder management"
            )
        elif context2 == "agency":
            print(
                f"  • For {context2}: Add questions about portfolio diversity, client communication styles"
            )
        elif context2 == "open_source":
            print(
                f"  • For {context2}: Focus on asynchronous collaboration, contributor onboarding"
            )

    # Check metric distribution
    dist1 = result1.get("metric_analysis", {}).get("distribution", {})
    dist2 = result2.get("metric_analysis", {}).get("distribution", {})

    if dist1.get("primary_focus") == dist2.get("primary_focus"):
        print(f"\n⚠️  Same primary metric focus: {dist1.get('primary_focus')}")
        print("  • Consider adjusting metric weights for each context")


def main():
    """Main comparison function."""
    if len(sys.argv) < 3:
        print("Usage: python compare_contexts.py <context1> <context2> [tier]")
        print("Contexts: startup, enterprise, agency, open_source")
        print("Tiers: free, starter, growth, scale (default: growth)")
        return

    context1 = sys.argv[1]
    context2 = sys.argv[2]
    tier = sys.argv[3] if len(sys.argv) > 3 else "growth"

    # Load results
    result1, result2 = load_context_results(context1, context2, tier)

    if not result1 or not result2:
        print(f"❌ Could not find results for {context1} and {context2} in {tier} tier")
        return

    print(
        f"\n🔍 COMPARING: {context1.upper()} vs {context2.upper()} ({tier.upper()} tier)"
    )
    print("=" * 80)

    # Basic stats
    print("\n📈 Basic Statistics:")
    print(f"{'Metric':20} {context1:>15} {context2:>15}")
    print("-" * 52)
    print(
        f"{'Context Fit':20} {result1['context_fit_score']:>14.1%} {result2['context_fit_score']:>14.1%}"
    )
    print(
        f"{'Confidence':20} {result1['confidence_score']:>14.1%} {result2['confidence_score']:>14.1%}"
    )
    print(
        f"{'Total Questions':20} {result1['total_questions']:>15} {result2['total_questions']:>15}"
    )

    # Detailed comparisons
    if "top_questions" in result1 and "top_questions" in result2:
        compare_questions(result1["top_questions"], result2["top_questions"])

    if "question_themes" in result1 and "question_themes" in result2:
        compare_themes(result1["question_themes"], result2["question_themes"])

    if "metric_analysis" in result1 and "metric_analysis" in result2:
        compare_metrics(result1["metric_analysis"], result2["metric_analysis"])

    if "analysis_recommendations" in result1 and "analysis_recommendations" in result2:
        compare_recommendations(
            result1["analysis_recommendations"], result2["analysis_recommendations"]
        )

    # Generate improvement suggestions
    generate_improvement_suggestions(context1, context2, result1, result2)


if __name__ == "__main__":
    main()
