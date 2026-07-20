#!/usr/bin/env python3
"""
PR Analysis Validation Script for Scale+ Tier.

Tests PR analysis with real GitHub data and Anthropic API using enterprise context.
Follows the same pipeline as public repository analysis.
"""

import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime  # noqa: F401
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
class PREvidence:
    """PR-specific evidence patterns."""

    pr_description_quality: List[str] = field(default_factory=list)
    review_responsiveness: List[str] = field(default_factory=list)
    code_review_skills: List[str] = field(default_factory=list)
    collaboration_patterns: List[str] = field(default_factory=list)
    integration_patterns: List[str] = field(default_factory=list)
    cross_repo_contributions: List[str] = field(default_factory=list)


@dataclass
class PRAnalysisResult:
    """Complete PR analysis result matching repo analysis structure."""

    # Core sections matching UI
    executive_summary: str
    key_insights: List[str]
    evidence_patterns: List[Dict[str, str]]
    interview_questions: List[Dict[str, Any]]
    recommendations: List[str]
    quality_indicators: List[Dict[str, str]]

    # Metadata
    username: str
    total_prs_analyzed: int
    repos_contributed_to: int
    analysis_context: str
    confidence_explanation: str

    # Raw data for debugging
    raw_pr_data: Optional[Dict[str, Any]] = None
    ai_tokens_used: int = 0
    ai_cost: float = 0.0


