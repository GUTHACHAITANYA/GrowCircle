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
import { MapLibreView, FarmerLocationPin } from '@/components/portal/MapLibreView';
import {
  Store,
  MapPin,
  ShieldCheck,
  CheckCircle2,
  Calendar,
  Layers,
  PhoneCall,
  ArrowRight,
  TrendingUp,
  AlertCircle,
  FileCheck,
  Clock,
  Camera,
  Star,
  Users,
  Building,
  RefreshCw,
  PlusCircle,
  Check,
  X,
  Volume2,
  Truck,
  Scale,
  AlertTriangle,
} from 'lucide-react';
import { RoleGuard } from '@/components/auth/RoleGuard';
import { isDemoMode, isProductionMode } from '@/lib/appMode';

interface WeeklyNeedItem {
  id: number;
  crop: string;
  quantityKg: number;
  preferredGrade: string;
  maxPriceKg: number;
  frequency: string;
  district: string;
  matchedCount: number;
}

interface DealItem {
  dealId: number;
  listingId: number;
  farmerName: string;
  crop: string;
  variety: string;
  grade: string;
  quantityKg: number;
  agreedPriceKg: number;
  totalAmount: number;
  status: 'pending_delivery' | 'completed' | 'disputed';
  deliveryOtp: string;
  farmerPhone: string;
  buyerPhone: string;
  createdAt: string;
  ratingGiven?: number;
}

interface OfferItem {
  offerId: number;
  listingId: number;
  farmerName: string;
  crop: string;
  variety: string;
  grade: string;
  quantityKg: number;
  offeredPriceKg: number;
  farmerCounterPriceKg?: number;
  status: 'pending' | 'countered' | 'accepted' | 'rejected';
  distanceKm: number;
}

const INITIAL_FARMER_LISTINGS: FarmerLocationPin[] = [
  {
    listing_id: 101,
    farmer_name: 'Ramesh Reddy',
    variety: 'Amruthapani',
    quantity_kg: 800,
    grade: 'A',
    expected_price_kg: 28.0,
    distance_km: 12.4,
    latitude: 16.243,
    longitude: 80.648,
    match_score: 0.94,
  },
  {
    listing_id: 102,
    farmer_name: 'Venkateswarlu K.',
    variety: 'Robusta',
    quantity_kg: 1500,
    grade: 'B',
    expected_price_kg: 22.5,
    distance_km: 26.8,
    latitude: 16.432,
    longitude: 80.562,
    match_score: 0.88,
  },
  {
    listing_id: 103,
    farmer_name: 'Krishna Murthy',
    variety: 'Karpura Chakkarakeli',
    quantity_kg: 600,
    grade: 'A',
    expected_price_kg: 32.0,
    distance_km: 18.2,
    latitude: 16.182,
    longitude: 80.352,
    match_score: 0.91,
  },
  {
    listing_id: 104,
    farmer_name: 'Samba Siva Rao',
    variety: 'Amruthapani',
    quantity_kg: 1200,
    grade: 'B',
    expected_price_kg: 24.0,
    distance_km: 38.5,
    latitude: 16.021,
    longitude: 80.451,
    match_score: 0.79,
  },
];

const INITIAL_NEEDS: WeeklyNeedItem[] = [
  {
    id: 1,
    crop: 'Banana',
    quantityKg: 2000,
    preferredGrade: 'A',
    maxPriceKg: 30.0,
    frequency: 'Weekly (Every Monday)',
    district: 'Guntur',
    matchedCount: 3,
  },
  {
    id: 2,
    crop: 'Banana',
    quantityKg: 500,
    preferredGrade: 'B',
    maxPriceKg: 25.0,
    frequency: 'Twice Weekly',
    district: 'Guntur',
    matchedCount: 2,
  },
];

const INITIAL_OFFERS: OfferItem[] = [
  {
    offerId: 501,
    listingId: 101,
    farmerName: 'Ramesh Reddy',
    crop: 'Banana',
    variety: 'Amruthapani',
    grade: 'A',
    quantityKg: 500,
    offeredPriceKg: 26.0,
    farmerCounterPriceKg: 27.5,
    status: 'countered',
    distanceKm: 12.4,
  },
];

const INITIAL_DEALS: DealItem[] = [
  {
    dealId: 901,
    listingId: 103,
    farmerName: 'Krishna Murthy',
    crop: 'Banana',
    variety: 'Karpura Chakkarakeli',
    grade: 'A',
    quantityKg: 400,
    agreedPriceKg: 31.0,
    totalAmount: 12400,
    status: 'pending_delivery',
    deliveryOtp: '492018',
    farmerPhone: '+919848011223',
    buyerPhone: '+919988776655',
    createdAt: 'Today, 11:30 AM',
  },
];

