'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useTranslations, useLocale } from 'next-intl';
import { useRouter, usePathname } from 'next/navigation';
import { Header } from '@/components/ui/Header';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { SupportedLocale } from '@/components/ui/LanguageSwitcher';
import { RoleGuard } from '@/components/auth/RoleGuard';
import { useAuth } from '@/lib/auth';
import { isDemoMode, isProductionMode } from '@/lib/appMode';
import {
  Tractor,
  Layers,
  TrendingUp,
  Tag,
  CheckCircle2,
  XCircle,
  Clock,
  ArrowRight,
  PlusCircle,
  MapPin,
  Calendar,
  DollarSign,
  PieChart,
  PhoneCall,
  Sparkles,
  Store,
  ShieldCheck,
  Scale,
} from 'lucide-react';

interface FarmerListing {
  id: number;
  crop: string;
  variety: string;
  grade: 'A' | 'B' | 'C';
  quantityKg: number;
  expectedPriceKg: number;
  status: 'active' | 'in_negotiation' | 'sold';
  createdAt: string;
}

interface FarmerOffer {
  id: number;
  listingId: number;
  buyerName: string;
  buyerType: string;
  offeredPriceKg: number;
  quantityKg: number;
  reliabilityScore: number;
  status: 'pending' | 'accepted' | 'rejected';
  createdAt: string;
}

const INITIAL_LISTINGS: FarmerListing[] = [
  {
    id: 101,
    crop: 'Banana',
    variety: 'Amruthapani (Grade A)',
    grade: 'A',
    quantityKg: 1200,
    expectedPriceKg: 32,
    status: 'active',
    createdAt: 'Today, 07:30 AM',
  },
  {
    id: 102,
    crop: 'Banana',
    variety: 'Robusta (Commercial Grade)',
    grade: 'B',
    quantityKg: 2500,
    expectedPriceKg: 22,
    status: 'in_negotiation',
    createdAt: 'Yesterday',
  },
  {
    id: 98,
    crop: 'Banana',
    variety: 'Yelakki Premium',
    grade: 'A',
    quantityKg: 800,
    expectedPriceKg: 48,
    status: 'sold',
    createdAt: '3 days ago',
  },
];

const INITIAL_OFFERS: FarmerOffer[] = [
  {
    id: 501,
    listingId: 101,
    buyerName: 'Sri Chaitanya Educational Institutions',
    buyerType: 'Institution (Hostel Mess)',
    offeredPriceKg: 31,
    quantityKg: 600,
    reliabilityScore: 4.9,
    status: 'pending',
    createdAt: '15 mins ago',
  },
  {
    id: 502,
    listingId: 101,
    buyerName: 'Annapurna Supermarket',
    buyerType: 'Retail Chain (Guntur)',
    offeredPriceKg: 30.5,
    quantityKg: 600,
    reliabilityScore: 4.8,
    status: 'pending',
    createdAt: '45 mins ago',
  },
];

const LOCAL_PRICES = [
  { mandi: 'Guntur Mandi', distance: '12 km', modal: 31, min: 28, max: 34, trend: '+₹2.50' },
  { mandi: 'Tenali Market Yard', distance: '24 km', modal: 30, min: 27, max: 33, trend: '+₹1.00' },
  { mandi: 'Duggirala Mandi', distance: '18 km', modal: 29.5, min: 26, max: 32, trend: '0.00' },
  { mandi: 'Vijayawada Wholesale', distance: '38 km', modal: 33, min: 30, max: 36, trend: '+₹3.00' },
];

