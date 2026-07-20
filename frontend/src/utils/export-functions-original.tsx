// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

import { format } from 'date-fns';

import type {
  AnalysisDetails,
  EvidencePatternModel,
  InsightModel,
  QuestionModel,
  RecommendationModel,
} from '@/types';

// Helper function to convert backend tier names to frontend display names
function _getTierDisplayName(backendTier: string): string {
  const tierMapping: { [key: string]: string } = {
    free: 'Free',
    basic: 'Starter',
    professional: 'Growth',
    enterprise: 'Scale',
    scale_plus: 'Scale+',
  };
  return tierMapping[backendTier?.toLowerCase()] || backendTier;
}

export const generatePDFExport = (data: AnalysisDetails, _currentUser?: unknown) => {
  const analysisData = data.full_analysis.analysis;
  const _metadata = data.full_analysis.metadata;
  const insights = analysisData.insights || [];
  const questions = analysisData.questions || [];
  const evidencePatterns = analysisData.evidence_patterns || [];
  const recommendations = analysisData.recommendations || [];
  const summary = analysisData.executive_summary || '';
  const confidenceExplanation = analysisData.confidence_explanation || '';
  const greenFlags = analysisData.green_flags || [];
  const redFlags = analysisData.red_flags || [];
  const _limitations = analysisData.limitations || [];
  const _dataLimitations = analysisData.data_limitations || [];
  const areasToExplore = analysisData.areas_to_explore || [];

  const pdfContent = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Analysis Report - ${data.repository_name}</title>
  <style>
    @page { 
      size: A4;
      margin: 0;
    }
    
    @media print {
      body {
        margin: 0;
        padding: 0;
      }
    }
    
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }
    
    html, body {
      height: 100%;
      margin: 0;
      padding: 0;
    }
    
    body { 
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; 
      color: #e5e7eb;
      background: #0A0A0A;
      font-size: 10pt;
      line-height: 1.5;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
      position: relative;
    }
    
    /* Container for all content */
    .pdf-container {
      background: #0A0A0A;
      min-height: 100vh;
      position: relative;
    }
    
    /* Page wrapper with fixed A4 dimensions */
    .page {
      width: 210mm;
      min-height: 297mm;
      padding: 15mm 15mm 25mm 15mm;
      margin: 0 auto;
      background: #0A0A0A;
      position: relative;
      page-break-after: always;
      display: flex;
      flex-direction: column;
    }
    
    .page:last-child {
      page-break-after: avoid;
    }
    
    /* Content area that grows */
    .page-content {
      flex: 1;
      padding-bottom: 40px;
    }
    
    /* Header Section */
    .header {
      background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
      color: white;
      padding: 25px;
      margin: -15mm -15mm 20px -15mm;
      page-break-inside: avoid;
      box-shadow: 0 4px 20px rgba(99, 102, 241, 0.3);
    }
    
    .header h1 { 
      font-size: 22pt;
      font-weight: 700;
      margin-bottom: 12px;
      text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }
    
    .header p { 
      opacity: 0.95;
      font-size: 10pt;
      margin: 4px 0;
    }
    
    /* Sections with better spacing */
    .section {
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: 8px;
      padding: 18px;
      margin-bottom: 16px;
      page-break-inside: avoid;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
    }
    
    .section h2 {
      color: #a5b4fc;
      font-size: 14pt;
      font-weight: 600;
      margin-bottom: 12px;
      padding-bottom: 8px;
      border-bottom: 2px solid rgba(99, 102, 241, 0.2);
    }
    
    /* Metrics Grid */
    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 10px;
      margin-bottom: 16px;
    }
    
    .metric-card {
      background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(139, 92, 246, 0.05));
      border: 1px solid rgba(99, 102, 241, 0.25);
      border-radius: 6px;
      padding: 12px;
      text-align: center;
      page-break-inside: avoid;
    }
    
    .metric-label {
      color: #9ca3af;
      font-size: 8pt;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 4px;
    }
    
    .metric-value {
      color: #e0e7ff;
      font-size: 16pt;
      font-weight: 700;
    }
    
    /* Cards with better contrast */
    .insight-card {
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 6px;
      padding: 14px;
      margin-bottom: 10px;
      page-break-inside: avoid;
    }
    
    .insight-card h3 {
      color: #e5e7eb;
      font-size: 11pt;
      margin-bottom: 8px;
      font-weight: 600;
    }
    
    /* Evidence items */
    .evidence-item {
      background: rgba(99, 102, 241, 0.08);
      border-left: 3px solid #6366f1;
      padding: 8px 10px;
      margin: 6px 0;
      border-radius: 4px;
      page-break-inside: avoid;
      font-size: 9pt;
      color: #d1d5db;
    }
    
    /* Pattern cards with type-based colors */
    .pattern-card {
      background: rgba(147, 51, 234, 0.08);
      border: 1px solid rgba(147, 51, 234, 0.25);
      border-radius: 6px;
      padding: 14px;
      margin-bottom: 10px;
      page-break-inside: avoid;
    }
    
    .pattern-card.technical {
      background: rgba(99, 102, 241, 0.08);
      border-color: rgba(99, 102, 241, 0.25);
    }
    
    .pattern-card.behavioral {
      background: rgba(236, 72, 153, 0.08);
      border-color: rgba(236, 72, 153, 0.25);
    }
    
    .pattern-card.collaboration {
      background: rgba(59, 130, 246, 0.08);
      border-color: rgba(59, 130, 246, 0.25);
    }
    
    .pattern-card.quality {
      background: rgba(34, 197, 94, 0.08);
      border-color: rgba(34, 197, 94, 0.25);
    }
    
    .pattern-card h3 {
      color: #e5e7eb;
      font-size: 11pt;
      margin-bottom: 6px;
      font-weight: 600;
    }
    
    /* Question cards */
    .question-card {
      background: rgba(251, 191, 36, 0.08);
      border: 1px solid rgba(251, 191, 36, 0.25);
      border-radius: 6px;
      padding: 14px;
      margin-bottom: 10px;
      page-break-inside: avoid;
    }
    
    .question-number {
      color: #fbbf24;
      font-weight: bold;
      font-size: 11pt;
      margin-bottom: 4px;
    }
    
    .question-card h3 {
      color: #e5e7eb;
      font-size: 10pt;
      margin-bottom: 8px;
      font-weight: 600;
    }
    
    /* Follow-ups */
    .follow-ups {
      background: rgba(255, 255, 255, 0.03);
      border-radius: 4px;
      padding: 8px;
      margin-top: 8px;
    }
    
    .follow-ups h4 {
      color: #fbbf24;
      font-size: 9pt;
      margin-bottom: 4px;
    }
    
    /* Recommendations */
    .recommendation {
      background: rgba(34, 197, 94, 0.08);
      border: 1px solid rgba(34, 197, 94, 0.25);
      border-radius: 6px;
      padding: 14px;
      margin-bottom: 10px;
      page-break-inside: avoid;
    }
    
    .recommendation.concern {
      background: rgba(239, 68, 68, 0.08);
      border-color: rgba(239, 68, 68, 0.25);
    }
    
    /* Badges */
    .badge {
      display: inline-block;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 8pt;
      font-weight: 500;
      margin-right: 4px;
    }
    
    .badge.high {
      background: rgba(34, 197, 94, 0.2);
      color: #4ade80;
    }
    
    .badge.medium {
      background: rgba(251, 191, 36, 0.2);
      color: #fbbf24;
    }
    
    .badge.low {
      background: rgba(156, 163, 175, 0.2);
      color: #9ca3af;
    }
    
    /* Lists */
    ul {
      margin: 8px 0;
      padding-left: 20px;
    }
    
    li {
      color: #d1d5db;
      margin: 4px 0;
      font-size: 9pt;
    }
    
    /* Footer for every page */
    .page-footer {
      position: absolute;
      bottom: 10mm;
      left: 15mm;
      right: 15mm;
      text-align: center;
      color: #6b7280;
      font-size: 8pt;
      padding-top: 8px;
      border-top: 1px solid rgba(255, 255, 255, 0.06);
    }
    
    .page-footer p {
      margin: 0;
      line-height: 1.2;
    }
    
    /* Page numbers */
    .page-number {
      position: absolute;
      bottom: 5mm;
      right: 15mm;
      color: #6b7280;
      font-size: 8pt;
    }
    
    /* Ensure content doesn't overflow */
    .content-wrapper {
      max-width: 100%;
      overflow: hidden;
    }
    
    /* Prevent widow/orphan lines */
    h1, h2, h3, h4, h5, h6 {
      page-break-after: avoid;
    }
    
    p {
      orphans: 3;
      widows: 3;
    }
    
    /* Remove excess whitespace */
    .compact {
      margin-bottom: 8px !important;
    }
  </style>
