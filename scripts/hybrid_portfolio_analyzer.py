#!/usr/bin/env python3
"""
Hybrid Multi-Model Portfolio Analyzer (Experimental).

Uses two models for optimal balance:
- Sonnet 4 (claude-sonnet-4-20250514): Main analysis (fast, neutral, fact-driven)
- Sonnet 4.5 (claude-sonnet-4-5-20250929): Question generation (deep, insightful)

Performance target: ~90s, ~$0.09, best quality
"""

import json
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# noqa directives for imports after sys.path modification
from dotenv import load_dotenv  # noqa: E402

# Import from existing script
from validate_developer_portfolio import (  # noqa: E402
    DeveloperPortfolioAnalyzer,
    PortfolioEvidence,
    RepoMetadata,
)

from src.github_analyzer.utils.config import get_config  # noqa: E402
from src.github_analyzer.utils.logging import get_logger  # noqa: E402

load_dotenv()
logger = get_logger(__name__)


class HybridPortfolioAnalyzer(DeveloperPortfolioAnalyzer):
    """Hybrid analyzer using Sonnet 4 for main analysis, Sonnet 4.5 for questions."""

    def __init__(self, github_token: str, anthropic_api_key: str):
        """Initialize with API credentials and dual models."""
        super().__init__(github_token, anthropic_api_key)

        # Override models - we'll use both
        self.main_model = "claude-sonnet-4-20250514"  # Fast, neutral
        self.question_model = "claude-sonnet-4-5-20250929"  # Deep insights
        self.max_tokens = 16000

        logger.info(
            f"Hybrid analyzer initialized: main={self.main_model}, questions={self.question_model}"
        )

    def generate_main_analysis_prompt(
        self,
        repo_data: Dict[str, Any],
        evidence: PortfolioEvidence,
        filtered_repos: List[RepoMetadata],
        context: str = "enterprise",
    ) -> str:
        """Generate prompt for MAIN ANALYSIS ONLY (no questions) - Pure facts."""

        # Prepare evidence JSON (same as original)
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
            "portfolio_evolution_by_period": evidence.portfolio_evolution_periods,
            "aggregated_technologies": evidence.aggregated_technologies,
            "aggregated_quality_indicators": evidence.aggregated_quality_indicators,
            "substantial_repos_structured": evidence.substantial_repos_structured,
            "public_repos_timeline_sample": evidence.public_repos_timeline[:10],
            "technology_adoption_timeline": evidence.technology_adoption_in_public[:10],
            "public_work_quality_indicators": evidence.public_work_quality_indicators,
            "timeline_gaps": evidence.timeline_gaps,
            "technologies_summary": evidence.cross_technology_evidence,
            "substantial_repos": evidence.repo_substance_indicators[:8],
            "cross_repo_patterns": evidence.cross_repo_patterns,
            "technology_evolution": evidence.technology_evolution_evidence,
            "quality_progression": evidence.quality_progression_evidence,
        }

        return f"""You are a senior technical hiring consultant analyzing a developer's PUBLIC GitHub portfolio.

⚠️ CRITICAL: THIS IS THE MAIN ANALYSIS PHASE - DO NOT GENERATE INTERVIEW QUESTIONS
Interview questions will be generated separately. Focus ONLY on evidence-based analysis.

⚠️ CRITICAL DATA LIMITATIONS WARNING:

THIS ANALYSIS EXAMINES **PUBLIC REPOSITORIES ONLY**.

1. **Private Work is Invisible**: Most professional developers work primarily in private company repositories.
2. **Timeline Gaps ≠ Inactivity**: Gaps in public activity DO NOT indicate no professional work.
3. **Technology Experience**: "First public use of X: 2021" ≠ "Learned X in 2021".
4. **No Complete Picture**: We analyze public repos only.

TERMINOLOGY REQUIREMENTS (CRITICAL - FOLLOW EXACTLY):
- Use "public portfolio" NOT "skill level"
- Use "observable in public repos" NOT "developer capabilities"
- Use "first public use of X: DATE" NOT "learned X in DATE"
- Use "not observed in public repos" NOT "no experience with X"
- State FACTS ONLY - no superlatives like "extremely limited", "complete absence", "minimal"

⚠️ CRITICAL: PURE FACTS ONLY - NO JUDGMENTS, NO INFERENCES
- ❌ DO NOT use: "extremely limited", "minimal", "complete absence", "likely", "suggests professional"
- ✅ DO use: "3 repos", "0 test files", "229 commits", "first observed 2023-09-20"
- ❌ DO NOT infer intent: "appears to be learning exercises", "suggests coursework"
- ✅ DO state facts: "Repo name 'Programmig_PYTHON_SoftUni' contains 223 commits"

{self._get_context_description(context)}

Public Portfolio Evidence (Pre-Analyzed): {json.dumps(evidence_json, indent=2)}

RESPONSE STRUCTURE (YOU MUST GENERATE ALL SECTIONS BELOW - NO QUESTIONS):

1. EXECUTIVE SUMMARY (2-3 sentences)
   - Focus on observable public work patterns (FACTS ONLY)
   - Note timeline span and repo count (NUMBERS ONLY)
   - Highlight key technologies in public repos (LIST ONLY)
   - MUST acknowledge data limitations (REQUIRED)
   - NO superlatives: avoid "extremely", "minimal", "complete", "significant"

2. DATA LIMITATIONS WARNING (2-3 sentences)
   - Remind that this is PUBLIC REPOS ONLY
   - Note what is NOT visible (private work, company repos)
   - Emphasize this is ONE data point for hiring decision

3. EVIDENCE PATTERNS (8-10 patterns) - **PURE FACTS ONLY**
   Each pattern as JSON:
   - "pattern": Name (e.g., "Testing in Public Repos", "Technology Adoption")
   - "evidence": Specific FACTUAL examples with repo names, counts, dates (NO JUDGMENTS)

   Example: {{"pattern": "Testing Adoption", "evidence": "0/3 repos contain test files. No testing frameworks detected in 'learning-python-course' (223 commits), 'guess-a-number' (3 commits), or 'random-sentence-generator' (3 commits)."}}

4. KEY OBSERVATIONS (6-8 observations as bullet points starting with -)
   Based on EVIDENCE PATTERNS above, synthesize key insights:
   - Observable pattern in PUBLIC repositories with specific evidence (FACTS ONLY)
   - Include specific repo names, counts, dates
   - NO inferences: avoid "likely", "suggests", "appears to be", "probably"
   - NO judgments: avoid "limited", "minimal", "poor", "weak", "strong", "excellent"

   FORMAT AS MARKDOWN LIST:
   - Python observed in 3/3 public repos. First public Python use: 2023-09-20 in 'Programmig_PYTHON_SoftUni'.
   - 0/3 repos contain test files. No testing frameworks visible in public repositories.
   - Public activity observed 2023-09-20 to 2023-10-13 (22 days). No public commits before or after this window.

5. PUBLIC PORTFOLIO EVOLUTION (REQUIRED - MUST GENERATE 3-5 time periods in markdown format)

   **CRITICAL: This section is PURE FACTS ONLY - NO JUDGMENTS, NO ASSERTIONS!**

   Format as markdown with PURE FACTS ONLY:

   ### 2023 (September-October)

   **Repos Created**: 3
   **Technologies**: Python
   **Total Commits**: 229 (avg 76/repo, median 3/repo)
   **Domain**: Data Science/Python
   **Largest Project**: 'Programmig_PYTHON_SoftUni' (223 commits, 391 KB, Python)
   **Code Quality**: Testing 0/3, README files 0/3
   **Community Recognition**: 7 stars total, 1 repo with 5+ stars

   *Note: All metrics from public repositories only. Private work not visible.*

6. POSITIVE INDICATORS (REQUIRED - MUST GENERATE 5-7 strengths as markdown list starting with -)

   State FACTS about STRENGTHS visible in public repos. Pure observations, no exaggeration.

   GOOD EXAMPLES (pure factual strengths):
   - 229 total commits across 3 public repos spanning 22 days
   - 'Programmig_PYTHON_SoftUni' received 5 stars, 'GuessANumber' received 2 stars
   - Python used in 3/3 repos (100% language consistency)
   - 'Programmig_PYTHON_SoftUni' contains 223 commits and 391 KB of code

   BAD EXAMPLES (DO NOT generate these):
   - ❌ "Excellent coding skills" (Vague, judgmental)
   - ❌ "Quick learner" (Behavioral assumption)
   - ❌ "Strong commitment" (Psychology)

7. AREAS TO EXPLORE (REQUIRED - MUST GENERATE 5-7 investigation areas as markdown list starting with -)

   State FACTS about what's MISSING or UNCLEAR in public repos.

   GOOD EXAMPLES (pure facts about gaps):
   - 0/3 repos contain test files or testing frameworks
   - 0/3 repos have README files, descriptions, or documentation
   - Python observed in public repos but no frameworks (Django/Flask/FastAPI) detected
   - Public activity spans only 22 days (2023-09-20 to 2023-10-13)

   BAD EXAMPLES (DO NOT generate these):
   - ❌ "Explore testing philosophy" (Behavioral inference)
   - ❌ "Understand learning approach" (Psychology)

8. RECOMMENDATIONS (5-6 actionable items as markdown list starting with -)

   FORMAT AS MARKDOWN LIST:
   - Verify complete Python experience timeline including professional work not visible in public repos
   - Explore testing practices - 0/3 public repos contain tests, professional standards may differ
   - Clarify employment history and private repository work to understand complete professional background

9. QUALITY INDICATORS (6-8 indicators)
   Each indicator as JSON:
   - "indicator": Name
   - "observation": What was observed IN PUBLIC REPOS (FACTS ONLY)
   - "scope": "public repositories only"
   - "implication": What this suggests (with caveats, NO JUDGMENTS)

10. EVIDENCE QUALITY ASSESSMENT (2-3 paragraphs)
   Assess the quality and limitations of the evidence:
   - Based on: Number of public repos, time span, commit counts
   - Limitations: Private repos not visible, professional work unknown
   - Confidence level: What we can/cannot conclude from public repos alone

⚠️ CRITICAL REMINDERS:
- EVERY statement must be scoped to "public repositories"
- NEVER infer complete skill level from public repos only
- STATE PURE FACTS with numbers/dates/repo names
- NO superlatives: avoid "extremely", "minimal", "significant", "strong", "weak"
- NO inferences without caveat: avoid "likely", "suggests", "appears", "probably"

Remember:
- This is the MAIN ANALYSIS phase - DO NOT generate interview questions
- Questions will be generated separately with deeper context
- Focus on NEUTRAL, FACT-DRIVEN evidence presentation
"""

    def _get_role_specific_question_guidance(self, role_level: str) -> str:
        """Generate role-specific question guidance for AI."""

        role_descriptions = {
            "junior": {
                "years": "0-2 years",
                "focus": "Fundamentals, basic implementation, learning approach, debugging basics",
                "avoid": "Architecture decisions, scaling, distributed systems, advanced patterns",
                "example": "Walk me through how you debugged an issue in this code",
                "complexity": "Surface-level technical understanding",
            },
            "mid": {
                "years": "2-5 years",
                "focus": "Implementation decisions, testing strategies, code quality, problem-solving",
                "avoid": "Org-wide architecture, executive decisions, multi-team coordination",
                "example": "How did you decide between approach A and B for this feature?",
                "complexity": "Moderate technical depth with practical application",
            },
            "senior": {
                "years": "5-8 years",
                "focus": "Architecture, scalability, technical leadership, mentorship, system design",
                "avoid": "Implementation minutiae, junior-level basics",
                "example": "How would you scale this system to handle 10x traffic?",
                "complexity": "Deep technical expertise with leadership thinking",
            },
            "staff": {
                "years": "8+ years",
                "focus": "Technical strategy, cross-team impact, organizational standards, system architecture",
                "avoid": "Single-team concerns, implementation details, basic concepts",
                "example": "How would you design a technical strategy for migrating 50 services?",
                "complexity": "Strategic technical leadership across multiple teams",
            },
        }

        role_info = role_descriptions.get(role_level, role_descriptions["senior"])

        return f"""
🎯 **ROLE LEVEL CONTEXT**: {role_level.upper()} ({role_info["years"]})

**CRITICAL: ADJUST QUESTION COMPLEXITY FOR {role_level.upper()} ROLE**

**{role_level.upper()}-Level Question Requirements**:
- **Focus on**: {role_info["focus"]}
- **Avoid**: {role_info["avoid"]}
- **Complexity Level**: {role_info["complexity"]}
- **Example Question Style**: "{role_info["example"]}"

**ENFORCEMENT RULES**:
{"- DO NOT ask about architecture, scaling, or distributed systems (too advanced)" if role_level == "junior" else ""}
{"- DO NOT ask about org-wide strategy or multi-team coordination (too advanced)" if role_level == "mid" else ""}
{"- DO NOT ask about implementation details or basic concepts (too junior)" if role_level in ["senior", "staff"] else ""}
{"- DO ask about technical strategy and cross-organizational impact" if role_level == "staff" else ""}
- Questions MUST match {role_level} level expectations
- Assume candidate has {role_info["years"]} experience level

⚠️ **CRITICAL: NO LOADED OR ACCUSATORY QUESTIONS**
- ❌ DO NOT frame questions as "Why isn't X visible?" or "What have you been doing?"
- ❌ DO NOT imply gaps in public activity are negative or need justification
- ❌ DO NOT ask defensive questions like "Tell me why you don't have..."
- ✅ DO frame questions as INVITATIONS to share experience: "Tell me about..." or "Walk me through..."
- ✅ DO assume positive intent - most professional work is in private repositories
- ✅ DO keep questions BROAD and OPEN-ENDED, not specific accusations
- ✅ DO acknowledge that public repos are ONE data point, not complete picture

**TONE GUIDANCE**:
- Junior: Encouraging, supportive, focused on learning journey
- Mid: Neutral, invitational, assumes they have professional experience
- Senior: Respectful, collaborative, assumes extensive private/professional work

**BAD QUESTION EXAMPLES (NEVER GENERATE THESE)**:
- ❌ "Your public activity stopped in 2023. Why isn't your recent work visible?"
- ❌ "You have no tests. Why didn't you write tests?"
- ❌ "Your repos lack documentation. What's your excuse?"

**GOOD QUESTION EXAMPLES (GENERATE THESE INSTEAD)**:
- ✅ "Tell me about your development journey and current work"
- ✅ "Walk me through your testing approach in professional projects"
- ✅ "How do you handle documentation in team environments?"
"""

    def generate_question_prompt(
        self,
        repo_data: Dict[str, Any],
        evidence: PortfolioEvidence,
        main_analysis: Dict[str, Any],
        context: str = "enterprise",
        role_level: str = "senior",
    ) -> str:
        """Generate prompt for QUESTION GENERATION ONLY - Deep, insightful."""

        # Pass main analysis results as context
        analysis_context = {
            "username": repo_data["username"],
            "evidence_patterns": main_analysis.get("evidence_patterns", []),
            "key_observations": main_analysis.get("key_observations", []),
            "areas_to_explore": main_analysis.get("areas_to_explore", []),
            "substantial_repos": evidence.substantial_repos_structured,
            "aggregated_code_patterns": evidence.aggregated_code_patterns,
            "aggregated_quality_indicators": evidence.aggregated_quality_indicators,
            "portfolio_metadata": {
                "total_public_repos": repo_data["total_public_repos"],
                "repos_analyzed": len(main_analysis.get("repos_analyzed", [])),
                "public_career_span_days": main_analysis.get("career_span_days", 0),
            },
        }

        # Get role-specific guidance
        role_guidance = self._get_role_specific_question_guidance(role_level)

        return f"""You are a senior technical hiring consultant generating INTERVIEW QUESTIONS for a developer portfolio analysis.

⚠️ CRITICAL: THIS IS THE QUESTION GENERATION PHASE ONLY
The main analysis has already been completed. Your job is to generate 8-10 DEEP, INSIGHTFUL interview questions.

{self._get_context_description(context)}

{role_guidance}

Analysis Context (from main analysis): {json.dumps(analysis_context, indent=2)}

GENERATE 8-10 INTERVIEW QUESTIONS (REQUIRED - markdown format)

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
1. **Reference SPECIFIC repos** from substantial_repos_structured
2. **Use actual evidence** from evidence_patterns and key_observations
3. **Context must explain WHY question matters** for {context} roles (not repeat evidence)
4. **Make questions PROBING** - assume they HAVE experience, just not visible
5. **Avoid generic questions** - tie to actual repos/patterns

GOOD QUESTION EXAMPLE:
### Q1
**Your 'Programmig_PYTHON_SoftUni' repository contains 223 commits over a 22-day period. Walk me through the architecture of the most complex component and how you structured the code for maintainability.**
`architecture`
💼 **Context**: Enterprise applications require thoughtful code organization that balances learning objectives with professional development practices. Understanding architectural thinking reveals problem-solving approach.
📍 **Based on Evidence**: 'Programmig_PYTHON_SoftUni' (223 commits, 391 KB, Python). Represents 97% of public commit activity.

**Follow-up questions**:
1. How did you decide on the project structure and file organization?
2. What design patterns did you apply, and why?
3. How would you refactor this for a production environment?

**Key Listening Points**:
*Assess understanding of code organization, separation of concerns, ability to think beyond learning exercises toward production-ready architecture.*

BAD QUESTION EXAMPLE (DO NOT generate):
### Q1
**Tell me about your Python experience.**
`general`
💼 **Context**: We need Python developers.
📍 **Based on Evidence**: Python repos.

**USE substantial_repos_structured AND evidence_patterns TO GENERATE 8-10 SPECIFIC, DEEP QUESTIONS!**

Generate interview questions now:
"""

    def analyze_with_hybrid_approach(
        self,
        repo_data: Dict[str, Any],
        evidence: PortfolioEvidence,
        filtered_repos: List[RepoMetadata],
        context: str = "enterprise",
        role_level: str = "senior",
    ) -> Dict[str, Any]:
        """Analyze using hybrid approach: Sonnet 4 main + Sonnet 4.5 questions."""
        logger.info(
            f"Starting hybrid analysis: main={self.main_model}, questions={self.question_model}, role={role_level}"
        )

        # PHASE 1: Main Analysis with Sonnet 4 (fast, neutral)
        logger.info("PHASE 1: Running main analysis with Sonnet 4...")
        phase1_start = time.time()

        main_prompt = self.generate_main_analysis_prompt(
            repo_data, evidence, filtered_repos, context
        )

        logger.info(
            f"Main analysis prompt: {len(main_prompt)} chars (~{len(main_prompt) // 4} tokens)"
        )

        try:
            main_response = self.anthropic_client.messages.create(
                model=self.main_model,
                max_tokens=self.max_tokens,
                temperature=0.3,
                messages=[{"role": "user", "content": main_prompt}],
            )

            main_content = (
                main_response.content[0].text if main_response.content else ""
            )
            main_input_tokens = main_response.usage.input_tokens
            main_output_tokens = main_response.usage.output_tokens
            main_cost = (
                main_input_tokens * 3.0 + main_output_tokens * 15.0
            ) / 1_000_000

            phase1_duration = time.time() - phase1_start

            logger.info(
                f"PHASE 1 complete: {phase1_duration:.2f}s, {main_input_tokens + main_output_tokens} tokens, ${main_cost:.4f}"
            )

            # Parse main analysis
            main_analysis = self.parse_ai_response(
                main_content, repo_data, filtered_repos
            )

        except Exception as e:
            logger.error(f"Phase 1 (main analysis) failed: {e}")
            raise

        # PHASE 2: Question Generation with Sonnet 4.5 (deep, insightful)
        logger.info("PHASE 2: Running question generation with Sonnet 4.5...")
        phase2_start = time.time()

        # Convert main_analysis to dict for context
        main_analysis_dict = {
            "evidence_patterns": main_analysis.evidence_patterns,
            "key_observations": main_analysis.key_observations,
            "areas_to_explore": main_analysis.areas_to_explore,
            "repos_analyzed": filtered_repos,
            "career_span_days": main_analysis.career_span_days,
        }

        question_prompt = self.generate_question_prompt(
            repo_data, evidence, main_analysis_dict, context, role_level
        )

        logger.info(
            f"Question prompt: {len(question_prompt)} chars (~{len(question_prompt) // 4} tokens)"
        )

        try:
            question_response = self.anthropic_client.messages.create(
                model=self.question_model,
                max_tokens=self.max_tokens,
                temperature=0.3,
                messages=[{"role": "user", "content": question_prompt}],
            )

            question_content = (
                question_response.content[0].text if question_response.content else ""
            )
            question_input_tokens = question_response.usage.input_tokens
            question_output_tokens = question_response.usage.output_tokens
            question_cost = (
                question_input_tokens * 3.0 + question_output_tokens * 15.0
            ) / 1_000_000

            phase2_duration = time.time() - phase2_start

            logger.info(
                f"PHASE 2 complete: {phase2_duration:.2f}s, {question_input_tokens + question_output_tokens} tokens, ${question_cost:.4f}"
            )

            # Parse questions from Sonnet 4.5 response
            questions = self.parse_questions_from_response(question_content)

        except Exception as e:
            logger.error(f"Phase 2 (question generation) failed: {e}")
            # Continue with empty questions rather than fail entire analysis
            questions = []
            question_input_tokens = 0
            question_output_tokens = 0
            question_cost = 0.0
            phase2_duration = 0.0

        # MERGE: Combine results
        total_duration = phase1_duration + phase2_duration
        total_tokens = (
            main_input_tokens
            + main_output_tokens
            + question_input_tokens
            + question_output_tokens
        )
        total_cost = main_cost + question_cost

        logger.info(
            f"Hybrid analysis complete: {total_duration:.2f}s, {total_tokens} tokens, ${total_cost:.4f}"
        )

        # Update main_analysis with Sonnet 4.5 questions
        main_analysis.interview_questions = questions
        main_analysis.ai_tokens_used = total_tokens
        main_analysis.ai_cost = total_cost

        # Return combined metrics
        return {
            "result": main_analysis,
            "metrics": {
                "phase1_duration": phase1_duration,
                "phase1_tokens": main_input_tokens + main_output_tokens,
                "phase1_cost": main_cost,
                "phase1_model": self.main_model,
                "phase2_duration": phase2_duration,
                "phase2_tokens": question_input_tokens + question_output_tokens,
                "phase2_cost": question_cost,
                "phase2_model": self.question_model,
                "total_duration": total_duration,
                "total_tokens": total_tokens,
                "total_cost": total_cost,
            },
        }

    def parse_questions_from_response(self, content: str) -> List[Dict[str, Any]]:
        """Parse interview questions from Sonnet 4.5 response."""
        questions = []
        lines = content.split("\n")
        current_question = None

        for line in lines:
            if line.strip().startswith("### Q"):
                if current_question:
                    questions.append(current_question)
                current_question = {
                    "question": "",
                    "category": "",
                    "evidence": "",
                    "follow_up_questions": [],
                    "key_listening_points": "",
                    "context": "",
                }
            elif (
                current_question
                and line.strip().startswith("**")
                and not line.strip().startswith("**Based on")
                and not line.strip().startswith("**Follow-up")
                and not line.strip().startswith("**Key Listening")
            ):
                # Question text
                question_text = line.strip().replace("**", "")
                if not current_question["question"]:
                    current_question["question"] = question_text
            elif current_question and "**Context**" in line:
                context_text = (
                    line.split(":")[-1].strip() if ":" in line else line.strip()
                )
                context_text = (
                    context_text.replace("💼", "").replace("**Context**", "").strip()
                )
                current_question["context"] = context_text
            elif current_question and "Based on Evidence" in line:
                evidence = line.split(":")[-1].strip() if ":" in line else line.strip()
                evidence = (
                    evidence.replace("📍", "")
                    .replace("**Based on Evidence**", "")
                    .strip()
                )
                current_question["evidence"] = evidence
            elif (
                current_question
                and line.strip().startswith("`")
                and line.strip().endswith("`")
            ):
                category = line.strip().replace("`", "")
                current_question["category"] = category
            elif (
                current_question
                and line.strip()
                and line.strip()[0].isdigit()
                and "." in line
            ):
                # Follow-up question
                import re

                follow_up = re.sub(r"^\d+\.\s*", "", line.strip())
                current_question["follow_up_questions"].append(follow_up)
            elif (
                current_question
                and line.strip().startswith("*")
                and line.strip().endswith("*")
                and not line.strip().startswith("**")
            ):
                # Key listening points
                listening_point = line.strip().replace("*", "")
                current_question["key_listening_points"] = listening_point

        if current_question:
            questions.append(current_question)

        return questions


