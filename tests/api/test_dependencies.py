"""
Tests for API dependencies.

This module tests the shared dependencies used across API endpoints
including URL validation, rate limiting, and utility functions.
"""

from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from pydantic import HttpUrl

from github_analyzer.api.dependencies import (
    check_rate_limit,
    generate_cache_key,
    get_client_ip,
    validate_batch_size,
    validate_github_url,
)


class TestValidateGithubUrl:
    """Test GitHub URL validation."""

    def test_valid_github_urls(self):
        """Test that valid GitHub URLs are accepted."""
        valid_urls = [
            "https://github.com/user/repo",
            "https://github.com/organization/project",
            "https://github.com/user-name/repo-name",
            "https://github.com/user123/repo_with_underscores",
            "http://github.com/user/repo",  # HTTP should work
        ]

        for url in valid_urls:
            result = validate_github_url(HttpUrl(url))
            assert result.startswith("https://github.com/")
            assert len(result.split("/")) >= 5  # https://github.com/user/repo

    def test_github_url_normalization(self):
        """Test that GitHub URLs are properly normalized."""
        test_cases = [
            ("https://github.com/user/repo/", "https://github.com/user/repo"),
            ("https://github.com/user/repo#readme", "https://github.com/user/repo"),
            ("https://github.com/user/repo?tab=readme", "https://github.com/user/repo"),
            ("https://github.com/user/repo/issues", "https://github.com/user/repo"),
            ("http://github.com/user/repo", "https://github.com/user/repo"),
        ]

        for input_url, expected in test_cases:
            result = validate_github_url(HttpUrl(input_url))
            assert result == expected

    def test_invalid_github_urls(self):
        """Test that invalid GitHub URLs are rejected."""
        invalid_urls = [
            "https://gitlab.com/user/repo",
            "https://bitbucket.org/user/repo",
            "https://example.com/user/repo",
            "https://github.com/",
            "https://github.com/user",
            "https://github.com/user/",
        ]

        for url in invalid_urls:
            with pytest.raises(HTTPException) as exc_info:
                validate_github_url(HttpUrl(url))

            assert exc_info.value.status_code == 400

    def test_non_github_domain_rejection(self):
        """Test that non-GitHub domains are rejected."""
        with pytest.raises(HTTPException) as exc_info:
            validate_github_url(HttpUrl("https://example.com/user/repo"))

        assert exc_info.value.status_code == 400
        assert "GitHub repository URL" in exc_info.value.detail

    def test_incomplete_github_urls(self):
        """Test that incomplete GitHub URLs are rejected."""
        incomplete_urls = [
            "https://github.com/",
            "https://github.com/user",
            "https://github.com/user/",
        ]

        for url in incomplete_urls:
            with pytest.raises(HTTPException) as exc_info:
                validate_github_url(HttpUrl(url))

            assert exc_info.value.status_code == 400
            assert "specific repository" in exc_info.value.detail


class TestGenerateCacheKey:
    """Test cache key generation."""

    def test_cache_key_consistency(self):
        """Test that same inputs produce same cache keys."""
        url = "https://github.com/user/repo"
        context = "general"

        key1 = generate_cache_key(url, context)
        key2 = generate_cache_key(url, context)

        assert key1 == key2
        assert key1.startswith("analysis:")

    def test_different_urls_different_keys(self):
        """Test that different URLs produce different cache keys."""
        url1 = "https://github.com/user/repo1"
        url2 = "https://github.com/user/repo2"
        context = "general"

        key1 = generate_cache_key(url1, context)
        key2 = generate_cache_key(url2, context)

        assert key1 != key2

    def test_different_contexts_different_keys(self):
        """Test that different contexts produce different cache keys."""
        url = "https://github.com/user/repo"

        key1 = generate_cache_key(url, "general")
        key2 = generate_cache_key(url, "startup")

        assert key1 != key2

    def test_cache_key_format(self):
        """Test that cache keys have the expected format."""
        url = "https://github.com/user/repo"
        context = "enterprise"

        key = generate_cache_key(url, context)

        assert key.startswith("analysis:")
        assert len(key.split(":")) == 2
        # MD5 hash should be 32 characters
        assert len(key.split(":")[1]) == 32


