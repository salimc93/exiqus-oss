#!/usr/bin/env python3
"""
Test context-aware variations for all 4 hiring contexts.
Shows how questions and metrics adapt to different hiring scenarios.
"""

import json
import time
from typing import Any, Dict, List

from test_utils import CONTEXT_CONFIGS, TEST_REPOS, TIER_CONFIGS, initialize_components
from pathlib import Path



VALIDATION_DIR = Path(__file__).resolve().parent
def analyze_context_variations(
    repo_url: str, tier: str = "professional"
) -> Dict[str, Any]:
    """Analyze variations across all 4 contexts for a single repository."""

    contexts = ["startup", "enterprise", "agency", "open_source"]
    results = {}

    components = initialize_components()

    # Fetch repo data once
    print(f"\n🔍 Analyzing repository: {repo_url}")
    repo_data = components["github_fetcher"].fetch_repository_data(repo_url)
    evidence = components["evidence_extractor"].extract_all_evidence(repo_data)
    classification = components["classifier"].classify_repository(repo_data)

    # Test each context
    for context_name in contexts:
        print(f"\n📋 Testing {context_name.upper()} context...")

        context_enum = CONTEXT_CONFIGS[context_name]

        # Get context-specific assessment
        context_assessment = components["context_analyzer"].analyze(
            repo_data, context_enum
        )
        confidence_analysis = components["confidence_scorer"].score_confidence_and_risk(
            repo_data, classification, context_assessment
        )

        # Generate questions for this context
        questions = components["question_builder"].generate_questions(
            evidence=evidence, context=context_name, tier=tier
        )

        # Generate report with metrics
        report = components["report_generator"].generate_report(
            repo_data,
            classification,
            context_assessment,
            context_enum,
            confidence_analysis,
            None,
            TIER_CONFIGS[tier]["plan"],
        )

        # Extract context-specific patterns
        results[context_name] = {
            "context_fit_score": report.context_fit_score,
            "confidence_score": confidence_analysis.confidence_breakdown.overall_confidence,
            "total_questions": len(questions.get("all_questions", [])),
            "question_categories": extract_question_categories(questions),
            "question_themes": extract_question_themes(questions),
            "metric_focus": extract_metric_focus(report),
            "top_questions": questions.get("all_questions", [])[:3],
            "analysis_recommendations": report.analysis_recommendations[:3],
        }

    return results


def extract_question_categories(questions: Dict[str, Any]) -> Dict[str, int]:
    """Count question categories."""
    categories = {}
    for q in questions.get("all_questions", []):
        cat = q.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1
    return categories


def extract_question_themes(questions: Dict[str, Any]) -> List[str]:
    """Extract key themes from questions."""
    themes = set()
    for q in questions.get("all_questions", []):
        question_text = q.get("question", "").lower()

        # Startup themes
        if any(
            word in question_text
            for word in ["fast", "quick", "mvp", "iterate", "pivot"]
        ):
            themes.add("agility")
        if any(
            word in question_text
            for word in ["multiple", "hats", "versatile", "generalist"]
        ):
            themes.add("versatility")
        if any(
            word in question_text for word in ["technical debt", "trade-o", "pragmatic"]
        ):
            themes.add("pragmatism")

        # Enterprise themes
        if any(
            word in question_text
            for word in ["compliance", "process", "governance", "standards"]
        ):
            themes.add("compliance")
        if any(
            word in question_text
            for word in ["scale", "enterprise", "large team", "organization"]
        ):
            themes.add("scale")
        if any(
            word in question_text
            for word in ["maintainability", "documentation", "standards"]
        ):
            themes.add("maintainability")

        # Agency themes
        if any(
            word in question_text
            for word in ["client", "stakeholder", "requirement", "communication"]
        ):
            themes.add("client_focus")
        if any(
            word in question_text
            for word in ["deadline", "timeline", "delivery", "project"]
        ):
            themes.add("deadline_driven")
        if any(
            word in question_text
            for word in ["juggle", "multiple projects", "prioritize", "switch"]
        ):
            themes.add("multi_project")

        # Open source themes
        if any(
            word in question_text
            for word in ["community", "contributor", "collaborate", "open"]
        ):
            themes.add("community")
        if any(
            word in question_text
            for word in ["documentation", "readme", "guide", "api"]
        ):
            themes.add("documentation")
        if any(
            word in question_text
            for word in ["vision", "roadmap", "sustainability", "long-term"]
        ):
            themes.add("long_term_vision")

    return list(themes)


def extract_metric_focus(report) -> Dict[str, float]:
    """Extract which metrics are emphasized."""
    focus = {}

    # Technical focus
    if hasattr(report, "technical_assessment") and report.technical_assessment:
        focus["technical"] = report.technical_assessment.score

    # Collaboration focus
    if hasattr(report, "communication_skills") and report.communication_skills:
        focus["collaboration"] = report.communication_skills.score

    # Professional practices
    if hasattr(report, "professional_practices") and report.professional_practices:
        focus["professional"] = report.professional_practices.score

    # Growth indicators
    if hasattr(report, "growth_indicators") and report.growth_indicators:
        focus["growth"] = report.growth_indicators.score

    return focus


