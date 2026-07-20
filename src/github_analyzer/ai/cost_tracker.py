# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Cost tracking and budget management for AI analysis.

This module tracks API usage, calculates costs, and enforces budget limits
to prevent unexpected charges from AI API usage.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from ..data.cost_storage import CostRecord, CostStorage, get_cost_storage
from ..utils.config import get_config
from ..utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class APIUsage:
    """Record of API usage for cost tracking."""

    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    timestamp: datetime

    def __post_init__(self) -> None:
        """Validate API usage data."""
        if self.input_tokens < 0:
            raise ValueError("Input tokens cannot be negative")
        if self.output_tokens < 0:
            raise ValueError("Output tokens cannot be negative")
        if self.cost < 0:
            raise ValueError("Cost cannot be negative")

    @property
    def total_tokens(self) -> int:
        """Calculate total tokens used."""
        return self.input_tokens + self.output_tokens


@dataclass
class DailyUsage:
    """Summary of daily API usage."""

    total_cost: float
    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    date: datetime

    @property
    def total_tokens(self) -> int:
        """Calculate total tokens for the day."""
        return self.total_input_tokens + self.total_output_tokens


@dataclass
class CostReport:
    """Comprehensive cost and usage report."""

    total_cost: float
    total_requests: int
    average_cost_per_request: float
    usage_by_model: Dict[str, int]
    period_start: datetime
    period_end: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "total_cost": self.total_cost,
            "total_requests": self.total_requests,
            "average_cost_per_request": self.average_cost_per_request,
            "usage_by_model": self.usage_by_model,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
        }


