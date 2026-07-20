"""Tests for TrainingDataExporter functionality."""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from github_analyzer.api.services.training_data_exporter import TrainingDataExporter
from github_analyzer.database.models import AnalysisResult


class TestTrainingDataExporter:
    """Test TrainingDataExporter functionality."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = MagicMock()
        session.execute = MagicMock()
        session.commit = MagicMock()
        session.rollback = MagicMock()
        return session

    @pytest.fixture
    def mock_analysis_result(self):
        """Create a mock evidence-based analysis result."""
        analysis = MagicMock(spec=AnalysisResult)
        analysis.id = "analysis-123"
        analysis.user_id = "user-456"
        analysis.repository_name = "owner/test-repo"
        analysis.repository_url = "https://github.com/owner/test-repo"
        analysis.context = "startup"
        analysis.created_at = datetime.now(timezone.utc)
        analysis.training_eligible = True
        analysis.analysis_method = "evidence_based"
        analysis.evidence_version = "1.0.0"
        analysis.deleted_at = None

        # Evidence-based fields
        analysis.evidence_patterns = json.dumps(
            {
                "code_quality": ["Clean architecture", "Good test coverage"],
                "collaboration": ["Active PR reviews", "Clear documentation"],
            }
        )
        analysis.screening_insights = json.dumps(
            {
                "overall_impression": "Strong technical skills",
                "key_strengths": ["Clean code", "Good testing"],
                "areas_to_explore": ["System design", "Performance optimization"],
                "confidence_explanation": "High confidence based on evidence",
            }
        )
        analysis.technical_patterns = json.dumps(
            ["Design patterns", "SOLID principles"]
        )
        analysis.collaboration_patterns = json.dumps(["Code reviews", "Documentation"])
        analysis.quality_indicators = json.dumps(["Unit tests", "CI/CD"])
        analysis.temporal_insights = json.dumps({"growth_rate": "steady"})
        analysis.context_alignment = json.dumps({"fit_score": 0.85})
        analysis.verification_gaps = json.dumps(["Live coding", "System design"])
        analysis.data_consent = json.dumps(
            {
                "training_usage": True,
                "anonymized": True,
                "tier": "professional",
            }
        )

        return analysis

    @pytest.fixture
    def mock_legacy_analysis(self):
        """Create a mock legacy analysis result."""
        analysis = MagicMock(spec=AnalysisResult)
        analysis.id = "legacy-123"
        analysis.user_id = "user-789"
        analysis.analysis_method = "legacy"
        analysis.evidence_patterns = None
        analysis.training_eligible = True
        return analysis

    def test_anonymize_user_id(self):
        """Test user ID anonymization."""
        user_id = "user-12345-sensitive"
        anonymized = TrainingDataExporter.anonymize_user_id(user_id)

        assert len(anonymized) == 16
        assert anonymized != user_id
        # Should be consistent
        assert anonymized == TrainingDataExporter.anonymize_user_id(user_id)
        # Different IDs should produce different hashes
        assert anonymized != TrainingDataExporter.anonymize_user_id("different-user")

    def test_sanitize_repository_url(self):
        """Test repository URL sanitization."""
        # Test normal GitHub URL
        url = "https://github.com/realuser/sensitive-project"
        sanitized = TrainingDataExporter.sanitize_repository_url(url)
        assert sanitized == "https://github.com/anonymous/sensitive-project"

        # Test URL with trailing slash
        url = "https://github.com/anotheruser/repo/"
        sanitized = TrainingDataExporter.sanitize_repository_url(url)
        assert sanitized == "https://github.com/anonymous/repo"

        # Test malformed URL
        url = "not-a-url"
        sanitized = TrainingDataExporter.sanitize_repository_url(url)
        assert sanitized == "https://github.com/anonymous/repository"

    def test_extract_training_features_evidence_based(self, mock_analysis_result):
        """Test extracting features from evidence-based analysis."""
        features = TrainingDataExporter.extract_training_features(mock_analysis_result)

        assert features is not None
        assert features["analysis_id"] == "analysis-123"
        assert features["anonymized_user"] == TrainingDataExporter.anonymize_user_id(
            "user-456"
        )
        assert features["repository_type"] == "test-repo"
        assert features["context"] == "startup"
        assert features["evidence_version"] == "1.0.0"

        # Check evidence patterns
        assert "evidence_patterns" in features
        assert features["evidence_patterns"]["code_quality"] == [
            "Clean architecture",
            "Good test coverage",
        ]

        # Check screening insights
        assert "screening_insights" in features
        assert (
            features["screening_insights"]["overall_impression"]
            == "Strong technical skills"
        )
        assert len(features["screening_insights"]["key_strengths"]) == 2

        # Check other evidence fields
        assert "technical_patterns" in features
        assert "collaboration_patterns" in features
        assert "quality_indicators" in features

    def test_extract_training_features_legacy(self, mock_legacy_analysis):
        """Test that legacy analyses are skipped."""
        features = TrainingDataExporter.extract_training_features(mock_legacy_analysis)
        assert features is None

    def test_extract_training_features_invalid_json(self):
        """Test handling of invalid JSON in analysis."""
        analysis = MagicMock(spec=AnalysisResult)
        analysis.id = "bad-analysis"
        analysis.analysis_method = "evidence_based"
        analysis.evidence_patterns = "invalid json {"

        features = TrainingDataExporter.extract_training_features(analysis)
        assert features is None

    @pytest.mark.asyncio
    async def test_export_training_data_basic(self, mock_db_session):
        """Test basic training data export."""
        # Create mock analyses
        analyses = []
        for i in range(10):
            analysis = MagicMock(spec=AnalysisResult)
            analysis.id = f"analysis-{i}"
            analysis.user_id = "user-1" if i < 5 else "user-2"
            analysis.repository_name = f"owner/repo-{i}"
            analysis.context = "startup"
            analysis.created_at = datetime.now(timezone.utc)
            analysis.training_eligible = True
            analysis.analysis_method = "evidence_based"
            analysis.evidence_version = "1.0.0"
            analysis.deleted_at = None
            analysis.evidence_patterns = json.dumps({"patterns": [f"pattern-{i}"]})
            analysis.screening_insights = json.dumps(
                {
                    "overall_impression": f"Impression {i}",
                    "key_strengths": [f"Strength {i}"],
                }
            )
            # Set all other evidence fields to None (they are optional)
            analysis.technical_patterns = None
            analysis.collaboration_patterns = None
            analysis.quality_indicators = None
            analysis.temporal_insights = None
            analysis.context_alignment = None
            analysis.verification_gaps = None
            analyses.append(analysis)

        # Mock query results
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = analyses
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Export data
        training_data = await TrainingDataExporter.export_training_data(
            mock_db_session,
            days_back=30,
            min_analyses_per_user=5,
        )

        # Should get data from both users (each has 5 analyses)
        assert len(training_data) == 10

        # Check anonymization
        unique_users = set(item["anonymized_user"] for item in training_data)
        assert len(unique_users) == 2

    @pytest.mark.asyncio
    async def test_export_training_data_min_analyses_filter(self, mock_db_session):
        """Test minimum analyses per user filtering."""
        # Create analyses with uneven distribution
        analyses = []
        # User 1: 3 analyses (below minimum)
        for i in range(3):
            analysis = MagicMock(spec=AnalysisResult)
            analysis.id = f"analysis-{i}"
            analysis.user_id = "user-1"
            analysis.analysis_method = "evidence_based"
            analysis.evidence_patterns = json.dumps({"test": True})
            analysis.screening_insights = json.dumps({})
            # Set all other evidence fields to None (they are optional)
            analysis.technical_patterns = None
            analysis.collaboration_patterns = None
            analysis.quality_indicators = None
            analysis.temporal_insights = None
            analysis.context_alignment = None
            analysis.verification_gaps = None
            analyses.append(analysis)

        # User 2: 5 analyses (meets minimum)
        for i in range(3, 8):
            analysis = MagicMock(spec=AnalysisResult)
            analysis.id = f"analysis-{i}"
            analysis.user_id = "user-2"
            analysis.analysis_method = "evidence_based"
            analysis.evidence_patterns = json.dumps({"test": True})
            analysis.screening_insights = json.dumps({})
            # Set all other evidence fields to None (they are optional)
            analysis.technical_patterns = None
            analysis.collaboration_patterns = None
            analysis.quality_indicators = None
            analysis.temporal_insights = None
            analysis.context_alignment = None
            analysis.verification_gaps = None
            analyses.append(analysis)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = analyses
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Export with minimum of 5 analyses per user
        training_data = await TrainingDataExporter.export_training_data(
            mock_db_session,
            min_analyses_per_user=5,
        )

        # Should only get user-2's data
        assert len(training_data) == 5
        assert all(
            item["anonymized_user"] == TrainingDataExporter.anonymize_user_id("user-2")
            for item in training_data
        )

    @pytest.mark.asyncio
    async def test_export_diversity_metrics(self):
        """Test diversity metrics calculation."""
        training_data = [
            {
                "anonymized_user": "user1",
                "context": "startup",
                "repository_type": "web-app",
                "analysis_date": "2024-01-01T10:00:00",
            },
            {
                "anonymized_user": "user1",
                "context": "startup",
                "repository_type": "api",
                "analysis_date": "2024-01-02T10:00:00",
            },
            {
                "anonymized_user": "user2",
                "context": "enterprise",
                "repository_type": "web-app",
                "analysis_date": "2024-01-03T10:00:00",
            },
        ]

        metrics = await TrainingDataExporter.export_diversity_metrics(training_data)

        assert metrics["total_examples"] == 3
        assert metrics["unique_users"] == 2
        assert metrics["context_distribution"]["startup"] == 2
        assert metrics["context_distribution"]["enterprise"] == 1
        assert metrics["repository_types"]["web-app"] == 2
        assert metrics["repository_types"]["api"] == 1
        assert metrics["examples_per_user"] == 1.5
        assert metrics["date_range"]["earliest"] == "2024-01-01T10:00:00"
        assert metrics["date_range"]["latest"] == "2024-01-03T10:00:00"

    @pytest.mark.asyncio
    async def test_export_diversity_metrics_empty(self):
        """Test diversity metrics with empty data."""
        metrics = await TrainingDataExporter.export_diversity_metrics([])

        assert metrics["total_examples"] == 0
        assert metrics["unique_users"] == 0
        assert metrics["context_distribution"] == {}
        assert metrics["date_range"] is None

    @pytest.mark.asyncio
    async def test_validate_consent_compliance(self, mock_db_session):
        """Test consent compliance validation."""
        # Create mock analyses with consent
        analysis1 = MagicMock(spec=AnalysisResult)
        analysis1.id = "compliant-1"
        analysis1.data_consent = json.dumps(
            {
                "training_usage": True,
                "anonymized": True,
            }
        )

        analysis2 = MagicMock(spec=AnalysisResult)
        analysis2.id = "non-compliant-1"
        analysis2.data_consent = json.dumps(
            {
                "training_usage": False,
                "anonymized": True,
            }
        )

        analysis3 = MagicMock(spec=AnalysisResult)
        analysis3.id = "no-consent"
        analysis3.data_consent = None

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            analysis1,
            analysis2,
            analysis3,
        ]
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        training_data = [
            {"analysis_id": "compliant-1"},
            {"analysis_id": "non-compliant-1"},
            {"analysis_id": "no-consent"},
        ]

        compliance = await TrainingDataExporter.validate_consent_compliance(
            mock_db_session, training_data
        )

        assert compliance["total_checked"] == 3
        assert compliance["compliant"] == 1
        assert compliance["non_compliant"] == 2
        assert "non-compliant-1" in compliance["non_compliant_ids"]
        assert "no-consent" in compliance["non_compliant_ids"]
        assert compliance["compliance_rate"] == pytest.approx(0.333, rel=0.01)

    def test_prepare_for_export_jsonl(self):
        """Test JSONL export format."""
        training_data = [
            {"id": "1", "data": "test1"},
            {"id": "2", "data": "test2"},
        ]

        result = TrainingDataExporter.prepare_for_export(training_data, "jsonl")

        lines = result.split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0]) == {"data": "test1", "id": "1"}
        assert json.loads(lines[1]) == {"data": "test2", "id": "2"}

    def test_prepare_for_export_json(self):
        """Test JSON export format."""
        training_data = [
            {"id": "1", "data": "test1"},
            {"id": "2", "data": "test2"},
        ]

        result = TrainingDataExporter.prepare_for_export(training_data, "json")

        parsed = json.loads(result)
        assert len(parsed) == 2
        assert parsed[0]["id"] == "1"

    def test_prepare_for_export_invalid_format(self):
        """Test invalid export format."""
        with pytest.raises(ValueError) as exc:
            TrainingDataExporter.prepare_for_export([], "invalid")

        assert "Unsupported format" in str(exc.value)
