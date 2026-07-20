// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import { formatDistanceToNow } from 'date-fns';
import {
  Activity,
  Calendar,
  ChevronRight,
  Filter,
  GitBranch,
  GitPullRequest,
  Loader2,
  Search,
  Sparkles,
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { ExiqusButton, ExiqusCard, GradientText } from '@/components/ui/exiqus-components';
import { UpgradePrompt } from '@/components/ui/upgrade-prompt';
import { useAuth } from '@/contexts/auth-context';
import { api } from '@/lib/api-client';

interface PRAnalysisItem {
  id: string;
  github_username: string;
  context: string;
  total_prs_analyzed: number;
  repositories_count?: number;
  data_quality: 'high' | 'moderate' | 'low';
  created_at: string;
  from_cache?: boolean;
  executive_summary?: string;
}

interface UsageStats {
  used_this_month: number;
  remaining_this_month: number;
  monthly_limit: number;
  reset_date?: string;
  days_until_reset?: number;
}

export default function PRAnalysesHistoryPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [analyses, setAnalyses] = useState<PRAnalysisItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterContext, setFilterContext] = useState<string>('all');
  const [usageStats, setUsageStats] = useState<UsageStats | null>(null);

  useEffect(() => {
    fetchAnalyses();
    fetchUsage();
  }, []);

  const fetchAnalyses = async () => {
    try {
      const response = await api.getPRAnalyses({ limit: 50 });
      setAnalyses(response.data.analyses || []);
    } catch (error) {
      console.error('Failed to fetch PR analyses:', error);
      setAnalyses([]); // Ensure analyses is always an array even on error
    } finally {
      setIsLoading(false);
    }
  };

  const fetchUsage = async () => {
    try {
      const response = await api.getPRAnalysisUsage();
      if (response.data.eligible) {
        setUsageStats(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch usage stats:', error);
    }
  };

  const filteredAnalyses = analyses.filter((analysis) => {
    const matchesSearch = analysis.github_username
      .toLowerCase()
      .includes(searchQuery.toLowerCase());
    const matchesContext =
      filterContext === 'all' || analysis.context.toLowerCase() === filterContext.toLowerCase();
    return matchesSearch && matchesContext;
  });

  const getDataQualityBadge = (quality: string) => {
    switch (quality) {
      case 'high':
        return (
          <span className="rounded-full border border-cyan-500/20 bg-cyan-900/30 px-2 py-1 text-cyan-300 text-xs">
            High Confidence
          </span>
        );
      case 'moderate':
        return (
          <span className="rounded-full border border-purple-500/20 bg-purple-900/30 px-2 py-1 text-purple-300 text-xs">
            Moderate Confidence
          </span>
        );
      case 'low':
        return (
          <span className="rounded-full border border-gray-500/20 bg-gray-900/30 px-2 py-1 text-gray-400 text-xs">
            Limited Confidence
          </span>
        );
      default:
        return null;
    }
  };

  const getContextBadge = (context: string) => {
    const bgColors = {
      startup: 'from-purple-900/20 to-pink-900/20',
      enterprise: 'from-blue-900/20 to-cyan-900/20',
      agency: 'from-orange-900/20 to-amber-900/20',
      open_source: 'from-green-900/20 to-emerald-900/20',
    };

    const ctx = context.toLowerCase() as keyof typeof bgColors;
    const bg = bgColors[ctx] || bgColors.startup;

    return (
      <span
        className={`rounded-full bg-gradient-to-r px-2 py-1 text-xs ${bg} border border-white/10 text-gray-300`}
      >
        {context}
      </span>
    );
  };

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0A0A0A]">
        <div className="text-center">
          <Loader2 className="mx-auto mb-4 h-12 w-12 animate-spin text-teal-400" />
          <p className="text-gray-400">Loading PR analysis history...</p>
        </div>
      </div>
    );
  }

  // Show upgrade prompt for FREE users (PR analyses available on all paid tiers)
  if (user && user.subscription_plan === 'free') {
    return (
      <UpgradePrompt
        feature="PR Analyses History"
        requiredTier="Starter"
        description="Access your complete history of developer PR contribution insights and collaboration patterns."
      />
    );
  }

  return (
    <div className="min-h-screen bg-[#0A0A0A]">
      {/* Animated gradient background - Teal/Cyan theme */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 h-80 w-80 animate-pulse rounded-full bg-teal-500/20 blur-3xl"></div>
        <div className="absolute -bottom-40 -left-40 h-80 w-80 animate-pulse rounded-full bg-cyan-500/20 blur-3xl delay-1000"></div>
      </div>

      <div className="container relative mx-auto max-w-7xl px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="mb-2 font-bold text-4xl">
            <GradientText className="bg-gradient-to-r from-teal-400 to-cyan-400">
              PR Analysis History
            </GradientText>
          </h1>
          <p className="text-gray-400 text-lg">Review your past developer insights</p>
        </div>

        {/* Actions Bar */}
        <div className="mb-8 flex flex-col gap-4 md:flex-row">
          <div className="relative flex-1">
            <Search className="absolute top-1/2 left-4 h-5 w-5 -translate-y-1/2 text-gray-500" />
            <input
              type="text"
              placeholder="Search by username..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-12 w-full rounded-lg border border-white/[0.09] bg-white/[0.06] pr-4 pl-12 text-gray-100 outline-none transition-all placeholder:text-gray-500 hover:bg-white/[0.08] focus:border-teal-500 focus:bg-white/[0.09]"
            />
          </div>

          <div className="flex gap-2">
            <select
              value={filterContext}
              onChange={(e) => setFilterContext(e.target.value)}
              className="h-12 rounded-lg border border-white/[0.09] bg-white/[0.06] px-4 text-gray-100 outline-none transition-all hover:bg-white/[0.08] focus:border-teal-500 [&>option]:bg-gray-900 [&>option]:text-gray-100"
            >
              <option value="all" className="bg-gray-900 text-gray-100">
                All Contexts
              </option>
              <option value="startup" className="bg-gray-900 text-gray-100">
                Startup
              </option>
              <option value="enterprise" className="bg-gray-900 text-gray-100">
                Enterprise
              </option>
              <option value="agency" className="bg-gray-900 text-gray-100">
                Agency
              </option>
              <option value="open_source" className="bg-gray-900 text-gray-100">
                Open Source
              </option>
            </select>

            <ExiqusButton
              onClick={() => router.push('/pr-analysis')}
              className="bg-gradient-to-r from-teal-600 to-cyan-600"
            >
              <GitPullRequest className="mr-2 h-4 w-4" />
              New Analysis
            </ExiqusButton>
          </div>
        </div>

        {/* Usage Stats & Info */}
        <div className="mb-8 space-y-4">
          {usageStats && (
            <div className="rounded-lg border border-teal-500/20 bg-gradient-to-r from-teal-900/20 to-cyan-900/20 p-6">
              <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
                <div className="flex items-center gap-3">
                  <Activity className="h-5 w-5 text-teal-400" />
                  <div>
                    <p className="font-medium text-gray-300 text-sm">PR Analyses This Month</p>
                    <p className="font-bold text-2xl text-teal-300">
                      {usageStats.remaining_this_month}
                      <span className="text-base text-gray-400"> / {usageStats.monthly_limit}</span>
                    </p>
                    <p className="mt-1 text-gray-500 text-xs">
                      {usageStats.used_this_month} used • {usageStats.remaining_this_month}{' '}
                      remaining
                      {usageStats.days_until_reset &&
                        ` • Resets in ${usageStats.days_until_reset} days`}
                    </p>
                  </div>
                </div>
                <ExiqusButton
                  onClick={() => router.push('/pr-analysis')}
                  className="whitespace-nowrap bg-gradient-to-r from-teal-600 to-cyan-600"
                >
                  <Sparkles className="mr-2 h-4 w-4" />
                  Analyze Another
                </ExiqusButton>
              </div>
            </div>
          )}

          {/* Showing Info */}
          {analyses.length > 0 && (
            <div className="rounded-lg border border-purple-500/20 bg-gradient-to-r from-purple-900/20 to-blue-900/20 p-4">
              <div className="flex items-center gap-2 text-gray-400 text-sm">
                <Filter className="h-4 w-4 text-purple-400" />
                <span>
                  Showing {filteredAnalyses.length} of {analyses.length} PR analyses
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Analyses Grid */}
        {filteredAnalyses.length === 0 ? (
          <ExiqusCard className="p-12 text-center">
            <GitPullRequest className="mx-auto mb-4 h-12 w-12 text-gray-600" />
            <h3 className="mb-2 font-semibold text-gray-300 text-xl">
              {searchQuery || filterContext !== 'all' ? 'No analyses found' : 'No PR analyses yet'}
            </h3>
            <p className="mb-6 text-gray-500">
              {searchQuery || filterContext !== 'all'
                ? 'Try adjusting your search or filters'
                : 'Start analyzing developer contributions'}
            </p>
            <ExiqusButton
              onClick={() => router.push('/pr-analysis')}
              className="bg-gradient-to-r from-teal-600 to-cyan-600"
            >
              Analyze Your First PR
            </ExiqusButton>
          </ExiqusCard>
        ) : (
          <div className="grid gap-4">
            {filteredAnalyses.map((analysis) => (
              <ExiqusCard
                key={analysis.id}
                className="group cursor-pointer p-6 transition-all hover:border-teal-500/40"
                onClick={() => router.push(`/pr-analyses/${analysis.id}`)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="mb-3 flex items-center gap-3">
                      <h3 className="font-semibold text-gray-100 text-xl transition-colors group-hover:text-teal-300">
                        @{analysis.github_username}
                      </h3>
                      {getContextBadge(analysis.context)}
                      {getDataQualityBadge(analysis.data_quality)}
                      {analysis.from_cache && (
                        <span className="rounded-full border border-purple-500/20 bg-purple-900/30 px-2 py-1 text-purple-300 text-xs">
                          Cached
                        </span>
                      )}
                    </div>

                    <div className="mb-3 flex flex-wrap gap-4 text-gray-400 text-sm">
                      <div className="flex items-center gap-2">
                        <GitPullRequest className="h-4 w-4 text-teal-400" />
                        <span>{analysis.total_prs_analyzed} PRs analyzed</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <GitBranch className="h-4 w-4 text-cyan-400" />
                        <span>{analysis.repositories_count} repositories</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Calendar className="h-4 w-4 text-gray-500" />
                        <span>
                          {formatDistanceToNow(new Date(analysis.created_at), { addSuffix: true })}
                        </span>
                      </div>
                    </div>

                    {/* Executive Summary Preview */}
                    {analysis.executive_summary && (
                      <div className="mt-3 rounded-lg border border-teal-500/10 bg-gradient-to-r from-teal-900/20 to-cyan-900/20 p-3">
                        <p className="line-clamp-2 text-gray-300 text-sm leading-relaxed">
                          {analysis.executive_summary}
                        </p>
                      </div>
                    )}
                  </div>

                  <ChevronRight className="h-5 w-5 flex-shrink-0 text-gray-500 transition-colors group-hover:text-teal-400" />
                </div>
              </ExiqusCard>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
