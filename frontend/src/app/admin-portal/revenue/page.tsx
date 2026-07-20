// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import { ArrowDown, ArrowUp, CreditCard, DollarSign, TrendingUp, Users } from 'lucide-react';
import { useEffect, useState } from 'react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { toast } from 'sonner';

import { AdminGuard } from '@/components/auth/admin-guard';
import { ExiqusCard, GradientText } from '@/components/ui/exiqus-components';
import { formatCurrency, formatDate } from '@/lib/utils';

// Convert backend plan names to display names
const getDisplayPlanName = (backendPlan: string): string => {
  const planMapping: Record<string, string> = {
    free: 'Free',
    basic: 'Starter',
    starter: 'Starter',
    professional: 'Growth',
    enterprise: 'Scale',
    scale_plus: 'Scale+',
  };
  return planMapping[backendPlan.toLowerCase()] || backendPlan;
};

interface RevenueData {
  metrics: {
    mrr: number;
    arr: number;
    total_revenue: number;
    active_subscriptions: number;
    churn_rate: number;
    average_revenue_per_user: number;
  };
  growth: {
    mrr_growth: number;
    user_growth: number;
    revenue_growth: number;
  };
  subscriptions_by_plan: {
    free: number;
    basic: number;
    professional: number;
    enterprise: number;
    scale_plus: number;
  };
  recent_transactions: Array<{
    id: string;
    user_email: string;
    plan: string;
    amount: number;
    type: 'subscription' | 'upgrade' | 'downgrade' | 'cancellation';
    created_at: string;
  }>;
  monthly_revenue: Array<{
    month: string;
    revenue: number;
    subscriptions: number;
  }>;
}

