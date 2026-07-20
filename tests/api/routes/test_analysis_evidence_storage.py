"""Tests for evidence storage in analysis route."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from github_analyzer.api.services.consent_service import CURRENT_CONSENT_VERSION
from github_analyzer.database.models import SubscriptionPlan, User


class TestAnalysisEvidenceStorage:
    """Test evidence storage functionality in analysis route."""

    @pytest.fixture
    def mock_user(self):
        """Create a mock user for testing."""
        user = MagicMock(spec=User)
        user.user_id = "test-user-123"
        user.email = "test@example.com"
        user.subscription_plan = SubscriptionPlan.PROFESSIONAL
        user.privacy_preferences = json.dumps(
            {
                "training_usage": True,
                "anonymized": True,
                "retention_period": "3_years",
            }
        )
        user.consent_version_accepted = CURRENT_CONSENT_VERSION
        return user

    @pytest.fixture
    def mock_free_user(self):
        """Create a mock free tier user."""
        user = MagicMock(spec=User)
        user.user_id = "free-user-123"
        user.email = "free@example.com"
        user.subscription_plan = SubscriptionPlan.FREE
        user.privacy_preferences = None  # Default consent
        user.consent_version_accepted = None
        return user

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = AsyncMock(spec=AsyncSession)
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def evidence_based_analysis_response(self):
        """Create a mock evidence-based analysis response."""
        response = MagicMock()
        response.repository_url = "https://github.com/owner/test-repo"
        response.analysis = {
            "evidence_patterns": {
                "code_quality": ["Clean architecture", "Good test coverage"],
                "collaboration": ["Active PR reviews", "Clear documentation"],
            },
            "insights": [
                {
                    "category": "technical_skills",
                    "description": "Strong technical skills demonstrated",
                    "evidence": ["Clean code", "Good testing practices"],
                },
                {
                    "category": "collaboration",
                    "description": "Excellent collaboration patterns",
                    "evidence": ["Active PR reviews", "Clear documentation"],
                },
            ],
            "confidence_explanation": "High confidence based on extensive evidence",
            "green_flags": [
                "Excellent documentation practices",
                "Strong test coverage",
            ],
            "red_flags": ["Limited recent activity"],
            "areas_to_explore": ["System design", "Performance optimization"],
            "questions": [
                {"question": "How do you approach testing?", "category": "technical"}
            ],
            "recommendations": [{"text": "Focus on system design", "priority": "high"}],
            "technical_assessment": {
                "summary": "Strong technical foundation",
                "details": ["Clean code", "Good patterns"],
            },
            "professional_practices": {
                "summary": "Excellent collaboration",
                "details": ["Code reviews", "Documentation"],
            },
            "communication_skills": {
                "summary": "Clear communication",
                "details": ["Well-documented code"],
            },
            "growth_indicators": {
                "summary": "Steady growth",
                "details": ["Consistent learning"],
            },
            "evidence": {
                "technical_patterns": ["Design patterns", "SOLID principles"],
                "collaboration_patterns": ["Code reviews", "Documentation"],
                "quality_indicators": ["Unit tests", "CI/CD"],
                "temporal_insights": {
                    "growth_rate": "steady",
                    "activity": "consistent",
                },
                "skill_evolution": {"learning_velocity": "fast"},
                "behavioral_analysis": {"work_style": "methodical"},
                "security_practices": {"secure_coding": True},
            },
            "context_alignment": {
                "alignment": "strong",
                "specific_strengths": ["Clean architecture", "Test coverage"],
            },
            "verification_gaps": ["Live coding", "System design"],
            "evidence_strength": "high",
        }
        response.metadata = {
            "response_time_seconds": 5.2,
            "analysis_cost_usd": 0.15,
        }

        # Mock model_dump method to return a serializable dict
        def model_dump(mode=None):
            return {
                "repository_url": response.repository_url,
                "analysis": response.analysis,
                "metadata": response.metadata,
            }

        response.model_dump = model_dump
        return response

    @pytest.fixture
    def legacy_analysis_response(self):
        """Create a mock legacy analysis response."""
        response = MagicMock()
        response.repository_url = "https://github.com/owner/legacy-repo"
        response.analysis = {
            "confidence_score": 0.85,
            "overall_recommendation": "Strong candidate",
            "technical_assessment": {
                "code_quality": 0.9,
                "architecture": 0.85,
            },
        }
        response.metadata = {
            "response_time_seconds": 3.1,
            "analysis_cost_usd": 0.10,
        }

        # Mock model_dump method to return a serializable dict
        def model_dump(mode=None):
            return {
                "repository_url": response.repository_url,
                "analysis": response.analysis,
                "metadata": response.metadata,
            }

        response.model_dump = model_dump
        return response

    @pytest.mark.asyncio
    async def test_store_evidence_based_analysis(
        self, mock_db_session, mock_user, evidence_based_analysis_response
    ):
        """Test storing evidence-based analysis with all fields."""
        from github_analyzer.api.routes.analysis import _store_analysis_result

        # Mock UUID generation
        test_uuid = "test-analysis-123"
        with patch(
            "github_analyzer.api.routes.analysis.uuid.uuid4", return_value=test_uuid
        ):
            analysis_id = await _store_analysis_result(
                db=mock_db_session,
                user=mock_user,
                repository_url="https://github.com/owner/test-repo",
                repository_name="owner/test-repo",
                context="startup",
                analysis_response=evidence_based_analysis_response,
                processing_time_ms=5200,
                token_count=1500,
                api_cost=0.15,
            )

        assert analysis_id == test_uuid

        # Verify the analysis result was created correctly
        mock_db_session.add.assert_called_once()
        analysis_result = mock_db_session.add.call_args[0][0]

        # Check basic fields
        assert analysis_result.id == test_uuid
        assert analysis_result.user_id == "test-user-123"
        assert analysis_result.repository_url == "https://github.com/owner/test-repo"
        assert analysis_result.repository_name == "owner/test-repo"
        assert analysis_result.context == "startup"
        assert analysis_result.processing_time_ms == 5200
        assert analysis_result.token_count == 1500
        assert analysis_result.api_cost == 0.15

        # Check evidence-based fields
        assert analysis_result.analysis_method == "evidence_based"
        assert analysis_result.evidence_version == "1.0.0"

        # Verify NO SCORES fields exist (Great Purge - fields removed from database)
        # overall_score, confidence_score, recommendation no longer exist in model
        assert not hasattr(analysis_result, "overall_score")
        assert not hasattr(analysis_result, "confidence_score")
        assert not hasattr(analysis_result, "recommendation")

        # Check evidence patterns
        evidence_patterns = json.loads(analysis_result.evidence_patterns)
        assert evidence_patterns["code_quality"] == [
            "Clean architecture",
            "Good test coverage",
        ]
        assert evidence_patterns["collaboration"] == [
            "Active PR reviews",
            "Clear documentation",
        ]

        # Check screening insights (now stored as insights array from real AI)
        screening_insights = json.loads(analysis_result.screening_insights)
        # Real AI returns insights as array
        assert isinstance(screening_insights, list)
        assert len(screening_insights) == 2
        assert screening_insights[0]["category"] == "technical_skills"
        assert (
            screening_insights[0]["description"]
            == "Strong technical skills demonstrated"
        )
        assert screening_insights[1]["category"] == "collaboration"
        assert (
            screening_insights[1]["description"] == "Excellent collaboration patterns"
        )

        # Check the new field mappings
        # technical_patterns stores technical_assessment (object)
        technical_patterns = json.loads(analysis_result.technical_patterns)
        assert technical_patterns["summary"] == "Strong technical foundation"
        assert technical_patterns["details"] == ["Clean code", "Good patterns"]

        # collaboration_patterns stores professional_practices (object)
        collaboration_patterns = json.loads(analysis_result.collaboration_patterns)
        assert collaboration_patterns["summary"] == "Excellent collaboration"
        assert collaboration_patterns["details"] == ["Code reviews", "Documentation"]

        # quality_indicators stores communication_skills (object)
        quality_indicators = json.loads(analysis_result.quality_indicators)
        assert quality_indicators["summary"] == "Clear communication"
        assert quality_indicators["details"] == ["Well-documented code"]

        # temporal_insights stores growth_indicators (object)
        temporal_insights = json.loads(analysis_result.temporal_insights)
        assert temporal_insights["summary"] == "Steady growth"
        assert temporal_insights["details"] == ["Consistent learning"]

        # skill_evolution stores questions (array)
        skill_evolution = json.loads(analysis_result.skill_evolution)
        assert len(skill_evolution) == 1
        assert skill_evolution[0]["question"] == "How do you approach testing?"

        # behavioral_analysis stores recommendations (array)
        behavioral_analysis = json.loads(analysis_result.behavioral_analysis)
        assert len(behavioral_analysis) == 1
        assert behavioral_analysis[0]["text"] == "Focus on system design"

        # security_practices stores green_flags (array)
        security_practices = json.loads(analysis_result.security_practices)
        assert len(security_practices) == 2
        assert "Excellent documentation practices" in security_practices

        # context_alignment stores red_flags (array)
        context_alignment = json.loads(analysis_result.context_alignment)
        assert len(context_alignment) == 1
        assert "Limited recent activity" in context_alignment

        # verification_gaps stores areas_to_explore (array)
        verification_gaps = json.loads(analysis_result.verification_gaps)
        assert len(verification_gaps) == 2
        assert "System design" in verification_gaps

        # Check consent and training eligibility
        assert analysis_result.training_eligible is True
        assert analysis_result.allow_training is True

        data_consent = json.loads(analysis_result.data_consent)
        assert data_consent["user_id"] == "test-user-123"
        assert data_consent["training_usage"] is True
        assert data_consent["tier"] == "PROFESSIONAL"

        # Verify commit was called
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_legacy_analysis(
        self, mock_db_session, mock_user, legacy_analysis_response
    ):
        """Test storing legacy analysis maintains scores."""
        from github_analyzer.api.routes.analysis import _store_analysis_result

        await _store_analysis_result(
            db=mock_db_session,
            user=mock_user,
            repository_url="https://github.com/owner/legacy-repo",
            repository_name="owner/legacy-repo",
            context="enterprise",
            analysis_response=legacy_analysis_response,
            processing_time_ms=3100,
        )

        analysis_result = mock_db_session.add.call_args[0][0]

        # Check it's marked as legacy
        assert analysis_result.analysis_method == "legacy"

        # After Great Purge, no more scores even for legacy
        assert not hasattr(analysis_result, "overall_score")
        assert not hasattr(analysis_result, "confidence_score")
        assert not hasattr(analysis_result, "recommendation")

        # Evidence fields should be None for legacy
        assert analysis_result.evidence_patterns is None
        assert analysis_result.screening_insights is None
        assert analysis_result.technical_patterns is None

    @pytest.mark.asyncio
    async def test_store_analysis_with_free_tier_consent(
        self, mock_db_session, mock_free_user, evidence_based_analysis_response
    ):
        """Test storing analysis with free tier default consent."""
        from github_analyzer.api.routes.analysis import _store_analysis_result

        await _store_analysis_result(
            db=mock_db_session,
            user=mock_free_user,
            repository_url="https://github.com/owner/test-repo",
            repository_name="owner/test-repo",
            context="startup",
            analysis_response=evidence_based_analysis_response,
            processing_time_ms=5200,
        )

        analysis_result = mock_db_session.add.call_args[0][0]

        # Free tier defaults to opt-in for training
        assert analysis_result.training_eligible is True
        assert analysis_result.allow_training is True

        data_consent = json.loads(analysis_result.data_consent)
        assert data_consent["tier"] == "FREE"
        assert data_consent["training_usage"] is True
        assert data_consent["anonymized"] is True

    @pytest.mark.asyncio
    async def test_store_analysis_with_opt_out_consent(
        self, mock_db_session, evidence_based_analysis_response
    ):
        """Test storing analysis when user has opted out of training."""
        # Create user who opted out
        opt_out_user = MagicMock(spec=User)
        opt_out_user.user_id = "opt-out-user"
        opt_out_user.email = "optout@example.com"
        opt_out_user.subscription_plan = SubscriptionPlan.PROFESSIONAL
        opt_out_user.privacy_preferences = json.dumps(
            {
                "training_usage": False,  # Opted out
                "anonymized": True,
            }
        )

        from github_analyzer.api.routes.analysis import _store_analysis_result

        await _store_analysis_result(
            db=mock_db_session,
            user=opt_out_user,
            repository_url="https://github.com/owner/test-repo",
            repository_name="owner/test-repo",
            context="startup",
            analysis_response=evidence_based_analysis_response,
            processing_time_ms=5200,
        )

        analysis_result = mock_db_session.add.call_args[0][0]

        # Should NOT be eligible for training
        assert analysis_result.training_eligible is False
        assert analysis_result.allow_training is False

        data_consent = json.loads(analysis_result.data_consent)
        assert data_consent["training_usage"] is False

    @pytest.mark.asyncio
    async def test_store_analysis_with_batch_id(
        self, mock_db_session, mock_user, evidence_based_analysis_response
    ):
        """Test storing analysis as part of a batch."""
        from github_analyzer.api.routes.analysis import _store_analysis_result

        batch_id = "batch-123-456"
        await _store_analysis_result(
            db=mock_db_session,
            user=mock_user,
            repository_url="https://github.com/owner/test-repo",
            repository_name="owner/test-repo",
            context="startup",
            analysis_response=evidence_based_analysis_response,
            processing_time_ms=5200,
            batch_id=batch_id,
        )

        analysis_result = mock_db_session.add.call_args[0][0]
        assert analysis_result.batch_id == batch_id

    @pytest.mark.asyncio
    async def test_store_analysis_handles_missing_evidence_fields(
        self, mock_db_session, mock_user
    ):
        """Test storing analysis with partial evidence fields."""
        # Create response with minimal evidence fields
        minimal_response = MagicMock()
        minimal_response.repository_url = "https://github.com/owner/minimal-repo"
        minimal_response.analysis = {
            "evidence_patterns": {"basic": ["Some pattern"]},
            "screening_insights": {"overall_impression": "Good"},
            # Missing other evidence fields
        }
        minimal_response.metadata = {"response_time_seconds": 2.0}

        def model_dump(mode=None):
            return {
                "repository_url": minimal_response.repository_url,
                "analysis": minimal_response.analysis,
                "metadata": minimal_response.metadata,
            }

        minimal_response.model_dump = model_dump

        from github_analyzer.api.routes.analysis import _store_analysis_result

        await _store_analysis_result(
            db=mock_db_session,
            user=mock_user,
            repository_url="https://github.com/owner/minimal-repo",
            repository_name="owner/minimal-repo",
            context="startup",
            analysis_response=minimal_response,
            processing_time_ms=2000,
        )

        analysis_result = mock_db_session.add.call_args[0][0]

        # Should still be marked as evidence-based
        assert analysis_result.analysis_method == "evidence_based"

        # Check that missing fields are None
        assert analysis_result.technical_patterns is None
        assert analysis_result.collaboration_patterns is None
        assert analysis_result.quality_indicators is None
        assert analysis_result.temporal_insights is None

        # But required fields should be present
        assert analysis_result.evidence_patterns is not None
        assert analysis_result.screening_insights is not None

    @pytest.mark.asyncio
    async def test_store_analysis_error_handling(
        self, mock_db_session, mock_user, evidence_based_analysis_response
    ):
        """Test error handling during storage."""
        # Simulate database error
        mock_db_session.commit.side_effect = Exception("Database error")

        from github_analyzer.api.routes.analysis import _store_analysis_result

        # Should not raise, just return None on error
        analysis_id = await _store_analysis_result(
            db=mock_db_session,
            user=mock_user,
            repository_url="https://github.com/owner/test-repo",
            repository_name="owner/test-repo",
            context="startup",
            analysis_response=evidence_based_analysis_response,
            processing_time_ms=5200,
        )

        assert analysis_id is None
        mock_db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_analysis_full_evidence_extraction(
        self, mock_db_session, mock_user
    ):
        """Test complete evidence extraction from complex analysis."""
        # Create comprehensive analysis response
        comprehensive_response = MagicMock()
        comprehensive_response.repository_url = (
            "https://github.com/owner/comprehensive-repo"
        )
        comprehensive_response.analysis = {
            "evidence_patterns": {
                "code_quality": ["Pattern 1", "Pattern 2"],
                "testing": ["Test pattern 1", "Test pattern 2"],
            },
            "insights": [
                {
                    "category": "overall_impression",
                    "description": "Excellent candidate",
                    "evidence": ["Strong architecture", "Great testing"],
                },
                {
                    "category": "areas_to_explore",
                    "description": "Further exploration needed",
                    "evidence": ["Scalability", "Security"],
                },
            ],
            "evidence": {
                "technical_patterns": ["Microservices", "Event-driven"],
                "collaboration_patterns": ["PR reviews", "Mentoring"],
                "quality_indicators": ["100% coverage", "E2E tests"],
                "temporal_insights": {
                    "growth_rate": "accelerating",
                    "consistency": "high",
                    "recent_activity": "very active",
                },
                "skill_evolution": {
                    "learning_velocity": "very fast",
                    "skill_breadth": "expanding",
                    "depth_indicators": ["Advanced patterns", "Novel solutions"],
                },
                "behavioral_analysis": {
                    "work_style": "collaborative",
                    "communication": "excellent",
                    "leadership": "emerging",
                },
                "security_practices": {
                    "secure_coding": True,
                    "vulnerability_handling": "proactive",
                    "security_awareness": "high",
                },
            },
            "context_alignment": {
                "alignment": "excellent",
                "specific_strengths": ["Startup experience", "Fast iteration"],
                "relevant_patterns": ["MVP development", "Rapid prototyping"],
            },
            "verification_gaps": ["Live coding", "Architecture discussion"],
            "evidence_strength": "very high",
        }
        comprehensive_response.metadata = {
            "response_time_seconds": 8.5,
            "analysis_cost_usd": 0.25,
        }

        def model_dump(mode=None):
            return {
                "repository_url": comprehensive_response.repository_url,
                "analysis": comprehensive_response.analysis,
                "metadata": comprehensive_response.metadata,
            }

        comprehensive_response.model_dump = model_dump

        from github_analyzer.api.routes.analysis import _store_analysis_result

        await _store_analysis_result(
            db=mock_db_session,
            user=mock_user,
            repository_url="https://github.com/owner/comprehensive-repo",
            repository_name="owner/comprehensive-repo",
            context="startup",
            analysis_response=comprehensive_response,
            processing_time_ms=8500,
            token_count=2500,
            api_cost=0.25,
        )

        analysis_result = mock_db_session.add.call_args[0][0]

        # Verify all evidence fields were extracted
        evidence_patterns = json.loads(analysis_result.evidence_patterns)
        assert "code_quality" in evidence_patterns
        assert len(evidence_patterns["code_quality"]) == 2

        # insights is stored as an array from the AI response
        screening_insights = json.loads(analysis_result.screening_insights)
        assert isinstance(screening_insights, list)
        assert len(screening_insights) == 2  # We added 2 insights in the mock

        technical_patterns = json.loads(analysis_result.technical_patterns)
        assert "Microservices" in technical_patterns

        temporal_insights = json.loads(analysis_result.temporal_insights)
        assert temporal_insights["growth_rate"] == "accelerating"
        assert temporal_insights["consistency"] == "high"

        skill_evolution = json.loads(analysis_result.skill_evolution)
        assert skill_evolution["learning_velocity"] == "very fast"

        behavioral_analysis = json.loads(analysis_result.behavioral_analysis)
        assert behavioral_analysis["work_style"] == "collaborative"

        security_practices = json.loads(analysis_result.security_practices)
        assert security_practices["secure_coding"] is True
        assert security_practices["security_awareness"] == "high"

        context_alignment = json.loads(analysis_result.context_alignment)
        assert context_alignment["alignment"] == "excellent"
        assert "Startup experience" in context_alignment["specific_strengths"]

        verification_gaps = json.loads(analysis_result.verification_gaps)
        assert "Live coding" in verification_gaps

        # Verify full analysis is stored
        full_analysis = json.loads(analysis_result.full_analysis)
        assert (
            full_analysis["repository_url"]
            == "https://github.com/owner/comprehensive-repo"
        )

    @pytest.mark.asyncio
    async def test_store_analysis_with_consent_snapshot(
        self, mock_db_session, evidence_based_analysis_response
    ):
        """Test that consent snapshot is properly stored with analysis."""
        # Create user with specific consent settings
        user = MagicMock(spec=User)
        user.user_id = "consent-test-user"
        user.email = "consent@example.com"
        user.subscription_plan = SubscriptionPlan.ENTERPRISE
        user.privacy_preferences = json.dumps(
            {
                "training_usage": True,
                "anonymized": True,
                "retention_period": "5_years",
                "third_party_sharing": False,
            }
        )
        user.consent_version_accepted = CURRENT_CONSENT_VERSION

        from github_analyzer.api.routes.analysis import _store_analysis_result

        await _store_analysis_result(
            db=mock_db_session,
            user=user,
            repository_url="https://github.com/owner/test-repo",
            repository_name="owner/test-repo",
            context="enterprise",
            analysis_response=evidence_based_analysis_response,
            processing_time_ms=5200,
        )

        analysis_result = mock_db_session.add.call_args[0][0]

        # Check consent snapshot
        data_consent = json.loads(analysis_result.data_consent)
        assert data_consent["user_id"] == "consent-test-user"
        assert data_consent["training_usage"] is True
        assert data_consent["anonymized"] is True
        assert data_consent["retention_period"] == "5_years"
        assert data_consent["third_party_sharing"] is False
        assert data_consent["tier"] == "ENTERPRISE"
        assert data_consent["consent_version"] == CURRENT_CONSENT_VERSION
        assert "snapshot_date" in data_consent

        # Verify training eligibility based on consent
        assert analysis_result.training_eligible is True
        assert analysis_result.allow_training is True
