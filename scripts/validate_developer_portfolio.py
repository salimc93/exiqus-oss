#!/usr/bin/env python3
"""
Developer Portfolio Analysis Validation Script.

Tests developer portfolio analysis with real GitHub data and Anthropic API.
Validates the multi-repo public portfolio evolution approach with proper data limitations.
"""

import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import anthropic  # noqa: E402
import requests  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

from src.github_analyzer.utils.config import get_config  # noqa: E402
from src.github_analyzer.utils.logging import get_logger  # noqa: E402

# Load environment variables
load_dotenv()

logger = get_logger(__name__)


@dataclass
class RepoMetadata:
    """Metadata for a single repository in developer's portfolio."""

    name: str
    full_name: str
    url: str
    created_at: str
    updated_at: str
    pushed_at: str
    stars: int
    forks: int
    is_fork: bool
    is_archived: bool
    primary_language: Optional[str]
    languages: Dict[str, int]
    total_commits: int
    topics: List[str]
    description: Optional[str]
    size_kb: int
    readme_content: Optional[str] = None
    readme_size: int = 0
    file_structure: Optional[Dict[str, Any]] = None


@dataclass
class PortfolioEvidence:
    """Evidence patterns from public portfolio analysis."""

    public_repos_timeline: List[str] = field(default_factory=list)
    technology_adoption_in_public: List[str] = field(default_factory=list)
    observable_public_patterns: List[str] = field(default_factory=list)
    public_work_quality_indicators: List[str] = field(default_factory=list)
    timeline_gaps: List[str] = field(default_factory=list)
    cross_technology_evidence: List[str] = field(default_factory=list)
    portfolio_evolution_periods: List[Dict[str, Any]] = field(
        default_factory=list
    )  # Time periods

    # Legacy fields (still used in some places)
    code_quality_patterns: List[str] = field(default_factory=list)
    repo_substance_indicators: List[str] = field(default_factory=list)
    technology_evolution_evidence: List[str] = field(default_factory=list)
    quality_progression_evidence: List[str] = field(default_factory=list)
    cross_repo_patterns: List[str] = field(default_factory=list)

    # NEW: Structured aggregations (like batch analysis format)
    aggregated_code_patterns: Dict[str, Dict[str, Any]] = field(
        default_factory=dict
    )  # {pattern_name: {count, repos, evidence_samples}}
    aggregated_technologies: Dict[str, int] = field(
        default_factory=dict
    )  # {Python: 19, Jupyter: 5}
    aggregated_quality_indicators: Dict[str, List[str]] = field(
        default_factory=dict
    )  # {repos_with_tests: [repo1, repo2]}
    substantial_repos_structured: List[Dict[str, Any]] = field(
        default_factory=list
    )  # [{name, commits, stars, language, key_feature}]


@dataclass
class PortfolioAnalysisResult:
    """Complete developer portfolio analysis result."""

    # Core sections
    executive_summary: str
    data_limitations_warning: str
    key_observations: List[str]
    public_portfolio_evolution: List[Dict[str, Any]]
    evidence_patterns: List[Dict[str, str]]
    interview_questions: List[Dict[str, Any]]
    positive_indicators: List[str]  # NEW: Strengths visible in public repos
    areas_to_explore: List[str]  # NEW: Investigation areas (gaps/unknowns)
    recommendations: List[str]
    quality_indicators: List[Dict[str, str]]

    # Metadata
    username: str
    total_public_repos: int
    repos_analyzed: int
    repos_skipped: int
    skip_breakdown: Optional[Dict[str, int]] = (
        None  # NEW: Breakdown of why repos were skipped
    )
    oldest_repo_date: str = ""
    newest_repo_date: str = ""
    career_span_days: int = 0
    timeline_gaps_identified: int = 0

    # Optional fields with defaults
    confidence_explanation: str = ""
    raw_repo_data: Optional[List[Dict[str, Any]]] = None
    ai_tokens_used: int = 0
    ai_cost: float = 0.0
    api_calls: int = 0
    analysis_duration_seconds: float = 0.0


