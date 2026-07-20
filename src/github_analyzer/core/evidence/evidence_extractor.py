# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Evidence extraction from repository data.

This module extracts specific, actionable evidence from commits, files, and patterns
to support AI-generated recommendations with concrete examples.
"""

import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Set

from ...data.models import CommitInfo, FileInfo, RepositoryData
from ...utils.logging import get_logger

# from .models import DataQualityInfo
from .temporal_analyzer import TemporalAnalyzer

logger = get_logger(__name__)


class EvidenceExtractor:
    """Extract specific evidence from repository data for actionable insights."""

    def __init__(self) -> None:
        """Initialize evidence extractor with pattern definitions."""
        # Initialize sub-analyzers
        self.temporal_analyzer = TemporalAnalyzer()

        # Security patterns to detect
        self.security_patterns = {
            "hardcoded_secrets": [
                r"(?i)(api[_-]?key|api[_-]?secret|access[_-]?token)\s*=\s*['\"][^'\"]+['\"]",
                r"(?i)password\s*=\s*['\"][^'\"]+['\"]",
                r"(?i)bearer\s+[a-zA-Z0-9\-\._~\+\/]+=*",
            ],
            "weak_crypto": [
                r"(?i)\b(md5|sha1)\s*\(",
                r"(?i)\.createHash\s*\(\s*['\"]md5['\"]",
                r"(?i)hashlib\.(md5|sha1)",
            ],
            "sql_injection": [
                r"(?i)query\s*\(\s*['\"].*\+.*['\"]",
                r"(?i)execute\s*\(\s*f['\"].*{.*}.*['\"]",
                r"(?i)\.raw\s*\(\s*[`'\"].*\$\{.*\}.*[`'\"]",
                r"(?i)sql\s*injection",  # Match commit messages about SQL injection
            ],
        }

        # Code quality patterns
        self.quality_patterns = {
            "todo_fixme": r"(?i)\b(todo|fixme|hack|xxx)\b",
            "console_log": r"console\.(log|error|warn|info)",
            "print_statement": r"\bprint\s*\(",
            "commented_code": r"^\s*[#/]{1,2}.*[;{}]\s*$",
        }

        # Testing patterns
        self.test_patterns = {
            "test_files": r"(test_|_test\.|\.test\.|spec\.|\.spec\.)",
            "test_frameworks": r"(?i)(pytest|jest|mocha|jasmine|unittest|rspec)",
            "assertions": r"(?i)(assert|expect|should|describe|it\(|test\()",
        }

        # Complexity patterns
        self.complexity_patterns = {
            "refactoring": r"(?i)(refactor|simplify|clean\s*up|reduce\s*complexity|improve\s*readability)",
            "complex_structures": r"(?i)(algorithm|recursive|nested|complex|intricate)",
            "architectural": r"(?i)(architecture|design\s*pattern|abstraction|interface|dependency)",
        }

        # Domain pattern indicators
        self.domain_patterns = {
            "distributed_systems": r"(?i)(microservice|distributed|event\s*driven|message\s*queue|kafka|rabbitmq|redis|grpc)",
            "real_time": r"(?i)(websocket|real\s*time|streaming|live|socket\.io|sse|server\s*sent)",
            "data_processing": r"(?i)(etl|pipeline|batch|stream|spark|hadoop|airflow|celery)",
            "financial": r"(?i)(payment|transaction|billing|stripe|paypal|crypto|blockchain|wallet)",
            "security": r"(?i)(auth|oauth|jwt|security|encrypt|hash|ssl|tls|cors)",
            "devops": r"(?i)(docker|kubernetes|k8s|terraform|ansible|jenkins|cicd|deployment)",
            "machine_learning": r"(?i)(ml|machine\s*learning|ai|neural|model|tensor|sklearn|pytorch)",
            "web_frameworks": r"(?i)(react|vue|angular|django|flask|rails|spring|express)",
        }

    def extract_all_evidence(self, repo_data: RepositoryData) -> Dict[str, Any]:
        """
        Extract all types of evidence from repository data.

        Args:
            repo_data: Repository data to analyze

        Returns:
            Dictionary containing categorized evidence
        """
        evidence = {
            "technical_patterns": self.extract_technical_evidence(repo_data),
            "security_issues": self.extract_security_evidence(repo_data),
            "collaboration_patterns": self.extract_collaboration_evidence(repo_data),
            "quality_indicators": self.extract_quality_evidence(repo_data),
            "temporal_insights": self.extract_temporal_evidence(repo_data),
            "skill_evolution": self._integrate_temporal_analysis(repo_data),
            "domain_patterns": self._extract_domain_patterns(repo_data),
        }

        logger.info(
            f"Extracted evidence: {sum(len(v) if isinstance(v, list) else 1 for v in evidence.values())} total items"
        )
        return evidence

    def extract_technical_evidence(
        self, repo_data: RepositoryData
    ) -> List[Dict[str, Any]]:
        """Extract technical skill evidence from code patterns and structure."""
        evidence: List[Dict[str, Any]] = []

        # Analyze language distribution
        if repo_data.languages:
            total_bytes = sum(repo_data.languages.values())
            primary_lang = max(repo_data.languages.items(), key=lambda x: x[1])
            evidence.append(
                {
                    "type": "language_expertise",
                    "finding": f"Primary language {primary_lang[0]} ({primary_lang[1] / total_bytes:.1%} of codebase)",
                    "languages": repo_data.languages,
                    "insight": "Language distribution shows specialization",
                }
            )

        # Analyze file structure patterns
        if repo_data.file_structure:
            structure_insights = self._analyze_file_structure(repo_data.file_structure)
            evidence.extend(structure_insights)

        # Analyze test coverage
        test_evidence = self._analyze_test_coverage(repo_data)
        if test_evidence:
            evidence.extend(test_evidence)

        # Analyze commit patterns
        if repo_data.recent_commits:
            commit_insights = self._analyze_commit_patterns(repo_data.recent_commits)
            evidence.extend(commit_insights)

        # Analyze code complexity
        complexity_evidence = self._analyze_code_complexity(repo_data)
        if complexity_evidence:
            evidence.extend(complexity_evidence)

        return evidence

    def extract_security_evidence(
        self, repo_data: RepositoryData
    ) -> List[Dict[str, Any]]:
        """Extract security-related evidence from commits and patterns."""
        evidence: List[Dict[str, Any]] = []

        # Search for security patterns in recent commits
        for commit in repo_data.recent_commits[:30]:  # Last 30 commits
            for pattern_type, patterns in self.security_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, commit.message, re.IGNORECASE):
                        evidence.append(
                            {
                                "type": "security_pattern",
                                "finding": f"Potential {pattern_type.replace('_', ' ')} in commit",
                                "commit_sha": commit.sha[:7],
                                "commit_message": commit.message[:100],
                                "severity": (
                                    "high"
                                    if pattern_type == "hardcoded_secrets"
                                    else "medium"
                                ),
                            }
                        )

        # Check for security-related files
        security_files = [
            f
            for f in repo_data.file_structure
            if any(
                sec in f.name.lower()
                for sec in ["security", "auth", "encrypt", "token", "crypto"]
            )
        ]

        if security_files:
            evidence.append(
                {
                    "type": "security_awareness",
                    "finding": f"Found {len(security_files)} security-related files",
                    "files": [f.path for f in security_files[:5]],
                    "insight": "Shows security consciousness in architecture",
                }
            )

        return evidence

    def extract_collaboration_evidence(
        self, repo_data: RepositoryData
    ) -> List[Dict[str, Any]]:
        """Extract evidence of collaboration and team dynamics."""
        evidence: List[Dict[str, Any]] = []

        if not repo_data.recent_commits:
            return evidence

        # Analyze contributor patterns using GitHub usernames
        # Extract repo owner from repository name (e.g., "sarahli-mp3" from "sarahli-mp3/rate-my-matcha")
        repo_owner = (
            repo_data.name.split("/")[0].lower() if "/" in repo_data.name else ""
        )

        contributors: Dict[str, int] = defaultdict(int)
        for commit in repo_data.recent_commits:
            # Use author_login (GitHub username) if available
            if commit.author_login:
                username = commit.author_login.lower()
                # Filter out bots
                if not username.endswith("[bot]"):
                    contributors[username] += 1
            else:
                # If no GitHub login available, assume it's the repo owner
                # (commits from local git without linked GitHub account)
                # This handles cases where developer commits from local machine
                # with different git configs (personal@macbook vs github username)
                if repo_owner:
                    contributors[repo_owner] += 1
                else:
                    # Fallback to email if we can't determine owner
                    contributors[commit.author_email] += 1

        # Only create collaboration evidence if there are TRULY multiple distinct GitHub users
        # (not just different git configs from the same person)
        distinct_github_users = {
            commit.author_login.lower()
            for commit in repo_data.recent_commits
            if commit.author_login and not commit.author_login.endswith("[bot]")
        }

        if len(distinct_github_users) > 1:
            evidence.append(
                {
                    "type": "collaboration",
                    "finding": f"{len(distinct_github_users)} distinct GitHub users have commits in this repository",
                    "top_contributors": sorted(
                        [(username, count) for username, count in contributors.items()],
                        key=lambda x: x[1],
                        reverse=True,
                    )[:3],
                    "insight": f"Repository has commits from {len(distinct_github_users)} different GitHub accounts",
                }
            )

        # Analyze commit message quality
        good_messages = [
            c
            for c in repo_data.recent_commits
            if len(c.message) > 50
            and any(
                prefix in c.message.lower()
                for prefix in ["feat:", "fix:", "docs:", "refactor:", "test:"]
            )
        ]

        if good_messages:
            evidence.append(
                {
                    "type": "commit_discipline",
                    "finding": f"{len(good_messages)}/{len(repo_data.recent_commits)} commits follow conventions",
                    "examples": [msg.message[:80] for msg in good_messages[:3]],
                    "insight": "Follows professional commit practices",
                }
            )

        # Check for PR/issue references
        pr_references = [
            c
            for c in repo_data.recent_commits
            if re.search(
                r"#\d+|pull request|pr\s*#|issue\s*#|fixes\s*#",
                c.message,
                re.IGNORECASE,
            )
        ]

        if pr_references:
            evidence.append(
                {
                    "type": "issue_tracking",
                    "finding": f"{len(pr_references)} commits reference issues/PRs",
                    "examples": [ref.message[:80] for ref in pr_references[:3]],
                    "insight": "Uses proper issue tracking workflow",
                }
            )

        return evidence

    def extract_quality_evidence(
        self, repo_data: RepositoryData
    ) -> List[Dict[str, Any]]:
        """Extract code quality indicators."""
        evidence: List[Dict[str, Any]] = []

        # Count TODOs/FIXMEs in recent commits
        todo_commits = []
        for commit in repo_data.recent_commits[:50]:
            if re.search(self.quality_patterns["todo_fixme"], commit.message):
                todo_commits.append(commit)

        if todo_commits:
            evidence.append(
                {
                    "type": "technical_debt",
                    "finding": f"{len(todo_commits)} commits mention TODO/FIXME",
                    "examples": [c.message[:80] for c in todo_commits[:3]],
                    "insight": "Tracks technical debt explicitly",
                }
            )

        # Analyze refactoring patterns
        refactor_commits = [
            c
            for c in repo_data.recent_commits
            if re.search(r"(?i)(refactor|clean|improve|optimize)", c.message)
        ]

        if refactor_commits:
            evidence.append(
                {
                    "type": "code_maintenance",
                    "finding": f"{len(refactor_commits)} refactoring commits",
                    "examples": [c.message[:80] for c in refactor_commits[:3]],
                    "recent_refactor": refactor_commits[0].date.strftime("%Y-%m-%d"),
                    "insight": "Actively maintains code quality",
                }
            )

        # Check documentation updates
        doc_files = [f for f in repo_data.file_structure if f.is_documentation]
        if doc_files:
            evidence.append(
                {
                    "type": "documentation",
                    "finding": f"{len(doc_files)} documentation files maintained",
                    "files": [f.path for f in doc_files[:5]],
                    "has_readme": repo_data.has_readme,
                    "insight": "Values documentation",
                }
            )

        return evidence

    def extract_temporal_evidence(
        self, repo_data: RepositoryData
    ) -> List[Dict[str, Any]]:
        """Extract time-based patterns and evolution."""
        evidence: List[Dict[str, Any]] = []

        if not repo_data.recent_commits:
            return evidence

        # Analyze commit frequency over time
        now = datetime.now(timezone.utc)
        last_week = [c for c in repo_data.recent_commits if (now - c.date).days <= 7]
        last_month = [c for c in repo_data.recent_commits if (now - c.date).days <= 30]

        # Qualitative activity assessment
        activity_level = "inactive"
        daily_avg = len(last_week) / 7
        if daily_avg >= 3:
            activity_level = "very active"
        elif daily_avg >= 1:
            activity_level = "active"
        elif daily_avg >= 0.3:
            activity_level = "moderately active"
        elif daily_avg > 0:
            activity_level = "low activity"

        evidence.append(
            {
                "type": "activity_pattern",
                "finding": f"{len(last_week)} commits in last week, {len(last_month)} in last month",
                "activity_level": activity_level,
                "insight": "Recent activity level",
            }
        )

        # Analyze commit size evolution
        if len(repo_data.recent_commits) >= 10:
            recent_sizes = []
            for commit in repo_data.recent_commits[:10]:
                if commit.additions is not None and commit.deletions is not None:
                    recent_sizes.append(commit.additions + commit.deletions)

            if recent_sizes:
                avg_size = sum(recent_sizes) / len(recent_sizes)
                evidence.append(
                    {
                        "type": "commit_size_pattern",
                        "finding": f"Average commit size: {avg_size:.0f} lines",
                        "largest": max(recent_sizes),
                        "smallest": min(recent_sizes),
                        "insight": "Commit granularity habits",
                    }
                )

        return evidence

    def _analyze_file_structure(self, files: List[FileInfo]) -> List[Dict[str, Any]]:
        """Analyze file structure for architectural insights."""
        insights = []

        # Check for modern patterns
        has_src = any(f.path.startswith("src/") for f in files)

        if has_src:
            insights.append(
                {
                    "type": "architecture",
                    "finding": "Uses src/ directory structure",
                    "insight": "Follows modern project organization",
                }
            )

        # Analyze test file ratio - language agnostic approach
        test_files = [f for f in files if f.is_test]
        # Instead of hardcoding extensions, use a more comprehensive approach
        code_extensions = self._get_code_file_extensions(files)
        code_files = [f for f in files if f.extension in code_extensions]

        if test_files and code_files:
            test_ratio = len(test_files) / len(code_files)
            insights.append(
                {
                    "type": "test_coverage_structure",
                    "finding": f"{len(test_files)} test files for {len(code_files)} code files",
                    "ratio": str(test_ratio),
                    "insight": f"{'Good' if test_ratio > 0.3 else 'Limited'} test coverage structure",
                }
            )

        return insights

    def _analyze_test_coverage(self, repo_data: RepositoryData) -> List[Dict[str, Any]]:
        """Analyze testing patterns and coverage."""
        evidence: List[Dict[str, Any]] = []

        # Look for test-related commits
        test_commits = [
            c
            for c in repo_data.recent_commits
            if re.search(r"(?i)(test|spec|coverage)", c.message)
        ]

        if test_commits:
            evidence.append(
                {
                    "type": "testing_activity",
                    "finding": f"{len(test_commits)} test-related commits",
                    "recent_test": test_commits[0].message[:80],
                    "recent_date": test_commits[0].date.strftime("%Y-%m-%d"),
                    "insight": "Active test development",
                }
            )

        # Check for CI/CD evidence
        ci_commits = [
            c
            for c in repo_data.recent_commits
            if re.search(r"(?i)(ci|cd|pipeline|workflow|github.actions)", c.message)
        ]

        if ci_commits:
            evidence.append(
                {
                    "type": "ci_cd_usage",
                    "finding": f"{len(ci_commits)} CI/CD related commits",
                    "examples": [c.message[:80] for c in ci_commits[:2]],
                    "insight": "Uses automated testing/deployment",
                }
            )

        return evidence

    def _analyze_commit_patterns(
        self, commits: List[CommitInfo]
    ) -> List[Dict[str, Any]]:
        """Analyze patterns in commit history."""
        insights = []

        # Find large refactoring commits
        large_commits = [
            c
            for c in commits
            if c.additions is not None
            and c.deletions is not None
            and (c.additions + c.deletions) > 500
        ]

        if large_commits:
            # Analyze what type of large changes these are
            largest = large_commits[0]
            total_changes = (largest.additions or 0) + (largest.deletions or 0)
            is_feature_development = (largest.additions or 0) > (largest.deletions or 0)

            # Provide context about what large commits indicate for hiring
            if is_feature_development:
                insight = f"Capable of substantial feature development (largest: {total_changes:,} lines added). Indicates ability to handle complex implementations."
            else:
                insight = f"Performs major refactoring/restructuring (largest: {total_changes:,} lines changed). Shows code quality focus and ability to manage technical debt."

            # Clean up the commit message for readability
            commit_msg = largest.message.split("\n")[0]  # Get first line only
            # Extract meaningful part before any issue/PR references
            if "(" in commit_msg:
                commit_msg = commit_msg.split("(")[0].strip()
            elif "[" in commit_msg:
                commit_msg = commit_msg.split("[")[0].strip()
            # Remove prefixes like "feat:", "fix:", etc. for cleaner reading
            for prefix in [
                "feat:",
                "fix:",
                "docs:",
                "refactor:",
                "test:",
                "chore:",
                "perf:",
                "style:",
            ]:
                if commit_msg.lower().startswith(prefix):
                    commit_msg = commit_msg[len(prefix) :].strip()
                    break

            # Create more understandable evidence text
            if len(large_commits) == 1:
                evidence_text = f"Made 1 substantial code change ({total_changes:,} lines modified) - {commit_msg}"
            else:
                evidence_text = f"Made {len(large_commits)} substantial code changes (500+ lines each). Largest change: {total_changes:,} lines for '{commit_msg}'"

            insights.append(
                {
                    "type": "major_changes",
                    "finding": evidence_text,
                    "largest": {
                        "sha": largest.sha[:7],
                        "size": total_changes,
                        "message": largest.message[:80],
                        "type": (
                            "feature development"
                            if is_feature_development
                            else "refactoring/restructuring"
                        ),
                    },
                    "insight": insight,
                }
            )

        # Find bug fix patterns
        bug_fixes = [
            c
            for c in commits
            if re.search(r"(?i)(fix|bug|issue|problem|error)", c.message)
        ]

        if bug_fixes:
            insights.append(
                {
                    "type": "bug_fixing",
                    "finding": f"{len(bug_fixes)} bug fix commits ({len(bug_fixes) / len(commits) * 100:.0f}%)",
                    "recent_fixes": [f.message[:80] for f in bug_fixes[:3]],
                    "insight": "Active problem solver",
                }
            )

        return insights

    def get_evidence_summary(
        self, evidence: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Generate a summary of extracted evidence."""
        high_value_findings: List[Dict[str, Any]] = []
        key_insights: List[str] = []

        summary = {
            "total_evidence_points": sum(
                len(v) if isinstance(v, list) else 1 for v in evidence.values()
            ),
            "categories": {
                category: len(items) if isinstance(items, list) else 1
                for category, items in evidence.items()
            },
            "high_value_findings": high_value_findings,
            "key_insights": key_insights,
        }

        # Extract high-value findings
        for category, items in evidence.items():
            if isinstance(items, list):
                for item in items:
                    if item.get("severity") == "high" or (
                        isinstance(item.get("ratio", 0), (int, float))
                        and item.get("ratio", 0) > 0.5
                    ):
                        high_value_findings.append(
                            {
                                "category": category,
                                "finding": item.get("finding", ""),
                                "insight": item.get("insight", ""),
                            }
                        )
            elif isinstance(items, dict) and items.get("behavioral_insights"):
                # Handle behavioral analysis dict
                for insight in items.get("behavioral_insights", []):
                    if insight.get("type") in ["work_consistency", "collaboration"]:
                        high_value_findings.append(
                            {
                                "category": category,
                                "finding": insight.get("finding", ""),
                                "insight": insight.get("insight", ""),
                            }
                        )

        # Generate key insights
        if evidence["technical_patterns"]:
            key_insights.append(
                f"Strong technical foundation with {len(evidence['technical_patterns'])} indicators"
            )

        if evidence["security_issues"]:
            key_insights.append(
                f"Security considerations: {len(evidence['security_issues'])} points to address"
            )

        if evidence["collaboration_patterns"]:
            key_insights.append(
                f"Team collaboration evident in {len(evidence['collaboration_patterns'])} patterns"
            )

        return summary

    def _get_code_file_extensions(self, files: List[FileInfo]) -> Set[str]:
        """
        Dynamically detect code file extensions from the repository.
        This ensures we analyze ALL languages, not just popular ones.
        """
        # Known code extensions (including less common ones)
        known_code_extensions = {
            # Common languages
            "py",
            "js",
            "ts",
            "jsx",
            "tsx",
            "java",
            "cpp",
            "c",
            "h",
            "hpp",
            "cs",
            "rb",
            "go",
            "rs",
            "php",
            "swift",
            "kt",
            "scala",
            "r",
            "m",
            "mm",
            # Less common but important
            "lisp",
            "lsp",
            "cl",
            "clj",
            "cljs",
            "scm",
            "rkt",
            "el",
            "elisp",  # Lisp family
            "hs",
            "lhs",
            "purs",  # Haskell, PureScript
            "ml",
            "mli",
            "fs",
            "fsi",
            "fsx",  # ML family
            "erl",
            "hrl",
            "ex",
            "exs",  # Erlang, Elixir
            "nim",
            "cr",
            "jl",
            "lua",
            "pas",
            "pp",
            "d",
            "zig",  # Other languages
            "v",
            "vhdl",
            "vhd",
            "sv",  # Hardware languages
            "sql",
            "plsql",
            "pgsql",  # Database
            "sh",
            "bash",
            "zsh",
            "fish",
            "ps1",
            "psm1",  # Shell scripts
            "dockerfile",
            "makefile",
            "cmake",  # Build files
            "proto",
            "thrift",
            "avdl",  # Protocol definitions
            "sol",
            "vy",  # Blockchain
            "dart",
            "coffee",
            "elm",
            "pony",
            "raku",
            "perl",
            "pl",
            "asm",
            "s",
            "nasm",  # Assembly
            "",
            "f90",
            "f95",
            "for",  # Fortran
            "cob",
            "cbl",  # COBOL
            "ada",
            "adb",
            "ads",  # Ada
            "groovy",
            "gradle",
            "gvy",
            "gy",
            "gsh",  # Groovy
            "tcl",
            "tk",  # Tcl
            "vb",
            "vbs",
            "vba",
            "bas",  # Visual Basic
            "matlab",
            "m",
            "octave",  # Scientific computing
            "sas",
            "stata",
            "do",  # Statistical
            "hack",
            "hh",
            "hhi",  # Hack
            "puppet",
            "pp",  # Configuration
            "terraform",
            "t",
            "tfvars",  # Infrastructure
        }

        # Detect extensions from actual files
        found_extensions = set()
        for f in files:
            if f.extension and f.type == "file":
                ext_lower = f.extension.lower()

                # Check if it's a known code extension
                if ext_lower in known_code_extensions:
                    found_extensions.add(f.extension)
                # Also check for files that might be code based on patterns
                elif any(
                    pattern in f.path.lower()
                    for pattern in ["src/", "lib/", "app/", "core/"]
                ):
                    # If in a code directory, consider it code unless it's clearly not
                    if ext_lower not in {
                        "md",
                        "txt",
                        "json",
                        "xml",
                        "yml",
                        "yaml",
                        "png",
                        "jpg",
                        "gi",
                        "pdf",
                    }:
                        found_extensions.add(f.extension)

        # If no extensions found, return a basic set
        if not found_extensions:
            return {"py", "js", "java", "cpp", "c", "go", "rb", "php"}

        return found_extensions

    def _extract_work_life_balance_status(self, balance: Any) -> str:
        """Extract work-life balance status from either old or new format."""
        if isinstance(balance, dict):
            return str(balance.get("burnout_risk", "unknown"))
        else:
            return "unknown"

    def _integrate_temporal_analysis(self, repo_data: RepositoryData) -> Dict[str, Any]:
        """
        Integrate temporal analysis into evidence extraction.

        Args:
            repo_data: Repository data to analyze

        Returns:
            Temporal analysis results formatted as evidence
        """
        try:
            # Run temporal analysis
            temporal_results = self.temporal_analyzer.analyze_skill_evolution(repo_data)

            # Extract key temporal evidence
            growth_summary = temporal_results.get("growth_summary", {})
            activity_trends = temporal_results.get("activity_trends", {})
            consistency_data = activity_trends.get("consistency", {})

            # Get recent focus
            recent_focus_data = temporal_results.get("recent_focus", {})
            recent_focus = recent_focus_data.get("primary_area", "unknown")

            evidence = {
                "development_trajectory": growth_summary.get("trajectory", "unknown"),
                "growth_indicators": growth_summary.get("growth_indicators", []),
                "challenges": growth_summary.get("challenges", []),
                "recent_focus": recent_focus,
                "activity_trend": activity_trends.get(
                    "momentum_interpretation", "unknown"
                ),
                "consistency_interpretation": consistency_data.get(
                    "interpretation", "unknown"
                ),
                "temporal_insights": [],
            }

            # Add specific temporal insights as evidence points
            insights: List[Dict[str, Any]] = []

            # Growth summary insights
            if growth_summary.get("growth_indicators"):
                for indicator in growth_summary["growth_indicators"][:3]:
                    insights.append(
                        {
                            "type": "skill_growth",
                            "finding": indicator,
                            "insight": "Demonstrates continuous learning and improvement",
                        }
                    )

            # Activity trend insights
            momentum_interp = activity_trends.get("momentum_interpretation", "")
            if momentum_interp and momentum_interp != "unknown":
                insights.append(
                    {
                        "type": "activity_trend",
                        "finding": momentum_interp,
                        "frequency": f"{activity_trends.get('overall_frequency', 0):.1f} commits/week",
                        "insight": "Current development activity level",
                    }
                )

            # Consistency insights
            consistency_interp = consistency_data.get("interpretation", "")
            if consistency_interp and consistency_interp != "unknown":
                insights.append(
                    {
                        "type": "consistency",
                        "finding": consistency_interp,
                        "active_weeks": consistency_data.get("active_weeks", 0),
                        "insight": "Development rhythm pattern",
                    }
                )

            # Recent focus insights
            recent = temporal_results.get("recent_focus", {})
            if recent.get("focus_areas"):
                insights.append(
                    {
                        "type": "recent_focus",
                        "finding": f"Recent focus on {recent['primary_area']}",
                        "areas": recent.get("focus_areas", [])[:3],
                        "insight": "Current technical priorities and interests",
                    }
                )

            evidence["temporal_insights"] = insights

            return evidence

        except Exception as e:
            logger.error(f"Error in temporal analysis integration: {e}")
            return {
                "error": "Failed to complete temporal analysis",
                "temporal_insights": [],
            }

    def _deduplicate_contributors(self, contributors: Dict[str, int]) -> Dict[str, int]:
        """
        Deduplicate contributor emails that likely belong to the same person.

        Args:
            contributors: Dictionary of email -> commit count

        Returns:
            Dictionary with deduplicated contributors
        """
        if len(contributors) <= 1:
            return contributors

        # Group emails that likely belong to the same person
        email_groups: List[List[str]] = []
        processed: Set[str] = set()

        for email in contributors.keys():
            if email in processed:
                continue

            # Start a new group with this email
            current_group = [email]
            processed.add(email)

            # Look for similar emails
            for other_email in contributors.keys():
                if other_email in processed:
                    continue

                if self._are_same_person(email, other_email):
                    current_group.append(other_email)
                    processed.add(other_email)

            email_groups.append(current_group)

        # Merge commit counts for each group
        deduplicated: Dict[str, int] = {}
        for group in email_groups:
            # Use the email with most commits as the primary
            primary_email = max(group, key=lambda e: contributors[e])
            total_commits = sum(contributors[e] for e in group)
            deduplicated[primary_email] = total_commits

        return deduplicated

    def _are_same_person(self, email1: str, email2: str) -> bool:
        """
        Determine if two email addresses likely belong to the same person.

        Args:
            email1: First email address
            email2: Second email address

        Returns:
            True if emails likely belong to same person
        """
        # Extract usernames (part before @)
        username1 = email1.split("@")[0]
        username2 = email2.split("@")[0]

        # Check for GitHub noreply pattern
        if "noreply.github.com" in email1 or "noreply.github.com" in email2:
            # Extract the actual username from GitHub noreply email
            github_pattern = r"(\d+\+)?([^@]+)@.*noreply\.github\.com"

            import re

            match1 = re.search(github_pattern, email1)
            match2 = re.search(github_pattern, email2)

            if match1 and match2:
                # Compare the username parts
                github_user1 = match1.group(2)
                github_user2 = match2.group(2)
                return github_user1 == github_user2
            elif match1:
                # Compare GitHub username with regular email username
                github_user = match1.group(2)
                # Clean both usernames for comparison
                clean_github = (
                    github_user.replace(".", "")
                    .replace("-", "")
                    .replace("_", "")
                    .lower()
                )
                clean_regular = (
                    username2.replace(".", "").replace("-", "").replace("_", "").lower()
                )

                # Check if one contains the other or they have common alpha parts
                if clean_github in clean_regular or clean_regular in clean_github:
                    return True

                # Check alpha parts (remove numbers)
                alpha_github = "".join(c for c in clean_github if c.isalpha())
                alpha_regular = "".join(c for c in clean_regular if c.isalpha())

                return alpha_github == alpha_regular and len(alpha_github) >= 3

            elif match2:
                # Compare regular email username with GitHub username
                github_user = match2.group(2)
                # Clean both usernames for comparison
                clean_github = (
                    github_user.replace(".", "")
                    .replace("-", "")
                    .replace("_", "")
                    .lower()
                )
                clean_regular = (
                    username1.replace(".", "").replace("-", "").replace("_", "").lower()
                )

                # Check if one contains the other or they have common alpha parts
                if clean_github in clean_regular or clean_regular in clean_github:
                    return True

                # Check alpha parts (remove numbers)
                alpha_github = "".join(c for c in clean_github if c.isalpha())
                alpha_regular = "".join(c for c in clean_regular if c.isalpha())

                return alpha_github == alpha_regular and len(alpha_github) >= 3

        # Check for similar usernames (common variations)
        # Remove common suffixes/prefixes
        clean_user1 = (
            username1.replace(".", "").replace("-", "").replace("_", "").lower()
        )
        clean_user2 = (
            username2.replace(".", "").replace("-", "").replace("_", "").lower()
        )

        # Check if one is contained in the other or they're very similar
        if clean_user1 in clean_user2 or clean_user2 in clean_user1:
            return True

        # Check for common patterns like adding numbers
        if len(clean_user1) >= 3 and len(clean_user2) >= 3:
            # Remove trailing numbers
            alpha1 = "".join(c for c in clean_user1 if c.isalpha())
            alpha2 = "".join(c for c in clean_user2 if c.isalpha())

            if alpha1 == alpha2 and len(alpha1) >= 3:
                return True

        return False

    def _analyze_code_complexity(
        self, repo_data: RepositoryData
    ) -> List[Dict[str, Any]]:
        """
        Analyze code complexity patterns and evidence.

        Args:
            repo_data: Repository data to analyze

        Returns:
            List of complexity evidence findings
        """
        evidence: List[Dict[str, Any]] = []

        # Analyze refactoring patterns
        refactoring_commits = []
        complex_commits = []

        for commit in repo_data.recent_commits[:100]:  # Last 100 commits
            if re.search(self.complexity_patterns["refactoring"], commit.message):
                refactoring_commits.append(commit)
            if re.search(
                self.complexity_patterns["complex_structures"], commit.message
            ):
                complex_commits.append(commit)

        # Analyze domain patterns
        domain_matches = self._analyze_domain_patterns(repo_data)

        # Build factual observations about repository structure
        observations = []

        # Language diversity - BE SPECIFIC about languages used
        if repo_data.languages:
            # Sort languages by bytes of code (descending)
            sorted_langs = sorted(
                repo_data.languages.items(), key=lambda x: x[1], reverse=True
            )
            total_bytes = sum(repo_data.languages.values())
            lang_count = len(repo_data.languages)

            if lang_count > 5:
                # Show top 5 languages with percentages, then list remaining
                top_5 = []
                for lang, bytes_count in sorted_langs[:5]:
                    percentage = (
                        (bytes_count / total_bytes * 100) if total_bytes > 0 else 0
                    )
                    top_5.append(f"{lang} ({percentage:.1f}%)")

                # Get names of remaining languages (if any)
                remaining_langs = [lang for lang, _ in sorted_langs[5:]]

                if remaining_langs:
                    observations.append(
                        f"Multi-language expertise: {', '.join(top_5)}, "
                        f"also includes {', '.join(remaining_langs)}"
                    )
                else:
                    observations.append(f"Multi-language expertise: {', '.join(top_5)}")
            elif lang_count > 2:
                # Show all languages with percentages for smaller counts
                lang_details = []
                for lang, bytes_count in sorted_langs:
                    percentage = (
                        (bytes_count / total_bytes * 100) if total_bytes > 0 else 0
                    )
                    lang_details.append(f"{lang} ({percentage:.1f}%)")

                observations.append(
                    f"Multi-language project: {', '.join(lang_details)}"
                )

        # Codebase size
        if repo_data.metrics.lines_of_code:
            loc = repo_data.metrics.lines_of_code
            if loc > 100000:
                observations.append(f"Very large codebase ({loc:,} lines of code)")
            elif loc > 50000:
                observations.append(f"Large codebase ({loc:,} lines of code)")
            elif loc > 10000:
                observations.append(f"Substantial codebase ({loc:,} lines of code)")
            else:
                observations.append(f"Compact codebase ({loc:,} lines of code)")

        # File structure organization
        if repo_data.file_structure:
            max_depth = max(f.path.count("/") for f in repo_data.file_structure)
            if max_depth <= 2:
                observations.append("Simple folder structure (flat organization)")
            elif max_depth <= 3:
                observations.append(
                    "Well-organized folder structure (up to 3 levels deep)"
                )
            elif max_depth <= 5:
                observations.append(
                    f"Complex folder structure ({max_depth} levels of nesting)"
                )
            else:
                observations.append(
                    f"Deep folder hierarchy ({max_depth} levels - may indicate complex architecture)"
                )

        # Contributor complexity
        if repo_data.metrics.unique_contributors:
            contributors = repo_data.metrics.unique_contributors
            if contributors > 50:
                observations.append(
                    f"Large team collaboration ({contributors} contributors)"
                )
            elif contributors > 10:
                observations.append(
                    f"Multi-contributor project ({contributors} contributors)"
                )

        # Refactoring activity
        if refactoring_commits:
            observations.append(
                f"Found {len(refactoring_commits)} refactoring commits in recent history"
            )

        # Complex feature commits
        if complex_commits:
            observations.append(
                f"Found {len(complex_commits)} commits implementing complex features"
            )

        # Build the finding text with better formatting
        if observations:
            if len(observations) == 1:
                finding_text = observations[0]
            else:
                finding_text = " • ".join(observations)
        else:
            finding_text = "Standard project structure observed"

        # Add evidence
        evidence.append(
            {
                "type": "code_complexity",
                "finding": finding_text,
                "details": {
                    "file_structure_depth": f"{self._estimate_nesting_depth(repo_data)} levels",
                    "estimated_function_length": f"~{self._estimate_function_length(repo_data)} lines",
                    "refactoring_activity": f"{len(refactoring_commits)} refactoring commits",
                    "complex_features": f"{len(complex_commits)} complex feature commits",
                },
                "evidence": observations,
                "insight": self._build_complexity_insight(observations),
                "domain_patterns": domain_matches,
            }
        )

        # Add refactoring evidence if significant
        if refactoring_commits:
            evidence.append(
                {
                    "type": "refactoring_practices",
                    "finding": f"Regular refactoring ({len(refactoring_commits)} commits)",
                    "examples": [c.message[:80] for c in refactoring_commits[:3]],
                    "recent_refactor": refactoring_commits[0].date.strftime("%Y-%m-%d"),
                    "insight": "Actively maintains code quality through refactoring",
                }
            )

        return evidence

    def _build_complexity_insight(self, observations: List[str]) -> str:
        """Build insight from factual observations."""
        if not observations:
            return "Standard repository structure"

        # Look for key patterns in observations
        has_multi_language = any("language" in obs.lower() for obs in observations)
        has_large_codebase = any("large" in obs.lower() for obs in observations)
        has_refactoring = any("refactor" in obs.lower() for obs in observations)

        insights = []
        if has_multi_language:
            insights.append("Works with diverse technology stacks")
        if has_large_codebase:
            insights.append("Manages substantial codebases")
        if has_refactoring:
            insights.append("Actively maintains code quality")

        return (
            "; ".join(insights)
            if insights
            else "Repository shows standard development patterns"
        )

    def _estimate_nesting_depth(self, repo_data: RepositoryData) -> int:
        """Estimate average nesting depth from file structure."""
        if not repo_data.file_structure:
            return 2

        depths = [f.path.count("/") for f in repo_data.file_structure]
        return min(int(sum(depths) / len(depths)) + 1, 6)

    def _estimate_function_length(self, repo_data: RepositoryData) -> int:
        """Estimate average function length."""
        if repo_data.metrics.lines_of_code and repo_data.file_structure:
            code_files = len(
                [f for f in repo_data.file_structure if not f.is_documentation]
            )
            if code_files > 0:
                avg_file_size = repo_data.metrics.lines_of_code / code_files
                # Rough estimate: assume 5-10 functions per file
                return int(avg_file_size / 7)
        return 25  # Default estimate

    def _analyze_domain_patterns(self, repo_data: RepositoryData) -> Dict[str, Any]:
        """
        Analyze domain patterns based on repository content.

        Args:
            repo_data: Repository data to analyze

        Returns:
            Dictionary with domain pattern analysis
        """
        domain_matches = {}

        # Analyze commit messages
        all_text = " ".join(
            [commit.message for commit in repo_data.recent_commits[:100]]
        )

        # Add file names and README content
        if repo_data.file_structure:
            all_text += " " + " ".join([f.name for f in repo_data.file_structure])

        if repo_data.readme_content:
            all_text += " " + repo_data.readme_content

        # Count matches for each domain
        for domain, pattern in self.domain_patterns.items():
            matches = len(re.findall(pattern, all_text))
            if matches > 0:
                domain_matches[domain] = matches

        # Determine primary domains (top 2-3 with significant matches)
        sorted_domains = sorted(
            domain_matches.items(), key=lambda x: x[1], reverse=True
        )
        primary_domains = [
            domain for domain, match_count in sorted_domains[:3] if match_count >= 2
        ]

        # Map domains to architecture types and role fits
        architecture_types = self._map_domains_to_architecture(primary_domains)
        role_fits = self._map_domains_to_roles(primary_domains)
        less_suitable = self._map_domains_to_less_suitable(primary_domains)

        return {
            "primary_domains": primary_domains,
            "architecture_experience": architecture_types,
            "role_suitability": role_fits,
            "less_suitable_for": less_suitable,
            # Removed domain_scores - using evidence-based approach
        }

    def _map_domains_to_architecture(self, domains: List[str]) -> List[str]:
        """Map detected domains to architecture types."""
        architecture_map = {
            "distributed_systems": "Microservices, Event-driven architectures",
            "real_time": "Real-time systems, WebSocket architectures",
            "data_processing": "Data pipelines, ETL systems",
            "financial": "Transaction processing, Payment systems",
            "security": "Authentication systems, Security frameworks",
            "devops": "CI/CD pipelines, Infrastructure as Code",
            "machine_learning": "ML pipelines, Model serving",
            "web_frameworks": "Web applications, API development",
        }

        return [
            architecture_map.get(domain, domain.replace("_", " ").title())
            for domain in domains
        ]

    def _map_domains_to_roles(self, domains: List[str]) -> List[str]:
        """Map detected domains to suitable roles."""
        role_map = {
            "distributed_systems": "Platform Engineering, Backend Architecture, DevOps",
            "real_time": "Real-time Systems Engineer, WebSocket Developer",
            "data_processing": "Data Engineer, ETL Developer, Analytics Engineer",
            "financial": "Fintech Developer, Payment Systems Engineer",
            "security": "Security Engineer, Authentication Specialist",
            "devops": "DevOps Engineer, Site Reliability Engineer",
            "machine_learning": "ML Engineer, Data Scientist, AI Developer",
            "web_frameworks": "Full-stack Developer, Frontend Engineer, Backend Developer",
        }

        roles = []
        for domain in domains:
            if domain in role_map:
                roles.extend(role_map[domain].split(", "))

        return list(set(roles))  # Remove duplicates

    def _map_domains_to_less_suitable(self, domains: List[str]) -> List[str]:
        """Map detected domains to less suitable roles/projects."""
        if not domains:
            return []

        # If they have complex domains, they're less suitable for simple work
        complex_domains = {
            "distributed_systems",
            "real_time",
            "data_processing",
            "financial",
            "machine_learning",
        }

        if any(domain in complex_domains for domain in domains):
            return [
                "Simple CRUD applications",
                "Static websites",
                "Basic scripting tasks",
            ]

        # If they only have web frameworks, less suitable for complex systems
        if "web_frameworks" in domains and len(domains) == 1:
            return ["Distributed systems", "Real-time processing", "Data engineering"]

        return []

    def _extract_domain_patterns(
        self, repo_data: RepositoryData
    ) -> Dict[str, List[str]]:
        """Extract domain patterns from repository data."""
        domain_matches = {}

        # Analyze README content
        text_content = ""
        if repo_data.readme_content:
            text_content += repo_data.readme_content + " "

        # Analyze description
        if repo_data.description:
            text_content += repo_data.description + " "

        # Analyze file names and paths
        if repo_data.file_structure:
            for file_info in repo_data.file_structure:
                text_content += file_info.path + " " + file_info.name + " "

        # Analyze commit messages
        if repo_data.recent_commits:
            for commit in repo_data.recent_commits[:20]:  # Last 20 commits
                text_content += commit.message + " "

        # Search for domain patterns
        for domain, pattern in self.domain_patterns.items():
            matches = re.findall(pattern, text_content)
            if matches:
                domain_matches[domain] = matches[:5]  # Limit to first 5 matches

        return domain_matches
