'use client';

import React, { useEffect, useRef, useState } from 'react';
import { MapPin, Navigation, Layers, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';

export interface FarmerLocationPin {
  listing_id: number;
  farmer_name: string;
  variety: string;
  quantity_kg: number;
  grade: 'A' | 'B' | 'C';
  expected_price_kg: number;
  distance_km: number;
  latitude: number;
  longitude: number;
  match_score?: number;
}

export interface MapLibreViewProps {
  buyerLat: number;
  buyerLng: number;
  buyerName: string;
  farmerPins: FarmerLocationPin[];
  selectedListingId?: number | null;
  onSelectListing: (listing: FarmerLocationPin) => void;
  className?: string;
}

export function MapLibreView({
  buyerLat,
  buyerLng,
  buyerName,
  farmerPins,
  selectedListingId,
  onSelectListing,
  className = '',
}: MapLibreViewProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const [useMapLibre, setUseMapLibre] = useState(true);
  const [mapLoaded, setMapLoaded] = useState(false);
  const mapInstanceRef = useRef<any>(null);

  // Initialize MapLibre GL JS
  useEffect(() => {
    let isMounted = true;
    let map: any = null;

    async function initMap() {
      try {
        const maplibreModule = await import('maplibre-gl');
        const maplibregl = (maplibreModule as any).default || maplibreModule;

        if (!mapContainerRef.current || !isMounted) return;

        map = new maplibregl.Map({
          container: mapContainerRef.current,
          style: {
            version: 8,
            sources: {
              osm: {
                type: 'raster',
                tiles: [
                  'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                ],
                tileSize: 256,
                attribution: '&copy; OpenStreetMap contributors',
              },
            },
            layers: [
              {
                id: 'osm-tiles',
                type: 'raster',
                source: 'osm',
                minzoom: 0,
                maxzoom: 19,
              },
            ],
          },
          center: [buyerLng, buyerLat],
          zoom: 10,
        });

        map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');

        map.on('load', () => {
          if (!isMounted) return;
          setMapLoaded(true);
          mapInstanceRef.current = map;

          // Add Buyer Marker
          const buyerEl = document.createElement('div');
          buyerEl.className =
            'w-8 h-8 rounded-full bg-amber text-ink border-2 border-white shadow-lg flex items-center justify-center font-bold text-xs ring-4 ring-amber/30 cursor-pointer';
          buyerEl.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>`;

          new maplibregl.Marker({ element: buyerEl })
            .setLngLat([buyerLng, buyerLat])
            .setPopup(
              new maplibregl.Popup({ offset: 15 }).setHTML(
                `<div class="p-2 font-body"><p class="font-bold text-ink">${buyerName}</p><p class="text-xs text-muted">Buyer Location (50 km radius)</p></div>`
              )
            )
            .addTo(map);

          // Add Farmer Listing Markers
          farmerPins.forEach((pin) => {
            const el = document.createElement('div');
            el.className = `w-7 h-7 rounded-full ${
              selectedListingId === pin.listing_id ? 'bg-amber ring-4 ring-amber/40 scale-125' : 'bg-deep-leaf ring-2 ring-deep-leaf/30'
            } text-white border-2 border-white shadow-md flex items-center justify-center font-bold text-xs cursor-pointer transition-transform hover:scale-125`;
            el.innerHTML = `<span>${pin.grade}</span>`;

            el.addEventListener('click', () => {
              onSelectListing(pin);
            });

            new maplibregl.Marker({ element: el })
              .setLngLat([pin.longitude, pin.latitude])
              .setPopup(
                new maplibregl.Popup({ offset: 12 }).setHTML(
                  `<div class="p-2 font-body text-xs">
                    <p class="font-bold text-deep-leaf">${pin.farmer_name}</p>
                    <p class="text-ink font-semibold">${pin.variety} &bull; ${pin.quantity_kg} kg</p>
                    <p class="text-ink font-bold">₹${pin.expected_price_kg}/kg &bull; ${pin.distance_km.toFixed(1)} km away</p>
                    <p class="text-muted text-[10px] mt-1">Grade ${pin.grade} Verified Produce</p>
                  </div>`
                )
              )
              .addTo(map);
          });
        });
      } catch (err) {
        // Fallback to SVG Geographic Radar if WebGL fails in headless browser
        console.warn('MapLibre GL initialization fallback to SVG radar:', err);
        setUseMapLibre(false);
      }
    }

    initMap();

    return () => {
      isMounted = false;
      if (map) {
        map.remove();
      }
    };
  }, [buyerLat, buyerLng, farmerPins, buyerName, onSelectListing, selectedListingId]);

  return (
    <div className={`relative bg-white rounded-3xl border border-border overflow-hidden shadow-sm ${className}`}>
      {/* Top Banner Control */}
      <div className="absolute top-3 left-3 z-10 flex items-center gap-2 bg-white/95 backdrop-blur px-3 py-1.5 rounded-full border border-border shadow-sm text-xs font-semibold text-ink">
        <Navigation className="w-3.5 h-3.5 text-deep-leaf animate-pulse" />
        <span>50 km Farm Radius Around {buyerName}</span>
        <span className="w-1.5 h-1.5 rounded-full bg-deep-leaf"></span>
        <span className="text-muted">{farmerPins.length} Matched Farms</span>
      </div>

      <div className="absolute top-3 right-3 z-10">
        <Button
          variant="secondary"
          size="md"
          onClick={() => setUseMapLibre(!useMapLibre)}
          className="bg-white/95 backdrop-blur shadow-sm text-xs h-9 px-2.5"
          leftIcon={<Layers className="w-3.5 h-3.5 text-muted" />}
        >
          {useMapLibre ? 'Radar Mode' : 'Tile Mode'}
        </Button>
      </div>

      {/* Render MapLibre Container or SVG Radar */}
      {useMapLibre ? (
        <div ref={mapContainerRef} className="w-full h-[380px] sm:h-[420px] bg-cream/50 relative">
          {!mapLoaded && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-cream/70 text-muted gap-2 text-sm font-semibold">
              <div className="w-6 h-6 border-2 border-deep-leaf border-t-transparent rounded-full animate-spin" />
              <span>Loading 50 km map coverage...</span>
            </div>
          )}
        </div>
      ) : (
        /* High-Contrast SVG 50 km Radar Fallback */
        <div className="w-full h-[380px] sm:h-[420px] bg-cream relative flex items-center justify-center p-6 overflow-hidden">
          {/* Radar Circles */}
          <div className="relative w-[320px] h-[320px] rounded-full border border-deep-leaf/30 bg-deep-leaf/5 flex items-center justify-center">
            {/* 25 km ring */}
            <div className="w-[200px] h-[200px] rounded-full border border-dashed border-deep-leaf/30 flex items-center justify-center">
              {/* 10 km ring */}
              <div className="w-[100px] h-[100px] rounded-full border border-deep-leaf/20 flex items-center justify-center" />
            </div>

            {/* Radar labels */}
            <span className="absolute top-2 text-[10px] font-bold text-muted uppercase tracking-wider">
              50 km Boundary
            </span>
            <span className="absolute top-16 text-[10px] font-bold text-muted/70">
              25 km
            </span>
            <span className="absolute top-28 text-[10px] font-bold text-muted/60">
              10 km
            </span>

            {/* Center: Buyer Pin */}
            <div className="absolute z-20 flex flex-col items-center">
              <div className="w-8 h-8 rounded-full bg-amber text-ink border-2 border-white shadow-lg flex items-center justify-center font-bold text-xs ring-4 ring-amber/30">
                <MapPin className="w-4 h-4 fill-ink" />
              </div>
              <span className="text-[11px] font-bold text-ink bg-white/90 px-2 py-0.5 rounded-full shadow-xs mt-1 border border-border">
                {buyerName}
              </span>
            </div>

            {/* Farmer Pins plotted on radar */}
            {farmerPins.map((pin, idx) => {
              // Convert km and lat/lng offset into radial angle & radius
              const angle = ((pin.longitude - buyerLng) * 200 + idx * 45) * (Math.PI / 180);
              const radiusRatio = Math.min(pin.distance_km / 50.0, 0.95);
              const radiusPx = radiusRatio * 150; // max 150px from center
              const x = Math.cos(angle) * radiusPx;
              const y = Math.sin(angle) * radiusPx;

              const isSelected = selectedListingId === pin.listing_id;

              return (
                <button
                  key={pin.listing_id}
                  onClick={() => onSelectListing(pin)}
                  style={{
                    transform: `translate(${x}px, ${y}px)`,
                  }}
                  className={`absolute z-30 flex flex-col items-center group transition-transform ${
                    isSelected ? 'scale-125 z-40' : 'hover:scale-110'
                  }`}
                  aria-label={`Listing by ${pin.farmer_name}`}
                >
                  <div
                    className={`w-7 h-7 rounded-full border-2 border-white shadow-md flex items-center justify-center font-bold text-xs ${
                      isSelected
                        ? 'bg-amber text-ink ring-4 ring-amber/40'
                        : 'bg-deep-leaf text-white ring-2 ring-deep-leaf/30'
                    }`}
                  >
                    {pin.grade}
                  </div>
                  <span className="text-[10px] font-bold text-ink bg-white/90 px-1.5 py-0.2 rounded shadow-xs mt-0.5 border border-border whitespace-nowrap">
                    ₹{pin.expected_price_kg} &bull; {pin.distance_km.toFixed(0)}km
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Map Legend */}
      <div className="p-3 bg-white border-t border-border flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5 font-medium text-ink">
            <span className="w-3 h-3 rounded-full bg-amber border border-white ring-1 ring-amber/40"></span>
            <span>Your Institution</span>
          </div>
          <div className="flex items-center gap-1.5 font-medium text-ink">
            <span className="w-3 h-3 rounded-full bg-deep-leaf border border-white ring-1 ring-deep-leaf/40"></span>
            <span>Matched Farmer Listings (A/B/C Grade)</span>
          </div>
        </div>
        <div className="flex items-center gap-1 text-muted">
          <CheckCircle2 className="w-3.5 h-3.5 text-deep-leaf" />
          <span>All 3-Photo Checklists Verified Fresh (&lt;24h)</span>
        </div>
      </div>
    </div>
  );
}
