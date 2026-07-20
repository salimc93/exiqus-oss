#!/usr/bin/env python3
"""
Combine individual test results into a single file for analysis.
"""

import glob
import json
import os


def combine_results():
    """Combine all context/tier results into one file."""

    all_results = []

    # Find all result files
    result_files = glob.glob("tests/validation/*_result.json")

    for file_path in result_files:
        # Extract context and tier from filename
        filename = os.path.basename(file_path)
        # Remove _result.json suffix
        name_without_suffix = filename.replace("_result.json", "")

        # Handle multi-word contexts like open_source
        if "_growth" in name_without_suffix:
            parts = name_without_suffix.split("_growth")
            context = parts[0]
            tier = "growth"
        elif "_" in name_without_suffix:
            parts = name_without_suffix.split("_")
            if len(parts) == 2:
                context, tier = parts
            else:
                # Handle cases like open_source_growth
                context = "_".join(parts[:-1])
                tier = parts[-1]
        else:
            continue

        # Load the result
        with open(file_path, "r") as f:
            result = json.load(f)

            # Ensure context and tier are set
            result["context"] = context
            result["tier"] = tier

            all_results.append(result)
            print(f"✓ Loaded {context}/{tier}")

    # Save combined results
    output_file = "tests/validation/ALL_CONTEXT_TIER_RESULTS.json"
    with open(output_file, "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\n💾 Combined {len(all_results)} results into: {output_file}")

    return all_results


if __name__ == "__main__":
    results = combine_results()

    # Show summary
    print("\nSummary by tier:")
    tiers = {}
    for r in results:
        tier = r.get("tier", "unknown")
        if tier not in tiers:
            tiers[tier] = []
        tiers[tier].append(r.get("context", "unknown"))

    for tier, contexts in tiers.items():
        print(f"  {tier}: {', '.join(contexts)}")
