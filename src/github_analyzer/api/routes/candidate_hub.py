# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Candidate Hub API endpoint.

Provides aggregated view of all analysis types for a specific GitHub username.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.connection import get_db_session
from ...database.models import AnalysisResult, PRAnalysisRecord, PRAnalysisResult, User
from ...database.models_portfolio import PortfolioAnalysis
from ...utils.logging import get_logger
from ..auth.dependencies import get_current_active_user

logger = get_logger(__name__)

router = APIRouter(prefix="/candidate-hub", tags=["Candidate Hub"])


def ensure_timezone_aware(dt: datetime) -> datetime:
    """Ensure datetime is timezone-aware (UTC if naive)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


@router.get(
    "/{username}",
    summary="Get candidate hub data",
    description=(
        "Get aggregated analysis data for a specific GitHub username "
        "(portfolio, PR, and single repo analyses)"
    ),
)
async def get_candidate_hub(
    username: str,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Get all analysis data for a specific GitHub username.

    Returns:
        - Latest portfolio analysis (if exists)
        - Latest PR analysis (if exists)
        - Recent single repo analyses (last 5)
        - GitHub stats (from latest analysis metadata)

    Args:
        username: GitHub username to fetch data for
        user: Authenticated user
        db: Database session

    Returns:
        Candidate hub data with all analysis types

    Raises:
        HTTPException: If data fetch fails
    """
    try:
        logger.info(
            f"Fetching candidate hub data for username: {username} (user: {user.email})"
        )

        # Fetch latest portfolio analysis for this username (owned by current user)
        portfolio_result = await db.execute(
            select(PortfolioAnalysis)
            .where(PortfolioAnalysis.user_id == user.user_id)
            .where(PortfolioAnalysis.github_username == username)
            .order_by(PortfolioAnalysis.created_at.desc())
            .limit(1)
        )
        portfolio_analysis = portfolio_result.scalar_one_or_none()

        # Fetch latest PR analysis for this username (owned by current user)
        pr_result = await db.execute(
            select(PRAnalysisRecord)
            .where(PRAnalysisRecord.user_id == user.user_id)
            .where(PRAnalysisRecord.github_username == username)
            .order_by(PRAnalysisRecord.created_at.desc())
            .limit(1)
        )
        pr_analysis = pr_result.scalar_one_or_none()

        # Fetch recent single repo analyses for this username (owned by current user)
        # Extract username from repository_name (format: "username/repo")
        single_repo_result = await db.execute(
            select(AnalysisResult)
            .where(AnalysisResult.user_id == user.user_id)
            .where(AnalysisResult.repository_name.like(f"{username}/%"))
            .order_by(AnalysisResult.created_at.desc())
            .limit(5)
        )
        single_repo_analyses = single_repo_result.scalars().all()

        # Fetch full PR analysis result if PR analysis exists
        pr_analysis_result = None
        if pr_analysis and pr_analysis.analysis_id:
            pr_result_query = await db.execute(
                select(PRAnalysisResult).where(
                    PRAnalysisResult.id == pr_analysis.analysis_id
                )
            )
            pr_analysis_result = pr_result_query.scalar_one_or_none()

        # Synthesize intelligence snapshot from all analyses
        intelligence_snapshot = await synthesize_candidate_intelligence(
            db,
            portfolio_analysis,
            pr_analysis,
            pr_analysis_result,
            single_repo_analyses,
            username,
        )

        # Format response
        response = {
            "username": username,
            "snapshot": intelligence_snapshot,
            "portfolio_analysis": (
                format_portfolio_summary(portfolio_analysis)
                if portfolio_analysis
                else None
            ),
            "pr_analysis": (
                format_pr_summary(pr_analysis, pr_analysis_result)
                if pr_analysis
                else None
            ),
            "single_repo_analyses": [
                format_single_repo_summary(analysis)
                for analysis in single_repo_analyses
            ],
        }

        logger.info(
            f"Successfully fetched candidate hub data for {username}: "
            f"portfolio={'yes' if portfolio_analysis else 'no'}, "
            f"pr={'yes' if pr_analysis else 'no'}, "
            f"repos={len(single_repo_analyses)}"
        )

        return response

    except Exception as e:
        logger.error(
            f"Error fetching candidate hub data for {username}: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch candidate hub data: {str(e)}",
        )


# Helper functions


async def synthesize_candidate_intelligence(
    db: AsyncSession,
    portfolio: Optional[PortfolioAnalysis],
    pr_record: Optional[PRAnalysisRecord],
    pr_result: Optional[PRAnalysisResult],
    repos: Sequence[AnalysisResult],
    username: str,
) -> Dict[str, Any]:
    """
    Role-aware intelligence synthesis - evidence-only, no judgment.

    Creates unified intelligence snapshot combining:
    - PR analysis metrics with confidence levels
    - Portfolio analysis insights
    - Single repo analysis data
    - Role-specific prioritization (junior/mid/senior)
    - Evidence trails to GitHub sources
    - Interview strategies

    Returns: Evidence-based snapshot with complete transparency about data scope.
    """
    from datetime import datetime

    # Determine role from analyses
    role = determine_role_level(portfolio, pr_record)

    # Determine organization context from analyses (ANY analysis type)
    org_context = determine_org_context(portfolio, pr_record, repos)

    # Build analyses list
    analyses_available: List[str] = []
    last_updated: Optional[str] = None

    if portfolio:
        # Extract role from database field (not JSON)
        portfolio_role = str(portfolio.role).title() if portfolio.role else "Mid"

        analyses_available.append(
            f"Portfolio ({format_context_label(portfolio.context)}, {portfolio_role})"
        )
        last_updated = ensure_timezone_aware(portfolio.created_at).isoformat()

    if pr_record:
        # Extract role from database field (not JSON)
        pr_role = str(pr_record.role).title() if pr_record.role else "Mid"

        analyses_available.append(
            f"PR Analysis ({format_context_label(pr_record.context)}, {pr_role})"
        )
        if not last_updated or ensure_timezone_aware(
            pr_record.created_at
        ) > datetime.fromisoformat(last_updated.replace("Z", "+00:00")):
            last_updated = pr_record.created_at.isoformat()

    if repos:
        analyses_available.append(
            f"{len(repos)} Repository Deep Dive{'s' if len(repos) > 1 else ''}"
        )

    # Assess data coverage (volume, not quality)
    data_coverage = assess_data_volume(pr_result, portfolio, repos)

    # Build data scope transparency
    data_scope = build_data_scope_notice(
        pr_result, portfolio, repos, username, data_coverage
    )

    # Extract observable patterns with role-aware prioritization
    observable_patterns = extract_role_aware_patterns(
        role, pr_result, portfolio, repos, username, data_coverage
    )

    # Extract evidence summary with role prioritization (from ANY analysis source)
    evidence_summary = extract_role_aware_evidence_summary(
        role, portfolio, pr_result, repos, data_coverage
    )

    # Featured single repo (most complex/prominent if 2+ repos analyzed)
    featured_repo = select_featured_repo_analysis(repos) if len(repos) >= 2 else None

    snapshot = {
        "username": username,
        "avatar_url": f"https://github.com/{username}.png",
        "role": role,
        "organization_context": org_context,
        "last_updated": last_updated,
        "analyses_run": analyses_available,
        "data_scope": data_scope,
        "observable_patterns": observable_patterns,
        "evidence_summary": evidence_summary,
        "key_observations": evidence_summary.get("key_observations", []),
        "featured_repo_analysis": featured_repo,
    }

    return snapshot


def format_context_label(context: str) -> str:
    """
    Format organization context for display.
    Handles underscores and proper capitalization.

    Examples:
        "open_source" -> "Open Source"
        "startup" -> "Startup"
        "enterprise" -> "Enterprise"
        "agency" -> "Agency"
    """
    if not context:
        return ""

    # Replace underscores with spaces, then title case each word
    return context.replace("_", " ").title()


