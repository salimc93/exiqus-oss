# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Database models for GitHub Analyzer.

This module defines SQLAlchemy models for users, authentication,
usage tracking, and other persistent data.
"""

import enum
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .connection import Base


class UserRole(enum.Enum):
    """User role enumeration."""

    USER = "user"
    ADMIN = "admin"
    ENTERPRISE = "enterprise"


class SubscriptionPlan(enum.Enum):
    """Subscription plan enumeration."""

    FREE = "FREE"
    BASIC = "BASIC"
    PROFESSIONAL = "PROFESSIONAL"
    ENTERPRISE = "ENTERPRISE"
    SCALE_PLUS = "SCALE_PLUS"


class SubscriptionStatus(enum.Enum):
    """Subscription status enumeration."""

    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    SUSPENDED = "suspended"
    TRIALING = "trialing"


class ContactStatus(enum.Enum):
    """Contact message status enumeration."""

    UNREAD = "unread"
    READ = "read"
    RESPONDED = "responded"


class AnalysisStatus(enum.Enum):
    """Analysis processing status enumeration."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class User(Base):
    """User account model."""

    __tablename__ = "users"

    # Primary key
    user_id: Mapped[str] = mapped_column(String(50), primary_key=True)

    # Authentication
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)

    # Profile information
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    company: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Account status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # User role and subscription information
    user_role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), default=UserRole.USER, nullable=False
    )
    subscription_plan: Mapped[SubscriptionPlan] = mapped_column(
        Enum(SubscriptionPlan), default=SubscriptionPlan.FREE, nullable=False
    )
    subscription_status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE, nullable=False
    )

    # Stripe subscription details
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )

    # Subscription dates
    subscription_start_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    subscription_end_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    trial_end_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Trial/Invite system fields
    is_trial: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    trial_plan: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # "basic", "professional", "enterprise", "custom"
    trial_analyses_limit: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # None = unlimited
    analyses_consumed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    invite_token: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, unique=True, index=True
    )
    invite_token_expires: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    has_completed_onboarding: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    trial_value: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # "$49/month", "$149/month", etc.

    # Company and preferences
    company_size: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    use_case: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notification_preferences: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON string

    # Privacy preferences (override tier defaults)
    privacy_preferences: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON string
    consent_version_accepted: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )
    consent_notice_dismissed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deletion_requested_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Usage tracking
    usage_quota: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Priority support fields
    is_priority_support: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    response_time_hours: Mapped[int] = mapped_column(
        Integer, default=48, nullable=False
    )

    # Custom limits for enterprise users
    custom_repo_size_limit_mb: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Custom repo size limit for enterprise users"
    )

    # Relationships
    api_keys: Mapped[List["APIKey"]] = relationship(
        "APIKey", back_populates="user", cascade="all, delete-orphan"
    )
    usage_records: Mapped[List["UsageRecord"]] = relationship(
        "UsageRecord", back_populates="user", cascade="all, delete-orphan"
    )
    password_reset_tokens: Mapped[List["PasswordResetToken"]] = relationship(
        "PasswordResetToken", back_populates="user", cascade="all, delete-orphan"
    )
    contact_messages: Mapped[List["ContactMessage"]] = relationship(
        "ContactMessage", foreign_keys="ContactMessage.user_id", back_populates="user"
    )
    verification_tokens: Mapped[List["EmailVerificationToken"]] = relationship(
        "EmailVerificationToken", back_populates="user", cascade="all, delete-orphan"
    )
    analysis_results: Mapped[List["AnalysisResult"]] = relationship(
        "AnalysisResult", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(user_id='{self.user_id}', email='{self.email}')>"


class APIKey(Base):
    """API key model for programmatic access."""

    __tablename__ = "api_keys"

    # Primary key
    key_id: Mapped[str] = mapped_column(String(50), primary_key=True)

    # Foreign key to user
    user_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("users.user_id"), nullable=False, index=True
    )

    # Key information
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    key_prefix: Mapped[str] = mapped_column(
        String(12), nullable=False, index=True, unique=True
    )  # Non-secret prefix for O(1) lookups
    key_hash: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # Store hashed key, not plain text
    salt: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # Store salt separately for better security
    permissions: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # JSON string of permissions list

    # Status and metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_used: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Quota tracking fields
    monthly_quota: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    monthly_usage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_quota_reset: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="api_keys")
    usage_records: Mapped[List["UsageRecord"]] = relationship(
        "UsageRecord", back_populates="api_key"
    )

    def __repr__(self) -> str:
        return f"<APIKey(key_id='{self.key_id}', name='{self.name}')>"


