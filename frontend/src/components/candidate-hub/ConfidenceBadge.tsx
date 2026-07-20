// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

import { AlertCircle, CheckCircle2, Info } from 'lucide-react';

import { cn } from '@/lib/utils';

interface ConfidenceBadgeProps {
  level: 'high' | 'moderate' | 'low';
  basis: string;
  note: string;
  size?: 'sm' | 'md';
}

const confidenceConfig = {
  high: {
    label: 'High Confidence',
    icon: CheckCircle2,
    bgColor: 'bg-green-500/10',
    textColor: 'text-green-400',
    ring: 'ring-green-500/30',
    borderStyle: 'border-green-500/50',
  },
  moderate: {
    label: 'Moderate Confidence',
    icon: AlertCircle,
    bgColor: 'bg-amber-500/10',
    textColor: 'text-amber-400',
    ring: 'ring-amber-500/30',
    borderStyle: 'border-amber-500/50 border-dashed',
  },
  low: {
    label: 'Limited Data',
    icon: Info,
    bgColor: 'bg-gray-500/10',
    textColor: 'text-gray-400',
    ring: 'ring-gray-500/30',
    borderStyle: 'border-gray-500/50 border-dotted',
  },
};

export function ConfidenceBadge({ level, basis, note, size = 'sm' }: ConfidenceBadgeProps) {
  const config = confidenceConfig[level];
  const Icon = config.icon;

  const sizeClasses = {
    sm: 'text-xs px-2 py-1',
    md: 'text-sm px-3 py-1.5',
  };

  const iconSizes = {
    sm: 'h-3 w-3',
    md: 'h-4 w-4',
  };

  return (
    <div
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full font-medium ring-1',
        config.bgColor,
        config.textColor,
        config.ring,
        sizeClasses[size]
      )}
      title={`${basis} - ${note}`}
    >
      <Icon className={iconSizes[size]} />
      <span>{config.label}</span>
    </div>
  );
}
