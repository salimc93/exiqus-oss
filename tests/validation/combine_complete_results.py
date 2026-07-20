#!/usr/bin/env python3
"""
Combine complete test results and analyze context differentiation.
"""

import glob
import json
from collections import defaultdict


def load_complete_results():
    """Load all complete test results."""
    results = []

    # Find all complete result files
    files = glob.glob("tests/validation/*_complete.json")

    for file_path in files:
        with open(file_path, "r") as f:
            data = json.load(f)
            if data.get("success"):
                results.append(data)

    return results


def analyze_question_differentiation(results):
    """Analyze how questions differ between contexts."""

    # Group by tier
    by_tier = defaultdict(list)
    for r in results:
        by_tier[r["tier"]].append(r)

    analysis = {}

    for tier, tier_results in by_tier.items():
        print(f"\n{'='*60}")
        print(f"TIER: {tier.upper()}")
        print(f"{'='*60}")

        # Extract questions for each context
        context_questions = {}
        for r in tier_results:
            context = r["context"]
            questions = r.get("questions", [])
            context_questions[context] = questions

            print(f"\n{context.upper()}:")
            print(f"  Questions: {len(questions)}")
            print(f"  Context Fit: {r['context_fit_score']:.1%}")
            print(f"  Metrics: {r['metrics_count']}")

        # Calculate similarity between contexts
        print("\n📊 Question Similarity Matrix:")
        contexts = list(context_questions.keys())

        similarity_scores = {}

        for i, ctx1 in enumerate(contexts):
            for j, ctx2 in enumerate(contexts):
                if i >= j:
                    continue

                q1 = context_questions[ctx1]
                q2 = context_questions[ctx2]

                # Calculate similarity
                similarity = calculate_question_similarity(q1, q2)
                similarity_scores[f"{ctx1}-{ctx2}"] = similarity

                print(f"  {ctx1} vs {ctx2}: {similarity:.1%} similar")

        # Calculate average differentiation
        if similarity_scores:
            avg_similarity = sum(similarity_scores.values()) / len(similarity_scores)
            differentiation = 1 - avg_similarity

            print(f"\n✅ Average Differentiation: {differentiation:.1%}")

            analysis[tier] = {
                "differentiation_score": differentiation,
                "similarity_scores": similarity_scores,
                "context_count": len(contexts),
            }

    return analysis


def calculate_question_similarity(questions1, questions2):
    """Calculate similarity between two sets of questions."""
    if not questions1 or not questions2:
        return 0.0

    # Convert to lowercase for comparison
    q1_words = set()
    q2_words = set()

    for q in questions1:
        q1_words.update(q.lower().split())

    for q in questions2:
        q2_words.update(q.lower().split())

    # Jaccard similarity
    intersection = len(q1_words.intersection(q2_words))
    union = len(q1_words.union(q2_words))

    return intersection / union if union > 0 else 0.0


def display_sample_questions(results):
    """Display sample questions for comparison."""

    print("\n" + "=" * 80)
    print("📝 SAMPLE QUESTIONS BY CONTEXT (GROWTH TIER)")
    print("=" * 80)

    growth_results = [r for r in results if r["tier"] == "growth"]

    for r in growth_results:
        context = r["context"]
        questions = r.get("questions", [])[:2]  # First 2 questions

        print(f"\n{context.upper()}:")
        for i, q in enumerate(questions, 1):
            print(f"  Q{i}: {q[:100]}...")


def generate_marketing_metrics(analysis):
    """Generate marketing-ready metrics."""

    print("\n" + "=" * 80)
    print("🎯 MARKETING METRICS")
    print("=" * 80)

    for tier, data in analysis.items():
        diff_score = data["differentiation_score"]
        diff_pct = int(diff_score * 100)

        print(f"\n{tier.upper()} Tier:")
        print(f"  📊 Differentiation: {diff_pct}% unique insights per context")

        if diff_pct >= 60:
            print(f"  ✅ Ready for claim: 'AI adapts with {diff_pct}% unique insights'")
        else:
            print(f"  ⚠️  Need {60-diff_pct}% more differentiation for 60% claim")


def main():
    """Run the analysis."""

    # Load results
    results = load_complete_results()
    print(f"📁 Loaded {len(results)} test results")

    # Analyze differentiation
    analysis = analyze_question_differentiation(results)

    # Display sample questions
    display_sample_questions(results)

    # Generate marketing metrics
    generate_marketing_metrics(analysis)

    # Save analysis
    output = {"results": results, "analysis": analysis}

    with open("tests/validation/CONTEXT_DIFFERENTIATION_ANALYSIS.json", "w") as f:
        json.dump(output, f, indent=2)

    print("\n💾 Analysis saved to CONTEXT_DIFFERENTIATION_ANALYSIS.json")


if __name__ == "__main__":
    main()
