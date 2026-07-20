// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

import type { LucideIcon } from 'lucide-react';
import React from 'react';

import { cn } from '@/lib/utils';

// Exiqus Card Component - Clean, modern design
export const ExiqusCard = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & {
    hover?: boolean;
    glow?: 'purple' | 'blue' | 'green' | 'subtle' | 'hover' | 'none';
  }
>(({ className, hover = true, glow = 'none', ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      'rounded-lg border border-white/[0.06] bg-[#111111]',
      hover && 'transition-all duration-200 hover:border-white/[0.09] hover:bg-[#1A1A1A]',
      glow === 'purple' && 'glow-purple',
      glow === 'blue' && 'glow-blue',
      glow === 'green' && 'glow-green',
      glow === 'subtle' && 'glow-subtle',
      glow === 'hover' && 'glow-hover',
      className
    )}
    {...props}
  />
));
ExiqusCard.displayName = 'ExiqusCard';

// Exiqus Button Component
export interface ExiqusButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'outline';
  size?: 'sm' | 'md' | 'lg';
}

export const ExiqusButton = React.forwardRef<HTMLButtonElement, ExiqusButtonProps>(
  ({ className, variant = 'primary', size = 'md', ...props }, ref) => {
    const variants = {
      primary: 'bg-gradient-to-r from-purple-600 to-blue-600 text-white hover:opacity-90',
      secondary: 'bg-white/[0.06] hover:bg-white/[0.09] text-white border border-white/[0.09]',
      ghost: 'text-gray-400 hover:text-white',
      outline: 'border border-white/[0.09] text-gray-300 hover:bg-white/[0.06] hover:text-white',
    };

    const sizes = {
      sm: 'px-3 py-1.5 text-sm',
      md: 'px-4 py-2 text-base',
      lg: 'px-6 py-3 text-lg',
    };

    return (
      <button
        type="button"
        ref={ref}
        className={cn(
          'rounded-md font-medium transition-all duration-200',
          variants[variant],
          sizes[size],
          className
        )}
        {...props}
      />
    );
  }
);
ExiqusButton.displayName = 'ExiqusButton';

// Exiqus Badge Component
export interface ExiqusBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info';
}

export const ExiqusBadge = React.forwardRef<HTMLSpanElement, ExiqusBadgeProps>(
  ({ className, variant = 'default', ...props }, ref) => {
    const variants = {
      default: 'bg-white/[0.06] text-gray-300 border-white/[0.09]',
      success: 'bg-green-500/10 text-green-400 border-green-500/20',
      warning: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
      error: 'bg-red-500/10 text-red-400 border-red-500/20',
      info: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    };

    return (
      <span
        ref={ref}
        className={cn(
          'inline-flex items-center rounded-md border px-2 py-1 font-medium text-xs',
          variants[variant],
          className
        )}
        {...props}
      />
    );
  }
);
ExiqusBadge.displayName = 'ExiqusBadge';

// Exiqus Section Header
export interface ExiqusSectionHeaderProps {
  title: string;
  description?: string;
  icon?: LucideIcon;
  action?: React.ReactNode;
}

export const ExiqusSectionHeader: React.FC<ExiqusSectionHeaderProps> = ({
  title,
  description,
  icon: Icon,
  action,
}) => (
  <div className="mb-6 flex items-start justify-between">
    <div className="space-y-1">
      <h2 className="flex items-center gap-3 font-semibold text-2xl">
        {Icon && (
          <div className="rounded-lg bg-white/[0.06] p-2">
            <Icon className="h-5 w-5 text-gray-400" />
          </div>
        )}
        {title}
      </h2>
      {description && <p className="text-gray-400 text-sm">{description}</p>}
    </div>
    {action && <div>{action}</div>}
  </div>
);

// Exiqus Metric Card
export interface ExiqusMetricProps {
  label: string;
  value: string | number;
  icon?: LucideIcon;
  trend?: 'up' | 'down' | 'neutral';
  color?: 'purple' | 'blue' | 'green' | 'amber' | 'red';
  onClick?: () => void;
}

