// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import { AlertCircle, CheckCircle2, Loader2, Mail, RefreshCw } from 'lucide-react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Suspense, useState } from 'react';
import { toast } from 'sonner';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { ExiqusButton, ExiqusCard } from '@/components/ui/exiqus-components';
import { api } from '@/lib/api-client';

function VerifyEmailSentContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const email = searchParams.get('email');

  const [isResending, setIsResending] = useState(false);
  const [resendDisabled, setResendDisabled] = useState(false);
  const [countdown, setCountdown] = useState(0);

  const handleResendEmail = async () => {
    if (!email) {
      toast.error('Email address not found', {
        description: 'Please try signing up again.',
      });
      return;
    }

    setIsResending(true);

    try {
      const response = await api.resendVerificationEmail(decodeURIComponent(email));

      if (response.data.message) {
        toast.success('Verification email sent!', {
          description: 'Please check your inbox for the new verification link.',
        });

        // Start countdown timer (5 minutes)
        setResendDisabled(true);
        setCountdown(300); // 5 minutes in seconds

        const timer = setInterval(() => {
          setCountdown((prev) => {
            if (prev <= 1) {
              clearInterval(timer);
              setResendDisabled(false);
              return 0;
            }
            return prev - 1;
          });
        }, 1000);
      }
    } catch (error) {
      let status = 0;
      let errorDetail = '';

      if (error && typeof error === 'object' && 'response' in error) {
        const axiosError = error as { response?: { status?: number; data?: { detail?: string } } };
        status = axiosError.response?.status || 0;
        errorDetail = axiosError.response?.data?.detail || '';
      }

      if (status === 429) {
        // Rate limit error - start countdown
        setResendDisabled(true);
        setCountdown(300);

        const timer = setInterval(() => {
          setCountdown((prev) => {
            if (prev <= 1) {
              clearInterval(timer);
              setResendDisabled(false);
              return 0;
            }
            return prev - 1;
          });
        }, 1000);

        toast.error('Too many requests', {
          description: 'Please wait 5 minutes before requesting another verification email.',
        });
      } else {
        const errorMessage = errorDetail || 'Failed to resend verification email';
        toast.error('Error', { description: errorMessage });
      }
    } finally {
      setIsResending(false);
    }
  };

  const formatCountdown = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

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
        <ExiqusCard className="p-8 shadow-2xl md:p-12" glow="purple">
          <div className="mb-8 flex flex-col space-y-4 text-center">
            <div className="mx-auto mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-purple-500/20 to-blue-500/20 backdrop-blur-sm">
              <Mail className="h-10 w-10 text-purple-400" />
            </div>
            <h1 className="font-bold text-3xl text-gray-100 tracking-tight">Check your email</h1>
            <p className="text-gray-400 text-lg">
              We&apos;ve sent a verification link to{' '}
              <span className="font-medium text-gray-200">
                {email ? decodeURIComponent(email) : 'your email'}
              </span>
            </p>
          </div>

          <div className="space-y-6">
            <Alert className="border-green-500/20 bg-green-500/10">
              <CheckCircle2 className="h-5 w-5 text-green-400" />
              <AlertDescription className="text-green-300">
                Please check your inbox and click the verification link to activate your account.
                The link will expire in 24 hours.
              </AlertDescription>
            </Alert>

            <div className="grid gap-6 md:grid-cols-2">
              <ExiqusCard className="p-6">
                <h3 className="mb-3 font-semibold text-gray-100 text-lg">
                  Didn&apos;t receive the email?
                </h3>
                <ul className="space-y-2 text-gray-400 text-sm">
                  <li className="flex items-start">
                    <span className="mr-2 text-purple-400">✓</span>
                    Check your spam or junk folder
                  </li>
                  <li className="flex items-start">
                    <span className="mr-2 text-purple-400">✓</span>
                    Make sure you entered the correct email
                  </li>
                  <li className="flex items-start">
                    <span className="mr-2 text-purple-400">✓</span>
                    Wait a few minutes for the email to arrive
                  </li>
                </ul>
              </ExiqusCard>

              <ExiqusCard className="p-6">
                <h3 className="mb-3 flex items-center font-semibold text-gray-100 text-lg">
                  <AlertCircle className="mr-2 h-5 w-5 text-blue-400" />
                  Email Delivery Notes
                </h3>
                <p className="text-gray-400 text-sm">
                  Some email providers may block or delay verification emails. If you&apos;re using
                  a temporary email service, it may not receive our emails.
                </p>
              </ExiqusCard>
            </div>

            <div className="flex flex-col gap-4 pt-4 sm:flex-row">
              <ExiqusButton
                onClick={handleResendEmail}
                disabled={isResending || resendDisabled || !email}
                variant="secondary"
                className="flex-1"
              >
                {isResending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Sending...
                  </>
                ) : resendDisabled ? (
                  <>
                    <RefreshCw className="mr-2 h-4 w-4" />
                    Resend in {formatCountdown(countdown)}
                  </>
                ) : (
                  <>
                    <RefreshCw className="mr-2 h-4 w-4" />
                    Resend verification email
                  </>
                )}
              </ExiqusButton>

              <ExiqusButton
                onClick={() => router.push('/login')}
                variant="primary"
                className="flex-1"
              >
                Go to Login
              </ExiqusButton>
            </div>

            <div className="mt-6 text-center">
              <Link
                href="/"
                className="text-gray-500 text-sm transition-colors hover:text-gray-400"
              >
                Back to home
              </Link>
            </div>
          </div>
        </ExiqusCard>
      </div>
    </div>
  );
}

export default function VerifyEmailSentPage() {
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
      <VerifyEmailSentContent />
    </Suspense>
  );
}
