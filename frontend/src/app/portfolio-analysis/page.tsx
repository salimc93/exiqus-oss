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
  Code2,
  FileCode,
  GitBranch,
  Layers,
  Loader2,
  Lock,
  MessageCircle,
  Rocket,
  Sparkles,
  Target,
  TrendingUp,
  User,
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
    label: 'Startup',
    icon: Rocket,
    description: 'Fast iteration, adaptability, MVP patterns',
    gradient: 'from-purple-600 to-pink-600',
    bgGradient: 'from-purple-900/20 to-pink-900/20',
    borderColor: 'border-purple-500',
  },
  {
    value: 'enterprise',
    label: 'Enterprise',
    icon: Building2,
    description: 'Architecture, scalability, documentation',
    gradient: 'from-blue-600 to-cyan-600',
    bgGradient: 'from-blue-900/20 to-cyan-900/20',
    borderColor: 'border-blue-500',
  },
  {
    value: 'agency',
    label: 'Agency',
    icon: Briefcase,
    description: 'Project variety, reusability, client patterns',
    gradient: 'from-orange-600 to-amber-600',
    bgGradient: 'from-orange-900/20 to-amber-900/20',
    borderColor: 'border-orange-500',
  },
  {
    value: 'open_source',
    label: 'Open Source',
    icon: Users,
    description: 'Community engagement, maintenance, quality',
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

export default function PortfolioAnalysisPage() {
  const { isLoading, showUnauthorized, UnauthorizedComponent } = useAuthGuard();
  const searchParams = useSearchParams();
  const { user } = useAuth();
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
  const router = useRouter();
  const { refreshUser } = useAuth();

  // Fetch locked context for the candidate
  const { lockedContext, refetch: refetchContext } = useCandidateContext(
    isValidUsername ? githubUsername : null
  );

  // Auto-sync role/context when locked context is fetched
  useEffect(() => {
    if (lockedContext) {
      setRole(lockedContext.role);
      setContext(lockedContext.organization_context);
    }
  }, [lockedContext]);

  // Check for username query parameter
  useEffect(() => {
    const username = searchParams.get('username');
    if (username) {
      setGithubUsername(username);
      validateGitHubUsername(username);
    }
  }, [searchParams]);

  const handleContextReset = () => {
    // Refetch to clear the locked context state
    refetchContext();
  };

  const validateGitHubUsername = (username: string): boolean => {
    const trimmedUsername = username.trim();

    if (!trimmedUsername) {
      setValidationError('Please enter a GitHub username');
      setIsValidUsername(false);
      return false;
    }

    // GitHub username validation: alphanumeric, hyphens, max 39 chars
    const usernameRegex = /^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$/;
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

    if (!validateGitHubUsername(githubUsername)) {
      return;
    }

    setIsAnalyzing(true);
    setLoadingStage('fetching');
    setAnalyzingUser(githubUsername);

    // Use setTimeout to allow React to render the loading screen before making API call
    setTimeout(async () => {
      try {
        const requestData = {
          github_username: githubUsername,
          context: context as 'startup' | 'enterprise' | 'agency' | 'open_source',
          role: role as 'junior' | 'mid' | 'senior',
          force_refresh: false,
        };

        const response = await api.analyzePortfolio(requestData);

        const analysisId = response.data.id || response.data.analysis_id;
        const status = response.data.status;

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
              const pollResponse = await api.getPortfolioAnalysis(analysisId);
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
                  toast.error('Portfolio analysis failed. Please try again.');
                  setIsAnalyzing(false);
                  return;
                }

                toast.success('Portfolio analysis completed successfully!');

                // Check if we should return to candidate hub
                const returnTo = searchParams.get('returnTo');
                if (returnTo === 'candidate-hub') {
                  const username = searchParams.get('username') || githubUsername;
                  router.push(`/candidate-hub/${username}`);
                } else {
                  router.push(`/portfolio-analyses/${analysisId}`);
                }
              }
            } catch (pollError) {
              console.error('Polling error:', pollError);
            }
          }, 30000); // Poll every 30 seconds - balances UX with server load

          // Don't reset isAnalyzing - let polling handle the state
          return;
        } else if (analysisId) {
          // Immediate completion (from cache)
          // Show UI for smooth UX even though it's instant
          setTimeout(() => setLoadingStage('analyzing'), 1000);
          setTimeout(() => setLoadingStage('generating'), 2000);
          setTimeout(() => setLoadingStage('finalizing'), 3000);

          // Wait 5 seconds before redirecting to show the UI
          await new Promise((resolve) => setTimeout(resolve, 5000));

          // Refresh user data to update usage counts
          try {
            await refreshUser();
          } catch {
            // Silently fail - not critical
          }

          toast.success('Portfolio analysis completed successfully!');

          // Check if we should return to candidate hub
          const returnTo = searchParams.get('returnTo');
          if (returnTo === 'candidate-hub') {
            const username = searchParams.get('username') || githubUsername;
            router.push(`/candidate-hub/${username}`);
          } else {
            router.push(`/portfolio-analyses/${analysisId}`);
          }
        } else {
          toast.error('Analysis completed but no ID received. Please check your history.');
          console.error('No analysis ID found in response:', response.data);
        }
      } catch (error: unknown) {
        console.error('Portfolio analysis failed:', error);

        const errorResponse = error as {
          response?: { status?: number; data?: { detail?: string } };
        };

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
                    <strong>What&apos;s a Candidate Insight?</strong>
                    <br />
                    Analysing a GitHub username (Portfolio + PR combined) = 1 insight.
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
            // String error detail
            const detailString = typeof errorDetail === 'string' ? errorDetail : '';

            if (detailString.includes('limit reached')) {
              toast.error(
                'Monthly candidate insight limit reached. Upgrade your plan or wait until next month.'
              );
            } else if (detailString.includes('paid plans')) {
              toast.error(
                'Portfolio Analysis is available for paid plans only. Please upgrade your account.'
              );
            } else {
              toast.error(detailString || 'You do not have access to this feature.');
            }
          }
        } else if (errorResponse.response?.status === 404) {
          toast.error('GitHub user not found. Please check the username and try again.');
        } else if (errorResponse.response?.status === 400) {
          const errorDetail = errorResponse.response.data?.detail || 'Invalid request';
          toast.error(errorDetail);
        } else if (errorResponse.response?.status === 401) {
          // Auth interceptor handles this
        } else {
          toast.error('Failed to analyse portfolio. Please try again.');
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

    if (validationError) {
      setValidationError('');
    }

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
            <div className="h-12 w-12 animate-spin rounded-full border-4 border-purple-600 border-t-transparent" />
          </div>
          <p className="text-gray-400">Preparing portfolio analysis tools...</p>
        </div>
      </div>
    );
  }

  // Show unauthorized component
  if (showUnauthorized && UnauthorizedComponent) {
    return <UnauthorizedComponent />;
  }

  // Show upgrade prompt for FREE users
  if (user && user.subscription_plan === 'free') {
    return (
      <UpgradePrompt
        feature="Portfolio Analysis"
        requiredTier="Starter"
        description="Analyze complete developer portfolios to assess technical evolution, architectural patterns, and code ownership across multiple repositories."
      />
    );
  }

  return (
    <div className="min-h-screen bg-[#0A0A0A]">
      {/* Animated gradient background */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 h-80 w-80 animate-pulse rounded-full bg-purple-500/20 blur-3xl"></div>
        <div className="absolute -bottom-40 -left-40 h-80 w-80 animate-pulse rounded-full bg-blue-500/20 blur-3xl delay-1000"></div>
      </div>

      {/* Full-screen loading overlay */}
      {isAnalyzing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
          <ExiqusCard className="max-w-md p-8 text-center" glow="purple">
            <div className="mb-6">
              <Loader2 className="mx-auto h-16 w-16 animate-spin text-purple-400" />
            </div>
            <h2 className="mb-4 font-semibold text-2xl">
              <GradientText>Analysing Portfolio</GradientText>
            </h2>
            <p className="mb-2 font-medium text-gray-300 text-lg">{analyzingUser}</p>
            <p className="mb-6 text-gray-400">
              Examining technical evolution, architectural patterns, and code ownership across
              public repositories...
            </p>
            <div className="space-y-2 text-gray-500 text-sm">
              <p className="flex items-center justify-center gap-2">
                {loadingStage === 'fetching' ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <CheckCircle className="h-4 w-4 text-green-500" />
                )}
                Fetching public repositories
              </p>
              <p className="flex items-center justify-center gap-2">
                {loadingStage === 'analyzing' ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : loadingStage === 'generating' || loadingStage === 'finalizing' ? (
                  <CheckCircle className="h-4 w-4 text-green-500" />
                ) : (
                  <span className="block h-4 w-4" />
                )}
                Analysing technical patterns
              </p>
              <p className="flex items-center justify-center gap-2">
                {loadingStage === 'generating' ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : loadingStage === 'finalizing' ? (
                  <CheckCircle className="h-4 w-4 text-green-500" />
                ) : (
                  <span className="block h-4 w-4" />
                )}
                Generating insights
              </p>
              <p className="flex items-center justify-center gap-2">
                {loadingStage === 'finalizing' ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <span className="block h-4 w-4" />
                )}
                Creating interview questions
              </p>
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
              Candidate Portfolio Insights
            </div>
            <h1 className="mb-4 font-bold text-4xl tracking-tight md:text-5xl">
              <GradientText>Gain Developer Portfolio Insights</GradientText>
            </h1>
            <p className="mx-auto max-w-2xl text-gray-400 text-xl">
              Analyse a candidate&apos;s technical evolution, architectural patterns, and code
              ownership across their public GitHub repositories
            </p>
          </div>

          {/* Main Analysis Form */}
          <ExiqusCard className="p-8" glow="purple">
            <div className="mb-6">
              <h2 className="flex items-center gap-2 font-semibold text-2xl text-gray-100">
                <User className="h-6 w-6 text-purple-400" />
                Portfolio Analysis
              </h2>
              <p className="mt-2 text-gray-400">
                Enter a GitHub username to assess their technical journey and capabilities
              </p>
            </div>
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* GitHub Username Input */}
              <div className="space-y-2">
                <label className="flex items-center gap-2 font-medium text-sm">
                  <User className="h-4 w-4 text-purple-400" />
                  GitHub Username
                </label>
                <div className="group relative">
                  <div className="absolute inset-0 rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 opacity-0 blur transition-opacity duration-500 group-focus-within:opacity-30 group-hover:opacity-20"></div>
                  <div className="relative">
                    <User className="absolute top-1/2 left-4 h-5 w-5 -translate-y-1/2 text-gray-500 transition-colors group-focus-within:text-purple-400" />
                    <input
                      type="text"
                      placeholder="octocat"
                      value={githubUsername}
                      onChange={handleUsernameChange}
                      disabled={isAnalyzing}
                      className={`h-14 w-full rounded-lg border px-12 py-2 pr-12 text-lg transition-all duration-300 ${validationError ? 'border-red-500 bg-red-500/5' : 'border-white/[0.09] bg-white/[0.06] hover:bg-white/[0.08] focus:bg-white/[0.09]'} text-gray-100 outline-none placeholder:text-gray-500 focus:border-purple-500 disabled:opacity-50 ${isValidUsername ? 'border-green-500/50' : ''}`}
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

              {/* Role Level Selection */}
              <div className="space-y-3">
                <label className="flex items-center gap-2 font-medium text-gray-300 text-sm">
                  <Award className="h-4 w-4 text-purple-400" />
                  Expected Role Level
                  {lockedContext && <span className="text-amber-400 text-xs">(Locked)</span>}
                </label>
                <div className="grid gap-3 sm:grid-cols-3">
                  {ROLE_OPTIONS.map((option, index) => {
                    const Icon = option.icon;
                    const isSelected = role === option.value;
                    const isLocked = lockedContext && lockedContext.role === option.value;
                    const isDisabled = !!lockedContext; // Disable when locked
                    return (
                      <label
                        key={option.value}
                        className={`group relative flex overflow-hidden rounded-xl border-2 p-4 transition-all duration-300 ${
                          isDisabled && !isLocked
                            ? 'cursor-not-allowed opacity-60'
                            : 'cursor-pointer hover:scale-[1.02]'
                        } ${
                          isSelected || isLocked
                            ? `${option.borderColor} bg-gradient-to-br ${option.bgGradient} shadow-lg`
                            : 'border-white/[0.09] bg-white/[0.03] hover:border-white/[0.15] hover:bg-white/[0.06]'
                        }`}
                        style={{
                          animationDelay: `${index * 50}ms`,
                        }}
                      >
                        {(isSelected || isLocked) && (
                          <div
                            className={`absolute inset-0 bg-gradient-to-br ${option.gradient} animate-pulse opacity-10`}
                          />
                        )}
                        <input
                          type="radio"
                          name="role"
                          value={option.value}
                          checked={isSelected}
                          onChange={(e) => !isDisabled && setRole(e.target.value)}
                          disabled={isDisabled}
                          className="sr-only"
                        />
                        <div className="relative flex w-full items-start gap-3">
                          <div
                            className={`rounded-lg p-2 transition-all duration-300 ${
                              isSelected || isLocked
                                ? `bg-gradient-to-br ${option.gradient} text-white shadow-md`
                                : 'bg-white/[0.06] text-gray-400 group-hover:bg-white/[0.09]'
                            }`}
                          >
                            <Icon className="h-5 w-5" />
                          </div>
                          <div className="flex-1">
                            <p
                              className={`font-medium transition-colors ${
                                isSelected || isLocked
                                  ? 'text-gray-100'
                                  : 'text-gray-200 group-hover:text-gray-100'
                              }`}
                            >
                              {option.label}
                            </p>
                            <p className="mt-1 text-gray-400 text-xs">{option.description}</p>
                          </div>
                          <div className="absolute top-1 right-1 z-10 flex items-center gap-1">
                            {isLocked && (
                              <div className="rounded-full bg-amber-500/20 p-1 ring-1 ring-amber-500/30 backdrop-blur-sm">
                                <Lock className="fade-in h-3.5 w-3.5 animate-in text-amber-300 duration-300" />
                              </div>
                            )}
                            {isSelected && (
                              <CheckCircle className="fade-in h-5 w-5 animate-in text-green-400 drop-shadow-glow duration-300" />
                            )}
                          </div>
                        </div>
                      </label>
                    );
                  })}
                </div>
              </div>

              {/* Analysis Context Selection */}
              <div className="space-y-3">
                <label className="flex items-center gap-2 font-medium text-gray-300 text-sm">
                  <Layers className="h-4 w-4 text-purple-400" />
                  Hiring Context
                  {lockedContext && <span className="text-amber-400 text-xs">(Locked)</span>}
                </label>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  {CONTEXT_OPTIONS.map((option, index) => {
                    const Icon = option.icon;
                    const isSelected = context === option.value;
                    const isLocked =
                      lockedContext &&
                      lockedContext.organization_context.toLowerCase() === option.value;
                    const isDisabled = !!lockedContext; // Disable when locked
                    return (
                      <label
                        key={option.value}
                        className={`group relative flex overflow-hidden rounded-xl border-2 p-4 transition-all duration-300 ${
                          isDisabled && !isLocked
                            ? 'cursor-not-allowed opacity-60'
                            : 'cursor-pointer hover:scale-[1.02]'
                        } ${
                          isSelected || isLocked
                            ? `${option.borderColor} bg-gradient-to-br ${option.bgGradient} shadow-lg`
                            : 'border-white/[0.09] bg-white/[0.03] hover:border-white/[0.15] hover:bg-white/[0.06]'
                        }`}
                        style={{
                          animationDelay: `${index * 50}ms`,
                        }}
                      >
                        {(isSelected || isLocked) && (
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
                              isSelected || isLocked
                                ? `bg-gradient-to-br ${option.gradient} text-white shadow-md`
                                : 'bg-white/[0.06] text-gray-400 group-hover:bg-white/[0.09]'
                            }`}
                          >
                            <Icon className="h-5 w-5" />
                          </div>
                          <div className="flex-1">
                            <p
                              className={`font-medium transition-colors ${
                                isSelected || isLocked
                                  ? 'text-gray-100'
                                  : 'text-gray-200 group-hover:text-gray-100'
                              }`}
                            >
                              {option.label}
                            </p>
                            <p className="mt-1 text-gray-400 text-xs">{option.description}</p>
                          </div>
                          <div className="absolute top-1 right-1 z-10 flex items-center gap-1">
                            {isLocked && (
                              <div className="rounded-full bg-amber-500/20 p-1 ring-1 ring-amber-500/30 backdrop-blur-sm">
                                <Lock className="fade-in h-3.5 w-3.5 animate-in text-amber-300 duration-300" />
                              </div>
                            )}
                            {isSelected && (
                              <CheckCircle className="fade-in h-5 w-5 animate-in text-green-400 drop-shadow-glow duration-300" />
                            )}
                          </div>
                        </div>
                      </label>
                    );
                  })}
                </div>
              </div>

              {/* What You'll Get */}
              <Alert className="border-purple-500/20 bg-gradient-to-r from-purple-900/10 to-blue-900/10">
                <AlertDescription>
                  <div className="mb-3 flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-purple-400" />
                    <p className="font-medium text-gray-100">What You&apos;ll Get:</p>
                  </div>
                  <div className="grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">
                    <div className="flex items-center gap-2">
                      <GitBranch className="h-3 w-3 text-purple-400" />
                      <span className="text-gray-400">Technical evolution over time</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Code2 className="h-3 w-3 text-purple-400" />
                      <span className="text-gray-400">Architectural patterns used</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Activity className="h-3 w-3 text-purple-400" />
                      <span className="text-gray-400">Code ownership analysis</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <MessageCircle className="h-3 w-3 text-purple-400" />
                      <span className="text-gray-400">Evidence-based interview questions</span>
                    </div>
                  </div>
                </AlertDescription>
              </Alert>

              {/* Analysis Note */}
              <Alert className="border-amber-500/20 bg-amber-500/10">
                <AlertCircle className="h-4 w-4 text-amber-500" />
                <AlertDescription className="text-amber-200">
                  <strong>Note:</strong> Portfolio analysis cannot be cancelled once started. The
                  process typically takes 2-4 minutes depending on the number of repositories.
                </AlertDescription>
              </Alert>

              {/* Submit Button */}
              <ExiqusButton
                type="submit"
                size="lg"
                disabled={isAnalyzing || !githubUsername || !isValidUsername}
                className="group relative flex h-14 w-full items-center justify-center overflow-hidden"
              >
                <div className="absolute inset-0 bg-gradient-to-r from-purple-600 to-blue-600 opacity-0 transition-opacity duration-500 group-hover:opacity-100" />
                <span className="relative flex items-center">
                  {isAnalyzing ? (
                    <>
                      <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                      <span className="font-medium text-base">Analysing Portfolio...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="mr-2 h-5 w-5 group-hover:animate-pulse" />
                      <span className="font-medium text-base">Analyse Portfolio</span>
                      <ArrowRight className="ml-2 h-5 w-5 -translate-x-2 opacity-0 transition-all duration-300 group-hover:translate-x-0 group-hover:opacity-100" />
                    </>
                  )}
                </span>
              </ExiqusButton>
            </form>
          </ExiqusCard>

          {/* Feature Cards */}
          <div className="grid gap-4 md:grid-cols-3">
            <ExiqusCard
              className="group border-purple-500/20 bg-gradient-to-br from-purple-900/10 to-transparent p-6"
              glow="purple"
            >
              <div className="space-y-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-purple-600 to-purple-400">
                  <GitBranch className="h-5 w-5 text-white" />
                </div>
                <h3 className="font-semibold text-gray-100 text-lg">Technical Evolution</h3>
                <p className="text-gray-400 text-sm">
                  Understand how the candidate&apos;s skills have evolved over time through their
                  repository contributions
                </p>
              </div>
            </ExiqusCard>

            <ExiqusCard
              className="group border-blue-500/20 bg-gradient-to-br from-blue-900/10 to-transparent p-6"
              glow="blue"
            >
              <div className="space-y-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-blue-600 to-cyan-400">
                  <FileCode className="h-5 w-5 text-white" />
                </div>
                <h3 className="font-semibold text-gray-100 text-lg">Architectural Patterns</h3>
                <p className="text-gray-400 text-sm">
                  Identify architectural decisions and patterns across multiple projects and tech
                  stacks
                </p>
              </div>
            </ExiqusCard>

            <ExiqusCard
              className="group border-green-500/20 bg-gradient-to-br from-green-900/10 to-transparent p-6"
              glow="green"
            >
              <div className="space-y-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-green-600 to-emerald-400">
                  <MessageCircle className="h-5 w-5 text-white" />
                </div>
                <h3 className="font-semibold text-gray-100 text-lg">Interview Questions</h3>
                <p className="text-gray-400 text-sm">
                  Get context-aware, evidence-based questions tailored to the candidate&apos;s
                  actual work
                </p>
              </div>
            </ExiqusCard>
          </div>
        </div>
      </div>
    </div>
  );
}
