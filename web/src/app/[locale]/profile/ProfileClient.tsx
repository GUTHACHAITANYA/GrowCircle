'use client';

import React, { useState, useEffect } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { useRouter, usePathname } from 'next/navigation';
import { Header } from '@/components/ui/Header';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { SupportedLocale } from '@/components/ui/LanguageSwitcher';
import { useAuth, UserRole } from '@/lib/auth';
import { AuthModal } from '@/components/auth/AuthModal';
import {
  User as UserIcon,
  Phone,
  MapPin,
  Globe,
  Shield,
  Download,
  Trash2,
  LogOut,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Lock,
  Layers,
  Sparkles,
  Tractor,
  Store,
  Truck,
  Users,
} from 'lucide-react';

const SUPPORTED_LANGUAGES = [
  { code: 'te', label: 'తెలుగు (Telugu)' },
  { code: 'hi', label: 'हिन्दी (Hindi)' },
  { code: 'en', label: 'English' },
  { code: 'ta', label: 'தமிழ் (Tamil)' },
  { code: 'kn', label: 'ಕನ್ನಡ (Kannada)' },
  { code: 'ml', label: 'മലയാളം (Malayalam)' },
  { code: 'mr', label: 'मराठी (Marathi)' },
  { code: 'gu', label: 'ગુજરાતી (Gujarati)' },
  { code: 'bn', label: 'বাংলা (Bengali)' },
  { code: 'or', label: 'ଓଡ଼ିଆ (Odia)' },
  { code: 'pa', label: 'ਪੰਜਾਬੀ (Punjabi)' },
  { code: 'ur', label: 'اردو (Urdu)' },
];