export function FarmerClient() {
  const t = useTranslations();
  const locale = useLocale() as SupportedLocale;
  const router = useRouter();
  const pathname = usePathname();
  const { user } = useAuth();

  const [activeTab, setActiveTab] = useState<'listings' | 'offers' | 'prices' | 'diary'>('listings');
  const [listings, setListings] = useState<FarmerListing[]>(isDemoMode ? INITIAL_LISTINGS : []);
  const [offers, setOffers] = useState<FarmerOffer[]>(isDemoMode ? INITIAL_OFFERS : []);
  const [toast, setToast] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 4000);
  };

  const handleLocaleChange = (newLocale: SupportedLocale) => {
    const segments = pathname.split('/');
    segments[1] = newLocale;
    router.push(segments.join('/'));
  };

  const handleAcceptOffer = (offerId: number) => {
    setOffers(
      offers.map((o) => (o.id === offerId ? { ...o, status: 'accepted' } : o))
    );
    showToast('Offer accepted! Transporter dispatch is being coordinated.');
  };

  const handleRejectOffer = (offerId: number) => {
    setOffers(
      offers.map((o) => (o.id === offerId ? { ...o, status: 'rejected' } : o))
    );
    showToast('Offer rejected.');
  };

  return (
    <div className="min-h-screen flex flex-col bg-cream">
      <Header
        currentLocale={locale}
        onSelectLocale={handleLocaleChange}
        activeNav="farmer"
      />

      <RoleGuard
        allowedRoles={['farmer', 'admin']}
        fallbackTitle="Farmer Login Required"
        fallbackMessage="This dashboard is reserved for verified farmers to manage direct listings, incoming offers, and diary analytics."
      >
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 space-y-8">
          {/* Header Banner */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-deep-leaf/10 text-deep-leaf text-xs font-bold uppercase tracking-wider mb-2">
                <Tractor className="w-3.5 h-3.5" />
                <span>Farmer Hub • రైతు డ్యాష్‌బోర్డ్</span>
              </div>
              <h1 className="text-3xl sm:text-4xl font-extrabold text-ink tracking-tight">
                Welcome, {user?.name || 'Farmer Raj'}
              </h1>
              <p className="text-sm text-muted mt-1">
                Guntur District • 2 Active Listings • 2 Pending Buyer Offers
              </p>
            </div>

            <div className="flex gap-2">
              <Link href={`/${locale}/diary`}>
                <Button variant="secondary" size="md" rightIcon={<ArrowRight className="w-4 h-4" />}>
                  Full Farm Diary
                </Button>
              </Link>
            </div>
          </div>

          {/* Toast Notification */}
          {toast && (
            <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-sm flex items-center gap-3">
              <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
              <span>{toast}</span>
            </div>
          )}

          {/* Mobile-First Metric Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="p-5 bg-white space-y-1">
              <span className="text-xs font-semibold text-muted uppercase tracking-wider block">
                Active Listings
              </span>
              <span className="text-2xl sm:text-3xl font-extrabold text-ink block font-mono">
                3,700 <span className="text-sm font-sans font-normal text-muted">kg</span>
              </span>
              <span className="text-xs text-deep-leaf font-bold block">
                ₹32/kg expected
              </span>
            </Card>

            <Card className="p-5 bg-white space-y-1">
              <span className="text-xs font-semibold text-muted uppercase tracking-wider block">
                Pending Offers
              </span>
              <span className="text-2xl sm:text-3xl font-extrabold text-amber block font-mono">
                2 <span className="text-sm font-sans font-normal text-muted">offers</span>
              </span>
              <span className="text-xs text-muted block">
                High: ₹31/kg (Sri Chaitanya)
              </span>
            </Card>

            <Card className="p-5 bg-white space-y-1">
              <span className="text-xs font-semibold text-muted uppercase tracking-wider block">
                Nearest Mandi Price
              </span>
              <span className="text-2xl sm:text-3xl font-extrabold text-ink block font-mono">
                ₹31 <span className="text-sm font-sans font-normal text-muted">/kg</span>
              </span>
              <span className="text-xs text-emerald-700 font-bold block">
                Guntur Mandi (+₹2.50 today)
              </span>
            </Card>

            <Card className="p-5 bg-white space-y-1">
              <span className="text-xs font-semibold text-muted uppercase tracking-wider block">
                Diary Margin
              </span>
              <span className="text-2xl sm:text-3xl font-extrabold text-deep-leaf block font-mono">
                ₹52,400
              </span>
              <span className="text-xs text-muted block">
                Kharif Banana (2.5 acres)
              </span>
            </Card>
          </div>

          {/* Navigation Tabs (Mobile First) */}
          <div className="flex border-b border-border gap-2 overflow-x-auto pb-1">
            <button
              onClick={() => setActiveTab('listings')}
              className={`px-4 py-2.5 rounded-xl font-bold text-sm whitespace-nowrap transition-all ${
                activeTab === 'listings'
                  ? 'bg-deep-leaf text-white shadow-xs'
                  : 'text-muted hover:text-ink hover:bg-white'
              }`}
            >
              My Listings ({listings.length})
            </button>
            <button
              onClick={() => setActiveTab('offers')}
              className={`px-4 py-2.5 rounded-xl font-bold text-sm whitespace-nowrap transition-all ${
                activeTab === 'offers'
                  ? 'bg-deep-leaf text-white shadow-xs'
                  : 'text-muted hover:text-ink hover:bg-white'
              }`}
            >
              Buyer Offers ({offers.filter((o) => o.status === 'pending').length})
            </button>
            <button
              onClick={() => setActiveTab('prices')}
              className={`px-4 py-2.5 rounded-xl font-bold text-sm whitespace-nowrap transition-all ${
                activeTab === 'prices'
                  ? 'bg-deep-leaf text-white shadow-xs'
                  : 'text-muted hover:text-ink hover:bg-white'
              }`}
            >
              Prices Near Me
            </button>
            <button
              onClick={() => setActiveTab('diary')}
              className={`px-4 py-2.5 rounded-xl font-bold text-sm whitespace-nowrap transition-all ${
                activeTab === 'diary'
                  ? 'bg-deep-leaf text-white shadow-xs'
                  : 'text-muted hover:text-ink hover:bg-white'
              }`}
            >
              Diary Summary
            </button>
          </div>

          {/* Tab 1: My Listings */}
          {activeTab === 'listings' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-bold text-ink">Active Harvest Listings</h2>
                <Button variant="primary" size="md" rightIcon={<PlusCircle className="w-4 h-4" />}>
                  New Listing
                </Button>
              </div>

              {listings.length === 0 ? (
                <div className="p-8 text-center bg-white rounded-2xl border border-dashed border-border text-muted text-sm">
                  No active produce listings yet. Click &quot;New Listing&quot; to list your harvest.
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {listings.map((item) => (
                    <Card key={item.id} className="p-6 bg-white space-y-4">
                      <div className="flex items-start justify-between">
                        <div>
                          <span className="text-xs font-bold text-deep-leaf uppercase tracking-wider block">
                            Grade {item.grade} Produce
                          </span>
                          <h3 className="font-extrabold text-ink text-lg">{item.variety}</h3>
                          <p className="text-xs text-muted mt-0.5">{item.createdAt}</p>
                        </div>
                        <span
                          className={`px-2.5 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider ${
                            item.status === 'active'
                              ? 'bg-emerald-100 text-emerald-800'
                              : item.status === 'in_negotiation'
                              ? 'bg-amber-100 text-amber-900'
                              : 'bg-zinc-100 text-zinc-700'
                          }`}
                        >
                          {item.status.replace('_', ' ')}
                        </span>
                      </div>

                      <div className="grid grid-cols-2 gap-3 p-3 bg-cream/50 rounded-xl text-xs">
                        <div>
                          <span className="text-muted block">Quantity</span>
                          <span className="font-mono font-bold text-ink text-sm">
                            {item.quantityKg.toLocaleString()} kg
                          </span>
                        </div>
                        <div>
                          <span className="text-muted block">Expected Price</span>
                          <span className="font-mono font-bold text-deep-leaf text-sm">
                            ₹{item.expectedPriceKg}/kg
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center justify-between pt-2 text-xs">
                        <span className="text-muted font-medium">Est. Value: ₹{(item.quantityKg * item.expectedPriceKg).toLocaleString()}</span>
                        <Button variant="secondary" size="md">
                          Manage
                        </Button>
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Tab 2: Offers */}
          {activeTab === 'offers' && (
            <div className="space-y-4">
              <h2 className="text-lg font-bold text-ink">Direct Buying Offers</h2>

              {offers.length === 0 ? (
                <div className="p-8 text-center bg-white rounded-2xl border border-dashed border-border text-muted text-sm">
                  No active direct buying offers yet. Wholesale buyers submit offers directly against your active harvest listings.
                </div>
              ) : (
                <div className="space-y-3">
                  {offers.map((offer) => (
                    <Card key={offer.id} className="p-5 bg-white space-y-4">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div className="flex items-center gap-3">
                          <div className="p-2.5 rounded-xl bg-amber-50 text-amber-700 border border-amber-200">
                            <Store className="w-5 h-5" />
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-extrabold text-ink text-base">{offer.buyerName}</span>
                              <span className="px-2 py-0.5 rounded-md bg-deep-leaf/10 text-deep-leaf text-[10px] font-bold">
                                ★ {offer.reliabilityScore} Rating
                              </span>
                            </div>
                            <p className="text-xs text-muted">{offer.buyerType} • {offer.createdAt}</p>
                          </div>
                        </div>

                        <div className="text-right sm:text-right">
                          <span className="text-xs text-muted block">Offered Rate</span>
                          <span className="font-mono text-xl font-extrabold text-deep-leaf">
                            ₹{offer.offeredPriceKg}/kg
                          </span>
                          <span className="text-[11px] text-muted block">for {offer.quantityKg} kg</span>
                        </div>
                      </div>

                      <div className="flex items-center justify-between pt-3 border-t border-border">
                        <span className="text-xs text-muted">
                          Total Deal Value: <strong className="text-ink font-mono">₹{(offer.quantityKg * offer.offeredPriceKg).toLocaleString()}</strong>
                        </span>

                        {offer.status === 'pending' ? (
                          <div className="flex gap-2">
                            <Button
                              variant="secondary"
                              size="md"
                              onClick={() => handleRejectOffer(offer.id)}
                              className="text-xs"
                            >
                              Decline
                            </Button>
                            <Button
                              variant="primary"
                              size="md"
                              onClick={() => handleAcceptOffer(offer.id)}
                              className="text-xs"
                            >
                              Accept Offer
                            </Button>
                          </div>
                        ) : (
                          <span className="text-xs font-bold capitalize text-deep-leaf">
                            Status: {offer.status}
                          </span>
                        )}
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Tab 3: Prices Near Me */}
          {activeTab === 'prices' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-bold text-ink">Mandi Prices Around Guntur</h2>
                  <p className="text-xs text-muted">Live government auction prices for Andhra Pradesh Banana</p>
                </div>
                <Link href={`/${locale}/prices`}>
                  <Button variant="secondary" size="md">
                    All India Browser
                  </Button>
                </Link>
              </div>

              <div className="overflow-x-auto rounded-2xl border border-border bg-white shadow-xs">
                <table className="w-full text-left text-sm">
                  <thead className="bg-cream/60 border-b border-border text-xs text-ink uppercase tracking-wider font-bold">
                    <tr>
                      <th className="py-3 px-4">Mandi & Distance</th>
                      <th className="py-3 px-4">Modal Price</th>
                      <th className="py-3 px-4">Min - Max</th>
                      <th className="py-3 px-4">Day Trend</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {isDemoMode &&
                      LOCAL_PRICES.map((row, idx) => (
                        <tr key={idx} className="hover:bg-cream/30 transition-colors">
                          <td className="py-3.5 px-4">
                            <div className="font-bold text-ink">{row.mandi}</div>
                            <div className="text-xs text-muted flex items-center gap-1">
                              <MapPin className="w-3 h-3 text-deep-leaf" />
                              <span>{row.distance}</span>
                            </div>
                          </td>
                          <td className="py-3.5 px-4 font-mono font-extrabold text-ink text-base">
                            ₹{row.modal}/kg
                          </td>
                          <td className="py-3.5 px-4 text-xs font-mono text-muted">
                            ₹{row.min} - ₹{row.max}
                          </td>
                          <td className="py-3.5 px-4">
                            <span className="px-2 py-1 rounded-md bg-emerald-50 text-emerald-800 font-mono text-xs font-bold">
                              {row.trend}
                            </span>
                          </td>
                        </tr>
                      ))}
                    {!isDemoMode && (
                      <tr>
                        <td colSpan={4} className="py-8 text-center text-muted text-sm">
                          No reported mandi prices recorded for today in Guntur district. Visit the Mandi Price Browser for statewide data.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Tab 4: Diary Summary */}
          {activeTab === 'diary' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-bold text-ink">Farm Diary: Kharif Season Summary</h2>
                  <p className="text-xs text-muted">2.5 Acres Banana Crop • Planted June 2026</p>
                </div>
                <Link href={`/${locale}/diary`}>
                  <Button variant="primary" size="md" rightIcon={<ArrowRight className="w-4 h-4" />}>
                    Open Ledger
                  </Button>
                </Link>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card className="p-6 bg-white space-y-2">
                  <div className="flex items-center gap-2 text-red-600 font-bold text-sm">
                    <DollarSign className="w-4 h-4" />
                    <span>Total Incurred Expenses</span>
                  </div>
                  <div className="font-mono text-2xl font-extrabold text-ink">
                    ₹67,600
                  </div>
                  <p className="text-xs text-muted">
                    Fertilizers (₹22k), Drip & Labour (₹34k), Plant Protection (₹11.6k)
                  </p>
                </Card>

                <Card className="p-6 bg-white space-y-2">
                  <div className="flex items-center gap-2 text-deep-leaf font-bold text-sm">
                    <Scale className="w-4 h-4" />
                    <span>Projected Harvest Yield</span>
                  </div>
                  <div className="font-mono text-2xl font-extrabold text-ink">
                    5,000 kg
                  </div>
                  <p className="text-xs text-muted">
                    Expected harvest window: October 2026
                  </p>
                </Card>

                <Card className="p-6 bg-white space-y-2">
                  <div className="flex items-center gap-2 text-emerald-700 font-bold text-sm">
                    <PieChart className="w-4 h-4" />
                    <span>Net Margin Forecast</span>
                  </div>
                  <div className="font-mono text-2xl font-extrabold text-emerald-700">
                    +₹52,400
                  </div>
                  <p className="text-xs text-muted">
                    Estimated ROI 77.5% at ₹24/kg benchmark
                  </p>
                </Card>
              </div>
            </div>
          )}
        </main>
      </RoleGuard>
    </div>
  );
}
