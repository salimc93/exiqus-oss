# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Database operations facade.

This module now delegates actual operations to specific repositories:
- UserRepository
- BillingRepository
- ActivityRepository
- SystemRepository

It is maintained for backward compatibility.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    APIKey,
    BillingUsageRecord,
    ContactMessage,
    ContactStatus,
    EmailVerificationToken,
    Invoice,
    Payment,
    SubscriptionPlan,
    SubscriptionStatus,
    SystemMetric,
    TokenBlacklist,
    UsageRecord,
    User,
    UserActivity,
    UserRole,
    WebhookEvent,
)
from .repositories.activity_repository import ActivityRepository
from .repositories.billing_repository import BillingRepository, UsageRepository
from .repositories.system_repository import (
    ContactRepository,
    SystemRepository,
    WebhookRepository,
)
from .repositories.user_repository import (
    APIKeyRepository,
    EmailVerificationRepository,
    TokenRepository,
    UserRepository,
)


class UserOperations:
    """Facade for user-related operations."""

    @staticmethod
    async def create_user(
        db: AsyncSession,
        email: str,
        password: str,
        full_name: str,
        company: Optional[str] = None,
        usage_quota: int = 100,
    ) -> User:
        """Create a new user account."""
        repo = UserRepository(db)
        return await repo.create_user(email, password, full_name, company, usage_quota)

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
        """Get user by ID."""
        repo = UserRepository(db)
        return await repo.get_user_by_id(user_id)

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        """Get user by email address."""
        repo = UserRepository(db)
        return await repo.get_user_by_email(email)

    @staticmethod
    async def authenticate_user(
        db: AsyncSession, email: str, password: str
    ) -> Optional[User]:
        """Authenticate user with email and password."""
        repo = UserRepository(db)
        return await repo.authenticate_user(email, password)

    @staticmethod
    async def update_last_login(db: AsyncSession, user_id: str) -> None:
        """Update user's last login timestamp."""
        repo = UserRepository(db)
        await repo.update_last_login(user_id)

    @staticmethod
    async def update_password(
        db: AsyncSession, user_id: str, new_password: str
    ) -> bool:
        """Update user password."""
        repo = UserRepository(db)
        return await repo.update_password(user_id, new_password)

    @staticmethod
    async def update_usage_quota(
        db: AsyncSession, user_id: str, new_quota: int
    ) -> bool:
        """Update user's usage quota."""
        repo = UserRepository(db)
        return await repo.update_usage_quota(user_id, new_quota)

    @staticmethod
    async def update_user_profile(
        db: AsyncSession,
        user_id: str,
        full_name: Optional[str] = None,
        company: Optional[str] = None,
        company_size: Optional[str] = None,
        industry: Optional[str] = None,
        use_case: Optional[str] = None,
        notification_preferences: Optional[str] = None,
    ) -> bool:
        """Update user profile information."""
        repo = UserRepository(db)
        return await repo.update_user_profile(
            user_id,
            full_name,
            company,
            company_size,
            industry,
            use_case,
            notification_preferences,
        )

    @staticmethod
    async def update_user_subscription(
        db: AsyncSession,
        user_id: str,
        subscription_plan: Optional[SubscriptionPlan] = None,
        subscription_status: Optional[SubscriptionStatus] = None,
        usage_quota: Optional[int] = None,
        subscription_start_date: Optional[datetime] = None,
        subscription_end_date: Optional[datetime] = None,
        trial_end_date: Optional[datetime] = None,
        stripe_customer_id: Optional[str] = None,
        stripe_subscription_id: Optional[str] = None,
    ) -> bool:
        """Update user subscription information."""
        repo = UserRepository(db)
        return await repo.update_subscription(
            user_id,
            subscription_plan,
            subscription_status,
            usage_quota,
            subscription_start_date,
            subscription_end_date,
            trial_end_date,
            stripe_customer_id,
            stripe_subscription_id,
        )

    @staticmethod
    async def update_user_role(
        db: AsyncSession, user_id: str, new_role: UserRole
    ) -> bool:
        """Update user role (admin function)."""
        repo = UserRepository(db)
        return await repo.update_user_role(user_id, new_role)

    @staticmethod
    async def get_users_by_subscription_plan(
        db: AsyncSession, plan: SubscriptionPlan, limit: int = 100, offset: int = 0
    ) -> List[User]:
        """Get users by subscription plan (admin function)."""
        repo = UserRepository(db)
        return await repo.get_users_by_subscription_plan(plan, limit, offset)

    @staticmethod
    async def get_all_users(
        db: AsyncSession, offset: int = 0, limit: int = 100, active_only: bool = True
    ) -> List[User]:
        """Get all users with pagination (admin function)."""
        repo = UserRepository(db)
        return await repo.get_all_users(offset, limit, active_only)

    @staticmethod
    async def get_user_count(db: AsyncSession) -> int:
        """Get total number of users (admin function)."""
        repo = UserRepository(db)
        return await repo.get_user_count()

    @staticmethod
    async def get_user_by_stripe_customer_id(
        db: AsyncSession, stripe_customer_id: str
    ) -> Optional[User]:
        """Get user by Stripe customer ID."""
        repo = UserRepository(db)
        return await repo.get_user_by_stripe_customer_id(stripe_customer_id)

    @staticmethod
    async def get_user_by_stripe_subscription_id(
        db: AsyncSession, stripe_subscription_id: str
    ) -> Optional[User]:
        """Get user by Stripe subscription ID."""
        repo = UserRepository(db)
        return await repo.get_user_by_stripe_subscription_id(stripe_subscription_id)

    @staticmethod
    async def increment_usage_count(
        db: AsyncSession, user_id: str, increment_by: int = 1
    ) -> bool:
        """Atomically increment user's usage count."""
        repo = UserRepository(db)
        return await repo.increment_usage_count(user_id, increment_by)

    @staticmethod
    async def update_usage_count(
        db: AsyncSession, user_id: str, usage_value: int
    ) -> bool:
        """Update user's usage count to a specific value."""
        repo = UserRepository(db)
        return await repo.update_usage_count(user_id, usage_value)

    @staticmethod
    async def soft_delete_user(db: AsyncSession, user_id: str) -> bool:
        """Soft delete user account (deactivate)."""
        repo = UserRepository(db)
        return await repo.soft_delete_user(user_id)

    @staticmethod
    async def hard_delete_user(db: AsyncSession, user_id: str) -> bool:
        """Permanently delete user and all associated data."""
        repo = UserRepository(db)
        return await repo.hard_delete_user(user_id)

    @staticmethod
    async def get_users_pending_deletion(
        db: AsyncSession, days_ago: int = 30
    ) -> List[User]:
        """Get users who requested deletion more than X days ago."""
        repo = UserRepository(db)
        return await repo.get_users_pending_deletion(days_ago)


