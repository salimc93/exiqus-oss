// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import { format } from 'date-fns';
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  Brain,
  Briefcase,
  Bug,
  Calendar,
  CheckCircle,
  Clock,
  Code,
  Download,
  ExternalLink,
  GitBranch,
  Layers,
  Lock,
  MessageSquare,
  Package,
  Search,
  Share2,
  Shield,
  Sparkles,
  Target,
  TrendingUp,
  Users,
  Wrench,
  Zap,
} from 'lucide-react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';

import {
  ExiqusBadge,
  ExiqusButton,
  ExiqusCard,
  ExiqusEmptyState,
  ExiqusMetric,
  ExiqusSectionHeader,
  ExiqusTabs,
  GradientText,
} from '@/components/ui/exiqus-components';
import { Skeleton } from '@/components/ui/skeleton';
import { useAuth } from '@/contexts/auth-context';
import { useAuthGuard } from '@/hooks/use-auth-guard';
import { api } from '@/lib/api-client';
import type {
  AnalysisDetails,
  EvidencePatternModel,
  InsightModel,
  QuestionModel,
  RecommendationModel,
} from '@/types';
import {
  generateHTMLExport,
  generateMarkdownExport,
  generatePDFExport,
} from '@/utils/export-functions';

// Helper function to format duration in human-readable format
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

// Helper function to convert backend tier names to frontend display names
function getTierDisplayName(backendTier: string): string {
  const tierMapping: { [key: string]: string } = {
    free: 'Free',
    basic: 'Starter',
    professional: 'Growth',
    enterprise: 'Scale',
    scale_plus: 'Scale+',
  };
  return tierMapping[backendTier?.toLowerCase()] || backendTier;
}

