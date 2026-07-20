# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Core analysis engine components.

This module contains the main analysis logic, metrics calculation,
and scoring algorithms for repository evaluation.
"""

from .classifier import (
    AnalysisMethod,
    ClassificationResult,
    RepositoryClassifier,
    TemplateCategory,
)

# Core analysis components will be added here as we implement them
# from .analyzer import CostOptimizedAnalyzer
# from .metrics import RepositoryMetrics
# from .scoring import ContextAwareScorer

__all__: list[str] = [
    "RepositoryClassifier",
    "AnalysisMethod",
    "TemplateCategory",
    "ClassificationResult",
    # Will be uncommented as modules are implemented
    # "CostOptimizedAnalyzer",
    # "RepositoryMetrics",
    # "ContextAwareScorer"
]
