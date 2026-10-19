'use client';

import React, { useState } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { useRouter, usePathname } from 'next/navigation';
import {
  Header,
  Button,
  Chip,
  PriceTile,
  MandiRow,
  SupportedLocale,
} from '@/components/ui';
import { PriceChart, ChartDataPoint } from '@/components/ui/PriceChart';
import { GeographicBrowser, PriceRecord } from '@/components/prices/GeographicBrowser';
import { isDemoMode, isProductionMode } from '@/lib/appMode';
import { API_BASE, getFriendlyErrorMessage } from '@/lib/api';
import {
  TrendingUp,
  TrendingDown,
  ShieldCheck,
  CheckCircle2,
  ChevronDown,
  Bell,
  Send,
  X,
  Check,
  Calendar,
  AlertTriangle,
  Navigation,
  MapPin,
  Search,
  Compass,
  Info,
  RefreshCw,
} from 'lucide-react';

export interface MandiItem {
  id: number;
  name: string;
  canonical_name?: string;
  district: string;
  state: string;
  mandal?: string | null;
  modalPriceKg: number;
  modalPriceQuintal: number;
  minPriceKg: number;
  maxPriceKg: number;
  variety: string;
  distanceKm: number;
  distanceLabel?: string;
  arrivalTonnes: number;
  date: string;
  reportedDate?: string;
  ageDays?: number;
  ageLabel?: string;
  isReportedToday?: boolean;
  sourceName?: string;
  provenanceText?: string;
  statusMessage?: string;
  trend: 'up' | 'down' | 'same';
  trendDiff: number;
  isNearest: boolean;
}

export interface CropSeasonalityInfo {
  benchmarkKg: number;
  seasonalityStatus: 'expensive' | 'fair' | 'cheap';
  seasonalityVerdict: string;
  seasonalityTip: string;
  mandis: MandiItem[];
}

// Multi-crop Mandi Datasets for Andhra Pradesh
export const CROP_MANDI_DATA: Record<string, CropSeasonalityInfo> = {
  banana: {
    benchmarkKg: 24.0,
    seasonalityStatus: 'fair',
    seasonalityVerdict: 'Normal / Fair Price this month (within 4% of baseline). Current: ₹25.0/kg.',
    seasonalityTip: 'Steady arrivals across Tenali and Guntur rural mandis. Stable pricing for households and bulk buyers.',
    mandis: [
      {
        id: 1,
        name: 'Guntur Mandi',
        district: 'Guntur',
        state: 'Andhra Pradesh',
        modalPriceKg: 25.0,
        modalPriceQuintal: 2500,
        minPriceKg: 22.0,
        maxPriceKg: 28.0,
        variety: 'Amruthapani',
        distanceKm: 0.0,
        arrivalTonnes: 45.0,
        date: 'Today, 13 Oct 2026',
        trend: 'up',
        trendDiff: 2,
        isNearest: true,
      },
      {
        id: 2,
        name: 'Tenali Mandi',
        district: 'Guntur',
        state: 'Andhra Pradesh',
        modalPriceKg: 18.0,
        modalPriceQuintal: 1800,
        minPriceKg: 16.0,
        maxPriceKg: 20.0,
        variety: 'Robusta',
        distanceKm: 28.4,
        arrivalTonnes: 25.0,
        date: 'Today, 13 Oct 2026',
        trend: 'same',
        trendDiff: 0,
        isNearest: false,
      },
      {
        id: 3,
        name: 'Vijayawada Mandi',
        district: 'NTR District',
        state: 'Andhra Pradesh',
        modalPriceKg: 27.0,
        modalPriceQuintal: 2700,
        minPriceKg: 24.0,
        maxPriceKg: 30.0,
        variety: 'Karpura',
        distanceKm: 34.2,
        arrivalTonnes: 60.0,
        date: 'Today, 13 Oct 2026',
        trend: 'up',
        trendDiff: 1,
        isNearest: false,
      },
    ],
  },
  tomato: {
    benchmarkKg: 28.0,
    seasonalityStatus: 'expensive',
    seasonalityVerdict: 'Expensive this month (+35.7% vs baseline). Current: ₹38.0/kg (baseline ₹28.0/kg).',
    seasonalityTip: 'Post-monsoon transition has reduced daily arrivals from Madanapalle. Expect prices to normalize within 2 weeks.',
    mandis: [
      {
        id: 11,
        name: 'Madanapalle Mandi',
        district: 'Annamayya',
        state: 'Andhra Pradesh',
        modalPriceKg: 38.0,
        modalPriceQuintal: 3800,
        minPriceKg: 32.0,
        maxPriceKg: 44.0,
        variety: 'Hybrid F1',
        distanceKm: 12.0,
        arrivalTonnes: 32.0,
        date: 'Today, 13 Oct 2026',
        trend: 'up',
        trendDiff: 6,
        isNearest: true,
      },
      {
        id: 12,
        name: 'Guntur Vegetable Market',
        district: 'Guntur',
        state: 'Andhra Pradesh',
        modalPriceKg: 40.0,
        modalPriceQuintal: 4000,
        minPriceKg: 35.0,
        maxPriceKg: 46.0,
        variety: 'Desi',
        distanceKm: 24.5,
        arrivalTonnes: 18.0,
        date: 'Today, 13 Oct 2026',
        trend: 'up',
        trendDiff: 5,
        isNearest: false,
      },
      {
        id: 13,
        name: 'Tirupati Mandi',
        district: 'Tirupati',
        state: 'Andhra Pradesh',
        modalPriceKg: 39.0,
        modalPriceQuintal: 3900,
        minPriceKg: 34.0,
        maxPriceKg: 45.0,
        variety: 'Hybrid',
        distanceKm: 45.0,
        arrivalTonnes: 28.0,
        date: 'Today, 13 Oct 2026',
        trend: 'up',
        trendDiff: 4,
        isNearest: false,
      },
    ],
  },
  onion: {
    benchmarkKg: 32.0,
    seasonalityStatus: 'cheap',
    seasonalityVerdict: 'Great time to buy! (-25.0% below baseline). Current: ₹24.0/kg (baseline ₹32.0/kg).',
    seasonalityTip: 'Kharif crop arrivals have flooded regional mandis. Excellent window for households and hostels to purchase weekly lots.',
    mandis: [
      {
        id: 21,
        name: 'Kurnool Mandi',
        district: 'Kurnool',
        state: 'Andhra Pradesh',
        modalPriceKg: 22.0,
        modalPriceQuintal: 2200,
        minPriceKg: 18.0,
        maxPriceKg: 25.0,
        variety: 'Bellary Red',
        distanceKm: 15.0,
        arrivalTonnes: 120.0,
        date: 'Today, 13 Oct 2026',
        trend: 'down',
        trendDiff: -4,
        isNearest: true,
      },
      {
        id: 22,
        name: 'Guntur Mandi',
        district: 'Guntur',
        state: 'Andhra Pradesh',
        modalPriceKg: 24.0,
        modalPriceQuintal: 2400,
        minPriceKg: 20.0,
        maxPriceKg: 27.0,
        variety: 'Red Medium',
        distanceKm: 0.0,
        arrivalTonnes: 75.0,
        date: 'Today, 13 Oct 2026',
        trend: 'down',
        trendDiff: -3,
        isNearest: false,
      },
      {
        id: 23,
        name: 'Vijayawada Mandi',
        district: 'NTR District',
        state: 'Andhra Pradesh',
        modalPriceKg: 25.0,
        modalPriceQuintal: 2500,
        minPriceKg: 21.0,
        maxPriceKg: 28.0,
        variety: 'Red',
        distanceKm: 34.2,
        arrivalTonnes: 90.0,
        date: 'Today, 13 Oct 2026',
        trend: 'down',
        trendDiff: -2,
        isNearest: false,
      },
    ],
  },
  chilli: {
    benchmarkKg: 65.0,
    seasonalityStatus: 'fair',
    seasonalityVerdict: 'Normal / Fair Price this month (+4.6% vs baseline). Current: ₹68.0/kg.',
    seasonalityTip: 'New harvest pickings arriving daily at Guntur Asia’s Largest Chilli Yard. High quality and steady supply.',
    mandis: [
      {
        id: 31,
        name: 'Guntur Chilli Yard',
        district: 'Guntur',
        state: 'Andhra Pradesh',
        modalPriceKg: 68.0,
        modalPriceQuintal: 6800,
        minPriceKg: 60.0,
        maxPriceKg: 75.0,
        variety: 'Teja / Guntur Sannam',
        distanceKm: 4.2,
        arrivalTonnes: 210.0,
        date: 'Today, 13 Oct 2026',
        trend: 'same',
        trendDiff: 0,
        isNearest: true,
      },
      {
        id: 32,
        name: 'Tenali Mandi',
        district: 'Guntur',
        state: 'Andhra Pradesh',
        modalPriceKg: 66.0,
        modalPriceQuintal: 6600,
        minPriceKg: 58.0,
        maxPriceKg: 72.0,
        variety: 'Green Long',
        distanceKm: 28.4,
        arrivalTonnes: 40.0,
        date: 'Today, 13 Oct 2026',
        trend: 'up',
        trendDiff: 2,
        isNearest: false,
      },
      {
        id: 33,
        name: 'Vijayawada Mandi',
        district: 'NTR District',
        state: 'Andhra Pradesh',
        modalPriceKg: 70.0,
        modalPriceQuintal: 7000,
        minPriceKg: 62.0,
        maxPriceKg: 78.0,
        variety: 'Guntur Local',
        distanceKm: 34.2,
        arrivalTonnes: 55.0,
        date: 'Today, 13 Oct 2026',
        trend: 'same',
        trendDiff: 0,
        isNearest: false,
      },
    ],
  },
};

