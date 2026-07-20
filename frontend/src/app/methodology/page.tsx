// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import {
  AlertTriangle,
  BarChart3,
  BookOpen,
  Brain,
  CheckCircle,
  Clock,
  Code2,
  DollarSign,
  Eye,
  FileCode,
  GitBranch,
  GitCommit,
  GitPullRequest,
  Layers,
  MessageSquare,
  Shield,
  Target,
  TestTube,
  Users,
  XCircle,
  Zap,
} from 'lucide-react';

import { ExiqusCard, ExiqusSectionHeader, GradientText } from '@/components/ui/exiqus-components';

export default function MethodologyPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0A] text-white">
      <div className="mx-auto max-w-4xl px-4 py-16 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-12 text-center">
          <div className="mb-6 flex justify-center">
            <div className="rounded-xl bg-purple-500/10 p-4">
              <Brain className="h-12 w-12 text-purple-400" />
            </div>
          </div>
          <h1 className="mb-4 font-bold text-4xl md:text-5xl">
            <GradientText>Our Methodology</GradientText>
          </h1>
          <p className="mx-auto max-w-2xl text-gray-400 text-xl">
            How Exiqus analyses developers through their GitHub evidence, not arbitrary scores
          </p>
        </div>

        {/* Core Principles */}
        <ExiqusCard className="mb-8 p-8">
          <ExiqusSectionHeader title="Fundamental Approach: Evidence, Not Scores" icon={Target} />
          <p className="mb-6 text-gray-400">
            Exiqus has adopted a purely evidence-based approach to developer assessment. We DO NOT
            assign numerical scores, ratings, or percentages to developers. Instead, we extract
            observable patterns from public repositories and present them as evidence for hiring
            decisions.
          </p>

          <div className="grid gap-6 md:grid-cols-3">
            <div className="space-y-2">
              <h4 className="flex items-center gap-2 font-semibold text-purple-400">
                <XCircle className="h-4 w-4" />
                No Numerical Scoring
              </h4>
              <p className="text-gray-400 text-sm">
                No &quot;8.5/10 code quality&quot; scores. Only observable evidence like &quot;126
                test files for 9 code files.&quot;
              </p>
            </div>
            <div className="space-y-2">
              <h4 className="flex items-center gap-2 font-semibold text-purple-400">
                <Eye className="h-4 w-4" />
                Observable Patterns Only
              </h4>
              <p className="text-gray-400 text-sm">
                We report facts like &quot;27 bug fix commits (54% of total)&quot; not subjective
                assessments.
              </p>
            </div>
            <div className="space-y-2">
              <h4 className="flex items-center gap-2 font-semibold text-purple-400">
                <Layers className="h-4 w-4" />
                Context-Aware
              </h4>
              <p className="text-gray-400 text-sm">
                Same data, different insights based on your company context (Startup, Enterprise,
                Agency, Open Source) and seniority level (Junior, Mid-level, Senior).
              </p>
            </div>
          </div>
        </ExiqusCard>

        {/* Data Limitations - Prominent Callout */}
        <ExiqusCard className="mb-8 border-amber-500 border-l-4 bg-gradient-to-r from-amber-500/10 to-orange-500/5 p-8">
          <div className="mb-6 flex items-start gap-4">
            <div className="rounded-lg bg-amber-500/20 p-3">
              <AlertTriangle className="h-7 w-7 text-amber-400" />
            </div>
            <div>
              <h3 className="mb-2 font-bold text-2xl text-amber-300">Critical Data Limitations</h3>
              <p className="text-gray-300 text-lg">
                We&apos;re transparent about what we <strong>cannot</strong> assess. Understanding
                these limitations is crucial for making fair hiring decisions.
              </p>
            </div>
          </div>

          <div className="mb-6 grid gap-6 md:grid-cols-2">
            <div className="space-y-3 rounded-lg border border-amber-500/30 bg-gray-900/50 p-5">
              <h4 className="flex items-center gap-2 font-semibold text-amber-400">
                <XCircle className="h-5 w-5" />
                Public Data Only
              </h4>
              <ul className="space-y-2 text-gray-300 text-sm">
                <li className="flex items-start gap-2">
                  <span className="mt-1 text-amber-500">•</span>
                  <span>
                    We analyse <strong>public repositories only</strong>. Private company work is
                    invisible to us.
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="mt-1 text-amber-500">•</span>
                  <span>
                    Gaps in public activity likely represent private work, not absence of skill.
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="mt-1 text-amber-500">•</span>
                  <span>
                    Professional experience may be significantly greater than public evidence shows.
                  </span>
                </li>
              </ul>
            </div>

            <div className="space-y-3 rounded-lg border border-amber-500/30 bg-gray-900/50 p-5">
              <h4 className="flex items-center gap-2 font-semibold text-amber-400">
                <XCircle className="h-5 w-5" />
                What We Cannot Measure
              </h4>
              <ul className="space-y-2 text-gray-300 text-sm">
                <li className="flex items-start gap-2">
                  <span className="mt-1 text-amber-500">•</span>
                  <span>Actual job performance or productivity</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="mt-1 text-amber-500">•</span>
                  <span>Soft skills, communication, or teamwork quality</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="mt-1 text-amber-500">•</span>
                  <span>Problem-solving under pressure or in meetings</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="mt-1 text-amber-500">•</span>
                  <span>Cultural fit, learning speed, or innovation capacity</span>
                </li>
              </ul>
            </div>
          </div>

          <div className="rounded-lg bg-amber-500/10 p-4 text-center">
            <p className="font-medium text-amber-300 text-sm">
              <strong>This is ONE data point for hiring decisions.</strong> Use it alongside
              interviews, references, and your professional judgment.
            </p>
          </div>
        </ExiqusCard>

        {/* Academic & Market Gap */}
        <ExiqusCard className="mb-8 border-purple-500/20 bg-gradient-to-br from-purple-900/10 to-blue-900/10 p-8">
          <ExiqusSectionHeader title="Filling the Academic & Market Gap" icon={Brain} />

          <div className="mb-6 space-y-4">
            <p className="text-gray-300">
              Exiqus is pioneering a research gap that exists in both academic literature and the
              commercial market: systematically linking GitHub evidence to hiring outcomes.
            </p>
          </div>

          <div className="mb-6 rounded-lg border border-blue-500/20 bg-blue-500/5 p-4">
            <h4 className="mb-3 font-semibold text-blue-400">Academic Landscape</h4>
            <ul className="space-y-2 text-gray-400 text-sm">
              <li className="flex items-start gap-2">
                <span className="mt-1 text-blue-500">•</span>
                <span>
                  The paper &quot;Improving Evidence-Based Tech Hiring with GitHub-Supported Resume
                  Matching&quot; (SANER 2025) is the first peer-reviewed work proposing GitHub
                  analysis for hiring—and it only demonstrates feasibility, not outcome correlation
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="mt-1 text-blue-500">•</span>
                <span>
                  Prior studies (2022-2024) analysed developer reputation or productivity via GitHub
                  metrics, not hiring outcomes
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="mt-1 text-blue-500">•</span>
                <span>
                  <strong className="text-blue-300">No peer-reviewed dataset</strong> connects
                  GitHub activity → hiring decision → on-job success
                </span>
              </li>
            </ul>
          </div>

          <div className="mb-6 rounded-lg border border-purple-500/20 bg-purple-500/5 p-4">
            <h4 className="mb-3 font-semibold text-purple-400">Market Landscape</h4>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[700px] text-sm">
                <thead className="border-white/10 border-b">
                  <tr>
                    <th className="pr-4 pb-2 text-left font-medium text-gray-400">Platform</th>
                    <th className="pr-4 pb-2 text-left font-medium text-gray-400">Focus</th>
                    <th className="pr-4 pb-2 text-left font-medium text-gray-400">
                      GitHub Integration
                    </th>
                    <th className="pb-2 text-left font-medium text-gray-400">Outcome Tracking</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/10">
                  <tr>
                    <td className="py-2 pr-4 text-gray-400">HackerRank / Codility</td>
                    <td className="py-2 pr-4 text-gray-400">Puzzle-scoring</td>
                    <td className="py-2 pr-4 text-gray-400">None</td>
                    <td className="py-2 text-red-400">No</td>
                  </tr>
                  <tr>
                    <td className="py-2 pr-4 text-gray-400">SeekOut / HireEZ</td>
                    <td className="py-2 pr-4 text-gray-400">Search/reach-out</td>
                    <td className="py-2 pr-4 text-gray-400">Metadata only</td>
                    <td className="py-2 text-red-400">No</td>
                  </tr>
                  <tr>
                    <td className="py-2 pr-4 text-gray-400">Hirable / Turing</td>
                    <td className="py-2 pr-4 text-gray-400">Portfolio marketing</td>
                    <td className="py-2 pr-4 text-gray-400">Minimal metrics</td>
                    <td className="py-2 text-red-400">No</td>
                  </tr>
                  <tr className="bg-purple-500/10">
                    <td className="py-2 pr-4 font-semibold text-purple-300">Exiqus</td>
                    <td className="py-2 pr-4 text-purple-300">Evidence framework</td>
                    <td className="py-2 pr-4 text-purple-300">Full repo + PR analysis</td>
                    <td className="py-2 font-semibold text-green-400">
                      In Development{' '}
                      <span className="text-gray-400 text-xs">(First in Market)</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div className="rounded-lg bg-gradient-to-r from-purple-900/20 to-blue-900/20 p-4">
            <p className="text-center text-gray-300 text-sm">
              <strong className="text-purple-300">We&apos;re uniquely positioned</strong> as the
              first platform systematically building a dataset that links GitHub evidence patterns
              to hiring outcomes—filling a gap that exists in both academia and the market.
            </p>
          </div>
        </ExiqusCard>

        {/* Evidence Validation */}
        <ExiqusCard className="mb-8 p-8">
          <ExiqusSectionHeader title="Evidence Validation: The Science" icon={BarChart3} />

          <p className="mb-6 text-gray-300">
            Traditional hiring methods vary widely in predictive validity. Work sample{' '}
            <em>tests</em>
            (standardized exercises) show 0.33 validity. But Exiqus doesn&apos;t test candidates—we
            analyse years of real work. No research yet validates GitHub portfolio analysis for
            hiring. We&apos;re building the first dataset to find out if it works.
          </p>

          <div className="mb-8 overflow-x-auto rounded-lg border border-gray-700">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead className="bg-gray-800/50">
                <tr>
                  <th className="px-4 py-3 font-semibold text-gray-200">Hiring Method</th>
                  <th className="px-4 py-3 text-center font-semibold text-gray-200">
                    Predictive Validity (r)
                  </th>
                  <th className="px-4 py-3 font-semibold text-gray-200">What This Means</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700">
                <tr className="bg-green-900/10">
                  <td className="px-4 py-3 font-semibold text-green-400">Work-sample tests</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex items-center justify-center gap-2">
                      <div className="h-2 w-24 rounded-full bg-gray-700">
                        <div className="h-2 w-[55%] rounded-full bg-green-500"></div>
                      </div>
                      <span className="font-semibold text-green-400">0.33</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-300">
                    Standardized exercises like take-homes
                  </td>
                </tr>
                <tr>
                  <td className="px-4 py-3 text-gray-300">Structured behavioral interview</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex items-center justify-center gap-2">
                      <div className="h-2 w-24 rounded-full bg-gray-700">
                        <div className="h-2 w-[72%] rounded-full bg-blue-500"></div>
                      </div>
                      <span className="text-blue-400">
                        0.42<span className="text-gray-500 text-xs">†</span>
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-400">Strong when standardized</td>
                </tr>
                <tr>
                  <td className="px-4 py-3 text-gray-300">
                    Coding puzzles / technical panels<span className="text-amber-400">*</span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex items-center justify-center gap-2">
                      <div className="h-2 w-24 rounded-full bg-gray-700">
                        <div className="h-2 w-[0%] rounded-full bg-amber-500"></div>
                      </div>
                      <span className="text-amber-400">Unknown</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-400">No published validity research</td>
                </tr>
                <tr className="bg-red-900/10">
                  <td className="px-4 py-3 font-semibold text-red-400">Unstructured interview</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex items-center justify-center gap-2">
                      <div className="h-2 w-24 rounded-full bg-gray-700">
                        <div className="h-2 w-[40%] rounded-full bg-red-500"></div>
                      </div>
                      <span className="font-semibold text-red-400">0.22</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-300">Nearly random—gut-feel bias</td>
                </tr>
                <tr>
                  <td className="px-4 py-3 text-gray-300">Résumé / reference review</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex items-center justify-center gap-2">
                      <div className="h-2 w-24 rounded-full bg-gray-700">
                        <div className="h-2 w-[30%] rounded-full bg-gray-500"></div>
                      </div>
                      <span className="text-gray-400">0.18</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-400">Filtering tool only</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="mb-6 space-y-1 text-gray-500 text-xs">
            <p>
              Source: Schmidt & Oh 2016 meta-analysis; Roth et al. 2005; updated IO research
              2020–2024
            </p>
            <p className="text-amber-400">
              * No published research validates coding puzzle interviews (e.g., LeetCode, HackerRank
              challenges) for predicting software engineering job performance. Estimates of
              0.30-0.40 are extrapolations from general cognitive ability tests (0.31) and job
              knowledge tests (0.40), but these are different assessment types.
            </p>
            <p className="text-gray-500">
              † Schmidt & Oh 2016 consensus is 0.42; some studies show ranges up to 0.51-0.64
              depending on structure and implementation.
            </p>
          </div>

          <h4 className="mb-4 font-semibold text-gray-200 text-lg">
            Traditional Pipeline vs Evidence-First Hiring
          </h4>

          <div className="grid gap-6 md:grid-cols-2">
            <div className="rounded-lg border border-red-500/20 bg-red-900/10 p-6">
              <h5 className="mb-4 flex items-center gap-2 font-semibold text-red-400">
                <XCircle className="h-5 w-5" />
                Traditional 5-Stage Process
              </h5>
              <ul className="mb-4 space-y-2 text-gray-400 text-sm">
                <li className="flex items-start gap-2">
                  <span className="text-red-500">1.</span>
                  <span>Résumé screen (r ≤ 0.18)</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-red-500">2.</span>
                  <span>Phone screen (r ≈ 0.23)</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-red-500">3.</span>
                  <span>Coding challenge (r = Unknown)</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-red-500">4.</span>
                  <span>Technical panel (r = 0.23–0.42)</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-red-500">5.</span>
                  <span>Culture fit (r ≈ 0.23)</span>
                </li>
              </ul>
              <div className="space-y-2 border-red-500/20 border-t pt-4">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-400">Signal Quality:</span>
                  <span className="font-semibold text-red-400">Mixed (0.18–0.42)</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="flex items-center gap-1 text-gray-400">
                    <Clock className="h-4 w-4" />
                    Time:
                  </span>
                  <span className="font-semibold text-red-400">28–34 hours</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="flex items-center gap-1 text-gray-400">
                    <DollarSign className="h-4 w-4" />
                    Cost:
                  </span>
                  <span className="font-semibold text-red-400">$4,700</span>
                </div>
              </div>
            </div>

            <div className="rounded-lg border border-green-500/20 bg-green-900/10 p-6">
              <h5 className="mb-4 flex items-center gap-2 font-semibold text-green-400">
                <CheckCircle className="h-5 w-5" />
                Evidence-First with Exiqus
              </h5>
              <ul className="mb-4 space-y-2 text-gray-400 text-sm">
                <li className="flex items-start gap-2">
                  <span className="text-green-500">1.</span>
                  <span>ATS / basic filter (r ≤ 0.18)</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-green-500">2.</span>
                  <span>
                    <strong className="text-green-400">Exiqus evidence-driven interview</strong>{' '}
                    (validity unknown—first to measure)
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-green-500">3.</span>
                  <span>Optional: Final team fit conversation</span>
                </li>
              </ul>
              <div className="space-y-2 border-green-500/20 border-t pt-4">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-400">Hypothesis:</span>
                  <span className="font-semibold text-green-400">&gt;0.33 (better than tests)</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="flex items-center gap-1 text-gray-400">
                    <Clock className="h-4 w-4" />
                    Time:
                  </span>
                  <span className="font-semibold text-green-400">6–10 hours</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="flex items-center gap-1 text-gray-400">
                    <DollarSign className="h-4 w-4" />
                    Cost:
                  </span>
                  <span className="font-semibold text-green-400">&lt;$1,500</span>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-6 rounded-lg bg-gradient-to-r from-purple-900/20 to-blue-900/20 p-4">
            <p className="text-center font-semibold text-lg text-purple-300">
              Higher signal. Lower cost. Better experience.
            </p>
          </div>
        </ExiqusCard>

        {/* What We Analyze */}
        <ExiqusCard className="mb-8 p-8">
          <ExiqusSectionHeader title="What We Analyze" icon={Eye} />
          <p className="mb-8 text-gray-400">
            We extract observable patterns from public GitHub data. These are factual observations,
            not judgments about code quality or developer ability.
          </p>

          <h4 className="mb-6 font-semibold text-gray-200 text-xl">Repository Data</h4>
          <div className="mb-12 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {/* Code Structure Card */}
            <div className="group rounded-lg border border-gray-700 bg-gray-800/30 p-5 transition-all hover:border-purple-500/50 hover:bg-gray-800/50">
              <div className="mb-3 flex items-center gap-3">
                <div className="rounded-lg bg-purple-500/10 p-2">
                  <FileCode className="h-5 w-5 text-purple-400" />
                </div>
                <h5 className="font-semibold text-gray-200">Code Structure</h5>
              </div>
              <p className="text-gray-400 text-sm">
                File counts, language distribution, directory depth, and organization patterns
              </p>
            </div>

            {/* Commit History Card */}
            <div className="group rounded-lg border border-gray-700 bg-gray-800/30 p-5 transition-all hover:border-purple-500/50 hover:bg-gray-800/50">
              <div className="mb-3 flex items-center gap-3">
                <div className="rounded-lg bg-purple-500/10 p-2">
                  <GitCommit className="h-5 w-5 text-purple-400" />
                </div>
                <h5 className="font-semibold text-gray-200">Commit History</h5>
              </div>
              <p className="text-gray-400 text-sm">
                Frequency patterns, timing, message conventions, and work distribution
              </p>
            </div>

            {/* Testing Evidence Card */}
            <div className="group rounded-lg border border-gray-700 bg-gray-800/30 p-5 transition-all hover:border-purple-500/50 hover:bg-gray-800/50">
              <div className="mb-3 flex items-center gap-3">
                <div className="rounded-lg bg-purple-500/10 p-2">
                  <TestTube className="h-5 w-5 text-purple-400" />
                </div>
                <h5 className="font-semibold text-gray-200">Testing Evidence</h5>
              </div>
              <p className="text-gray-400 text-sm">
                Test file ratios, CI/CD configurations, and automated quality checks
              </p>
            </div>

            {/* Documentation Card */}
            <div className="group rounded-lg border border-gray-700 bg-gray-800/30 p-5 transition-all hover:border-purple-500/50 hover:bg-gray-800/50">
              <div className="mb-3 flex items-center gap-3">
                <div className="rounded-lg bg-purple-500/10 p-2">
                  <BookOpen className="h-5 w-5 text-purple-400" />
                </div>
                <h5 className="font-semibold text-gray-200">Documentation</h5>
              </div>
              <p className="text-gray-400 text-sm">
                README presence, comment density, docs folders, and code explanation patterns
              </p>
            </div>

            {/* Branch Management Card */}
            <div className="group rounded-lg border border-gray-700 bg-gray-800/30 p-5 transition-all hover:border-purple-500/50 hover:bg-gray-800/50">
              <div className="mb-3 flex items-center gap-3">
                <div className="rounded-lg bg-purple-500/10 p-2">
                  <GitBranch className="h-5 w-5 text-purple-400" />
                </div>
                <h5 className="font-semibold text-gray-200">Repository Activity</h5>
              </div>
              <p className="text-gray-400 text-sm">
                Branch patterns, fork counts, stars, and community engagement signals
              </p>
            </div>
          </div>

          <h4 className="mb-6 font-semibold text-gray-200 text-xl">PR Contribution Data</h4>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {/* PR Metadata Card */}
            <div className="group rounded-lg border border-gray-700 bg-gray-800/30 p-5 transition-all hover:border-blue-500/50 hover:bg-gray-800/50">
              <div className="mb-3 flex items-center gap-3">
                <div className="rounded-lg bg-blue-500/10 p-2">
                  <GitPullRequest className="h-5 w-5 text-blue-400" />
                </div>
                <h5 className="font-semibold text-gray-200">PR Metadata</h5>
              </div>
              <p className="text-gray-400 text-sm">
                Counts, states, merge dates, and contribution frequency patterns
              </p>
            </div>

            {/* Code Changes Card */}
            <div className="group rounded-lg border border-gray-700 bg-gray-800/30 p-5 transition-all hover:border-blue-500/50 hover:bg-gray-800/50">
              <div className="mb-3 flex items-center gap-3">
                <div className="rounded-lg bg-blue-500/10 p-2">
                  <Code2 className="h-5 w-5 text-blue-400" />
                </div>
                <h5 className="font-semibold text-gray-200">Code Changes</h5>
              </div>
              <p className="text-gray-400 text-sm">
                Additions, deletions, commit counts per PR, and change scope patterns
              </p>
            </div>

            {/* Quality Gates Card */}
            <div className="group rounded-lg border border-gray-700 bg-gray-800/30 p-5 transition-all hover:border-blue-500/50 hover:bg-gray-800/50">
              <div className="mb-3 flex items-center gap-3">
                <div className="rounded-lg bg-blue-500/10 p-2">
                  <Shield className="h-5 w-5 text-blue-400" />
                </div>
                <h5 className="font-semibold text-gray-200">Quality Gates</h5>
              </div>
              <p className="text-gray-400 text-sm">
                Review decisions (APPROVED, CHANGES_REQUESTED) and approval patterns
              </p>
            </div>

            {/* Work Categorization Card */}
            <div className="group rounded-lg border border-gray-700 bg-gray-800/30 p-5 transition-all hover:border-blue-500/50 hover:bg-gray-800/50">
              <div className="mb-3 flex items-center gap-3">
                <div className="rounded-lg bg-blue-500/10 p-2">
                  <Target className="h-5 w-5 text-blue-400" />
                </div>
                <h5 className="font-semibold text-gray-200">Work Categorization</h5>
              </div>
              <p className="text-gray-400 text-sm">
                GitHub labels (feature, bug, docs) and PR type classification
              </p>
            </div>

            {/* Review Engagement Card */}
            <div className="group rounded-lg border border-gray-700 bg-gray-800/30 p-5 transition-all hover:border-blue-500/50 hover:bg-gray-800/50">
              <div className="mb-3 flex items-center gap-3">
                <div className="rounded-lg bg-blue-500/10 p-2">
                  <MessageSquare className="h-5 w-5 text-blue-400" />
                </div>
                <h5 className="font-semibold text-gray-200">Review Engagement</h5>
              </div>
              <p className="text-gray-400 text-sm">
                Comment volume, merge rates, and code review participation patterns
              </p>
            </div>

            {/* Collaboration Markers Card */}
            <div className="group rounded-lg border border-gray-700 bg-gray-800/30 p-5 transition-all hover:border-blue-500/50 hover:bg-gray-800/50">
              <div className="mb-3 flex items-center gap-3">
                <div className="rounded-lg bg-blue-500/10 p-2">
                  <Users className="h-5 w-5 text-blue-400" />
                </div>
                <h5 className="font-semibold text-gray-200">Collaboration Markers</h5>
              </div>
              <p className="text-gray-400 text-sm">
                Contributor counts, issue references, co-authored commits, and team coordination
              </p>
            </div>
          </div>
        </ExiqusCard>

        {/* What We DON'T Analyze */}
        <ExiqusCard className="mb-8 border-red-500/20 p-8">
          <ExiqusSectionHeader title="What We DON'T Analyze" icon={XCircle} />
          <p className="mb-6 text-gray-400">
            Transparency matters. Here&apos;s what our analysis explicitly does NOT cover:
          </p>

          <div className="grid gap-6 md:grid-cols-2">
            <div className="space-y-3">
              <h5 className="font-semibold text-red-400">Repository Limitations</h5>
              <ul className="space-y-2 text-gray-400 text-sm">
                <li className="flex items-start gap-2">
                  <XCircle className="mt-0.5 h-4 w-4 flex-shrink-0 text-red-500" />
                  <span>
                    <strong className="text-gray-300">Private Data:</strong> Private repositories
                    (coming soon)
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <XCircle className="mt-0.5 h-4 w-4 flex-shrink-0 text-red-500" />
                  <span>
                    <strong className="text-gray-300">Runtime Performance:</strong> Actual execution
                    speed or resource usage
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <XCircle className="mt-0.5 h-4 w-4 flex-shrink-0 text-red-500" />
                  <span>
                    <strong className="text-gray-300">Personal Metrics:</strong> Individual
                    productivity or time tracking
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <XCircle className="mt-0.5 h-4 w-4 flex-shrink-0 text-red-500" />
                  <span>
                    <strong className="text-gray-300">Subjective Quality:</strong> &quot;Good&quot;
                    vs &quot;bad&quot; code judgments
                  </span>
                </li>
              </ul>
            </div>

            <div className="space-y-3">
              <h5 className="font-semibold text-red-400">PR Analysis Limitations</h5>
              <ul className="space-y-2 text-gray-400 text-sm">
                <li className="flex items-start gap-2">
                  <XCircle className="mt-0.5 h-4 w-4 flex-shrink-0 text-red-500" />
                  <span>
                    <strong className="text-gray-300">Private PRs:</strong> Only public PRs are
                    accessible
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <XCircle className="mt-0.5 h-4 w-4 flex-shrink-0 text-red-500" />
                  <span>
                    <strong className="text-gray-300">Comment Content:</strong> Review decision
                    counts only, not text analysis
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <XCircle className="mt-0.5 h-4 w-4 flex-shrink-0 text-red-500" />
                  <span>
                    <strong className="text-gray-300">Code Quality:</strong> No static analysis or
                    runtime testing
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <XCircle className="mt-0.5 h-4 w-4 flex-shrink-0 text-red-500" />
                  <span>
                    <strong className="text-gray-300">Behavioral Inferences:</strong> No personality
                    traits or &quot;cultural fit&quot;
                  </span>
                </li>
              </ul>
            </div>
          </div>
        </ExiqusCard>

        {/* Context-Aware Analysis */}
        <ExiqusCard className="mb-8 p-8">
          <ExiqusSectionHeader title="Context-Aware Analysis" icon={Layers} />
          <p className="mb-6 text-gray-400">
            We understand that different roles require different evaluation. A startup needs
            builders who can experiment and iterate. An enterprise needs architects who consider
            scale and maintainability. A junior developer shows different evidence patterns than a
            senior technical leader. We tailor our analysis accordingly.
          </p>

          <h4 className="mb-4 font-semibold text-gray-200 text-lg">Company Context</h4>
          <div className="mb-8 space-y-4">
            <div className="rounded-lg border border-purple-500/20 p-4">
              <h4 className="mb-2 font-semibold text-purple-400">Startup Context</h4>
              <p className="text-gray-400 text-sm">
                For experimental projects, we explore innovation, learning agility, and rapid
                prototyping skills. Perfect for evaluating builders and early-stage contributors.
              </p>
            </div>

            <div className="rounded-lg border border-blue-500/20 p-4">
              <h4 className="mb-2 font-semibold text-blue-400">Enterprise Context</h4>
              <p className="text-gray-400 text-sm">
                For production-ready code, we assess architectural decisions, team collaboration,
                and maintainability practices.
              </p>
            </div>

            <div className="rounded-lg border border-green-500/20 p-4">
              <h4 className="mb-2 font-semibold text-green-400">Open Source Context</h4>
              <p className="text-gray-400 text-sm">
                For community projects, we evaluate contribution quality, documentation, and
                collaborative development skills.
              </p>
            </div>

            <div className="rounded-lg border border-amber-500/20 p-4">
              <h4 className="mb-2 font-semibold text-amber-400">Agency Context</h4>
              <p className="text-gray-400 text-sm">
                For client-ready developers, we assess versatility, professional practices, and
                ability to deliver under constraints.
              </p>
            </div>
          </div>

          <h4 className="mb-4 font-semibold text-gray-200 text-lg">Seniority Context</h4>
          <div className="space-y-4">
            <div className="rounded-lg border border-green-500/20 p-4">
              <h4 className="mb-2 font-semibold text-green-400">Junior (0-2 years)</h4>
              <p className="text-gray-400 text-sm">
                We look for learning fundamentals, code comprehension, and growth trajectory.
                Evidence of experimentation, following established patterns, and building confidence
                through repetition.
              </p>
            </div>

            <div className="rounded-lg border border-blue-500/20 p-4">
              <h4 className="mb-2 font-semibold text-blue-400">Mid-Level (3-5 years)</h4>
              <p className="text-gray-400 text-sm">
                We assess independent problem-solving, technical decision-making, and ownership of
                features. Evidence of navigating ambiguity, balancing tradeoffs, and contributing
                without heavy guidance.
              </p>
            </div>

            <div className="rounded-lg border border-purple-500/20 p-4">
              <h4 className="mb-2 font-semibold text-purple-400">Senior (5+ years)</h4>
              <p className="text-gray-400 text-sm">
                We examine technical leadership, architectural thinking, and long-term impact.
                Evidence of mentorship, system design, cross-functional collaboration, and guiding
                team-level technical decisions.
              </p>
            </div>
          </div>

          <div className="mt-6 rounded-lg bg-yellow-500/10 p-4">
            <p className="text-sm text-yellow-300">
              <AlertTriangle className="mb-1 inline h-4 w-4" />
              <strong>Transparency Note:</strong> If a repository has limited patterns for a
              specific context, we&apos;ll tell you. An experimental notebook might generate fewer
              enterprise-focused questions - and that&apos;s honest feedback, not a limitation.
            </p>
          </div>
        </ExiqusCard>

        {/* Evidence Hierarchy */}
        <ExiqusCard className="mb-8 p-8">
          <ExiqusSectionHeader title="The Evidence Hierarchy" icon={Layers} />
          <div className="mb-6 rounded-lg border border-amber-500/20 bg-amber-500/10 p-4">
            <p className="mb-2 flex items-center gap-2 font-semibold text-amber-400">
              <AlertTriangle className="h-5 w-5" />
              Important: Insights are Repository-Dependent, Not Fixed
            </p>
            <p className="text-gray-300 text-sm">
              The number of insights generated is{' '}
              <span className="font-semibold text-amber-400">
                deterministic based on repository content
              </span>
              , not a fixed quota. A minimal repo might generate only 1-2 insights, while
              feature-rich repos like tinygrad or facebook/react can generate 25-30 insights. We
              never generate artificial insights just to hit a number - every insight is based on
              actual evidence found in the repository.
            </p>
          </div>

          <div className="space-y-6">
            {[
              {
                level: 'Direct Observations',
                confidence: 'Highest Confidence',
                examples: [
                  'File counts and sizes',
                  'Language percentages',
                  'PR counts and merge status',
                  'Review decisions (APPROVED, CHANGES_REQUESTED)',
                ],
                color: 'text-green-400 border-green-400/20 bg-green-400/5',
              },
              {
                level: 'Derived Patterns',
                confidence: 'High Confidence',
                examples: [
                  'Test coverage ratios',
                  'Commit frequency trends',
                  'Merge success rates',
                  'Review cycle patterns',
                ],
                color: 'text-blue-400 border-blue-400/20 bg-blue-400/5',
              },
              {
                level: 'Development Patterns',
                confidence: 'Medium Confidence',
                examples: [
                  'Collaboration style (co-authored commits)',
                  'Code maintenance habits',
                  'Assignment patterns (PRs assigned vs authored)',
                  'Technical scope (surgical vs architectural)',
                ],
                color: 'text-purple-400 border-purple-400/20 bg-purple-400/5',
              },
              {
                level: 'Contextual Insights',
                confidence: 'Requires Human Interpretation',
                examples: [
                  'Domain expertise markers',
                  'Feature ownership patterns',
                  'Long-term commitment (sustained contributions)',
                  'Community engagement (external vs internal)',
                ],
                color: 'text-amber-400 border-amber-400/20 bg-amber-400/5',
              },
            ].map((tier, index) => (
              <div key={index} className={`rounded-lg border p-4 ${tier.color}`}>
                <div className="mb-2 flex items-start justify-between">
                  <h4 className="font-semibold">{tier.level}</h4>
                  <span className="rounded-full bg-white/10 px-2 py-1 text-xs">
                    {tier.confidence}
                  </span>
                </div>
                <p className="text-gray-400 text-sm">{tier.examples.join(' • ')}</p>
              </div>
            ))}
          </div>
        </ExiqusCard>

        {/* Repository Size Limits */}
        <ExiqusCard className="mb-8 p-8">
          <ExiqusSectionHeader title="Repository Size Limits by Tier" icon={Layers} />
          <p className="mb-6 text-gray-400">
            Our system analyses repositories of all sizes, with tier-based limits to ensure optimal
            performance:
          </p>

          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-lg border border-gray-700 bg-gray-800/50 p-4">
              <h4 className="mb-2 font-semibold text-gray-300">FREE/STARTER</h4>
              <p className="mb-2 font-bold text-2xl text-purple-400">Up to 500MB</p>
              <p className="text-gray-400 text-sm">Standard projects and libraries</p>
            </div>
            <div className="rounded-lg border border-purple-700 bg-purple-800/20 p-4">
              <h4 className="mb-2 font-semibold text-purple-300">GROWTH</h4>
              <p className="mb-2 font-bold text-2xl text-purple-400">Up to 2GB</p>
              <p className="text-gray-400 text-sm">Large frameworks and applications</p>
            </div>
            <div className="rounded-lg border border-blue-700 bg-blue-800/20 p-4">
              <h4 className="mb-2 font-semibold text-blue-300">SCALE</h4>
              <p className="mb-2 font-bold text-2xl text-blue-400">Up to 5GB</p>
              <p className="text-gray-400 text-sm">Enterprise systems and major projects</p>
            </div>
          </div>

          <div className="mt-4 rounded-lg border border-amber-500/20 bg-amber-500/10 p-4">
            <p className="text-gray-300 text-sm">
              <strong className="text-amber-400">Note:</strong> If a repository exceeds your tier
              limit, the system will suggest upgrading to analyse larger repositories. We never
              attempt partial or incomplete analysis.
            </p>
          </div>
        </ExiqusCard>

        {/* Edge Cases */}
        <ExiqusCard className="mb-8 p-8">
          <ExiqusSectionHeader title="Handling Edge Cases" icon={AlertTriangle} />

          <div className="grid gap-6 md:grid-cols-3">
            <div className="space-y-2">
              <h4 className="font-semibold text-amber-400">Minimal/Empty Repos</h4>
              <p className="text-gray-400 text-sm">
                When a repository has less than 10KB of code and fewer than 5 files, we honestly
                tell you it lacks sufficient content for meaningful analysis rather than generating
                fluff
              </p>
            </div>
            <div className="space-y-2">
              <h4 className="font-semibold text-amber-400">Monorepos</h4>
              <p className="text-gray-400 text-sm">
                Smart sampling ensures efficient analysis without timeouts, maintaining accuracy
                despite size (up to 5GB on Scale tier)
              </p>
            </div>
            <div className="space-y-2">
              <h4 className="font-semibold text-amber-400">Documentation-Only</h4>
              <p className="text-gray-400 text-sm">
                Properly classified with no code quality claims, focusing solely on documentation
                evidence
              </p>
            </div>
          </div>
        </ExiqusCard>

        {/* Interview Questions */}
        <ExiqusCard className="mb-8 p-8">
          <ExiqusSectionHeader title="Interview Question Generation" icon={Users} />
          <p className="mb-4 text-gray-400">
            Available across all tiers, our AI generates questions that are:
          </p>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="flex items-start gap-3">
              <Zap className="mt-1 h-5 w-5 text-purple-400" />
              <div>
                <h4 className="font-semibold text-gray-300">Evidence-Based</h4>
                <p className="text-gray-400 text-sm">Reference specific repository data</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Target className="mt-1 h-5 w-5 text-purple-400" />
              <div>
                <h4 className="font-semibold text-gray-300">Practice-Focused</h4>
                <p className="text-gray-400 text-sm">Focus on technical approaches</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Shield className="mt-1 h-5 w-5 text-purple-400" />
              <div>
                <h4 className="font-semibold text-gray-300">Context-Aware</h4>
                <p className="text-gray-400 text-sm">Tailored to your hiring situation</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Users className="mt-1 h-5 w-5 text-purple-400" />
              <div>
                <h4 className="font-semibold text-gray-300">Open-Ended</h4>
                <p className="text-gray-400 text-sm">Encourage discussion, not yes/no</p>
              </div>
            </div>
          </div>

          <div className="mt-6 rounded-lg border border-purple-500/20 bg-purple-500/10 p-4">
            <p className="text-gray-300 text-sm">
              <strong>Example Question:</strong> &quot;I noticed 27 of your commits were bug fixes.
              Walk me through your approach to debugging in a fast-moving startup environment.&quot;
            </p>
          </div>
        </ExiqusCard>

        {/* The Human Element */}
        <ExiqusCard className="bg-gradient-to-br from-purple-900/10 to-blue-900/10 p-8">
          <ExiqusSectionHeader title="The Human Element" icon={Users} />
          <p className="mb-6 text-gray-400">
            Our analysis is designed to augment human judgment, not replace it:
          </p>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="flex items-start gap-3">
              <CheckCircle className="mt-1 h-5 w-5 text-green-500" />
              <div>
                <strong className="text-gray-300">Provide evidence</strong> for discussion, not
                decisions
              </div>
            </div>
            <div className="flex items-start gap-3">
              <CheckCircle className="mt-1 h-5 w-5 text-green-500" />
              <div>
                <strong className="text-gray-300">Generate questions</strong> for interviews, not
                answers
              </div>
            </div>
            <div className="flex items-start gap-3">
              <CheckCircle className="mt-1 h-5 w-5 text-green-500" />
              <div>
                <strong className="text-gray-300">Surface patterns</strong> for exploration, not
                conclusions
              </div>
            </div>
            <div className="flex items-start gap-3">
              <CheckCircle className="mt-1 h-5 w-5 text-green-500" />
              <div>
                <strong className="text-gray-300">Augment expertise</strong> with data, not replace
                it
              </div>
            </div>
          </div>
        </ExiqusCard>

        {/* Footer */}
        <div className="mt-12 text-center text-gray-500">
          <p>Last Updated: October 2025</p>
          <p>Methodology Version: 2.0 - Evidence-Based Approach</p>
        </div>
      </div>
    </div>
  );
}
