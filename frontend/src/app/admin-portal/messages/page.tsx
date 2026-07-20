// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import {
  AlertCircle,
  AlertTriangle,
  CheckCircle,
  ChevronRight,
  Clock,
  Mail,
  MessageSquare,
  Search,
  Shield,
  User,
  X,
  Zap,
} from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';

import { AdminGuard } from '@/components/auth/admin-guard';
import { Badge } from '@/components/ui/badge';
import { ExiqusButton, ExiqusCard, GradientText } from '@/components/ui/exiqus-components';
import { formatDate } from '@/lib/utils';

interface SupportMessage {
  id: string;
  user_email: string;
  user_name: string;
  subject: string;
  message: string;
  status: 'UNREAD' | 'READ' | 'RESPONDED' | 'unread' | 'read' | 'responded';
  created_at: string;
  updated_at: string | null;
  is_priority: boolean;
  priority_level: number;
  target_response_hours: number;
  user_plan: string | null;
  admin_response: string | null;
  responded_at: string | null;
  responded_by: string | null;
}

export default function AdminMessagesPage() {
  const [messages, setMessages] = useState<SupportMessage[]>([]);
  const [filteredMessages, setFilteredMessages] = useState<SupportMessage[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedMessage, setSelectedMessage] = useState<SupportMessage | null>(null);
  const [replyText, setReplyText] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [priorityFilter, setPriorityFilter] = useState<string>('all');
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchMessages();
    // Auto-refresh every 30 seconds to check for new priority messages
    const interval = setInterval(fetchMessages, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    // Filter messages based on search and filters
    let filtered = messages;

    if (searchTerm) {
      filtered = filtered.filter(
        (msg) =>
          msg.subject.toLowerCase().includes(searchTerm.toLowerCase()) ||
          msg.message.toLowerCase().includes(searchTerm.toLowerCase()) ||
          msg.user_email.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    if (statusFilter !== 'all') {
      filtered = filtered.filter((msg) => msg.status === statusFilter);
    }

    if (priorityFilter === 'priority') {
      filtered = filtered.filter((msg) => msg.is_priority);
    } else if (priorityFilter === 'standard') {
      filtered = filtered.filter((msg) => !msg.is_priority);
    }

    setFilteredMessages(filtered);
  }, [messages, searchTerm, statusFilter, priorityFilter]);

  useEffect(() => {
    // Check for priority messages that need attention
    const urgentMessages = messages.filter(
      (msg) =>
        msg.is_priority &&
        msg.status !== 'RESPONDED' &&
        msg.status !== 'responded' && // Check both cases
        getTimeUntilSLA(msg) !== null &&
        getTimeUntilSLA(msg)! < 2 // Less than 2 hours until SLA breach
    );

    if (urgentMessages.length > 0) {
      toast.error(`⚠️ ${urgentMessages.length} priority message(s) approaching SLA deadline!`, {
        duration: 10000,
      });
    }
  }, [messages]);

  // Click outside to close modal
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (modalRef.current && !modalRef.current.contains(event.target as Node)) {
        setSelectedMessage(null);
        setReplyText('');
      }
    };

    if (selectedMessage) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [selectedMessage]);

  const fetchMessages = async () => {
    try {
      const adminToken = localStorage.getItem('adminToken');
      const API_URL = process.env.NEXT_PUBLIC_API_URL || '';
      const response = await fetch(`${API_URL}/api/v1/admin/support-messages`, {
        headers: {
          Authorization: `Bearer ${adminToken}`,
        },
      });

      if (response.ok) {
        const data = await response.json();

        // Debug logging for production - using console.warn for ESLint compliance
        if (process.env.NODE_ENV === 'development') {
          console.warn('[Messages Debug] Fetched messages:', data.messages?.length || 0);
          if (data.messages?.length > 0) {
            console.warn('[Messages Debug] Sample message data:', {
              user_plan: data.messages[0].user_plan,
              is_priority: data.messages[0].is_priority,
              priority_level: data.messages[0].priority_level,
              target_response_hours: data.messages[0].target_response_hours,
            });
            // Log a Scale+ message specifically if found
            const scalePlusMessage = data.messages.find(
              (msg: SupportMessage) => msg.user_plan === 'scale_plus'
            );
            if (scalePlusMessage) {
              console.warn('[Messages Debug] Scale+ message found:', {
                subject: scalePlusMessage.subject,
                user_plan: scalePlusMessage.user_plan,
                is_priority: scalePlusMessage.is_priority,
                priority_level: scalePlusMessage.priority_level,
              });
            }
          }
        }

        setMessages(data.messages);
      } else {
        toast.error('Failed to fetch messages');
      }
    } catch {
      toast.error('Error loading messages');
    } finally {
      setIsLoading(false);
    }
  };

  const updateMessageStatus = async (messageId: string, status: string) => {
    try {
      const adminToken = localStorage.getItem('adminToken');
      const API_URL = process.env.NEXT_PUBLIC_API_URL || '';
      const response = await fetch(`${API_URL}/api/v1/admin/support-messages/${messageId}`, {
        method: 'PATCH',
        headers: {
          Authorization: `Bearer ${adminToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ status }),
      });

      if (response.ok) {
        toast.success(`Message marked as ${status.toLowerCase()}`);
        fetchMessages();
      } else {
        toast.error('Failed to update message status');
      }
    } catch {
      toast.error('Error updating message');
    }
  };

  const sendReply = async (messageId: string) => {
    if (!replyText.trim()) return;

    try {
      const adminToken = localStorage.getItem('adminToken');
      const API_URL = process.env.NEXT_PUBLIC_API_URL || '';
      const response = await fetch(`${API_URL}/api/v1/admin/support-messages/${messageId}/reply`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${adminToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ reply: replyText }),
      });

      if (response.ok) {
        toast.success('Reply sent successfully');
        setReplyText('');
        setSelectedMessage(null);
        fetchMessages();
      } else {
        toast.error('Failed to send reply');
      }
    } catch {
      toast.error('Error sending reply');
    }
  };

  const getTimeUntilSLA = (message: SupportMessage) => {
    if (!message.is_priority) return null;
    // Don't show SLA for responded messages
    if (message.status === 'RESPONDED' || message.status === 'responded') return null;

    const created = new Date(message.created_at);
    const now = new Date();
    const hoursPassed = (now.getTime() - created.getTime()) / (1000 * 60 * 60);
    const hoursRemaining = message.target_response_hours - hoursPassed;

    return hoursRemaining;
  };

  const getSLABadge = (message: SupportMessage) => {
    const hoursRemaining = getTimeUntilSLA(message);
    if (hoursRemaining === null) return null;

    if (hoursRemaining < 0) {
      return <Badge className="bg-red-600 text-white">SLA BREACHED</Badge>;
    } else if (hoursRemaining < 1) {
      return (
        <Badge className="animate-pulse bg-orange-600 text-white">
          SLA: {Math.floor(hoursRemaining * 60)}m left
        </Badge>
      );
    } else if (hoursRemaining < 2) {
      return (
        <Badge className="bg-yellow-600 text-white">SLA: {hoursRemaining.toFixed(1)}h left</Badge>
      );
    } else {
      return (
        <Badge className="bg-green-600 text-white">SLA: {Math.floor(hoursRemaining)}h left</Badge>
      );
    }
  };

  const getPriorityIcon = (message: SupportMessage) => {
    if (!message.is_priority) return null;

    if (message.priority_level >= 3) {
      return <Zap className="h-4 w-4 text-red-500" />;
    } else if (message.priority_level >= 2) {
      return <AlertTriangle className="h-4 w-4 text-orange-500" />;
    } else {
      return <Shield className="h-4 w-4 text-yellow-500" />;
    }
  };

  const getPriorityLabel = (message: SupportMessage) => {
    // Backend sends: 'scale_plus' for Scale+, 'enterprise' for Scale, 'growth' for Growth
    const isScalePlus = message.user_plan === 'scale_plus';
    const isScale = message.user_plan === 'enterprise' || message.user_plan === 'scale';
    const isProfessional = message.user_plan === 'growth' || message.user_plan === 'professional';

    // Show priority label if user has a priority plan OR if message is marked as priority
    if (isScalePlus || (message.is_priority && message.priority_level >= 3)) {
      return (
        <Badge className="animate-pulse bg-red-100 text-red-800">
          🚨 URGENT - Scale+ (4hr SLA)
        </Badge>
      );
    } else if (isScale || (message.is_priority && message.priority_level >= 2)) {
      return <Badge className="bg-orange-100 text-orange-800">HIGH - Scale (8hr SLA)</Badge>;
    } else if (isProfessional || (message.is_priority && message.priority_level >= 1)) {
      return <Badge className="bg-yellow-100 text-yellow-800">MEDIUM - Growth (24hr SLA)</Badge>;
    } else if (message.is_priority) {
      return <Badge className="bg-blue-100 text-blue-800">Priority</Badge>;
    }
    return null;
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'RESPONDED':
        return <CheckCircle className="h-4 w-4 text-green-400" />;
      case 'READ':
        return <AlertCircle className="h-4 w-4 text-blue-400" />;
      case 'UNREAD':
        return <Clock className="h-4 w-4 text-yellow-400" />;
      default:
        return null;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toUpperCase()) {
      case 'RESPONDED':
        return 'bg-green-600 text-white font-semibold';
      case 'READ':
        return 'bg-blue-600 text-white';
      case 'UNREAD':
        return 'bg-yellow-600 text-white';
      default:
        return 'bg-gray-600 text-white';
    }
  };

  // Sort messages: Priority first, then by creation date
  const sortedMessages = [...filteredMessages].sort((a, b) => {
    if (a.is_priority && !b.is_priority) return -1;
    if (!a.is_priority && b.is_priority) return 1;
    if (a.is_priority && b.is_priority) {
      if (a.priority_level > b.priority_level) return -1;
      if (a.priority_level < b.priority_level) return 1;
    }
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });

  // Count statistics
  const stats = {
    total: messages.length,
    unread: messages.filter((m) => m.status === 'UNREAD' || m.status === 'unread').length,
    priority: messages.filter(
      (m) => m.is_priority && m.status !== 'RESPONDED' && m.status !== 'responded'
    ).length,
    breached: messages.filter((m) => {
      const hours = getTimeUntilSLA(m);
      return hours !== null && hours < 0;
    }).length,
  };

  return (
    <AdminGuard>
      <div className="min-h-screen bg-[#0A0A0A] p-4">
        <div className="mx-auto max-w-7xl">
          {/* Header with Stats */}
          <div className="mb-6">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <MessageSquare className="h-8 w-8 text-red-600" />
                <h1 className="font-bold text-3xl">
                  <GradientText>Support Messages</GradientText>
                </h1>
              </div>
              <div className="flex gap-2">
                {stats.breached > 0 && (
                  <Badge className="animate-pulse bg-red-600 text-white">
                    {stats.breached} SLA BREACHED
                  </Badge>
                )}
                {stats.priority > 0 && (
                  <Badge className="bg-orange-600 text-white">
                    {stats.priority} Priority Pending
                  </Badge>
                )}
                <Badge className="bg-blue-600 text-white">{stats.unread} Unread</Badge>
                <Badge className="bg-gray-600 text-white">{stats.total} Total</Badge>
              </div>
            </div>

            {/* Filters */}
            <div className="mb-4 flex gap-4">
              <div className="relative flex-1">
                <Search className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 transform text-gray-400" />
                <input
                  type="text"
                  placeholder="Search messages..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full rounded-lg border border-gray-800 bg-gray-900 py-2 pr-4 pl-10 text-white placeholder:text-gray-500 focus:border-red-600 focus:outline-none"
                />
              </div>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="rounded-lg border border-gray-800 bg-gray-900 px-4 py-2 text-white focus:border-red-600 focus:outline-none"
              >
                <option value="all">All Status</option>
                <option value="UNREAD">Unread</option>
                <option value="READ">Read</option>
                <option value="RESPONDED">Responded</option>
              </select>
              <select
                value={priorityFilter}
                onChange={(e) => setPriorityFilter(e.target.value)}
                className="rounded-lg border border-gray-800 bg-gray-900 px-4 py-2 text-white focus:border-red-600 focus:outline-none"
              >
                <option value="all">All Messages</option>
                <option value="priority">Priority Only</option>
                <option value="standard">Standard Only</option>
              </select>
            </div>
          </div>

          {/* Messages List */}
          <div className="space-y-4">
            {isLoading ? (
              <ExiqusCard>
                <div className="p-8 text-center text-gray-500">Loading messages...</div>
              </ExiqusCard>
            ) : sortedMessages.length === 0 ? (
              <ExiqusCard>
                <div className="p-8 text-center text-gray-500">
                  {searchTerm || statusFilter !== 'all' || priorityFilter !== 'all'
                    ? 'No messages match your filters'
                    : 'No messages yet'}
                </div>
              </ExiqusCard>
            ) : (
              sortedMessages.map((message) => {
                const isScalePlus =
                  message.user_plan === 'scale_plus' || message.user_plan === 'Scale+';
                const isScale = message.user_plan === 'scale' || message.user_plan === 'Scale';
                const isProfessional =
                  message.user_plan === 'professional' ||
                  message.user_plan === 'growth' ||
                  message.user_plan === 'Growth';

                return (
                  <ExiqusCard
                    key={message.id}
                    className={`cursor-pointer transition-all hover:scale-[1.01] ${
                      isScalePlus &&
                      message.status !== 'RESPONDED' &&
                      message.status !== 'responded'
                        ? 'animate-pulse border-red-600 bg-red-900/20 ring-2 ring-red-600/50'
                        : isScale &&
                            message.status !== 'RESPONDED' &&
                            message.status !== 'responded'
                          ? 'border-orange-600 bg-orange-900/15'
                          : isProfessional &&
                              message.status !== 'RESPONDED' &&
                              message.status !== 'responded'
                            ? 'border-yellow-600/50 bg-yellow-900/10'
                            : message.is_priority &&
                                message.status !== 'RESPONDED' &&
                                message.status !== 'responded'
                              ? 'border-orange-600/50 bg-orange-900/10'
                              : message.status === 'RESPONDED' || message.status === 'responded'
                                ? 'border-green-600/30 bg-green-900/5'
                                : ''
                    }`}
                    onClick={() => setSelectedMessage(message)}
                  >
                    <div className="p-6">
                      <div className="mb-3 flex items-start justify-between">
                        <div className="flex-1">
                          <div className="mb-2 flex items-center gap-2">
                            {getPriorityIcon(message)}
                            <h3 className="font-semibold text-lg text-white">{message.subject}</h3>
                            {getPriorityLabel(message)}
                            {getSLABadge(message)}
                          </div>
                          <div className="flex items-center gap-4 text-gray-400 text-sm">
                            <span className="flex items-center gap-1">
                              <User className="h-3 w-3" />
                              {message.user_name}
                            </span>
                            <span>{message.user_email}</span>
                            <span className="flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              {formatDate(message.created_at)}
                            </span>
                          </div>
                        </div>
                        <Badge className={getStatusColor(message.status)}>
                          <span className="flex items-center gap-1">
                            {getStatusIcon(message.status)}
                            {message.status}
                          </span>
                        </Badge>
                      </div>
                      <p className="line-clamp-2 text-gray-400">{message.message}</p>
                      {message.admin_response && (
                        <div className="mt-3 rounded-lg border border-green-600/30 bg-green-900/20 p-3">
                          <div className="flex items-start gap-2">
                            <CheckCircle className="mt-0.5 h-4 w-4 flex-shrink-0 text-green-500" />
                            <div className="flex-1">
                              <p className="mb-1 font-semibold text-green-400 text-sm">
                                Support Team
                              </p>
                              <p className="text-gray-300 text-sm">{message.admin_response}</p>
                              <p className="mt-2 text-gray-500 text-xs">
                                {formatDate(message.responded_at!)}
                              </p>
                            </div>
                          </div>
                        </div>
                      )}
                      <div className="mt-3 flex items-center justify-end gap-2">
                        <ChevronRight className="h-4 w-4 text-gray-500" />
                      </div>
                    </div>
                  </ExiqusCard>
                );
              })
            )}
          </div>

          {/* Message Detail Modal */}
          {selectedMessage && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4">
              <div ref={modalRef} className="max-h-[90vh] w-full max-w-3xl overflow-y-auto">
                <ExiqusCard className="p-6">
                  <div className="mb-4 flex items-start justify-between">
                    <div className="flex-1">
                      <div className="mb-2 flex items-center gap-2">
                        {getPriorityIcon(selectedMessage)}
                        <h2 className="font-semibold text-white text-xl">
                          {selectedMessage.subject}
                        </h2>
                        {getPriorityLabel(selectedMessage)}
                        {getSLABadge(selectedMessage)}
                      </div>
                      <div className="flex items-center gap-4 text-gray-400 text-sm">
                        <span className="flex items-center gap-1">
                          <User className="h-3 w-3" />
                          {selectedMessage.user_name}
                        </span>
                        <span>{selectedMessage.user_email}</span>
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {formatDate(selectedMessage.created_at)}
                        </span>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedMessage(null);
                        setReplyText('');
                      }}
                      className="text-gray-400 transition-colors hover:text-white"
                    >
                      <X className="h-6 w-6" />
                    </button>
                  </div>

                  <div className="space-y-4">
                    {/* Message Content */}
                    <div className="rounded-lg bg-gray-900 p-4">
                      <h3 className="mb-2 font-semibold text-gray-300 text-sm">
                        Original Message:
                      </h3>
                      <p className="whitespace-pre-wrap text-gray-100">{selectedMessage.message}</p>
                    </div>

                    {/* Previous Response */}
                    {selectedMessage.admin_response && (
                      <div className="rounded-lg border border-green-600/30 bg-green-900/20 p-4">
                        <div className="flex items-start gap-3">
                          <CheckCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-green-500" />
                          <div className="flex-1">
                            <h3 className="mb-2 font-semibold text-green-400 text-sm">
                              Support Team
                            </h3>
                            <p className="whitespace-pre-wrap text-gray-100">
                              {selectedMessage.admin_response}
                            </p>
                            <p className="mt-2 text-gray-500 text-xs">
                              {formatDate(selectedMessage.responded_at!)}
                            </p>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Quick Actions */}
                    <div className="flex gap-2">
                      {selectedMessage.status === 'UNREAD' && (
                        <ExiqusButton
                          variant="outline"
                          size="sm"
                          onClick={() => updateMessageStatus(selectedMessage.id, 'read')}
                        >
                          Mark as Read
                        </ExiqusButton>
                      )}
                      {selectedMessage.status !== 'RESPONDED' && (
                        <ExiqusButton
                          variant="outline"
                          size="sm"
                          onClick={() => updateMessageStatus(selectedMessage.id, 'responded')}
                        >
                          Mark as Responded
                        </ExiqusButton>
                      )}
                    </div>

                    {/* Reply Section */}
                    <div>
                      <label className="mb-2 block font-medium text-gray-300 text-sm">
                        Send Reply
                      </label>
                      <textarea
                        value={replyText}
                        onChange={(e) => setReplyText(e.target.value)}
                        placeholder="Type your reply..."
                        className="mb-4 h-32 w-full rounded-lg border border-gray-800 bg-gray-900 px-4 py-2 text-white placeholder:text-gray-500 focus:border-red-600 focus:outline-none"
                      />
                      <ExiqusButton
                        onClick={() => sendReply(selectedMessage.id)}
                        disabled={!replyText.trim()}
                      >
                        <Mail className="mr-2 h-4 w-4" />
                        Send Reply
                      </ExiqusButton>
                    </div>
                  </div>
                </ExiqusCard>
              </div>
            </div>
          )}
        </div>
      </div>
    </AdminGuard>
  );
}
