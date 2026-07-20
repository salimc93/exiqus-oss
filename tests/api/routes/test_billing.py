"""
Tests for billing API endpoints.

Tests subscription management, usage tracking, invoice retrieval,
and webhook processing endpoints.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import status

from github_analyzer.database.models import (
    Invoice,
    Payment,
    SubscriptionPlan,
    SubscriptionStatus,
    User,
)


class TestBillingAPI:
    """Test suite for billing API endpoints."""

    @pytest.fixture
    def mock_user(self):
        """Mock authenticated user."""
        return Mock(
            spec=User,
            **{
                "user_id": "usr_test123",
                "email": "test@example.com",
                "full_name": "Test User",
                "subscription_plan": SubscriptionPlan.FREE,
                "subscription_status": SubscriptionStatus.ACTIVE,
                "usage_quota": 10,
                "usage_count": 2,
                "stripe_customer_id": "cus_test123",
                "stripe_subscription_id": "sub_test123",
            },
        )

    @pytest.fixture
    def auth_headers(self):
        """Authentication headers for API requests."""
        return {"Authorization": "Bearer test_jwt_token"}

    @pytest.fixture
    async def authenticated_client(self, test_db):
        """Create async test client with mocked authentication."""
        from httpx import ASGITransport, AsyncClient

        from github_analyzer.api.auth.dependencies import get_current_user_id
        from github_analyzer.database.connection import get_db_session
        from tests.conftest import create_test_app

        app = create_test_app()
        session_maker = test_db

        # Override database dependency
        async def override_get_db():
            async with session_maker() as session:
                yield session

        # Override auth dependency to return test user ID
        async def mock_get_current_user_id():
            return "usr_test123"

        app.dependency_overrides[get_db_session] = override_get_db
        app.dependency_overrides[get_current_user_id] = mock_get_current_user_id

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client

        # Clear overrides
        app.dependency_overrides.clear()

    async def test_get_subscription_status_success(
        self, authenticated_client, auth_headers, mock_user
    ):
        """Test successful subscription status retrieval."""
        subscription_status = {
            "user_id": "usr_test123",
            "plan": "basic",
            "status": "active",
            "usage_quota": 100,
            "usage_consumed": 25,
            "usage_remaining": 75,
            "current_period_start": "2024-07-01T00:00:00Z",
            "current_period_end": "2024-07-31T23:59:59Z",
        }

        with patch(
            "github_analyzer.billing.subscription_manager.SubscriptionManager.get_subscription_status",
            return_value=subscription_status,
        ):
            response = await authenticated_client.get(
                "/api/v1/billing/subscription", headers=auth_headers
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["data"]["user_id"] == "usr_test123"
            assert data["data"]["plan"] == "basic"

    async def test_get_subscription_status_error(
        self, authenticated_client, auth_headers
    ):
        """Test subscription status retrieval with error."""
        with patch(
            "github_analyzer.billing.subscription_manager.SubscriptionManager.get_subscription_status",
            side_effect=Exception("Database error"),
        ):
            response = await authenticated_client.get(
                "/api/v1/billing/subscription", headers=auth_headers
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    async def test_create_subscription_success(
        self, authenticated_client, auth_headers
    ):
        """Test successful subscription creation."""
        request_data = {"plan": "basic", "payment_method_id": "pm_test123"}

        subscription_data = {
            "subscription_id": "sub_test123",
            "status": "active",
            "plan": "basic",
            "checkout_url": "https://checkout.stripe.com/test",
        }

        with patch(
            "github_analyzer.billing.subscription_manager.SubscriptionManager.create_subscription",
            return_value=subscription_data,
        ):
            response = await authenticated_client.post(
                "/api/v1/billing/subscription", headers=auth_headers, json=request_data
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["data"]["subscription_id"] == "sub_test123"

    async def test_create_subscription_invalid_plan(
        self, authenticated_client, auth_headers
    ):
        """Test subscription creation with invalid plan."""
        request_data = {"plan": "INVALID_PLAN"}

        response = await authenticated_client.post(
            "/api/v1/billing/subscription", headers=auth_headers, json=request_data
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_update_subscription_success(
        self, authenticated_client, auth_headers
    ):
        """Test successful subscription update."""
        request_data = {"plan": "professional"}

        subscription_data = {
            "subscription_id": "sub_test123",
            "status": "active",
            "plan": "professional",
        }

        with patch(
            "github_analyzer.billing.subscription_manager.SubscriptionManager.update_subscription_plan",
            return_value=subscription_data,
        ):
            response = await authenticated_client.put(
                "/api/v1/billing/subscription", headers=auth_headers, json=request_data
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["data"]["plan"] == "professional"

    async def test_cancel_subscription_success(
        self, authenticated_client, auth_headers
    ):
        """Test successful subscription cancellation."""
        cancellation_data = {
            "subscription_id": "sub_test123",
            "status": "canceled",
            "cancel_at_period_end": True,
        }

        with patch(
            "github_analyzer.billing.subscription_manager.SubscriptionManager.cancel_subscription",
            return_value=cancellation_data,
        ):
            response = await authenticated_client.delete(
                "/api/v1/billing/subscription?at_period_end=true", headers=auth_headers
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["data"]["status"] == "canceled"

    async def test_create_checkout_session_success(
        self, authenticated_client, auth_headers, mock_user
    ):
        """Test successful checkout session creation."""
        request_data = {
            "plan": "basic",
            "success_url": "https://example.com/success",
            "cancel_url": "https://example.com/cancel",
        }

        checkout_session = {
            "id": "cs_test123",
            "url": "https://checkout.stripe.com/c/pay/test123",
        }

        with (
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_id",
                return_value=mock_user,
            ),
            patch(
                "github_analyzer.billing.stripe_client.StripeClient.create_customer",
                return_value={"id": "cus_test123"},
            ),
            patch(
                "github_analyzer.billing.stripe_client.StripeClient.create_checkout_session",
                return_value=checkout_session,
            ),
        ):
            response = await authenticated_client.post(
                "/api/v1/billing/checkout-session",
                headers=auth_headers,
                json=request_data,
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert (
                data["data"]["checkout_url"]
                == "https://checkout.stripe.com/c/pay/test123"
            )

    async def test_get_usage_summary_success(
        self, authenticated_client, auth_headers, mock_user
    ):
        """Test successful usage summary retrieval."""
        # Patch all dependencies used in the billing route
        with (
            patch(
                "github_analyzer.api.routes.billing.UserOperations.get_user_by_id",
                new_callable=AsyncMock,
                return_value=mock_user,
            ),
            patch(
                "github_analyzer.api.routes.billing.CandidateUsageService"
            ) as mock_candidate_service,
            patch(
                "github_analyzer.api.routes.billing.PlanFeatures.get_plan_limits"
            ) as mock_plan_features,
        ):
            # Mock the candidate usage service instance and methods
            mock_service_instance = AsyncMock()
            mock_service_instance.get_monthly_usage = AsyncMock(return_value=2)
            mock_candidate_service.return_value = mock_service_instance
            mock_candidate_service.get_tier_limit = Mock(return_value=10)

            # Mock plan features
            mock_plan_features.return_value = {
                "features": ["GitHub Portfolio Analysis", "PR Analysis"]
            }

            response = await authenticated_client.get(
                "/api/v1/billing/usage", headers=auth_headers
            )

            # Debug: print response details if failing
            if response.status_code != status.HTTP_200_OK:
                print(f"\nResponse status: {response.status_code}")
                print(f"Response body: {response.text}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["user_id"] == "usr_test123"
            assert data["plan"] == "FREE"
            assert data["usage_quota"] == 10
            assert data["usage_consumed"] == 2
            assert data["usage_remaining"] == 8

    async def test_get_invoices_success(self, authenticated_client, auth_headers):
        """Test successful invoice retrieval."""
        mock_invoice = Mock(
            spec=Invoice,
            **{
                "invoice_id": "inv_test123",
                "amount_due": 2000,
                "amount_paid": 2000,
                "currency": "usd",
                "status": "paid",
                "billing_period_start": datetime(2024, 7, 1, tzinfo=timezone.utc),
                "billing_period_end": datetime(2024, 7, 31, tzinfo=timezone.utc),
                "due_date": None,
                "paid_at": datetime(2024, 7, 1, tzinfo=timezone.utc),
                "invoice_url": "https://invoice.stripe.com/test",
                "created_at": datetime(2024, 7, 1, tzinfo=timezone.utc),
            },
        )

        with patch(
            "github_analyzer.database.operations.InvoiceOperations.get_user_invoices",
            return_value=[mock_invoice],
        ):
            response = await authenticated_client.get(
                "/api/v1/billing/invoices?limit=10&offset=0", headers=auth_headers
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 1
            assert data[0]["invoice_id"] == "inv_test123"
            assert data[0]["amount_due"] == 2000
            assert data[0]["status"] == "paid"

    async def test_get_payments_success(self, authenticated_client, auth_headers):
        """Test successful payment history retrieval."""
        mock_payment = Mock(
            spec=Payment,
            **{
                "payment_id": "pay_test123",
                "amount": 2000,
                "currency": "usd",
                "status": "succeeded",
                "payment_method": "card",
                "created_at": datetime(2024, 7, 1, tzinfo=timezone.utc),
                "processed_at": datetime(2024, 7, 1, tzinfo=timezone.utc),
            },
        )

        with patch(
            "github_analyzer.database.operations.PaymentOperations.get_user_payments",
            return_value=[mock_payment],
        ):
            response = await authenticated_client.get(
                "/api/v1/billing/payments?limit=10&offset=0", headers=auth_headers
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 1
            assert data[0]["payment_id"] == "pay_test123"
            assert data[0]["amount"] == 2000
            assert data[0]["status"] == "succeeded"

    async def test_stripe_webhook_success(self, authenticated_client):
        """Test successful Stripe webhook processing."""
        webhook_payload = {
            "id": "evt_test123",
            "type": "customer.subscription.created",
            "data": {
                "object": {
                    "id": "sub_test123",
                    "customer": "cus_test123",
                    "status": "active",
                }
            },
        }

        webhook_result = {
            "processed": True,
            "event_type": "customer.subscription.created",
            "event_id": "evt_test123",
        }

        with patch(
            "github_analyzer.billing.stripe_client.StripeClient.verify_webhook_signature",
            return_value=webhook_payload,
        ):
            with patch(
                "github_analyzer.api.services.webhook_service.WebhookService.process_webhook",
                return_value=webhook_result,
            ):
                response = await authenticated_client.post(
                    "/api/v1/billing/webhooks/stripe",
                    json=webhook_payload,
                    headers={"stripe-signature": "test_signature"},
                )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["processed"] is True
            assert data["event_type"] == "customer.subscription.created"

    async def test_stripe_webhook_missing_signature(self, authenticated_client):
        """Test Stripe webhook with missing signature."""
        webhook_payload = {"id": "evt_test123", "type": "customer.subscription.created"}

        response = await authenticated_client.post(
            "/api/v1/billing/webhooks/stripe", json=webhook_payload
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "Missing Stripe signature" in data["detail"]

    async def test_stripe_webhook_processing_error(self, authenticated_client):
        """Test Stripe webhook with processing error."""
        webhook_payload = {"id": "evt_test123", "type": "customer.subscription.created"}

        with patch(
            "github_analyzer.api.services.webhook_service.WebhookService.process_webhook",
            side_effect=Exception("Processing error"),
        ):
            response = await authenticated_client.post(
                "/api/v1/billing/webhooks/stripe",
                json=webhook_payload,
                headers={"stripe-signature": "test_signature"},
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()
            assert "Webhook processing error" in data["detail"]

    async def test_get_usage_summary_user_not_found(
        self, authenticated_client, auth_headers
    ):
        """Test usage summary with user not found."""
        with patch(
            "github_analyzer.database.operations.UserOperations.get_user_by_id",
            return_value=None,
        ):
            response = await authenticated_client.get(
                "/api/v1/billing/usage", headers=auth_headers
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND
            data = response.json()
            assert "User not found" in data["detail"]

    async def test_create_checkout_session_user_not_found(
        self, authenticated_client, auth_headers
    ):
        """Test checkout session creation with user not found."""
        request_data = {
            "plan": "basic",
            "success_url": "https://example.com/success",
            "cancel_url": "https://example.com/cancel",
        }

        with patch(
            "github_analyzer.database.operations.UserOperations.get_user_by_id",
            return_value=None,
        ):
            response = await authenticated_client.post(
                "/api/v1/billing/checkout-session",
                headers=auth_headers,
                json=request_data,
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND
            data = response.json()
            assert "User not found" in data["detail"]
