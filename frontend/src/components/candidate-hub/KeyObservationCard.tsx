// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

import { FolderGit2, GitPullRequest, Lightbulb } from 'lucide-react';

import { ExiqusCard } from '@/components/ui/exiqus-components';
import { renderBoldSafe } from '@/lib/sanitize';

interface KeyObservation {
  text: string;
  source: 'portfolio' | 'pr';
}

interface KeyObservationCardProps {
  observation: KeyObservation;
}

export function KeyObservationCard({ observation }: KeyObservationCardProps) {
  const isPortfolio = observation.source === 'portfolio';

  // Convert markdown bold (**text**) to HTML <strong> tags - XSS safe
  const renderText = (text: string) => {
    return <span dangerouslySetInnerHTML={{ __html: renderBoldSafe(text) }} />;
  };

  // Color scheme based on analysis source
  const colors = isPortfolio
    ? {
        border: 'border-l-violet-500/40',
        icon: 'text-violet-400',
        badge: 'bg-violet-500/10 text-violet-300 border-violet-500/30',
        badgeIcon: FolderGit2,
      }
    : {
        border: 'border-l-cyan-500/40',
        icon: 'text-cyan-400',
        badge: 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30',
        badgeIcon: GitPullRequest,
      };

  const BadgeIcon = colors.badgeIcon;

  return (
    <ExiqusCard
      className={`border-l-2 ${colors.border} bg-white/[0.02] p-4 transition-all hover:bg-white/[0.03]`}
      glow="none"
    >
      <div className="flex items-start gap-3">
        <Lightbulb className={`mt-0.5 h-5 w-5 flex-shrink-0 ${colors.icon}`} />
        <div className="flex-1">
          {/* Source Badge */}
          <div className="mb-2 flex items-center gap-1.5">
            <span
              className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-medium text-[10px] ${colors.badge}`}
            >
              <BadgeIcon className="h-2.5 w-2.5" />
              {isPortfolio ? 'Portfolio' : 'PR Analysis'}
            </span>
          </div>
          <p className="text-gray-300 text-sm leading-relaxed">{renderText(observation.text)}</p>
        </div>
      </div>
    </ExiqusCard>
  );
}
