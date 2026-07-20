// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

import { AlertCircle, CheckCircle2 } from 'lucide-react';

import { cn } from '@/lib/utils';

interface VisibilityBadgeProps {
  visibility: 'observed' | 'not_observed';
  size?: 'sm' | 'md';
}

const visibilityConfig = {
  observed: {
    label: 'Observed',
    icon: CheckCircle2,
    bgColor: 'bg-green-500/10',
    textColor: 'text-green-400',
    ring: 'ring-green-500/30',
  },
  not_observed: {
    label: 'Not Observed',
    icon: AlertCircle,
    bgColor: 'bg-gray-500/10',
    textColor: 'text-gray-400',
    ring: 'ring-gray-500/30',
  },
};

export function VisibilityBadge({ visibility, size = 'sm' }: VisibilityBadgeProps) {
  const config = visibilityConfig[visibility];
  const Icon = config.icon;

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5',
    md: 'text-sm px-3 py-1',
  };

  const iconSizes = {
    sm: 'h-3 w-3',
    md: 'h-4 w-4',
  };

  return (
    <div
      className={cn(
        'inline-flex items-center gap-1 rounded-full font-medium ring-1',
        config.bgColor,
        config.textColor,
        config.ring,
        sizeClasses[size]
      )}
    >
      <Icon className={iconSizes[size]} />
      <span>{config.label}</span>
    </div>
  );
}
