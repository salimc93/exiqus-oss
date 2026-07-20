// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import { ChevronDown, ChevronUp, HelpCircle } from 'lucide-react';
import { useState } from 'react';

import { FAQPageSchema } from '@/components/seo/json-ld';
import { ExiqusCard, GradientText } from '@/components/ui/exiqus-components';

interface FAQItem {
  question: string;
  answer: string;
  category: 'general' | 'pricing' | 'technical' | 'privacy';
}

const faqs: FAQItem[] = [
  // General Questions
  {
    question: 'What is Exiqus?',
    answer:
      'Exiqus is an evidence-based developer hiring platform that systematically analyses GitHub portfolios and pull requests as direct evidence for hiring decisions. We help you assess complete candidate portfolios—from technical evolution to collaboration patterns—without subjective scores or algorithmic puzzles. Real work, not performance theatre.',
    category: 'general',
  },
  {
    question: 'How does Exiqus work?',
    answer:
      'Enter a GitHub username to analyse their complete portfolio, or analyse individual repositories and pull requests. Paid users can select hiring context (Startup, Enterprise, Agency, Open Source) and role level (Junior, Mid, Senior) to generate evidence-based insights with contextual interview questions tailored to your needs. FREE users get Open Source context only with basic analysis. No scores, no grades—just observable facts about real work.',
    category: 'general',
  },
  {
    question: 'What can I analyse with Exiqus?',
    answer:
      'Free users can analyse individual public repositories (repository deep dives). Paid users unlock candidate insights: Portfolio Analysis (complete developer portfolio across all repos), PR Analysis (pull request contributions and collaboration patterns), and Candidate Hub (unified view of all analyses for a developer). All analyses work with public GitHub data only.',
    category: 'general',
  },
  {
    question: 'How is Exiqus different from other assessment tools?',
    answer:
      "We're pioneering evidence-based hiring powered by real developer work. Unlike LeetCode-style tests, we analyse actual code contributions. Unlike manual code review (what companies like Zed Industries spend months doing), we systematise it into minutes. We're building the world's first validated dataset connecting GitHub evidence to hiring outcomes. No peer-reviewed research or commercial platform has done this—we're filling both the academic and market gap.",
    category: 'general',
  },
  {
    question: 'Can I analyse private repositories?',
    answer:
      'Not at this time. Exiqus analyses public GitHub data only. However, if your candidates have contributed PRs to public open-source projects (like the Zed hire did), we can analyze those. GitHub has 100 million developers—most have SOME public work: PRs to OSS projects, side projects from when they were learning, or contributions to company OSS initiatives. This works best for dev-tool companies, OSS contributors, and candidates with public GitHub activity.',
    category: 'general',
  },
  {
    question: 'Who is Exiqus best for?',
    answer:
      "Exiqus works best for: (1) Dev-tool startups (like Zed, Linear, Supabase) who hire from OSS contributors, (2) Technical hiring managers tired of LeetCode theater, (3) Companies hiring remote developers globally, (4) Candidates with public GitHub work (PRs to major projects, side projects, learning repos). This doesn't work well for: (1) Companies hiring only from private repos (though we can analyze PRs to public projects), (2) Companies committed to whiteboard interviews, (3) Candidates with zero public GitHub activity.",
    category: 'general',
  },
  // Pricing Questions
  {
    question: "What's included in the Free tier?",
    answer:
      'The Free tier includes 3 repository deep dives per month with Open Source context only (no role selection). Perfect for exploring repos and testing the platform. Upgrade to Starter ($49/month) to unlock ALL contexts (Startup/Enterprise/Agency/Open Source), ALL role levels (Junior/Mid/Senior), AND candidate insight features: Portfolio Analysis, PR Analysis, and Candidate Hub.',
    category: 'pricing',
  },
  {
    question: "What's the difference between candidate insights and repository deep dives?",
    answer:
      'Candidate insights (Portfolio + PR Analysis) evaluate a complete developer across their entire GitHub presence—technical evolution, collaboration patterns, and work history. Repository deep dives analyse a single repo for code quality and patterns. Free users get repo deep dives only. Paid users get both: candidate insights for hiring decisions, plus repo deep dives for technical evaluation.',
    category: 'pricing',
  },
  {
    question: 'Can I change my plan anytime?',
    answer:
      "Yes! You can upgrade or downgrade your plan at any time. When upgrading, you'll have immediate access to enhanced features. When downgrading, changes take effect at the next billing cycle.",
    category: 'pricing',
  },
  {
    question: 'Do you offer trials for paid plans?',
    answer:
      'Yes! Free trials are available for paid tiers (Starter, Growth, and Scale). Reach out via the contact page with your use case, or start with the Free tier to explore the platform on your own.',
    category: 'pricing',
  },
  {
    question: 'Do you offer annual billing?',
    answer:
      "Currently, we only offer monthly billing. We're considering annual plans with discounts for the future based on user feedback.",
    category: 'pricing',
  },
  {
    question: 'What payment methods do you accept?',
    answer:
      'We accept all major credit cards through our secure payment processor, Stripe. All payment information is encrypted and we never store your card details.',
    category: 'pricing',
  },
  // Technical Questions
  {
    question: 'How accurate are the AI insights?',
    answer:
      'Our AI uses anti-hallucination safeguards and reports only observable evidence from actual code, commits, and pull requests. We never assign scores or invent expertise. Every insight must be grounded in verifiable patterns. The quality improves with richer portfolios—developers with extensive commit history, documentation, and collaboration patterns provide more evidence to analyse.',
    category: 'technical',
  },
  {
    question: 'What is Portfolio Analysis?',
    answer:
      "Portfolio Analysis evaluates a developer's complete GitHub portfolio across all their public repositories. We analyse technical evolution (how their skills developed over time), architectural patterns, code ownership, testing practices, and documentation quality. Available on Starter tier and above. This is your primary tool for candidate insights—understanding who they are as a developer, not just one repo.",
    category: 'technical',
  },
  {
    question: 'What is PR Analysis?',
    answer:
      "PR Analysis (Beta) examines a developer's pull request contributions across open source projects and collaborations. We analyse code review quality, collaboration patterns, communication skills, and how they work with other developers. Available on all paid tiers. Perfect for understanding how candidates contribute to team codebases beyond their solo work.",
    category: 'technical',
  },
  {
    question: 'What languages and frameworks do you support?',
    answer:
      "Exiqus analyses code in any programming language. Our AI recognises patterns across all major languages, frameworks, and tools. We're language-agnostic—evidence is evidence, whether it's TypeScript, Python, Rust, or Go.",
    category: 'technical',
  },
  {
    question: 'How long does an analysis take?',
    answer:
      'Repository deep dives: 60-90 seconds. Portfolio Analysis: 2-4 minutes (analysing entire developer history). PR Analysis: 3-5 minutes (examining collaboration across multiple projects). Analysis time varies based on portfolio size and complexity.',
    category: 'technical',
  },
  {
    question: 'What are evidence-based interview questions?',
    answer:
      'Every paid tier generates contextual interview questions grounded in actual code and decisions from the candidate\'s work. For example: "Your portfolio shows a shift from monolithic architecture to microservices in Project X. What drove this architectural evolution?" These questions are impossible to rehearse - only the actual developer who wrote the code can answer them authentically.',
    category: 'technical',
  },
  {
    question: 'Do you have an API?',
    answer:
      "Not in our current MVP. We're focusing on perfecting the web experience first. API access is planned for future releases based on user demand.",
    category: 'technical',
  },
  // Privacy & Support Questions
  {
    question: 'How do you handle my data?',
    answer:
      "We analyse repositories in real-time and don't permanently store repository code. Analysis results are saved for your reference, but the actual repository data is fetched fresh for each analysis. We take privacy seriously and never share your analysis data.",
    category: 'privacy',
  },
  {
    question: 'How does support work?',
    answer:
      'All support is handled through our integrated messaging system. Submit a message through the contact form or your dashboard, and our team will respond within 24-48 hours. Professional and Enterprise tiers receive priority support with faster response times.',
    category: 'privacy',
  },
  {
    question: 'Can I export my analysis reports?',
    answer:
      'Yes! The Free tier supports JSON export only. Starter, Growth, and Scale tiers can export reports in JSON, HTML, and PDF formats for maximum flexibility.',
    category: 'privacy',
  },
  {
    question: 'Is my analysis history private?',
    answer:
      'Absolutely. Your analysis history is private to your account. We never share your data with third parties, and you have full control over your analysis history.',
    category: 'privacy',
  },
  {
    question: 'Do you store GitHub access tokens?',
    answer:
      "No, we don't require or store any GitHub access tokens. All our analyses work with publicly available repository data accessed through GitHub's public API.",
    category: 'privacy',
  },
  {
    question: 'How do I delete my account?',
    answer:
      'To request account deletion, please contact our support team through the contact form or send us a message from your dashboard. We handle deletion requests manually to ensure security and to understand how we can improve. Your account will be deactivated immediately and permanently deleted after 30 days, giving you time to change your mind if needed. All your data, analyses, and associated information will be completely removed.',
    category: 'privacy',
  },
];

