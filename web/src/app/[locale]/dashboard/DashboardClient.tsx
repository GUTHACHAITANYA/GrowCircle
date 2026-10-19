'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useLocale } from 'next-intl';
import { useAuth, UserRole } from '@/lib/auth';
import { Header, Button, SupportedLocale } from '@/components/ui';
import { AuthModal } from '@/components/auth/AuthModal';
import { 
  Tractor, 
  Store, 
  Truck, 
  ShieldCheck, 
  TrendingUp, 
  ArrowRight,
  Loader2,
  Lock
} from 'lucide-react';

export const DashboardClient: React.FC = () => {
  const router = useRouter();
  const currentLocale = useLocale() as SupportedLocale;
  const { user, isAuthenticated, isLoading } = useAuth();
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [initialRole, setInitialRole] = useState<UserRole>('farmer');

  useEffect(() => {
    if (!isLoading && isAuthenticated && user) {
      switch (user.role) {
        case 'farmer':
          router.replace(`/${currentLocale}/farmer`);
          break;
        case 'buyer':
          router.replace(`/${currentLocale}/portal`);
          break;
        case 'driver':
          router.replace(`/${currentLocale}/driver`);
          break;
        case 'admin':
          router.replace(`/${currentLocale}/admin`);
          break;
        case 'consumer':
        default:
          router.replace(`/${currentLocale}/prices`);
          break;
      }
    }
  }, [isLoading, isAuthenticated, user, currentLocale, router]);

  const handleSelectLocale = (newLocale: SupportedLocale) => {
    router.push(`/${newLocale}/dashboard`);
  };

  const handleOpenAuth = (role: UserRole) => {
    setInitialRole(role);
    setIsAuthModalOpen(true);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-sand flex flex-col font-sans">
        <Header currentLocale={currentLocale} onSelectLocale={handleSelectLocale} />
        <div className="flex-1 flex flex-col items-center justify-center p-6 space-y-4">
          <Loader2 className="w-10 h-10 text-deep-leaf animate-spin" />
          <p className="text-sm font-semibold text-muted">Locating your role workspace...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-sand flex flex-col font-sans">
      <Header currentLocale={currentLocale} onSelectLocale={handleSelectLocale} />

      <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-6 py-12 flex flex-col items-center justify-center text-center">
        {!isAuthenticated ? (
          <div className="bg-white rounded-3xl border border-border p-8 sm:p-12 shadow-sm max-w-xl w-full space-y-6">
            <div className="w-16 h-16 rounded-2xl bg-deep-leaf/10 text-deep-leaf flex items-center justify-center mx-auto">
              <Lock className="w-8 h-8" />
            </div>
            <div>
              <h1 className="text-2xl sm:text-3xl font-extrabold text-ink font-heading">
                Sign In to Access Your Dashboard
              </h1>
              <p className="text-sm text-muted mt-2">
                GrowCircle provides dedicated workspaces for Farmers, Wholesale Buyers, Transporter Drivers, and Administrators.
              </p>
            </div>

            <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3">
              <Button
                variant="primary"
                size="lg"
                onClick={() => handleOpenAuth('farmer')}
                className="w-full sm:w-auto"
                rightIcon={<ArrowRight className="w-4 h-4" />}
              >
                Sign In with OTP
              </Button>
              <Button
                variant="secondary"
                size="lg"
                onClick={() => router.push(`/${currentLocale}/prices`)}
                className="w-full sm:w-auto"
              >
                View Price Today (No Login)
              </Button>
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-3xl border border-border p-8 sm:p-12 shadow-sm max-w-2xl w-full space-y-6 text-left">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-deep-leaf/10 text-deep-leaf flex items-center justify-center">
                {user?.role === 'farmer' && <Tractor className="w-6 h-6" />}
                {user?.role === 'buyer' && <Store className="w-6 h-6" />}
                {user?.role === 'driver' && <Truck className="w-6 h-6" />}
                {user?.role === 'admin' && <ShieldCheck className="w-6 h-6" />}
                {user?.role === 'consumer' && <TrendingUp className="w-6 h-6" />}
              </div>
              <div>
                <h2 className="text-xl font-bold text-ink">Welcome back, {user?.name || user?.phone}</h2>
                <span className="text-xs font-semibold uppercase tracking-wider text-deep-leaf">
                  Role: {user?.role}
                </span>
              </div>
            </div>

            <p className="text-sm text-muted">
              Redirecting you to your primary workspace. If you are not redirected automatically, click below:
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
              {user?.role === 'farmer' && (
                <Button
                  variant="primary"
                  onClick={() => router.push(`/${currentLocale}/farmer`)}
                  rightIcon={<ArrowRight className="w-4 h-4" />}
                >
                  Go to Farmer Hub
                </Button>
              )}
              {user?.role === 'buyer' && (
                <Button
                  variant="primary"
                  onClick={() => router.push(`/${currentLocale}/portal`)}
                  rightIcon={<ArrowRight className="w-4 h-4" />}
                >
                  Go to Buyer Portal
                </Button>
              )}
              {user?.role === 'driver' && (
                <Button
                  variant="primary"
                  onClick={() => router.push(`/${currentLocale}/driver`)}
                  rightIcon={<ArrowRight className="w-4 h-4" />}
                >
                  Go to Driver Hub
                </Button>
              )}
              {user?.role === 'admin' && (
                <Button
                  variant="primary"
                  onClick={() => router.push(`/${currentLocale}/admin`)}
                  rightIcon={<ArrowRight className="w-4 h-4" />}
                >
                  Go to Admin Ops Center
                </Button>
              )}
              <Button
                variant="secondary"
                onClick={() => router.push(`/${currentLocale}/profile`)}
              >
                Manage My Profile
              </Button>
            </div>
          </div>
        )}
      </main>

      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        initialRole={initialRole}
      />
    </div>
  );
};
