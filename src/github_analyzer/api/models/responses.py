# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
API response models.

This module defines Pydantic models for all API response payloads,
ensuring consistent response structure and automatic documentation.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from ...database.models import ContactStatus


class EvidencePatternResponse(BaseModel):
    """Evidence pattern extracted from repository analysis."""

    name: str = Field(..., description="Pattern name (e.g., 'Testing Practices')")
    pattern_type: str = Field(
        ..., description="Type of pattern (technical, behavioral, etc.)"
    )
    evidence: str = Field(..., description="Specific examples from the repository")
    context: str = Field(..., description="Why this pattern matters for hiring")
    insight: str = Field(..., description="What this reveals about the developer")


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Response timestamp")
    version: str = Field(..., description="API version")
    environment: str = Field(..., description="Environment name")


class MetricsResponse(BaseModel):
    """API metrics response model."""

    total_requests: int = Field(..., description="Total number of requests")
    cache_hit_rate: float = Field(..., description="Cache hit rate percentage")
    avg_response_time: float = Field(
        ..., description="Average response time in seconds"
    )
    active_connections: int = Field(..., description="Number of active connections")
    uptime_seconds: int = Field(..., description="Service uptime in seconds")


class CacheStatsResponse(BaseModel):
    """Cache statistics response model."""

    total_keys: int = Field(..., description="Total number of cached keys")
    hit_count: int = Field(..., description="Number of cache hits")
    miss_count: int = Field(..., description="Number of cache misses")
    hit_rate: float = Field(..., description="Cache hit rate percentage")
    memory_usage: int = Field(..., description="Cache memory usage in bytes")


class AnalysisResponse(BaseModel):
    """Single repository analysis response model."""

    id: Optional[str] = Field(None, description="Analysis ID for retrieval")
    repository_url: str = Field(..., description="Analyzed repository URL")
    context: str = Field(..., description="Analysis context")
    analysis: dict[str, Any] = Field(..., description="Complete analysis result")
    metadata: dict[str, Any] = Field(..., description="Analysis metadata and timing")
    formatted_report: Optional[str] = Field(
        None,
        description="Formatted report in requested format (user_friendly, markdown, html)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "repository_url": "https://github.com/user/repository",
                "context": "general",
                "analysis": {
                    "summary": (
                        "Evidence-based analysis reveals strong testing practices and clean architecture"
                    ),
                    "evidence_strength": {
                        "technical_competence": 85,
                        "communication_skills": 75,
                        "professional_practices": 90,
                        "growth_potential": 80,
                    },
                    "evidence_patterns": [
                        {
                            "pattern": "test_coverage_high",
                            "evidence": "98% test coverage with 847 tests across 23 test files",
                            "commits": ["abc123", "def456"],
                            "files": ["tests/unit/", "tests/integration/"],
                            "strength": "strong",
                        }
                    ],
                    "context_alignment": {
                        "startup": {
                            "shipping_velocity": "Fast iteration cycles, 15 commits in last 2 weeks",
                            "adaptability": "Multiple technology switches handled cleanly",
                        },
                        "enterprise": {
                            "scalability_thinking": "Implements proper error handling and logging",
                            "maintainability": "Clear separation of concerns",
                        },
                    },
                    "verification_gaps": [
                        "Cannot assess team collaboration - solo repository"
                    ],
                    "key_insights": [
                        "Exceptional test coverage",
                        "Clean architecture patterns",
                    ],
                    "interview_questions": [
                        "How do you approach testing in production systems?"
                    ],
                    "repository_type": "portfolio",
                    "data_completeness": 0.92,
                },
                "metadata": {
                    "analysis_id": "analysis_1704110400_1234",
                    "repository_type": "portfolio",
                    "analysis_depth": "comprehensive",
                    "ai_analysis_used": True,
                    "analysis_cost_usd": 0.002,
                    "response_time_seconds": 15.5,
                    "cached": False,
                    "timestamp": "2024-01-01T12:00:00Z",
                },
            }
        }
    )