def main() -> None:
    """Test hybrid analyzer."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Test hybrid portfolio analyzer (Sonnet 4 + Sonnet 4.5)"
    )
    parser.add_argument("username", help="GitHub username to analyze")
    parser.add_argument(
        "--context",
        choices=["startup", "enterprise", "agency", "open_source"],
        default="enterprise",
        help="Hiring context (default: enterprise)",
    )
    parser.add_argument(
        "--role",
        choices=["junior", "mid", "senior"],
        default="senior",
        help="Role level for question generation (default: senior)",
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

    analyzer = HybridPortfolioAnalyzer(github_token, anthropic_api_key)

    # Create output directory
    output_dir = "developer_portfolio_validation"
    os.makedirs(output_dir, exist_ok=True)

    username = args.username
    logger.info(f"\n{'=' * 60}")
    logger.info(f"Hybrid Portfolio Analysis for: {username}")
    logger.info(f"{'=' * 60}")

    # Fetch repos
    start_time = time.time()
    repo_data = analyzer.fetch_developer_repos_graphql(username, max_repos=100)

    if not repo_data or not repo_data.get("repos"):
        logger.warning(f"No repo data found for {username}")
        sys.exit(1)

    # Filter repos
    filtered_repos, skip_counts, skipped_repos = analyzer.filter_repos(
        repo_data["repos"], include_forks=False
    )

    if not filtered_repos:
        logger.warning(f"No repos to analyze for {username} after filtering")
        sys.exit(1)

    # Extract evidence
    evidence = analyzer.extract_portfolio_evidence(filtered_repos)

    # Analyze with HYBRID approach
    hybrid_result = analyzer.analyze_with_hybrid_approach(
        repo_data, evidence, filtered_repos, args.context, args.role
    )

    result = hybrid_result["result"]
    metrics = hybrid_result["metrics"]

    # Add metadata
    result.skip_breakdown = skip_counts
    result.api_calls = repo_data.get("api_calls", 0)
    result.analysis_duration_seconds = round(time.time() - start_time, 2)

    # Format report
    markdown_report = analyzer.format_markdown_report(result)

    # Add hybrid metrics section to report
    hybrid_metrics = f"""