class UsageRecord(Base):
    """Usage tracking for API calls and analysis requests."""

    __tablename__ = "usage_records"

    # Primary key
    record_id: Mapped[str] = mapped_column(String(50), primary_key=True)

    # Foreign key to user
    user_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("users.user_id"), nullable=False, index=True
    )

    # Request details
    endpoint: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g., "/api/v1/analyze"
    method: Mapped[str] = mapped_column(String(10), nullable=False)  # e.g., "POST"
    repository_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Usage metrics
    tokens_consumed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_incurred: Mapped[str] = mapped_column(
        String(20), default="0.00", nullable=False
    )  # Decimal as string
    response_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)

    # Status
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # API tracking fields
    api_key_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("api_keys.key_id"), nullable=True, index=True
    )
    is_api_request: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="usage_records")
    api_key: Mapped[Optional["APIKey"]] = relationship("APIKey")

    def __repr__(self) -> str:
        return (
            f"<UsageRecord(record_id='{self.record_id}', endpoint='{self.endpoint}')>"
        )


class TokenBlacklist(Base):
    """Blacklisted JWT tokens for logout/revocation."""

    __tablename__ = "token_blacklist"

    # Primary key - use token's jti (JWT ID) if available, or token hash
    token_id: Mapped[str] = mapped_column(String(100), primary_key=True)

    # Token metadata
    user_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("users.user_id"), nullable=False, index=True
    )
    token_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "access" or "refresh"

    # Expiration - tokens can be removed from blacklist after expiry
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    # Blacklist timestamp
    blacklisted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<TokenBlacklist(token_id='{self.token_id}', user_id='{self.user_id}')>"


class SystemMetric(Base):
    """System-wide metrics and analytics for admin dashboard."""

    __tablename__ = "system_metrics"

    # Primary key
    metric_id: Mapped[str] = mapped_column(String(50), primary_key=True)

    # Metric details
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    metric_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "counter", "gauge", "histogram"
    metric_value: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # JSON string for complex values

    # Dimensions/labels
    labels: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string

    # Timestamps
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return (
            f"<SystemMetric(metric_name='{self.metric_name}', "
            f"timestamp='{self.timestamp}')>"
        )


class UserActivity(Base):
    """User activity tracking for analytics and admin insights."""

    __tablename__ = "user_activities"

    # Primary key
    activity_id: Mapped[str] = mapped_column(String(50), primary_key=True)

    # Foreign key to user
    user_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("users.user_id"), nullable=False, index=True
    )

    # Activity details
    activity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    activity_data: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON string

    # Context
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45), nullable=True
    )  # IPv6 support
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Relationship
    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<UserActivity(activity_type='{self.activity_type}', "
            f"user_id='{self.user_id}')>"
        )


class Invoice(Base):
    """Billing invoice records for tracking payments and billing history."""

    __tablename__ = "invoices"

    # Primary key
    invoice_id: Mapped[str] = mapped_column(String(50), primary_key=True)

    # Foreign key to user
    user_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("users.user_id"), nullable=False, index=True
    )

    # Stripe integration
    stripe_invoice_id: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    stripe_customer_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # Invoice details
    amount_due: Mapped[int] = mapped_column(Integer, nullable=False)  # Amount in cents
    amount_paid: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="usd", nullable=False)

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # draft, open, paid, void, uncollectible

    # Billing period
    billing_period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    billing_period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    # Invoice metadata
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    invoice_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    invoice_pdf: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    due_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    # Relationship
    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<Invoice(invoice_id='{self.invoice_id}', "
            f"amount_due={self.amount_due}, status='{self.status}')>"
        )