class BatchAnalysisResponse(BaseModel):
    """Batch repository analysis response model."""

    results: List[AnalysisResponse] = Field(
        ..., description="Successful analysis results"
    )
    errors: List[dict[str, Any]] = Field(..., description="Failed analysis errors")
    metadata: dict[str, Any] = Field(..., description="Batch analysis metadata")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "results": [
                    {
                        "repository_url": "https://github.com/user/repo1",
                        "context": "general",
                        "analysis": {
                            "summary": (
                                "Evidence-based analysis shows excellent repository with strong practices"
                            ),
                            "evidence_strength": {
                                "technical_competence": 85,
                                "communication_skills": 80,
                                "professional_practices": 88,
                                "growth_potential": 82,
                            },
                            "key_insights": [
                                "Strong testing practices",
                                "Clean architecture",
                            ],
                        },
                        "metadata": {
                            "analysis_cost_usd": 0.002,
                            "response_time_seconds": 15.5,
                            "ai_analysis_used": True,
                            "cached": False,
                        },
                    }
                ],
                "errors": [],
                "metadata": {
                    "total_repositories": 1,
                    "successful_count": 1,
                    "failed_count": 0,
                    "total_time_seconds": 15.5,
                    "batch_id": "batch_1704110400_192168001",
                },
            }
        }
    )


class SuccessResponse(BaseModel):
    """Generic success response model."""

    success: bool = Field(True, description="Operation success status")
    message: str = Field(..., description="Success message")
    data: Optional[dict[str, Any]] = Field(None, description="Response data")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Response timestamp"
    )


class ErrorResponse(BaseModel):
    """Error response model."""

    detail: str = Field(..., description="Error description")
    error_code: Optional[str] = Field(None, description="Error code")
    timestamp: datetime = Field(..., description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")


class RepositorySizeLimitErrorResponse(BaseModel):
    """Repository size limit error response model."""

    error: str = Field(..., description="Error type")
    message: str = Field(
        ..., description="Detailed error message with upgrade suggestions"
    )
    repository_url: str = Field(
        ..., description="Repository URL that exceeded the limit"
    )
    current_plan: str = Field(..., description="User's current subscription plan")
    size_limit_mb: int = Field(..., description="Current plan's size limit in MB")
    repository_size_mb: float = Field(..., description="Actual repository size in MB")
    suggested_plans: List[str] = Field(
        ..., description="Plans that support this repository size"
    )
    upgrade_url: str = Field(
        default="/pricing", description="URL to upgrade subscription"
    )
    timestamp: datetime = Field(..., description="Error timestamp")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "Repository too large",
                "message": "Repository size (150.5MB) exceeds maximum allowed size (50MB) for your free plan. Upgrade to Basic (100MB), Professional (500MB), or Enterprise (custom limits) for larger repositories.",
                "repository_url": "https://github.com/user/large-repo",
                "current_plan": "free",
                "size_limit_mb": 50,
                "repository_size_mb": 150.5,
                "suggested_plans": ["basic", "professional", "enterprise"],
                "upgrade_url": "/pricing",
                "timestamp": "2024-01-01T12:00:00Z",
            }
        }
    )


class CacheInvalidateResponse(BaseModel):
    """Cache invalidation response model."""

    invalidated_keys: int = Field(..., description="Number of keys invalidated")
    message: str = Field(..., description="Success message")
    timestamp: datetime = Field(..., description="Operation timestamp")