export function ProfileClient() {
  const t = useTranslations();
  const locale = useLocale() as SupportedLocale;
  const router = useRouter();
  const pathname = usePathname();

  const {
    user,
    isAuthenticated,
    isLoading,
    updateProfile,
    exportMyData,
    deleteMyAccount,
    logout,
    logoutAll,
  } = useAuth();

  const [name, setName] = useState('');
  const [district, setDistrict] = useState('');
  const [preferredLang, setPreferredLang] = useState('te');
  const [consentLocation, setConsentLocation] = useState(true);

  const [isSaving, setIsSaving] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteConfirmationText, setDeleteConfirmationText] = useState('');

  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [showAuthModal, setShowAuthModal] = useState(false);

  useEffect(() => {
    if (user) {
      setName(user.name || '');
      setDistrict(user.district || 'Guntur');
      setPreferredLang(user.language || 'te');
      setConsentLocation(!!user.consent_at);
    }
  }, [user]);

  const handleLocaleChange = (newLocale: SupportedLocale) => {
    const segments = pathname.split('/');
    segments[1] = newLocale;
    router.push(segments.join('/'));
  };

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setFeedback(null);
    setIsSaving(true);
    try {
      await updateProfile({
        name: name.trim() || undefined,
        district: district.trim() || undefined,
        language: preferredLang,
        consent_location: consentLocation,
      });
      setFeedback({ type: 'success', message: 'Profile information updated successfully!' });
      setTimeout(() => setFeedback(null), 4000);
    } catch (err: unknown) {
      setFeedback({
        type: 'error',
        message: err instanceof Error ? err.message : 'Failed to update profile',
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleExportData = async () => {
    setFeedback(null);
    setIsExporting(true);
    try {
      const data = await exportMyData();
      const jsonStr = JSON.stringify(data, null, 2);
      const blob = new Blob([jsonStr], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `growcircle_dpdp_export_user_${user?.id || 'data'}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      setFeedback({
        type: 'success',
        message: 'Your complete data package was exported and downloaded under the DPDP Act 2023.',
      });
      setTimeout(() => setFeedback(null), 5000);
    } catch (err: unknown) {
      setFeedback({
        type: 'error',
        message: err instanceof Error ? err.message : 'Failed to export data',
      });
    } finally {
      setIsExporting(false);
    }
  };

  const handleLogoutAll = async () => {
    if (confirm('Are you sure you want to log out of all active devices? All other sessions will be terminated immediately.')) {
      await logoutAll();
      router.push(`/${locale}/prices`);
    }
  };

  const handleDeleteAccount = async () => {
    if (deleteConfirmationText.trim().toUpperCase() !== 'DELETE') {
      alert('Please type DELETE in the box to confirm account closure.');
      return;
    }

    setIsDeleting(true);
    try {
      await deleteMyAccount('User requested account deletion via profile page');
      setShowDeleteModal(false);
      router.push(`/${locale}/prices`);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to delete account');
      setIsDeleting(false);
    }
  };

  const getRoleDetails = (role: UserRole) => {
    switch (role) {
      case 'farmer':
        return {
          title: 'Verified Farmer (రైతు)',
          icon: <Tractor className="w-6 h-6 text-deep-leaf" />,
          desc: 'Direct selling privileges, farm diary ledger, nearest mandi price discovery.',
        };
      case 'buyer':
        return {
          title: 'Institutional / Retail Buyer',
          icon: <Store className="w-6 h-6 text-amber-700" />,
          desc: 'Post weekly produce requirements, direct farm bidding, and delivery dispute resolution.',
        };
      case 'driver':
        return {
          title: 'Registered Transporter (రవాణాదారు)',
          icon: <Truck className="w-6 h-6 text-blue-700" />,
          desc: 'Farm-to-mandi dispatch trips, OTP verification handshakes, transparent freight.',
        };
      case 'admin':
        return {
          title: 'System Administrator (2FA Protected)',
          icon: <Shield className="w-6 h-6 text-red-600" />,
          desc: 'Verification queues, audit logs, dispute mediation, and mandi hierarchy governance.',
        };
      default:
        return {
          title: 'Consumer Participant',
          icon: <Users className="w-6 h-6 text-purple-700" />,
          desc: 'Mandi price exploration and group direct buying.',
        };
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-cream">
      <Header
        currentLocale={locale}
        onSelectLocale={handleLocaleChange}
        activeNav="profile"
      />

      <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 space-y-8">
        {!isAuthenticated || !user ? (
          <div className="p-8 sm:p-12 bg-white rounded-3xl border border-border text-center space-y-6">
            <div className="w-16 h-16 rounded-3xl bg-deep-leaf/10 border border-deep-leaf/20 flex items-center justify-center mx-auto text-deep-leaf">
              <Lock className="w-8 h-8" />
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold text-ink">
              Sign In to View Your Profile
            </h1>
            <p className="text-muted text-sm max-w-md mx-auto">
              Manage your personal details, language preference, DPDP Act data rights, and role settings.
            </p>
            <Button
              variant="primary"
              size="lg"
              onClick={() => setShowAuthModal(true)}
            >
              Sign In with Phone OTP
            </Button>
            <AuthModal
              isOpen={showAuthModal}
              onClose={() => setShowAuthModal(false)}
            />
          </div>
        ) : (
          <>
            {/* Header Title */}
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-deep-leaf">
                Account Settings • ఖాతా వివరాలు
              </span>
              <h1 className="text-3xl sm:text-4xl font-extrabold text-ink tracking-tight mt-1">
                Profile & Data Controls
              </h1>
              <p className="text-sm text-muted mt-1">
                Manage your credentials, preferred language, district, and statutory DPDP Act data rights.
              </p>
            </div>

            {/* Notification alert */}
            {feedback && (
              <div
                className={`p-4 rounded-2xl border text-sm flex items-center gap-3 ${
                  feedback.type === 'success'
                    ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                    : 'bg-red-50 border-red-200 text-red-900'
                }`}
              >
                {feedback.type === 'success' ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
                ) : (
                  <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0" />
                )}
                <span>{feedback.message}</span>
              </div>
            )}

            {/* Role Card */}
            <div className="p-6 rounded-3xl bg-white border border-border shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <div className="p-3.5 rounded-2xl bg-cream border border-border flex-shrink-0">
                  {getRoleDetails(user.role).icon}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-extrabold text-ink text-lg">
                      {getRoleDetails(user.role).title}
                    </span>
                    <span className="px-2 py-0.5 rounded-md bg-deep-leaf/10 text-deep-leaf text-[10px] font-bold uppercase tracking-wider">
                      Active Role
                    </span>
                  </div>
                  <p className="text-xs text-muted mt-0.5 max-w-md">
                    {getRoleDetails(user.role).desc}
                  </p>
                </div>
              </div>

              {user.role === 'admin' && (
                <div className="px-3 py-1.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs font-bold flex items-center gap-2">
                  <Shield className="w-4 h-4 text-amber-600" />
                  <span>2FA {user.is_admin_2fa_verified ? 'Verified ✓' : 'Required'}</span>
                </div>
              )}
            </div>

            {/* Profile Form */}
            <form onSubmit={handleSaveProfile} className="space-y-6">
              <Card className="p-6 sm:p-8 space-y-6">
                <h2 className="text-lg font-bold text-ink flex items-center gap-2">
                  <UserIcon className="w-5 h-5 text-deep-leaf" />
                  <span>Personal Details</span>
                </h2>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                  {/* Phone (Immutable / Verified) */}
                  <div>
                    <label className="block text-xs font-bold text-ink uppercase tracking-wider mb-2">
                      Verified Phone Number (ఫోన్ సంఖ్య)
                    </label>
                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-muted font-bold text-sm">
                        +91
                      </div>
                      <input
                        type="text"
                        value={user.phone}
                        disabled
                        className="w-full pl-12 pr-10 py-3 bg-cream/70 border border-border rounded-xl text-ink font-mono font-bold text-sm cursor-not-allowed opacity-90"
                      />
                      <div className="absolute inset-y-0 right-0 pr-3.5 flex items-center pointer-events-none">
                        <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                      </div>
                    </div>
                    <span className="text-[11px] text-muted mt-1 block">
                      Phone verified via OTP. Logins require no passwords.
                    </span>
                  </div>

                  {/* Name */}
                  <div>
                    <label htmlFor="profile-name" className="block text-xs font-bold text-ink uppercase tracking-wider mb-2">
                      Full Name (పూర్తి పేరు)
                    </label>
                    <input
                      id="profile-name"
                      type="text"
                      placeholder="e.g. Venkata Subba Rao"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="w-full px-4 py-3 bg-white border border-border rounded-xl text-ink text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-deep-leaf"
                    />
                  </div>

                  {/* Preferred Language */}
                  <div>
                    <label htmlFor="profile-lang" className="block text-xs font-bold text-ink uppercase tracking-wider mb-2">
                      Preferred Language (భాష)
                    </label>
                    <div className="relative">
                      <select
                        id="profile-lang"
                        value={preferredLang}
                        onChange={(e) => setPreferredLang(e.target.value)}
                        className="w-full px-4 py-3 bg-white border border-border rounded-xl text-ink text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-deep-leaf appearance-none"
                      >
                        {SUPPORTED_LANGUAGES.map((lang) => (
                          <option key={lang.code} value={lang.code}>
                            {lang.label}
                          </option>
                        ))}
                      </select>
                      <div className="absolute inset-y-0 right-0 pr-3.5 flex items-center pointer-events-none text-muted">
                        <Globe className="w-4 h-4" />
                      </div>
                    </div>
                  </div>

                  {/* District */}
                  <div>
                    <label htmlFor="profile-district" className="block text-xs font-bold text-ink uppercase tracking-wider mb-2">
                      District (జిల్లా)
                    </label>
                    <div className="relative">
                      <input
                        id="profile-district"
                        type="text"
                        placeholder="e.g. Guntur"
                        value={district}
                        onChange={(e) => setDistrict(e.target.value)}
                        className="w-full px-4 py-3 bg-white border border-border rounded-xl text-ink text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-deep-leaf"
                      />
                      <div className="absolute inset-y-0 right-0 pr-3.5 flex items-center pointer-events-none text-muted">
                        <MapPin className="w-4 h-4" />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Location Consent */}
                <div className="pt-4 border-t border-border">
                  <label className="flex items-start gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={consentLocation}
                      onChange={(e) => setConsentLocation(e.target.checked)}
                      className="w-5 h-5 rounded-md text-deep-leaf focus:ring-deep-leaf mt-0.5 cursor-pointer accent-deep-leaf"
                    />
                    <div>
                      <span className="font-bold text-sm text-ink block">
                        Location Consent for Mandi Distance & Vehicle Dispatch
                      </span>
                      <span className="text-xs text-muted leading-relaxed block mt-0.5">
                        Under Section 6 of the DPDP Act 2023, granting location consent allows GrowCircle
                        to calculate exact road distance to nearest mandis and dispatch logistics. You may withdraw anytime.
                      </span>
                      {user.consent_at && (
                        <span className="text-[11px] text-emerald-700 font-semibold block mt-1">
                          Consent actively recorded on: {new Date(user.consent_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  </label>
                </div>

                <div className="flex justify-end pt-2">
                  <Button
                    type="submit"
                    variant="primary"
                    disabled={isSaving}
                  >
                    {isSaving ? 'Saving Changes...' : 'Save Profile Changes'}
                  </Button>
                </div>
              </Card>
            </form>

            {/* DPDP Act Data Rights & Security Section */}
            <Card className="p-6 sm:p-8 space-y-6">
              <div>
                <h2 className="text-lg font-bold text-ink flex items-center gap-2">
                  <Shield className="w-5 h-5 text-deep-leaf" />
                  <span>DPDP Act 2023 Rights & Device Security</span>
                </h2>
                <p className="text-xs text-muted mt-1">
                  GrowCircle is committed to statutory data portability, right to erasure, and full session control.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Export Data */}
                <div className="p-5 rounded-2xl bg-cream/40 border border-border flex flex-col justify-between space-y-4">
                  <div>
                    <div className="flex items-center gap-2 text-ink font-bold text-sm mb-1">
                      <Download className="w-4 h-4 text-deep-leaf" />
                      <span>Export My Personal Data</span>
                    </div>
                    <p className="text-xs text-muted leading-relaxed">
                      Download a complete, machine-readable JSON package of your profile, listings, farm diary, and trips under Section 11 of DPDP Act.
                    </p>
                  </div>
                  <Button
                    type="button"
                    variant="secondary"
                    size="md"
                    onClick={handleExportData}
                    disabled={isExporting}
                    className="w-full text-xs"
                  >
                    {isExporting ? 'Generating Package...' : 'Download My Data Package (JSON)'}
                  </Button>
                </div>

                {/* Log Out All Devices */}
                <div className="p-5 rounded-2xl bg-cream/40 border border-border flex flex-col justify-between space-y-4">
                  <div>
                    <div className="flex items-center gap-2 text-ink font-bold text-sm mb-1">
                      <LogOut className="w-4 h-4 text-amber-700" />
                      <span>Log Out of All Devices</span>
                    </div>
                    <p className="text-xs text-muted leading-relaxed">
                      Session version #{user.session_version}. Increments your server session version, invalidating all other phones and browser tokens.
                    </p>
                  </div>
                  <Button
                    type="button"
                    variant="secondary"
                    size="md"
                    onClick={handleLogoutAll}
                    className="w-full text-xs text-amber-800 hover:bg-amber-50"
                  >
                    Revoke All Device Sessions
                  </Button>
                </div>
              </div>

              {/* Danger Zone: Delete Account */}
              <div className="p-5 rounded-2xl bg-red-50/50 border border-red-200 space-y-3">
                <div className="flex items-center gap-2 text-red-900 font-bold text-sm">
                  <Trash2 className="w-4 h-4 text-red-600" />
                  <span>Right to Erasure • Delete My Account and Data</span>
                </div>
                <p className="text-xs text-red-800 leading-relaxed">
                  Permanently anonymize and erase your phone number, name, listings, and personal identifiers
                  under Section 12 of the DPDP Act 2023. This action is irreversible.
                </p>
                <Button
                  type="button"
                  variant="secondary"
                  size="md"
                  onClick={() => setShowDeleteModal(true)}
                  className="text-xs border-red-300 text-red-700 hover:bg-red-100"
                >
                  Delete My Account and Personal Data
                </Button>
              </div>
            </Card>

            {/* Delete Confirmation Modal */}
            {showDeleteModal && (
              <div
                role="dialog"
                aria-modal="true"
                aria-labelledby="delete-dialog-title"
                className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in"
              >
                <div className="bg-white rounded-3xl max-w-md w-full p-6 sm:p-8 space-y-5 border border-red-200 shadow-2xl">
                  <div className="w-12 h-12 rounded-2xl bg-red-100 text-red-600 flex items-center justify-center mx-auto">
                    <AlertTriangle className="w-6 h-6" />
                  </div>

                  <div className="text-center space-y-1">
                    <h3 id="delete-dialog-title" className="text-xl font-bold text-ink">
                      Permanently Delete Account?
                    </h3>
                    <p className="text-xs text-muted">
                      All your personal records, contact details, and listings will be completely anonymized under DPDP Act.
                    </p>
                  </div>

                  <div className="p-3 bg-red-50 rounded-xl text-xs text-red-800">
                    Type <strong>DELETE</strong> below to confirm.
                  </div>

                  <input
                    type="text"
                    placeholder="Type DELETE"
                    value={deleteConfirmationText}
                    onChange={(e) => setDeleteConfirmationText(e.target.value)}
                    className="w-full text-center px-4 py-3 border border-red-300 rounded-xl font-bold tracking-wider text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
                    autoFocus
                  />

                  <div className="flex gap-3">
                    <Button
                      type="button"
                      variant="secondary"
                      size="md"
                      onClick={() => setShowDeleteModal(false)}
                      className="flex-1"
                    >
                      Cancel
                    </Button>
                    <Button
                      type="button"
                      variant="primary"
                      size="md"
                      disabled={deleteConfirmationText.trim().toUpperCase() !== 'DELETE' || isDeleting}
                      onClick={handleDeleteAccount}
                      className="flex-1 bg-red-600 hover:bg-red-700 text-white"
                    >
                      {isDeleting ? 'Deleting...' : 'Confirm Deletion'}
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
