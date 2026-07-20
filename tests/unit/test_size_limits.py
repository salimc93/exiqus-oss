"""
Unit tests for repository size limit functionality.

Tests the plan-based and custom size limit logic to ensure
proper enforcement across different subscription plans.
"""

from unittest.mock import Mock, patch

import pytest

from github_analyzer.api.dependencies import get_user_repo_size_limit
from github_analyzer.database.models import SubscriptionPlan, User
from github_analyzer.utils.config import get_config


class TestSizeLimits:
    """Test repository size limit calculations."""

    def test_plan_based_limits_config(self):
        """Test that plan-based limits are correctly configured."""
        config = get_config()

        # Test all plan limits match actual configuration
        assert config.analysis.get_plan_repo_size_limit("free") == 50
        assert config.analysis.get_plan_repo_size_limit("basic") == 1000
        assert config.analysis.get_plan_repo_size_limit("professional") == 3000
        assert config.analysis.get_plan_repo_size_limit("enterprise") == 5000

        # Test case insensitivity
        assert config.analysis.get_plan_repo_size_limit("FREE") == 50
        assert config.analysis.get_plan_repo_size_limit("Professional") == 3000

        # Test default fallback for unknown plan
        assert config.analysis.get_plan_repo_size_limit("unknown") == 50

    @patch("github_analyzer.api.dependencies.get_config")
    def test_custom_limit_override(self, mock_get_config):
        """Test that custom limits override plan-based limits."""
        # Mock config
        mock_config = Mock()
        mock_get_config.return_value = mock_config

        # Create mock user with custom limit
        user = Mock(spec=User)
        user.custom_repo_size_limit_mb = 5000
        user.subscription_plan = SubscriptionPlan.ENTERPRISE
        user.email = "test@enterprise.com"

        # Should return custom limit, not plan default
        limit = get_user_repo_size_limit(user)
        assert limit == 5000

    @patch("github_analyzer.api.dependencies.get_config")
    def test_free_plan_limit(self, mock_get_config):
        """Test free plan size limit."""
        # Mock config
        mock_config = Mock()
        mock_config.analysis.get_plan_repo_size_limit.return_value = 10000
        mock_get_config.return_value = mock_config

        user = Mock(spec=User)
        user.custom_repo_size_limit_mb = None
        user.subscription_plan = SubscriptionPlan.FREE
        user.email = "test@free.com"

        limit = get_user_repo_size_limit(user)
        assert limit == 10000

    @patch("github_analyzer.api.dependencies.get_config")
    def test_basic_plan_limit(self, mock_get_config):
        """Test basic plan size limit."""
        # Mock config
        mock_config = Mock()
        mock_config.analysis.get_plan_repo_size_limit.return_value = 10000
        mock_get_config.return_value = mock_config

        user = Mock(spec=User)
        user.custom_repo_size_limit_mb = None
        user.subscription_plan = SubscriptionPlan.BASIC
        user.email = "test@basic.com"

        limit = get_user_repo_size_limit(user)
        assert limit == 10000

    @patch("github_analyzer.api.dependencies.get_config")
    def test_professional_plan_limit(self, mock_get_config):
        """Test professional plan size limit."""
        # Mock config
        mock_config = Mock()
        mock_config.analysis.get_plan_repo_size_limit.return_value = 10000
        mock_get_config.return_value = mock_config

        user = Mock(spec=User)
        user.custom_repo_size_limit_mb = None
        user.subscription_plan = SubscriptionPlan.PROFESSIONAL
        user.email = "test@professional.com"

        limit = get_user_repo_size_limit(user)
        assert limit == 10000

    @patch("github_analyzer.api.dependencies.get_config")
    def test_enterprise_plan_limit(self, mock_get_config):
        """Test enterprise plan size limit."""
        # Mock config
        mock_config = Mock()
        mock_config.analysis.get_plan_repo_size_limit.return_value = 10000
        mock_get_config.return_value = mock_config

        user = Mock(spec=User)
        user.custom_repo_size_limit_mb = None
        user.subscription_plan = SubscriptionPlan.ENTERPRISE
        user.email = "test@enterprise.com"

        limit = get_user_repo_size_limit(user)
        assert limit == 10000

    @patch("github_analyzer.api.dependencies.get_config")
    def test_custom_limit_priority(self, mock_get_config):
        """Test that custom limits take priority over plan limits."""
        # Mock config
        mock_config = Mock()
        mock_get_config.return_value = mock_config

        # Enterprise user with custom limit lower than plan default
        user = Mock(spec=User)
        user.custom_repo_size_limit_mb = 200
        user.subscription_plan = SubscriptionPlan.ENTERPRISE
        user.email = "test@enterprise.com"

        limit = get_user_repo_size_limit(user)
        assert limit == 200  # Should use custom, not plan default of 10000

    @patch("github_analyzer.api.dependencies.get_config")
    def test_zero_custom_limit(self, mock_get_config):
        """Test that zero custom limit is respected."""
        # Mock config
        mock_config = Mock()
        mock_get_config.return_value = mock_config

        user = Mock(spec=User)
        user.custom_repo_size_limit_mb = 0
        user.subscription_plan = SubscriptionPlan.ENTERPRISE
        user.email = "test@enterprise.com"

        limit = get_user_repo_size_limit(user)
        assert limit == 0  # Should respect the zero limit

    @patch("github_analyzer.api.dependencies.get_config")
    @pytest.mark.parametrize(
        "plan,expected_limit",
        [
            (SubscriptionPlan.FREE, 10000),
            (SubscriptionPlan.BASIC, 10000),
            (SubscriptionPlan.PROFESSIONAL, 10000),
            (SubscriptionPlan.ENTERPRISE, 10000),
        ],
    )
    def test_all_plans_parametrized(self, mock_get_config, plan, expected_limit):
        """Test all subscription plans with parametrized test."""
        # Mock config
        mock_config = Mock()
        mock_config.analysis.get_plan_repo_size_limit.return_value = expected_limit
        mock_get_config.return_value = mock_config

        user = Mock(spec=User)
        user.custom_repo_size_limit_mb = None
        user.subscription_plan = plan
        user.email = f"test@{plan.value}.com"

        limit = get_user_repo_size_limit(user)
        assert limit == expected_limit

    def test_config_limits_dictionary(self):
        """Test that the config limits dictionary is properly structured."""
        config = get_config()
        limits = config.analysis.repo_size_limits_mb

        # Check all required keys exist
        assert "free" in limits
        assert "basic" in limits
        assert "professional" in limits
        assert "enterprise" in limits

        # Check values are integers and make sense
        assert isinstance(limits["free"], int)
        assert isinstance(limits["basic"], int)
        assert isinstance(limits["professional"], int)
        assert isinstance(limits["enterprise"], int)

        # Check actual plan limits
        assert limits["free"] == 50
        assert limits["basic"] == 1000
        assert limits["professional"] == 3000
        assert limits["enterprise"] == 5000

    @patch("github_analyzer.api.dependencies.get_config")
    def test_none_custom_limit_uses_plan(self, mock_get_config):
        """Test that None custom limit falls back to plan limit."""
        # Mock config
        mock_config = Mock()
        mock_config.analysis.get_plan_repo_size_limit.return_value = 10000
        mock_get_config.return_value = mock_config

        user = Mock(spec=User)
        user.custom_repo_size_limit_mb = None  # Explicitly None
        user.subscription_plan = SubscriptionPlan.PROFESSIONAL
        user.email = "test@professional.com"

        limit = get_user_repo_size_limit(user)
        assert limit == 10000  # Should use plan limit

    def test_config_get_plan_limit_edge_cases(self):
        """Test edge cases for get_plan_repo_size_limit method."""
        config = get_config()

        # Test empty string
        assert config.analysis.get_plan_repo_size_limit("") == 50

        # Test None (should handle gracefully)
        try:
            limit = config.analysis.get_plan_repo_size_limit(None)
            # If it doesn't raise an exception, should return default
            assert limit == 50
        except (AttributeError, TypeError):
            # This is also acceptable behavior
            pass

        # Test whitespace
        assert config.analysis.get_plan_repo_size_limit("  free  ") == 50

        # Test mixed case
        assert config.analysis.get_plan_repo_size_limit("ENTERPRISE") == 5000
        assert config.analysis.get_plan_repo_size_limit("Basic") == 1000

    @patch("github_analyzer.api.dependencies.logger")
    @patch("github_analyzer.api.dependencies.get_config")
    def test_logging_custom_limit(self, mock_get_config, mock_logger):
        """Test that custom limits are logged correctly."""
        # Mock config
        mock_config = Mock()
        mock_get_config.return_value = mock_config

        user = Mock(spec=User)
        user.custom_repo_size_limit_mb = 2048
        user.subscription_plan = SubscriptionPlan.ENTERPRISE
        user.email = "test@enterprise.com"

        get_user_repo_size_limit(user)

        # Should log the custom limit usage
        mock_logger.info.assert_called_once()
        log_message = mock_logger.info.call_args[0][0]
        assert "custom repo size limit" in log_message.lower()
        assert "test@enterprise.com" in log_message
        assert "2048MB" in log_message

    @patch("github_analyzer.api.dependencies.logger")
    @patch("github_analyzer.api.dependencies.get_config")
    def test_logging_plan_limit(self, mock_get_config, mock_logger):
        """Test that plan-based limits are logged correctly."""
        # Mock config
        mock_config = Mock()
        mock_config.analysis.get_plan_repo_size_limit.return_value = 10000
        mock_get_config.return_value = mock_config

        user = Mock(spec=User)
        user.custom_repo_size_limit_mb = None
        user.subscription_plan = SubscriptionPlan.BASIC
        user.email = "test@basic.com"

        get_user_repo_size_limit(user)

        # Should log the plan limit usage
        mock_logger.debug.assert_called_once()
        log_message = mock_logger.debug.call_args[0][0]
        assert "plan-based repo size limit" in log_message.lower()
        assert "test@basic.com" in log_message
        assert "basic" in log_message.lower()
        assert "10000MB" in log_message


