# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Authentication models for API security.

This module defines Pydantic models for authentication requests,
responses, and JWT token handling.
"""

from datetime import datetime
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRole(str, Enum):
    """User role enumeration for API models."""

    USER = "user"
    ADMIN = "admin"
    ENTERPRISE = "enterprise"


class SubscriptionPlan(str, Enum):
    """Subscription plan enumeration for API models."""

    FREE = "free"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    SCALE_PLUS = "scale_plus"


class SubscriptionStatus(str, Enum):
    """Subscription status enumeration for API models."""

    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    SUSPENDED = "suspended"
    TRIALING = "trialing"


class UserRegistration(BaseModel):
    """User registration request model."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(
        ..., min_length=8, description="Password (minimum 8 characters)"
    )
    full_name: str = Field(..., min_length=1, description="User's full name")
    company: Optional[str] = Field(None, description="Company name")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@company.com",
                "password": "securepassword123",
                "full_name": "John Doe",
                "company": "Tech Corp",
            }
        }
    )


class UserLogin(BaseModel):
    """User login request model."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"email": "user@company.com", "password": "securepassword123"}
        }
    )


class TokenResponse(BaseModel):
    """JWT token response model."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    refresh_token: Optional[str] = Field(None, description="Refresh token")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600,
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            }
        }
    )


class RefreshTokenRequest(BaseModel):
    """Refresh token request model."""

    refresh_token: str = Field(..., description="Valid refresh token")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}
        }
    )


class UserProfile(BaseModel):
    """User profile response model."""

    user_id: str = Field(..., description="Unique user identifier")
    email: str = Field(..., description="User email address")
    full_name: str = Field(..., description="User's full name")
    company: Optional[str] = Field(None, description="Company name")
    is_active: bool = Field(..., description="Whether user account is active")
    is_verified: bool = Field(..., description="Whether email is verified")
    created_at: datetime = Field(..., description="Account creation timestamp")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    usage_quota: int = Field(..., description="Monthly analysis quota")
    usage_consumed: int = Field(..., description="Analyses used this month")

    # Subscription information
    user_role: UserRole = Field(..., description="User role")
    subscription_plan: str = Field(
        ...,
        description="Current subscription plan (free, starter, growth, scale, scale_plus)",
    )
    subscription_status: SubscriptionStatus = Field(
        ..., description="Subscription status"
    )
    subscription_start_date: Optional[datetime] = Field(
        None, description="Subscription start date"
    )
    subscription_end_date: Optional[datetime] = Field(
        None, description="Subscription end date"
    )
    trial_end_date: Optional[datetime] = Field(None, description="Trial end date")

    # Extended profile information
    company_size: Optional[str] = Field(None, description="Company size")
    industry: Optional[str] = Field(None, description="Industry")
    use_case: Optional[str] = Field(None, description="Primary use case")

    # Privacy preferences
    consent_settings: Optional[dict[str, Any]] = Field(
        None, description="User consent settings"
    )
    consent_version: Optional[str] = Field(None, description="Accepted consent version")
    show_consent_notice: Optional[bool] = Field(
        None, description="Whether to show consent notice"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "usr_1234567890abcde",
                "email": "user@company.com",
                "full_name": "John Doe",
                "company": "Tech Corp",
                "is_active": True,
                "is_verified": True,
                "created_at": "2024-01-01T12:00:00Z",
                "last_login": "2024-01-15T10:30:00Z",
                "usage_quota": 500,
                "usage_consumed": 125,
                "user_role": "user",
                "subscription_plan": "professional",
                "subscription_status": "active",
                "subscription_start_date": "2024-01-01T00:00:00Z",
                "subscription_end_date": "2024-02-01T00:00:00Z",
                "trial_end_date": None,
                "company_size": "50-200",
                "industry": "Technology",
                "use_case": "Technical recruitment and candidate assessment",
            }
        }
    )