class Payment(Base):
    """Payment records for tracking successful and failed payment attempts."""

    __tablename__ = "payments"

    # Primary key
    payment_id: Mapped[str] = mapped_column(String(50), primary_key=True)

    # Foreign key to user
    user_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("users.user_id"), nullable=False, index=True
    )

    # Optional foreign key to invoice
    invoice_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("invoices.invoice_id"), nullable=True, index=True
    )

    # Stripe integration
    stripe_payment_intent_id: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    stripe_customer_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # Payment details
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # Amount in cents
    currency: Mapped[str] = mapped_column(String(3), default="usd", nullable=False)

    # Status and method
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # succeeded, failed, canceled, processing
    payment_method: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # card, bank_transfer, etc.
    payment_method_details: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON string with details

    # Failure information
    failure_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    failure_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User")
    invoice: Mapped[Optional["Invoice"]] = relationship("Invoice")

    def __repr__(self) -> str:
        return (
            f"<Payment(payment_id='{self.payment_id}', "
            f"amount={self.amount}, status='{self.status}')>"
        )


class BillingUsageRecord(Base):
    """Usage records for metered billing and quota tracking."""

    __tablename__ = "billing_usage_records"

    # Primary key
    record_id: Mapped[str] = mapped_column(String(50), primary_key=True)

    # Foreign key to user
    user_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("users.user_id"), nullable=False, index=True
    )

    # Usage details
    usage_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # api_call, analysis, batch_analysis, etc.
    usage_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Billing period tracking
    billing_period: Mapped[str] = mapped_column(
        String(10), nullable=False, index=True
    )  # YYYY-MM format

    # Cost tracking
    unit_cost: Mapped[str] = mapped_column(
        String(20), default="0.00", nullable=False
    )  # Decimal as string
    total_cost: Mapped[str] = mapped_column(
        String(20), default="0.00", nullable=False
    )  # Decimal as string

    # Request metadata
    request_metadata: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON string for additional request data

    # Stripe integration (for usage-based billing)
    stripe_usage_record_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )
    reported_to_stripe: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    reported_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    # Relationship
    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<BillingUsageRecord(usage_type='{self.usage_type}', "
            f"count={self.usage_count}, period='{self.billing_period}')>"
        )


class WebhookEvent(Base):
    """Webhook event tracking for idempotency and audit trail."""

    __tablename__ = "webhook_events"

    # Primary key - use Stripe event ID for idempotency
    event_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    stripe_event_id: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )

    # Event details
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_data: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string

    # Processing status
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False, index=True
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Processing results
    processing_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    def __repr__(self) -> str:
        return (
            f"<WebhookEvent(event_id='{self.event_id}', "
            f"type='{self.event_type}', status='{self.status}')>"
        )


class ContactMessage(Base):
    """Contact form messages from users."""

    __tablename__ = "contact_messages"

    # Primary key
    message_id: Mapped[str] = mapped_column(String(50), primary_key=True)

    # User association (optional - for logged-in users)
    user_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("users.user_id"), nullable=True, index=True
    )

    # Contact information
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Status tracking
    status: Mapped[ContactStatus] = mapped_column(
        Enum(ContactStatus), default=ContactStatus.UNREAD, nullable=False, index=True
    )

    # Priority support fields
    is_priority: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    priority_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    target_response_hours: Mapped[int] = mapped_column(
        Integer, default=48, nullable=False
    )
    sla_status: Mapped[str] = mapped_column(String(20), default="green", nullable=False)

    # Admin response
    admin_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    responded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    responded_by: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("users.user_id"), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[user_id], back_populates="contact_messages"
    )
    responder: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[responded_by]
    )

    def __repr__(self) -> str:
        return (
            f"<ContactMessage(message_id='{self.message_id}', "
            f"subject='{self.subject}', status='{self.status.value}')>"
        )


