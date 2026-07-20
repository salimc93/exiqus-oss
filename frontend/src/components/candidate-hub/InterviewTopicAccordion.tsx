// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import { ChevronDown, FolderGit2, GitPullRequest, MessageSquare } from 'lucide-react';
import { useState } from 'react';

import { ExiqusCard } from '@/components/ui/exiqus-components';
import { cn } from '@/lib/utils';

interface InterviewTopic {
  category: string;
  observation: string;
  question: string;
  why_discuss: string;
}

interface InterviewTopicAccordionProps {
  topic: InterviewTopic;
  analysisType?: 'portfolio' | 'pr';
}

export function InterviewTopicAccordion({
  topic,
  analysisType = 'pr',
}: InterviewTopicAccordionProps) {
  const [isOpen, setIsOpen] = useState(false);
  const isPortfolio = analysisType === 'portfolio';

  // Color scheme based on analysis type
  const colors = isPortfolio
    ? {
        border: 'border-l-violet-500/40',
        icon: 'text-violet-400',
        badge: 'bg-violet-500/10 text-violet-400',
        sourceBadge: 'bg-violet-500/10 text-violet-300 border-violet-500/30',
        box: 'bg-violet-500/10',
        text: 'text-violet-400',
        textLight: 'text-violet-300/80',
        badgeIcon: FolderGit2,
      }
    : {
        border: 'border-l-cyan-500/40',
        icon: 'text-cyan-400',
        badge: 'bg-cyan-500/10 text-cyan-400',
        sourceBadge: 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30',
        box: 'bg-cyan-500/10',
        text: 'text-cyan-400',
        textLight: 'text-cyan-300/80',
        badgeIcon: GitPullRequest,
      };

  const BadgeIcon = colors.badgeIcon;

  return (
    <ExiqusCard
      className={`border-l-2 ${colors.border} overflow-hidden p-0 transition-all`}
      glow="subtle"
    >
      {/* Header - Clickable */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-start gap-3 p-4 text-left transition-colors hover:bg-white/5"
      >
        <MessageSquare className={cn('mt-0.5 h-4 w-4 flex-shrink-0', colors.icon)} />
        <div className="flex-1">
          <div className="mb-1 flex items-center gap-2">
            <span
              className={cn(
                'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-medium text-[10px]',
                colors.sourceBadge
              )}
            >
              <BadgeIcon className="h-2.5 w-2.5" />
              {isPortfolio ? 'Portfolio' : 'PR Analysis'}
            </span>
            <span className={cn('rounded-full px-2 py-0.5 font-medium text-xs', colors.badge)}>
              {topic.category}
            </span>
          </div>
          <p className="font-medium text-gray-200 text-sm">{topic.observation}</p>
        </div>
        <ChevronDown
          className={cn(
            'h-5 w-5 flex-shrink-0 text-gray-400 transition-transform',
            isOpen && 'rotate-180'
          )}
        />
      </button>

      {/* Expandable Content */}
      {isOpen && (
        <div className="border-white/5 border-t bg-black/20 p-4">
          <div className="mb-3">
            <p className="mb-1 font-medium text-gray-500 text-xs">Suggested Question:</p>
            <p className="text-gray-300 text-sm">{topic.question}</p>
          </div>
          <div className={cn('rounded-lg px-3 py-2', colors.box)}>
            <p className={cn('mb-1 font-medium text-xs', colors.text)}>Why Discuss This:</p>
            <p className={cn('text-xs', colors.textLight)}>{topic.why_discuss}</p>
          </div>
        </div>
      )}
    </ExiqusCard>
  );
}
