"""
Tests for billing administration API endpoints.

Tests comprehensive billing monitoring, webhook management,
overage tracking, and payment analytics endpoints.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict
from unittest.mock import Mock, patch

import pytest
from fastapi import status
from httpx import AsyncClient

from github_analyzer.api.auth.dependencies import require_admin
from github_analyzer.database.models import (
    SubscriptionPlan,
    SubscriptionStatus,
    User,
)


@pytest.fixture
def mock_admin_user() -> Mock:
    """Mock authenticated admin user."""
    return Mock(
        spec=User,
        user_id="usr_admin123",
        email="admin@example.com",
        full_name="Admin User",
        user_role="admin",
        is_active=True,
    )


@pytest.fixture
def mock_regular_user() -> Mock:
    """Mock regular user for testing."""
    return Mock(
        spec=User,
        user_id="usr_test123",
        email="test@example.com",
        full_name="Test User",
        subscription_plan=SubscriptionPlan.PROFESSIONAL,
        subscription_status=SubscriptionStatus.ACTIVE,
        usage_quota=1000,
        usage_count=1200,
        stripe_customer_id="cus_test123",
    )


@pytest.fixture
def auth_headers() -> Dict[str, str]:
    """Authentication headers for admin API requests."""
    return {"Authorization": "Bearer admin_jwt_token"}


class TestBillingAdminAPI:
    """Test suite for billing administration API endpoints."""

    async def test_get_billing_overview_success(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test successful billing overview retrieval."""
        app = async_client.app

        async def mock_require_admin() -> str:
            return "usr_admin123"

        app.dependency_overrides[require_admin] = mock_require_admin
        mock_users = [
            Mock(
                user_id=f"usr_{i}",
                subscription_plan=SubscriptionPlan.PROFESSIONAL,
                usage_quota=1000,
                usage_count=1100,
            )
            for i in range(5)
        ]

        mock_payments = [
            Mock(amount=14900, status="succeeded"),  # $149.00
            Mock(amount=14900, status="succeeded"),
            Mock(amount=14900, status="failed"),
        ]

        mock_webhook_stats = {
            "success_rate": 95.5,
            "pending": 3,
        }

        with (
            patch(
                "github_analyzer.database.operations.UserOperations.get_users_by_subscription_plan",
                side_effect=[
                    [],  # Free users
                    [],  # Basic users
                    mock_users,  # Professional users
                    [],  # Enterprise users
                    [],  # Scale+ users
                    mock_users,  # Professional users (called again for overage calculation)
                    [],  # Enterprise users (called again for overage calculation)
                    [],  # Scale+ users (called again for overage calculation)
                ],
            ),
            patch(
                "github_analyzer.database.operations.PaymentOperations.get_payments_by_date_range",
                return_value=mock_payments,
            ),
            patch(
                "github_analyzer.database.operations.WebhookEventOperations.get_webhook_statistics",
                return_value=mock_webhook_stats,
            ),
        ):
            response = await async_client.get(
                "/api/v1/admin/billing/overview", headers=auth_headers
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["total_revenue_month"] == 298.0  # 2 successful payments
            assert data["active_subscriptions"]["PROFESSIONAL"] == 5
            assert data["overage_users_count"] == 5
            assert data["payment_success_rate"] == pytest.approx(66.67, 0.01)
            assert data["webhook_success_rate"] == 95.5

    async def test_get_subscription_metrics_success(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test successful subscription metrics retrieval."""
        app = async_client.app

        async def mock_require_admin() -> str:
            return "usr_admin123"

        app.dependency_overrides[require_admin] = mock_require_admin
        with patch(
            "github_analyzer.database.operations.UserOperations.get_users_by_subscription_plan",
            side_effect=[
                [Mock()] * 10,  # 10 Basic users
                [Mock()] * 5,  # 5 Professional users
                [Mock()] * 2,  # 2 Enterprise users
            ],
        ):
            response = await async_client.get(
                "/api/v1/admin/billing/subscriptions/metrics", headers=auth_headers
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["mrr"] == 2033  # (10*49) + (5*149) + (2*399)
            assert data["arr"] == 24396  # MRR * 12
            assert data["total_paid_subscriptions"] == 17
            assert data["plan_distribution"]["basic"] == 10
            assert data["average_revenue_per_user"] == pytest.approx(119.59, 0.01)

    async def test_get_overage_report_success(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test successful overage report generation."""
        app = async_client.app

        async def mock_require_admin() -> str:
            return "usr_admin123"

        app.dependency_overrides[require_admin] = mock_require_admin
        mock_users = [
            Mock(
                user_id=f"usr_{i}",
                email=f"user{i}@example.com",
                subscription_plan=SubscriptionPlan.PROFESSIONAL,
                usage_quota=1000,
                usage_count=1200 + (i * 100),
            )
            for i in range(3)
        ]

        mock_overage_info = {
            "is_over_quota": True,
            "in_grace_period": False,
            "overage_count": 200,
            "overage_cost": 4000,  # in cents
            "quota_limit": 1000,
            "grace_period_limit": 1050,
            "current_usage": 1200,
        }

        with (
            patch(
                "github_analyzer.database.operations.UserOperations.get_users_by_subscription_plan",
                side_effect=[mock_users, []],
            ),
            patch(
                "github_analyzer.billing.usage_tracker.UsageTracker.get_user_overage_info",
                return_value=mock_overage_info,
            ),
        ):
            response = await async_client.get(
                "/api/v1/admin/billing/overages/report?threshold=100",
                headers=auth_headers,
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 3
            assert data[0]["overage_amount"] == 400  # Highest overage first
            assert data[0]["email"] == "user2@example.com"
            assert all(
                report["overage_cost"] == 40.0 for report in data
            )  # Convert cents to dollars

    async def test_get_webhook_metrics_success(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test successful webhook metrics retrieval."""
        app = async_client.app

        async def mock_require_admin() -> str:
            return "usr_admin123"

        app.dependency_overrides[require_admin] = mock_require_admin
        mock_stats = {
            "total_webhooks": 1000,
            "processed": 950,
            "failed": 30,
            "pending": 20,
            "success_rate": 95.0,
            "average_processing_time": 150,
            "events_by_type": {
                "customer.subscription.created": 100,
                "invoice.payment_succeeded": 500,
            },
        }

        mock_failed_webhooks = [
            Mock(
                event_id=f"evt_{i}",
                event_type="invoice.payment_failed",
                attempts=3,
                last_error="Connection timeout",
                created_at=datetime.now(timezone.utc),
            )
            for i in range(5)
        ]

        with (
            patch(
                "github_analyzer.api.services.webhook_service.WebhookService.get_webhook_statistics",
                return_value=mock_stats,
            ),
            patch(
                "github_analyzer.database.operations.WebhookEventOperations.get_failed_webhooks",
                return_value=mock_failed_webhooks,
            ),
        ):
            response = await async_client.get(
                "/api/v1/admin/billing/webhooks/metrics", headers=auth_headers
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["total_webhooks"] == 1000
            assert data["success_rate"] == 95.0
            assert len(data["failed_webhook_details"]) == 5

    async def test_retry_failed_webhooks_success(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test successful webhook retry operation."""
        app = async_client.app

        async def mock_require_admin() -> str:
            return "usr_admin123"

        app.dependency_overrides[require_admin] = mock_require_admin
        mock_result = {
            "total_webhooks": 10,
            "successful_retries": 8,
            "failed_retries": 2,
        }

        with patch(
            "github_analyzer.api.services.webhook_service.WebhookService.retry_failed_webhooks",
            return_value=mock_result,
        ):
            response = await async_client.post(
                "/api/v1/admin/billing/webhooks/retry-failed?max_attempts=5",
                headers=auth_headers,
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["total_retried"] == 10
            assert data["successful"] == 8
            assert data["failed"] == 2

    async def test_cleanup_old_webhooks_success(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test successful webhook cleanup operation."""
        app = async_client.app

        async def mock_require_admin() -> str:
            return "usr_admin123"

        app.dependency_overrides[require_admin] = mock_require_admin
        mock_result = {"deleted_count": 250}

        with patch(
            "github_analyzer.api.services.webhook_service.WebhookService.cleanup_old_webhooks",
            return_value=mock_result,
        ):
            response = await async_client.delete(
                "/api/v1/admin/billing/webhooks/cleanup?days=30",
                headers=auth_headers,
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["deleted_count"] == 250
            assert data["days"] == 30

    async def test_get_recent_invoices_success(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test successful invoice list retrieval."""
        app = async_client.app

        async def mock_require_admin() -> str:
            return "usr_admin123"

        app.dependency_overrides[require_admin] = mock_require_admin
        mock_invoices = [
            Mock(
                invoice_id=f"inv_{i}",
                user_id=f"usr_{i}",
                amount_due=10000,  # $100.00
                amount_paid=10000 if i % 2 == 0 else None,
                status="paid" if i % 2 == 0 else "pending",
                due_date=datetime.now(timezone.utc) + timedelta(days=30),
                created_at=datetime.now(timezone.utc),
            )
            for i in range(3)
        ]

        mock_user = Mock(email="test@example.com")

        with (
            patch(
                "github_analyzer.database.operations.InvoiceOperations.get_recent_invoices",
                return_value=mock_invoices,
            ),
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_id",
                return_value=mock_user,
            ),
        ):
            response = await async_client.get(
                "/api/v1/admin/billing/invoices?limit=50", headers=auth_headers
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["total_count"] == 3
            assert len(data["invoices"]) == 3
            assert all(
                inv["user_email"] == "test@example.com" for inv in data["invoices"]
            )

    async def test_get_recent_invoices_with_status_filter(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test invoice retrieval with status filter."""
        app = async_client.app

        async def mock_require_admin() -> str:
            return "usr_admin123"

        app.dependency_overrides[require_admin] = mock_require_admin
        mock_invoices = [
            Mock(
                invoice_id="inv_1",
                user_id="usr_1",
                amount_due=10000,
                amount_paid=None,
                status="pending",
                due_date=datetime.now(timezone.utc) + timedelta(days=30),
                created_at=datetime.now(timezone.utc),
            )
        ]

        with (
            patch(
                "github_analyzer.database.operations.InvoiceOperations.get_invoices_by_status",
                return_value=mock_invoices,
            ),
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_id",
                return_value=Mock(email="pending@example.com"),
            ),
        ):
            response = await async_client.get(
                "/api/v1/admin/billing/invoices?status=pending&limit=50",
                headers=auth_headers,
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data["invoices"]) == 1
            assert data["invoices"][0]["status"] == "pending"

    async def test_get_recent_payments_success(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test successful payment history retrieval."""
        app = async_client.app

        async def mock_require_admin() -> str:
            return "usr_admin123"

        app.dependency_overrides[require_admin] = mock_require_admin
        mock_payments = [
            Mock(
                payment_id=f"pay_{i}",
                user_id=f"usr_{i}",
                amount=10000,  # $100.00
                status="succeeded" if i < 2 else "failed",
                payment_method="card",
                failure_message="Insufficient funds" if i >= 2 else None,
                processed_at=datetime.now(timezone.utc) if i < 2 else None,
            )
            for i in range(3)
        ]

        mock_user = Mock(email="test@example.com")

        with (
            patch(
                "github_analyzer.database.operations.PaymentOperations.get_payments_by_date_range",
                return_value=mock_payments,
            ),
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_id",
                return_value=mock_user,
            ),
        ):
            response = await async_client.get(
                "/api/v1/admin/billing/payments?days=7", headers=auth_headers
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["total_count"] == 3
            assert data["total_amount"] == 200.0  # 2 successful payments
            assert data["success_count"] == 2
            assert data["failed_count"] == 1

    async def test_reset_user_usage_success(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str],
        mock_regular_user: Mock,
    ):
        """Test successful user usage reset."""
        app = async_client.app

        async def mock_require_admin() -> str:
            return "usr_admin123"

        app.dependency_overrides[require_admin] = mock_require_admin
        with (
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_id",
                return_value=mock_regular_user,
            ),
            patch(
                "github_analyzer.database.operations.UserOperations.update_usage_count",
                return_value=True,
            ),
        ):
            response = await async_client.post(
                "/api/v1/admin/billing/usage/reset/usr_test123",
                headers=auth_headers,
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "success"
            assert "test@example.com" in data["message"]
            assert data["previous_usage"] == "1200"

    async def test_reset_user_usage_user_not_found(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test usage reset with non-existent user."""
        app = async_client.app

        async def mock_require_admin() -> str:
            return "usr_admin123"

        app.dependency_overrides[require_admin] = mock_require_admin
        with patch(
            "github_analyzer.database.operations.UserOperations.get_user_by_id",
            return_value=None,
        ):
            response = await async_client.post(
                "/api/v1/admin/billing/usage/reset/usr_invalid",
                headers=auth_headers,
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND
            data = response.json()
            assert "User usr_invalid not found" in data["detail"]

    async def test_reset_user_usage_failure(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str],
        mock_regular_user: Mock,
    ):
        """Test usage reset failure."""
        app = async_client.app

        async def mock_require_admin() -> str:
            return "usr_admin123"

        app.dependency_overrides[require_admin] = mock_require_admin
        with (
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_id",
                return_value=mock_regular_user,
            ),
            patch(
                "github_analyzer.database.operations.UserOperations.update_usage_count",
                return_value=False,
            ),
        ):
            response = await async_client.post(
                "/api/v1/admin/billing/usage/reset/usr_test123",
                headers=auth_headers,
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()
            assert "Failed to reset usage" in data["detail"]

    async def test_non_admin_access_denied(self, async_client: AsyncClient):
        """Test that non-admin users cannot access billing admin endpoints."""
        app = async_client.app

        async def mock_require_admin_denied() -> None:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )

        app.dependency_overrides[require_admin] = mock_require_admin_denied

        response = await async_client.get(
            "/api/v1/admin/billing/overview",
            headers={"Authorization": "Bearer regular_user_token"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "Admin access required" in data["detail"]

    async def test_billing_overview_calculations(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test billing overview with complex calculations."""
        app = async_client.app

        async def mock_require_admin() -> str:
            return "usr_admin123"

        app.dependency_overrides[require_admin] = mock_require_admin
        # Create users with different subscription plans and usage
        professional_users = [
            Mock(
                user_id=f"usr_p{i}",
                subscription_plan=SubscriptionPlan.PROFESSIONAL,
                usage_quota=1000,
                usage_count=1100 + (i * 50),  # Various overage amounts
            )
            for i in range(3)
        ]

        enterprise_users = [
            Mock(
                user_id=f"usr_e{i}",
                subscription_plan=SubscriptionPlan.ENTERPRISE,
                usage_quota=5000,
                usage_count=5200 + (i * 100),  # Various overage amounts
            )
            for i in range(2)
        ]

        # Mix of successful and failed payments
        payments = [
            Mock(amount=14900, status="succeeded"),  # Professional
            Mock(amount=14900, status="succeeded"),
            Mock(amount=39900, status="succeeded"),  # Enterprise
            Mock(amount=14900, status="failed"),
            Mock(amount=39900, status="failed"),
        ]

        with (
            patch(
                "github_analyzer.database.operations.UserOperations.get_users_by_subscription_plan",
                side_effect=[
                    [],  # Free users
                    [],  # Basic users
                    professional_users,
                    enterprise_users,
                    [],  # Scale+ users
                    professional_users,  # Called again for overage calculation
                    enterprise_users,  # Called again for overage calculation
                    [],  # Scale+ users (called again for overage calculation)
                ],
            ),
            patch(
                "github_analyzer.database.operations.PaymentOperations.get_payments_by_date_range",
                return_value=payments,
            ),
            patch(
                "github_analyzer.database.operations.WebhookEventOperations.get_webhook_statistics",
                return_value={"success_rate": 92.3, "pending": 5},
            ),
        ):
            response = await async_client.get(
                "/api/v1/admin/billing/overview", headers=auth_headers
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # Total revenue: 3 successful payments
            assert data["total_revenue_month"] == 697.0  # (149*2 + 399) = 697

            # Overage calculations
            # Professional: (100*0.20) + (150*0.20) + (200*0.20) = 90
            # Enterprise: (200*0.10) + (300*0.10) = 50
            # Total: 140
            assert data["total_overage_revenue"] == 140.0
            assert data["overage_users_count"] == 5
            assert data["payment_success_rate"] == 60.0

    async def test_webhook_metrics_edge_cases(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test webhook metrics with edge cases."""
        app = async_client.app

        async def mock_require_admin() -> str:
            return "usr_admin123"

        app.dependency_overrides[require_admin] = mock_require_admin
        # Test with no webhooks
        with (
            patch(
                "github_analyzer.api.services.webhook_service.WebhookService.get_webhook_statistics",
                return_value={
                    "total_webhooks": 0,
                    "processed": 0,
                    "failed": 0,
                    "pending": 0,
                    "success_rate": 0,
                    "average_processing_time": 0,
                    "events_by_type": {},
                },
            ),
            patch(
                "github_analyzer.database.operations.WebhookEventOperations.get_failed_webhooks",
                return_value=[],
            ),
        ):
            response = await async_client.get(
                "/api/v1/admin/billing/webhooks/metrics", headers=auth_headers
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["total_webhooks"] == 0
            assert data["success_rate"] == 0
            assert len(data["failed_webhook_details"]) == 0

    async def test_overage_report_grace_period_calculations(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test overage report with grace period calculations."""
        app = async_client.app

        async def mock_require_admin() -> str:
            return "usr_admin123"

        app.dependency_overrides[require_admin] = mock_require_admin
        mock_users = [
            Mock(
                user_id="usr_1",
                email="under_grace@example.com",
                subscription_plan=SubscriptionPlan.PROFESSIONAL,
                usage_quota=1000,
                usage_count=1050,  # Within 10% grace
            ),
            Mock(
                user_id="usr_2",
                email="over_grace@example.com",
                subscription_plan=SubscriptionPlan.PROFESSIONAL,
                usage_quota=1000,
                usage_count=1150,  # Over 10% grace
            ),
        ]

        mock_overage_info = {
            "is_over_quota": True,
            "in_grace_period": False,
            "overage_count": 50,
            "overage_cost": 1000,  # in cents
            "quota_limit": 1000,
            "grace_period_limit": 1050,
            "current_usage": 1050,
        }

        with (
            patch(
                "github_analyzer.database.operations.UserOperations.get_users_by_subscription_plan",
                side_effect=[mock_users, []],
            ),
            patch(
                "github_analyzer.billing.usage_tracker.UsageTracker.get_user_overage_info",
                return_value=mock_overage_info,
            ),
        ):
            response = await async_client.get(
                "/api/v1/admin/billing/overages/report",
                headers=auth_headers,
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 2

            # Check grace period calculations
            under_grace = next(
                r for r in data if r["email"] == "under_grace@example.com"
            )
            assert under_grace["in_grace_period"] is True
            assert under_grace["grace_remaining"] == 50  # 1100 - 1050

            over_grace = next(r for r in data if r["email"] == "over_grace@example.com")
            assert over_grace["in_grace_period"] is False
            assert over_grace["grace_remaining"] == 0
