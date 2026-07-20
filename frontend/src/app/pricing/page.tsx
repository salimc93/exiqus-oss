// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import {
  ArrowRight,
  Check,
  CheckCircle,
  Flame,
  GitBranch,
  Rocket,
  Sparkles,
  Users,
  X,
  Zap,
} from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import type React from 'react';
import { useState } from 'react';
import { toast } from 'sonner';

import { ExiqusButton, ExiqusCard, GradientText } from '@/components/ui/exiqus-components';
import { useAuth } from '@/contexts/auth-context';
import { api } from '@/lib/api-client';
import { cn } from '@/lib/utils';

interface PricingTier {
  name: string;
  price: string;
  period: string;
  analyses: string;
  description: string;
  idealCustomer: string;
  features: string[];
  notIncluded?: string[];
  highlighted?: boolean;
  icon: React.ReactNode;
  gradient?: string;
  ctaText: string;
  ctaLink: string;
  badge?: string;
}

const pricingTiers: PricingTier[] = [
  {
    name: 'Free',
    price: '$0',
    period: '/month',
    analyses: '3 repository deep dives',
    description: 'Repository Deep Dives - Basic Technical Evaluation',
    idealCustomer: 'Developers exploring the platform',
    icon: <Sparkles className="h-5 w-5" />,
    gradient: 'from-gray-600 to-gray-700',
    features: [
      '3 repository deep dives per month',
      'Open Source context only',
      'No role selection (basic analysis)',
      'Public repositories only',
      'Basic evidence patterns',
      'Message support',
    ],
    notIncluded: [
      'All contexts (Startup/Enterprise/Agency)',
      'Role-specific analysis (Junior/Mid/Senior)',
      'Candidate insights (Portfolio/PR)',
      'Evidence-based interview questions',
      'Temporal evolution analysis',
    ],
    ctaText: 'Get Started',
    ctaLink: '/signup',
  },
  {
    name: 'Starter',
    price: '$49',
    period: '/month',
    analyses: 'Up to 10 insights/month',
    description: 'Full candidate insight reports with portfolio + PR analysis',
    idealCustomer: 'Small startups hiring occasionally',
    icon: <Rocket className="h-5 w-5" />,
    gradient: 'from-blue-600 to-blue-700',
    features: [
      'Up to 10 candidate insight reports/month (Portfolio + PR analysis)',
      '10 repository deep dives/month',
      'Context-aware analysis (Startup/Enterprise/Agency/Open Source)',
      'Role-specific insights (Junior/Mid/Senior)',
      'Portfolio: Technical evolution & patterns',
      'PR Analysis: Collaboration & code review (Beta)',
      'Evidence-based interview questions',
      'Public repositories only',
      'Message support',
    ],
    notIncluded: ['Premium AI model', 'Priority support'],
    ctaText: 'Get Started',
    ctaLink: '/signup?plan=basic',
  },
  {
    name: 'Growth',
    price: '$199',
    period: '/month',
    analyses: 'Up to 50 insights/month',
    description: 'High-volume hiring: up to 50 full candidate insight reports per month',
    idealCustomer: 'Early-stage recruiters, boutique agencies',
    icon: <Flame className="h-5 w-5" />,
    gradient: 'from-purple-600 to-purple-700',
    features: [
      'Up to 50 candidate insight reports/month (Portfolio + PR analysis)',
      '50 repository deep dives/month',
      'Context-aware analysis (Startup/Enterprise/Agency/Open Source)',
      'Role-specific insights (Junior/Mid/Senior)',
      'Portfolio: Technical evolution & patterns',
      'PR Analysis: Collaboration & code review (Beta)',
      'Evidence-based interview questions',
      'Public repositories only',
      '24-hour priority support SLA',
    ],
    highlighted: true,
    ctaText: 'Get Started',
    ctaLink: '/signup?plan=professional',
  },
  {
    name: 'Scale',
    price: '$499',
    period: '/month',
    analyses: 'Up to 200 insights/month',
    description: 'Enterprise intelligence: up to 200 full candidate insight reports per month',
    idealCustomer: 'Growth-stage teams or hiring partners',
    icon: <Zap className="h-5 w-5" />,
    gradient: 'from-yellow-500 to-yellow-600',
    features: [
      'Up to 200 candidate insight reports/month (Portfolio + PR analysis)',
      '200 repository deep dives/month',
      'Context-aware analysis (Startup/Enterprise/Agency/Open Source)',
      'Role-specific insights (Junior/Mid/Senior)',
      'Portfolio: Technical evolution & patterns',
      'PR Analysis: Collaboration & code review (Beta)',
      'Evidence-based interview questions',
      'Premium AI model (deeper insights)',
      'Public repositories only',
      '12-hour priority support SLA',
    ],
    ctaText: 'Get Started',
    ctaLink: '/signup?plan=enterprise',
  },
];