def determine_role_level(
    portfolio: Optional[PortfolioAnalysis], pr_record: Optional[PRAnalysisRecord]
) -> str:
    """
    Determine role level from analyses.
    Fallback hierarchy: Portfolio > PR > Default to 'mid'

    Note: Role is stored as a direct database field in both models.
    """
    # Try portfolio role field (direct database column)
    if portfolio and hasattr(portfolio, "role") and portfolio.role:
        return str(portfolio.role).lower()

    # Try PR record role field
    if pr_record and hasattr(pr_record, "role") and pr_record.role:
        return str(pr_record.role).lower()

    return "mid"  # Conservative default


def determine_org_context(
    portfolio: Optional[PortfolioAnalysis],
    pr_record: Optional[PRAnalysisRecord],
    repos: Sequence[AnalysisResult],
) -> Optional[str]:
    """
    Determine organization context from ANY available analysis.
    Checks portfolio, PR, and single repo analyses in order of recency.

    Returns the most recent context, or None if no analyses exist.
    Handles cases where user runs analyses in any order.
    """
    contexts_with_dates = []

    # Check portfolio
    if portfolio and portfolio.context and portfolio.created_at:
        contexts_with_dates.append(
            (portfolio.context, ensure_timezone_aware(portfolio.created_at))
        )

    # Check PR record
    if pr_record and pr_record.context and pr_record.created_at:
        contexts_with_dates.append(
            (pr_record.context, ensure_timezone_aware(pr_record.created_at))
        )

    # Check single repo analyses
    for repo in repos:
        if repo.context and repo.created_at:
            contexts_with_dates.append(
                (repo.context, ensure_timezone_aware(repo.created_at))
            )

    # Return most recent context
    if contexts_with_dates:
        # Sort by date descending (most recent first)
        contexts_with_dates.sort(key=lambda x: x[1], reverse=True)
        return str(contexts_with_dates[0][0]).lower()

    return None  # No context available


def select_featured_repo_analysis(
    repos: Sequence[AnalysisResult],
) -> Optional[Dict[str, Any]]:
    """
    Select the most prominent single repo analysis from available repos.

    Uses observable evidence depth to determine prominence:
    - Number of screening insights generated
    - Number of evidence patterns identified
    - Commit activity

    Repos with more insights/patterns demonstrate higher complexity and depth.
    No arbitrary scoring - just count the actual evidence generated.

    Returns formatted repo snapshot with:
    - repository_name
    - commits
    - languages (top 3 by usage)
    - context
    - analysis_id (for linking to detailed page)
    - created_at
    - insights_count (for display)
    - patterns_count (for display)

    Returns None if no valid repos or analysis data is unavailable.
    """
    import re

    if not repos or len(repos) < 2:
        return None

    repo_candidates = []

    for repo in repos:
        try:
            # Parse full_analysis JSON
            full_data = (
                json.loads(repo.full_analysis)
                if isinstance(repo.full_analysis, str)
                else repo.full_analysis
            )

            analysis = full_data.get("analysis", {})
            technical_assessment = analysis.get("technical_assessment", {})
            sub_metrics = technical_assessment.get("sub_metrics", [])

            # Extract commits from sub_metrics
            commits = 0
            language_str = ""

            for metric in sub_metrics:
                if metric.get("name") == "Development Activity":
                    # Extract number from evidence like "30 total commits"
                    evidence = metric.get("evidence", "")
                    match = re.search(r"(\d+)\s+total commits", evidence)
                    if match:
                        commits = int(match.group(1))

                elif metric.get("name") == "Primary Language":
                    # Extract language from evidence like "Python (100% of codebase)"
                    evidence = metric.get("evidence", "")
                    match = re.search(r"^([A-Za-z+#]+)", evidence)
                    if match:
                        language_str = match.group(1)

            # Get top languages
            top_languages = [language_str] if language_str else []

            # Count evidence depth (insights + patterns)
            # Parse screening_insights if it's a JSON string
            insights_count = 0
            if repo.screening_insights:
                try:
                    insights_data = (
                        json.loads(repo.screening_insights)
                        if isinstance(repo.screening_insights, str)
                        else repo.screening_insights
                    )
                    insights_count = (
                        len(insights_data) if isinstance(insights_data, list) else 0
                    )
                except (json.JSONDecodeError, TypeError):
                    insights_count = 0

            # Parse evidence_patterns if it's a JSON string
            patterns_count = 0
            if repo.evidence_patterns:
                try:
                    patterns_data = (
                        json.loads(repo.evidence_patterns)
                        if isinstance(repo.evidence_patterns, str)
                        else repo.evidence_patterns
                    )
                    patterns_count = (
                        len(patterns_data) if isinstance(patterns_data, list) else 0
                    )
                except (json.JSONDecodeError, TypeError):
                    patterns_count = 0

            # Total evidence depth
            evidence_depth = insights_count + patterns_count

            repo_candidates.append(
                {
                    "evidence_depth": evidence_depth,
                    "commits": commits,
                    "repository_name": repo.repository_name,
                    "languages": top_languages,
                    "context": str(repo.context).lower() if repo.context else None,
                    "analysis_id": repo.id,
                    "created_at": (
                        repo.created_at.isoformat() if repo.created_at else None
                    ),
                    "insights_count": insights_count,
                    "patterns_count": patterns_count,
                }
            )

        except (json.JSONDecodeError, KeyError, TypeError, AttributeError) as e:
            logger.warning(
                f"Failed to parse repo analysis for {repo.repository_name}: {e}"
            )
            continue

    if not repo_candidates:
        return None

    # Sort by evidence depth first (most insights/patterns = most complex),
    # then by commits as tiebreaker
    repo_candidates.sort(
        key=lambda x: (x["evidence_depth"], x["commits"]), reverse=True
    )

    # Remove internal sorting field
    featured = repo_candidates[0]
    featured.pop("evidence_depth", None)

    return featured


def assess_data_volume(
    pr_result: Optional[PRAnalysisResult],
    portfolio: Optional[PortfolioAnalysis],
    repos: Sequence[AnalysisResult],
) -> str:
    """
    Assess data volume (not quality).
    Returns: "high", "moderate", "limited", "none"
    """
    if pr_result:
        total_prs = pr_result.total_prs_analyzed
        if total_prs >= 50:
            return "high"
        elif total_prs >= 20:
            return "moderate"
        elif total_prs > 0:
            return "limited"

    if portfolio:
        if portfolio.repos_analyzed >= 10:
            return "moderate"
        elif portfolio.repos_analyzed >= 5:
            return "limited"

    if len(repos) > 0:
        return "limited"

    return "none"


