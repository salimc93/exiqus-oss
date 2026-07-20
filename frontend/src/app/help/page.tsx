// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import { ArrowLeft, ChevronDown, ChevronUp, HelpCircle } from 'lucide-react';
import Link from 'next/link';
import type React from 'react';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

interface FAQItem {
  question: string;
  answer: string | React.ReactNode;
  category: 'getting-started' | 'pricing' | 'technical' | 'account';
}

const faqs: FAQItem[] = [
  // Getting Started
  {
    question: 'How do I analyse a repository?',
    answer: (
      <div>
        <p className="mb-2">It&apos;s simple! Just follow these steps:</p>
        <ol className="ml-5 list-decimal space-y-1">
          <li>Sign up for a free account</li>
          <li>Go to the analysis page</li>
          <li>Paste any GitHub repository URL</li>
          <li>Select the analysis context (startup, enterprise, agency, or open source)</li>
          <li>Click &quot;Analyze&quot; and get results in 30 seconds!</li>
        </ol>
      </div>
    ),
    category: 'getting-started',
  },
  {
    question: 'How do I analyse a private repository?',
    answer: (
      <div>
        <p className="mb-2">
          Private repository analysis requires a Professional or Enterprise plan.
        </p>
        <p className="mb-2">Once upgraded:</p>
        <ol className="ml-5 list-decimal space-y-1">
          <li>Connect your GitHub account in settings</li>
          <li>Grant repository access permissions</li>
          <li>Analyze private repos just like public ones!</li>
        </ol>
        <Link href="/pricing" className="mt-2 inline-block text-primary hover:underline">
          View pricing plans →
        </Link>
      </div>
    ),
    category: 'getting-started',
  },

  // Pricing & Billing
  {
    question: 'What counts as an analysis?',
    answer:
      "Each time you analyse a repository (whether successful or not), it counts as one analysis against your monthly limit. Re-analysing the same repository also counts as a new analysis. Cached results (within 24 hours) don't count against your limit.",
    category: 'pricing',
  },
  {
    question: "What's the difference between plans?",
    answer: (
      <div>
        <p className="mb-3">Our plans are designed to scale with your needs:</p>
        <ul className="space-y-2">
          <li>
            <strong>Free:</strong> 10 analyses/month, public repos only
          </li>
          <li>
            <strong>Basic ($49):</strong> 100 analyses/month, public repos, export reports
          </li>
          <li>
            <strong>Professional ($149):</strong> 500 analyses/month, private repos, API access
          </li>
          <li>
            <strong>Enterprise ($399):</strong> 2,000 analyses/month, priority support, custom
            integrations
          </li>
        </ul>
      </div>
    ),
    category: 'pricing',
  },
  {
    question: 'Can I change my plan anytime?',
    answer:
      'Yes! You can upgrade or downgrade your plan at any time. Upgrades take effect immediately, while downgrades take effect at the start of your next billing cycle.',
    category: 'pricing',
  },
  {
    question: 'What happens if I exceed my monthly limit?',
    answer:
      'For Professional and Enterprise plans, you can continue analysing at the overage rate ($0.20 and $0.10 per analysis respectively). Free and Basic plans will need to wait for the next billing cycle or upgrade.',
    category: 'pricing',
  },

  // Technical
  {
    question: 'How accurate are the AI insights?',
    answer:
      'Our AI analyses code quality, architecture patterns, and development practices to provide evidence-based insights about repositories. It identifies factual patterns, metrics, and observable evidence from the codebase - helping you understand development practices, technology usage, and project structure. The analysis is purely objective and evidence-based, focusing on what can be directly observed in the code without making subjective judgements.',
    category: 'technical',
  },
  {
    question: 'Can I export analysis reports?',
    answer: (
      <div>
        <p className="mb-2">Export functionality is available on paid plans:</p>
        <ul className="ml-5 list-disc space-y-1">
          <li>
            <strong>Basic and above:</strong> PDF and JSON exports
          </li>
          <li>
            <strong>Professional and above:</strong> PDF, JSON, HTML, and Markdown exports
          </li>
        </ul>
        <p className="mt-2">Free plan users can view reports online but cannot export them.</p>
      </div>
    ),
    category: 'technical',
  },
  {
    question: 'How do I get API access?',
    answer: (
      <div>
        <p className="mb-2">API access is available for Professional and Enterprise plans.</p>
        <p className="mb-2">To get started:</p>
        <ol className="ml-5 list-decimal space-y-1">
          <li>Upgrade to Professional or Enterprise</li>
          <li>Go to your dashboard</li>
          <li>Navigate to API Keys section</li>
          <li>Generate your API key</li>
        </ol>
        <p className="mt-2">Full API documentation will be available in your dashboard.</p>
      </div>
    ),
    category: 'technical',
  },
  {
    question: 'What information does the analysis include?',
    answer: (
      <div>
        <p className="mb-2">Our comprehensive analysis covers:</p>
        <ul className="ml-5 list-disc space-y-1">
          <li>Code quality and best practices</li>
          <li>Architecture and design patterns</li>
          <li>Testing and documentation practices</li>
          <li>Technology stack proficiency</li>
          <li>Collaboration indicators</li>
          <li>Project complexity handling</li>
          <li>Overall recommendation with confidence score</li>
        </ul>
      </div>
    ),
    category: 'technical',
  },

  // Account & Security
  {
    question: "Why haven't I received my verification email?",
    answer: (
      <div id="email-verification">
        <p className="mb-2">If you haven&apos;t received your verification email:</p>
        <ol className="ml-5 list-decimal space-y-1">
          <li>
            <strong>Check your spam/junk folder</strong> - Sometimes emails end up there
          </li>
          <li>
            <strong>Verify your email address</strong> - Make sure you entered it correctly during
            signup
          </li>
          <li>
            <strong>Wait a few minutes</strong> - Email delivery can sometimes be delayed
          </li>
          <li>
            <strong>Check email filters</strong> - Ensure emails from this Exiqus instance
            aren&apos;t blocked
          </li>
          <li>
            <strong>Resend the email</strong> - Visit the verification pending page to resend
          </li>
        </ol>
        <p className="mt-3">If you still have issues after 30 minutes, please contact support.</p>
      </div>
    ),
    category: 'account',
  },
  {
    question: 'How long is the verification link valid?',
    answer:
      "Email verification links are valid for 24 hours. If your link has expired, you can request a new one from the login page by attempting to log in - you'll see an option to resend the verification email.",
    category: 'account',
  },
  {
    question: 'Can I change my email address after signing up?',
    answer:
      "Currently, email addresses cannot be changed after account creation. If you need to use a different email, you'll need to create a new account. Send us a message if you need help transferring your subscription.",
    category: 'account',
  },
  {
    question: 'How do I reset my password?',
    answer: (
      <div>
        <p className="mb-2">To reset your password:</p>
        <ol className="ml-5 list-decimal space-y-1">
          <li>Go to the login page</li>
          <li>Click &quot;Forgot password?&quot;</li>
          <li>Enter your email address</li>
          <li>Check your email for reset instructions</li>
          <li>Follow the link to set a new password</li>
        </ol>
      </div>
    ),
    category: 'account',
  },
  {
    question: 'Is my repository data secure?',
    answer:
      "Yes! We take security seriously. We only access repository data during analysis and don't store any source code. All data is encrypted in transit and at rest. Your repository content is never stored on our servers - we only keep the analysis results.",
    category: 'account',
  },
  {
    question: 'Can I delete my account?',
    answer: (
      <div>
        <p className="mb-2">We&apos;re sorry to see you go! To close your account:</p>
        <ol className="ml-5 list-decimal space-y-1">
          <li>Contact our support team through the contact form</li>
          <li>Let us know you&apos;d like to close your account</li>
          <li>We&apos;ll help resolve any issues or process your request</li>
        </ol>
        <p className="mt-2">
          This ensures proper handling of your data and any active subscriptions. We&apos;ll confirm
          deletion within 48 hours and permanently remove your data within 30 days per our retention
          policy.
        </p>
        <Link
          href="/contact?subject=account-deletion"
          className="mt-3 inline-flex items-center text-primary hover:underline"
        >
          Contact Support to Delete Account →
        </Link>
      </div>
    ),
    category: 'account',
  },
];

