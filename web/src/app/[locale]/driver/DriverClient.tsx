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
  Truck,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  MapPin,
  PhoneCall,
  Calendar,
  Layers,
  ArrowRight,
  Clock,
  Star,
  Check,
  X,
  MessageSquare,
  AlertCircle,
  FileCheck,
  RefreshCw,
  Camera,
  Navigation,
} from 'lucide-react';
import { RoleGuard } from '@/components/auth/RoleGuard';
import { isDemoMode, isProductionMode } from '@/lib/appMode';

interface DocumentRecord {
  name: string;
  code: string;
  docNumber: string;
  expiryDate: string;
  isExpired: boolean;
  photoUrl: string;
}

interface AssignedTrip {
  id: string;
  tripIdNum: number;
  dealId: number;
  farmerName: string;
  farmerPhone: string;
  farmerVillage: string;
  farmerLat: number;
  farmerLng: number;
  buyerName: string;
  buyerPhone: string;
  buyerDestination: string;
  buyerLat: number;
  buyerLng: number;
  crop: string;
  variety: string;
  quantityKg: number;
  vehicleClass: 'goods_auto' | 'mini_truck' | 'large_truck';
  distanceKm: number;
  guideRateAmount: number;
  status: 'assigned' | 'arrived_pickup' | 'in_transit' | 'delivered' | 'disputed';
  pickupOtp: string;
  deliveryOtp: string;
  buyerDisputeReason?: string;
  buyerDisputePhoto?: string;
  farmerRatingGiven?: number;
  buyerRatingGiven?: number;
}

interface PooledLoadItem {
  id: string;
  farmA: {
    farmer: string;
    village: string;
    crop: string;
    weightKg: number;
  };
  farmB: {
    farmer: string;
    village: string;
    crop: string;
    weightKg: number;
  };
  destination: string;
  totalWeightKg: number;
  totalKm: number;
  pooledFreight: number;
  individualFreight: number;
  savingsPercent: number;
}

const INITIAL_DOCS: DocumentRecord[] = [
  {
    name: 'Commercial Driving Licence (DL)',
    code: 'DL',
    docNumber: 'AP07-2019-0091218',
    expiryDate: '2028-11-14',
    isExpired: false,
    photoUrl: '/docs/dl_sample.png',
  },
  {
    name: 'Registration Certificate (RC)',
    code: 'RC',
    docNumber: 'AP 07 TA 4120',
    expiryDate: '2035-06-22',
    isExpired: false,
    photoUrl: '/docs/rc_sample.png',
  },
  {
    name: 'Commercial Vehicle Insurance',
    code: 'INSURANCE',
    docNumber: 'BAJAJ-ALL-88912-COMM',
    expiryDate: '2026-12-19',
    isExpired: false,
    photoUrl: '/docs/insurance_sample.png',
  },
  {
    name: 'Fitness Certificate (FC)',
    code: 'FITNESS',
    docNumber: 'AP-FIT-2025-4109',
    expiryDate: '2027-08-15',
    isExpired: false,
    photoUrl: '/docs/fitness_sample.png',
  },
];

const INITIAL_TRIP: AssignedTrip = {
  id: 'TRIP-8102',
  tripIdNum: 8102,
  dealId: 901,
  farmerName: 'Ramesh Reddy',
  farmerPhone: '+919848011223',
  farmerVillage: 'Chiluvuru, Tenali Rural (18.5 km away)',
  farmerLat: 16.243,
  farmerLng: 80.648,
  buyerName: 'Acharya Nagarjuna University Hostel',
  buyerPhone: '+919988776655',
  buyerDestination: 'Mess Procurement Gate, Nagarjuna Nagar, Guntur',
  buyerLat: 16.306,
  buyerLng: 80.436,
  crop: 'Banana',
  variety: 'Amruthapani (Grade A)',
  quantityKg: 400,
  vehicleClass: 'goods_auto',
  distanceKm: 18.5,
  guideRateAmount: 483, // 150 base + 18.5 * 18
  status: 'assigned',
  pickupOtp: '8291',
  deliveryOtp: '492018',
};

const INITIAL_POOLS: PooledLoadItem[] = [
  {
    id: 'POOL-TENALI-ANU-01',
    farmA: {
      farmer: 'Ramesh Reddy',
      village: 'Tenali Rural (North)',
      crop: 'Banana (Amruthapani)',
      weightKg: 400,
    },
    farmB: {
      farmer: 'Venkateswarlu K.',
      village: 'Tenali Rural (East, 3.8 km from Farm A)',
      crop: 'Banana (Robusta)',
      weightKg: 350,
    },
    destination: 'Acharya Nagarjuna University Central Store, Guntur',
    totalWeightKg: 750,
    totalKm: 22.8,
    pooledFreight: 780,
    individualFreight: 966,
    savingsPercent: 19,
  },
];

