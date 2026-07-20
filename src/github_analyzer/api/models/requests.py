# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
API request models.

This module defines Pydantic models for all API request payloads,
providing validation and documentation for incoming data.
"""

from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, HttpUrl, field_validator

from ...core.context_analyzer import AnalysisContext


class AnalyzeRequest(BaseModel):
    """Request model for single repository analysis."""

    repository_url: HttpUrl = Field(
        ...,
        description="GitHub repository URL to analyze",
        json_schema_extra={"example": "https://github.com/user/repository"},
    )
    context: AnalysisContext = Field(
        default=AnalysisContext.GENERAL, description="Analysis context for evaluation"
    )
    role: str = Field(
        default="senior",
        description="Role level for interview questions: junior, mid, senior",
        json_schema_extra={"example": "senior"},
    )
    github_username: Optional[str] = Field(
        None,
        description=(
            "GitHub username for candidate linking "
            "(extracted from repo URL if not provided, required for paid tiers)"
        ),
        max_length=39,
        json_schema_extra={"example": "torvalds"},
    )
    force_refresh: bool = Field(
        default=False, description="Force fresh analysis, bypassing cache"
    )
    format: Optional[str] = Field(
        default="json",
        description="Output format: json, user_friendly, markdown, html",
        json_schema_extra={"example": "json"},
    )

    @field_validator("repository_url")
    @classmethod
    def validate_github_url(cls, v: str) -> str:
        """Validate that the URL is a GitHub repository URL."""
        url_str = str(v)
        if not url_str.startswith(("https://github.com/", "http://github.com/")):
            raise ValueError("URL must be a GitHub repository URL")
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate role is one of the allowed values."""
        allowed = ["junior", "mid", "senior"]
        v_lower = v.lower()
        if v_lower not in allowed:
            raise ValueError(f"Role must be one of: {', '.join(allowed)}")
        return v_lower


class RepositoryRequest(BaseModel):
    """Individual repository request within a batch."""

    repository_url: HttpUrl = Field(..., description="GitHub repository URL to analyze")
    context: AnalysisContext = Field(
        default=AnalysisContext.GENERAL, description="Analysis context for evaluation"
    )
    role: str = Field(
        default="senior",
        description="Role level for interview questions: junior, mid, senior",
        json_schema_extra={"example": "senior"},
    )

    @field_validator("repository_url")
    @classmethod
    def validate_github_url(cls, v: str) -> str:
        """Validate that the URL is a GitHub repository URL."""
        url_str = str(v)
        if not url_str.startswith(("https://github.com/", "http://github.com/")):
            raise ValueError("URL must be a GitHub repository URL")
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate role is one of the allowed values."""
        allowed = ["junior", "mid", "senior"]
        v_lower = v.lower()
        if v_lower not in allowed:
            raise ValueError(f"Role must be one of: {', '.join(allowed)}")
        return v_lower


class BatchAnalyzeRequest(BaseModel):
    """Request model for batch repository analysis."""

    repositories: List[RepositoryRequest] = Field(
        ...,
        description="List of repositories to analyze with their contexts",
        max_length=10,  # Limit batch size
        json_schema_extra={
            "example": [
                {
                    "repository_url": "https://github.com/user/repo1",
                    "context": "general",
                },
                {
                    "repository_url": "https://github.com/user/repo2",
                    "context": "startup",
                },
            ]
        },
    )
    concurrency_mode: Optional[str] = Field(
        default="sequential",
        description=(
            "Concurrency mode: 'sequential' (1 at a time, highest quality), "
            "'balanced' (2 at a time, Enterprise/Scale/Scale+), "
            "'fast' (5 at a time, Scale+ only)"
        ),
        json_schema_extra={
            "example": "sequential",
            "enum": ["sequential", "balanced", "fast"],
        },
    )


class CacheInvalidateRequest(BaseModel):
    """Request model for cache invalidation."""

    repository_url: Optional[HttpUrl] = Field(
        None, description="Specific repository URL to invalidate (if None, clears all)"
    )
    pattern: Optional[str] = Field(
        None, description="Cache key pattern to match for invalidation"
    )


class ContactFormRequest(BaseModel):
    """Request model for contact form submission."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Name of the person submitting the form",
        json_schema_extra={"example": "John Doe"},
    )
    email: EmailStr = Field(
        ...,
        description="Email address for contact",
        json_schema_extra={"example": "john.doe@example.com"},
    )
    subject: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Subject of the message",
        json_schema_extra={"example": "Question about Enterprise Plan"},
    )
    message: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Message content",
        json_schema_extra={
            "example": "I'm interested in learning more about the Enterprise Plan features..."
        },
    )


class AdminContactResponseRequest(BaseModel):
    """Request model for admin response to a contact message."""

    admin_response: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Admin response to the contact message",
        json_schema_extra={
            "example": "Thank you for your interest. Our Enterprise Plan includes..."
        },
    )


class PRAnalyzeRequest(BaseModel):
    """Request model for PR analysis."""

    github_username: str = Field(
        ...,
        min_length=1,
        max_length=39,  # GitHub username max length
        description="GitHub username to analyze",
        json_schema_extra={"example": "torvalds"},
    )
    context: str = Field(
        default="OPEN_SOURCE",
        description="Analysis context: STARTUP, ENTERPRISE, AGENCY, OPEN_SOURCE",
        json_schema_extra={"example": "STARTUP"},
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
    include_all_evidence: bool = Field(
        default=False,
        description="Include all evidence items (not just top items)",
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
        allowed = ["STARTUP", "ENTERPRISE", "AGENCY", "OPEN_SOURCE"]
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f"Context must be one of: {', '.join(allowed)}")
        return v_upper

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate role is one of the allowed values."""
        allowed = ["junior", "mid", "senior"]
        v_lower = v.lower()
        if v_lower not in allowed:
            raise ValueError(f"Role must be one of: {', '.join(allowed)}")
        return v_lower
