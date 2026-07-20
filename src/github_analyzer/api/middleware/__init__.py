# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
API middleware modules.

This package contains custom middleware for the FastAPI application
including request logging, rate limiting, authentication, and security headers.
"""

from .authentication import APIKeyAuthenticationMiddleware, APIKeyValidationMiddleware

__all__ = [
    "APIKeyAuthenticationMiddleware",
    "APIKeyValidationMiddleware",
]
