// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

/* eslint-disable @typescript-eslint/no-explicit-any */
'use client';

import { format } from 'date-fns';
import {
  AlertCircle,
  ArrowLeft,
  Award,
  BarChart3,
  Brain,
  Calendar,
  ChevronDown,
  ChevronRight,
  Clock,
  Code2,
  Eye,
  FileText,
  GitBranch,
  GitPullRequest,
  MessageCircle,
  Search,
  Shield,
  Sparkles,
  Target,
  TrendingUp,
  User,
} from 'lucide-react';
import { useParams, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { UnauthorizedAccess } from '@/components/auth/unauthorized-access';
import { ExiqusButton, ExiqusCard, GradientText } from '@/components/ui/exiqus-components';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useAuth } from '@/contexts/auth-context';
import { api } from '@/lib/api-client';
import { renderMarkdownSafe } from '@/lib/sanitize';

interface PortfolioAnalysisData {
  id: string;
  user_id: string;
  github_username: string;
  context: string;
  role: string;
  status?: 'pending' | 'processing' | 'completed' | 'failed';
  total_repos: number;
  repos_analyzed: number;
  repos_skipped: number;
  repositories_analyzed?: string[]; // List of "username/repo" strings for clickable links
  full_analysis: string;
  data_quality?: string;
  pr_count?: number; // Total PR count
  has_pr_analysis?: boolean; // Whether PR analysis exists
  pr_analysis_id?: string; // ID of existing PR analysis
  show_pr_card?: boolean; // Whether to show PR card
  analysis_metadata: {
    total_public_repos: number;
    repos_analyzed: number;
    repos_skipped: number;
    forks_count?: number;
    oldest_repo_date: string;
    newest_repo_date: string;
    portfolio_span_days: number;
    model: string;
    token_count: number;
    api_cost: number;
  };
  processing_time_seconds: number;
  from_cache: boolean;
  created_at: string;
}

