// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import { useRouter } from 'next/navigation';
import type React from 'react';
import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { toast } from 'sonner';

import { api, setAccessToken, setGlobalLogoutHandler, useMockData } from '@/lib/api-client';
import type { AuthTokens, LoginRequest, SignupRequest, User } from '@/types';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (data: LoginRequest) => Promise<void>;
  signup: (data: SignupRequest) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Mock user for development
const MOCK_USER: User = {
  id: 'mock-user-id',
  email: 'test@example.com',
  full_name: 'Test User',
  company: 'Test Company',
  role: 'user',
  is_active: true,
  subscription_plan: 'growth',
  subscription_status: 'active',
  usage_consumed: 0,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [isInitialized, setIsInitialized] = useState(false);
  const router = useRouter();
  const isMockMode = useMockData();

  // Load user profile
  const loadUser = useCallback(async () => {
    try {
      // Always use API call - mock mode is handled in api-client
      const response = await api.getProfile();
      // Ensure role is properly typed
      const userData = {
        ...response.data,
        role: response.data.role as 'user' | 'admin' | 'enterprise',
        subscription_plan: response.data.subscription_plan as
          | 'free'
          | 'starter'
          | 'growth'
          | 'scale',
        subscription_status: response.data.subscription_status as
          | 'active'
          | 'canceled'
          | 'past_due'
          | 'suspended'
          | 'trialing',
      };
      setUser(userData);

      // Set mock token if in mock mode
      if (isMockMode && localStorage.getItem('mock_logged_in') === 'true') {
        setAccessToken('mock-access-token');
      }
    } catch {
      // User not authenticated
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, [isMockMode]);

  // Initial load
  useEffect(() => {
    // Skip if already initialized
    if (isInitialized) {
      return;
    }

    // Mark as initialized immediately to prevent multiple runs
    setIsInitialized(true);

    const initializeAuth = async () => {
      // Don't try to load user on auth pages only (admin pages can have user context too)
      const isAuthPage =
        typeof window !== 'undefined' &&
        (window.location.pathname.includes('/auth/') ||
          window.location.pathname.includes('/login') ||
          window.location.pathname.includes('/signup') ||
          window.location.pathname.includes('/reset-password') ||
          window.location.pathname.includes('/forgot-password'));

      if (isAuthPage) {
        // On auth pages, just set loading to false
        setLoading(false);
        return;
      }

      // In mock mode, check if user is logged in
      if (isMockMode) {
        const mockLoggedIn = localStorage.getItem('mock_logged_in') === 'true';
        if (mockLoggedIn) {
          setUser(MOCK_USER);
          setAccessToken('mock-access-token');
        }
        setLoading(false);
      } else {
        // In real mode, try to restore access token from localStorage
        // Note: Refresh token is in httpOnly cookie, not accessible client-side
        const storedAccessToken = localStorage.getItem('access_token');

        if (storedAccessToken) {
          // Set the access token in api-client
          setAccessToken(storedAccessToken);
          // Try to load user - if access token expired, interceptor will use refresh cookie
          await loadUser();
        } else {
          // No access token - user needs to login
          setLoading(false);
        }
      }
    };

    initializeAuth();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run once on mount

  // Login function
  const login = async (data: LoginRequest) => {
    try {
      if (isMockMode) {
        // Mock login
        if (data.email === 'test@example.com' && data.password === 'password') {
          localStorage.setItem('mock_logged_in', 'true');
          // Set a mock token for API calls
          setAccessToken('mock-access-token');
          setUser(MOCK_USER);
          toast.success('Logged in successfully!');
          router.push('/dashboard');
        } else {
          throw new Error('Invalid credentials. Use test@example.com / password');
        }
      } else {
        // Real API login
        const response = await api.login(data);
        const tokens: AuthTokens = response.data;

        // Store access token (refresh token is set via httpOnly cookie by server)
        setAccessToken(tokens.access_token);
        localStorage.setItem('access_token', tokens.access_token);
        // Note: refresh_token is now in httpOnly cookie, not in localStorage

        // Load user profile
        await loadUser();

        toast.success('Logged in successfully!');
        router.push('/dashboard');
      }
    } catch (error) {
      const errorResponse = error as {
        response?: { data?: { detail?: string }; status?: number };
        message?: string;
      };

      let message = errorResponse.response?.data?.detail || errorResponse.message || 'Login failed';

      // Make error messages more user-friendly
      if (errorResponse.response?.status === 403) {
        if (message.toLowerCase().includes('not verified')) {
          message =
            'Please verify your email before logging in. Check your inbox for the verification link.';
        } else {
          message = 'Access denied. Please check your credentials.';
        }
      } else if (errorResponse.response?.status === 401) {
        message = 'Invalid email or password. Please try again.';
      } else if (errorResponse.response?.status === 404) {
        message = 'Unable to connect to the server. Please try again later.';
      } else if (message.includes('Request failed with status code')) {
        // Generic axios error - make it user-friendly
        if (message.includes('403')) {
          message = 'Email not verified. Please check your email for verification link.';
        } else if (message.includes('401')) {
          message = 'Invalid credentials. Please check your email and password.';
        } else if (message.includes('404')) {
          message = 'Connection error. Please try again later.';
        } else {
          message = 'An error occurred. Please try again.';
        }
      }

      toast.error(message);
      throw new Error(message);
    }
  };

  // Signup function
  const signup = async (data: SignupRequest) => {
    try {
      if (isMockMode) {
        // Mock signup with email verification flow
        localStorage.setItem('mock_logged_in', 'false'); // Not logged in until verified
        localStorage.setItem('mock_user_email', data.email);
        localStorage.setItem('mock_user_verified', 'false');
        toast.success('Account created! Please check your email to verify your account.');
        router.push(`/auth/verify-email-sent?email=${encodeURIComponent(data.email)}`);
      } else {
        // Real API signup
        await api.signup(data);

        // After successful signup, redirect to verification page
        // The backend automatically sends verification email
        toast.success('Account created! Please check your email to verify your account.');
        router.push(`/auth/verify-email-sent?email=${encodeURIComponent(data.email)}`);
      }
    } catch (error) {
      const errorResponse = error as {
        response?: { status?: number; data?: { detail?: string } };
        message?: string;
      };
      let message =
        errorResponse.response?.data?.detail || errorResponse.message || 'Signup failed';

      // Make 409 conflict errors more user-friendly
      if (errorResponse.response?.status === 409) {
        message =
          'An account with this email already exists. Please login or use a different email address.';
      }

      // Make 400 bad request errors more user-friendly (includes disposable email rejection)
      if (errorResponse.response?.status === 400) {
        // The backend already sends a clear message about disposable emails
        // Just use it directly if available
        if (errorResponse.response?.data?.detail) {
          message = errorResponse.response.data.detail;
        }
      }

      toast.error(message);
      throw error;
    }
  };

  // Logout function
  const logout = async () => {
    try {
      if (!isMockMode) {
        await api.logout();
      }
    } catch {
      // Ignore logout errors
    } finally {
      // Clear local state
      if (isMockMode) {
        localStorage.removeItem('mock_logged_in');
      } else {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
      }
      setAccessToken(null);
      setUser(null);
      router.push('/');
      toast.success('Logged out successfully');
    }
  };

  // Graceful logout handler for token expiration
  const handleGracefulLogout = useCallback(async () => {
    // Clear local state without making API call since token is expired
    if (isMockMode) {
      localStorage.removeItem('mock_logged_in');
    } else {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    }
    setAccessToken(null);
    setUser(null);

    // Show user-friendly notification
    toast.error('Your session has expired. Please log in again.', {
      duration: 5000,
    });

    // Redirect to login
    router.push('/login');
  }, [isMockMode, router]);

  // Refresh user profile
  const refreshUser = async () => {
    await loadUser();
  };

  // Register the graceful logout handler with the API client
  useEffect(() => {
    setGlobalLogoutHandler(handleGracefulLogout);
  }, [handleGracefulLogout]);

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        signup,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// Hook to use auth context
export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
