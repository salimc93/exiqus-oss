# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Evidence-based recommendation system using Claude Haiku.

This module extracts specific, actionable evidence from repository data
to generate insights worth $149-399/month using a model that costs $0.0008.

The magic? We use Haiku's reasoning capabilities to find patterns that
would take humans hours to discover.
"""

from .evidence_extractor import EvidenceExtractor
from .temporal_analyzer import TemporalAnalyzer

__all__ = [
    "EvidenceExtractor",
    "TemporalAnalyzer",
]

# Haiku can do ALL of this for $0.0008:
# - Extract specific commit evidence
# - Track skill evolution over time
# - Identify team dynamics
# - Find security vulnerabilities
# - Generate context-aware questions
# - Detect behavioral patterns
# - Calculate technical debt
# - And so much more!
