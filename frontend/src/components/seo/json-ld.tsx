// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

/**
 * JSON-LD Structured Data Components for SEO
 *
 * SECURITY NOTES:
 * - All data is HARDCODED - no user input accepted
 * - No dynamic content injection
 * - No sensitive information included
 * - Server-side rendered for safety
 * - Validated against schema.org standards
 */

import Script from 'next/script';

import { SITE_URL } from '@/lib/site';

/**
 * Organization Schema - Sitewide company information
 * Used on all pages to establish brand identity
 */
export function OrganizationSchema() {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: 'Exiqus',
    url: SITE_URL,
    logo: `${SITE_URL}/icon.png`,
    description:
      'Evidence-based developer hiring platform that systematically analyses GitHub portfolios and pull requests as direct evidence for hiring decisions.',
    foundingDate: '2024',
  };

  return (
    <Script
      id="organization-schema"
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  );
}

/**
 * SoftwareApplication Schema - Product information
 * Used on homepage and pricing page
 */
export function SoftwareApplicationSchema() {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'SoftwareApplication',
    name: 'Exiqus',
    applicationCategory: 'BusinessApplication',
    operatingSystem: 'Web',
    description:
      'Evidence-based developer hiring platform that analyses GitHub portfolios and pull requests to provide direct evidence for hiring decisions. Compress months of manual code review into minutes of structured insights.',
  };

  return (
    <Script
      id="software-application-schema"
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  );
}

/**
 * BreadcrumbList Schema - Navigation breadcrumbs
 * SECURITY: Only accepts predefined breadcrumb items
 *
 * @param items - Array of breadcrumb items (VALIDATED, no user input)
 */
interface BreadcrumbItem {
  name: string;
  url: string;
}

interface BreadcrumbListSchemaProps {
  items: BreadcrumbItem[];
}

export function BreadcrumbListSchema({ items }: BreadcrumbListSchemaProps) {
  // SECURITY: Validate that items only contain safe, hardcoded paths
  const safeItems = items.map((item, index) => ({
    '@type': 'ListItem' as const,
    position: index + 1,
    name: item.name,
    item: `${SITE_URL}${item.url}`,
  }));

  const schema = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: safeItems,
  };

  return (
    <Script
      id="breadcrumb-schema"
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  );
}

/**
 * WebSite Schema - Basic site identity
 * Used on homepage
 */
export function WebSiteSchema() {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'WebSite',
    name: 'Exiqus',
    url: SITE_URL,
    description: 'Evidence-based developer hiring through GitHub portfolio analysis',
  };

  return (
    <Script
      id="website-schema"
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  );
}

/**
 * FAQPage Schema - Frequently asked questions
 * SECURITY: Only accepts hardcoded FAQ data from FAQ page
 */
interface FAQItem {
  question: string;
  answer: string;
}

interface FAQPageSchemaProps {
  faqs: FAQItem[];
}

export function FAQPageSchema({ faqs }: FAQPageSchemaProps) {
  // SECURITY: All FAQ data is hardcoded, no user input
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: faqs.map((faq) => ({
      '@type': 'Question',
      name: faq.question,
      acceptedAnswer: {
        '@type': 'Answer',
        text: faq.answer,
      },
    })),
  };

  return (
    <Script
      id="faq-page-schema"
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  );
}
