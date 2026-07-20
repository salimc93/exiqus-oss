// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import { useEffect, useRef } from 'react';

import { GradientText } from '@/components/ui/exiqus-components';

export default function VideoDemo() {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    // Set playback speed to 1.5x when component mounts
    if (videoRef.current) {
      videoRef.current.playbackRate = 1.5;
    }
  }, []);

  return (
    <section className="border-white/[0.06] border-t bg-gradient-to-b from-transparent to-white/[0.02] px-4 py-20">
      <div className="mx-auto max-w-7xl">
        <div className="mb-12 text-center">
          <h2 className="mb-4 font-bold text-3xl md:text-4xl">
            <GradientText>See Exiqus in Action</GradientText>
          </h2>
          <p className="mx-auto max-w-2xl text-gray-400 text-lg">
            Watch how Exiqus transforms GitHub portfolios into evidence-based hiring insights in
            under 3 minutes.
          </p>
        </div>

        <div className="relative mx-auto max-w-5xl">
          {/* Video Container */}
          <div className="relative overflow-hidden rounded-2xl border border-white/[0.08] bg-black/40 shadow-2xl backdrop-blur-sm">
            {/* Gradient overlay for depth */}
            <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-purple-900/20 via-transparent to-blue-900/20"></div>

            {/* Video Element */}
            <div className="relative">
              <video
                ref={videoRef}
                className="w-full"
                controls
                controlsList="nodownload nofullscreen noplaybackrate"
                playsInline
                poster="/demo-poster.jpg"
                preload="metadata"
                autoPlay
                muted
                loop
                disablePictureInPicture
              >
                <source src="/demo-video.mp4" type="video/mp4" />
                Your browser does not support the video tag.
              </video>
            </div>

            {/* Video Info Bar */}
            <div className="border-white/[0.08] border-t bg-black/60 px-6 py-4 backdrop-blur-sm">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-gray-200 text-sm">
                    Portfolio Analysis → Candidate Hub Demo
                  </h3>
                  <p className="text-gray-500 text-xs">Full workflow walkthrough</p>
                </div>
                <div className="text-gray-400 text-xs">2:30</div>
              </div>
            </div>
          </div>

          {/* Decorative elements */}
          <div className="absolute -top-10 -left-10 h-40 w-40 animate-float rounded-full bg-purple-600/20 blur-3xl filter"></div>
          <div className="animation-delay-2000 absolute -right-10 -bottom-10 h-40 w-40 animate-float rounded-full bg-blue-600/20 blur-3xl filter"></div>
        </div>

        {/* Feature Callouts Below Video */}
        <div className="mt-12 grid gap-6 md:grid-cols-3">
          <div className="text-center">
            <div className="mb-2 font-bold text-2xl text-purple-400">Portfolio Analysis</div>
            <p className="text-gray-500 text-sm">
              Analyze complete GitHub portfolios with AI-powered insights
            </p>
          </div>
          <div className="text-center">
            <div className="mb-2 font-bold text-2xl text-blue-400">PR Deep Dives</div>
            <p className="text-gray-500 text-sm">
              Extract evidence from real pull request contributions
            </p>
          </div>
          <div className="text-center">
            <div className="mb-2 font-bold text-2xl text-green-400">Candidate Hub</div>
            <p className="text-gray-500 text-sm">
              Unified dashboard for all candidate analysis and insights
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
