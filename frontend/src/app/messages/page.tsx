// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import {
  AlertCircle,
  Bell,
  CheckCircle,
  Clock,
  Inbox,
  MessageCircle,
  Shield,
  User,
  X,
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ExiqusButton, ExiqusCard, GradientText } from '@/components/ui/exiqus-components';
import { useAuth } from '@/contexts/auth-context';
import { useAuthGuard } from '@/hooks/use-auth-guard';
import { useToast } from '@/hooks/use-toast';
import { api } from '@/lib/api-client';

interface ContactMessage {
  message_id: string;
  name: string;
  email: string;
  subject: string;
  message: string;
  status: 'pending' | 'read' | 'responded';
  created_at: string;
  admin_response?: string;
  responded_at?: string;
  responded_by?: string;
}

export default function MessagesPage() {
  const router = useRouter();
  const { user } = useAuth();
  const { isLoading, showUnauthorized, UnauthorizedComponent } = useAuthGuard();
  const { toast } = useToast();
  const [messages, setMessages] = useState<ContactMessage[]>([]);
  const [_loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [selectedMessage, setSelectedMessage] = useState<ContactMessage | null>(null);
  const [hasNewResponse, setHasNewResponse] = useState(false);

  const fetchMessages = useCallback(async () => {
    if (!user) return;

    try {
      setLoading(true);
      const response = await api.getMyMessages({ page });
      setMessages(response.data.messages);
      setTotalPages(response.data.total_pages);

      // Check if any messages have responses user hasn't seen
      const hasResponses = response.data.messages.some(
        (msg: ContactMessage) => msg.status === 'responded' && msg.admin_response
      );
      setHasNewResponse(hasResponses);
    } catch (error) {
      // Check if it's an auth error
      const axiosError = error as { response?: { status?: number; data?: { detail?: string } } };
      if (axiosError?.response?.status === 401) {
        toast({
          title: 'Session Expired',
          description: 'Please login again to view your messages.',
          variant: 'destructive',
        });
      } else if (user) {
        toast({
          title: 'Error',
          description:
            axiosError?.response?.data?.detail || 'Failed to load your messages. Please try again.',
          variant: 'destructive',
        });
      }
    } finally {
      setLoading(false);
    }
  }, [page, toast, user]);

  useEffect(() => {
    if (user) {
      fetchMessages();
    }
  }, [user, page, fetchMessages]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'read':
        return 'bg-blue-100 text-blue-800';
      case 'responded':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pending':
        return <Clock className="h-4 w-4" />;
      case 'read':
        return <AlertCircle className="h-4 w-4" />;
      case 'responded':
        return <CheckCircle className="h-4 w-4" />;
      default:
        return null;
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // Handle loading state
  if (isLoading) {
    return (
      <div className="flex min-h-[calc(100vh-12rem)] items-center justify-center bg-[#0A0A0A]">
        <div className="text-center">
          <div className="mb-4 inline-flex h-16 w-16 items-center justify-center">
            <div className="h-12 w-12 animate-spin rounded-full border-4 border-purple-600 border-t-transparent" />
          </div>
          <p className="text-gray-400">Loading your messages...</p>
        </div>
      </div>
    );
  }

  // Handle unauthorized state
  if (showUnauthorized && UnauthorizedComponent) {
    return <UnauthorizedComponent />;
  }

  return (
    <div className="min-h-[calc(100vh-12rem)] bg-[#0A0A0A]">
      {/* Subtle gradient overlay */}
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-purple-900/10 via-transparent to-blue-900/10"></div>

      <div className="container relative mx-auto px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <MessageCircle className="h-8 w-8 text-purple-400" />
            <h1 className="font-bold text-3xl">
              <GradientText>My Messages</GradientText>
            </h1>
            {hasNewResponse && (
              <Badge className="animate-pulse bg-green-600 text-white">
                <Bell className="mr-1 h-3 w-3" />
                New Response
              </Badge>
            )}
          </div>
          <ExiqusButton onClick={() => router.push('/contact')}>New Message</ExiqusButton>
        </div>

        {messages.length === 0 ? (
          <ExiqusCard className="py-12 text-center" glow="subtle">
            <MessageCircle className="mx-auto mb-4 h-16 w-16 text-purple-400" />
            <p className="text-gray-100 text-lg">No messages yet</p>
            <p className="mt-2 text-gray-400">Contact us if you need any assistance!</p>
            <ExiqusButton className="mt-4" onClick={() => router.push('/contact')}>
              Send a Message
            </ExiqusButton>
          </ExiqusCard>
        ) : (
          <div className="space-y-4">
            {messages.map((message) => (
              <ExiqusCard
                key={message.message_id}
                className={`cursor-pointer p-6 transition-all hover:scale-[1.01] ${
                  message.admin_response ? 'border-green-600/30 bg-green-900/5' : ''
                }`}
                onClick={() => setSelectedMessage(message)}
                glow="hover"
              >
                <div className="mb-4 flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-gray-100 text-lg">{message.subject}</h3>
                      {message.admin_response && (
                        <Badge className="border-green-600/30 bg-green-600/20 text-green-400">
                          <Inbox className="mr-1 h-3 w-3" />
                          Response Available
                        </Badge>
                      )}
                    </div>
                    <p className="mt-1 text-gray-400 text-sm">
                      Sent on {formatDate(message.created_at)}
                    </p>
                  </div>
                  <Badge className={`${getStatusColor(message.status)} flex items-center gap-1`}>
                    {getStatusIcon(message.status)}
                    {message.status}
                  </Badge>
                </div>
                <p className="line-clamp-2 text-gray-400">{message.message}</p>
                {message.admin_response && (
                  <div className="mt-4 rounded-lg border border-white/[0.06] bg-white/[0.03] p-3">
                    <p className="mb-1 font-semibold text-gray-300 text-sm">Admin Response:</p>
                    <p className="line-clamp-2 text-gray-400 text-sm">{message.admin_response}</p>
                  </div>
                )}
              </ExiqusCard>
            ))}

            {totalPages > 1 && (
              <div className="mt-6 flex justify-center gap-2">
                <Button variant="outline" onClick={() => setPage(page - 1)} disabled={page === 1}>
                  Previous
                </Button>
                <span className="flex items-center px-4">
                  Page {page} of {totalPages}
                </span>
                <Button
                  variant="outline"
                  onClick={() => setPage(page + 1)}
                  disabled={page === totalPages}
                >
                  Next
                </Button>
              </div>
            )}
          </div>
        )}

        {selectedMessage && (
          <MessageDetailModal message={selectedMessage} onClose={() => setSelectedMessage(null)} />
        )}
      </div>
    </div>
  );
}

function MessageDetailModal({
  message,
  onClose,
}: {
  message: ContactMessage;
  onClose: () => void;
}) {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'responded':
        return <CheckCircle className="h-5 w-5 text-green-400" />;
      case 'read':
        return <AlertCircle className="h-5 w-5 text-blue-400" />;
      case 'pending':
        return <Clock className="h-5 w-5 text-yellow-400" />;
      default:
        return null;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4">
      <div className="max-h-[90vh] w-full max-w-3xl overflow-hidden rounded-xl">
        <ExiqusCard className="h-full overflow-hidden" glow="purple">
          {/* Header */}
          <div className="border-white/[0.06] border-b bg-gradient-to-r from-purple-900/20 to-blue-900/20 p-6">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="mb-2 flex items-center gap-3">
                  {getStatusIcon(message.status)}
                  <h2 className="font-bold text-2xl text-gray-100">{message.subject}</h2>
                </div>
                <div className="flex items-center gap-4 text-gray-400 text-sm">
                  <span className="flex items-center gap-1">
                    <MessageCircle className="h-4 w-4" />
                    Conversation Started
                  </span>
                  <span>{formatDate(message.created_at)}</span>
                </div>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="rounded-lg p-2 transition-colors hover:bg-white/10"
              >
                <X className="h-5 w-5 text-gray-400 hover:text-white" />
              </button>
            </div>
          </div>

          {/* Messages Container */}
          <div className="max-h-[calc(90vh-120px)] overflow-y-auto p-6">
            <div className="space-y-6">
              {/* User Message */}
              <div className="flex gap-4">
                <div className="flex-shrink-0">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-purple-600">
                    <User className="h-5 w-5 text-white" />
                  </div>
                </div>
                <div className="flex-1">
                  <div className="rounded-lg border border-purple-600/20 bg-gray-900/50 p-4">
                    <div className="mb-2 flex items-center gap-2">
                      <span className="font-semibold text-purple-400">You</span>
                      <span className="text-gray-500 text-xs">
                        {formatDate(message.created_at)}
                      </span>
                    </div>
                    <p className="whitespace-pre-wrap text-gray-200 leading-relaxed">
                      {message.message}
                    </p>
                  </div>
                </div>
              </div>

              {/* Admin Response */}
              {message.admin_response ? (
                <div className="flex gap-4">
                  <div className="flex-shrink-0">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-red-600 to-purple-600">
                      <Shield className="h-5 w-5 text-white" />
                    </div>
                  </div>
                  <div className="flex-1">
                    <div className="rounded-lg border border-blue-600/30 bg-gradient-to-br from-blue-900/30 to-purple-900/30 p-4">
                      <div className="mb-2 flex items-center gap-2">
                        <span className="font-semibold text-blue-400">Support Team</span>
                        <Badge className="bg-blue-600/20 text-blue-400 text-xs">Admin</Badge>
                        <span className="text-gray-500 text-xs">
                          {message.responded_at ? formatDate(message.responded_at) : ''}
                        </span>
                      </div>
                      <p className="whitespace-pre-wrap text-gray-200 leading-relaxed">
                        {message.admin_response}
                      </p>
                      {message.responded_by && (
                        <p className="mt-3 text-gray-500 text-xs italic">
                          — {message.responded_by}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex gap-4">
                  <div className="flex-shrink-0">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gray-800">
                      <Clock className="h-5 w-5 text-gray-500" />
                    </div>
                  </div>
                  <div className="flex-1">
                    <div className="rounded-lg border border-gray-800 bg-gray-900/30 p-4 text-center">
                      <p className="text-gray-500 italic">Awaiting response from support team...</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </ExiqusCard>
      </div>
    </div>
  );
}
