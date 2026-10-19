"""
OpenStreetMap Nominatim Geocoding Client with Strict Usage Policy Compliance.
Features:
1. Custom User-Agent header (Nominatim policy requirement).
2. Rate-limiting enforced at max 1 request per second.
3. Persistent disk cache in data/cache/nominatim/ to eliminate duplicate HTTP requests.
4. Coordinate sanity check: ensures coordinates fall inside the state's geographic bounds.
5. Confidence scoring and review flagging for ambiguous or low-confidence matches.
6. Absolute rule: NEVER invent or guess coordinates.
"""

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
CACHE_DIR = ROOT_DIR / "data" / "cache" / "nominatim"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# State geographic bounding boxes for coordinate sanity verification
STATE_BOUNDING_BOXES: dict[str, dict[str, float]] = {
    "andhra pradesh": {"min_lat": 12.6, "max_lat": 19.9, "min_lon": 76.7, "max_lon": 84.8},
    "telangana": {"min_lat": 15.8, "max_lat": 19.9, "min_lon": 77.2, "max_lon": 81.8},
    "karnataka": {"min_lat": 11.5, "max_lat": 18.5, "min_lon": 74.0, "max_lon": 78.6},
    "tamil nadu": {"min_lat": 8.0, "max_lat": 13.6, "min_lon": 76.2, "max_lon": 80.4},
    "maharashtra": {"min_lat": 15.6, "max_lat": 22.0, "min_lon": 72.6, "max_lon": 80.9},
}


@dataclass
class GeocodeResult:
    latitude: float | None
    longitude: float | None
    confidence: float
    display_name: str | None
    location_verified: bool
    needs_review: bool
    review_reason: str | None
    source: str = "nominatim"
    from_cache: bool = False


class NominatimGeocoder:
    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
    USER_AGENT = "GrowCircle-MandiMaster/1.0 (contact@growcircle.in; agricultural-logistics)"

    def __init__(self, min_request_interval: float = 1.0):
        self.min_interval = min_request_interval
        self._last_request_time = 0.0
        self._lock = asyncio.Lock()

    def _get_cache_path(self, query: str) -> Path:
        query_hash = hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()
        return CACHE_DIR / f"{query_hash}.json"

    def is_coordinate_inside_state(self, lat: float, lon: float, state_name: str) -> bool:
        """Sanity check: validates if lat/lon falls within state bounding box."""
        key = state_name.strip().lower()
        bbox = STATE_BOUNDING_BOXES.get(key)
        if not bbox:
            return True  # Unknown state, cannot strictly bound
        return (
            bbox["min_lat"] <= lat <= bbox["max_lat"]
            and bbox["min_lon"] <= lon <= bbox["max_lon"]
        )

    async def _rate_limit_wait(self) -> None:
        """Enforces at least 1.0 second between consecutive Nominatim requests."""
        async with self._lock:
            elapsed = time.monotonic() - self._last_request_time
            if elapsed < self.min_interval:
                await asyncio.sleep(self.min_interval - elapsed)
            self._last_request_time = time.monotonic()

    async def geocode_mandi(
        self,
        mandi_name: str,
        district: str,
        state: str,
        country: str = "India",
    ) -> GeocodeResult:
        """
        Geocodes a mandi using structured address search with local caching and sanity validation.
        """
        query_str = f"{mandi_name}, {district}, {state}, {country}"
        cache_path = self._get_cache_path(query_str)

        # 1. Check disk cache
        if cache_path.exists():
            try:
                with open(cache_path, encoding="utf-8") as f:
                    cached_data = json.load(f)
                    res = self._process_nominatim_results(cached_data, mandi_name, district, state)
                    res.from_cache = True
                    return res
            except Exception as ex:
                logger.warning(f"Error reading geocode cache for {query_str}: {ex}")

        # 2. Rate-limit wait before network query
        await self._rate_limit_wait()

        # 3. Network request
        params = {
            "q": query_str,
            "format": "json",
            "addressdetails": 1,
            "limit": 3,
            "countrycodes": "in",
        }
        headers = {"User-Agent": self.USER_AGENT}

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.get(self.NOMINATIM_URL, params=params, headers=headers)
                if resp.status_code != 200:
                    logger.warning(f"Nominatim returned HTTP {resp.status_code} for '{query_str}'")
                    return GeocodeResult(
                        latitude=None,
                        longitude=None,
                        confidence=0.0,
                        display_name=None,
                        location_verified=False,
                        needs_review=True,
                        review_reason=f"Geocoding service HTTP {resp.status_code}",
                    )

                results = resp.json()

                # Save raw response to cache
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)

                return self._process_nominatim_results(results, mandi_name, district, state)

        except Exception as ex:
            logger.error(f"Geocoding network exception for '{query_str}': {ex}")
            return GeocodeResult(
                latitude=None,
                longitude=None,
                confidence=0.0,
                display_name=None,
                location_verified=False,
                needs_review=True,
                review_reason=f"Geocoding network error: {ex}",
            )

    def _process_nominatim_results(
        self,
        results: list[dict[str, Any]],
        mandi_name: str,
        district: str,
        state: str,
    ) -> GeocodeResult:
        if not results:
            return GeocodeResult(
                latitude=None,
                longitude=None,
                confidence=0.0,
                display_name=None,
                location_verified=False,
                needs_review=True,
                review_reason="No match found in OpenStreetMap Nominatim",
            )

        top_match = results[0]
        try:
            lat = float(top_match.get("lat"))
            lon = float(top_match.get("lon"))
        except (TypeError, ValueError):
            return GeocodeResult(
                latitude=None,
                longitude=None,
                confidence=0.0,
                display_name=None,
                location_verified=False,
                needs_review=True,
                review_reason="Invalid coordinates in Nominatim response",
            )

        # Coordinate sanity check: must fall within state bounding box
        if not self.is_coordinate_inside_state(lat, lon, state):
            return GeocodeResult(
                latitude=lat,
                longitude=lon,
                confidence=0.2,
                display_name=top_match.get("display_name"),
                location_verified=False,
                needs_review=True,
                review_reason=f"Coordinate ({lat:.4f}, {lon:.4f}) outside bounds for {state}",
            )

        importance = float(top_match.get("importance", 0.5))
        place_type = top_match.get("type", "")
        place_class = top_match.get("class", "")

        # High confidence if match specifies city, town, village, marketplace, or high importance
        is_granular = place_type in (
            "marketplace", "commercial", "city", "town", "village", "suburb", "neighbourhood"
        ) or place_class in ("shop", "amenity", "place")

        if is_granular and importance >= 0.5:
            confidence = min(round(importance + 0.3, 2), 0.95)
            return GeocodeResult(
                latitude=lat,
                longitude=lon,
                confidence=confidence,
                display_name=top_match.get("display_name"),
                location_verified=True,
                needs_review=False,
                review_reason=None,
            )

        # Moderate/low confidence (e.g. matched only broad district or administrative boundary)
        confidence = round(importance, 2)
        return GeocodeResult(
            latitude=lat,
            longitude=lon,
            confidence=confidence,
            display_name=top_match.get("display_name"),
            location_verified=False,
            needs_review=True,
            review_reason="Low-confidence match (broad boundary rather than specific market yard)",
        )
