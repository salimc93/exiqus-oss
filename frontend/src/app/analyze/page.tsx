// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import {
  AlertCircle,
  ArrowRight,
  Award,
  Briefcase,
  Building2,
  CheckCircle,
  Code2,
  ExternalLink,
  Eye,
  GitBranch,
  Github,
  Layers,
  Loader2,
  Rocket,
  Search,
  Shield,
  Sparkles,
  Target,
  TrendingUp,
  Users,
  XCircle,
  Zap,
} from 'lucide-react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import { toast } from 'sonner';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { ContextLockIndicator } from '@/components/ui/context-lock-indicator';
import { ExiqusButton, ExiqusCard, GradientText } from '@/components/ui/exiqus-components';
import { useAuth } from '@/contexts/auth-context';
import { useAuthGuard } from '@/hooks/use-auth-guard';
import { useCandidateContext } from '@/hooks/use-candidate-context';
import { api } from '@/lib/api-client';

const CONTEXT_OPTIONS = [
  {
    value: 'startup',
    label: 'Startup Context',
    icon: Rocket,
    description: 'Fast iteration, MVP patterns, adaptability signals',
    gradient: 'from-purple-600 to-pink-600',
    bgGradient: 'from-purple-900/20 to-pink-900/20',
    borderColor: 'border-purple-500',
  },
  {
    value: 'enterprise',
    label: 'Enterprise Context',
    icon: Building2,
    description: 'Architecture patterns, scalability, documentation',
    gradient: 'from-blue-600 to-cyan-600',
    bgGradient: 'from-blue-900/20 to-cyan-900/20',
    borderColor: 'border-blue-500',
  },
  {
    value: 'agency',
    label: 'Agency Context',
    icon: Briefcase,
    description: 'Project variety, code reusability, client patterns',
    gradient: 'from-orange-600 to-amber-600',
    bgGradient: 'from-orange-900/20 to-amber-900/20',
    borderColor: 'border-orange-500',
  },
  {
    value: 'open_source',
    label: 'Open Source',
    icon: Users,
    description: 'Community patterns, contribution quality, maintenance',
    gradient: 'from-green-600 to-emerald-600',
    bgGradient: 'from-green-900/20 to-emerald-900/20',
    borderColor: 'border-green-500',
  },
];

const ROLE_OPTIONS = [
  {
    value: 'junior',
    label: 'Junior',
    icon: Target,
    description: '0-2 years: Learning fundamentals',
    gradient: 'from-green-600 to-teal-600',
    bgGradient: 'from-green-900/20 to-teal-900/20',
    borderColor: 'border-green-500',
  },
  {
    value: 'mid',
    label: 'Mid-Level',
    icon: Award,
    description: '3-5 years: Independent contributor',
    gradient: 'from-blue-600 to-indigo-600',
    bgGradient: 'from-blue-900/20 to-indigo-900/20',
    borderColor: 'border-blue-500',
  },
  {
    value: 'senior',
    label: 'Senior',
    icon: TrendingUp,
    description: '5+ years: Technical leadership',
    gradient: 'from-purple-600 to-violet-600',
    bgGradient: 'from-purple-900/20 to-violet-900/20',
    borderColor: 'border-purple-500',
  },
];

