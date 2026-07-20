# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Evidence-based behavioral analysis without arbitrary metrics.

This module analyzes observable patterns from commit history WITHOUT
imposing arbitrary thresholds, scores, or subjective categorizations.
"""

import re
from collections import defaultdict
from typing import Any, Dict, List

from ...data.models import CommitInfo, RepositoryData
from ...utils.logging import get_logger

logger = get_logger(__name__)


class BehavioralAnalyzerEvidenceBased:
    """Analyze behavioral patterns using only factual observations."""

    def __init__(self) -> None:
        """Initialize behavioral analyzer with pattern definitions."""
        # Communication patterns to look for (not judge)
        self.communication_patterns = {
            "collaborative": [
                r"(?i)\b(thanks|thank you|appreciate|helped by|pair|collaborated)\b",
                r"(?i)\b(co-authored|reviewed by|suggested by)\b",
            ],
            "responsive": [
                r"(?i)\b(address|addresses|fix|fixes|resolve|resolves)\s*#\d+",
                r"(?i)\b(response to|requested by|as discussed)\b",
            ],
            "documentation": [
                r"(?i)\b(docs?|documentation|readme|guide|tutorial)\b",
                r"(?i)\b(explain|clarify|describe|document)\b",
            ],
        }

        # Work style patterns to identify (not evaluate)
        self.work_patterns = {
            "methodical": [
                r"(?i)\b(refactor|clean|organize|restructure)\b",
                r"(?i)\b(step \d+|phase \d+|part \d+)\b",
            ],
            "detail_oriented": [
                r"(?i)\b(typo|spelling|format|style|lint)\b",
                r"(?i)\b(minor|small|tiny)\s+(fix|change|update)\b",
            ],
            "big_picture": [
                r"(?i)\b(architecture|design|system|infrastructure)\b",
                r"(?i)\b(major|significant|complete)\s+(overhaul|refactor|rewrite)\b",
            ],
        }

    def analyze_behavior(self, repo_data: RepositoryData) -> Dict[str, Any]:
        """
        Analyze behavioral patterns from repository data.

        Returns only factual observations without scores or judgments.
        """
        if not repo_data.recent_commits:
            return {
                "status": "no_data",
                "message": "No commits available for analysis",
                "observations": [],
            }

        observations = {
            "work_patterns": self._observe_work_patterns(repo_data),
            "collaboration_patterns": self._observe_collaboration_patterns(repo_data),
            "communication_patterns": self._observe_communication_patterns(repo_data),
            "time_patterns": self._observe_time_patterns(repo_data),
            "response_patterns": self._observe_response_patterns(repo_data),
            "leadership_indicators": self._observe_leadership_indicators(repo_data),
            "data_context": {
                "total_commits_analyzed": len(repo_data.recent_commits),
                "time_span": self._calculate_time_span(repo_data.recent_commits),
                "unique_contributors": len(
                    set(c.author_email for c in repo_data.recent_commits)
                ),
            },
        }

        # Generate summary of observations
        observations["summary"] = self._generate_observation_summary(observations)

        logger.info(
            f"Behavioral analysis complete: {len(observations)} pattern categories observed"
        )
        return observations

    def _observe_work_patterns(self, repo_data: RepositoryData) -> Dict[str, Any]:
        """Observe work patterns without imposing thresholds."""
        patterns: Dict[str, Any] = {
            "commit_messages_analyzed": len(repo_data.recent_commits),
            "patterns_found": defaultdict(list),
            "observations": [],
        }

        # Count occurrences of different patterns
        for commit in repo_data.recent_commits:
            for style, regexes in self.work_patterns.items():
                for regex in regexes:
                    if re.search(regex, commit.message):
                        patterns["patterns_found"][style].append(
                            {"commit": commit.sha[:8], "message": commit.message[:80]}
                        )

        # Report what was found
        for style, matches in patterns["patterns_found"].items():
            if matches:
                patterns["observations"].append(
                    f"Found {len(matches)} commits with {style.replace('_', ' ')} patterns"
                )

        return patterns

    def _observe_collaboration_patterns(
        self, repo_data: RepositoryData
    ) -> Dict[str, Any]:
        """Observe collaboration patterns in commits."""
        collab: Dict[str, Any] = {
            "team_mentions": [],
            "pr_references": [],
            "co_authoring": [],
            "collaborative_language": [],
            "observations": [],
        }

        for commit in repo_data.recent_commits:
            msg_lower = commit.message.lower()

            # Check for team mentions
            mentions = re.findall(r"@(\w+)", commit.message)
            if mentions:
                collab["team_mentions"].extend(mentions)

            # Check for PR/issue references
            references = re.findall(r"#(\d+)", commit.message)
            if references:
                collab["pr_references"].extend(references)

            # Check for co-authoring
            if "co-authored-by" in msg_lower:
                collab["co_authoring"].append(commit.sha[:8])

            # Check for collaborative language
            for pattern in self.communication_patterns["collaborative"]:
                if re.search(pattern, msg_lower):
                    collab["collaborative_language"].append(
                        {"commit": commit.sha[:8], "example": commit.message[:80]}
                    )
                    break

        # Generate observations
        if collab["team_mentions"]:
            unique_mentions = len(set(collab["team_mentions"]))
            collab["observations"].append(
                f"Mentioned {unique_mentions} different team members in {len(collab['team_mentions'])} commits"
            )

        if collab["pr_references"]:
            collab["observations"].append(
                f"Referenced {len(set(collab['pr_references']))} different issues/PRs"
            )

        if collab["co_authoring"]:
            collab["observations"].append(
                f"Co-authored {len(collab['co_authoring'])} commits"
            )

        return collab

    def _observe_communication_patterns(
        self, repo_data: RepositoryData
    ) -> Dict[str, Any]:
        """Observe communication quality in commits."""
        comm: Dict[str, Any] = {
            "commit_message_lengths": [],
            "multi_line_commits": 0,
            "documentation_commits": 0,
            "examples": [],
            "observations": [],
        }

        for commit in repo_data.recent_commits:
            msg_length = len(commit.message)
            comm["commit_message_lengths"].append(msg_length)

            # Check for multi-line commits
            if "\n" in commit.message:
                comm["multi_line_commits"] += 1

            # Check for documentation focus
            for pattern in self.communication_patterns["documentation"]:
                if re.search(pattern, commit.message):
                    comm["documentation_commits"] += 1
                    comm["examples"].append(commit.message[:100])
                    break

        # Generate observations
        if comm["commit_message_lengths"]:
            avg_length = sum(comm["commit_message_lengths"]) / len(
                comm["commit_message_lengths"]
            )
            comm["observations"].append(
                f"Average commit message length: {int(avg_length)} characters"
            )

        if comm["multi_line_commits"]:
            comm["observations"].append(
                f"{comm['multi_line_commits']} commits have detailed descriptions"
            )

        if comm["documentation_commits"]:
            comm["observations"].append(
                f"{comm['documentation_commits']} commits mention documentation"
            )

        return comm

    def _observe_time_patterns(self, repo_data: RepositoryData) -> Dict[str, Any]:
        """Observe when work happens without judgment."""
        time_patterns: Dict[str, Any] = {
            "commits_by_hour": defaultdict(int),
            "commits_by_day": defaultdict(int),
            "weekend_commits": 0,
            "late_night_commits": 0,
            "vacation_gaps": [],
            "observations": [],
        }

        sorted_commits = sorted(repo_data.recent_commits, key=lambda c: c.date)

        for commit in repo_data.recent_commits:
            hour = commit.date.hour
            weekday = commit.date.weekday()

            time_patterns["commits_by_hour"][hour] += 1
            time_patterns["commits_by_day"][weekday] += 1

            # Count weekend commits (Saturday=5, Sunday=6)
            if weekday >= 5:
                time_patterns["weekend_commits"] += 1

            # Count late night commits (10 PM - 4 AM)
            if hour >= 22 or hour < 4:
                time_patterns["late_night_commits"] += 1

        # Find vacation gaps
        for i in range(1, len(sorted_commits)):
            gap = sorted_commits[i].date - sorted_commits[i - 1].date
            if gap.days > 14:  # More than 2 weeks
                time_patterns["vacation_gaps"].append(
                    {
                        "start": sorted_commits[i - 1].date.isoformat(),
                        "end": sorted_commits[i].date.isoformat(),
                        "days": gap.days,
                    }
                )

        # Generate factual observations
        total = len(repo_data.recent_commits)

        if time_patterns["weekend_commits"]:
            time_patterns["observations"].append(
                f"{time_patterns['weekend_commits']} commits made on weekends (out of {total} total)"
            )

        if time_patterns["late_night_commits"]:
            time_patterns["observations"].append(
                f"{time_patterns['late_night_commits']} commits made between 10 PM and 4 AM"
            )

        if time_patterns["vacation_gaps"]:
            time_patterns["observations"].append(
                f"Found {len(time_patterns['vacation_gaps'])} periods with 2+ week gaps"
            )

        # Most active hour
        if time_patterns["commits_by_hour"]:
            peak_hour = max(
                time_patterns["commits_by_hour"].items(), key=lambda x: x[1]
            )
            time_patterns["observations"].append(
                f"Most active hour: {peak_hour[0]}:00 ({peak_hour[1]} commits)"
            )

        return time_patterns

    def _observe_response_patterns(self, repo_data: RepositoryData) -> Dict[str, Any]:
        """Observe how issues and problems are addressed."""
        responses: Dict[str, Any] = {
            "fix_commits": [],
            "response_commits": [],
            "observations": [],
        }

        for commit in repo_data.recent_commits:
            for pattern in self.communication_patterns["responsive"]:
                if re.search(pattern, commit.message):
                    if "fix" in commit.message.lower():
                        responses["fix_commits"].append(
                            {
                                "message": commit.message[:100],
                                "date": commit.date.isoformat(),
                            }
                        )
                    else:
                        responses["response_commits"].append(
                            {
                                "message": commit.message[:100],
                                "date": commit.date.isoformat(),
                            }
                        )
                    break

        # Generate observations
        if responses["fix_commits"]:
            responses["observations"].append(
                f"Found {len(responses['fix_commits'])} commits addressing fixes"
            )

        if responses["response_commits"]:
            responses["observations"].append(
                f"Found {len(responses['response_commits'])} commits responding to requests"
            )

        return responses

    def _observe_leadership_indicators(
        self, repo_data: RepositoryData
    ) -> Dict[str, Any]:
        """Observe potential leadership behaviors."""
        leadership: Dict[str, Any] = {
            "mentoring_language": 0,
            "decision_language": 0,
            "team_coordination": 0,
            "examples": [],
            "observations": [],
        }

        # Leadership keywords
        leadership_patterns = {
            "mentoring": r"(?i)\b(mentor|guide|help|assist|teach|explain to)\b",
            "decisions": r"(?i)\b(decided to|let's|we should|proposal|rfc)\b",
            "coordination": r"(?i)\b(team|everyone|all|folks)\b",
        }

        for commit in repo_data.recent_commits:
            msg_lower = commit.message.lower()

            for category, pattern in leadership_patterns.items():
                if re.search(pattern, msg_lower):
                    if category == "mentoring":
                        leadership["mentoring_language"] += 1
                    elif category == "decisions":
                        leadership["decision_language"] += 1
                    elif category == "coordination":
                        leadership["team_coordination"] += 1

                    leadership["examples"].append(
                        {"type": category, "message": commit.message[:100]}
                    )

        # Generate observations
        total_indicators = (
            leadership["mentoring_language"]
            + leadership["decision_language"]
            + leadership["team_coordination"]
        )

        if total_indicators > 0:
            leadership["observations"].append(
                f"Found {total_indicators} commits with leadership indicators"
            )

            if leadership["mentoring_language"]:
                leadership["observations"].append(
                    f"{leadership['mentoring_language']} commits show mentoring language"
                )

            if leadership["decision_language"]:
                leadership["observations"].append(
                    f"{leadership['decision_language']} commits show decision-making language"
                )

        return leadership

    def _calculate_time_span(self, commits: List[CommitInfo]) -> Dict[str, Any]:
        """Calculate the time span of commits."""
        if not commits:
            return {"days": 0, "description": "No commits"}

        sorted_commits = sorted(commits, key=lambda c: c.date)
        span = sorted_commits[-1].date - sorted_commits[0].date

        return {
            "days": span.days,
            "start": sorted_commits[0].date.isoformat(),
            "end": sorted_commits[-1].date.isoformat(),
            "description": f"{span.days} days",
        }

    def _generate_observation_summary(
        self, observations: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a summary of all observations."""
        summary: Dict[str, Any] = {
            "total_observations": 0,
            "key_findings": [],
            "data_limitations": [],
        }

        # Count all observations
        for category in observations:
            if (
                isinstance(observations[category], dict)
                and "observations" in observations[category]
            ):
                summary["total_observations"] += len(
                    observations[category]["observations"]
                )
                summary["key_findings"].extend(
                    observations[category]["observations"][:2]
                )

        # Note data limitations
        total_commits = observations["data_context"]["total_commits_analyzed"]
        if total_commits < 10:
            summary["data_limitations"].append(
                f"Limited data: only {total_commits} commits available"
            )

        time_span = observations["data_context"]["time_span"]["days"]
        if time_span < 30:
            summary["data_limitations"].append(
                f"Short time period: only {time_span} days of activity"
            )

        return summary

    def generate_behavioral_insights(self, repo_data: RepositoryData) -> List[str]:
        """Generate human-readable insights from observations."""
        analysis = self.analyze_behavior(repo_data)
        insights = []

        # Work patterns
        work = analysis.get("work_patterns", {})
        for obs in work.get("observations", []):
            insights.append(f"Work style: {obs}")

        # Collaboration
        collab = analysis.get("collaboration_patterns", {})
        for obs in collab.get("observations", []):
            insights.append(f"Collaboration: {obs}")

        # Time patterns
        time = analysis.get("time_patterns", {})
        for obs in time.get("observations", [])[:2]:  # Limit to top 2
            insights.append(f"Schedule: {obs}")

        return insights
