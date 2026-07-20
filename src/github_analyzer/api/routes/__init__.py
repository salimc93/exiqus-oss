# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
API route modules.

This package contains all FastAPI router modules organized by functionality,
including health checks, analysis endpoints, and administrative functions.
"""

from . import (
    analysis,
    analytics,
    api_keys,
    auth,
    batch_history,
    billing,
    billing_admin,
    budget,
    consent,
    contact,
    cost_analytics,
    email_verification,
    health,
    priority_support,
    quota,
    scheduler,
    training_data,
    trial_activation,
    trial_admin,
    trial_management,
    trial_status,
)

__all__ = [
    "analysis",
    "analytics",
    "api_keys",
    "auth",
    "batch_history",
    "billing",
    "billing_admin",
    "budget",
    "consent",
    "contact",
    "cost_analytics",
    "email_verification",
    "health",
    "priority_support",
    "quota",
    "scheduler",
    "training_data",
    "trial_activation",
    "trial_admin",
    "trial_management",
    "trial_status",
]