const categories = [
  { id: 'getting-started', label: 'Getting Started', icon: '🚀' },
  { id: 'pricing', label: 'Pricing & Billing', icon: '💳' },
  { id: 'technical', label: 'Technical Questions', icon: '⚙️' },
  { id: 'account', label: 'Account & Security', icon: '🔒' },
];

export default function HelpPage() {
  const [openItems, setOpenItems] = useState<Set<number>>(new Set());
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  const toggleItem = (index: number) => {
    setOpenItems((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      return newSet;
    });
  };

  const filteredFaqs =
    selectedCategory === 'all' ? faqs : faqs.filter((faq) => faq.category === selectedCategory);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 px-4 py-12">
      <div className="mx-auto max-w-4xl">
        {/* Header */}
        <div className="mb-12 text-center">
          <div className="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-r from-blue-600 to-purple-600">
            <HelpCircle className="h-8 w-8 text-white" />
          </div>
          <h1 className="mb-4 font-bold text-4xl">Help Center</h1>
          <p className="text-gray-600 text-xl">Find answers to common questions about Exiqus</p>
        </div>

        {/* Category Filter */}
        <div className="mb-8">
          <div className="flex flex-wrap justify-center gap-2">
            <Button
              variant={selectedCategory === 'all' ? 'default' : 'outline'}
              onClick={() => setSelectedCategory('all')}
              className={
                selectedCategory === 'all' ? 'bg-gradient-to-r from-blue-600 to-purple-600' : ''
              }
            >
              All Questions
            </Button>
            {categories.map((category) => (
              <Button
                key={category.id}
                variant={selectedCategory === category.id ? 'default' : 'outline'}
                onClick={() => setSelectedCategory(category.id)}
                className={
                  selectedCategory === category.id
                    ? 'bg-gradient-to-r from-blue-600 to-purple-600'
                    : ''
                }
              >
                <span className="mr-2">{category.icon}</span>
                {category.label}
              </Button>
            ))}
          </div>
        </div>

        {/* FAQ Items */}
        <div className="space-y-4">
          {filteredFaqs.map((faq, index) => {
            const isOpen = openItems.has(index);

            return (
              <Card
                key={index}
                className="overflow-hidden transition-all duration-200 hover:shadow-md"
              >
                <button
                  type="button"
                  className="flex w-full items-center justify-between px-6 py-4 text-left transition-colors hover:bg-gray-50"
                  onClick={() => toggleItem(index)}
                >
                  <h3 className="pr-4 font-semibold text-lg">{faq.question}</h3>
                  {isOpen ? (
                    <ChevronUp className="h-5 w-5 flex-shrink-0 text-gray-400" />
                  ) : (
                    <ChevronDown className="h-5 w-5 flex-shrink-0 text-gray-400" />
                  )}
                </button>

                {isOpen && (
                  <div className="border-t px-6 pb-4 text-gray-600">
                    <div className="pt-4">
                      {typeof faq.answer === 'string' ? <p>{faq.answer}</p> : faq.answer}
                    </div>
                  </div>
                )}
              </Card>
            );
          })}
        </div>

        {/* Still need help? */}
        <div className="mt-12 text-center">
          <Card className="bg-gradient-to-r from-blue-50 to-purple-50 p-8">
            <h2 className="mb-4 font-bold text-2xl">Still have questions?</h2>
            <p className="mb-6 text-gray-600">
              Our support team is here to help you get the most out of Exiqus
            </p>
            <Link href="/contact">
              <Button
                size="lg"
                className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
              >
                Contact Support
              </Button>
            </Link>
          </Card>
        </div>

        {/* Back to home */}
        <div className="mt-8 text-center">
          <Link
            href="/"
            className="inline-flex items-center text-gray-600 transition hover:text-gray-900"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Home
          </Link>
        </div>
      </div>
    </div>
  );
}
