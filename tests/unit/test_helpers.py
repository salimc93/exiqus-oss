"""
Unit tests for helper functions and utilities.

Tests utility functions for URL validation, cost calculation,
data processing, and formatting.
"""

from datetime import datetime, timezone

from github_analyzer.utils.helpers import (
    calculate_cost,
    calculate_days_between,
    extract_repo_info,
    format_analysis_result,
    get_file_extension,
    is_documentation_file,
    is_test_file,
    normalize_datetime,
    parse_github_languages,
    safe_json_dumps,
    safe_json_loads,
    sanitize_repo_name,
    truncate_text,
    validate_github_url,
)


class TestGitHubURLValidation:
    """Test GitHub URL validation functions."""

    def test_validate_github_url_valid_urls(self):
        """Test validation of valid GitHub URLs."""
        valid_urls = [
            "https://github.com/user/repo",
            "https://github.com/org-name/repo-name",
            "https://github.com/user123/repo_name",
            "https://github.com/user/repo.name",
            "https://github.com/a/b",  # Minimal valid case
        ]

        for url in valid_urls:
            assert validate_github_url(url), f"Should be valid: {url}"

    def test_validate_github_url_invalid_urls(self):
        """Test validation of invalid GitHub URLs."""
        invalid_urls = [
            "https://gitlab.com/user/repo",  # Wrong domain
            "https://github.com/user",  # Missing repo
            "https://github.com/",  # No user/repo
            "not-a-url",  # Not a URL
            "",  # Empty string
            None,  # Not a string
            123,  # Not a string
            "https://github.com/-invalid/repo",  # Invalid username
            "https://github.com/user/-invalid",  # Invalid repo name
        ]

        for url in invalid_urls:
            assert not validate_github_url(url), f"Should be invalid: {url}"

    def test_extract_repo_info_valid(self):
        """Test repository information extraction from valid URLs."""
        test_cases = [
            (
                "https://github.com/user/repo",
                {"owner": "user", "repo": "repo", "full_name": "user/repo"},
            ),
            (
                "https://github.com/org-name/repo-name",
                {
                    "owner": "org-name",
                    "repo": "repo-name",
                    "full_name": "org-name/repo-name",
                },
            ),
            (
                "https://github.com/user123/repo_123",
                {
                    "owner": "user123",
                    "repo": "repo_123",
                    "full_name": "user123/repo_123",
                },
            ),
        ]

        for url, expected in test_cases:
            result = extract_repo_info(url)
            assert result == expected, f"Failed for URL: {url}"

    def test_extract_repo_info_invalid(self):
        """Test repository information extraction from invalid URLs."""
        invalid_urls = [
            "https://gitlab.com/user/repo",
            "not-a-url",
            "https://github.com/user",
            None,
        ]

        for url in invalid_urls:
            result = extract_repo_info(url)
            assert result is None, f"Should return None for: {url}"


class TestStringUtilities:
    """Test string processing utilities."""

    def test_sanitize_repo_name(self):
        """Test repository name sanitization."""
        test_cases = [
            ("normal-repo", "normal-repo"),
            ("repo with spaces", "repo_with_spaces"),
            ("repo/with/slashes", "repo_with_slashes"),
            ("repo@with#special$chars", "repo_with_special_chars"),
            ("___multiple___underscores___", "multiple_underscores"),
            ("", "unnamed_repo"),  # Empty string
            ("___", "unnamed_repo"),  # Only underscores
            ("repo..name", "repo..name"),  # Dots are allowed
            ("repo-name_123", "repo-name_123"),  # Valid chars preserved
        ]

        for input_name, expected in test_cases:
            result = sanitize_repo_name(input_name)
            assert result == expected, f"Failed for: {input_name}"

    def test_truncate_text(self):
        """Test text truncation utility."""
        test_cases = [
            ("short", 10, "short"),  # No truncation needed
            ("this is a long text", 10, "this is..."),  # Basic truncation
            ("exact text", 10, "exact text"),  # Exact length (10 chars)
            ("", 10, ""),  # Empty string
            ("test", 10, "test"),  # Shorter than limit
            ("custom suffix", 5, "cu***", "***"),  # Custom suffix
        ]

        for case in test_cases:
            if len(case) == 3:
                text, max_len, expected = case
                result = truncate_text(text, max_len)
            else:
                text, max_len, expected, suffix = case
                result = truncate_text(text, max_len, suffix)

            assert result == expected, f"Failed for: {text}"


