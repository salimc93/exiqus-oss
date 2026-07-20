// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

import { ChevronDown, ExternalLink, FolderGit2, GitPullRequest } from 'lucide-react';
import { useState } from 'react';

import { ExiqusCard } from '@/components/ui/exiqus-components';
import { cn } from '@/lib/utils';

import { VisibilityBadge } from './VisibilityBadge';

interface EvidenceTrail {
  source: string;
  url: string;
}

interface ConfidenceLevel {
  level: 'high' | 'moderate' | 'low';
  basis: string;
  note: string;
}

interface ObservablePattern {
  pattern: string;
  value: string;
  visibility: 'observed' | 'not_observed';
  context: string;
  confidence?: ConfidenceLevel;
  evidence_trail?: EvidenceTrail[];
  analysis_source?: 'portfolio' | 'pr';
}

interface ObservablePatternCardProps {
  pattern: ObservablePattern;
  roleContext?: 'junior' | 'mid' | 'senior';
}

export function ObservablePatternCard({ pattern }: ObservablePatternCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const isObserved = pattern.visibility === 'observed';
  const isPortfolio = pattern.analysis_source === 'portfolio';

  // Color scheme based on analysis source
  const colors = isPortfolio
    ? {
        border: 'border-l-violet-500/40',
        hoverBorder: 'hover:border-l-violet-400/60',
        badge: 'bg-violet-500/10 text-violet-300 border-violet-500/30',
        badgeIcon: FolderGit2,
      }
    : {
        border: 'border-l-cyan-500/40',
        hoverBorder: 'hover:border-l-cyan-400/60',
        badge: 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30',
        badgeIcon: GitPullRequest,
      };

  const BadgeIcon = colors.badgeIcon;

  return (
    <ExiqusCard
      className={cn(
        'border-l-2 p-4 transition-all',
        isObserved
          ? `bg-white/[0.02] ${colors.border} ${colors.hoverBorder} hover:bg-white/[0.03]`
          : 'border-l-slate-500/50 bg-slate-900/40 hover:border-l-slate-400/60 hover:bg-slate-900/50'
      )}
      glow="none"
    >
      {/* Compact Header - Always Visible */}
      <button type="button" onClick={() => setIsExpanded(!isExpanded)} className="w-full text-left">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1">
            {/* Source Badge - Show for both observed and not_observed */}
            {pattern.analysis_source && (
              <div className="mb-1.5 flex items-center gap-1.5">
                <span
                  className={cn(
                    'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-medium text-[10px]',
                    isObserved ? colors.badge : 'border-slate-500/30 bg-slate-500/10 text-slate-300'
                  )}
                >
                  <BadgeIcon className="h-2.5 w-2.5" />
                  {isPortfolio ? 'Portfolio' : 'PR Analysis'}
                </span>
              </div>
            )}
            <h4 className="font-semibold text-gray-200 text-sm">{pattern.pattern}</h4>
            <p
              className={cn(
                'mt-0.5 font-medium text-base',
                isObserved ? 'text-gray-300' : 'text-slate-200'
              )}
            >
              {pattern.value}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <VisibilityBadge visibility={pattern.visibility} />
            <ChevronDown
              className={cn(
                'h-4 w-4 text-gray-400 transition-transform',
                isExpanded && 'rotate-180'
              )}
            />
          </div>
        </div>
      </button>

      {/* Expandable Details */}
      {isExpanded && (
        <div className="mt-3 space-y-3 border-white/5 border-t pt-3">
          {/* Context */}
          {pattern.context && <p className="text-gray-400 text-xs">{pattern.context}</p>}

          {/* Confidence Level - Compact */}
          {pattern.confidence && isObserved && (
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  'rounded-full px-2 py-0.5 font-medium text-xs',
                  pattern.confidence.level === 'high' && 'bg-green-500/10 text-green-400',
                  pattern.confidence.level === 'moderate' && 'bg-yellow-500/10 text-yellow-400',
                  pattern.confidence.level === 'low' && 'bg-gray-500/10 text-gray-400'
                )}
              >
                {pattern.confidence.level.charAt(0).toUpperCase() +
                  pattern.confidence.level.slice(1)}{' '}
                Confidence
              </span>
            </div>
          )}

          {/* Evidence Trail - Compact */}
          {pattern.evidence_trail && pattern.evidence_trail.length > 0 && isObserved && (
            <div className="flex items-center gap-2">
              {pattern.evidence_trail.map((evidence, idx) => (
                <a
                  key={idx}
                  href={evidence.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group flex items-center gap-1 text-indigo-400 text-xs transition-colors hover:text-indigo-300"
                >
                  <ExternalLink className="h-3 w-3" />
                  <span>View Evidence</span>
                </a>
              ))}
            </div>
          )}
        </div>
      )}
    </ExiqusCard>
  );
}
