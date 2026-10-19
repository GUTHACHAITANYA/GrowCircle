'use client';

import React, { useState } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { useRouter, usePathname } from 'next/navigation';
import {
  Header,
  Button,
  Card,
  Chip,
  SupportedLocale,
} from '@/components/ui';
import {
  ShieldCheck,
  CheckCircle2,
  XCircle,
  FileText,
  Lock,
  Unlock,
  Building,
  UserCheck,
  AlertTriangle,
  Eye,
  Check,
  X,
  Clock,
  Sparkles,
  Truck,
  AlertCircle,
  Camera,
  FileCheck,
  Scale,
  Calendar,
  PhoneCall,
  MapPin,
  Activity,
  Database,
  History,
} from 'lucide-react';
import { RoleGuard } from '@/components/auth/RoleGuard';
import { isDemoMode, isProductionMode } from '@/lib/appMode';
import { GroundTruthSection } from '@/components/admin/GroundTruthSection';
import { MandiMasterSection } from '@/components/admin/MandiMasterSection';
import { DataHealthSection } from '@/components/admin/DataHealthSection';
import { AuditLogsSection } from '@/components/admin/AuditLogsSection';

interface BuyerVerificationRecord {
  id: number;
  userId: number;
  businessName: string;
  buyerType: 'institution' | 'retail_shop' | 'wholesaler' | 'hotel' | 'hostel';
  district: string;
  phone: string;
  encryptedGst: string;
  decryptedGst: string;
  encryptedDocRef: string;
  decryptedDocRef: string;
  submittedAt: string;
  status: 'pending' | 'verified' | 'rejected';
  rejectionReason?: string;
}

interface TransporterVerificationRecord {
  id: number;
  name: string;
  phone: string;
  vehicleType: 'goods_auto' | 'mini_truck' | 'large_truck';
  vehicleModel: string;
  capacityKg: number;
  licenseNumber: string;
  licenseExpiry: string;
  rcNumber: string;
  rcExpiry: string;
  insuranceNumber: string;
  insuranceExpiry: string;
  fitnessNumber: string;
  fitnessExpiry: string;
  serviceArea: string;
  status: 'pending' | 'verified' | 'rejected';
  hasExpiredDoc: boolean;
  expiredDocReason?: string;
  rejectionReason?: string;
  submittedAt: string;
}

interface DisputedTripRecord {
  tripId: string;
  dealId: number;
  farmerName: string;
  buyerName: string;
  driverName: string;
  crop: string;
  quantityKg: number;
  guideRate: number;
  status: 'disputed' | 'resolved';
  complaintReason: string;
  damagePhotoUrl: string;
  resolutionNotes?: string;
  reportedAt: string;
}

const INITIAL_BUYER_APPLICATIONS: BuyerVerificationRecord[] = [
  {
    id: 1,
    userId: 10,
    businessName: 'Acharya Nagarjuna University Hostel',
    buyerType: 'institution',
    district: 'Guntur',
    phone: '+919988776655',
    encryptedGst: 'gAAAAABn...[AES-256 Fernet Ciphertext]...==',
    decryptedGst: '37AAAAA0000A1Z5',
    encryptedDocRef: 'gAAAAABn...[AES-256 Fernet Ciphertext]...==',
    decryptedDocRef: 'anu_hostel_procurement_license_2026.pdf',
    submittedAt: 'Today, 09:15 AM',
    status: 'pending',
  },
  {
    id: 2,
    userId: 11,
    businessName: 'Sri Venkateswara Supermarket & Fresh Mart',
    buyerType: 'retail_shop',
    district: 'Guntur',
    phone: '+919876543210',
    encryptedGst: 'gAAAAABn...[AES-256 Fernet Ciphertext]...==',
    decryptedGst: '37AABCS1429B1Z8',
    encryptedDocRef: 'gAAAAABn...[AES-256 Fernet Ciphertext]...==',
    decryptedDocRef: 'shop_and_establishment_act_reg_5829.pdf',
    submittedAt: 'Today, 10:45 AM',
    status: 'pending',
  },
  {
    id: 3,
    userId: 12,
    businessName: 'Krishna Valley School Dining Hall',
    buyerType: 'institution',
    district: 'Krishna',
    phone: '+919123456789',
    encryptedGst: 'gAAAAABn...[AES-256 Fernet Ciphertext]...==',
    decryptedGst: '37KVSDH8821C1Z3',
    encryptedDocRef: 'gAAAAABn...[AES-256 Fernet Ciphertext]...==',
    decryptedDocRef: 'krishna_district_fssai_cert.pdf',
    submittedAt: 'Yesterday, 04:30 PM',
    status: 'verified',
  },
];