class TestCostCalculation:
    """Test cost calculation utilities."""

    def test_calculate_cost_for_an_explicit_model(self):
        """Cost scales linearly with tokens at that model's published rate.

        The model is passed explicitly: calculate_cost() defaults to whatever
        ANTHROPIC_MODEL is set to, which is a deployment choice and not
        something to pin arithmetic assertions to.
        """
        # Haiku 3.0: $0.25/1M input, $1.25/1M output
        model = "claude-3-haiku-20240307"
        test_cases = [
            (1000, 1000, 0.00025 + 0.00125),  # 1K tokens each
            (0, 0, 0.0),  # No tokens
            (1_000_000, 1_000_000, 0.25 + 1.25),  # 1M tokens each
            (500_000, 200_000, 0.125 + 0.25),  # Mixed amounts
        ]

        for input_tokens, output_tokens, expected_cost in test_cases:
            result = calculate_cost(input_tokens, output_tokens, model)
            assert abs(result - expected_cost) < 0.000001, (
                f"Cost calculation failed for {input_tokens}/{output_tokens}"
            )

    def test_calculate_cost_defaults_to_the_configured_model(self):
        """With no model argument, pricing follows ANTHROPIC_MODEL."""
        from github_analyzer.ai.cost_tracker import CostTracker
        from github_analyzer.core.tier_config import get_configured_model

        configured = get_configured_model()
        assert calculate_cost(1000, 1000) == calculate_cost(1000, 1000, configured)
        assert configured in CostTracker.MODEL_PRICING

    def test_calculate_cost_unknown_model(self):
        """An unpriced model costs at least as much as any model we know.

        Over-reporting an unknown model is safe; under-reporting hides spend.
        """
        from github_analyzer.ai.cost_tracker import CostTracker

        result = calculate_cost(1000, 1000, "unknown-model")

        for known in CostTracker.MODEL_PRICING:
            assert result >= calculate_cost(1000, 1000, known)


class TestJSONUtilities:
    """Test JSON processing utilities."""

    def test_safe_json_loads_valid(self):
        """Test safe JSON loading with valid data."""
        test_cases = [
            ('{"key": "value"}', {"key": "value"}),
            ("[]", []),
            ("null", None),
            ("123", 123),
            ('"string"', "string"),
        ]

        for json_str, expected in test_cases:
            result = safe_json_loads(json_str)
            assert result == expected

    def test_safe_json_loads_invalid(self):
        """Test safe JSON loading with invalid data."""
        invalid_cases = [
            '{"invalid": json}',  # Invalid JSON
            "",  # Empty string
            None,  # Not a string
            "{unclosed",  # Malformed JSON
        ]

        for invalid_json in invalid_cases:
            result = safe_json_loads(invalid_json, default="DEFAULT")
            assert result == "DEFAULT"

    def test_safe_json_dumps_valid(self):
        """Test safe JSON serialization with valid data."""
        test_cases = [
            ({"key": "value"}, '{\n  "key": "value"\n}'),
            ([], "[]"),
            (None, "null"),
        ]

        for data, expected in test_cases:
            result = safe_json_dumps(data)
            assert result == expected

    def test_safe_json_dumps_invalid(self):
        """Test safe JSON serialization with invalid data."""

        # Create an object that can't be serialized
        class NonSerializable:
            pass

        result = safe_json_dumps(NonSerializable(), default="DEFAULT")
        assert result == "DEFAULT"


class TestDateTimeUtilities:
    """Test datetime processing utilities."""

    def test_normalize_datetime_string(self):
        """Test datetime normalization from string."""
        test_cases = [
            "2024-01-01T00:00:00Z",
            "2024-01-01T00:00:00+00:00",
            "2024-01-01T12:30:45Z",
        ]

        for dt_str in test_cases:
            result = normalize_datetime(dt_str)
            assert isinstance(result, datetime)
            assert result.tzinfo == timezone.utc

    def test_normalize_datetime_object(self):
        """Test datetime normalization from datetime object."""
        # Naive datetime
        naive_dt = datetime(2024, 1, 1, 12, 0, 0)
        result = normalize_datetime(naive_dt)
        assert result.tzinfo == timezone.utc

        # Aware datetime
        aware_dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = normalize_datetime(aware_dt)
        assert result.tzinfo == timezone.utc

    def test_calculate_days_between(self):
        """Test day calculation between dates."""
        start = "2024-01-01T00:00:00Z"
        end = "2024-01-05T00:00:00Z"

        result = calculate_days_between(start, end)
        assert result == 4  # 4 days difference

        # Test with default end (current time)
        result = calculate_days_between(start)
        assert isinstance(result, int)
        assert result > 0  # Should be positive (start is in past)


