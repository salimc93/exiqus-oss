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

// Twitter card uses same design as OpenGraph
export default async function Image() {
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
        padding: '80px',
        position: 'relative',
      }}
    >
      {/* Gradient background */}
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
        }}
      >
        {/* Logo */}
        <h1
          style={{
            fontSize: 120,
            fontWeight: 600,
            background: 'linear-gradient(135deg, #9333ea 0%, #3b82f6 100%)',
            backgroundClip: 'text',
            color: 'transparent',
            margin: 0,
            marginBottom: 40,
            letterSpacing: '0.05em',
          }}
        >
          EXIQUS
        </h1>

        {/* Tagline */}
        <p
          style={{
            fontSize: 48,
            fontWeight: 700,
            color: '#f3f4f6',
            margin: 0,
            marginBottom: 16,
            textAlign: 'center',
            lineHeight: 1.2,
          }}
        >
          From Four Interviews to One.
          <br />
          From Guesswork to Evidence.
        </p>

        {/* Subtitle */}
        <p
          style={{
            fontSize: 32,
            fontWeight: 400,
            color: '#9ca3af',
            margin: 0,
            marginTop: 24,
            textAlign: 'center',
          }}
        >
          Evidence-Based Developer Hiring
        </p>

        {/* URL */}
        <p
          style={{
            fontSize: 24,
            fontWeight: 400,
            color: '#6b7280',
            margin: 0,
            marginTop: 40,
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