def build_data_scope_notice(
    pr_result: Optional[PRAnalysisResult],
    portfolio: Optional[PortfolioAnalysis],
    repos: Sequence[AnalysisResult],
    username: str,
    data_coverage: str,
) -> Dict[str, Any]:
    """
    Build transparent data scope notice.

    BLEND BABY BLEND: Combines all available data sources.
    - Portfolio analysis provides comprehensive repo count
    - Single repo analyses show deep-dive count when no portfolio
    - PR analysis adds collaboration dimension
    """
    prs_analyzed = pr_result.total_prs_analyzed if pr_result else 0

    # BLEND: Use most comprehensive repo count available
    # Portfolio = all repos, Single repos = deep dives only
    repos_analyzed = portfolio.repos_analyzed if portfolio else len(repos)

    # Calculate timeline span - take LONGEST from Portfolio AND PR analysis
    timeline_span = "Unknown"
    portfolio_days = 0
    pr_days = 0

    # Get Portfolio timeline (has oldest_repo and newest_repo dates in full_analysis)
    if portfolio and portfolio.full_analysis:
        from datetime import datetime

        try:
            full_data = (
                json.loads(portfolio.full_analysis)
                if isinstance(portfolio.full_analysis, str)
                else portfolio.full_analysis
            )
            # Metadata is at top level, not under result
            metadata = full_data.get("metadata", {})
            oldest = metadata.get("oldest_repo")
            newest = metadata.get("newest_repo")

            if oldest and newest:
                oldest_dt = datetime.fromisoformat(oldest.replace("Z", "+00:00"))
                newest_dt = datetime.fromisoformat(newest.replace("Z", "+00:00"))
                portfolio_days = (newest_dt - oldest_dt).days
        except (json.JSONDecodeError, KeyError, TypeError, AttributeError, ValueError):
            pass

    # Get PR timeline
    if pr_result and pr_result.detailed_report:
        try:
            detailed = (
                json.loads(pr_result.detailed_report)
                if isinstance(pr_result.detailed_report, str)
                else pr_result.detailed_report
            )
            quality_signals = detailed.get("quality_signals", {})
            pr_timespan_str = quality_signals.get("contribution_timespan", "")

            # Parse PR timespan string (e.g., "4 years, 1 months" -> days)
            if pr_timespan_str and pr_timespan_str != "Unknown":
                years = 0
                months = 0
                if "year" in pr_timespan_str:
                    years = int(pr_timespan_str.split("year")[0].strip().split()[-1])
                if "month" in pr_timespan_str:
                    months = int(pr_timespan_str.split("month")[0].strip().split()[-1])
                pr_days = (years * 365) + (months * 30)
        except (json.JSONDecodeError, KeyError, TypeError, AttributeError, ValueError):
            pass

    # Take the LONGEST timeline from both sources
    longest_days = max(portfolio_days, pr_days)
    timeline_label = "Timeline Span"  # Default label

    if longest_days > 0:
        # Determine label based on which sources we have (check if analyses exist, not just if timeline was extracted)
        if portfolio and pr_result:
            timeline_label = "Total Activity Timeline"
        elif pr_result and pr_days > 0:
            timeline_label = "PR Contribution Timeline"
        elif portfolio and portfolio_days > 0:
            timeline_label = "Portfolio Timeline"

        # Format as human-readable string
        if longest_days < 30:
            timeline_span = f"{longest_days} days"
        elif longest_days < 365:
            months = longest_days // 30
            timeline_span = f"{months} month{'s' if months > 1 else ''}"
        else:
            years = longest_days // 365
            remaining_months = (longest_days % 365) // 30
            if remaining_months > 0:
                timeline_span = f"{years} year{'s' if years > 1 else ''}, {remaining_months} month{'s' if remaining_months > 1 else ''}"
            else:
                timeline_span = f"{years} year{'s' if years > 1 else ''}"

    return {
        "what_analyzed": "Public repositories only",
        "prs_analyzed": prs_analyzed,
        "repos_analyzed": repos_analyzed,
        "timeline_span": timeline_span,
        "timeline_label": timeline_label,
        "data_volume": data_coverage,
        "not_analyzed": [
            "Private company repositories",
            "Proprietary codebases",
            "Work before public GitHub activity",
        ],
        "important_note": "This is one data point. Professional work in private repos not visible.",
    }


def calculate_confidence_level(metric_type: str, data_points: int) -> Dict[str, Any]:
    """
    Calculate confidence based on data volume (NOT quality judgment).
    Returns confidence metadata.
    """
    thresholds = {
        "commit_activity": {"high": 100, "moderate": 20},
        "pr_contributions": {"high": 50, "moderate": 10},
        "code_reviews": {"high": 30, "moderate": 5},
        "repository_diversity": {"high": 10, "moderate": 3},
    }

    metric_threshold = thresholds.get(metric_type, {"high": 10, "moderate": 3})

    if data_points >= metric_threshold["high"]:
        level = "high"
        note = "Sufficient volume for pattern detection"
    elif data_points >= metric_threshold["moderate"]:
        level = "moderate"
        note = "Moderate data points available"
    else:
        level = "low"
        note = "Limited visibility—discuss professional habits"

    return {"level": level, "basis": f"{data_points} data points", "note": note}


def extract_pr_activity_metrics(pr_result: PRAnalysisResult) -> Dict[str, Any]:
    """Extract activity metrics from PR analysis result."""

    activity: Dict[str, Any] = {
        "prs": {},
        "repositories": {},
        "collaboration": {},
        "timeline": {},
        "technologies": [],
    }

    try:
        # Parse detailed_report for quality signals
        if pr_result.detailed_report:
            detailed = (
                json.loads(pr_result.detailed_report)
                if isinstance(pr_result.detailed_report, str)
                else pr_result.detailed_report
            )
            quality_signals = detailed.get("quality_signals", {})

            # PR metrics
            total_prs = quality_signals.get("total_prs", pr_result.total_prs_analyzed)
            merged_prs = quality_signals.get("merged_prs", 0)

            activity["prs"] = {
                "total": total_prs,
                "merged": merged_prs,
                "merge_rate": round(merged_prs / total_prs, 2) if total_prs > 0 else 0,
            }

            # Repository reach
            activity["repositories"] = {
                "unique_repos": quality_signals.get("unique_repos", 0),
                "contribution_span": quality_signals.get(
                    "contribution_timespan", "Unknown"
                ),
            }

            # Timeline
            activity["timeline"] = {
                "contribution_span": quality_signals.get(
                    "contribution_timespan", "Unknown"
                ),
            }

        # Parse evidence for collaboration metrics
        if pr_result.evidence:
            evidence = (
                json.loads(pr_result.evidence)
                if isinstance(pr_result.evidence, str)
                else pr_result.evidence
            )
            collab_patterns = evidence.get("collaboration_patterns", [])

            # Extract review count from collaboration evidence
            review_count = 0
            for pattern in collab_patterns:
                if "review" in pattern.lower():
                    # Try to extract number from evidence text
                    import re

                    numbers = re.findall(r"\d+", pattern)
                    if numbers:
                        review_count = max(review_count, int(numbers[0]))

            activity["collaboration"] = {
                "reviews_given": review_count,
                "has_collaboration_evidence": len(collab_patterns) > 0,
            }

        # Extract languages from summary or full analysis
        if pr_result.full_analysis:
            # Languages might be in metadata or inferred from repos
            # For now, we'll leave this empty and populate from GitHub API if needed
            activity["technologies"] = []

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning(f"Error extracting PR activity metrics: {e}")

    return activity


