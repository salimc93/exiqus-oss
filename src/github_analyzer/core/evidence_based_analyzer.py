# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Evidence-based repository analyzer.

This module provides fact-based analysis without arbitrary scores or thresholds.
It focuses on observable patterns and provides context for interpretation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List

from ..utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Observation:
    """A single factual observation from repository analysis."""

    category: str  # technical, behavioral, collaboration, quality
    finding: str  # The factual observation
    evidence: List[str]  # Specific files, commits, or patterns
    context: str  # Additional context for interpretation
    data_limitations: List[str] = field(default_factory=list)  # What we can't determine
    interview_topics: List[str] = field(default_factory=list)  # Topics to explore


@dataclass
class DataSufficiency:
    """Information about the sufficiency of available data."""

    total_commits: int
    time_span_days: int
    contributors: int
    file_count: int
    languages: List[str]
    has_tests: bool
    has_documentation: bool
    limitations: List[str]

    @property
    def summary(self) -> str:
        """Human-readable summary of data availability."""
        parts = []
        parts.append(f"{self.total_commits} commits")
        parts.append(f"spanning {self.time_span_days} days")
        parts.append(
            f"from {self.contributors} contributor{'s' if self.contributors != 1 else ''}"
        )
        parts.append(f"across {self.file_count} files")
        return "Analysis based on " + ", ".join(parts)


@dataclass
class EvidenceBasedAnalysis:
    """Complete evidence-based analysis without arbitrary metrics."""

    observations: List[Observation]
    data_sufficiency: DataSufficiency
    patterns: List[Dict[str, Any]]  # Identified patterns with evidence
    interview_guidance: List[str]  # Suggested interview topics
    context_notes: Dict[str, str]  # Context-specific observations


