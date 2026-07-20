// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import { format } from 'date-fns';
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle,
  ChevronDown,
  ChevronUp,
  Clock,
  Eye,
  FileArchive,
  FileJson,
  FileSpreadsheet,
  GitBranch,
  Loader2,
  RefreshCw,
  TrendingUp,
  XCircle,
} from 'lucide-react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import React, { useEffect, useState } from 'react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { ExiqusButton, ExiqusCard, GradientText } from '@/components/ui/exiqus-components';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { useAuth } from '@/contexts/auth-context';
import { useAuthGuard } from '@/hooks/use-auth-guard';
import { useToast } from '@/hooks/use-toast';
import { api } from '@/lib/api-client';
import { cn } from '@/lib/utils';
import type { BatchAnalysisResponse } from '@/types';

// Type for individual repository result in a batch
interface BatchRepositoryResult {
  analysis_id?: string;
  repository_url: string;
  repository_name: string;
  context: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  analysis?: {
    insights_count?: number;
    questions_count?: number;
    evidence_patterns_count?: number;
  };
  error?: string;
  created_at?: string;
}

interface AggregatedInsights {
  analyzed_repositories: number;
  total_repositories: number;
  common_patterns: Record<string, { repositories: string[]; count: number }>;
  technology_distribution: Record<string, number>;
  quality_indicators: Record<string, string[]>;
  top_strengths: Array<{ text: string; repositories: string[] }>;
  common_challenges: Array<{ text: string; repositories: string[] }>;
  quality_summary: string;
  repository_comparison: Array<{
    repository: string;
    repository_name: string;
    repository_url: string;
    insights_count: number;
    questions_count: number;
    patterns_count: number;
    key_strengths: string[];
  }>;
}

// Helper to get status icon
const getStatusIcon = (status: string) => {
  switch (status) {
    case 'completed':
      return <CheckCircle className="h-5 w-5 text-green-400" />;
    case 'failed':
      return <XCircle className="h-5 w-5 text-red-400" />;
    case 'processing':
      return <Loader2 className="h-5 w-5 animate-spin text-blue-400" />;
    default:
      return <Clock className="h-5 w-5 text-gray-400" />;
  }
};

// Get available export formats based on tier
const getExportFormats = (plan: string): string[] => {
  switch (plan) {
    case 'starter':
      return ['json', 'csv'];
    case 'growth':
      return ['json', 'csv'];
    case 'scale':
      return ['json', 'csv', 'zip'];
    case 'scale_plus':
      return ['json', 'csv', 'zip'];
    default:
      return ['json'];
  }
};