def extract_portfolio_insights(portfolio: PortfolioAnalysis) -> Dict[str, Any]:
    """Extract key insights from portfolio analysis."""

    insights: Dict[str, Any] = {
        "executive_summary": "",
        "strengths": [],
        "discussion_areas": [],
        "key_observations": [],  # NEW: Key observations for quick insights
        "context": portfolio.context,
        "role": "senior",  # Default, will be extracted from full_analysis if available
    }

    try:
        if portfolio.full_analysis:
            full_data = (
                json.loads(portfolio.full_analysis)
                if isinstance(portfolio.full_analysis, str)
                else portfolio.full_analysis
            )
            result = full_data.get("result", {})

            # Executive summary (first 400 chars)
            summary = result.get("summary", "")
            insights["executive_summary"] = (
                summary[:400] + "..." if len(summary) > 400 else summary
            )

            # Extract ONLY positive indicators as strengths (evidence patterns shown in Patterns section)
            strengths_list = insights.get("strengths", [])
            if isinstance(strengths_list, list):
                # Positive indicators are actual STRENGTHS (not raw evidence)
                positive_indicators = result.get("positive_indicators", [])
                for indicator in positive_indicators[:6]:  # Show more (was 4)
                    if isinstance(indicator, str):
                        # Strip markdown ** formatting
                        clean_indicator = indicator.replace("**", "")

                        # Split on ": " (most indicators are formatted as "**Title**: Description")
                        if ": " in clean_indicator:
                            parts = clean_indicator.split(": ", 1)
                            title = parts[0].strip()
                            description = parts[1].strip() if len(parts) > 1 else ""
                        else:
                            # Fallback: split on first sentence
                            parts = clean_indicator.split(". ", 1)
                            title = parts[0].strip()
                            description = parts[1].strip() if len(parts) > 1 else ""

                        strengths_list.append(
                            {
                                "title": title,
                                "evidence": (
                                    description if description else clean_indicator
                                ),  # Just the description, not full text
                                "analysis": "Strength from portfolio analysis",
                                "category": "positive_indicator",
                            }
                        )

            # Extract key observations from Portfolio (uses 'observations' field)
            observations = result.get("observations", [])
            observations_list = insights.get("key_observations", [])
            if isinstance(observations_list, list):
                for obs in observations[:6]:  # Top 6 observations
                    if isinstance(obs, str):
                        observations_list.append(obs)

            # Extract interview questions - PRIORITIZED by category importance
            interview_questions = result.get("interview_questions", [])

            # Define priority order for question categories
            category_priority = {
                "problem-solving": 1,
                "testing": 2,
                "collaboration": 3,
                "code-quality": 4,
                "learning-agility": 5,
            }

            # Sort questions by category priority
            sorted_questions = sorted(
                [q for q in interview_questions if isinstance(q, dict)],
                key=lambda x: category_priority.get(x.get("category", "").lower(), 999),
            )

            # Add ALL interview questions to insights for candidate hub
            insights["interview_questions"] = interview_questions

            # Take top 3-4 highest priority questions for snapshot (legacy discussion_areas)
            discussion_areas_list = insights.get("discussion_areas", [])
            if isinstance(discussion_areas_list, list):
                for q in sorted_questions[:4]:
                    discussion_areas_list.append(
                        {
                            "category": q.get("category", "General"),
                            "title": q.get("category", "General")
                            .replace("-", " ")
                            .title(),
                            "question": q.get("question", ""),
                            "evidence": q.get("evidence_reference", ""),
                        }
                    )

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning(f"Error extracting portfolio insights: {e}")

    return insights


def extract_pr_insights(pr_result: PRAnalysisResult) -> Dict[str, Any]:
    """Extract insights from PR analysis."""

    insights = {
        "executive_summary": "",
        "strengths": [],
        "discussion_areas": [],
        "key_observations": [],  # NEW: Use discussion_areas as observations for PR
        "interview_questions": [],
    }

    try:
        # Get executive summary from AI insights
        if pr_result.ai_insights:
            ai = (
                json.loads(pr_result.ai_insights)
                if isinstance(pr_result.ai_insights, str)
                else pr_result.ai_insights
            )

            exec_summary = ai.get("executive_summary", "")
            insights["executive_summary"] = (
                exec_summary[:400] + "..." if len(exec_summary) > 400 else exec_summary
            )

            # Key insights and strengths from PR analysis
            key_insights = ai.get("key_insights", [])
            key_strengths = ai.get("key_strengths", [])

            logger.info(
                f"PR INSIGHTS DEBUG - key_insights count: {len(key_insights)}, key_strengths count: {len(key_strengths)}"
            )

            # Combine both into strengths list
            all_pr_strengths = []

            # Extract from key_insights (these are the high-level insights)
            for insight in key_insights[:5]:
                if isinstance(insight, dict):
                    all_pr_strengths.append(
                        {
                            "title": insight.get(
                                "title", insight.get("description", "")
                            ),
                            "evidence": insight.get(
                                "evidence", "From PR analysis patterns"
                            ),
                            "category": insight.get("category", "pr_analysis"),
                        }
                    )
                elif isinstance(insight, str):
                    all_pr_strengths.append(
                        {
                            "title": insight,
                            "evidence": "From PR analysis patterns",
                            "category": "pr_analysis",
                        }
                    )

            # Extract from key_strengths (backup if key_insights is empty)
            if not all_pr_strengths:
                for strength in key_strengths[:5]:
                    all_pr_strengths.append(
                        {
                            "title": (
                                strength
                                if isinstance(strength, str)
                                else strength.get("title", "")
                            ),
                            "evidence": "From PR analysis patterns",
                            "category": "pr_analysis",
                        }
                    )

            # Add to insights
            strengths_list = insights.get("strengths", [])
            if isinstance(strengths_list, list):
                strengths_list.extend(all_pr_strengths)
                insights["strengths"] = strengths_list  # CRITICAL: Assign back!

            # Key observations from areas_for_discussion
            areas_for_discussion = ai.get("areas_for_discussion", [])
            observations_list = insights.get("key_observations", [])
            if isinstance(observations_list, list):
                for area in areas_for_discussion[:6]:  # Top 6 observations
                    if isinstance(area, str):
                        observations_list.append(area)
                    elif isinstance(area, dict):
                        # If it's a dict, extract the title or description
                        observations_list.append(
                            area.get("title", area.get("description", ""))
                        )
                insights["key_observations"] = (
                    observations_list  # CRITICAL: Assign back!
                )

            # Interview questions
            interview_qs = ai.get("interview_questions", [])
            questions_list = insights.get("interview_questions", [])
            if isinstance(questions_list, list):
                for q in interview_qs[:4]:
                    if isinstance(q, dict):
                        questions_list.append(
                            {
                                "category": q.get("category", "General"),
                                "question": q.get("question", ""),
                                "evidence_basis": q.get("evidence_reference", ""),
                            }
                        )

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning(f"Error extracting PR insights: {e}")

    return insights


def convert_kb_to_mb(text: str) -> str:
    """Convert KB values to MB in text for consistency with portfolio results page."""
    import re

    # Check if this text has multiple KB values (comparison scenario)
    kb_matches = re.findall(r"([\d,]+)\s*KB", text, re.IGNORECASE)
    has_multiple_kb = len(kb_matches) > 1

    has_large_kb = any(int(match.replace(",", "")) >= 1024 for match in kb_matches)

    # If comparing sizes and one is large, convert ALL to MB for consistency
    convert_all_to_mb = has_multiple_kb and has_large_kb

    def replace_kb(match: re.Match[str]) -> str:
        num = match.group(1).replace(",", "")
        kb = int(num)
        if kb >= 1024 or convert_all_to_mb:
            mb = kb / 1024
            return f"{mb:.2f}MB" if mb < 10 else f"{mb:.1f}MB"
        return match.group(0)

    return re.sub(r"([\d,]+)\s*KB", replace_kb, text, flags=re.IGNORECASE)


