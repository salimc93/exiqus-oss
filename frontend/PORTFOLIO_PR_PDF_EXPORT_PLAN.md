# Portfolio & PR Analysis PDF Export Implementation Plan

## Overview

Add client-side PDF export functionality for Portfolio Analysis and PR Analysis pages, following the exact pattern used for single repository analysis.

---

## Current Architecture (Single Repo Reference)

### File Structure

- **Export Functions**: `/frontend/src/utils/export-functions.tsx`
- **Implementation**: `/frontend/src/app/analyses/[id]/page.tsx`

### How It Works

1. Client-side HTML generation with dark theme CSS
2. Opens print dialog in new window (`window.open()`)
3. User saves as PDF using browser's print-to-PDF
4. Tier-gated: JSON (all), PDF/HTML (Starter+), Markdown (Scale+)

### Key Pattern

```typescript
const handleExport = async (exportFormat: 'json' | 'pdf' | 'html' | 'markdown') => {
  if (exportFormat === 'pdf') {
    const pdfContent = generatePDFExport(analysis, user);
    const printWindow = window.open('', '_blank');
    printWindow.document.write(pdfContent);
    printWindow.document.close();
    printWindow.focus();
    setTimeout(() => printWindow.print(), 250);
  }
};
```

---

## Implementation Tasks

### 1. Create Portfolio Export Functions

**File**: `/frontend/src/utils/portfolio-export-functions.tsx`

#### Portfolio Data Structure

```typescript
interface PortfolioAnalysisData {
  id: string;
  github_username: string;
  context: string; // STARTUP, ENTERPRISE, AGENCY, OPEN_SOURCE
  role: string; // JUNIOR, MID, SENIOR
  total_repos: number;
  repos_analyzed: number;
  repos_skipped: number;
  repositories_analyzed?: string[]; // ["owner/repo", ...]
  full_analysis: string; // Markdown content with ## sections
  analysis_metadata: {
    oldest_repo_date: string;
    newest_repo_date: string;
    portfolio_span_days: number;
    model: string;
    token_count: number;
  };
  processing_time_seconds: number;
  created_at: string;
}
```

#### Sections to Extract (from markdown)

1. **Executive Summary** (required)
2. **Key Strengths** (required)
3. **Technical Evolution** (required)
4. **Evidence Patterns** (parse as structured list)
5. **Interview Framework** (questions)
6. **Areas to Explore** (concerns/questions)
7. **Observable Patterns** (technical details)

#### Functions to Create

```typescript
export const generatePortfolioPDFExport = (data: PortfolioAnalysisData) => {
  // Parse markdown sections
  const sections = parsePortfolioSections(data.full_analysis);

  // Extract structured data
  const evidencePatterns = extractEvidencePatterns(sections);
  const interviewQuestions = extractInterviewQuestions(sections);
  const keyStrengths = extractKeyStrengths(sections);

  // Generate HTML with dark theme
  return generatePortfolioHTML(data, sections, evidencePatterns, interviewQuestions);
};

const parsePortfolioSections = (markdown: string) => {
  // Split by ## headers, extract content
};

const extractEvidencePatterns = (sections: Record<string, string>) => {
  // Parse "🔍 Evidence Patterns" section
  // Format: ### Pattern Name\n**Evidence:** ...\n**Analysis:** ...
};

const extractInterviewQuestions = (sections: Record<string, string>) => {
  // Parse "💬 Interview Framework" section
  // Format: ### Category\n**Q:** ...\n**Follow-up:** ...\n**Listen for:** ...
};
```

#### PDF Layout (Dark Theme)

```css
/* Match single repo export styling */
- A4 page size
- Dark background (#0A0A0F)
- Gradient header (purple → blue → pink)
- Section cards with borders
- Evidence boxes with left border accent
- Interview questions in bordered cards
- Print-optimized: page-break controls, orphan/widow control
```

**Header Content**:

```
Portfolio Analysis: @{username}
Context: {context} | Role: {role}
Analysis Date: {created_at}
Repositories: {repos_analyzed} analyzed, {repos_skipped} skipped
Portfolio Span: {oldest_date} → {newest_date} ({span_days} days)
```

**Metrics Grid** (4 columns):

- Total Repositories
- Repositories Analyzed
- Portfolio Span (days)
- Evidence Patterns Count

---

### 2. Create PR Export Functions

**File**: `/frontend/src/utils/pr-export-functions.tsx`

#### PR Data Structure

