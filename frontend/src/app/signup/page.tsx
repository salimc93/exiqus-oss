// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { AlertCircle, Building, CheckCircle, Clock, Loader2, Lock, Mail, User } from 'lucide-react';
import Link from 'next/link';
import { useState } from 'react';
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

const signupSchema = z
  .object({
    full_name: z.string().min(2, 'Name must be at least 2 characters'),
    email: z.string().email('Please enter a valid email'),
    password: z.string().min(8, 'Password must be at least 8 characters'),
    confirmPassword: z.string(),
    company: z.string().optional(),
    acceptTerms: z.boolean().refine((val) => val === true, {
      message: 'You must accept the terms and conditions',
    }),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords don't match",
    path: ['confirmPassword'],
  });

type SignupFormValues = z.infer<typeof signupSchema>;

export default function SignupPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [isRateLimited, setIsRateLimited] = useState(false);
  const { signup } = useAuth();

  const form = useForm<SignupFormValues>({
    resolver: zodResolver(signupSchema),
    defaultValues: {
      full_name: '',
      email: '',
      password: '',
      confirmPassword: '',
      company: '',
      acceptTerms: false,
    },
  });

  async function onSubmit(data: SignupFormValues) {
    setIsLoading(true);
    setError('');
    setIsRateLimited(false);

    try {
      const { confirmPassword: _confirmPassword, acceptTerms: _acceptTerms, ...signupData } = data;
      await signup(signupData);
      // Success is handled in the auth context (redirects to dashboard)
    } catch (err) {
      // Handle specific error cases
      let errorMessage = 'Failed to create account';

      // Extract detailed error message from the response
      const error = err as {
        response?: {
          status?: number;
          data?: {
            detail?:
              | string
              | {
                  message?: string;
                  reset_in_seconds?: number;
                };
          };
        };
        message?: string;
      };

      // Handle rate limiting with friendly message
      if (error.response?.status === 429) {
        setIsRateLimited(true);
        const detail = error.response.data?.detail;
        if (typeof detail === 'object' && detail?.message && detail?.reset_in_seconds) {
          // Backend provides structured rate limit info
          const resetHours = Math.ceil(detail.reset_in_seconds / 3600);
          errorMessage = `${detail.message}. Please try again in ${resetHours} hour${resetHours > 1 ? 's' : ''}.`;
        } else if (typeof detail === 'string') {
          errorMessage = detail;
        } else {
          errorMessage = 'Too many registration attempts. Please try again later to prevent abuse.';
        }
      } else if (error.response?.data?.detail) {
        errorMessage =
          typeof error.response.data.detail === 'string'
            ? error.response.data.detail
            : 'Failed to create account';
      } else if (error.message) {
        errorMessage = error.message;
      }

      setError(errorMessage);
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
        <div className="absolute -top-40 -left-40 h-80 w-80 animate-float rounded-full bg-blue-600/20 blur-3xl filter"></div>
        <div className="animation-delay-2000 absolute -right-40 -bottom-40 h-80 w-80 animate-float rounded-full bg-purple-600/20 blur-3xl filter"></div>
      </div>

      {/* Signup Card */}
      <ExiqusCard className="relative z-10 w-full max-w-md p-8 shadow-2xl" glow="purple">
        <div className="space-y-6">
          <div className="space-y-2 text-center">
            <Link href="/" className="mb-4 inline-block">
              <h1 className="font-brand font-semibold text-3xl tracking-wide">
                <GradientText>EXIQUS</GradientText>
              </h1>
            </Link>
            <h2 className="font-bold text-2xl text-gray-100">Create an account</h2>
            <p className="text-gray-400">Start analyzing developers with evidence-based insights</p>
          </div>

          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              {error && (
                <Alert
                  className={
                    isRateLimited
                      ? 'border-yellow-500/20 bg-yellow-500/10'
                      : 'border-red-500/20 bg-red-500/10'
                  }
                >
                  {isRateLimited ? (
                    <Clock className="h-4 w-4 text-yellow-400" />
                  ) : (
                    <AlertCircle className="h-4 w-4 text-red-400" />
                  )}
                  <AlertDescription className={isRateLimited ? 'text-yellow-300' : 'text-red-300'}>
                    {error}
                    {error.includes('already exists') && (
                      <Link
                        href="/login"
                        className="mt-2 block text-purple-400 text-sm underline hover:text-purple-300"
                      >
                        Go to login page
                      </Link>
                    )}
                  </AlertDescription>
                </Alert>
              )}

              <FormField
                control={form.control}
                name="full_name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-gray-300">Full Name</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <User className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-gray-500" />
                        <Input
                          placeholder="John Doe"
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
                name="company"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-gray-300">
                      Company <span className="text-gray-500">(optional)</span>
                    </FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Building className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-gray-500" />
                        <Input
                          placeholder="Your company"
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

              <FormField
                control={form.control}
                name="confirmPassword"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-gray-300">Confirm Password</FormLabel>
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

              {/* Terms and Privacy Policy Checkbox */}
              <FormField
                control={form.control}
                name="acceptTerms"
                render={({ field }) => (
                  <FormItem>
                    <div className="flex items-start space-x-2">
                      <FormControl>
                        <input
                          type="checkbox"
                          className="mt-1 h-4 w-4 rounded border-gray-600 bg-gray-800 text-purple-500 focus:ring-2 focus:ring-purple-500 focus:ring-offset-0 focus:ring-offset-gray-900"
                          checked={field.value}
                          onChange={field.onChange}
                          disabled={isLoading}
                        />
                      </FormControl>
                      <div className="space-y-1 leading-none">
                        <FormLabel className="text-gray-300 text-sm">
                          I agree to the{' '}
                          <Link
                            href="/terms"
                            target="_blank"
                            className="text-purple-400 underline hover:text-purple-300"
                          >
                            Terms of Service
                          </Link>{' '}
                          and{' '}
                          <Link
                            href="/privacy"
                            target="_blank"
                            className="text-purple-400 underline hover:text-purple-300"
                          >
                            Privacy Policy
                          </Link>
                        </FormLabel>
                        <FormMessage className="text-red-400 text-xs" />
                      </div>
                    </div>
                  </FormItem>
                )}
              />

              <ExiqusButton type="submit" className="w-full" size="lg" disabled={isLoading}>
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Creating account...
                  </>
                ) : (
                  'Create account'
                )}
              </ExiqusButton>
            </form>
          </Form>

          {/* Benefits list */}
          <div className="space-y-3 pt-4">
            <h3 className="font-medium text-gray-300 text-sm">Get instant access to:</h3>
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-gray-400 text-sm">
                <CheckCircle className="h-4 w-4 text-green-500" />
                <span>10 free repository analyses per month</span>
              </div>
              <div className="flex items-center gap-2 text-gray-400 text-sm">
                <CheckCircle className="h-4 w-4 text-green-500" />
                <span>Evidence-based developer insights</span>
              </div>
              <div className="flex items-center gap-2 text-gray-400 text-sm">
                <CheckCircle className="h-4 w-4 text-green-500" />
                <span>AI-powered code pattern analysis</span>
              </div>
            </div>
          </div>

          {/* Links */}
          <div className="pt-4 text-center text-sm">
            <span className="text-gray-400">Already have an account? </span>
            <Link href="/login" className="font-medium text-purple-400 hover:text-purple-300">
              Sign in
            </Link>
          </div>
        </div>
      </ExiqusCard>
    </div>
  );
}