class PRAnalyzer:
    """Analyzes GitHub PRs using the same pipeline as repository analysis."""

    def __init__(self, github_token: str, anthropic_api_key: str):
        """Initialize with API credentials."""
        self.github_token = github_token
        self.anthropic_client = anthropic.Anthropic(
            api_key=anthropic_api_key,
            timeout=600.0,  # 10 minute timeout (maximum)
            max_retries=2,
        )

        # Scale+ tier configuration
        self.model = "claude-sonnet-4-20250514"  # Scale+ exclusive model
        self.max_tokens = 12000  # Scale+ unified approach tokens

        # GitHub API headers with timeout
        self.headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3+json",
        }
        self.request_timeout = 30  # 30 seconds for GitHub API calls

    def fetch_user_prs(self, username: str, max_prs: int = 50) -> Dict[str, Any]:
        """Fetch PRs created by a user across all public repositories."""
        logger.info(f"Fetching PRs for user: {username}")

        # Search for all PRs created by the user
        search_url = "https://api.github.com/search/issues"
        params = {
            "q": f"author:{username} type:pr is:public",
            "sort": "created",
            "order": "desc",
            "per_page": min(max_prs, 100),
        }

        response = requests.get(
            search_url,
            headers=self.headers,
            params=params,
            timeout=self.request_timeout,
        )

        if response.status_code != 200:
            logger.error(f"GitHub API error: {response.status_code}")
            return {}

        data = response.json()
        pr_list = data.get("items", [])

        # Fetch detailed PR data including reviews and comments
        detailed_prs = []
        repos_contributed = set()

        for pr in pr_list[:max_prs]:
            # Extract repo info
            repo_url = pr["repository_url"]
            repo_parts = repo_url.split("/")
            owner = repo_parts[-2]
            repo = repo_parts[-1]
            repos_contributed.add(f"{owner}/{repo}")

            # Fetch PR details
            pr_number = pr["number"]
            pr_detail_url = (
                f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
            )

            detail_response = requests.get(
                pr_detail_url, headers=self.headers, timeout=self.request_timeout
            )
            if detail_response.status_code == 200:
                pr_detail = detail_response.json()

                # Fetch reviews
                reviews_url = f"{pr_detail_url}/reviews"
                reviews_response = requests.get(
                    reviews_url, headers=self.headers, timeout=self.request_timeout
                )
                if reviews_response.status_code == 200:
                    pr_detail["reviews"] = reviews_response.json()

                # Fetch review comments
                comments_url = f"{pr_detail_url}/comments"
                comments_response = requests.get(
                    comments_url, headers=self.headers, timeout=self.request_timeout
                )
                if comments_response.status_code == 200:
                    pr_detail["review_comments"] = comments_response.json()

                detailed_prs.append(pr_detail)

        return {
            "username": username,
            "total_prs": len(detailed_prs),
            "repos_contributed_to": list(repos_contributed),
            "repos_count": len(repos_contributed),
            "prs": detailed_prs,
        }

    def extract_pr_evidence(self, pr_data: Dict[str, Any]) -> PREvidence:
        """Extract evidence patterns from PR data."""
        evidence = PREvidence()

        for pr in pr_data.get("prs", []):
            # PR Description Quality
            if pr.get("body"):
                body_length = len(pr["body"])
                if body_length > 500:
                    evidence.pr_description_quality.append(
                        f"Comprehensive PR description ({body_length} chars) in {pr['base']['repo']['name']}"
                    )
                elif body_length > 100:
                    evidence.pr_description_quality.append(
                        f"Adequate PR description in {pr['base']['repo']['name']}"
                    )

            # Review Responsiveness
            if pr.get("review_comments"):
                comment_count = len(pr["review_comments"])
                if comment_count > 0:
                    evidence.review_responsiveness.append(
                        f"Engaged with {comment_count} review comments in {pr['base']['repo']['name']}"
                    )

            # Code Review Skills (if they reviewed others)
            if pr.get("reviews"):
                for review in pr["reviews"]:
                    if review.get("user", {}).get("login") != pr_data["username"]:
                        evidence.code_review_skills.append(
                            f"Received {review['state']} review from {review['user']['login']}"
                        )

            # Collaboration Patterns
            if pr.get("merged"):
                evidence.collaboration_patterns.append(
                    f"Successfully merged PR into {pr['base']['repo']['name']}"
                )

            # Integration Patterns
            if pr.get("additions", 0) < 100 and pr.get("deletions", 0) < 100:
                evidence.integration_patterns.append(
                    "Small, focused PR (good practice for review)"
                )
            elif pr.get("additions", 0) > 500:
                evidence.integration_patterns.append(
                    "Large PR (may indicate significant feature work)"
                )

        # Cross-repo contributions
        if pr_data.get("repos_count", 0) > 1:
            evidence.cross_repo_contributions.append(
                f"Contributed to {pr_data['repos_count']} different repositories"
            )

        return evidence

    def generate_enterprise_prompt(
        self, pr_data: Dict[str, Any], evidence: PREvidence
    ) -> str:
        """Generate enterprise-context prompt for PR analysis - matching public repo structure."""

        # Convert PR evidence to format matching public repo evidence structure
        evidence_json = {
            "pr_patterns": {
                "total_prs": pr_data["total_prs"],
                "repos_contributed": pr_data["repos_count"],
                "merge_success_rate": len(evidence.collaboration_patterns),
                "review_engagement": len(evidence.review_responsiveness),
            },
            "collaboration_evidence": {
                "pr_descriptions": evidence.pr_description_quality[:5],
                "review_responses": evidence.review_responsiveness[:5],
                "merge_patterns": evidence.collaboration_patterns[:5],
            },
            "technical_substance": {
                "integration_approach": evidence.integration_patterns[:5],
                "cross_repo_work": evidence.cross_repo_contributions[:2],
            },
            "observable_patterns": [
                f"Contributed to {pr_data['repos_count']} repositories",
                f"Total of {pr_data['total_prs']} PRs analyzed",
                f"{len(evidence.collaboration_patterns)} successfully merged PRs",
                f"{len(evidence.review_responsiveness)} PRs with review engagement",
            ],
        }

        return f"""You are a senior technical hiring consultant analyzing GitHub pull requests for ENTERPRISE hiring context.

⚠️ CRITICAL WARNING: DO NOT GENERATE ANY NUMERIC SCORES, PERCENTAGES, RATINGS, OR ARBITRARY THRESHOLDS
- No numbers like 0.5, 70%, 3/5, etc.
- No "high/medium/low" based on numeric cutoffs
- Only report what you directly observe from PRs
- NEVER include fields like "score", "rating", "percentage" in your JSON response

ENTERPRISE CONTEXT FOCUS:
You are evaluating for a large enterprise organization where developers must:
- Work within established architectural standards and governance
- Collaborate across multiple teams and time zones
- Navigate complex approval and deployment processes
- Ensure compliance with security and regulatory requirements
- Maintain and evolve mission-critical legacy systems
- Document thoroughly for knowledge transfer
- Think in quarters and years, not weeks

ZED-VALIDATED HIRING SIGNALS TO LOOK FOR IN PRs:
1. SUSTAINED ENGAGEMENT: Multiple PRs over time (Junkui had 30+ PRs before hiring)
2. TECHNICAL SUBSTANCE: Implementing features, not just fixes (OpenType support, debugger work)
3. PROACTIVE ALIGNMENT: Engaging in discussions BEFORE submitting PRs
4. COLLABORATION DEPTH: Responding to reviews, iterating based on feedback
5. PASSION INDICATORS: Going beyond requirements, solving unsolicited problems

Your job: Generate ACTIONABLE, SPECIFIC insights that help enterprise hiring teams understand this candidate's:
- Ability to work within enterprise constraints
- Cross-team collaboration evidence
- Process adherence and documentation habits
- Long-term thinking and sustainability focus

PR Evidence Data: {json.dumps(evidence_json, indent=2)}

CRITICAL REQUIREMENTS:
- Each insight must be SPECIFIC and backed by concrete evidence from PRs
- Focus on PRACTICAL hiring implications that matter to enterprise teams
- Reference actual repositories, PR patterns as evidence with specific examples
- Connect PR patterns to enterprise needs and team fit
- Be honest about limitations - don't oversell what GitHub PRs can tell us

1. EXECUTIVE SUMMARY (2-3 sentences)
   - Focus on contribution consistency and quality (Zed signal #1)
   - Highlight collaboration depth and community engagement
   - Note technical substance of contributions

2. KEY INSIGHTS (5-7 insights)
   Each insight should address one of these hiring signals:
   - CONSISTENCY: Sustained vs sporadic contributions
   - QUALITY: Code craftsmanship and attention to detail
   - COLLABORATION: How they work with others
   - COMMUNICATION: PR descriptions, review responses
   - SUBSTANCE: Meaningful features vs trivial fixes
   - ENGAGEMENT: Genuine interest vs resume building

3. EVIDENCE PATTERNS (8-10 patterns)
   Each pattern as a JSON object with:
   - "pattern": Pattern name (e.g., "Sustained Contributor", "Drive-by PRs")
   - "evidence": Specific examples from PRs
   - "strength": "strong" | "moderate" | "emerging"
   - "hiring_signal": Which Zed hiring signal this addresses
   - "enterprise_relevance": Why this matters for enterprise

4. INTERVIEW QUESTIONS (5-6 questions)
   Each question as a JSON object with:
   - "question": Probe deeper into their PR work (beyond what's visible)
   - "category": "consistency" | "quality" | "collaboration" | "substance"
   - "context": Why this matters based on their GitHub activity
   - "evidence_basis": Specific PR that triggered this question
   - "follow_up_prompts": 2-3 follow-ups to dig deeper

5. RECOMMENDATIONS (5-6 actionable items)
   Focus on:
   - Validation areas (what to verify in interviews)
   - Collaboration style assessment
   - Technical depth verification
   - Red flags to investigate
   - Positive signals to explore further

6. QUALITY INDICATORS (6-8 indicators)
   Each indicator as a JSON object with:
   - "indicator": Name (e.g., "PR Engagement Level", "Code Review Participation")
   - "observation": What was observed in PRs
   - "hiring_signal": "positive" | "neutral" | "investigate"
   - "implication": What this suggests about the candidate

7. CONFIDENCE EXPLANATION
   - Based on: PR volume, contribution diversity, time span
   - Note limitations: private repos not visible, role context missing

Remember:
- NO numerical scores or percentages
- Focus on OBSERVABLE PATTERNS from actual PRs
- Emphasize ENTERPRISE-SPECIFIC insights
- Generate questions that probe BEYOND what we can see in PRs
"""

    def analyze_with_ai(
        self, pr_data: Dict[str, Any], evidence: PREvidence, context: str = "enterprise"
    ) -> PRAnalysisResult:
        """Analyze PR data using Anthropic API."""
        logger.info(f"Analyzing with AI using {self.model}")

        prompt = self.generate_enterprise_prompt(pr_data, evidence)

        try:
            response = self.anthropic_client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=0.3,  # Lower temperature for consistency
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )

            # Parse AI response
            ai_content = response.content[0].text if response.content else ""

            # Calculate token usage and cost
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            total_tokens = input_tokens + output_tokens

            # Sonnet 4 pricing (official rates)
            # Input: $3/MTok, Output: $15/MTok
            cost = (input_tokens * 3.0 + output_tokens * 15.0) / 1_000_000

            # Parse the structured response
            result = self.parse_ai_response(ai_content, pr_data, context)
            result.ai_tokens_used = total_tokens
            result.ai_cost = cost

            logger.info(
                f"AI analysis complete. Tokens: {total_tokens}, Cost: ${cost:.4f}"
            )

            return result

        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            # Return a basic result on failure
            return PRAnalysisResult(
                executive_summary="Analysis failed due to AI error.",
                key_insights=[],
                evidence_patterns=[],
                interview_questions=[],
                recommendations=[],
                quality_indicators=[],
                username=pr_data["username"],
                total_prs_analyzed=pr_data["total_prs"],
                repos_contributed_to=pr_data["repos_count"],
                analysis_context=context,
                confidence_explanation="Analysis incomplete due to error.",
            )

    def parse_ai_response(
        self, ai_content: str, pr_data: Dict[str, Any], context: str
    ) -> PRAnalysisResult:
        """Parse AI response into structured result."""
        # Initialize with defaults
        result = PRAnalysisResult(
            executive_summary="",
            key_insights=[],
            evidence_patterns=[],
            interview_questions=[],
            recommendations=[],
            quality_indicators=[],
            username=pr_data["username"],
            total_prs_analyzed=pr_data["total_prs"],
            repos_contributed_to=pr_data["repos_count"],
            analysis_context=context,
            confidence_explanation="",
            raw_pr_data=pr_data,
        )

        # Split content into sections
        lines = ai_content.split("\n")
        current_section = ""
        section_content = []

        for line in lines:
            if "EXECUTIVE SUMMARY" in line:
                current_section = "summary"
                section_content = []
            elif "KEY INSIGHTS" in line:
                current_section = "insights"
                section_content = []
            elif "EVIDENCE PATTERNS" in line:
                current_section = "patterns"
                section_content = []
            elif "INTERVIEW QUESTIONS" in line:
                current_section = "questions"
                section_content = []
            elif "RECOMMENDATIONS" in line:
                current_section = "recommendations"
                section_content = []
            elif "QUALITY INDICATORS" in line:
                current_section = "indicators"
                section_content = []
            elif "CONFIDENCE EXPLANATION" in line:
                current_section = "confidence"
                section_content = []
            else:
                section_content.append(line)

                # Process completed sections
                if (
                    current_section == "summary"
                    and line.strip()
                    and not line.startswith("-")
                ):
                    result.executive_summary += line.strip() + " "
                elif current_section == "insights" and line.strip().startswith("-"):
                    result.key_insights.append(line.strip()[1:].strip())
                elif current_section == "recommendations" and line.strip().startswith(
                    "-"
                ):
                    result.recommendations.append(line.strip()[1:].strip())
                elif current_section == "confidence" and line.strip():
                    result.confidence_explanation += line.strip() + " "

        # Try to parse JSON sections
        full_content = "\n".join(lines)

        # Extract evidence patterns
        try:
            import re

            patterns_match = re.search(
                r"EVIDENCE PATTERNS.*?(\[.*?\])", full_content, re.DOTALL
            )
            if patterns_match:
                result.evidence_patterns = json.loads(patterns_match.group(1))
        except Exception:
            pass

        # Extract interview questions
        try:
            questions_match = re.search(
                r"INTERVIEW QUESTIONS.*?(\[.*?\])", full_content, re.DOTALL
            )
            if questions_match:
                result.interview_questions = json.loads(questions_match.group(1))
        except Exception:
            pass

        # Extract quality indicators
        try:
            indicators_match = re.search(
                r"QUALITY INDICATORS.*?(\[.*?\])", full_content, re.DOTALL
            )
            if indicators_match:
                result.quality_indicators = json.loads(indicators_match.group(1))
        except Exception:
            pass

        return result

    def format_markdown_report(self, result: PRAnalysisResult) -> str:
        """Format analysis result as markdown matching UI structure."""
        report = f"""# PR Analysis Report - {result.username}

## 📊 Analysis Metadata
- **Context**: {result.analysis_context.upper()}
- **PRs Analyzed**: {result.total_prs_analyzed}
- **Repositories**: {result.repos_contributed_to}
- **Model**: Scale+ (claude-sonnet-4-20250514)
- **Tokens Used**: {result.ai_tokens_used:,}
- **Analysis Cost**: ${result.ai_cost:.4f}

---

## 🏢 Executive Summary
{result.executive_summary}

### Evidence Quality Assessment
{result.confidence_explanation}

---

## 💡 Key Insights

"""
        for i, insight in enumerate(result.key_insights, 1):
            report += f"{i}. {insight}\n"

        report += """
---

## 🔍 Evidence Patterns

"""
        for pattern in result.evidence_patterns[:10]:
            if isinstance(pattern, dict):
                report += f"### {pattern.get('pattern', 'Unknown Pattern')}\n"
                report += f"**Evidence**: {pattern.get('evidence', 'N/A')}\n"
                report += f"**Strength**: {pattern.get('strength', 'moderate')}\n"
                report += f"**Enterprise Relevance**: {pattern.get('enterprise_relevance', 'N/A')}\n\n"

        report += """
---

## 💬 Interview Questions

"""
        for i, question in enumerate(result.interview_questions[:6], 1):
            if isinstance(question, dict):
                report += f"### Q{i}: {question.get('question', 'N/A')}\n\n"
                report += f"**Category**: `{question.get('category', 'general')}`\n"
                report += f"**Context**: {question.get('context', 'N/A')}\n\n"
                report += f"📍 **Based on Evidence**: {question.get('evidence_basis', 'N/A')}\n\n"
                report += "**Follow-up questions**:\n"
                for follow_up in question.get("follow_up_prompts", []):
                    report += f"- {follow_up}\n"
                report += "\n"

        report += """
---

## ✅ Recommendations

"""
        for i, rec in enumerate(result.recommendations, 1):
            report += f"{i}. {rec}\n"

        report += """
---

## 📈 Quality Indicators

"""
        for indicator in result.quality_indicators[:8]:
            if isinstance(indicator, dict):
                report += f"### {indicator.get('indicator', 'N/A')}\n"
                report += f"**Observation**: {indicator.get('observation', 'N/A')}\n"
                report += f"**Implication**: {indicator.get('implication', 'N/A')}\n\n"

        return report


