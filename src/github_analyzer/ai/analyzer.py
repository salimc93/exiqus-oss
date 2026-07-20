# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
AI-powered repository analysis module.

This module provides AI-driven analysis of GitHub repositories using
Anthropic's Claude API for complex repositories that require nuanced evaluation.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

import anthropic

from ..core.classifier import RepositoryClassifier
from ..core.confidence_scorer import ConfidenceRiskAssessor
from ..core.context_analyzer import AnalysisContext, ContextAnalyzer
from ..core.evidence.evidence_extractor import EvidenceExtractor
from ..core.report_generator import ReportFormat, ReportGenerator
from ..data.models import RepositoryData
from ..database.models import SubscriptionPlan
from ..utils.config import get_config
from ..utils.logging import get_logger
from .cost_tracker import APIUsage, CostTracker

logger = get_logger(__name__)


@dataclass
class EvidencePattern:
    """Represents a specific evidence pattern found in the repository."""

    pattern: str
    evidence: str
    commits: List[str] = field(default_factory=list)
    files: List[str] = field(default_factory=list)
    strength: str = "moderate"  # weak, moderate, strong


@dataclass
class EvidenceStrength:
    """Evidence strength counts for different competency areas."""

    technical_competence: int = 0  # Evidence count
    communication_skills: int = 0  # Evidence count
    professional_practices: int = 0  # Evidence count
    growth_potential: int = 0  # Evidence count


@dataclass
class ContextAlignment:
    """Context-specific alignment evidence."""

    startup: Dict[str, str] = field(default_factory=dict)
    enterprise: Dict[str, str] = field(default_factory=dict)
    agency: Dict[str, str] = field(default_factory=dict)
    open_source: Dict[str, str] = field(default_factory=dict)


@dataclass
class EvidenceBasedResult:
    """Evidence-based analysis result."""

    evidence_strength: EvidenceStrength
    evidence_patterns: List[EvidencePattern]
    context_alignment: ContextAlignment
    verification_gaps: List[str] = field(default_factory=list)
    anti_patterns: List[str] = field(default_factory=list)
    summary: str = ""
    cost: float = 0.0
    analysis_time: float = 0.0
    generated_by: str = "ai"
    model_used: Optional[str] = None  # Track which model was used for cost analytics


