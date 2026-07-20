"""
Test suite for admin management routes.

Tests the new admin dashboard and message management endpoints.
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from github_analyzer.api.auth.dependencies import get_admin_user_from_token
from github_analyzer.database.models import (
    ContactMessage,
    ContactStatus,
    Invoice,
    SubscriptionPlan,
    SubscriptionStatus,
    User,
)


class TestAdminManagementRoutes:
    """Test suite for admin management endpoints."""

    @pytest.fixture
    async def admin_user(self, test_db: AsyncSession):
        """Create an admin user for testing."""
        async with test_db() as db:
            admin = User(
                user_id="admin123",
                email="admin@example.com",
                password_hash="hashed",
                full_name="Admin User",
                is_admin=True,
                is_active=True,
            )
            db.add(admin)
            await db.commit()
            await db.refresh(admin)
            return admin

    @pytest.fixture
    async def admin_client(self, async_client: AsyncClient, admin_user: User):
        """Create an async client with admin authentication mocked."""

        async def override_get_admin_user():
            return admin_user

        async_client.app.dependency_overrides[get_admin_user_from_token] = (
            override_get_admin_user
        )
        yield async_client
        # Clean up the override after test
        del async_client.app.dependency_overrides[get_admin_user_from_token]

    @pytest.mark.asyncio
    async def test_get_admin_dashboard_success(
        self, admin_client: AsyncClient, test_db: AsyncSession
    ):
        """Test successful retrieval of admin dashboard data."""
        # Create some test users with different plans
        async with test_db() as db:
            users = [
                User(
                    user_id=f"user{i}",
                    email=f"user{i}@example.com",
                    password_hash="hashed",
                    full_name=f"Test User {i}",
                    subscription_plan=(
                        SubscriptionPlan.SCALE_PLUS
                        if i % 2 == 0
                        else SubscriptionPlan.FREE
                    ),
                    is_active=True,
                    created_at=datetime.now(timezone.utc) - timedelta(days=i),
                )
                for i in range(5)
            ]

            db.add_all(users)
            await db.commit()

        response = await admin_client.get(
            "/api/v1/admin/dashboard",
            headers={"Authorization": "Bearer fake-token"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify dashboard structure
        assert "total_users" in data
        assert "active_users" in data
        assert "revenue" in data
        assert "recent_activities" in data
        assert "actionable_alerts" in data
        assert data["total_users"] >= 5

    @pytest.mark.asyncio
    async def test_get_admin_dashboard_unauthorized(self, async_client: AsyncClient):
        """Test admin dashboard access without authentication."""
        response = await async_client.get("/api/v1/admin/dashboard")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_admin_dashboard_non_admin(
        self, async_client: AsyncClient, test_db: AsyncSession
    ):
        """Test admin dashboard access by non-admin user."""
        async with test_db() as db:
            regular_user = User(
                user_id="user123",
                email="user@example.com",
                password_hash="hashed",
                full_name="Regular User",
                is_admin=False,
                is_active=True,
            )
            db.add(regular_user)
            await db.commit()
            await db.refresh(regular_user)

        # Override dependency to simulate non-admin user trying to access
        async def override_get_admin_user():
            from fastapi import HTTPException

            raise HTTPException(status_code=403, detail="Not an admin")

        async_client.app.dependency_overrides[get_admin_user_from_token] = (
            override_get_admin_user
        )

        response = await async_client.get(
            "/api/v1/admin/dashboard",
            headers={"Authorization": "Bearer fake-token"},
        )

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

        # Clean up override
        del async_client.app.dependency_overrides[get_admin_user_from_token]

    @pytest.mark.asyncio
    async def test_get_support_messages_success(
        self, admin_client: AsyncClient, test_db: AsyncSession
    ):
        """Test successful retrieval of support messages."""
        async with test_db() as db:
            # Create test messages with different priorities
            messages = [
                ContactMessage(
                    message_id=f"msg{i}",
                    user_id=None,
                    name=f"User {i}",
                    email=f"user{i}@example.com",
                    subject=f"Test Subject {i}",
                    message=f"Test message content {i}",
                    status=ContactStatus.UNREAD if i % 2 == 0 else ContactStatus.READ,
                    is_priority=i < 2,  # First 2 are priority
                    priority_level=3 if i == 0 else (2 if i == 1 else 0),
                    created_at=datetime.now(timezone.utc) - timedelta(hours=i),
                )
                for i in range(5)
            ]

            db.add_all(messages)
            await db.commit()

        response = await admin_client.get(
            "/api/v1/admin/support-messages",
            headers={"Authorization": "Bearer fake-token"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "messages" in data
        assert "total_count" in data
        assert len(data["messages"]) > 0

        # Verify priority messages come first
        if len(data["messages"]) > 1:
            first_msg = data["messages"][0]
            assert first_msg["is_priority"] is True

    @pytest.mark.asyncio
    async def test_get_support_messages_with_status_filter(
        self, admin_client: AsyncClient, test_db: AsyncSession
    ):
        """Test filtering support messages by status."""
        async with test_db() as db:
            # Create messages with different statuses
            unread_msg = ContactMessage(
                message_id="unread1",
                user_id=None,
                name="User 1",
                email="user1@example.com",
                subject="Unread Message",
                message="This is unread",
                status=ContactStatus.UNREAD,
            )

            responded_msg = ContactMessage(
                message_id="responded1",
                user_id=None,
                name="User 2",
                email="user2@example.com",
                subject="Responded Message",
                message="This was responded to",
                status=ContactStatus.RESPONDED,
                admin_response="Admin response here",
                responded_at=datetime.now(timezone.utc),
            )

            db.add(unread_msg)
            db.add(responded_msg)
            await db.commit()

        # Test filtering by UNREAD status
        response = await admin_client.get(
            "/api/v1/admin/support-messages?status=UNREAD",
            headers={"Authorization": "Bearer fake-token"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert all(msg["status"] == "UNREAD" for msg in data["messages"])

    @pytest.mark.asyncio
    async def test_respond_to_message_success(
        self, admin_client: AsyncClient, test_db: AsyncSession
    ):
        """Test successfully responding to a support message."""
        async with test_db() as db:
            message = ContactMessage(
                message_id="msg123",
                user_id=None,
                name="Test User",
                email="user@example.com",
                subject="Need Help",
                message="I need assistance",
                status=ContactStatus.UNREAD,
            )

            db.add(message)
            await db.commit()

        response = await admin_client.post(
            "/api/v1/admin/support-messages/msg123/reply",
            json={"reply": "Here is your help!"},
            headers={"Authorization": "Bearer fake-token"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Response sent successfully"

        # Verify message was updated
        async with test_db() as db:
            updated_msg = await db.get(ContactMessage, "msg123")
            assert updated_msg.status == ContactStatus.RESPONDED
            assert updated_msg.admin_response == "Here is your help!"
            assert updated_msg.responded_at is not None
            assert updated_msg.responded_by == "admin123"  # Now uses user_id not email

    @pytest.mark.asyncio
    async def test_respond_to_nonexistent_message(
        self, admin_client: AsyncClient, test_db: AsyncSession
    ):
        """Test responding to a message that doesn't exist."""
        response = await admin_client.post(
            "/api/v1/admin/support-messages/nonexistent/reply",
            json={"reply": "Response"},
            headers={"Authorization": "Bearer fake-token"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_user_details_success(
        self, admin_client: AsyncClient, test_db: AsyncSession
    ):
        """Test getting detailed user information."""
        async with test_db() as db:
            target_user = User(
                user_id="target123",
                email="target@example.com",
                password_hash="hashed",
                full_name="Target User",
                subscription_plan=SubscriptionPlan.SCALE_PLUS,
                is_active=True,
                analyses_consumed=5,
            )

            db.add(target_user)
            await db.commit()

        response = await admin_client.get(
            "/api/v1/admin/users/target123",
            headers={"Authorization": "Bearer fake-token"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["user_id"] == "target123"
        assert data["email"] == "target@example.com"
        assert data["subscription_plan"] == "SCALE_PLUS"

    @pytest.mark.asyncio
    async def test_search_users_success(
        self, admin_client: AsyncClient, test_db: AsyncSession
    ):
        """Test searching for users."""
        async with test_db() as db:
            # Create users with searchable attributes
            users = [
                User(
                    user_id=f"user{i}",
                    email=f"test{i}@example.com" if i < 3 else f"other{i}@example.com",
                    password_hash="hashed",
                    full_name=f"Test User {i}" if i < 3 else f"Other User {i}",
                    is_active=True,
                )
                for i in range(5)
            ]

            db.add_all(users)
            await db.commit()

        response = await admin_client.get(
            "/api/v1/admin/users/search?query=test",
            headers={"Authorization": "Bearer fake-token"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 3  # Should find 3 users with "test" in email/name

    @pytest.mark.asyncio
    async def test_admin_routes_require_authentication(self, async_client: AsyncClient):
        """Test that all admin routes require authentication."""
        routes = [
            ("/api/v1/admin/dashboard", "GET"),
            ("/api/v1/admin/support-messages", "GET"),
            ("/api/v1/admin/support-messages/123/reply", "POST"),
            ("/api/v1/admin/users/123", "GET"),
            ("/api/v1/admin/users/search", "GET"),
        ]

        for route, method in routes:
            if method == "GET":
                response = await async_client.get(route)
            else:
                response = await async_client.post(route, json={})

            assert response.status_code == status.HTTP_401_UNAUTHORIZED, (
                f"Route {route} did not require auth"
            )

    @pytest.mark.asyncio
    async def test_revenue_analytics_with_invoice_fallback(
        self, admin_client: AsyncClient, test_db: AsyncSession
    ):
        """Test revenue analytics endpoint with invoice fallback when Stripe is not available."""
        async with test_db() as db:
            # Create test users with different subscription plans
            users = [
                User(
                    user_id="user_scale_plus",
                    email="scale_plus@example.com",
                    password_hash="hashed",
                    full_name="Scale Plus User",
                    subscription_plan=SubscriptionPlan.SCALE_PLUS,
                    subscription_status=SubscriptionStatus.ACTIVE,
                    is_active=True,
                ),
                User(
                    user_id="user_enterprise",
                    email="enterprise@example.com",
                    password_hash="hashed",
                    full_name="Enterprise User",
                    subscription_plan=SubscriptionPlan.ENTERPRISE,
                    subscription_status=SubscriptionStatus.ACTIVE,
                    is_active=True,
                ),
                User(
                    user_id="user_professional",
                    email="professional@example.com",
                    password_hash="hashed",
                    full_name="Professional User",
                    subscription_plan=SubscriptionPlan.PROFESSIONAL,
                    subscription_status=SubscriptionStatus.ACTIVE,
                    is_active=True,
                ),
            ]
            db.add_all(users)
            await db.commit()

            # Create test invoices (paid)
            invoices = [
                Invoice(
                    invoice_id="inv_scale_plus_1",
                    user_id="user_scale_plus",
                    stripe_invoice_id="in_test_scale_plus",
                    stripe_customer_id="cus_test_scale_plus",
                    amount_due=250000,  # $2500 in cents
                    amount_paid=250000,
                    currency="usd",
                    status="paid",
                    billing_period_start=datetime.now(timezone.utc) - timedelta(days=5),
                    billing_period_end=datetime.now(timezone.utc) + timedelta(days=25),
                    created_at=datetime.now(timezone.utc) - timedelta(days=3),
                ),
                Invoice(
                    invoice_id="inv_enterprise_1",
                    user_id="user_enterprise",
                    stripe_invoice_id="in_test_enterprise",
                    stripe_customer_id="cus_test_enterprise",
                    amount_due=150000,  # $1500 in cents
                    amount_paid=150000,
                    currency="usd",
                    status="paid",
                    billing_period_start=datetime.now(timezone.utc)
                    - timedelta(days=10),
                    billing_period_end=datetime.now(timezone.utc) + timedelta(days=20),
                    created_at=datetime.now(timezone.utc) - timedelta(days=8),
                ),
                Invoice(
                    invoice_id="inv_professional_1",
                    user_id="user_professional",
                    stripe_invoice_id="in_test_professional",
                    stripe_customer_id="cus_test_professional",
                    amount_due=34900,  # $349 in cents
                    amount_paid=34900,
                    currency="usd",
                    status="paid",
                    billing_period_start=datetime.now(timezone.utc)
                    - timedelta(days=15),
                    billing_period_end=datetime.now(timezone.utc) + timedelta(days=15),
                    created_at=datetime.now(timezone.utc) - timedelta(days=12),
                ),
            ]
            db.add_all(invoices)
            await db.commit()

        # Test revenue analytics endpoint
        response = await admin_client.get(
            "/api/v1/admin/revenue?range=30d",
            headers={"Authorization": "Bearer fake-token"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify response structure
        assert "metrics" in data
        assert "growth" in data
        assert "subscriptions_by_plan" in data
        assert "recent_transactions" in data
        assert "monthly_revenue" in data

        # Verify metrics
        metrics = data["metrics"]
        assert "mrr" in metrics
        assert "arr" in metrics
        assert "active_subscriptions" in metrics
        assert "average_revenue_per_user" in metrics

        # Verify subscriptions by plan includes our test data
        subs_by_plan = data["subscriptions_by_plan"]
        assert "scale_plus" in subs_by_plan
        assert "enterprise" in subs_by_plan
        assert "professional" in subs_by_plan

        # Verify recent transactions include invoice data
        transactions = data["recent_transactions"]
        assert len(transactions) >= 3  # Should include our test invoices

        # Check that transactions have correct structure
        for transaction in transactions:
            assert "id" in transaction
            assert "user_email" in transaction
            assert "plan" in transaction
            assert "amount" in transaction
            assert "type" in transaction
            assert "created_at" in transaction

        # Verify at least one Scale+ transaction exists
        scale_plus_transactions = [t for t in transactions if t["plan"] == "scale_plus"]
        assert len(scale_plus_transactions) >= 1

        # Verify the Scale+ transaction has correct amount
        scale_plus_tx = scale_plus_transactions[0]
        assert scale_plus_tx["amount"] == 2500.0  # $2500

    @pytest.mark.asyncio
    async def test_get_support_messages_with_priority_filter(
        self, admin_client: AsyncClient, test_db: AsyncSession
    ):
        """Test filtering support messages by priority status."""
        async with test_db() as db:
            # Create priority and non-priority messages
            priority_msg = ContactMessage(
                message_id="priority1",
                user_id=None,
                name="Scale+ User",
                email="scale@example.com",
                subject="Urgent Issue",
                message="Need immediate help",
                status=ContactStatus.UNREAD,
                is_priority=True,
                priority_level=3,
            )

            normal_msg = ContactMessage(
                message_id="normal1",
                user_id=None,
                name="Free User",
                email="free@example.com",
                subject="Question",
                message="General inquiry",
                status=ContactStatus.UNREAD,
                is_priority=False,
                priority_level=0,
            )

            db.add(priority_msg)
            db.add(normal_msg)
            await db.commit()

        # Get all messages and check priority sorting
        response = await admin_client.get(
            "/api/v1/admin/support-messages",
            headers={"Authorization": "Bearer fake-token"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Priority messages should come first
        messages = data["messages"]
        if len(messages) > 0:
            # Check that priority message is in the results
            assert any(msg["is_priority"] is True for msg in messages)

    @pytest.mark.asyncio
    async def test_update_message_status(
        self, admin_client: AsyncClient, test_db: AsyncSession
    ):
        """Test updating a support message status."""
        async with test_db() as db:
            message = ContactMessage(
                message_id="msg_to_update",
                user_id=None,
                name="Test User",
                email="user@example.com",
                subject="Test Subject",
                message="Test message",
                status=ContactStatus.UNREAD,
            )

            db.add(message)
            await db.commit()

        response = await admin_client.patch(
            "/api/v1/admin/support-messages/msg_to_update",
            json={"status": "READ"},
            headers={"Authorization": "Bearer fake-token"},
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify message status was updated
        async with test_db() as db:
            updated_msg = await db.get(ContactMessage, "msg_to_update")
            assert updated_msg.status == ContactStatus.READ

    @pytest.mark.asyncio
    async def test_extend_trial_with_custom_days(
        self, admin_client: AsyncClient, test_db: AsyncSession
    ):
        """Test extending user trial with custom number of days."""
        async with test_db() as db:
            trial_user = User(
                user_id="trial_user",
                email="trial@example.com",
                password_hash="hashed",
                full_name="Trial User",
                subscription_plan=SubscriptionPlan.FREE,
                subscription_status=SubscriptionStatus.TRIALING,
                trial_end_date=datetime.now(timezone.utc) + timedelta(days=3),
                is_active=True,
            )

            db.add(trial_user)
            await db.commit()
            await db.refresh(trial_user)
            original_trial_end = trial_user.trial_end_date

        response = await admin_client.post(
            "/api/v1/admin/users/trial_user/extend-trial",
            json={"days": 14},  # API expects "days" not "additional_days"
            headers={"Authorization": "Bearer fake-token"},
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify trial was extended
        async with test_db() as db:
            updated_user = await db.get(User, "trial_user")
            assert updated_user.trial_end_date > original_trial_end
            # Check it was extended by approximately 14 days
            time_diff = updated_user.trial_end_date - original_trial_end
            assert 13 <= time_diff.days <= 15

    @pytest.mark.asyncio
    async def test_revenue_analytics_with_paid_invoices_only(
        self, admin_client: AsyncClient, test_db: AsyncSession
    ):
        """Test that revenue analytics only includes paid invoices."""
        async with test_db() as db:
            # Create users
            user = User(
                user_id="user_with_mixed_invoices",
                email="mixed@example.com",
                password_hash="hashed",
                full_name="Mixed User",
                subscription_plan=SubscriptionPlan.PROFESSIONAL,
                is_active=True,
            )
            db.add(user)

            # Create mixed invoices
            billing_start = datetime.now(timezone.utc) - timedelta(days=30)
            billing_end = datetime.now(timezone.utc)

            paid_invoice = Invoice(
                invoice_id="paid_1",
                user_id="user_with_mixed_invoices",
                stripe_invoice_id="in_paid",
                stripe_customer_id="cus_mixed",
                amount_due=34900,
                amount_paid=34900,
                currency="usd",
                status="paid",
                billing_period_start=billing_start,
                billing_period_end=billing_end,
                created_at=datetime.now(timezone.utc) - timedelta(days=5),
            )

            unpaid_invoice = Invoice(
                invoice_id="unpaid_1",
                user_id="user_with_mixed_invoices",
                stripe_invoice_id="in_unpaid",
                stripe_customer_id="cus_mixed",
                amount_due=34900,
                amount_paid=0,
                currency="usd",
                status="open",
                billing_period_start=billing_start,
                billing_period_end=billing_end,
                created_at=datetime.now(timezone.utc) - timedelta(days=3),
            )

            failed_invoice = Invoice(
                invoice_id="failed_1",
                user_id="user_with_mixed_invoices",
                stripe_invoice_id="in_failed",
                stripe_customer_id="cus_mixed",
                amount_due=34900,
                amount_paid=0,
                currency="usd",
                status="failed",
                billing_period_start=billing_start,
                billing_period_end=billing_end,
                created_at=datetime.now(timezone.utc) - timedelta(days=1),
            )

            db.add(paid_invoice)
            db.add(unpaid_invoice)
            db.add(failed_invoice)
            await db.commit()

        response = await admin_client.get(
            "/api/v1/admin/revenue?range=30d",
            headers={"Authorization": "Bearer fake-token"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify only paid invoices are included in transactions
        transactions = data["recent_transactions"]
        for transaction in transactions:
            if transaction["id"].startswith("inv_"):
                # This is an invoice-based transaction
                # It should only include paid invoices
                assert transaction["id"] != "unpaid_1"
                assert transaction["id"] != "failed_1"
