"""
Unit tests for logging functionality.

Tests logging setup, security filtering, and structured logging
components for the GitHub analyzer.
"""

import json
import logging
from io import StringIO
from unittest.mock import patch

import pytest

from github_analyzer.utils.logging import (
    JSONFormatter,
    SecurityFilter,
    get_logger,
    log_analysis_complete,
    log_analysis_start,
    log_api_call,
    log_security_event,
    setup_logging,
)


class TestSecurityFilter:
    """Test the SecurityFilter for removing sensitive information."""

    def setup_method(self):
        """Set up test fixtures."""
        self.filter = SecurityFilter()

    def test_filter_github_token(self):
        """Test filtering of GitHub tokens from log messages."""
        # Create a log record with GitHub token
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Using token: ghp_abcdefghijklmnopqrstuvwxyz123456789",
            args=(),
            exc_info=None,
        )

        # Apply filter
        self.filter.filter(record)

        # Token should be redacted
        assert "ghp_[REDACTED]" in str(record.msg)
        assert "ghp_abcdefghijklmnopqrstuvwxyz123456789" not in str(record.msg)

    def test_filter_anthropic_key(self):
        """Test filtering of Anthropic API keys from log messages."""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="API key: sk-ant-api03-abc123def456ghi789jkl012mno345",
            args=(),
            exc_info=None,
        )

        self.filter.filter(record)

        assert "sk-ant-api[REDACTED]" in str(record.msg)
        assert "sk-ant-api03-abc123def456ghi789jkl012mno345" not in str(record.msg)

    def test_filter_general_secrets(self):
        """Test filtering of general long alphanumeric strings."""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Secret value: abcdefghijklmnopqrstuvwxyz123456789012",
            args=(),
            exc_info=None,
        )

        self.filter.filter(record)

        # Long alphanumeric strings should be redacted
        assert "[REDACTED]" in str(record.msg)
        assert "abcdefghijklmnopqrstuvwxyz123456789012" not in str(record.msg)

    def test_filter_preserves_normal_text(self):
        """Test that normal text is preserved during filtering."""
        normal_messages = [
            "Starting analysis for repository",
            "Analysis completed successfully",
            "Rate limit: 4500/5000 remaining",
            "Processing commit sha: abc123",  # Short strings preserved
        ]

        for msg in normal_messages:
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg=msg,
                args=(),
                exc_info=None,
            )

            original_msg = str(record.msg)
            self.filter.filter(record)

            # Message should be unchanged
            assert str(record.msg) == original_msg

    def test_filter_mixed_content(self):
        """Test filtering messages with both normal and sensitive content."""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Authenticating with token ghp_secrettoken123456789012345678 "
            "for user analysis",
            args=(),
            exc_info=None,
        )

        self.filter.filter(record)

        # Should redact token but preserve other text
        filtered_msg = str(record.msg)
        assert "ghp_[REDACTED]" in filtered_msg
        assert "Authenticating with token" in filtered_msg
        assert "for user analysis" in filtered_msg
        assert "ghp_secrettoken123456789012345678" not in filtered_msg