export default function BatchStatusPage() {
  const params = useParams();
  const router = useRouter();
  const { user } = useAuth();
  const { isLoading: authLoading, showUnauthorized, UnauthorizedComponent } = useAuthGuard();
  const { toast } = useToast();

  const batchId = params.batchId as string;

  const [batch, setBatch] = useState<BatchAnalysisResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isPolling, setIsPolling] = useState(false);
  const [selectedRepo] = useState<BatchRepositoryResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [aggregatedInsights, setAggregatedInsights] = useState<AggregatedInsights | null>(null);
  const [showAggregated, setShowAggregated] = useState(false);
  const [previousStatus, setPreviousStatus] = useState<string | null>(null);

  const exportFormats = user ? getExportFormats(user.subscription_plan) : ['json'];

  // Fetch batch status - useCallback to prevent infinite loops
  const fetchBatchStatus = React.useCallback(async () => {
    try {
      const response = await api.getBatchDetails(batchId);
      const newBatch = response.data;

      // Check for status change and show appropriate notification
      if (previousStatus && previousStatus !== newBatch.status) {
        if (newBatch.status === 'completed') {
          // Show success-first notification for completed batches
          const successRate =
            newBatch.total_repositories > 0
              ? Math.round((newBatch.completed_count / newBatch.total_repositories) * 100)
              : 0;

          if (newBatch.completed_count > 0) {
            toast({
              title: 'Batch Analysis Complete! 🎉',
              description: `Successfully analyzed ${newBatch.completed_count} of ${newBatch.total_repositories} repositories (${successRate}% success rate)${newBatch.failed_count > 0 ? `. ${newBatch.failed_count} repos had issues but analysis continued.` : '.'}`,
            });
          } else {
            toast({
              title: 'Batch Analysis Complete',
              description: 'All repositories encountered issues during analysis.',
              variant: 'destructive',
            });
          }
        } else if (newBatch.status === 'failed') {
          toast({
            title: 'Batch Analysis Failed',
            description: 'The batch analysis encountered critical errors.',
            variant: 'destructive',
          });
        }
      }

      setBatch(newBatch);
      setPreviousStatus(newBatch.status);
      setError(null);

      // Continue polling if still processing
      if (newBatch.status === 'pending' || newBatch.status === 'processing') {
        setIsPolling(true);
      } else {
        setIsPolling(false);
        // Fetch aggregated insights if batch is completed and user has access
        if (
          newBatch.status === 'completed' &&
          user &&
          (user.subscription_plan === 'scale' || user.subscription_plan === 'scale_plus')
        ) {
          try {
            const aggregatedResponse = await api.getBatchAggregatedInsights(batchId);
            if (aggregatedResponse.data?.data) {
              setAggregatedInsights(aggregatedResponse.data.data);
            }
          } catch {
            // Could not fetch aggregated insights - not critical, don't show error
          }
        }
      }
    } catch (error) {
      const err = error as Error & { response?: { data?: { detail?: string } } };
      setError(err.response?.data?.detail || 'Failed to load batch details');
      setIsPolling(false);
      toast({
        title: 'Failed to load batch status',
        description: err.response?.data?.detail || 'Please try again',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  }, [batchId, toast, user, previousStatus]);

  // Export batch results
  const [exportingFormat, setExportingFormat] = useState<string | null>(null);

  const handleExport = React.useCallback(
    async (format: 'json' | 'csv' | 'zip', event?: React.MouseEvent) => {
      // Prevent default and stop propagation
      if (event) {
        event.preventDefault();
        event.stopPropagation();
      }

      // Prevent multiple simultaneous exports
      if (exportingFormat !== null) {
        return;
      }

      setExportingFormat(format);

      try {
        const response = await api.exportBatchResults(batchId, format);

        // Create download link
        let blob: Blob;
        let filename: string;

        if (format === 'json') {
          blob = new Blob([JSON.stringify(response.data, null, 2)], { type: 'application/json' });
          filename = `batch-${batchId}.json`;
        } else {
          blob = response.data as Blob;
          filename = format === 'csv' ? `batch-${batchId}.csv` : `batch-${batchId}.zip`;
        }

        // Force download using a different approach
        const url = window.URL.createObjectURL(blob);

        // Create a temporary iframe for download
        const iframe = document.createElement('iframe');
        iframe.style.display = 'none';
        iframe.src = url;
        document.body.appendChild(iframe);

        // Use the download attribute with a delay
        setTimeout(() => {
          const link = document.createElement('a');
          link.href = url;
          link.download = filename;
          link.setAttribute('download', filename);

          // Trigger download
          const clickEvent = new MouseEvent('click', {
            view: window,
            bubbles: false,
            cancelable: false,
          });
          link.dispatchEvent(clickEvent);

          // Cleanup
          setTimeout(() => {
            document.body.removeChild(iframe);
            window.URL.revokeObjectURL(url);
          }, 100);
        }, 100);

        toast({
          title: 'Export successful',
          description: `Downloaded batch results as ${format.toUpperCase()}`,
        });
      } catch (error) {
        const err = error as Error & { response?: { data?: { detail?: string } } };
        console.error('Export failed:', err);
        toast({
          title: 'Export failed',
          description: err.response?.data?.detail || 'Please try again',
          variant: 'destructive',
        });
      } finally {
        // Reset export state after a delay
        setTimeout(() => {
          setExportingFormat(null);
        }, 2000);
      }
    },
    [batchId, toast, exportingFormat]
  );

  // Initial fetch
  useEffect(() => {
    if (batchId) {
      fetchBatchStatus();
    }
  }, [batchId, fetchBatchStatus]);

  // Polling
  useEffect(() => {
    if (!isPolling) return;

    const interval = setInterval(() => {
      fetchBatchStatus();
    }, 5000); // Poll every 5 seconds

    return () => clearInterval(interval);
  }, [isPolling, fetchBatchStatus]);

  // Handle loading state
  if (authLoading || isLoading) {
    return (
      <div className="flex min-h-[calc(100vh-12rem)] items-center justify-center bg-[#0A0A0A]">
        <div className="text-center">
          <div className="mb-4 inline-flex h-16 w-16 items-center justify-center">
            <div className="h-12 w-12 animate-spin rounded-full border-4 border-purple-600 border-t-transparent" />
          </div>
          <p className="text-gray-400">Loading batch analysis...</p>
        </div>
      </div>
    );
  }

  // Handle unauthorized state
  if (showUnauthorized && UnauthorizedComponent) {
    return <UnauthorizedComponent />;
  }

  if (!batch) {
    return (
      <div className="min-h-[calc(100vh-12rem)] bg-[#0A0A0A] py-8">
        <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8">
          <ExiqusCard className="p-12 text-center" glow="purple">
            <AlertCircle className="mx-auto mb-4 h-16 w-16 text-red-400" />
            <h1 className="mb-4 font-bold text-2xl text-gray-100">Batch Not Found</h1>
            <p className="mb-6 text-gray-400">
              {error || 'This batch analysis could not be found.'}
            </p>
            <ExiqusButton onClick={() => router.push('/batch/history')}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Batch History
            </ExiqusButton>
          </ExiqusCard>
        </div>
      </div>
    );
  }

  const progress =
    batch.total_repositories > 0
      ? ((batch.completed_count + batch.failed_count) / batch.total_repositories) * 100
      : 0;

  return (
    <div className="min-h-[calc(100vh-12rem)] bg-[#0A0A0A] py-8">
      {/* Animated gradient background */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 h-80 w-80 animate-pulse rounded-full bg-purple-500/20 blur-3xl"></div>
        <div className="absolute -bottom-40 -left-40 h-80 w-80 animate-pulse rounded-full bg-blue-500/20 blur-3xl delay-1000"></div>
      </div>

      <div className="relative mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <div className="mb-4 flex items-center gap-4">
            <Link href="/batch/history">
              <ExiqusButton variant="ghost" size="sm">
                <ArrowLeft className="h-4 w-4" />
              </ExiqusButton>
            </Link>
            <div className="flex-1">
              <h1 className="mb-2 font-bold text-3xl text-gray-100">
                <GradientText>Batch Analysis Status</GradientText>
              </h1>
              <p className="text-gray-400">
                Batch ID: <code className="text-purple-400">{batchId}</code>
              </p>
            </div>
            <Badge
              className={cn(
                'px-3 py-1',
                batch.status === 'completed' && 'bg-green-500/20 text-green-400',
                batch.status === 'failed' && 'bg-red-500/20 text-red-400',
                batch.status === 'processing' && 'bg-blue-500/20 text-blue-400',
                batch.status === 'pending' && 'bg-gray-500/20 text-gray-400'
              )}
            >
              {getStatusIcon(batch.status)}
              <span className="ml-2 capitalize">
                {batch.status === 'completed' && batch.completed_count > 0 && batch.failed_count > 0
                  ? `Completed: ${batch.completed_count}/${batch.total_repositories} successful`
                  : batch.status === 'completed' && batch.failed_count === 0
                    ? 'All Complete'
                    : batch.status === 'failed' && batch.completed_count === 0
                      ? 'All Failed'
                      : batch.status}
              </span>
            </Badge>
          </div>
        </div>

        {/* Success Rate Alert for Completed Batches */}
        {batch.status === 'completed' && batch.completed_count > 0 && (
          <Alert className="mb-6 border-green-500/30 bg-green-500/10">
            <CheckCircle className="h-4 w-4 text-green-400" />
            <AlertDescription className="text-green-300">
              <span className="font-semibold">Batch Analysis Complete!</span> Successfully analyzed{' '}
              {batch.completed_count} of {batch.total_repositories} repositories
              {batch.total_repositories > 0 && (
                <>
                  {' '}
                  ({Math.round((batch.completed_count / batch.total_repositories) * 100)}% success
                  rate)
                </>
              )}
              .{' '}
              {batch.failed_count > 0 && (
                <>
                  {batch.failed_count} {batch.failed_count === 1 ? 'repository' : 'repositories'}{' '}
                  encountered issues but analysis continued.
                </>
              )}
            </AlertDescription>
          </Alert>
        )}

        {/* Progress Overview */}
        <ExiqusCard className="mb-8 p-6" glow="subtle">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-semibold text-gray-100 text-xl">Progress Overview</h2>
            {batch.status === 'processing' && (
              <ExiqusButton variant="ghost" size="sm" onClick={fetchBatchStatus}>
                <RefreshCw className="h-4 w-4" />
              </ExiqusButton>
            )}
          </div>

          <div className="mb-6 space-y-4">
            <div>
              <div className="mb-2 flex justify-between text-sm">
                <span className="text-gray-400">Overall Progress</span>
                <span className="text-gray-100">
                  {batch.completed_count + batch.failed_count} / {batch.total_repositories}
                </span>
              </div>
              <Progress value={progress} className="h-3" />
            </div>

            <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
              <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
                <p className="mb-1 text-gray-400 text-xs">Total</p>
                <p className="font-bold text-gray-100 text-xl">{batch.total_repositories}</p>
              </div>
              <div className="rounded-lg border border-green-500/20 bg-green-500/10 p-3">
                <p className="mb-1 text-green-400 text-xs">Completed</p>
                <p className="font-bold text-green-400 text-xl">{batch.completed_count}</p>
              </div>
              {batch.total_repositories > 0 && batch.status === 'completed' && (
                <div className="rounded-lg border border-purple-500/20 bg-purple-500/10 p-3">
                  <p className="mb-1 text-purple-400 text-xs">Success Rate</p>
                  <p className="font-bold text-purple-400 text-xl">
                    {Math.round((batch.completed_count / batch.total_repositories) * 100)}%
                  </p>
                </div>
              )}
              <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-3">
                <p className="mb-1 text-red-400 text-xs">Failed</p>
                <p className="font-bold text-red-400 text-xl">{batch.failed_count}</p>
              </div>
              <div className="rounded-lg border border-blue-500/20 bg-blue-500/10 p-3">
                <p className="mb-1 text-blue-400 text-xs">Processing</p>
                <p className="font-bold text-blue-400 text-xl">
                  {batch.total_repositories - batch.completed_count - batch.failed_count}
                </p>
              </div>
            </div>
          </div>

          {/* Export Actions */}
          {batch.status === 'completed' && (
            <>
              <Separator className="my-6 bg-white/[0.06]" />
              <div>
                <h3 className="mb-3 font-medium text-gray-300 text-sm">Export Results</h3>
                <div className="flex flex-wrap gap-3">
                  {exportFormats.includes('json') && (
                    <ExiqusButton
                      variant="secondary"
                      size="sm"
                      onClick={(e) => handleExport('json', e)}
                      disabled={exportingFormat !== null}
                    >
                      <FileJson className="mr-2 h-4 w-4" />
                      {exportingFormat === 'json' ? 'Exporting...' : 'Export JSON'}
                    </ExiqusButton>
                  )}
                  {exportFormats.includes('csv') && (
                    <ExiqusButton
                      variant="secondary"
                      size="sm"
                      onClick={(e) => handleExport('csv', e)}
                      disabled={exportingFormat !== null}
                    >
                      <FileSpreadsheet className="mr-2 h-4 w-4" />
                      {exportingFormat === 'csv' ? 'Exporting...' : 'Export CSV'}
                    </ExiqusButton>
                  )}
                  {exportFormats.includes('zip') && (
                    <ExiqusButton
                      variant="secondary"
                      size="sm"
                      onClick={(e) => handleExport('zip', e)}
                      disabled={exportingFormat !== null}
                    >
                      <FileArchive className="mr-2 h-4 w-4" />
                      {exportingFormat === 'zip' ? 'Exporting...' : 'Export ZIP'}
                    </ExiqusButton>
                  )}
                </div>
              </div>
            </>
          )}
        </ExiqusCard>

        {/* Aggregated Insights Section - Only for Scale/Scale+ */}
        {aggregatedInsights && batch.status === 'completed' && (
          <ExiqusCard
            className="mb-6 border-2 border-purple-500/30 bg-gradient-to-br from-purple-900/10 to-blue-900/10 p-6"
            glow="purple"
          >
            <div className="mb-6 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-500/20">
                  <TrendingUp className="h-5 w-5 text-purple-400" />
                </div>
                <div>
                  <h2 className="font-bold text-2xl text-gray-100">
                    <GradientText>Cross-Repository Intelligence</GradientText>
                  </h2>
                  <p className="text-gray-400 text-sm">
                    Aggregated patterns and insights across repositories in this batch
                  </p>
                  <div className="mt-2 rounded-md border border-amber-800/50 bg-amber-900/20 px-3 py-1.5">
                    <p className="text-amber-300 text-xs">
                      ⚠️ This analysis aggregates patterns across all repositories in your batch for
                      comparative insights
                    </p>
                  </div>
                </div>
              </div>
              <ExiqusButton
                variant="outline"
                size="sm"
                onClick={() => setShowAggregated(!showAggregated)}
                className="border-purple-500/30 hover:border-purple-500/50"
              >
                {showAggregated ? (
                  <>
                    <ChevronUp className="mr-2 h-4 w-4" /> Collapse
                  </>
                ) : (
                  <>
                    <ChevronDown className="mr-2 h-4 w-4" /> Expand
                  </>
                )}
              </ExiqusButton>
            </div>

            {showAggregated && (
              <div className="space-y-6">
                {/* Summary Stats */}
                <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                  <div className="rounded-lg bg-white/[0.02] p-3">
                    <p className="text-gray-400 text-sm">Repositories Analyzed</p>
                    <p className="font-bold text-2xl text-gray-100">
                      {aggregatedInsights.analyzed_repositories}/
                      {aggregatedInsights.total_repositories}
                    </p>
                  </div>
                  <div className="rounded-lg bg-white/[0.02] p-3">
                    <p className="text-gray-400 text-sm">Common Patterns</p>
                    <p className="font-bold text-2xl text-gray-100">
                      {Object.keys(aggregatedInsights.common_patterns || {}).length}
                    </p>
                  </div>
                  <div className="rounded-lg bg-white/[0.02] p-3">
                    <p className="text-gray-400 text-sm">Technologies</p>
                    <p className="font-bold text-2xl text-gray-100">
                      {Object.keys(aggregatedInsights.technology_distribution || {}).length}
                    </p>
                  </div>
                  <div className="rounded-lg bg-white/[0.02] p-3">
                    <p className="text-gray-400 text-sm">Quality Indicators</p>
                    <p className="font-bold text-2xl text-gray-100">
                      {
                        Object.values(aggregatedInsights.quality_indicators || {}).filter(
                          (repos: string[]) => repos.length > 0
                        ).length
                      }
                    </p>
                  </div>
                </div>

                {/* Top Common Patterns */}
                {aggregatedInsights.common_patterns &&
                  Object.keys(aggregatedInsights.common_patterns).length > 0 && (
                    <div>
                      <h3 className="mb-3 font-medium text-gray-100 text-lg">
                        Common Evidence Patterns
                      </h3>
                      <div className="space-y-2">
                        {Object.entries(aggregatedInsights.common_patterns)
                          .slice(0, 5)
                          .map(
                            ([pattern, data]: [
                              string,
                              { repositories: string[]; count: number },
                            ]) => (
                              <div
                                key={pattern}
                                className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3"
                              >
                                <div className="mb-1 flex items-center justify-between">
                                  <span className="font-medium text-gray-100">
                                    {pattern.replace(/_/g, ' ')}
                                  </span>
                                  <Badge variant="secondary">
                                    Found in {data.count} {data.count === 1 ? 'repo' : 'repos'}
                                  </Badge>
                                </div>
                                <p className="text-gray-400 text-sm">
                                  {data.repositories.slice(0, 3).join(', ')}
                                  {data.repositories.length > 3 &&
                                    ` +${data.repositories.length - 3} more`}
                                </p>
                              </div>
                            )
                          )}
                      </div>
                    </div>
                  )}

                {/* Top Strengths & Challenges - Full Width Layout */}
                <div className="space-y-6">
                  {/* Top Strengths */}
                  {aggregatedInsights.top_strengths &&
                    aggregatedInsights.top_strengths.length > 0 && (
                      <div>
                        <div className="mb-4 flex items-center gap-2">
                          <CheckCircle className="h-5 w-5 text-green-400" />
                          <h3 className="font-semibold text-gray-100 text-lg">
                            Common Strengths Across Repositories
                          </h3>
                        </div>
                        <div className="grid gap-3 lg:grid-cols-2 xl:grid-cols-3">
                          {aggregatedInsights.top_strengths.map(
                            (strength: { text: string; repositories: string[] }, idx: number) => (
                              <div
                                key={idx}
                                className="group relative overflow-hidden rounded-xl border border-green-500/20 bg-gradient-to-br from-green-500/10 to-green-500/5 p-4 transition-all hover:border-green-500/30 hover:shadow-green-500/10 hover:shadow-lg"
                              >
                                <div className="absolute -top-8 -right-8 h-24 w-24 rounded-full bg-green-500/10 blur-2xl" />
                                <p className="relative mb-2 font-medium text-gray-100">
                                  {strength.text}
                                </p>
                                <div className="relative flex flex-wrap gap-1">
                                  {strength.repositories.map((repo: string, repoIdx: number) => (
                                    <span
                                      key={repoIdx}
                                      className="inline-flex items-center rounded-md bg-green-500/20 px-2 py-0.5 font-medium text-green-300 text-xs"
                                    >
                                      {repo}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )
                          )}
                        </div>
                      </div>
                    )}

                  {/* Common Challenges */}
                  {aggregatedInsights.common_challenges &&
                    aggregatedInsights.common_challenges.length > 0 && (
                      <div>
                        <div className="mb-4 flex items-center gap-2">
                          <AlertCircle className="h-5 w-5 text-yellow-400" />
                          <h3 className="font-semibold text-gray-100 text-lg">
                            Areas for Exploration
                          </h3>
                        </div>
                        <div className="grid gap-3 lg:grid-cols-2 xl:grid-cols-3">
                          {aggregatedInsights.common_challenges.map(
                            (challenge: { text: string; repositories: string[] }, idx: number) => (
                              <div
                                key={idx}
                                className="group relative overflow-hidden rounded-xl border border-yellow-500/20 bg-gradient-to-br from-yellow-500/10 to-yellow-500/5 p-4 transition-all hover:border-yellow-500/30 hover:shadow-lg hover:shadow-yellow-500/10"
                              >
                                <div className="absolute -top-8 -right-8 h-24 w-24 rounded-full bg-yellow-500/10 blur-2xl" />
                                <p className="relative mb-2 font-medium text-gray-100">
                                  {challenge.text}
                                </p>
                                <div className="relative flex flex-wrap gap-1">
                                  {challenge.repositories.map((repo: string, repoIdx: number) => (
                                    <span
                                      key={repoIdx}
                                      className="inline-flex items-center rounded-md bg-yellow-500/20 px-2 py-0.5 font-medium text-xs text-yellow-300"
                                    >
                                      {repo}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )
                          )}
                        </div>
                      </div>
                    )}
                </div>

                {/* Quality Summary */}
                {aggregatedInsights.quality_summary && (
                  <div>
                    <h3 className="mb-3 font-medium text-gray-100 text-lg">Quality Evidence</h3>
                    <div className="grid gap-3 md:grid-cols-2">
                      {Object.entries(aggregatedInsights.quality_summary).map(([key, value]) => (
                        <div
                          key={key}
                          className="flex items-center gap-2 rounded-lg bg-white/[0.02] p-3"
                        >
                          <CheckCircle className="h-4 w-4 text-green-400" />
                          <span className="text-gray-300 text-sm">{value as string}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Repository Comparison Table - Enhanced */}
                {aggregatedInsights.repository_comparison &&
                  aggregatedInsights.repository_comparison.length > 0 && (
                    <div>
                      <div className="mb-4 flex items-center gap-2">
                        <GitBranch className="h-5 w-5 text-purple-400" />
                        <h3 className="font-semibold text-gray-100 text-lg">
                          Repository Comparison Matrix
                        </h3>
                      </div>
                      <div className="overflow-hidden rounded-xl border border-white/[0.06] bg-white/[0.02]">
                        <div className="overflow-x-auto">
                          <table className="w-full">
                            <thead>
                              <tr className="border-white/[0.06] border-b bg-gradient-to-r from-purple-900/20 to-blue-900/20">
                                <th className="p-3 text-left font-semibold text-gray-300 text-sm">
                                  Repository
                                </th>
                                <th className="p-3 text-center font-semibold text-gray-300 text-sm">
                                  Insights
                                </th>
                                <th className="p-3 text-center font-semibold text-gray-300 text-sm">
                                  Questions
                                </th>
                                <th className="p-3 text-center font-semibold text-gray-300 text-sm">
                                  Patterns
                                </th>
                                <th className="min-w-[400px] p-3 text-left font-semibold text-gray-300 text-sm">
                                  <span className="flex items-center gap-2">
                                    <span className="inline-flex h-6 w-6 items-center justify-center rounded bg-purple-500/20">
                                      ✨
                                    </span>
                                    Key Observations
                                  </span>
                                </th>
                              </tr>
                            </thead>
                            <tbody>
                              {aggregatedInsights.repository_comparison.map(
                                (
                                  repo: AggregatedInsights['repository_comparison'][0],
                                  idx: number
                                ) => (
                                  <tr
                                    key={idx}
                                    className="border-white/[0.03] border-b transition-colors hover:bg-white/[0.02]"
                                  >
                                    <td className="p-3">
                                      <div className="flex items-center gap-2">
                                        <div className="h-2 w-2 rounded-full bg-purple-400" />
                                        <span className="font-medium text-gray-100">
                                          {repo.repository}
                                        </span>
                                      </div>
                                    </td>
                                    <td className="p-3 text-center">
                                      <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-blue-500/20 font-semibold text-blue-300 text-sm">
                                        {repo.insights_count}
                                      </span>
                                    </td>
                                    <td className="p-3 text-center">
                                      <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-purple-500/20 font-semibold text-purple-300 text-sm">
                                        {repo.questions_count}
                                      </span>
                                    </td>
                                    <td className="p-3 text-center">
                                      <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-green-500/20 font-semibold text-green-300 text-sm">
                                        {repo.patterns_count}
                                      </span>
                                    </td>
                                    <td className="p-3">
                                      {repo.key_strengths.length > 0 ? (
                                        <div className="rounded-lg border border-purple-500/20 bg-gradient-to-r from-purple-500/10 to-blue-500/10 p-3">
                                          <p className="font-medium text-gray-100 text-sm leading-relaxed">
                                            ✨ {repo.key_strengths[0]}
                                          </p>
                                          {repo.key_strengths.length > 1 && (
                                            <div className="mt-2 flex flex-wrap gap-1">
                                              {repo.key_strengths
                                                .slice(1, 3)
                                                .map((strength: string, idx: number) => (
                                                  <span
                                                    key={idx}
                                                    className="inline-flex items-center rounded-md bg-purple-500/20 px-2 py-0.5 font-medium text-purple-300 text-xs"
                                                  >
                                                    +{strength.split(' ').slice(0, 3).join(' ')}...
                                                  </span>
                                                ))}
                                              {repo.key_strengths.length > 3 && (
                                                <span className="inline-flex items-center rounded-md bg-purple-500/20 px-2 py-0.5 font-medium text-purple-300 text-xs">
                                                  +{repo.key_strengths.length - 3} more
                                                </span>
                                              )}
                                            </div>
                                          )}
                                        </div>
                                      ) : (
                                        <div className="rounded-lg border border-gray-700/30 bg-gray-800/30 p-3">
                                          <p className="text-gray-500 text-sm italic">
                                            No significant patterns identified
                                          </p>
                                        </div>
                                      )}
                                    </td>
                                  </tr>
                                )
                              )}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </div>
                  )}
              </div>
            )}
          </ExiqusCard>
        )}

        {/* Repository Results */}
        <ExiqusCard className="p-6" glow="subtle">
          <h2 className="mb-4 font-semibold text-gray-100 text-xl">Repository Results</h2>

          <div className="space-y-3">
            {batch.results && batch.results.length > 0 ? (
              (batch.results as BatchRepositoryResult[]).map((repo, index) => (
                <div
                  key={index}
                  className={cn(
                    'rounded-lg border p-4 transition-all',
                    'border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.04]',
                    selectedRepo?.repository_url === repo.repository_url && 'border-purple-500/50'
                  )}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <GitBranch className="h-5 w-5 text-purple-400" />
                      <div>
                        <h3 className="font-medium text-gray-100">{repo.repository_name}</h3>
                        <p className="text-gray-400 text-sm">{repo.repository_url}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <Badge
                        className={cn(
                          'capitalize',
                          repo.status === 'completed' && 'bg-green-500/20 text-green-400',
                          repo.status === 'failed' && 'bg-red-500/20 text-red-400',
                          repo.status === 'processing' && 'bg-blue-500/20 text-blue-400',
                          repo.status === 'pending' && 'bg-gray-500/20 text-gray-400'
                        )}
                      >
                        {getStatusIcon(repo.status)}
                        <span className="ml-2">{repo.status}</span>
                      </Badge>
                      {repo.status === 'completed' && repo.analysis && repo.analysis_id ? (
                        <Link href={`/analyses/${repo.analysis_id}`}>
                          <ExiqusButton variant="ghost" size="sm">
                            <Eye className="h-4 w-4" />
                          </ExiqusButton>
                        </Link>
                      ) : null}
                    </div>
                  </div>

                  {repo.error && (
                    <Alert className="mt-3 border-red-500/20 bg-red-500/10">
                      <AlertCircle className="h-4 w-4 text-red-400" />
                      <AlertDescription className="text-red-400">{repo.error}</AlertDescription>
                    </Alert>
                  )}

                  {repo.status === 'completed' && repo.analysis ? (
                    <div className="mt-3 grid grid-cols-3 gap-3 text-sm">
                      <div className="rounded bg-white/[0.02] p-2">
                        <p className="text-gray-500">Insights</p>
                        <p className="font-medium text-gray-300">
                          {repo.analysis.insights_count || 0}
                        </p>
                      </div>
                      <div className="rounded bg-white/[0.02] p-2">
                        <p className="text-gray-500">Questions</p>
                        <p className="font-medium text-gray-300">
                          {repo.analysis.questions_count || 0}
                        </p>
                      </div>
                      <div className="rounded bg-white/[0.02] p-2">
                        <p className="text-gray-500">Patterns</p>
                        <p className="font-medium text-gray-300">
                          {repo.analysis.evidence_patterns_count || 0}
                        </p>
                      </div>
                    </div>
                  ) : null}
                </div>
              ))
            ) : batch.failed_count > 0 && batch.error_messages ? (
              // Show failed repositories from error messages
              <div className="space-y-3">
                {batch.error_messages.map((errorMsg: string, index: number) => {
                  // Parse the error message to extract repository URL
                  const urlMatch = errorMsg.match(/^(https:\/\/github\.com\/[^:]+):/);
                  const repoUrl = urlMatch ? urlMatch[1] : 'Unknown repository';
                  const repoName = repoUrl.split('/').slice(-2).join('/');

                  // Extract and parse error details
                  let userFriendlyError = 'Analysis failed';

                  // Check for specific error patterns and provide user-friendly messages
                  if (errorMsg.includes('timeout') || errorMsg.includes('timed out')) {
                    // Check if this was likely a cancellation (timeout happens quickly)
                    if (errorMsg.includes('timeout_seconds')) {
                      const timeMatch = errorMsg.match(/timeout_seconds['":\s]+(\d+)/);
                      const timeoutSecs = timeMatch ? parseInt(timeMatch[1]) : 0;

                      if (timeoutSecs < 300) {
                        // Under 5 minutes likely means cancellation
                        userFriendlyError = 'Analysis was cancelled or interrupted';
                      } else {
                        userFriendlyError = 'Analysis took too long to complete';
                      }
                    } else {
                      userFriendlyError =
                        'Analysis timed out - the repository may be too large or complex';
                    }
                  } else if (errorMsg.includes('404')) {
                    userFriendlyError = 'Repository not found - it may be private or deleted';
                  } else if (errorMsg.includes('403') || errorMsg.includes('unauthorized')) {
                    userFriendlyError = 'Access denied - the repository may be private';
                  } else if (errorMsg.includes('rate limit')) {
                    userFriendlyError = 'GitHub API rate limit exceeded - please try again later';
                  } else if (errorMsg.includes('500') || errorMsg.includes('server error')) {
                    userFriendlyError = 'Server error occurred during analysis';
                  } else {
                    // Try to extract a clean message from JSON-like structure
                    const msgMatch = errorMsg.match(/'message':\s*'([^']+)'/);
                    if (msgMatch && msgMatch[1]) {
                      // Clean up the message
                      userFriendlyError = msgMatch[1]
                        .replace(/\. Please try.*$/, '') // Remove suggestions
                        .replace(/\. This repository.*$/, '') // Remove technical details
                        .replace(/Repository analysis/, 'Analysis')
                        .trim();
                    }
                  }

                  return (
                    <div
                      key={index}
                      className="rounded-lg border border-red-500/20 bg-red-500/5 p-4"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <GitBranch className="h-5 w-5 text-red-400" />
                          <div>
                            <h3 className="font-medium text-gray-100">{repoName}</h3>
                            <p className="text-gray-400 text-sm">{repoUrl}</p>
                          </div>
                        </div>
                        <Badge className="bg-red-500/20 text-red-400">
                          {getStatusIcon('failed')}
                          <span className="ml-2">Failed</span>
                        </Badge>
                      </div>
                      <Alert className="mt-3 border-red-500/20 bg-red-500/10">
                        <AlertCircle className="h-4 w-4 text-red-400" />
                        <AlertDescription className="text-red-400">
                          {userFriendlyError}
                        </AlertDescription>
                      </Alert>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="py-8 text-center">
                <p className="text-gray-400">No repository results available</p>
              </div>
            )}
          </div>
        </ExiqusCard>

        {/* Metadata */}
        <div className="mt-8 text-center text-gray-500 text-sm">
          <p>
            {batch.created_at && (
              <>Started: {format(new Date(batch.created_at), 'MMM d, yyyy h:mm a')}</>
            )}
            {batch.updated_at && (
              <> • Last updated: {format(new Date(batch.updated_at), 'h:mm a')}</>
            )}
          </p>
        </div>
      </div>
    </div>
  );
}
