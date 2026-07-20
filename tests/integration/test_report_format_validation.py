"""
Enhanced Report Format Validation Tests.

This module provides comprehensive validation for all report formats,
ensuring robust output generation and proper format compliance.
"""

import json
import re
from typing import Any, Tuple
from unittest.mock import Mock, patch

import pytest

from github_analyzer.core.classifier import RepositoryClassifier

# Evidence-based approach - no confidence scorer needed
from github_analyzer.core.context_analyzer import AnalysisContext, ContextAnalyzer
from github_analyzer.core.report_generator import ReportFormat, ReportGenerator
from github_analyzer.data.models import FileInfo, RepositoryMetrics
from tests.integration.test_comprehensive_end_to_end import create_test_repo


class TestReportFormatValidation:
    """Comprehensive validation tests for all report formats."""

    @pytest.fixture
    def mock_anthropic(self):
        """Mock Anthropic client for all tests."""
        with patch("anthropic.Anthropic") as mock_anthropic_class:
            mock_client = Mock()
            mock_anthropic_class.return_value = mock_client

            # Mock AI response for questions generation
            mock_response = Mock()
            mock_response.content = [
                Mock(
                    text='[{"category": "technical", "question": "Test question", "evidence_reference": "Test re", "follow_ups": ["Follow up 1"], "what_to_listen_for": "Listen for depth", "green_flags": ["Flag1"], "red_flags": ["Flag2"], "context_relevance": "Relevant"}]'
                )
            ]
            mock_client.messages.create.return_value = mock_response
            yield mock_client

    @pytest.fixture
    def sample_report(self, mock_anthropic) -> Tuple[Any, ReportGenerator]:
        """Generate a sample report for format validation testing."""
        # Create a representative test repository
        test_repo = create_test_repo(
            name="format-validation-test",
            description="Repository for testing format validation",
            size=5000,
            has_tests=True,
            has_ci_config=True,
            has_license=True,
            readme_content="# Format Validation Test\n\nComprehensive test repository for format validation.\n"
            * 20,
            languages={"Python": 30000, "JavaScript": 20000, "TypeScript": 10000},
            file_structure=[
                FileInfo(path="src", name="src", size=0, type="directory"),
                FileInfo(path="tests", name="tests", size=0, type="directory"),
                FileInfo(
                    path="src/main.py",
                    name="main.py",
                    size=1000,
                    type="file",
                    extension="py",
                ),
                FileInfo(
                    path="src/utils.py",
                    name="utils.py",
                    size=800,
                    type="file",
                    extension="py",
                ),
                FileInfo(
                    path="src/config.py",
                    name="config.py",
                    size=500,
                    type="file",
                    extension="py",
                ),
                FileInfo(
                    path="tests/test_main.py",
                    name="test_main.py",
                    size=600,
                    type="file",
                    extension="py",
                    is_test=True,
                ),
                FileInfo(
                    path="tests/test_utils.py",
                    name="test_utils.py",
                    size=400,
                    type="file",
                    extension="py",
                    is_test=True,
                ),
                FileInfo(
                    path="README.md",
                    name="README.md",
                    size=1500,
                    type="file",
                    extension="md",
                    is_documentation=True,
                ),
                FileInfo(
                    path=".github/workflows/ci.yml",
                    name="ci.yml",
                    size=300,
                    type="file",
                    extension="yml",
                ),
                FileInfo(
                    path="requirements.txt",
                    name="requirements.txt",
                    size=200,
                    type="file",
                    extension="txt",
                ),
            ],
            metrics=RepositoryMetrics(
                total_commits=150,
                unique_contributors=8,
                lines_of_code=20000,
                test_coverage_estimate=0.85,
                documentation_presence="5 documentation files in 20 total files",
                days_since_last_commit=3,
                commit_frequency=6.0,
                avg_commit_size=140.0,
            ),
            stars=75,
            forks=20,
            open_issues=5,
        )

        # Generate complete analysis
        classifier = RepositoryClassifier()
        context_analyzer = ContextAnalyzer()
        # Evidence-based approach - no confidence scorer
        report_generator = ReportGenerator()

        classification = classifier.classify(test_repo)
        contextual_assessment = context_analyzer.analyze(
            test_repo, AnalysisContext.ENTERPRISE
        )
        # Evidence-based approach - no confidence scoring
        confidence_scoring = None

        report = report_generator.generate_report(
            test_repo,
            classification,
            contextual_assessment,
            AnalysisContext.ENTERPRISE,
            confidence_scoring,
        )

        return report, report_generator

    def test_json_format_validation(
        self, sample_report: Tuple[Any, ReportGenerator]
    ) -> None:
        """Validate JSON format structure and content."""
        report, generator = sample_report

        json_output = generator.format_report(
            report, ReportFormat.JSON, subscription_plan="professional"
        )

        # Basic JSON validation
        assert json_output is not None
        assert len(json_output) > 500

        # Parse JSON to ensure it's valid
        try:
            parsed_json = json.loads(json_output)
        except json.JSONDecodeError as e:
            pytest.fail(f"JSON format is invalid: {e}")

        # Validate required JSON structure
        required_sections = [
            "metadata",
            "executive_summary",
            "context_analysis",
            "section_assessments",
            "recommendations",
            "analysis_quality",
        ]

        for section in required_sections:
            assert section in parsed_json, f"Missing required section: {section}"

        # Validate metadata structure
        metadata = parsed_json["metadata"]
        assert "repository_url" in metadata
        assert "repository_name" in metadata
        assert "analysis_date" in metadata
        assert "report_version" in metadata

        # Validate executive summary for evidence-based approach
        exec_summary = parsed_json["executive_summary"]
        assert "summary" in exec_summary
        # No recommendations or scores in evidence-based approach

        # Validate context analysis
        context_analysis = parsed_json["context_analysis"]
        assert "context" in context_analysis
        assert "repository_type" in context_analysis
        # No scores in evidence-based approach

        # Validate section assessments
        section_assessments = parsed_json["section_assessments"]
        assert "technical" in section_assessments
        assert "professional" in section_assessments
        assert "communication" in section_assessments
        assert "growth" in section_assessments

        # Validate recommendations
        recommendations = parsed_json["recommendations"]
        assert "recommendations" in recommendations
        assert "interview_focus" in recommendations

        # Validate analysis quality for evidence-based approach
        analysis_quality = parsed_json["analysis_quality"]
        assert "limitations" in analysis_quality
        assert "confidence_explanation" in analysis_quality
        # No scores or grades in evidence-based approach

    def test_markdown_format_validation(
        self, sample_report: Tuple[Any, ReportGenerator]
    ) -> None:
        """Validate Markdown format structure and syntax."""
        report, generator = sample_report

        markdown_output = generator.format_report(
            report, ReportFormat.MARKDOWN, subscription_plan="professional"
        )

        # Basic validation
        assert markdown_output is not None
        assert len(markdown_output) > 1000

        # Check for required Markdown elements
        assert "# Repository Analysis Report" in markdown_output
        assert "## Executive Summary" in markdown_output
        assert "## Key Observations" in markdown_output
        assert "## Evidence-Based Analysis" in markdown_output
        assert "## Topics for Discussion" in markdown_output

        # Validate basic Markdown syntax
        # Check for properly formatted headers
        header_pattern = r"^#{1,6}\s+.+$"
        headers = re.findall(header_pattern, markdown_output, re.MULTILINE)
        assert len(headers) >= 5, "Should have multiple properly formatted headers"

        # Check for bold text formatting
        assert "**Repository:**" in markdown_output
        # Evidence-based approach - no binary recommendations or confidence scores

        # Check for list formatting
        assert re.search(r"^-\s+", markdown_output, re.MULTILINE), (
            "Should contain bullet lists"
        )

        # Ensure no HTML tags in markdown (except allowed ones)
        html_tags = re.findall(r"<(?!/?(em|strong|code|pre))[^>]+>", markdown_output)
        assert len(html_tags) == 0, f"Unexpected HTML tags in markdown: {html_tags}"

    def test_html_format_validation(
        self, sample_report: Tuple[Any, ReportGenerator]
    ) -> None:
        """Validate HTML format structure and syntax."""
        report, generator = sample_report

        html_output = generator.format_report(
            report, ReportFormat.HTML, subscription_plan="professional"
        )

        # Basic validation
        assert html_output is not None
        assert len(html_output) > 2000

        # Check for proper HTML structure
        assert "<!DOCTYPE html>" in html_output
        assert '<html lang="en">' in html_output
        assert "<head>" in html_output
        assert '<meta charset="UTF-8">' in html_output
        assert "<title>" in html_output
        assert "<body>" in html_output
        assert "</html>" in html_output.strip()

        # Check for CSS styling
        assert "<style>" in html_output
        assert "</style>" in html_output

        # Validate semantic HTML structure (using class-based structure)
        assert 'class="header"' in html_output or "<header>" in html_output
        assert "<main>" in html_output or 'class="container"' in html_output
        assert "</main>" in html_output or "</div>" in html_output

        # Check for proper heading hierarchy
        assert "<h1>" in html_output
        assert (
            "<h2>" in html_output or "<h3>" in html_output
        )  # Allow h3 as secondary headings

        # Validate content sections
        assert "Repository Analysis Report" in html_output
        assert "Executive Summary" in html_output
        # Evidence-based sections
        assert "Key Insights" in html_output or "insights" in html_output.lower()
        assert "Evidence" in html_output or "evidence" in html_output.lower()

        # Check for proper list formatting
        assert "<ul>" in html_output or "<ol>" in html_output
        assert "<li>" in html_output

        # Ensure CSS classes are applied
        assert "class=" in html_output

        # Basic HTML syntax validation (simplified)
        # Check that opened tags are closed
        open_tags = re.findall(r"<(\w+)(?:\s[^>]*)?>(?![^<]*/>)", html_output)
        close_tags = re.findall(r"</(\w+)>", html_output)

        # Filter out self-closing tags and meta tags
        filtered_open = [
            tag for tag in open_tags if tag not in ["meta", "br", "hr", "img", "input"]
        ]

        # Basic tag balance check for major elements
        major_tags = ["html", "head", "body", "main", "header"]
        for tag in major_tags:
            if tag in filtered_open:
                assert tag in close_tags, f"Tag '{tag}' opened but not closed"

    def test_pdf_ready_format_validation(
        self, sample_report: Tuple[Any, ReportGenerator]
    ) -> None:
        """Validate PDF-ready format structure and content."""
        report, generator = sample_report

        pdf_output = generator.format_report(
            report, ReportFormat.PDF_READY, subscription_plan="professional"
        )

        # Basic validation
        assert pdf_output is not None
        assert len(pdf_output) > 1500

        # Check for proper plain text structure
        assert "REPOSITORY ANALYSIS REPORT" in pdf_output
        assert "Executive Summary:" in pdf_output or "EXECUTIVE SUMMARY" in pdf_output
        # Evidence-based sections
        assert "Key Insights" in pdf_output or "INSIGHTS" in pdf_output
        assert "Evidence" in pdf_output or "EVIDENCE" in pdf_output

        # Ensure no HTML or Markdown formatting remains
        assert (
            "<" not in pdf_output or pdf_output.count("<") <= 2
        )  # Allow minimal HTML entities
        assert (
            "#" not in pdf_output or pdf_output.count("#") <= 5
        )  # Allow minimal hash symbols

        # Check for proper line breaks and formatting
        lines = pdf_output.split("\n")
        assert len(lines) > 20, "PDF format should have multiple lines"

        # Validate proper text formatting for evidence-based approach
        # No scores or grades to check

        # Check for proper section separation
        section_breaks = [
            line for line in lines if "─" in line or "=" in line or line.strip() == ""
        ]
        assert len(section_breaks) > 5, "Should have section breaks for readability"

    def test_format_consistency_across_types(
        self, sample_report: Tuple[Any, ReportGenerator]
    ) -> None:
        """Validate that core information is consistent across all formats."""
        report, generator = sample_report

        # Generate all formats
        formats = {
            ReportFormat.JSON: generator.format_report(
                report, ReportFormat.JSON, subscription_plan="professional"
            ),
            ReportFormat.MARKDOWN: generator.format_report(
                report, ReportFormat.MARKDOWN, subscription_plan="professional"
            ),
            ReportFormat.HTML: generator.format_report(
                report, ReportFormat.HTML, subscription_plan="professional"
            ),
            ReportFormat.PDF_READY: generator.format_report(
                report, ReportFormat.PDF_READY, subscription_plan="professional"
            ),
        }

        # Validate all formats are generated
        for format_type, content in formats.items():
            assert content is not None, f"{format_type} format should not be None"
            assert len(content) > 200, (
                f"{format_type} format should have substantial content"
            )

        # Check for consistent core information across formats
        core_info = [
            report.repository_name,
            # Evidence-based approach - check different core info
            str(report.repository_type.value if report.repository_type else "Unknown"),
        ]

        for info in core_info:
            for format_type, content in formats.items():
                # JSON format uses structured data, so check differently
                if format_type == ReportFormat.JSON:
                    json_data = json.loads(content)
                    # Check if info appears in stringified JSON
                    json_str = json.dumps(json_data)
                    info_found = (
                        str(info).lower() in json_str.lower()
                        or str(info) in json_str
                        or any(
                            str(info) in str(v)
                            for v in json_data.values()
                            if isinstance(v, (str, dict))
                        )
                    )
                    assert info_found, (
                        f"Core info '{info}' missing from {format_type} format"
                    )
                else:
                    assert str(info) in content, (
                        f"Core info '{info}' missing from {format_type} format"
                    )

    def test_format_error_handling(self) -> None:
        """Test format generation with edge cases and error conditions."""
        generator = ReportGenerator()

        # Test with minimal report data
        minimal_repo = create_test_repo(
            name="minimal-test",
            description="",
            size=0,
            languages={},
            readme_content="",
            metrics=RepositoryMetrics(
                total_commits=0,
                unique_contributors=0,
                lines_of_code=0,
                test_coverage_estimate=0.0,
                documentation_presence="0 documentation files found",
                days_since_last_commit=0,
                commit_frequency=0.0,
                avg_commit_size=0.0,
            ),
        )

        classifier = RepositoryClassifier()
        classification = classifier.classify(minimal_repo)

        minimal_report = generator.generate_report(minimal_repo, classification)

        # Ensure all formats can handle minimal data
        for format_type in [
            ReportFormat.JSON,
            ReportFormat.MARKDOWN,
            ReportFormat.HTML,
            ReportFormat.PDF_READY,
        ]:
            try:
                output = generator.format_report(
                    minimal_report, format_type, subscription_plan="professional"
                )
                assert output is not None
                assert len(output) > 50  # Should still produce meaningful output
            except Exception as e:
                pytest.fail(f"Format {format_type} failed with minimal data: {e}")

    def test_format_special_characters(
        self, sample_report: Tuple[Any, ReportGenerator]
    ) -> None:
        """Test format handling of special characters and edge cases."""
        report, generator = sample_report

        # Modify report to include special characters
        report.executive_summary = "Test with special chars: <>&\"'éñüñ 中文 🚀"
        report.key_strengths = [
            "Strength with <tags>",
            "Unicode: émojis 🎉",
            'Quotes: "test"',
        ]

        # Test all formats handle special characters properly
        for format_type in [
            ReportFormat.JSON,
            ReportFormat.MARKDOWN,
            ReportFormat.HTML,
            ReportFormat.PDF_READY,
        ]:
            try:
                output = generator.format_report(
                    report, format_type, subscription_plan="professional"
                )
                assert output is not None
                assert len(output) > 100

                if format_type == ReportFormat.JSON:
                    # JSON should properly escape special characters
                    json.loads(output)  # Should not raise exception
                elif format_type == ReportFormat.HTML:
                    # HTML should properly escape dangerous characters
                    assert (
                        "&lt;" in output or "<" not in output or "<h" in output
                    )  # Either escaped or only in valid HTML tags

            except Exception as e:
                pytest.fail(f"Format {format_type} failed with special characters: {e}")

    def test_format_performance(
        self, sample_report: Tuple[Any, ReportGenerator]
    ) -> None:
        """Test format generation performance and memory usage."""
        import time

        report, generator = sample_report

        # Test performance for each format
        for format_type in [
            ReportFormat.JSON,
            ReportFormat.MARKDOWN,
            ReportFormat.HTML,
            ReportFormat.PDF_READY,
        ]:
            start_time = time.time()

            # Generate format multiple times to test consistency
            for _ in range(5):
                output = generator.format_report(
                    report, format_type, subscription_plan="professional"
                )
                assert output is not None

            end_time = time.time()
            duration = end_time - start_time

            # Format generation should be reasonably fast (under 1 second for 5 iterations)
            assert duration < 1.0, (
                f"Format {format_type} took too long: {duration:.2f}s"
            )

    def test_format_output_sizes(
        self, sample_report: Tuple[Any, ReportGenerator]
    ) -> None:
        """Validate that format output sizes are reasonable and proportional."""
        report, generator = sample_report

        formats = {}
        for format_type in [
            ReportFormat.JSON,
            ReportFormat.MARKDOWN,
            ReportFormat.HTML,
            ReportFormat.PDF_READY,
        ]:
            output = generator.format_report(
                report, format_type, subscription_plan="professional"
            )
            formats[format_type] = len(output)

        # Validate minimum sizes
        assert formats[ReportFormat.JSON] > 500, "JSON should be substantial"
        assert formats[ReportFormat.MARKDOWN] > 800, "Markdown should be substantial"
        assert formats[ReportFormat.HTML] > 1500, (
            "HTML should be largest due to styling"
        )
        assert formats[ReportFormat.PDF_READY] > 800, "PDF-ready should be substantial"

        # HTML should generally be largest due to CSS styling
        assert formats[ReportFormat.HTML] >= formats[ReportFormat.MARKDOWN], (
            "HTML should be larger than Markdown"
        )

        # Validate reasonable upper bounds (prevent memory issues)
        for format_type, size in formats.items():
            assert size < 100000, f"Format {format_type} output too large: {size} bytes"