</head>
<body>
  <div class="pdf-container">
    <!-- Page 1: Header and Summary -->
    <div class="page">
      <div class="page-content">
        <div class="header">
          <h1>GitHub Repository Analysis Report</h1>
          <p><strong>Repository:</strong> ${data.repository_name}</p>
          <p><strong>URL:</strong> ${data.repository_url}</p>
          <p><strong>Analysis Date:</strong> ${format(new Date(data.created_at), 'PPP')}</p>
          <p><strong>Context:</strong> ${data.context}</p>
        </div>

        <div class="section">
          <h2>Executive Summary</h2>
          <p style="white-space: pre-wrap; margin-bottom: 12px;">${summary}</p>
          ${
            confidenceExplanation
              ? `
            <div class="evidence-item" style="margin-top: 12px;">
              <strong>Evidence Quality:</strong> ${confidenceExplanation}
            </div>
          `
              : ''
          }
        </div>

        <div class="section compact">
          <h2>Key Metrics</h2>
          <div class="metrics-grid">
            <div class="metric-card">
              <div class="metric-label">Insights</div>
              <div class="metric-value">${insights.length}</div>
            </div>
            <div class="metric-card">
              <div class="metric-label">Evidence</div>
              <div class="metric-value">${evidencePatterns.length}</div>
            </div>
            <div class="metric-card">
              <div class="metric-label">Questions</div>
              <div class="metric-value">${questions.length}</div>
            </div>
            <div class="metric-card">
              <div class="metric-label">Actions</div>
              <div class="metric-value">${recommendations.length}</div>
            </div>
          </div>
        </div>
      </div>
      <div class="page-footer">
        <p>© 2025 Exiqus GitHub Analyser • Confidential Analysis Report</p>
      </div>
    </div>

    <!-- Combined Content Pages -->
    <div class="page">
      <div class="page-content">
        ${
          insights.length > 0
            ? `
          <div class="section">
            <h2>Key Insights (${insights.length} Total)</h2>
            ${insights
              .slice(0, 10)
              .map(
                (insight: InsightModel, index: number) => `
              <div class="insight-card">
                <h3>${index + 1}. ${insight.description}</h3>
                ${
                  insight.evidence && insight.evidence.length > 0
                    ? `
                  <div style="margin-top: 4px;">
                    ${insight.evidence
                      .slice(0, 1)
                      .map(
                        (ev: string) => `
                      <div class="evidence-item">• ${ev}</div>
                    `
                      )
                      .join('')}
                  </div>
                `
                    : ''
                }
                <div style="margin-top: 4px;">
                  <span class="badge ${insight.confidence}">${insight.confidence}</span>
                  <span class="badge">${insight.category?.replace(/_/g, ' ')}</span>
                </div>
              </div>
            `
              )
              .join('')}
          </div>
        `
            : ''
        }

        ${
          evidencePatterns.length > 0
            ? `
          <div class="section">
            <h2>Evidence Patterns (${evidencePatterns.length} Total)</h2>
            ${evidencePatterns
              .slice(0, 15)
              .map(
                (pattern: EvidencePatternModel, index: number) => `
              <div class="pattern-card ${pattern.pattern_type}">
                <h3>${index + 1}. ${pattern.name}</h3>
                ${
                  pattern.evidence
                    ? `
                  <p style="margin: 4px 0; color: #d1d5db; font-size: 8pt;">${pattern.evidence}</p>
                `
                    : ''
                }
                <div style="margin-top: 4px;">
                  <span class="badge">${pattern.pattern_type}</span>
                  <span class="badge">${pattern.category}</span>
                </div>
              </div>
            `
              )
              .join('')}
          </div>
        `
            : ''
        }
      </div>
      <div class="page-footer">
        <p>© 2025 Exiqus GitHub Analyser • Confidential Analysis Report</p>
      </div>
    </div>

    ${
      insights.length > 10
        ? `
    <!-- Remaining Insights -->
    <div class="page">
      <div class="page-content">
        <div class="section">
          <h2>Key Insights (Continued)</h2>
          ${insights
            .slice(10)
            .map(
              (insight: InsightModel, index: number) => `
            <div class="insight-card">
              <h3>${index + 11}. ${insight.description}</h3>
              ${
                insight.evidence && insight.evidence.length > 0
                  ? `
                <div style="margin-top: 4px;">
                  ${insight.evidence
                    .slice(0, 1)
                    .map(
                      (ev: string) => `
                    <div class="evidence-item">• ${ev}</div>
                  `
                    )
                    .join('')}
                </div>
              `
                  : ''
              }
              <div style="margin-top: 4px;">
                <span class="badge ${insight.confidence}">${insight.confidence}</span>
                <span class="badge">${insight.category?.replace(/_/g, ' ')}</span>
              </div>
            </div>
          `
            )
            .join('')}
        </div>
      </div>
      <div class="page-footer">
        <p>© 2025 Exiqus GitHub Analyser • Confidential Analysis Report</p>
      </div>
    </div>
    `
        : ''
    }

    ${
      evidencePatterns.length > 15
        ? `
    <!-- Remaining Evidence Patterns -->
    <div class="page">
      <div class="page-content">
        <div class="section">
          <h2>Evidence Patterns (Continued)</h2>
          ${evidencePatterns
            .slice(15)
            .map(
              (pattern: EvidencePatternModel, index: number) => `
            <div class="pattern-card ${pattern.pattern_type}">
              <h3>${index + 16}. ${pattern.name}</h3>
              ${
                pattern.evidence
                  ? `
                <p style="margin: 4px 0; color: #d1d5db; font-size: 8pt;">${pattern.evidence}</p>
              `
                  : ''
              }
              <div style="margin-top: 4px;">
                <span class="badge">${pattern.pattern_type}</span>
                <span class="badge">${pattern.category}</span>
              </div>
            </div>
          `
            )
            .join('')}
        </div>
      </div>
      <div class="page-footer">
        <p>© 2025 Exiqus GitHub Analyser • Confidential Analysis Report</p>
      </div>
    </div>
    `
        : ''
    }

    <!-- Questions and Indicators Page -->
    <div class="page">
      <div class="page-content">
        ${
          questions.length > 0
            ? `
          <div class="section">
            <h2>Interview Questions (${questions.length} Total)</h2>
            ${questions
              .map(
                (question: QuestionModel, index: number) => `
              <div class="question-card">
                <div class="question-number">Q${index + 1}</div>
                <h3>${question.question}</h3>
                ${
                  question.evidence_reference
                    ? `
                  <p style="margin: 4px 0; color: #9ca3af; font-size: 8pt;">
                    <strong>Based on:</strong> ${question.evidence_reference}
                  </p>
                `
                    : ''
                }
                ${
                  question.follow_ups && question.follow_ups.length > 0
                    ? `
                  <div class="follow-ups">
                    <h4>Follow-up questions:</h4>
                    <ul style="margin: 2px 0;">
                      ${question.follow_ups
                        .slice(0, 2)
                        .map((f: string) => `<li>${f}</li>`)
                        .join('')}
                    </ul>
                  </div>
                `
                    : ''
                }
                ${
                  question.what_to_listen_for
                    ? `
                  <div class="evidence-item" style="margin-top: 4px;">
                    <strong>Listen for:</strong> ${question.what_to_listen_for}
                  </div>
                `
                    : ''
                }
              </div>
            `
              )
              .join('')}
          </div>
        `
            : ''
        }

        ${
          greenFlags.length > 0 || redFlags.length > 0 || areasToExplore.length > 0
            ? `
          <div class="section">
            <h2>Key Indicators</h2>
            ${
              greenFlags.length > 0
                ? `
              <div style="margin-bottom: 8px;">
                <h3 style="color: #4ade80; margin-bottom: 4px; font-size: 10pt;">✓ Positive Indicators</h3>
                <ul style="margin-left: 15px;">
                  ${greenFlags
                    .slice(0, 5)
                    .map(
                      (flag: string) => `<li style="color: #86efac; font-size: 8pt;">${flag}</li>`
                    )
                    .join('')}
                </ul>
              </div>
            `
                : ''
            }
            ${
              redFlags.length > 0 || areasToExplore.length > 0
                ? `
              <div>
                <h3 style="color: #fbbf24; margin-bottom: 4px; font-size: 10pt;">⚠ Areas to Explore</h3>
                <ul style="margin-left: 15px;">
                  ${redFlags
                    .slice(0, 3)
                    .map(
                      (flag: string) => `<li style="color: #fcd34d; font-size: 8pt;">${flag}</li>`
                    )
                    .join('')}
                  ${areasToExplore
                    .slice(0, 3)
                    .map(
                      (area: string) => `<li style="color: #fcd34d; font-size: 8pt;">${area}</li>`
                    )
                    .join('')}
                </ul>
              </div>
            `
                : ''
            }
          </div>
        `
            : ''
        }
      </div>
      <div class="page-footer">
        <p>© 2025 Exiqus GitHub Analyser • Confidential Analysis Report</p>
      </div>
    </div>

    <!-- Recommendations Page -->
    ${
      recommendations.length > 0
        ? `
      <div class="page">
        <div class="page-content">
          <div class="section">
            <h2>Recommendations (${recommendations.length} Total)</h2>
            ${recommendations
              .map(
                (rec: RecommendationModel, index: number) => `
              <div class="recommendation ${rec.type === 'concern' ? 'concern' : ''}">
                <h3>${index + 1}. ${rec.text}</h3>
                ${
                  rec.evidence
                    ? `
                  <p style="margin: 4px 0; color: #9ca3af; font-size: 8pt;">
                    <strong>Based on:</strong> ${rec.evidence}
                  </p>
                `
                    : ''
                }
                <div style="margin-top: 4px;">
                  <span class="badge ${rec.priority}">${rec.priority} priority</span>
                  <span class="badge">${rec.type}</span>
                </div>
              </div>
            `
              )
              .join('')}
          </div>
        </div>
        <div class="page-footer">
          <p>© 2025 Exiqus GitHub Analyser • Confidential Analysis Report</p>
        </div>
      </div>
    `
        : ''
    }
  </div>
