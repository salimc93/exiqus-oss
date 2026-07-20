// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import { X } from 'lucide-react';
import Link from 'next/link';
import { useEffect, useState } from 'react';

export function CookieConsent() {
  const [showBanner, setShowBanner] = useState(false);
  const [isClosing, setIsClosing] = useState(false);

  useEffect(() => {
    // Check if user has already made a choice
    const consent = localStorage.getItem('cookie-consent');
    if (!consent) {
      // Show banner after a small delay for better UX
      setTimeout(() => setShowBanner(true), 1000);
    }
  }, []);

  const handleAccept = () => {
    localStorage.setItem('cookie-consent', 'accepted');
    localStorage.setItem('cookie-consent-date', new Date().toISOString());
    closeBanner();
  };

  const handleReject = () => {
    localStorage.setItem('cookie-consent', 'rejected');
    localStorage.setItem('cookie-consent-date', new Date().toISOString());
    closeBanner();
  };

  const closeBanner = () => {
    setIsClosing(true);
    setTimeout(() => {
      setShowBanner(false);
      setIsClosing(false);
    }, 300);
  };

  if (!showBanner) return null;

  return (
    <div
      className={`fixed bottom-6 left-1/2 z-50 -translate-x-1/2 transition-all duration-300 ${
        isClosing ? 'translate-y-full opacity-0' : 'translate-y-0 opacity-100'
      }`}
    >
      <div className="relative mx-auto max-w-md rounded-xl border border-white/10 bg-gray-900/95 p-4 shadow-2xl backdrop-blur-xl">
        {/* Gradient overlay */}
        <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-indigo-500/10 via-purple-500/10 to-pink-500/10 opacity-50" />

        <div className="relative">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="flex items-center gap-1 font-semibold text-sm text-white">
              🍪 Cookie Consent
            </h3>
            <button
              type="button"
              onClick={closeBanner}
              className="text-gray-400 transition-colors hover:text-gray-300"
              aria-label="Close cookie banner"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <p className="mb-3 text-gray-300 text-xs">
            We use cookies to enhance your experience. By continuing, you agree to our{' '}
            <Link href="/privacy" className="text-indigo-400 underline hover:text-indigo-300">
              Privacy Policy
            </Link>
            .
          </p>

          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleAccept}
              className="flex-1 rounded-lg bg-gradient-to-r from-indigo-500 to-purple-600 px-3 py-1.5 font-medium text-white text-xs shadow-lg transition-all duration-200 hover:from-indigo-600 hover:to-purple-700 hover:shadow-indigo-500/25"
            >
              Accept
            </button>
            <button
              type="button"
              onClick={handleReject}
              className="flex-1 rounded-lg border border-gray-700 bg-gray-800 px-3 py-1.5 font-medium text-gray-300 text-xs transition-colors duration-200 hover:bg-gray-700"
            >
              Decline
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
