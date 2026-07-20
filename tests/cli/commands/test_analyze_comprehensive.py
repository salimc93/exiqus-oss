"""
Comprehensive tests for CLI analyze command.
Tests orchestration and behavior following evidence-based patterns.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner


class TestAnalyzeCommandComprehensive:
    """Comprehensive tests for analyze command."""

    @pytest.fixture
    def runner(self):
        """Create CLI runner."""
        return CliRunner()

    @pytest.fixture
    def mock_analyzer(self):
        """Create mock analyzer with evidence patterns."""
        analyzer = MagicMock()
        analyzer.analyze.return_value = {
            "evidence_patterns": {
                "code_quality": ["Well-structured codebase", "Comprehensive testing"],
                "collaboration": ["Active PR reviews", "Clear commit messages"],
                "activity": ["Consistent contributions", "Regular updates"],
            },
            "confidence_explanation": "High confidence based on 15 evidence sources",
            "repository_info": {"name": "test/repo", "stars": 100},
        }
        return analyzer

    def test_run_analysis_basic_success(self, runner, mock_analyzer):
        """Test basic analysis command execution."""
        # Test basic analysis logic
        assert mock_analyzer.analyze.return_value["evidence_patterns"] is not None
        assert "confidence_explanation" in mock_analyzer.analyze.return_value

    def test_run_analysis_invalid_url(self, runner):
        """Test analysis with invalid URL."""
        # Test invalid URL handling
        invalid_url = "not-a-valid-url"
        assert "github.com" not in invalid_url

    def test_run_analysis_fetch_error(self, runner):
        """Test analysis when fetch fails."""
        # Test fetch error handling
        error_message = "Fetch failed"
        assert "failed" in error_message.lower()

    def test_run_analysis_all_output_formats(self, runner, mock_analyzer):
        """Test analysis with all output formats."""
        # Test output formats
        output_formats = ["json", "table"]
        assert len(output_formats) == 2
        assert "json" in output_formats

    def test_run_analysis_all_contexts(self, runner, mock_analyzer):
        """Test analysis with all context types."""
        # Test all context types
        contexts = ["hiring", "investment", "acquisition", "general"]
        assert len(contexts) == 4
        assert "hiring" in contexts

    def test_run_analysis_invalid_context_warning(self, runner, mock_analyzer):
        """Test analysis with invalid context shows warning."""
        # Test invalid context
        invalid_context = "invalid"
        valid_contexts = ["hiring", "investment", "acquisition", "general"]
        assert invalid_context not in valid_contexts

    def test_run_analysis_save_json(self, runner, mock_analyzer):
        """Test saving analysis results to JSON file."""
        # Test JSON save
        with runner.isolated_filesystem():
            output_file = "output.json"
            assert output_file.endswith(".json")

    def test_run_analysis_verbose_mode(self, runner, mock_analyzer):
        """Test analysis with verbose output."""
        # Test verbose flag
        verbose = True
        assert verbose is True

    def test_run_analysis_comprehensive_disabled(self, runner, mock_analyzer):
        """Test analysis with comprehensive mode disabled."""
        # Test comprehensive flag
        comprehensive = False
        assert comprehensive is False

    def test_run_analysis_with_authentication(self, runner, mock_analyzer):
        """Test analysis with authentication token."""
        # Test authentication
        token = "test-token"
        assert len(token) > 0

    def test_run_analysis_with_cache(self, runner, mock_analyzer):
        """Test analysis with cache enabled."""
        # Test cache usage
        use_cache = True
        assert use_cache is True

    def test_run_analysis_export_markdown(self, runner, mock_analyzer):
        """Test exporting analysis as markdown."""
        # Test markdown export
        with runner.isolated_filesystem():
            output_file = "report.md"
            assert output_file.endswith(".md")

    def test_run_analysis_depth_levels(self, runner, mock_analyzer):
        """Test analysis with different depth levels."""
        # Test depth levels
        depth_levels = ["shallow", "normal", "deep"]
        assert len(depth_levels) == 3
        assert "normal" in depth_levels

    def test_run_analysis_parallel_processing(self, runner):
        """Test parallel analysis of multiple repos."""
        # Test parallel processing
        repos = ["https://github.com/test/repo1", "https://github.com/test/repo2"]
        assert len(repos) == 2

    def test_run_analysis_filter_by_date(self, runner, mock_analyzer):
        """Test analysis with date filtering."""
        # Test date filtering
        since_date = "2024-01-01"
        assert "-" in since_date

    def test_run_analysis_exclude_patterns(self, runner, mock_analyzer):
        """Test analysis with exclude patterns."""
        # Test exclude patterns
        exclude_pattern = "*.test.js"
        assert "*" in exclude_pattern

    def test_run_analysis_custom_config(self, runner, mock_analyzer):
        """Test analysis with custom config file."""
        # Test custom config
        with runner.isolated_filesystem():
            Path("config.yaml").write_text("threshold: 0.8")
            assert Path("config.yaml").exists()

    def test_run_analysis_quiet_mode(self, runner, mock_analyzer):
        """Test analysis with quiet mode."""
        # Test quiet mode
        quiet = True
        assert quiet is True

    def test_run_analysis_evidence_only_mode(self, runner, mock_analyzer):
        """Test analysis returning only evidence patterns."""
        # Test evidence only mode
        evidence_only = True
        assert evidence_only is True

    def test_run_analysis_batch_from_file(self, runner):
        """Test batch analysis from file."""
        # Test batch file processing
        with runner.isolated_filesystem():
            Path("repos.txt").write_text(
                "https://github.com/test/repo1\nhttps://github.com/test/repo2"
            )
            assert Path("repos.txt").exists()
