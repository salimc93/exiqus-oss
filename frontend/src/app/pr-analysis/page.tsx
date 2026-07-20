// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import {
  Activity,
  AlertCircle,
  ArrowRight,
  Award,
  Briefcase,
  Building2,
  CheckCircle,
  Clock,
  Code2,
  Eye,
  FolderGit2,
  GitBranch,
  GitMerge,
  GitPullRequest,
  Layers,
  Loader2,
  Lock,
  MessageCircle,
  Rocket,
  Search,
  Shield,
  Sparkles,
  Star,
  Target,
  TrendingUp,
  UserCheck,
  Users,
  XCircle,
} from 'lucide-react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import { toast } from 'sonner';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { ContextLockIndicator } from '@/components/ui/context-lock-indicator';
import { ExiqusButton, ExiqusCard, GradientText } from '@/components/ui/exiqus-components';
import { UpgradePrompt } from '@/components/ui/upgrade-prompt';
import { useAuth } from '@/contexts/auth-context';
import { useAuthGuard } from '@/hooks/use-auth-guard';
import { useCandidateContext } from '@/hooks/use-candidate-context';
import { api } from '@/lib/api-client';

const CONTEXT_OPTIONS = [
  {
    value: 'startup',
    label: 'Startup Context',
    icon: Rocket,
    description: 'Fast iteration, ownership, adaptability',
    gradient: 'from-teal-600 to-cyan-600',
    bgGradient: 'from-teal-900/20 to-cyan-900/20',
    borderColor: 'border-teal-500',
  },
  {
    value: 'enterprise',
    label: 'Enterprise Context',
    icon: Building2,
    description: 'Process adherence, collaboration, scalability',
    gradient: 'from-cyan-600 to-blue-600',
    bgGradient: 'from-cyan-900/20 to-blue-900/20',
    borderColor: 'border-cyan-500',
  },
  {
    value: 'agency',
    label: 'Agency Context',
    icon: Briefcase,
    description: 'Client communication, delivery focus',
    gradient: 'from-teal-600 to-emerald-600',
    bgGradient: 'from-teal-900/20 to-emerald-900/20',
    borderColor: 'border-teal-500',
  },
  {
    value: 'open_source',
    label: 'Open Source',
    icon: Users,
    description: 'Community engagement, documentation',
    gradient: 'from-emerald-600 to-green-600',
    bgGradient: 'from-emerald-900/20 to-green-900/20',
    borderColor: 'border-emerald-500',
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

export default function PRAnalysisPage() {
  const { isLoading, showUnauthorized, UnauthorizedComponent } = useAuthGuard();
  const searchParams = useSearchParams();
  const [githubUsername, setGithubUsername] = useState('');
  const [context, setContext] = useState('startup');
  const [role, setRole] = useState('mid');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [validationError, setValidationError] = useState('');
  const [isValidUsername, setIsValidUsername] = useState(false);
  const [analyzingUser, setAnalyzingUser] = useState<string>('');
  const [loadingStage, setLoadingStage] = useState<
    'fetching' | 'analyzing' | 'generating' | 'finalizing'
  >('fetching');
  const [prCount, setPrCount] = useState<number>(0);
  const [loadingMessage, setLoadingMessage] = useState<string>('');
  const [showZeroPRModal, setShowZeroPRModal] = useState(false);
  const [zeroPRUsername, setZeroPRUsername] = useState('');
  const router = useRouter();
  const { user, refreshUser } = useAuth();

  // Fetch locked context for the candidate
  const { lockedContext, refetch: refetchContext } = useCandidateContext(
    isValidUsername ? githubUsername : null
  );

  // Auto-fill role and context when locked context is detected
  useEffect(() => {
    if (lockedContext) {
      setRole(lockedContext.role);
      setContext(lockedContext.organization_context);
    }
  }, [lockedContext]);

  // Disable role and context selectors when locked
  const isDisabled = !!lockedContext;

  // Handle context reset
  const handleContextReset = () => {
    // Refetch to clear the locked context state
    refetchContext();
  };

  // Check for username and returnTo query parameters
  useEffect(() => {
    const username = searchParams.get('username');
    if (username) {
      setGithubUsername(username);
      validateGitHubUsername(username);
    }
  }, [searchParams]);

  const validateGitHubUsername = (username: string): boolean => {
    const trimmedUsername = username.trim();

    if (!trimmedUsername) {
      setValidationError('Please enter a GitHub username');
      setIsValidUsername(false);
      return false;
    }

    // GitHub username validation (39 chars max, alphanumeric and hyphens)
    const usernameRegex = /^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$/;
    if (!usernameRegex.test(trimmedUsername)) {
      setValidationError('Invalid GitHub username format');
      setIsValidUsername(false);
      return false;
    }

    setValidationError('');
    setIsValidUsername(true);
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Check if user has paid tier access
    if (user?.subscription_plan === 'free') {
      toast.error('PR Analysis is available on paid plans. Please upgrade your plan.');
      router.push('/pricing');
      return;
    }

    if (!validateGitHubUsername(githubUsername)) {
      return;
    }

    setIsAnalyzing(true);
    setLoadingStage('fetching');
    setAnalyzingUser(githubUsername);
    setLoadingMessage('Connecting to GitHub API...');
    setPrCount(0);

    // Use setTimeout to allow React to render the loading screen before making API call
    setTimeout(async () => {
      try {
        const requestData = {
          github_username: githubUsername.trim(),
          context: context as 'startup' | 'enterprise' | 'agency' | 'open_source',
          role: role as 'junior' | 'mid' | 'senior',
          force_refresh: false,
        };

        // Call the PR analysis API
        const response = await api.analyzePRs(requestData);

        // Extract the analysis ID from the response
        const analysisId = response.data.id || response.data.analysis_id;
        const status = response.data.status;

        if (!analysisId) {
          toast.error(
            'Analysis started but no ID received. Please check your PR analysis history.'
          );
          setIsAnalyzing(false);
          return;
        }

        // If status is pending or processing, poll until complete
        if (status === 'pending' || status === 'processing') {
          // Fake UI timers for smooth progress
          const stageTimer = setTimeout(() => setLoadingStage('analyzing'), 15000);
          const generateTimer = setTimeout(() => setLoadingStage('generating'), 45000);
          const finalTimer = setTimeout(() => setLoadingStage('finalizing'), 75000);

          // Flag to prevent multiple redirects/toasts
          let hasRedirected = false;

          // Poll every 30 seconds to check if analysis is complete
          const pollInterval = setInterval(async () => {
            try {
              const pollResponse = await api.getPRAnalysis(analysisId);
              const pollStatus = pollResponse.data.status;

              // Only redirect when actually completed or failed
              if (
                (pollStatus === 'completed' || pollStatus === 'failed' || !pollStatus) &&
                !hasRedirected
              ) {
                hasRedirected = true;
                clearInterval(pollInterval);
                clearTimeout(stageTimer);
                clearTimeout(generateTimer);
                clearTimeout(finalTimer);

                // Refresh user data
                try {
                  await refreshUser();
                } catch {
                  // Silently fail
                }

                if (pollStatus === 'failed') {
                  toast.error('Analysis failed. Please try again.');
                  setIsAnalyzing(false);
                  return;
                }

                // Check if this is a 0 PR analysis
                if (pollResponse.data.total_prs_analyzed === 0) {
                  setZeroPRUsername(pollResponse.data.username || githubUsername);
                  setShowZeroPRModal(true);
                  setIsAnalyzing(false);
                  return;
                }

                toast.success('PR analysis completed successfully!');

                // Check if we should return to candidate hub
                const returnTo = searchParams.get('returnTo');
                if (returnTo === 'candidate-hub') {
                  const username = searchParams.get('username') || githubUsername;
                  router.push(`/candidate-hub/${username}`);
                } else {
                  router.push(`/pr-analyses/${analysisId}`);
                }
              }
            } catch (pollError) {
              console.error('Polling error:', pollError);
            }
          }, 30000); // Poll every 30 seconds - balances UX with server load

          // Don't reset isAnalyzing - let polling handle the state
          return;
        } else {
          // Analysis completed immediately (from cache or very fast)
          // Show UI for smooth UX even though it's instant
          setTimeout(() => setLoadingStage('analyzing'), 1000);
          setTimeout(() => setLoadingStage('generating'), 2000);
          setTimeout(() => setLoadingStage('finalizing'), 3000);

          // Wait 5 seconds before redirecting to show the UI
          await new Promise((resolve) => setTimeout(resolve, 5000));

          // Refresh user data
          try {
            await refreshUser();
          } catch {
            // Silently fail
          }

          // Check if this is a 0 PR analysis
          if (response.data.total_prs_analyzed === 0) {
            setZeroPRUsername(response.data.username || githubUsername);
            setShowZeroPRModal(true);
            return;
          }

          toast.success('PR analysis completed successfully!');

          // Check if we should return to candidate hub
          const returnTo = searchParams.get('returnTo');
          if (returnTo === 'candidate-hub') {
            const username = searchParams.get('username') || githubUsername;
            router.push(`/candidate-hub/${username}`);
          } else {
            // Redirect to the PR analysis results page
            router.push(`/pr-analyses/${analysisId}`);
          }
        }
      } catch (error: unknown) {
        console.error('PR Analysis failed:', error);

        const errorResponse = error as {
          response?: { status?: number; data?: { detail?: string } };
        };

        // Handle specific error cases
        if (errorResponse.response?.status === 429) {
          const errorDetail = errorResponse.response.data?.detail || '';
          if (errorDetail.includes('hourly')) {
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
                  Hourly Rate Limit Reached
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
                <div className="mt-2 text-gray-400 text-xs">
                  Take a break and come back soon! ☕
                </div>
              </div>,
              { duration: 8000 }
            );
          } else {
            toast.error('Monthly PR analysis quota exceeded. Please wait for next billing cycle.');
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
              upgrade_message?: string;
            };

            // Check if this is a candidate insight quota error
            if (quotaError.error?.includes('candidate assessment')) {
              const currentUsage = quotaError.current_usage || 0;
              const limit = quotaError.limit || 0;

              toast.error(
                <div className="space-y-2">
                  <div className="font-semibold">Candidate Insight Quota Reached</div>
                  <div className="text-sm">
                    You&apos;ve used all {limit} candidate insights this month ({currentUsage}/
                    {limit}).
                  </div>
                  <div className="mt-2 text-gray-400 text-xs">
                    <strong>What&apos;s a Candidate Assessment?</strong>
                    <br />
                    Analyzing a GitHub username (Portfolio + PR combined) = 1 insight.
                    <br />
                    {quotaError.upgrade_message}
                  </div>
                </div>,
                {
                  duration: 10000,
                }
              );
            } else {
              // Generic quota error
              toast.error(
                quotaError.message || 'You have reached your quota. Please upgrade your plan.'
              );
            }
          } else {
            // String error - legacy handling
            toast.error('PR Analysis is only available on paid plans.');
          }
        } else if (errorResponse.response?.status === 404) {
          toast.error('GitHub user not found. Please check the username.');
        } else if (errorResponse.response?.status === 400) {
          const errorDetail = errorResponse.response.data?.detail;
          toast.error(errorDetail || 'Invalid request. Please check your input.');
        } else {
          toast.error('Failed to analyse pull requests. Please try again.');
        }

        // Only reset state on error - polling will handle success case
        setIsAnalyzing(false);
        setAnalyzingUser('');
        setLoadingStage('fetching');
      }
    }, 0);
  };

  const handleUsernameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const username = e.target.value.trim(); // Auto-trim to prevent trailing/leading spaces
    setGithubUsername(username);

    // Clear validation error when user starts typing
    if (validationError) {
      setValidationError('');
    }

    // Validate and update the checkmark/X display
    if (username) {
      validateGitHubUsername(username);
    } else {
      setIsValidUsername(false);
    }
  };

  // Show loading state
  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="mb-4 inline-flex h-16 w-16 items-center justify-center">
            <div className="h-12 w-12 animate-spin rounded-full border-4 border-teal-600 border-t-transparent" />
          </div>
          <p className="text-gray-400">Preparing PR analysis tools...</p>
        </div>
      </div>
    );
  }

  // Show unauthorized component
  if (showUnauthorized && UnauthorizedComponent) {
    return <UnauthorizedComponent />;
  }

  // Show upgrade prompt for FREE users (PR Analysis available on all paid tiers)
  if (user && user.subscription_plan === 'free') {
    return (
      <UpgradePrompt
        feature="PR Analysis"
        requiredTier="Starter"
        description="Analyze developer pull request contributions to assess collaboration patterns, technical expertise, and communication skills across their PR history."
      />
    );
  }

  // Check for paid tier access (all paid tiers have access)
  const hasAccess = user?.subscription_plan && user.subscription_plan !== 'free';

  return (
    <div className="min-h-screen bg-[#0A0A0A]">
      {/* Animated gradient background - Teal/Cyan theme */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 h-80 w-80 animate-pulse rounded-full bg-teal-500/20 blur-3xl"></div>
        <div className="absolute -bottom-40 -left-40 h-80 w-80 animate-pulse rounded-full bg-cyan-500/20 blur-3xl delay-1000"></div>
        <div className="absolute top-1/2 left-1/2 h-80 w-80 -translate-x-1/2 -translate-y-1/2 animate-pulse rounded-full bg-gradient-to-r from-teal-500/10 to-cyan-500/10 blur-3xl delay-500"></div>
      </div>

      {/* Full-screen loading overlay */}
      {isAnalyzing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
          <ExiqusCard className="max-w-md p-8 text-center" glow="green">
            <div className="mb-6">
              <Loader2 className="mx-auto h-16 w-16 animate-spin text-teal-400" />
            </div>
            <h2 className="mb-4 font-semibold text-2xl">
              <GradientText className="bg-gradient-to-r from-teal-400 to-cyan-400">
                Analysing Pull Requests
              </GradientText>
            </h2>
            <p className="mb-2 font-medium text-gray-300 text-lg">@{analyzingUser}</p>

            {/* Dynamic message based on stage */}
            <p className="mb-6 text-gray-400">
              {loadingStage === 'fetching' && 'Fetching pull request data from GitHub...'}
              {loadingStage === 'analyzing' &&
                'Analysing contribution patterns and collaboration style...'}
              {loadingStage === 'generating' &&
                'Generating AI-powered insights and interview questions...'}
              {loadingStage === 'finalizing' && 'Preparing comprehensive insight report...'}
            </p>

            {/* Show PR count if available */}
            {prCount > 0 && (
              <div className="mb-4 rounded-lg border border-teal-600/30 bg-teal-900/20 px-4 py-3">
                <p className="text-sm text-teal-400">
                  Analysing {prCount} pull request{prCount !== 1 ? 's' : ''}
                </p>
              </div>
            )}

            {/* Additional loading message if set */}
            {loadingMessage && <p className="mb-4 text-gray-500 text-sm">{loadingMessage}</p>}

            <div className="space-y-3 text-gray-500 text-sm">
              <div className="flex items-center justify-center gap-2">
                {loadingStage === 'fetching' ? (
                  <Loader2 className="h-4 w-4 animate-spin text-teal-400" />
                ) : (
                  <CheckCircle className="h-4 w-4 text-green-500" />
                )}
                <span className={loadingStage === 'fetching' ? 'text-gray-300' : ''}>
                  GitHub API Connection
                </span>
              </div>

              <div className="flex items-center justify-center gap-2">
                {loadingStage === 'analyzing' ? (
                  <Loader2 className="h-4 w-4 animate-spin text-teal-400" />
                ) : loadingStage === 'generating' || loadingStage === 'finalizing' ? (
                  <CheckCircle className="h-4 w-4 text-green-500" />
                ) : (
                  <Clock className="h-4 w-4 text-gray-600" />
                )}
                <span className={loadingStage === 'analyzing' ? 'text-gray-300' : ''}>
                  Pattern Analysis
                </span>
              </div>

              <div className="flex items-center justify-center gap-2">
                {loadingStage === 'generating' ? (
                  <Loader2 className="h-4 w-4 animate-spin text-teal-400" />
                ) : loadingStage === 'finalizing' ? (
                  <CheckCircle className="h-4 w-4 text-green-500" />
                ) : (
                  <Clock className="h-4 w-4 text-gray-600" />
                )}
                <span className={loadingStage === 'generating' ? 'text-gray-300' : ''}>
                  AI Analysis & Report Generation
                </span>
              </div>

              <div className="flex items-center justify-center gap-2">
                {loadingStage === 'finalizing' ? (
                  <Loader2 className="h-4 w-4 animate-spin text-teal-400" />
                ) : (
                  <Clock className="h-4 w-4 text-gray-600" />
                )}
                <span className={loadingStage === 'finalizing' ? 'text-gray-300' : ''}>
                  Finalizing
                </span>
              </div>
            </div>

            {/* Informative note */}
            <p className="mt-6 text-gray-600 text-xs">
              Analysis time varies based on PR history size and complexity
            </p>
          </ExiqusCard>
        </div>
      )}

      <div className="container relative mx-auto max-w-6xl px-4 py-8">
        <div className="space-y-8">
          {/* Header */}
          <div className="relative text-center">
            <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-teal-900/20 to-cyan-900/20 px-4 py-2 font-medium text-sm">
              <Star className="h-4 w-4 text-teal-400" />
              BETA
            </div>
            <h1 className="mb-4 font-bold text-4xl tracking-tight md:text-5xl">
              <GradientText className="bg-gradient-to-r from-teal-400 to-cyan-400">
                Analyse Developer Pull Requests
              </GradientText>
            </h1>
            <p className="mx-auto max-w-2xl text-gray-400 text-xl">
              Discover evidence-based insights about developer contributions, collaboration
              patterns, and technical expertise
            </p>
          </div>

          {/* Main Content - Available to all paid tiers */}
          {hasAccess && (
            <>
              {/* Main Analysis Form */}
              <ExiqusCard className="p-8" glow="green">
                <div className="mb-6">
                  <h2 className="flex items-center gap-2 font-semibold text-2xl text-gray-100">
                    <GitPullRequest className="h-6 w-6 text-teal-400" />
                    PR Analysis
                  </h2>
                  <p className="mt-2 text-gray-400">
                    Enter a GitHub username to analyse their pull request contributions (up to 1,500
                    PRs)
                  </p>
                </div>
                <form onSubmit={handleSubmit} className="space-y-6">
                  {/* GitHub Username Input */}
                  <div className="space-y-2">
                    <label className="flex items-center gap-2 font-medium text-sm">
                      <GitBranch className="h-4 w-4 text-teal-400" />
                      GitHub Username
                    </label>
                    <div className="group relative">
                      <div className="absolute inset-0 rounded-lg bg-gradient-to-r from-teal-600 to-cyan-600 opacity-0 blur transition-opacity duration-500 group-focus-within:opacity-30 group-hover:opacity-20"></div>
                      <div className="relative">
                        <GitBranch className="absolute top-1/2 left-4 h-5 w-5 -translate-y-1/2 text-gray-500 transition-colors group-focus-within:text-teal-400" />
                        <input
                          type="text"
                          placeholder="octocat"
                          value={githubUsername}
                          onChange={handleUsernameChange}
                          disabled={isAnalyzing}
                          className={`h-14 w-full rounded-lg border px-12 py-2 pr-12 text-lg transition-all duration-300 ${validationError ? 'border-red-500 bg-red-500/5' : 'border-white/[0.09] bg-white/[0.06] hover:bg-white/[0.08] focus:bg-white/[0.09]'} text-gray-100 outline-none placeholder:text-gray-500 focus:border-teal-500 disabled:opacity-50 ${isValidUsername ? 'border-green-500/50' : ''}`}
                        />
                        {isValidUsername && (
                          <CheckCircle className="fade-in absolute top-1/2 right-4 h-5 w-5 -translate-y-1/2 animate-in text-green-500 duration-300" />
                        )}
                        {githubUsername && !isValidUsername && (
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
                  </div>

                  {/* Context Lock Indicator */}
                  {isValidUsername && lockedContext && (
                    <ContextLockIndicator
                      username={githubUsername}
                      currentRole={role}
                      currentContext={context}
                      lockedRole={lockedContext.role}
                      lockedContext={lockedContext.organization_context}
                      isLocked={!!lockedContext}
                      onContextReset={handleContextReset}
                      className="fade-in slide-in-from-top-4 animate-in duration-500"
                    />
                  )}

                  {/* Analysis Context Selection */}
                  <div className="space-y-3">
                    <label className="flex items-center gap-2 font-medium text-gray-300 text-sm">
                      <Layers className="h-4 w-4 text-teal-400" />
                      Hiring Context{' '}
                      {isDisabled && (
                        <span className="flex items-center gap-1 text-amber-400 text-xs">
                          <Lock className="h-3 w-3" />
                          (Locked)
                        </span>
                      )}
                    </label>
                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                      {CONTEXT_OPTIONS.map((option, index) => {
                        const Icon = option.icon;
                        const isSelected = context === option.value;
                        return (
                          <label
                            key={option.value}
                            className={`group relative flex overflow-hidden rounded-xl border-2 p-4 transition-all duration-300 ${
                              isDisabled
                                ? 'cursor-not-allowed opacity-60'
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
                              onChange={(e) => setContext(e.target.value)}
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

                  {/* Role Level Selection */}
                  <div className="space-y-3">
                    <label className="flex items-center gap-2 font-medium text-gray-300 text-sm">
                      <Users className="h-4 w-4 text-teal-400" />
                      Experience Level{' '}
                      {isDisabled && (
                        <span className="flex items-center gap-1 text-amber-400 text-xs">
                          <Lock className="h-3 w-3" />
                          (Locked)
                        </span>
                      )}
                    </label>
                    <div className="grid gap-3 sm:grid-cols-3">
                      {ROLE_OPTIONS.map((option, index) => {
                        const Icon = option.icon;
                        const isSelected = role === option.value;
                        return (
                          <label
                            key={option.value}
                            className={`group relative flex overflow-hidden rounded-xl border-2 p-4 transition-all duration-300 ${
                              isDisabled
                                ? 'cursor-not-allowed opacity-60'
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
                              name="role"
                              value={option.value}
                              checked={isSelected}
                              onChange={(e) => setRole(e.target.value)}
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

                  {/* Rate Limits Information */}
                  <Alert className="border-teal-500/20 bg-teal-900/10">
                    <AlertDescription className="text-gray-300 text-sm">
                      <div className="flex items-center gap-2">
                        <Clock className="h-4 w-4 text-teal-400" />
                        <span>
                          Rate Limits: {user?.subscription_plan === 'starter' && '10 analyses/hour'}
                          {user?.subscription_plan === 'growth' && '15 analyses/hour'}
                          {user?.subscription_plan === 'scale' && '20 analyses/hour'}
                          {user?.subscription_plan === 'scale_plus' && '25 analyses/hour'}
                          {!user?.subscription_plan && '20 analyses/hour'}
                        </span>
                      </div>
                    </AlertDescription>
                  </Alert>

                  {/* Beta Notice */}
                  <Alert className="border-amber-500/20 bg-amber-500/10">
                    <AlertCircle className="h-4 w-4 text-amber-500" />
                    <AlertDescription className="text-amber-200">
                      <strong>Beta Feature:</strong> PR Analysis is in active beta. We&apos;re
                      continuously improving based on real-world usage. You may encounter edge cases
                      or unexpected results—if you do, please report them so we can refine the
                      analysis.
                    </AlertDescription>
                  </Alert>

                  {/* Submit Button */}
                  <ExiqusButton
                    type="submit"
                    size="lg"
                    disabled={isAnalyzing || !githubUsername}
                    className="group relative flex h-14 w-full items-center justify-center overflow-hidden bg-gradient-to-r from-teal-600 to-cyan-600"
                  >
                    <span className="relative flex items-center">
                      {isAnalyzing ? (
                        <>
                          <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                          <span className="font-medium text-base">Analysing PRs...</span>
                        </>
                      ) : (
                        <>
                          <GitPullRequest className="mr-2 h-5 w-5 group-hover:animate-pulse" />
                          <span className="font-medium text-base">Analyse Pull Requests</span>
                          <ArrowRight className="ml-2 h-5 w-5 -translate-x-2 opacity-0 transition-all duration-300 group-hover:translate-x-0 group-hover:opacity-100" />
                        </>
                      )}
                    </span>
                  </ExiqusButton>
                </form>
              </ExiqusCard>

              {/* Analysis Features */}
              <div className="grid gap-4 md:grid-cols-3">
                {/* PR Analysis Card */}
                <ExiqusCard
                  className="group relative border-teal-500/20 bg-gradient-to-br from-teal-900/10 via-transparent to-transparent p-6 transition-all hover:border-teal-500/40"
                  glow="green"
                >
                  <div className="absolute top-0 right-0 h-32 w-32 translate-x-16 -translate-y-16 rounded-full bg-teal-500/10 blur-3xl transition-colors group-hover:bg-teal-500/20" />
                  <div className="relative space-y-3">
                    <div className="flex items-start gap-3">
                      <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-teal-600 to-cyan-400 shadow-lg shadow-teal-500/20 transition-shadow group-hover:shadow-teal-500/40">
                        <GitMerge className="h-5 w-5 text-white" />
                      </div>
                      <div className="flex-1">
                        <p className="mb-2 font-semibold text-gray-100 text-lg">PR Patterns</p>
                        <div className="space-y-2 text-gray-400 text-sm">
                          <div className="flex items-center gap-2">
                            <Code2 className="h-3 w-3 text-teal-400" />
                            <span>Technical substance & quality</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <UserCheck className="h-3 w-3 text-teal-400" />
                            <span>Collaboration & review patterns</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <Activity className="h-3 w-3 text-teal-400" />
                            <span>Contribution consistency</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </ExiqusCard>

                {/* AI Insights Card */}
                <ExiqusCard
                  className="group relative border-cyan-500/20 bg-gradient-to-br from-cyan-900/10 via-transparent to-transparent p-6 transition-all hover:border-cyan-500/40"
                  glow="blue"
                >
                  <div className="absolute top-0 right-0 h-32 w-32 translate-x-16 -translate-y-16 rounded-full bg-cyan-500/10 blur-3xl transition-colors group-hover:bg-cyan-500/20" />
                  <div className="relative space-y-3">
                    <div className="flex items-start gap-3">
                      <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-600 to-blue-400 shadow-cyan-500/20 shadow-lg transition-shadow group-hover:shadow-cyan-500/40">
                        <TrendingUp className="h-5 w-5 text-white" />
                      </div>
                      <div className="flex-1">
                        <p className="mb-2 font-semibold text-gray-100 text-lg">AI Analysis</p>
                        <div className="space-y-2 text-gray-400 text-sm">
                          <div className="flex items-center gap-2">
                            <Sparkles className="h-3 w-3 text-cyan-400" />
                            <span>Interview questions generated</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <Shield className="h-3 w-3 text-cyan-400" />
                            <span>Key strengths identified</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <Eye className="h-3 w-3 text-cyan-400" />
                            <span>Areas to explore highlighted</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </ExiqusCard>

                {/* Context Alignment Card */}
                <ExiqusCard
                  className="group relative border-emerald-500/20 bg-gradient-to-br from-emerald-900/10 via-transparent to-transparent p-6 transition-all hover:border-emerald-500/40"
                  glow="green"
                >
                  <div className="absolute top-0 right-0 h-32 w-32 translate-x-16 -translate-y-16 rounded-full bg-emerald-500/10 blur-3xl transition-colors group-hover:bg-emerald-500/20" />
                  <div className="relative space-y-3">
                    <div className="flex items-start gap-3">
                      <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-600 to-green-400 shadow-emerald-500/20 shadow-lg transition-shadow group-hover:shadow-emerald-500/40">
                        <UserCheck className="h-5 w-5 text-white" />
                      </div>
                      <div className="flex-1">
                        <p className="mb-2 font-semibold text-gray-100 text-lg">Context Fit</p>
                        <div className="space-y-2 text-gray-400 text-sm">
                          <div className="flex items-center gap-2">
                            <Rocket className="h-3 w-3 text-emerald-400" />
                            <span>Startup: Ownership & velocity</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <Building2 className="h-3 w-3 text-emerald-400" />
                            <span>Enterprise: Process adherence</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <Users className="h-3 w-3 text-emerald-400" />
                            <span>Open Source: Community focus</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </ExiqusCard>
              </div>

              {/* Example Users */}
              <ExiqusCard className="p-6" glow="subtle">
                <div className="mb-4">
                  <h3 className="font-semibold text-gray-100 text-lg">
                    Try These Example Developers
                  </h3>
                  <p className="text-gray-400 text-sm">
                    Click any username to analyse their contributions
                  </p>
                </div>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {[
                    {
                      username: 'torvalds',
                      description: 'Linux kernel creator and maintainer',
                      activity: 'Very High',
                    },
                    {
                      username: 'kentcdodds',
                      description: 'React educator and Testing Library creator',
                      activity: 'High',
                    },
                    {
                      username: 'wesbos',
                      description: 'Web developer and educator',
                      activity: 'Medium',
                    },
                    {
                      username: 'addyosmani',
                      description: 'Chrome DevTools & web performance',
                      activity: 'High',
                    },
                    {
                      username: 'yyx990803',
                      description: 'Vue.js creator',
                      activity: 'High',
                    },
                    {
                      username: 'tj',
                      description: 'Express.js creator',
                      activity: 'Medium',
                    },
                  ].map((dev) => (
                    <button
                      key={dev.username}
                      type="button"
                      onClick={() => {
                        setGithubUsername(dev.username);
                        setValidationError('');
                        validateGitHubUsername(dev.username);
                      }}
                      className="group flex items-start gap-3 rounded-lg border border-white/[0.09] bg-white/[0.03] p-3 text-left transition-all hover:scale-[1.02] hover:border-teal-500 hover:bg-white/[0.06]"
                    >
                      <GitPullRequest className="mt-0.5 h-5 w-5 text-gray-400 group-hover:text-teal-400" />
                      <div className="flex-1">
                        <p className="font-medium text-gray-100 group-hover:text-teal-400">
                          @{dev.username}
                        </p>
                        <p className="text-gray-400 text-sm">{dev.description}</p>
                        {dev.activity && (
                          <span
                            className={`mt-1 inline-block rounded-full px-2 py-0.5 text-xs ${
                              dev.activity === 'Very High'
                                ? 'bg-teal-900/20 text-teal-400'
                                : dev.activity === 'High'
                                  ? 'bg-cyan-900/20 text-cyan-400'
                                  : 'bg-blue-900/20 text-blue-400'
                            }`}
                          >
                            {dev.activity} activity
                          </span>
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              </ExiqusCard>
            </>
          )}
        </div>
      </div>

      {/* Zero PR Modal Dialog */}
      {showZeroPRModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
          onClick={() => {
            setShowZeroPRModal(false);
            setZeroPRUsername('');
          }}
        >
          <ExiqusCard
            className="max-w-2xl border-teal-500/20 p-12 text-center"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Icon */}
            <div className="mb-6 flex justify-center">
              <div className="rounded-full border border-teal-500/30 bg-gradient-to-br from-teal-900/40 to-cyan-900/40 p-4">
                <GitPullRequest className="h-16 w-16 text-teal-400" />
              </div>
            </div>

            {/* Title */}
            <h2 className="mb-4 font-bold text-3xl">
              <GradientText className="bg-gradient-to-r from-teal-400 to-cyan-400">
                No Pull Request Activity Found
              </GradientText>
            </h2>

            {/* User info */}
            <p className="mb-6 text-gray-300 text-xl">@{zeroPRUsername}</p>

            {/* Message */}
            <div className="mb-8 rounded-xl border border-teal-500/20 bg-gradient-to-r from-teal-950/30 to-cyan-950/30 p-6">
              <p className="mb-4 text-gray-300">
                This user has no public pull request activity on GitHub.
              </p>
              <p className="text-gray-400 text-sm">
                This could mean they work primarily in private repositories, contribute to other
                platforms, or their development work doesn&apos;t involve pull requests.
              </p>
            </div>

            {/* Suggestions */}
            <div className="mb-8">
              <h3 className="mb-4 font-semibold text-gray-200 text-lg">What to try next:</h3>
              <div className="grid gap-4 text-left">
                <div className="rounded-lg border border-purple-500/20 bg-gradient-to-r from-purple-900/20 to-transparent p-4">
                  <div className="flex items-start gap-3">
                    <FolderGit2 className="mt-0.5 h-5 w-5 flex-shrink-0 text-purple-400" />
                    <div>
                      <h4 className="mb-1 font-medium text-purple-300">Try Portfolio Analysis</h4>
                      <p className="text-gray-400 text-sm">
                        Analyse their entire portfolio to see technical evolution, architectural
                        patterns, and code ownership across all public repositories.
                      </p>
                    </div>
                  </div>
                </div>
                <div className="rounded-lg border border-emerald-500/20 bg-gradient-to-r from-emerald-900/20 to-transparent p-4">
                  <div className="flex items-start gap-3">
                    <GitBranch className="mt-0.5 h-5 w-5 flex-shrink-0 text-emerald-400" />
                    <div>
                      <h4 className="mb-1 font-medium text-emerald-300">
                        Try Single Repository Analysis
                      </h4>
                      <p className="text-gray-400 text-sm">
                        Deep dive into a specific repository to see code quality, commit history,
                        and development patterns.
                      </p>
                    </div>
                  </div>
                </div>
                <div className="rounded-lg border border-blue-500/20 bg-gradient-to-r from-blue-900/20 to-transparent p-4">
                  <div className="flex items-start gap-3">
                    <MessageCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-blue-400" />
                    <div>
                      <h4 className="mb-1 font-medium text-blue-300">Discuss Their Experience</h4>
                      <p className="text-gray-400 text-sm">
                        Ask about their development work in private repositories, other platforms,
                        or non-PR based contributions.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-col justify-center gap-4 sm:flex-row">
              <ExiqusButton
                onClick={() => {
                  setShowZeroPRModal(false);
                  router.push('/portfolio-analysis');
                }}
                className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"
              >
                <FolderGit2 className="mr-2 h-4 w-4" />
                Try Portfolio Analysis
              </ExiqusButton>
              <ExiqusButton
                onClick={() => {
                  setShowZeroPRModal(false);
                  router.push('/analyze');
                }}
                className="bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-700 hover:to-green-700"
              >
                <GitBranch className="mr-2 h-4 w-4" />
                Try Single Repo Analysis
              </ExiqusButton>
              <ExiqusButton
                onClick={() => {
                  setShowZeroPRModal(false);
                  setZeroPRUsername('');
                  setGithubUsername('');
                }}
                className="bg-gradient-to-r from-teal-600 to-cyan-600 hover:from-teal-700 hover:to-cyan-700"
              >
                <Search className="mr-2 h-4 w-4" />
                Try Another User
              </ExiqusButton>
            </div>
          </ExiqusCard>
        </div>
      )}
    </div>
  );
}
