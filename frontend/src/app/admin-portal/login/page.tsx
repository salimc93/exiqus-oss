// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import { AlertCircle, Lock, Shield } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { toast } from 'sonner';

import { ExiqusButton, ExiqusCard, GradientText } from '@/components/ui/exiqus-components';
import { api } from '@/lib/api-client';

export default function AdminLoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [adminSecret, setAdminSecret] = useState('');
  const [loading, setLoading] = useState(false);

  const handleAdminLogin = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!email || !password || !adminSecret) {
      toast.error('Please fill in all fields');
      return;
    }

    try {
      setLoading(true);

      // Use dedicated admin auth endpoint
      const response = await api.adminLogin({
        email,
        password,
        admin_secret: adminSecret,
      });

      if (response.data.access_token) {
        // IMPORTANT: Do NOT use the main access token system - that's for regular users
        // Admin tokens should be completely separate to avoid session conflicts

        // Only store admin-specific tokens
        localStorage.setItem('adminToken', response.data.access_token);
        localStorage.setItem('adminRefreshToken', response.data.refresh_token);

        // Set admin session flag
        sessionStorage.setItem('adminSession', 'true');
        sessionStorage.setItem('adminLoginTime', new Date().toISOString());
        sessionStorage.setItem('adminEmail', email);

        toast.success('Admin access granted');
        router.push('/admin-portal/dashboard');
      }
    } catch (error) {
      const axiosError = error as { response?: { data?: { detail?: string } } };
      toast.error(axiosError.response?.data?.detail || 'Admin authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0A0A0A]">
      <div className="w-full max-w-md px-4">
        <div className="mb-8 text-center">
          <div className="mb-4 flex justify-center">
            <div className="rounded-full bg-gradient-to-r from-red-600 to-orange-600 p-4">
              <Shield className="h-12 w-12 text-white" />
            </div>
          </div>
          <h1 className="font-bold text-3xl">
            <GradientText>Admin Portal</GradientText>
          </h1>
          <p className="mt-2 text-gray-400">Restricted Access - Authorized Personnel Only</p>
        </div>

        <ExiqusCard className="p-8" glow="subtle">
          <form onSubmit={handleAdminLogin} className="space-y-6">
            <div>
              <label className="mb-2 block font-medium text-gray-300 text-sm">Admin Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@example.com"
                className="w-full rounded-lg bg-gray-900 px-4 py-3 text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-red-500"
                required
              />
            </div>

            <div>
              <label className="mb-2 block font-medium text-gray-300 text-sm">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full rounded-lg bg-gray-900 px-4 py-3 text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-red-500"
                required
              />
            </div>

            <div>
              <label className="mb-2 block font-medium text-gray-300 text-sm">
                Admin Access Code
              </label>
              <div className="relative">
                <Lock className="absolute top-3.5 left-3 h-5 w-5 text-gray-500" />
                <input
                  type="password"
                  value={adminSecret}
                  onChange={(e) => setAdminSecret(e.target.value)}
                  placeholder="Enter admin secret"
                  className="w-full rounded-lg bg-gray-900 py-3 pr-4 pl-10 text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-red-500"
                  required
                />
              </div>
            </div>

            <ExiqusButton
              type="submit"
              disabled={loading}
              className="w-full bg-gradient-to-r from-red-600 to-orange-600 hover:from-red-700 hover:to-orange-700"
            >
              {loading ? 'Authenticating...' : 'Access Admin Portal'}
            </ExiqusButton>
          </form>

          <div className="mt-6 rounded-lg bg-red-900/20 p-4">
            <div className="flex items-start gap-3">
              <AlertCircle className="mt-0.5 h-5 w-5 text-red-400" />
              <div className="text-gray-300 text-sm">
                <p className="font-semibold text-red-400">Security Notice</p>
                <p className="mt-1">
                  This portal is for authorized administrators only. All access attempts are logged
                  and monitored. Unauthorized access is prohibited and will be reported.
                </p>
              </div>
            </div>
          </div>
        </ExiqusCard>

        <div className="mt-8 text-center text-gray-500 text-sm">
          <p>Admin session expires after 2 hours of inactivity</p>
          <p className="mt-2">Need help? Contact your instance administrator.</p>
        </div>
      </div>
    </div>
  );
}
