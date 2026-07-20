// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import { ArrowRight, Sparkles } from 'lucide-react';
import Link from 'next/link';

import { ExiqusButton, ExiqusCard, GradientText } from './exiqus-components';

interface UpgradePromptProps {
  feature: string;
  requiredTier: string;
  description?: string;
}

export function UpgradePrompt({ feature, requiredTier, description }: UpgradePromptProps) {
  return (
    <div className="flex min-h-[calc(100vh-12rem)] items-center justify-center bg-[#0A0A0A] px-4 py-12">
      {/* Subtle background gradient */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 h-80 w-80 animate-pulse rounded-full bg-purple-500/10 blur-3xl"></div>
        <div className="absolute -bottom-40 -left-40 h-80 w-80 animate-pulse rounded-full bg-blue-500/10 blur-3xl delay-1000"></div>
      </div>

      <ExiqusCard className="relative max-w-2xl p-12 text-center" glow="subtle">
        {/* Icon */}
        <div className="mb-6 flex justify-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-purple-600/20 to-blue-600/20">
            <Sparkles className="h-8 w-8 text-purple-400" />
          </div>
        </div>

        {/* Heading */}
        <h1 className="mb-3 font-bold text-3xl text-gray-100">
          <GradientText>{feature}</GradientText>
        </h1>

        {/* Required Tier Badge */}
        <div className="mb-4 flex justify-center">
          <span className="inline-flex items-center gap-2 rounded-full border border-purple-500/30 bg-purple-500/10 px-4 py-1.5 font-medium text-purple-300 text-sm">
            Available on {requiredTier} and above
          </span>
        </div>

        {/* Description */}
        {description && <p className="mb-8 text-gray-400">{description}</p>}

        {/* CTA */}
        <Link href="/pricing">
          <ExiqusButton size="lg" className="group">
            View Plans
            <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
          </ExiqusButton>
        </Link>

        {/* Subtle footer note */}
        <p className="mt-8 text-gray-500 text-sm">
          Already have access?{' '}
          <Link href="/account" className="text-purple-400 hover:text-purple-300">
            Check your account
          </Link>
        </p>
      </ExiqusCard>
    </div>
  );
}
