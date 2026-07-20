// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { CheckCircle2, Loader2, Lock, Mail, Sparkles } from 'lucide-react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { Suspense, useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import * as z from 'zod';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { ExiqusButton, ExiqusCard, GradientText } from '@/components/ui/exiqus-components';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { useAuth } from '@/contexts/auth-context';

const loginSchema = z.object({
  email: z.string().email('Please enter a valid email'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
});

type LoginFormValues = z.infer<typeof loginSchema>;

function LoginContent() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const searchParams = useSearchParams();
  const { login } = useAuth();

  const form = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: '',
      password: '',
    },
  });

  useEffect(() => {
    // Check if user just verified their email
    if (searchParams.get('verified') === 'true') {
      setSuccessMessage('Email verified successfully! You can now log in.');
    }
  }, [searchParams]);

  async function onSubmit(data: LoginFormValues) {
    setIsLoading(true);
    setError('');
    setSuccessMessage('');

    try {
      await login(data);
      // Success is handled in the auth context (redirects to dashboard)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Invalid email or password';

      // Check if it's an email verification error
      if (errorMessage.includes('not verified')) {
        setError(
          'Please verify your email before logging in. Check your inbox for the verification link.'
        );
      } else {
        setError(errorMessage);
      }
    } finally {
      setIsLoading(false);
    }
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

      {/* Login Card */}
      <ExiqusCard className="relative z-10 w-full max-w-md p-8 shadow-2xl" glow="purple">
        <div className="space-y-6">
          <div className="space-y-2 text-center">
            <Link href="/" className="mb-4 inline-block">
              <h1 className="font-brand font-semibold text-3xl tracking-wide">
                <GradientText>EXIQUS</GradientText>
              </h1>
            </Link>
            <h2 className="font-bold text-2xl text-gray-100">Welcome back</h2>
            <p className="text-gray-400">Enter your credentials to access your account</p>
          </div>

          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              {successMessage && (
                <Alert className="border-green-500/20 bg-green-500/10">
                  <CheckCircle2 className="h-4 w-4 text-green-400" />
                  <AlertDescription className="text-green-300">{successMessage}</AlertDescription>
                </Alert>
              )}

              {error && (
                <Alert className="border-red-500/20 bg-red-500/10">
                  <AlertDescription className="text-red-300">{error}</AlertDescription>
                </Alert>
              )}

              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-gray-300">Email</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Mail className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-gray-500" />
                        <Input
                          placeholder="you@example.com"
                          className="border-white/[0.09] bg-white/[0.06] pl-10 text-gray-100 placeholder:text-gray-500"
                          disabled={isLoading}
                          {...field}
                        />
                      </div>
                    </FormControl>
                    <FormMessage className="text-red-400" />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-gray-300">Password</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Lock className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-gray-500" />
                        <Input
                          type="password"
                          placeholder="••••••••"
                          className="border-white/[0.09] bg-white/[0.06] pl-10 text-gray-100 placeholder:text-gray-500"
                          disabled={isLoading}
                          {...field}
                        />
                      </div>
                    </FormControl>
                    <FormMessage className="text-red-400" />
                  </FormItem>
                )}
              />

              <ExiqusButton type="submit" className="w-full" size="lg" disabled={isLoading}>
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Signing in...
                  </>
                ) : (
                  'Sign in'
                )}
              </ExiqusButton>
            </form>
          </Form>

          {/* Demo Credentials */}
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-white/[0.06] border-t" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-[#111111] px-2 text-gray-500">Or</span>
            </div>
          </div>

          <ExiqusCard className="border-white/[0.06] bg-white/[0.03] p-4">
            <div className="mb-2 flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-purple-400" />
              <span className="font-medium text-gray-300 text-sm">Demo Credentials</span>
            </div>
            <p className="text-gray-400 text-sm">
              Email: test@example.com
              <br />
              Password: password
            </p>
          </ExiqusCard>

          {/* Links */}
          <div className="space-y-4 text-center text-sm">
            <div>
              <span className="text-gray-400">Don&apos;t have an account? </span>
              <Link href="/signup" className="font-medium text-purple-400 hover:text-purple-300">
                Sign up
              </Link>
            </div>
            <Link href="/forgot-password" className="block text-gray-400 hover:text-gray-300">
              Forgot your password?
            </Link>
          </div>
        </div>
      </ExiqusCard>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100 p-4">
          <div className="text-center">
            <Loader2 className="mx-auto h-12 w-12 animate-spin text-blue-600" />
            <p className="mt-4 text-gray-600">Loading...</p>
          </div>
        </div>
      }
    >
      <LoginContent />
    </Suspense>
  );
}
