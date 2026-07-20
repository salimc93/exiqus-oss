// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import { ArrowRight, MessageSquare } from 'lucide-react';
import Link from 'next/link';

import { ExiqusButton, ExiqusCard } from '@/components/ui/exiqus-components';

interface InterviewTopic {
  category: string;
  observation: string;
  question: string;
  why_discuss: string;
}

interface InterviewTopicsPreviewProps {
  topics: InterviewTopic[];
  portfolioAnalysisId?: string;
  prAnalysisId?: string;
}

export function InterviewTopicsPreview({
  topics,
  portfolioAnalysisId,
  prAnalysisId,
}: InterviewTopicsPreviewProps) {
  // Determine which analysis to link to (prefer Portfolio, fallback to PR)
  const analysisLink = portfolioAnalysisId
    ? `/portfolio-analyses/${portfolioAnalysisId}`
    : prAnalysisId
      ? `/pr-analyses/${prAnalysisId}`
      : null;

  return (
    <ExiqusCard className="border-l-2 border-l-amber-500/40 p-5" glow="subtle">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <MessageSquare className="h-5 w-5 text-amber-400" />
          <h3 className="font-semibold text-gray-100 text-lg">Interview Topics</h3>
        </div>
        <span className="rounded-full bg-amber-500/10 px-3 py-1 font-medium text-amber-400 text-sm">
          {topics.length} {topics.length === 1 ? 'Topic' : 'Topics'}
        </span>
      </div>

      {/* Topics Preview - Show first 3 */}
      <div className="mb-4 space-y-2">
        {topics.slice(0, 3).map((topic, idx) => (
          <div key={idx} className="flex items-start gap-2 rounded-lg bg-black/20 px-3 py-2">
            <span className="mt-1 text-amber-500 text-xs">•</span>
            <div className="flex-1">
              <span className="mr-2 rounded bg-amber-500/20 px-2 py-0.5 font-medium text-amber-300 text-xs">
                {topic.category}
              </span>
              <p className="mt-1 text-gray-300 text-sm">{topic.observation}</p>
            </div>
          </div>
        ))}
        {topics.length > 3 && (
          <p className="text-gray-500 text-xs">+ {topics.length - 3} more topics...</p>
        )}
      </div>

      {/* CTA to Full Interview Guide */}
      {analysisLink ? (
        <Link href={analysisLink}>
          <ExiqusButton variant="secondary" className="w-full">
            View Full Interview Guide
            <ArrowRight className="ml-2 h-4 w-4" />
          </ExiqusButton>
        </Link>
      ) : (
        <div className="rounded-lg bg-gray-800/50 px-4 py-3 text-center">
          <p className="text-gray-400 text-xs">
            Run a Portfolio or PR Analysis to generate detailed interview questions
          </p>
        </div>
      )}

      {/* Helper Text */}
      <p className="mt-3 text-gray-500 text-xs">
        Full interview guide includes suggested questions, follow-ups, and listening strategies
      </p>
    </ExiqusCard>
  );
}