export default function AdminRevenuePage() {
  const [revenueData, setRevenueData] = useState<RevenueData | null>(null);
  const [_isLoading, setIsLoading] = useState(true);
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d' | '1y'>('30d');

  useEffect(() => {
    fetchRevenueData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timeRange]);

  const fetchRevenueData = async () => {
    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || '';
      const adminToken = localStorage.getItem('adminToken');
      const response = await fetch(`${API_URL}/api/v1/admin/revenue?range=${timeRange}`, {
        headers: {
          Authorization: `Bearer ${adminToken}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setRevenueData(data);
      } else {
        toast.error('Failed to fetch revenue data');
      }
    } catch {
      toast.error('Error loading revenue data');
    } finally {
      setIsLoading(false);
    }
  };

  if (!revenueData) {
    return (
      <AdminGuard>
        <div className="min-h-screen bg-gray-950 p-8">
          <div className="flex h-64 items-center justify-center">
            <div className="text-gray-500">Loading revenue data...</div>
          </div>
        </div>
      </AdminGuard>
    );
  }

  return (
    <AdminGuard>
      <div className="min-h-screen bg-gray-950 p-8">
        <div className="mx-auto max-w-7xl">
          <div className="mb-8 flex items-center justify-between">
            <div>
              <h1 className="font-bold text-4xl">
                <GradientText className="bg-gradient-to-r from-red-600 to-orange-600">
                  Revenue Analytics
                </GradientText>
              </h1>
              <p className="mt-2 text-gray-400">Track revenue, growth, and subscription metrics</p>
            </div>

            {/* Time Range Selector */}
            <div className="flex gap-2">
              {(['7d', '30d', '90d', '1y'] as const).map((range) => (
                <button
                  type="button"
                  key={range}
                  onClick={() => setTimeRange(range)}
                  className={`rounded-lg px-4 py-2 text-sm transition-colors ${
                    timeRange === range
                      ? 'bg-red-600 text-white'
                      : 'bg-gray-900 text-gray-400 hover:bg-gray-800'
                  }`}
                >
                  {range === '7d'
                    ? '7 Days'
                    : range === '30d'
                      ? '30 Days'
                      : range === '90d'
                        ? '90 Days'
                        : '1 Year'}
                </button>
              ))}
            </div>
          </div>

          {/* Key Metrics */}
          <div className="mb-8 grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            <ExiqusCard>
              <div className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-400 text-sm">Monthly Recurring Revenue</p>
                    <p className="mt-2 font-bold text-3xl text-white">
                      {formatCurrency(revenueData.metrics.mrr)}
                    </p>
                    <div className="mt-2 flex items-center gap-1">
                      {revenueData.growth.mrr_growth >= 0 ? (
                        <ArrowUp className="h-4 w-4 text-green-400" />
                      ) : (
                        <ArrowDown className="h-4 w-4 text-red-400" />
                      )}
                      <span
                        className={`text-sm ${
                          revenueData.growth.mrr_growth >= 0 ? 'text-green-400' : 'text-red-400'
                        }`}
                      >
                        {Math.abs(revenueData.growth.mrr_growth).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                  <DollarSign className="h-8 w-8 text-red-600" />
                </div>
              </div>
            </ExiqusCard>

            <ExiqusCard>
              <div className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-400 text-sm">Annual Recurring Revenue</p>
                    <p className="mt-2 font-bold text-3xl text-white">
                      {formatCurrency(revenueData.metrics.arr)}
                    </p>
                    <p className="mt-2 text-gray-500 text-sm">Projected yearly</p>
                  </div>
                  <TrendingUp className="h-8 w-8 text-green-600" />
                </div>
              </div>
            </ExiqusCard>

            <ExiqusCard>
              <div className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-400 text-sm">Active Subscriptions</p>
                    <p className="mt-2 font-bold text-3xl text-white">
                      {revenueData.metrics.active_subscriptions}
                    </p>
                    <div className="mt-2 flex items-center gap-1">
                      {revenueData.growth.user_growth >= 0 ? (
                        <ArrowUp className="h-4 w-4 text-green-400" />
                      ) : (
                        <ArrowDown className="h-4 w-4 text-red-400" />
                      )}
                      <span
                        className={`text-sm ${
                          revenueData.growth.user_growth >= 0 ? 'text-green-400' : 'text-red-400'
                        }`}
                      >
                        {Math.abs(revenueData.growth.user_growth).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                  <Users className="h-8 w-8 text-blue-600" />
                </div>
              </div>
            </ExiqusCard>

            <ExiqusCard>
              <div className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-400 text-sm">Avg Revenue Per User</p>
                    <p className="mt-2 font-bold text-3xl text-white">
                      {formatCurrency(revenueData.metrics.average_revenue_per_user)}
                    </p>
                    <p className="mt-2 text-gray-500 text-sm">Per month</p>
                  </div>
                  <CreditCard className="h-8 w-8 text-purple-600" />
                </div>
              </div>
            </ExiqusCard>
          </div>

          {/* Subscriptions by Plan */}
          <div className="mb-8 grid gap-6 lg:grid-cols-2">
            <ExiqusCard>
              <div className="p-6">
                <h3 className="mb-4 font-semibold text-lg text-white">Subscriptions by Plan</h3>
                <div className="space-y-3">
                  {Object.entries(revenueData.subscriptions_by_plan).map(([plan, count]) => (
                    <div key={plan} className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="h-2 w-2 rounded-full bg-red-600" />
                        <span className="text-gray-300">{getDisplayPlanName(plan)}</span>
                      </div>
                      <div className="flex items-center gap-4">
                        <span className="font-medium text-white">{count}</span>
                        <span className="text-gray-500 text-sm">
                          ({((count / revenueData.metrics.active_subscriptions) * 100).toFixed(1)}%)
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </ExiqusCard>

            <ExiqusCard>
              <div className="p-6">
                <h3 className="mb-4 font-semibold text-lg text-white">Recent Transactions</h3>
                <div className="max-h-64 space-y-3 overflow-y-auto">
                  {revenueData.recent_transactions.map((transaction) => (
                    <div
                      key={transaction.id}
                      className="flex items-center justify-between border-gray-800 border-b pb-2"
                    >
                      <div>
                        <p className="text-sm text-white">{transaction.user_email}</p>
                        <p className="text-gray-500 text-xs">
                          {transaction.type} - {getDisplayPlanName(transaction.plan)}
                        </p>
                      </div>
                      <div className="text-right">
                        <p
                          className={`font-medium text-sm ${
                            transaction.type === 'cancellation' ? 'text-red-400' : 'text-green-400'
                          }`}
                        >
                          {transaction.type === 'cancellation' ? '-' : '+'}
                          {formatCurrency(transaction.amount)}
                        </p>
                        <p className="text-gray-500 text-xs">
                          {formatDate(transaction.created_at)}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </ExiqusCard>
          </div>

          {/* Monthly Revenue Chart */}
          <ExiqusCard>
            <div className="p-6">
              <h3 className="mb-4 font-semibold text-lg text-white">Monthly Revenue Trend</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={[...revenueData.monthly_revenue].reverse()}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="month" stroke="#9CA3AF" tick={{ fill: '#9CA3AF' }} />
                    <YAxis
                      stroke="#9CA3AF"
                      tick={{ fill: '#9CA3AF' }}
                      tickFormatter={(value) => `$${value}`}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1F2937',
                        border: '1px solid #374151',
                        borderRadius: '8px',
                      }}
                      labelStyle={{ color: '#F3F4F6' }}
                      formatter={(value) => [`$${value ?? 0}`, 'Revenue']}
                    />
                    <Legend wrapperStyle={{ color: '#9CA3AF' }} />
                    <Line
                      type="monotone"
                      dataKey="revenue"
                      stroke="#DC2626"
                      strokeWidth={2}
                      dot={{ fill: '#DC2626', r: 4 }}
                      activeDot={{ r: 6 }}
                      name="Monthly Revenue"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </ExiqusCard>
        </div>
      </div>
    </AdminGuard>
  );
}
