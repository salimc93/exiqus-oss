// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

import { ArrowRight, FlaskConical, Microscope, User } from 'lucide-react';
import React from 'react';

import { ExiqusCard } from '@/components/ui/exiqus-components';

const steps = [
  {
    number: '1',
    title: 'Enter GitHub Username',
    description: "Enter a candidate's GitHub username to analyse their real contributions and code",
    icon: <User className="h-8 w-8" />,
  },
  {
    number: '2',
    title: 'Select Context & Role',
    description:
      'Choose your hiring context (Startup, Enterprise, Agency, or Open Source) and role level (Junior, Mid, or Senior) for tailored insights',
    icon: <Microscope className="h-8 w-8" />,
  },
  {
    number: '3',
    title: 'Get Candidate Insights',
    description:
      'Deep portfolio intelligence, PR analysis, and evidence-based interview questions—all grounded in real work, not test scores',
    icon: <FlaskConical className="h-8 w-8" />,
  },
];

export default function HowItWorks() {
  return (
    <div className="mx-auto max-w-6xl">
      <div className="relative grid gap-8 md:grid-cols-3">
        {/* Connection lines for desktop */}
        <div className="absolute top-20 right-1/4 left-1/4 hidden h-px bg-gradient-to-r from-purple-600/20 via-purple-600/40 to-purple-600/20 md:block"></div>

        {steps.map((step, index) => (
          <div key={step.number} className="relative">
            <ExiqusCard className="h-full p-8 text-center">
              {/* Step number */}
              <div className="relative mb-6 inline-flex h-16 w-16 items-center justify-center">
                <div className="absolute inset-0 animate-pulse rounded-full bg-gradient-to-r from-purple-600 to-blue-600 opacity-20"></div>
                <div className="relative flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-r from-purple-600 to-blue-600 font-bold text-white text-xl">
                  {step.number}
                </div>
              </div>

              {/* Icon */}
              <div className="mb-4 flex justify-center">
                <div className="relative">
                  {/* Background glow effect */}
                  <div className="absolute inset-0 bg-gradient-to-r from-purple-600 to-blue-600 opacity-40 blur-xl"></div>
                  {/* Icon with gradient */}
                  <div className="relative rounded-xl bg-gradient-to-r from-purple-500 to-blue-500 p-3">
                    {React.cloneElement(step.icon, { className: 'h-8 w-8 text-white' })}
                  </div>
                </div>
              </div>

              {/* Content */}
              <h3 className="mb-2 font-bold text-gray-100 text-xl">{step.title}</h3>
              <p className="text-gray-400">{step.description}</p>
            </ExiqusCard>

            {/* Arrow for mobile */}
            {index < steps.length - 1 && (
              <div className="my-6 flex justify-center md:hidden">
                <ArrowRight className="h-6 w-6 rotate-90 text-gray-600" />
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="mt-12 text-center">
        <p className="mb-6 text-gray-400 text-lg">
          Ready to revolutionize your technical hiring process?
        </p>
      </div>
    </div>
  );
}
