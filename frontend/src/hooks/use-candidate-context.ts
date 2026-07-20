// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

/* eslint-disable @typescript-eslint/no-explicit-any */
'use client';

import axios from 'axios';
import { useEffect, useState } from 'react';

interface CandidateContext {
  username: string;
  role: string;
  organization_context: string;
  locked_at: string;
  locked_by_user_id: string;
}

interface UseCandidateContextResult {
  lockedContext: CandidateContext | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useCandidateContext(username: string | null): UseCandidateContextResult {
  const [lockedContext, setLockedContext] = useState<CandidateContext | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchContext = async () => {
    if (!username || username.trim() === '') {
      setLockedContext(null);
      setError(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || '';
      const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;

      const response = await axios.get<CandidateContext>(
        `${apiUrl}/api/v1/candidates/${username}/context`,
        {
          headers: {
            Authorization: token ? `Bearer ${token}` : '',
          },
        }
      );
      setLockedContext(response.data);
    } catch (err: any) {
      // 404 means no locked context - not an error
      if (err.response?.status === 404) {
        setLockedContext(null);
        setError(null);
      } else {
        const message = err.response?.data?.detail || 'Failed to fetch locked context';
        setError(message);
        setLockedContext(null);
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchContext();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [username]);

  return {
    lockedContext,
    isLoading,
    error,
    refetch: fetchContext,
  };
}
