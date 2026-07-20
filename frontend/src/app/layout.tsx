// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

import type { Metadata } from 'next';
import { Inter, Montserrat } from 'next/font/google';
import { Toaster } from 'sonner';
import { LayoutContent } from '@/components/layouts/layout-content';
import { OrganizationSchema, WebSiteSchema } from '@/components/seo/json-ld';
import { CookieConsent } from '@/components/ui/cookie-consent';
import { AuthProvider } from '@/contexts/auth-context';
import { SITE_URL } from '@/lib/site';

import './globals.css';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-sans',
});

const montserrat = Montserrat({
  subsets: ['latin'],
  variable: '--font-brand',
  weight: ['300', '400', '500', '600', '700', '800', '900'],
});

// Security: All metadata values are hardcoded - no user input
export const metadata: Metadata = {
  title: 'Exiqus - The Insight Engine for Developer Hiring | AI-Powered Candidate Intelligence',
  description:
    'Evidence-driven candidate intelligence from real code, not performance tests. Exiqus analyses GitHub contributions to reveal meaningful insights about how developers think, build, and solve problems. AI-powered insight. Human-driven judgment.',
  keywords: [
    'developer insights',
    'candidate intelligence',
    'insight engine',
    'github analysis',
    'developer hiring',
    'technical recruiting',
    'evidence-based hiring',
    'developer intelligence platform',
    'github portfolio insights',
    'ai hiring tools',
    'candidate insight platform',
  ],
  authors: [{ name: 'Exiqus' }],
  creator: 'Exiqus',
  publisher: 'Exiqus',
  metadataBase: new URL(SITE_URL),
  alternates: {
    canonical: '/',
  },
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: '/',
    title: 'Exiqus - The Insight Engine for Developer Hiring',
    description:
      'Evidence-driven candidate intelligence from real code, not performance tests. AI-powered insight. Human-driven judgment.',
    siteName: 'Exiqus',
    images: [
      {
        url: '/opengraph-image',
        width: 1200,
        height: 630,
        alt: 'Exiqus - The Insight Engine for Developer Hiring',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Exiqus - The Insight Engine for Developer Hiring',
    description:
      'Evidence-driven candidate intelligence from real code, not performance tests. AI-powered insight. Human-driven judgment.',
    images: ['/twitter-image'],
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
  icons: {
    icon: '/favicon.ico',
    shortcut: '/favicon.ico',
    apple: '/apple-icon.png',
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`dark ${inter.variable} ${montserrat.variable}`}>
      <body className="min-h-screen bg-[#0A0A0A] font-sans antialiased">
        {/* Sitewide JSON-LD Structured Data for SEO */}
        <OrganizationSchema />
        <WebSiteSchema />

        <AuthProvider>
          <LayoutContent>{children}</LayoutContent>
          <Toaster position="top-right" richColors />
          <CookieConsent />
        </AuthProvider>
      </body>
    </html>
  );
}