</body>
</html>
  `;

  return pdfContent;
};

export const generateHTMLExport = (data: AnalysisDetails, _currentUser?: unknown) => {
  const pdfContent = generatePDFExport(data, _currentUser);
  // HTML export uses the same content as PDF but with slightly different styling
  return pdfContent
    .replace('@page { size: A4; margin: 0; }', '')
    .replace('page-break-after: always;', '')
    .replace('page-break-inside: avoid;', '');
};

export const generateMarkdownExport = (data: AnalysisDetails, _currentUser?: unknown) => {
  const analysisData = data.full_analysis.analysis;
  const insights = analysisData.insights || [];
  const questions = analysisData.questions || [];
  const evidencePatterns = analysisData.evidence_patterns || [];
  const recommendations = analysisData.recommendations || [];
  const summary = analysisData.executive_summary || '';
  const confidenceExplanation = analysisData.confidence_explanation || '';
  const greenFlags = analysisData.green_flags || [];
  const redFlags = analysisData.red_flags || [];
  const areasToExplore = analysisData.areas_to_explore || [];

  const markdown = `# GitHub Repository Analysis Report

## Repository Information
- **Name:** ${data.repository_name}
- **URL:** ${data.repository_url}
- **Analysis Date:** ${format(new Date(data.created_at), 'PPP')}
- **Context:** ${data.context}