class DeveloperPortfolioAnalyzer:
    """Analyzes developer's public GitHub portfolio using GraphQL + REST."""

    def __init__(
        self,
        github_token: str,
        anthropic_api_key: str,
        model: str = "claude-sonnet-4-5-20250929",
    ):
        """Initialize with API credentials."""
        self.github_token = github_token
        self.anthropic_client = anthropic.Anthropic(
            api_key=anthropic_api_key,
            timeout=600.0,  # 10 minute timeout
            max_retries=2,
        )

        self.model = model  # Configurable model
        # Set max_tokens based on model (Haiku 3.5 = 8K, others = 16K)
        if "3-5-haiku" in model:
            self.max_tokens = 8000  # Haiku 3.5 limit is 8192
        else:
            self.max_tokens = 16000  # Sonnet/Haiku 4.5 support higher

        # Set up session with retry strategy (same as PR fetcher)
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        self.session = requests.Session()
        retry_strategy = Retry(
            total=5,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.headers.update(
            {
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github.v3+json",
            }
        )

        self.graphql_url = "https://api.github.com/graphql"
        self.request_timeout = 30

    def fetch_developer_repos_graphql(
        self, username: str, max_repos: int = 100
    ) -> Dict[str, Any]:
        """Fetch developer's public repos using GraphQL (efficient)."""
        logger.info(f"Fetching public repos for user: {username} via GraphQL")

        query = """
        query($username: String!, $cursor: String) {
          user(login: $username) {
            repositories(
              first: 100,
              after: $cursor,
              ownerAffiliations: OWNER,
              privacy: PUBLIC,
              orderBy: {field: CREATED_AT, direction: ASC}
            ) {
              totalCount
              pageInfo { hasNextPage, endCursor }
              nodes {
                name
                nameWithOwner
                description
                url
                createdAt
                updatedAt
                pushedAt
                stargazerCount
                forkCount
                isArchived
                isFork
                diskUsage
                primaryLanguage { name }
                languages(first: 10) {
                  edges {
                    node { name }
                    size
                  }
                }
                defaultBranchRef {
                  target {
                    ... on Commit {
                      history(first: 1) {
                        totalCount
                      }
                    }
                  }
                }
                repositoryTopics(first: 10) {
                  nodes {
                    topic { name }
                  }
                }
                readme: object(expression: "HEAD:README.md") {
                  ... on Blob {
                    text
                    byteSize
                  }
                }
                fileStructure: object(expression: "HEAD:") {
                  ... on Tree {
                    entries {
                      name
                      type
                      object {
                        ... on Blob {
                          byteSize
                        }
                      }
                    }
                  }
                }
                # File content will be fetched in second GraphQL call for substantial repos
              }
            }
          }
        }
        """

        repos: List[RepoMetadata] = []
        cursor = None
        api_calls = 0
        user_data = None

        while len(repos) < max_repos:
            variables = {"username": username, "cursor": cursor}

            response = self.session.post(
                self.graphql_url,
                json={"query": query, "variables": variables},
                timeout=self.request_timeout,
            )
            api_calls += 1

            if response.status_code != 200:
                logger.error(
                    f"GraphQL API error: {response.status_code} - {response.text[:200]}"
                )
                return {
                    "username": username,
                    "repos": [],
                    "total_public_repos": 0,
                    "api_calls": api_calls,
                    "oldest_repo_date": None,
                    "newest_repo_date": None,
                }

            data = response.json()
            if "errors" in data:
                logger.error(f"GraphQL errors: {data['errors']}")
                return {
                    "username": username,
                    "repos": [],
                    "total_public_repos": 0,
                    "api_calls": api_calls,
                    "oldest_repo_date": None,
                    "newest_repo_date": None,
                }

            user_data = data.get("data", {}).get("user", {})
            if not user_data:
                logger.warning(f"User {username} not found")
                return {
                    "username": username,
                    "repos": [],
                    "total_public_repos": 0,
                    "api_calls": api_calls,
                    "oldest_repo_date": None,
                    "newest_repo_date": None,
                }

            repo_connection = user_data.get("repositories", {})
            repo_nodes = repo_connection.get("nodes", [])

            for node in repo_nodes:
                if len(repos) >= max_repos:
                    break

                # Parse repo metadata
                languages = {}
                for edge in node.get("languages", {}).get("edges", []):
                    lang_name = edge.get("node", {}).get("name")
                    lang_size = edge.get("size", 0)
                    if lang_name:
                        languages[lang_name] = lang_size

                topics = [
                    t.get("topic", {}).get("name")
                    for t in node.get("repositoryTopics", {}).get("nodes", [])
                    if t.get("topic", {}).get("name")
                ]

                # Get commit count
                total_commits = 0
                default_branch = node.get("defaultBranchRef")
                repo_name = node.get("name", "UNKNOWN")
                if default_branch:
                    target = default_branch.get("target", {})
                    history = target.get("history", {})
                    total_commits = history.get("totalCount", 0)
                else:
                    print(
                        f"⚠️  {repo_name}: defaultBranchRef is NULL - will have 0 commits!"
                    )

                # Parse README
                readme_content = None
                readme_size = 0
                readme_obj = node.get("readme")
                if readme_obj:
                    readme_content = readme_obj.get("text", "")
                    readme_size = readme_obj.get("byteSize", 0)

                # Parse file structure
                file_structure = None
                file_structure_obj = node.get("fileStructure")
                if file_structure_obj:
                    entries = file_structure_obj.get("entries", [])
                    folders = [e["name"] for e in entries if e.get("type") == "tree"]
                    files = [e["name"] for e in entries if e.get("type") == "blob"]
                    file_structure = {
                        "total_files": len(files),
                        "folders": folders,
                        "files": files[:20],  # Top 20 files
                        "has_tests": any("test" in f.lower() for f in folders),
                        "has_docs": any("doc" in f.lower() for f in folders),
                        "has_src": any("src" in f.lower() for f in folders),
                    }

                repo_metadata = RepoMetadata(
                    name=node.get("name", ""),
                    full_name=node.get("nameWithOwner", ""),
                    url=node.get("url", ""),
                    created_at=node.get("createdAt", ""),
                    updated_at=node.get("updatedAt", ""),
                    pushed_at=node.get("pushedAt", ""),
                    stars=node.get("stargazerCount", 0),
                    forks=node.get("forkCount", 0),
                    is_fork=node.get("isFork", False),
                    is_archived=node.get("isArchived", False),
                    primary_language=(
                        node.get("primaryLanguage", {}).get("name")
                        if node.get("primaryLanguage")
                        else None
                    ),
                    languages=languages,
                    total_commits=total_commits,
                    topics=topics,
                    description=node.get("description"),
                    size_kb=node.get("diskUsage", 0),
                    readme_content=readme_content,
                    readme_size=readme_size,
                    file_structure=file_structure,
                )

                repos.append(repo_metadata)

            page_info = repo_connection.get("pageInfo", {})
            if not page_info.get("hasNextPage", False):
                break

            cursor = page_info.get("endCursor")

        total_count = (
            user_data.get("repositories", {}).get("totalCount", len(repos))
            if user_data
            else len(repos)
        )

        logger.info(
            f"Fetched {len(repos)} repos (total: {total_count}) in {api_calls} API calls"
        )

        return {
            "username": username,
            "repos": repos,
            "total_public_repos": total_count,
            "api_calls": api_calls,
            "oldest_repo_date": repos[0].created_at if repos else None,
            "newest_repo_date": repos[-1].created_at if repos else None,
        }

    def filter_repos(
        self, repos: List[RepoMetadata], include_forks: bool = False
    ) -> tuple[List[RepoMetadata], Dict[str, int]]:
        """Filter repos - remove forks, archived, empty repos. Returns (filtered_repos, skip_counts).

        Uses ADAPTIVE filtering based on total repo count:
        - If candidate has ≤5 original repos: Very lenient (≥1 commit, any size)
        - If candidate has 6-15 original repos: Moderate (≥2 commits, ≥5KB)
        - If candidate has >15 original repos: Strict (≥3 commits, ≥10KB)

        This ensures we don't filter out everything for candidates with small portfolios.
        """
        # First pass: Count original (non-fork) repos to determine filtering strictness
        original_repos = [r for r in repos if not r.is_fork]
        original_count = len(original_repos)

        # Determine filtering thresholds based on portfolio size
        if original_count <= 5:
            # VERY LENIENT: Candidate has few repos, keep almost everything
            min_commits = 1
            min_size_kb = 1  # Any size (even very small projects)
            strictness = "lenient"
            logger.info(
                f"Using LENIENT filtering ({original_count} original repos) - min {min_commits} commits, {min_size_kb}KB"
            )
        elif original_count <= 15:
            # MODERATE: Candidate has some repos, be selective
            min_commits = 2
            min_size_kb = 5
            strictness = "moderate"
            logger.info(
                f"Using MODERATE filtering ({original_count} original repos) - min {min_commits} commits, {min_size_kb}KB"
            )
        else:
            # STRICT: Candidate has many repos, focus on substantial work
            min_commits = 3
            min_size_kb = 10
            strictness = "strict"
            logger.info(
                f"Using STRICT filtering ({original_count} original repos) - min {min_commits} commits, {min_size_kb}KB"
            )

        filtered = []
        skip_counts = {
            "forks": 0,
            "archived": 0,
            "low_commits": 0,
            "trivial_size": 0,
        }
        skipped_repos = {
            "forks": [],
            "archived": [],
            "low_commits": [],
            "trivial_size": [],
        }

        for repo in repos:
            # Skip forks unless explicitly included
            if repo.is_fork and not include_forks:
                skip_counts["forks"] += 1
                skipped_repos["forks"].append(repo.name)
                logger.info(f"  ⏭️  SKIP (fork): {repo.name}")
                print(f"  ⏭️  SKIP (fork): {repo.name}")
                continue

            # Skip archived repos (always skip these)
            if repo.is_archived:
                skip_counts["archived"] += 1
                skipped_repos["archived"].append(repo.name)
                logger.info(f"  ⏭️  SKIP (archived): {repo.name}")
                print(f"  ⏭️  SKIP (archived): {repo.name}")
                continue

            # Skip repos below commit threshold (adaptive)
            if repo.total_commits < min_commits:
                skip_counts["low_commits"] += 1
                skipped_repos["low_commits"].append(
                    f"{repo.name} ({repo.total_commits} commits)"
                )
                logger.info(
                    f"  ⏭️  SKIP (low commits {repo.total_commits} < {min_commits}): {repo.name}"
                )
                print(
                    f"  ⏭️  SKIP (low commits {repo.total_commits} < {min_commits}): {repo.name}"
                )
                continue

            # Skip repos below size threshold (adaptive)
            if repo.size_kb < min_size_kb:
                skip_counts["trivial_size"] += 1
                skipped_repos["trivial_size"].append(f"{repo.name} ({repo.size_kb}KB)")
                logger.info(
                    f"  ⏭️  SKIP (trivial size {repo.size_kb}KB < {min_size_kb}KB): {repo.name}"
                )
                print(
                    f"  ⏭️  SKIP (trivial size {repo.size_kb}KB < {min_size_kb}KB): {repo.name}"
                )
                continue

            logger.info(
                f"  ✅ INCLUDE: {repo.name} ({repo.total_commits} commits, {repo.size_kb}KB)"
            )
            print(
                f"  ✅ INCLUDE: {repo.name} ({repo.total_commits} commits, {repo.size_kb}KB)"
            )
            filtered.append(repo)

        total_skipped = sum(skip_counts.values())
        logger.info(
            f"Filtered {len(repos)} repos → {len(filtered)} (skipped {total_skipped}: {skip_counts['forks']} forks, {skip_counts['archived']} archived, {skip_counts['low_commits']} low commits, {skip_counts['trivial_size']} trivial) [strictness: {strictness}]"
        )
        return filtered, skip_counts, skipped_repos

    def extract_portfolio_evidence(
        self, repos: List[RepoMetadata]
    ) -> PortfolioEvidence:
        """Extract evidence patterns from public portfolio."""
        evidence = PortfolioEvidence()

        if not repos:
            return evidence

        # Timeline of public repos
        for repo in repos:
            created_year = repo.created_at[:4]
            evidence.public_repos_timeline.append(
                f"{created_year}: {repo.name} ({repo.primary_language or 'Unknown'})"
            )

        # Technology adoption in public repos
        tech_first_seen = {}
        for repo in repos:
            if repo.primary_language and repo.primary_language not in tech_first_seen:
                tech_first_seen[repo.primary_language] = repo.created_at[:10]

        for tech, first_date in tech_first_seen.items():
            evidence.technology_adoption_in_public.append(
                f"{tech}: First observed in public repos on {first_date}"
            )

        # Quality indicators in public work
        repos_with_topics = sum(1 for r in repos if r.topics)
        repos_with_desc = sum(1 for r in repos if r.description)
        popular_repos = [r for r in repos if r.stars >= 5]

        evidence.public_work_quality_indicators.append(
            f"{repos_with_topics}/{len(repos)} public repos have topics/tags"
        )
        evidence.public_work_quality_indicators.append(
            f"{repos_with_desc}/{len(repos)} public repos have descriptions"
        )
        if popular_repos:
            evidence.public_work_quality_indicators.append(
                f"{len(popular_repos)} public repos have 5+ stars"
            )

        # Detect timeline gaps in public activity
        repo_years = sorted(set(r.created_at[:4] for r in repos))
        if len(repo_years) > 1:
            all_years = range(int(repo_years[0]), int(repo_years[-1]) + 1)
            for year in all_years:
                if str(year) not in repo_years:
                    evidence.timeline_gaps.append(
                        f"{year}: No public repository activity (likely private work)"
                    )

        # Cross-technology evidence with ENHANCED detection
        all_languages = set()
        enhanced_languages = set()  # Will include detected frameworks/platforms

        for repo in repos:
            # Add GitHub-reported languages
            if repo.primary_language:
                all_languages.add(repo.primary_language)
                enhanced_languages.add(repo.primary_language)
            all_languages.update(repo.languages.keys())
            enhanced_languages.update(repo.languages.keys())

            # ENHANCED: Detect Arduino, frameworks, platforms from file extensions
            if repo.file_structure and repo.file_structure.get("files"):
                files = repo.file_structure["files"]

                # Detect Arduino (.ino files)
                if any(f.endswith(".ino") for f in files):
                    enhanced_languages.add("Arduino")

                # Detect specific HTML frameworks (if HTML is present)
                if "HTML" in enhanced_languages:
                    # Check for Vue.js
                    if any("vue" in f.lower() or f.endswith(".vue") for f in files):
                        enhanced_languages.add("Vue.js")
                    # Check for React
                    elif any(
                        "react" in f.lower() or f.endswith(".jsx") or f.endswith(".tsx")
                        for f in files
                    ):
                        enhanced_languages.add("React")
                    # Check for Angular
                    elif any(
                        "angular" in f.lower() or "ng-" in f.lower() for f in files
                    ):
                        enhanced_languages.add("Angular")

        evidence.cross_technology_evidence.append(
            f"Technologies observed in public repos: {', '.join(sorted(enhanced_languages))}"
        )

        # NEW: Extract portfolio evolution by time periods (chronological grouping)
        # Group repos by year ranges to show evolution
        if repos:
            # Sort repos chronologically
            sorted_repos = sorted(repos, key=lambda r: r.created_at)

            # Determine year span
            first_year = int(sorted_repos[0].created_at[:4])
            last_year = int(sorted_repos[-1].created_at[:4])

            # Create time periods (2-year buckets)
            current_start = first_year
            while current_start <= last_year:
                period_end = min(current_start + 1, last_year)  # 2-year periods
                period_repos = [
                    r
                    for r in sorted_repos
                    if current_start <= int(r.created_at[:4]) <= period_end
                ]

                if period_repos:
                    # Extract technologies used in this period with ENHANCED detection
                    period_techs = set()
                    for r in period_repos:
                        if r.primary_language:
                            period_techs.add(r.primary_language)

                        # ENHANCED: Detect Arduino, frameworks, platforms from file extensions
                        if r.file_structure and r.file_structure.get("files"):
                            files = r.file_structure["files"]

                            # Detect Arduino (.ino files)
                            if any(f.endswith(".ino") for f in files):
                                period_techs.add("Arduino")

                            # Detect specific HTML frameworks (if HTML is present)
                            if r.primary_language == "HTML" or "HTML" in r.languages:
                                # Check for Vue.js
                                if any(
                                    "vue" in f.lower() or f.endswith(".vue")
                                    for f in files
                                ):
                                    period_techs.add("Vue.js")
                                # Check for React
                                elif any(
                                    "react" in f.lower()
                                    or f.endswith(".jsx")
                                    or f.endswith(".tsx")
                                    for f in files
                                ):
                                    period_techs.add("React")
                                # Check for Angular
                                elif any(
                                    "angular" in f.lower() or "ng-" in f.lower()
                                    for f in files
                                ):
                                    period_techs.add("Angular")

                    # Calculate FACTUAL metrics only (no judgments)
                    total_commits = sum(r.total_commits for r in period_repos)
                    avg_commits = (
                        total_commits // len(period_repos) if period_repos else 0
                    )

                    # Find largest project by commits (fact)
                    largest_project = (
                        max(period_repos, key=lambda r: r.total_commits)
                        if period_repos
                        else None
                    )

                    # Calculate code quality metrics (pure facts - counts only)
                    repos_with_tests = [
                        r
                        for r in period_repos
                        if r.file_structure and r.file_structure.get("has_tests")
                    ]
                    repos_with_readme = [
                        r
                        for r in period_repos
                        if r.readme_content and len(r.readme_content) > 500
                    ]

                    # Domain focus - categorize by language/purpose (factual categorization)
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

                    # Community recognition (only include if stars > 0 - don't penalize 0 stars)
                    popular = [r for r in period_repos if r.stars >= 5]
                    total_stars = sum(r.stars for r in period_repos)

                    # Build period data dictionary (PURE FACTS ONLY)
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
                            f"{largest_project.name} ({largest_project.total_commits} commits, {largest_project.primary_language or 'Unknown'})"
                            if largest_project
                            else None
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

                    # Only add community recognition if there ARE stars (never show 0)
                    if total_stars > 0:
                        period_data["community_recognition"] = {
                            "total_stars": total_stars,
                            "repos_with_5plus_stars": len(popular),
                        }

                    evidence.portfolio_evolution_periods.append(period_data)

                current_start = period_end + 1

        # NEW: Extract substantial repo indicators (for interview questions)
        # ADAPTIVE threshold based on portfolio size (matches filtering logic)
        repo_count = len(repos)
        if repo_count <= 5:
            # LENIENT: Include all repos (no minimum)
            min_commits_threshold = 0
        elif repo_count <= 15:
            # MODERATE: Include repos with decent activity
            min_commits_threshold = 10
        else:
            # STRICT: Only substantial repos
            min_commits_threshold = 50

        substantial_repos = sorted(
            [r for r in repos if r.total_commits > min_commits_threshold],
            key=lambda r: r.total_commits,
            reverse=True,
        )[:10]  # Top 10 by commits (increased from 5 to ensure coverage)

        for repo in substantial_repos:
            indicator = f"'{repo.name}': {repo.total_commits} commits"
            if repo.stars > 0:
                indicator += f", {repo.stars} stars"
            if repo.primary_language:
                indicator += f", {repo.primary_language}"
            if repo.size_kb > 1000:
                indicator += f", {repo.size_kb}KB"
            evidence.repo_substance_indicators.append(indicator)

        # NEW: Extract cross-repo patterns (like batch analysis does)
        # Technology Evolution: Track when technologies were adopted across repos
        tech_timeline: Dict[str, Dict[str, Any]] = {}
        for repo in sorted_repos:
            year = repo.created_at[:4]  # type: ignore[assignment]
            if repo.primary_language:
                if repo.primary_language not in tech_timeline:
                    tech_timeline[repo.primary_language] = {
                        "first_year": year,
                        "repos": [],
                    }
                repos_list = tech_timeline[repo.primary_language]["repos"]
                if isinstance(repos_list, list):
                    repos_list.append(repo.name)

        for tech, data in sorted(
            tech_timeline.items(), key=lambda x: str(x[1]["first_year"])
        ):
            repos_list = data["repos"]
            repos_count = len(repos_list) if isinstance(repos_list, list) else 0
            repos_preview = (
                ", ".join(repos_list[:3]) if isinstance(repos_list, list) else ""
            )
            evidence.technology_evolution_evidence.append(
                f"{tech}: First public use {data['first_year']}, used in {repos_count} repos ({repos_preview}{'...' if repos_count > 3 else ''})"
            )

        # Quality Progression: Compare early repos vs later repos
        if len(sorted_repos) >= 6:
            early_third = sorted_repos[: len(sorted_repos) // 3]
            late_third = sorted_repos[-len(sorted_repos) // 3 :]

            # Testing adoption
            early_with_tests = [
                r
                for r in early_third
                if r.file_structure and r.file_structure.get("has_tests")
            ]
            late_with_tests = [
                r
                for r in late_third
                if r.file_structure and r.file_structure.get("has_tests")
            ]
            if len(late_with_tests) > len(early_with_tests):
                evidence.quality_progression_evidence.append(
                    f"Testing adoption: Early repos {len(early_with_tests)}/{len(early_third)} had tests, "
                    f"recent repos {len(late_with_tests)}/{len(late_third)} have tests - improvement visible"
                )

            # Documentation evolution
            early_with_readme = [
                r
                for r in early_third
                if r.readme_content and len(r.readme_content) > 500
            ]
            late_with_readme = [
                r
                for r in late_third
                if r.readme_content and len(r.readme_content) > 500
            ]
            if len(late_with_readme) != len(early_with_readme):
                trend = (
                    "improved"
                    if len(late_with_readme) > len(early_with_readme)
                    else "decreased"
                )
                evidence.quality_progression_evidence.append(
                    f"Documentation: Early repos {len(early_with_readme)}/{len(early_third)} had substantial READMEs, "
                    f"recent {len(late_with_readme)}/{len(late_third)} - {trend}"
                )

            # Commit volume progression
            early_avg_commits = sum(r.total_commits for r in early_third) / len(
                early_third
            )
            late_avg_commits = sum(r.total_commits for r in late_third) / len(
                late_third
            )
            if late_avg_commits > early_avg_commits * 1.5:
                evidence.quality_progression_evidence.append(
                    f"Project scale: Early repos avg {early_avg_commits:.0f} commits, "
                    f"recent avg {late_avg_commits:.0f} commits - larger projects over time"
                )

        # Cross-Repo Patterns: Common patterns across multiple repos
        # Pattern: Consistent language use
        lang_usage: Dict[str, int] = {}
        for repo in repos:
            if repo.primary_language:
                lang_usage[repo.primary_language] = (
                    lang_usage.get(repo.primary_language, 0) + 1
                )

        dominant_lang = (
            max(lang_usage.items(), key=lambda x: x[1]) if lang_usage else None
        )
        if dominant_lang and dominant_lang[1] >= len(repos) * 0.7:
            evidence.cross_repo_patterns.append(
                f"Language consistency: {dominant_lang[0]} used in {dominant_lang[1]}/{len(repos)} repos ({dominant_lang[1] * 100 // len(repos)}%) - deep specialization"
            )

        # Pattern: Domain focus
        domain_keywords: Dict[str, int] = {}
        for repo in repos:
            if repo.description:
                # Simple keyword extraction
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
                evidence.cross_repo_patterns.append(
                    f"Domain focus: '{top_domain[0]}' theme in {top_domain[1]} repos - specialized interest area"
                )

        # NEW: Build structured aggregations (like batch analysis format)
        # This gives AI clear, structured data instead of string arrays

        # 1. Aggregate technologies (simple count)
        for repo in repos:
            if repo.primary_language:
                evidence.aggregated_technologies[repo.primary_language] = (
                    evidence.aggregated_technologies.get(repo.primary_language, 0) + 1
                )

        # 2. Aggregate quality indicators (repo lists)
        evidence.aggregated_quality_indicators["repos_with_tests"] = [
            r.name
            for r in repos
            if r.file_structure and r.file_structure.get("has_tests")
        ]
        evidence.aggregated_quality_indicators["repos_with_docs"] = [
            r.name for r in repos if r.readme_content and len(r.readme_content) > 500
        ]
        evidence.aggregated_quality_indicators["repos_with_ci"] = [
            r.name
            for r in repos
            if r.file_structure and r.file_structure.get("has_ci_cd")
        ]
        evidence.aggregated_quality_indicators["substantial_repos"] = [
            r.name for r in substantial_repos
        ]
        # Detect concept/documentation-only repos (no primary language)
        concept_repos = [r for r in repos if not r.primary_language]
        evidence.aggregated_quality_indicators["concept_repos"] = [
            f"{r.name} ({r.total_commits} commits, {r.stars} stars)"
            for r in concept_repos
        ]

        # 3. Structure substantial repos with key details (NO CODE EXTRACTION)
        for repo in substantial_repos[:10]:  # Top 10 substantial repos
            repo_dict = {
                "name": repo.name,
                "commits": repo.total_commits,
                "stars": repo.stars,
                "forks": repo.forks,
                "language": repo.primary_language,
                "size_kb": repo.size_kb,
                "created": repo.created_at[:10],  # Just date
                "description": (
                    repo.description[:100] if repo.description else "No description"
                ),
            }
            evidence.substantial_repos_structured.append(repo_dict)

        return evidence

    def calculate_career_span(
        self, oldest_date: str, newest_date: str
    ) -> tuple[int, List[str]]:
        """Calculate career span and identify gaps."""
        oldest = datetime.fromisoformat(oldest_date.replace("Z", "+00:00"))
        newest = datetime.fromisoformat(newest_date.replace("Z", "+00:00"))

        span_days = (newest - oldest).days

        return span_days, []

    def _get_context_description(self, context: str) -> str:
        """Get context-specific description for the prompt."""
        context_descriptions = {
            "startup": """
STARTUP CONTEXT FOCUS:
You are evaluating for a fast-moving startup where developers must:
- Ship features quickly with pragmatic technical decisions
- Wear multiple hats and adapt to changing priorities
- Build MVPs and iterate based on user feedback
- Work with limited resources and tight deadlines
- Make autonomous decisions with minimal process
- Balance speed with sustainable architecture
- Think in weeks and months, not years

Your interview questions should assess:
- Ability to prototype and iterate rapidly
- Comfort with ambiguity and changing requirements
- Pragmatic problem-solving under constraints
- Self-direction and initiative
""",
            "enterprise": """
ENTERPRISE CONTEXT FOCUS:
You are evaluating for a large enterprise organization where developers must:
- Work within established architectural standards and governance
- Collaborate across multiple teams and time zones
- Navigate complex approval and deployment processes
- Ensure compliance with security and regulatory requirements
- Maintain and evolve mission-critical legacy systems
- Document thoroughly for knowledge transfer
- Think in quarters and years, not weeks

Your interview questions should assess:
- Experience with large-scale systems and architecture
- Collaboration and communication in complex organizations
- Process adherence and documentation habits
- Security and quality mindset
- Ability to work within constraints
""",
            "agency": """
AGENCY CONTEXT FOCUS:
You are evaluating for an agency/consultancy where developers must:
- Deliver client projects with clear deadlines and budgets
- Context-switch between multiple projects and tech stacks
- Communicate technical decisions to non-technical stakeholders
- Create maintainable code for client handoffs
- Work with diverse teams and external stakeholders
- Balance quality with project constraints
- Think in sprints and project milestones

Your interview questions should assess:
- Client communication and project management skills
- Ability to context-switch and learn quickly
- Code handoff and documentation practices
- Balancing technical excellence with business constraints
""",
            "open_source": """
OPEN SOURCE CONTEXT FOCUS:
You are evaluating for open source maintainer/contributor roles where developers must:
- Build welcoming, inclusive communities around projects
- Communicate clearly with diverse global contributors
- Write comprehensive documentation for external users
- Respond to issues and PRs from the community
- Make code accessible and easy to contribute to
- Balance feature requests with project vision
- Think in terms of community health and sustainability

Your interview questions should assess:
- Community engagement and communication skills
- Documentation and knowledge-sharing practices
- Collaboration with external contributors
- Inclusivity and mentorship approach
- Responsiveness to community feedback
""",
        }
        return context_descriptions.get(context, context_descriptions["enterprise"])

    def _get_role_level_guidance(self, role_level: str) -> str:
        """Get role-level specific guidance for question generation."""
        role_guidance = {
            "junior": {
                "years": "0-2 years",
                "focus": "Fundamentals, basic implementation, learning approach, debugging basics, code comprehension",
                "avoid": "Architecture decisions, scaling strategies, distributed systems, advanced design patterns, multi-team coordination",
                "complexity": "Surface-level technical understanding",
                "tone": "Encouraging, supportive, focused on learning journey",
                "example": "Walk me through how you debugged an issue in this code",
            },
            "mid": {
                "years": "2-5 years",
                "focus": "Implementation decisions, testing strategies, code quality practices, problem-solving methodology, API design basics",
                "avoid": "Org-wide architecture, executive decisions, multi-team coordination, infrastructure at scale",
                "complexity": "Moderate technical depth with practical application",
                "tone": "Neutral, invitational, assumes professional experience exists",
                "example": "How did you decide between approach A and B for this feature?",
            },
            "senior": {
                "years": "5+ years",
                "focus": "System architecture, scalability strategies, technical leadership, mentorship approach, system design, cross-team collaboration",
                "avoid": "Implementation minutiae, junior-level basics, overly simplistic questions",
                "complexity": "Deep technical expertise with leadership thinking",
                "tone": "Respectful, collaborative, assumes extensive private/professional work",
                "example": "How would you scale this system to handle 10x traffic?",
            },
        }

        role = role_guidance.get(role_level, role_guidance["senior"])

        return f"""
🎯 **ROLE LEVEL CONTEXT**: {role_level.upper()} ({role["years"]})

**CRITICAL: ADJUST QUESTION COMPLEXITY FOR {role_level.upper()} ROLE**

**{role_level.upper()}-Level Question Requirements**:
- **Focus on**: {role["focus"]}
- **Avoid**: {role["avoid"]}
- **Complexity Level**: {role["complexity"]}
- **Example Question Style**: "{role["example"]}"
- **Tone**: {role["tone"]}

⚠️ **CRITICAL: NO LOADED OR ACCUSATORY QUESTIONS**
- ❌ DO NOT frame questions as "Why isn't X visible?" or "What have you been doing?"
- ❌ DO NOT imply gaps in public activity are negative or need justification
- ❌ DO NOT ask defensive questions like "Tell me why you don't have..."
- ✅ DO frame questions as INVITATIONS to share experience: "Tell me about..." or "Walk me through..."
- ✅ DO assume positive intent - most professional work is in private repositories
- ✅ DO keep questions BROAD and OPEN-ENDED, not specific accusations
- ✅ DO acknowledge that public repos are ONE data point, not complete picture

**TONE GUIDANCE**:
- Assume professional experience exists (especially for mid/senior)
- Frame questions as collaborative exploration, not interrogation
- Focus on learning about their approach, not challenging their gaps

⚠️ **IMPORTANT FOR {role_level.upper()}: "Avoid minutiae" applies to QUESTIONS ONLY**
- ✅ DO generate ALL required sections: Evidence Patterns, Quality Indicators, Observations, etc.
- ✅ DO include factual repo-level details (dates, commit counts, technology adoption timeline)
- ❌ DO NOT skip Evidence Patterns thinking they are "minutiae" - they are REQUIRED factual observations
- The "avoid minutiae" guidance means: don't ask questions about line-by-line code implementation details
"""

    def generate_portfolio_prompt(
        self,
        repo_data: Dict[str, Any],
        evidence: PortfolioEvidence,
        filtered_repos: List[RepoMetadata],
        context: str = "enterprise",
        role_level: str = "senior",
    ) -> str:
        """Generate prompt for portfolio analysis with hiring context and role level."""

        # Prepare evidence JSON (ONLY evidence, NO individual repo details!)
        evidence_json = {
            "public_portfolio_metadata": {
                "username": repo_data["username"],
                "total_public_repos": repo_data["total_public_repos"],
                "repos_analyzed": len(filtered_repos),
                "oldest_public_repo": repo_data["oldest_repo_date"],
                "newest_public_repo": repo_data["newest_repo_date"],
                "public_career_span_days": (
                    (
                        datetime.fromisoformat(
                            repo_data["newest_repo_date"].replace("Z", "+00:00")
                        )
                        - datetime.fromisoformat(
                            repo_data["oldest_repo_date"].replace("Z", "+00:00")
                        )
                    ).days
                    if repo_data["oldest_repo_date"] and repo_data["newest_repo_date"]
                    else 0
                ),
            },
            "portfolio_evolution_by_period": evidence.portfolio_evolution_periods,  # Pre-analyzed time periods
            # NEW: Structured aggregations (like batch analysis format) - Clear counts and repo lists
            "aggregated_code_patterns": evidence.aggregated_code_patterns,  # {pattern_name: {count, repos, evidence_samples}}
            "aggregated_technologies": evidence.aggregated_technologies,  # {Python: 19, Jupyter: 5}
            "aggregated_quality_indicators": evidence.aggregated_quality_indicators,  # {repos_with_tests: [repo1, repo2]}
            "substantial_repos_structured": evidence.substantial_repos_structured,  # [{name, commits, stars, language, key_feature}]
            # Legacy fields (keep for now, may deprecate later)
            "public_repos_timeline_sample": evidence.public_repos_timeline[:10],
            "technology_adoption_timeline": evidence.technology_adoption_in_public[:10],
            "public_work_quality_indicators": evidence.public_work_quality_indicators,
            "timeline_gaps": evidence.timeline_gaps,
            "technologies_summary": evidence.cross_technology_evidence,
            "code_quality_patterns": evidence.code_quality_patterns[
                :10
            ],  # Code patterns from samples
            "substantial_repos": evidence.repo_substance_indicators[
                :8
            ],  # Top repos for questions
            "cross_repo_patterns": evidence.cross_repo_patterns,  # NEW: Patterns across repos (like batch)
            "technology_evolution": evidence.technology_evolution_evidence,  # NEW: Tech progression over time
            "quality_progression": evidence.quality_progression_evidence,  # NEW: Quality improvement over time
        }

        # NO LONGER SENDING repo_details - evidence extraction already analyzed everything!
        # All data is now in evidence_json above (evolution periods, code patterns, substantial repos)

        return f"""You are a senior technical hiring consultant analyzing a developer's PUBLIC GitHub portfolio.

⚠️ CRITICAL DATA LIMITATIONS WARNING:

THIS ANALYSIS EXAMINES **PUBLIC REPOSITORIES ONLY**.

1. **Private Work is Invisible**: Most professional developers work primarily in private company repositories. Public repos may represent side projects, learning experiments, or portfolio pieces only.

2. **Timeline Gaps ≠ Inactivity**: Gaps in public activity DO NOT indicate no professional work. Developers may be employed full-time working in private repos.

3. **Technology Experience**: "First public use of X: 2021" ≠ "Learned X in 2021". Developer may have years of professional experience in technologies not visible in public repos.

4. **No Complete Picture**: We analyze public repos, public commits, public code patterns. We DO NOT analyze private repos, company work, professional experience, education, or certifications.

TERMINOLOGY REQUIREMENTS:
- Use "public portfolio evolution" NOT "skill evolution"
- Use "observable public work" NOT "developer capabilities"
- Use "public repository patterns" NOT "development practices"
- Use "first public use of X: DATE" NOT "learned X in DATE"
- Use "not observed in public repos" NOT "no experience with X"

⚠️ CRITICAL: DO NOT GENERATE NUMERIC SCORES, PERCENTAGES, RATINGS, OR ARBITRARY THRESHOLDS
- No numbers like 0.5, 70%, 3/5, etc.
- No "high/medium/low" based on numeric cutoffs
- Only report observable patterns from public repos
- NEVER include fields like "score", "rating", "percentage" in JSON

{self._get_context_description(context)}

{self._get_role_level_guidance(role_level)}

Public Portfolio Evidence (Pre-Analyzed): {json.dumps(evidence_json, indent=2)}

**IMPORTANT**: The evidence above includes:
- `portfolio_evolution_by_period`: Pre-analyzed time periods showing repo creation, technologies, and patterns over time
- `technology_evolution`: Technology adoption timeline showing when each tech was first used
- `quality_progression`: Quality improvement over time (testing, docs, project scale)
- `cross_repo_patterns`: Common patterns across repos (language consistency, domain focus)
- `code_quality_patterns`: Specific code patterns extracted from actual files (for interview questions)
- `substantial_repos_structured`: Top repos by commit count - USE THESE IN INTERVIEW QUESTIONS!
- `aggregated_code_patterns`: Code patterns detected across repos (hardcoded credentials, error handling, database code, etc.)
- `aggregated_quality_indicators.concept_repos`: List of concept/documentation-only repos (no primary_language) - IF THIS LIST EXISTS AND IS NOT EMPTY, you MUST create an evidence pattern called "Concept/Documentation Repositories" that explicitly lists these repos by name and notes they are README-only/documentation repos with NO implementation code. Example: "3 concept repos without code: 'PRECOMPUTED-AI-WEIGHTS' (117 commits, 19 stars), 'for-sponsors-only-hidden-repos-list' (7 commits, 16 stars), 'world_ai_flasher' (5 commits, 9 stars). These repos contain ideas/research documentation rather than implemented code."

Use these cross-repo patterns to understand evolution and create SPECIFIC interview questions that reference actual repos and code patterns.

Your job: Generate HONEST, EVIDENCE-BASED insights about this developer's PUBLIC work that help hiring teams understand:
- Observable patterns in public repository work
- Public portfolio evolution over time
- Technologies used in public projects
- Timeline gaps that may represent private work
- What questions to ask to understand COMPLETE experience

RESPONSE STRUCTURE (YOU MUST GENERATE ALL SECTIONS BELOW):

1. EXECUTIVE SUMMARY (2-3 sentences)
   - Focus on observable public work patterns
   - Note timeline span and repo count
   - Highlight key technologies in public repos
   - MUST acknowledge data limitations

2. DATA LIMITATIONS WARNING (2-3 sentences)
   - Remind that this is PUBLIC REPOS ONLY
   - Note what is NOT visible (private work, company repos)
   - Emphasize this is ONE data point for hiring decision

3. EVIDENCE PATTERNS (8-10 patterns) - **START HERE WITH RAW EVIDENCE**
   Each pattern as JSON:
   - "pattern": Name (e.g., "Testing in Public Repos", "Technology Adoption")
   - "evidence": Specific FACTUAL examples from public repos (NO JUDGMENTS - pure facts only with repo names, counts, dates)

   REMOVED FIELDS (DO NOT INCLUDE):
   - ❌ NO "scope" field (already stated in top warning section - DRY principle)
   - ❌ NO "hiring_relevance" field (Context system already explains hiring relevance - DRY principle)

   JUST PURE FACTS:
   ✅ Pattern name + Evidence (with specific repo names, counts, dates)
   ✅ Example: {{"pattern": "Testing Adoption", "evidence": "Testing in 2/9 repos: 'koa' (Vue, 2020), 'TapIn' (Swift, 2021). 7/9 repos show no test files."}}
   ✅ Example: {{"pattern": "Technology Timeline", "evidence": "TypeScript first seen 2019-02-08 in 'hornet', Python 2020-01-02 in 'chatbot2020', Swift 2021-07-10 in 'TapIn'. Each used in 1-3 repos."}}

4. KEY OBSERVATIONS (6-8 observations as bullet points starting with -)
   Based on the EVIDENCE PATTERNS above, synthesize key insights:
   - Observable pattern in PUBLIC repositories with specific evidence
   - Scoped explicitly to "public repos" or "public work"
   - Include specific repo names, counts, dates

   FORMAT AS MARKDOWN LIST:
   - First public TypeScript repo: 'backend-api' (2021-06, 45 commits). May have used professionally before this.
   - Testing patterns visible in 3/21 public repos: 'api-server', 'data-processor', 'web-app'. Professional testing practices unknown.
   - Gap in public activity 2020-2022 (15 months). Likely private work or employment not visible here.
   - Sustained educational commitment: 'Harvard-CS50' (436 commits, 2024), 'SoftUni-Python' (452 commits, 2023-2024)
   - Machine learning adoption: 'PyTorch-Tutorial' (first public use 2025-01), 'AI-Course' (436 commits). Professional ML experience needs verification.

5. PUBLIC PORTFOLIO EVOLUTION (REQUIRED - MUST GENERATE 3-5 time periods in markdown format)

   **YOU MUST GENERATE THIS SECTION!**

   CRITICAL: This section is PURE FACTS ONLY - NO JUDGMENTS, NO ASSERTIONS, NO INTERPRETATIONS!

   The evidence contains `portfolio_evolution_by_period` with rich factual metrics per time period:
   - public_repos_created: count
   - technologies_observed: list of languages
   - total_commits: sum across all repos in period
   - avg_commits_per_repo: average project size
   - largest_project: biggest repo by commits
   - domain_focus: Mobile, Web, Data Science/Python, Systems (based on languages used)
   - code_quality_facts: repos_with_tests (X/Y), repos_with_readme (X/Y)
   - community_recognition: total_stars, repos_with_5plus_stars (ONLY IF STARS > 0 - never show 0)

   Format as markdown with PURE FACTS ONLY:

   ### 2019-2020

   **Repos Created**: 6
   **Technologies**: HTML, Python, TypeScript, Vue
   **Total Commits**: 162 (avg 27/repo)
   **Domain**: Web, Data Science/Python
   **Largest Project**: 'webtech-assignments' (56 commits, HTML)
   **Code Quality**: Testing 0/6, README files 2/6

   ### 2021-2022

   **Repos Created**: 3
   **Technologies**: HTML, Jupyter Notebook, Swift
   **Total Commits**: 192 (avg 64/repo)
   **Domain**: Mobile, Data Science/Python
   **Largest Project**: 'TapIn' (117 commits, Swift)
   **Code Quality**: Testing 1/3, README files 2/3
   **Community Recognition**: 5 stars total, 1 repo with 5+ stars

   *Note: All metrics from public repositories only. Private work not visible.*

   **USE THE RICH DATA:** portfolio_evolution_by_period contains ALL these metrics. Just output the FACTS - no interpretations!

6. INTERVIEW QUESTIONS (REQUIRED - MUST GENERATE 8-10 questions in markdown format)

   **YOU MUST GENERATE THIS SECTION!**

   Ask about their ACTUAL WORK in SPECIFIC REPOS (like single repo analysis does), but across multiple repos to show evolution.

   **USE THE DATA:**
   - `substantial_repos_structured` for repo names/commits/details
   - `aggregated_code_patterns` for specific code patterns
   - `aggregated_quality_indicators` for testing/documentation data

   **FORMAT FOR EACH QUESTION** (FOLLOW THIS EXACTLY):
   ### Q[number]
   **[Your question about specific repo/code]**
   `category-name`
   💼 **Context**: [Business/hiring relevance - why this matters]
   📍 **Based on Evidence**: [Specific repo, file, commits, pattern]

   **Follow-up questions**:
   1. [Question 1]
   2. [Question 2]
   3. [Question 3]

   **Key Listening Points**:
   *[What to assess in their answer]*

   **CATEGORY OPTIONS** (PICK ONE - DO NOT LEAVE BLANK):
   - `architecture` - System design, architectural decisions, scalability
   - `code-quality` - Code organization, testing, maintainability
   - `problem-solving` - Technical problem-solving approach, debugging
   - `learning-agility` - Learning new technologies, adaptation
   - `collaboration` - Team work, code review, communication
   - `devops` - Deployment, CI/CD, infrastructure
   - `security` - Security practices, authentication, authorization
   - `performance` - Optimization, profiling, scalability
   - `database` - Data modeling, queries, migrations
   - `testing` - Testing strategy, TDD, quality assurance

   CRITICAL: Context must explain WHY this question matters, NOT repeat evidence!

   Example Context fields:
   - "Enterprise applications require thoughtful data layer architecture decisions that balance performance, maintainability, and team velocity"
   - "Startups need developers who can make pragmatic security decisions while moving fast"
   - "Agency work demands clear documentation and handoff practices for client projects"
   - "Open source projects benefit from contributors who understand community collaboration patterns"

   GOOD QUESTIONS (reference SPECIFIC repos from evidence):
   - "'protein_level_measurement' (68 commits) analyzes protein data. Walk me through your data processing pipeline architecture."
   - "'autoGraph' shows hardcoded credentials pattern (from aggregated_code_patterns). How would you architect database access for production?"
   - "Your projects grew from 'Newspaper-Analysis' (19 commits, 2019) to 'SoftUni-Software-Engineering' (452 commits, 2023). How did your architecture approach evolve?"

   BAD QUESTIONS (DO NOT generate these):
   - ❌ "What's your biology background?" (Generic, no repo reference)
   - ❌ "Tell me your employment history" (Not about their code)

   ⚠️ **CRITICAL: NO LOADED OR ACCUSATORY QUESTIONS** (APPLIES TO ALL ROLE LEVELS):
   - ❌ DO NOT frame questions as "Why isn't X visible?" or "What have you been doing?"
   - ❌ DO NOT imply gaps in public activity are negative or need justification
   - ❌ DO NOT ask defensive questions like "Tell me why you don't have..."
   - ✅ DO frame questions as INVITATIONS to share experience: "Tell me about..." or "Walk me through..."
   - ✅ DO assume positive intent - most professional work is in private repositories
   - ✅ DO keep questions BROAD and OPEN-ENDED, not specific accusations
   - ✅ DO acknowledge that public repos are ONE data point, not complete picture

   **BAD QUESTION EXAMPLES (NEVER GENERATE THESE)**:
   - ❌ "Your public activity stopped in 2023. Why isn't your recent work visible?"
   - ❌ "You have no tests. Why didn't you write tests?"
   - ❌ "Your repos lack documentation. What's your excuse?"

   **GOOD QUESTION EXAMPLES (GENERATE THESE INSTEAD)**:
   - ✅ "Tell me about your development journey and current work"
   - ✅ "Walk me through your testing approach in professional projects"
   - ✅ "How do you handle documentation in team environments?"

   **USE substantial_repos_structured AND aggregated_code_patterns TO GENERATE 8-10 SPECIFIC QUESTIONS!**

7. POSITIVE INDICATORS (REQUIRED - MUST GENERATE 5-7 strengths as markdown list starting with -)

   **YOU MUST GENERATE THIS SECTION!**

   State FACTS about STRENGTHS visible in public repos. These are positive patterns, good practices, or notable achievements. Pure observations, no exaggeration.

   FORMAT AS MARKDOWN LIST starting with "-":

   GOOD EXAMPLES (pure factual strengths):
   - Consistent commit activity across 13 repos spanning 601 days (2,341 total commits)
   - Project scale progression visible: early repos averaged 43 commits, recent projects exceed 400 commits
   - Database technology depth: PostgreSQL (547 commits), Python-ORM (547 commits) showing sustained backend focus
   - Testing adoption in advanced projects: 'Python-OOP' and 'JavaScript-Advanced' both include test files
   - Substantial README in 'Python-Fundamentals' (170 commits) demonstrates documentation capability
   - Sequential technology learning: Python → PLpgSQL → JavaScript progression over 18 months
   - Large-scale educational commitment: 'Python-OOP' (560 commits), 'Python-ORM' (547 commits), 'JavaScript-Advanced' (396 commits)

   BAD EXAMPLES (DO NOT generate these):
   - ❌ "Excellent coding skills" (Vague, judgmental)
   - ❌ "Quick learner" (Behavioral assumption)
   - ❌ "Strong work ethic" (Psychology, not observable)
   - ❌ "Good communication" (Can't assess from code alone)

   **CRITICAL**: Each indicator must be an OBSERVABLE FACT from public repos with specific numbers/dates/repo names. Focus on patterns that ARE present, not what's missing!

8. AREAS TO EXPLORE (REQUIRED - MUST GENERATE 5-7 investigation areas as markdown list starting with -)

   **YOU MUST GENERATE THIS SECTION!**

   State FACTS about what's MISSING or UNCLEAR in public repos - these are gaps/unknowns worth exploring in interviews. NO behavioral inferences, NO assumptions about why something is missing.

   FORMAT AS MARKDOWN LIST starting with "-":

   GOOD EXAMPLES (pure facts about gaps):
   - Lacks automated testing across all 13 public repos
   - No CI/CD configurations visible in any public projects
   - PostgreSQL used in 2 repos (547 commits) but database architecture decisions not documented
   - JavaScript used in 3 repos but no visible framework experience (React/Vue/Angular)
   - 0 forks and 6 total stars across all repos - collaborative development experience unknown
   - 9/13 repos have no descriptions or documentation
   - Commit history spans 2023-2025 but professional employment timeline not visible in public repos
   - Code review practices not observable in public solo projects
   - 'Python-OOP' has 560 commits but no README explaining project architecture or purpose

   BAD EXAMPLES (DO NOT generate these):
   - ❌ "Explore testing philosophy" (Behavioral inference)
   - ❌ "Understand learning approach" (Psychology, not facts)
   - ❌ "Verify if this represents real work" (Judgment)
   - ❌ "Discuss team collaboration skills" (This is an interview question, not a gap)
   - ❌ "Check references" (Generic hiring advice)

   **CRITICAL**: Each area must state OBSERVABLE FACTS about what's MISSING/UNCLEAR in public repos. This is PUBLIC data - they likely have testing/CI/CD/docs in private company work!

9. RECOMMENDATIONS (5-6 actionable items as markdown list starting with -)

   FORMAT AS MARKDOWN LIST:
   - Verify complete Python experience timeline including professional work not visible in public repos
   - Explore bioinformatics domain expertise depth - public repos show specialized knowledge but professional research experience needs assessment
   - Discuss testing practices and TDD experience - minimal testing visible in public repos but professional standards may differ
   - Clarify employment history and private repository work to understand complete professional background
   - Assess production system experience and enterprise-scale project work beyond visible personal projects
   - Probe ML/AI experience depth beyond recent public learning projects

10. QUALITY INDICATORS (6-8 indicators)
   Each indicator as JSON:
   - "indicator": Name
   - "observation": What was observed IN PUBLIC REPOS
   - "scope": "public repositories only"
   - "implication": What this suggests (with caveats)

11. EVIDENCE QUALITY ASSESSMENT (2-3 paragraphs)
   Similar to PR analysis format - assess the quality and limitations of the evidence:
   - Based on: Number of public repos, time span, commit counts, diversity
   - Limitations: Private repos not visible, professional work unknown, employment gaps invisible
   - Confidence level: What we can/cannot conclude from public repos alone
   - Example: "Based on 21 public repositories spanning 5+ years with substantial commit history (100-450 commits). However, private professional work, company repositories, and formal employment history are completely invisible. This represents a LIMITED view of the developer's complete capabilities."

⚠️ CRITICAL EVIDENCE REQUIREMENTS:

**BE SPECIFIC - NOT VAGUE:**

❌ BAD (vague, no evidence):
- "Few stars, minimal topics/tags, individual project patterns"
- "Recent technology adoption"
- "High development activity"

✅ GOOD (specific, with evidence):
- "Most popular repo: 'SoftUni-Python-Databases' (5 stars, 452 commits, created 2024-01). 20/21 other repos have 0-1 stars. Topics used in 6/21 repos (python, bioinformatics, database). 15/21 repos lack topic tags entirely."
- "MongoDB first appeared in 'data-acquisition' repo (2025-05, 8 commits). PyTorch first seen in 'Harvard_AI_Course' (2025-03, 436 commits). Both marked as learning/course projects."
- "Three substantial projects: 'SoftUni-Python-Databases' (452 commits, 2.4MB), 'Harvard_AI_Course' (436 commits, 1.8MB), 'protein-analysis-toolkit' (127 commits, 850KB). Average 100+ commits per major project showing sustained engagement."

**EVERY evidence statement must include:**
- Specific repo names (in quotes or italics)
- Exact counts (X/Y format)
- Dates (YYYY-MM format minimum)
- Sizes or commit counts
- Topics or language percentages

**Reference actual repos from the data provided above!**

Remember:
- EVERY insight must be scoped to "public repositories"
- ALWAYS acknowledge data limitations
- NEVER infer complete skill level from public repos only
- Frame questions to probe BEYOND what's visible
- Emphasize: This is ONE data point, not complete assessment
- BE SPECIFIC: Use repo names, stars, commits, dates in EVERY evidence statement
"""

    def analyze_with_ai(
        self,
        repo_data: Dict[str, Any],
        evidence: PortfolioEvidence,
        filtered_repos: List[RepoMetadata],
        context: str = "enterprise",
        role_level: str = "senior",
    ) -> PortfolioAnalysisResult:
        """Analyze portfolio data using Anthropic API."""
        logger.info(
            f"Analyzing portfolio with AI using {self.model} (context: {context}, role: {role_level})"
        )

        prompt = self.generate_portfolio_prompt(
            repo_data, evidence, filtered_repos, context, role_level
        )

        # Log prompt size
        logger.info(
            f"Prompt length: {len(prompt)} chars (~{len(prompt) // 4} tokens estimate)"
        )

        try:
            response = self.anthropic_client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}],
            )

            # Parse AI response
            first_block = response.content[0] if response.content else None
            ai_content = ""
            if first_block and hasattr(first_block, "text"):
                ai_content = first_block.text

            # Debug: Log first 500 chars of AI response
            logger.info(f"AI response preview: {ai_content[:500]}")
            logger.info(f"AI response length: {len(ai_content)} chars")

            # Calculate costs
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            total_tokens = input_tokens + output_tokens
            cost = (input_tokens * 3.0 + output_tokens * 15.0) / 1_000_000

            # Save raw AI output for debugging
            debug_output_path = f"developer_portfolio_validation/{repo_data['username']}_raw_ai_output_latest.txt"
            with open(debug_output_path, "w") as f:
                f.write(ai_content)
            logger.info(f"Saved raw AI output to {debug_output_path}")

            # Parse response
            result = self.parse_ai_response(ai_content, repo_data, filtered_repos)
            result.ai_tokens_used = total_tokens
            result.ai_cost = cost

            logger.info(
                f"AI analysis complete. Tokens: {total_tokens}, Cost: ${cost:.4f}"
            )

            return result

        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            # Calculate career span for error case too
            career_span_days = 0
            if repo_data.get("oldest_repo_date") and repo_data.get("newest_repo_date"):
                oldest = datetime.fromisoformat(
                    repo_data["oldest_repo_date"].replace("Z", "+00:00")
                )
                newest = datetime.fromisoformat(
                    repo_data["newest_repo_date"].replace("Z", "+00:00")
                )
                career_span_days = (newest - oldest).days

            return PortfolioAnalysisResult(
                executive_summary="Analysis failed due to AI error.",
                data_limitations_warning="PUBLIC REPOS ONLY",
                key_observations=[],
                public_portfolio_evolution=[],
                evidence_patterns=[],
                interview_questions=[],
                positive_indicators=[],  # NEW
                areas_to_explore=[],  # NEW
                recommendations=[],
                quality_indicators=[],
                username=repo_data["username"],
                total_public_repos=repo_data["total_public_repos"],
                repos_analyzed=len(filtered_repos),
                repos_skipped=0,
                oldest_repo_date=repo_data.get("oldest_repo_date", ""),
                newest_repo_date=repo_data.get("newest_repo_date", ""),
                career_span_days=career_span_days,
                timeline_gaps_identified=0,
            )

    def parse_ai_response(
        self,
        ai_content: str,
        repo_data: Dict[str, Any],
        filtered_repos: List[RepoMetadata],
    ) -> PortfolioAnalysisResult:
        """Parse AI response into structured result."""
        # Calculate career span
        career_span_days = 0
        if repo_data.get("oldest_repo_date") and repo_data.get("newest_repo_date"):
            oldest = datetime.fromisoformat(
                repo_data["oldest_repo_date"].replace("Z", "+00:00")
            )
            newest = datetime.fromisoformat(
                repo_data["newest_repo_date"].replace("Z", "+00:00")
            )
            career_span_days = (newest - oldest).days

        result = PortfolioAnalysisResult(
            executive_summary="",
            data_limitations_warning="",
            key_observations=[],
            public_portfolio_evolution=[],
            evidence_patterns=[],
            interview_questions=[],
            positive_indicators=[],  # NEW
            areas_to_explore=[],  # NEW
            recommendations=[],
            quality_indicators=[],
            username=repo_data["username"],
            total_public_repos=repo_data["total_public_repos"],
            repos_analyzed=len(filtered_repos),
            repos_skipped=repo_data["total_public_repos"] - len(filtered_repos),
            oldest_repo_date=repo_data.get("oldest_repo_date", ""),
            newest_repo_date=repo_data.get("newest_repo_date", ""),
            career_span_days=career_span_days,
            timeline_gaps_identified=0,
            raw_repo_data=[r.__dict__ for r in filtered_repos],
        )

        # Split content into sections
        import re

        lines = ai_content.split("\n")
        current_section = ""
        current_evolution_period = None
        current_question = None
        in_code_block = False
        code_block_lines = []

        for line in lines:
            if "EXECUTIVE SUMMARY" in line:
                current_section = "summary"
            elif "DATA LIMITATIONS" in line:
                current_section = "limitations"
            elif "KEY OBSERVATIONS" in line:
                current_section = "observations"
            elif "PUBLIC PORTFOLIO EVOLUTION" in line:
                current_section = "evolution"
            elif "EVIDENCE PATTERNS" in line:
                current_section = "patterns"
            elif "INTERVIEW QUESTIONS" in line:
                current_section = "questions"
            elif "POSITIVE INDICATORS" in line:
                current_section = "positive_indicators"
            elif "AREAS TO EXPLORE" in line:
                current_section = "areas_to_explore"
            elif "RECOMMENDATIONS" in line:
                current_section = "recommendations"
            elif "QUALITY INDICATORS" in line:
                current_section = "indicators"
            elif "EVIDENCE QUALITY ASSESSMENT" in line:
                current_section = "confidence"
            else:
                if current_section == "summary" and line.strip():
                    result.executive_summary += line.strip() + " "
                elif current_section == "limitations" and line.strip():
                    result.data_limitations_warning += line.strip() + " "
                elif current_section == "observations" and line.strip().startswith("-"):
                    result.key_observations.append(line.strip()[1:].strip())
                elif current_section == "recommendations" and line.strip().startswith(
                    "-"
                ):
                    result.recommendations.append(line.strip()[1:].strip())
                elif (
                    current_section == "positive_indicators"
                    and line.strip().startswith("-")
                ):
                    result.positive_indicators.append(line.strip()[1:].strip())
                elif current_section == "areas_to_explore" and line.strip().startswith(
                    "-"
                ):
                    result.areas_to_explore.append(line.strip()[1:].strip())
                elif current_section == "evolution":
                    # Parse markdown evolution periods: ### 2019-2020
                    if line.strip().startswith("###"):
                        if current_evolution_period:
                            result.public_portfolio_evolution.append(
                                current_evolution_period
                            )
                        period_name = line.strip().replace("###", "").strip()
                        current_evolution_period = {
                            "period": period_name,
                            "public_repos_created": 0,
                            "technologies_observed": [],
                            "total_commits": "",
                            "domain_focus": "",
                            "largest_project": "",
                            "code_quality": "",
                            "community_recognition": "",
                            "note": "",
                        }
                    elif current_evolution_period and (
                        "**Repos Created**:" in line
                        or "**Public Repos Created**:" in line
                    ):
                        # Extract number from "**Repos Created**: 3" or "**Public Repos Created**: 3"
                        match = re.search(r"(\d+)", line)
                        if match:
                            current_evolution_period["public_repos_created"] = int(
                                match.group(1)
                            )
                    elif current_evolution_period and (
                        "**Technologies**:" in line
                        or "**Technologies Observed**:" in line
                    ):
                        # Extract technologies from "**Technologies Observed**: Python, Jupyter"
                        tech_part = line.split(":")[-1].strip()
                        if tech_part and not tech_part.startswith("**"):
                            current_evolution_period["technologies_observed"] = [
                                t.strip() for t in tech_part.split(",")
                            ]
                    elif current_evolution_period and "**Total Commits**:" in line:
                        # Extract total commits like "**Total Commits**: 192 (avg 64/repo)"
                        commits_part = line.split(":")[-1].strip()
                        if commits_part and not commits_part.startswith("**"):
                            current_evolution_period["total_commits"] = commits_part
                    elif current_evolution_period and (
                        "**Domain**:" in line or "**Domain Focus**:" in line
                    ):
                        # Extract domain like "**Domain**: Mobile, Web" or "**Domain Focus**: Mobile, Web"
                        domain_part = line.split(":")[-1].strip()
                        if domain_part and not domain_part.startswith("**"):
                            current_evolution_period["domain_focus"] = domain_part
                    elif current_evolution_period and "**Largest Project**:" in line:
                        # Extract largest project like "**Largest Project**: 'TapIn' (117 commits, Swift)"
                        project_part = line.split(":")[-1].strip()
                        if project_part and not project_part.startswith("**"):
                            current_evolution_period["largest_project"] = project_part
                    elif current_evolution_period and "**Code Quality**:" in line:
                        # Extract code quality like "**Code Quality**: Testing 1/3, Documentation 2/3"
                        quality_part = line.split(":")[-1].strip()
                        if quality_part and not quality_part.startswith("**"):
                            current_evolution_period["code_quality"] = quality_part
                    elif (
                        current_evolution_period
                        and "**Community Recognition**:" in line
                    ):
                        # Extract community recognition like "**Community Recognition**: 5 stars total, 1 repo with 5+ stars"
                        recognition_part = line.split(":")[-1].strip()
                        if recognition_part and not recognition_part.startswith("**"):
                            current_evolution_period["community_recognition"] = (
                                recognition_part
                            )
                    elif current_evolution_period and "**Note**:" in line:
                        # Extract note like "**Note**: Facts from public repos only"
                        note_part = line.split(":")[-1].strip()
                        if note_part and not note_part.startswith("**"):
                            current_evolution_period["note"] = note_part
                elif current_section == "questions":
                    # Parse markdown questions: ### Q1
                    if line.strip().startswith("### Q"):
                        if current_question:
                            result.interview_questions.append(current_question)
                        current_question = {
                            "question": "",
                            "category": "",
                            "evidence": "",
                            "follow_up_questions": [],
                            "key_listening_points": "",
                            "context": "",
                            "code_snippet": "",  # NEW: Code snippet if available
                        }
                    elif (
                        current_question
                        and line.strip().startswith("**")
                        and not line.strip().startswith("**Based on")
                        and not line.strip().startswith("**Follow-up")
                        and not line.strip().startswith("**Key Listening")
                    ):
                        # Question text like "**Walk me through...**" (first ** line after ### Q)
                        question_text = line.strip().replace("**", "")
                        if not current_question[
                            "question"
                        ]:  # Only set if not already set
                            current_question["question"] = question_text
                    elif current_question and "**Context**" in line:
                        # Context line like 💼 **Context**: Enterprise applications require...
                        context_text = (
                            line.split(":")[-1].strip() if ":" in line else line.strip()
                        )
                        context_text = (
                            context_text.replace("💼", "")
                            .replace("**Context**", "")
                            .strip()
                        )
                        current_question["context"] = context_text
                    elif current_question and "Based on Evidence" in line:
                        # Evidence line like 📍 **Based on Evidence**: repo details
                        evidence = (
                            line.split(":")[-1].strip() if ":" in line else line.strip()
                        )
                        evidence = (
                            evidence.replace("📍", "")
                            .replace("**Based on Evidence**", "")
                            .strip()
                        )
                        current_question["evidence"] = evidence
                    elif current_question and line.strip().startswith("```"):
                        # Code block start/end
                        if not in_code_block:
                            in_code_block = True
                            code_block_lines = [line]
                        else:
                            # End of code block
                            code_block_lines.append(line)
                            current_question["code_snippet"] = "\n".join(
                                code_block_lines
                            )
                            in_code_block = False
                            code_block_lines = []
                    elif current_question and in_code_block:
                        # Inside code block - capture the line
                        code_block_lines.append(line)
                    elif (
                        current_question
                        and line.strip().startswith("`")
                        and line.strip().endswith("`")
                    ):
                        # Category like `architecture`
                        category = line.strip().replace("`", "")
                        current_question["category"] = category
                    elif current_question and "**Follow-up questions**:" in line:
                        # Start of follow-up questions section
                        pass  # Just mark that we're in this section
                    elif (
                        current_question
                        and line.strip()
                        and re.match(r"^\d+\.", line.strip())
                    ):
                        # Follow-up question like "1. What specific..."
                        follow_up = re.sub(r"^\d+\.\s*", "", line.strip())
                        follow_ups_list = current_question.get("follow_up_questions")
                        if isinstance(follow_ups_list, list):
                            follow_ups_list.append(follow_up)
                    elif current_question and "**Key Listening Points**:" in line:
                        # Start of key listening points section
                        pass  # Next line will have the points
                    elif (
                        current_question
                        and line.strip().startswith("*")
                        and line.strip().endswith("*")
                        and not line.strip().startswith("**")
                    ):
                        # Key listening points in italics like *Assess bioinformatics...*
                        listening_point = line.strip().replace("*", "")
                        current_question["key_listening_points"] = listening_point
                elif current_section == "confidence" and line.strip():
                    result.confidence_explanation += line.strip() + " "

        # Save last evolution period and question if any
        if current_evolution_period:
            result.public_portfolio_evolution.append(current_evolution_period)
        if current_question:
            result.interview_questions.append(current_question)

        # Extract JSON sections (only for patterns and indicators, evolution/questions are markdown now)

        # Evolution and Questions are now MARKDOWN format, skip JSON extraction for them

        try:
            patterns_match = re.search(
                r"EVIDENCE PATTERNS.*?(\[.*?\]).*?(?:INTERVIEW QUESTIONS|$)",
                ai_content,
                re.DOTALL,
            )
            if patterns_match:
                result.evidence_patterns = json.loads(patterns_match.group(1))
        except Exception:
            pass

        try:
            indicators_match = re.search(
                r"QUALITY INDICATORS.*?(\[.*?\]).*?(?:NEXT STEPS|$)",
                ai_content,
                re.DOTALL,
            )
            if indicators_match:
                result.quality_indicators = json.loads(indicators_match.group(1))
        except Exception:
            pass

        return result

    def format_markdown_report(self, result: PortfolioAnalysisResult) -> str:
        """Format analysis result as markdown."""
        report = f"""# Developer Portfolio Analysis - {result.username}

## 📊 Analysis Metadata
- **Total Public Repos**: {result.total_public_repos}
- **Original Repos Analyzed**: {result.repos_analyzed}"""

        # Add skip breakdown if available
        if result.skip_breakdown:
            forks = result.skip_breakdown.get("forks", 0)
            archived = result.skip_breakdown.get("archived", 0)
            low_commits = result.skip_breakdown.get("low_commits", 0)
            trivial_size = result.skip_breakdown.get("trivial_size", 0)
            other_skipped = archived + low_commits + trivial_size

            if forks > 0:
                report += f"\n- **Forks**: {forks} (analyzed separately via [PR Analysis](https://github.com/features) feature)"
            if other_skipped > 0:
                skip_details = []
                if archived > 0:
                    skip_details.append(f"{archived} archived")
                if low_commits > 0:
                    skip_details.append(f"{low_commits} low commits")
                if trivial_size > 0:
                    skip_details.append(f"{trivial_size} trivial size")
                report += f"\n- **Other Skipped**: {other_skipped} ({', '.join(skip_details)})"
        else:
            report += f"\n- **Repos Skipped**: {result.repos_skipped} (forks, archived, trivial)"

        report += f"""
- **Oldest Public Repo**: {result.oldest_repo_date[:10]}
- **Newest Public Repo**: {result.newest_repo_date[:10]}
- **Public Portfolio Span**: {result.career_span_days} days ({result.career_span_days // 365} years)
- **Timeline Gaps**: {result.timeline_gaps_identified}
- **Model**: claude-sonnet-4-5-20250929
- **Tokens Used**: {result.ai_tokens_used:,}
- **Analysis Cost**: ${result.ai_cost:.4f}
- **GraphQL API Calls**: {result.api_calls}
- **Total Analysis Time**: {result.analysis_duration_seconds}s

---

## ⚠️ CRITICAL DATA LIMITATIONS

**THIS ANALYSIS EXAMINES PUBLIC REPOSITORIES ONLY**

{result.data_limitations_warning}

**What this means:**
- ❌ Private company work is NOT visible
- ❌ Professional experience may be significantly greater
- ❌ Technology experience may predate public repos
- ❌ Gaps in public activity likely represent private work
- ✅ This is ONE data point for hiring decisions

---

## 🏢 Executive Summary

{result.executive_summary}

### Analysis Confidence Level
{result.confidence_explanation}

---

## 💡 Key Observations (Public Repos Only)

"""
        for i, obs in enumerate(result.key_observations, 1):
            report += f"{i}. {obs}\n"

        report += """
---

## 📈 Public Portfolio Evolution

"""
        for period in result.public_portfolio_evolution:
            if isinstance(period, dict):
                report += f"### {period.get('period', 'Unknown Period')}\n\n"
                report += (
                    f"**Repos Created**: {period.get('public_repos_created', 0)}\n"
                )

                # Handle technologies - can be list or string
                techs = period.get("technologies_observed", [])
                if isinstance(techs, list):
                    report += f"**Technologies**: {', '.join(techs)}\n"
                else:
                    report += f"**Technologies**: {techs}\n"

                # Add total commits if present
                if period.get("total_commits"):
                    report += f"**Total Commits**: {period.get('total_commits')}\n"

                # Add domain focus if present
                if period.get("domain_focus"):
                    report += f"**Domain**: {period.get('domain_focus')}\n"

                # Add largest project if present
                if period.get("largest_project"):
                    report += f"**Largest Project**: {period.get('largest_project')}\n"

                # Add code quality if present
                if period.get("code_quality"):
                    report += f"**Code Quality**: {period.get('code_quality')}\n"

                # Add community recognition if present (only shows if stars > 0)
                if period.get("community_recognition"):
                    report += f"**Community Recognition**: {period.get('community_recognition')}\n"

                report += "\n"

        # Add ONE note at the end instead of repeating for each period
        report += "*Note: All metrics from public repositories only. Private work not visible.*\n\n"

        report += """
---

## 🔍 Evidence Patterns

"""
        for pattern in result.evidence_patterns:
            if isinstance(pattern, dict):
                report += f"### {pattern.get('pattern', 'Unknown Pattern')}\n\n"
                report += f"{pattern.get('evidence', 'N/A')}\n\n"

        report += """
---

## 💬 Interview Questions

**Purpose**: Probe BEYOND public repos to understand complete experience

"""
        for i, question in enumerate(result.interview_questions, 1):
            if isinstance(question, dict):
                report += f"### Q{i}: {question.get('question', 'N/A')}\n\n"
                report += f"**Category**: `{question.get('category', 'general')}`\n"
                report += f"**Context**: {question.get('context', 'N/A')}\n"

                # Add evidence field if present
                if question.get("evidence"):
                    report += f"**📍 Based on Evidence**: {question.get('evidence')}\n"

                report += f"**⚠️ Data Scope**: {question.get('public_data_disclaimer', 'Based on public repositories only')}\n\n"

                # Add code snippet if present
                if question.get("code_snippet"):
                    report += f"**Code from repo**:\n{question.get('code_snippet')}\n\n"

                # Check for both field name variants (follow_up_prompts or follow_up_questions)
                follow_ups_field = question.get("follow_up_prompts") or question.get(
                    "follow_up_questions", []
                )
                follow_ups = (
                    follow_ups_field if isinstance(follow_ups_field, list) else []
                )
                if follow_ups:
                    report += "**Follow-up Questions**:\n"
                    for follow_up in follow_ups:
                        report += f"- {follow_up}\n"
                    report += "\n"

                # Check for interview_focus or key_listening_points
                listening_points = question.get(
                    "interview_focus", question.get("key_listening_points", "")
                )
                if listening_points:
                    report += "**Key Listening Points**:\n"
                    if isinstance(listening_points, list):
                        for point in listening_points:
                            report += f"- {point}\n"
                    else:
                        report += f"- {listening_points}\n"
                    report += "\n"

        report += """
---

## ✨ Positive Indicators

"""
        for indicator in result.positive_indicators:
            report += f"- {indicator}\n"

        report += """
---

## 🔍 Areas to Explore

"""
        for area in result.areas_to_explore:
            report += f"- {area}\n"

        report += """
---

## ✅ Recommendations

"""
        for i, rec in enumerate(result.recommendations, 1):
            report += f"{i}. {rec}\n"

        report += """
---

## 📈 Quality Indicators (Public Work Only)

"""
        for indicator in result.quality_indicators:  # type: ignore[assignment]
            if isinstance(indicator, dict):
                report += f"### {indicator.get('indicator', 'N/A')}\n\n"
                report += f"**Observation** (public repos): {indicator.get('observation', 'N/A')}\n"
                report += (
                    f"**Scope**: {indicator.get('scope', 'public repositories only')}\n"
                )
                report += f"**Implication**: {indicator.get('implication', 'N/A')}\n\n"

        report += """
---

## 🎯 Next Steps for Hiring Team

1. **Review this analysis** as ONE data point (not complete picture)
2. **Use interview questions** to probe beyond public repos
3. **Ask about timeline gaps** to understand private/professional work
4. **Verify technology experience** beyond what's visible publicly
5. **Combine with**: Resume, interviews, technical assessments, references

**Remember**: Most professional developers work primarily in private repos. Public portfolio may not reflect complete capabilities.
"""

        return report


