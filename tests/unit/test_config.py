"""
Unit tests for configuration management.

Tests the Config class and related functionality for environment
variable handling, validation, and configuration management.
"""

import os
from unittest.mock import patch

import pytest

from github_analyzer.utils.config import (
    DEFAULT_ANTHROPIC_MODEL,
    Config,
    get_config,
    reload_config,
)


class TestConfig:
    """Test the Config class functionality."""

    def test_config_with_valid_environment(self):
        """Test configuration with valid environment variables."""
        with patch.dict(
            os.environ,
            {
                "GITHUB_TOKEN": "ghp_test_token_1234567890123456789012345678",
                "ANTHROPIC_API_KEY": "sk-ant-api-test-key-12345",
                "ENVIRONMENT": "test",
                "DEBUG": "true",
            },
        ):
            config = Config()

            assert config.github_token == "ghp_test_token_1234567890123456789012345678"
            assert config.anthropic_api_key == "sk-ant-api-test-key-12345"
            assert config.environment == "test"
            assert config.debug is True

    def test_config_missing_required_vars(self):
        """Test configuration fails with missing required variables."""
        # Clear any cached config first
        import github_analyzer.utils.config

        github_analyzer.utils.config._config = None

        with patch.dict(os.environ, {}, clear=True):
            # Pass a non-existent env file to prevent loading from any .env file
            # Explicitly disable validation skipping for this test
            with pytest.raises(ValueError) as exc_info:
                Config(env_file="/non/existent/path/.env", skip_validation=False)

            assert "Missing required environment variables" in str(exc_info.value)
            assert "GITHUB_TOKEN" in str(exc_info.value)
            assert "ANTHROPIC_API_KEY" in str(exc_info.value)

    def test_config_placeholder_values(self):
        """Test configuration fails with placeholder values."""
        with patch.dict(
            os.environ,
            {
                "GITHUB_TOKEN": "your_github_token_here",
                "ANTHROPIC_API_KEY": "your_anthropic_key_here",
            },
        ):
            # Explicitly disable validation skipping for this test
            with pytest.raises(ValueError) as exc_info:
                Config(skip_validation=False)

            assert "Missing required environment variables" in str(exc_info.value)

    def test_config_defaults(self):
        """Test configuration default values."""
        with patch.dict(
            os.environ,
            {
                "GITHUB_TOKEN": "ghp_test_token_1234567890123456789012345678",
                "ANTHROPIC_API_KEY": "sk-ant-api-test-key-12345",
                "MAX_TOKENS": "1000",  # Include MAX_TOKENS from .env
                "ANALYSIS_TIMEOUT": "45",  # Include ANALYSIS_TIMEOUT from .env
            },
        ):
            config = Config()

            # Test default values
            assert config.analysis.template_threshold_days == 730
            assert config.analysis.min_commits_for_ai == 3
            assert config.analysis.anthropic_model == DEFAULT_ANTHROPIC_MODEL
            assert config.analysis.max_tokens == 1000
            assert config.analysis.analysis_timeout == 45
            assert config.analysis.temperature == 0.0

            assert config.cost.max_cost_per_user_daily == 0.50
            assert config.cost.cost_tracking_enabled is True

            assert config.security.rate_limit_enabled is True
            assert config.security.default_rate_limit == 100
            assert config.security.allowed_domains == ["github.com"]

            assert config.cache.enabled is True
            assert config.cache.default_ttl == 3600

            # Multi-model configuration now in tier_config.py

    def test_config_custom_values(self):
        """Test configuration with custom environment values."""
        with patch.dict(
            os.environ,
            {
                "GITHUB_TOKEN": "ghp_test_token_1234567890123456789012345678",
                "ANTHROPIC_API_KEY": "sk-ant-api-test-key-12345",
                "TEMPLATE_THRESHOLD_DAYS": "365",
                "MIN_COMMITS_FOR_AI": "5",
                "MAX_TOKENS": "500",
                "ANALYSIS_TIMEOUT": "45",
                "MAX_COST_PER_USER_DAILY": "1.00",
                "DEFAULT_RATE_LIMIT": "200",
            },
        ):
            config = Config()

            assert config.analysis.template_threshold_days == 365
            assert config.analysis.min_commits_for_ai == 5
            assert config.analysis.max_tokens == 500
            assert config.analysis.analysis_timeout == 45
            assert config.cost.max_cost_per_user_daily == 1.00
            assert config.security.default_rate_limit == 200

    def test_config_boolean_parsing(self):
        """Test boolean environment variable parsing."""
        test_cases = [
            ("true", True),
            ("True", True),
            ("1", True),
            ("yes", True),
            ("on", True),
            ("false", False),
            ("False", False),
            ("0", False),
            ("no", False),
            ("of", False),
            ("invalid", False),  # Default to False for invalid values
        ]

        for value, expected in test_cases:
            with patch.dict(
                os.environ,
                {
                    "GITHUB_TOKEN": "ghp_test_token_1234567890123456789012345678",
                    "ANTHROPIC_API_KEY": "sk-ant-api-test-key-12345",
                    "DEBUG": value,
                },
            ):
                config = Config()
                assert config.debug == expected, f"Failed for value: {value}"

    def test_config_validation(self):
        """Test configuration validation method."""
        with patch.dict(
            os.environ,
            {
                "GITHUB_TOKEN": "ghp_test_token_1234567890123456789012345678",
                "ANTHROPIC_API_KEY": "sk-ant-api-test-key-12345",
            },
        ):
            config = Config()

            # Should validate successfully
            assert config.validate() is True

    def test_config_validation_invalid_tokens(self):
        """Test configuration validation with invalid token formats."""
        with patch.dict(
            os.environ,
            {
                "GITHUB_TOKEN": "invalid_token",
                "ANTHROPIC_API_KEY": "sk-ant-api-test-key-12345",
            },
        ):
            config = Config()

            with pytest.raises(ValueError) as exc_info:
                config.validate()

            assert "Invalid GitHub token format" in str(exc_info.value)

    def test_config_validation_invalid_values(self):
        """Test configuration validation with invalid parameter values."""
        with patch.dict(
            os.environ,
            {
                "GITHUB_TOKEN": "ghp_test_token_1234567890123456789012345678",
                "ANTHROPIC_API_KEY": "sk-ant-api-test-key-12345",
                "MAX_TOKENS": "0",  # Invalid value
                "ANALYSIS_TIMEOUT": "-5",  # Invalid value
            },
        ):
            config = Config()

            with pytest.raises(ValueError) as exc_info:
                config.validate()

            error_message = str(exc_info.value)
            assert (
                "max_tokens must be between 1 and 4000" in error_message
                or "analysis_timeout must be positive" in error_message
            )

    def test_config_to_dict(self):
        """Test configuration serialization to dictionary."""
        with patch.dict(
            os.environ,
            {
                "GITHUB_TOKEN": "ghp_test_token_1234567890123456789012345678",
                "ANTHROPIC_API_KEY": "sk-ant-api-test-key-12345",
                "ENVIRONMENT": "test",
            },
        ):
            config = Config()
            config_dict = config.to_dict()

            # Should not contain sensitive information
            assert "github_token" not in config_dict
            assert "anthropic_api_key" not in config_dict

            # Should contain non-sensitive configuration
            assert config_dict["environment"] == "test"
            assert "analysis" in config_dict
            assert "cost" in config_dict
            assert "security" in config_dict
            assert "cache" in config_dict

    @patch("github_analyzer.utils.config.load_dotenv")
    def test_config_env_file_loading(self, mock_load_dotenv):
        """Test loading configuration from specific .env file."""
        with patch.dict(
            os.environ,
            {
                "GITHUB_TOKEN": "ghp_test_token_1234567890123456789012345678",
                "ANTHROPIC_API_KEY": "sk-ant-api-test-key-12345",
            },
        ):
            Config(env_file="/custom/.env")
            mock_load_dotenv.assert_called_once_with("/custom/.env")


