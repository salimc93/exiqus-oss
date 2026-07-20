// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

// User and Authentication Types
export interface User {
  id: string;
  email: string;
  full_name: string;
  company?: string;
  role: 'user' | 'admin' | 'enterprise';
  is_active: boolean;
  subscription_plan: 'free' | 'starter' | 'growth' | 'scale' | 'scale_plus';
  subscription_status: 'active' | 'canceled' | 'past_due' | 'suspended' | 'trialing';
  trial_end_date?: string | null;
  usage_consumed: number;
  created_at: string;
  updated_at: string;
}

export interface AuthTokens {
  access_token: string;
  token_type: string;
  expires_in: number;
  refresh_token: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface SignupRequest {
  email: string;
  password: string;
  full_name: string;
  company?: string;
}

// Evidence-Based Types (Great Purge compliant)
export interface InsightModel {
  category: string;
  description: string;
  evidence: string[];
  confidence: string;
  impact: string;
}

export interface QuestionModel {
  category: string;
  question: string;
  evidence_reference: string;
  follow_ups: string[];
  what_to_listen_for: string;
  context_relevance: string;
}

export interface RecommendationModel {
  type: string; // "strength", "concern", "neutral"
  text: string;
  priority: string;
  evidence?: string;
}

export interface EvidencePatternModel {
  name: string;
  pattern_type: string; // technical, behavioral, collaboration, quality
  evidence: string;
  context: string;
  insight: string;
  category: string; // technical, professional, communication, growth

  // Tier-aware fields for locked patterns
  source_depth?: string; // Surface/Architectural/Forensic/Maximum
  confidence?: string; // Low/Medium/High based on data richness
  upgrade_hint?: string | null; // Hint for higher tier value
  tier_locked?: boolean; // True if pattern is locked for current tier
  required_tier?: string | null; // Required tier to unlock this pattern
  preview_teaser?: string | null; // Preview text for locked patterns
}

// Analysis Types
export interface AnalysisRequest {
  repository_url: string;
  context: 'startup' | 'enterprise' | 'agency' | 'open_source';
  force_refresh?: boolean;
}

export interface AnalysisResponse {
  id?: string; // Analysis ID for retrieval
  repository_url: string;
  repository_name: string;
  analysis_date: string;
  subscription_tier: string;
  context: string;

  // Summary - NO SCORES
  executive_summary: string;
  repository_type: string;
  confidence_explanation: string; // Changed from confidence_score

  // Evidence-based content
  insights: InsightModel[];
  insights_count: number;

  questions: QuestionModel[];
  questions_count: number;

  recommendations: RecommendationModel[];
  recommendations_count: number;

  evidence_patterns: EvidencePatternModel[];
  evidence_patterns_count: number;

  // Limitations
  limitations: string[];
  data_limitations: string[];

  // Flags
  green_flags: string[];
  red_flags: string[];

  // Areas to explore (added for frontend compatibility)
  areas_to_explore?: string[];

  // Metadata from backend response
  metadata?: {
    analysis_id?: string;
    [key: string]: unknown;
  };

  // Legacy field for backward compatibility
  analysis_id?: string;
}

// Analysis Details (for the detail page)
export interface AnalysisDetails {
  id: string;
  user_id: string;
  repository_url: string;
  repository_name: string;
  context: string;
  github_username?: string; // GitHub username for candidate linking
  batch_id?: string; // Batch ID if part of a batch analysis
  key_insight?: string; // Executive summary or key insight
  full_analysis: {
    repository_url: string;
    context: string;
    analysis: AnalysisResponse;
    metadata: {
      analysis_id: string;
      repository_type?: string;
      confidence_grade?: string;
      ai_analysis_used?: boolean;
      response_time_seconds?: number;
      timestamp: string;
      cached?: boolean;
      data_completeness?: number;
    };
  };
  analysis_version?: string;
  processing_time_ms?: number;
  token_count?: number;
  allow_training?: boolean;
  created_at: string;
  updated_at: string;
}

// Billing Types
export interface Subscription {
  plan: 'free' | 'starter' | 'growth' | 'scale' | 'scale_plus';
  status: 'active' | 'canceled' | 'past_due' | 'suspended' | 'trialing';
  current_period_end?: string;
  cancel_at_period_end: boolean;
  stripe_subscription_id?: string;
  stripe_customer_id?: string;
}

export interface UsageSummary {
  user_id: string;
  current_period: string;
  plan: string;
  usage_quota: number;
  usage_consumed: number;
  usage_remaining: number;
  usage_percentage: number;
  plan_features: string[];
}

// API Key Types
export interface APIKey {
  id: string;
  name: string;
  key_prefix: string;
  permissions: string[];
  last_used?: string;
  created_at: string;
  expires_at?: string;
  usage_count: number;
}

// Contact Types
export interface ContactMessage {
  name: string;
  email: string;
  subject: string;
  message: string;
}

// Dashboard Types
export interface DashboardMetrics {
  total_analyses: number;
  analyses_this_month: number;
  usage_percentage: number;
  days_until_reset: number;
  recent_analyses: RecentAnalysis[];
}

export interface RecentAnalysis {
  id: string;
  repository_url: string;
  context: string;
  confidence_explanation: string; // Changed from confidence_score
  evidence_count: number; // New: number of evidence patterns found
  analyzed_at: string;
  cached: boolean;
}

// Batch Analysis Types
export interface BatchAnalysisRequest {
  repositories: Array<{
    repository_url: string;
    context: string;
  }>;
  concurrency_mode?: 'sequential' | 'balanced' | 'fast';
}

export interface BatchAnalysisResponse {
  batch_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  total_repositories: number;
  completed_count: number;
  failed_count: number;
  results?: unknown[];
  error_message?: string;
  error_messages?: string[];
  created_at: string;
  updated_at?: string;
}

export interface BatchHistoryItem {
  batch_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  total_repositories: number;
  completed_count: number;
  failed_count: number;
  context: string;
  concurrency_mode?: 'sequential' | 'balanced' | 'fast';
  processing_time_ms?: number;
  created_at: string;
  updated_at?: string;
}

export interface BatchHistoryResponse {
  success: boolean;
  data: BatchHistoryItem[];
  message: string;
  total_count?: number;
  items?: BatchHistoryItem[]; // For pagination
}

export interface BatchStatistics {
  period_days: number;
  total_batches: number;
  total_repositories: number;
  total_successful: number;
  total_failed: number;
  total_cost: number;
  avg_processing_time_ms: number;
  success_rate: number;
  status_breakdown: {
    [key: string]: number;
  };
}
