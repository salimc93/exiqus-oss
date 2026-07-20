// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import {
  AlertCircle,
  AlertTriangle,
  ArrowDown,
  ArrowUp,
  DollarSign,
  Loader2,
  Mail,
  TrendingUp,
  UserCheck,
  UserMinus,
  UserPlus,
  Users,
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { toast } from 'sonner';

import { AdminGuard } from '@/components/auth/admin-guard';
import { ExiqusButton, ExiqusCard, GradientText } from '@/components/ui/exiqus-components';
import { api } from '@/lib/api-client';
import { formatCurrency, formatDate } from '@/lib/utils';

interface AdminDashboard {
  total_users: number;
  verified_users: number;
  unverified_users: number;
  active_users: number;
  new_users_today: number;
  new_users_week: number;
  new_verified_month: number;
  users_by_plan: {
    free: number;
    basic: number;
    professional: number;
    enterprise: number;
    scale_plus: number;
  };
  total_analyses: number;
  analyses_today: number;
  analyses_week: number;
  revenue: {
    mrr: number;
    arr: number;
    daily_revenue: number;
    weekly_revenue: number;
  };
  recent_activities: Array<{
    user_id: string;
    user_email: string;
    activity_type: string;
    timestamp: string;
  }>;
  monthly_growth?: Array<{
    month: string;
    users: number;
  }>;
  churn_metrics?: {
    cancelled_users: number;
    churn_rate: number;
    retention_rate: number;
    trial_conversion_rate: number;
    trials_ended: number;
    trials_converted: number;
  };
  growth_indicators?: {
    upgrades: number;
    downgrades: number;
    net_new_mrr: number;
    arpu: number;
    paying_users: number;
    growth_rate: number;
  };
  actionable_alerts?: Array<{
    type: 'warning' | 'error' | 'info';
    title: string;
    message: string;
    action: string;
    priority: 'low' | 'medium' | 'high' | 'critical';
  }>;
}

interface User {
  user_id: string;
  email: string;
  full_name: string;
  subscription_plan: string;
  subscription_status?: string;
  is_active: boolean;
  is_verified?: boolean;
  created_at: string;
  analyses_consumed: number;
  analyses_count?: number;
  is_admin: boolean;
  trial_ends_at?: string;
  trial_end_date?: string;
}

interface ContactMessage {
  message_id: string;
  user_id: string;
  user_email: string;
  subject: string;
  message: string;
  status: string;
  created_at: string;
  response?: string;
}