const INITIAL_TRANSPORTERS: TransporterVerificationRecord[] = [
  {
    id: 1,
    name: 'Venkat Rao',
    phone: '+919848099881',
    vehicleType: 'goods_auto',
    vehicleModel: 'Tata Ace Gold (Diesel)',
    capacityKg: 750,
    licenseNumber: 'AP07-2019-0091218',
    licenseExpiry: '2028-11-14',
    rcNumber: 'AP 07 TA 4120',
    rcExpiry: '2035-06-22',
    insuranceNumber: 'BAJAJ-ALL-88912-COMM',
    insuranceExpiry: '2026-12-19',
    fitnessNumber: 'AP-FIT-2025-4109',
    fitnessExpiry: '2027-08-15',
    serviceArea: 'Guntur - Tenali - Mangalagiri (45 km)',
    status: 'pending',
    hasExpiredDoc: false,
    submittedAt: 'Today, 08:30 AM',
  },
  {
    id: 2,
    name: 'Satyanarayana Murthy',
    phone: '+919440122334',
    vehicleType: 'mini_truck',
    vehicleModel: 'Mahindra Bolero Maxi Truck Plus',
    capacityKg: 1250,
    licenseNumber: 'AP07-2015-0044129',
    licenseExpiry: '2030-04-10',
    rcNumber: 'AP 07 TB 8841',
    rcExpiry: '2033-09-12',
    insuranceNumber: 'ICICI-LOMB-33910-COMM',
    insuranceExpiry: '2027-01-20',
    fitnessNumber: 'AP-FIT-2024-9912',
    fitnessExpiry: '2027-03-30',
    serviceArea: 'Guntur & Krishna Districts (60 km)',
    status: 'verified',
    hasExpiredDoc: false,
    submittedAt: 'Yesterday, 02:15 PM',
  },
  {
    id: 3,
    name: 'Ravi Teja Pandu',
    phone: '+919988112244',
    vehicleType: 'goods_auto',
    vehicleModel: 'Piaggio Ape Auto Xtra',
    capacityKg: 480,
    licenseNumber: 'AP07-2020-0019283',
    licenseExpiry: '2029-07-20',
    rcNumber: 'AP 07 TC 1102',
    rcExpiry: '2034-01-18',
    insuranceNumber: 'TATA-AIG-99120-COMM',
    insuranceExpiry: '2027-05-10',
    fitnessNumber: 'AP-FIT-2023-1102',
    fitnessExpiry: '2026-02-10', // EXPIRED!
    serviceArea: 'Tenali Rural & Urban (25 km)',
    status: 'pending',
    hasExpiredDoc: true,
    expiredDocReason: 'Fitness Certificate expired on 2026-02-10. Hidden from dispatch.',
    submittedAt: 'Today, 11:20 AM',
  },
];

const INITIAL_DISPUTES: DisputedTripRecord[] = [
  {
    tripId: 'TRIP-8094',
    dealId: 901,
    farmerName: 'Venkateswarlu K.',
    buyerName: 'Acharya Nagarjuna University Hostel',
    driverName: 'Ravi Teja Pandu (Goods Auto)',
    crop: 'Banana (Robusta, Grade B)',
    quantityKg: 500,
    guideRate: 420,
    status: 'disputed',
    complaintReason:
      '3 Crates of bananas crushed on the bottom tier during transit over rough road. Approx 60 kg bruised and unserviceable for dining hall.',
    damagePhotoUrl: '/docs/damaged_crates_sample.png',
    reportedAt: 'Today, 01:15 PM',
  },
];