class EvidenceBasedAnalyzer:
    """Analyzes repositories based on observable facts without arbitrary scoring."""

    def analyze(self, repo_data: Dict[str, Any]) -> EvidenceBasedAnalysis:
        """
        Perform evidence-based analysis on repository data.

        Args:
            repo_data: Raw repository data including commits, files, etc.

        Returns:
            EvidenceBasedAnalysis with observations and context
        """
        # Assess data sufficiency
        data_sufficiency = self._assess_data_sufficiency(repo_data)

        # Extract observations
        observations = []
        observations.extend(self._observe_technical_patterns(repo_data))
        observations.extend(self._observe_collaboration_patterns(repo_data))
        observations.extend(self._observe_quality_practices(repo_data))
        observations.extend(self._observe_work_patterns(repo_data, data_sufficiency))

        # Identify patterns
        patterns = self._identify_patterns(observations, repo_data)

        # Generate interview guidance
        interview_guidance = self._generate_interview_guidance(observations, patterns)

        # Add context notes
        context_notes = self._generate_context_notes(repo_data, observations)

        return EvidenceBasedAnalysis(
            observations=observations,
            data_sufficiency=data_sufficiency,
            patterns=patterns,
            interview_guidance=interview_guidance,
            context_notes=context_notes,
        )

    def _assess_data_sufficiency(self, repo_data: Dict[str, Any]) -> DataSufficiency:
        """Assess the sufficiency of available data."""
        commits = repo_data.get("commits", [])

        # Calculate time span
        if commits:
            dates = []
            for c in commits:
                date_val = c.get("date")
                if date_val:
                    # Handle both datetime objects and ISO strings
                    if isinstance(date_val, str):
                        dates.append(
                            datetime.fromisoformat(date_val.replace("Z", "+00:00"))
                        )
                    elif isinstance(date_val, datetime):
                        dates.append(date_val)

            if dates:
                oldest = min(dates)
                newest = max(dates)
                time_span = (newest - oldest).days
            else:
                time_span = 0
        else:
            time_span = 0

        # Count contributors
        contributors = set()
        for commit in commits:
            if commit.get("author"):
                contributors.add(commit["author"])

        # Identify limitations
        limitations = []
        if len(commits) < 10:
            limitations.append("Very limited commit history for pattern analysis")
        if time_span < 30:
            limitations.append("Short time span limits work pattern assessment")
        if len(contributors) == 1:
            limitations.append("Single contributor limits collaboration insights")
        if not repo_data.get("pull_requests"):
            limitations.append("No pull request data available")
        if not repo_data.get("issues"):
            limitations.append("No issue tracking data available")

        return DataSufficiency(
            total_commits=len(commits),
            time_span_days=time_span,
            contributors=len(contributors),
            file_count=len(repo_data.get("files", [])),
            languages=list(repo_data.get("languages", {}).keys()),
            has_tests=self._has_test_files(repo_data),
            has_documentation=self._has_documentation(repo_data),
            limitations=limitations,
        )

    def _observe_technical_patterns(
        self, repo_data: Dict[str, Any]
    ) -> List[Observation]:
        """Observe technical patterns without scoring."""
        observations = []

        # Language usage
        languages = repo_data.get("languages", {})
        if languages:
            primary_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)[
                :3
            ]
            lang_list = [f"{lang} ({count} files)" for lang, count in primary_langs]

            observations.append(
                Observation(
                    category="technical",
                    finding=f"Primary languages: {', '.join(lang_list)}",
                    evidence=[
                        f
                        for f in repo_data.get("files", [])
                        if any(f.endswith(ext) for ext in [".py", ".js", ".java"])
                    ],
                    context="Language distribution indicates technology stack",
                    interview_topics=[
                        "Experience with these languages in production",
                        "Language selection criteria for projects",
                    ],
                )
            )

        # Test presence
        test_files = self._find_test_files(repo_data)
        if test_files:
            observations.append(
                Observation(
                    category="quality",
                    finding=f"Found {len(test_files)} test files",
                    evidence=test_files[:5],  # Show first 5 as evidence
                    context="Test files present indicate testing practices",
                    interview_topics=[
                        "Testing philosophy and approach",
                        "How they decide what to test",
                        "Experience with test-driven development",
                    ],
                )
            )
        else:
            observations.append(
                Observation(
                    category="quality",
                    finding="No test files detected",
                    evidence=[],
                    context="Absence of tests in public repo doesn't indicate testing approach",
                    data_limitations=[
                        "Cannot assess testing practices from private work"
                    ],
                    interview_topics=[
                        "Quality assurance strategies",
                        "Testing in professional vs personal projects",
                    ],
                )
            )

        # Documentation
        doc_files = self._find_documentation_files(repo_data)
        if doc_files:
            observations.append(
                Observation(
                    category="technical",
                    finding=f"Documentation found in {len(doc_files)} files",
                    evidence=doc_files[:3],
                    context="Documentation presence suggests communication practices",
                    interview_topics=[
                        "Documentation philosophy",
                        "Balancing documentation with development speed",
                    ],
                )
            )

        return observations

    def _observe_collaboration_patterns(
        self, repo_data: Dict[str, Any]
    ) -> List[Observation]:
        """Observe collaboration patterns."""
        observations = []

        contributors = set()
        for commit in repo_data.get("commits", []):
            if commit.get("author"):
                contributors.add(commit["author"])

        if len(contributors) > 1:
            observations.append(
                Observation(
                    category="collaboration",
                    finding=f"Repository has {len(contributors)} contributors",
                    evidence=list(contributors)[:5],
                    context="Multiple contributors suggest collaborative work",
                    interview_topics=[
                        "Experience working in teams",
                        "Collaboration and communication style",
                        "Conflict resolution approaches",
                    ],
                )
            )
        else:
            observations.append(
                Observation(
                    category="collaboration",
                    finding="Single contributor repository",
                    evidence=[],
                    context="Solo project - collaboration skills need other assessment",
                    data_limitations=["Cannot assess team dynamics from solo work"],
                    interview_topics=[
                        "Team collaboration experience",
                        "Preferred working style",
                    ],
                )
            )

        # PR/Issue references in commits
        pr_refs = []
        issue_refs = []
        for commit in repo_data.get("commits", []):
            msg = commit.get("message", "")
            if "#" in msg:
                if "pull" in msg.lower() or "pr" in msg.lower():
                    pr_refs.append(commit["sha"][:7])
                else:
                    issue_refs.append(commit["sha"][:7])

        if pr_refs or issue_refs:
            observations.append(
                Observation(
                    category="collaboration",
                    finding=f"Found {len(pr_refs)} PR references and {len(issue_refs)} issue references in commits",
                    evidence=pr_refs[:3] + issue_refs[:3],
                    context="References suggest engagement with issue tracking",
                    interview_topics=[
                        "Approach to issue tracking and project management",
                        "Experience with different development workflows",
                    ],
                )
            )

        return observations

    def _observe_quality_practices(
        self, repo_data: Dict[str, Any]
    ) -> List[Observation]:
        """Observe quality practices without judging them."""
        observations = []

        # CI/CD configuration
        ci_files = self._find_ci_files(repo_data)
        if ci_files:
            observations.append(
                Observation(
                    category="quality",
                    finding=f"CI/CD configuration found: {', '.join(ci_files)}",
                    evidence=ci_files,
                    context="Automated pipeline configuration present",
                    interview_topics=[
                        "Experience with CI/CD pipelines",
                        "Automation philosophy",
                        "Deployment strategies",
                    ],
                )
            )

        # Linting/formatting configs
        quality_configs = self._find_quality_configs(repo_data)
        if quality_configs:
            observations.append(
                Observation(
                    category="quality",
                    finding=f"Code quality tools configured: {', '.join(quality_configs)}",
                    evidence=quality_configs,
                    context="Quality tooling suggests attention to code standards",
                    interview_topics=[
                        "Code quality standards and enforcement",
                        "Team conventions and standardization",
                    ],
                )
            )

        # Commit message patterns
        commit_messages = [
            c.get("message", "") for c in repo_data.get("commits", [])[:20]
        ]
        if commit_messages:
            conventional = sum(
                1
                for m in commit_messages
                if any(
                    m.startswith(prefix)
                    for prefix in ["feat:", "fix:", "docs:", "test:", "refactor:"]
                )
            )
            if conventional > 0:
                observations.append(
                    Observation(
                        category="quality",
                        finding=f"{conventional} of last {len(commit_messages)} commits follow conventional format",
                        evidence=commit_messages[:3],
                        context="Structured commit messages found",
                        interview_topics=[
                            "Commit message conventions",
                            "Team communication standards",
                        ],
                    )
                )

        return observations

    def _observe_work_patterns(
        self, repo_data: Dict[str, Any], sufficiency: DataSufficiency
    ) -> List[Observation]:
        """Observe work patterns without making judgments."""
        # REMOVED: All behavioral work pattern analysis to prevent biased inferences
        # about work ethic, dedication, or work-life balance based on commit timestamps
        return []

    def _identify_patterns(
        self, observations: List[Observation], repo_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify patterns from observations."""
        patterns = []

        # Quality-focused pattern
        quality_obs = [o for o in observations if o.category == "quality"]
        quality_indicators = sum(
            1
            for o in quality_obs
            if any(
                keyword in o.finding.lower()
                for keyword in ["test", "ci", "quality", "documentation"]
            )
        )

        if quality_indicators >= 2:
            patterns.append(
                {
                    "type": "quality_awareness",
                    "evidence": [o.finding for o in quality_obs],
                    "description": "Multiple quality practices observed",
                    "interview_focus": "Understanding quality philosophy and trade-offs",
                }
            )

        # Solo vs collaborative pattern
        collab_obs = [o for o in observations if o.category == "collaboration"]
        is_solo = any("single contributor" in o.finding.lower() for o in collab_obs)

        if is_solo:
            patterns.append(
                {
                    "type": "independent_work",
                    "evidence": ["Single contributor repository"],
                    "description": "Independent project work",
                    "interview_focus": "Team collaboration experience from other contexts",
                }
            )

        return patterns

    def _generate_interview_guidance(
        self, observations: List[Observation], patterns: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate interview guidance based on observations."""
        guidance = []

        # Collect all interview topics
        all_topics = []
        for obs in observations:
            all_topics.extend(obs.interview_topics)

        # Deduplicate and prioritize
        seen = set()
        for topic in all_topics:
            if topic not in seen:
                seen.add(topic)
                guidance.append(topic)

        # Add pattern-based guidance
        for pattern in patterns:
            if pattern.get("interview_focus"):
                guidance.append(pattern["interview_focus"])

        # Always include fundamental topics
        guidance.extend(
            [
                "Problem-solving approach on challenging tasks",
                "Learning strategies and growth mindset",
                "Communication style and preferences",
            ]
        )

        return list(dict.fromkeys(guidance))[:10]  # Limit to 10 unique topics

    def _generate_context_notes(
        self, repo_data: Dict[str, Any], observations: List[Observation]
    ) -> Dict[str, str]:
        """Generate context-specific notes."""
        context_notes = {}

        # For startup context
        has_tests = any("test" in o.finding.lower() for o in observations)
        has_ci = any("ci" in o.finding.lower() for o in observations)

        context_notes["startup"] = (
            "Repository shows "
            + (
                "some quality practices"
                if has_tests or has_ci
                else "limited quality tooling"
            )
            + ". Explore pragmatic approach to technical debt and iteration speed."
        )

        # For enterprise context
        has_docs = any("documentation" in o.finding.lower() for o in observations)
        context_notes["enterprise"] = (
            "Documentation "
            + ("present" if has_docs else "limited")
            + ". Discuss experience with enterprise processes and compliance requirements."
        )

        # For open source context
        contributors = next(
            (o for o in observations if "contributors" in o.finding), None
        )
        context_notes["open_source"] = (
            "Community collaboration "
            + (
                "visible"
                if contributors and "multiple" in contributors.finding.lower()
                else "limited"
            )
            + ". Explore open source contribution experience."
        )

        return context_notes

    def _has_test_files(self, repo_data: Dict[str, Any]) -> bool:
        """Check if repository has test files."""
        return len(self._find_test_files(repo_data)) > 0

    def _has_documentation(self, repo_data: Dict[str, Any]) -> bool:
        """Check if repository has documentation."""
        return len(self._find_documentation_files(repo_data)) > 0

    def _find_test_files(self, repo_data: Dict[str, Any]) -> List[str]:
        """Find test files in repository."""
        test_patterns = ["test_", "_test", "spec.", ".spec", "tests/", "test/"]
        files = repo_data.get("files", [])
        return [
            f for f in files if any(pattern in f.lower() for pattern in test_patterns)
        ]

    def _find_documentation_files(self, repo_data: Dict[str, Any]) -> List[str]:
        """Find documentation files."""
        doc_patterns = ["readme", "docs/", "documentation", ".md", "wiki"]
        files = repo_data.get("files", [])
        return [
            f for f in files if any(pattern in f.lower() for pattern in doc_patterns)
        ]

    def _find_ci_files(self, repo_data: Dict[str, Any]) -> List[str]:
        """Find CI/CD configuration files."""
        ci_patterns = [
            ".github/workflows",
            ".gitlab-ci",
            "jenkinsfile",
            ".travis",
            "circle.yml",
            "azure-pipelines",
            "bitbucket-pipelines",
            ".drone",
        ]
        files = repo_data.get("files", [])
        return [
            f for f in files if any(pattern in f.lower() for pattern in ci_patterns)
        ]

    def _find_quality_configs(self, repo_data: Dict[str, Any]) -> List[str]:
        """Find code quality tool configurations."""
        quality_patterns = [
            ".eslintrc",
            ".prettierrc",
            ".pylintrc",
            ".flake8",
            "pyproject.toml",
            ".rubocop",
            "tslint.json",
            ".editorconfig",
            "setup.cfg",
        ]
        files = repo_data.get("files", [])
        return [
            f
            for f in files
            if any(pattern in f.lower() for pattern in quality_patterns)
        ]