class TestJSONFormatter:
    """Test the JSONFormatter for structured logging."""

    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = JSONFormatter()

    def test_basic_formatting(self):
        """Test basic JSON log formatting."""
        record = logging.LogRecord(
            name="github_analyzer.test",
            level=logging.INFO,
            pathname="/test/module.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.module = "module"
        record.funcName = "test_function"

        formatted = self.formatter.format(record)
        parsed = json.loads(formatted)

        # Check required fields
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "github_analyzer.test"
        assert parsed["message"] == "Test message"
        assert parsed["module"] == "module"
        assert parsed["function"] == "test_function"
        assert parsed["line"] == 42
        assert "timestamp" in parsed

    def test_extra_fields(self):
        """Test JSON formatting with extra fields."""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.module = "test"
        record.funcName = "test"

        # Add extra fields
        record.user_id = "user123"
        record.request_id = "req456"
        record.cost = 0.001
        record.repository_url = "https://github.com/user/repo"
        record.analysis_time = 12.5

        formatted = self.formatter.format(record)
        parsed = json.loads(formatted)

        # Check extra fields are included
        assert parsed["user_id"] == "user123"
        assert parsed["request_id"] == "req456"
        assert parsed["cost"] == 0.001
        assert parsed["repository_url"] == "https://github.com/user/repo"
        assert parsed["analysis_time"] == 12.5

    def test_exception_formatting(self):
        """Test JSON formatting with exception information."""
        import sys

        try:
            raise ValueError("Test exception")
        except ValueError:
            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="",
                lineno=0,
                msg="Error occurred",
                args=(),
                exc_info=sys.exc_info(),
            )
            record.module = "test"
            record.funcName = "test"

            formatted = self.formatter.format(record)
            parsed = json.loads(formatted)

            # Should include exception information
            assert "exception" in parsed
            assert "ValueError: Test exception" in parsed["exception"]


class TestLoggingSetup:
    """Test logging setup and configuration."""

    def test_setup_logging_basic(self):
        """Test basic logging setup."""
        with patch("github_analyzer.utils.logging.get_config") as mock_config:
            mock_config.return_value.debug = False
            mock_config.return_value.environment = "test"

            logger = setup_logging(level="INFO", enable_console=True, enable_json=False)

            assert logger.level == logging.INFO
            assert len(logger.handlers) > 0

    def test_setup_logging_debug_mode(self):
        """Test logging setup in debug mode."""
        # Clean up any existing handlers first
        root_logger = logging.getLogger("github_analyzer")
        root_logger.handlers.clear()
        root_logger.setLevel(logging.NOTSET)

        with patch("github_analyzer.utils.logging.get_config") as mock_config:
            mock_config.return_value.debug = True
            mock_config.return_value.environment = "development"

            logger = setup_logging(enable_console=True)

            assert logger.level == logging.DEBUG

    def test_setup_logging_json_format(self):
        """Test logging setup with JSON formatting."""
        with patch("github_analyzer.utils.logging.get_config") as mock_config:
            mock_config.return_value.debug = False
            mock_config.return_value.environment = "test"

            logger = setup_logging(enable_json=True, enable_console=True)

            # Should have JSON formatter
            console_handler = None
            for handler in logger.handlers:
                if isinstance(handler, logging.StreamHandler):
                    console_handler = handler
                    break

            assert console_handler is not None
            assert isinstance(console_handler.formatter, JSONFormatter)

    @patch("pathlib.Path.mkdir")
    def test_setup_logging_file_handler(self, mock_mkdir):
        """Test logging setup with file handler."""
        with patch("github_analyzer.utils.logging.get_config") as mock_config:
            mock_config.return_value.debug = False
            mock_config.return_value.environment = "production"

            logger = setup_logging(log_file="/tmp/test.log")

            # Should create log directory
            mock_mkdir.assert_called()

            # Should have file handler
            file_handler = None
            for handler in logger.handlers:
                if hasattr(handler, "baseFilename"):
                    file_handler = handler
                    break

            assert file_handler is not None

    def test_get_logger(self):
        """Test getting a named logger."""
        logger = get_logger("test_module")

        assert logger.name == "github_analyzer.test_module"
        assert isinstance(logger, logging.Logger)