## Executive Summary
${summary}

${confidenceExplanation ? `**Evidence Quality:** ${confidenceExplanation}` : ''}

## Key Metrics
- **Insights:** ${insights.length}
- **Evidence Patterns:** ${evidencePatterns.length}
- **Questions:** ${questions.length}
- **Recommendations:** ${recommendations.length}

${
  insights.length > 0
    ? `
## Key Insights
${insights
  .map(
    (insight: InsightModel, index: number) => `
### ${index + 1}. ${insight.description}
${insight.evidence && insight.evidence.length > 0 ? insight.evidence.map((ev: string) => `- ${ev}`).join('\n') : ''}
- **Confidence:** ${insight.confidence}
- **Category:** ${insight.category?.replace(/_/g, ' ')}
${insight.impact ? `- **Impact:** ${insight.impact}` : ''}
`
  )
  .join('\n')}
`
    : ''
}

${
  evidencePatterns.length > 0
    ? `
## Evidence Patterns
${evidencePatterns
  .map(
    (pattern: EvidencePatternModel, index: number) => `
### ${index + 1}. ${pattern.name}
- **Type:** ${pattern.pattern_type}
- **Category:** ${pattern.category}
${pattern.evidence ? `- **Evidence:** ${pattern.evidence}` : ''}
`
  )
  .join('\n')}
`
    : ''
}