class APIKeyOperations:
    """Facade for API key operations."""

    @staticmethod
    async def create_api_key(
        db: AsyncSession,
        user_id: str,
        name: str,
        key_hash: str,
        key_prefix: str,
        salt: str,
        permissions: List[str],
        expires_at: Optional[datetime] = None,
    ) -> APIKey:
        """Create a new API key."""
        repo = APIKeyRepository(db)
        return await repo.create_api_key(
            user_id, name, key_hash, key_prefix, salt, permissions, expires_at
        )

    @staticmethod
    async def get_api_key_by_id(db: AsyncSession, key_id: str) -> Optional[APIKey]:
        """Get API key by ID."""
        repo = APIKeyRepository(db)
        return await repo.get_api_key_by_id(key_id)

    @staticmethod
    async def get_user_api_keys(
        db: AsyncSession, user_id: str, active_only: bool = True
    ) -> List[APIKey]:
        """Get all API keys for a user."""
        repo = APIKeyRepository(db)
        return await repo.get_user_api_keys(user_id, active_only)

    @staticmethod
    async def deactivate_api_key(db: AsyncSession, key_id: str, user_id: str) -> bool:
        """Deactivate an API key."""
        repo = APIKeyRepository(db)
        return await repo.deactivate_api_key(key_id, user_id)

    @staticmethod
    async def deactivate_all_user_keys(db: AsyncSession, user_id: str) -> int:
        """Deactivate all API keys for a user."""
        repo = APIKeyRepository(db)
        return await repo.deactivate_all_user_keys(user_id)

    @staticmethod
    async def update_last_used(db: AsyncSession, key_id: str) -> None:
        """Update API key's last used timestamp."""
        repo = APIKeyRepository(db)
        await repo.update_last_used(key_id)


