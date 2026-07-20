// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

import { Badge } from 'lucide-react';

import { cn } from '@/lib/utils';

interface RoleBadgeProps {
  role: 'junior' | 'mid' | 'senior';
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
}

const roleConfig = {
  junior: {
    label: 'Junior',
    gradient: 'from-emerald-500 to-green-600',
    bgLight: 'bg-emerald-500/10',
    textColor: 'text-emerald-400',
    ring: 'ring-emerald-500/30',
    description: 'Early-career developer showing learning agility',
  },
  mid: {
    label: 'Mid-Level',
    gradient: 'from-indigo-500 to-blue-600',
    bgLight: 'bg-indigo-500/10',
    textColor: 'text-indigo-400',
    ring: 'ring-indigo-500/30',
    description: 'Experienced developer with proven delivery',
  },
  senior: {
    label: 'Senior',
    gradient: 'from-violet-500 to-purple-600',
    bgLight: 'bg-violet-500/10',
    textColor: 'text-violet-400',
    ring: 'ring-violet-500/30',
    description: 'Expert developer with leadership and architectural impact',
  },
};

export function RoleBadge({ role, size = 'md', showIcon = true }: RoleBadgeProps) {
  const config = roleConfig[role];

  const sizeClasses = {
    sm: 'text-xs px-2 py-1',
    md: 'text-sm px-3 py-1.5',
    lg: 'text-base px-4 py-2',
  };

  const iconSizes = {
    sm: 'h-3 w-3',
    md: 'h-4 w-4',
    lg: 'h-5 w-5',
  };

  return (
    <div
      className={cn(
        'inline-flex items-center gap-2 rounded-full font-medium ring-1',
        config.bgLight,
        config.textColor,
        config.ring,
        sizeClasses[size]
      )}
      title={config.description}
    >
      {showIcon && <Badge className={iconSizes[size]} />}
      <span>{config.label}</span>
    </div>
  );
}
