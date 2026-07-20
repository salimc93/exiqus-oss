// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

/**
 * Safe HTML sanitization utilities using DOMPurify
 *
 * Prevents XSS attacks when rendering user-generated or AI-generated content
 * that may contain malicious scripts from analyzed GitHub repositories.
 */
import DOMPurify from 'dompurify';

/**
 * Sanitize configuration - whitelist only the tags we generate
 */
const SANITIZE_CONFIG = {
  ALLOWED_TAGS: ['strong', 'em', 'code', 'b', 'i', 'span', 'br'],
  ALLOWED_ATTR: ['class'],
  USE_PROFILES: { html: true },
};

/**
 * Sanitize HTML string to prevent XSS
 */
export function sanitizeHtml(dirty: string): string {
  return DOMPurify.sanitize(dirty, SANITIZE_CONFIG);
}

/**
 * Convert markdown bold/italic/code to HTML and sanitize
 * Used for rendering AI-generated analysis content safely
 */
export function renderMarkdownSafe(text: string): string {
  const htmlText = text
    .replace(/\s*---+\s*/g, ' ') // Remove horizontal rules (---)
    .replace(/^##\s+/gm, '') // Remove ## headers at start of line
    .replace(/^#+\s*/gm, '') // Remove other header markers
    .replace(/\s*#+\s*$/gm, '') // Remove trailing header markers
    .replace(/\*\*([^*]+)\*\*/g, '<strong class="font-semibold text-gray-100">$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code class="rounded bg-gray-800 px-1 py-0.5 text-sm">$1</code>');

  // Sanitize to remove any malicious content that might have slipped through
  return DOMPurify.sanitize(htmlText, SANITIZE_CONFIG);
}

/**
 * Simple markdown bold to HTML conversion with sanitization
 * Used for shorter text like observations
 */
export function renderBoldSafe(text: string): string {
  const htmlText = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  return DOMPurify.sanitize(htmlText, SANITIZE_CONFIG);
}
