// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

import type { MetadataRoute } from 'next';

import { SITE_URL } from '@/lib/site';

export default function robots(): MetadataRoute.Robots {
  const baseUrl = SITE_URL;

  return {
    rules: [
      {
        userAgent: '*',
        allow: '/',
        disallow: [
          // API routes
          '/api/',

          // User-specific pages (authentication required)
          '/dashboard/',
          '/account/',
          '/billing/',

          // Analysis pages (private results)
          '/analyses/',
          '/pr-analyses/',
          '/portfolio-analyses/',
          '/candidate-hub/',
          '/analyze/',
          '/pr-analysis/',
          '/portfolio-analysis/',
          '/batch/',

          // Admin pages
          '/admin-portal/',

          // User communication
          '/messages/',

          // Auth flows (no need to index)
          '/auth/',
          '/login/',
          '/signup/',
          '/forgot-password/',
          '/reset-password/',

          // Testing/development pages
          '/test/',

          // Next.js internals and static assets
          '/_next/static/',
          '/_next/image/',
          '/favicon.ico',
        ],
      },
    ],
    sitemap: `${baseUrl}/sitemap.xml`,
  };
}
