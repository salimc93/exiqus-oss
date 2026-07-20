// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import { format } from 'date-fns';
import {
  AlertCircle,
  ArrowLeft,
  Award,
  Brain,
  Calendar,
  CheckCircle,
  ChevronRight,
  Clock,
  Code2,
  Eye,
  FileText,
  FolderGit2,
  GitBranch,
  GitPullRequest,
  Lightbulb,
  Loader2,
  MessageCircle,
  MessageSquare,
  Puzzle,
  Search,
  Shield,
  Star,
  Target,
  Users,
  XCircle,
  Zap,
} from 'lucide-react';
import { useParams, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { toast } from 'sonner';

import { UnauthorizedAccess } from '@/components/auth/unauthorized-access';
import { OrganizationBadge } from '@/components/candidate-hub/OrganizationBadge';
import { RoleBadge } from '@/components/candidate-hub/RoleBadge';
import { ExiqusButton, ExiqusCard, GradientText } from '@/components/ui/exiqus-components';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useAuth } from '@/contexts/auth-context';
import { api } from '@/lib/api-client';

interface PRAnalysisData {
  username: string;
  context: string;
  role: string;
  total_prs_analyzed: number;
  repositories_contributed: string[];
  summary_report: string;
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
      context_note?: string;
      follow_up_questions?: string[];
      key_listening_points?: string;
    }>;
    key_insights?: Array<{
      title: string;
      category: string;
      description: string;
      evidence: string;
      impact: 'positive' | 'negative' | 'neutral';
      hiring_implication: string;
    }>;
    key_strengths?: string[];
    technical_capabilities?: string[];
    collaboration_style?: string[];
    code_quality_indicators?: string[];
    areas_for_discussion?: string[];
    notable_contributions?: string[];
    data_limitations?: string[];
    context_fit?: {
      alignment?: string;
      supporting_evidence?: string[];
      considerations?: string[];
      specific_strengths_for_context?: string[];
    };
  };
  data_quality: 'high' | 'moderate' | 'low';
  ai_insights_available: boolean;
  api_calls_used: number;
  fetch_time_seconds: number;
  from_cache: boolean;
  created_at?: string;
  total_time_seconds?: number;
  status?: 'pending' | 'processing' | 'completed' | 'failed';
  // Portfolio analysis info
  repos_analyzed?: number;
  has_portfolio_analysis?: boolean;
  portfolio_analysis_id?: string;
  show_portfolio_card?: boolean;
}

// Helper function to format duration
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

