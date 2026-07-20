# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Dashboard API routes.

Provides candidate aggregation and dashboard-specific data.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.connection import get_db_session
from ...database.models import AnalysisResult, PRAnalysisRecord, PRAnalysisResult, User
from ...database.models_portfolio import PortfolioAnalysis
from ..auth.dependencies import get_current_active_user

router = APIRouter()


def ensure_timezone_aware(dt: datetime) -> datetime:
    """Ensure datetime is timezone-aware (UTC if naive)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


@router.get(
    "/candidates",
    summary="Get dashboard candidates",
    description="Get aggregated candidate data for dashboard display (grouped by username)",
)
async def get_dashboard_candidates(
    limit: int = 10,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> List[Dict[str, Any]]:
    """
    Get candidates for dashboard display, grouped by GitHub username.

    Returns:
        List of candidates with:
        - username
        - avatar_url
        - has_portfolio (bool)
        - has_pr (bool)
        - repo_count (int)
        - latest_activity (datetime)
        - portfolio_summary (first 100 chars of executive summary from portfolio or PR analysis)
    """
    # Get all unique usernames from portfolio analyses
    portfolio_result = await db.execute(
        select(PortfolioAnalysis)
        .where(PortfolioAnalysis.user_id == user.user_id)
        .order_by(PortfolioAnalysis.created_at.desc())
    )
    portfolio_analyses = portfolio_result.scalars().all()

    # Build candidate dict keyed by username
    candidates_dict: Dict[str, Dict[str, Any]] = {}

    for portfolio in portfolio_analyses:
        username = portfolio.github_username
        if username not in candidates_dict:
            # Extract summary from full_analysis JSON
            summary = ""
            try:
                if portfolio.full_analysis:
                    full_data = json.loads(portfolio.full_analysis)
                    result = full_data.get("result", {})
                    summary = result.get("summary", "")[:100]
            except (json.JSONDecodeError, KeyError):
                pass

            candidates_dict[username] = {
                "username": username,
                "avatar_url": f"https://github.com/{username}.png",
                "has_portfolio": True,
                "has_pr": False,
                "repo_count": 0,
                "latest_activity": ensure_timezone_aware(portfolio.created_at),
                "portfolio_summary": summary,
            }

    # Get PR analyses for these usernames
    pr_result = await db.execute(
        select(PRAnalysisRecord).where(PRAnalysisRecord.user_id == user.user_id)
    )
    pr_analyses = pr_result.scalars().all()

    for pr in pr_analyses:
        username = pr.github_username

        # Try to fetch PR analysis result for summary
        pr_summary = ""
        if pr.analysis_id:
            pr_analysis_query = await db.execute(
                select(PRAnalysisResult).where(PRAnalysisResult.id == pr.analysis_id)
            )
            pr_analysis: Optional[PRAnalysisResult] = (
                pr_analysis_query.scalar_one_or_none()
            )
            if pr_analysis and pr_analysis.ai_insights:
                try:
                    ai_data = json.loads(pr_analysis.ai_insights)
                    pr_summary = ai_data.get("executive_summary", "")[:100]
                except (json.JSONDecodeError, KeyError):
                    pass

        if username in candidates_dict:
            candidates_dict[username]["has_pr"] = True
            # Update latest_activity if PR is more recent
            pr_created_at = ensure_timezone_aware(pr.created_at)
            if pr_created_at > candidates_dict[username]["latest_activity"]:
                candidates_dict[username]["latest_activity"] = pr_created_at
            # If no portfolio summary, use PR summary
            if not candidates_dict[username]["portfolio_summary"] and pr_summary:
                candidates_dict[username]["portfolio_summary"] = pr_summary
        else:
            # Username has PR but no portfolio
            candidates_dict[username] = {
                "username": username,
                "avatar_url": f"https://github.com/{username}.png",
                "has_portfolio": False,
                "has_pr": True,
                "repo_count": 0,
                "latest_activity": ensure_timezone_aware(pr.created_at),
                "portfolio_summary": pr_summary,
            }

    # Get single repo analyses - count repos per username
    repo_result = await db.execute(
        select(AnalysisResult).where(AnalysisResult.user_id == user.user_id)
    )
    repo_analyses = repo_result.scalars().all()

    for repo in repo_analyses:
        # Extract username from repository_name (format: "username/repo")
        if "/" in repo.repository_name:
            username = repo.repository_name.split("/")[0]

            if username in candidates_dict:
                candidates_dict[username]["repo_count"] += 1
                # Update latest_activity if repo analysis is more recent
                repo_created_at = ensure_timezone_aware(repo.created_at)
                if repo_created_at > candidates_dict[username]["latest_activity"]:
                    candidates_dict[username]["latest_activity"] = repo_created_at

    # Convert dict to list and sort by latest_activity
    candidates_list = list(candidates_dict.values())
    candidates_list.sort(key=lambda x: x["latest_activity"], reverse=True)

    # Limit results
    return candidates_list[:limit]