def main():
    """Main validation function."""
    # Get API credentials
    config = get_config()
    github_token = os.getenv("GITHUB_TOKEN") or config.github.token
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY") or config.anthropic_api_key

    if not github_token or not anthropic_api_key:
        logger.error("Missing API credentials. Set GITHUB_TOKEN and ANTHROPIC_API_KEY.")
        sys.exit(1)

    # Test users - one at a time for better analysis
    test_users = [
        "octocat",  # Public example account
    ]

    analyzer = PRAnalyzer(github_token, anthropic_api_key)

    # Create output directory
    output_dir = "pr_analysis_validation"
    os.makedirs(output_dir, exist_ok=True)

    for username in test_users:
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Analyzing PRs for: {username}")
        logger.info(f"{'=' * 60}")

        # Fetch PR data
        pr_data = analyzer.fetch_user_prs(username, max_prs=30)

        if not pr_data or not pr_data.get("prs"):
            logger.warning(f"No PR data found for {username}")
            continue

        # Extract evidence
        evidence = analyzer.extract_pr_evidence(pr_data)

        # Analyze with AI
        result = analyzer.analyze_with_ai(pr_data, evidence, context="enterprise")

        # Format report
        markdown_report = analyzer.format_markdown_report(result)

        # Save report
        output_file = os.path.join(output_dir, f"{username}_pr_analysis.md")
        with open(output_file, "w") as f:
            f.write(markdown_report)

        logger.info(f"Report saved to: {output_file}")

        # Also save raw JSON for debugging
        json_file = os.path.join(output_dir, f"{username}_pr_analysis.json")
        with open(json_file, "w") as f:
            json.dump(
                {
                    "username": result.username,
                    "summary": result.executive_summary,
                    "insights": result.key_insights,
                    "patterns": result.evidence_patterns,
                    "questions": result.interview_questions,
                    "recommendations": result.recommendations,
                    "indicators": result.quality_indicators,
                    "confidence": result.confidence_explanation,
                    "metadata": {
                        "prs_analyzed": result.total_prs_analyzed,
                        "repos": result.repos_contributed_to,
                        "tokens": result.ai_tokens_used,
                        "cost": result.ai_cost,
                    },
                },
                f,
                indent=2,
            )

        # Print summary
        print(f"\n✅ Analysis complete for {username}")
        print(f"   - PRs analyzed: {result.total_prs_analyzed}")
        print(f"   - Repos contributed to: {result.repos_contributed_to}")
        print(f"   - Key insights: {len(result.key_insights)}")
        print(f"   - Evidence patterns: {len(result.evidence_patterns)}")
        print(f"   - Interview questions: {len(result.interview_questions)}")
        print(f"   - Cost: ${result.ai_cost:.4f}")


if __name__ == "__main__":
    main()