class APIKeyCreate(BaseModel):
    """API key creation request model."""

    name: str = Field(..., min_length=1, description="Descriptive name for the API key")
    permissions: List[str] = Field(
        default=["analyze"], description="List of permissions for this key"
    )
    expires_in_days: Optional[int] = Field(
        None, ge=1, le=365, description="Key expiration in days (max 365)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Production Analysis Key",
                "permissions": ["analyze", "batch"],
                "expires_in_days": 90,
            }
        }
    )


class APIKeyResponse(BaseModel):
    """API key response model."""

    key_id: str = Field(..., description="Unique key identifier")
    name: str = Field(..., description="Key name")
    key: str = Field(..., description="The actual API key (shown only once)")
    permissions: List[str] = Field(..., description="Key permissions")
    created_at: datetime = Field(..., description="Key creation timestamp")
    expires_at: Optional[datetime] = Field(None, description="Key expiration timestamp")
    is_active: bool = Field(..., description="Whether key is active")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "key_id": "key_1234567890abcde",
                "name": "Production Analysis Key",
                "key": "sk_live_1234567890abcdef...",
                "permissions": ["analyze", "batch"],
                "created_at": "2024-01-01T12:00:00Z",
                "expires_at": "2024-04-01T12:00:00Z",
                "is_active": True,
            }
        }
    )


class APIKeyInfo(BaseModel):
    """API key information model (without exposing the key)."""

    key_id: str = Field(..., description="Unique key identifier")
    name: str = Field(..., description="Key name")
    permissions: List[str] = Field(..., description="Key permissions")
    created_at: datetime = Field(..., description="Key creation timestamp")
    expires_at: Optional[datetime] = Field(None, description="Key expiration timestamp")
    is_active: bool = Field(..., description="Whether key is active")
    last_used: Optional[datetime] = Field(None, description="Last usage timestamp")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "key_id": "key_1234567890abcde",
                "name": "Production Analysis Key",
                "permissions": ["analyze", "batch"],
                "created_at": "2024-01-01T12:00:00Z",
                "expires_at": "2024-04-01T12:00:00Z",
                "is_active": True,
                "last_used": "2024-01-15T10:30:00Z",
            }
        }
    )


class PasswordChange(BaseModel):
    """Password change request model."""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(
        ..., min_length=8, description="New password (minimum 8 characters)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "current_password": "oldpassword123",
                "new_password": "newsecurepassword456",
            }
        }
    )


class UserProfileUpdate(BaseModel):
    """User profile update request model."""

    full_name: Optional[str] = Field(None, min_length=1, description="User's full name")
    company: Optional[str] = Field(None, description="Company name")
    company_size: Optional[str] = Field(None, description="Company size")
    industry: Optional[str] = Field(None, description="Industry")
    use_case: Optional[str] = Field(None, description="Primary use case")
    notification_preferences: Optional[dict[str, Any]] = Field(
        None, description="Notification preferences"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "full_name": "John Doe",
                "company": "Tech Corp Inc.",
                "company_size": "200-500",
                "industry": "Software Development",
                "use_case": "Automated candidate screening for technical roles",
                "notification_preferences": {
                    "email_reports": True,
                    "usage_alerts": True,
                    "product_updates": False,
                },
            }
        }
    )


class AdminUserUpdate(BaseModel):
    """Admin user update request model."""

    user_role: Optional[UserRole] = Field(None, description="User role")
    subscription_plan: Optional[SubscriptionPlan] = Field(
        None, description="Subscription plan"
    )
    subscription_status: Optional[SubscriptionStatus] = Field(
        None, description="Subscription status"
    )
    usage_quota: Optional[int] = Field(None, ge=0, description="Usage quota")
    is_active: Optional[bool] = Field(None, description="Account active status")
    is_verified: Optional[bool] = Field(None, description="Email verification status")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_role": "enterprise",
                "subscription_plan": "enterprise",
                "subscription_status": "active",
                "usage_quota": 1000,
                "is_active": True,
                "is_verified": True,
            }
        }
    )