export default function AnalyzePage() {
  const { isLoading, showUnauthorized, UnauthorizedComponent } = useAuthGuard();
  const searchParams = useSearchParams();
  const { user, refreshUser } = useAuth();

  // FREE tier restrictions: Open Source context only, no role selection
  const isFreeTier = user?.subscription_plan === 'free';
  const [repoUrl, setRepoUrl] = useState('');
  const [context, setContext] = useState(isFreeTier ? 'open_source' : 'startup');
  const [role, setRole] = useState('mid');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [validationError, setValidationError] = useState('');
  const [isValidUrl, setIsValidUrl] = useState(false);
  const [analyzingRepo, setAnalyzingRepo] = useState<string>('');
  const [loadingStage, setLoadingStage] = useState<
    'fetching' | 'analyzing' | 'generating' | 'retrying'
  >('fetching');
  const [retryInfo, setRetryInfo] = useState<{
    attempt: number;
    maxAttempts: number;
    message: string;
  } | null>(null);

  // Username extraction from repo URL (for context lock on paid tiers)
  const [extractedUsername, setExtractedUsername] = useState<string>('');
  const [isValidUsername, setIsValidUsername] = useState(false);

  const router = useRouter();

  // Fetch locked context for the candidate (paid tiers only)
  const { lockedContext } = useCandidateContext(
    !isFreeTier && isValidUsername ? extractedUsername : null
  );

  const validateGitHubUrl = (url: string): boolean => {
    const trimmedUrl = url.trim();

    if (!trimmedUrl) {
      setValidationError('Please enter a GitHub repository URL');
      setIsValidUrl(false);
      setExtractedUsername('');
      setIsValidUsername(false);
      return false;
    }

    // Extract base URL without query params, hash, or trailing slashes
    const urlWithoutParams = trimmedUrl.split('?')[0].split('#')[0].replace(/\/+$/, '');

    // Extract just the owner/repo part, ignoring any subdirectory paths
    const githubMatch = urlWithoutParams.match(
      /^https?:\/\/(www\.)?github\.com\/([\w.-]+)\/([\w.-]+)/i
    );
    if (!githubMatch) {
      setValidationError(
        'Please enter a valid GitHub repository URL (e.g., https://github.com/owner/repo)'
      );
      setIsValidUrl(false);
      setExtractedUsername('');
      setIsValidUsername(false);
      return false;
    }

    // Extract the username (owner) from the URL
    const username = githubMatch[2];

    // Construct the clean base repository URL
    const cleanUrl = `https://github.com/${username}/${githubMatch[3]}`;

    // Update the repoUrl with the cleaned version if it's different
    if (trimmedUrl !== cleanUrl) {
      setRepoUrl(cleanUrl);
    }

    // Update username extraction state
    setExtractedUsername(username);
    setIsValidUsername(true);
    setValidationError('');
    setIsValidUrl(true);
    return true;
  };

  // Check for username or repo query parameter
  useEffect(() => {
    const username = searchParams.get('username');
    const repo = searchParams.get('repo');

    if (repo) {
      // Repo URL provided from Deep Dive button - pre-fill the input and validate
      setRepoUrl(repo);
      validateGitHubUrl(repo);
    } else if (username) {
      // Username provided - pre-fill with a prompt, user will select the repo
      // We can't auto-fill the URL since we don't know which repo they want
    }
  }, [searchParams]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateGitHubUrl(repoUrl)) {
      return;
    }

    setIsAnalyzing(true);
    setLoadingStage('fetching');
    setRetryInfo(null); // Reset retry info

    // Extract repo name from URL for display
    // Clean URL first: remove protocol, query params, hash, and trailing slashes
    const cleanUrl = repoUrl
      .replace(/^https?:\/\/(www\.)?github\.com\//, '')
      .split('?')[0]
      .split('#')[0]
      .replace(/\.git$/, '')
      .replace(/\/$/, '');

    // Extract owner/repo from the clean URL (ignore any additional path segments)
    const pathSegments = cleanUrl.split('/');
    const repoName = pathSegments.length >= 2 ? `${pathSegments[0]}/${pathSegments[1]}` : cleanUrl;
    setAnalyzingRepo(repoName);

    // Simulate stage progression
    setTimeout(() => setLoadingStage('analyzing'), 2000);
    setTimeout(() => setLoadingStage('generating'), 15000);

    try {
      // Clean the URL to standard format: https://github.com/owner/repo
      const standardUrl = `https://github.com/${repoName}`;

      // Prepare the request data
      const requestData = {
        repository_url: standardUrl,
        context: context as 'startup' | 'enterprise' | 'agency' | 'open_source',
        role: role as 'junior' | 'mid' | 'senior',
        force_refresh: false,
      };

      // Calculate timeout based on user's plan
      // Higher tiers get longer timeouts due to more complex AI processing
      const getAnalysisTimeout = () => {
        switch (user?.subscription_plan) {
          case 'free':
            return 60000; // 1 minute (templates only)
          case 'starter':
            return 180000; // 3 minutes (Basic/Starter tier)
          case 'growth':
            return 300000; // 5 minutes (Professional/Growth tier)
          case 'scale':
            return 480000; // 8 minutes (Scale tier)
          case 'scale_plus':
            return 600000; // 10 minutes (Scale+ tier)
          default:
            return 300000; // 5 minutes default
        }
      };

      // Call the analysis API with appropriate timeout
      const response = await api.analyze(requestData, getAnalysisTimeout());

      // Extract the analysis ID from the response
      // Check multiple possible locations for the ID
      const analysisId =
        response.data.id || response.data.metadata?.analysis_id || response.data.analysis_id;

      // Extract task ID from response if available (optional)
      const responseTaskId = (response.data.metadata as { task_id?: string })?.task_id;
      if (responseTaskId) {
      }

      if (analysisId) {
        toast.success('Analysis completed successfully!');
        // Refresh user data to update usage counts
        try {
          await refreshUser();
        } catch {
          // Silently fail - not critical
        }
        // Check if we should return to candidate hub
        const returnTo = searchParams.get('returnTo');
        const username = searchParams.get('username');
        if (returnTo === 'candidate-hub' && username) {
          router.push(`/candidate-hub/${username}`);
        } else {
          // Redirect to the analysis results page
          router.push(`/analyses/${analysisId}`);
        }
      } else {
        // If no ID, show the results inline (backward compatibility)
        toast.error('Analysis completed but no ID received. Please check your analysis history.');
        console.error('No analysis ID found in response:', response.data);
        // You could store the results in state and display them here
      }
    } catch (error: unknown) {
      console.error('Analysis failed:', error);

      const errorResponse = error as { response?: { status?: number; data?: { detail?: string } } };

      // Handle rate limiting (429)
      if (errorResponse.response?.status === 429) {
        const errorDetail = errorResponse.response.data?.detail || '';

        // Extract reset time from error message (e.g., "Resets in 45 minutes")
        const resetMatch = errorDetail.match(/Resets in (\d+) minutes?/i);
        const resetMinutes = resetMatch ? parseInt(resetMatch[1]) : null;

        // Extract current count and limit (e.g., "(15/20)")
        const countMatch = errorDetail.match(/\((\d+)\/(\d+)\)/);
        const currentCount = countMatch ? parseInt(countMatch[1]) : null;
        const limit = countMatch ? parseInt(countMatch[2]) : null;

        toast.error(
          <div className="space-y-2">
            <div className="flex items-center gap-2 font-semibold">
              <svg
                className="h-5 w-5 text-amber-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              Rate Limit Reached
            </div>
            {currentCount && limit && (
              <div className="text-sm">
                You&apos;ve used {currentCount} of {limit} analyses this hour.
              </div>
            )}
            {resetMinutes && (
              <div className="text-amber-300 text-sm">
                ⏱️ Resets in{' '}
                <strong>
                  {resetMinutes} minute{resetMinutes !== 1 ? 's' : ''}
                </strong>
              </div>
            )}
            <div className="mt-2 text-gray-400 text-xs">Take a break and come back soon! ☕</div>
          </div>,
          { duration: 8000 }
        );
      } else if (errorResponse.response?.status === 413) {
        const errorDetail = errorResponse.response.data?.detail;
        const detailString = typeof errorDetail === 'string' ? errorDetail : '';

        if (detailString.includes('Repository size')) {
          const match = detailString.match(
            /Repository size \(([^)]+)\) exceeds maximum allowed size \(([^)]+)\)/
          );
          if (match) {
            toast.error(
              `Repository is too large (${match[1]}). Maximum allowed size is ${match[2]}.`
            );
          } else {
            toast.error('Repository is too large for analysis. Please try a smaller repository.');
          }
        } else {
          toast.error('Request too large. Please try a smaller repository.');
        }
      } else if (errorResponse.response?.status === 403) {
        const errorDetail = errorResponse.response.data?.detail;

        // Check if it's an object with quota information
        if (typeof errorDetail === 'object' && errorDetail !== null) {
          const quotaError = errorDetail as {
            error?: string;
            message?: string;
            current_usage?: number;
            limit?: number;
            billing_period?: string;
          };

          // Check if this is a repo deep dive quota error
          if (quotaError.error?.includes('repo deep dive')) {
            const currentUsage = quotaError.current_usage || 0;
            const limit = quotaError.limit || 0;

            toast.error(
              <div className="space-y-2">
                <div className="font-semibold">Repo Deep Dive Quota Reached</div>
                <div className="text-sm">
                  You&apos;ve used all {limit} repository analyses this month ({currentUsage}/
                  {limit}).
                </div>
                <div className="mt-2 text-gray-400 text-xs">
                  This is separate from your Candidate Assessment quota. Upgrade for more capacity.
                </div>
              </div>,
              {
                duration: 8000,
              }
            );
          } else {
            // Generic quota error
            toast.error(
              quotaError.message ||
                'You have reached your analysis quota. Please upgrade your plan.'
            );
          }
        } else {
          // String error detail
          const detailString = typeof errorDetail === 'string' ? errorDetail : '';

          if (detailString.includes('private repository')) {
            toast.error(
              'This repository appears to be private. Only public repositories are supported.'
            );
          } else {
            toast.error('You have reached your analysis quota. Please upgrade your plan.');
          }
        }
      } else if (errorResponse.response?.status === 401) {
        // Don't show error toast for 401 errors - the interceptor handles session expiry
        // Just silently fail and let the auth interceptor redirect
      } else if (errorResponse.response?.status === 400) {
        // Handle both string and object error responses
        const errorDetail = errorResponse.response.data?.detail;
        if (typeof errorDetail === 'object' && errorDetail !== null) {
          // If detail is an object, extract the error message and retry info
          const errorObj = errorDetail as {
            error?: string;
            message?: string;
            retry_info?: { retries_performed: number };
          };
          const errorMessage = errorObj.error || errorObj.message || 'Invalid repository URL';

          // Include retry information if available
          if (errorObj.retry_info && errorObj.retry_info.retries_performed > 0) {
            toast.error(
              `${errorMessage} (attempted ${errorObj.retry_info.retries_performed} retries)`
            );
          } else {
            toast.error(errorMessage);
          }
        } else {
          toast.error(errorDetail || 'Invalid repository URL');
        }
      } else {
        toast.error('Failed to analyse repository. Please try again.');
      }
    } finally {
      setIsAnalyzing(false);
      setAnalyzingRepo('');
      setLoadingStage('fetching'); // Reset for next analysis
      setRetryInfo(null); // Reset retry info
    }
  };

  const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const url = e.target.value.trim(); // Auto-trim to prevent trailing/leading spaces
    setRepoUrl(url);

    // Clear validation error when user starts typing
    if (validationError) {
      setValidationError('');
    }

    // Validate and update the checkmark/X display
    if (url) {
      validateGitHubUrl(url);
    } else {
      setIsValidUrl(false);
    }
  };

  // Show loading state
  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="mb-4 inline-flex h-16 w-16 items-center justify-center">
            <div className="h-12 w-12 animate-spin rounded-full border-4 border-purple-600 border-t-transparent" />
          </div>
          <p className="text-gray-400">Preparing repository analysis tools...</p>
        </div>
      </div>
    );
  }

  // Show unauthorized component
  if (showUnauthorized && UnauthorizedComponent) {
    return <UnauthorizedComponent />;
  }

  return (
    <div className="min-h-screen bg-[#0A0A0A]">
      {/* Animated gradient background */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 h-80 w-80 animate-pulse rounded-full bg-purple-500/20 blur-3xl"></div>
        <div className="absolute -bottom-40 -left-40 h-80 w-80 animate-pulse rounded-full bg-blue-500/20 blur-3xl delay-1000"></div>
        <div className="absolute top-1/2 left-1/2 h-80 w-80 -translate-x-1/2 -translate-y-1/2 animate-pulse rounded-full bg-gradient-to-r from-purple-500/10 to-blue-500/10 blur-3xl delay-500"></div>
      </div>

      {/* Full-screen loading overlay */}
      {isAnalyzing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
          <ExiqusCard className="max-w-md p-8 text-center" glow="purple">
            <div className="mb-6">
              <Loader2 className="mx-auto h-16 w-16 animate-spin text-purple-400" />
            </div>
            <h2 className="mb-4 font-semibold text-2xl">
              <GradientText>Analysing Repository</GradientText>
            </h2>
            <p className="mb-2 font-medium text-gray-300 text-lg">{analyzingRepo}</p>
            <p className="mb-6 text-gray-400">
              Our AI is examining code patterns, architecture, and development practices...
            </p>
            {retryInfo && (
              <div className="mb-4 rounded-lg border border-amber-600/30 bg-amber-900/20 px-4 py-3">
                <p className="flex items-center justify-center gap-2 text-amber-400 text-sm">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {retryInfo.message ||
                    `Optimizing analysis (attempt ${retryInfo.attempt} of ${retryInfo.maxAttempts})...`}
                </p>
              </div>
            )}
            <div className="space-y-2 text-gray-500 text-sm">
              <p className="flex items-center justify-center gap-2">
                {loadingStage === 'fetching' ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <CheckCircle className="h-4 w-4 text-green-500" />
                )}
                Fetching repository data
              </p>
              <p className="flex items-center justify-center gap-2">
                {loadingStage === 'analyzing' ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : loadingStage === 'generating' ? (
                  <CheckCircle className="h-4 w-4 text-green-500" />
                ) : (
                  <span className="block h-4 w-4" />
                )}
                Analysing code patterns
              </p>
              <p className="flex items-center justify-center gap-2">
                {loadingStage === 'generating' ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <span className="block h-4 w-4" />
                )}
                Generating insights
              </p>
              {loadingStage === 'retrying' && (
                <p className="mt-4 flex items-center justify-center gap-2 text-amber-400">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Optimizing response format...
                </p>
              )}
            </div>
          </ExiqusCard>
        </div>
      )}

      <div className="container relative mx-auto max-w-6xl px-4 py-8">
        <div className="space-y-8">
          {/* Header */}
          <div className="relative text-center">
            <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-purple-900/20 to-blue-900/20 px-4 py-2 font-medium text-sm">
              <Sparkles className="h-4 w-4 text-purple-400" />
              AI-Powered Repository Analysis
            </div>
            <h1 className="mb-4 font-bold text-4xl tracking-tight md:text-5xl">
              <GradientText>Analyse Any GitHub Repository</GradientText>
            </h1>
            <p className="mx-auto max-w-2xl text-gray-400 text-xl">
              Discover evidence-based insights about code patterns, architecture quality, and
              development practices
            </p>
          </div>

          {/* Main Analysis Form */}
          <ExiqusCard className="p-8" glow="purple">
            <div className="mb-6">
              <h2 className="flex items-center gap-2 font-semibold text-2xl text-gray-100">
                <GitBranch className="h-6 w-6 text-purple-400" />
                Repository Analysis
              </h2>
              <p className="mt-2 text-gray-400">
                Enter a GitHub repository URL to discover code patterns and evidence
              </p>
            </div>
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Repository URL Input */}
              <div className="space-y-2">
                <label className="flex items-center gap-2 font-medium text-sm">
                  <Github className="h-4 w-4 text-purple-400" />
                  Repository URL
                </label>
                <div className="group relative">
                  <div className="absolute inset-0 rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 opacity-0 blur transition-opacity duration-500 group-focus-within:opacity-30 group-hover:opacity-20"></div>
                  <div className="relative">
                    <Github className="absolute top-1/2 left-4 h-5 w-5 -translate-y-1/2 text-gray-500 transition-colors group-focus-within:text-purple-400" />
                    <input
                      type="url"
                      placeholder="https://github.com/owner/repository"
                      value={repoUrl}
                      onChange={handleUrlChange}
                      disabled={isAnalyzing}
                      className={`h-14 w-full rounded-lg border px-12 py-2 pr-12 text-lg transition-all duration-300 ${validationError ? 'border-red-500 bg-red-500/5' : 'border-white/[0.09] bg-white/[0.06] hover:bg-white/[0.08] focus:bg-white/[0.09]'} text-gray-100 outline-none placeholder:text-gray-500 focus:border-purple-500 disabled:opacity-50 ${isValidUrl ? 'border-green-500/50' : ''}`}
                      style={{
                        WebkitUserSelect: 'text',
                        MozUserSelect: 'text',
                        msUserSelect: 'text',
                        userSelect: 'text',
                        cursor: 'text',
                      }}
                    />
                    {isValidUrl && (
                      <CheckCircle className="fade-in absolute top-1/2 right-4 h-5 w-5 -translate-y-1/2 animate-in text-green-500 duration-300" />
                    )}
                    {repoUrl && !isValidUrl && (
                      <XCircle className="fade-in absolute top-1/2 right-4 h-5 w-5 -translate-y-1/2 animate-in text-red-400 duration-300" />
                    )}
                  </div>
                </div>
                {validationError && (
                  <p className="flex items-center gap-1 text-red-500 text-sm">
                    <AlertCircle className="h-4 w-4" />
                    {validationError}
                  </p>
                )}

                {/* Username Extraction Indicator (Paid Tiers Only) */}
                {!isFreeTier && isValidUsername && extractedUsername && (
                  <div className="slide-in-from-top-2 fade-in mt-3 animate-in rounded-lg border border-purple-500/30 bg-purple-900/10 p-3 duration-300">
                    <div className="flex items-center gap-2 text-sm">
                      <CheckCircle className="h-4 w-4 flex-shrink-0 text-purple-400" />
                      <span className="text-gray-300">
                        Candidate identified:{' '}
                        <span className="font-medium text-purple-400">@{extractedUsername}</span>
                      </span>
                    </div>
                    <p className="mt-1 ml-6 text-gray-400 text-xs">
                      This repository will be linked to the candidate profile for consistent
                      insights
                    </p>
                  </div>
                )}
              </div>

              {/* Context Lock Indicator (Paid Tiers Only) */}
              {!isFreeTier && isValidUsername && lockedContext && (
                <ContextLockIndicator
                  username={extractedUsername}
                  currentRole={role}
                  currentContext={context}
                  lockedRole={lockedContext.role}
                  lockedContext={lockedContext.organization_context}
                  isLocked={true}
                />
              )}

              {/* Analysis Context Selection */}
              <div className="space-y-3">
                <label className="flex items-center gap-2 font-medium text-gray-300 text-sm">
                  <Layers className="h-4 w-4 text-purple-400" />
                  Analysis Context
                </label>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  {CONTEXT_OPTIONS.map((option, index) => {
                    const Icon = option.icon;
                    const isSelected = context === option.value;
                    // FREE tier restriction: Only open_source context available
                    const isDisabled = isFreeTier && option.value !== 'open_source';
                    return (
                      <label
                        key={option.value}
                        className={`group relative flex overflow-hidden rounded-xl border-2 p-4 transition-all duration-300 ${
                          isDisabled
                            ? 'cursor-not-allowed opacity-40'
                            : 'cursor-pointer hover:scale-[1.02]'
                        } ${
                          isSelected
                            ? `${option.borderColor} bg-gradient-to-br ${option.bgGradient} shadow-lg`
                            : 'border-white/[0.09] bg-white/[0.03] hover:border-white/[0.15] hover:bg-white/[0.06]'
                        }`}
                        style={{
                          animationDelay: `${index * 50}ms`,
                        }}
                      >
                        {/* Animated gradient overlay */}
                        {isSelected && (
                          <div
                            className={`absolute inset-0 bg-gradient-to-br ${option.gradient} animate-pulse opacity-10`}
                          />
                        )}

                        <input
                          type="radio"
                          name="context"
                          value={option.value}
                          checked={isSelected}
                          onChange={(e) => !isDisabled && setContext(e.target.value)}
                          disabled={isDisabled}
                          className="sr-only"
                        />
                        <div className="relative flex items-start gap-3">
                          <div
                            className={`rounded-lg p-2 transition-all duration-300 ${
                              isSelected
                                ? `bg-gradient-to-br ${option.gradient} text-white shadow-md group-hover:shadow-lg`
                                : 'bg-white/[0.06] text-gray-400 group-hover:bg-white/[0.09] group-hover:text-gray-300'
                            }`}
                          >
                            <Icon className="h-5 w-5" />
                          </div>
                          <div className="flex-1">
                            <p
                              className={`font-medium transition-colors ${
                                isSelected
                                  ? 'text-gray-100'
                                  : 'text-gray-200 group-hover:text-gray-100'
                              }`}
                            >
                              {option.label}
                            </p>
                            <p className="mt-1 text-gray-400 text-xs">{option.description}</p>
                          </div>
                          {isSelected && (
                            <CheckCircle className="fade-in absolute top-2 right-2 h-4 w-4 animate-in text-green-400 duration-300" />
                          )}
                        </div>
                      </label>
                    );
                  })}
                </div>
              </div>

              {/* FREE Tier AI Analysis Quota */}
              {isFreeTier && user && (
                <Alert className="border-purple-500/30 bg-gradient-to-r from-purple-900/20 to-pink-900/20">
                  <Zap className="h-4 w-4 text-purple-400" />
                  <AlertDescription className="text-gray-300 text-sm">
                    <div className="space-y-2">
                      <div>
                        <strong className="text-purple-300">FREE Tier:</strong> You get{' '}
                        <span className="font-bold text-purple-400">10 analyses</span> per month
                      </div>
                      <div className="text-gray-400 text-xs">
                        Start with 3 premium analyses, then 7 basic analyses. Upgrade to{' '}
                        <a
                          href="/pricing"
                          className="font-semibold text-purple-400 underline hover:text-purple-300"
                        >
                          Starter
                        </a>{' '}
                        for unlimited premium analyses.
                      </div>
                    </div>
                  </AlertDescription>
                </Alert>
              )}

              {/* FREE Tier Context Restriction Notice */}
              {isFreeTier && (
                <Alert className="border-blue-500/30 bg-gradient-to-r from-blue-900/20 to-cyan-900/20">
                  <Sparkles className="h-4 w-4 text-blue-400" />
                  <AlertDescription className="text-gray-300 text-sm">
                    <div className="space-y-2">
                      <div>
                        <strong className="text-blue-300">FREE Tier:</strong>{' '}
                        <span className="text-blue-100">Open Source context only</span>
                      </div>
                      <div className="text-gray-400 text-xs">
                        Unlock{' '}
                        <span className="font-semibold text-blue-300">
                          Startup, Enterprise & Agency
                        </span>{' '}
                        contexts plus (
                        <span className="font-semibold text-blue-300">Junior, Mid & Senior</span>)
                        role analysis with{' '}
                        <a
                          href="/pricing"
                          className="font-semibold text-blue-400 underline hover:text-blue-300"
                        >
                          Starter ($49/month)
                        </a>
                      </div>
                    </div>
                  </AlertDescription>
                </Alert>
              )}

              {/* Role Level Selection - Only for PAID tiers */}
              {!isFreeTier && (
                <div className="space-y-3">
                  <label className="flex items-center gap-2 font-medium text-gray-300 text-sm">
                    <Users className="h-4 w-4 text-purple-400" />
                    Experience Level
                  </label>
                  <div className="grid gap-3 sm:grid-cols-3">
                    {ROLE_OPTIONS.map((option, index) => {
                      const Icon = option.icon;
                      const isSelected = role === option.value;
                      return (
                        <label
                          key={option.value}
                          className={`group relative flex cursor-pointer overflow-hidden rounded-xl border-2 p-4 transition-all duration-300 hover:scale-[1.02] ${
                            isSelected
                              ? `${option.borderColor} bg-gradient-to-br ${option.bgGradient} shadow-lg`
                              : 'border-white/[0.09] bg-white/[0.03] hover:border-white/[0.15] hover:bg-white/[0.06]'
                          }`}
                          style={{
                            animationDelay: `${index * 50}ms`,
                          }}
                        >
                          {/* Animated gradient overlay */}
                          {isSelected && (
                            <div
                              className={`absolute inset-0 bg-gradient-to-br ${option.gradient} animate-pulse opacity-10`}
                            />
                          )}

                          <input
                            type="radio"
                            name="role"
                            value={option.value}
                            checked={isSelected}
                            onChange={(e) => setRole(e.target.value)}
                            className="sr-only"
                          />
                          <div className="relative flex items-start gap-3">
                            <div
                              className={`rounded-lg p-2 transition-all duration-300 ${
                                isSelected
                                  ? `bg-gradient-to-br ${option.gradient} text-white shadow-md group-hover:shadow-lg`
                                  : 'bg-white/[0.06] text-gray-400 group-hover:bg-white/[0.09] group-hover:text-gray-300'
                              }`}
                            >
                              <Icon className="h-5 w-5" />
                            </div>
                            <div className="flex-1">
                              <p
                                className={`font-medium transition-colors ${
                                  isSelected
                                    ? 'text-gray-100'
                                    : 'text-gray-200 group-hover:text-gray-100'
                                }`}
                              >
                                {option.label}
                              </p>
                              <p className="mt-1 text-gray-400 text-xs">{option.description}</p>
                            </div>
                            {isSelected && (
                              <CheckCircle className="fade-in absolute top-2 right-2 h-4 w-4 animate-in text-green-400 duration-300" />
                            )}
                          </div>
                        </label>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Context Tips */}
              <div className="space-y-2">
                <Alert className="border-purple-500/20 bg-gradient-to-r from-purple-900/10 to-blue-900/10 p-6 backdrop-blur-sm">
                  <AlertDescription>
                    <div className="mb-4 flex items-center gap-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-purple-600 to-blue-600">
                        <Zap className="h-4 w-4 text-white" />
                      </div>
                      <p className="font-medium text-gray-100">
                        Pro Tip: Context helps focus the analysis
                      </p>
                    </div>
                    <div className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
                      <div className="flex items-center gap-2">
                        <Rocket className="h-4 w-4 flex-shrink-0 text-purple-400" />
                        <div>
                          <strong className="text-purple-300">Startup:</strong>
                          <span className="ml-1 text-gray-400">Fast iteration & adaptability</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Building2 className="h-4 w-4 flex-shrink-0 text-blue-400" />
                        <div>
                          <strong className="text-blue-300">Enterprise:</strong>
                          <span className="ml-1 text-gray-400">Architecture & scalability</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Briefcase className="h-4 w-4 flex-shrink-0 text-orange-400" />
                        <div>
                          <strong className="text-orange-300">Agency:</strong>
                          <span className="ml-1 text-gray-400">
                            Project diversity & reusability
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Users className="h-4 w-4 flex-shrink-0 text-green-400" />
                        <div>
                          <strong className="text-green-300">Open Source:</strong>
                          <span className="ml-1 text-gray-400">Community engagement</span>
                        </div>
                      </div>
                    </div>
                  </AlertDescription>
                </Alert>
              </div>

              {/* Usage Information - only show if user exists and has a plan */}
              {user && user.subscription_plan && (
                <Alert className="border-purple-500/20 bg-purple-900/10">
                  <AlertDescription className="text-gray-300 text-sm">
                    {user.subscription_plan === 'free' && (
                      <span>Free Plan: 10 analyses per month</span>
                    )}
                    {user.subscription_plan === 'starter' && (
                      <span>Starter Plan: 100 analyses per month</span>
                    )}
                    {user.subscription_plan === 'growth' && (
                      <span>Growth Plan: 200 analyses per month</span>
                    )}
                    {user.subscription_plan === 'scale' && (
                      <span>Scale Plan: 1000 analyses per month</span>
                    )}
                    {user.subscription_plan === 'scale_plus' && (
                      <span>Scale+ Plan: 3000 analyses per month</span>
                    )}
                  </AlertDescription>
                </Alert>
              )}

              {/* Analysis Disclaimer */}
              <Alert className="border-amber-500/20 bg-amber-500/10">
                <AlertCircle className="h-4 w-4 text-amber-500" />
                <AlertDescription className="text-amber-200">
                  <strong>Note:</strong> Repository analysis cannot be cancelled once started. The
                  process typically takes 2-4 minutes to complete.
                </AlertDescription>
              </Alert>

              {/* Submit Button */}
              <ExiqusButton
                type="submit"
                size="lg"
                disabled={isAnalyzing || !repoUrl}
                className="group relative flex h-14 w-full items-center justify-center overflow-hidden"
              >
                <div className="absolute inset-0 bg-gradient-to-r from-purple-600 to-blue-600 opacity-0 transition-opacity duration-500 group-hover:opacity-100" />
                <span className="relative flex items-center">
                  {isAnalyzing ? (
                    <>
                      <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                      <span className="font-medium text-base">Discovering Evidence...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="mr-2 h-5 w-5 group-hover:animate-pulse" />
                      <span className="font-medium text-base">Analyse Repository</span>
                      <ArrowRight className="ml-2 h-5 w-5 -translate-x-2 opacity-0 transition-all duration-300 group-hover:translate-x-0 group-hover:opacity-100" />
                    </>
                  )}
                </span>
              </ExiqusButton>
            </form>
          </ExiqusCard>

          {/* Analysis Features */}
          <div className="grid gap-4 md:grid-cols-3">
            {/* Deep Analysis Card */}
            <ExiqusCard
              className="group relative border-purple-500/20 bg-gradient-to-br from-purple-900/10 via-transparent to-transparent p-6 transition-all hover:border-purple-500/40"
              glow="purple"
            >
              <div className="absolute top-0 right-0 h-32 w-32 translate-x-16 -translate-y-16 rounded-full bg-purple-500/10 blur-3xl transition-colors group-hover:bg-purple-500/20" />
              <div className="relative space-y-3">
                <div className="flex items-start gap-3">
                  <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-purple-600 to-purple-400 shadow-lg shadow-purple-500/20 transition-shadow group-hover:shadow-purple-500/40">
                    <Search className="h-5 w-5 text-white" />
                  </div>
                  <div className="flex-1">
                    <p className="mb-2 font-semibold text-gray-100 text-lg">Deep Analysis</p>
                    <div className="space-y-2 text-gray-400 text-sm">
                      <div className="flex items-center gap-2">
                        <Code2 className="h-3 w-3 text-purple-400" />
                        <span>Examines commit history & patterns</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Layers className="h-3 w-3 text-purple-400" />
                        <span>Analyses code structure & architecture</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Shield className="h-3 w-3 text-purple-400" />
                        <span>Identifies testing & quality practices</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </ExiqusCard>

            {/* Evidence-Based Card */}
            <ExiqusCard
              className="group relative border-blue-500/20 bg-gradient-to-br from-blue-900/10 via-transparent to-transparent p-6 transition-all hover:border-blue-500/40"
              glow="blue"
            >
              <div className="absolute top-0 right-0 h-32 w-32 translate-x-16 -translate-y-16 rounded-full bg-blue-500/10 blur-3xl transition-colors group-hover:bg-blue-500/20" />
              <div className="relative space-y-3">
                <div className="flex items-start gap-3">
                  <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-blue-600 to-cyan-400 shadow-blue-500/20 shadow-lg transition-shadow group-hover:shadow-blue-500/40">
                    <TrendingUp className="h-5 w-5 text-white" />
                  </div>
                  <div className="flex-1">
                    <p className="mb-2 font-semibold text-gray-100 text-lg">Evidence-Based</p>
                    <div className="space-y-2 text-gray-400 text-sm">
                      <div className="flex items-center gap-2">
                        <XCircle className="h-3 w-3 text-blue-400" />
                        <span>No subjective judgments or scores</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <CheckCircle className="h-3 w-3 text-blue-400" />
                        <span>Factual code metrics & observations</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Eye className="h-3 w-3 text-blue-400" />
                        <span>Transparent reasoning & evidence</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </ExiqusCard>

            {/* All Repositories Card */}
            <ExiqusCard
              className="group relative border-green-500/20 bg-gradient-to-br from-green-900/10 via-transparent to-transparent p-6 transition-all hover:border-green-500/40"
              glow="green"
            >
              <div className="absolute top-0 right-0 h-32 w-32 translate-x-16 -translate-y-16 rounded-full bg-green-500/10 blur-3xl transition-colors group-hover:bg-green-500/20" />
              <div className="relative space-y-3">
                <div className="flex items-start gap-3">
                  <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-green-600 to-emerald-400 shadow-green-500/20 shadow-lg transition-shadow group-hover:shadow-green-500/40">
                    <GitBranch className="h-5 w-5 text-white" />
                  </div>
                  <div className="flex-1">
                    <p className="mb-2 font-semibold text-gray-100 text-lg">Repository Limits</p>
                    <div className="space-y-2 text-gray-400 text-sm">
                      <div className="flex items-center gap-2">
                        <Github className="h-3 w-3 text-green-400" />
                        <span>Any public GitHub repository</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Sparkles className="h-3 w-3 text-green-400" />
                        <span>
                          {(() => {
                            const plan = user?.subscription_plan?.toLowerCase();
                            if (plan === 'scale_plus') {
                              return 'Up to 10GB, max 10K files per repo';
                            } else if (plan === 'scale' || plan === 'enterprise') {
                              return 'Up to 5GB, max 10K files per repo';
                            } else if (plan === 'growth' || plan === 'professional') {
                              return 'Up to 3GB, max 10K files per repo';
                            }
                            return 'From scripts to standard projects';
                          })()}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </ExiqusCard>
          </div>

          {/* Example Repositories */}
          <ExiqusCard className="p-6" glow="subtle">
            <div className="mb-4">
              <h3 className="font-semibold text-gray-100 text-lg">
                Try These Popular Repositories
              </h3>
              <p className="text-gray-400 text-sm">Click any repository to analyse it instantly</p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {[
                // Small complexity repos
                {
                  name: 'expressjs/express',
                  description: 'Fast, unopinionated, minimalist web framework',
                  complexity: 'Small',
                },
                {
                  name: 'sindresorhus/awesome',
                  description: 'Awesome lists about all kinds of topics',
                  complexity: 'Small',
                },
                {
                  name: 'axios/axios',
                  description: 'Promise based HTTP client',
                  complexity: 'Small',
                },
                // Medium complexity repos
                {
                  name: 'facebook/react',
                  description: 'A declarative UI library for building user interfaces',
                  complexity: 'Medium',
                },
                {
                  name: 'vercel/next.js',
                  description: 'The React Framework for Production',
                  complexity: 'Medium',
                },
                {
                  name: 'nestjs/nest',
                  description: 'A progressive Node.js framework',
                  complexity: 'Medium',
                },
                {
                  name: 'prisma/prisma',
                  description: 'Next-generation ORM for Node.js & TypeScript',
                  complexity: 'Medium',
                },
                {
                  name: 'strapi/strapi',
                  description: 'Open source Node.js Headless CMS',
                  complexity: 'Medium',
                },
                {
                  name: 'nuxt/nuxt',
                  description: 'The Intuitive Vue Framework',
                  complexity: 'Medium',
                },
              ].map((repo) => (
                <button
                  key={repo.name}
                  type="button"
                  onClick={() => {
                    const url = `https://github.com/${repo.name}`;
                    setRepoUrl(url);
                    setValidationError('');
                    // Also validate the URL to show the checkmark
                    validateGitHubUrl(url);
                  }}
                  className="group flex items-start gap-3 rounded-lg border border-white/[0.09] bg-white/[0.03] p-3 text-left transition-all hover:scale-[1.02] hover:border-purple-500 hover:bg-white/[0.06]"
                >
                  <GitBranch className="mt-0.5 h-5 w-5 text-gray-400 group-hover:text-purple-400" />
                  <div className="flex-1">
                    <p className="font-medium text-gray-100 group-hover:text-purple-400">
                      {repo.name}
                    </p>
                    <p className="text-gray-400 text-sm">{repo.description}</p>
                    {repo.complexity && (
                      <span
                        className={`mt-1 inline-block rounded-full px-2 py-0.5 text-xs ${
                          repo.complexity === 'Small'
                            ? 'bg-green-900/20 text-green-400'
                            : repo.complexity === 'Medium'
                              ? 'bg-yellow-900/20 text-yellow-400'
                              : 'bg-red-900/20 text-red-400'
                        }`}
                      >
                        {repo.complexity} complexity
                      </span>
                    )}
                  </div>
                  <ExternalLink className="ml-auto h-4 w-4 text-gray-400 opacity-0 transition-opacity group-hover:text-purple-400 group-hover:opacity-100" />
                </button>
              ))}
            </div>
          </ExiqusCard>
        </div>
      </div>
    </div>
  );
}
