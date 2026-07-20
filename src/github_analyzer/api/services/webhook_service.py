# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Webhook processing service.

This module provides centralized webhook processing with
idempotency, error handling, and retry mechanisms.
"""

import json
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ...billing.webhook_handlers import WEBHOOK_HANDLERS
from ...database.models import WebhookEvent
from ...database.operations import WebhookEventOperations
from ...utils.logging import get_logger

logger = get_logger(__name__)


class WebhookService:
    """
    Service for processing Stripe webhooks.

    Provides centralized webhook processing with proper
    error handling, idempotency, and monitoring.
    """

    async def process_webhook(
        self, db: AsyncSession, event: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a webhook event.

        Args:
            db: Database session
            event: Webhook event data

        Returns:
            Processing result
        """
        event_id = event.get("id")
        event_type = event.get("type")

        # Check for duplicate processing
        if event_id:
            existing = await WebhookEventOperations.get_webhook_event(db, event_id)
            if existing and existing.status == "processed":
                return {
                    "status": "already_processed",
                    "event_id": event_id,
                }

        # Create webhook event record
        if event_id and event_type:
            await WebhookEventOperations.create_webhook_event(
                db=db,
                event_id=event_id,
                stripe_event_id=event_id,
                event_type=event_type,
                event_data=event,
                status="pending",
            )

        # Process the event
        if event_type:
            handler = WEBHOOK_HANDLERS.get(event_type)
            if handler:
                try:
                    result = await handler(db, event)
                    if event_id:
                        await WebhookEventOperations.update_webhook_status(
                            db, event_id, status="processed"
                        )
                    return result
                except Exception as e:
                    if event_id:
                        await WebhookEventOperations.update_webhook_status(
                            db, event_id, status="failed", error=str(e)
                        )
                    raise
        return {"status": "ignored", "reason": "No handler for event type"}

    async def retry_failed_webhooks(
        self, db: AsyncSession, max_attempts: int = 5
    ) -> Dict[str, Any]:
        """
        Retry processing of failed webhooks.

        Args:
            db: Database session
            max_attempts: Maximum retry attempts

        Returns:
            Retry results
        """
        failed_webhooks = await WebhookEventOperations.get_failed_webhooks(
            db, max_attempts
        )

        total = len(failed_webhooks)
        successful = 0
        failed = 0

        for webhook in failed_webhooks:
            handler = WEBHOOK_HANDLERS.get(webhook.event_type)
            if handler:
                try:
                    event_data = self.get_event_data(webhook)
                    if event_data:
                        await handler(db, event_data)
                        await WebhookEventOperations.update_webhook_status(
                            db, webhook.event_id, status="processed"
                        )
                        successful += 1
                    else:
                        failed += 1
                except Exception as e:
                    await WebhookEventOperations.update_webhook_status(
                        db, webhook.event_id, status="failed", error=str(e)
                    )
                    failed += 1
            else:
                failed += 1

        return {
            "total_webhooks": total,
            "successful_retries": successful,
            "failed_retries": failed,
        }

    async def cleanup_old_webhooks(
        self, db: AsyncSession, days: int = 30
    ) -> Dict[str, Any]:
        """
        Clean up old processed webhooks.

        Args:
            db: Database session
            days: Days to keep webhooks

        Returns:
            Cleanup results
        """
        deleted_count = await WebhookEventOperations.delete_old_webhooks(db, days=days)
        return {"deleted_count": deleted_count}

    async def get_webhook_statistics(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Get webhook processing statistics.

        Args:
            db: Database session

        Returns:
            Webhook statistics
        """
        return await WebhookEventOperations.get_webhook_statistics(db)

    def get_event_data(self, webhook: WebhookEvent) -> Optional[Dict[str, Any]]:
        """Safely parse and return event data from a webhook record."""
        try:
            if isinstance(webhook.event_data, str):
                event_data: Dict[str, Any] = json.loads(webhook.event_data)
                return event_data
            elif isinstance(webhook.event_data, dict):
                return webhook.event_data
        except json.JSONDecodeError:
            return None
        return None
