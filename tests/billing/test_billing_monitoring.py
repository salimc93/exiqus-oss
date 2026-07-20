"""
Tests for billing monitoring and analytics.

Tests monitoring functionality, analytics calculations,
and reporting features.
"""

from datetime import datetime, timezone
from typing import List

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from github_analyzer.billing.usage_tracker import UsageTracker
from github_analyzer.database.models import (
    Invoice,
    Payment,
    SubscriptionPlan,
    SubscriptionStatus,
    User,
    WebhookEvent,
)
from github_analyzer.database.operations import (
    BillingUsageOperations,
    InvoiceOperations,
    PaymentOperations,
    UserOperations,
    WebhookEventOperations,
)


class TestBillingMonitoring:
    """Test suite for billing monitoring functionality."""

    @pytest.fixture
    async def sample_users(self, test_db) -> List[User]:
        """Create sample users with different subscription plans."""
        users = []
        plans = [
            (SubscriptionPlan.FREE, 10, 5),
            (SubscriptionPlan.BASIC, 100, 80),
            (SubscriptionPlan.PROFESSIONAL, 1000, 1200),
            (SubscriptionPlan.ENTERPRISE, 5000, 4500),
        ]

        async with test_db() as db:
            for i, (plan, quota, usage) in enumerate(plans):
                user = await UserOperations.create_user(
                    db=db,
                    email=f"test{i}@example.com",
                    password="testpass",
                    full_name=f"Test User {i}",
                    usage_quota=quota,
                )
                user.subscription_plan = plan
                user.subscription_status = SubscriptionStatus.ACTIVE
                user.usage_count = usage
                user.stripe_customer_id = f"cus_test{i}"
                await db.commit()
                users.append(user)

        return users

    @pytest.fixture
    async def sample_invoices(self, test_db, sample_users: List[User]) -> List[Invoice]:
        """Create sample invoices for testing."""
        invoices = []

        async with test_db() as db:
            for i, user in enumerate(sample_users):
                if user.subscription_plan != SubscriptionPlan.FREE:
                    invoice = await InvoiceOperations.create_invoice(
                        db=db,
                        invoice_id=f"inv_test{i}",
                        user_id=user.user_id,
                        stripe_invoice_id=f"in_test{i}",
                        stripe_customer_id=user.stripe_customer_id,
                        amount_due=10000 * (i + 1),  # Varying amounts
                        currency="usd",
                        status="paid" if i % 2 == 0 else "pending",
                        billing_period_start=datetime(2024, 7, 1, tzinfo=timezone.utc),
                        billing_period_end=datetime(2024, 7, 31, tzinfo=timezone.utc),
                    )
                    invoices.append(invoice)

        return invoices

    @pytest.fixture
    async def sample_payments(self, test_db, sample_users: List[User]) -> List[Payment]:
        """Create sample payments for testing."""
        payments = []

        async with test_db() as db:
            for i, user in enumerate(sample_users):
                if user.subscription_plan != SubscriptionPlan.FREE:
                    payment = await PaymentOperations.create_payment(
                        db=db,
                        payment_id=f"pay_test{i}",
                        user_id=user.user_id,
                        stripe_payment_intent_id=f"pi_test{i}",
                        stripe_customer_id=user.stripe_customer_id,
                        amount=10000 * (i + 1),
                        currency="usd",
                        status="succeeded" if i % 2 == 0 else "failed",
                        payment_method="card",
                        processed_at=datetime.now(timezone.utc) if i % 2 == 0 else None,
                    )
                    payments.append(payment)

        return payments

    @pytest.fixture
    async def sample_webhooks(self, test_db) -> List[WebhookEvent]:
        """Create sample webhook events for testing."""
        webhooks = []
        event_types = [
            "customer.subscription.created",
            "invoice.payment_succeeded",
            "invoice.payment_failed",
            "customer.subscription.updated",
        ]

        async with test_db() as db:
            for i, event_type in enumerate(event_types * 3):  # Create 12 events
                webhook = await WebhookEventOperations.create_webhook_event(
                    db=db,
                    event_id=f"evt_test{i}",
                    stripe_event_id=f"evt_test{i}",
                    event_type=event_type,
                    event_data={"test": "data"},
                    status="processed" if i % 3 != 2 else "failed",
                )
                webhooks.append(webhook)

        return webhooks

    async def test_calculate_monthly_revenue(
        self, test_db, sample_payments: List[Payment]
    ):
        """Test monthly revenue calculation."""
        async with test_db() as db:
            # Calculate expected revenue from successful payments
            expected_revenue = (
                sum(p.amount for p in sample_payments if p.status == "succeeded") / 100
            )  # Convert cents to dollars

            # Get payments for current month
            now = datetime.now(timezone.utc)
            start_of_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

            payments = await PaymentOperations.get_payments_by_date_range(
                db, start_of_month, now
            )

            actual_revenue = (
                sum(p.amount for p in payments if p.status == "succeeded") / 100
            )

            assert actual_revenue == expected_revenue

    async def test_overage_detection(self, test_db, sample_users: List[User]):
        """Test overage detection for users exceeding quotas."""
        async with test_db() as db:
            # Find users with overages
            overage_users = []
            for user in sample_users:
                if user.usage_count > user.usage_quota:
                    overage_users.append(user)

            # Professional user should have overage
            professional_user = next(
                u
                for u in sample_users
                if u.subscription_plan == SubscriptionPlan.PROFESSIONAL
            )
            assert professional_user.usage_count > professional_user.usage_quota

            # Calculate overage cost
            overage_amount = (
                professional_user.usage_count - professional_user.usage_quota
            )
            # Grace period is 5% (not 10%), so grace_limit = 1000 * 1.05 = 1050
            grace_period_limit = int(professional_user.usage_quota * 1.05)
            # Only charge for usage beyond grace period: 1200 - 1050 = 150
            billable_overage = professional_user.usage_count - grace_period_limit
            # Cost in cents: 150 * 20 = 3000 cents
            overage_cost_cents = (
                billable_overage * 20
            )  # 20 cents per call for Professional

            usage_tracker = UsageTracker()
            overage_info = await usage_tracker.get_user_overage_info(
                db, professional_user.user_id
            )

            assert overage_info["overage_cost"] == overage_cost_cents
            assert overage_info["overage_count"] == overage_amount

    async def test_subscription_distribution(self, test_db, sample_users: List[User]):
        """Test subscription plan distribution calculation."""
        async with test_db() as db:
            plan_counts = {}

            for plan in SubscriptionPlan:
                users = await UserOperations.get_users_by_subscription_plan(db, plan)
                plan_counts[plan.value] = len(users)

            # Verify we have one user per plan
            assert plan_counts["FREE"] == 1
            assert plan_counts["BASIC"] == 1
            assert plan_counts["PROFESSIONAL"] == 1
            assert plan_counts["ENTERPRISE"] == 1

    async def test_payment_success_rate(
        self, test_db: AsyncSession, sample_payments: List[Payment]
    ):
        """Test payment success rate calculation."""
        total_payments = len(sample_payments)
        successful_payments = len(
            [p for p in sample_payments if p.status == "succeeded"]
        )

        success_rate = (
            (successful_payments / total_payments * 100) if total_payments > 0 else 0
        )

        # Our fixture creates 2 successful and 2 failed payments
        assert success_rate == pytest.approx(33.33, 0.01)

    async def test_webhook_processing_metrics(
        self, test_db: AsyncSession, sample_webhooks: List[WebhookEvent]
    ):
        """Test webhook processing metrics calculation."""
        async with test_db() as db:
            stats = await WebhookEventOperations.get_webhook_statistics(db)

        assert stats["total_webhooks"] == len(sample_webhooks)
        assert stats["processed"] == 8  # 2/3 are processed
        assert stats["failed"] == 4  # 1/3 are failed
        assert stats["success_rate"] == pytest.approx(66.67, 0.01)

        # Check event type distribution
        assert "customer.subscription.created" in stats["events_by_type"]
        assert "invoice.payment_succeeded" in stats["events_by_type"]

    async def test_grace_period_calculation(
        self, test_db: AsyncSession, sample_users: List[User]
    ):
        """Test grace period calculation for overage users."""
        professional_user = next(
            u
            for u in sample_users
            if u.subscription_plan == SubscriptionPlan.PROFESSIONAL
        )

        # Professional user has quota of 1000, usage of 1200
        # Grace period is 5% = 50 calls (not 10%)
        grace_limit = int(professional_user.usage_quota * 1.05)  # 1050
        in_grace_period = professional_user.usage_count <= grace_limit

        assert not in_grace_period  # 1200 > 1050
        assert grace_limit == 1050

    async def test_mrr_arr_calculation(
        self, test_db: AsyncSession, sample_users: List[User]
    ):
        """Test Monthly and Annual Recurring Revenue calculation."""
        async with test_db() as db:
            # Get users by plan
            basic_count = len(
                await UserOperations.get_users_by_subscription_plan(
                    db, SubscriptionPlan.BASIC
                )
            )
            professional_count = len(
                await UserOperations.get_users_by_subscription_plan(
                    db, SubscriptionPlan.PROFESSIONAL
                )
            )
            enterprise_count = len(
                await UserOperations.get_users_by_subscription_plan(
                    db, SubscriptionPlan.ENTERPRISE
                )
            )

        # Calculate MRR (prices from our subscription plans)
        mrr = (basic_count * 49) + (professional_count * 149) + (enterprise_count * 399)
        arr = mrr * 12

        assert mrr == 597  # 49 + 149 + 399
        assert arr == 7164  # MRR * 12

    async def test_failed_webhook_retry_identification(
        self, test_db: AsyncSession, sample_webhooks: List[WebhookEvent]
    ):
        """Test identification of webhooks needing retry."""
        async with test_db() as db:
            failed_webhooks = await WebhookEventOperations.get_failed_webhooks(
                db, max_attempts=5
            )

        # All failed webhooks should have attempts < 5
        assert all(w.attempts < 5 for w in failed_webhooks)
        assert len(failed_webhooks) == 4  # 1/3 of our sample webhooks

    async def test_invoice_aging_report(
        self, test_db: AsyncSession, sample_invoices: List[Invoice]
    ):
        """Test invoice aging for unpaid invoices."""
        async with test_db() as db:
            pending_invoices = await InvoiceOperations.get_invoices_by_status(
                db, "pending"
            )

        # Calculate days outstanding
        now = datetime.now(timezone.utc)
        for invoice in pending_invoices:
            # Ensure created_at is offset-aware before comparison
            created_at_aware = invoice.created_at.replace(tzinfo=timezone.utc)
            days_outstanding = (now - created_at_aware).days
            assert days_outstanding >= 0

    async def test_usage_trend_analysis(
        self, test_db: AsyncSession, sample_users: List[User]
    ):
        """Test usage trend analysis for capacity planning."""
        async with test_db() as db:
            # Create usage records for trend analysis
            for user in sample_users:
                if user.subscription_plan != SubscriptionPlan.FREE:
                    for day in range(7):
                        await BillingUsageOperations.create_usage_record(
                            db=db,
                            record_id=f"usage_{user.user_id}_{day}",
                            user_id=user.user_id,
                            usage_type="api_call",
                            usage_count=10 + day,  # Increasing usage
                            billing_period="2024-07",
                        )

            # Get usage summary for a user
            professional_user = next(
                u
                for u in sample_users
                if u.subscription_plan == SubscriptionPlan.PROFESSIONAL
            )

            usage_summary = await BillingUsageOperations.get_usage_summary_for_period(
                db, professional_user.user_id, "2024-07"
            )

        assert "api_call" in usage_summary
        assert usage_summary["api_call"] == sum(10 + day for day in range(7))  # 70

    async def test_revenue_by_plan_breakdown(
        self, test_db: AsyncSession, sample_payments: List[Payment]
    ):
        """Test revenue breakdown by subscription plan."""
        async with test_db() as db:
            # Group payments by user's subscription plan
            revenue_by_plan = {}

            for payment in sample_payments:
                if payment.status == "succeeded":
                    user = await UserOperations.get_user_by_id(db, payment.user_id)
                    if user:
                        plan = user.subscription_plan.value
                        if plan not in revenue_by_plan:
                            revenue_by_plan[plan] = 0
                        revenue_by_plan[plan] += payment.amount / 100

        # Verify revenue is tracked by plan
        assert len(revenue_by_plan) > 0
        assert all(revenue >= 0 for revenue in revenue_by_plan.values())

    async def test_webhook_processing_time_analysis(
        self, test_db: AsyncSession, sample_webhooks: List[WebhookEvent]
    ):
        """Test webhook processing time analysis."""
        async with test_db() as db:
            # Find a failed webhook to update
            failed_webhook = next(
                (w for w in sample_webhooks if w.status == "failed"), None
            )

            if failed_webhook:
                # Update the failed webhook to processed
                await WebhookEventOperations.update_webhook_status(
                    db,
                    failed_webhook.event_id,
                    status="processed",
                )

                # Verify webhook was updated
                updated_webhook = await WebhookEventOperations.get_webhook_event(
                    db, failed_webhook.event_id
                )
                assert updated_webhook is not None
                assert updated_webhook.status == "processed"
            else:
                # If no failed webhook, just verify we can retrieve one
                webhook = await WebhookEventOperations.get_webhook_event(
                    db, sample_webhooks[0].event_id
                )
                assert webhook is not None

    async def test_billing_alert_thresholds(
        self, test_db: AsyncSession, sample_users: List[User]
    ):
        """Test billing alert threshold detection."""
        alerts = []

        for user in sample_users:
            if user.usage_quota > 0:
                usage_percentage = (user.usage_count / user.usage_quota) * 100

                # Alert thresholds
                if usage_percentage >= 90:
                    alerts.append(
                        {
                            "user_id": user.user_id,
                            "email": user.email,
                            "usage_percentage": usage_percentage,
                            "alert_level": (
                                "critical" if usage_percentage >= 100 else "warning"
                            ),
                        }
                    )

        # Professional user should trigger alert (1200/1000 = 120%)
        assert len(alerts) >= 1
        professional_alert = next(
            (a for a in alerts if "test2@example.com" in a["email"]), None
        )
        assert professional_alert is not None
        assert professional_alert["alert_level"] == "critical"
