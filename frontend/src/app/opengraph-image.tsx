// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

import { ImageResponse } from 'next/og';

// Security: Static configuration only - no user input
export const runtime = 'edge';
export const alt = 'Exiqus - Evidence-Based Developer Hiring';
export const size = {
  width: 1200,
  height: 630,
};
export const contentType = 'image/png';

export default async function Image() {
  // Security: All text is hardcoded - no user input
  // Security: Using static assets only from /public directory

  return new ImageResponse(
    <div
      style={{
        background: '#0A0A0A',
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '60px',
        position: 'relative',
      }}
    >
      {/* Gradient background - matching brand colors */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background:
            'linear-gradient(135deg, rgba(147, 51, 234, 0.1) 0%, rgba(59, 130, 246, 0.1) 100%)',
        }}
      />

      {/* Content */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 10,
          gap: 24,
        }}
      >
        {/* Logo Text - using brand font style */}
        <h1
          style={{
            fontSize: 100,
            fontWeight: 600,
            background: 'linear-gradient(135deg, #9333ea 0%, #3b82f6 100%)',
            backgroundClip: 'text',
            color: 'transparent',
            margin: 0,
            letterSpacing: '0.05em',
          }}
        >
          EXIQUS
        </h1>

        {/* Main tagline */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            textAlign: 'center',
            width: '100%',
          }}
        >
          <p
            style={{
              fontSize: 40,
              fontWeight: 700,
              color: '#f3f4f6',
              margin: 0,
              lineHeight: 1.3,
            }}
          >
            From Four Interviews to One.
          </p>
          <p
            style={{
              fontSize: 40,
              fontWeight: 700,
              color: '#f3f4f6',
              margin: 0,
              lineHeight: 1.3,
            }}
          >
            From Guesswork to Evidence.
          </p>
        </div>

        {/* Subtitle */}
        <p
          style={{
            fontSize: 28,
            fontWeight: 400,
            color: '#9ca3af',
            margin: 0,
            textAlign: 'center',
          }}
        >
          Evidence-Based Developer Hiring
        </p>

        {/* URL */}
        <p
          style={{
            fontSize: 22,
            fontWeight: 400,
            color: '#6b7280',
            margin: 0,
            marginTop: 16,
          }}
        >
          Exiqus
        </p>
      </div>
    </div>,
    {
      ...size,
    }
  );
}
