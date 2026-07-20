// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import { format } from 'date-fns';
import {
  ArrowLeft,
  ArrowRight,
  Briefcase,
  Building2,
  Calendar,
  CheckCircle2,
  Circle,
  FolderGit2,
  GitBranch,
  GitCommit,
  GitPullRequest,
  RefreshCw,
  Rocket,
  User,
  Users,
} from 'lucide-react';
import Image from 'next/image';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import {
  DataTransparencyBanner,
  InterviewTopicAccordion,
  KeyObservationCard,
  ObservablePatternCard,
  OrganizationBadge,
  RoleBadge,
  StrengthCard,
} from '@/components/candidate-hub';
import { ExiqusButton, ExiqusCard, GradientText } from '@/components/ui/exiqus-components';
import { UpgradePrompt } from '@/components/ui/upgrade-prompt';
import { useAuth } from '@/contexts/auth-context';
import { useAuthGuard } from '@/hooks/use-auth-guard';
import { api } from '@/lib/api-client';
import { renderBoldSafe } from '@/lib/sanitize';
import { cn } from '@/lib/utils';

// Intelligence Snapshot Types
interface ConfidenceLevel {
  level: 'high' | 'moderate' | 'low';
  basis: string;
  note: string;
}

interface EvidenceTrail {
  source: string;
  url: string;
}

interface ObservablePattern {
  pattern: string;
  value: string;
  visibility: 'observed' | 'not_observed';
  context: string;
  confidence?: ConfidenceLevel;
  evidence_trail?: EvidenceTrail[];
  analysis_source?: 'portfolio' | 'pr';
}

interface VisibleStrength {
  title: string;
  evidence: string;
  what_this_shows: string;
  source?: 'portfolio' | 'pr';
}

interface InterviewTopic {
  category: string;
  observation: string;
  question: string;
  why_discuss: string;
  source?: 'portfolio' | 'pr';
}

interface KeyObservation {
  text: string;
  source: 'portfolio' | 'pr';
}

interface EvidenceSummary {
  executive_summary: string;
  context_evaluated: string;
  role_evaluated: string;
  visible_strengths: VisibleStrength[];
  interview_topics: InterviewTopic[];
  data_interpretation: string;
}

interface DataScope {
  what_analyzed: string;
  prs_analyzed: number;
  repos_analyzed: number;
  timeline_span: string;
  timeline_label?: string;
  data_volume: 'high' | 'moderate' | 'limited' | 'none';
  not_analyzed: string[];
  important_note: string;
}

interface FeaturedRepoAnalysis {
  repository_name: string;
  commits: number;
  languages: string[];
  context: string | null;
  analysis_id: string;
  created_at: string | null;
  insights_count: number;
  patterns_count: number;
}

interface IntelligenceSnapshot {
  username: string;
  avatar_url: string;
  role: 'junior' | 'mid' | 'senior';
  organization_context: string | null;
  last_updated: string | null;
  analyses_run: string[];
  data_scope: DataScope;
  observable_patterns: ObservablePattern[];
  evidence_summary: EvidenceSummary;
  key_observations: KeyObservation[];
  featured_repo_analysis: FeaturedRepoAnalysis | null;
}

interface CandidateHubData {
  username: string;
  snapshot: IntelligenceSnapshot;
  portfolio_analysis: {
    id: string;
    created_at: string;
    context: string;
    role: string;
    executive_summary?: string;
  } | null;
  pr_analysis: {
    id: string;
    created_at: string;
    context: string;
    role: string;
    executive_summary?: string;
  } | null;
  single_repo_analyses: Array<{
    id: string;
    repository_name: string;
    created_at: string;
    context: string;
  }>;
}

// Helper function to format backend strings (remove underscores, capitalize properly)
const formatBackendString = (str: string): string => {
  return str
    .replace(/_/g, ' ') // Replace underscores with spaces
    .split(' ')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
};

// Helper function to render markdown text with bold support - XSS safe
const renderMarkdownText = (text: string) => {
  return <span dangerouslySetInnerHTML={{ __html: renderBoldSafe(text) }} />;
};

