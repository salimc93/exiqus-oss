// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

import axios, { type AxiosInstance } from 'axios';

import type {
  AnalysisRequest,
  AnalysisResponse,
  APIKey,
  AuthTokens,
  BatchAnalysisRequest,
  BatchAnalysisResponse,
  BatchHistoryResponse,
  BatchStatistics,
  ContactMessage,
  DashboardMetrics,
  LoginRequest,
  SignupRequest,
  UsageSummary,
  User,
} from '@/types';

// Check if we're in mock mode
const MOCK_MODE = process.env.NEXT_PUBLIC_MOCK_API === 'true';
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '';

// Create axios instance with default timeout
const axiosInstance: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 180000, // Default 3 minutes for most requests
  withCredentials: true, // Send httpOnly cookies with requests (for refresh token)
});

// Token management
// Note: Only access token is stored client-side. Refresh token is in httpOnly cookie.
let accessToken: string | null = null;

// Global logout handler for graceful token expiration
let globalLogoutHandler: (() => Promise<void>) | null = null;
let isHandlingSessionExpiry = false; // Prevent multiple simultaneous logout calls

export const setGlobalLogoutHandler = (handler: () => Promise<void>) => {
  globalLogoutHandler = handler;
};

// Initialize access token from localStorage on module load
// Note: Refresh token is handled via httpOnly cookie (server-side only)
if (typeof window !== 'undefined') {
  const storedAccessToken = localStorage.getItem('access_token');

  if (storedAccessToken) {
    accessToken = storedAccessToken;
    // Don't set default header - let interceptor handle it based on endpoint
  }
}

// Set access token
export const setAccessToken = (token: string | null) => {
  accessToken = token;
  if (token) {
    axiosInstance.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    // Persist to localStorage
    if (typeof window !== 'undefined') {
      localStorage.setItem('access_token', token);
    }
  } else {
    delete axiosInstance.defaults.headers.common['Authorization'];
    // Remove from localStorage
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
    }
  }
};

// Get access token (refresh token is httpOnly cookie, not accessible client-side)
export const getAccessToken = () => accessToken;

// Check if using mock data
export const useMockData = () => MOCK_MODE;

