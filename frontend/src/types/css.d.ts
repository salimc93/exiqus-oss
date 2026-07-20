// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

// Type declarations for side-effect stylesheet imports, e.g.
//   import './globals.css'
//
// Next normally supplies these through next-env.d.ts, but that file is
// generated (and gitignored), so it does not exist on a fresh checkout. CI runs
// `typecheck` before `build`, so nothing has generated it yet and TypeScript
// reports TS2882. Declaring it here is version-controlled and independent of
// generation order.

declare module '*.css';
declare module '*.scss';
declare module '*.sass';
