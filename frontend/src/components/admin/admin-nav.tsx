// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import { Home, LogOut, Mail, Shield, TrendingUp, Users } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { toast } from 'sonner';

import { GradientText } from '@/components/ui/exiqus-components';

export function AdminNav() {
  const router = useRouter();
  const [adminEmail, setAdminEmail] = useState<string>('');

  useEffect(() => {
    // Only access sessionStorage on client side
    if (typeof window !== 'undefined') {
      setAdminEmail(sessionStorage.getItem('adminEmail') || 'Unknown');
    }
  }, []);

  const handleLogout = () => {
    // Clear admin session
    if (typeof window !== 'undefined') {
      sessionStorage.removeItem('adminSession');
      sessionStorage.removeItem('adminLoginTime');
      sessionStorage.removeItem('adminEmail');
      localStorage.removeItem('adminToken');
      localStorage.removeItem('adminRefreshToken');
    }

    toast.success('Logged out of admin portal');
    router.push('/admin-portal/login');
  };

  return (
    <nav className="border-red-900/20 border-b bg-gradient-to-r from-gray-950 via-red-950/10 to-gray-950">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-8">
            <Link href="/admin-portal/dashboard" className="flex items-center gap-2">
              <Shield className="h-8 w-8 text-red-600" />
              <span className="font-bold text-xl">
                <GradientText className="bg-gradient-to-r from-red-600 to-orange-600">
                  ADMIN PORTAL
                </GradientText>
              </span>
            </Link>

            {/* Admin Navigation Links */}
            <div className="hidden items-center gap-6 md:flex">
              <Link
                href="/admin-portal/dashboard"
                className="flex items-center gap-2 text-gray-300 transition-colors hover:text-red-400"
              >
                <Home className="h-4 w-4" />
                Dashboard
              </Link>
              <Link
                href="/admin-portal/users"
                className="flex items-center gap-2 text-gray-300 transition-colors hover:text-red-400"
              >
                <Users className="h-4 w-4" />
                Users
              </Link>
              <Link
                href="/admin-portal/messages"
                className="flex items-center gap-2 text-gray-300 transition-colors hover:text-red-400"
              >
                <Mail className="h-4 w-4" />
                Support
              </Link>
              <Link
                href="/admin-portal/revenue"
                className="flex items-center gap-2 text-gray-300 transition-colors hover:text-red-400"
              >
                <TrendingUp className="h-4 w-4" />
                Revenue
              </Link>
            </div>
          </div>

          {/* Right side */}
          <div className="flex items-center gap-4">
            <div className="text-gray-400 text-sm">Admin: {adminEmail || 'Loading...'}</div>
            <button
              type="button"
              onClick={handleLogout}
              className="flex items-center gap-2 rounded-lg bg-red-900/20 px-4 py-2 text-red-400 text-sm transition-colors hover:bg-red-900/30"
            >
              <LogOut className="h-4 w-4" />
              Logout
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}
