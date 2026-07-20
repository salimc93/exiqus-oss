# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Abstract base class for analysis strategies.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class AnalysisStrategy(ABC):
    """Abstract base class for repository analysis strategies."""

    @abstractmethod
    def analyze(
        self,
        repo_data: Any,
        context: Any,
        tier: str,
        anthropic_client: Any,
        evidence: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Perform analysis using the specific strategy.

        Args:
            repo_data: Repository data object
            context: Analysis context
            tier: User subscription tier
            anthropic_client: Client for AI calls
            evidence: Collected evidence dictionary

        Returns:
            Dictionary containing insights, questions, and other analysis results.
        """
        pass

    def get_role_level_guidance(
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
- ❌ DO NOT ask defensive questions like "why didn't you do X?"
"""