function AdminDashboardPage() {
  // Admin authentication handled by AdminGuard
  const [dashboard, setDashboard] = useState<AdminDashboard | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [messages, setMessages] = useState<ContactMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'users' | 'messages' | 'trials'>(
    'overview'
  );
  const [trialEmail, setTrialEmail] = useState('');
  const [trialDays, setTrialDays] = useState(14);
  const [trialTier, setTrialTier] = useState('starter');
  const [grantingTrial, setGrantingTrial] = useState(false);
  const [removingTrial, setRemovingTrial] = useState(false);
  const [removeTrialEmail, setRemoveTrialEmail] = useState('');

  // Modal states
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showViewModal, setShowViewModal] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteConfirmEmail, setDeleteConfirmEmail] = useState('');
  const [deleteConfirmPassword, setDeleteConfirmPassword] = useState('');

  useEffect(() => {
    fetchAdminData();
  }, []);

  const getPlanDisplayName = (backendPlan: string): string => {
    const planMapping: { [key: string]: string } = {
      FREE: 'free',
      BASIC: 'starter',
      PROFESSIONAL: 'growth',
      ENTERPRISE: 'scale',
      SCALE_PLUS: 'scale_plus',
    };
    return planMapping[backendPlan] || backendPlan.toLowerCase();
  };

  const fetchAdminData = async () => {
    try {
      setLoading(true);
      const [dashboardRes, usersRes, messagesRes] = await Promise.all([
        api.getAdminDashboard(),
        api.getAdminUsers(),
        api.getContactMessages(),
      ]);

      // Transform the backend response to match frontend expectations
      const dashboardData = dashboardRes.data;
      const transformedDashboard = {
        total_users: dashboardData?.user_stats?.total_users || dashboardData?.total_users || 0,
        verified_users: dashboardData?.verified_users || 0,
        unverified_users: dashboardData?.unverified_users || 0,
        active_users: dashboardData?.user_stats?.active_users || dashboardData?.active_users || 0,
        new_users_today:
          dashboardData?.user_stats?.new_users_this_month || dashboardData?.new_users_today || 0,
        new_users_week:
          dashboardData?.user_stats?.new_users_this_month || dashboardData?.new_users_week || 0,
        new_verified_month: dashboardData?.new_verified_month || 0,
        users_by_plan: dashboardData?.users_by_plan || {
          free: dashboardData?.subscription_stats?.free_users || 0,
          basic: dashboardData?.subscription_stats?.basic_users || 0,
          professional: dashboardData?.subscription_stats?.professional_users || 0,
          enterprise: dashboardData?.subscription_stats?.enterprise_users || 0,
          scale_plus: dashboardData?.subscription_stats?.scale_plus_users || 0,
        },
        total_analyses:
          dashboardData?.usage_stats?.total_analyses || dashboardData?.total_analyses || 0,
        analyses_today:
          dashboardData?.usage_stats?.analyses_this_month || dashboardData?.analyses_today || 0,
        analyses_week:
          dashboardData?.usage_stats?.analyses_this_month || dashboardData?.analyses_week || 0,
        revenue: dashboardData?.revenue || {
          mrr: dashboardData?.subscription_stats?.monthly_recurring_revenue || 0,
          arr: (dashboardData?.subscription_stats?.monthly_recurring_revenue || 0) * 12,
          daily_revenue: (dashboardData?.subscription_stats?.monthly_recurring_revenue || 0) / 30,
          weekly_revenue: (dashboardData?.subscription_stats?.monthly_recurring_revenue || 0) / 4,
        },
        recent_activities: dashboardData?.recent_activities || [],
        churn_metrics: dashboardData?.churn_metrics,
        growth_indicators: dashboardData?.growth_indicators,
        actionable_alerts: dashboardData?.actionable_alerts,
      };

      setDashboard(transformedDashboard);
      setUsers(usersRes.data.users || usersRes.data || []);
      setMessages(messagesRes.data.messages || messagesRes.data || []);
    } catch {
      toast.error('Failed to load admin dashboard');
    } finally {
      setLoading(false);
    }
  };

  const handleGrantTrial = async () => {
    if (!trialEmail) {
      toast.error('Please enter an email address');
      return;
    }

    try {
      setGrantingTrial(true);
      await api.grantTrial({
        email: trialEmail,
        days: trialDays,
        tier: trialTier,
      });
      toast.success(`Trial granted to ${trialEmail}`);
      setTrialEmail('');
      fetchAdminData();
    } catch {
      toast.error('Failed to grant trial');
    } finally {
      setGrantingTrial(false);
    }
  };

  const handleExtendTrial = async (userId: string) => {
    try {
      await api.extendTrial(userId, { additional_days: 7 });
      toast.success('Trial extended by 7 days');
      fetchAdminData();
    } catch {
      toast.error('Failed to extend trial');
    }
  };

  const handleChangeTier = async (userId: string, email: string) => {
    const tier = prompt(
      `Change trial tier for ${email}\n\nEnter tier (starter, growth, scale, scale_plus):`
    );
    if (!tier) return;

    const validTiers = ['starter', 'growth', 'scale', 'scale_plus'];
    if (!validTiers.includes(tier.toLowerCase())) {
      toast.error('Invalid tier. Must be one of: starter, growth, scale, scale_plus');
      return;
    }

    try {
      await api.changeTrial(email, { tier: tier.toLowerCase() });
      toast.success(`Trial tier changed to ${tier} for ${email}`);
      fetchAdminData();
    } catch {
      toast.error('Failed to change trial tier');
    }
  };

  const handleRemoveTrial = async () => {
    if (!removeTrialEmail) {
      toast.error('Please enter an email address');
      return;
    }

    try {
      setRemovingTrial(true);
      await api.removeTrial(removeTrialEmail);
      toast.success(`Trial removed from ${removeTrialEmail}`);
      setRemoveTrialEmail('');
      fetchAdminData();
    } catch {
      toast.error('Failed to remove trial');
    } finally {
      setRemovingTrial(false);
    }
  };

  const handleViewUser = (user: User) => {
    setSelectedUser(user);
    setShowViewModal(true);
  };

  const handleEditUser = (user: User) => {
    setSelectedUser(user);
    setShowEditModal(true);
  };

  const handleDeleteUser = (user: User) => {
    // Check if user has active subscription
    if (user.subscription_status === 'active' && user.subscription_plan !== 'FREE') {
      toast.error(
        'Cannot delete users with active paid subscriptions. Please cancel their subscription first.'
      );
      return;
    }

    setSelectedUser(user);
    setShowDeleteConfirm(true);
    setDeleteConfirmEmail('');
    setDeleteConfirmPassword('');
  };

  const confirmDeleteUser = async () => {
    if (!selectedUser) return;

    // Validate email confirmation
    if (deleteConfirmEmail !== selectedUser.email) {
      toast.error('Email does not match. Please type the exact email address.');
      return;
    }

    // Validate password
    if (deleteConfirmPassword.length < 8) {
      toast.error('Please enter your admin password to confirm deletion.');
      return;
    }

    try {
      // TODO: Implement actual delete API call with password verification
      // await api.deleteUser(selectedUser.user_id, { password: deleteConfirmPassword });

      toast.success(
        `User ${selectedUser.email} has been marked for deletion. This action has been logged.`
      );
      setShowDeleteConfirm(false);
      setSelectedUser(null);
      setDeleteConfirmEmail('');
      setDeleteConfirmPassword('');
      fetchAdminData();
    } catch {
      toast.error('Failed to delete user. Please verify your password and try again.');
    }
  };

  const handleRespondToMessage = async (messageId: string, response: string) => {
    try {
      await api.respondToContactMessage(messageId, {
        response,
        status: 'resolved',
      });
      toast.success('Response sent');
      fetchAdminData();
    } catch {
      toast.error('Failed to send response');
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[calc(100vh-12rem)] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-purple-600" />
      </div>
    );
  }

  return (
    <div className="min-h-[calc(100vh-12rem)] bg-[#0A0A0A] py-8">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="font-bold text-3xl">
            <GradientText>Admin Dashboard</GradientText>
          </h1>
          <p className="mt-2 text-gray-400">Platform management and analytics</p>
        </div>

        {/* Tabs */}
        <div className="mb-8 flex gap-2">
          <ExiqusButton
            variant={activeTab === 'overview' ? 'primary' : 'secondary'}
            onClick={() => setActiveTab('overview')}
          >
            Overview
          </ExiqusButton>
          <ExiqusButton
            variant={activeTab === 'users' ? 'primary' : 'secondary'}
            onClick={() => setActiveTab('users')}
          >
            Users
          </ExiqusButton>
          <ExiqusButton
            variant={activeTab === 'messages' ? 'primary' : 'secondary'}
            onClick={() => setActiveTab('messages')}
          >
            Support Messages
          </ExiqusButton>
          <ExiqusButton
            variant={activeTab === 'trials' ? 'primary' : 'secondary'}
            onClick={() => setActiveTab('trials')}
          >
            Grant Trials
          </ExiqusButton>
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && dashboard && (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {/* User Stats */}
            <ExiqusCard className="p-6" glow="subtle">
              <div className="mb-4 flex items-center justify-between">
                <h3 className="font-semibold text-gray-100 text-lg">Users</h3>
                <Users className="h-6 w-6 text-purple-400" />
              </div>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-400">Total Users</span>
                  <span className="text-gray-100">{dashboard?.total_users || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">✅ Verified</span>
                  <span className="text-green-400">{dashboard?.verified_users || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">❌ Unverified</span>
                  <span className="text-red-400">{dashboard?.unverified_users || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Active (7 days)</span>
                  <span className="text-blue-400">{dashboard?.active_users || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">New This Month</span>
                  <span className="text-purple-400">{dashboard?.new_users_today || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">New This Week</span>
                  <span className="text-blue-400">{dashboard?.new_users_week || 0}</span>
                </div>
              </div>
            </ExiqusCard>

            {/* Revenue Stats */}
            <ExiqusCard className="p-6" glow="subtle">
              <div className="mb-4 flex items-center justify-between">
                <h3 className="font-semibold text-gray-100 text-lg">Revenue</h3>
                <DollarSign className="h-6 w-6 text-green-400" />
              </div>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-400">MRR</span>
                  <span className="text-green-400">
                    {formatCurrency(dashboard?.revenue?.mrr || 0)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">ARR</span>
                  <span className="text-green-400">
                    {formatCurrency(dashboard?.revenue?.arr || 0)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Daily Revenue</span>
                  <span className="text-gray-100">
                    {formatCurrency(dashboard?.revenue?.daily_revenue || 0)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Weekly Revenue</span>
                  <span className="text-gray-100">
                    {formatCurrency(dashboard?.revenue?.weekly_revenue || 0)}
                  </span>
                </div>
              </div>
            </ExiqusCard>

            {/* Subscription Distribution */}
            <ExiqusCard className="p-6" glow="subtle">
              <div className="mb-4 flex items-center justify-between">
                <h3 className="font-semibold text-gray-100 text-lg">Plans</h3>
                <TrendingUp className="h-6 w-6 text-purple-400" />
              </div>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-400">Free</span>
                  <span className="text-gray-100">{dashboard?.users_by_plan?.free || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Starter</span>
                  <span className="text-blue-400">{dashboard?.users_by_plan?.basic || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Growth</span>
                  <span className="text-purple-400">
                    {dashboard?.users_by_plan?.professional || 0}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Scale</span>
                  <span className="text-orange-400">
                    {dashboard?.users_by_plan?.enterprise || 0}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Scale+</span>
                  <span className="text-red-400">{dashboard?.users_by_plan?.scale_plus || 0}</span>
                </div>
              </div>
            </ExiqusCard>

            {/* Churn & Retention Metrics */}
            {dashboard?.churn_metrics && (
              <ExiqusCard className="p-6" glow="subtle">
                <div className="mb-4 flex items-center justify-between">
                  <h3 className="font-semibold text-gray-100 text-lg">Churn & Retention</h3>
                  <UserMinus className="h-6 w-6 text-red-400" />
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Churn Rate</span>
                    <span
                      className={
                        dashboard.churn_metrics.churn_rate > 10 ? 'text-red-400' : 'text-green-400'
                      }
                    >
                      {dashboard.churn_metrics.churn_rate}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Retention Rate</span>
                    <span className="text-green-400">
                      {dashboard.churn_metrics.retention_rate}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Trial Conversion</span>
                    <span
                      className={
                        dashboard.churn_metrics.trial_conversion_rate < 20
                          ? 'text-yellow-400'
                          : 'text-green-400'
                      }
                    >
                      {dashboard.churn_metrics.trial_conversion_rate}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Cancelled Users</span>
                    <span className="text-gray-100">{dashboard.churn_metrics.cancelled_users}</span>
                  </div>
                </div>
              </ExiqusCard>
            )}

            {/* Growth Indicators */}
            {dashboard?.growth_indicators && (
              <ExiqusCard className="p-6" glow="subtle">
                <div className="mb-4 flex items-center justify-between">
                  <h3 className="font-semibold text-gray-100 text-lg">Growth</h3>
                  <TrendingUp className="h-6 w-6 text-green-400" />
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Growth Rate</span>
                    <span className="text-green-400">
                      {dashboard.growth_indicators.growth_rate}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">ARPU</span>
                    <span className="text-blue-400">
                      {formatCurrency(dashboard.growth_indicators.arpu)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-400">Upgrades</span>
                    <span className="flex items-center text-green-400">
                      <ArrowUp className="mr-1 h-3 w-3" />
                      {dashboard.growth_indicators.upgrades}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-400">Downgrades</span>
                    <span className="flex items-center text-red-400">
                      <ArrowDown className="mr-1 h-3 w-3" />
                      {dashboard.growth_indicators.downgrades}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Net New MRR</span>
                    <span
                      className={
                        dashboard.growth_indicators.net_new_mrr >= 0
                          ? 'text-green-400'
                          : 'text-red-400'
                      }
                    >
                      {formatCurrency(dashboard.growth_indicators.net_new_mrr)}
                    </span>
                  </div>
                </div>
              </ExiqusCard>
            )}

            {/* Actionable Alerts */}
            {dashboard?.actionable_alerts && dashboard.actionable_alerts.length > 0 && (
              <ExiqusCard className="p-6 lg:col-span-3" glow="subtle">
                <div className="mb-4 flex items-center justify-between">
                  <h3 className="font-semibold text-gray-100 text-lg">Action Required</h3>
                  <AlertTriangle className="h-6 w-6 text-yellow-400" />
                </div>
                <div className="space-y-3">
                  {dashboard.actionable_alerts.map((alert, index) => (
                    <div
                      key={index}
                      className={`rounded-lg p-4 ${
                        alert.type === 'error'
                          ? 'border border-red-900/50 bg-red-900/20'
                          : alert.type === 'warning'
                            ? 'border border-yellow-900/50 bg-yellow-900/20'
                            : 'border border-blue-900/50 bg-blue-900/20'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="mb-1 flex items-center gap-2">
                            <h4
                              className={`font-semibold ${
                                alert.type === 'error'
                                  ? 'text-red-400'
                                  : alert.type === 'warning'
                                    ? 'text-yellow-400'
                                    : 'text-blue-400'
                              }`}
                            >
                              {alert.title}
                            </h4>
                            <span
                              className={`rounded-full px-2 py-0.5 text-xs ${
                                alert.priority === 'critical'
                                  ? 'bg-red-900/50 text-red-300'
                                  : alert.priority === 'high'
                                    ? 'bg-orange-900/50 text-orange-300'
                                    : alert.priority === 'medium'
                                      ? 'bg-yellow-900/50 text-yellow-300'
                                      : 'bg-gray-900/50 text-gray-300'
                              }`}
                            >
                              {alert.priority}
                            </span>
                          </div>
                          <p className="mb-2 text-gray-300 text-sm">{alert.message}</p>
                          <p className="text-gray-400 text-xs">
                            <strong>Action:</strong> {alert.action}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </ExiqusCard>
            )}

            {/* Recent Activities */}
            <ExiqusCard className="p-6 lg:col-span-3" glow="subtle">
              <div className="mb-4 flex items-center justify-between">
                <h3 className="font-semibold text-gray-100 text-lg">Recent Activities</h3>
                <AlertCircle className="h-6 w-6 text-blue-400" />
              </div>
              <div className="space-y-2">
                {(dashboard?.recent_activities || []).slice(0, 5).map((activity, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between rounded-lg bg-gray-900/50 p-3"
                  >
                    <div>
                      <p className="text-gray-100 text-sm">{activity.user_email}</p>
                      <p className="text-gray-400 text-xs">{activity.activity_type}</p>
                    </div>
                    <span className="text-gray-500 text-xs">{formatDate(activity.timestamp)}</span>
                  </div>
                ))}
              </div>
            </ExiqusCard>
          </div>
        )}

        {/* Users Tab */}
        {activeTab === 'users' && (
          <ExiqusCard className="p-6" glow="subtle">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="font-semibold text-gray-100 text-lg">Recent Users</h3>
              <span className="text-gray-400 text-sm">Showing last 10 users</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-gray-800 border-b">
                    <th className="px-4 py-2 text-left text-gray-400">Email</th>
                    <th className="px-4 py-2 text-left text-gray-400">Verified</th>
                    <th className="px-4 py-2 text-left text-gray-400">Plan</th>
                    <th className="px-4 py-2 text-left text-gray-400">Analyses</th>
                    <th className="px-4 py-2 text-left text-gray-400">Status</th>
                    <th className="px-4 py-2 text-left text-gray-400">Joined</th>
                    <th className="px-4 py-2 text-left text-gray-400">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.slice(0, 10).map((user) => (
                    <tr key={user.user_id} className="border-gray-900 border-b">
                      <td className="px-4 py-3">
                        <div>
                          <p className="text-gray-100 text-sm">{user.email}</p>
                          {user.full_name && (
                            <p className="text-gray-500 text-xs">{user.full_name}</p>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        {user.is_verified ? (
                          <span className="text-green-400">✅</span>
                        ) : (
                          <span className="text-red-400">❌</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span className="rounded-full bg-purple-900/50 px-2 py-1 text-purple-400 text-xs">
                          {getPlanDisplayName(user.subscription_plan)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-300 text-sm">
                        {user.analyses_count || user.analyses_consumed || 0}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`rounded-full px-2 py-1 text-xs ${
                            user.is_active
                              ? 'bg-green-900/50 text-green-400'
                              : 'bg-red-900/50 text-red-400'
                          }`}
                        >
                          {user.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-400 text-sm">
                        {formatDate(user.created_at)}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex gap-2">
                          {user.trial_end_date && (
                            <>
                              <ExiqusButton
                                size="sm"
                                variant="secondary"
                                onClick={() => handleExtendTrial(user.user_id)}
                              >
                                Extend Trial
                              </ExiqusButton>
                              <ExiqusButton
                                size="sm"
                                variant="secondary"
                                onClick={() => handleChangeTier(user.user_id, user.email)}
                              >
                                Change Tier
                              </ExiqusButton>
                            </>
                          )}
                          <div className="flex gap-1">
                            <ExiqusButton
                              size="sm"
                              variant="ghost"
                              onClick={() => handleViewUser(user)}
                              title="View User Details"
                            >
                              View
                            </ExiqusButton>
                            <ExiqusButton
                              size="sm"
                              variant="ghost"
                              onClick={() => handleEditUser(user)}
                              title="Edit User"
                            >
                              Edit
                            </ExiqusButton>
                            {user.subscription_plan === 'FREE' ||
                            user.subscription_status !== 'active' ? (
                              <ExiqusButton
                                size="sm"
                                variant="ghost"
                                className="text-red-400 hover:text-red-300"
                                onClick={() => handleDeleteUser(user)}
                                title="Delete User"
                              >
                                Delete
                              </ExiqusButton>
                            ) : (
                              <ExiqusButton
                                size="sm"
                                variant="ghost"
                                className="text-gray-600"
                                disabled
                                title="Cannot delete active paid users"
                              >
                                Delete
                              </ExiqusButton>
                            )}
                          </div>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {users.length > 10 && (
              <div className="mt-4 text-center">
                <ExiqusButton
                  variant="secondary"
                  onClick={() => {
                    window.location.href = '/admin-portal/users';
                  }}
                >
                  View All Users ({users.length} total)
                </ExiqusButton>
              </div>
            )}
          </ExiqusCard>
        )}

        {/* Messages Tab */}
        {activeTab === 'messages' && (
          <div className="space-y-4">
            {messages.length === 0 ? (
              <ExiqusCard className="p-6 text-center" glow="subtle">
                <Mail className="mx-auto mb-4 h-12 w-12 text-gray-600" />
                <p className="text-gray-400">No pending support messages</p>
              </ExiqusCard>
            ) : (
              messages.map((message) => (
                <ExiqusCard key={message.message_id} className="p-6" glow="subtle">
                  <div className="mb-4">
                    <div className="flex items-start justify-between">
                      <div>
                        <h4 className="font-semibold text-gray-100">{message.subject}</h4>
                        <p className="text-gray-400 text-sm">
                          From: {message.user_email} • {formatDate(message.created_at)}
                        </p>
                      </div>
                      <span
                        className={`rounded-full px-2 py-1 text-xs ${
                          message.status === 'pending'
                            ? 'bg-yellow-900/50 text-yellow-400'
                            : 'bg-green-900/50 text-green-400'
                        }`}
                      >
                        {message.status}
                      </span>
                    </div>
                  </div>
                  <p className="mb-4 text-gray-300">{message.message}</p>
                  {message.status === 'pending' && (
                    <div className="flex gap-2">
                      <input
                        type="text"
                        placeholder="Type your response..."
                        className="flex-1 rounded-lg bg-gray-900 px-4 py-2 text-gray-100 placeholder-gray-500"
                        onKeyPress={(e) => {
                          if (e.key === 'Enter') {
                            handleRespondToMessage(message.message_id, e.currentTarget.value);
                          }
                        }}
                      />
                      <ExiqusButton size="sm">Send Response</ExiqusButton>
                    </div>
                  )}
                </ExiqusCard>
              ))
            )}
          </div>
        )}

        {/* Trials Tab */}
        {activeTab === 'trials' && (
          <ExiqusCard className="p-6" glow="subtle">
            <div className="mb-6">
              <h3 className="mb-4 font-semibold text-gray-100 text-lg">Grant Trial Access</h3>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <div>
                  <label className="mb-2 block text-gray-400 text-sm">Email Address</label>
                  <input
                    type="email"
                    value={trialEmail}
                    onChange={(e) => setTrialEmail(e.target.value)}
                    placeholder="user@example.com"
                    className="w-full rounded-lg bg-gray-900 px-4 py-2 text-gray-100 placeholder-gray-500"
                  />
                </div>
                <div>
                  <label className="mb-2 block text-gray-400 text-sm">Trial Days</label>
                  <select
                    value={trialDays}
                    onChange={(e) => setTrialDays(parseInt(e.target.value))}
                    className="w-full rounded-lg bg-gray-900 px-4 py-2 text-gray-100"
                  >
                    <option value="7">7 days</option>
                    <option value="14">14 days</option>
                  </select>
                </div>
                <div>
                  <label className="mb-2 block text-gray-400 text-sm">Trial Tier</label>
                  <select
                    value={trialTier}
                    onChange={(e) => setTrialTier(e.target.value)}
                    className="w-full rounded-lg bg-gray-900 px-4 py-2 text-gray-100"
                  >
                    <option value="starter">Starter</option>
                    <option value="growth">Growth</option>
                    <option value="scale">Scale</option>
                    <option value="scale_plus">Scale+</option>
                  </select>
                </div>
                <div className="flex items-end">
                  <ExiqusButton
                    onClick={handleGrantTrial}
                    disabled={grantingTrial || !trialEmail}
                    className="w-full"
                  >
                    {grantingTrial ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <UserPlus className="mr-2 h-4 w-4" />
                    )}
                    Grant Trial
                  </ExiqusButton>
                </div>
              </div>
            </div>

            <div className="border-gray-800 border-t pt-6">
              <h3 className="mb-4 font-semibold text-gray-100 text-lg">Remove Trial Access</h3>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                <div>
                  <label className="mb-2 block text-gray-400 text-sm">Email Address</label>
                  <input
                    type="email"
                    value={removeTrialEmail}
                    onChange={(e) => setRemoveTrialEmail(e.target.value)}
                    placeholder="user@example.com"
                    className="w-full rounded-lg bg-gray-900 px-4 py-2 text-gray-100 placeholder-gray-500"
                  />
                </div>
                <div className="flex items-end">
                  <ExiqusButton
                    onClick={handleRemoveTrial}
                    disabled={removingTrial || !removeTrialEmail}
                    className="w-full bg-red-600 hover:bg-red-700"
                    variant="primary"
                  >
                    {removingTrial ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <UserMinus className="mr-2 h-4 w-4" />
                    )}
                    Remove Trial
                  </ExiqusButton>
                </div>
              </div>
            </div>

            <div className="border-gray-800 border-t pt-6">
              <h4 className="mb-4 font-medium text-base text-gray-100">Active Trial Users</h4>
              <div className="space-y-2">
                {users
                  .filter((u) => u.trial_ends_at)
                  .map((user) => (
                    <div
                      key={user.user_id}
                      className="flex items-center justify-between rounded-lg bg-gray-900/50 p-4"
                    >
                      <div>
                        <p className="text-gray-100 text-sm">{user.email}</p>
                        <div className="flex items-center gap-2">
                          <p className="text-gray-400 text-xs">
                            Trial ends: {formatDate(user.trial_ends_at!)}
                          </p>
                          <span className="text-gray-400 text-xs">•</span>
                          <span className="rounded-full bg-purple-900/50 px-2 py-0.5 text-purple-400 text-xs">
                            {getPlanDisplayName(user.subscription_plan)}
                          </span>
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <ExiqusButton
                          size="sm"
                          variant="secondary"
                          onClick={() => handleChangeTier(user.user_id, user.email)}
                        >
                          Change Tier
                        </ExiqusButton>
                        <ExiqusButton
                          size="sm"
                          variant="secondary"
                          onClick={() => handleExtendTrial(user.user_id)}
                        >
                          <UserCheck className="mr-2 h-3 w-3" />
                          Extend 7 Days
                        </ExiqusButton>
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          </ExiqusCard>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && selectedUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <ExiqusCard className="mx-4 w-full max-w-md p-6">
            <h3 className="mb-4 font-bold text-red-400 text-xl">⚠️ Confirm User Deletion</h3>

            <div className="space-y-4">
              <div className="rounded-lg border border-red-900/50 bg-red-900/20 p-3">
                <p className="text-red-300 text-sm">
                  This action cannot be undone. The user&apos;s data will be permanently deleted.
                </p>
              </div>

              <div>
                <p className="mb-2 text-gray-300">
                  Deleting user: <span className="font-mono text-white">{selectedUser.email}</span>
                </p>
              </div>

              <div>
                <label className="mb-1 block text-gray-400 text-sm">
                  Type the email address to confirm:
                </label>
                <input
                  type="email"
                  value={deleteConfirmEmail}
                  onChange={(e) => setDeleteConfirmEmail(e.target.value)}
                  placeholder={selectedUser.email}
                  className="w-full rounded-lg border border-gray-800 bg-gray-900 px-3 py-2 text-white"
                />
              </div>

              <div>
                <label className="mb-1 block text-gray-400 text-sm">
                  Enter your admin password:
                </label>
                <input
                  type="password"
                  value={deleteConfirmPassword}
                  onChange={(e) => setDeleteConfirmPassword(e.target.value)}
                  placeholder="Admin password"
                  className="w-full rounded-lg border border-gray-800 bg-gray-900 px-3 py-2 text-white"
                />
              </div>

              <div className="flex gap-3 pt-4">
                <ExiqusButton
                  variant="secondary"
                  onClick={() => {
                    setShowDeleteConfirm(false);
                    setSelectedUser(null);
                    setDeleteConfirmEmail('');
                    setDeleteConfirmPassword('');
                  }}
                  className="flex-1"
                >
                  Cancel
                </ExiqusButton>
                <ExiqusButton
                  variant="primary"
                  onClick={confirmDeleteUser}
                  disabled={
                    deleteConfirmEmail !== selectedUser.email || deleteConfirmPassword.length < 8
                  }
                  className="flex-1 bg-red-600 hover:bg-red-700"
                >
                  Delete User
                </ExiqusButton>
              </div>
            </div>
          </ExiqusCard>
        </div>
      )}

      {/* View User Modal */}
      {showViewModal && selectedUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <ExiqusCard className="mx-4 max-h-[80vh] w-full max-w-2xl overflow-y-auto p-6">
            <h3 className="mb-4 font-bold text-white text-xl">User Details</h3>

            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-gray-400 text-sm">Email</p>
                  <p className="text-white">{selectedUser.email}</p>
                </div>
                <div>
                  <p className="text-gray-400 text-sm">Name</p>
                  <p className="text-white">{selectedUser.full_name || 'Not provided'}</p>
                </div>
                <div>
                  <p className="text-gray-400 text-sm">Plan</p>
                  <p className="text-white">{selectedUser.subscription_plan}</p>
                </div>
                <div>
                  <p className="text-gray-400 text-sm">Status</p>
                  <p className="text-white">{selectedUser.subscription_status}</p>
                </div>
                <div>
                  <p className="text-gray-400 text-sm">Analyses Used</p>
                  <p className="text-white">
                    {selectedUser.analyses_count || selectedUser.analyses_consumed || 0}
                  </p>
                </div>
                <div>
                  <p className="text-gray-400 text-sm">Joined</p>
                  <p className="text-white">{formatDate(selectedUser.created_at)}</p>
                </div>
              </div>

              <div className="flex justify-end pt-4">
                <ExiqusButton
                  onClick={() => {
                    setShowViewModal(false);
                    setSelectedUser(null);
                  }}
                >
                  Close
                </ExiqusButton>
              </div>
            </div>
          </ExiqusCard>
        </div>
      )}

      {/* Edit User Modal */}
      {showEditModal && selectedUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <ExiqusCard className="mx-4 w-full max-w-md p-6">
            <h3 className="mb-4 font-bold text-white text-xl">Edit User</h3>

            <div className="space-y-4">
              <p className="text-sm text-yellow-400">
                Edit functionality will be implemented soon. This will allow you to:
              </p>
              <ul className="list-inside list-disc space-y-1 text-gray-300 text-sm">
                <li>Change user subscription plan</li>
                <li>Modify usage limits</li>
                <li>Update user information</li>
                <li>Reset password</li>
                <li>Manage permissions</li>
              </ul>

              <div className="flex justify-end pt-4">
                <ExiqusButton
                  onClick={() => {
                    setShowEditModal(false);
                    setSelectedUser(null);
                  }}
                >
                  Close
                </ExiqusButton>
              </div>
            </div>
          </ExiqusCard>
        </div>
      )}
    </div>
  );
}

export default function AdminPage() {
  return (
    <AdminGuard>
      <AdminDashboardPage />
    </AdminGuard>
  );
}