def extract_role_aware_patterns(
    role: str,
    pr_result: Optional[PRAnalysisResult],
    portfolio: Optional[PortfolioAnalysis],
    repos: Sequence[AnalysisResult],
    username: str,
    data_coverage: str,
) -> List[Dict[str, Any]]:
    """
    Extract observable patterns with role-aware prioritization.
    Returns evidence-only patterns with confidence levels and GitHub links.
    """

    patterns: List[Dict[str, Any]] = []

    # Define role-specific metric priorities
    ROLE_METRIC_PRIORITIES = {
        "junior": [
            "commit_activity",
            "repository_diversity",
            "technology_focus",
            "timeline_span",
            "test_files",
            "documentation",
        ],
        "mid": [
            "pr_merge_rate",
            "code_review_participation",
            "repository_reach",
            "testing_frameworks",
            "ci_cd_presence",
            "commit_activity",
        ],
        "senior": [
            "code_review_volume",
            "cross_repository_impact",
            "polyglot_development",
            "contribution_timespan",
            "project_scale",
            "long_term_maintenance",
        ],
    }

    # Get priority order for this role
    priority_order = ROLE_METRIC_PRIORITIES.get(role, ROLE_METRIC_PRIORITIES["mid"])

    # Extract all available metrics
    all_metrics = {}

    # 1. Extract PR metrics
    if pr_result:
        activity: Dict[str, Any] = extract_pr_activity_metrics(pr_result)

        # PR merge rate
        prs = activity.get("prs", {})
        if prs.get("total", 0) > 0:
            merge_rate = prs.get("merge_rate", 0)
            merged = prs.get("merged", 0)
            total = prs.get("total", 0)

            all_metrics["pr_merge_rate"] = {
                "pattern": "PR Merge Rate",
                "value": f"{int(merge_rate * 100)}% ({merged}/{total} PRs merged)",
                "visibility": "observed",
                "context": "Public PR contributions",
                "confidence": calculate_confidence_level("pr_contributions", total),
                "evidence_trail": [
                    {
                        "source": "Public GitHub PRs",
                        "url": f"https://github.com/search?q=is:pr+author:{username}+is:merged",
                    }
                ],
                "analysis_source": "pr",
            }

        # Code review participation
        collab = activity.get("collaboration", {})
        reviews = collab.get("reviews_given", 0)
        if reviews > 0:
            all_metrics["code_review_participation"] = {
                "pattern": "Code Review Participation",
                "value": f"{reviews} reviews given",
                "visibility": "observed",
                "context": "Public collaboration activity",
                "confidence": calculate_confidence_level("code_reviews", reviews),
                "evidence_trail": [
                    {
                        "source": "Public review activity",
                        "url": f"https://github.com/search?q=commenter:{username}+type:pr",
                    }
                ],
                "analysis_source": "pr",
            }
            all_metrics["code_review_volume"] = all_metrics[
                "code_review_participation"
            ]  # Alias for senior

        # Repository reach
        repos_data = activity.get("repositories", {})
        unique_repos = repos_data.get("unique_repos", 0)
        if unique_repos > 0:
            all_metrics["repository_reach"] = {
                "pattern": "Repository Reach",
                "value": f"{unique_repos} unique repositories",
                "visibility": "observed",
                "context": "Contributions span multiple codebases",
                "confidence": calculate_confidence_level(
                    "repository_diversity", unique_repos
                ),
                "evidence_trail": [
                    {
                        "source": "Public repositories",
                        "url": f"https://github.com/{username}?tab=repositories",
                    }
                ],
                "analysis_source": "pr",
            }
            all_metrics["cross_repository_impact"] = all_metrics[
                "repository_reach"
            ]  # Alias for senior

        # Contribution timespan
        timeline = activity.get("timeline", {})
        timespan = timeline.get("contribution_span", "")
        if timespan and timespan != "Unknown":
            all_metrics["contribution_timespan"] = {
                "pattern": "Contribution Timespan",
                "value": timespan,
                "visibility": "observed",
                "context": "Public GitHub timeline - professional history should be verified",
                "confidence": {
                    "level": "moderate",
                    "basis": "Timeline from public activity",
                    "note": "Does not include private work",
                },
                "evidence_trail": [],
                "analysis_source": "pr",
            }
            all_metrics["timeline_span"] = all_metrics[
                "contribution_timespan"
            ]  # Alias for junior

    # 2. Extract portfolio metrics
    if portfolio:
        # Commit activity
        if hasattr(portfolio, "full_analysis") and portfolio.full_analysis:
            try:
                full_data = (
                    json.loads(portfolio.full_analysis)
                    if isinstance(portfolio.full_analysis, str)
                    else portfolio.full_analysis
                )
                metadata = full_data.get("metadata", {})

                # Total commits if available
                total_commits = metadata.get("total_commits", 0)
                if total_commits > 0:
                    all_metrics["commit_activity"] = {
                        "pattern": "Commit Activity",
                        "value": f"{total_commits} commits visible",
                        "visibility": "observed",
                        "context": "Public repos only - recent activity period",
                        "confidence": calculate_confidence_level(
                            "commit_activity", total_commits
                        ),
                        "evidence_trail": [
                            {
                                "source": "Portfolio analysis",
                                "url": f"https://github.com/{username}",
                            }
                        ],
                        "analysis_source": "portfolio",
                    }

                # Extract patterns from Portfolio evidence_patterns and quality_indicators
                result = full_data.get("result", {})

                # Evidence Patterns - these are rich, factual patterns
                evidence_patterns = result.get("evidence_patterns", [])
                for i, pattern in enumerate(evidence_patterns[:8]):  # Top 8 patterns
                    if isinstance(pattern, dict):
                        pattern_name = pattern.get("pattern", "")
                        evidence = pattern.get("evidence", "")
                        analysis = pattern.get("analysis", "")

                        # Convert KB to MB for consistency with portfolio results page
                        evidence_formatted = convert_kb_to_mb(evidence)
                        analysis_formatted = (
                            convert_kb_to_mb(analysis) if analysis else ""
                        )

                        # Extract KEY METRIC from evidence (first sentence only for readability)
                        # This makes it scannable instead of showing truncated walls of text
                        key_metric = (
                            evidence_formatted.split(". ")[0]
                            if ". " in evidence_formatted
                            else evidence_formatted
                        )
                        if len(key_metric) > 100:
                            key_metric = key_metric[:97] + "..."

                        # Create a metric key from pattern name (lowercase, spaces to underscores)
                        metric_key = f"portfolio_pattern_{i}_{pattern_name.lower().replace(' ', '_')}"

                        all_metrics[metric_key] = {
                            "pattern": pattern_name,
                            "value": key_metric,  # Just the key metric, not full evidence
                            "visibility": "observed",
                            "context": (
                                analysis_formatted[:200]
                                if analysis_formatted
                                else "Pattern from portfolio analysis"
                            ),
                            "confidence": {
                                "level": "moderate",
                                "basis": "From portfolio analysis",
                                "note": "Based on public repository evidence",
                            },
                            "evidence_trail": [
                                {
                                    "source": "Portfolio analysis",
                                    "url": f"https://github.com/{username}",
                                }
                            ],
                            "analysis_source": "portfolio",
                        }

                # Quality Indicators - these show deeper insights
                quality_indicators = result.get("quality_indicators", [])
                for i, indicator in enumerate(
                    quality_indicators[:5]
                ):  # Top 5 indicators
                    if isinstance(indicator, dict):
                        indicator_name = indicator.get("indicator", "")
                        observation = indicator.get("observation", "")

                        metric_key = f"portfolio_quality_{i}_{indicator_name.lower().replace(' ', '_')}"

                        all_metrics[metric_key] = {
                            "pattern": indicator_name,
                            "value": (
                                observation[:150] + "..."
                                if len(observation) > 150
                                else observation
                            ),
                            "visibility": "observed",
                            "context": indicator.get(
                                "implication", "Quality indicator from portfolio"
                            )[:200],
                            "confidence": {
                                "level": "moderate",
                                "basis": f"Observed across {portfolio.repos_analyzed} repos",
                                "note": "Public repositories only",
                            },
                            "evidence_trail": [
                                {
                                    "source": "Portfolio analysis",
                                    "url": f"https://github.com/{username}",
                                }
                            ],
                            "analysis_source": "portfolio",
                        }
            except (json.JSONDecodeError, KeyError, TypeError):
                pass

        # Repository diversity
        repos_analyzed = portfolio.repos_analyzed
        all_metrics["repository_diversity"] = {
            "pattern": "Repository Diversity",
            "value": f"{repos_analyzed} repositories analyzed",
            "visibility": "observed",
            "context": "Multiple project types visible in public repos",
            "confidence": calculate_confidence_level(
                "repository_diversity", repos_analyzed
            ),
            "evidence_trail": [
                {
                    "source": "Portfolio analysis",
                    "url": f"https://github.com/{username}?tab=repositories",
                }
            ],
            "analysis_source": "portfolio",
        }

    # 3. Extract repo-level patterns (test files, documentation, etc.)
    if repos:
        # Count test files and docs across all repos
        test_count = 0
        doc_count = 0
        total_repos = len(repos)

        for repo in repos:
            # Check if repo has tests (would be in metadata/full_analysis)
            # This is simplified - real implementation would parse repo analysis
            # For now, we'll mark as "not_observed" if we don't have data
            pass

        # Test files pattern
        all_metrics["test_files"] = {
            "pattern": "Test Files",
            "value": (
                f"{test_count}/{total_repos} repos contain test files"
                if test_count > 0
                else f"Not detected in {total_repos} public repos"
            ),
            "visibility": "observed" if test_count > 0 else "not_observed",
            "context": (
                "Testing practices not visible in public repos - verify in interview"
                if test_count == 0
                else "Test files detected"
            ),
            "confidence": {
                "level": "low" if test_count == 0 else "moderate",
                "basis": f"{total_repos} repositories analyzed",
                "note": "Limited to public repository visibility",
            },
            "evidence_trail": [],
            "analysis_source": "portfolio",
        }
        all_metrics["testing_frameworks"] = all_metrics["test_files"]  # Alias for mid

        # Documentation pattern
        all_metrics["documentation"] = {
            "pattern": "Documentation",
            "value": (
                f"{doc_count}/{total_repos} repos have README files"
                if doc_count > 0
                else f"Not detected in {total_repos} public repos"
            ),
            "visibility": "observed" if doc_count > 0 else "not_observed",
            "context": (
                "Documentation not visible in public repos - discuss approach"
                if doc_count == 0
                else "Documentation detected"
            ),
            "confidence": {
                "level": "low" if doc_count == 0 else "moderate",
                "basis": f"{total_repos} repositories analyzed",
                "note": "Public repositories only",
            },
            "evidence_trail": [],
            "analysis_source": "portfolio",
        }

        # Project scale (for senior)
        if repos:
            # Extract project scale metric
            all_metrics["project_scale"] = {
                "pattern": "Project Scale",
                "value": f"{len(repos)} repositories analyzed",
                "visibility": "observed",
                "context": "Public repos show varied scale - verify enterprise experience",
                "confidence": {
                    "level": "moderate",
                    "basis": f"{len(repos)} repositories",
                    "note": "Enterprise work may exist in private repos",
                },
                "evidence_trail": [],
                "analysis_source": "portfolio",
            }

    # CI/CD and long-term maintenance (typically not observable in public repos)
    all_metrics["ci_cd_presence"] = {
        "pattern": "CI/CD Presence",
        "value": "Not detected in public repos",
        "visibility": "not_observed",
        "context": "DevOps practices not visible - verify in interview",
        "confidence": {
            "level": "low",
            "basis": "Public repository visibility only",
            "note": "CI/CD pipelines may exist in private work",
        },
        "evidence_trail": [],
        "analysis_source": "portfolio",
    }

    all_metrics["long_term_maintenance"] = {
        "pattern": "Long-term Project Maintenance",
        "value": "Not visible in public repos",
        "visibility": "not_observed",
        "context": "System maintenance experience not observable - verify professional work",
        "confidence": {
            "level": "low",
            "basis": "Public data only",
            "note": "Enterprise maintenance work typically in private repos",
        },
        "evidence_trail": [],
        "analysis_source": "portfolio",
    }

    # 4. Prioritize metrics by role and return top patterns
    # BLEND LOGIC: If both PR and Portfolio exist:
    #   - Select 4 OBSERVED patterns total: Try to get 2 from PR + 2 from Portfolio (but be flexible)
    #   - Select 2-3 NOT_OBSERVED patterns from either source
    # If only one source exists:
    #   - Select 6 patterns total (mix of observed and not_observed)

    has_pr = pr_result is not None
    has_portfolio = portfolio is not None

    if has_pr and has_portfolio:
        # BLEND: Both sources available
        pr_observed = []
        portfolio_observed = []
        not_observed_patterns = []

        # Separate patterns by source and visibility
        for metric_key, metric_value in all_metrics.items():
            visibility = metric_value.get("visibility", "observed")

            if visibility == "not_observed":
                not_observed_patterns.append(metric_value)
            elif metric_key.startswith(
                ("pr_", "code_review_", "repository_reach", "contribution_timespan")
            ):
                pr_observed.append(metric_value)
            elif metric_key.startswith(
                (
                    "portfolio_pattern_",
                    "portfolio_quality_",
                    "commit_activity",
                    "repository_diversity",
                )
            ):
                portfolio_observed.append(metric_value)
            else:
                # Generic patterns (test_files, documentation, project_scale) - add to portfolio side
                portfolio_observed.append(metric_value)

        # Select 4 observed patterns: Try to get 2 from PR + 2 from Portfolio
        # Be flexible if one source has fewer patterns
        pr_count = min(2, len(pr_observed))
        portfolio_count = min(2, len(portfolio_observed))

        # If one source has fewer than 2, take more from the other
        if pr_count < 2:
            portfolio_count = min(4 - pr_count, len(portfolio_observed))
        elif portfolio_count < 2:
            pr_count = min(4 - portfolio_count, len(pr_observed))

        observed = pr_observed[:pr_count] + portfolio_observed[:portfolio_count]

        # Select 2-3 NOT_OBSERVED patterns
        not_obs = not_observed_patterns[:3]

        patterns = observed + not_obs
    else:
        # Single source: take 6 patterns (mix of observed and not_observed)
        observed_patterns = []
        not_observed_patterns = []

        # Separate by visibility
        for metric_key, metric_value in all_metrics.items():
            if metric_value.get("visibility", "observed") == "not_observed":
                not_observed_patterns.append(metric_value)
            else:
                observed_patterns.append(metric_value)

        # First add priority metrics (observed)
        priority_observed = []
        for metric_key in priority_order:
            if (
                metric_key in all_metrics
                and all_metrics[metric_key] in observed_patterns
            ):
                priority_observed.append(all_metrics[metric_key])

        # Then add any portfolio patterns not in priority list
        for metric_key, metric_value in all_metrics.items():
            if (
                metric_key.startswith(("portfolio_pattern_", "portfolio_quality_"))
                and metric_value not in priority_observed
                and metric_value in observed_patterns
            ):
                priority_observed.append(metric_value)

        # Take up to 4 observed + 2 not_observed = 6 total
        observed = priority_observed[:4]
        not_obs = not_observed_patterns[:2]
        patterns = observed + not_obs

        # If we have fewer than 6, fill with more observed
        if len(patterns) < 6 and len(observed_patterns) > len(observed):
            remaining = observed_patterns[: 6 - len(patterns)]
            for p in remaining:
                if p not in patterns:
                    patterns.append(p)

        patterns = patterns[:6]

    return patterns


