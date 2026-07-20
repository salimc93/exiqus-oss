#!/usr/bin/env python3
"""
Showcase what users see at each subscription tier.
"""

import os
import signal
import sys
import time
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from github_analyzer.ai.analyzer import AIAnalyzer  # noqa: E402
from github_analyzer.core.classifier import RepositoryClassifier  # noqa: E402
from github_analyzer.core.confidence_scorer import ConfidenceRiskAssessor  # noqa: E402
from github_analyzer.core.context_analyzer import (  # noqa: E402
    ContextAnalyzer,
    HiringContext,
)
from github_analyzer.core.report_generator import ReportGenerator  # noqa: E402
from github_analyzer.data.github_fetcher import GitHubFetcher  # noqa: E402
from github_analyzer.database.models import SubscriptionPlan  # noqa: E402
from github_analyzer.utils.config import get_config  # noqa: E402


@contextmanager
def timeout(duration):
    """Context manager for timeout."""

    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {duration} seconds")

    # Set the signal handler and alarm
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(duration)
    try:
        yield
    finally:
        signal.alarm(0)  # Disable the alarm


def print_tier_header(tier: str, price: str):
    """Print a nice header for each tier."""
    print(f"\n{'=' * 100}")
    print(f"🎯 {tier.upper()} TIER - {price}")
    print(f"{'=' * 100}")


def showcase_tier(
    repo_url: str,
    context: HiringContext,
    plan: SubscriptionPlan,
    tier_name: str,
    price: str,
):
    """Show what a specific tier gets."""
    config = get_config()

    print_tier_header(tier_name, price)
    print(f"Repository: {repo_url}")
    print(f"Context: {context.value}")

    # Initialize components
    github_fetcher = GitHubFetcher(config.github_token)
    classifier = RepositoryClassifier()
    context_analyzer = ContextAnalyzer()
    confidence_scorer = ConfidenceRiskAssessor()
    report_generator = ReportGenerator(config.anthropic_api_key)
    ai_analyzer = AIAnalyzer()

    start = time.time()

    try:
        with timeout(600):  # 10 minute timeout per tier
            # Quick analysis
            repo_data = github_fetcher.fetch_repository_data(repo_url)
            # evidence = evidence_extractor.extract_all_evidence(repo_data)  # TODO: Use this evidence data
            classification = classifier.classify_repository(repo_data)
            context_assessment = context_analyzer.analyze(repo_data, context)
            confidence_analysis = confidence_scorer.score_confidence_and_risk(
                repo_data, classification, context_assessment
            )
            ai_result = ai_analyzer.analyze_repository(repo_data)

            # Generate report
            report = report_generator.generate_report(
                repo_data,
                classification,
                context_assessment,
                context,
                confidence_analysis,
                ai_result,
                plan,
            )
    except TimeoutError as e:
        print(f"\n⚠️  {e}")
        print("Skipping this tier due to timeout...")
        return 0, 0
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        import traceback

        traceback.print_exc()
        return 0, 0

    total_time = time.time() - start

    # SHOW WHAT USERS SEE
    print(f"\n⏱️  Analysis Time: {total_time:.1f} seconds")
    print("\n📊 EXECUTIVE SUMMARY:")
    print(f"{'─' * 50}")
    print(f"Verdict: {report.overall_recommendation}")
    print(f"Confidence: {report.confidence_score * 100:.0f}% ± 10%")
    if report.context_fit_score < 0:
        print("Context Fit: Insufficient data for assessment")
    else:
        print(f"Context Fit: {report.context_fit_score * 10:.1f}/10")

    # TECHNICAL METRICS
    if report.technical_assessment and hasattr(
        report.technical_assessment, "sub_metrics"
    ):
        print(
            f"\n🔧 TECHNICAL ASSESSMENT ({len(report.technical_assessment.sub_metrics)} metrics):"
        )
        print(f"{'─' * 50}")

        for i, metric in enumerate(report.technical_assessment.sub_metrics[:3], 1):
            print(f"\n{i}. {metric.name}: {metric.percentage}%")
            print(f"   Evidence: {metric.evidence[:80]}...")
            print(f"   Insight: {metric.insight[:80]}...")

    # SCREENING INSIGHTS (NEW AI FEATURE)
    if hasattr(report, "screening_insights") and report.screening_insights:
        insights = getattr(report.screening_insights, "insights", [])
        if insights:
            print(f"\n🔍 AI-POWERED INSIGHTS ({len(insights)}):")
            print(f"{'─' * 50}")
            for i, insight in enumerate(insights[:3], 1):
                if hasattr(insight, "title"):
                    print(f"\n{i}. {insight.title}")
                    print(f"   {insight.description[:80]}...")
                    print(f"   Confidence: {insight.confidence}")

    # RECOMMENDATIONS
    if (
        hasattr(report, "evidence_based_recommendations")
        and report.evidence_based_recommendations
    ):
        if isinstance(report.evidence_based_recommendations, dict):
            recs = report.evidence_based_recommendations.get("all_recommendations", [])
        else:
            recs = getattr(
                report.evidence_based_recommendations, "all_recommendations", []
            )

        if recs:
            print(f"\n💡 EVIDENCE-BASED RECOMMENDATIONS ({len(recs)}):")
            print(f"{'─' * 50}")
            for i, rec in enumerate(recs[:3], 1):
                if isinstance(rec, dict):
                    print(
                        f"\n{i}. {rec.get('recommendation', rec.get('text', 'N/A'))[:100]}..."
                    )
                    print(f"   Evidence: {rec.get('evidence', 'N/A')[:80]}...")
                    print(f"   Priority: {rec.get('priority', 'N/A').upper()}")
                else:
                    print(
                        f"\n{i}. {getattr(rec, 'recommendation', getattr(rec, 'text', 'N/A'))[:100]}..."
                    )
                    print(f"   Evidence: {getattr(rec, 'evidence', 'N/A')[:80]}...")
                    print(f"   Priority: {getattr(rec, 'priority', 'N/A').upper()}")

    # INTERVIEW QUESTIONS - THE KEY DIFFERENTIATOR!
    all_qs = []
    if report.interview_questions and isinstance(report.interview_questions, dict):
        all_qs = report.interview_questions.get("all_questions", [])
        upgrade_prompt = report.interview_questions.get("upgrade_prompt", "")

        print("\n❓ INTERVIEW QUESTIONS:")
        print(f"{'─' * 50}")

        if plan == SubscriptionPlan.ENTERPRISE:
            print(f"Generated: {len(all_qs)} questions using Haiku 3.5 (Advanced AI)")
        else:
            print(f"Generated: {len(all_qs)} questions")

        # Show questions based on tier
        for i, q in enumerate(all_qs, 1):
            if q.get("is_blurred", False):
                print(f"\n{i}. {'█' * 60}")
                print(
                    f"   🔒 {q.get('upgrade_message', 'Upgrade to see this question')}"
                )
            else:
                print(f"\n{i}. {q.get('question', 'N/A')[:100]}...")
                print(f"   Based on: {q.get('evidence_reference', 'N/A')[:60]}...")
                print(f"   Category: {q.get('category', 'N/A')}")
                if i == 1:  # Show more detail for first question
                    print(
                        f"   Listen for: {q.get('what_to_listen_for', 'N/A')[:60]}..."
                    )

        if upgrade_prompt:
            print(f"\n📈 {upgrade_prompt}")
    else:
        print("\n❓ INTERVIEW QUESTIONS:")
        print(f"{'─' * 50}")
        print("No questions generated")

    # EXPORT FORMATS
    print("\n📄 AVAILABLE EXPORT FORMATS:")
    print(f"{'─' * 50}")
    formats = {
        SubscriptionPlan.FREE: ["✓ Text", "✓ Markdown", "✗ HTML", "✗ JSON", "✗ PDF"],
        SubscriptionPlan.BASIC: ["✓ Text", "✓ Markdown", "✓ HTML", "✗ JSON", "✗ PDF"],
        SubscriptionPlan.PROFESSIONAL: [
            "✓ Text",
            "✓ Markdown",
            "✓ HTML",
            "✓ JSON",
            "✓ PDF",
        ],
        SubscriptionPlan.ENTERPRISE: [
            "✓ Text",
            "✓ Markdown",
            "✓ HTML",
            "✓ JSON",
            "✓ PDF",
        ],
    }
    print("  " + "  ".join(formats[plan]))

    # COST
    cost = (
        0.0097 if plan != SubscriptionPlan.ENTERPRISE else 0.0127
    )  # Higher for Haiku 3.5
    print(f"\n💰 Analysis Cost: ${cost:.4f}")

    return total_time, len(all_qs)


