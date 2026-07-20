// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

import { AlertCircle, Database, GitBranch } from 'lucide-react';

import { ExiqusCard } from '@/components/ui/exiqus-components';

interface DataScope {
  what_analyzed: string;
  prs_analyzed: number;
  repos_analyzed: number;
  timeline_span: string;
  timeline_label?: string;
  data_volume: 'high' | 'moderate' | 'limited' | 'none';
  not_analyzed: string[];
  important_note: string;
}

interface DataTransparencyBannerProps {
  dataScope: DataScope;
}

export function DataTransparencyBanner({ dataScope }: DataTransparencyBannerProps) {
  return (
    <ExiqusCard className="mb-6 border-amber-500/20 bg-gradient-to-r from-amber-900/10 to-orange-900/10 p-5">
      {/* Header */}
      <div className="mb-4 flex items-start gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-500/10">
          <AlertCircle className="h-5 w-5 text-amber-400" />
        </div>
        <div className="flex-1">
          <h3 className="font-semibold text-amber-300 text-lg">Data Transparency Notice</h3>
          <p className="mt-1 text-amber-400/80 text-sm">{dataScope.important_note}</p>
        </div>
      </div>

      {/* What Was Analyzed */}
      <div className="mb-4 grid gap-4 sm:grid-cols-3">
        <div className="flex items-center gap-2 rounded-lg bg-white/5 px-3 py-2">
          <GitBranch className="h-4 w-4 text-gray-400" />
          <div>
            <p className="text-gray-500 text-xs">Repositories</p>
            <p className="font-semibold text-gray-200 text-sm">{dataScope.repos_analyzed}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 rounded-lg bg-white/5 px-3 py-2">
          <Database className="h-4 w-4 text-gray-400" />
          <div>
            <p className="text-gray-500 text-xs">Pull Requests</p>
            <p className="font-semibold text-gray-200 text-sm">{dataScope.prs_analyzed}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 rounded-lg bg-white/5 px-3 py-2">
          <AlertCircle className="h-4 w-4 text-gray-400" />
          <div>
            <p className="text-gray-500 text-xs">{dataScope.timeline_label || 'Timeline Span'}</p>
            <p className="font-semibold text-gray-200 text-sm">{dataScope.timeline_span}</p>
          </div>
        </div>
      </div>

      {/* What Was NOT Analyzed */}
      {dataScope.not_analyzed && dataScope.not_analyzed.length > 0 && (
        <div className="rounded-lg bg-black/20 p-4">
          <p className="mb-2 font-medium text-gray-400 text-xs">Not Analyzed:</p>
          <ul className="space-y-1">
            {dataScope.not_analyzed.map((item, idx) => (
              <li key={idx} className="flex items-start gap-2 text-gray-500 text-xs">
                <span className="mt-1 h-1 w-1 flex-shrink-0 rounded-full bg-gray-600"></span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </ExiqusCard>
  );
}
