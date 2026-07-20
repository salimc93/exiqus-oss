#!/usr/bin/env python3
"""
Context-aware testing with different repository sizes/complexities.
Tests how the system adapts to different contexts AND repository characteristics.
"""

import json
import sys
import time
from typing import Any, Dict, List

from test_utils import CONTEXT_CONFIGS, TIER_CONFIGS, initialize_components
from pathlib import Path


VALIDATION_DIR = Path(__file__).resolve().parent
# Repository matrix: Different sizes/complexities for each context
CONTEXT_REPO_MATRIX = {
    "startup": [
        {
            "url": "https://github.com/tinygrad/tinygrad",
            "type": "small_fast_moving",
            "description": "Small, fast-moving ML framework",
            "expected_themes": ["agility", "innovation", "technical_debt_awareness"],
        },
        {
            "url": "https://github.com/supabase/supabase",
            "type": "medium_growing",
            "description": "Growing startup with rapid iteration",
            "expected_themes": ["scalability", "versatility", "product_focus"],
        },
    ],
    "enterprise": [
        {
            "url": "https://github.com/microsoft/vscode",
            "type": "large_mature",
            "description": "Large enterprise codebase",
            "expected_themes": ["process", "scale", "maintainability"],
        },
        {
            "url": "https://github.com/elastic/elasticsearch",
            "type": "complex_distributed",
            "description": "Complex distributed system",
            "expected_themes": ["architecture", "team_coordination", "standards"],
        },
    ],
    "agency": [
        {
            "url": "https://github.com/vercel/next.js",
            "type": "framework_multiple_projects",
            "description": "Framework used in multiple client projects",
            "expected_themes": ["flexibility", "client_needs", "rapid_delivery"],
        },
        {
            "url": "https://github.com/tailwindlabs/tailwindcss",
            "type": "tool_client_focused",
            "description": "Tool for rapid client development",
            "expected_themes": ["efficiency", "customization", "documentation"],
        },
    ],
    "open_source": [
        {
            "url": "https://github.com/rust-lang/rust",
            "type": "community_driven",
            "description": "Large community-driven project",
            "expected_themes": ["collaboration", "documentation", "long_term_vision"],
        },
        {
            "url": "https://github.com/home-assistant/core",
            "type": "volunteer_maintained",
            "description": "Volunteer-maintained smart home platform",
            "expected_themes": [
                "community_engagement",
                "sustainability",
                "contributor_experience",
            ],
        },
    ],
}


def test_context_with_repo(
    context_name: str, repo_info: Dict[str, str], tier_name: str
) -> Dict[str, Any]:
    """Test a specific context with a specific repository type."""

    print(f"\n🔬 Testing {context_name.upper()} context")
    print(f"📦 Repository: {repo_info['description']}")
    print(f"🏷️  Tier: {tier_name.upper()}")
    print("-" * 60)

    components = initialize_components()
    start_time = time.time()

    try:
        # Fetch and analyze
        repo_data = components["github_fetcher"].fetch_repository_data(repo_info["url"])
        evidence = components["evidence_extractor"].extract_all_evidence(repo_data)
        classification = components["classifier"].classify_repository(repo_data)

        context_enum = CONTEXT_CONFIGS[context_name]
        context_assessment = components["context_analyzer"].analyze(
            repo_data, context_enum
        )
        confidence_analysis = components["confidence_scorer"].score_confidence_and_risk(
            repo_data, classification, context_assessment
        )

        # Generate questions
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

        # Analyze results
        result = analyze_results(
            context_name, repo_info, tier_name, questions, report, generation_time
        )

        # Check if expected themes appear
        result["theme_match"] = check_theme_match(
            questions, repo_info.get("expected_themes", [])
        )

        print(f"✅ Completed in {generation_time:.1f}s")
        print(f"📊 Theme match: {result['theme_match']['score']:.0%}")

        return result

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()

        return {
            "context": context_name,
            "repo": repo_info["url"],
            "repo_type": repo_info["type"],
            "tier": tier_name,
            "success": False,
            "error": str(e),
        }


