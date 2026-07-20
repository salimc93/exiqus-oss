# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Structured report generation for repository analysis.

This module provides professional, recruiter-ready report formats with
executive summaries, technical breakdowns, and clear indicators.
"""

import re
import sys
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..core.classifier import ClassificationResult, RepositoryType
from ..core.context_analyzer import AnalysisContext, ContextualAssessment
from ..data.models import RepositoryData
from ..database.models import SubscriptionPlan
from ..utils.logging import get_logger
from .constants import METRIC_CONFIDENCE_RANGES, MetricName, normalize_metric_name
from .evidence.evidence_extractor import EvidenceExtractor
from .evidence.insight_engine import InsightEngine, ScreeningReport
from .evidence.question_builder import QuestionBuilder
from .evidence.recommendation_engine_evidence_based import (
    EvidenceBasedRecommendationEngine,
)
from .report_models import (
    ConfidenceLevel,
    Flag,
    ReportFormat,
    SectionAssessment,
    StructuredReport,
    SubMetric,
)
from .tier_config import get_model_for_tier, get_token_limit

__all__ = [
    "ConfidenceLevel",
    "Flag",
    "ReportFormat",
    "ReportGenerator",
    "ScreeningReport",
    "SectionAssessment",
    "StructuredReport",
    "SubMetric",
]

logger = get_logger(__name__)


class ReportGenerator:
    """
    Generates structured, professional reports for repository analysis.

    Creates recruiter-friendly reports with executive summaries,
    technical breakdowns, and evidence-based analysis insights.
    """

    def __init__(self, anthropic_api_key: Optional[str] = None) -> None:
        """Initialize report generator with evidence components."""
        from ..utils.config import get_config

        self.config = get_config()
        self.report_version = "1.0"

        # Initialize evidence components
        self.evidence_extractor = EvidenceExtractor()
        self.insight_engine = InsightEngine()  # NEW: For evidence-based insights
        self.question_builder = QuestionBuilder(anthropic_api_key)
        self.recommendation_engine = EvidenceBasedRecommendationEngine(
            anthropic_api_key
        )

    def _sanitize_insights_for_data_sufficiency(
        self, insights: List[Any], repo_data: RepositoryData
    ) -> List[Any]:
        """Remove any hallucinated metrics from insights based on data sufficiency."""
        commit_count = len(repo_data.recent_commits) if repo_data.recent_commits else 0

        if commit_count >= 20:
            # Sufficient data, no need to sanitize
            return insights

        # Pattern matching for suspicious behavioral metrics
        suspicious_patterns = [
            r"late[_\s-]?night[_\s-]?ratio[:\s]+[\d.]+",
            r"weekend[_\s-]?work[_\s-]?ratio[:\s]+[\d.]+",
            r"\d+%\s+of\s+commits\s+(after|before|during|happen)",
            r"burnout[_\s-]?risk[:\s]+(high|medium|low)",
            r"work[_\s-]?life[_\s-]?balance.*\d+%",
            r"consistent[ly]?\s+work[s]?\s+pattern",
        ]

        sanitized_insights = []
        for insight in insights:
            # Check description field for suspicious patterns
            description = getattr(insight, "description", "") or ""
            title = getattr(insight, "title", "") or ""

            contains_suspicious = False
            for pattern in suspicious_patterns:
                if (description and re.search(pattern, description, re.IGNORECASE)) or (
                    title and re.search(pattern, title, re.IGNORECASE)
                ):
                    logger.warning(
                        f"Removing insight with hallucinated metric (only {commit_count} commits): "
                        f"{(title or 'Untitled')[:50]}..."
                    )
                    contains_suspicious = True
                    break

            if not contains_suspicious:
                sanitized_insights.append(insight)

        # Log if we removed insights
        removed_count = len(insights) - len(sanitized_insights)
        if removed_count > 0:
            logger.info(
                f"Removed {removed_count} insights due to insufficient data "
                f"(only {commit_count} commits)"
            )

        return sanitized_insights

    def _build_repository_context(
        self, repo_data: RepositoryData, hiring_context: str
    ) -> str:
        """Build comprehensive repository context with actual statistics."""
        # Extract language statistics
        languages = []
        if repo_data.languages:
            # Sort languages by bytes of code (descending)
            sorted_langs = sorted(
                repo_data.languages.items(), key=lambda x: x[1], reverse=True
            )
            total_bytes = sum(repo_data.languages.values())
            for lang, bytes_count in sorted_langs[:5]:  # Top 5 languages
                percentage = (bytes_count / total_bytes * 100) if total_bytes > 0 else 0
                languages.append(f"{lang} ({percentage:.1f}%)")

        # Extract framework information from strategic key files only (not all files)
        frameworks = []

        # Use key_files_content if available (strategic file sampling)
        if repo_data.key_files_content:
            # Check package manager files for frameworks
            package_info = repo_data.key_files_content.get("package_info", {})
            if package_info:
                content = package_info.get("content", "").lower()
                filename = package_info.get("filename", "").lower()

                if "package.json" in filename:
                    if "react" in content:
                        frameworks.append("React")
                    if "next" in content:
                        frameworks.append("Next.js")
                    if "express" in content:
                        frameworks.append("Express")
                    if "vue" in content:
                        frameworks.append("Vue")
                    if "angular" in content:
                        frameworks.append("Angular")
                elif any(f in filename for f in ["pom.xml", "build.gradle"]):
                    frameworks.append("Spring")
                elif "gemfile" in filename:
                    frameworks.append("Rails")
                elif any(f in filename for f in ["requirements.txt", "pyproject.toml"]):
                    if "django" in content:
                        frameworks.append("Django")
                    if "flask" in content:
                        frameworks.append("Flask")
                    if "fastapi" in content:
                        frameworks.append("FastAPI")

            # Check for containerization
            if any(
                "docker" in f.get("filename", "").lower()
                for f in repo_data.key_files_content.values()
                if isinstance(f, dict)
            ):
                frameworks.append("Docker")

        # Fallback to limited file structure check (only root level files)
        if not frameworks:
            root_files = [
                f.path.lower()
                for f in repo_data.file_structure[:50]
                if f.type == "file" and "/" not in f.path.strip("/")
            ]
            if any("package.json" in f for f in root_files):
                frameworks.append("Node.js")
            if any("dockerfile" in f for f in root_files):
                frameworks.append("Docker")
            if any(f in root_files for f in ["pom.xml", "build.gradle"]):
                frameworks.append("Java/Spring")
            if any(f in root_files for f in ["gemfile", "gemfile.lock"]):
                frameworks.append("Ruby/Rails")

        # Analyze recent commits for context
        commit_analysis = []
        if repo_data.recent_commits:
            large_commits = [
                c
                for c in repo_data.recent_commits
                if (c.additions or 0) + (c.deletions or 0) > 500
            ]
            refactoring_commits = [
                c
                for c in repo_data.recent_commits
                if any(
                    keyword in (c.message or "").lower()
                    for keyword in ["refactor", "restructure", "reorganize", "cleanup"]
                )
            ]

            if large_commits:
                # Provide specific context about what large commits indicate
                largest = large_commits[0]
                total_changes = (largest.additions or 0) + (largest.deletions or 0)
                commit_analysis.append(
                    f"Recent Large Commits: {len(large_commits)} commits >500 lines "
                    f"(largest: {total_changes:,} lines - '{largest.message[:60]}...'). "
                    f"Indicates: {'feature development' if largest.additions and largest.additions > (largest.deletions or 0) else 'major refactoring'}"
                )

            if refactoring_commits:
                commit_analysis.append(
                    f"Refactoring Activity: {len(refactoring_commits)} refactoring commits "
                    f"indicates code quality focus and technical debt management"
                )

        # Build context string
        context_parts = [
            f"Hiring Context: {hiring_context}",
            f"Repository: {repo_data.full_name}",
            (
                f"Primary Languages: "
                f"{', '.join(languages) if languages else 'Not detected'}"
            ),
            (
                f"Frameworks/Tools: "
                f"{', '.join(frameworks) if frameworks else 'Not detected'}"
            ),
            (
                f"Total Files: "
                f"{len([f for f in repo_data.file_structure if f.type == 'file'])}"
            ),
            (
                f"Lines of Code: {repo_data.metrics.lines_of_code:,}"
                if repo_data.metrics.lines_of_code
                else "Lines of Code: Not calculated"
            ),
            (
                (
                    f"Test Coverage Estimate: "
                    f"{repo_data.metrics.test_coverage_estimate:.0%}"
                )
                if repo_data.metrics.test_coverage_estimate > 0
                else "Test Coverage: Not detected"
            ),
            f"Total Commits: {repo_data.metrics.total_commits}",
            f"Contributors: {repo_data.metrics.unique_contributors}",
            f"Repository Size: {round(repo_data.size / 1024, 2)} MB",
            f"Last Activity: {repo_data.metrics.days_since_last_commit} days ago",
        ]

        # Add commit analysis if available
        context_parts.extend(commit_analysis)

        return "\n".join(context_parts)

    def _generate_unified_insights_and_questions(
        self,
        evidence: Dict[str, Any],
        context: str,
        tier: str,
        anthropic_client: Optional[Any] = None,
        repo_data: Optional[RepositoryData] = None,
        subscription_plan: Optional[Any] = None,
        status_callback: Optional[Callable[..., None]] = None,
        role: str = "senior",
        use_ai_for_free: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Delegate analysis to appropriate strategy based on tier.
        """
        logger.info(f"Unified generation called for tier: {tier}")

        if tier.lower() == "free" and not use_ai_for_free:
            logger.info("FREE tier: No AI quota remaining, skipping unified generation")
            return None

        # Generate repository characteristics (moved from monolithic method)
        from .evidence.repository_characteristics import (
            generate_repository_characteristics,
        )

        if repo_data:
            characteristics = generate_repository_characteristics(repo_data)
            evidence["repository_characteristics"] = characteristics

        # Setup Client
        from ..ai.anthropic_wrapper import AnthropicWrapper

        if not anthropic_client:
            if not self.insight_engine.anthropic_client:
                raise Exception("AI client not available")
            anthropic_client = self.insight_engine.anthropic_client

        if not isinstance(anthropic_client, AnthropicWrapper):
            # Simplistic timeout logic for wrapper creation
            timeout = 300
            api_key = (
                getattr(anthropic_client, "_api_key", None)
                or self.insight_engine.anthropic_api_key
            )
            anthropic_client = AnthropicWrapper(
                api_key=api_key, default_timeout=timeout
            )

        # Select Strategy
        from .analysis.strategies.advanced_strategy import AdvancedAnalysisStrategy
        from .analysis.strategies.analysis_strategy import AnalysisStrategy
        from .analysis.strategies.standard_strategy import StandardAnalysisStrategy

        strategy: AnalysisStrategy
        if tier.lower() in ["professional", "enterprise", "scale_plus"]:
            strategy = AdvancedAnalysisStrategy()
        else:
            strategy = StandardAnalysisStrategy()

        # Execute Strategy (Circuit Breaker logic reduced for readability/refactoring,
        # normally would wrap this call)
        try:
            return strategy.analyze(
                repo_data=repo_data,
                context=context,
                tier=tier,
                anthropic_client=anthropic_client,
                evidence=evidence,
            )
        except Exception as e:
            logger.error(f"Strategy execution failed: {e}")
            raise

    def _sanitize_behavioral_inferences(self, text: str) -> str:
        """
        Remove any behavioral inferences from AI-generated text.

        This is the final firewall to prevent biased behavioral judgments
        based on commit timestamps or work patterns.
        """
        # FORBIDDEN_PHRASES that indicate behavioral inference
        FORBIDDEN_PHRASES = [
            # Project lifecycle and abandonment judgments (CRITICAL - hobby projects get abandoned)
            r"\bproject\s+appears\s+abandoned\b",  # Exact phrase that keeps appearing
            r"\bappears\s+abandoned\b",
            r"\babandoned\s+for\s+over\b",  # "Repository abandoned for over X years"
            r"\brepository\s+abandoned\b",
            r"\brepository\s+may\s+be\s+outdated\s+or\s+abandoned\b",
            r"\bdormancy\s+period\b",
            r"\binactivity\s+period\b",
            r"\bproject\s+(completion|abandonment|lifecycle|transition)\b",
            r"\blifecycle\s+transition\b",
            r"\btransition\s+indicators?\b",
            r"\binactive\s+project\b",
            r"\bno\s+recent\s+activity\b",
            r"\bproject\s+status\b",
            r"\bsuggests?\s+potential\s+(challenges?|issues?)\b",
            r"\bmay\s+require\s+validation\b",
            r"\brequire.*validation.*enterprise\b",
            r"\bvalidation.*enterprise\s+context\b",
            r"\bthis\s+pattern\s+suggests\b",
            r"\btransition\s+management\b",
            r"\bproject\s+closure\s+communication\b",
            r"\bchallenges?\s+with.*closure\b",
            r"\bindicates?\s+either.*or\b",
            r"\beither.*completion\s+or\s+abandonment\b",
            # Testing judgments for small/experimental projects
            r"\blacks?\s+automated\s+testing\b",  # Inappropriate for tiny/hobby projects
            r"\bno\s+automated\s+tests\b",
            r"\bmissing\s+test\s+coverage\b",
            r"\babsence\s+of\s+tests?\b",
            # Absence/gap language (sounds judgmental, not evidence-based)
            r"\bcomplete\s+absence\s+of\b",
            r"\babsence\s+of.*indicates\s+gap\b",
            r"\bgap\s+in.*\b(practices|skills|knowledge|understanding)\b",
            r"\brepresents\s+(a\s+)?significant\s+area\s+for\s+professional\s+development\b",
            r"\barea\s+for\s+professional\s+development\b",
            # Work ethic inferences
            r"work\s+ethic",
            r"dedication",
            r"dedicated\s+(developer|contributor|programmer)",
            r"hard[_\s-]?working",
            r"committed\s+to\s+(the\s+)?project",
            # Work-life balance inferences
            r"work[_\s-]?life[_\s-]?balance",
            r"burnout(\s+risk)?",
            r"sustainable\s+pace",
            r"healthy\s+boundaries",
            # Schedule preference inferences
            r"(prefers?|likes?)\s+(to\s+)?work\s+(at\s+)?night",
            r"night\s+owl",
            r"early\s+bird",
            r"weekend\s+warrior",
            r"works?\s+best\s+(at|during)",
            # Responsiveness/availability inferences
            r"responsive(ness)?\s+to\s+project\s+needs",
            r"available\s+(during|outside)\s+hours",
            r"flexible\s+schedule",
            # Commitment level inferences
            r"level\s+of\s+commitment",
            r"shows?\s+commitment",
            r"committed\s+contributor",
            r"passionate\s+about",
            # General behavioral judgments
            r"work\s+style\s+and\s+dedication",
            r"demonstrates?\s+dedication",
            r"shows?\s+(a\s+)?strong\s+commitment",
            r"dedicated\s+work\s+ethic",
            # Corporate jargon and non-observable inferences
            r"minimal\s+bureaucracy",
            r"bureaucratic",
            r"startup\s+mentality",
            r"cultural?\s+fit",
            r"team\s+player",
            r"go[_\s-]?getter",
            r"self[_\s-]?starter",
            r"proactive\s+(approach|mindset)",
            r"takes?\s+initiative",
            r"ownership\s+mentality",
            r"entrepreneurial\s+spirit",
            r"startup\s+environment\s+fit",
            r"autonomous\s+work\s+style",
            r"independent\s+problem[_\s-]?solving\s+approach",
            r"fits?\s+startup\s+environments?",
            # PR-specific forbidden inferences
            r"low\s+(pr\s+)?merge\s+rate",
            r"poor\s+(pr\s+)?success\s+rate",
            r"indicates?\s+(process\s+)?alignment\s+issues",
            r"suggests?\s+challenges?\s+with",
            r"may\s+not\s+align\s+with",
            r"could\s+indicate\s+(problems?|issues?)",
            r"raises?\s+questions?\s+about",
            r"sustained\s+engagement",
            r"maintained\s+engagement",
            r"consistent\s+activity",
            r"sporadic\s+contributions?",
            r"focus(es)?\s+(primarily|mainly)\s+on",
            r"priorities?\s+appear\s+to\s+be",
            r"prefers?\s+to\s+work\s+on",
            r"collaboration\s+style",
            r"team\s+dynamics",
            r"work(ing)?\s+relationships?",
        ]

        original_text = text
        violations_found = []

        # Check each forbidden phrase
        for pattern in FORBIDDEN_PHRASES:
            if re.search(pattern, text, re.IGNORECASE):
                violations_found.append(pattern)

                # CRITICAL: Handle both paragraph text and single-line list items
                # If text has no periods, it's likely a bullet point - just return empty string
                if "." not in text:
                    logger.critical(
                        f"AI VIOLATION DETECTED! Forbidden pattern '{pattern}' "
                        f"found in list item: '{text[:100]}' - REMOVING ENTIRE ITEM"
                    )
                    return ""  # Remove the entire list item

                # For paragraph text, filter out sentences containing the pattern
                sentences = text.split(".")
                filtered_sentences: list[str] = []

                for sentence in sentences:
                    if not re.search(pattern, sentence, re.IGNORECASE):
                        filtered_sentences.append(sentence)
                    else:
                        logger.critical(
                            f"AI VIOLATION DETECTED! Forbidden inference pattern '{pattern}' "
                            f"found in: {sentence.strip()[:100]}..."
                        )

                text = ".".join(filtered_sentences)

        # Clean up any double periods or spacing issues
        text = re.sub(r"\.+", ".", text)
        text = re.sub(r"\s+", " ", text)
        text = text.strip()

        if violations_found:
            logger.critical(
                f"BEHAVIORAL INFERENCE FIREWALL ACTIVATED! "
                f"Removed {len(violations_found)} forbidden patterns: {violations_found}"
            )
            logger.debug(f"Original text length: {len(original_text)}")
            logger.debug(f"Sanitized text length: {len(text)}")

        return text

    def _get_role_level_guidance(
        self, role: str, tier: str = "basic", context: str = ""
    ) -> str:
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

        role_level = role_guidance.get(role, role_guidance["senior"])

        # Add organizational context for paid tiers (Starter/Basic and Growth/Professional)
        org_context_section = ""
        if tier.lower() in ["basic", "professional"] and context:
            # Use context directly - it's already the org context value (e.g., "enterprise", "startup")
            hiring_context = context.strip()

            if hiring_context:
                # STARTER/BASIC TIER: Just org/role context for question tailoring
                if tier.lower() == "basic":
                    org_context_section = f"""

🏢 **ORGANIZATIONAL CONTEXT**:
{hiring_context}

**Tailor questions to this hiring context** - consider the organization's needs and the target role when crafting interview questions.
"""
                # GROWTH/PROFESSIONAL TIER: Full context + key listening points
                elif tier.lower() == "professional":
                    org_context_section = f"""

🏢 **ORGANIZATIONAL CONTEXT** (Professional/Growth Tier): **{hiring_context.upper()}** for **{role.upper()}** role

⚠️ **CRITICAL: ALL QUESTIONS MUST EXPLICITLY REFERENCE BOTH {hiring_context.upper()} CONTEXT AND {role.upper()} SENIORITY**

**🎯 Key Listening Points for Interview Questions**:
When crafting questions, consider how answers will reveal:
- **Technical Fit**: Does this work demonstrate relevant skills for our tech stack/domain?
- **Problem-Solving Approach**: How does the candidate tackle real-world challenges?
- **Team Collaboration**: Evidence of working with others, code reviews, communication
- **Production Mindset**: Understanding of deployment, testing, monitoring, real-world constraints
- **Growth Trajectory**: Are they learning and improving? Do they refactor and iterate?

**🎯 MANDATORY: Context-Aware Question Requirements**:
- **EVERY question MUST explicitly reference BOTH "{hiring_context}" AND "{role}" level**
- Connect technical decisions to {hiring_context}-specific challenges at {role} level
- Ask how their approach would translate to {hiring_context} environment for a {role} role
- Include {hiring_context} AND {role}-relevant follow-ups in each question
- Example: "For a {role}-level role in a {hiring_context} environment, how would you..." or "Given {hiring_context} constraints at {role} level, walk me through..."

⚠️ **QUESTIONS WITHOUT BOTH {hiring_context.upper()} AND {role.upper()} CONTEXT WILL BE REJECTED**
"""

        return f"""
🎯 **ROLE LEVEL CONTEXT**: {role.upper()} ({role_level["years"]})

**CRITICAL: ADJUST QUESTION COMPLEXITY FOR {role.upper()} ROLE**

**{role.upper()}-Level Question Requirements**:
- **Focus on**: {role_level["focus"]}
- **Avoid**: {role_level["avoid"]}
- **Complexity Level**: {role_level["complexity"]}
- **Example Question Style**: "{role_level["example"]}"
- **Tone**: {role_level["tone"]}
{org_context_section}
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

⚠️ **IMPORTANT FOR {role.upper()}: "Avoid minutiae" applies to QUESTIONS ONLY**
- ✅ DO generate ALL required sections: Evidence Patterns, Quality Indicators, Observations, etc.
- ✅ DO include factual repo-level details (dates, commit counts, technology adoption timeline)
- ❌ DO NOT skip Evidence Patterns thinking they are "minutiae" - they are REQUIRED factual observations
- The "avoid minutiae" guidance means: don't ask questions about line-by-line code implementation details
"""

    def generate_report(
        self,
        repo_data: RepositoryData,
        classification: ClassificationResult,
        contextual_assessment: Optional[ContextualAssessment] = None,
        context: Optional[AnalysisContext] = None,
        confidence_scoring: Optional[
            Any
        ] = None,  # Kept for backward compatibility but not used
        ai_analysis: Optional[Any] = None,  # AI AnalysisResult when available
        subscription_plan: Optional[SubscriptionPlan] = None,
        status_callback: Optional[
            Callable[..., None]
        ] = None,  # Callback for retry status updates
        role: str = "senior",  # Developer role level for question generation
        use_ai_for_free: bool = False,  # NEW: Allow AI for FREE tier (first 3 analyses)
    ) -> StructuredReport:
        """
        Generate comprehensive structured report.

        Args:
            repo_data: Repository data
            classification: Classification result
            contextual_assessment: Context-aware analysis results
            context: Analysis context for evaluation
            confidence_scoring: Optional - kept for backward compatibility

        Returns:
            Complete structured report
        """
        sys.stdout.flush()
        try:
            logger.info(f"Generating structured report for {repo_data.full_name}")
        except Exception:
            sys.stdout.flush()
            raise

        report = StructuredReport(
            repository_url=repo_data.url,
            repository_name=repo_data.full_name,
            analysis_date=datetime.now(),
            context=context,
            repository_type=classification.repository_type,
            subscription_tier=subscription_plan.value if subscription_plan else "free",
        )

        # CRITICAL: Check for minimal/empty repositories FIRST
        # This prevents hallucination about non-existent code
        from ..core.classifier import AnalysisMethod, TemplateCategory

        if (
            classification.method == AnalysisMethod.TEMPLATE
            and classification.template_category == TemplateCategory.EMPTY
        ):
            # Handle minimal repository - no code analysis possible
            logger.info(
                f"Repository {repo_data.full_name} identified as minimal/empty - skipping analysis"
            )

            # Set minimal report data
            report.executive_summary = f"This repository contains minimal content (size: {round(repo_data.size / 1024, 2)}MB, {len([f for f in repo_data.file_structure if f.type == 'file'])} files) and lacks sufficient code for meaningful technical analysis."

            # Create minimal screening insights instead of trying to analyze
            report.screening_insights = ScreeningReport(
                insights=[],
                key_strengths=[],
                areas_to_explore=[
                    "Cannot analyze - repository contains minimal or no code"
                ],
                data_limitations=["Repository lacks sufficient content for analysis"],
                overall_impression="This repository contains minimal content and lacks sufficient code for meaningful technical analysis.",
                confidence_explanation="No analysis performed - repository contains minimal or no code",
            )

            # Skip evidence extraction for empty repos
            report.evidence_summary = None
            report.interview_questions = None
            report.evidence_based_recommendations = None

            # Add limitations
            report.analysis_limitations = [
                "Repository contains minimal or no code",
                "Technical analysis not possible",
                "Consider analyzing repositories with substantial implementation",
            ]

            report.risk_indicators = [
                "Repository too small for comprehensive assessment"
            ]

            # Set confidence grade for minimal repositories
            report.confidence_grade = "N/A"

            # Return early - no further analysis possible
            return report

        # Extract evidence for all tiers (needed for metrics and questions)
        evidence = None
        try:
            # Extract all evidence
            evidence = self.evidence_extractor.extract_all_evidence(repo_data)
            report.evidence_summary = evidence

            # 🎯 CRITICAL FIX: Add AI-generated evidence patterns to evidence dict
            # This is what the unified generation uses to calculate proportional insight counts
            if ai_analysis and hasattr(ai_analysis, "evidence_patterns"):
                # Convert EvidencePattern objects to dictionaries for JSON serialization
                pattern_dicts = []
                for pattern in ai_analysis.evidence_patterns:
                    if hasattr(pattern, "__dict__"):
                        # If it's a dataclass/object, convert to dict
                        pattern_dict = {
                            "pattern": getattr(pattern, "pattern", ""),
                            "evidence": getattr(pattern, "evidence", ""),
                            "files": getattr(pattern, "files", []),
                            "relevance": getattr(pattern, "relevance", ""),
                            "strength": getattr(pattern, "strength", "medium"),
                        }
                        pattern_dicts.append(pattern_dict)
                    elif isinstance(pattern, dict):
                        # If already a dict, use as-is
                        pattern_dicts.append(pattern)

                evidence["evidence_patterns"] = pattern_dicts
                logger.info(
                    f"Added {len(pattern_dicts)} AI-generated patterns to evidence"
                )
            else:
                # If no AI analysis, initialize empty patterns list
                evidence["evidence_patterns"] = []
                logger.warning("No AI analysis patterns available, using empty list")

            # 🧠 PHASE 2: THE UNIFIED APPROACH - Generate insights AND questions together
            context_str = context.value if context else "general"
            tier = subscription_plan.value.lower() if subscription_plan else "free"

            # Build comprehensive repository context with actual statistics
            repository_context = self._build_repository_context(repo_data, context_str)

            try:
                # Try the unified approach first
                sys.stdout.flush()
                logger.info("Calling unified insights generation")
                unified_result = self._generate_unified_insights_and_questions(
                    evidence=evidence,
                    context=repository_context,  # Pass full context with stats
                    tier=tier,
                    repo_data=repo_data,  # Also pass repo_data for additional info
                    subscription_plan=subscription_plan,
                    status_callback=status_callback,  # Pass status callback for retry notifications
                    role=role,  # Pass role level for question generation
                    use_ai_for_free=use_ai_for_free,  # NEW: Pass FREE tier AI availability
                )

                if unified_result:
                    # 🎯 SUCCESS: Parse unified results into separate components

                    # Convert unified insights to ScreeningInsight objects
                    from .evidence.insight_engine import (
                        InsightCategory,
                        InsightConfidence,
                        ScreeningInsight,
                    )

                    screening_insights_list = []
                    for insight_data in unified_result.get("insights", []):
                        try:
                            # Map category string to enum
                            category_mapping = {
                                "technical": InsightCategory.TECHNICAL_SKILLS,
                                "work_style": InsightCategory.WORK_PATTERNS,
                                "collaboration": InsightCategory.COLLABORATION,
                                "context_fit": InsightCategory.TECHNICAL_SKILLS,  # Default mapping
                            }
                            category = category_mapping.get(
                                insight_data.get("category", "technical"),
                                InsightCategory.TECHNICAL_SKILLS,
                            )

                            # Map confidence string to enum
                            confidence_mapping = {
                                "high": InsightConfidence.HIGH,
                                "medium": InsightConfidence.MEDIUM,
                                "low": InsightConfidence.LOW,
                            }
                            confidence = confidence_mapping.get(
                                insight_data.get("confidence", "medium"),
                                InsightConfidence.MEDIUM,
                            )

                            insight = ScreeningInsight(
                                category=category,
                                title=insight_data.get("title", ""),
                                description=insight_data.get("description", ""),
                                evidence=insight_data.get("evidence", []),
                                confidence=confidence,
                                impact=insight_data.get("impact", "neutral"),
                                context_relevance={
                                    context_str: insight_data.get(
                                        "context_relevance", ""
                                    )
                                },
                            )
                            screening_insights_list.append(insight)

                        except Exception as e:
                            logger.warning(f"Failed to parse insight: {e}")
                            continue

                    # Apply safety nets to unified insights
                    screening_insights_list = (
                        self._sanitize_insights_for_data_sufficiency(
                            screening_insights_list, repo_data
                        )
                    )

                    # Create ScreeningReport with unified results
                    analysis_summary = unified_result.get("analysis_summary", {})

                    # Extract areas_to_explore from unified AI result
                    # The AI generates these based on repository characteristics
                    areas_to_explore = unified_result.get("areas_to_explore", [])

                    # Fallback to red_flags if areas_to_explore not present (backwards compatibility)
                    if not areas_to_explore:
                        areas_to_explore = unified_result.get("red_flags", [])

                    # Final fallback - but only if AI completely failed
                    if not areas_to_explore:
                        areas_to_explore = []

                    # CRITICAL: Sanitize areas_to_explore to remove portfolio abandonment judgments
                    # Filter out "Project appears abandoned" and similar inappropriate items
                    if areas_to_explore:
                        sanitized_areas = []
                        for area in areas_to_explore:
                            if isinstance(area, str):
                                area_sanitized = self._sanitize_behavioral_inferences(
                                    area
                                )
                                # Only include if sanitization didn't remove everything
                                if area_sanitized and area_sanitized.strip():
                                    sanitized_areas.append(area_sanitized)
                        areas_to_explore = sanitized_areas

                    screening_insights = ScreeningReport(
                        insights=screening_insights_list,
                        key_strengths=analysis_summary.get("key_strengths", []),
                        areas_to_explore=areas_to_explore,
                        data_limitations=unified_result.get("data_limitations", []),
                        overall_impression=unified_result.get(
                            "summary",
                            f"Repository analysis generated {len(screening_insights_list)} insights and {len(unified_result.get('questions', []))} evidence-based questions.",
                        ),
                        confidence_explanation=unified_result.get(
                            "confidence_explanation",
                            analysis_summary.get(
                                "confidence_explanation",
                                "Analysis completed with unified approach",
                            ),
                        ).replace(
                            "**", ""
                        ),  # Remove markdown bold symbols for cleaner display
                    )

                    # Apply behavioral inference firewall
                    for insight in screening_insights.insights:
                        if hasattr(insight, "description") and insight.description:
                            insight.description = self._sanitize_behavioral_inferences(
                                insight.description
                            )
                        if hasattr(insight, "title") and insight.title:
                            insight.title = self._sanitize_behavioral_inferences(
                                insight.title
                            )

                    report.screening_insights = screening_insights

                    # Format questions for compatibility with existing structure
                    # Ensure all questions have required fields
                    validated_questions = []
                    missing_what_to_listen_for = 0
                    missing_context_relevance = 0

                    for q in unified_result.get("questions", []):
                        if isinstance(q, dict) and "question" in q:
                            # Ensure context field exists
                            if "context" not in q:
                                q["context"] = (
                                    context_str  # Use the hiring context as fallback
                                )
                            # Ensure what_to_listen_for exists
                            if "what_to_listen_for" not in q:
                                missing_what_to_listen_for += 1
                                q["what_to_listen_for"] = (
                                    "Depth of technical understanding, problem-solving approach, and real-world experience"
                                )
                            # Ensure context_relevance exists
                            if "context_relevance" not in q:
                                missing_context_relevance += 1
                                q["context_relevance"] = (
                                    f"Assesses fit for {context_str} environment and {role}-level expectations"
                                )
                            validated_questions.append(q)
                        else:
                            logger.warning(f"Skipping invalid question structure: {q}")

                    # Log summary of missing fields
                    total_questions = len(validated_questions)
                    if missing_what_to_listen_for > 0 or missing_context_relevance > 0:
                        logger.warning(
                            f"AI FIELD GENERATION REPORT FOR {tier.upper()} TIER: "
                            f"Total questions: {total_questions}, "
                            f"Missing what_to_listen_for: {missing_what_to_listen_for}/{total_questions}, "
                            f"Missing context_relevance: {missing_context_relevance}/{total_questions} - "
                            f"AI is NOT generating these fields - using fallbacks"
                        )
                    else:
                        logger.info(
                            f"AI FIELD GENERATION SUCCESS FOR {tier.upper()} TIER: "
                            f"All {total_questions} questions have what_to_listen_for and context_relevance"
                        )

                    questions = {
                        "context": context_str,
                        "total_questions": len(validated_questions),
                        "all_questions": validated_questions,
                        "customization_notes": f"Questions unified with insights for {context_str} hiring context",
                    }
                    report.interview_questions = questions

                    # Generate evidence-based recommendations from unified result
                    # Extract recommendations from insights
                    recommendations_list = []
                    for insight in screening_insights_list:
                        confidence_value = (
                            insight.confidence.value
                            if hasattr(insight.confidence, "value")
                            else str(insight.confidence)
                        )
                        if insight.impact == "positive" and confidence_value in [
                            "high",
                            "medium",
                        ]:
                            recommendations_list.append(
                                {
                                    "type": "strength",
                                    "recommendation": insight.description,
                                    "evidence": (
                                        " and ".join(insight.evidence[:2])
                                        if insight.evidence
                                        else ""
                                    ),
                                    "priority": (
                                        "high"
                                        if confidence_value == "high"
                                        else "medium"
                                    ),
                                    "context_relevance": f"Relevant for {context_str} context",
                                }
                            )
                        elif insight.impact == "concerning":
                            recommendations_list.append(
                                {
                                    "type": "concern",
                                    "recommendation": f"Review {insight.description}",
                                    "evidence": (
                                        " and ".join(insight.evidence[:2])
                                        if insight.evidence
                                        else ""
                                    ),
                                    "priority": "medium",
                                    "context_relevance": f"Important for {context_str} context",
                                }
                            )

                    # Add any explicit red flags as concerns
                    for red_flag in unified_result.get("red_flags", []):
                        recommendations_list.append(
                            {
                                "type": "concern",
                                "recommendation": red_flag,
                                "evidence": "Identified during analysis",
                                "priority": "high",
                                "context_relevance": f"Critical for {context_str} context",
                            }
                        )

                    # Build recommendations structure
                    report.evidence_based_recommendations = {
                        "context": context_str,
                        "tier": tier,
                        "total_recommendations": len(recommendations_list),
                        "all_recommendations": recommendations_list[:10],  # Limit to 10
                        "key_strengths": analysis_summary.get("key_strengths", []),
                        "areas_to_probe": areas_to_explore,
                        "decision_factors": [],
                    }

                    logger.info(
                        f"✅ Unified approach successful: {len(screening_insights_list)} insights, {len(unified_result.get('questions', []))} questions, {len(recommendations_list)} recommendations"
                    )

                    # Generate flags from unified result for the Indicators tab
                    # Always generate flags even for unified approach
                    self._generate_flags(report, repo_data, classification)

                else:
                    # Free tier - check if AI quota available
                    if use_ai_for_free:
                        logger.info(
                            "FREE tier: Using Haiku 3.5 AI analysis (within 3/month quota)"
                        )
                        # Continue with AI analysis (don't raise exception)
                    else:
                        logger.info(
                            "FREE tier: AI quota exhausted, using rule-based analysis"
                        )
                        raise Exception("Free tier uses rule-based analysis")

            except Exception as unified_error:
                # 🔥 PHASE 3: HONEST FAILURE HANDLING - No silent fallbacks
                sys.stdout.flush()
                logger.error(f"Unified AI analysis failed: {unified_error}")

                if tier.lower() == "free":
                    # Free tier uses rule-based insights (expected path)
                    screening_insights = (
                        self.insight_engine.generate_screening_insights(
                            evidence=evidence,
                            context=context_str,
                            repository_type=(
                                classification.repository_type.value
                                if classification.repository_type
                                else None
                            ),
                            tier=tier,
                        )
                    )
                    report.screening_insights = screening_insights

                    # Free tier gets limited template questions
                    questions = {
                        "context": context_str,
                        "total_questions": 3,
                        "all_questions": [
                            {
                                "category": "general",
                                "question": "Walk me through a recent technical challenge you solved and your approach.",
                                "evidence_reference": "General technical assessment",
                                "follow_ups": [
                                    "What did you learn from this experience?"
                                ],
                                "what_to_listen_for": "Problem-solving methodology and learning mindset",
                                "context_relevance": "Universal technical assessment",
                            },
                            {
                                "category": "collaboration",
                                "question": "Describe your ideal development environment and team collaboration style.",
                                "evidence_reference": "Team fit assessment",
                                "follow_ups": [
                                    "How do you handle disagreements or conflicts?"
                                ],
                                "what_to_listen_for": "Communication skills and adaptability",
                                "context_relevance": "Team dynamics evaluation",
                            },
                            {
                                "category": "growth",
                                "question": "What technologies or skills are you currently learning and why?",
                                "evidence_reference": "Growth potential",
                                "follow_ups": [
                                    "How do you stay current with industry trends?"
                                ],
                                "what_to_listen_for": "Continuous learning and curiosity",
                                "context_relevance": "Future potential assessment",
                            },
                        ],
                        "customization_notes": f"Template questions for {context_str} context - upgrade for AI-powered insights",
                    }
                    report.interview_questions = questions

                else:
                    # ⚠️ CRITICAL: AI analysis failed for paid tier - BE HONEST
                    logger.critical(
                        f"AI analysis failed for paid tier {tier}: {unified_error}"
                    )

                    # Don't pretend it worked - return honest error state
                    report.screening_insights = ScreeningReport(
                        insights=[],
                        key_strengths=[],
                        areas_to_explore=["AI analysis failed - please try again"],
                        data_limitations=[
                            "Analysis could not be completed due to technical issues"
                        ],
                        overall_impression="The AI analysis for this repository failed to complete successfully.",
                        confidence_explanation="No analysis performed - technical failure occurred",
                    )

                    report.interview_questions = {
                        "context": context_str,
                        "total_questions": 0,
                        "all_questions": [],
                        "error": "AI analysis failed to complete",
                        "message": "Please try again. If the problem persists, contact support.",
                        "can_retry": True,
                    }

                    # Add error indicators
                    report.analysis_limitations.append("AI analysis failed to complete")
                    report.risk_indicators.append(
                        "Analysis incomplete due to technical issues"
                    )

            # Generate evidence-based recommendations for Professional, Enterprise, and Scale+ only
            # Check if recommendations were already generated by unified approach
            unified_approach_succeeded = (
                hasattr(report, "evidence_based_recommendations")
                and report.evidence_based_recommendations
                and report.evidence_based_recommendations.get("all_recommendations")
            )

            if (
                subscription_plan
                and subscription_plan
                in [
                    SubscriptionPlan.PROFESSIONAL,
                    SubscriptionPlan.ENTERPRISE,
                    SubscriptionPlan.SCALE_PLUS,
                ]
                and not unified_approach_succeeded
            ):
                # Fallback: Generate recommendations using legacy engine if unified approach didn't provide them
                logger.info("Using legacy recommendation engine as fallback")
                recommendations = self.recommendation_engine.generate_recommendations(
                    evidence=evidence,
                    context=context_str,
                    tier=tier,
                    repository_type=(
                        classification.repository_type.value
                        if classification.repository_type
                        else None
                    ),
                )
                report.evidence_based_recommendations = recommendations

                # Update analysis recommendations with evidence-based ones
                if recommendations.get("all_recommendations"):
                    evidence_recs = [
                        rec.get("recommendation", "")
                        for rec in recommendations["all_recommendations"]
                        if rec.get("type") == "strength"
                        and rec.get("priority") == "high"
                    ][:3]
                    if evidence_recs:
                        report.analysis_recommendations = evidence_recs

        except Exception as e:
            logger.error(f"Error extracting evidence: {e}")
            # Continue with standard report generation

        # Evidence-based approach - context alignment through patterns and insights

        # Use AI analysis if available, otherwise generate from templates
        if ai_analysis:
            # When AI analysis is available, use its high-quality insights
            report.executive_summary = ai_analysis.summary

            # Calculate average confidence from evidence strength
            if hasattr(ai_analysis, "evidence_strength"):
                # Handle dataclass instance
                if hasattr(ai_analysis.evidence_strength, "__dict__"):
                    # Evidence-based approach - no scoring
                    pass
                # Handle dict
                elif isinstance(ai_analysis.evidence_strength, dict):
                    # Evidence-based approach - no scoring
                    pass
                else:
                    # Evidence-based approach - no scoring
                    pass
            else:
                # Evidence-based approach - no scoring
                pass

            # Extract strengths and concerns from evidence patterns
            report.key_strengths = []
            report.primary_concerns = []

            if (
                hasattr(ai_analysis, "evidence_patterns")
                and ai_analysis.evidence_patterns
            ):
                for pattern in ai_analysis.evidence_patterns[:5]:
                    if hasattr(pattern, "strength") and pattern.strength in [
                        "strong",
                        "moderate",
                    ]:
                        report.key_strengths.append(
                            pattern.evidence
                            if hasattr(pattern, "evidence")
                            else str(pattern)
                        )
                    elif hasattr(pattern, "strength") and pattern.strength == "weak":
                        report.primary_concerns.append(
                            pattern.evidence
                            if hasattr(pattern, "evidence")
                            else str(pattern)
                        )

            # Add verification gaps as concerns
            if (
                hasattr(ai_analysis, "verification_gaps")
                and ai_analysis.verification_gaps
            ):
                report.primary_concerns.extend(ai_analysis.verification_gaps[:3])

            # Use AI analysis recommendations if available
            if (
                hasattr(ai_analysis, "analysis_recommendations")
                and ai_analysis.analysis_recommendations
            ):
                report.analysis_recommendations = ai_analysis.analysis_recommendations

            # Use AI interview focus areas if available
            if (
                hasattr(ai_analysis, "interview_questions")
                and ai_analysis.interview_questions
            ):
                report.interview_focus_areas = ai_analysis.interview_questions

            # Still generate technical sections from data for completeness
            self._generate_technical_assessment(report, repo_data, classification)
            self._generate_professional_practices(report, repo_data, classification)
            self._generate_communication_assessment(report, repo_data)
            self._generate_growth_indicators(report, repo_data)

            # Generate granular metrics for Professional/Enterprise tiers
            self._generate_granular_metrics(
                report, repo_data, evidence, subscription_plan
            )

            # Use AI red/green flags if available
            if hasattr(ai_analysis, "red_flags") and ai_analysis.red_flags:
                report.red_flags = [
                    Flag(
                        type="red",
                        category="ai_analysis",
                        description=flag,
                        severity="moderate",
                    )
                    for flag in ai_analysis.red_flags
                ]
            if hasattr(ai_analysis, "green_flags") and ai_analysis.green_flags:
                report.green_flags = [
                    Flag(
                        type="green",
                        category="ai_analysis",
                        description=flag,
                        severity="minor",
                    )
                    for flag in ai_analysis.green_flags
                ]
            else:
                # Generate flags from data if not in AI result
                self._generate_flags(report, repo_data, classification)
        else:
            # Template-based generation (existing logic)
            self._generate_executive_summary(
                report, repo_data, classification, contextual_assessment
            )

            # Generate section assessments
            self._generate_technical_assessment(report, repo_data, classification)
            self._generate_professional_practices(report, repo_data, classification)
            self._generate_communication_assessment(report, repo_data)
            self._generate_growth_indicators(report, repo_data)

            # Generate granular metrics for Professional/Enterprise tiers
            self._generate_granular_metrics(
                report, repo_data, evidence, subscription_plan
            )

            # Generate flags and insights
            self._generate_flags(report, repo_data, classification)
            self._extract_key_insights(report, contextual_assessment)

            # Generate recommendations
            self._generate_recommendations(
                report, repo_data, classification, contextual_assessment
            )

        # Legacy confidence parameter - kept for backward compatibility
        if confidence_scoring:
            self._incorporate_confidence_scoring(report, confidence_scoring)

        # Calculate analysis quality metrics
        self._calculate_analysis_quality(report, repo_data)

        logger.info(f"Report generated successfully for {repo_data.full_name}")
        return report

    def _generate_executive_summary(
        self,
        report: StructuredReport,
        repo_data: RepositoryData,
        classification: ClassificationResult,
        contextual_assessment: Optional[ContextualAssessment],
    ) -> None:
        """Generate executive summary for non-technical stakeholders."""

        # Replace hardcoded recommendations with evidence-based insights
        if report.screening_insights:
            # Enhanced executive summary for complex repositories
            insights_count = (
                len(report.screening_insights.insights)
                if report.screening_insights.insights
                else 0
            )
            patterns_count = (
                len(report.evidence_summary.get("patterns", []))
                if report.evidence_summary
                else 0
            )

            # For complex repositories with rich analysis, create comprehensive summary
            if insights_count >= 8 and patterns_count >= 10:
                # Synthesize key themes from multiple insights
                key_themes = []
                if report.screening_insights.key_strengths:
                    technical_strengths = [
                        s for s in report.screening_insights.key_strengths[:2]
                    ]
                    key_themes.extend(technical_strengths)

                base_summary = report.screening_insights.overall_impression

                # Add synthesis of evidence depth
                evidence_depth = f"Analysis revealed {insights_count} actionable insights from {patterns_count} evidence patterns"

                # Create comprehensive summary
                if key_themes:
                    themes_text = (
                        " Key strengths include "
                        + " and ".join(key_themes).lower()
                        + "."
                    )
                    report.executive_summary = f"{base_summary} {evidence_depth}, showing strong technical foundation.{themes_text}"
                else:
                    report.executive_summary = f"{base_summary} {evidence_depth}, demonstrating substantial technical capabilities."
            else:
                # Use simple summary for smaller repositories
                report.executive_summary = report.screening_insights.overall_impression

            # Extract key strengths for the report
            report.key_strengths = report.screening_insights.key_strengths[:5]

            # Areas to explore become the primary concerns
            report.primary_concerns = report.screening_insights.areas_to_explore[:5]

            # Set confidence based on evidence quality
            # Evidence-based confidence - no numerical scoring
            pass
        else:
            # Fallback if screening insights generation failed
            pass
            report.executive_summary = (
                "Repository analysis completed. Manual review recommended."
            )

        # Context alignment is evidence-based, not score-based

        # Executive summary is now set from screening insights above
        # If not already set, provide a neutral summary
        if not report.executive_summary:
            repo_type_desc = self._get_repository_type_description(
                classification.repository_type
            )
            context_desc = (
                f" for {report.context.value} roles" if report.context else ""
            )

            report.executive_summary = (
                f"Analysis of {repo_type_desc}{context_desc}. "
                "Please review the screening insights and evidence-based findings "
                "to inform your interview and evaluation process."
            )

    def _generate_technical_assessment(
        self,
        report: StructuredReport,
        repo_data: RepositoryData,
        classification: ClassificationResult,
    ) -> None:
        """Generate technical skills assessment."""

        details = []
        flags = []
        limitations = []
        evidence_count = 0

        # Code quality indicators
        if repo_data.has_tests:
            evidence_count += 1
            details.append(
                f"Test coverage estimated at {repo_data.metrics.test_coverage_estimate:.0%}"
            )
            flags.append(
                Flag("green", "technical", "Has testing infrastructure", "minor")
            )
        else:
            details.append("No automated testing detected")
            flags.append(
                Flag("red", "technical", "Lacks automated testing", "moderate")
            )

        # Architecture and organization
        if len(repo_data.languages) > 1:
            evidence_count += 1
            details.append(
                f"Multi-language experience: {', '.join(repo_data.languages.keys())}"
            )

        if repo_data.size > 1000:  # >1MB suggests substantial project
            evidence_count += 1
            details.append(
                f"Substantial codebase ({round(repo_data.size / 1024, 2)}MB)"
            )

        # Development patterns
        if repo_data.metrics.commit_frequency > 1:
            evidence_count += 1
            details.append(
                f"Active development pattern ({repo_data.metrics.commit_frequency:.1f} commits/week)"
            )
        else:
            details.append("Infrequent development activity")
            limitations.append(
                "Development velocity assessment limited by low activity"
            )

        # Technical complexity
        if repo_data.metrics.lines_of_code and repo_data.metrics.lines_of_code > 5000:
            evidence_count += 1
            details.append(
                f"Handles complex projects ({repo_data.metrics.lines_of_code:,} lines of code)"
            )

        confidence = (
            ConfidenceLevel.HIGH
            if evidence_count >= 4
            else ConfidenceLevel.MEDIUM
            if evidence_count >= 2
            else ConfidenceLevel.LOW
        )

        # Evidence-based summary
        if evidence_count >= 4:
            summary = "Demonstrates strong technical skills across multiple areas based on repository evidence."
        elif evidence_count >= 2:
            summary = (
                "Shows moderate technical capability with opportunities for growth."
            )
        else:
            summary = (
                "Limited evidence of advanced technical skills in this repository."
            )

        # Add basic sub_metrics for FREE tier (will be enhanced by Haiku for paid tiers)
        basic_sub_metrics = []
        if repo_data.languages:
            primary_lang = list(repo_data.languages.keys())[0]
            lang_percentage = (
                repo_data.languages[primary_lang] / sum(repo_data.languages.values())
            ) * 100
            basic_sub_metrics.append(
                SubMetric(
                    name="Primary Language",
                    evidence=f"{primary_lang} ({lang_percentage:.0f}% of codebase)",
                    context="Shows technology specialization",
                    insight="Primary language expertise",
                )
            )

        if repo_data.has_tests:
            basic_sub_metrics.append(
                SubMetric(
                    name="Testing Practices",
                    evidence=f"Test coverage estimated at {repo_data.metrics.test_coverage_estimate:.0%}",
                    context="Quality assurance practices",
                    insight="Shows commitment to code quality",
                )
            )

        if repo_data.metrics.total_commits > 0:
            basic_sub_metrics.append(
                SubMetric(
                    name="Development Activity",
                    evidence=f"{repo_data.metrics.total_commits} total commits",
                    context="Development engagement",
                    insight="Active repository maintenance",
                )
            )

        report.technical_assessment = SectionAssessment(
            title="Technical Skills",
            confidence=confidence,
            summary=summary,
            details=details,
            flags=flags,
            limitations=limitations,
            sub_metrics=basic_sub_metrics,
        )

    def _generate_professional_practices(
        self,
        report: StructuredReport,
        repo_data: RepositoryData,
        classification: ClassificationResult,
    ) -> None:
        """Generate professional practices assessment."""

        details = []
        flags = []
        evidence_count = 0

        # Documentation practices
        if repo_data.has_readme:
            evidence_count += 1
            readme_quality = (
                "comprehensive"
                if len(repo_data.readme_content or "") > 1000
                else "basic"
            )
            details.append(f"Has {readme_quality} README documentation")
            if readme_quality == "comprehensive":
                evidence_count += 1
                flags.append(
                    Flag(
                        "green",
                        "professional",
                        "Excellent documentation practices",
                        "minor",
                    )
                )
        else:
            flags.append(
                Flag("red", "professional", "Missing README documentation", "moderate")
            )

        # Version control practices
        if repo_data.metrics.total_commits > 20:
            evidence_count += 1
            details.append(
                f"Strong version control history ({repo_data.metrics.total_commits} commits)"
            )

        # Collaboration indicators
        if repo_data.metrics.unique_contributors > 1:
            evidence_count += 1
            details.append(
                f"Collaborative development ({repo_data.metrics.unique_contributors} contributors)"
            )
            flags.append(
                Flag(
                    "green",
                    "professional",
                    "Demonstrates collaboration skills",
                    "minor",
                )
            )

        # Project maintenance
        if repo_data.metrics.days_since_last_commit < 90:
            evidence_count += 1
            details.append("Recent activity shows ongoing maintenance")
        else:
            details.append(
                f"Last activity {repo_data.metrics.days_since_last_commit} days ago"
            )
            # REMOVED: "Project appears abandoned" - judgmental language for hobby/experimental projects

        # Professional setup
        if repo_data.has_license:
            evidence_count += 1
            details.append("Includes proper licensing")

        if repo_data.has_ci_config:
            evidence_count += 1
            details.append("Has CI/CD configuration")
            flags.append(
                Flag("green", "professional", "Automated deployment practices", "minor")
            )

        confidence = (
            ConfidenceLevel.HIGH if evidence_count >= 5 else ConfidenceLevel.MEDIUM
        )

        # Evidence-based summary
        if evidence_count >= 5:
            summary = "Follows industry best practices consistently based on repository evidence."
        elif evidence_count >= 2:
            summary = "Shows awareness of professional practices with some gaps."
        else:
            summary = "Limited evidence of professional development practices in this repository."

        report.professional_practices = SectionAssessment(
            title="Professional Practices",
            confidence=confidence,
            summary=summary,
            details=details,
            flags=flags,
        )

    def _generate_communication_assessment(
        self, report: StructuredReport, repo_data: RepositoryData
    ) -> None:
        """Generate communication skills assessment."""

        details = []
        flags = []
        limitations = ["Communication assessment based on written artifacts only"]
        evidence_count = 0

        # Documentation quality
        if repo_data.readme_content:
            readme_length = len(repo_data.readme_content)
            if readme_length > 1500:
                evidence_count += 2
                details.append("Comprehensive project documentation")
                flags.append(
                    Flag(
                        "green",
                        "communication",
                        "Strong written communication",
                        "minor",
                    )
                )
            elif readme_length > 500:
                evidence_count += 1
                details.append("Adequate project documentation")
            else:
                details.append("Minimal project documentation")

        # Commit message quality (heuristic)
        if repo_data.metrics.total_commits > 10:
            evidence_count += 1
            details.append("Consistent commit history suggests organized thinking")

        # Community engagement
        if repo_data.open_issues > 0 or repo_data.forks > 0:
            evidence_count += 1
            details.append("Project generates community interest")

        # Contributing guidelines
        if repo_data.has_contributing:
            evidence_count += 1
            details.append("Provides contributor guidelines")
            flags.append(
                Flag("green", "communication", "Clear contribution guidelines", "minor")
            )

        confidence = ConfidenceLevel.MEDIUM  # Always medium due to limitations

        # Evidence-based summary without scores
        if evidence_count >= 3:
            summary = "Strong written communication evident in documentation."
        elif evidence_count >= 1:
            summary = "Adequate communication skills demonstrated through repository artifacts."
        else:
            summary = "Limited evidence of communication skills in this repository."

        report.communication_skills = SectionAssessment(
            title="Communication Skills",
            confidence=confidence,
            summary=summary,
            details=details,
            flags=flags,
            limitations=limitations,
        )

    def _generate_growth_indicators(
        self, report: StructuredReport, repo_data: RepositoryData
    ) -> None:
        """Generate growth and learning indicators assessment."""

        details = []
        flags = []
        evidence_count = 0

        # Technology diversity
        if len(repo_data.languages) > 2:
            evidence_count += 1
            details.append(
                f"Experience with multiple technologies: {len(repo_data.languages)} languages"
            )
            flags.append(
                Flag("green", "growth", "Demonstrates learning agility", "minor")
            )

        # Project evolution (commits over time)
        if repo_data.metrics.total_commits > 50:
            evidence_count += 1
            details.append("Sustained development effort over time")

        # Recent activity
        if repo_data.metrics.days_since_last_commit < 30:
            evidence_count += 1
            details.append("Recent activity shows continued engagement")

        # Repository type progression
        if report.repository_type in [
            RepositoryType.PRODUCTION,
            RepositoryType.OPEN_SOURCE,
        ]:
            evidence_count += 1
            details.append("Advanced project complexity indicates skill development")

        confidence = ConfidenceLevel.MEDIUM

        # Evidence-based summary
        if evidence_count >= 3:
            summary = "Shows strong indicators of continuous learning and growth."
        elif evidence_count >= 1:
            summary = "Demonstrates some growth patterns and learning."
        else:
            summary = "Limited evidence of recent skill development in available data."

        report.growth_indicators = SectionAssessment(
            title="Growth & Learning",
            confidence=confidence,
            summary=summary,
            details=details,
            flags=flags,
        )

    def _generate_flags(
        self,
        report: StructuredReport,
        repo_data: RepositoryData,
        classification: ClassificationResult,
    ) -> None:
        """Generate red and green flags for quick assessment."""

        # Collect flags from all sections
        all_flags = []
        for section in [
            report.technical_assessment,
            report.professional_practices,
            report.communication_skills,
            report.growth_indicators,
        ]:
            if section:
                all_flags.extend(section.flags)

        # Separate and prioritize flags
        red_flags = [f for f in all_flags if f.type == "red"]
        green_flags = [f for f in all_flags if f.type == "green"]

        # CRITICAL FIX: Extract green_flags from screening_insights when using unified approach
        # This ensures the "Positive Indicators" section is populated in the UI
        if report.screening_insights and report.screening_insights.insights:
            for insight in report.screening_insights.insights:
                if insight.impact == "positive":
                    # Convert positive insights to green flags
                    green_flags.append(
                        Flag(
                            type="green",
                            category=(
                                insight.category.value
                                if hasattr(insight.category, "value")
                                else str(insight.category)
                            ),
                            description=insight.title + ": " + insight.description,
                            severity="minor",
                            evidence=insight.evidence[:2] if insight.evidence else [],
                        )
                    )
                elif insight.impact == "concerning":
                    # Convert concerning insights to red flags
                    red_flags.append(
                        Flag(
                            type="red",
                            category=(
                                insight.category.value
                                if hasattr(insight.category, "value")
                                else str(insight.category)
                            ),
                            description=insight.title + ": " + insight.description,
                            severity="moderate",
                            evidence=insight.evidence[:2] if insight.evidence else [],
                        )
                    )

        # Add critical flags based on repository analysis
        # REMOVED: "Repository abandoned for over 2 years" - judgmental language
        # Many hobby/experimental projects are not actively maintained but still valuable

        if repo_data.metrics.total_commits < 5:
            red_flags.append(
                Flag(
                    "red",
                    "experience",
                    "Very limited development history",
                    "moderate",
                    [f"Only {repo_data.metrics.total_commits} commits"],
                )
            )

        # Sort by severity
        severity_order = {"critical": 0, "moderate": 1, "minor": 2}
        red_flags.sort(key=lambda f: severity_order.get(f.severity, 3))
        green_flags.sort(key=lambda f: severity_order.get(f.severity, 3))

        report.red_flags = red_flags[:5]  # Top 5 concerns
        report.green_flags = green_flags[:5]  # Top 5 strengths

    def _extract_key_insights(
        self,
        report: StructuredReport,
        contextual_assessment: Optional[ContextualAssessment],
    ) -> None:
        """Extract key strengths and concerns."""

        # Extract from contextual assessment if available
        if contextual_assessment:
            report.key_strengths = contextual_assessment.strengths[:3]
            report.primary_concerns = contextual_assessment.concerns[:3]
        else:
            # Extract from section assessments
            strengths = []
            concerns = []

            for section in [
                report.technical_assessment,
                report.professional_practices,
                report.communication_skills,
                report.growth_indicators,
            ]:
                if section and section.confidence == ConfidenceLevel.HIGH:
                    strengths.append(
                        f"{section.title}: {section.summary.split('.')[0]}"
                    )
                elif section and section.confidence == ConfidenceLevel.LOW:
                    concerns.append(f"{section.title}: Limited evidence of capability")

            report.key_strengths = strengths[:3]
            report.primary_concerns = concerns[:3]

    def _generate_recommendations(
        self,
        report: StructuredReport,
        repo_data: RepositoryData,
        classification: ClassificationResult,
        contextual_assessment: Optional[ContextualAssessment],
    ) -> None:
        """Generate analysis recommendations and areas for exploration."""

        # Use evidence-based insights instead of hardcoded recommendations
        if report.screening_insights:
            # Use areas to explore as analysis recommendations
            report.analysis_recommendations = (
                report.screening_insights.areas_to_explore[:5]
            )

            # Add data limitations as important context
            if report.screening_insights.data_limitations:
                report.analysis_recommendations.append(
                    f"Note: GitHub analysis has limitations - {report.screening_insights.data_limitations[0]}"
                )
        elif contextual_assessment:
            # Fallback to contextual assessment if available
            report.analysis_recommendations = contextual_assessment.recommendations
        else:
            # Generic recommendations if no insights available
            report.analysis_recommendations = [
                "Review developer's actual work samples and portfolio",
                "Conduct thorough technical interview",
                "Assess problem-solving approach with real scenarios",
                "Evaluate communication and collaboration skills",
                "Discuss specific experiences relevant to your needs",
            ]

        # Generate interview focus areas
        focus_areas = []

        # Focus on weak areas based on confidence levels
        if (
            report.technical_assessment
            and report.technical_assessment.confidence == ConfidenceLevel.LOW
        ):
            focus_areas.append("Technical problem-solving abilities")

        if (
            report.professional_practices
            and report.professional_practices.confidence == ConfidenceLevel.LOW
        ):
            focus_areas.append("Development process and best practices")

        if (
            report.communication_skills
            and report.communication_skills.confidence == ConfidenceLevel.LOW
        ):
            focus_areas.append("Communication and documentation skills")

        # Add context-specific focus areas based on evidence patterns
        if report.context:
            # Always explore context-specific areas without numerical judgments
            if report.context == AnalysisContext.STARTUP:
                focus_areas.append("Adaptability and rapid learning ability")
            elif report.context == AnalysisContext.ENTERPRISE:
                focus_areas.append("Process adherence and collaboration skills")
            elif report.context == AnalysisContext.AGENCY:
                focus_areas.append("Client interaction and project management")

        report.interview_focus_areas = focus_areas[:4]  # Top 4 areas

    def _calculate_analysis_quality(
        self, report: StructuredReport, repo_data: RepositoryData
    ) -> None:
        """Calculate data completeness and analysis limitations."""

        completeness = 0.0
        limitations = []
        risk_indicators = []

        # Data availability assessment
        if repo_data.readme_content:
            completeness += 0.2
        else:
            limitations.append("No README available for context assessment")

        if repo_data.metrics.total_commits > 10:
            completeness += 0.3
        else:
            limitations.append("Limited commit history reduces analysis confidence")

        if repo_data.has_tests:
            completeness += 0.2
        else:
            limitations.append("No test coverage data available")

        if repo_data.metrics.lines_of_code:
            completeness += 0.1

        if len(repo_data.languages) > 0:
            completeness += 0.1

        if repo_data.metrics.days_since_last_commit < 365:
            completeness += 0.1
        # REMOVED: "Repository may be outdated or abandoned" - judgmental language

        # Risk indicators
        if repo_data.is_fork and repo_data.metrics.unique_contributors == 1:
            risk_indicators.append("Fork without significant original contributions")

        if repo_data.size < 100:  # Very small
            risk_indicators.append("Repository too small for comprehensive assessment")

        if not repo_data.has_license and repo_data.stars > 10:
            risk_indicators.append("Popular project without clear licensing")

        report.data_completeness = min(completeness, 1.0)
        report.analysis_limitations = limitations
        report.risk_indicators = risk_indicators

    def _generate_granular_metrics(
        self,
        report: StructuredReport,
        repo_data: RepositoryData,
        evidence: Optional[Dict[str, Any]] = None,
        subscription_plan: Optional[SubscriptionPlan] = None,
    ) -> None:
        """Generate granular sub-metrics using Haiku for Professional/Enterprise tiers."""

        # Generate metrics for all paid tiers (BASIC, Professional, Enterprise)
        # FREE tier gets basic metrics from standard generation methods
        if not subscription_plan or subscription_plan == SubscriptionPlan.FREE:
            # For FREE tier, ensure basic metrics are populated
            # These are generated by the standard _generate_* methods
            return

        # Only generate if we have evidence data
        if not evidence:
            return

        try:
            # Extract evidence for Haiku
            evidence_summary = self._prepare_evidence_for_metrics(evidence, repo_data)

            # Generate metrics using Haiku
            metrics_data = self._call_haiku_for_metrics(
                evidence_summary, repo_data, subscription_plan
            )

            # Parse and apply metrics to sections
            self._apply_metrics_to_sections(report, metrics_data)

        except Exception as e:
            logger.error(f"Error generating granular metrics: {e}")
            # Continue without granular metrics - graceful degradation

    def _prepare_evidence_for_metrics(
        self, evidence: Dict[str, Any], repo_data: RepositoryData
    ) -> Dict[str, Any]:
        """Prepare evidence data for Haiku metrics generation."""

        context = {
            "repository_name": repo_data.full_name,
            "description": repo_data.description or "No description",
            "stars": repo_data.stars,
            "primary_language": (
                list(repo_data.languages.keys())[0]
                if repo_data.languages
                else "Unknown"
            ),
            "total_commits": repo_data.metrics.total_commits,
            "contributors": repo_data.metrics.unique_contributors,
            "test_coverage": repo_data.metrics.test_coverage_estimate,
            "documentation_presence": repo_data.metrics.documentation_presence,
            "has_tests": repo_data.has_tests,
            "has_ci": repo_data.has_ci_config,
            "has_readme": repo_data.has_readme,
            "has_license": repo_data.has_license,
        }

        # Add evidence data
        summary = {
            "context": context,
            "technical_patterns": evidence.get("technical_patterns", []),
            "security_issues": evidence.get("security_issues", []),
            "collaboration_patterns": evidence.get("collaboration_patterns", []),
            "skill_evolution": evidence.get("skill_evolution", {}),
        }

        return summary

    def _call_haiku_for_metrics(
        self,
        evidence_summary: Dict[str, Any],
        repo_data: RepositoryData,
        subscription_plan: Optional[SubscriptionPlan] = None,
    ) -> Dict[str, Any]:
        """Call Haiku to generate granular metrics."""

        import json  # noqa: F811

        # Determine metrics count based on subscription tier
        if subscription_plan == SubscriptionPlan.BASIC:
            metrics_count = "2-3"
        elif subscription_plan == SubscriptionPlan.PROFESSIONAL:
            metrics_count = "3-4"  # 3-4 per category × 4 categories = 12-16 total
        elif subscription_plan == SubscriptionPlan.ENTERPRISE:
            metrics_count = "4-5"  # 4-5 per category × 4 categories = 16-20 total
        elif subscription_plan == SubscriptionPlan.SCALE_PLUS:
            metrics_count = (
                "8-10"  # 8-10 per category × 4 categories = 32-40 total (premium depth)
            )
        else:  # FREE
            metrics_count = "1-2"

        # Check if this is a public repository (has more data available)
        is_public_repo = not repo_data.is_private
        data_context = (
            "public repository with full commit history"
            if is_public_repo
            else "private repository with limited data access"
        )

        # Build comprehensive prompt
        prompt = f"""You are an expert technical assessor analyzing a {data_context}. Based on this repository analysis, generate detailed sub-metrics with contextual insights.

Repository Context:
{json.dumps(evidence_summary["context"], indent=2)}

Evidence Analysis:
Technical Patterns: {json.dumps(evidence_summary["technical_patterns"], indent=2)}
Security Issues: {json.dumps(evidence_summary["security_issues"], indent=2)}
Collaboration Patterns: {json.dumps(evidence_summary["collaboration_patterns"], indent=2)}
Skill Evolution: {json.dumps(evidence_summary["skill_evolution"], indent=2)}

Generate {metrics_count} sub-metrics for each of these 4 categories:

1. TECHNICAL ASSESSMENT
2. PROFESSIONAL PRACTICES
3. COMMUNICATION SKILLS
4. GROWTH INDICATORS

IMPORTANT GUIDELINES:
- Focus on metrics that can be meaningfully calculated from available data
- If insufficient data exists for a metric, either exclude it or find alternative evidence
- For public repos: Use commit history, file structure, documentation quality
- Never return 0% with "Limited historical data" - find positive evidence or exclude the metric
- Ensure all percentages are realistic and based on actual evidence from the repository

For each sub-metric, provide:
- name: MUST use one of these canonical metric names:
  Technical: language_proficiency, test_coverage, code_complexity, ci_cd_integration, bug_fixing
  Professional: commit_discipline, documentation_quality, security_awareness, collaboration_effectiveness
  Communication: communication_clarity, commit_message_quality, issue_tracking, responsiveness
  Growth: continuous_improvement, refactoring_activity, technology_adoption, problem_solving
- Evidence patterns and observations only
- evidence: Specific examples from the repository data
- context: Why this metric matters for analysis
- insight: What this reveals about the developer (2-3 sentences)

Return as JSON:
{{
  "technical_assessment": [
    {{
      "name": "code_complexity",
      "evidence": "TypeScript usage shows type safety focus, 2 test files for 8 code files",
      "context": "Code quality directly impacts maintenance cost and team productivity",
      "insight": "Strong TypeScript adoption indicates mature development practices and attention to type safety."
    }}
  ],
  "professional_practices": [...],
  "communication_skills": [...],
  "growth_indicators": [...]
}}

Focus on actionable insights with specific evidence from the repository data. Ensure all metrics provide meaningful value for technical evaluation."""

        # Add team fit analysis for enterprise and scale+ tiers
        if subscription_plan in [
            SubscriptionPlan.ENTERPRISE,
            SubscriptionPlan.SCALE_PLUS,
        ]:
            prompt += """

Additionally, for Enterprise tier, analyze team fit dynamics based on the evidence:

{{
  "team_fit_analysis": {{
    "collaboration_style": "Assess work patterns from commits and contributions",
    "work_pattern": "Identify daily/weekly patterns from commit history",
    "leadership_potential": "Evaluate based on project ownership and initiative",
    "mentorship_capacity": "Assess ability to guide others based on code quality and docs",
    "team_dynamics_fit": [
      "3 specific team environment recommendations based on evidence"
    ],
    "onboarding_recommendations": [
      "3 specific onboarding steps based on skill gaps and strengths"
    ]
  }}
}}"""

        # Call Haiku API with Glass House Protocol
        from ..ai.anthropic_wrapper import AnthropicWrapper
        from ..utils.config import get_config

        config = get_config()

        # 🏗️ GLASS HOUSE: Use wrapper for full transparency
        anthropic_client = AnthropicWrapper(
            api_key=config.anthropic_api_key, default_timeout=300
        )

        # Get tier name and use centralized configuration
        # Use .value to get the string value for comparison
        tier_name = "free"  # Default
        if subscription_plan:
            # Handle both enum and string cases
            plan_value = (
                subscription_plan.value
                if hasattr(subscription_plan, "value")
                else str(subscription_plan)
            )
            # Map the string value to tier name
            value_to_tier = {
                "free": "free",
                "basic": "basic",
                "professional": "professional",
                "enterprise": "enterprise",
                "scale_plus": "scale_plus",
            }
            tier_name = value_to_tier.get(plan_value.lower(), "free")

        model_to_use = get_model_for_tier(
            tier_name
        )  # Simplified: single model per tier
        max_tokens = get_token_limit(tier_name, "unified")

        if subscription_plan == SubscriptionPlan.ENTERPRISE:
            logger.info(f"Using {model_to_use} for SCALE tier metrics generation")
        else:
            logger.info(
                f"Using {model_to_use} for {tier_name} tier metrics generation with {max_tokens} tokens"
            )

        response = anthropic_client.create_message(
            model=model_to_use,
            max_tokens=max_tokens,
            temperature=0.1,  # Lowered for deterministic output
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract and parse response
        response_text = ""
        if response.content:
            content_block = response.content[0]
            if hasattr(content_block, "text"):
                response_text = content_block.text
            else:
                response_text = str(content_block)

        # Parse JSON response with better error handling
        try:
            # First try to find clean JSON
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1

            if json_start == -1 or json_end == 0:
                logger.error("No JSON found in response")
                return self._get_fallback_metrics(
                    subscription_plan or SubscriptionPlan.FREE
                )

            json_str = response_text[json_start:json_end]

            # Try to fix common JSON issues
            json_str = json_str.strip()

            # Count braces to check if JSON is complete
            open_braces = json_str.count("{")
            close_braces = json_str.count("}")

            if open_braces > close_braces:
                # JSON was truncated, add closing braces
                json_str += "}" * (open_braces - close_braces)
                logger.warning(
                    f"JSON appears truncated, added {open_braces - close_braces} closing braces"
                )

            metrics_data: Dict[str, Any] = json.loads(json_str)

            # Validate essential structure
            if not isinstance(metrics_data, dict):
                raise ValueError("Response is not a dictionary")

            return metrics_data

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse Haiku metrics response: {e}")
            logger.debug(f"Response text: {response_text[:500]}...")

            # Return fallback metrics instead of empty dict
            return self._get_fallback_metrics(
                subscription_plan or SubscriptionPlan.FREE
            )

    def _get_fallback_metrics(
        self, subscription_plan: SubscriptionPlan
    ) -> Dict[str, Any]:
        """Return empty metrics when AI parsing fails."""
        logger.warning("AI metrics generation failed, returning empty metrics")
        return {
            "metrics": {},
            "parsing_failed": True,
            "user_message": "Unable to generate detailed metrics for this repository. Please try again or contact support if the issue persists.",
        }

    def _calibrate_confidence_to_methodology(
        self, metric_name: str, raw_confidence: float
    ) -> float:
        """
        Process evidence patterns for analysis.
        Evidence-based approach without numerical scoring.

        Args:
            metric_name: Name of the metric being calibrated
            raw_confidence: Raw confidence value (0-100)

        Returns:
            Calibrated confidence value (0-100) within docs/technical/METHODOLOGY.md ranges
        """
        # docs/technical/METHODOLOGY.md confidence ranges for honesty and transparency

        # Normalize the metric name
        normalized_name = normalize_metric_name(metric_name)

        # Try to find in our standardized metrics
        min_conf, max_conf = 50, 70  # Default
        found_metric = False

        for metric in MetricName:
            if metric.value == normalized_name:
                min_conf, max_conf = METRIC_CONFIDENCE_RANGES.get(metric, (50, 70))
                found_metric = True
                break

        if not found_metric:
            logger.warning(
                f"Unknown metric '{metric_name}' (normalized: '{normalized_name}') - using default range {min_conf}-{max_conf}%"
            )

        # Calibrate the confidence to fit within the allowed range
        # This ensures we're honest about measurement limitations

        # Allow some flexibility - up to 10% above the range for exceptional cases
        flexibility_margin = 10

        if raw_confidence > max_conf:
            # If significantly over the range, apply soft calibration
            if raw_confidence > max_conf + flexibility_margin:
                # Gradually reduce confidence as it exceeds the range
                excess = raw_confidence - (max_conf + flexibility_margin)
                calibrated = max_conf + flexibility_margin - (excess * 0.5)
                logger.info(
                    f"High confidence for {metric_name}: {raw_confidence}% exceeds range {min_conf}-{max_conf}% by {raw_confidence - max_conf}%"
                )
            else:
                # Within flexibility margin - allow it but log
                calibrated = raw_confidence
                logger.info(
                    f"Allowing exceptional confidence for {metric_name}: {raw_confidence}% (slightly above range {min_conf}-{max_conf}%)"
                )
        elif raw_confidence < min_conf:
            # Below minimum - this is concerning, apply hard floor
            calibrated = min_conf
            logger.info(
                f"Low confidence for {metric_name}: {raw_confidence}% below minimum {min_conf}%"
            )
        else:
            # Within range - no calibration needed
            calibrated = raw_confidence

        if raw_confidence != calibrated:
            logger.info(
                f"Calibrated {metric_name} confidence from {raw_confidence}% to {calibrated}% (range: {min_conf}-{max_conf}%)"
            )

        return calibrated

    def _apply_metrics_to_sections(
        self, report: StructuredReport, metrics_data: Dict[str, Any]
    ) -> None:
        """Apply generated metrics to report sections."""

        # Check if parsing failed
        if metrics_data.get("parsing_failed"):
            # Log the failure but don't crash - graceful degradation
            logger.warning("Metrics parsing failed, using basic metrics only")
            if metrics_data.get("user_message"):
                # Log the message for debugging
                logger.info(f"Metrics parsing note: {metrics_data['user_message']}")
            return

        # Map metrics to sections
        section_mapping = {
            "technical_assessment": report.technical_assessment,
            "professional_practices": report.professional_practices,
            "communication_skills": report.communication_skills,
            "growth_indicators": report.growth_indicators,
        }

        for category, metrics in metrics_data.items():
            if category == "team_fit_analysis":
                # Store team fit analysis directly in evidence summary
                if not report.evidence_summary:
                    report.evidence_summary = {}
                report.evidence_summary["team_fit_analysis"] = metrics
            else:
                section = section_mapping.get(category)
                if section and isinstance(metrics, list):
                    # Convert to SubMetric objects
                    sub_metrics = []
                    for metric_data in metrics:
                        if isinstance(metric_data, dict):
                            try:
                                # Apply confidence calibration
                                raw_percentage_value = metric_data.get("percentage", 0)
                                # Handle "unknown" or other non-numeric values
                                if (
                                    isinstance(raw_percentage_value, str)
                                    and raw_percentage_value.lower() == "unknown"
                                ):
                                    raw_percentage = 0
                                else:
                                    try:
                                        raw_percentage = int(raw_percentage_value)
                                    except (ValueError, TypeError):
                                        raw_percentage = 0

                                # Note: calibration is now handled elsewhere
                                # Evidence-based approach doesn't use percentage scores
                                _ = int(
                                    self._calibrate_confidence_to_methodology(
                                        metric_data.get("name", "Unknown"),
                                        raw_percentage,
                                    )
                                )

                                # Evidence-based approach - no numerical values

                                sub_metric = SubMetric(
                                    name=metric_data.get("name", "Unknown"),
                                    evidence=metric_data.get("evidence", ""),
                                    context=metric_data.get("context", ""),
                                    insight=metric_data.get("insight", ""),
                                )
                                sub_metrics.append(sub_metric)
                            except (ValueError, TypeError) as e:
                                logger.error(f"Error creating SubMetric: {e}")
                                continue

                    # Add to section (extend if there are existing basic metrics)
                    if section.sub_metrics:
                        # Extend existing metrics (e.g., basic metrics from FREE tier)
                        section.sub_metrics.extend(sub_metrics)
                    else:
                        section.sub_metrics = sub_metrics

    def _incorporate_confidence_scoring(
        self, report: StructuredReport, confidence_scoring: Any
    ) -> None:
        """Legacy method kept for backward compatibility - evidence-based approach."""
        # Evidence-based approach - no longer using numerical scores

        # Set risk level (keeping only what exists)
        if hasattr(confidence_scoring, "overall_risk_level"):
            report.overall_risk_level = confidence_scoring.overall_risk_level.value

        # Add risk indicators from confidence scoring
        risk_descriptions = [
            risk.description for risk in confidence_scoring.risk_indicators[:3]
        ]
        report.risk_indicators.extend(risk_descriptions)

        # Add confidence-based limitations
        if confidence_scoring.confidence_breakdown.analysis_limitations:
            report.analysis_limitations.extend(
                confidence_scoring.confidence_breakdown.analysis_limitations[:3]
            )

        # Add evidence-based recommendations based on patterns found
        evidence_count = (
            len(confidence_scoring.confidence_breakdown.evidence_patterns)
            if hasattr(confidence_scoring.confidence_breakdown, "evidence_patterns")
            else 0
        )

        if evidence_count < 3:
            confidence_msg = "Limited evidence patterns identified - recommend thorough technical interview"
            report.analysis_recommendations.extend([confidence_msg])
        elif evidence_count < 5:
            confidence_msg = "Moderate evidence available - suggest additional code samples for verification"
            report.analysis_recommendations.extend([confidence_msg])

        # Add risk-based interview focus areas
        high_risk_indicators = [
            risk
            for risk in confidence_scoring.risk_indicators
            if risk.risk_level.value in ["high", "critical"]
        ]

        for risk in high_risk_indicators[:2]:  # Top 2 high risks
            if risk.mitigation_suggestions:
                report.interview_focus_areas.extend(risk.mitigation_suggestions[:1])

    def _get_repository_type_description(
        self, repo_type: Optional[RepositoryType]
    ) -> str:
        """Get human-readable description for repository type."""
        if not repo_type:
            return "repository"

        descriptions = {
            RepositoryType.PORTFOLIO: "portfolio project",
            RepositoryType.LEARNING: "learning project",
            RepositoryType.PRODUCTION: "production application",
            RepositoryType.OPEN_SOURCE: "open source library",
            RepositoryType.EXPERIMENTAL: "experimental project",
            RepositoryType.ABANDONED: "legacy repository",
            RepositoryType.FORK_CONTRIBUTION: "contributed fork",
            RepositoryType.FORK_PERSONAL: "personal fork",
        }

        return descriptions.get(repo_type, "repository")

    def format_report(
        self,
        report: StructuredReport,
        format_type: ReportFormat,
        subscription_plan: Optional[str] = None,
    ) -> str:
        """
        Format report for specific output type with tier-based restrictions.

        Args:
            report: Structured report to format
            format_type: Desired output format
            subscription_plan: User's subscription plan for access control

        Returns:
            Formatted report string
        """
        # Handle string format types (for testing/compatibility)
        if isinstance(format_type, str):
            try:
                # Try to convert string to ReportFormat enum
                format_type = ReportFormat(format_type)
            except (ValueError, KeyError):
                # Invalid format string
                return f"Format '{format_type}' not available. Valid formats: JSON, MARKDOWN, HTML, PDF_READY, USER_FRIENDLY"

        # Define tier-based format access
        format_tiers = {
            ReportFormat.USER_FRIENDLY: ["free", "basic", "professional", "enterprise"],
            ReportFormat.MARKDOWN: ["free", "basic", "professional", "enterprise"],
            ReportFormat.HTML: ["basic", "professional", "enterprise"],
            ReportFormat.JSON: ["professional", "enterprise"],  # Pro tier and above
            ReportFormat.PDF_READY: [
                "professional",
                "enterprise",
            ],  # Pro tier and above
        }

        # Check access
        allowed_tiers = format_tiers.get(format_type, ["enterprise"])
        plan = subscription_plan.lower() if subscription_plan else "free"

        if plan not in allowed_tiers:
            # Return upgrade prompt instead
            if format_type == ReportFormat.JSON:
                import json  # noqa: F811

                return json.dumps(
                    {
                        "error": "Format not available",
                        "message": "JSON export is available in Professional and Enterprise plans",
                        "current_plan": plan,
                        "upgrade_url": "/pricing",
                    },
                    indent=2,
                )
            elif format_type == ReportFormat.PDF_READY:
                return self._format_upgrade_prompt_pdf(plan)
            else:
                return f"This format ({format_type.value}) is not available in your {plan} plan. Please upgrade to access this feature."

        # Original formatting logic
        if format_type == ReportFormat.JSON:
            from .presentation.json_renderer import JSONRenderer

            renderer = JSONRenderer()
            return renderer.render(report)

        elif format_type == ReportFormat.MARKDOWN:
            return self._format_markdown(report)

        elif format_type == ReportFormat.HTML:
            return self._format_html(report)

        elif format_type == ReportFormat.PDF_READY:
            return self._format_pdf_ready(report)

        elif format_type == ReportFormat.USER_FRIENDLY:
            return self._format_user_friendly(report)

        else:
            raise ValueError(f"Unsupported format: {format_type}")

    def _format_upgrade_prompt_pdf(self, current_plan: str) -> str:
        """Format PDF upgrade prompt as a simple text message."""
        return """
====================================
    PDF EXPORT NOT AVAILABLE
====================================

Your current plan: {current_plan.upper()}

PDF export is available in:
✓ Professional Plan
✓ Enterprise Plan

Benefits of PDF export:
- Professional reports for stakeholders
- Offline access and archiving
- Print-ready formatting
- Executive-friendly layout

Upgrade at: /pricing
====================================
"""

    def _format_markdown(self, report: StructuredReport) -> str:
        """Format report as Markdown - Evidence-Based Approach."""
        from .presentation.markdown_renderer import MarkdownRenderer

        renderer = MarkdownRenderer()
        return renderer.render(report)

    def _format_html(self, report: StructuredReport) -> str:
        """Format report as comprehensive, professional HTML."""
        from .presentation.html_renderer import HTMLRenderer

        renderer = HTMLRenderer()
        return renderer.render(report)

    def generate_pdf(self, report: StructuredReport) -> bytes:
        """Generate a PDF report from structured report data."""
        import io

        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import (
            ParagraphStyle,
            getSampleStyleSheet,
        )
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            PageBreak,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )

        # Create PDF buffer
        buffer = io.BytesIO()

        # Create PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch,
        )

        # Container for the 'Flowable' objects
        from reportlab.platypus import Flowable

        elements: List[Flowable] = []

        # Get styles
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Title"],
            fontSize=24,
            textColor=colors.HexColor("#1a1a1a"),
            alignment=TA_CENTER,
            spaceAfter=30,
        )

        heading_style = ParagraphStyle(
            "CustomHeading",
            parent=styles["Heading1"],
            fontSize=16,
            textColor=colors.HexColor("#2c3e50"),
            spaceAfter=12,
            spaceBefore=20,
        )

        subheading_style = ParagraphStyle(
            "CustomSubheading",
            parent=styles["Heading2"],
            fontSize=14,
            textColor=colors.HexColor("#34495e"),
            spaceAfter=10,
            spaceBefore=15,
        )

        # Title
        elements.append(Paragraph("REPOSITORY ANALYSIS REPORT", title_style))
        elements.append(Spacer(1, 12))

        # Repository info table
        repo_data = [
            ["Repository:", report.repository_name],
            ["URL:", report.repository_url],
            [
                "Type:",
                (
                    report.repository_type.value.title()
                    if report.repository_type
                    else "Unknown"
                ),
            ],
            ["Context:", report.context.value if report.context else "GENERAL"],
            ["Analysis Date:", report.analysis_date.strftime("%Y-%m-%d %H:%M UTC")],
        ]

        repo_table = Table(repo_data, colWidths=[2 * inch, 4 * inch])
        repo_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#ecf0f1")),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#2c3e50")),
                    ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                    ("ALIGN", (1, 0), (1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bdc3c7")),
                ]
            )
        )

        elements.append(repo_table)
        elements.append(Spacer(1, 30))

        # Executive Summary
        elements.append(Paragraph("EXECUTIVE SUMMARY", heading_style))

        if report.executive_summary:
            elements.append(Paragraph(report.executive_summary, styles["Normal"]))
            elements.append(Spacer(1, 20))

        # Screening Insights
        if report.screening_insights:
            elements.append(Paragraph("EVIDENCE-BASED INSIGHTS", heading_style))

            # Overall Impression
            if report.screening_insights.overall_impression:
                elements.append(
                    Paragraph(
                        report.screening_insights.overall_impression, styles["Normal"]
                    )
                )
                elements.append(Spacer(1, 12))

            # Key Strengths
            if report.screening_insights.key_strengths:
                elements.append(Paragraph("Key Strengths", subheading_style))
                for strength in report.screening_insights.key_strengths[:5]:
                    elements.append(Paragraph(f"• {strength}", styles["Normal"]))
                elements.append(Spacer(1, 12))

            # Areas to Explore
            if report.screening_insights.areas_to_explore:
                elements.append(Paragraph("Areas to Explore", subheading_style))
                for area in report.screening_insights.areas_to_explore[:5]:
                    elements.append(Paragraph(f"• {area}", styles["Normal"]))
                elements.append(Spacer(1, 12))

            # Confidence Explanation
            if report.screening_insights.confidence_explanation:
                elements.append(
                    Paragraph(
                        f"<b>Confidence Level:</b> {report.screening_insights.confidence_explanation}",
                        styles["Normal"],
                    )
                )
                elements.append(Spacer(1, 20))

        # Section Assessments
        sections = [
            ("technical_assessment", "TECHNICAL ASSESSMENT"),
            ("professional_practices", "PROFESSIONAL PRACTICES"),
            ("communication_skills", "COMMUNICATION SKILLS"),
            ("growth_indicators", "GROWTH INDICATORS"),
        ]

        for attr_name, title in sections:
            section = getattr(report, attr_name, None)
            if section and section.sub_metrics:
                elements.append(PageBreak())
                elements.append(Paragraph(title, heading_style))
                elements.append(Paragraph(section.summary, styles["Normal"]))
                elements.append(Spacer(1, 12))

                # Sub-metrics
                for metric in section.sub_metrics[:8]:
                    elements.append(
                        Paragraph(f"<b>{metric.name}</b>", styles["Normal"])
                    )
                    if metric.insight:
                        elements.append(
                            Paragraph(f"  {metric.insight}", styles["Normal"])
                        )
                    if metric.evidence:
                        elements.append(
                            Paragraph(
                                f"  Evidence: {metric.evidence}", styles["Normal"]
                            )
                        )
                    elements.append(Spacer(1, 10))

        # Build PDF
        doc.build(elements)

        # Get PDF data
        pdf_data = buffer.getvalue()
        buffer.close()

        return pdf_data

    def _format_pdf_ready(self, report: StructuredReport) -> str:
        """Format report for PDF conversion with comprehensive content."""
        # Professional text format optimized for PDF generation
        content = f"""═══════════════════════════════════════════════════════════════
                         REPOSITORY ANALYSIS REPORT
═══════════════════════════════════════════════════════════════

Repository: {report.repository_name}
Analysis Date: {report.analysis_date.strftime("%Y-%m-%d %H:%M UTC")}
Repository Type: {report.repository_type.value.title() if report.repository_type else "Unknown"}
Report Version: {report.report_version}
Analysis Type: Evidence-Based Assessment

───────────────────────────────────────────────────────────────
EVIDENCE-BASED ANALYSIS
───────────────────────────────────────────────────────────────

"""

        # Add context information if available
        if report.context:
            content += f"""ANALYSIS CONTEXT
Context: {report.context.value.title()}

"""

        # Executive Summary
        content += f"""EXECUTIVE SUMMARY
{report.executive_summary}

"""

        # Add Evidence-Based Screening Insights if available
        if report.screening_insights:
            content += "EVIDENCE-BASED SCREENING INSIGHTS\n"
            content += "─" * 50 + "\n"
            content += (
                f"Overall Assessment: {report.screening_insights.overall_impression}\n"
            )
            content += f"Analysis Context: {report.screening_insights.confidence_explanation}\n\n"

            # Group insights by category
            insights_by_category: Dict[str, List[Any]] = {}
            for insight in report.screening_insights.insights:
                category = insight.category.value
                if category not in insights_by_category:
                    insights_by_category[category] = []
                insights_by_category[category].append(insight)

            for category, insights in sorted(insights_by_category.items()):
                content += f"{category.replace('_', ' ').upper()}:\n"
                for insight in insights:
                    content += (
                        f"• {insight.title} ({insight.confidence.value} confidence)\n"
                    )
                    content += f"  {insight.description}\n"
                    if insight.evidence:
                        content += "  Evidence:\n"
                        for evidence in insight.evidence[:2]:
                            content += f"  - {evidence}\n"
                    content += "\n"

            # Data limitations
            if report.screening_insights.areas_to_explore:
                content += "AREAS TO EXPLORE:\n"
                content += "Key topics for discussion:\n"
                for area in report.screening_insights.areas_to_explore:
                    content += f"• {area}\n"
                content += "\n"

            if report.screening_insights.data_limitations:
                content += "IMPORTANT LIMITATIONS:\n"
                content += "What GitHub data cannot tell us:\n"
                for limitation in report.screening_insights.data_limitations:
                    content += f"• {limitation}\n"
                content += "\n"

        # Key Insights Section
        content += "KEY INSIGHTS\n\n"

        if report.key_strengths:
            content += "STRENGTHS:\n"
            for i, strength in enumerate(report.key_strengths, 1):
                content += f"{i}. {strength}\n"
            content += "\n"

        if report.primary_concerns:
            content += "PRIMARY CONCERNS:\n"
            for i, concern in enumerate(report.primary_concerns, 1):
                content += f"{i}. {concern}\n"
            content += "\n"

        # Evidence Summary for Professional/Enterprise tiers
        if (
            report.subscription_tier in ["professional", "enterprise"]
            and report.evidence_summary
        ):
            content += "EVIDENCE PATTERNS IDENTIFIED\n"
            content += "─" * 50 + "\n"

            patterns = report.evidence_summary.get("patterns", [])
            for pattern in patterns[:8]:  # Show top 8 patterns
                content += f"\n• Pattern: {pattern.get('pattern', 'N/A')}\n"
                content += f"  Evidence: {pattern.get('evidence', '')}\n"
                if pattern.get("files"):
                    content += f"  Files: {', '.join(pattern['files'][:3])}\n"
            content += "\n"

        # Flags Section
        if report.green_flags or report.red_flags:
            content += "ASSESSMENT FLAGS\n\n"

            if report.green_flags:
                content += "POSITIVE INDICATORS:\n"
                for flag in report.green_flags:
                    content += f"✓ {flag.category.title()}: {flag.description}\n"
                content += "\n"

            if report.red_flags:
                content += "AREAS OF CONCERN:\n"
                for flag in report.red_flags:
                    content += f"⚠ {flag.category.title()}: {flag.description}\n"
                content += "\n"

        # Topics for Discussion (from areas_to_explore)
        if report.analysis_recommendations:
            content += "TOPICS FOR INTERVIEW DISCUSSION\n"
            for i, topic in enumerate(report.analysis_recommendations, 1):
                content += f"{i}. {topic}\n"
            content += "\n"

        # Interview Focus Areas
        if report.interview_focus_areas:
            content += "KEY AREAS TO EXPLORE\n"
            for i, area in enumerate(report.interview_focus_areas, 1):
                content += f"{i}. {area}\n"
            content += "\n"

        # Evidence-Based Features for Professional and Enterprise tiers
        if report.subscription_tier in ["professional", "enterprise"]:
            content += (
                "───────────────────────────────────────────────────────────────\n"
            )
            content += (
                f"EVIDENCE-BASED ANALYSIS ({report.subscription_tier.upper()} TIER)\n"
            )
            content += (
                "───────────────────────────────────────────────────────────────\n\n"
            )

            # Evidence-Based Analysis
            if report.evidence_summary:
                content += "DETAILED EVIDENCE ANALYSIS\n"
                content += "─" * 40 + "\n"

                # Key evidence-based strengths
                key_strengths = (
                    report.evidence_based_recommendations.get("key_strengths", [])
                    if report.evidence_based_recommendations
                    else []
                )
                if key_strengths:
                    content += "KEY EVIDENCE-BASED STRENGTHS:\n"
                    for i, strength in enumerate(key_strengths[:5], 1):
                        content += f"\n{i}. {strength.get('category', 'N/A').upper()}: {strength.get('recommendation', '')}\n"
                        content += f"   Evidence: {strength.get('evidence', '')}\n"
                        content += f"   Priority: {strength.get('priority', 'medium').title()}\n"
                        content += (
                            f"   Relevance: {strength.get('context_relevance', '')}\n"
                        )
                    content += "\n"

                # Areas to probe (concerns)
                areas_to_probe = (
                    report.evidence_based_recommendations.get("areas_to_probe", [])
                    if report.evidence_based_recommendations
                    else []
                )
                if areas_to_probe:
                    content += "AREAS TO INVESTIGATE:\n"
                    for i, concern in enumerate(areas_to_probe[:3], 1):
                        content += f"\n{i}. {concern.get('category', 'N/A').upper()}: {concern.get('recommendation', '')}\n"
                        content += f"   Evidence: {concern.get('evidence', '')}\n"
                        content += f"   Action: {concern.get('action', '')}\n"
                    content += "\n"

                # Decision factors
                decision_factors = (
                    report.evidence_based_recommendations.get("decision_factors", [])
                    if report.evidence_based_recommendations
                    else []
                )
                if decision_factors:
                    content += "KEY DECISION FACTORS:\n"
                    for factor in decision_factors:
                        content += f"• {factor}\n"
                    content += "\n"

                # Enterprise-only features
                if report.subscription_tier == "enterprise":
                    # Risk summary
                    risk_summary = (
                        report.evidence_based_recommendations.get("risk_summary", {})
                        if report.evidence_based_recommendations
                        else {}
                    )
                    if risk_summary:
                        content += "RISK ASSESSMENT (ENTERPRISE):\n"
                        content += f"Overall Risk Level: {risk_summary.get('overall_risk', 'unknown').upper()}\n"
                        risk_areas = risk_summary.get("risk_areas", [])
                        if risk_areas:
                            content += "Risk Areas:\n"
                            for risk in risk_areas:
                                content += f"• {risk.get('area', 'N/A')}: {risk.get('concern', '')}\n"
                                content += (
                                    f"  Mitigation: {risk.get('mitigation', '')}\n"
                                )
                        content += f"Mitigation Priority: {risk_summary.get('mitigation_priority', 'standard').title()}\n\n"

                    # Team integration plan
                    integration_plan = (
                        report.evidence_based_recommendations.get(
                            "team_integration_plan", {}
                        )
                        if report.evidence_based_recommendations
                        else {}
                    )
                    if integration_plan:
                        content += "TEAM INTEGRATION PLAN (ENTERPRISE):\n"
                        if integration_plan.get("onboarding_focus"):
                            content += "Onboarding Focus:\n"
                            for focus in integration_plan["onboarding_focus"]:
                                content += f"• {focus}\n"
                        if integration_plan.get("support_areas"):
                            content += "\nSupport Areas:\n"
                            for area in integration_plan["support_areas"]:
                                content += f"• {area}\n"
                        content += f"\nMentor Profile: {integration_plan.get('mentor_profile', 'N/A')}\n"
                        content += f"Timeline: {integration_plan.get('integration_timeline', 'N/A')}\n\n"

            # Evidence-Based Interview Questions
            if report.interview_questions:
                content += "EVIDENCE-BASED INTERVIEW QUESTIONS\n"
                content += f"Total Questions: {report.interview_questions.get('total_questions', 0)}\n"
                content += f"Estimated Time: {report.interview_questions.get('estimated_time', '15-30 minutes')}\n"
                content += f"Key Areas: {', '.join(report.interview_questions.get('key_areas_covered', []))}\n\n"

                # Interview flow
                interview_flow = report.interview_questions.get("interview_flow", [])
                if interview_flow:
                    content += "RECOMMENDED INTERVIEW FLOW:\n"
                    for step in interview_flow:
                        content += f"{step}\n"
                    content += "\n"

                # Top priority questions
                all_questions = report.interview_questions.get("all_questions", [])
                high_priority_questions = [
                    q for q in all_questions if q.get("priority") == "high"
                ][:3]
                other_questions = [
                    q for q in all_questions if q.get("priority") != "high"
                ][:5]

                if high_priority_questions:
                    content += "HIGH PRIORITY QUESTIONS:\n"
                    for i, q in enumerate(high_priority_questions, 1):
                        content += f"\n{i}. {q.get('question', '')}\n"
                        content += f"   Based on: {q.get('evidence_reference', '')}\n"
                        content += f"   Category: {q.get('category', '').replace('_', ' ').title()}\n"
                        content += f"   Listen for: {q.get('what_to_listen_for', '')}\n"
                        if q.get("red_flags"):
                            content += f"   Red flags: {', '.join(q['red_flags'])}\n"
                        content += f"   Time estimate: {q.get('time_estimate', '2-5 minutes')}\n"

                if other_questions:
                    content += "\nADDITIONAL QUESTIONS:\n"
                    for i, q in enumerate(other_questions, 1):
                        content += f"\n{i}. {q.get('question', '')}\n"
                        content += f"   Based on: {q.get('evidence_reference', '')}\n"
                        content += f"   Category: {q.get('category', '').replace('_', ' ').title()}\n"

                content += "\n"

        # Analysis Quality Information
        if report.analysis_limitations:
            content += "ANALYSIS LIMITATIONS\n"
            for limitation in report.analysis_limitations:
                content += f"• {limitation}\n"
            content += "\n"

        if report.risk_indicators:
            content += "RISK INDICATORS\n"
            for risk in report.risk_indicators:
                content += f"• {risk}\n"
            content += "\n"

        # Footer
        tier_features = {
            "free": "Public repositories only",
            "basic": "Public repositories only",
            "professional": "Public repositories + Evidence-based insights + Interview questions",
            "enterprise": "Public repositories + Full evidence suite + Team analysis + API access",
        }

        # Note: Behavioral signals have been removed in the evidence-based approach

        content += f"""───────────────────────────────────────────────────────────────
Generated automatically by Exiqus. © 2025 Exiqus AI Assessment Platform.
See the Methodology page for limitations and methodology.
Subscription Tier: {report.subscription_tier.upper() if report.subscription_tier else "FREE"}
Features: {tier_features.get(report.subscription_tier or "free", "Public repositories only")}
───────────────────────────────────────────────────────────────

DISCLAIMER: This analysis is based on {"publicly available" if report.subscription_tier in ["free", "basic"] else "authorized"} repository
information and should be used as one factor in the technical evaluation
process. Consider conducting code reviews and technical discussions
for comprehensive developer assessment.
"""

        return content

    # Configuration-based metric insights - DRY approach
    METRIC_INSIGHTS_CONFIG = {
        # Technical metrics (65-85% confidence)
        "Language Expertise": {
            "high": "Expert-level {language} skills - can contribute immediately",
            "medium": "Strong {language} foundation - minimal ramp-up needed",
            "low": "Limited {language} experience - may need training period",
            "confidence": 85,
            "confidence_range": (80, 90),
            "extract_context": "language",
        },
        "Test Coverage": {
            "high": "Writes comprehensive tests - reduces production bugs",
            "medium": "Some testing habits - understands quality importance",
            "low": "Minimal testing - may need quality process training",
            "confidence": 70,
            "confidence_range": (60, 80),
            "interview_prompt": "Can you walk through your testing strategy for a recent feature?",
        },
        "Documentation": {
            "high": "Documents code well - team can easily maintain their work",
            "medium": "Basic documentation - may need guidance on team standards",
            "low": "Poor documentation habits - requires mentoring on team practices",
            "confidence": 70,
            "confidence_range": (60, 80),
            "interview_prompt": "How do you decide what needs documentation in your code?",
        },
        "Commit Quality": {
            "high": "Clear change tracking - easy to debug and review code",
            "medium": "Decent commit practices - room for improvement",
            "low": "Unclear change tracking - may slow down team collaboration",
            "confidence": 75,
            "confidence_range": (65, 85),
        },
        "Bug Fixing": {
            "high": "Proactive problem solver - takes ownership of code issues",
            "medium": "Addresses problems when needed - shows responsibility",
            "low": "Limited issue resolution - may need oversight",
            "confidence": 65,
            "confidence_range": (50, 75),
        },
        "Problem-Solving Complexity": {
            "high": "Handles complex architectures - suitable for senior/architect roles",
            "medium": "Manages moderate complexity - ready for standard development tasks",
            "low": "Works on straightforward problems - ideal for junior positions",
            "confidence": 75,
            "confidence_range": (70, 85),
            "percentile_based": True,
            "interview_prompt": "Describe the most complex technical challenge you've solved recently",
            "domain_patterns": True,  # Enable domain pattern analysis
        },
        "CI/CD": {
            "high": "Modern deployment practices - understands DevOps workflows",
            "medium": "Some automation experience - can adapt to team processes",
            "low": "Limited automation knowledge - needs training on deployment",
            "confidence": 80,
            "confidence_range": (70, 90),
        },
        "Security": {
            "high": "Security-conscious - follows best practices proactively",
            "medium": "Basic security awareness - can learn company standards",
            "low": "Limited security focus - needs training on secure coding",
            "confidence": 70,
            "confidence_range": (60, 80),
        },
    }

    def _format_user_friendly(self, report: StructuredReport) -> str:
        """Format report in user-friendly format for technical evaluation."""

        # Header with disclaimers
        output = """🎯 DEVELOPER ASSESSMENT REPORT
================================================================

⚠️  IMPORTANT DISCLAIMER
This AI analysis is based on publicly available code and should be used
as a supplement to, not replacement for, comprehensive technical evaluation.
Always conduct interviews and reference checks before making final decisions.

📊 Overall Analysis Confidence: 65-85% (Based on public repository data only)
================================================================

"""

        # Repository overview
        output += """📁 REPOSITORY OVERVIEW
Repository: {report.repository_name}
URL: {report.repository_url}
Analysis Date: {report.analysis_date.strftime('%B %d, %Y')}
Repository Type: {'Private' if getattr(report, 'is_private', False) else 'Public'}

"""

        # Evidence-based assessment
        output += "📊 ASSESSMENT SUMMARY\n"
        output += "=" * 30 + "\n"

        # Evidence-based approach - no more verdicts
        output += "Assessment Type: 📊 EVIDENCE-BASED ANALYSIS\n\n"

        # Executive summary
        if report.executive_summary:
            output += f"📋 Executive Summary:\n{report.executive_summary}\n\n"

        # Add Evidence-Based Screening Insights if available
        if report.screening_insights:
            output += "🔍 EVIDENCE-BASED SCREENING INSIGHTS\n"
            output += "=" * 50 + "\n"
            output += (
                f"Overall Assessment: {report.screening_insights.overall_impression}\n"
            )
            output += (
                f"Confidence: {report.screening_insights.confidence_explanation}\n\n"
            )

            # Key strengths from insights
            if report.screening_insights.key_strengths:
                output += "✅ KEY STRENGTHS:\n"
                for strength in report.screening_insights.key_strengths[:5]:
                    output += f"   • {strength}\n"
                output += "\n"

            # Areas to explore
            if report.screening_insights.areas_to_explore:
                output += "🔍 AREAS TO EXPLORE:\n"
                for area in report.screening_insights.areas_to_explore[:5]:
                    output += f"   • {area}\n"
                output += "\n"

            # Group detailed insights by category
            insights_by_category: Dict[str, List[Any]] = {}
            for insight in report.screening_insights.insights:
                category = insight.category.value
                if category not in insights_by_category:
                    insights_by_category[category] = []
                insights_by_category[category].append(insight)

            for category, insights in sorted(insights_by_category.items()):
                output += f"📊 {category.replace('_', ' ').upper()}:\n"
                for insight in insights:
                    confidence_icon = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(
                        insight.confidence.value, "⚪"
                    )

                    output += f"{confidence_icon} {insight.title}\n"
                    output += f"   {insight.description}\n"
                    if insight.evidence:
                        output += "   Evidence:\n"
                        for evidence in insight.evidence[:2]:
                            output += f"   - {evidence}\n"
                    output += "\n"

            # Data limitations
            if report.screening_insights.data_limitations:
                output += "⚠️ IMPORTANT LIMITATIONS:\n"
                output += "What GitHub data cannot tell us:\n"
                for limitation in report.screening_insights.data_limitations:
                    output += f"   • {limitation}\n"
                output += "\n"

        # Technical sections
        output += "📊 TECHNICAL INDICATORS\n"
        output += "─" * 50 + "\n\n"

        technical_sections = [
            ("Technical Skills", report.technical_assessment),
            ("Work Quality", report.professional_practices),
            ("Communication", report.communication_skills),
            ("Growth Potential", report.growth_indicators),
        ]

        strengths: List[str] = []
        concerns: List[str] = []
        interview_prompts: List[str] = []

        # Process technical sections
        for section_name, section in technical_sections:
            if section and section.sub_metrics:
                output += f"📊 {section_name.upper()}\n"
                output += (
                    f"Confidence: {self._calculate_section_confidence(section)}%\n"
                )
                output += "-" * 25 + "\n"

                for metric in section.sub_metrics:
                    # Use the insight directly - it's already evidence-based
                    insight_text = metric.insight

                    # Get metric configuration
                    config = self._find_metric_config(metric.name)
                    confidence_range = config.get("confidence_range", (60, 80))

                    # Evidence-based categorization based on evidence keywords
                    evidence_lower = metric.evidence.lower()
                    if any(
                        word in evidence_lower
                        for word in [
                            "extensive",
                            "strong",
                            "comprehensive",
                            "high",
                            ">70%",
                            ">80%",
                            ">90%",
                        ]
                    ):
                        status = "🟢"
                        strengths.append(insight_text)
                    elif any(
                        word in evidence_lower
                        for word in [
                            "limited",
                            "minimal",
                            "weak",
                            "low",
                            "<30%",
                            "<20%",
                            "<10%",
                        ]
                    ):
                        status = "🔴"
                        concerns.append(insight_text)
                        # Add interview prompt if available
                        if config.get("interview_prompt"):
                            interview_prompts.append(config["interview_prompt"])
                    else:
                        status = "🟡"

                    # Determine confidence tier
                    avg_confidence = sum(confidence_range) / 2
                    if avg_confidence >= 70:
                        confidence_tier = "[High Confidence]"
                    elif avg_confidence >= 50:
                        confidence_tier = "[Medium Confidence]"
                    else:
                        confidence_tier = "[Low Confidence]"

                    output += f"{status} {metric.name} {confidence_tier}\n"
                    output += f"   💡 {insight_text}\n"
                    output += f"   📋 Evidence: {metric.evidence[:100]}{'...' if len(metric.evidence) > 100 else ''}\n"
                    # Calculate ± range
                    avg_conf = (confidence_range[0] + confidence_range[1]) / 2
                    conf_spread = (confidence_range[1] - confidence_range[0]) / 2
                    output += (
                        f"   📊 Confidence: {avg_conf:.0f}% ± {conf_spread:.0f}%\n\n"
                    )

        # Add interview prompts section if any were collected
        if interview_prompts:
            output += "📋 INTERVIEW PROMPTS FOR LOW-CONFIDENCE AREAS\n"
            output += "─" * 50 + "\n"
            for i, prompt in enumerate(interview_prompts[:5], 1):
                output += f"{i}. {prompt}\n"
            output += "\n"

        # Action items
        output += "🎯 RECOMMENDED NEXT STEPS\n"
        output += "=" * 30 + "\n"

        # Evidence-based next steps
        if report.screening_insights:
            output += "📊 EVIDENCE-BASED NEXT STEPS\n"
            output += "Key areas to explore in interview:\n"
            for area in report.screening_insights.areas_to_explore[:3]:
                output += f"   • {area}\n"
            if report.screening_insights.data_limitations:
                output += "\nConsiderations:\n"
                for limitation in report.screening_insights.data_limitations[:2]:
                    output += f"   • {limitation}\n"

        else:
            output += "📝 STANDARD EVALUATION\n"
            output += "Consider exploring:\n"
            for concern in concerns[:3]:
                output += f"   • {concern}\n"

        # Interview questions if available
        if hasattr(report, "interview_questions") and report.interview_questions:
            output += "\n❓ SUGGESTED INTERVIEW QUESTIONS\n"
            output += "=" * 35 + "\n"
            questions: List[Any] = (
                report.interview_questions
                if isinstance(report.interview_questions, list)
                else []
            )
            for i, question in enumerate(questions[:5], 1):
                clean_question = str(question).replace(
                    "Can you walk me through", "Tell me about"
                )
                output += f"{i}. {clean_question}\n"

        # Summary metrics
        output += "\n📈 ASSESSMENT SUMMARY\n"
        output += "=" * 25 + "\n"
        all_sections = technical_sections
        total_metrics = sum(
            len(s.sub_metrics) for _, s in all_sections if s and s.sub_metrics
        )
        output += f"Total insights analyzed: {total_metrics}\n"
        output += f"Strengths identified: {len(strengths)}\n"
        output += f"Areas of concern: {len(concerns)}\n"

        # Final disclaimer with compliance footer
        output += "\n" + "─" * 60 + "\n"
        output += (
            "Generated automatically by Exiqus. © 2025 Exiqus AI Assessment Platform.\n"
        )
        output += "See the Methodology page for limitations and methodology.\n"
        output += "This analysis is based on publicly available repository data only.\n"
        output += "─" * 60 + "\n\n"

        output += (
            "⚠️  REMINDER: Use this analysis as guidance for interview preparation\n"
        )
        output += "and technical assessment. Final evaluation should always include\n"
        output += "human assessment, interviews, and reference checks.\n"
        output += "=" * 60 + "\n"

        return output

    def _calculate_section_confidence(
        self, section: Optional[SectionAssessment]
    ) -> int:
        """Calculate confidence level for a section based on its metrics."""
        if not section or not section.sub_metrics:
            return 50

        # Base confidence on data availability and metric consistency
        metric_count = len(section.sub_metrics)
        # No longer using percentage - evidence-based approach

        # Configuration-based confidence calculation
        confidence = 60  # Base confidence

        if metric_count >= 3:
            confidence += 15  # More metrics = higher confidence

        # Evidence-based confidence - no longer using percentage ranges

        return min(confidence, 90)  # Cap at 90%

    def _get_metric_confidence(
        self, metric_name: str, percentage: int
    ) -> Tuple[int, int]:
        """Get confidence range for specific metric types using configuration."""

        # Find matching configuration
        config = self._find_metric_config(metric_name)

        # Use confidence range if available, otherwise calculate from base
        if "confidence_range" in config:
            low, high = config["confidence_range"]
        else:
            base_confidence: int = int(config.get("confidence", 70))
            # Create range around base confidence
            low = max(base_confidence - 10, 20)
            high = min(base_confidence + 10, 95)

        # Adjust based on percentage (extreme values are less confident)
        if percentage == 0 or percentage == 100:
            low = max(low - 15, 20)
            high = max(high - 15, 40)
        elif percentage <= 10 or percentage >= 90:
            low = max(low - 10, 25)
            high = max(high - 10, 50)

        return (low, high)

    def _find_metric_config(self, metric_name: str) -> Dict[str, Any]:
        """Find the best matching configuration for a metric name."""

        # Direct match first
        if metric_name in self.METRIC_INSIGHTS_CONFIG:
            return self.METRIC_INSIGHTS_CONFIG[metric_name]

        # Partial match
        for config_key, config_value in self.METRIC_INSIGHTS_CONFIG.items():
            if (
                config_key.lower() in metric_name.lower()
                or metric_name.lower() in config_key.lower()
            ):
                return config_value

        # Default fallback
        return {"confidence": 70}

    def _convert_to_meaningful_insight(
        self, metric_name: str, percentage: int, evidence: str, insight: str
    ) -> str:
        """Convert technical metrics into meaningful insights using configuration."""

        # Find matching configuration
        config = self._find_metric_config(metric_name)

        # Determine level based on percentage
        if percentage >= 70:
            level = "high"
        elif percentage <= 30:
            level = "low"
        else:
            level = "medium"

        # Get insight template
        insight_template: str = str(
            config.get(level, config.get("medium", "Average performance"))
        )

        # Handle special context extraction
        if config.get("extract_context") == "language":
            language = self._extract_language_from_evidence(evidence)
            return insight_template.format(language=language)

        # Handle percentile-based metrics like complexity
        if config.get("percentile_based") and "percentile" in evidence:
            percentile = self._extract_percentile_from_evidence(evidence)
            if percentile:
                return f"{insight_template} ({percentile}th percentile)"

        # Note: Domain patterns would need to be passed separately, not in evidence string

        return insight_template

    def _extract_language_from_evidence(self, evidence: str) -> str:
        """Extract programming language from evidence string."""
        languages = [
            "Python",
            "JavaScript",
            "TypeScript",
            "Java",
            "Go",
            "Rust",
            "C++",
            "C#",
            "Ruby",
            "PHP",
        ]
        for lang in languages:
            if lang in evidence:
                return lang
        return "primary language"

    def _extract_percentile_from_evidence(self, evidence: str) -> Optional[str]:
        """Extract percentile from evidence string."""
        import re

        # Look for pattern like "75th percentile" or "(75th percentile)"
        match = re.search(r"(\d+)th percentile", evidence)
        if match:
            return match.group(1)
        return None

    def _extract_domain_patterns_from_evidence(
        self, evidence: Dict[str, Any]
    ) -> Optional[str]:
        """Extract domain patterns from evidence for complexity insights."""
        if "domain_patterns" not in evidence:
            return None

        domain_patterns = evidence["domain_patterns"]
        if not domain_patterns:
            return None

        # Map domain patterns to user-friendly descriptions
        domain_descriptions = {
            "distributed_systems": "Distributed Systems",
            "real_time": "Real-time Processing",
            "data_processing": "Data Processing & ETL",
            "financial": "Financial Systems",
            "security": "Security & Authentication",
            "devops": "DevOps & Infrastructure",
            "machine_learning": "Machine Learning & AI",
            "web_frameworks": "Web Development",
        }

        # Architecture implications
        architecture_mapping = {
            "distributed_systems": "Microservices, Event-driven architectures",
            "real_time": "Streaming systems, WebSocket implementations",
            "data_processing": "Pipeline architectures, Batch processing",
            "financial": "High-reliability transaction systems",
            "security": "Zero-trust architectures, Secure by design",
            "devops": "Infrastructure as Code, CI/CD pipelines",
            "machine_learning": "ML pipelines, Model serving architectures",
            "web_frameworks": "MVC patterns, RESTful APIs",
        }

        # Extract active domains
        active_domains = []
        active_architectures = []

        for domain, indicators in domain_patterns.items():
            if indicators and len(indicators) > 0:  # Has pattern matches
                if domain in domain_descriptions:
                    active_domains.append(domain_descriptions[domain])
                if domain in architecture_mapping:
                    active_architectures.append(architecture_mapping[domain])

        if not active_domains:
            return None

        # Format output
        domain_info = f"Experience with: {', '.join(active_domains[:3])}"

        if active_architectures:
            domain_info += (
                f"\nArchitectural patterns: {', '.join(active_architectures[:2])}"
            )

        return domain_info
