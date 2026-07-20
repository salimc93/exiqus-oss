// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import { format } from 'date-fns';
import {
  Activity,
  ArrowRight,
  Calendar,
  FolderGit2,
  GitBranch,
  Loader2,
  Search,
  Sparkles,
  User,
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { ExiqusButton, ExiqusCard, GradientText } from '@/components/ui/exiqus-components';
import { UpgradePrompt } from '@/components/ui/upgrade-prompt';
import { useAuth } from '@/contexts/auth-context';
import { useAuthGuard } from '@/hooks/use-auth-guard';
import { api } from '@/lib/api-client';
import { cn } from '@/lib/utils';

interface PortfolioAnalysis {
  id: string;
  github_username: string;
  context: string;
  role: string;
  total_repos: number;
  repos_analyzed: number;
  repos_skipped: number;
  from_cache: boolean;
  created_at: string;
  analysis_metadata?: {
    portfolio_span_days?: number;
    model?: string;
    summary?: string;
  };
}

export default function PortfolioAnalysesPage() {
  const router = useRouter();
  const { user } = useAuth();
  const { isLoading: authLoading, showUnauthorized, UnauthorizedComponent } = useAuthGuard();
  const [analyses, setAnalyses] = useState<PortfolioAnalysis[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterContext, setFilterContext] = useState<string>('all');
  const [filterRole, setFilterRole] = useState<string>('all');

  useEffect(() => {
    const fetchAnalyses = async () => {
      try {
        setIsLoading(true);
        const response = await api.getPortfolioAnalyses({ limit: 100 });
        setAnalyses(response.data.analyses || []);
      } catch (error) {
        console.error('Failed to fetch portfolio analyses:', error);
        setAnalyses([]); // Ensure analyses is always an array even on error
      } finally {
        setIsLoading(false);
      }
    };

    fetchAnalyses();
  }, []);

  const filteredAnalyses = analyses.filter((analysis) => {
    const matchesSearch = analysis.github_username.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesContext = filterContext === 'all' || analysis.context === filterContext;
    const matchesRole = filterRole === 'all' || analysis.role === filterRole;
    return matchesSearch && matchesContext && matchesRole;
  });

  // Show auth loading state
  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0A0A0A]">
        <div className="text-center">
          <div className="mb-4 inline-flex h-16 w-16 items-center justify-center">
            <div className="h-12 w-12 animate-spin rounded-full border-4 border-purple-600 border-t-transparent" />
          </div>
          <p className="text-gray-400">Loading...</p>
        </div>
      </div>
    );
  }

  // Show unauthorized component
  if (showUnauthorized && UnauthorizedComponent) {
    return <UnauthorizedComponent />;
  }

  // Show upgrade prompt for FREE users (Portfolio analyses available on all paid tiers)
  if (user && user.subscription_plan === 'free') {
    return (
      <UpgradePrompt
        feature="Portfolio Analyses History"
        requiredTier="Starter"
        description="Access your complete history of candidate portfolio insights and technical intelligence."
      />
    );
  }

  return (
    <div className="min-h-screen bg-[#0A0A0A] py-8">
      {/* Animated gradient background */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 h-80 w-80 animate-pulse rounded-full bg-purple-500/20 blur-3xl"></div>
        <div className="absolute -bottom-40 -left-40 h-80 w-80 animate-pulse rounded-full bg-blue-500/20 blur-3xl delay-1000"></div>
      </div>

      <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-purple-900/20 to-blue-900/20 px-4 py-2 font-medium text-sm">
            <User className="h-4 w-4 text-purple-400" />
            Portfolio Analysis History
          </div>
          <h1 className="mb-2 font-bold text-4xl text-gray-100">
            <GradientText>Portfolio Analyses</GradientText>
          </h1>
          <p className="text-gray-400">
            View all your candidate portfolio insights and technical intelligence
          </p>
        </div>

        {/* Actions Bar */}
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-1 items-center gap-4">
            {/* Search */}
            <div className="relative max-w-md flex-1">
              <Search className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-gray-500" />
              <input
                type="text"
                placeholder="Search by username..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="h-10 w-full rounded-lg border border-white/[0.09] bg-white/[0.06] pr-4 pl-10 text-gray-100 text-sm outline-none placeholder:text-gray-500 focus:border-purple-500 focus:bg-white/[0.09]"
              />
            </div>

            {/* Filters */}
            <select
              value={filterContext}
              onChange={(e) => setFilterContext(e.target.value)}
              className="h-10 rounded-lg border border-white/[0.09] bg-white/[0.06] px-3 text-gray-100 text-sm outline-none focus:border-purple-500 focus:bg-white/[0.09] [&>option]:bg-gray-900 [&>option]:text-gray-100"
            >
              <option value="all">All Contexts</option>
              <option value="startup">Startup</option>
              <option value="enterprise">Enterprise</option>
              <option value="agency">Agency</option>
              <option value="open_source">Open Source</option>
            </select>

            <select
              value={filterRole}
              onChange={(e) => setFilterRole(e.target.value)}
              className="h-10 rounded-lg border border-white/[0.09] bg-white/[0.06] px-3 text-gray-100 text-sm outline-none focus:border-purple-500 focus:bg-white/[0.09] [&>option]:bg-gray-900 [&>option]:text-gray-100"
            >
              <option value="all">All Roles</option>
              <option value="junior">Junior</option>
              <option value="mid">Mid-Level</option>
              <option value="senior">Senior</option>
            </select>
          </div>

          <ExiqusButton onClick={() => router.push('/portfolio-analysis')}>
            <Sparkles className="mr-2 h-4 w-4" />
            New Analysis
          </ExiqusButton>
        </div>

        {/* Loading State */}
        {isLoading && (
          <ExiqusCard className="p-12">
            <div className="flex items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-purple-400" />
            </div>
          </ExiqusCard>
        )}

        {/* Empty State */}
        {!isLoading && analyses.length === 0 && (
          <ExiqusCard className="p-16 text-center" glow="subtle">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-purple-600/20 to-blue-600/20">
              <User className="h-8 w-8 text-purple-400" />
            </div>
            <h3 className="mb-2 font-semibold text-gray-100 text-lg">No portfolio analyses yet</h3>
            <p className="mb-6 text-gray-400">
              Start assessing candidates by analyzing their GitHub portfolios
            </p>
            <ExiqusButton onClick={() => router.push('/portfolio-analysis')} size="lg">
              <Sparkles className="mr-2 h-4 w-4" />
              Analyze Your First Portfolio
            </ExiqusButton>
          </ExiqusCard>
        )}

        {/* No Results State */}
        {!isLoading && analyses.length > 0 && filteredAnalyses.length === 0 && (
          <ExiqusCard className="p-12 text-center">
            <Search className="mx-auto mb-4 h-12 w-12 text-gray-500" />
            <h3 className="mb-2 font-semibold text-gray-100 text-lg">No results found</h3>
            <p className="text-gray-400">Try adjusting your search or filters</p>
          </ExiqusCard>
        )}

        {/* Analyses Grid */}
        {!isLoading && filteredAnalyses.length > 0 && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {filteredAnalyses.map((analysis) => (
              <ExiqusCard
                key={analysis.id}
                className="group cursor-pointer border-violet-500/10 transition-all duration-300 hover:scale-[1.02] hover:border-violet-500/30 hover:shadow-lg hover:shadow-violet-500/10"
                onClick={() => router.push(`/portfolio-analyses/${analysis.id}`)}
              >
                <div className="p-6">
                  {/* Avatar and Username */}
                  <div className="mb-4 flex items-center gap-4">
                    <div className="relative">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={`https://github.com/${analysis.github_username}.png`}
                        alt={analysis.github_username}
                        className="h-14 w-14 rounded-full ring-2 ring-violet-500/20 ring-offset-2 ring-offset-[#0A0A0A] transition-all group-hover:ring-violet-500/40"
                        onError={(e) => {
                          e.currentTarget.src = `https://ui-avatars.com/api/?name=${analysis.github_username}&background=7c3aed&color=fff`;
                        }}
                      />
                    </div>
                    <div className="min-w-0 flex-1">
                      <h3 className="truncate font-semibold text-gray-200 text-lg transition-colors group-hover:text-violet-400">
                        {analysis.github_username}
                      </h3>
                      <div className="flex items-center gap-2 text-gray-500 text-xs">
                        <Calendar className="h-3 w-3" />
                        {format(new Date(analysis.created_at), 'MMM d, yyyy')}
                      </div>
                    </div>
                  </div>

                  {/* Analysis Type Badge */}
                  <div className="mb-4">
                    <div className="flex w-fit items-center gap-1 rounded-full bg-indigo-500/10 px-2.5 py-1 font-medium text-indigo-400 text-xs ring-1 ring-indigo-500/20 transition-all group-hover:bg-indigo-500/15 group-hover:ring-indigo-500/30">
                      <FolderGit2 className="h-3 w-3" />
                      Portfolio
                    </div>
                  </div>

                  {/* Metrics */}
                  <div className="mb-4 space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="flex items-center gap-1 text-gray-400">
                        <GitBranch className="h-3 w-3" />
                        Repos Analyzed
                      </span>
                      <span className="font-medium text-gray-100">
                        {analysis.repos_analyzed}/{analysis.total_repos}
                      </span>
                    </div>
                    {analysis.analysis_metadata?.portfolio_span_days && (
                      <div className="flex items-center justify-between text-sm">
                        <span className="flex items-center gap-1 text-gray-400">
                          <Activity className="h-3 w-3" />
                          Activity Span
                        </span>
                        <span className="font-medium text-gray-100">
                          {Math.floor(analysis.analysis_metadata.portfolio_span_days / 365)} years
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Summary */}
                  <p className="mb-4 line-clamp-2 text-gray-400 text-sm leading-relaxed">
                    {analysis.repos_analyzed === 1
                      ? `Portfolio analysis of ${analysis.repos_analyzed} public repository`
                      : `Comprehensive analysis of ${analysis.repos_analyzed} public repositories across ${analysis.total_repos} total repos`}
                    {analysis.analysis_metadata?.portfolio_span_days &&
                      ` spanning ${Math.floor(analysis.analysis_metadata.portfolio_span_days / 365)} ${Math.floor(analysis.analysis_metadata.portfolio_span_days / 365) === 1 ? 'year' : 'years'} of activity`}
                    .
                  </p>

                  {/* Context and Role Tags */}
                  <div className="flex flex-wrap gap-2">
                    <div
                      className={cn(
                        'rounded-full px-2.5 py-0.5 font-medium text-xs ring-1',
                        analysis.context === 'startup'
                          ? 'bg-purple-500/10 text-purple-300 ring-purple-500/20'
                          : analysis.context === 'enterprise'
                            ? 'bg-blue-500/10 text-blue-300 ring-blue-500/20'
                            : analysis.context === 'agency'
                              ? 'bg-amber-500/10 text-amber-300 ring-amber-500/20'
                              : 'bg-green-500/10 text-green-300 ring-green-500/20'
                      )}
                    >
                      {analysis.context.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                    </div>
                    <div className="rounded-full bg-gray-500/10 px-2.5 py-0.5 font-medium text-gray-300 text-xs ring-1 ring-gray-500/20">
                      {analysis.role
                        ? analysis.role.charAt(0).toUpperCase() + analysis.role.slice(1)
                        : 'Mid'}
                    </div>
                    {analysis.from_cache && (
                      <div className="rounded-full bg-blue-500/10 px-2.5 py-0.5 font-medium text-blue-300 text-xs ring-1 ring-blue-500/20">
                        Cached
                      </div>
                    )}
                  </div>

                  {/* View Arrow */}
                  <div className="mt-4 flex items-center justify-end text-gray-500 text-xs transition-colors group-hover:text-violet-400">
                    <span className="mr-1">View Insights</span>
                    <ArrowRight className="h-3 w-3" />
                  </div>
                </div>
              </ExiqusCard>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
