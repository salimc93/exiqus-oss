#!/usr/bin/env python3
"""
Verify that API response includes sub_metrics field.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import json  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

from github_analyzer.api.routes.analysis import (  # noqa: E402
    _perform_repository_analysis,
)
from github_analyzer.data.github_fetcher import GitHubFetcher  # noqa: E402
from github_analyzer.database.models import SubscriptionPlan, User  # noqa: E402
from github_analyzer.utils.config import get_config  # noqa: E402


async def verify_sub_metrics():
    """Verify sub_metrics are included in API response."""
    config = get_config()
    github_fetcher = GitHubFetcher(config.github_token)

    # Mock user
    user = User(
        id="test_user",
        email="test@example.com",
        github_username="test",
        subscription_plan=SubscriptionPlan.ENTERPRISE,
        subscription_status="active",
    )

    print("🔍 Verifying API response includes sub_metrics...")

    # Perform analysis
    response = await _perform_repository_analysis(
        repository_url="https://github.com/sindresorhus/p-queue",
        context="startup",
        start_time=datetime.now(timezone.utc),
        github_fetcher=github_fetcher,
        user=user,
        size_limit_mb=1000,
        output_format="json",
    )

    # Check if sub_metrics are in the response
    analysis = response.analysis
    sections_with_metrics = []

    for section_name in [
        "technical_assessment",
        "professional_practices",
        "communication_skills",
        "growth_indicators",
    ]:
        section = analysis.get(section_name)
        if section and "sub_metrics" in section:
            sub_metrics = section["sub_metrics"]
            if sub_metrics:
                sections_with_metrics.append(section_name)
                print(f"\n✅ {section_name} has {len(sub_metrics)} sub_metrics:")
                for metric in sub_metrics[:2]:  # Show first 2
                    print(f"   - {metric.get('name')}: {metric.get('percentage')}%")

    if sections_with_metrics:
        print(
            f"\n✅ SUCCESS: Sub_metrics found in {len(sections_with_metrics)} sections"
        )
        print(f"   Sections: {', '.join(sections_with_metrics)}")
    else:
        print("\n❌ WARNING: No sub_metrics found in any section")

    # Save full response for inspection
    with open("/tmp/api_response_sample.json", "w") as f:
        json.dump(response.model_dump(), f, indent=2, default=str)
    print("\nFull response saved to /tmp/api_response_sample.json")


def main():
    import asyncio

    if not os.getenv("GITHUB_TOKEN") or not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ Error: Missing environment variables")
        return

    asyncio.run(verify_sub_metrics())


if __name__ == "__main__":
    main()
