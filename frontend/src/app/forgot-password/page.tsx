// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import { ArrowLeft, Mail } from 'lucide-react';
import Link from 'next/link';
import type React from 'react';
import { useState } from 'react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { ExiqusButton, ExiqusCard, GradientText } from '@/components/ui/exiqus-components';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useToast } from '@/hooks/use-toast';

export default function ForgotPasswordPage() {
  const { toast } = useToast();
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || '';
      const response = await fetch(`${API_URL}/api/v1/auth/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });

      if (response.ok) {
        const data = await response.json();
        setIsSubmitted(true);
        toast({
          title: 'Check your email',
          description:
            data.message ||
            "If an account exists with this email, we've sent password reset instructions.",
        });
      } else {
        let errorMessage = 'Something went wrong. Please try again.';
        try {
          const data = await response.json();
          errorMessage = data.detail || data.message || errorMessage;
        } catch (jsonError) {
          // Response might not be JSON
          console.error('Failed to parse error response:', jsonError);
        }
        toast({
          title: 'Error',
          description: errorMessage,
          variant: 'destructive',
        });
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

  if (isSubmitted) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0A0A0A] px-4 py-12">
        {/* Subtle gradient overlay */}
        <div className="absolute inset-0 bg-gradient-to-br from-purple-900/10 via-transparent to-blue-900/10"></div>

        {/* Animated gradient orbs */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute -top-40 -right-40 h-80 w-80 animate-float rounded-full bg-purple-600/20 blur-3xl filter"></div>
          <div className="animation-delay-2000 absolute -bottom-40 -left-40 h-80 w-80 animate-float rounded-full bg-blue-600/20 blur-3xl filter"></div>
        </div>

        <ExiqusCard className="relative z-10 w-full max-w-md p-8 shadow-2xl" glow="green">
          <div className="mb-6 flex justify-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full border border-green-500/20 bg-green-500/10">
              <Mail className="h-8 w-8 text-green-400" />
            </div>
          </div>

          <h2 className="mb-2 text-center font-bold text-2xl text-gray-100">Check your email</h2>
          <p className="mb-6 text-center text-gray-400">
            We&apos;ve sent password reset instructions to{' '}
            <span className="text-gray-300">{email}</span>
          </p>

          <div className="space-y-4">
            <Alert className="border-blue-500/20 bg-blue-500/10">
              <AlertDescription className="text-center text-blue-300 text-sm">
                Didn&apos;t receive the email? Check your spam folder or try again with a different
                email address.
              </AlertDescription>
            </Alert>

            <ExiqusButton
              onClick={() => {
                setIsSubmitted(false);
                setEmail('');
              }}
              variant="outline"
              className="w-full"
            >
              Try another email
            </ExiqusButton>

            <div className="text-center">
              <Link
                href="/login"
                className="inline-flex items-center gap-1 text-purple-400 text-sm hover:text-purple-300"
              >
                <ArrowLeft className="h-4 w-4" />
                Back to login
              </Link>
            </div>
          </div>
        </ExiqusCard>
      </div>
    );
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

      <ExiqusCard className="relative z-10 w-full max-w-md p-8 shadow-2xl" glow="purple">
        <div className="space-y-6">
          <div className="space-y-2 text-center">
            <Link href="/" className="mb-4 inline-block">
              <h1 className="font-brand font-semibold text-3xl tracking-wide">
                <GradientText>EXIQUS</GradientText>
              </h1>
            </Link>
            <h2 className="font-bold text-2xl text-gray-100">Forgot your password?</h2>
            <p className="text-gray-400">
              No worries! Enter your email and we&apos;ll send you reset instructions.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label htmlFor="email" className="text-gray-300">
                Email address
              </Label>
              <div className="relative mt-1">
                <Mail className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-gray-500" />
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  required
                  autoComplete="email"
                  disabled={isLoading}
                  className="border-white/[0.09] bg-white/[0.06] pl-10 text-gray-100 placeholder:text-gray-500"
                />
              </div>
            </div>

            <ExiqusButton type="submit" className="w-full" size="lg" disabled={isLoading}>
              {isLoading ? 'Sending...' : 'Send reset instructions'}
            </ExiqusButton>
          </form>

          <div className="text-center">
            <Link
              href="/login"
              className="inline-flex items-center gap-1 text-purple-400 text-sm hover:text-purple-300"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to login
            </Link>
          </div>
        </div>
      </ExiqusCard>
    </div>
  );
}