export default function PricingPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [isCreatingCheckout, setIsCreatingCheckout] = useState(false);

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

  const handlePlanAction = async (tier: PricingTier) => {
    // If user is not logged in, redirect to signup
    if (!user) {
      router.push(tier.ctaLink);
      return;
    }

    // Map tier names to backend plan names
    const planMapping: Record<string, string> = {
      Free: 'free',
      Starter: 'basic',
      Growth: 'professional',
      Scale: 'enterprise',
    };

    const targetPlan = planMapping[tier.name];
    const currentPlan = user.subscription_plan?.toLowerCase() || 'free';

    // If clicking on current plan, go to billing page
    if (targetPlan === currentPlan) {
      router.push('/billing');
      return;
    }

    // If downgrading to free tier, redirect to billing with message
    if (targetPlan === 'free') {
      router.push('/billing');
      toast.info(
        'To downgrade to the Free plan, please cancel your current subscription from the billing page. You will retain access until the end of your billing period.'
      );
      return;
    }

    // Determine if this is an upgrade or downgrade
    const planOrder = ['free', 'basic', 'professional', 'enterprise'];
    const currentIndex = planOrder.indexOf(currentPlan);
    const targetIndex = planOrder.indexOf(targetPlan);
    const isUpgrade = targetIndex > currentIndex;

    // Show confirmation dialog for downgrades
    if (!isUpgrade && currentPlan !== 'free') {
      const confirmed = window.confirm(
        `Downgrade to ${tier.name} plan?\n\n` +
          `Your plan will be downgraded immediately with a prorated credit applied to your account. ` +
          `The credit will be automatically applied to your next invoice.\n\n` +
          `Are you sure you want to continue?`
      );
      if (!confirmed) {
        return;
      }
    }

    // For upgrades and downgrades between paid plans, use the update subscription endpoint
    try {
      setIsCreatingCheckout(true);

      // If user is on free plan, they need to create a new subscription via checkout
      if (currentPlan === 'free') {
        const response = await api.createCheckoutSession({
          plan: targetPlan,
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
      } else {
        // For existing paid subscriptions, use update endpoint
        // This will handle proration automatically through Stripe
        const response = await api.updateSubscription({
          plan: targetPlan,
        });

        if (response.data?.success) {
          // Redirect to billing page to see the updated plan
          router.push('/billing?updated=true');
          toast.success(
            isUpgrade
              ? `Upgraded to ${tier.name}! Changes are active immediately.`
              : `Downgraded to ${tier.name}. A prorated credit has been applied to your account.`
          );
        } else {
          toast.error('Failed to update subscription. Please try again.');
        }
      }
    } catch (error: unknown) {
      console.error('Failed to update subscription:', error);

      // Check for specific error messages
      const errorObj = error as { response?: { data?: { detail?: string } }; message?: string };
      const errorMessage = errorObj?.response?.data?.detail || errorObj?.message || '';

      if (
        errorMessage.includes('subscription not found') ||
        errorMessage.includes('Current subscription not found')
      ) {
        // Subscription ID is stale - guide user to create a new subscription
        toast.error(
          'Your subscription needs to be reactivated. Please create a new subscription.',
          { duration: 6000 }
        );

        // Fallback to checkout flow to create a new subscription
        try {
          const response = await api.createCheckoutSession({
            plan: targetPlan,
            success_url: `${window.location.origin}/billing?success=true`,
            cancel_url: `${window.location.origin}/billing?canceled=true`,
          });

          if (response.data?.data?.checkout_url) {
            window.location.href = response.data.data.checkout_url;
          } else if (response.data?.checkout_url) {
            window.location.href = response.data.checkout_url;
          } else {
            toast.error('Failed to create checkout session. Please contact support.');
          }
        } catch (checkoutError) {
          console.error('Fallback checkout also failed:', checkoutError);
          toast.error('Failed to process plan change. Please contact support.');
        }
      } else {
        // Generic error - show helpful message
        toast.error(
          `Unable to ${isUpgrade ? 'upgrade' : 'downgrade'} subscription. Please try again or contact support.`,
          { duration: 5000 }
        );
      }
    } finally {
      setIsCreatingCheckout(false);
    }
  };

  const getCtaText = (tierName: string) => {
    if (!user) {
      return 'Get Started';
    }

    const tierPlanMap: Record<string, string> = {
      Free: 'free',
      Starter: 'starter',
      Growth: 'growth',
      Scale: 'scale',
    };

    const tierPlan = tierPlanMap[tierName];
    const userPlan = PLAN_MAP[user.subscription_plan?.toLowerCase() || 'free'] || 'free';

    if (tierPlan === userPlan) {
      return 'Current Plan';
    } else if (tierPlan === 'free') {
      return 'Downgrade';
    } else {
      const planOrder = ['free', 'starter', 'growth', 'scale', 'scale_plus'];
      const currentIndex = planOrder.indexOf(userPlan);
      const targetIndex = planOrder.indexOf(tierPlan);
      return targetIndex > currentIndex ? 'Upgrade' : 'Downgrade';
    }
  };

  return (
    <div className="min-h-screen bg-[#0A0A0A] text-white">
      <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-12 text-center">
          <h1 className="mb-4 font-bold text-4xl md:text-5xl">
            <GradientText>Evidence-Based Hiring. Clear Pricing.</GradientText>
          </h1>
          <p className="mx-auto max-w-2xl text-gray-400 text-xl">
            Assess complete candidate portfolios through Portfolio Analysis, PR contributions, and
            repository deep dives. No scores, no grades—just evidence.
          </p>
        </div>

        {/* Pricing Cards */}
        <div className="mb-16 grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-4">
          {pricingTiers.map((tier, index) => (
            <ExiqusCard
              key={tier.name}
              className={cn(
                'group relative flex h-full flex-col p-6 transition-all duration-500',
                'hover:-translate-y-2 hover:scale-105',
                'bg-gradient-to-b from-white/[0.04] to-white/[0.02]',
                tier.highlighted && 'border-purple-500/50 shadow-purple-500/10'
              )}
              glow={tier.highlighted ? 'purple' : 'none'}
              style={{
                animationDelay: `${index * 100}ms`,
              }}
            >
              {/* Premium gradient border for highlighted tier */}
              {tier.highlighted && (
                <div className="absolute inset-0 rounded-lg bg-gradient-to-r from-purple-500/20 via-blue-500/20 to-purple-500/20 blur-xl" />
              )}

              {/* Floating particles effect */}
              <div className="absolute inset-0 overflow-hidden rounded-lg">
                <div className="absolute -top-4 -right-4 h-20 w-20 animate-pulse rounded-full bg-gradient-to-br from-purple-500/10 to-blue-500/10 blur-2xl" />
                <div className="animation-delay-1000 absolute -bottom-4 -left-4 h-16 w-16 animate-pulse rounded-full bg-gradient-to-tr from-blue-500/10 to-purple-500/10 blur-2xl" />
              </div>

              <div className="relative z-10 flex h-full flex-col">
                <div className="mb-6 flex items-center justify-between">
                  <h3 className="font-bold text-2xl text-white">{tier.name}</h3>
                  <div
                    className={cn(
                      'rounded-xl bg-gradient-to-br p-3 shadow-lg',
                      tier.gradient || 'from-gray-600 to-gray-700',
                      'transform transition-transform duration-300 group-hover:rotate-12 group-hover:scale-110'
                    )}
                  >
                    {tier.icon}
                  </div>
                </div>

                <div className="mb-6 flex items-baseline">
                  <span className="bg-gradient-to-r from-white to-gray-300 bg-clip-text font-bold text-4xl text-transparent">
                    {tier.price}
                  </span>
                  <span className="ml-1 whitespace-nowrap text-gray-400">{tier.period}</span>
                </div>

                <p className="mb-2 font-medium text-purple-400 text-sm">
                  {tier.analyses} per month
                </p>
                <p className="mb-3 text-gray-500 text-sm">{tier.description}</p>
                <p className="mb-6 text-gray-600 text-xs">
                  <span className="font-semibold text-gray-400">Ideal for:</span>{' '}
                  {tier.idealCustomer}
                </p>

                <div className="flex-grow">
                  <ul className="mb-8 space-y-3">
                    {tier.features.map((feature, index) => {
                      const hasBeta = feature.includes('(Beta)');
                      const featureText = hasBeta ? feature.replace('(Beta)', '').trim() : feature;

                      return (
                        <li key={index} className="group/item flex items-start text-sm">
                          <Check className="mt-0.5 mr-2 h-4 w-4 flex-shrink-0 text-green-400 transition-transform duration-300 group-hover/item:scale-125" />
                          <span className="flex items-center gap-2 text-gray-300 transition-colors duration-300 group-hover/item:text-white">
                            <span>{featureText}</span>
                            {hasBeta && (
                              <span className="whitespace-nowrap rounded-full border border-teal-500/30 bg-gradient-to-r from-teal-500/20 to-cyan-500/20 px-2 py-0.5 font-semibold text-teal-300 text-xs">
                                BETA
                              </span>
                            )}
                          </span>
                        </li>
                      );
                    })}
                    {tier.notIncluded?.map((feature, index) => (
                      <li key={index} className="group/item flex items-start text-sm opacity-50">
                        <X className="mt-0.5 mr-2 h-4 w-4 flex-shrink-0 text-gray-600" />
                        <span className="text-gray-500 line-through">{feature}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <ExiqusButton
                  onClick={() => handlePlanAction(tier)}
                  className="group/btn mt-auto w-full"
                  variant={tier.highlighted ? 'primary' : 'secondary'}
                  size="lg"
                  disabled={
                    isCreatingCheckout || (!!user && getCtaText(tier.name) === 'Current Plan')
                  }
                >
                  <span className="relative z-10">{getCtaText(tier.name)}</span>
                  {getCtaText(tier.name) !== 'Current Plan' && (
                    <ArrowRight className="ml-2 h-4 w-4 transition-transform duration-300 group-hover/btn:translate-x-1" />
                  )}
                </ExiqusButton>
              </div>
            </ExiqusCard>
          ))}
        </div>

        {/* What's Included Explanation */}
        <div className="mt-12 mb-16">
          <ExiqusCard className="border-blue-500/30 bg-gradient-to-br from-blue-900/10 via-purple-900/10 to-pink-900/10">
            <div className="p-8">
              <h3 className="mb-6 text-center font-bold text-2xl">
                <GradientText>Understanding Your Quota</GradientText>
              </h3>

              <div className="grid gap-8 md:grid-cols-2">
                {/* Candidate Assessment */}
                <div className="space-y-3">
                  <div className="flex items-start gap-3">
                    <div className="rounded-lg bg-gradient-to-br from-purple-600 to-pink-600 p-2">
                      <Users className="h-5 w-5" />
                    </div>
                    <div>
                      <h4 className="font-semibold text-lg text-purple-300">
                        Candidate Insight Report
                      </h4>
                      <p className="mt-2 text-gray-400 text-sm">
                        Analyzing a <strong>GitHub username</strong> counts as 1 candidate insight
                        report. This includes:
                      </p>
                      <ul className="mt-2 space-y-1 text-gray-400 text-sm">
                        <li className="flex items-start gap-2">
                          <CheckCircle className="mt-0.5 h-4 w-4 flex-shrink-0 text-purple-400" />
                          <span>
                            <strong>Portfolio Analysis:</strong> Complete developer profile across
                            all repos
                          </span>
                        </li>
                        <li className="flex items-start gap-2">
                          <CheckCircle className="mt-0.5 h-4 w-4 flex-shrink-0 text-purple-400" />
                          <span>
                            <strong>PR Analysis:</strong> Collaboration patterns and code review
                            quality
                          </span>
                        </li>
                        <li className="flex items-start gap-2">
                          <CheckCircle className="mt-0.5 h-4 w-4 flex-shrink-0 text-purple-400" />
                          <span>
                            Running both Portfolio + PR for the same username ={' '}
                            <strong>1 insight report</strong>
                          </span>
                        </li>
                      </ul>
                    </div>
                  </div>
                </div>

                {/* Repository Deep Dive */}
                <div className="space-y-3">
                  <div className="flex items-start gap-3">
                    <div className="rounded-lg bg-gradient-to-br from-blue-600 to-cyan-600 p-2">
                      <GitBranch className="h-5 w-5" />
                    </div>
                    <div>
                      <h4 className="font-semibold text-blue-300 text-lg">Repository Deep Dive</h4>
                      <p className="mt-2 text-gray-400 text-sm">
                        Analyzing a <strong>single repository</strong> (without full candidate
                        profile) counts as 1 repo deep dive:
                      </p>
                      <ul className="mt-2 space-y-1 text-gray-400 text-sm">
                        <li className="flex items-start gap-2">
                          <CheckCircle className="mt-0.5 h-4 w-4 flex-shrink-0 text-blue-400" />
                          <span>
                            Evaluate <strong>individual repositories</strong> in isolation
                          </span>
                        </li>
                        <li className="flex items-start gap-2">
                          <CheckCircle className="mt-0.5 h-4 w-4 flex-shrink-0 text-blue-400" />
                          <span>Assess code quality, architecture, and technical debt</span>
                        </li>
                        <li className="flex items-start gap-2">
                          <CheckCircle className="mt-0.5 h-4 w-4 flex-shrink-0 text-blue-400" />
                          <span>
                            <strong>Separate quota</strong> from candidate insight reports
                          </span>
                        </li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-6 rounded-lg border border-purple-500/30 bg-purple-900/20 p-4">
                <p className="text-center text-gray-300 text-sm">
                  <strong className="text-purple-300">Example:</strong> With Starter plan (10 + 10),
                  you can assess <strong>10 different candidates</strong> (Portfolio + PR for each)
                  AND analyse <strong>10 standalone repositories</strong> separately each month.
                </p>
              </div>
            </div>
          </ExiqusCard>
        </div>

        {/* Feature Comparison */}
        <div className="mt-20">
          <h2 className="mb-12 text-center font-bold text-3xl">
            <GradientText>Compare Plans</GradientText>
          </h2>

          <ExiqusCard className="overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-white/[0.06] border-b">
                    <th className="p-4 text-left font-medium text-gray-400">Features</th>
                    {pricingTiers.map((tier) => (
                      <th key={tier.name} className="p-4 text-center">
                        <div className="font-semibold">{tier.name}</div>
                        <div className="text-gray-400 text-sm">{tier.price}/mo</div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.06]">
                  {[
                    {
                      feature: 'Candidate insight reports/month',
                      values: ['0', '10', '50', '200'],
                    },
                    {
                      feature: 'Portfolio Analysis (technical evolution)',
                      values: [false, true, true, true],
                    },
                    {
                      feature: 'PR Analysis (collaboration patterns)',
                      values: [false, true, true, true],
                    },
                    { feature: 'Repository deep dives/month', values: ['3', '10', '50', '200'] },
                    {
                      feature: 'Analysis contexts available',
                      values: [
                        'Open Source only',
                        'All 4 contexts',
                        'All 4 contexts',
                        'All 4 contexts',
                      ],
                    },
                    {
                      feature: 'Role-specific analysis',
                      values: [false, true, true, true],
                    },
                    { feature: 'Public repositories only', values: [true, true, true, true] },
                    {
                      feature: 'Evidence-based interview questions',
                      values: [false, true, true, true],
                    },
                    {
                      feature: 'Premium AI model (deeper insights)',
                      values: [false, false, false, true],
                    },
                    {
                      feature: 'Support',
                      values: ['Message', 'Message', '24-hour SLA', '12-hour SLA'],
                    },
                  ].map((row, index) => {
                    const hasBeta = row.feature.includes('(Beta)');
                    const featureText = hasBeta
                      ? row.feature.replace('(Beta)', '').trim()
                      : row.feature;

                    return (
                      <tr key={index}>
                        <td className="p-4 text-gray-300">
                          <span className="flex items-center gap-2">
                            {featureText}
                            {hasBeta && (
                              <span className="whitespace-nowrap rounded-full border border-teal-500/30 bg-gradient-to-r from-teal-500/20 to-cyan-500/20 px-2 py-0.5 font-semibold text-teal-300 text-xs">
                                BETA
                              </span>
                            )}
                          </span>
                        </td>
                        {row.values.map((value, idx) => (
                          <td key={idx} className="p-4 text-center">
                            {typeof value === 'boolean' ? (
                              value ? (
                                <Check className="mx-auto h-5 w-5 text-green-500" />
                              ) : (
                                <X className="mx-auto h-5 w-5 text-gray-600" />
                              )
                            ) : (
                              <span className="text-gray-400">{value}</span>
                            )}
                          </td>
                        ))}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </ExiqusCard>

          {/* Quota Clarity Note */}
          <p className="mt-4 text-center text-gray-500 text-sm">
            * All quotas are <strong>fixed monthly limits</strong> that reset at the start of each
            billing period.
            <br />
            Candidate insight reports and repo deep dives are tracked separately—giving you
            flexibility in how you use your quota.
          </p>
        </div>

        {/* CTA Section */}
        <div className="mt-20 text-center">
          <ExiqusCard className="bg-gradient-to-br from-purple-900/10 to-blue-900/10 p-12">
            <h2 className="mb-4 font-bold text-3xl">
              <GradientText>Ready to Assess Candidates Holistically?</GradientText>
            </h2>
            <p className="mb-8 text-gray-400 text-xl">
              Make better hiring decisions with evidence-based candidate insights.
            </p>
            <div className="flex flex-col items-center justify-center gap-4 sm:flex-row">
              {user ? (
                <>
                  <Link href="/billing" className="w-full sm:w-auto">
                    <ExiqusButton size="lg" className="w-full min-w-[160px] gap-2 sm:w-auto">
                      <Zap className="h-5 w-5" />
                      View Your Plan
                    </ExiqusButton>
                  </Link>
                  <Link href="/contact" className="w-full sm:w-auto">
                    <ExiqusButton
                      variant="secondary"
                      size="lg"
                      className="w-full min-w-[160px] sm:w-auto"
                    >
                      Contact Sales
                    </ExiqusButton>
                  </Link>
                </>
              ) : (
                <>
                  <Link href="/signup" className="w-full sm:w-auto">
                    <ExiqusButton size="lg" className="w-full min-w-[160px] gap-2 sm:w-auto">
                      <Zap className="h-5 w-5" />
                      Get Started Free
                    </ExiqusButton>
                  </Link>
                  <Link href="/contact" className="w-full sm:w-auto">
                    <ExiqusButton
                      variant="secondary"
                      size="lg"
                      className="w-full min-w-[160px] sm:w-auto"
                    >
                      Contact Sales
                    </ExiqusButton>
                  </Link>
                </>
              )}
            </div>
          </ExiqusCard>
        </div>
      </div>
    </div>
  );
}
