// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import {
  AlertCircle,
  Archive,
  ArrowRight,
  Briefcase,
  Building2,
  CheckCircle,
  ChevronRight,
  Clock,
  Database,
  Eye,
  FileSpreadsheet,
  FileText,
  GitBranch,
  Info,
  Layers,
  Loader2,
  Plus,
  Rocket,
  Shield,
  Sparkles,
  TrendingUp,
  Upload,
  Users,
  X,
  Zap,
} from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCallback, useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { ExiqusButton, ExiqusCard, GradientText } from '@/components/ui/exiqus-components';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useAuth } from '@/contexts/auth-context';
import { useAuthGuard } from '@/hooks/use-auth-guard';
import { useToast } from '@/hooks/use-toast';
import { api } from '@/lib/api-client';
import { cn } from '@/lib/utils';

// Validation schema
const batchFormSchema = z.object({
  repositories: z
    .array(z.string().url('Invalid URL format'))
    .min(2, 'At least 2 repositories required for batch analysis')
    .max(15, 'Maximum 15 repositories allowed'),
  context: z.enum(['startup', 'enterprise', 'agency', 'open_source']),
  concurrency_mode: z.enum(['sequential', 'balanced', 'fast']),
});

type BatchFormValues = z.infer<typeof batchFormSchema>;

// Context options with sophisticated styling
const CONTEXT_OPTIONS = [
  {
    value: 'startup',
    label: 'Startup',
    icon: Rocket,
    description: 'Fast iteration & adaptability',
    gradient: 'from-purple-600 to-pink-600',
    bgGradient: 'from-purple-900/20 to-pink-900/20',
    borderColor: 'border-purple-500/50',
  },
  {
    value: 'enterprise',
    label: 'Enterprise',
    icon: Building2,
    description: 'Scalability & architecture',
    gradient: 'from-blue-600 to-cyan-600',
    bgGradient: 'from-blue-900/20 to-cyan-900/20',
    borderColor: 'border-blue-500/50',
  },
  {
    value: 'agency',
    label: 'Agency',
    icon: Briefcase,
    description: 'Project variety & reusability',
    gradient: 'from-orange-600 to-amber-600',
    bgGradient: 'from-orange-900/20 to-amber-900/20',
    borderColor: 'border-orange-500/50',
  },
  {
    value: 'open_source',
    label: 'Open Source',
    icon: Users,
    description: 'Community & maintenance',
    gradient: 'from-green-600 to-emerald-600',
    bgGradient: 'from-green-900/20 to-emerald-900/20',
    borderColor: 'border-green-500/50',
  },
];

// Helper to validate GitHub URL
const isValidGitHubUrl = (url: string): boolean => {
  try {
    const parsed = new URL(url);
    return parsed.hostname === 'github.com' && parsed.pathname.split('/').length >= 3;
  } catch {
    return false;
  }
};

// Get batch limit based on tier
const getBatchLimit = (plan: string): number => {
  switch (plan) {
    case 'starter':
      return 2;
    case 'growth':
      return 5;
    case 'scale':
      return 10;
    case 'scale_plus':
      return 15;
    default:
      return 0;
  }
};

// Tier benefits display
const TIER_BENEFITS = [
  { tier: 'Starter', limit: 2, icon: Zap, color: 'text-yellow-400' },
  { tier: 'Growth', limit: 5, icon: TrendingUp, color: 'text-green-400' },
  { tier: 'Scale', limit: 10, icon: Layers, color: 'text-blue-400' },
  { tier: 'Scale+', limit: 15, icon: Shield, color: 'text-purple-400' },
];

// Concurrency mode options
const CONCURRENCY_MODES: Record<
  string,
  {
    value: string;
    label: string;
    icon: React.ComponentType<{ className?: string }>;
    description: string;
    timeEstimate: Record<string, string>;
    qualityNote: string;
    gradient: string;
    bgGradient: string;
    borderColor: string;
    requiresPlan?: string[];
  }
> = {
  sequential: {
    value: 'sequential',
    label: 'Highest Quality',
    icon: CheckCircle,
    description: 'One at a time for deepest analysis',
    timeEstimate: {
      enterprise: '~10-15 min for 5 repos',
      scale_plus: '~30-45 min for 15 repos',
    },
    qualityNote:
      '✨ Best analysis depth - recommended for final candidates. You can also analyse repos individually for final stage interviews.',
    gradient: 'from-green-600 to-emerald-600',
    bgGradient: 'from-green-900/20 to-emerald-900/20',
    borderColor: 'border-green-500/50',
  },
  balanced: {
    value: 'balanced',
    label: 'Balanced',
    icon: Layers,
    description: '2 concurrent for good quality',
    timeEstimate: {
      enterprise: '~5-8 min for 5 repos',
      scale_plus: '~15-23 min for 15 repos',
    },
    qualityNote: '⚖️ Good quality with faster results',
    gradient: 'from-blue-600 to-cyan-600',
    bgGradient: 'from-blue-900/20 to-cyan-900/20',
    borderColor: 'border-blue-500/50',
    requiresPlan: ['scale', 'scale_plus'], // Enterprise/Scale and Scale+
  },
  fast: {
    value: 'fast',
    label: 'Fastest',
    icon: Zap,
    description: '5 concurrent for quick screening',
    timeEstimate: {
      scale_plus: '~6-9 min for 15 repos',
    },
    qualityNote: '⚡ Quick screening - may miss subtle patterns',
    gradient: 'from-orange-600 to-amber-600',
    bgGradient: 'from-orange-900/20 to-amber-900/20',
    borderColor: 'border-orange-500/50',
    requiresPlan: ['scale_plus'], // Scale+ only
  },
};

