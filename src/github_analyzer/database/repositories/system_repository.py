# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
System repository for database operations related to system metrics, webhooks, and contact messages.
"""

import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import ContactMessage, ContactStatus, SystemMetric, WebhookEvent
from ..rowcount import affected_rows


class SystemRepository:
    """Repository for system metrics and general operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_metric(
        self,
        metric_name: str,
        metric_type: str,
        metric_value: Dict[str, Any],
        labels: Optional[Dict[str, Any]] = None,
    ) -> SystemMetric:
        """
        Record a system metric.
        """
        metric_id = f"metric_{secrets.token_urlsafe(16)}"

        metric = SystemMetric(
            metric_id=metric_id,
            metric_name=metric_name,
            metric_type=metric_type,
            metric_value=json.dumps(metric_value),
            labels=json.dumps(labels) if labels else None,
        )

        self.db.add(metric)
        await self.db.flush()
        return metric

    async def get_metrics(
        self,
        metric_name: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[SystemMetric]:
        """
        Get system metrics with optional filters.
        """
        query = select(SystemMetric)

        if metric_name:
            query = query.where(SystemMetric.metric_name == metric_name)

        if start_date:
            query = query.where(SystemMetric.timestamp >= start_date)

        if end_date:
            query = query.where(SystemMetric.timestamp <= end_date)

        query = query.order_by(SystemMetric.timestamp.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_metric_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get metric summary for the last N hours (admin dashboard).
        """
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        # Get total metrics count
        total_result = await self.db.execute(
            select(func.count(SystemMetric.metric_id)).where(
                SystemMetric.timestamp >= start_time
            )
        )
        total_metrics = total_result.scalar() or 0

        # Get metrics by type
        type_result = await self.db.execute(
            select(SystemMetric.metric_type, func.count(SystemMetric.metric_id))
            .where(SystemMetric.timestamp >= start_time)
            .group_by(SystemMetric.metric_type)
        )

        metrics_by_type = {row[0]: row[1] for row in type_result}

        return {
            "total_metrics": total_metrics,
            "metrics_by_type": metrics_by_type,
            "time_window_hours": hours,
            "start_time": start_time.isoformat(),
        }


class WebhookRepository:
    """Repository for webhook event tracking."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_webhook_event(
        self,
        event_id: str,
        stripe_event_id: str,
        event_type: str,
        event_data: Dict[str, Any],
        status: str = "pending",
    ) -> WebhookEvent:
        """Create a new webhook event record."""
        webhook_event = WebhookEvent(
            event_id=event_id,
            stripe_event_id=stripe_event_id,
            event_type=event_type,
            event_data=json.dumps(event_data),
            status=status,
            attempts=0,
        )

        try:
            self.db.add(webhook_event)
            await self.db.commit()
            await self.db.refresh(webhook_event)
            return webhook_event
        except Exception:
            # Event might already exist (idempotency)
            await self.db.rollback()
            existing = await self.get_webhook_event(event_id)
            if existing:
                return existing
            raise

    async def get_webhook_event(self, event_id: str) -> Optional[WebhookEvent]:
        """Get webhook event by ID."""
        result = await self.db.execute(
            select(WebhookEvent).where(WebhookEvent.event_id == event_id)
        )
        return result.scalar_one_or_none()

    async def mark_event_processed(
        self, event_id: str, processing_result: str, success: bool = True
    ) -> bool:
        """Mark webhook event as processed."""
        update_data = {
            "status": "processed" if success else "failed",
            "processing_result": processing_result,
            "processed_at": datetime.now(timezone.utc) if success else None,
            "last_attempt_at": datetime.now(timezone.utc),
        }

        # Increment processing attempts
        result = await self.db.execute(
            update(WebhookEvent)
            .where(WebhookEvent.event_id == event_id)
            .values(attempts=WebhookEvent.attempts + 1, **update_data)
        )

        await self.db.commit()
        return affected_rows(result) > 0

    async def get_unprocessed_events(
        self, limit: int = 50, max_attempts: int = 3
    ) -> List[WebhookEvent]:
        """Get unprocessed webhook events."""
        result = await self.db.execute(
            select(WebhookEvent)
            .where(
                and_(
                    WebhookEvent.status == "pending",
                    WebhookEvent.attempts < max_attempts,
                )
            )
            .order_by(WebhookEvent.created_at)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def mark_event_failed(self, event_id: str, error_message: str) -> bool:
        """Mark webhook event as failed."""
        result = await self.db.execute(
            update(WebhookEvent)
            .where(WebhookEvent.event_id == event_id)
            .values(
                last_error=error_message,
                last_attempt_at=datetime.now(timezone.utc),
                attempts=WebhookEvent.attempts + 1,
                status="failed",
            )
        )

        await self.db.commit()
        return affected_rows(result) > 0

    async def cleanup_old_events(self, days_old: int = 30) -> int:
        """Clean up old processed webhook events."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)

        result = await self.db.execute(
            delete(WebhookEvent).where(
                and_(
                    WebhookEvent.status == "processed",
                    WebhookEvent.processed_at < cutoff_date,
                )
            )
        )

        await self.db.commit()
        return affected_rows(result)

    async def get_failed_webhooks(self, max_attempts: int = 5) -> List[WebhookEvent]:
        """Get failed webhook events for retry."""
        result = await self.db.execute(
            select(WebhookEvent).where(
                and_(
                    WebhookEvent.status == "failed",
                    WebhookEvent.attempts < max_attempts,
                )
            )
        )
        return list(result.scalars().all())

    async def update_webhook_status(
        self,
        event_id: str,
        status: str,
        error: Optional[str] = None,
        processing_time: Optional[int] = None,
    ) -> bool:
        """Update webhook event status."""
        update_data: Dict[str, Any] = {
            "status": status,
            "last_attempt_at": datetime.now(timezone.utc),
        }
        if error:
            update_data["last_error"] = error
        if status == "processed":
            update_data["processed_at"] = datetime.now(timezone.utc)
        # Note: processing_time is not persisted; the WebhookEvent model has no
        # such column yet.

        result = await self.db.execute(
            update(WebhookEvent)
            .where(WebhookEvent.event_id == event_id)
            .values(update_data)
        )

        await self.db.commit()
        return affected_rows(result) > 0

    async def delete_old_webhooks(self, days: int = 30) -> int:
        """Delete old processed webhook events."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        result = await self.db.execute(
            delete(WebhookEvent).where(
                and_(
                    WebhookEvent.status == "processed",
                    WebhookEvent.created_at < cutoff_date,
                )
            )
        )

        await self.db.commit()
        return affected_rows(result)

    async def get_webhook_statistics(self) -> Dict[str, Any]:
        """Get webhook processing statistics."""
        total_result = await self.db.execute(select(func.count(WebhookEvent.event_id)))
        total_webhooks = total_result.scalar() or 0

        status_result = await self.db.execute(
            select(WebhookEvent.status, func.count(WebhookEvent.event_id)).group_by(
                WebhookEvent.status
            )
        )

        status_counts = {row[0]: row[1] for row in status_result}
        processed = status_counts.get("processed", 0)
        failed = status_counts.get("failed", 0)
        pending = status_counts.get("pending", 0)

        type_result = await self.db.execute(
            select(WebhookEvent.event_type, func.count(WebhookEvent.event_id)).group_by(
                WebhookEvent.event_type
            )
        )

        events_by_type = {row[0]: row[1] for row in type_result}

        # Average processing time (stub for now)
        average_processing_time = 250  # milliseconds

        return {
            "total_webhooks": total_webhooks,
            "processed": processed,
            "failed": failed,
            "pending": pending,
            "success_rate": (
                (processed / total_webhooks * 100) if total_webhooks > 0 else 0
            ),
            "average_processing_time": average_processing_time,
            "events_by_type": events_by_type,
        }


class ContactRepository:
    """Repository for contact messages."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_message(
        self,
        name: str,
        email: str,
        subject: str,
        message: str,
        user_id: Optional[str] = None,
    ) -> ContactMessage:
        """
        Create a new contact message.
        """
        # Generate message ID
        message_id = f"msg_{secrets.token_urlsafe(16)}"

        # Create message
        contact_message = ContactMessage(
            message_id=message_id,
            user_id=user_id,
            name=name,
            email=email,
            subject=subject,
            message=message,
            status=ContactStatus.UNREAD,
        )

        self.db.add(contact_message)
        await self.db.commit()
        await self.db.refresh(contact_message)
        return contact_message

    async def get_message_by_id(self, message_id: str) -> Optional[ContactMessage]:
        """
        Get contact message by ID.
        """
        result = await self.db.execute(
            select(ContactMessage).where(ContactMessage.message_id == message_id)
        )
        return result.scalar_one_or_none()

    async def get_messages(
        self,
        status: Optional[ContactStatus] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[List[ContactMessage], int]:
        """
        Get paginated list of contact messages.
        """
        # Build query
        query = select(ContactMessage)
        count_query = select(func.count()).select_from(ContactMessage)

        if status:
            query = query.where(ContactMessage.status == status)
            count_query = count_query.where(ContactMessage.status == status)

        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Get messages
        query = (
            query.order_by(ContactMessage.created_at.desc()).limit(limit).offset(offset)
        )
        result = await self.db.execute(query)
        messages = list(result.scalars().all())

        return messages, total

    async def get_messages_by_user_id(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[List[ContactMessage], int]:
        """Get paginated list of contact messages for a specific user."""
        query = select(ContactMessage).where(ContactMessage.user_id == user_id)
        count_query = (
            select(func.count())
            .select_from(ContactMessage)
            .where(ContactMessage.user_id == user_id)
        )

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = (
            query.order_by(ContactMessage.created_at.desc()).limit(limit).offset(offset)
        )
        result = await self.db.execute(query)
        messages = list(result.scalars().all())

        return messages, total

    async def update_message_status(
        self,
        message_id: str,
        status: ContactStatus,
    ) -> bool:
        """
        Update message status.
        """
        message = await self.get_message_by_id(message_id)
        if not message:
            return False

        message.status = status
        await self.db.flush()
        return True

    async def add_admin_response(
        self,
        message_id: str,
        admin_user_id: str,
        admin_response: str,
    ) -> bool:
        """
        Add admin response to a contact message.
        """
        message = await self.get_message_by_id(message_id)
        if not message:
            return False

        message.admin_response = admin_response
        message.responded_at = datetime.now(timezone.utc)
        message.responded_by = admin_user_id
        message.status = ContactStatus.RESPONDED

        await self.db.flush()
        return True

    async def get_unread_count(self) -> int:
        """
        Get count of unread messages.
        """
        result = await self.db.execute(
            select(func.count())
            .select_from(ContactMessage)
            .where(ContactMessage.status == ContactStatus.UNREAD)
        )
        return result.scalar() or 0
