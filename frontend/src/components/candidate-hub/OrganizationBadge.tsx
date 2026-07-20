// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

import { Briefcase, Building2, Rocket, Users } from 'lucide-react';

import { cn } from '@/lib/utils';

interface OrganizationBadgeProps {
  context: 'startup' | 'enterprise' | 'agency' | 'open_source';
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
}

const contextConfig = {
  startup: {
    label: 'Startup',
    icon: Rocket,
    gradient: 'from-purple-600 to-pink-600',
    bgLight: 'bg-purple-500/10',
    textColor: 'text-purple-400',
    ring: 'ring-purple-500/30',
    description: 'Fast iteration & adaptability context',
  },
  enterprise: {
    label: 'Enterprise',
    icon: Building2,
    gradient: 'from-blue-600 to-cyan-600',
    bgLight: 'bg-blue-500/10',
    textColor: 'text-blue-400',
    ring: 'ring-blue-500/30',
    description: 'Architecture patterns & scalability context',
  },
  agency: {
    label: 'Agency',
    icon: Briefcase,
    gradient: 'from-orange-600 to-amber-600',
    bgLight: 'bg-orange-500/10',
    textColor: 'text-orange-400',
    ring: 'ring-orange-500/30',
    description: 'Project variety & client patterns context',
  },
  open_source: {
    label: 'Open Source',
    icon: Users,
    gradient: 'from-green-600 to-emerald-600',
    bgLight: 'bg-green-500/10',
    textColor: 'text-green-400',
    ring: 'ring-green-500/30',
    description: 'Open source collaboration & community context',
  },
};

export function OrganizationBadge({
  context,
  size = 'md',
  showIcon = true,
}: OrganizationBadgeProps) {
  // Normalize context to lowercase and provide fallback
  const normalizedContext = context?.toLowerCase() as
    | 'startup'
    | 'enterprise'
    | 'agency'
    | 'open_source';
  const config = contextConfig[normalizedContext] || contextConfig.enterprise; // Default to enterprise if not found

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

  const Icon = config.icon;

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
      {showIcon && <Icon className={iconSizes[size]} />}
      <span>{config.label}</span>
    </div>
  );
}
