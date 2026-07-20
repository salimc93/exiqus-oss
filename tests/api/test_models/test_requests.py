"""
Tests for API request models.

This module tests Pydantic models for API request validation
and data parsing.
"""

import pytest
from pydantic import ValidationError

from github_analyzer.api.models.requests import (
    AnalyzeRequest,
    BatchAnalyzeRequest,
    CacheInvalidateRequest,
)
from github_analyzer.core.context_analyzer import AnalysisContext


class TestAnalyzeRequest:
    """Test AnalyzeRequest model."""

    def test_valid_analyze_request(self):
        """Test creation of valid analyze request."""
        data = {
            "repository_url": "https://github.com/user/repo",
            "context": "general",
            "force_refresh": False,
        }

        request = AnalyzeRequest(**data)

        assert str(request.repository_url) == "https://github.com/user/repo"
        assert request.context == AnalysisContext.GENERAL
        assert request.force_refresh is False

    def test_analyze_request_defaults(self):
        """Test default values for analyze request."""
        data = {"repository_url": "https://github.com/user/repo"}

        request = AnalyzeRequest(**data)

        assert request.context == AnalysisContext.GENERAL
        assert request.force_refresh is False

    def test_analyze_request_with_all_contexts(self):
        """Test analyze request with different hiring contexts."""
        contexts = ["general", "startup", "enterprise", "agency", "open_source"]

        for context in contexts:
            data = {
                "repository_url": "https://github.com/user/repo",
                "context": context,
            }

            request = AnalyzeRequest(**data)
            assert request.context.value == context

    def test_invalid_github_url(self):
        """Test that invalid GitHub URLs are rejected."""
        invalid_urls = [
            "https://gitlab.com/user/repo",
            "https://example.com/user/repo",
            "not-a-url",
            "github.com/user/repo",  # Missing protocol
        ]

        for url in invalid_urls:
            data = {"repository_url": url}

            with pytest.raises(ValidationError) as exc_info:
                AnalyzeRequest(**data)

            # Should have validation error for repository_url
            errors = exc_info.value.errors()
            assert any(error["loc"] == ("repository_url",) for error in errors)

    def test_github_url_validation_message(self):
        """Test GitHub URL validation error message."""
        data = {"repository_url": "https://gitlab.com/user/repo"}

        with pytest.raises(ValidationError) as exc_info:
            AnalyzeRequest(**data)

        errors = exc_info.value.errors()
        github_error = next(e for e in errors if e["loc"] == ("repository_url",))
        assert "GitHub repository URL" in github_error["msg"]

    def test_force_refresh_boolean(self):
        """Test force_refresh field accepts boolean values."""
        data = {"repository_url": "https://github.com/user/repo", "force_refresh": True}

        request = AnalyzeRequest(**data)
        assert request.force_refresh is True


class TestBatchAnalyzeRequest:
    """Test BatchAnalyzeRequest model."""

    def test_valid_batch_request(self):
        """Test creation of valid batch analyze request."""
        data = {
            "repositories": [
                {
                    "repository_url": "https://github.com/user/repo1",
                    "context": "startup",
                },
                {
                    "repository_url": "https://github.com/user/repo2",
                    "context": "startup",
                },
                {
                    "repository_url": "https://github.com/user/repo3",
                    "context": "startup",
                },
            ]
        }

        request = BatchAnalyzeRequest(**data)

        assert len(request.repositories) == 3
        assert all(
            str(repo.repository_url).startswith("https://github.com/")
            for repo in request.repositories
        )
        assert all(
            repo.context == AnalysisContext.STARTUP for repo in request.repositories
        )

    def test_batch_request_defaults(self):
        """Test default values for batch request."""
        data = {"repositories": [{"repository_url": "https://github.com/user/repo"}]}

        request = BatchAnalyzeRequest(**data)

        assert len(request.repositories) == 1
        assert request.repositories[0].context == AnalysisContext.GENERAL

    def test_batch_request_max_items(self):
        """Test that batch requests are limited to 10 items."""
        # This should pass (exactly 10 items)
        valid_repos = [
            {"repository_url": f"https://github.com/user/repo{i}"} for i in range(10)
        ]
        data = {"repositories": valid_repos}

        request = BatchAnalyzeRequest(**data)
        assert len(request.repositories) == 10

        # This should fail (11 items)
        invalid_repos = [
            {"repository_url": f"https://github.com/user/repo{i}"} for i in range(11)
        ]
        data = {"repositories": invalid_repos}

        with pytest.raises(ValidationError) as exc_info:
            BatchAnalyzeRequest(**data)

        errors = exc_info.value.errors()
        # Look for max_items validation error
        assert any(error["type"] == "too_long" for error in errors)

    def test_batch_request_validates_all_urls(self):
        """Test that all URLs in batch are validated."""
        data = {
            "repositories": [
                {"repository_url": "https://github.com/user/repo1"},
                {"repository_url": "https://gitlab.com/user/repo2"},  # Invalid
                {"repository_url": "https://github.com/user/repo3"},
            ]
        }

        with pytest.raises(ValidationError) as exc_info:
            BatchAnalyzeRequest(**data)

        errors = exc_info.value.errors()
        assert any("GitHub repository URL" in str(error) for error in errors)

    def test_empty_batch_request(self):
        """Test that empty batch requests are handled."""
        data = {"repositories": []}

        # This should create the object but might be caught by API validation
        request = BatchAnalyzeRequest(**data)
        assert len(request.repositories) == 0


