"""
Test suite for usage reporting service.

Tests the batch processing, aggregation, retry logic,
and Stripe integration for usage reporting.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from github_analyzer.billing.stripe_client import StripeClientError
from github_analyzer.billing.usage_reporter import UsageReporter
from github_analyzer.database.models import SubscriptionPlan


class TestUsageReporter:
    """Test usage reporting functionality."""

    @pytest.fixture
    def usage_reporter(self):
        """Create a UsageReporter instance with mocked Stripe client."""
        mock_stripe_client = MagicMock()
        return UsageReporter(stripe_client=mock_stripe_client)

    @pytest.fixture
    def mock_usage_records(self):
        """Create mock usage records."""
        records = []
        for i in range(5):
            record = MagicMock()
            record.record_id = f"usage_{i}"
            record.user_id = "user123" if i < 3 else "user456"
            record.usage_count = 10
            record.billing_period = "2025-01"
            record.created_at = datetime.now(timezone.utc)
            records.append(record)
        return records

    @pytest.fixture
    def mock_user_professional(self):
        """Create a mock professional user."""
        user = MagicMock()
        user.user_id = "user123"
        user.subscription_plan = SubscriptionPlan.PROFESSIONAL
        user.stripe_subscription_id = "sub_prof123"
        return user

    @pytest.fixture
    def mock_user_enterprise(self):
        """Create a mock enterprise user."""
        user = MagicMock()
        user.user_id = "user456"
        user.subscription_plan = SubscriptionPlan.ENTERPRISE
        user.stripe_subscription_id = "sub_ent456"
        return user

    @pytest.fixture
    def mock_user_basic(self):
        """Create a mock basic user (no overages)."""
        user = MagicMock()
        user.user_id = "user789"
        user.subscription_plan = SubscriptionPlan.BASIC
        user.stripe_subscription_id = "sub_basic789"
        return user

    async def test_report_all_unreported_usage_no_records(self, usage_reporter):
        """Test reporting when no unreported records exist."""
        mock_db = MagicMock()

        with patch(
            "github_analyzer.database.operations.BillingUsageOperations.get_unreported_usage"
        ) as mock_get:
            mock_get.return_value = []

            result = await usage_reporter.report_all_unreported_usage(mock_db)

            assert result["success"] is True
            assert result["records_processed"] == 0
            assert result["records_reported"] == 0
            assert result["records_failed"] == 0

    async def test_report_all_unreported_usage_success(
        self,
        usage_reporter,
        mock_usage_records,
        mock_user_professional,
        mock_user_enterprise,
    ):
        """Test successful reporting of unreported usage."""
        mock_db = MagicMock()

        with patch(
            "github_analyzer.database.operations.BillingUsageOperations.get_unreported_usage"
        ) as mock_get_unreported:
            mock_get_unreported.return_value = mock_usage_records

            with patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_id"
            ) as mock_get_user:
                # Return different users based on ID
                def get_user_side_effect(db, user_id):
                    if user_id == "user123":
                        return mock_user_professional
                    elif user_id == "user456":
                        return mock_user_enterprise
                    return None

                mock_get_user.side_effect = get_user_side_effect

                # Mock subscription item lookup
                usage_reporter.stripe_client.get_subscription_item_for_price = (
                    AsyncMock(return_value={"id": "si_overage123"})
                )

                # Mock usage record creation
                usage_reporter.stripe_client.create_usage_record = AsyncMock()

                with patch(
                    "github_analyzer.database.operations.BillingUsageOperations.mark_usage_reported_to_stripe"
                ) as mock_mark:
                    mock_mark.return_value = True

                    result = await usage_reporter.report_all_unreported_usage(mock_db)

                    assert result["success"] is True
                    assert result["records_processed"] == 5
                    assert result["records_reported"] == 5
                    assert result["records_failed"] == 0

    async def test_report_user_overage_usage_success(
        self, usage_reporter, mock_user_professional
    ):
        """Test reporting overage usage for a specific user."""
        mock_db = MagicMock()

        with patch(
            "github_analyzer.database.operations.UserOperations.get_user_by_id"
        ) as mock_get_user:
            mock_get_user.return_value = mock_user_professional

            # Mock subscription item lookup
            usage_reporter.stripe_client.get_subscription_item_for_price = AsyncMock(
                return_value={"id": "si_overage123"}
            )

            # Mock usage record creation
            usage_reporter.stripe_client.create_usage_record = AsyncMock()

            result = await usage_reporter.report_user_overage_usage(
                mock_db, "user123", 50
            )

            assert result is True
            usage_reporter.stripe_client.create_usage_record.assert_awaited_once()

    async def test_report_user_overage_usage_user_not_found(self, usage_reporter):
        """Test reporting overage when user doesn't exist."""
        mock_db = MagicMock()

        with patch(
            "github_analyzer.database.operations.UserOperations.get_user_by_id"
        ) as mock_get_user:
            mock_get_user.return_value = None

            result = await usage_reporter.report_user_overage_usage(
                mock_db, "nonexistent", 50
            )

            assert result is False

    async def test_report_user_overage_usage_plan_no_overages(
        self, usage_reporter, mock_user_basic
    ):
        """Test reporting overage for plan that doesn't support overages."""
        mock_db = MagicMock()

        with patch(
            "github_analyzer.database.operations.UserOperations.get_user_by_id"
        ) as mock_get_user:
            mock_get_user.return_value = mock_user_basic

            result = await usage_reporter.report_user_overage_usage(
                mock_db, "user789", 50
            )

            assert result is False

    async def test_report_user_overage_usage_stripe_error(
        self, usage_reporter, mock_user_professional
    ):
        """Test handling Stripe errors during overage reporting."""
        mock_db = MagicMock()

        with patch(
            "github_analyzer.database.operations.UserOperations.get_user_by_id"
        ) as mock_get_user:
            mock_get_user.return_value = mock_user_professional

            usage_reporter.stripe_client.get_subscription_item_for_price = AsyncMock(
                return_value={"id": "si_overage123"}
            )

            # Mock Stripe error
            usage_reporter.stripe_client.create_usage_record = AsyncMock(
                side_effect=StripeClientError("API error")
            )

            result = await usage_reporter.report_user_overage_usage(
                mock_db, "user123", 50
            )

            assert result is False

    async def test_process_user_records_user_not_found(
        self, usage_reporter, mock_usage_records
    ):
        """Test processing records when user is not found."""
        mock_db = MagicMock()
        user_records_map = {"user999": mock_usage_records[:2]}

        with patch(
            "github_analyzer.database.operations.UserOperations.get_user_by_id"
        ) as mock_get_user:
            mock_get_user.return_value = None

            result = await usage_reporter._process_user_records(
                mock_db, user_records_map
            )

            assert result["success"] is False
            assert result["records_failed"] == 2
            assert len(result["failed_records"]) == 2

    async def test_report_user_usage_batch_no_stripe_subscription(
        self, usage_reporter, mock_usage_records
    ):
        """Test batch reporting when user has no Stripe subscription."""
        mock_db = MagicMock()
        user = MagicMock()
        user.user_id = "user123"
        user.subscription_plan = SubscriptionPlan.PROFESSIONAL
        user.stripe_subscription_id = None

        result = await usage_reporter._report_user_usage_batch(
            mock_db, user, mock_usage_records[:3]
        )

        assert result["processed"] == 3
        assert result["reported"] == 0
        assert result["failed"] == 3

    async def test_report_with_retries_success(self, usage_reporter):
        """Test successful usage reporting with retries."""
        usage_reporter.stripe_client.create_usage_record = AsyncMock()

        result = await usage_reporter._report_with_retries("si_123", 100, 1234567890)

        assert result is True
        usage_reporter.stripe_client.create_usage_record.assert_awaited_once()

    async def test_report_with_retries_eventual_success(self, usage_reporter):
        """Test usage reporting succeeds after retries."""
        # Fail twice, then succeed
        usage_reporter.stripe_client.create_usage_record = AsyncMock(
            side_effect=[
                StripeClientError("Temporary error"),
                StripeClientError("Temporary error"),
                None,  # Success
            ]
        )

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await usage_reporter._report_with_retries(
                "si_123", 100, 1234567890
            )

        assert result is True
        assert usage_reporter.stripe_client.create_usage_record.call_count == 3

    async def test_report_with_retries_all_attempts_fail(self, usage_reporter):
        """Test usage reporting fails after all retries."""
        usage_reporter.stripe_client.create_usage_record = AsyncMock(
            side_effect=StripeClientError("Permanent error")
        )

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await usage_reporter._report_with_retries(
                "si_123", 100, 1234567890
            )

        assert result is False
        assert usage_reporter.stripe_client.create_usage_record.call_count == 3

    def test_group_records_by_user(self, usage_reporter, mock_usage_records):
        """Test grouping usage records by user ID."""
        grouped = usage_reporter._group_records_by_user(mock_usage_records)

        assert len(grouped) == 2
        assert "user123" in grouped
        assert "user456" in grouped
        assert len(grouped["user123"]) == 3
        assert len(grouped["user456"]) == 2

    def test_aggregate_usage_by_period(self, usage_reporter):
        """Test aggregating usage records by billing period."""
        records = []
        for i in range(5):
            record = MagicMock()
            record.billing_period = "2025-01" if i < 3 else "2025-02"
            records.append(record)

        aggregated = usage_reporter._aggregate_usage_by_period(records)

        assert len(aggregated) == 2
        assert "2025-01" in aggregated
        assert "2025-02" in aggregated
        assert len(aggregated["2025-01"]) == 3
        assert len(aggregated["2025-02"]) == 2

    async def test_process_hourly_usage_reporting_success(self, usage_reporter):
        """Test hourly usage reporting task."""
        mock_db = MagicMock()

        with patch.object(usage_reporter, "report_all_unreported_usage") as mock_report:
            mock_report.return_value = {
                "success": True,
                "records_processed": 100,
                "records_reported": 95,
                "records_failed": 5,
            }

            result = await usage_reporter.process_hourly_usage_reporting(mock_db)

            assert result["success"] is True
            assert result["records_reported"] == 95
            mock_report.assert_called_once_with(mock_db, limit=500)

    async def test_process_hourly_usage_reporting_error(self, usage_reporter):
        """Test hourly usage reporting with error handling."""
        mock_db = MagicMock()

        with patch.object(usage_reporter, "report_all_unreported_usage") as mock_report:
            mock_report.side_effect = Exception("Database error")

            result = await usage_reporter.process_hourly_usage_reporting(mock_db)

            assert result["success"] is False
            assert "error" in result
            assert result["records_reported"] == 0

    async def test_report_user_usage_batch_plan_no_support(
        self, usage_reporter, mock_usage_records, mock_user_basic
    ):
        """Test batch reporting for plan without overage support."""
        mock_db = MagicMock()

        with patch(
            "github_analyzer.database.operations.BillingUsageOperations.mark_usage_reported_to_stripe"
        ) as mock_mark:
            mock_mark.return_value = True

            result = await usage_reporter._report_user_usage_batch(
                mock_db, mock_user_basic, mock_usage_records[:2]
            )

            assert result["processed"] == 2
            assert result["reported"] == 2  # Marked as reported even without Stripe
            assert result["failed"] == 0
            assert mock_mark.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
