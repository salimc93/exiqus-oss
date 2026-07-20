"""
Tests for health check endpoints.

This module tests all health check and monitoring endpoints
including health, readiness, liveness, and metrics.
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from github_analyzer.api.main import create_app
from github_analyzer.api.routes.health import update_metrics


class TestHealthEndpoints:
    """Test health check endpoints."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        app = create_app()
        return TestClient(app)

    def test_health_check_returns_200(self, client):
        """Test that health check returns 200 status."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_health_check_response_structure(self, client):
        """Test health check response has correct structure."""
        response = client.get("/api/v1/health")
        data = response.json()

        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "environment" in data

        assert data["status"] in [
            "healthy",
            "degraded",
        ]  # Status depends on service availability
        assert data["version"] == "1.0.0"

    def test_health_check_timestamp_is_valid(self, client):
        """Test that health check timestamp is valid."""
        response = client.get("/api/v1/health")
        data = response.json()

        # Parse the timestamp to ensure it's valid
        timestamp = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
        assert isinstance(timestamp, datetime)

    def test_readiness_check_returns_200(self, client):
        """Test that readiness check returns 200 status."""
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 200

    def test_readiness_check_response_structure(self, client):
        """Test readiness check response structure."""
        response = client.get("/api/v1/health/ready")
        data = response.json()

        assert "status" in data
        assert "timestamp" in data
        assert "checks" in data

        assert data["status"] in [
            "ready",
            "not_ready",
        ]  # Status depends on service availability
        assert isinstance(data["checks"], dict)

    def test_liveness_check_returns_200(self, client):
        """Test that liveness check returns 200 status."""
        response = client.get("/api/v1/health/live")
        assert response.status_code == 200

    def test_liveness_check_response_structure(self, client):
        """Test liveness check response structure."""
        response = client.get("/api/v1/health/live")
        data = response.json()

        assert "status" in data
        assert "timestamp" in data
        assert "uptime_seconds" in data

        assert data["status"] == "alive"
        assert isinstance(data["uptime_seconds"], int)
        assert data["uptime_seconds"] >= 0


class TestMetricsEndpoint:
    """Test metrics endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        app = create_app()
        return TestClient(app)

    def test_metrics_returns_200(self, client):
        """Test that metrics endpoint returns 200 status."""
        response = client.get("/api/v1/metrics")
        assert response.status_code == 200

    def test_metrics_response_structure(self, client):
        """Test metrics response has correct structure."""
        response = client.get("/api/v1/metrics")
        data = response.json()

        required_fields = [
            "total_requests",
            "cache_hit_rate",
            "avg_response_time",
            "active_connections",
            "uptime_seconds",
        ]

        for field in required_fields:
            assert field in data

    def test_metrics_data_types(self, client):
        """Test that metrics return correct data types."""
        response = client.get("/api/v1/metrics")
        data = response.json()

        assert isinstance(data["total_requests"], int)
        assert isinstance(data["cache_hit_rate"], (int, float))
        assert isinstance(data["avg_response_time"], (int, float))
        assert isinstance(data["active_connections"], int)
        assert isinstance(data["uptime_seconds"], int)

    def test_metrics_values_are_non_negative(self, client):
        """Test that metric values are non-negative."""
        response = client.get("/api/v1/metrics")
        data = response.json()

        assert data["total_requests"] >= 0
        assert data["cache_hit_rate"] >= 0
        assert data["avg_response_time"] >= 0
        assert data["active_connections"] >= 0
        assert data["uptime_seconds"] >= 0


class TestUpdateMetrics:
    """Test metrics update functionality."""

    def test_update_metrics_increments_counters(self):
        """Test that update_metrics properly increments counters."""
        # Import the metrics dictionary for testing
        from github_analyzer.api.routes.health import _metrics

        initial_requests = _metrics["total_requests"]
        initial_time = _metrics["total_response_time"]
        initial_hits = _metrics["cache_hits"]
        initial_misses = _metrics["cache_misses"]

        # Update with cache hit
        update_metrics(1.5, cache_hit=True)

        assert _metrics["total_requests"] == initial_requests + 1
        assert _metrics["total_response_time"] == initial_time + 1.5
        assert _metrics["cache_hits"] == initial_hits + 1
        assert _metrics["cache_misses"] == initial_misses

        # Update with cache miss
        update_metrics(2.0, cache_hit=False)

        assert _metrics["total_requests"] == initial_requests + 2
        assert _metrics["total_response_time"] == initial_time + 3.5
        assert _metrics["cache_hits"] == initial_hits + 1
        assert _metrics["cache_misses"] == initial_misses + 1