def analyze_results(
    context_name: str,
    repo_info: Dict[str, str],
    tier_name: str,
    questions: Dict[str, Any],
    report: Any,
    generation_time: float,
) -> Dict[str, Any]:
    """Analyze test results."""

    all_questions = questions.get("all_questions", [])

    # Extract question themes
    question_themes = extract_themes_from_questions(all_questions)

    # Analyze metrics focus
    metric_analysis = analyze_metric_distribution(report)

    # Count question types
    question_analysis = analyze_question_distribution(all_questions)

    return {
        "context": context_name,
        "repo": repo_info["url"],
        "repo_type": repo_info["type"],
        "repo_description": repo_info["description"],
        "tier": tier_name,
        "success": True,
        "generation_time": generation_time,
        "context_fit_score": report.context_fit_score,
        "confidence_score": report.confidence_score,
        "total_questions": len(all_questions),
        "question_themes": question_themes,
        "question_analysis": question_analysis,
        "metric_analysis": metric_analysis,
        "top_questions": [q.get("question", "") for q in all_questions[:3]],
        "analysis_recommendations": report.analysis_recommendations[:3],
    }


def extract_themes_from_questions(questions: List[Dict[str, Any]]) -> List[str]:
    """Extract themes from questions."""
    theme_keywords = {
        # Startup themes
        "agility": ["fast", "quick", "mvp", "iterate", "pivot", "adapt"],
        "innovation": ["new", "creative", "innovative", "experiment", "cutting-edge"],
        "technical_debt_awareness": [
            "technical debt",
            "trade-o",
            "pragmatic",
            "balance",
        ],
        "versatility": [
            "multiple",
            "hats",
            "versatile",
            "generalist",
            "cross-functional",
        ],
        # Enterprise themes
        "process": ["process", "procedure", "governance", "compliance", "standard"],
        "scale": ["scale", "enterprise", "large", "distributed", "performance"],
        "maintainability": ["maintain", "documentation", "long-term", "sustainable"],
        "architecture": ["architecture", "design", "system", "structure", "pattern"],
        # Agency themes
        "flexibility": ["flexible", "adapt", "change", "various", "different"],
        "client_needs": [
            "client",
            "customer",
            "stakeholder",
            "requirement",
            "expectation",
        ],
        "rapid_delivery": ["deadline", "timeline", "delivery", "quick", "efficient"],
        "customization": ["customize", "tailor", "specific", "unique", "bespoke"],
        # Open source themes
        "collaboration": [
            "community",
            "contributor",
            "collaborate",
            "together",
            "team",
        ],
        "documentation": ["document", "readme", "guide", "api", "tutorial"],
        "long_term_vision": ["vision", "roadmap", "future", "sustainable", "long-term"],
        "community_engagement": [
            "engage",
            "feedback",
            "review",
            "discussion",
            "contribute",
        ],
    }

    found_themes = set()

    for question in questions:
        q_text = question.get("question", "").lower()
        evidence = question.get("evidence_reference", "").lower()

        for theme, keywords in theme_keywords.items():
            if any(keyword in q_text or keyword in evidence for keyword in keywords):
                found_themes.add(theme)

    return list(found_themes)


def analyze_metric_distribution(report) -> Dict[str, Any]:
    """Analyze which metrics are emphasized."""
    distribution = {"technical": 0, "professional": 0, "communication": 0, "growth": 0}

    # Count metrics by section
    if hasattr(report, "technical_assessment") and report.technical_assessment:
        if hasattr(report.technical_assessment, "sub_metrics"):
            distribution["technical"] = len(
                report.technical_assessment.sub_metrics or []
            )

    if hasattr(report, "professional_practices") and report.professional_practices:
        if hasattr(report.professional_practices, "sub_metrics"):
            distribution["professional"] = len(
                report.professional_practices.sub_metrics or []
            )

    if hasattr(report, "communication_skills") and report.communication_skills:
        if hasattr(report.communication_skills, "sub_metrics"):
            distribution["communication"] = len(
                report.communication_skills.sub_metrics or []
            )

    if hasattr(report, "growth_indicators") and report.growth_indicators:
        if hasattr(report.growth_indicators, "sub_metrics"):
            distribution["growth"] = len(report.growth_indicators.sub_metrics or [])

    total = sum(distribution.values())

    return {
        "distribution": distribution,
        "total_metrics": total,
        "primary_focus": (
            max(distribution.items(), key=lambda x: x[1])[0] if total > 0 else "none"
        ),
    }


