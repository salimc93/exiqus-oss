#!/usr/bin/env python3
"""
Performance validation script for evidence-based recommendations.

Tests that analysis completes within 30 seconds for various repository types.

IMPORTANT: This script makes REAL API calls to:
- GitHub API (to fetch actual repository data)
- Anthropic API (for AI analysis)

No mocking or test data is used - all tests are against real repositories.
"""

import asyncio
import os

# Add project root to Python path
import sys
import time
from pathlib import Path
from typing import Dict

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


class PerformanceValidator:
    """Validates analysis performance meets <30s requirement."""

    def __init__(self):
        self.config = get_config()
        self.github_fetcher = GitHubFetcher(self.config.github_token)
        self.classifier = RepositoryClassifier()
        self.context_analyzer = ContextAnalyzer()
        self.confidence_scorer = ConfidenceRiskAssessor()
        self.report_generator = ReportGenerator(self.config.anthropic_api_key)
        self.ai_analyzer = AIAnalyzer()

    async def validate_repository(
        self, repo_url: str, context: HiringContext, plan: SubscriptionPlan
    ) -> Dict[str, any]:
        """Validate performance for a single repository.

        This makes REAL API calls - no mocking:
        - Real GitHub API call to fetch repository data
        - Real Anthropic API call for AI analysis
        """
        print(f"\n{'=' * 80}")
        print(f"Testing REAL repository: {repo_url}")
        print(f"Context: {context.value}, Plan: {plan.value}")
        print(f"{'=' * 80}")

        start_time = time.time()
        step_times = {}

        try:
            # Step 1: Fetch repository data (REAL GitHub API call)
            step_start = time.time()
            repo_data = self.github_fetcher.fetch_repository_data(repo_url)
            step_times["fetch"] = time.time() - step_start
            print(f"✓ GitHub API fetch completed in {step_times['fetch']:.2f}s")

            # Step 2: Classify repository
            step_start = time.time()
            classification = self.classifier.classify_repository(repo_data)
            step_times["classify"] = time.time() - step_start
            print(f"✓ Classification completed in {step_times['classify']:.2f}s")

            # Step 3: Analyze context
            step_start = time.time()
            context_assessment = self.context_analyzer.analyze(repo_data, context)
            step_times["context"] = time.time() - step_start
            print(f"✓ Context analysis completed in {step_times['context']:.2f}s")

            # Step 4: Score confidence and risk
            step_start = time.time()
            confidence_analysis = self.confidence_scorer.score_confidence_and_risk(
                repo_data, classification, context_assessment
            )
            step_times["confidence"] = time.time() - step_start
            print(f"✓ Confidence scoring completed in {step_times['confidence']:.2f}s")

            # Step 5: Generate AI analysis (REAL Anthropic API call)
            step_start = time.time()
            # Use the simple analyze_repository that only takes repo_data
            ai_result = self.ai_analyzer.analyze_repository(repo_data)
            step_times["ai_analysis"] = time.time() - step_start
            print(
                f"✓ Anthropic API analysis completed in {step_times['ai_analysis']:.2f}s"
            )

            # Step 6: Generate report with evidence
            step_start = time.time()
            self.report_generator.generate_report(
                repo_data,
                classification,
                context_assessment,  # contextual_assessment parameter
                context,  # context (HiringContext)
                confidence_analysis,  # confidence_scoring
                ai_result,  # ai_analysis
                plan,  # subscription_plan
            )
            step_times["report"] = time.time() - step_start
            print(f"✓ Report generation completed in {step_times['report']:.2f}s")

            total_time = time.time() - start_time

            return {
                "success": True,
                "total_time": total_time,
                "step_times": step_times,
                "passes_30s": total_time < 30,
                "repo_size_mb": (
                    repo_data.size / 1024 if repo_data.size else 0
                ),  # Convert KB to MB
                "files_count": len(repo_data.file_structure),
                "commits_count": len(repo_data.recent_commits),
            }

        except Exception as e:
            total_time = time.time() - start_time
            return {
                "success": False,
                "error": str(e),
                "total_time": total_time,
                "step_times": step_times,
            }

    async def run_validation(self) -> None:
        """Run performance validation on test repositories."""
        # REAL repositories of various sizes and types - NO MOCKS
        test_cases = [
            # (repo_url, context, plan)
            (
                "https://github.com/sindresorhus/p-queue",  # Real: ~20 files, small lib
                HiringContext.STARTUP,
                SubscriptionPlan.PROFESSIONAL,
            ),
            (
                "https://github.com/facebook/react",  # Real: ~2000 files, large project
                HiringContext.ENTERPRISE,
                SubscriptionPlan.ENTERPRISE,
            ),
            (
                "https://github.com/tensorflow/tensorflow",  # Real: ~30000 files, massive
                HiringContext.AGENCY,  # Agency context - client flexibility focus
                SubscriptionPlan.ENTERPRISE,
            ),
            (
                "https://github.com/torvalds/linux",  # Real: ~70000 files, kernel
                HiringContext.OPEN_SOURCE,  # Linux kernel - classic open source
                SubscriptionPlan.ENTERPRISE,
            ),
        ]

        results = []
        for repo_url, context, plan in test_cases:
            result = await self.validate_repository(repo_url, context, plan)
            results.append((repo_url, result))

        # Print summary
        print("\n" + "=" * 80)
        print("PERFORMANCE VALIDATION SUMMARY")
        print("=" * 80)
        print(f"{'Repository':<50} {'Total Time':<12} {'Status':<10} {'Size (MB)':<10}")
        print("-" * 80)

        all_passed = True
        for repo_url, result in results:
            repo_name = repo_url.split("/")[-2] + "/" + repo_url.split("/")[-1]
            if result["success"]:
                status = "PASS" if result["passes_30s"] else "FAIL"
                if not result["passes_30s"]:
                    all_passed = False
                print(
                    f"{repo_name:<50} {result['total_time']:>8.2f}s   {status:<10} {result.get('repo_size_mb', 0):>8.1f}"
                )
            else:
                all_passed = False
                print(f"{repo_name:<50} {result['total_time']:>8.2f}s   ERROR      N/A")
                print(f"  Error: {result['error']}")

        print("\n" + "=" * 80)
        print(
            f"Overall Result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}"
        )
        print("=" * 80)

        # Detailed breakdown for any failures
        for repo_url, result in results:
            if result["success"] and not result["passes_30s"]:
                repo_name = repo_url.split("/")[-2] + "/" + repo_url.split("/")[-1]
                print(f"\nDetailed breakdown for {repo_name}:")
                for step, duration in result["step_times"].items():
                    print(f"  - {step:<15}: {duration:>6.2f}s")


async def main():
    """Run performance validation."""
    # Check for required environment variables
    if not os.getenv("GITHUB_TOKEN"):
        print("❌ Error: GITHUB_TOKEN environment variable not set")
        return

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ Error: ANTHROPIC_API_KEY environment variable not set")
        return

    print("⚠️  WARNING: This script makes REAL API calls!")
    print("   - GitHub API calls to fetch actual repository data")
    print("   - Anthropic API calls for AI analysis (costs ~$0.003-0.015 per repo)")
    print("   - Testing 4 real repositories (p-queue, React, TensorFlow, Linux kernel)")
    print("")

    validator = PerformanceValidator()
    await validator.run_validation()


if __name__ == "__main__":
    asyncio.run(main())
