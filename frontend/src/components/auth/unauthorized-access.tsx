// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import { Coffee, Lock, Rocket, Shield, Sparkles, Zap } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { ExiqusButton, ExiqusCard } from '@/components/ui/exiqus-components';

const REPO_MESSAGES = [
  {
    icon: Lock,
    title: 'Repository Analysis Credentials Required! 🔍',
    message:
      'Only verified users can access our AI-powered repository analysis platform. Time to authenticate!',
    action: 'Show my analysis badge!',
  },
  {
    icon: Coffee,
    title: 'Code Analysis Lounge is Members Only! ☕',
    message:
      'This exclusive evidence-based analysis lounge requires authentication. Your repository insights are waiting inside!',
    action: 'Let me in the analysis room!',
  },
  {
    icon: Shield,
    title: 'Repository Intelligence Clearance Needed! 🛡️',
    message:
      'Our AI guardians protect valuable repository insights. Authenticate to access the evidence treasure trove!',
    action: 'Grant me clearance!',
  },
  {
    icon: Zap,
    title: 'Analysis Power Levels Low! ⚡',
    message:
      'Recharge your analysis abilities by logging in. The Exiqus evidence engine is ready to supercharge your insights!',
    action: 'Power up my analysis game!',
  },
];

const PORTFOLIO_MESSAGES = [
  {
    icon: Lock,
    title: 'Portfolio Analysis Access Required! 🔍',
    message:
      'Only verified users can access developer portfolio analysis. Sign in to view this candidate insight!',
    action: 'Show me the portfolio!',
  },
  {
    icon: Coffee,
    title: 'Portfolio Intelligence Lounge is Members Only! ☕',
    message:
      'This exclusive candidate portfolio analysis requires authentication. The insights are waiting inside!',
    action: 'Let me see the analysis!',
  },
  {
    icon: Shield,
    title: 'Portfolio Intelligence Clearance Needed! 🛡️',
    message:
      'Our AI guardians protect valuable candidate insights. Authenticate to access this portfolio analysis!',
    action: 'Grant me clearance!',
  },
  {
    icon: Sparkles,
    title: 'Portfolio Magic Requires Login! ✨',
    message:
      'Unlock the mystical powers of AI-driven developer insights. Your portfolio insights await!',
    action: 'Activate portfolio analysis!',
  },
];

const PR_MESSAGES = [
  {
    icon: Lock,
    title: 'PR Analysis Access Required! 🔍',
    message:
      'Only verified users can access PR collaboration analysis. Sign in to view this candidate insight!',
    action: 'Show me the PR insights!',
  },
  {
    icon: Coffee,
    title: 'PR Intelligence Lounge is Members Only! ☕',
    message:
      'This exclusive PR analysis requires authentication. The collaboration insights are waiting inside!',
    action: 'Let me see the analysis!',
  },
  {
    icon: Shield,
    title: 'PR Intelligence Clearance Needed! 🛡️',
    message:
      'Our AI guardians protect valuable PR insights. Authenticate to access this collaboration analysis!',
    action: 'Grant me clearance!',
  },
  {
    icon: Rocket,
    title: 'PR Analysis Mission Unauthorized! 🚀',
    message:
      'PR Mission Control requires authentication before launching your collaboration insights exploration!',
    action: 'Begin PR analysis!',
  },
];

const MESSAGE_SETS = {
  repo: REPO_MESSAGES,
  portfolio: PORTFOLIO_MESSAGES,
  pr: PR_MESSAGES,
};

interface UnauthorizedAccessProps {
  context?: 'repo' | 'portfolio' | 'pr';
}

export function UnauthorizedAccess({ context = 'repo' }: UnauthorizedAccessProps = {}) {
  const router = useRouter();
  const messages = MESSAGE_SETS[context];
  const [message, setMessage] = useState(messages[0]);
  const [isRedirecting, setIsRedirecting] = useState(false);

  useEffect(() => {
    // Pick a random message from the appropriate set
    const randomMessage = messages[Math.floor(Math.random() * messages.length)];
    setMessage(randomMessage);
  }, [messages]);

  const handleLogin = () => {
    setIsRedirecting(true);
    // Save the intended destination
    const currentPath = window.location.pathname;
    sessionStorage.setItem('redirectAfterLogin', currentPath);

    // Add a small delay for the animation
    setTimeout(() => {
      router.push('/login');
    }, 300);
  };

  const Icon = message.icon;

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0A0A0A] p-4">
      {/* Subtle gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-br from-purple-900/10 via-transparent to-blue-900/10"></div>

      {/* Animated gradient orbs */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 h-80 w-80 animate-float rounded-full bg-purple-600/20 blur-3xl filter"></div>
        <div className="animation-delay-2000 absolute -bottom-40 -left-40 h-80 w-80 animate-float rounded-full bg-blue-600/20 blur-3xl filter"></div>
      </div>

      <ExiqusCard
        className="fade-in slide-in-from-bottom-4 relative z-10 w-full max-w-md animate-in p-8 duration-500"
        glow="purple"
      >
        <div className="text-center">
          <div className="mb-6 flex justify-center">
            <div className="relative">
              <div className="absolute inset-0 animate-pulse rounded-full bg-gradient-to-r from-purple-600 to-pink-600 opacity-60 blur-xl" />
              <div className="relative rounded-full bg-[#1A1A1A] p-4 shadow-lg">
                <Icon className="h-12 w-12 text-purple-400" />
              </div>
            </div>
          </div>

          <h2 className="mb-3 bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text font-bold text-2xl text-transparent">
            {message.title}
          </h2>

          <p className="mb-6 text-gray-400 leading-relaxed">{message.message}</p>

          <ExiqusButton onClick={handleLogin} disabled={isRedirecting} className="w-full" size="lg">
            {isRedirecting ? (
              <>
                <Sparkles className="mr-2 h-4 w-4 animate-spin" />
                Redirecting to login...
              </>
            ) : (
              message.action
            )}
          </ExiqusButton>

          <p className="mt-4 text-gray-500 text-sm">
            Don&apos;t have an account?{' '}
            <button
              type="button"
              className="font-semibold text-purple-400 transition-colors hover:text-purple-300"
              onClick={() => router.push('/signup')}
            >
              Start analyzing repositories
            </button>
          </p>
        </div>
      </ExiqusCard>
    </div>
  );
}
