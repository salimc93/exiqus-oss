// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import { useEffect, useState } from 'react';

import { UnauthorizedAccess } from '@/components/auth/unauthorized-access';
import { useAuth } from '@/contexts/auth-context';

export function useAuthGuard() {
  const { user, loading } = useAuth();
  const [showUnauthorized, setShowUnauthorized] = useState(false);

  useEffect(() => {
    // Wait for auth to finish loading
    if (!loading && !user) {
      setShowUnauthorized(true);
    } else if (user) {
      setShowUnauthorized(false);
    }
  }, [loading, user]);

  return {
    isAuthenticated: !!user,
    isLoading: loading,
    showUnauthorized,
    UnauthorizedComponent: showUnauthorized ? UnauthorizedAccess : null,
  };
}

// Higher Order Component for protected pages
export function withAuthGuard<P extends object>(Component: React.ComponentType<P>) {
  return function ProtectedComponent(props: P) {
    const { isLoading, showUnauthorized, UnauthorizedComponent } = useAuthGuard();

    // Show loading state
    if (isLoading) {
      return (
        <div className="flex min-h-screen items-center justify-center">
          <div className="text-center">
            <div className="mb-4 inline-flex h-16 w-16 items-center justify-center">
              <div className="h-12 w-12 animate-spin rounded-full border-4 border-purple-600 border-t-transparent" />
            </div>
            <p className="text-gray-600">Preparing your talent intelligence dashboard...</p>
          </div>
        </div>
      );
    }

    // Show unauthorized component
    if (showUnauthorized && UnauthorizedComponent) {
      return <UnauthorizedComponent />;
    }

    // Show the protected component
    return <Component {...props} />;
  };
}
