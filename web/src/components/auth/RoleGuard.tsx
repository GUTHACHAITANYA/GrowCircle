'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useLocale } from 'next-intl';
import { useAuth, UserRole } from '@/lib/auth';
import { AuthModal } from './AuthModal';
import { Button } from '@/components/ui/Button';
import {
  ShieldAlert,
  Lock,
  ArrowRight,
  ShieldCheck,
  KeyRound,
  RefreshCw,
  UserCheck,
} from 'lucide-react';

export interface RoleGuardProps {
  allowedRoles: UserRole[];
  require2FA?: boolean;
  children: React.ReactNode;
  fallbackTitle?: string;
  fallbackMessage?: string;
}

export const RoleGuard: React.FC<RoleGuardProps> = ({
  allowedRoles,
  require2FA = false,
  children,
  fallbackTitle,
  fallbackMessage,
}) => {
  const locale = useLocale();
  const { user, isAuthenticated, isLoading, verifyAdmin2FA } = useAuth();
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [twoFactorCode, setTwoFactorCode] = useState('');
  const [isVerifying2FA, setIsVerifying2FA] = useState(false);
  const [twoFactorError, setTwoFactorError] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div className="min-h-[400px] flex flex-col items-center justify-center p-8 text-center">
        <RefreshCw className="w-8 h-8 text-deep-leaf animate-spin mb-4" />
        <p className="text-muted font-medium text-sm">Verifying role permissions...</p>
      </div>
    );
  }

  // 1. Not Authenticated: Require login
  if (!isAuthenticated || !user) {
    return (
      <div className="max-w-2xl mx-auto my-12 p-8 sm:p-12 bg-white rounded-3xl border border-border shadow-sm text-center">
        <div className="w-16 h-16 rounded-3xl bg-deep-leaf/10 border border-deep-leaf/20 flex items-center justify-center mx-auto mb-6">
          <Lock className="w-8 h-8 text-deep-leaf" />
        </div>
        <h2 className="text-2xl sm:text-3xl font-bold text-ink tracking-tight mb-3">
          {fallbackTitle || 'Sign In Required (లాగిన్ అవసరం)'}
        </h2>
        <p className="text-muted text-base max-w-md mx-auto mb-8 leading-relaxed">
          {fallbackMessage ||
            'This area is protected for verified agricultural participants. Sign in with your phone number and OTP to continue.'}
        </p>

        <div className="flex flex-wrap items-center justify-center gap-4">
          <Button
            variant="primary"
            size="lg"
            onClick={() => setShowAuthModal(true)}
            rightIcon={<ArrowRight className="w-5 h-5" />}
          >
            Sign In with Phone OTP (OTP తో లాగిన్)
          </Button>
          <Link href={`/${locale}/prices`}>
            <Button variant="secondary" size="lg">
              View Price Today (No Login)
            </Button>
          </Link>
        </div>

        <AuthModal
          isOpen={showAuthModal}
          onClose={() => setShowAuthModal(false)}
          initialRole={allowedRoles[0] || 'farmer'}
        />
      </div>
    );
  }

  // 2. Authenticated but Unauthorized Role: 403 Forbidden
  if (!allowedRoles.includes(user.role)) {
    const roleRedirects: Record<UserRole, string> = {
      farmer: `/${locale}/diary`,
      buyer: `/${locale}/portal`,
      driver: `/${locale}/driver`,
      consumer: `/${locale}/prices`,
      admin: `/${locale}/admin`,
    };
    const targetDashboard = roleRedirects[user.role] || `/${locale}/prices`;

    return (
      <div
        role="alert"
        aria-live="assertive"
        className="max-w-2xl mx-auto my-12 p-8 sm:p-12 bg-white rounded-3xl border border-red-200 shadow-sm text-center"
      >
        <div className="w-16 h-16 rounded-3xl bg-red-50 border border-red-200 flex items-center justify-center mx-auto mb-6 text-red-600">
          <ShieldAlert className="w-8 h-8" />
        </div>

        <span className="inline-block px-3 py-1 rounded-full bg-red-100 text-red-800 font-bold text-xs uppercase tracking-wider mb-3">
          403 Forbidden • Access Denied
        </span>

        <h2 className="text-2xl sm:text-3xl font-bold text-ink tracking-tight mb-3">
          Role Permission Required
        </h2>

        <p className="text-muted text-base max-w-md mx-auto mb-6 leading-relaxed">
          Your current account role is <strong className="text-ink uppercase">{user.role}</strong>.
          This page requires one of the following authorized roles:{' '}
          <span className="font-semibold text-deep-leaf">{allowedRoles.join(', ')}</span>.
        </p>

        <div className="p-4 rounded-2xl bg-cream border border-border max-w-md mx-auto mb-8 text-xs text-left space-y-1.5 text-muted">
          <p>
            <strong className="text-ink">User:</strong> {user.name || user.phone}
          </p>
          <p>
            <strong className="text-ink">Phone:</strong> +91 {user.phone}
          </p>
          <p>
            <strong className="text-ink">Active Role:</strong> {user.role}
          </p>
        </div>

        <div className="flex flex-wrap items-center justify-center gap-4">
          <Link href={targetDashboard}>
            <Button variant="primary" size="lg" rightIcon={<ArrowRight className="w-5 h-5" />}>
              Go to My {user.role.toUpperCase()} Dashboard
            </Button>
          </Link>
          <Link href={`/${locale}/profile`}>
            <Button variant="secondary" size="lg">
              Switch / Update Profile
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  // 3. Admin requires 2FA verification
  if (require2FA && user.role === 'admin' && !user.is_admin_2fa_verified) {
    const handleVerifyAdmin = async (e: React.FormEvent) => {
      e.preventDefault();
      setTwoFactorError(null);
      if (twoFactorCode.trim().length !== 6) {
        setTwoFactorError('Please enter the 6-digit TOTP code');
        return;
      }

      setIsVerifying2FA(true);
      try {
        await verifyAdmin2FA(twoFactorCode.trim());
      } catch (err: unknown) {
        setTwoFactorError(err instanceof Error ? err.message : 'Invalid 2FA code');
      } finally {
        setIsVerifying2FA(false);
      }
    };

    return (
      <div className="max-w-md mx-auto my-12 p-8 bg-white rounded-3xl border border-amber-300 shadow-sm text-center">
        <div className="w-16 h-16 rounded-3xl bg-amber-50 border border-amber-200 flex items-center justify-center mx-auto mb-6 text-amber-600">
          <KeyRound className="w-8 h-8" />
        </div>

        <span className="inline-block px-3 py-1 rounded-full bg-amber-100 text-amber-900 font-bold text-xs uppercase tracking-wider mb-3">
          2FA Verification Required
        </span>

        <h2 className="text-2xl font-bold text-ink tracking-tight mb-2">
          Administrator 2FA Guard
        </h2>

        <p className="text-muted text-sm mb-6 leading-relaxed">
          Admin queues, disputes, and mandi governance are protected by mandatory Two-Factor Authentication.
          In demo mode, use master code <strong className="font-mono text-ink">654321</strong>.
        </p>

        {twoFactorError && (
          <div className="p-3 mb-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs text-left">
            {twoFactorError}
          </div>
        )}

        <form onSubmit={handleVerifyAdmin} className="space-y-4">
          <input
            type="text"
            inputMode="numeric"
            maxLength={6}
            placeholder="654321"
            value={twoFactorCode}
            onChange={(e) => setTwoFactorCode(e.target.value.replace(/\D/g, ''))}
            className="w-full text-center tracking-[0.4em] px-4 py-3.5 bg-cream/50 border border-border rounded-2xl text-ink font-mono text-xl font-bold focus:outline-none focus:ring-2 focus:ring-deep-leaf focus:bg-white"
            autoFocus
          />

          <div className="flex gap-2">
            <Button
              type="button"
              variant="secondary"
              size="md"
              onClick={() => setTwoFactorCode('654321')}
              className="flex-1 text-xs"
            >
              Fill Demo (654321)
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="md"
              disabled={twoFactorCode.length !== 6 || isVerifying2FA}
              className="flex-1 text-xs"
            >
              {isVerifying2FA ? 'Verifying...' : 'Unlock 2FA'}
            </Button>
          </div>
        </form>
      </div>
    );
  }

  // 4. Authorized
  return <>{children}</>;
};
