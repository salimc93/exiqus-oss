// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import { FileText, Mail, MessageCircle, MessageSquare, Send, User } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { toast } from 'sonner';

import { ExiqusButton, ExiqusCard, GradientText } from '@/components/ui/exiqus-components';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { useAuth } from '@/contexts/auth-context';
import { api } from '@/lib/api-client';

interface ContactFormData {
  name: string;
  email: string;
  subject: string;
  message: string;
}

export default function ContactPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState<ContactFormData>({
    name: user?.full_name || '',
    email: user?.email || '',
    subject: '',
    message: '',
  });

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.name || !formData.email || !formData.subject || !formData.message) {
      toast.error('Please fill in all fields');
      return;
    }

    setLoading(true);
    try {
      await api.sendContactMessage(formData);

      toast.success(
        user
          ? 'Your message has been sent. You can view it in your messages page.'
          : "Thank you for contacting us. We'll respond to your email within 24-48 hours."
      );

      // Reset form
      setFormData({
        name: user?.full_name || '',
        email: user?.email || '',
        subject: '',
        message: '',
      });

      // Don't auto-redirect, let user choose to go to messages
    } catch (error) {
      console.error('Failed to send message:', error);
      toast.error('Failed to send message. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0A0A0A] text-white">
      <div className="container mx-auto max-w-3xl px-4 py-16">
        <ExiqusCard className="p-8 md:p-12" glow="purple">
          <div className="mb-8 text-center">
            <div className="mb-6 flex justify-center">
              <div className="rounded-xl bg-purple-500/10 p-4">
                <MessageCircle className="h-12 w-12 text-purple-400" />
              </div>
            </div>
            <h1 className="mb-4 font-bold text-3xl md:text-4xl">
              <GradientText>Contact Us</GradientText>
            </h1>
            <p className="text-gray-400 text-lg">
              Have questions about Exiqus? We&apos;d love to hear from you!
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid gap-6 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="name" className="text-gray-300">
                  Name
                </Label>
                <div className="relative">
                  <User className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-gray-500" />
                  <Input
                    id="name"
                    name="name"
                    placeholder="Your name"
                    value={formData.name}
                    onChange={handleInputChange}
                    disabled={loading}
                    className="border-white/[0.09] bg-white/[0.06] pl-10 text-gray-100 placeholder:text-gray-500 focus:border-purple-500/50"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="email" className="text-gray-300">
                  Email
                </Label>
                <div className="relative">
                  <Mail className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-gray-500" />
                  <Input
                    id="email"
                    name="email"
                    type="email"
                    placeholder="your@email.com"
                    value={formData.email}
                    onChange={handleInputChange}
                    disabled={loading}
                    className="border-white/[0.09] bg-white/[0.06] pl-10 text-gray-100 placeholder:text-gray-500 focus:border-purple-500/50"
                  />
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="subject" className="text-gray-300">
                Subject
              </Label>
              <div className="relative">
                <FileText className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-gray-500" />
                <Input
                  id="subject"
                  name="subject"
                  placeholder="What is your message about?"
                  value={formData.subject}
                  onChange={handleInputChange}
                  disabled={loading}
                  className="border-white/[0.09] bg-white/[0.06] pl-10 text-gray-100 placeholder:text-gray-500 focus:border-purple-500/50"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="message" className="text-gray-300">
                Message
              </Label>
              <div className="relative">
                <MessageSquare className="absolute top-3 left-3 h-4 w-4 text-gray-500" />
                <Textarea
                  id="message"
                  name="message"
                  placeholder="Tell us more about your inquiry..."
                  value={formData.message}
                  onChange={handleInputChange}
                  disabled={loading}
                  className="min-h-[150px] resize-none border-white/[0.09] bg-white/[0.06] pl-10 text-gray-100 placeholder:text-gray-500 focus:border-purple-500/50"
                />
              </div>
            </div>

            <div className="pt-4">
              <ExiqusButton type="submit" size="lg" className="w-full gap-2" disabled={loading}>
                {loading ? (
                  <>
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                    Sending...
                  </>
                ) : (
                  <>
                    <Send className="h-4 w-4" />
                    Send Message
                  </>
                )}
              </ExiqusButton>
            </div>
          </form>

          {!user && (
            <div className="mt-8 rounded-lg border border-purple-500/20 bg-purple-500/10 p-6">
              <p className="text-gray-300 text-sm">
                <span className="font-medium text-purple-400">Not logged in:</span> We&apos;ll
                respond to your message via email within 24-48 hours. For a better experience,
                consider{' '}
                <a href="/signup" className="text-purple-400 underline hover:text-purple-300">
                  creating an account
                </a>{' '}
                to track your messages.
              </p>
            </div>
          )}

          {user && (
            <div className="mt-8 text-center">
              <p className="mb-4 text-gray-400 text-sm">
                You can view all your messages and responses in your dashboard.
              </p>
              <ExiqusButton variant="secondary" size="sm" onClick={() => router.push('/messages')}>
                <MessageCircle className="mr-2 h-4 w-4" />
                View My Messages
              </ExiqusButton>
            </div>
          )}
        </ExiqusCard>
      </div>
    </div>
  );
}
