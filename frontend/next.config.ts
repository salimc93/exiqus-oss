import type { NextConfig } from 'next';

const isDev = process.env.NODE_ENV === 'development';
const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Content Security Policy - strict but practical
const cspHeader = `
  default-src 'self';
  script-src 'self' 'unsafe-eval' 'unsafe-inline' https://*.stripe.com;
  style-src 'self' 'unsafe-inline';
  img-src 'self' blob: data: https://avatars.githubusercontent.com https://*.stripe.com;
  font-src 'self' data:;
  connect-src 'self' ${apiUrl} https://*.stripe.com wss://*.stripe.com;
  frame-src 'self' https://*.stripe.com;
  object-src 'none';
  base-uri 'self';
  form-action 'self';
  frame-ancestors 'none';
  upgrade-insecure-requests;
`.replace(/\n/g, '');

const securityHeaders = [
  {
    key: 'Content-Security-Policy',
    value: cspHeader.replace(/\s{2,}/g, ' ').trim(),
  },
  {
    key: 'X-Frame-Options',
    value: 'DENY',
  },
  {
    key: 'X-Content-Type-Options',
    value: 'nosniff',
  },
  {
    key: 'Referrer-Policy',
    value: 'strict-origin-when-cross-origin',
  },
  {
    key: 'Permissions-Policy',
    value: 'geolocation=(), microphone=(), camera=(), payment=(self), usb=()',
  },
  // Only add HSTS in production
  ...(isDev
    ? []
    : [
        {
          key: 'Strict-Transport-Security',
          value: 'max-age=31536000; includeSubDomains; preload',
        },
      ]),
];

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'github.com',
        pathname: '/**',
      },
    ],
  },
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: securityHeaders,
      },
    ];
  },
  async rewrites() {
    const rewriteApiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

    return [
      {
        source: '/api/:path*',
        destination: `${rewriteApiUrl}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