class TestConfigGlobalFunctions:
    """Test global configuration functions."""

    def test_get_config_singleton(self):
        """Test that get_config returns the same instance."""
        with patch.dict(
            os.environ,
            {
                "GITHUB_TOKEN": "ghp_test_token_1234567890123456789012345678",
                "ANTHROPIC_API_KEY": "sk-ant-api-test-key-12345",
            },
        ):
            # Clear any existing global config
            import github_analyzer.utils.config as config_module

            config_module._config = None

            config1 = get_config()
            config2 = get_config()

            assert config1 is config2  # Same instance

    def test_reload_config(self):
        """Test configuration reloading."""
        with patch.dict(
            os.environ,
            {
                "GITHUB_TOKEN": "ghp_test_token_1234567890123456789012345678",
                "ANTHROPIC_API_KEY": "sk-ant-api-test-key-12345",
            },
        ):
            # Clear any existing global config
            import github_analyzer.utils.config as config_module

            config_module._config = None

            config1 = get_config()
            config2 = reload_config()

            assert config1 is not config2  # Different instances after reload


# Integration-style tests
class TestConfigIntegration:
    """Integration tests for configuration management."""

    def test_config_with_real_env_structure(self):
        """Test configuration loading mimicking real environment setup."""
        # Simulate a realistic .env file setup
        env_vars = {
            "GITHUB_TOKEN": "ghp_realistic_token_example_1234567890123456",
            "ANTHROPIC_API_KEY": "sk-ant-api-realistic-example-key-12345",
            "ENVIRONMENT": "development",
            "DEBUG": "true",
            "TEMPLATE_THRESHOLD_DAYS": "365",
            "MAX_COST_PER_USER_DAILY": "0.25",
            "RATE_LIMIT_ENABLED": "true",
            "DEFAULT_RATE_LIMIT": "50",
        }

        with patch.dict(os.environ, env_vars):
            config = Config()

            # Validate all settings are loaded correctly
            assert config.environment == "development"
            assert config.debug is True
            assert config.analysis.template_threshold_days == 365
            assert config.cost.max_cost_per_user_daily == 0.25
            assert config.security.rate_limit_enabled is True
            assert config.security.default_rate_limit == 50

            # Validate configuration
            assert config.validate() is True

            # Test serialization
            config_dict = config.to_dict()
            assert isinstance(config_dict, dict)
            assert len(config_dict) > 0

    def test_tier_config_integration(self):
        """Test that tier configuration is now handled by tier_config module."""
        with patch.dict(
            os.environ,
            {
                "GITHUB_TOKEN": "ghp_test_token_1234567890123456789012345678",
                "ANTHROPIC_API_KEY": "sk-ant-api-test-key-12345",
            },
        ):
            config = Config()

            # These model configurations are no longer in config.py
            # They are now managed by tier_config.py
            assert not hasattr(config.analysis, "growth_metrics_model")
            assert not hasattr(config.analysis, "growth_questions_model")
            assert not hasattr(config.analysis, "scale_metrics_model")
            assert not hasattr(config.analysis, "scale_questions_model")
            assert not hasattr(config.analysis, "enterprise_question_tokens")

            # Only base model and minimal token configs remain
            assert hasattr(config.analysis, "anthropic_model")
            assert hasattr(config.analysis, "max_tokens")
            assert hasattr(config.analysis, "quick_check_tokens")