class ContactMessageResponse(BaseModel):
    """Contact message response model."""

    message_id: str = Field(..., description="Unique message identifier")
    name: str = Field(..., description="Name of the sender")
    email: str = Field(..., description="Email address of the sender")
    subject: str = Field(..., description="Message subject")
    message: str = Field(..., description="Message content")
    status: ContactStatus = Field(..., description="Message status")
    admin_response: Optional[str] = Field(None, description="Admin response if any")
    responded_at: Optional[datetime] = Field(
        None, description="Timestamp when admin responded"
    )
    responded_by: Optional[str] = Field(None, description="Admin user ID who responded")
    created_at: datetime = Field(..., description="Message creation timestamp")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message_id": "msg_AbCdEfGhIjKlMnOp",
                "name": "John Doe",
                "email": "john.doe@example.com",
                "subject": "Question about Enterprise Plan",
                "message": "I'm interested in learning more about the Enterprise Plan features...",
                "status": "unread",
                "admin_response": None,
                "responded_at": None,
                "responded_by": None,
                "created_at": "2024-01-01T12:00:00Z",
            }
        }
    )


class ContactMessageListResponse(BaseModel):
    """Paginated list of contact messages."""

    messages: List[ContactMessageResponse] = Field(
        ..., description="List of contact messages"
    )
    total: int = Field(..., description="Total number of messages")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")


class ContactFormSubmitResponse(BaseModel):
    """Response after successful contact form submission."""

    message_id: str = Field(..., description="Created message ID")
    message: str = Field(
        default="Thank you for contacting us. We'll respond as soon as possible.",
        description="Success message",
    )
    timestamp: datetime = Field(..., description="Submission timestamp")


class APIKeyResponse(BaseModel):
    """API key response model."""

    key_id: str = Field(..., description="Unique API key identifier")
    name: str = Field(..., description="Descriptive name for the API key")
    api_key: Optional[str] = Field(
        None, description="Plain text API key (only shown once on creation)"
    )
    permissions: List[str] = Field(
        ..., description="List of permissions granted to this key"
    )
    monthly_quota: int = Field(
        ..., description="Monthly API call quota (-1 for unlimited)"
    )
    monthly_usage: int = Field(..., description="Current month's API call usage")
    is_active: bool = Field(..., description="Whether the API key is active")
    created_at: datetime = Field(..., description="API key creation timestamp")
    last_used: Optional[datetime] = Field(
        None, description="Last time the API key was used"
    )
    expires_at: Optional[datetime] = Field(
        None, description="API key expiration timestamp"
    )
    user_id: Optional[str] = Field(
        None, description="Owner user ID (only in admin views)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "key_id": "ak_AbCdEfGhIjKlMnOp",
                "name": "Production API Key",
                "api_key": "gha_1234567890_123456789012345678901",
                "permissions": ["analyze", "batch"],
                "monthly_quota": 1000,
                "monthly_usage": 245,
                "is_active": True,
                "created_at": "2024-01-01T12:00:00Z",
                "last_used": "2024-01-15T14:30:00Z",
                "expires_at": None,
                "user_id": None,
            }
        }
    )


class APIKeyListResponse(BaseModel):
    """List of API keys response model."""

    keys: List[APIKeyResponse] = Field(..., description="List of API keys")
    total_count: int = Field(..., description="Total number of API keys")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "keys": [
                    {
                        "key_id": "ak_AbCdEfGhIjKlMnOp",
                        "name": "Production API Key",
                        "api_key": None,
                        "permissions": ["analyze", "batch"],
                        "monthly_quota": 1000,
                        "monthly_usage": 245,
                        "is_active": True,
                        "created_at": "2024-01-01T12:00:00Z",
                        "last_used": "2024-01-15T14:30:00Z",
                        "expires_at": None,
                    }
                ],
                "total_count": 1,
            }
        }
    )