class TestLoggingHelpers:
    """Test logging helper functions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.logger = logging.getLogger("test")
        self.logger.handlers.clear()

        # Add a string handler to capture log output
        self.log_capture = StringIO()
        handler = logging.StreamHandler(self.log_capture)
        handler.setFormatter(JSONFormatter())
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def test_log_api_call(self):
        """Test API call logging helper."""
        log_api_call(
            self.logger,
            service="github",
            endpoint="/repos/user/repo",
            response_time=1.23,
            status_code=200,
            cost=0.001,
        )

        log_output = self.log_capture.getvalue()
        parsed = json.loads(log_output.strip())

        assert "API call to github" in parsed["message"]
        assert parsed["service"] == "github"
        assert parsed["endpoint"] == "/repos/user/repo"
        assert parsed["response_time"] == 1.23
        assert parsed["status_code"] == 200
        assert parsed["cost"] == 0.001

    def test_log_analysis_start(self):
        """Test analysis start logging helper."""
        log_analysis_start(
            self.logger,
            repository_url="https://github.com/user/repo",
            user_id="user123",
        )

        log_output = self.log_capture.getvalue()
        parsed = json.loads(log_output.strip())

        assert "Starting analysis" in parsed["message"]
        assert parsed["repository_url"] == "https://github.com/user/repo"
        assert parsed["user_id"] == "user123"

    def test_log_analysis_complete(self):
        """Test analysis completion logging helper."""
        log_analysis_complete(
            self.logger,
            repository_url="https://github.com/user/repo",
            analysis_time=12.5,
            verdict="HIRE",
            cost=0.002,
            user_id="user123",
        )

        log_output = self.log_capture.getvalue()
        parsed = json.loads(log_output.strip())

        assert "Analysis complete" in parsed["message"]
        assert parsed["repository_url"] == "https://github.com/user/repo"
        assert parsed["analysis_time"] == 12.5
        assert parsed["verdict"] == "HIRE"
        assert parsed["cost"] == 0.002
        assert parsed["user_id"] == "user123"

    def test_log_security_event(self):
        """Test security event logging helper."""
        log_security_event(
            self.logger,
            event_type="rate_limit_exceeded",
            description="User exceeded rate limit",
            severity="WARNING",
            ip_address="192.168.1.1",
            user_id="user123",
        )

        log_output = self.log_capture.getvalue()
        parsed = json.loads(log_output.strip())

        assert "Security event [rate_limit_exceeded]" in parsed["message"]
        assert parsed["event_type"] == "rate_limit_exceeded"
        assert parsed["security_event"] is True
        assert parsed["ip_address"] == "192.168.1.1"
        assert parsed["user_id"] == "user123"


# Integration tests
class TestLoggingIntegration:
    """Integration tests for logging functionality."""

    def test_security_filter_in_real_setup(self):
        """Test that security filter works in real logging setup."""
        with patch("github_analyzer.utils.logging.get_config") as mock_config:
            mock_config.return_value.debug = False
            mock_config.return_value.environment = "test"

            # Capture log output
            log_capture = StringIO()

            with patch("sys.stdout", log_capture):
                logger = setup_logging(enable_console=True, enable_json=False)

                # Log a message with sensitive information
                logger.info(
                    "Using GitHub token: ghp_secret123456789012345678901234567890"
                )

                log_output = log_capture.getvalue()

                # Token should be redacted
                assert "ghp_[REDACTED]" in log_output
                assert "ghp_secret123456789012345678901234567890" not in log_output

    def test_json_logging_with_security(self):
        """Test JSON logging with security filtering."""
        with patch("github_analyzer.utils.logging.get_config") as mock_config:
            mock_config.return_value.debug = False
            mock_config.return_value.environment = "test"

            log_capture = StringIO()

            with patch("sys.stdout", log_capture):
                logger = setup_logging(enable_console=True, enable_json=True)

                # Log structured data with sensitive information
                logger.info("Authentication successful with key: sk-ant-api-secret123")

                log_output = log_capture.getvalue()

                # Should be valid JSON - parse the last line (user's message)
                lines = log_output.strip().split("\n")
                try:
                    # Parse the last log line (user message, not init message)
                    last_line = lines[-1]
                    parsed = json.loads(last_line)
                    assert "sk-ant-api[REDACTED]" in parsed["message"]
                    assert "sk-ant-api-secret123" not in parsed["message"]
                except json.JSONDecodeError:
                    pytest.fail("Log output is not valid JSON")
