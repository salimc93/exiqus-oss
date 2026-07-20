# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Pydantic models for analysis results storage.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class AnalysisResultCreate(BaseModel):
    """Schema for creating an analysis result."""

    repository_url: str
    repository_name: str
    context: str
    evidence_strength: Optional[Dict[str, int]] = (
        None  # technical, communication, etc scores
    )
    key_insights: Optional[List[str]] = None  # Top insights from analysis
    data_completeness: Optional[float] = None  # 0.0-1.0 completeness score
    full_analysis: Dict[str, Any]
    processing_time_ms: Optional[int] = None
    token_count: Optional[int] = None
    api_cost: Optional[float] = None
    allow_training: bool = True


class AnalysisResultResponse(BaseModel):
    """Schema for analysis result response."""

    id: str
    user_id: str
    repository_url: str
    repository_name: str
    context: str
    github_username: Optional[str] = None  # GitHub username for candidate linking
    evidence_strength: Optional[Dict[str, int]] = (
        None  # technical, communication, etc scores
    )
    key_insights: Optional[List[str]] = None  # Top insights from analysis
    data_completeness: Optional[float] = None  # 0.0-1.0 completeness score
    full_analysis: Dict[str, Any]
    analysis_version: str
    processing_time_ms: Optional[int] = None
    token_count: Optional[int] = None
    api_cost: Optional[float] = None
    allow_training: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnalysisResultListItem(BaseModel):
    """Schema for analysis result in list view (minimal data)."""

    id: str
    repository_name: str
    repository_url: str
    context: str
    evidence_strength: Optional[Dict[str, int]] = None  # Summary scores
    key_insight: Optional[str] = None  # Primary insight from analysis
    created_at: datetime
    batch_id: Optional[str] = None  # Batch ID if part of a batch

    model_config = ConfigDict(from_attributes=True)


class PaginationParams(BaseModel):
    """Schema for pagination parameters."""

    cursor: Optional[str] = Field(None, description="Cursor for pagination")
    limit: int = Field(20, ge=1, le=100, description="Number of items per page")


class AnalysisResultList(BaseModel):
    """Schema for paginated analysis results list."""

    items: List[AnalysisResultListItem]
    cursor: Optional[str] = Field(None, description="Cursor for next page")
    has_next: bool = Field(False, description="Whether there are more results")
    has_prev: bool = Field(False, description="Whether there are previous results")
    total_count: Optional[int] = Field(
        None, description="Total count of results (if available)"
    )
    weekly_count: Optional[int] = Field(
        None, description="Number of analyses completed in the last 7 days"
    )


class AnalysisStorageResponse(BaseModel):
    """Response after storing an analysis."""

    analysis_id: str
    message: str = "Analysis stored successfully"