def extract_role_aware_evidence_summary(
    role: str,
    portfolio: Optional[PortfolioAnalysis],
    pr_result: Optional[PRAnalysisResult],
    repos: Sequence[AnalysisResult],
    data_coverage: str,
) -> Dict[str, Any]:
    """
    Extract evidence summary with role-aware prioritization.

    Priority cascade for intelligence snapshot:
    1. Portfolio Analysis (most comprehensive)
    2. PR Analysis (if no portfolio)
    3. Single Repo Analysis (if no portfolio/PR)

    Supports ALL user journeys - user can start with any analysis type,
    and higher-priority analyses will upgrade the snapshot when run.

    Returns executive summary, strengths, and interview questions.
    """
    summary = {
        "executive_summary": "",
        "context_evaluated": "",
        "role_evaluated": role,
        "visible_strengths": [],
        "interview_topics": [],
        "data_interpretation": "",
    }

    # BLEND Portfolio + PR when both exist for complete picture
    portfolio_insights = None
    pr_insights = None

    if portfolio:
        portfolio_insights = extract_portfolio_insights(portfolio)
        summary["context_evaluated"] = portfolio_insights.get("context", "")

    if pr_result:
        pr_insights = extract_pr_insights(pr_result)
        if not portfolio:
            summary["context_evaluated"] = "From PR Analysis"

    # EXECUTIVE SUMMARY: Blend both when available
    if portfolio_insights and pr_insights:
        # BLEND BABY BLEND - Combine both perspectives
        portfolio_summary = portfolio_insights.get("executive_summary", "")
        pr_summary = pr_insights.get("executive_summary", "")
        summary["executive_summary"] = f"{portfolio_summary}\n\n{pr_summary}"
    elif portfolio_insights:
        summary["executive_summary"] = portfolio_insights.get("executive_summary", "")
    elif pr_insights:
        summary["executive_summary"] = pr_insights.get("executive_summary", "")

    # VISIBLE STRENGTHS: Blend Portfolio + PR strengths
    all_strengths = []

    if portfolio_insights:
        portfolio_strengths = portfolio_insights.get("strengths", [])
        for strength in portfolio_strengths:
            all_strengths.append(
                {
                    "title": f"Portfolio: {strength.get('title', '')}",
                    "evidence": strength.get("evidence", ""),
                    "what_this_shows": strength.get(
                        "analysis", strength.get("evidence", "")[:150]
                    ),
                    "source": "portfolio",
                    "category": strength.get("category", ""),
                }
            )

    if pr_insights:
        pr_strengths = pr_insights.get("strengths", [])
        for strength in pr_strengths:
            all_strengths.append(
                {
                    "title": f"PR Analysis: {strength.get('title', '')}",
                    "evidence": strength.get("evidence", ""),
                    "what_this_shows": "Pattern observed in public PR work",
                    "source": "pr",
                    "category": strength.get("category", ""),
                }
            )

    # Define role-specific strength priorities
    ROLE_STRENGTH_PRIORITIES = {
        "junior": [
            "activity",
            "learning-agility",
            "technology-focus",
            "engagement",
        ],
        "mid": [
            "contribution-quality",
            "collaboration",
            "technical-breadth",
            "professional-practices",
        ],
        "senior": ["scope", "longevity", "collaboration", "architectural-impact"],
    }

    priority_categories = ROLE_STRENGTH_PRIORITIES.get(
        role, ROLE_STRENGTH_PRIORITIES["mid"]
    )

    # Sort strengths by role priority
    def strength_priority(strength: Dict[str, Any]) -> int:
        category = strength.get("category", "").lower()
        try:
            return priority_categories.index(category)
        except ValueError:
            return 999

    # BLEND LOGIC: 3 from each when both exist (3+3=6), otherwise 6 from single source
    visible_strengths_list = summary.get("visible_strengths", [])
    if isinstance(visible_strengths_list, list):
        if portfolio_insights and pr_insights:
            # BLEND: 3 from Portfolio + 3 from PR = 6 total
            portfolio_strengths = [
                s for s in all_strengths if s.get("title", "").startswith("Portfolio:")
            ]
            pr_strengths = [
                s
                for s in all_strengths
                if s.get("title", "").startswith("PR Analysis:")
            ]

            # Sort each group by priority
            sorted_portfolio = sorted(portfolio_strengths, key=strength_priority)[:3]
            sorted_pr = sorted(pr_strengths, key=strength_priority)[:3]

            # Add 3 from each
            for strength in sorted_portfolio + sorted_pr:
                visible_strengths_list.append(
                    {
                        "title": strength.get("title", ""),
                        "evidence": strength.get("evidence", ""),
                        "what_this_shows": strength.get("what_this_shows", ""),
                        "source": strength.get("source", "portfolio"),
                    }
                )
        else:
            # Single source: Take 6 strengths
            sorted_strengths = sorted(all_strengths, key=strength_priority)[:6]
            for strength in sorted_strengths:
                visible_strengths_list.append(
                    {
                        "title": strength.get("title", ""),
                        "evidence": strength.get("evidence", ""),
                        "what_this_shows": strength.get("what_this_shows", ""),
                        "source": strength.get(
                            "source", "portfolio"
                        ),  # Include source for UI
                    }
                )

    # Assign back to summary
    summary["visible_strengths"] = visible_strengths_list
    # INTERVIEW TOPICS: Blend Portfolio + PR questions
    all_questions = []

    if portfolio_insights:
        # Get interview questions from portfolio analysis
        interview_questions = portfolio_insights.get("interview_questions", [])
        for q in interview_questions:
            # Skip questions with empty/missing data
            if not q.get("question") or not q.get("category"):
                continue

            all_questions.append(
                {
                    "category": q.get("category", "General"),
                    "observation": f"Portfolio: {q.get('category', '').replace('-', ' ').title()}",
                    "question": q.get("question", ""),
                    "why_discuss": q.get("context", "Should be explored in interview"),
                    "source": "portfolio",
                    "priority_category": q.get("category", "").lower(),
                }
            )

    if pr_insights:
        pr_questions = pr_insights.get("interview_questions", [])
        for q in pr_questions:
            all_questions.append(
                {
                    "category": q.get("category", "General"),
                    "observation": f"PR Analysis: {q.get('title', 'Observation')}",
                    "question": q.get("question", ""),
                    "why_discuss": q.get(
                        "evidence_basis", "Should be explored in interview"
                    ),
                    "source": "pr",
                    "priority_category": q.get("category", "").lower(),
                }
            )

    # Define role-specific question priorities
    ROLE_QUESTION_PRIORITIES = {
        "junior": {
            "learning-agility": 1,
            "problem-solving": 2,
            "code-quality": 3,
            "collaboration": 4,
            "testing": 5,
        },
        "mid": {
            "testing": 1,
            "code-quality": 2,
            "collaboration": 3,
            "architecture": 4,
            "devops": 5,
        },
        "senior": {
            "collaboration": 1,
            "architecture": 2,
            "testing": 3,
            "devops": 4,
            "problem-solving": 5,
            "security": 6,
        },
    }

    priority_map = ROLE_QUESTION_PRIORITIES.get(role, ROLE_QUESTION_PRIORITIES["mid"])

    # Sort questions by category priority
    def question_priority(q: Dict[str, Any]) -> int:
        category = q.get("priority_category", "").lower()
        return priority_map.get(category, 999)

    # BLEND: Take 3 from each when both exist, 6 when single source
    interview_topics_list = summary.get("interview_topics", [])
    if isinstance(interview_topics_list, list):
        if portfolio_insights and pr_insights:
            # BLEND: 3 from Portfolio + 3 from PR
            portfolio_questions = [
                q for q in all_questions if q.get("source") == "portfolio"
            ]
            pr_questions = [q for q in all_questions if q.get("source") == "pr"]

            # Sort each group by priority
            sorted_portfolio = sorted(portfolio_questions, key=question_priority)[:3]
            sorted_pr = sorted(pr_questions, key=question_priority)[:3]

            # Combine 3 from each
            blended_questions = sorted_portfolio + sorted_pr

            for q in blended_questions:
                interview_topics_list.append(
                    {
                        "category": q.get("category", "General"),
                        "observation": q.get("observation", ""),
                        "question": q.get("question", ""),
                        "why_discuss": q.get(
                            "why_discuss", "Should be explored in interview"
                        ),
                        "source": q.get("source", "portfolio"),
                    }
                )
        else:
            # Single source: Take top 6 questions
            sorted_questions = sorted(all_questions, key=question_priority)
            for q in sorted_questions[:6]:
                interview_topics_list.append(
                    {
                        "category": q.get("category", "General"),
                        "observation": q.get("observation", ""),
                        "question": q.get("question", ""),
                        "why_discuss": q.get(
                            "why_discuss", "Should be explored in interview"
                        ),
                        "source": q.get("source", "portfolio"),  # Include source for UI
                    }
                )

    # KEY OBSERVATIONS: Blend Portfolio + PR observations (3+3 when both, 6 when single)
    all_observations = []

    if portfolio_insights:
        portfolio_observations = portfolio_insights.get("key_observations", [])
        for obs in portfolio_observations:
            all_observations.append({"text": obs, "source": "portfolio"})

    if pr_insights:
        pr_observations = pr_insights.get("key_observations", [])
        for obs in pr_observations:
            all_observations.append({"text": obs, "source": "pr"})

    # Add to summary with blending logic (3 from each when both exist)
    summary["key_observations"] = []
    if portfolio_insights and pr_insights:
        # BLEND: Take 3 from each
        portfolio_obs = [o for o in all_observations if o["source"] == "portfolio"][:3]
        pr_obs = [o for o in all_observations if o["source"] == "pr"][:3]
        summary["key_observations"] = portfolio_obs + pr_obs  # type: ignore[assignment]
    else:
        # Single source: Take 6
        summary["key_observations"] = all_observations[:6]  # type: ignore[assignment]

    # Build data interpretation statement
    if portfolio_insights and pr_insights and portfolio and pr_result:
        # BLENDED: Both Portfolio and PR available
        summary["data_interpretation"] = (
            f"Blended intelligence from portfolio (individual coding work "
            f"across {portfolio.repos_analyzed} repos) and PR activity "
            f"({pr_result.total_prs_analyzed} PRs showing collaboration "
            f"patterns). Provides comprehensive view of both technical "
            f"depth and team dynamics for {role}-level assessment."
        )
    elif portfolio_insights and portfolio:
        # Portfolio only
        summary["data_interpretation"] = (
            f"Analysis based on portfolio activity across "
            f"{portfolio.repos_analyzed} repositories. Shows individual "
            f"coding patterns and technical depth for {role}-level "
            f"context. PR/collaboration data not available."
        )
    elif pr_insights and pr_result:
        # PR only
        summary["data_interpretation"] = (
            f"Analysis based on {pr_result.total_prs_analyzed} public "
            f"pull requests. Shows collaboration patterns and code review "
            f"dynamics for {role}-level context. Portfolio/individual "
            f"project data not available."
        )
    else:
        # Fallback
        summary["data_interpretation"] = (
            f"Limited analysis available for {role}-level context. "
            f"Use interview to verify complete experience."
        )

    return summary