export default function AnalysisDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const { user } = useAuth();
  const {
    isAuthenticated,
    isLoading: authLoading,
    showUnauthorized,
    UnauthorizedComponent,
  } = useAuthGuard();
  const [analysis, setAnalysis] = useState<AnalysisDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('insights');
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [candidateHubExists, setCandidateHubExists] = useState(false);
  const [candidateUsername, setCandidateUsername] = useState<string | null>(null);

  const fetchAnalysis = useCallback(async () => {
    try {
      const response = await api.getAnalysis(id as string);
      setAnalysis(response.data);

      // Check if candidate hub exists for this username
      // Try github_username field first, fallback to extracting from URL for old analyses
      let username = response.data.github_username;
      if (!username) {
        const match = response.data.repository_url.match(/github\.com\/([^/]+)/);
        username = match ? match[1] : null;
      }

      // Store the username for use in the button
      setCandidateUsername(username);

      if (username && user?.subscription_plan !== 'free') {
        try {
          const hubResponse = await api.getCandidateHub(username);
          // Hub exists if it has portfolio or PR data
          const hasData =
            hubResponse.data.portfolio_analysis !== null || hubResponse.data.pr_analysis !== null;
          setCandidateHubExists(hasData);
        } catch {
          // Hub doesn't exist or error fetching it
          setCandidateHubExists(false);
        }
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load analysis';
      toast.error(errorMessage);
      router.push('/dashboard');
    } finally {
      setLoading(false);
    }
  }, [id, router, user?.subscription_plan]);

  useEffect(() => {
    if (!authLoading && isAuthenticated && id) {
      fetchAnalysis();
    } else if (!authLoading && !isAuthenticated) {
      // User is not authenticated after loading
      setLoading(false);
    }
  }, [authLoading, isAuthenticated, id, fetchAnalysis]);

  const handleExport = async (exportFormat: 'json' | 'pdf' | 'html' | 'markdown') => {
    try {
      if (!analysis) return;

      // Close the dropdown after selection
      setShowExportMenu(false);

      const user = JSON.parse(localStorage.getItem('user') || '{}');

      if (exportFormat === 'json') {
        // Export only the analysis results visible to users
        const exportData = {
          repository: {
            name: analysis.repository_name,
            url: analysis.repository_url,
            context: analysis.context,
          },
          summary: analysisData.executive_summary,
          confidence_explanation: analysisData.confidence_explanation,
          insights: analysisData.insights,
          evidence_patterns: analysisData.evidence_patterns,
          questions: analysisData.questions,
          recommendations: analysisData.recommendations,
          positive_indicators: analysisData.green_flags,
          areas_to_explore: [...analysisData.red_flags, ...analysisData.areas_to_explore],
          limitations: analysisData.limitations,
          analyzed_at: analysis.created_at,
        };

        const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `analysis-${analysis.repository_name.replace('/', '-')}-${format(new Date(analysis.created_at), 'yyyy-MM-dd')}.json`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        toast.success('Analysis exported as JSON');
      } else if (exportFormat === 'html') {
        // Generate HTML export
        const htmlContent = generateHTMLExport(analysis, user);
        const blob = new Blob([htmlContent], { type: 'text/html' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `analysis-${analysis.repository_name.replace('/', '-')}-${format(new Date(analysis.created_at), 'yyyy-MM-dd')}.html`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        toast.success('Analysis exported as HTML');
      } else if (exportFormat === 'pdf') {
        // Generate a proper PDF-optimized HTML and open print dialog
        const pdfContent = generatePDFExport(analysis, user);
        const printWindow = window.open('', '_blank');
        if (printWindow) {
          printWindow.document.write(pdfContent);
          printWindow.document.close();
          printWindow.focus();
          setTimeout(() => {
            printWindow.print();
          }, 250);
        }
        toast.info('Opening print dialog for PDF export');
      } else if (exportFormat === 'markdown') {
        // Generate Markdown export
        const mdContent = generateMarkdownExport(analysis, user);
        const blob = new Blob([mdContent], { type: 'text/markdown' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `analysis-${analysis.repository_name.replace('/', '-')}-${format(new Date(analysis.created_at), 'yyyy-MM-dd')}.md`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        toast.success('Analysis exported as Markdown');
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to export analysis';
      toast.error(errorMessage);
    }
  };

  if (authLoading) {
    return <LoadingState />;
  }

  if (showUnauthorized && UnauthorizedComponent) {
    return <UnauthorizedComponent />;
  }

  if (loading) {
    return <LoadingState />;
  }

  if (!analysis) {
    return null;
  }

  // Type for raw analysis data from API
  interface RawAnalysisData {
    screening_insights?: {
      overall_impression?: string;
      confidence_explanation?: string;
      insights?: { insights?: InsightModel[] };
      interview_questions?: { all_questions?: QuestionModel[] };
      recommendations?: { all_recommendations?: RecommendationModel[] };
      areas_to_explore?: string[];
      data_limitations?: string[];
    };
    executive_summary?: string | { summary: string; recommendation: string };
    confidence_explanation?: string;
    subscription_tier?: string;
    insights?: InsightModel[];
    insights_count?: number;
    questions?: QuestionModel[];
    questions_count?: number;
    evidence_patterns?: EvidencePatternModel[];
    evidence_patterns_count?: number;
    recommendations?: RecommendationModel[];
    recommendations_count?: number;
    key_insights?: { green_flags?: string[]; red_flags?: string[] };
    green_flags?: string[];
    red_flags?: string[];
    areas_to_explore?: string[];
    limitations?: string[];
    data_limitations?: string[];
  }

  // Extract analysis data - handle both legacy and unified AI formats
  const rawAnalysisData = analysis.full_analysis.analysis as RawAnalysisData;
  const metadata = analysis.full_analysis.metadata;

  // For unified AI response, data is nested under screening_insights
  const screeningInsights = rawAnalysisData.screening_insights || {};

  // Extract the actual data, mapping from backend structure to frontend expectations
  const analysisData = {
    // Executive summary and basics - handle both object and string formats
    executive_summary: (() => {
      const execSummary = screeningInsights.overall_impression || rawAnalysisData.executive_summary;
      // Handle the case where executive_summary is an object with {summary, recommendation}
      if (typeof execSummary === 'object' && execSummary !== null && 'summary' in execSummary) {
        return `${execSummary.summary}\n\nRecommendation: ${execSummary.recommendation}`;
      }
      return execSummary || '';
    })(),
    confidence_explanation:
      screeningInsights.confidence_explanation || rawAnalysisData.confidence_explanation || '',
    subscription_tier: rawAnalysisData.subscription_tier || 'basic',

    // Insights from unified AI response
    insights: screeningInsights.insights?.insights || rawAnalysisData.insights || [],
    insights_count:
      screeningInsights.insights?.insights?.length || rawAnalysisData.insights_count || 0,

    // Questions from unified AI response
    questions:
      screeningInsights.interview_questions?.all_questions || rawAnalysisData.questions || [],
    questions_count:
      screeningInsights.interview_questions?.all_questions?.length ||
      rawAnalysisData.questions_count ||
      0,

    // Evidence patterns from API response (post-fix)
    evidence_patterns: rawAnalysisData.evidence_patterns || [],
    evidence_patterns_count: rawAnalysisData.evidence_patterns_count || 0,

    // Recommendations from unified AI response
    recommendations:
      screeningInsights.recommendations?.all_recommendations ||
      rawAnalysisData.recommendations ||
      [],
    recommendations_count:
      screeningInsights.recommendations?.all_recommendations?.length ||
      rawAnalysisData.recommendations_count ||
      0,

    // Flags from key_insights
    green_flags: rawAnalysisData.key_insights?.green_flags || rawAnalysisData.green_flags || [],
    red_flags: rawAnalysisData.key_insights?.red_flags || rawAnalysisData.red_flags || [],

    // Areas to explore from screening_insights or top level (filter out empty/placeholder items)
    areas_to_explore: (
      screeningInsights.areas_to_explore ||
      rawAnalysisData.areas_to_explore ||
      []
    ).filter((item: string) => item && item.trim() !== '' && item.trim() !== '--'),

    // Limitations
    limitations: rawAnalysisData.limitations || [],
    data_limitations: screeningInsights.data_limitations || rawAnalysisData.data_limitations || [],
  };

  // Update evidence patterns count
  analysisData.evidence_patterns_count = analysisData.evidence_patterns.length;

  const tabs = [
    { id: 'insights', label: 'Insights', icon: Brain },
    { id: 'evidence', label: 'Evidence', icon: Sparkles },
    { id: 'questions', label: 'Questions', icon: MessageSquare },
    { id: 'flags', label: 'Indicators', icon: Target },
    { id: 'actions', label: 'Actions', icon: TrendingUp },
  ];

  return (
    <div className="isolate min-h-screen bg-[#0A0A0A]" style={{ transform: 'translateZ(0)' }}>
      <div className="relative isolate z-0 mx-auto max-w-7xl px-6 py-8 lg:px-12">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <ExiqusButton
              variant="ghost"
              size="sm"
              onClick={() => {
                // If candidate hub exists and we have a username, go to hub
                if (candidateHubExists && candidateUsername) {
                  router.push(`/candidate-hub/${candidateUsername}`);
                } else {
                  // Otherwise always go to dashboard
                  router.push('/dashboard');
                }
              }}
              className="gap-2"
            >
              <ArrowLeft className="h-4 w-4" />
              {candidateHubExists && candidateUsername
                ? `Back to ${candidateUsername}'s Hub`
                : 'Back to Dashboard'}
            </ExiqusButton>
          </div>
          <div className="flex items-center gap-3">
            <div className="relative">
              <ExiqusButton
                variant="secondary"
                size="sm"
                className="gap-2"
                onClick={() => setShowExportMenu(!showExportMenu)}
              >
                <Download className="h-4 w-4" />
                Export
              </ExiqusButton>
              {showExportMenu && (
                <>
                  {/* Invisible overlay to close menu when clicking outside */}
                  <div className="fixed inset-0 z-20" onClick={() => setShowExportMenu(false)} />
                  <div className="absolute right-0 z-30 mt-1 w-48 origin-top-right divide-y divide-white/10 rounded-md bg-[#1a1a1a] shadow-lg ring-1 ring-white/10">
                    <div className="py-1">
                      <button
                        type="button"
                        onClick={() => handleExport('json')}
                        className="group flex w-full items-center px-4 py-2 text-gray-300 text-sm hover:bg-white/10"
                      >
                        JSON (All Tiers)
                      </button>
                      {/* HTML and PDF available for Starter and above */}
                      {(() => {
                        const plan = user?.subscription_plan;
                        return (
                          <>
                            {plan &&
                              ['starter', 'growth', 'scale', 'scale_plus'].includes(plan) && (
                                <>
                                  <button
                                    type="button"
                                    onClick={() => handleExport('html')}
                                    className="group flex w-full items-center px-4 py-2 text-gray-300 text-sm hover:bg-white/10"
                                  >
                                    HTML
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => handleExport('pdf')}
                                    className="group flex w-full items-center px-4 py-2 text-gray-300 text-sm hover:bg-white/10"
                                  >
                                    PDF
                                  </button>
                                </>
                              )}
                            {/* Markdown only for Scale and Scale+ */}
                            {plan && ['scale', 'scale_plus'].includes(plan) && (
                              <button
                                type="button"
                                onClick={() => handleExport('markdown')}
                                className="group flex w-full items-center px-4 py-2 text-gray-300 text-sm hover:bg-white/10"
                              >
                                Markdown
                              </button>
                            )}
                          </>
                        );
                      })()}
                    </div>
                  </div>
                </>
              )}
            </div>
            <ExiqusButton
              variant="secondary"
              size="sm"
              onClick={() => toast.info('Share functionality coming soon')}
            >
              <Share2 className="mr-2 h-4 w-4" />
              Share
            </ExiqusButton>
          </div>
        </div>

        {/* Repository Header */}
        <div className="mb-8">
          <div className="flex items-start justify-between">
            <div>
              <div className="mb-2 flex items-center gap-3">
                <div className="rounded-xl bg-white/[0.06] p-3">
                  <GitBranch className="h-6 w-6 text-purple-400" />
                </div>
                <h1 className="font-bold text-3xl">
                  <GradientText>{analysis.repository_name}</GradientText>
                </h1>
              </div>
              <div className="ml-[60px] flex items-center gap-6 text-gray-400 text-sm">
                <span className="flex items-center gap-2">
                  <Calendar className="h-4 w-4" />
                  {format(new Date(analysis.created_at), 'PPP')}
                </span>
                <span className="flex items-center gap-2">
                  <Clock className="h-4 w-4" />
                  {metadata.response_time_seconds
                    ? formatDuration(metadata.response_time_seconds)
                    : 'N/A'}
                </span>
                <span className="flex items-center gap-2">
                  <Target className="h-4 w-4" />
                  {analysis.context} context
                </span>
              </div>
            </div>
            <Link
              href={analysis.repository_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 rounded-lg bg-white/[0.06] px-4 py-2 font-medium text-sm transition-all hover:bg-white/[0.09]"
            >
              View on GitHub
              <ExternalLink className="h-4 w-4" />
            </Link>
          </div>
        </div>

        {/* Dynamic Metrics */}
        <div className="mb-12 grid grid-cols-2 gap-6 md:grid-cols-4">
          <ExiqusMetric
            label="Key insights"
            value={analysisData.insights_count || 0}
            icon={Brain}
            color="purple"
            onClick={() => {
              setActiveTab('insights');
              // Scroll to tabs section smoothly
              setTimeout(() => {
                const tabsElement = document.getElementById('analysis-tabs');
                if (tabsElement) {
                  tabsElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
              }, 100);
            }}
          />
          <ExiqusMetric
            label="Evidence patterns"
            value={analysisData.evidence_patterns_count || 0}
            icon={Sparkles}
            color="blue"
            onClick={() => {
              setActiveTab('evidence');
              // Scroll to tabs section smoothly
              setTimeout(() => {
                const tabsElement = document.getElementById('analysis-tabs');
                if (tabsElement) {
                  tabsElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
              }, 100);
            }}
          />
          <ExiqusMetric
            label="Interview questions"
            value={analysisData.questions_count || 0}
            icon={MessageSquare}
            color="amber"
            onClick={() => {
              setActiveTab('questions');
              // Scroll to tabs section smoothly
              setTimeout(() => {
                const tabsElement = document.getElementById('analysis-tabs');
                if (tabsElement) {
                  tabsElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
              }, 100);
            }}
          />
          <ExiqusMetric
            label="Actions"
            value={analysisData.recommendations_count || 0}
            icon={TrendingUp}
            color="green"
            onClick={() => {
              setActiveTab('actions');
              // Scroll to tabs section smoothly
              setTimeout(() => {
                const tabsElement = document.getElementById('analysis-tabs');
                if (tabsElement) {
                  tabsElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
              }, 100);
            }}
          />
        </div>

        {/* Executive Summary */}
        <ExiqusCard className="relative isolate z-10 mb-12 overflow-hidden">
          <div
            className="relative isolate z-10 bg-gradient-to-br from-purple-500/10 via-blue-500/10 to-purple-500/10 p-8"
            style={{ transform: 'translateZ(0)' }}
          >
            <ExiqusSectionHeader
              title="Executive Summary"
              description="AI-powered analysis of repository patterns and practices"
              icon={Briefcase}
              action={
                metadata.ai_analysis_used && (
                  <ExiqusBadge
                    variant="info"
                    className="relative isolate z-10 bg-gradient-to-r from-purple-500/20 to-blue-500/20"
                  >
                    <Zap className="mr-1 h-3 w-3" />
                    AI Enhanced
                  </ExiqusBadge>
                )
              }
            />
            <div className="mt-8 space-y-6">
              <div className="text-gray-100 text-lg leading-relaxed">
                <p className="whitespace-pre-wrap">{analysisData.executive_summary}</p>
              </div>
              {analysisData.confidence_explanation && (
                <div
                  className="relative isolate z-10 mt-6 rounded-xl border border-amber-500/20 bg-gradient-to-r from-amber-500/10 to-orange-500/10 p-6"
                  style={{ transform: 'translateZ(0)' }}
                >
                  <div className="flex items-start gap-3">
                    <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-amber-400" />
                    <div className="w-full">
                      <p className="mb-3 font-semibold text-amber-300 text-sm">
                        Evidence Quality Assessment
                      </p>
                      <p className="whitespace-pre-wrap text-gray-300 text-sm leading-relaxed">
                        {analysisData.confidence_explanation}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </ExiqusCard>

        {/* Tabs */}
        <div id="analysis-tabs" className="relative isolate z-20 mb-8">
          <ExiqusTabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />
        </div>

        {/* Tab Content */}
        <div className="relative isolate z-10 space-y-6">
          {activeTab === 'insights' && <InsightsTab data={analysisData.insights} />}
          {activeTab === 'evidence' && <EvidenceTab data={analysisData.evidence_patterns} />}
          {activeTab === 'questions' && (
            <QuestionsTab
              data={analysisData.questions}
              tier={analysisData.subscription_tier || 'professional'}
            />
          )}
          {activeTab === 'flags' && (
            <FlagsTab
              greenFlags={analysisData.green_flags}
              redFlags={analysisData.red_flags}
              areasToExplore={analysisData.areas_to_explore}
            />
          )}
          {activeTab === 'actions' && <ActionsTab data={analysisData.recommendations} />}
        </div>

        {/* Limitations Footer */}
        {(analysisData.limitations?.length > 0 || analysisData.data_limitations?.length > 0) && (
          <ExiqusCard className="mt-12 border-dashed p-6">
            <h3 className="mb-4 flex items-center gap-2 font-semibold text-lg">
              <AlertCircle className="h-5 w-5 text-amber-400" />
              Analysis Limitations
            </h3>
            <div className="space-y-4">
              {analysisData.limitations?.length > 0 && (
                <div>
                  <p className="mb-2 font-medium text-gray-300 text-sm">General Limitations</p>
                  <ul className="space-y-1">
                    {analysisData.limitations.map((limitation: string, index: number) => (
                      <li key={index} className="flex items-start gap-2 text-gray-400 text-sm">
                        <span className="mt-0.5 text-amber-400">•</span>
                        {limitation}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {analysisData.data_limitations?.length > 0 && (
                <div>
                  <p className="mb-2 font-medium text-gray-300 text-sm">Data Limitations</p>
                  <ul className="space-y-1">
                    {analysisData.data_limitations.map((limitation: string, index: number) => (
                      <li key={index} className="flex items-start gap-2 text-gray-400 text-sm">
                        <span className="mt-0.5 text-amber-400">•</span>
                        {limitation}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </ExiqusCard>
        )}
      </div>
    </div>
  );
}

// Tab Components
function InsightsTab({ data }: { data: InsightModel[] }) {
  if (!data || data.length === 0) {
    return (
      <ExiqusEmptyState
        icon={Brain}
        title="No insights available"
        description="This analysis did not generate any insights"
      />
    );
  }

  // Helper function to format evidence for better readability
  const formatEvidence = (evidence: string): React.ReactNode => {
    // Check if this is a ratio/fraction pattern - improved regex to capture full text
    const ratioMatch = evidence.match(
      /(\d+)\s+([^\d]+?)\s+for\s+(\d+)\s+([^(]+?)(?:\s*\(ratio of ([\d.]+)\))?$/
    );
    if (ratioMatch) {
      const [, numerator, numeratorLabel, denominator, denominatorLabel, ratio] = ratioMatch;
      // Clean up labels
      const cleanNumeratorLabel = numeratorLabel.trim();
      const cleanDenominatorLabel = denominatorLabel.trim();
      const percentage = ratio
        ? (parseFloat(ratio) * 100).toFixed(0)
        : ((parseInt(numerator) / parseInt(denominator)) * 100).toFixed(0);

      return (
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="font-medium text-gray-200">{numerator}</span>
            <span className="text-gray-400">{cleanNumeratorLabel}</span>
            <span className="text-gray-500">out of</span>
            <span className="font-medium text-gray-200">{denominator}</span>
            <span className="text-gray-400">{cleanDenominatorLabel}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-2 w-32 overflow-hidden rounded-full bg-white/[0.06]">
              <div
                className="h-full bg-gradient-to-r from-purple-500 to-blue-500"
                style={{ width: `${percentage}%` }}
              />
            </div>
            <span className="font-medium text-gray-300 text-sm">{percentage}%</span>
          </div>
        </div>
      );
    }

    // Check for percentage patterns
    const percentMatch = evidence.match(/(\d+(?:\.\d+)?)\s*%/);
    if (percentMatch) {
      return <span>{evidence}</span>;
    }

    return evidence;
  };

  return (
    <div className="grid gap-6">
      {data.map((insight, index) => {
        const impactIcon =
          insight.impact === 'positive'
            ? CheckCircle
            : insight.impact === 'concerning'
              ? AlertCircle
              : Zap;
        const ImpactIcon = impactIcon;

        return (
          <ExiqusCard
            key={index}
            className={`overflow-hidden ${
              insight.confidence === 'high'
                ? 'border-emerald-500/50 border-l-4'
                : insight.confidence === 'medium'
                  ? 'border-amber-500/50 border-l-4'
                  : insight.confidence === 'low'
                    ? 'border-red-500/50 border-l-4'
                    : ''
            }`}
          >
            <div
              className={`p-6 ${
                insight.confidence === 'high'
                  ? 'bg-gradient-to-br from-emerald-500/10 to-green-500/10'
                  : insight.confidence === 'medium'
                    ? 'bg-gradient-to-br from-amber-500/10 to-orange-500/10'
                    : insight.impact === 'positive'
                      ? 'bg-gradient-to-br from-green-500/5 to-emerald-500/5'
                      : insight.impact === 'concerning'
                        ? 'bg-gradient-to-br from-amber-500/5 to-orange-500/5'
                        : 'bg-gradient-to-br from-gray-500/5 to-gray-600/5'
              }`}
            >
              <div className="space-y-4">
                {/* Header */}
                <div className="flex items-start justify-between gap-4">
                  <div className="flex flex-1 items-start gap-4">
                    <div
                      className={`rounded-lg p-3 ${
                        insight.impact === 'positive'
                          ? 'bg-green-500/10'
                          : insight.impact === 'concerning'
                            ? 'bg-amber-500/10'
                            : 'bg-gray-500/10'
                      }`}
                    >
                      <ImpactIcon
                        className={`h-6 w-6 ${
                          insight.impact === 'positive'
                            ? 'text-green-400'
                            : insight.impact === 'concerning'
                              ? 'text-amber-400'
                              : 'text-gray-400'
                        }`}
                      />
                    </div>
                    <div className="flex-1">
                      <h3 className="font-semibold text-gray-100 text-lg leading-tight">
                        {insight.description}
                      </h3>
                    </div>
                  </div>
                  <ExiqusBadge
                    variant={
                      insight.confidence === 'high'
                        ? 'success'
                        : insight.confidence === 'medium'
                          ? 'warning'
                          : 'default'
                    }
                    className="shrink-0"
                  >
                    {insight.confidence} confidence
                  </ExiqusBadge>
                </div>

                {/* Evidence */}
                {insight.evidence && insight.evidence.length > 0 && (
                  <div className="ml-[60px] space-y-3">
                    <p className="font-semibold text-gray-400 text-xs uppercase tracking-wider">
                      Supporting Evidence
                    </p>
                    <div className="space-y-3">
                      {insight.evidence.map((evidence: string, evidenceIndex: number) => (
                        <div
                          key={evidenceIndex}
                          className="flex items-start gap-3 rounded-lg bg-white/[0.03] p-3"
                        >
                          <span className="mt-0.5 text-purple-400">•</span>
                          <div className="flex-1 text-gray-300 text-sm">
                            {formatEvidence(evidence)}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Metadata */}
                <div className="ml-[60px] flex items-center gap-3 pt-2">
                  <ExiqusBadge variant="default" className="text-xs">
                    {insight.category?.replace(/_/g, ' ')}
                  </ExiqusBadge>
                  {insight.impact && (
                    <ExiqusBadge
                      variant={
                        insight.impact === 'positive'
                          ? 'success'
                          : insight.impact === 'concerning'
                            ? 'warning'
                            : 'default'
                      }
                      className="text-xs"
                    >
                      {insight.impact}
                    </ExiqusBadge>
                  )}
                </div>
              </div>
            </div>
          </ExiqusCard>
        );
      })}
    </div>
  );
}

function EvidenceTab({ data }: { data: EvidencePatternModel[] }) {
  if (!data || data.length === 0) {
    return (
      <ExiqusEmptyState
        icon={Sparkles}
        title="No evidence patterns found"
        description="Unable to extract evidence patterns from this repository"
      />
    );
  }

  // Clean and consolidate patterns - merge duplicates and improve titles
  const cleanedData = data.reduce((acc, pattern) => {
    // Normalize pattern type and category
    const normalizedType = pattern.pattern_type?.toLowerCase() || 'other';
    const normalizedCategory = pattern.category?.toLowerCase() || 'general';

    // Create a unique key to detect duplicates
    const key = `${normalizedType}-${normalizedCategory}-${pattern.name?.toLowerCase()}`;

    // Skip if we already have this pattern or if it's too generic
    if (
      acc.some(
        (p) =>
          `${p.pattern_type?.toLowerCase()}-${p.category?.toLowerCase()}-${p.name?.toLowerCase()}` ===
          key
      ) ||
      pattern.name === 'Growth Pattern' ||
      pattern.name === 'Technical Pattern' ||
      pattern.name === 'Professional Pattern'
    ) {
      return acc;
    }

    // Use the AI-generated pattern name directly - don't override it!
    // The AI is trained to provide specific, unique pattern names
    // Only clean up if it ends with generic 'Pattern' suffix
    let cleanedName = pattern.name;
    if (pattern.name?.endsWith(' Pattern') && pattern.name !== 'Pattern') {
      cleanedName = pattern.name.replace(' Pattern', '');
    }

    acc.push({
      ...pattern,
      name: cleanedName || pattern.name, // Fallback to original if cleaning fails
      pattern_type: normalizedType,
      category: normalizedCategory,
    });

    return acc;
  }, [] as EvidencePatternModel[]);

  // Group patterns by type
  const groupedPatterns = cleanedData.reduce(
    (acc, pattern) => {
      const type = pattern.pattern_type || 'other';
      if (!acc[type]) acc[type] = [];
      acc[type].push(pattern);
      return acc;
    },
    {} as Record<string, EvidencePatternModel[]>
  );

  const typeConfig = {
    technical: {
      icon: Zap,
      color: 'purple',
      label: 'Technical Expertise',
      bgGradient: 'from-purple-900/20 via-purple-800/10 to-purple-900/20',
      borderColor: 'border-purple-500/30',
    },
    behavioral: {
      icon: Users,
      color: 'pink',
      label: 'Work Patterns',
      bgGradient: 'from-pink-900/20 via-pink-800/10 to-pink-900/20',
      borderColor: 'border-pink-500/30',
    },
    collaboration: {
      icon: Users,
      color: 'blue',
      label: 'Team Collaboration',
      bgGradient: 'from-blue-900/20 via-blue-800/10 to-blue-900/20',
      borderColor: 'border-blue-500/30',
    },
    quality: {
      icon: CheckCircle,
      color: 'green',
      label: 'Quality Indicators',
      bgGradient: 'from-green-900/20 via-green-800/10 to-green-900/20',
      borderColor: 'border-green-500/30',
    },
    security: {
      icon: Shield,
      color: 'amber',
      label: 'Security Practices',
      bgGradient: 'from-amber-900/20 via-amber-800/10 to-amber-900/20',
      borderColor: 'border-amber-500/30',
    },
    professional: {
      icon: Briefcase,
      color: 'indigo',
      label: 'Professional Practices',
      bgGradient: 'from-indigo-900/20 via-indigo-800/10 to-indigo-900/20',
      borderColor: 'border-indigo-500/30',
    },
    communication: {
      icon: MessageSquare,
      color: 'teal',
      label: 'Communication Skills',
      bgGradient: 'from-teal-900/20 via-teal-800/10 to-teal-900/20',
      borderColor: 'border-teal-500/30',
    },
    growth: {
      icon: TrendingUp,
      color: 'emerald',
      label: 'Learning & Growth',
      bgGradient: 'from-emerald-900/20 via-emerald-800/10 to-emerald-900/20',
      borderColor: 'border-emerald-500/30',
    },
    other: {
      icon: Sparkles,
      color: 'gray',
      label: 'Additional Insights',
      bgGradient: 'from-gray-500/10 via-slate-500/5 to-gray-500/10',
      borderColor: 'border-gray-500/30',
    },
  };

  return (
    <div className="relative isolate z-10 space-y-8" style={{ transform: 'translateZ(0)' }}>
      {Object.entries(groupedPatterns).map(([type, patterns]) => {
        const config = typeConfig[type as keyof typeof typeConfig] || typeConfig.other;
        const Icon = config.icon;

        return (
          <section
            key={type}
            className="relative isolate z-10"
            style={{ transform: 'translateZ(0)' }}
          >
            <ExiqusCard className={`relative isolate z-10 overflow-hidden ${config.borderColor}`}>
              <div
                className={`relative isolate z-10 bg-gradient-to-br ${config.bgGradient} p-6`}
                style={{ willChange: 'transform' }}
              >
                {/* Section Header */}
                <div className="mb-6 flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className={`rounded-xl bg-${config.color}-500/10 p-3`}>
                      <Icon className={`h-6 w-6 text-${config.color}-400`} />
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-100 text-xl">{config.label}</h3>
                      <p className="mt-1 text-gray-400 text-sm">
                        Observable patterns from repository analysis
                      </p>
                    </div>
                  </div>
                  <ExiqusBadge
                    variant={
                      config.color === 'green'
                        ? 'success'
                        : config.color === 'amber'
                          ? 'warning'
                          : config.color === 'purple'
                            ? 'info'
                            : 'default'
                    }
                    className="border-white/20 bg-white/10"
                  >
                    {patterns.length} pattern{patterns.length !== 1 ? 's' : ''}
                  </ExiqusBadge>
                </div>

                {/* Pattern Cards */}
                <div className="grid gap-4">
                  {patterns.map((pattern, index) => {
                    // Check if this is a locked pattern
                    const isLocked = pattern.tier_locked === true;

                    // Skip showing insight/context if they're identical to avoid redundancy
                    const showInsight =
                      !isLocked &&
                      pattern.insight &&
                      pattern.insight !== pattern.evidence &&
                      pattern.insight !== pattern.context;
                    const showContext =
                      !isLocked &&
                      pattern.context &&
                      pattern.context !== pattern.insight &&
                      pattern.context !== pattern.evidence &&
                      !pattern.context.includes('Observable pattern in') && // Skip generic context
                      pattern.context.length > 10;

                    // Get pattern-specific styling based on the pattern name
                    const patternName = pattern.name?.toLowerCase() || '';
                    let patternStyle = {
                      gradient: config.bgGradient,
                      border: config.borderColor,
                      iconBg: `bg-${config.color}-500/20`,
                      iconColor: `text-${config.color}-400`,
                      evidenceBg: 'border-white/10 bg-white/5',
                      headerBg: 'bg-gradient-to-r from-transparent to-white/5',
                    };

                    // Override with specific pattern colors
                    if (patternName.includes('bug') || patternName.includes('fix')) {
                      patternStyle = {
                        gradient: 'from-red-900/30 via-red-800/10 to-rose-900/20',
                        border: 'border-red-500/40',
                        iconBg: 'bg-red-500/25',
                        iconColor: 'text-red-400',
                        evidenceBg: 'border-red-400/20 bg-red-900/10',
                        headerBg: 'bg-gradient-to-r from-transparent to-red-500/10',
                      };
                    } else if (patternName.includes('test') || patternName.includes('coverage')) {
                      patternStyle = {
                        gradient: 'from-green-900/30 via-green-800/10 to-emerald-900/20',
                        border: 'border-green-500/40',
                        iconBg: 'bg-green-500/25',
                        iconColor: 'text-green-400',
                        evidenceBg: 'border-green-400/20 bg-green-900/10',
                        headerBg: 'bg-gradient-to-r from-transparent to-green-500/10',
                      };
                    } else if (patternName.includes('refactor')) {
                      patternStyle = {
                        gradient: 'from-blue-900/30 via-blue-800/10 to-sky-900/20',
                        border: 'border-blue-500/40',
                        iconBg: 'bg-blue-500/25',
                        iconColor: 'text-blue-400',
                        evidenceBg: 'border-blue-400/20 bg-blue-900/10',
                        headerBg: 'bg-gradient-to-r from-transparent to-blue-500/10',
                      };
                    } else if (
                      patternName.includes('ci') ||
                      patternName.includes('cd') ||
                      patternName.includes('pipeline')
                    ) {
                      patternStyle = {
                        gradient: 'from-purple-900/30 via-purple-800/10 to-violet-900/20',
                        border: 'border-purple-500/40',
                        iconBg: 'bg-purple-500/25',
                        iconColor: 'text-purple-400',
                        evidenceBg: 'border-purple-400/20 bg-purple-900/10',
                        headerBg: 'bg-gradient-to-r from-transparent to-purple-500/10',
                      };
                    } else if (patternName.includes('document')) {
                      patternStyle = {
                        gradient: 'from-indigo-900/30 via-indigo-800/10 to-blue-900/20',
                        border: 'border-indigo-500/40',
                        iconBg: 'bg-indigo-500/25',
                        iconColor: 'text-indigo-400',
                        evidenceBg: 'border-indigo-400/20 bg-indigo-900/10',
                        headerBg: 'bg-gradient-to-r from-transparent to-indigo-500/10',
                      };
                    } else if (patternName.includes('security')) {
                      patternStyle = {
                        gradient: 'from-amber-900/30 via-amber-800/10 to-yellow-900/20',
                        border: 'border-amber-500/40',
                        iconBg: 'bg-amber-500/25',
                        iconColor: 'text-amber-400',
                        evidenceBg: 'border-amber-400/20 bg-amber-900/10',
                        headerBg: 'bg-gradient-to-r from-transparent to-amber-500/10',
                      };
                    } else if (
                      patternName.includes('architecture') ||
                      patternName.includes('complex')
                    ) {
                      patternStyle = {
                        gradient: 'from-slate-800/30 via-slate-700/10 to-gray-800/20',
                        border: 'border-slate-500/40',
                        iconBg: 'bg-slate-500/25',
                        iconColor: 'text-slate-400',
                        evidenceBg: 'border-slate-400/20 bg-slate-900/10',
                        headerBg: 'bg-gradient-to-r from-transparent to-slate-500/10',
                      };
                    } else if (
                      patternName.includes('language') ||
                      patternName.includes('integration')
                    ) {
                      patternStyle = {
                        gradient: 'from-cyan-900/30 via-cyan-800/10 to-teal-900/20',
                        border: 'border-cyan-500/40',
                        iconBg: 'bg-cyan-500/25',
                        iconColor: 'text-cyan-400',
                        evidenceBg: 'border-cyan-400/20 bg-cyan-900/10',
                        headerBg: 'bg-gradient-to-r from-transparent to-cyan-500/10',
                      };
                    }

                    return (
                      <div
                        key={index}
                        className={`group relative isolate z-10 rounded-xl border ${isLocked ? 'border-amber-500/50' : patternStyle.border} bg-gradient-to-br ${isLocked ? 'from-amber-500/5 via-orange-500/5 to-amber-500/5' : patternStyle.gradient} p-6 shadow-lg transition-all duration-300 hover:shadow-xl ${isLocked ? 'overflow-hidden' : ''}`}
                        style={{ transform: 'translateZ(0)' }}
                      >
                        {/* Locked Pattern Overlay Effect */}
                        {isLocked && (
                          <div className="pointer-events-none absolute inset-0 isolate z-10 bg-gradient-to-t from-amber-500/10 via-transparent to-transparent" />
                        )}

                        {/* Pattern header background gradient */}
                        <div
                          className={`absolute inset-x-0 top-0 isolate z-10 h-24 ${patternStyle.headerBg} pointer-events-none`}
                        />

                        <div className="relative space-y-4">
                          {/* Pattern Header */}
                          <div className="flex items-center justify-between gap-4">
                            <div className="flex items-center gap-3">
                              <div
                                className={`rounded-lg ${isLocked ? 'bg-amber-500/20' : patternStyle.iconBg} p-2 shadow-sm`}
                              >
                                {isLocked ? (
                                  <Lock className="h-5 w-5 text-amber-400" />
                                ) : (
                                  <Icon className={`h-5 w-5 ${patternStyle.iconColor}`} />
                                )}
                              </div>
                              <h4 className="font-semibold text-gray-100 text-lg">
                                {pattern.name}
                              </h4>
                            </div>
                            {isLocked && pattern.required_tier ? (
                              <ExiqusBadge variant="warning" className="text-xs uppercase">
                                {getTierDisplayName(pattern.required_tier)} tier
                              </ExiqusBadge>
                            ) : (
                              <ExiqusBadge
                                variant={
                                  config.color === 'green'
                                    ? 'success'
                                    : config.color === 'amber'
                                      ? 'warning'
                                      : config.color === 'purple'
                                        ? 'info'
                                        : 'default'
                                }
                                className="text-xs"
                              >
                                {pattern.category}
                              </ExiqusBadge>
                            )}
                          </div>

                          {/* Evidence Section - Show locked message or actual evidence */}
                          {pattern.evidence && (
                            <div
                              className={`rounded-lg border ${isLocked ? 'border-amber-500/30 bg-amber-500/5' : patternStyle.evidenceBg} p-4 transition-colors duration-300 group-hover:border-white/20`}
                            >
                              <div className="flex items-start gap-3">
                                {isLocked ? (
                                  <>
                                    <Lock className="mt-0.5 h-4 w-4 flex-shrink-0 text-amber-400" />
                                    <div className="flex-1">
                                      <p className="mb-1 font-semibold text-amber-300 text-xs uppercase tracking-wide">
                                        Locked Pattern
                                      </p>
                                      <p className="text-amber-100 text-sm leading-relaxed">
                                        {pattern.evidence}
                                      </p>
                                      {pattern.preview_teaser && (
                                        <p className="mt-2 text-amber-200/80 text-xs italic">
                                          {pattern.preview_teaser}
                                        </p>
                                      )}
                                    </div>
                                  </>
                                ) : (
                                  <>
                                    <CheckCircle
                                      className={`mt-0.5 h-4 w-4 flex-shrink-0 text-${config.color}-400`}
                                    />
                                    <div className="flex-1">
                                      <p className="mb-1 font-semibold text-gray-300 text-xs uppercase tracking-wide">
                                        Evidence Found
                                      </p>
                                      <p className="text-gray-100 text-sm leading-relaxed">
                                        {pattern.evidence}
                                      </p>
                                    </div>
                                  </>
                                )}
                              </div>
                            </div>
                          )}

                          {/* Additional Details - Only if meaningful and different */}
                          {(showInsight || showContext) && (
                            <div className="space-y-3">
                              {showInsight && (
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
                                    {pattern.insight}
                                  </p>
                                </div>
                              )}

                              {showContext && (
                                <div className="flex items-start gap-3">
                                  <AlertCircle className="mt-1 h-4 w-4 flex-shrink-0 text-amber-400" />
                                  <div>
                                    <p className="mb-1 font-semibold text-amber-300 text-xs">
                                      Context
                                    </p>
                                    <p className="text-gray-300 text-sm leading-tight">
                                      {pattern.context}
                                    </p>
                                  </div>
                                </div>
                              )}
                            </div>
                          )}

                          {/* Upgrade Prompt for Locked Patterns */}
                          {isLocked && pattern.upgrade_hint && (
                            <div className="mt-4 rounded-lg border border-amber-500/30 bg-gradient-to-r from-amber-500/10 to-orange-500/10 p-3">
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                  <TrendingUp className="h-4 w-4 text-amber-400" />
                                  <p className="text-amber-200 text-xs">{pattern.upgrade_hint}</p>
                                </div>
                                <Link href="/pricing">
                                  <ExiqusButton
                                    variant="outline"
                                    size="sm"
                                    className="border-amber-500/50 text-amber-300 text-xs hover:bg-amber-500/10"
                                  >
                                    Upgrade
                                  </ExiqusButton>
                                </Link>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </ExiqusCard>
          </section>
        );
      })}
    </div>
  );
}

function QuestionsTab({ data, tier }: { data: QuestionModel[]; tier: string }) {
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  if (!data || data.length === 0) {
    const isBasicOrFree = tier === 'free' || tier === 'basic';
    return (
      <ExiqusEmptyState
        icon={MessageSquare}
        title="No interview questions available"
        description={
          isBasicOrFree
            ? 'Interview questions are available in Professional and Enterprise tiers'
            : 'No questions were generated for this analysis'
        }
      />
    );
  }

  // Group questions by category
  const categorizedQuestions = data.reduce(
    (acc, question) => {
      const category = question.category || 'other';
      if (!acc[category]) acc[category] = [];
      acc[category].push(question);
      return acc;
    },
    {} as Record<string, QuestionModel[]>
  );

  const categories = Object.keys(categorizedQuestions);
  const filteredQuestions =
    selectedCategory === 'all' ? data : categorizedQuestions[selectedCategory] || [];

  // Category styling config - matches portfolio analysis colors
  const categoryConfig: Record<
    string,
    { label: string; color: string; bgColor: string; borderColor: string }
  > = {
    technical: {
      label: 'Technical',
      color: 'text-blue-300',
      bgColor: 'bg-blue-600/20',
      borderColor: 'border-blue-600/40',
    },
    professional_practices: {
      label: 'Professional Practices',
      color: 'text-indigo-300',
      bgColor: 'bg-indigo-600/20',
      borderColor: 'border-indigo-600/40',
    },
    problem_solving: {
      label: 'Problem Solving',
      color: 'text-cyan-300',
      bgColor: 'bg-cyan-600/20',
      borderColor: 'border-cyan-600/40',
    },
    collaboration: {
      label: 'Collaboration',
      color: 'text-emerald-300',
      bgColor: 'bg-emerald-600/20',
      borderColor: 'border-emerald-600/40',
    },
  };

  return (
    <div className="space-y-6">
      {/* Category Pills */}
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={() => setSelectedCategory('all')}
          className={`rounded-full border px-5 py-2.5 font-semibold text-sm transition-all ${
            selectedCategory === 'all'
              ? 'border-amber-500 bg-gradient-to-r from-amber-500/30 to-orange-500/30 text-amber-200 shadow-amber-500/20 shadow-lg'
              : 'border-gray-700/50 bg-gray-900/50 text-gray-400 hover:border-gray-600/50 hover:bg-gray-800/50 hover:text-gray-300'
          }`}
        >
          All ({data.length})
        </button>
        {categories.map((category) => {
          const config = categoryConfig[category] || {
            label: category.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()),
            color: 'text-gray-400',
            bgColor: 'bg-gray-500/10',
            borderColor: 'border-gray-500/30',
          };
          const count = categorizedQuestions[category].length;

          return (
            <button
              type="button"
              key={category}
              onClick={() => setSelectedCategory(category)}
              className={`rounded-full border px-5 py-2.5 font-semibold text-sm transition-all ${
                selectedCategory === category
                  ? `${config.borderColor.replace('/30', '')} ${config.bgColor.replace('/10', '/30')} ${config.color.replace('400', '200')} shadow-lg`
                  : 'border-gray-700/50 bg-gray-900/50 text-gray-400 hover:border-gray-600/50 hover:bg-gray-800/50 hover:text-gray-300'
              }`}
            >
              {config.label} ({count})
            </button>
          );
        })}
      </div>

      {/* Questions Grid */}
      <div className="grid gap-6">
        {filteredQuestions.map((question, index) => (
          <ExiqusCard key={index} className="overflow-hidden">
            <div className="bg-gradient-to-br from-amber-500/5 to-orange-500/5 p-6">
              <div className="space-y-4">
                {/* Question Header */}
                <div className="flex items-start gap-4">
                  <div className="shrink-0 rounded-lg bg-amber-500/10 p-3">
                    <MessageSquare className="h-6 w-6 text-amber-400" />
                  </div>
                  <div className="flex-1 space-y-4">
                    <div>
                      <div className="mb-2 flex items-start justify-between gap-4">
                        <h3 className="flex-1 font-semibold text-gray-100 text-xl leading-tight">
                          {question.question}
                        </h3>
                        <span className="shrink-0 font-bold text-amber-400 text-lg">
                          Q{data.indexOf(question) + 1}
                        </span>
                      </div>

                      {/* Category badges */}
                      <div className="mb-4 flex items-center gap-2">
                        <ExiqusBadge
                          variant="warning"
                          className="border-amber-500/30 bg-amber-500/20 text-xs"
                        >
                          {question.category?.replace(/_/g, ' ')}
                        </ExiqusBadge>
                        {question.context_relevance && (
                          <ExiqusBadge variant="default" className="text-xs">
                            {question.context_relevance}
                          </ExiqusBadge>
                        )}
                      </div>
                    </div>

                    {question.evidence_reference && (
                      <div className="rounded-lg border border-blue-500/20 bg-gradient-to-r from-blue-500/10 to-purple-500/10 p-4">
                        <div className="flex items-start gap-3">
                          <Sparkles className="mt-0.5 h-4 w-4 flex-shrink-0 text-blue-400" />
                          <div>
                            <p className="mb-1 font-semibold text-blue-300 text-xs">
                              Based on Evidence
                            </p>
                            <p className="text-gray-300 text-sm">{question.evidence_reference}</p>
                          </div>
                        </div>
                      </div>
                    )}

                    {question.follow_ups && question.follow_ups.length > 0 && (
                      <div className="rounded-lg bg-white/[0.03] p-4">
                        <p className="mb-3 flex items-center gap-2 font-semibold text-gray-200 text-sm">
                          <ArrowRight className="h-4 w-4 text-amber-400" />
                          Follow-up questions
                        </p>
                        <div className="ml-6 space-y-2">
                          {question.follow_ups.map((followUp: string, followUpIndex: number) => (
                            <div
                              key={followUpIndex}
                              className="flex items-start gap-2 text-gray-300 text-sm"
                            >
                              <span className="font-bold text-amber-400">{followUpIndex + 1}.</span>
                              <span>{followUp}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {question.what_to_listen_for && (
                      <div className="rounded-lg border border-green-500/20 bg-gradient-to-r from-green-500/10 to-emerald-500/10 p-4">
                        <div className="flex items-start gap-3">
                          <Target className="mt-0.5 h-4 w-4 flex-shrink-0 text-green-400" />
                          <div>
                            <p className="mb-1 font-semibold text-green-300 text-xs">
                              Key Listening Points
                            </p>
                            <p className="text-gray-300 text-sm">{question.what_to_listen_for}</p>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </ExiqusCard>
        ))}
      </div>
    </div>
  );
}

function FlagsTab({
  greenFlags,
  redFlags,
  areasToExplore,
}: {
  greenFlags: string[];
  redFlags: string[];
  areasToExplore?: string[];
}) {
  return (
    <div className="grid gap-6 md:grid-cols-2">
      {/* Positive Indicators */}
      <ExiqusCard className="p-6">
        <div className="mb-4 flex items-center gap-3">
          <div className="rounded-lg bg-green-500/10 p-2">
            <CheckCircle className="h-5 w-5 text-green-400" />
          </div>
          <h3 className="font-semibold text-lg">Positive Indicators</h3>
        </div>
        {greenFlags && greenFlags.length > 0 ? (
          <div className="space-y-3">
            {greenFlags.map((flag, index) => (
              <div key={index} className="flex items-start gap-3">
                <CheckCircle className="mt-0.5 h-4 w-4 flex-shrink-0 text-green-400" />
                <p className="text-gray-300 text-sm">{flag}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500 text-sm">No specific positive indicators identified</p>
        )}
      </ExiqusCard>

      {/* Areas to Explore */}
      <ExiqusCard className="p-6">
        <div className="mb-4 flex items-center gap-3">
          <div className="rounded-lg bg-teal-500/10 p-2">
            <Search className="h-5 w-5 text-teal-400" />
          </div>
          <h3 className="font-semibold text-lg">Areas to Explore</h3>
        </div>
        {/* Combine red flags and areas to explore */}
        {(redFlags && redFlags.length > 0) || (areasToExplore && areasToExplore.length > 0) ? (
          <div className="space-y-3">
            {redFlags &&
              redFlags.map((flag, index) => (
                <div key={`rf-${index}`} className="flex items-start gap-3">
                  <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0 text-red-400" />
                  <p className="text-gray-300 text-sm">{flag}</p>
                </div>
              ))}
            {areasToExplore &&
              areasToExplore.map((area, index) => (
                <div key={`ae-${index}`} className="flex items-start gap-3">
                  <Search className="mt-0.5 h-4 w-4 flex-shrink-0 text-teal-400" />
                  <p className="text-gray-300 text-sm">{area}</p>
                </div>
              ))}
          </div>
        ) : (
          <p className="text-gray-500 text-sm">No specific concerns identified</p>
        )}
      </ExiqusCard>
    </div>
  );
}

function ActionsTab({ data }: { data: RecommendationModel[] }) {
  if (!data || data.length === 0) {
    return (
      <ExiqusEmptyState
        icon={TrendingUp}
        title="No recommendations available"
        description="No specific action items for this analysis"
      />
    );
  }

  // Intelligent icon selection based on action content
  const getActionIcon = (text: string) => {
    const lowerText = text.toLowerCase();

    // Bug fixes and testing
    if (lowerText.includes('bug') || lowerText.includes('fix') || lowerText.includes('issue')) {
      return Bug;
    }
    // Refactoring and code quality
    if (
      lowerText.includes('refactor') ||
      lowerText.includes('improve') ||
      lowerText.includes('quality')
    ) {
      return Wrench;
    }
    // Architecture and integration
    if (
      lowerText.includes('integrate') ||
      lowerText.includes('architecture') ||
      lowerText.includes('layer') ||
      lowerText.includes('backend') ||
      lowerText.includes('frontend')
    ) {
      return Layers;
    }
    // Feature delivery
    if (
      lowerText.includes('feature') ||
      lowerText.includes('deliver') ||
      lowerText.includes('commit') ||
      lowerText.includes('added')
    ) {
      return Package;
    }
    // Technical decisions and language choices
    if (
      lowerText.includes('typescript') ||
      lowerText.includes('language') ||
      lowerText.includes('choice') ||
      lowerText.includes('technical decision')
    ) {
      return Code;
    }
    // Default
    return TrendingUp;
  };

  // Get icon-specific styling
  const getIconStyling = (text: string) => {
    const lowerText = text.toLowerCase();

    if (lowerText.includes('bug') || lowerText.includes('fix') || lowerText.includes('issue')) {
      return { border: 'border-l-4 border-red-500/50', bg: 'bg-red-500/5' };
    }
    if (
      lowerText.includes('refactor') ||
      lowerText.includes('improve') ||
      lowerText.includes('quality')
    ) {
      return { border: 'border-l-4 border-amber-500/50', bg: 'bg-amber-500/5' };
    }
    if (
      lowerText.includes('integrate') ||
      lowerText.includes('architecture') ||
      lowerText.includes('layer') ||
      lowerText.includes('backend') ||
      lowerText.includes('frontend')
    ) {
      return { border: 'border-l-4 border-blue-500/50', bg: 'bg-blue-500/5' };
    }
    if (
      lowerText.includes('feature') ||
      lowerText.includes('deliver') ||
      lowerText.includes('commit') ||
      lowerText.includes('added')
    ) {
      return { border: 'border-l-4 border-purple-500/50', bg: 'bg-purple-500/5' };
    }
    if (
      lowerText.includes('typescript') ||
      lowerText.includes('language') ||
      lowerText.includes('choice') ||
      lowerText.includes('technical decision')
    ) {
      return { border: 'border-l-4 border-cyan-500/50', bg: 'bg-cyan-500/5' };
    }
    return { border: '', bg: '' };
  };

  return (
    <div className="grid gap-6">
      {data.map((rec, index) => {
        const ActionIcon = getActionIcon(rec.text);
        const iconStyling = getIconStyling(rec.text);

        return (
          <ExiqusCard
            key={index}
            className={`overflow-hidden ${iconStyling.border} ${
              rec.type === 'strength'
                ? 'border-green-500/20'
                : rec.type === 'concern'
                  ? 'border-red-500/20'
                  : 'border-gray-500/20'
            }`}
          >
            <div className={`flex items-start gap-4 p-6 ${iconStyling.bg}`}>
              <div
                className={`rounded-lg p-3 ${
                  rec.type === 'strength'
                    ? 'bg-green-500/10'
                    : rec.type === 'concern'
                      ? 'bg-red-500/10'
                      : 'bg-gray-500/10'
                }`}
              >
                <ActionIcon
                  className={`h-6 w-6 ${
                    rec.type === 'strength'
                      ? 'text-green-400'
                      : rec.type === 'concern'
                        ? 'text-red-400'
                        : 'text-gray-400'
                  }`}
                />
              </div>
              <div className="flex-1 space-y-3">
                <p className="font-medium text-base text-gray-100 leading-relaxed">{rec.text}</p>
                {rec.evidence && (
                  <div className="rounded-lg border border-gray-800/50 bg-gray-900/30 p-3">
                    <p className="text-gray-400 text-sm leading-relaxed">
                      <span className="font-semibold text-gray-300">Based on:</span> {rec.evidence}
                    </p>
                  </div>
                )}
                <div className="flex items-center gap-2">
                  <ExiqusBadge
                    variant={
                      rec.priority === 'high'
                        ? 'error'
                        : rec.priority === 'medium'
                          ? 'warning'
                          : 'default'
                    }
                    className="text-xs"
                  >
                    {rec.priority} priority
                  </ExiqusBadge>
                  <ExiqusBadge variant="default" className="text-xs">
                    {rec.type}
                  </ExiqusBadge>
                </div>
              </div>
            </div>
          </ExiqusCard>
        );
      })}
    </div>
  );
}

// Loading State Component
function LoadingState() {
  return (
    <div className="min-h-screen bg-[#0A0A0A] p-8">
      <div className="mx-auto max-w-7xl">
        <Skeleton className="mb-8 h-8 w-48" />
        <Skeleton className="mb-8 h-24 w-full" />
        <div className="mb-8 grid grid-cols-4 gap-6">
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
        </div>
        <Skeleton className="h-64 w-full" />
      </div>
    </div>
  );
}
