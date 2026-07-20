#!/usr/bin/env python3
"""
Interactive runner for context-aware tests.
Choose what to test based on your needs.
"""

import subprocess


def display_menu():
    """Display test options."""
    print("\n🔬 CONTEXT-AWARE TESTING MENU")
    print("=" * 50)
    print("1. Quick Test - Single context/tier combo")
    print("2. Matrix Test - Different repos per context")
    print("3. Full Test - All 16 combinations (slow)")
    print("4. Specific Context - Test all tiers for one context")
    print("5. Specific Tier - Test all contexts for one tier")
    print("0. Exit")
    print("=" * 50)


def quick_test():
    """Run a single context/tier combination."""
    print("\nContexts: startup, enterprise, agency, open_source")
    print("Tiers: free, starter, growth, scale")

    context = input("\nEnter context: ").strip().lower()
    tier = input("Enter tier: ").strip().lower()

    print(f"\n🚀 Running {context}/{tier} test...")
    subprocess.run(
        [
            "poetry",
            "run",
            "python",
            "tests/validation/test_context_by_tier.py",
            context,
            tier,
        ]
    )


def matrix_test():
    """Run matrix test with different repos."""
    print("\nContexts: startup, enterprise, agency, open_source, all")
    context = input("\nEnter context (or 'all'): ").strip().lower()

    print("\nTiers: free, starter, growth, scale")
    tier = input("Enter tier (default: growth): ").strip().lower() or "growth"

    print("\n🚀 Running matrix test...")

    if context == "all":
        subprocess.run(
            ["poetry", "run", "python", "tests/validation/test_context_matrix.py"]
        )
    else:
        subprocess.run(
            [
                "poetry",
                "run",
                "python",
                "tests/validation/test_context_matrix.py",
                context,
                tier,
            ]
        )


def full_test():
    """Run all 16 combinations."""
    confirm = input(
        "\n⚠️  This will run 16 tests and may take 5-10 minutes. Continue? (y/n): "
    )

    if confirm.lower() == "y":
        print("\n🚀 Running all combinations...")
        subprocess.run(
            ["poetry", "run", "python", "tests/validation/test_context_by_tier.py"]
        )


def test_specific_context():
    """Test all tiers for a specific context."""
    print("\nContexts: startup, enterprise, agency, open_source")
    context = input("\nEnter context: ").strip().lower()

    print(f"\n🚀 Testing all tiers for {context} context...")

    tiers = ["free", "starter", "growth", "scale"]
    for tier in tiers:
        print(f"\n--- Testing {tier.upper()} tier ---")
        subprocess.run(
            [
                "poetry",
                "run",
                "python",
                "tests/validation/test_context_by_tier.py",
                context,
                tier,
            ]
        )


def test_specific_tier():
    """Test all contexts for a specific tier."""
    print("\nTiers: free, starter, growth, scale")
    tier = input("\nEnter tier: ").strip().lower()

    print(f"\n🚀 Testing all contexts for {tier} tier...")

    contexts = ["startup", "enterprise", "agency", "open_source"]
    for context in contexts:
        print(f"\n--- Testing {context.upper()} context ---")
        subprocess.run(
            [
                "poetry",
                "run",
                "python",
                "tests/validation/test_context_by_tier.py",
                context,
                tier,
            ]
        )


def main():
    """Main runner."""
    while True:
        display_menu()

        try:
            choice = input("\nSelect option (0-5): ").strip()

            if choice == "0":
                print("\n👋 Exiting...")
                break
            elif choice == "1":
                quick_test()
            elif choice == "2":
                matrix_test()
            elif choice == "3":
                full_test()
            elif choice == "4":
                test_specific_context()
            elif choice == "5":
                test_specific_tier()
            else:
                print("\n❌ Invalid option. Please try again.")

        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Exiting...")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
