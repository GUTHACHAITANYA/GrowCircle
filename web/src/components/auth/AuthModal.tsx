'use client';

import React, { useState, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { useAuth, UserRole, User } from '@/lib/auth';
import { Button } from '@/components/ui/Button';
import {
  X,
  Phone,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Clock,
  Sparkles,
  Tractor,
  Store,
  Truck,
  Users,
  Shield,
  KeyRound,
  ArrowRight,
  Info,
} from 'lucide-react';

export interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialRole?: UserRole;
  onSuccess?: (user: User) => void;
}

import { API_BASE, getFriendlyErrorMessage, ApiError } from '@/lib/api';

export const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  onClose,
  initialRole = 'farmer',
  onSuccess,
}) => {
  const t = useTranslations();
  const { sendOtp, verifyOtp, verifyAdmin2FA } = useAuth();

  // Public roles only: admin is strictly excluded from public self-registration
  const safeInitialRole: UserRole = initialRole === 'admin' ? 'farmer' : initialRole;

  const [step, setStep] = useState<'phone' | 'otp' | 'admin2fa'>('phone');
  const [phone, setPhone] = useState('');
  const [name, setName] = useState('');
  const [role, setRole] = useState<UserRole>(safeInitialRole);
  const [otp, setOtp] = useState('');
  const [admin2faCode, setAdmin2faCode] = useState('');
  const [sandboxOtp, setSandboxOtp] = useState<string | null>(null);
  const [isRealProvider, setIsRealProvider] = useState<boolean>(false);
  const [isDemo, setIsDemo] = useState<boolean>(false);

  // Separate timers & counters
  const [expirySeconds, setExpirySeconds] = useState(300);
  const [resendCooldown, setResendCooldown] = useState(0);
  const [attemptsRemaining, setAttemptsRemaining] = useState<number | null>(null);
  const [lockoutSeconds, setLockoutSeconds] = useState<number>(0);

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorRequestId, setErrorRequestId] = useState<string | null>(null);
  const [isServerError, setIsServerError] = useState<boolean>(false);
  const [pendingNotice, setPendingNotice] = useState<string | null>(null);
  const [verifiedUser, setVerifiedUser] = useState<User | null>(null);

  const startCooldown = (seconds: number) => {
    const sec = Math.min(30, Math.max(0, seconds));
    setResendCooldown(sec);
    if (typeof window !== 'undefined' && sec > 0) {
      sessionStorage.setItem('growcircle_resend_until', (Date.now() + sec * 1000).toString());
    }
  };

  // Check provider status (live SMS/WhatsApp vs demo simulation)
  useEffect(() => {
    if (isOpen) {
      fetch(`${API_BASE}/auth/provider-status`)
        .then((res) => (res.ok ? res.json() : null))
        .then((data) => {
          if (data) {
            if (typeof data.is_real_provider === 'boolean') {
              setIsRealProvider(data.is_real_provider);
            }
            if (data.is_demo || data.provider_type === 'mock') {
              setIsDemo(true);
            }
          }
        })
        .catch(() => {
          setIsRealProvider(false);
          setIsDemo(true);
        });

      // Restore active cooldown from sessionStorage
      if (typeof window !== 'undefined') {
        const stored = sessionStorage.getItem('growcircle_resend_until');
        if (stored) {
          const until = parseInt(stored, 10);
          const remaining = Math.max(0, Math.ceil((until - Date.now()) / 1000));
          if (remaining > 0) {
            setResendCooldown(Math.min(30, remaining));
          }
        }
      }
    }
  }, [isOpen]);

  // Sync initial state when modal opens
  useEffect(() => {
    if (isOpen) {
      setRole(safeInitialRole);
      setStep('phone');
      setError(null);
      setErrorRequestId(null);
      setIsServerError(false);
      setPendingNotice(null);
      setOtp('');
      setAdmin2faCode('');
      setSandboxOtp(null);
      setLockoutSeconds(0);
      setAttemptsRemaining(null);
    }
  }, [isOpen, safeInitialRole]);

  // Expiry countdown timer (5m)
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (step === 'otp' && expirySeconds > 0) {
      interval = setInterval(() => {
        setExpirySeconds((prev) => Math.max(0, prev - 1));
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [step, expirySeconds]);

  // Resend cooldown timer (30s)
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (resendCooldown > 0) {
      interval = setInterval(() => {
        setResendCooldown((prev) => {
          const next = Math.max(0, prev - 1);
          if (next === 0 && typeof window !== 'undefined') {
            sessionStorage.removeItem('growcircle_resend_until');
          }
          return next;
        });
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [resendCooldown]);

  // Lockout countdown timer
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (lockoutSeconds > 0) {
      interval = setInterval(() => {
        setLockoutSeconds((prev) => Math.max(0, prev - 1));
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [lockoutSeconds]);

  if (!isOpen) return null;

  const handleSendOtp = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (resendCooldown > 0 || lockoutSeconds > 0) return;
    setError(null);
    setErrorRequestId(null);
    setIsServerError(false);

    const cleanPhone = phone.trim().replace(/\D/g, '');
    if (cleanPhone.length < 10) {
      setError(t('auth.mobileNumberLabel') + ' — 10 digits required');
      return;
    }

    setIsLoading(true);
    try {
      const res = await sendOtp(cleanPhone);
      // Dev OTP is ONLY returned in demo mode; in production it is undefined
      setSandboxOtp(res.sandbox_otp || res.dev_otp || null);
      if (typeof res.is_real_provider === 'boolean') {
        setIsRealProvider(res.is_real_provider);
      }
      if (res.is_demo) {
        setIsDemo(true);
      }
      setExpirySeconds(res.expires_in_seconds || 300);
      startCooldown(res.resend_cooldown_seconds || 30);
      setAttemptsRemaining(5);
      setStep('otp');
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.isServerError) {
          setError('Something went wrong on our side');
          setIsServerError(true);
        } else {
          setError(err.message);
          setIsServerError(false);
        }
        setErrorRequestId(err.requestId || null);

        if (err.status === 429) {
          const match = err.message.match(/(\d+)\s*s/);
          if (match) {
            const sec = parseInt(match[1], 10);
            if (err.message.toLowerCase().includes('cooldown')) {
              startCooldown(sec);
            } else {
              setLockoutSeconds(sec);
            }
          }
        }
      } else {
        const msg = getFriendlyErrorMessage(err, 'Send verification code');
        setError(msg);
        setIsServerError(false);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerifyOtp = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (lockoutSeconds > 0) return;
    setError(null);
    setErrorRequestId(null);
    setIsServerError(false);

    if (otp.trim().length !== 6) {
      setError(t('auth.enterOtpLabel'));
      return;
    }

    setIsLoading(true);
    try {
      const cleanPhone = phone.trim().replace(/\D/g, '');
      const user = await verifyOtp(cleanPhone, otp.trim(), role, name.trim() || undefined);
      setVerifiedUser(user);

      // Check verification status for buyer and driver
      if (
        (user.role === 'buyer' || user.role === 'driver') &&
        user.verification_status === 'pending'
      ) {
        setPendingNotice(t('auth.pendingVerificationNotice'));
        setTimeout(() => {
          onSuccess?.(user);
          onClose();
        }, 2200);
        return;
      }

      if (user.role === 'admin' && !user.is_admin_2fa_verified) {
        setStep('admin2fa');
      } else {
        onSuccess?.(user);
        onClose();
      }
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.isServerError) {
          setError('Something went wrong on our side');
          setIsServerError(true);
        } else {
          setError(err.message);
          setIsServerError(false);
        }
        setErrorRequestId(err.requestId || null);
      } else {
        const msg = getFriendlyErrorMessage(err, 'Verify OTP');
        setError(msg);
        setIsServerError(false);
      }

      const errStr = (err instanceof Error ? err.message : '').toLowerCase();
      // Extract attempts left from message if available
      const matchAttempts = errStr.match(/(\d+)\s*attempt/i);
      if (matchAttempts) {
        setAttemptsRemaining(parseInt(matchAttempts[1], 10));
      }

      // Check if device locked
      if (errStr.includes('locked') || errStr.includes('too many failed')) {
        const match = errStr.match(/(\d+)\s*min/);
        setLockoutSeconds(match ? parseInt(match[1], 10) * 60 : 900);
        setAttemptsRemaining(0);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerify2FA = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setError(null);

    if (admin2faCode.trim().length !== 6) {
      setError(t('auth.adminCodeLabel'));
      return;
    }

    setIsLoading(true);
    try {
      await verifyAdmin2FA(admin2faCode.trim());
      if (verifiedUser) {
        onSuccess?.({ ...verifiedUser, is_admin_2fa_verified: true });
      }
      onClose();
    } catch (err: unknown) {
      setError(getFriendlyErrorMessage(err, 'Verify 2FA'));
    } finally {
      setIsLoading(false);
    }
  };

  // Public roles only: Farmer, Buyer, Transporter, Consumer
  const publicRolesList: {
    role: UserRole;
    titleKey: string;
    subtitleKey: string;
    icon: React.ReactNode;
  }[] = [
    {
      role: 'farmer',
      titleKey: 'auth.roles.farmer.title',
      subtitleKey: 'auth.roles.farmer.subtitle',
      icon: <Tractor className="w-5 h-5 text-deep-leaf" />,
    },
    {
      role: 'buyer',
      titleKey: 'auth.roles.buyer.title',
      subtitleKey: 'auth.roles.buyer.subtitle',
      icon: <Store className="w-5 h-5 text-amber-700" />,
    },
    {
      role: 'driver',
      titleKey: 'auth.roles.driver.title',
      subtitleKey: 'auth.roles.driver.subtitle',
      icon: <Truck className="w-5 h-5 text-blue-700" />,
    },
    {
      role: 'consumer',
      titleKey: 'auth.roles.consumer.title',
      subtitleKey: 'auth.roles.consumer.subtitle',
      icon: <Users className="w-5 h-5 text-purple-700" />,
    },
  ];

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="auth-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in"
    >
      <div className="bg-white rounded-3xl max-w-lg w-full shadow-2xl border border-border overflow-hidden relative">
        {/* Header */}
        <div className="bg-gradient-to-r from-deep-leaf to-forest px-6 py-5 text-white flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-white/10 flex items-center justify-center border border-white/20">
              <ShieldCheck className="w-6 h-6 text-harvest-gold" />
            </div>
            <div>
              <h2 id="auth-modal-title" className="text-xl font-bold tracking-tight">
                {step === 'phone' && t('auth.signInTitle')}
                {step === 'otp' && t('auth.verifyOtpTitle')}
                {step === 'admin2fa' && t('auth.admin2faTitle')}
              </h2>
              <p className="text-xs text-white/80">
                {step === 'phone' && t('auth.phoneSubtitle')}
                {step === 'otp' && t('auth.otpSubtitle', { phone })}
                {step === 'admin2fa' && t('auth.admin2faSubtitle')}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close modal"
            className="text-white/80 hover:text-white p-2 rounded-xl hover:bg-white/10 transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 sm:p-8 space-y-6">
          {error && (
            <div className="p-4 rounded-2xl bg-red-50 border border-red-200 text-red-800 text-sm flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="font-semibold">{error}</p>
                {errorRequestId && (
                  <p className="text-xs font-mono text-red-700/80 mt-1">
                    Request ID: {errorRequestId}
                  </p>
                )}
                {isServerError && (
                  <div className="mt-2.5">
                    <Button
                      type="button"
                      size="md"
                      variant="secondary"
                      className="text-xs bg-white text-red-800 border-red-300 hover:bg-red-100 py-1 px-3"
                      onClick={() => {
                        if (step === 'phone') handleSendOtp();
                        else if (step === 'otp') handleVerifyOtp();
                      }}
                    >
                      Try again
                    </Button>
                  </div>
                )}
                {lockoutSeconds > 0 && (
                  <p className="text-xs mt-1 text-red-700 font-medium">
                    {t('auth.accountLocked', { seconds: lockoutSeconds })}
                  </p>
                )}
              </div>
            </div>
          )}

          {pendingNotice && (
            <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200 text-amber-900 text-sm flex items-start gap-3">
              <Info className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-bold text-sm">{pendingNotice}</p>
              </div>
            </div>
          )}

          {step === 'phone' && (
            <form onSubmit={handleSendOtp} className="space-y-5">
              {/* Phone Input */}
              <div>
                <label htmlFor="auth-phone-input" className="block text-sm font-bold text-ink mb-2">
                  {t('auth.mobileNumberLabel')}
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-muted font-bold">
                    +91
                  </div>
                  <input
                    id="auth-phone-input"
                    type="tel"
                    inputMode="numeric"
                    maxLength={10}
                    placeholder={t('auth.mobileNumberPlaceholder')}
                    value={phone}
                    onChange={(e) => setPhone(e.target.value.replace(/\D/g, ''))}
                    className="w-full pl-14 pr-4 py-3.5 bg-cream/50 border border-border rounded-2xl text-ink font-mono text-lg font-bold focus:outline-none focus:ring-2 focus:ring-deep-leaf focus:bg-white transition-all"
                    required
                    autoFocus
                  />
                  <div className="absolute inset-y-0 right-0 pr-4 flex items-center pointer-events-none">
                    <Phone className="w-5 h-5 text-muted" />
                  </div>
                </div>
                {/* Requirement 6: Only show WhatsApp/SMS if real provider configured; else Demo mode */}
                <p className="text-xs text-muted mt-1.5 flex items-center gap-1.5">
                  <span
                    className={`inline-block w-2 h-2 rounded-full ${
                      isRealProvider ? 'bg-emerald-500' : 'bg-amber-500'
                    }`}
                  />
                  {isRealProvider
                    ? t('auth.realProviderNotice')
                    : t('auth.demoModeNotice')}
                </p>
              </div>

              {/* Optional Name */}
              <div>
                <label htmlFor="auth-name-input" className="block text-sm font-bold text-ink mb-1.5">
                  {t('auth.nameLabel')}{' '}
                  <span className="font-normal text-muted">({t('auth.optional')})</span>
                </label>
                <input
                  id="auth-name-input"
                  type="text"
                  placeholder={t('auth.namePlaceholder')}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-4 py-3 bg-cream/50 border border-border rounded-2xl text-ink text-sm font-medium focus:outline-none focus:ring-2 focus:ring-deep-leaf focus:bg-white transition-all"
                />
              </div>

              {/* Role Selection: Public roles only */}
              <div>
                <label className="block text-sm font-bold text-ink mb-2">
                  {t('auth.selectRoleLabel')}
                </label>
                <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                  {publicRolesList.map((item) => (
                    <button
                      type="button"
                      key={item.role}
                      onClick={() => setRole(item.role)}
                      className={`w-full text-left p-3 rounded-2xl border transition-all flex items-center gap-3 ${
                        role === item.role
                          ? 'bg-deep-leaf/10 border-deep-leaf shadow-sm ring-1 ring-deep-leaf'
                          : 'bg-white border-border hover:border-deep-leaf/40 hover:bg-cream/30'
                      }`}
                    >
                      <div className="p-2 rounded-xl bg-white shadow-xs border border-border flex-shrink-0">
                        {item.icon}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="font-bold text-ink text-sm flex items-center gap-2">
                          <span>{t(item.titleKey)}</span>
                          {role === item.role && (
                            <CheckCircle2 className="w-4 h-4 text-deep-leaf ml-auto flex-shrink-0" />
                          )}
                        </div>
                        <p className="text-xs text-muted truncate">{t(item.subtitleKey)}</p>
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Submit Button */}
              <Button
                type="submit"
                variant="primary"
                size="lg"
                className="w-full shadow-md"
                disabled={phone.length < 10 || isLoading || resendCooldown > 0 || lockoutSeconds > 0}
                rightIcon={<ArrowRight className="w-5 h-5" />}
              >
                {isLoading
                  ? t('auth.sendingOtp')
                  : resendCooldown > 0
                  ? t('auth.resendCooldown', { seconds: resendCooldown })
                  : t('auth.sendOtpButton')}
              </Button>
            </form>
          )}

          {step === 'otp' && (
            <form onSubmit={handleVerifyOtp} className="space-y-5">
              {/* Demo Mode Notice: check server log for the code, no hardcoded OTP on screen */}
              {isDemo && (
                <div className="p-3.5 rounded-2xl bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-amber-600 flex-shrink-0" />
                    <div>
                      <p className="font-semibold text-amber-900">
                        Demo mode: check the server log for the code
                      </p>
                    </div>
                  </div>
                  {sandboxOtp && (
                    <Button
                      type="button"
                      size="md"
                      variant="secondary"
                      onClick={() => setOtp(sandboxOtp)}
                      className="text-xs py-1 px-3"
                    >
                      {t('auth.autoFill')}
                    </Button>
                  )}
                </div>
              )}

              <div>
                <div className="flex items-center justify-between mb-2">
                  <label htmlFor="auth-otp-input" className="block text-sm font-bold text-ink">
                    {t('auth.enterOtpLabel')}
                  </label>
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-muted">
                    <Clock className="w-3.5 h-3.5" />
                    <span>
                      {Math.floor(expirySeconds / 60)}:
                      {(expirySeconds % 60).toString().padStart(2, '0')}
                    </span>
                  </div>
                </div>

                <input
                  id="auth-otp-input"
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  placeholder="• • • • • •"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
                  disabled={lockoutSeconds > 0}
                  className="w-full text-center tracking-[0.5em] px-4 py-4 bg-cream/50 border border-border rounded-2xl text-ink font-mono text-2xl font-extrabold focus:outline-none focus:ring-2 focus:ring-deep-leaf focus:bg-white transition-all disabled:opacity-50"
                  required
                  autoFocus
                />

                {attemptsRemaining !== null && attemptsRemaining < 5 && (
                  <p className="text-xs font-semibold text-amber-700 mt-1.5">
                    {t('auth.attemptsLeft', { count: attemptsRemaining })}
                  </p>
                )}
              </div>

              <div className="flex items-center justify-between text-xs text-muted">
                <button
                  type="button"
                  onClick={() => setStep('phone')}
                  className="hover:text-deep-leaf underline font-semibold"
                >
                  {t('auth.changePhone')} (+91 {phone})
                </button>
                <button
                  type="button"
                  onClick={handleSendOtp}
                  disabled={resendCooldown > 0 || isLoading || lockoutSeconds > 0}
                  className="hover:text-deep-leaf font-semibold disabled:opacity-40"
                >
                  {resendCooldown > 0
                    ? t('auth.resendCooldown', { seconds: resendCooldown })
                    : t('auth.resendOtp')}
                </button>
              </div>

              <Button
                type="submit"
                variant="primary"
                size="lg"
                className="w-full shadow-md"
                disabled={otp.length !== 6 || isLoading || lockoutSeconds > 0}
              >
                {isLoading ? t('auth.verifying') : t('auth.verifyButton')}
              </Button>
            </form>
          )}

          {step === 'admin2fa' && (
            <form onSubmit={handleVerify2FA} className="space-y-5">
              <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200 text-amber-900 text-sm">
                <div className="flex items-center gap-2 mb-1">
                  <Shield className="w-5 h-5 text-amber-600" />
                  <p className="font-bold">{t('auth.admin2faTitle')}</p>
                </div>
                <p className="text-xs text-amber-800">{t('auth.adminCodeDesc')}</p>
              </div>

              <div>
                <label htmlFor="admin-2fa-input" className="block text-sm font-bold text-ink mb-2">
                  {t('auth.adminCodeLabel')}
                </label>
                <div className="relative">
                  <input
                    id="admin-2fa-input"
                    type="text"
                    inputMode="numeric"
                    maxLength={6}
                    placeholder="654321"
                    value={admin2faCode}
                    onChange={(e) => setAdmin2faCode(e.target.value.replace(/\D/g, ''))}
                    className="w-full text-center tracking-[0.4em] px-4 py-3.5 bg-cream/50 border border-border rounded-2xl text-ink font-mono text-xl font-bold focus:outline-none focus:ring-2 focus:ring-deep-leaf focus:bg-white transition-all"
                    required
                    autoFocus
                  />
                  <div className="absolute inset-y-0 right-0 pr-4 flex items-center pointer-events-none">
                    <KeyRound className="w-5 h-5 text-muted" />
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between">
                <Button
                  type="button"
                  variant="secondary"
                  size="md"
                  onClick={() => setAdmin2faCode('654321')}
                >
                  {t('auth.autoFill')} (654321)
                </Button>
              </div>

              <Button
                type="submit"
                variant="primary"
                size="lg"
                className="w-full shadow-md"
                disabled={admin2faCode.length !== 6 || isLoading}
              >
                {isLoading ? t('auth.verifying') : t('auth.adminSubmit')}
              </Button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
