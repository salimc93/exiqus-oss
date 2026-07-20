// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import { format, formatDistanceToNow } from 'date-fns';
import {
  Activity,
  AlertCircle,
  ArrowUpRight,
  BarChart3,
  Calendar,
  CheckCircle,
  ChevronLeft,
  ChevronRight,
  Clock,
  Eye,
  FileText,
  Filter,
  GitBranch,
  Loader2,
  Search,
  Sparkles,
  Target,
  Trash2,
  TrendingUp,
  XCircle,
} from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { ExiqusButton, ExiqusCard, GradientText } from '@/components/ui/exiqus-components';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { useAuth } from '@/contexts/auth-context';
import { useAuthGuard } from '@/hooks/use-auth-guard';
import { api } from '@/lib/api-client';

interface AnalysisResult {
  id: string;
  repository_url: string;
  repository_name: string;
  status: 'completed' | 'failed' | 'pending';
  created_at: string;
  updated_at: string;
  batch_id?: string;
  key_insight?: string;
  analysis_data?: {
    summary?: string;
    overall_assessment?: string;
    key_findings?: string[];
  };
  error_message?: string;
}

interface PaginationInfo {
  page: number;
  total: number;
  totalPages: number;
  limit: number;
  cursor?: string | null;
  cursors: string[]; // Store cursors for each page for back navigation
}