def main() -> None:
    """Main validation function."""
    import argparse

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Analyze developer's GitHub portfolio")
    parser.add_argument("username", help="GitHub username to analyze")
    parser.add_argument(
        "--context",
        choices=["startup", "enterprise", "agency", "open_source"],
        default="enterprise",
        help="Hiring context for analysis (default: enterprise)",
    )
    parser.add_argument(
        "--role",
        choices=["junior", "mid", "senior"],
        default="senior",
        help="Role level for question generation (default: senior)",
    )
    parser.add_argument(
        "--model",
        default="claude-sonnet-4-5-20250929",
        help="Anthropic model to use (default: claude-sonnet-4-5-20250929)",
    )
    args = parser.parse_args()

    config = get_config()
    github_token = os.getenv("GITHUB_TOKEN") or getattr(
        getattr(config, "github", None), "token", None
    )
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY") or getattr(
        config, "anthropic_api_key", None
    )

    if not github_token or not anthropic_api_key:
        logger.error("Missing API credentials. Set GITHUB_TOKEN and ANTHROPIC_API_KEY.")
        sys.exit(1)

    # Use command-line provided username
    test_users = [args.username]
    hiring_context = args.context
    role_level = args.role

    analyzer = DeveloperPortfolioAnalyzer(
        github_token, anthropic_api_key, model=args.model
    )

    # Create output directory
    output_dir = "developer_portfolio_validation"
    os.makedirs(output_dir, exist_ok=True)

    for username in test_users:
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Analyzing developer portfolio for: {username}")
        logger.info(f"{'=' * 60}")

        # Fetch repos via GraphQL
        import time

        start_time = time.time()

        repo_data = analyzer.fetch_developer_repos_graphql(username, max_repos=100)

        if not repo_data or not repo_data.get("repos"):
            logger.warning(f"No repo data found for {username}")
            continue

        # Filter repos
        filtered_repos, skip_counts, skipped_repos = analyzer.filter_repos(
            repo_data["repos"], include_forks=False
        )

        if not filtered_repos:
            logger.warning(f"No repos to analyze for {username} after filtering")
            continue

        # Extract evidence
        evidence = analyzer.extract_portfolio_evidence(filtered_repos)

        # Analyze with AI (pass hiring context and role level)
        result = analyzer.analyze_with_ai(
            repo_data, evidence, filtered_repos, hiring_context, role_level
        )

        # Add skip breakdown to result
        result.skip_breakdown = skip_counts

        # Calculate total time
        end_time = time.time()
        total_duration = end_time - start_time

        # Add timing and API call metrics to result
        result.api_calls = repo_data.get("api_calls", 0)
        result.analysis_duration_seconds = round(total_duration, 2)

        # Format report
        markdown_report = analyzer.format_markdown_report(result)

        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_short = (
            args.model.replace("claude-", "")
            .replace("-20250929", "")
            .replace("-20250514", "")
            .replace("-20241022", "")
            .replace("-20251001", "")
        )
        output_file = os.path.join(
            output_dir, f"{username}_{model_short}_{role_level}_{timestamp}.md"
        )
        with open(output_file, "w") as f:
            f.write(markdown_report)

        logger.info(f"Report saved to: {output_file}")

        # Save JSON
        json_file = os.path.join(
            output_dir, f"{username}_{model_short}_{role_level}_{timestamp}.json"
        )
        with open(json_file, "w") as f:
            json.dump(
                {
                    "username": result.username,
                    "metadata": {
                        "total_public_repos": result.total_public_repos,
                        "repos_analyzed": result.repos_analyzed,
                        "repos_skipped": result.repos_skipped,
                        "skip_counts": skip_counts,
                        "skipped_repos": skipped_repos,
                        "analyzed_repos": [r.name for r in filtered_repos],
                        "oldest_repo": result.oldest_repo_date,
                        "newest_repo": result.newest_repo_date,
                        "timeline_gaps": result.timeline_gaps_identified,
                        "tokens": result.ai_tokens_used,
                        "cost": result.ai_cost,
                    },
                    "summary": result.executive_summary,
                    "limitations": result.data_limitations_warning,
                    "observations": result.key_observations,
                    "evolution": result.public_portfolio_evolution,
                    "patterns": result.evidence_patterns,
                    "questions": result.interview_questions,
                    "recommendations": result.recommendations,
                    "indicators": result.quality_indicators,
                },
                f,
                indent=2,
            )

        # Print summary
        print(f"\n✅ Analysis complete for {username}")
        print(f"   - Total public repos: {result.total_public_repos}")
        print(f"   - Repos analyzed: {result.repos_analyzed}")
        print(f"   - Repos skipped: {result.repos_skipped}")
        print(f"   - Key observations: {len(result.key_observations)}")
        print(f"   - Evidence patterns: {len(result.evidence_patterns)}")
        print(f"   - Interview questions: {len(result.interview_questions)}")
        print(f"   - Timeline gaps: {result.timeline_gaps_identified}")
        print(f"   - Cost: ${result.ai_cost:.4f}")


if __name__ == "__main__":
    main()
