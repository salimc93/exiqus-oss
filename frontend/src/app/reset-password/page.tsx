// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import { CheckCircle, Lock } from 'lucide-react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import type React from 'react';
import { Suspense, useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import { ExiqusCard, GradientText } from '@/components/ui/exiqus-components';
import { Label } from '@/components/ui/label';
import { useToast } from '@/hooks/use-toast';

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { toast } = useToast();
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [hasCheckedToken, setHasCheckedToken] = useState(false);

  // Get token from URL - searchParams is available immediately in Suspense
  const token = searchParams.get('token');

  useEffect(() => {
    // Only check once to avoid multiple redirects
    if (!hasCheckedToken) {
      setHasCheckedToken(true);
      if (!token) {
        toast({
          title: 'Invalid Link',
          description: 'This password reset link is invalid or has expired.',
          variant: 'destructive',
        });
        router.push('/forgot-password');
      }
    }
  }, [token, router, toast, hasCheckedToken]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (password !== confirmPassword) {
      toast({
        title: 'Passwords do not match',
        description: 'Please make sure both passwords are the same.',
        variant: 'destructive',
      });
      return;
    }

    if (password.length < 8) {
      toast({
        title: 'Password too short',
        description: 'Password must be at least 8 characters long.',
        variant: 'destructive',
      });
      return;
    }

    setIsLoading(true);

    try {
      // Use fetch directly to avoid auth interceptor
      const API_URL = process.env.NEXT_PUBLIC_API_URL || '';
      const response = await fetch(`${API_URL}/api/v1/auth/reset-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          // Don't send auth headers on password reset
        },
        body: JSON.stringify({
          token,
          new_password: password,
        }),
        // Don't send credentials on password reset
      });

      if (response.ok) {
        setIsSuccess(true);
        toast({
          title: 'Password reset successful',
          description: 'Your password has been updated. You can now login with your new password.',
        });
      } else {
        const data = await response.json();
        toast({
          title: 'Error',
          description: data.detail || 'Failed to reset password. The link may have expired.',
          variant: 'destructive',
        });

        // If token is invalid/expired, redirect to forgot password
        if (response.status === 400) {
          setTimeout(() => {
            router.push('/forgot-password');
          }, 3000);
        }
      }
    } catch (error) {
      console.error('Password reset error:', error);
      toast({
        title: 'Error',
        description: 'Network error. Please check your connection and try again.',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  if (isSuccess) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0A0A0A] px-4 py-12">
        {/* Subtle gradient overlay */}
        <div className="absolute inset-0 bg-gradient-to-br from-purple-900/10 via-transparent to-blue-900/10"></div>

        {/* Animated gradient orbs */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute -top-40 -right-40 h-80 w-80 animate-float rounded-full bg-purple-600/20 blur-3xl filter"></div>
          <div className="animation-delay-2000 absolute -bottom-40 -left-40 h-80 w-80 animate-float rounded-full bg-blue-600/20 blur-3xl filter"></div>
        </div>

        <ExiqusCard className="relative z-10 w-full max-w-md p-8 shadow-2xl" glow="purple">
          <div className="mb-6 flex justify-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-emerald-600 to-teal-600">
              <CheckCircle className="h-8 w-8 text-white" />
            </div>
          </div>

          <h2 className="mb-2 text-center font-bold text-2xl text-gray-100">
            Password Reset Successful!
          </h2>
          <p className="mb-6 text-center text-gray-400">
            Your password has been updated successfully.
          </p>

          <div className="space-y-4">
            <Link href="/login" className="block">
              <Button className="w-full bg-gradient-to-r from-blue-600 to-purple-600 py-3.5 font-semibold text-base text-white shadow-lg transition-all duration-200 hover:from-blue-700 hover:to-purple-700 hover:shadow-xl">
                Go to Login
              </Button>
            </Link>
          </div>
        </ExiqusCard>
      </div>
    );
  }

  // If no token, component will redirect
  if (!token) {
    return null;
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0A0A0A] px-4 py-12">
      {/* Subtle gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-br from-purple-900/10 via-transparent to-blue-900/10"></div>

      {/* Animated gradient orbs */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 h-80 w-80 animate-float rounded-full bg-purple-600/20 blur-3xl filter"></div>
        <div className="animation-delay-2000 absolute -bottom-40 -left-40 h-80 w-80 animate-float rounded-full bg-blue-600/20 blur-3xl filter"></div>
      </div>

      {/* Reset Password Card */}
      <ExiqusCard className="relative z-10 w-full max-w-md p-8 shadow-2xl" glow="purple">
        <div className="space-y-6">
          <div className="space-y-2 text-center">
            <Link href="/" className="mb-4 inline-block">
              <h1 className="font-brand font-semibold text-3xl tracking-wide">
                <GradientText>EXIQUS</GradientText>
              </h1>
            </Link>
            <h2 className="font-bold text-2xl text-gray-100">Create new password</h2>
            <p className="text-gray-400">
              Enter your new password below. Make sure it&apos;s at least 8 characters long.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <Label htmlFor="password" className="mb-2 block font-medium text-gray-300 text-sm">
                New Password
              </Label>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4">
                  <Lock className="h-5 w-5 text-gray-500" />
                </div>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter new password"
                  required
                  autoComplete="new-password"
                  minLength={8}
                  className="block w-full rounded-lg border border-gray-700 bg-gray-800/50 py-3.5 pr-4 pl-12 text-base text-gray-100 placeholder-gray-500 shadow-sm backdrop-blur-sm transition-all duration-200 hover:bg-gray-800/70 focus:border-purple-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                />
              </div>
            </div>

            <div>
              <Label
                htmlFor="confirmPassword"
                className="mb-2 block font-medium text-gray-300 text-sm"
              >
                Confirm Password
              </Label>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4">
                  <Lock className="h-5 w-5 text-gray-500" />
                </div>
                <input
                  id="confirmPassword"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Confirm new password"
                  required
                  autoComplete="new-password"
                  minLength={8}
                  className="block w-full rounded-lg border border-gray-700 bg-gray-800/50 py-3.5 pr-4 pl-12 text-base text-gray-100 placeholder-gray-500 shadow-sm backdrop-blur-sm transition-all duration-200 hover:bg-gray-800/70 focus:border-purple-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                />
              </div>
            </div>

            <Button
              type="submit"
              disabled={isLoading || !token}
              className="w-full bg-gradient-to-r from-blue-600 to-purple-600 py-3.5 font-semibold text-base text-white shadow-lg transition-all duration-200 hover:from-blue-700 hover:to-purple-700 hover:shadow-xl disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isLoading ? 'Resetting...' : 'Reset Password'}
            </Button>
          </form>

          <div className="mt-6 text-center">
            <Link
              href="/login"
              className="text-gray-400 text-sm transition-colors hover:text-purple-400 hover:underline"
            >
              Back to login
            </Link>
          </div>
        </div>
      </ExiqusCard>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-[#0A0A0A] p-4">
          <div className="text-center">
            <div className="mx-auto h-12 w-12 animate-spin rounded-full border-purple-500 border-b-2"></div>
            <p className="mt-4 text-gray-400">Loading...</p>
          </div>
        </div>
      }
    >
      <ResetPasswordForm />
    </Suspense>
  );
}
