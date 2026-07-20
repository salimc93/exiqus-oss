// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

import type { Metadata } from 'next';

import { SITE_URL } from './site';

// Security: Sanitize text to prevent XSS in meta tags
function sanitizeMetaText(text: string): string {
  // Remove any HTML tags
  const withoutTags = text.replace(/<[^>]*>/g, '');
  // Remove special characters that could break HTML attributes
  const sanitized = withoutTags
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/&/g, '&amp;');
  return sanitized;
}

// Security: Validate URL to prevent open redirects
function isValidUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    // Only allow https and relative paths
    return parsed.protocol === 'https:' || url.startsWith('/');
  } catch {
    return url.startsWith('/'); // Allow relative paths
  }
}

export const siteConfig = {
  name: 'Exiqus',
  url: SITE_URL,
  description:
    'Evidence-Based Developer Hiring. Systematically analyze GitHub portfolios and pull requests as direct evidence for hiring decisions.',
  tagline: 'From Four Interviews to One. From Guesswork to Evidence.',
  ogImage: '/og-image.png',
  twitterImage: '/twitter-image.png',
} as const;

export function createMetadata({
  title,
  description,
  path = '',
  image,
}: {
  title: string;
  description?: string;
  path?: string;
  image?: string;
}): Metadata {
  // Security: Sanitize all user-facing text
  const sanitizedTitle = sanitizeMetaText(title);
  const sanitizedDescription = sanitizeMetaText(description || siteConfig.description);

  // Security: Validate image URL
  const imageUrl = image || siteConfig.ogImage;
  if (!isValidUrl(imageUrl)) {
    throw new Error('Invalid image URL provided to metadata');
  }

  // Security: Ensure path starts with / and doesn't contain dangerous characters
  const safePath = path.startsWith('/') ? path : `/${path}`;
  if (safePath.includes('<') || safePath.includes('>') || safePath.includes('"')) {
    throw new Error('Invalid path provided to metadata');
  }

  const fullTitle =
    sanitizedTitle === siteConfig.name ? sanitizedTitle : `${sanitizedTitle} | ${siteConfig.name}`;
  const metaDescription = sanitizedDescription;
  const url = `${siteConfig.url}${safePath}`;
  const ogImage = imageUrl;

  return {
    title: fullTitle,
    description: metaDescription,
    keywords: [
      'github analysis',
      'developer hiring',
      'portfolio analysis',
      'technical recruiting',
      'evidence-based hiring',
      'pull request analysis',
      'candidate assessment',
      'github portfolio',
      'developer assessment',
      'technical interview',
    ],
    authors: [{ name: 'Exiqus' }],
    creator: 'Exiqus',
    publisher: 'Exiqus',
    metadataBase: new URL(siteConfig.url),
    alternates: {
      canonical: url,
    },
    openGraph: {
      type: 'website',
      locale: 'en_US',
      url,
      title: fullTitle,
      description: metaDescription,
      siteName: siteConfig.name,
      images: [
        {
          url: ogImage,
          width: 1200,
          height: 630,
          alt: fullTitle,
        },
      ],
    },
    twitter: {
      card: 'summary_large_image',
      title: fullTitle,
      description: metaDescription,
      images: [image || siteConfig.twitterImage],
    },
    robots: {
      index: true,
      follow: true,
      googleBot: {
        index: true,
        follow: true,
        'max-video-preview': -1,
        'max-image-preview': 'large',
        'max-snippet': -1,
      },
    },
  };
}