class TokenOperations:
    """Facade for token blacklist operations."""

    @staticmethod
    async def blacklist_token(
        db: AsyncSession,
        token_id: str,
        user_id: str,
        token_type: str,
        expires_at: datetime,
    ) -> TokenBlacklist:
        """Add token to blacklist."""
        repo = TokenRepository(db)
        return await repo.blacklist_token(token_id, user_id, token_type, expires_at)

    @staticmethod
    async def is_token_blacklisted(db: AsyncSession, token_id: str) -> bool:
        """Check if token is blacklisted."""
        repo = TokenRepository(db)
        return await repo.is_token_blacklisted(token_id)

    @staticmethod
    async def cleanup_expired_tokens(db: AsyncSession) -> int:
        """Remove expired tokens from blacklist."""
        repo = TokenRepository(db)
        return await repo.cleanup_expired_tokens()


class UserActivityOperations:
    """Facade for activity tracking operations."""

    @staticmethod
    async def record_activity(
        db: AsyncSession,
        user_id: str,
        activity_type: str,
        activity_data: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> UserActivity:
        """Record a user activity event."""
        repo = ActivityRepository(db)
        return await repo.record_activity(
            user_id, activity_type, activity_data, ip_address, user_agent
        )

    @staticmethod
    async def get_user_activities(
        db: AsyncSession,
        user_id: str,
        activity_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[UserActivity]:
        """Get user activities with optional filters."""
        repo = ActivityRepository(db)
        return await repo.get_user_activities(
            user_id, activity_type, start_date, end_date, limit
        )

    @staticmethod
    async def get_recent_activities(
        db: AsyncSession, limit: int = 100
    ) -> List[UserActivity]:
        """Get recent activities across all users (admin function)."""
        repo = ActivityRepository(db)
        return await repo.get_recent_activities(limit)


class SystemMetricOperations:
    """Facade for system metric operations."""

    @staticmethod
    async def record_metric(
        db: AsyncSession,
        metric_name: str,
        metric_type: str,
        metric_value: Dict[str, Any],
        labels: Optional[Dict[str, Any]] = None,
    ) -> SystemMetric:
        """Record a system metric."""
        repo = SystemRepository(db)
        return await repo.record_metric(metric_name, metric_type, metric_value, labels)

    @staticmethod
    async def get_metrics(
        db: AsyncSession,
        metric_name: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[SystemMetric]:
        """Get system metrics with optional filters."""
        repo = SystemRepository(db)
        return await repo.get_metrics(metric_name, start_date, end_date, limit)

    @staticmethod
    async def get_metric_summary(db: AsyncSession, hours: int = 24) -> Dict[str, Any]:
        """Get metric summary for the last N hours (admin dashboard)."""
        repo = SystemRepository(db)
        return await repo.get_metric_summary(hours)


class InvoiceOperations:
    """Facade for invoice operations."""

    @staticmethod
    async def create_invoice(
        db: AsyncSession,
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
        repo = BillingRepository(db)
        return await repo.create_invoice(
            invoice_id,
            user_id,
            stripe_invoice_id,
            stripe_customer_id,
            amount_due,
            currency,
            status,
            billing_period_start,
            billing_period_end,
            amount_paid,
            description,
            invoice_url,
            due_date,
        )

    @staticmethod
    async def get_invoice_by_id(db: AsyncSession, invoice_id: str) -> Optional[Invoice]:
        """Get invoice by ID."""
        repo = BillingRepository(db)
        return await repo.get_invoice_by_id(invoice_id)

    @staticmethod
    async def get_invoice_by_stripe_id(
        db: AsyncSession, stripe_invoice_id: str
    ) -> Optional[Invoice]:
        """Get invoice by Stripe invoice ID."""
        repo = BillingRepository(db)
        return await repo.get_invoice_by_stripe_id(stripe_invoice_id)

    @staticmethod
    async def get_user_invoices(
        db: AsyncSession, user_id: str, limit: int = 10, offset: int = 0
    ) -> List[Invoice]:
        """Get invoices for a user."""
        repo = BillingRepository(db)
        return await repo.get_user_invoices(user_id, limit, offset)

    @staticmethod
    async def update_invoice_status(
        db: AsyncSession,
        invoice_id: str,
        status: str,
        amount_paid: Optional[int] = None,
        paid_at: Optional[datetime] = None,
    ) -> bool:
        """Update invoice status and payment details."""
        repo = BillingRepository(db)
        return await repo.update_invoice_status(
            invoice_id, status, amount_paid, paid_at
        )

    @staticmethod
    async def get_invoices_by_status(
        db: AsyncSession, status: str, limit: int = 50
    ) -> List[Invoice]:
        """Get invoices by status."""
        repo = BillingRepository(db)
        return await repo.get_invoices_by_status(status, limit)

    @staticmethod
    async def get_recent_invoices(db: AsyncSession, limit: int = 50) -> List[Invoice]:
        """Get recent invoices regardless of status."""
        repo = BillingRepository(db)
        return await repo.get_recent_invoices(limit)


class PaymentOperations:
    """Facade for payment operations."""

    @staticmethod
    async def create_payment(
        db: AsyncSession,
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
        repo = BillingRepository(db)
        return await repo.create_payment(
            payment_id,
            user_id,
            stripe_payment_intent_id,
            stripe_customer_id,
            amount,
            currency,
            status,
            payment_method,
            invoice_id,
            payment_method_details,
            failure_code,
            failure_message,
            processed_at,
        )

    @staticmethod
    async def get_payment_by_id(db: AsyncSession, payment_id: str) -> Optional[Payment]:
        """Get payment by ID."""
        repo = BillingRepository(db)
        return await repo.get_payment_by_id(payment_id)

    @staticmethod
    async def get_payment_by_stripe_id(
        db: AsyncSession, stripe_payment_intent_id: str
    ) -> Optional[Payment]:
        """Get payment by Stripe payment intent ID."""
        repo = BillingRepository(db)
        return await repo.get_payment_by_stripe_id(stripe_payment_intent_id)

    @staticmethod
    async def get_user_payments(
        db: AsyncSession, user_id: str, limit: int = 10, offset: int = 0
    ) -> List[Payment]:
        """Get payments for a user."""
        repo = BillingRepository(db)
        return await repo.get_user_payments(user_id, limit, offset)

    @staticmethod
    async def update_payment_status(
        db: AsyncSession,
        payment_id: str,
        status: str,
        processed_at: Optional[datetime] = None,
        failure_code: Optional[str] = None,
        failure_message: Optional[str] = None,
    ) -> bool:
        """Update payment status and processing details."""
        repo = BillingRepository(db)
        return await repo.update_payment_status(
            payment_id, status, processed_at, failure_code, failure_message
        )

    @staticmethod
    async def get_payments_by_date_range(
        db: AsyncSession, start_date: datetime, end_date: datetime
    ) -> List[Payment]:
        """Get payments within a date range."""
        repo = BillingRepository(db)
        return await repo.get_payments_by_date_range(start_date, end_date)


class BillingUsageOperations:
    """Facade for billing usage operations."""

    @staticmethod
    async def create_usage_record(
        db: AsyncSession,
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
        repo = BillingRepository(db)
        return await repo.create_usage_record(
            record_id,
            user_id,
            usage_type,
            usage_count,
            billing_period,
            unit_cost,
            total_cost,
            metadata,
        )

    @staticmethod
    async def get_user_usage_for_period(
        db: AsyncSession,
        user_id: str,
        billing_period: str,
        usage_type: Optional[str] = None,
    ) -> List[BillingUsageRecord]:
        """Get user usage records for a billing period."""
        repo = BillingRepository(db)
        return await repo.get_user_usage_for_period(user_id, billing_period, usage_type)

    @staticmethod
    async def get_usage_summary_for_period(
        db: AsyncSession, user_id: str, billing_period: str
    ) -> Dict[str, int]:
        """Get usage summary by type for a billing period."""
        repo = BillingRepository(db)
        return await repo.get_usage_summary_for_period(user_id, billing_period)

    @staticmethod
    async def mark_usage_reported_to_stripe(
        db: AsyncSession, record_id: str, stripe_usage_record_id: str
    ) -> bool:
        """Mark usage record as reported to Stripe."""
        repo = BillingRepository(db)
        return await repo.mark_usage_reported_to_stripe(
            record_id, stripe_usage_record_id
        )

    @staticmethod
    async def get_unreported_usage(
        db: AsyncSession, limit: int = 100
    ) -> List[BillingUsageRecord]:
        """Get usage records not yet reported to Stripe."""
        repo = BillingRepository(db)
        return await repo.get_unreported_usage(limit)


class UsageOperations:
    """Database operations for usage tracking."""

    @staticmethod
    async def record_usage(
        db: AsyncSession,
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
        """Record a usage event."""
        repo = UsageRepository(db)
        return await repo.record_usage(
            user_id,
            endpoint,
            method,
            repository_url,
            tokens_consumed,
            cost_incurred,
            response_time_ms,
            success,
            error_message,
        )

    @staticmethod
    async def get_user_usage(
        db: AsyncSession,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[UsageRecord]:
        """Get usage records for a user."""
        repo = UsageRepository(db)
        return await repo.get_user_usage(user_id, start_date, end_date, limit)


class WebhookEventOperations:
    """Facade for webhook event operations."""

    @staticmethod
    async def create_webhook_event(
        db: AsyncSession,
        event_id: str,
        stripe_event_id: str,
        event_type: str,
        event_data: Dict[str, Any],
        status: str = "pending",
    ) -> WebhookEvent:
        """Create a new webhook event record."""
        repo = WebhookRepository(db)
        return await repo.create_webhook_event(
            event_id, stripe_event_id, event_type, event_data, status
        )

    @staticmethod
    async def get_webhook_event(
        db: AsyncSession, event_id: str
    ) -> Optional[WebhookEvent]:
        """Get webhook event by ID."""
        repo = WebhookRepository(db)
        return await repo.get_webhook_event(event_id)

    @staticmethod
    async def mark_event_processed(
        db: AsyncSession, event_id: str, processing_result: str, success: bool = True
    ) -> bool:
        """Mark webhook event as processed."""
        repo = WebhookRepository(db)
        return await repo.mark_event_processed(event_id, processing_result, success)

    @staticmethod
    async def get_unprocessed_events(
        db: AsyncSession, limit: int = 50, max_attempts: int = 3
    ) -> List[WebhookEvent]:
        """Get unprocessed webhook events."""
        repo = WebhookRepository(db)
        return await repo.get_unprocessed_events(limit, max_attempts)

    @staticmethod
    async def mark_event_failed(
        db: AsyncSession, event_id: str, error_message: str
    ) -> bool:
        """Mark webhook event as failed."""
        repo = WebhookRepository(db)
        return await repo.mark_event_failed(event_id, error_message)

    @staticmethod
    async def cleanup_old_events(db: AsyncSession, days_old: int = 30) -> int:
        """Clean up old processed webhook events."""
        repo = WebhookRepository(db)
        return await repo.cleanup_old_events(days_old)

    @staticmethod
    async def get_failed_webhooks(
        db: AsyncSession, max_attempts: int = 5
    ) -> List[WebhookEvent]:
        """Get failed webhook events for retry."""
        repo = WebhookRepository(db)
        return await repo.get_failed_webhooks(max_attempts)

    @staticmethod
    async def update_webhook_status(
        db: AsyncSession,
        event_id: str,
        status: str,
        error: Optional[str] = None,
        processing_time: Optional[int] = None,
    ) -> bool:
        """Update webhook event status."""
        repo = WebhookRepository(db)
        return await repo.update_webhook_status(
            event_id, status, error, processing_time
        )

    @staticmethod
    async def delete_old_webhooks(db: AsyncSession, days: int = 30) -> int:
        """Delete old processed webhook events."""
        repo = WebhookRepository(db)
        return await repo.delete_old_webhooks(days)

    @staticmethod
    async def get_webhook_statistics(db: AsyncSession) -> Dict[str, Any]:
        """Get webhook processing statistics."""
        repo = WebhookRepository(db)
        return await repo.get_webhook_statistics()


class EmailVerificationOperations:
    """Facade for email verification operations."""

    @staticmethod
    async def create_verification_token(
        db: AsyncSession,
        user_id: str,
        token: str,
        expires_in_hours: int = 24,
    ) -> EmailVerificationToken:
        """Create a new email verification token."""
        repo = EmailVerificationRepository(db)
        return await repo.create_verification_token(user_id, token, expires_in_hours)

    @staticmethod
    async def get_valid_token(
        db: AsyncSession, token: str
    ) -> Optional[EmailVerificationToken]:
        """Get a valid (unused and not expired) verification token."""
        repo = EmailVerificationRepository(db)
        return await repo.get_valid_token(token)

    @staticmethod
    async def mark_token_used(db: AsyncSession, token: str) -> bool:
        """Mark a verification token as used."""
        repo = EmailVerificationRepository(db)
        return await repo.mark_token_used(token)

    @staticmethod
    async def verify_user_email(db: AsyncSession, user_id: str) -> bool:
        """Mark user's email as verified."""
        repo = EmailVerificationRepository(db)
        return await repo.verify_user_email(user_id)

    @staticmethod
    async def cleanup_expired_tokens(db: AsyncSession, days_old: int = 7) -> int:
        """Clean up expired tokens older than specified days."""
        repo = EmailVerificationRepository(db)
        return await repo.cleanup_expired_tokens(days_old)

    @staticmethod
    async def get_user_tokens(
        db: AsyncSession, user_id: str
    ) -> List[EmailVerificationToken]:
        """Get all verification tokens for a user."""
        repo = EmailVerificationRepository(db)
        return await repo.get_user_tokens(user_id)


class ContactOperations:
    """Facade for contact operations."""

    @staticmethod
    async def create_message(
        db: AsyncSession,
        name: str,
        email: str,
        subject: str,
        message: str,
        user_id: Optional[str] = None,
    ) -> ContactMessage:
        """Create a new contact message."""
        repo = ContactRepository(db)
        return await repo.create_message(name, email, subject, message, user_id)

    @staticmethod
    async def get_message_by_id(
        db: AsyncSession, message_id: str
    ) -> Optional[ContactMessage]:
        """Get contact message by ID."""
        repo = ContactRepository(db)
        return await repo.get_message_by_id(message_id)

    @staticmethod
    async def get_messages(
        db: AsyncSession,
        status: Optional[ContactStatus] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[List[ContactMessage], int]:
        """Get paginated list of contact messages."""
        repo = ContactRepository(db)
        return await repo.get_messages(status, limit, offset)

    @staticmethod
    async def get_messages_by_user_id(
        db: AsyncSession,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[List[ContactMessage], int]:
        """Get paginated list of contact messages for a specific user."""
        repo = ContactRepository(db)
        return await repo.get_messages_by_user_id(user_id, limit, offset)

    @staticmethod
    async def update_message_status(
        db: AsyncSession,
        message_id: str,
        status: ContactStatus,
    ) -> bool:
        """Update message status."""
        repo = ContactRepository(db)
        return await repo.update_message_status(message_id, status)

    @staticmethod
    async def add_admin_response(
        db: AsyncSession,
        message_id: str,
        admin_user_id: str,
        admin_response: str,
    ) -> bool:
        """Add admin response to a contact message."""
        repo = ContactRepository(db)
        return await repo.add_admin_response(message_id, admin_user_id, admin_response)

    @staticmethod
    async def get_unread_count(db: AsyncSession) -> int:
        """Get count of unread messages."""
        repo = ContactRepository(db)
        return await repo.get_unread_count()
