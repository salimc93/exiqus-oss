# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Repository classification for cost-optimized analysis decisions.

This module determines whether repositories should receive template responses
or AI-powered analysis based on complexity, activity, and quality indicators.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from ..data.models import RepositoryData
from ..utils.config import get_config
from ..utils.logging import get_logger

logger = get_logger(__name__)


class AnalysisMethod(Enum):
    """Analysis method recommendation."""

    TEMPLATE = "template"
    AI = "ai"


class TemplateCategory(Enum):
    """Categories for template responses."""

    INACTIVE = "inactive"  # >2 years inactive
    MINIMAL = "minimal"  # <3 commits
    POOR_PRACTICES = "poor_practices"  # Clear anti-patterns
    LEARNING = "learning"  # Tutorial/educational content
    EMPTY = "empty"  # No meaningful content
    ARCHIVED = "archived"  # Explicitly archived
    FORK = "fork"  # Fork without significant changes


class RepositoryType(Enum):
    """Sophisticated repository type classification for business logic."""

    PORTFOLIO = "portfolio"  # Personal showcase projects
    LEARNING = "learning"  # Educational journey/tutorial work
    PRODUCTION = "production"  # Enterprise/production applications
    OPEN_SOURCE = "open_source"  # Community/library projects
    EXPERIMENTAL = "experimental"  # Research/prototype projects
    ABANDONED = "abandoned"  # Stale/inactive projects
    FORK_CONTRIBUTION = "fork_contribution"  # Meaningful fork contributions
    FORK_PERSONAL = "fork_personal"  # Personal forks without changes
    MONOREPO = "monorepo"  # Large multi-project repositories


@dataclass
class ClassificationResult:
    """Result of repository classification."""

    method: AnalysisMethod
    template_category: Optional[TemplateCategory] = None
    repository_type: Optional[RepositoryType] = None
    reasoning: str = ""
    cost_estimate: float = 0.0  # USD

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "method": self.method.value,
            "template_category": (
                self.template_category.value if self.template_category else None
            ),
            "repository_type": (
                self.repository_type.value if self.repository_type else None
            ),
            "reasoning": self.reasoning,
            "cost_estimate": self.cost_estimate,
        }


