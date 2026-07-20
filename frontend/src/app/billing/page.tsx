// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import { CreditCard, Download, Loader2, Package, Receipt, TrendingUp, Users } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { toast } from 'sonner';

import { UnauthorizedAccess } from '@/components/auth/unauthorized-access';
import { ExiqusButton, ExiqusCard, GradientText } from '@/components/ui/exiqus-components';
import { useAuth } from '@/contexts/auth-context';
import { api } from '@/lib/api-client';
import { formatCurrency, formatDate } from '@/lib/utils';

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

interface Invoice {
  invoice_id: string;
  amount_paid: number;
  currency: string;
  status: string;
  billing_period_start: string;
  billing_period_end: string;
  invoice_url?: string;
  created_at: string;
}

interface UsageSummary {
  plan: string;
  usage_quota: number;
  usage_consumed: number;
  usage_remaining: number;
  usage_percentage: number;
  current_period: string;
  plan_features: string[];
}

// Map backend plan names to our display names
const PLAN_MAP: Record<string, string> = {
  free: 'free',
  starter: 'starter',
  basic: 'starter', // Backend uses 'basic' for starter
  growth: 'growth',
  professional: 'growth', // Backend uses 'professional' for growth
  scale: 'scale',
  enterprise: 'scale', // Backend uses 'enterprise' for scale
  scale_plus: 'scale_plus',
};

const PLAN_DETAILS = {
  free: {
    name: 'Free',
    price: 0,
    color: 'gray',
    features: [
      '3 AI-powered analyses',
      '7 template-based analyses',
      'Basic evidence insights',
      'Message support',
    ],
  },
  starter: {
    name: 'Starter',
    price: 49,
    color: 'blue',
    features: [
      '10 candidate insight reports per month',
      '50 repository deep dives per month',
      'Portfolio + PR Analysis',
      'Evidence-based interview questions',
      'Message support',
    ],
  },
  growth: {
    name: 'Growth',
    price: 199,
    color: 'purple',
    features: [
      '50 candidate insight reports per month',
      '100 repository deep dives per month',
      'Portfolio + PR Analysis',
      'Evidence-based interview questions',
      '24-hour priority support SLA',
    ],
  },
  scale: {
    name: 'Scale',
    price: 499,
    color: 'orange',
    features: [
      '200 candidate insight reports per month',
      '250 repository deep dives per month',
      'Portfolio + PR Analysis',
      'Evidence-based interview questions',
      'Premium AI model (deeper insights)',
      '12-hour priority support SLA',
    ],
  },
  scale_plus: {
    name: 'Scale+',
    price: 2500,
    color: 'red',
    features: [
      '500 candidate insight reports per month',
      'Unlimited repository deep dives',
      'Portfolio + PR Analysis',
      'Evidence-based interview questions',
      'Premium AI model (deeper insights)',
      '6-hour dedicated support SLA',
    ],
  },
};

// Helper function to format feature names from API
function formatFeatureName(feature: string): string {
  // Handle underscore-separated feature names from backend
  const featureMap: Record<string, string> = {
    basic_analysis: 'Basic Analysis',
    ai_analysis: 'AI-Powered Analysis',
    advanced_analysis: 'Advanced AI Analysis',
    pdf_reports: 'PDF Export',
    html_reports: 'HTML Export',
    advanced_metrics: 'Advanced Metrics',
    api_access: 'API Access',
    priority_support: 'Priority Support',
    batch_analysis: 'Batch Analysis',
    temporal_analysis: 'Temporal Analysis',
    interview_questions: 'Interview Questions',
    dedicated_support: 'Dedicated Support',
    custom_integrations: 'Custom Integrations',
  };

  return (
    featureMap[feature] ||
    feature
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  );
}

