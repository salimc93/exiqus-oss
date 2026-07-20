// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import { ArrowRight, CheckCircle2, Loader2, Mail, XCircle } from 'lucide-react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Suspense, useEffect, useState } from 'react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { ExiqusButton, ExiqusCard } from '@/components/ui/exiqus-components';
import { api } from '@/lib/api-client';

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get('token');

  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');

  useEffect(() => {
    const verifyEmail = async () => {
      if (!token) {
        setStatus('error');
        setMessage('Invalid verification link. Please check your email for the correct link.');
        return;
      }

      try {
        const response = await api.verifyEmail(token);

        if (response.data.message) {
          setStatus('success');
          setMessage('Email verified successfully! You can now log in to your account.');

          // Redirect to login after 3 seconds
          setTimeout(() => {
            router.push('/login?verified=true');
          }, 3000);
        }
      } catch (error) {
        setStatus('error');
        let errorMessage = 'Verification failed. The link may be expired or invalid.';

        let errorDetail = '';
        if (error && typeof error === 'object' && 'response' in error) {
          const axiosError = error as { response?: { data?: { detail?: string } } };
          errorDetail = axiosError.response?.data?.detail || '';
        }

        // Make error messages more user-friendly
        if (errorDetail.includes('Invalid or expired verification token')) {
          errorMessage =
            'This verification link has expired or has already been used. Please request a new verification email.';
        } else if (errorDetail.includes('User not found')) {
          errorMessage =
            "We couldn't find an account associated with this verification link. Please sign up again.";
        } else if (
          errorDetail.includes('already verified') ||
          errorDetail.includes('Email already verified')
        ) {
          errorMessage =
            'Great news! Your email has already been verified. You can log in to your account right away.';
          // Change to success state for already verified
          setStatus('success');
          setTimeout(() => {
            router.push('/login');
          }, 3000);
          setMessage(errorMessage);
          return;
        }

        setMessage(errorMessage);
      }
    };

    verifyEmail();
  }, [token, router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0A0A0A] px-4 py-12">
      {/* Subtle gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-br from-purple-900/10 via-transparent to-blue-900/10"></div>

      {/* Animated gradient orbs */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 h-80 w-80 animate-float rounded-full bg-purple-600/20 blur-3xl filter"></div>
        <div className="animation-delay-2000 absolute -bottom-40 -left-40 h-80 w-80 animate-float rounded-full bg-blue-600/20 blur-3xl filter"></div>
      </div>

      <div className="relative z-10 w-full max-w-xl">
        <ExiqusCard className="p-8 shadow-2xl md:p-10" glow="purple">
          <div className="mb-8 flex flex-col space-y-4 text-center">
            <div className="mx-auto mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-purple-500/20 to-blue-500/20 backdrop-blur-sm">
              <Mail className="h-10 w-10 text-purple-400" />
            </div>
            <h1 className="font-bold text-3xl text-gray-100 tracking-tight">Email Verification</h1>
          </div>

          <div className="space-y-6">
            {status === 'loading' && (
              <div className="flex flex-col items-center space-y-4 py-8">
                <Loader2 className="h-12 w-12 animate-spin text-purple-400" />
                <p className="text-gray-400 text-lg">Verifying your email address...</p>
              </div>
            )}

            {status === 'success' && (
              <div className="flex flex-col items-center space-y-6">
                <div className="flex h-24 w-24 items-center justify-center rounded-full bg-green-500/10">
                  <CheckCircle2 className="h-14 w-14 text-green-400" />
                </div>
                <Alert className="border-green-500/20 bg-green-500/10 text-center">
                  <AlertDescription className="text-center font-medium text-base text-green-300">
                    {message}
                  </AlertDescription>
                </Alert>
                <div className="flex items-center space-x-2">
                  <Loader2 className="h-4 w-4 animate-spin text-gray-500" />
                  <p className="text-gray-500 text-sm">Redirecting to login page...</p>
                </div>
                <Link
                  href="/login"
                  className="mt-4 flex items-center text-purple-400 transition-colors hover:text-purple-300"
                >
                  Continue to login <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </div>
            )}

            {status === 'error' && (
              <div className="flex flex-col items-center space-y-6">
                <div className="flex h-24 w-24 items-center justify-center rounded-full bg-red-500/10">
                  <XCircle className="h-14 w-14 text-red-400" />
                </div>
                <Alert className="border-red-500/20 bg-red-500/10 text-center">
                  <AlertDescription className="text-center font-medium text-base text-red-300">
                    {message}
                  </AlertDescription>
                </Alert>

                <div className="flex w-full flex-col gap-4 pt-4 sm:flex-row">
                  <ExiqusButton
                    onClick={() => router.push('/signup')}
                    variant="secondary"
                    className="flex-1"
                  >
                    Back to Sign Up
                  </ExiqusButton>
                  <ExiqusButton
                    onClick={() => {
                      // Need to pass email somehow, for now just go to resend page
                      router.push('/auth/verify-email-sent');
                    }}
                    variant="primary"
                    className="flex-1"
                  >
                    Request New Link
                  </ExiqusButton>
                </div>

                <Link
                  href="/"
                  className="text-center text-gray-500 text-sm transition-colors hover:text-gray-400"
                >
                  Back to home
                </Link>
              </div>
            )}
          </div>
        </ExiqusCard>
      </div>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-[#0A0A0A] p-4">
          <div className="text-center">
            <Loader2 className="mx-auto h-12 w-12 animate-spin text-purple-600" />
            <p className="mt-4 text-gray-400">Loading...</p>
          </div>
        </div>
      }
    >
      <VerifyEmailContent />
    </Suspense>
  );
}
