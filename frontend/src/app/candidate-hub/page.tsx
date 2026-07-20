// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

/* eslint-disable import/order */
'use client';

import {
  Activity,
  ArrowRight,
  Calendar,
  CheckCircle2,
  Circle,
  FolderGit2,
  GitBranch,
  GitPullRequest,
  Loader2,
  Plus,
  Search,
  Users,
} from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { ExiqusButton, ExiqusCard, GradientText } from '@/components/ui/exiqus-components';
import { useAuth } from '@/contexts/auth-context';
import { useAuthGuard } from '@/hooks/use-auth-guard';
import { api } from '@/lib/api-client';

interface Candidate {
  username: string;
  avatar_url: string;
  has_portfolio: boolean;
  has_pr: boolean;
  repo_count: number;
  latest_activity: string;
  portfolio_summary: string;
}

function CandidateHubPage() {
  const router = useRouter();
  const { user } = useAuth();
  const { isLoading, showUnauthorized, UnauthorizedComponent } = useAuthGuard();
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  const fetchCandidates = async () => {
    if (!user) return;

    try {
      setLoading(true);
      const response = await api.getDashboardCandidates({ limit: 100 });
      setCandidates(response.data || []);
    } catch (error) {
      console.error('Error fetching candidates:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user) {
      fetchCandidates();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  // Helper functions
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const formatTimeAgo = (date: Date) => {
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 60) return `${diffMins} ${diffMins === 1 ? 'min' : 'mins'} ago`;
    if (diffHours < 24) return `${diffHours} ${diffHours === 1 ? 'hr' : 'hrs'} ago`;
    if (diffDays < 7) return `${diffDays} ${diffDays === 1 ? 'day' : 'days'} ago`;
    return formatDate(date.toISOString());
  };

  const filteredCandidates = candidates.filter((candidate) =>
    candidate.username.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Calculate aggregate statistics
  const _completeCandidates = candidates.filter((c) => c.has_portfolio && c.has_pr).length;
  const _assessedCandidates = candidates.filter((c) => c.has_portfolio || c.has_pr).length;

  // Analysis Coverage categorization
  // High: Has both Portfolio AND PR (repo count doesn't matter)
  const highCoverage = candidates.filter((c) => c.has_portfolio && c.has_pr).length;
  // Moderate: Has Portfolio OR PR, but not both
  const moderateCoverage = candidates.filter(
    (c) => (c.has_portfolio || c.has_pr) && !(c.has_portfolio && c.has_pr)
  ).length;
  // Low: Has only individual repo analyses, no Portfolio or PR
  const lowCoverage = candidates.filter(
    (c) => !c.has_portfolio && !c.has_pr && c.repo_count > 0
  ).length;

  // Last activity
  const mostRecent = candidates.length > 0 ? candidates[0] : null;
  const lastActivityText = mostRecent ? formatTimeAgo(new Date(mostRecent.latest_activity)) : 'N/A';

  const stats = {
    totalCandidates: candidates.length,
    portfolioAnalyses: candidates.filter((c) => c.has_portfolio).length,
    prAnalyses: candidates.filter((c) => c.has_pr).length,
    totalRepoAnalyses: candidates.reduce((sum, c) => sum + c.repo_count, 0),
    highCoverage,
    moderateCoverage,
    lowCoverage,
    lastActivity: lastActivityText,
  };

  // Show auth guard if unauthorized
  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-gray-950 via-gray-900 to-black">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-400" />
      </div>
    );
  }

  if (showUnauthorized && UnauthorizedComponent) {
    return <UnauthorizedComponent />;
  }

  return (
    <div className="min-h-screen bg-[#0A0A0A]">
      {/* Multi-gradient animated background */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 -left-40 h-80 w-80 animate-pulse rounded-full bg-emerald-500/20 blur-3xl"></div>
        <div className="absolute -top-20 right-0 h-80 w-80 animate-pulse rounded-full bg-teal-500/20 blur-3xl delay-700"></div>
        <div className="absolute top-20 left-1/3 h-80 w-80 animate-pulse rounded-full bg-indigo-500/20 blur-3xl delay-1000"></div>
      </div>

      <div className="relative mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <div className="mb-2 flex items-center gap-2 text-gray-400 text-sm">
            <Users className="h-4 w-4" />
            <span>Candidate Hub</span>
          </div>
          <div className="mb-4">
            <h1 className="font-bold text-4xl">
              <GradientText>Candidate Intelligence Hub</GradientText>
            </h1>
            <p className="mt-2 text-gray-400 text-lg">
              Comprehensive candidate intelligence and insight management powered by advanced
              portfolio and PR analysis
            </p>
          </div>
          {!loading && candidates.length > 0 && (
            <div className="space-y-4">
              <div className="flex gap-2">
                <ExiqusButton
                  onClick={() => router.push('/portfolio-analysis')}
                  className="bg-gradient-to-r from-indigo-600 to-indigo-700"
                  size="sm"
                >
                  <Plus className="mr-1 h-4 w-4" />
                  Portfolio
                </ExiqusButton>
                <ExiqusButton
                  onClick={() => router.push('/pr-analysis')}
                  className="bg-gradient-to-r from-teal-600 to-teal-700"
                  size="sm"
                >
                  <Plus className="mr-1 h-4 w-4" />
                  PR Analysis
                </ExiqusButton>
                <ExiqusButton
                  onClick={() => router.push('/analyze')}
                  className="bg-gradient-to-r from-purple-600 to-purple-700"
                  size="sm"
                >
                  <Plus className="mr-1 h-4 w-4" />
                  Single Repo
                </ExiqusButton>
              </div>
              <div className="relative max-w-md">
                <Search className="absolute top-1/2 left-3 h-5 w-5 -translate-y-1/2 text-gray-500" />
                <input
                  type="text"
                  placeholder="Search candidates..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="h-11 w-full rounded-lg border border-white/[0.08] bg-black/40 py-2 pr-4 pl-10 text-gray-300 placeholder-gray-500 transition-colors focus:border-emerald-500/50 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                />
              </div>
            </div>
          )}
        </div>

        {/* Pipeline Intelligence Overview - Only show when candidates exist */}
        {!loading && candidates.length > 0 && (
          <>
            {/* Pipeline Overview */}
            <ExiqusCard className="mb-6 p-6">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="font-semibold text-gray-200 text-xl">Pipeline Overview</h2>
                <div className="text-gray-500 text-sm">Last Activity: {stats.lastActivity}</div>
              </div>
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="flex items-center gap-3">
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-600 to-indigo-800">
                    <FolderGit2 className="h-6 w-6 text-white" />
                  </div>
                  <div>
                    <p className="text-gray-500 text-sm">Portfolio Analyses</p>
                    <p className="font-bold text-2xl text-gray-100">{stats.portfolioAnalyses}</p>
                    <p className="text-gray-600 text-xs">Complete</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-teal-600 to-teal-800">
                    <GitPullRequest className="h-6 w-6 text-white" />
                  </div>
                  <div>
                    <p className="text-gray-500 text-sm">PR Analyses</p>
                    <p className="font-bold text-2xl text-gray-100">{stats.prAnalyses}</p>
                    <p className="text-gray-600 text-xs">Complete</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-purple-600 to-purple-800">
                    <GitBranch className="h-6 w-6 text-white" />
                  </div>
                  <div>
                    <p className="text-gray-500 text-sm">Repo Deep Dives</p>
                    <p className="font-bold text-2xl text-gray-100">{stats.totalRepoAnalyses}</p>
                    <p className="text-gray-600 text-xs">Complete</p>
                  </div>
                </div>
              </div>
            </ExiqusCard>

            {/* Analysis Coverage */}
            <ExiqusCard className="mb-6 p-6">
              <h2 className="mb-4 font-semibold text-gray-200 text-xl">Analysis Coverage</h2>
              <div className="grid gap-4 sm:grid-cols-3">
                {/* High Coverage Card */}
                <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-4">
                  <div className="mb-2 flex items-center gap-2">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/20">
                      <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                    </div>
                    <div className="flex-1">
                      <p className="text-gray-500 text-xs">High Coverage</p>
                      <p className="font-bold text-2xl text-emerald-400">{stats.highCoverage}</p>
                    </div>
                  </div>
                  <p className="text-gray-400 text-xs">Portfolio + PR + Repo analyses complete</p>
                </div>

                {/* Moderate Coverage Card */}
                <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-4">
                  <div className="mb-2 flex items-center gap-2">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-500/20">
                      <Activity className="h-5 w-5 text-amber-400" />
                    </div>
                    <div className="flex-1">
                      <p className="text-gray-500 text-xs">Moderate Coverage</p>
                      <p className="font-bold text-2xl text-amber-400">{stats.moderateCoverage}</p>
                    </div>
                  </div>
                  <p className="text-gray-400 text-xs">Portfolio or PR analysis only</p>
                </div>

                {/* Low Coverage Card */}
                <div className="rounded-lg border border-gray-500/20 bg-gray-500/5 p-4">
                  <div className="mb-2 flex items-center gap-2">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gray-500/20">
                      <Circle className="h-5 w-5 text-gray-400" />
                    </div>
                    <div className="flex-1">
                      <p className="text-gray-500 text-xs">Low Coverage</p>
                      <p className="font-bold text-2xl text-gray-400">{stats.lowCoverage}</p>
                    </div>
                  </div>
                  <p className="text-gray-400 text-xs">Limited data—recommend analysis</p>
                </div>
              </div>
            </ExiqusCard>

            {/* Data Scope Note */}
            <div className="mb-6 rounded-lg border border-blue-500/20 bg-blue-500/5 p-4">
              <div className="flex items-start gap-3">
                <div className="mt-0.5 text-blue-400">
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                </div>
                <div className="flex-1">
                  <h3 className="mb-1 font-semibold text-blue-300 text-sm">Data Scope Note</h3>
                  <p className="text-gray-400 text-sm">
                    All analyses are based on <strong>public GitHub data only</strong>. Private
                    repositories and proprietary work are not included in insights. This provides
                    evidence-based insights while respecting privacy and confidentiality.
                  </p>
                </div>
              </div>
            </div>

            {/* Recent Activity - Horizontal Carousel */}
            <div className="mb-6">
              <h2 className="mb-3 font-semibold text-gray-200 text-lg">Recent Activity</h2>
              <div className="flex gap-3 overflow-x-auto pb-2">
                {candidates.slice(0, 6).map((candidate) => {
                  return (
                    <Link
                      key={candidate.username}
                      href={`/candidate-hub/${candidate.username}`}
                      className="group min-w-[220px] flex-shrink-0 cursor-pointer rounded-lg border border-white/[0.06] bg-white/[0.02] p-4 transition-all hover:border-violet-500/30 hover:bg-white/[0.04]"
                    >
                      <div className="mb-2 flex items-center gap-2">
                        <span className="truncate font-medium text-gray-300 text-sm transition-colors group-hover:text-violet-400">
                          {candidate.username}
                        </span>
                      </div>
                      <div className="mb-3 text-gray-500 text-xs">
                        {formatTimeAgo(new Date(candidate.latest_activity))}
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {candidate.has_portfolio && (
                          <span className="inline-flex items-center gap-1 rounded-full border border-violet-500/30 bg-violet-500/10 px-1.5 py-0.5 font-medium text-[10px] text-violet-300">
                            <FolderGit2 className="h-2.5 w-2.5" />
                            Portfolio
                          </span>
                        )}
                        {candidate.has_pr && (
                          <span className="inline-flex items-center gap-1 rounded-full border border-cyan-500/30 bg-cyan-500/10 px-1.5 py-0.5 font-medium text-[10px] text-cyan-300">
                            <GitPullRequest className="h-2.5 w-2.5" />
                            PR
                          </span>
                        )}
                        {candidate.repo_count > 0 && (
                          <span className="inline-flex items-center gap-1 rounded-full border border-purple-500/30 bg-purple-500/10 px-1.5 py-0.5 font-medium text-[10px] text-purple-300">
                            <GitBranch className="h-2.5 w-2.5" />
                            {candidate.repo_count}
                          </span>
                        )}
                      </div>
                    </Link>
                  );
                })}
              </div>
            </div>
          </>
        )}

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-emerald-400" />
          </div>
        )}

        {/* Empty State */}
        {!loading && candidates.length === 0 && (
          <ExiqusCard className="p-12 text-center">
            <Users className="mx-auto mb-4 h-12 w-12 text-gray-600" />
            <h3 className="mb-2 font-semibold text-gray-300 text-lg">No Candidates Assessed Yet</h3>
            <p className="mb-6 text-gray-500">Start assessing candidates to see them here</p>
            <div className="flex flex-col items-center justify-center gap-3 sm:flex-row">
              <ExiqusButton
                onClick={() => router.push('/portfolio-analysis')}
                variant="primary"
                size="lg"
              >
                <FolderGit2 className="mr-2 h-4 w-4" />
                Assess via Portfolio
              </ExiqusButton>
              <ExiqusButton
                onClick={() => router.push('/pr-analysis')}
                variant="secondary"
                size="lg"
              >
                <GitPullRequest className="mr-2 h-4 w-4" />
                Assess via PR
              </ExiqusButton>
            </div>
          </ExiqusCard>
        )}

        {/* Candidates Grid */}
        {!loading && filteredCandidates.length > 0 && (
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {filteredCandidates.map((candidate) => {
              // Determine card border based on coverage
              const hasHighCoverage =
                candidate.has_portfolio && candidate.has_pr && candidate.repo_count > 0;
              const hasModerateCoverage =
                (candidate.has_portfolio || candidate.has_pr) && candidate.repo_count === 0;

              let borderClass = 'border-white/[0.08]';
              let hoverBorderClass = 'hover:border-emerald-500/40';
              let bgGradient = '';

              if (hasHighCoverage) {
                borderClass = 'border-emerald-500/20';
                hoverBorderClass = 'hover:border-emerald-500/50';
                bgGradient = 'bg-gradient-to-br from-emerald-500/[0.03] to-transparent';
              } else if (hasModerateCoverage) {
                borderClass = 'border-amber-500/15';
                hoverBorderClass = 'hover:border-amber-500/40';
                bgGradient = 'bg-gradient-to-br from-amber-500/[0.02] to-transparent';
              }

              return (
                <ExiqusCard
                  key={candidate.username}
                  className={`group cursor-pointer transition-all duration-300 hover:scale-[1.02] hover:shadow-emerald-500/10 hover:shadow-lg ${borderClass} ${hoverBorderClass} ${bgGradient}`}
                  onClick={() => router.push(`/candidate-hub/${candidate.username}`)}
                >
                  <div className="p-6">
                    {/* Avatar and Username */}
                    <div className="mb-4 flex items-center gap-4">
                      <div className="relative">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={candidate.avatar_url}
                          alt={candidate.username}
                          className="h-14 w-14 rounded-full ring-2 ring-emerald-500/20 ring-offset-2 ring-offset-[#0A0A0A] transition-all group-hover:ring-emerald-500/40"
                        />
                        {hasHighCoverage && (
                          <div className="absolute -right-1 -bottom-1 flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500 ring-2 ring-[#0A0A0A]">
                            <CheckCircle2 className="h-3 w-3 text-white" />
                          </div>
                        )}
                      </div>
                      <div className="min-w-0 flex-1">
                        <h3 className="truncate font-semibold text-gray-200 text-lg transition-colors group-hover:text-emerald-400">
                          {candidate.username}
                        </h3>
                        <div className="flex items-center gap-2 text-gray-500 text-xs">
                          <Calendar className="h-3 w-3" />
                          {formatDate(candidate.latest_activity)}
                        </div>
                      </div>
                    </div>

                    {/* Analysis Types */}
                    <div className="mb-4 flex flex-wrap gap-2">
                      {candidate.has_portfolio && (
                        <div className="flex items-center gap-1 rounded-full bg-indigo-500/10 px-2.5 py-1 font-medium text-indigo-400 text-xs ring-1 ring-indigo-500/20 transition-all group-hover:bg-indigo-500/15 group-hover:ring-indigo-500/30">
                          <FolderGit2 className="h-3 w-3" />
                          Portfolio
                        </div>
                      )}
                      {candidate.has_pr && (
                        <div className="flex items-center gap-1 rounded-full bg-teal-500/10 px-2.5 py-1 font-medium text-teal-400 text-xs ring-1 ring-teal-500/20 transition-all group-hover:bg-teal-500/15 group-hover:ring-teal-500/30">
                          <GitPullRequest className="h-3 w-3" />
                          PR Analysis
                        </div>
                      )}
                      {candidate.repo_count > 0 && (
                        <div className="flex items-center gap-1 rounded-full bg-purple-500/10 px-2.5 py-1 font-medium text-purple-400 text-xs ring-1 ring-purple-500/20 transition-all group-hover:bg-purple-500/15 group-hover:ring-purple-500/30">
                          <FolderGit2 className="h-3 w-3" />
                          {candidate.repo_count} {candidate.repo_count === 1 ? 'Repo' : 'Repos'}
                        </div>
                      )}
                    </div>

                    {/* Summary */}
                    {candidate.portfolio_summary && (
                      <p className="mb-4 line-clamp-2 text-gray-400 text-sm leading-relaxed">
                        {candidate.portfolio_summary}
                      </p>
                    )}

                    {/* View Details Button */}
                    <div className="flex items-center justify-between rounded-lg bg-white/[0.02] px-3 py-2 transition-colors group-hover:bg-emerald-500/10">
                      <span className="font-medium text-gray-400 text-sm group-hover:text-emerald-400">
                        View Assessment
                      </span>
                      <ArrowRight className="h-4 w-4 text-gray-500 transition-transform group-hover:translate-x-1 group-hover:text-emerald-400" />
                    </div>
                  </div>
                </ExiqusCard>
              );
            })}
          </div>
        )}

        {/* No Results */}
        {!loading && candidates.length > 0 && filteredCandidates.length === 0 && (
          <ExiqusCard className="p-12 text-center">
            <Search className="mx-auto mb-4 h-12 w-12 text-gray-600" />
            <h3 className="mb-2 font-semibold text-gray-300 text-lg">No candidates found</h3>
            <p className="text-gray-500">Try adjusting your search query</p>
          </ExiqusCard>
        )}
      </div>
    </div>
  );
}

export default CandidateHubPage;