@dataclass
class AnalysisResult:
    """Evidence-based repository analysis result focused on actionable insights."""

    # Core evidence-based fields
    summary: str
    evidence_strength: EvidenceStrength = field(default_factory=EvidenceStrength)
    evidence_patterns: List[EvidencePattern] = field(default_factory=list)
    context_alignment: ContextAlignment = field(default_factory=ContextAlignment)
    verification_gaps: List[str] = field(default_factory=list)
    anti_patterns: List[str] = field(default_factory=list)

    # Actionable insights
    key_insights: List[str] = field(default_factory=list)  # Replaces strengths/concerns
    interview_questions: List[str] = field(default_factory=list)
    areas_to_explore: List[str] = field(
        default_factory=list
    )  # Areas for further investigation

    # Metadata
    cost: float = 0.0
    token_count: int = 0  # Total tokens used (input + output)
    analysis_time: float = 0.0
    generated_by: str = "ai"
    model_used: Optional[str] = None  # Track which model was used for cost analytics

    # Enhanced business logic components
    classification_result: Optional[Any] = None  # ClassificationResult
    contextual_assessment: Optional[Any] = None  # ContextualAssessment
    structured_report: Optional[Any] = None  # StructuredReport
    confidence_scoring: Optional[Any] = (
        None  # ScoringResult from ConfidenceRiskAssessor
    )
    context: Optional[AnalysisContext] = None

    # Analysis quality indicators
    repository_type: Optional[str] = None
    evidence_count: int = 0  # Total number of evidence patterns found
    analysis_depth: str = "standard"  # standard, limited, comprehensive

    # Legacy compatibility fields
    # Removed: trust_score → Using evidence-based approach
    risk_level: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate analysis result after initialization."""
        # Removed: Score validation logic (The Great Purge)
        # Evidence strength now uses counts, not scores
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "summary": self.summary,
            "evidence_strength": (
                {
                    "technical_competence": self.evidence_strength.technical_competence,
                    "communication_skills": self.evidence_strength.communication_skills,
                    "professional_practices": self.evidence_strength.professional_practices,
                    "growth_potential": self.evidence_strength.growth_potential,
                }
                if self.evidence_strength
                else {}
            ),
            "evidence_patterns": [
                {
                    "pattern": p.pattern,
                    "evidence": p.evidence,
                    "commits": p.commits,
                    "files": p.files,
                    "strength": p.strength,
                }
                for p in self.evidence_patterns
            ],
            "context_alignment": (
                {
                    "startup": self.context_alignment.startup,
                    "enterprise": self.context_alignment.enterprise,
                    "agency": self.context_alignment.agency,
                    "open_source": self.context_alignment.open_source,
                }
                if self.context_alignment
                else {}
            ),
            "verification_gaps": self.verification_gaps,
            "anti_patterns": self.anti_patterns,
            "key_insights": self.key_insights,
            "interview_questions": self.interview_questions,
            "areas_to_explore": self.areas_to_explore,
            "cost": self.cost,
            "analysis_time": self.analysis_time,
            "generated_by": self.generated_by,
            "method": "ai",
            # Analysis quality indicators
            "repository_type": self.repository_type,
            "evidence_count": self.evidence_count,
            "analysis_depth": self.analysis_depth,
            "context": self.context.value if self.context else None,
        }

        # Include business logic component data if available
        if self.classification_result:
            result["classification"] = self.classification_result.to_dict()

        if self.contextual_assessment:
            result["contextual_assessment"] = {
                "context": self.contextual_assessment.context.value,
                "strengths": self.contextual_assessment.strengths,
                "concerns": self.contextual_assessment.concerns,
                "recommendations": self.contextual_assessment.recommendations,
                "key_insight": self.contextual_assessment.key_insight,
            }

        if self.structured_report:
            result["structured_report"] = self.structured_report.to_dict()

        if self.confidence_scoring:
            result["confidence_scoring"] = {
                "confidence_level": (
                    self.confidence_scoring.confidence_breakdown.get_confidence_level()
                ),
                "confidence_explanation": (
                    self.confidence_scoring.confidence_breakdown.confidence_explanation
                ),
                "evidence_patterns": (
                    self.confidence_scoring.confidence_breakdown.evidence_patterns
                ),
                "trust_explanation": self.confidence_scoring.trust_explanation,
                "overall_risk_level": self.confidence_scoring.overall_risk_level.value,
                "risk_indicator_count": len(self.confidence_scoring.risk_indicators),
                "analysis_limitations": (
                    self.confidence_scoring.confidence_breakdown.analysis_limitations
                ),
            }

        return result


class AIAnalyzer:
    """
    AI-powered repository analyzer using Anthropic Claude.

    Provides sophisticated analysis for complex repositories that require
    nuanced evaluation beyond simple template responses.
    """

    # Anthropic Claude 3 Haiku pricing (as of 2025)
    HAIKU_INPUT_RATE = 0.25 / 1_000_000  # $0.25 per million input tokens
    HAIKU_OUTPUT_RATE = 1.25 / 1_000_000  # $1.25 per million output tokens

    # Documentation-only language list
    DOCUMENTATION_LANGUAGES = {
        "Markdown",
        "Text",
        "reStructuredText",
        "AsciiDoc",
        "Textile",
        "Org",
        "Pod",
        "RDoc",
        "MediaWiki",
    }

    # Non-code file types that might show up as "languages"
    NON_CODE_LANGUAGES = {
        "JSON",
        "YAML",
        "XML",
        "INI",
        "TOML",
        "CSV",
        "Git Config",
        "GitIgnore",
        "Dockerfile",
        "Makefile",
    }

    def __init__(self) -> None:
        """Initialize AI analyzer with configuration and business logic components."""
        self.config = get_config()
        # CRITICAL FIX: Add timeout to prevent 60s default cutoff
        # This was the root cause of Enterprise tier generating 0 questions!
        self.anthropic_client = anthropic.Anthropic(
            api_key=self.config.anthropic_api_key,
            timeout=300,  # 5 minutes timeout for all AI operations
        )
        self.cost_tracker = CostTracker()

        # Business logic components
        self.classifier = RepositoryClassifier()
        self.context_analyzer = ContextAnalyzer()
        self.report_generator = ReportGenerator(self.config.anthropic_api_key)
        self.confidence_scorer = ConfidenceRiskAssessor()
        self.evidence_extractor = EvidenceExtractor()

        # Analysis configuration
        self.max_context_length = getattr(
            self.config.analysis, "max_context_length", 8000
        )
        self.temperature = getattr(
            self.config.analysis, "ai_temperature", 0.1
        )  # Lowered for deterministic output
        self.model = self.config.analysis.anthropic_model  # Cost-optimized model

    def _has_actual_code(self, repo_data: RepositoryData) -> bool:
        """
        Check if repository contains actual programming code.

        Returns False for documentation-only repos, config collections, etc.
        """
        if not repo_data.languages:
            return False

        # Get all non-documentation languages
        code_languages = {
            lang
            for lang in repo_data.languages
            if lang not in self.DOCUMENTATION_LANGUAGES
            and lang not in self.NON_CODE_LANGUAGES
        }

        # If we have any actual programming language, we have code
        if code_languages:
            # But check if it's significant (more than 10% of the repo)
            total_bytes = sum(repo_data.languages.values())
            code_bytes = sum(
                bytes_count
                for lang, bytes_count in repo_data.languages.items()
                if lang in code_languages
            )
            return (code_bytes / total_bytes) > 0.1 if total_bytes > 0 else False

        return False

    def analyze_repository(
        self,
        repo_data: RepositoryData,
        subscription_plan: Optional[SubscriptionPlan] = None,
    ) -> AnalysisResult:
        """
        Perform AI-powered analysis of repository.

        Args:
            repo_data: Repository data to analyze

        Returns:
            Analysis result with assessment and insights

        Raises:
            Exception: If analysis fails or exceeds budget
        """
        logger.info(f"Starting AI analysis for {repo_data.full_name}")
        start_time = datetime.now(timezone.utc)

        try:
            # Check budget before proceeding
            estimated_cost = self._estimate_cost(repo_data)
            is_within_budget, reason = self.cost_tracker.check_budget(estimated_cost)

            if not is_within_budget:
                raise Exception(f"Analysis would exceed budget: {reason}")

            # Prepare analysis context (no evidence for basic analyze_repository)
            context = self._prepare_context(repo_data, include_evidence=False)

            # Get AI analysis with retry logic
            response_text, input_tokens, output_tokens = (
                self._call_anthropic_api_with_retry(
                    context, subscription_plan=subscription_plan
                )
            )

            # Parse response into structured result
            result = self._parse_response(
                response_text, repo_data, input_tokens, output_tokens, subscription_plan
            )

            # Calculate actual cost and track usage
            analysis_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            result.analysis_time = analysis_time

            # Track API usage with real token counts
            api_usage = APIUsage(
                model=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=result.cost,
                timestamp=datetime.now(timezone.utc),
            )
            self.cost_tracker.track_analysis(api_usage)

            logger.info(
                f"AI analysis completed for {repo_data.full_name} in "
                f"{analysis_time:.2f}s"
            )
            return result

        except Exception as e:
            logger.error(f"AI analysis failed for {repo_data.full_name}: {str(e)}")
            # Re-raise to allow upstream handling of UnparsableAIResponseError
            raise

    def analyze_repository_comprehensive(
        self,
        repo_data: RepositoryData,
        context: Optional[AnalysisContext] = None,
        format_type: ReportFormat = ReportFormat.JSON,
        subscription_plan: Optional[SubscriptionPlan] = None,
        status_callback: Optional[Callable[..., None]] = None,
    ) -> AnalysisResult:
        """
        Perform comprehensive analysis integrating all business logic components.

        This method provides the full MVP analysis experience with:
        - Repository classification and type detection
        - Context-aware analysis for specific hiring scenarios
        - AI-powered insights for complex evaluation
        - Structured report generation with professional formatting
        - Confidence and risk scoring with granular assessment

        Args:
            repo_data: Repository data to analyze
            context: Optional hiring context for context-aware analysis
            format_type: Output format for structured report

        Returns:
            Comprehensive analysis result with all business logic components

        Raises:
            Exception: If analysis fails or exceeds budget
        """
        logger.info(f"Starting comprehensive analysis for {repo_data.full_name}")
        start_time = datetime.now(timezone.utc)

        try:
            # Step 1: Repository Classification
            logger.debug("Running repository classification")
            classification_result = self.classifier.classify(repo_data)

            # Step 2: Determine if AI analysis is needed
            if classification_result.method.value == "ai":
                # Check budget before proceeding with AI
                estimated_cost = self._estimate_cost(repo_data)
                is_within_budget, reason = self.cost_tracker.check_budget(
                    estimated_cost
                )

                if not is_within_budget:
                    raise Exception(f"AI analysis would exceed budget: {reason}")

                # Get AI insights for complex repositories
                logger.debug("Running AI analysis for complex repository")
                # Include evidence for Professional/Enterprise tiers
                include_evidence = bool(
                    subscription_plan
                    and subscription_plan
                    in [SubscriptionPlan.PROFESSIONAL, SubscriptionPlan.ENTERPRISE]
                )
                ai_context = self._prepare_context(
                    repo_data, include_evidence=include_evidence
                )
                # Get repository type from classification
                repo_type = (
                    str(classification_result.repository_type)
                    if classification_result.repository_type
                    else None
                )

                ai_response_text, ai_input_tokens, ai_output_tokens = (
                    self._call_anthropic_api_with_retry(
                        ai_context,
                        analysis_context=context,
                        subscription_plan=subscription_plan,
                        repository_type=repo_type,
                    )
                )
                ai_result = self._parse_response(
                    ai_response_text, repo_data, ai_input_tokens, ai_output_tokens
                )

                # Track AI usage with real token counts
                ai_api_usage = APIUsage(
                    model=self.model,
                    input_tokens=ai_input_tokens,
                    output_tokens=ai_output_tokens,
                    cost=ai_result.cost,
                    timestamp=datetime.now(timezone.utc),
                )
                self.cost_tracker.track_analysis(ai_api_usage)
            else:
                # Use template-based analysis for simpler cases
                logger.debug("Using template-based analysis")
                ai_result = self._generate_template_result(
                    repo_data, classification_result
                )

            # Step 3: Context-Aware Analysis (if context provided)
            contextual_assessment = None
            if context:
                logger.debug(f"Running context-aware analysis for {context.value}")
                contextual_assessment = self.context_analyzer.analyze(
                    repo_data, context
                )

            # Step 4: Confidence and Risk Scoring
            logger.debug("Assessing confidence and risk (evidence-based)")
            confidence_scoring = self.confidence_scorer.assess_confidence_and_risk(
                repo_data, classification_result, contextual_assessment
            )

            # Step 5: Generate Structured Report
            logger.debug("Generating structured report")
            structured_report = self.report_generator.generate_report(
                repo_data,
                classification_result,
                contextual_assessment,
                context,
                confidence_scoring,
                ai_analysis=ai_result,  # Always pass ai_result if available
                subscription_plan=subscription_plan,
                status_callback=status_callback,  # Pass status callback for retry notifications
            )

            # Step 6: Create Comprehensive Result
            analysis_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            # Build comprehensive result using evidence-based approach
            result = AnalysisResult(
                summary=structured_report.executive_summary or ai_result.summary,
                evidence_strength=ai_result.evidence_strength,
                evidence_patterns=ai_result.evidence_patterns,
                context_alignment=ai_result.context_alignment,
                verification_gaps=ai_result.verification_gaps,
                anti_patterns=ai_result.anti_patterns,
                key_insights=ai_result.key_insights,
                interview_questions=getattr(ai_result, "interview_questions", []),
                areas_to_explore=getattr(ai_result, "areas_to_explore", []),
                cost=(
                    ai_result.cost
                    if classification_result.method.value == "ai"
                    else 0.0
                ),
                analysis_time=analysis_time,
                generated_by="comprehensive",
                # Business logic components
                classification_result=classification_result,
                contextual_assessment=contextual_assessment,
                structured_report=structured_report,
                confidence_scoring=confidence_scoring,
                context=context,
                # Legacy compatibility
                repository_type=(
                    classification_result.repository_type.value
                    if classification_result.repository_type
                    else None
                ),
                # Removed: trust_score (Evidence-based approach)
                risk_level=confidence_scoring.overall_risk_level.value,
            )

            logger.info(
                f"Comprehensive analysis completed for {repo_data.full_name} in "
                f"{analysis_time:.2f}s (method: {classification_result.method.value})"
            )

            return result

        except Exception as e:
            logger.error(
                f"Comprehensive analysis failed for {repo_data.full_name}: {str(e)}"
            )
            # Re-raise to allow upstream handling of UnparsableAIResponseError
            raise

    def _generate_template_result(
        self, repo_data: RepositoryData, classification_result: Any
    ) -> AnalysisResult:
        """Generate template-based analysis result for simple cases."""
        if classification_result.template_category:
            category = classification_result.template_category.value

            # Special handling for monorepos
            if (
                hasattr(classification_result, "repository_type")
                and classification_result.repository_type == "MONOREPO"
            ):
                return self._generate_monorepo_template(repo_data)

            if category in ["inactive", "abandoned", "empty", "minimal"]:
                evidence_strength = EvidenceStrength(
                    technical_competence=20,
                    communication_skills=15,
                    professional_practices=10,
                    growth_potential=10,
                )
                summary = (
                    "Repository shows insufficient development activity for assessment"
                )
                evidence_patterns = [
                    EvidencePattern(
                        pattern="minimal_activity",
                        evidence=(
                            f"Repository has only {repo_data.metrics.total_commits} commits "
                            f"and was last updated {repo_data.metrics.days_since_last_commit} days ago"
                        ),
                        commits=[],
                        files=[],
                        strength="weak",
                    )
                ]
                verification_gaps = [
                    "Minimal development history",
                    "Insufficient evidence of technical skills",
                ]
            elif category == "poor_practices":
                evidence_strength = EvidenceStrength(
                    technical_competence=35,
                    communication_skills=30,
                    professional_practices=25,
                    growth_potential=30,
                )
                summary = "Repository demonstrates poor development practices"
                evidence_patterns = [
                    EvidencePattern(
                        pattern="poor_practices",
                        evidence="Repository lacks tests, documentation, and professional development standards",
                        commits=[],
                        files=[],
                        strength="weak",
                    )
                ]
                verification_gaps = [
                    "Poor coding practices evident",
                    "Lacks professional development standards",
                ]
            elif category == "learning":
                evidence_strength = EvidenceStrength(
                    technical_competence=40,
                    communication_skills=35,
                    professional_practices=30,
                    growth_potential=50,
                )
                summary = "Repository appears to be learning/educational project"
                evidence_patterns = [
                    EvidencePattern(
                        pattern="learning_project",
                        evidence="Repository appears to be educational with learning-focused content",
                        commits=[],
                        files=[],
                        strength="moderate",
                    )
                ]
                verification_gaps = [
                    "Limited production experience",
                    "Educational project scope",
                ]
            else:
                evidence_strength = EvidenceStrength(
                    technical_competence=45,
                    communication_skills=40,
                    professional_practices=40,
                    growth_potential=45,
                )
                summary = "Repository requires deeper evaluation"
                evidence_patterns = [
                    EvidencePattern(
                        pattern="needs_evaluation",
                        evidence="Repository has activity but requires deeper analysis",
                        commits=[],
                        files=[],
                        strength="moderate",
                    )
                ]
                verification_gaps = ["Limited automated assessment possible"]
        else:
            evidence_strength = EvidenceStrength(
                technical_competence=40,
                communication_skills=35,
                professional_practices=35,
                growth_potential=40,
            )
            summary = "Repository classified for AI analysis but template fallback used"
            evidence_patterns = [
                EvidencePattern(
                    pattern="classification_uncertainty",
                    evidence="Complex project requiring deeper evaluation",
                    commits=[],
                    files=[],
                    strength="moderate",
                )
            ]
            verification_gaps = ["Classification uncertainty"]

        return AnalysisResult(
            summary=summary,
            evidence_strength=evidence_strength,
            evidence_patterns=evidence_patterns,
            context_alignment=ContextAlignment(),
            verification_gaps=verification_gaps,
            anti_patterns=[],
            cost=0.0,
            generated_by="template",
        )

    def _generate_monorepo_template(self, repo_data: RepositoryData) -> AnalysisResult:
        """Generate specialized template for monorepo analysis."""
        # Extract observable facts from sampled data
        languages_str = ", ".join(list(repo_data.languages.keys())[:5])
        if len(repo_data.languages) > 5:
            languages_str += f" (+{len(repo_data.languages) - 5} more)"

        # Identify architecture patterns from directory structure
        top_dirs = [
            f.name
            for f in repo_data.file_structure
            if f.type == "dir" and "/" not in f.path
        ][:10]

        # Build summary based on observable patterns only
        summary = (
            f"Monorepo analysis based on sampled data. "
            f"Repository structure: {len(top_dirs)} top-level directories including {', '.join(top_dirs[:3])}. "
            f"Languages detected: {languages_str}. "
            f"Contributors: {repo_data.metrics.unique_contributors}. "
            f"Note: Analysis performed on representative sample due to repository size."
        )

        # Create evidence patterns from actual data
        evidence_patterns = []

        # Structural evidence
        if top_dirs:
            evidence_patterns.append(
                EvidencePattern(
                    pattern="repository_structure",
                    evidence=f"Found {len(top_dirs)} top-level directories: {', '.join(top_dirs[:5])}",
                    commits=[],
                    files=[
                        f.path
                        for f in repo_data.file_structure
                        if f.type == "dir" and "/" not in f.path
                    ][:5],
                    strength="observed",
                )
            )

        # Language diversity
        if repo_data.languages:
            evidence_patterns.append(
                EvidencePattern(
                    pattern="technology_stack",
                    evidence=f"Repository uses {len(repo_data.languages)} programming languages",
                    commits=[],
                    files=[],
                    strength="observed",
                )
            )

        # Infrastructure patterns
        if repo_data.has_ci_config:
            evidence_patterns.append(
                EvidencePattern(
                    pattern="automation",
                    evidence="CI/CD configuration files detected",
                    commits=[],
                    files=[
                        f.path
                        for f in repo_data.file_structure
                        if f.is_config and "ci" in f.path.lower()
                    ][:3],
                    strength="observed",
                )
            )

        if repo_data.has_tests:
            test_dirs = [
                f.path
                for f in repo_data.file_structure
                if f.type == "dir" and "test" in f.path.lower()
            ][:5]
            evidence_patterns.append(
                EvidencePattern(
                    pattern="testing",
                    evidence=f"Test directories found: {', '.join(test_dirs) if test_dirs else 'test files detected'}",
                    commits=[],
                    files=test_dirs,
                    strength="observed",
                )
            )

        # Let the AI determine all assessments based on these patterns
        # No pre-set numerical ratings or competence levels

        verification_gaps = [
            "Full repository structure analysis limited by sampling",
            "Individual service architectures not deeply analyzed",
            "Cross-service dependencies require manual investigation",
            "Contribution patterns across services need detailed review",
        ]

        return AnalysisResult(
            summary=summary,
            evidence_strength=EvidenceStrength(),  # Default instance
            evidence_patterns=evidence_patterns,
            context_alignment=ContextAlignment(),  # Default instance
            verification_gaps=verification_gaps,
            anti_patterns=[],
            cost=0.0,
            token_count=0,  # Template-based, no tokens used
            generated_by="template",
        )

    def _prepare_context(
        self, repo_data: RepositoryData, include_evidence: bool = False
    ) -> str:
        """
        Prepare repository context for AI analysis.

        Args:
            repo_data: Repository data
            include_evidence: Whether to include evidence data for Professional/Enterprise tiers

        Returns:
            Formatted context string within token limits
        """
        context_parts = []

        # Basic repository information
        context_parts.extend(
            [
                f"Repository: {repo_data.full_name}",
                f"Description: {repo_data.description or 'No description'}",
                f"Owner: {repo_data.owner}",
                f"Created: {repo_data.created_at.strftime('%Y-%m-%d')}",
                f"Last Updated: {repo_data.updated_at.strftime('%Y-%m-%d')}",
                "",
            ]
        )

        # Repository metrics
        context_parts.extend(
            [
                "Repository Metrics:",
                f"  Size: {repo_data.size}KB",
                f"  Stars: {repo_data.stars}",
                f"  Forks: {repo_data.forks}",
                f"  Open Issues: {repo_data.open_issues}",
                f"  Total Commits: {repo_data.metrics.total_commits}",
                f"  Unique Contributors: {repo_data.metrics.unique_contributors}",
                f"  Days Since Last Commit: {repo_data.metrics.days_since_last_commit}",
                f"  Commit Frequency: {repo_data.metrics.commit_frequency:.2f} "
                "commits/week",
                f"  Average Commit Size: {repo_data.metrics.avg_commit_size:.1f} lines",
                "",
            ]
        )

        # Languages
        has_code = self._has_actual_code(repo_data)

        # Add explicit warning for documentation-only repos
        if not has_code:
            context_parts.extend(
                [
                    "⚠️ DOCUMENTATION-ONLY REPOSITORY ⚠️",
                    "This repository contains NO actual programming code.",
                    "DO NOT generate technical insights or code quality assessments.",
                    "",
                ]
            )

        if repo_data.languages:
            total_bytes = sum(repo_data.languages.values())
            lang_percentages = {
                lang: (bytes_count / total_bytes) * 100
                for lang, bytes_count in repo_data.languages.items()
            }
            sorted_langs = sorted(
                lang_percentages.items(), key=lambda x: x[1], reverse=True
            )

            context_parts.append("Languages:")
            for lang, percentage in sorted_langs[:5]:  # Top 5 languages
                context_parts.append(f"  {lang}: {percentage:.1f}%")
            context_parts.append("")

        # Repository structure indicators
        context_parts.extend(
            [
                "Repository Structure:",
                f"  Has README: {repo_data.has_readme}",
                f"  Has License: {repo_data.has_license}",
                f"  Has Tests: {repo_data.has_tests}",
                f"  Has CI/CD Config: {repo_data.has_ci_config}",
                f"  Has Contributing Guide: {repo_data.has_contributing}",
                "",
            ]
        )

        # Quality indicators
        context_parts.extend(
            [
                "Quality Indicators:",
                "  Test Coverage Estimate: "
                f"{repo_data.metrics.test_coverage_estimate:.1%}",
                f"  Documentation Presence: {repo_data.metrics.documentation_presence}",
                f"  Lines of Code: {repo_data.metrics.lines_of_code or 'Unknown'}",
                "",
            ]
        )

        # Repository status
        status_info = []
        if repo_data.is_fork:
            status_info.append("Fork")
        if repo_data.is_archived:
            status_info.append("Archived")
        if repo_data.is_private:
            status_info.append("Private")
        if status_info:
            context_parts.append(f"Status: {', '.join(status_info)}")
            context_parts.append("")

        # Topics/tags
        if repo_data.topics:
            context_parts.append(f"Topics: {', '.join(repo_data.topics[:10])}")
            context_parts.append("")

        # Recent activity
        if repo_data.recent_commits:
            context_parts.append("Recent Commits:")
            for commit in repo_data.recent_commits[:3]:  # Last 3 commits
                context_parts.append(
                    f"  {commit.date.strftime('%Y-%m-%d')}: {commit.message[:100]}"
                )
            context_parts.append("")

        # README content (truncated if necessary)
        if repo_data.readme_content:
            readme = repo_data.readme_content.strip()
            if len(readme) > 1500:
                readme = readme[:1500] + "..."
            context_parts.extend(["README Content:", readme, ""])

        # Add evidence data for Professional/Enterprise tiers
        if include_evidence:
            try:
                evidence = self.evidence_extractor.extract_all_evidence(repo_data)

                # Add key evidence summary
                context_parts.append("Evidence-Based Insights:")

                # Technical patterns
                if evidence.get("technical_patterns"):
                    context_parts.append("\nTechnical Patterns:")
                    for pattern in evidence["technical_patterns"][:5]:  # Top 5
                        context_parts.append(f"  - {pattern.get('finding', '')}")

                # Behavioral analysis
                if evidence.get("behavioral_analysis"):
                    behavioral = evidence["behavioral_analysis"]
                    context_parts.append(
                        f"\nWork Style: {behavioral.get('work_style', 'Unknown')}"
                    )
                    context_parts.append(
                        f"Collaboration Level: {behavioral.get('collaboration_level', 'Unknown')}"
                    )

                # Skill evolution
                if evidence.get("skill_evolution"):
                    evolution = evidence["skill_evolution"]
                    context_parts.append(
                        f"\nDevelopment Trajectory: {evolution.get('development_trajectory', 'Unknown')}"
                    )
                    context_parts.append(
                        f"Growth Rate: {evolution.get('growth_rate', 0):.2f}"
                    )

                # Security issues
                if evidence.get("security_issues"):
                    context_parts.append(
                        f"\nSecurity Concerns: {len(evidence['security_issues'])} found"
                    )

                context_parts.append("")
            except Exception as e:
                logger.warning(f"Failed to extract evidence for AI context: {e}")
                # Continue without evidence

        # Join all parts
        context = "\n".join(context_parts)

        # Ensure context stays within limits (rough token estimation: 1 token ≈ 4 chars)
        max_chars = self.max_context_length * 4
        if len(context) > max_chars:
            context = (
                context[:max_chars] + "\n\n[Context truncated to fit token limits]"
            )

        return context

    def _call_anthropic_api_with_retry(
        self,
        context: str,
        analysis_context: Optional[AnalysisContext] = None,
        subscription_plan: Optional[SubscriptionPlan] = None,
        repository_type: Optional[str] = None,
        max_retries: int = 2,
    ) -> tuple[str, int, int]:
        """
        Phase 3 of Operation Containment Field: Call Anthropic API with retry logic for JSON correction.

        If the initial response fails JSON parsing, retry with explicit correction instructions.

        Args:
            context: Repository context string
            analysis_context: Optional analysis context for specialized prompts
            subscription_plan: Optional subscription plan for tier-specific prompts
            repository_type: Optional repository type for specialized prompts
            max_retries: Maximum number of retries for JSON correction (default: 2)

        Returns:
            Tuple of (AI response text, input_tokens, output_tokens)

        Raises:
            UnparsableAIResponseError: When all retry attempts fail to produce valid JSON
        """
        from .exceptions import UnparsableAIResponseError
        from .hardened_json_parser import create_hardened_parser

        total_input_tokens = 0
        total_output_tokens = 0
        last_error = None
        last_response = ""

        for attempt in range(max_retries + 1):
            if attempt == 0:
                # First attempt with normal prompt
                response_text, input_tokens, output_tokens = self._call_anthropic_api(
                    context, analysis_context, subscription_plan, repository_type
                )
            else:
                # Retry with correction prompt
                logger.warning(
                    f"Retry attempt {attempt} with JSON correction instructions"
                )
                response_text, input_tokens, output_tokens = (
                    self._call_anthropic_api_with_correction(
                        context,
                        analysis_context,
                        subscription_plan,
                        repository_type,
                        last_error or "Invalid JSON format",
                        last_response,
                    )
                )

            total_input_tokens += input_tokens
            total_output_tokens += output_tokens
            last_response = response_text

            # Test if response is valid JSON using HardenedJSONParser
            parser = create_hardened_parser()
            expected_keys = [
                "summary",
                "observed_patterns",
                "limitations",
                "context_notes",
                "upgrade_benefit",
            ]
            parsed_data, error_message = parser.parse(response_text, expected_keys)

            if parsed_data:
                logger.info(f"Valid JSON obtained on attempt {attempt + 1}")
                return response_text, total_input_tokens, total_output_tokens
            else:
                last_error = error_message
                logger.error(f"Attempt {attempt + 1} failed: {error_message}")

        # All retries exhausted - raise exception to prevent poison from entering the system
        error_msg = f"Failed to obtain valid JSON after {max_retries + 1} attempts. Last error: {last_error}"
        logger.error(error_msg)
        raise UnparsableAIResponseError(
            message=error_msg,
            last_response=last_response[
                :1000
            ],  # Include first 1000 chars for debugging
            attempts=max_retries + 1,
        )

    def _call_anthropic_api_with_correction(
        self,
        context: str,
        analysis_context: Optional[AnalysisContext],
        subscription_plan: Optional[SubscriptionPlan],
        repository_type: Optional[str],
        error_message: str,
        previous_response: str,
    ) -> tuple[str, int, int]:
        """
        Call Anthropic API with JSON correction instructions.

        This is Phase 3 of Operation Containment Field - demanding corrected JSON.
        """
        # Create correction prompt
        correction_prompt = f"""
