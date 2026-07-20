// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

import { ArrowRight, Check, Flame, Rocket, Sparkles, Zap } from 'lucide-react';
import Link from 'next/link';
import React from 'react';

import { ExiqusButton, ExiqusCard, GradientText } from '@/components/ui/exiqus-components';
import { cn } from '@/lib/utils';

const plans = [
  {
    name: 'Free',
    price: '$0',
    analyses: '3 repo deep dives',
    features: ['Basic evidence patterns', 'Public repos only', 'Try the platform'],
    icon: <Sparkles className="h-5 w-5" />,
    gradient: 'from-gray-600 to-gray-700',
  },
  {
    name: 'Starter',
    price: '$49',
    analyses: '10 candidates/mo',
    features: [
      'Portfolio + PR Analysis',
      '10 repo deep dives/mo',
      'All contexts & roles',
      'Evidence-based insights',
    ],
    icon: <Rocket className="h-5 w-5" />,
    gradient: 'from-blue-600 to-blue-700',
  },
  {
    name: 'Growth',
    price: '$199',
    analyses: '50 candidates/mo',
    features: [
      'Everything in Starter',
      '50 repo deep dives/mo',
      'Interview questions',
      'Priority support',
    ],
    icon: <Flame className="h-5 w-5" />,
    gradient: 'from-purple-600 to-purple-700',
    highlighted: true,
  },
  {
    name: 'Scale',
    price: '$499',
    analyses: '200 candidates/mo',
    features: [
      'Everything in Growth',
      '200 repo deep dives/mo',
      'Premium AI model (deeper insights)',
      'Dedicated support',
    ],
    icon: <Zap className="h-5 w-5" />,
    gradient: 'from-yellow-500 to-yellow-600',
  },
];

export default function PricingPreview() {
  return (
    <section className="bg-gradient-to-b from-transparent via-purple-500/5 to-transparent px-4 py-20">
      <div className="mx-auto max-w-7xl">
        <div className="mb-12 text-center">
          <h2 className="mb-4 font-bold text-3xl md:text-4xl">
            <GradientText>Simple, Transparent Pricing</GradientText>
          </h2>
          <p className="mx-auto max-w-2xl text-gray-400 text-xl">
            Start free and scale as your hiring needs grow
          </p>
        </div>

        <div className="mb-12 grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {plans.map((plan, index) => (
            <ExiqusCard
              key={plan.name}
              className={cn(
                'group relative flex h-full flex-col p-6 transition-all duration-500',
                'hover:-translate-y-2 hover:scale-105',
                'bg-gradient-to-b from-white/[0.04] to-white/[0.02]',
                plan.highlighted && 'border-purple-500/50 shadow-purple-500/10'
              )}
              glow={plan.highlighted ? 'purple' : 'none'}
              style={{
                animationDelay: `${index * 100}ms`,
              }}
            >
              {/* Premium gradient border for highlighted tier */}
              {plan.highlighted && (
                <div className="absolute inset-0 rounded-lg bg-gradient-to-r from-purple-500/20 via-blue-500/20 to-purple-500/20 blur-xl" />
              )}

              {/* Floating particles effect */}
              <div className="absolute inset-0 overflow-hidden rounded-lg">
                <div className="absolute -top-4 -right-4 h-20 w-20 animate-pulse rounded-full bg-gradient-to-br from-purple-500/10 to-blue-500/10 blur-2xl" />
                <div className="animation-delay-1000 absolute -bottom-4 -left-4 h-16 w-16 animate-pulse rounded-full bg-gradient-to-tr from-blue-500/10 to-purple-500/10 blur-2xl" />
              </div>

              <div className="relative z-10 flex h-full flex-col">
                <div className="mb-6 flex items-center justify-between">
                  <h3 className="font-bold text-2xl text-white">{plan.name}</h3>
                  <div
                    className={cn(
                      'rounded-xl bg-gradient-to-br p-3 shadow-lg',
                      plan.gradient,
                      'transform transition-transform duration-300 group-hover:rotate-12 group-hover:scale-110'
                    )}
                  >
                    {plan.icon}
                  </div>
                </div>

                <div className="mb-6">
                  <span className="bg-gradient-to-r from-white to-gray-300 bg-clip-text font-bold text-4xl text-transparent">
                    {plan.price}
                  </span>
                  <span className="text-gray-400">/month</span>
                </div>

                <p className="mb-6 font-medium text-purple-400 text-sm">{plan.analyses}</p>

                <ul className="mb-6 flex-grow space-y-3">
                  {plan.features.map((feature, idx) => (
                    <li key={idx} className="group/item flex items-start text-sm">
                      <Check className="mt-0.5 mr-2 h-4 w-4 flex-shrink-0 text-green-400 transition-transform duration-300 group-hover/item:scale-125" />
                      <span className="text-gray-300 transition-colors duration-300 group-hover/item:text-white">
                        {feature}
                      </span>
                    </li>
                  ))}
                </ul>

                <Link href="/pricing" className="mt-auto block">
                  <ExiqusButton
                    variant={plan.highlighted ? 'primary' : 'secondary'}
                    className="group/btn w-full"
                  >
                    <span className="relative z-10">View Details</span>
                    <ArrowRight className="ml-2 h-4 w-4 transition-transform duration-300 group-hover/btn:translate-x-1" />
                  </ExiqusButton>
                </Link>
              </div>
            </ExiqusCard>
          ))}
        </div>

        <div className="text-center">
          <Link href="/pricing">
            <ExiqusButton size="lg" variant="secondary" className="group">
              View Full Pricing Details
              <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
            </ExiqusButton>
          </Link>
        </div>
      </div>
    </section>
  );
}
