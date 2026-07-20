# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Budget monitoring endpoints.

Provides REST API endpoints for checking budget status and spending history.
"""

from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from ...utils.logging import get_logger
from ..auth.dependencies import require_api_access
from ..services.budget_dependencies import get_budget_monitor
from ..services.budget_monitor import BudgetMonitor

logger = get_logger(__name__)

router = APIRouter()


@router.get("/budget/status")
async def get_budget_status(
    user_id: str = Depends(require_api_access),
    budget_monitor: BudgetMonitor = Depends(get_budget_monitor),
) -> Dict[str, Any]:
    """
    Get current budget status and warnings.

    Returns:
        Budget status with spending information and any warnings
    """
    try:
        status = await budget_monitor.check_budget_status()

        # Add user-specific spending
        user_daily_spending = await budget_monitor.get_user_daily_spending(user_id)
        status["user_daily_spending"] = user_daily_spending

        return {
            "status": "ok" if not status["warnings"] else "warning",
            "budget": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get budget status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to retrieve budget status",
                "message": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )


@router.get("/budget/spending")
async def get_spending_summary(
    user_id: str = Depends(require_api_access),
    budget_monitor: BudgetMonitor = Depends(get_budget_monitor),
) -> Dict[str, Any]:
    """
    Get spending summary for the current user.

    Returns:
        Spending summary with daily and monthly totals
    """
    try:
        daily_total = await budget_monitor.get_daily_spending()
        monthly_total = await budget_monitor.get_monthly_spending()
        user_daily = await budget_monitor.get_user_daily_spending(user_id)

        return {
            "spending": {
                "daily": {
                    "total": daily_total,
                    "user": user_daily,
                },
                "monthly": {
                    "total": monthly_total,
                },
            },
            "estimates": {
                "analyses_today": int(daily_total / 0.002) if daily_total > 0 else 0,
                "analyses_this_month": (
                    int(monthly_total / 0.002) if monthly_total > 0 else 0
                ),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get spending summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to retrieve spending summary",
                "message": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