def display_variations(results: Dict[str, Dict[str, Any]], repo_url: str):
    """Display context variations in a clear format."""

    print("\n" + "=" * 80)
    print("📊 CONTEXT-AWARE VARIATIONS ANALYSIS")
    print("=" * 80)
    print(f"\nRepository: {repo_url}")

    # Compare fit scores
    print("\n🎯 Context Fit Scores:")
    print("-" * 40)
    for context, data in results.items():
        print(
            f"{context.upper():12} {data['context_fit_score']:.1%} fit | {data['confidence_score']:.1%} confidence"
        )

    # Compare question themes
    print("\n💡 Question Themes by Context:")
    print("-" * 40)
    for context, data in results.items():
        themes = data["question_themes"]
        print(f"{context.upper():12} {', '.join(themes) if themes else 'general'}")

    # Compare question categories
    print("\n📝 Question Category Distribution:")
    print("-" * 40)
    all_categories = set()
    for data in results.values():
        all_categories.update(data["question_categories"].keys())

    for category in sorted(all_categories):
        print(f"\n{category}:")
        for context, data in results.items():
            count = data["question_categories"].get(category, 0)
            if count > 0:
                print(f"  {context:12} {count} questions")

    # Compare metric focus
    print("\n📈 Metric Emphasis by Context:")
    print("-" * 40)
    for context, data in results.items():
        focus = data["metric_focus"]
        top_focus = max(focus.items(), key=lambda x: x[1])[0] if focus else "balanced"
        print(f"{context.upper():12} Primary focus: {top_focus}")

    # Show sample questions
    print("\n❓ Sample Questions by Context:")
    print("-" * 80)

    for context, data in results.items():
        print(f"\n{context.upper()} CONTEXT:")
        for i, q in enumerate(data["top_questions"][:2], 1):
            print(f"\n  Q{i}: {q.get('question', 'N/A')}")
            print(f"      Focus: {q.get('evidence_reference', 'N/A')}")


def compare_specific_variations():
    """Compare specific expected variations."""

    print("\n" + "=" * 80)
    print("🔍 EXPECTED CONTEXT VARIATIONS VERIFICATION")
    print("=" * 80)

    expected_variations = {
        "startup": {
            "themes": ["agility", "versatility", "pragmatism"],
            "questions_about": [
                "moving fast vs technical debt",
                "wearing multiple hats",
                "adaptability",
            ],
            "metric_focus": "growth and innovation",
        },
        "enterprise": {
            "themes": ["compliance", "scale", "maintainability"],
            "questions_about": [
                "compliance and process",
                "scale and maintainability",
                "team collaboration",
            ],
            "metric_focus": "professional practices and stability",
        },
        "agency": {
            "themes": ["client_focus", "deadline_driven", "multi_project"],
            "questions_about": [
                "client communication",
                "project juggling",
                "deadline-driven patterns",
            ],
            "metric_focus": "communication and delivery",
        },
        "open_source": {
            "themes": ["community", "documentation", "long_term_vision"],
            "questions_about": [
                "community engagement",
                "documentation quality",
                "sustainability",
            ],
            "metric_focus": "collaboration and documentation",
        },
    }

    for context, expected in expected_variations.items():
        print(f"\n{context.upper()} CONTEXT:")
        print(f"  Expected themes: {', '.join(expected['themes'])}")
        print(f"  Questions about: {', '.join(expected['questions_about'])}")
        print(f"  Metric focus: {expected['metric_focus']}")


def main():
    """Run context variation tests."""

    print("🔬 CONTEXT-AWARE PROMPTING TEST")
    print("Testing how questions and metrics adapt to different hiring contexts")
    print("=" * 80)

    # Test with a versatile repository
    test_repo = TEST_REPOS["api_framework"]  # FastAPI - works for all contexts
    tier = "professional"  # Use GROWTH tier for rich variations

    # Run analysis
    start_time = time.time()
    results = analyze_context_variations(test_repo, tier)
    analysis_time = time.time() - start_time

    # Display results
    display_variations(results, test_repo)

    # Show expected variations
    compare_specific_variations()

    # Summary
    print(f"\n⏱️  Total analysis time: {analysis_time:.1f} seconds")
    print(f"📊 Analyzed {len(results)} contexts")

    # Save detailed results
    output_file = str(VALIDATION_DIR / "CONTEXT_VARIATIONS_RESULTS.json")
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n💾 Detailed results saved to: {output_file}")
    print("\n✅ Context variation test completed successfully")


if __name__ == "__main__":
    main()
