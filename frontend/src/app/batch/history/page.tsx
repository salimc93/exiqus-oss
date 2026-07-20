// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import { format } from 'date-fns';
import {
  CheckCircle,
  ChevronLeft,
  ChevronRight,
  Clock,
  Eye,
  FileArchive,
  FileJson,
  FileSpreadsheet,
  Filter,
  GitBranch,
  Loader2,
  TrendingUp,
  XCircle,
} from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { ExiqusButton, ExiqusCard, GradientText } from '@/components/ui/exiqus-components';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useAuth } from '@/contexts/auth-context';
import { useAuthGuard } from '@/hooks/use-auth-guard';
import { useToast } from '@/hooks/use-toast';
import { api } from '@/lib/api-client';
import { cn } from '@/lib/utils';
import type { BatchHistoryResponse, BatchStatistics } from '@/types';

// Helper function to format duration
const formatDuration = (milliseconds: number): string => {
  const seconds = Math.round(milliseconds / 1000);
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;

  if (minutes === 0) {
    return `${seconds}s`;
  } else if (minutes < 60) {
    return remainingSeconds > 0 ? `${minutes}m ${remainingSeconds}s` : `${minutes}m`;
  } else {
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    return `${hours}h ${remainingMinutes}m`;
  }
};

// Helper to get status color
const getStatusColor = (status: string) => {
  switch (status) {
    case 'completed':
      return 'bg-green-500/20 text-green-400';
    case 'failed':
      return 'bg-red-500/20 text-red-400';
    case 'processing':
      return 'bg-blue-500/20 text-blue-400';
    default:
      return 'bg-gray-500/20 text-gray-400';
  }
};

// Helper to get status icon
const getStatusIcon = (status: string) => {
  switch (status) {
    case 'completed':
      return <CheckCircle className="h-4 w-4" />;
    case 'failed':
      return <XCircle className="h-4 w-4" />;
    case 'processing':
      return <Loader2 className="h-4 w-4 animate-spin" />;
    default:
      return <Clock className="h-4 w-4" />;
  }
};

