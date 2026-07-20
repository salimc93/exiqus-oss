# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2025-2026 Exiqus

"""HTML export utility matching frontend export design."""

from datetime import datetime
from typing import Any, Dict, List


def generate_analysis_html(
    repository_name: str,
    repository_url: str,
    context: str,
    created_at: datetime,
    insights: List[Dict[str, Any]],
    questions: List[Dict[str, Any]],
    evidence_patterns: List[Dict[str, Any]],
    recommendations: List[Dict[str, Any]],
    executive_summary: Any,
    confidence_explanation: str,
    green_flags: List[str],
    red_flags: List[str],
    limitations: List[str],
    data_limitations: List[str],
    areas_to_explore: List[str],
) -> str:
    """Generate HTML report matching frontend export exactly."""

    # Parse executive summary
    if isinstance(executive_summary, dict):
        summary_text = executive_summary.get("summary", "")
    else:
        summary_text = str(executive_summary) if executive_summary else ""

    # Format date
    formatted_date = created_at.strftime("%B %d, %Y at %I:%M %p")

    # Start HTML with exact frontend styling
    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Analysis Report - {repository_name}</title>
  <style>
    @page {{
      size: A4;
      margin: 0;
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    html {{
      height: 100%;
      background: #0A0A0F !important;
      margin: 0;
      padding: 0;
    }}

    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
      color: #e5e7eb !important;
      background: #0A0A0F !important;
      font-size: 11pt;
      line-height: 1.6;
      margin: 0;
      padding: 0;
      min-height: 100vh;
      -webkit-print-color-adjust: exact !important;
      print-color-adjust: exact !important;
      color-adjust: exact !important;
    }}

    /* Container for content */
    .container {{
      padding: 25px;
      background: linear-gradient(to bottom, #0A0A0F, #0f0f14);
      min-height: 100vh;
    }}

    /* Force dark background for printing */
    @media print {{
      html, body {{
        background: #0A0A0F !important;
        color: #e5e7eb !important;
        margin: 0;
        padding: 0;
        height: 100%;
      }}

      .container {{
        padding: 20px;
        min-height: 100vh;
      }}

      * {{
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
        color-adjust: exact !important;
      }}
    }}

    /* Header with gradient like UI */
    .header {{
      background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #ec4899 100%);
      color: white;
      padding: 35px;
      margin: -25px -25px 30px -25px;
      border-radius: 0 0 20px 20px;
      box-shadow: 0 10px 30px rgba(99, 102, 241, 0.3);
    }}

    .header h1 {{
      font-size: 26pt;
      font-weight: 700;
      margin-bottom: 12px;
      text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }}

    .header p {{
      font-size: 12pt;
      margin: 4px 0;
      opacity: 0.95;
    }}

    /* Section headings */
    h2 {{
      color: #c7d2fe;
      font-size: 18pt;
      font-weight: 600;
      margin: 35px 0 20px 0;
      padding-bottom: 10px;
      border-bottom: 2px solid rgba(99, 102, 241, 0.3);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}

    h3 {{
      color: #e5e7eb;
      font-size: 13pt;
      font-weight: 500;
      margin: 20px 0 10px 0;
    }}

    p {{
      margin: 10px 0;
      font-size: 11pt;
      line-height: 1.6;
      color: #d1d5db;
    }}

    /* Metrics Grid */
    .metrics {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 20px;
      margin: 30px 0;
    }}

    .metric {{
      background: linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(139, 92, 246, 0.1));
      border: 1px solid rgba(99, 102, 241, 0.3);
      border-radius: 15px;
      padding: 20px;
      text-align: center;
      box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
    }}

    .metric-value {{
      font-size: 28pt;
      font-weight: bold;
      color: #e0e7ff;
      display: block;
      margin-bottom: 5px;
    }}

    .metric-label {{
      font-size: 11pt;
      color: #a5b4fc;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}

    /* Insight Cards matching UI design */
    .insight-card {{
      background: linear-gradient(to bottom right, #1e1e2e, #1a1a28);
      border: 1px solid rgba(99, 102, 241, 0.2);
      border-radius: 15px;
      padding: 20px;
      margin-bottom: 20px;
      box-shadow: 0 6px 15px rgba(0, 0, 0, 0.5);
    }}

    .insight-card h4 {{
      font-size: 13pt;
      color: #f3f4f6;
      margin-bottom: 10px;
      line-height: 1.5;
    }}

    .insight-card .evidence {{
      background: rgba(99, 102, 241, 0.08);
      border-left: 3px solid #6366f1;
      padding: 12px 15px;
      margin: 12px 0;
      border-radius: 8px;
      font-size: 11pt;
      color: #d1d5db;
    }}

    /* Evidence box matching UI */
    .evidence-box {{
      background: linear-gradient(to right, rgba(99, 102, 241, 0.15), rgba(99, 102, 241, 0.05));
      border-left: 3px solid #6366f1;
      padding: 12px 16px;
      margin: 12px 0;
      border-radius: 6px;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
    }}

    /* Badges */
    .badge {{
      display: inline-block;
      padding: 4px 10px;
      border-radius: 8px;
      font-size: 10pt;
      font-weight: 500;
      margin-right: 8px;
    }}

    .badge-confidence {{
      background: rgba(99, 102, 241, 0.2);
      color: #a5b4fc;
    }}

    .badge-category {{
      background: rgba(147, 51, 234, 0.2);
      color: #c084fc;
    }}

    .badge-type {{
      background: rgba(34, 197, 94, 0.2);
      color: #86efac;
    }}

    .badge-priority-high {{
      background: rgba(239, 68, 68, 0.2);
      color: #f87171;
    }}

    .badge-priority-medium {{
      background: rgba(251, 191, 36, 0.2);
      color: #fbbf24;
    }}

    .badge-priority-low {{
      background: rgba(34, 197, 94, 0.2);
      color: #86efac;
    }}

    /* Lists */
    ul {{
      margin: 4px 0 4px 15px;
      padding: 0;
    }}

    li {{
      font-size: 8pt;
      margin: 2px 0;
    }}

    /* Summary Box */
    .summary-box {{
      background: linear-gradient(135deg, rgba(99, 102, 241, 0.08), rgba(139, 92, 246, 0.04));
      border: 1px solid rgba(99, 102, 241, 0.2);
      border-radius: 15px;
      padding: 25px;
      margin: 25px 0;
      font-size: 12pt;
      line-height: 1.7;
      color: #e5e7eb;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }}

    /* Evidence Pattern Cards */
    .evidence-card {{
      background: linear-gradient(135deg, rgba(34, 197, 94, 0.1), rgba(16, 185, 129, 0.05));
      border: 1px solid rgba(34, 197, 94, 0.3);
      border-radius: 12px;
      padding: 18px;
      margin-bottom: 15px;
      box-shadow: 0 4px 10px rgba(0, 0, 0, 0.4);
    }}

    .evidence-card h4 {{
      font-size: 12pt;
      color: #86efac;
      margin-bottom: 8px;
    }}

    .evidence-card p {{
      font-size: 11pt;
      color: #d1d5db;
      margin: 8px 0;
    }}

    /* Question Cards */
    .question-card {{
      background: linear-gradient(135deg, #1f1f2e, #1a1a28);
      border: 2px solid rgba(251, 191, 36, 0.3);
      border-radius: 15px;
      padding: 25px;
      margin-bottom: 30px;
      box-shadow: 0 8px 20px rgba(0, 0, 0, 0.5);
      page-break-inside: avoid;
      break-inside: avoid;
      position: relative;
    }}

    .question-number {{
      color: #fbbf24;
      font-weight: bold;
      font-size: 16pt;
      margin-bottom: 10px;
      display: block;
    }}

    .question-text {{
      color: #f3f4f6;
      font-size: 12pt;
      margin-bottom: 15px;
      line-height: 1.7;
      font-weight: 500;
    }}

    .follow-ups {{
      background: rgba(59, 130, 246, 0.08);
      border-radius: 10px;
      padding: 15px;
      margin: 12px 0;
    }}

    .follow-ups strong {{
      color: #93c5fd;
      font-size: 11pt;
      display: block;
      margin-bottom: 8px;
    }}

    .follow-ups li {{
      color: #d1d5db;
      font-size: 10pt;
      margin: 6px 0;
      line-height: 1.5;
    }}

    .listen-for {{
      background: rgba(34, 197, 94, 0.08);
      border-left: 3px solid #22c55e;
      border-radius: 10px;
      padding: 15px;
      margin: 12px 0;
    }}

    .listen-for strong {{
      color: #86efac;
      font-size: 11pt;
      display: block;
      margin-bottom: 5px;
    }}

    .listen-for span {{
      color: #d1d5db;
      font-size: 11pt;
    }}

    /* Indicators Section */
    .indicators {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 25px;
      margin: 25px 0;
    }}

    .indicator-box {{
      background: linear-gradient(135deg, rgba(99, 102, 241, 0.05), rgba(139, 92, 246, 0.02));
      border-radius: 15px;
      padding: 20px;
      border: 1px solid rgba(99, 102, 241, 0.2);
    }}

    /* Recommendations */
    .recommendation-card {{
      background: linear-gradient(to right, #1e1e2e, #1a1a28);
      border: 1px solid rgba(147, 51, 234, 0.2);
      border-radius: 15px;
      padding: 20px;
      margin-bottom: 20px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
    }}

    .recommendation-card h4 {{
      font-size: 13pt;
      color: #f3f4f6;
      margin-bottom: 10px;
    }}

    .recommendation-card .based-on {{
      font-size: 11pt;
      color: #9ca3af;
      margin: 10px 0;
    }}

    .recommendation-card .based-on strong {{
      color: #a5b4fc;
    }}

    /* Footer */
    .footer {{
      text-align: center;
      color: #6b7280;
      font-size: 10pt;
      margin-top: 40px;
      padding-top: 20px;
      border-top: 1px solid rgba(99, 102, 241, 0.2);
    }}

    /* Enhanced Page break controls */
    .page-break {{
      page-break-before: always;
      break-before: always;
      margin: 0;
      padding: 0;
      height: 0;
    }}

    /* Prevent breaks inside critical elements */
    .insight-card, .evidence-card, .question-card, .recommendation-card {{
      page-break-inside: avoid;
      break-inside: avoid;
    }}

    h1, h2, h3, h4, h5, h6 {{
      page-break-after: avoid;
      break-after: avoid;
      page-break-inside: avoid;
      break-inside: avoid;
    }}

    /* Keep elements together */
    .question-card {{
      page-break-inside: avoid;
      break-inside: avoid;
      display: block;
    }}

    .follow-ups, .listen-for {{
      page-break-inside: avoid;
      break-inside: avoid;
    }}

    /* Orphan and widow control */
    p, li {{
      orphans: 3;
      widows: 3;
    }}

    @media print {{
      .no-print {{
        display: none;
      }}

      /* Ensure questions don't break */
      .question-card {{
        page-break-inside: avoid !important;
        break-inside: avoid !important;
      }}

      /* Keep sections together when possible */
      .section {{
        page-break-inside: avoid;
        break-inside: avoid;
      }}
    }}
  </style>
</head>
<body>
  <div class="container">
  <!-- Page 1: Header, Summary, Metrics, Top Insights -->
  <div class="header">
    <h1>{repository_name}</h1>
    <p><strong>URL:</strong> {repository_url}</p>
    <p><strong>Analysis Date:</strong> {formatted_date} | <strong>Context:</strong> {
        context
    }</p>
  </div>

  <h2>Executive Summary</h2>
  <div style="background: linear-gradient(to bottom right, #1e1e2e, #1a1a28); border: 1px solid rgba(99, 102, 241, 0.2); border-radius: 15px; padding: 25px; margin: 25px 0; box-shadow: 0 6px 15px rgba(0, 0, 0, 0.5);">
    <p style="font-size: 12pt; line-height: 1.7; color: #e5e7eb; margin: 0 0 20px 0;">{
        summary_text
    }</p>

    {
        f'''
    <div style="background: linear-gradient(135deg, rgba(34, 197, 94, 0.08), rgba(16, 185, 129, 0.04)); border: 1px solid rgba(34, 197, 94, 0.2); border-radius: 12px; padding: 20px; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3);">
      <div style="display: flex; align-items: center; margin-bottom: 10px;">
        <div style="width: 24px; height: 24px; background: linear-gradient(135deg, #22c55e, #16a34a); border-radius: 6px; display: flex; align-items: center; justify-content: center; margin-right: 10px;">
          <span style="color: white; font-size: 14px;">✓</span>
        </div>
        <h3 style="color: #86efac; font-size: 13pt; margin: 0;">Analysis Confidence Level</h3>
      </div>
      <p style="font-size: 11pt; line-height: 1.6; color: #d1d5db; margin: 0;">{confidence_explanation}</p>
    </div>
    '''
        if confidence_explanation
        else ""
    }
  </div>

  <div class="metrics">
    <div class="metric">
      <div style="width: 40px; height: 40px; background: linear-gradient(135deg, #6366f1, #8b5cf6); border-radius: 10px; display: flex; align-items: center; justify-content: center; margin: 0 auto 12px;">
        <span style="color: white; font-size: 20px;">💡</span>
      </div>
      <div class="metric-value">{len(insights)}</div>
      <div class="metric-label">Key insights</div>
    </div>
    <div class="metric">
      <div style="width: 40px; height: 40px; background: linear-gradient(135deg, #22c55e, #16a34a); border-radius: 10px; display: flex; align-items: center; justify-content: center; margin: 0 auto 12px;">
        <span style="color: white; font-size: 20px;">📊</span>
      </div>
      <div class="metric-value">{len(evidence_patterns)}</div>
      <div class="metric-label">Evidence patterns</div>
    </div>
    <div class="metric">
      <div style="width: 40px; height: 40px; background: linear-gradient(135deg, #f59e0b, #d97706); border-radius: 10px; display: flex; align-items: center; justify-content: center; margin: 0 auto 12px;">
        <span style="color: white; font-size: 20px;">❓</span>
      </div>
      <div class="metric-value">{len(questions)}</div>
      <div class="metric-label">Interview questions</div>
    </div>
    <div class="metric">
      <div style="width: 40px; height: 40px; background: linear-gradient(135deg, #ec4899, #db2777); border-radius: 10px; display: flex; align-items: center; justify-content: center; margin: 0 auto 12px;">
        <span style="color: white; font-size: 20px;">🎯</span>
      </div>
      <div class="metric-value">{len(recommendations)}</div>
      <div class="metric-label">Recommendations</div>
    </div>
  </div>
"""

    # Key Insights
    if insights:
        html += """
  <h2>Key Insights</h2>
"""
        for i, insight in enumerate(insights[:15], 1):
            if isinstance(insight, dict):
                description = insight.get("description", "")
                evidence_list = insight.get("evidence", [])
                confidence = insight.get("confidence", "")
                category = insight.get("category", "").replace("_", " ")

                html += f"""
  <div class="insight-card">
    <h4>{i}. {description}</h4>
    {f'<div class="evidence">• {evidence_list[0]}</div>' if evidence_list and len(evidence_list) > 0 else ""}
    <div style="margin-top: 12px;">
      <span class="badge badge-confidence">{confidence}</span>
      <span class="badge badge-category">{category}</span>
    </div>
  </div>
"""

    # Add page break if many insights
    if insights and len(insights) > 3:
        html += '<div class="page-break"></div>\n'

    # Evidence Patterns
    if evidence_patterns:
        html += """
  <h2>Evidence Patterns</h2>
"""
        for i, pattern in enumerate(evidence_patterns[:10], 1):
            if isinstance(pattern, dict):
                name = pattern.get("name", "Pattern")
                evidence = pattern.get("evidence", "")
                pattern_type = pattern.get("pattern_type", "")
                category = pattern.get("category", "")

                html += f"""
  <div class="evidence-card" style="background: linear-gradient(135deg, rgba(34, 197, 94, 0.1), rgba(16, 185, 129, 0.05)); border: 1px solid rgba(34, 197, 94, 0.3); border-radius: 12px; padding: 18px; margin-bottom: 15px; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.4);">
    <h4 style="font-size: 12pt; color: #86efac; margin-bottom: 8px;">{i}. {name}</h4>
    {f'<p style="font-size: 11pt; color: #d1d5db; margin: 8px 0;">{evidence}</p>' if evidence else ""}
    <div style="margin-top: 10px;">
      <span class="badge badge-type">{pattern_type}</span>
      <span class="badge badge-category">{category}</span>
    </div>
  </div>
"""

    # Add page break if many evidence patterns
    if evidence_patterns and len(evidence_patterns) > 3:
        html += '<div class="page-break"></div>\n'

    # Interview Questions
    if questions:
        html += """
  <h2>Interview Questions</h2>
  <div style="margin-bottom: 20px;">
"""
        for i, question in enumerate(questions, 1):
            if isinstance(question, dict):
                question_text = question.get("question", "")
                evidence_reference = question.get("evidence_reference", "")
                follow_ups = question.get("follow_ups", [])
                what_to_listen_for = question.get("what_to_listen_for", "")

                html += f"""
  <div class="question-card" style="page-break-inside: avoid; break-inside: avoid; min-height: 0; position: relative;">
    <div style="position: absolute; top: 20px; right: 20px; background: linear-gradient(135deg, #fbbf24, #f59e0b); color: #1a1a28; padding: 6px 12px; border-radius: 8px; font-weight: bold; font-size: 14pt;">Q{
                    i
                }</div>
    <div class="question-text" style="margin-right: 60px;">{question_text}</div>

    {
                    f'''
    <div style="background: rgba(99, 102, 241, 0.05); border-radius: 10px; padding: 15px; margin: 15px 0; border-left: 3px solid #6366f1;">
      <div style="display: flex; align-items: center; margin-bottom: 8px;">
        <span style="color: #a5b4fc; font-weight: 600; font-size: 11pt;">Based on Evidence</span>
      </div>
      <div style="color: #d1d5db; font-size: 11pt;">{evidence_reference}</div>
    </div>
    '''
                    if evidence_reference
                    else ""
                }

    {
                    f'''
    <div style="background: rgba(59, 130, 246, 0.08); border-radius: 10px; padding: 15px; margin: 15px 0;">
      <div style="display: flex; align-items: center; margin-bottom: 10px;">
        <span style="color: #93c5fd; font-weight: 600; font-size: 11pt;">📝 Follow-up questions</span>
      </div>
      <div style="margin-left: 5px;">
        {''.join([f'<div style="margin: 8px 0; color: #d1d5db; font-size: 10pt;"><span style="color: #93c5fd; font-weight: 600; margin-right: 8px;">{j}.</span>{fu}</div>' for j, fu in enumerate(follow_ups, 1)])}
      </div>
    </div>
    '''
                    if follow_ups and len(follow_ups) > 0
                    else ""
                }

    {
                    f'''
    <div style="background: rgba(34, 197, 94, 0.08); border-radius: 10px; padding: 15px; margin: 15px 0; border-left: 3px solid #22c55e;">
      <div style="display: flex; align-items: center; margin-bottom: 8px;">
        <span style="color: #86efac; font-weight: 600; font-size: 11pt;">🎧 Key Listening Points</span>
      </div>
      <div style="color: #d1d5db; font-size: 11pt;">{what_to_listen_for}</div>
    </div>
    '''
                    if what_to_listen_for
                    else ""
                }
  </div>
"""
        html += "  </div>\n"

        # Add page break if many questions
        if len(questions) > 2:
            html += '<div class="page-break"></div>\n'

    # Key Indicators
    html += """
  <h2>Key Indicators</h2>
  <div class="indicators">
"""
    if green_flags:
        html += """
    <div class="indicator-box">
      <h3 class="positive-indicators" style="color: #4ade80;">✓ Positive Indicators</h3>
      <ul style="margin: 10px 0 0 20px;">
"""
        for flag in green_flags:
            html += f'        <li style="font-size: 11pt; margin: 6px 0;">{flag}</li>\n'
        html += """      </ul>
    </div>
"""

    if red_flags or areas_to_explore:
        html += """
    <div class="indicator-box">
      <h3 class="warning-indicators" style="color: #fbbf24;">⚠ Areas to Explore</h3>
      <ul style="margin: 10px 0 0 20px;">
"""
        combined_areas = red_flags + areas_to_explore
        for item in combined_areas:
            html += f'        <li style="font-size: 11pt; margin: 6px 0;">{item}</li>\n'
        html += """      </ul>
    </div>
"""
    html += "  </div>\n"

    # Recommendations
    if recommendations:
        html += """
  <h2>Recommendations</h2>
"""
        for i, rec in enumerate(recommendations[:10], 1):
            if isinstance(rec, dict):
                rec_type = rec.get("type", "")
                text = rec.get("text", "")
                priority = rec.get("priority", "")
                evidence = rec.get("evidence", "")

                border_style = (
                    "border-color: rgba(239, 68, 68, 0.3);"
                    if rec_type == "concern"
                    else ""
                )

                html += f"""
  <div class="recommendation-card" style="{border_style}">
    <h4>{i}. {text}</h4>
    {
                    f'''
      <div class="based-on">
        <strong>Based on:</strong> {evidence}
      </div>
    '''
                    if evidence
                    else ""
                }
    <div style="margin-top: 12px;">
      <span class="badge badge-priority-{priority}">{priority} priority</span>
      <span class="badge badge-category">{rec_type}</span>
    </div>
  </div>
"""

    # Footer
    html += """
  <div class="footer">
    <p>© 2025 Exiqus GitHub Analyzer • Confidential Analysis Report</p>
  </div>
  </div>
</body>
</html>"""

    return html