class AuditLog(Base):
    """Audit log for tracking administrative actions and important events."""

    __tablename__ = "audit_logs"

    # Primary key
    log_id: Mapped[str] = mapped_column(String(50), primary_key=True)

    # Action details
    action: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )  # "trial_granted", "trial_activated", "trial_extended", etc.

    # User references
    admin_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("users.user_id"), nullable=True, index=True
    )
    target_user_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("users.user_id"), nullable=True, index=True
    )
    target_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Additional metadata
    action_metadata: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON string with action-specific details

    # Request context
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Relationships
    admin: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[admin_id], primaryjoin="AuditLog.admin_id == User.user_id"
    )
    target_user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[target_user_id],
        primaryjoin="AuditLog.target_user_id == User.user_id",
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog(action='{self.action}', "
            f"admin_id='{self.admin_id}', created_at='{self.created_at}')>"
        )


class APIUsageOverage(Base):
    """API usage overage records for billing."""

    __tablename__ = "api_usage_overages"

    # Primary key
    overage_id: Mapped[str] = mapped_column(String(50), primary_key=True)

    # Foreign keys
    user_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("users.user_id"), nullable=False, index=True
    )
    api_key_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("api_keys.key_id"), nullable=False, index=True
    )

    # Billing details
    billing_month: Mapped[datetime] = mapped_column(
        Date, nullable=False, index=True
    )  # Using datetime for Date type
    overage_count: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_charged: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # Decimal as string for money

    # Payment tracking
    stripe_invoice_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    payment_status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False, index=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User")
    api_key: Mapped["APIKey"] = relationship("APIKey")

    def __repr__(self) -> str:
        return (
            f"<APIUsageOverage(overage_id='{self.overage_id}', "
            f"api_key_id='{self.api_key_id}', "
            f"billing_month='{self.billing_month}', "
            f"amount_charged={self.amount_charged})>"
        )


class EmailVerificationToken(Base):
    """
    Email verification token model.

    Stores tokens for email verification with expiration.
    """

    __tablename__ = "email_verification_tokens"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Token info
    user_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("users.user_id"), nullable=False, index=True
    )
    token: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="verification_tokens")

    def is_expired(self) -> bool:
        """Check if token has expired."""
        return datetime.now(timezone.utc) > self.expires_at

    def is_valid(self) -> bool:
        """Check if token is valid (not used and not expired)."""
        return self.used_at is None and not self.is_expired()


class PasswordResetToken(Base):
    """Password reset token model for secure password recovery."""

    __tablename__ = "password_reset_tokens"

    # Primary key
    token_id: Mapped[str] = mapped_column(String(50), primary_key=True)

    # Foreign key to user
    user_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("users.user_id"), nullable=False, index=True
    )

    # Token information
    token_hash: Mapped[str] = mapped_column(
        Text, nullable=False, unique=True
    )  # Store hashed token, not plain text

    # Expiration and usage
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Request metadata
    request_ip: Mapped[Optional[str]] = mapped_column(
        String(45), nullable=True
    )  # IPv6 support
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="password_reset_tokens")

    @property
    def is_expired(self) -> bool:
        """Check if the token has expired."""
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_used(self) -> bool:
        """Check if the token has been used."""
        return self.used_at is not None

    @property
    def is_valid(self) -> bool:
        """Check if the token is valid (not expired and not used)."""
        return not self.is_expired and not self.is_used

    def __repr__(self) -> str:
        return (
            f"<PasswordResetToken(token_id='{self.token_id}', "
            f"user_id='{self.user_id}', expires_at='{self.expires_at}')>"
        )


