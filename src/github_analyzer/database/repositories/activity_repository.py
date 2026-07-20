# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Activity repository for database operations related to user activity tracking.
"""

import json
import secrets
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import UserActivity


class ActivityRepository:
    """Repository for user activity tracking."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_activity(
        self,
        user_id: str,
        activity_type: str,
        activity_data: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> UserActivity:
        """
        Record a user activity event.
        """
        activity_id = f"act_{secrets.token_urlsafe(16)}"

        activity = UserActivity(
            activity_id=activity_id,
            user_id=user_id,
            activity_type=activity_type,
            activity_data=json.dumps(activity_data) if activity_data else None,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        self.db.add(activity)
        await self.db.flush()
        return activity

    async def get_user_activities(
        self,
        user_id: str,
        activity_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[UserActivity]:
        """
        Get user activities with optional filters.
        """
        query = select(UserActivity).where(UserActivity.user_id == user_id)

        if activity_type:
            query = query.where(UserActivity.activity_type == activity_type)

        if start_date:
            query = query.where(UserActivity.created_at >= start_date)

        if end_date:
            query = query.where(UserActivity.created_at <= end_date)

        query = query.order_by(UserActivity.created_at.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_recent_activities(self, limit: int = 100) -> List[UserActivity]:
        """Get recent activities across all users (admin function)."""
        query = (
            select(UserActivity).order_by(UserActivity.created_at.desc()).limit(limit)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())
