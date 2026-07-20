# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Command line interface for Exiqus.

This module provides the CLI entry point and command handling
for the AI-powered developer assessment platform.
"""

# CLI components
from .main import cli, main

__all__: list[str] = ["main", "cli"]
