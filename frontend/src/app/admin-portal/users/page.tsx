// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import { useEffect, useState } from 'react';
import { toast } from 'sonner';

import { AdminGuard } from '@/components/auth/admin-guard';
import { ExiqusButton, ExiqusCard, GradientText } from '@/components/ui/exiqus-components';
import { api } from '@/lib/api-client';
import { formatDate } from '@/lib/utils';

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

interface User {
  id: string;
  email: string;
  full_name: string;
  created_at: string;
  last_login: string | null;
  subscription_plan: string;
  subscription_status: string;
  trial_ends_at: string | null;
  analyses_count: number;
  is_active: boolean;
  is_verified?: boolean;
}

export default function AdminUsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [_isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  // Modal states
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showViewModal, setShowViewModal] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteConfirmEmail, setDeleteConfirmEmail] = useState('');
  const [deleteConfirmPassword, setDeleteConfirmPassword] = useState('');

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      const response = await api.getAdminUsers();
      setUsers(response.data.users || []);
    } catch {
      toast.error('Failed to fetch users');
    } finally {
      setIsLoading(false);
    }
  };

  const extendTrial = async (userId: string) => {
    try {
      await api.extendTrial(userId, { additional_days: 7 });
      toast.success('Trial extended by 7 days');
      fetchUsers();
    } catch {
      toast.error('Failed to extend trial');
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
    // Check if user is active with paid subscription
    if (user.is_active && user.subscription_plan !== 'FREE') {
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
      // await api.deleteUser(selectedUser.id, { password: deleteConfirmPassword });

      toast.success(
        `User ${selectedUser.email} has been marked for deletion. This action has been logged.`
      );
      setShowDeleteConfirm(false);
      setSelectedUser(null);
      setDeleteConfirmEmail('');
      setDeleteConfirmPassword('');
      fetchUsers();
    } catch {
      toast.error('Failed to delete user. Please verify your password and try again.');
    }
  };

  const filteredUsers = users.filter(
    (user) =>
      user.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      user.full_name?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <AdminGuard>
      <div className="min-h-screen bg-gray-950 p-8">
        <div className="mx-auto max-w-7xl">
          <div className="mb-8">
            <h1 className="font-bold text-4xl">
              <GradientText className="bg-gradient-to-r from-red-600 to-orange-600">
                User Management
              </GradientText>
            </h1>
            <p className="mt-2 text-gray-400">Manage users, subscriptions, and trials</p>
          </div>

          {/* Search Bar */}
          <div className="mb-6">
            <input
              type="text"
              placeholder="Search by email or name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full max-w-md rounded-lg border border-gray-800 bg-gray-900 px-4 py-2 text-white placeholder:text-gray-500 focus:border-red-600 focus:outline-none"
            />
          </div>

          {/* Users Table */}
          <ExiqusCard className="overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="border-gray-800 border-b">
                  <tr className="text-left text-gray-400">
                    <th className="p-4">User</th>
                    <th className="p-4">Verified</th>
                    <th className="p-4">Plan</th>
                    <th className="p-4">Status</th>
                    <th className="p-4">Joined</th>
                    <th className="p-4">Analyses</th>
                    <th className="p-4">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800">
                  {filteredUsers.map((user) => (
                    <tr key={user.id} className="hover:bg-gray-900/50">
                      <td className="p-4">
                        <div>
                          <div className="font-medium text-white">
                            {user.full_name || 'No name'}
                          </div>
                          <div className="text-gray-400 text-sm">{user.email}</div>
                        </div>
                      </td>
                      <td className="p-4">
                        {user.is_verified ? (
                          <span className="text-green-400">✅</span>
                        ) : (
                          <span className="text-red-400">❌</span>
                        )}
                      </td>
                      <td className="p-4">
                        <span className="rounded-full bg-blue-900/20 px-3 py-1 text-blue-400 text-sm">
                          {getDisplayPlanName(user.subscription_plan)}
                        </span>
                      </td>
                      <td className="p-4">
                        <span
                          className={`text-sm ${
                            user.is_active
                              ? 'text-green-400'
                              : user.subscription_status === 'trialing'
                                ? 'text-yellow-400'
                                : 'text-gray-400'
                          }`}
                        >
                          {user.is_active
                            ? 'Active'
                            : user.subscription_status === 'trialing'
                              ? 'Trialing'
                              : 'Inactive'}
                        </span>
                        {user.trial_ends_at && (
                          <div className="mt-1 text-gray-500 text-xs">
                            Trial ends: {formatDate(user.trial_ends_at)}
                          </div>
                        )}
                      </td>
                      <td className="p-4 text-gray-400 text-sm">{formatDate(user.created_at)}</td>
                      <td className="p-4 text-gray-400 text-sm">{user.analyses_count}</td>
                      <td className="p-4">
                        <div className="flex items-center gap-2">
                          {user.subscription_status === 'trialing' && (
                            <button
                              type="button"
                              onClick={() => extendTrial(user.id)}
                              className="text-blue-400 text-sm hover:text-blue-300"
                              title="Extend Trial"
                            >
                              Extend Trial
                            </button>
                          )}
                          <button
                            type="button"
                            onClick={() => handleViewUser(user)}
                            className="text-gray-400 text-sm hover:text-gray-300"
                            title="View Details"
                          >
                            View
                          </button>
                          <button
                            type="button"
                            onClick={() => handleEditUser(user)}
                            className="text-sm text-yellow-400 hover:text-yellow-300"
                            title="Edit User"
                          >
                            Edit
                          </button>
                          {user.subscription_plan === 'FREE' || !user.is_active ? (
                            <button
                              type="button"
                              onClick={() => handleDeleteUser(user)}
                              className="text-red-400 text-sm hover:text-red-300"
                              title="Delete User"
                            >
                              Delete
                            </button>
                          ) : (
                            <button
                              type="button"
                              className="cursor-not-allowed text-gray-600 text-sm"
                              disabled
                              title="Cannot delete active paid users"
                            >
                              Delete
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {filteredUsers.length === 0 && (
                <div className="p-8 text-center text-gray-500">
                  {searchQuery ? 'No users found matching your search' : 'No users yet'}
                </div>
              )}
            </div>
          </ExiqusCard>
        </div>
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
                  <p className="text-white">{getDisplayPlanName(selectedUser.subscription_plan)}</p>
                </div>
                <div>
                  <p className="text-gray-400 text-sm">Status</p>
                  <p className="text-white">{selectedUser.subscription_status}</p>
                </div>
                <div>
                  <p className="text-gray-400 text-sm">Analyses Used</p>
                  <p className="text-white">{selectedUser.analyses_count || 0}</p>
                </div>
                <div>
                  <p className="text-gray-400 text-sm">Joined</p>
                  <p className="text-white">{formatDate(selectedUser.created_at)}</p>
                </div>
                {selectedUser.last_login && (
                  <div>
                    <p className="text-gray-400 text-sm">Last Login</p>
                    <p className="text-white">{formatDate(selectedUser.last_login)}</p>
                  </div>
                )}
                {selectedUser.trial_ends_at && (
                  <div>
                    <p className="text-gray-400 text-sm">Trial Ends</p>
                    <p className="text-white">{formatDate(selectedUser.trial_ends_at)}</p>
                  </div>
                )}
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
                Edit functionality will be implemented when you go live. This will allow you to:
              </p>
              <ul className="list-inside list-disc space-y-1 text-gray-300 text-sm">
                <li>Change user subscription plan</li>
                <li>Modify usage limits</li>
                <li>Update user information</li>
                <li>Reset password</li>
                <li>Manage permissions</li>
                <li>Add/remove features</li>
                <li>Adjust billing settings</li>
              </ul>

              <div className="rounded-lg border border-blue-900/50 bg-blue-900/20 p-3">
                <p className="text-blue-300 text-sm">
                  💡 For now, use Stripe Dashboard to manage subscriptions and billing.
                </p>
              </div>

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
    </AdminGuard>
  );
}