class APIKeyUsageResponse(BaseModel):
    """API key usage statistics response model."""

    key_id: str = Field(..., description="API key identifier")
    name: str = Field(..., description="API key name")
    monthly_quota: int = Field(
        ..., description="Monthly API call quota (-1 for unlimited)"
    )
    monthly_usage: int = Field(..., description="Current month's API call usage")
    remaining_quota: Optional[int] = Field(
        None, description="Remaining API calls this month"
    )
    has_quota_available: bool = Field(
        ..., description="Whether quota is available for more calls"
    )
    last_quota_reset: Optional[datetime] = Field(
        None, description="Last quota reset timestamp"
    )
    last_used: Optional[datetime] = Field(
        None, description="Last time the API key was used"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "key_id": "ak_AbCdEfGhIjKlMnOp",
                "name": "Production API Key",
                "monthly_quota": 1000,
                "monthly_usage": 245,
                "remaining_quota": 755,
                "has_quota_available": True,
                "last_quota_reset": "2024-01-01T00:00:00Z",
                "last_used": "2024-01-15T14:30:00Z",
            }
        }
    )


class QuotaDetailsResponse(BaseModel):
    """Detailed quota and usage information for a user."""

    user_id: str = Field(..., description="User's unique identifier")
    billing_period: str = Field(..., description="Billing period (YYYY-MM)")
    usage_breakdown: Dict[str, int] = Field(
        ..., description="Breakdown of usage by type"
    )
    total_usage: int = Field(..., description="Total usage units consumed")
    total_cost: float = Field(..., description="Total cost of usage in USD")
    quota_total: int = Field(..., description="Total quota allocated for the period")
    quota_remaining: int = Field(..., description="Remaining quota for the period")


class BulkResetResponse(BaseModel):
    """Response for a bulk usage reset operation."""

    total_users: int = Field(..., description="Total users considered for reset")
    reset_successful: int = Field(..., description="Number of users successfully reset")
    reset_failed: int = Field(..., description="Number of users who failed to reset")
    plan_filter: Optional[str] = Field(None, description="Plan filter applied, if any")


class BillingOverviewResponse(BaseModel):
    """Comprehensive billing overview for administrators."""

    total_revenue_month: float = Field(
        ..., description="Total revenue for current month in USD"
    )
    total_revenue_all_time: float = Field(
        ..., description="Total revenue all-time in USD"
    )
    active_subscriptions: Dict[str, int] = Field(
        ..., description="Active subscriptions by plan"
    )
    total_active_subscriptions: int = Field(
        ..., description="Total number of active paid subscriptions"
    )
    overage_users_count: int = Field(..., description="Number of users with overages")
    total_overage_revenue: float = Field(
        ..., description="Total estimated overage revenue in USD"
    )
    payment_success_rate: float = Field(
        ..., description="Payment success rate percentage"
    )
    failed_payments_count: int = Field(
        ..., description="Number of failed payments this month"
    )
    webhook_success_rate: float = Field(
        ..., description="Webhook processing success rate"
    )
    pending_webhooks: int = Field(..., description="Number of pending webhooks")


class SubscriptionMetricsResponse(BaseModel):
    """Detailed subscription metrics for monitoring."""

    mrr: float = Field(..., description="Monthly Recurring Revenue in USD")
    arr: float = Field(..., description="Annual Recurring Revenue in USD")
    total_paid_subscriptions: int = Field(
        ..., description="Total number of paid subscriptions"
    )
    plan_distribution: Dict[str, int] = Field(
        ..., description="Distribution of subscriptions by plan"
    )
    churn_rate: float = Field(..., description="Monthly churn rate percentage")
    upgrades_this_month: int = Field(
        ..., description="Number of plan upgrades this month"
    )
    downgrades_this_month: int = Field(
        ..., description="Number of plan downgrades this month"
    )
    average_revenue_per_user: float = Field(
        ..., description="Average revenue per user (ARPU) in USD"
    )


class OverageReportResponse(BaseModel):
    """Overage report for a single user."""

    user_id: str = Field(..., description="User's unique identifier")
    email: str = Field(..., description="User's email address")
    plan: str = Field(..., description="User's subscription plan")
    usage_quota: int = Field(..., description="Monthly usage quota")
    usage_count: int = Field(..., description="Current usage count")
    overage_amount: int = Field(..., description="Number of calls over quota")
    overage_cost: float = Field(..., description="Estimated overage cost in USD")
    overage_rate: str = Field(..., description="Overage rate per call")
    in_grace_period: bool = Field(..., description="Whether user is in grace period")
    grace_remaining: int = Field(..., description="Remaining grace period calls")
    billing_period: str = Field(..., description="Current billing period")