class UserActivity(BaseModel):
    """User activity response model."""

    activity_id: str = Field(..., description="Activity identifier")
    user_id: str = Field(..., description="User identifier")
    activity_type: str = Field(..., description="Type of activity")
    activity_data: Optional[dict[str, Any]] = Field(None, description="Activity data")
    ip_address: Optional[str] = Field(None, description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent")
    created_at: datetime = Field(..., description="Activity timestamp")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "activity_id": "act_1234567890abcde",
                "user_id": "usr_1234567890abcde",
                "activity_type": "login",
                "activity_data": {"method": "password", "success": True},
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0...",
                "created_at": "2024-01-15T10:30:00Z",
            }
        }
    )


class SystemMetric(BaseModel):
    """System metric response model."""

    metric_id: str = Field(..., description="Metric identifier")
    metric_name: str = Field(..., description="Metric name")
    metric_type: str = Field(..., description="Metric type")
    metric_value: dict[str, Any] = Field(..., description="Metric value")
    labels: Optional[dict[str, Any]] = Field(None, description="Metric labels")
    timestamp: datetime = Field(..., description="Metric timestamp")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "metric_id": "metric_1234567890abcde",
                "metric_name": "api_requests_total",
                "metric_type": "counter",
                "metric_value": {"count": 1250},
                "labels": {"endpoint": "/api/v1/analyze", "status": "success"},
                "timestamp": "2024-01-15T10:30:00Z",
            }
        }
    )


class AdminDashboard(BaseModel):
    """Admin dashboard response model."""

    user_stats: dict[str, Any] = Field(..., description="User statistics")
    usage_stats: dict[str, Any] = Field(..., description="Usage statistics")
    subscription_stats: dict[str, Any] = Field(
        ..., description="Subscription statistics"
    )
    system_metrics: dict[str, Any] = Field(..., description="System metrics summary")
    recent_activities: List[UserActivity] = Field(
        ..., description="Recent user activities"
    )
    contact_stats: Optional[dict[str, Any]] = Field(
        None, description="Contact message statistics"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_stats": {
                    "total_users": 1250,
                    "active_users": 1100,
                    "new_users_this_month": 85,
                    "verified_users": 950,
                },
                "usage_stats": {
                    "total_analyses": 15750,
                    "analyses_this_month": 2100,
                    "average_daily_analyses": 70,
                    "cost_this_month": 42.50,
                },
                "subscription_stats": {
                    "free_users": 850,
                    "basic_users": 200,
                    "professional_users": 150,
                    "enterprise_users": 50,
                    "monthly_recurring_revenue": 12500,
                },
                "system_metrics": {
                    "api_requests_24h": 2500,
                    "average_response_time": 450,
                    "error_rate": 0.02,
                    "cache_hit_rate": 0.75,
                },
                "recent_activities": [],
                "contact_stats": {
                    "unread_messages": 3,
                    "total_messages": 45,
                },
            }
        }
    )


class UserListResponse(BaseModel):
    """User list response model for admin."""

    users: List[UserProfile] = Field(..., description="List of users")
    total_count: int = Field(..., description="Total number of users")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")
    has_next: bool = Field(..., description="Whether there are more pages")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "users": [],
                "total_count": 1250,
                "page": 1,
                "page_size": 50,
                "has_next": True,
            }
        }
    )


class PasswordResetRequest(BaseModel):
    """Password reset request model."""

    email: EmailStr = Field(..., description="Email address to send reset link")

    model_config = ConfigDict(
        json_schema_extra={"example": {"email": "user@example.com"}}
    )


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation model."""

    token: str = Field(..., description="Password reset token from email")
    new_password: str = Field(
        ..., min_length=8, description="New password (minimum 8 characters)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "token": "abcdef123456789",
                "new_password": "MyNewSecurePassword123!",
            }
        }
    )
