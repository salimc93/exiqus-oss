# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Portfolio Report Generator.

Prepares portfolio evidence for AI analysis and generates structured prompts.
Follows validation script approach - AI generates complete report sections.
"""

import json
from typing import Any, Dict, List

from ..utils.logging import get_logger
from .portfolio_models import PortfolioMetadata, RepoData

logger = get_logger(__name__)


class PortfolioReportGenerator:
    """Generate portfolio analysis prompts and format evidence for AI."""

    def __init__(self) -> None:
        """Initialize portfolio report generator."""
        pass

    def prepare_evidence_for_ai(
        self,
        username: str,
        metadata: PortfolioMetadata,
        repos: List[RepoData],
        evidence: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Prepare evidence dictionary for AI consumption.

        Args:
            username: GitHub username
            metadata: Portfolio metadata
            repos: List of repository data
            evidence: Extracted evidence patterns

        Returns:
            Dictionary with all evidence structured for AI prompt
        """
        logger.info(
            f"Preparing evidence for AI: {len(repos)} repos, "
            f"{metadata.total_public_repos} total public repos"
        )

        # Calculate career span
        career_span_days = 0
        if repos:
            sorted_repos = sorted(repos, key=lambda r: r.created_at)
            oldest_repo = sorted_repos[0].created_at
            newest_repo = sorted_repos[-1].created_at
            career_span_days = (newest_repo - oldest_repo).days

        evidence_json = {
            "public_portfolio_metadata": {
                "username": username,
                "total_public_repos": metadata.total_public_repos,
                "repos_analyzed": len(repos),
                "oldest_public_repo": (
                    repos[0].created_at.strftime("%Y-%m-%d") if repos else None
                ),
                "newest_public_repo": (
                    repos[-1].created_at.strftime("%Y-%m-%d") if repos else None
                ),
                "public_career_span_days": career_span_days,
            },
            # Portfolio evolution by time periods (from evidence extractor)
            "portfolio_evolution_by_period": evidence.get(
                "portfolio_evolution_periods", []
            ),
            # Structured aggregations
            "aggregated_technologies": evidence.get("aggregated_technologies", {}),
            "aggregated_quality_indicators": evidence.get(
                "aggregated_quality_indicators", {}
            ),
            "substantial_repos_structured": evidence.get(
                "substantial_repos_structured", []
            ),
            # Evidence patterns
            "public_repos_timeline_sample": evidence.get("public_repos_timeline", [])[
                :10
            ],
            "technology_adoption_timeline": evidence.get(
                "technology_adoption_timeline", []
            )[:10],
            "public_work_quality_indicators": evidence.get(
                "public_work_quality_indicators", []
            ),
            "timeline_gaps": evidence.get("timeline_gaps", []),
            "technologies_summary": evidence.get("cross_technology_evidence", []),
            "substantial_repos": evidence.get("repo_substance_indicators", [])[:8],
            "cross_repo_patterns": evidence.get("cross_repo_patterns", []),
            "technology_evolution": evidence.get("technology_evolution_evidence", []),
            "quality_progression": evidence.get("quality_progression_evidence", []),
        }

        return evidence_json

    def get_context_description(self, context: str) -> str:
        """
        Get hiring context description for AI prompt.

        Args:
            context: Hiring context (startup, enterprise, agency, open_source)

        Returns:
            Context-specific description
        """
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

    def _get_role_level_guidance(self, role: str) -> str:
        """Get role-level specific guidance for interview question generation."""
        role_guidance = {
            "junior": {
                "level": "Junior Developer",
                "years": "0-2 years",
                "focus": "Fundamentals, basic implementation, learning approach, debugging basics, code comprehension",
                "avoid": "Architecture decisions, scaling strategies, distributed systems, advanced design patterns, multi-team coordination",
                "complexity": "Surface-level technical understanding",
                "tone": "Encouraging, supportive, focused on learning journey",
                "example": "Walk me through how you built this feature",
            },
            "mid": {
                "level": "Mid-Level Developer",
                "years": "2-5 years",
                "focus": "Implementation decisions, testing strategies, code quality practices, problem-solving methodology, API design basics",
                "avoid": "Org-wide architecture, executive decisions, multi-team coordination, infrastructure at scale",
                "complexity": "Moderate technical depth with practical application",
                "tone": "Neutral, invitational, assumes professional experience exists",
                "example": "How did you decide between approach A and B for this project?",
            },
            "senior": {
                "level": "Senior Developer",
                "years": "5+ years",
                "focus": "System architecture, scalability strategies, technical leadership, mentorship approach, system design, cross-team collaboration",
                "avoid": "Implementation minutiae, junior-level basics, overly simplistic questions",
                "complexity": "Deep technical expertise with leadership thinking",
                "tone": "Respectful, collaborative, assumes extensive private/professional work",
                "example": "How would you architect this system for 10x scale?",
            },
        }

        role_config = role_guidance.get(role, role_guidance["senior"])

        return f"""
🎯 **ROLE LEVEL CONTEXT**: {role_config["level"].upper()} ({role_config["years"]})

**CRITICAL: ADJUST INTERVIEW QUESTION COMPLEXITY FOR {role_config["level"].upper()} ROLE**

**{role_config["level"].upper()}-Level Interview Question Requirements**:
- **Focus on**: {role_config["focus"]}
- **Avoid**: {role_config["avoid"]}
- **Complexity Level**: {role_config["complexity"]}
- **Example Question Style**: "{role_config["example"]}"
- **Tone**: {role_config["tone"]}

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
"""

    def generate_analysis_prompt(
        self,
        username: str,
        metadata: PortfolioMetadata,
        repos: List[RepoData],
        evidence: Dict[str, Any],
        context: str = "enterprise",
        role: str = "senior",
        tier: str = "professional",
    ) -> str:
        """
        Generate AI prompt for portfolio analysis.

        Args:
            username: GitHub username
            metadata: Portfolio metadata
            repos: List of repository data
            evidence: Extracted evidence patterns
            context: Hiring context
            role: Role level for interview questions (junior, mid, senior)

        Returns:
            Complete AI prompt string
        """
        logger.info(f"Generating AI prompt for {username} (context: {context})")

        # Determine counts based on tier
        # Scale+ and Scale (enterprise) get more comprehensive analysis
        # Normalize tier to lowercase for comparison
        tier_lower = tier.lower() if tier else ""

        if tier_lower == "scale_plus":
            pattern_count = "10-12"
            observation_count = "10-12"
            recommendation_count = "10-12"
            indicator_count = "10-12"
            question_count = "10-12"
        elif tier_lower == "enterprise":
            # Scale tier gets same comprehensive counts as Scale+
            pattern_count = "10-12"
            observation_count = "10-12"
            recommendation_count = "10-12"
            indicator_count = "10-12"
            question_count = "10-12"
        else:
            # Growth and Starter get standard counts
            pattern_count = "8-10"
            observation_count = "6-8"
            recommendation_count = "6-8"
            indicator_count = "6-8"
            question_count = "8-10"

        # Prepare evidence for AI
        evidence_json = self.prepare_evidence_for_ai(
            username, metadata, repos, evidence
        )

        # Get context description
        context_description = self.get_context_description(context)

        # Get role-level guidance
        role_guidance = self._get_role_level_guidance(role)

        prompt = f"""You are a senior technical hiring consultant analyzing a developer's PUBLIC GitHub portfolio.

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

{context_description}

{role_guidance}

Public Portfolio Evidence (Pre-Analyzed): {json.dumps(evidence_json, indent=2)}

**IMPORTANT**: The evidence above includes:
- `portfolio_evolution_by_period`: Pre-analyzed time periods showing repo creation, technologies, and patterns over time
- `technology_evolution`: Technology adoption timeline showing when each tech was first used
- `quality_progression`: Quality improvement over time (testing, docs, project scale)
- `cross_repo_patterns`: Common patterns across repos (language consistency, domain focus)
- `substantial_repos_structured`: Top repos by commit count - USE THESE IN INTERVIEW QUESTIONS!
- `aggregated_quality_indicators.concept_repos`: List of concept/documentation-only repos (no primary_language) - IF THIS LIST EXISTS AND IS NOT EMPTY, you MUST create an evidence pattern called "Concept/Documentation Repositories" that explicitly lists these repos by name and notes they are README-only/documentation repos with NO implementation code.

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

3. EVIDENCE PATTERNS ({pattern_count} patterns) - **START HERE WITH RAW EVIDENCE**
   Each pattern as JSON with THREE fields:
   - "pattern": Name (e.g., "Testing in Public Repos", "Technology Adoption")
   - "evidence": Specific FACTUAL examples from public repos (NO JUDGMENTS - pure facts only with repo names, counts, dates)
   - "analysis": FACTUAL explanation of what this evidence shows (2-3 sentences, NO JUDGMENTS OR INFERENCES - only explain what the data demonstrates)

   REMOVED FIELDS (DO NOT INCLUDE):
   - ❌ NO "scope" field (already stated in top warning section - DRY principle)
   - ❌ NO "hiring_relevance" field (Context system already explains hiring relevance - DRY principle)

   THREE REQUIRED FIELDS - PURE FACTS ONLY:
   ✅ Pattern name + Evidence (with specific repo names, counts, dates) + Analysis (factual explanation)
   ✅ Example: {{
       "pattern": "Testing Adoption",
       "evidence": "Testing observed in 2/9 repos: 'koa' (Vue test files, 2020), 'TapIn' (Swift XCTest, 2021). 7/9 repos show no visible test files or testing frameworks in public commits.",
       "analysis": "Testing infrastructure is present in 22% of public repositories. The testing spans different technologies (Vue and Swift) and occurred across 2020-2021. The remaining 78% of public repos show no test files, which may reflect the nature of these projects (learning exercises, prototypes) or testing may exist in private company work not visible here."
   }}
   ✅ Example: {{
       "pattern": "Technology Timeline",
       "evidence": "TypeScript first seen 2019-02-08 in 'hornet', Python 2020-01-02 in 'chatbot2020', Swift 2021-07-10 in 'TapIn'. Each language used in 1-3 repos.",
       "analysis": "Public portfolio shows technology adoption spanning 3 years (2019-2021) across three different languages. Each technology appears in a limited number of public projects. This represents the timeline of public work only - professional experience with these technologies may predate or extend beyond these public repository timestamps."
   }}

   ANALYSIS FIELD RULES - CRITICAL:
   - State ONLY what the data factually demonstrates
   - NO assertions about skill level, capability, or quality
   - NO inferences about what developer "can" or "cannot" do
   - NO egregious inferences about project purpose (e.g., "passion project", "hobby project", "portfolio piece")
   - ALWAYS acknowledge when data limitations apply
   - Explain the numbers/patterns in plain language without judgment
   - 2-3 sentences maximum - keep it concise and factual
   - Minor comparative phrases like "rather than" or "instead of" are acceptable when comparing visible patterns

   ⛔ FORBIDDEN SPECULATION PHRASES IN ANALYSIS FIELD (EGREGIOUS ONLY):
   - "suggesting these may be passion/hobby/portfolio projects" - inferring project purpose
   - "passion project" or "hobby project" - cannot determine intent from code
   - "portfolio piece" - cannot determine purpose from code
   - "appears to be a passion/hobby project" - purpose inference
   - "lacks/demonstrates strong/weak/poor/excellent skill" - skill judgments

4. KEY OBSERVATIONS ({observation_count} observations as bullet points starting with -)
   Based on the EVIDENCE PATTERNS above, synthesize key insights:
   - Observable pattern in PUBLIC repositories with specific evidence
   - Scoped explicitly to "public repos" or "public work"
   - Include specific repo names, counts, dates

5. PUBLIC PORTFOLIO EVOLUTION (REQUIRED - MUST GENERATE 3-5 time periods in markdown format)
   **YOU MUST GENERATE THIS SECTION!**

   CRITICAL: This section is PURE FACTS ONLY - NO JUDGMENTS, NO ASSERTIONS, NO INTERPRETATIONS!

   Use `portfolio_evolution_by_period` data to generate time periods with the EXACT format below:

   ### 2023 (September-October)

   **Repos Created**: 3
   **Technologies**: Python
   **Total Commits**: 229 (avg 76/repo, median 3/repo)
   **Domain**: Data Science/Python
   **Largest Project**: 'Programmig_PYTHON_SoftUni' (223 commits, 391 KB, Python)
   **Code Quality**: Testing 0/3, README files 0/3
   **Community Recognition**: 7 stars total, 1 repo with 5+ stars

   *Note: All metrics from public repositories only. Private work not visible.*

   Calculate these metrics from the evidence data and format EXACTLY as shown above.

6. INTERVIEW QUESTIONS (REQUIRED - MUST GENERATE {question_count} questions in markdown format)
   **YOU MUST GENERATE THIS SECTION!**

   Ask about their ACTUAL WORK in SPECIFIC REPOS, using `substantial_repos_structured` and `aggregated_quality_indicators`.

   **FORMAT FOR EACH QUESTION** (FOLLOW THIS EXACTLY):
   ### Q[number]
   **[Your question about specific repo/code]**
   `category-name`
   💼 **Context**: [Business/hiring relevance - why this matters for {context} roles]
   📍 **Based on Evidence**: [Specific repo, commits, pattern from analysis]

   **Follow-up questions**:
   1. [Question 1]
   2. [Question 2]
   3. [Question 3]

   *Key Listening Points: [What to assess in their answer]*

7. POSITIVE INDICATORS (REQUIRED - MUST GENERATE {indicator_count} strengths as markdown list starting with -)
   **YOU MUST GENERATE THIS SECTION!**

   State FACTS about STRENGTHS visible in public repos.

8. AREAS TO EXPLORE (REQUIRED - MUST GENERATE {indicator_count} investigation areas as markdown list starting with -)
   **YOU MUST GENERATE THIS SECTION!**

   State FACTS about what's MISSING or UNCLEAR in public repos.

9. RECOMMENDATIONS ({recommendation_count} actionable items as markdown list starting with -)

10. QUALITY INDICATORS ({indicator_count} indicators)
    Each indicator as JSON:
    - "indicator": Name
    - "observation": What was observed IN PUBLIC REPOS
    - "scope": "public repositories only"
    - "implication": What this suggests (with caveats)

11. EVIDENCE QUALITY ASSESSMENT
    CRITICAL: Keep this section CONCISE. Each subsection should be 2-3 sentences maximum.

    **Portfolio Span:** [1-2 sentences about timeframe and repo creation dates]

    **Visibility Gaps:** [2-3 sentences listing what's NOT visible: testing, docs, CI/CD, collaboration, private work, professional experience]

    **What This Shows:** [2 sentences max: What IS visible in public repos]

    **What This Does NOT Show:** [2 sentences max: Private work, professional experience, complete skills]

    **Next Steps:**
    - [First recommendation - one clear action]
    - [Second recommendation - one clear action]
    - [Third recommendation - one clear action]
    - [Fourth recommendation - one clear action]

    IMPORTANT FORMATTING RULES:
    - Each labeled section (Portfolio Span, Visibility Gaps, etc.) must be separated by double line breaks (\n\n)
    - "Next Steps" MUST be formatted as a clean bullet list with each item on its own line starting with "-"
    - Keep each section to 2-3 sentences MAXIMUM
    - Be concise and direct - no lengthy explanations
    - Total section should be under 200 words
    - DO NOT include "END OF ANALYSIS" or any other closing markers
    - DO NOT add "---" separators or extra formatting

Remember:
- EVERY insight must be scoped to "public repositories"
- ALWAYS acknowledge data limitations
- NEVER infer complete skill level from public repos only
- Frame questions to probe BEYOND what's visible
- Emphasize: This is ONE data point, not complete assessment
- BE SPECIFIC: Use repo names, stars, commits, dates in EVERY evidence statement
"""

        return prompt

    def generate_question_prompt(
        self,
        username: str,
        metadata: PortfolioMetadata,
        repos: List[RepoData],
        evidence: Dict[str, Any],
        main_analysis_insights: Dict[str, Any],
        context: str = "enterprise",
        role: str = "senior",
        tier: str = "professional",
    ) -> str:
        """
        Generate AI prompt for Phase 2 interview question generation (multi-model approach).

        Args:
            username: GitHub username
            metadata: Portfolio metadata
            repos: List of repository data
            evidence: Extracted evidence patterns
            main_analysis_insights: Results from Phase 1 main analysis
            context: Hiring context
            role: Role level for interview questions (junior, mid, senior)

        Returns:
            Complete AI prompt string for question generation
        """
        logger.info(
            f"Generating Phase 2 question prompt for {username} (context: {context}, role: {role})"
        )

        # Determine question count based on tier
        if tier == "scale_plus":
            question_count = "10-12"
        else:
            question_count = "8-10"

        # Prepare evidence for AI
        evidence_json = self.prepare_evidence_for_ai(
            username, metadata, repos, evidence
        )

        # Get context description and role guidance
        context_description = self.get_context_description(context)
        role_guidance = self._get_role_level_guidance(role)

        # Extract key insights from Phase 1 to provide context
        analysis_context = {
            "username": username,
            "evidence_patterns": main_analysis_insights.get("evidence_patterns", []),
            "key_observations": main_analysis_insights.get("key_observations", []),
            "areas_to_explore": main_analysis_insights.get("areas_to_explore", []),
            "substantial_repos": evidence_json.get("substantial_repos_structured", []),
            "portfolio_metadata": evidence_json.get("public_portfolio_metadata", {}),
        }

        prompt = f"""You are a senior technical hiring consultant generating INTERVIEW QUESTIONS for a developer portfolio analysis.

⚠️ CRITICAL: THIS IS THE QUESTION GENERATION PHASE ONLY
The main analysis has already been completed. Your job is to generate {question_count} DEEP, INSIGHTFUL interview questions.

{context_description}

{role_guidance}

Analysis Context (from main analysis): {json.dumps(analysis_context, indent=2)}

GENERATE {question_count} INTERVIEW QUESTIONS (REQUIRED - markdown format)

**FORMAT FOR EACH QUESTION** (FOLLOW THIS EXACTLY):
### Q[number]
**[Your question about specific repo/code]**
`category-name`
💼 **Context**: [Business/hiring relevance - why this matters for {context} roles]
📍 **Based on Evidence**: [Specific repo, commits, pattern from analysis]

**Follow-up questions**:
1. [Question 1]
2. [Question 2]
3. [Question 3]

**Key Listening Points**:
*[What to assess in their answer]*

**CATEGORY OPTIONS** (PICK ONE):
- `architecture` - System design, architectural decisions
- `code-quality` - Code organization, testing, maintainability
- `problem-solving` - Technical problem-solving approach
- `learning-agility` - Learning new technologies
- `collaboration` - Team work, code review
- `devops` - Deployment, CI/CD
- `security` - Security practices
- `performance` - Optimization, scalability
- `database` - Data modeling, queries
- `testing` - Testing strategy, TDD

CRITICAL REQUIREMENTS:
1. **Reference SPECIFIC repos** from substantial_repos in analysis context
2. **Use actual evidence** from evidence_patterns and key_observations
3. **Context must explain WHY question matters** for {context} roles (not repeat evidence)
4. **Make questions PROBING** - assume they HAVE experience, just not visible in public repos
5. **Avoid generic questions** - tie to actual repos/patterns from their portfolio

⚠️ **NO LOADED OR ACCUSATORY QUESTIONS**:
- ❌ DO NOT frame questions as "Why isn't X visible?" or "What have you been doing?"
- ❌ DO NOT imply gaps in public activity are negative or need justification
- ❌ DO NOT ask defensive questions like "Tell me why you don't have..."
- ✅ DO frame questions as INVITATIONS to share experience: "Tell me about..." or "Walk me through..."
- ✅ DO assume positive intent - most professional work is in private repositories
- ✅ DO keep questions BROAD and OPEN-ENDED, not specific accusations

**USE substantial_repos AND evidence_patterns TO GENERATE {question_count} SPECIFIC, DEEP QUESTIONS!**

Generate interview questions now:
"""

        return prompt

    def format_markdown_report(
        self,
        username: str,
        result: Dict[str, Any],
        metadata: PortfolioMetadata,
        fetch_time: float,
        analysis_time: float,
        context: str = "enterprise",
        api_calls: int = 0,
    ) -> str:
        """
        Format portfolio analysis result as markdown report.

        Args:
            username: GitHub username
            result: AI-generated analysis result
            metadata: Portfolio metadata
            fetch_time: Time spent fetching data (seconds)
            analysis_time: Time spent on analysis (seconds)
            context: Hiring context
            api_calls: Number of API calls made

        Returns:
            Formatted markdown report
        """
        logger.info(f"Formatting markdown report for {username}")

        report = f"""# Developer Portfolio Analysis - {username}

## 📊 Analysis Metadata
- **Total Public Repos**: {metadata.total_public_repos}
- **Repos Analyzed**: {result.get("repos_analyzed", 0)}
- **Repos Skipped**: {result.get("repos_skipped", 0)}
- **Fetch Time**: {fetch_time:.2f}s
- **Analysis Time**: {analysis_time:.2f}s
- **API Calls**: {api_calls}
- **Context**: {context}

---

## ⚠️ CRITICAL DATA LIMITATIONS

**THIS ANALYSIS EXAMINES PUBLIC REPOSITORIES ONLY**

{result.get("data_limitations_warning", "PUBLIC REPOS ONLY")}

**What this means:**
- ❌ Private company work is NOT visible
- ❌ Professional experience may be significantly greater
- ❌ Technology experience may predate public repos
- ❌ Gaps in public activity likely represent private work
- ✅ This is ONE data point for hiring decisions

---

## 🏢 Executive Summary

{result.get("executive_summary", "No summary available")}

### Analysis Confidence Level
{result.get("confidence_explanation", "No confidence assessment available")}

---

## 💡 Key Observations (Public Repos Only)

"""

        # Key observations
        for i, obs in enumerate(result.get("key_observations", []), 1):
            report += f"{i}. {obs}\n"

        report += "\n---\n\n## 📈 Public Portfolio Evolution\n\n"

        # Portfolio evolution periods
        for period in result.get("public_portfolio_evolution", []):
            if isinstance(period, dict):
                report += f"### {period.get('period', 'Unknown Period')}\n\n"
                report += (
                    f"**Repos Created**: {period.get('public_repos_created', 0)}\n"
                )

                # Technologies
                techs = period.get("technologies_observed", [])
                if isinstance(techs, list):
                    report += f"**Technologies**: {', '.join(techs)}\n"
                else:
                    report += f"**Technologies**: {techs}\n"

                # Add metrics if present
                if period.get("total_commits"):
                    report += f"**Total Commits**: {period.get('total_commits')}\n"
                if period.get("domain_focus"):
                    report += f"**Domain**: {period.get('domain_focus')}\n"
                if period.get("largest_project"):
                    report += f"**Largest Project**: {period.get('largest_project')}\n"
                if period.get("code_quality"):
                    report += f"**Code Quality**: {period.get('code_quality')}\n"
                if period.get("community_recognition"):
                    report += f"**Community Recognition**: {period.get('community_recognition')}\n"

                report += "\n"

        report += "*Note: All metrics from public repositories only. Private work not visible.*\n\n"
        report += "\n---\n\n## 🔍 Evidence Patterns\n\n"

        # Evidence patterns
        for pattern in result.get("evidence_patterns", []):
            if isinstance(pattern, dict):
                report += f"### {pattern.get('pattern', 'Unknown Pattern')}\n\n"
                report += "**Evidence Found**\n\n"
                report += f"{pattern.get('evidence', 'N/A')}\n\n"
                # Add analysis section if available (AI-generated insight)
                if pattern.get("analysis"):
                    report += "**Analysis**\n\n"
                    report += f"{pattern.get('analysis')}\n\n"

        report += "\n---\n\n## 💬 Interview Questions\n\n"

        # Interview questions
        for i, question in enumerate(result.get("interview_questions", []), 1):
            if isinstance(question, dict):
                report += f"### Q{i}: {question.get('question', 'N/A')}\n\n"
                report += f"**Category**: `{question.get('category', 'general')}`\n"
                report += f"**Context**: {question.get('context', 'N/A')}\n"
                if question.get("evidence"):
                    report += f"**📍 Based on Evidence**: {question.get('evidence')}\n"
                report += "\n"

                # Follow-up questions
                follow_ups = question.get("follow_up_questions", [])
                if follow_ups:
                    report += "**Follow-up Questions**:\n"
                    for follow_up in follow_ups:
                        report += f"- {follow_up}\n"
                    report += "\n"

                # Key listening points
                listening_points = question.get("key_listening_points", "")
                if listening_points:
                    report += "**Key Listening Points**:\n"
                    report += f"- {listening_points}\n\n"

        report += "\n---\n\n## ✨ Positive Indicators\n\n"

        # Positive indicators
        for indicator in result.get("positive_indicators", []):
            report += f"- {indicator}\n"

        report += "\n---\n\n## 🔍 Areas to Explore\n\n"

        # Areas to explore
        for area in result.get("areas_to_explore", []):
            report += f"- {area}\n"

        report += "\n---\n\n## ✅ Recommendations\n\n"

        # Recommendations
        for i, rec in enumerate(result.get("recommendations", []), 1):
            report += f"{i}. {rec}\n"

        report += "\n---\n\n## 📈 Quality Indicators (Public Work Only)\n\n"

        # Quality indicators
        for indicator in result.get("quality_indicators", []):
            if isinstance(indicator, dict):
                report += f"### {indicator.get('indicator', 'N/A')}\n\n"
                report += f"**Observation**: {indicator.get('observation', 'N/A')}\n"
                report += (
                    f"**Scope**: {indicator.get('scope', 'public repositories only')}\n"
                )
                report += f"**Implication**: {indicator.get('implication', 'N/A')}\n\n"

        return report
