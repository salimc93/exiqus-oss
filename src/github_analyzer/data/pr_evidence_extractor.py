# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Evidence extraction from PR data for analysis.

This module extracts meaningful evidence patterns from PR data,
focusing on factual observations rather than behavioral inferences.
"""

import re
from collections import defaultdict
from typing import Dict, List

from ..utils.logging import get_logger
from .pr_models import PRData, PREvidence, QualitySignals

logger = get_logger(__name__)


class PREvidenceExtractor:
    """Extract evidence and quality signals from PR data."""

    def __init__(self) -> None:
        """Initialize the evidence extractor."""
        self.feature_patterns = [
            r"feat|feature|add|implement|create|introduce|build",
            r"new\s+\w+|added\s+\w+",
        ]
        self.fix_patterns = [
            r"fix|bug|issue|error|crash|broken|repair",
            r"resolve|patch|hotfix|bugfix",
        ]
        self.refactor_patterns = [
            r"refactor|restructure|reorganize|cleanup|clean\s+up",
            r"improve|optimize|enhance\s+code",
        ]

    def extract_evidence(self, prs: List[PRData], username: str) -> PREvidence:
        """
        Extract evidence patterns from PR data.

        Args:
            prs: List of PR data objects
            username: Username being analyzed

        Returns:
            PREvidence object with categorized evidence
        """
        evidence = PREvidence()

        if not prs:
            return evidence

        # Extract different types of evidence
        self._extract_technical_substance(prs, evidence)
        self._extract_collaboration_patterns(prs, username, evidence)
        self._extract_review_responsiveness(prs, evidence)
        self._extract_integration_patterns(prs, evidence)
        self._extract_cross_repo_contributions(prs, evidence)
        self._extract_pr_description_quality(prs, evidence)
        self._extract_process_adherence(prs, evidence)

        # CRITICAL: Add time-based consistency as PRIMARY evidence
        self._add_time_consistency_evidence(prs, evidence)

        # Sort evidence by importance (data-driven sorting)
        self._sort_evidence_by_importance(evidence)

        return evidence

    def extract_quality_signals(
        self, prs: List[PRData], username: str
    ) -> QualitySignals:
        """
        Extract quality signals from PR data.

        Args:
            prs: List of PR data objects
            username: Username being analyzed

        Returns:
            QualitySignals object with metrics
        """
        signals = QualitySignals()

        if not prs:
            return signals

        # Time-based metrics
        self._extract_time_metrics(prs, signals)

        # Collaboration metrics
        self._extract_collaboration_metrics(prs, username, signals)

        # Contribution patterns
        self._extract_contribution_patterns(prs, signals)

        # Repository diversity
        self._extract_repository_diversity(prs, signals)

        # Size metrics
        self._extract_size_metrics(prs, signals)

        return signals

    def _extract_technical_substance(
        self, prs: List[PRData], evidence: PREvidence
    ) -> None:
        """Extract technical substance evidence - prioritize by impact."""
        merged_prs = [pr for pr in prs if pr.merged]

        # CRITICAL: Find massive PRs like the debugger (977 commits, 25k+ additions)
        massive_prs = []
        for pr in prs:
            if pr.commits_total > 100 or pr.additions > 10000:
                massive_prs.append(pr)

        # Sort by impact - prioritize APPROVED, then merged, then size
        massive_prs.sort(
            key=lambda p: (
                p.review_decision == "APPROVED",  # Approved first
                p.merged,  # Then merged
                p.commits_total,  # Then by commits
                p.additions,  # Then by additions
            ),
            reverse=True,
        )

        for pr in massive_prs[:3]:  # Top 3 massive PRs
            collab_note = " (assigned to user)" if pr.assigned_to_user else ""

            # Add observable review and scope evidence
            review_note = (
                f", reviewDecision: {pr.review_decision}" if pr.review_decision else ""
            )
            scope_note = (
                f", {pr.changed_files} files changed" if pr.changed_files > 0 else ""
            )
            labels_note = f" [{', '.join(pr.labels[:3])}]" if pr.labels else ""

            # Format based on merge status - unmerged large PRs need validation
            if pr.merged:
                evidence.technical_substance.insert(
                    0,  # INSERT AT BEGINNING - CRITICAL
                    f"MAJOR SUCCESS: PR #{pr.number} '{pr.title[:50]}'{labels_note} - {pr.commits_total} commits, "
                    f"{pr.additions:,}+ additions{scope_note} (MERGED to production{review_note}){collab_note}",
                )
            else:
                # Unmerged large PRs still show capability but need context
                evidence.technical_substance.insert(
                    2,  # Still important but not at top
                    f"Large Implementation: PR #{pr.number} '{pr.title[:50]}'{labels_note} - "
                    f"{pr.additions:,}+ additions{scope_note} (unmerged{review_note}){collab_note}",
                )

        # Large merged PRs (500+ lines)
        large_merged = [pr for pr in merged_prs if pr.total_changes >= 500]
        if large_merged:
            evidence.technical_substance.insert(
                0,
                f"Successfully merged {len(large_merged)} large PRs (500+ lines) - "
                f"proven ability to ship substantial features",
            )

        # Production Integration Success - KEY hiring signal
        if len(merged_prs) > 0:
            merge_rate = len(merged_prs) / len(prs) if len(prs) > 0 else 0

            # This is a CRITICAL hiring signal - ability to ship to production
            evidence.technical_substance.insert(
                0,
                f"Production Integration Success: {len(merged_prs)}/{len(prs)} PRs "
                f"successfully merged into production codebases ({merge_rate:.0%} success rate)",
            )

            # Add specific evidence about code meeting standards
            if merge_rate > 0.8:
                evidence.technical_substance.insert(
                    1,
                    "Code consistently met production standards - proven ability to ship quality code",
                )

    def _extract_collaboration_patterns(
        self, prs: List[PRData], username: str, evidence: PREvidence
    ) -> None:
        """Extract collaboration pattern evidence - CRITICAL hiring signals."""
        # Deep collaboration (3+ review cycles) - Zed values this highly
        deep_collab = [pr for pr in prs if pr.reviews_count >= 3]
        if deep_collab:
            merged_deep = sum(1 for pr in deep_collab if pr.merged)
            evidence.collaboration_patterns.insert(
                0,  # FIRST position - key signal
                f"Deep collaboration: {len(deep_collab)} PRs with 3+ review cycles "
                f"({merged_deep} merged after iteration)",
            )

        # Pair programming (co-authored PRs) - Another Zed key signal
        co_authored = [pr for pr in prs if pr.co_authors]
        if co_authored:
            unique_co_authors = set()
            for pr in co_authored:
                unique_co_authors.update(pr.co_authors)
            evidence.collaboration_patterns.insert(
                0,  # FIRST position
                f"Pair programming: {len(co_authored)} PRs co-authored with "
                f"{len(unique_co_authors)} different developers",
            )

        # Assigned PRs - especially large ones like debugger PR
        assigned = [pr for pr in prs if pr.assigned_to_user and pr.author != username]
        if assigned:
            # Find the most impactful assigned PRs - prioritize approved/merged
            assigned.sort(
                key=lambda p: (
                    p.review_decision == "APPROVED",
                    p.merged,
                    p.commits_total,
                    p.additions,
                ),
                reverse=True,
            )

            for pr in assigned[:2]:  # Top 2 assigned PRs
                if pr.additions > 1000 or pr.commits_total > 50:
                    evidence.collaboration_patterns.insert(
                        1,  # Near top
                        f"Trusted with major PR: '{pr.title[:40]}' ({pr.commits_total} commits, "
                        f"{pr.additions:,}+ additions) - assigned by {pr.author}",
                    )

            evidence.collaboration_patterns.insert(
                2,
                f"Assigned to {len(assigned)} PRs by other developers (high trust indicator)",
            )

    def _extract_review_responsiveness(
        self, prs: List[PRData], evidence: PREvidence
    ) -> None:
        """Extract review responsiveness evidence - shows persistence and iteration ability."""
        # Persistent Review Engagement - KEY hiring signal
        high_review_merged = []
        for pr in prs:
            if pr.merged and pr.reviews_count >= 5:
                high_review_merged.append(pr)

        if high_review_merged:
            # Sort by review count to show most persistent examples
            high_review_merged.sort(key=lambda p: p.reviews_count, reverse=True)

            # Overall persistence evidence
            evidence.review_responsiveness.insert(
                0,
                f"Persistent Review Engagement: {len(high_review_merged)} PRs merged after "
                f"extensive review cycles - demonstrates feedback incorporation",
            )

            # Specific examples of persistence
            for pr in high_review_merged[:3]:  # Top 3 examples
                evidence.review_responsiveness.insert(
                    1,
                    f"Persisted through {pr.reviews_count} reviews on '{pr.title[:40]}' - merged successfully",
                )

        # PRs merged after review (general)
        reviewed_merged = [pr for pr in prs if pr.merged and pr.reviews_count > 0]
        if reviewed_merged:
            evidence.review_responsiveness.append(
                f"{len(reviewed_merged)} total PRs merged after review cycles"
            )

        # Quick merges show different skill
        quick_merges = []
        for pr in prs:
            if pr.merged and pr.merge_time_days is not None:
                if pr.merge_time_days <= 2:
                    quick_merges.append(pr)

        if quick_merges:
            evidence.review_responsiveness.append(
                f"{len(quick_merges)} PRs merged within 2 days (quick iteration)"
            )

    def _extract_integration_patterns(
        self, prs: List[PRData], evidence: PREvidence
    ) -> None:
        """Extract integration pattern evidence."""
        # Branch naming patterns
        feature_branches = [pr for pr in prs if self._is_feature_branch(pr.head_ref)]
        fix_branches = [pr for pr in prs if self._is_fix_branch(pr.head_ref)]

        if feature_branches:
            evidence.integration_patterns.append(
                f"{len(feature_branches)} feature implementations via organized branches"
            )

        if fix_branches:
            evidence.integration_patterns.append(
                f"{len(fix_branches)} bug fixes with dedicated fix branches"
            )

        # Target branch patterns
        main_merges = [
            pr
            for pr in prs
            if pr.base_ref in ["main", "master", "develop"] and pr.merged
        ]
        if main_merges:
            evidence.integration_patterns.append(
                f"{len(main_merges)} direct merges to main branches"
            )

    def _extract_cross_repo_contributions(
        self, prs: List[PRData], evidence: PREvidence
    ) -> None:
        """Extract cross-repository contribution evidence - shows adaptability."""
        repos = defaultdict(list)
        for pr in prs:
            repos[pr.repository].append(pr)

        if len(repos) >= 3:
            # Cross-Repository Adaptability is a KEY hiring signal
            evidence.cross_repo_contributions.insert(
                0,
                f"Cross-Repository Adaptability: Contributed across {len(repos)} different "
                f"repositories - demonstrates ability to understand different codebases",
            )

            # List all repos if not too many
            if len(repos) <= 10:
                repo_names = ", ".join(sorted(repos.keys())[:7])
                if len(repos) > 7:
                    repo_names += f", and {len(repos) - 7} more"
                evidence.cross_repo_contributions.insert(
                    1, f"Repositories: {repo_names}"
                )

            # Find most active repos with merge success
            sorted_repos = sorted(repos.items(), key=lambda x: len(x[1]), reverse=True)[
                :3
            ]
            for i, (repo_name, repo_prs) in enumerate(sorted_repos):
                merged = sum(1 for pr in repo_prs if pr.merged)
                merge_rate = merged / len(repo_prs) if len(repo_prs) > 0 else 0
                if merge_rate > 0.7:  # Good success rate
                    evidence.cross_repo_contributions.append(
                        f"{repo_name}: {len(repo_prs)} PRs ({merged} merged - {merge_rate:.0%} success)"
                    )

    def _extract_pr_description_quality(
        self, prs: List[PRData], evidence: PREvidence
    ) -> None:
        """Extract PR description quality evidence."""
        well_documented = []
        for pr in prs:
            if pr.body and len(pr.body) > 200:
                well_documented.append(pr)

        if well_documented:
            evidence.pr_description_quality.append(
                f"{len(well_documented)} PRs with detailed descriptions (200+ characters)"
            )

        # PRs with structured descriptions
        structured = []
        for pr in prs:
            if pr.body and any(
                marker in pr.body.lower()
                for marker in ["## ", "### ", "- [ ]", "- [x]", "fixes #", "closes #"]
            ):
                structured.append(pr)

        if structured:
            evidence.pr_description_quality.append(
                f"{len(structured)} PRs with structured descriptions (sections/checklists/issue refs)"
            )

    def _extract_process_adherence(
        self, prs: List[PRData], evidence: PREvidence
    ) -> None:
        """Extract process adherence evidence."""
        # Conventional commit patterns
        conventional = []
        for pr in prs:
            if self._has_conventional_prefix(pr.title):
                conventional.append(pr)

        if conventional:
            evidence.process_adherence.append(
                f"{len(conventional)} PRs following conventional commit format"
            )

        # Issue references
        issue_linked = []
        for pr in prs:
            if pr.body and re.search(r"#\d+|[A-Z]+-\d+", pr.body):
                issue_linked.append(pr)

        if issue_linked:
            evidence.process_adherence.append(
                f"{len(issue_linked)} PRs linked to issues/tickets"
            )

    def _extract_time_metrics(self, prs: List[PRData], signals: QualitySignals) -> None:
        """Extract time-based metrics - CRITICAL for hiring decisions."""
        if not prs:
            return

        # Find date range
        dates = [pr.created_at for pr in prs if pr.created_at]
        if dates:
            signals.first_pr_date = min(dates)
            signals.last_pr_date = max(dates)

            # Calculate timespan
            delta = signals.last_pr_date - signals.first_pr_date
            years = delta.days // 365
            months = (delta.days % 365) // 30
            days = (delta.days % 365) % 30

            # More precise timespan reporting
            if years > 0:
                if months > 0:
                    signals.contribution_timespan = f"{years} years, {months} months"
                else:
                    signals.contribution_timespan = f"{years} years"
            elif months > 0:
                signals.contribution_timespan = f"{months} months, {days} days"
            else:
                signals.contribution_timespan = f"{delta.days} days"

            # Calculate monthly rate - KEY METRIC
            if delta.days > 30:
                signals.monthly_pr_rate = len(prs) / (delta.days / 30)

            # Sustained engagement is a PRIMARY hiring signal
            # (handled in evidence extraction)

    def _extract_collaboration_metrics(
        self, prs: List[PRData], username: str, signals: QualitySignals
    ) -> None:
        """Extract collaboration metrics."""
        # Pair programming (co-authored PRs)
        signals.pair_programming_count = sum(1 for pr in prs if pr.co_authors)

        # Deep collaboration (3+ review cycles)
        signals.deep_collaboration_count = sum(1 for pr in prs if pr.reviews_count >= 3)

        # Self-managed vs assigned
        signals.self_managed_prs = sum(
            1 for pr in prs if pr.author == username and not pr.assigned_to_user
        )
        signals.assigned_prs = sum(1 for pr in prs if pr.assigned_to_user)

    def _extract_contribution_patterns(
        self, prs: List[PRData], signals: QualitySignals
    ) -> None:
        """Extract contribution pattern metrics."""
        signals.total_prs = len(prs)
        signals.merged_prs = sum(1 for pr in prs if pr.merged)

        # Classify PRs
        for pr in prs:
            if self._is_feature_pr(pr):
                signals.feature_prs += 1
                # Check if taken to production (merged + substantial)
                if pr.merged and pr.additions >= 200:
                    signals.feature_ownership_count += 1
            elif self._is_fix_pr(pr):
                signals.fix_prs += 1

    def _extract_repository_diversity(
        self, prs: List[PRData], signals: QualitySignals
    ) -> None:
        """Extract repository diversity metrics."""
        repos = set(pr.repository for pr in prs)
        signals.unique_repos = len(repos)
        signals.repo_list = sorted(list(repos))

    def _extract_size_metrics(self, prs: List[PRData], signals: QualitySignals) -> None:
        """Extract PR size metrics."""
        signals.large_prs = sum(1 for pr in prs if pr.total_changes >= 500)
        signals.focused_prs = sum(1 for pr in prs if pr.total_changes <= 100)

    def _add_time_consistency_evidence(
        self, prs: List[PRData], evidence: PREvidence
    ) -> None:
        """Add time-based consistency evidence - PRIMARY hiring signal."""
        if not prs:
            return

        dates = [pr.created_at for pr in prs if pr.created_at]
        if not dates or len(dates) < 2:
            return

        dates.sort()
        first_pr = dates[0]
        last_pr = dates[-1]
        delta = last_pr - first_pr

        # Only add time evidence if there's sustained engagement
        if delta.days > 30:  # More than a month
            years = delta.days // 365
            months = (delta.days % 365) // 30

            # Calculate monthly rate
            monthly_rate = len(prs) / max(1, (delta.days / 30))

            # Format timespan
            if years > 0:
                timespan = f"{years} years, {months} months"
            else:
                timespan = f"{months} months"

            # This goes FIRST in collaboration patterns - it's what Zed values most
            evidence.collaboration_patterns.insert(
                0,
                f"Sustained contributions over {timespan} "
                f"({first_pr.date()} to {last_pr.date()})",
            )

            if monthly_rate > 2:  # Consistent delivery
                evidence.collaboration_patterns.insert(
                    1,
                    f"Consistent delivery pace: {monthly_rate:.1f} PRs per month average",
                )

            # Add to technical substance if very long-term
            if years >= 2:
                evidence.technical_substance.insert(
                    0, f"Long-term commitment: {years}+ years of contributions"
                )

    def _sort_evidence_by_importance(self, evidence: PREvidence) -> None:
        """
        Sort evidence items by importance based on data metrics.

        Note: We use .insert(0, ...) for priority items, so this just
        ensures remaining items are reasonably ordered.
        """
        # For categories that might have many items, sort by numbers mentioned
        for category in [
            evidence.cross_repo_contributions,
            evidence.pr_description_quality,
        ]:
            # Simple sort by first number found (usually the count)
            category.sort(key=lambda x: self._extract_first_number(x), reverse=True)

    def _extract_first_number(self, text: str) -> int:
        """Extract first number from text for sorting."""
        numbers = re.findall(r"\d+", text)
        return int(numbers[0]) if numbers else 0

    def _is_feature_branch(self, branch_name: str) -> bool:
        """Check if branch name indicates a feature."""
        if not branch_name:
            return False
        branch_lower = branch_name.lower()
        return any(
            pattern in branch_lower for pattern in ["feature/", "feat/", "add/", "new/"]
        )

    def _is_fix_branch(self, branch_name: str) -> bool:
        """Check if branch name indicates a fix."""
        if not branch_name:
            return False
        branch_lower = branch_name.lower()
        return any(
            pattern in branch_lower
            for pattern in ["fix/", "bug/", "hotfix/", "bugfix/", "patch/"]
        )

    def _is_feature_pr(self, pr: PRData) -> bool:
        """Check if PR is a feature implementation."""
        title_lower = pr.title.lower()
        for pattern in self.feature_patterns:
            if re.search(pattern, title_lower):
                return True
        return self._is_feature_branch(pr.head_ref)

    def _is_fix_pr(self, pr: PRData) -> bool:
        """Check if PR is a bug fix."""
        title_lower = pr.title.lower()
        for pattern in self.fix_patterns:
            if re.search(pattern, title_lower):
                return True
        return self._is_fix_branch(pr.head_ref)

    def _has_conventional_prefix(self, title: str) -> bool:
        """Check if title follows conventional commit format."""
        conventional_prefixes = [
            "feat:",
            "fix:",
            "docs:",
            "style:",
            "refactor:",
            "test:",
            "chore:",
            "perf:",
            "ci:",
            "build:",
        ]
        title_lower = title.lower()
        return any(title_lower.startswith(prefix) for prefix in conventional_prefixes)

    def transform_to_evidence_patterns(
        self, evidence: PREvidence, quality_signals: QualitySignals
    ) -> List[Dict[str, str]]:
        """
        Transform existing PR evidence into EvidencePatternModel format for Evidence tab display.

        Args:
            evidence: Extracted PR evidence
            quality_signals: Quality signals from analysis

        Returns:
            List of evidence patterns in EvidencePatternModel format
        """
        patterns = []

        # Transform technical substance evidence
        for idx, item in enumerate(evidence.technical_substance[:5]):
            patterns.append(
                {
                    "name": f"Technical Implementation Pattern {idx + 1}",
                    "pattern_type": "technical",
                    "evidence": item,
                    "context": "Based on PR analysis showing technical capabilities",
                    "insight": self._generate_technical_insight(item),
                    "category": "technical",
                }
            )

        # Transform collaboration patterns
        for idx, item in enumerate(evidence.collaboration_patterns[:5]):
            patterns.append(
                {
                    "name": f"Collaboration Pattern {idx + 1}",
                    "pattern_type": "collaboration",
                    "evidence": item,
                    "context": "Derived from PR interaction and merge patterns",
                    "insight": self._generate_collaboration_insight(item),
                    "category": "professional",
                }
            )

        # Transform review responsiveness
        for idx, item in enumerate(evidence.review_responsiveness[:3]):
            patterns.append(
                {
                    "name": f"Review Engagement Pattern {idx + 1}",
                    "pattern_type": "behavioral",
                    "evidence": item,
                    "context": "Analysis of review cycles and feedback incorporation",
                    "insight": self._generate_review_insight(item),
                    "category": "communication",
                }
            )

        # Transform cross-repo contributions
        for idx, item in enumerate(evidence.cross_repo_contributions[:3]):
            patterns.append(
                {
                    "name": f"Cross-Repository Pattern {idx + 1}",
                    "pattern_type": "technical",
                    "evidence": item,
                    "context": "Multi-repository contribution analysis",
                    "insight": self._generate_cross_repo_insight(item),
                    "category": "technical",
                }
            )

        # Add quality signal patterns
        if quality_signals.merge_rate > 0:
            patterns.append(
                {
                    "name": "Merge Success Pattern",
                    "pattern_type": "quality",
                    "evidence": f"{quality_signals.merge_rate:.0%} merge rate ({quality_signals.merged_prs}/{quality_signals.total_prs} PRs) across {quality_signals.unique_repos} repositories",
                    "context": f"Analysis of PR success rate over {quality_signals.contribution_timespan or 'analyzed period'}",
                    "insight": self._generate_merge_success_insight(
                        quality_signals.merge_rate
                    ),
                    "category": "professional",
                }
            )

        if quality_signals.contribution_timespan:
            patterns.append(
                {
                    "name": "Sustained Engagement Pattern",
                    "pattern_type": "behavioral",
                    "evidence": f"Sustained contributions over {quality_signals.contribution_timespan}",
                    "context": f"Long-term contribution analysis showing {quality_signals.total_prs} PRs",
                    "insight": "Demonstrates long-term commitment and sustained technical engagement",
                    "category": "growth",
                }
            )

        # Areas to explore as patterns
        for idx, item in enumerate(evidence.areas_to_explore[:3]):
            patterns.append(
                {
                    "name": f"Investigation Area {idx + 1}",
                    "pattern_type": "quality",
                    "evidence": item,
                    "context": "Pattern identified for further validation in interviews",
                    "insight": "Requires deeper exploration to understand full capability",
                    "category": "growth",
                }
            )

        return patterns

    def _generate_technical_insight(self, evidence: str) -> str:
        """Generate insight for technical evidence."""
        if "500+" in evidence or "large" in evidence.lower():
            return "Demonstrates capability to handle substantial technical implementations"
        elif "merged" in evidence.lower():
            return "Shows ability to deliver production-ready code"
        elif "repository" in evidence.lower() or "repo" in evidence.lower():
            return "Indicates adaptability across different technical environments"
        else:
            return "Represents solid technical contribution pattern"

    def _generate_collaboration_insight(self, evidence: str) -> str:
        """Generate insight for collaboration evidence."""
        if "merged" in evidence.lower():
            return "Shows successful collaboration leading to production integration"
        elif "review" in evidence.lower():
            return "Demonstrates effective engagement with code review processes"
        elif "day" in evidence.lower():
            return "Indicates efficient collaboration and delivery cycles"
        else:
            return "Reflects positive collaborative working patterns"

    def _generate_review_insight(self, evidence: str) -> str:
        """Generate insight for review evidence."""
        if "review" in evidence.lower():
            return "Shows engagement with feedback and iterative improvement"
        elif "feedback" in evidence.lower():
            return "Demonstrates receptiveness to code review feedback"
        else:
            return "Indicates professional approach to code review processes"

    def _generate_cross_repo_insight(self, evidence: str) -> str:
        """Generate insight for cross-repository evidence."""
        if "repository" in evidence.lower() or "repo" in evidence.lower():
            return "Shows adaptability and learning across different codebases"
        elif "contributed" in evidence.lower():
            return "Demonstrates versatility in technical contribution patterns"
        else:
            return "Indicates broad technical engagement capabilities"

    def _generate_merge_success_insight(self, merge_rate: float) -> str:
        """Generate insight based on merge success rate."""
        if merge_rate >= 0.8:
            return "High merge success rate indicates strong code quality and collaboration skills"
        elif merge_rate >= 0.5:
            return "Moderate merge success shows developing skills with room for improvement"
        elif merge_rate >= 0.3:
            return "Mixed merge success suggests need to explore development approach and validation processes"
        else:
            return "Low merge rate indicates potential challenges with code quality or feature validation"
