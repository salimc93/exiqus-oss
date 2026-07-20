#!/usr/bin/env python3
"""
Test a single repository to verify fixes.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.test_full_analysis_transparency import (  # noqa: E402
    FullAnalysisTransparencyTest,
)

from github_analyzer.core.context_analyzer import HiringContext  # noqa: E402
from github_analyzer.database.models import SubscriptionPlan  # noqa: E402


def main():
    if not os.getenv("GITHUB_TOKEN") or not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ Error: Missing environment variables")
        return

    print("🔬 SINGLE REPO TEST")
    print("Testing p-queue with all fixes applied...")
    print("")

    tester = FullAnalysisTransparencyTest()

    # Test just p-queue
    tester.run_transparent_analysis(
        "https://github.com/sindresorhus/p-queue",
        HiringContext.STARTUP,
        SubscriptionPlan.ENTERPRISE,
    )

    print("\n✅ TEST COMPLETE")


if __name__ == "__main__":
    main()
