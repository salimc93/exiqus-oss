"""
Tests for admin dashboard with user verification status.

Tests that the admin dashboard correctly reports verified vs unverified users.
"""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.github_analyzer.api.routes.admin_management import get_admin_dashboard
from src.github_analyzer.database.models import SubscriptionPlan, User


@pytest.fixture
def mock_admin_user():
    """Create mock admin user for authentication."""
    user = AsyncMock(spec=User)
    user.user_id = "admin_123"
    user.is_admin = True
    user.email = "admin@example.com"
    return user


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.mark.asyncio
async def test_admin_dashboard_shows_verification_status(
    mock_db_session, mock_admin_user
):
    """Test that admin dashboard correctly separates verified and unverified users."""

    # Mock user counts - set up return values for different queries
    call_count = 0

    def scalar_side_effect(query):
        nonlocal call_count
        call_count += 1

        # Map call order to return values
        returns = {
            1: 10,  # total_users
            2: 7,  # verified_users
            3: 3,  # unverified_users
            4: 5,  # active_users (only verified)
            5: 8,  # new_users_month
            6: 6,  # new_verified_month
            7: 4,  # new_users_week
            8: 15,  # total_analyses
            9: 2,  # analyses_today
            10: 5,  # analyses_week
        }
        return returns.get(call_count, 0)

    # Configure AsyncMock to return the side effect values when awaited
    mock_db_session.scalar = AsyncMock(side_effect=scalar_side_effect)

    # Mock users by plan query
    mock_plan_result = [
        (SubscriptionPlan.FREE, 4),
        (SubscriptionPlan.BASIC, 2),
        (SubscriptionPlan.PROFESSIONAL, 1),
    ]
    # Mock execute to handle both plan counts and recent activities
    call_count_execute = 0

    def execute_side_effect(query, *args, **kwargs):
        nonlocal call_count_execute
        call_count_execute += 1

        from unittest.mock import Mock

        mock_result = Mock()

        if call_count_execute == 1:  # Plan counts query
            mock_result.__iter__ = lambda self: iter(mock_plan_result)
        else:  # All other queries - return empty iterables
            mock_result.__iter__ = lambda self: iter([])
            mock_result.all = lambda: []

        return mock_result

    mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

    # Mock dependencies
    with patch(
        "src.github_analyzer.api.routes.admin_management.StripeClient"
    ) as mock_stripe:
        mock_stripe.return_value.is_configured = False

        with patch(
            "src.github_analyzer.api.routes.admin_management.get_admin_user_from_token",
            return_value=mock_admin_user,
        ):
            # Call the endpoint
            response = await get_admin_dashboard(
                current_user=mock_admin_user, db=mock_db_session
            )

    # Verify response includes verification stats
    assert response.total_users == 10
    assert response.verified_users == 7
    assert response.unverified_users == 3
    assert response.active_users == 5  # Only verified users who logged in recently
    assert response.new_verified_month == 6  # New users who verified


@pytest.mark.asyncio
async def test_admin_dashboard_filters_plan_counts_by_verification(
    mock_db_session, mock_admin_user
):
    """Test that subscription plan counts only include verified users."""

    # Mock scalar queries (simplified)
    mock_db_session.scalar = AsyncMock(return_value=0)

    # Mock the plan counts query - should filter by is_verified
    mock_plan_result = [
        (SubscriptionPlan.FREE, 5),
        (SubscriptionPlan.PROFESSIONAL, 2),
    ]

    # Create multiple mock results for different execute calls
    call_count = 0

    def execute_side_effect(query, *args, **kwargs):
        nonlocal call_count
        call_count += 1

        from unittest.mock import Mock

        mock_result = Mock()

        if call_count == 1:  # Plan counts query
            mock_result.__iter__ = lambda self: iter(mock_plan_result)
        else:  # All other queries - return empty iterables
            mock_result.__iter__ = lambda self: iter([])
            mock_result.all = lambda: []
            mock_result.scalar = lambda: 0

        return mock_result

    mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

    # Mock dependencies
    with patch(
        "src.github_analyzer.api.routes.admin_management.StripeClient"
    ) as mock_stripe:
        mock_stripe.return_value.is_configured = False

        with patch(
            "src.github_analyzer.api.routes.admin_management.get_admin_user_from_token",
            return_value=mock_admin_user,
        ):
            response = await get_admin_dashboard(
                current_user=mock_admin_user, db=mock_db_session
            )

    # Verify plan counts in response (only includes verified users)
    assert response.users_by_plan["free"] == 5
    assert response.users_by_plan["professional"] == 2


@pytest.mark.asyncio
async def test_admin_dashboard_active_users_excludes_unverified(
    mock_db_session, mock_admin_user
):
    """Test that active users count excludes unverified users."""

    call_count = 0

    def scalar_with_inspection(query):
        nonlocal call_count
        call_count += 1

        # Convert query to string to inspect it
        query_str = str(query)

        # Check if this is the active users query
        if "last_login" in query_str and call_count == 4:  # 4th call is active users
            # Verify it filters by is_verified
            assert "is_verified" in query_str
            return 3  # Return active verified users count

        return 0  # Default for other queries

    mock_db_session.scalar = AsyncMock(side_effect=scalar_with_inspection)

    # Mock execute for empty results
    from unittest.mock import Mock

    mock_empty_result = Mock()
    mock_empty_result.__iter__ = lambda self: iter([])
    mock_db_session.execute = AsyncMock(return_value=mock_empty_result)

    with patch(
        "src.github_analyzer.api.routes.admin_management.StripeClient"
    ) as mock_stripe:
        mock_stripe.return_value.is_configured = False

        with patch(
            "src.github_analyzer.api.routes.admin_management.get_admin_user_from_token",
            return_value=mock_admin_user,
        ):
            response = await get_admin_dashboard(
                current_user=mock_admin_user, db=mock_db_session
            )

    # Active users should only count verified users
    assert response.active_users == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