class WebhookMetricsResponse(BaseModel):
    """Webhook processing metrics."""

    total_webhooks: int = Field(..., description="Total number of webhooks received")
    processed: int = Field(..., description="Number of successfully processed webhooks")
    failed: int = Field(..., description="Number of failed webhooks")
    pending: int = Field(..., description="Number of pending webhooks")
    success_rate: float = Field(..., description="Processing success rate percentage")
    average_processing_time: int = Field(
        ..., description="Average processing time in milliseconds"
    )
    events_by_type: Dict[str, int] = Field(
        ..., description="Webhook count by event type"
    )
    failed_webhook_details: List[Dict[str, Any]] = Field(
        ..., description="Details of recent failed webhooks"
    )


class InvoiceListResponse(BaseModel):
    """List of invoices for monitoring."""

    invoices: List[Dict[str, Any]] = Field(..., description="List of invoice details")
    total_count: int = Field(..., description="Total number of invoices")


class PaymentListResponse(BaseModel):
    """List of payments with summary statistics."""

    payments: List[Dict[str, Any]] = Field(..., description="List of payment details")
    total_count: int = Field(..., description="Total number of payments")
    total_amount: float = Field(
        ..., description="Total successful payment amount in USD"
    )
    success_count: int = Field(..., description="Number of successful payments")
    failed_count: int = Field(..., description="Number of failed payments")


class BatchHistoryResponse(BaseModel):
    """Response for batch history list."""

    success: bool
    data: List[Dict[str, Any]]
    total_count: int = Field(..., description="Total number of batch records")
    message: str


class BatchDetailsResponse(BaseModel):
    """Response for batch details."""

    success: bool
    data: Dict[str, Any]
    message: str


class BatchStatisticsResponse(BaseModel):
    """Response for batch statistics."""

    success: bool
    data: Dict[str, Any]
    message: str


class PRAnalysisResponse(BaseModel):
    """Response model for PR analysis."""

    analysis_id: str = Field(..., description="Unique ID of the PR analysis")
    username: str = Field(..., description="GitHub username analyzed")
    context: str = Field(
        ..., description="Analysis context used (STARTUP, ENTERPRISE, etc.)"
    )
    total_prs_analyzed: int = Field(..., description="Total number of PRs analyzed")
    repositories_contributed: List[str] = Field(
        ..., description="List of repositories with contributions"
    )
    summary_report: str = Field(..., description="Human-readable summary report")
    detailed_report: Dict[str, Any] = Field(
        ..., description="Detailed structured report with evidence sections"
    )
    ai_insights: Optional[Dict[str, Any]] = Field(
        None,
        description="AI-generated insights including interview questions and analysis",
    )
    data_quality: str = Field(
        ...,
        description="Quality of data available: 'high' (10+ PRs), 'moderate' (5+ PRs or 1000+ lines), 'low' (< 5 PRs)",
    )
    ai_insights_available: bool = Field(
        ...,
        description="Whether AI insights were generated (requires sufficient data)",
    )
    api_calls_used: int = Field(..., description="Number of GitHub API calls used")
    fetch_time_seconds: float = Field(..., description="Time taken to fetch PR data")
    total_time_seconds: float = Field(
        ..., description="Total time for complete analysis"
    )
    from_cache: bool = Field(..., description="Whether result was from cache")
    remaining_analyses_this_month: int = Field(
        ..., description="Remaining PR analyses for current month"
    )
    monthly_limit: int = Field(..., description="Monthly limit for PR analyses")
    status: Optional[str] = Field(
        None,
        description="Analysis status: 'pending', 'processing', 'completed', 'failed'",
    )
