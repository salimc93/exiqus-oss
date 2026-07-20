// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import { format } from 'date-fns';
import {
  Activity,
  AlertCircle,
  ArrowUpRight,
  BarChart,
  Brain,
  Calendar,
  ChevronRight,
  Clock,
  FileCode2,
  GitBranch,
  GitPullRequest,
  Loader2,
  Search,
  Sparkles,
  Target,
  TrendingUp,
  Users,
  Zap,
} from 'lucide-react';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { ExiqusButton, ExiqusCard, GradientText } from '@/components/ui/exiqus-components';
import { Progress } from '@/components/ui/progress';
import { useAuth } from '@/contexts/auth-context';
import { useAuthGuard } from '@/hooks/use-auth-guard';
import { api } from '@/lib/api-client';
import { cn } from '@/lib/utils';
import type { AnalysisDetails } from '@/types';

interface CandidateCard {
  username: string;
  avatar_url: string;
  has_portfolio: boolean;
  has_pr: boolean;
  repo_count: number;
  latest_activity: string;
  portfolio_summary: string;
}

export default function DashboardPage() {
  const { user } = useAuth();
  const router = useRouter();
  const { isLoading, showUnauthorized, UnauthorizedComponent } = useAuthGuard();
  const [analysesCount, setAnalysesCount] = useState(0);
  const [candidatesCount, setCandidatesCount] = useState(0);
  const [lastAnalysis, setLastAnalysis] = useState<Date | null>(null);
  const [recentAnalyses, setRecentAnalyses] = useState<AnalysisDetails[]>([]);
  const [recentCandidates, setRecentCandidates] = useState<CandidateCard[]>([]);
  const [loadingAnalyses, setLoadingAnalyses] = useState(true);
  const [loadingCandidates, setLoadingCandidates] = useState(true);
  const [weeklyCount, setWeeklyCount] = useState(0);
  const [candidateSearchQuery, setCandidateSearchQuery] = useState('');
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [aiQuota, setAIQuota] = useState<any>(null);
  const [loadingQuota, setLoadingQuota] = useState(false);

  // Fetch AI quota status for FREE tier users
  useEffect(() => {
    const fetchAIQuota = async () => {
      if (!user || user.subscription_plan !== 'free') return;

      try {
        setLoadingQuota(true);
        const response = await api.getAIQuotaStatus();
        setAIQuota(response.data);
      } catch (error) {
        console.error('Failed to fetch AI quota:', error);
      } finally {
        setLoadingQuota(false);
      }
    };

    if (user) {
      fetchAIQuota();
    }
  }, [user]);

  useEffect(() => {
    const fetchAnalyses = async () => {
      if (!user) return;

      try {
        setLoadingAnalyses(true);
        const response = await api.getAnalyses({ limit: 10 });
        const data = response.data;

        setAnalysesCount(data.total_count || 0);
        setWeeklyCount(data.weekly_count || 0);

        // Get the most recent analysis date and recent analyses
        if (data.items && data.items.length > 0) {
          setLastAnalysis(new Date(data.items[0].created_at));
          setRecentAnalyses(data.items.slice(0, 6)); // Show last 6 analyses
        }
      } catch (error) {
        console.error('Failed to fetch analyses:', error);
      } finally {
        setLoadingAnalyses(false);
      }
    };

    if (user) {
      fetchAnalyses();
    }
  }, [user]);

  useEffect(() => {
    const fetchCandidates = async () => {
      if (!user) return;

      try {
        setLoadingCandidates(true);
        const response = await api.getDashboardCandidates({ limit: 6 });
        const candidates = response.data || [];
        setRecentCandidates(candidates);
        setCandidatesCount(candidates.length);

        // Update lastAnalysis to include candidate activity dates
        if (candidates.length > 0 && candidates[0].latest_activity) {
          const candidateLatestDate = new Date(candidates[0].latest_activity);
          setLastAnalysis((prevLastAnalysis) => {
            if (!prevLastAnalysis || candidateLatestDate > prevLastAnalysis) {
              return candidateLatestDate;
            }
            return prevLastAnalysis;
          });
        }
      } catch (error) {
        console.error('Failed to fetch candidates:', error);
      } finally {
        setLoadingCandidates(false);
      }
    };

    if (user) {
      fetchCandidates();
    }
  }, [user]);

  // Calculate plan limits - Repository Deep Dives
  const getSingleRepoPlanLimit = () => {
    switch (user?.subscription_plan) {
      case 'free':
        return 10; // 3 premium + 7 basic analyses
      case 'starter':
        return 50;
      case 'growth':
        return 100;
      case 'scale':
        return 250;
      case 'scale_plus':
        return -1; // Unlimited
      default:
        return 0;
    }
  };

  // Calculate plan limits - Candidate Assessments
  const getCandidateAssessmentLimit = () => {
    switch (user?.subscription_plan) {
      case 'free':
        return 0;
      case 'starter':
        return 10;
      case 'growth':
        return 50;
      case 'scale':
        return 200;
      case 'scale_plus':
        return 500;
      default:
        return 0;
    }
  };

  const planLimit = getSingleRepoPlanLimit();
  const candidateLimit = getCandidateAssessmentLimit();
  const usagePercentage = planLimit > 0 && planLimit !== -1 ? (analysesCount / planLimit) * 100 : 0;
  const candidateUsagePercentage =
    candidateLimit > 0 ? (candidatesCount / candidateLimit) * 100 : 0;

  // Filter candidates based on search query
  const filteredCandidates = recentCandidates.filter((candidate) => {
    const query = candidateSearchQuery.toLowerCase();
    return (
      candidate.username.toLowerCase().includes(query) ||
      candidate.portfolio_summary.toLowerCase().includes(query)
    );
  });

  // Handle loading state
  if (isLoading) {
    return (
      <div className="flex min-h-[calc(100vh-12rem)] items-center justify-center bg-[#0A0A0A]">
        <div className="text-center">
          <div className="mb-4 inline-flex h-16 w-16 items-center justify-center">
            <div className="h-12 w-12 animate-spin rounded-full border-4 border-purple-600 border-t-transparent" />
          </div>
          <p className="text-gray-400">Preparing your analysis dashboard...</p>
        </div>
      </div>
    );
  }

  // Handle unauthorized state
  if (showUnauthorized && UnauthorizedComponent) {
    return <UnauthorizedComponent />;
  }

  // Ensure user is defined at this point
  if (!user) {
    return null;
  }

  return (
    <div className="min-h-[calc(100vh-12rem)] bg-[#0A0A0A] py-8">
      {/* Animated gradient background - Emerald for Growth/Innovation */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 h-80 w-80 animate-pulse rounded-full bg-emerald-500/15 blur-3xl"></div>
        <div className="absolute -bottom-40 -left-40 h-80 w-80 animate-pulse rounded-full bg-green-500/15 blur-3xl delay-1000"></div>
        <div className="absolute top-1/2 left-1/2 h-80 w-80 -translate-x-1/2 -translate-y-1/2 animate-pulse rounded-full bg-emerald-500/10 blur-3xl delay-500"></div>
      </div>

      <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Welcome Header with enhanced design */}
        <div className="mb-10">
          <div className="mb-2 flex items-center gap-2">
            <Badge className="border-0 bg-gradient-to-r from-purple-600 to-blue-600 text-white">
              {user.subscription_plan === 'free' ? 'Free' : user.subscription_plan.toUpperCase()}{' '}
              PLAN
            </Badge>
            <Badge variant="outline" className="border-gray-700 text-gray-400">
              <Activity className="mr-1 h-3 w-3" />
              Active
            </Badge>
          </div>
          <h1 className="mb-2 font-bold text-4xl text-gray-100">
            Welcome back,{' '}
            <GradientText>{user.company || user.full_name || 'Developer'}</GradientText>!
          </h1>
          <p className="text-gray-400">
            {candidateLimit > 0 && recentCandidates.length > 0
              ? `You've assessed ${recentCandidates.length} candidate${recentCandidates.length === 1 ? '' : 's'}. Continue building your talent pipeline!`
              : candidateLimit > 0
                ? 'Welcome to evidence-driven hiring. Start assessing candidates today!'
                : analysesCount > 0
                  ? `You've performed ${analysesCount} repository analysis${analysesCount === 1 ? '' : 'es'}. Upgrade to assess complete candidate portfolios!`
                  : 'Welcome! Start analyzing repositories to evaluate code quality and development practices.'}
          </p>
        </div>

        {/* AI Quota Warning Banner for FREE tier */}
        {!loadingQuota && aiQuota && aiQuota.has_quota_limit && (
          <div
            className={cn(
              'mb-8 rounded-xl border p-6 transition-all duration-300',
              aiQuota.ai_remaining === 0
                ? 'border-amber-500/50 bg-gradient-to-r from-amber-500/10 via-orange-500/10 to-amber-500/10'
                : aiQuota.ai_remaining === 1
                  ? 'border-purple-500/50 bg-gradient-to-r from-purple-500/10 via-blue-500/10 to-purple-500/10'
                  : 'border-blue-500/30 bg-gradient-to-r from-blue-500/5 via-purple-500/5 to-blue-500/5'
            )}
          >
            <div className="flex items-start gap-4">
              {aiQuota.ai_remaining === 0 ? (
                <AlertCircle className="h-6 w-6 flex-shrink-0 text-amber-400" />
              ) : (
                <Sparkles className="h-6 w-6 flex-shrink-0 text-purple-400" />
              )}
              <div className="flex-1">
                <h3
                  className={cn(
                    'mb-2 font-semibold text-lg',
                    aiQuota.ai_remaining === 0 ? 'text-amber-300' : 'text-purple-300'
                  )}
                >
                  {aiQuota.ai_remaining === 0
                    ? 'AI Analysis Quota Exhausted'
                    : `${aiQuota.ai_remaining} AI Analysis${aiQuota.ai_remaining === 1 ? '' : 'es'} Remaining`}
                </h3>
                <p className="mb-4 text-gray-300 text-sm leading-relaxed">
                  {aiQuota.message}{' '}
                  {aiQuota.ai_remaining === 0 &&
                    'We hope the AI insights generated by Exiqus gave you a glimpse into the powerful analysis capabilities we provide!'}
                </p>

                {/* Quota Progress Bar */}
                <div className="mb-4">
                  <div className="mb-2 flex items-center justify-between text-gray-400 text-xs">
                    <span>AI Analyses Used</span>
                    <span>
                      {aiQuota.ai_used}/{aiQuota.ai_quota_limit}
                    </span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-white/10">
                    <div
                      className={cn(
                        'h-full transition-all duration-500',
                        aiQuota.ai_remaining === 0
                          ? 'bg-gradient-to-r from-amber-500 to-orange-500'
                          : 'bg-gradient-to-r from-purple-500 to-blue-500'
                      )}
                      style={{ width: `${(aiQuota.ai_used / aiQuota.ai_quota_limit) * 100}%` }}
                    />
                  </div>
                </div>

                {aiQuota.upgrade_available && (
                  <ExiqusButton
                    variant="secondary"
                    size="sm"
                    onClick={() => router.push('/pricing')}
                    className="border-purple-500/30 bg-purple-500/10 hover:bg-purple-500/20"
                  >
                    <Zap className="mr-2 h-4 w-4" />
                    Upgrade for More AI Analyses
                  </ExiqusButton>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Enhanced Stats Grid with visual improvements */}
        <div className="mb-10 grid grid-cols-1 gap-6 lg:grid-cols-4">
          {/* Usage Card with Progress Bar */}
          <ExiqusCard
            className="bg-gradient-to-br from-purple-900/20 to-transparent p-6"
            glow="purple"
          >
            <div className="mb-4 flex items-center justify-between">
              <h3 className="font-medium text-gray-400 text-sm">Monthly Usage</h3>
              <BarChart className="h-5 w-5 text-purple-400" />
            </div>
            <div className="space-y-4">
              {/* Candidate Assessments - Paid plans only */}
              {candidateLimit > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center gap-1 text-gray-500 text-xs">
                    <Users className="h-3 w-3" />
                    <span>Candidates</span>
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="font-bold text-2xl text-gray-100">
                      {loadingCandidates ? (
                        <Loader2 className="h-5 w-5 animate-spin" />
                      ) : (
                        candidatesCount
                      )}
                    </span>
                    <span className="text-gray-500 text-sm">/ {candidateLimit}</span>
                  </div>
                  <Progress value={candidateUsagePercentage} className="h-1.5" />
                </div>
              )}

              {/* Repository Deep Dives */}
              <div className="space-y-2">
                <div className="flex items-center gap-1 text-gray-500 text-xs">
                  <GitBranch className="h-3 w-3" />
                  <span>Repository Deep Dives</span>
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="font-bold text-2xl text-gray-100">
                    {loadingAnalyses ? <Loader2 className="h-5 w-5 animate-spin" /> : analysesCount}
                  </span>
                  <span className="text-gray-500 text-sm">
                    / {planLimit === -1 ? '∞' : planLimit}
                  </span>
                </div>
                {planLimit !== -1 && <Progress value={usagePercentage} className="h-1.5" />}
              </div>
            </div>
          </ExiqusCard>

          {/* Plan Status Card with Icon */}
          <ExiqusCard className="bg-gradient-to-br from-blue-900/20 to-transparent p-6" glow="blue">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="font-medium text-gray-400 text-sm">Current Plan</h3>
              <Zap className="h-5 w-5 text-blue-400" />
            </div>
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Target className="h-8 w-8 text-blue-500" />
                <div>
                  <div className="font-bold text-2xl text-gray-100">
                    {user.subscription_plan === 'free'
                      ? 'Free'
                      : user.subscription_plan === 'starter'
                        ? 'Starter'
                        : user.subscription_plan === 'growth'
                          ? 'Growth'
                          : user.subscription_plan === 'scale'
                            ? 'Scale'
                            : user.subscription_plan === 'scale_plus'
                              ? 'Scale+'
                              : user.subscription_plan}
                  </div>
                  <p className="text-gray-500 text-xs">Active subscription</p>
                </div>
              </div>
            </div>
          </ExiqusCard>

          {/* Last Analysis Card with Time */}
          <ExiqusCard
            className="bg-gradient-to-br from-green-900/20 to-transparent p-6"
            glow="green"
          >
            <div className="mb-4 flex items-center justify-between">
              <h3 className="font-medium text-gray-400 text-sm">Last Analysis</h3>
              <Clock className="h-5 w-5 text-green-400" />
            </div>
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Calendar className="h-8 w-8 text-green-500" />
                <div>
                  <div className="font-bold text-gray-100 text-lg">
                    {loadingAnalyses ? (
                      <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
                    ) : lastAnalysis ? (
                      format(lastAnalysis, 'MMM d')
                    ) : (
                      'Never'
                    )}
                  </div>
                  <p className="text-gray-500 text-xs">
                    {lastAnalysis ? format(lastAnalysis, 'h:mm a') : 'Start analyzing'}
                  </p>
                </div>
              </div>
            </div>
          </ExiqusCard>

          {/* Quick Stats Card */}
          <ExiqusCard
            className="bg-gradient-to-br from-orange-900/20 to-transparent p-6"
            glow="subtle"
          >
            <div className="mb-4 flex items-center justify-between">
              <h3 className="font-medium text-gray-400 text-sm">This Week</h3>
              <Activity className="h-5 w-5 text-orange-400" />
            </div>
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <TrendingUp className="h-8 w-8 text-orange-500" />
                <div>
                  <div className="font-bold text-2xl text-gray-100">
                    {loadingAnalyses ? <Loader2 className="h-6 w-6 animate-spin" /> : weeklyCount}
                  </div>
                  <p className="text-gray-500 text-xs">Analyses completed</p>
                </div>
              </div>
            </div>
          </ExiqusCard>
        </div>

        {/* Quick Actions - Candidate-Centric with Emerald Primary CTA */}
        <div className="mb-10 grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Primary: Assess Candidate (Emerald - Growth Action) */}
          <ExiqusCard
            className="bg-gradient-to-br from-emerald-900/10 to-green-900/10 p-8"
            glow="subtle"
          >
            <div className="mb-6">
              <div className="mb-2 flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-600 to-green-600">
                  <Users className="h-5 w-5 text-white" />
                </div>
                <h2 className="font-semibold text-gray-100 text-xl">Assess Candidate</h2>
              </div>
              <p className="text-gray-400 text-sm">
                Evaluate a developer&apos;s complete GitHub portfolio and contributions
              </p>
            </div>
            <div className="flex flex-col gap-3">
              <ExiqusButton
                onClick={() => router.push('/portfolio-analysis')}
                size="lg"
                className="w-full bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-500 hover:to-green-500"
              >
                <Sparkles className="mr-2 h-4 w-4" />
                Assess New Candidate
                <ArrowUpRight className="ml-2 h-4 w-4" />
              </ExiqusButton>
              <ExiqusButton
                onClick={() => router.push('/candidate-hub')}
                variant="secondary"
                size="lg"
                className="w-full"
              >
                <Clock className="mr-2 h-4 w-4" />
                View Candidate Assessments
              </ExiqusButton>
            </div>
          </ExiqusCard>

          {/* Secondary: PR Analysis */}
          <ExiqusCard
            className="bg-gradient-to-br from-teal-900/10 to-cyan-900/10 p-8"
            glow="subtle"
          >
            <div className="mb-6">
              <div className="mb-2 flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-teal-600 to-cyan-600">
                  <GitPullRequest className="h-5 w-5 text-white" />
                </div>
                <h2 className="font-semibold text-gray-100 text-xl">PR Analysis</h2>
              </div>
              <p className="text-gray-400 text-sm">
                Analyze pull requests for code review insights
              </p>
            </div>
            <div className="flex flex-col gap-3">
              <ExiqusButton
                onClick={() => router.push('/pr-analysis')}
                size="lg"
                className="w-full bg-gradient-to-r from-teal-600 to-cyan-600 hover:from-teal-500 hover:to-cyan-500"
              >
                <GitPullRequest className="mr-2 h-4 w-4" />
                Analyze PR
                <ArrowUpRight className="ml-2 h-4 w-4" />
              </ExiqusButton>
              <ExiqusButton
                onClick={() => router.push('/pr-analyses')}
                variant="secondary"
                size="lg"
                className="w-full"
              >
                <Clock className="mr-2 h-4 w-4" />
                View PR Analysis History
              </ExiqusButton>
            </div>
          </ExiqusCard>

          {/* Tertiary: Repository Deep Dive */}
          <ExiqusCard
            className="bg-gradient-to-br from-purple-900/10 to-blue-900/10 p-8"
            glow="subtle"
          >
            <div className="mb-6">
              <div className="mb-2 flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-purple-600 to-blue-600">
                  <Brain className="h-5 w-5 text-white" />
                </div>
                <h2 className="font-semibold text-gray-100 text-xl">Repository Deep Dive</h2>
              </div>
              <p className="text-gray-400 text-sm">Analyze a specific repository in detail</p>
            </div>
            <div className="flex flex-col gap-3">
              <ExiqusButton onClick={() => router.push('/analyze')} size="lg" className="w-full">
                <GitBranch className="mr-2 h-4 w-4" />
                Analyze Repository
                <ArrowUpRight className="ml-2 h-4 w-4" />
              </ExiqusButton>
              <ExiqusButton
                onClick={() => router.push('/analyses')}
                variant="secondary"
                size="lg"
                className="w-full"
              >
                <Clock className="mr-2 h-4 w-4" />
                View Analysis History
              </ExiqusButton>
            </div>
          </ExiqusCard>
        </div>

        {/* Recent Candidate Assessments - Candidate-Centric View */}
        {candidateLimit > 0 && (
          <div className="mb-10 rounded-xl bg-gradient-to-br from-emerald-900/5 via-transparent to-green-900/5 p-6">
            <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="font-semibold text-2xl text-gray-100">
                  Recent Candidate Assessments
                </h2>
                <p className="mt-1 text-gray-400 text-sm">
                  Candidates you&apos;ve analyzed recently
                </p>
              </div>
              {recentCandidates.length > 0 && (
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                  {/* Search Input */}
                  <div className="relative">
                    <Search className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-gray-500" />
                    <input
                      type="text"
                      placeholder="Search candidates..."
                      value={candidateSearchQuery}
                      onChange={(e) => setCandidateSearchQuery(e.target.value)}
                      className="h-10 w-full rounded-lg border border-white/[0.08] bg-black/40 py-2 pr-4 pl-10 text-gray-300 text-sm placeholder-gray-500 transition-colors focus:border-emerald-500/50 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 sm:w-64"
                    />
                  </div>
                  <ExiqusButton
                    variant="ghost"
                    onClick={() => router.push('/candidate-hub')}
                    className="text-emerald-400 hover:text-emerald-300"
                  >
                    View All
                    <ChevronRight className="ml-1 h-4 w-4" />
                  </ExiqusButton>
                </div>
              )}
            </div>

            {loadingCandidates ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-emerald-500" />
              </div>
            ) : recentCandidates.length === 0 ? (
              <div className="rounded-xl border border-white/[0.08] bg-black/20 p-12 text-center">
                <Users className="mx-auto mb-4 h-12 w-12 text-gray-600" />
                <h3 className="mb-2 font-semibold text-gray-300 text-lg">
                  No Candidates Assessed Yet
                </h3>
                <p className="mb-6 text-gray-500 text-sm">
                  Start assessing candidates to see them here
                </p>
                <ExiqusButton
                  onClick={() => router.push('/portfolio-analysis')}
                  className="bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-500 hover:to-green-500"
                >
                  <Sparkles className="mr-2 h-4 w-4" />
                  Assess First Candidate
                </ExiqusButton>
              </div>
            ) : filteredCandidates.length === 0 ? (
              <div className="rounded-xl border border-white/[0.08] bg-black/20 p-12 text-center">
                <Search className="mx-auto mb-4 h-12 w-12 text-gray-600" />
                <h3 className="mb-2 font-semibold text-gray-300 text-lg">No Results Found</h3>
                <p className="mb-6 text-gray-500 text-sm">
                  No candidates match &quot;{candidateSearchQuery}&quot;
                </p>
                <ExiqusButton
                  variant="secondary"
                  onClick={() => setCandidateSearchQuery('')}
                  size="sm"
                >
                  Clear Search
                </ExiqusButton>
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                {filteredCandidates.map((candidate) => (
                  <ExiqusCard
                    key={candidate.username}
                    className={cn(
                      'group cursor-pointer p-5 transition-all hover:scale-[1.02]',
                      'border-2 bg-gradient-to-br from-emerald-900/10 to-transparent',
                      'border-white/[0.09] hover:border-emerald-500/30'
                    )}
                    glow="subtle"
                    onClick={() => router.push(`/candidate-hub/${candidate.username}`)}
                  >
                    {/* Candidate Header */}
                    <div className="mb-4 flex items-start gap-3">
                      <div className="relative">
                        <Image
                          src={candidate.avatar_url}
                          alt={`${candidate.username}'s avatar`}
                          width={48}
                          height={48}
                          className="rounded-full ring-2 ring-white/10"
                        />
                      </div>
                      <div className="flex-1">
                        <h3 className="font-semibold text-gray-100 group-hover:text-emerald-400">
                          {candidate.username}
                        </h3>
                        <p className="text-gray-500 text-xs">
                          {format(new Date(candidate.latest_activity), 'MMM d, yyyy')}
                        </p>
                      </div>
                    </div>

                    {/* Analysis Type Badges */}
                    <div className="mb-3 flex flex-wrap gap-1.5">
                      {candidate.has_portfolio && (
                        <Badge
                          variant="outline"
                          className="border-indigo-500/30 bg-indigo-900/20 text-indigo-400 text-xs"
                        >
                          <Brain className="mr-1 h-3 w-3" />
                          Portfolio
                        </Badge>
                      )}
                      {candidate.has_pr && (
                        <Badge
                          variant="outline"
                          className="border-teal-500/30 bg-teal-900/20 text-teal-400 text-xs"
                        >
                          <GitPullRequest className="mr-1 h-3 w-3" />
                          PRs
                        </Badge>
                      )}
                      {candidate.repo_count > 0 && (
                        <Badge
                          variant="outline"
                          className="border-purple-500/30 bg-purple-900/20 text-purple-400 text-xs"
                        >
                          <FileCode2 className="mr-1 h-3 w-3" />
                          {candidate.repo_count} {candidate.repo_count === 1 ? 'Repo' : 'Repos'}
                        </Badge>
                      )}
                    </div>

                    {/* Portfolio Summary */}
                    {candidate.portfolio_summary && (
                      <p className="line-clamp-2 text-gray-400 text-xs">
                        {candidate.portfolio_summary}
                      </p>
                    )}

                    {/* View Details Link */}
                    <div className="mt-4 flex items-center text-emerald-400 text-xs opacity-0 transition-opacity group-hover:opacity-100">
                      View Details
                      <ArrowUpRight className="ml-1 h-3 w-3" />
                    </div>
                  </ExiqusCard>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Recent Repository Analyses - Grid Layout */}
        <div className="rounded-xl bg-gradient-to-br from-emerald-900/5 via-transparent to-green-900/5 p-6">
          <div className="mb-6 flex items-center justify-between">
            <div>
              <h2 className="font-semibold text-2xl text-gray-100">Recent Repository Analyses</h2>
              <p className="mt-1 text-gray-400 text-sm">Your latest repository deep dives</p>
            </div>
            {recentAnalyses.length > 0 && (
              <ExiqusButton
                variant="ghost"
                onClick={() => router.push('/analyses')}
                className="text-purple-400 hover:text-purple-300"
              >
                View All
                <ChevronRight className="ml-1 h-4 w-4" />
              </ExiqusButton>
            )}
          </div>

          {loadingAnalyses ? (
            <ExiqusCard className="p-12">
              <div className="flex items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-purple-400" />
              </div>
            </ExiqusCard>
          ) : recentAnalyses.length > 0 ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {recentAnalyses.map((analysis) => (
                <ExiqusCard
                  key={analysis.id}
                  className="group cursor-pointer p-5 transition-all hover:scale-[1.02] hover:shadow-2xl"
                  onClick={() => router.push(`/analyses/${analysis.id}`)}
                  glow="hover"
                >
                  <div className="flex h-full flex-col">
                    <div className="mb-3 flex items-start justify-between">
                      <div className="flex items-center gap-2">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-purple-600/20 to-blue-600/20">
                          <GitBranch className="h-5 w-5 text-purple-400" />
                        </div>
                        <div
                          className={cn(
                            'rounded-full px-2.5 py-0.5 font-medium text-xs',
                            analysis.context === 'startup'
                              ? 'bg-purple-500/20 text-purple-300 ring-1 ring-purple-500/30'
                              : analysis.context === 'enterprise'
                                ? 'bg-blue-500/20 text-blue-300 ring-1 ring-blue-500/30'
                                : analysis.context === 'agency'
                                  ? 'bg-amber-500/20 text-amber-300 ring-1 ring-amber-500/30'
                                  : analysis.context === 'open_source'
                                    ? 'bg-green-500/20 text-green-300 ring-1 ring-green-500/30'
                                    : 'bg-gray-500/20 text-gray-300 ring-1 ring-gray-500/30'
                          )}
                        >
                          {analysis.context === 'open_source'
                            ? 'Open Source'
                            : analysis.context === 'startup'
                              ? 'Startup'
                              : analysis.context === 'enterprise'
                                ? 'Enterprise'
                                : analysis.context === 'agency'
                                  ? 'Agency'
                                  : analysis.context || 'Startup'}
                        </div>
                        {analysis.batch_id && (
                          <Badge className="border-purple-500/30 bg-purple-500/10 text-purple-300">
                            Batch #{analysis.batch_id.slice(0, 8)}
                          </Badge>
                        )}
                      </div>
                      <ArrowUpRight className="h-4 w-4 text-gray-500 transition-colors group-hover:text-purple-400" />
                    </div>

                    <div className="flex-1">
                      <h3 className="mb-1 line-clamp-1 font-semibold text-gray-100">
                        {analysis.repository_name}
                      </h3>
                      <p className="mb-3 text-gray-400 text-sm">
                        Analyzed {format(new Date(analysis.created_at), 'MMM d, yyyy')}
                      </p>
                      {/* Show key insight/summary if available */}
                      {analysis.key_insight && (
                        <p className="mb-2 line-clamp-2 text-gray-500 text-xs">
                          {analysis.key_insight}
                        </p>
                      )}
                    </div>

                    <div className="flex items-center justify-between border-gray-800 border-t pt-3">
                      <span className="text-gray-500 text-xs">
                        {format(new Date(analysis.created_at), 'h:mm a')}
                      </span>
                    </div>
                  </div>
                </ExiqusCard>
              ))}
            </div>
          ) : (
            <ExiqusCard className="bg-gradient-to-br from-purple-900/5 to-blue-900/5 p-16 text-center">
              <div className="flex flex-col items-center justify-center">
                <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-purple-600/20 to-blue-600/20">
                  <GitBranch className="h-8 w-8 text-purple-400" />
                </div>
                <h3 className="mb-2 font-semibold text-gray-100 text-lg">No analyses yet</h3>
                <p className="mb-6 max-w-sm text-gray-400">
                  Start analyzing repositories to get AI-powered insights and evidence-based
                  candidate insights
                </p>
                <ExiqusButton onClick={() => router.push('/analyze')} size="lg">
                  <Sparkles className="mr-2 h-4 w-4" />
                  Start Your First Analysis
                </ExiqusButton>
              </div>
            </ExiqusCard>
          )}
        </div>
      </div>
    </div>
  );
}