export default function BatchHistoryPage() {
  const router = useRouter();
  const { user } = useAuth();
  const { isLoading: authLoading, showUnauthorized, UnauthorizedComponent } = useAuthGuard();
  const { toast } = useToast();

  const [history, setHistory] = useState<BatchHistoryResponse | null>(null);
  const [statistics, setStatistics] = useState<BatchStatistics | null>(null);
  const [isLoading, setIsLoading] = useState(false); // Start with false since we'll only load when user is ready
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [currentPage, setCurrentPage] = useState(0);
  const [dataFetched, setDataFetched] = useState(false); // Track if data has been fetched

  const limit = 10;
  const canViewHistory =
    user?.subscription_plan === 'scale' || user?.subscription_plan === 'scale_plus';

  // Fetch batch history
  const fetchHistory = async () => {
    if (!canViewHistory) return;

    try {
      setIsLoading(true);
      const params: Record<string, unknown> = {
        limit,
        offset: currentPage * limit,
      };

      if (statusFilter !== 'all') {
        params.status = statusFilter;
      }

      const [historyResponse, statsResponse] = await Promise.all([
        api.getBatchHistory(params),
        api.getBatchStatistics(),
      ]);

      setHistory(historyResponse.data);
      // The statistics are wrapped in a response object with { success, data, message }
      // We need to extract the actual data
      if (
        statsResponse.data &&
        typeof statsResponse.data === 'object' &&
        'data' in statsResponse.data
      ) {
        setStatistics((statsResponse.data as { data: BatchStatistics }).data);
      } else {
        setStatistics(statsResponse.data);
      }
      setDataFetched(true);
    } catch (error) {
      const err = error as Error & { response?: { data?: { detail?: string }; status?: number } };
      console.error('Failed to fetch batch history:', err);
      // Don't show error toast for 401 errors - the interceptor handles session expiry
      if (err.response?.status !== 401) {
        toast({
          title: 'Failed to load batch history',
          description: err.response?.data?.detail || 'Please try again',
          variant: 'destructive',
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Download batch export with enhanced ZIP support including PDFs
  const handleDownload = async (batchId: string, format: 'csv' | 'zip' | 'json') => {
    try {
      // Show different loading message for ZIP with HTML reports
      if (format === 'zip') {
        toast({
          title: 'Preparing export...',
          description:
            'Generating ZIP with HTML reports for each analysis. This may take a moment.',
        });
      }

      const response =
        format === 'json'
          ? await api.exportBatchResults(batchId, 'json')
          : await api.downloadBatchExport(batchId, format as 'csv' | 'zip');

      const blob =
        format === 'json'
          ? new Blob([JSON.stringify(response.data, null, 2)], { type: 'application/json' })
          : (response.data as Blob);

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;

      // Better filename with date
      const date = new Date().toISOString().split('T')[0];
      a.download = `batch-${batchId}-${date}.${format}`;

      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

      toast({
        title: 'Export successful',
        description:
          format === 'zip'
            ? 'Downloaded batch results with HTML reports'
            : `Downloaded batch results as ${format.toUpperCase()}`,
      });
    } catch (error) {
      const err = error as Error & { response?: { data?: { detail?: string } } };
      console.error('Download failed:', err);
      toast({
        title: 'Download failed',
        description: err.response?.data?.detail || 'Please try again',
        variant: 'destructive',
      });
    }
  };

  useEffect(() => {
    // Only fetch if user is authenticated and can view history
    if (user && canViewHistory) {
      fetchHistory();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, currentPage, user, canViewHistory]);

  // Handle loading state - only show if we're actually loading data for a user who can view it
  if (authLoading || (isLoading && canViewHistory)) {
    return (
      <div className="flex min-h-[calc(100vh-12rem)] items-center justify-center bg-[#0A0A0A]">
        <div className="text-center">
          <div className="mb-4 inline-flex h-16 w-16 items-center justify-center">
            <div className="h-12 w-12 animate-spin rounded-full border-4 border-purple-600 border-t-transparent" />
          </div>
          <p className="text-gray-400">Loading batch history...</p>
        </div>
      </div>
    );
  }

  // Handle unauthorized state
  if (showUnauthorized && UnauthorizedComponent) {
    return <UnauthorizedComponent />;
  }

  // Check if user can view history
  if (!canViewHistory) {
    return (
      <div className="min-h-[calc(100vh-12rem)] bg-[#0A0A0A] py-8">
        <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8">
          <ExiqusCard className="p-12 text-center" glow="purple">
            <div className="mb-6 inline-flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-purple-600/20 to-blue-600/20">
              <FileArchive className="h-10 w-10 text-purple-400" />
            </div>
            <h1 className="mb-4 font-bold text-3xl">
              <GradientText>Batch History</GradientText>
            </h1>
            <p className="mb-8 text-gray-400 text-lg">
              Batch history and statistics are available for Scale and Scale+ plans.
              <br />
              Track your batch analyses and export comprehensive reports.
            </p>
            <ExiqusButton size="lg" onClick={() => router.push('/pricing')}>
              Upgrade to Scale
            </ExiqusButton>
          </ExiqusCard>
        </div>
      </div>
    );
  }

  const totalPages = history?.total_count ? Math.ceil(history.total_count / limit) : 0;

  return (
    <div className="min-h-[calc(100vh-12rem)] bg-[#0A0A0A] py-8">
      {/* Animated gradient background */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 h-80 w-80 animate-pulse rounded-full bg-purple-500/20 blur-3xl"></div>
        <div className="absolute -bottom-40 -left-40 h-80 w-80 animate-pulse rounded-full bg-blue-500/20 blur-3xl delay-1000"></div>
      </div>

      <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h1 className="mb-2 font-bold text-4xl text-gray-100">
                <GradientText>Batch History</GradientText>
              </h1>
              <p className="text-gray-400">
                View and export your batch analysis history and statistics
              </p>
            </div>
            <Link href="/batch">
              <ExiqusButton>
                <GitBranch className="mr-2 h-4 w-4" />
                New Batch Analysis
              </ExiqusButton>
            </Link>
          </div>
        </div>

        {/* Statistics Cards */}
        {statistics && (
          <div className="mb-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
            <ExiqusCard className="p-6" glow="subtle">
              <div className="mb-4 flex items-center justify-between">
                <h3 className="font-medium text-gray-400 text-sm">Total Batches</h3>
                <FileArchive className="h-5 w-5 text-purple-400" />
              </div>
              <p className="font-bold text-3xl text-gray-100">{statistics.total_batches}</p>
              <p className="mt-2 text-gray-500 text-xs">All time</p>
            </ExiqusCard>

            <ExiqusCard className="p-6" glow="subtle">
              <div className="mb-4 flex items-center justify-between">
                <h3 className="font-medium text-gray-400 text-sm">Repos Analyzed</h3>
                <GitBranch className="h-5 w-5 text-blue-400" />
              </div>
              <p className="font-bold text-3xl text-gray-100">{statistics.total_repositories}</p>
              <p className="mt-2 text-gray-500 text-xs">
                Avg{' '}
                {statistics.total_batches > 0
                  ? (statistics.total_repositories / statistics.total_batches).toFixed(1)
                  : '0'}{' '}
                per batch
              </p>
            </ExiqusCard>

            <ExiqusCard className="p-6" glow="subtle">
              <div className="mb-4 flex items-center justify-between">
                <h3 className="font-medium text-gray-400 text-sm">Success Rate</h3>
                <TrendingUp className="h-5 w-5 text-green-400" />
              </div>
              <p className="font-bold text-3xl text-gray-100">
                {statistics.success_rate?.toFixed(1) || '0'}%
              </p>
              <Progress value={statistics.success_rate || 0} className="mt-2 h-2" />
            </ExiqusCard>

            <ExiqusCard className="p-6" glow="subtle">
              <div className="mb-4 flex items-center justify-between">
                <h3 className="font-medium text-gray-400 text-sm">Avg Time</h3>
                <Clock className="h-5 w-5 text-orange-400" />
              </div>
              <p className="font-bold text-3xl text-gray-100">
                {statistics.avg_processing_time_ms
                  ? formatDuration(statistics.avg_processing_time_ms)
                  : '0s'}
              </p>
              <p className="mt-2 text-gray-500 text-xs">Per batch</p>
            </ExiqusCard>
          </div>
        )}

        {/* Filters and History */}
        <ExiqusCard className="p-6" glow="subtle">
          <div className="mb-6 flex items-center justify-between">
            <h2 className="font-semibold text-gray-100 text-xl">Batch Analysis History</h2>
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-gray-400" />
              <Tabs value={statusFilter} onValueChange={setStatusFilter}>
                <TabsList>
                  <TabsTrigger value="all">All</TabsTrigger>
                  <TabsTrigger value="completed">Completed</TabsTrigger>
                  <TabsTrigger value="processing">Processing</TabsTrigger>
                  <TabsTrigger value="failed">Failed</TabsTrigger>
                </TabsList>
              </Tabs>
            </div>
          </div>

          {/* History Table */}
          {!dataFetched && isLoading ? (
            <div className="py-12 text-center">
              <Loader2 className="mx-auto mb-4 h-8 w-8 animate-spin text-purple-400" />
              <p className="text-gray-400">Loading your batch history...</p>
            </div>
          ) : history && history.data && history.data.length > 0 ? (
            <>
              <div className="space-y-3">
                {history.data.map((batch) => (
                  <div
                    key={batch.batch_id}
                    className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-4 transition-all hover:bg-white/[0.04]"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="mb-2 flex items-center gap-3">
                          <h3 className="font-medium text-gray-100">
                            Batch Analysis - {batch.context}
                          </h3>
                          <Badge className={cn('capitalize', getStatusColor(batch.status))}>
                            {getStatusIcon(batch.status)}
                            <span className="ml-1">{batch.status}</span>
                          </Badge>
                          {batch.concurrency_mode && (
                            <Badge variant="outline" className="text-xs">
                              {batch.concurrency_mode === 'sequential' && '🎯 Sequential'}
                              {batch.concurrency_mode === 'balanced' && '⚖️ Balanced'}
                              {batch.concurrency_mode === 'fast' && '⚡ Fast'}
                            </Badge>
                          )}
                        </div>
                        <div className="flex flex-wrap gap-4 text-gray-400 text-sm">
                          <span>
                            <GitBranch className="mr-1 inline h-3 w-3" />
                            {batch.total_repositories} repositories
                          </span>
                          <span>
                            <CheckCircle className="mr-1 inline h-3 w-3 text-green-400" />
                            {batch.completed_count} completed
                          </span>
                          {batch.failed_count > 0 && (
                            <span>
                              <XCircle className="mr-1 inline h-3 w-3 text-red-400" />
                              {batch.failed_count} failed
                            </span>
                          )}
                          <span>
                            <Clock className="mr-1 inline h-3 w-3" />
                            {format(new Date(batch.created_at), 'MMM d, h:mm a')}
                          </span>
                          {batch.processing_time_ms && (
                            <span>Duration: {formatDuration(batch.processing_time_ms)}</span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Link href={`/batch/${batch.batch_id}`}>
                          <ExiqusButton variant="ghost" size="sm">
                            <Eye className="h-4 w-4" />
                          </ExiqusButton>
                        </Link>
                        {batch.status === 'completed' && (
                          <>
                            <ExiqusButton
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDownload(batch.batch_id, 'json')}
                              title="Export as JSON"
                            >
                              <FileJson className="h-4 w-4" />
                            </ExiqusButton>
                            <ExiqusButton
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDownload(batch.batch_id, 'csv')}
                              title="Export as CSV"
                            >
                              <FileSpreadsheet className="h-4 w-4" />
                            </ExiqusButton>
                            <ExiqusButton
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDownload(batch.batch_id, 'zip')}
                              title="Export as ZIP with HTML reports"
                            >
                              <FileArchive className="h-4 w-4" />
                            </ExiqusButton>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <>
                  <Separator className="my-6 bg-white/[0.06]" />
                  <div className="flex items-center justify-between">
                    <p className="text-gray-400 text-sm">
                      Showing {currentPage * limit + 1} to{' '}
                      {Math.min((currentPage + 1) * limit, history?.total_count || 0)} of{' '}
                      {history?.total_count || 0} batches
                    </p>
                    <div className="flex gap-2">
                      <ExiqusButton
                        variant="secondary"
                        size="sm"
                        onClick={() => setCurrentPage(currentPage - 1)}
                        disabled={currentPage === 0}
                      >
                        <ChevronLeft className="h-4 w-4" />
                        Previous
                      </ExiqusButton>
                      <ExiqusButton
                        variant="secondary"
                        size="sm"
                        onClick={() => setCurrentPage(currentPage + 1)}
                        disabled={currentPage >= totalPages - 1}
                      >
                        Next
                        <ChevronRight className="h-4 w-4" />
                      </ExiqusButton>
                    </div>
                  </div>
                </>
              )}
            </>
          ) : (
            <div className="py-12 text-center">
              <FileArchive className="mx-auto mb-4 h-16 w-16 text-gray-600" />
              <p className="mb-2 font-medium text-gray-100 text-lg">No batch analyses yet</p>
              <p className="mb-6 text-gray-400">Start a batch analysis to see your history here</p>
              <Link href="/batch">
                <ExiqusButton>
                  <GitBranch className="mr-2 h-4 w-4" />
                  Start Batch Analysis
                </ExiqusButton>
              </Link>
            </div>
          )}
        </ExiqusCard>

        {/* Status Distribution */}
        {statistics && statistics.total_batches > 0 && (
          <ExiqusCard className="mt-8 p-6" glow="subtle">
            <h3 className="mb-4 font-semibold text-gray-100 text-lg">Status Distribution</h3>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <div className="rounded-lg bg-green-500/10 p-3 text-center">
                <p className="font-bold text-2xl text-green-400">
                  {statistics.status_breakdown?.completed || 0}
                </p>
                <p className="text-gray-400 text-sm">Completed</p>
              </div>
              <div className="rounded-lg bg-blue-500/10 p-3 text-center">
                <p className="font-bold text-2xl text-blue-400">
                  {statistics.status_breakdown?.processing || 0}
                </p>
                <p className="text-gray-400 text-sm">Processing</p>
              </div>
              <div className="rounded-lg bg-gray-500/10 p-3 text-center">
                <p className="font-bold text-2xl text-gray-400">
                  {statistics.status_breakdown?.pending || 0}
                </p>
                <p className="text-gray-400 text-sm">Pending</p>
              </div>
              <div className="rounded-lg bg-red-500/10 p-3 text-center">
                <p className="font-bold text-2xl text-red-400">
                  {statistics.status_breakdown?.failed || 0}
                </p>
                <p className="text-gray-400 text-sm">Failed</p>
              </div>
            </div>
          </ExiqusCard>
        )}
      </div>
    </div>
  );
}
