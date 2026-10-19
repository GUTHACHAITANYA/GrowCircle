'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Table,
  LayoutGrid,
  MapPin,
  ArrowUpDown,
  AlertTriangle,
  CheckCircle2,
  Info,
  RotateCcw,
  Search,
  Building2,
  Calendar,
  Layers,
  ChevronLeft,
  ChevronRight,
  TrendingUp,
  ShieldCheck,
  Scale,
} from 'lucide-react';
import { PriceSparkline } from './PriceSparkline';
import { API_BASE } from '@/lib/api';

export interface PriceRecord {
  mandi_id: number;
  mandi_name: string;
  canonical_name?: string | null;
  district: string;
  state: string;
  mandal?: string | null;
  crop_id: string;
  crop_name_en: string;
  variety: string;
  grade: string;
  price_date: string;
  reported_date: string;
  age_label: string;
  is_reported_today: boolean;
  min_price_kg: number;
  max_price_kg: number;
  modal_price_kg: number;
  min_price_quintal: number;
  max_price_quintal: number;
  modal_price_quintal: number;
  arrival_tonnes: number;
  distance_km?: number | null;
  distance_label?: string;
  sparkline_30d: number[];
  source: string;
  source_name: string;
  provenance_text: string;
  status_message?: string | null;
}

export interface PriceAggregate {
  state?: string | null;
  district?: string | null;
  mandal?: string | null;
  mandi?: string | null;
  crop: string;
  variety?: string | null;
  reporting_mandis_count: number;
  total_records: number;
  median_modal_price_kg?: number | null;
  median_modal_price_quintal?: number | null;
  min_modal_price_kg?: number | null;
  max_modal_price_kg?: number | null;
  avg_arrival_tonnes: number;
  is_area_average_reliable: boolean;
  area_level: string;
  area_name: string;
  note: string;
  mandal_has_mandi: boolean;
  mandal_status_message?: string | null;
}

interface GeographicBrowserProps {
  userCoords?: { lat: number; lng: number; source: string; label: string } | null;
  priceUnit: 'kg' | 'quintal';
  onSelectMandi?: (mandi: PriceRecord) => void;
  activeMandiId?: number;
  initialCrop?: string;
}

const STORAGE_KEY = 'growcircle_geo_filters_v2';