def generate_pattern_summary(
    coverage: str,
    activity: Dict[str, Any],
    strengths: List[Dict[str, Any]],
    context: str,
    role: str,
) -> str:
    """Generate a concise pattern summary based on available data."""

    if coverage == "none":
        return "No analysis data available yet. Run analyses to see candidate patterns."

    # Build summary based on what we know
    summary_parts = []

    # Data coverage statement
    if coverage == "high":
        summary_parts.append("Based on comprehensive analysis")
    elif coverage == "medium":
        summary_parts.append("Based on available analysis")
    else:
        summary_parts.append("Based on limited analysis data")

    # PR activity if available
    prs = activity.get("prs", {})
    if prs.get("total", 0) > 0:
        merge_rate = prs.get("merge_rate", 0)
        if merge_rate >= 0.75:
            summary_parts.append(
                f"with strong PR merge rate ({int(merge_rate * 100)}%)"
            )
        summary_parts.append(f"across {prs['total']} pull requests")

    # Context fit
    summary_parts.append(f"evaluated for {context} context")

    # Strength count
    if len(strengths) >= 3:
        summary_parts.append(f"with {len(strengths)} key strengths identified")

    # Role alignment
    summary_parts.append(f"at {role} level")

    base = ", ".join(summary_parts) + "."

    # Add recommendation nuance
    if coverage == "high" and len(strengths) >= 3:
        base += (
            " Candidate demonstrates patterns consistent with successful "
            "engineers in this context."
        )
    elif coverage == "medium":
        base += " Additional analysis recommended for complete assessment."
    else:
        base += " Run more comprehensive analyses for detailed evaluation."

    return base


