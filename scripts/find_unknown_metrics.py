#!/usr/bin/env python3
"""
Extract unknown metrics from test outputs.
"""

# From the test outputs, these metrics were flagged as unknown:
unknown_metrics = [
    "Architectural Complexity",
    "Continuous Integration",
    "Issue Tracking",
    "Documentation Ratio",
    "Communication Quality",
    "Collaboration Patterns",
    "Collaboration Engagement",
    "Refactoring Ratio",
    "Refactoring Practices",
    "Refactoring Efforts",
    "Bug Fixing Ratio",
    "Activity Trend",
    "Commit Discipline",
    "Contribution Diversity",
    "Skill Progression",
    "Complexity Management",
    "Complexity Trend",
    "Domain Expertise",
    "Clarity of Communication",
    "Clarity of Commit Messages",
    "Commit Message Quality",
    "Commit Frequency",
    "Documentation Quality",
    "Documentation Clarity",
    "Commitment to Security",
]

# Group by category
categories = {
    "Technical Practices": [
        "Architectural Complexity",
        "Continuous Integration",
        "Issue Tracking",
        "Documentation Ratio",
        "Documentation Quality",
        "Documentation Clarity",
        "Complexity Management",
        "Complexity Trend",
        "Domain Expertise",
        "Commitment to Security",
    ],
    "Professional Practices": [
        "Refactoring Ratio",
        "Refactoring Practices",
        "Refactoring Efforts",
        "Bug Fixing Ratio",
        "Commit Discipline",
        "Commit Frequency",
    ],
    "Communication & Collaboration": [
        "Communication Quality",
        "Collaboration Patterns",
        "Collaboration Engagement",
        "Contribution Diversity",
        "Clarity of Communication",
        "Clarity of Commit Messages",
        "Commit Message Quality",
    ],
    "Growth & Development": [
        "Activity Trend",
        "Skill Progression",
    ],
}

print("UNKNOWN METRICS TO ADD TO docs/technical/METHODOLOGY.md")
print("=" * 50)
print(f"Total unknown metrics: {len(unknown_metrics)}")
print("\nGrouped by category:")

for category, metrics in categories.items():
    print(f"\n{category}:")
    for metric in sorted(metrics):
        print(f"  - {metric}")

print("\n\nSUGGESTED CONFIDENCE RANGES:")
print("=" * 50)

# Suggest confidence ranges based on metric type
confidence_suggestions = {
    "Technical Practices": "65-85%",
    "Professional Practices": "55-75%",
    "Communication & Collaboration": "45-70%",
    "Growth & Development": "40-65%",
}

for category, confidence in confidence_suggestions.items():
    print(f"\n{category}: {confidence}")
    metrics = categories[category]
    for metric in sorted(metrics):
        print(f"  - {metric}: {confidence}")