class RepositoryClassifier:
    """
    Classifier for determining analysis method based on repository characteristics.

    Implements cost-optimization strategy by routing simple/obvious cases to
    template responses and complex cases to AI analysis.
    """

    def __init__(self) -> None:
        """Initialize classifier with configuration."""
        self.config = get_config()
        self.analysis_config = self.config.analysis
        self.cost_config = self.config.cost

        # Classification thresholds
        self.inactive_threshold_days = self.analysis_config.template_threshold_days
        self.min_commits_threshold = self.analysis_config.min_commits_for_ai

        # Cost estimates (per analysis)
        self.template_cost = 0.0
        self.ai_cost_estimate = 0.0015  # Average between $0.001-0.002

    def classify(self, repo_data: RepositoryData) -> ClassificationResult:
        """
        Classify repository for analysis method and type.

        Args:
            repo_data: Repository data to classify

        Returns:
            Classification result with method, type, and reasoning
        """
        logger.debug(f"Classifying repository: {repo_data.full_name}")

        # First determine repository type
        repo_type = self._classify_repository_type(repo_data)

        # Check template conditions in priority order
        template_result = self._check_template_conditions(repo_data)
        if template_result:
            template_result.repository_type = repo_type
            return template_result

        # Default to AI analysis for complex cases
        ai_result = self._recommend_ai_analysis(repo_data)
        ai_result.repository_type = repo_type
        return ai_result

    def classify_repository(self, repo_data: RepositoryData) -> ClassificationResult:
        """
        Alias for classify method for backward compatibility.

        Args:
            repo_data: Repository data to classify

        Returns:
            Classification result with method and reasoning
        """
        return self.classify(repo_data)

    def _check_template_conditions(
        self, repo_data: RepositoryData
    ) -> Optional[ClassificationResult]:
        """Check if repository qualifies for template response."""

        # 1. Content-free or trivial repositories (HIGHEST PRIORITY CHECK)
        # This MUST come first to catch minimal repos before other conditions
        if self._is_content_free_or_trivial(repo_data):
            return ClassificationResult(
                method=AnalysisMethod.TEMPLATE,
                template_category=TemplateCategory.EMPTY,
                reasoning="Repository lacks sufficient content for meaningful analysis",
                cost_estimate=self.template_cost,
            )

        # 2. Archived repositories
        if repo_data.is_archived:
            return ClassificationResult(
                method=AnalysisMethod.TEMPLATE,
                template_category=TemplateCategory.ARCHIVED,
                reasoning="Repository is explicitly archived",
                cost_estimate=self.template_cost,
            )

        # 3. Inactive repositories (>2 years)
        # EXCEPTION: Don't mark as inactive if repo has substantial commit history (>30 commits)
        # These are completed projects worth analyzing even if old
        if repo_data.metrics.days_since_last_commit > self.inactive_threshold_days:
            # Exception for repos with substantial development history
            if repo_data.metrics.total_commits > 30:
                logger.info(
                    f"Repository {repo_data.full_name} is old but has substantial history "
                    f"({repo_data.metrics.total_commits} commits) - allowing AI analysis"
                )
            else:
                return ClassificationResult(
                    method=AnalysisMethod.TEMPLATE,
                    template_category=TemplateCategory.INACTIVE,
                    reasoning=(
                        "Repository inactive for "
                        f"{repo_data.metrics.days_since_last_commit} "
                        f"days (>{self.inactive_threshold_days} threshold)"
                    ),
                    cost_estimate=self.template_cost,
                )

        # 4. Minimal commit history
        if repo_data.metrics.total_commits < self.min_commits_threshold:
            return ClassificationResult(
                method=AnalysisMethod.TEMPLATE,
                template_category=TemplateCategory.MINIMAL,
                reasoning=(
                    f"Only {repo_data.metrics.total_commits} commits "
                    f"(<{self.min_commits_threshold} threshold)"
                ),
                cost_estimate=self.template_cost,
            )

        # 5. Empty or nearly empty repositories
        if self._is_empty_repository(repo_data):
            return ClassificationResult(
                method=AnalysisMethod.TEMPLATE,
                template_category=TemplateCategory.EMPTY,
                reasoning="Repository has minimal content",
                cost_estimate=self.template_cost,
            )

        # 5. Fork without significant changes
        if self._is_unmodified_fork(repo_data):
            return ClassificationResult(
                method=AnalysisMethod.TEMPLATE,
                template_category=TemplateCategory.FORK,
                reasoning="Fork with minimal original contributions",
                cost_estimate=self.template_cost,
            )

        # 6. Documentation-only repositories
        if self._is_documentation_only_repository(repo_data):
            return ClassificationResult(
                method=AnalysisMethod.TEMPLATE,
                template_category=TemplateCategory.MINIMAL,
                reasoning="Documentation-only repository with no significant code",
                cost_estimate=self.template_cost,
            )

        # 7. Hello World / Single file repositories
        if self._is_hello_world_repository(repo_data):
            return ClassificationResult(
                method=AnalysisMethod.TEMPLATE,
                template_category=TemplateCategory.LEARNING,
                reasoning="Minimal hello-world or single-file example",
                cost_estimate=self.template_cost,
            )

        # 8. Learning/tutorial repositories
        if self._is_learning_repository(repo_data):
            return ClassificationResult(
                method=AnalysisMethod.TEMPLATE,
                template_category=TemplateCategory.LEARNING,
                reasoning="Appears to be learning/tutorial content",
                cost_estimate=self.template_cost,
            )

        # 7. Poor practices (clear anti-patterns)
        if self._has_poor_practices(repo_data):
            return ClassificationResult(
                method=AnalysisMethod.TEMPLATE,
                template_category=TemplateCategory.POOR_PRACTICES,
                reasoning="Repository shows clear anti-patterns",
                cost_estimate=self.template_cost,
            )

        return None  # No template conditions met

    def _recommend_ai_analysis(self, repo_data: RepositoryData) -> ClassificationResult:
        """Recommend AI analysis for complex repositories."""

        reasoning_parts = []

        # Activity indicators
        if repo_data.metrics.days_since_last_commit <= 30:
            reasoning_parts.append("recently active")

        # Quality indicators
        if repo_data.has_tests:
            reasoning_parts.append("has tests")
        if repo_data.has_readme and len(repo_data.readme_content or "") > 500:
            reasoning_parts.append("good documentation")
        if repo_data.has_ci_config:
            reasoning_parts.append("CI/CD configured")

        # Complexity indicators
        if len(repo_data.languages) > 1:
            reasoning_parts.append(f"{len(repo_data.languages)} languages")
        if repo_data.metrics.unique_contributors > 1:
            reasoning_parts.append(
                f"{repo_data.metrics.unique_contributors} contributors"
            )

        reasoning = (
            f"Complex repository with: {', '.join(reasoning_parts)}"
            if reasoning_parts
            else "Repository requires nuanced analysis"
        )

        return ClassificationResult(
            method=AnalysisMethod.AI,
            reasoning=reasoning,
            cost_estimate=self.ai_cost_estimate,
        )

    def _is_empty_repository(self, repo_data: RepositoryData) -> bool:
        """Check if repository is empty, nearly empty, or lacks meaningful content."""

        # Calculate content indicators
        empty_indicators = 0

        # Size-based checks
        if repo_data.size < 10:  # Less than 10KB
            empty_indicators += 3
        elif repo_data.size < 50:  # Less than 50KB
            empty_indicators += 2
        elif repo_data.size < 100:  # Less than 100KB
            empty_indicators += 1

        # File count checks
        total_files = len([f for f in repo_data.file_structure if f.type == "file"])
        if total_files == 0:
            return True  # Definitively empty
        elif total_files < 3:
            empty_indicators += 2
        elif total_files < 5:
            empty_indicators += 1

        # Check for meaningful code files
        CODE_EXTENSIONS = {
            "py",
            "js",
            "ts",
            "java",
            "cpp",
            "c",
            "cs",
            "rb",
            "go",
            "rs",
            "php",
            "kt",
            "swift",
            "m",
            "h",
            "cc",
            "cxx",
            "scala",
            "clj",
            "lua",
            "r",
            "pl",
            "sh",
            "ps1",
            "bat",
            "asm",
            "f90",
            "jl",
            "dart",
            "elm",
            "ex",
            "ino",  # Arduino sketches
            # Hardware description languages
            "v",  # Verilog
            "vh",  # Verilog header
            "sv",  # SystemVerilog
            "vhd",  # VHDL
            "vhdl",  # VHDL
            # Web templates and markup (needed for Flask, Express, Rails apps)
            "html",
            "htm",
            "ejs",
            "erb",
            "jsx",
            "tsx",
            "vue",
            "svelte",
        }

        code_files = [
            f
            for f in repo_data.file_structure
            if f.type == "file"
            and not f.is_documentation
            and f.extension
            and f.extension.lower() in CODE_EXTENSIONS
        ]

        # No code files at all
        if len(code_files) == 0:
            empty_indicators += 3
        elif len(code_files) < 2:
            empty_indicators += 2

        # Check meaningful code content (not just placeholders)
        total_code_size = sum(f.size for f in code_files)
        if total_code_size < 500:  # Less than 500 bytes total
            empty_indicators += 2
        elif total_code_size < 1000:  # Less than 1KB total
            empty_indicators += 1

        # Check commit patterns
        if repo_data.metrics.total_commits < 3:
            empty_indicators += 1

        # Check if mostly documentation
        if total_files > 0:
            doc_files = [
                f
                for f in repo_data.file_structure
                if f.type == "file" and f.is_documentation
            ]
            doc_ratio = len(doc_files) / total_files
            if doc_ratio > 0.8:  # More than 80% documentation
                empty_indicators += 2

        # CRITICAL ESCAPE HATCH: Check actual lines of code
        # Even if repo is small/few files, substantial code (100+ LOC) should be analyzed
        # This prevents false positives like LagouSpider (173 LOC in main.py)
        if code_files:
            total_loc: float = 0.0
            for code_file in code_files:
                # Estimate lines of code from file size
                # Average: ~50 characters per line including whitespace/comments
                estimated_loc = code_file.size / 50
                total_loc += estimated_loc

            # If we have substantial code (100+ lines), allow AI analysis
            if total_loc >= 100:
                logger.info(
                    f"Repository {repo_data.full_name} has substantial code "
                    f"(~{int(total_loc)} LOC) despite small size/file count - allowing AI analysis"
                )
                return False  # Not empty - has real implementation

        # Return true if multiple indicators suggest empty/minimal repo
        return empty_indicators >= 4

    def _is_content_free_or_trivial(self, repo_data: RepositoryData) -> bool:
        """High-priority check for content-free or trivial repositories.

        This method is deeply skeptical and does NOT trust language statistics.
        It focuses on raw, verifiable facts about repository content.
        """
        # CRITICAL: Size check - less than 10KB is almost always trivial
        if repo_data.size < 10:  # Less than 10KB
            logger.info(
                f"Repository {repo_data.full_name} is trivial: size {repo_data.size}KB < 10KB"
            )
            return True

        # File count check - fewer than 3 files is insufficient
        # NOTE: Lowered from 5 to 3 because functional apps (Flask, Express) can have few files
        # Example: app.py + models.py + template.html = 3 files but real functionality
        total_files = len([f for f in repo_data.file_structure if f.type == "file"])
        if total_files < 3:
            logger.info(
                f"Repository {repo_data.full_name} is trivial: {total_files} files < 3"
            )
            return True

        # Check for actual code content (not trusting language percentages)
        CODE_EXTENSIONS = {
            "py",
            "js",
            "ts",
            "java",
            "cpp",
            "c",
            "cs",
            "rb",
            "go",
            "rs",
            "php",
            "kt",
            "swift",
            "m",
            "h",
            "cc",
            "cxx",
            "scala",
            "clj",
            "lua",
            "r",
            "ino",  # Arduino sketches
            # Hardware description languages
            "v",  # Verilog
            "vh",  # Verilog header
            "sv",  # SystemVerilog
            "vhd",  # VHDL
            "vhdl",  # VHDL
            # Web templates and markup (needed for Flask, Express, Rails apps)
            "html",
            "htm",
            "ejs",
            "erb",
            "jsx",
            "tsx",
            "vue",
            "svelte",
        }

        code_files = [
            f
            for f in repo_data.file_structure
            if f.type == "file"
            and f.extension
            and f.extension.lower() in CODE_EXTENSIONS
        ]

        # No real code files
        if len(code_files) == 0:
            logger.info(
                f"Repository {repo_data.full_name} is trivial: no code files found"
            )
            return True

        # Check if the "primary" file is essentially empty
        # Look for the largest code file
        if code_files:
            largest_code_file = max(code_files, key=lambda f: f.size)
            if largest_code_file.size < 100:  # Less than 100 bytes
                logger.info(
                    f"Repository {repo_data.full_name} is trivial: largest code file is {largest_code_file.size} bytes"
                )
                return True

        # Total code content check
        total_code_size = sum(f.size for f in code_files)
        if total_code_size < 500:  # Less than 500 bytes total
            logger.info(
                f"Repository {repo_data.full_name} is trivial: total code size {total_code_size} bytes < 500"
            )
            return True

        # Commit check - very few commits suggest no real development
        if repo_data.metrics.total_commits < 3:
            # Combined with small size, this is a strong indicator
            if repo_data.size < 50:  # Less than 50KB
                logger.info(
                    f"Repository {repo_data.full_name} is trivial: {repo_data.metrics.total_commits} commits and size {repo_data.size}KB"
                )
                return True

        # Additional check for joke/demo repositories
        # If ALL conditions are met, it's likely trivial:
        # - Small overall size (<25KB)
        # - Few commits (<10)
        # - Limited code files (<3)
        if (
            repo_data.size < 25
            and repo_data.metrics.total_commits < 10
            and len(code_files) < 3
        ):
            # ESCAPE HATCH: Check actual lines of code before flagging as trivial
            # Even small repos can have substantial implementation (e.g., LagouSpider: 173 LOC)
            if code_files:
                total_loc = sum(
                    f.size / 50 for f in code_files
                )  # Estimate LOC (50 chars/line avg)
                if total_loc >= 100:
                    logger.info(
                        f"Repository {repo_data.full_name} has substantial code (~{int(total_loc)} LOC) "
                        f"despite small size/commits/files - allowing AI analysis"
                    )
                    return False  # Not trivial - has real implementation

            logger.info(
                f"Repository {repo_data.full_name} is likely a demo/joke: size {repo_data.size}KB, {repo_data.metrics.total_commits} commits, {len(code_files)} code files"
            )
            return True

        return False

    def _is_documentation_only_repository(self, repo_data: RepositoryData) -> bool:
        """Check if repository is primarily documentation."""

        # Define code extensions as class constant (could move to __init__)
        CODE_EXTENSIONS = {
            "py",
            "js",
            "ts",
            "java",
            "cpp",
            "c",
            "cs",
            "rb",
            "go",
            "rs",
            "php",
            "kt",
            "swift",
            "m",
            "h",
            "cc",
            "cxx",
            "scala",
            "clj",
            "lua",
            "r",
            "pl",
            "sh",
            "ps1",
            "bat",
            "asm",
            "f90",
            "jl",
            "dart",
            "elm",
            "ex",
            "ino",  # Arduino sketches
        }

        # Count file types using existing is_documentation flag
        doc_files = [
            f
            for f in repo_data.file_structure
            if f.type == "file" and f.is_documentation
        ]
        code_files = [
            f
            for f in repo_data.file_structure
            if f.type == "file"
            and not f.is_documentation
            and f.extension
            and f.extension.lower() in CODE_EXTENSIONS
        ]

        total_files = len([f for f in repo_data.file_structure if f.type == "file"])

        # Documentation-only indicators
        if len(code_files) == 0 and len(doc_files) > 0:
            return True

        # Mostly documentation (>90% docs)
        if total_files > 0 and len(doc_files) / total_files > 0.9:
            return True

        # "Awesome" list pattern - common documentation repos
        if "awesome" in repo_data.name.lower() and len(code_files) < 3:
            return True

        # Other documentation patterns
        doc_patterns = {"docs", "documentation", "wiki", "knowledge", "notes", "guide"}
        if (
            any(pattern in repo_data.name.lower() for pattern in doc_patterns)
            and len(code_files) < 5
        ):
            return True

        return False

    def _is_hello_world_repository(self, repo_data: RepositoryData) -> bool:
        """Check if repository is a simple hello world or minimal example."""

        # Check for hello world patterns in name/description
        hello_patterns = {
            "hello",
            "helloworld",
            "hello-world",
            "hello_world",
            "test",
            "example",
            "sample",
        }
        name_lower = repo_data.name.lower()

        # Strong indicator if in name
        if any(pattern in name_lower for pattern in hello_patterns):
            # Validate it's actually minimal
            if (
                len(repo_data.file_structure) < 5
                and repo_data.metrics.total_commits < 5
            ):
                return True

        # Single file repositories
        code_files = [
            f
            for f in repo_data.file_structure
            if f.type == "file"
            and not f.is_documentation
            and f.extension
            in {"py", "js", "ts", "java", "cpp", "c", "cs", "rb", "go", "rs", "php"}
        ]

        # Single small code file
        if len(code_files) == 1 and code_files[0].size < 2000:  # Less than 2KB
            return True

        # Very minimal repo (1-2 files total)
        total_files = len([f for f in repo_data.file_structure if f.type == "file"])
        if total_files <= 2 and repo_data.size < 50:  # Less than 50KB total
            return True

        return False

    def _is_unmodified_fork(self, repo_data: RepositoryData) -> bool:
        """Check if repository is a fork without significant changes."""

        if not repo_data.is_fork:
            return False

        # Few commits suggest minimal changes
        if repo_data.metrics.total_commits < 5:
            return True

        # Single contributor suggests no collaboration
        if repo_data.metrics.unique_contributors == 1:
            return True

        return False

    def _is_learning_repository(self, repo_data: RepositoryData) -> bool:
        """Check if repository appears to be for learning purposes."""

        # Learning keywords in name or description
        learning_keywords = {
            "tutorial",
            "learning",
            "practice",
            "exercise",
            "bootcamp",
            "course",
            "lesson",
            "study",
            "example",
            "demo",
            "sample",
            "beginner",
            "intro",
            "basic",
            "fundamentals",
        }

        name_lower = repo_data.name.lower()
        desc_lower = (repo_data.description or "").lower()

        for keyword in learning_keywords:
            if keyword in name_lower or keyword in desc_lower:
                return True

        # Multiple small, simple files (common in tutorials)
        if len(repo_data.file_structure) > 5:
            small_files = [
                f
                for f in repo_data.file_structure
                if f.type == "file" and f.size < 1000
            ]  # Less than 1KB
            if (
                len(small_files) > len(repo_data.file_structure) * 0.7
            ):  # 70% small files
                return True

        return False

    def _has_poor_practices(self, repo_data: RepositoryData) -> bool:
        """Check for clear anti-patterns and poor practices."""

        # No README (for non-trivial projects)
        if not repo_data.has_readme and repo_data.metrics.total_commits > 5:
            return True

        # No tests for significant projects
        if (
            not repo_data.has_tests
            and repo_data.metrics.total_commits > 10
            and repo_data.size > 1000
        ):  # >1MB
            return True

        # Poor commit patterns
        if repo_data.metrics.commit_frequency < 0.1:  # Less than 1 commit per 10 weeks
            return True

        # Check for poor naming patterns
        poor_naming_patterns = {
            "untitled",
            "new",
            "test",
            "asd",
            "qwerty",
            "temp",
            "backup",
        }

        name_lower = repo_data.name.lower()
        for pattern in poor_naming_patterns:
            if pattern in name_lower:
                return True

        return False

    def _classify_repository_type(self, repo_data: RepositoryData) -> RepositoryType:
        """
        Classify repository into business logic types.

        Args:
            repo_data: Repository data to classify

        Returns:
            Repository type classification
        """
        # Check for abandoned projects first
        if (
            repo_data.is_archived
            or repo_data.metrics.days_since_last_commit > 730  # >2 years
        ):
            return RepositoryType.ABANDONED

        # Check for fork types
        if repo_data.is_fork:
            if self._is_meaningful_fork(repo_data):
                return RepositoryType.FORK_CONTRIBUTION
            else:
                return RepositoryType.FORK_PERSONAL

        # Check for monorepo pattern early (before other classifications)
        if self._is_monorepo(repo_data):
            return RepositoryType.MONOREPO

        # Check for production applications first (enterprise patterns)
        if self._is_production_project(repo_data):
            return RepositoryType.PRODUCTION

        # Check for open source libraries/tools (high confidence)
        if self._is_open_source_project(repo_data):
            return RepositoryType.OPEN_SOURCE

        # Check for experimental/research projects (specific indicators)
        if self._is_experimental_project(repo_data):
            return RepositoryType.EXPERIMENTAL

        # Check for learning/tutorial projects (can overlap with portfolio)
        if self._is_learning_project(repo_data):
            return RepositoryType.LEARNING

        # Default to portfolio project
        return RepositoryType.PORTFOLIO

    def _is_meaningful_fork(self, repo_data: RepositoryData) -> bool:
        """Check if fork has meaningful contributions."""
        # Multiple contributors suggests collaboration
        if repo_data.metrics.unique_contributors > 2:
            return True

        # Significant commit history
        if repo_data.metrics.total_commits > 20:
            return True

        # Active development
        if repo_data.metrics.days_since_last_commit < 90:
            return True

        # Has issues or discussions
        if repo_data.open_issues > 3:
            return True

        return False

    def _is_learning_project(self, repo_data: RepositoryData) -> bool:
        """Enhanced learning project detection."""
        learning_indicators = 0

        # Name/description keywords
        learning_keywords = {
            "tutorial",
            "learning",
            "practice",
            "exercise",
            "bootcamp",
            "course",
            "lesson",
            "study",
            "example",
            "demo",
            "sample",
            "beginner",
            "intro",
            "basic",
            "fundamentals",
            "training",
            "workshop",
            "homework",
            "assignment",
            "challenge",
        }

        text_to_check = f"{repo_data.name} {repo_data.description or ''}".lower()
        for keyword in learning_keywords:
            if keyword in text_to_check:
                learning_indicators += 2
                break

        # Topic tags
        learning_topics = {"tutorial", "learning", "education", "course", "example"}
        for topic in repo_data.topics:
            if topic.lower() in learning_topics:
                learning_indicators += 1

        # Structure patterns typical of learning projects
        if len(repo_data.file_structure) < 20:  # Simple structure
            learning_indicators += 1

        # Multiple small files (exercises)
        small_files = [
            f for f in repo_data.file_structure if f.type == "file" and f.size < 2000
        ]
        if len(small_files) > len(repo_data.file_structure) * 0.6:
            learning_indicators += 1

        # Low star count (not widely used)
        if repo_data.stars < 5:
            learning_indicators += 1

        return learning_indicators >= 3

    def _is_monorepo(self, repo_data: RepositoryData) -> bool:
        """Detect if repository is a monorepo based on structure and patterns."""
        monorepo_indicators = 0

        # Check file count (monorepos typically have many files)
        if len(repo_data.file_structure) >= 1000:  # Hit our limit
            monorepo_indicators += 3

        # Look for monorepo tool configs
        monorepo_configs = {
            "lerna.json",
            "nx.json",
            "rush.json",
            "pnpm-workspace.yaml",
            "yarn.lock",
            "package-lock.json",
            "Cargo.lock",
        }
        file_names = {
            f.name.lower() for f in repo_data.file_structure if f.type == "file"
        }
        if monorepo_configs.intersection(file_names):
            monorepo_indicators += 2

        # Check for typical monorepo directory patterns
        top_level_dirs = [
            f.name.lower()
            for f in repo_data.file_structure
            if f.type == "dir" and "/" not in f.path
        ]
        monorepo_patterns = {
            "packages",
            "services",
            "apps",
            "modules",
            "libs",
            "cmd",
            "pkg",
        }
        matching_patterns = monorepo_patterns.intersection(set(top_level_dirs))
        if len(matching_patterns) >= 2:
            monorepo_indicators += 3
        elif len(matching_patterns) == 1:
            monorepo_indicators += 1

        # Large size is an indicator
        if repo_data.size > 100000:  # 100MB
            monorepo_indicators += 1

        # Multiple languages often indicate monorepo
        if len(repo_data.languages) > 5:
            monorepo_indicators += 1

        # High contributor count
        if repo_data.metrics.unique_contributors > 50:
            monorepo_indicators += 1

        return monorepo_indicators >= 4

    def _is_open_source_project(self, repo_data: RepositoryData) -> bool:
        """Detect open source libraries and tools."""
        os_indicators = 0

        # Has license (important for OS projects)
        if repo_data.has_license:
            os_indicators += 2

        # Community engagement
        if repo_data.stars > 10:
            os_indicators += 2
        if repo_data.forks > 5:
            os_indicators += 1
        if repo_data.metrics.unique_contributors > 3:
            os_indicators += 2

        # Proper documentation
        if repo_data.has_contributing:
            os_indicators += 2
        if repo_data.has_readme and len(repo_data.readme_content or "") > 1500:
            os_indicators += 1

        # Package/library indicators
        library_files = {
            "setup.py",
            "package.json",
            "cargo.toml",
            "pom.xml",
            "build.gradle",
            "composer.json",
            "__init__.py",
        }
        for file_info in repo_data.file_structure:
            if file_info.name.lower() in library_files:
                os_indicators += 2
                break

        # Testing (important for libraries)
        if repo_data.has_tests:
            os_indicators += 1

        # CI/CD (professional setup)
        if repo_data.has_ci_config:
            os_indicators += 1

        return os_indicators >= 5

    def _is_production_project(self, repo_data: RepositoryData) -> bool:
        """Detect production-ready applications."""
        prod_indicators = 0

        # Size and complexity
        if repo_data.size > 5000:  # >5MB
            prod_indicators += 1
        if repo_data.metrics.lines_of_code and repo_data.metrics.lines_of_code > 10000:
            prod_indicators += 2

        # Professional practices
        if repo_data.has_tests:
            prod_indicators += 3  # More weight for tests
        if repo_data.has_ci_config:
            prod_indicators += 2
        if repo_data.metrics.test_coverage_estimate > 0.5:
            prod_indicators += 1

        # Documentation
        if repo_data.has_readme and len(repo_data.readme_content or "") > 2000:
            prod_indicators += 1
        # Check for substantial documentation presence
        doc_presence = repo_data.metrics.documentation_presence
        if doc_presence and "documentation files" in doc_presence:
            # Extract number of doc files from string like "5 documentation files in 20 total files"
            import re

            match = re.search(r"(\d+) documentation files", doc_presence)
            if match and int(match.group(1)) > 3:
                prod_indicators += 1

        # Multiple contributors (team development)
        if repo_data.metrics.unique_contributors > 5:
            prod_indicators += 2

        # Sustained development
        if repo_data.metrics.total_commits > 100:
            prod_indicators += 1
        if repo_data.metrics.commit_frequency > 1:  # >1 commit/week
            prod_indicators += 1

        # Production keywords
        prod_keywords = {
            "api",
            "service",
            "app",
            "application",
            "system",
            "platform",
            "server",
            "backend",
            "frontend",
            "web",
            "mobile",
            "enterprise",
        }
        text_to_check = f"{repo_data.name} {repo_data.description or ''}".lower()
        for keyword in prod_keywords:
            if keyword in text_to_check:
                prod_indicators += 1
                break

        return prod_indicators >= 7

    def _is_experimental_project(self, repo_data: RepositoryData) -> bool:
        """Detect experimental/research projects."""
        exp_indicators = 0

        # Experimental keywords
        exp_keywords = {
            "experiment",
            "prototype",
            "poc",
            "proo",
            "concept",
            "research",
            "study",
            "test",
            "trial",
            "alpha",
            "beta",
            "experimental",
            "playground",
            "sandbox",
            "spike",
            "investigation",
        }

        text_to_check = f"{repo_data.name} {repo_data.description or ''}".lower()
        for keyword in exp_keywords:
            if keyword in text_to_check:
                exp_indicators += 2
                break

        # Low commit count but recent activity
        if (
            repo_data.metrics.total_commits < 50
            and repo_data.metrics.days_since_last_commit < 30
        ):
            exp_indicators += 1

        # Unusual language combinations (data science/research languages)
        research_languages = {"R", "MATLAB", "Jupyter Notebook", "Julia", "Fortran"}
        has_research_languages = any(
            lang in research_languages for lang in repo_data.languages.keys()
        )
        if has_research_languages and len(repo_data.languages) > 3:
            exp_indicators += 2

        # Limited documentation (quick experiments)
        if not repo_data.has_readme or len(repo_data.readme_content or "") < 500:
            exp_indicators += 1

        # No tests (quick prototyping)
        if not repo_data.has_tests:
            exp_indicators += 1

        return exp_indicators >= 3

    def get_classification_stats(
        self, classifications: List[ClassificationResult]
    ) -> Dict[str, Any]:
        """
        Calculate statistics for a batch of classifications.

        Args:
            classifications: List of classification results

        Returns:
            Dictionary with statistics
        """
        if not classifications:
            return {}

        total = len(classifications)
        template_count = sum(
            1 for c in classifications if c.method == AnalysisMethod.TEMPLATE
        )
        ai_count = total - template_count

        total_cost = sum(c.cost_estimate for c in classifications)

        # Template category breakdown
        template_categories: Dict[str, int] = {}
        for c in classifications:
            if c.template_category:
                cat = c.template_category.value
                template_categories[cat] = template_categories.get(cat, 0) + 1

        return {
            "total_repositories": total,
            "template_responses": template_count,
            "ai_analyses": ai_count,
            "template_percentage": round((template_count / total) * 100, 1),
            "ai_percentage": round((ai_count / total) * 100, 1),
            "total_cost_estimate": round(total_cost, 4),
            "average_cost_per_repo": round(total_cost / total, 4),
            "template_categories": template_categories,
        }