def extract_github_stats(
    portfolio: Optional[PortfolioAnalysis],
    pr: Optional[PRAnalysisRecord],
    repos: Sequence[AnalysisResult],
    username: str,
) -> Dict[str, Any]:
    """
    Extract GitHub stats from available analyses.

    Priority: Portfolio > PR > Single Repo metadata
    """
    # Try to get stats from portfolio analysis metadata
    if portfolio and portfolio.full_analysis:
        try:
            full_data = json.loads(portfolio.full_analysis)
            metadata = full_data.get("metadata", {})
            if metadata:
                return {
                    "public_repos": portfolio.total_repos
                    or metadata.get("total_public_repos", 0),
                    "total_commits": metadata.get("total_commits", 0),  # If available
                    "created_at": metadata.get("account_created", ""),
                    "avatar_url": f"https://github.com/{username}.png",
                }
        except (json.JSONDecodeError, KeyError):
            pass

    # Fallback: PR analysis doesn't have detailed metadata (it's in PRAnalysisResult)
    # Skip PR fallback, move to simpler defaults

    # Fallback: Use portfolio repo counts or defaults
    return {
        "public_repos": portfolio.total_repos if portfolio else len(repos),
        "total_commits": 0,  # Unknown
        "created_at": "",  # Unknown
        "avatar_url": f"https://github.com/{username}.png",
    }


def format_portfolio_summary(analysis: PortfolioAnalysis) -> Dict[str, Any]:
    """Format portfolio analysis for hub display."""

    # Extract executive summary from full analysis
    executive_summary = ""
    if analysis.full_analysis:
        try:
            full_data = json.loads(analysis.full_analysis)
            result = full_data.get("result", {})
            executive_summary = result.get("summary", "")[:300]  # First 300 chars
        except (json.JSONDecodeError, KeyError):
            pass

    return {
        "id": analysis.id,
        "created_at": analysis.created_at.isoformat(),
        "context": analysis.context,
        "role": "senior",  # Extract from full_analysis if needed
        "executive_summary": executive_summary,
        "total_repos": analysis.total_repos,
        "repos_analyzed": analysis.repos_analyzed,
    }


def format_pr_summary(
    analysis: PRAnalysisRecord, result: Optional[PRAnalysisResult] = None
) -> Dict[str, Any]:
    """Format PR analysis for hub display."""
    summary_data = {
        "id": analysis.analysis_id,  # Link to PRAnalysisResult
        "created_at": analysis.created_at.isoformat(),
        "context": analysis.context,
        "total_prs": analysis.pr_count,
        "status": analysis.status,
    }

    # Add executive summary if result is available
    if result and result.summary_report:
        try:
            # summary_report is a Markdown string, not JSON
            # Parse the Executive Summary section from the markdown
            summary_report = result.summary_report

            # Extract text between "## Executive Summary" and next "##" section
            if "## Executive Summary" in summary_report:
                start = summary_report.index("## Executive Summary") + len(
                    "## Executive Summary"
                )
                # Find the next section marker
                next_section = summary_report.find("##", start)
                if next_section != -1:
                    executive_summary = summary_report[start:next_section].strip()
                else:
                    executive_summary = summary_report[start:].strip()

                # Clean up: replace \n with spaces, remove extra whitespace
                executive_summary = executive_summary.replace("\\n", " ").replace(
                    "\n", " "
                )
                executive_summary = " ".join(
                    executive_summary.split()
                )  # Remove extra spaces

                # Take first 500 chars
                executive_summary = (
                    executive_summary[:500]
                    if len(executive_summary) > 500
                    else executive_summary
                )
                summary_data["executive_summary"] = executive_summary
        except (ValueError, AttributeError, IndexError) as e:
            logger.warning(
                f"Failed to parse executive summary from PR analysis {summary_data['id']}: {e}. "
                "Leaving executive_summary field empty."
            )
            # executive_summary remains empty string (default)

    return summary_data


def format_single_repo_summary(analysis: AnalysisResult) -> Dict[str, Any]:
    """Format single repo analysis for hub display."""
    return {
        "id": analysis.id,
        "repository_name": analysis.repository_name,
        "created_at": analysis.created_at.isoformat(),
        "context": analysis.context,
    }