export default function FAQPage() {
  const [openItems, setOpenItems] = useState<Set<number>>(new Set());
  const [activeCategory, setActiveCategory] = useState<string>('all');

  const toggleItem = (index: number) => {
    const newOpenItems = new Set(openItems);
    if (newOpenItems.has(index)) {
      newOpenItems.delete(index);
    } else {
      newOpenItems.add(index);
    }
    setOpenItems(newOpenItems);
  };

  const filteredFAQs =
    activeCategory === 'all' ? faqs : faqs.filter((faq) => faq.category === activeCategory);

  const categories = [
    { value: 'all', label: 'All Questions', count: faqs.length },
    {
      value: 'general',
      label: 'General',
      count: faqs.filter((f) => f.category === 'general').length,
    },
    {
      value: 'pricing',
      label: 'Pricing',
      count: faqs.filter((f) => f.category === 'pricing').length,
    },
    {
      value: 'technical',
      label: 'Technical',
      count: faqs.filter((f) => f.category === 'technical').length,
    },
    {
      value: 'privacy',
      label: 'Privacy & Support',
      count: faqs.filter((f) => f.category === 'privacy').length,
    },
  ];

  return (
    <div className="min-h-screen bg-[#0A0A0A] text-white">
      {/* JSON-LD FAQ Schema for "People Also Ask" in Google */}
      <FAQPageSchema faqs={faqs} />

      <div className="mx-auto max-w-4xl px-4 py-16 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-12 text-center">
          <div className="mb-6 flex justify-center">
            <div className="rounded-xl bg-purple-500/10 p-4">
              <HelpCircle className="h-12 w-12 text-purple-400" />
            </div>
          </div>
          <h1 className="mb-4 font-bold text-4xl md:text-5xl">
            <GradientText>Frequently Asked Questions</GradientText>
          </h1>
          <p className="text-gray-400 text-xl">Everything you need to know about Exiqus</p>
        </div>

        {/* Category Filter */}
        <div className="mb-8 flex flex-wrap justify-center gap-2">
          {categories.map((category) => (
            <button
              type="button"
              key={category.value}
              onClick={() => setActiveCategory(category.value)}
              className={`rounded-lg px-4 py-2 font-medium text-sm transition-all ${
                activeCategory === category.value
                  ? 'bg-gradient-to-r from-purple-600 to-blue-600 text-white'
                  : 'bg-white/[0.06] text-gray-400 hover:bg-white/[0.09] hover:text-white'
              }`}
            >
              {category.label} ({category.count})
            </button>
          ))}
        </div>

        {/* FAQ Items */}
        <div className="space-y-4">
          {filteredFAQs.map((faq) => {
            const globalIndex = faqs.indexOf(faq);
            const isOpen = openItems.has(globalIndex);

            return (
              <ExiqusCard
                key={globalIndex}
                className="overflow-hidden transition-all duration-200"
                hover={true}
              >
                <button
                  type="button"
                  onClick={() => toggleItem(globalIndex)}
                  className="flex w-full items-start justify-between gap-4 p-6 text-left"
                >
                  <div className="flex-1">
                    <h3 className="mb-1 font-semibold text-gray-100 text-lg">{faq.question}</h3>
                    {isOpen && <p className="mt-3 text-gray-400 leading-relaxed">{faq.answer}</p>}
                  </div>
                  <div className="mt-1 flex-shrink-0">
                    {isOpen ? (
                      <ChevronUp className="h-5 w-5 text-gray-400" />
                    ) : (
                      <ChevronDown className="h-5 w-5 text-gray-400" />
                    )}
                  </div>
                </button>
              </ExiqusCard>
            );
          })}
        </div>

        {/* Contact CTA */}
        <div className="mt-16 text-center">
          <ExiqusCard className="bg-gradient-to-br from-purple-900/10 to-blue-900/10 p-8">
            <h2 className="mb-4 font-bold text-2xl">Still have questions?</h2>
            <p className="mb-6 text-gray-400">
              Can&apos;t find the answer you&apos;re looking for? Send us a message and we&apos;ll
              get back to you within 24-48 hours.
            </p>
            <a
              href="/contact"
              className="inline-flex items-center justify-center rounded-md bg-gradient-to-r from-purple-600 to-blue-600 px-6 py-3 font-medium text-white transition-opacity hover:opacity-90"
            >
              Contact Support
            </a>
          </ExiqusCard>
        </div>
      </div>
    </div>
  );
}