export const ExiqusMetric: React.FC<ExiqusMetricProps> = ({
  label,
  value,
  icon: Icon,
  trend,
  color = 'purple',
  onClick,
}) => {
  const colors = {
    purple: 'from-purple-500/10 to-purple-600/10',
    blue: 'from-blue-500/10 to-blue-600/10',
    green: 'from-green-500/10 to-green-600/10',
    amber: 'from-amber-500/10 to-amber-600/10',
    red: 'from-red-500/10 to-red-600/10',
  };

  const iconColors = {
    purple: 'text-purple-500',
    blue: 'text-blue-500',
    green: 'text-green-500',
    amber: 'text-amber-500',
    red: 'text-red-500',
  };

  return (
    <ExiqusCard
      className={cn(
        'group relative isolate overflow-hidden',
        onClick && 'cursor-pointer transition-transform hover:scale-105'
      )}
      onClick={onClick}
    >
      <div
        className={cn('absolute inset-0 -z-10 bg-gradient-to-br', colors[color], 'opacity-50')}
      />
      <div className="relative z-10 p-6">
        <div className="mb-4 flex items-start justify-between">
          {Icon && (
            <div className="rounded-lg bg-white/[0.06] p-2">
              <Icon className={cn('h-5 w-5', iconColors[color])} />
            </div>
          )}
          {trend && (
            <span
              className={cn(
                'font-medium text-xs',
                trend === 'up'
                  ? 'text-green-400'
                  : trend === 'down'
                    ? 'text-red-400'
                    : 'text-gray-400'
              )}
            >
              {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'}
            </span>
          )}
        </div>
        <div className="space-y-1">
          <p className="font-bold text-3xl">{value}</p>
          <p className="text-gray-400 text-sm">{label}</p>
        </div>
      </div>
    </ExiqusCard>
  );
};

// Exiqus Empty State
export interface ExiqusEmptyStateProps {
  icon: LucideIcon;
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export const ExiqusEmptyState: React.FC<ExiqusEmptyStateProps> = ({
  icon: Icon,
  title,
  description,
  action,
}) => (
  <ExiqusCard className="border-dashed">
    <div className="p-12 text-center">
      <Icon className="mx-auto mb-4 h-12 w-12 text-gray-600" />
      <h3 className="mb-2 font-medium text-lg">{title}</h3>
      {description && <p className="mb-4 text-gray-400 text-sm">{description}</p>}
      {action}
    </div>
  </ExiqusCard>
);

// Gradient Text Component
export const GradientText: React.FC<React.HTMLAttributes<HTMLSpanElement>> = ({
  className,
  ...props
}) => (
  <span
    className={cn(
      'bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent',
      className
    )}
    {...props}
  />
);

// Exiqus Tab Navigation
export interface ExiqusTabsProps {
  tabs: Array<{
    id: string;
    label: string;
    icon?: LucideIcon;
  }>;
  activeTab: string;
  onChange: (tabId: string) => void;
}

export const ExiqusTabs: React.FC<ExiqusTabsProps> = ({ tabs, activeTab, onChange }) => (
  <div className="overflow-x-auto rounded-lg bg-white/[0.03] p-1">
    <div className="inline-flex min-w-max items-center gap-1">
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;
        return (
          <button
            type="button"
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={cn(
              'relative isolate flex items-center gap-2 rounded-md px-3 py-2.5 font-medium text-sm transition-all duration-200 sm:px-4',
              isActive
                ? 'bg-gradient-to-r from-purple-500/20 to-blue-500/20 text-white shadow-lg'
                : 'text-gray-400 hover:bg-white/[0.03] hover:text-gray-200'
            )}
          >
            {isActive && (
              <div className="absolute inset-0 -z-10 rounded-md bg-gradient-to-r from-purple-500/10 to-blue-500/10 blur-md" />
            )}
            <span className="relative z-10 flex items-center gap-2">
              {tab.icon && (
                <tab.icon
                  className={cn('h-4 w-4 transition-colors', isActive ? 'text-purple-400' : '')}
                />
              )}
              {tab.label}
            </span>
            {isActive && (
              <div className="absolute inset-x-4 bottom-0 h-[2px] bg-gradient-to-r from-purple-400 to-blue-400" />
            )}
          </button>
        );
      })}
    </div>
  </div>
);