export function DriverClient() {
  const t = useTranslations();
  const locale = useLocale() as SupportedLocale;
  const router = useRouter();
  const pathname = usePathname();

  // Navigation tab
  const [activeTab, setActiveTab] = useState<'trips' | 'pool' | 'documents' | 'whatsapp'>('trips');

  // Transporter state
  const [isAvailableToday, setIsAvailableToday] = useState(isDemoMode);
  const [docs, setDocs] = useState<DocumentRecord[]>(isDemoMode ? INITIAL_DOCS : []);
  const [activeTrip, setActiveTrip] = useState<AssignedTrip | null>(isDemoMode ? INITIAL_TRIP : null);
  const [pooledLoads, setPooledLoads] = useState<PooledLoadItem[]>(isDemoMode ? INITIAL_POOLS : []);

  // OTP Modals
  const [showPickupOtpModal, setShowPickupOtpModal] = useState(false);
  const [pickupOtpInput, setPickupOtpInput] = useState('');
  const [pickupError, setPickupError] = useState<string | null>(null);

  const [showDeliveryOtpModal, setShowDeliveryOtpModal] = useState(false);
  const [deliveryOtpInput, setDeliveryOtpInput] = useState('');
  const [deliveryPhotoUploaded, setDeliveryPhotoUploaded] = useState(true);
  const [deliveryError, setDeliveryError] = useState<string | null>(null);

  // Rating Modal
  const [showRatingModal, setShowRatingModal] = useState(false);
  const [ratingFarmerScore, setRatingFarmerScore] = useState(5);
  const [ratingBuyerScore, setRatingBuyerScore] = useState(5);
  const [ratingNotes, setRatingNotes] = useState('Smooth loading and exact weighing at farm gate.');

  // Masked call modal
  const [maskedCallParty, setMaskedCallParty] = useState<{ name: string; role: string; phone: string } | null>(null);

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

  // Check if any document is expired
  const hasExpiredDocs = docs.some((d) => d.isExpired);

  const handleToggleAvailability = () => {
    if (hasExpiredDocs) {
      showToast('Cannot go online: You have expired compliance documents. Please renew with admin.');
      return;
    }
    const nextState = !isAvailableToday;
    setIsAvailableToday(nextState);
    showToast(
      nextState
        ? 'Status: Available Today! Nearest post-deal loads will be assigned to you.'
        : 'Status: Offline. You will not receive new trip requests today.'
    );
  };

  const handleToggleSimulateExpiredDoc = (code: string) => {
    setDocs((prev) =>
      prev.map((d) => {
        if (d.code === code) {
          const toggled = !d.isExpired;
          return {
            ...d,
            isExpired: toggled,
            expiryDate: toggled ? '2026-01-15' : '2027-08-15',
          };
        }
        return d;
      })
    );
  };

  const handleVerifyPickupOtp = () => {
    if (!activeTrip) return;
    if (pickupOtpInput.trim() !== activeTrip.pickupOtp) {
      setPickupError(`Incorrect OTP. Ask farmer ${activeTrip.farmerName} for their 4-digit pickup code.`);
      return;
    }
    setPickupError(null);
    setShowPickupOtpModal(false);
    setPickupOtpInput('');
    setActiveTrip({ ...activeTrip, status: 'in_transit' });
    showToast('Pickup verified! Status updated to In-Transit. Proceed to delivery destination.');
  };

  const handleVerifyDeliveryOtp = () => {
    if (!activeTrip) return;
    if (deliveryOtpInput.trim() !== activeTrip.deliveryOtp) {
      setDeliveryError(`Incorrect delivery OTP. Request the 6-digit code from buyer ${activeTrip.buyerName}.`);
      return;
    }
    setDeliveryError(null);
    setShowDeliveryOtpModal(false);
    setDeliveryOtpInput('');
    setActiveTrip({ ...activeTrip, status: 'delivered' });
    showToast('Delivery successful! Crate handover verified. Please rate the farmer & buyer.');
    setTimeout(() => setShowRatingModal(true), 600);
  };

  const handleSubmitRating = () => {
    if (!activeTrip) return;
    setActiveTrip({
      ...activeTrip,
      farmerRatingGiven: ratingFarmerScore,
      buyerRatingGiven: ratingBuyerScore,
    });
    setShowRatingModal(false);
    showToast('Mutual rating submitted! Your reliability score has increased.');
  };

  const handleAcceptPooledTrip = (pool: PooledLoadItem) => {
    setActiveTrip({
      id: pool.id,
      tripIdNum: 9201,
      dealId: 901,
      farmerName: `${pool.farmA.farmer} + ${pool.farmB.farmer}`,
      farmerPhone: '+919848011223',
      farmerVillage: `${pool.farmA.village} & ${pool.farmB.village}`,
      farmerLat: 16.243,
      farmerLng: 80.648,
      buyerName: pool.destination,
      buyerPhone: '+919988776655',
      buyerDestination: pool.destination,
      buyerLat: 16.306,
      buyerLng: 80.436,
      crop: 'Banana (Multi-Farm Lot)',
      variety: 'Combined Amruthapani + Robusta',
      quantityKg: pool.totalWeightKg,
      vehicleClass: 'mini_truck',
      distanceKm: pool.totalKm,
      guideRateAmount: pool.pooledFreight,
      status: 'assigned',
      pickupOtp: '5192',
      deliveryOtp: '741930',
    });
    setActiveTab('trips');
    showToast(`Pooled Trip #${pool.id} accepted! 2 Pickups combined into 1 delivery.`);
  };

  return (
    <div className="min-h-screen flex flex-col bg-cream">
      <Header
        currentLocale={locale}
        onSelectLocale={handleLocaleChange}
        brandName={t('brand.name')}
        activeNav="driver"
      />

      {/* Floating Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-deep-leaf text-white px-5 py-3 rounded-2xl shadow-xl flex items-center gap-3 animate-slide-up border border-white/20">
          <CheckCircle2 className="w-5 h-5 text-harvest-gold flex-shrink-0" />
          <span className="text-sm font-semibold">{toastMessage}</span>
        </div>
      )}

      <RoleGuard
        allowedRoles={['driver', 'admin']}
        fallbackTitle="Transporter Dashboard Protected"
        fallbackMessage="This dashboard is reserved for verified transporters and drivers to manage assigned farm-to-mandi trips, vehicle documents, and live pickup/delivery OTPs."
      >
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* DRIVER PROFILE & VEHICLE CARD */}
        <div className="bg-white rounded-3xl border border-border p-6 shadow-sm mb-6 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
          <div className="flex items-start sm:items-center gap-4">
            <div className="w-16 h-16 rounded-2xl bg-deep-leaf/10 text-deep-leaf flex items-center justify-center flex-shrink-0">
              <Truck className="w-8 h-8" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h1 className="font-heading text-2xl font-extrabold text-ink">
                  Venkat Rao
                </h1>
                <Chip variant="primary" size="sm">
                  Verified Transporter
                </Chip>
                <div className="flex items-center text-xs font-bold text-amber bg-amber/10 px-2 py-0.5 rounded-full">
                  <Star className="w-3.5 h-3.5 mr-1 fill-amber text-amber" />
                  4.9 (42 Trips)
                </div>
              </div>
              <p className="text-xs text-muted mt-1">
                Vehicle: <strong>Tata Ace Gold</strong> &bull; Reg: <strong>AP 07 TA 4120</strong> &bull; Capacity: <strong>750 kg</strong>
              </p>
              <p className="text-xs text-muted">
                Service Radius: <strong>Guntur - Tenali - Mangalagiri (45 km)</strong>
              </p>
            </div>
          </div>

          {/* AVAILABILITY TOGGLE & COMPLIANCE BADGE */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 w-full lg:w-auto">
            {/* Automatic Expiry Warning Notice */}
            {hasExpiredDocs && (
              <div className="bg-danger/10 text-danger border border-danger/20 rounded-2xl px-4 py-2 text-xs flex items-center gap-2 font-bold">
                <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                <span>Locked: Expired Document Detected</span>
              </div>
            )}

            <button
              onClick={handleToggleAvailability}
              className={`flex items-center gap-3 px-5 py-3 rounded-2xl border transition-all text-sm font-bold min-h-[48px] w-full sm:w-auto justify-between sm:justify-start ${
                hasExpiredDocs
                  ? 'bg-muted/10 border-muted text-muted cursor-not-allowed opacity-60'
                  : isAvailableToday
                  ? 'bg-deep-leaf text-white border-deep-leaf shadow-md'
                  : 'bg-white text-ink border-border hover:bg-cream'
              }`}
              disabled={hasExpiredDocs}
            >
              <span
                className={`w-3.5 h-3.5 rounded-full ${
                  isAvailableToday && !hasExpiredDocs ? 'bg-harvest-gold animate-pulse' : 'bg-muted'
                }`}
              />
              <span>
                {hasExpiredDocs
                  ? 'Offline (Compliance Block)'
                  : isAvailableToday
                  ? 'Available Today (Receiving Loads)'
                  : 'Currently Offline'}
              </span>
            </button>
          </div>
        </div>

        {/* COMPLIANCE RADAR NOTICE */}
        {hasExpiredDocs ? (
          <div className="bg-danger/10 border-2 border-danger/30 rounded-2xl p-4 mb-6 flex items-start gap-3 text-xs text-ink leading-relaxed">
            <AlertCircle className="w-5 h-5 text-danger flex-shrink-0 mt-0.5" />
            <div>
              <strong className="text-danger text-sm block mb-0.5">
                Automatic Expiry Protection Active:
              </strong>
              One or more vehicle documents (FC/RC/Insurance) have expired. Under GrowCircle transport safety rules, drivers with expired documents are automatically hidden from load dispatch algorithms. Renew your documents and upload proofs to resume receiving dispatch requests.
            </div>
          </div>
        ) : (
          <div className="bg-deep-leaf/5 border border-deep-leaf/20 rounded-2xl p-4 mb-6 flex items-start gap-3 text-xs text-ink leading-relaxed">
            <ShieldCheck className="w-5 h-5 text-deep-leaf flex-shrink-0 mt-0.5" />
            <div>
              <strong className="text-deep-leaf text-sm block mb-0.5">
                All Mandatory Documents Active:
              </strong>
              All documents (DL, RC, Commercial Insurance, Fitness Certificate) are verified and active. You are eligible for automated 3-driver dispatch suggestions and freight pooling across Guntur district.
            </div>
          </div>
        )}

        {/* TABS HEADER */}
        <div className="flex border-b border-border mb-6 gap-2 sm:gap-6 overflow-x-auto pb-1">
          <button
            onClick={() => setActiveTab('trips')}
            className={`pb-3 px-2 text-sm sm:text-base font-semibold transition-all border-b-2 whitespace-nowrap flex items-center gap-2 ${
              activeTab === 'trips'
                ? 'border-deep-leaf text-deep-leaf'
                : 'border-transparent text-muted hover:text-ink'
            }`}
          >
            <Truck className="w-4 h-4" />
            <span>My Active Trips</span>
            {activeTrip && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-deep-leaf text-white font-bold">
                1
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab('pool')}
            className={`pb-3 px-2 text-sm sm:text-base font-semibold transition-all border-b-2 whitespace-nowrap flex items-center gap-2 ${
              activeTab === 'pool'
                ? 'border-deep-leaf text-deep-leaf'
                : 'border-transparent text-muted hover:text-ink'
            }`}
          >
            <Layers className="w-4 h-4" />
            <span>Freight Pooling v1</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-harvest-gold/40 text-ink font-bold">
              {pooledLoads.length} Match
            </span>
          </button>

          <button
            onClick={() => setActiveTab('documents')}
            className={`pb-3 px-2 text-sm sm:text-base font-semibold transition-all border-b-2 whitespace-nowrap flex items-center gap-2 ${
              activeTab === 'documents'
                ? 'border-deep-leaf text-deep-leaf'
                : 'border-transparent text-muted hover:text-ink'
            }`}
          >
            <FileCheck className="w-4 h-4" />
            <span>Documents & Compliance</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-border text-ink font-bold">
              4
            </span>
          </button>

          <button
            onClick={() => setActiveTab('whatsapp')}
            className={`pb-3 px-2 text-sm sm:text-base font-semibold transition-all border-b-2 whitespace-nowrap flex items-center gap-2 ${
              activeTab === 'whatsapp'
                ? 'border-deep-leaf text-deep-leaf'
                : 'border-transparent text-muted hover:text-ink'
            }`}
          >
            <MessageSquare className="w-4 h-4" />
            <span>WhatsApp Quick Door</span>
          </button>
        </div>

        {/* TAB 1: ACTIVE TRIPS */}
        {activeTab === 'trips' && (
          <div className="space-y-6">
            {!activeTrip ? (
              <Card className="p-12 text-center text-muted">
                <Truck className="w-12 h-12 text-muted mx-auto mb-3 opacity-40" />
                <h3 className="font-heading text-lg font-bold text-ink mb-1">
                  No Active Trips Right Now
                </h3>
                <p className="text-xs text-muted mb-4">
                  Keep your &quot;Available Today&quot; switch turned on to receive post-deal load dispatch alerts near Guntur.
                </p>
                <Button
                  variant="secondary"
                  size="md"
                  onClick={() => setActiveTab('pool')}
                >
                  View Nearby Pooled Loads
                </Button>
              </Card>
            ) : (
              <Card className="p-6 bg-white border border-border shadow-sm">
                {/* Trip Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-border">
                  <div>
                    <div className="flex items-center gap-2.5 flex-wrap">
                      <span className="font-mono text-sm font-bold text-deep-leaf bg-deep-leaf/10 px-2.5 py-1 rounded-lg">
                        {activeTrip.id}
                      </span>
                      <h2 className="font-heading text-lg sm:text-xl font-bold text-ink">
                        {activeTrip.quantityKg} kg {activeTrip.variety} {activeTrip.crop}
                      </h2>
                      <Chip
                        variant={
                          activeTrip.status === 'delivered'
                            ? 'primary'
                            : activeTrip.status === 'in_transit'
                            ? 'accent'
                            : activeTrip.status === 'disputed'
                            ? 'danger'
                            : 'default'
                        }
                        size="sm"
                      >
                        {activeTrip.status === 'assigned'
                          ? 'Assigned (Head to Farm)'
                          : activeTrip.status === 'arrived_pickup'
                          ? 'Arrived at Pickup'
                          : activeTrip.status === 'in_transit'
                          ? 'In-Transit to Buyer'
                          : activeTrip.status === 'delivered'
                          ? 'Delivered & Completed'
                          : 'Dispute Under Review'}
                      </Chip>
                    </div>
                    <p className="text-xs text-muted mt-1">
                      Matched Vehicle: <strong>Goods Auto (&lt;500 kg)</strong> &bull; Distance: <strong>{activeTrip.distanceKm} km</strong>
                    </p>
                  </div>

                  {/* Guide Rate Display */}
                  <div className="bg-cream rounded-2xl p-4 border border-border sm:text-right min-w-[200px]">
                    <span className="text-[11px] font-bold text-muted block uppercase tracking-wider">
                      Indicative Guide Rate
                    </span>
                    <span className="text-2xl font-extrabold text-deep-leaf">
                      ₹{activeTrip.guideRateAmount}
                    </span>
                    <p className="text-[10px] text-muted leading-tight mt-0.5">
                      ₹150 base + ₹18/km. Not fixed: Driver &amp; parties finalize directly.
                    </p>
                  </div>
                </div>

                {/* Route Diagram */}
                <div className="py-6 grid grid-cols-1 md:grid-cols-2 gap-6 border-b border-border">
                  {/* Pickup Node */}
                  <div className="bg-cream/60 rounded-2xl p-4 border border-border/80 flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-bold text-deep-leaf flex items-center gap-1.5 uppercase tracking-wide">
                          <MapPin className="w-4 h-4" /> 1. Pickup Point (Farm Gate)
                        </span>
                        <Button
                          variant="secondary"
                          size="md"
                          className="text-xs h-8 min-h-[32px] px-2.5"
                          onClick={() =>
                            setMaskedCallParty({
                              name: activeTrip.farmerName,
                              role: 'Farmer',
                              phone: activeTrip.farmerPhone,
                            })
                          }
                          leftIcon={<PhoneCall className="w-3.5 h-3.5 text-deep-leaf" />}
                        >
                          Call Farmer
                        </Button>
                      </div>
                      <h4 className="font-heading text-base font-bold text-ink">
                        {activeTrip.farmerName}
                      </h4>
                      <p className="text-xs text-muted mt-0.5">
                        {activeTrip.farmerVillage}
                      </p>
                    </div>

                    <div className="mt-4 pt-3 border-t border-border flex items-center justify-between text-xs">
                      <span className="text-muted">Farmer Pickup Handover OTP:</span>
                      <span className="font-mono font-bold text-ink bg-white px-2 py-0.5 rounded border border-border">
                        **** (Provided by Farmer)
                      </span>
                    </div>
                  </div>

                  {/* Dropoff Node */}
                  <div className="bg-cream/60 rounded-2xl p-4 border border-border/80 flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-bold text-amber flex items-center gap-1.5 uppercase tracking-wide">
                          <Navigation className="w-4 h-4" /> 2. Delivery Destination
                        </span>
                        <Button
                          variant="secondary"
                          size="md"
                          className="text-xs h-8 min-h-[32px] px-2.5"
                          onClick={() =>
                            setMaskedCallParty({
                              name: activeTrip.buyerName,
                              role: 'Institutional Buyer',
                              phone: activeTrip.buyerPhone,
                            })
                          }
                          leftIcon={<PhoneCall className="w-3.5 h-3.5 text-deep-leaf" />}
                        >
                          Call Buyer
                        </Button>
                      </div>
                      <h4 className="font-heading text-base font-bold text-ink">
                        {activeTrip.buyerName}
                      </h4>
                      <p className="text-xs text-muted mt-0.5">
                        {activeTrip.buyerDestination}
                      </p>
                    </div>

                    <div className="mt-4 pt-3 border-t border-border flex items-center justify-between text-xs">
                      <span className="text-muted">Buyer Delivery Handover OTP:</span>
                      <span className="font-mono font-bold text-ink bg-white px-2 py-0.5 rounded border border-border">
                        ****** (Provided by Buyer)
                      </span>
                    </div>
                  </div>
                </div>

                {/* TRIP ACTIONS ACCORDING TO STATE */}
                <div className="pt-6 flex flex-col sm:flex-row items-center justify-between gap-4">
                  <div className="text-xs text-muted">
                    {activeTrip.status === 'assigned' && (
                      <span>Step 1: Travel to farm gate &amp; obtain the 4-digit pickup code from farmer.</span>
                    )}
                    {activeTrip.status === 'in_transit' && (
                      <span>Step 2: Transport crates safely to the buyer &amp; obtain the 6-digit delivery OTP.</span>
                    )}
                    {activeTrip.status === 'delivered' && (
                      <span className="text-deep-leaf font-bold flex items-center gap-1.5">
                        <CheckCircle2 className="w-4 h-4" />
                        Trip completed and physical handover confirmed.
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-3 w-full sm:w-auto">
                    {activeTrip.status === 'assigned' && (
                      <Button
                        variant="primary"
                        size="md"
                        className="w-full sm:w-auto"
                        onClick={() => setShowPickupOtpModal(true)}
                        leftIcon={<Check className="w-4 h-4" />}
                      >
                        Enter Pickup OTP
                      </Button>
                    )}

                    {activeTrip.status === 'in_transit' && (
                      <Button
                        variant="primary"
                        size="md"
                        className="w-full sm:w-auto bg-amber text-ink hover:bg-amber/90"
                        onClick={() => setShowDeliveryOtpModal(true)}
                        leftIcon={<Check className="w-4 h-4" />}
                      >
                        Complete Delivery with OTP
                      </Button>
                    )}

                    {activeTrip.status === 'delivered' && (
                      <Button
                        variant="secondary"
                        size="md"
                        className="w-full sm:w-auto"
                        onClick={() => setShowRatingModal(true)}
                        leftIcon={<Star className="w-4 h-4 text-amber" />}
                      >
                        {activeTrip.farmerRatingGiven ? 'Update Ratings' : 'Rate Farmer & Buyer'}
                      </Button>
                    )}
                  </div>
                </div>
              </Card>
            )}
          </div>
        )}

        {/* TAB 2: FREIGHT POOLING V1 */}
        {activeTab === 'pool' && (
          <div className="space-y-6">
            <div className="bg-white rounded-3xl border border-border p-6 shadow-sm">
              <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
                <div className="flex items-center gap-2">
                  <Layers className="w-6 h-6 text-deep-leaf" />
                  <h2 className="font-heading text-xl font-bold text-ink">
                    Rule-Based Freight Pooling (v1 Engine)
                  </h2>
                </div>
                <Chip variant="accent" size="sm">
                  15 km Pickup Cluster Radius
                </Chip>
              </div>
              <p className="text-xs text-muted leading-relaxed">
                GrowCircle&apos;s rule engine automatically detects nearby farm pickups going to the same institutional destination (college, hostel, hotel). Pooling combines small loads into a single trip, giving the driver higher capacity utilization and saving farmers up to 25% on freight!
              </p>
            </div>

            <div className="space-y-4">
              {pooledLoads.map((pool) => (
                <Card key={pool.id} className="p-6 bg-white border border-border shadow-sm">
                  <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-border">
                    <div>
                      <div className="flex items-center gap-2.5">
                        <span className="font-mono text-xs font-bold text-deep-leaf bg-deep-leaf/10 px-2.5 py-1 rounded-lg">
                          {pool.id}
                        </span>
                        <h3 className="font-heading text-lg font-bold text-ink">
                          Combined 2-Stop Pickup &bull; {pool.totalWeightKg} kg Total Load
                        </h3>
                        <Chip variant="primary" size="sm">
                          Fits Tata Ace (750 kg capacity)
                        </Chip>
                      </div>
                      <p className="text-xs text-muted mt-1">
                        Delivery to: <strong>{pool.destination}</strong>
                      </p>
                    </div>

                    <div className="flex items-center gap-4 bg-cream rounded-2xl p-3 border border-border">
                      <div>
                        <span className="text-[10px] text-muted block uppercase">Separate Cost</span>
                        <span className="text-sm font-semibold line-through text-muted">
                          ₹{pool.individualFreight}
                        </span>
                      </div>
                      <div>
                        <span className="text-[10px] font-bold text-deep-leaf block uppercase">
                          Pooled Guide Fare
                        </span>
                        <span className="text-xl font-extrabold text-deep-leaf">
                          ₹{pool.pooledFreight}
                        </span>
                      </div>
                      <div className="bg-harvest-gold/30 text-ink text-xs font-bold px-2.5 py-1 rounded-lg">
                        {pool.savingsPercent}% Freight Savings
                      </div>
                    </div>
                  </div>

                  {/* Multi-stop schedule */}
                  <div className="py-4 grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                    <div className="bg-cream/60 p-3 rounded-xl border border-border">
                      <span className="font-bold text-deep-leaf block mb-1">
                        Stop 1: Farm Pickup A
                      </span>
                      <p className="font-semibold text-ink">{pool.farmA.farmer}</p>
                      <p className="text-muted">{pool.farmA.village}</p>
                      <span className="text-deep-leaf font-bold mt-1 inline-block">
                        {pool.farmA.weightKg} kg &bull; {pool.farmA.crop}
                      </span>
                    </div>

                    <div className="bg-cream/60 p-3 rounded-xl border border-border">
                      <span className="font-bold text-deep-leaf block mb-1">
                        Stop 2: Farm Pickup B (+3.8 km)
                      </span>
                      <p className="font-semibold text-ink">{pool.farmB.farmer}</p>
                      <p className="text-muted">{pool.farmB.village}</p>
                      <span className="text-deep-leaf font-bold mt-1 inline-block">
                        {pool.farmB.weightKg} kg &bull; {pool.farmB.crop}
                      </span>
                    </div>

                    <div className="bg-cream/60 p-3 rounded-xl border border-border">
                      <span className="font-bold text-amber block mb-1">
                        Stop 3: Institutional Dropoff
                      </span>
                      <p className="font-semibold text-ink">{pool.destination}</p>
                      <p className="text-muted">Total Run: {pool.totalKm} km</p>
                      <span className="text-amber font-bold mt-1 inline-block">
                        Full Handover Verification
                      </span>
                    </div>
                  </div>

                  <div className="pt-3 border-t border-border flex items-center justify-between">
                    <span className="text-xs text-muted">
                      Both farmers agreed to freight pooling via Voice IVR &amp; WhatsApp.
                    </span>
                    <Button
                      variant="primary"
                      size="md"
                      onClick={() => handleAcceptPooledTrip(pool)}
                      rightIcon={<ArrowRight className="w-4 h-4" />}
                    >
                      Accept Pooled Trip (₹{pool.pooledFreight})
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          </div>
        )}

        {/* TAB 3: DOCUMENTS & COMPLIANCE */}
        {activeTab === 'documents' && (
          <div className="space-y-6">
            <div className="bg-white rounded-3xl border border-border p-6 shadow-sm">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <FileCheck className="w-6 h-6 text-deep-leaf" />
                  <h2 className="font-heading text-xl font-bold text-ink">
                    Transporter Document Expiry Radar
                  </h2>
                </div>
                <span className="text-xs text-muted">
                  Strictly Enforced: Real-time Validity Verification
                </span>
              </div>
              <p className="text-xs text-muted leading-relaxed">
                All commercial vehicles on GrowCircle undergo automated daily document expiry verification. If any of your Driving Licence, RC, Commercial Insurance, or Fitness Certificate expires, your vehicle is automatically hidden from load matching to protect farmers and buyers.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {docs.map((doc) => (
                <Card
                  key={doc.code}
                  className={`p-5 transition-all ${
                    doc.isExpired ? 'border-2 border-danger bg-danger/5' : 'bg-white'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div>
                      <h4 className="font-heading text-base font-bold text-ink">
                        {doc.name}
                      </h4>
                      <p className="font-mono text-xs font-semibold text-muted mt-0.5">
                        {doc.docNumber}
                      </p>
                    </div>

                    <Chip
                      variant={doc.isExpired ? 'danger' : 'primary'}
                      size="sm"
                    >
                      {doc.isExpired ? 'EXPIRED' : 'VALID'}
                    </Chip>
                  </div>

                  <div className="bg-cream p-3 rounded-xl border border-border flex items-center justify-between text-xs mb-4">
                    <div>
                      <span className="text-muted block">Expiry Date</span>
                      <span
                        className={`font-bold ${
                          doc.isExpired ? 'text-danger' : 'text-deep-leaf'
                        }`}
                      >
                        {doc.expiryDate}
                      </span>
                    </div>

                    <div className="text-right">
                      <span className="text-muted block">Status</span>
                      <span className="font-semibold text-ink">
                        {doc.isExpired ? 'Dispatch Blocked' : 'Active on Radar'}
                      </span>
                    </div>
                  </div>

                  {/* Testing simulator toggle */}
                  {isDemoMode && (
                    <div className="flex items-center justify-between pt-2 border-t border-border/80">
                      <span className="text-[11px] text-muted">
                        Test Automatic Expiry Rule:
                      </span>
                      <button
                        onClick={() => handleToggleSimulateExpiredDoc(doc.code)}
                        className="text-xs font-bold text-amber hover:underline focus:outline-none"
                      >
                        {doc.isExpired ? 'Restore Valid Date' : 'Simulate Expired'}
                      </button>
                    </div>
                  )}
                </Card>
              ))}
            </div>
          </div>
        )}

        {/* TAB 4: WHATSAPP QUICK FLOW */}
        {activeTab === 'whatsapp' && (
          <div className="space-y-6">
            <Card className="p-8 bg-white border border-border shadow-sm">
              <div className="max-w-2xl mx-auto text-center space-y-4">
                <div className="w-16 h-16 rounded-3xl bg-deep-leaf/10 text-deep-leaf flex items-center justify-center mx-auto">
                  <MessageSquare className="w-8 h-8" />
                </div>
                <h2 className="font-heading text-2xl font-extrabold text-ink">
                  Zero App Required: Drive with WhatsApp
                </h2>
                <p className="text-sm text-muted leading-relaxed">
                  Most drivers in Andhra Pradesh prefer using WhatsApp over downloading an app. Send simple text messages or voice notes to GrowCircle&apos;s verified WhatsApp number:
                </p>

                <div className="bg-cream rounded-2xl p-5 border border-border text-left font-mono text-xs sm:text-sm space-y-2.5">
                  <div className="flex items-center justify-between py-1 border-b border-border">
                    <span className="font-bold text-deep-leaf">AVAILABLE YES</span>
                    <span className="text-muted">Turn ON your driver availability for the day</span>
                  </div>
                  <div className="flex items-center justify-between py-1 border-b border-border">
                    <span className="font-bold text-deep-leaf">AVAILABLE NO</span>
                    <span className="text-muted">Turn OFF availability (offline mode)</span>
                  </div>
                  <div className="flex items-center justify-between py-1 border-b border-border">
                    <span className="font-bold text-deep-leaf">TRIPS</span>
                    <span className="text-muted">List your assigned trips and guide fares</span>
                  </div>
                  <div className="flex items-center justify-between py-1 border-b border-border">
                    <span className="font-bold text-deep-leaf">PICKUP 8291</span>
                    <span className="text-muted">Verify farm gate pickup with 4-digit OTP</span>
                  </div>
                  <div className="flex items-center justify-between py-1">
                    <span className="font-bold text-deep-leaf">DELIVER 492018</span>
                    <span className="text-muted">Verify delivery to buyer with 6-digit OTP</span>
                  </div>
                </div>

                <div className="pt-2">
                  <a
                    href="https://wa.me/919000000000?text=TRIPS"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 bg-deep-leaf text-white px-6 py-3 rounded-2xl font-bold shadow-md hover:bg-deep-leaf/90 transition-all min-h-[48px]"
                  >
                    <MessageSquare className="w-5 h-5 text-harvest-gold" />
                    <span>Open GrowCircle WhatsApp Chat</span>
                  </a>
                </div>
              </div>
            </Card>
          </div>
        )}
      </main>
      </RoleGuard>

      {/* MODAL: ENTER PICKUP OTP */}
      {showPickupOtpModal && activeTrip && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl border border-border animate-scale-in">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-6 h-6 text-deep-leaf" />
                <h3 className="font-heading text-xl font-bold text-ink">
                  Farm Gate Pickup Verification
                </h3>
              </div>
              <button
                onClick={() => {
                  setShowPickupOtpModal(false);
                  setPickupError(null);
                }}
                className="p-1 rounded-full text-muted hover:text-ink hover:bg-black/5"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-muted mb-4 leading-relaxed">
              Ask farmer <strong>{activeTrip.farmerName}</strong> for the 4-digit pickup OTP after inspecting the {activeTrip.quantityKg} kg crate count.
            </p>

            <div className="mb-4">
              <label className="block text-xs font-bold text-ink mb-1.5">
                Farmer 4-Digit Pickup OTP
              </label>
              <input
                type="text"
                maxLength={4}
                value={pickupOtpInput}
                onChange={(e) => setPickupOtpInput(e.target.value.trim())}
                placeholder="e.g. 8291"
                className="w-full text-center text-3xl font-mono tracking-widest font-extrabold p-3 rounded-xl border border-border focus:ring-2 focus:ring-deep-leaf"
              />
              {pickupError && (
                <p className="text-xs font-semibold text-danger mt-1.5 flex items-center gap-1">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  {pickupError}
                </p>
              )}
            </div>

            <div className="flex items-center gap-3">
              <Button
                variant="secondary"
                className="flex-1"
                onClick={() => {
                  setShowPickupOtpModal(false);
                  setPickupError(null);
                }}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                className="flex-1"
                onClick={handleVerifyPickupOtp}
              >
                Verify &amp; Start Transit
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: ENTER DELIVERY OTP */}
      {showDeliveryOtpModal && activeTrip && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl border border-border animate-scale-in">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-6 h-6 text-deep-leaf" />
                <h3 className="font-heading text-xl font-bold text-ink">
                  Complete Buyer Delivery
                </h3>
              </div>
              <button
                onClick={() => {
                  setShowDeliveryOtpModal(false);
                  setDeliveryError(null);
                }}
                className="p-1 rounded-full text-muted hover:text-ink hover:bg-black/5"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-muted mb-4 leading-relaxed">
              Ask buyer <strong>{activeTrip.buyerName}</strong> for their secret 6-digit delivery handover OTP after they inspect the produce crates.
            </p>

            <div className="mb-4">
              <label className="block text-xs font-bold text-ink mb-1.5">
                Buyer 6-Digit Delivery OTP
              </label>
              <input
                type="text"
                maxLength={6}
                value={deliveryOtpInput}
                onChange={(e) => setDeliveryOtpInput(e.target.value.trim())}
                placeholder="e.g. 492018"
                className="w-full text-center text-3xl font-mono tracking-widest font-extrabold p-3 rounded-xl border border-border focus:ring-2 focus:ring-deep-leaf"
              />
              {deliveryError && (
                <p className="text-xs font-semibold text-danger mt-1.5 flex items-center gap-1">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  {deliveryError}
                </p>
              )}
            </div>

            {/* Photo Proof Confirmation */}
            <div className="bg-cream rounded-2xl p-3 border border-border mb-4 flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <Camera className="w-4 h-4 text-deep-leaf" />
                <span>Delivery Handover Photo Proof</span>
              </div>
              <span className="font-bold text-deep-leaf flex items-center gap-1">
                <Check className="w-3.5 h-3.5" /> Captured
              </span>
            </div>

            <div className="flex items-center gap-3">
              <Button
                variant="secondary"
                className="flex-1"
                onClick={() => {
                  setShowDeliveryOtpModal(false);
                  setDeliveryError(null);
                }}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                className="flex-1"
                onClick={handleVerifyDeliveryOtp}
              >
                Confirm Delivery
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: MUTUAL RATING */}
      {showRatingModal && activeTrip && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl border border-border animate-scale-in">
            <h3 className="font-heading text-xl font-bold text-ink mb-2">
              Mutual Ratings (Trip #{activeTrip.id})
            </h3>
            <p className="text-xs text-muted mb-4">
              Help keep the GrowCircle community reliable and fair for all transporters.
            </p>

            {/* Rate Farmer */}
            <div className="mb-4 bg-cream p-3.5 rounded-2xl border border-border">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold text-ink">Rate Farmer ({activeTrip.farmerName})</span>
                <span className="text-xs font-bold text-amber">{ratingFarmerScore} / 5 Stars</span>
              </div>
              <div className="flex items-center gap-2">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    type="button"
                    onClick={() => setRatingFarmerScore(star)}
                    className="p-1 focus:outline-none"
                  >
                    <Star
                      className={`w-6 h-6 ${
                        star <= ratingFarmerScore
                          ? 'fill-amber text-amber'
                          : 'text-border hover:text-amber/50'
                      }`}
                    />
                  </button>
                ))}
              </div>
            </div>

            {/* Rate Buyer */}
            <div className="mb-4 bg-cream p-3.5 rounded-2xl border border-border">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold text-ink">Rate Buyer ({activeTrip.buyerName})</span>
                <span className="text-xs font-bold text-amber">{ratingBuyerScore} / 5 Stars</span>
              </div>
              <div className="flex items-center gap-2">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    type="button"
                    onClick={() => setRatingBuyerScore(star)}
                    className="p-1 focus:outline-none"
                  >
                    <Star
                      className={`w-6 h-6 ${
                        star <= ratingBuyerScore
                          ? 'fill-amber text-amber'
                          : 'text-border hover:text-amber/50'
                      }`}
                    />
                  </button>
                ))}
              </div>
            </div>

            {/* Notes */}
            <div className="mb-5">
              <label className="block text-xs font-bold text-ink mb-1">
                Driver Feedback Notes
              </label>
              <textarea
                value={ratingNotes}
                onChange={(e) => setRatingNotes(e.target.value)}
                rows={2}
                className="w-full p-2.5 rounded-xl border border-border text-xs text-ink focus:ring-2 focus:ring-deep-leaf"
              />
            </div>

            <div className="flex items-center gap-3">
              <Button
                variant="secondary"
                className="flex-1"
                onClick={() => setShowRatingModal(false)}
              >
                Skip
              </Button>
              <Button
                variant="primary"
                className="flex-1"
                onClick={handleSubmitRating}
              >
                Submit Mutual Ratings
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: MASKED CALL INITIATION */}
      {maskedCallParty && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-sm w-full p-6 shadow-2xl border border-border animate-scale-in text-center">
            <div className="w-14 h-14 rounded-2xl bg-deep-leaf/10 text-deep-leaf flex items-center justify-center mx-auto mb-3">
              <PhoneCall className="w-7 h-7" />
            </div>
            <h3 className="font-heading text-lg font-bold text-ink mb-1">
              Masked Telephony Call
            </h3>
            <p className="text-xs text-muted mb-4">
              Calling <strong>{maskedCallParty.name}</strong> ({maskedCallParty.role})
            </p>

            <div className="bg-cream rounded-2xl p-4 border border-border text-xs text-ink mb-4 text-left space-y-1.5">
              <p className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-deep-leaf flex-shrink-0" />
                <span>Your real phone number remains masked &amp; private.</span>
              </p>
              <p className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-deep-leaf flex-shrink-0" />
                <span>Zero charge to driver or farmer.</span>
              </p>
            </div>

            <Button
              variant="primary"
              className="w-full"
              onClick={() => {
                showToast(`Dialing ${maskedCallParty.name} via virtual bridge 080-692-0000...`);
                setMaskedCallParty(null);
              }}
            >
              Connect Call Now
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
