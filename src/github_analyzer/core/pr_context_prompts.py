# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
PR Analysis context-specific prompts.

Provides context-aware prompts for PR analysis based on hiring environment.
These prompts guide the AI to focus on relevant patterns for each context.
"""

from typing import Dict

PR_CONTEXT_PROMPTS: Dict[str, str] = {
    "STARTUP": """
    Analyze PR contributions for startup environment fit.
    Focus on:
    - Feature velocity and MVP mindset
    - Adaptability across tech stacks
    - Rapid iteration patterns
    - Ownership of features from concept to production
    - Small PR philosophy vs large feature drops
    - Direct problem-solving without bureaucracy

    Key evidence to highlight:
    - Time from PR creation to merge (velocity)
    - Feature PRs that went straight to production
    - Cross-repository contributions showing adaptability
    - Self-managed PRs without extensive review cycles

    IMPORTANT: Use only evidence provided. No behavioral inferences.
    """,
    "ENTERPRISE": """
    Analyze PR contributions for enterprise environment fit.
    Focus on:
    - Scale and architecture patterns
    - Process adherence and documentation
    - Review cycle participation
    - Long-term maintenance patterns
    - Security and compliance awareness
    - Team collaboration at scale

    Key evidence to highlight:
    - Extensive review cycles (3+ rounds)
    - Documentation in PR descriptions
    - Test coverage and quality gates
    - Breaking changes handled carefully
    - Long-lived feature branches with planning

    IMPORTANT: Use only evidence provided. No behavioral inferences.
    """,
    "AGENCY": """
    Analyze PR contributions for agency environment fit.
    Focus on:
    - Multi-project adaptability
    - Client-ready code quality
    - Quick context switching
    - Diverse technology experience
    - Deadline-driven delivery
    - Clean handoff patterns

    Key evidence to highlight:
    - Contributions across many different repositories
    - Various technology stacks and languages
    - Consistent PR quality despite context switches
    - Clear PR descriptions for handoffs
    - Rapid PR turnaround times

    IMPORTANT: Use only evidence provided. No behavioral inferences.
    """,
    "OPEN_SOURCE": """
    Analyze PR contributions for open source collaboration.
    Focus on:
    - Community engagement patterns
    - Documentation and communication
    - Code review participation
    - Following project conventions
    - Constructive feedback handling
    - Long-term commitment to projects

    Key evidence to highlight:
    - PR discussions and review participation
    - Following contributing guidelines
    - Detailed PR descriptions for community
    - Response to feedback and iterations
    - Sustained contributions over time

    IMPORTANT: Use only evidence provided. No behavioral inferences.
    """,
}


def get_pr_context_prompt(context: str) -> str:
    """
    Get the appropriate PR analysis prompt for a given context.

    Args:
        context: The hiring context (STARTUP, ENTERPRISE, AGENCY, OPEN_SOURCE)

    Returns:
        Context-specific prompt string, or OPEN_SOURCE prompt as default
    """
    return PR_CONTEXT_PROMPTS.get(context.upper(), PR_CONTEXT_PROMPTS["OPEN_SOURCE"])


def enhance_pr_evidence_with_context(evidence_summary: str, context: str) -> str:
    """
    Enhance PR evidence summary with context-specific framing.

    Args:
        evidence_summary: The extracted PR evidence summary
        context: The hiring context

    Returns:
        Enhanced prompt combining evidence and context focus
    """
    context_prompt = get_pr_context_prompt(context)

    return f"""
{context_prompt}

EXTRACTED PR EVIDENCE:
{evidence_summary}

Based on the evidence above and the {context} context, provide:
1. Key strengths demonstrated through PR patterns
2. Areas where evidence suggests strong fit
3. Patterns that deserve deeper exploration
4. Specific PRs that exemplify important qualities

Remember: Focus only on observable patterns in the PR data.
Do not infer personality traits or work habits beyond what the data shows.
"""
