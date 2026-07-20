// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

import { LoadingLogo } from '@/components/ui/loading-logo';

export default function Loading() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0A0A0A]">
      <LoadingLogo size="lg" message="Loading..." />
    </div>
  );
}
