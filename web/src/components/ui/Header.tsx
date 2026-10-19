'use client';

import React, { useState } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { clsx } from 'clsx';
import { useAuth } from '@/lib/auth';
import { AuthModal } from '@/components/auth/AuthModal';
import { LanguageSwitcher, SupportedLocale } from './LanguageSwitcher';
import {
  LogOut,
  User as UserIcon,
  LogIn,
  Shield,
  Tractor,
  Store,
  Truck,
  Users,
} from 'lucide-react';

export interface HeaderProps {
  currentLocale: SupportedLocale;
  onSelectLocale: (locale: SupportedLocale) => void;
  brandName?: string;
  className?: string;
  activeNav?: string;
  isDemoMode?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  currentLocale,
  onSelectLocale,
  brandName = 'GrowCircle',
  className,
  activeNav,
  isDemoMode,
}) => {
  const { user, isAuthenticated, logout } = useAuth();
  const [showAuthModal, setShowAuthModal] = useState(false);

  const showDemoBanner =
    isDemoMode ?? (process.env.NEXT_PUBLIC_APP_MODE !== 'production');

  const getRoleIcon = () => {
    switch (user?.role) {
      case 'farmer':
        return <Tractor className="w-3.5 h-3.5 text-deep-leaf" />;
      case 'buyer':
        return <Store className="w-3.5 h-3.5 text-amber-700" />;
      case 'driver':
        return <Truck className="w-3.5 h-3.5 text-blue-700" />;
      case 'admin':
        return <Shield className="w-3.5 h-3.5 text-red-600" />;
      default:
        return <Users className="w-3.5 h-3.5 text-muted" />;
    }
  };

  return (
    <>
      <header
        role="banner"
        className={clsx(
          'sticky top-0 z-40 bg-white/95 backdrop-blur border-b border-border transition-shadow',
          className
        )}
      >
        {/* RULE A: Permanent visible banner in Demo mode */}
        {showDemoBanner && (
          <div
            role="alert"
            className="bg-amber-100/90 border-b border-amber-300 text-amber-900 py-1.5 px-4 text-center text-xs sm:text-sm font-bold flex items-center justify-center gap-2"
          >
            <span className="w-2.5 h-2.5 rounded-full bg-amber-600 animate-pulse" />
            <span>Demo data, not real prices</span>
            <span className="hidden sm:inline font-normal text-amber-800">
              — Real prices require verified government mandi auctions
            </span>
          </div>
        )}

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-20 gap-4">
            {/* Logo & Brand Name */}
            <Link
              href={`/${currentLocale}`}
              className="flex items-center gap-3 focus:outline-none focus-visible:ring-2 focus-visible:ring-deep-leaf rounded-xl p-1 -ml-1 group flex-shrink-0"
              aria-label={`${brandName} Home`}
            >
              <div className="w-12 h-12 relative flex-shrink-0">
                <Image
                  src="/logo-mark.svg"
                  alt=""
                  width={48}
                  height={48}
                  priority
                  className="w-full h-full object-contain"
                />
              </div>

              <div className="flex flex-col">
                <span className="font-heading text-2xl sm:text-3xl font-extrabold tracking-tight leading-none">
                  <span className="text-amber">G</span>
                  <span className="text-deep-leaf">row</span>
                  <span className="text-amber">C</span>
                  <span className="text-deep-leaf">ircle</span>
                </span>
                {currentLocale !== 'en' && (
                  <span className="text-xs font-semibold text-muted leading-tight mt-0.5">
                    {brandName}
                  </span>
                )}
              </div>
            </Link>

            {/* Navigation links filtered by User Role */}
            <div className="flex items-center gap-2 sm:gap-4">
              <nav className="hidden md:flex items-center gap-1.5 lg:gap-2">
                {/* 1. Price Today is universally accessible to all visitors and roles */}
                <Link
                  href={`/${currentLocale}/prices`}
                  className={clsx(
                    'px-3 py-2 rounded-xl text-sm font-semibold transition-colors min-h-[44px] inline-flex items-center',
                    activeNav === 'prices'
                      ? 'bg-deep-leaf text-white shadow-sm'
                      : 'text-ink hover:text-deep-leaf hover:bg-black/5'
                  )}
                >
                  Price Today
                </Link>

                {/* 2. Role-specific Links: Only shown when logged in with appropriate role */}
                {isAuthenticated && user?.role === 'farmer' && (
                  <>
                    <Link
                      href={`/${currentLocale}/farmer`}
                      className={clsx(
                        'px-3 py-2 rounded-xl text-sm font-semibold transition-colors min-h-[44px] inline-flex items-center',
                        activeNav === 'farmer'
                          ? 'bg-deep-leaf text-white shadow-sm'
                          : 'text-ink hover:text-deep-leaf hover:bg-black/5'
                      )}
                    >
                      Farmer Dashboard
                    </Link>
                    <Link
                      href={`/${currentLocale}/diary`}
                      className={clsx(
                        'px-3 py-2 rounded-xl text-sm font-semibold transition-colors min-h-[44px] inline-flex items-center',
                        activeNav === 'diary'
                          ? 'bg-deep-leaf text-white shadow-sm'
                          : 'text-ink hover:text-deep-leaf hover:bg-black/5'
                      )}
                    >
                      Farm Diary
                    </Link>
                    <Link
                      href={`/${currentLocale}/plan`}
                      className={clsx(
                        'px-3 py-2 rounded-xl text-sm font-semibold transition-colors min-h-[44px] inline-flex items-center',
                        activeNav === 'plan'
                          ? 'bg-deep-leaf text-white shadow-sm'
                          : 'text-ink hover:text-deep-leaf hover:bg-black/5'
                      )}
                    >
                      Crop Planning
                    </Link>
                  </>
                )}

                {isAuthenticated && user?.role === 'buyer' && (
                  <Link
                    href={`/${currentLocale}/portal`}
                    className={clsx(
                      'px-3 py-2 rounded-xl text-sm font-semibold transition-colors min-h-[44px] inline-flex items-center',
                      activeNav === 'portal'
                        ? 'bg-deep-leaf text-white shadow-sm'
                        : 'text-ink hover:text-deep-leaf hover:bg-black/5'
                    )}
                  >
                    Buyer Portal
                  </Link>
                )}

                {isAuthenticated && user?.role === 'driver' && (
                  <Link
                    href={`/${currentLocale}/driver`}
                    className={clsx(
                      'px-3 py-2 rounded-xl text-sm font-semibold transition-colors min-h-[44px] inline-flex items-center',
                      activeNav === 'driver'
                        ? 'bg-deep-leaf text-white shadow-sm'
                        : 'text-ink hover:text-deep-leaf hover:bg-black/5'
                    )}
                  >
                    Transporter Hub
                  </Link>
                )}

                {/* 3. Admin & Design System: Strictly hidden from non-admin users */}
                {isAuthenticated && user?.role === 'admin' && (
                  <>
                    <Link
                      href={`/${currentLocale}/admin`}
                      className={clsx(
                        'px-3 py-2 rounded-xl text-sm font-semibold transition-colors min-h-[44px] inline-flex items-center',
                        activeNav === 'admin'
                          ? 'bg-deep-leaf text-white shadow-sm'
                          : 'text-ink hover:text-deep-leaf hover:bg-black/5'
                      )}
                    >
                      Admin Console
                    </Link>
                    <Link
                      href={`/${currentLocale}/showcase`}
                      className={clsx(
                        'px-3 py-2 rounded-xl text-sm font-semibold transition-colors min-h-[44px] inline-flex items-center',
                        activeNav === 'showcase'
                          ? 'bg-deep-leaf/10 text-deep-leaf font-bold'
                          : 'text-ink hover:text-deep-leaf hover:bg-black/5'
                      )}
                    >
                      Design System
                    </Link>
                  </>
                )}
              </nav>

              {/* Language Switcher */}
              <LanguageSwitcher
                currentLocale={currentLocale}
                onSelectLocale={onSelectLocale}
                compact
              />

              {/* Authentication & Profile Controls */}
              {isAuthenticated && user ? (
                <div className="flex items-center gap-1.5 sm:gap-2">
                  {/* Profile Link with Role Badge */}
                  <Link
                    href={`/${currentLocale}/profile`}
                    className={clsx(
                      'flex items-center gap-2 px-2.5 sm:px-3 py-1.5 rounded-xl border transition-all text-xs sm:text-sm font-semibold min-h-[44px]',
                      activeNav === 'profile'
                        ? 'bg-deep-leaf/10 border-deep-leaf text-deep-leaf'
                        : 'bg-cream/60 border-border text-ink hover:border-deep-leaf/40 hover:bg-white'
                    )}
                    aria-label="My Profile"
                  >
                    <div className="p-1 rounded-lg bg-white border border-border/80 flex items-center justify-center">
                      {getRoleIcon()}
                    </div>
                    <div className="hidden sm:flex flex-col text-left leading-tight">
                      <span className="font-bold truncate max-w-[100px]">
                        {user.name || user.phone}
                      </span>
                      <span className="text-[10px] uppercase tracking-wider text-muted font-mono font-bold">
                        {user.role}
                      </span>
                    </div>
                  </Link>

                  {/* R6 Requirement 2: Logout button on every page */}
                  <button
                    onClick={() => logout()}
                    className="p-2 sm:px-3 sm:py-2 rounded-xl border border-border bg-white text-ink hover:text-red-600 hover:border-red-200 hover:bg-red-50 transition-colors flex items-center gap-1.5 text-xs sm:text-sm font-semibold min-h-[44px]"
                    aria-label="Log Out of this device"
                    title="Log Out"
                  >
                    <LogOut className="w-4 h-4 text-red-500" />
                    <span className="hidden lg:inline">Log Out</span>
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setShowAuthModal(true)}
                  className="px-3 sm:px-4 py-2 rounded-xl bg-deep-leaf text-white font-semibold text-xs sm:text-sm shadow-sm hover:bg-forest transition-colors flex items-center gap-1.5 min-h-[44px]"
                >
                  <LogIn className="w-4 h-4" />
                  <span>Sign In</span>
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Auth Modal for Sign In / OTP Verification */}
      <AuthModal
        isOpen={showAuthModal}
        onClose={() => setShowAuthModal(false)}
      />
    </>
  );
};

