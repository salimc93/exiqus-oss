// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import { ArrowLeft, FileQuestion, Home } from 'lucide-react';
import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

import { ExiqusButton, ExiqusCard, GradientText } from '@/components/ui/exiqus-components';

export default function NotFound() {
  const router = useRouter();

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0A0A0A] px-4 py-12">
      {/* Subtle gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-br from-purple-900/10 via-transparent to-blue-900/10"></div>

      {/* Animated gradient orbs */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 h-80 w-80 animate-float rounded-full bg-purple-600/20 blur-3xl filter"></div>
        <div className="animation-delay-2000 absolute -bottom-40 -left-40 h-80 w-80 animate-float rounded-full bg-blue-600/20 blur-3xl filter"></div>
      </div>

      <div className="relative z-10 w-full max-w-2xl">
        <ExiqusCard className="p-8 text-center shadow-2xl md:p-12" glow="subtle">
          <div className="mb-8 flex flex-col items-center space-y-4">
            {/* Logo */}
            <div className="mb-4">
              <Image
                src="/exiqus-logo.png"
                alt="Exiqus Logo"
                width={1024}
                height={1024}
                className="h-20 w-auto opacity-80"
                unoptimized
              />
            </div>

            <div className="mx-auto mb-4 flex h-24 w-24 items-center justify-center rounded-full bg-gradient-to-br from-purple-500/20 to-blue-500/20 backdrop-blur-sm">
              <FileQuestion className="h-12 w-12 text-purple-400" />
            </div>

            <div className="space-y-2">
              <h1 className="font-bold text-6xl">
                <GradientText>404</GradientText>
              </h1>
              <h2 className="font-semibold text-2xl text-gray-100">Page Not Found</h2>
              <p className="mx-auto max-w-md text-gray-400">
                The page you&apos;re looking for doesn&apos;t exist or has been moved.
              </p>
            </div>
          </div>

          <div className="flex flex-col justify-center gap-4 sm:flex-row">
            <ExiqusButton
              onClick={() => router.back()}
              variant="secondary"
              className="flex items-center justify-center"
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Go Back
            </ExiqusButton>

            <Link href="/">
              <ExiqusButton variant="primary" className="flex w-full items-center justify-center">
                <Home className="mr-2 h-4 w-4" />
                Back to Home
              </ExiqusButton>
            </Link>
          </div>

          <div className="mt-8 border-gray-800 border-t pt-8">
            <p className="text-gray-500 text-sm">
              Need help? Check out our{' '}
              <Link
                href="/help"
                className="text-purple-400 transition-colors hover:text-purple-300"
              >
                help centre
              </Link>{' '}
              or{' '}
              <Link
                href="/contact"
                className="text-purple-400 transition-colors hover:text-purple-300"
              >
                contact support
              </Link>
            </p>
          </div>
        </ExiqusCard>
      </div>
    </div>
  );
}
