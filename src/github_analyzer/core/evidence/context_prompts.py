# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Context-specific prompt enhancements for better differentiation.

This module provides specialized prompts for each hiring context to ensure
maximum differentiation in questions and insights.
"""

from typing import Any, Dict


class ContextPromptEnhancer:
    """Enhance prompts with context-specific focus areas."""

    @staticmethod
    def get_context_prompt(context: str, evidence_summary: Dict[str, Any]) -> str:
        """Get context-specific prompt enhancement."""

        if context.lower() == "startup":
            return ContextPromptEnhancer._get_startup_prompt(evidence_summary)
        elif context.lower() == "enterprise":
            return ContextPromptEnhancer._get_enterprise_prompt(evidence_summary)
        elif context.lower() == "agency":
            return ContextPromptEnhancer._get_agency_prompt(evidence_summary)
        elif context.lower() == "open_source":
            return ContextPromptEnhancer._get_open_source_prompt(evidence_summary)
        else:
            return ""

    @staticmethod
    def _get_startup_prompt(evidence_summary: Dict[str, Any]) -> str:
        """Startup-specific prompt focusing on agility and versatility."""
        return """
STARTUP CONTEXT FOCUS:
You are interviewing for a fast-paced startup environment where developers must:
- Ship MVPs quickly while managing technical debt consciously
- Wear multiple hats and switch contexts rapidly
- Make pragmatic trade-offs between perfection and speed
- Scale systems from 10 to 10,000 users
- Work with limited resources and tight deadlines
- Pivot quickly when market demands change

Generate questions that specifically probe:
1. "Move fast and break things" vs sustainable velocity
2. How they prioritize when everything is urgent
3. Experience building from scratch vs maintaining legacy
4. Comfort with ambiguity and changing requirements
5. Ability to do "good enough" without compromising critical quality
6. Resource optimization and creative problem-solving
7. Direct customer interaction and feedback incorporation

AVOID generic questions about:
- Large team coordination (startups are small)
- Extensive documentation (startup docs are lean)
- Complex approval processes (startups move fast)
- Rigid architectural standards (startups iterate)
"""

    @staticmethod
    def _get_enterprise_prompt(evidence_summary: Dict[str, Any]) -> str:
        """Enterprise-specific prompt focusing on scale and process."""
        return """
ENTERPRISE CONTEXT FOCUS:
You are interviewing for a large enterprise organization where developers must:
- Work within established architectural standards and governance
- Collaborate across multiple teams and time zones
- Navigate complex approval and deployment processes
- Ensure compliance with security and regulatory requirements
- Maintain and evolve mission-critical legacy systems
- Document thoroughly for knowledge transfer
- Think in quarters and years, not weeks

Generate questions that specifically probe:
1. Experience with enterprise-scale systems (millions of users)
2. Working within architectural review boards and standards
3. Security-first mindset and compliance awareness
4. Cross-functional collaboration with non-technical stakeholders
5. Long-term thinking and technical debt management
6. Change management and risk mitigation strategies
7. Mentoring and knowledge transfer at scale

AVOID questions about:
- Rapid prototyping and MVPs (enterprises plan thoroughly)
- Working without specifications (enterprises document everything)
- Making unilateral technical decisions (enterprises have process)
- Startup hustle culture (enterprises value sustainability)
"""

    @staticmethod
    def _get_agency_prompt(evidence_summary: Dict[str, Any]) -> str:
        """Agency-specific prompt focusing on client work and versatility."""
        return """
AGENCY CONTEXT FOCUS:
You are interviewing for a digital agency where developers must:
- Juggle multiple client projects simultaneously
- Adapt to vastly different tech stacks and industries
- Communicate technical concepts to non-technical clients
- Deliver on tight, fixed deadlines with fixed budgets
- Rapidly onboard to new codebases and domains
- Balance perfectionism with billable hours
- Handle demanding clients and changing requirements

Generate questions that specifically probe:
1. Project juggling and context switching abilities
2. Client communication and expectation management
3. Rapid learning and adaptation to new domains
4. Working with inherited codebases of varying quality
5. Time estimation and deadline management
6. Handling difficult clients and scope creep
7. Portfolio diversity and technology flexibility