export default function MyAnalysesPage() {
  const { isLoading: authLoading, showUnauthorized, UnauthorizedComponent } = useAuthGuard();
  const [analyses, setAnalyses] = useState<AnalysisResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [paginationLoading, setPaginationLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [pagination, setPagination] = useState<PaginationInfo>({
    page: 1,
    total: 0,
    totalPages: 0,
    limit: 10,
    cursor: null,
    cursors: [], // cursors[0] = cursor for page 2, cursors[1] = cursor for page 3, etc.
  });
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const router = useRouter();
  const { user } = useAuth();

  const fetchAnalysesForPage = useCallback(
    async (targetPage: number, currentCursors: string[], isInitialLoad = false) => {
      // Don't fetch if user is not loaded yet
      if (!user) {
        setLoading(false);
        return;
      }

      try {
        // Use different loading state for pagination vs initial load
        if (isInitialLoad) {
          setLoading(true);
        } else {
          setPaginationLoading(true);
        }

        // Determine cursor based on target page number
        let cursor = null;
        if (targetPage > 1) {
          // Use the stored cursor for this page
          cursor = currentCursors[targetPage - 2]; // page 2 uses cursors[0]
        }

        const response = await api.getAnalyses({
          cursor,
          limit: 10,
        });

        // Handle the response - the backend returns { items: [], cursor, has_next, has_prev, total_count }
        const responseData = response.data;
        // Add status field to each analysis (backend doesn't include it, but all stored analyses are completed)
        const analysesWithStatus = (responseData.items || []).map((analysis: AnalysisResult) => {
          return {
            ...analysis,
            status: 'completed' as const,
            analysis_data: {
              summary: analysis.key_insight || 'Analysis completed successfully',
              overall_assessment: 'Evidence-based assessment',
              key_findings: [],
            },
          };
        });
        setAnalyses(analysesWithStatus);

        // Update pagination with cursor info
        const totalPages = Math.ceil((responseData.total_count || 0) / 10);

        setPagination((_prev) => {
          const newCursors = [...currentCursors];
          // Store the cursor for the next page if it exists
          if (responseData.cursor && targetPage <= newCursors.length) {
            // Update existing cursor
            newCursors[targetPage - 1] = responseData.cursor;
          } else if (responseData.cursor) {
            // Add new cursor for next page
            newCursors[targetPage - 1] = responseData.cursor;
          }

          return {
            page: targetPage,
            total: responseData.total_count || 0,
            totalPages,
            limit: 10,
            cursor: responseData.cursor,
            cursors: newCursors,
          };
        });
      } catch (error) {
        console.error('Failed to fetch analyses:', error);
        // Only show error if we're authenticated and it's not a backend 500 error
        // Backend returns 500 when there are no analyses, but we handle that gracefully
        const isServerError =
          (error as { response?: { status?: number } })?.response?.status === 500;
        if (user && !isServerError) {
          toast.error('Failed to load analyses');
        }
      } finally {
        if (isInitialLoad) {
          setLoading(false);
        } else {
          setPaginationLoading(false);
        }
      }
    },
    [user]
  );

  // Only fetch on initial load or search changes, not pagination
  useEffect(() => {
    if (user) {
      fetchAnalysesForPage(1, [], true); // Pass empty cursors for initial load
    }
  }, [searchQuery, user, fetchAnalysesForPage]);

  const handleDelete = async () => {
    if (!deleteId) return;

    try {
      setDeleting(true);
      // await api.deleteAnalysis(deleteId);
      // Delete functionality not yet implemented
      toast.error('Delete functionality not yet available');
      setDeleteId(null);
    } catch (error) {
      console.error('Failed to delete analysis:', error);
      toast.error('Failed to delete analysis');
    } finally {
      setDeleting(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPagination({
      page: 1,
      total: 0,
      totalPages: 0,
      limit: 10,
      cursor: null,
      cursors: [],
    });
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return (
          <Badge className="border-green-500/30 bg-green-500/20 text-green-400">
            <CheckCircle className="mr-1 h-3 w-3" />
            Completed
          </Badge>
        );
      case 'failed':
        return (
          <Badge className="border-red-500/30 bg-red-500/20 text-red-400">
            <XCircle className="mr-1 h-3 w-3" />
            Failed
          </Badge>
        );
      case 'pending':
        return (
          <Badge className="border-yellow-500/30 bg-yellow-500/20 text-yellow-400">
            <Clock className="mr-1 h-3 w-3 animate-pulse" />
            Pending
          </Badge>
        );
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  // Get card theme based on index and repository
  const getCardTheme = (index: number, _repoName: string) => {
    const themes = [
      {
        gradient: 'from-purple-600/10 via-purple-500/5 to-transparent',
        iconGradient: 'from-purple-600 to-purple-400',
        iconBorder: 'border-purple-500/30',
        accentColor: 'text-purple-400',
        hoverGradient: 'from-purple-600/15 to-purple-500/10',
        pattern: 'radial-gradient(circle at 20% 50%, rgba(168, 85, 247, 0.1) 0%, transparent 50%)',
      },
      {
        gradient: 'from-blue-600/10 via-blue-500/5 to-transparent',
        iconGradient: 'from-blue-600 to-cyan-400',
        iconBorder: 'border-blue-500/30',
        accentColor: 'text-blue-400',
        hoverGradient: 'from-blue-600/15 to-cyan-500/10',
        pattern: 'radial-gradient(circle at 80% 20%, rgba(59, 130, 246, 0.1) 0%, transparent 50%)',
      },
      {
        gradient: 'from-emerald-600/10 via-emerald-500/5 to-transparent',
        iconGradient: 'from-emerald-600 to-green-400',
        iconBorder: 'border-emerald-500/30',
        accentColor: 'text-emerald-400',
        hoverGradient: 'from-emerald-600/15 to-green-500/10',
        pattern: 'radial-gradient(circle at 50% 80%, rgba(16, 185, 129, 0.1) 0%, transparent 50%)',
      },
      {
        gradient: 'from-orange-600/10 via-orange-500/5 to-transparent',
        iconGradient: 'from-orange-600 to-amber-400',
        iconBorder: 'border-orange-500/30',
        accentColor: 'text-orange-400',
        hoverGradient: 'from-orange-600/15 to-amber-500/10',
        pattern: 'radial-gradient(circle at 70% 70%, rgba(251, 146, 60, 0.1) 0%, transparent 50%)',
      },
      {
        gradient: 'from-pink-600/10 via-pink-500/5 to-transparent',
        iconGradient: 'from-pink-600 to-rose-400',
        iconBorder: 'border-pink-500/30',
        accentColor: 'text-pink-400',
        hoverGradient: 'from-pink-600/15 to-rose-500/10',
        pattern: 'radial-gradient(circle at 30% 30%, rgba(236, 72, 153, 0.1) 0%, transparent 50%)',
      },
    ];
    return themes[index % themes.length];
  };

  // Get tech stack badge (mock data - would come from API)
  const getTechStackBadge = (repoName: string) => {
    const techStacks: Record<string, { lang: string; color: string; icon: string }> = {
      lodash: {
        lang: 'JavaScript',
        color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
        icon: '⚡',
      },
      vue: {
        lang: 'Vue.js',
        color: 'bg-green-500/20 text-green-400 border-green-500/30',
        icon: '💚',
      },
      prisma: {
        lang: 'TypeScript',
        color: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
        icon: '🔷',
      },
      react: {
        lang: 'React',
        color: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
        icon: '⚛️',
      },
      python: {
        lang: 'Python',
        color: 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30',
        icon: '🐍',
      },
    };

    const key = Object.keys(techStacks).find((k) => repoName.toLowerCase().includes(k));
    return key
      ? techStacks[key]
      : { lang: 'Code', color: 'bg-gray-500/20 text-gray-400 border-gray-500/30', icon: '📦' };
  };

  // Get freshness indicator
  const getFreshnessIndicator = (createdAt: string) => {
    const date = new Date(createdAt);
    const now = new Date();
    const diffHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));

    if (diffHours < 1) return { label: 'Fresh', color: 'text-green-400', pulse: true };
    if (diffHours < 24) return { label: 'Recent', color: 'text-blue-400', pulse: false };
    if (diffHours < 168) return { label: 'This Week', color: 'text-purple-400', pulse: false };
    return { label: 'Archived', color: 'text-gray-500', pulse: false };
  };

  // Get monthly limit based on plan
  const getMonthlyLimit = () => {
    switch (user?.subscription_plan) {
      case 'free':
        return 10;
      case 'starter':
        return 100;
      case 'growth':
        return 500;
      case 'scale':
        return 2000;
      case 'scale_plus':
        return 3000;
      default:
        return 0;
    }
  };

  const monthlyLimit = getMonthlyLimit();
  const usagePercentage = monthlyLimit > 0 ? (pagination.total / monthlyLimit) * 100 : 0;

  // Show auth loading state
  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0A0A0A]">
        <div className="text-center">
          <div className="mb-4 inline-flex h-16 w-16 items-center justify-center">
            <div className="h-12 w-12 animate-spin rounded-full border-4 border-purple-600 border-t-transparent" />
          </div>
          <p className="text-gray-400">Loading your repository analyses...</p>
        </div>
      </div>
    );
  }

  // Show unauthorized component
  if (showUnauthorized && UnauthorizedComponent) {
    return <UnauthorizedComponent />;
  }

  if (loading && analyses.length === 0) {
    return (
      <div className="min-h-screen bg-[#0A0A0A]">
        <div className="container mx-auto max-w-7xl px-4 py-8">
          <div className="space-y-8">
            <div className="relative">
              <div className="absolute inset-0 -z-10 bg-gradient-to-r from-purple-900/10 to-blue-900/10 blur-3xl" />
              <div>
                <Skeleton className="mb-2 h-10 w-64 bg-white/10" />
                <Skeleton className="h-6 w-96 bg-white/10" />
              </div>
            </div>

            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
              <div className="md:col-span-2">
                <Skeleton className="h-12 w-full" />
              </div>
              <Skeleton className="h-24 w-full rounded-lg" />
              <Skeleton className="h-24 w-full rounded-lg" />
            </div>

            <div className="grid gap-6">
              {[1, 2, 3].map((i) => (
                <Card key={i} className="border-gray-200/50">
                  <CardHeader>
                    <div className="flex items-start gap-3">
                      <Skeleton className="h-10 w-10 rounded-lg" />
                      <div className="flex-1">
                        <Skeleton className="mb-2 h-6 w-48" />
                        <Skeleton className="h-4 w-32" />
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <Skeleton className="mb-4 h-16 w-full" />
                    <div className="flex gap-3">
                      <Skeleton className="h-9 w-32" />
                      <Skeleton className="h-9 w-24" />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0A0A0A] py-8">
      {/* Animated gradient background */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 h-80 w-80 animate-pulse rounded-full bg-purple-500/20 blur-3xl"></div>
        <div className="absolute -bottom-40 -left-40 h-80 w-80 animate-pulse rounded-full bg-blue-500/20 blur-3xl delay-1000"></div>
        <div className="absolute top-1/2 left-1/2 h-80 w-80 -translate-x-1/2 -translate-y-1/2 animate-pulse rounded-full bg-green-500/10 blur-3xl delay-500"></div>
      </div>

      <div className="container relative mx-auto max-w-7xl px-4">
        <div className="space-y-8">
          {/* Enhanced Header */}
          <div className="relative">
            <div className="flex flex-col items-start justify-between gap-6 sm:flex-row sm:items-center">
              <div>
                <h1 className="mb-2 font-bold text-4xl text-gray-100">
                  My <GradientText>Analyses</GradientText>
                </h1>
                <p className="text-gray-400 text-lg">
                  Track your repository insights and analysis history
                </p>
              </div>
              <ExiqusButton onClick={() => router.push('/analyze')} size="lg" className="shadow-lg">
                <Sparkles className="mr-2 h-4 w-4" />
                New Analysis
              </ExiqusButton>
            </div>
          </div>

          {/* Enhanced Stats Cards with Usage Progress */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {/* Search Bar - Spans 2 columns on desktop */}
            <div className="sm:col-span-2 lg:col-span-2">
              <form onSubmit={handleSearch} className="relative">
                <Search className="absolute top-1/2 left-4 h-5 w-5 -translate-y-1/2 text-gray-400" />
                <Input
                  type="text"
                  placeholder="Search your analyses..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="h-14 w-full border-white/[0.09] bg-white/[0.06] pr-12 pl-12 text-gray-100 transition-all placeholder:text-gray-500 focus:bg-white/[0.09]"
                />
                <Button
                  type="submit"
                  size="icon"
                  variant="ghost"
                  className="absolute top-1/2 right-1 h-10 w-10 -translate-y-1/2"
                >
                  <Filter className="h-4 w-4" />
                </Button>
              </form>
            </div>

            {/* Total Analyses Card */}
            <ExiqusCard
              className="bg-gradient-to-br from-purple-900/20 to-transparent p-5"
              glow="purple"
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="mb-1 flex items-center gap-2">
                    <BarChart3 className="h-4 w-4 text-purple-400" />
                    <p className="font-medium text-gray-400 text-xs uppercase tracking-wide">
                      Total
                    </p>
                  </div>
                  <p className="font-bold text-3xl text-gray-100">{pagination.total || 0}</p>
                  <p className="mt-1 text-gray-500 text-xs">All time analyses</p>
                </div>
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-purple-500/20">
                  <FileText className="h-6 w-6 text-purple-400" />
                </div>
              </div>
            </ExiqusCard>

            {/* Monthly Usage with Progress */}
            <ExiqusCard
              className="bg-gradient-to-br from-blue-900/20 to-transparent p-5"
              glow="blue"
            >
              <div className="flex flex-col">
                <div className="mb-3 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Target className="h-4 w-4 text-blue-400" />
                    <p className="font-medium text-gray-400 text-xs uppercase tracking-wide">
                      Usage
                    </p>
                  </div>
                  <Badge className="bg-blue-500/20 text-blue-300 text-xs">
                    {user?.subscription_plan?.toUpperCase()}
                  </Badge>
                </div>
                <div className="space-y-2">
                  <div className="flex items-baseline justify-between">
                    <p className="font-bold text-2xl text-gray-100">{pagination.total}</p>
                    <p className="text-gray-400 text-sm">/ {monthlyLimit}</p>
                  </div>
                  <Progress value={usagePercentage} className="h-2" />
                  <p className="text-gray-500 text-xs">
                    {100 - usagePercentage > 0
                      ? `${Math.round(100 - usagePercentage)}% remaining`
                      : 'Limit reached'}
                  </p>
                </div>
              </div>
            </ExiqusCard>
          </div>

          {/* Recent Activity Summary */}
          <div className="grid gap-4 sm:grid-cols-3">
            <ExiqusCard
              className="bg-gradient-to-br from-green-900/10 to-transparent p-4"
              glow="subtle"
            >
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-500/20">
                  <Activity className="h-5 w-5 text-green-400" />
                </div>
                <div>
                  <p className="text-gray-400 text-xs">This Week</p>
                  <p className="font-bold text-gray-100 text-xl">
                    {
                      analyses.filter((a) => {
                        const date = new Date(a.created_at);
                        const weekAgo = new Date();
                        weekAgo.setDate(weekAgo.getDate() - 7);
                        return date >= weekAgo;
                      }).length
                    }
                  </p>
                </div>
              </div>
            </ExiqusCard>

            <ExiqusCard
              className="bg-gradient-to-br from-yellow-900/10 to-transparent p-4"
              glow="subtle"
            >
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-yellow-500/20">
                  <Clock className="h-5 w-5 text-yellow-400" />
                </div>
                <div>
                  <p className="text-gray-400 text-xs">Today</p>
                  <p className="font-bold text-gray-100 text-xl">
                    {
                      analyses.filter((a) => {
                        const date = new Date(a.created_at);
                        const today = new Date();
                        return date.toDateString() === today.toDateString();
                      }).length
                    }
                  </p>
                </div>
              </div>
            </ExiqusCard>

            <ExiqusCard
              className="bg-gradient-to-br from-orange-900/10 to-transparent p-4"
              glow="subtle"
            >
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-orange-500/20">
                  <TrendingUp className="h-5 w-5 text-orange-400" />
                </div>
                <div>
                  <p className="text-gray-400 text-xs">This Month</p>
                  <p className="font-bold text-gray-100 text-xl">
                    {
                      analyses.filter((a) => {
                        const date = new Date(a.created_at);
                        const monthAgo = new Date();
                        monthAgo.setDate(monthAgo.getDate() - 30);
                        return date >= monthAgo;
                      }).length
                    }
                  </p>
                </div>
              </div>
            </ExiqusCard>
          </div>

          {/* Results */}
          {analyses.length === 0 ? (
            <ExiqusCard className="relative overflow-hidden border-2 border-white/[0.06] border-dashed bg-gradient-to-br from-purple-900/5 via-blue-900/5 to-transparent p-16">
              {/* Decorative background elements */}
              <div className="absolute inset-0 opacity-30">
                <div className="absolute top-10 left-10 h-32 w-32 rounded-full bg-purple-500/10 blur-3xl" />
                <div className="absolute right-10 bottom-10 h-32 w-32 rounded-full bg-blue-500/10 blur-3xl" />
                <div className="absolute top-1/2 left-1/2 h-48 w-48 -translate-x-1/2 -translate-y-1/2 rounded-full bg-gradient-to-r from-purple-500/5 to-blue-500/5 blur-2xl" />
              </div>

              <div className="relative flex flex-col items-center justify-center">
                <div className="mb-6 flex h-20 w-20 animate-pulse items-center justify-center rounded-full border border-purple-500/20 bg-gradient-to-br from-purple-600/20 to-blue-600/20">
                  <FileText className="h-10 w-10 text-purple-400" />
                </div>
                <h3 className="mb-2 font-semibold text-gray-100 text-xl">No analyses found</h3>
                <p className="mb-6 max-w-sm text-center text-gray-400">
                  {searchQuery
                    ? 'No analyses match your search criteria'
                    : 'Start by analyzing your first repository to get AI-powered insights'}
                </p>
                <ExiqusButton
                  onClick={() => router.push('/analyze')}
                  size="lg"
                  className="shadow-lg"
                >
                  <GitBranch className="mr-2 h-5 w-5" />
                  Analyze Your First Repository
                </ExiqusButton>
              </div>
            </ExiqusCard>
          ) : (
            <>
              <div className="grid gap-6">
                {analyses.map((analysis, index) => {
                  const theme = getCardTheme(index, analysis.repository_name);
                  const techStack = getTechStackBadge(analysis.repository_name);
                  const freshness = getFreshnessIndicator(analysis.created_at);

                  return (
                    <ExiqusCard
                      key={analysis.id}
                      className={`group relative isolate overflow-hidden bg-gradient-to-br transition-all duration-500 hover:scale-[1.01] hover:shadow-2xl ${theme.gradient}`}
                      glow="hover"
                      style={{
                        animationDelay: `${index * 100}ms`,
                        backgroundImage: theme.pattern,
                        backgroundSize: '100% 100%',
                        backgroundPosition: 'center',
                      }}
                    >
                      {/* Animated gradient overlay on hover */}
                      <div
                        className={`absolute inset-0 -z-10 bg-gradient-to-r ${theme.hoverGradient} opacity-0 transition-all duration-700 group-hover:opacity-100`}
                      />

                      {/* Decorative elements */}
                      <div className="absolute top-0 right-0 h-32 w-32 translate-x-16 -translate-y-16 rounded-full bg-gradient-to-br from-white/[0.02] to-transparent transition-transform duration-700 group-hover:scale-150" />
                      <div className="absolute bottom-0 left-0 h-24 w-24 -translate-x-12 translate-y-12 rounded-full bg-gradient-to-tr from-white/[0.02] to-transparent transition-transform duration-700 group-hover:scale-150" />

                      {/* Card content */}
                      <div className="relative p-6">
                        {/* Header section with improved layout */}
                        <div className="mb-4 flex items-start justify-between">
                          <div className="flex flex-1 items-start gap-4">
                            {/* Enhanced icon with unique gradient background */}
                            <div className="relative isolate">
                              <div
                                className={`absolute inset-0 -z-10 bg-gradient-to-br ${theme.iconGradient} rounded-xl opacity-20 blur-lg transition-opacity group-hover:opacity-40`}
                              />
                              <div
                                className={`relative z-10 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br ${theme.iconGradient} border bg-opacity-20 ${theme.iconBorder} transition-all duration-500 group-hover:rotate-3 group-hover:border-opacity-60`}
                              >
                                <span className="text-2xl">{techStack.icon}</span>
                              </div>
                            </div>

                            {/* Repository info with enhanced typography */}
                            <div className="min-w-0 flex-1">
                              <div className="flex items-start justify-between">
                                <div className="flex-1">
                                  <h3 className="mb-1 font-semibold text-xl">
                                    <Link
                                      href={`/analyses/${analysis.id}`}
                                      className="group/link flex items-center gap-2 text-gray-100 transition-all hover:text-purple-400"
                                    >
                                      <span className="truncate">{analysis.repository_name}</span>
                                      <ArrowUpRight className="h-4 w-4 flex-shrink-0 translate-x-1 -translate-y-1 opacity-0 transition-all group-hover/link:translate-x-0 group-hover/link:translate-y-0 group-hover/link:opacity-100" />
                                    </Link>
                                  </h3>

                                  {/* Tech stack and freshness badges */}
                                  <div className="mt-2 flex items-center gap-2">
                                    <Badge className={`text-xs ${techStack.color}`}>
                                      {techStack.lang}
                                    </Badge>
                                    <div
                                      className={`flex items-center gap-1 text-xs ${freshness.color}`}
                                    >
                                      {freshness.pulse && (
                                        <span className="h-2 w-2 animate-pulse rounded-full bg-current" />
                                      )}
                                      <span>{freshness.label}</span>
                                    </div>
                                  </div>

                                  {/* Meta information with icons */}
                                  <div className="flex flex-wrap items-center gap-3 text-sm">
                                    <span className="flex items-center gap-1.5 text-gray-400">
                                      <Calendar className="h-3.5 w-3.5 text-gray-500" />
                                      {format(new Date(analysis.created_at), 'MMM d, yyyy')}
                                    </span>
                                    <span className="flex items-center gap-1.5 text-gray-400">
                                      <Clock className="h-3.5 w-3.5 text-gray-500" />
                                      {(() => {
                                        const createdAt = new Date(analysis.created_at);
                                        const now = new Date();
                                        const diffMinutes = Math.floor(
                                          (now.getTime() - createdAt.getTime()) / (1000 * 60)
                                        );

                                        if (diffMinutes < 1) return 'just now';
                                        if (diffMinutes < 60)
                                          return `${diffMinutes} minute${diffMinutes > 1 ? 's' : ''} ago`;
                                        return formatDistanceToNow(createdAt, { addSuffix: true });
                                      })()}
                                    </span>
                                    <a
                                      href={analysis.repository_url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="flex items-center gap-1.5 text-gray-400 transition-colors hover:text-purple-400"
                                    >
                                      <GitBranch className="h-3.5 w-3.5" />
                                      <span className="text-xs">View on GitHub</span>
                                    </a>
                                  </div>
                                </div>
                              </div>
                            </div>
                          </div>

                          {/* Status badge, batch badge and actions */}
                          <div className="ml-4 flex items-center gap-2">
                            {analysis.batch_id && (
                              <Badge className="border-purple-500/30 bg-purple-500/10 text-purple-300">
                                Batch #{analysis.batch_id.slice(0, 8)}
                              </Badge>
                            )}
                            {getStatusBadge(analysis.status)}
                            <Button
                              variant="ghost"
                              size="icon"
                              className="opacity-0 transition-all hover:bg-red-500/10 group-hover:opacity-100"
                              onClick={() => setDeleteId(analysis.id)}
                            >
                              <Trash2 className="h-4 w-4 text-red-400 hover:text-red-300" />
                            </Button>
                          </div>
                        </div>

                        {/* Content section with better spacing */}
                        <div className="mt-4 space-y-4 border-white/[0.06] border-t pt-4">
                          {analysis.status === 'completed' ? (
                            <>
                              {/* Summary with themed typography */}
                              <div className="space-y-3">
                                <div className="mb-2 flex items-center gap-2">
                                  <Sparkles className={`h-4 w-4 ${theme.accentColor}`} />
                                  <p
                                    className={`font-medium text-xs ${theme.accentColor} uppercase tracking-wide`}
                                  >
                                    Analysis Summary
                                  </p>
                                </div>
                                <p className="pl-6 text-gray-300 text-sm leading-relaxed">
                                  {analysis.analysis_data?.summary ||
                                    'Evidence-based assessment completed successfully. The repository demonstrates strong technical implementation with comprehensive testing and documentation practices.'}
                                </p>
                              </div>

                              {/* Key findings with enhanced badges */}
                              {analysis.analysis_data?.key_findings &&
                                analysis.analysis_data.key_findings.length > 0 && (
                                  <div className="space-y-2">
                                    <div className="mb-2 flex items-center gap-2">
                                      <Target className={`h-4 w-4 ${theme.accentColor}`} />
                                      <p
                                        className={`font-medium text-xs ${theme.accentColor} uppercase tracking-wide`}
                                      >
                                        Key Patterns
                                      </p>
                                    </div>
                                    <div className="flex flex-wrap gap-2 pl-6">
                                      {analysis.analysis_data.key_findings
                                        .slice(0, 4)
                                        .map((finding, i) => (
                                          <Badge
                                            key={i}
                                            className="border-purple-500/20 bg-gradient-to-r from-purple-500/10 to-blue-500/10 text-gray-300 transition-colors hover:border-purple-500/40"
                                          >
                                            {finding}
                                          </Badge>
                                        ))}
                                      {analysis.analysis_data.key_findings.length > 4 && (
                                        <Badge className="border-gray-700 bg-gray-800/50 text-gray-400">
                                          +{analysis.analysis_data.key_findings.length - 4} more
                                        </Badge>
                                      )}
                                    </div>
                                  </div>
                                )}
                            </>
                          ) : analysis.status === 'failed' ? (
                            <Alert
                              variant="destructive"
                              className="border-red-500/20 bg-red-500/10"
                            >
                              <AlertCircle className="h-4 w-4" />
                              <AlertDescription className="text-red-300">
                                {analysis.error_message ||
                                  'Analysis failed. Please try again or contact support if the issue persists.'}
                              </AlertDescription>
                            </Alert>
                          ) : (
                            <div className="flex items-center gap-3 rounded-lg border border-purple-500/10 bg-purple-500/5 p-4">
                              <Loader2 className="h-5 w-5 animate-spin text-purple-400" />
                              <div>
                                <p className="font-medium text-gray-200 text-sm">
                                  Analysis in progress
                                </p>
                                <p className="mt-0.5 text-gray-400 text-xs">
                                  This may take a few moments...
                                </p>
                              </div>
                            </div>
                          )}
                        </div>

                        {/* Action buttons with better styling */}
                        <div className="mt-6 flex items-center justify-between border-white/[0.06] border-t pt-4">
                          <div className="flex gap-3">
                            {analysis.id ? (
                              <Link href={`/analyses/${analysis.id}`}>
                                <ExiqusButton variant="secondary" size="sm" className="group/btn">
                                  <Eye className="mr-2 h-4 w-4 transition-transform group-hover/btn:scale-110" />
                                  View Details
                                </ExiqusButton>
                              </Link>
                            ) : (
                              <ExiqusButton
                                variant="secondary"
                                size="sm"
                                disabled
                                className="cursor-not-allowed opacity-50"
                              >
                                <Eye className="mr-2 h-4 w-4" />
                                No Analysis ID
                              </ExiqusButton>
                            )}

                            <ExiqusButton
                              variant="ghost"
                              size="sm"
                              onClick={() => navigator.clipboard.writeText(analysis.repository_url)}
                              className="group/copy"
                            >
                              <span className="text-gray-400 text-xs group-hover/copy:text-gray-200">
                                Copy URL
                              </span>
                            </ExiqusButton>
                          </div>

                          {/* Quick stats */}
                          <div className="flex items-center gap-4 text-gray-500 text-xs">
                            <span className="flex items-center gap-1">
                              <Activity className="h-3 w-3" />
                              Analysis #{analyses.length - index}
                            </span>
                          </div>
                        </div>
                      </div>
                    </ExiqusCard>
                  );
                })}
              </div>

              {/* Pagination */}
              {pagination.totalPages > 1 && (
                <div className="mt-6 flex items-center justify-center gap-2">
                  <ExiqusButton
                    variant="secondary"
                    size="sm"
                    onClick={async () => {
                      const newPage = Math.max(1, pagination.page - 1);
                      if (newPage !== pagination.page) {
                        await fetchAnalysesForPage(newPage, pagination.cursors, false);
                      }
                    }}
                    disabled={pagination.page <= 1 || paginationLoading}
                  >
                    {paginationLoading ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <ChevronLeft className="mr-2 h-4 w-4" />
                    )}
                    Previous
                  </ExiqusButton>
                  <span className="px-4 text-gray-400 text-sm">
                    {paginationLoading
                      ? 'Loading...'
                      : `Page ${pagination.page} of ${pagination.totalPages}`}
                  </span>
                  <ExiqusButton
                    variant="secondary"
                    size="sm"
                    onClick={async () => {
                      const newPage = Math.min(pagination.totalPages, pagination.page + 1);
                      if (newPage !== pagination.page && pagination.cursor) {
                        await fetchAnalysesForPage(newPage, pagination.cursors, false);
                      }
                    }}
                    disabled={
                      pagination.page >= pagination.totalPages ||
                      !pagination.cursor ||
                      paginationLoading
                    }
                  >
                    Next
                    {paginationLoading ? (
                      <Loader2 className="ml-2 h-4 w-4 animate-spin" />
                    ) : (
                      <ChevronRight className="ml-2 h-4 w-4" />
                    )}
                  </ExiqusButton>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {deleteId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <ExiqusCard className="mx-4 w-full max-w-md p-6">
            <h3 className="mb-4 font-bold text-red-400 text-xl">⚠️ Delete Analysis?</h3>

            <div className="space-y-4">
              <div className="rounded-lg border border-red-900/50 bg-red-900/20 p-3">
                <p className="text-red-300 text-sm">
                  This will permanently delete this repository analysis. This action cannot be
                  undone.
                </p>
              </div>

              <div className="flex gap-3 pt-4">
                <ExiqusButton
                  variant="secondary"
                  onClick={() => setDeleteId(null)}
                  className="flex-1"
                  disabled={deleting}
                >
                  Cancel
                </ExiqusButton>
                <ExiqusButton
                  variant="primary"
                  onClick={handleDelete}
                  disabled={deleting}
                  className="flex-1 bg-red-600 hover:bg-red-700"
                >
                  {deleting ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Deleting...
                    </>
                  ) : (
                    'Delete'
                  )}
                </ExiqusButton>
              </div>
            </div>
          </ExiqusCard>
        </div>
      )}
    </div>
  );
}