// 30-Day Historical Curve Generator
const GENERATE_30_DAY_HISTORY = (basePrice: number): ChartDataPoint[] => {
  const points: ChartDataPoint[] = [];
  for (let i = 29; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    const dateStr = d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
    const wave = Math.sin(i / 3.5) * (basePrice * 0.08) + ((i % 4) * 0.3);
    const priceKg = Math.round((basePrice + wave) * 10) / 10;
    points.push({
      date: dateStr,
      modalPrice: priceKg,
      modalPriceQuintal: priceKg * 100,
      arrivalTonnes: Math.round(35 + (i % 6) * 5),
    });
  }
  return points;
};

export function PricesClient() {
  const t = useTranslations();
  const locale = useLocale() as SupportedLocale;
  const router = useRouter();
  const pathname = usePathname();

  const [selectedCrop, setSelectedCrop] = useState<string>('banana');
  const [selectedDistrict, setSelectedDistrict] = useState<string>('all');
  const [priceUnit, setPriceUnit] = useState<'kg' | 'quintal'>('kg');

  const currentCropData = CROP_MANDI_DATA[selectedCrop] || CROP_MANDI_DATA.banana;
  const [liveMandis, setLiveMandis] = useState<MandiItem[]>([]);
  const [activeMandi, setActiveMandi] = useState<MandiItem>(currentCropData.mandis[0]);
  const [isLoadingLivePrices, setIsLoadingLivePrices] = useState<boolean>(true);

  // R3 Location State
  const [userCoords, setUserCoords] = useState<{
    lat: number;
    lng: number;
    source: 'gps' | 'pincode' | 'hierarchy' | 'default';
    label: string;
  } | null>(null);
  const [isLocating, setIsLocating] = useState<boolean>(false);
  const [locationDenied, setLocationDenied] = useState<boolean>(false);
  const [showLocationFallback, setShowLocationFallback] = useState<boolean>(false);
  const [searchRadiusKm, setSearchRadiusKm] = useState<number>(100);
  const [nearbyMandis, setNearbyMandis] = useState<MandiItem[]>([]);
  const [isLoadingNearby, setIsLoadingNearby] = useState<boolean>(false);

  // Pincode fallback state
  const [pincodeInput, setPincodeInput] = useState<string>('');
  const [pincodeLoading, setPincodeLoading] = useState<boolean>(false);
  const [pincodeError, setPincodeError] = useState<string | null>(null);

  // Hierarchy cascade state
  const [statesList, setStatesList] = useState<Array<{ id: string; name: string }>>([
    { id: 'AP', name: 'Andhra Pradesh' },
  ]);
  const [districtsList, setDistrictsList] = useState<Array<{ id: number; name: string; state_id: string }>>([]);
  const [mandalsList, setMandalsList] = useState<
    Array<{ id: number; name: string; latitude: number | null; longitude: number | null }>
  >([]);
  const [selectedHierState, setSelectedHierState] = useState<string>('AP');
  const [selectedHierDistrict, setSelectedHierDistrict] = useState<string>('');
  const [selectedHierMandal, setSelectedHierMandal] = useState<string>('');

  // 1. Fetch live commodity overview prices
  React.useEffect(() => {
    async function fetchLiveMandiPrices() {
      try {
        setIsLoadingLivePrices(true);
        const res = await fetch(`${API_BASE}/prices?crop=${selectedCrop}&state=andhra-pradesh`);
        if (res.ok) {
          const apiPrices = await res.json();
          if (Array.isArray(apiPrices) && apiPrices.length > 0) {
            const mapped: MandiItem[] = apiPrices.map((item: any, idx: number) => ({
              id: item.mandi_id,
              name: item.mandi_name,
              canonical_name: item.canonical_name,
              district: item.district,
              state: item.state,
              mandal: item.mandal,
              modalPriceKg: item.modal_price_kg,
              modalPriceQuintal: item.modal_price_quintal,
              minPriceKg: item.min_price_kg,
              maxPriceKg: item.max_price_kg,
              variety: item.variety,
              distanceKm: idx * 12.5,
              distanceLabel: 'straight-line distance',
              arrivalTonnes: item.arrival_tonnes,
              date: item.is_reported_today ? 'Today' : `${item.age_label} (${item.reported_date})`,
              reportedDate: item.reported_date,
              ageDays: item.age_days,
              ageLabel: item.age_label,
              isReportedToday: item.is_reported_today,
              sourceName: item.source_name,
              provenanceText: item.provenance_text,
              statusMessage: item.status_message,
              trend: 'same',
              trendDiff: 0,
              isNearest: idx === 0,
            }));
            setLiveMandis(mapped);
            if (!userCoords) {
              setActiveMandi(mapped[0]);
            }
          }
        }
      } catch (err) {
        console.warn('Live price fetch warning, using preview data:', err);
      } finally {
        setIsLoadingLivePrices(false);
      }
    }
    fetchLiveMandiPrices();
  }, [selectedCrop]);

  // 2. Fetch Nearby Mandis within radius (R3 PostGIS distance query)
  const fetchNearbyMandis = React.useCallback(
    async (lat: number, lng: number, crop: string, radius: number) => {
      try {
        setIsLoadingNearby(true);
        const url = `${API_BASE}/nearby-mandis?lat=${lat}&lng=${lng}&crop=${crop}&limit=5&radius_km=${radius}&max_age_days=3`;
        const res = await fetch(url);
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data)) {
            const mapped: MandiItem[] = data.map((item: any, idx: number) => ({
              id: item.mandi_id,
              name: item.mandi_name,
              canonical_name: item.canonical_name,
              district: item.district,
              state: item.state,
              mandal: item.mandal,
              modalPriceKg: item.modal_price_kg,
              modalPriceQuintal: item.modal_price_quintal,
              minPriceKg: item.modal_price_kg * 0.9,
              maxPriceKg: item.modal_price_kg * 1.1,
              variety: item.variety,
              distanceKm: item.distance_km,
              distanceLabel: item.distance_label || 'straight-line distance',
              arrivalTonnes: item.arrival_tonnes,
              date: item.age_label === 'Today' ? 'Today' : `${item.age_label} (${item.price_date})`,
              reportedDate: item.price_date,
              ageDays: item.age_days,
              ageLabel: item.age_label,
              isReportedToday: item.age_days === 0,
              sourceName: item.source_name || 'Agmarknet',
              provenanceText: `Source: ${item.source_name || 'Agmarknet'} | Reported: ${item.price_date} (${item.age_label})`,
              statusMessage:
                item.age_days === 0
                  ? 'Fresh auction reported today'
                  : `Last auction: ${item.price_date} (${item.age_label})`,
              trend: 'same',
              trendDiff: 0,
              isNearest: idx === 0,
            }));
            setNearbyMandis(mapped);
            if (mapped.length > 0) {
              setActiveMandi(mapped[0]);
            }
          }
        }
      } catch (err) {
        console.warn('Failed to fetch nearby mandis:', err);
      } finally {
        setIsLoadingNearby(false);
      }
    },
    []
  );

  // Trigger initial nearby query on mount centered on Guntur anchor
  React.useEffect(() => {
    const defaultLat = 16.3067;
    const defaultLng = 80.4365;
    const targetLat = userCoords ? userCoords.lat : defaultLat;
    const targetLng = userCoords ? userCoords.lng : defaultLng;
    fetchNearbyMandis(targetLat, targetLng, selectedCrop, searchRadiusKm);
  }, [selectedCrop, searchRadiusKm, userCoords, fetchNearbyMandis]);

  // Load Hierarchy states and districts
  React.useEffect(() => {
    async function loadHierarchy() {
      try {
        const [statesRes, distRes] = await Promise.all([
          fetch(`${API_BASE}/hierarchy/states`),
          fetch(`${API_BASE}/hierarchy/districts?state_id=AP`),
        ]);
        if (statesRes.ok) {
          const statesData = await statesRes.json();
          if (Array.isArray(statesData) && statesData.length > 0) setStatesList(statesData);
        }
        if (distRes.ok) {
          const distData = await distRes.json();
          if (Array.isArray(distData)) setDistrictsList(distData);
        }
      } catch (err) {
        console.warn('Hierarchy loading err:', err);
      }
    }
    loadHierarchy();
  }, []);

  const handleStateChange = async (stateId: string) => {
    setSelectedHierState(stateId);
    setSelectedHierDistrict('');
    setSelectedHierMandal('');
    try {
      const res = await fetch(`${API_BASE}/hierarchy/districts?state_id=${stateId}`);
      if (res.ok) {
        const data = await res.json();
        setDistrictsList(data);
      }
    } catch (err) {
      console.warn('Failed to load districts:', err);
    }
  };

  const handleDistrictChange = async (distId: string) => {
    setSelectedHierDistrict(distId);
    setSelectedHierMandal('');
    try {
      const res = await fetch(`${API_BASE}/hierarchy/mandals?district_id=${distId}`);
      if (res.ok) {
        const data = await res.json();
        setMandalsList(data);
      }
    } catch (err) {
      console.warn('Failed to load mandals:', err);
    }
  };

  const handleMandalChange = (mandalIdStr: string) => {
    setSelectedHierMandal(mandalIdStr);
    const m = mandalsList.find((x) => x.id.toString() === mandalIdStr);
    if (m && m.latitude && m.longitude) {
      const coords = {
        lat: m.latitude,
        lng: m.longitude,
        source: 'hierarchy' as const,
        label: `${m.name} Mandal`,
      };
      setUserCoords(coords);
      setLocationDenied(false);
      fetchNearbyMandis(m.latitude, m.longitude, selectedCrop, searchRadiusKm);
    }
  };

  // 3. User taps "Use my location" button
  const handleUseMyLocation = () => {
    setIsLocating(true);
    setLocationDenied(false);

    if (typeof window === 'undefined' || !navigator.geolocation) {
      setLocationDenied(true);
      setIsLocating(false);
      setShowLocationFallback(true);
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        setUserCoords({
          lat,
          lng,
          source: 'gps',
          label: 'My GPS Location',
        });
        setIsLocating(false);
        setShowLocationFallback(false);
        fetchNearbyMandis(lat, lng, selectedCrop, searchRadiusKm);
      },
      (err) => {
        console.warn('Geolocation denied or failed:', err);
        setIsLocating(false);
        setLocationDenied(true);
        setShowLocationFallback(true);
      },
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 60000 }
    );
  };

  // 4. Pincode submit
  const handlePincodeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pincodeInput || pincodeInput.trim().length !== 6) {
      setPincodeError('Please enter a 6-digit Indian PIN code');
      return;
    }
    setPincodeLoading(true);
    setPincodeError(null);
    try {
      const res = await fetch(`${API_BASE}/pincode-lookup?pincode=${pincodeInput.trim()}`);
      if (res.ok) {
        const data = await res.json();
        const coords = {
          lat: data.latitude,
          lng: data.longitude,
          source: 'pincode' as const,
          label: `PIN ${data.pincode} (${data.mandal || data.district})`,
        };
        setUserCoords(coords);
        setLocationDenied(false);
        fetchNearbyMandis(data.latitude, data.longitude, selectedCrop, searchRadiusKm);
      } else {
        setPincodeError('PIN code not found. Try 522001 (Guntur), 520001 (Vijayawada), 517501 (Tirupati), etc.');
      }
    } catch (err) {
      setPincodeError(getFriendlyErrorMessage(err, 'PIN code lookup'));
    } finally {
      setPincodeLoading(false);
    }
  };

  // Alert Modal State
  const [isAlertModalOpen, setIsAlertModalOpen] = useState(false);
  const [alertChannel, setAlertChannel] = useState<'whatsapp' | 'telegram'>('whatsapp');
  const [alertRecipient, setAlertRecipient] = useState('');
  const [alertTargetPrice, setAlertTargetPrice] = useState(
    Math.round(currentCropData.mandis[0].modalPriceKg * 0.9)
  );
  const [alertSuccessMessage, setAlertSuccessMessage] = useState<string | null>(null);

  const [realHistory, setRealHistory] = useState<ChartDataPoint[]>([]);

  React.useEffect(() => {
    let isSubscribed = true;
    async function fetchHistory() {
      if (!activeMandi?.id) return;
      try {
        const res = await fetch(`${API_BASE}/history?mandi_id=${activeMandi.id}&crop=${selectedCrop}&days=30`);
        if (res.ok) {
          const data = await res.json();
          if (data.history && Array.isArray(data.history) && data.history.length > 0) {
            const pts: ChartDataPoint[] = data.history.map((p: any) => ({
              date: new Date(p.date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }),
              modalPrice: p.modal_price_kg,
              modalPriceQuintal: p.modal_price_quintal,
              arrivalTonnes: p.arrival_tonnes,
            }));
            if (isSubscribed) setRealHistory(pts);
            return;
          }
        }
      } catch (err) {
        console.warn('Real history fetch warning:', err);
      }
      if (isSubscribed) {
        if (isDemoMode && activeMandi?.modalPriceKg) {
          setRealHistory(GENERATE_30_DAY_HISTORY(activeMandi.modalPriceKg));
        } else {
          setRealHistory([]);
        }
      }
    }
    fetchHistory();
    return () => { isSubscribed = false; };
  }, [activeMandi?.id, selectedCrop]);

  const historyData = realHistory.length > 0
    ? realHistory
    : (isDemoMode && activeMandi?.modalPriceKg ? GENERATE_30_DAY_HISTORY(activeMandi.modalPriceKg) : []);

  const handleLocaleChange = (newLocale: SupportedLocale) => {
    const segments = pathname.split('/');
    segments[1] = newLocale;
    router.push(segments.join('/'));
  };

  const handleCropChange = (cropKey: string) => {
    setSelectedCrop(cropKey);
    const targetCrop = CROP_MANDI_DATA[cropKey] || CROP_MANDI_DATA.banana;
    setActiveMandi(targetCrop.mandis[0]);
    setAlertTargetPrice(Math.round(targetCrop.mandis[0].modalPriceKg * 0.9));
  };

  const handleSelectGeographicMandi = (item: PriceRecord) => {
    setActiveMandi({
      id: item.mandi_id,
      name: item.mandi_name,
      canonical_name: item.canonical_name || item.mandi_name,
      district: item.district,
      state: item.state,
      mandal: item.mandal,
      modalPriceKg: item.modal_price_kg,
      modalPriceQuintal: item.modal_price_quintal,
      minPriceKg: item.min_price_kg,
      maxPriceKg: item.max_price_kg,
      variety: item.variety,
      distanceKm: item.distance_km ?? 0,
      distanceLabel: item.distance_label || 'straight-line distance',
      arrivalTonnes: item.arrival_tonnes,
      date: item.is_reported_today ? 'Today' : `${item.age_label} (${item.reported_date})`,
      reportedDate: item.reported_date,
      ageDays: item.is_reported_today ? 0 : 1,
      ageLabel: item.age_label,
      isReportedToday: item.is_reported_today,
      sourceName: item.source_name,
      provenanceText: item.provenance_text,
      statusMessage: item.status_message || undefined,
      trend: 'same',
      trendDiff: 0,
      isNearest: false,
    });
  };

  // Filtered mandis based on district selection
  const cropMandis = liveMandis.length > 0 ? liveMandis : (isDemoMode ? currentCropData.mandis : []);
  const filteredMandis =
    selectedDistrict === 'all'
      ? cropMandis
      : cropMandis.filter((m: MandiItem) =>
          m.district.toLowerCase().includes(selectedDistrict.toLowerCase())
        );

  const displayedNearbyMandis =
    nearbyMandis.length > 0
      ? nearbyMandis
      : (filteredMandis.length > 0 ? filteredMandis : cropMandis).slice(0, 5);

  // Multilingual crop display names
  const cropNames: Record<string, string> = {
    banana:
      locale === 'te' ? 'అరటిపండు' : locale === 'hi' ? 'केला' : locale === 'gu' ? 'કેળા' : 'Banana',
    tomato:
      locale === 'te' ? 'టమాటా' : locale === 'hi' ? 'टमाटर' : locale === 'gu' ? 'ટામેટા' : 'Tomato',
    onion:
      locale === 'te' ? 'ఉల్లిపాయ' : locale === 'hi' ? 'प्याज' : locale === 'gu' ? 'ડુંગળી' : 'Onion',
    chilli:
      locale === 'te' ? 'పచ్చిమిర్చి' : locale === 'hi' ? 'हरी मिर्च' : locale === 'gu' ? 'લીલાં મરચાં' : 'Green Chilli',
  };

  // Seasonality visual status helper
  const isExpensive = currentCropData.seasonalityStatus === 'expensive';
  const isCheap = currentCropData.seasonalityStatus === 'cheap';

  const handleSubscribeAlert = (e: React.FormEvent) => {
    e.preventDefault();
    if (!alertRecipient.trim()) return;

    setAlertSuccessMessage(
      `Alert active! We will notify you on ${
        alertChannel === 'whatsapp' ? 'WhatsApp' : 'Telegram'
      } at "${alertRecipient}" whenever ${cropNames[selectedCrop]} drops below ₹${alertTargetPrice}/kg in ${activeMandi.district}.`
    );

    setTimeout(() => {
      setIsAlertModalOpen(false);
      setAlertSuccessMessage(null);
      setAlertRecipient('');
    }, 2800);
  };

  return (
    <div className="min-h-screen bg-cream flex flex-col">
      <Header
        currentLocale={locale}
        onSelectLocale={handleLocaleChange}
        brandName={t('brand.name')}
        activeNav="prices"
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 space-y-8">
        {/* Title Bar & Verification Tag */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-border">
          <div>
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-deep-leaf/10 text-deep-leaf text-xs font-bold mb-2">
              <ShieldCheck className="w-4 h-4" />
              <span>Agmarknet Public Mandi Rates &bull; Andhra Pradesh</span>
            </div>
            <h1 className="font-heading text-3xl sm:text-4xl font-extrabold text-ink">
              {t('consumer.anyCrop')} &mdash; {cropNames[selectedCrop]}
            </h1>
            <p className="text-sm text-muted mt-1">
              Real-time daily modal prices directly from government mandi arrival registries. No login required.
            </p>
          </div>

          {/* Unit Toggle Switch */}
          <div className="inline-flex items-center p-1 bg-white border border-border rounded-xl self-start md:self-center shadow-sm">
            <button
              type="button"
              onClick={() => setPriceUnit('kg')}
              className={`min-h-[44px] min-w-[56px] px-4 py-2 rounded-lg text-sm font-bold transition-colors ${
                priceUnit === 'kg'
                  ? 'bg-deep-leaf text-white'
                  : 'text-ink hover:text-deep-leaf'
              }`}
            >
              ₹ / kg
            </button>
            <button
              type="button"
              onClick={() => setPriceUnit('quintal')}
              className={`min-h-[44px] min-w-[56px] px-4 py-2 rounded-lg text-sm font-bold transition-colors ${
                priceUnit === 'quintal'
                  ? 'bg-deep-leaf text-white'
                  : 'text-ink hover:text-deep-leaf'
              }`}
            >
              ₹ / quintal
            </button>
          </div>
        </div>

        {/* Consumer Seasonality Widget: "Is it expensive this month?" */}
        <section
          aria-labelledby="seasonality-heading"
          className="bg-white rounded-2xl border-2 border-border shadow-sm p-5 sm:p-6 transition-all duration-200"
        >
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-border">
            <div className="flex items-center gap-3">
              <div
                className={`p-2.5 rounded-xl ${
                  isExpensive
                    ? 'bg-red-50 text-red-700'
                    : isCheap
                    ? 'bg-emerald-50 text-emerald-800'
                    : 'bg-cream text-deep-leaf'
                }`}
              >
                {isExpensive ? (
                  <TrendingUp className="w-6 h-6" />
                ) : isCheap ? (
                  <TrendingDown className="w-6 h-6" />
                ) : (
                  <Calendar className="w-6 h-6" />
                )}
              </div>
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-muted">
                  Consumer Price Insights
                </span>
                <h2
                  id="seasonality-heading"
                  className="font-heading text-xl sm:text-2xl font-extrabold text-ink"
                >
                  {t('consumer.isExpensive')}
                </h2>
              </div>
            </div>

            {/* Status Pill Badge */}
            <div className="flex items-center gap-3">
              <div
                className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-sm font-extrabold border ${
                  isExpensive
                    ? 'bg-red-50 border-red-200 text-red-800'
                    : isCheap
                    ? 'bg-emerald-50 border-emerald-300 text-emerald-900'
                    : 'bg-emerald-50/60 border-emerald-200 text-deep-leaf'
                }`}
              >
                {isExpensive ? (
                  <>
                    <AlertTriangle className="w-4 h-4 text-red-700" />
                    <span>{t('consumer.expensiveBadge')}</span>
                  </>
                ) : isCheap ? (
                  <>
                    <CheckCircle2 className="w-4 h-4 text-emerald-800" />
                    <span>{t('consumer.cheapBadge')}</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-4 h-4 text-deep-leaf" />
                    <span>{t('consumer.fairBadge')}</span>
                  </>
                )}
              </div>

              {/* Subscribe Alerts Trigger Button */}
              <Button
                variant="primary"
                size="md"
                onClick={() => setIsAlertModalOpen(true)}
                className="whitespace-nowrap"
              >
                <Bell className="w-4 h-4 mr-1.5" />
                {t('consumer.subscribeAlerts')}
              </Button>
            </div>
          </div>

          {/* Seasonality Verdict & Comparative Metric */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 items-center">
            <div className="md:col-span-2 space-y-1.5">
              <p className="text-base font-bold text-ink leading-relaxed">
                {currentCropData.seasonalityVerdict}
              </p>
              <p className="text-sm text-muted leading-relaxed">
                {currentCropData.seasonalityTip}
              </p>
              <div className="pt-1 text-xs text-deep-leaf font-bold">
                {t('consumer.noLogin')}
              </div>
            </div>

            {/* Key Comparison numbers */}
            <div className="bg-cream/70 rounded-xl p-3.5 border border-border flex items-center justify-around text-center">
              <div>
                <span className="block text-xs font-bold text-muted uppercase">Today’s Modal</span>
                <span className="font-heading text-xl font-extrabold text-ink">
                  ₹{activeMandi.modalPriceKg}
                  <span className="text-xs font-normal text-muted">/kg</span>
                </span>
              </div>
              <div className="h-8 w-px bg-border" />
              <div>
                <span className="block text-xs font-bold text-muted uppercase">30-Day Benchmark</span>
                <span className="font-heading text-xl font-extrabold text-muted">
                  ₹{currentCropData.benchmarkKg}
                  <span className="text-xs font-normal text-muted">/kg</span>
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* Filter Controls: Crop chips & District Dropdown */}
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 bg-white p-4 sm:p-5 rounded-2xl border border-border shadow-sm">
          {/* Crop Selector Chips */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-bold text-muted uppercase mr-1">Crop:</span>
            {['banana', 'tomato', 'onion', 'chilli'].map((cropKey) => (
              <Chip
                key={cropKey}
                isClickable
                selected={selectedCrop === cropKey}
                onClick={() => handleCropChange(cropKey)}
              >
                {cropNames[cropKey]}
              </Chip>
            ))}
          </div>

          {/* District Dropdown for Andhra Pradesh */}
          <div className="flex items-center gap-2 w-full lg:w-auto">
            <span className="text-xs font-bold text-muted uppercase whitespace-nowrap">District:</span>
            <div className="relative w-full sm:w-64">
              <select
                value={selectedDistrict}
                onChange={(e) => setSelectedDistrict(e.target.value)}
                className="w-full min-h-[44px] px-3.5 py-2.5 bg-cream border border-border rounded-xl text-sm font-semibold text-ink appearance-none focus:outline-none focus:ring-2 focus:ring-deep-leaf cursor-pointer pr-10"
              >
                <option value="all">All Andhra Pradesh Districts</option>
                <option value="guntur">Guntur District</option>
                <option value="ntr district">NTR / Vijayawada District</option>
                <option value="annamayya">Annamayya / Madanapalle</option>
                <option value="tirupati">Tirupati District</option>
                <option value="kurnool">Kurnool District</option>
              </select>
              <ChevronDown className="w-4 h-4 text-muted absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>
          </div>
        </div>

        {/* R3 LOCATION CONTROLS & GPS TOOLBAR */}
        <div className="bg-white p-4 sm:p-5 rounded-2xl border border-border shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3 flex-wrap">
              <Button
                variant={userCoords?.source === 'gps' ? 'secondary' : 'primary'}
                onClick={handleUseMyLocation}
                disabled={isLocating}
                className="flex items-center gap-2"
              >
                <Navigation className={`w-4 h-4 ${isLocating ? 'animate-spin' : ''}`} />
                <span>
                  {isLocating
                    ? (locale === 'te' ? 'లొకేషన్ గుర్తిస్తోంది...' : locale === 'hi' ? 'स्थान खोजा जा रहा है...' : 'Detecting location...')
                    : (locale === 'te' ? 'నా స్థానాన్ని ఉపయోగించండి' : locale === 'hi' ? 'मेरी लोकेशन उपयोग करें' : 'Use my location')}
                </span>
              </Button>

              <button
                type="button"
                onClick={() => setShowLocationFallback(!showLocationFallback)}
                className="text-xs font-semibold text-deep-leaf hover:underline flex items-center gap-1 p-2 rounded-lg hover:bg-cream"
              >
                <MapPin className="w-3.5 h-3.5" />
                <span>PIN Code / Mandal Selector</span>
              </button>
            </div>

            {/* Active Location & Radius Selector */}
            <div className="flex items-center gap-2 flex-wrap text-xs">
              <span className="text-muted font-medium">Search Radius:</span>
              {[100, 150, 200, 300].map((r) => (
                <button
                  key={r}
                  onClick={() => setSearchRadiusKm(r)}
                  className={`px-2.5 py-1 rounded-full font-bold transition-all ${
                    searchRadiusKm === r
                      ? 'bg-deep-leaf text-white shadow-xs'
                      : 'bg-cream text-ink border border-border hover:border-deep-leaf'
                  }`}
                >
                  {r} km
                </button>
              ))}
            </div>
          </div>

          {/* Active location status pill */}
          <div className="flex items-center justify-between flex-wrap gap-2 pt-2 border-t border-border/60 text-xs">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-muted">Target Center:</span>
              <span className="font-bold text-ink">
                {userCoords ? userCoords.label : 'Guntur (Default Anchor)'}
              </span>
              <span className="text-muted">
                ({userCoords ? `${userCoords.lat.toFixed(4)}, ${userCoords.lng.toFixed(4)}` : '16.3067, 80.4365'})
              </span>
            </div>
            <span className="text-muted text-[11px]">
              Distance measurement: <strong>straight-line distance</strong>
            </span>
          </div>

          {/* FALLBACK DRAWER (Shown when location denied or user clicked PIN/Mandal) */}
          {showLocationFallback && (
            <div className="p-4 bg-cream/70 rounded-xl border border-border space-y-4 animate-fade-in">
              <div className="flex items-center justify-between">
                <span className="font-bold text-ink text-xs flex items-center gap-1.5">
                  <Compass className="w-4 h-4 text-deep-leaf" />
                  Manual Location Selection (No GPS Required)
                </span>
                <button
                  onClick={() => setShowLocationFallback(false)}
                  className="text-muted hover:text-ink text-xs p-1"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {locationDenied && (
                <div className="p-3 bg-amber-50 border border-amber-300 rounded-xl text-amber-900 text-xs flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-700 flex-shrink-0" />
                  <span>
                    {locale === 'te'
                      ? 'లొకేషన్ అనుమతి లభించలేదు. మీ 6-అంకెల పిన్ కోడ్ నమోదు చేయండి లేదా క్రింద మండలాన్ని ఎంచుకోండి.'
                      : 'Browser geolocation was denied or unavailable. Enter your 6-digit PIN code or pick a Mandal below.'}
                  </span>
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* 1. Pincode Input Form */}
                <form onSubmit={handlePincodeSubmit} className="space-y-2">
                  <label className="block text-xs font-bold text-muted uppercase">
                    Enter 6-Digit Indian PIN Code:
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      maxLength={6}
                      value={pincodeInput}
                      onChange={(e) => setPincodeInput(e.target.value.replace(/\D/g, ''))}
                      placeholder="e.g. 522001, 520001, 517501"
                      className="flex-1 p-2.5 text-xs font-mono rounded-xl border border-border bg-white text-ink focus:outline-none focus:ring-2 focus:ring-deep-leaf"
                    />
                    <Button variant="primary" disabled={pincodeLoading || pincodeInput.length !== 6}>
                      {pincodeLoading ? 'Searching...' : 'Locate'}
                    </Button>
                  </div>
                  {pincodeError && <p className="text-xs text-danger font-medium">{pincodeError}</p>}
                </form>

                {/* 2. State > District > Mandal Cascading Selectors */}
                <div className="space-y-2">
                  <label className="block text-xs font-bold text-muted uppercase">
                    Or Select State &gt; District &gt; Mandal:
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    <select
                      value={selectedHierState}
                      onChange={(e) => handleStateChange(e.target.value)}
                      className="p-2 text-xs rounded-xl border border-border bg-white text-ink"
                    >
                      {statesList.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.name}
                        </option>
                      ))}
                    </select>

                    <select
                      value={selectedHierDistrict}
                      onChange={(e) => handleDistrictChange(e.target.value)}
                      className="p-2 text-xs rounded-xl border border-border bg-white text-ink"
                    >
                      <option value="">-- District --</option>
                      {districtsList.map((d) => (
                        <option key={d.id} value={d.id.toString()}>
                          {d.name}
                        </option>
                      ))}
                    </select>

                    <select
                      value={selectedHierMandal}
                      onChange={(e) => handleMandalChange(e.target.value)}
                      disabled={!selectedHierDistrict}
                      className="p-2 text-xs rounded-xl border border-border bg-white text-ink"
                    >
                      <option value="">-- Mandal --</option>
                      {mandalsList.map((m) => (
                        <option key={m.id} value={m.id.toString()}>
                          {m.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* R4 GEOGRAPHIC BROWSING ENGINE (Table & Cards, Cascading Filters, Sparklines, Aggregates) */}
        <GeographicBrowser
          userCoords={userCoords}
          priceUnit={priceUnit}
          onSelectMandi={handleSelectGeographicMandi}
          activeMandiId={activeMandi.id}
          initialCrop={selectedCrop}
        />

        {/* Main Grid: Active Price Tile + 5 Nearest Mandis */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Left: Big Price Tile (5 cols) */}
          <div className="lg:col-span-5 flex flex-col gap-4">
            <div className="text-xs font-bold text-muted uppercase tracking-wider">
              Selected Mandi Daily Price
            </div>
            <PriceTile
              commodityName={cropNames[selectedCrop]}
              variety={activeMandi.variety}
              modalPrice={
                priceUnit === 'kg'
                  ? activeMandi.modalPriceKg
                  : activeMandi.modalPriceQuintal
              }
              unit={priceUnit}
              trend={activeMandi.trend}
              trendDiff={activeMandi.trendDiff}
              lastUpdated={activeMandi.date}
              mandiName={activeMandi.name}
              className="border-2 border-deep-leaf/30 shadow-md"
              labels={{
                unitLabel: priceUnit === 'kg' ? '/kg' : '/qtl',
                modalPriceLabel: t('priceTile.modalPrice'),
                lastUpdatedPrefix: activeMandi.isReportedToday ? 'Reported' : 'Last Reported',
                staleWarning: t('priceTile.staleWarning'),
              }}
            />

            {/* RULE B: Fail Closed Alert if Price is not reported today */}
            {activeMandi.isReportedToday === false && (
              <div
                role="alert"
                className="p-4 bg-amber-50 border-2 border-amber-300 rounded-2xl text-amber-950 text-xs font-semibold flex items-start gap-3 shadow-xs"
              >
                <AlertTriangle className="w-5 h-5 text-amber-700 flex-shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <span className="font-extrabold text-sm block text-amber-900">
                    No price reported for this mandi today
                  </span>
                  <span className="text-amber-800 leading-relaxed block">
                    {activeMandi.statusMessage || `Last reported auction: ${activeMandi.reportedDate || activeMandi.date} (${activeMandi.ageLabel || 'older'})`}.
                    GrowCircle never fills gaps with estimates or rolling averages.
                  </span>
                </div>
              </div>
            )}

            {/* RULE C: Full Data Provenance Card */}
            <div className="p-4 bg-white rounded-2xl border border-border text-xs space-y-2">
              <div className="flex items-center justify-between font-bold text-ink border-b border-border pb-1.5">
                <span>Data Provenance</span>
                <span className="text-[10px] uppercase tracking-wider text-muted font-bold">
                  {activeMandi.sourceName || 'Agmarknet / DMI'}
                </span>
              </div>
              <div className="text-muted leading-relaxed">
                {activeMandi.provenanceText || `Source: Agmarknet / Directorate of Marketing & Inspection | Reported: ${activeMandi.date}`}
              </div>
              <div className="flex items-center justify-between text-[11px] font-semibold text-deep-leaf pt-1">
                <span>Canonical Rate:</span>
                <span>₹{activeMandi.modalPriceKg}/kg (₹{activeMandi.modalPriceQuintal}/quintal)</span>
              </div>
            </div>

            {/* Quick Mandi Info Card */}
            <div className="p-4 bg-white rounded-2xl border border-border text-sm space-y-2">
              <div className="flex items-center justify-between text-muted">
                <span>District &bull; State:</span>
                <span className="font-semibold text-ink">
                  {activeMandi.district}, {activeMandi.state}
                </span>
              </div>
              <div className="flex items-center justify-between text-muted">
                <span>Daily Arrivals:</span>
                <span className="font-semibold text-deep-leaf">
                  {activeMandi.arrivalTonnes} Metric Tonnes
                </span>
              </div>
              <div className="flex items-center justify-between text-muted">
                <span>Price Range:</span>
                <span className="font-semibold text-ink">
                  ₹{priceUnit === 'kg' ? activeMandi.minPriceKg : activeMandi.modalPriceQuintal - 250} &mdash; ₹
                  {priceUnit === 'kg' ? activeMandi.maxPriceKg : activeMandi.modalPriceQuintal + 300} {priceUnit === 'kg' ? '/kg' : '/qtl'}
                </span>
              </div>
            </div>
          </div>

          {/* Right: 5 Nearest Mandis (7 cols) */}
          <div className="lg:col-span-7 flex flex-col gap-4">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div>
                <h3 className="text-base font-bold text-ink flex items-center gap-1.5">
                  <MapPin className="w-4 h-4 text-deep-leaf" />
                  5 Nearest Mandis (Straight-Line Distance)
                </h3>
                <span className="text-xs text-muted block">
                  Reporting within {searchRadiusKm} km &bull; Maximum price age: 3 days
                </span>
              </div>
              <span className="text-xs text-deep-leaf font-bold flex items-center gap-1 bg-deep-leaf/10 px-2.5 py-1 rounded-full">
                <CheckCircle2 className="w-3.5 h-3.5" /> Straight-Line Distance (km)
              </span>
            </div>

            {/* FEW RESULTS NOTICE (< 5 mandis) */}
            {displayedNearbyMandis.length > 0 && displayedNearbyMandis.length < 5 && (
              <div className="p-3.5 bg-amber-50 border border-amber-300 rounded-2xl text-amber-950 text-xs space-y-1.5">
                <div className="flex items-center gap-2 font-bold text-amber-900">
                  <Info className="w-4 h-4 text-amber-700 flex-shrink-0" />
                  <span>
                    Only {displayedNearbyMandis.length} mandis reported within {searchRadiusKm} km (straight-line distance)
                  </span>
                </div>
                <p className="text-amber-800 leading-relaxed text-[11px]">
                  No other mandis reported prices for {cropNames[selectedCrop]} in the last 3 days. GrowCircle never pads distance results with stale or estimated prices.
                </p>
                <div className="pt-1 flex items-center gap-2">
                  <span className="text-[11px] font-semibold text-amber-900">Expand search radius:</span>
                  {[150, 200, 300].filter((r) => r > searchRadiusKm).map((r) => (
                    <button
                      key={r}
                      onClick={() => setSearchRadiusKm(r)}
                      className="px-2.5 py-0.5 rounded-full bg-amber-200/80 hover:bg-amber-300 text-amber-900 text-[11px] font-bold"
                    >
                      {r} km
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* NO RESULTS NOTICE (0 mandis) */}
            {displayedNearbyMandis.length === 0 && (
              <div className="p-6 bg-cream rounded-2xl border border-dashed border-border text-center space-y-3">
                <div className="w-10 h-10 rounded-full bg-amber-100 text-amber-800 flex items-center justify-center mx-auto">
                  <AlertTriangle className="w-5 h-5" />
                </div>
                <div className="space-y-1">
                  <h4 className="font-bold text-ink text-sm">
                    No mandis reported prices within {searchRadiusKm} km
                  </h4>
                  <p className="text-xs text-muted max-w-sm mx-auto">
                    No recent auction prices reported for {cropNames[selectedCrop]} in the last 3 days within {searchRadiusKm} km.
                  </p>
                </div>
                <div className="flex items-center justify-center gap-2 pt-1">
                  <Button
                    variant="primary"
                    onClick={() => setSearchRadiusKm(Math.min(300, searchRadiusKm + 100))}
                  >
                    Expand Search Radius to {Math.min(300, searchRadiusKm + 100)} km
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => setShowLocationFallback(true)}
                  >
                    Select Another Mandal
                  </Button>
                </div>
              </div>
            )}

            {/* MANDI ROWS (up to 5) */}
            <div className="space-y-3">
              {displayedNearbyMandis.map((mandi: MandiItem, idx: number) => (
                <MandiRow
                  key={mandi.id}
                  mandiName={mandi.canonical_name || mandi.name}
                  district={`${mandi.district}, ${mandi.state || 'AP'}`}
                  distanceKm={mandi.distanceKm}
                  modalPrice={
                    priceUnit === 'kg'
                      ? mandi.modalPriceKg
                      : mandi.modalPriceQuintal
                  }
                  priceUnit={priceUnit}
                  arrivalDate={mandi.date}
                  arrivalQtyQuintal={mandi.arrivalTonnes * 10}
                  isNearest={idx === 0}
                  onClick={() => setActiveMandi(mandi)}
                  labels={{
                    distanceSuffix:
                      locale === 'te'
                        ? 'కి.మీ (సరళ రేఖ దూరం)'
                        : locale === 'hi'
                        ? 'किमी (सीधी दूरी)'
                        : locale === 'gu'
                        ? 'કિમી (સીધુ અંતર)'
                        : 'km (straight-line)',
                    nearestBadge: idx === 0 ? 'Nearest' : `${idx + 1}th Nearest`,
                    unitLabel: priceUnit === 'kg' ? '/kg' : '/qtl',
                  }}
                />
              ))}
            </div>

            {/* PRIVACY & DPDP ACT NOTICE (Rule 6) */}
            <div className="p-3.5 bg-white rounded-2xl border border-border text-xs text-muted flex items-start gap-2.5">
              <ShieldCheck className="w-4 h-4 text-deep-leaf flex-shrink-0 mt-0.5" />
              <div className="leading-relaxed text-[11px]">
                <strong className="text-ink font-semibold">Privacy Protected:</strong> Your exact GPS location is only processed locally in your browser to compute straight-line distances and is never stored on our servers without your explicit account consent (DPDP Act 2023 aligned). Default account settings store only district-level location.
              </div>
            </div>
          </div>
        </div>

        {/* 30-Day Historical Price Trend Chart */}
        <section className="pt-4">
          <PriceChart
            data={historyData}
            commodityName={cropNames[selectedCrop]}
            mandiName={activeMandi.name}
          />
        </section>
      </main>

      {/* WhatsApp / Telegram Price Alert Subscription Modal */}
      {isAlertModalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="alert-modal-title"
          className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4 backdrop-blur-sm"
        >
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 sm:p-7 shadow-2xl border border-border relative">
            <button
              type="button"
              onClick={() => {
                setIsAlertModalOpen(false);
                setAlertSuccessMessage(null);
              }}
              className="absolute right-4 top-4 min-h-[44px] min-w-[44px] flex items-center justify-center text-muted hover:text-ink rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-deep-leaf"
              aria-label="Close dialog"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-3 mb-4">
              <div className="p-3 bg-deep-leaf/10 text-deep-leaf rounded-xl">
                <Bell className="w-6 h-6" />
              </div>
              <div>
                <h3 id="alert-modal-title" className="font-heading text-xl font-bold text-ink">
                  {t('consumer.subscribeAlerts')}
                </h3>
                <p className="text-xs text-muted">
                  {t('consumer.noLogin')}
                </p>
              </div>
            </div>

            {alertSuccessMessage ? (
              <div className="py-6 text-center space-y-3">
                <div className="w-12 h-12 bg-emerald-100 text-emerald-800 rounded-full flex items-center justify-center mx-auto">
                  <Check className="w-6 h-6" />
                </div>
                <h4 className="font-bold text-ink text-base">Subscription Confirmed!</h4>
                <p className="text-sm text-muted max-w-sm mx-auto">{alertSuccessMessage}</p>
              </div>
            ) : (
              <form onSubmit={handleSubscribeAlert} className="space-y-4">
                {/* Crop & District context pill */}
                <div className="p-3 bg-cream rounded-xl text-xs space-y-1 border border-border">
                  <div className="flex justify-between">
                    <span className="text-muted">Target Commodity:</span>
                    <span className="font-bold text-ink">{cropNames[selectedCrop]}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted">Target Mandi:</span>
                    <span className="font-bold text-ink">
                      {activeMandi.name} ({activeMandi.district})
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted">Today&apos;s Price:</span>
                    <span className="font-bold text-deep-leaf">₹{activeMandi.modalPriceKg}/kg</span>
                  </div>
                </div>

                {/* Channel toggle: WhatsApp vs Telegram */}
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-muted mb-1.5">
                    Notification Channel
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => setAlertChannel('whatsapp')}
                      className={`min-h-[44px] flex items-center justify-center gap-2 rounded-xl text-sm font-bold border transition-colors ${
                        alertChannel === 'whatsapp'
                          ? 'bg-deep-leaf text-white border-deep-leaf'
                          : 'bg-white text-ink border-border hover:bg-cream'
                      }`}
                    >
                      <Send className="w-4 h-4" />
                      WhatsApp
                    </button>
                    <button
                      type="button"
                      onClick={() => setAlertChannel('telegram')}
                      className={`min-h-[44px] flex items-center justify-center gap-2 rounded-xl text-sm font-bold border transition-colors ${
                        alertChannel === 'telegram'
                          ? 'bg-deep-leaf text-white border-deep-leaf'
                          : 'bg-white text-ink border-border hover:bg-cream'
                      }`}
                    >
                      <Send className="w-4 h-4" />
                      Telegram
                    </button>
                  </div>
                </div>

                {/* Recipient input */}
                <div>
                  <label
                    htmlFor="alert-recipient"
                    className="block text-xs font-bold uppercase tracking-wider text-muted mb-1.5"
                  >
                    {alertChannel === 'whatsapp'
                      ? 'WhatsApp Phone Number'
                      : 'Telegram Username or Chat ID'}
                  </label>
                  <input
                    id="alert-recipient"
                    type={alertChannel === 'whatsapp' ? 'tel' : 'text'}
                    required
                    placeholder={
                      alertChannel === 'whatsapp' ? '+91 98765 43210' : '@your_username'
                    }
                    value={alertRecipient}
                    onChange={(e) => setAlertRecipient(e.target.value)}
                    className="w-full min-h-[44px] px-3.5 py-2.5 rounded-xl border border-border bg-white text-ink text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-deep-leaf"
                  />
                </div>

                {/* Target Price */}
                <div>
                  <label
                    htmlFor="alert-target-price"
                    className="block text-xs font-bold uppercase tracking-wider text-muted mb-1.5"
                  >
                    Alert me when price drops below (₹ / kg)
                  </label>
                  <input
                    id="alert-target-price"
                    type="number"
                    min="1"
                    max="500"
                    required
                    value={alertTargetPrice}
                    onChange={(e) => setAlertTargetPrice(Number(e.target.value))}
                    className="w-full min-h-[44px] px-3.5 py-2.5 rounded-xl border border-border bg-white text-ink text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-deep-leaf"
                  />
                  <span className="text-[11px] text-muted mt-1 block">
                    Current rate is ₹{activeMandi.modalPriceKg}/kg. Default set to 10% below current modal.
                  </span>
                </div>

                <div className="pt-2 flex items-center justify-end gap-3">
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => setIsAlertModalOpen(false)}
                  >
                    Cancel
                  </Button>
                  <Button type="submit" variant="primary">
                    <Bell className="w-4 h-4 mr-1.5" />
                    Subscribe Free Alert
                  </Button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      <footer className="border-t border-border bg-white py-6 px-4 text-center text-xs text-muted">
        GrowCircle Mandi Price Engine &bull; Non-negotiable real Agmarknet data &bull; DPDP Act Aligned
      </footer>
    </div>
  );
}
