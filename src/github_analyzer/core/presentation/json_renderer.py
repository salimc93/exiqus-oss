# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
JSON renderer for repository analysis reports.
"""

import json

from ..report_models import StructuredReport
from .report_renderer import ReportRenderer


class JSONRenderer(ReportRenderer):
    """Renders reports in JSON format."""

    def render(self, report: StructuredReport) -> str:
        """Format report as JSON."""
        return json.dumps(report.to_dict(), indent=2, default=str)
