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
    
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }
    
    html {
      height: 100%;
      background: #0A0A0F !important;
      margin: 0;
      padding: 0;
    }
    
    body { 
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
    }
    
    /* Container for content */
    .container {
      padding: 25px;
      background: linear-gradient(to bottom, #0A0A0F, #0f0f14);
      min-height: 100vh;
    }
    
    /* Force dark background for printing */
    @media print {
      html, body {
        background: #0A0A0F !important;
        color: #e5e7eb !important;
        margin: 0;
        padding: 0;
        height: 100%;
      }
      
      .container {
        padding: 20px;
        min-height: 100vh;
      }
      
      * {
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
        color-adjust: exact !important;
      }
    }
    
    /* Header with gradient like UI */
    .header {
      background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #ec4899 100%);
      color: white;
      padding: 35px;
      margin: -25px -25px 30px -25px;
      border-radius: 0 0 20px 20px;
      box-shadow: 0 10px 30px rgba(99, 102, 241, 0.3);
    }
    
    .header h1 { 
      font-size: 26pt;
      font-weight: 700;
      margin-bottom: 12px;
      text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }
    
    .header p { 
      font-size: 12pt;
      margin: 4px 0;
      opacity: 0.95;
    }
    
    /* Section headings */
    h2 {
      color: #c7d2fe;
      font-size: 18pt;
      font-weight: 600;
      margin: 35px 0 20px 0;
      padding-bottom: 10px;
      border-bottom: 2px solid rgba(99, 102, 241, 0.3);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    
    h3 {
      color: #e5e7eb;
      font-size: 13pt;
      font-weight: 500;
      margin: 20px 0 10px 0;
    }
    
    p {
      margin: 10px 0;
      font-size: 11pt;
      line-height: 1.6;
      color: #d1d5db;
    }
    
    /* Metrics Grid */
    .metrics {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 20px;
      margin: 30px 0;
    }
    
    .metric {
      background: linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(139, 92, 246, 0.1));
      border: 1px solid rgba(99, 102, 241, 0.3);
      border-radius: 15px;
      padding: 20px;
      text-align: center;
      box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
    }
    
    .metric-value {
      font-size: 28pt;
      font-weight: bold;
      color: #e0e7ff;
      display: block;
      margin-bottom: 5px;
    }
    
    .metric-label {
      font-size: 11pt;
      color: #a5b4fc;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    
    /* Insight Cards matching UI design */
    .insight-card {
      background: linear-gradient(to bottom right, #1e1e2e, #1a1a28);
      border: 1px solid rgba(99, 102, 241, 0.2);
      border-radius: 15px;
      padding: 20px;
      margin-bottom: 20px;
      box-shadow: 0 6px 15px rgba(0, 0, 0, 0.5);
    }
    
    .insight-card h4 {
      font-size: 13pt;
      color: #f3f4f6;
      margin-bottom: 10px;
      line-height: 1.5;
    }
    
    .insight-card .evidence {
      background: rgba(99, 102, 241, 0.08);
      border-left: 3px solid #6366f1;
      padding: 12px 15px;
      margin: 12px 0;
      border-radius: 8px;
      font-size: 11pt;
      color: #d1d5db;
    }
    
    /* Evidence box matching UI */
    .evidence-box {
      background: linear-gradient(to right, rgba(99, 102, 241, 0.15), rgba(99, 102, 241, 0.05));
      border-left: 3px solid #6366f1;
      padding: 12px 16px;
      margin: 12px 0;
      border-radius: 6px;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
    }
    
    /* Badges */
    .badge {
      display: inline-block;
      padding: 4px 10px;
      border-radius: 8px;
      font-size: 10pt;
      font-weight: 500;
      margin-right: 8px;
    }
    
    .badge-confidence {
      background: rgba(99, 102, 241, 0.2);
      color: #a5b4fc;
    }
    
    .badge-category {
      background: rgba(147, 51, 234, 0.2);
      color: #c084fc;
    }
    
    .badge-type {
      background: rgba(34, 197, 94, 0.2);
      color: #86efac;
    }
    
    .badge-priority-high {
      background: rgba(239, 68, 68, 0.2);
      color: #f87171;
    }
    
    .badge-priority-medium {
      background: rgba(251, 191, 36, 0.2);
      color: #fbbf24;
    }
    
    .badge-priority-low {
      background: rgba(34, 197, 94, 0.2);
      color: #86efac;
    }
    
    /* Lists */
    ul {
      margin: 4px 0 4px 15px;
      padding: 0;
    }
    
    li {
      font-size: 8pt;
      margin: 2px 0;
    }
    
    /* Summary Box */
    .summary-box {
      background: linear-gradient(135deg, rgba(99, 102, 241, 0.08), rgba(139, 92, 246, 0.04));
      border: 1px solid rgba(99, 102, 241, 0.2);
      border-radius: 15px;
      padding: 25px;
      margin: 25px 0;
      font-size: 12pt;
      line-height: 1.7;
      color: #e5e7eb;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }
    
    /* Evidence Pattern Cards */
    .evidence-card {
      background: linear-gradient(135deg, rgba(34, 197, 94, 0.1), rgba(16, 185, 129, 0.05));
      border: 1px solid rgba(34, 197, 94, 0.3);
      border-radius: 12px;
      padding: 18px;
      margin-bottom: 15px;
      box-shadow: 0 4px 10px rgba(0, 0, 0, 0.4);
    }
    
    .evidence-card h4 {
      font-size: 12pt;
      color: #86efac;
      margin-bottom: 8px;
    }
    
    .evidence-card p {
      font-size: 11pt;
      color: #d1d5db;
      margin: 8px 0;
    }
    
    /* Question Cards */
    .question-card {
      background: linear-gradient(135deg, #1f1f2e, #1a1a28);
      border: 2px solid rgba(251, 191, 36, 0.3);
      border-radius: 15px;
      padding: 25px;
      margin-bottom: 30px;
      box-shadow: 0 8px 20px rgba(0, 0, 0, 0.5);
      page-break-inside: avoid;
      break-inside: avoid;
      position: relative;
    }
    
    .question-number {
      color: #fbbf24;
      font-weight: bold;
      font-size: 16pt;
      margin-bottom: 10px;
      display: block;
    }
    
    .question-text {
      color: #f3f4f6;
      font-size: 12pt;
      margin-bottom: 15px;
      line-height: 1.7;
      font-weight: 500;
    }
    
    .follow-ups {
      background: rgba(59, 130, 246, 0.08);
      border-radius: 10px;
      padding: 15px;
      margin: 12px 0;
    }
    
    .follow-ups strong {
      color: #93c5fd;
      font-size: 11pt;
      display: block;
      margin-bottom: 8px;
    }
    
    .follow-ups li {
      color: #d1d5db;
      font-size: 10pt;
      margin: 6px 0;
      line-height: 1.5;
    }
    
    .listen-for {
      background: rgba(34, 197, 94, 0.08);
      border-left: 3px solid #22c55e;
      border-radius: 10px;
      padding: 15px;
      margin: 12px 0;
    }
    
    .listen-for strong {
      color: #86efac;
      font-size: 11pt;
      display: block;
      margin-bottom: 5px;
    }
    
    .listen-for span {
      color: #d1d5db;
      font-size: 11pt;
    }
    
    /* Indicators Section */
    .indicators {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 25px;
      margin: 25px 0;
    }
    
    .indicator-box {
      background: linear-gradient(135deg, rgba(99, 102, 241, 0.05), rgba(139, 92, 246, 0.02));
      border-radius: 15px;
      padding: 20px;
      border: 1px solid rgba(99, 102, 241, 0.2);
    }
    
    /* Recommendations */
    .recommendation-card {
      background: linear-gradient(to right, #1e1e2e, #1a1a28);
      border: 1px solid rgba(147, 51, 234, 0.2);
      border-radius: 15px;
      padding: 20px;
      margin-bottom: 20px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
    }
    
    .recommendation-card h4 {
      font-size: 13pt;
      color: #f3f4f6;
      margin-bottom: 10px;
    }
    
    .recommendation-card .based-on {
      font-size: 11pt;
      color: #9ca3af;
      margin: 10px 0;
    }
    
    .recommendation-card .based-on strong {
      color: #a5b4fc;
    }
    
    /* Footer */
    .footer {
      text-align: center;
      color: #6b7280;
      font-size: 10pt;
      margin-top: 40px;
      padding-top: 20px;
      border-top: 1px solid rgba(99, 102, 241, 0.2);
    }
    
    /* Enhanced Page break controls */
    .page-break {
      page-break-before: always;
      break-before: always;
      margin: 0;
      padding: 0;
      height: 0;
    }
    
    /* Prevent breaks inside critical elements */
    .insight-card, .evidence-card, .question-card, .recommendation-card {
      page-break-inside: avoid;
      break-inside: avoid;
    }
    
    h1, h2, h3, h4, h5, h6 {
      page-break-after: avoid;
      break-after: avoid;
      page-break-inside: avoid;
      break-inside: avoid;
    }
    
    /* Keep elements together */
    .question-card {
      page-break-inside: avoid;
      break-inside: avoid;
      display: block;
    }
    
    .follow-ups, .listen-for {
      page-break-inside: avoid;
      break-inside: avoid;
    }
    
    /* Orphan and widow control */
    p, li {
      orphans: 3;
      widows: 3;
    }
    
    @media print {
      .no-print {
        display: none;
      }
      
      /* Ensure questions don't break */
      .question-card {
        page-break-inside: avoid !important;
        break-inside: avoid !important;
      }
      
      /* Keep sections together when possible */
      .section {
        page-break-inside: avoid;
        break-inside: avoid;
      }
    }
  </style>
</head>
<body>
  <div class="container">
  <!-- Page 1: Header, Summary, Metrics, Top Insights -->
  <div class="header">
    <h1>${data.repository_name}</h1>
    <p><strong>URL:</strong> ${data.repository_url}</p>
    <p><strong>Analysis Date:</strong> ${format(new Date(data.created_at), 'PPP')} | <strong>Context:</strong> ${data.context}</p>
  </div>

  <h2>Executive Summary</h2>
  <div class="summary-box">
    ${summary}
    ${
      confidenceExplanation
        ? `
      <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(99, 102, 241, 0.2);">
        <strong style="color: #a5b4fc;">Evidence Quality:</strong> ${confidenceExplanation}
      </div>
    `
        : ''
    }
  </div>

  <div class="metrics">
    <div class="metric">
      <div class="metric-value">${insights.length}</div>
      <div class="metric-label">Insights</div>
    </div>
    <div class="metric">
      <div class="metric-value">${evidencePatterns.length}</div>
      <div class="metric-label">Evidence</div>
    </div>
    <div class="metric">
      <div class="metric-value">${questions.length}</div>
      <div class="metric-label">Questions</div>
    </div>
    <div class="metric">
      <div class="metric-value">${recommendations.length}</div>
      <div class="metric-label">Actions</div>
    </div>
  </div>

  <h2>Key Insights</h2>
  ${insights
    .map(
      (insight: InsightModel, index: number) => `
    <div class="insight-card">
      <h4>${index + 1}. ${insight.description}</h4>
      ${
        insight.evidence && insight.evidence.length > 0
          ? `<div class="evidence">• ${insight.evidence[0]}</div>`
          : ''
      }
      <div style="margin-top: 12px;">
        <span class="badge badge-confidence">${insight.confidence}</span>
        <span class="badge badge-category">${insight.category?.replace(/_/g, ' ')}</span>
      </div>
    </div>
  `
    )
    .join('')}


  ${insights.length > 3 ? '<div class="page-break"></div>' : ''}
  
  <h2>Evidence Patterns</h2>
  ${evidencePatterns
    .map(
      (pattern: EvidencePatternModel, index: number) => `
    <div class="evidence-card" style="background: linear-gradient(135deg, rgba(34, 197, 94, 0.1), rgba(16, 185, 129, 0.05)); border: 1px solid rgba(34, 197, 94, 0.3); border-radius: 12px; padding: 18px; margin-bottom: 15px; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.4);">
      <h4 style="font-size: 12pt; color: #86efac; margin-bottom: 8px;">${index + 1}. ${pattern.name}</h4>
      ${pattern.evidence ? `<p style="font-size: 11pt; color: #d1d5db; margin: 8px 0;">${pattern.evidence}</p>` : ''}
      <div style="margin-top: 10px;">
        <span class="badge badge-type">${pattern.pattern_type}</span>
        <span class="badge badge-category">${pattern.category}</span>
      </div>
    </div>
  `
    )
    .join('')}


  ${evidencePatterns.length > 3 ? '<div class="page-break"></div>' : ''}

  <h2>Interview Questions</h2>
  <div style="margin-bottom: 20px;">
  ${questions
    .map(
      (question: QuestionModel, index: number) => `
    <div class="question-card" style="page-break-inside: avoid; break-inside: avoid; min-height: 0;">
      <span class="question-number">Q${index + 1}</span>
      <div class="question-text">${question.question}</div>
      ${
        question.evidence_reference
          ? `
        <div style="font-size: 11pt; color: #9ca3af; margin-top: 10px;">
          <strong style="color: #a5b4fc;">Based on:</strong> ${question.evidence_reference}
        </div>
      `
          : ''
      }
      ${
        question.follow_ups && question.follow_ups.length > 0
          ? `
        <div class="follow-ups">
          <strong>Follow-up questions:</strong>
          <ul style="margin: 8px 0 0 20px; padding: 0;">
            ${question.follow_ups.map((f: string) => `<li>${f}</li>`).join('')}
          </ul>
        </div>
      `
          : ''
      }
      ${
        question.what_to_listen_for
          ? `
        <div class="listen-for">
          <strong>Listen for:</strong>
          <span>${question.what_to_listen_for}</span>
        </div>
      `
          : ''
      }
    </div>
  `
    )
    .join('')}
  </div>

  ${questions.length > 2 ? '<div class="page-break"></div>' : ''}
  
  <h2>Key Indicators</h2>
  <div class="indicators">
    ${
      greenFlags.length > 0
        ? `
      <div class="indicator-box">
        <h3 class="positive-indicators" style="color: #4ade80;">✓ Positive Indicators</h3>
        <ul style="margin: 10px 0 0 20px;">
          ${greenFlags.map((flag: string) => `<li style="font-size: 11pt; margin: 6px 0;">${flag}</li>`).join('')}
        </ul>
      </div>
    `
        : ''
    }
    ${
      redFlags.length > 0 || areasToExplore.length > 0
        ? `
      <div class="indicator-box">
        <h3 class="warning-indicators" style="color: #fbbf24;">⚠ Areas to Explore</h3>
        <ul style="margin: 10px 0 0 20px;">
          ${[...redFlags, ...areasToExplore].map((item: string) => `<li style="font-size: 11pt; margin: 6px 0;">${item}</li>`).join('')}
        </ul>
      </div>
    `
        : ''
    }
  </div>

  <h2>Recommendations</h2>
  ${recommendations
    .map(
      (rec: RecommendationModel, index: number) => `
    <div class="recommendation-card" style="${rec.type === 'concern' ? 'border-color: rgba(239, 68, 68, 0.3);' : ''}">
      <h4>${index + 1}. ${rec.text}</h4>
      ${
        rec.evidence
          ? `
        <div class="based-on">
          <strong>Based on:</strong> ${rec.evidence}
        </div>
      `
          : ''
      }
      <div style="margin-top: 12px;">
        <span class="badge badge-priority-${rec.priority}">${rec.priority} priority</span>
        <span class="badge badge-category">${rec.type}</span>
      </div>
    </div>
  `
    )
    .join('')}

  <div class="footer">
    <p>© 2025 Exiqus GitHub Analyser • Confidential Analysis Report</p>
  </div>
  </div>
</body>
</html>
  `;

  return pdfContent;
};

export const generateHTMLExport = (data: AnalysisDetails, _currentUser?: unknown) => {
  return generatePDFExport(data, _currentUser);
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