export function PortalClient() {
  const t = useTranslations();
  const locale = useLocale() as SupportedLocale;
  const router = useRouter();
  const pathname = usePathname();

  // Active Tab
  const [activeTab, setActiveTab] = useState<'matches' | 'needs' | 'group' | 'orders'>('matches');

  // Buyer Info & Verification
  const [buyerName, setBuyerName] = useState(isDemoMode ? 'Acharya Nagarjuna University Mess' : '');
  const [buyerType, setBuyerType] = useState(isDemoMode ? 'Institution / Hostel' : '');
  const [isVerified, setIsVerified] = useState(isDemoMode);
  const [showVerifyModal, setShowVerifyModal] = useState(false);
  const [gstInput, setGstInput] = useState(isDemoMode ? '37AAAAA0000A1Z5' : '');
  const [docRefInput, setDocRefInput] = useState(isDemoMode ? 'shop_act_license_2026.pdf' : '');

  // Data states
  const [farmerListings, setFarmerListings] = useState<FarmerLocationPin[]>(isDemoMode ? INITIAL_FARMER_LISTINGS : []);
  const [weeklyNeeds, setWeeklyNeeds] = useState<WeeklyNeedItem[]>(isDemoMode ? INITIAL_NEEDS : []);
  const [offers, setOffers] = useState<OfferItem[]>(isDemoMode ? INITIAL_OFFERS : []);
  const [deals, setDeals] = useState<DealItem[]>(isDemoMode ? INITIAL_DEALS : []);

  // Selected Listing for Modal / Details
  const [selectedListing, setSelectedListing] = useState<FarmerLocationPin | null>(null);
  const [offerPriceInput, setOfferPriceInput] = useState<number>(27);
  const [offerQtyInput, setOfferQtyInput] = useState<number>(500);

  // Read-back Confirmation Modal State
  const [showReadBackModal, setShowReadBackModal] = useState(false);
  const [readBackTarget, setReadBackTarget] = useState<{
    offerId: number;
    farmerName: string;
    crop: string;
    quantityKg: number;
    priceKg: number;
    totalAmount: number;
  } | null>(null);
  const [readBackConfirmed, setReadBackConfirmed] = useState(false);

  // Masked Call Modal State
  const [showCallModal, setShowCallModal] = useState(false);
  const [callContext, setCallContext] = useState<{
    farmerName: string;
    maskedNumber: string;
    sessionId: string;
  } | null>(null);

  // New Need Modal State
  const [showNewNeedModal, setShowNewNeedModal] = useState(false);
  const [newNeedCrop, setNewNeedCrop] = useState('Banana');
  const [newNeedQty, setNewNeedQty] = useState(1000);
  const [newNeedGrade, setNewNeedGrade] = useState('A');
  const [newNeedMaxPrice, setNewNeedMaxPrice] = useState(28);
  const [newNeedFreq, setNewNeedFreq] = useState('Weekly');

  // Farmer New Listing Simulation Modal
  const [showFarmerListModal, setShowFarmerListModal] = useState(false);
  const [newListingFarmerName, setNewListingFarmerName] = useState('Prakash V.');
  const [newListingVariety, setNewListingVariety] = useState('Amruthapani');
  const [newListingQty, setNewListingQty] = useState(750);
  const [newListingGrade, setNewListingGrade] = useState<'A' | 'B' | 'C'>('A');
  const [newListingPrice, setNewListingPrice] = useState(26.5);
  const [checklistWholeLot, setChecklistWholeLot] = useState(true);
  const [checklistCloseUp, setChecklistCloseUp] = useState(true);
  const [checklistCrate, setChecklistCrate] = useState(true);
  const [photoFreshnessHours, setPhotoFreshnessHours] = useState(1.5);

  // Transport matching and dispatch state
  const [selectedDealForTransport, setSelectedDealForTransport] = useState<DealItem | null>(null);
  const [assignedTransporterByDeal, setAssignedTransporterByDeal] = useState<Record<number, string>>({});

  // Delivery Dispute state
  const [disputingDeal, setDisputingDeal] = useState<DealItem | null>(null);
  const [disputeReasonInput, setDisputeReasonInput] = useState(
    '3 Crates of bananas crushed during transit. Significant bruising on bottom tier.'
  );
  const [disputePhotoAttached, setDisputePhotoAttached] = useState(true);

  // Success Notification
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

  // Group Supply calculation
  const totalSupplyWithin50km = farmerListings.reduce((sum, f) => sum + f.quantity_kg, 0);
  const weightedPriceSum = farmerListings.reduce(
    (sum, f) => sum + f.expected_price_kg * f.quantity_kg,
    0
  );
  const avgWeightedPrice = totalSupplyWithin50km > 0 ? (weightedPriceSum / totalSupplyWithin50km).toFixed(2) : '0';

  // Make an offer handler
  const handleCreateOffer = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedListing) return;

    const newOffer: OfferItem = {
      offerId: Date.now(),
      listingId: selectedListing.listing_id,
      farmerName: selectedListing.farmer_name,
      crop: 'Banana',
      variety: selectedListing.variety,
      grade: selectedListing.grade,
      quantityKg: offerQtyInput,
      offeredPriceKg: offerPriceInput,
      status: 'pending',
      distanceKm: selectedListing.distance_km,
    };

    setOffers([newOffer, ...offers]);
    setSelectedListing(null);
    setActiveTab('orders');
    showToast(`Offer of ₹${offerPriceInput}/kg for ${offerQtyInput} kg sent to ${selectedListing.farmer_name}`);
  };

  // Trigger read-back modal for counter offer acceptance
  const triggerAcceptOfferReadBack = (offer: OfferItem) => {
    const priceToAccept = offer.farmerCounterPriceKg || offer.offeredPriceKg;
    const total = priceToAccept * offer.quantityKg;

    setReadBackTarget({
      offerId: offer.offerId,
      farmerName: offer.farmerName,
      crop: `${offer.variety} ${offer.crop}`,
      quantityKg: offer.quantityKg,
      priceKg: priceToAccept,
      totalAmount: total,
    });
    setReadBackConfirmed(false);
    setShowReadBackModal(true);
  };

  // Finalize Deal after Read-Back Confirmation
  const confirmAcceptDeal = () => {
    if (!readBackTarget) return;

    // Update Offer status
    setOffers(
      offers.map((o) => (o.offerId === readBackTarget.offerId ? { ...o, status: 'accepted' } : o))
    );

    // Create New Deal
    const generatedOtp = Math.floor(100000 + Math.random() * 900000).toString();
    const newDeal: DealItem = {
      dealId: Date.now(),
      listingId: 101,
      farmerName: readBackTarget.farmerName,
      crop: 'Banana',
      variety: readBackTarget.crop,
      grade: 'A',
      quantityKg: readBackTarget.quantityKg,
      agreedPriceKg: readBackTarget.priceKg,
      totalAmount: readBackTarget.totalAmount,
      status: 'pending_delivery',
      deliveryOtp: generatedOtp,
      farmerPhone: '+919848011223',
      buyerPhone: '+919988776655',
      createdAt: 'Just now',
    };

    setDeals([newDeal, ...deals]);
    setShowReadBackModal(false);
    showToast(`Deal confirmed! Delivery OTP is ${generatedOtp}. No upfront payments required.`);
  };

  // Initiate Masked Call
  const handleInitiateMaskedCall = (farmerName: string) => {
    const maskedNum = '+91 80 4719 3800 (Ext ' + Math.floor(100 + Math.random() * 900) + ')';
    setCallContext({
      farmerName,
      maskedNumber: maskedNum,
      sessionId: 'MASK-' + Math.random().toString(36).substring(2, 8).toUpperCase(),
    });
    setShowCallModal(true);
  };

  // Assign Transporter
  const handleAssignTransporter = (dealId: number, driverName: string) => {
    setAssignedTransporterByDeal((prev) => ({ ...prev, [dealId]: driverName }));
    setSelectedDealForTransport(null);
    showToast(`Transporter ${driverName} assigned to Deal #${dealId}! Transporter notified.`);
  };

  // Raise Dispute
  const handleRaiseDispute = () => {
    if (!disputingDeal) return;
    if (!disputePhotoAttached) {
      showToast('Mandatory delivery photo proof is required to submit a complaint!');
      return;
    }
    setDeals(
      deals.map((d) =>
        d.dealId === disputingDeal.dealId ? { ...d, status: 'disputed' } : d
      )
    );
    const id = disputingDeal.dealId;
    setDisputingDeal(null);
    showToast(`Dispute registered for Deal #${id}. Withholding OTP until Admin mediation review.`);
  };

  // Create New Weekly Need
  const handleSaveWeeklyNeed = (e: React.FormEvent) => {
    e.preventDefault();
    const newNeed: WeeklyNeedItem = {
      id: Date.now(),
      crop: newNeedCrop,
      quantityKg: newNeedQty,
      preferredGrade: newNeedGrade,
      maxPriceKg: newNeedMaxPrice,
      frequency: newNeedFreq,
      district: 'Guntur',
      matchedCount: 3,
    };
    setWeeklyNeeds([newNeed, ...weeklyNeeds]);
    setShowNewNeedModal(false);
    showToast(`Weekly requirement for ${newNeedQty} kg ${newNeedCrop} posted.`);
  };

  // Farmer Listing Creation
  const handleCreateFarmerListing = (e: React.FormEvent) => {
    e.preventDefault();
    if (!checklistWholeLot || !checklistCloseUp || !checklistCrate) {
      alert('Photo checklist required: whole lot, close-up, and opened crate must all be captured.');
      return;
    }
    if (photoFreshnessHours > 24) {
      alert('Photos older than 24 hours are rejected. Fresh in-app camera capture required.');
      return;
    }

    const newPin: FarmerLocationPin = {
      listing_id: Date.now(),
      farmer_name: newListingFarmerName,
      variety: newListingVariety,
      quantity_kg: newListingQty,
      grade: newListingGrade,
      expected_price_kg: newListingPrice,
      distance_km: 15.0,
      latitude: 16.295,
      longitude: 80.485,
      match_score: 0.95,
    };

    setFarmerListings([newPin, ...farmerListings]);
    setShowFarmerListModal(false);
    showToast(`Farmer listing by ${newListingFarmerName} published with verified fresh photos!`);
  };

  return (
    <div className="min-h-screen flex flex-col bg-cream">
      <Header
        currentLocale={locale}
        onSelectLocale={handleLocaleChange}
        brandName={t('brand.name')}
        activeNav="portal"
      />

      {/* Floating Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-deep-leaf text-white px-5 py-3 rounded-2xl shadow-xl flex items-center gap-3 animate-slide-up border border-white/20">
          <CheckCircle2 className="w-5 h-5 text-harvest-gold flex-shrink-0" />
          <span className="text-sm font-semibold">{toastMessage}</span>
        </div>
      )}

      <RoleGuard
        allowedRoles={['buyer', 'admin']}
        fallbackTitle="Buyer Portal Access Restricted"
        fallbackMessage="This portal connects verified wholesale buyers, hostels, and institutions with fresh farmer listings. Sign in as a buyer to post requirements and submit offers."
      >
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Top Header Banner: Institutional Profile & Verification Status */}
        <div className="bg-white rounded-3xl border border-border p-6 sm:p-8 shadow-sm mb-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="flex items-start gap-4">
            <div className="w-14 h-14 rounded-2xl bg-harvest-gold/30 text-ink flex items-center justify-center flex-shrink-0">
              <Building className="w-7 h-7" />
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2 mb-1">
                <h1 className="font-heading text-2xl sm:text-3xl font-extrabold text-ink">
                  {buyerName}
                </h1>
                {isVerified ? (
                  <Chip
                    variant="primary"
                    size="sm"
                    icon={<ShieldCheck className="w-4 h-4" />}
                  >
                    Registered Institutional Buyer (Documented)
                  </Chip>
                ) : (
                  <Chip
                    variant="accent"
                    size="sm"
                    icon={<Clock className="w-4 h-4" />}
                  >
                    Pending Verification (Encrypted Proof)
                  </Chip>
                )}
              </div>
              <p className="text-sm text-muted">
                {buyerType} &bull; Guntur District, Andhra Pradesh &bull; 50 km Direct Farmer Sourcing Radius
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
            <Button
              variant="secondary"
              size="md"
              onClick={() => setShowVerifyModal(true)}
              leftIcon={<FileCheck className="w-4 h-4 text-deep-leaf" />}
            >
              {isVerified ? 'Verification Details' : 'Verify Account (GST/Shop)'}
            </Button>
            {isDemoMode && (
              <Button
                variant="primary"
                size="md"
                onClick={() => setShowFarmerListModal(true)}
                leftIcon={<Camera className="w-4 h-4 text-white" />}
              >
                Simulate Farmer Listing
              </Button>
            )}
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-border mb-6 gap-2 sm:gap-6 overflow-x-auto pb-1">
          <button
            onClick={() => setActiveTab('matches')}
            className={`pb-3 px-2 text-sm sm:text-base font-semibold transition-all border-b-2 whitespace-nowrap flex items-center gap-2 ${
              activeTab === 'matches'
                ? 'border-deep-leaf text-deep-leaf'
                : 'border-transparent text-muted hover:text-ink'
            }`}
          >
            <MapPin className="w-4 h-4" />
            <span>Matched Farmers (50 km Radar)</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-deep-leaf/10 text-deep-leaf font-bold">
              {farmerListings.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('needs')}
            className={`pb-3 px-2 text-sm sm:text-base font-semibold transition-all border-b-2 whitespace-nowrap flex items-center gap-2 ${
              activeTab === 'needs'
                ? 'border-deep-leaf text-deep-leaf'
                : 'border-transparent text-muted hover:text-ink'
            }`}
          >
            <Calendar className="w-4 h-4" />
            <span>Weekly Requirements</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-border text-ink font-bold">
              {weeklyNeeds.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('group')}
            className={`pb-3 px-2 text-sm sm:text-base font-semibold transition-all border-b-2 whitespace-nowrap flex items-center gap-2 ${
              activeTab === 'group'
                ? 'border-deep-leaf text-deep-leaf'
                : 'border-transparent text-muted hover:text-ink'
            }`}
          >
            <Users className="w-4 h-4" />
            <span>Group Supply (Multi-Farmer)</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-harvest-gold/40 text-ink font-bold">
              {totalSupplyWithin50km} kg
            </span>
          </button>

          <button
            onClick={() => setActiveTab('orders')}
            className={`pb-3 px-2 text-sm sm:text-base font-semibold transition-all border-b-2 whitespace-nowrap flex items-center gap-2 ${
              activeTab === 'orders'
                ? 'border-deep-leaf text-deep-leaf'
                : 'border-transparent text-muted hover:text-ink'
            }`}
          >
            <CheckCircle2 className="w-4 h-4" />
            <span>Offers & Active Deals</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-deep-leaf text-white font-bold">
              {deals.length + offers.length}
            </span>
          </button>
        </div>

        {/* TAB 1: MATCHED FARMERS WITHIN 50 KM */}
        {activeTab === 'matches' && (
          <div className="space-y-6">
            {/* Interactive Map */}
            <MapLibreView
              buyerLat={16.3067}
              buyerLng={80.4365}
              buyerName={buyerName}
              farmerPins={farmerListings}
              selectedListingId={selectedListing?.listing_id}
              onSelectListing={(listing) => {
                setSelectedListing(listing);
                setOfferPriceInput(listing.expected_price_kg);
                setOfferQtyInput(listing.quantity_kg);
              }}
            />

            {/* List of Matched Farmer Cards */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="font-heading text-xl font-bold text-ink">
                    Farmer Listings within 50 km
                  </h2>
                  <p className="text-xs text-muted">
                    Ranked by Haversine distance, quantity match, grade match, and reliability score.
                  </p>
                </div>
                <span className="text-xs font-semibold text-deep-leaf bg-deep-leaf/10 px-3 py-1.5 rounded-full">
                  Zero Commission Platform
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {farmerListings.map((listing) => {
                  const isSelected = selectedListing?.listing_id === listing.listing_id;

                  return (
                    <Card
                      key={listing.listing_id}
                      className={`p-5 transition-all ${
                        isSelected
                          ? 'border-2 border-deep-leaf ring-4 ring-deep-leaf/10'
                          : 'hover:border-deep-leaf/50'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3 mb-3">
                        <div>
                          <div className="flex items-center gap-2">
                            <h3 className="font-heading text-lg font-bold text-ink">
                              {listing.farmer_name}
                            </h3>
                            <Chip
                              variant={
                                listing.grade === 'A'
                                  ? 'primary'
                                  : listing.grade === 'B'
                                  ? 'default'
                                  : 'accent'
                              }
                              size="sm"
                            >
                              Grade {listing.grade}
                            </Chip>
                          </div>
                          <p className="text-xs text-muted mt-0.5">
                            {listing.variety} Banana &bull; Tenali / Guntur Belt
                          </p>
                        </div>

                        <div className="text-right">
                          <span className="text-2xl font-extrabold text-deep-leaf">
                            ₹{listing.expected_price_kg}
                          </span>
                          <span className="text-xs text-muted block">/ kg</span>
                        </div>
                      </div>

                      {/* Details row */}
                      <div className="grid grid-cols-3 gap-2 py-3 border-y border-border text-center text-xs mb-3">
                        <div>
                          <span className="text-muted block text-[11px]">Distance</span>
                          <span className="font-bold text-ink">
                            {listing.distance_km.toFixed(1)} km
                          </span>
                        </div>
                        <div>
                          <span className="text-muted block text-[11px]">Available</span>
                          <span className="font-bold text-ink">
                            {listing.quantity_kg} kg
                          </span>
                        </div>
                        <div>
                          <span className="text-muted block text-[11px]">Match Score</span>
                          <span className="font-bold text-deep-leaf">
                            {Math.round((listing.match_score || 0.9) * 100)}%
                          </span>
                        </div>
                      </div>

                      {/* Photo checklist verification pill */}
                      <div className="bg-cream/60 rounded-xl p-2.5 mb-4 text-xs flex items-center justify-between text-muted">
                        <div className="flex items-center gap-2">
                          <Camera className="w-3.5 h-3.5 text-deep-leaf" />
                          <span className="font-semibold text-ink">
                            3-Photo Verification:
                          </span>
                        </div>
                        <div className="flex items-center gap-2 text-[11px] font-medium text-deep-leaf">
                          <span className="inline-flex items-center gap-0.5"><CheckCircle2 className="w-3 h-3 text-deep-leaf" /> Lot</span>
                          <span className="inline-flex items-center gap-0.5"><CheckCircle2 className="w-3 h-3 text-deep-leaf" /> Close-up</span>
                          <span className="inline-flex items-center gap-0.5"><CheckCircle2 className="w-3 h-3 text-deep-leaf" /> Crate</span>
                          <span className="text-muted font-normal text-[10px]">&bull; Fresh (&lt;24h)</span>
                        </div>
                      </div>

                      {/* Action buttons */}
                      <div className="flex items-center gap-2">
                        <Button
                          variant="primary"
                          size="md"
                          className="flex-1 text-xs py-2 h-9 min-h-[36px]"
                          onClick={() => {
                            setSelectedListing(listing);
                            setOfferPriceInput(listing.expected_price_kg);
                            setOfferQtyInput(listing.quantity_kg);
                          }}
                        >
                          Make Direct Offer
                        </Button>
                        <Button
                          variant="secondary"
                          size="md"
                          className="text-xs py-2 h-9 min-h-[36px]"
                          onClick={() => handleInitiateMaskedCall(listing.farmer_name)}
                          leftIcon={<PhoneCall className="w-3.5 h-3.5 text-deep-leaf" />}
                        >
                          Masked Call
                        </Button>
                      </div>
                    </Card>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: WEEKLY REQUIREMENTS (TENDER) */}
        {activeTab === 'needs' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-heading text-xl font-bold text-ink">
                  Institutional Weekly Demands
                </h2>
                <p className="text-xs text-muted">
                  Auto-broadcasted to registered farmers within 50 km of your kitchen/hostel.
                </p>
              </div>
              <Button
                variant="primary"
                size="md"
                className="text-xs px-3 py-1.5 h-9 min-h-[36px]"
                onClick={() => setShowNewNeedModal(true)}
                leftIcon={<PlusCircle className="w-4 h-4 text-white" />}
              >
                Post New Requirement
              </Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {weeklyNeeds.map((need) => (
                <Card key={need.id} className="p-6">
                  <div className="flex items-start justify-between gap-3 mb-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-heading text-xl font-bold text-ink">
                          {need.quantityKg} kg {need.crop}
                        </h3>
                        <Chip variant="default" size="sm">
                          Grade {need.preferredGrade}
                        </Chip>
                      </div>
                      <p className="text-xs text-muted mt-1">
                        Schedule: {need.frequency} &bull; Delivery: {need.district}
                      </p>
                    </div>
                    <div className="text-right">
                      <span className="text-xs text-muted block">Budget Max</span>
                      <span className="text-lg font-bold text-deep-leaf">
                        ₹{need.maxPriceKg}/kg
                      </span>
                    </div>
                  </div>

                  <div className="bg-cream/70 rounded-2xl p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-xl bg-deep-leaf/10 text-deep-leaf flex items-center justify-center font-bold text-sm">
                        {need.matchedCount}
                      </div>
                      <div>
                        <span className="text-xs font-bold text-ink block">
                          {need.matchedCount} Nearby Farmers Match
                        </span>
                        <span className="text-[11px] text-muted">
                          Within 50 km delivery zone
                        </span>
                      </div>
                    </div>

                    <Button
                      variant="secondary"
                      size="md"
                      className="text-xs px-3 py-1.5 h-9 min-h-[36px]"
                      onClick={() => setActiveTab('matches')}
                      rightIcon={<ArrowRight className="w-3.5 h-3.5" />}
                    >
                      View Matches
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          </div>
        )}

        {/* TAB 3: GROUP SUPPLY (MULTI-FARMER AGGREGATION) */}
        {activeTab === 'group' && (
          <div className="space-y-6">
            <Card className="p-6 sm:p-8 bg-white border border-border">
              <div className="max-w-2xl">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-harvest-gold/30 text-ink text-xs font-semibold mb-3">
                  <Users className="w-3.5 h-3.5 text-deep-leaf" />
                  <span>Institutional Bulk Aggregator</span>
                </div>
                <h2 className="font-heading text-2xl font-bold text-ink mb-2">
                  Group Supply from Nearby Farmers
                </h2>
                <p className="text-sm text-muted mb-6">
                  Institutions, hostels, and colleges often require several tonnes per week that no
                  individual smallholder farmer can supply alone. GrowCircle bundles nearby registered
                  farmers within 50 km to meet your aggregate order at a fair combined rate.
                </p>
              </div>

              {/* Aggregation Summary Metric Banner */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
                <div className="bg-cream rounded-2xl p-4 border border-border">
                  <span className="text-xs text-muted block">Total Pooled Supply</span>
                  <span className="text-3xl font-extrabold text-ink">
                    {totalSupplyWithin50km} kg
                  </span>
                  <span className="text-xs text-deep-leaf font-semibold block mt-1">
                    ({(totalSupplyWithin50km / 1000).toFixed(1)} tonnes)
                  </span>
                </div>

                <div className="bg-cream rounded-2xl p-4 border border-border">
                  <span className="text-xs text-muted block">Participating Farmers</span>
                  <span className="text-3xl font-extrabold text-deep-leaf">
                    {farmerListings.length}
                  </span>
                  <span className="text-xs text-muted block mt-1">
                    All within 40 km radius
                  </span>
                </div>

                <div className="bg-cream rounded-2xl p-4 border border-border">
                  <span className="text-xs text-muted block">Weighted Avg Price</span>
                  <span className="text-3xl font-extrabold text-amber">
                    ₹{avgWeightedPrice}
                  </span>
                  <span className="text-xs text-muted block mt-1">
                    / kg combined rate
                  </span>
                </div>
              </div>

              {/* Farmers in the Bundle */}
              <h3 className="font-heading text-lg font-bold text-ink mb-3">
                Bundled Farmer Lots (Ready for Pickup)
              </h3>
              <div className="divide-y divide-border border border-border rounded-2xl overflow-hidden mb-6">
                {farmerListings.map((farmer, idx) => (
                  <div
                    key={farmer.listing_id}
                    className="p-4 bg-white flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-sm"
                  >
                    <div className="flex items-center gap-3">
                      <span className="w-6 h-6 rounded-full bg-deep-leaf/10 text-deep-leaf font-bold text-xs flex items-center justify-center">
                        {idx + 1}
                      </span>
                      <div>
                        <span className="font-bold text-ink block">
                          {farmer.farmer_name}
                        </span>
                        <span className="text-xs text-muted">
                          {farmer.variety} &bull; Grade {farmer.grade} &bull; {farmer.distance_km.toFixed(1)} km away
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-6 sm:text-right">
                      <div>
                        <span className="text-xs text-muted block">Supply</span>
                        <span className="font-bold text-ink">
                          {farmer.quantity_kg} kg
                        </span>
                      </div>
                      <div>
                        <span className="text-xs text-muted block">Price</span>
                        <span className="font-bold text-deep-leaf">
                          ₹{farmer.expected_price_kg}/kg
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="flex items-center justify-between flex-wrap gap-4 pt-4 border-t border-border">
                <div className="text-xs text-muted flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-deep-leaf" />
                  <span>Single dispatch trip can collect all {farmerListings.length} lots</span>
                </div>

                <Button
                  variant="primary"
                  size="md"
                  onClick={() => {
                    showToast('Group supply tender created! Farmers notified via voice IVR and WhatsApp.');
                  }}
                  rightIcon={<ArrowRight className="w-4 h-4" />}
                >
                  Create Group Supply Contract ({totalSupplyWithin50km} kg)
                </Button>
              </div>
            </Card>
          </div>
        )}

        {/* TAB 4: OFFERS & ACTIVE DEALS */}
        {activeTab === 'orders' && (
          <div className="space-y-8">
            {/* Active Negotiations / Offers */}
            <div>
              <h2 className="font-heading text-xl font-bold text-ink mb-1">
                Active Negotiations & Counter-Offers
              </h2>
              <p className="text-xs text-muted mb-4">
                Accepting an offer triggers explicit read-back confirmation.
              </p>

              {offers.length === 0 ? (
                <Card className="p-8 text-center text-muted text-sm">
                  No active negotiations right now. Select a farmer from the radar to send an offer!
                </Card>
              ) : (
                <div className="space-y-3">
                  {offers.map((offer) => (
                    <Card key={offer.offerId} className="p-5">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                        <div>
                          <div className="flex items-center gap-2">
                            <h3 className="font-heading text-base font-bold text-ink">
                              {offer.quantityKg} kg {offer.variety} {offer.crop}
                            </h3>
                            <Chip
                              variant={offer.status === 'countered' ? 'accent' : 'default'}
                              size="sm"
                            >
                              {offer.status === 'countered'
                                ? 'Farmer Countered'
                                : offer.status === 'accepted'
                                ? 'Accepted'
                                : 'Awaiting Reply'}
                            </Chip>
                          </div>
                          <p className="text-xs text-muted mt-1">
                            Farmer: {offer.farmerName} &bull; {offer.distanceKm} km away &bull; Grade {offer.grade}
                          </p>
                        </div>

                        <div className="flex items-center gap-6">
                          <div>
                            <span className="text-xs text-muted block">Your Offer</span>
                            <span className="text-base font-bold text-ink">
                              ₹{offer.offeredPriceKg}/kg
                            </span>
                          </div>

                          {offer.farmerCounterPriceKg && (
                            <div className="bg-amber/10 px-3 py-1.5 rounded-xl border border-amber/20">
                              <span className="text-xs text-amber font-semibold block">
                                Farmer Counter
                              </span>
                              <span className="text-base font-extrabold text-amber">
                                ₹{offer.farmerCounterPriceKg}/kg
                              </span>
                            </div>
                          )}

                          {offer.status === 'countered' && (
                            <Button
                              variant="primary"
                              size="md"
                              className="text-xs px-3 py-1.5 h-9 min-h-[36px]"
                              onClick={() => triggerAcceptOfferReadBack(offer)}
                            >
                              Accept Counter
                            </Button>
                          )}
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </div>

            {/* Finalized Deals & Orders */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="font-heading text-xl font-bold text-ink">
                    Finalized Deals & Orders
                  </h2>
                  <p className="text-xs text-muted">
                    No payment custody. Buyers verify produce physical grade upon delivery and share the secret Handover OTP.
                  </p>
                </div>
              </div>

              <div className="space-y-4">
                {deals.map((deal) => (
                  <Card key={deal.dealId} className="p-6 bg-white border border-border">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4 pb-4 border-b border-border">
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-heading text-lg font-bold text-ink">
                            Deal #{deal.dealId.toString().slice(-4)} &bull; {deal.quantityKg} kg {deal.variety}
                          </h3>
                          <Chip
                            variant={
                              deal.status === 'disputed'
                                ? 'danger'
                                : deal.status === 'pending_delivery'
                                ? 'accent'
                                : 'primary'
                            }
                            size="sm"
                          >
                            {deal.status === 'disputed'
                              ? 'Disputed by Buyer'
                              : deal.status === 'pending_delivery'
                              ? 'Pending Physical Handover'
                              : 'Completed & Delivered'}
                          </Chip>
                        </div>
                        <p className="text-xs text-muted mt-1">
                          Farmer: {deal.farmerName} &bull; Created {deal.createdAt}
                        </p>
                      </div>

                      <div className="flex items-center gap-4 text-right">
                        <div>
                          <span className="text-xs text-muted block">Agreed Price</span>
                          <span className="text-lg font-extrabold text-deep-leaf">
                            ₹{deal.agreedPriceKg}/kg
                          </span>
                        </div>
                        <div className="pl-4 border-l border-border">
                          <span className="text-xs text-muted block">Total Deal Value</span>
                          <span className="text-lg font-extrabold text-ink">
                            ₹{deal.totalAmount.toLocaleString('en-IN')}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Transporter Assignment & Matched 3 Drivers Callout */}
                    <div className="bg-cream/70 rounded-2xl p-4 border border-border mb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <div className="flex items-start gap-3">
                        <div className="w-10 h-10 rounded-xl bg-deep-leaf/10 text-deep-leaf flex items-center justify-center flex-shrink-0 mt-0.5">
                          <Truck className="w-5 h-5" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-ink uppercase tracking-wide">
                              Transport Logistics:
                            </span>
                            {assignedTransporterByDeal[deal.dealId] ? (
                              <Chip variant="primary" size="sm">
                                Assigned: {assignedTransporterByDeal[deal.dealId]}
                              </Chip>
                            ) : (
                              <Chip variant="default" size="sm">
                                Load: {deal.quantityKg < 500 ? 'Goods Auto (<500kg)' : deal.quantityKg <= 1500 ? 'Mini-Truck (500kg-1.5t)' : 'Large Truck (>1.5t)'}
                              </Chip>
                            )}
                          </div>
                          <p className="text-xs text-muted mt-0.5">
                            {assignedTransporterByDeal[deal.dealId]
                              ? 'Driver dispatched for farm gate pickup with secure OTP handshake.'
                              : `3 nearby available drivers near ${deal.farmerName}'s farm matched to this ${deal.quantityKg} kg load.`}
                          </p>
                        </div>
                      </div>

                      {!assignedTransporterByDeal[deal.dealId] && (
                        <Button
                          variant="primary"
                          size="md"
                          className="text-xs whitespace-nowrap"
                          onClick={() => setSelectedDealForTransport(deal)}
                          leftIcon={<Truck className="w-4 h-4" />}
                        >
                          Find Drivers (3 Matched)
                        </Button>
                      )}
                    </div>

                    {/* Freight Pooling v1 Banner */}
                    <div className="bg-harvest-gold/15 rounded-2xl p-3 border border-harvest-gold/30 mb-4 flex items-center justify-between text-xs text-ink gap-2">
                      <div className="flex items-center gap-2">
                        <Layers className="w-4 h-4 text-ink flex-shrink-0" />
                        <span>
                          <strong>Rule-Based Pooling Available:</strong> Group this {deal.quantityKg} kg lot with nearby Tenali farmers to save up to 19% on freight!
                        </span>
                      </div>
                      <span className="font-bold text-deep-leaf whitespace-nowrap">
                        15 km Cluster
                      </span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 items-center">
                      {/* Delivery OTP box */}
                      <div className="bg-cream rounded-2xl p-4 border border-border flex items-center justify-between">
                        <div>
                          <span className="text-xs font-semibold text-muted block uppercase tracking-wide">
                            Secret Delivery OTP
                          </span>
                          <span className="text-2xl font-mono font-extrabold text-deep-leaf tracking-widest">
                            {deal.status === 'disputed' ? 'LOCKED' : deal.deliveryOtp}
                          </span>
                        </div>
                        <p className="text-[11px] text-muted max-w-[150px] text-right">
                          {deal.status === 'disputed'
                            ? 'OTP withheld pending Admin mediation'
                            : 'Share with driver ONLY after inspecting crates'}
                        </p>
                      </div>

                      {/* Action buttons */}
                      <div className="flex items-center gap-2 flex-wrap">
                        <Button
                          variant="secondary"
                          size="md"
                          className="flex-1 text-xs"
                          onClick={() => handleInitiateMaskedCall(deal.farmerName)}
                          leftIcon={<PhoneCall className="w-4 h-4 text-deep-leaf" />}
                        >
                          Call Farmer
                        </Button>

                        {deal.status === 'pending_delivery' && (
                          <Button
                            variant="secondary"
                            size="md"
                            className="text-xs text-danger hover:bg-danger/10 border-danger/20"
                            onClick={() => setDisputingDeal(deal)}
                            leftIcon={<Scale className="w-4 h-4 text-danger" />}
                          >
                            Report Dispute
                          </Button>
                        )}

                        <Button
                          variant="secondary"
                          size="md"
                          className="text-xs"
                          onClick={() => {
                            showToast(`Feedback recorded: 5-star reliability rating given to ${deal.farmerName}!`);
                          }}
                          leftIcon={<Star className="w-4 h-4 text-amber" />}
                        >
                          Rate
                        </Button>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          </div>
        )}
      </main>
      </RoleGuard>

      {/* MAKE OFFER MODAL */}
      {selectedListing && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl border border-border animate-scale-in">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-heading text-xl font-bold text-ink">
                Make Offer to {selectedListing.farmer_name}
              </h3>
              <button
                onClick={() => setSelectedListing(null)}
                className="p-1 rounded-full text-muted hover:text-ink hover:bg-black/5"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="bg-cream rounded-2xl p-4 mb-5 text-sm space-y-1">
              <p className="font-semibold text-ink">
                {selectedListing.variety} Banana &bull; Grade {selectedListing.grade}
              </p>
              <p className="text-xs text-muted">
                Available: {selectedListing.quantity_kg} kg &bull; Farmer asking: ₹{selectedListing.expected_price_kg}/kg
              </p>
            </div>

            <form onSubmit={handleCreateOffer} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-ink mb-1">
                  Offered Price (₹ / kg)
                </label>
                <input
                  type="number"
                  step="0.5"
                  min="1"
                  value={offerPriceInput}
                  onChange={(e) => setOfferPriceInput(parseFloat(e.target.value) || 0)}
                  className="w-full px-4 py-2.5 rounded-xl border border-border bg-white text-ink text-base font-bold focus:outline-none focus:ring-2 focus:ring-deep-leaf"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-ink mb-1">
                  Quantity Required (kg)
                </label>
                <input
                  type="number"
                  step="50"
                  min="50"
                  max={selectedListing.quantity_kg}
                  value={offerQtyInput}
                  onChange={(e) => setOfferQtyInput(parseInt(e.target.value) || 0)}
                  className="w-full px-4 py-2.5 rounded-xl border border-border bg-white text-ink text-base font-bold focus:outline-none focus:ring-2 focus:ring-deep-leaf"
                />
              </div>

              <div className="p-3 bg-deep-leaf/5 rounded-xl text-xs text-muted flex items-center justify-between">
                <span>Total Offer Amount:</span>
                <span className="font-extrabold text-deep-leaf text-base">
                  ₹{(offerPriceInput * offerQtyInput).toLocaleString('en-IN')}
                </span>
              </div>

              <div className="flex items-center gap-3 pt-2">
                <Button
                  type="button"
                  variant="secondary"
                  className="flex-1"
                  onClick={() => setSelectedListing(null)}
                >
                  Cancel
                </Button>
                <Button type="submit" variant="primary" className="flex-1">
                  Send Offer
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* READ-BACK CONFIRMATION MODAL */}
      {showReadBackModal && readBackTarget && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-lg w-full p-6 sm:p-8 shadow-2xl border-2 border-deep-leaf animate-scale-in">
            <div className="flex items-center gap-3 mb-4 text-deep-leaf">
              <Volume2 className="w-6 h-6 flex-shrink-0 animate-pulse" />
              <h3 className="font-heading text-xl font-extrabold text-ink">
                Read-Back Confirmation
              </h3>
            </div>

            <div className="bg-cream/90 rounded-2xl p-5 mb-6 border border-border leading-relaxed text-sm text-ink space-y-3">
              <p className="font-bold text-base text-deep-leaf">
                Please verify the agreed transaction terms:
              </p>
              <div className="divide-y divide-border/60 text-xs sm:text-sm">
                <div className="py-1.5 flex justify-between">
                  <span className="text-muted">Farmer:</span>
                  <span className="font-bold">{readBackTarget.farmerName}</span>
                </div>
                <div className="py-1.5 flex justify-between">
                  <span className="text-muted">Produce:</span>
                  <span className="font-bold">{readBackTarget.crop}</span>
                </div>
                <div className="py-1.5 flex justify-between">
                  <span className="text-muted">Quantity:</span>
                  <span className="font-bold">{readBackTarget.quantityKg} kg</span>
                </div>
                <div className="py-1.5 flex justify-between">
                  <span className="text-muted">Agreed Price:</span>
                  <span className="font-bold text-deep-leaf">₹{readBackTarget.priceKg}/kg</span>
                </div>
                <div className="py-1.5 flex justify-between font-bold text-base pt-2">
                  <span>Total Amount:</span>
                  <span className="text-ink">₹{readBackTarget.totalAmount.toLocaleString('en-IN')}</span>
                </div>
              </div>
              <p className="text-[11px] text-muted italic pt-2">
                &bull; Zero payment custody: Payment is settled directly upon physical produce delivery.
                <br />
                &bull; A 6-digit secret OTP is generated to confirm inspection and release.
              </p>
            </div>

            <label className="flex items-start gap-3 cursor-pointer select-none mb-6 p-2 rounded-xl hover:bg-cream/50">
              <input
                type="checkbox"
                checked={readBackConfirmed}
                onChange={(e) => setReadBackConfirmed(e.target.checked)}
                className="mt-1 w-5 h-5 rounded border-border text-deep-leaf focus:ring-deep-leaf"
              />
              <span className="text-xs sm:text-sm text-ink font-semibold">
                I have reviewed and confirmed all details above. I agree to finalize this deal.
              </span>
            </label>

            <div className="flex items-center gap-3">
              <Button
                variant="secondary"
                size="md"
                className="flex-1"
                onClick={() => setShowReadBackModal(false)}
              >
                Go Back
              </Button>
              <Button
                variant="primary"
                size="md"
                className="flex-1"
                disabled={!readBackConfirmed}
                onClick={confirmAcceptDeal}
              >
                Confirm & Create Deal
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* MASKED CALL MODAL */}
      {showCallModal && callContext && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl border border-border animate-scale-in text-center">
            <div className="w-16 h-16 rounded-full bg-deep-leaf/10 text-deep-leaf mx-auto flex items-center justify-center mb-4">
              <PhoneCall className="w-8 h-8 animate-bounce" />
            </div>

            <h3 className="font-heading text-xl font-bold text-ink mb-1">
              Masked Telephony Bridge Active
            </h3>
            <p className="text-xs text-muted mb-4">
              Connecting you with <strong>{callContext.farmerName}</strong> without revealing either personal phone number.
            </p>

            <div className="bg-cream rounded-2xl p-4 mb-6 border border-border">
              <span className="text-xs text-muted block mb-1">GrowCircle Virtual Bridge</span>
              <span className="text-lg font-mono font-bold text-deep-leaf">
                {callContext.maskedNumber}
              </span>
              <span className="text-[10px] text-muted block mt-1">
                Session ID: {callContext.sessionId}
              </span>
            </div>

            <Button
              variant="primary"
              size="md"
              className="w-full"
              onClick={() => setShowCallModal(false)}
            >
              End Masked Call Simulation
            </Button>
          </div>
        </div>
      )}

      {/* BUYER VERIFICATION & GST MODAL */}
      {showVerifyModal && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl border border-border animate-scale-in">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-heading text-xl font-bold text-ink">
                Buyer Verification & Proof
              </h3>
              <button
                onClick={() => setShowVerifyModal(false)}
                className="p-1 rounded-full text-muted hover:text-ink hover:bg-black/5"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-3 bg-deep-leaf/10 rounded-2xl text-xs text-deep-leaf font-semibold mb-4 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 flex-shrink-0" />
              <span>DPDP Act Compliance: All GST and proof files are stored AES-256 encrypted at rest.</span>
            </div>

            <div className="space-y-4 text-sm">
              <div>
                <label className="block text-xs font-bold text-ink mb-1">
                  Institution / Business Name
                </label>
                <input
                  type="text"
                  value={buyerName}
                  onChange={(e) => setBuyerName(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl border border-border text-ink font-semibold"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-ink mb-1">
                  GSTIN (Encrypted at Rest)
                </label>
                <input
                  type="text"
                  value={gstInput}
                  onChange={(e) => setGstInput(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl border border-border text-ink font-mono font-bold"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-ink mb-1">
                  Shop Act / Institution Proof Document
                </label>
                <input
                  type="text"
                  value={docRefInput}
                  onChange={(e) => setDocRefInput(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl border border-border text-ink font-mono text-xs"
                />
              </div>

              <div className="pt-2">
                <Button
                  variant="primary"
                  size="md"
                  className="w-full"
                  onClick={() => {
                    setIsVerified(true);
                    setShowVerifyModal(false);
                    showToast('Proof submitted and encrypted! Account documented for direct trade.');
                  }}
                >
                  Save Encrypted Proof
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* NEW WEEKLY NEED MODAL */}
      {showNewNeedModal && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl border border-border animate-scale-in">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-heading text-xl font-bold text-ink">
                Post Weekly Requirement
              </h3>
              <button
                onClick={() => setShowNewNeedModal(false)}
                className="p-1 rounded-full text-muted hover:text-ink hover:bg-black/5"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveWeeklyNeed} className="space-y-4 text-sm">
              <div>
                <label className="block text-xs font-bold text-ink mb-1">Crop</label>
                <input
                  type="text"
                  value={newNeedCrop}
                  onChange={(e) => setNewNeedCrop(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl border border-border"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-ink mb-1">Quantity (kg)</label>
                  <input
                    type="number"
                    value={newNeedQty}
                    onChange={(e) => setNewNeedQty(parseInt(e.target.value) || 0)}
                    className="w-full px-3.5 py-2 rounded-xl border border-border font-bold"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-ink mb-1">Preferred Grade</label>
                  <select
                    value={newNeedGrade}
                    onChange={(e) => setNewNeedGrade(e.target.value)}
                    className="w-full px-3.5 py-2 rounded-xl border border-border font-bold"
                  >
                    <option value="A">Grade A (Uniform, blemish-free)</option>
                    <option value="B">Grade B (Kitchen grade, firm)</option>
                    <option value="C">Grade C (Processing, ripe)</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-ink mb-1">Max Price (₹/kg)</label>
                  <input
                    type="number"
                    value={newNeedMaxPrice}
                    onChange={(e) => setNewNeedMaxPrice(parseFloat(e.target.value) || 0)}
                    className="w-full px-3.5 py-2 rounded-xl border border-border font-bold"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-ink mb-1">Frequency</label>
                  <select
                    value={newNeedFreq}
                    onChange={(e) => setNewNeedFreq(e.target.value)}
                    className="w-full px-3.5 py-2 rounded-xl border border-border font-bold"
                  >
                    <option value="Weekly (Every Monday)">Weekly</option>
                    <option value="Twice Weekly">Twice Weekly</option>
                    <option value="Daily">Daily</option>
                  </select>
                </div>
              </div>

              <div className="pt-2 flex gap-3">
                <Button
                  type="button"
                  variant="secondary"
                  className="flex-1"
                  onClick={() => setShowNewNeedModal(false)}
                >
                  Cancel
                </Button>
                <Button type="submit" variant="primary" className="flex-1">
                  Save Requirement
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* SIMULATE FARMER LISTING CREATION (DEMO & TESTING DOOR) */}
      {isDemoMode && showFarmerListModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-3xl max-w-lg w-full p-6 sm:p-8 shadow-2xl border border-border animate-scale-in my-8">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Camera className="w-6 h-6 text-deep-leaf" />
                <h3 className="font-heading text-xl font-bold text-ink">
                  Farmer Produce Listing
                </h3>
              </div>
              <button
                onClick={() => setShowFarmerListModal(false)}
                className="p-1 rounded-full text-muted hover:text-ink hover:bg-black/5"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-muted mb-4">
              Requires fresh camera capture (&lt;24 hours, rejecting old gallery files) and mandatory 3-photo checklist.
            </p>

            <form onSubmit={handleCreateFarmerListing} className="space-y-4 text-sm">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-ink mb-1">Farmer Name</label>
                  <input
                    type="text"
                    value={newListingFarmerName}
                    onChange={(e) => setNewListingFarmerName(e.target.value)}
                    className="w-full px-3.5 py-2 rounded-xl border border-border font-semibold"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-ink mb-1">Variety</label>
                  <input
                    type="text"
                    value={newListingVariety}
                    onChange={(e) => setNewListingVariety(e.target.value)}
                    className="w-full px-3.5 py-2 rounded-xl border border-border font-semibold"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-ink mb-1">Quantity (kg)</label>
                  <input
                    type="number"
                    value={newListingQty}
                    onChange={(e) => setNewListingQty(parseInt(e.target.value) || 0)}
                    className="w-full px-3.5 py-2 rounded-xl border border-border font-bold"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-ink mb-1">Expected Price (₹/kg)</label>
                  <input
                    type="number"
                    step="0.5"
                    value={newListingPrice}
                    onChange={(e) => setNewListingPrice(parseFloat(e.target.value) || 0)}
                    className="w-full px-3.5 py-2 rounded-xl border border-border font-bold text-deep-leaf"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-ink mb-1">Quality Grade</label>
                <div className="grid grid-cols-3 gap-2">
                  {(['A', 'B', 'C'] as const).map((grade) => (
                    <button
                      key={grade}
                      type="button"
                      onClick={() => setNewListingGrade(grade)}
                      className={`p-2.5 rounded-xl border text-xs font-bold text-center transition-all ${
                        newListingGrade === grade
                          ? 'border-deep-leaf bg-deep-leaf text-white shadow-sm'
                          : 'border-border bg-white text-ink hover:bg-cream'
                      }`}
                    >
                      Grade {grade}
                    </button>
                  ))}
                </div>
                <p className="text-[11px] text-muted mt-1.5">
                  {newListingGrade === 'A' && 'Grade A: Uniform size, blemish-free skin, export/supermarket grade.'}
                  {newListingGrade === 'B' && 'Grade B: Slight cosmetic marks, good firmness, ideal for kitchens.'}
                  {newListingGrade === 'C' && 'Grade C: Variable size, ripe peel, processing/immediate use.'}
                </p>
              </div>

              {/* Mandatory 3-Photo Checklist */}
              <div className="bg-cream rounded-2xl p-4 border border-border">
                <span className="text-xs font-bold text-ink block mb-2">
                  Mandatory 3-Photo Checklist (In-App Camera)
                </span>
                <div className="space-y-2 text-xs">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={checklistWholeLot}
                      onChange={(e) => setChecklistWholeLot(e.target.checked)}
                      className="rounded text-deep-leaf"
                    />
                    <span>1. Whole Lot overview photo</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={checklistCloseUp}
                      onChange={(e) => setChecklistCloseUp(e.target.checked)}
                      className="rounded text-deep-leaf"
                    />
                    <span>2. Close-up photo showing peel texture</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={checklistCrate}
                      onChange={(e) => setChecklistCrate(e.target.checked)}
                      className="rounded text-deep-leaf"
                    />
                    <span>3. One opened crate cross-section</span>
                  </label>
                </div>

                <div className="mt-3 pt-2 border-t border-border/60 flex items-center justify-between text-[11px]">
                  <span className="text-muted">Simulated Photo Age:</span>
                  <select
                    value={photoFreshnessHours}
                    onChange={(e) => setPhotoFreshnessHours(parseFloat(e.target.value))}
                    className="bg-white border border-border rounded px-2 py-0.5 text-ink font-semibold"
                  >
                    <option value={1.5}>1.5 hours ago (Fresh - Accepted)</option>
                    <option value={12}>12 hours ago (Fresh - Accepted)</option>
                    <option value={48}>48 hours ago (Old - Will be Rejected!)</option>
                  </select>
                </div>
              </div>

              <div className="pt-2 flex gap-3">
                <Button
                  type="button"
                  variant="secondary"
                  className="flex-1"
                  onClick={() => setShowFarmerListModal(false)}
                >
                  Cancel
                </Button>
                <Button type="submit" variant="primary" className="flex-1">
                  Publish Listing
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* SUGGESTED TRANSPORTERS MODAL (3 MATCHED DRIVERS) */}
      {selectedDealForTransport && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-3xl max-w-xl w-full p-6 sm:p-8 shadow-2xl border border-border animate-scale-in my-8">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2.5">
                <div className="w-10 h-10 rounded-2xl bg-deep-leaf/10 text-deep-leaf flex items-center justify-center">
                  <Truck className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-heading text-xl font-bold text-ink">
                    Matched Transporters Near Farm
                  </h3>
                  <p className="text-xs text-muted">
                    Post-deal dispatch matched to {selectedDealForTransport.quantityKg} kg load
                  </p>
                </div>
              </div>
              <button
                onClick={() => setSelectedDealForTransport(null)}
                className="p-1 rounded-full text-muted hover:text-ink hover:bg-black/5"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Load Classification Pill */}
            <div className="bg-cream rounded-2xl p-4 border border-border mb-5 flex items-center justify-between text-xs">
              <div>
                <span className="text-muted block">Recommended Vehicle Class:</span>
                <strong className="text-ink text-sm">
                  {selectedDealForTransport.quantityKg < 500
                    ? 'Goods Auto (Under 500 kg)'
                    : selectedDealForTransport.quantityKg <= 1500
                    ? 'Mini-Truck (500 kg to 1.5 t)'
                    : 'Large Truck (Above 1.5 t)'}
                </strong>
              </div>
              <Chip variant="primary" size="sm">
                3 Matched Drivers
              </Chip>
            </div>

            {/* Guide Rate Disclaimer Banner */}
            <div className="bg-amber/10 border border-amber/25 rounded-2xl p-3 mb-5 text-[11px] text-ink leading-relaxed">
              <strong className="text-amber block mb-0.5">Indicative Guide Rate Notice:</strong>
              Fares are computed as base fare + (distance &times; per-km vehicle rate). This is strictly an indicative guide, not a fixed price. Transporter and farmer/buyer negotiate and settle final freight charges directly.
            </div>

            {/* 3 Driver Cards */}
            <div className="space-y-3 mb-6">
              {[
                {
                  id: 1,
                  name: 'Venkat Rao',
                  vehicle: 'Tata Ace Gold (Goods Auto / Mini)',
                  rating: 4.9,
                  trips: 42,
                  distanceKm: 12.4,
                  guideFare: Math.round(150 + 12.4 * 18),
                  phone: '+919848099881',
                },
                {
                  id: 2,
                  name: 'Satyanarayana Murthy',
                  vehicle: 'Mahindra Bolero Maxi Truck',
                  rating: 4.8,
                  trips: 38,
                  distanceKm: 15.2,
                  guideFare: Math.round(150 + 15.2 * 18),
                  phone: '+919440122334',
                },
                {
                  id: 3,
                  name: 'Mallikarjun Rao',
                  vehicle: 'Piaggio Ape Auto Xtra',
                  rating: 4.7,
                  trips: 29,
                  distanceKm: 18.0,
                  guideFare: Math.round(150 + 18.0 * 18),
                  phone: '+919848011990',
                },
              ].map((driver) => (
                <div
                  key={driver.id}
                  className="bg-cream/50 rounded-2xl p-4 border border-border flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:border-deep-leaf/40 transition-colors"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className="font-heading text-sm font-bold text-ink">
                        {driver.name}
                      </h4>
                      <div className="flex items-center text-[11px] font-bold text-amber">
                        <Star className="w-3 h-3 fill-amber mr-0.5" />
                        {driver.rating}
                      </div>
                    </div>
                    <p className="text-xs text-muted mt-0.5">{driver.vehicle}</p>
                    <p className="text-[11px] text-muted">
                      {driver.distanceKm} km from farm &bull; {driver.trips} completed trips
                    </p>
                  </div>

                  <div className="flex items-center gap-3 justify-between sm:justify-end">
                    <div className="text-right">
                      <span className="text-[10px] text-muted block uppercase">Guide Fare</span>
                      <span className="text-base font-extrabold text-deep-leaf">
                        ₹{driver.guideFare}
                      </span>
                    </div>

                    <Button
                      variant="primary"
                      size="md"
                      className="text-xs h-9 min-h-[36px] px-3.5"
                      onClick={() =>
                        handleAssignTransporter(
                          selectedDealForTransport.dealId,
                          `${driver.name} (${driver.vehicle.split(' ')[0]})`
                        )
                      }
                    >
                      Assign Driver
                    </Button>
                  </div>
                </div>
              ))}
            </div>

            <div className="flex justify-end">
              <Button
                variant="secondary"
                size="md"
                onClick={() => setSelectedDealForTransport(null)}
              >
                Close
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* DELIVERY DISPUTE & PRODUCE DAMAGE MODAL */}
      {disputingDeal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-3xl max-w-lg w-full p-6 sm:p-8 shadow-2xl border border-border animate-scale-in my-8">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2.5">
                <div className="w-10 h-10 rounded-2xl bg-danger/10 text-danger flex items-center justify-center">
                  <Scale className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-heading text-xl font-bold text-ink">
                    Report Delivery Dispute
                  </h3>
                  <p className="text-xs text-muted">
                    Deal #{disputingDeal.dealId.toString().slice(-4)} &bull; {disputingDeal.quantityKg} kg {disputingDeal.variety}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setDisputingDeal(null)}
                className="p-1 rounded-full text-muted hover:text-ink hover:bg-black/5"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-muted mb-4 leading-relaxed">
              If produce arrives bruised, crushed, or below agreed grade, GrowCircle enables buyers to file a formal delivery complaint. The Handover OTP is safely withheld while administrators arbitrate.
            </p>

            <div className="mb-4">
              <label className="block text-xs font-bold text-ink mb-1.5">
                Specific Damage / Complaint Reason
              </label>
              <textarea
                value={disputeReasonInput}
                onChange={(e) => setDisputeReasonInput(e.target.value)}
                rows={3}
                className="w-full p-3 rounded-xl border border-border text-xs text-ink focus:ring-2 focus:ring-danger"
              />
            </div>

            {/* Mandatory Damage Photo Proof */}
            <div className="bg-cream rounded-2xl p-4 border border-border mb-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold text-ink flex items-center gap-1.5">
                  <Camera className="w-4 h-4 text-deep-leaf" />
                  Mandatory Photographic Proof
                </span>
                <span className="text-[11px] text-danger font-bold">
                  Required by Platform Rules
                </span>
              </div>
              <div className="bg-white rounded-xl border border-dashed border-border p-3 text-center text-xs text-muted mb-2">
                <p className="font-semibold text-ink">[Damage Proof: 3 Crates Crushed in Transit]</p>
                <p className="text-[10px] text-muted">Timestamped: 2026-10-13 13:14 IST &bull; GPS Tagged</p>
              </div>
              <label className="flex items-center gap-2 text-xs text-ink cursor-pointer">
                <input
                  type="checkbox"
                  checked={disputePhotoAttached}
                  onChange={(e) => setDisputePhotoAttached(e.target.checked)}
                  className="rounded text-danger focus:ring-danger"
                />
                <span>I confirm physical inspection was performed at gate with delivery driver present.</span>
              </label>
            </div>

            <div className="flex items-center gap-3">
              <Button
                variant="secondary"
                className="flex-1"
                onClick={() => setDisputingDeal(null)}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                className="flex-1 bg-danger text-white hover:bg-danger/90"
                onClick={handleRaiseDispute}
                leftIcon={<AlertTriangle className="w-4 h-4" />}
              >
                Submit Dispute to Admin
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