class TestGetClientIp:
    """Test client IP extraction."""

    @pytest.mark.asyncio
    async def test_get_client_ip_from_forwarded_for(self):
        """Test IP extraction from X-Forwarded-For header."""
        mock_request = Mock()
        mock_request.headers = {"X-Forwarded-For": "192.168.1.1, 10.0.0.1"}

        ip = await get_client_ip(mock_request)
        assert ip == "192.168.1.1"

    @pytest.mark.asyncio
    async def test_get_client_ip_from_real_ip(self):
        """Test IP extraction from X-Real-IP header."""
        mock_request = Mock()
        mock_request.headers = {"X-Real-IP": "192.168.1.100"}

        ip = await get_client_ip(mock_request)
        assert ip == "192.168.1.100"

    @pytest.mark.asyncio
    async def test_get_client_ip_from_client_host(self):
        """Test IP extraction from client.host."""
        mock_request = Mock()
        mock_request.headers = {}
        mock_request.client.host = "192.168.1.50"

        ip = await get_client_ip(mock_request)
        assert ip == "192.168.1.50"

    @pytest.mark.asyncio
    async def test_get_client_ip_no_client(self):
        """Test IP extraction when no client info is available."""
        mock_request = Mock()
        mock_request.headers = {}
        mock_request.client = None

        ip = await get_client_ip(mock_request)
        assert ip == "unknown"

    @pytest.mark.asyncio
    async def test_forwarded_for_precedence(self):
        """Test that X-Forwarded-For takes precedence over other headers."""
        mock_request = Mock()
        mock_request.headers = {
            "X-Forwarded-For": "192.168.1.1",
            "X-Real-IP": "192.168.1.2",
        }
        mock_request.client.host = "192.168.1.3"

        ip = await get_client_ip(mock_request)
        assert ip == "192.168.1.1"


class TestCheckRateLimit:
    """Test rate limiting functionality."""

    @pytest.mark.asyncio
    async def test_rate_limit_placeholder(self):
        """Test that rate limit check is currently a no-op."""
        # This should not raise an exception for Phase 1
        await check_rate_limit("192.168.1.1")
        await check_rate_limit("192.168.1.1", 100, 1000)

    @pytest.mark.asyncio
    async def test_rate_limit_logging(self):
        """Test that rate limit check logs properly."""
        # For Phase 1, rate limiting is a no-op that just logs
        # In Phase 2, this will be implemented with Redis
        await check_rate_limit("192.168.1.1", 60, 1000)


class TestValidateBatchSize:
    """Test batch size validation."""

    def test_valid_batch_sizes(self):
        """Test that valid batch sizes are accepted."""
        valid_batches = [
            ["url1"],
            ["url1", "url2"],
            ["url1", "url2", "url3", "url4", "url5"],
            ["url"] * 10,  # Maximum size
        ]

        for batch in valid_batches:
            # Should not raise an exception
            validate_batch_size(batch)

    def test_empty_batch_rejected(self):
        """Test that empty batches are rejected."""
        with pytest.raises(HTTPException) as exc_info:
            validate_batch_size([])

        assert exc_info.value.status_code == 400
        assert "at least one repository" in exc_info.value.detail

    def test_oversized_batch_rejected(self):
        """Test that oversized batches are rejected."""
        oversized_batch = ["url"] * 11  # Default max is 10

        with pytest.raises(HTTPException) as exc_info:
            validate_batch_size(oversized_batch)

        assert exc_info.value.status_code == 400
        assert "cannot exceed 10" in exc_info.value.detail

    def test_custom_max_size(self):
        """Test batch validation with custom max size."""
        batch = ["url"] * 5

        # Should pass with max_size=5
        validate_batch_size(batch, max_size=5)

        # Should fail with max_size=4
        with pytest.raises(HTTPException) as exc_info:
            validate_batch_size(batch, max_size=4)

        assert exc_info.value.status_code == 400
        assert "cannot exceed 4" in exc_info.value.detail
