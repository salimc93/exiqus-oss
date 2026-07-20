"""
Tests for subscription renewal and auto-renewal functionality.

This module tests that subscription dates are properly updated on renewals
and that the system correctly handles the subscription lifecycle.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.github_analyzer.billing.webhook_handlers import WebhookHandlers
from src.github_analyzer.database.models import (
    SubscriptionPlan,
    SubscriptionStatus,
    User,
)


@pytest.fixture
def webhook_handlers():
    """Create webhook handlers instance."""
    return WebhookHandlers()


@pytest.fixture
def mock_user():
    """Create a mock user with subscription."""
    user = MagicMock(spec=User)
    user.user_id = "usr_test123"
    user.email = "test@example.com"
    user.stripe_customer_id = "cus_test123"
    user.stripe_subscription_id = "sub_test123"
    user.subscription_plan = SubscriptionPlan.PROFESSIONAL
    user.subscription_status = SubscriptionStatus.ACTIVE
    user.subscription_start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
    user.subscription_end_date = datetime(2024, 2, 1, tzinfo=timezone.utc)
    return user


@pytest.fixture
def initial_invoice_payment_event():
    """Create an initial invoice payment event (first payment)."""
    return {
        "id": "evt_test_initial",
        "type": "invoice.payment_succeeded",
        "data": {
            "object": {
                "id": "in_test_initial",
                "customer": "cus_test123",
                "subscription": "sub_test123",
                "amount_due": 19900,  # $199.00
                "amount_paid": 19900,
                "currency": "usd",
                "period_start": int(
                    datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp()
                ),
                "period_end": int(
                    datetime(2024, 2, 1, tzinfo=timezone.utc).timestamp()
                ),
                "lines": {
                    "data": [
                        {
                            "type": "subscription",
                            "amount": 19900,
                            "period": {
                                "start": int(
                                    datetime(
                                        2024, 1, 1, tzinfo=timezone.utc
                                    ).timestamp()
                                ),
                                "end": int(
                                    datetime(
                                        2024, 2, 1, tzinfo=timezone.utc
                                    ).timestamp()
                                ),
                            },
                        }
                    ]
                },
                "payment_intent": "pi_test_initial",
                "status_transitions": {
                    "paid_at": int(
                        datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc).timestamp()
                    )
                },
            }
        },
    }


@pytest.fixture
def renewal_invoice_payment_event():
    """Create a renewal invoice payment event (monthly renewal)."""
    return {
        "id": "evt_test_renewal",
        "type": "invoice.payment_succeeded",
        "data": {
            "object": {
                "id": "in_test_renewal",
                "customer": "cus_test123",
                "subscription": "sub_test123",
                "amount_due": 19900,  # $199.00
                "amount_paid": 19900,
                "currency": "usd",
                "period_start": int(
                    datetime(2024, 2, 1, tzinfo=timezone.utc).timestamp()
                ),
                "period_end": int(
                    datetime(2024, 3, 1, tzinfo=timezone.utc).timestamp()
                ),
                "lines": {
                    "data": [
                        {
                            "type": "subscription",
                            "amount": 19900,
                            "period": {
                                "start": int(
                                    datetime(
                                        2024, 2, 1, tzinfo=timezone.utc
                                    ).timestamp()
                                ),
                                "end": int(
                                    datetime(
                                        2024, 3, 1, tzinfo=timezone.utc
                                    ).timestamp()
                                ),
                            },
                        }
                    ]
                },
                "payment_intent": "pi_test_renewal",
                "status_transitions": {
                    "paid_at": int(
                        datetime(2024, 2, 1, 12, 0, tzinfo=timezone.utc).timestamp()
                    )
                },
            }
        },
    }


@pytest.mark.asyncio
async def test_initial_subscription_payment_sets_dates(
    webhook_handlers, mock_user, initial_invoice_payment_event
):
    """Test that initial subscription payment sets the period dates correctly."""
    db = AsyncMock(spec=AsyncSession)

    # Mock the price mapping to recognize our test price IDs
    with patch.object(
        webhook_handlers,
        "_map_price_to_plan",
        return_value=SubscriptionPlan.PROFESSIONAL,
    ):
        with patch(
            "src.github_analyzer.billing.webhook_handlers.UserOperations"
        ) as mock_user_ops:
            with patch(
                "src.github_analyzer.billing.webhook_handlers.InvoiceOperations"
            ) as mock_invoice_ops:
                with patch(
                    "src.github_analyzer.billing.webhook_handlers.PaymentOperations"
                ) as mock_payment_ops:
                    # Setup mocks
                    mock_user_ops.get_user_by_stripe_customer_id = AsyncMock(
                        return_value=mock_user
                    )
                    mock_user_ops.update_user_subscription = AsyncMock()

                    mock_invoice_ops.get_invoice_by_stripe_id = AsyncMock(
                        return_value=None
                    )

                    # Create a proper mock invoice object
                    mock_invoice = MagicMock()
                    mock_invoice.invoice_id = "inv_test_initial"
                    mock_invoice_ops.create_invoice = AsyncMock(
                        return_value=mock_invoice
                    )

                    # Mock payment operations
                    mock_payment_ops.create_payment = AsyncMock()

                    # Mock the Stripe client
                    webhook_handlers.stripe_client.get_subscription = AsyncMock(
                        return_value={
                            "id": "sub_test123",
                            "items": {
                                "data": [
                                    {
                                        "price": {
                                            "id": "mock_price_professional"  # Mocked Professional plan
                                        }
                                    }
                                ]
                            },
                            "current_period_start": int(
                                datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp()
                            ),
                            "current_period_end": int(
                                datetime(2024, 2, 1, tzinfo=timezone.utc).timestamp()
                            ),
                            "status": "active",
                        }
                    )

                    # Process the event
                    result = await webhook_handlers.handle_invoice_payment_succeeded(
                        db, initial_invoice_payment_event
                    )

                    # Verify the dates were updated
                    assert mock_user_ops.update_user_subscription.call_count >= 1

                    # Check that dates were set correctly
                    call_args_list = (
                        mock_user_ops.update_user_subscription.call_args_list
                    )
                    date_update_call = None
                    for call in call_args_list:
                        if "subscription_start_date" in call.kwargs:
                            date_update_call = call
                            break

                    assert date_update_call is not None
                    assert date_update_call.kwargs[
                        "subscription_start_date"
                    ] == datetime(2024, 1, 1, tzinfo=timezone.utc)
                    assert date_update_call.kwargs["subscription_end_date"] == datetime(
                        2024, 2, 1, tzinfo=timezone.utc
                    )

                    # Verify result
                    assert result["status"] == "processed"
                    assert result["action"] == "created"


@pytest.mark.asyncio
async def test_renewal_payment_updates_dates(
    webhook_handlers, mock_user, renewal_invoice_payment_event
):
    """Test that renewal payments update the subscription period dates."""
    db = AsyncMock(spec=AsyncSession)

    # Create a mock existing invoice to simulate a renewal
    existing_invoice = MagicMock()
    existing_invoice.invoice_id = "inv_existing"

    with patch(
        "src.github_analyzer.billing.webhook_handlers.UserOperations"
    ) as mock_user_ops:
        with patch(
            "src.github_analyzer.billing.webhook_handlers.InvoiceOperations"
        ) as mock_invoice_ops:
            # Setup mocks
            mock_user_ops.get_user_by_stripe_customer_id = AsyncMock(
                return_value=mock_user
            )
            mock_user_ops.update_user_subscription = AsyncMock()
            mock_invoice_ops.get_invoice_by_stripe_id = AsyncMock(
                return_value=existing_invoice
            )
            mock_invoice_ops.update_invoice_status = AsyncMock()

            # Process the renewal event
            result = await webhook_handlers.handle_invoice_payment_succeeded(
                db, renewal_invoice_payment_event
            )

            # Verify the dates were updated for the renewal
            mock_user_ops.update_user_subscription.assert_called_with(
                db,
                mock_user.user_id,
                subscription_start_date=datetime(2024, 2, 1, tzinfo=timezone.utc),
                subscription_end_date=datetime(2024, 3, 1, tzinfo=timezone.utc),
            )

            # Verify result
            assert result["status"] == "processed"
            assert result["action"] == "updated"
            assert result["invoice_id"] == existing_invoice.invoice_id


@pytest.mark.asyncio
async def test_multiple_renewals_keep_dates_current(webhook_handlers, mock_user):
    """Test that multiple renewals keep updating dates to stay current."""
    db = AsyncMock(spec=AsyncSession)

    # Simulate 3 months of renewals
    renewal_months = [
        (2, 3),  # February to March
        (3, 4),  # March to April
        (4, 5),  # April to May
    ]

    with patch(
        "src.github_analyzer.billing.webhook_handlers.UserOperations"
    ) as mock_user_ops:
        with patch(
            "src.github_analyzer.billing.webhook_handlers.InvoiceOperations"
        ) as mock_invoice_ops:
            mock_user_ops.get_user_by_stripe_customer_id = AsyncMock(
                return_value=mock_user
            )
            mock_user_ops.update_user_subscription = AsyncMock()
            mock_invoice_ops.update_invoice_status = AsyncMock()

            for start_month, end_month in renewal_months:
                # Create renewal event for this month
                renewal_event = {
                    "id": f"evt_test_month_{start_month}",
                    "type": "invoice.payment_succeeded",
                    "data": {
                        "object": {
                            "id": f"in_test_month_{start_month}",
                            "customer": "cus_test123",
                            "subscription": "sub_test123",
                            "amount_due": 34900,
                            "amount_paid": 34900,
                            "currency": "usd",
                            "period_start": int(
                                datetime(
                                    2024, start_month, 1, tzinfo=timezone.utc
                                ).timestamp()
                            ),
                            "period_end": int(
                                datetime(
                                    2024, end_month, 1, tzinfo=timezone.utc
                                ).timestamp()
                            ),
                            "status_transitions": {
                                "paid_at": int(
                                    datetime(
                                        2024, start_month, 1, 12, 0, tzinfo=timezone.utc
                                    ).timestamp()
                                )
                            },
                        }
                    },
                }

                # Return existing invoice to simulate renewal
                existing_invoice = MagicMock()
                existing_invoice.invoice_id = f"inv_month_{start_month}"
                mock_invoice_ops.get_invoice_by_stripe_id = AsyncMock(
                    return_value=existing_invoice
                )

                # Process the renewal
                await webhook_handlers.handle_invoice_payment_succeeded(
                    db, renewal_event
                )

                # Verify dates were updated to this month's period
                mock_user_ops.update_user_subscription.assert_called_with(
                    db,
                    mock_user.user_id,
                    subscription_start_date=datetime(
                        2024, start_month, 1, tzinfo=timezone.utc
                    ),
                    subscription_end_date=datetime(
                        2024, end_month, 1, tzinfo=timezone.utc
                    ),
                )

            # Verify we processed all 3 renewals
            assert mock_user_ops.update_user_subscription.call_count == 3


@pytest.mark.asyncio
async def test_subscription_cancellation_sets_end_date(webhook_handlers, mock_user):
    """Test that subscription cancellation properly sets the end date."""
    db = AsyncMock(spec=AsyncSession)

    cancellation_event = {
        "id": "evt_test_cancel",
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": "sub_test123",
                "customer": "cus_test123",
                "status": "canceled",
                "canceled_at": int(
                    datetime(2024, 2, 15, tzinfo=timezone.utc).timestamp()
                ),
                "ended_at": int(datetime(2024, 2, 15, tzinfo=timezone.utc).timestamp()),
            }
        },
    }

    with patch(
        "src.github_analyzer.billing.webhook_handlers.UserOperations"
    ) as mock_user_ops:
        mock_user_ops.get_user_by_stripe_subscription_id = AsyncMock(
            return_value=mock_user
        )
        mock_user_ops.update_user_subscription = AsyncMock()

        # Process cancellation
        result = await webhook_handlers.handle_customer_subscription_deleted(
            db, cancellation_event
        )

        # Verify subscription was downgraded and end date set
        update_call = mock_user_ops.update_user_subscription.call_args
        assert update_call.kwargs["subscription_plan"] == SubscriptionPlan.FREE
        assert update_call.kwargs["subscription_status"] == SubscriptionStatus.CANCELED
        assert update_call.kwargs["subscription_end_date"] is not None
        assert update_call.kwargs["stripe_subscription_id"] is None

        # Verify result
        assert result["status"] == "processed"
        assert result["downgraded_to"] == "free"


@pytest.mark.asyncio
async def test_zero_amount_invoices_ignored(webhook_handlers):
    """Test that $0 invoices (TEST mode setup) are ignored."""
    db = AsyncMock(spec=AsyncSession)

    zero_invoice_event = {
        "id": "evt_test_zero",
        "type": "invoice.payment_succeeded",
        "data": {
            "object": {
                "id": "in_test_zero",
                "customer": "cus_test123",
                "subscription": "sub_test123",
                "amount_due": 0,
                "amount_paid": 0,
                "currency": "usd",
            }
        },
    }

    result = await webhook_handlers.handle_invoice_payment_succeeded(
        db, zero_invoice_event
    )

    assert result["status"] == "ignored"
    assert "Zero amount invoice" in result["reason"]


@pytest.mark.asyncio
async def test_subscription_updated_event_refreshes_dates(webhook_handlers, mock_user):
    """Test that subscription.updated events also refresh dates."""
    db = AsyncMock(spec=AsyncSession)

    update_event = {
        "id": "evt_test_update",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_test123",
                "customer": "cus_test123",
                "status": "active",
                "current_period_start": int(
                    datetime(2024, 3, 1, tzinfo=timezone.utc).timestamp()
                ),
                "current_period_end": int(
                    datetime(2024, 4, 1, tzinfo=timezone.utc).timestamp()
                ),
                "items": {"data": [{"price": {"id": "mock_price_professional"}}]},
            }
        },
    }

    with patch(
        "src.github_analyzer.billing.webhook_handlers.UserOperations"
    ) as mock_user_ops:
        mock_user_ops.get_user_by_stripe_subscription_id = AsyncMock(
            return_value=mock_user
        )
        mock_user_ops.update_user_subscription = AsyncMock()

        # Process update event
        result = await webhook_handlers.handle_customer_subscription_updated(
            db, update_event
        )

        # Verify dates were updated
        update_call = mock_user_ops.update_user_subscription.call_args
        assert update_call.kwargs["subscription_start_date"] == datetime(
            2024, 3, 1, tzinfo=timezone.utc
        )
        assert update_call.kwargs["subscription_end_date"] == datetime(
            2024, 4, 1, tzinfo=timezone.utc
        )

        assert result["status"] == "processed"