export default function BillingPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [usage, setUsage] = useState<UsageSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [cancelLoading, setCancelLoading] = useState(false);
  const [actualUsageCount, setActualUsageCount] = useState(0);

  useEffect(() => {
    // Check for success/canceled/updated parameters first (before auth check)
    const urlParams = new URLSearchParams(window.location.search);
    const hasSuccess = urlParams.get('success') === 'true';
    const hasCanceled = urlParams.get('canceled') === 'true';
    const hasUpdated = urlParams.get('updated') === 'true';

    if (!authLoading && user) {
      // For plan updates, poll until webhook completes
      if (hasUpdated || hasSuccess) {
        // Show loading toast
        const loadingToast = toast.loading('Processing your subscription update...');

        // Poll for subscription update (max 10 seconds)
        let pollCount = 0;
        const maxPolls = 10;
        const pollInterval = setInterval(async () => {
          pollCount++;

          try {
            const subResponse = await api.getSubscription();
            const currentPlan = subResponse.data?.data?.plan || subResponse.data?.plan;

            // Check if plan has changed (webhook completed)
            if (currentPlan !== user?.subscription_plan || pollCount >= maxPolls) {
              clearInterval(pollInterval);
              toast.dismiss(loadingToast);

              // Fetch all billing data
              fetchBillingData();

              // Show success message
              if (pollCount < maxPolls) {
                toast.success('Your subscription has been updated. Changes are now active.');
              } else {
                toast.success(
                  "Your subscription is being processed. Refresh if changes don't appear."
                );
              }

              // Clean up URL
              window.history.replaceState({}, document.title, '/billing');
            }
          } catch (error) {
            console.error('Polling error:', error);
            if (pollCount >= maxPolls) {
              clearInterval(pollInterval);
              toast.dismiss(loadingToast);
              fetchBillingData();
              toast.info('Please refresh the page to see your updated subscription.');
              window.history.replaceState({}, document.title, '/billing');
            }
          }
        }, 1000); // Poll every 1 second
      } else {
        fetchBillingData();
      }

      // Show appropriate toast messages for other cases
      if (hasCanceled) {
        setTimeout(() => {
          toast.info('Payment canceled. You can try again anytime.');
        }, 500);
        // Clean up the URL
        window.history.replaceState({}, document.title, '/billing');
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authLoading, user]);

  const fetchBillingData = async () => {
    try {
      setLoading(true);
      const [subResponse, usageResponse, invoicesResponse] = await Promise.all([
        api.getSubscription(),
        api.getUsage(),
        api.getInvoices(),
      ]);

      setSubscription(subResponse.data?.data || subResponse.data);
      setUsage(usageResponse.data);
      setInvoices(invoicesResponse.data);

      // For FREE tier, fetch AI quota separately
      const rawPlan = user?.subscription_plan || subResponse.data?.plan || 'free';
      const currentPlan = PLAN_MAP[rawPlan.toLowerCase()] || 'free';

      if (currentPlan === 'free') {
        // Use AI quota endpoint for free tier
        const aiQuotaResponse = await api.getAIQuotaStatus();
        setActualUsageCount(aiQuotaResponse.data.ai_used || 0);
      } else {
        // Use candidate insight count from usage API (candidate-centric model)
        setActualUsageCount(usageResponse.data.usage_consumed || 0);
      }
    } catch (error) {
      console.error('Failed to fetch billing data:', error);
      // Don't show error toast for 401 errors - the interceptor handles session expiry
      const axiosError = error as { response?: { status?: number } };
      if (axiosError?.response?.status !== 401) {
        toast.error('Failed to load billing information');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = async () => {
    try {
      // Map the current plan to determine the upgrade path
      const upgradePlan = currentPlan === 'starter' ? 'professional' : 'enterprise';

      const response = await api.createCheckoutSession({
        plan: upgradePlan,
        success_url: `${window.location.origin}/billing?success=true`,
        cancel_url: `${window.location.origin}/billing?canceled=true`,
      });

      if (response.data?.data?.checkout_url) {
        window.location.href = response.data.data.checkout_url;
      } else if (response.data?.checkout_url) {
        window.location.href = response.data.checkout_url;
      } else {
        toast.error('Failed to create checkout session. Please try again.');
      }
    } catch (error) {
      console.error('Failed to create checkout session:', error);
      toast.error('Failed to create checkout session. Please contact support.');
    }
  };

  const handleCancel = async () => {
    if (!window.confirm('Are you sure you want to cancel your subscription?')) {
      return;
    }

    try {
      setCancelLoading(true);
      await api.cancelSubscription();
      toast.success('Subscription will be canceled at the end of the billing period');
      await fetchBillingData();
    } catch (error) {
      console.error('Failed to cancel subscription:', error);
      toast.error('Failed to cancel subscription');
    } finally {
      setCancelLoading(false);
    }
  };

  if (authLoading || loading) {
    return (
      <div className="flex min-h-[calc(100vh-12rem)] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-purple-600" />
      </div>
    );
  }

  if (!user) {
    return <UnauthorizedAccess />;
  }

  // Get the plan from user profile first, fall back to subscription API
  const rawPlan = user?.subscription_plan || subscription?.plan || 'free';
  const currentPlan = PLAN_MAP[rawPlan.toLowerCase()] || 'free';
  const planDetails = PLAN_DETAILS[currentPlan as keyof typeof PLAN_DETAILS] || PLAN_DETAILS.free;

  return (
    <div className="min-h-[calc(100vh-12rem)] bg-[#0A0A0A] py-8">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="font-bold text-3xl">
            <GradientText>Billing & Subscription</GradientText>
          </h1>
          <p className="mt-2 text-gray-400">Manage your subscription and billing details</p>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          {/* Current Plan Card */}
          <div className="lg:col-span-2">
            <ExiqusCard className="p-6" glow="subtle">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="font-semibold text-gray-100 text-xl">Current Plan</h2>
                <Package className="h-6 w-6 text-purple-400" />
              </div>

              <div className="space-y-4">
                <div>
                  <div className="flex items-baseline gap-2">
                    <span className="font-bold text-3xl text-gray-100">{planDetails.name}</span>
                    {currentPlan !== 'free' && (
                      <span className="text-2xl text-gray-400">${planDetails.price}/month</span>
                    )}
                  </div>
                  {subscription && (
                    <p className="mt-1 text-gray-500 text-sm">
                      Status: <span className="capitalize">{subscription.status}</span>
                      {subscription.cancel_at_period_end && (
                        <span className="ml-2 text-yellow-500">(Canceling at period end)</span>
                      )}
                    </p>
                  )}
                </div>

                {subscription && currentPlan !== 'free' && (
                  <div className="rounded-lg bg-gray-900/50 p-4">
                    <p className="text-gray-400 text-sm">
                      {subscription.cancel_at_period_end ? (
                        <>
                          <span className="text-yellow-400">Cancels on:</span>{' '}
                          {formatDate(
                            subscription.current_period_end || subscription.subscription_end_date
                          )}
                        </>
                      ) : (
                        <>
                          <span className="text-green-400">Auto-renews on:</span>{' '}
                          {formatDate(
                            subscription.current_period_end || subscription.subscription_end_date
                          )}
                        </>
                      )}
                    </p>
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex gap-3">
                  {currentPlan === 'free' ? (
                    <ExiqusButton onClick={() => router.push('/pricing')} className="flex-1">
                      <TrendingUp className="mr-2 h-4 w-4" />
                      Upgrade Plan
                    </ExiqusButton>
                  ) : (
                    <>
                      <ExiqusButton
                        onClick={() => router.push('/pricing')}
                        variant="secondary"
                        className="flex-1"
                      >
                        Change Plan
                      </ExiqusButton>
                      {currentPlan !== 'scale_plus' && (
                        <ExiqusButton onClick={handleUpgrade} className="flex-1">
                          <TrendingUp className="mr-2 h-4 w-4" />
                          Quick Upgrade
                        </ExiqusButton>
                      )}
                      {!subscription?.cancel_at_period_end && (
                        <ExiqusButton
                          onClick={handleCancel}
                          variant="secondary"
                          disabled={cancelLoading}
                          className="flex-1"
                        >
                          {cancelLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                          Cancel Subscription
                        </ExiqusButton>
                      )}
                    </>
                  )}
                </div>
              </div>
            </ExiqusCard>

            {/* Invoices */}
            <ExiqusCard className="mt-6 p-6" glow="subtle">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="font-semibold text-gray-100 text-xl">Invoice History</h2>
                <Receipt className="h-6 w-6 text-purple-400" />
              </div>

              {invoices.length > 0 ? (
                <div className="space-y-3">
                  {invoices.slice(0, 5).map((invoice) => (
                    <div
                      key={invoice.invoice_id}
                      className="flex items-center justify-between rounded-lg bg-gray-900/50 p-4"
                    >
                      <div>
                        <p className="font-medium text-gray-100">
                          {formatCurrency(invoice.amount_paid / 100, invoice.currency)}
                        </p>
                        <p className="text-gray-400 text-sm">{formatDate(invoice.created_at)}</p>
                      </div>
                      <div className="flex items-center gap-3">
                        <span
                          className={`rounded-full px-2 py-1 font-medium text-xs ${
                            invoice.status === 'paid'
                              ? 'bg-green-900/50 text-green-400'
                              : 'bg-gray-900/50 text-gray-400'
                          }`}
                        >
                          {invoice.status}
                        </span>
                        {invoice.invoice_url && (
                          <a
                            href={invoice.invoice_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-purple-400 hover:text-purple-300"
                          >
                            <Download className="h-4 w-4" />
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-400">No invoices yet</p>
              )}
            </ExiqusCard>
          </div>

          {/* Usage Summary */}
          {usage && (
            <div>
              <ExiqusCard className="p-6" glow="subtle">
                <div className="mb-4 flex items-center justify-between">
                  <h2 className="font-semibold text-gray-100 text-xl">This Month</h2>
                  <Users className="h-6 w-6 text-purple-400" />
                </div>

                <div className="space-y-4">
                  <div>
                    <div className="mb-2 flex justify-between text-sm">
                      <span className="text-gray-400">
                        {currentPlan === 'free' ? 'Repository Deep Dives' : 'Candidates Assessed'}
                      </span>
                      <span className="text-gray-100">
                        {actualUsageCount} /{' '}
                        {currentPlan === 'free'
                          ? '3'
                          : planDetails.features[0].split(' ')[0].replace(',', '')}
                      </span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-gray-800">
                      <div
                        className="h-full bg-gradient-to-r from-purple-600 to-blue-600 transition-all"
                        style={{
                          width: `${Math.min(
                            (actualUsageCount /
                              (currentPlan === 'free'
                                ? 3
                                : parseInt(
                                    planDetails.features[0].split(' ')[0].replace(',', '')
                                  ))) *
                              100,
                            100
                          )}%`,
                        }}
                      />
                    </div>
                    <p className="mt-1 text-gray-500 text-xs">
                      {(() => {
                        const limit =
                          currentPlan === 'free'
                            ? 3
                            : parseInt(planDetails.features[0].split(' ')[0].replace(',', ''));
                        const remaining = limit - actualUsageCount;
                        const itemType = currentPlan === 'free' ? 'deep dives' : 'candidates';
                        if (remaining >= 0) {
                          return `${remaining} ${itemType} remaining`;
                        } else {
                          return `${Math.abs(remaining)} ${itemType} over limit`;
                        }
                      })()}
                    </p>
                  </div>

                  <div className="rounded-lg bg-gray-900/50 p-4">
                    <p className="mb-2 font-medium text-gray-300 text-sm">Plan Features</p>
                    <ul className="space-y-1 text-gray-400 text-sm">
                      {(
                        planDetails.features || usage.plan_features.map((f) => formatFeatureName(f))
                      ).map((feature, index) => (
                        <li key={index}>• {feature}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </ExiqusCard>

              {/* Payment Method */}
              <ExiqusCard className="mt-6 p-6" glow="subtle">
                <div className="mb-4 flex items-center justify-between">
                  <h2 className="font-semibold text-gray-100 text-xl">Payment Method</h2>
                  <CreditCard className="h-6 w-6 text-purple-400" />
                </div>

                {subscription?.stripe_customer_id ? (
                  <ExiqusButton
                    variant="secondary"
                    className="w-full"
                    onClick={() => toast.info('Stripe customer portal coming soon')}
                  >
                    Manage Payment Methods
                  </ExiqusButton>
                ) : (
                  <div className="space-y-3">
                    <p className="text-gray-400">No payment method on file</p>
                    <div className="rounded-lg bg-gray-900/50 p-3">
                      <p className="text-gray-500 text-xs">
                        🔒 Payment information is securely handled by Stripe. We never store credit
                        card details on our servers.
                      </p>
                    </div>
                  </div>
                )}
              </ExiqusCard>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
