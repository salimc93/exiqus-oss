# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Configuration management for Exiqus.

This module handles environment variables, settings, and configuration
for the AI-powered developer assessment platform.
"""

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# The Anthropic model every analysis uses unless ANTHROPIC_MODEL overrides it.
#
# Exiqus ran as a SaaS and pinned a different model to each paid tier. As an
# open-source project there is one operator paying for one API key, so the model
# is a deployment choice rather than a product tier: set ANTHROPIC_MODEL once and
# every tier uses it. See docs in README for the current model IDs.
DEFAULT_ANTHROPIC_MODEL = "claude-opus-4-8"


@dataclass
class AnalysisConfig:
    """Configuration for analysis parameters."""

    template_threshold_days: int = 730  # Use templates for repos inactive >2 years
    min_commits_for_ai: int = 3  # Use templates for repos with <3 commits
    anthropic_model: str = DEFAULT_ANTHROPIC_MODEL
    # Token limits (defaults, tier-specific in tier_config.py)
    max_tokens: int = 1000  # Default/fallback
    quick_check_tokens: int = 100  # Simple validations
    analysis_timeout: int = 45  # seconds (quality over speed)
    temperature: float = 0.0  # Deterministic for analysis
    report_version: str = "1.0"  # Report version
    max_repo_size_mb: int = (
        100  # Maximum repository size in MB (deprecated, use plan limits)
    )
    max_repo_files: int = 100000  # Maximum number of files in repository
    max_concurrent_per_user: int = 3  # Max concurrent analyses per user
    max_concurrent_global: int = 10  # Max concurrent analyses system-wide
    # Budget monitoring (not strict limits)
    budget_warning_threshold: float = 0.8  # Warn at 80% of budget
    budget_critical_threshold: float = 0.9  # Critical alert at 90%
    estimated_cost_per_analysis: float = 0.002  # For cost estimation

    # Feature flags
    use_markdown_parsing: bool = True  # Use Markdown instead of JSON for AI responses

    # Plan-based repository size limits (in MB) - permanent limits, not monthly quotas
    # Tier-based limits: Free=50MB, Basic=1GB, Pro=3GB, Enterprise=5GB, Scale+=10GB
    repo_size_limits_mb: Dict[str, int] = field(
        default_factory=lambda: {
            "free": 50,  # 50MB max per repo
            "basic": 1000,  # 1GB max per repo
            "professional": 3000,  # 3GB max per repo
            "enterprise": 5000,  # 5GB max per repo
            "scale_plus": 10000,  # 10GB max per repo
        }
    )

    def get_plan_repo_size_limit(self, plan: str) -> int:
        """Get repository size limit for a subscription plan (in MB)."""
        if plan is None:
            return 50
        return self.repo_size_limits_mb.get(plan.strip().lower(), 50)


@dataclass
class CostConfig:
    """Configuration for cost tracking and limits."""

    max_cost_per_user_daily: float = 0.50
    cost_tracking_enabled: bool = True
    haiku_input_cost_per_token: float = 0.00025 / 1000  # $0.25 per million tokens
    haiku_output_cost_per_token: float = 0.00125 / 1000  # $1.25 per million tokens


@dataclass
class SecurityConfig:
    """Configuration for security settings."""

    rate_limit_enabled: bool = True
    default_rate_limit: int = 100  # requests per hour
    allowed_domains: Optional[List[str]] = None
    input_validation_strict: bool = True

    def __post_init__(self) -> None:
        if self.allowed_domains is None:
            self.allowed_domains = ["github.com"]


@dataclass
class CostStorageConfig:
    """Configuration for cost storage persistence."""

    enabled: bool = True
    storage_path: Optional[str] = None  # None = use default ~/.exiqus/costs/
    backend: str = "json"  # Options: "json" or "sqlite"
    rotation_days: int = 30  # Keep archived files for 30 days
    auto_export: bool = False  # Automatically export on rotation
    export_format: str = "csv"  # Format for auto-export


@dataclass
class CacheConfig:
    """Configuration for caching."""

    enabled: bool = True
    redis_url: str = "redis://localhost:6379"
    default_ttl: int = 3600  # 1 hour
    github_data_ttl: int = 7200  # 2 hours
    analysis_ttl: int = 86400  # 24 hours


class Config:
    """Main configuration class for GitHub Analyzer."""

    def __init__(
        self, env_file: Optional[str] = None, skip_validation: Optional[bool] = None
    ):
        """
        Initialize configuration.

        Args:
            env_file: Path to .env file. If None, uses default .env
            skip_validation: Skip environment variable validation (for testing).
                           None = auto-detect test mode, True = skip, False = force validation
        """
        self._load_environment(env_file)

        # Skip validation if explicitly requested or if in automatic test mode
        # Explicit skip_validation=False will force validation even in test mode
        if skip_validation is False:
            # Explicitly force validation even in test mode
            should_skip_validation = False
        elif skip_validation is True:
            # Explicitly skip validation
            should_skip_validation = True
        else:
            # Default behavior: skip in test mode, validate otherwise
            should_skip_validation = self._is_testing_mode()

        if not should_skip_validation:
            self._validate_required_vars()

        # Sub-configurations
        self.analysis = AnalysisConfig(
            template_threshold_days=self._get_int("TEMPLATE_THRESHOLD_DAYS", 730),
            min_commits_for_ai=self._get_int("MIN_COMMITS_FOR_AI", 3),
            anthropic_model=self._get_str("ANTHROPIC_MODEL", DEFAULT_ANTHROPIC_MODEL),
            max_tokens=self._get_int("MAX_TOKENS", 400),
            quick_check_tokens=self._get_int("QUICK_CHECK_TOKENS", 100),
            analysis_timeout=self._get_int("ANALYSIS_TIMEOUT", 30),
            temperature=self._get_float("TEMPERATURE", 0.0),
            max_repo_size_mb=self._get_int("MAX_REPO_SIZE_MB", 100),
            max_repo_files=self._get_int("MAX_REPO_FILES", 100000),
            max_concurrent_per_user=self._get_int("MAX_CONCURRENT_PER_USER", 3),
            max_concurrent_global=self._get_int("MAX_CONCURRENT_GLOBAL", 10),
            budget_warning_threshold=self._get_float("BUDGET_WARNING_THRESHOLD", 0.8),
            budget_critical_threshold=self._get_float("BUDGET_CRITICAL_THRESHOLD", 0.9),
            estimated_cost_per_analysis=self._get_float(
                "ESTIMATED_COST_PER_ANALYSIS", 0.002
            ),
        )

        self.cost = CostConfig(
            max_cost_per_user_daily=self._get_float("MAX_COST_PER_USER_DAILY", 0.50),
            cost_tracking_enabled=self._get_bool("COST_TRACKING_ENABLED", True),
        )

        self.security = SecurityConfig(
            rate_limit_enabled=self._get_bool("RATE_LIMIT_ENABLED", True),
            default_rate_limit=self._get_int("DEFAULT_RATE_LIMIT", 100),
            input_validation_strict=self._get_bool("INPUT_VALIDATION_STRICT", True),
        )

        self.cache = CacheConfig(
            enabled=self._get_bool("CACHE_ENABLED", True),
            redis_url=self._get_str("REDIS_URL", "redis://localhost:6379"),
            default_ttl=self._get_int("CACHE_DEFAULT_TTL", 3600),
            github_data_ttl=self._get_int("GITHUB_DATA_TTL", 7200),
            analysis_ttl=self._get_int("ANALYSIS_TTL", 86400),
        )

        # Add REDIS_URL as a direct attribute for backward compatibility
        self.REDIS_URL = self.cache.redis_url

        self.cost_storage = CostStorageConfig(
            enabled=self._get_bool("COST_STORAGE_ENABLED", True),
            storage_path=self._get_optional_str("COST_STORAGE_PATH"),
            backend=self._get_str("COST_STORAGE_BACKEND", "json"),
            rotation_days=self._get_int("COST_STORAGE_ROTATION_DAYS", 30),
            auto_export=self._get_bool("COST_STORAGE_AUTO_EXPORT", False),
            export_format=self._get_str("COST_STORAGE_EXPORT_FORMAT", "csv"),
        )

    def _is_testing_mode(self) -> bool:
        """Check if we're in testing mode."""
        return (
            os.getenv("TESTING", "").lower() in ("true", "1", "yes")
            or "pytest" in sys.modules
            or "unittest" in sys.modules
        )

    def _load_environment(self, env_file: Optional[str] = None) -> None:
        """Load environment variables from .env file."""
        if env_file:
            load_dotenv(env_file)
        else:
            # Try to find .env file in current directory or parent directories
            current_dir = Path.cwd()
            for parent in [current_dir] + list(current_dir.parents):
                env_path = parent / ".env"
                if env_path.exists():
                    load_dotenv(env_path)
                    break

    def _validate_required_vars(self) -> None:
        """Validate that required environment variables are set."""
        required_vars = ["GITHUB_TOKEN", "ANTHROPIC_API_KEY"]

        # Allow test tokens in CI/CD environment
        ci_test_tokens = {
            "GITHUB_TOKEN": [
                "ghp_test_token_for_ci_only",
                "ghp_test_token_1234567890123456789012345678",
            ],
            "ANTHROPIC_API_KEY": [
                "sk-ant-api-test-key-for-ci-only",
                "sk-ant-api-test-key-12345",
            ],
        }

        missing_vars = []
        for var in required_vars:
            value = os.getenv(var)
            if not value or value.startswith("your_"):
                missing_vars.append(var)
            elif var in ci_test_tokens and value in ci_test_tokens[var]:
                # Allow known test tokens in CI/CD
                continue

        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}\n"
                "Please set these in your .env file or environment."
            )

    def _get_str(self, key: str, default: str) -> str:
        """Get string environment variable with default."""
        return os.getenv(key, default)

    def _get_optional_str(
        self, key: str, default: Optional[str] = None
    ) -> Optional[str]:
        """Get optional string environment variable with default."""
        value = os.getenv(key)
        return value if value is not None else default

    def _get_int(self, key: str, default: int) -> int:
        """Get integer environment variable with default."""
        value = os.getenv(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            return default

    def _get_float(self, key: str, default: float) -> float:
        """Get float environment variable with default."""
        value = os.getenv(key)
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            return default

    def _get_bool(self, key: str, default: bool) -> bool:
        """Get boolean environment variable with default."""
        value = os.getenv(key)
        if value is None:
            return default
        return value.lower() in ("true", "1", "yes", "on")

    @property
    def github_token(self) -> str:
        """Get GitHub API token."""
        return os.getenv("GITHUB_TOKEN", "")

    @property
    def anthropic_api_key(self) -> str:
        """Get Anthropic API key."""
        return os.getenv("ANTHROPIC_API_KEY", "")

    @property
    def environment(self) -> str:
        """Get current environment (development, test, production)."""
        return os.getenv("ENVIRONMENT", "production")

    @property
    def debug(self) -> bool:
        """Get debug mode setting."""
        return self._get_bool("DEBUG", False)

    @property
    def database_url(self) -> str:
        """Get database URL.

        Defaults to the local docker-compose PostgreSQL
        (`docker compose up -d postgres`).
        """
        return os.getenv(
            "DATABASE_URL",
            "postgresql://github_analyzer:exiqus_dev_password"
            "@localhost:5432/github_analyzer",
        )

    @property
    def stripe_webhook_secret(self) -> str:
        """Get Stripe webhook secret."""
        return os.getenv("STRIPE_WEBHOOK_SECRET", "")

    @property
    def ADMIN_SECRET(self) -> str:
        """Get admin authentication secret."""
        return os.getenv("ADMIN_SECRET", "")

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary (excluding sensitive data)."""
        return {
            "environment": self.environment,
            "debug": self.debug,
            "analysis": {
                "template_threshold_days": self.analysis.template_threshold_days,
                "min_commits_for_ai": self.analysis.min_commits_for_ai,
                "anthropic_model": self.analysis.anthropic_model,
                "max_tokens": self.analysis.max_tokens,
                "analysis_timeout": self.analysis.analysis_timeout,
                "temperature": self.analysis.temperature,
                "max_repo_size_mb": self.analysis.max_repo_size_mb,
                "max_repo_files": self.analysis.max_repo_files,
                "max_concurrent_per_user": self.analysis.max_concurrent_per_user,
                "max_concurrent_global": self.analysis.max_concurrent_global,
                "budget_warning_threshold": self.analysis.budget_warning_threshold,
                "budget_critical_threshold": self.analysis.budget_critical_threshold,
                "estimated_cost_per_analysis": self.analysis.estimated_cost_per_analysis,
            },
            "cost": {
                "max_cost_per_user_daily": self.cost.max_cost_per_user_daily,
                "cost_tracking_enabled": self.cost.cost_tracking_enabled,
            },
            "security": {
                "rate_limit_enabled": self.security.rate_limit_enabled,
                "default_rate_limit": self.security.default_rate_limit,
                "allowed_domains": self.security.allowed_domains,
                "input_validation_strict": self.security.input_validation_strict,
            },
            "cache": {
                "enabled": self.cache.enabled,
                "default_ttl": self.cache.default_ttl,
                "github_data_ttl": self.cache.github_data_ttl,
                "analysis_ttl": self.cache.analysis_ttl,
            },
            "cost_storage": {
                "enabled": self.cost_storage.enabled,
                "backend": self.cost_storage.backend,
                "rotation_days": self.cost_storage.rotation_days,
                "auto_export": self.cost_storage.auto_export,
                "export_format": self.cost_storage.export_format,
                # Note: storage_path is not included for security
            },
        }

    def validate(self) -> bool:
        """Validate configuration settings."""
        try:
            # Check API keys are valid format
            if not self.github_token.startswith(("ghp_", "github_pat_")):
                raise ValueError("Invalid GitHub token format")

            if not self.anthropic_api_key.startswith("sk-ant-api"):
                raise ValueError("Invalid Anthropic API key format")

            # Check reasonable values
            if self.analysis.max_tokens <= 0 or self.analysis.max_tokens > 4000:
                raise ValueError("max_tokens must be between 1 and 4000")

            if self.analysis.analysis_timeout <= 0:
                raise ValueError("analysis_timeout must be positive")

            if self.cost.max_cost_per_user_daily < 0:
                raise ValueError("max_cost_per_user_daily must be non-negative")

            return True

        except Exception as e:
            raise ValueError(f"Configuration validation failed: {e}")


# Global configuration instance
_config: Optional[Config] = None


def get_config(
    env_file: Optional[str] = None, skip_validation: Optional[bool] = None
) -> Config:
    """
    Get global configuration instance.

    Args:
        env_file: Path to .env file for initial load
        skip_validation: Skip environment variable validation (for testing).
                        None = auto-detect test mode, True = skip, False = force validation

    Returns:
        Global Config instance
    """
    global _config
    if _config is None:
        _config = Config(env_file, skip_validation=skip_validation)
    return _config


def reload_config(
    env_file: Optional[str] = None, skip_validation: Optional[bool] = None
) -> Config:
    """
    Reload configuration (useful for testing).

    Args:
        env_file: Path to .env file
        skip_validation: Skip environment variable validation (for testing).
                        None = auto-detect test mode, True = skip, False = force validation

    Returns:
        New Config instance
    """
    global _config
    _config = Config(env_file, skip_validation=skip_validation)
    return _config
