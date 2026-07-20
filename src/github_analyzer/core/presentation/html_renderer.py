# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""
HTML renderer for repository analysis reports.
"""

from typing import Any, Dict, List

from ..report_models import StructuredReport
from .report_renderer import ReportRenderer


class HTMLRenderer(ReportRenderer):
    """Renders reports in HTML format."""

    def render(self, report: StructuredReport) -> str:
        """Format report as comprehensive, professional HTML."""
        # Professional HTML template with enhanced styling
        # Evidence-based approach - no more verdict colors
        recommendation_color = "#333"  # Neutral color for all reports

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Repository Analysis Report - {report.repository_name}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 0;
            background-color: #f8f9fa;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0 0 20px 0;
            font-size: 2.5em;
            font-weight: 300;
        }}
        .meta-info {{
            display: flex;
            justify-content: space-around;
            flex-wrap: wrap;
            margin-top: 20px;
        }}
        .meta-item {{
            text-align: center;
            margin: 10px;
        }}
        .meta-label {{
            font-size: 0.9em;
            opacity: 0.8;
            margin-bottom: 5px;
        }}
        .meta-value {{
            font-size: 1.2em;
            font-weight: bold;
        }}
        .recommendation {{
            background: {recommendation_color};
            color: white;
            padding: 15px 30px;
            margin: 20px;
            border-radius: 10px;
            text-align: center;
            font-size: 1.3em;
            font-weight: bold;
        }}
        .content {{
            padding: 30px;
        }}
        .section {{
            margin: 30px 0;
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            overflow: hidden;
        }}
        .section-header {{
            background: #f8f9fa;
            padding: 20px;
            border-bottom: 1px solid #e0e0e0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .section-title {{
            font-size: 1.4em;
            font-weight: 600;
            margin: 0;
            color: #495057;
        }}
        .section-confidence {{
            background: #6c757d;
            color: white;
            padding: 6px 12px;
            border-radius: 15px;
            font-size: 0.9em;
        }}
        .section-content {{
            padding: 20px;
        }}
        .summary {{
            font-size: 1.1em;
            margin-bottom: 20px;
            color: #495057;
        }}
        .details-list {{
            list-style: none;
            padding: 0;
        }}
        .details-list li {{
            padding: 8px 0;
            border-bottom: 1px solid #f0f0f0;
            display: flex;
            align-items: center;
        }}
        .details-list li:before {{
            content: '✓';
            background: #28a745;
            color: white;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 10px;
            font-size: 12px;
        }}
        .insights-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin: 30px 0;
        }}
        .insight-box {{
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            overflow: hidden;
        }}
        .insight-header {{
            padding: 15px;
            font-weight: bold;
            color: white;
        }}
        .strengths .insight-header {{
            background: #28a745;
        }}
        .concerns .insight-header {{
            background: #dc3545;
        }}
        .insight-content {{
            padding: 15px;
        }}
        .insight-content ul {{
            margin: 0;
            padding-left: 20px;
        }}
        .flags-section {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin: 30px 0;
        }}
        .flag {{
            padding: 10px;
            margin: 5px 0;
            border-radius: 5px;
            border-left: 4px solid;
        }}
        .green-flag {{
            background: #d4edda;
            border-left-color: #28a745;
            color: #155724;
        }}
        .red-flag {{
            background: #f8d7da;
            border-left-color: #dc3545;
            color: #721c24;
        }}
        .recommendations {{
            background: #e3f2fd;
            border: 1px solid #bbdefb;
            border-radius: 10px;
            padding: 20px;
            margin: 30px 0;
        }}
        .recommendations h3 {{
            color: #1976d2;
            margin-top: 0;
        }}
        .context-info {{
            background: #f1f3f4;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #6c757d;
            border-top: 1px solid #e0e0e0;
        }}
        .sub-metrics {{
            margin-top: 25px;
            padding-top: 20px;
            border-top: 1px solid #e9ecef;
        }}
        .sub-metrics h4 {{
            margin: 0 0 15px 0;
            color: #495057;
            font-size: 1.1em;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        .metric-card {{
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 15px;
            transition: transform 0.2s ease;
        }}
        .metric-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}
        .metric-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        .metric-name {{
            font-weight: 600;
            color: #495057;
            font-size: 1.05em;
        }}
        .metric-evidence {{
            font-size: 0.9em;
            color: #6c757d;
            margin-bottom: 8px;
            font-style: italic;
        }}
        .metric-insight {{
            font-size: 0.95em;
            color: #495057;
            line-height: 1.4;
        }}
        @media (max-width: 768px) {{
            .insights-grid, .flags-section {{
                grid-template-columns: 1fr;
            }}
            .meta-info {{
                flex-direction: column;
            }}
            .metrics-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Repository Analysis Report</h1>
            <div class="meta-info">
                <div class="meta-item">
                    <div class="meta-label">Repository</div>
                    <div class="meta-value">{report.repository_name}</div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">Analysis Date</div>
                    <div class="meta-value">{report.analysis_date.strftime("%Y-%m-%d")}</div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">Repository Type</div>
                    <div class="meta-value">{report.repository_type.value.title() if report.repository_type else "Unknown"}</div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">Analysis Type</div>
                    <div class="meta-value">Evidence-Based Assessment</div>
                </div>
            </div>
        </div>
        <div class="recommendation">
            Analysis Type: Evidence-Based Assessment
        </div>
        <div class="content">
            <div class="section">
                <div class="section-header">
                    <h2 class="section-title">Executive Summary</h2>
                </div>
                <div class="section-content">
                    <p class="summary">{report.executive_summary}</p>
                </div>
            </div>
"""

        # Add context information if available
        if report.context:
            html += f"""
            <div class="context-info">
                <strong>Analysis Context:</strong> {report.context.value.title()}
            </div>
"""

        # Add key insights
        if report.key_strengths or report.primary_concerns:
            html += """
            <div class="insights-grid">
                <div class="insight-box strengths">
                    <div class="insight-header">Key Strengths</div>
                    <div class="insight-content">
"""
            if report.key_strengths:
                html += "<ul>"
                for strength in report.key_strengths:
                    html += f"<li>{strength}</li>"
                html += "</ul>"
            else:
                html += "<p>No specific strengths identified.</p>"

            html += """
                    </div>
                </div>
                <div class="insight-box concerns">
                    <div class="insight-header">Primary Concerns</div>
                    <div class="insight-content">
"""
            if report.primary_concerns:
                html += "<ul>"
                for concern in report.primary_concerns:
                    html += f"<li>{concern}</li>"
                html += "</ul>"
            else:
                html += "<p>No significant concerns identified.</p>"

            html += """
                    </div>
                </div>
            </div>
"""

        # Add Screening Insights if available
        if report.screening_insights:
            html += """
            <div class="section">
                <div class="section-header">
                    <h2 class="section-title">Evidence-Based Screening Insights</h2>
                </div>
                <div class="section-content">
"""
            html += f"<p><strong>Overall Assessment:</strong> {report.screening_insights.overall_impression}</p>"
            html += f"<p><strong>Analysis Context:</strong> {report.screening_insights.confidence_explanation}</p>"

            # Group insights by category
            insights_by_category: Dict[str, List[Any]] = {}
            for insight in report.screening_insights.insights:
                category = insight.category.value
                if category not in insights_by_category:
                    insights_by_category[category] = []
                insights_by_category[category].append(insight)

            for category, insights in sorted(insights_by_category.items()):
                html += f"<h3>{category.replace('_', ' ').title()}</h3>"
                for insight in insights:
                    html += "<div style='margin-bottom: 20px;'>"
                    html += f"<h4>{insight.title}</h4>"
                    html += f"<p>{insight.description}</p>"
                    if insight.evidence:
                        html += "<p><em>Supporting Evidence:</em></p><ul>"
                        for evidence in insight.evidence[:2]:
                            html += f"<li>{evidence}</li>"
                        html += "</ul>"
                    html += "</div>"

            # Data limitations
            if report.screening_insights.data_limitations:
                html += "<h3>Analysis Considerations</h3>"
                html += "<p><em>Repository data limitations:</em></p><ul>"
                for limitation in report.screening_insights.data_limitations:
                    html += f"<li>{limitation}</li>"
                html += "</ul>"

            html += """
                </div>
            </div>
"""

        # Add recommendations if any (these come from areas_to_explore)
        if report.analysis_recommendations:
            html += """
            <div class="recommendations">
                <h3>Topics for Discussion</h3>
                <ul>
"""
            for rec in report.analysis_recommendations:
                html += f"<li>{rec}</li>"
            html += """
                </ul>
            </div>
"""

        # Add detailed flags section if there are any flags
        if report.red_flags or report.green_flags:
            html += """
            <div class="section">
                <div class="section-header">
                    <h2 class="section-title">Detailed Findings</h2>
                </div>
                <div class="section-content">
                    <div class="flags-section">
"""
            # Green flags column
            html += "<div><h3>Positive Indicators</h3>"
            if report.green_flags:
                for flag in report.green_flags:
                    html += f"""
                        <div class="flag green-flag">
                            <strong>{flag.category.title()}</strong><br>
                            {flag.description}
                        </div>
                    """
            else:
                html += "<p>No specific positive indicators flagged.</p>"
            html += "</div>"

            # Red flags column
            html += "<div><h3>Risk Indicators</h3>"
            if report.red_flags:
                for flag in report.red_flags:
                    html += f"""
                        <div class="flag red-flag">
                            <strong>{flag.category.title()}</strong><br>
                            {flag.description}
                        </div>
                    """
            else:
                html += "<p>No specific risk indicators flagged.</p>"
            html += "</div>"

            html += """
                    </div>
                </div>
            </div>
"""

        html += """
        </div>
        <div class="footer">
            <p>Generated by GitHub Analyzer AI • Professional Edition</p>
        </div>
    </div>
</body>
</html>
"""
        return html