export function AdminClient() {
  const t = useTranslations();
  const locale = useLocale() as SupportedLocale;
  const router = useRouter();
  const pathname = usePathname();

  // Top Section Switcher
  const [activeSection, setActiveSection] = useState<
    'buyers' | 'transporters' | 'disputes' | 'data_health' | 'audit_logs' | 'ground_truth' | 'mandi_master'
  >('buyers');

  // Buyer applications state
  const [buyerApplications, setBuyerApplications] = useState<BuyerVerificationRecord[]>(isDemoMode ? INITIAL_BUYER_APPLICATIONS : []);
  const [filterBuyerStatus, setFilterBuyerStatus] = useState<'all' | 'pending' | 'verified'>('pending');
  const [revealedProofId, setRevealedProofId] = useState<number | null>(null);

  // Transporter state
  const [transporters, setTransporters] = useState<TransporterVerificationRecord[]>(isDemoMode ? INITIAL_TRANSPORTERS : []);
  const [inspectingTransporterId, setInspectingTransporterId] = useState<number | null>(null);

  // Disputes state
  const [disputes, setDisputes] = useState<DisputedTripRecord[]>(isDemoMode ? INITIAL_DISPUTES : []);
  const [resolvingTripId, setResolvingTripId] = useState<string | null>(null);
  const [resolutionText, setResolutionText] = useState(
    'Farmer and buyer mutually accepted 15% credit note (₹1,800) for damaged fruit. Driver freight of ₹420 cleared in full.'
  );

  // Rejection modal
  const [rejectingTarget, setRejectingTarget] = useState<{ type: 'buyer' | 'transporter'; id: number } | null>(null);
  const [rejectionNotes, setRejectionNotes] = useState('Document unreadable or invalid credentials.');

  // Toast
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  const handleLocaleChange = (newLocale: SupportedLocale) => {
    const segments = pathname.split('/');
    segments[1] = newLocale;
    router.push(segments.join('/'));
  };

  // Buyer actions
  const handleApproveBuyer = (appId: number) => {
    setBuyerApplications(
      buyerApplications.map((app) =>
        app.id === appId ? { ...app, status: 'verified' } : app
      )
    );
    showToast(`Buyer #${appId} verified! Account granted direct bidding & group supply access.`);
  };

  // Transporter actions
  const handleApproveTransporter = (transporterId: number) => {
    const target = transporters.find((t) => t.id === transporterId);
    if (target?.hasExpiredDoc) {
      showToast('Cannot approve driver: One or more documents are expired! Require renewal first.');
      return;
    }
    setTransporters(
      transporters.map((t) =>
        t.id === transporterId ? { ...t, status: 'verified' } : t
      )
    );
    showToast(`Transporter #${transporterId} approved! Driver is now active on 3-driver load radar.`);
  };

  // Dispute actions
  const handleResolveDispute = () => {
    if (!resolvingTripId) return;
    setDisputes(
      disputes.map((d) =>
        d.tripId === resolvingTripId
          ? { ...d, status: 'resolved', resolutionNotes: resolutionText }
          : d
      )
    );
    setResolvingTripId(null);
    showToast(`Trip ${resolvingTripId} dispute resolved with settlement terms recorded.`);
  };

  const handleConfirmReject = () => {
    if (!rejectingTarget) return;
    if (rejectingTarget.type === 'buyer') {
      setBuyerApplications(
        buyerApplications.map((app) =>
          app.id === rejectingTarget.id
            ? { ...app, status: 'rejected', rejectionReason: rejectionNotes }
            : app
        )
      );
      showToast(`Buyer application #${rejectingTarget.id} rejected.`);
    } else {
      setTransporters(
        transporters.map((t) =>
          t.id === rejectingTarget.id
            ? { ...t, status: 'rejected', rejectionReason: rejectionNotes }
            : t
        )
      );
      showToast(`Transporter application #${rejectingTarget.id} rejected.`);
    }
    setRejectingTarget(null);
  };

  const pendingBuyers = buyerApplications.filter((a) => a.status === 'pending').length;
  const pendingTransporters = transporters.filter((t) => t.status === 'pending').length;
  const activeDisputes = disputes.filter((d) => d.status === 'disputed').length;

  return (
    <div className="min-h-screen flex flex-col bg-cream">
      <Header
        currentLocale={locale}
        onSelectLocale={handleLocaleChange}
        brandName={t('brand.name')}
        activeNav="admin"
      />

      {/* Floating Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-deep-leaf text-white px-5 py-3 rounded-2xl shadow-xl flex items-center gap-3 animate-slide-up border border-white/20">
          <CheckCircle2 className="w-5 h-5 text-harvest-gold flex-shrink-0" />
          <span className="text-sm font-semibold">{toastMessage}</span>
        </div>
      )}

      <RoleGuard
        allowedRoles={['admin']}
        require2FA={true}
        fallbackTitle="Administrator Access Required"
        fallbackMessage="This administrative console controls buyer/driver verification queues, delivery dispute arbitrations, and system data health. Admin credentials and 2FA are required."
      >
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Admin Header */}
        <div className="bg-white rounded-3xl border border-border p-6 sm:p-8 shadow-sm mb-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="flex items-start gap-4">
            <div className="w-14 h-14 rounded-2xl bg-deep-leaf/10 text-deep-leaf flex items-center justify-center flex-shrink-0">
              <ShieldCheck className="w-7 h-7" />
            </div>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <h1 className="font-heading text-2xl sm:text-3xl font-extrabold text-ink">
                  Admin Verification &amp; Mediation
                </h1>
                <Chip variant="primary" size="sm">
                  DPDP Act 2023 Aligned
                </Chip>
              </div>
              <p className="text-sm text-muted">
                Inspect encrypted buyer records, verify transporter vehicle documents with auto-expiry checks, and arbitrate delivery disputes.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            <div className="bg-cream px-3.5 py-2 rounded-2xl border border-border text-center">
              <span className="text-[11px] text-muted block">Pending Buyers</span>
              <span className="text-xl font-extrabold text-amber">{pendingBuyers}</span>
            </div>
            <div className="bg-cream px-3.5 py-2 rounded-2xl border border-border text-center">
              <span className="text-[11px] text-muted block">Pending Drivers</span>
              <span className="text-xl font-extrabold text-deep-leaf">{pendingTransporters}</span>
            </div>
            <div className="bg-cream px-3.5 py-2 rounded-2xl border border-border text-center">
              <span className="text-[11px] text-muted block">Open Disputes</span>
              <span className="text-xl font-extrabold text-danger">{activeDisputes}</span>
            </div>
          </div>
        </div>

        {/* SECTION TABS SWITCHER */}
        <div className="flex border-b border-border mb-6 gap-2 sm:gap-6 overflow-x-auto pb-1">
          <button
            onClick={() => setActiveSection('buyers')}
            className={`pb-3 px-2 text-sm sm:text-base font-semibold transition-all border-b-2 whitespace-nowrap flex items-center gap-2 ${
              activeSection === 'buyers'
                ? 'border-deep-leaf text-deep-leaf'
                : 'border-transparent text-muted hover:text-ink'
            }`}
          >
            <Building className="w-4 h-4" />
            <span>Buyer Verification</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-border text-ink font-bold">
              {buyerApplications.length}
            </span>
          </button>

          <button
            onClick={() => setActiveSection('transporters')}
            className={`pb-3 px-2 text-sm sm:text-base font-semibold transition-all border-b-2 whitespace-nowrap flex items-center gap-2 ${
              activeSection === 'transporters'
                ? 'border-deep-leaf text-deep-leaf'
                : 'border-transparent text-muted hover:text-ink'
            }`}
          >
            <Truck className="w-4 h-4" />
            <span>Transporters Queue</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-deep-leaf text-white font-bold">
              {transporters.length}
            </span>
          </button>

          <button
            onClick={() => setActiveSection('disputes')}
            className={`pb-3 px-2 text-sm sm:text-base font-semibold transition-all border-b-2 whitespace-nowrap flex items-center gap-2 ${
              activeSection === 'disputes'
                ? 'border-deep-leaf text-deep-leaf'
                : 'border-transparent text-muted hover:text-ink'
            }`}
          >
            <Scale className="w-4 h-4" />
            <span>Delivery Disputes</span>
            {activeDisputes > 0 && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-danger text-white font-bold">
                {activeDisputes}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveSection('ground_truth')}
            className={`pb-3 px-2 text-sm sm:text-base font-semibold transition-all border-b-2 whitespace-nowrap flex items-center gap-2 ${
              activeSection === 'ground_truth'
                ? 'border-deep-leaf text-deep-leaf'
                : 'border-transparent text-muted hover:text-ink'
            }`}
          >
            <PhoneCall className="w-4 h-4" />
            <span>Ground-Truth Phone Audits</span>
            <Chip variant="accent" size="sm">R1 Validation</Chip>
          </button>

          <button
            onClick={() => setActiveSection('mandi_master')}
            className={`pb-3 px-2 text-sm sm:text-base font-semibold transition-all border-b-2 whitespace-nowrap flex items-center gap-2 ${
              activeSection === 'mandi_master'
                ? 'border-deep-leaf text-deep-leaf'
                : 'border-transparent text-muted hover:text-ink'
            }`}
          >
            <MapPin className="w-4 h-4" />
            <span>Mandi Master &amp; LGD Hierarchy</span>
            <Chip variant="primary" size="sm">R2</Chip>
          </button>

          <button
            onClick={() => setActiveSection('data_health')}
            className={`pb-3 px-2 text-sm sm:text-base font-semibold transition-all border-b-2 whitespace-nowrap flex items-center gap-2 ${
              activeSection === 'data_health'
                ? 'border-deep-leaf text-deep-leaf'
                : 'border-transparent text-muted hover:text-ink'
            }`}
          >
            <Activity className="w-4 h-4" />
            <span>Data Health</span>
            <Chip variant="default" size="sm">Live</Chip>
          </button>

          <button
            onClick={() => setActiveSection('audit_logs')}
            className={`pb-3 px-2 text-sm sm:text-base font-semibold transition-all border-b-2 whitespace-nowrap flex items-center gap-2 ${
              activeSection === 'audit_logs'
                ? 'border-deep-leaf text-deep-leaf'
                : 'border-transparent text-muted hover:text-ink'
            }`}
          >
            <History className="w-4 h-4" />
            <span>Security Audit Trail</span>
            <Chip variant="accent" size="sm">DPDP</Chip>
          </button>
        </div>

        {/* ===================== SECTION 1: BUYER VERIFICATION ===================== */}
        {activeSection === 'buyers' && (
          <div className="space-y-6">
            <div className="bg-deep-leaf/5 border border-deep-leaf/20 rounded-2xl p-4 flex items-start gap-3 text-xs text-ink leading-relaxed">
              <Lock className="w-4 h-4 text-deep-leaf flex-shrink-0 mt-0.5" />
              <div>
                <strong className="text-deep-leaf">Cryptographic Proof Protection:</strong> All buyer GST numbers and document references are encrypted at rest with Fernet AES-256 derived from the platform master key.
              </div>
            </div>

            <div className="flex items-center justify-between flex-wrap gap-3">
              <div className="flex items-center gap-2">
                <Button
                  variant={filterBuyerStatus === 'pending' ? 'primary' : 'secondary'}
                  size="md"
                  className="text-xs px-3 py-1.5 h-9 min-h-[36px]"
                  onClick={() => setFilterBuyerStatus('pending')}
                >
                  Pending Approval ({pendingBuyers})
                </Button>
                <Button
                  variant={filterBuyerStatus === 'verified' ? 'primary' : 'secondary'}
                  size="md"
                  className="text-xs px-3 py-1.5 h-9 min-h-[36px]"
                  onClick={() => setFilterBuyerStatus('verified')}
                >
                  Verified ({buyerApplications.filter((a) => a.status === 'verified').length})
                </Button>
                <Button
                  variant={filterBuyerStatus === 'all' ? 'primary' : 'secondary'}
                  size="md"
                  className="text-xs px-3 py-1.5 h-9 min-h-[36px]"
                  onClick={() => setFilterBuyerStatus('all')}
                >
                  All Records ({buyerApplications.length})
                </Button>
              </div>
            </div>

            <div className="space-y-4">
              {buyerApplications
                .filter((app) => (filterBuyerStatus === 'all' ? true : app.status === filterBuyerStatus))
                .map((app) => {
                  const isRevealed = revealedProofId === app.id;
                  return (
                    <Card key={app.id} className="p-6 bg-white border border-border shadow-sm">
                      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-1">
                            <h3 className="font-heading text-lg font-bold text-ink">
                              {app.businessName}
                            </h3>
                            <Chip variant="default" size="sm">
                              {app.buyerType.toUpperCase()}
                            </Chip>
                            <Chip
                              variant={
                                app.status === 'verified'
                                  ? 'primary'
                                  : app.status === 'rejected'
                                  ? 'danger'
                                  : 'accent'
                              }
                              size="sm"
                            >
                              {app.status.toUpperCase()}
                            </Chip>
                          </div>
                          <p className="text-xs text-muted mb-4">
                            District: {app.district} &bull; Contact: {app.phone} &bull; Submitted {app.submittedAt}
                          </p>

                          <div className="bg-cream p-4 rounded-2xl border border-border text-xs space-y-2">
                            <div className="flex items-center justify-between">
                              <span className="font-semibold text-muted">GST / Proof:</span>
                              <span className="font-mono font-bold text-ink">
                                {isRevealed ? app.decryptedGst : app.encryptedGst}
                              </span>
                            </div>
                            <div className="flex items-center justify-between">
                              <span className="font-semibold text-muted">Document File:</span>
                              <span className="font-mono text-ink">
                                {isRevealed ? app.decryptedDocRef : app.encryptedDocRef}
                              </span>
                            </div>
                          </div>
                        </div>

                        <div className="flex flex-col sm:flex-row items-center gap-3">
                          <Button
                            variant="secondary"
                            size="md"
                            className="text-xs"
                            onClick={() => setRevealedProofId(isRevealed ? null : app.id)}
                            leftIcon={isRevealed ? <Lock className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                          >
                            {isRevealed ? 'Hide Proof' : 'Decrypt & Inspect'}
                          </Button>

                          {app.status === 'pending' && (
                            <>
                              <Button
                                variant="primary"
                                size="md"
                                className="text-xs"
                                onClick={() => handleApproveBuyer(app.id)}
                                leftIcon={<Check className="w-4 h-4" />}
                              >
                                Approve Buyer
                              </Button>
                              <Button
                                variant="secondary"
                                size="md"
                                className="text-xs text-danger"
                                onClick={() => setRejectingTarget({ type: 'buyer', id: app.id })}
                                leftIcon={<X className="w-4 h-4" />}
                              >
                                Reject
                              </Button>
                            </>
                          )}
                        </div>
                      </div>
                    </Card>
                  );
                })}
            </div>
          </div>
        )}

        {/* ===================== SECTION 2: TRANSPORTER VERIFICATION ===================== */}
        {activeSection === 'transporters' && (
          <div className="space-y-6">
            <div className="bg-white rounded-3xl border border-border p-6 shadow-sm">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Truck className="w-6 h-6 text-deep-leaf" />
                  <h2 className="font-heading text-xl font-bold text-ink">
                    Transporter Fleet Document Verification
                  </h2>
                </div>
                <span className="text-xs text-deep-leaf font-bold bg-deep-leaf/10 px-3 py-1 rounded-full">
                  Automatic Expiry Check Enabled
                </span>
              </div>
              <p className="text-xs text-muted leading-relaxed">
                Review Driving Licence, Registration Certificate (RC), Commercial Vehicle Insurance, and Fitness Certificates. Vehicles with expired documents are strictly forbidden from receiving load dispatches.
              </p>
            </div>

            <div className="space-y-4">
              {transporters.map((driver) => {
                const isInspecting = inspectingTransporterId === driver.id;

                return (
                  <Card key={driver.id} className="p-6 bg-white border border-border shadow-sm">
                    <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 pb-4 border-b border-border">
                      <div>
                        <div className="flex items-center gap-3 flex-wrap">
                          <h3 className="font-heading text-lg font-bold text-ink">
                            {driver.name}
                          </h3>
                          <Chip variant="default" size="sm">
                            {driver.vehicleModel}
                          </Chip>
                          <Chip
                            variant={
                              driver.status === 'verified'
                                ? 'primary'
                                : driver.status === 'rejected'
                                ? 'danger'
                                : 'accent'
                            }
                            size="sm"
                          >
                            {driver.status.toUpperCase()}
                          </Chip>
                          {driver.hasExpiredDoc && (
                            <Chip variant="danger" size="sm">
                              DOCUMENTS EXPIRED
                            </Chip>
                          )}
                        </div>
                        <p className="text-xs text-muted mt-1">
                          Phone: <strong>{driver.phone}</strong> &bull; Capacity: <strong>{driver.capacityKg} kg</strong> &bull; Area: <strong>{driver.serviceArea}</strong> &bull; Submitted: {driver.submittedAt}
                        </p>
                      </div>

                      <div className="flex items-center gap-3">
                        <Button
                          variant="secondary"
                          size="md"
                          className="text-xs"
                          onClick={() => setInspectingTransporterId(isInspecting ? null : driver.id)}
                          leftIcon={<FileCheck className="w-4 h-4 text-deep-leaf" />}
                        >
                          {isInspecting ? 'Collapse Docs' : 'Inspect Credentials'}
                        </Button>

                        {driver.status === 'pending' && (
                          <>
                            <Button
                              variant="primary"
                              size="md"
                              className="text-xs"
                              disabled={driver.hasExpiredDoc}
                              onClick={() => handleApproveTransporter(driver.id)}
                              leftIcon={<Check className="w-4 h-4" />}
                            >
                              Approve Driver
                            </Button>
                            <Button
                              variant="secondary"
                              size="md"
                              className="text-xs text-danger"
                              onClick={() => setRejectingTarget({ type: 'transporter', id: driver.id })}
                              leftIcon={<X className="w-4 h-4" />}
                            >
                              Reject
                            </Button>
                          </>
                        )}
                      </div>
                    </div>

                    {/* Expiry Warning Callout */}
                    {driver.hasExpiredDoc && (
                      <div className="mt-4 bg-danger/10 text-danger border border-danger/20 rounded-xl p-3 text-xs flex items-center gap-2 font-bold">
                        <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                        <span>{driver.expiredDocReason}</span>
                      </div>
                    )}

                    {/* Document Inspection Drawer */}
                    {isInspecting && (
                      <div className="mt-4 pt-4 border-t border-border/80 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
                        {/* Driving Licence */}
                        <div className="bg-cream p-3 rounded-xl border border-border">
                          <span className="font-bold text-ink block mb-0.5">Driving Licence</span>
                          <span className="font-mono text-muted block mb-1">{driver.licenseNumber}</span>
                          <span className="text-deep-leaf font-bold">Expires: {driver.licenseExpiry}</span>
                        </div>

                        {/* Registration Certificate */}
                        <div className="bg-cream p-3 rounded-xl border border-border">
                          <span className="font-bold text-ink block mb-0.5">RC Certificate</span>
                          <span className="font-mono text-muted block mb-1">{driver.rcNumber}</span>
                          <span className="text-deep-leaf font-bold">Expires: {driver.rcExpiry}</span>
                        </div>

                        {/* Commercial Insurance */}
                        <div className="bg-cream p-3 rounded-xl border border-border">
                          <span className="font-bold text-ink block mb-0.5">Commercial Insurance</span>
                          <span className="font-mono text-muted block mb-1">{driver.insuranceNumber}</span>
                          <span className="text-deep-leaf font-bold">Expires: {driver.insuranceExpiry}</span>
                        </div>

                        {/* Fitness Certificate */}
                        <div
                          className={`p-3 rounded-xl border ${
                            driver.fitnessExpiry < '2026-10-13'
                              ? 'bg-danger/10 border-danger/30'
                              : 'bg-cream border-border'
                          }`}
                        >
                          <span className="font-bold text-ink block mb-0.5">Fitness Certificate</span>
                          <span className="font-mono text-muted block mb-1">{driver.fitnessNumber}</span>
                          <span
                            className={`font-bold ${
                              driver.fitnessExpiry < '2026-10-13' ? 'text-danger' : 'text-deep-leaf'
                            }`}
                          >
                            Expires: {driver.fitnessExpiry}
                          </span>
                        </div>
                      </div>
                    )}
                  </Card>
                );
              })}
            </div>
          </div>
        )}

        {/* ===================== SECTION 3: DELIVERY DISPUTES ===================== */}
        {activeSection === 'disputes' && (
          <div className="space-y-6">
            <div className="bg-white rounded-3xl border border-border p-6 shadow-sm">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Scale className="w-6 h-6 text-deep-leaf" />
                  <h2 className="font-heading text-xl font-bold text-ink">
                    Delivery Disputes &amp; Damaged Produce Arbitration
                  </h2>
                </div>
                <Chip variant="danger" size="sm">
                  Mandatory Photo Evidence
                </Chip>
              </div>
              <p className="text-xs text-muted leading-relaxed">
                When a buyer accepts delivery with a complaint or rejects damaged crates, GrowCircle requires photographic proof taken directly at physical delivery before withholding OTP release. Administrators arbitrate disputes impartially.
              </p>
            </div>

            <div className="space-y-4">
              {disputes.map((dispute) => (
                <Card key={dispute.tripId} className="p-6 bg-white border border-border shadow-sm">
                  <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-6 pb-5 border-b border-border">
                    <div className="space-y-2 flex-1">
                      <div className="flex items-center gap-2.5">
                        <span className="font-mono text-sm font-bold text-danger bg-danger/10 px-2.5 py-1 rounded-lg">
                          {dispute.tripId}
                        </span>
                        <h3 className="font-heading text-lg font-bold text-ink">
                          {dispute.crop} ({dispute.quantityKg} kg)
                        </h3>
                        <Chip
                          variant={dispute.status === 'resolved' ? 'primary' : 'danger'}
                          size="sm"
                        >
                          {dispute.status.toUpperCase()}
                        </Chip>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs pt-1">
                        <div>
                          <span className="text-muted block">Farmer</span>
                          <strong className="text-ink">{dispute.farmerName}</strong>
                        </div>
                        <div>
                          <span className="text-muted block">Buyer (Complainant)</span>
                          <strong className="text-ink">{dispute.buyerName}</strong>
                        </div>
                        <div>
                          <span className="text-muted block">Transporter</span>
                          <strong className="text-ink">{dispute.driverName}</strong>
                        </div>
                      </div>

                      <div className="bg-danger/5 border border-danger/20 rounded-2xl p-4 text-xs">
                        <strong className="text-danger block mb-1">
                          Buyer Inspection Complaint Note:
                        </strong>
                        <p className="text-ink leading-relaxed">
                          &quot;{dispute.complaintReason}&quot;
                        </p>
                      </div>

                      {dispute.resolutionNotes && (
                        <div className="bg-deep-leaf/10 border border-deep-leaf/20 rounded-2xl p-4 text-xs">
                          <strong className="text-deep-leaf block mb-1">
                            Mutual Settlement Record:
                          </strong>
                          <p className="text-ink leading-relaxed">
                            {dispute.resolutionNotes}
                          </p>
                        </div>
                      )}
                    </div>

                    {/* Photographic Proof Card */}
                    <div className="bg-cream rounded-2xl p-4 border border-border flex flex-col items-center text-center w-full lg:w-64 flex-shrink-0">
                      <div className="w-10 h-10 rounded-full bg-danger/10 text-danger flex items-center justify-center mb-2">
                        <Camera className="w-5 h-5" />
                      </div>
                      <span className="text-xs font-bold text-ink block">
                        Mandatory Proof Upload
                      </span>
                      <span className="text-[10px] text-muted mb-3">
                        Captured at Delivery Gate
                      </span>

                      <div className="w-full h-32 bg-ink/5 rounded-xl border border-dashed border-border flex items-center justify-center text-muted text-xs p-2">
                        <span>[Damage Photo: Crushed Banana Crates Timestamped 2026-10-13 13:12 IST]</span>
                      </div>
                    </div>
                  </div>

                  <div className="pt-4 flex items-center justify-between flex-wrap gap-4">
                    <span className="text-xs text-muted">
                      Agreed Freight Guide Rate: <strong>₹{dispute.guideRate}</strong> &bull; Reported: {dispute.reportedAt}
                    </span>

                    {dispute.status === 'disputed' && (
                      <Button
                        variant="primary"
                        size="md"
                        onClick={() => setResolvingTripId(dispute.tripId)}
                        leftIcon={<Check className="w-4 h-4" />}
                      >
                        Arbitrate &amp; Resolve Dispute
                      </Button>
                    )}
                  </div>
                </Card>
              ))}
            </div>
          </div>
        )}

        {/* ===================== SECTION 4: GROUND TRUTH VALIDATION ===================== */}
        {activeSection === 'ground_truth' && (
          <GroundTruthSection locale={locale} />
        )}

        {/* ===================== SECTION 5: MANDI MASTER & LGD HIERARCHY (R2) ===================== */}
        {activeSection === 'mandi_master' && (
          <MandiMasterSection />
        )}

        {/* ===================== SECTION 6: DATA HEALTH (R6) ===================== */}
        {activeSection === 'data_health' && (
          <DataHealthSection />
        )}

        {/* ===================== SECTION 7: AUDIT LOGS (R6) ===================== */}
        {activeSection === 'audit_logs' && (
          <AuditLogsSection />
        )}
        </main>
      </RoleGuard>

      {/* RESOLUTION MODAL */}
      {resolvingTripId && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-lg w-full p-6 shadow-2xl border border-border animate-scale-in">
            <h3 className="font-heading text-xl font-bold text-ink mb-2">
              Record Dispute Settlement Terms
            </h3>
            <p className="text-xs text-muted mb-4">
              Enter agreed settlement between farmer, buyer, and transporter for Trip #{resolvingTripId}.
            </p>

            <textarea
              value={resolutionText}
              onChange={(e) => setResolutionText(e.target.value)}
              rows={4}
              className="w-full p-3 rounded-xl border border-border text-xs text-ink mb-4 focus:ring-2 focus:ring-deep-leaf"
            />

            <div className="flex items-center gap-3">
              <Button
                variant="secondary"
                className="flex-1"
                onClick={() => setResolvingTripId(null)}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                className="flex-1"
                onClick={handleResolveDispute}
              >
                Save Resolution
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* REJECTION REASON MODAL */}
      {rejectingTarget && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl border border-border animate-scale-in">
            <h3 className="font-heading text-xl font-bold text-ink mb-2">
              Reject Application
            </h3>
            <p className="text-xs text-muted mb-4">
              Specify reason to notify applicant via WhatsApp &amp; SMS.
            </p>

            <textarea
              value={rejectionNotes}
              onChange={(e) => setRejectionNotes(e.target.value)}
              rows={3}
              className="w-full p-3 rounded-xl border border-border text-sm text-ink mb-4 focus:ring-2 focus:ring-danger"
            />

            <div className="flex items-center gap-3">
              <Button
                variant="secondary"
                className="flex-1"
                onClick={() => setRejectingTarget(null)}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                className="flex-1 bg-danger text-white hover:bg-danger/90"
                onClick={handleConfirmReject}
              >
                Confirm Reject
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
