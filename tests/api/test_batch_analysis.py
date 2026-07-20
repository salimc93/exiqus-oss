"""Test batch analysis endpoints."""

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from github_analyzer.api.dependencies import get_current_active_user
from github_analyzer.database.models import AnalysisResult, AnalysisStatus, User


@pytest.fixture
def batch_id():
    """Generate a test batch ID."""
    return str(uuid.uuid4())


@pytest.fixture
def auth_headers():
    """Create authentication headers for testing."""
    return {"Authorization": "Bearer test_token"}


@pytest.fixture
async def mock_user(db_session: AsyncSession):
    """Create a test user."""
    from github_analyzer.database.models import SubscriptionPlan

    user = User(
        user_id="test_user_123",
        email="test@example.com",
        password_hash="hashed_password",
        full_name="Test User",
        is_active=True,
        is_verified=True,
        subscription_plan=SubscriptionPlan.ENTERPRISE,  # Enterprise plan for batch analysis
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture
async def mock_batch_analysis(db_session: AsyncSession, mock_user: User, batch_id: str):
    """Create a test batch analysis record."""
    from github_analyzer.database.models import BatchAnalysis

    batch = BatchAnalysis(
        batch_id=batch_id,
        user_id=mock_user.user_id,
        repository_count=3,
        successful_count=3,
        failed_count=0,
        status=AnalysisStatus.COMPLETED,
        concurrency_mode="sequential",
        contexts=json.dumps(["startup"]),
        total_cost=0.0075,
        processing_time_ms=4500,
        created_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(batch)
    await db_session.commit()
    return batch


@pytest.fixture
async def mock_analysis_results(
    db_session: AsyncSession, mock_user: User, batch_id: str, mock_batch_analysis
):
    """Create test analysis results for a batch."""
    results = []

    # Create 3 analysis results for the batch
    for i in range(3):
        analysis_data = {
            "executive_summary": {
                "summary": f"Test analysis {i}",
                "recommendation": "Evidence-based analysis",
            },
            "evidence_patterns": {
                "strong_testing": ["Has 100% test coverage", "Uses CI/CD"],
                "code_quality": ["Follows style guides", "Well documented"],
            },
            "metadata": {
                "repository_url": f"https://github.com/test/repo{i}",
                "analysis_date": datetime.now(timezone.utc).isoformat(),
            },
        }

        result = AnalysisResult(
            id=str(uuid.uuid4()),
            user_id=mock_user.user_id,
            repository_url=f"https://github.com/test/repo{i}",
            repository_name=f"test/repo{i}",
            context="startup",
            # Obsolete scoring fields removed (Great Purge)
            full_analysis=json.dumps(analysis_data),
            evidence_patterns=json.dumps(analysis_data.get("evidence_patterns", {})),
            processing_time_ms=1500 + i * 100,
            api_cost=0.0025,
            batch_id=batch_id,
            analysis_method="evidence_based",
            evidence_version="1.0.0",
        )
        db_session.add(result)
        results.append(result)

    await db_session.commit()
    return results


@pytest.mark.asyncio
async def test_get_batch_status_success(
    async_client: AsyncClient,
    mock_user: User,
    mock_analysis_results: list,
    batch_id: str,
    auth_headers: dict,
):
    """Test successful batch status retrieval."""
    # Mock the authentication dependency
    async_client.app.dependency_overrides[get_current_active_user] = lambda: mock_user

    response = await async_client.get(
        f"/api/v1/analysis/batch/{batch_id}", headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert data["batch_id"] == batch_id
    assert data["status"] == AnalysisStatus.COMPLETED.value
    assert data["total_repositories"] == 3
    assert data["completed"] == 3
    assert data["failed"] == 0
    assert len(data["results"]) == 3

    # Verify individual results
    for i, result in enumerate(data["results"]):
        assert result["repository_url"] == f"https://github.com/test/repo{i}"
        assert result["context"] == "startup"
        assert "analysis" in result
        assert "metadata" in result
        # Evidence-based analysis should have evidence_patterns (not scores)
        analysis = result.get("analysis", {})
        assert "evidence_patterns" in analysis or isinstance(analysis, dict)


@pytest.mark.asyncio
async def test_get_batch_status_not_found(
    async_client: AsyncClient, mock_user: User, auth_headers: dict
):
    """Test batch status for non-existent batch."""
    fake_batch_id = str(uuid.uuid4())

    # Mock the authentication dependency
    async_client.app.dependency_overrides[get_current_active_user] = lambda: mock_user

    response = await async_client.get(
        f"/api/v1/analysis/batch/{fake_batch_id}", headers=auth_headers
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Batch not found"


@pytest.mark.asyncio
async def test_get_batch_status_unauthorized(async_client: AsyncClient, batch_id: str):
    """Test batch status without authentication."""
    response = await async_client.get(f"/api/v1/analysis/batch/{batch_id}")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing authentication token"


@pytest.mark.asyncio
async def test_get_batch_status_other_user(
    async_client: AsyncClient,
    db_session: AsyncSession,
    mock_user: User,
    mock_analysis_results: list,
    batch_id: str,
    auth_headers: dict,
):
    """Test batch status for another user's batch."""
    from github_analyzer.database.models import SubscriptionPlan

    # Create another user with Enterprise tier (to pass tier check)
    other_user = User(
        user_id="other_user_456",
        email="other@example.com",
        password_hash="hashed_password",
        full_name="Other User",
        is_active=True,
        is_verified=True,
        subscription_plan=SubscriptionPlan.ENTERPRISE,
    )
    db_session.add(other_user)
    await db_session.commit()

    # Mock the authentication dependency for the other user
    async_client.app.dependency_overrides[get_current_active_user] = lambda: other_user

    response = await async_client.get(
        f"/api/v1/analysis/batch/{batch_id}", headers=auth_headers
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Batch not found"


@pytest.mark.asyncio
async def test_get_batch_status_soft_deleted(
    async_client: AsyncClient,
    db_session: AsyncSession,
    mock_user: User,
    batch_id: str,
    auth_headers: dict,
):
    """Test batch status with soft-deleted results."""
    # Create one normal and one soft-deleted result
    normal_result = AnalysisResult(
        id=str(uuid.uuid4()),
        user_id=mock_user.user_id,
        repository_url="https://github.com/test/normal",
        repository_name="test/normal",
        context="startup",
        analysis_method="evidence_based",
        evidence_version="1.0",
        full_analysis=json.dumps({"analysis": {}, "metadata": {}}),
        batch_id=batch_id,
    )

    deleted_result = AnalysisResult(
        id=str(uuid.uuid4()),
        user_id=mock_user.user_id,
        repository_url="https://github.com/test/deleted",
        repository_name="test/deleted",
        context="startup",
        analysis_method="evidence_based",
        evidence_version="1.0",
        full_analysis=json.dumps({"analysis": {}, "metadata": {}}),
        batch_id=batch_id,
        deleted_at=datetime.now(timezone.utc),  # Soft deleted
    )

    db_session.add(normal_result)
    db_session.add(deleted_result)
    await db_session.commit()

    # Mock the authentication dependency
    async_client.app.dependency_overrides[get_current_active_user] = lambda: mock_user

    response = await async_client.get(
        f"/api/v1/analysis/batch/{batch_id}", headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()

    # Should only include non-deleted result
    assert data["total_repositories"] == 1
    assert data["completed"] == 1
    assert len(data["results"]) == 1
    assert data["results"][0]["repository_url"] == "https://github.com/test/normal"


@pytest.mark.asyncio
async def test_batch_analysis_creates_batch_id(
    async_client: AsyncClient, mock_user: User, auth_headers: dict
):
    """Test that batch analysis creates and returns a batch_id."""
    # Mock the authentication dependency
    async_client.app.dependency_overrides[get_current_active_user] = lambda: mock_user

    with patch("github_analyzer.api.routes.analysis.GitHubFetcher") as mock_fetcher:
        # Mock repository data
        mock_repo_data = MagicMock()
        mock_repo_data.url = "https://github.com/test/repo1"
        mock_repo_data.name = "repo1"
        mock_repo_data.owner = "test"
        mock_repo_data.description = "Test repo"
        mock_repo_data.stars = 100
        mock_repo_data.size_kb = 1000

        mock_fetcher_instance = mock_fetcher.return_value
        mock_fetcher_instance.check_repository_size.return_value = {"size_kb": 1000}
        mock_fetcher_instance.fetch_repository_data.return_value = mock_repo_data

        # Mock analysis
        with patch(
            "github_analyzer.api.routes.analysis._perform_repository_analysis"
        ) as mock_analysis:
            mock_response = MagicMock()
            mock_response.analysis = {"confidence_score": 0.85}
            mock_response.metadata = {"analysis_cost_usd": 0.01}
            mock_response.model_dump.return_value = {
                "analysis": {"confidence_score": 0.85},
                "metadata": {"analysis_cost_usd": 0.01},
            }
            mock_analysis.return_value = mock_response

            # Make batch request
            request_data = {
                "repositories": [
                    {
                        "repository_url": "https://github.com/test/repo1",
                        "context": "startup",
                    }
                ]
            }

            response = await async_client.post(
                "/api/v1/batch", json=request_data, headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()

            # Verify batch_id is returned
            assert "batch_id" in data["metadata"]
            assert isinstance(data["metadata"]["batch_id"], str)
            assert len(data["metadata"]["batch_id"]) == 36  # UUID length


@pytest.mark.asyncio
async def test_export_batch_csv_success(
    async_client: AsyncClient,
    mock_user: User,
    mock_analysis_results: list,
    batch_id: str,
    auth_headers: dict,
):
    """Test successful CSV export of batch results."""
    # Mock the authentication dependency
    async_client.app.dependency_overrides[get_current_active_user] = lambda: mock_user

    response = await async_client.get(
        f"/api/v1/analysis/batch/{batch_id}/export?format=csv", headers=auth_headers
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert "attachment" in response.headers["content-disposition"]
    assert f"batch_{batch_id}_export.csv" in response.headers["content-disposition"]

    # Verify CSV content
    csv_content = response.text
    lines = csv_content.strip().split("\n")

    # Check header
    assert lines[0].startswith("Repository URL,Repository Name,Context")

    # Check we have data rows (1 header + 3 data rows)
    assert len(lines) == 4

    # Verify first data row contains expected repository
    assert "https://github.com/test/repo0" in lines[1]


@pytest.mark.asyncio
async def test_export_batch_json_success(
    async_client: AsyncClient,
    mock_user: User,
    mock_analysis_results: list,
    batch_id: str,
    auth_headers: dict,
):
    """Test successful JSON export of batch results."""
    # Mock the authentication dependency
    async_client.app.dependency_overrides[get_current_active_user] = lambda: mock_user

    response = await async_client.get(
        f"/api/v1/analysis/batch/{batch_id}/export?format=json", headers=auth_headers
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert "attachment" in response.headers["content-disposition"]
    assert f"batch_{batch_id}_export.json" in response.headers["content-disposition"]

    # Verify JSON content
    data = response.json()
    assert data["batch_id"] == batch_id
    assert "export_date" in data
    assert data["total_analyses"] == 3
    assert len(data["analyses"]) == 3

    # Check first analysis
    first_analysis = data["analyses"][0]
    assert first_analysis["repository_url"] == "https://github.com/test/repo0"
    assert first_analysis["context"] == "startup"
    assert "executive_summary" in first_analysis
    assert "evidence_patterns" in first_analysis
    assert "insights" in first_analysis


@pytest.mark.asyncio
async def test_export_batch_invalid_format(
    async_client: AsyncClient, mock_user: User, batch_id: str, auth_headers: dict
):
    """Test export with invalid format parameter."""
    # Mock the authentication dependency
    async_client.app.dependency_overrides[get_current_active_user] = lambda: mock_user

    response = await async_client.get(
        f"/api/v1/analysis/batch/{batch_id}/export?format=xml", headers=auth_headers
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"] == "Invalid format. Supported formats: csv, json, zip"
    )


@pytest.mark.asyncio
async def test_export_batch_not_found(
    async_client: AsyncClient, mock_user: User, auth_headers: dict
):
    """Test export for non-existent batch."""
    fake_batch_id = str(uuid.uuid4())

    # Mock the authentication dependency
    async_client.app.dependency_overrides[get_current_active_user] = lambda: mock_user

    response = await async_client.get(
        f"/api/v1/analysis/batch/{fake_batch_id}/export", headers=auth_headers
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Batch not found"


@pytest.mark.asyncio
async def test_export_batch_other_user(
    async_client: AsyncClient,
    db_session: AsyncSession,
    mock_user: User,
    mock_analysis_results: list,
    batch_id: str,
    auth_headers: dict,
):
    """Test export for another user's batch."""
    from github_analyzer.database.models import SubscriptionPlan

    # Create another user with Enterprise tier (to pass tier check)
    other_user = User(
        user_id="other_user_456",
        email="other@example.com",
        password_hash="hashed_password",
        full_name="Other User",
        is_active=True,
        is_verified=True,
        subscription_plan=SubscriptionPlan.ENTERPRISE,
    )
    db_session.add(other_user)
    await db_session.commit()

    # Mock the authentication dependency for the other user
    async_client.app.dependency_overrides[get_current_active_user] = lambda: other_user

    response = await async_client.get(
        f"/api/v1/analysis/batch/{batch_id}/export", headers=auth_headers
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Batch not found"


@pytest.mark.asyncio
async def test_export_batch_zip_success(
    async_client: AsyncClient,
    db_session: AsyncSession,
    mock_user: User,
    mock_analysis_results: list,
    batch_id: str,
    auth_headers: dict,
):
    """Test successful ZIP export with PDFs."""
    # Mock the authentication dependency
    async_client.app.dependency_overrides[get_current_active_user] = lambda: mock_user

    response = await async_client.get(
        f"/api/v1/analysis/batch/{batch_id}/export?format=zip", headers=auth_headers
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "attachment" in response.headers["content-disposition"]
    assert f"batch_{batch_id}_export.zip" in response.headers["content-disposition"]

    # Verify ZIP content
    import io
    import zipfile

    zip_buffer = io.BytesIO(response.content)
    with zipfile.ZipFile(zip_buffer, "r") as zip_file:
        # Check files in ZIP
        file_names = zip_file.namelist()

        # Should have HTML files for each analysis
        html_files = [f for f in file_names if f.endswith(".html")]
        assert len(html_files) == len(mock_analysis_results)

        # Should have summary JSON
        assert "batch_summary.json" in file_names

        # Verify HTML files are not empty
        for html_name in html_files:
            html_content = zip_file.read(html_name)
            assert len(html_content) > 0
            # HTML files should contain expected tags
            assert b"<!DOCTYPE html>" in html_content or b"<html" in html_content


@pytest.mark.asyncio
async def test_batch_status_tier_restriction(
    async_client: AsyncClient,
    db_session: AsyncSession,
    batch_id: str,
    auth_headers: dict,
):
    """Test that batch status requires Professional, Enterprise, or Scale+ tier."""
    from github_analyzer.database.models import SubscriptionPlan

    # Create a FREE tier user
    free_user = User(
        user_id="free_user_123",
        email="free@example.com",
        password_hash="hashed_password",
        full_name="Free User",
        is_active=True,
        is_verified=True,
        subscription_plan=SubscriptionPlan.FREE,
    )
    db_session.add(free_user)
    await db_session.commit()

    # Mock the authentication dependency
    async_client.app.dependency_overrides[get_current_active_user] = lambda: free_user

    response = await async_client.get(
        f"/api/v1/analysis/batch/{batch_id}", headers=auth_headers
    )

    assert response.status_code == 403
    assert (
        "require Professional, Enterprise, or Scale+ plan" in response.json()["detail"]
    )


@pytest.mark.asyncio
async def test_batch_export_tier_restriction(
    async_client: AsyncClient,
    db_session: AsyncSession,
    batch_id: str,
    auth_headers: dict,
):
    """Test that batch export requires Professional, Enterprise, or Scale+ tier."""
    from github_analyzer.database.models import SubscriptionPlan

    # Create a BASIC tier user
    basic_user = User(
        user_id="basic_user_123",
        email="basic@example.com",
        password_hash="hashed_password",
        full_name="Basic User",
        is_active=True,
        is_verified=True,
        subscription_plan=SubscriptionPlan.BASIC,
    )
    db_session.add(basic_user)
    await db_session.commit()

    # Mock the authentication dependency
    async_client.app.dependency_overrides[get_current_active_user] = lambda: basic_user

    response = await async_client.get(
        f"/api/v1/analysis/batch/{batch_id}/export", headers=auth_headers
    )

    assert response.status_code == 403
    assert (
        "require Professional, Enterprise, or Scale+ plan" in response.json()["detail"]
    )


@pytest.mark.asyncio
async def test_batch_professional_tier_success(
    async_client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict,
):
    """Test that Professional tier can access batch features."""
    from github_analyzer.database.models import SubscriptionPlan

    # Create a Professional tier user
    pro_user = User(
        user_id="pro_user_123",
        email="pro@example.com",
        password_hash="hashed_password",
        full_name="Pro User",
        is_active=True,
        is_verified=True,
        subscription_plan=SubscriptionPlan.PROFESSIONAL,
    )
    db_session.add(pro_user)
    await db_session.commit()

    # Create BatchAnalysis record first
    batch_id = str(uuid.uuid4())
    from datetime import datetime, timezone

    from github_analyzer.database.models import BatchAnalysis

    batch = BatchAnalysis(
        batch_id=batch_id,
        user_id=pro_user.user_id,
        repository_count=3,
        successful_count=3,
        failed_count=0,
        status=AnalysisStatus.COMPLETED,
        concurrency_mode="sequential",
        contexts=json.dumps(["startup"]),
        total_cost=0.06,
        processing_time_ms=3000,
        created_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(batch)

    # Create some analysis results for this user with a batch_id
    for i in range(3):
        analysis_data = {
            "analysis": {
                "executive_summary": {
                    "summary": f"Professional tier analysis {i}",
                    "recommendation": "Evidence-based analysis",
                },
            },
        }

        result = AnalysisResult(
            id=str(uuid.uuid4()),
            user_id=pro_user.user_id,
            repository_url=f"https://github.com/pro/repo{i}",
            repository_name=f"pro/repo{i}",
            context="startup",
            analysis_method="evidence_based",
            evidence_version="1.0",
            full_analysis=json.dumps(analysis_data),
            processing_time_ms=1000,
            api_cost=0.02,
            batch_id=batch_id,
        )
        db_session.add(result)

    await db_session.commit()

    # Mock the authentication dependency
    async_client.app.dependency_overrides[get_current_active_user] = lambda: pro_user

    # Test batch status endpoint
    response = await async_client.get(
        f"/api/v1/analysis/batch/{batch_id}", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["batch_id"] == batch_id
    assert response.json()["total_repositories"] == 3

    # Test batch export endpoint
    response = await async_client.get(
        f"/api/v1/analysis/batch/{batch_id}/export?format=json", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
