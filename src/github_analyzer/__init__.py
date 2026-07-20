# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Exiqus - AI-Powered Developer Assessment Platform

Transform technical recruitment with intelligent, context-aware analysis of GitHub repositories.

This package provides intelligent analysis of GitHub repositories to help recruiters
and hiring managers make informed decisions about developer candidates.
"""

__version__ = "0.1.0"
__author__ = "Exiqus Team"
__email__ = ""

# Utilities (only import what exists)
from .utils.config import Config
from .utils.helpers import format_analysis_result, validate_github_url

__all__ = [
    # Utilities (available now)
    "Config",
    "validate_github_url",
    "format_analysis_result",
    # Core analysis (will be added later)
    # "CostOptimizedAnalyzer",
    # "GitHubFetcher",
    # "TemplateResponses",
    # "HaikuPromptTemplates",
]

# Package metadata
SUPPORTED_PYTHON_VERSIONS = ["3.9", "3.10", "3.11", "3.12"]
REQUIRED_API_KEYS = ["GITHUB_TOKEN", "ANTHROPIC_API_KEY"]