def main():
    if not os.getenv("GITHUB_TOKEN") or not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ Error: Missing environment variables")
        return

    print("🚀 EVIDENCE-BASED HIRING INSIGHTS - TIER COMPARISON")
    print("See exactly what each tier gets!")

    # Test repository and context - using an edge case repo
    # Options for edge cases:
    # - "https://github.com/kelseyhightower/nocode" - No code repository (just README)
    # - "https://github.com/jwasham/coding-interview-university" - Educational repo, mostly docs
    # - "https://github.com/996icu/996.ICU" - Activism repo with minimal code
    # - "https://github.com/ytdl-org/youtube-dl" - Legally complex repo

    repo_url = "https://github.com/kelseyhightower/nocode"  # Edge case: No actual code!
    context = HiringContext.STARTUP

    # Show each tier with correct pricing from README.md
    tiers = [
        (SubscriptionPlan.FREE, "FREE", "$0/month"),
        (SubscriptionPlan.BASIC, "BASIC", "$49/month"),
        (SubscriptionPlan.PROFESSIONAL, "PROFESSIONAL", "$149/month"),
        (SubscriptionPlan.ENTERPRISE, "ENTERPRISE", "$399/month"),
    ]

    results = []
    for plan, name, price in tiers:
        time_taken, questions = showcase_tier(repo_url, context, plan, name, price)
        results.append((name, time_taken, questions))

    # SUMMARY
    print(f"\n{'=' * 100}")
    print("📊 TIER COMPARISON SUMMARY")
    print(f"{'=' * 100}")
    print(f"\n{'Tier':<15} {'Time':<10} {'Questions':<20} {'Key Features'}")
    print(f"{'─' * 80}")

    features = {
        "FREE": "3 visible questions (rest blurred), basic metrics",
        "BASIC": "5-7 questions, HTML export",
        "PROFESSIONAL": "8-10 questions, JSON/PDF export",
        "ENTERPRISE": "20-25 questions (Haiku 3.5), all features",
    }

    for name, time_taken, questions in results:
        print(f"{name:<15} {time_taken:.1f}s{'':<6} {questions:<20} {features[name]}")

    print("\n🎯 VALUE PROPOSITION:")
    print("   • Manual review: 15-30 minutes per candidate")
    print("   • Our analysis: 40-60 seconds with AI")
    print("   • Time saved: 95%+")
    print("   • Cost per analysis: $0.01-0.013")
    print("   • One good hire pays for 100,000+ analyses")

    print("\n🚀 ENTERPRISE ADVANTAGE:")
    print("   • Uses Haiku 3.5 (most advanced model)")
    print("   • 20-25 tailored questions vs 3-10 for other tiers")
    print("   • Deeper insights and evidence connections")
    print("   • Executive-ready PDF reports")
    print("   • Priority support")


if __name__ == "__main__":
    main()