```typescript
interface PRAnalysisData {
  username: string;
  context: string;
  role: string;
  total_prs_analyzed: number;
  repositories_contributed: string[]; // ["owner/repo", ...]
  summary_report: string; // Main summary text
  detailed_report: {
    evidence?: {
      technical_substance?: string[];
      collaboration_patterns?: string[];
      review_responsiveness?: string[];
      cross_repo_contributions?: string[];
      areas_to_explore?: string[];
    };
    quality_signals?: {
      total_prs?: number;
      merged_prs?: number;
      unique_repos?: number;
      contribution_timespan?: string;
      feature_prs?: number;
      fix_prs?: number;
    };
  };
  evidence_patterns?: Array<{
    name: string;
    pattern_type: string;
    evidence: string;
    context: string;
    insight: string;
    category: string;
  }>;
  ai_insights?: {
    executive_summary?: string;
    confidence_explanation?: string;
    interview_questions?: Array<{
      question: string;
      category?: string;
      evidence_reference?: string;
      follow_up_questions?: string[];
      key_listening_points?: string;
    }>;
    key_insights?: Array<{
      title: string;
      category: string;
      description: string;
      evidence: string;
      impact: 'positive' | 'negative' | 'neutral';
    }>;
    key_strengths?: string[];
  };
  created_at: string;
}
```

#### Sections to Include

1. **Executive Summary** (ai_insights.executive_summary or summary_report)
2. **Key Insights** (ai_insights.key_insights with impact colors)
3. **Interview Questions** (ai_insights.interview_questions)
4. **Evidence Patterns** (evidence_patterns array)
5. **Technical Substance** (detailed_report.evidence.technical_substance)
6. **Collaboration Patterns** (detailed_report.evidence.collaboration_patterns)
7. **Quality Signals** (detailed_report.quality_signals as metrics)
8. **Areas to Explore** (detailed_report.evidence.areas_to_explore)

#### Functions to Create

```typescript
export const generatePRPDFExport = (data: PRAnalysisData) => {
  // Extract all sections
  const executiveSummary = data.ai_insights?.executive_summary || data.summary_report;
  const keyInsights = data.ai_insights?.key_insights || [];
  const interviewQuestions = data.ai_insights?.interview_questions || [];
  const evidencePatterns = data.evidence_patterns || [];

  // Generate HTML
  return generatePRHTML(data, executiveSummary, keyInsights, interviewQuestions, evidencePatterns);
};
```

#### PDF Layout

**Header Content**:

```
PR Analysis: @{username}
Context: {context} | Role: {role}
Analysis Date: {created_at}
PRs Analyzed: {total_prs_analyzed} across {unique_repos} repositories
Contribution Timespan: {timespan}
```

**Metrics Grid** (5 columns):

- Total PRs
- Merged PRs
- Unique Repos
- Feature PRs
- Fix PRs

**Key Insight Cards** with impact badges:

- Positive (green)
- Negative (red)
- Neutral (gray)

---

### 3. Add Export UI to Portfolio Analysis Page

**File**: `/frontend/src/app/portfolio-analyses/[id]/page.tsx`

#### Import Export Functions

```typescript
import { generatePortfolioPDFExport } from '@/utils/portfolio-export-functions';
```

#### Add State Management

```typescript
const [showExportMenu, setShowExportMenu] = useState(false);
```

#### Add Export Handler

```typescript
const handleExport = async (exportFormat: 'json' | 'pdf') => {
  try {
    if (!analysis) return;
    setShowExportMenu(false);

    if (exportFormat === 'json') {
      const blob = new Blob([JSON.stringify(analysis, null, 2)], {
        type: 'application/json',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `portfolio-${analysis.github_username}-${format(new Date(), 'yyyy-MM-dd')}.json`;
      a.click();
      toast.success('Portfolio exported as JSON');
    } else if (exportFormat === 'pdf') {
      const pdfContent = generatePortfolioPDFExport(analysis);
      const printWindow = window.open('', '_blank');
      if (printWindow) {
        printWindow.document.write(pdfContent);
        printWindow.document.close();
        printWindow.focus();
        setTimeout(() => printWindow.print(), 250);
      }
      toast.info('Opening print dialog for PDF export');
    }
  } catch (error) {
    console.error('Export failed:', error);
    toast.error('Failed to export portfolio');
  }
};
```

#### Add Export Button (near back button or header)

```typescript
<div className="relative">
  <ExiqusButton
    variant="secondary"
    onClick={() => setShowExportMenu(!showExportMenu)}
  >
    <Download className="mr-2 h-4 w-4" />
    Export
    <ChevronDown className="ml-2 h-4 w-4" />
  </ExiqusButton>

  {showExportMenu && (
    <div className="absolute right-0 z-30 mt-1 w-48 rounded-md bg-[#1a1a1a] shadow-lg">
      <button onClick={() => handleExport('json')}>
        JSON (All Tiers)
      </button>
      {['starter', 'growth', 'scale', 'scale_plus'].includes(user?.subscription_plan) && (
        <button onClick={() => handleExport('pdf')}>
          PDF
        </button>
      )}
    </div>
  )}
</div>
```

---

### 4. Add Export UI to PR Analysis Page

**File**: `/frontend/src/app/pr-analyses/[id]/page.tsx`

Same pattern as Portfolio Analysis:

1. Import `generatePRPDFExport` from `/utils/pr-export-functions`
2. Add state: `showExportMenu`
3. Add `handleExport` function
4. Add Export dropdown button
5. Tier-gate PDF for Starter+

