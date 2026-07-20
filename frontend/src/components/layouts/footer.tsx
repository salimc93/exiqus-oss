// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

import Image from 'next/image';
import Link from 'next/link';
import React from 'react';

export function Footer() {
  return (
    <footer className="border-white/[0.06] border-t bg-[#0A0A0A]">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {/* Logo and Tagline */}
        <div className="mb-6 flex flex-col items-center gap-3">
          <Image
            src="/exiqus-logo.png"
            alt="Exiqus Logo"
            width={1024}
            height={1024}
            className="h-12 w-auto opacity-80"
            unoptimized
          />
          <div className="text-center text-gray-500 text-sm">
            Exiqus is pioneering evidence-based hiring powered by real developer work.
          </div>
        </div>

        {/* Footer Links - Legal > Product > Support */}
        <div className="mb-4 flex flex-wrap items-center justify-center gap-4 text-sm">
          <Link href="/terms" className="text-gray-400 transition-colors hover:text-gray-300">
            Terms of Service
          </Link>
          <span className="text-gray-600">|</span>
          <Link href="/privacy" className="text-gray-400 transition-colors hover:text-gray-300">
            Privacy Policy
          </Link>
          <span className="text-gray-600">|</span>
          <Link href="/refund" className="text-gray-400 transition-colors hover:text-gray-300">
            Refund Policy
          </Link>
          <span className="text-gray-600">|</span>
          <Link href="/methodology" className="text-gray-400 transition-colors hover:text-gray-300">
            Methodology
          </Link>
          <span className="text-gray-600">|</span>
          <Link href="/faq" className="text-gray-400 transition-colors hover:text-gray-300">
            FAQ
          </Link>
          <span className="text-gray-600">|</span>
          <Link href="/contact" className="text-gray-400 transition-colors hover:text-gray-300">
            Contact
          </Link>
        </div>

        {/* Copyright - Below footer links */}
        <div className="border-white/[0.06] border-t pt-4 text-center text-gray-500 text-sm">
          Copyright © 2025 Exiqus. All rights reserved.
        </div>
      </div>
    </footer>
  );
}
