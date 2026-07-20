# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Temporal analysis of repository evolution and developer growth.

This module analyzes how skills, patterns, and practices evolve over time,
providing insights into learning velocity and growth trajectories.
"""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from ...data.models import CommitInfo, RepositoryData
from ...utils.logging import get_logger

logger = get_logger(__name__)


class TemporalAnalyzer:
    """Analyze temporal patterns and evolution in repository history."""

    def __init__(self) -> None:
        """Initialize temporal analyzer."""
        self.time_windows = {
            "week": timedelta(days=7),
            "month": timedelta(days=30),
            "quarter": timedelta(days=90),
            "year": timedelta(days=365),
        }

    def analyze_skill_evolution(self, repo_data: RepositoryData) -> Dict[str, Any]:
        """
        Analyze how technical skills have evolved over time.

        Args:
            repo_data: Repository data to analyze

        Returns:
            Dictionary containing skill evolution insights
        """
        if not repo_data.recent_commits:
            return {"error": "No commits to analyze"}

        analysis = {
            "commit_patterns": self._analyze_commit_evolution(repo_data.recent_commits),
            "language_evolution": self._analyze_language_trends(repo_data),
            "complexity_growth": self._analyze_complexity_evolution(
                repo_data.recent_commits
            ),
            "learning_indicators": self._identify_learning_patterns(
                repo_data.recent_commits
            ),
            "activity_trends": self._analyze_activity_trends(repo_data.recent_commits),
        }

        # Generate overall growth assessment
        analysis["growth_summary"] = self._generate_growth_summary(analysis)

        return analysis

    def _analyze_commit_evolution(self, commits: List[CommitInfo]) -> Dict[str, Any]:
        """Analyze how commit patterns have evolved."""
        if not commits:
            return {}

        # Sort commits by date (oldest first)
        sorted_commits = sorted(commits, key=lambda c: c.date)

        # Split into time periods
        total_duration = sorted_commits[-1].date - sorted_commits[0].date
        if total_duration.days < 30:
            # Too short for meaningful evolution analysis
            return {
                "duration_days": total_duration.days,
                "insufficient_data": True,
            }

        # Analyze first vs last quarter
        mid_point = sorted_commits[0].date + (total_duration / 2)
        early_commits = [c for c in sorted_commits if c.date < mid_point]
        recent_commits = [c for c in sorted_commits if c.date >= mid_point]

        early_period_analysis = self._analyze_commit_quality(early_commits)
        recent_period_analysis = self._analyze_commit_quality(recent_commits)

        evolution = {
            "duration_days": total_duration.days,
            "early_period": early_period_analysis,
            "recent_period": recent_period_analysis,
        }

        # Calculate improvement based on evidence patterns
        early_indicators = early_period_analysis.get("quality_indicators", 0)
        recent_indicators = recent_period_analysis.get("quality_indicators", 0)

        evolution["improvement"] = {
            "improved": recent_indicators > early_indicators,
            "message_length_change": (
                int(recent_period_analysis["avg_message_length"])
                - int(early_period_analysis["avg_message_length"])
            ),
        }

        return evolution

    def _analyze_commit_quality(self, commits: List[CommitInfo]) -> Dict[str, Any]:
        """Analyze quality metrics for a set of commits."""
        if not commits:
            return {"quality_indicators": 0}

        quality_indicators = {
            "has_conventional_format": 0,  # feat:, fix:, etc.
            "has_description": 0,  # Multi-line commits
            "references_issue": 0,  # #123, fixes #456
            "proper_capitalization": 0,
            "no_typos": 0,  # Basic spell check
        }

        total_message_length = 0
        total_changes = 0

        for commit in commits:
            msg = commit.message
            total_message_length += len(msg)

            # Check conventional format
            if any(
                msg.lower().startswith(prefix)
                for prefix in [
                    "feat:",
                    "fix:",
                    "docs:",
                    "style:",
                    "refactor:",
                    "test:",
                    "chore:",
                ]
            ):
                quality_indicators["has_conventional_format"] += 1

            # Check for description (multi-line)
            if "\n" in msg and len(msg.split("\n", 1)[1].strip()) > 10:
                quality_indicators["has_description"] += 1

            # Check for issue references
            if "#" in msg and any(char.isdigit() for char in msg):
                quality_indicators["references_issue"] += 1

            # Check capitalization
            if msg and msg[0].isupper():
                quality_indicators["proper_capitalization"] += 1

            # Calculate change size
            if commit.additions is not None and commit.deletions is not None:
                total_changes += commit.additions + commit.deletions

        # Calculate total quality indicators found (evidence-based approach)
        total_quality_indicators = sum(quality_indicators.values())

        return {
            "quality_indicators": total_quality_indicators,
            "avg_message_length": total_message_length // len(commits),
            "avg_change_size": total_changes // len(commits) if commits else 0,
            "quality_breakdown": {k: v for k, v in quality_indicators.items()},
        }

    def _analyze_language_trends(self, repo_data: RepositoryData) -> Dict[str, Any]:
        """Analyze trends in language usage over time."""
        # This is simplified since we don't have historical language data
        # In a real implementation, we'd analyze file changes over time

        if not repo_data.languages:
            return {"no_language_data": True}

        trends = {
            "current_languages": repo_data.languages,
            "primary_language": max(repo_data.languages.items(), key=lambda x: x[1])[0],
            "language_diversity": len(repo_data.languages),
        }

        # Analyze file additions by extension in recent commits
        extension_timeline = defaultdict(list)

        for commit in repo_data.recent_commits[:50]:  # Last 50 commits
            # We'd need file-level commit data for accurate analysis
            # This is a simplified version based on commit messages
            msg_lower = commit.message.lower()

            # Comprehensive language detection - covering ALL languages
            for lang, extensions in {
                # Common languages
                "Python": ["py", "python", "django", "flask", "pytest"],
                "JavaScript": ["js", "javascript", "node", "npm", "webpack"],
                "TypeScript": ["ts", "typescript", "tsc"],
                "Go": ["go", "golang"],
                "Java": ["java", "spring", "maven", "gradle"],
                "C++": ["cpp", "c++", "cmake"],
                "C": ["c ", "gcc", "clang"],
                "Rust": ["rust", "cargo", "rustc"],
                "Ruby": ["ruby", "rb", "rails", "gem"],
                "PHP": ["php", "laravel", "symfony"],
                # Functional languages
                "Haskell": ["haskell", "hs", "stack", "cabal"],
                "Scala": ["scala", "sbt", "akka"],
                "Clojure": ["clojure", "clj", "lein"],
                "Elixir": ["elixir", "ex", "phoenix", "mix"],
                "Erlang": ["erlang", "erl", "otp"],
                "F#": ["f#", "fsharp", "dotnet"],
                "OCaml": ["ocaml", "ml", "dune"],
                # Lisp family
                "Lisp": ["lisp", "common lisp", "cl", "sbcl"],
                "Scheme": ["scheme", "scm", "racket"],
                "Emacs Lisp": ["elisp", "emacs"],
                # Other languages
                "Swift": ["swift", "ios", "xcode"],
                "Kotlin": ["kotlin", "kt", "android"],
                "Dart": ["dart", "flutter"],
                "Julia": ["julia", "jl"],
                "R": ["r ", "rstats", "tidyverse"],
                "MATLAB": ["matlab", "octave"],
                "Fortran": ["fortran", "f90", "f77"],
                "COBOL": ["cobol", "cbl"],
                "Ada": ["ada"],
                "Nim": ["nim", "nimble"],
                "Crystal": ["crystal", "cr"],
                "Zig": ["zig"],
                "V": ["vlang"],
                "D": ["dlang", "dmd"],
                # Web/Frontend
                "React": ["react", "jsx", "next.js"],
                "Vue": ["vue", "vuex", "nuxt"],
                "Angular": ["angular", "ng "],
                "Svelte": ["svelte", "sveltekit"],
                # Database
                "SQL": ["sql", "postgres", "mysql", "sqlite"],
                "MongoDB": ["mongo", "mongodb", "mongoose"],
                "Redis": ["redis"],
                # Shell/Script
                "Bash": ["bash", "shell", "sh "],
                "PowerShell": ["powershell", "ps1"],
                # Infrastructure
                "Terraform": ["terraform", "tf ", "hcl"],
                "Ansible": ["ansible", "playbook"],
                "Docker": ["docker", "dockerfile", "container"],
                "Kubernetes": ["kubernetes", "k8s", "kubectl"],
            }.items():
                if any(ext in msg_lower for ext in extensions):
                    extension_timeline[lang].append(commit.date)

        # Find new languages adopted
        trends["language_mentions"] = {
            lang: len(dates) for lang, dates in extension_timeline.items()
        }

        return trends

    def _analyze_complexity_evolution(
        self, commits: List[CommitInfo]
    ) -> Dict[str, Any]:
        """Analyze how code complexity has evolved based on commit patterns."""
        if len(commits) < 10:
            return {"insufficient_data": True}

        # Group commits by time period
        sorted_commits = sorted(commits, key=lambda c: c.date)

        # Analyze commit size trends
        time_periods: List[Dict[str, Any]] = []
        period_size = max(1, len(sorted_commits) // 4)  # Quarterly analysis

        for i in range(0, len(sorted_commits), period_size):
            period_commits = sorted_commits[i : i + period_size]
            if not period_commits:
                continue

            sizes = [
                c.additions + c.deletions
                for c in period_commits
                if c.additions is not None and c.deletions is not None
            ]

            if sizes:
                time_periods.append(
                    {
                        "period_start": period_commits[0].date,
                        "period_end": period_commits[-1].date,
                        "avg_commit_size": sum(sizes) / len(sizes),
                        "max_commit_size": max(sizes),
                        "commit_count": len(period_commits),
                    }
                )

        if len(time_periods) < 2:
            return {"insufficient_periods": True}

        # Analyze trends
        size_trend = (
            "increasing"
            if float(time_periods[-1]["avg_commit_size"])
            > float(time_periods[0]["avg_commit_size"])
            else "decreasing"
        )

        return {
            "periods_analyzed": len(time_periods),
            "size_trend": size_trend,
            "early_avg_size": time_periods[0]["avg_commit_size"],
            "recent_avg_size": time_periods[-1]["avg_commit_size"],
            "insight": self._interpret_complexity_trend(size_trend, time_periods),
        }

    def _identify_learning_patterns(
        self, commits: List[CommitInfo]
    ) -> List[Dict[str, Any]]:
        """Identify patterns that indicate learning and growth."""
        patterns = []

        # Look for experimentation patterns
        experiment_keywords = [
            "experiment",
            "try",
            "attempt",
            "test",
            "poc",
            "prototype",
        ]
        experimentation_commits = [
            c
            for c in commits
            if any(keyword in c.message.lower() for keyword in experiment_keywords)
        ]

        if experimentation_commits:
            patterns.append(
                {
                    "type": "experimentation",
                    "count": len(experimentation_commits),
                    "examples": [c.message[:80] for c in experimentation_commits[:3]],
                    "insight": "Shows willingness to experiment and learn",
                }
            )

        # Look for learning from mistakes
        fix_patterns = ["fix", "fixed", "correct", "mistake", "error", "bug"]
        learning_commits = []

        for i, commit in enumerate(commits[1:], 1):
            if any(pattern in commit.message.lower() for pattern in fix_patterns):
                # Check if fixing own recent work
                prev_commits = commits[max(0, i - 5) : i]
                if any(
                    prev.author_email == commit.author_email for prev in prev_commits
                ):
                    learning_commits.append(commit)

        if learning_commits:
            patterns.append(
                {
                    "type": "learning_from_mistakes",
                    "count": len(learning_commits),
                    "examples": [c.message[:80] for c in learning_commits[:3]],
                    "insight": "Actively fixes and improves own code",
                }
            )

        # Look for adoption of new practices
        practice_keywords = {
            "typing": ["type hint", "typing", "mypy", "typescript"],
            "testing": ["add test", "test coverage", "unit test", "integration test"],
            "documentation": ["add docs", "document", "readme", "docstring"],
            "ci_cd": ["ci", "cd", "pipeline", "github action", "workflow"],
        }

        for practice, keywords in practice_keywords.items():
            matching_commits = [
                c
                for c in commits
                if any(keyword in c.message.lower() for keyword in keywords)
            ]

            if matching_commits:
                patterns.append(
                    {
                        "type": f"adopting_{practice}",
                        "count": len(matching_commits),
                        "first_seen": matching_commits[-1].date.strftime("%Y-%m-%d"),
                        "last_seen": matching_commits[0].date.strftime("%Y-%m-%d"),
                        "insight": f"Adopted {practice.replace('_', ' ')} practices",
                    }
                )

        return patterns

    def _analyze_activity_trends(self, commits: List[CommitInfo]) -> Dict[str, Any]:
        """Analyze activity level trends over time."""
        if not commits:
            return {}

        now = datetime.now(timezone.utc)

        # Calculate activity by time window
        activity = {}
        for window_name, window_delta in self.time_windows.items():
            window_commits = [c for c in commits if (now - c.date) <= window_delta]
            activity[window_name] = len(window_commits)

        # Analyze commit frequency trends
        sorted_commits = sorted(commits, key=lambda c: c.date)
        duration = (sorted_commits[-1].date - sorted_commits[0].date).days

        if duration > 0:
            overall_frequency = len(commits) / duration * 7  # Commits per week
        else:
            overall_frequency = 0

        # Calculate momentum (recent vs historical activity)
        if activity["month"] > 0 and activity["quarter"] > 0:
            momentum = activity["week"] / (activity["month"] / 4)  # Current vs average
        else:
            momentum = 0

        return {
            "activity_by_period": activity,
            "overall_frequency": round(overall_frequency, 2),
            "momentum": round(momentum, 2),
            "momentum_interpretation": self._interpret_momentum(momentum),
            "consistency": self._calculate_consistency(commits),
        }

    def _calculate_consistency(self, commits: List[CommitInfo]) -> Dict[str, Any]:
        """Calculate consistency metrics."""
        if len(commits) < 7:
            return {"insufficient_data": True}

        # Group commits by week
        weeks: Dict[tuple[int, int], int] = defaultdict(int)
        for commit in commits:
            week_key = commit.date.isocalendar()[:2]  # (year, week_number)
            weeks[week_key] += 1

        if not weeks:
            return {"no_weekly_data": True}

        # Calculate consistency metrics
        active_weeks = len(weeks)

        week_counts = list(weeks.values())
        avg_commits_per_active_week = sum(week_counts) / len(week_counts)

        # Calculate consistency based on active weeks (evidence-based)
        total_possible_weeks = (commits[-1].date - commits[0].date).days // 7 + 1
        consistency_evidence = active_weeks

        # Evidence-based interpretation
        if active_weeks >= total_possible_weeks * 0.7:
            interpretation = "Highly consistent"
        elif active_weeks >= total_possible_weeks * 0.4:
            interpretation = "Moderate consistency"
        else:
            interpretation = "Variable activity"

        return {
            "active_weeks": active_weeks,
            "consistency_evidence": consistency_evidence,
            "avg_commits_per_week": round(avg_commits_per_active_week, 2),
            "interpretation": interpretation,
        }

    def _generate_growth_summary(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate an overall growth summary."""
        summary: Dict[str, Any] = {
            "growth_indicators": [],
            "challenges": [],
            "trajectory": "unknown",
        }

        # Check commit quality evolution
        if "commit_patterns" in analysis and not analysis["commit_patterns"].get(
            "insufficient_data"
        ):
            improvement = analysis["commit_patterns"].get("improvement", {})
            if improvement.get("improved"):
                summary["growth_indicators"].append(
                    "Commit quality shows improvement over time"
                )
            else:
                summary["challenges"].append("Commit quality needs attention")

        # Check learning patterns
        if "learning_indicators" in analysis and analysis["learning_indicators"]:
            summary["growth_indicators"].append(
                f"Found {len(analysis['learning_indicators'])} learning patterns"
            )

        # Check activity trends
        if "activity_trends" in analysis:
            momentum = analysis["activity_trends"].get("momentum", 0)
            if momentum > 1.2:
                summary["growth_indicators"].append("Increasing development momentum")
            elif momentum < 0.5:
                summary["challenges"].append("Declining activity levels")

        # Determine overall trajectory
        if len(summary["growth_indicators"]) > len(summary["challenges"]):
            summary["trajectory"] = "positive"
        elif len(summary["challenges"]) > len(summary["growth_indicators"]):
            summary["trajectory"] = "needs_attention"
        else:
            summary["trajectory"] = "stable"

        return summary

    def _interpret_complexity_trend(
        self, trend: str, periods: List[Dict[str, Any]]
    ) -> str:
        """Interpret what complexity trends mean."""
        if trend == "increasing":
            return "Taking on more complex changes over time"
        elif trend == "decreasing":
            return "Moving towards smaller, focused commits"
        else:
            return "Maintaining consistent commit complexity"

    def _interpret_momentum(self, momentum: float) -> str:
        """Interpret momentum score."""
        if momentum > 1.5:
            return "Significantly increased activity"
        elif momentum > 1.1:
            return "Increasing activity"
        elif momentum > 0.9:
            return "Stable activity"
        elif momentum > 0.5:
            return "Decreasing activity"
        else:
            return "Significantly reduced activity"

    def generate_evolution_insights(self, repo_data: RepositoryData) -> List[str]:
        """Generate human-readable insights about skill evolution."""
        analysis = self.analyze_skill_evolution(repo_data)
        insights = []

        # Commit quality evolution
        if "commit_patterns" in analysis and analysis["commit_patterns"].get(
            "improvement"
        ):
            imp = analysis["commit_patterns"]["improvement"]
            if imp["improved"]:
                insights.append("Commit quality has improved over project lifetime")

        # Learning patterns
        if "learning_indicators" in analysis:
            for pattern in analysis["learning_indicators"]:
                if pattern["type"] == "experimentation":
                    insights.append(
                        f"Shows experimentation mindset with {pattern['count']} experimental commits"
                    )
                elif pattern["type"] == "learning_from_mistakes":
                    insights.append(
                        "Demonstrates learning velocity by fixing own mistakes quickly"
                    )

        # Activity trends
        if "activity_trends" in analysis:
            trends = analysis["activity_trends"]
            if trends.get("momentum", 0) > 1.2:
                insights.append(
                    f"Momentum increasing: {trends['momentum']:.1f}x recent activity vs average"
                )

        return insights
