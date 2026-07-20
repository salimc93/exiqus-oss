"""
Tests for usage tracking functionality.

Tests API usage recording, quota checking, usage summaries,
and billing usage calculations.
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from github_analyzer.billing.usage_tracker import UsageTracker
from github_analyzer.database.models import (
    BillingUsageRecord,
    SubscriptionPlan,
    User,
)


class TestUsageTracker:
    """Test suite for UsageTracker."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        """Mock user for testing."""
        return Mock(
            spec=User,
            **{
                "user_id": "usr_test123",
                "email": "test@example.com",
                "subscription_plan": SubscriptionPlan.BASIC,
                "usage_quota": 100,
                "usage_count": 25,
            },
        )

    @pytest.fixture
    def mock_usage_record(self):
        """Mock billing usage record."""
        return Mock(
            spec=BillingUsageRecord,
            **{
                "record_id": "usage_20240701_120000_usr_test",
                "user_id": "usr_test123",
                "usage_type": "analysis",
                "usage_count": 1,
                "unit_cost": "0.01",
                "total_cost": "0.01",
                "created_at": datetime.now(timezone.utc),
            },
        )

    async def test_record_api_usage_success(self, mock_db, mock_user):
        """Test successful API usage recording."""
        with (
            patch(
                "github_analyzer.database.operations.BillingUsageOperations.create_usage_record",
                return_value=None,
            ) as mock_create,
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_id",
                return_value=mock_user,
            ),
            patch(
                "github_analyzer.database.operations.UserOperations.increment_usage_count",
                return_value=True,
            ),
        ):
            record_id = await UsageTracker.record_api_usage(
                db=mock_db, user_id="usr_test123", usage_type="analysis", usage_count=1
            )

            assert record_id.startswith("usage_")
            assert "usr_test" in record_id
            mock_create.assert_called_once()

    async def test_record_api_usage_with_metadata(self, mock_db, mock_user):
        """Test API usage recording with metadata."""
        metadata = {"endpoint": "/api/v1/analyze", "repository": "test/repo"}

        with (
            patch(
                "github_analyzer.database.operations.BillingUsageOperations.create_usage_record",
                return_value=None,
            ) as mock_create,
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_id",
                return_value=mock_user,
            ),
            patch(
                "github_analyzer.database.operations.UserOperations.increment_usage_count",
                return_value=True,
            ),
        ):
            record_id = await UsageTracker.record_api_usage(
                db=mock_db,
                user_id="usr_test123",
                usage_type="analysis",
                usage_count=1,
                metadata=metadata,
            )

            assert record_id.startswith("usage_")

            # Check that create_usage_record was called with JSON metadata
            call_args = mock_create.call_args[1]
            assert call_args["metadata"] == json.dumps(metadata)

    async def test_record_api_usage_batch_calculation(self, mock_db, mock_user):
        """Test usage recording for batch operations with cost calculation."""
        with (
            patch(
                "github_analyzer.database.operations.BillingUsageOperations.create_usage_record",
                return_value=None,
            ) as mock_create,
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_id",
                return_value=mock_user,
            ),
            patch(
                "github_analyzer.database.operations.UserOperations.increment_usage_count",
                return_value=True,
            ) as mock_increment,
        ):
            await UsageTracker.record_api_usage(
                db=mock_db,
                user_id="usr_test123",
                usage_type="batch_analysis",
                usage_count=5,
            )

            call_args = mock_create.call_args[1]
            assert call_args["usage_count"] == 5
            assert call_args["unit_cost"] == "0.01"
            assert call_args["total_cost"] == "0.05"
            mock_increment.assert_called_once_with(mock_db, "usr_test123", 5)

    async def test_check_quota_available_sufficient(self, mock_db, mock_user):
        """Test quota check when user has sufficient quota."""
        with patch(
            "github_analyzer.database.operations.UserOperations.get_user_by_id",
            return_value=mock_user,
        ):
            result = await UsageTracker.check_quota_available(
                db=mock_db, user_id="usr_test123", requested_usage=10
            )

            assert result["available"] is True
            assert result["quota_remaining"] == 75
            assert result["usage_consumed"] == 25
            assert result["requested_usage"] == 10
            assert result["plan"] == "BASIC"

    async def test_check_quota_available_insufficient(self, mock_db, mock_user):
        """Test quota check when user has insufficient quota."""
        mock_user.usage_count = 95  # Close to limit

        with patch(
            "github_analyzer.database.operations.UserOperations.get_user_by_id",
            return_value=mock_user,
        ):
            result = await UsageTracker.check_quota_available(
                db=mock_db, user_id="usr_test123", requested_usage=10
            )

            assert result["available"] is False
            assert result["quota_remaining"] == 5  # 100 - 95
            assert result["requested_usage"] == 10
            assert result["reason"] == "Insufficient quota - please upgrade your plan"

    async def test_check_quota_available_user_not_found(self, mock_db):
        """Test quota check when user doesn't exist."""
        with patch(
            "github_analyzer.database.operations.UserOperations.get_user_by_id",
            return_value=None,
        ):
            result = await UsageTracker.check_quota_available(
                db=mock_db, user_id="usr_nonexistent", requested_usage=1
            )

            assert result["available"] is False
            assert result["reason"] == "User not found"
            assert result["quota_remaining"] == 0

    async def test_get_usage_summary_success(
        self, mock_db, mock_user, mock_usage_record
    ):
        """Test successful usage summary generation."""
        usage_records = [mock_usage_record]
        usage_summary = {"analysis": 5, "api_call": 10}

        with (
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_id",
                return_value=mock_user,
            ),
            patch(
                "github_analyzer.database.operations.BillingUsageOperations.get_user_usage_for_period",
                return_value=usage_records,
            ),
            patch(
                "github_analyzer.database.operations.BillingUsageOperations.get_usage_summary_for_period",
                return_value=usage_summary,
            ),
        ):
            result = await UsageTracker.get_usage_summary(
                db=mock_db, user_id="usr_test123", billing_period="2024-07"
            )

            assert result["user_id"] == "usr_test123"
            assert result["billing_period"] == "2024-07"
            assert result["plan"] == "BASIC"
            assert result["usage_summary"] == usage_summary
            assert result["total_usage"] == 15  # 5 + 10
            assert result["total_cost"] == 0.01  # From mock record
            assert result["quota_total"] == 100
            assert result["quota_remaining"] == 75

    async def test_get_usage_summary_default_period(self, mock_db, mock_user):
        """Test usage summary with default current period."""
        current_month = datetime.now(timezone.utc).strftime("%Y-%m")

        with (
            patch(
                "github_analyzer.database.operations.UserOperations.get_user_by_id",
                return_value=mock_user,
            ),
            patch(
                "github_analyzer.database.operations.BillingUsageOperations.get_user_usage_for_period",
                return_value=[],
            ),
            patch(
                "github_analyzer.database.operations.BillingUsageOperations.get_usage_summary_for_period",
                return_value={},
            ),
        ):
            result = await UsageTracker.get_usage_summary(
                db=mock_db, user_id="usr_test123"
            )

            assert result["billing_period"] == current_month

    async def test_reset_monthly_usage_success(self, mock_db):
        """Test successful monthly usage reset."""
        with patch(
            "github_analyzer.database.operations.UserOperations.update_usage_count",
            return_value=True,
        ) as mock_update:
            result = await UsageTracker.reset_monthly_usage(
                db=mock_db, user_id="usr_test123"
            )

            assert result is True
            mock_update.assert_called_once_with(mock_db, "usr_test123", 0)

    async def test_reset_monthly_usage_failure(self, mock_db):
        """Test monthly usage reset failure."""
        with patch(
            "github_analyzer.database.operations.UserOperations.update_usage_count",
            return_value=False,
        ):
            result = await UsageTracker.reset_monthly_usage(
                db=mock_db, user_id="usr_test123"
            )

            assert result is False

    async def test_bulk_reset_monthly_usage_success(self, mock_db):
        """Test successful bulk monthly usage reset."""
        mock_users = [
            Mock(user_id="usr_test1"),
            Mock(user_id="usr_test2"),
            Mock(user_id="usr_test3"),
        ]

        with (
            patch(
                "github_analyzer.database.operations.UserOperations.get_all_users",
                return_value=mock_users,
            ),
            patch(
                "github_analyzer.database.operations.UserOperations.update_usage_count",
                return_value=True,
            ) as mock_update,
        ):
            result = await UsageTracker.bulk_reset_monthly_usage(mock_db)

            assert result["total_users"] == 3
            assert result["reset_successful"] == 3
            assert result["reset_failed"] == 0
            assert result["plan_filter"] is None
            assert mock_update.call_count == 3

    async def test_bulk_reset_monthly_usage_with_plan_filter(self, mock_db):
        """Test bulk usage reset with plan filter."""
        mock_users = [Mock(user_id="usr_basic1"), Mock(user_id="usr_basic2")]

        with (
            patch(
                "github_analyzer.database.operations.UserOperations.get_users_by_subscription_plan",
                return_value=mock_users,
            ),
            patch(
                "github_analyzer.database.operations.UserOperations.update_usage_count",
                return_value=True,
            ),
        ):
            result = await UsageTracker.bulk_reset_monthly_usage(
                mock_db, plan=SubscriptionPlan.BASIC
            )

            assert result["total_users"] == 2
            assert result["reset_successful"] == 2
            assert result["plan_filter"] == "BASIC"

    def test_calculate_overage_cost_no_overage(self):
        """Test overage cost calculation when within limits."""
        cost = UsageTracker.calculate_overage_cost(
            usage_consumed=50, quota_limit=100, overage_rate="0.02"
        )

        assert cost == "0.00"

    def test_calculate_overage_cost_with_overage(self):
        """Test overage cost calculation with usage over limits."""
        cost = UsageTracker.calculate_overage_cost(
            usage_consumed=120, quota_limit=100, overage_rate="0.02"
        )

        # 20 units over limit * $0.02 = $0.40
        assert cost == "0.40"

    async def test_get_unreported_usage_success(self, mock_db, mock_usage_record):
        """Test getting unreported usage records."""
        unreported_records = [mock_usage_record]

        with patch(
            "github_analyzer.database.operations.BillingUsageOperations.get_unreported_usage",
            return_value=unreported_records,
        ):
            result = await UsageTracker.get_unreported_usage(mock_db, limit=100)

            assert len(result) == 1
            assert result[0] == mock_usage_record

    async def test_mark_usage_reported_success(self, mock_db):
        """Test marking usage as reported to Stripe."""
        with patch(
            "github_analyzer.database.operations.BillingUsageOperations.mark_usage_reported_to_stripe",
            return_value=True,
        ) as mock_mark:
            result = await UsageTracker.mark_usage_reported(
                db=mock_db,
                record_id="usage_test123",
                stripe_usage_record_id="ur_stripe123",
            )

            assert result is True
            mock_mark.assert_called_once_with(mock_db, "usage_test123", "ur_stripe123")
