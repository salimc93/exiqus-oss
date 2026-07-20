#!/usr/bin/env python3
"""
Simulate the enterprise context fix to verify it works before implementation.
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class MockRepo:
    """Mock repository for testing."""

    total_commits: int = 500
    commit_frequency: float = 2.5
    unique_contributors: int = 10
    has_tests: bool = True
    has_readme: bool = True
    has_ci_config: bool = True
    has_contributing: bool = True
    has_license: bool = True
    test_coverage_estimate: float = 0.75
    languages: Dict[str, int] = None
    file_structure: List = None

    def __post_init__(self):
        if self.languages is None:
            self.languages = {"Python": 80, "JavaScript": 20}
        if self.file_structure is None:
            self.file_structure = [
                type("File", (), {"name": "src", "type": "directory"}),
                type("File", (), {"name": "tests", "type": "directory"}),
                type("File", (), {"name": "docs", "type": "directory"}),
                type("File", (), {"name": "lib", "type": "directory"}),
            ]


def simulate_current_scoring(repo: MockRepo, context: str) -> float:
    """Simulate current biased scoring."""
    base_score = 0.5

    # Current positive signals for enterprise
    if context == "enterprise":
        positive_signals = [
            "comprehensive_testing",
            "detailed_documentation",
            "design_patterns",
            "scalable_architecture",
            "security_focus",
            "code_reviews",
            "ci_cd_pipeline",
        ]

        # Count matches (FastAPI might match 3-4 of these)
        matches = 0
        if repo.has_tests and repo.test_coverage_estimate > 0.6:
            matches += 1  # comprehensive_testing
        if repo.has_readme:
            matches += 1  # detailed_documentation (partial)
        if repo.has_ci_config:
            matches += 1  # ci_cd_pipeline
        # Missing: design_patterns, scalable_architecture, security_focus, code_reviews

        positive_ratio = matches / len(positive_signals)  # 3/7 = 0.43
        positive_contribution = positive_ratio * 0.5  # 0.215 (BIASED multiplier)

        # Negative signals
        # FastAPI has no negative signals
        negative_penalty = 0

        # Weight adjustments
        weight_contributions = 0.1  # Some bonuses

        score = (
            base_score + positive_contribution - negative_penalty + weight_contributions
        )
        # 0.5 + 0.215 - 0 + 0.1 = 0.815

        # But enterprise has penalty in current code
        score -= 0.3  # Various penalties in actual implementation

        return min(max(score, 0), 1.0)  # ~0.52

    else:  # startup/agency/open_source
        # These contexts have easier signals and better multipliers
        positive_contribution = 0.3  # Easier to achieve
        weight_contributions = 0.2  # More bonuses

        score = base_score + positive_contribution + weight_contributions
        return min(max(score, 0), 1.0)  # ~1.0


def simulate_fixed_scoring(repo: MockRepo, context: str) -> float:
    """Simulate fixed balanced scoring."""
    base_score = 0.5

    if context == "enterprise":
        # Updated positive signals (more achievable)
        positive_signals = [
            "comprehensive_testing",
            "detailed_documentation",
            "scalable_architecture",
            "ci_cd_pipeline",
            "consistent_commits",  # NEW
            "structured_codebase",  # NEW
            "team_collaboration",  # NEW
        ]

        # Count matches with new signals
        matches = 0
        if repo.has_tests and repo.test_coverage_estimate > 0.6:
            matches += 1  # comprehensive_testing
        if repo.has_readme:
            matches += 1  # detailed_documentation
        if repo.has_ci_config:
            matches += 1  # ci_cd_pipeline
        if repo.total_commits > 50 and repo.commit_frequency > 0.5:
            matches += 1  # consistent_commits (NEW)
        if (
            len([f for f in repo.file_structure if f.name in ["src", "lib", "tests"]])
            >= 3
        ):
            matches += 1  # structured_codebase (NEW)
        if repo.unique_contributors >= 2:
            matches += 1  # team_collaboration (NEW)

        positive_ratio = matches / len(positive_signals)  # 6/7 = 0.86
        positive_contribution = positive_ratio * 0.4  # 0.34 (FIXED multiplier)

        # Weight adjustments
        weight_contributions = 0.15  # Process and scale bonuses

        score = base_score + positive_contribution + weight_contributions
        # 0.5 + 0.34 + 0.15 = 0.99

        return min(max(score, 0), 1.0)

    else:
        # Keep other contexts the same
        return simulate_current_scoring(repo, context)


def test_fix():
    """Test the enterprise context fix."""
    print("🧪 TESTING ENTERPRISE CONTEXT FIX")
    print("=" * 60)

    # Create a good repository (like FastAPI)
    good_repo = MockRepo()

    contexts = ["startup", "enterprise", "agency", "open_source"]

    print("\n📊 CURRENT SCORING (with bias):")
    print("-" * 40)
    current_scores = {}
    for context in contexts:
        score = simulate_current_scoring(good_repo, context)
        current_scores[context] = score
        print(f"{context:12} {score:.1%}")

    print("\n📊 FIXED SCORING (balanced):")
    print("-" * 40)
    fixed_scores = {}
    for context in contexts:
        score = simulate_fixed_scoring(good_repo, context)
        fixed_scores[context] = score
        print(f"{context:12} {score:.1%}")

    # Analyze improvement
    print("\n📈 IMPROVEMENT ANALYSIS:")
    print("-" * 40)

    enterprise_improvement = fixed_scores["enterprise"] - current_scores["enterprise"]
    print(f"Enterprise score improvement: +{enterprise_improvement:.1%}")

    # Check if bias is fixed
    fixed_spread = max(fixed_scores.values()) - min(fixed_scores.values())
    current_spread = max(current_scores.values()) - min(current_scores.values())

    print("\nScore spread (max-min):")
    print(f"  Current: {current_spread:.1%}")
    print(f"  Fixed:   {fixed_spread:.1%}")

    if fixed_spread < 0.2:
        print("\n✅ SUCCESS: All contexts now score within 20% of each other!")
    else:
        print("\n⚠️  Still some bias, but much improved")

    # Test with a mediocre repo
    print("\n\n🧪 TESTING WITH MEDIOCRE REPOSITORY:")
    print("-" * 40)

    mediocre_repo = MockRepo(
        total_commits=30,
        commit_frequency=0.3,
        unique_contributors=1,
        has_tests=False,
        test_coverage_estimate=0,
    )

    print("Mediocre repo characteristics:")
    print("  - Only 30 commits")
    print("  - No tests")
    print("  - Single contributor")

    print("\nFixed scoring for mediocre repo:")
    for context in contexts:
        score = simulate_fixed_scoring(mediocre_repo, context)
        print(f"{context:12} {score:.1%}")


def test_fallback_strategy():
    """Test API fallback strategy for different tiers."""
    print("\n\n🔄 API FALLBACK STRATEGY")
    print("=" * 60)

    print("Current implementation:")
    print("  FREE/BASIC: Haiku 3.0 → Fallback to rule-based")
    print("  GROWTH: Haiku 3.0 + Haiku 3.5 → Fallback to Haiku 3.0")
    print("  SCALE: Haiku 3.5 + Sonnet 3.5 → Fallback to Haiku 3.5")

    print("\n✅ BETTER STRATEGY:")
    print("  FREE/BASIC: Haiku 3.0 → Fallback to rule-based")
    print("  GROWTH: Haiku 3.5 (questions) → Fallback to Haiku 3.5 with reduced tokens")
    print("  SCALE: Sonnet 3.5 (questions) → Fallback to Haiku 3.5")

    print("\nRationale:")
    print("  - GROWTH users paid for Haiku 3.5, should get it even during overload")
    print("  - SCALE users can fallback to Haiku 3.5 (still premium)")
    print("  - Reduce tokens/questions during overload, not model quality")


if __name__ == "__main__":
    test_fix()
    test_fallback_strategy()
