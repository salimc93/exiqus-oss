// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import { usePathname } from 'next/navigation';

import { Footer } from '@/components/layouts/footer';
import { Navigation } from '@/components/layouts/navigation';

export function LayoutContent({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isAdminPortal = pathname?.startsWith('/admin-portal');

  return (
    <div className="flex min-h-screen flex-col">
      {!isAdminPortal && <Navigation />}
      <main className="flex-1">{children}</main>
      {!isAdminPortal && <Footer />}
    </div>
  );
}
