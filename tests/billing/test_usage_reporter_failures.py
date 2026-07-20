"""
Test suite for usage reporter failure scenarios.

Tests data integrity, retry failures, and edge cases in
the usage reporting service.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from github_analyzer.billing.stripe_client import StripeClientError
from github_analyzer.billing.usage_reporter import (
    UsageReporter,
    UsageReportingError,
)
from github_analyzer.database.models import SubscriptionPlan


class TestUsageReporterFailures:
    """Test failure scenarios and edge cases in usage reporting."""

    @pytest.fixture
    def usage_reporter(self):
        """Create a UsageReporter instance with mocked Stripe client."""
        mock_stripe_client = MagicMock()
        return UsageReporter(stripe_client=mock_stripe_client)

    @pytest.fixture
    def mock_usage_records_mixed(self):
        """Create mock usage records with various scenarios."""
        records = []
        # Valid user records
        for i in range(3):
            record = MagicMock()
            record.record_id = f"usage_valid_{i}"
            record.user_id = "user_valid"
            record.usage_count = 10
            record.billing_period = "2025-01"
            record.created_at = datetime.now(timezone.utc)
            records.append(record)

        # Records for user without subscription
        for i in range(2):
            record = MagicMock()
            record.record_id = f"usage_nosub_{i}"
            record.user_id = "user_no_subscription"
            record.usage_count = 5
            record.billing_period = "2025-01"
            record.created_at = datetime.now(timezone.utc)
            records.append(record)

        # Records for non-existent user
        for i in range(2):
            record = MagicMock()
            record.record_id = f"usage_nonexist_{i}"
            record.user_id = "user_nonexistent"
            record.usage_count = 15
            record.billing_period = "2025-01"
            record.created_at = datetime.now(timezone.utc)
            records.append(record)

        return records

    async def test_report_all_unreported_usage_database_error(self, usage_reporter):
        """Test database error during unreported usage retrieval."""
        mock_db = MagicMock()

        with patch(
            "github_analyzer.database.operations.BillingUsageOperations.get_unreported_usage"
        ) as mock_get:
            mock_get.side_effect = Exception("Database connection lost")

            with pytest.raises(UsageReportingError) as exc_info:
                await usage_reporter.report_all_unreported_usage(mock_db)

            assert "Database connection lost" in str(exc_info.value)

    async def test_mixed_user_scenarios(self, usage_reporter, mock_usage_records_mixed):
        """Test handling of mixed user scenarios in one batch."""
        mock_db = MagicMock()

        # Create users with different scenarios
        user_valid = MagicMock()
        user_valid.user_id = "user_valid"
        user_valid.subscription_plan = SubscriptionPlan.PROFESSIONAL
        user_valid.stripe_subscription_id = "sub_valid"

        user_no_sub = MagicMock()
        user_no_sub.user_id = "user_no_subscription"
        user_no_sub.subscription_plan = SubscriptionPlan.PROFESSIONAL
        user_no_sub.stripe_subscription_id = None

        with patch(
            "github_analyzer.database.operations.BillingUsageOperations.get_unreported_usage"
        ) as mock_get_unreported:
            mock_get_unreported.return_value = mock_usage_records_mixed

            with patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_id",
                new_callable=AsyncMock,
            ) as mock_get_user:

                def get_user_side_effect(db, user_id):
                    if user_id == "user_valid":
                        return user_valid
                    elif user_id == "user_no_subscription":
                        return user_no_sub
                    return None  # Non-existent user

                mock_get_user.side_effect = get_user_side_effect

                # Mock successful Stripe operations for valid user
                usage_reporter.stripe_client.get_subscription_item_for_price = (
                    AsyncMock(return_value={"id": "si_valid"})
                )
                usage_reporter.stripe_client.create_usage_record = AsyncMock()

                with patch(
                    "github_analyzer.database.operations.BillingUsageOperations.mark_usage_reported_to_stripe"
                ) as mock_mark:
                    mock_mark.return_value = True

                    result = await usage_reporter.report_all_unreported_usage(mock_db)

                    # Should have partial success
                    assert result["success"] is False
                    assert result["records_processed"] == 7
                    assert result["records_reported"] == 3  # Only valid user's records
                    assert result["records_failed"] == 4  # No sub + non-existent
                    assert len(result["failed_records"]) == 4

    async def test_stripe_subscription_item_not_found(self, usage_reporter):
        """Test when subscription item for overage price is not found."""
        mock_db = MagicMock()
        user = MagicMock()
        user.user_id = "user123"
        user.subscription_plan = SubscriptionPlan.ENTERPRISE
        user.stripe_subscription_id = "sub_123"

        records = []
        for i in range(3):
            record = MagicMock()
            record.record_id = f"usage_{i}"
            record.user_id = "user123"
            record.usage_count = 10
            record.billing_period = "2025-01"
            record.created_at = datetime.now(timezone.utc)
            records.append(record)

        # Mock subscription item not found
        usage_reporter.stripe_client.get_subscription_item_for_price = AsyncMock(
            return_value=None
        )

        result = await usage_reporter._report_user_usage_batch(mock_db, user, records)

        assert result["processed"] == 3
        assert result["reported"] == 0
        assert result["failed"] == 3
        assert len(result["failed_records"]) == 3

    async def test_retry_logic_exhaustion(self, usage_reporter):
        """Test when all retry attempts fail."""
        mock_db = MagicMock()
        user = MagicMock()
        user.user_id = "user123"
        user.subscription_plan = SubscriptionPlan.PROFESSIONAL
        user.stripe_subscription_id = "sub_123"

        # Create a record
        record = MagicMock()
        record.record_id = "usage_1"
        record.user_id = "user123"
        record.usage_count = 100
        record.billing_period = "2025-01"
        record.created_at = datetime.now(timezone.utc)

        # Mock subscription item found
        usage_reporter.stripe_client.get_subscription_item_for_price = AsyncMock(
            return_value={"id": "si_123"}
        )

        # Mock all retry attempts failing
        usage_reporter.stripe_client.create_usage_record = AsyncMock(
            side_effect=StripeClientError("Rate limit exceeded")
        )

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await usage_reporter._report_user_usage_batch(
                mock_db, user, [record]
            )

            assert result["processed"] == 1
            assert result["reported"] == 0
            assert result["failed"] == 1
            assert usage_reporter.stripe_client.create_usage_record.call_count == 3

    async def test_partial_period_failure(self, usage_reporter):
        """Test when some billing periods succeed and others fail."""
        mock_db = MagicMock()
        user = MagicMock()
        user.user_id = "user123"
        user.subscription_plan = SubscriptionPlan.ENTERPRISE
        user.stripe_subscription_id = "sub_123"

        # Create records for multiple periods
        records = []
        for period in ["2025-01", "2025-02"]:
            for i in range(2):
                record = MagicMock()
                record.record_id = f"usage_{period}_{i}"
                record.user_id = "user123"
                record.usage_count = 20
                record.billing_period = period
                record.created_at = datetime.now(timezone.utc)
                records.append(record)

        usage_reporter.stripe_client.get_subscription_item_for_price = AsyncMock(
            return_value={"id": "si_123"}
        )

        # First period succeeds, second fails
        call_count = 0

        async def create_usage_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return None  # Success
            raise StripeClientError("Payment required")

        usage_reporter.stripe_client.create_usage_record = AsyncMock(
            side_effect=create_usage_side_effect
        )

        with patch(
            "github_analyzer.database.operations.BillingUsageOperations.mark_usage_reported_to_stripe"
        ) as mock_mark:
            mock_mark.return_value = True

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await usage_reporter._report_user_usage_batch(
                    mock_db, user, records
                )

                assert result["processed"] == 4
                assert result["reported"] == 2  # First period only
                assert result["failed"] == 2  # Second period
                assert mock_mark.call_count == 2  # Only successful records

    async def test_mark_as_reported_failure(self, usage_reporter):
        """Test when marking records as reported fails."""
        mock_db = MagicMock()
        user = MagicMock()
        user.user_id = "user123"
        user.subscription_plan = SubscriptionPlan.PROFESSIONAL
        user.stripe_subscription_id = "sub_123"

        record = MagicMock()
        record.record_id = "usage_1"
        record.user_id = "user123"
        record.usage_count = 50
        record.billing_period = "2025-01"
        record.created_at = datetime.now(timezone.utc)

        usage_reporter.stripe_client.get_subscription_item_for_price = AsyncMock(
            return_value={"id": "si_123"}
        )

        usage_reporter.stripe_client.create_usage_record = AsyncMock()

        # Mock database error when marking as reported
        with patch(
            "github_analyzer.database.operations.BillingUsageOperations.mark_usage_reported_to_stripe"
        ) as mock_mark:
            mock_mark.side_effect = Exception("Database error")

            # Should handle the error gracefully
            result = await usage_reporter._report_user_usage_batch(
                mock_db, user, [record]
            )

            # The record was reported to Stripe but couldn't be marked in DB
            assert result["processed"] == 1
            # Due to the exception, it's counted as failed
            assert result["failed"] == 1

    async def test_concurrent_reporting_for_same_user(self, usage_reporter):
        """Test handling concurrent reporting attempts for the same user."""
        mock_db = MagicMock()

        # Simulate records being processed concurrently
        records = []
        for i in range(5):
            record = MagicMock()
            record.record_id = f"usage_{i}"
            record.user_id = "user123"
            record.usage_count = 10
            record.billing_period = "2025-01"
            record.created_at = datetime.now(timezone.utc)
            records.append(record)

        with patch(
            "github_analyzer.database.operations.BillingUsageOperations.get_unreported_usage"
        ) as mock_get:
            # Simulate some records being reported by another process
            mock_get.return_value = records[:3]  # Only first 3 are still unreported

            user = MagicMock()
            user.user_id = "user123"
            user.subscription_plan = SubscriptionPlan.PROFESSIONAL
            user.stripe_subscription_id = "sub_123"

            with patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_id",
                new_callable=AsyncMock,
            ) as mock_get_user:
                mock_get_user.return_value = user

                usage_reporter.stripe_client.get_subscription_item_for_price = (
                    AsyncMock(return_value={"id": "si_123"})
                )
                usage_reporter.stripe_client.create_usage_record = AsyncMock()

                with patch(
                    "github_analyzer.database.operations.BillingUsageOperations.mark_usage_reported_to_stripe"
                ) as mock_mark:
                    mock_mark.return_value = True

                    result = await usage_reporter.report_all_unreported_usage(mock_db)

                    assert result["records_processed"] == 3
                    assert result["records_reported"] == 3

    async def test_zero_usage_aggregation(self, usage_reporter):
        """Test handling of records that aggregate to zero usage."""
        mock_db = MagicMock()
        user = MagicMock()
        user.user_id = "user123"
        user.subscription_plan = SubscriptionPlan.ENTERPRISE
        user.stripe_subscription_id = "sub_123"

        # Create records with zero usage
        records = []
        for i in range(3):
            record = MagicMock()
            record.record_id = f"usage_{i}"
            record.user_id = "user123"
            record.usage_count = 0
            record.billing_period = "2025-01"
            record.created_at = datetime.now(timezone.utc)
            records.append(record)

        usage_reporter.stripe_client.get_subscription_item_for_price = AsyncMock(
            return_value={"id": "si_123"}
        )

        # Should still report zero usage to Stripe
        usage_reporter.stripe_client.create_usage_record = AsyncMock()

        with patch(
            "github_analyzer.database.operations.BillingUsageOperations.mark_usage_reported_to_stripe"
        ) as mock_mark:
            mock_mark.return_value = True

            result = await usage_reporter._report_user_usage_batch(
                mock_db, user, records
            )

            # Verify zero usage was reported
            usage_reporter.stripe_client.create_usage_record.assert_awaited_once()
            call_args = usage_reporter.stripe_client.create_usage_record.call_args
            assert call_args[1]["quantity"] == 0
            assert result["reported"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
