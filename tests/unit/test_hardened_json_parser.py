"""
Tests for HardenedJSONParser - Phase 2 of Operation Containment Field

Validates the parser's ability to handle various malformed JSON scenarios
that commonly occur in AI responses.
"""

from src.github_analyzer.ai.hardened_json_parser import (
    HardenedJSONParser,
    create_hardened_parser,
)


class TestHardenedJSONParser:
    """Test cases for the HardenedJSONParser utility."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = create_hardened_parser()
        self.expected_keys = [
            "summary",
            "observed_patterns",
            "limitations",
            "context_notes",
            "upgrade_benefit",
        ]

    def test_parse_valid_json(self):
        """Test parsing of valid JSON response."""
        valid_json = """
        {
            "summary": "Test repository analysis",
            "observed_patterns": [
                {
                    "pattern": "Testing practices",
                    "evidence": "Has comprehensive test suite",
                    "files": ["test/"],
                    "relevance": "Shows good development practices"
                }
            ],
            "limitations": ["Limited commit history"],
            "context_notes": "Small project scope",
            "upgrade_benefit": "Professional analysis provides detailed insights"
        }
        """

        result, error = self.parser.parse(valid_json, self.expected_keys)

        assert result is not None
        assert error == ""
        assert result["summary"] == "Test repository analysis"
        assert len(result["observed_patterns"]) == 1
        assert result["limitations"] == ["Limited commit history"]

    def test_parse_json_with_trailing_commas(self):
        """Test repair of trailing commas."""
        malformed_json = """
        {
            "summary": "Test analysis",
            "observed_patterns": [
                {
                    "pattern": "Testing",
                    "evidence": "Good tests",
                    "files": [],
                    "relevance": "Important",
                }
            ],
            "limitations": ["Limited data",],
            "context_notes": "Brief notes",
            "upgrade_benefit": "Better insights",
        }
        """

        result, error = self.parser.parse(malformed_json, self.expected_keys)

        assert result is not None
        assert error == ""
        assert result["summary"] == "Test analysis"

    def test_parse_json_with_mixed_content(self):
        """Test extraction from response with non-JSON content."""
        mixed_content = """
        Here is my analysis of the repository:

        {
            "summary": "Analysis complete",
            "observed_patterns": [],
            "limitations": ["Some limitations"],
            "context_notes": "Mixed content test",
            "upgrade_benefit": "Upgrade for more"
        }

        Additional notes about the analysis...
        """

        result, error = self.parser.parse(mixed_content, self.expected_keys)

        assert result is not None
        assert error == ""
        assert result["summary"] == "Analysis complete"

    def test_parse_json_with_single_quotes(self):
        """Test repair of single quotes to double quotes."""
        single_quote_json = """
        {
            'summary': 'Test with single quotes',
            'observed_patterns': [],
            'limitations': ['Quote issue'],
            'context_notes': 'Single quote test',
            'upgrade_benefit': 'Professional tier'
        }
        """

        result, error = self.parser.parse(single_quote_json, self.expected_keys)

        assert result is not None
        assert error == ""
        assert result["summary"] == "Test with single quotes"

    def test_parse_json_with_unquoted_keys(self):
        """Test repair of unquoted object keys."""
        unquoted_json = """
        {
            summary: "Unquoted keys test",
            observed_patterns: [],
            limitations: ["Key format issue"],
            context_notes: "Testing key repairs",
            upgrade_benefit: "Better analysis"
        }
        """

        result, error = self.parser.parse(unquoted_json, self.expected_keys)

        assert result is not None
        assert error == ""
        assert result["summary"] == "Unquoted keys test"

    def test_parse_json_with_extra_content(self):
        """Test handling of extra content after JSON."""
        extra_content_json = """
        {
            "summary": "Test analysis",
            "observed_patterns": [],
            "limitations": ["Some limits"],
            "context_notes": "Extra content test",
            "upgrade_benefit": "Upgrade available"
        }

        This is extra text that should be ignored.
        More text here.
        """

        result, error = self.parser.parse(extra_content_json, self.expected_keys)

        assert result is not None
        assert error == ""
        assert result["summary"] == "Test analysis"

    def test_aggressive_extraction(self):
        """Test aggressive extraction from severely malformed JSON."""
        severely_malformed = """
        Analysis results:

        "summary": "Severely malformed test"
        "observed_patterns": [{"pattern": "Test pattern", "evidence": "Some evidence"}]
        "limitations": ["Extraction test"]
        "context_notes": "Aggressive parsing needed"
        "upgrade_benefit": "Professional insights"

        End of analysis.
        """

        result, error = self.parser.parse(severely_malformed, self.expected_keys)

        assert result is not None
        assert error == ""
        assert result["summary"] == "Severely malformed test"

    def test_parse_completely_invalid(self):
        """Test handling of completely unparseable content."""
        invalid_content = """
        This is not JSON at all.
        No structured data here.
        Just plain text response.
        """

        result, error = self.parser.parse(invalid_content, self.expected_keys)

        assert result is None
        assert "No JSON block found" in error

    def test_parse_empty_response(self):
        """Test handling of empty response."""
        result, error = self.parser.parse("", self.expected_keys)

        assert result is None
        assert "No JSON block found" in error

    def test_parse_json_with_boolean_fixes(self):
        """Test repair of Python boolean values to JSON format."""
        python_booleans_json = """
        {
            "summary": "Boolean test",
            "observed_patterns": [],
            "limitations": ["Boolean format"],
            "context_notes": "Testing boolean repairs",
            "upgrade_benefit": "Better parsing",
            "has_tests": True,
            "is_active": False,
            "missing_data": None
        }
        """

        result, error = self.parser.parse(python_booleans_json, self.expected_keys)

        assert result is not None
        assert error == ""
        assert result["has_tests"] is True
        assert result["is_active"] is False
        assert result["missing_data"] is None

    def test_parse_json_with_nested_structures(self):
        """Test parsing complex nested JSON structures."""
        nested_json = """
        {
            "summary": "Complex nested test",
            "observed_patterns": [
                {
                    "pattern": "Nested pattern",
                    "evidence": "Complex structure",
                    "files": ["src/", "test/"],
                    "relevance": "Architectural insight",
                    "details": {
                        "complexity": "high",
                        "maintainability": "good"
                    }
                }
            ],
            "limitations": ["Complex nesting"],
            "context_notes": "Nested structure test",
            "upgrade_benefit": "Advanced analysis"
        }
        """

        result, error = self.parser.parse(nested_json, self.expected_keys)

        assert result is not None, f"Parse failed: {error}"
        assert error == ""
        assert len(result["observed_patterns"]) == 1
        assert "details" in result["observed_patterns"][0]

    def test_structure_validation(self):
        """Test structure validation with missing required keys."""
        incomplete_json = """
        {
            "summary": "Incomplete test",
            "observed_patterns": []
        }
        """

        result, error = self.parser.parse(incomplete_json, self.expected_keys)

        # Should still parse but may not pass full validation
        assert result is not None
        assert result["summary"] == "Incomplete test"

    def test_factory_function(self):
        """Test the factory function creates proper instance."""
        parser = create_hardened_parser()

        assert isinstance(parser, HardenedJSONParser)
        assert hasattr(parser, "parse")
        assert hasattr(parser, "repair_attempts")

    def test_repair_attempt_tracking(self):
        """Test that repair attempts are tracked."""
        malformed_json = """
        {
            'summary': 'Repair tracking test',
            observed_patterns: [],
            'limitations': ['Tracking test',],
            context_notes: 'Multiple repairs needed',
            'upgrade_benefit': 'Better results',
        }
        """

        result, error = self.parser.parse(malformed_json, self.expected_keys)

        assert result is not None
        assert self.parser.repair_attempts > 0

    def test_large_response_handling(self):
        """Test handling of large response content."""
        # Create a large JSON response
        large_patterns = []
        for i in range(100):
            large_patterns.append(
                {
                    "pattern": f"Pattern {i}",
                    "evidence": f"Evidence for pattern {i} with lots of detail " * 10,
                    "files": [f"file{i}.py"],
                    "relevance": f"Relevance {i}",
                }
            )

        large_json = f"""
        {{
            "summary": "Large response test with extensive content",
            "observed_patterns": {large_patterns},
            "limitations": ["Large dataset", "Processing complexity"],
            "context_notes": "Testing large response handling",
            "upgrade_benefit": "Enhanced processing for large repositories"
        }}
        """

        result, error = self.parser.parse(
            large_json.replace("'", '"'), self.expected_keys
        )

        assert result is not None
        assert error == ""
        assert len(result["observed_patterns"]) == 100