class TestLanguageProcessing:
    """Test language data processing utilities."""

    def test_parse_github_languages(self):
        """Test GitHub language data parsing to percentages."""
        test_cases = [
            (
                {"Python": 12345, "JavaScript": 5678},
                {"Python": 68.5, "JavaScript": 31.5},
            ),
            ({}, {}),  # Empty languages
            ({"Python": 1000}, {"Python": 100.0}),  # Single language
            ({"A": 0, "B": 0}, {}),  # All zero bytes
        ]

        for languages, expected in test_cases:
            result = parse_github_languages(languages)

            if not expected:  # Empty case
                assert result == expected
            else:
                # Check percentages are close (allowing for rounding)
                for lang, percentage in expected.items():
                    assert abs(result[lang] - percentage) < 0.1, (
                        f"Failed for {languages}"
                    )


class TestFileUtilities:
    """Test file processing utilities."""

    def test_get_file_extension(self):
        """Test file extension extraction."""
        test_cases = [
            ("file.py", "py"),
            ("script.js", "js"),
            ("README.md", "md"),
            ("no_extension", ""),
            ("file.tar.gz", "gz"),  # Gets last extension
            (".hidden", ""),  # Hidden file with no extension
            ("", ""),  # Empty filename
        ]

        for filename, expected in test_cases:
            result = get_file_extension(filename)
            assert result == expected, f"Failed for: {filename}"

    def test_is_documentation_file(self):
        """Test documentation file detection."""
        doc_files = [
            "README.md",
            "readme.txt",
            "CONTRIBUTING.md",
            "docs/api.md",
            "LICENSE",
            "CHANGELOG.md",
            "installation.md",
        ]

        for filename in doc_files:
            assert is_documentation_file(filename), f"Should be doc file: {filename}"

        non_doc_files = [
            "script.py",
            "test_file.py",
            "config.json",
            "data.csv",
        ]

        for filename in non_doc_files:
            assert not is_documentation_file(filename), (
                f"Should not be doc file: {filename}"
            )

    def test_is_test_file(self):
        """Test test file detection."""
        test_files = [
            "test_module.py",
            "module_test.py",
            "tests/test_config.py",
            "spec/config.spec.js",
            "integration.test.js",
            "TestClass.java",
        ]

        for filename in test_files:
            assert is_test_file(filename), f"Should be test file: {filename}"

        non_test_files = [
            "module.py",
            "config.js",
            "README.md",
            "data.json",
        ]

        for filename in non_test_files:
            assert not is_test_file(filename), f"Should not be test file: {filename}"


class TestResultFormatting:
    """Test analysis result formatting."""

    def test_format_analysis_result_complete(self):
        """Test formatting of complete analysis result."""
        result = {
            "repository_url": "https://github.com/user/repo",
            "assessment_type": "EVIDENCE-BASED ANALYSIS",
            "confidence": 85,
            "summary": "Well-maintained repository with good practices",
            "key_signal": "Active development with quality code",
            "strengths": ["Good testing", "Clear documentation"],
            "yellow_flags": ["Needs more comments"],
            "context_fit": {"startup": True, "enterprise": True, "agency": False},
            "generated_by": "haiku",
            "cost": 0.002,
            "analysis_time": 12.5,
        }

        formatted = format_analysis_result(result)

        # Check that key elements are present
        assert "user/repo" in formatted
        assert "EVIDENCE-BASED ANALYSIS" in formatted
        assert "[Target] Confidence: 85%" in formatted
        assert "Well-maintained repository" in formatted
        assert "Good testing" in formatted
        assert "Needs more comments" in formatted
        assert "[OK] Startup" in formatted
        assert "[X] Agency" in formatted
        assert "$0.002000" in formatted
        assert "12.50s" in formatted

    def test_format_analysis_result_minimal(self):
        """Test formatting of minimal analysis result."""
        result = {
            "assessment_type": "EVIDENCE-BASED ANALYSIS",
            "summary": "Basic analysis result",
        }

        formatted = format_analysis_result(result)

        assert "EVIDENCE-BASED ANALYSIS" in formatted
        assert "Basic analysis result" in formatted

    def test_format_analysis_result_empty(self):
        """Test formatting of empty analysis result."""
        formatted = format_analysis_result({})
        assert "No analysis result available" in formatted

        formatted = format_analysis_result(None)
        assert "No analysis result available" in formatted
