# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
FastAPI application main module.

This module sets up the FastAPI application with all necessary middleware,
routes, and configuration for the Exiqus repository analysis API.
"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from guard.middleware import SecurityMiddleware
from guard.models import SecurityConfig as GuardSecurityConfig

from ..database.connection import AsyncSessionLocal, close_database, init_database
from ..utils.config import get_config
from ..utils.logging import get_logger
from .middleware.authentication import APIKeyAuthenticationMiddleware
from .middleware.logging import RequestLoggingMiddleware
from .middleware.rate_limiting import RateLimitingMiddleware
from .middleware.trial_enforcement import TrialEnforcementMiddleware
from .middleware.usage_tracking import UsageTrackingMiddleware
from .routes import (
    analysis,
    analytics,
    api_keys,
    auth,
    batch_history,
    billing,
    billing_admin,
    budget,
    candidate_hub,
    candidates,
    consent,
    contact,
    cost_analytics,
    dashboard,
    health,
    portfolio_analysis,
    pr_analysis,
    priority_support,
    quota,
    scheduler,
    training_data,
    trial_activation,
    trial_admin,
    trial_management,
    trial_status,
)
from .services.redis_service import redis_service
from .services.scheduler_service import get_scheduler_service

logger = get_logger(__name__)
config = get_config()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Handles startup and shutdown events for the FastAPI application.
    """
    # Startup
    logger.info("Starting Exiqus API application")
    logger.info("Environment: %s", config.environment)
    logger.info("API Version: 1.0.0")

    # Initialize database
    await init_database()
    logger.info("Database initialized")

    # Initialize Redis connection
    await redis_service.connect()

    # Initialize scheduler service with database session factory
    scheduler = await get_scheduler_service()
    scheduler.set_session_factory(AsyncSessionLocal)
    await scheduler.start()
    logger.info("Scheduler service started")

    yield

    # Shutdown
    logger.info("Shutting down Exiqus API application")

    # Stop scheduler service
    await scheduler.stop()
    logger.info("Scheduler service stopped")

    # Cleanup Redis connection
    await redis_service.disconnect()

    # Cleanup database connections
    await close_database()


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        FastAPI: Configured FastAPI application instance
    """
    app = FastAPI(
        title="Exiqus API",
        description="AI-Powered Developer Assessment Platform API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Add custom middleware first (they will execute after CORS)
    app.add_middleware(APIKeyAuthenticationMiddleware, enforce_quota=True)
    app.add_middleware(UsageTrackingMiddleware)
    app.add_middleware(TrialEnforcementMiddleware)
    app.add_middleware(
        RateLimitingMiddleware,
        requests_per_minute=60,
        burst_requests_per_minute=120,
        analysis_requests_per_hour=20,  # Increased from 10 to match frontend
    )
    app.add_middleware(RequestLoggingMiddleware)

    # Security middleware for bot/scanner protection (fastapi-guard)
    # Only enabled when ENVIRONMENT is explicitly set to production
    # Protects against:
    # - /.git/config, /.env, /.aws/credentials probes
    # - SQL injection, XSS, command injection attempts
    # - Automated vulnerability scanners
    env_value = os.getenv("ENVIRONMENT", "").lower()
    is_production = env_value in ["production", "prod"]
    if is_production:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        # Get trusted proxies from env (Railway uses 100.64.0.0/10)
        trusted_proxies_env = os.getenv("TRUSTED_PROXIES", "100.64.0.0/10")
        trusted_proxies = [
            p.strip() for p in trusted_proxies_env.split(",") if p.strip()
        ]

        guard_config = GuardSecurityConfig(
            # Penetration detection - blocks common attack patterns
            enable_penetration_detection=True,
            # Auto-ban IPs after suspicious requests
            auto_ban_threshold=5,  # Ban after 5 suspicious requests
            auto_ban_duration=3600,  # Ban for 1 hour
            # Redis for distributed banning across instances
            enable_redis=bool(os.getenv("REDIS_URL")),
            redis_url=redis_url,
            redis_prefix="exiqus:security:",
            # Trust Railway/cloud provider proxies
            trusted_proxies=trusted_proxies,
            # Block common vulnerability scanner user agents
            blocked_user_agents=["sqlmap", "nikto", "nmap", "masscan", "zgrab"],
            # Exclude paths from penetration detection
            # - Health/docs: No security value in scanning these
            # - Analysis endpoints: Legitimately contain URLs in request body
            #   (repository_url, pr_url fields trigger false positives)
            exclude_paths=[
                "/api/v1/health",
                "/health",
                "/docs",
                "/redoc",
                "/openapi.json",
                # Analysis endpoints - protected by JWT auth + rate limiting
                "/api/v1/analyze",
                "/api/v1/portfolio/analyze",
                "/api/v1/pr/analyze",
            ],
        )
        app.add_middleware(SecurityMiddleware, config=guard_config)
        logger.info("Security middleware enabled for production")

    # Configure CORS - MUST be added LAST so it executes FIRST
    # This ensures preflight requests are handled before other middleware

    # Get allowed origins from environment or use defaults
    cors_origins_env = os.getenv("CORS_ALLOWED_ORIGINS", "")

    # Determine if we're in production
    is_production = config.environment.lower() in ["production", "prod"]

    if cors_origins_env:
        # Use explicitly configured origins
        allowed_origins = [
            origin.strip() for origin in cors_origins_env.split(",") if origin.strip()
        ]
    elif is_production:
        # Production: origins must be configured explicitly
        allowed_origins = []
        logger.warning(
            "Production CORS: CORS_ALLOWED_ORIGINS is not set - "
            "cross-origin requests will be rejected. Set it to your "
            "frontend's URL(s)."
        )
    else:
        # Development: Allow localhost origins
        allowed_origins = [
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:3002",
            "http://localhost:3003",
            "http://localhost:3004",
        ]
        logger.info("Development CORS: Allowing localhost origins")

    # Log the configured origins for transparency
    logger.info(f"CORS allowed origins: {allowed_origins}")

    # Configure CORS with secure defaults for production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,  # Configured via environment
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=[
            "Accept",
            "Accept-Language",
            "Content-Type",
            "Authorization",
            "X-API-Key",
            "X-Requested-With",
            "X-CSRF-Token",
        ],
        expose_headers=[
            "Content-Length",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Resource",
            "X-Request-ID",
        ],
        max_age=3600,  # Cache preflight requests for 1 hour
    )

    # Include routers
    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(analysis.router, prefix="/api/v1", tags=["analysis"])
    app.include_router(pr_analysis.router, prefix="/api/v1", tags=["pr_analysis"])
    app.include_router(
        portfolio_analysis.router, prefix="/api/v1", tags=["portfolio_analysis"]
    )
    app.include_router(candidate_hub.router, prefix="/api/v1", tags=["candidate_hub"])
    app.include_router(candidates.router)  # Candidates router already has prefix
    app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
    app.include_router(auth.router, prefix="/api/v1", tags=["authentication"])

    # Import and include email verification routes
    from .routes import email_verification

    app.include_router(
        email_verification.router, prefix="/api/v1", tags=["authentication"]
    )

    app.include_router(api_keys.router)  # API key router already has prefix

    # Import and include admin auth routes
    from .routes import admin_auth, admin_management

    app.include_router(
        admin_auth.router, prefix="/api/v1", tags=["admin_authentication"]
    )
    app.include_router(
        admin_management.router, prefix="/api/v1", tags=["admin_management"]
    )

    app.include_router(billing.router, prefix="/api/v1", tags=["billing"])
    app.include_router(
        billing_admin.router, prefix="/api/v1", tags=["billing_administration"]
    )
    app.include_router(training_data.router, prefix="/api/v1", tags=["training_data"])
    app.include_router(budget.router, prefix="/api/v1", tags=["budget"])
    app.include_router(analytics.router, prefix="/api/v1", tags=["analytics"])
    app.include_router(contact.router, prefix="/api/v1", tags=["contact"])
    app.include_router(consent.router, prefix="/api/v1", tags=["privacy"])
    app.include_router(quota.router, prefix="/api/v1", tags=["quota"])
    app.include_router(
        trial_admin.router, prefix="/api/v1", tags=["trial_administration"]
    )
    app.include_router(
        trial_activation.router, prefix="/api/v1", tags=["trial_activation"]
    )
    app.include_router(
        trial_management.router, prefix="/api/v1", tags=["trial_management"]
    )
    app.include_router(trial_status.router, prefix="/api/v1", tags=["trial_status"])
    app.include_router(batch_history.router)  # Batch history router already has prefix
    app.include_router(
        priority_support.router
    )  # Priority support router already has prefix
    app.include_router(
        cost_analytics.router
    )  # Cost analytics router already has prefix
    app.include_router(scheduler.router)  # Scheduler router already has prefix

    # Add validation error handler to capture and log detailed errors
    from fastapi.exceptions import RequestValidationError

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Log detailed validation error for debugging
        logger.error(
            f"Request validation error for {request.url.path}",
            extra={
                "path": request.url.path,
                "errors": exc.errors(),
                "body": exc.body if hasattr(exc, "body") else None,
            },
        )

        # Convert errors to JSON-serializable format
        errors = []
        for error in exc.errors():
            # Convert ValueError objects to strings in ctx
            serializable_error = error.copy()
            if "ctx" in serializable_error and "error" in serializable_error["ctx"]:
                ctx_error = serializable_error["ctx"]["error"]
                if isinstance(ctx_error, Exception):
                    serializable_error["ctx"]["error"] = str(ctx_error)
            errors.append(serializable_error)

        # Return the error details
        return JSONResponse(
            status_code=400,
            content={
                "detail": "Validation error",
                "errors": errors,
            },
        )

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500, content={"detail": "Internal server error"}
        )

    return app


# Create the FastAPI application instance
app = create_app()