class AnalysisResult(Base):
    """Analysis result storage model."""

    __tablename__ = "analysis_results"

    # Primary key - UUID
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Processing status
    status: Mapped[AnalysisStatus] = mapped_column(
        Enum(AnalysisStatus), default=AnalysisStatus.PENDING, nullable=False, index=True
    )

    # Foreign key to user
    user_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("users.user_id"), nullable=False, index=True
    )

    # Repository information
    repository_url: Mapped[str] = mapped_column(Text, nullable=False)
    repository_name: Mapped[str] = mapped_column(String(255), nullable=False)
    context: Mapped[str] = mapped_column(String(50), nullable=False)

    # Candidate linking (for context lock + Candidate Hub integration)
    # Required for paid tiers, optional for free tier
    # Ties repo analysis to specific candidate for consistent assessment
    github_username: Mapped[Optional[str]] = mapped_column(
        String(39), nullable=True, index=True
    )
    role: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Batch tracking
    batch_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, index=True
    )

    # Core results - OBSOLETE FIELDS REMOVED (Great Purge)
    # overall_score, confidence_score, recommendation removed
    # No longer used in evidence-based system

    # Full analysis data (JSON/JSONB)
    full_analysis: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string

    # Metadata
    analysis_version: Mapped[str] = mapped_column(
        String(20), default="1.0.0", nullable=False
    )
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    api_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Evidence-based analysis fields
    evidence_patterns: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON string
    screening_insights: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON string
    confidence_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    technical_patterns: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON string
    collaboration_patterns: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON string
    quality_indicators: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON string
    temporal_insights: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON string
    skill_evolution: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON string
    behavioral_analysis: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON string
    security_practices: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON string
    context_alignment: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON string
    verification_gaps: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON array string
    analysis_method: Mapped[str] = mapped_column(
        String(20), default="legacy", nullable=False
    )
    evidence_version: Mapped[str] = mapped_column(
        String(20), default="1.0.0", nullable=False
    )

    # Privacy & consent fields
    data_consent: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON string
    data_anonymized_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    consent_updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    training_eligible: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Privacy & soft delete
    allow_training: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="analysis_results")

    @property
    def is_deleted(self) -> bool:
        """Check if the analysis is soft deleted."""
        return self.deleted_at is not None

    def __repr__(self) -> str:
        return (
            f"<AnalysisResult(id='{self.id}', "
            f"repository_name='{self.repository_name}', "
            f"analysis_method='{self.analysis_method}')>"
        )


class BatchAnalysis(Base):
    """Batch analysis history for Scale and Scale+ tiers."""

    __tablename__ = "batch_analyses"

    # Primary key
    batch_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Processing status
    status: Mapped[AnalysisStatus] = mapped_column(
        Enum(AnalysisStatus), default=AnalysisStatus.PENDING, nullable=False, index=True
    )

    # Foreign key to user
    user_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("users.user_id"), nullable=False, index=True
    )

    # Batch details
    repository_count: Mapped[int] = mapped_column(Integer, nullable=False)
    successful_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Processing details
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    concurrency_mode: Mapped[str] = mapped_column(
        String(20), default="sequential", nullable=False
    )  # sequential, balanced, fast

    # Metadata
    contexts: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array
    error_messages: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<BatchAnalysis(batch_id='{self.batch_id}', "
            f"user_id='{self.user_id}', "
            f"repository_count={self.repository_count}, "
            f"status='{self.status}')>"
        )


