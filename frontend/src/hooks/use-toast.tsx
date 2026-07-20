// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

import * as React from 'react';
import { toast as sonnerToast } from 'sonner';

export interface ToastProps {
  title?: string;
  description?: string;
  variant?: 'default' | 'destructive';
}

export function useToast() {
  const toast = React.useCallback(({ title, description, variant }: ToastProps) => {
    if (variant === 'destructive') {
      sonnerToast.error(title || 'Error', {
        description,
      });
    } else {
      sonnerToast.success(title || 'Success', {
        description,
      });
    }
  }, []);

  return { toast };
}