class TestSizeLimitValidation:
    """Test validation logic for size limits."""

    def test_valid_size_ranges(self):
        """Test that size limits are within reasonable ranges."""
        config = get_config()
        limits = config.analysis.repo_size_limits_mb

        # All limits should be positive
        for plan, limit in limits.items():
            assert limit > 0, f"{plan} plan has invalid limit: {limit}"

        # All limits should be reasonable (not too large)
        for plan, limit in limits.items():
            assert limit <= 10240, f"{plan} plan limit too large: {limit}MB (>10GB)"

    def test_size_limit_progression(self):
        """Test that size limits increase with tier progression."""
        config = get_config()

        free_limit = config.analysis.get_plan_repo_size_limit("free")
        basic_limit = config.analysis.get_plan_repo_size_limit("basic")
        pro_limit = config.analysis.get_plan_repo_size_limit("professional")
        enterprise_limit = config.analysis.get_plan_repo_size_limit("enterprise")

        # Verify tiered progression: 50MB -> 1GB -> 3GB -> 5GB
        assert free_limit == 50
        assert basic_limit == 1000
        assert pro_limit == 3000
        assert enterprise_limit == 5000
        assert free_limit < basic_limit < pro_limit < enterprise_limit


if __name__ == "__main__":
    # Simple test runner if pytest is not available
    test_instance = TestSizeLimits()
    validation_instance = TestSizeLimitValidation()

    try:
        test_instance.test_plan_based_limits_config()
        print("✓ test_plan_based_limits_config passed")

        test_instance.test_config_limits_dictionary()
        print("✓ test_config_limits_dictionary passed")

        test_instance.test_config_get_plan_limit_edge_cases()
        print("✓ test_config_get_plan_limit_edge_cases passed")

        validation_instance.test_valid_size_ranges()
        print("✓ test_valid_size_ranges passed")

        validation_instance.test_size_limit_progression()
        print("✓ test_size_limit_progression passed")

        print("\n✅ Basic size limit tests passed!")
        print("Note: Mocked dependency tests require pytest to run properly")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise
