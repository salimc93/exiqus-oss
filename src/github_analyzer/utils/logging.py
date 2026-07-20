# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Logging configuration for Exiqus.

This module provides structured logging setup with appropriate
log levels, formatting, and security considerations.
"""

import json
import logging
import logging.handlers
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import get_config


class SecurityFilter(logging.Filter):
    """Filter to remove sensitive information from logs."""

    SENSITIVE_KEYS = [
        "api_key",
        "token",
        "password",
        "secret",
        "auth",
        "anthropic_api_key",
        "github_token",
        "authorization",
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter sensitive information from log records."""
        import re

        if hasattr(record, "msg"):
            # Convert message to string for processing
            msg = str(record.msg)

            # Pattern for GitHub tokens (ghp_ followed by variable length)
            msg = re.sub(r"ghp_[a-zA-Z0-9]+", "ghp_[REDACTED]", msg)

            # Pattern for Anthropic API keys
            msg = re.sub(r"sk-ant-api[0-9]*-[a-zA-Z0-9-]+", "sk-ant-api[REDACTED]", msg)

            # General pattern for long alphanumeric strings that might be keys
            msg = re.sub(r"\b[a-zA-Z0-9]{32,}\b", "[REDACTED]", msg)

            record.msg = msg

        return True


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        try:
            log_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "module": getattr(record, "module", "unknown"),
                "function": getattr(record, "funcName", "unknown"),
                "line": getattr(record, "lineno", 0),
            }

            # Add all extra fields from record
            # Skip standard logging fields and internal fields
            standard_fields = {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "getMessage",
                "message",
                "taskName",
            }

            for key, value in record.__dict__.items():
                if key not in standard_fields and not key.startswith("_"):
                    log_data[key] = value

            # Add exception info if present
            if record.exc_info:
                log_data["exception"] = self.formatException(record.exc_info)

            return json.dumps(log_data)
        except Exception:
            # Fallback to simple format if JSON formatting fails
            return (
                f"{datetime.now(timezone.utc).isoformat()} - "
                f"{record.levelname} - {record.getMessage()}"
            )


def setup_logging(
    level: Optional[str] = None,
    log_file: Optional[str] = None,
    enable_json: bool = False,
    enable_console: bool = True,
) -> logging.Logger:
    """
    Set up logging configuration for GitHub Analyzer.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file. If None, uses default location
        enable_json: Whether to use JSON formatting
        enable_console: Whether to log to console

    Returns:
        Configured logger instance
    """
    config = get_config()

    # Determine log level
    if level is None:
        level = "DEBUG" if config.debug else "INFO"

    # Create logger
    logger = logging.getLogger("github_analyzer")
    logger.setLevel(getattr(logging, level.upper()))

    # Close and clear existing handlers to prevent resource leaks
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)

    # Add security filter
    security_filter = SecurityFilter()

    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)

        if enable_json:
            console_handler.setFormatter(JSONFormatter())
        else:
            console_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            console_handler.setFormatter(console_formatter)

        console_handler.addFilter(security_filter)
        logger.addHandler(console_handler)

    # File handler
    if log_file or config.environment == "production":
        if log_file is None:
            # Default log file location
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            log_file = str(log_dir / "github_analyzer.log")
        else:
            # Ensure parent directory exists for provided log file
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

        # Rotating file handler (10MB max, keep 5 files)
        file_handler = logging.handlers.RotatingFileHandler(
            str(log_file),
            maxBytes=10 * 1024 * 1024,
            backupCount=5,  # 10MB
        )

        if enable_json:
            file_handler.setFormatter(JSONFormatter())
        else:
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - "
                "%(module)s:%(funcName)s:%(lineno)d - %(message)s"
            )
            file_handler.setFormatter(file_formatter)

        file_handler.addFilter(security_filter)
        logger.addHandler(file_handler)

    # Set up specific loggers for different components
    _setup_component_loggers(level)

    logger.info(
        f"Logging initialized - Level: {level}, Environment: {config.environment}"
    )

    return logger


def _setup_component_loggers(level: str) -> None:
    """Set up loggers for specific components."""
    components = [
        "github_analyzer.core",
        "github_analyzer.data",
        "github_analyzer.ai",
        "github_analyzer.utils",
        "github_analyzer.cli",
    ]

    for component in components:
        component_logger = logging.getLogger(component)
        component_logger.setLevel(getattr(logging, level.upper()))


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(f"github_analyzer.{name}")


# Security-aware logging helpers
def log_api_call(
    logger: logging.Logger,
    service: str,
    endpoint: str,
    response_time: float,
    status_code: Optional[int] = None,
    cost: Optional[float] = None,
) -> None:
    """
    Log API call with security and performance information.

    Args:
        logger: Logger instance
        service: Service name (github, anthropic)
        endpoint: API endpoint called
        response_time: Response time in seconds
        status_code: HTTP status code
        cost: API call cost in USD
    """
    # Create a custom LogRecord with extra fields
    record = logger.makeRecord(
        logger.name,
        logging.INFO,
        "(unknown file)",
        0,
        f"API call to {service}: {endpoint} - {response_time:.3f}s",
        (),
        None,
    )

    # Add extra fields directly to the record
    record.service = service
    record.endpoint = endpoint
    record.response_time = response_time

    if status_code:
        record.status_code = status_code
    if cost:
        record.cost = cost

    logger.handle(record)


def log_analysis_start(
    logger: logging.Logger, repository_url: str, user_id: Optional[str] = None
) -> None:
    """
    Log start of repository analysis.

    Args:
        logger: Logger instance
        repository_url: Repository URL being analyzed
        user_id: User ID if available
    """
    record = logger.makeRecord(
        logger.name,
        logging.INFO,
        "(unknown file)",
        0,
        f"Starting analysis for repository: {repository_url}",
        (),
        None,
    )

    record.repository_url = repository_url
    if user_id:
        record.user_id = user_id

    logger.handle(record)


def log_analysis_complete(
    logger: logging.Logger,
    repository_url: str,
    analysis_time: float,
    verdict: str,
    cost: Optional[float] = None,
    user_id: Optional[str] = None,
) -> None:
    """
    Log completion of repository analysis.

    Args:
        logger: Logger instance
        repository_url: Repository URL analyzed
        analysis_time: Total analysis time in seconds
        verdict: Analysis verdict
        cost: Total cost in USD
        user_id: User ID if available
    """
    record = logger.makeRecord(
        logger.name,
        logging.INFO,
        "(unknown file)",
        0,
        f"Analysis complete for {repository_url}: {verdict} ({analysis_time:.2f}s)",
        (),
        None,
    )

    record.repository_url = repository_url
    record.analysis_time = analysis_time
    record.verdict = verdict

    if cost:
        record.cost = cost
    if user_id:
        record.user_id = user_id

    logger.handle(record)


def log_security_event(
    logger: logging.Logger,
    event_type: str,
    description: str,
    severity: str = "WARNING",
    ip_address: Optional[str] = None,
    user_id: Optional[str] = None,
) -> None:
    """
    Log security-related events.

    Args:
        logger: Logger instance
        event_type: Type of security event
        description: Event description
        severity: Event severity (INFO, WARNING, ERROR, CRITICAL)
        ip_address: Client IP address
        user_id: User ID if available
    """
    level = getattr(logging, severity.upper())
    record = logger.makeRecord(
        logger.name,
        level,
        "(unknown file)",
        0,
        f"Security event [{event_type}]: {description}",
        (),
        None,
    )

    record.event_type = event_type
    record.security_event = True

    if ip_address:
        record.ip_address = ip_address
    if user_id:
        record.user_id = user_id

    logger.handle(record)
