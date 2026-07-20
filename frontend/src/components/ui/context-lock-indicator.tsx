// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

/* eslint-disable @typescript-eslint/no-explicit-any */
'use client';

import axios from 'axios';
import { AlertTriangle, Lock, X } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';

import { ExiqusButton } from './exiqus-components';

interface ContextLockIndicatorProps {
  username: string;
  currentRole: string;
  currentContext: string;
  lockedRole?: string;
  lockedContext?: string;
  isLocked: boolean;
  onContextReset?: () => void;
  className?: string;
}

export function ContextLockIndicator({
  username,
  currentRole,
  currentContext,
  lockedRole,
  lockedContext,
  isLocked,
  onContextReset,
}: ContextLockIndicatorProps) {
  const [isResetting, setIsResetting] = useState(false);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);

  const handleResetClick = () => {
    setShowConfirmDialog(true);
  };

  const handleCancelReset = () => {
    setShowConfirmDialog(false);
  };

  const handleConfirmReset = async () => {
    setShowConfirmDialog(false);
    setIsResetting(true);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || '';
      const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;

      await axios.delete(`${apiUrl}/api/v1/candidates/${username}/context`, {
        headers: {
          Authorization: token ? `Bearer ${token}` : '',
        },
      });

      toast.success(`Context reset for @${username}. You can now analyze with different settings.`);
      onContextReset?.();
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Failed to reset context';
      toast.error(message);
    } finally {
      setIsResetting(false);
    }
  };

  // Context mismatch
  const isMismatch = isLocked && (lockedRole !== currentRole || lockedContext !== currentContext);

  if (!isLocked) {
    return null;
  }

  return (
    <>
      {/* Context Lock Indicator */}
      <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3">
        <div className="flex items-center gap-3">
          <Lock className="h-4 w-4 shrink-0 text-amber-400" />
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-medium text-gray-100 text-sm">
                Existing analyses found for{' '}
                <span className="font-semibold text-white">@{username}</span>
              </span>
              <span className="text-gray-400 text-xs">·</span>
              <span className="font-medium text-gray-200 text-xs">
                Using:{' '}
                <span className="font-semibold text-amber-400">{lockedRole?.toUpperCase()}</span> |{' '}
                <span className="font-semibold text-amber-400">{lockedContext?.toUpperCase()}</span>
              </span>
            </div>
            {isMismatch && (
              <p className="mt-1 font-medium text-amber-200 text-xs">
                Your selected settings don&apos;t match. Change settings above or reset to
                re-analyze.
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={handleResetClick}
            disabled={isResetting}
            className="ml-auto shrink-0 font-medium text-gray-300 text-xs underline underline-offset-2 transition-colors hover:text-white disabled:opacity-50"
          >
            {isResetting ? 'Resetting...' : 'Reset context'}
          </button>
        </div>
      </div>

      {/* Custom Confirmation Dialog */}
      {showConfirmDialog && (
        <div className="fade-in fixed inset-0 z-50 flex animate-in items-center justify-center p-4 duration-200">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/80 backdrop-blur-sm"
            onClick={handleCancelReset}
          />

          {/* Dialog */}
          <div className="zoom-in-95 relative w-full max-w-md animate-in rounded-xl border border-red-500/30 bg-gradient-to-b from-gray-900 to-black p-6 shadow-2xl duration-200">
            {/* Close button */}
            <button
              type="button"
              onClick={handleCancelReset}
              className="absolute top-4 right-4 text-gray-500 transition-colors hover:text-gray-300"
            >
              <X className="h-5 w-5" />
            </button>

            {/* Icon */}
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-500/10 ring-1 ring-red-500/30">
              <AlertTriangle className="h-6 w-6 text-red-400" />
            </div>

            {/* Title */}
            <h3 className="mb-2 font-semibold text-white text-xl">Reset @{username}?</h3>

            {/* Message */}
            <p className="mb-6 text-gray-400 text-sm leading-relaxed">
              This will remove all existing analyses from the Candidate Hub. You&apos;ll need to
              re-analyze with your new settings to see data again.
            </p>

            {/* Actions */}
            <div className="flex gap-3">
              <ExiqusButton
                type="button"
                onClick={handleConfirmReset}
                className="flex-1 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800"
              >
                Reset Context
              </ExiqusButton>
              <ExiqusButton
                type="button"
                onClick={handleCancelReset}
                variant="outline"
                className="flex-1"
              >
                Cancel
              </ExiqusButton>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
