# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
Abstract base class for report renderers.
"""

from abc import ABC, abstractmethod

from ..report_models import StructuredReport


class ReportRenderer(ABC):
    """Abstract base class for report renderers."""

    @abstractmethod
    def render(self, report: StructuredReport) -> str:
        """
        Render the report to a string format.

        Args:
            report: The structured report to render.

        Returns:
            The rendered report as a string.
        """
        pass
