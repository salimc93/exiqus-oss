// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import { format } from 'date-fns';
import {
  Activity,
  Building,
  Calendar,
  CheckCircle,
  ChevronRight,
  Clock,
  CreditCard,
  Crown,
  GitBranch,
  HelpCircle,
  Key,
  Loader2,
  LogOut,
  Mail,
  MessageSquare,
  Settings,
  Shield,
  Sparkles,
  User,
  Users,
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Badge } from '@/components/ui/badge';
import { ExiqusButton, ExiqusCard, GradientText } from '@/components/ui/exiqus-components';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { useAuth } from '@/contexts/auth-context';
import { useAuthGuard } from '@/hooks/use-auth-guard';
import { useToast } from '@/hooks/use-toast';
import { api } from '@/lib/api-client';
import { formatDate } from '@/lib/utils';
import type { AnalysisDetails } from '@/types';

interface Subscription {
  plan: string;
  status: string;
  current_period_start?: string;
  current_period_end?: string;
  subscription_end_date?: string;
  cancel_at_period_end: boolean;
  stripe_customer_id?: string;
  stripe_subscription_id?: string;
}

export default function AccountPage() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const { isLoading, showUnauthorized, UnauthorizedComponent } = useAuthGuard();
  const { toast } = useToast();
  const [logoutModalOpen, setLogoutModalOpen] = useState(false);
  const [recentAnalyses, setRecentAnalyses] = useState<AnalysisDetails[]>([]);
  const [analysesCount, setAnalysesCount] = useState(0);
  const [candidatesCount, setCandidatesCount] = useState(0);
  const [loadingAnalyses, setLoadingAnalyses] = useState(true);
  const [loadingCandidates, setLoadingCandidates] = useState(true);
  const [subscription, setSubscription] = useState<Subscription | null>(null);

  // Fetch recent analyses and subscription data
  useEffect(() => {
    const fetchData = async () => {
      if (!user) return;

      try {
        setLoadingAnalyses(true);
        setLoadingCandidates(true);
        const [analysesResponse, candidatesResponse, subscriptionResponse] = await Promise.all([
          api.getAnalyses({ limit: 5 }),
          api.getDashboardCandidates({ limit: 1000 }), // Fetch all candidates to get accurate count
          api.getSubscription().catch(() => ({ data: null })), // Handle potential errors gracefully
        ]);

        const analysesData = analysesResponse.data;
        setAnalysesCount(analysesData.total_count || 0);
        if (analysesData.items && analysesData.items.length > 0) {
          setRecentAnalyses(analysesData.items.slice(0, 2)); // Show last 2 analyses
        }

        // Set candidates count - get total count from all fetched candidates
        const candidatesData = candidatesResponse.data || [];
        setCandidatesCount(candidatesData.length);

        // Set subscription data
        setSubscription(subscriptionResponse.data?.data || subscriptionResponse.data);
      } catch (error) {
        console.error('Failed to fetch data:', error);
      } finally {
        setLoadingAnalyses(false);
        setLoadingCandidates(false);
      }
    };

    if (user) {
      fetchData();
    }
  }, [user]);

  // Handle loading state
  if (isLoading) {
    return (
      <div className="flex min-h-[calc(100vh-12rem)] items-center justify-center bg-[#0A0A0A]">
        <div className="text-center">
          <div className="mb-4 inline-flex h-16 w-16 items-center justify-center">
            <div className="h-12 w-12 animate-spin rounded-full border-4 border-purple-600 border-t-transparent" />
          </div>
          <p className="text-gray-400">Loading account settings...</p>
        </div>
      </div>
    );
  }

  // Handle unauthorized state
  if (showUnauthorized && UnauthorizedComponent) {
    return <UnauthorizedComponent />;
  }

  // Ensure user is defined at this point
  if (!user) {
    return null;
  }

  const handleLogout = async () => {
    setLogoutModalOpen(false);
    await logout();
    router.push('/');
  };

  const handleContactSupport = () => {
    router.push('/contact?subject=account');
  };

  // Calculate usage stats for single repo deep dives
  const getSingleRepoPlanLimit = () => {
    switch (user?.subscription_plan) {
      case 'free':
        return 3;
      case 'starter':
        return 50;
      case 'growth':
        return 100;
      case 'scale':
        return 250;
      case 'scale_plus':
        return -1; // Unlimited
      default:
        return 0;
    }
  };

  // Get candidate insight limits
  const getCandidateInsightLimit = () => {
    switch (user?.subscription_plan) {
      case 'free':
        return 0;
      case 'starter':
        return 10;
      case 'growth':
        return 50;
      case 'scale':
        return 200;
      case 'scale_plus':
        return 500;
      default:
        return 0;
    }
  };

  const planLimit = getSingleRepoPlanLimit();
  const candidateInsightLimit = getCandidateInsightLimit();
  const usagePercentage = planLimit > 0 ? Math.min((analysesCount / planLimit) * 100, 100) : 0;
  const candidateUsagePercentage =
    candidateInsightLimit > 0 ? Math.min((candidatesCount / candidateInsightLimit) * 100, 100) : 0;

  // Get plan badge color
  const getPlanBadgeColor = () => {
    switch (user?.subscription_plan) {
      case 'scale_plus':
        return 'bg-gradient-to-r from-yellow-600 to-amber-600';
      case 'scale':
        return 'bg-gradient-to-r from-purple-600 to-pink-600';
      case 'growth':
        return 'bg-gradient-to-r from-blue-600 to-indigo-600';
      case 'starter':
        return 'bg-gradient-to-r from-green-600 to-emerald-600';
      default:
        return 'bg-gray-600';
    }
  };

  return (
    <div className="min-h-[calc(100vh-12rem)] bg-[#0A0A0A] py-8">
      {/* Animated gradient background */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 h-80 w-80 animate-pulse rounded-full bg-purple-500/10 blur-3xl"></div>
        <div className="absolute -bottom-40 -left-40 h-80 w-80 animate-pulse rounded-full bg-blue-500/10 blur-3xl delay-1000"></div>
      </div>

      <div className="relative mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        {/* Page Header with User Info */}
        <div className="mb-10">
          <div className="mb-6 flex items-center justify-between">
            <div>
              <h1 className="mb-2 font-bold text-4xl text-gray-100">
                Account <GradientText>Settings</GradientText>
              </h1>
              <p className="text-gray-400">Manage your profile, subscription, and preferences</p>
            </div>
            <Badge className={`${getPlanBadgeColor()} border-0 px-4 py-2 text-white`}>
              <Crown className="mr-1 h-4 w-4" />
              {user.subscription_plan.toUpperCase()} PLAN
            </Badge>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Left Column - Profile & Subscription */}
          <div className="space-y-6 lg:col-span-2">
            {/* Profile Information Card */}
            <ExiqusCard
              className="bg-gradient-to-br from-purple-900/10 to-transparent p-6"
              glow="purple"
            >
              <div className="mb-6 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-gradient-to-br from-purple-600 to-blue-600">
                    <User className="h-6 w-6 text-white" />
                  </div>
                  <div>
                    <h2 className="font-semibold text-gray-100 text-xl">Profile Information</h2>
                    <p className="text-gray-400 text-sm">Your personal details</p>
                  </div>
                </div>
                <ExiqusButton variant="ghost" size="sm">
                  <Settings className="h-4 w-4" />
                </ExiqusButton>
              </div>

              <div className="space-y-4">
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-4">
                    <div className="mb-1 flex items-center gap-2">
                      <User className="h-4 w-4 text-purple-400" />
                      <p className="font-medium text-gray-400 text-xs">Full Name</p>
                    </div>
                    <p className="font-medium text-gray-100 text-lg">{user.full_name}</p>
                  </div>

                  <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-4">
                    <div className="mb-1 flex items-center gap-2">
                      <Mail className="h-4 w-4 text-blue-400" />
                      <p className="font-medium text-gray-400 text-xs">Email Address</p>
                    </div>
                    <p className="font-medium text-gray-100 text-lg">{user.email}</p>
                  </div>

                  {user.company && (
                    <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-4">
                      <div className="mb-1 flex items-center gap-2">
                        <Building className="h-4 w-4 text-green-400" />
                        <p className="font-medium text-gray-400 text-xs">Company</p>
                      </div>
                      <p className="font-medium text-gray-100 text-lg">{user.company}</p>
                    </div>
                  )}

                  <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-4">
                    <div className="mb-1 flex items-center gap-2">
                      <Calendar className="h-4 w-4 text-orange-400" />
                      <p className="font-medium text-gray-400 text-xs">Member Since</p>
                    </div>
                    <p className="font-medium text-gray-100 text-lg">
                      {user.created_at
                        ? format(new Date(user.created_at), 'MMMM yyyy')
                        : 'January 2025'}
                    </p>
                  </div>
                </div>
              </div>
            </ExiqusCard>

            {/* Subscription Details Card */}
            <ExiqusCard
              className="bg-gradient-to-br from-blue-900/10 to-transparent p-6"
              glow="blue"
            >
              <div className="mb-6 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-gradient-to-br from-blue-600 to-purple-600">
                    <CreditCard className="h-6 w-6 text-white" />
                  </div>
                  <div>
                    <h2 className="font-semibold text-gray-100 text-xl">Subscription</h2>
                    <p className="text-gray-400 text-sm">Plan details and usage</p>
                  </div>
                </div>
                <div className="flex gap-2">
                  {/* Show Upgrade button for all plans except scale_plus */}
                  {user.subscription_plan !== 'scale_plus' && (
                    <ExiqusButton onClick={() => router.push('/pricing')} size="sm">
                      <Sparkles className="mr-1 h-4 w-4" />
                      Upgrade
                    </ExiqusButton>
                  )}
                  {/* Show Manage Plan button for scale_plus, Downgrade for others (except free) */}
                  {user.subscription_plan !== 'free' && (
                    <ExiqusButton
                      onClick={() => router.push('/pricing')}
                      size="sm"
                      variant="secondary"
                    >
                      {user.subscription_plan === 'scale_plus' ? 'Manage Plan' : 'Downgrade'}
                    </ExiqusButton>
                  )}
                </div>
              </div>

              <div className="space-y-6">
                {/* Plan Status */}
                <div className="rounded-lg border border-purple-500/20 bg-gradient-to-r from-purple-900/20 to-blue-900/20 p-4">
                  <div className="mb-3 flex items-center justify-between">
                    <div>
                      <p className="mb-1 text-gray-400 text-sm">Current Plan</p>
                      <div className="flex items-center gap-2">
                        <h3 className="font-bold text-2xl text-gray-100 capitalize">
                          {user.subscription_plan}
                        </h3>
                        <Badge className="border-green-500/30 bg-green-500/20 text-green-400">
                          <CheckCircle className="mr-1 h-3 w-3" />
                          Active
                        </Badge>
                      </div>
                    </div>
                  </div>

                  {/* Candidate Insights (Portfolio + PR) - Paid plans only */}
                  {candidateInsightLimit > 0 && (
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="flex items-center gap-1 text-gray-400">
                          <Users className="h-3 w-3" />
                          Candidate Insights
                        </span>
                        <span className="text-gray-100">
                          {loadingCandidates ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            `${candidatesCount} / ${candidateInsightLimit} used`
                          )}
                        </span>
                      </div>
                      <Progress value={candidateUsagePercentage} className="h-2" />
                      <p className="text-gray-500 text-xs">
                        Portfolio + PR Analysis per unique candidate
                      </p>
                    </div>
                  )}

                  {/* Repository Deep Dives */}
                  <div className={`space-y-2 ${candidateInsightLimit > 0 ? 'mt-6' : ''}`}>
                    <div className="flex justify-between text-sm">
                      <span className="flex items-center gap-1 text-gray-400">
                        <GitBranch className="h-3 w-3" />
                        Repository Deep Dives
                      </span>
                      <span className="text-gray-100">
                        {analysesCount} / {planLimit === -1 ? 'Unlimited' : planLimit}
                      </span>
                    </div>
                    {planLimit !== -1 && (
                      <>
                        <Progress value={usagePercentage} className="h-2" />
                        <p className="text-gray-500 text-xs">
                          {analysesCount >= planLimit
                            ? 'Limit reached for this month'
                            : planLimit - analysesCount === 1
                              ? '1 deep dive remaining this month'
                              : `${planLimit - analysesCount} deep dives remaining this month`}
                        </p>
                      </>
                    )}
                    {planLimit === -1 && (
                      <p className="text-gray-500 text-xs">
                        Unlimited single repository deep dives
                      </p>
                    )}
                  </div>
                </div>

                {/* Billing Info */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
                    <p className="mb-1 text-gray-400 text-xs">Status</p>
                    <p className="font-medium text-gray-100 text-sm capitalize">
                      {user.subscription_status}
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
                    <p className="mb-1 text-gray-400 text-xs">Next Billing</p>
                    <p className="font-medium text-gray-100 text-sm">
                      {user.subscription_plan === 'free'
                        ? 'N/A'
                        : subscription?.current_period_end || subscription?.subscription_end_date
                          ? (() => {
                              const renewalDate = formatDate(
                                subscription.current_period_end ||
                                  subscription.subscription_end_date
                              );
                              return subscription.cancel_at_period_end
                                ? `Cancels on ${renewalDate}`
                                : `Auto-renews on ${renewalDate}`;
                            })()
                          : 'Loading...'}
                    </p>
                  </div>
                </div>
              </div>
            </ExiqusCard>

            {/* Recent Activity Card */}
            <ExiqusCard className="p-6" glow="subtle">
              <div className="mb-6 flex items-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-gradient-to-br from-green-600 to-emerald-600">
                  <Activity className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h2 className="font-semibold text-gray-100 text-xl">Recent Activity</h2>
                  <p className="text-gray-400 text-sm">Your latest analyses</p>
                </div>
              </div>

              <div className="space-y-3">
                {loadingAnalyses ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
                  </div>
                ) : recentAnalyses.length > 0 ? (
                  <>
                    {recentAnalyses.map((analysis) => {
                      const timeAgo = analysis.created_at
                        ? new Date(analysis.created_at).toLocaleDateString('en-US', {
                            month: 'short',
                            day: 'numeric',
                            hour: 'numeric',
                            minute: '2-digit',
                          })
                        : 'Recently';

                      const repoName =
                        analysis.repository_url
                          ?.replace('https://github.com/', '')
                          ?.replace('.git', '') || 'repository';

                      return (
                        <div
                          key={analysis.id}
                          className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <CheckCircle className="h-4 w-4 text-green-400" />
                              <p className="text-gray-100 text-sm">Analysis completed</p>
                            </div>
                            <p className="text-gray-500 text-xs">{timeAgo}</p>
                          </div>
                          <p className="mt-1 text-gray-400 text-xs">{repoName}</p>
                        </div>
                      );
                    })}
                    <ExiqusButton
                      variant="ghost"
                      className="mt-2 w-full"
                      onClick={() => router.push('/analyses')}
                    >
                      View All Analyses
                      <ChevronRight className="ml-1 h-4 w-4" />
                    </ExiqusButton>
                  </>
                ) : (
                  <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-6 text-center">
                    <GitBranch className="mx-auto mb-3 h-8 w-8 text-gray-600" />
                    <p className="text-gray-400 text-sm">No analyses yet</p>
                    <p className="mt-1 text-gray-500 text-xs">
                      Your repository analyses will appear here
                    </p>
                    <ExiqusButton
                      variant="primary"
                      className="mt-4"
                      size="sm"
                      onClick={() => router.push('/analyze')}
                    >
                      <Sparkles className="mr-1 h-4 w-4" />
                      Start First Analysis
                    </ExiqusButton>
                  </div>
                )}
              </div>
            </ExiqusCard>
          </div>

          {/* Right Column - Quick Actions & Support */}
          <div className="space-y-6">
            {/* Quick Actions */}
            <ExiqusCard className="p-6" glow="subtle">
              <h3 className="mb-4 font-semibold text-gray-100 text-lg">Quick Actions</h3>
              <div className="space-y-3">
                <button
                  type="button"
                  onClick={() => router.push('/analyze')}
                  className="flex w-full items-center justify-between rounded-lg border border-white/[0.06] bg-white/[0.02] p-3 transition-colors hover:bg-white/[0.04]"
                >
                  <div className="flex items-center gap-3">
                    <Sparkles className="h-5 w-5 text-purple-400" />
                    <span className="text-gray-100">New Analysis</span>
                  </div>
                  <ChevronRight className="h-4 w-4 text-gray-400" />
                </button>

                <button
                  type="button"
                  onClick={() => router.push('/analyses')}
                  className="flex w-full items-center justify-between rounded-lg border border-white/[0.06] bg-white/[0.02] p-3 transition-colors hover:bg-white/[0.04]"
                >
                  <div className="flex items-center gap-3">
                    <Activity className="h-5 w-5 text-blue-400" />
                    <span className="text-gray-100">View Analyses</span>
                  </div>
                  <ChevronRight className="h-4 w-4 text-gray-400" />
                </button>

                {/* Show Manage Plan for scale_plus, Upgrade Plan for others */}
                <button
                  type="button"
                  onClick={() => router.push('/pricing')}
                  className="flex w-full items-center justify-between rounded-lg border border-white/[0.06] bg-white/[0.02] p-3 transition-colors hover:bg-white/[0.04]"
                >
                  <div className="flex items-center gap-3">
                    <Crown className="h-5 w-5 text-yellow-400" />
                    <span className="text-gray-100">
                      {user?.subscription_plan === 'scale_plus' ? 'Manage Plan' : 'Upgrade Plan'}
                    </span>
                  </div>
                  <ChevronRight className="h-4 w-4 text-gray-400" />
                </button>

                {(user?.subscription_plan === 'scale' ||
                  user?.subscription_plan === 'scale_plus') && (
                  <button
                    type="button"
                    onClick={() =>
                      toast({
                        title: 'Coming Soon',
                        description: 'API access will be available soon for Scale plans',
                      })
                    }
                    className="flex w-full items-center justify-between rounded-lg border border-white/[0.06] bg-white/[0.02] p-3 opacity-60 transition-colors hover:bg-white/[0.04]"
                  >
                    <div className="flex items-center gap-3">
                      <Key className="h-5 w-5 text-green-400" />
                      <span className="text-gray-100">API Access</span>
                      <Badge className="bg-purple-500/20 text-purple-300 text-xs">Soon</Badge>
                    </div>
                    <ChevronRight className="h-4 w-4 text-gray-400" />
                  </button>
                )}
              </div>
            </ExiqusCard>

            {/* Support Card */}
            <ExiqusCard
              className="bg-gradient-to-br from-orange-900/10 to-transparent p-6"
              glow="subtle"
            >
              <div className="mb-4 flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-orange-600 to-red-600">
                  <HelpCircle className="h-5 w-5 text-white" />
                </div>
                <h3 className="font-semibold text-gray-100 text-lg">Need Help?</h3>
              </div>

              <p className="mb-4 text-gray-400 text-sm">
                Our support team is here to assist you with any questions or concerns.
              </p>

              <div className="space-y-3">
                <ExiqusButton
                  variant="secondary"
                  className="w-full"
                  onClick={() => router.push('/contact')}
                >
                  <MessageSquare className="mr-2 h-4 w-4" />
                  Contact Support
                </ExiqusButton>

                <ExiqusButton
                  variant="secondary"
                  className="w-full"
                  onClick={() => router.push('/faq')}
                >
                  <HelpCircle className="mr-2 h-4 w-4" />
                  View FAQ
                </ExiqusButton>
              </div>

              <Separator className="my-4 bg-white/[0.06]" />

              <div className="text-gray-400 text-sm">
                <p className="mb-2">For account deletion requests:</p>
                <button
                  type="button"
                  onClick={handleContactSupport}
                  className="text-orange-400 underline hover:text-orange-300"
                >
                  Contact our support team
                </button>
              </div>
            </ExiqusCard>

            {/* Security Card */}
            <ExiqusCard className="p-6" glow="subtle">
              <div className="mb-4 flex items-center gap-3">
                <Shield className="h-5 w-5 text-green-400" />
                <h3 className="font-semibold text-gray-100 text-lg">Security</h3>
              </div>

              <div className="space-y-3">
                <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
                  <div className="mb-1 flex items-center justify-between">
                    <p className="text-gray-400 text-sm">Last Login</p>
                    <Clock className="h-3 w-3 text-gray-500" />
                  </div>
                  <p className="font-medium text-gray-100 text-sm">Today at 2:12 PM</p>
                </div>

                <ExiqusButton
                  variant="secondary"
                  className="w-full"
                  onClick={() => setLogoutModalOpen(true)}
                >
                  <LogOut className="mr-2 h-4 w-4" />
                  Sign Out
                </ExiqusButton>
              </div>
            </ExiqusCard>
          </div>
        </div>

        {/* Logout Confirmation Dialog */}
        <AlertDialog open={logoutModalOpen} onOpenChange={setLogoutModalOpen}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Sign out of your account?</AlertDialogTitle>
              <AlertDialogDescription>
                You&apos;ll need to sign in again to access your account and analyses.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <ExiqusButton onClick={handleLogout}>Sign Out</ExiqusButton>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </div>
  );
}