export default function BatchAnalysisPage() {
  const { user } = useAuth();
  const router = useRouter();
  const { isLoading, showUnauthorized, UnauthorizedComponent } = useAuthGuard();
  const { toast } = useToast();

  const [urls, setUrls] = useState<string[]>(['']);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [inputMethod, setInputMethod] = useState<'manual' | 'csv'>('manual');
  const [isDragging, setIsDragging] = useState(false);
  const [loadingStage, setLoadingStage] = useState<'preparing' | 'submitting' | 'processing'>(
    'preparing'
  );
  const [_abortController, setAbortController] = useState<AbortController | null>(null);
  const [currentBatchId, setCurrentBatchId] = useState<string | null>(null);

  const batchLimit = user ? getBatchLimit(user.subscription_plan) : 0;
  const canUseBatch = batchLimit > 0;

  const form = useForm<BatchFormValues>({
    resolver: zodResolver(batchFormSchema),
    defaultValues: {
      repositories: [],
      context: 'startup',
      concurrency_mode: 'sequential',
    },
  });

  // Add URL field
  const addUrlField = () => {
    if (urls.length < batchLimit) {
      setUrls([...urls, '']);
    }
  };

  // Remove URL field
  const removeUrlField = (index: number) => {
    const newUrls = urls.filter((_, i) => i !== index);
    setUrls(newUrls.length === 0 ? [''] : newUrls);
  };

  // Update URL
  const updateUrl = (index: number, value: string) => {
    const newUrls = [...urls];
    newUrls[index] = value;
    setUrls(newUrls);
  };

  // Parse CSV file
  const parseCSVFile = useCallback(
    async (file: File): Promise<string[]> => {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => {
          const text = e.target?.result as string;
          const lines = text.split('\n');
          const urls: string[] = [];

          for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed && isValidGitHubUrl(trimmed)) {
              urls.push(trimmed);
            }
          }

          if (urls.length === 0) {
            reject(new Error('No valid GitHub URLs found in CSV'));
          } else if (urls.length > batchLimit) {
            reject(new Error(`CSV contains ${urls.length} URLs, but your limit is ${batchLimit}`));
          } else {
            resolve(urls);
          }
        };
        reader.onerror = () => reject(new Error('Failed to read CSV file'));
        reader.readAsText(file);
      });
    },
    [batchLimit]
  );

  // Process CSV file (shared by upload and drag-drop)
  const processCSVFile = async (file: File) => {
    // Security: Check file extension
    if (!file.name.endsWith('.csv')) {
      toast({
        title: 'Invalid file type',
        description: 'Please upload a CSV file',
        variant: 'destructive',
      });
      return;
    }

    // Security: Check file size (max 1MB)
    const maxSize = 1024 * 1024; // 1MB
    if (file.size > maxSize) {
      toast({
        title: 'File too large',
        description: 'CSV file must be less than 1MB',
        variant: 'destructive',
      });
      return;
    }

    setCsvFile(file);
    try {
      const csvUrls = await parseCSVFile(file);
      setUrls(csvUrls);
      toast({
        title: 'CSV loaded',
        description: `Found ${csvUrls.length} valid GitHub URLs`,
      });
    } catch (error) {
      toast({
        title: 'CSV parsing failed',
        description: error instanceof Error ? error.message : 'Failed to parse CSV',
        variant: 'destructive',
      });
      setCsvFile(null);
    }
  };

  // Handle CSV file upload (click)
  const handleCSVUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    await processCSVFile(file);
  };

  // Handle drag and drop events
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    // Only set dragging to false if we're leaving the drop zone entirely
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX;
    const y = e.clientY;
    if (x < rect.left || x >= rect.right || y < rect.top || y >= rect.bottom) {
      setIsDragging(false);
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      const file = files[0];
      await processCSVFile(file);
    }
  };

  // Submit batch analysis
  const onSubmit = async () => {
    // Don't use form values for repos, use our state directly
    const validUrls = urls.filter((url) => url && isValidGitHubUrl(url));

    if (validUrls.length < 2) {
      toast({
        title: 'Not enough repositories',
        description: 'Please add at least 2 valid GitHub URLs',
        variant: 'destructive',
      });
      return;
    }

    // Create a new AbortController for this submission
    const controller = new AbortController();
    setAbortController(controller);

    setIsSubmitting(true);
    setLoadingStage('preparing');

    try {
      // Show loading stage updates
      setTimeout(() => setLoadingStage('submitting'), 500);

      // Format URLs into the expected structure
      const formattedRepos = validUrls.map((url) => ({
        repository_url: url,
        context: form.getValues('context'),
      }));

      const response = await api.submitBatchAnalysis(
        {
          repositories: formattedRepos,
          concurrency_mode: form.getValues('concurrency_mode'),
        },
        controller.signal
      );

      setLoadingStage('processing');

      // Store the batch ID immediately if we have it
      if (response.data.batch_id) {
        setCurrentBatchId(response.data.batch_id);
      }

      // Always redirect to batch detail page if we have a batch_id
      // This provides better UX - users can monitor progress and see results
      if (response.data.batch_id) {
        toast({
          title: 'Batch analysis started',
          description: `Analyzing ${validUrls.length} repositories. You can monitor progress and view results.`,
        });

        // Small delay before redirect for UX
        setTimeout(() => {
          router.push(`/batch/${response.data.batch_id}`);
        }, 1000);
      } else {
        // Fallback: redirect to analyses list if no batch_id (shouldn't happen)
        toast({
          title: 'Batch analysis submitted',
          description: `Successfully submitted ${validUrls.length} repositories. View them in your analyses.`,
        });

        // Redirect to analyses page where results will appear
        setTimeout(() => {
          router.push('/analyses');
        }, 1500);
      }
    } catch (error) {
      // Clear batch state on error

      const err = error as Error & {
        response?: { data?: { detail?: string } };
        name?: string;
        code?: string;
        message?: string;
      };

      // Check if it was cancelled
      if (err.name === 'CanceledError' || err.code === 'ERR_CANCELED') {
        // User aborted - don't show error toast
      } else if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
        // Handle timeout specifically for Scale/Scale+ users
        const hasBatchHistory =
          user?.subscription_plan === 'scale' || user?.subscription_plan === 'scale_plus';

        if (hasBatchHistory) {
          // For Scale/Scale+ users, explain that processing continues
          toast({
            title: 'Batch processing continues in background',
            description:
              'Your batch analysis is taking longer than expected but continues processing. You can monitor progress in Batch History.',
          });

          // Redirect to batch history after a delay
          setTimeout(() => {
            router.push('/batch/history');
          }, 2000);
        } else {
          // For other tiers, suggest checking analyses later
          toast({
            title: 'Batch processing in progress',
            description:
              'Your batch analysis is taking longer than expected. Check your analyses in a few minutes.',
          });

          setTimeout(() => {
            router.push('/analyses');
          }, 2000);
        }
      } else {
        console.error('Batch submission failed:', err);

        // Check if this is actually a partial failure during processing
        if (err.message?.includes('analysis') || err.message?.includes('repository')) {
          toast({
            title: 'Some repositories encountered issues',
            description:
              'The batch is still processing. Check Batch History to monitor progress and view results.',
          });

          // Redirect to batch history instead of staying on error
          setTimeout(() => {
            router.push('/batch/history');
          }, 2000);
        } else {
          toast({
            title: 'Batch submission failed',
            description: err.response?.data?.detail || err.message || 'Please try again',
            variant: 'destructive',
          });
        }
      }
      setIsSubmitting(false);
      setAbortController(null);
    }
  };

  // Handle loading state
  if (isLoading) {
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

  // Check if user can use batch
  if (!canUseBatch) {
    return (
      <div className="min-h-[calc(100vh-12rem)] bg-[#0A0A0A] py-12">
        <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
          <ExiqusCard className="relative overflow-hidden p-12" glow="purple">
            {/* Background effects */}
            <div className="absolute inset-0 bg-gradient-to-br from-purple-900/10 via-transparent to-blue-900/10" />
            <div className="absolute -top-24 -right-24 h-48 w-48 rounded-full bg-purple-600/20 blur-3xl" />
            <div className="absolute -bottom-24 -left-24 h-48 w-48 rounded-full bg-blue-600/20 blur-3xl" />

            <div className="relative">
              <div className="mb-8 flex justify-center">
                <div className="group relative">
                  <div className="absolute inset-0 animate-pulse rounded-full bg-gradient-to-r from-purple-600 to-blue-600 opacity-50 blur-xl" />
                  <div className="relative rounded-full bg-gradient-to-br from-purple-600/20 to-blue-600/20 p-6">
                    <Database className="h-12 w-12 text-purple-400" />
                  </div>
                </div>
              </div>

              <h1 className="mb-4 text-center font-bold text-4xl">
                <GradientText>Unlock Batch Analysis</GradientText>
              </h1>
              <p className="mx-auto mb-10 max-w-2xl text-center text-gray-400 text-lg">
                Analyze multiple repositories simultaneously with our powerful batch processing.
                Export comprehensive reports in multiple formats.
              </p>

              {/* Tier Benefits Grid */}
              <div className="mb-10 grid grid-cols-2 gap-4 sm:grid-cols-4">
                {TIER_BENEFITS.map((benefit) => {
                  const Icon = benefit.icon;
                  return (
                    <div
                      key={benefit.tier}
                      className="group rounded-lg border border-white/[0.06] bg-white/[0.02] p-4 transition-all hover:border-white/[0.12] hover:bg-white/[0.04]"
                    >
                      <div className="mb-3 flex items-center justify-between">
                        <Icon className={cn('h-5 w-5', benefit.color)} />
                        <Badge variant="secondary" className="text-xs">
                          {benefit.limit} repos
                        </Badge>
                      </div>
                      <h3 className="font-semibold text-gray-100">{benefit.tier}</h3>
                      <p className="mt-1 text-gray-500 text-xs">Per batch</p>
                    </div>
                  );
                })}
              </div>

              {/* CTA */}
              <div className="flex justify-center">
                <ExiqusButton
                  size="lg"
                  onClick={() => router.push('/pricing')}
                  className="group relative overflow-hidden"
                >
                  <span className="relative z-10 flex items-center">
                    <Sparkles className="mr-2 h-5 w-5" />
                    Upgrade Your Plan
                    <ChevronRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
                  </span>
                </ExiqusButton>
              </div>
            </div>
          </ExiqusCard>
        </div>
      </div>
    );
  }

  // Show loading overlay when submitting
  if (isSubmitting) {
    const validUrlCount = urls.filter((u) => u && isValidGitHubUrl(u)).length;
    const selectedContext = CONTEXT_OPTIONS.find((opt) => opt.value === form.getValues('context'));
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#0A0A0A]/95 backdrop-blur-sm">
        {/* Animated gradient background */}
        <div className="pointer-events-none absolute inset-0 overflow-hidden">
          <div className="absolute -top-40 -right-40 h-80 w-80 animate-pulse rounded-full bg-purple-500/30 blur-3xl" />
          <div className="absolute -bottom-40 -left-40 h-80 w-80 animate-pulse rounded-full bg-blue-500/30 blur-3xl delay-1000" />
        </div>

        <div className="relative">
          <ExiqusCard className="p-12 text-center" glow="purple">
            <div className="mb-8 flex justify-center">
              <div className="relative">
                <div className="absolute inset-0 animate-ping rounded-full bg-purple-600/20" />
                <div className="relative rounded-full bg-gradient-to-br from-purple-600/20 to-blue-600/20 p-6">
                  <Database className="h-12 w-12 animate-pulse text-purple-400" />
                </div>
              </div>
            </div>

            <h2 className="mb-4 font-bold text-2xl text-gray-100">
              <GradientText>Preparing Batch Analysis</GradientText>
            </h2>

            <div className="mb-6 space-y-3">
              {/* Stage indicators */}
              <div className="flex items-center justify-center gap-2">
                <div
                  className={cn(
                    'flex items-center gap-2 rounded-full px-3 py-1 text-sm',
                    loadingStage === 'preparing'
                      ? 'bg-purple-500/20 text-purple-400'
                      : 'bg-white/[0.06] text-gray-500'
                  )}
                >
                  {loadingStage === 'preparing' ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <CheckCircle className="h-3 w-3" />
                  )}
                  Validating repositories
                </div>
              </div>

              <div className="flex items-center justify-center gap-2">
                <div
                  className={cn(
                    'flex items-center gap-2 rounded-full px-3 py-1 text-sm',
                    loadingStage === 'submitting'
                      ? 'bg-purple-500/20 text-purple-400'
                      : loadingStage === 'processing'
                        ? 'bg-white/[0.06] text-gray-500'
                        : 'bg-white/[0.06] text-gray-600'
                  )}
                >
                  {loadingStage === 'submitting' ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : loadingStage === 'processing' ? (
                    <CheckCircle className="h-3 w-3" />
                  ) : (
                    <div className="h-3 w-3 rounded-full border border-gray-600" />
                  )}
                  Processing batch analysis on server
                </div>
              </div>

              {/* Add helpful link to batch history */}
              <div className="mt-2 mb-2 text-center">
                <p className="mb-1 text-gray-400 text-xs">Your batch is being processed</p>
                <Link
                  href="/batch/history"
                  className="inline-flex items-center gap-1 text-purple-400 text-sm underline hover:text-purple-300"
                >
                  <Eye className="h-3 w-3" />
                  View batch history to monitor progress →
                </Link>
              </div>

              <div className="flex items-center justify-center gap-2">
                <div
                  className={cn(
                    'flex items-center gap-2 rounded-full px-3 py-1 text-sm',
                    loadingStage === 'processing'
                      ? 'bg-purple-500/20 text-purple-400'
                      : 'bg-white/[0.06] text-gray-600'
                  )}
                >
                  {loadingStage === 'processing' ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <div className="h-3 w-3 rounded-full border border-gray-600" />
                  )}
                  Finalizing results
                </div>
              </div>
            </div>

            <p className="text-gray-400 text-sm">
              Analyzing {validUrlCount} repositories with {selectedContext?.label || 'Startup'}{' '}
              context
            </p>

            {loadingStage === 'submitting' && (
              <p className="mt-2 text-gray-500 text-xs">
                This may take 60-150 seconds per repository
                {form.watch('concurrency_mode') === 'fast'
                  ? ' (processing in fast mode)'
                  : form.watch('concurrency_mode') === 'sequential'
                    ? ' (processing sequentially)'
                    : ' (processing with balanced mode)'}
              </p>
            )}

            {/* Progress bar */}
            <div className="mx-auto mt-6 h-1 w-64 overflow-hidden rounded-full bg-white/[0.06]">
              <div
                className="h-full animate-pulse bg-gradient-to-r from-purple-600 to-blue-600"
                style={{
                  width:
                    loadingStage === 'preparing'
                      ? '33%'
                      : loadingStage === 'submitting'
                        ? '66%'
                        : '100%',
                  transition: 'width 0.5s ease-out',
                }}
              />
            </div>

            {/* Action buttons - View Progress for Enterprise/Scale+ and Cancel */}
            <div className="mt-8 border-white/[0.06] border-t pt-6">
              <div className="flex items-center justify-center gap-6">
                {/* View Progress button - only for Enterprise/Scale/Scale+ during processing */}
                {loadingStage === 'processing' &&
                  user &&
                  (user.subscription_plan === 'scale' || user.subscription_plan === 'scale_plus') &&
                  currentBatchId && (
                    <Link href={`/batch/${currentBatchId}`}>
                      <button
                        type="button"
                        className="group flex items-center justify-center gap-2 text-purple-400 text-sm transition-colors duration-200 hover:text-purple-300"
                      >
                        <div className="flex h-8 w-8 items-center justify-center rounded-full border border-purple-500/50 bg-purple-500/10 transition-all group-hover:border-purple-400">
                          <Eye className="h-4 w-4" />
                        </div>
                        <span>View Progress</span>
                      </button>
                    </Link>
                  )}
              </div>
            </div>
          </ExiqusCard>
        </div>
      </div>
    );
  }

  const validUrlCount = urls.filter((u) => u && isValidGitHubUrl(u)).length;
  const selectedContext = CONTEXT_OPTIONS.find((opt) => opt.value === form.watch('context'));

  return (
    <div className="min-h-[calc(100vh-12rem)] bg-[#0A0A0A] py-12">
      {/* Animated gradient background */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 h-80 w-80 animate-pulse rounded-full bg-purple-500/20 blur-3xl" />
        <div className="absolute -bottom-40 -left-40 h-80 w-80 animate-pulse rounded-full bg-blue-500/20 blur-3xl delay-1000" />
        <div className="absolute top-1/2 left-1/2 h-60 w-60 -translate-x-1/2 -translate-y-1/2 animate-pulse rounded-full bg-cyan-500/10 blur-3xl delay-500" />
      </div>

      <div className="relative mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
        {/* Header with sophisticated styling */}
        <div className="mb-10 text-center">
          <div className="mb-6 inline-flex items-center rounded-full bg-gradient-to-r from-purple-900/20 to-blue-900/20 px-4 py-2 backdrop-blur-sm">
            <Sparkles className="mr-2 h-4 w-4 text-purple-400" />
            <span className="font-medium text-gray-300 text-sm">
              {user?.subscription_plan.replace('_', ' ').toUpperCase()} TIER
            </span>
          </div>

          <h1 className="mb-4 font-bold text-5xl text-gray-100">
            <GradientText>Batch Repository Analysis</GradientText>
          </h1>
          <p className="mx-auto max-w-2xl text-gray-400 text-lg">
            Analyze up to {batchLimit} repositories simultaneously with evidence-based insights
          </p>

          {/* Progress indicator */}
          <div className="mx-auto mt-8 max-w-md">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-500">Repositories selected</span>
              <span
                className={cn(
                  'font-medium transition-colors',
                  validUrlCount >= 2 ? 'text-green-400' : 'text-gray-400'
                )}
              >
                {validUrlCount} / {batchLimit}
              </span>
            </div>
            <div className="mt-2 h-2 overflow-hidden rounded-full bg-white/[0.06]">
              <div
                className="h-full bg-gradient-to-r from-purple-600 to-blue-600 transition-all duration-300"
                style={{ width: `${(validUrlCount / batchLimit) * 100}%` }}
              />
            </div>
          </div>
        </div>

        <Form {...form}>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              onSubmit();
            }}
            className="space-y-8"
          >
            {/* Context Selection with enhanced visuals */}
            <ExiqusCard className="relative overflow-hidden p-8" glow="subtle">
              <div className="absolute inset-0 bg-gradient-to-br from-purple-900/5 via-transparent to-blue-900/5" />

              <FormField
                control={form.control}
                name="context"
                render={({ field }) => (
                  <FormItem className="relative">
                    <div className="mb-6">
                      <FormLabel className="font-semibold text-gray-100 text-lg">
                        Analysis Context
                      </FormLabel>
                      <FormDescription className="mt-2 text-gray-400">
                        Select the hiring context to tailor the analysis patterns
                      </FormDescription>
                    </div>

                    <FormControl>
                      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                        {CONTEXT_OPTIONS.map((option) => {
                          const Icon = option.icon;
                          const isSelected = field.value === option.value;

                          return (
                            <button
                              key={option.value}
                              type="button"
                              onClick={() => field.onChange(option.value)}
                              className={cn(
                                'group relative overflow-hidden rounded-lg border-2 p-4 transition-all duration-300',
                                isSelected
                                  ? cn(
                                      'border-opacity-100',
                                      option.borderColor,
                                      'bg-gradient-to-br',
                                      option.bgGradient
                                    )
                                  : 'border-white/[0.06] bg-white/[0.02] hover:border-white/[0.12] hover:bg-white/[0.04]'
                              )}
                            >
                              {isSelected && (
                                <div
                                  className={cn(
                                    'absolute inset-0 bg-gradient-to-br opacity-10',
                                    option.gradient
                                  )}
                                />
                              )}

                              <div className="relative">
                                <div
                                  className={cn(
                                    'mb-3 inline-flex rounded-lg p-2 transition-colors',
                                    isSelected
                                      ? cn('bg-gradient-to-br', option.gradient, 'text-white')
                                      : 'bg-white/[0.06] text-gray-400 group-hover:text-gray-300'
                                  )}
                                >
                                  <Icon className="h-5 w-5" />
                                </div>

                                <h3
                                  className={cn(
                                    'font-semibold text-sm transition-colors',
                                    isSelected ? 'text-gray-100' : 'text-gray-300'
                                  )}
                                >
                                  {option.label}
                                </h3>
                                <p className="mt-1 text-gray-500 text-xs">{option.description}</p>
                              </div>
                            </button>
                          );
                        })}
                      </div>
                    </FormControl>
                  </FormItem>
                )}
              />
            </ExiqusCard>

            {/* Concurrency Mode Selection - Only for Enterprise/Scale and Scale+ */}
            {user &&
              (user.subscription_plan === 'scale' || user.subscription_plan === 'scale_plus') && (
                <ExiqusCard className="relative overflow-hidden p-8" glow="subtle">
                  <div className="absolute inset-0 bg-gradient-to-br from-indigo-900/5 via-transparent to-purple-900/5" />

                  <FormField
                    control={form.control}
                    name="concurrency_mode"
                    render={({ field }) => (
                      <FormItem className="relative">
                        <div className="mb-6">
                          <FormLabel className="font-semibold text-gray-100 text-lg">
                            Analysis Mode
                          </FormLabel>
                          <FormDescription className="mt-2 text-gray-400">
                            Choose between analysis quality and speed
                          </FormDescription>
                        </div>

                        <FormControl>
                          <div className="space-y-4">
                            {Object.values(CONCURRENCY_MODES).map((mode) => {
                              const Icon = mode.icon;
                              const isSelected = field.value === mode.value;
                              const isDisabled =
                                mode.requiresPlan &&
                                !mode.requiresPlan.includes(user.subscription_plan);
                              const timeEstimate =
                                mode.timeEstimate[
                                  user.subscription_plan as keyof typeof mode.timeEstimate
                                ];

                              if (isDisabled) return null;

                              return (
                                <button
                                  key={mode.value}
                                  type="button"
                                  onClick={() => field.onChange(mode.value)}
                                  disabled={isDisabled}
                                  className={cn(
                                    'group relative w-full overflow-hidden rounded-lg border-2 p-6 text-left transition-all duration-300',
                                    isSelected
                                      ? cn(
                                          'border-opacity-100',
                                          mode.borderColor,
                                          'bg-gradient-to-br',
                                          mode.bgGradient
                                        )
                                      : 'border-white/[0.06] bg-white/[0.02] hover:border-white/[0.12] hover:bg-white/[0.04]',
                                    isDisabled && 'cursor-not-allowed opacity-50'
                                  )}
                                >
                                  {isSelected && (
                                    <div
                                      className={cn(
                                        'absolute inset-0 bg-gradient-to-br opacity-10',
                                        mode.gradient
                                      )}
                                    />
                                  )}

                                  <div className="relative flex items-start space-x-4">
                                    <div
                                      className={cn(
                                        'inline-flex rounded-lg p-3 transition-colors',
                                        isSelected
                                          ? cn('bg-gradient-to-br', mode.gradient, 'text-white')
                                          : 'bg-white/[0.06] text-gray-400 group-hover:text-gray-300'
                                      )}
                                    >
                                      <Icon className="h-6 w-6" />
                                    </div>

                                    <div className="flex-1">
                                      <div className="flex items-center justify-between">
                                        <h3
                                          className={cn(
                                            'font-semibold text-base transition-colors',
                                            isSelected ? 'text-gray-100' : 'text-gray-300'
                                          )}
                                        >
                                          {mode.label}
                                        </h3>
                                        {timeEstimate && (
                                          <Badge variant="outline" className="ml-2">
                                            <Clock className="mr-1 h-3 w-3" />
                                            {timeEstimate}
                                          </Badge>
                                        )}
                                      </div>
                                      <p className="mt-1 text-gray-500 text-sm">
                                        {mode.description}
                                      </p>
                                      <p className="mt-2 text-gray-400 text-sm">
                                        {mode.qualityNote}
                                      </p>
                                    </div>
                                  </div>
                                </button>
                              );
                            })}
                          </div>
                        </FormControl>
                      </FormItem>
                    )}
                  />
                </ExiqusCard>
              )}

            {/* Repository Input with enhanced styling */}
            <ExiqusCard className="relative overflow-hidden p-8" glow="subtle">
              <div className="absolute inset-0 bg-gradient-to-br from-blue-900/5 via-transparent to-purple-900/5" />

              <div className="relative">
                <div className="mb-6 flex items-center justify-between">
                  <div>
                    <h2 className="font-semibold text-gray-100 text-lg">Repository URLs</h2>
                    <p className="mt-1 text-gray-400 text-sm">
                      Add GitHub repositories to analyse in batch
                    </p>
                  </div>
                  {selectedContext && (
                    <Badge className={cn('bg-gradient-to-r text-white', selectedContext.gradient)}>
                      {selectedContext.label} Context
                    </Badge>
                  )}
                </div>

                <Tabs
                  value={inputMethod}
                  onValueChange={(v) => setInputMethod(v as 'manual' | 'csv')}
                >
                  <TabsList className="grid w-full grid-cols-2 bg-white/[0.02]">
                    <TabsTrigger value="manual" className="data-[state=active]:bg-white/[0.06]">
                      <GitBranch className="mr-2 h-4 w-4" />
                      Manual Input
                    </TabsTrigger>
                    <TabsTrigger value="csv" className="data-[state=active]:bg-white/[0.06]">
                      <FileSpreadsheet className="mr-2 h-4 w-4" />
                      CSV Upload
                    </TabsTrigger>
                  </TabsList>

                  <TabsContent value="manual" className="mt-6">
                    <div className="space-y-3">
                      {urls.map((url, index) => (
                        <div key={index} className="group relative">
                          <div className="flex gap-2">
                            <div className="relative flex-1">
                              <GitBranch className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-gray-500" />
                              <Input
                                placeholder="https://github.com/owner/repository"
                                value={url}
                                onChange={(e) => updateUrl(index, e.target.value)}
                                className={cn(
                                  'pl-10 transition-all',
                                  url && isValidGitHubUrl(url)
                                    ? 'border-green-500/30 bg-green-500/5'
                                    : url && !isValidGitHubUrl(url)
                                      ? 'border-red-500/30 bg-red-500/5'
                                      : ''
                                )}
                              />
                            </div>
                            {urls.length > 1 && (
                              <ExiqusButton
                                type="button"
                                variant="ghost"
                                size="sm"
                                onClick={() => removeUrlField(index)}
                                className="opacity-0 transition-opacity group-hover:opacity-100"
                              >
                                <X className="h-4 w-4" />
                              </ExiqusButton>
                            )}
                          </div>
                        </div>
                      ))}

                      {urls.length < batchLimit && (
                        <ExiqusButton
                          type="button"
                          variant="secondary"
                          size="sm"
                          onClick={addUrlField}
                          className="w-full border-dashed"
                        >
                          <Plus className="mr-2 h-4 w-4" />
                          Add Repository ({urls.length}/{batchLimit})
                        </ExiqusButton>
                      )}
                    </div>
                  </TabsContent>

                  <TabsContent value="csv" className="mt-6">
                    <div className="space-y-4">
                      <div
                        className={cn(
                          'group relative overflow-hidden rounded-lg border-2 border-dashed p-8 text-center transition-all',
                          isDragging
                            ? 'scale-[1.02] border-purple-500 bg-purple-500/10'
                            : 'border-white/[0.1] bg-white/[0.01] hover:border-white/[0.2] hover:bg-white/[0.02]'
                        )}
                        onDragOver={handleDragOver}
                        onDragEnter={handleDragEnter}
                        onDragLeave={handleDragLeave}
                        onDrop={handleDrop}
                      >
                        <Input
                          type="file"
                          accept=".csv"
                          onChange={handleCSVUpload}
                          className="hidden"
                          id="csv-upload"
                        />
                        <Label htmlFor="csv-upload" className="cursor-pointer">
                          <div
                            className={cn(
                              'mb-4 inline-flex rounded-full p-4 transition-all',
                              isDragging
                                ? 'scale-110 bg-gradient-to-br from-purple-600/30 to-blue-600/30'
                                : 'bg-gradient-to-br from-purple-900/20 to-blue-900/20'
                            )}
                          >
                            <Upload
                              className={cn(
                                'h-8 w-8 transition-all',
                                isDragging ? 'animate-pulse text-purple-300' : 'text-purple-400'
                              )}
                            />
                          </div>
                          <p
                            className={cn(
                              'mb-2 font-medium text-lg transition-colors',
                              isDragging ? 'text-purple-300' : 'text-gray-100'
                            )}
                          >
                            {csvFile
                              ? csvFile.name
                              : isDragging
                                ? 'Release to upload'
                                : 'Drop your CSV file here or click to browse'}
                          </p>
                          <p className="text-gray-500 text-sm">
                            One GitHub URL per line • Max {batchLimit} URLs • 1MB limit
                          </p>
                        </Label>

                        {/* Visual feedback overlay when dragging */}
                        {isDragging && (
                          <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
                            <div className="absolute inset-0 animate-pulse bg-gradient-to-br from-purple-600/20 to-blue-600/20" />
                          </div>
                        )}
                      </div>

                      <div className="rounded-lg border border-white/[0.06] bg-gradient-to-br from-purple-900/10 to-blue-900/10 p-4">
                        <h4 className="mb-3 flex items-center font-medium text-gray-300 text-sm">
                          <FileText className="mr-2 h-4 w-4 text-purple-400" />
                          CSV Format Example
                        </h4>
                        <code className="block rounded bg-black/40 p-3 text-gray-400 text-xs">
                          https://github.com/facebook/react
                          <br />
                          https://github.com/vercel/next.js
                          <br />
                          https://github.com/microsoft/TypeScript
                          <br />
                          https://github.com/tailwindlabs/tailwindcss
                        </code>
                        <a
                          href="/sample-batch-analysis.csv"
                          download
                          className="mt-3 inline-flex items-center text-purple-400 text-xs transition-colors hover:text-purple-300"
                        >
                          <Archive className="mr-1 h-3 w-3" />
                          Download sample CSV
                        </a>
                      </div>

                      {csvFile && urls.length > 0 && (
                        <Alert className="border-green-500/20 bg-green-500/10">
                          <FileText className="h-4 w-4 text-green-400" />
                          <AlertDescription>
                            Loaded {urls.length} repositories from {csvFile.name}
                          </AlertDescription>
                        </Alert>
                      )}
                    </div>
                  </TabsContent>
                </Tabs>

                {/* Preview loaded URLs with enhanced styling */}
                {inputMethod === 'csv' && urls.length > 0 && (
                  <div className="mt-6">
                    <h3 className="mb-3 flex items-center font-medium text-gray-300 text-sm">
                      <Database className="mr-2 h-4 w-4 text-blue-400" />
                      Loaded Repositories
                    </h3>
                    <div className="max-h-48 space-y-2 overflow-y-auto rounded-lg border border-white/[0.06] bg-gradient-to-br from-blue-900/10 to-purple-900/10 p-4">
                      {urls.map((url, index) => (
                        <div
                          key={index}
                          className="flex items-center gap-3 rounded bg-white/[0.02] px-3 py-2"
                        >
                          <span className="font-medium text-gray-500 text-xs">#{index + 1}</span>
                          <GitBranch className="h-4 w-4 text-purple-400" />
                          <span className="flex-1 truncate text-gray-300 text-sm">{url}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </ExiqusCard>

            {/* Enhanced Info Section */}
            <div className="grid gap-4 sm:grid-cols-3">
              <ExiqusCard className="p-4" glow="subtle">
                <div className="flex items-start gap-3">
                  <Clock className="mt-0.5 h-5 w-5 text-blue-400" />
                  <div>
                    <h4 className="font-medium text-gray-100 text-sm">Processing Time</h4>
                    <p className="mt-1 text-gray-400 text-xs">60-150s per repository</p>
                  </div>
                </div>
              </ExiqusCard>

              <ExiqusCard className="p-4" glow="subtle">
                <div className="flex items-start gap-3">
                  <Shield className="mt-0.5 h-5 w-5 text-green-400" />
                  <div>
                    <h4 className="font-medium text-gray-100 text-sm">Evidence-Based</h4>
                    <p className="mt-1 text-gray-400 text-xs">Factual patterns only</p>
                  </div>
                </div>
              </ExiqusCard>

              <ExiqusCard className="p-4" glow="subtle">
                <div className="flex items-start gap-3">
                  <Archive className="mt-0.5 h-5 w-5 text-purple-400" />
                  <div>
                    <h4 className="font-medium text-gray-100 text-sm">Export Formats</h4>
                    <p className="mt-1 text-gray-400 text-xs">JSON, CSV, ZIP</p>
                  </div>
                </div>
              </ExiqusCard>
            </div>

            {/* Tier-specific notice about where results will appear */}
            {user &&
              (user.subscription_plan === 'starter' || user.subscription_plan === 'growth') && (
                <Alert className="border-blue-500/20 bg-blue-500/10">
                  <Info className="h-4 w-4 text-blue-400" />
                  <AlertDescription className="text-gray-300">
                    <strong>Note:</strong> With your{' '}
                    {user.subscription_plan.replace('_', ' ').charAt(0).toUpperCase() +
                      user.subscription_plan.slice(1)}{' '}
                    plan, batch analysis results will appear in your{' '}
                    <span className="font-semibold text-blue-400">Analyses</span> page. Batch
                    history and grouped results are available with Scale and Scale+ plans.
                  </AlertDescription>
                </Alert>
              )}

            {/* Submit section with better visual hierarchy */}
            <ExiqusCard className="relative overflow-hidden p-8" glow="purple">
              <div className="absolute inset-0 bg-gradient-to-br from-purple-900/10 via-transparent to-blue-900/10" />

              <div className="relative text-center">
                {/* Status Badge */}
                <div className="mb-6 inline-flex items-center rounded-full bg-white/[0.06] px-4 py-2">
                  {validUrlCount >= 2 ? (
                    <>
                      <CheckCircle className="mr-2 h-4 w-4 text-green-400" />
                      <span className="font-medium text-green-400 text-sm">Ready to analyze</span>
                    </>
                  ) : (
                    <>
                      <AlertCircle className="mr-2 h-4 w-4 text-yellow-400" />
                      <span className="font-medium text-sm text-yellow-400">
                        Need at least 2 repositories
                      </span>
                    </>
                  )}
                </div>

                {/* Main Message */}
                <h3 className="mb-2 font-bold text-2xl text-gray-100">
                  {validUrlCount >= 2
                    ? `Analyze ${validUrlCount} ${validUrlCount === 1 ? 'Repository' : 'Repositories'}`
                    : 'Add Repository URLs Above'}
                </h3>
                <p className="mb-8 text-gray-400">
                  {validUrlCount >= 2
                    ? `Batch analysis will process all repositories in parallel`
                    : `Select at least 2 repositories to start batch analysis`}
                </p>

                {/* Batch Analysis Disclaimer */}
                <Alert className="mb-6 border-amber-500/20 bg-amber-500/10">
                  <AlertCircle className="h-4 w-4 text-amber-500" />
                  <AlertDescription className="text-amber-200">
                    <strong>Note:</strong> Batch analysis cannot be cancelled once started.
                    Processing time varies based on repository size and quantity.
                  </AlertDescription>
                </Alert>

                {/* Action Buttons - Centered and Prominent */}
                <div className="flex justify-center gap-4">
                  <ExiqusButton
                    type="button"
                    variant="ghost"
                    size="lg"
                    onClick={() => router.push('/dashboard')}
                    className="min-w-[120px]"
                  >
                    Cancel
                  </ExiqusButton>

                  <ExiqusButton
                    type="submit"
                    disabled={isSubmitting || validUrlCount < 2}
                    size="lg"
                    className="group relative min-w-[200px] overflow-hidden"
                  >
                    {isSubmitting ? (
                      <>
                        <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                        Starting Analysis...
                      </>
                    ) : (
                      <>
                        <Zap className="mr-2 h-5 w-5" />
                        Start Batch Analysis
                        <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
                      </>
                    )}
                  </ExiqusButton>
                </div>

                {/* Helper Text */}
                {validUrlCount > 0 && validUrlCount < 2 && (
                  <p className="mt-6 text-gray-500 text-sm">
                    Add {2 - validUrlCount} more{' '}
                    {2 - validUrlCount === 1 ? 'repository' : 'repositories'} to continue
                  </p>
                )}
              </div>
            </ExiqusCard>
          </form>
        </Form>
      </div>
    </div>
  );
}
