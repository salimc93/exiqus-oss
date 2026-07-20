// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import { usePathname } from 'next/navigation';

import { AdminNav } from '@/components/admin/admin-nav';

export default function AdminPortalLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  // Don't show admin nav on login page
  const isLoginPage = pathname === '/admin-portal/login';

  return (
    <>
      {!isLoginPage && <AdminNav />}
      <div className={isLoginPage ? '' : 'min-h-[calc(100vh-4rem)] bg-gray-950'}>{children}</div>
    </>
  );
}
