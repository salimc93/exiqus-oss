// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import {
  AlertCircle,
  AlertTriangle,
  BookOpen,
  Brain,
  Bug,
  Building,
  CheckCircle,
  ChevronDown,
  ChevronUp,
  Code2,
  Cog,
  FileCode,
  Gauge,
  GitBranch,
  GitPullRequest,
  Info,
  Layers,
  MessageSquare,
  Package,
  RefreshCw,
  Search,
  Shield,
  Sparkles,
  TestTube,
  TrendingUp,
  Users,
  Zap,
} from 'lucide-react';
import { useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import type { EvidencePatternModel } from '@/types';

interface EvidenceCardProps {
  title: string;
  icon: React.ReactNode;
  patterns: EvidencePatternModel[];
  confidence: string;
  summary: string;
  insights: string[];
  flags?: {
    type: 'green' | 'red';
    description: string;
    evidence?: string[];
  }[];
  limitations?: string[];
  color: string; // e.g., "indigo", "violet", "cyan", "orange"
}

// Enhanced pattern icons based on specific pattern names
const getPatternIcon = (patternName: string, type: string) => {
  // First, check for specific pattern name matches (case-insensitive)
  const nameLower = patternName.toLowerCase();

  // 🚫 HANDLE LEGACY GENERIC "COMMIT QUALITY" - Give them distinct icons by context
  if (nameLower.includes('commit quality') || nameLower === 'commit quality') {
    // Use evidence content to differentiate - this is a fallback for existing bad data
    return <GitBranch className="h-4 w-4 text-orange-600" />;
  }

  // ✅ NEW SPECIFIC PATTERN NAMES (from our updated requirements)
  if (nameLower.includes('bug fix methodology')) {
    return <Bug className="h-4 w-4 text-red-600" />;
  }

  if (nameLower.includes('refactoring discipline')) {
    return <RefreshCw className="h-4 w-4 text-blue-600" />;
  }

  if (nameLower.includes('test infrastructure')) {
    return <TestTube className="h-4 w-4 text-green-600" />;
  }

  if (nameLower.includes('feature implementation')) {
    return <Package className="h-4 w-4 text-purple-600" />;
  }

  if (nameLower.includes('code maintenance')) {
    return <Cog className="h-4 w-4 text-gray-600" />;
  }

  if (nameLower.includes('cross-language integration')) {
    return <Layers className="h-4 w-4 text-cyan-600" />;
  }

  if (nameLower.includes('architecture evolution')) {
    return <Building className="h-4 w-4 text-slate-600" />;
  }

  // 🔍 GENERIC KEYWORD MATCHING (for fallback)
  // Bug fixing patterns
  if (nameLower.includes('bug') || nameLower.includes('fix')) {
    return <Bug className="h-4 w-4 text-red-600" />;
  }

  // Refactoring patterns
  if (
    nameLower.includes('refactor') ||
    nameLower.includes('cleanup') ||
    nameLower.includes('improve')
  ) {
    return <RefreshCw className="h-4 w-4 text-blue-600" />;
  }

  // Testing patterns
  if (nameLower.includes('test') || nameLower.includes('spec') || nameLower.includes('coverage')) {
    return <TestTube className="h-4 w-4 text-green-600" />;
  }

  // CI/CD and automation patterns
  if (
    nameLower.includes('ci') ||
    nameLower.includes('cd') ||
    nameLower.includes('pipeline') ||
    nameLower.includes('deploy')
  ) {
    return <Cog className="h-4 w-4 text-purple-600" />;
  }

  // Security patterns
  if (
    nameLower.includes('security') ||
    nameLower.includes('auth') ||
    nameLower.includes('encrypt')
  ) {
    return <Shield className="h-4 w-4 text-yellow-600" />;
  }

  // Error handling patterns
  if (
    nameLower.includes('error') ||
    nameLower.includes('exception') ||
    nameLower.includes('handle')
  ) {
    return <AlertTriangle className="h-4 w-4 text-orange-600" />;
  }

  // Documentation patterns
  if (nameLower.includes('doc') || nameLower.includes('readme') || nameLower.includes('comment')) {
    return <BookOpen className="h-4 w-4 text-indigo-600" />;
  }

  // Architecture patterns
  if (
    nameLower.includes('architecture') ||
    nameLower.includes('design') ||
    nameLower.includes('structure')
  ) {
    return <Building className="h-4 w-4 text-slate-600" />;
  }

  // Multi-language/integration patterns
  if (
    nameLower.includes('language') ||
    nameLower.includes('integration') ||
    nameLower.includes('cross')
  ) {
    return <Layers className="h-4 w-4 text-cyan-600" />;
  }

  // Performance patterns
  if (
    nameLower.includes('performance') ||
    nameLower.includes('optimiz') ||
    nameLower.includes('speed')
  ) {
    return <Gauge className="h-4 w-4 text-emerald-600" />;
  }

  // Code review patterns
  if (nameLower.includes('review') || nameLower.includes('pr') || nameLower.includes('merge')) {
    return <GitPullRequest className="h-4 w-4 text-violet-600" />;
  }

  // Dependency patterns
  if (
    nameLower.includes('depend') ||
    nameLower.includes('package') ||
    nameLower.includes('library')
  ) {
    return <Package className="h-4 w-4 text-amber-600" />;
  }

  // Fallback to type-based icons with enhanced colors
  switch (type) {
    case 'technical':
      return <Code2 className="h-4 w-4 text-blue-600" />;
    case 'collaboration':
      return <Users className="h-4 w-4 text-green-600" />;
    case 'growth':
      return <TrendingUp className="h-4 w-4 text-purple-600" />;
    case 'communication':
      return <MessageSquare className="h-4 w-4 text-indigo-600" />;
    case 'work_patterns':
      return <GitBranch className="h-4 w-4 text-orange-600" />;
    default:
      return <FileCode className="h-4 w-4 text-gray-600" />;
  }
};

// Confidence badge styling
const getConfidenceBadge = (confidence: string) => {
  const configs = {
    high: {
      bg: 'bg-gradient-to-r from-emerald-500/10 to-green-500/10 border-emerald-500/20',
      text: 'text-emerald-700',
      icon: <Zap className="h-3 w-3" />,
    },
    medium: {
      bg: 'bg-gradient-to-r from-blue-500/10 to-indigo-500/10 border-blue-500/20',
      text: 'text-blue-700',
      icon: <Brain className="h-3 w-3" />,
    },
    low: {
      bg: 'bg-gradient-to-r from-amber-500/10 to-yellow-500/10 border-amber-500/20',
      text: 'text-amber-700',
      icon: <Search className="h-3 w-3" />,
    },
  };

  const config = configs[confidence as keyof typeof configs] || configs.medium;

  return (
    <Badge variant="outline" className={`${config.bg} ${config.text} backdrop-blur-sm`}>
      {config.icon}
      <span className="ml-1.5 font-medium">{confidence} confidence</span>
    </Badge>
  );
};

// Get pattern-specific background color class
const getPatternBackground = (patternName: string, type: string) => {
  const nameLower = patternName.toLowerCase();

  // Specific pattern background colors
  if (nameLower.includes('bug') || nameLower.includes('fix')) {
    return 'from-red-50/70 to-red-100/50 border-red-200/60';
  }

  if (nameLower.includes('refactor') || nameLower.includes('cleanup')) {
    return 'from-blue-50/70 to-blue-100/50 border-blue-200/60';
  }

  if (nameLower.includes('test') || nameLower.includes('spec')) {
    return 'from-green-50/70 to-green-100/50 border-green-200/60';
  }

  if (nameLower.includes('ci') || nameLower.includes('cd') || nameLower.includes('pipeline')) {
    return 'from-purple-50/70 to-purple-100/50 border-purple-200/60';
  }

  if (nameLower.includes('security') || nameLower.includes('auth')) {
    return 'from-yellow-50/70 to-yellow-100/50 border-yellow-200/60';
  }

  if (nameLower.includes('error') || nameLower.includes('handle')) {
    return 'from-orange-50/70 to-orange-100/50 border-orange-200/60';
  }

  if (nameLower.includes('doc') || nameLower.includes('readme')) {
    return 'from-indigo-50/70 to-indigo-100/50 border-indigo-200/60';
  }

  if (nameLower.includes('architecture') || nameLower.includes('design')) {
    return 'from-slate-50/70 to-slate-100/50 border-slate-200/60';
  }

  if (nameLower.includes('language') || nameLower.includes('integration')) {
    return 'from-cyan-50/70 to-cyan-100/50 border-cyan-200/60';
  }

  if (nameLower.includes('performance') || nameLower.includes('optimiz')) {
    return 'from-emerald-50/70 to-emerald-100/50 border-emerald-200/60';
  }

  // Type-based fallback colors
  switch (type) {
    case 'technical':
      return 'from-blue-50/60 to-blue-100/40 border-blue-200/50';
    case 'collaboration':
      return 'from-green-50/60 to-green-100/40 border-green-200/50';
    case 'work_patterns':
      return 'from-orange-50/60 to-orange-100/40 border-orange-200/50';
    case 'communication':
      return 'from-indigo-50/60 to-indigo-100/40 border-indigo-200/50';
    default:
      return 'from-gray-50/60 to-gray-100/40 border-gray-200/50';
  }
};

export function EvidenceCard({
  title,
  icon,
  patterns,
  confidence,
  summary,
  insights,
  flags = [],
  limitations = [],
  color,
}: EvidenceCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Map color to Tailwind classes with gradients
  const colorClasses = {
    indigo: {
      card: 'border-indigo-200/50 bg-gradient-to-br from-indigo-50/30 via-white to-indigo-50/10',
      header: 'bg-gradient-to-r from-indigo-50 to-white',
      icon: 'bg-gradient-to-br from-indigo-500 to-indigo-600 shadow-indigo-500/20',
      pattern: 'from-indigo-500/5 to-indigo-500/10 hover:from-indigo-500/10 hover:to-indigo-500/15',
    },
    violet: {
      card: 'border-violet-200/50 bg-gradient-to-br from-violet-50/30 via-white to-violet-50/10',
      header: 'bg-gradient-to-r from-violet-50 to-white',
      icon: 'bg-gradient-to-br from-violet-500 to-violet-600 shadow-violet-500/20',
      pattern: 'from-violet-500/5 to-violet-500/10 hover:from-violet-500/10 hover:to-violet-500/15',
    },
    cyan: {
      card: 'border-cyan-200/50 bg-gradient-to-br from-cyan-50/30 via-white to-cyan-50/10',
      header: 'bg-gradient-to-r from-cyan-50 to-white',
      icon: 'bg-gradient-to-br from-cyan-500 to-cyan-600 shadow-cyan-500/20',
      pattern: 'from-cyan-500/5 to-cyan-500/10 hover:from-cyan-500/10 hover:to-cyan-500/15',
    },
    orange: {
      card: 'border-orange-200/50 bg-gradient-to-br from-orange-50/30 via-white to-orange-50/10',
      header: 'bg-gradient-to-r from-orange-50 to-white',
      icon: 'bg-gradient-to-br from-orange-500 to-orange-600 shadow-orange-500/20',
      pattern: 'from-orange-500/5 to-orange-500/10 hover:from-orange-500/10 hover:to-orange-500/15',
    },
  };

  const classes = colorClasses[color as keyof typeof colorClasses] || colorClasses.indigo;

  return (
    <Card
      className={`shadow-xl transition-all duration-300 hover:shadow-2xl ${classes.card} backdrop-blur-sm`}
    >
      <CardHeader className={`pb-4 ${classes.header}`}>
        <div className="flex items-start justify-between gap-4">
          <div className="flex min-w-0 flex-1 items-start gap-4">
            <div className={`flex-shrink-0 rounded-xl p-3 shadow-lg ${classes.icon}`}>{icon}</div>
            <div className="min-w-0 flex-1">
              <CardTitle className="bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text font-bold text-2xl text-transparent">
                {title}
              </CardTitle>
              <CardDescription className="mt-2 text-gray-600 text-sm leading-relaxed">
                {summary}
              </CardDescription>
            </div>
          </div>

          <div className="flex flex-shrink-0 flex-col items-end gap-3">
            {getConfidenceBadge(confidence)}

            <button
              type="button"
              onClick={() => setIsExpanded(!isExpanded)}
              className="group flex items-center gap-1.5 text-gray-600 text-sm transition-colors hover:text-gray-900"
            >
              <span className="font-medium">{isExpanded ? 'Show less' : 'Explore evidence'}</span>
              {isExpanded ? (
                <ChevronUp className="h-4 w-4 transition-transform group-hover:translate-y-[-2px]" />
              ) : (
                <ChevronDown className="h-4 w-4 transition-transform group-hover:translate-y-[2px]" />
              )}
            </button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-6 pt-2">
        {/* Evidence Patterns - Always visible */}
        {patterns.length > 0 && (
          <div className="space-y-3">
            <div className="mb-3 flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-purple-600" />
              <h4 className="font-semibold text-gray-900">Evidence Patterns Found</h4>
              <Badge variant="secondary" className="ml-auto bg-purple-100 text-purple-700">
                {patterns.length} patterns
              </Badge>
            </div>

            <div className="grid gap-3">
              {patterns.slice(0, isExpanded ? undefined : 3).map((pattern, idx) => {
                // Handle duplicate "Commit Quality" names by adding index suffix for display
                let displayName = pattern.name;
                const isCommitQuality =
                  pattern.name.toLowerCase() === 'commit quality' ||
                  pattern.name === 'Commit Quality';

                // Count how many "Commit Quality" patterns we've seen before this one
                if (isCommitQuality) {
                  const previousCommitQualityCount = patterns
                    .slice(0, idx)
                    .filter((p) => p.name.toLowerCase() === 'commit quality').length;

                  if (previousCommitQualityCount > 0) {
                    // Add a distinguishing suffix based on evidence content
                    const evidenceLower = (pattern.evidence || '').toLowerCase();
                    if (evidenceLower.includes('refactor')) {
                      displayName = 'Refactoring Practices';
                    } else if (evidenceLower.includes('bug') || evidenceLower.includes('fix')) {
                      displayName = 'Bug Fix Methodology';
                    } else if (evidenceLower.includes('test')) {
                      displayName = 'Testing Approach';
                    } else if (evidenceLower.includes('ci') || evidenceLower.includes('cd')) {
                      displayName = 'CI/CD Practices';
                    } else if (evidenceLower.includes('language')) {
                      displayName = 'Language Expertise';
                    } else {
                      // Fallback: add a number
                      displayName = `Development Pattern ${previousCommitQualityCount + 1}`;
                    }
                  }
                }

                const patternBg = getPatternBackground(displayName, pattern.pattern_type);
                return (
                  <div
                    key={idx}
                    className={`group relative overflow-hidden rounded-xl border bg-gradient-to-br ${patternBg} p-4 transition-all duration-300 hover:scale-[1.01] hover:shadow-md`}
                  >
                    <div className="flex items-start gap-3">
                      <div className="rounded-lg bg-white/80 p-2 shadow-sm">
                        {getPatternIcon(displayName, pattern.pattern_type)}
                      </div>

                      <div className="flex-1 space-y-2">
                        <div className="flex items-start justify-between gap-3">
                          <h5 className="font-semibold text-gray-900 text-sm">
                            {displayName
                              .replace(/_/g, ' ')
                              .split(' ')
                              .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
                              .join(' ')}
                          </h5>
                          <Badge variant="outline" className="text-xs">
                            {pattern.category}
                          </Badge>
                        </div>

                        <p className="font-medium text-gray-700 text-sm">
                          <FileCode className="mr-1 inline h-3 w-3 text-gray-500" />
                          {pattern.evidence}
                        </p>

                        <p className="text-gray-600 text-sm italic">
                          &quot;{pattern.insight}&quot;
                        </p>
                      </div>
                    </div>

                    {/* Decorative gradient overlay */}
                    <div className="pointer-events-none absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent opacity-0 transition-opacity duration-500 group-hover:opacity-100" />
                  </div>
                );
              })}
            </div>

            {!isExpanded && patterns.length > 3 && (
              <p className="mt-3 text-center text-gray-500 text-sm">
                +{patterns.length - 3} more patterns available
              </p>
            )}
          </div>
        )}

        {/* Expanded Details */}
        {isExpanded && (
          <>
            <Separator className="bg-gradient-to-r from-transparent via-gray-200 to-transparent" />

            {/* Key Insights */}
            {insights.length > 0 && (
              <div>
                <h4 className="mb-3 flex items-center gap-2 font-semibold text-gray-900">
                  <Info className="h-4 w-4 text-blue-600" />
                  Key Insights
                </h4>
                <ul className="space-y-2">
                  {insights.map((insight, idx) => (
                    <li key={idx} className="flex items-start gap-3 text-gray-700 text-sm">
                      <span className="mt-0.5 text-blue-500">•</span>
                      <span>{insight}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Positive Indicators */}
            {flags.filter((f) => f.type === 'green').length > 0 && (
              <div>
                <h4 className="mb-3 flex items-center gap-2 font-semibold text-gray-900">
                  <CheckCircle className="h-4 w-4 text-green-600" />
                  Strengths Observed
                </h4>
                <div className="space-y-2">
                  {flags
                    .filter((f) => f.type === 'green')
                    .map((flag, idx) => (
                      <div
                        key={idx}
                        className="rounded-lg border border-green-200/50 bg-gradient-to-r from-green-50 to-emerald-50 p-3"
                      >
                        <div className="font-medium text-green-900">{flag.description}</div>
                        {flag.evidence && flag.evidence.length > 0 && (
                          <ul className="mt-1.5 space-y-0.5 text-green-700 text-sm">
                            {flag.evidence.map((e, i) => (
                              <li key={i} className="flex items-start gap-2">
                                <span className="mt-0.5 text-green-500">›</span>
                                {e}
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    ))}
                </div>
              </div>
            )}

            {/* Areas to Explore */}
            {flags.filter((f) => f.type === 'red').length > 0 && (
              <div>
                <h4 className="mb-3 flex items-center gap-2 font-semibold text-gray-900">
                  <AlertCircle className="h-4 w-4 text-amber-600" />
                  Areas to Explore
                </h4>
                <div className="space-y-2">
                  {flags
                    .filter((f) => f.type === 'red')
                    .map((flag, idx) => (
                      <div
                        key={idx}
                        className="rounded-lg border border-amber-200/50 bg-gradient-to-r from-amber-50 to-yellow-50 p-3"
                      >
                        <div className="font-medium text-amber-900">{flag.description}</div>
                        {flag.evidence && flag.evidence.length > 0 && (
                          <ul className="mt-1.5 space-y-0.5 text-amber-700 text-sm">
                            {flag.evidence.map((e, i) => (
                              <li key={i} className="flex items-start gap-2">
                                <span className="mt-0.5 text-amber-500">›</span>
                                {e}
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    ))}
                </div>
              </div>
            )}

            {/* Analysis Context */}
            {limitations.length > 0 && (
              <div>
                <h4 className="mb-3 flex items-center gap-2 font-semibold text-gray-900">
                  <Info className="h-4 w-4 text-gray-500" />
                  Analysis Context
                </h4>
                <div className="rounded-lg border border-gray-200/50 bg-gradient-to-r from-gray-50 to-slate-50 p-4">
                  <ul className="space-y-1.5 text-gray-600 text-sm">
                    {limitations.map((limitation, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="mt-0.5 text-gray-400">•</span>
                        {limitation}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