class TestCacheInvalidateRequest:
    """Test CacheInvalidateRequest model."""

    def test_cache_invalidate_with_url(self):
        """Test cache invalidation request with specific URL."""
        data = {"repository_url": "https://github.com/user/repo"}

        request = CacheInvalidateRequest(**data)

        assert str(request.repository_url) == "https://github.com/user/repo"
        assert request.pattern is None

    def test_cache_invalidate_with_pattern(self):
        """Test cache invalidation request with pattern."""
        data = {"pattern": "analysis:*"}

        request = CacheInvalidateRequest(**data)

        assert request.repository_url is None
        assert request.pattern == "analysis:*"

    def test_cache_invalidate_empty(self):
        """Test cache invalidation request with no parameters."""
        request = CacheInvalidateRequest()

        assert request.repository_url is None
        assert request.pattern is None

    def test_cache_invalidate_both_parameters(self):
        """Test cache invalidation with both URL and pattern."""
        data = {
            "repository_url": "https://github.com/user/repo",
            "pattern": "analysis:user*",
        }

        request = CacheInvalidateRequest(**data)

        assert str(request.repository_url) == "https://github.com/user/repo"
        assert request.pattern == "analysis:user*"


class TestRequestModelIntegration:
    """Test request model integration and edge cases."""

    def test_analyze_request_json_serialization(self):
        """Test that request models can be serialized to JSON."""
        request = AnalyzeRequest(
            repository_url="https://github.com/user/repo",
            context="enterprise",
            force_refresh=True,
        )

        json_data = request.model_dump()

        assert str(json_data["repository_url"]) == "https://github.com/user/repo"
        assert json_data["context"] == AnalysisContext.ENTERPRISE
        assert json_data["force_refresh"] is True

    def test_batch_request_json_serialization(self):
        """Test batch request JSON serialization."""
        request = BatchAnalyzeRequest(
            repositories=[
                {
                    "repository_url": "https://github.com/user/repo1",
                    "context": "agency",
                },
                {
                    "repository_url": "https://github.com/user/repo2",
                    "context": "agency",
                },
            ]
        )

        json_data = request.model_dump()

        assert len(json_data["repositories"]) == 2
        assert all(
            repo["context"] == AnalysisContext.AGENCY
            for repo in json_data["repositories"]
        )

    def test_request_field_descriptions(self):
        """Test that request models have proper field descriptions."""
        # Test AnalyzeRequest schema
        schema = AnalyzeRequest.model_json_schema()
        properties = schema["properties"]

        assert "description" in properties["repository_url"]
        assert "description" in properties["context"]
        assert "description" in properties["force_refresh"]

        # Test BatchAnalyzeRequest schema
        schema = BatchAnalyzeRequest.model_json_schema()
        properties = schema["properties"]

        assert "description" in properties["repositories"]
        assert properties["repositories"]["maxItems"] == 10
