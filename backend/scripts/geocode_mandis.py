"""
OpenStreetMap Nominatim geocoding script for Andhra Pradesh Mandis.
Features:
- Rate-limiting (1.0 second delay between requests per OSM policy)
- Persistent JSON cache (backend/data/geocache.json)
- Manual CSV override priority (backend/data/mandi_coordinates_override.csv)
"""

import csv
import json
import logging
import time
from pathlib import Path

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CACHE_FILE = DATA_DIR / "geocache.json"
OVERRIDE_CSV = DATA_DIR / "mandi_coordinates_override.csv"

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "GrowCircle-Geocoder/1.0 (contact@growcircle.app)"


def load_cache() -> dict[str, dict[str, float]]:
    if CACHE_FILE.exists():
        with open(CACHE_FILE, encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}


def save_cache(cache: dict[str, dict[str, float]]) -> None:
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)


def load_manual_overrides() -> dict[str, tuple[float, float]]:
    overrides = {}
    if OVERRIDE_CSV.exists():
        with open(OVERRIDE_CSV, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row["name"].strip()
                try:
                    overrides[name] = (float(row["latitude"]), float(row["longitude"]))
                except (ValueError, KeyError):
                    pass
    return overrides


def geocode_mandi(
    name: str,
    district: str,
    state: str = "Andhra Pradesh",
    cache: dict[str, dict[str, float]] | None = None,
    overrides: dict[str, tuple[float, float]] | None = None,
) -> tuple[float | None, float | None, str]:
    """
    Geocodes a mandi with manual override and cache checks.
    Returns: (lat, lng, source)
    """
    cache = cache or {}
    overrides = overrides or {}

    # 1. Check manual override
    if name in overrides:
        lat, lng = overrides[name]
        return lat, lng, "manual_override_csv"

    # 2. Check cache
    cache_key = f"{name}_{district}_{state}".lower()
    if cache_key in cache:
        cached = cache[cache_key]
        return cached["lat"], cached["lng"], "cache"

    # 3. Live Nominatim Query (Rate-limited)
    query = f"{name}, {district}, {state}, India"
    headers = {"User-Agent": USER_AGENT}
    params = {"q": query, "format": "json", "limit": 1}

    logger.info(f"Querying Nominatim for: '{query}'")
    try:
        time.sleep(1.0)  # Strict OSM rate-limiting
        resp = httpx.get(NOMINATIM_URL, params=params, headers=headers, timeout=10.0)
        if resp.status_code == 200:
            results = resp.json()
            if results:
                lat = float(results[0]["lat"])
                lng = float(results[0]["lon"])
                cache[cache_key] = {"lat": lat, "lng": lng}
                save_cache(cache)
                return lat, lng, "nominatim_api"
    except Exception as e:
        logger.error(f"Geocoding failed for {name}: {e}")

    return None, None, "not_found"


def main() -> None:
    logger.info("Starting Mandi Geocoding pipeline...")
    cache = load_cache()
    overrides = load_manual_overrides()

    mandis = [
        ("Guntur", "Guntur"),
        ("Madanapalle", "Annamayya"),
        ("Vijayawada", "NTR"),
        ("Anantapur", "Anantapur"),
        ("Kurnool", "Kurnool"),
        ("Tirupati", "Tirupati"),
        ("Rajahmundry", "East Godavari"),
        ("Tenali", "Guntur"),
    ]

    for name, district in mandis:
        lat, lng, source = geocode_mandi(name, district, cache=cache, overrides=overrides)
        logger.info(f"Mandi: {name:<12} | District: {district:<12} -> ({lat}, {lng}) via {source}")

    logger.info("Geocoding process complete.")


if __name__ == "__main__":
    main()