// Mock data responses
const mockResponses = {
  login: {
    access_token: 'mock-access-token',
    token_type: 'bearer',
    expires_in: 3600,
    refresh_token: 'mock-refresh-token',
  },
  profile: {
    id: 'mock-user-id',
    email: 'test@example.com',
    full_name: 'Test User',
    company: 'Test Company',
    role: 'user',
    is_active: true,
    subscription_plan: 'starter',
    subscription_status: 'active',
    usage_consumed: 1,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  analyze: {
    id: 'mock-analysis-123',
    repository_url: 'https://github.com/test/repo',
    repository_name: 'test/repo',
    analysis_date: new Date().toISOString(),
    subscription_tier: 'starter',
    context: 'startup',
    metadata: {
      analysis_id: 'mock-analysis-123',
    },
    analysis_id: 'mock-analysis-123',
    executive_summary:
      'This repository demonstrates strong TypeScript expertise with modern development practices.',
    repository_type: 'portfolio_project',
    confidence_explanation:
      'High confidence based on comprehensive code analysis and active development patterns',
    insights: [
      {
        category: 'technical_skills',
        description: 'Strong TypeScript proficiency demonstrated',
        evidence: ['89.5% TypeScript codebase', 'Advanced type patterns in 15 files'],
        confidence: 'high',
        impact: 'positive',
      },
    ],
    insights_count: 1,
    questions: [],
    questions_count: 0,
    recommendations: [
      {
        type: 'strength',
        text: 'Strong TypeScript expertise with modern development practices',
        priority: 'high',
        evidence: '89.5% TypeScript, testing infrastructure, active maintenance',
      },
    ],
    recommendations_count: 1,
    evidence_patterns: [
      {
        name: 'language_expertise',
        pattern_type: 'technical',
        evidence: '89.5% TypeScript across 343 files',
        context: 'Modern web development expertise',
        insight: 'Deep TypeScript experience in production code',
        category: 'technical',
      },
    ],
    evidence_patterns_count: 1,
    limitations: ['Cannot assess soft skills from code alone'],
    data_limitations: ['No access to code reviews'],
    green_flags: ['Has testing infrastructure', 'Consistent commit patterns'],
    red_flags: [],
  },
  usage: {
    user_id: 'mock-user-id',
    current_period: new Date().toISOString().slice(0, 7),
    plan: 'starter',
    usage_quota: 10,
    usage_consumed: 1,
    usage_remaining: 9,
    usage_percentage: 10,
    plan_features: ['AI Analysis', 'Email Support'],
  },
  dashboard: {
    total_analyses: 12,
    analyses_this_month: 5,
    usage_percentage: 10,
    days_until_reset: 25,
    recent_analyses: [
      {
        id: '1',
        repository_url: 'https://github.com/test/repo',
        context: 'startup',
        confidence_explanation: 'High confidence based on comprehensive analysis',
        evidence_count: 7,
        analyzed_at: new Date().toISOString(),
        cached: false,
      },
    ],
  },
};

// Request interceptor for auth
axiosInstance.interceptors.request.use(
  (config) => {
    // Build the full URL to check against
    const fullUrl = config.url || '';
    const isAdminEndpoint = fullUrl.includes('/admin/');

    // Always check localStorage for tokens since they might have been set after initial load
    if (isAdminEndpoint) {
      // For admin endpoints, ALWAYS use admin token from localStorage
      const adminToken = localStorage.getItem('adminToken');
      if (adminToken) {
        config.headers.Authorization = `Bearer ${adminToken}`;
      }
    } else {
      // For regular endpoints, use regular access token
      const regularToken = accessToken || localStorage.getItem('access_token');
      if (regularToken && !config.headers.Authorization) {
        config.headers.Authorization = `Bearer ${regularToken}`;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for token refresh
axiosInstance.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const isAdminEndpoint = originalRequest?.url?.includes('/admin/');

    // Handle admin token expiration
    if (error.response?.status === 401 && isAdminEndpoint) {
      // Admin token expired, redirect to admin login
      localStorage.removeItem('adminToken');
      if (typeof window !== 'undefined') {
        window.location.href = '/admin-portal/login';
      }
      return Promise.reject(error);
    }

    // Attempt token refresh on 401 for non-admin endpoints
    // Refresh token is sent automatically via httpOnly cookie
    if (error.response?.status === 401 && !originalRequest._retry && !isAdminEndpoint) {
      originalRequest._retry = true;

      try {
        const response = await api.refreshToken();
        setAccessToken(response.data.access_token);
        // Note: refresh_token is set via httpOnly cookie by the server

        // Retry original request with new token
        originalRequest.headers.Authorization = `Bearer ${response.data.access_token}`;
        return axiosInstance(originalRequest);
      } catch (refreshError) {
        // Refresh failed, clear access token
        setAccessToken(null);

        // Use global logout handler for graceful UX if available, with debouncing
        if (globalLogoutHandler && !isHandlingSessionExpiry) {
          isHandlingSessionExpiry = true;
          await globalLogoutHandler();
          // Reset after a short delay to allow future logouts
          setTimeout(() => {
            isHandlingSessionExpiry = false;
          }, 1000);
        } else if (!isHandlingSessionExpiry) {
          // Fallback to hard redirect
          window.location.href = '/login';
        }

        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

// API client
export const api = {
  // Auth endpoints
  login: async (data: LoginRequest) => {
    if (MOCK_MODE) {
      localStorage.setItem('mock_logged_in', 'true');
      return { data: mockResponses.login };
    }
    const response = await axiosInstance.post<AuthTokens>('/api/v1/auth/login', data);
    return response;
  },

  signup: async (data: SignupRequest) => {
    if (MOCK_MODE) {
      localStorage.setItem('mock_logged_in', 'true');
      return { data: mockResponses.login };
    }
    const response = await axiosInstance.post<AuthTokens>('/api/v1/auth/register', data);
    return response;
  },

  logout: async () => {
    if (MOCK_MODE) {
      localStorage.removeItem('mock_logged_in');
      return { data: { message: 'Logged out' } };
    }
    const response = await axiosInstance.post('/api/v1/auth/logout');
    return response;
  },

  refreshToken: async () => {
    // Create a new axios instance without interceptors to avoid infinite loop
    // Uses withCredentials to send httpOnly cookie containing refresh token
    const plainAxios = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
      withCredentials: true, // Send httpOnly cookie with refresh token
    });

    // Server reads refresh token from httpOnly cookie, not request body
    const response = await plainAxios.post<AuthTokens>('/api/v1/auth/refresh');
    return response;
  },

  // User endpoints
  getProfile: async () => {
    if (MOCK_MODE && localStorage.getItem('mock_logged_in') === 'true') {
      return { data: mockResponses.profile };
    }
    const response = await axiosInstance.get<User>('/api/v1/auth/profile');
    return response;
  },

  updateProfile: async (data: Partial<User>) => {
    const response = await axiosInstance.put<User>('/api/v1/auth/profile', data);
    return response;
  },

  // Analysis endpoints
  analyze: async (data: AnalysisRequest, timeoutMs?: number) => {
    if (MOCK_MODE) {
      return { data: mockResponses.analyze };
    }
    // Use custom timeout for analysis endpoint (can be long-running)
    // Default to 5 minutes if not specified
    const analysisTimeout = timeoutMs || 300000; // 5 minutes default
    const response = await axiosInstance.post<AnalysisResponse>('/api/v1/analyze', data, {
      timeout: analysisTimeout,
    });
    return response;
  },

  cancelAnalysis: async (analysisId: string) => {
    const response = await axiosInstance.post(`/api/v1/cancel/${analysisId}`);
    return response;
  },

  cancelBatchAnalysis: async (batchId: string) => {
    const response = await axiosInstance.post(`/api/v1/batch/cancel/${batchId}`);
    return response;
  },

  getAnalysis: async (id: string) => {
    if (MOCK_MODE) {
      return {
        data: {
          id,
          user_id: 'mock-user-id',
          repository_url: 'https://github.com/test/repo',
          repository_name: 'test/repo',
          context: 'startup',
          full_analysis: {
            repository_url: 'https://github.com/test/repo',
            context: 'startup',
            analysis: mockResponses.analyze,
            metadata: {
              analysis_id: id,
              repository_type: 'portfolio_project',
              confidence_grade: 'A',
              ai_analysis_used: true,
              response_time_seconds: 12.5,
              timestamp: new Date().toISOString(),
              cached: false,
              data_completeness: 0.95,
            },
          },
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      };
    }
    const response = await axiosInstance.get(`/api/v1/analyses/${id}`);
    return response;
  },

  getAnalyses: async (params?: { cursor?: string | null; limit?: number }) => {
    if (MOCK_MODE) {
      return {
        data: {
          items: [
            {
              id: '1',
              repository_url: 'https://github.com/test/repo',
              repository_name: 'test/repo',
              context: 'startup',
              confidence_explanation: 'High confidence based on comprehensive analysis',
              created_at: new Date().toISOString(),
            },
          ],
          cursor: null,
          has_next: false,
          has_prev: false,
          total_count: 1,
        },
      };
    }
    const response = await axiosInstance.get('/api/v1/analyses', { params });
    return response;
  },

  // Usage endpoints
  getUsage: async () => {
    if (MOCK_MODE) {
      return { data: mockResponses.usage };
    }
    const response = await axiosInstance.get<UsageSummary>('/api/v1/billing/usage');
    return response;
  },

  // Dashboard
  getDashboard: async () => {
    if (MOCK_MODE) {
      return { data: mockResponses.dashboard };
    }
    const response = await axiosInstance.get<DashboardMetrics>('/api/v1/dashboard');
    return response;
  },

  // Contact
  sendContactMessage: async (data: ContactMessage) => {
    const response = await axiosInstance.post('/api/v1/contact', data);
    return response;
  },

  getMyMessages: async (params?: { page?: number; page_size?: number }) => {
    const response = await axiosInstance.get('/api/v1/contact/my-messages', { params });
    return response;
  },

  // API Keys
  getAPIKeys: async () => {
    const response = await axiosInstance.get<APIKey[]>('/api/v1/api-keys');
    return response;
  },

  createAPIKey: async (data: { name: string; permissions: string[] }) => {
    const response = await axiosInstance.post<APIKey>('/api/v1/api-keys', data);
    return response;
  },

  deleteAPIKey: async (id: string) => {
    const response = await axiosInstance.delete(`/api/v1/api-keys/${id}`);
    return response;
  },

  // Email verification
  verifyEmail: async (token: string) => {
    const response = await axiosInstance.get(
      `/api/v1/auth/verify-email?token=${encodeURIComponent(token)}`
    );
    return response;
  },

  resendVerificationEmail: async (email: string) => {
    const response = await axiosInstance.post('/api/v1/auth/resend-verification', { email });
    return response;
  },

  // Password reset
  requestPasswordReset: async (email: string) => {
    const response = await axiosInstance.post('/api/v1/auth/forgot-password', { email });
    return response;
  },

  resetPassword: async (token: string, password: string) => {
    const response = await axiosInstance.post('/api/v1/auth/reset-password', { token, password });
    return response;
  },

  // Batch Analysis endpoints
  submitBatchAnalysis: async (data: BatchAnalysisRequest, signal?: AbortSignal) => {
    // Calculate timeout based on concurrency mode and number of repos
    const numRepos = data.repositories.length;
    const mode = data.concurrency_mode || 'sequential';
    let timeoutMs: number;

    if (mode === 'sequential') {
      // 5 min per repo + buffer (increased for enterprise context)
      timeoutMs = (numRepos * 300 + 120) * 1000; // Add 2 min buffer
    } else if (mode === 'balanced') {
      // 3 min per batch of 2 + buffer
      const numBatches = Math.ceil(numRepos / 2);
      timeoutMs = (numBatches * 180 + 120) * 1000;
    } else {
      // fast mode: 2 min per batch of 5 + buffer
      const numBatches = Math.ceil(numRepos / 5);
      timeoutMs = (numBatches * 120 + 120) * 1000;
    }

    // Cap at 65 minutes (backend max is 60 min + buffer)
    timeoutMs = Math.min(timeoutMs, 3900000);

    const response = await axiosInstance.post<BatchAnalysisResponse>('/api/v1/batch', data, {
      timeout: timeoutMs,
      signal, // Add abort signal support
    });
    return response;
  },

  getBatchStatus: async (batchId: string) => {
    const response = await axiosInstance.get<BatchAnalysisResponse>(
      `/api/v1/batch-history/${batchId}`
    );
    return response;
  },

  exportBatchResults: async (batchId: string, format: 'json' | 'csv' | 'zip' = 'json') => {
    const response = await axiosInstance.get(`/api/v1/analysis/batch/${batchId}/export`, {
      params: { format },
      responseType: format === 'json' ? 'json' : 'blob',
    });
    return response;
  },

  // Batch History endpoints (Scale/Scale+ only)
  getBatchHistory: async (params?: {
    limit?: number;
    offset?: number;
    status?: 'pending' | 'processing' | 'completed' | 'failed';
  }) => {
    const response = await axiosInstance.get<BatchHistoryResponse>('/api/v1/batch-history/', {
      params,
    });
    return response;
  },

  getBatchDetails: async (batchId: string) => {
    const response = await axiosInstance.get<{
      success: boolean;
      data: BatchAnalysisResponse;
      message: string;
    }>(`/api/v1/batch-history/${batchId}`);
    // Return just the data field which contains the actual batch details
    return { ...response, data: response.data.data };
  },

  getBatchAggregatedInsights: async (batchId: string) => {
    const response = await axiosInstance.get(
      `/api/v1/batch-history/${batchId}/aggregated-insights`
    );
    return response;
  },

  getBatchStatistics: async () => {
    const response = await axiosInstance.get<BatchStatistics>(
      '/api/v1/batch-history/statistics/summary'
    );
    return response;
  },

  downloadBatchExport: async (batchId: string, format: 'csv' | 'zip') => {
    const response = await axiosInstance.get(`/api/v1/analysis/batch/${batchId}/export`, {
      params: { format },
      responseType: 'blob',
    });
    return response;
  },

  // Individual analysis exports - using the correct endpoint
  exportAnalysisPDF: async (analysisId: string) => {
    const response = await axiosInstance.get(`/api/v1/export/${analysisId}`, {
      params: { format: 'pdf' },
      responseType: 'blob',
    });
    return response;
  },

  exportAnalysisHTML: async (analysisId: string) => {
    const response = await axiosInstance.get(`/api/v1/export/${analysisId}`, {
      params: { format: 'html' },
      responseType: 'blob',
    });
    return response;
  },

  exportAnalysisMarkdown: async (analysisId: string) => {
    const response = await axiosInstance.get(`/api/v1/export/${analysisId}`, {
      params: { format: 'markdown' },
      responseType: 'blob',
    });
    return response;
  },

  // Billing endpoints
  getSubscription: async () => {
    const response = await axiosInstance.get('/api/v1/billing/subscription');
    return response;
  },

  getInvoices: async () => {
    const response = await axiosInstance.get('/api/v1/billing/invoices');
    return response;
  },

  createCheckoutSession: async (data: {
    plan: string;
    success_url: string;
    cancel_url: string;
  }) => {
    const response = await axiosInstance.post('/api/v1/billing/checkout-session', data);
    return response;
  },

  updateSubscription: async (data: { plan: string }) => {
    const response = await axiosInstance.put('/api/v1/billing/subscription', data);
    return response;
  },

  cancelSubscription: async () => {
    const response = await axiosInstance.delete('/api/v1/billing/subscription');
    return response;
  },

  // Admin endpoints
  getAdminDashboard: async () => {
    const response = await axiosInstance.get('/api/v1/admin/dashboard');
    return response;
  },

  getAdminUsers: async (params?: { page?: number; page_size?: number; search?: string }) => {
    const response = await axiosInstance.get('/api/v1/admin/users', { params });
    return response;
  },

  getAdminUser: async (userId: string) => {
    const response = await axiosInstance.get(`/api/v1/admin/users/${userId}`);
    return response;
  },

  updateAdminUser: async (userId: string, data: Record<string, unknown>) => {
    const response = await axiosInstance.put(`/api/v1/admin/users/${userId}`, data);
    return response;
  },

  deleteAdminUser: async (userId: string) => {
    const response = await axiosInstance.delete(`/api/v1/admin/users/${userId}`);
    return response;
  },

  getAdminRevenue: async (params?: { start_date?: string; end_date?: string }) => {
    const response = await axiosInstance.get('/api/v1/admin/revenue', { params });
    return response;
  },

  getAdminContactMessages: async (params?: {
    status?: string;
    page?: number;
    page_size?: number;
  }) => {
    const response = await axiosInstance.get('/api/v1/admin/support', { params });
    return response;
  },

  updateContactMessageStatus: async (messageId: string, status: string) => {
    const response = await axiosInstance.put(`/api/v1/admin/support/${messageId}`, { status });
    return response;
  },

  // Trial management endpoints
  grantTrial: async (data: { email: string; days?: number; tier?: string }) => {
    const response = await axiosInstance.post('/api/v1/admin/trial/grant', data);
    return response;
  },

  removeTrial: async (email: string) => {
    const response = await axiosInstance.delete(
      `/api/v1/admin/trial/remove?email=${encodeURIComponent(email)}`
    );
    return response;
  },

  extendTrial: async (userId: string, data: { additional_days: number }) => {
    const response = await axiosInstance.post(`/api/v1/admin/users/${userId}/extend-trial`, {
      days: data.additional_days,
    });
    return response;
  },

  changeTrial: async (email: string, data: { tier: string }) => {
    const response = await axiosInstance.put('/api/v1/admin/trial/change-tier', {
      email,
      tier: data.tier,
    });
    return response;
  },

  revokeTrial: async (userId: string) => {
    const response = await axiosInstance.delete(`/api/v1/admin/trial/revoke/${userId}`);
    return response;
  },

  // Admin authentication endpoints
  adminLogin: async (data: { email: string; password: string; admin_secret: string }) => {
    const response = await axiosInstance.post<AuthTokens>('/api/v1/admin/auth/login', data);
    return response;
  },

  adminProfile: async () => {
    const response = await axiosInstance.get('/api/v1/admin/auth/profile');
    return response;
  },

  getAdminStats: async () => {
    const response = await axiosInstance.get('/api/v1/admin/dashboard');
    return response;
  },

  getContactMessages: async () => {
    const response = await axiosInstance.get('/api/v1/admin/support-messages');
    return response;
  },

  respondToContactMessage: async (
    messageId: string,
    data: { response: string; status: string }
  ) => {
    const response = await axiosInstance.post(
      `/api/v1/admin/support-messages/${messageId}/reply`,
      data
    );
    return response;
  },

  // PR Analysis endpoints (Scale+ only)
  analyzePRs: async (data: {
    github_username: string;
    context: 'startup' | 'enterprise' | 'agency' | 'open_source';
    force_refresh?: boolean;
  }) => {
    const response = await axiosInstance.post('/api/v1/pr/analyze', data, {
      timeout: 600000, // 10 minutes for PR analysis
    });
    return response;
  },

  getPRAnalysis: async (id: string) => {
    const response = await axiosInstance.get(`/api/v1/pr/${id}`);
    return response;
  },

  getPRAnalyses: async (params?: { limit?: number; offset?: number }) => {
    const response = await axiosInstance.get('/api/v1/pr/', { params });
    return response;
  },

  getPRAnalysisUsage: async () => {
    const response = await axiosInstance.get('/api/v1/pr/usage');
    return response;
  },

  // Portfolio Analysis endpoints (All paid tiers)
  analyzePortfolio: async (data: {
    github_username: string;
    context: 'startup' | 'enterprise' | 'agency' | 'open_source';
    role: 'junior' | 'mid' | 'senior';
    force_refresh?: boolean;
    max_repos?: number;
  }) => {
    const response = await axiosInstance.post('/api/v1/portfolio/analyze', data, {
      timeout: 600000, // 10 minutes for portfolio analysis
    });
    return response;
  },

  getPortfolioAnalysis: async (id: string) => {
    const response = await axiosInstance.get(`/api/v1/portfolio/${id}`);
    return response;
  },

  getPortfolioAnalyses: async (params?: { skip?: number; limit?: number }) => {
    const response = await axiosInstance.get('/api/v1/portfolio/', { params });
    return response;
  },

  getPortfolioUsage: async () => {
    const response = await axiosInstance.get('/api/v1/portfolio/usage');
    return response;
  },

  // Candidate Hub endpoints
  getCandidateHub: async (username: string) => {
    const response = await axiosInstance.get(`/api/v1/candidate-hub/${username}`);
    return response;
  },

  // Dashboard endpoints
  getDashboardCandidates: async (params?: { limit?: number }) => {
    const response = await axiosInstance.get('/api/v1/dashboard/candidates', { params });
    return response;
  },

  // AI Quota endpoint (FREE tier)
  getAIQuotaStatus: async () => {
    const response = await axiosInstance.get('/api/v1/ai-quota');
    return response;
  },
};
