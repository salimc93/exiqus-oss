// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

import {
  Binary,
  Cpu,
  Fingerprint,
  Layers,
  MessageSquare,
  Microscope,
  ShieldCheck,
  TrendingUp,
} from 'lucide-react';
import React from 'react';

import { ExiqusCard } from '@/components/ui/exiqus-components';

const features = [
  {
    icon: <Microscope className="h-6 w-6" />,
    title: 'Evidence-Based Analysis',
    description: 'Get comprehensive insights based on actual code patterns, not arbitrary scores.',
  },
  {
    icon: <Layers className="h-6 w-6" />,
    title: 'Context-Aware Insights',
    description:
      'Choose from Startup, Enterprise, Agency, or Open Source contexts for tailored analysis.',
  },
  {
    icon: <ShieldCheck className="h-6 w-6" />,
    title: 'Secure Analysis',
    description: 'Your repository data is analyzed securely and never stored permanently.',
  },
  {
    icon: <Binary className="h-6 w-6" />,
    title: 'Deep Code Analysis',
    description: 'Understand code quality, patterns, and architectural decisions.',
  },
  {
    icon: <Fingerprint className="h-6 w-6" />,
    title: 'Pattern Recognition',
    description: 'Identify coding patterns, best practices, and areas of expertise.',
  },
  {
    icon: <MessageSquare className="h-6 w-6" />,
    title: 'AI-Generated Questions',
    description: 'Get targeted interview questions based on the code analysis.',
  },
  {
    icon: <Cpu className="h-6 w-6" />,
    title: 'Technology Detection',
    description: 'Automatically identify frameworks, languages, and tools used.',
  },
  {
    icon: <TrendingUp className="h-6 w-6" />,
    title: 'Growth Identification',
    description: 'Identify technical strengths and areas for potential growth.',
  },
];

export default function FeaturesGrid() {
  return (
    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
      {features.map((feature, index) => (
        <ExiqusCard
          key={index}
          className="p-6 transition-all duration-200 hover:border-white/[0.12]"
          hover={true}
        >
          <div className="flex items-start space-x-4">
            <div className="flex-shrink-0">
              <div className="rounded-lg bg-gradient-to-r from-purple-600/10 to-blue-600/10 p-3 text-purple-400">
                {feature.icon}
              </div>
            </div>
            <div>
              <h3 className="mb-2 font-bold text-gray-100 text-lg">{feature.title}</h3>
              <p className="text-gray-400 text-sm">{feature.description}</p>
            </div>
          </div>
        </ExiqusCard>
      ))}
    </div>
  );
}
