# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Data models for evidence and behavioral analysis.

This module provides structured data models for analysis results,
ensuring consistent handling of data sufficiency and confidence scoring.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional


@dataclass
class BehavioralAnalysisResult:
    """Structured result for behavioral analysis components."""

    status: Literal["ok", "insufficient_data", "error"]
    confidence: float  # 0.0 to 1.0
    sample_size: int
    required_size: int
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

    @property
    def is_sufficient(self) -> bool:
        """Check if analysis has sufficient data."""
        return self.status == "ok"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result: Dict[str, Any] = {
            "status": self.status,
            "confidence": self.confidence,
            "sample_size": self.sample_size,
            "required_size": self.required_size,
        }
        if self.message:
            result["message"] = self.message
        if self.data:
            result["data"] = self.data
        return result


@dataclass
class DataQualityInfo:
    """Information about data quality and sufficiency."""

    total_commits_analyzed: int
    sufficient_for_behavioral: bool
    missing_analyses: List[Dict[str, Any]]
    confidence_levels: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_commits_analyzed": self.total_commits_analyzed,
            "sufficient_for_behavioral": self.sufficient_for_behavioral,
            "missing_analyses": self.missing_analyses,
            "confidence_levels": self.confidence_levels,
        }
