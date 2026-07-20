"""
Tests for analysis storage functionality.
"""

import json
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient

from github_analyzer.database.models import AnalysisResult
from github_analyzer.database.operations import UserOperations


@pytest.fixture
async def auth_user_and_token(async_client, test_db):
    """Create a test user and return user_id and auth token."""
    async with test_db() as db_session:
        user = await UserOperations.create_user(
            db_session,
            email="test_storage@example.com",
            password="TestPassword123!",
            full_name="Test Storage User",
        )
        user.is_verified = True
        await db_session.commit()
        user_id = user.user_id

    # Login to get token
    login_response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "test_storage@example.com", "password": "TestPassword123!"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    return user_id, token


@pytest.mark.asyncio
async def test_analyze_stores_result_in_database(
    async_client: AsyncClient,
    test_db,
    auth_user_and_token,
):
    """Test that analyze endpoint stores results in database."""
    user_id, token = auth_user_and_token

    # Create mock GitHub fetcher
    mock_github_fetcher = MagicMock()
    mock_github_fetcher.check_repository_size.return_value = {
        "size_kb": 1024,
        "file_count": 10,
    }
    mock_github_fetcher.fetch_repository_data.return_value = MagicMock(
        name="test-repo",
        owner="test-user",
        is_private=False,
        size_kb=1024,
        contributors_count=5,
        file_extensions={".py": 10, ".md": 2},
    )

    # Override github fetcher dependency
    from github_analyzer.api.dependencies import get_github_fetcher

    async_client.app.dependency_overrides[get_github_fetcher] = lambda: (
        mock_github_fetcher
    )

    # Mock the analysis pipeline
    from github_analyzer.api.models.responses import AnalysisResponse

    mock_analysis_response = AnalysisResponse(
        repository_url="https://github.com/test-user/test-repo",
        context="general",
        analysis={
            "executive_summary": "Test summary",
            "overall_recommendation": "HIRE",
            "confidence_score": 0.85,
            "repository_type": "portfolio",
            "context_fit_score": 0.90,
            "key_strengths": ["Good code"],
            "primary_concerns": [],
            "analysis_recommendations": ["Proceed"],
            "interview_focus_areas": ["Technical"],
        },
        metadata={
            "analysis_id": "test_id",
            "repository_type": "portfolio",
            "confidence_grade": "B+",
            "ai_analysis_used": False,
            "analysis_cost_usd": 0.0,
            "response_time_seconds": 1.0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cached": False,
            "data_completeness": 0.95,
        },
    )

    with (
        patch(
            "github_analyzer.api.routes.analysis._perform_repository_analysis"
        ) as mock_perform_analysis,
        patch(
            "github_analyzer.api.routes.analysis.TierRateLimiter"
        ) as mock_tier_limiter,
    ):
        # Mock the tier rate limiter to always allow
        from unittest.mock import AsyncMock

        mock_instance = MagicMock()
        mock_instance.check_rate_limit = AsyncMock(
            return_value=(True, None, {})  # allowed, no error, no retry info
        )
        mock_tier_limiter.return_value = mock_instance

        mock_perform_analysis.return_value = mock_analysis_response

        # Make request
        response = await async_client.post(
            "/api/v1/analyze",
            json={
                "repository_url": "https://github.com/test-user/test-repo",
                "context": "general",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    data = response.json()

    # Check that analysis_id is in metadata
    assert "analysis_id" in data["metadata"]
    assert data["metadata"]["stored"] is True

    # Verify database storage
    from sqlalchemy import select

    async with test_db() as db_session:
        query = select(AnalysisResult).where(AnalysisResult.user_id == user_id)
        result = await db_session.execute(query)
        analysis = result.scalar_one_or_none()

        assert analysis is not None
        assert analysis.repository_url == "https://github.com/test-user/test-repo"
        assert analysis.repository_name == "test-user/test-repo"
        assert analysis.context == "general"
        assert analysis.id == data["metadata"]["analysis_id"]


@pytest.mark.asyncio
async def test_get_user_analyses_pagination(
    async_client: AsyncClient,
    test_db,
    auth_user_and_token,
):
    """Test getting user analyses with pagination."""
    user_id, token = auth_user_and_token

    # Create test analyses
    async with test_db() as db_session:
        analyses = []
        for i in range(25):
            analysis = AnalysisResult(
                id=str(uuid.uuid4()),
                user_id=user_id,
                repository_url=f"https://github.com/test-user/repo-{i}",
                repository_name=f"test-user/repo-{i}",
                context="general",
                analysis_method="evidence_based",
                evidence_version="1.0",
                full_analysis=json.dumps(
                    {
                        "analysis": {
                            "evidence_patterns": {},
                            "confidence_explanation": "Evidence-based analysis",
                        }
                    }
                ),
                created_at=datetime.now(timezone.utc) - timedelta(hours=i),
            )
            analyses.append(analysis)
            db_session.add(analysis)

        await db_session.commit()

    # Test first page
    response = await async_client.get(
        "/api/v1/analyses?limit=10", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) == 10
    assert data["has_next"] is True
    assert data["has_prev"] is False
    assert data["total_count"] == 25
    assert data["cursor"] is not None

    # Test second page using cursor
    response = await async_client.get(
        f"/api/v1/analyses?limit=10&cursor={data['cursor']}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) == 10
    assert data["has_next"] is True
    assert data["has_prev"] is True

    # Verify items are in descending order by created_at
    for i in range(len(data["items"]) - 1):
        assert data["items"][i]["created_at"] > data["items"][i + 1]["created_at"]


@pytest.mark.asyncio
async def test_get_analysis_by_id(
    async_client: AsyncClient,
    test_db,
    auth_user_and_token,
):
    """Test getting a specific analysis by ID."""
    user_id, token = auth_user_and_token

    # Create test analysis
    analysis_id = str(uuid.uuid4())
    async with test_db() as db_session:
        analysis = AnalysisResult(
            id=analysis_id,
            user_id=user_id,
            repository_url="https://github.com/test-user/test-repo",
            repository_name="test-user/test-repo",
            context="startup",
            analysis_method="evidence_based",
            evidence_version="1.0",
            full_analysis=json.dumps(
                {
                    "repository_url": "https://github.com/test-user/test-repo",
                    "context": "startup",
                    "analysis": {
                        "summary": "Evidence-based analysis shows strong technical competence",
                        "evidence_strength": {
                            "technical_competence": 85,
                            "communication_skills": 80,
                            "professional_practices": 75,
                            "growth_potential": 90,
                        },
                        "key_insights": ["Good code quality", "Active contributor"],
                        "evidence_patterns": [
                            {
                                "pattern": "active_development",
                                "evidence": "Regular commits and contributions",
                                "strength": "strong",
                            }
                        ],
                        "verification_gaps": ["Limited testing coverage"],
                    },
                    "metadata": {
                        "analysis_cost_usd": 0.002,
                        "response_time_seconds": 12.5,
                    },
                }
            ),
            processing_time_ms=12500,
            api_cost=0.002,
        )
        db_session.add(analysis)
        await db_session.commit()

    # Get analysis by ID
    response = await async_client.get(
        f"/api/v1/analyses/{analysis_id}", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == analysis_id
    assert data["repository_url"] == "https://github.com/test-user/test-repo"
    assert data["context"] == "startup"
    # Check for evidence-based fields
    assert "evidence_strength" in data
    assert data["evidence_strength"]["technical_competence"] == 85
    assert "key_insights" in data
    assert len(data["key_insights"]) > 0
    assert data["processing_time_ms"] == 12500
    assert data["api_cost"] == 0.002
    assert "full_analysis" in data
    assert (
        data["full_analysis"]["analysis"]["summary"]
        == "Evidence-based analysis shows strong technical competence"
    )


@pytest.mark.asyncio
async def test_get_analysis_by_id_not_found(
    async_client: AsyncClient,
    auth_user_and_token,
):
    """Test getting non-existent analysis returns 404."""
    user_id, token = auth_user_and_token
    fake_id = str(uuid.uuid4())

    response = await async_client.get(
        f"/api/v1/analyses/{fake_id}", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Analysis not found"


@pytest.mark.asyncio
async def test_get_analysis_by_id_wrong_user(
    async_client: AsyncClient,
    test_db,
    auth_user_and_token,
):
    """Test that users can't access other users' analyses."""
    user_id, token = auth_user_and_token

    # Create analysis for a different (real) user - Postgres enforces the FK
    analysis_id = str(uuid.uuid4())
    async with test_db() as db_session:
        other_user = await UserOperations.create_user(
            db_session,
            email=f"other_{analysis_id[:8]}@example.com",
            password="OtherPassword123!",
            full_name="Other User",
        )
        await db_session.commit()
        analysis = AnalysisResult(
            id=analysis_id,
            user_id=other_user.user_id,
            repository_url="https://github.com/other/repo",
            repository_name="other/repo",
            context="general",
            full_analysis=json.dumps({"test": "data"}),
        )
        db_session.add(analysis)
        await db_session.commit()

    # Try to access with test user
    response = await async_client.get(
        f"/api/v1/analyses/{analysis_id}", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Analysis not found"


@pytest.mark.asyncio
async def test_delete_analysis(
    async_client: AsyncClient,
    test_db,
    auth_user_and_token,
):
    """Test soft deleting an analysis."""
    user_id, token = auth_user_and_token

    # Create test analysis
    analysis_id = str(uuid.uuid4())
    async with test_db() as db_session:
        analysis = AnalysisResult(
            id=analysis_id,
            user_id=user_id,
            repository_url="https://github.com/test-user/test-repo",
            repository_name="test-user/test-repo",
            context="general",
            full_analysis=json.dumps({"test": "data"}),
        )
        db_session.add(analysis)
        await db_session.commit()

    # Delete analysis
    response = await async_client.delete(
        f"/api/v1/analyses/{analysis_id}", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 204

    # Verify soft delete
    async with test_db() as db_session:
        from sqlalchemy import select

        query = select(AnalysisResult).where(AnalysisResult.id == analysis_id)
        result = await db_session.execute(query)
        analysis = result.scalar_one()

        assert analysis.deleted_at is not None

    # Verify it's not returned in list
    response = await async_client.get(
        "/api/v1/analyses", headers={"Authorization": f"Bearer {token}"}
    )

    data = response.json()
    assert len(data["items"]) == 0

    # Verify it returns 404 when accessed directly
    response = await async_client.get(
        f"/api/v1/analyses/{analysis_id}", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_analysis_not_found(
    async_client: AsyncClient,
    auth_user_and_token,
):
    """Test deleting non-existent analysis returns 404."""
    user_id, token = auth_user_and_token
    fake_id = str(uuid.uuid4())

    response = await async_client.delete(
        f"/api/v1/analyses/{fake_id}", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Analysis not found"


@pytest.mark.asyncio
async def test_cannot_delete_others_analysis(
    async_client: AsyncClient,
    test_db,
    auth_user_and_token,
):
    """Test that users cannot delete other users' analyses."""
    user_id, token = auth_user_and_token

    # Create analysis for a different (real) user - Postgres enforces the FK
    analysis_id = str(uuid.uuid4())
    async with test_db() as db_session:
        other_user = await UserOperations.create_user(
            db_session,
            email=f"other_{analysis_id[:8]}@example.com",
            password="OtherPassword123!",
            full_name="Other User",
        )
        await db_session.commit()
        analysis = AnalysisResult(
            id=analysis_id,
            user_id=other_user.user_id,
            repository_url="https://github.com/other/repo",
            repository_name="other/repo",
            context="general",
            full_analysis=json.dumps({"test": "data"}),
        )
        db_session.add(analysis)
        await db_session.commit()

    # Try to delete with test user
    response = await async_client.delete(
        f"/api/v1/analyses/{analysis_id}", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Analysis not found"

    # Verify the analysis still exists and is not deleted
    async with test_db() as db_session:
        from sqlalchemy import select

        query = select(AnalysisResult).where(AnalysisResult.id == analysis_id)
        result = await db_session.execute(query)
        analysis = result.scalar_one()

        assert analysis.deleted_at is None  # Not deleted


@pytest.mark.asyncio
async def test_analysis_storage_handles_db_errors_gracefully(
    async_client: AsyncClient,
    auth_user_and_token,
):
    """Test that analysis still returns even if storage fails."""
    user_id, token = auth_user_and_token

    # Mock GitHub fetcher
    mock_github_fetcher = MagicMock()
    mock_github_fetcher.check_repository_size.return_value = {
        "size_kb": 1024,
        "file_count": 10,
    }
    mock_github_fetcher.fetch_repository_data.return_value = MagicMock(
        name="test-repo",
        owner="test-user",
        is_private=False,
        size_kb=1024,
        contributors_count=5,
        file_extensions={".py": 10, ".md": 2},
    )

    # Override github fetcher dependency
    from github_analyzer.api.dependencies import get_github_fetcher

    async_client.app.dependency_overrides[get_github_fetcher] = lambda: (
        mock_github_fetcher
    )

    # Mock the analysis pipeline
    from github_analyzer.api.models.responses import AnalysisResponse

    mock_analysis_response = AnalysisResponse(
        repository_url="https://github.com/test-user/test-repo",
        context="general",
        analysis={
            "executive_summary": "Test summary",
            "overall_recommendation": "HIRE",
            "confidence_score": 0.85,
        },
        metadata={
            "analysis_id": "test_id",
            "ai_analysis_used": False,
            "analysis_cost_usd": 0.0,
            "response_time_seconds": 1.0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cached": False,
        },
    )

    # Mock database error
    with (
        patch(
            "github_analyzer.api.routes.analysis._store_analysis_result"
        ) as mock_store,
        patch(
            "github_analyzer.api.routes.analysis._perform_repository_analysis"
        ) as mock_perform_analysis,
        patch(
            "github_analyzer.api.routes.analysis.TierRateLimiter"
        ) as mock_tier_limiter,
    ):
        # Mock the tier rate limiter to always allow
        from unittest.mock import AsyncMock

        mock_instance = MagicMock()
        mock_instance.check_rate_limit = AsyncMock(
            return_value=(True, None, {})  # allowed, no error, no retry info
        )
        mock_tier_limiter.return_value = mock_instance

        mock_store.return_value = None  # Simulate storage failure
        mock_perform_analysis.return_value = mock_analysis_response

        response = await async_client.post(
            "/api/v1/analyze",
            json={
                "repository_url": "https://github.com/test-user/test-repo",
                "context": "general",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        # Should still return successful analysis
        assert response.status_code == 200
        data = response.json()
        assert "analysis" in data
        assert data["metadata"]["stored"] is False


@pytest.mark.asyncio
async def test_get_analyses_excludes_soft_deleted(
    async_client: AsyncClient,
    test_db,
    auth_user_and_token,
):
    """Test that soft-deleted analyses are excluded from listings."""
    user_id, token = auth_user_and_token

    # Create mix of active and deleted analyses
    async with test_db() as db_session:
        for i in range(5):
            analysis = AnalysisResult(
                id=str(uuid.uuid4()),
                user_id=user_id,
                repository_url=f"https://github.com/test-user/repo-{i}",
                repository_name=f"test-user/repo-{i}",
                context="general",
                full_analysis=json.dumps({"test": f"data-{i}"}),
                deleted_at=datetime.now(timezone.utc) if i % 2 == 0 else None,
            )
            db_session.add(analysis)

        await db_session.commit()

    # Get analyses
    response = await async_client.get(
        "/api/v1/analyses", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()

    # Should only return non-deleted analyses (indices 1 and 3)
    assert len(data["items"]) == 2
    assert data["total_count"] == 2

    # Verify all returned items are not deleted
    for item in data["items"]:
        assert (
            "repo-1" in item["repository_name"] or "repo-3" in item["repository_name"]
        )


@pytest.mark.asyncio
async def test_analysis_pagination_edge_cases(
    async_client: AsyncClient,
    test_db,
    auth_user_and_token,
):
    """Test edge cases for pagination."""
    user_id, token = auth_user_and_token

    # Test with no analyses
    response = await async_client.get(
        "/api/v1/analyses", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 0
    assert data["has_next"] is False
    assert data["has_prev"] is False
    assert data["total_count"] == 0

    # Create exactly limit number of analyses
    async with test_db() as db_session:
        for i in range(20):  # Default limit
            analysis = AnalysisResult(
                id=str(uuid.uuid4()),
                user_id=user_id,
                repository_url=f"https://github.com/test-user/repo-{i}",
                repository_name=f"test-user/repo-{i}",
                context="general",
                full_analysis=json.dumps({"test": f"data-{i}"}),
            )
            db_session.add(analysis)
        await db_session.commit()

    # Test with exactly limit items
    response = await async_client.get(
        "/api/v1/analyses?limit=20", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 20
    assert data["has_next"] is False
    assert data["cursor"] is None