---

## 🔬 Hybrid Model Performance Metrics

### Model Strategy: Dual-Model Approach
- **Phase 1 (Main Analysis)**: {metrics["phase1_model"]}
- **Phase 2 (Question Generation)**: {metrics["phase2_model"]}

### Performance Breakdown:
- **Phase 1 Time**: {metrics["phase1_duration"]:.2f}s
- **Phase 1 Tokens**: {metrics["phase1_tokens"]:,}
- **Phase 1 Cost**: ${metrics["phase1_cost"]:.4f}

- **Phase 2 Time**: {metrics["phase2_duration"]:.2f}s
- **Phase 2 Tokens**: {metrics["phase2_tokens"]:,}
- **Phase 2 Cost**: ${metrics["phase2_cost"]:.4f}

- **Total Time**: {metrics["total_duration"]:.2f}s
- **Total Tokens**: {metrics["total_tokens"]:,}
- **Total Cost**: ${metrics["total_cost"]:.4f}

### Strategy Benefits:
✅ Neutral, fact-driven main analysis (Sonnet 4)
✅ Deep, insightful interview questions (Sonnet 4.5)
✅ Balanced performance/quality tradeoff

"""

    markdown_report += hybrid_metrics

    # Save report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(
        output_dir, f"{username}_hybrid_{args.role}_{timestamp}.md"
    )
    with open(output_file, "w") as f:
        f.write(markdown_report)

    logger.info(f"Hybrid report saved to: {output_file}")

    # Print summary
    print(f"\n✅ Hybrid Analysis Complete for {username}")
    print(
        f"   📊 Phase 1 (Sonnet 4):  {metrics['phase1_duration']:.2f}s, ${metrics['phase1_cost']:.4f}"
    )
    print(
        f"   📊 Phase 2 (Sonnet 4.5): {metrics['phase2_duration']:.2f}s, ${metrics['phase2_cost']:.4f}"
    )
    print(
        f"   📊 Total:               {metrics['total_duration']:.2f}s, ${metrics['total_cost']:.4f}"
    )
    print(f"   - Evidence patterns: {len(result.evidence_patterns)}")
    print(f"   - Interview questions: {len(result.interview_questions)}")
    print(f"   - Key observations: {len(result.key_observations)}")


if __name__ == "__main__":
    main()