// Helper to format duration
const formatDuration = (seconds: number): string => {
  const totalSeconds = Math.round(seconds);
  const minutes = Math.floor(totalSeconds / 60);
  const remainingSeconds = totalSeconds % 60;

  if (minutes === 0) {
    return `${totalSeconds}s`;
  } else if (minutes < 60) {
    return remainingSeconds > 0 ? `${minutes}m ${remainingSeconds}s` : `${minutes}m`;
  } else {
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}m` : `${hours}h`;
  }
};

// Strip markdown formatting for clean display (used for parsing/extraction)
const stripMarkdown = (text: string): string => {
  return text
    .replace(/\*\*([^*]+)\*\*/g, '$1') // **bold** -> bold
    .replace(/\*([^*]+)\*/g, '$1') // *italic* -> italic
    .replace(/`([^`]+)`/g, '$1') // `code` -> code
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // [text](url) -> text
    .replace(/^#+\s+/gm, '') // ### headers -> text
    .trim();
};

// Render markdown with bold support (used for display) - XSS safe
const renderMarkdown = (text: string) => {
  return <span dangerouslySetInnerHTML={{ __html: renderMarkdownSafe(text) }} />;
};

// Parse markdown sections
const parsePortfolioAnalysis = (markdown: string) => {
  const sections: Record<string, string> = {};

  // Split by ## headers
  const parts = markdown.split(/^##\s+/m);

  parts.forEach((part) => {
    const lines = part.trim().split('\n');
    const title = lines[0]?.replace(/[📊⚠️🏢💡📈🔍💬✨🔍✅📈🎯]/gu, '').trim();
    const content = lines.slice(1).join('\n').trim();

    if (title && content) {
      sections[title] = content;
    }
  });

  return sections;
};

// Extract evidence patterns
const extractEvidencePatterns = (markdown: string) => {
  const patterns: Array<{ pattern: string; evidence: string; analysis?: string }> = [];
  const patternSection = markdown.match(/##\s+🔍\s+Evidence Patterns\s*\n([\s\S]*?)(?=\n## |$)/);

  if (!patternSection) return patterns;

  const content = patternSection[1];

  // Check if using ### headers format or numbered list format
  if (content.includes('###')) {
    // Format 1: ### Header style
    const patternBlocks = content.split(/###\s+/).filter(Boolean);

    for (const block of patternBlocks) {
      const lines = block.trim().split('\n');
      const pattern = stripMarkdown(lines[0] || '');
      const restOfContent = lines.slice(1).join('\n').trim();

      // Check if there's an "Analysis" subsection (like in single repo analysis)
      const analysisMatch = restOfContent.match(
        /\*\*Analysis\*\*:?\s*\n\n([\s\S]+?)(?=\n\n\*\*|$)/
      );
      const evidenceMatch = restOfContent.match(
        /\*\*Evidence(?:\s+Found)?\*\*:?\s*\n\n([\s\S]+?)(?=\n\n\*\*Analysis|$)/
      );

      let evidence = '';
      let analysis = '';

      if (evidenceMatch && analysisMatch) {
        // Has both Evidence and Analysis sections
        evidence = stripMarkdown(evidenceMatch[1].trim());
        analysis = stripMarkdown(analysisMatch[1].trim());
      } else {
        // Just plain content (current portfolio format)
        evidence = stripMarkdown(restOfContent);
      }

      if (pattern && evidence) {
        patterns.push({ pattern, evidence, analysis: analysis || undefined });
      }
    }
  } else {
    // Format 2: Numbered list style (e.g., "1\nJavaScript Consistency\n\nJavaScript used in...")
    const numberedPattern = /^\d+\s*\n([^\n]+)\s*\n\n([\s\S]*?)(?=\n\d+\s*\n|$)/gm;
    let match;

    while ((match = numberedPattern.exec(content)) !== null) {
      const pattern = stripMarkdown(match[1].trim());
      const evidence = stripMarkdown(match[2].trim());

      if (pattern && evidence) {
        patterns.push({ pattern, evidence });
      }
    }
  }

  return patterns;
};

// Extract quality indicators
const extractQualityIndicators = (markdown: string) => {
  const indicators: Array<{
    indicator: string;
    observation: string;
    scope: string;
    implication: string;
  }> = [];

  const indicatorSection = markdown.match(
    /##\s+📈\s+Quality Indicators[^\n]*\n([\s\S]*?)(?=\n## |$)/
  );

  if (!indicatorSection) return indicators;

  // Split by ### headers
  const indicatorBlocks = indicatorSection[1].split(/###\s+/).filter(Boolean);

  for (const block of indicatorBlocks) {
    const lines = block.trim().split('\n');
    const indicator = stripMarkdown(lines[0] || '');

    const observationMatch = block.match(/\*\*Observation\*\*:\s*([^\n]+)/);
    const scopeMatch = block.match(/\*\*Scope\*\*:\s*([^\n]+)/);
    const implicationMatch = block.match(/\*\*Implication\*\*:\s*([^\n]+)/);

    if (indicator) {
      indicators.push({
        indicator,
        observation: stripMarkdown(observationMatch?.[1] || ''),
        scope: stripMarkdown(scopeMatch?.[1] || ''),
        implication: stripMarkdown(implicationMatch?.[1] || ''),
      });
    }
  }

  return indicators;
};

// Extract interview questions
const extractInterviewQuestions = (markdown: string) => {
  const questions: Array<{
    question: string;
    category?: string;
    context?: string;
    evidence?: string;
    followUps?: string[];
    listeningPoints?: string;
  }> = [];

  const qSection = markdown.match(/##\s+💬\s+Interview Questions\s*\n([\s\S]*?)(?=\n## |$)/);
  if (!qSection) return questions;

  // Split by ### headers
  const qBlocks = qSection[1].split(/###\s+Q\d+:\s+/).filter(Boolean);

  for (const qText of qBlocks) {
    const questionMatch = qText.match(/^([^\n]+)/);
    const categoryMatch = qText.match(/\*\*Category\*\*:\s*`([^`]+)`/);
    const contextMatch = qText.match(/\*\*Context\*\*:\s*([^\n]+)/);
    const evidenceMatch = qText.match(/📍\s+Based on Evidence\*\*:\s*([^\n]+)/);
    const followUpMatch = qText.match(/\*\*Follow-up Questions\*\*:\s*\n([\s\S]*?)(?=\n\n|$)/);
    const listeningMatch = qText.match(/\*\*Key Listening Points\*\*:\s*\n-\s*([^\n]+)/);

    if (questionMatch) {
      const followUps: string[] = [];
      if (followUpMatch) {
        const fuLines = followUpMatch[1].split('\n').filter((l) => l.trim().startsWith('-'));
        followUps.push(...fuLines.map((l) => stripMarkdown(l.replace(/^-\s*/, '').trim())));
      }

      questions.push({
        question: stripMarkdown(questionMatch[1].trim()),
        category: categoryMatch?.[1],
        context: stripMarkdown(contextMatch?.[1] || ''),
        evidence: stripMarkdown(evidenceMatch?.[1]?.trim() || ''),
        followUps,
        listeningPoints: stripMarkdown(listeningMatch?.[1] || ''),
      });
    }
  }

  return questions;
};

// Extract list items with markdown stripping
const extractListItems = (content: string): string[] => {
  const items: string[] = [];
  const lines = content.split('\n');

  for (const line of lines) {
    const trimmed = line.trim();
    // Match numbered lists (1., 2., etc.) or bullet points (-, *)
    if (trimmed.match(/^(\d+\.|[-*])\s+/)) {
      const item = stripMarkdown(
        trimmed
          .replace(/^\d+\.\s*/, '') // Remove "1. "
          .replace(/^[-*]\s*/, '') // Remove "- " or "* "
          .trim()
      );
      if (item && !item.startsWith('--')) {
        items.push(item);
      }
    }
  }

  return items;
};

// Get context icon
const getContextIcon = (context: string) => {
  switch (context.toLowerCase()) {
    case 'startup':
      return <Target className="h-4 w-4" />;
    case 'enterprise':
      return <Code2 className="h-4 w-4" />;
    case 'agency':
      return <MessageCircle className="h-4 w-4" />;
    case 'open_source':
      return <GitBranch className="h-4 w-4" />;
    default:
      return <Target className="h-4 w-4" />;
  }
};

export default function PortfolioAnalysisResultPage() {
  const params = useParams();
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [analysis, setAnalysis] = useState<PortfolioAnalysisData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('summary');
  const [activeStrengthsTab, setActiveStrengthsTab] = useState('positive');
  const [activeInterviewGuideTab, setActiveInterviewGuideTab] = useState('questions');
  const [activeQuestionCategory, setActiveQuestionCategory] = useState('all');
  const [showConfidenceLevel, setShowConfidenceLevel] = useState(false);

  // Handle hash navigation to interview questions
  useEffect(() => {
    if (window.location.hash === '#interview-questions') {
      setActiveTab('interview');
      setTimeout(() => {
        const element = document.getElementById('interview-questions');
        if (element) {
          element.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }, 100);
    }
  }, []);

  useEffect(() => {
    let pollInterval: NodeJS.Timeout | null = null;
    let isMounted = true;

    const fetchAnalysis = async () => {
      // Wait for auth to complete
      if (authLoading) return;

      // Don't fetch if not authenticated
      if (!user) {
        setIsLoading(false);
        return;
      }

      if (!params.id) {
        setError('No analysis ID provided');
        setIsLoading(false);
        return;
      }

      try {
        const response = await api.getPortfolioAnalysis(params.id as string);
        const data = response.data;

        // Check if analysis is still processing
        if (data.status === 'pending' || data.status === 'processing') {
          setAnalysis(data);
          setIsLoading(false); // Show pending/processing UI

          // Start polling every 30 seconds
          if (!pollInterval && isMounted) {
            pollInterval = setInterval(async () => {
              try {
                const pollResponse = await api.getPortfolioAnalysis(params.id as string);
                const pollData = pollResponse.data;

                if (isMounted) {
                  setAnalysis(pollData);
                }

                // Stop polling if completed or failed
                if (
                  pollData.status === 'completed' ||
                  pollData.status === 'failed' ||
                  !pollData.status
                ) {
                  if (pollInterval) {
                    clearInterval(pollInterval);
                    pollInterval = null;
                  }

                  if (pollData.status === 'completed' || !pollData.status) {
                    // Analysis completed successfully - no toast needed, just show results
                  } else if (pollData.status === 'failed') {
                    if (isMounted) {
                      setError('Portfolio analysis failed. Please try again.');
                    }
                  }
                }
              } catch (pollErr) {
                console.error('Polling error:', pollErr);
              }
            }, 30000); // Poll every 30 seconds to reduce server load
          }
        } else {
          // Analysis is completed or failed
          setAnalysis(data);
          setIsLoading(false);
        }
      } catch (err: any) {
        console.error('Failed to fetch portfolio analysis:', err);
        if (err?.response?.status === 404) {
          setError(
            'Analysis not found. It may have been deleted or you may not have access to it.'
          );
        } else if (err?.response?.status >= 500) {
          setError(
            'Server error. Please try again later or contact support if the issue persists.'
          );
        } else {
          setError('Failed to load analysis. Please check your connection and try again.');
        }
        setIsLoading(false);
      }
    };

    fetchAnalysis();

    // Cleanup function
    return () => {
      isMounted = false;
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };
  }, [params.id, user, authLoading]);

  // Set initial question category when analysis is loaded
  useEffect(() => {
    if (analysis && !activeQuestionCategory) {
      const questions = extractInterviewQuestions(analysis.full_analysis);
      if (questions.length > 0) {
        const questionsByCategory = questions.reduce((acc: Record<string, typeof questions>, q) => {
          const cat = q.category || 'other';
          if (!acc[cat]) acc[cat] = [];
          acc[cat].push(q);
          return acc;
        }, {});
        const categories = Object.keys(questionsByCategory);
        if (categories.length > 0) {
          setActiveQuestionCategory(categories[0]);
        }
      }
    }
  }, [analysis, activeQuestionCategory]);

  // Show loading while checking auth or loading data
  if (authLoading || isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0A0A0A]">
        <div className="text-center">
          <div className="mb-4 inline-flex h-16 w-16 items-center justify-center">
            <div className="h-12 w-12 animate-spin rounded-full border-4 border-purple-600 border-t-transparent" />
          </div>
          <p className="text-gray-400">Loading portfolio analysis...</p>
        </div>
      </div>
    );
  }

  // Show beautiful unauthorized component if not authenticated
  if (!user) {
    return <UnauthorizedAccess context="portfolio" />;
  }

  if (error || !analysis) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0A0A0A]">
        <ExiqusCard className="max-w-md p-8 text-center">
          <AlertCircle className="mx-auto mb-4 h-16 w-16 text-red-400" />
          <h2 className="mb-2 font-semibold text-gray-100 text-xl">Failed to Load Analysis</h2>
          <p className="mb-6 text-gray-400">{error || 'Analysis not found'}</p>
          <ExiqusButton onClick={() => router.push('/portfolio-analyses')}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to History
          </ExiqusButton>
        </ExiqusCard>
      </div>
    );
  }

  const sections = parsePortfolioAnalysis(analysis.full_analysis);
  const interviewQuestions = extractInterviewQuestions(analysis.full_analysis);
  // Use structured data from API if available, otherwise fall back to markdown parsing
  const evidencePatterns =
    (analysis as any).evidence_patterns || extractEvidencePatterns(analysis.full_analysis);
  const evolutionPeriods = (analysis as any).evolution_periods || [];
  const qualityIndicators = extractQualityIndicators(analysis.full_analysis);
  const keyObservations = extractListItems(sections['Key Observations (Public Repos Only)'] || '');
  const positiveIndicators = extractListItems(sections['Positive Indicators'] || '');
  const areasToExplore = extractListItems(sections['Areas to Explore'] || '');
  const recommendations = extractListItems(sections['Recommendations'] || '');
  const metadata = analysis.analysis_metadata;

  // Determine if this is AI-enhanced analysis (has interview questions and evidence patterns)
  const hasRealAIInsights = interviewQuestions.length > 0 && evidencePatterns.length > 0;

  const years = metadata.portfolio_span_days ? Math.floor(metadata.portfolio_span_days / 365) : 0;

  return (
    <div className="min-h-screen bg-[#0A0A0A]">
      {/* Animated gradient background - Purple/Blue theme for portfolio */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 h-80 w-80 animate-pulse rounded-full bg-purple-500/20 blur-3xl"></div>
        <div className="absolute -bottom-40 -left-40 h-80 w-80 animate-pulse rounded-full bg-blue-500/20 blur-3xl delay-1000"></div>
        <div className="absolute top-1/2 left-1/2 h-80 w-80 -translate-x-1/2 -translate-y-1/2 animate-pulse rounded-full bg-gradient-to-r from-purple-500/10 to-blue-500/10 blur-3xl delay-500"></div>
      </div>

      <div className="container relative mx-auto max-w-7xl px-4 py-8">
        {/* Back Button */}
        <button
          type="button"
          onClick={() => {
            if (analysis?.github_username) {
              router.push(`/candidate-hub/${analysis.github_username}`);
            } else {
              router.push('/portfolio-analyses');
            }
          }}
          className="group mb-6 flex items-center gap-2 text-gray-400 transition-colors hover:text-purple-400"
        >
          <ArrowLeft className="h-5 w-5 transition-transform group-hover:-translate-x-1" />
          <span className="font-medium">
            {analysis?.github_username
              ? `Back to ${analysis.github_username}'s Hub`
              : 'Back to Portfolio History'}
          </span>
        </button>

        {/* Header Section */}
        <div className="mb-8">
          <div className="mb-4 flex items-center gap-2 text-gray-400 text-sm">
            <User className="h-4 w-4 text-purple-400" />
            <span>Portfolio Analysis</span>
            <ChevronRight className="h-4 w-4" />
            <a
              href={`https://github.com/${analysis.github_username}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-300 transition-colors hover:text-purple-400 hover:underline"
            >
              @{analysis.github_username}
            </a>
          </div>

          <div className="grid gap-8 lg:grid-cols-2">
            {/* Left: Title and Info */}
            <div>
              <h1 className="mb-3 font-bold text-4xl">
                <a
                  href={`https://github.com/${analysis.github_username}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="transition-opacity hover:opacity-80"
                >
                  <GradientText className="bg-gradient-to-r from-purple-400 to-blue-400">
                    @{analysis.github_username}
                  </GradientText>
                </a>
              </h1>
              <p className="mb-4 text-gray-400 text-lg">Developer Portfolio Analysis</p>

              {/* Analysis date and time */}
              <div className="flex items-center gap-4 text-gray-500 text-sm">
                <div className="flex items-center gap-1">
                  <Calendar className="h-4 w-4" />
                  <span>{format(new Date(analysis.created_at), 'PPP')}</span>
                </div>
                <div className="flex items-center gap-1">
                  <Clock className="h-4 w-4" />
                  <span>{formatDuration(analysis.processing_time_seconds)}</span>
                </div>
              </div>

              {/* Context & Role Badges */}
              <div className="mt-4 flex items-center gap-2">
                <div className="flex items-center gap-2 rounded-full border border-purple-500/20 bg-gradient-to-r from-purple-900/20 to-blue-900/20 px-4 py-2">
                  {getContextIcon(analysis.context)}
                  <span className="font-medium text-purple-300 uppercase">
                    {analysis.context} context
                  </span>
                </div>
                <div className="flex items-center gap-2 rounded-full border border-blue-500/20 bg-gradient-to-r from-blue-900/20 to-purple-900/20 px-4 py-2">
                  <Award className="h-4 w-4" />
                  <span className="font-medium text-blue-300 uppercase">{analysis.role} level</span>
                </div>
              </div>
            </div>

            {/* Right: Key Metrics Grid */}
            <div className="grid grid-cols-3 gap-3">
              <div
                className="cursor-pointer rounded-xl border border-purple-500/20 bg-gradient-to-br from-purple-900/20 to-transparent p-4 transition-all hover:border-purple-400/40"
                onClick={() => setActiveTab('observations')}
              >
                <div className="mb-1 font-bold text-3xl text-purple-300">
                  {(analysis as any).key_observations_count || keyObservations.length || 0}
                </div>
                <div className="text-gray-400 text-sm">Key observations</div>
              </div>

              <div
                className="cursor-pointer rounded-xl border border-indigo-500/20 bg-gradient-to-br from-indigo-900/20 to-transparent p-4 transition-all hover:border-indigo-400/40"
                onClick={() => setActiveTab('evidence')}
              >
                <div className="mb-1 font-bold text-3xl text-indigo-300">
                  {(analysis as any).evidence_patterns_count ||
                    evidencePatterns.length + qualityIndicators.length ||
                    0}
                </div>
                <div className="text-gray-400 text-sm">Evidence depth</div>
              </div>

              <div
                className="cursor-pointer rounded-xl border border-emerald-500/20 bg-gradient-to-br from-emerald-900/20 to-transparent p-4 transition-all hover:border-emerald-400/40"
                onClick={() => setActiveTab('interview')}
              >
                <div className="mb-1 font-bold text-3xl text-emerald-300">
                  {(analysis as any).interview_questions_count || interviewQuestions.length || 0}
                </div>
                <div className="text-gray-400 text-sm">Interview questions</div>
              </div>
            </div>
          </div>
        </div>

        {/* Portfolio Statistics Bar */}
        <div className="mb-8 grid grid-cols-2 gap-4 rounded-xl border border-purple-500/20 bg-gradient-to-r from-purple-950/30 to-blue-950/30 p-6 md:grid-cols-5">
          <div className="text-center">
            <div className="font-bold text-2xl text-purple-300">{metadata.repos_analyzed}</div>
            <div className="mt-1 text-gray-400 text-xs">Repos Analyzed</div>
          </div>
          <div className="text-center">
            <div className="font-bold text-2xl text-blue-300">{metadata.total_public_repos}</div>
            <div className="mt-1 text-gray-400 text-xs">Total Public</div>
          </div>
          <div className="text-center">
            <div className="font-bold text-2xl text-indigo-300">{years}y</div>
            <div className="mt-1 text-gray-400 text-xs">Portfolio Span</div>
          </div>
          <div className="text-center">
            <div className="font-bold text-2xl text-violet-300">{evidencePatterns.length}</div>
            <div className="mt-1 text-gray-400 text-xs">Evidence Patterns</div>
          </div>
          <div className="text-center">
            <div className="font-bold text-2xl text-emerald-300">{qualityIndicators.length}</div>
            <div className="mt-1 text-gray-400 text-xs">Quality Signals</div>
          </div>
        </div>

        {/* PR Analysis Card - Show either "Run Analysis" or "View Existing" */}
        {analysis.show_pr_card && (
          <ExiqusCard className="mb-8 border-teal-500/30 bg-gradient-to-r from-teal-900/20 via-cyan-900/10 to-transparent p-6">
            <div className="flex items-start gap-4">
              <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-teal-600 to-cyan-600 shadow-lg shadow-teal-500/20">
                <GitPullRequest className="h-6 w-6 text-white" />
              </div>
              <div className="flex-1">
                {analysis.has_pr_analysis ? (
                  /* Existing PR Analysis - Show link to view it */
                  <>
                    <div className="mb-2 flex items-center gap-2">
                      <h3 className="font-semibold text-lg text-teal-300">PR Analysis Complete</h3>
                      <span className="rounded-full bg-teal-500/20 px-2 py-0.5 font-medium text-teal-300 text-xs">
                        {analysis.pr_count} PRs Analyzed
                      </span>
                    </div>
                    <p className="mb-4 text-gray-300 text-sm">
                      PR analysis reveals collaboration patterns, code review quality, and team
                      communication across {analysis.pr_count} pull requests. View the full analysis
                      for deeper insights.
                    </p>
                    <ExiqusButton
                      onClick={() =>
                        router.push(
                          `/pr-analyses/${analysis.pr_analysis_id}?returnTo=/portfolio-analyses/${analysis.id}`
                        )
                      }
                      className="bg-gradient-to-r from-teal-600 to-cyan-600 hover:from-teal-700 hover:to-cyan-700"
                    >
                      <Eye className="mr-2 h-4 w-4" />
                      View PR Analysis
                    </ExiqusButton>
                  </>
                ) : (
                  /* No PR Analysis - Show recommendation to run it */
                  <>
                    <div className="mb-2 flex items-center gap-2">
                      <h3 className="font-semibold text-lg text-teal-300">Complete the Picture</h3>
                    </div>
                    <p className="mb-4 text-gray-300 text-sm">
                      Portfolio shows {analysis.repos_analyzed} of {analysis.total_repos}{' '}
                      repositories. Run PR Analysis to assess collaboration patterns, code review
                      quality, and team communication skills.
                    </p>
                    <ExiqusButton
                      onClick={() =>
                        router.push(`/pr-analysis?username=${analysis.github_username}`)
                      }
                      className="bg-gradient-to-r from-teal-600 to-cyan-600 hover:from-teal-700 hover:to-cyan-700"
                    >
                      <GitPullRequest className="mr-2 h-4 w-4" />
                      Run PR Analysis
                    </ExiqusButton>
                  </>
                )}
              </div>
            </div>
          </ExiqusCard>
        )}

        {/* Tabs Navigation - 7 tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-4 gap-2 bg-white/[0.03] p-1 lg:grid-cols-8">
            <TabsTrigger
              value="summary"
              className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-purple-600 data-[state=active]:to-blue-600"
            >
              <FileText className="mr-2 h-4 w-4" />
              Summary
            </TabsTrigger>
            <TabsTrigger
              value="evolution"
              className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-indigo-600 data-[state=active]:to-purple-600"
            >
              <TrendingUp className="mr-2 h-4 w-4" />
              Evolution
            </TabsTrigger>
            <TabsTrigger
              value="strengths"
              className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-emerald-600 data-[state=active]:to-green-600"
            >
              <Sparkles className="mr-2 h-4 w-4" />
              Insights
            </TabsTrigger>
            <TabsTrigger
              value="interview"
              className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-blue-600 data-[state=active]:to-purple-600"
            >
              <MessageCircle className="mr-2 h-4 w-4" />
              Interview
            </TabsTrigger>
            <TabsTrigger
              value="evidence"
              className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-indigo-600 data-[state=active]:to-purple-600"
            >
              <Search className="mr-2 h-4 w-4" />
              Evidence
            </TabsTrigger>
            <TabsTrigger
              value="repositories"
              className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-pink-600 data-[state=active]:to-rose-600"
            >
              <GitBranch className="mr-2 h-4 w-4" />
              Repositories
            </TabsTrigger>
            <TabsTrigger
              value="quality"
              className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-purple-600 data-[state=active]:to-violet-600"
            >
              <Shield className="mr-2 h-4 w-4" />
              Signals
            </TabsTrigger>
            <TabsTrigger
              value="observations"
              className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-blue-600 data-[state=active]:to-indigo-600"
            >
              <Eye className="mr-2 h-4 w-4" />
              Observations
            </TabsTrigger>
          </TabsList>

          {/* Tab 1: Decision Guide */}
          <TabsContent value="summary" className="space-y-6">
            {/* Executive Summary Card */}
            <ExiqusCard className="border-purple-500/20 p-8">
              <div className="mb-6 flex items-center gap-3">
                <div className="rounded-xl bg-gradient-to-br from-purple-600 to-violet-600 p-3 shadow-lg">
                  <FileText className="h-6 w-6 text-white" />
                </div>
                <h2 className="bg-gradient-to-r from-purple-300 to-violet-300 bg-clip-text font-bold text-2xl text-transparent">
                  Executive Summary
                </h2>
                {hasRealAIInsights ? (
                  <div className="ml-auto rounded-full bg-gradient-to-r from-purple-600 to-violet-600 px-3 py-1 font-bold text-white text-xs">
                    ✨ AI Enhanced
                  </div>
                ) : (
                  <div className="ml-auto rounded-full bg-gradient-to-r from-orange-600 to-red-600 px-3 py-1 font-bold text-white text-xs">
                    ⚠️ Basic Analysis
                  </div>
                )}
              </div>

              {/* Key Intelligence Section */}
              <div className="mb-6 rounded-xl border border-purple-400/20 bg-gradient-to-r from-purple-950/50 to-violet-950/50 p-6">
                <div className="mb-4 flex items-center gap-3">
                  <Eye className="h-5 w-5 text-purple-400" />
                  <h3 className="font-bold text-lg text-purple-300">Key Intelligence</h3>
                </div>
                <div className="text-gray-200 leading-relaxed">
                  {renderMarkdown(
                    sections['Executive Summary']?.includes('Analysis Confidence Level')
                      ? sections['Executive Summary'].split('Analysis Confidence Level')[0]
                      : sections['Executive Summary'] || ''
                  )}
                </div>
              </div>

              {/* Analysis Confidence Level */}
              {sections['Executive Summary']?.includes('Analysis Confidence Level') && (
                <div className="rounded-xl border border-indigo-500/20 bg-gradient-to-br from-indigo-950/20 to-blue-950/20 p-6">
                  <div
                    className="mb-4 flex cursor-pointer items-center justify-between"
                    onClick={() => setShowConfidenceLevel(!showConfidenceLevel)}
                  >
                    <div className="flex items-center gap-3">
                      <BarChart3 className="h-5 w-5 text-indigo-400" />
                      <h3 className="font-bold text-indigo-300 text-lg">
                        Analysis Confidence Level
                      </h3>
                    </div>
                    <button
                      type="button"
                      className="rounded-lg border border-indigo-500/30 bg-indigo-900/20 px-3 py-1.5 text-indigo-300 text-sm transition-colors hover:bg-indigo-900/40"
                      onClick={(e) => {
                        e.stopPropagation();
                        setShowConfidenceLevel(!showConfidenceLevel);
                      }}
                    >
                      <div className="flex items-center gap-2">
                        <span>{showConfidenceLevel ? 'Hide' : 'Show'} Details</span>
                        <ChevronDown
                          className={`h-4 w-4 transition-transform ${showConfidenceLevel ? 'rotate-180' : ''}`}
                        />
                      </div>
                    </button>
                  </div>
                  {showConfidenceLevel && (
                    <div className="space-y-4">
                      {(() => {
                        const assessmentText =
                          sections['Executive Summary']
                            ?.split('Analysis Confidence Level')[1]
                            ?.trim() || '';

                        // Split by bold headers (e.g., **Portfolio Span:**)
                        const assessmentSections = assessmentText.split(/\*\*([^*]+):\*\*/g);
                        const items: React.ReactElement[] = [];

                        for (let i = 1; i < assessmentSections.length; i += 2) {
                          const heading = assessmentSections[i];
                          const content = assessmentSections[i + 1]?.trim() || '';

                          if (heading && content) {
                            // Special handling for "Next Steps" - render as list
                            if (heading === 'Next Steps') {
                              const steps = content
                                .split('\n')
                                .map((line) => line.trim())
                                .filter((line) => line && line.startsWith('-'))
                                .map((line) => line.replace(/^-\s*/, ''));

                              items.push(
                                <div
                                  key={heading}
                                  className="rounded-lg border border-amber-500/20 bg-amber-950/20 p-4"
                                >
                                  <h4 className="mb-3 font-semibold text-amber-400 text-sm uppercase tracking-wide">
                                    {heading}
                                  </h4>
                                  <ul className="space-y-2">
                                    {steps.map((step, idx) => (
                                      <li key={idx} className="flex gap-2 text-gray-300 text-sm">
                                        <span className="mt-1 text-amber-400">•</span>
                                        <span className="flex-1">{step}</span>
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              );
                            } else {
                              // Regular section with icon
                              const icon = heading.includes('Span')
                                ? '📅'
                                : heading.includes('Gap')
                                  ? '⚠️'
                                  : heading.includes('Shows') && !heading.includes('NOT')
                                    ? '✓'
                                    : heading.includes('NOT Show')
                                      ? '✗'
                                      : '📋';

                              items.push(
                                <div
                                  key={heading}
                                  className="rounded-lg border border-gray-700/50 bg-gray-900/30 p-4"
                                >
                                  <div className="mb-2 flex items-start gap-2">
                                    <span className="text-lg">{icon}</span>
                                    <h4 className="font-semibold text-gray-200 text-sm">
                                      {heading}
                                    </h4>
                                  </div>
                                  <p className="text-gray-400 text-sm leading-relaxed">{content}</p>
                                </div>
                              );
                            }
                          }
                        }

                        // If we found structured sections, return them as cards
                        if (items.length > 0) {
                          return items;
                        }

                        // FALLBACK: For old format without structured headers, split by paragraphs
                        const paragraphs = assessmentText
                          .split('\n\n')
                          .map((p) => p.trim())
                          .filter((p) => p.length > 0);

                        if (paragraphs.length > 1) {
                          return paragraphs.map((paragraph, idx) => {
                            // Check if paragraph starts with a recognizable heading pattern
                            const headingMatch = paragraph.match(/^([^:]+):/);
                            const heading = headingMatch ? headingMatch[1] : null;

                            // Determine icon based on content
                            const icon =
                              paragraph.includes('Scope') ||
                              paragraph.includes('Timeline') ||
                              paragraph.includes('Span')
                                ? '📅'
                                : paragraph.includes('Limitation') || paragraph.includes('Gap')
                                  ? '⚠️'
                                  : paragraph.includes('Shows:') && !paragraph.includes('NOT Show')
                                    ? '✓'
                                    : paragraph.includes('NOT Show') ||
                                        paragraph.includes('Does NOT')
                                      ? '✗'
                                      : paragraph.includes('Recommended') ||
                                          paragraph.includes('Next Steps')
                                        ? '📋'
                                        : '📄';

                            // If it looks like a list of recommendations, format as bullets
                            if (
                              paragraph.includes('Recommended Next Steps') ||
                              paragraph.match(/^\d+\./m)
                            ) {
                              const lines = paragraph.split('\n').filter((l) => l.trim());
                              const listItems = lines.slice(1).filter((l) => l.match(/^\d+\./));

                              return (
                                <div
                                  key={idx}
                                  className="rounded-lg border border-amber-500/20 bg-amber-950/20 p-4"
                                >
                                  <h4 className="mb-3 font-semibold text-amber-400 text-sm uppercase tracking-wide">
                                    {heading || 'Recommended Next Steps'}
                                  </h4>
                                  <ul className="space-y-2">
                                    {listItems.map((item, itemIdx) => (
                                      <li
                                        key={itemIdx}
                                        className="flex gap-2 text-gray-300 text-sm"
                                      >
                                        <span className="mt-1 text-amber-400">•</span>
                                        <span className="flex-1">
                                          {item.replace(/^\d+\.\s*/, '')}
                                        </span>
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              );
                            }

                            return (
                              <div
                                key={idx}
                                className="rounded-lg border border-gray-700/50 bg-gray-900/30 p-4"
                              >
                                <div className="mb-2 flex items-start gap-2">
                                  <span className="text-lg">{icon}</span>
                                  {heading && (
                                    <h4 className="font-semibold text-gray-200 text-sm">
                                      {heading}
                                    </h4>
                                  )}
                                </div>
                                <p className="text-gray-400 text-sm leading-relaxed">
                                  {heading ? paragraph.replace(/^[^:]+:\s*/, '') : paragraph}
                                </p>
                              </div>
                            );
                          });
                        }

                        // Final fallback: render as-is
                        return (
                          <div className="text-gray-300 text-sm leading-relaxed">
                            {renderMarkdown(assessmentText)}
                          </div>
                        );
                      })()}
                    </div>
                  )}
                </div>
              )}
            </ExiqusCard>

            {/* Intelligence Assessment Cards - Two Column Grid */}
            <div className="grid gap-8 lg:grid-cols-2">
              {/* Key Intelligence Card (Actionable) */}
              <div className="relative overflow-hidden rounded-2xl border border-purple-500/30 bg-gradient-to-br from-purple-900/40 via-violet-900/30 to-indigo-900/40 backdrop-blur-sm">
                <div className="absolute inset-0 animate-pulse bg-gradient-to-r from-purple-600/10 via-transparent to-indigo-600/10"></div>

                <div className="relative p-8">
                  <div className="mb-6 flex items-center gap-3">
                    <div className="rounded-xl bg-gradient-to-br from-purple-600 to-violet-600 p-3 shadow-lg">
                      <Brain className="h-6 w-6 text-white" />
                    </div>
                    <h2 className="bg-gradient-to-r from-purple-300 to-violet-300 bg-clip-text font-bold text-2xl text-transparent">
                      Key Intelligence
                    </h2>
                  </div>

                  {/* Intelligence Assessment */}
                  <div className="mb-6 rounded-xl border border-blue-400/30 bg-gradient-to-r from-blue-950/50 to-indigo-950/50 p-6">
                    <div className="mb-3 flex items-center gap-3">
                      <Eye className="h-6 w-6 text-blue-400" />
                      <span className="font-bold text-blue-300 text-xl">ACTIONABLE INSIGHTS</span>
                    </div>
                    <p className="text-gray-200 leading-relaxed">
                      {evidencePatterns.length > 0 && keyObservations.length > 0
                        ? 'Portfolio demonstrates consistent technical patterns requiring targeted validation through interview discussion.'
                        : 'Review evidence patterns for actionable intelligence and context compatibility.'}
                    </p>
                  </div>

                  {/* Key Context Fit */}
                  <div className="rounded-lg border border-violet-400/30 bg-gradient-to-r from-violet-950/40 to-purple-950/40 p-4">
                    <h4 className="mb-2 font-medium text-violet-300">
                      {analysis.context.toUpperCase()} Context Intelligence
                    </h4>
                    <p className="text-gray-300 text-sm">
                      {positiveIndicators[0] ||
                        'Review evidence patterns for context compatibility intelligence.'}
                    </p>
                  </div>
                </div>
              </div>

              {/* Analysis Summary Card */}
              <div className="relative overflow-hidden rounded-2xl border border-purple-500/30 bg-gradient-to-br from-purple-900/40 via-violet-900/30 to-indigo-900/40 backdrop-blur-sm">
                <div className="absolute inset-0 animate-pulse bg-gradient-to-r from-purple-600/10 via-transparent to-indigo-600/10"></div>

                <div className="relative p-8">
                  <div className="mb-6 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="rounded-xl bg-gradient-to-br from-purple-600 to-violet-600 p-3 shadow-lg">
                        <FileText className="h-6 w-6 text-white" />
                      </div>
                      <h3 className="bg-gradient-to-r from-purple-300 to-violet-300 bg-clip-text font-bold text-transparent text-xl">
                        Analysis Summary
                      </h3>
                    </div>

                    {/* AI Status Badge */}
                    {hasRealAIInsights ? (
                      <div className="rounded-full bg-gradient-to-r from-purple-600 to-violet-600 px-3 py-1 font-bold text-white text-xs">
                        ✨ AI Enhanced
                      </div>
                    ) : (
                      <div className="rounded-full bg-gradient-to-r from-orange-600 to-red-600 px-3 py-1 font-bold text-white text-xs">
                        ⚠️ Basic Analysis
                      </div>
                    )}
                  </div>

                  <div className="space-y-4 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-400">Repos Analyzed:</span>
                      <span className="font-medium text-purple-300">{metadata.repos_analyzed}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Portfolio Span:</span>
                      <span className="font-medium text-violet-300">
                        {metadata.portfolio_span_days
                          ? years > 0
                            ? `${years} year${years !== 1 ? 's' : ''}`
                            : `${Math.floor(metadata.portfolio_span_days / 30)} months`
                          : 'N/A'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Technologies:</span>
                      <span className="font-medium text-indigo-300">
                        {evidencePatterns.length} patterns identified
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Evidence Confidence:</span>
                      <span
                        className={`font-medium capitalize ${
                          (analysis.data_quality || 'moderate') === 'high'
                            ? 'text-cyan-300'
                            : (analysis.data_quality || 'moderate') === 'moderate'
                              ? 'text-purple-300'
                              : 'text-gray-400'
                        }`}
                      >
                        {analysis.data_quality || 'moderate'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Top Strengths Preview */}
            {positiveIndicators.length > 0 && (
              <ExiqusCard className="border-emerald-500/20 p-8">
                <div className="mb-6 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="rounded-xl bg-gradient-to-br from-emerald-600 to-teal-600 p-3 shadow-lg">
                      <Sparkles className="h-6 w-6 text-white" />
                    </div>
                    <div>
                      <h3 className="font-bold text-emerald-300 text-xl">
                        Top Strengths ({Math.min(positiveIndicators.length, 3)})
                      </h3>
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  {positiveIndicators.slice(0, 3).map((strength, idx) => (
                    <div
                      key={idx}
                      className="flex gap-4 rounded-lg border border-emerald-400/20 bg-gradient-to-r from-emerald-950/30 to-teal-950/20 p-4"
                    >
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-emerald-600 to-teal-600 font-bold text-sm text-white">
                        {idx + 1}
                      </div>
                      <p className="text-gray-200 leading-relaxed">{strength}</p>
                    </div>
                  ))}
                </div>

                {positiveIndicators.length > 3 && (
                  <button
                    type="button"
                    onClick={() => setActiveTab('strengths')}
                    className="mt-4 w-full rounded-lg border border-emerald-400/30 bg-gradient-to-r from-emerald-900/20 to-teal-900/20 px-4 py-2 font-medium text-emerald-300 text-sm transition-all hover:border-emerald-400/50 hover:from-emerald-900/30 hover:to-teal-900/30"
                  >
                    View all {positiveIndicators.length} strengths →
                  </button>
                )}
              </ExiqusCard>
            )}

            {/* Areas Requiring Investigation Preview */}
            {areasToExplore.length > 0 && (
              <ExiqusCard className="border-amber-500/20 p-8">
                <div className="mb-6 flex items-center gap-3">
                  <div className="rounded-xl bg-gradient-to-br from-amber-600 to-orange-600 p-3 shadow-lg">
                    <AlertCircle className="h-6 w-6 text-white" />
                  </div>
                  <div>
                    <h3 className="font-bold text-amber-300 text-xl">
                      Areas Requiring Investigation ({Math.min(areasToExplore.length, 2)})
                    </h3>
                  </div>
                </div>

                <div className="space-y-4">
                  {areasToExplore.slice(0, 2).map((area, idx) => (
                    <div
                      key={idx}
                      className="flex gap-4 rounded-lg border border-amber-400/20 bg-gradient-to-r from-amber-950/30 to-orange-950/20 p-4"
                    >
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-amber-600 to-orange-600 font-bold text-sm text-white">
                        {idx + 1}
                      </div>
                      <p className="text-gray-200 leading-relaxed">{area}</p>
                    </div>
                  ))}
                </div>

                {areasToExplore.length > 2 && (
                  <button
                    type="button"
                    onClick={() => setActiveTab('interview')}
                    className="mt-4 w-full rounded-lg border border-amber-400/30 bg-gradient-to-r from-amber-900/20 to-orange-900/20 px-4 py-2 font-medium text-amber-300 text-sm transition-all hover:border-amber-400/50 hover:from-amber-900/30 hover:to-orange-900/30"
                  >
                    View all investigation areas in Interview Guide →
                  </button>
                )}
              </ExiqusCard>
            )}
          </TabsContent>

          {/* Tab 2: Portfolio Evolution */}
          <TabsContent value="evolution" className="space-y-6">
            <ExiqusCard className="border-indigo-500/20 p-8">
              <div className="mb-6 flex items-center gap-3">
                <div className="rounded-xl bg-gradient-to-br from-indigo-600 to-purple-600 p-3 shadow-lg">
                  <TrendingUp className="h-6 w-6 text-white" />
                </div>
                <h2 className="bg-gradient-to-r from-indigo-300 to-purple-300 bg-clip-text font-bold text-2xl text-transparent">
                  Portfolio Evolution Over Time
                </h2>
              </div>

              {evolutionPeriods && evolutionPeriods.length > 0 ? (
                evolutionPeriods.length >= 3 ? (
                  // Nested tabs for portfolios with 3+ time periods
                  <Tabs defaultValue="period-0" className="w-full">
                    <TabsList className="mb-6 flex h-auto flex-wrap gap-2 bg-transparent p-0">
                      {evolutionPeriods.map((period: any, index: number) => {
                        // Extract just the year range (e.g., "2009-2010" from "2009-2010: Systems Programming Foundation")
                        const yearRange = period.period.split(':')[0].trim();
                        return (
                          <TabsTrigger
                            key={index}
                            value={`period-${index}`}
                            className="rounded-lg border border-indigo-500/30 bg-indigo-950/40 px-4 py-2.5 font-medium text-indigo-200 text-sm transition-all hover:border-indigo-400/50 hover:bg-indigo-900/50 data-[state=active]:border-indigo-400 data-[state=active]:bg-gradient-to-r data-[state=active]:from-indigo-600 data-[state=active]:to-purple-600 data-[state=active]:text-white data-[state=active]:shadow-lg"
                          >
                            {yearRange}
                          </TabsTrigger>
                        );
                      })}
                    </TabsList>
                    {evolutionPeriods.map((period: any, index: number) => (
                      <TabsContent
                        key={index}
                        value={`period-${index}`}
                        className="mt-0 data-[state=inactive]:hidden"
                      >
                        <div className="group relative overflow-hidden rounded-2xl border border-indigo-400/20 bg-gradient-to-br from-indigo-950/40 via-purple-950/30 to-indigo-950/40 p-8 transition-all hover:border-indigo-400/40 hover:shadow-indigo-500/10 hover:shadow-lg">
                          {/* Period Header */}
                          <div className="mb-6 flex items-center gap-4">
                            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 font-bold text-white text-xl shadow-lg">
                              {index + 1}
                            </div>
                            <div>
                              <h3 className="font-bold text-2xl text-indigo-300">
                                {period.period}
                              </h3>
                              {period.note && (
                                <p className="mt-1 text-gray-400 text-xs italic">{period.note}</p>
                              )}
                            </div>
                          </div>

                          {/* Metrics Grid */}
                          <div className="grid gap-6 md:grid-cols-2">
                            {/* Left Column */}
                            <div className="space-y-4">
                              {period.public_repos_created !== undefined && (
                                <div className="rounded-lg bg-indigo-900/30 p-4">
                                  <div className="mb-2 flex items-center gap-2">
                                    <GitBranch className="h-4 w-4 text-indigo-400" />
                                    <span className="font-medium text-indigo-300 text-sm">
                                      Repositories
                                    </span>
                                  </div>
                                  <div className="font-bold text-2xl text-white">
                                    {period.public_repos_created}
                                    <span className="ml-2 font-normal text-gray-400 text-sm">
                                      repos
                                    </span>
                                  </div>
                                </div>
                              )}

                              {period.technologies_observed &&
                                period.technologies_observed.length > 0 && (
                                  <div className="rounded-lg bg-purple-900/30 p-4">
                                    <div className="mb-2 flex items-center gap-2">
                                      <Code2 className="h-4 w-4 text-purple-400" />
                                      <span className="font-medium text-purple-300 text-sm">
                                        Technologies
                                      </span>
                                    </div>
                                    <div className="flex flex-wrap gap-2">
                                      {(Array.isArray(period.technologies_observed)
                                        ? period.technologies_observed
                                        : [period.technologies_observed]
                                      ).map((tech: string, i: number) => (
                                        <span
                                          key={i}
                                          className="rounded-full bg-purple-500/20 px-3 py-1 font-medium text-purple-200 text-xs"
                                        >
                                          {tech}
                                        </span>
                                      ))}
                                    </div>
                                  </div>
                                )}

                              {period.domain_focus && (
                                <div className="rounded-lg bg-blue-900/30 p-4">
                                  <div className="mb-2 flex items-center gap-2">
                                    <Target className="h-4 w-4 text-blue-400" />
                                    <span className="font-medium text-blue-300 text-sm">
                                      Domain
                                    </span>
                                  </div>
                                  <div className="font-medium text-base text-white">
                                    {period.domain_focus}
                                  </div>
                                </div>
                              )}
                            </div>

                            {/* Right Column */}
                            <div className="space-y-4">
                              {period.total_commits && (
                                <div className="rounded-lg bg-emerald-900/30 p-4">
                                  <div className="mb-2 flex items-center gap-2">
                                    <GitBranch className="h-4 w-4 text-emerald-400" />
                                    <span className="font-medium text-emerald-300 text-sm">
                                      Commits
                                    </span>
                                  </div>
                                  <div className="font-bold text-2xl text-white">
                                    {period.total_commits}
                                  </div>
                                </div>
                              )}

                              {period.largest_project && (
                                <div className="rounded-lg bg-violet-900/30 p-4">
                                  <div className="mb-2 flex items-center gap-2">
                                    <Award className="h-4 w-4 text-violet-400" />
                                    <span className="font-medium text-sm text-violet-300">
                                      Largest Project
                                    </span>
                                  </div>
                                  <div className="font-medium text-base text-white">
                                    {period.largest_project}
                                  </div>
                                </div>
                              )}

                              {period.code_quality && (
                                <div className="rounded-lg bg-amber-900/30 p-4">
                                  <div className="mb-2 flex items-center gap-2">
                                    <Shield className="h-4 w-4 text-amber-400" />
                                    <span className="font-medium text-amber-300 text-sm">
                                      Code Quality
                                    </span>
                                  </div>
                                  <div className="text-gray-300 text-sm">{period.code_quality}</div>
                                </div>
                              )}

                              {period.community_recognition && (
                                <div className="rounded-lg bg-pink-900/30 p-4">
                                  <div className="mb-2 flex items-center gap-2">
                                    <Sparkles className="h-4 w-4 text-pink-400" />
                                    <span className="font-medium text-pink-300 text-sm">
                                      Community
                                    </span>
                                  </div>
                                  <div className="text-gray-300 text-sm">
                                    {period.community_recognition}
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      </TabsContent>
                    ))}
                  </Tabs>
                ) : (
                  // Original vertical list for portfolios with ≤3 time periods
                  <div className="space-y-8">
                    {evolutionPeriods.map((period: any, index: number) => (
                      <div
                        key={index}
                        className="group relative overflow-hidden rounded-2xl border border-indigo-400/20 bg-gradient-to-br from-indigo-950/40 via-purple-950/30 to-indigo-950/40 p-8 transition-all hover:border-indigo-400/40 hover:shadow-indigo-500/10 hover:shadow-lg"
                      >
                        {/* Timeline connector */}
                        {index < evolutionPeriods.length - 1 && (
                          <div className="absolute top-full left-[44px] h-8 w-0.5 bg-gradient-to-b from-indigo-400/40 to-transparent"></div>
                        )}

                        {/* Period Header */}
                        <div className="mb-6 flex items-center gap-4">
                          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 font-bold text-white text-xl shadow-lg">
                            {index + 1}
                          </div>
                          <div>
                            <h3 className="font-bold text-2xl text-indigo-300">{period.period}</h3>
                            {period.note && (
                              <p className="mt-1 text-gray-400 text-xs italic">{period.note}</p>
                            )}
                          </div>
                        </div>

                        {/* Metrics Grid */}
                        <div className="grid gap-6 md:grid-cols-2">
                          {/* Left Column */}
                          <div className="space-y-4">
                            {period.public_repos_created !== undefined && (
                              <div className="rounded-lg bg-indigo-900/30 p-4">
                                <div className="mb-2 flex items-center gap-2">
                                  <GitBranch className="h-4 w-4 text-indigo-400" />
                                  <span className="font-medium text-indigo-300 text-sm">
                                    Repositories
                                  </span>
                                </div>
                                <div className="font-bold text-2xl text-white">
                                  {period.public_repos_created}
                                  <span className="ml-2 font-normal text-gray-400 text-sm">
                                    repos
                                  </span>
                                </div>
                              </div>
                            )}

                            {period.technologies_observed &&
                              period.technologies_observed.length > 0 && (
                                <div className="rounded-lg bg-purple-900/30 p-4">
                                  <div className="mb-2 flex items-center gap-2">
                                    <Code2 className="h-4 w-4 text-purple-400" />
                                    <span className="font-medium text-purple-300 text-sm">
                                      Technologies
                                    </span>
                                  </div>
                                  <div className="flex flex-wrap gap-2">
                                    {(Array.isArray(period.technologies_observed)
                                      ? period.technologies_observed
                                      : [period.technologies_observed]
                                    ).map((tech: string, i: number) => (
                                      <span
                                        key={i}
                                        className="rounded-full bg-purple-500/20 px-3 py-1 font-medium text-purple-200 text-xs"
                                      >
                                        {tech}
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              )}

                            {period.domain_focus && (
                              <div className="rounded-lg bg-blue-900/30 p-4">
                                <div className="mb-2 flex items-center gap-2">
                                  <Target className="h-4 w-4 text-blue-400" />
                                  <span className="font-medium text-blue-300 text-sm">Domain</span>
                                </div>
                                <div className="font-medium text-base text-white">
                                  {period.domain_focus}
                                </div>
                              </div>
                            )}
                          </div>

                          {/* Right Column */}
                          <div className="space-y-4">
                            {period.total_commits && (
                              <div className="rounded-lg bg-emerald-900/30 p-4">
                                <div className="mb-2 flex items-center gap-2">
                                  <GitBranch className="h-4 w-4 text-emerald-400" />
                                  <span className="font-medium text-emerald-300 text-sm">
                                    Commits
                                  </span>
                                </div>
                                <div className="font-bold text-2xl text-white">
                                  {period.total_commits}
                                </div>
                              </div>
                            )}

                            {period.largest_project && (
                              <div className="rounded-lg bg-violet-900/30 p-4">
                                <div className="mb-2 flex items-center gap-2">
                                  <Award className="h-4 w-4 text-violet-400" />
                                  <span className="font-medium text-sm text-violet-300">
                                    Largest Project
                                  </span>
                                </div>
                                <div className="font-medium text-base text-white">
                                  {period.largest_project}
                                </div>
                              </div>
                            )}

                            {period.code_quality && (
                              <div className="rounded-lg bg-amber-900/30 p-4">
                                <div className="mb-2 flex items-center gap-2">
                                  <Shield className="h-4 w-4 text-amber-400" />
                                  <span className="font-medium text-amber-300 text-sm">
                                    Code Quality
                                  </span>
                                </div>
                                <div className="text-gray-300 text-sm">{period.code_quality}</div>
                              </div>
                            )}

                            {period.community_recognition && (
                              <div className="rounded-lg bg-pink-900/30 p-4">
                                <div className="mb-2 flex items-center gap-2">
                                  <Sparkles className="h-4 w-4 text-pink-400" />
                                  <span className="font-medium text-pink-300 text-sm">
                                    Community
                                  </span>
                                </div>
                                <div className="text-gray-300 text-sm">
                                  {period.community_recognition}
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )
              ) : (
                <div className="rounded-xl border border-gray-700/20 bg-gray-900/20 p-8 text-center">
                  <p className="text-gray-400">No evolution data available for this portfolio.</p>
                </div>
              )}
            </ExiqusCard>
          </TabsContent>

          {/* Tab 3: Key Observations */}
          <TabsContent value="observations" className="space-y-6">
            <ExiqusCard className="border-blue-500/20 p-8">
              <div className="mb-6 flex items-center gap-3">
                <div className="rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 p-3 shadow-lg">
                  <Eye className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h2 className="font-semibold text-2xl text-gray-100">
                    Key Observations ({keyObservations.length})
                  </h2>
                  <p className="text-gray-400 text-sm">Based on public repository analysis</p>
                </div>
              </div>
              <div className="space-y-3">
                {keyObservations.map((obs, idx) => (
                  <div
                    key={idx}
                    className="flex items-start gap-3 rounded-lg border border-blue-500/20 bg-gradient-to-r from-blue-900/20 to-indigo-900/10 p-4"
                  >
                    <div className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-blue-600 to-indigo-600 font-bold text-white text-xs">
                      {idx + 1}
                    </div>
                    <p className="text-gray-300 text-sm leading-relaxed">{obs}</p>
                  </div>
                ))}
              </div>
            </ExiqusCard>
          </TabsContent>

          {/* Tab 3: Evidence Patterns */}
          <TabsContent value="evidence" className="space-y-6">
            <ExiqusCard className="border-indigo-500/20 p-8">
              <div className="mb-6 flex items-center gap-3">
                <div className="rounded-xl bg-gradient-to-br from-indigo-600 to-purple-600 p-3 shadow-lg">
                  <Search className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h2 className="font-semibold text-2xl text-gray-100">
                    Evidence Patterns ({evidencePatterns.length})
                  </h2>
                  <p className="text-gray-400 text-sm">Observable patterns in public work</p>
                </div>
              </div>
              <div className="space-y-5">
                {evidencePatterns.map((pattern: any, idx: number) => {
                  // Helper to convert KB to MB in any text
                  const convertKBtoMB = (text: string): string => {
                    // Check if this text has multiple KB values (comparison scenario)
                    const kbMatches = text.match(/([\d,]+)\s*KB/gi);
                    const hasMultipleKB = kbMatches && kbMatches.length > 1;

                    // Check if any KB value is >= 1024 (requires MB conversion)
                    const hasLargeKB = kbMatches?.some((match) => {
                      const kb = parseInt(match.replace(/[^\d]/g, ''));
                      return kb >= 1024;
                    });

                    // If comparing sizes and one is large, convert ALL to MB for consistency
                    const convertAllToMB = hasMultipleKB && hasLargeKB;

                    return text.replace(/([\d,]+)\s*KB/gi, (match, num) => {
                      const kb = parseInt(num.replace(/,/g, ''));
                      if (kb >= 1024 || convertAllToMB) {
                        const mb = (kb / 1024).toFixed(kb < 1024 ? 2 : 1);
                        return `${mb}MB`;
                      }
                      return match;
                    });
                  };

                  // Parse evidence text to extract key data points
                  // First, convert all KB to MB in the entire text
                  const evidence = convertKBtoMB(pattern.evidence);

                  // Extract repo mentions with patterns like 'repo_name' or 'repo_name' (details)
                  const repos: Array<{ name: string; details: string }> = [];

                  // Pattern 1: 'repo_name' (details) - repo with parentheses
                  const repoWithDetailsPattern = /'([^']+)'\s*\(([^)]+)\)/g;
                  let match;
                  while ((match = repoWithDetailsPattern.exec(evidence)) !== null) {
                    repos.push({ name: match[1], details: match[2] });
                  }

                  // Pattern 2: 'repo_name' without parentheses - only extract if not already in repos list
                  const repoOnlyPattern = /'([^']+)'/g;
                  const repoNames = new Set(repos.map((r) => r.name));
                  let match2;
                  while ((match2 = repoOnlyPattern.exec(evidence)) !== null) {
                    const repoName = match2[1];
                    if (!repoNames.has(repoName)) {
                      // Try to extract any details that might be nearby (e.g., "from 'repo' to 'repo2'")
                      repos.push({ name: repoName, details: 'mentioned' });
                      repoNames.add(repoName);
                    }
                  }

                  // Extract numbers and percentages for highlighting
                  const highlightNumbers = (text: string) => {
                    // Split by repo mentions first to avoid breaking them
                    const parts = text.split(/('[\w-]+'\s*\([^)]+\))/g);

                    return parts.map((part, i) => {
                      if (part.match(/^'[\w-]+'\s*\([^)]+\)$/)) {
                        // This is a repo mention - don't modify
                        return <span key={i}>{part}</span>;
                      }

                      // Highlight numbers, dates, and percentages in remaining text
                      // Updated regex to handle numbers with commas and MB (already converted from KB)
                      const segments = part.split(
                        /(\d+\/\d+|\d+%|[\d.]+\s*MB|[\d,]+\s*KB|[\d,]+\s*commits|\d{4}-\d{2}-\d{2}|\d{4}|[\d,]+\s*stars?|[\d,]+\s*forks?|[\d,]+\s*repos?|[\d,]+\s*days?)/gi
                      );

                      return segments.map((seg, j) => {
                        if (
                          seg.match(
                            /(\d+\/\d+|\d+%|[\d.]+\s*MB|[\d,]+\s*KB|[\d,]+\s*commits|\d{4}-\d{2}-\d{2}|\d{4}|[\d,]+\s*stars?|[\d,]+\s*forks?|[\d,]+\s*repos?|[\d,]+\s*days?)/i
                          )
                        ) {
                          return (
                            <span key={`${i}-${j}`} className="font-semibold text-indigo-300">
                              {seg}
                            </span>
                          );
                        }
                        return <span key={`${i}-${j}`}>{seg}</span>;
                      });
                    });
                  };

                  return (
                    <div
                      key={idx}
                      className="group relative overflow-hidden rounded-xl border border-indigo-400/20 bg-gradient-to-br from-indigo-900/30 via-purple-900/20 to-violet-900/10 p-6 transition-all hover:border-indigo-400/40 hover:shadow-indigo-500/10 hover:shadow-lg"
                    >
                      {/* Subtle background accent */}
                      <div className="absolute top-0 right-0 h-24 w-24 rounded-full bg-gradient-to-br from-indigo-500/10 to-transparent blur-2xl"></div>

                      <div className="relative">
                        {/* Header with number badge and title */}
                        <div className="mb-4 flex items-start gap-4">
                          <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-600 to-purple-600 font-bold text-base text-white shadow-indigo-500/30 shadow-lg">
                            {idx + 1}
                          </div>
                          <div className="flex-1">
                            <h3 className="mb-1 font-bold text-indigo-200 text-xl transition-colors group-hover:text-indigo-100">
                              {pattern.pattern}
                            </h3>
                            <div className="h-0.5 w-12 rounded-full bg-gradient-to-r from-indigo-500 to-purple-500"></div>
                          </div>
                        </div>

                        {/* Evidence content with highlighted data points */}
                        <div className="ml-14 space-y-3">
                          {/* Referenced Repositories - TOP for quick context */}
                          {repos.length > 0 && (
                            <div className="rounded-xl border-2 border-cyan-400/40 bg-gradient-to-br from-cyan-950/40 via-blue-950/30 to-indigo-950/20 p-4 shadow-cyan-500/10 shadow-lg">
                              <div className="mb-3 flex items-center gap-2">
                                <svg
                                  className="h-4 w-4 text-cyan-400"
                                  fill="none"
                                  viewBox="0 0 24 24"
                                  stroke="currentColor"
                                  strokeWidth={2.5}
                                >
                                  <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    d="M5 19a2 2 0 01-2-2V7a2 2 0 012-2h4l2 2h4a2 2 0 012 2v1M5 19h14a2 2 0 002-2v-5a2 2 0 00-2-2H9a2 2 0 00-2 2v5a2 2 0 01-2 2z"
                                  />
                                </svg>
                                <span className="font-bold text-cyan-300 text-sm uppercase tracking-wide">
                                  Referenced Repositories ({repos.length})
                                </span>
                              </div>
                              <div className="flex flex-wrap gap-2">
                                {repos.map((repo, ridx) => (
                                  <div
                                    key={ridx}
                                    className="inline-flex items-center gap-2 rounded-lg border border-cyan-300/50 bg-gradient-to-br from-cyan-900/60 to-blue-900/40 px-3 py-2 font-medium text-sm transition-all hover:border-cyan-300/70 hover:shadow-cyan-500/20 hover:shadow-md"
                                  >
                                    <span className="font-bold font-mono text-cyan-200">
                                      {repo.name}
                                    </span>
                                    <span className="text-cyan-500/60">•</span>
                                    <span className="text-cyan-100/80">{repo.details}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Evidence Found - Factual data */}
                          <div className="rounded-lg border border-emerald-400/30 bg-gradient-to-r from-emerald-950/40 to-teal-950/30 py-3.5 pr-4 pl-4">
                            <div className="mb-2 flex items-center gap-2">
                              <svg
                                className="h-4 w-4 text-emerald-400"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                                strokeWidth={2}
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                                />
                              </svg>
                              <span className="font-bold text-emerald-400 text-xs uppercase tracking-wide">
                                Evidence Found
                              </span>
                            </div>
                            <p className="text-[15px] text-gray-200 leading-relaxed">
                              {highlightNumbers(evidence)}
                            </p>
                          </div>

                          {/* Analysis section - AI-generated insight (bottom, most prominent) */}
                          {pattern.analysis && (
                            <div className="rounded-xl border-2 border-amber-400/40 bg-gradient-to-br from-amber-950/40 via-orange-950/30 to-yellow-950/20 p-4 shadow-amber-500/10 shadow-lg">
                              <div className="mb-3 flex items-center gap-2">
                                <svg
                                  className="h-5 w-5 text-amber-400"
                                  fill="none"
                                  viewBox="0 0 24 24"
                                  stroke="currentColor"
                                  strokeWidth={2.5}
                                >
                                  <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                                  />
                                </svg>
                                <span className="font-bold text-amber-300 text-sm uppercase tracking-wide">
                                  Analysis
                                </span>
                              </div>
                              <p className="font-light text-[15px] text-gray-100 leading-relaxed">
                                {pattern.analysis}
                              </p>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </ExiqusCard>
          </TabsContent>

          {/* Tab 4: Quality Indicators */}
          <TabsContent value="quality" className="space-y-6">
            <ExiqusCard className="border-purple-500/20 p-8">
              <div className="mb-6 flex items-center gap-3">
                <div className="rounded-xl bg-gradient-to-br from-purple-600 to-violet-600 p-3 shadow-lg">
                  <Shield className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h2 className="font-semibold text-2xl text-gray-100">
                    Quality Indicators ({qualityIndicators.length})
                  </h2>
                  <p className="text-gray-400 text-sm">Code quality and professional signals</p>
                </div>
              </div>
              <div className="space-y-5">
                {qualityIndicators.map((indicator, idx) => (
                  <div
                    key={idx}
                    className="group relative overflow-hidden rounded-xl border border-purple-400/20 bg-gradient-to-br from-purple-900/30 via-violet-900/20 to-indigo-900/10 transition-all hover:border-purple-400/40 hover:shadow-lg hover:shadow-purple-500/10"
                  >
                    {/* Subtle background accent */}
                    <div className="absolute top-0 right-0 h-24 w-24 rounded-full bg-gradient-to-br from-purple-500/10 to-transparent blur-2xl"></div>

                    <div className="relative p-6">
                      {/* Header with number badge and title */}
                      <div className="mb-5 flex items-start gap-4">
                        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-purple-600 to-violet-600 font-bold text-base text-white shadow-lg shadow-purple-500/30">
                          {idx + 1}
                        </div>
                        <div className="flex-1">
                          <h3 className="mb-1 font-bold text-purple-200 text-xl transition-colors group-hover:text-purple-100">
                            {indicator.indicator}
                          </h3>
                          <div className="h-0.5 w-12 rounded-full bg-gradient-to-r from-purple-500 to-violet-500"></div>
                        </div>
                      </div>

                      {/* Three distinct sections with visual hierarchy */}
                      <div className="ml-14 space-y-3">
                        {/* Observation - Primary (Emerald) */}
                        <div className="rounded-lg border border-emerald-400/30 bg-gradient-to-r from-emerald-950/40 to-teal-950/30 p-3.5">
                          <div className="mb-2 flex items-center gap-2">
                            <svg
                              className="h-4 w-4 text-emerald-400"
                              fill="none"
                              viewBox="0 0 24 24"
                              stroke="currentColor"
                              strokeWidth={2}
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                              />
                            </svg>
                            <span className="font-bold text-emerald-400 text-xs uppercase tracking-wide">
                              Observation
                            </span>
                          </div>
                          <p className="text-gray-200 text-sm leading-relaxed">
                            {indicator.observation}
                          </p>
                        </div>

                        {/* Scope - Secondary (Blue) */}
                        <div className="rounded-lg border border-blue-400/20 bg-gradient-to-r from-blue-950/30 to-indigo-950/20 px-3.5 py-2.5">
                          <div className="flex items-center gap-2">
                            <svg
                              className="h-3.5 w-3.5 text-blue-400"
                              fill="none"
                              viewBox="0 0 24 24"
                              stroke="currentColor"
                              strokeWidth={2}
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                              />
                            </svg>
                            <span className="font-semibold text-blue-400 text-xs uppercase tracking-wide">
                              Scope:
                            </span>
                            <span className="text-blue-200/80 text-xs">{indicator.scope}</span>
                          </div>
                        </div>

                        {/* Implication - Insight (Amber) */}
                        <div className="rounded-lg border border-amber-400/30 bg-gradient-to-r from-amber-950/40 to-orange-950/30 p-3.5">
                          <div className="mb-2 flex items-center gap-2">
                            <svg
                              className="h-4 w-4 text-amber-400"
                              fill="none"
                              viewBox="0 0 24 24"
                              stroke="currentColor"
                              strokeWidth={2}
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                              />
                            </svg>
                            <span className="font-bold text-amber-400 text-xs uppercase tracking-wide">
                              Implication
                            </span>
                          </div>
                          <p className="font-light text-gray-200 text-sm leading-relaxed">
                            {indicator.implication}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </ExiqusCard>
          </TabsContent>

          {/* Tab 5: Strengths & Areas - with sub-tabs */}
          <TabsContent value="strengths" className="space-y-6">
            <Tabs value={activeStrengthsTab} onValueChange={setActiveStrengthsTab}>
              <TabsList className="grid w-full grid-cols-3 gap-2 bg-white/[0.05] p-1">
                <TabsTrigger
                  value="positive"
                  className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-emerald-600 data-[state=active]:to-green-600"
                >
                  Positive
                </TabsTrigger>
                <TabsTrigger
                  value="explore"
                  className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-teal-600 data-[state=active]:to-cyan-600"
                >
                  Explore
                </TabsTrigger>
                <TabsTrigger
                  value="recommendations"
                  className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-blue-600 data-[state=active]:to-purple-600"
                >
                  Recommendations
                </TabsTrigger>
              </TabsList>

              <TabsContent value="positive">
                <ExiqusCard className="border-emerald-500/20 p-8">
                  <div className="mb-6 flex items-center gap-3">
                    <div className="rounded-xl bg-gradient-to-br from-emerald-600 to-green-600 p-3 shadow-lg">
                      <Sparkles className="h-6 w-6 text-white" />
                    </div>
                    <div>
                      <h2 className="font-semibold text-2xl text-gray-100">
                        Positive Indicators ({positiveIndicators.length})
                      </h2>
                      <p className="text-gray-400 text-sm">Strengths visible in public repos</p>
                    </div>
                  </div>
                  <div className="space-y-3">
                    {positiveIndicators.map((ind, idx) => (
                      <div
                        key={idx}
                        className="flex items-start gap-3 rounded-lg border border-emerald-500/20 bg-gradient-to-r from-emerald-900/20 to-green-900/10 p-4"
                      >
                        <div className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-emerald-600 to-green-600 font-bold text-white text-xs">
                          {idx + 1}
                        </div>
                        <p className="text-gray-300 text-sm leading-relaxed">{ind}</p>
                      </div>
                    ))}
                  </div>
                </ExiqusCard>
              </TabsContent>

              <TabsContent value="explore">
                <ExiqusCard className="border-teal-500/20 p-8">
                  <div className="mb-6 flex items-center gap-3">
                    <div className="rounded-xl bg-gradient-to-br from-teal-600 to-cyan-600 p-3 shadow-lg">
                      <Search className="h-6 w-6 text-white" />
                    </div>
                    <div>
                      <h2 className="font-semibold text-2xl text-gray-100">
                        Areas to Explore ({areasToExplore.length})
                      </h2>
                      <p className="text-gray-400 text-sm">Questions for deeper insights</p>
                    </div>
                  </div>
                  <div className="space-y-3">
                    {areasToExplore.map((area, idx) => (
                      <div
                        key={idx}
                        className="flex items-start gap-3 rounded-lg border border-teal-500/20 bg-gradient-to-r from-teal-900/20 to-cyan-900/10 p-4"
                      >
                        <div className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-teal-600 to-cyan-600 font-bold text-white text-xs">
                          {idx + 1}
                        </div>
                        <p className="text-gray-300 text-sm leading-relaxed">{area}</p>
                      </div>
                    ))}
                  </div>
                </ExiqusCard>
              </TabsContent>

              <TabsContent value="recommendations">
                <ExiqusCard className="border-blue-500/20 p-8">
                  <div className="mb-6 flex items-center gap-3">
                    <div className="rounded-xl bg-gradient-to-br from-blue-600 to-purple-600 p-3 shadow-lg">
                      <Target className="h-6 w-6 text-white" />
                    </div>
                    <div>
                      <h2 className="font-semibold text-2xl text-gray-100">
                        Recommendations ({recommendations.length})
                      </h2>
                      <p className="text-gray-400 text-sm">Actionable next steps</p>
                    </div>
                  </div>
                  <div className="space-y-3">
                    {recommendations.map((rec, idx) => (
                      <div
                        key={idx}
                        className="flex items-start gap-3 rounded-lg border border-blue-500/20 bg-gradient-to-r from-blue-900/20 to-purple-900/10 p-4"
                      >
                        <div className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-blue-600 to-purple-600 font-bold text-white text-xs">
                          {idx + 1}
                        </div>
                        <p className="text-gray-300 text-sm leading-relaxed">{rec}</p>
                      </div>
                    ))}
                  </div>
                </ExiqusCard>
              </TabsContent>
            </Tabs>
          </TabsContent>

          {/* Tab 6: Interview Guide */}
          <TabsContent value="interview" className="space-y-6" id="interview-questions">
            {/* Interview Overview */}
            <div className="mb-6 rounded-xl border border-purple-500/20 bg-gradient-to-r from-purple-900/20 to-blue-900/20 p-6">
              <div className="mb-3 flex items-center gap-3">
                <MessageCircle className="h-6 w-6 text-purple-400" />
                <h2 className="font-bold text-purple-300 text-xl">Interview Intelligence Guide</h2>
              </div>
              <p className="text-gray-400 text-sm">
                {areasToExplore.length} priority areas to investigate • {interviewQuestions.length}{' '}
                evidence-based questions for {analysis.context} context
              </p>
            </div>

            {/* Nested Tabs: Priority Areas vs Questions */}
            <Tabs
              value={activeInterviewGuideTab}
              onValueChange={setActiveInterviewGuideTab}
              className="space-y-6"
            >
              <TabsList className="grid w-full grid-cols-2 bg-white/[0.05] p-1">
                <TabsTrigger
                  value="priority"
                  className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-amber-600 data-[state=active]:to-orange-600"
                >
                  <AlertCircle className="mr-2 h-4 w-4" />
                  Priority Areas ({areasToExplore.length})
                </TabsTrigger>
                <TabsTrigger
                  value="questions"
                  className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-purple-600 data-[state=active]:to-blue-600"
                >
                  <MessageCircle className="mr-2 h-4 w-4" />
                  Interview Framework ({interviewQuestions.length})
                </TabsTrigger>
              </TabsList>

              {/* Priority Investigation Areas Tab */}
              <TabsContent value="priority" className="space-y-6">
                {areasToExplore.length > 0 ? (
                  <ExiqusCard className="border-amber-500/20 p-6">
                    <h3 className="mb-4 flex items-center gap-2 font-bold text-xl">
                      <AlertCircle className="h-6 w-6 text-amber-400" />
                      Priority Investigation Areas
                    </h3>
                    <p className="mb-4 text-gray-400 text-sm">
                      High-priority questions to investigate based on gaps or concerns in the public
                      portfolio
                    </p>
                    <div className="space-y-4">
                      {areasToExplore.map((area, idx) => (
                        <div
                          key={idx}
                          className="rounded-lg border border-amber-500/20 bg-gradient-to-r from-amber-900/20 to-transparent p-4"
                        >
                          <div className="flex items-start gap-3">
                            <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-amber-600 to-orange-600 font-bold text-sm text-white">
                              P{idx + 1}
                            </div>
                            <div>
                              <p className="mb-2 text-gray-300 leading-relaxed">{area}</p>
                              <div className="text-amber-400 text-xs">
                                💡 Switch to Questions tab to explore related interview questions
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </ExiqusCard>
                ) : (
                  <ExiqusCard className="p-8 text-center">
                    <AlertCircle className="mx-auto mb-4 h-12 w-12 text-gray-600" />
                    <p className="text-gray-400">No priority investigation areas identified.</p>
                  </ExiqusCard>
                )}
              </TabsContent>

              {/* Interview Questions Tab with Category Sub-tabs */}
              <TabsContent value="questions" className="space-y-6">
                {interviewQuestions.length > 0 &&
                  (() => {
                    // Group questions by category
                    const questionsByCategory = interviewQuestions.reduce(
                      (acc: Record<string, typeof interviewQuestions>, q) => {
                        const cat = q.category || 'other';
                        if (!acc[cat]) acc[cat] = [];
                        acc[cat].push(q);
                        return acc;
                      },
                      {}
                    );

                    const categories = Object.keys(questionsByCategory);
                    const showCategoryTabs = categories.length > 1;

                    return (
                      <>
                        {/* Information Banner */}
                        <div className="mb-6 rounded-xl border border-blue-500/30 bg-gradient-to-r from-blue-900/20 to-indigo-900/20 p-5">
                          <div className="flex items-start gap-4">
                            <div className="flex-shrink-0 rounded-lg bg-blue-500/20 p-2">
                              <Sparkles className="h-5 w-5 text-blue-400" />
                            </div>
                            <div className="flex-1 space-y-2">
                              <h4 className="font-semibold text-blue-300">
                                Portfolio-Level Question Framework
                              </h4>
                              <p className="text-gray-300 text-sm leading-relaxed">
                                These questions are intentionally broad and open-ended, based on
                                <span className="font-medium text-blue-200">
                                  {' '}
                                  high-level portfolio metrics
                                </span>{' '}
                                (repository counts, commit volumes, technology distribution). They
                                provide a strategic interview framework across your entire
                                portfolio.
                              </p>
                              <div className="mt-3 flex items-start gap-2 rounded-lg bg-blue-950/40 p-3 text-sm">
                                <Target className="mt-0.5 h-4 w-4 flex-shrink-0 text-blue-400" />
                                <p className="text-gray-300">
                                  <span className="font-semibold text-blue-200">
                                    Want granular insights?
                                  </span>{' '}
                                  Use the{' '}
                                  <span className="font-medium text-white">Repositories tab</span>{' '}
                                  to analyze individual repos. Single repository analysis references{' '}
                                  <span className="font-medium text-blue-200">
                                    specific commit messages, line changes, and code patterns
                                  </span>
                                  —providing detailed, evidence-backed questions.
                                </p>
                              </div>
                            </div>
                          </div>
                        </div>

                        <ExiqusCard className="border-purple-500/20 p-6">
                          <h3 className="mb-6 flex items-center gap-2 font-bold text-2xl">
                            <MessageCircle className="h-6 w-6 text-purple-400" />
                            Interview Framework ({interviewQuestions.length})
                          </h3>

                          {showCategoryTabs && (
                            <Tabs
                              value={activeQuestionCategory}
                              onValueChange={setActiveQuestionCategory}
                              className="space-y-10"
                            >
                              <TabsList className="mb-10 flex max-h-[200px] w-full flex-wrap gap-2 overflow-y-auto bg-transparent p-0 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-purple-500/50 hover:[&::-webkit-scrollbar-thumb]:bg-purple-500/70 [&::-webkit-scrollbar-track]:bg-purple-900/20 [&::-webkit-scrollbar]:w-2">
                                {/* All tab */}
                                <TabsTrigger
                                  value="all"
                                  className="whitespace-nowrap rounded-full border border-purple-500/30 bg-purple-900/20 px-4 py-1.5 font-medium text-xs transition-all hover:border-purple-500/40 hover:bg-purple-900/30 data-[state=active]:scale-105 data-[state=active]:border-purple-500/50 data-[state=active]:bg-gradient-to-r data-[state=active]:from-purple-600 data-[state=active]:to-blue-600 data-[state=active]:shadow-lg data-[state=active]:shadow-purple-500/30"
                                >
                                  All ({interviewQuestions.length})
                                </TabsTrigger>
                                {categories.map((cat) => {
                                  // Category-specific color mapping
                                  const getCategoryColors = (category: string) => {
                                    const catLower = category.toLowerCase();
                                    if (
                                      catLower.includes('technical') ||
                                      catLower.includes('architecture')
                                    ) {
                                      return {
                                        inactive: 'border-blue-500/30 bg-blue-900/20 text-blue-300',
                                        active:
                                          'data-[state=active]:from-blue-600 data-[state=active]:to-cyan-600',
                                      };
                                    }
                                    if (
                                      catLower.includes('problem') ||
                                      catLower.includes('scalability')
                                    ) {
                                      return {
                                        inactive:
                                          'border-emerald-500/30 bg-emerald-900/20 text-emerald-300',
                                        active:
                                          'data-[state=active]:from-emerald-600 data-[state=active]:to-teal-600',
                                      };
                                    }
                                    if (
                                      catLower.includes('quality') ||
                                      catLower.includes('professional')
                                    ) {
                                      return {
                                        inactive:
                                          'border-amber-500/30 bg-amber-900/20 text-amber-300',
                                        active:
                                          'data-[state=active]:from-amber-600 data-[state=active]:to-orange-600',
                                      };
                                    }
                                    if (
                                      catLower.includes('adapt') ||
                                      catLower.includes('learning') ||
                                      catLower.includes('context')
                                    ) {
                                      return {
                                        inactive:
                                          'border-violet-500/30 bg-violet-900/20 text-violet-300',
                                        active:
                                          'data-[state=active]:from-violet-600 data-[state=active]:to-purple-600',
                                      };
                                    }
                                    if (
                                      catLower.includes('project') ||
                                      catLower.includes('management') ||
                                      catLower.includes('work')
                                    ) {
                                      return {
                                        inactive: 'border-pink-500/30 bg-pink-900/20 text-pink-300',
                                        active:
                                          'data-[state=active]:from-pink-600 data-[state=active]:to-rose-600',
                                      };
                                    }
                                    // Default purple for any other categories
                                    return {
                                      inactive:
                                        'border-purple-500/30 bg-purple-900/20 text-purple-300',
                                      active:
                                        'data-[state=active]:from-purple-600 data-[state=active]:to-blue-600',
                                    };
                                  };

                                  const colors = getCategoryColors(cat);
                                  const catLower = cat.toLowerCase();

                                  // Get hover color based on category
                                  let hoverBg = 'hover:bg-purple-900/30';
                                  if (
                                    catLower.includes('technical') ||
                                    catLower.includes('architecture')
                                  ) {
                                    hoverBg = 'hover:bg-blue-900/30 hover:border-blue-500/40';
                                  } else if (
                                    catLower.includes('problem') ||
                                    catLower.includes('scalability')
                                  ) {
                                    hoverBg = 'hover:bg-emerald-900/30 hover:border-emerald-500/40';
                                  } else if (
                                    catLower.includes('quality') ||
                                    catLower.includes('professional')
                                  ) {
                                    hoverBg = 'hover:bg-amber-900/30 hover:border-amber-500/40';
                                  } else if (
                                    catLower.includes('adapt') ||
                                    catLower.includes('learning') ||
                                    catLower.includes('context')
                                  ) {
                                    hoverBg = 'hover:bg-violet-900/30 hover:border-violet-500/40';
                                  } else if (
                                    catLower.includes('project') ||
                                    catLower.includes('management') ||
                                    catLower.includes('work')
                                  ) {
                                    hoverBg = 'hover:bg-pink-900/30 hover:border-pink-500/40';
                                  }

                                  return (
                                    <TabsTrigger
                                      key={cat}
                                      value={cat}
                                      className={`whitespace-nowrap rounded-full border px-4 py-1.5 font-medium text-xs transition-all hover:scale-105 ${colors.inactive} ${hoverBg} data-[state=active]:border-opacity-50 data-[state=active]:bg-gradient-to-r ${colors.active} data-[state=active]:scale-105 data-[state=active]:text-white data-[state=active]:shadow-lg`}
                                    >
                                      {cat.charAt(0).toUpperCase() + cat.slice(1)} (
                                      {questionsByCategory[cat].length})
                                    </TabsTrigger>
                                  );
                                })}
                              </TabsList>

                              {/* All questions tab content */}
                              <TabsContent value="all" className="space-y-4">
                                {interviewQuestions.map((q, idx) => (
                                  <div
                                    key={idx}
                                    className="group rounded-xl border border-purple-400/20 bg-gradient-to-br from-purple-900/20 via-blue-900/10 to-indigo-900/10 p-6 transition-all hover:border-purple-400/40 hover:shadow-lg hover:shadow-purple-500/10"
                                  >
                                    <div className="flex items-start gap-4">
                                      <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-purple-600 to-blue-600 font-bold text-sm text-white shadow-lg shadow-purple-500/30">
                                        Q{idx + 1}
                                      </div>
                                      <div className="flex-1 space-y-4">
                                        <div>
                                          <div className="mb-2 flex items-center gap-2">
                                            <span className="rounded-full bg-purple-500/20 px-3 py-1 font-medium text-purple-300 text-xs">
                                              {q.category}
                                            </span>
                                          </div>
                                          <p className="font-semibold text-gray-100 text-lg transition-colors group-hover:text-purple-100">
                                            {q.question}
                                          </p>
                                        </div>

                                        {q.context && (
                                          <div className="rounded-lg border border-blue-400/30 bg-gradient-to-r from-blue-950/40 to-indigo-950/30 p-3.5">
                                            <div className="mb-2 flex items-center gap-2">
                                              <svg
                                                className="h-4 w-4 text-blue-400"
                                                fill="none"
                                                viewBox="0 0 24 24"
                                                stroke="currentColor"
                                                strokeWidth={2}
                                              >
                                                <path
                                                  strokeLinecap="round"
                                                  strokeLinejoin="round"
                                                  d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                                                />
                                              </svg>
                                              <span className="font-bold text-blue-400 text-xs uppercase tracking-wide">
                                                Context Intelligence
                                              </span>
                                            </div>
                                            <p className="text-gray-300 text-sm leading-relaxed">
                                              {q.context}
                                            </p>
                                          </div>
                                        )}

                                        {q.evidence && (
                                          <div className="rounded-lg border border-emerald-400/30 bg-gradient-to-r from-emerald-950/40 to-teal-950/30 p-3.5">
                                            <div className="mb-2 flex items-center gap-2">
                                              <svg
                                                className="h-4 w-4 text-emerald-400"
                                                fill="none"
                                                viewBox="0 0 24 24"
                                                stroke="currentColor"
                                                strokeWidth={2}
                                              >
                                                <path
                                                  strokeLinecap="round"
                                                  strokeLinejoin="round"
                                                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                                                />
                                              </svg>
                                              <span className="font-bold text-emerald-400 text-xs uppercase tracking-wide">
                                                Based on Evidence
                                              </span>
                                            </div>
                                            <p className="text-gray-300 text-sm leading-relaxed">
                                              {q.evidence}
                                            </p>
                                          </div>
                                        )}

                                        {q.followUps && q.followUps.length > 0 && (
                                          <div className="rounded-lg border border-indigo-400/20 bg-gradient-to-r from-indigo-950/30 to-purple-950/20 p-3.5">
                                            <p className="mb-2 font-bold text-indigo-400 text-xs uppercase tracking-wide">
                                              Follow-up Questions
                                            </p>
                                            <ul className="space-y-2">
                                              {q.followUps.map((fu, fuIdx) => (
                                                <li
                                                  key={fuIdx}
                                                  className="flex items-start gap-2 text-gray-300 text-sm"
                                                >
                                                  <ChevronRight className="mt-0.5 h-4 w-4 flex-shrink-0 text-indigo-400" />
                                                  <span>{fu}</span>
                                                </li>
                                              ))}
                                            </ul>
                                          </div>
                                        )}

                                        {q.listeningPoints && (
                                          <div className="rounded-lg border border-amber-400/30 bg-gradient-to-r from-amber-950/40 to-orange-950/30 p-3.5">
                                            <div className="mb-2 flex items-center gap-2">
                                              <svg
                                                className="h-4 w-4 text-amber-400"
                                                fill="none"
                                                viewBox="0 0 24 24"
                                                stroke="currentColor"
                                                strokeWidth={2}
                                              >
                                                <path
                                                  strokeLinecap="round"
                                                  strokeLinejoin="round"
                                                  d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                                                />
                                              </svg>
                                              <span className="font-bold text-amber-400 text-xs uppercase tracking-wide">
                                                Key Listening Points
                                              </span>
                                            </div>
                                            <p className="text-gray-300 text-sm leading-relaxed">
                                              {q.listeningPoints}
                                            </p>
                                          </div>
                                        )}
                                      </div>
                                    </div>
                                  </div>
                                ))}
                              </TabsContent>

                              {categories.map((cat) => (
                                <TabsContent key={cat} value={cat} className="space-y-4">
                                  {questionsByCategory[cat].map((q, idx) => (
                                    <div
                                      key={idx}
                                      className="group rounded-xl border border-purple-400/20 bg-gradient-to-br from-purple-900/20 via-blue-900/10 to-indigo-900/10 p-6 transition-all hover:border-purple-400/40 hover:shadow-lg hover:shadow-purple-500/10"
                                    >
                                      <div className="flex items-start gap-4">
                                        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-purple-600 to-blue-600 font-bold text-sm text-white shadow-lg shadow-purple-500/30">
                                          Q{idx + 1}
                                        </div>
                                        <div className="flex-1 space-y-4">
                                          <div>
                                            <div className="mb-2 flex items-center gap-2">
                                              <span className="rounded-full bg-purple-500/20 px-3 py-1 font-medium text-purple-300 text-xs">
                                                {q.category}
                                              </span>
                                            </div>
                                            <p className="font-semibold text-gray-100 text-lg transition-colors group-hover:text-purple-100">
                                              {q.question}
                                            </p>
                                          </div>

                                          {q.context && (
                                            <div className="rounded-lg border border-blue-400/30 bg-gradient-to-r from-blue-950/40 to-indigo-950/30 p-3.5">
                                              <div className="mb-2 flex items-center gap-2">
                                                <svg
                                                  className="h-4 w-4 text-blue-400"
                                                  fill="none"
                                                  viewBox="0 0 24 24"
                                                  stroke="currentColor"
                                                  strokeWidth={2}
                                                >
                                                  <path
                                                    strokeLinecap="round"
                                                    strokeLinejoin="round"
                                                    d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                                                  />
                                                </svg>
                                                <span className="font-bold text-blue-400 text-xs uppercase tracking-wide">
                                                  Context Intelligence
                                                </span>
                                              </div>
                                              <p className="text-gray-300 text-sm leading-relaxed">
                                                {q.context}
                                              </p>
                                            </div>
                                          )}

                                          {q.evidence && (
                                            <div className="rounded-lg border border-emerald-400/30 bg-gradient-to-r from-emerald-950/40 to-teal-950/30 p-3.5">
                                              <div className="mb-2 flex items-center gap-2">
                                                <svg
                                                  className="h-4 w-4 text-emerald-400"
                                                  fill="none"
                                                  viewBox="0 0 24 24"
                                                  stroke="currentColor"
                                                  strokeWidth={2}
                                                >
                                                  <path
                                                    strokeLinecap="round"
                                                    strokeLinejoin="round"
                                                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                                                  />
                                                </svg>
                                                <span className="font-bold text-emerald-400 text-xs uppercase tracking-wide">
                                                  Based on Evidence
                                                </span>
                                              </div>
                                              <p className="text-gray-300 text-sm leading-relaxed">
                                                {q.evidence}
                                              </p>
                                            </div>
                                          )}

                                          {q.followUps && q.followUps.length > 0 && (
                                            <div className="rounded-lg border border-indigo-400/20 bg-gradient-to-r from-indigo-950/30 to-purple-950/20 p-3.5">
                                              <p className="mb-2 font-bold text-indigo-400 text-xs uppercase tracking-wide">
                                                Follow-up Questions
                                              </p>
                                              <ul className="space-y-2">
                                                {q.followUps.map((fu, fuIdx) => (
                                                  <li
                                                    key={fuIdx}
                                                    className="flex items-start gap-2 text-gray-300 text-sm"
                                                  >
                                                    <ChevronRight className="mt-0.5 h-4 w-4 flex-shrink-0 text-indigo-400" />
                                                    <span>{fu}</span>
                                                  </li>
                                                ))}
                                              </ul>
                                            </div>
                                          )}

                                          {q.listeningPoints && (
                                            <div className="rounded-lg border border-amber-400/30 bg-gradient-to-r from-amber-950/40 to-orange-950/30 p-3.5">
                                              <div className="mb-2 flex items-center gap-2">
                                                <svg
                                                  className="h-4 w-4 text-amber-400"
                                                  fill="none"
                                                  viewBox="0 0 24 24"
                                                  stroke="currentColor"
                                                  strokeWidth={2}
                                                >
                                                  <path
                                                    strokeLinecap="round"
                                                    strokeLinejoin="round"
                                                    d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                                                  />
                                                </svg>
                                                <span className="font-bold text-amber-400 text-xs uppercase tracking-wide">
                                                  Key Listening Points
                                                </span>
                                              </div>
                                              <p className="text-gray-300 text-sm leading-relaxed">
                                                {q.listeningPoints}
                                              </p>
                                            </div>
                                          )}
                                        </div>
                                      </div>
                                    </div>
                                  ))}
                                </TabsContent>
                              ))}
                            </Tabs>
                          )}
                        </ExiqusCard>
                      </>
                    );
                  })()}
              </TabsContent>
            </Tabs>
          </TabsContent>

          {/* Repositories Tab */}
          <TabsContent value="repositories" className="space-y-6">
            <ExiqusCard className="border-pink-500/20 p-8">
              <div className="mb-6 flex items-center gap-3">
                <div className="rounded-xl bg-gradient-to-br from-pink-600 to-rose-600 p-3 shadow-lg">
                  <GitBranch className="h-6 w-6 text-white" />
                </div>
                <h2 className="bg-gradient-to-r from-pink-300 to-rose-300 bg-clip-text font-bold text-2xl text-transparent">
                  Analyzed Repositories
                </h2>
              </div>

              {analysis.repositories_analyzed && analysis.repositories_analyzed.length > 0 ? (
                <>
                  <div className="mb-6 rounded-xl border border-pink-500/20 bg-gradient-to-r from-pink-900/20 to-rose-900/20 p-6">
                    <p className="text-gray-300 text-lg">
                      Analyzed{' '}
                      <span className="font-bold text-pink-300">
                        {analysis.repositories_analyzed.length}
                      </span>{' '}
                      {analysis.repositories_analyzed.length !== 1 ? 'repositories' : 'repository'}{' '}
                      from{' '}
                      <span className="font-bold text-pink-300">@{analysis.github_username}</span>
                    </p>
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    {analysis.repositories_analyzed.map((repo, idx) => (
                      <div
                        key={idx}
                        className="group rounded-lg border border-pink-500/20 bg-gradient-to-r from-pink-900/20 to-transparent p-4 transition-all hover:border-pink-400/40"
                      >
                        <div className="flex items-center justify-between gap-3">
                          {/* GitHub Link */}
                          <a
                            href={`https://github.com/${repo}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex min-w-0 flex-1 items-center gap-3"
                          >
                            <GitBranch className="h-5 w-5 flex-shrink-0 text-pink-400 transition-colors group-hover:text-pink-300" />
                            <span className="truncate font-mono text-gray-200 text-sm transition-colors group-hover:text-pink-200">
                              {repo}
                            </span>
                          </a>

                          {/* Deep Dive Button */}
                          <ExiqusButton
                            onClick={() => {
                              router.push(
                                `/analyze?repo=${encodeURIComponent(`https://github.com/${repo}`)}`
                              );
                            }}
                            className="flex-shrink-0 rounded-md bg-gradient-to-r from-pink-600 to-rose-600 px-3 py-1.5 text-white text-xs transition-all hover:from-pink-500 hover:to-rose-500"
                          >
                            <Search className="mr-1.5 h-3.5 w-3.5" />
                            Deep Dive
                          </ExiqusButton>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <div className="rounded-xl border border-pink-500/20 bg-gradient-to-r from-pink-900/20 to-rose-900/20 p-6">
                  <p className="text-center text-gray-400">No repository data available</p>
                </div>
              )}
            </ExiqusCard>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