class PRAnalysisRecord(Base):
    """Record of PR analysis for usage tracking."""

    __tablename__ = "pr_analysis_records"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to user
    user_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("users.user_id"), nullable=False, index=True
    )

    # Foreign key to analysis result
    analysis_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("pr_analysis_results.id"), nullable=True, index=True
    )

    # PR analysis details
    github_username: Mapped[str] = mapped_column(String(39), nullable=False)
    pr_count: Mapped[int] = mapped_column(Integer, nullable=False)
    api_calls_used: Mapped[int] = mapped_column(Integer, nullable=False)
    context: Mapped[str] = mapped_column(String(50), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # junior, mid, senior

    # Status tracking
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<PRAnalysisRecord(id={self.id}, "
            f"user_id='{self.user_id}', "
            f"github_username='{self.github_username}', "
            f"pr_count={self.pr_count})>"
        )


class PRAnalysisResult(Base):
    """PR analysis result storage model - anonymized with only GitHub username."""

    __tablename__ = "pr_analysis_results"

    # Primary key - UUID
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Processing status
    status: Mapped[AnalysisStatus] = mapped_column(
        Enum(AnalysisStatus), default=AnalysisStatus.PENDING, nullable=False, index=True
    )

    # Real-time progress tracking (for async background processing)
    progress_stage: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # fetching, analyzing, generating, finalizing
    progress_percent: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # 0-100
    progress_message: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )  # Human-readable progress message

    # No user_id - keep it anonymous, just GitHub username for training data
    # This allows multiple analyses of same username by different users
    github_username: Mapped[str] = mapped_column(String(39), nullable=False, index=True)
    context: Mapped[str] = mapped_column(String(50), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # junior, mid, senior - affects interview questions
    total_prs_analyzed: Mapped[int] = mapped_column(Integer, nullable=False)

    # Full analysis data (JSON/JSONB) - Unified result first, then separated
    full_analysis: Mapped[str] = mapped_column(Text, nullable=False)  # Complete JSON
    summary_report: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    detailed_report: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_insights: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quality_signals: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Data quality indicator
    data_quality: Mapped[str] = mapped_column(String(20), nullable=False)

    # API usage tracking
    api_calls_used: Mapped[int] = mapped_column(Integer, nullable=False)
    fetch_time_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    total_time_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    from_cache: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # No user relationship - keep it anonymous

    def __repr__(self) -> str:
        return (
            f"<PRAnalysisResult(id={self.id}, "
            f"github_username='{self.github_username}', "
            f"context='{self.context}', "
            f"total_prs={self.total_prs_analyzed})>"
        )


class PRAnalysisCache(Base):
    """
    Cache table for PR analyses with deduplication.

    Separate from PRAnalysisResult to enable:
    - Clean historical storage (PRAnalysisResult) never deleted
    - Aggressive cache clearing without losing training data
    - Database-level deduplication via UNIQUE constraint
    - Race condition protection

    Cache key: (github_username, context, role)
    """

    __tablename__ = "pr_analysis_cache"

    __table_args__ = (
        UniqueConstraint(
            "github_username",
            "context",
            "role",
            name="uq_pr_cache_context",
        ),
    )

    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Foreign key to result storage
    result_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pr_analysis_results.id"), nullable=False, index=True
    )

    # Cache key components
    github_username: Mapped[str] = mapped_column(String(39), nullable=False, index=True)
    context: Mapped[str] = mapped_column(String(50), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)

    # Cache expiry (30-day TTL)
    cache_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationship to result
    result: Mapped["PRAnalysisResult"] = relationship("PRAnalysisResult")

    @property
    def is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        return datetime.now(timezone.utc) < self.cache_expires_at

    def __repr__(self) -> str:
        return (
            f"<PRAnalysisCache(id='{self.id}', "
            f"github_username='{self.github_username}', "
            f"context='{self.context}', role='{self.role}')>"
        )


class CandidateContext(Base):
    """
    Locked role + organization context for candidate evaluations.

    Ensures consistent evaluation context across all analysis types
    (Portfolio, PR, Single Repo) for a given candidate. This enables
    meaningful blending of intelligence from multiple sources.

    Note: Context is locked per (hiring_manager + candidate), allowing
    different hiring managers to evaluate the same candidate with
    different role/org contexts. This supports scenarios where:
    - Same candidate applies for different roles (junior vs senior)
    - Same candidate applies to different org types (startup vs enterprise)
    """

    __tablename__ = "candidate_contexts"

    # Composite primary key: (locked_by_user_id, username)
    # This allows each hiring manager to have their own context lock per candidate
    locked_by_user_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("users.user_id"), primary_key=True, nullable=False
    )
    username: Mapped[str] = mapped_column(String(39), primary_key=True, nullable=False)

    # Locked context - must match across all analyses for this candidate
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # junior, mid, senior
    organization_context: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # startup, enterprise

    # Metadata
    locked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    locked_by: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<CandidateContext(user_id='{self.locked_by_user_id}', "
            f"username='{self.username}', "
            f"role='{self.role}', "
            f"organization_context='{self.organization_context}')>"
        )
