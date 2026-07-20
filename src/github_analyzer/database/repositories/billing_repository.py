# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Billing repository for database operations related to invoices, payments, and usage tracking.
"""

import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import (
    BillingUsageRecord,
    Invoice,
    Payment,
    UsageRecord,
    User,
)
from ..rowcount import affected_rows


class BillingRepository:
    """Repository for billing and usage operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_invoice(
        self,
        invoice_id: str,
        user_id: str,
        stripe_invoice_id: str,
        stripe_customer_id: str,
        amount_due: int,
        currency: str,
        status: str,
        billing_period_start: datetime,
        billing_period_end: datetime,
        amount_paid: Optional[int] = None,
        description: Optional[str] = None,
        invoice_url: Optional[str] = None,
        due_date: Optional[datetime] = None,
    ) -> Invoice:
        """Create a new invoice record."""
        invoice = Invoice(
            invoice_id=invoice_id,
            user_id=user_id,
            stripe_invoice_id=stripe_invoice_id,
            stripe_customer_id=stripe_customer_id,
            amount_due=amount_due,
            amount_paid=amount_paid if amount_paid is not None else 0,
            currency=currency,
            status=status,
            billing_period_start=billing_period_start,
            billing_period_end=billing_period_end,
            description=description,
            invoice_url=invoice_url,
            due_date=due_date,
        )

        self.db.add(invoice)
        await self.db.commit()
        await self.db.refresh(invoice)
        return invoice

    async def get_invoice_by_id(self, invoice_id: str) -> Optional[Invoice]:
        """Get invoice by ID."""
        result = await self.db.execute(
            select(Invoice).where(Invoice.invoice_id == invoice_id)
        )
        return result.scalar_one_or_none()

    async def get_invoice_by_stripe_id(
        self, stripe_invoice_id: str
    ) -> Optional[Invoice]:
        """Get invoice by Stripe invoice ID."""
        result = await self.db.execute(
            select(Invoice).where(Invoice.stripe_invoice_id == stripe_invoice_id)
        )
        return result.scalar_one_or_none()

    async def get_user_invoices(
        self, user_id: str, limit: int = 10, offset: int = 0
    ) -> List[Invoice]:
        """Get invoices for a user."""
        result = await self.db.execute(
            select(Invoice)
            .where(Invoice.user_id == user_id)
            .order_by(Invoice.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def update_invoice_status(
        self,
        invoice_id: str,
        status: str,
        amount_paid: Optional[int] = None,
        paid_at: Optional[datetime] = None,
    ) -> bool:
        """Update invoice status and payment details."""
        update_data: Dict[str, Any] = {"status": status}
        if amount_paid is not None:
            update_data["amount_paid"] = amount_paid
        if paid_at is not None:
            update_data["paid_at"] = paid_at

        result = await self.db.execute(
            update(Invoice)
            .where(Invoice.invoice_id == invoice_id)
            .values(**update_data)
        )

        await self.db.commit()
        return affected_rows(result) > 0

    async def get_invoices_by_status(
        self, status: str, limit: int = 50
    ) -> List[Invoice]:
        """Get invoices by status."""
        result = await self.db.execute(
            select(Invoice)
            .where(Invoice.status == status)
            .order_by(Invoice.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_recent_invoices(self, limit: int = 50) -> List[Invoice]:
        """Get recent invoices regardless of status."""
        result = await self.db.execute(
            select(Invoice).order_by(Invoice.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def create_payment(
        self,
        payment_id: str,
        user_id: str,
        stripe_payment_intent_id: str,
        stripe_customer_id: str,
        amount: int,
        currency: str,
        status: str,
        payment_method: str,
        invoice_id: Optional[str] = None,
        payment_method_details: Optional[str] = None,
        failure_code: Optional[str] = None,
        failure_message: Optional[str] = None,
        processed_at: Optional[datetime] = None,
    ) -> Payment:
        """Create a new payment record."""
        payment = Payment(
            payment_id=payment_id,
            user_id=user_id,
            invoice_id=invoice_id,
            stripe_payment_intent_id=stripe_payment_intent_id,
            stripe_customer_id=stripe_customer_id,
            amount=amount,
            currency=currency,
            status=status,
            payment_method=payment_method,
            payment_method_details=payment_method_details,
            failure_code=failure_code,
            failure_message=failure_message,
            processed_at=processed_at,
        )

        self.db.add(payment)
        await self.db.commit()
        await self.db.refresh(payment)
        return payment

    async def get_payment_by_id(self, payment_id: str) -> Optional[Payment]:
        """Get payment by ID."""
        result = await self.db.execute(
            select(Payment).where(Payment.payment_id == payment_id)
        )
        return result.scalar_one_or_none()

    async def get_payment_by_stripe_id(
        self, stripe_payment_intent_id: str
    ) -> Optional[Payment]:
        """Get payment by Stripe payment intent ID."""
        result = await self.db.execute(
            select(Payment).where(
                Payment.stripe_payment_intent_id == stripe_payment_intent_id
            )
        )
        return result.scalar_one_or_none()

    async def get_user_payments(
        self, user_id: str, limit: int = 10, offset: int = 0
    ) -> List[Payment]:
        """Get payments for a user."""
        result = await self.db.execute(
            select(Payment)
            .where(Payment.user_id == user_id)
            .order_by(Payment.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def update_payment_status(
        self,
        payment_id: str,
        status: str,
        processed_at: Optional[datetime] = None,
        failure_code: Optional[str] = None,
        failure_message: Optional[str] = None,
    ) -> bool:
        """Update payment status and processing details."""
        update_data: Dict[str, Any] = {"status": status}
        if processed_at is not None:
            update_data["processed_at"] = processed_at
        if failure_code is not None:
            update_data["failure_code"] = failure_code
        if failure_message is not None:
            update_data["failure_message"] = failure_message

        result = await self.db.execute(
            update(Payment)
            .where(Payment.payment_id == payment_id)
            .values(**update_data)
        )

        await self.db.commit()
        return affected_rows(result) > 0

    async def get_payments_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[Payment]:
        """Get payments within a date range."""
        result = await self.db.execute(
            select(Payment)
            .where(
                and_(
                    Payment.created_at >= start_date,
                    Payment.created_at <= end_date,
                )
            )
            .order_by(Payment.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_usage_record(
        self,
        record_id: str,
        user_id: str,
        usage_type: str,
        usage_count: int = 1,
        billing_period: Optional[str] = None,
        unit_cost: str = "0.00",
        total_cost: str = "0.00",
        metadata: Optional[str] = None,
    ) -> BillingUsageRecord:
        """Create a new billing usage record."""
        if billing_period is None:
            billing_period = datetime.now(timezone.utc).strftime("%Y-%m")

        usage_record = BillingUsageRecord(
            record_id=record_id,
            user_id=user_id,
            usage_type=usage_type,
            usage_count=usage_count,
            billing_period=billing_period,
            unit_cost=unit_cost,
            total_cost=total_cost,
            request_metadata=metadata,
        )

        self.db.add(usage_record)
        await self.db.commit()
        await self.db.refresh(usage_record)
        return usage_record

    async def get_user_usage_for_period(
        self,
        user_id: str,
        billing_period: str,
        usage_type: Optional[str] = None,
    ) -> List[BillingUsageRecord]:
        """Get user usage records for a billing period."""
        query = select(BillingUsageRecord).where(
            and_(
                BillingUsageRecord.user_id == user_id,
                BillingUsageRecord.billing_period == billing_period,
            )
        )

        if usage_type:
            query = query.where(BillingUsageRecord.usage_type == usage_type)

        result = await self.db.execute(query.order_by(BillingUsageRecord.created_at))
        return list(result.scalars().all())

    async def get_usage_summary_for_period(
        self, user_id: str, billing_period: str
    ) -> Dict[str, int]:
        """Get usage summary by type for a billing period."""
        result = await self.db.execute(
            select(
                BillingUsageRecord.usage_type, func.sum(BillingUsageRecord.usage_count)
            )
            .where(
                and_(
                    BillingUsageRecord.user_id == user_id,
                    BillingUsageRecord.billing_period == billing_period,
                )
            )
            .group_by(BillingUsageRecord.usage_type)
        )

        return {row[0]: row[1] for row in result}

    async def mark_usage_reported_to_stripe(
        self, record_id: str, stripe_usage_record_id: str
    ) -> bool:
        """Mark usage record as reported to Stripe."""
        result = await self.db.execute(
            update(BillingUsageRecord)
            .where(BillingUsageRecord.record_id == record_id)
            .values(
                stripe_usage_record_id=stripe_usage_record_id,
                reported_to_stripe=True,
                reported_at=datetime.now(timezone.utc),
            )
        )

        await self.db.commit()
        return affected_rows(result) > 0

    async def get_unreported_usage(self, limit: int = 100) -> List[BillingUsageRecord]:
        """Get usage records not yet reported to Stripe."""
        result = await self.db.execute(
            select(BillingUsageRecord)
            .where(BillingUsageRecord.reported_to_stripe.is_(False))
            .order_by(BillingUsageRecord.created_at)
            .limit(limit)
        )
        return list(result.scalars().all())


class UsageRepository:
    """Repository for API usage tracking."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_usage(
        self,
        user_id: str,
        endpoint: str,
        method: str,
        repository_url: Optional[str],
        tokens_consumed: int,
        cost_incurred: str,
        response_time_ms: int,
        success: bool,
        error_message: Optional[str] = None,
    ) -> UsageRecord:
        """
        Record a usage event.
        """
        record_id = f"usage_{secrets.token_urlsafe(16)}"

        usage_record = UsageRecord(
            record_id=record_id,
            user_id=user_id,
            endpoint=endpoint,
            method=method,
            repository_url=repository_url,
            tokens_consumed=tokens_consumed,
            cost_incurred=cost_incurred,
            response_time_ms=response_time_ms,
            success=success,
            error_message=error_message,
        )

        self.db.add(usage_record)
        await self.db.flush()

        # Update user's usage consumed
        curr_user = await self.db.get(User, user_id)
        if curr_user:
            curr_user.usage_count += 1
            await self.db.flush()

        return usage_record

    async def get_user_usage(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[UsageRecord]:
        """
        Get usage records for a user.
        """
        query = select(UsageRecord).where(UsageRecord.user_id == user_id)

        if start_date:
            query = query.where(UsageRecord.created_at >= start_date)

        if end_date:
            query = query.where(UsageRecord.created_at <= end_date)

        query = query.order_by(UsageRecord.created_at.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())