---

## Styling Reference (Reuse from Single Repo)

### CSS Classes to Maintain

```css
.container - Main wrapper with gradient background
.header - Gradient header (purple → blue → pink)
.summary-box - Executive summary box
.metrics - 4-column grid for key metrics
.metric, .metric-value, .metric-label - Metric cards
.insight-card - Key insights/strengths
.evidence-card - Evidence pattern cards
.question-card - Interview question cards
.question-number, .question-text - Question formatting
.follow-ups, .listen-for - Question sub-sections
.indicators - 2-column grid for positive/explore
.badge-* - Category, confidence, priority badges
.page-break - Page break control
.footer - Copyright footer
```

### Print Optimization

```css
@page {
  size: A4;
  margin: 0;
}
-webkit-print-color-adjust: exact;
page-break-inside: avoid;
orphans: 3;
widows: 3;
```

---

## Tier Gating Rules

### Export Availability

- **Free**: JSON only
- **Starter+**: JSON + PDF + HTML
- **Scale+**: JSON + PDF + HTML + Markdown

### Implementation

```typescript
const plan = user?.subscription_plan;
const canExportPDF = ['starter', 'growth', 'scale', 'scale_plus'].includes(plan);
```

---

## Testing Checklist

### Portfolio PDF Export

- [ ] Parse markdown sections correctly
- [ ] Extract evidence patterns with proper formatting
- [ ] Extract interview questions with follow-ups
- [ ] Display metrics grid (repos, span, patterns)
- [ ] Dark theme renders correctly
- [ ] Page breaks work properly
- [ ] Print dialog opens successfully
- [ ] Export button shows for Starter+ only

### PR PDF Export

- [ ] Extract AI insights (summary, questions, key insights)
- [ ] Display evidence patterns from structured data
- [ ] Show quality signals metrics
- [ ] Render collaboration patterns
- [ ] Impact badges color-coded correctly
- [ ] Dark theme renders correctly
- [ ] Page breaks work properly
- [ ] Export button shows for Starter+ only

### Both Exports

- [ ] JSON export works for all tiers
- [ ] PDF tier-gating enforced
- [ ] Toast notifications appear
- [ ] No console errors
- [ ] Mobile responsive (though PDF is desktop-focused)

---

## Edge Cases to Handle

### Portfolio Analysis

- Empty repositories_analyzed array
- Missing markdown sections
- Malformed markdown (missing headers)
- Very long analysis (pagination)
- Special characters in username

### PR Analysis

- Missing ai_insights (fallback to basic report)
- No evidence_patterns array
- Zero PRs analyzed
- Missing quality_signals
- Empty arrays (technical_substance, etc.)

### Both

- User without subscription plan
- Print dialog blocked by browser
- Very slow page rendering (large content)

---

## Files to Create/Modify

### New Files

1. `/frontend/src/utils/portfolio-export-functions.tsx` - Portfolio PDF generation
2. `/frontend/src/utils/pr-export-functions.tsx` - PR PDF generation

### Modified Files

1. `/frontend/src/app/portfolio-analyses/[id]/page.tsx` - Add export UI
2. `/frontend/src/app/pr-analyses/[id]/page.tsx` - Add export UI

### Reference Files (Do Not Modify)

- `/frontend/src/utils/export-functions.tsx` - Single repo export (copy styling)
- `/frontend/src/app/analyses/[id]/page.tsx` - Export UI pattern

---

## Implementation Order

1. **Create portfolio-export-functions.tsx**
   - Copy CSS from export-functions.tsx
   - Parse Portfolio markdown structure
   - Generate HTML with Portfolio-specific sections
   - Test with sample data

2. **Create pr-export-functions.tsx**
   - Copy CSS from export-functions.tsx
   - Extract PR structured data
   - Generate HTML with PR-specific sections
   - Test with sample data

3. **Add Export to Portfolio Analysis Page**
   - Import export function
   - Add state & handler
   - Add Export button UI
   - Test tier-gating

4. **Add Export to PR Analysis Page**
   - Import export function
   - Add state & handler
   - Add Export button UI
   - Test tier-gating

5. **Quality Checks**
   - Run Prettier, ESLint, TypeScript
   - Test on real Portfolio/PR analyses
   - Verify PDF rendering in multiple browsers
   - Test print-to-PDF workflow

---

## Future Enhancements (Out of Scope)

- Markdown export for Portfolio/PR
- Custom branding (logo, colors)
- Email PDF directly
- Batch export (multiple analyses)
- Server-side PDF generation
- PDF templates/themes

---

## Notes

- **Client-side only**: No backend changes required
- **Browser print dialog**: Users save PDF themselves (simple, no dependencies)
- **Dark theme**: Matches Exiqus brand and UI design
- **Reuse patterns**: Copy extensively from single repo export
- **Tier enforcement**: Check user.subscription_plan before showing PDF option