CRITICAL ERROR: Your previous response contained invalid JSON that could not be parsed.

Error details: {error_message}

Your previous response (first 500 chars):
{previous_response[:500]}...

YOU MUST provide a response with VALID JSON ONLY. No explanatory text, no markdown, ONLY the JSON object.

The JSON MUST match this exact structure:
{{
    "summary": "string",
    "observed_patterns": [array of pattern objects],
    "limitations": [array of strings],
    "context_notes": "string",
    "upgrade_benefit": "string"
}}

Now provide the CORRECTED JSON response for the repository analysis:

{context}
"""

        # Use same model and token settings
        from ..core.tier_config import TIER_CONFIGURATIONS, get_model_for_tier

        if subscription_plan:
            model_to_use = get_model_for_tier(
                subscription_plan.value.lower()
            )  # Simplified
            tier_config = TIER_CONFIGURATIONS.get(subscription_plan.value.lower())
            max_tokens = (
                tier_config.main_generation_tokens
                if tier_config
                else self.config.analysis.max_tokens
            )
        else:
            model_to_use = self.model
            max_tokens = self.config.analysis.max_tokens

        # Call API with correction prompt
        response = self.anthropic_client.messages.create(
            model=model_to_use,
            max_tokens=max_tokens,
            temperature=0.1,  # Lower temperature for more deterministic JSON
            messages=[{"role": "user", "content": correction_prompt}],
        )

        # Extract token usage
        input_tokens = response.usage.input_tokens if hasattr(response, "usage") else 0
        output_tokens = (
            response.usage.output_tokens if hasattr(response, "usage") else 0
        )

        # Extract text content
        content_block = response.content[0]
        if hasattr(content_block, "text"):
            response_text = str(content_block.text)
        else:
            response_text = str(content_block)

        return response_text, input_tokens, output_tokens

    def _call_anthropic_api(
        self,
        context: str,
        analysis_context: Optional[AnalysisContext] = None,
        subscription_plan: Optional[SubscriptionPlan] = None,
        repository_type: Optional[str] = None,
    ) -> tuple[str, int, int]:
        """
        Call Anthropic API with repository context.

        Args:
            context: Repository context string
            analysis_context: Optional analysis context for specialized prompts
            subscription_plan: Optional subscription plan for tier-specific prompts
            repository_type: Optional repository type for specialized prompts

        Returns:
            Tuple of (AI response text, input_tokens, output_tokens)
        """

        # Import context prompt enhancer and evidence-based prompts
        from ..core.evidence.context_prompts import ContextPromptEnhancer
        from .evidence_based_prompts import (
            BASIC_MONOREPO_ANALYSIS_PROMPT,
            EVIDENCE_BASED_ANALYSIS_PROMPT,
            MONOREPO_ANALYSIS_PROMPT,
            get_tier_specific_analysis_prompt,
        )

        # Get context-specific instructions if provided
        context_instruction = ""
        if analysis_context:
            context_instruction = ContextPromptEnhancer.get_context_prompt(
                analysis_context.value, {}
            )

        # Select appropriate prompt based on repository type and tier
        if repository_type == "MONOREPO":
            if subscription_plan == SubscriptionPlan.BASIC:
                prompt = BASIC_MONOREPO_ANALYSIS_PROMPT.format(context=context)
            elif subscription_plan in [
                SubscriptionPlan.PROFESSIONAL,
                SubscriptionPlan.ENTERPRISE,
            ]:
                prompt = MONOREPO_ANALYSIS_PROMPT.format(context=context)
            else:
                # Default to basic monorepo prompt for free tier (shouldn't happen)
                prompt = BASIC_MONOREPO_ANALYSIS_PROMPT.format(context=context)
        else:
            # Get tier-specific prompt for regular repositories
            if subscription_plan:
                tier_prompt = get_tier_specific_analysis_prompt(
                    subscription_plan.value.lower()
                )
                if tier_prompt:
                    prompt = tier_prompt.format(
                        context_instruction=context_instruction, context=context
                    )
                else:
                    # Fallback to standard prompt
                    prompt = EVIDENCE_BASED_ANALYSIS_PROMPT.format(
                        context_instruction=context_instruction, context=context
                    )
            else:
                # Default evidence-based prompt
                prompt = EVIDENCE_BASED_ANALYSIS_PROMPT.format(
                    context_instruction=context_instruction, context=context
                )

        # Select model based on subscription plan
        from ..core.tier_config import TIER_CONFIGURATIONS, get_model_for_tier

        if subscription_plan:
            model_to_use = get_model_for_tier(
                subscription_plan.value.lower()
            )  # Simplified: single model per tier
            # Get tier-specific token limit
            tier_config = TIER_CONFIGURATIONS.get(subscription_plan.value.lower())
            max_tokens = (
                tier_config.main_generation_tokens
                if tier_config
                else self.config.analysis.max_tokens
            )
        else:
            model_to_use = self.model  # Fallback to config model
            max_tokens = self.config.analysis.max_tokens

        # Call Anthropic API
        logger.info(
            f"Calling Anthropic API with model={model_to_use}, max_tokens={max_tokens}"
        )
        response = self.anthropic_client.messages.create(
            model=model_to_use,
            max_tokens=max_tokens,
            temperature=self.temperature,
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract token usage from response
        input_tokens = response.usage.input_tokens if hasattr(response, "usage") else 0
        output_tokens = (
            response.usage.output_tokens if hasattr(response, "usage") else 0
        )

        # Extract text content from response
        content_block = response.content[0]
        if hasattr(content_block, "text"):
            response_text = str(content_block.text)
        else:
            response_text = str(content_block)

        return response_text, input_tokens, output_tokens

    def _parse_markdown_patterns(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Parse Markdown response for observed patterns (Scale+ tier).

        Args:
            response: Markdown formatted response

        Returns:
            Dictionary with parsed data or None if parsing fails
        """
        import re

        result: Dict[str, Any] = {
            "summary": "",
            "observed_patterns": [],
            "limitations": [],
            "context_notes": "",
            "upgrade_benefit": "",
        }

        try:
            # Parse Summary
            summary_match = re.search(
                r"# Summary\s*\n(.*?)(?=\n#|\Z)", response, re.DOTALL
            )
            if summary_match:
                result["summary"] = summary_match.group(1).strip()

            # Parse Observed Patterns
            patterns_section = re.search(
                r"# Observed Patterns\s*\n(.*?)(?=\n# [A-Z]|\Z)", response, re.DOTALL
            )
            if patterns_section:
                pattern_blocks = re.findall(
                    r"## Pattern \d+\s*\n(.*?)(?=## Pattern \d+|# [A-Z]|\Z)",
                    patterns_section.group(1),
                    re.DOTALL,
                )

                for block in pattern_blocks:
                    pattern_data = {}

                    # Extract pattern fields
                    pattern_match = re.search(
                        r"\*\*Pattern:\*\*\s*(.*?)(?:\n|$)", block
                    )
                    if pattern_match:
                        pattern_data["pattern"] = pattern_match.group(1).strip()

                    evidence_match = re.search(
                        r"\*\*Evidence:\*\*\s*(.*?)(?=\*\*Files:|\*\*Relevance:|\n|$)",
                        block,
                        re.DOTALL,
                    )
                    if evidence_match:
                        pattern_data["evidence"] = evidence_match.group(1).strip()

                    files_match = re.search(
                        r"\*\*Files:\*\*\s*(.*?)(?=\*\*Relevance:|\n|$)", block
                    )
                    if files_match:
                        files_text = files_match.group(1).strip()
                        if (
                            files_text.lower() == "none"
                            or files_text.lower() == "repository-wide"
                        ):
                            pattern_data["files"] = []
                        else:
                            pattern_data["files"] = [
                                f.strip() for f in files_text.split(",")
                            ]

                    relevance_match = re.search(
                        r"\*\*Relevance:\*\*\s*(.*?)(?:\n|$)", block
                    )
                    if relevance_match:
                        pattern_data["relevance"] = relevance_match.group(1).strip()

                    if pattern_data:
                        result["observed_patterns"].append(pattern_data)

            # Parse Limitations
            limitations_section = re.search(
                r"# Limitations\s*\n(.*?)(?=\n# [A-Z]|\Z)", response, re.DOTALL
            )
            if limitations_section:
                limitations = re.findall(
                    r"^-\s*(.*?)$", limitations_section.group(1), re.MULTILINE
                )
                result["limitations"] = limitations

            # Parse Context Notes
            context_section = re.search(
                r"# Context Notes\s*\n(.*?)(?=\n# [A-Z]|\Z)", response, re.DOTALL
            )
            if context_section:
                result["context_notes"] = context_section.group(1).strip()

            # Parse Upgrade Benefit
            upgrade_section = re.search(
                r"# (?:Upgrade Benefit|Tier Benefit)\s*\n(.*?)(?=\n#|\Z)",
                response,
                re.DOTALL,
            )
            if upgrade_section:
                result["upgrade_benefit"] = upgrade_section.group(1).strip()

            return result

        except Exception as e:
            logger.error(f"Failed to parse Markdown patterns: {e}")
            return None

    def _sanitize_hobby_project_judgments(self, text_items: List[str]) -> List[str]:
        """
        Remove harsh judgments about hobby/learning projects from insights and areas_to_explore.

        Filters out:
        - Psychology inferences (frustrated, fatigue, under pressure, challenges with)
        - Speculation (may indicate, suggests, declining quality, degradation)
        - Project abandonment or commitment issues
        - Missing README/documentation in personal projects
        - Informal commit messages
        - Missing CI/CD in hobby code
        - Lack of stars/forks/community engagement
        """
        import re

        FORBIDDEN_PATTERNS = [
            # Psychology and mental state inferences (FORBIDDEN - cannot read minds)
            r"\bfrustrated?\b",
            r"\bfatigue\b",
            r"\bunder\s+pressure\b",
            r"\bchallenges?\s+with\b",
            r"\bmay\s+indicate\b",
            r"\bsuggests?\b.*\b(frustration|fatigue|pressure|stress|overwhelmed)\b",
            r"\bindicates?\b.*\b(frustration|fatigue|pressure|stress|overwhelmed)\b",
            r"\bdeclining\s+quality\b",
            r"\bdegradation\b",
            r"\bintellectual\s+property.*\bgap\b",
            r"\bdeficiency\b",
            r"\bdeficiencies\b",
            r"\bdormancy\b",
            r"\bextended.*\bdormancy\b",
            # Speculation and subjective judgments (NEW - catch "suggests need for")
            r"\bsuggests?\s+need\s+for\b",
            r"\bthis\s+suggests\b",
            r"\bthis\s+indicates\b",
            r"\bmay\s+not\s+align\s+with\b",
            r"\bshows?\s+commitment\b",
            r"\bdemonstrat(es|ing)\s+(informal|casual|non-professional)\b",
            r"\binconsistent.*\b(communication|standards|practices)\b",
            r"\bvariability\s+in.*\b(communication|practices)\b",
            r"\bcontrasts?\s+(sharply\s+)?with.*\b(professional|standards)\b",
            r"\bunder\s+different\s+circumstances\b",
            # Negative judgment words about hobby projects
            r"\bgap\b.*\b(in|represents|indicates)\b",
            r"\babsence\b.*\b(of|represents|suggests)\b",
            r"\bweakness(es)?\b.*\b(in|represents)\b",
            r"\bconcerning\b.*\b(pattern|lack|absence)\b",
            r"\bcomplete\s+absence\s+of.*documentation\b",
            r"\bdocumentation\s+strategy\s+absence\b",
            # Abandonment and commitment inferences
            r"^Project appears abandoned$",  # Exact match for areas_to_explore items
            r"^Missing README documentation$",  # Exact match for areas_to_explore items
            r"\babandon(ment|ed)?.*\bpattern\b",
            r"\bproject\s+(abandon(ment|ed)?|appears\s+abandoned)\b",
            r"\bappears\s+abandoned\b",  # Simpler catch-all
            r"\bdifficultly?\s+maintaining.*\bcommitment\b",
            r"\bfollow[_\s-]?through\s+(problem|issue|difficult)\b",
            r"\bcommitment\s+(issue|problem|difficult|concern)\b",
            r"\blong[_\s-]?term\s+commitment\b",
            # Documentation judgments on personal projects
            r"^Documentation and Communication Gap",  # Exact title match
            r"^Legal and Licensing Oversight",  # Exact title match
            r"\bdocumentation.*\bgap\b",  # Any "documentation gap" phrase
            r"\bcommunication.*\bgap\b",  # Any "communication gap" phrase
            r"\blegal.*licensing.*oversight\b",
            r"\babsence.*license.*file\b",
            r"\bintellectual\s+property.*unclear\b",
            r"(missing|absence\s+of|lack\s+of)\s+README.*communication.*deficien",
            r"README.*communication.*weakness",
            r"documentation.*critical\s+for\s+team",
            r"documentation.*strategy.*deficien",
            r"documentation.*\bgap\b.*knowledge\s+sharing",
            r"knowledge\s+sharing.*capabilit",
            r"\blimits\s+project\s+accessibility\b",
            r"\bmaintainability\s+for\s+team\s+environments\b",
            r"\bcomplete\s+absence.*documentation\b",
            r"\bpotential\s+gap\s+in\s+knowledge\s+sharing\b",
            # Commit message judgments (professionalism - EXPANDED)
            r"\bcryptic\s+commit\b",
            r"\binformal.*communication\s+(style|practice|patterns?)\b",
            r"\bcasual.*non-professional.*communication\b",
            r"\bprofessional\s+communication\s+skill\s+development\b",
            r"\bfrustration\s+management\b",
            r"\bunprofessional.*\bcommit\b",
            r"\b(idek|wip|stuff).*\b(suggests|reveals|indicates|demonstrat)\b",
            r"\bcommunication.*\bdiscipline.*\bdegradation\b",
            r"\bcasual.*\bapproach.*\b(version\s+control|communication)\b",
            r"\binformal\s+messaging\s+approach\b",
            # CI/CD judgments on hobby projects
            r"\babsence\s+of\s+CI/CD.*\bgap\b",
            r"\bno\s+CI/CD.*DevOps\s+culture\b",
            r"\bmissing.*automation.*\bgap\b",
            r"\bmanual.*quality.*assurance.*process\b",
            r"\breliance.*manual.*(testing|processes)\b",
            # Community engagement judgments
            r"\bno\s+community\s+engagement.*despite\b",
            r"\black.*stars.*forks.*suggests\b",
        ]

        sanitized = []
        violations_count = 0

        for item in text_items:
            if not isinstance(item, str):
                sanitized.append(item)
                continue

            should_filter = False
            for pattern in FORBIDDEN_PATTERNS:
                if re.search(pattern, item, re.IGNORECASE):
                    should_filter = True
                    violations_count += 1
                    logger.critical(
                        f"🚨 AI VIOLATION DETECTED! Harsh hobby project judgment filtered: "
                        f"Pattern '{pattern}' found in: {item[:100]}..."
                    )
                    break

            if not should_filter:
                sanitized.append(item)

        if violations_count > 0:
            logger.critical(
                f"HOBBY PROJECT SANITIZATION ACTIVATED! "
                f"Filtered {violations_count} harsh judgments about personal projects"
            )

        return sanitized

    def _sanitize_insight_objects(
        self, insights: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Sanitize insight objects by filtering harsh titles and descriptions.

        Filters out:
        - Psychology inferences (frustrated, fatigue, under pressure, challenges with)
        - Speculation (may indicate, suggests, declining quality, degradation)
        - Project abandonment or commitment issues
        - Documentation/CI/CD judgments on hobby projects
        - Commit message quality judgments
        """
        import re

        FORBIDDEN_PATTERNS = [
            # Psychology and mental state inferences (FORBIDDEN - cannot read minds)
            r"\bfrustrated?\b",
            r"\bfatigue\b",
            r"\bunder\s+pressure\b",
            r"\bchallenges?\s+with\b",
            r"\bmay\s+indicate\b",
            r"\bsuggests?\b.*\b(frustration|fatigue|pressure|stress|overwhelmed)\b",
            r"\bindicates?\b.*\b(frustration|fatigue|pressure|stress|overwhelmed)\b",
            r"\bdeclining\s+quality\b",
            r"\bdegradation\b",
            r"\bintellectual\s+property.*\bgap\b",
            r"\bdeficiency\b",
            r"\bdeficiencies\b",
            r"\bdormancy\b",
            r"\bextended.*\bdormancy\b",
            # Speculation and subjective judgments (NEW - catch "suggests need for")
            r"\bsuggests?\s+need\s+for\b",
            r"\bthis\s+suggests\b",
            r"\bthis\s+indicates\b",
            r"\bmay\s+not\s+align\s+with\b",
            r"\bshows?\s+commitment\b",
            r"\bdemonstrat(es|ing)\s+(informal|casual|non-professional)\b",
            r"\binconsistent.*\b(communication|standards|practices)\b",
            r"\bvariability\s+in.*\b(communication|practices)\b",
            r"\bcontrasts?\s+(sharply\s+)?with.*\b(professional|standards)\b",
            r"\bunder\s+different\s+circumstances\b",
            # Negative judgment words about hobby projects
            r"\bgap\b.*\b(in|represents|indicates)\b",
            r"\babsence\b.*\b(of|represents|suggests)\b",
            r"\bweakness(es)?\b.*\b(in|represents)\b",
            r"\bconcerning\b.*\b(pattern|lack|absence)\b",
            r"\bcomplete\s+absence\s+of.*documentation\b",
            r"\bdocumentation\s+strategy\s+absence\b",
            # Abandonment and commitment inferences
            r"^Project appears abandoned$",  # Exact match for areas_to_explore items
            r"^Missing README documentation$",  # Exact match for areas_to_explore items
            r"\babandon(ment|ed)?.*\bpattern\b",
            r"\bproject\s+(abandon(ment|ed)?|appears\s+abandoned)\b",
            r"\bappears\s+abandoned\b",  # Simpler catch-all
            r"\bdifficultly?\s+maintaining.*\bcommitment\b",
            r"\bfollow[_\s-]?through\s+(problem|issue|difficult)\b",
            r"\bcommitment\s+(issue|problem|difficult|concern)\b",
            r"\blong[_\s-]?term\s+commitment\b",
            r"\bdormancy.*\bpattern\b",
            r"\bshift\s+in\s+priorities\b",
            # Documentation judgments
            r"(missing|absence\s+of|lack\s+of)\s+README.*communication",
            r"README.*communication.*weakness",
            r"documentation.*critical\s+for\s+team",
            r"knowledge\s+sharing.*capabilit",
            r"documentation.*strategy.*deficien",
            r"documentation.*\bgap\b.*knowledge\s+sharing",
            r"\blimits\s+project\s+accessibility\b",
            r"\bmaintainability\s+for\s+team\s+environments\b",
            # Commit message judgments (professionalism - EXPANDED)
            r"\bcryptic\s+commit\b",
            r"\binformal.*communication\s+(style|practice|patterns?)\b",
            r"\bcasual.*non-professional.*communication\b",
            r"\bprofessional\s+communication\s+skill\s+development\b",
            r"\bcasual.*\bapproach.*\b(version\s+control|communication)\b",
            r"\bfrustration\s+management\b",
            r"\bunprofessional.*\bcommit\b",
            r"\b(idek|wip|stuff).*\b(reveals|suggests|indicates|demonstrat)\b",
            r"\bcommunication.*\bdiscipline.*\bdegradation\b",
            r"\binformal\s+messaging\s+approach\b",
            # CI/CD judgments
            r"\babsence\s+of\s+CI/CD\b",
            r"\bno\s+CI/CD.*(gap|culture|practices)\b",
            r"\bmissing.*automation.*\bgap\b",
            r"\bmanual.*quality.*assurance.*process\b",
            r"reliance.*manual.*(testing|processes)",
            r"automated.*deployment.*pipeline",
            # Community engagement
            r"no\s+community\s+engagement.*despite",
            r"lack.*(stars|forks|community).*suggests",
        ]

        sanitized = []
        violations_count = 0

        for insight in insights:
            should_filter = False

            # Check title
            title = insight.get("title", "")
            if title:
                for pattern in FORBIDDEN_PATTERNS:
                    if re.search(pattern, title, re.IGNORECASE):
                        should_filter = True
                        violations_count += 1
                        logger.critical(
                            f"🚨 AI VIOLATION in INSIGHT TITLE! "
                            f"Pattern '{pattern}' found in: {title}"
                        )
                        break

            # Check description if not already filtered
            if not should_filter:
                description = insight.get("description", "")
                if description:
                    for pattern in FORBIDDEN_PATTERNS:
                        if re.search(pattern, description, re.IGNORECASE):
                            should_filter = True
                            violations_count += 1
                            logger.critical(
                                f"🚨 AI VIOLATION in INSIGHT DESCRIPTION! "
                                f"Pattern '{pattern}' found in: {description[:100]}..."
                            )
                            break

            if not should_filter:
                sanitized.append(insight)

        if violations_count > 0:
            logger.critical(
                f"INSIGHT OBJECT SANITIZATION! "
                f"Filtered {violations_count} insights with harsh judgments"
            )

        return sanitized

    def _parse_response(
        self,
        response: str,
        repo_data: RepositoryData,
        input_tokens: int,
        output_tokens: int,
        subscription_plan: Optional[SubscriptionPlan] = None,
    ) -> AnalysisResult:
        """
        Parse AI response into structured analysis result.

        Args:
            response: Raw AI response text
            repo_data: Original repository data
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens generated
            subscription_plan: Optional subscription plan to determine parsing format

        Returns:
            Structured analysis result
        """
        # Use JSON parser for ALL tiers (including Scale+)
        # This is what was working perfectly with the TODO app
        from .hardened_json_parser import create_hardened_parser

        # Phase 2 of Operation Containment Field: Use HardenedJSONParser
        parser = create_hardened_parser()
        expected_keys = [
            "summary",
            "observed_patterns",
            "limitations",
            "context_notes",
            "upgrade_benefit",
        ]

        parsed_data, error_message = parser.parse(response, expected_keys)

        if parsed_data:
            logger.info("HardenedJSONParser successfully extracted structured data")
        else:
            logger.error(f"HardenedJSONParser failed: {error_message}")
            # Fall back to template response
            return self._create_fallback_result(
                repo_data, input_tokens, output_tokens, error_message
            )

        try:
            # Extract evidence-based fields
            summary = parsed_data.get(
                "summary", f"Evidence-based analysis of {repo_data.full_name}"
            )

            # Parse evidence strength
            evidence_strength_data = parsed_data.get("evidence_strength", {})

            # Helper function to get evidence count (replaced scoring)
            def get_evidence_count(key: str, default: int = 0) -> int:
                evidence = evidence_strength_data.get(key, default)
                try:
                    # Evidence count - no range validation needed
                    return max(0, int(evidence))  # Ensure non-negative
                except (ValueError, TypeError):
                    logger.warning(
                        f"Invalid {key} evidence count, using default {default}"
                    )
                    return default

            evidence_strength = EvidenceStrength(
                technical_competence=get_evidence_count("technical_competence"),
                communication_skills=get_evidence_count("communication_skills"),
                professional_practices=get_evidence_count("professional_practices"),
                growth_potential=get_evidence_count("growth_potential"),
            )

            # Parse evidence patterns from new "observed_patterns" structure
            evidence_patterns = []
            patterns_data = parsed_data.get(
                "observed_patterns", parsed_data.get("evidence_patterns", [])
            )

            for pattern_data in patterns_data:
                evidence_patterns.append(
                    EvidencePattern(
                        pattern=pattern_data.get("pattern", ""),
                        evidence=pattern_data.get("evidence", ""),
                        commits=pattern_data.get("commits", []),
                        files=pattern_data.get("files", []),
                        strength=pattern_data.get(
                            "relevance", pattern_data.get("strength", "moderate")
                        ),
                    )
                )

            # Parse context alignment with two-factor validation
            context_alignment_data = parsed_data.get("context_alignment", {})

            # Two-factor check: Must have sufficient commits AND actual code
            has_sufficient_data = (
                repo_data.metrics.total_commits >= 20
                and self._has_actual_code(repo_data)
            )

            if has_sufficient_data:
                context_alignment = ContextAlignment(
                    startup=context_alignment_data.get("startup", {}),
                    enterprise=context_alignment_data.get("enterprise", {}),
                    agency=context_alignment_data.get("agency", {}),
                    open_source=context_alignment_data.get("open_source", {}),
                )
            else:
                # Force empty context alignment for insufficient data
                logger.info(
                    f"Insufficient data for context alignment: "
                    f"commits={repo_data.metrics.total_commits}, "
                    f"has_code={self._has_actual_code(repo_data)}"
                )
                context_alignment = ContextAlignment()

            # Extract other fields (use new structure or fallback to old)
            verification_gaps = parsed_data.get(
                "limitations", parsed_data.get("verification_gaps", [])
            )
            anti_patterns = parsed_data.get("anti_patterns", [])

            # Extract key insights from parsed data and sanitize
            key_insights = parsed_data.get("key_insights", [])
            areas_to_explore = parsed_data.get("areas_to_explore", [])

            # Sanitize harsh judgments about hobby projects
            key_insights = self._sanitize_hobby_project_judgments(key_insights)
            areas_to_explore = self._sanitize_hobby_project_judgments(areas_to_explore)

            return AnalysisResult(
                summary=summary,
                evidence_strength=evidence_strength,
                evidence_patterns=evidence_patterns,
                context_alignment=context_alignment,
                verification_gaps=verification_gaps,
                anti_patterns=anti_patterns,
                key_insights=key_insights,
                areas_to_explore=areas_to_explore,
                cost=self._calculate_actual_cost(input_tokens, output_tokens),
                token_count=input_tokens + output_tokens,
            )

        except Exception as e:
            logger.error(f"Failed to process parsed JSON data: {e}")
            return self._create_fallback_result(
                repo_data, input_tokens, output_tokens, str(e)
            )

    def _create_fallback_result(
        self,
        repo_data: RepositoryData,
        input_tokens: int,
        output_tokens: int,
        error_message: str,
    ) -> AnalysisResult:
        """
        Create a fallback analysis result when JSON parsing completely fails.

        This ensures we always return a valid result structure even when
        the AI response is completely unparseable.
        """
        logger.warning(
            f"Creating fallback result due to parsing failure: {error_message}"
        )

        # Create minimal but valid result
        summary = f"Evidence-based analysis of {repo_data.full_name}"

        # Default evidence strength (neutral)
        evidence_strength = EvidenceStrength(
            technical_competence=50,
            communication_skills=50,
            professional_practices=50,
            growth_potential=50,
        )

        # Create basic evidence patterns from repo data
        evidence_patterns = [
            EvidencePattern(
                pattern="parsing_failure",
                evidence=f"AI response could not be parsed: {error_message[:100]}",
                commits=[],
                files=[],
                strength="system_error",
            )
        ]

        # Default structures
        context_alignment = ContextAlignment()
        verification_gaps = [
            "AI response parsing failed - analysis incomplete",
            "Structured data extraction was not possible",
            "Manual review of raw response may be needed",
        ]
        anti_patterns: List[str] = []
        key_insights = [
            "Analysis system encountered parsing difficulties",
            "Raw AI response may contain useful insights requiring manual extraction",
        ]

        return AnalysisResult(
            summary=summary,
            evidence_strength=evidence_strength,
            evidence_patterns=evidence_patterns,
            context_alignment=context_alignment,
            verification_gaps=verification_gaps,
            anti_patterns=anti_patterns,
            key_insights=key_insights,
            cost=self._calculate_actual_cost(input_tokens, output_tokens),
            token_count=input_tokens + output_tokens,
            generated_by="fallback",
        )

    def _estimate_cost(self, repo_data: RepositoryData) -> float:
        """
        Estimate cost for analyzing repository.

        Args:
            repo_data: Repository data

        Returns:
            Estimated cost in USD
        """
        # Rough estimation based on context size
        context_length = len(self._prepare_context(repo_data))
        estimated_input_tokens = min(
            context_length // 4, 8000
        )  # Cap at 8K tokens for safety
        estimated_output_tokens = 500  # Conservative estimate

        return self._calculate_actual_cost(
            estimated_input_tokens, estimated_output_tokens
        )

    def _calculate_actual_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate actual cost based on real token usage.

        Args:
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens generated

        Returns:
            Actual cost in USD
        """
        return (
            input_tokens * self.HAIKU_INPUT_RATE
            + output_tokens * self.HAIKU_OUTPUT_RATE
        )


class RepositoryAnalyzer:
    """
    Repository analyzer with CLI-compatible interface.

    Provides repository analysis functionality with cost tracking
    and multiple analysis methods.
    """

    def __init__(self, cost_tracker: Optional[CostTracker] = None) -> None:
        """Initialize repository analyzer."""
        self.config = get_config()
        # CRITICAL FIX: Add timeout to prevent 60s default cutoff
        self.anthropic_client = anthropic.Anthropic(
            api_key=self.config.anthropic_api_key,
            timeout=300,  # 5 minutes timeout for all AI operations
        )
        self.cost_tracker = cost_tracker or CostTracker()
        self.ai_analyzer = AIAnalyzer()

    def analyze_repository(
        self,
        repo_data: RepositoryData,
        classification: Any,
        context: Optional[str] = None,
    ) -> Any:
        """
        Analyze repository with context awareness.

        Args:
            repo_data: Repository data
            classification: Repository classification result
            context: Analysis context (startup, enterprise, etc.)

        Returns:
            Analysis result with CLI-compatible structure
        """
        # Use the existing AI analyzer
        ai_result = self.ai_analyzer.analyze_repository(repo_data)

        # Convert to CLI-compatible format
        # Extract strengths from evidence patterns
        strengths = []
        concerns = []

        for pattern in ai_result.evidence_patterns:
            if pattern.strength in ["strong", "moderate"]:
                strengths.append(pattern.evidence)
            elif pattern.strength == "weak":
                concerns.append(pattern.evidence)

        # Add verification gaps as concerns
        concerns.extend(ai_result.verification_gaps)

        # Calculate evidence count summary (replaced scoring logic)
        evidence_counts = [
            ai_result.evidence_strength.technical_competence,
            ai_result.evidence_strength.communication_skills,
            ai_result.evidence_strength.professional_practices,
            ai_result.evidence_strength.growth_potential,
        ]
        total_evidence = sum(evidence_counts)  # Total evidence patterns found

        return type(
            "AnalysisResult",
            (),
            {
                "summary": ai_result.summary,
                "strengths": strengths[:5],  # Top 5 strengths
                "concerns": concerns[:5],  # Top 5 concerns
                "recommendations": [],  # Could derive from concerns
                "evidence_total": total_evidence,  # Total evidence patterns
                "context": context or "general",
            },
        )()

    def _generate_simple_analysis(self, repo_name: str, language: str) -> str:
        """
        Generate a simple test analysis for API testing.

        Args:
            repo_name: Repository name
            language: Primary language

        Returns:
            Simple analysis text for testing
        """
        try:
            # Simple test prompt
            prompt = f"Analyze this {language} repository called '{repo_name}'. Provide a brief 1-sentence summary."

            # Use a small token limit for quick tests
            from ..core.tier_config import get_configured_model

            model = get_configured_model()
            response = self.anthropic_client.messages.create(
                model=model,
                max_tokens=500,  # Small limit for quick tests
                temperature=0.1,  # Lowered for deterministic output
                messages=[{"role": "user", "content": prompt}],
            )

            # Track the usage
            self.cost_tracker.track_api_call(
                model=model,
                input_tokens=len(prompt) // 4,  # Rough estimation
                output_tokens=(
                    len(response.content[0].text) // 4
                    if response.content and hasattr(response.content[0], "text")
                    else len(str(response.content[0])) // 4
                    if response.content
                    else 0
                ),
            )

            return (
                response.content[0].text
                if response.content and hasattr(response.content[0], "text")
                else (
                    str(response.content[0])
                    if response.content
                    else "Test analysis completed successfully"
                )
            )

        except Exception as e:
            logger.error(f"Simple analysis test failed: {e}")
            return f"Test analysis failed: {str(e)}"
