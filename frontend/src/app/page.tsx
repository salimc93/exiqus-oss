// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import { ArrowRight, Rocket, Target } from 'lucide-react';
import Image from 'next/image';
import Link from 'next/link';
import { useEffect, useState } from 'react';

import FeaturesGrid from '@/components/landing/features-grid';
import HowItWorks from '@/components/landing/how-it-works';
import PricingPreview from '@/components/landing/pricing-preview';
import VideoDemo from '@/components/landing/video-demo';
import { SoftwareApplicationSchema } from '@/components/seo/json-ld';
import { ExiqusButton, GradientText } from '@/components/ui/exiqus-components';

// Home page - Last updated: 2025-10-27
export default function Home() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <div className="bg-[#0A0A0A] text-white">
      {/* JSON-LD Product Schema for SEO */}
      <SoftwareApplicationSchema />

      {/* Hero Section */}
      <div className="relative min-h-[calc(100vh-12rem)] overflow-hidden">
        {/* Subtle gradient overlay */}
        <div className="absolute inset-0 bg-gradient-to-br from-purple-900/10 via-transparent to-blue-900/10"></div>

        {/* Grid pattern overlay */}
        <div className="absolute inset-0 bg-[url('/grid.svg')] bg-center opacity-5"></div>

        {/* Content */}
        <div className="relative z-10 flex min-h-[calc(100vh-12rem)] flex-col items-center justify-center px-4">
          {/* Logo/Brand with glow effect */}
          <div
            className={`mb-8 transition-all duration-1000 ${mounted ? 'translate-y-0 opacity-100' : 'translate-y-4 opacity-0'}`}
          >
            <div className="relative flex flex-col items-center gap-4">
              {/* Glow effect behind everything */}
              <div className="absolute inset-0 bg-gradient-to-r from-purple-600 to-blue-600 opacity-20 blur-3xl"></div>

              {/* Logo Image - seamlessly blended */}
              <div className="relative">
                <Image
                  src="/exiqus-logo.png"
                  alt="Exiqus Logo"
                  width={1024}
                  height={1024}
                  className="h-40 w-auto drop-shadow-[0_0_40px_rgba(147,51,234,0.7)] md:h-48"
                  priority
                  unoptimized
                />
              </div>
            </div>
          </div>

          {/* Animated tagline */}
          <div
            className={`mb-4 transition-all delay-200 duration-1000 ${mounted ? 'translate-y-0 opacity-100' : 'translate-y-4 opacity-0'}`}
          >
            <h2 className="text-center font-bold text-2xl text-gray-100 md:text-4xl">
              Hire Like Zed Industries: Watch Real Work, Not LeetCode
            </h2>
          </div>

          {/* Subheading with animation */}
          <div
            className={`mb-12 max-w-3xl text-center transition-all delay-300 duration-1000 ${mounted ? 'translate-y-0 opacity-100' : 'translate-y-4 opacity-0'}`}
          >
            <p className="text-gray-400 text-lg leading-relaxed md:text-xl">
              Zed hired 2 developers in 2024-2025 by watching their GitHub for 6-10 months. No
              LeetCode. No whiteboard. Just real work.
            </p>
            <p className="mt-6 text-base text-gray-400 leading-relaxed md:text-lg">
              One developer got hired with a 977-commit debugger PR over 9 months. That&apos;s what
              got them hired. We automate what Zed does manually—analyzing months of real GitHub
              work in minutes.
            </p>
            <p className="mt-6 font-medium text-gray-300 text-lg">
              Generate interview questions only the actual developer could answer. Not LeetCode
              puzzles they memorized.
            </p>
          </div>

          {/* CTA Button */}
          <div
            className={`transition-all delay-400 duration-1000 ${mounted ? 'translate-y-0 opacity-100' : 'translate-y-4 opacity-0'}`}
          >
            <Link href="/signup">
              <div className="group relative">
                {/* Glow effect on hover */}
                <div className="absolute -inset-1 rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 opacity-70 blur-lg transition duration-200 group-hover:opacity-100"></div>
                <ExiqusButton size="lg" className="relative gap-3 px-8 py-4 font-semibold text-lg">
                  <Rocket className="h-5 w-5 transition-transform group-hover:rotate-12" />
                  Get Candidate Insights
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                </ExiqusButton>
              </div>
            </Link>
          </div>

          {/* Unified message */}
          <div
            className={`mt-12 text-center transition-all delay-500 duration-1000 ${mounted ? 'opacity-100' : 'opacity-0'}`}
          >
            <p className="font-medium text-base text-gray-400 md:text-lg">
              The best companies skip interviews and watch real work.
              <br />
              We make that possible in minutes instead of months.
            </p>
          </div>
        </div>

        {/* Animated gradient orbs - more subtle */}
        <div className="absolute top-40 -left-20 h-96 w-96 animate-float rounded-full bg-purple-600/20 blur-3xl filter"></div>
        <div className="animation-delay-2000 absolute -right-20 bottom-40 h-96 w-96 animate-float rounded-full bg-blue-600/20 blur-3xl filter"></div>
      </div>

      {/* The $4,700 Problem Section */}
      <section className="border-white/[0.06] border-t bg-gradient-to-b from-white/[0.02] to-transparent px-4 py-20">
        <div className="mx-auto max-w-7xl">
          <div className="mb-12 text-center">
            <h2 className="mb-4 font-bold text-3xl md:text-4xl">
              <GradientText>The Standard Interview Process is Broken</GradientText>
            </h2>
            <p className="mx-auto max-w-2xl text-gray-400 text-lg">
              While Zed hires by watching real work, you&apos;re spending $4,700 per hire on broken
              interviews with LeetCode puzzles that have zero validity research.
            </p>
          </div>

          <div className="mx-auto grid max-w-5xl gap-8 md:grid-cols-3">
            {/* Cost Card */}
            <div className="rounded-xl border border-white/[0.08] bg-gradient-to-br from-red-900/10 to-transparent p-8 text-center">
              <div className="mb-4 font-bold text-5xl text-red-400">$4,700</div>
              <div className="mb-2 font-semibold text-gray-200 text-lg">Cost Per Hire</div>
              <p className="text-gray-500 text-sm">
                Engineering time, recruiter hours, and multiple interview rounds add up fast
              </p>
            </div>

            {/* Time Card */}
            <div className="rounded-xl border border-white/[0.08] bg-gradient-to-br from-amber-900/10 to-transparent p-8 text-center">
              <div className="mb-4 font-bold text-5xl text-amber-400">28</div>
              <div className="mb-2 font-semibold text-gray-200 text-lg">Hours Per Hire</div>
              <p className="text-gray-500 text-sm">
                Multiple rounds, technical puzzles, and coordination drain your team
              </p>
            </div>

            {/* Drop-off Card */}
            <div className="rounded-xl border border-white/[0.08] bg-gradient-to-br from-orange-900/10 to-transparent p-8">
              <div className="mb-4 text-center font-bold text-3xl text-orange-400">
                The Best Candidates Walk Away
              </div>
              <div className="space-y-3 text-gray-400 text-sm">
                <div>
                  <span className="font-semibold text-orange-300">25%</span> drop out during the
                  interview phase (highest of any hiring stage)
                </div>
                <div>
                  <span className="font-semibold text-orange-300">72%</span> abandon processes with
                  poor communication
                </div>
                <div>
                  <span className="font-semibold text-orange-300">60%</span> quit if the process
                  feels too rigid or time-consuming
                </div>
              </div>
              <p className="mt-4 text-gray-500 text-xs">
                With AI tools making traditional interviews easier to game, companies need
                evidence-based alternatives more than ever
              </p>
            </div>
          </div>

          {/* Solution */}
          <div className="mt-16 text-center">
            <div className="mx-auto max-w-3xl rounded-xl border border-white/[0.08] bg-gradient-to-br from-green-900/10 to-transparent p-8">
              <h3 className="mb-4 font-bold text-2xl text-gray-100">
                What if you could see months of real work in 5 minutes?
              </h3>
              <p className="mb-4 text-gray-400 text-lg">
                We analyze GitHub portfolios and PRs to show you what developers actually build. Not
                LeetCode puzzles. Real work.
              </p>
              <div className="mb-6 space-y-4 text-left">
                <div className="rounded-lg border border-purple-500/20 bg-purple-900/10 p-4">
                  <p className="mb-3 font-semibold text-purple-400 text-sm">
                    Example: Senior Developer (Hired by Zed)
                  </p>
                  <div className="mb-3 space-y-1 text-gray-400 text-xs">
                    <p className="font-semibold">Evidence Extracted:</p>
                    <p>
                      PR #13433 &apos;Debugger implementation&apos; - 977 commits - 25,837 lines -
                      Zed&apos;s most requested feature
                    </p>
                  </div>
                  <div className="space-y-2">
                    <p className="font-semibold text-purple-300 text-xs">Generated Question:</p>
                    <p className="text-gray-300 text-sm italic">
                      &quot;Walk me through your experience with the Debugger implementation PR
                      #13433—how did you approach taking on this 977-commit, 25,837-line feature
                      that was Zed&apos;s most requested capability?&quot;
                    </p>
                    <p className="text-gray-500 text-xs">
                      📍 Category: technical • Context: KEY HIRING SIGNAL - most substantial
                      contribution
                    </p>
                  </div>
                </div>
                <div className="rounded-lg border border-blue-500/20 bg-blue-900/10 p-4">
                  <p className="mb-3 font-semibold text-blue-400 text-sm">
                    Example: Junior Developer
                  </p>
                  <div className="mb-3 space-y-1 text-gray-400 text-xs">
                    <p className="font-semibold">Evidence Extracted:</p>
                    <p>
                      223 commits in 22 days • Python exclusively •
                      &apos;Programmig_PYTHON_SoftUni&apos; repository (97% of all public activity)
                    </p>
                  </div>
                  <div className="space-y-2">
                    <p className="font-semibold text-blue-300 text-xs">Generated Question:</p>
                    <p className="text-gray-300 text-sm italic">
                      &quot;Your &apos;Programmig_PYTHON_SoftUni&apos; repository shows 223 commits
                      over 22 days, which suggests intensive learning. Walk me through how you
                      approached learning Python fundamentals and what your typical development
                      workflow looked like during this period.&quot;
                    </p>
                    <p className="text-gray-500 text-xs">
                      📍 Category: learning-agility • Context: Reveals ability to onboard onto new
                      systems
                    </p>
                  </div>
                </div>
              </div>
              <p className="mb-6 font-medium text-base text-gray-300">
                Both examples generate questions only the actual developer could answer. Not
                LeetCode puzzles they memorized.
              </p>
              <Link href="/signup">
                <ExiqusButton size="lg" className="gap-2">
                  <Target className="h-5 w-5" />
                  Try the Zed Approach - Analyze Free
                  <ArrowRight className="h-4 w-4" />
                </ExiqusButton>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Video Demo Section */}
      <VideoDemo />

      {/* How it Works Section */}
      <section className="border-white/[0.06] border-t px-4 py-20">
        <div className="mx-auto max-w-7xl">
          <div className="mb-16 text-center">
            <h2 className="mb-4 font-bold text-3xl md:text-4xl">
              <GradientText>How Evidence Becomes Insight</GradientText>
            </h2>
            <p className="mx-auto max-w-2xl text-gray-400 text-lg">
              We turn GitHub portfolios into structured evidence and contextual interview questions.
              No scores, no grades—just facts about real work.
            </p>
          </div>
          <HowItWorks />
        </div>
      </section>

      {/* Features Section */}
      <section className="border-white/[0.06] border-t bg-white/[0.02] px-4 py-20">
        <div className="mx-auto max-w-7xl">
          <div className="mb-16 text-center">
            <h2 className="mb-4 font-bold text-3xl md:text-4xl">
              <GradientText>Evidence Over Inference. Facts Over Feelings.</GradientText>
            </h2>
            <p className="mx-auto max-w-2xl text-gray-400 text-lg">
              Analyze complete developer portfolios through Portfolio Analysis, PR contributions,
              and repository deep dives—all grounded in observable work.
            </p>
          </div>
          <FeaturesGrid />
        </div>
      </section>

      {/* Pricing Preview Section */}
      <section className="border-white/[0.06] border-t px-4 py-20">
        <div className="mx-auto max-w-7xl">
          <PricingPreview />
        </div>
      </section>

      {/* Final CTA */}
      <section className="border-white/[0.06] border-t bg-gradient-to-t from-purple-900/10 to-transparent px-4 py-20">
        <div className="mx-auto max-w-4xl text-center">
          <h2 className="mb-6 font-bold text-3xl md:text-4xl">
            <GradientText>
              Stop Guessing Through Puzzles. Start Hiring Through Evidence.
            </GradientText>
          </h2>
          <p className="mb-8 text-gray-400 text-lg">
            Every great hire leaves evidence. Exiqus makes it visible.
          </p>
          <Link href="/signup">
            <ExiqusButton size="lg" className="gap-2">
              <Target className="h-5 w-5" />
              Start Free Analysis
              <ArrowRight className="h-4 w-4" />
            </ExiqusButton>
          </Link>
        </div>
      </section>
    </div>
  );
}
