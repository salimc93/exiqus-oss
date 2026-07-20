// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

'use client';

import {
  Archive,
  // Package, // TEMP: Commented out until batch analysis is reimplemented
  BarChart3,
  ChevronDown,
  CreditCard,
  FolderGit2,
  GitBranch,
  GitPullRequest,
  LayoutDashboard,
  LogOut,
  Menu,
  MessageCircle,
  RefreshCw,
  Search,
  Sparkles,
  User,
  Users,
  X,
} from 'lucide-react';
import Image from 'next/image';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import React, { useState } from 'react';

import { ExiqusButton, GradientText } from '@/components/ui/exiqus-components';
import { useAuth } from '@/contexts/auth-context';
import { cn } from '@/lib/utils';

export function Navigation() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [isAnalysisDropdownOpen, setIsAnalysisDropdownOpen] = useState(false);
  const [isDashboardDropdownOpen, setDashboardDropdownOpen] = useState(false);
  const [isHistoryDropdownOpen, setIsHistoryDropdownOpen] = useState(false);
  const [isMobileAnalysisOpen, setIsMobileAnalysisOpen] = useState(false);
  const [isMobileDashboardOpen, setIsMobileDashboardOpen] = useState(false);
  const [isMobileHistoryOpen, setIsMobileHistoryOpen] = useState(false);
  const pathname = usePathname();
  const { user, logout } = useAuth();

  // Timers for dropdown hover delay
  const analysisCloseTimer = React.useRef<NodeJS.Timeout | null>(null);
  const dashboardCloseTimer = React.useRef<NodeJS.Timeout | null>(null);
  const historyCloseTimer = React.useRef<NodeJS.Timeout | null>(null);

  const handleAnalysisMouseEnter = () => {
    if (analysisCloseTimer.current) {
      clearTimeout(analysisCloseTimer.current);
    }
    // Close other dropdowns when opening Analysis
    setIsHistoryDropdownOpen(false);
    setDashboardDropdownOpen(false);
    if (historyCloseTimer.current) {
      clearTimeout(historyCloseTimer.current);
    }
    if (dashboardCloseTimer.current) {
      clearTimeout(dashboardCloseTimer.current);
    }
    setIsAnalysisDropdownOpen(true);
  };

  const handleAnalysisMouseLeave = () => {
    analysisCloseTimer.current = setTimeout(() => {
      setIsAnalysisDropdownOpen(false);
    }, 300); // 300ms delay before closing
  };

  const handleDashboardMouseEnter = () => {
    if (dashboardCloseTimer.current) {
      clearTimeout(dashboardCloseTimer.current);
    }
    // Close other dropdowns
    setIsAnalysisDropdownOpen(false);
    setIsHistoryDropdownOpen(false);
    if (analysisCloseTimer.current) {
      clearTimeout(analysisCloseTimer.current);
    }
    if (historyCloseTimer.current) {
      clearTimeout(historyCloseTimer.current);
    }
    setDashboardDropdownOpen(true);
  };

  const handleDashboardMouseLeave = () => {
    dashboardCloseTimer.current = setTimeout(() => {
      setDashboardDropdownOpen(false);
    }, 300); // 300ms delay before closing
  };

  const handleHistoryMouseEnter = () => {
    if (historyCloseTimer.current) {
      clearTimeout(historyCloseTimer.current);
    }
    // Close other dropdowns when opening History
    setIsAnalysisDropdownOpen(false);
    setDashboardDropdownOpen(false);
    if (analysisCloseTimer.current) {
      clearTimeout(analysisCloseTimer.current);
    }
    if (dashboardCloseTimer.current) {
      clearTimeout(dashboardCloseTimer.current);
    }
    setIsHistoryDropdownOpen(true);
  };

  const handleHistoryMouseLeave = () => {
    historyCloseTimer.current = setTimeout(() => {
      setIsHistoryDropdownOpen(false);
    }, 300); // 300ms delay before closing
  };

  const navigation = [
    { name: 'Home', href: '/' },
    { name: 'Pricing', href: '/pricing' },
    { name: 'Contact', href: '/contact' },
  ].filter((item) => {
    // Hide Contact and Pricing links when user is logged in
    if (user && (item.name === 'Contact' || item.name === 'Pricing')) return false;
    return true;
  });

  // Grouped navigation structure for dropdowns
  const analysisDropdownItems = [
    {
      name: 'Portfolio Analysis',
      href: '/portfolio-analysis',
      icon: FolderGit2,
      description: 'Assess candidate via portfolio',
      color: 'indigo',
      badge: 'NEW',
      badgeColor: 'indigo',
      requiresPlan: ['starter', 'growth', 'scale', 'scale_plus'], // Hide from FREE users
    },
    {
      name: 'PR Analysis',
      href: '/pr-analysis',
      icon: GitPullRequest,
      description: 'Assess candidate via PR contributions',
      color: 'teal',
      badge: 'BETA',
      badgeColor: 'teal',
      requiresPlan: ['starter', 'growth', 'scale', 'scale_plus'], // Hide from FREE users
    },
    {
      name: 'Repository Analysis',
      href: '/analyze',
      icon: GitBranch,
      description: 'Deep dive into single repository',
      color: 'purple',
      // Available to all tiers including FREE
    },
    // TEMPORARILY REMOVED: Batch Analysis (repo-centric)
    // Will be reimplemented as candidate-centric portfolio batch analysis
    // {
    //   name: 'Batch Analysis',
    //   href: '/batch',
    //   icon: Package,
    //   description: 'Bulk repository assessment',
    //   color: 'blue',
    // },
  ].filter((item) => {
    // Filter based on plan requirements
    if (item.requiresPlan && user?.subscription_plan) {
      return item.requiresPlan.includes(user.subscription_plan);
    }
    // If no requiresPlan is specified, show to everyone
    return !item.requiresPlan || true;
  });

  const historyDropdownItems = [
    {
      name: 'Portfolio Analyses',
      href: '/portfolio-analyses',
      icon: FolderGit2,
      description: 'Past candidate portfolio insights',
      requiresPlan: ['starter', 'growth', 'scale', 'scale_plus'], // Hide from FREE users
    },
    {
      name: 'PR Analyses',
      href: '/pr-analyses',
      icon: RefreshCw,
      description: 'Past PR contribution insights',
      requiresPlan: ['starter', 'growth', 'scale', 'scale_plus'], // Hide from FREE users
    },
    {
      name: 'Repository Analyses',
      href: '/analyses',
      icon: BarChart3,
      description: 'Past repository deep dives',
      // Available to all tiers including FREE
    },
    // TEMPORARILY REMOVED: Batch History (repo-centric)
    // Will be reimplemented as candidate-centric portfolio batch analysis
    // {
    //   name: 'Batch History',
    //   href: '/batch/history',
    //   icon: Archive,
    //   description: 'Past bulk assessments',
    //   requiresPlan: ['scale', 'scale_plus'],
    // },
  ].filter((item) => {
    // Filter based on plan requirements
    if (item.requiresPlan && user?.subscription_plan) {
      return item.requiresPlan.includes(user.subscription_plan);
    }
    // If no requiresPlan is specified, show to everyone
    return !item.requiresPlan || true;
  });

  // Single-level navigation items (not in dropdowns)
  const directNavItems = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Billing', href: '/billing', icon: CreditCard },
    { name: 'Messages', href: '/messages', icon: MessageCircle },
  ];

  const adminNavigation = [{ name: 'Admin', href: '/admin' }];

  return (
    <nav className="sticky top-0 z-50 border-white/[0.06] border-b bg-[#0A0A0A]/80 shadow-sm backdrop-blur-md">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-14 items-center justify-between">
          <div className="flex flex-1 items-center">
            {/* Logo */}
            <div className="flex flex-shrink-0 items-center">
              <Link href="/" className="group relative flex items-center gap-3">
                <div className="absolute inset-0 bg-gradient-to-r from-purple-600 to-blue-600 opacity-0 blur-xl transition-opacity duration-300 group-hover:opacity-50"></div>
                <Image
                  src="/exiqus-logo.png"
                  alt="Exiqus Logo"
                  width={56}
                  height={56}
                  className="relative h-14 w-14 transition-transform duration-300 group-hover:scale-110"
                  priority
                  unoptimized
                />
                <span className="relative font-brand font-semibold text-2xl tracking-wide">
                  <GradientText>EXIQUS</GradientText>
                </span>
              </Link>
            </div>

            {/* Desktop Navigation */}
            <div className="hidden sm:mr-auto sm:ml-auto sm:flex sm:items-center sm:space-x-2">
              {navigation.map((item) => (
                <Link
                  key={item.name}
                  href={item.href}
                  className={cn(
                    'inline-flex items-center rounded-md px-3 py-1 font-medium text-sm transition-colors',
                    pathname === item.href
                      ? 'bg-purple-600/10 text-purple-400'
                      : 'text-gray-400 hover:bg-white/[0.03] hover:text-gray-300'
                  )}
                >
                  {item.name}
                </Link>
              ))}
              {user && (
                <>
                  {/* Analysis Dropdown */}
                  <div
                    className="relative"
                    onMouseEnter={handleAnalysisMouseEnter}
                    onMouseLeave={handleAnalysisMouseLeave}
                  >
                    <button
                      type="button"
                      className={cn(
                        'flex items-center gap-1.5 rounded-md px-3 py-2 font-medium text-sm transition-colors',
                        analysisDropdownItems.some((item) => pathname.startsWith(item.href))
                          ? 'bg-purple-600/10 text-purple-400'
                          : 'text-gray-400 hover:bg-white/[0.03] hover:text-gray-300'
                      )}
                    >
                      <Search className="h-4 w-4" />
                      <span>Analysis</span>
                      <ChevronDown
                        className={cn(
                          'h-3 w-3 transition-transform',
                          isAnalysisDropdownOpen && 'rotate-180'
                        )}
                      />
                    </button>

                    {isAnalysisDropdownOpen && (
                      <div className="fade-in slide-in-from-top-2 absolute top-full left-0 mt-2 w-64 animate-in duration-200">
                        <div className="rounded-xl border border-white/[0.09] bg-[#111111]/95 shadow-2xl ring-1 ring-white/5 backdrop-blur-xl">
                          {analysisDropdownItems.map((item) => (
                            <Link
                              key={item.name}
                              href={item.href}
                              className="flex items-start gap-3 px-4 py-3 transition-colors first:rounded-t-xl last:rounded-b-xl hover:bg-white/[0.06]"
                              onClick={() => setIsAnalysisDropdownOpen(false)}
                            >
                              <item.icon
                                className={cn(
                                  'mt-0.5 h-4 w-4',
                                  item.color === 'indigo' && 'text-indigo-400',
                                  item.color === 'purple' && 'text-purple-400',
                                  item.color === 'teal' && 'text-teal-400',
                                  item.color === 'blue' && 'text-blue-400'
                                )}
                              />
                              <div className="min-w-0 flex-1">
                                <div className="flex items-center gap-2">
                                  <span className="font-medium text-gray-200 text-sm">
                                    {item.name}
                                  </span>
                                  {item.badge && (
                                    <span
                                      className={cn(
                                        'rounded-full px-2 py-0.5 font-medium text-xs',
                                        item.badgeColor === 'indigo' &&
                                          'bg-indigo-500/20 text-indigo-400',
                                        item.badgeColor === 'teal' &&
                                          'bg-teal-500/20 text-teal-400',
                                        item.badgeColor === 'purple' &&
                                          'bg-purple-500/20 text-purple-400'
                                      )}
                                    >
                                      {item.badge}
                                    </span>
                                  )}
                                </div>
                                <p className="mt-0.5 text-gray-500 text-xs">{item.description}</p>
                              </div>
                            </Link>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Dashboard Dropdown */}
                  <div
                    className="relative"
                    onMouseEnter={handleDashboardMouseEnter}
                    onMouseLeave={handleDashboardMouseLeave}
                  >
                    <button
                      type="button"
                      className={cn(
                        'flex items-center gap-1.5 rounded-md px-3 py-2 font-medium text-sm transition-colors',
                        pathname === '/dashboard' || pathname.startsWith('/candidate-hub')
                          ? 'bg-purple-600/10 text-purple-400'
                          : 'text-gray-400 hover:bg-white/[0.03] hover:text-gray-300'
                      )}
                    >
                      <LayoutDashboard className="h-4 w-4" />
                      <span>Dashboard</span>
                      <ChevronDown className="h-3.5 w-3.5" />
                    </button>

                    {isDashboardDropdownOpen && (
                      <div className="absolute top-full left-0 z-50 mt-1 w-80 rounded-lg border border-white/10 bg-gray-900/95 p-2 shadow-xl backdrop-blur-xl">
                        <div className="space-y-0.5">
                          <Link
                            href="/dashboard"
                            className={cn(
                              'flex items-start gap-3 rounded-md p-3 transition-colors',
                              pathname === '/dashboard'
                                ? 'bg-purple-600/10 text-purple-400'
                                : 'text-gray-300 hover:bg-white/[0.05] hover:text-white'
                            )}
                          >
                            <LayoutDashboard className="mt-0.5 h-5 w-5 shrink-0 text-purple-400" />
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <span className="font-medium">Overview</span>
                              </div>
                              <p className="mt-0.5 text-gray-500 text-xs">
                                Analytics and activity dashboard
                              </p>
                            </div>
                          </Link>

                          {/* Candidate Hub - Hidden for FREE tier */}
                          {user?.subscription_plan !== 'free' && (
                            <Link
                              href="/candidate-hub"
                              className={cn(
                                'flex items-start gap-3 rounded-md p-3 transition-colors',
                                pathname.startsWith('/candidate-hub')
                                  ? 'bg-emerald-600/10 text-emerald-400'
                                  : 'text-gray-300 hover:bg-white/[0.05] hover:text-white'
                              )}
                            >
                              <Users className="mt-0.5 h-5 w-5 shrink-0 text-emerald-400" />
                              <div className="flex-1">
                                <div className="flex items-center gap-2">
                                  <span className="font-medium">Candidate Intelligence Hub</span>
                                </div>
                                <p className="mt-0.5 text-gray-500 text-xs">
                                  Manage all candidate insights
                                </p>
                              </div>
                            </Link>
                          )}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* History Dropdown */}
                  <div
                    className="relative"
                    onMouseEnter={handleHistoryMouseEnter}
                    onMouseLeave={handleHistoryMouseLeave}
                  >
                    <button
                      type="button"
                      className={cn(
                        'flex items-center gap-1.5 rounded-md px-3 py-2 font-medium text-sm transition-colors',
                        historyDropdownItems.some((item) => pathname.startsWith(item.href))
                          ? 'bg-purple-600/10 text-purple-400'
                          : 'text-gray-400 hover:bg-white/[0.03] hover:text-gray-300'
                      )}
                    >
                      <Archive className="h-4 w-4" />
                      <span>History</span>
                      <ChevronDown
                        className={cn(
                          'h-3 w-3 transition-transform',
                          isHistoryDropdownOpen && 'rotate-180'
                        )}
                      />
                    </button>

                    {isHistoryDropdownOpen && (
                      <div className="fade-in slide-in-from-top-2 absolute top-full left-0 mt-2 w-64 animate-in duration-200">
                        <div className="rounded-xl border border-white/[0.09] bg-[#111111]/95 shadow-2xl ring-1 ring-white/5 backdrop-blur-xl">
                          {historyDropdownItems.map((item) => (
                            <Link
                              key={item.name}
                              href={item.href}
                              className="flex items-start gap-3 px-4 py-3 transition-colors first:rounded-t-xl last:rounded-b-xl hover:bg-white/[0.06]"
                              onClick={() => setIsHistoryDropdownOpen(false)}
                            >
                              <item.icon className="mt-0.5 h-4 w-4 text-cyan-400" />
                              <div className="min-w-0 flex-1">
                                <span className="font-medium text-gray-200 text-sm">
                                  {item.name}
                                </span>
                                <p className="mt-0.5 text-gray-500 text-xs">{item.description}</p>
                              </div>
                            </Link>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Direct Navigation Items (Billing, Messages) */}
                  {directNavItems
                    .filter((item) => item.name !== 'Dashboard')
                    .map((item) => (
                      <Link
                        key={item.name}
                        href={item.href}
                        className={cn(
                          'inline-flex items-center gap-2 rounded-md px-3 py-2 font-medium text-sm transition-colors',
                          pathname === item.href
                            ? 'bg-purple-600/10 text-purple-400'
                            : 'text-gray-400 hover:bg-white/[0.03] hover:text-gray-300'
                        )}
                      >
                        <item.icon className="h-4 w-4" />
                        <span>{item.name}</span>
                      </Link>
                    ))}

                  {/* Admin Link */}
                  {user.role === 'admin' &&
                    adminNavigation.map((item) => (
                      <Link
                        key={item.name}
                        href={item.href}
                        className={cn(
                          'inline-flex items-center rounded-md px-3 py-2 font-medium text-sm transition-colors',
                          pathname === item.href
                            ? 'bg-purple-600/10 text-purple-400'
                            : 'text-gray-400 hover:bg-white/[0.03] hover:text-gray-300'
                        )}
                      >
                        {item.name}
                      </Link>
                    ))}
                </>
              )}
            </div>
          </div>

          {/* Right side buttons */}
          <div className="hidden space-x-3 sm:flex sm:items-center sm:justify-end">
            {user ? (
              <div className="flex items-center gap-3 sm:gap-4">
                {/* Trial Badge */}
                {user.subscription_status === 'trialing' && (
                  <div className="flex items-center rounded-full bg-gradient-to-r from-yellow-500/20 to-orange-500/20 px-3 py-1 font-medium text-xs text-yellow-400 ring-1 ring-yellow-500/30">
                    <Sparkles className="mr-1.5 h-3 w-3" />
                    <span className="whitespace-nowrap">
                      TRIAL ACTIVE
                      {user.trial_end_date && (
                        <>
                          {' · '}
                          {(() => {
                            const daysLeft = Math.ceil(
                              (new Date(user.trial_end_date).getTime() - new Date().getTime()) /
                                (1000 * 60 * 60 * 24)
                            );
                            if (daysLeft <= 0) return 'Expires today';
                            if (daysLeft === 1) return '1 day left';
                            return `${daysLeft} days left`;
                          })()}
                        </>
                      )}
                    </span>
                  </div>
                )}

                <div className="relative">
                  <button
                    type="button"
                    onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                    onBlur={() => setTimeout(() => setIsUserMenuOpen(false), 200)}
                    className="flex max-w-48 items-center rounded-md px-3 py-2 font-medium text-gray-300 text-sm transition-colors hover:text-gray-100 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2"
                  >
                    <span className="truncate">{user.company || user.full_name || user.email}</span>
                    <ChevronDown
                      className={cn(
                        'ml-2 h-4 w-4 transition-transform',
                        isUserMenuOpen && 'rotate-180'
                      )}
                    />
                  </button>

                  {isUserMenuOpen && (
                    <div className="absolute right-0 z-50 mt-2 w-48 rounded-md bg-[#111111] shadow-lg ring-1 ring-white/10">
                      <div className="py-1">
                        <Link
                          href="/account"
                          className="flex items-center px-4 py-2 text-gray-300 text-sm hover:bg-white/[0.06]"
                          onClick={() => setIsUserMenuOpen(false)}
                        >
                          <User className="mr-3 h-4 w-4" />
                          Account Settings
                        </Link>
                        <Link
                          href="/messages"
                          className="flex items-center px-4 py-2 text-gray-300 text-sm hover:bg-white/[0.06]"
                          onClick={() => setIsUserMenuOpen(false)}
                        >
                          <MessageCircle className="mr-3 h-4 w-4" />
                          My Messages
                        </Link>
                        <hr className="my-1 border-white/[0.06]" />
                        <button
                          type="button"
                          onClick={() => {
                            logout();
                            setIsUserMenuOpen(false);
                          }}
                          className="flex w-full items-center px-4 py-2 text-left text-gray-300 text-sm hover:bg-white/[0.06]"
                        >
                          <LogOut className="mr-3 h-4 w-4" />
                          Logout
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <>
                <Link href="/login">
                  <ExiqusButton variant="ghost" size="sm">
                    Login
                  </ExiqusButton>
                </Link>
                <Link href="/signup">
                  <ExiqusButton size="sm">Get Started</ExiqusButton>
                </Link>
              </>
            )}
          </div>

          {/* Mobile menu button */}
          <div className="flex items-center sm:hidden">
            <button
              type="button"
              className="inline-flex items-center justify-center rounded-md p-2 text-gray-400 hover:bg-white/[0.06] hover:text-gray-300 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-inset"
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            >
              <span className="sr-only">Open main menu</span>
              {isMobileMenuOpen ? (
                <X className="block h-5 w-5" />
              ) : (
                <Menu className="block h-5 w-5" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      {isMobileMenuOpen && (
        <div className="border-white/[0.06] border-b bg-[#111111] sm:hidden">
          <div className="space-y-1 pt-2 pb-3">
            {navigation.map((item) => (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  'block py-2 pr-4 pl-3 font-medium text-base transition-colors',
                  pathname === item.href
                    ? 'border-purple-400 border-l-4 bg-white/[0.06] text-purple-400'
                    : 'text-gray-400 hover:bg-white/[0.03] hover:text-gray-300'
                )}
                onClick={() => setIsMobileMenuOpen(false)}
              >
                {item.name}
              </Link>
            ))}
            {user && (
              <>
                {/* Analysis Accordion */}
                <div className="border-transparent border-l-4">
                  <button
                    type="button"
                    onClick={() => setIsMobileAnalysisOpen(!isMobileAnalysisOpen)}
                    className="flex w-full items-center justify-between py-2 pr-4 pl-3 font-medium text-base text-gray-400 hover:bg-white/[0.03] hover:text-gray-300"
                  >
                    <div className="flex items-center gap-2">
                      <Search className="h-4 w-4" />
                      <span>Analysis</span>
                    </div>
                    <ChevronDown
                      className={cn(
                        'h-4 w-4 transition-transform',
                        isMobileAnalysisOpen && 'rotate-180'
                      )}
                    />
                  </button>
                  {isMobileAnalysisOpen && (
                    <div className="bg-white/[0.02]">
                      {analysisDropdownItems.map((item) => (
                        <Link
                          key={item.name}
                          href={item.href}
                          className={cn(
                            'flex items-center gap-3 py-2 pr-4 pl-8 text-sm transition-colors',
                            pathname === item.href
                              ? 'bg-white/[0.06] text-purple-400'
                              : 'text-gray-400 hover:bg-white/[0.03] hover:text-gray-300'
                          )}
                          onClick={() => {
                            setIsMobileMenuOpen(false);
                            setIsMobileAnalysisOpen(false);
                          }}
                        >
                          <item.icon className="h-4 w-4" />
                          <span>{item.name}</span>
                          {item.badge && (
                            <span className="ml-auto rounded-full bg-teal-500/20 px-2 py-0.5 font-medium text-teal-400 text-xs">
                              {item.badge}
                            </span>
                          )}
                        </Link>
                      ))}
                    </div>
                  )}
                </div>

                {/* Dashboard Accordion */}
                <div className="border-transparent border-l-4">
                  <button
                    type="button"
                    onClick={() => setIsMobileDashboardOpen(!isMobileDashboardOpen)}
                    className="flex w-full items-center justify-between py-2 pr-4 pl-3 font-medium text-base text-gray-400 hover:bg-white/[0.03] hover:text-gray-300"
                  >
                    <div className="flex items-center gap-2">
                      <LayoutDashboard className="h-4 w-4" />
                      <span>Dashboard</span>
                    </div>
                    <ChevronDown
                      className={cn(
                        'h-4 w-4 transition-transform',
                        isMobileDashboardOpen && 'rotate-180'
                      )}
                    />
                  </button>
                  {isMobileDashboardOpen && (
                    <div className="bg-white/[0.02]">
                      <Link
                        href="/dashboard"
                        className={cn(
                          'flex items-center gap-3 py-2 pr-4 pl-8 text-sm transition-colors',
                          pathname === '/dashboard'
                            ? 'bg-white/[0.06] text-purple-400'
                            : 'text-gray-400 hover:bg-white/[0.03] hover:text-gray-300'
                        )}
                        onClick={() => {
                          setIsMobileMenuOpen(false);
                          setIsMobileDashboardOpen(false);
                        }}
                      >
                        <LayoutDashboard className="h-4 w-4 text-purple-400" />
                        <span>Overview</span>
                      </Link>
                      {/* Candidate Hub - Hidden for FREE tier */}
                      {user?.subscription_plan !== 'free' && (
                        <Link
                          href="/candidate-hub"
                          className={cn(
                            'flex items-center gap-3 py-2 pr-4 pl-8 text-sm transition-colors',
                            pathname.startsWith('/candidate-hub')
                              ? 'bg-white/[0.06] text-emerald-400'
                              : 'text-gray-400 hover:bg-white/[0.03] hover:text-gray-300'
                          )}
                          onClick={() => {
                            setIsMobileMenuOpen(false);
                            setIsMobileDashboardOpen(false);
                          }}
                        >
                          <Users className="h-4 w-4 text-emerald-400" />
                          <span>Candidate Intelligence Hub</span>
                        </Link>
                      )}
                    </div>
                  )}
                </div>

                {/* History Accordion */}
                <div className="border-transparent border-l-4">
                  <button
                    type="button"
                    onClick={() => setIsMobileHistoryOpen(!isMobileHistoryOpen)}
                    className="flex w-full items-center justify-between py-2 pr-4 pl-3 font-medium text-base text-gray-400 hover:bg-white/[0.03] hover:text-gray-300"
                  >
                    <div className="flex items-center gap-2">
                      <Archive className="h-4 w-4" />
                      <span>History</span>
                    </div>
                    <ChevronDown
                      className={cn(
                        'h-4 w-4 transition-transform',
                        isMobileHistoryOpen && 'rotate-180'
                      )}
                    />
                  </button>
                  {isMobileHistoryOpen && (
                    <div className="bg-white/[0.02]">
                      {historyDropdownItems.map((item) => (
                        <Link
                          key={item.name}
                          href={item.href}
                          className={cn(
                            'flex items-center gap-3 py-2 pr-4 pl-8 text-sm transition-colors',
                            pathname === item.href
                              ? 'bg-white/[0.06] text-purple-400'
                              : 'text-gray-400 hover:bg-white/[0.03] hover:text-gray-300'
                          )}
                          onClick={() => {
                            setIsMobileMenuOpen(false);
                            setIsMobileHistoryOpen(false);
                          }}
                        >
                          <item.icon className="h-4 w-4" />
                          <span>{item.name}</span>
                        </Link>
                      ))}
                    </div>
                  )}
                </div>

                {/* Direct Navigation Items (Billing, Messages) */}
                {directNavItems
                  .filter((item) => item.name !== 'Dashboard')
                  .map((item) => (
                    <Link
                      key={item.name}
                      href={item.href}
                      className={cn(
                        'flex items-center gap-3 py-2 pr-4 pl-3 font-medium text-base transition-colors',
                        pathname === item.href
                          ? 'border-purple-400 border-l-4 bg-white/[0.06] text-purple-400'
                          : 'border-transparent border-l-4 text-gray-400 hover:bg-white/[0.03] hover:text-gray-300'
                      )}
                      onClick={() => setIsMobileMenuOpen(false)}
                    >
                      <item.icon className="h-4 w-4" />
                      <span>{item.name}</span>
                    </Link>
                  ))}

                {/* Admin Link */}
                {user.role === 'admin' &&
                  adminNavigation.map((item) => (
                    <Link
                      key={item.name}
                      href={item.href}
                      className={cn(
                        'block py-2 pr-4 pl-3 font-medium text-base transition-colors',
                        pathname === item.href
                          ? 'border-purple-400 border-l-4 bg-white/[0.06] text-purple-400'
                          : 'border-transparent border-l-4 text-gray-400 hover:bg-white/[0.03] hover:text-gray-300'
                      )}
                      onClick={() => setIsMobileMenuOpen(false)}
                    >
                      {item.name}
                    </Link>
                  ))}
              </>
            )}
          </div>
          <div className="border-white/[0.06] border-t pt-4 pb-3">
            {user ? (
              <div className="space-y-1">
                <div className="px-4 py-2">
                  <p className="font-medium text-gray-300 text-sm">
                    {user.company || user.full_name || user.email}
                  </p>
                  {(user.company || user.full_name) && (
                    <p className="text-gray-500 text-xs">{user.email}</p>
                  )}
                </div>
                <Link
                  href="/account"
                  className="block px-4 py-2 font-medium text-base text-gray-400 hover:bg-white/[0.03] hover:text-gray-300"
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  Account Settings
                </Link>
                <button
                  type="button"
                  onClick={() => {
                    logout();
                    setIsMobileMenuOpen(false);
                  }}
                  className="block w-full px-4 py-2 text-left font-medium text-base text-gray-400 hover:bg-white/[0.03] hover:text-gray-300"
                >
                  Logout
                </button>
              </div>
            ) : (
              <div className="space-y-2 px-3 py-2">
                <Link
                  href="/login"
                  className="block w-full"
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  <ExiqusButton variant="ghost" size="sm" className="w-full">
                    Login
                  </ExiqusButton>
                </Link>
                <Link
                  href="/signup"
                  className="block w-full"
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  <ExiqusButton size="sm" className="w-full">
                    Get Started
                  </ExiqusButton>
                </Link>
              </div>
            )}
          </div>
        </div>
      )}
    </nav>
  );
}