export function GeographicBrowser({
  userCoords,
  priceUnit,
  onSelectMandi,
  activeMandiId,
  initialCrop = 'banana',
}: GeographicBrowserProps) {
  // 1. Cascading Filters State
  const [geoState, setGeoState] = useState<string>('Andhra Pradesh');
  const [geoDistrict, setGeoDistrict] = useState<string>('Guntur');
  const [geoMandal, setGeoMandal] = useState<string>('');
  const [geoMandi, setGeoMandi] = useState<string>('');
  const [selectedCrop, setSelectedCrop] = useState<string>(initialCrop);
  const [selectedVariety, setSelectedVariety] = useState<string>('');

  // 2. View Mode & Sorting State
  const [viewMode, setViewMode] = useState<'table' | 'cards'>('table');
  const [sortBy, setSortBy] = useState<'price' | 'distance' | 'name' | 'date'>('price');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');

  // 3. Dynamic Options from Database
  const [statesOptions, setStatesOptions] = useState<Array<{ id: string; name: string }>>([]);
  const [districtsOptions, setDistrictsOptions] = useState<Array<{ id: number; name: string; state_id: string }>>([]);
  const [mandalsOptions, setMandalsOptions] = useState<Array<{ id: number; name: string }>>([]);
  const [mandisOptions, setMandisOptions] = useState<Array<{ id: number; name: string; canonical_name?: string }>>([]);
  const [cropsOptions, setCropsOptions] = useState<string[]>(['banana', 'chilli', 'onion', 'tomato']);
  const [varietiesOptions, setVarietiesOptions] = useState<string[]>([]);

  // 4. Data & Response States
  const [pricesList, setPricesList] = useState<PriceRecord[]>([]);
  const [aggregates, setAggregates] = useState<PriceAggregate | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isLoadingAggregates, setIsLoadingAggregates] = useState<boolean>(true);
  const [mandalHasNoMandi, setMandalHasNoMandi] = useState<boolean>(false);
  const [mandalFallbackMessage, setMandalFallbackMessage] = useState<string | null>(null);

  // 5. Pagination
  const [currentPage, setCurrentPage] = useState<number>(1);
  const pageSize = 10;

  // A. Load saved selection from LocalStorage or user profile
  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed.geoState) setGeoState(parsed.geoState);
        if (parsed.geoDistrict) setGeoDistrict(parsed.geoDistrict);
        if (parsed.geoMandal) setGeoMandal(parsed.geoMandal);
        if (parsed.geoMandi) setGeoMandi(parsed.geoMandi);
        if (parsed.selectedCrop) setSelectedCrop(parsed.selectedCrop);
        if (parsed.selectedVariety) setSelectedVariety(parsed.selectedVariety);
        if (parsed.viewMode) setViewMode(parsed.viewMode);
        if (parsed.sortBy) setSortBy(parsed.sortBy);
        if (parsed.sortOrder) setSortOrder(parsed.sortOrder);
      } else {
        // Fallback: check profile preferences endpoint
        fetch(`${API_BASE}/user/preferences`)
          .then((res) => (res.ok ? res.json() : null))
          .then((pref) => {
            if (pref) {
              if (pref.state) setGeoState(pref.state);
              if (pref.district) setGeoDistrict(pref.district);
              if (pref.crop) setSelectedCrop(pref.crop);
            }
          })
          .catch(() => {});
      }
    } catch (e) {
      console.warn('Could not restore filters from localStorage:', e);
    }
  }, []);

  // B. Save changes to LocalStorage and user profile
  useEffect(() => {
    try {
      const payload = {
        geoState,
        geoDistrict,
        geoMandal,
        geoMandi,
        selectedCrop,
        selectedVariety,
        viewMode,
        sortBy,
        sortOrder,
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));

      // Best effort profile sync
      fetch(`${API_BASE}/user/preferences`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          state: geoState,
          district: geoDistrict,
          mandal: geoMandal,
          crop: selectedCrop,
        }),
      }).catch(() => {});
    } catch (e) {
      console.warn('Could not save filters to localStorage:', e);
    }
  }, [geoState, geoDistrict, geoMandal, geoMandi, selectedCrop, selectedVariety, viewMode, sortBy, sortOrder]);

  // C. Load initial database options (States and Crops)
  useEffect(() => {
    async function loadInitialOptions() {
      try {
        const [statesRes, cropsRes] = await Promise.all([
          fetch(`${API_BASE}/hierarchy/states`),
          fetch(`${API_BASE}/crops`),
        ]);

        if (statesRes.ok) {
          const sData = await statesRes.json();
          if (Array.isArray(sData)) setStatesOptions(sData);
        }
        if (cropsRes.ok) {
          const cData = await cropsRes.json();
          if (Array.isArray(cData)) {
            const cropStrings = cData
              .map((c: any) => (typeof c === 'string' ? c : (c.id || c.name_en || '').toLowerCase()))
              .filter(Boolean);
            if (cropStrings.length > 0) setCropsOptions(cropStrings);
          }
        }
      } catch (err) {
        console.warn('Initial options fetch warning:', err);
      }
    }
    loadInitialOptions();
  }, []);

  // D. Cascade: When State changes, fetch Districts and Mandis for that state
  useEffect(() => {
    async function loadDistrictsForState() {
      if (!geoState) {
        setDistrictsOptions([]);
        return;
      }
      try {
        const res = await fetch(`${API_BASE}/hierarchy/districts?state=${encodeURIComponent(geoState)}`);
        if (res.ok) {
          const data = await res.json();
          setDistrictsOptions(Array.isArray(data) ? data : []);
        }
      } catch (err) {
        console.warn('Districts load error:', err);
      }
    }
    loadDistrictsForState();
  }, [geoState]);

  // E. Cascade: When District changes, fetch Mandals and Mandis for that district
  useEffect(() => {
    async function loadMandalsAndMandis() {
      if (!geoDistrict) {
        setMandalsOptions([]);
        setMandisOptions([]);
        return;
      }
      try {
        const [mandalsRes, mandisRes] = await Promise.all([
          fetch(`${API_BASE}/hierarchy/mandals?district=${encodeURIComponent(geoDistrict)}`),
          fetch(
            `${API_BASE}/hierarchy/mandis?state=${encodeURIComponent(geoState)}&district=${encodeURIComponent(
              geoDistrict
            )}${geoMandal ? `&mandal=${encodeURIComponent(geoMandal)}` : ''}`
          ),
        ]);

        if (mandalsRes.ok) {
          const mData = await mandalsRes.json();
          setMandalsOptions(Array.isArray(mData) ? mData : []);
        }
        if (mandisRes.ok) {
          const mdData = await mandisRes.json();
          setMandisOptions(Array.isArray(mdData) ? mdData : []);
        }
      } catch (err) {
        console.warn('Mandals/Mandis load error:', err);
      }
    }
    loadMandalsAndMandis();
  }, [geoState, geoDistrict, geoMandal]);

  // F. Cascade: When Crop changes, fetch Varieties
  useEffect(() => {
    async function loadVarietiesForCrop() {
      if (!selectedCrop) {
        setVarietiesOptions([]);
        return;
      }
      try {
        const res = await fetch(`${API_BASE}/varieties?crop=${encodeURIComponent(selectedCrop)}`);
        if (res.ok) {
          const data = await res.json();
          setVarietiesOptions(Array.isArray(data) ? data : []);
        }
      } catch (err) {
        console.warn('Varieties load error:', err);
      }
    }
    loadVarietiesForCrop();
  }, [selectedCrop]);

  // G. Fetch Prices and Aggregates dynamically
  const fetchPricesAndAggregates = useCallback(async () => {
    setIsLoading(true);
    setIsLoadingAggregates(true);

    const params = new URLSearchParams();
    if (geoState) params.append('state', geoState);
    if (geoDistrict) params.append('district', geoDistrict);
    if (geoMandal) params.append('mandal', geoMandal);
    if (geoMandi) params.append('mandi', geoMandi);
    if (selectedCrop) params.append('crop', selectedCrop);
    if (selectedVariety) params.append('variety', selectedVariety);
    if (sortBy) params.append('sort_by', sortBy);
    if (sortOrder) params.append('sort_order', sortOrder);
    if (userCoords?.lat && userCoords?.lng) {
      params.append('user_lat', userCoords.lat.toString());
      params.append('user_lng', userCoords.lng.toString());
    }

    try {
      // 1. Fetch Prices list
      const pricesUrl = `${API_BASE}/prices?${params.toString()}`;
      const pricesRes = await fetch(pricesUrl);

      if (pricesRes.ok) {
        const data: PriceRecord[] = await pricesRes.json();
        setPricesList(data);

        // Check honest fallback header
        const mandalHasMandiHdr = pricesRes.headers.get('x-mandal-has-mandi');
        const mandalFallbackHdr = pricesRes.headers.get('x-mandal-fallback');
        if (mandalHasMandiHdr === 'false' || mandalFallbackHdr === 'true') {
          setMandalHasNoMandi(true);
          const firstMsg = data[0]?.status_message;
          setMandalFallbackMessage(
            firstMsg || `No mandi exists in ${geoMandal} mandal. Showing nearest reporting mandis.`
          );
        } else {
          setMandalHasNoMandi(false);
          setMandalFallbackMessage(null);
        }
      } else {
        setPricesList([]);
      }

      // 2. Fetch Aggregates (with 5-minute backend cache)
      const aggUrl = `${API_BASE}/prices/aggregates?${params.toString()}`;
      const aggRes = await fetch(aggUrl);
      if (aggRes.ok) {
        const aggData: PriceAggregate = await aggRes.json();
        setAggregates(aggData);
        if (aggData.mandal_has_mandi === false) {
          setMandalHasNoMandi(true);
          setMandalFallbackMessage(
            aggData.mandal_status_message ||
              `No mandi exists in ${geoMandal} mandal. Showing nearest reporting mandis.`
          );
        }
      }
    } catch (err) {
      console.warn('Error fetching prices or aggregates:', err);
    } finally {
      setIsLoading(false);
      setIsLoadingAggregates(false);
    }
  }, [geoState, geoDistrict, geoMandal, geoMandi, selectedCrop, selectedVariety, sortBy, sortOrder, userCoords]);

  useEffect(() => {
    fetchPricesAndAggregates();
    setCurrentPage(1);
  }, [fetchPricesAndAggregates]);

  // Reset Filters
  const handleResetFilters = () => {
    setGeoState('Andhra Pradesh');
    setGeoDistrict('Guntur');
    setGeoMandal('');
    setGeoMandi('');
    setSelectedCrop('banana');
    setSelectedVariety('');
    setSortBy('price');
    setSortOrder('asc');
  };

  // Pagination calculation
  const totalItems = pricesList.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
  const paginatedPrices = pricesList.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  const toggleSort = (column: 'price' | 'distance' | 'name' | 'date') => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder(column === 'price' || column === 'distance' ? 'asc' : 'desc');
    }
  };

  return (
    <section aria-labelledby="geo-browser-title" className="space-y-6">
      {/* SECTION HEADER & VIEW CONTROLS */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-border">
        <div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-deep-leaf/10 text-deep-leaf text-xs font-bold mb-2">
            <Building2 className="w-3.5 h-3.5" />
            <span>Geographic Browsing Engine &bull; APMC Public Mandi Data</span>
          </div>
          <h2 id="geo-browser-title" className="font-heading text-2xl sm:text-3xl font-extrabold text-ink">
            Mandi Price Explorer
          </h2>
          <p className="text-xs sm:text-sm text-muted mt-1">
            Browse real daily auction modal rates across State &gt; District &gt; Mandal &gt; Mandi.
          </p>
        </div>

        {/* View Switcher & Action Toolbar */}
        <div className="flex items-center gap-2 self-start md:self-auto">
          <div className="inline-flex items-center p-1 bg-white border border-border rounded-xl shadow-xs">
            <button
              type="button"
              onClick={() => setViewMode('table')}
              className={`min-h-[38px] px-3.5 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-colors ${
                viewMode === 'table' ? 'bg-deep-leaf text-white' : 'text-ink hover:text-deep-leaf'
              }`}
              title="Table View"
            >
              <Table className="w-4 h-4" />
              <span>Table</span>
            </button>
            <button
              type="button"
              onClick={() => setViewMode('cards')}
              className={`min-h-[38px] px-3.5 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-colors ${
                viewMode === 'cards' ? 'bg-deep-leaf text-white' : 'text-ink hover:text-deep-leaf'
              }`}
              title="Grid / List View"
            >
              <LayoutGrid className="w-4 h-4" />
              <span>Cards</span>
            </button>
          </div>

          <button
            type="button"
            onClick={handleResetFilters}
            className="min-h-[38px] px-3 py-1.5 rounded-xl border border-border bg-white text-ink text-xs font-semibold hover:bg-cream flex items-center gap-1.5 transition-colors shadow-xs"
            title="Reset to default filters"
          >
            <RotateCcw className="w-3.5 h-3.5 text-muted" />
            <span>Reset</span>
          </button>
        </div>
      </div>

      {/* 1. DYNAMIC CASCADING FILTERS BAR (Rule 1) */}
      <div className="p-4 sm:p-5 bg-white rounded-2xl border border-border shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-muted uppercase tracking-wider flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-deep-leaf" />
            Cascading Geographic &amp; Crop Selectors
          </span>
          <span className="text-[11px] text-muted">
            Options loaded dynamically from database &bull; All levels optional
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {/* Level 1: State */}
          <div className="space-y-1">
            <label className="block text-[11px] font-bold text-muted uppercase">1. State</label>
            <select
              value={geoState}
              onChange={(e) => {
                setGeoState(e.target.value);
                setGeoDistrict('');
                setGeoMandal('');
                setGeoMandi('');
              }}
              className="w-full p-2.5 bg-cream border border-border rounded-xl text-xs font-semibold text-ink focus:outline-none focus:ring-2 focus:ring-deep-leaf cursor-pointer"
            >
              <option value="">All States</option>
              {statesOptions.map((s) => (
                <option key={s.id} value={s.name}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>

          {/* Level 2: District */}
          <div className="space-y-1">
            <label className="block text-[11px] font-bold text-muted uppercase">2. District</label>
            <select
              value={geoDistrict}
              onChange={(e) => {
                setGeoDistrict(e.target.value);
                setGeoMandal('');
                setGeoMandi('');
              }}
              className="w-full p-2.5 bg-cream border border-border rounded-xl text-xs font-semibold text-ink focus:outline-none focus:ring-2 focus:ring-deep-leaf cursor-pointer"
            >
              <option value="">All Districts</option>
              {districtsOptions.map((d) => (
                <option key={d.id} value={d.name}>
                  {d.name}
                </option>
              ))}
            </select>
          </div>

          {/* Level 3: Mandal */}
          <div className="space-y-1">
            <label className="block text-[11px] font-bold text-muted uppercase">3. Mandal</label>
            <select
              value={geoMandal}
              onChange={(e) => {
                setGeoMandal(e.target.value);
                setGeoMandi('');
              }}
              disabled={!geoDistrict}
              className="w-full p-2.5 bg-cream border border-border rounded-xl text-xs font-semibold text-ink focus:outline-none focus:ring-2 focus:ring-deep-leaf cursor-pointer disabled:opacity-50"
            >
              <option value="">All Mandals</option>
              {mandalsOptions.map((m) => (
                <option key={m.id} value={m.name}>
                  {m.name}
                </option>
              ))}
            </select>
          </div>

          {/* Level 4: Mandi */}
          <div className="space-y-1">
            <label className="block text-[11px] font-bold text-muted uppercase">4. Mandi</label>
            <select
              value={geoMandi}
              onChange={(e) => setGeoMandi(e.target.value)}
              className="w-full p-2.5 bg-cream border border-border rounded-xl text-xs font-semibold text-ink focus:outline-none focus:ring-2 focus:ring-deep-leaf cursor-pointer"
            >
              <option value="">All Mandis</option>
              {mandisOptions.map((m) => (
                <option key={m.id} value={m.name}>
                  {m.name}
                </option>
              ))}
            </select>
          </div>

          {/* Level 5: Crop */}
          <div className="space-y-1">
            <label className="block text-[11px] font-bold text-muted uppercase">5. Commodity</label>
            <select
              value={selectedCrop}
              onChange={(e) => {
                setSelectedCrop(e.target.value);
                setSelectedVariety('');
              }}
              className="w-full p-2.5 bg-cream border border-border rounded-xl text-xs font-semibold text-ink capitalize focus:outline-none focus:ring-2 focus:ring-deep-leaf cursor-pointer"
            >
              {cropsOptions.map((c: any) => {
                const cId = typeof c === 'string' ? c : (c.id || '');
                const cLabel = typeof c === 'string' ? (c.charAt(0).toUpperCase() + c.slice(1)) : (c.name_en || c.id || '');
                return (
                  <option key={cId} value={cId}>
                    {cLabel}
                  </option>
                );
              })}
            </select>
          </div>

          {/* Level 6: Variety */}
          <div className="space-y-1">
            <label className="block text-[11px] font-bold text-muted uppercase">6. Variety</label>
            <select
              value={selectedVariety}
              onChange={(e) => setSelectedVariety(e.target.value)}
              className="w-full p-2.5 bg-cream border border-border rounded-xl text-xs font-semibold text-ink focus:outline-none focus:ring-2 focus:ring-deep-leaf cursor-pointer"
            >
              <option value="">All Varieties</option>
              {varietiesOptions.map((v) => (
                <option key={v} value={v}>
                  {v}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* 2. AREA AGGREGATES & INTEGRITY BANNER (Rule 3) */}
      {aggregates && (
        <div className="p-5 bg-white rounded-2xl border border-border shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-muted">
                Area Benchmark Insights &bull;
              </span>
              <span className="text-sm font-extrabold text-ink">
                {aggregates.area_name} ({aggregates.crop.toUpperCase()})
              </span>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-muted">Mandis Reporting:</span>
              <span className="px-2.5 py-0.5 rounded-full bg-deep-leaf/10 text-deep-leaf text-xs font-extrabold">
                {aggregates.reporting_mandis_count}
              </span>
            </div>
          </div>

          {/* Metric Badges */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="p-3 bg-cream rounded-xl border border-border">
              <span className="block text-[11px] font-bold text-muted uppercase">Median Modal Price</span>
              <span className="text-lg sm:text-xl font-heading font-extrabold text-ink">
                {aggregates.median_modal_price_kg !== null ? (
                  <>
                    ₹
                    {priceUnit === 'kg'
                      ? aggregates.median_modal_price_kg
                      : aggregates.median_modal_price_quintal}
                    <span className="text-xs font-normal text-muted">/{priceUnit}</span>
                  </>
                ) : (
                  <span className="text-muted text-sm">&mdash;</span>
                )}
              </span>
            </div>

            <div className="p-3 bg-cream rounded-xl border border-border">
              <span className="block text-[11px] font-bold text-muted uppercase">Price Range</span>
              <span className="text-sm sm:text-base font-extrabold text-ink">
                {typeof aggregates.min_modal_price_kg === 'number' && typeof aggregates.max_modal_price_kg === 'number' ? (
                  <>
                    ₹
                    {priceUnit === 'kg'
                      ? aggregates.min_modal_price_kg
                      : Math.round(aggregates.min_modal_price_kg * 100)}{' '}
                    &mdash; ₹
                    {priceUnit === 'kg'
                      ? aggregates.max_modal_price_kg
                      : Math.round(aggregates.max_modal_price_kg * 100)}{' '}
                    <span className="text-xs font-normal text-muted">/{priceUnit}</span>
                  </>
                ) : (
                  <span className="text-muted text-sm">&mdash;</span>
                )}
              </span>
            </div>

            <div className="p-3 bg-cream rounded-xl border border-border">
              <span className="block text-[11px] font-bold text-muted uppercase">Avg Daily Arrivals</span>
              <span className="text-base sm:text-lg font-extrabold text-deep-leaf">
                {aggregates.avg_arrival_tonnes > 0 ? `${aggregates.avg_arrival_tonnes} Tonnes` : 'N/A'}
              </span>
            </div>

            <div className="p-3 bg-cream rounded-xl border border-border">
              <span className="block text-[11px] font-bold text-muted uppercase">Area Sample Size</span>
              <span className="text-base sm:text-lg font-extrabold text-ink">
                {aggregates.reporting_mandis_count}{' '}
                {aggregates.reporting_mandis_count === 1 ? 'Mandi' : 'Mandis'}
              </span>
            </div>
          </div>

          {/* INTEGRITY NOTICE: If only 1 or 2 mandis reported, say so explicitly! (Rule 3) */}
          {aggregates.reporting_mandis_count > 0 && aggregates.reporting_mandis_count <= 2 && (
            <div
              role="alert"
              className="p-3.5 bg-amber-50 border border-amber-300 rounded-xl text-amber-950 text-xs flex items-start gap-2.5"
            >
              <AlertTriangle className="w-4 h-4 text-amber-700 flex-shrink-0 mt-0.5" />
              <div className="space-y-0.5">
                <span className="font-extrabold text-amber-900 block">{aggregates.note}</span>
                <span className="text-amber-800 text-[11px] block">
                  Reporting sample is too small to present as a statistical area average. GrowCircle presents actual
                  auction transactions without synthetic extrapolation.
                </span>
              </div>
            </div>
          )}

          {aggregates.reporting_mandis_count >= 3 && (
            <div className="p-3 bg-emerald-50/70 border border-emerald-200 rounded-xl text-emerald-950 text-xs flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-700 flex-shrink-0" />
              <span className="font-semibold text-emerald-900">{aggregates.note}</span>
            </div>
          )}
        </div>
      )}

      {/* 3. HONEST MANDAL EMPTY STATE / FALLBACK (Rule 4) */}
      {mandalHasNoMandi && (
        <div
          role="alert"
          className="p-5 bg-amber-50 border-2 border-amber-300 rounded-2xl text-amber-950 text-xs space-y-2 shadow-sm"
        >
          <div className="flex items-center gap-2 font-bold text-sm text-amber-900">
            <AlertTriangle className="w-5 h-5 text-amber-700 flex-shrink-0" />
            <span>No APMC Mandi Exists in {geoMandal} Mandal</span>
          </div>
          <p className="text-amber-900 leading-relaxed text-xs">
            {mandalFallbackMessage ||
              `There is no government-notified market yard in ${geoMandal} mandal. Showing the nearest reporting mandis within 100 km (straight-line distance). GrowCircle never invents market data for mandals without mandis.`}
          </p>
          <div className="pt-1 text-[11px] font-semibold text-amber-800 flex items-center gap-1">
            <MapPin className="w-3.5 h-3.5 text-amber-700" />
            <span>Distance calculated from {geoMandal} mandal centroid</span>
          </div>
        </div>
      )}

      {/* 4. SORTING & TOOLBAR (Rule 2) */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs bg-white p-3.5 rounded-xl border border-border">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-muted font-bold uppercase">Sort By:</span>
          <div className="flex items-center gap-1.5 flex-wrap">
            <button
              type="button"
              onClick={() => toggleSort('price')}
              className={`px-3 py-1.5 rounded-lg font-semibold flex items-center gap-1 border transition-colors ${
                sortBy === 'price'
                  ? 'bg-deep-leaf text-white border-deep-leaf'
                  : 'bg-cream text-ink border-border hover:bg-cream/80'
              }`}
            >
              <span>Price ({priceUnit})</span>
              <ArrowUpDown className="w-3 h-3" />
            </button>

            <button
              type="button"
              onClick={() => toggleSort('distance')}
              className={`px-3 py-1.5 rounded-lg font-semibold flex items-center gap-1 border transition-colors ${
                sortBy === 'distance'
                  ? 'bg-deep-leaf text-white border-deep-leaf'
                  : 'bg-cream text-ink border-border hover:bg-cream/80'
              }`}
            >
              <span>Distance</span>
              <ArrowUpDown className="w-3 h-3" />
            </button>

            <button
              type="button"
              onClick={() => toggleSort('name')}
              className={`px-3 py-1.5 rounded-lg font-semibold flex items-center gap-1 border transition-colors ${
                sortBy === 'name'
                  ? 'bg-deep-leaf text-white border-deep-leaf'
                  : 'bg-cream text-ink border-border hover:bg-cream/80'
              }`}
            >
              <span>Mandi Name</span>
              <ArrowUpDown className="w-3 h-3" />
            </button>

            <button
              type="button"
              onClick={() => toggleSort('date')}
              className={`px-3 py-1.5 rounded-lg font-semibold flex items-center gap-1 border transition-colors ${
                sortBy === 'date'
                  ? 'bg-deep-leaf text-white border-deep-leaf'
                  : 'bg-cream text-ink border-border hover:bg-cream/80'
              }`}
            >
              <span>Date</span>
              <ArrowUpDown className="w-3 h-3" />
            </button>
          </div>
        </div>

        <div className="text-muted font-medium">
          Showing {paginatedPrices.length} of {totalItems} {totalItems === 1 ? 'mandi' : 'mandis'}
        </div>
      </div>

      {/* 5. DATA VIEWS (Rule 2) */}
      {isLoading ? (
        <div className="p-12 text-center bg-white rounded-2xl border border-border space-y-3">
          <div className="w-8 h-8 border-3 border-deep-leaf border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-sm font-semibold text-ink">Loading verified APMC prices...</p>
        </div>
      ) : paginatedPrices.length === 0 ? (
        <div className="p-12 text-center bg-white rounded-2xl border border-dashed border-border space-y-3">
          <div className="w-12 h-12 bg-amber-100 text-amber-800 rounded-full flex items-center justify-center mx-auto">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <h3 className="font-heading text-lg font-bold text-ink">No Mandis Reported Prices</h3>
          <p className="text-xs text-muted max-w-md mx-auto">
            No prices were reported matching the current geographic and variety filters. GrowCircle fails closed and
            never fills gaps with synthetic or rolling averages.
          </p>
          <button
            type="button"
            onClick={handleResetFilters}
            className="px-4 py-2 bg-deep-leaf text-white text-xs font-bold rounded-xl hover:bg-deep-leaf/90 transition-colors"
          >
            Reset Filters
          </button>
        </div>
      ) : viewMode === 'table' ? (
        /* TABLE VIEW (Rule 2) */
        <div className="bg-white rounded-2xl border border-border shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-cream/70 border-b border-border text-[11px] font-bold text-muted uppercase tracking-wider select-none">
                  <th scope="col" className="py-3.5 px-4 cursor-pointer" onClick={() => toggleSort('name')}>
                    <div className="flex items-center gap-1">
                      <span>Mandi / Market Yard</span>
                      <ArrowUpDown className="w-3 h-3 text-muted" />
                    </div>
                  </th>
                  <th scope="col" className="py-3.5 px-3">
                    District &bull; Mandal
                  </th>
                  <th scope="col" className="py-3.5 px-3">
                    Variety &bull; Grade
                  </th>
                  <th scope="col" className="py-3.5 px-4 cursor-pointer" onClick={() => toggleSort('price')}>
                    <div className="flex items-center gap-1">
                      <span>Modal Price</span>
                      <ArrowUpDown className="w-3 h-3 text-muted" />
                    </div>
                  </th>
                  <th scope="col" className="py-3.5 px-3">
                    Min &mdash; Max
                  </th>
                  <th scope="col" className="py-3.5 px-3">
                    Arrivals
                  </th>
                  <th scope="col" className="py-3.5 px-3 cursor-pointer" onClick={() => toggleSort('distance')}>
                    <div className="flex items-center gap-1">
                      <span>Distance</span>
                      <ArrowUpDown className="w-3 h-3 text-muted" />
                    </div>
                  </th>
                  <th scope="col" className="py-3.5 px-4 text-center">
                    30-Day Trend
                  </th>
                  <th scope="col" className="py-3.5 px-4 cursor-pointer text-right" onClick={() => toggleSort('date')}>
                    <div className="flex items-center justify-end gap-1">
                      <span>Reported Date</span>
                      <ArrowUpDown className="w-3 h-3 text-muted" />
                    </div>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {paginatedPrices.map((item) => {
                  const isSelected = activeMandiId === item.mandi_id;
                  const modalPrice = priceUnit === 'kg' ? item.modal_price_kg : item.modal_price_quintal;
                  const minPrice = priceUnit === 'kg' ? item.min_price_kg : item.min_price_quintal;
                  const maxPrice = priceUnit === 'kg' ? item.max_price_kg : item.max_price_quintal;

                  return (
                    <tr
                      key={`${item.mandi_id}-${item.crop_id}-${item.variety}`}
                      onClick={() => onSelectMandi && onSelectMandi(item)}
                      className={`hover:bg-cream/40 transition-colors cursor-pointer ${
                        isSelected ? 'bg-deep-leaf/5 font-semibold' : ''
                      }`}
                    >
                      {/* 1. Mandi Name */}
                      <td className="py-3.5 px-4">
                        <div className="space-y-0.5">
                          <span className="font-extrabold text-ink text-sm block">
                            {item.canonical_name || item.mandi_name}
                          </span>
                          {item.canonical_name && item.canonical_name !== item.mandi_name && (
                            <span className="text-[10px] text-muted block">APMC: {item.mandi_name}</span>
                          )}
                          <span className="inline-block px-1.5 py-0.2 rounded text-[10px] font-bold bg-muted/10 text-muted">
                            {item.source_name || 'Agmarknet'}
                          </span>
                        </div>
                      </td>

                      {/* 2. District & Mandal */}
                      <td className="py-3.5 px-3">
                        <div className="text-muted">
                          <span className="font-bold text-ink block">{item.district}</span>
                          <span className="text-[11px] block">{item.mandal || item.state}</span>
                        </div>
                      </td>

                      {/* 3. Variety & Grade */}
                      <td className="py-3.5 px-3">
                        <div>
                          <span className="font-semibold text-ink block">{item.variety}</span>
                          <span className="text-[10px] text-muted uppercase font-bold">{item.grade}</span>
                        </div>
                      </td>

                      {/* 4. Modal Price */}
                      <td className="py-3.5 px-4">
                        <div className="space-y-0.5">
                          <span className="text-base font-heading font-extrabold text-deep-leaf block">
                            ₹{modalPrice.toFixed(1)}
                            <span className="text-xs font-normal text-muted">/{priceUnit}</span>
                          </span>
                        </div>
                      </td>

                      {/* 5. Min - Max */}
                      <td className="py-3.5 px-3 text-muted">
                        <span>
                          ₹{minPrice.toFixed(0)} &mdash; ₹{maxPrice.toFixed(0)}
                        </span>
                      </td>

                      {/* 6. Arrivals */}
                      <td className="py-3.5 px-3 font-semibold text-ink">
                        {item.arrival_tonnes > 0 ? `${item.arrival_tonnes.toFixed(1)} MT` : '0.0 MT'}
                      </td>

                      {/* 7. Distance */}
                      <td className="py-3.5 px-3">
                        {item.distance_km !== null && item.distance_km !== undefined ? (
                          <span
                            className="inline-flex items-center gap-1 font-bold text-ink"
                            title={item.distance_label || 'straight-line distance'}
                          >
                            <MapPin className="w-3 h-3 text-deep-leaf flex-shrink-0" />
                            <span>{item.distance_km.toFixed(1)} km</span>
                          </span>
                        ) : (
                          <span className="text-muted font-mono">&mdash;</span>
                        )}
                      </td>

                      {/* 8. 30-Day Sparkline (Rule 2) */}
                      <td className="py-3.5 px-4 text-center">
                        <PriceSparkline points={item.sparkline_30d} />
                      </td>

                      {/* 9. Reported Date & Age */}
                      <td className="py-3.5 px-4 text-right">
                        <div className="space-y-0.5">
                          <span
                            className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-extrabold ${
                              item.is_reported_today
                                ? 'bg-emerald-100 text-emerald-800'
                                : 'bg-amber-100 text-amber-900'
                            }`}
                          >
                            {item.is_reported_today ? 'Today' : item.age_label}
                          </span>
                          <span className="text-[10px] text-muted block font-mono">
                            {item.reported_date}
                          </span>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        /* SIMPLE LIST / CARD VIEW (Rule 2) */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {paginatedPrices.map((item) => {
            const isSelected = activeMandiId === item.mandi_id;
            const modalPrice = priceUnit === 'kg' ? item.modal_price_kg : item.modal_price_quintal;
            const minPrice = priceUnit === 'kg' ? item.min_price_kg : item.min_price_quintal;
            const maxPrice = priceUnit === 'kg' ? item.max_price_kg : item.max_price_quintal;

            return (
              <div
                key={`${item.mandi_id}-${item.crop_id}-${item.variety}`}
                onClick={() => onSelectMandi && onSelectMandi(item)}
                className={`p-4 bg-white rounded-2xl border-2 transition-all cursor-pointer space-y-3.5 shadow-sm hover:border-deep-leaf/60 ${
                  isSelected ? 'border-deep-leaf ring-2 ring-deep-leaf/20' : 'border-border'
                }`}
              >
                {/* Header: Name and Distance */}
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h4 className="font-extrabold text-ink text-base">
                      {item.canonical_name || item.mandi_name}
                    </h4>
                    <span className="text-xs text-muted block">
                      {item.district}, {item.state} {item.mandal ? `• ${item.mandal}` : ''}
                    </span>
                  </div>

                  {item.distance_km !== null && item.distance_km !== undefined ? (
                    <span
                      className="px-2 py-0.5 rounded-full bg-deep-leaf/10 text-deep-leaf text-xs font-bold whitespace-nowrap flex items-center gap-1"
                      title={item.distance_label || 'straight-line distance'}
                    >
                      <MapPin className="w-3 h-3" />
                      {item.distance_km.toFixed(1)} km
                    </span>
                  ) : null}
                </div>

                {/* Price block */}
                <div className="flex items-center justify-between pt-1">
                  <div>
                    <span className="text-[11px] font-bold text-muted uppercase block">Modal Auction Rate</span>
                    <span className="font-heading text-2xl font-black text-deep-leaf">
                      ₹{modalPrice.toFixed(1)}
                      <span className="text-xs font-normal text-muted">/{priceUnit}</span>
                    </span>
                  </div>

                  <div className="text-right">
                    <span className="text-[11px] font-bold text-muted uppercase block">Min &mdash; Max</span>
                    <span className="text-xs font-bold text-ink block">
                      ₹{minPrice.toFixed(0)} &mdash; ₹{maxPrice.toFixed(0)}
                    </span>
                  </div>
                </div>

                {/* 30-Day Trend Sparkline (Rule 2) */}
                <div className="p-2 bg-cream/70 rounded-xl border border-border flex items-center justify-between">
                  <span className="text-[11px] font-bold text-muted">30-Day Trend:</span>
                  <PriceSparkline points={item.sparkline_30d} />
                </div>

                {/* Footer details: Arrivals & Reported date */}
                <div className="flex items-center justify-between text-xs pt-1 border-t border-border/70 text-muted">
                  <span>
                    Arrivals: <strong className="text-ink">{item.arrival_tonnes.toFixed(1)} MT</strong>
                  </span>

                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                      item.is_reported_today
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-amber-100 text-amber-900'
                    }`}
                  >
                    {item.is_reported_today ? 'Today' : `${item.age_label} (${item.reported_date})`}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* 6. PAGINATION CONTROLS (Rule 6) */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-2 text-xs">
          <button
            type="button"
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            className="px-3.5 py-2 rounded-xl border border-border bg-white text-ink font-bold disabled:opacity-40 hover:bg-cream transition-colors flex items-center gap-1"
          >
            <ChevronLeft className="w-4 h-4" />
            <span>Previous</span>
          </button>

          <span className="text-muted font-semibold">
            Page <strong className="text-ink">{currentPage}</strong> of{' '}
            <strong className="text-ink">{totalPages}</strong>
          </span>

          <button
            type="button"
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages}
            className="px-3.5 py-2 rounded-xl border border-border bg-white text-ink font-bold disabled:opacity-40 hover:bg-cream transition-colors flex items-center gap-1"
          >
            <span>Next</span>
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </section>
  );
}
