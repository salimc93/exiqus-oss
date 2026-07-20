#!/usr/bin/env python3
"""
Pre-push testing script for GitHub Analyzer Project.

This script runs all quality checks that must pass before pushing code.
It ensures consistent code quality and prevents broken commits.

Usage:
    python scripts/test_before_push.py
"""

import subprocess
import sys
import time
from pathlib import Path
from typing import List, Tuple

# ANSI color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


class QualityChecker:
    """Runs quality checks for the project."""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.checks_passed = []
        self.checks_failed = []

    def run_command(self, cmd: List[str], description: str) -> Tuple[bool, str]:
        """Run a command and return success status and output."""
        print(f"\n{BLUE}▶ {description}{RESET}")
        print(f"  Command: {' '.join(cmd)}")

        start_time = time.time()
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=self.project_root
            )
            elapsed = time.time() - start_time

            if result.returncode == 0:
                print(f"{GREEN}✓ PASSED{RESET} ({elapsed:.1f}s)")
                return True, result.stdout
            else:
                print(f"{RED}✗ FAILED{RESET} ({elapsed:.1f}s)")
                if result.stderr:
                    print(f"  Error: {result.stderr}")
                return False, result.stderr or result.stdout

        except Exception as e:
            print(f"{RED}✗ ERROR{RESET}: {str(e)}")
            return False, str(e)

    def check_ruff_format(self) -> bool:
        """Check code formatting with Ruff."""
        success, _ = self.run_command(
            [
                "poetry",
                "run",
                "ruff",
                "format",
                "--check",
                "src/",
                "tests/",
                "scripts/",
            ],
            "Checking code formatting (Ruff)",
        )
        return success

    def check_ruff_lint(self) -> bool:
        """Check linting, import order and security rules with Ruff."""
        success, _ = self.run_command(
            ["poetry", "run", "ruff", "check", "src/", "tests/", "scripts/"],
            "Checking lint, imports and security (Ruff)",
        )
        return success

    def check_mypy(self) -> bool:
        """Check type hints with MyPy."""
        success, _ = self.run_command(
            ["poetry", "run", "mypy", "src/github_analyzer/"],
            "Checking type hints (MyPy)",
        )
        return success

    def run_tests(self) -> Tuple[bool, float]:
        """Run pytest and return success status and coverage percentage."""
        success, output = self.run_command(
            [
                "poetry",
                "run",
                "pytest",
                "tests/unit/",
                "-v",
                "--cov=src/github_analyzer",
                "--cov-report=term",
            ],
            "Running unit tests (Pytest)",
        )

        # Extract coverage percentage from output
        coverage = 0.0
        if success:
            for line in output.split("\n"):
                if "TOTAL" in line and "%" in line:
                    try:
                        # Extract percentage from line like "TOTAL    1803    692    62%"
                        parts = line.split()
                        for part in parts:
                            if part.endswith("%"):
                                coverage = float(part.rstrip("%"))
                                break
                    except (ValueError, IndexError):
                        pass

        return success, coverage

    def check_pre_commit(self) -> bool:
        """Run pre-commit hooks."""
        success, _ = self.run_command(
            ["pre-commit", "run", "--all-files"], "Running pre-commit hooks"
        )
        return success

    def run_all_checks(self) -> bool:
        """Run all quality checks and return overall success status."""
        print(f"{BOLD}🚀 GitHub Analyzer Pre-Push Quality Checks{RESET}")
        print("=" * 50)

        # Run formatting check
        if self.check_ruff_format():
            self.checks_passed.append("Ruff (formatting)")
        else:
            self.checks_failed.append("Ruff (formatting)")
            print(
                f"{YELLOW}  Tip: Run 'poetry run ruff format src/ tests/ "
                f"scripts/' to fix{RESET}"
            )

        # Run linting check (includes import order and security rules)
        if self.check_ruff_lint():
            self.checks_passed.append("Ruff (lint, imports, security)")
        else:
            self.checks_failed.append("Ruff (lint, imports, security)")
            print(
                f"{YELLOW}  Tip: Run 'poetry run ruff check --fix src/ tests/ "
                f"scripts/' to fix{RESET}"
            )

        # Run type checking
        if self.check_mypy():
            self.checks_passed.append("MyPy (type checking)")
        else:
            self.checks_failed.append("MyPy (type checking)")

        # Run tests with coverage
        test_success, coverage = self.run_tests()
        if test_success:
            self.checks_passed.append(f"Pytest (coverage: {coverage}%)")
            if coverage < 80:
                print(
                    f"{YELLOW}  Warning: Coverage {coverage}% is below 80% target{RESET}"
                )
        else:
            self.checks_failed.append("Pytest")

        # Summary
        print(f"\n{BOLD}📊 Summary{RESET}")
        print("=" * 50)

        if self.checks_passed:
            print(f"{GREEN}✓ Passed ({len(self.checks_passed)}):{RESET}")
            for check in self.checks_passed:
                print(f"  • {check}")

        if self.checks_failed:
            print(f"\n{RED}✗ Failed ({len(self.checks_failed)}):{RESET}")
            for check in self.checks_failed:
                print(f"  • {check}")

        # Overall result
        all_passed = len(self.checks_failed) == 0

        print("\n" + "=" * 50)
        if all_passed:
            print(f"{GREEN}{BOLD}✅ All checks passed! Safe to push.{RESET}")
        else:
            print(
                f"{RED}{BOLD}❌ Some checks failed. Please fix before pushing.{RESET}"
            )
            print(
                f"\n{YELLOW}Run 'poetry run ruff format src/ tests/ scripts/' "
                f"to auto-fix formatting{RESET}"
            )

        return all_passed


def main():
    """Main entry point."""
    checker = QualityChecker()

    # Check if poetry is installed
    try:
        subprocess.run(["poetry", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"{RED}Error: Poetry is not installed or not in PATH{RESET}")
        print("Please install Poetry: https://python-poetry.org/docs/#installation")
        sys.exit(1)

    # Run all checks
    success = checker.run_all_checks()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