${
  questions.length > 0
    ? `
## Interview Questions
${questions
  .map(
    (question: QuestionModel, index: number) => `
### Q${index + 1}: ${question.question}
${question.evidence_reference ? `- **Based on:** ${question.evidence_reference}` : ''}
${
  question.follow_ups && question.follow_ups.length > 0
    ? `
**Follow-up questions:**
${question.follow_ups.map((f: string) => `- ${f}`).join('\n')}
`
    : ''
}
${question.what_to_listen_for ? `- **Listen for:** ${question.what_to_listen_for}` : ''}
`
  )
  .join('\n')}
`
    : ''
}

${
  greenFlags.length > 0 || redFlags.length > 0 || areasToExplore.length > 0
    ? `
## Key Indicators

${
  greenFlags.length > 0
    ? `
### Positive Indicators
${greenFlags.map((flag: string) => `- ${flag}`).join('\n')}
`
    : ''
}

${
  redFlags.length > 0 || areasToExplore.length > 0
    ? `
### Areas to Explore
${redFlags.map((flag: string) => `- ${flag}`).join('\n')}
${areasToExplore.map((area: string) => `- ${area}`).join('\n')}
`
    : ''
}
`
    : ''
}

${
  recommendations.length > 0
    ? `
## Recommendations
${recommendations
  .map(
    (rec: RecommendationModel, index: number) => `
### ${index + 1}. ${rec.text}
- **Priority:** ${rec.priority}
- **Type:** ${rec.type}
${rec.evidence ? `- **Based on:** ${rec.evidence}` : ''}
`
  )
  .join('\n')}
`
    : ''
}

---
*Generated by Exiqus GitHub Analyser on ${format(new Date(), 'PPP')}*
`;

  return markdown;
};