export default function PRAnalysisResultsPage() {
  const params = useParams();
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [analysis, setAnalysis] = useState<PRAnalysisData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('decision');
  const [activeEvidenceTab, setActiveEvidenceTab] = useState('strengths');
  const [activeInterviewGuideTab, setActiveInterviewGuideTab] = useState('priority');
  const [activeInterviewTab, setActiveInterviewTab] = useState('all');

  // Handle hash navigation to interview questions
  useEffect(() => {
    if (window.location.hash === '#interview-questions') {
      setActiveTab('interview'); // Main tab: Interview Guide
      setActiveInterviewGuideTab('questions'); // Sub-tab: Interview Questions
      // Scroll to the section after a brief delay to ensure tab content is rendered
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
        const response = await api.getPRAnalysis(params.id as string);
        const data = response.data;

        // Check if analysis is still processing
        if (data.status === 'pending' || data.status === 'processing') {
          setAnalysis(data);
          setIsLoading(false); // Show the pending/processing UI

          // Start polling every 30 seconds if not already polling
          if (!pollInterval && isMounted) {
            pollInterval = setInterval(async () => {
              try {
                const pollResponse = await api.getPRAnalysis(params.id as string);
                const pollData = pollResponse.data;

                // Update analysis data
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
                    toast.success('Analysis completed!');
                  } else if (pollData.status === 'failed') {
                    toast.error('Analysis failed. Please try again.');
                  }
                }
              } catch (pollErr) {
                console.error('Polling error:', pollErr);
                // Don't stop polling on transient errors
              }
            }, 30000); // Poll every 30 seconds to reduce server load
          }
        } else {
          // Analysis is completed or failed
          setAnalysis(data);
          setIsLoading(false);

          if (data.status === 'failed') {
            toast.error('Analysis failed. Please try again.');
          }
        }
      } catch (err: unknown) {
        console.error('Failed to fetch PR analysis:', err);
        const error = err as { response?: { status?: number; data?: { detail?: string } } };

        // Provide specific error messages based on status code
        if (error.response?.status === 404) {
          setError(
            'Analysis not found. It may have been deleted or you may not have access to it.'
          );
          toast.error('PR analysis not found');
        } else if (error.response?.status && error.response.status >= 500) {
          setError(
            'Server error. Please try again later or contact support if the issue persists.'
          );
          toast.error('Server error loading PR analysis');
        } else {
          setError(
            error.response?.data?.detail ||
              'Failed to load analysis. Please check your connection and try again.'
          );
          toast.error('Failed to load PR analysis');
        }
      } finally {
        if (!pollInterval) {
          setIsLoading(false);
        }
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

  // Helper function to format context for display
  const formatContext = (context: string): string => {
    return context.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());
  };

  const _getContextIcon = (context: string) => {
    switch (context.toLowerCase()) {
      case 'startup':
        return <Zap className="h-5 w-5" />;
      case 'enterprise':
        return <Shield className="h-5 w-5" />;
      case 'agency':
        return <Users className="h-5 w-5" />;
      case 'open_source':
        return <GitBranch className="h-5 w-5" />;
      default:
        return <Code2 className="h-5 w-5" />;
    }
  };

  // Show loading while checking auth or loading data
  if (authLoading || isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0A0A0A]">
        <div className="text-center">
          <Loader2 className="mx-auto mb-4 h-12 w-12 animate-spin text-teal-400" />
          <p className="text-gray-400">Loading PR analysis results...</p>
        </div>
      </div>
    );
  }

  // Show beautiful unauthorized component if not authenticated
  if (!user) {
    return <UnauthorizedAccess context="pr" />;
  }

  if (error || !analysis) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0A0A0A]">
        <ExiqusCard className="max-w-md p-8 text-center">
          <XCircle className="mx-auto mb-4 h-12 w-12 text-red-500" />
          <h2 className="mb-2 font-semibold text-gray-100 text-xl">Failed to Load Analysis</h2>
          <p className="mb-6 text-gray-400">{error || 'Analysis not found'}</p>
          <ExiqusButton onClick={() => router.push('/pr-analysis')}>
            Try Another Analysis
          </ExiqusButton>
        </ExiqusCard>
      </div>
    );
  }

  // Check for 0 PRs - show clean message instead of confusing UI
  if (analysis.total_prs_analyzed === 0) {
    return (
      <div className="min-h-screen bg-[#0A0A0A]">
        {/* Animated gradient background */}
        <div className="pointer-events-none fixed inset-0 overflow-hidden">
          <div className="absolute -top-40 -right-40 h-80 w-80 animate-pulse rounded-full bg-teal-500/20 blur-3xl"></div>
          <div className="absolute -bottom-40 -left-40 h-80 w-80 animate-pulse rounded-full bg-cyan-500/20 blur-3xl delay-1000"></div>
        </div>

        <div className="container relative mx-auto flex min-h-screen max-w-4xl items-center justify-center px-4 py-16">
          <ExiqusCard className="max-w-2xl border-teal-500/20 p-12 text-center">
            {/* Icon */}
            <div className="mb-6 flex justify-center">
              <div className="rounded-full border border-teal-500/30 bg-gradient-to-br from-teal-900/40 to-cyan-900/40 p-4">
                <GitPullRequest className="h-16 w-16 text-teal-400" />
              </div>
            </div>

            {/* Title */}
            <h2 className="mb-4 font-bold text-3xl">
              <GradientText className="bg-gradient-to-r from-teal-400 to-cyan-400">
                No Pull Request Activity Found
              </GradientText>
            </h2>

            {/* User info */}
            <p className="mb-6 text-gray-300 text-xl">@{analysis.username}</p>

            {/* Message */}
            <div className="mb-8 rounded-xl border border-teal-500/20 bg-gradient-to-r from-teal-950/30 to-cyan-950/30 p-6">
              <p className="mb-4 text-gray-300">
                This user has no public pull request activity on GitHub.
              </p>
              <p className="text-gray-400 text-sm">
                This could mean they work primarily in private repositories, contribute to other
                platforms, or their development work doesn&apos;t involve pull requests.
              </p>
            </div>

            {/* Suggestions */}
            <div className="mb-8">
              <h3 className="mb-4 font-semibold text-gray-200 text-lg">What to try next:</h3>
              <div className="grid gap-4 text-left">
                <div className="rounded-lg border border-indigo-500/20 bg-gradient-to-r from-indigo-900/20 to-transparent p-4">
                  <div className="flex items-start gap-3">
                    <FolderGit2 className="mt-0.5 h-5 w-5 flex-shrink-0 text-indigo-400" />
                    <div>
                      <h4 className="mb-1 font-medium text-indigo-300">Try Portfolio Analysis</h4>
                      <p className="text-gray-400 text-sm">
                        Get comprehensive insights across all their public repositories with
                        evidence-based analysis, technical patterns, and interview questions.
                      </p>
                    </div>
                  </div>
                </div>
                <div className="rounded-lg border border-blue-500/20 bg-gradient-to-r from-blue-900/20 to-transparent p-4">
                  <div className="flex items-start gap-3">
                    <MessageCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-blue-400" />
                    <div>
                      <h4 className="mb-1 font-medium text-blue-300">Discuss Their Experience</h4>
                      <p className="text-gray-400 text-sm">
                        Ask about their development work in private repositories, other platforms,
                        or non-PR based contributions.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-col justify-center gap-4 sm:flex-row">
              <ExiqusButton
                onClick={() => router.push('/portfolio-analysis')}
                className="bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700"
              >
                <FolderGit2 className="mr-2 h-4 w-4" />
                Try Portfolio Analysis
              </ExiqusButton>
              <ExiqusButton
                onClick={() => router.push('/pr-analysis')}
                className="bg-gradient-to-r from-teal-600 to-cyan-600 hover:from-teal-700 hover:to-cyan-700"
              >
                <Search className="mr-2 h-4 w-4" />
                Analyze Another User
              </ExiqusButton>
            </div>

            {/* Analysis Info */}
            <div className="mt-8 border-gray-800 border-t pt-6">
              <div className="flex items-center justify-center gap-6 text-gray-500 text-sm">
                {analysis.created_at && (
                  <div className="flex items-center gap-1">
                    <Calendar className="h-4 w-4" />
                    <span>{format(new Date(analysis.created_at), 'PPP')}</span>
                  </div>
                )}
                <div className="flex items-center gap-1">
                  <Clock className="h-4 w-4" />
                  <span>
                    {formatDuration(analysis.total_time_seconds || analysis.fetch_time_seconds)}
                  </span>
                </div>
              </div>
            </div>
          </ExiqusCard>
        </div>
      </div>
    );
  }

  // Calculate total analysis time - if no AI processing occurred, just show fetch time
  const totalAnalysisTime = analysis.total_time_seconds || analysis.fetch_time_seconds;

  // Extract AI insights data properly and determine if we actually have AI insights
  const aiInsights = analysis.ai_insights || {};
  const interviewQuestions = aiInsights.interview_questions || [];
  const keyInsights = aiInsights.key_insights || [];
  const keyStrengths = aiInsights.key_strengths || [];
  const technicalCapabilities = aiInsights.technical_capabilities || [];
  const collaborationStyle = aiInsights.collaboration_style || [];
  const codeQualityIndicators = aiInsights.code_quality_indicators || [];
  const areasForDiscussion = aiInsights.areas_for_discussion || [];
  const notableContributions = aiInsights.notable_contributions || [];
  const dataLimitations = aiInsights.data_limitations || [];
  const contextFit = aiInsights.context_fit || {};

  // Determine if we actually have meaningful AI insights (ignore the flag, check actual data)
  const hasRealAIInsights = interviewQuestions.length > 0 && keyStrengths.length > 0;

  // Extract quality signals data
  const qualitySignals = analysis.detailed_report?.quality_signals || {};

  // Helper function to find related interview questions for a given evidence text
  const findRelatedQuestions = (evidenceText: string) => {
    return interviewQuestions
      .map((q, idx) => ({ ...q, index: idx + 1 }))
      .filter((q) => {
        const evidenceRef = q.evidence_reference?.toLowerCase() || '';
        const questionText = q.question?.toLowerCase() || '';
        const evidence = evidenceText.toLowerCase();

        return (
          evidenceRef.includes(evidence) ||
          questionText.includes(evidence) ||
          (evidence.includes('500+') &&
            (evidenceRef.includes('500+') || evidenceRef.includes('large'))) ||
          (evidence.includes('merge') && evidenceRef.includes('merge')) ||
          (evidence.includes('assigned') && evidenceRef.includes('assigned')) ||
          (evidence.includes('collaboration') && evidenceRef.includes('collaboration'))
        );
      });
  };

  return (
    <div className="min-h-screen bg-[#0A0A0A]">
      {/* Animated gradient background - Teal/Cyan theme for PR analysis */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 h-80 w-80 animate-pulse rounded-full bg-teal-500/20 blur-3xl"></div>
        <div className="absolute -bottom-40 -left-40 h-80 w-80 animate-pulse rounded-full bg-cyan-500/20 blur-3xl delay-1000"></div>
        <div className="absolute top-1/2 left-1/2 h-80 w-80 -translate-x-1/2 -translate-y-1/2 animate-pulse rounded-full bg-gradient-to-r from-teal-500/10 to-cyan-500/10 blur-3xl delay-500"></div>
      </div>

      <div className="container relative mx-auto max-w-7xl px-4 py-8">
        {/* Back Button */}
        <button
          type="button"
          onClick={() => {
            // If we have a username, go back to their candidate hub
            if (analysis?.username) {
              router.push(`/candidate-hub/${analysis.username}`);
            } else {
              router.push('/pr-analyses');
            }
          }}
          className="group mb-6 flex items-center gap-2 text-gray-400 transition-colors hover:text-teal-400"
        >
          <ArrowLeft className="h-5 w-5 transition-transform group-hover:-translate-x-1" />
          <span className="font-medium">
            {analysis?.username
              ? `Back to ${analysis.username}'s Hub`
              : 'Back to PR Analysis History'}
          </span>
        </button>

        {/* Header Section */}
        <div className="mb-8">
          <div className="mb-4 flex items-center gap-2 text-gray-400 text-sm">
            <GitPullRequest className="h-4 w-4 text-teal-400" />
            <span>PR Analysis</span>
            <ChevronRight className="h-4 w-4" />
            <a
              href={`https://github.com/pulls?q=is:pr+author:${analysis.username}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-300 transition-colors hover:text-teal-400 hover:underline"
            >
              @{analysis.username}
            </a>
          </div>

          <div className="grid gap-8 lg:grid-cols-2">
            {/* Left: Title and Info */}
            <div>
              <h1 className="mb-3 font-bold text-4xl">
                <a
                  href={`https://github.com/pulls?q=is:pr+author:${analysis.username}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="transition-opacity hover:opacity-80"
                >
                  <GradientText className="bg-gradient-to-r from-teal-400 to-cyan-400">
                    @{analysis.username}
                  </GradientText>
                </a>
              </h1>
              <p className="mb-4 text-gray-400 text-lg">Pull Request Analysis Report</p>

              {/* Analysis date and time */}
              <div className="flex items-center gap-4 text-gray-500 text-sm">
                {analysis.created_at && (
                  <div className="flex items-center gap-1">
                    <Calendar className="h-4 w-4" />
                    <span>{format(new Date(analysis.created_at), 'PPP')}</span>
                  </div>
                )}
                <div className="flex items-center gap-1">
                  <Clock className="h-4 w-4" />
                  <span>{formatDuration(totalAnalysisTime)}</span>
                </div>
              </div>

              {/* Context & Role Badges */}
              <div className="mt-4 flex items-center gap-2">
                <OrganizationBadge
                  context={analysis.context as 'startup' | 'enterprise' | 'agency' | 'open_source'}
                  size="lg"
                />
                <RoleBadge role={analysis.role as 'junior' | 'mid' | 'senior'} size="lg" />
              </div>
            </div>

            {/* Right: Key Metrics Grid */}
            <div className="grid grid-cols-3 gap-3">
              <div
                className="cursor-pointer rounded-xl border border-teal-500/20 bg-gradient-to-br from-teal-900/20 to-transparent p-4 transition-all hover:border-teal-400/40"
                onClick={() => setActiveTab('insights')}
              >
                <div className="mb-1 font-bold text-3xl text-teal-300">
                  {keyInsights.length || 0}
                </div>
                <div className="text-gray-400 text-sm">Key insights</div>
              </div>

              <div
                className="cursor-pointer rounded-xl border border-cyan-500/20 bg-gradient-to-br from-cyan-900/20 to-transparent p-4 transition-all hover:border-cyan-400/40"
                onClick={() => setActiveTab('evidence')}
              >
                <div className="mb-1 font-bold text-3xl text-cyan-300">
                  {(() => {
                    // Count all items in Evidence & Capabilities sections
                    const technicalCount = technicalCapabilities.length || 0;
                    const qualityCount = codeQualityIndicators.length || 0;
                    const collaborationCount = collaborationStyle.length || 0;
                    const notableCount = notableContributions.length || 0;
                    const strengthsCount = keyStrengths.length || 0;

                    return (
                      technicalCount +
                      qualityCount +
                      collaborationCount +
                      notableCount +
                      strengthsCount
                    );
                  })()}
                </div>
                <div className="text-gray-400 text-sm">Evidence & capabilities</div>
              </div>

              <div
                className="cursor-pointer rounded-xl border border-emerald-500/20 bg-gradient-to-br from-emerald-900/20 to-transparent p-4 transition-all hover:border-emerald-400/40"
                onClick={() => setActiveTab('interview')}
              >
                <div className="mb-1 font-bold text-3xl text-emerald-300">
                  {interviewQuestions.length || 0}
                </div>
                <div className="text-gray-400 text-sm">Interview questions</div>
              </div>
            </div>
          </div>
        </div>

        {/* PR Statistics Bar */}
        <div className="mb-8 grid grid-cols-2 gap-4 rounded-xl border border-teal-500/20 bg-gradient-to-r from-teal-950/30 to-cyan-950/30 p-6 md:grid-cols-5">
          <div className="text-center">
            <div className="font-bold text-2xl text-teal-300">{analysis.total_prs_analyzed}</div>
            <div className="mt-1 text-gray-400 text-xs">Total PRs</div>
          </div>
          <div className="text-center">
            <div className="font-bold text-2xl text-cyan-300">{qualitySignals.merged_prs || 0}</div>
            <div className="mt-1 text-gray-400 text-xs">Merged</div>
          </div>
          <div className="text-center">
            <div className="font-bold text-2xl text-emerald-300">
              {analysis.repositories_contributed.length}
            </div>
            <div className="mt-1 text-gray-400 text-xs">Repos</div>
          </div>
          <div className="text-center">
            <div className="font-bold text-2xl text-blue-300">
              {qualitySignals.feature_prs || 0}
            </div>
            <div className="mt-1 text-gray-400 text-xs">Features</div>
          </div>
          <div className="text-center">
            <div className="font-bold text-2xl text-green-300">{qualitySignals.fix_prs || 0}</div>
            <div className="mt-1 text-gray-400 text-xs">Fixes</div>
          </div>
        </div>

        {/* Portfolio Analysis Card - Show either "Run Analysis" or "View Existing" */}
        {analysis.show_portfolio_card && (
          <ExiqusCard className="mb-8 border-purple-500/30 bg-gradient-to-r from-purple-900/20 via-blue-900/10 to-transparent p-6">
            <div className="flex items-start gap-4">
              <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-purple-600 to-blue-600 shadow-lg shadow-purple-500/20">
                <FolderGit2 className="h-6 w-6 text-white" />
              </div>
              <div className="flex-1">
                {analysis.has_portfolio_analysis ? (
                  /* Existing Portfolio Analysis - Show link to view it */
                  <>
                    <div className="mb-2 flex items-center gap-2">
                      <h3 className="font-semibold text-lg text-purple-300">
                        Portfolio Analysis Complete
                      </h3>
                      <span className="rounded-full bg-purple-500/20 px-2 py-0.5 font-medium text-purple-300 text-xs">
                        {analysis.repos_analyzed} Repos Analyzed
                      </span>
                    </div>
                    <p className="mb-4 text-gray-300 text-sm">
                      Portfolio analysis reveals repository patterns, code quality, and technical
                      depth across {analysis.repos_analyzed} repositories. View the full analysis
                      for comprehensive insights.
                    </p>
                    <ExiqusButton
                      onClick={() =>
                        router.push(
                          `/portfolio-analyses/${analysis.portfolio_analysis_id}?returnTo=/pr-analyses/${params.id}`
                        )
                      }
                      className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"
                    >
                      <Eye className="mr-2 h-4 w-4" />
                      View Portfolio Analysis
                    </ExiqusButton>
                  </>
                ) : (
                  /* No Portfolio Analysis - Show recommendation to run it */
                  <>
                    <div className="mb-2 flex items-center gap-2">
                      <h3 className="font-semibold text-lg text-purple-300">
                        Complete the Picture
                      </h3>
                    </div>
                    <p className="mb-4 text-gray-300 text-sm">
                      PR analysis shows {analysis.total_prs_analyzed} pull requests across{' '}
                      {analysis.repositories_contributed.length} repositories. Run Portfolio
                      Analysis to assess repository quality, architecture patterns, and technical
                      depth.
                    </p>
                    <ExiqusButton
                      onClick={() =>
                        router.push(`/portfolio-analysis?username=${analysis.username}`)
                      }
                      className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"
                    >
                      <FolderGit2 className="mr-2 h-4 w-4" />
                      Run Portfolio Analysis
                    </ExiqusButton>
                  </>
                )}
              </div>
            </div>
          </ExiqusCard>
        )}

        {/* Main Content Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-6 bg-white/[0.03] p-1">
            <TabsTrigger
              value="decision"
              className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-teal-600 data-[state=active]:to-cyan-600"
            >
              <Target className="mr-2 h-4 w-4" />
              Summary
            </TabsTrigger>
            <TabsTrigger
              value="insights"
              className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-emerald-600 data-[state=active]:to-green-600"
            >
              <Lightbulb className="mr-2 h-4 w-4" />
              Insights
            </TabsTrigger>
            <TabsTrigger
              value="interview"
              className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-purple-600 data-[state=active]:to-pink-600"
            >
              <MessageSquare className="mr-2 h-4 w-4" />
              Interview
            </TabsTrigger>
            <TabsTrigger
              value="evidence"
              className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-indigo-600 data-[state=active]:to-purple-600"
            >
              <Star className="mr-2 h-4 w-4" />
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
              value="scope"
              className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-yellow-600 data-[state=active]:to-orange-600"
            >
              <AlertCircle className="mr-2 h-4 w-4" />
              Scope
            </TabsTrigger>
          </TabsList>

          {/* Intelligence Summary Tab */}
          <TabsContent value="decision" className="space-y-6">
            {/* Executive Summary - Key Intelligence Overview */}
            <ExiqusCard className="border-teal-500/20 p-8">
              <div className="mb-6 flex items-center gap-3">
                <div className="rounded-xl bg-gradient-to-br from-teal-600 to-cyan-600 p-3 shadow-lg">
                  <FileText className="h-6 w-6 text-white" />
                </div>
                <h2 className="bg-gradient-to-r from-teal-300 to-cyan-300 bg-clip-text font-bold text-2xl text-transparent">
                  Executive Summary
                </h2>
                {hasRealAIInsights ? (
                  <div className="ml-auto rounded-full bg-gradient-to-r from-emerald-600 to-teal-600 px-3 py-1 font-bold text-white text-xs">
                    ✨ AI Enhanced
                  </div>
                ) : (
                  <div className="ml-auto rounded-full bg-gradient-to-r from-orange-600 to-red-600 px-3 py-1 font-bold text-white text-xs">
                    ⚠️ Basic Analysis
                  </div>
                )}
              </div>

              {/* Key Intelligence Summary */}
              <div className="mb-6 rounded-xl border border-teal-400/20 bg-gradient-to-r from-teal-950/50 to-cyan-950/50 p-6">
                <div className="mb-4 flex items-center gap-3">
                  <Eye className="h-5 w-5 text-teal-400" />
                  <h3 className="font-bold text-lg text-teal-300">Key Intelligence</h3>
                </div>
                <p className="text-gray-200 leading-relaxed">
                  {(() => {
                    // Use AI-generated executive_summary if available
                    if (aiInsights.executive_summary) {
                      return aiInsights.executive_summary;
                    }

                    // Fallback: create a summary from the data
                    return `Analysis of ${analysis.total_prs_analyzed} pull request${analysis.total_prs_analyzed !== 1 ? 's' : ''} across ${analysis.repositories_contributed.length} repositor${analysis.repositories_contributed.length !== 1 ? 'ies' : 'y'}. ${qualitySignals.contribution_timespan ? `Sustained contributions over ${qualitySignals.contribution_timespan}` : 'Active contributor'} with a ${Math.round(((qualitySignals.merged_prs || 0) / analysis.total_prs_analyzed) * 100)}% production integration rate (${qualitySignals.merged_prs || 0} of ${analysis.total_prs_analyzed} PRs successfully merged). ${(qualitySignals.feature_prs || 0) > 0 ? 'Feature-focused contributor' : 'Balanced contribution profile'} demonstrating ${analysis.context.toLowerCase()} environment compatibility.`;
                  })()}
                </p>
              </div>

              {/* Evidence Quality Assessment */}
              <div className="rounded-xl border border-cyan-400/30 bg-gradient-to-r from-teal-950/50 to-cyan-950/40 p-6">
                <div className="mb-4 flex items-center gap-3">
                  <Shield className="h-5 w-5 text-cyan-400" />
                  <h3 className="font-bold text-cyan-300 text-lg">Evidence Quality Assessment</h3>
                </div>
                <div className="text-gray-200 leading-relaxed">
                  {(() => {
                    // Use AI-generated confidence_explanation if available
                    if (aiInsights.confidence_explanation) {
                      return aiInsights.confidence_explanation;
                    }

                    // Fallback: template-based assessment
                    const confidence =
                      analysis.data_quality === 'high'
                        ? 'High'
                        : analysis.data_quality === 'moderate'
                          ? 'Medium'
                          : 'Limited';

                    const aiInsightsText = hasRealAIInsights
                      ? `${confidence} confidence insight with AI-enhanced analysis generating ${interviewQuestions.length} interview questions and ${keyStrengths.length} key insights.`
                      : `${confidence} confidence insight based on automated pattern analysis of available PR data.`;

                    const contextText =
                      analysis.context === 'STARTUP'
                        ? 'Evidence patterns evaluated for startup environment compatibility including rapid iteration capability, feature development focus, and collaborative development practices.'
                        : `Evidence patterns evaluated for ${analysis.context.toLowerCase()} context compatibility.`;

                    return `${aiInsightsText} ${contextText} covering ${analysis.total_prs_analyzed} PR${analysis.total_prs_analyzed !== 1 ? 's' : ''}.`;
                  })()}
                </div>
              </div>
            </ExiqusCard>

            {/* Intelligence Assessment Cards */}
            <div className="grid gap-8 lg:grid-cols-2">
              {/* Primary Intelligence Assessment */}
              <div className="relative overflow-hidden rounded-2xl border border-emerald-500/30 bg-gradient-to-br from-emerald-900/40 via-teal-900/30 to-blue-900/40 backdrop-blur-sm">
                <div className="absolute inset-0 animate-pulse bg-gradient-to-r from-emerald-600/10 via-transparent to-blue-600/10"></div>
                <div className="absolute top-0 left-0 h-32 w-32 rounded-full bg-gradient-to-br from-emerald-500/20 to-transparent blur-xl"></div>

                <div className="relative p-8">
                  <div className="mb-6 flex items-center gap-3">
                    <div className="rounded-xl bg-gradient-to-br from-emerald-600 to-teal-600 p-3 shadow-lg">
                      <Brain className="h-6 w-6 text-white" />
                    </div>
                    <h2 className="bg-gradient-to-r from-emerald-300 to-teal-300 bg-clip-text font-bold text-2xl text-transparent">
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
                      {contextFit.alignment === 'strong'
                        ? 'Strong patterns indicate high compatibility with role requirements.'
                        : contextFit.alignment === 'moderate'
                          ? 'Promising indicators with specific areas requiring deeper validation.'
                          : 'Mixed patterns require targeted investigation to assess fit.'}
                    </p>
                  </div>

                  {/* Key Context Fit */}
                  <div className="rounded-lg border border-purple-400/30 bg-gradient-to-r from-purple-950/40 to-pink-950/40 p-4">
                    <h4 className="mb-2 font-medium text-purple-300">
                      {analysis.context} Context Intelligence
                    </h4>
                    <p className="text-gray-300 text-sm">
                      {(contextFit.supporting_evidence && contextFit.supporting_evidence[0]) ||
                        'Review evidence patterns for context compatibility intelligence.'}
                    </p>
                  </div>
                </div>
              </div>

              {/* Analysis Summary */}
              <div className="relative overflow-hidden rounded-2xl border border-teal-500/30 bg-gradient-to-br from-teal-900/40 via-cyan-900/30 to-indigo-900/40 backdrop-blur-sm">
                <div className="absolute inset-0 animate-pulse bg-gradient-to-r from-teal-600/10 via-transparent to-indigo-600/10"></div>

                <div className="relative p-8">
                  <div className="mb-6 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="rounded-xl bg-gradient-to-br from-teal-600 to-cyan-600 p-3 shadow-lg">
                        <FileText className="h-6 w-6 text-white" />
                      </div>
                      <h3 className="bg-gradient-to-r from-teal-300 to-cyan-300 bg-clip-text font-bold text-transparent text-xl">
                        Analysis Summary
                      </h3>
                    </div>

                    {/* AI Status Badge */}
                    {hasRealAIInsights ? (
                      <div className="rounded-full bg-gradient-to-r from-emerald-600 to-teal-600 px-3 py-1 font-bold text-white text-xs">
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
                      <span className="text-gray-400">PRs Analyzed:</span>
                      <span className="font-medium text-teal-300">
                        {analysis.total_prs_analyzed}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Success Rate:</span>
                      <span className="font-medium text-cyan-300">
                        {Math.round(
                          ((qualitySignals.merged_prs || 0) / analysis.total_prs_analyzed) * 100
                        )}
                        %
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Time Span:</span>
                      <span className="font-medium text-indigo-300">
                        {qualitySignals.contribution_timespan || 'N/A'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Evidence Confidence:</span>
                      <span
                        className={`font-medium capitalize ${
                          analysis.data_quality === 'high'
                            ? 'text-cyan-300'
                            : analysis.data_quality === 'moderate'
                              ? 'text-purple-300'
                              : 'text-gray-400'
                        }`}
                      >
                        {analysis.data_quality}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Top Strengths */}
            {keyStrengths.length > 0 && (
              <ExiqusCard className="border-emerald-500/20 p-6">
                <h3 className="mb-4 flex items-center gap-2 font-bold text-xl">
                  <Star className="h-6 w-6 text-emerald-400" />
                  Top Strengths ({Math.min(keyStrengths.length, 3)})
                </h3>
                <div className="grid gap-4">
                  {keyStrengths.slice(0, 3).map((strength, idx) => (
                    <div
                      key={idx}
                      className="flex items-start gap-4 rounded-lg border border-emerald-500/20 bg-gradient-to-r from-emerald-900/20 to-transparent p-4"
                    >
                      <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-emerald-600 to-green-600 font-bold text-sm text-white">
                        {idx + 1}
                      </div>
                      <p className="text-gray-300 leading-relaxed">{strength}</p>
                    </div>
                  ))}
                </div>
                {keyStrengths.length > 3 && (
                  <div className="mt-4 text-center">
                    <button
                      type="button"
                      onClick={() => setActiveTab('evidence')}
                      className="font-medium text-emerald-400 text-sm hover:text-emerald-300"
                    >
                      View all {keyStrengths.length} strengths →
                    </button>
                  </div>
                )}
              </ExiqusCard>
            )}

            {/* Areas Requiring Investigation */}
            {areasForDiscussion.length > 0 && (
              <ExiqusCard className="border-amber-500/20 p-6">
                <h3 className="mb-4 flex items-center gap-2 font-bold text-xl">
                  <Search className="h-6 w-6 text-amber-400" />
                  Areas Requiring Investigation ({Math.min(areasForDiscussion.length, 2)})
                </h3>
                <div className="grid gap-4">
                  {areasForDiscussion.slice(0, 2).map((area, idx) => (
                    <div
                      key={idx}
                      className="flex items-start gap-4 rounded-lg border border-amber-500/20 bg-gradient-to-r from-amber-900/20 to-transparent p-4"
                    >
                      <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-amber-600 to-orange-600 font-bold text-sm text-white">
                        {idx + 1}
                      </div>
                      <p className="text-gray-300 leading-relaxed">{area}</p>
                    </div>
                  ))}
                </div>
                {areasForDiscussion.length > 2 && (
                  <div className="mt-4 text-center">
                    <button
                      type="button"
                      onClick={() => setActiveTab('interview')}
                      className="font-medium text-amber-400 text-sm hover:text-amber-300"
                    >
                      View all investigation areas in Interview Guide →
                    </button>
                  </div>
                )}
              </ExiqusCard>
            )}
          </TabsContent>

          {/* Key Insights Tab */}
          <TabsContent value="insights" className="space-y-6">
            {keyInsights.length > 0 ? (
              <>
                <div className="mb-6 rounded-xl border border-teal-500/20 bg-gradient-to-r from-teal-900/20 to-blue-900/20 p-6">
                  <div className="mb-3 flex items-center gap-3">
                    <Lightbulb className="h-6 w-6 text-teal-400" />
                    <h2 className="font-bold text-teal-300 text-xl">
                      Key Insights for Hiring Decision
                    </h2>
                  </div>
                  <p className="text-gray-400 text-sm">
                    {keyInsights.length} critical patterns and hiring-relevant observations with
                    evidence-based implications
                  </p>
                </div>

                <div className="space-y-6">
                  {keyInsights.map((insight, idx) => (
                    <ExiqusCard
                      key={idx}
                      className="border-teal-500/20 bg-gradient-to-r from-teal-900/10 to-cyan-900/10 p-6"
                    >
                      <div className="flex items-start gap-4">
                        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-teal-600 to-cyan-600 font-semibold text-white shadow-lg">
                          {idx + 1}
                        </div>
                        <div className="flex-1 space-y-4">
                          <div className="flex items-start justify-between gap-4">
                            <h3 className="font-semibold text-teal-300 text-xl">{insight.title}</h3>
                            <div className="flex flex-shrink-0 items-center gap-2">
                              <span
                                className={`rounded-full px-3 py-1 font-medium text-xs capitalize ${
                                  insight.impact === 'positive'
                                    ? 'border border-green-500/20 bg-green-900/30 text-green-300'
                                    : insight.impact === 'negative'
                                      ? 'border border-red-500/20 bg-red-900/30 text-red-300'
                                      : 'border border-gray-500/20 bg-gray-900/30 text-gray-300'
                                }`}
                              >
                                {insight.impact}
                              </span>
                              <span className="rounded-full border border-purple-500/20 bg-purple-900/30 px-3 py-1 font-medium text-purple-300 text-xs capitalize">
                                {insight.category.replace('_', ' ')}
                              </span>
                            </div>
                          </div>

                          <p className="text-base text-gray-300 leading-relaxed">
                            {insight.description}
                          </p>

                          <div className="border-gray-700/50 border-t pt-3">
                            <p className="text-gray-400 text-sm">
                              <span className="font-semibold text-gray-300">Evidence:</span>{' '}
                              {insight.evidence}
                            </p>
                          </div>

                          <div className="rounded-lg border-teal-500 border-l-4 bg-gradient-to-r from-teal-900/30 to-transparent p-4">
                            <div className="flex items-start gap-2">
                              <Target className="mt-0.5 h-5 w-5 flex-shrink-0 text-teal-400" />
                              <div>
                                <p className="mb-1 font-semibold text-teal-300 text-xs uppercase tracking-wide">
                                  Hiring Implication
                                </p>
                                <p className="text-sm text-teal-100 leading-relaxed">
                                  {insight.hiring_implication}
                                </p>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </ExiqusCard>
                  ))}
                </div>
              </>
            ) : (
              <ExiqusCard className="p-8 text-center">
                <Lightbulb className="mx-auto mb-4 h-12 w-12 text-gray-600" />
                <p className="text-gray-400">No key insights available for this analysis.</p>
              </ExiqusCard>
            )}
          </TabsContent>

          {/* Evidence & Capabilities Tab */}
          <TabsContent value="evidence" className="space-y-6">
            {/* Nested Tabs for Evidence & Capabilities */}
            <Tabs
              value={activeEvidenceTab}
              onValueChange={setActiveEvidenceTab}
              className="space-y-6"
            >
              <TabsList className="grid w-full grid-cols-2 bg-white/[0.05] p-1 lg:grid-cols-4">
                <TabsTrigger
                  value="strengths"
                  className="text-xs data-[state=active]:bg-gradient-to-r data-[state=active]:from-emerald-600 data-[state=active]:to-green-600"
                >
                  <Star className="mr-1 h-3 w-3" />
                  Strengths
                </TabsTrigger>
                <TabsTrigger
                  value="technical"
                  className="text-xs data-[state=active]:bg-gradient-to-r data-[state=active]:from-purple-600 data-[state=active]:to-indigo-600"
                >
                  <Code2 className="mr-1 h-3 w-3" />
                  Technical
                </TabsTrigger>
                <TabsTrigger
                  value="collaboration"
                  className="text-xs data-[state=active]:bg-gradient-to-r data-[state=active]:from-cyan-600 data-[state=active]:to-blue-600"
                >
                  <Users className="mr-1 h-3 w-3" />
                  Collaboration
                </TabsTrigger>
                <TabsTrigger
                  value="context"
                  className="text-xs data-[state=active]:bg-gradient-to-r data-[state=active]:from-pink-600 data-[state=active]:to-orange-600"
                >
                  <Target className="mr-1 h-3 w-3" />
                  Context Fit
                </TabsTrigger>
              </TabsList>

              {/* Strengths Tab - Compact Grid Layout */}
              <TabsContent value="strengths" className="space-y-6">
                <div className="grid gap-6 lg:grid-cols-2">
                  {/* All Key Strengths */}
                  {keyStrengths.length > 0 && (
                    <ExiqusCard className="border-emerald-500/20 p-6">
                      <h3 className="mb-4 flex items-center gap-2 font-bold text-xl">
                        <Star className="h-6 w-6 text-emerald-400" />
                        Key Strengths ({keyStrengths.length})
                      </h3>
                      <div className="max-h-[600px] space-y-3 overflow-y-auto pr-2">
                        {keyStrengths.map((strength, idx) => {
                          const relatedQuestions = findRelatedQuestions(strength);
                          return (
                            <div
                              key={idx}
                              className="flex items-start gap-3 rounded-lg border border-emerald-500/20 bg-gradient-to-r from-emerald-900/20 to-transparent p-3"
                            >
                              <div className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-emerald-600 to-green-600 font-bold text-white text-xs">
                                {idx + 1}
                              </div>
                              <div className="min-w-0 flex-1">
                                <p className="text-gray-300 text-sm leading-relaxed">{strength}</p>
                                {relatedQuestions.length > 0 && (
                                  <div className="mt-1.5 flex items-center gap-2">
                                    <span className="text-gray-500 text-xs">Q:</span>
                                    <div className="flex gap-1">
                                      {relatedQuestions.slice(0, 2).map((q) => (
                                        <button
                                          type="button"
                                          key={q.index}
                                          onClick={() => {
                                            setActiveTab('interview');
                                            toast.success(`Navigating to question ${q.index}`);
                                          }}
                                          className="rounded border border-emerald-500/30 bg-emerald-600/20 px-1.5 py-0.5 text-emerald-300 text-xs transition-colors hover:bg-emerald-600/30"
                                        >
                                          {q.index}
                                        </button>
                                      ))}
                                      {relatedQuestions.length > 2 && (
                                        <span className="text-gray-500 text-xs">
                                          +{relatedQuestions.length - 2}
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </ExiqusCard>
                  )}

                  {/* Notable Contributions */}
                  {notableContributions.length > 0 && (
                    <ExiqusCard className="border-orange-500/20 p-6">
                      <h3 className="mb-4 flex items-center gap-2 font-bold text-xl">
                        <Award className="h-6 w-6 text-orange-400" />
                        Notable Contributions ({notableContributions.length})
                      </h3>
                      <div className="max-h-[600px] space-y-3 overflow-y-auto pr-2">
                        {notableContributions.map((contribution, idx) => (
                          <div
                            key={idx}
                            className="rounded-lg border border-orange-500/20 bg-gradient-to-r from-orange-900/20 to-transparent p-3"
                          >
                            <div className="flex items-start gap-3">
                              <div className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-orange-600 to-red-600 font-semibold text-white text-xs">
                                {idx + 1}
                              </div>
                              <p className="text-gray-300 text-sm leading-relaxed">
                                {contribution}
                              </p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </ExiqusCard>
                  )}
                </div>
              </TabsContent>

              {/* Technical Tab */}
              <TabsContent value="technical" className="space-y-6">
                {/* Technical Capabilities */}
                {technicalCapabilities.length > 0 && (
                  <ExiqusCard className="border-purple-500/20 p-6">
                    <h3 className="mb-4 flex items-center gap-2 font-bold text-xl">
                      <Code2 className="h-6 w-6 text-purple-400" />
                      Technical Capabilities ({technicalCapabilities.length})
                    </h3>
                    <p className="mb-4 text-gray-400 text-sm">
                      Specific technical skills demonstrated through PR contributions
                    </p>
                    <div className="grid gap-3 md:grid-cols-2">
                      {technicalCapabilities.map((capability, idx) => (
                        <div
                          key={idx}
                          className="flex items-start gap-3 rounded-lg border border-purple-500/20 bg-gradient-to-r from-purple-900/20 to-transparent p-3"
                        >
                          <Puzzle className="mt-0.5 h-5 w-5 flex-shrink-0 text-purple-400" />
                          <p className="text-gray-300 text-sm">{capability}</p>
                        </div>
                      ))}
                    </div>
                  </ExiqusCard>
                )}

                {/* Code Quality Indicators */}
                {codeQualityIndicators.length > 0 && (
                  <ExiqusCard className="border-indigo-500/20 p-6">
                    <h3 className="mb-4 flex items-center gap-2 font-bold text-xl">
                      <Shield className="h-6 w-6 text-indigo-400" />
                      Code Quality Indicators ({codeQualityIndicators.length})
                    </h3>
                    <p className="mb-4 text-gray-400 text-sm">
                      Quality patterns observed in their development practices
                    </p>
                    <div className="space-y-3">
                      {codeQualityIndicators.map((indicator, idx) => (
                        <div
                          key={idx}
                          className="flex items-start gap-3 rounded-lg border border-indigo-500/20 bg-gradient-to-r from-indigo-900/20 to-transparent p-3"
                        >
                          <CheckCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-indigo-400" />
                          <p className="text-gray-300 text-sm leading-relaxed">{indicator}</p>
                        </div>
                      ))}
                    </div>
                  </ExiqusCard>
                )}
              </TabsContent>

              {/* Collaboration Tab */}
              <TabsContent value="collaboration" className="space-y-6">
                {/* Collaboration Style */}
                {collaborationStyle.length > 0 && (
                  <ExiqusCard className="border-cyan-500/20 p-6">
                    <h3 className="mb-4 flex items-center gap-2 font-bold text-xl">
                      <Users className="h-6 w-6 text-cyan-400" />
                      Collaboration & Communication ({collaborationStyle.length})
                    </h3>
                    <p className="mb-4 text-gray-400 text-sm">
                      How they work with teams based on PR interaction patterns
                    </p>
                    <div className="space-y-3">
                      {collaborationStyle.map((style, idx) => (
                        <div
                          key={idx}
                          className="flex items-start gap-3 rounded-lg border border-cyan-500/20 bg-gradient-to-r from-cyan-900/20 to-transparent p-3"
                        >
                          <MessageSquare className="mt-0.5 h-5 w-5 flex-shrink-0 text-cyan-400" />
                          <p className="text-gray-300 text-sm leading-relaxed">{style}</p>
                        </div>
                      ))}
                    </div>
                  </ExiqusCard>
                )}
              </TabsContent>

              {/* Context Fit Tab */}
              <TabsContent value="context" className="space-y-6">
                {/* Context Fit Assessment */}
                {contextFit.alignment && (
                  <ExiqusCard className="border-cyan-500/20 p-6">
                    <h3 className="mb-4 flex items-center gap-2 font-bold text-xl">
                      <Target className="h-6 w-6 text-cyan-400" />
                      {formatContext(analysis.context)} Context Fit Assessment
                    </h3>

                    {/* Alignment Status */}
                    <div className="mb-6 rounded-lg border border-cyan-500/20 bg-gradient-to-r from-cyan-900/20 to-transparent p-4">
                      <div className="mb-2 flex items-center gap-2">
                        {contextFit.alignment === 'strong' && (
                          <CheckCircle className="h-5 w-5 text-emerald-400" />
                        )}
                        {contextFit.alignment === 'moderate' && (
                          <AlertCircle className="h-5 w-5 text-amber-400" />
                        )}
                        {contextFit.alignment === 'needs_discussion' && (
                          <Search className="h-5 w-5 text-orange-400" />
                        )}
                        <span className="font-medium text-cyan-300">
                          {contextFit.alignment === 'needs_discussion'
                            ? 'Requires Discussion'
                            : contextFit.alignment === 'strong'
                              ? 'Strong Alignment'
                              : contextFit.alignment === 'moderate'
                                ? 'Moderate Alignment'
                                : 'Assessment Pending'}
                        </span>
                      </div>
                    </div>

                    {/* Internal Tabs for Context Fit */}
                    <Tabs defaultValue="evidence" className="w-full">
                      <TabsList className="mb-6 grid w-full grid-cols-2 bg-white/[0.05] p-1 lg:grid-cols-4">
                        <TabsTrigger
                          value="evidence"
                          className="text-xs data-[state=active]:bg-gradient-to-r data-[state=active]:from-emerald-600 data-[state=active]:to-green-600"
                        >
                          <CheckCircle className="mr-1 h-3 w-3" />
                          Evidence
                        </TabsTrigger>
                        <TabsTrigger
                          value="considerations"
                          className="text-xs data-[state=active]:bg-gradient-to-r data-[state=active]:from-amber-600 data-[state=active]:to-orange-600"
                        >
                          <AlertCircle className="mr-1 h-3 w-3" />
                          Considerations
                        </TabsTrigger>
                        <TabsTrigger
                          value="validation"
                          className="text-xs data-[state=active]:bg-gradient-to-r data-[state=active]:from-orange-600 data-[state=active]:to-red-600"
                        >
                          <Search className="mr-1 h-3 w-3" />
                          Validation
                        </TabsTrigger>
                        <TabsTrigger
                          value="strengths"
                          className="text-xs data-[state=active]:bg-gradient-to-r data-[state=active]:from-teal-600 data-[state=active]:to-cyan-600"
                        >
                          <Star className="mr-1 h-3 w-3" />
                          Strengths
                        </TabsTrigger>
                      </TabsList>

                      {/* Supporting Evidence Tab */}
                      <TabsContent value="evidence">
                        {contextFit.supporting_evidence &&
                          contextFit.supporting_evidence.length > 0 && (
                            <div>
                              <div className="grid gap-3">
                                {contextFit.supporting_evidence.map((evidence, idx) => (
                                  <div
                                    key={idx}
                                    className="rounded-lg border border-emerald-500/20 bg-gradient-to-r from-emerald-900/20 to-transparent p-4"
                                  >
                                    <div className="flex items-start gap-3">
                                      <div className="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full border border-emerald-500/40 bg-emerald-600/30">
                                        <CheckCircle className="h-3 w-3 text-emerald-400" />
                                      </div>
                                      <p className="text-gray-300 text-sm leading-relaxed">
                                        {evidence}
                                      </p>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                      </TabsContent>

                      {/* Key Considerations Tab */}
                      <TabsContent value="considerations">
                        {contextFit.considerations && contextFit.considerations.length > 0 && (
                          <div className="grid gap-3">
                            {contextFit.considerations.map((consideration, idx) => (
                              <div
                                key={idx}
                                className="rounded-lg border border-amber-500/20 bg-gradient-to-r from-amber-900/20 to-transparent p-4"
                              >
                                <div className="flex items-start gap-3">
                                  <div className="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full border border-amber-500/40 bg-amber-600/30">
                                    <AlertCircle className="h-3 w-3 text-amber-400" />
                                  </div>
                                  <p className="text-gray-300 text-sm leading-relaxed">
                                    {consideration}
                                  </p>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </TabsContent>

                      {/* Needs Validation Tab */}
                      <TabsContent value="validation">
                        {contextFit.considerations && contextFit.considerations.length > 0 && (
                          <div>
                            <p className="mb-4 text-gray-400 text-sm">
                              Areas requiring deeper investigation during interview process:
                            </p>
                            <div className="grid gap-3">
                              {contextFit.considerations
                                .filter(
                                  (consideration) =>
                                    consideration.toLowerCase().includes('question') ||
                                    consideration.toLowerCase().includes('gap') ||
                                    consideration.toLowerCase().includes('limited') ||
                                    consideration.toLowerCase().includes('may not') ||
                                    consideration.toLowerCase().includes('suggests potential') ||
                                    consideration.toLowerCase().includes('raises questions')
                                )
                                .map((validation, idx) => (
                                  <div
                                    key={idx}
                                    className="rounded-lg border border-orange-500/20 bg-gradient-to-r from-orange-900/20 to-transparent p-4"
                                  >
                                    <div className="flex items-start gap-3">
                                      <div className="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full border border-orange-500/40 bg-orange-600/30">
                                        <Eye className="h-3 w-3 text-orange-400" />
                                      </div>
                                      <p className="text-gray-300 text-sm leading-relaxed">
                                        {validation}
                                      </p>
                                    </div>
                                  </div>
                                ))}
                              {/* Add general validation items if no specific ones found */}
                              {contextFit.considerations.filter(
                                (consideration) =>
                                  consideration.toLowerCase().includes('question') ||
                                  consideration.toLowerCase().includes('gap') ||
                                  consideration.toLowerCase().includes('limited') ||
                                  consideration.toLowerCase().includes('may not') ||
                                  consideration.toLowerCase().includes('suggests potential') ||
                                  consideration.toLowerCase().includes('raises questions')
                              ).length === 0 && (
                                <>
                                  <div className="rounded-lg border border-orange-500/20 bg-gradient-to-r from-orange-900/20 to-transparent p-4">
                                    <div className="flex items-start gap-3">
                                      <div className="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full border border-orange-500/40 bg-orange-600/30">
                                        <Eye className="h-3 w-3 text-orange-400" />
                                      </div>
                                      <p className="text-gray-300 text-sm leading-relaxed">
                                        Validate development practices during periods of low PR
                                        activity
                                      </p>
                                    </div>
                                  </div>
                                  <div className="rounded-lg border border-orange-500/20 bg-gradient-to-r from-orange-900/20 to-transparent p-4">
                                    <div className="flex items-start gap-3">
                                      <div className="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full border border-orange-500/40 bg-orange-600/30">
                                        <Eye className="h-3 w-3 text-orange-400" />
                                      </div>
                                      <p className="text-gray-300 text-sm leading-relaxed">
                                        Explore debugging and maintenance capabilities beyond
                                        feature development
                                      </p>
                                    </div>
                                  </div>
                                  <div className="rounded-lg border border-orange-500/20 bg-gradient-to-r from-orange-900/20 to-transparent p-4">
                                    <div className="flex items-start gap-3">
                                      <div className="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full border border-orange-500/40 bg-orange-600/30">
                                        <Eye className="h-3 w-3 text-orange-400" />
                                      </div>
                                      <p className="text-gray-300 text-sm leading-relaxed">
                                        Assess consistency patterns across larger sample of
                                        contributions
                                      </p>
                                    </div>
                                  </div>
                                </>
                              )}
                            </div>
                          </div>
                        )}
                      </TabsContent>

                      {/* Context-Specific Strengths Tab */}
                      <TabsContent value="strengths">
                        {contextFit.specific_strengths_for_context &&
                          contextFit.specific_strengths_for_context.length > 0 && (
                            <div className="grid gap-3">
                              {contextFit.specific_strengths_for_context.map((strength, idx) => (
                                <div
                                  key={idx}
                                  className="rounded-lg border border-teal-500/20 bg-gradient-to-r from-teal-900/20 to-transparent p-4"
                                >
                                  <div className="flex items-start gap-3">
                                    <div className="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full border border-teal-500/40 bg-teal-600/30">
                                      <Star className="h-3 w-3 text-teal-400" />
                                    </div>
                                    <p className="text-gray-300 text-sm leading-relaxed">
                                      {strength}
                                    </p>
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                      </TabsContent>
                    </Tabs>
                  </ExiqusCard>
                )}
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
                  Repository Context
                </h2>
              </div>

              {analysis.repositories_contributed && analysis.repositories_contributed.length > 0 ? (
                <>
                  <div className="mb-6 rounded-xl border border-pink-500/20 bg-gradient-to-r from-pink-900/20 to-rose-900/20 p-6">
                    <p className="text-gray-300 text-lg">
                      Contributed to{' '}
                      <span className="font-bold text-pink-300">
                        {analysis.repositories_contributed.length}
                      </span>{' '}
                      repositor{analysis.repositories_contributed.length !== 1 ? 'ies' : 'y'} over{' '}
                      <span className="font-bold text-pink-300">
                        {qualitySignals.contribution_timespan || 'unknown timespan'}
                      </span>
                    </p>
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    {analysis.repositories_contributed.map((repo, idx) => (
                      <a
                        key={idx}
                        href={`https://github.com/${repo}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="group block rounded-lg border border-pink-500/20 bg-gradient-to-r from-pink-900/20 to-transparent p-4 transition-all hover:border-pink-400/40 hover:bg-pink-900/30"
                      >
                        <div className="flex items-center gap-3">
                          <GitBranch className="h-5 w-5 flex-shrink-0 text-pink-400 transition-colors group-hover:text-pink-300" />
                          <span className="font-mono text-gray-200 text-sm transition-colors group-hover:text-pink-200">
                            {repo}
                          </span>
                        </div>
                      </a>
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

          {/* Interview Guide Tab with Nested Tabs */}
          <TabsContent value="interview" className="space-y-6">
            {/* Interview Overview */}
            <div className="mb-6 rounded-xl border border-purple-500/20 bg-gradient-to-r from-purple-900/20 to-pink-900/20 p-6">
              <div className="mb-3 flex items-center gap-3">
                <MessageSquare className="h-6 w-6 text-purple-400" />
                <h2 className="font-bold text-purple-300 text-xl">Interview Intelligence Guide</h2>
              </div>
              <p className="text-gray-400 text-sm">
                {areasForDiscussion.length} priority areas to investigate •{' '}
                {interviewQuestions.length} evidence-based questions for {analysis.context} context
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
                  Priority Areas ({areasForDiscussion.length})
                </TabsTrigger>
                <TabsTrigger
                  value="questions"
                  className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-purple-600 data-[state=active]:to-pink-600"
                >
                  <MessageSquare className="mr-2 h-4 w-4" />
                  Interview Framework ({interviewQuestions.length})
                </TabsTrigger>
              </TabsList>

              {/* Priority Investigation Areas Tab */}
              <TabsContent value="priority" className="space-y-6">
                {areasForDiscussion.length > 0 ? (
                  <ExiqusCard className="border-amber-500/20 p-6">
                    <h3 className="mb-4 flex items-center gap-2 font-bold text-xl">
                      <AlertCircle className="h-6 w-6 text-amber-400" />
                      Priority Investigation Areas
                    </h3>
                    <p className="mb-4 text-gray-400 text-sm">
                      High-priority questions to investigate based on gaps or concerns in the PR
                      evidence
                    </p>
                    <div className="space-y-4">
                      {areasForDiscussion.map((area, idx) => (
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
              <TabsContent value="questions" className="space-y-6" id="interview-questions">
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
                      <ExiqusCard className="border-purple-500/20 p-6">
                        <h3 className="mb-6 flex items-center gap-2 font-bold text-2xl">
                          <MessageSquare className="h-6 w-6 text-purple-400" />
                          Interview Framework ({interviewQuestions.length})
                        </h3>

                        {showCategoryTabs ? (
                          <Tabs
                            value={activeInterviewTab}
                            onValueChange={setActiveInterviewTab}
                            className="space-y-6"
                          >
                            <TabsList className="grid w-full grid-cols-5 bg-white/[0.05] p-1">
                              <TabsTrigger
                                value="all"
                                className="border border-purple-500/30 bg-purple-900/20 text-xs data-[state=active]:border-purple-500/50 data-[state=active]:bg-gradient-to-r data-[state=active]:from-purple-600 data-[state=active]:to-pink-600"
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
                                      'data-[state=active]:from-purple-600 data-[state=active]:to-pink-600',
                                  };
                                };

                                const colors = getCategoryColors(cat);
                                return (
                                  <TabsTrigger
                                    key={cat}
                                    value={cat}
                                    className={`border text-xs capitalize ${colors.inactive} data-[state=active]:border-opacity-50 data-[state=active]:bg-gradient-to-r ${colors.active} data-[state=active]:text-white`}
                                  >
                                    {cat} ({questionsByCategory[cat].length})
                                  </TabsTrigger>
                                );
                              })}
                            </TabsList>

                            <TabsContent value="all" className="space-y-4">
                              {interviewQuestions.map((q, idx) => (
                                <div
                                  key={idx}
                                  className="rounded-lg border border-purple-500/20 bg-gradient-to-r from-purple-900/20 to-transparent p-5"
                                >
                                  <div className="flex items-start gap-4">
                                    <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-purple-600 to-pink-600 font-semibold text-sm text-white">
                                      {idx + 1}
                                    </div>
                                    <div className="flex-1 space-y-4">
                                      {/* Main Question */}
                                      <div>
                                        <div className="mb-3 flex items-start justify-between">
                                          <h3 className="font-medium text-gray-100 text-lg leading-relaxed">
                                            {q.question}
                                          </h3>
                                          {q.category && (
                                            <span className="ml-4 flex-shrink-0 rounded-full border border-purple-500/20 bg-purple-900/30 px-3 py-1 text-purple-300 text-xs capitalize">
                                              {q.category}
                                            </span>
                                          )}
                                        </div>

                                        {/* Evidence Reference with Cross-Reference */}
                                        {q.evidence_reference && (
                                          <div className="mb-3 rounded-lg border border-indigo-500/20 bg-indigo-900/20 p-3">
                                            <div className="flex items-start justify-between gap-3">
                                              <div className="flex-1">
                                                <p className="text-indigo-300 text-sm">
                                                  <span className="font-medium">
                                                    Evidence Reference:
                                                  </span>{' '}
                                                  {q.evidence_reference}
                                                </p>
                                              </div>
                                              <button
                                                type="button"
                                                onClick={() => {
                                                  // Find matching evidence and navigate to it
                                                  const evidenceText =
                                                    q.evidence_reference?.toLowerCase() || '';

                                                  // Navigate to Evidence & Capabilities tab
                                                  setActiveTab('evidence');

                                                  // Determine which evidence tab to show based on content
                                                  if (
                                                    evidenceText.includes('technical') ||
                                                    evidenceText.includes('implementation') ||
                                                    evidenceText.includes('code')
                                                  ) {
                                                    setActiveEvidenceTab('technical');
                                                  } else if (
                                                    evidenceText.includes('collaboration') ||
                                                    evidenceText.includes('team') ||
                                                    evidenceText.includes('assigned')
                                                  ) {
                                                    setActiveEvidenceTab('collaboration');
                                                  } else if (
                                                    evidenceText.includes('strength') ||
                                                    evidenceText.includes('capability')
                                                  ) {
                                                    setActiveEvidenceTab('strengths');
                                                  } else if (
                                                    evidenceText.includes('context') ||
                                                    evidenceText.includes('startup') ||
                                                    evidenceText.includes('fit')
                                                  ) {
                                                    setActiveEvidenceTab('context');
                                                  } else {
                                                    setActiveEvidenceTab('strengths'); // default
                                                  }

                                                  // Show toast with navigation info
                                                  toast.success(
                                                    `Navigating to evidence: ${q.evidence_reference}`
                                                  );
                                                }}
                                                className="flex items-center gap-1 rounded-full border border-indigo-500/30 bg-indigo-600/20 px-3 py-1 text-indigo-300 text-xs transition-colors hover:bg-indigo-600/30"
                                              >
                                                <Search className="h-3 w-3" />
                                                View Evidence
                                              </button>
                                            </div>
                                          </div>
                                        )}

                                        {/* Context Note */}
                                        {q.context_note && (
                                          <div className="mb-3 rounded-lg border border-pink-500/20 bg-pink-900/20 p-3">
                                            <p className="text-pink-300 text-sm">
                                              <span className="font-medium">
                                                Context Intelligence:
                                              </span>{' '}
                                              {q.context_note}
                                            </p>
                                          </div>
                                        )}
                                      </div>

                                      {/* Follow-up Questions */}
                                      {q.follow_up_questions &&
                                        q.follow_up_questions.length > 0 && (
                                          <div className="border-purple-500/30 border-l-2 pl-4">
                                            <p className="mb-3 font-medium text-gray-400 text-sm">
                                              Follow-up questions:
                                            </p>
                                            <div className="space-y-2">
                                              {q.follow_up_questions.map((followUp, fIdx) => (
                                                <div
                                                  key={fIdx}
                                                  className="flex items-start gap-3 rounded-lg bg-white/[0.02] p-2"
                                                >
                                                  <ChevronRight className="mt-0.5 h-4 w-4 flex-shrink-0 text-purple-400" />
                                                  <span className="text-gray-300 text-sm">
                                                    {followUp}
                                                  </span>
                                                </div>
                                              ))}
                                            </div>
                                          </div>
                                        )}

                                      {/* Key Listening Points */}
                                      {q.key_listening_points && (
                                        <div className="rounded-lg border border-amber-500/20 bg-gradient-to-r from-amber-900/20 to-orange-900/20 p-4">
                                          <div className="flex items-start gap-2">
                                            <Lightbulb className="mt-0.5 h-5 w-5 flex-shrink-0 text-amber-400" />
                                            <div>
                                              <p className="mb-1 font-medium text-amber-300 text-sm">
                                                Key Intelligence Points:
                                              </p>
                                              <p className="text-gray-300 text-sm">
                                                {q.key_listening_points}
                                              </p>
                                            </div>
                                          </div>
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </TabsContent>

                            {/* Category-specific tabs */}
                            {categories.map((cat) => (
                              <TabsContent key={cat} value={cat} className="space-y-4">
                                {questionsByCategory[cat].map((q, idx) => (
                                  <div
                                    key={idx}
                                    className="rounded-lg border border-purple-500/20 bg-gradient-to-r from-purple-900/20 to-transparent p-5"
                                  >
                                    <div className="flex items-start gap-4">
                                      <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-purple-600 to-pink-600 font-semibold text-sm text-white">
                                        {idx + 1}
                                      </div>
                                      <div className="flex-1 space-y-4">
                                        {/* Main Question */}
                                        <div>
                                          <div className="mb-3 flex items-start justify-between">
                                            <h3 className="font-medium text-gray-100 text-lg leading-relaxed">
                                              {q.question}
                                            </h3>
                                            {q.category && (
                                              <span className="ml-4 flex-shrink-0 rounded-full border border-purple-500/20 bg-purple-900/30 px-3 py-1 text-purple-300 text-xs capitalize">
                                                {q.category}
                                              </span>
                                            )}
                                          </div>

                                          {/* Evidence Reference with Cross-Reference */}
                                          {q.evidence_reference && (
                                            <div className="mb-3 rounded-lg border border-indigo-500/20 bg-indigo-900/20 p-3">
                                              <div className="flex items-start justify-between gap-3">
                                                <div className="flex-1">
                                                  <p className="text-indigo-300 text-sm">
                                                    <span className="font-medium">
                                                      Evidence Reference:
                                                    </span>{' '}
                                                    {q.evidence_reference}
                                                  </p>
                                                </div>
                                                <button
                                                  type="button"
                                                  onClick={() => {
                                                    // Find matching evidence and navigate to it
                                                    const evidenceText =
                                                      q.evidence_reference?.toLowerCase() || '';

                                                    // Navigate to Evidence & Capabilities tab
                                                    setActiveTab('evidence');

                                                    // Determine which evidence tab to show based on content
                                                    if (
                                                      evidenceText.includes('technical') ||
                                                      evidenceText.includes('implementation') ||
                                                      evidenceText.includes('code')
                                                    ) {
                                                      setActiveEvidenceTab('technical');
                                                    } else if (
                                                      evidenceText.includes('collaboration') ||
                                                      evidenceText.includes('team') ||
                                                      evidenceText.includes('assigned')
                                                    ) {
                                                      setActiveEvidenceTab('collaboration');
                                                    } else if (
                                                      evidenceText.includes('strength') ||
                                                      evidenceText.includes('capability')
                                                    ) {
                                                      setActiveEvidenceTab('strengths');
                                                    } else if (
                                                      evidenceText.includes('context') ||
                                                      evidenceText.includes('startup') ||
                                                      evidenceText.includes('fit')
                                                    ) {
                                                      setActiveEvidenceTab('context');
                                                    } else {
                                                      setActiveEvidenceTab('strengths'); // default
                                                    }

                                                    // Show toast with navigation info
                                                    toast.success(
                                                      `Navigating to evidence: ${q.evidence_reference}`
                                                    );
                                                  }}
                                                  className="flex items-center gap-1 rounded-full border border-indigo-500/30 bg-indigo-600/20 px-3 py-1 text-indigo-300 text-xs transition-colors hover:bg-indigo-600/30"
                                                >
                                                  <Search className="h-3 w-3" />
                                                  View Evidence
                                                </button>
                                              </div>
                                            </div>
                                          )}

                                          {/* Context Note */}
                                          {q.context_note && (
                                            <div className="mb-3 rounded-lg border border-pink-500/20 bg-pink-900/20 p-3">
                                              <p className="text-pink-300 text-sm">
                                                <span className="font-medium">
                                                  Context Intelligence:
                                                </span>{' '}
                                                {q.context_note}
                                              </p>
                                            </div>
                                          )}
                                        </div>

                                        {/* Follow-up Questions */}
                                        {q.follow_up_questions &&
                                          q.follow_up_questions.length > 0 && (
                                            <div className="border-purple-500/30 border-l-2 pl-4">
                                              <p className="mb-3 font-medium text-gray-400 text-sm">
                                                Follow-up questions:
                                              </p>
                                              <div className="space-y-2">
                                                {q.follow_up_questions.map((followUp, fIdx) => (
                                                  <div
                                                    key={fIdx}
                                                    className="flex items-start gap-3 rounded-lg bg-white/[0.02] p-2"
                                                  >
                                                    <ChevronRight className="mt-0.5 h-4 w-4 flex-shrink-0 text-purple-400" />
                                                    <span className="text-gray-300 text-sm">
                                                      {followUp}
                                                    </span>
                                                  </div>
                                                ))}
                                              </div>
                                            </div>
                                          )}

                                        {/* Key Listening Points */}
                                        {q.key_listening_points && (
                                          <div className="rounded-lg border border-amber-500/20 bg-gradient-to-r from-amber-900/20 to-orange-900/20 p-4">
                                            <div className="flex items-start gap-2">
                                              <Lightbulb className="mt-0.5 h-5 w-5 flex-shrink-0 text-amber-400" />
                                              <div>
                                                <p className="mb-1 font-medium text-amber-300 text-sm">
                                                  Key Intelligence Points:
                                                </p>
                                                <p className="text-gray-300 text-sm">
                                                  {q.key_listening_points}
                                                </p>
                                              </div>
                                            </div>
                                          </div>
                                        )}
                                      </div>
                                    </div>
                                  </div>
                                ))}
                              </TabsContent>
                            ))}
                          </Tabs>
                        ) : (
                          <div className="space-y-4">
                            {interviewQuestions.map((q, idx) => (
                              <div
                                key={idx}
                                className="rounded-lg border border-purple-500/20 bg-gradient-to-r from-purple-900/20 to-transparent p-5"
                              >
                                <div className="flex items-start gap-4">
                                  <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-purple-600 to-pink-600 font-semibold text-sm text-white">
                                    {idx + 1}
                                  </div>
                                  <h3 className="font-medium text-gray-100 text-lg leading-relaxed">
                                    {q.question}
                                  </h3>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </ExiqusCard>
                    );
                  })()}

                {interviewQuestions.length === 0 && (
                  <ExiqusCard className="border-gray-500/20 p-8 text-center">
                    <MessageSquare className="mx-auto mb-4 h-12 w-12 text-gray-500" />
                    <h3 className="mb-2 font-medium text-gray-400 text-lg">
                      No Interview Questions Generated
                    </h3>
                    <p className="text-gray-500 text-sm">
                      AI insights may not be available for this analysis.
                    </p>
                  </ExiqusCard>
                )}
              </TabsContent>
            </Tabs>
          </TabsContent>

          {/* Assessment Scope Tab */}
          <TabsContent value="scope" className="space-y-6">
            <ExiqusCard className="border-yellow-500/20 bg-gradient-to-r from-yellow-900/20 to-orange-900/20 p-6">
              <div className="mb-6">
                <h3 className="mb-2 flex items-center gap-2 font-bold text-2xl">
                  <AlertCircle className="h-6 w-6 text-yellow-400" />
                  Assessment Scope & Limitations
                </h3>
                <p className="text-gray-400 text-sm">
                  Understanding what PR data can and cannot reveal about a candidate
                </p>
              </div>

              {/* What We Can Assess */}
              <div className="mb-8 rounded-lg border border-green-500/20 bg-gradient-to-r from-green-900/20 to-transparent p-6">
                <h4 className="mb-4 flex items-center gap-2 font-semibold text-green-300 text-lg">
                  <CheckCircle className="h-5 w-5" />
                  What We Can Assess from PR Data
                </h4>
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <p className="flex items-start gap-2 text-gray-300">
                      <span className="mt-1 text-green-400">✓</span>
                      <span>Technical implementation patterns and code organisation</span>
                    </p>
                    <p className="flex items-start gap-2 text-gray-300">
                      <span className="mt-1 text-green-400">✓</span>
                      <span>Collaboration through PR reviews and feedback incorporation</span>
                    </p>
                    <p className="flex items-start gap-2 text-gray-300">
                      <span className="mt-1 text-green-400">✓</span>
                      <span>Code quality indicators from review outcomes</span>
                    </p>
                    <p className="flex items-start gap-2 text-gray-300">
                      <span className="mt-1 text-green-400">✓</span>
                      <span>Contribution patterns and consistency over time</span>
                    </p>
                  </div>
                  <div className="space-y-2">
                    <p className="flex items-start gap-2 text-gray-300">
                      <span className="mt-1 text-green-400">✓</span>
                      <span>Feature vs fix contribution balance</span>
                    </p>
                    <p className="flex items-start gap-2 text-gray-300">
                      <span className="mt-1 text-green-400">✓</span>
                      <span>Cross-repository adaptability</span>
                    </p>
                    <p className="flex items-start gap-2 text-gray-300">
                      <span className="mt-1 text-green-400">✓</span>
                      <span>Response to code review feedback</span>
                    </p>
                    <p className="flex items-start gap-2 text-gray-300">
                      <span className="mt-1 text-green-400">✓</span>
                      <span>PR scope and complexity management</span>
                    </p>
                  </div>
                </div>
              </div>

              {/* Data Limitations */}
              {dataLimitations.length > 0 && (
                <div className="rounded-lg border border-yellow-500/20 bg-gradient-to-r from-yellow-900/20 to-transparent p-6">
                  <h4 className="mb-4 flex items-center gap-2 font-semibold text-lg text-yellow-300">
                    <XCircle className="h-5 w-5" />
                    What PR Data Cannot Assess ({dataLimitations.length})
                  </h4>
                  <p className="mb-4 text-gray-400 text-sm">
                    These important aspects require interview exploration and cannot be reliably
                    determined from PR history alone
                  </p>
                  <div className="space-y-3">
                    {dataLimitations.map((limitation, idx) => (
                      <div
                        key={idx}
                        className="flex items-start gap-3 rounded-lg bg-yellow-900/10 p-3"
                      >
                        <div className="mt-1 flex-shrink-0">
                          <div className="h-2 w-2 rounded-full bg-yellow-500"></div>
                        </div>
                        <p className="text-gray-300 leading-relaxed">{limitation}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Recommendation */}
              <div className="mt-6 rounded-lg border border-teal-500/20 bg-gradient-to-r from-teal-900/20 to-transparent p-4">
                <p className="text-sm text-teal-200">
                  <span className="font-semibold">Recommendation:</span> Use this analysis as a
                  foundation for targeted interview questions. Focus interviews on exploring the
                  limitations above while validating the observable patterns identified in the
                  evidence.
                </p>
              </div>
            </ExiqusCard>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
