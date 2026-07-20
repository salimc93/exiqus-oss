// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import { Loader2, Shield } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { toast } from 'sonner';

interface AdminGuardProps {
  children: React.ReactNode;
}

export function AdminGuard({ children }: AdminGuardProps) {
  const router = useRouter();
  const [isValidating, setIsValidating] = useState(true);
  const [isAuthorized, setIsAuthorized] = useState(false);

  useEffect(() => {
    // Check for admin session (only on client side)
    if (typeof window === 'undefined') {
      return;
    }

    const adminSession = sessionStorage.getItem('adminSession');
    const adminLoginTime = sessionStorage.getItem('adminLoginTime');
    const adminToken = localStorage.getItem('adminToken');

    if (!adminSession || !adminLoginTime || !adminToken) {
      // Not logged in as admin
      setIsValidating(false);
      setIsAuthorized(false);
      router.push('/admin-portal/login');
      return;
    }

    // Check session expiry (2 hours)
    const loginTime = new Date(adminLoginTime);
    const now = new Date();
    const hoursSinceLogin = (now.getTime() - loginTime.getTime()) / (1000 * 60 * 60);

    if (hoursSinceLogin > 2) {
      // Session expired - clear everything
      if (typeof window !== 'undefined') {
        sessionStorage.removeItem('adminSession');
        sessionStorage.removeItem('adminLoginTime');
        sessionStorage.removeItem('adminEmail');
        localStorage.removeItem('adminToken');
        localStorage.removeItem('adminRefreshToken');

        // Show session expired message
        toast.error('Admin session expired. Please login again.');
      }
      setIsValidating(false);
      setIsAuthorized(false);
      router.push('/admin-portal/login');
      return;
    }

    // Valid session - authorize
    setIsAuthorized(true);
    setIsValidating(false);

    // Re-validate every minute
    const interval = setInterval(() => {
      const currentLoginTime = sessionStorage.getItem('adminLoginTime');
      if (!currentLoginTime) {
        clearInterval(interval);
        router.push('/admin-portal/login');
        return;
      }

      const loginTime = new Date(currentLoginTime);
      const now = new Date();
      const hoursSinceLogin = (now.getTime() - loginTime.getTime()) / (1000 * 60 * 60);

      if (hoursSinceLogin > 2) {
        sessionStorage.removeItem('adminSession');
        sessionStorage.removeItem('adminLoginTime');
        sessionStorage.removeItem('adminEmail');
        localStorage.removeItem('adminToken');
        localStorage.removeItem('adminRefreshToken');
        clearInterval(interval);
        router.push('/admin-portal/login');
      }
    }, 60000);

    return () => clearInterval(interval);
  }, [router]);

  if (isValidating) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0A0A0A]">
        <div className="text-center">
          <Shield className="mx-auto mb-4 h-12 w-12 text-red-600" />
          <Loader2 className="mx-auto h-8 w-8 animate-spin text-gray-400" />
          <p className="mt-4 text-gray-400">Validating admin access...</p>
        </div>
      </div>
    );
  }

  if (!isAuthorized) {
    return null;
  }

  return <>{children}</>;
}
