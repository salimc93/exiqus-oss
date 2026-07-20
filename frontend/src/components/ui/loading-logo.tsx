// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

import Image from 'next/image';

interface LoadingLogoProps {
  size?: 'sm' | 'md' | 'lg';
  message?: string;
}

export function LoadingLogo({ size = 'md', message }: LoadingLogoProps) {
  const sizeClasses = {
    sm: 'h-16 w-16',
    md: 'h-24 w-24',
    lg: 'h-32 w-32',
  };

  return (
    <div className="flex flex-col items-center justify-center gap-4">
      <div className="relative">
        {/* Pulsing glow effect */}
        <div className="absolute inset-0 animate-pulse rounded-full bg-gradient-to-r from-purple-600 to-blue-600 opacity-30 blur-2xl"></div>

        {/* Logo with rotate animation */}
        <div className="relative animate-pulse">
          <Image
            src="/exiqus-logo.png"
            alt="Loading..."
            width={1024}
            height={1024}
            className={`${sizeClasses[size]} w-auto drop-shadow-[0_0_30px_rgba(147,51,234,0.6)]`}
            unoptimized
            priority
          />
        </div>
      </div>

      {message && <p className="animate-pulse text-gray-400 text-sm">{message}</p>}
    </div>
  );
}