// Helper function to get the correct icon for organization context
const getOrganizationIcon = (context: string) => {
  const normalizedContext = context?.toLowerCase();
  switch (normalizedContext) {
    case 'startup':
      return Rocket;
    case 'enterprise':
      return Building2;
    case 'agency':
      return Briefcase;
    case 'open_source':
      return Users;
    default:
      return Building2;
  }
};

export default function CandidateHubPage() {
  const params = useParams();
  const router = useRouter();
  const { user } = useAuth();
  const { isLoading: authLoading, showUnauthorized, UnauthorizedComponent } = useAuthGuard();
  const username = params.username as string;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [candidateData, setCandidateData] = useState<CandidateHubData | null>(null);

  // Scroll to top when navigating to a new candidate
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [username]);

  useEffect(() => {
    const fetchCandidateData = async () => {
      if (!user) return;

      try {
        setLoading(true);
        setError(null);
        const response = await api.getCandidateHub(username);
        setCandidateData(response.data);
      } catch (err) {
        console.error('Failed to fetch candidate data:', err);
        setError('Failed to load candidate data. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    if (user) {
      fetchCandidateData();
    }
  }, [user, username]);

  // Handle auth loading state first
  if (authLoading) {
    return (
      <div className="flex min-h-[calc(100vh-12rem)] items-center justify-center bg-[#0A0A0A]">
        <div className="text-center">
          <div className="mb-4 inline-flex h-16 w-16 items-center justify-center">
            <div className="h-12 w-12 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
          </div>
          <p className="text-gray-400">Checking authentication...</p>
        </div>
      </div>
    );
  }

  // Handle unauthorized state
  if (showUnauthorized && UnauthorizedComponent) {
    return <UnauthorizedComponent />;
  }

  // Handle data loading state (only for authenticated users)
  if (loading) {
    return (
      <div className="flex min-h-[calc(100vh-12rem)] items-center justify-center bg-[#0A0A0A]">
        <div className="text-center">
          <div className="mb-4 inline-flex h-16 w-16 items-center justify-center">
            <div className="h-12 w-12 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
          </div>
          <p className="text-gray-400">Loading candidate insight hub...</p>
        </div>
      </div>
    );
  }

  // Show upgrade prompt for FREE users (Candidate Hub available on all paid tiers)
  if (user && user.subscription_plan === 'free') {
    return (
      <UpgradePrompt
        feature="Candidate Hub"
        requiredTier="Starter"
        description="Access unified candidate insight views combining portfolio analysis, PR analysis, and repository deep dives in one place."
      />
    );
  }

  // Handle error state
  if (error || !candidateData) {
    return (
      <div className="min-h-[calc(100vh-12rem)] bg-[#0A0A0A] py-12">
        <div className="container mx-auto max-w-4xl px-4">
          <ExiqusCard className="p-12 text-center">
            <div className="mb-4 flex justify-center">
              <Circle className="h-16 w-16 text-red-400" />
            </div>
            <h2 className="mb-2 font-bold text-2xl text-gray-100">
              {error || 'Candidate Not Found'}
            </h2>
            <p className="mb-6 text-gray-400">Unable to load candidate data for @{username}</p>
            <ExiqusButton onClick={() => router.push('/candidate-hub')}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Candidate Intelligence Hub
            </ExiqusButton>
          </ExiqusCard>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-[calc(100vh-12rem)] bg-[#0A0A0A] py-8">
      {/* Multi-gradient animated background - blends all three colors */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 -left-40 h-80 w-80 animate-pulse rounded-full bg-indigo-500/20 blur-3xl"></div>
        <div className="absolute -top-20 right-0 h-80 w-80 animate-pulse rounded-full bg-teal-500/20 blur-3xl delay-700"></div>
        <div className="absolute top-20 left-1/3 h-80 w-80 animate-pulse rounded-full bg-purple-500/20 blur-3xl delay-1000"></div>
      </div>

      <div className="container relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Back Button */}
        <div className="mb-6">
          <Link
            href="/candidate-hub"
            className="inline-flex items-center text-gray-400 text-sm transition-colors hover:text-gray-300"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Candidate Intelligence Hub
          </Link>
        </div>

        {/* Header with unified gradient */}
        <div className="mb-8 rounded-2xl bg-gradient-to-r from-indigo-900/10 via-teal-900/10 to-purple-900/10 p-8 ring-1 ring-white/5">
          <div className="flex items-start gap-6">
            {/* Avatar */}
            {candidateData.snapshot.avatar_url && (
              <Image
                src={candidateData.snapshot.avatar_url}
                alt={`${username}'s avatar`}
                width={80}
                height={80}
                className="h-20 w-20 rounded-full ring-4 ring-white/10"
              />
            )}

            {/* Header Info */}
            <div className="flex-1">
              <div className="mb-2 flex items-center gap-3">
                <User className="h-6 w-6 text-gray-400" />
                <h1 className="font-bold text-4xl">
                  <GradientText>@{username}</GradientText>
                </h1>
                <RoleBadge role={candidateData.snapshot.role} size="lg" />
                {candidateData.snapshot.organization_context && (
                  <OrganizationBadge
                    context={
                      candidateData.snapshot.organization_context as
                        | 'startup'
                        | 'enterprise'
                        | 'agency'
                        | 'open_source'
                    }
                    size="lg"
                  />
                )}
              </div>
              <p className="text-gray-400 text-lg">Complete Developer Assessment</p>
            </div>
          </div>

          {/* Intelligence Snapshot Stats - UPDATED */}
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="flex items-center gap-3 rounded-lg bg-white/5 px-4 py-3">
              <GitBranch className="h-5 w-5 text-gray-400" />
              <div>
                <p className="text-gray-500 text-sm">Data Coverage</p>
                <p className="font-semibold text-gray-100 text-xl capitalize">
                  {candidateData.snapshot.data_scope.data_volume}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3 rounded-lg bg-white/5 px-4 py-3">
              <GitCommit className="h-5 w-5 text-gray-400" />
              <div>
                <p className="text-gray-500 text-sm">Role Level</p>
                <p className="font-semibold text-gray-100 text-xl capitalize">
                  {candidateData.snapshot.role}
                </p>
              </div>
            </div>
            {candidateData.snapshot.organization_context &&
              (() => {
                const OrgIcon = getOrganizationIcon(candidateData.snapshot.organization_context);
                return (
                  <div className="flex items-center gap-3 rounded-lg bg-white/5 px-4 py-3">
                    <OrgIcon className="h-5 w-5 text-gray-400" />
                    <div>
                      <p className="text-gray-500 text-sm">Organization Context</p>
                      <p className="font-semibold text-gray-100 text-xl">
                        {formatBackendString(candidateData.snapshot.organization_context)}
                      </p>
                    </div>
                  </div>
                );
              })()}
            <div className="flex flex-col gap-2 rounded-lg bg-white/5 px-4 py-3">
              <div className="flex items-center gap-2">
                <Calendar className="h-4 w-4 text-gray-400" />
                <p className="text-gray-500 text-sm">Analyses Available</p>
              </div>
              <div className="flex flex-col gap-1">
                {candidateData.snapshot.analyses_run.map((analysis, idx) => (
                  <p key={idx} className="text-gray-300 text-xs">
                    • {analysis}
                  </p>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Analysis Type Cards - 3 columns */}
        <div className="mb-8 grid gap-6 lg:grid-cols-3">
          {/* Portfolio Analysis Card - INDIGO */}
          <ExiqusCard
            className={cn(
              'group flex flex-col p-6 transition-all hover:scale-[1.02]',
              'border-2 bg-gradient-to-br from-indigo-900/20 to-indigo-600/10',
              candidateData.portfolio_analysis ? 'border-indigo-500/30' : 'border-white/[0.09]'
            )}
            glow={candidateData.portfolio_analysis ? 'purple' : 'subtle'}
          >
            {/* Card Header */}
            <div className="mb-4 flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-600 to-indigo-800">
                  <FolderGit2 className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-100 text-lg">Portfolio Analysis</h3>
                  <p className="text-gray-500 text-xs">Comprehensive insight</p>
                </div>
              </div>
              {candidateData.portfolio_analysis && (
                <CheckCircle2 className="h-5 w-5 text-indigo-400" />
              )}
              {!candidateData.portfolio_analysis && <Circle className="h-5 w-5 text-gray-600" />}
            </div>

            {/* Card Content */}
            <div className="mb-6 flex-1">
              {candidateData.portfolio_analysis ? (
                <>
                  <div className="mb-3 flex items-center gap-2">
                    <span className="rounded-full bg-indigo-500/20 px-3 py-1 font-medium text-indigo-400 text-xs ring-1 ring-indigo-500/30">
                      Completed
                    </span>
                    <span className="text-gray-500 text-xs">
                      {candidateData.portfolio_analysis.created_at
                        ? format(
                            new Date(candidateData.portfolio_analysis.created_at),
                            'MMM d, h:mm a'
                          )
                        : 'N/A'}
                    </span>
                  </div>
                  {candidateData.portfolio_analysis.executive_summary && (
                    <p className="line-clamp-3 text-gray-400 text-sm">
                      {candidateData.portfolio_analysis.executive_summary}
                    </p>
                  )}
                </>
              ) : (
                <div className="py-4 text-center">
                  <Circle className="mx-auto mb-2 h-12 w-12 text-gray-600" />
                  <p className="text-gray-500 text-sm">Not run yet</p>
                  <p className="mt-1 text-gray-600 text-xs">Analyze their complete portfolio</p>
                </div>
              )}
            </div>

            {/* Card Actions */}
            <div className="flex gap-2">
              {candidateData.portfolio_analysis ? (
                <>
                  <ExiqusButton
                    onClick={() =>
                      router.push(`/portfolio-analyses/${candidateData.portfolio_analysis?.id}`)
                    }
                    className="flex-1 bg-gradient-to-r from-indigo-600 to-indigo-700"
                    size="sm"
                  >
                    View Analysis
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </ExiqusButton>
                  <ExiqusButton
                    onClick={() =>
                      router.push(`/portfolio-analysis?username=${username}&returnTo=candidate-hub`)
                    }
                    variant="secondary"
                    size="sm"
                  >
                    <RefreshCw className="h-4 w-4" />
                  </ExiqusButton>
                </>
              ) : (
                <ExiqusButton
                  onClick={() =>
                    router.push(`/portfolio-analysis?username=${username}&returnTo=candidate-hub`)
                  }
                  className="w-full bg-gradient-to-r from-indigo-600 to-indigo-700"
                  size="sm"
                >
                  Run Portfolio Analysis
                  <ArrowRight className="ml-2 h-4 w-4" />
                </ExiqusButton>
              )}
            </div>
          </ExiqusCard>

          {/* PR Analysis Card - TEAL */}
          <ExiqusCard
            className={cn(
              'group flex flex-col p-6 transition-all hover:scale-[1.02]',
              'border-2 bg-gradient-to-br from-teal-900/20 to-teal-600/10',
              candidateData.pr_analysis ? 'border-teal-500/30' : 'border-white/[0.09]'
            )}
            glow={candidateData.pr_analysis ? 'green' : 'subtle'}
          >
            {/* Card Header */}
            <div className="mb-4 flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-teal-600 to-teal-800">
                  <GitPullRequest className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-100 text-lg">PR Analysis</h3>
                  <p className="text-gray-500 text-xs">Collaboration activity</p>
                </div>
              </div>
              {candidateData.pr_analysis && <CheckCircle2 className="h-5 w-5 text-teal-400" />}
              {!candidateData.pr_analysis && <Circle className="h-5 w-5 text-gray-600" />}
            </div>

            {/* Card Content */}
            <div className="mb-6 flex-1">
              {candidateData.pr_analysis ? (
                <>
                  <div className="mb-3 flex items-center gap-2">
                    <span className="rounded-full bg-teal-500/20 px-3 py-1 font-medium text-teal-400 text-xs ring-1 ring-teal-500/30">
                      Completed
                    </span>
                    <span className="text-gray-500 text-xs">
                      {candidateData.pr_analysis.created_at
                        ? format(new Date(candidateData.pr_analysis.created_at), 'MMM d, h:mm a')
                        : 'N/A'}
                    </span>
                  </div>
                  {candidateData.pr_analysis.executive_summary && (
                    <p className="line-clamp-3 text-gray-400 text-sm">
                      {candidateData.pr_analysis.executive_summary}
                    </p>
                  )}
                </>
              ) : (
                <div className="py-4 text-center">
                  <Circle className="mx-auto mb-2 h-12 w-12 text-gray-600" />
                  <p className="text-gray-500 text-sm">Not run yet</p>
                  <p className="mt-1 text-gray-600 text-xs">Analyze their PR contributions</p>
                </div>
              )}
            </div>

            {/* Card Actions */}
            <div className="flex gap-2">
              {candidateData.pr_analysis ? (
                <>
                  <ExiqusButton
                    onClick={() => router.push(`/pr-analyses/${candidateData.pr_analysis?.id}`)}
                    className="flex-1 bg-gradient-to-r from-teal-600 to-teal-700"
                    size="sm"
                  >
                    View Analysis
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </ExiqusButton>
                  <ExiqusButton
                    onClick={() =>
                      router.push(`/pr-analysis?username=${username}&returnTo=candidate-hub`)
                    }
                    variant="secondary"
                    size="sm"
                  >
                    <RefreshCw className="h-4 w-4" />
                  </ExiqusButton>
                </>
              ) : (
                <ExiqusButton
                  onClick={() =>
                    router.push(`/pr-analysis?username=${username}&returnTo=candidate-hub`)
                  }
                  className="w-full bg-gradient-to-r from-teal-600 to-teal-700"
                  size="sm"
                >
                  Run PR Analysis
                  <ArrowRight className="ml-2 h-4 w-4" />
                </ExiqusButton>
              )}
            </div>
          </ExiqusCard>

          {/* Single Repo Card - PURPLE */}
          <ExiqusCard
            className={cn(
              'group flex flex-col p-6 transition-all hover:scale-[1.02]',
              'border-2 bg-gradient-to-br from-purple-900/20 to-purple-600/10',
              candidateData.single_repo_analyses.length > 0
                ? 'border-purple-500/30'
                : 'border-white/[0.09]'
            )}
            glow={candidateData.single_repo_analyses.length > 0 ? 'purple' : 'subtle'}
          >
            {/* Card Header */}
            <div className="mb-4 flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-purple-600 to-purple-800">
                  <GitBranch className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-100 text-lg">Repository Deep Dives</h3>
                  <p className="text-gray-500 text-xs">Specific repo analysis</p>
                </div>
              </div>
              {candidateData.single_repo_analyses.length > 0 && (
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-purple-500/20 font-medium text-purple-400 text-xs ring-1 ring-purple-500/30">
                  {candidateData.single_repo_analyses.length}
                </span>
              )}
            </div>

            {/* Card Content */}
            <div className="mb-6 flex-1">
              {candidateData.single_repo_analyses.length > 0 ? (
                <div className="space-y-2">
                  {candidateData.single_repo_analyses.slice(0, 3).map((analysis) => (
                    <div
                      key={analysis.id}
                      className="cursor-pointer rounded-lg bg-white/5 p-3 transition-colors hover:bg-white/10"
                      onClick={() => router.push(`/analyses/${analysis.id}`)}
                    >
                      <div className="mb-1 flex items-center justify-between">
                        <p className="font-medium text-gray-300 text-sm">
                          {analysis.repository_name}
                        </p>
                        <ArrowRight className="h-3 w-3 text-gray-500" />
                      </div>
                      <p className="text-gray-500 text-xs">
                        {analysis.created_at
                          ? format(new Date(analysis.created_at), 'MMM d, yyyy')
                          : 'N/A'}
                      </p>
                    </div>
                  ))}
                  {candidateData.single_repo_analyses.length > 3 && (
                    <p className="pt-2 text-center text-gray-500 text-xs">
                      +{candidateData.single_repo_analyses.length - 3} more
                    </p>
                  )}
                </div>
              ) : (
                <div className="py-4 text-center">
                  <Circle className="mx-auto mb-2 h-12 w-12 text-gray-600" />
                  <p className="text-gray-500 text-sm">No repositories analyzed</p>
                  <p className="mt-1 text-gray-600 text-xs">Deep dive into specific repos</p>
                </div>
              )}
            </div>

            {/* Card Actions */}
            <ExiqusButton
              onClick={() => router.push(`/analyze?username=${username}&returnTo=candidate-hub`)}
              className="w-full bg-gradient-to-r from-purple-600 to-purple-700"
              size="sm"
            >
              Analyze Repository
              <ArrowRight className="ml-2 h-4 w-4" />
            </ExiqusButton>
          </ExiqusCard>
        </div>

        {/* Intelligence Snapshot Section */}
        <div className="mb-8 space-y-6">
          {/* Executive Summary - Top Priority */}
          {candidateData.snapshot.evidence_summary?.executive_summary && (
            <ExiqusCard className="border-l-2 border-l-violet-500/40 p-6" glow="subtle">
              <h2 className="mb-3 font-bold text-2xl text-gray-100">Executive Summary</h2>
              <div className="mb-4 text-base text-gray-300 leading-relaxed">
                {renderMarkdownText(candidateData.snapshot.evidence_summary.executive_summary)}
              </div>
              <div className="rounded-lg bg-violet-500/10 px-4 py-3">
                <div className="text-violet-300 text-xs">
                  {renderMarkdownText(candidateData.snapshot.evidence_summary.data_interpretation)}
                </div>
              </div>
            </ExiqusCard>
          )}

          {/* Data Transparency Banner */}
          <DataTransparencyBanner dataScope={candidateData.snapshot.data_scope} />

          {/* Key Observations */}
          {candidateData.snapshot.key_observations &&
            candidateData.snapshot.key_observations.length > 0 && (
              <div>
                <h2 className="mb-4 font-bold text-2xl text-gray-100">Key Observations</h2>
                <div className="grid gap-3 md:grid-cols-2">
                  {candidateData.snapshot.key_observations.map((observation, idx) => (
                    <KeyObservationCard key={idx} observation={observation} />
                  ))}
                </div>
              </div>
            )}

          {/* Patterns (Observable & Not Observable) */}
          <div>
            <h2 className="mb-4 font-bold text-2xl text-gray-100">Patterns</h2>
            <div className="grid gap-4 md:grid-cols-2">
              {candidateData.snapshot.observable_patterns.map((pattern, idx) => (
                <ObservablePatternCard
                  key={idx}
                  pattern={pattern}
                  roleContext={candidateData.snapshot.role}
                />
              ))}
            </div>
          </div>

          {/* Evidence Summary */}
          {candidateData.snapshot.evidence_summary && (
            <div className="grid gap-6 lg:grid-cols-2">
              {/* Visible Strengths */}
              <div>
                <h2 className="mb-4 font-bold text-2xl text-gray-100">Visible Strengths</h2>
                <div className="space-y-3">
                  {candidateData.snapshot.evidence_summary.visible_strengths.map(
                    (strength, idx) => (
                      <StrengthCard key={idx} strength={strength} />
                    )
                  )}
                </div>
              </div>

              {/* Interview Topics */}
              <div>
                <h2 className="mb-4 font-bold text-2xl text-gray-100">Interview Topics</h2>

                {/* Accordions */}
                <div className="space-y-3">
                  {candidateData.snapshot.evidence_summary.interview_topics.map((topic, idx) => (
                    <InterviewTopicAccordion
                      key={idx}
                      topic={topic}
                      analysisType={topic.source || 'portfolio'}
                    />
                  ))}
                </div>

                {/* CTA to Full Interview Guide(s) */}
                {(candidateData.portfolio_analysis?.id || candidateData.pr_analysis?.id) && (
                  <div className="mt-4">
                    {/* Show BOTH buttons when both analyses exist */}
                    {candidateData.portfolio_analysis?.id && candidateData.pr_analysis?.id ? (
                      <div className="grid gap-3 md:grid-cols-2">
                        {/* Portfolio Interview Guide */}
                        <Link
                          href={`/portfolio-analyses/${candidateData.portfolio_analysis.id}#interview-questions`}
                        >
                          <ExiqusButton variant="secondary" className="w-full">
                            <FolderGit2 className="mr-2 h-4 w-4" />
                            Portfolio Interview Guide
                            <ArrowRight className="ml-auto h-4 w-4" />
                          </ExiqusButton>
                        </Link>

                        {/* PR Analysis Interview Guide */}
                        <Link
                          href={`/pr-analyses/${candidateData.pr_analysis.id}#interview-questions`}
                        >
                          <ExiqusButton variant="secondary" className="w-full">
                            <GitPullRequest className="mr-2 h-4 w-4" />
                            PR Analysis Interview Guide
                            <ArrowRight className="ml-auto h-4 w-4" />
                          </ExiqusButton>
                        </Link>
                      </div>
                    ) : (
                      /* Show single button when only one analysis exists */
                      <Link
                        href={
                          candidateData.portfolio_analysis?.id
                            ? `/portfolio-analyses/${candidateData.portfolio_analysis.id}#interview-questions`
                            : `/pr-analyses/${candidateData.pr_analysis?.id}#interview-questions`
                        }
                      >
                        <ExiqusButton variant="secondary" className="w-full">
                          View Full Interview Guide with Listening Strategies
                          <ArrowRight className="ml-2 h-4 w-4" />
                        </ExiqusButton>
                      </Link>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Featured Single Repo Analysis - Only show if 2+ repos analyzed */}
        {candidateData.snapshot.featured_repo_analysis && (
          <div className="mb-8">
            <h2 className="mb-4 font-bold text-2xl text-gray-100">Featured Repository Analysis</h2>
            <ExiqusCard className="border-l-2 border-l-cyan-500/40 p-6" glow="subtle">
              <div className="mb-4 flex items-start justify-between">
                <div>
                  <h3 className="mb-1 font-semibold text-gray-100 text-xl">
                    {candidateData.snapshot.featured_repo_analysis.repository_name.split('/')[1]}
                  </h3>
                  <p className="text-gray-400 text-sm">
                    Most complex repository from{' '}
                    {candidateData.snapshot.featured_repo_analysis.insights_count +
                      candidateData.snapshot.featured_repo_analysis.patterns_count}{' '}
                    evidence insights & patterns
                  </p>
                </div>
                {candidateData.snapshot.featured_repo_analysis.context && (
                  <span className="rounded-full bg-cyan-500/10 px-3 py-1 font-medium text-cyan-400 text-sm capitalize">
                    {candidateData.snapshot.featured_repo_analysis.context}
                  </span>
                )}
              </div>

              <div className="mb-4 grid gap-4 sm:grid-cols-3">
                <div className="flex items-center gap-2 rounded-lg bg-white/5 px-3 py-2">
                  <GitCommit className="h-4 w-4 text-gray-400" />
                  <div>
                    <p className="text-gray-500 text-xs">Commits</p>
                    <p className="font-semibold text-gray-100 text-lg">
                      {candidateData.snapshot.featured_repo_analysis.commits}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 rounded-lg bg-white/5 px-3 py-2">
                  <Circle className="h-4 w-4 text-gray-400" />
                  <div>
                    <p className="text-gray-500 text-xs">Insights</p>
                    <p className="font-semibold text-gray-100 text-lg">
                      {candidateData.snapshot.featured_repo_analysis.insights_count}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 rounded-lg bg-white/5 px-3 py-2">
                  <CheckCircle2 className="h-4 w-4 text-gray-400" />
                  <div>
                    <p className="text-gray-500 text-xs">Patterns</p>
                    <p className="font-semibold text-gray-100 text-lg">
                      {candidateData.snapshot.featured_repo_analysis.patterns_count}
                    </p>
                  </div>
                </div>
              </div>

              {candidateData.snapshot.featured_repo_analysis.languages.length > 0 && (
                <div className="mb-4">
                  <p className="mb-2 text-gray-500 text-sm">Top Languages</p>
                  <div className="flex flex-wrap gap-2">
                    {candidateData.snapshot.featured_repo_analysis.languages.map((lang, idx) => (
                      <span
                        key={idx}
                        className="rounded-full bg-gradient-to-r from-cyan-500/10 to-blue-500/10 px-3 py-1 font-medium text-cyan-300 text-sm"
                      >
                        {lang}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <Link href={`/analyses/${candidateData.snapshot.featured_repo_analysis.analysis_id}`}>
                <ExiqusButton variant="secondary" className="w-full">
                  View Detailed Analysis
                  <ArrowRight className="ml-2 h-4 w-4" />
                </ExiqusButton>
              </Link>
            </ExiqusCard>
          </div>
        )}
      </div>
    </div>
  );
}
