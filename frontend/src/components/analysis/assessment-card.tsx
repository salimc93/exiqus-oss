// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import { AlertCircle, CheckCircle, ChevronDown, ChevronUp, Info } from 'lucide-react';
import { useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

interface Flag {
  type: 'green' | 'red';
  category: string;
  description: string;
  severity?: string;
  evidence?: string[];
}

interface AssessmentCardProps {
  title: string;
  icon: React.ReactNode;
  overall_score: number;
  confidence: string;
  summary: string;
  details: string[];
  flags?: Flag[];
  limitations?: string[];
  metrics?: Record<string, number>;
  color: string; // e.g., "indigo", "violet", "cyan", "orange"
}

const getScoreInterpretation = (
  score: number
): { label: string; color: string; description: string } => {
  if (score >= 0.8)
    return {
      label: 'Excellent',
      color: 'text-green-700',
      description: 'Top-tier performance in this area',
    };
  if (score >= 0.6)
    return {
      label: 'Good',
      color: 'text-blue-700',
      description: 'Above average, with room for growth',
    };
  if (score >= 0.4)
    return {
      label: 'Developing',
      color: 'text-yellow-700',
      description: 'Shows promise but needs improvement',
    };
  return {
    label: 'Needs Focus',
    color: 'text-red-700',
    description: 'Significant improvement opportunity',
  };
};

const getMetricLabel = (key: string): { label: string; description: string } => {
  const metrics: Record<string, { label: string; description: string }> = {
    // Technical Skills
    code_quality: {
      label: 'Code Quality',
      description: 'Clean, maintainable, and well-structured code',
    },
    architecture: {
      label: 'Architecture',
      description: 'System design and structural decisions',
    },
    testing: {
      label: 'Testing Practices',
      description: 'Test coverage and quality assurance',
    },
    documentation: {
      label: 'Documentation',
      description: 'Code comments and technical docs',
    },
    best_practices: {
      label: 'Best Practices',
      description: 'Industry standards and conventions',
    },

    // Professional Practices
    version_control: {
      label: 'Version Control',
      description: 'Git workflow and commit practices',
    },
    collaboration: {
      label: 'Collaboration',
      description: 'Team interaction and code reviews',
    },
    issue_management: {
      label: 'Issue Management',
      description: 'Task tracking and organization',
    },
    ci_cd: {
      label: 'CI/CD Practices',
      description: 'Automation and deployment processes',
    },

    // Communication Skills
    documentation_quality: {
      label: 'Documentation Quality',
      description: 'README, guides, and explanations',
    },
    commit_messages: {
      label: 'Commit Messages',
      description: 'Clear and descriptive change history',
    },
    pr_descriptions: {
      label: 'PR Descriptions',
      description: 'Pull request communication',
    },
    issue_discussions: {
      label: 'Issue Discussions',
      description: 'Problem-solving communication',
    },

    // Growth Indicators
    learning_velocity: {
      label: 'Learning Velocity',
      description: 'Speed of acquiring new skills',
    },
    technology_adoption: {
      label: 'Technology Adoption',
      description: 'Embracing new tools and languages',
    },
    contribution_consistency: {
      label: 'Consistency',
      description: 'Regular contribution patterns',
    },
    skill_progression: {
      label: 'Skill Progression',
      description: 'Improvement over time',
    },
  };

  return metrics[key] || { label: key.replace(/_/g, ' '), description: '' };
};

export function AssessmentCard({
  title,
  icon,
  overall_score,
  confidence,
  summary,
  details,
  flags = [],
  limitations = [],
  metrics = {},
  color,
}: AssessmentCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const scoreInterpretation = getScoreInterpretation(overall_score);

  // Map color to Tailwind classes (must be complete class names for Tailwind to detect them)
  const colorClasses = {
    indigo: {
      card: 'border-indigo-100 bg-gradient-to-br from-indigo-50/30 to-indigo-50/10',
      icon: 'bg-gradient-to-br from-indigo-500 to-indigo-600',
    },
    violet: {
      card: 'border-violet-100 bg-gradient-to-br from-violet-50/30 to-violet-50/10',
      icon: 'bg-gradient-to-br from-violet-500 to-violet-600',
    },
    cyan: {
      card: 'border-cyan-100 bg-gradient-to-br from-cyan-50/30 to-cyan-50/10',
      icon: 'bg-gradient-to-br from-cyan-500 to-cyan-600',
    },
    orange: {
      card: 'border-orange-100 bg-gradient-to-br from-orange-50/30 to-orange-50/10',
      icon: 'bg-gradient-to-br from-orange-500 to-orange-600',
    },
  };

  const classes = colorClasses[color as keyof typeof colorClasses] || colorClasses.indigo;

  return (
    <Card className={`shadow-lg ${classes.card}`}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-4">
          <div className="flex min-w-0 flex-1 items-start gap-3">
            <div className={`flex-shrink-0 rounded-lg p-2 ${classes.icon}`}>{icon}</div>
            <div className="min-w-0 flex-1">
              <CardTitle className="text-xl leading-tight">{title}</CardTitle>
              <CardDescription className="mt-1 text-sm leading-relaxed">
                <span className={`font-semibold ${scoreInterpretation.color}`}>
                  {scoreInterpretation.label}
                </span>
                {' - '}
                <span className="text-gray-600">{scoreInterpretation.description}</span>
              </CardDescription>
            </div>
          </div>

          <div className="flex flex-shrink-0 flex-col items-end gap-2">
            <div className="flex flex-wrap items-center justify-end gap-2">
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Badge variant="outline" className="cursor-help whitespace-nowrap text-sm">
                      {confidence} confidence
                    </Badge>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Assessment reliability based on available data</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>

              <Badge
                className={`whitespace-nowrap font-bold text-lg ${
                  overall_score >= 0.8
                    ? 'bg-green-600'
                    : overall_score >= 0.6
                      ? 'bg-blue-600'
                      : overall_score >= 0.4
                        ? 'bg-yellow-600'
                        : 'bg-red-600'
                }`}
              >
                {(overall_score * 100).toFixed(0)}%
              </Badge>
            </div>

            <button
              type="button"
              onClick={() => setIsExpanded(!isExpanded)}
              className="flex items-center gap-1 whitespace-nowrap text-gray-600 text-sm transition-colors hover:text-gray-900"
            >
              {isExpanded ? 'Show less' : 'Show details'}
              {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-6">
        {/* Summary */}
        <div className="rounded-lg bg-white/60 p-4">
          <p className="text-gray-700 text-sm leading-relaxed">{summary}</p>
        </div>

        {/* Individual Metrics */}
        {Object.keys(metrics).length > 0 && (
          <div className="space-y-3">
            <h4 className="font-semibold text-gray-900">Detailed Breakdown</h4>
            <div className="grid gap-3">
              {Object.entries(metrics).map(([key, value]) => {
                const metric = getMetricLabel(key);
                const score = typeof value === 'number' ? value : 0;

                return (
                  <div key={key} className="rounded-lg bg-white/50 p-3">
                    <div className="mb-2 flex items-start justify-between">
                      <div className="flex-1">
                        <div className="font-medium text-gray-900">{metric.label}</div>
                        <div className="mt-0.5 text-gray-600 text-xs">{metric.description}</div>
                      </div>
                      <Badge variant="secondary" className="ml-2">
                        {(score * 100).toFixed(0)}%
                      </Badge>
                    </div>
                    <Progress value={score * 100} className="h-2" />
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Expanded Details */}
        {isExpanded && (
          <>
            <Separator />

            {/* What We Found */}
            {details.length > 0 && (
              <div>
                <h4 className="mb-3 flex items-center gap-2 font-semibold text-gray-900">
                  <Info className="h-4 w-4" />
                  What We Found
                </h4>
                <ul className="space-y-2">
                  {details.map((detail, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-gray-700 text-sm">
                      <span className="mt-0.5 text-gray-400">•</span>
                      <span>{detail}</span>
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
                  Positive Indicators
                </h4>
                <div className="space-y-2">
                  {flags
                    .filter((f) => f.type === 'green')
                    .map((flag, idx) => (
                      <div key={idx} className="rounded-lg border border-green-200 bg-green-50 p-3">
                        <div className="font-medium text-green-900">{flag.description}</div>
                        {flag.evidence && flag.evidence.length > 0 && (
                          <ul className="mt-1 text-green-700 text-sm">
                            {flag.evidence.map((e, i) => (
                              <li key={i}>• {e}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    ))}
                </div>
              </div>
            )}

            {/* Areas of Concern */}
            {flags.filter((f) => f.type === 'red').length > 0 && (
              <div>
                <h4 className="mb-3 flex items-center gap-2 font-semibold text-gray-900">
                  <AlertCircle className="h-4 w-4 text-amber-600" />
                  Areas of Concern
                </h4>
                <div className="space-y-2">
                  {flags
                    .filter((f) => f.type === 'red')
                    .map((flag, idx) => (
                      <div key={idx} className="rounded-lg border border-amber-200 bg-amber-50 p-3">
                        <div className="font-medium text-amber-900">{flag.description}</div>
                        {flag.evidence && flag.evidence.length > 0 && (
                          <ul className="mt-1 text-amber-700 text-sm">
                            {flag.evidence.map((e, i) => (
                              <li key={i}>• {e}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    ))}
                </div>
              </div>
            )}

            {/* Assessment Limitations */}
            {limitations.length > 0 && (
              <div>
                <h4 className="mb-3 flex items-center gap-2 font-semibold text-gray-900">
                  <Info className="h-4 w-4 text-gray-500" />
                  Assessment Limitations
                </h4>
                <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                  <ul className="space-y-1 text-gray-600 text-sm">
                    {limitations.map((limitation, idx) => (
                      <li key={idx}>• {limitation}</li>
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
