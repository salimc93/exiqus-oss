# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Portfolio Analysis API request models.

Pydantic models for portfolio analysis API request validation.
"""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class PortfolioAnalyzeRequest(BaseModel):
    """Request model for portfolio analysis."""

    github_username: str = Field(
        ...,
        min_length=1,
        max_length=39,  # GitHub username max length
        description="GitHub username to analyze",
        json_schema_extra={"example": "torvalds"},
    )
    context: str = Field(
        default="enterprise",
        description="Analysis context: startup, enterprise, agency, open_source",
        json_schema_extra={"example": "enterprise"},
    )
    role: str = Field(
        default="senior",
        description="Role level for interview questions: junior, mid, senior",
        json_schema_extra={"example": "senior"},
    )
    github_token: Optional[str] = Field(
        None,
        description="Optional GitHub token for higher rate limits",
    )
    force_refresh: bool = Field(
        default=False,
        description="Force fresh analysis, bypassing cache",
    )
    max_repos: int = Field(
        default=100,
        ge=1,
        le=200,
        description="Maximum number of repos to analyze (1-200)",
    )

    @field_validator("github_username")
    @classmethod
    def validate_github_username(cls, v: str) -> str:
        """Validate GitHub username format."""
        import re

        if not v or not v.strip():
            raise ValueError("GitHub username cannot be empty")

        # GitHub username rules:
        # - Can only contain alphanumeric characters and hyphens
        # - Cannot start or end with a hyphen
        # - Cannot have consecutive hyphens
        # - Maximum 39 characters
        if not re.match(r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$", v):
            raise ValueError(
                "Invalid GitHub username format. Must be 1-39 characters, "
                "contain only alphanumeric characters and hyphens, "
                "and cannot start/end with a hyphen"
            )
        return v

    @field_validator("context")
    @classmethod
    def validate_context(cls, v: str) -> str:
        """Validate context is one of the allowed values."""
        allowed = ["startup", "enterprise", "agency", "open_source"]
        v_lower = v.lower()
        if v_lower not in allowed:
            raise ValueError(f"Context must be one of: {', '.join(allowed)}")
        return v_lower

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate role is one of the allowed values."""
        allowed = ["junior", "mid", "senior"]
        v_lower = v.lower()
        if v_lower not in allowed:
            raise ValueError(f"Role must be one of: {', '.join(allowed)}")
        return v_lower