def analyze_question_distribution(questions: List[Dict[str, Any]]) -> Dict[str, int]:
    """Analyze question category distribution."""
    categories = {}

    for q in questions:
        cat = q.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1

    return categories


def check_theme_match(
    questions: Dict[str, Any], expected_themes: List[str]
) -> Dict[str, Any]:
    """Check if expected themes appear in questions."""
    all_questions = questions.get("all_questions", [])
    found_themes = extract_themes_from_questions(all_questions)

    matches = [theme for theme in expected_themes if theme in found_themes]

    return {
        "expected": expected_themes,
        "found": found_themes,
        "matches": matches,
        "score": len(matches) / len(expected_themes) if expected_themes else 0,
    }


def display_matrix_results(results: List[Dict[str, Any]]):
    """Display results in a matrix format."""
    print("\n" + "=" * 80)
    print("📊 CONTEXT-REPOSITORY MATRIX RESULTS")
    print("=" * 80)

    # Group by context
    by_context = {}
    for result in results:
        context = result["context"]
        if context not in by_context:
            by_context[context] = []
        by_context[context].append(result)

    # Display each context
    for context, context_results in by_context.items():
        print(f"\n🎯 {context.upper()} CONTEXT")
        print("-" * 60)

        for result in context_results:
            if not result["success"]:
                print(f"  ❌ {result['repo_type']}: Failed - {result['error']}")
                continue

            print(f"\n  📦 {result['repo_type']} ({result['tier']} tier)")
            print(f"     Repository: {result['repo_description']}")
            print(f"     Fit Score: {result['context_fit_score']:.1%}")
            print(f"     Questions: {result['total_questions']}")
            print(f"     Themes: {', '.join(result['question_themes'][:5])}")
            print(f"     Theme Match: {result['theme_match']['score']:.0%}")
            print(f"     Metric Focus: {result['metric_analysis']['primary_focus']}")


def run_context_matrix(selected_context: str = None, selected_tier: str = "growth"):
    """Run the context-repository matrix test."""

    contexts = (
        [selected_context] if selected_context else list(CONTEXT_REPO_MATRIX.keys())
    )
    results = []

    print("🚀 Testing Context-Repository Matrix")
    print(f"📊 Tier: {selected_tier.upper()}")
    print(f"🎯 Contexts: {', '.join(contexts)}")

    for context in contexts:
        repos = CONTEXT_REPO_MATRIX[context]

        for repo_info in repos:
            result = test_context_with_repo(context, repo_info, selected_tier)
            results.append(result)

            # Brief pause to avoid rate limits
            time.sleep(1)

    # Display results
    display_matrix_results(results)

    # Save results
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_file = f"{VALIDATION_DIR}/context_matrix_{timestamp}.json"

    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n💾 Results saved to: {output_file}")

    # Summary statistics
    successful = sum(1 for r in results if r["success"])
    avg_theme_match = (
        sum(r["theme_match"]["score"] for r in results if r["success"]) / successful
        if successful > 0
        else 0
    )

    print("\n📈 Summary:")
    print(f"  • Success Rate: {successful}/{len(results)}")
    print(f"  • Average Theme Match: {avg_theme_match:.0%}")


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        if sys.argv[1] in CONTEXT_REPO_MATRIX:
            # Test specific context
            context = sys.argv[1]
            tier = sys.argv[2] if len(sys.argv) > 2 else "growth"
            run_context_matrix(context, tier)
        else:
            print("Usage: python test_context_matrix.py [context] [tier]")
            print(f"  Contexts: {', '.join(CONTEXT_REPO_MATRIX.keys())}")
            print("  Tiers: free, starter, growth, scale")
    else:
        # Test all contexts with growth tier
        run_context_matrix(selected_tier="growth")


if __name__ == "__main__":
    main()
