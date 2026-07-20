// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

import { FolderGit2, GitPullRequest, Sparkles } from 'lucide-react';

import { ExiqusCard } from '@/components/ui/exiqus-components';

interface VisibleStrength {
  title: string;
  evidence: string;
  what_this_shows: string;
  source?: 'portfolio' | 'pr';
}

interface StrengthCardProps {
  strength: VisibleStrength;
}

export function StrengthCard({ strength }: StrengthCardProps) {
  const isPortfolio = strength.source === 'portfolio';

  // Color scheme based on analysis source
  const colors = isPortfolio
    ? {
        border: 'border-l-violet-500/40 hover:border-l-violet-400/60',
        icon: 'text-violet-400',
        badge: 'bg-violet-500/10 text-violet-300 border-violet-500/30',
        badgeIcon: FolderGit2,
      }
    : {
        border: 'border-l-cyan-500/40 hover:border-l-cyan-400/60',
        icon: 'text-cyan-400',
        badge: 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30',
        badgeIcon: GitPullRequest,
      };

  const BadgeIcon = colors.badgeIcon;

  return (
    <ExiqusCard className={`border-l-2 ${colors.border} p-4 transition-all`} glow="none">
      <div className="flex items-start gap-2">
        <Sparkles className={`mt-0.5 h-4 w-4 flex-shrink-0 ${colors.icon}`} />
        <div className="flex-1">
          {/* Source Badge */}
          <div className="mb-1.5 flex items-center gap-1.5">
            <span
              className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-medium text-[10px] ${colors.badge}`}
            >
              <BadgeIcon className="h-2.5 w-2.5" />
              {isPortfolio ? 'Portfolio' : 'PR Analysis'}
            </span>
          </div>
          <h4 className="font-semibold text-gray-100 text-sm">{strength.title}</h4>
          <p className="mt-1 text-gray-400 text-xs">{strength.evidence}</p>
        </div>
      </div>
    </ExiqusCard>
  );
}
