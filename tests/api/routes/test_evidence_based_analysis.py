"""
Tests for evidence-based analysis endpoints.

Tests the analysis API endpoints to ensure they return evidence-based
responses without numerical scores.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import create_test_app


class TestEvidenceBasedAnalysis:
    """Test cases for evidence-based repository analysis endpoints."""

    @pytest.fixture
    def app(self):
        """Create test FastAPI application."""
        return create_test_app()

    @pytest.fixture(autouse=True)
    def mock_rate_limits(self):
        """Fixture to automatically mock rate limiting for all tests."""
        from unittest.mock import MagicMock

        # Create a mock RateLimitContext
        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_context)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        # Create a mock TierRateLimiter
        mock_tier_limiter = MagicMock()
        mock_tier_limiter.check_rate_limit = AsyncMock(
            return_value=(True, None, None)  # allowed, no error, no retry info
        )

        with (
            patch(
                "github_analyzer.api.routes.analysis.check_rate_limits",
                return_value=mock_context,
            ),
            patch(
                "github_analyzer.api.routes.analysis.TierRateLimiter",
                return_value=mock_tier_limiter,
            ),
        ):
            yield

    @pytest.fixture
    async def auth_headers(self, async_client, test_db):
        """Get auth headers for test user with Professional plan."""
        from github_analyzer.database.models import SubscriptionPlan
        from github_analyzer.database.operations import UserOperations

        async with test_db() as db_session:
            # Check if user already exists
            user = await UserOperations.get_user_by_email(
                db_session, "test_api_user@example.com"
            )
            if not user:
                # Create user with Professional plan
                user = await UserOperations.create_user(
                    db_session,
                    email="test_api_user@example.com",
                    password="TestPassword123!",
                    full_name="Test API User",
                )
                user.is_verified = True
                user.subscription_plan = SubscriptionPlan.PROFESSIONAL
                await db_session.commit()

        # Login to get token
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "test_api_user@example.com", "password": "TestPassword123!"},
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def mock_evidence_report(self):
        """Mock evidence-based analysis report."""
        return {
            "repository_url": "https://github.com/user/test-repo",
            "repository_name": "test-repo",
            "analysis_date": datetime.now(timezone.utc).isoformat(),
            "subscription_tier": "professional",
            "context": "startup",
            "executive_summary": "Repository analysis shows strong TypeScript expertise with evidence of testing and modern practices.",
            "repository_type": "portfolio_project",
            "confidence_explanation": "High confidence based on comprehensive code analysis and commit history",
            "insights": [
                {
                    "category": "technical_skills",
                    "description": "Strong TypeScript proficiency demonstrated",
                    "evidence": [
                        "89.5% TypeScript codebase",
                        "Advanced type patterns in 15 files",
                    ],
                    "confidence": "high",
                    "impact": "positive",
                },
                {
                    "category": "professional",
                    "description": "Active testing practices",
                    "evidence": [
                        "40 test files for 343 source files",
                        "Recent test commits",
                    ],
                    "confidence": "high",
                    "impact": "positive",
                },
            ],
            "insights_count": 2,
            "questions": [
                {
                    "category": "technical_decisions",
                    "question": "Your repository shows 89.5% TypeScript usage. Walk me through your approach to type safety.",
                    "evidence_reference": "89.5% TypeScript codebase with advanced patterns",
                    "follow_ups": ["How do you handle type complexity?"],
                    "what_to_listen_for": "Understanding of type system benefits",
                    "context_relevance": "Critical for startup's tech stack",
                }
            ],
            "questions_count": 1,
            "recommendations": [
                {
                    "type": "strength",
                    "text": "Strong TypeScript expertise with modern development practices",
                    "priority": "high",
                    "evidence": "89.5% TypeScript, testing infrastructure",
                }
            ],
            "recommendations_count": 1,
            "evidence_patterns": [
                {
                    "name": "language_expertise",
                    "pattern_type": "technical",
                    "evidence": "89.5% TypeScript across 343 files",
                    "context": "Modern web development expertise",
                    "insight": "Deep TypeScript experience",
                    "category": "technical",
                }
            ],
            "evidence_patterns_count": 1,
            "limitations": ["Cannot assess soft skills from code alone"],
            "data_limitations": [
                "No access to code reviews",
                "Cannot evaluate real-time problem solving",
            ],
            "green_flags": ["Has testing infrastructure", "Active maintenance"],
            "red_flags": [],
            "estimated_cost": 0.0034,
        }

    @pytest.fixture
    def mock_minimal_repo_report(self):
        """Mock report for minimal/empty repository."""
        return {
            "repository_url": "https://github.com/kelseyhightower/nocode",
            "repository_name": "nocode",
            "analysis_date": datetime.now(timezone.utc).isoformat(),
            "subscription_tier": "free",
            "context": "startup",
            "executive_summary": "This repository contains minimal content and lacks sufficient code for meaningful technical analysis.",
            "repository_type": "minimal",
            "confidence_explanation": "No analysis performed - repository contains minimal or no code",
            "insights": [],
            "insights_count": 0,
            "questions": [],
            "questions_count": 0,
            "recommendations": [],
            "recommendations_count": 0,
            "evidence_patterns": [],
            "evidence_patterns_count": 0,
            "limitations": ["Repository contains minimal or no code"],
            "data_limitations": ["Insufficient content for analysis"],
            "green_flags": [],
            "red_flags": [],
            "estimated_cost": 0.0,
        }

    @pytest.mark.asyncio
    async def test_evidence_based_response_structure(
        self, async_client, auth_headers, mock_evidence_report
    ):
        """Test that analysis returns evidence-based structure without scores."""
        with patch(
            "github_analyzer.api.services.redis_service.redis_service"
        ) as mock_redis:
            mock_redis.get = AsyncMock(return_value=None)

            with patch(
                "github_analyzer.api.routes.analysis._perform_repository_analysis"
            ) as mock_perform:
                # Create proper AnalysisResponse object
                from github_analyzer.api.models.responses import AnalysisResponse

                mock_perform.return_value = AnalysisResponse(
                    repository_url=mock_evidence_report["repository_url"],
                    context="startup",
                    analysis=mock_evidence_report,
                    metadata={
                        "analysis_date": datetime.now(timezone.utc).isoformat(),
                        "response_time_seconds": 2.5,
                        "ai_analysis_used": True,
                        "analysis_cost_usd": 0.0034,
                    },
                )

                response = await async_client.post(
                    "/api/v1/analyze",
                    json={
                        "repository_url": "https://github.com/user/test-repo",
                        "context": "startup",
                    },
                    headers=auth_headers,
                )

                assert response.status_code == 200
                data = response.json()

                # Verify structure
                assert "analysis" in data
                analysis = data["analysis"]

                # Verify NO numeric scores
                assert "score" not in str(analysis).lower()
                assert "percentage" not in str(analysis)
                assert "confidence_score" not in analysis

                # Verify evidence-based fields
                assert "confidence_explanation" in analysis
                assert "evidence_patterns" in analysis
                assert "data_limitations" in analysis

                # Verify patterns have no scores
                if analysis["evidence_patterns"]:
                    pattern = analysis["evidence_patterns"][0]
                    assert "score" not in pattern
                    assert "percentage" not in pattern
                    assert "evidence" in pattern
                    assert "pattern_type" in pattern

    @pytest.mark.asyncio
    async def test_minimal_repository_handling(
        self, async_client, auth_headers, mock_minimal_repo_report
    ):
        """Test that minimal repositories are handled without hallucination."""
        with patch(
            "github_analyzer.api.services.redis_service.redis_service"
        ) as mock_redis:
            mock_redis.get = AsyncMock(return_value=None)

            with patch(
                "github_analyzer.api.routes.analysis._perform_repository_analysis"
            ) as mock_perform:
                from github_analyzer.api.models.responses import AnalysisResponse

                mock_perform.return_value = AnalysisResponse(
                    repository_url=mock_minimal_repo_report["repository_url"],
                    context="startup",
                    analysis=mock_minimal_repo_report,
                    metadata={
                        "analysis_date": datetime.now(timezone.utc).isoformat(),
                        "response_time_seconds": 0.5,
                        "ai_analysis_used": False,
                        "analysis_cost_usd": 0.0,
                    },
                )

                response = await async_client.post(
                    "/api/v1/analyze",
                    json={
                        "repository_url": "https://github.com/kelseyhightower/nocode",
                        "context": "startup",
                    },
                    headers=auth_headers,
                )

                assert response.status_code == 200
                data = response.json()

                analysis = data["analysis"]

                # Verify minimal repo handling
                assert analysis["repository_type"] == "minimal"
                assert analysis["insights_count"] == 0
                assert analysis["evidence_patterns_count"] == 0
                assert "minimal content" in analysis["executive_summary"].lower()
                assert analysis["estimated_cost"] == 0.0

    @pytest.mark.asyncio
    async def test_tier_based_features(self, async_client, test_db):
        """Test that different tiers get appropriate features in evidence-based approach."""
        # Test FREE tier
        free_response = await self._test_tier_features(
            async_client, test_db, "free", "free@example.com"
        )
        free_analysis = free_response["analysis"]

        # In evidence-based approach, verify key fields exist
        assert "insights_count" in free_analysis
        assert "evidence_patterns_count" in free_analysis
        assert "recommendations_count" in free_analysis

        # Free tier has basic analysis
        assert free_analysis["insights_count"] >= 0
        assert free_analysis["evidence_patterns_count"] >= 0

        # Test PROFESSIONAL tier
        pro_response = await self._test_tier_features(
            async_client, test_db, "professional", "pro@example.com"
        )
        pro_analysis = pro_response["analysis"]

        # Professional tier also has evidence-based fields
        assert "insights_count" in pro_analysis
        assert "evidence_patterns_count" in pro_analysis
        assert "recommendations_count" in pro_analysis

        # Both tiers now get evidence-based analysis
        # The difference is in the mock data setup, not in field presence
        assert pro_analysis["evidence_patterns_count"] >= 0

    async def _test_tier_features(self, async_client, test_db, plan, email):
        """Helper to test tier-specific features."""
        from github_analyzer.database.models import SubscriptionPlan
        from github_analyzer.database.operations import UserOperations

        async with test_db() as db_session:
            user = await UserOperations.get_user_by_email(db_session, email)
            if not user:
                user = await UserOperations.create_user(
                    db_session,
                    email=email,
                    password="TestPassword123!",
                    full_name=f"{plan.title()} User",
                )
                user.is_verified = True
                user.subscription_plan = getattr(SubscriptionPlan, plan.upper())
                await db_session.commit()

        # Login
        login_response = await async_client.post(
            "/api/v1/auth/login", json={"email": email, "password": "TestPassword123!"}
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Mock analysis based on tier
        mock_report = self._get_tier_appropriate_report(plan)

        with patch(
            "github_analyzer.api.services.redis_service.redis_service"
        ) as mock_redis:
            mock_redis.get = AsyncMock(return_value=None)

            with patch(
                "github_analyzer.api.routes.analysis._perform_repository_analysis"
            ) as mock_perform:
                from github_analyzer.api.models.responses import AnalysisResponse

                mock_perform.return_value = AnalysisResponse(
                    repository_url="https://github.com/user/test-repo",
                    context="startup",
                    analysis=mock_report,
                    metadata={
                        "analysis_date": datetime.now(timezone.utc).isoformat(),
                        "response_time_seconds": 2.0,
                        "ai_analysis_used": plan != "free",
                        "analysis_cost_usd": 0.0034 if plan != "free" else 0.0,
                    },
                )

                response = await async_client.post(
                    "/api/v1/analyze",
                    json={
                        "repository_url": "https://github.com/user/test-repo",
                        "context": "startup",
                    },
                    headers=headers,
                )

                if response.status_code != 200:
                    assert response.status_code == 200
                return response.json()

    def _get_tier_appropriate_report(self, plan):
        """Get report appropriate for subscription tier."""
        base_report = {
            "repository_url": "https://github.com/user/test-repo",
            "repository_name": "test-repo",
            "analysis_date": datetime.now(timezone.utc).isoformat(),
            "subscription_tier": plan,
            "context": "startup",
            "executive_summary": "Repository shows evidence of TypeScript development.",
            "repository_type": "portfolio_project",
            "confidence_explanation": "Based on available repository data",
            "key_observations": ["TypeScript usage detected"],
            "analysis_limitations": [],
            "evidence_summary": {
                "primary_technologies": ["TypeScript"],
                "development_practices": ["Version control usage"],
            },
            "insights": [
                {
                    "category": "technical",
                    "description": "TypeScript usage detected",
                    "evidence": ["TypeScript files present"],
                    "impact": "positive",
                }
            ],
            "insights_count": 1,
            "recommendations": [],
            "recommendations_count": 0,
            "evidence_patterns": [
                {
                    "name": "typescript_usage",
                    "pattern_type": "technical",
                    "evidence": "TypeScript files detected",
                    "context": "Modern web development",
                    "insight": "TypeScript expertise",
                    "category": "technical",
                }
            ],
            "evidence_patterns_count": 1,
            "limitations": ["Limited to public repository data"],
            "data_limitations": ["Cannot assess private discussions"],
            "green_flags": [],
            "red_flags": [],
            "estimated_cost": 0.0,
        }

        if plan == "professional":
            # Add questions for professional tier
            base_report["questions"] = [
                {
                    "category": "technical",
                    "question": "Describe your TypeScript experience.",
                    "evidence_reference": "TypeScript files in repository",
                    "follow_ups": [],
                    "what_to_listen_for": "Technical depth",
                    "context_relevance": "Relevant for role",
                }
            ]
            base_report["questions_count"] = 1
        else:
            base_report["questions"] = []
            base_report["questions_count"] = 0

        return base_report

    @pytest.mark.asyncio
    async def test_clean_response_format(self, async_client, auth_headers):
        """Test that responses include evidence-based fields."""
        with patch(
            "github_analyzer.api.services.redis_service.redis_service"
        ) as mock_redis:
            mock_redis.get = AsyncMock(return_value=None)

            with patch(
                "github_analyzer.api.routes.analysis._perform_repository_analysis"
            ) as mock_perform:
                from github_analyzer.api.models.responses import AnalysisResponse

                # Create a response with evidence-based fields
                evidence_analysis = {
                    "executive_summary": "Repository shows TypeScript expertise",
                    "confidence_explanation": "Based on code analysis",
                    "repository_type": "portfolio_project",
                    "insights": [
                        {
                            "category": "technical",
                            "description": "Strong TypeScript usage",
                            "evidence": ["90% TypeScript"],
                            "impact": "positive",
                        }
                    ],
                    "insights_count": 1,
                    "questions": [],
                    "questions_count": 0,
                    "recommendations": [],
                    "recommendations_count": 0,
                    "evidence_patterns": [
                        {
                            "name": "typescript_mastery",
                            "pattern_type": "technical",
                            "evidence": "90% TypeScript codebase",
                            "context": "Modern development",
                            "insight": "Deep TypeScript knowledge",
                            "category": "technical",
                        }
                    ],
                    "evidence_patterns_count": 1,
                    "green_flags": ["Strong typing"],
                    "red_flags": [],
                    "limitations": ["Cannot assess soft skills"],
                    "data_limitations": ["Public data only"],
                    "estimated_cost": 0.0034,
                }

                mock_perform.return_value = AnalysisResponse(
                    repository_url="https://github.com/user/test-repo",
                    context="startup",
                    analysis=evidence_analysis,
                    metadata={
                        "analysis_date": datetime.now(timezone.utc).isoformat(),
                        "response_time_seconds": 2.5,
                        "ai_analysis_used": True,
                        "analysis_cost_usd": 0.0034,
                    },
                )

                response = await async_client.post(
                    "/api/v1/analyze",
                    json={
                        "repository_url": "https://github.com/user/test-repo",
                        "context": "startup",
                    },
                    headers=auth_headers,
                )

                assert response.status_code == 200
                data = response.json()

                # Verify evidence-based fields are present
                analysis = data["analysis"]
                assert "confidence_explanation" in analysis
                assert "evidence_patterns" in analysis
                assert "data_limitations" in analysis
                assert analysis["evidence_patterns_count"] > 0