DIFFERENTIATE from startup by focusing on:
- Multiple concurrent projects (vs single product focus)
- Client relationship management (vs internal stakeholders)
- Billable hours awareness (vs equity/ownership mindset)
- Technology diversity (vs deep specialization)
- External deadlines (vs self-imposed sprints)

Questions should reflect AGENCY-SPECIFIC scenarios:
- "How do you handle a client requesting a technology you've never used?"
- "Describe juggling three projects with conflicting deadlines"
- "How do you explain technical debt to a non-technical client?"
"""

    @staticmethod
    def _get_open_source_prompt(evidence_summary: Dict[str, Any]) -> str:
        """Open source-specific prompt focusing on community and sustainability."""
        return """
OPEN SOURCE CONTEXT FOCUS:
You are interviewing for an open source project where developers must:
- Collaborate asynchronously with global contributors
- Write code that others can understand and maintain
- Review PRs from developers of all skill levels
- Build consensus in public discussions
- Create comprehensive documentation
- Think about long-term project sustainability
- Balance community needs with project vision

Generate questions that specifically probe:
1. Asynchronous communication and collaboration skills
2. Code readability and documentation practices
3. Community building and contributor mentorship
4. Handling public criticism and feedback
5. Sustainable development practices
6. Vision alignment and consensus building
7. Volunteer motivation and management

UNIQUE to open source context:
- Working in public (all mistakes visible)
- Motivating unpaid contributors
- Dealing with drive-by PRs and issues
- Maintaining backwards compatibility
- Building inclusive communities
- Managing burnout in volunteer projects

Questions should be OPEN SOURCE SPECIFIC:
- "How do you handle a PR that doesn't match project standards?"
- "Describe building consensus when contributors disagree"
- "How do you maintain quality with volunteer contributors?"
"""

    @staticmethod
    def get_context_differentiators(context1: str, context2: str) -> Dict[str, Any]:
        """Get key differentiators between two contexts."""

        differentiators = {
            ("startup", "agency"): {
                "startup_focus": [
                    "Single product ownership and vision",
                    "Equity and long-term investment mindset",
                    "Building for scale from day one",
                    "Internal stakeholder management",
                ],
                "agency_focus": [
                    "Multiple client project juggling",
                    "Billable hours and project profitability",
                    "Adapting to existing client systems",
                    "External client relationship management",
                ],
                "key_differences": [
                    "Ownership model: Product vs Service",
                    "Timeline: Long-term vs Project-based",
                    "Stakeholders: Internal vs External",
                    "Tech choices: Strategic vs Client-driven",
                ],
            },
            ("startup", "enterprise"): {
                "startup_focus": [
                    "Moving fast with calculated risks",
                    "Minimal viable documentation",
                    "Direct user feedback loops",
                    "Resource constraints driving creativity",
                ],
                "enterprise_focus": [
                    "Risk mitigation and compliance",
                    "Comprehensive documentation standards",
                    "Multi-layer approval processes",
                    "Resource abundance with budget controls",
                ],
                "key_differences": [
                    "Speed: Weeks vs Quarters",
                    "Process: Agile vs Governance",
                    "Scale: Thousands vs Millions",
                    "Risk: Embrace vs Mitigate",
                ],
            },
            ("agency", "open_source"): {
                "agency_focus": [
                    "Client-driven requirements",
                    "Deadline-driven development",
                    "Billable efficiency",
                    "Private code ownership",
                ],
                "open_source_focus": [
                    "Community-driven development",
                    "Sustainable pace",
                    "Volunteer coordination",
                    "Public code and discussions",
                ],
                "key_differences": [
                    "Motivation: Profit vs Purpose",
                    "Pace: Deadline vs Sustainable",
                    "Visibility: Private vs Public",
                    "Contributors: Employees vs Volunteers",
                ],
            },
        }

        # Return differentiators for the requested pair
        key = (context1.lower(), context2.lower())
        reverse_key = (context2.lower(), context1.lower())

        if key in differentiators:
            return differentiators[key]
        elif reverse_key in differentiators:
            # Swap the focus areas
            diff = differentiators[reverse_key]
            return {
                f"{context1}_focus": diff.get(f"{context2}_focus", []),
                f"{context2}_focus": diff.get(f"{context1}_focus", []),
                "key_differences": diff.get("key_differences", []),
            }
        else:
            return {
                f"{context1}_focus": [],
                f"{context2}_focus": [],
                "key_differences": [],
            }
