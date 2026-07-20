# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Priority support service for paid tier users.

Enhances the existing ContactMessage system with priority handling and SLA tracking.
- Scale+: 4 hour SLA (priority level 3)
- Scale/Enterprise: 12 hour SLA (priority level 2)
- Professional: 24 hour SLA (priority level 1)
- Basic/Free: 48 hour standard response
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from github_analyzer.database.models import (
    ContactMessage,
    ContactStatus,
    SubscriptionPlan,
    User,
)

logger = logging.getLogger(__name__)


class PrioritySupportService:
    """Service for enhancing ContactMessage system with priority support for Scale+ and Enterprise users."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def enhance_message_with_priority(
        self, message: ContactMessage, user: Optional[User] = None
    ) -> ContactMessage:
        """
        Enhance a contact message with priority settings based on user's subscription.

        Scale+ users get priority level 3 (URGENT) with 4 hour SLA.
        Enterprise/Scale users get priority level 2 (HIGH) with 12 hour SLA.
        Professional users get priority level 1 (MEDIUM) with 24 hour SLA.
        Basic/Free users get standard 48 hour response time.
        """
        if user:
            if user.subscription_plan == SubscriptionPlan.SCALE_PLUS:
                message.is_priority = True
                message.priority_level = 3  # URGENT
                message.target_response_hours = 4
                logger.info(f"Set URGENT priority for Scale+ user {user.user_id}")
            elif user.subscription_plan == SubscriptionPlan.ENTERPRISE:
                message.is_priority = True
                message.priority_level = 2  # HIGH
                message.target_response_hours = 12
                logger.info(f"Set HIGH priority for Enterprise user {user.user_id}")
            elif user.subscription_plan == SubscriptionPlan.PROFESSIONAL:
                message.is_priority = True
                message.priority_level = 1  # MEDIUM
                message.target_response_hours = 24
                logger.info(f"Set MEDIUM priority for Professional user {user.user_id}")
            else:
                # Basic and Free users - standard response time
                message.is_priority = False
                message.priority_level = 0
                message.target_response_hours = 48

        return message

    async def update_sla_status(self, message: ContactMessage) -> ContactMessage:
        """Update SLA status based on current time and response status."""
        if not message.is_priority:
            return message

        now = datetime.now(timezone.utc)
        time_since_created = (now - message.created_at).total_seconds() / 3600  # hours

        if message.status == ContactStatus.UNREAD:
            # No response yet
            if time_since_created < message.target_response_hours * 0.5:
                message.sla_status = "green"  # Less than 50% of SLA
            elif time_since_created < message.target_response_hours * 0.8:
                message.sla_status = "yellow"  # 50-80% of SLA
            elif time_since_created < message.target_response_hours:
                message.sla_status = "orange"  # 80-100% of SLA
            else:
                message.sla_status = "red"  # SLA breached
        else:
            # Already responded
            if message.responded_at:
                response_time = (
                    message.responded_at - message.created_at
                ).total_seconds() / 3600
                if response_time <= message.target_response_hours:
                    message.sla_status = "green"  # Met SLA
                else:
                    message.sla_status = "red"  # Missed SLA
            else:
                message.sla_status = (
                    "green"  # Marked as read/responded but no timestamp
                )

        return message

    async def get_priority_messages(
        self,
        status_filter: Optional[ContactStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[ContactMessage], int]:
        """Get priority messages sorted by urgency."""
        query = select(ContactMessage).where(ContactMessage.is_priority)

        if status_filter:
            query = query.where(ContactMessage.status == status_filter)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Get messages sorted by priority level (highest first) and created date
        query = (
            query.order_by(
                desc(ContactMessage.priority_level),
                ContactMessage.created_at,
            )
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(query)
        messages = result.scalars().all()

        # Update SLA status for each message
        for message in messages:
            await self.update_sla_status(message)

        return list(messages), total

    async def get_sla_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Get SLA performance metrics for priority support."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        # Get all priority messages in the period
        query = select(ContactMessage).where(
            and_(
                ContactMessage.is_priority,
                ContactMessage.created_at >= cutoff_date,
            )
        )
        result = await self.db.execute(query)
        messages = result.scalars().all()

        if not messages:
            return {
                "total_priority_messages": 0,
                "sla_met_count": 0,
                "sla_missed_count": 0,
                "sla_compliance_rate": 100.0,
                "average_response_time_hours": None,
                "by_priority_level": {},
            }

        sla_met = 0
        sla_missed = 0
        response_times = []
        by_priority = {
            0: {"met": 0, "missed": 0},
            1: {"met": 0, "missed": 0},
            2: {"met": 0, "missed": 0},
            3: {"met": 0, "missed": 0},
        }

        for message in messages:
            if message.responded_at:
                response_time = (
                    message.responded_at - message.created_at
                ).total_seconds() / 3600
                response_times.append(response_time)

                if response_time <= message.target_response_hours:
                    sla_met += 1
                    by_priority[message.priority_level]["met"] += 1
                else:
                    sla_missed += 1
                    by_priority[message.priority_level]["missed"] += 1
            else:
                # Not yet responded - check if SLA is already breached
                time_since_created = (
                    datetime.now(timezone.utc) - message.created_at
                ).total_seconds() / 3600
                if time_since_created > message.target_response_hours:
                    sla_missed += 1
                    by_priority[message.priority_level]["missed"] += 1

        total_evaluated = sla_met + sla_missed
        compliance_rate = (
            (sla_met / total_evaluated * 100) if total_evaluated > 0 else 100.0
        )
        avg_response_time = (
            sum(response_times) / len(response_times) if response_times else None
        )

        return {
            "total_priority_messages": len(messages),
            "sla_met_count": sla_met,
            "sla_missed_count": sla_missed,
            "sla_compliance_rate": round(compliance_rate, 2),
            "average_response_time_hours": (
                round(avg_response_time, 2) if avg_response_time else None
            ),
            "by_priority_level": {
                level: {
                    "met": stats["met"],
                    "missed": stats["missed"],
                    "compliance_rate": (
                        round(stats["met"] / (stats["met"] + stats["missed"]) * 100, 2)
                        if (stats["met"] + stats["missed"]) > 0
                        else 100.0
                    ),
                }
                for level, stats in by_priority.items()
                if stats["met"] + stats["missed"] > 0
            },
        }

    async def get_user_support_metrics(self, user_id: str) -> Dict[str, Any]:
        """Get support metrics for a specific user."""
        # Get user's messages
        query = select(ContactMessage).where(ContactMessage.user_id == user_id)
        result = await self.db.execute(query)
        messages = result.scalars().all()

        if not messages:
            return {
                "total_messages": 0,
                "priority_messages": 0,
                "average_response_time_hours": None,
                "messages_by_status": {},
            }

        priority_count = len([m for m in messages if m.is_priority])
        response_times = []

        for message in messages:
            if message.responded_at:
                response_time = (
                    message.responded_at - message.created_at
                ).total_seconds() / 3600
                response_times.append(response_time)

        avg_response = (
            sum(response_times) / len(response_times) if response_times else None
        )

        # Count by status
        status_counts = {}
        for status in ContactStatus:
            count = len([m for m in messages if m.status == status])
            if count > 0:
                status_counts[status.value] = count

        return {
            "total_messages": len(messages),
            "priority_messages": priority_count,
            "average_response_time_hours": (
                round(avg_response, 2) if avg_response else None
            ),
            "messages_by_status": status_counts,
        }

    async def check_priority_support_access(self, user_id: str) -> bool:
        """Check if user has access to priority support."""
        result = await self.db.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            return False

        return user.subscription_plan in [
            SubscriptionPlan.SCALE_PLUS,
            SubscriptionPlan.ENTERPRISE,
            SubscriptionPlan.PROFESSIONAL,
        ]
