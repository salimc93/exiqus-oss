# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Health check and monitoring endpoints.

This module provides endpoints for service health checks, metrics,
and operational monitoring.
"""

import time
from datetime import datetime, timezone
from typing import Any, Dict, Union

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import text

from ...database.connection import AsyncSessionLocal
from ...utils.config import get_config
from ...utils.logging import get_logger
from ..models.responses import HealthResponse, MetricsResponse
from ..services.redis_service import redis_service

logger = get_logger(__name__)
config = get_config()
router = APIRouter()

# Application startup time for uptime calculation
_start_time = time.time()

# Simple in-memory metrics (replace with Redis in Phase 2)
_metrics = {
    "total_requests": 0,
    "total_response_time": 0.0,
    "cache_hits": 0,
    "cache_misses": 0,
}


async def _check_database() -> bool:
    """Check database connectivity."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        return False


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns the current health status of the API service
    including basic system information and dependency checks.

    Returns:
        HealthResponse: Current health status and metadata
    """
    try:
        # Check database connectivity
        db_healthy = await _check_database()

        # Check Redis connectivity
        redis_healthy = redis_service.is_connected()

        # Determine overall health status
        status = "healthy" if db_healthy and redis_healthy else "degraded"

        return HealthResponse(
            status=status,
            timestamp=datetime.now(timezone.utc),
            version="1.0.0",
            environment=config.environment,
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


@router.get("/health/ready", response_model=None)
async def readiness_check() -> Union[Dict[str, Any], JSONResponse]:
    """
    Readiness check endpoint for Kubernetes deployments.

    Verifies that the service is ready to handle requests.

    Returns:
        Dict: Readiness status
    """
    try:
        # Check critical dependencies here
        # (database, Redis, external APIs, etc.)

        # Check dependencies
        db_healthy = await _check_database()
        redis_healthy = redis_service.is_connected()

        # Determine readiness status
        all_ready = db_healthy and redis_healthy
        overall_status = "ready" if all_ready else "not_ready"

        return {
            "status": overall_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": {
                "api": "ready",
                "database": "ready" if db_healthy else "not_ready",
                "redis": "ready" if redis_healthy else "not_ready",
            },
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
            },
        )


@router.get("/health/live")
async def liveness_check() -> Dict[str, Any]:
    """
    Liveness check endpoint for Kubernetes deployments.

    Simple check to verify the service is alive.

    Returns:
        Dict: Liveness status
    """
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": int(time.time() - _start_time),
    }


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics() -> MetricsResponse:
    """
    Get API metrics and performance statistics.

    Returns:
        MetricsResponse: Current metrics and statistics
    """
    try:
        uptime = int(time.time() - _start_time)

        # Calculate average response time
        avg_response_time = 0.0
        if _metrics["total_requests"] > 0:
            avg_response_time = (
                _metrics["total_response_time"] / _metrics["total_requests"]
            )

        # Calculate cache hit rate
        total_cache_requests = _metrics["cache_hits"] + _metrics["cache_misses"]
        cache_hit_rate = 0.0
        if total_cache_requests > 0:
            cache_hit_rate = (_metrics["cache_hits"] / total_cache_requests) * 100

        return MetricsResponse(
            total_requests=int(_metrics["total_requests"]),
            cache_hit_rate=cache_hit_rate,
            avg_response_time=avg_response_time,
            active_connections=1,  # Simplified for Phase 1
            uptime_seconds=uptime,
        )
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve metrics: {str(e)}"
        )


@router.get("/cache/status")
async def cache_status() -> Dict[str, Any]:
    """
    Get Redis cache status and statistics.

    Returns:
        Dict: Cache status and statistics
    """
    try:
        if not redis_service.is_connected():
            return {
                "status": "disconnected",
                "message": "Redis cache is not available",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        # Get Redis statistics
        stats = await redis_service.get_stats()

        return {
            "status": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "redis_stats": stats,
        }

    except Exception as e:
        logger.error(f"Cache status check failed: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@router.delete("/cache/clear")
async def clear_cache(pattern: str = "*") -> Dict[str, Any]:
    """
    Clear cache entries matching a pattern.

    Args:
        pattern: Redis pattern to match keys (default: all keys)

    Returns:
        Dict: Number of keys cleared
    """
    try:
        if not redis_service.is_connected():
            raise HTTPException(status_code=503, detail="Redis cache is not available")

        # Security: Only allow specific patterns
        allowed_patterns = ["analysis:*", "rate_limit:*", "*"]
        if pattern not in allowed_patterns:
            raise HTTPException(
                status_code=400,
                detail=f"Pattern '{pattern}' not allowed. Use: {allowed_patterns}",
            )

        cleared_count = await redis_service.clear_pattern(pattern)

        return {
            "status": "success",
            "pattern": pattern,
            "cleared_count": cleared_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cache clear failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")


def update_metrics(response_time: float, cache_hit: bool = False) -> None:
    """
    Update internal metrics counters.

    Args:
        response_time: Request response time in seconds
        cache_hit: Whether the request was a cache hit
    """
    _metrics["total_requests"] += 1
    _metrics["total_response_time"] += response_time

    if cache_hit:
        _metrics["cache_hits"] += 1
    else:
        _metrics["cache_misses"] += 1
