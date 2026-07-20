# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Portfolio Evidence Extractor.

Extracts evidence patterns from portfolio repository data following the
validation script's proven approach - ZERO SCORES, purely factual observations.
"""

from typing import Any, Dict, List

from ..utils.logging import get_logger
from .portfolio_models import RepoData

logger = get_logger(__name__)


class PortfolioEvidenceExtractor:
    """Extract evidence patterns from portfolio repos (NO SCORES - pure facts)."""

    def extract_all_evidence(
        self, repos: List[RepoData], username: str
    ) -> Dict[str, Any]:
        """
        Extract all evidence patterns from repos.

        Args:
            repos: List of repository data objects
            username: GitHub username

        Returns:
            Dictionary with all evidence patterns (ZERO SCORES)
        """
        if not repos:
            logger.warning(f"No repos provided for evidence extraction for {username}")
            return self._empty_evidence()

        logger.info(f"Extracting evidence from {len(repos)} repos for {username}")

        # Build timeline of public repos
        public_repos_timeline = self._build_repos_timeline(repos)

        # Track technology adoption timeline
        technology_adoption_timeline = self._build_technology_timeline(repos)

        # Detect timeline gaps
        timeline_gaps = self._detect_timeline_gaps(repos)

        # Build cross-technology evidence
        cross_technology_evidence = self._build_technology_summary(repos)

        # Extract portfolio evolution by time periods
        portfolio_evolution_periods = self._extract_evolution_periods(repos)

        # Extract substantial repos
        substantial_repos_structured = self._extract_substantial_repos(repos)

        # Build cross-repo patterns
        technology_evolution_evidence = self._build_technology_evolution(repos)
        quality_progression_evidence = self._build_quality_progression(repos)
        cross_repo_patterns = self._build_cross_repo_patterns(repos)

        # Build structured aggregations
        aggregated_technologies = self._aggregate_technologies(repos)
        aggregated_quality_indicators = self._aggregate_quality_indicators(
            repos, substantial_repos_structured
        )

        # Build quality indicators list
        public_work_quality_indicators = self._build_quality_indicators(repos)

        # Build substantial repo indicators (for interview questions)
        repo_substance_indicators = self._build_substance_indicators(
            substantial_repos_structured
        )

        return {
            "public_repos_timeline": public_repos_timeline[:10],  # Sample
            "technology_adoption_timeline": technology_adoption_timeline[:10],  # Sample
            "public_work_quality_indicators": public_work_quality_indicators,
            "timeline_gaps": timeline_gaps,
            "cross_technology_evidence": cross_technology_evidence,
            "portfolio_evolution_periods": portfolio_evolution_periods,
            "substantial_repos_structured": substantial_repos_structured,
            "technology_evolution_evidence": technology_evolution_evidence,
            "quality_progression_evidence": quality_progression_evidence,
            "cross_repo_patterns": cross_repo_patterns,
            "aggregated_technologies": aggregated_technologies,
            "aggregated_quality_indicators": aggregated_quality_indicators,
            "repo_substance_indicators": repo_substance_indicators[:8],  # Top 8
        }

    def _empty_evidence(self) -> Dict[str, Any]:
        """Return empty evidence structure."""
        return {
            "public_repos_timeline": [],
            "technology_adoption_timeline": [],
            "public_work_quality_indicators": [],
            "timeline_gaps": [],
            "cross_technology_evidence": [],
            "portfolio_evolution_periods": [],
            "substantial_repos_structured": [],
            "technology_evolution_evidence": [],
            "quality_progression_evidence": [],
            "cross_repo_patterns": [],
            "aggregated_technologies": {},
            "aggregated_quality_indicators": {},
            "repo_substance_indicators": [],
        }

    def _build_repos_timeline(self, repos: List[RepoData]) -> List[str]:
        """Build timeline of public repos."""
        timeline = []
        for repo in repos:
            created_year = repo.created_at.strftime("%Y")
            timeline.append(
                f"{created_year}: {repo.name} ({repo.primary_language or 'Unknown'})"
            )
        return timeline

    def _build_technology_timeline(self, repos: List[RepoData]) -> List[str]:
        """Build technology adoption timeline."""
        tech_first_seen: Dict[str, str] = {}

        for repo in repos:
            if repo.primary_language and repo.primary_language not in tech_first_seen:
                tech_first_seen[repo.primary_language] = repo.created_at.strftime(
                    "%Y-%m-%d"
                )

        timeline = []
        for tech, first_date in tech_first_seen.items():
            timeline.append(f"{tech}: First observed in public repos on {first_date}")

        return timeline

    def _detect_timeline_gaps(self, repos: List[RepoData]) -> List[str]:
        """Detect gaps in public activity."""
        repo_years = sorted(set(r.created_at.year for r in repos))
        gaps = []

        if len(repo_years) > 1:
            all_years = range(repo_years[0], repo_years[-1] + 1)
            for year in all_years:
                if year not in repo_years:
                    gaps.append(
                        f"{year}: No public repository activity (likely private work)"
                    )

        return gaps

    def _build_technology_summary(self, repos: List[RepoData]) -> List[str]:
        """Build cross-technology evidence with framework detection."""
        enhanced_languages = set()

        for repo in repos:
            # Add GitHub-reported languages
            if repo.primary_language:
                enhanced_languages.add(repo.primary_language)
            enhanced_languages.update(repo.languages.keys())

            # ENHANCED: Detect frameworks from file structure
            if repo.key_files:
                # Detect Arduino (.ino files)
                if any(f.endswith(".ino") for f in repo.key_files):
                    enhanced_languages.add("Arduino")

                # Detect web frameworks
                if "HTML" in enhanced_languages:
                    if any(
                        "vue" in f.lower() or f.endswith(".vue") for f in repo.key_files
                    ):
                        enhanced_languages.add("Vue.js")
                    elif any(
                        "react" in f.lower() or f.endswith(".jsx") or f.endswith(".tsx")
                        for f in repo.key_files
                    ):
                        enhanced_languages.add("React")
                    elif any(
                        "angular" in f.lower() or "ng-" in f.lower()
                        for f in repo.key_files
                    ):
                        enhanced_languages.add("Angular")

        return [
            f"Technologies observed in public repos: {', '.join(sorted(enhanced_languages))}"
        ]

    def _extract_evolution_periods(self, repos: List[RepoData]) -> List[Dict[str, Any]]:
        """Extract portfolio evolution by time periods (PURE FACTS ONLY)."""
        if not repos:
            return []

        # Sort repos chronologically
        sorted_repos = sorted(repos, key=lambda r: r.created_at)

        # Determine year span
        first_year = sorted_repos[0].created_at.year
        last_year = sorted_repos[-1].created_at.year

        periods = []

        # Create time periods (2-year buckets)
        current_start = first_year
        while current_start <= last_year:
            period_end = min(current_start + 1, last_year)
            period_repos = [
                r
                for r in sorted_repos
                if current_start <= r.created_at.year <= period_end
            ]

            if period_repos:
                # Extract technologies with framework detection
                period_techs = set()
                for r in period_repos:
                    if r.primary_language:
                        period_techs.add(r.primary_language)

                    # ENHANCED: Detect frameworks
                    if r.key_files:
                        if any(f.endswith(".ino") for f in r.key_files):
                            period_techs.add("Arduino")

                        if r.primary_language == "HTML" or "HTML" in r.languages:
                            if any(
                                "vue" in f.lower() or f.endswith(".vue")
                                for f in r.key_files
                            ):
                                period_techs.add("Vue.js")
                            elif any(
                                "react" in f.lower()
                                or f.endswith(".jsx")
                                or f.endswith(".tsx")
                                for f in r.key_files
                            ):
                                period_techs.add("React")
                            elif any(
                                "angular" in f.lower() or "ng-" in f.lower()
                                for f in r.key_files
                            ):
                                period_techs.add("Angular")

                # Calculate FACTUAL metrics only
                total_commits = sum(r.total_commits for r in period_repos)
                avg_commits = total_commits // len(period_repos) if period_repos else 0

                # Find largest project by commits
                largest_project = max(period_repos, key=lambda r: r.total_commits)

                # Calculate code quality metrics (pure facts - counts only)
                repos_with_tests = [r for r in period_repos if r.has_tests]
                repos_with_readme = [
                    r for r in period_repos if r.readme_content and r.readme_size > 500
                ]

                # Domain focus - categorize by language (factual)
                domain_categories = []
                if any(
                    r.primary_language in ["Swift", "Kotlin", "Java"]
                    for r in period_repos
                ):
                    domain_categories.append("Mobile")
                if any(
                    r.primary_language
                    in ["TypeScript", "JavaScript", "Vue", "React", "HTML"]
                    for r in period_repos
                ):
                    domain_categories.append("Web")
                if any(
                    r.primary_language in ["Python", "Jupyter Notebook", "R"]
                    for r in period_repos
                ):
                    domain_categories.append("Data Science/Python")
                if any(
                    r.primary_language in ["Go", "Rust", "C", "C++"]
                    for r in period_repos
                ):
                    domain_categories.append("Systems")

                # Community recognition (only if stars > 0)
                popular = [r for r in period_repos if r.stars >= 5]
                total_stars = sum(r.stars for r in period_repos)

                # Build period data (PURE FACTS ONLY)
                period_label = (
                    f"{current_start}-{period_end}"
                    if period_end > current_start
                    else str(current_start)
                )

                period_data = {
                    "period": period_label,
                    "public_repos_created": len(period_repos),
                    "technologies_observed": sorted(list(period_techs)),
                    "total_commits": total_commits,
                    "avg_commits_per_repo": avg_commits,
                    "largest_project": (
                        f"{largest_project.name} ({largest_project.total_commits} commits, "
                        f"{largest_project.primary_language or 'Unknown'})"
                    ),
                    "domain_focus": (
                        domain_categories if domain_categories else ["General"]
                    ),
                    "code_quality_facts": {
                        "repos_with_tests": f"{len(repos_with_tests)}/{len(period_repos)}",
                        "repos_with_readme": f"{len(repos_with_readme)}/{len(period_repos)}",
                    },
                    "note": "Facts from public repos only",
                }

                # Only add community recognition if stars > 0
                if total_stars > 0:
                    period_data["community_recognition"] = {
                        "total_stars": total_stars,
                        "repos_with_5plus_stars": len(popular),
                    }

                periods.append(period_data)

            current_start = period_end + 1

        return periods

    def _extract_substantial_repos(self, repos: List[RepoData]) -> List[Dict[str, Any]]:
        """Extract substantial repos (ADAPTIVE threshold based on portfolio size)."""
        repo_count = len(repos)

        # Adaptive thresholds (matches filtering logic)
        if repo_count <= 5:
            min_commits_threshold = 0  # LENIENT
        elif repo_count <= 15:
            min_commits_threshold = 10  # MODERATE
        else:
            min_commits_threshold = 50  # STRICT

        substantial_repos = sorted(
            [r for r in repos if r.total_commits > min_commits_threshold],
            key=lambda r: r.total_commits,
            reverse=True,
        )[:10]  # Top 10

        structured = []
        for repo in substantial_repos:
            repo_dict = {
                "name": repo.name,
                "commits": repo.total_commits,
                "stars": repo.stars,
                "forks": repo.forks,
                "language": repo.primary_language,
                "size_mb": round(repo.size_kb / 1024, 2),  # Convert KB to MB
                "created": repo.created_at.strftime("%Y-%m-%d"),
                "description": (
                    repo.description[:100] if repo.description else "No description"
                ),
            }
            structured.append(repo_dict)

        return structured

    def _build_technology_evolution(self, repos: List[RepoData]) -> List[str]:
        """Build technology evolution evidence."""
        sorted_repos = sorted(repos, key=lambda r: r.created_at)

        tech_timeline: Dict[str, Dict[str, Any]] = {}
        for repo in sorted_repos:
            year = repo.created_at.strftime("%Y")
            if repo.primary_language:
                if repo.primary_language not in tech_timeline:
                    tech_timeline[repo.primary_language] = {
                        "first_year": year,
                        "repos": [],
                    }
                tech_timeline[repo.primary_language]["repos"].append(repo.name)

        evolution = []
        for tech, data in sorted(
            tech_timeline.items(), key=lambda x: str(x[1]["first_year"])
        ):
            repos_list = data["repos"]
            repos_count = len(repos_list)
            repos_preview = ", ".join(repos_list[:3])
            evolution.append(
                f"{tech}: First public use {data['first_year']}, used in {repos_count} repos "
                f"({repos_preview}{'...' if repos_count > 3 else ''})"
            )

        return evolution

    def _build_quality_progression(self, repos: List[RepoData]) -> List[str]:
        """Compare early vs late repos (quality progression)."""
        sorted_repos = sorted(repos, key=lambda r: r.created_at)

        if len(sorted_repos) < 6:
            return []

        progression = []

        early_third = sorted_repos[: len(sorted_repos) // 3]
        late_third = sorted_repos[-len(sorted_repos) // 3 :]

        # Testing adoption
        early_with_tests = [r for r in early_third if r.has_tests]
        late_with_tests = [r for r in late_third if r.has_tests]

        if len(late_with_tests) > len(early_with_tests):
            progression.append(
                f"Testing adoption: Early repos {len(early_with_tests)}/{len(early_third)} had tests, "
                f"recent repos {len(late_with_tests)}/{len(late_third)} have tests - improvement visible"
            )

        # Documentation evolution
        early_with_readme = [
            r for r in early_third if r.readme_content and r.readme_size > 500
        ]
        late_with_readme = [
            r for r in late_third if r.readme_content and r.readme_size > 500
        ]

        if len(late_with_readme) != len(early_with_readme):
            trend = (
                "improved"
                if len(late_with_readme) > len(early_with_readme)
                else "decreased"
            )
            progression.append(
                f"Documentation: Early repos {len(early_with_readme)}/{len(early_third)} had substantial READMEs, "
                f"recent {len(late_with_readme)}/{len(late_third)} - {trend}"
            )

        # Commit volume progression
        early_avg_commits = sum(r.total_commits for r in early_third) / len(early_third)
        late_avg_commits = sum(r.total_commits for r in late_third) / len(late_third)

        if late_avg_commits > early_avg_commits * 1.5:
            progression.append(
                f"Project scale: Early repos avg {early_avg_commits:.0f} commits, "
                f"recent avg {late_avg_commits:.0f} commits - larger projects over time"
            )

        return progression

    def _build_cross_repo_patterns(self, repos: List[RepoData]) -> List[str]:
        """Build cross-repo patterns (language consistency, domain focus)."""
        patterns = []

        # Language consistency
        lang_usage: Dict[str, int] = {}
        for repo in repos:
            if repo.primary_language:
                lang_usage[repo.primary_language] = (
                    lang_usage.get(repo.primary_language, 0) + 1
                )

        if lang_usage:
            dominant_lang = max(lang_usage.items(), key=lambda x: x[1])
            if dominant_lang[1] >= len(repos) * 0.7:
                patterns.append(
                    f"Language consistency: {dominant_lang[0]} used in {dominant_lang[1]}/{len(repos)} repos "
                    f"({dominant_lang[1] * 100 // len(repos)}%) - deep specialization"
                )

        # Domain focus from descriptions
        domain_keywords: Dict[str, int] = {}
        for repo in repos:
            if repo.description:
                desc_lower = repo.description.lower()
                for keyword in [
                    "data",
                    "machine learning",
                    "web",
                    "api",
                    "database",
                    "bio",
                    "analysis",
                ]:
                    if keyword in desc_lower:
                        domain_keywords[keyword] = domain_keywords.get(keyword, 0) + 1

        if domain_keywords:
            top_domain = max(domain_keywords.items(), key=lambda x: x[1])
            if top_domain[1] >= 3:
                patterns.append(
                    f"Domain focus: '{top_domain[0]}' theme in {top_domain[1]} repos - specialized interest area"
                )

        return patterns

    def _aggregate_technologies(self, repos: List[RepoData]) -> Dict[str, int]:
        """Aggregate technologies (simple count)."""
        tech_count: Dict[str, int] = {}

        for repo in repos:
            if repo.primary_language:
                tech_count[repo.primary_language] = (
                    tech_count.get(repo.primary_language, 0) + 1
                )

        return tech_count

    def _aggregate_quality_indicators(
        self, repos: List[RepoData], substantial_repos: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """Aggregate quality indicators (repo lists)."""
        indicators: Dict[str, List[str]] = {}

        # Repos with tests
        indicators["repos_with_tests"] = [r.name for r in repos if r.has_tests]

        # Repos with docs
        indicators["repos_with_docs"] = [
            r.name for r in repos if r.readme_content and r.readme_size > 500
        ]

        # Repos with CI
        indicators["repos_with_ci"] = [r.name for r in repos if r.has_ci]

        # Substantial repos
        indicators["substantial_repos"] = [r["name"] for r in substantial_repos]

        # Concept/documentation-only repos (no primary language)
        concept_repos = [r for r in repos if not r.primary_language]
        indicators["concept_repos"] = [
            f"{r.name} ({r.total_commits} commits, {r.stars} stars)"
            for r in concept_repos
        ]

        return indicators

    def _build_quality_indicators(self, repos: List[RepoData]) -> List[str]:
        """Build quality indicators list."""
        indicators = []

        repos_with_topics = sum(1 for r in repos if r.topics)
        repos_with_desc = sum(1 for r in repos if r.description)
        popular_repos = [r for r in repos if r.stars >= 5]

        indicators.append(
            f"{repos_with_topics}/{len(repos)} public repos have topics/tags"
        )
        indicators.append(
            f"{repos_with_desc}/{len(repos)} public repos have descriptions"
        )

        if popular_repos:
            indicators.append(f"{len(popular_repos)} public repos have 5+ stars")

        return indicators

    def _build_substance_indicators(
        self, substantial_repos: List[Dict[str, Any]]
    ) -> List[str]:
        """Build substance indicators for interview questions."""
        indicators = []

        for repo in substantial_repos:
            indicator = f"'{repo['name']}': {repo['commits']} commits"
            if repo.get("stars", 0) > 0:
                indicator += f", {repo['stars']} stars"
            if repo.get("language"):
                indicator += f", {repo['language']}"
            # Handle both old (size_kb) and new (size_mb) data for backward compatibility
            size_mb = repo.get("size_mb")
            if size_mb is None and repo.get("size_kb"):
                # Convert old KB data to MB
                size_mb = round(repo.get("size_kb", 0) / 1024, 2)
            if size_mb and size_mb > 1:
                indicator += f", {size_mb}MB"
            indicators.append(indicator)

        return indicators