class CostTracker:
    """
    Tracks API usage and costs for budget management.

    Monitors daily spending, enforces limits, and provides usage analytics
    to prevent unexpected API charges.
    """

    # Model pricing (per 1000 tokens)
    MODEL_PRICING = {
        "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},  # Haiku 3.0
        "claude-3-5-haiku-20241022": {"input": 0.001, "output": 0.005},  # Haiku 3.5
        "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},  # Sonnet 3.5
        "claude-3-7-sonnet-20250219": {
            "input": 0.003,
            "output": 0.015,
        },  # Sonnet 3.7 (highest model)
    }

    def __init__(self, storage: Optional["CostStorage"] = None) -> None:
        """Initialize cost tracker with configuration and persistent storage."""
        self.config = get_config()
        self.usage_history: List[APIUsage] = []

        # Initialize cost storage for persistence
        if storage is not None:
            # Use provided storage (for testing)
            self.cost_storage: Optional[CostStorage] = storage
            self.persistence_enabled = getattr(storage, "enabled", False)
        else:
            # Use default storage
            try:
                self.cost_storage = get_cost_storage()
                self.persistence_enabled = getattr(self.cost_storage, "enabled", False)
            except Exception as e:
                logger.warning(f"Cost storage initialization failed: {e}")
                self.cost_storage = None
                self.persistence_enabled = False

        # Budget limits from configuration
        self.max_daily_cost = getattr(self.config.cost, "max_daily_cost", 10.0)
        self.max_cost_per_analysis = getattr(
            self.config.cost, "max_cost_per_analysis", 0.02
        )
        self.alert_threshold = getattr(self.config.cost, "alert_threshold", 0.8)

        logger.debug(
            f"Cost tracker initialized with daily limit: ${self.max_daily_cost}, "
            f"persistence: {'enabled' if self.persistence_enabled else 'disabled'}"
        )

    def track_analysis(self, usage: APIUsage) -> None:
        """
        Track API usage for an analysis with persistent storage.

        Args:
            usage: API usage details
        """
        # Add to in-memory history for backward compatibility
        self.usage_history.append(usage)

        # Persist to storage if enabled
        if self.persistence_enabled and self.cost_storage:
            try:
                cost_record = CostRecord(
                    timestamp=usage.timestamp.isoformat(),
                    model=usage.model,
                    operation="api_usage",  # Default operation type
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                    cost=usage.cost,
                    metadata={"total_tokens": usage.total_tokens},
                )
                self.cost_storage.save_cost(cost_record)
                logger.debug("Usage data persisted to storage")
            except Exception as e:
                logger.warning(f"Failed to persist usage data: {e}")

        logger.info(
            f"Tracked usage: {usage.model}, {usage.total_tokens} tokens, "
            f"${usage.cost:.4f}"
        )

        # Check if we should alert
        if self.should_alert():
            logger.warning(
                "Daily usage approaching limit: "
                f"${self.get_daily_usage().total_cost:.4f}"
            )

    def calculate_cost(
        self, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        """
        Calculate cost for API usage.

        Args:
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD

        Raises:
            ValueError: If model is not supported
        """
        if model not in self.MODEL_PRICING:
            logger.warning(
                f"Unknown model pricing for: {model}, using default Haiku pricing"
            )
            # Default to Haiku 3.0 pricing for unknown models
            pricing = self.MODEL_PRICING["claude-3-haiku-20240307"]
        else:
            pricing = self.MODEL_PRICING[model]
        input_cost = (input_tokens * pricing["input"]) / 1000
        output_cost = (output_tokens * pricing["output"]) / 1000

        total_cost = input_cost + output_cost
        logger.debug(
            f"Cost calculation: {input_tokens}+{output_tokens} tokens = "
            f"${total_cost:.6f}"
        )

        return total_cost

    def get_daily_usage(
        self, date: Optional[datetime] = None, use_persistent_data: bool = True
    ) -> DailyUsage:
        """
        Get usage summary for a specific day.

        Args:
            date: Date to get usage for (defaults to today)
            use_persistent_data: Whether to include data from persistent storage

        Returns:
            Daily usage summary
        """
        if date is None:
            date = datetime.now(timezone.utc)

        total_cost = 0.0
        total_requests = 0
        total_input_tokens = 0
        total_output_tokens = 0

        # Get data from persistent storage if enabled
        if use_persistent_data and self.persistence_enabled and self.cost_storage:
            try:
                summary = self.cost_storage.get_daily_summary(date)
                total_cost += summary["total_cost"]
                total_requests += summary["total_operations"]
                total_input_tokens += summary["total_input_tokens"]
                total_output_tokens += summary["total_output_tokens"]
                logger.debug(
                    f"Loaded persistent data: ${total_cost:.4f}, {total_requests} operations"
                )
            except Exception as e:
                logger.warning(f"Failed to load persistent data: {e}")

        # Also include in-memory data (for current session)
        day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        daily_usage = [
            usage
            for usage in self.usage_history
            if day_start <= usage.timestamp < day_end
        ]

        # Add in-memory data (avoiding double-counting if persistence is working)
        memory_cost = sum(usage.cost for usage in daily_usage)
        memory_requests = len(daily_usage)
        memory_input_tokens = sum(usage.input_tokens for usage in daily_usage)
        memory_output_tokens = sum(usage.output_tokens for usage in daily_usage)

        # If we have persistent data, only add memory data that's not persisted yet
        # For simplicity, we'll just use persistent data when available
        if not (
            use_persistent_data and self.persistence_enabled and total_requests > 0
        ):
            total_cost += memory_cost
            total_requests += memory_requests
            total_input_tokens += memory_input_tokens
            total_output_tokens += memory_output_tokens

        return DailyUsage(
            total_cost=total_cost,
            total_requests=total_requests,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            date=date,
        )

    def check_budget(self, estimated_cost: float) -> Tuple[bool, Optional[str]]:
        """
        Check if analysis is within budget limits.

        Args:
            estimated_cost: Estimated cost for the analysis

        Returns:
            Tuple of (is_within_budget, reason_if_not)
        """
        # Check per-analysis limit
        if estimated_cost > self.max_cost_per_analysis:
            return (
                False,
                f"Analysis cost ${estimated_cost:.4f} exceeds limit "
                f"${self.max_cost_per_analysis:.4f}",
            )

        # Check daily limit
        daily_usage = self.get_daily_usage()
        projected_daily_cost = daily_usage.total_cost + estimated_cost

        if projected_daily_cost > self.max_daily_cost:
            return (
                False,
                f"Daily cost would be ${projected_daily_cost:.4f}, exceeding limit "
                f"${self.max_daily_cost:.4f}",
            )

        return True, None

    def should_alert(self) -> bool:
        """
        Check if usage has reached alert threshold.

        Returns:
            True if alert should be sent
        """
        daily_usage = self.get_daily_usage()
        usage_percentage = daily_usage.total_cost / self.max_daily_cost

        return usage_percentage >= self.alert_threshold

    def get_cost_report(
        self, days: int = 7, use_persistent_data: bool = True
    ) -> CostReport:
        """
        Generate cost report for specified period with persistent data.

        Args:
            days: Number of days to include in report
            use_persistent_data: Whether to include data from persistent storage

        Returns:
            Comprehensive cost report
        """
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days)

        total_cost = 0.0
        total_requests = 0
        usage_by_model: Dict[str, int] = {}

        # Get data from persistent storage if enabled
        if use_persistent_data and self.persistence_enabled and self.cost_storage:
            try:
                # Get historical records from storage
                persistent_records = self.cost_storage.get_costs_by_date_range(
                    start_time, end_time
                )

                for record in persistent_records:
                    total_cost += record.cost
                    total_requests += 1
                    usage_by_model[record.model] = (
                        usage_by_model.get(record.model, 0) + 1
                    )

                logger.debug(
                    f"Loaded {len(persistent_records)} records from persistent storage"
                )
            except Exception as e:
                logger.warning(f"Failed to load persistent data for report: {e}")

        # Also include in-memory data (for current session)
        period_usage = [
            usage
            for usage in self.usage_history
            if start_time <= usage.timestamp <= end_time
        ]

        # Add in-memory data (only if we don't have persistent data or as fallback)
        if not (
            use_persistent_data and self.persistence_enabled and total_requests > 0
        ):
            memory_cost = sum(usage.cost for usage in period_usage)
            memory_requests = len(period_usage)

            total_cost += memory_cost
            total_requests += memory_requests

            # Count usage by model from memory
            for usage in period_usage:
                usage_by_model[usage.model] = usage_by_model.get(usage.model, 0) + 1

        average_cost = total_cost / total_requests if total_requests > 0 else 0.0

        return CostReport(
            total_cost=total_cost,
            total_requests=total_requests,
            average_cost_per_request=average_cost,
            usage_by_model=usage_by_model,
            period_start=start_time,
            period_end=end_time,
        )

    def reset_daily_usage(self) -> None:
        """Reset daily usage counters (for testing or manual reset)."""
        today = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        # Remove today's usage from history
        self.usage_history = [
            usage for usage in self.usage_history if usage.timestamp < today
        ]

        logger.info("Daily usage counters reset")

    def get_total_tokens(self) -> int:
        """Get total tokens used across all tracked usage."""
        return sum(usage.total_tokens for usage in self.usage_history)

    def get_total_requests(self) -> int:
        """Get total number of API requests made."""
        return len(self.usage_history)

    def get_usage_by_model(self) -> Dict[str, int]:
        """Get token usage breakdown by model."""
        usage_by_model: Dict[str, int] = {}
        for usage in self.usage_history:
            model = usage.model
            if model in usage_by_model:
                usage_by_model[model] += usage.total_tokens
            else:
                usage_by_model[model] = usage.total_tokens
        return usage_by_model

    def get_total_cost(self) -> float:
        """Get total cost across all tracked usage."""
        return sum(usage.cost for usage in self.usage_history)

    def track_api_call(self, model: str, input_tokens: int, output_tokens: int) -> None:
        """
        Track an individual API call.

        Args:
            model: Model name used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
        """
        # Use the calculate_cost method for consistency
        total_cost = self.calculate_cost(model, input_tokens, output_tokens)

        # Create usage record
        usage = APIUsage(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=total_cost,
            timestamp=datetime.now(timezone.utc),
        )

        self.track_analysis(usage)

    def get_historical_data(
        self, start_date: datetime, end_date: datetime
    ) -> List[CostRecord]:
        """
        Get historical cost data from persistent storage.

        Args:
            start_date: Start date for data retrieval
            end_date: End date for data retrieval

        Returns:
            List of cost records for the specified date range
        """
        if not self.persistence_enabled or not self.cost_storage:
            logger.warning("Persistent storage not available for historical data")
            return []

        try:
            return self.cost_storage.get_costs_by_date_range(start_date, end_date)
        except Exception as e:
            logger.error(f"Failed to retrieve historical data: {e}")
            return []

    def get_weekly_summary(self, weeks_back: int = 1) -> Dict[str, float]:
        """
        Get cost summary for previous weeks.

        Args:
            weeks_back: Number of weeks to look back

        Returns:
            Dictionary with weekly cost summaries
        """
        end_date = datetime.now(timezone.utc)
        summaries = {}

        for week in range(weeks_back):
            week_end = end_date - timedelta(weeks=week)
            week_start = week_end - timedelta(weeks=1)

            if self.persistence_enabled and self.cost_storage:
                try:
                    records = self.cost_storage.get_costs_by_date_range(
                        week_start, week_end
                    )
                    total_cost = sum(record.cost for record in records)
                    summaries[f"week_{week + 1}"] = total_cost
                except Exception as e:
                    logger.warning(f"Failed to get week {week + 1} summary: {e}")
                    summaries[f"week_{week + 1}"] = 0.0
            else:
                summaries[f"week_{week + 1}"] = 0.0

        return summaries

    def get_storage_status(self) -> Dict[str, Any]:
        """
        Get status information about cost storage.

        Returns:
            Dictionary with storage status information
        """
        status = {
            "persistence_enabled": self.persistence_enabled,
            "storage_available": self.cost_storage is not None,
            "storage_path": None,
            "current_session_records": len(self.usage_history),
        }

        if self.cost_storage:
            try:
                status["storage_path"] = str(
                    getattr(self.cost_storage, "storage_path", "unknown")
                )
                # Get today's summary to show storage is working
                if hasattr(self.cost_storage, "get_daily_summary"):
                    today_summary = self.cost_storage.get_daily_summary()
                    status["today_stored_records"] = today_summary["total_operations"]
                    status["today_stored_cost"] = today_summary["total_cost"]
            except Exception as e:
                status["storage_error"] = str(e)

        return status
